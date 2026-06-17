---
title: Scan Pipeline
description: How RCARS analyzes Showroom content — cloning, filtering, LLM analysis, embeddings, and deduplication
---

# Scan Pipeline

The scan pipeline analyzes Showroom content for each catalog item. It is implemented in `analyzer.py` and runs on the scan worker.

```mermaid
flowchart TD
    Start[Catalog Item] --> Clone[Clone Showroom Repo<br/>git clone --depth 1]
    Clone --> Read[Read .adoc Files<br/>content/modules/ROOT/pages/]
    Read --> Filter[Filter Boilerplate<br/>login, index, credentials pages]
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

The filtered file contents are concatenated with file-level headers and truncated to a maximum of 150,000 characters. This text, along with the catalog item's metadata (CI name, display name, category, product), is inserted into the analysis prompt template.

The prompt instructs Sonnet to:

- Identify what the lab covers and who it's for
- Extract **stated** learning objectives (what the Showroom text explicitly claims)
- Infer **additional** learning objectives from the actual exercises (what a learner will genuinely learn even if it's never stated)
- Assess suitability for booth demos, hands-on sessions, and presentation support
- Return everything as structured JSON

Temperature is set to 0. Each analysis call is completely stateless — no conversation history is maintained between items, and Sonnet has no knowledge of other items in the catalog.

## Step 5 — Parse Response

Sonnet's response is expected to be JSON. The parser handles common response artifacts: markdown code fences (`` ```json ``), leading/trailing whitespace, and partial JSON embedded in a longer response. If parsing fails entirely, the item is marked as an error.

## Step 6 — Generate Embeddings

Two types of embeddings are generated using a locally-running sentence-transformers model (`all-MiniLM-L6-v2`, 384 dimensions):

1. **CI-level embedding** — the analysis summary, all learning objectives, topics, products, audience descriptors, use cases, and **catalog keywords** concatenated into a single string and embedded. This is the primary search target.
2. **Module-level embeddings** — one embedding per module in the analysis, built from the module title, topics, and learning objectives. These are stored but not used in the default similarity search (reserved for future module-level matching).

Catalog keywords (from `catalog_items.keywords`, sourced from the CRD's `spec.keywords` during catalog refresh) are appended to the CI-level embedding text. This is important because keywords contain metadata not present in the Showroom content itself — event tags like `rh1-2026`, product identifiers, and lab codes. Including them in the embedding means queries like "Summit 2026 labs" can match via vector similarity even when the Showroom content never mentions the event.

Keywords and analysis come from **two different sources**: keywords are read from Kubernetes CRDs during catalog refresh, while the analysis is generated by the LLM from Showroom content during scanning. The embedding is built at scan time by combining both. This means that if keywords are added or changed in the CRD after the last scan, the existing embedding will not reflect the new keywords until the item is re-scanned.

The sentence-transformers model runs locally inside the RCARS pod with no external API call. Embeddings are normalized (unit vectors), which makes cosine similarity equivalent to dot product — a requirement of pgvector's `<=>` operator.

## Step 7 — Store, Propagate, and Clean Up

The analysis and embeddings are written to the database. The temporary clone directory is deleted. This cleanup runs in a `finally` block — the clone is always deleted regardless of whether earlier steps succeeded or failed.

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

## Git Retry Logic

Clone operations use exponential backoff with 3 retries (10s, 20s, 40s delays) when GitHub rate limiting is detected. The `git ls-remote` fast check during stale detection has a 30-second timeout.

---

## Deduplication and Propagation

Many catalog items share the same Showroom content. For example, `agd-v2.modernize-ocp-virt` exists as dev, event, and prod — if event and prod both point to the same `(showroom_url, showroom_ref)`, scanning both would be redundant.

RCARS deduplicates scan jobs by `(showroom_url, showroom_ref)`:

1. All scannable items (with Showroom URL, non-published) are grouped by `(url, ref)`.
2. One representative per group is selected for scanning (prod preferred, then event, then dev).
3. After scanning the representative, the analysis and embeddings are **propagated** to all siblings in the same group.
4. Each sibling gets its own `showroom_analysis` row and `embeddings` rows — every CI is independently searchable and recommendable.

**Different ref = different scan.** If dev has `ref=main` and prod has `ref=v1.0.0`, they are in separate groups and scanned independently, even if the underlying content happens to be identical. This avoids the complexity of resolving whether two refs point to the same commit.

**`ref=NULL` (HEAD) is its own group**, separate from `ref=main` — they may resolve to the same content, but RCARS treats them as distinct.

**No content caching.** Every scan is a fresh `git clone` with the ref resolved at clone time. There is no persistent cache of repo content between scans.

Both the CLI (`rcars scan`) and the worker (`run_analysis`) implement propagation identically.
