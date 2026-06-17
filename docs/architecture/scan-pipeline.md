---
title: Scan Pipeline
description: How RCARS analyzes Showroom content — cloning, filtering, LLM analysis, embeddings, and deduplication
---

# Scan Pipeline

The scan pipeline is how RCARS understands what each lab teaches. For every catalog item that has a Showroom (a Git repository containing the lab's AsciiDoc content), the pipeline clones the repo, reads the content files, sends them to an LLM for structured analysis, generates vector embeddings from the analysis, and stores everything in PostgreSQL. The result is a searchable understanding of each lab — its topics, learning objectives, audience, duration, and format suitability — that powers both the recommendation engine and content overlap detection.

The pipeline runs on the scan worker and is implemented in `analyzer.py`. It can be triggered per-item, in bulk for unanalyzed content, or automatically as part of the nightly maintenance pipeline when stale content is detected.

```mermaid
flowchart TD
    Start[Catalog Item] --> Clone[Clone Showroom Repo<br/>git clone --depth 1]
    Clone --> Nav{nav.adoc<br/>exists?}
    Nav -->|Yes| NavFilter[Parse nav.adoc<br/>Keep only referenced pages]
    Nav -->|No| ReadAll[Read all .adoc files<br/>from content/modules/ROOT/pages/]
    NavFilter --> Filter[Filter Boilerplate<br/>login, index, credentials pages]
    ReadAll --> Filter
    Filter --> Prompt[Build Prompt<br/>+ CI metadata]
    Prompt --> LLM[Call Claude Sonnet<br/>max_tokens=8192, temp=0]
    LLM --> Parse[Parse JSON Response]
    Parse --> Embed[Generate Embeddings<br/>all-MiniLM-L6-v2, 384-dim]
    Embed --> Store[Store Analysis +<br/>Embeddings in PostgreSQL]
    Store --> Siblings{Has Siblings?<br/>Same URL+ref}
    Siblings -->|Yes| Propagate[Propagate to<br/>All Siblings]
    Siblings -->|No| Cleanup[Cleanup<br/>Delete Clone]
    Propagate --> Cleanup
```

Each item is processed independently with no shared state between items.

## Step 1 — Clone

The item's Showroom Git repository is shallow-cloned (`--depth 1`) to a temporary directory. If the configured branch or ref is not found, the clone falls back to the repository's default branch. Clone timeout is 120 seconds. On any clone failure, the item is marked as an error in the action log and the pipeline moves to the next item.

## Step 2 — Read

AsciiDoc files are read from the standard Antora content layout: `content/modules/ROOT/pages/*.adoc`. If a `nav.adoc` navigation file exists, RCARS parses it to identify which pages are actively linked — only pages referenced in `nav.adoc` xref lines are included. This prevents reading orphaned or draft pages that are present in the repo but not part of the live content. A custom content path can be set via the `content_path` field to handle non-standard repository layouts. Files are read with error-replacement for encoding issues. The repository HEAD commit SHA and timestamp are recorded for staleness tracking.

## Step 3 — Filter Boilerplate

Not all pages in a Showroom contain educational content. Login/credentials pages, environment setup pages, index and navigation pages, and author bio pages are filtered out before the content reaches the LLM. The filter checks both filename patterns (e.g., `index.adoc`) and content signals in the first 500 characters of each file (e.g., "your username is", "your lab environment has been provisioned"). If the filter removes everything, the pipeline falls back to the unfiltered content rather than failing.

This filtering step is important for analysis quality. Without it, the LLM would spend a significant portion of its context window on content that looks similar across every Showroom in the catalog and teaches it nothing about what makes this particular lab unique.

## Step 4 — Build Prompt and Call Sonnet

The filtered file contents are concatenated with file-level headers and truncated to a maximum of 150,000 characters. This text, along with the catalog item's metadata (CI name, display name, category, product), is inserted into the analysis prompt template (`prompts/analyze_showroom.txt`).

The prompt instructs the model to focus on what someone would **learn or experience** by completing the lab. It explicitly tells the model to skip boilerplate pages (login, credentials, environment setup) even if they slipped through the file-level filter. The prompt asks for structured JSON covering:

- **Content type** — `workshop` or `demo`
- **Summary** — 2-3 sentence description of what the lab covers and who it's for
- **Products** — Red Hat product names covered (official names)
- **Audience** — target audience descriptors (e.g., "platform engineers", "developers")
- **Difficulty** — `beginner`, `intermediate`, or `advanced` based on prerequisite knowledge
- **Estimated duration** — realistic completion time in minutes
- **Topics** — specific technical topics (e.g., "Kubernetes operators", "CI/CD pipelines")
- **Learning objectives** — split into two categories:
    - **Stated**: objectives the Showroom explicitly claims
    - **Inferred**: objectives determined from the actual exercises (e.g., a lab that deploys with ArgoCD teaches "GitOps workflows" even if never stated)
- **Modules** — per-module breakdown with title, topics, learning objectives, and duration estimate
- **Use cases** — business problems this content helps solve
- **Event fit** — suitability assessment for two formats: `demo` and `hands_on_lab`, each with a boolean and notes explaining why

Temperature is set to 0. Each analysis call is completely stateless — no conversation history is maintained between items, and the model has no knowledge of other items in the catalog.

### Example Output

A typical analysis response (abbreviated) looks like:

```json
{
  "content_type": "workshop",
  "summary": "A hands-on workshop that guides platform engineers through deploying and configuring Red Hat OpenShift AI on an existing OpenShift cluster, including model serving, data science pipelines, and GPU workload management.",
  "products": ["Red Hat OpenShift AI", "Red Hat OpenShift Container Platform"],
  "audience": ["platform engineers", "ML engineers", "data scientists"],
  "difficulty": "intermediate",
  "estimated_duration_min": 120,
  "topics": ["model serving", "data science pipelines", "GPU scheduling", "S3 storage integration"],
  "learning_objectives": {
    "stated": ["Deploy and configure OpenShift AI components", "Create and manage data science projects"],
    "inferred": ["Kubernetes resource management for ML workloads", "Object storage integration patterns"]
  },
  "modules": [
    {
      "title": "Deploying OpenShift AI Operator",
      "topics": ["operator installation", "custom resource configuration"],
      "learning_objectives": ["Install and configure the RHOAI operator"],
      "estimated_duration_min": 20
    }
  ],
  "use_cases": ["AI/ML platform enablement", "self-service data science environments"],
  "event_fit": {
    "demo": {"suitable": true, "notes": "First two modules work well as a 30-min demo of RHOAI capabilities"},
    "hands_on_lab": {"suitable": true, "notes": "Full workshop designed for 2-hour hands-on session"}
  }
}
```

This structured output drives everything downstream: the summary and learning objectives feed into vector embeddings for semantic search, the module breakdown enables the recommendation engine to suggest partial lab usage, and the duration estimate informs duration-aware reranking.

## Step 5 — Parse Response

Sonnet's response is expected to be JSON. The parser handles common response artifacts: markdown code fences (`` ```json ``), leading/trailing whitespace, and partial JSON embedded in a longer response. If parsing fails entirely, the item is marked as an error.

## Step 6 — Generate Embeddings

This is where the structured analysis from Step 4 gets converted into a form that enables semantic search. The analysis JSON tells us *what* a lab teaches in human-readable terms. The embedding step converts that into a **vector** — a list of 384 numbers — that captures the *meaning* of that content in a way that a database can search efficiently.

The conversion is done by a sentence-transformers model (`all-MiniLM-L6-v2`) that runs locally inside the RCARS pod. The model takes text as input and produces a 384-dimensional vector as output. Texts with similar meaning produce similar vectors — so two labs that both teach "deploying applications with GitOps on OpenShift" will have vectors that point in roughly the same direction, even if one uses ArgoCD terminology and the other uses Flux.

These vectors are stored in the `embeddings` table in PostgreSQL (using the pgvector extension) and are the foundation for two features:

- The [recommendation engine](recommendation-engine.md) converts a user's query into the same kind of vector and finds the closest lab vectors — this is how RCARS matches "I need content about Kubernetes security" to labs that cover ACS, compliance operators, and pod security standards.
- [Content overlap detection](content-overlap.md) compares lab vectors against each other to find duplicates — two labs with very similar vectors teach substantially the same material.

### What Goes Into Each Embedding

RCARS generates two types of embeddings per catalog item:

**CI-level embedding** (one per item) — the primary search target. Built by concatenating:

- Analysis summary
- All learning objectives (stated + inferred)
- Topics
- Products
- Audience descriptors
- Use cases
- **Catalog keywords** from the CRD's `spec.keywords` (event tags like `rh1-2026`, product identifiers, lab codes)

The catalog keywords are important because they contain metadata not present in the Showroom content itself. Including them means queries like "Summit 2026 labs" can match via vector similarity even when the Showroom content never mentions the event.

**Module-level embeddings** (one per module) — built from each module's title, topics, and learning objectives. Stored for future module-level matching but not currently used in search.

### Keyword Sourcing

The CI-level embedding combines data from **two different sources**: keywords come from Kubernetes CRDs (read during catalog refresh), while the analysis comes from the LLM (generated during scanning). The embedding is built at scan time by combining both. If keywords are added or changed in the CRD after the last scan, the embedding will not reflect them until the item is re-scanned.

### Technical Details

The sentence-transformers model requires no external API call — it runs locally with negligible latency. Embeddings are normalized to unit vectors, which makes cosine similarity equivalent to dot product. pgvector's IVFFlat index on the embedding column enables fast nearest-neighbor search across thousands of vectors.

## Step 7 — Store, Propagate, and Clean Up

The analysis and embeddings are written to the database. The temporary clone directory is deleted. This cleanup runs in a `finally` block — the clone is always deleted regardless of whether earlier steps succeeded or failed.

---

## Deduplication and Propagation

Many catalog items share the same Showroom content. For example, `agd-v2.modernize-ocp-virt` exists as dev, event, and prod — if event and prod both point to the same `(showroom_url, showroom_ref)`, scanning both would be redundant. With ~600 scannable items in the catalog, deduplication and change detection are essential to keeping the nightly pipeline fast and LLM costs reasonable.

### Sibling Grouping

RCARS deduplicates scan jobs by `(showroom_url, showroom_ref)`:

1. All scannable items (with Showroom URL, non-published) are grouped by `(url, ref)`.
2. One representative per group is selected for scanning (prod preferred, then event, then dev).
3. After scanning the representative, the analysis and embeddings are **propagated** to all siblings in the same group.
4. Each sibling gets its own `showroom_analysis` row and `embeddings` rows — every CI is independently searchable and recommendable.

**Different ref = different scan.** If dev has `ref=main` and prod has `ref=v1.0.0`, they are in separate groups and scanned independently, even if the underlying content happens to be identical. This avoids the complexity of resolving whether two refs point to the same commit.

**`ref=NULL` (HEAD) is its own group**, separate from `ref=main` — they may resolve to the same content, but RCARS treats them as distinct.

### Change Detection — Only Scan What Changed

RCARS does not rescan the entire catalog on every run. Whether triggered by the nightly pipeline or a manual scan, only items whose content has actually changed are reprocessed. The change detection is a two-phase process:

1. **Fast check (`git ls-remote`)** — for every analyzed Showroom, RCARS calls `git ls-remote` to get the current commit SHA for the configured ref. This is a lightweight network call that does not clone the repository. If the SHA matches the one recorded during the last scan, the item is unchanged and skipped entirely.

2. **Content hash comparison** — if the SHA has changed (or the item has never been scanned), RCARS clones the repo and hashes the content files. If the hash matches the stored `content_hash`, the content is identical despite the SHA change (e.g., a merge commit that didn't modify the content directory). The item is still skipped.

Only items that fail both checks — new SHA **and** different content hash — are sent through the full scan pipeline (Steps 1-7 above). In practice, the nightly pipeline typically rescans 5-20 items out of ~600, completing in minutes rather than hours.

Clone operations use exponential backoff with 3 retries (10s, 20s, 40s delays) when GitHub rate limiting is detected.

---

## Error Classification

When a scan fails, RCARS classifies the error into one of these categories (stored in `catalog_items.scan_error_class`):

| Error Class | Cause |
|---|---|
| `jinja_url` | Showroom URL contains unresolved Jinja2 template variables |
| `timeout` | Git clone or LLM call exceeded timeout |
| `private_repo` | Git repository requires authentication |
| `http_404` | Repository URL returns 404 |
| `clone_failed` | Git clone failed (network, permissions, other git error) |
| `missing_antora` | Repository does not follow standard Antora layout (`content/modules/ROOT/pages/`) |
| `no_content` | No substantive content files found after boilerplate filtering |
| `parse_error` | LLM response could not be parsed as JSON |
| `unknown` | Unclassified error |

Error classes enable targeted debugging — `jinja_url` errors indicate a catalog metadata issue, while `no_content` errors may need a custom `content_path` override.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `RCARS_MODEL` | `claude-sonnet-4-6` | Model used for content analysis |
| `RCARS_MAX_PARALLEL` | 5 | Max concurrent scan jobs per worker pod |
| `RCARS_CLONE_DIR` | `/tmp/rcars-clones` | Temporary directory for git clones |
| `RCARS_STALE_DAYS` | 3 | Days before content is considered potentially stale |

## CLI

```bash
rcars refresh              # Sync catalog from Babylon CRDs
rcars scan [--max N]       # Analyze unanalyzed items (optionally limit batch size)
rcars status [--failures]  # Show catalog and analysis status
```

## API

- `POST /analysis/scan` — start scan of unanalyzed items
- `POST /analysis/check-stale` — run stale content detection
- `POST /analysis/rescan-all` — mark all stale and full rescan
- `POST /analysis/{ci_name}` — analyze a single item
- `POST /catalog/refresh` — trigger catalog refresh
