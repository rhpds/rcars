# Portfolio Architecture Ingest — Design Spec

**Jira:** [RHDPCD-28](https://redhat.atlassian.net/browse/RHDPCD-28) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Date:** 2026-07-30 (revised 2026-08-07)
**Status:** Design
**Author:** M. Rudisill
**Depends on:** RHDPCD-359 (Generalized Content Model — deployed)

## Problem

RCARS can only recommend Babylon Showroom content. Red Hat's Architecture Center publishes ~70 curated assets — reference architectures and demos — that cover the same products and use cases that RHDP labs cover, but are not hands-on environments. Sales teams and learners who need a conceptual overview rather than a provisioned lab get nothing from RCARS today.

These assets come from OSSPA GitLab, are public, and have rich AsciiDoc content. The generalized content model (RHDPCD-359) deliberately left room for exactly this source: `portfolio_architectures` and `architecture_analysis` tables are defined as illustrative placeholders, ready to be created by this spec.

## Approach

Ingest **all** Portfolio Architecture assets — `PA`, `PA,VP`, and `SP` — that have a readable `.adoc`, regardless of live/catalog status. These three asset types all map to `content_type = architecture`. Demos and Interactive Experiences are **out of scope for Phase 1** (see Scope & Asset Types). Each item is tagged with a lifecycle status (`live` / `in_progress` / `draft`) derived from the CSV, so curators can see in-progress and unpublished work in RCARS while Advisor and Browse surface only `live` items by default. Each item gets a row in `content_entities` (the universal card), a row in `portfolio_architectures` (OSSPA-specific metadata), and after LLM analysis a row in `architecture_analysis`. Embeddings land in the shared `embeddings` table, making these items immediately searchable alongside Babylon labs.

The Babylon ingest pipeline is the pattern to follow: upsert the entity registry first, write source-specific extension fields second, run analysis third.

## Source Data

Two public GitLab repos — no auth required:


| Repo                                | URL                                                        | Purpose                                                                    |
| ----------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------- |
| **osspa-site**                      | `https://gitlab.com/osspa/osspa-site`                      | Inventory (`PAList.csv`) — what exists and whether it is live              |
| **portfolio-architecture-examples** | `https://gitlab.com/osspa/portfolio-architecture-examples` | Content — one `.adoc` file per item, referenced by `DetailPage` in the CSV |




### PAList.csv — relevant columns


| Column                     | Use                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------ |
| `ppid`                     | Numeric unique ID — becomes part of `content_id`                                           |
| `PAName`                   | Slug (e.g. `275-rhacs-multitenant`)                                                        |
| `Heading`                  | Display name → `content_entities.display_name`                                             |
| `islive`                   | Drives the `status` tag (not an ingest gate) — see Ingestion Scope                                               |
| `showInCatalog`            | Drives the `status` tag (not an ingest gate) — see Ingestion Scope                                         |
| `Summary`                  | Short description — seed for `content_entities.summary` before analysis                    |
| `metaDesc` / `metaKeyword` | Extra text for LLM prompt context                                                          |
| `Vertical`                 | Industry verticals → `portfolio_architectures.verticals`                                   |
| `Solutions`                | Solution areas → `portfolio_architectures.solutions`                                       |
| `Product`                  | Red Hat products mentioned → `content_entities.products_json` (initial)                    |
| `ProductType`              | **Asset type**, not a RH product — `PA`, `VP`/`PA,VP`, `SP`, `Demo`, `IE` → drives scope + `content_type` |
| `Image1Url`                | Relative image path under examples repo → `portfolio_architectures.image_url`              |
| `DetailPage`               | Relative `.adoc` path in examples repo — **required for inclusion**                        |
| `externalUrl`              | Not used — Phase 1 items have an empty `externalUrl`; the detail URL is derived from `PAName` |


Raw CSV URL: `https://gitlab.com/osspa/osspa-site/-/raw/main/src/app/ArchitectureList/PAList.csv`

### Ingestion Scope & Status Tagging

RCARS ingests **every** in-scope row that has a usable `.adoc` DetailPage — not just the live, catalog-visible ones. This gives curators a complete view of the Portfolio Architecture content, including in-progress and unpublished work, while keeping recommendations limited to published content. `islive` and `showInCatalog` no longer gate ingestion; they derive a per-row `status` tag, and Advisor/Browse filter on that tag by default.

**Ingestion gate** — what gets a row at all:

```text
split ProductType on ","  →  tokens
keep the row IF:
    any token ∈ {PA, VP, SP}          # it is an architecture asset
    AND no token == IE                # IE deferred, even in combination
    AND DetailPage is non-empty
    AND DetailPage ends with ".adoc"
```

The three architecture asset types — `PA`, `VP`, `SP` — are what we ingest, in any combination (e.g. `PA,VP`). A row is an architecture if it carries any of those types; it all maps to `content_type='architecture'`. Rows that are only `Demo` or `IE` are excluded from Phase 1 (see Scope & Asset Types).

**Status tag** — derived per row, drives default visibility:

| CSV state                                            | `status`      | Surfaced by default?      |
| ---------------------------------------------------- | ------------- | ------------------------- |
| `islive=TRUE` AND `showInCatalog=TRUE`               | `live`        | Yes — Advisor + Browse    |
| exactly one of `islive` / `showInCatalog` is `TRUE`  | `in_progress` | Curators only             |
| neither is `TRUE`                                    | `draft`       | Curators only             |

Advisor and Browse default to `status='live'`. A curator-only "Show non-live" toggle exposes `in_progress` and `draft` items, mirroring the existing "Show Retired" pattern.

As of 2026-07 there are ~39 in-scope rows with `showInCatalog=TRUE` (PA 34, PA,VP 3, SP 2); ingesting all in-scope rows with a valid `.adoc` also pulls in additional `in_progress` / `draft` items beyond those. Rows excluded from Phase 1 entirely:

- `ProductType=Demo` (~30 rows) — deferred; these may migrate off OSSPA to Interact Hub, or be introduced in a later phase
- `ProductType=IE` (e.g. `ppid=64`) — Interactive Experience, deferred to a future phase
- `ppid=144` — empty `DetailPage` (links out to redhat.com) → no `.adoc` to analyze

### Asset types

The CSV column is named `ProductType`, but its values are **asset types** — the kind of Architecture Center artifact — **not** Red Hat products. Phase 1 ingests the three architecture asset types:

| Asset type | Full name             | What it is                                                                       |
| ---------- | --------------------- | ------------------------------------------------------------------------------- |
| `PA`       | Portfolio Architecture | A curated reference architecture for a solution or use case                     |
| `VP`       | Validated Pattern      | A GitOps-deployable, tested reference architecture (appears as `PA,VP`)          |
| `SP`       | Solution Pattern       | A lighter-weight architectural pattern for a specific problem                    |

All three are read-through reference architectures, so they map to the single RCARS `content_type='architecture'`. `Demo` and `IE` are separate asset types, deferred (below).

### Asset type → content_type mapping


| Asset type      | `content_type` in RCARS     |
| --------------- | --------------------------- |
| `PA`            | `architecture`              |
| `VP` / `PA,VP`  | `architecture`              |
| `SP`            | `architecture`              |
| `Demo`          | **excluded — deferred**     |
| `IE`            | **excluded — deferred**     |
| anything else   | **excluded — not ingested** |


All Phase 1 OSSPA items are `is_hands_on = FALSE` — they are reference/read-through content, not provisioned environments.

> **Demo and IE are out of scope for Phase 1.** `Demo` items may be migrating off OSSPA into Interact Hub; if they stay, they can be introduced in a later phase. `IE` (Interactive Experience) needs a different metadata/analysis approach (Arcade embeds, thin adoc) and is also deferred. Phase 1 ingests only the three architecture asset types — `PA`, `PA,VP`, `SP` — all mapping to `content_type='architecture'`. The `source` field (`portfolio_arch` vs `babylon`) remains the authoritative disambiguator against Babylon content.



### DetailPage path resolution

The examples repo has a flat root plus one `IE/` subdirectory:


| DetailPage value                                        | Resolved location      |
| ------------------------------------------------------- | ---------------------- |
| `rhacs-multitenant.adoc`                                | repo root              |
| `mockup/cloud-sovereignty.adoc`                         | nested path under repo |
| `IE/omnicloud-as-a-service-interactive-experience.adoc` | `IE/` subdirectory     |


**Safety rules:** Reject any path containing `..` or starting with `/`. Normalize to forward slashes and join under the clone root, then **resolve the real path and confirm it is still under the clone root** — this blocks symlinks inside the repo that point outside the clone (see 3h). A path that escapes → skip the row, log a warning.

Clone URL: `https://gitlab.com/osspa/portfolio-architecture-examples.git`
Default ref: `main`

## Design



### 1. Identity and Naming

`content_id` for each item: `pa:{ppid}`

Examples (in scope — ingested):

- `pa:275` — Multitenant Setup for RHACS (PA), `status=live`
- `pa:273` — Open Sovereign AI Cloud with Red Hat and Netris (PA), `status=live`
- `pa:272` — `showInCatalog=FALSE` → ingested with `status=in_progress` (curators only, not surfaced by default)

Excluded examples (out of scope — not ingested):

- `ppid=274` — `ProductType=Demo`, deferred (may move to Interact Hub)
- `ppid=64` — `ProductType=IE`, deferred
- `ppid=144` — empty `DetailPage`, nothing to analyze

`source` is always `portfolio_arch`. This keeps OSSPA items isolated from Babylon lifecycle signals — the Babylon CRD scan never touches `source='portfolio_arch'` rows.

### 2. Schema



#### 2a. portfolio_architectures (new table)

```sql
CREATE TABLE IF NOT EXISTS portfolio_architectures (
    content_id          TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    ppid                INTEGER NOT NULL UNIQUE,
    pa_name             TEXT,
    verticals           TEXT[],
    solutions           TEXT[],
    detail_page         TEXT,
    image_url           TEXT,
    is_live             BOOLEAN DEFAULT FALSE,   -- raw CSV islive
    show_in_catalog     BOOLEAN DEFAULT FALSE,   -- raw CSV showInCatalog
    status              TEXT DEFAULT 'draft',    -- live | in_progress | draft (derived)
    last_manifest_sync  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pa_ppid ON portfolio_architectures(ppid);
CREATE INDEX IF NOT EXISTS idx_pa_status ON portfolio_architectures(status);
```

This extends the illustrative table from RHDPCD-359 with `show_in_catalog` and `status` to support the ingest-all + status-tagging model (see Ingestion Scope & Status Tagging). `status` is derived on each sync from the two raw CSV booleans and drives default Advisor/Browse visibility.


| Column               | Source                                                       | Notes                                     |
| -------------------- | ------------------------------------------------------------ | ----------------------------------------- |
| `content_id`         | `pa:{ppid}`                                                  | FK to content_entities                    |
| `ppid`               | CSV `ppid`                                                   | Numeric, globally unique in OSSPA         |
| `pa_name`            | CSV `PAName`                                                 | Slug for diagnostics                      |
| `verticals`          | CSV `Vertical` (comma-split)                                 | Industry verticals                        |
| `solutions`          | CSV `Solutions` (comma-split)                                | Solution areas                            |
| `detail_page`        | CSV `DetailPage`                                             | Relative adoc path in examples repo       |
| `image_url`          | CSV `Image1Url`                                              | Relative image path in examples repo      |
| `is_live`            | Raw CSV `islive`                                            | Stored for diagnostics + status derivation |
| `show_in_catalog`    | Raw CSV `showInCatalog`                                     | Stored for diagnostics + status derivation |
| `status`             | Derived: `live` / `in_progress` / `draft`                  | Drives default Advisor/Browse visibility; non-`live` items are stored, not retired |
| `last_manifest_sync` | Set on each sync                                            | When this row was last seen in the CSV     |




#### 2b. architecture_analysis (new table)

Shared analysis contract columns are **required** — they feed `content_entities` denormalization, triage, and embeddings. Architecture-specific columns extend it.

```sql
CREATE TABLE IF NOT EXISTS architecture_analysis (
    content_id                  TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,

    -- Shared contract (required — feeds triage, embeddings, content_entities denormalization)
    summary                     TEXT,
    products_json               JSONB,
    topics_json                 JSONB,
    audience_json               JSONB,
    difficulty                  TEXT,
    content_hash                TEXT,
    last_analyzed               TIMESTAMPTZ,
    is_stale                    BOOLEAN DEFAULT FALSE,
    stale_commit                TEXT,

    -- Architecture-specific
    solution_areas_json         JSONB,
    use_cases_json              JSONB,
    key_components_json         JSONB,
    detailed_topics_json        JSONB,
    product_type                TEXT,

    -- Curator
    enrichment_review_needed    BOOLEAN DEFAULT FALSE,
    review_reasons              JSONB,
    notes                       TEXT
);
```


| Column                | Purpose                                                                        |
| --------------------- | ------------------------------------------------------------------------------ |
| `solution_areas_json` | e.g. `["ApplicationPlatform", "ContainerManagement"]` from LLM + CSV Solutions |
| `use_cases_json`      | Short phrases extracted from adoc Use Case / Business Problem sections         |
| `key_components_json` | Products and tools mentioned in the adoc                                       |
| `detailed_topics_json`| Detailed, architecture-wide topics (technologies, integration points, design decisions) — richer than `topics_json`; enriches the single embedding |
| `product_type`        | Raw CSV asset type (`PA`, `VP`/`PA,VP`, `SP`) — stored for diagnostics          |


`content_hash`: SHA-256 of the DetailPage adoc body **plus the CSV fields that feed the LLM prompt** (`Summary`, `Product`, `Solutions`, `Vertical`, `metaKeyword`) — see 3h. Because those metadata fields are analysis inputs, a change to any of them deterministically re-triggers analysis on the next sync without a manual `--force`. CSV fields that do *not* feed the prompt (e.g. `Image1Url`) still update the extension/card row on upsert but do not force re-analysis.

`stale_commit`: the HEAD SHA of the examples repo at the time the hash change was detected. Set when a re-analysis is triggered by a content change; cleared (set to NULL) when analysis succeeds. Same staleness pattern as `showroom_analysis`.

#### 2c. SCHEMA_SQL placement

Both tables go into `src/api/rcars/db/database.py` `SCHEMA_SQL` using `CREATE TABLE IF NOT EXISTS`. They are appended after the `content_similarity` block, before operational tables. The Babylon tables are not affected.

#### 2d. content_entities card fields for OSSPA items

Populated on ingest from CSV (before analysis), then overwritten by analysis when it runs:


| Field           | Initial value (CSV)                   | After analysis |
| --------------- | ------------------------------------- | -------------- |
| `display_name`  | CSV `Heading`                         | Unchanged      |
| `summary`       | CSV `Summary`                         | LLM summary    |
| `products_json` | CSV `Product` (comma-split)           | LLM products   |
| `topics_json`   | Derived from `Solutions` + `Vertical` | LLM topics     |
| `audience_json` | `["architect", "developer"]` default  | LLM audience   |
| `difficulty`    | `null`                                | LLM difficulty |




### 3. Ingest Pipeline



#### 3a. New service module: `src/api/rcars/services/osspa_sync.py`


| Function                                                                          | Responsibility                                                                                             |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `fetch_palist_csv(settings) -> list[dict]`                                        | HTTP GET PAList.csv, parse, normalize booleans                                                             |
| `scope_rows(rows) -> list[dict]`                                                  | Apply ingestion gate — any `ProductType` token ∈ {PA, VP, SP} (no IE token) AND `.adoc` DetailPage. Not a live/catalog filter |
| `derive_status(row) -> str`                                                       | Map raw `islive` + `showInCatalog` → `live` / `in_progress` / `draft`                                      |
| `upsert_osspa_item(db, row) -> str`                                               | Write `content_entities` + `portfolio_architectures` (incl. derived `status`) for one CSV row; return `content_id` |
| `retire_missing_osspa(db, active_content_ids) -> int`                             | Soft-retire `source='portfolio_arch'` items not in the current in-scope set — only when the CSV fetch was complete (completeness guard, see 3h)  |
| `clone_examples_repo(settings) -> Path`                                           | Shallow clone or fetch portfolio-architecture-examples at configured ref                                   |
| `read_detail_adoc(clone_path, detail_page) -> str`                                | Safe path join with canonical real-path containment check; enforce size cap; read `.adoc` text; strip `++++` passthrough blocks (see 3h) |
| `analyze_architecture_item(db, content_id, adoc_text, csv_row, settings) -> dict` | Hash check → LLM → write `architecture_analysis` + denormalize to `content_entities` + generate embeddings |
| `run_osspa_sync(ctx, job_id, force=False) -> dict`                                | Orchestrator: acquire advisory lock → CSV → upsert → retire → clone → analyze; return stats (see 3h)       |




#### 3b. Orchestrator flow

```text
0. Acquire the osspa_sync advisory lock; if already held → exit early
   ("sync already running") — serializes nightly + manual runs (see 3h)
1. Fetch and parse PAList.csv (bounded timeout, see 3h)
2. Apply ingestion gate (scope_rows) → active_rows (all in-scope PA/PA,VP/SP with .adoc, any status)
3. Guard: if active_rows is empty → abort (do not wipe existing items)
4. For each row → upsert_osspa_item:
       derive status (live / in_progress / draft) from islive + showInCatalog
       content_entities (ON CONFLICT DO UPDATE — card fields)
       portfolio_architectures (ON CONFLICT DO UPDATE — extension fields incl. status)
5. retire_missing_osspa: only if the CSV fetch was complete (HTTP 200,
   parseable header, non-empty active set — completeness guard, see 3h)
   → soft-retire source='portfolio_arch' items with content_id NOT IN active content_ids
6. Ensure examples repo clone at configured ref (bounded timeout); record HEAD SHA
7. For each active item needing analysis:
       a. Resolve DetailPage under clone root (safe join + real-path check)
       b. Read adoc text (capped at max size); strip ++++...++++ passthrough blocks
       c. Compute content_hash (adoc body + prompt-input CSV fields)
       d. If hash unchanged AND architecture_analysis row exists AND not force → skip
       e. Else: LLM analyze → write architecture_analysis
              → denormalize summary/products/topics/audience/difficulty to content_entities
              → in ONE transaction: clear old embeddings for this content_id and
                store the new architecture embedding (embed_type='summary') from
                summary + detailed topics — atomic swap (see 3h); no per-section embeddings
8. Release advisory lock; return stats: upserted, retired, analyzed, skipped, failed
```



#### 3c. adoc reader

`read_detail_adoc` is **not** the Showroom reader. Key differences:

- Showroom uses Antora modules + `nav.adoc`; OSSPA uses a single flat `.adoc` per item
- Strip `++++` / `<!--ARCADE EMBED ... -->` HTML passthrough blocks — they add no text signal
- Keep all AsciiDoc section headings and prose
- Do not recurse; do not follow `include::` directives (not used in examples repo)



#### 3d. LLM analysis prompt

Reuse the structured JSON output format from Showroom analysis (same `parse_analysis_response()` helper). Phase 1 also reuses the **same analysis model** the Showroom analyzer already uses — a dedicated model for architecture analysis (frontier vs. open-source, cost trade-offs) is deferred to Phase 2 pending a team discussion (see Out of Scope). Adapt the prompt:

- Provide CSV metadata as context: `Summary`, `Product`, `Solutions`, `Vertical`, `metaKeyword` (untrusted input — framed as data, not instructions; see 3h)
- Provide adoc prose as content body
- Request: `summary`, `products`, `topics`, `detailed_topics`, `audience`, `difficulty`, `solution_areas`, `use_cases`, `key_components`
- Instruct the LLM to draw from both CSV metadata and adoc prose; prefer adoc for specifics
- Constrain `products`, `topics`, and `solution_areas` to the controlled vocabulary where a listed term fits; only coin a new term when nothing matches (see 3g)
- `detailed_topics` is a richer, architecture-wide list of the specific topics the doc covers (technologies, integration points, design decisions) — more detailed than the short `topics`, applicable to the **whole** architecture, not per section. It enriches the single embedding (see 3e)
- For thin content (an adoc with mostly diagrams/embeds and a short intro): the prompt must produce a useful summary from CSV metadata alone — the adoc intro may only be 2-3 sentences
- Do **not** request `modules` or `learning_objectives` — these are architecture docs, not labs

Prompt file: `src/api/rcars/prompts/architecture_analyze.txt`

#### 3e. Embeddings

One embedding per item — architecture-level, not per-section. Per-section
embeddings are **not** generated: searching or recommending an individual
section of a reference architecture has no clear use, and per-section vectors
add complexity and noise. Instead, the single embedding is enriched with the
LLM-generated **detailed topics** so it captures more of the architecture than
the summary alone.


| `embed_type` | `content_text`                                                    | When                              |
| ------------ | ---------------------------------------------------------------- | --------------------------------- |
| `summary`    | `"Reference architecture: {summary}\nTopics: {detailed_topics}"` | Always — drives Advisor retrieval |


All embeddings: `source='portfolio_arch'`, `content_type` from the mapping table in this spec.

The type prefix `"Reference architecture: "` places these in slightly different vector space from `"Hands-on lab: "` and `"Environment: "` prefixes used by Babylon items.

#### 3f. Babylon safety

The Babylon CRD scan retires rows that disappear from Babylon. This must only apply to `source='babylon'` rows. Confirm (and fix if needed) that the retirement query filters by source:

```sql
-- Only retire Babylon items based on CRD disappearance
WHERE source = 'babylon' AND content_id NOT IN (...)
```

As part of this work, **rename the existing Babylon helper `retire_removed_items()` → `retire_missing_babylon()`** so it reads as a matched pair with `retire_missing_osspa()` — each source owns a clearly named retire helper. OSSPA lifecycle is owned exclusively by `retire_missing_osspa()` in this service; Babylon lifecycle by `retire_missing_babylon()`.

#### 3g. Controlled Vocabulary

To keep `products`, `topics`, `solutions`, and learning-objective verbs consistent **across sources** — Babylon labs and OSSPA architectures alike — analysis draws from a shared, controlled vocabulary rather than emitting free text. This is net-new: today RCARS enforces almost no vocabulary at ingest (only `content_type` and `format_suitability` are constrained), so products/topics arrive as unnormalized LLM free-text. A shared vocabulary makes triage, Browse filtering, and cross-source similarity more reliable by collapsing near-duplicate terms (e.g. "RHACS" vs "Advanced Cluster Security").

**Storage.** A version-controlled YAML file is the source of truth, mounted as a k8s ConfigMap so ops can override it per environment without an image rebuild — mirroring the Publishing House [`configmap-validation-policy.yaml`](https://github.com/rhpds/rhdp-publishing-house/blob/main/central-api/k8s/configmap-validation-policy.yaml) pattern:

```text
src/api/rcars/prompts/vocabulary.yaml      # source of truth, PR-reviewed
   └─ mounted as a ConfigMap (Ansible)     # per-env override, no rebuild
```

```yaml
# vocabulary.yaml — source-agnostic; shared by all content analyzers.
# products/solutions/verticals carry {name, aliases} so near-duplicates and
# acronyms (RHACS, ApplicationPlatform, FSI, ...) normalize to one canonical
# term. Layout mirrors the Publishing House ph-validation-policy ConfigMap.
products:                                    # canonical Red Hat product names
  - {name: "Red Hat Advanced Cluster Security", aliases: [RHACS, ACS, StackRox]}
  - ...
solutions:                                   # high-level solution areas (OSSPA-anchored)
  - {name: "Application Platform", aliases: [ApplicationPlatform, ApplicationDevelopment]}
  - ...
verticals:                                   # industry verticals (OSSPA PAList Vertical)
  - {name: "Financial Services", aliases: [FSI]}
  - ...
platforms:  [On-Premise, AWS, Azure, Cloud, Edge]   # OSSPA-native deployment target
topics:     [gitops, service-mesh, observability, ...]   # BROAD only — LLM coins the specifics
audience:   ["platform engineers", developers, ...]      # roles (open-ended)
difficulty: [beginner, intermediate, advanced]           # closed set
action_verbs_valid:    [deploy, configure, integrate, ...]   # learning-objective verbs (Babylon labs)
action_verbs_rejected: [understand, learn, know, ...]        # non-measurable — flag/replace
```

`topics` is deliberately a **broad** guide, not an exhaustive taxonomy: the OSSPA `metaKeyword` column alone holds 186 near-unique keywords (e.g. "granite 3.2 8b instruct"), and codifying that granularity would blunt the model's own topic detection. The vocabulary normalizes the *stable* dimensions (products, solutions, verticals, LO verbs) and leaves fine-grained topics to the LLM.

**Loading.** A cached loader reads the file (or the ConfigMap mount path) once per process:

```python
# src/api/rcars/services/vocabulary.py
@lru_cache
def load_vocabulary() -> dict: ...   # {"solutions": [...], "products": [...], ...}
```

**Injection.** At analysis time the vocabulary lists are interpolated into the analysis prompt (both `architecture_analyze.txt` and the existing `analyze_showroom.txt`). The prompt instructs the model to prefer a listed term where one fits and only coin a new one when nothing matches. A post-analysis normalization pass — mirroring the existing `_sanitize_format_suitability` in `scan.py` — snaps obvious near-misses to their canonical form before write.

**Scope notes.**

- The vocabulary is deliberately **generic and source-agnostic** so Babylon and OSSPA converge on the same terms over time. `lo_verbs` applies to labs, not architectures (Phase 1 does not request learning objectives for OSSPA) — it lives in the shared file for Babylon's use.
- Phase 1 introduces the file, the loader, and injection into the **architecture** prompt. Wiring the same vocabulary into the Babylon analyzer is a low-risk follow-up, not a Phase 1 blocker.

#### 3h. Robustness & Safety

Hardening for untrusted input (public GitLab repos, LLM output) and concurrent runs. Each item closes a specific failure mode raised in review; the inline references above (path resolution, `content_hash`, orchestrator flow) point here.

1. **Path canonicalization & symlink containment.** Beyond rejecting `..` and absolute paths, resolve the joined DetailPage to its real path and confirm it is still under the clone root before reading. This blocks symlinks committed inside the repo that point outside the clone. A path that escapes → skip the row, log a warning.

2. **Freshness hash includes CSV metadata.** `content_hash` covers the adoc body **plus** the CSV fields that feed the prompt (`Summary`, `Product`, `Solutions`, `Vertical`, `metaKeyword`), so a metadata-only edit re-triggers analysis deterministically. Hashing the adoc body alone would silently miss those edits.

3. **Bounded fetch, clone, and file size.** All external I/O is bounded: the CSV fetch and git clone/fetch run under `osspa_fetch_timeout_s`; the adoc read is capped at `osspa_max_adoc_bytes`. An adoc over the cap → truncate to the cap for analysis and flag `enrichment_review_needed`; a fetch/clone over its timeout → abort the sync (existing rows intact). Prevents a hostile or runaway input from stalling the shared scan worker.

4. **Catalog completeness before retire.** `retire_missing_osspa` runs only after a **complete** CSV fetch — HTTP 200, a parseable header row, and a non-empty active set. The empty-active-set guard (step 3) covers the all-empty case; this extends it so a truncated or malformed CSV is never trusted as the authoritative active set and cannot mass-retire real items. If completeness is not established, retirement is skipped and logged while upserts from whatever parsed still proceed.

5. **Atomic embedding swap.** The clear-old + write-new embedding sequence for an item runs in **one transaction**, so a crash mid-write can never leave an item with zero or partial vectors (which would silently drop it from vector search). The prior vectors remain until the new set commits.

6. **Untrusted input in the prompt.** Both the adoc body and CSV metadata come from public repos and are treated as untrusted. The prompt frames them as data to analyze, not instructions to follow, and the output is validated by `parse_analysis_response()` against the expected JSON shape. Content attempting to steer the model ("ignore previous instructions…") cannot alter control flow — the worst case is a low-quality analysis, caught by curator review.

7. **Advisory lock serializes sync.** `run_osspa_sync` takes a Postgres advisory lock at start, so a manual `POST /admin/sync-osspa` and the nightly pipeline cannot run concurrently and clobber each other's upserts/retires. If the lock is already held, the second run exits early with a "sync already running" status.

### 4. Worker Integration

**Queue:** `arq:queue:scan` (same as Babylon scan worker — reuses existing scan worker process)

**Job type:** `osspa_sync`

**Entry points:**


| Entry                           | Details                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| Nightly maintenance pipeline    | New step in `run_maintenance_pipeline` after catalog refresh, before similarity recompute |
| `POST /api/v1/admin/sync-osspa` | Admin-only endpoint; enqueues job; returns `{job_id}`                                     |
| `rcars osspa sync [--force]`    | CLI command; synchronous; `--force` bypasses hash check                                   |


All three entry points funnel through `run_osspa_sync`, which is serialized by a Postgres advisory lock (see 3h) — a manual sync and the nightly pipeline cannot overlap.




### 5. Configuration

All settings in `src/api/rcars/config.py` using existing `RCARS_` prefix pattern:


| Setting                   | Default                                                        | Purpose                     |
| ------------------------- | -------------------------------------------------------------- | --------------------------- |
| `osspa_sync_enabled`      | `true`                                                         | Gates nightly pipeline step |
| `osspa_palist_url`        | PAList.csv raw URL                                             | Inventory source            |
| `osspa_examples_repo_url` | `https://gitlab.com/osspa/portfolio-architecture-examples.git` | Content repo                |
| `osspa_examples_ref`      | `main`                                                         | Git ref to clone/fetch      |
| `osspa_clone_dir`         | `{clone_dir}/osspa-examples`                                   | Working directory           |
| `osspa_fetch_timeout_s`   | `30`                                                          | Timeout for CSV fetch + git clone/fetch (see 3h) |
| `osspa_max_adoc_bytes`    | `1000000`                                                     | Max adoc bytes read for analysis; larger is truncated + flagged (see 3h) |
| `vocabulary_path`         | `prompts/vocabulary.yaml` (ConfigMap mount overrides)         | Controlled-vocabulary source (see 3g); shared across sources |


No auth tokens required — both repos are public. If GitLab rate-limits the clone, an optional `RCARS_GITLAB_TOKEN` can be wired later.

### 6. Lifecycle


| Event                                                    | Result                                                                              |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| New in-scope row appears                                 | Upserted on next sync; `status` derived; analysis runs                              |
| `islive` and/or `showInCatalog` flips FALSE              | `status` re-derived (`in_progress` or `draft`); item **stays ingested**, dropped from default Advisor/Browse — not retired |
| `islive` and `showInCatalog` both back to TRUE           | `status` re-derived to `live`; item surfaces again by default                       |
| Row removed from CSV entirely                            | Not in active set → `retire_missing_osspa` soft-retires it                          |
| Asset type changes to Demo/IE                            | No longer in scope → treated as removed → soft-retired                              |
| Content of DetailPage `.adoc` changes                    | `content_hash` mismatch → re-analyzed on next sync                                  |
| CSV prompt-input changes (Summary, Product, Solutions, Vertical, metaKeyword) | Included in `content_hash` → re-analysis triggered on next sync (see 3h)  |
| CSV non-prompt field changes (e.g. Image1Url)            | Card/extension row updated on upsert; re-analysis not forced                        |
| Previously retired row reappears in CSV                  | Upserted with `retired_at = NULL` on next sync; `status` re-derived; treated as new |




### 7. Failure and Edge Cases


| Case                                          | Behavior                                                                                                                                      |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| CSV fetch fails                               | Abort sync; leave existing OSSPA rows intact; job fails                                                                                       |
| Active set is empty after filtering           | Abort sync (safety guard — never wipe all items on a bad CSV)                                                                                 |
| DetailPage file missing from clone            | Upsert catalog row; mark `is_stale=TRUE` on analysis record; log error; continue                                                              |
| LLM analysis fails                            | Same error patterns as Showroom scan failure; scan_status not set (architecture_analysis has no scan_status — log error, skip item, continue) |
| `ProductType=PA,VP`                           | Maps to `architecture`; `pa_name` slug uses full PAName                                                                                       |
| `Product` column empty for a row              | `products_json` seeded empty; LLM fills from adoc + other CSV fields                                                                          |
| Duplicate `ppid` in CSV                       | Should not happen; log warning; last row wins                                                                                                 |
| Path traversal / symlink escape in DetailPage | Real path resolves outside clone root → skip row; log warning (see 3h)                                                                        |
| adoc exceeds `osspa_max_adoc_bytes`           | Truncate to the cap for analysis; flag `enrichment_review_needed`; continue (see 3h)                                                          |
| CSV fetch incomplete / malformed header       | Completeness guard fails → retirement skipped; upsert whatever parsed; log (see 3h)                                                           |
| Fetch or clone exceeds `osspa_fetch_timeout_s`| Abort sync; leave existing OSSPA rows intact; job fails                                                                                       |
| Prompt-injection text in adoc/CSV             | Treated as untrusted data, not instructions; output schema-validated; worst case a low-quality analysis flagged for review (see 3h)           |
| Concurrent sync (nightly + manual)            | Second run exits early — advisory lock already held (see 3h)                                                                                  |
| Crash mid embedding write                     | Atomic swap → prior vectors intact; item never left with zero/partial embeddings (see 3h)                                                     |




### 8. Testing


| Test                                                                 | Type        | Assertion                                              |
| -------------------------------------------------------------------- | ----------- | ------------------------------------------------------ |
| Ingestion gate: `Demo` and `IE` excluded                             | Unit        | Row not in active set                                  |
| Ingestion gate: `DetailPage` without `.adoc` excluded                | Unit        | Row not in active set                                  |
| Ingestion gate: in-scope row is ingested regardless of live status   | Unit        | `showInCatalog=FALSE` / `islive=FALSE` row still in active set |
| Status derivation: live / in_progress / draft                        | Unit        | Both TRUE → `live`; one TRUE → `in_progress`; neither → `draft` |
| Default visibility: non-`live` items excluded from default queries   | Integration | `in_progress`/`draft` items absent unless "Show non-live" set |
| `content_id` format: `pa:{ppid}`                                     | Unit        | Correct for PA, PA,VP, and SP rows                     |
| Asset-type mapping: PA/PA,VP/SP → `architecture`; Demo/IE excluded   | Unit        | Only the three architecture types in active set        |
| Path resolution: root, nested                                        | Unit        | Correct path; traversal rejected                       |
| Upsert: writes both `content_entities` and `portfolio_architectures` | Integration | Both rows exist after sync                             |
| Soft-retire: OSSPA item missing from next sync                       | Integration | `retired_at` set                                       |
| Babylon safety: Babylon CRD scan does not retire OSSPA items         | Integration | OSSPA row survives Babylon scan run                    |
| Analysis: produces exactly one architecture embedding                | Integration | one `embeddings` row, `embed_type='summary'`; no `section` rows |
| Empty active set guard                                               | Unit        | Sync aborts; no retirements                            |
| Vocabulary: analysis output normalized to canonical terms            | Unit        | Near-miss products/topics snapped to `vocabulary.yaml` terms |
| Path safety: symlink escaping clone root rejected                    | Unit        | Row skipped; nothing read outside clone root           |
| Freshness: CSV prompt-field change re-triggers analysis              | Unit        | `content_hash` changes when `Summary`/`Solutions` edited |
| Completeness guard: malformed/partial CSV does not retire            | Integration | No retirements when CSV fetch incomplete               |
| Atomic embeddings: crash mid-swap leaves prior vectors               | Integration | Item never left with zero embeddings                   |
| Concurrency: second concurrent sync exits early                     | Integration | Advisory lock prevents overlapping runs                |
| Retrieval: OSSPA item returned by vector search for matching query   | Integration | Candidate has `source='portfolio_arch'`                |




### 9. Out of Scope (Phase 1)

- **Demo ingest** — `ProductType=Demo` items (~30 rows) are excluded from Phase 1. These may be migrating off OSSPA into Interact Hub; if they remain, they can be introduced in a later phase.
- **Interactive Experience ingest** — IE items (`ProductType=IE`) are excluded from Phase 1 entirely. The one IE in `showInCatalog=TRUE` (`ppid=64`) is not ingested. IE content requires a different analysis approach (Arcade embeds, thin adoc) and is a future spec.
- **Retirement scoring** — RHDP reporting is Babylon-keyed; OSSPA items do not get performance scores in Phase 1.
- **Workload / infrastructure facets** — not applicable to non-hands-on content.
- **Diagram image OCR** — image URLs stored but not analyzed.
- **Writing back to OSSPA GitLab** — read-only.
- **Interactive Labs performance channel** — separate spec.
- **Dedicated model selection** — Phase 1 reuses the existing Showroom-analysis model. Choosing a dedicated architecture-analysis model (frontier now vs. open-source later, with cost/quality trade-offs) needs a team discussion — including Ashok on open-source options — before a `pa_model`-style config lever is added. Deferred to Phase 2.
- **Advisor & Browse integration** — surfacing architecture items in the Advisor rationale flow and the Browse UI (content-type filter, architecture cards, CTA/detail links, curator-control handling) is deferred to a future spec. Phase 1 ends at ingest: items land in `content_entities` + `embeddings` and are retrievable by vector search, but the consuming UI work ships separately.
- **Full Browse UI for architecture content type** — Phase 2, ships alongside actual items.



## Relationship to Other Specs

- **RHDPCD-359 (Generalized Content Model)** — prerequisite; deployed. This spec creates the tables that 359 left as illustrative placeholders.
- **Overlap analysis redesign** — `content_similarity` `related` pairs between Babylon and OSSPA will populate automatically once embeddings exist. No overlap spec changes needed.
- **Interactive Experience ingest** — future spec. Phase 1 excludes all `ProductType=IE` rows.
- **Browse/Advisor UI redesign** — Phase 2; architecture content type cards and filters ship alongside new content types.



## Next Steps

1. **Review and approve this spec** — share with the team; confirm scope (PA/PA,VP/SP only; Demo & IE deferred; ingest-all with `live`/`in_progress`/`draft` status tagging) and the two new tables (`portfolio_architectures`, `architecture_analysis`) are acceptable before implementation begins.
2. **Write implementation plan** — once approved, create a step-by-step implementation plan (`docs/superpowers/plans/`) that breaks this spec into ordered, independently-testable tasks. Key tasks will include: schema additions, `osspa_sync.py` service, LLM prompt, worker/CLI/API wiring, and the Babylon safety fix. (Advisor & Browse integration is deferred to a future spec — see Out of Scope.)
3. **Verify Babylon retirement safety** — before writing any new code, confirm that the existing Babylon retire query (`retire_removed_items()`, to be renamed `retire_missing_babylon()`) already filters by `source='babylon'`. If not, that fix ships first as it is a data-safety prerequisite. Fold the rename into the same change.
4. **Pilot sync on dev** — after implementation, run `rcars osspa sync` on the dev environment against the live CSV and examples repo. Spot-check 3–5 analyzed items (one PA, one SP, one PA,VP) for summary quality and vector-search retrievability before enabling the nightly pipeline step.
5. **Phase 2 — Interactive Experience ingest** — separate spec and implementation cycle after Phase 1 is stable.

