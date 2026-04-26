---
title: Architecture
description: End-to-end technical architecture of RCARS
---

# Architecture

## System Overview

RCARS is a three-tier application (React SPA, FastAPI API, arq workers) that pulls from the RHDP catalog, analyzes lab content with an LLM, stores results in PostgreSQL with pgvector, and answers recommendation queries using vector similarity search and LLM ranking.

### Deployments

| Component | Image | Queue | Purpose |
|---|---|---|---|
| `rcars-api` | `rcars-api:latest` | — | FastAPI JSON API, serves `/api/v1/*` |
| `rcars-scan-worker` | `rcars-api:latest` | `arq:queue:scan` | Analysis, catalog refresh, stale checks |
| `rcars-recommend-worker` | `rcars-api:latest` | `arq:queue:recommend` | Advisor recommendation queries |
| `rcars-frontend` | `rcars-frontend:latest` | — | React SPA (nginx), proxies `/api/*` to API |

Workers are split into two deployments so bulk scans never block user-facing advisor queries. Both workers use the same container image with different arq entrypoints.

Supporting infrastructure: PostgreSQL 16 + pgvector, Redis 7, OAuth proxy.

The three main pipelines — catalog sync, content analysis, and recommendation — run independently and can be triggered separately. Nothing in the analysis pipeline depends on the state of an ongoing recommendation query, and vice versa.

---

## Data Sources

### Babylon Kubernetes CRDs

The RHDP catalog is defined as Kubernetes custom resources in the Babylon platform. RCARS reads two CRD types from the Babylon namespaces using a read-only kubeconfig:

- **`AgnosticVComponent`** — the primary resource for each catalog item. Contains the display name, category, product, description, keywords, stage, and workload variable configuration (which includes Showroom URLs when present).
- **`CatalogItem`** — the ordering layer resource. Used to resolve published Virtual CI identities and their relationship to underlying base components.

Three namespaces are tracked:

- `babylon-catalog-prod` — live production catalog items
- `babylon-catalog-dev` — items in development or testing
- `babylon-catalog-event` — event-specific items

By default, RCARS syncs only `babylon-catalog-prod`. The `--include-dev` flag on `rcars refresh` includes all three.

### CI Hierarchy

Catalog items in RHDP are not all the same kind of thing. There are broadly three tiers:

- **Published Virtual CIs** — ordering entry points visible on `catalog.demo.redhat.com`. Some catalog items are published this way: the Published VCI is what a user orders, and it references an underlying Base CI for the actual content and provisioning.
- **Base CIs** — the actual lab definitions, containing the Showroom content link, full description, and workload configuration. Many Base CIs are ordered directly — they don't have a Published VCI in front of them. This is actually the more common pattern.
- **Infrastructure CIs** — the underlying provisioning layer. RCARS does not interact with these.

What matters for RCARS is whether a CI has a Showroom URL — that is where the lab content lives and what gets analyzed. RCARS tracks the Published VCI ↔ Base CI relationship when it exists to avoid recommending the same underlying content twice (once as the VCI, once as the base). Where no VCI exists, the Base CI is returned directly as the recommendation target.

---

## Catalog Reader (`services/catalog.py`)

The catalog reader connects to the Babylon Kubernetes API using the configured kubeconfig and lists all `CatalogItem` and `AgnosticVComponent` resources. CatalogItems provide catalog metadata (display name, category, stage); AgnosticVComponents provide the showroom URLs from `spec.definition`.

For each component, it extracts:

- **Display name, category, product, description, keywords, stage** — from CatalogItem CRD metadata and labels
- **Showroom URL and ref** — extracted from the AgnosticVComponent using a three-tier resolution strategy (see below)
- **Published/base CI relationship** — derived from `__meta__.components[].item` references

The catalog reader is stateless. Each call to `rcars refresh` performs a full read and upsert. Items removed from Babylon are deleted from the database.

### Showroom URL Extraction

Showroom URLs are not stored in a single consistent field. RCARS checks three locations in priority order:

**1. Top-level `spec.definition`** — the most common pattern. URL variables checked (in order): `ocp4_workload_showroom_content_git_repo`, `showroom_git_repo`, `bookbag_git_repo`. Ref variables: `ocp4_workload_showroom_content_git_repo_ref`, `ocp4_workload_showroom_content_git_ref`, `showroom_git_ref`.

**2. Template variable resolution** — some CIs use Jinja2 templates for the ref (e.g., `{{ showroom_repo_revision }}`). RCARS resolves these by looking up the variable name in `spec.definition`, with catalog parameter defaults taking precedence per stage. Example: `modernize-ocp-virt` dev has a catalog parameter defaulting to `main`, while prod/event inherit `v1.0.0` from the definition.

**3. Component `parameter_values`** — Zero Touch (ZT) Virtual CIs have `deployer.type: null` and delegate to a base component, passing the showroom URL as a parameter override in `__meta__.components[].parameter_values`. This covers ~254 CIs (entire `zt-rhelbu` and most `zt-ansiblebu`).

**Template repos skipped:** URLs containing `showroom_template_default`, `showroom_template_nookbag`, or `showroom_template_zero` are filtered out — these are placeholder defaults from shared includes, not real content.

---

## PostgreSQL Schema

RCARS uses PostgreSQL with the pgvector extension. Schema is managed with **Alembic** — the baseline migration (`alembic/versions/001_initial_schema.py`) defines the complete initial schema. On OpenShift, the Ansible playbook runs Alembic via `k8s_exec` as the `migrate` deploy tag. For local development, `rcars status` (via `db.create_schema()`) applies the same schema directly and stamps the Alembic version table so the two paths stay in sync.

### Understanding Vector Embeddings

Several sections below reference vector embeddings. Before getting into the table structure, it helps to understand what these are and why they exist.

A **vector embedding** is a fixed-length list of numbers (in RCARS, 384 numbers) that represents the meaning of a piece of text. The numbers are produced by a machine learning model trained to place semantically similar texts close together in this 384-dimensional space. The key property: texts that mean similar things end up with similar vectors, even if they use completely different words.

For example, the phrase "hands-on OpenShift workshop for platform engineers" and the phrase "practical lab teaching Kubernetes cluster management to infrastructure teams" would produce similar vectors, because they describe the same kind of thing. A keyword search would not connect them.

RCARS generates these vectors for every analyzed Showroom using a locally-running sentence-transformers model (`all-MiniLM-L6-v2`). When a user asks a question, the question is converted into the same kind of vector, and PostgreSQL with the **pgvector** extension runs a cosine similarity search — finding stored embeddings whose vectors are closest to the query vector. This is how RCARS finds semantically relevant content without requiring exact keyword matches.

Cosine similarity measures the angle between two vectors regardless of their magnitude. A score of 1.0 means identical direction (perfect match); 0.0 means orthogonal (unrelated). pgvector's `<=>` operator returns cosine *distance* (1 minus similarity), so lower is better. An IVFFlat index on the embedding column makes this search fast even with thousands of stored vectors.

---

### `catalog_items`

One row per catalog item. The primary source of truth for everything read from the Babylon CRDs.

| Column | Type | Description |
|---|---|---|
| `ci_name` | TEXT (PK) | Unique CI identifier, e.g. `openshift-cnv.ocp4-getting-started.prod` |
| `display_name` | TEXT | Human-readable name shown in the UI and catalog |
| `category` | TEXT | Catalog category (e.g. "Workshops", "Demos") |
| `product` | TEXT | Primary Red Hat product |
| `product_family` | TEXT | Red Hat product family grouping |
| `primary_bu` | TEXT | Primary business unit |
| `secondary_bu` | TEXT | Secondary business unit |
| `stage` | TEXT | `prod`, `dev`, or `event` |
| `catalog_namespace` | TEXT | Babylon namespace this item came from |
| `keywords` | TEXT[] | Array of keyword tags |
| `description` | TEXT | Full description from the CRD |
| `icon_url` | TEXT | URL to the catalog item's icon image |
| `owners_json` | JSONB | List of owner contacts from the CRD |
| `showroom_url` | TEXT | Git repository URL for the Showroom lab content |
| `showroom_ref` | TEXT | Git branch or tag for the Showroom repo |
| `last_crd_update` | TIMESTAMPTZ | Timestamp of the last CRD change in Babylon |
| `last_refreshed` | TIMESTAMPTZ | Timestamp of the last `rcars refresh` for this item |
| `is_prod` | BOOLEAN | True if stage is prod |
| `is_published` | BOOLEAN | True if this is a Published Virtual CI |
| `published_ci_name` | TEXT | For Base CIs: the Published VCI that references them (if any) |
| `base_ci_name` | TEXT | For Published VCIs: the Base CI they reference |

---

### `showroom_analysis`

One row per analyzed catalog item. Stores the full structured output from the Sonnet analysis, plus staleness tracking and curator notes.

| Column | Type | Description |
|---|---|---|
| `ci_name` | TEXT (PK, FK) | References `catalog_items.ci_name` |
| `content_type` | TEXT | `"workshop"` or `"demo"` |
| `summary` | TEXT | 2–3 sentence human-readable summary of the lab |
| `products_json` | JSONB | List of Red Hat products covered, e.g. `["OpenShift", "RHEL"]` |
| `audience_json` | JSONB | List of target audience descriptors, e.g. `["developers", "platform engineers"]` |
| `topics_json` | JSONB | Specific technical topics covered |
| `modules_json` | JSONB | Array of module objects: `[{title, topics, learning_objectives, estimated_duration_min}]` |
| `learning_objectives_json` | JSONB | `{stated: [...], inferred: [...]}` — what the lab claims vs. what it actually teaches |
| `difficulty` | TEXT | `"beginner"`, `"intermediate"`, or `"advanced"` |
| `estimated_duration_min` | INTEGER | Estimated time to complete the full lab, in minutes |
| `event_fit_json` | JSONB | Suitability assessments: `{booth_demo: {suitable, notes}, hands_on_lab: {...}, presentation_support: {...}}` |
| `use_cases_json` | JSONB | Business problems or scenarios this content addresses |
| `last_repo_commit` | TEXT | Git HEAD SHA at the time of analysis — used for staleness detection |
| `last_repo_updated` | TIMESTAMPTZ | Commit date of the HEAD at time of analysis |
| `last_analyzed` | TIMESTAMPTZ | When RCARS last ran the analysis pipeline for this item |
| `is_stale` | BOOLEAN | True if the Showroom content has changed since last analysis |
| `stale_commit` | TEXT | HEAD commit SHA at the time staleness was detected |
| `content_hash` | TEXT | SHA-256 hash of the filtered .adoc content — used for change detection |
| `enrichment_review_needed` | BOOLEAN | Curator-set flag indicating this item needs manual review |
| `notes` | TEXT | Free-text curator note — visible only to curators on the Curate page |

JSONB columns are stored as native PostgreSQL JSON and can be queried with JSON operators, though RCARS currently reads them as Python objects rather than querying inside them at the SQL level.

---

### `embeddings`

Stores vector embeddings alongside the text they were generated from. Each row represents one embedded piece of content for one catalog item.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `ci_name` | TEXT (FK) | References `catalog_items.ci_name` |
| `embed_type` | TEXT | `"ci_summary"` (item-level) or `"module"` (per-module) |
| `module_title` | TEXT | Module name — populated only for `embed_type = 'module'` |
| `content_text` | TEXT | The text that was fed to the embedding model — stored for inspection and debugging |
| `embedding` | vector(384) | The 384-dimensional vector produced by sentence-transformers |

Two embedding types are generated per analyzed item:

- **`ci_summary`** — one embedding per catalog item, built from the full analysis: summary, learning objectives (stated and inferred), topics, products, audience, and use cases. This is what the similarity search runs against.
- **`module`** — one embedding per lab module, built from the module title, topics, and learning objectives. Stored for potential future use in module-level matching; not used in the current default search.

The `embedding` column uses pgvector's native `vector(384)` type. An IVFFlat index on this column enables approximate nearest-neighbor search, which is significantly faster than exact search at scale and precise enough for this use case.

---

### `enrichment_tags`

Curator-applied labels attached to catalog items. Tags have a type and a value, allowing structured labeling. Tags are visible to all users on recommendation cards.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `ci_name` | TEXT (FK) | References `catalog_items.ci_name` |
| `tag_type` | TEXT | Label category, e.g. `"lifecycle"`, `"event"`, `"quality"` |
| `tag_value` | TEXT | Label value, e.g. `"retiring"`, `"kubecon-2026"`, `"flagship"` |
| `added_by` | TEXT | Email address of the curator who added the tag |
| `added_at` | TIMESTAMPTZ | When the tag was added |

A unique constraint on `(ci_name, tag_type, tag_value)` prevents duplicates. Tags are additive — multiple curators can tag the same item and all tags are retained.

---

### `analysis_log`

An append-only audit trail of every operation RCARS performs. Used by the Admin UI for scan status and by engineers debugging failed items.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `ci_name` | TEXT | The catalog item involved (not a FK — preserved even if the item is removed) |
| `action` | TEXT | `"refresh"`, `"analyze"`, or `"error"` |
| `user_id` | TEXT | Identity of who or what triggered the action (SSO email or system) |
| `details` | TEXT | Optional extra context — error messages, commit SHAs, etc. |
| `created_at` | TIMESTAMPTZ | When the action was recorded |

Nothing is deleted from this table. It grows with every `rcars refresh` and `rcars scan` run.

---

### `jobs`

Tracks background async jobs — primarily catalog scans triggered from the Admin UI. Allows the UI to show live progress and retrieve results after completion.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Auto-generated job ID, passed to the client to poll for status |
| `job_type` | TEXT | Type of job, e.g. `"scan"` |
| `status` | TEXT | `"queued"`, `"running"`, `"complete"`, or `"failed"` |
| `triggered_by` | TEXT | SSO email of the user who triggered the job |
| `progress_current` | INTEGER | Items processed so far |
| `progress_total` | INTEGER | Total items to process |
| `result_json` | JSONB | Final result payload once the job completes |
| `created_at` | TIMESTAMPTZ | When the job was queued |
| `started_at` | TIMESTAMPTZ | When execution began |
| `completed_at` | TIMESTAMPTZ | When the job finished (success or failure) |

---

## The Scan Pipeline (`analyzer.py`)

The scan pipeline runs per catalog item and is fully isolated — each item is processed independently with no shared state or context leakage between items.

### Step 1 — Clone

The item's Showroom Git repository is shallow-cloned (`--depth 1`) to a temporary directory. If the configured branch or ref is not found, the clone falls back to the repository's default branch. Clone timeout is 120 seconds. On any clone failure, the item is marked as an error in the action log and the pipeline moves to the next item.

### Step 2 — Read

AsciiDoc files are read from the standard Antora content layout: `content/modules/ROOT/pages/*.adoc`. The navigation file (`nav.adoc`) is also read for structural context. Files are read with error-replacement for encoding issues. The repository HEAD commit SHA and timestamp are recorded for staleness tracking.

### Step 3 — Filter Boilerplate

Not all pages in a Showroom contain educational content. Login/credentials pages, environment setup pages, index and navigation pages, and author bio pages are filtered out before the content reaches the LLM. The filter checks both filename patterns (e.g., `index.adoc`) and content signals in the first 500 characters of each file (e.g., "your username is", "your lab environment has been provisioned"). If the filter removes everything, the pipeline falls back to the unfiltered content rather than failing.

This filtering step is important for analysis quality. Without it, the LLM would spend a significant portion of its context window on content that looks similar across every Showroom in the catalog and teaches it nothing about what makes this particular lab unique.

### Step 4 — Build Prompt and Call Sonnet

The filtered file contents are concatenated with file-level headers and truncated to a maximum of 150,000 characters. This text, along with the catalog item's metadata (CI name, display name, category, product), is inserted into the analysis prompt template.

The prompt instructs Sonnet to:

- Identify what the lab covers and who it's for
- Extract **stated** learning objectives (what the Showroom text explicitly claims)
- Infer **additional** learning objectives from the actual exercises (what a learner will genuinely learn even if it's never stated)
- Assess suitability for booth demos, hands-on sessions, and presentation support
- Return everything as structured JSON

Temperature is set to 0. Each analysis call is completely stateless — no conversation history is maintained between items, and Sonnet has no knowledge of other items in the catalog.

### Step 5 — Parse Response

Sonnet's response is expected to be JSON. The parser handles common response artifacts: markdown code fences (`\`\`\`json`), leading/trailing whitespace, and partial JSON embedded in a longer response. If parsing fails entirely, the item is marked as an error.

### Step 6 — Generate Embeddings

Two types of embeddings are generated using a locally-running sentence-transformers model (`all-MiniLM-L6-v2`, 384 dimensions):

1. **CI-level embedding** — the analysis summary, all learning objectives, topics, products, audience descriptors, and use cases concatenated into a single string and embedded. This is the primary search target.
2. **Module-level embeddings** — one embedding per module in the analysis, built from the module title, topics, and learning objectives. These are stored but not used in the default similarity search (reserved for future module-level matching).

The sentence-transformers model runs locally inside the RCARS pod with no external API call. Embeddings are normalized (unit vectors), which makes cosine similarity equivalent to dot product — a requirement of pgvector's `<=>` operator.

### Step 7 — Store, Propagate, and Clean Up

The analysis and embeddings are written to the database. The temporary clone directory is deleted. This cleanup runs in a `finally` block — the clone is always deleted regardless of whether earlier steps succeeded or failed.

---

## Scan Deduplication and Propagation

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

---

## The Recommendation Engine (`recommender/`)

Recommendation is a three-phase progressive pipeline. Each phase narrows and enriches the results. The pipeline is implemented as a generator that yields state after each phase, allowing the web UI to show progressive results.

### Phase 1 — Vector Search

The user's query text is embedded using the same sentence-transformers model used during scanning. A pgvector cosine similarity search (`<=>` operator) finds the top candidates within a configurable distance cutoff (default: 0.55). Results beyond the cutoff are discarded — this prevents low-relevance items from reaching later phases.

**Published/base CI deduplication:** Embeddings are stored on base CIs (they own the Showroom content). When a base CI has a published counterpart, the vector search promotes it — presenting the published CI's identity (the orderable item) while using the base CI's analysis data. Base CIs that have a published counterpart are never shown directly.

### Phase 2 — Haiku Triage

The vector search candidates are sent to Claude Haiku for fast relevance scoring. For each candidate, Haiku assigns a relevance score (0-100), a boolean relevant/not-relevant flag, and a one-line reason. Candidates below the triage cutoff (default: 30) are removed. Survivors are sorted by relevance score.

This phase is fast (~1-3 seconds) and inexpensive. It filters out items that are semantically similar but not actually relevant to the request — something embedding similarity alone cannot do.

### Phase 3 — Sonnet Rationale

The top candidates from triage (default: 5) are sent to Claude Sonnet with their full analysis data for structured rationale generation. For each candidate, Sonnet returns:

- **Why it fits** — topic alignment and learning outcomes
- **How to use** — practical delivery suggestion
- **Suggested format** — booth demo, hands-on lab, or presentation (based on the user's request context)
- **Duration notes** — timing adaptation suggestions
- **Caveats** — concerns or limitations relevant to the request

Sonnet also returns an overall assessment (response, top picks, adapting suggestions, content gaps) and a structured list of content gaps — topics the query asked for that no candidate addresses well. Content gaps are always surfaced in the chat response.

### Event URL Mode

When a URL is detected in the user's query (in both the web UI and CLI), RCARS automatically fetches the event page and follows links to schedule, program, tracks, talks, and similar subpages on the same domain (up to 3 subpages, 80,000 characters combined). This content is sent to Sonnet with a prompt requesting a structured event profile: event name, audience, themes, format opportunities, and suggested search queries. The profile is merged with the user's query before vector search runs.

For broad multi-track events, follow-up queries can narrow results to specific areas (e.g., "focus on platform and infrastructure content").

---

## Frontend (`src/frontend/`)

The frontend is a React Single Page Application built with Vite and TypeScript, styled with the LCARS theme. It is served by nginx and communicates with the FastAPI backend via JSON API calls under `/api/v1/`.

### Pages

- **Advisor** — Two-pane layout: chat on the left, recommendation cards on the right. Queries are submitted via POST, progress is streamed via SSE (Server-Sent Events) from Redis pub/sub, and results render as scored recommendation cards grouped by tier.
- **Browse** — Filterable catalog view showing all items with analysis status. Expandable detail panels show summary, topics, products, difficulty, and duration.
- **Admin** — Four sub-tabs: Catalog Status (sync/scan controls), Workers (queue depths and job list with CI names), Token Usage (LLM cost tracking), Query History (advisor session log).

### API Routes

All API routes are under `/api/v1/`:

- `POST /advisor/query` — Submit recommendation query, returns `{job_id}`
- `GET /advisor/query/{job_id}/stream` — SSE stream of recommendation progress
- `GET /advisor/query/{job_id}/result` — Poll for final results
- `POST /analysis/scan` — Trigger bulk scan of unanalyzed items
- `POST /analysis/{ci_name}` — Trigger single-item analysis
- `POST /catalog/refresh` — Trigger catalog sync from Babylon CRDs
- `GET /catalog/stats` — Catalog status summary
- `GET /catalog/browse` — Paginated catalog listing with filters
- `GET /admin/workers` — Worker health and queue depths
- `GET /admin/scan-progress` — Live scan progress with CI names and propagation counts

### Conversation Store

Advisor sessions are stored in the PostgreSQL `advisor_sessions` table. Each session contains multiple turns with query text, results, and user selections. Sessions persist across server restarts.

### Authentication and Roles

An OAuth proxy sits in front of the application. All requests pass through the proxy, which authenticates users against Red Hat SSO and injects the `X-Forwarded-Email` header.

The API reads this header on every request via a FastAPI dependency (`get_current_user()`):

- **Admin** — email in `RCARS_ADMIN_EMAILS_STR`. Full access including catalog sync, scan, and worker controls.
- **Curator** — email in `RCARS_CURATOR_EMAILS_STR`. Can trigger single-item analysis and manage enrichment tags.
- **Viewer** — authenticated but not in either list. Can use the advisor and browse.

In local development, `RCARS_DEV_USER` bypasses auth entirely.

---

## Deployment

RCARS runs as four separate deployments on OpenShift, all in the `rcars-dev` namespace. See [Deployment Guide](deployment.md) for full setup instructions.

Deployments are managed by an Ansible playbook (`ansible/deploy.yml`) with tagged execution:

| Tag | What it does |
|---|---|
| `update` | Full cycle: apply manifests + build images + wait for rollout + schema setup |
| `apply` | Apply Kubernetes manifests only (no build) |
| `build-api` | Trigger API image build (rolls API + both workers via ImageStream trigger) |
| `build-frontend` | Trigger frontend image build |

ImageStream change triggers automatically roll deployments when a new image is pushed — no manual restart needed.
