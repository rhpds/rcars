# Portfolio Architecture Ingest — Design Spec

**Jira:** [RHDPCD-28](https://redhat.atlassian.net/browse/RHDPCD-28) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Date:** 2026-07-30 (revised 2026-08-07, 2026-08-10)
**Status:** Design
**Author:** M. Rudisill
**Depends on:** RHDPCD-359 (Generalized Content Model — deployed)

## Problem

RCARS can only recommend Babylon Showroom content. Red Hat's Architecture Center publishes ~70 curated assets — reference architectures and demos — that cover the same products and use cases that RHDP labs cover, but are not hands-on environments. Sales teams and learners who need a conceptual overview rather than a provisioned lab get nothing from RCARS today.

These assets come from OSSPA GitLab, are public, and have rich AsciiDoc content. The generalized content model (RHDPCD-359) deliberately left room for exactly this source: `portfolio_architectures` and `architecture_analysis` tables were planned as part of 359's design but never created — this spec creates them.

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

Advisor and Browse default to `status='live'`. A curator-only "Show non-live" toggle exposes `in_progress` and `draft` items, mirroring the existing "Show Retired" pattern. **This filter is a Phase 1 deliverable, not deferred:** the shared candidate-retrieval query used by Advisor's vector search and by the Browse API applies `(source != 'portfolio_arch' OR status = 'live')` in Phase 1, before any dedicated architecture UI exists — see 3i. Without it, `in_progress`/`draft` items would leak into recommendations and Browse results via vector search the moment embeddings exist, regardless of whether a curator UI toggle has shipped.

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

This implements the table planned (but not created) by RHDPCD-359, extended with `show_in_catalog` and `status` to support the ingest-all + status-tagging model (see Ingestion Scope & Status Tagging). `status` is derived on each sync from the two raw CSV booleans and drives default Advisor/Browse visibility.


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


`content_hash`: SHA-256 of the **full** DetailPage adoc body (before any truncation for the LLM prompt) **plus the CSV fields that feed the LLM prompt** (`Summary`, `Product`, `Solutions`, `Vertical`, `metaKeyword`) — see 3h. The hash is computed from the complete source so edits past the `osspa_max_adoc_bytes` cap still trigger re-analysis. Because those metadata fields are analysis inputs, a change to any of them deterministically re-triggers analysis on the next sync without a manual `--force`. CSV fields that do *not* feed the prompt (e.g. `Image1Url`) still update the extension/card row on upsert but do not force re-analysis.

`stale_commit`: the HEAD SHA of the examples repo at the time the hash change was detected. Set when a re-analysis is triggered by a content change; cleared (set to NULL) when analysis succeeds. Same staleness pattern as `showroom_analysis`.

#### 2c. SCHEMA_SQL placement

Both tables go into `src/api/rcars/db/database.py` `SCHEMA_SQL` using `CREATE TABLE IF NOT EXISTS`. They are appended after the `overlap_candidates` block, before the reference tables (`workload_mapping`, `workload_aliases`). The Babylon tables are not affected.

#### 2d. content_entities card fields for OSSPA items

Populated on ingest from CSV **on first insert only**, then owned by analysis from that point on:


| Field           | Initial value (CSV, INSERT only)      | Owner after first analysis |
| --------------- | -------------------------------------- | -------------------------- |
| `display_name`  | CSV `Heading`                          | CSV `Heading` (updated every sync — CSV-owned, not LLM-owned) |
| `summary`       | CSV `Summary`                          | `analyze_architecture_item` — LLM summary |
| `products_json` | CSV `Product` (comma-split)            | `analyze_architecture_item` — LLM products |
| `topics_json`   | Derived from `Solutions` + `Vertical`  | `analyze_architecture_item` — LLM topics |
| `audience_json` | `["architect", "developer"]` default   | `analyze_architecture_item` — LLM audience |
| `difficulty`    | `null`                                 | `analyze_architecture_item` — LLM difficulty |

**`upsert_osspa_item` never updates `summary`, `products_json`, `topics_json`, `audience_json`, or `difficulty` on conflict.** These five columns are set once on `INSERT` as a pre-analysis seed and excluded from the `ON CONFLICT DO UPDATE` clause entirely — only `analyze_architecture_item` writes to them after that. This matters because `upsert_osspa_item` runs on *every* sync (CSV-only, no analysis), while analysis only reruns when `content_hash` changes; without the exclusion, a routine CSV-only sync would silently overwrite good LLM output with the stale CSV seed values, and the following hash-unchanged skip (3b step 7d) would leave it that way indefinitely. `upsert_babylon_catalog_item` in `src/api/rcars/db/database.py` (line 539) already applies this same insert-only pattern to `content_entities` for Babylon items — `upsert_osspa_item` follows the identical approach.




### 3. Ingest Pipeline



#### 3a. New service module: `src/api/rcars/services/osspa_sync.py`


| Function                                                                          | Responsibility                                                                                             |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `fetch_palist_csv(settings) -> list[dict]`                                        | HTTP GET PAList.csv, parse, normalize booleans                                                             |
| `scope_rows(rows) -> list[dict]`                                                  | Apply ingestion gate — any `ProductType` token ∈ {PA, VP, SP} (no IE token) AND `.adoc` DetailPage. Not a live/catalog filter |
| `derive_status(row) -> str`                                                       | Map raw `islive` + `showInCatalog` → `live` / `in_progress` / `draft`                                      |
| `upsert_osspa_item(db, row) -> str`                                               | Write `content_entities` (card fields **except** `summary`/`products_json`/`topics_json`/`audience_json`/`difficulty`, which are INSERT-only — see 2d) + `portfolio_architectures` (incl. derived `status`) for one CSV row. Always resets `retired_at = NULL, retirement_reason = NULL` on conflict, mirroring `upsert_babylon_catalog_item`. Returns `content_id` |
| `retire_missing_osspa(db, active_content_ids) -> int`                             | Soft-retire `source='portfolio_arch'` items not in the current in-scope set — only when completeness + shrink-guard checks pass (see 3h)  |
| `clone_examples_repo(settings) -> Path`                                           | Shallow clone or fetch portfolio-architecture-examples at configured ref; bounded timeout; must succeed before any DB writes this sync (see 3h). When reusing an existing checkout, reset to configured ref and clean untracked files to ensure a known-good state |
| `read_detail_adoc(clone_path, detail_page) -> tuple[str, str]`                    | Safe path join with canonical real-path containment check; verify file is tracked at recorded HEAD (`git ls-tree`); read **full** `.adoc` text and compute `content_hash` from it; then truncate to `osspa_max_adoc_bytes` for the LLM prompt copy; strip `++++` passthrough blocks from the prompt copy; return `(full_text_for_hash, prompt_text)` (see 3h) |
| `analyze_architecture_item(db, content_id, adoc_text, csv_row, settings) -> dict` | Sets `is_stale=TRUE` before analysis → LLM → write `architecture_analysis` + denormalize to `content_entities` + generate embeddings → clears `is_stale` only after all three commit (see 3h) |
| `run_osspa_sync(ctx, job_id, force=False, confirm_empty_inventory=False) -> dict` | Orchestrator: acquire advisory lock → CSV → clone/validate → upsert → retire → analyze; return stats (see 3h). All blocking I/O (HTTP, git, DB, file reads, LLM calls) must run via `asyncio.to_thread()` since this executes on the shared arq scan worker event loop |




#### 3b. Orchestrator flow

```text
0. Acquire the osspa_sync advisory lock (`pg_try_advisory_lock(osspa_advisory_lock_id)`);
   if already held → exit early ("sync already running") — serializes nightly + manual runs (see 3h).
   Hold the lock connection for the entire sync; release in finally block
1. Fetch and parse PAList.csv (bounded by `osspa_csv_fetch_timeout_s`, see 3h)
2. Apply ingestion gate (scope_rows) → active_rows (all in-scope PA/PA,VP/SP with .adoc, any status)
3. Guard: if active_rows is empty →
       if confirm_empty_inventory is NOT set → abort sync (do not wipe existing items); log + return stats
       if confirm_empty_inventory IS set → proceed (operator has verified the inventory is genuinely empty);
           retire_missing_osspa in step 6 is then permitted to retire all source='portfolio_arch' rows
4. Ensure examples repo clone at configured ref (bounded by `osspa_clone_timeout_s`); record HEAD SHA.
   MUST succeed before any DB write below — a clone/fetch failure aborts the sync here,
   before upsert or retire, so existing rows are never mutated by a run that can't
   validate content (closes the "clone fails after DB already changed" gap — see 3h)
5. For each row → upsert_osspa_item:
       derive status (live / in_progress / draft) from islive + showInCatalog
       content_entities (ON CONFLICT DO UPDATE — card fields EXCEPT summary/products_json/
           topics_json/audience_json/difficulty, which are INSERT-only — see 2d;
           always resets retired_at = NULL, retirement_reason = NULL on conflict)
       portfolio_architectures (ON CONFLICT DO UPDATE — extension fields incl. status)
6. retire_missing_osspa: only if completeness is established — HTTP 200, parseable header,
   AND (active_rows count is not a suspicious drop vs. the current DB's active
   source='portfolio_arch' count, i.e. within the shrink-guard threshold — see 3h)
   OR confirm_empty_inventory was set in step 3
   → soft-retire source='portfolio_arch' items with content_id NOT IN active content_ids
   → if completeness/shrink-guard fails: skip retirement, log a warning, continue to step 7
     with whatever upserted from this run (do not abort the whole sync)
7. For each active item needing analysis:
       a. Resolve DetailPage under clone root (safe join + real-path check).
          If the file is missing and no architecture_analysis row exists yet for this
          content_id, first create a minimal row (content_id, is_stale=TRUE) so
          staleness has somewhere to live — then **skip to the next item** (do not
          fall through to analysis without adoc text)
       b. Read full adoc text via read_detail_adoc: verify file is tracked at HEAD
          (git ls-tree), read full source, compute content_hash from the FULL body
          + prompt-input CSV fields, then produce a separate prompt copy truncated
          to osspa_max_adoc_bytes with ++++...++++ passthrough blocks stripped
       c. content_hash is from the full source (not the truncated prompt copy)
       d. If is_stale=FALSE AND hash unchanged AND embedding for this content_id already
          matches the current content_hash AND not force → skip (analysis is genuinely current)
       e. Else: set is_stale=TRUE first → LLM analyze → write architecture_analysis
              → denormalize summary/products/topics/audience/difficulty to content_entities
              → in ONE transaction: clear old embeddings for this content_id and
                store the new architecture embedding (embed_type='summary') from
                summary + detailed topics — atomic swap (see 3h); no per-section embeddings
              → clear is_stale (set FALSE) and clear stale_commit ONLY after that
                transaction commits successfully; a failure at any point (LLM error,
                denormalization, embedding write) leaves is_stale=TRUE so the next
                sync retries this item instead of treating the stale hash as done
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
- Prefer precise product / solution / topic terms; when the shared controlled vocabulary ships ([2026-08-10-controlled-vocabulary-design.md](2026-08-10-controlled-vocabulary-design.md)), analysis will prefer listed terms and normalize aliases — but that wiring is **not** part of this Phase 1 deliverable
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

#### 3g. Controlled Vocabulary — deferred to separate spec

Cross-source term normalization (products, solutions, verticals, LO verbs, …) touches every analyzer, not just OSSPA. Per code-owner guidance (Nate, 2026-08-10), that work lives in its own design spec and must not be munged into this ingest feature:

→ **[2026-08-10-controlled-vocabulary-design.md](2026-08-10-controlled-vocabulary-design.md)**

OSSPA Phase 1 analysis lands free-text (structured JSON) and picks up normalization on the next re-analysis once the vocabulary ships — or lands already normalized if vocabulary ships first. Either order is fine; the two are independently deployable. A draft `src/api/rcars/data/vocabulary.yaml` may already exist in-tree as seed data for that separate work; this ingest spec does not own, mount, or wire it.

#### 3h. Robustness & Safety

Hardening for untrusted input (public GitLab repos, LLM output) and concurrent runs. Each item closes a specific failure mode raised in review; the inline references above (path resolution, `content_hash`, orchestrator flow) point here.

1. **Path canonicalization & symlink containment.** Beyond rejecting `..` and absolute paths, resolve the joined DetailPage to its real path and confirm it is still under the clone root before reading. This blocks symlinks committed inside the repo that point outside the clone. A path that escapes → skip the row, log a warning.

2. **Freshness hash includes CSV metadata, and staleness is tied to embedding completion, not just the hash.** `content_hash` covers the adoc body **plus** the CSV fields that feed the prompt (`Summary`, `Product`, `Solutions`, `Vertical`, `metaKeyword`), so a metadata-only edit re-triggers analysis deterministically. But an unchanged hash is only trusted if the item is also **not** `is_stale`: `analyze_architecture_item` sets `is_stale=TRUE` *before* starting analysis and clears it only after analysis, `content_entities` denormalization, and the embedding swap have all committed (3b step 7e). The hash-unchanged skip (3b step 7d) additionally requires `is_stale=FALSE`. This closes the gap where an LLM call or embedding write fails mid-way: without this, the `content_hash` column could already reflect the new content while the embedding still reflects the old (or no) content, and the next sync would see "hash unchanged" and skip forever, permanently losing that item from vector search. If a DetailPage file goes missing and no `architecture_analysis` row exists yet, one is created with `is_stale=TRUE` so this mechanism has a row to track (3b step 7a).

3. **Bounded fetch, clone, and file size — validated before any DB write.** All external I/O is bounded: the CSV fetch runs under `osspa_csv_fetch_timeout_s`; the git clone/fetch runs under `osspa_clone_timeout_s` (separate timeout because shallow clone may be slow from OpenShift pods); the adoc read is capped at `osspa_max_adoc_bytes`. An adoc over the cap → truncate to the cap for analysis and flag `enrichment_review_needed`. The examples-repo clone (step 4 in 3b) now runs, and must succeed, **before** `upsert_osspa_item` or `retire_missing_osspa` run — a fetch/clone over its timeout aborts the sync at that point, so existing rows are provably untouched, not just "probably fine because nothing else changed yet." Prevents a hostile or runaway input from stalling the shared scan worker, and prevents a partial sync (cards written, clone failed) from leaving the catalog in a half-updated state.

4. **Catalog completeness and a row-count shrink guard, before retire.** `retire_missing_osspa` runs only after: HTTP 200 + a parseable header row (existing checks), **and** a shrink guard — the new active-row count must not fall below `osspa_retire_shrink_guard_pct` (default 50%) of the current count of non-retired `source='portfolio_arch'` rows already in the database. HTTP 200 and a parseable header prove the request succeeded, not that the *body* is complete — a connection that drops mid-stream can still deliver a syntactically valid, non-empty, truncated CSV. The shrink guard catches that case: a truncation big enough to drop real rows will also produce a suspicious drop in row count relative to what's already in the DB, which HTTP status and header parsing cannot detect. **Note:** a truncated response that retains >50% of rows would pass the shrink guard and retire the omitted items — the 50% threshold is a safety net, not a completeness proof. If higher confidence is needed, the implementation should also compare the HTTP `Content-Length` header (when present) against bytes received, or use `Transfer-Encoding: chunked` terminal markers to detect incomplete transfers. If either check fails, retirement is skipped and logged as a completeness/shrink-guard failure; upserts from whatever parsed still proceed. The empty-active-set guard (step 3 in 3b) is the zero-row edge case of the same problem: retiring *everything* is never automatic. An operator who has independently verified the OSSPA inventory is genuinely empty must pass `--confirm-empty-inventory` to `rcars osspa sync` (or the equivalent admin request param) to allow `retire_missing_osspa` to retire all `source='portfolio_arch'` rows in one run.

5. **Atomic embedding swap.** The clear-old + write-new embedding sequence for an item runs in **one transaction**, so a crash mid-write can never leave an item with zero or partial vectors (which would silently drop it from vector search). The prior vectors remain until the new set commits. This transaction is also the one whose successful commit clears `is_stale` (item 2, above).

6. **Untrusted input in the prompt.** Both the adoc body and CSV metadata come from public repos and are treated as untrusted. The prompt frames them as data to analyze, not instructions to follow, and the output is validated by `parse_analysis_response()` against the expected JSON shape. Content attempting to steer the model ("ignore previous instructions…") cannot alter control flow — the worst case is a low-quality analysis, caught by curator review.

7. **Advisory lock serializes sync.** `run_osspa_sync` acquires a Postgres session-level advisory lock (`pg_try_advisory_lock(osspa_advisory_lock_id)`) at start. The connection that holds the lock must remain checked out from the pool for the entire sync — returning it would allow another sync to reuse the same session and reentrantly acquire the lock. Release with `pg_advisory_unlock` in a `finally` block (including cancellation). If the lock is already held, the second run exits early with a "sync already running" status.

8. **CSV-to-clone race window.** The CSV is fetched (step 1) before the examples repo is cloned (step 4). If the examples repo is updated between those two operations, a newly-referenced `DetailPage` might not exist in the clone yet. This is a known, accepted race: the missing-file handling (step 7a — mark `is_stale=TRUE`) covers it, and the next nightly sync picks it up. The window is small (seconds between the two fetches) and self-healing.

9. **URL override for Architecture Center links.** The detail URL is derived at display time from `pa_name` (`https://www.redhat.com/architect/portfolio/detail/{pa_name}/`). If Red Hat restructures the Architecture Center URL scheme, add a `url_override TEXT` column to `portfolio_architectures` (same pattern as `showroom_url_override` on `babylon_items`) and prefer it when set. Not required for Phase 1 — the current URL pattern has been stable — but the escape hatch is documented here.

10. **LLM-owned card fields survive routine CSV syncs.** `upsert_osspa_item` excludes `summary`, `products_json`, `topics_json`, `audience_json`, and `difficulty` from its `ON CONFLICT DO UPDATE` clause (2d) — they are seeded on `INSERT` only and owned by `analyze_architecture_item` afterward. Without this, the CSV-only upsert that runs on every sync would overwrite good LLM analysis with the CSV seed on the very next sync, and the hash-unchanged skip (item 2, above) would prevent analysis from ever restoring it. `upsert_osspa_item` also always resets `retired_at = NULL, retirement_reason = NULL` on conflict, so a row that reappears in the CSV after being retired is correctly un-retired on the next sync — matching the Lifecycle table (Section 6) and `upsert_babylon_catalog_item`'s existing behavior for Babylon.

#### 3i. Default visibility filter (Phase 1, not deferred)

Advisor/Browse **UI** for architecture content (cards, content-type filter chips, CTA/detail links) is deferred to a future spec (see Out of Scope). That is a rendering concern, not a data-safety one — until it ships, non-`live` OSSPA rows must still be prevented from surfacing through the *existing* Advisor retrieval and Browse API paths, because embeddings for `in_progress`/`draft` items exist the moment analysis runs (3e) and are visible to any vector-search query regardless of UI support.

To close that gap without waiting on the UI work, the shared candidate-retrieval query paths add one filter clause in Phase 1:

```sql
-- Applied by: Advisor vector-search candidate query, Browse default (non-curator) query
WHERE retired_at IS NULL
  AND (source != 'portfolio_arch' OR status = 'live')
```

- Curator-facing queries (Browse "Show non-live" toggle, admin/curation endpoints) omit the `status = 'live'` clause, mirroring the existing "Show Retired" pattern.
- This is a query-clause change to existing shared retrieval code, not new UI. It ships in Phase 1 alongside ingest so the Phase 1 visibility guarantee (Ingestion Scope & Status Tagging) is actually enforced by a consumer, not just asserted.
- Babylon rows are unaffected — the `source != 'portfolio_arch'` branch is a no-op for them.

**Specific integration points** that need this filter:

1. **`search_embeddings`** (`database.py`, `Database.search_embeddings`) — the vector search candidate query. Currently filters on `retired_at IS NULL` plus Babylon-specific `stage` and ZT-namespace filters. Add the `status = 'live'` clause for `source='portfolio_arch'` here. Note: this function is accumulating per-source filter logic; a future refactor should consider a single `is_searchable` flag on `content_entities` maintained by each source's sync.

2. **`list_content_entities_filtered`** (`database.py`, `Database.list_content_entities_filtered`) — the Browse API query. This function LEFT JOINs `babylon_items` and has Babylon-centric stage logic (`bi.stage = 'prod' OR bi.content_id IS NULL` at line 781). OSSPA items have no `babylon_items` row, so they fall through the `bi.content_id IS NULL` branch and appear in Browse results with no status filtering. The `status = 'live'` clause must be added here too.

3. **`_format_single_candidate`** (`services/recommender/rationale.py`) — the rationale formatter. Currently handles `lab`/`demo` and `sandbox` content types only. `live` OSSPA items WILL reach this function via vector search in Phase 1. Without an `architecture` branch, they get bare-minimum formatting (no solution areas, use cases, or key components context). **Phase 1 must add a minimal `architecture` branch** that formats the available fields — this is not a UI concern; it's a data-quality concern for the rationale prompt.

### 4. Worker Integration

**Queue:** `arq:queue:scan` (same as Babylon scan worker — reuses existing scan worker process)

**Job type:** `osspa_sync`

**Entry points:**


| Entry                           | Details                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| Nightly maintenance pipeline    | New step in `run_nightly_pipeline` (`src/api/rcars/workers/ops.py`) after Step 1 (catalog refresh), before Step 2 (stale check); never passes `confirm_empty_inventory` |
| `POST /api/v1/admin/sync-osspa` | Admin-only endpoint; enqueues job; accepts optional `confirm_empty_inventory: bool`; returns `{job_id}` |
| `rcars osspa sync [--force] [--confirm-empty-inventory]` | CLI command; synchronous; `--force` bypasses hash check; `--confirm-empty-inventory` permits retiring all items when the CSV has zero in-scope rows (see 3h) |


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
| `osspa_csv_fetch_timeout_s` | `15`                                                        | Timeout for CSV HTTP fetch (see 3h) |
| `osspa_clone_timeout_s`   | `60`                                                          | Timeout for git clone/fetch (see 3h); separate from CSV fetch because shallow clone of the examples repo may be slow from OpenShift pods |
| `osspa_max_adoc_bytes`    | `1000000`                                                     | Max adoc bytes read for analysis; larger is truncated + flagged (see 3h) |
| `osspa_retire_shrink_guard_pct` | `0.5`                                                    | Minimum fraction of the current DB's active `source='portfolio_arch'` row count that the new active set must retain before `retire_missing_osspa` is allowed to run (see 3h) |
| `osspa_advisory_lock_id`  | `736372`                                                      | Postgres advisory lock ID for sync serialization (see 3h); chosen to avoid collision with other RCARS locks |

No auth tokens required — both repos are public (HTTPS clone is intentional — these are GitLab repos, not GitHub, and public access does not require SSH). If GitLab rate-limits the clone, an optional `RCARS_GITLAB_TOKEN` can be wired later.

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
| Previously retired row reappears in CSV                  | `upsert_osspa_item` always clears `retired_at`/`retirement_reason` on conflict (3a/3h#8) — upserted with `retired_at = NULL` on next sync; `status` re-derived; treated as new |




### 7. Failure and Edge Cases


| Case                                          | Behavior                                                                                                                                      |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| CSV fetch fails                               | Abort sync; leave existing OSSPA rows intact; job fails                                                                                       |
| Active set is empty after filtering, no `--confirm-empty-inventory` | Abort sync (safety guard — never wipe all items on a bad CSV); no upserts, no retirements                             |
| Active set is empty after filtering, `--confirm-empty-inventory` set | Proceed; `retire_missing_osspa` retires all `source='portfolio_arch'` rows (operator-confirmed empty inventory)       |
| Active set shrinks below `osspa_retire_shrink_guard_pct` of current DB count (but is non-empty) | Upserts proceed for whatever parsed; retirement skipped and logged as a possible truncation (see 3h#4) |
| Examples repo clone/fetch fails or times out  | Abort sync **before any upsert or retire runs**; leave existing OSSPA rows intact; job fails (see 3h#3)                                       |
| DetailPage file missing from clone, analysis row exists | Mark `is_stale=TRUE` on the existing `architecture_analysis` row; log error; **skip to next item** (do not attempt analysis without adoc text) |
| DetailPage file missing from clone, no analysis row yet | Create a minimal `architecture_analysis` row (`content_id`, `is_stale=TRUE`); log error; **skip to next item** (see 3b step 7a)    |
| LLM analysis fails                            | Row stays `is_stale=TRUE` (never cleared); same error patterns as Showroom scan failure; scan_status not set (architecture_analysis has no scan_status — log error, skip item, continue); retried on next sync |
| Denormalization or embedding write fails after a successful LLM call | Transaction rolls back; `architecture_analysis` row and `is_stale` are unaffected by the failed write — `is_stale` stays TRUE from step 7e, retried on next sync |
| `ProductType=PA,VP`                           | Maps to `architecture`; `pa_name` slug uses full PAName                                                                                       |
| `Product` column empty for a row              | `products_json` seeded empty on INSERT only; LLM fills from adoc + other CSV fields; never reset by a later CSV-only sync (2d)               |
| Duplicate `ppid` in CSV                       | Should not happen; log warning; last row wins                                                                                                 |
| Path traversal / symlink escape in DetailPage | Real path resolves outside clone root → skip row; log warning (see 3h)                                                                        |
| adoc exceeds `osspa_max_adoc_bytes`           | Truncate to the cap for analysis; flag `enrichment_review_needed`; continue (see 3h)                                                          |
| CSV fetch incomplete / malformed header       | Completeness guard fails → retirement skipped; upsert whatever parsed; log (see 3h#4)                                                         |
| Prompt-injection text in adoc/CSV             | Treated as untrusted data, not instructions; output schema-validated; worst case a low-quality analysis flagged for review (see 3h)           |
| Concurrent sync (nightly + manual)            | Second run exits early — advisory lock already held (see 3h)                                                                                  |
| Crash mid embedding write                     | Atomic swap → prior vectors intact; item never left with zero/partial embeddings; `is_stale` stays TRUE, retried next sync (see 3h)           |
| Non-`live` item's embedding exists but item hasn't shipped in UI yet | Excluded from Advisor/Browse default results by the 3i status filter regardless — not dependent on UI existing |




### 8. Testing


| Test                                                                 | Type        | Assertion                                              |
| -------------------------------------------------------------------- | ----------- | ------------------------------------------------------ |
| Ingestion gate: `Demo` and `IE` excluded                             | Unit        | Row not in active set                                  |
| Ingestion gate: `DetailPage` without `.adoc` excluded                | Unit        | Row not in active set                                  |
| Ingestion gate: in-scope row is ingested regardless of live status   | Unit        | `showInCatalog=FALSE` / `islive=FALSE` row still in active set |
| Status derivation: live / in_progress / draft                        | Unit        | Both TRUE → `live`; one TRUE → `in_progress`; neither → `draft` |
| Default visibility: non-`live` items excluded from default queries (see 3i) | Integration | `in_progress`/`draft` items absent from Advisor + Browse default queries unless "Show non-live" set |
| `content_id` format: `pa:{ppid}`                                     | Unit        | Correct for PA, PA,VP, and SP rows                     |
| Asset-type mapping: PA/PA,VP/SP → `architecture`; Demo/IE excluded   | Unit        | Only the three architecture types in active set        |
| Path resolution: root, nested                                        | Unit        | Correct path; traversal rejected                       |
| Upsert: writes both `content_entities` and `portfolio_architectures` | Integration | Both rows exist after sync                             |
| Soft-retire: OSSPA item missing from next sync                       | Integration | `retired_at` set                                       |
| Babylon safety: Babylon CRD scan does not retire OSSPA items         | Integration | OSSPA row survives Babylon scan run                    |
| Analysis: produces exactly one architecture embedding                | Integration | one `embeddings` row, `embed_type='summary'`; no `section` rows |
| Empty active set guard                                               | Unit        | Sync aborts; no retirements                            |
| Empty active set with `--confirm-empty-inventory`                    | Integration | All `source='portfolio_arch'` rows retired              |
| Shrink guard: active set drops >50% but is non-empty                 | Integration | Retirement skipped and logged; upserts still applied   |
| Path safety: symlink escaping clone root rejected                    | Unit        | Row skipped; nothing read outside clone root           |
| Freshness: CSV prompt-field change re-triggers analysis              | Unit        | `content_hash` changes when `Summary`/`Solutions` edited |
| Freshness: edit past osspa_max_adoc_bytes still triggers re-analysis | Unit        | `content_hash` computed from full source, not truncated prompt copy |
| Checkout: untracked file in clone root is not read                   | Unit        | File not in `git ls-tree HEAD` → row skipped             |
| Freshness: failed embedding write leaves item stale                  | Integration | `is_stale` stays TRUE after a simulated embedding-write failure; next sync retries instead of skipping on unchanged hash |
| Freshness: missing DetailPage with no prior analysis row             | Integration | Minimal `architecture_analysis` row created with `is_stale=TRUE` |
| Completeness guard: malformed/partial CSV does not retire            | Integration | No retirements when CSV fetch incomplete               |
| LLM-owned fields survive a CSV-only resync                           | Integration | `summary`/`products_json`/`topics_json`/`audience_json`/`difficulty` unchanged after a sync where only CSV fields changed and content_hash was unaffected |
| Clone failure aborts before any DB write                             | Integration | No upserts or retirements committed when the examples-repo clone times out |
| Atomic embeddings: crash mid-swap leaves prior vectors               | Integration | Item never left with zero embeddings                   |
| Concurrency: second concurrent sync exits early                     | Integration | Advisory lock prevents overlapping runs                |
| Retrieval: OSSPA item returned by vector search for matching query   | Integration | Candidate has `source='portfolio_arch'`                |
| Retrieval: non-`live` OSSPA item excluded from Advisor default candidates (see 3i) | Integration | `in_progress`/`draft` item embeddings exist but are filtered from the default candidate query |




### 9. Out of Scope (Phase 1)

- **Demo ingest** — `ProductType=Demo` items (~30 rows) are excluded from Phase 1. These may be migrating off OSSPA into Interact Hub; if they remain, they can be introduced in a later phase.
- **Interactive Experience ingest** — IE items (`ProductType=IE`) are excluded from Phase 1 entirely. The one IE in `showInCatalog=TRUE` (`ppid=64`) is not ingested. IE content requires a different analysis approach (Arcade embeds, thin adoc) and is a future spec.
- **Retirement scoring** — RHDP reporting is Babylon-keyed; OSSPA items do not get performance scores in Phase 1.
- **Workload / infrastructure facets** — not applicable to non-hands-on content.
- **Diagram image OCR** — image URLs stored but not analyzed.
- **Writing back to OSSPA GitLab** — read-only.
- **Interactive Labs performance channel** — separate spec.
- **Dedicated model selection** — Phase 1 reuses the existing Showroom-analysis model. Choosing a dedicated architecture-analysis model (frontier now vs. open-source later, with cost/quality trade-offs) needs a team discussion — including Ashok on open-source options — before a `pa_model`-style config lever is added. Deferred to Phase 2.
- **Advisor & Browse UI** — surfacing architecture items in the Advisor rationale flow and dedicated Browse UI (content-type filter, architecture cards, CTA/detail links, curator-control handling) is deferred to a future spec. Phase 1 ends at ingest: items land in `content_entities` + `embeddings` and are retrievable by vector search, but the consuming UI work ships separately. **Not deferred:** the default-visibility query filter (3i) that keeps non-`live` items out of Advisor recommendations and default Browse results — that's a small change to existing shared retrieval code, and ships in Phase 1 so the status-visibility contract in Ingestion Scope & Status Tagging is actually enforced.
- **Full Browse UI for architecture content type** — Phase 2, ships alongside actual items.
- **Controlled vocabulary** — shared analysis-time term normalization across all sources. Owned by [2026-08-10-controlled-vocabulary-design.md](2026-08-10-controlled-vocabulary-design.md); not a Phase 1 deliverable of this ingest (see 3g).



## Relationship to Other Specs

- **RHDPCD-359 (Generalized Content Model)** — prerequisite; deployed. This spec creates the tables that 359 planned but did not create.
- **Controlled vocabulary** — [2026-08-10-controlled-vocabulary-design.md](2026-08-10-controlled-vocabulary-design.md). Cross-cutting; ships independently. This ingest consumes it when available and does not block on it.
- **Overlap analysis redesign** — `overlap_candidates` pairs between Babylon and OSSPA will populate automatically once embeddings exist via `generate_overlap_candidates` (`src/api/rcars/db/overlap.py`). No overlap spec changes needed.
- **Interactive Experience ingest** — future spec. Phase 1 excludes all `ProductType=IE` rows.
- **Browse/Advisor UI redesign** — Phase 2; architecture content type cards and filters ship alongside new content types.



## Next Steps

1. **Review and approve this spec** — share with the team; confirm scope (PA/PA,VP/SP only; Demo & IE deferred; ingest-all with `live`/`in_progress`/`draft` status tagging) and the two new tables (`portfolio_architectures`, `architecture_analysis`) are acceptable before implementation begins.
2. **Write implementation plan** — once approved, create a step-by-step implementation plan (`docs/superpowers/plans/`) that breaks this spec into ordered, independently-testable tasks. Key tasks will include: schema additions, `osspa_sync.py` service, LLM prompt, worker/CLI/API wiring, and the Babylon safety fix. (Advisor & Browse integration is deferred to a future spec — see Out of Scope.)
3. **Verify Babylon retirement safety** — before writing any new code, confirm that the existing Babylon retire query (`retire_removed_items()`, to be renamed `retire_missing_babylon()`) already filters by `source='babylon'`. If not, that fix ships first as it is a data-safety prerequisite. Fold the rename into the same change.
4. **Pilot sync on dev** — after implementation, run `rcars osspa sync` on the dev environment against the live CSV and examples repo. Spot-check 3–5 analyzed items (one PA, one SP, one PA,VP) for summary quality and vector-search retrievability before enabling the nightly pipeline step.
5. **Phase 2 — Interactive Experience ingest** — separate spec and implementation cycle after Phase 1 is stable.

