# Portfolio Architecture Ingest — Design Spec

**Jira:** [RHDPCD-28](https://redhat.atlassian.net/browse/RHDPCD-28) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Date:** 2026-07-30 (revised 2026-08-07, 2026-08-10, 2026-08-25)
**Status:** Design
**Author:** M. Rudisill
**Depends on:** RHDPCD-359 (Generalized Content Model — deployed)

## Problem

RCARS can only recommend Babylon Showroom content. Red Hat's Architecture Center publishes ~70 curated assets — portfolio architectures, validated patterns, solution patterns and demos — that cover the same products and use cases that RHDP labs cover, but are not hands-on environments. Sales teams and learners who need a conceptual overview rather than a provisioned lab get nothing from RCARS today.

These assets come from OSSPA GitLab, are public, and have rich AsciiDoc content. The generalized content model (RHDPCD-359) deliberately left room for exactly this source: `portfolio_architectures` and `architecture_analysis` tables were planned as part of 359's design but never created — this spec creates them.

## Approach

Ingest **all** Portfolio Architecture assets — `PA`, `PA,VP`, and `SP` — that have a readable `.adoc`, regardless of live/catalog status. These three asset types all map to `content_type = architecture`. Demos and Interactive Experiences are **out of scope for Phase 1** (see Scope & Asset Types). Each item is tagged with a lifecycle status (`prod` / `dev`) derived from the CSV using Babylon's status vocabulary, so curators can see in-progress and unpublished work in RCARS while Advisor and Browse surface only `prod` items by default. Each item gets a row in `content_entities` (the universal card), a row in `portfolio_architectures` (OSSPA-specific metadata), and after LLM analysis a row in `architecture_analysis`. Embeddings land in the shared `embeddings` table, making these items immediately searchable alongside Babylon labs.

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

**Status tag** — derived per row using Babylon's status vocabulary (`prod` / `dev`), drives default visibility:

| CSV state                                            | `status`  | Surfaced by default?      |
| ---------------------------------------------------- | --------- | ------------------------- |
| `islive=TRUE` AND `showInCatalog=TRUE`               | `prod`    | Yes — Advisor + Browse    |
| exactly one of `islive` / `showInCatalog` is `TRUE`  | `dev`     | Curators only             |
| neither is `TRUE`                                    | `dev`     | Curators only             |

Advisor and Browse default to `status='prod'`. A curator-only toggle exposes `dev` items, mirroring the existing "Show Retired" pattern. **This filter is a Phase 1 deliverable, not deferred:** the shared candidate-retrieval query used by Advisor's vector search and by the Browse API applies `status = 'prod'` in Phase 1, before any dedicated architecture UI exists — see 3i. Without it, non-`prod` items would leak into recommendations and Browse results via vector search the moment embeddings exist, regardless of whether a curator UI toggle has shipped.

The raw CSV booleans (`is_live`, `show_in_catalog`) on `portfolio_architectures` preserve the distinction between "one boolean TRUE" and "neither TRUE" for curator diagnostics.

As of 2026-07 there are ~39 in-scope rows with `showInCatalog=TRUE` (PA 34, PA,VP 3, SP 2); ingesting all in-scope rows with a valid `.adoc` also pulls in additional `dev`-status items beyond those. Rows excluded from Phase 1 entirely:

- `ProductType=Demo` (~30 rows) — deferred; these may migrate off OSSPA to Interact Hub, or be introduced in a later phase
- `ProductType=IE` (e.g. `ppid=64`) — Interactive Experience, deferred to a future phase
- `ppid=144` — empty `DetailPage` (links out to redhat.com) → no `.adoc` to analyze

### Asset types

The CSV column is named `ProductType`, but its values are **asset types** — the kind of Architecture Center artifact — **not** Red Hat products. Phase 1 ingests the three architecture asset types:

| Asset type | Full name             | What it is                                                                       |
| ---------- | --------------------- | ------------------------------------------------------------------------------- |
| `PA`       | Portfolio Architecture | A curated architecture example for a solution or use case — "art of the possible", not a prescriptive standard |
| `VP`       | Validated Pattern      | A GitOps-deployable, tested architecture example (appears as `PA,VP`)            |
| `SP`       | Solution Pattern       | A lighter-weight architectural pattern for a specific problem                    |

All three are read-through architecture content, so they map to the single RCARS `content_type='architecture'`. `Demo` and `IE` are separate asset types, deferred (below).

> **Terminology: do not call these "reference architectures."** In Red Hat usage a *reference architecture* is a specific, formally published, prescriptive artifact. OSSPA assets are curated "art of the possible" examples, not standards to conform to, and mislabelling them sets a false expectation for sales teams. This applies to **anything a user can see or is derived from what a user sees**:
>
> | Surface | Use | Not |
> | ------- | --- | --- |
> | Browse content-format filter group | "Architectures" | "Reference Architectures" |
> | Browse card badge | `Portfolio Architecture` / `Validated Pattern` / `Solution Pattern` (from `asset_type`) | "Reference Architecture" |
> | CTA button | "View Architecture" | — |
> | Embedding text prefix (3e) | `"Portfolio architecture: "` | `"Reference architecture: "` |
> | LLM analysis prompt (3d) | "portfolio architecture", "architecture example" | "reference architecture" |
>
> The embedding prefix and the analysis prompt are not rendered directly, but both reach users indirectly: the prompt shapes `summary` text shown on cards, and the Advisor rationale model paraphrases whatever wording it is fed. Settle the term before first ingest — changing the embedding prefix later invalidates every stored vector and forces a full re-embed.

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

- `pa:275` — Multitenant Setup for RHACS (PA), `status=prod`
- `pa:273` — Open Sovereign AI Cloud with Red Hat and Netris (PA), `status=prod`
- `pa:272` — `showInCatalog=FALSE` → ingested with `status=dev` (curators only, not surfaced by default)

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
    last_manifest_sync  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pa_ppid ON portfolio_architectures(ppid);
```

This implements the table planned (but not created) by RHDPCD-359, extended with `show_in_catalog` to preserve the raw CSV booleans for diagnostics and `derive_osspa_status()` input.

**`status` lives on `content_entities`** (not here) — see 2c. It uses Babylon's vocabulary (`prod`/`event`/`dev`) as the universal default-visibility gate. This avoids per-source LEFT JOINs in every retrieval query and gives future content sources the same column for free.


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
    recommender_audience_json   JSONB,
    asset_type                  TEXT,          -- PA / VP / SP

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
| `recommender_audience_json` | Internal Red Hat roles who should know about this content (SAs, consultants, TAMs) — distinct from `audience_json` which is the target consumer audience. See vocabulary spec, Audience section |
| `asset_type`          | Raw CSV asset type (`PA`, `VP`/`PA,VP`, `SP`) — stored for diagnostics. Named `asset_type`, **not** `product_type`: the CSV's `ProductType` column name is misleading — these values are Architecture Center artifact kinds, not Red Hat products. Actual products live in `content_entities.products_json`. |


`content_hash`: SHA-256 of the **full** DetailPage adoc body (before any truncation for the LLM prompt) **plus the CSV fields that feed the LLM prompt** (`Summary`, `Product`, `Solutions`, `Vertical`, `metaKeyword`) — see 3h. The hash is computed from the complete source so edits past the `osspa_max_adoc_bytes` cap still trigger re-analysis. Because those metadata fields are analysis inputs, a change to any of them deterministically re-triggers analysis on the next sync without a manual `--force`. CSV fields that do *not* feed the prompt (e.g. `Image1Url`) still update the extension/card row on upsert but do not force re-analysis.

`stale_commit`: the commit SHA of the **DetailPage file itself** (`git log -1 --format=%H -- <detail_page>`), recorded at the time the hash change was detected. Set when a re-analysis is triggered by a content change; cleared (set to NULL) when analysis succeeds. It is resolved only for items whose `content_hash` already changed, so it costs one `git log` per changed item — never a repo-wide walk. Same staleness pattern as `showroom_analysis`, but file-scoped rather than repo-scoped, because all OSSPA items share one repo.

**What triggers re-analysis — and what does not.** Staleness is decided **per item, by content hash**. The state of the examples repo is not an input:

| Signal                                             | Re-analyzes? | Scope             |
| -------------------------------------------------- | ------------ | ----------------- |
| Examples-repo HEAD moves (any commit, any file)    | **No**       | —                 |
| This item's `.adoc` bytes change                   | Yes          | This item only    |
| This item's prompt-input CSV fields change         | Yes          | This item only    |
| A *different* item's `.adoc` changes               | No           | That item only    |
| An included partial this item pulls in changes (3c)| Yes          | Every item including it |

Every sync clones/fetches the repo and re-hashes all in-scope adocs. That is cheap: the examples repo has 289 tracked `.adoc` files totalling ~1.2 MB (largest single file 31 KB), so hashing the entire set is milliseconds of local I/O and zero LLM cost. Only items whose own hash moved reach step 7e (LLM call + embedding write). A one-line edit to one architecture re-analyzes exactly one item.

> **Note on repo size and clone cost.** The 482 MB working tree is almost entirely `images/` (267 MB) and `diagrams/` (20 MB); the `.git` dir is 192 MB. Implementation should use a shallow **sparse** checkout limited to text (`*.adoc` and any include partials), which brings the working tree to ~1.2 MB and makes `osspa_clone_timeout_s = 60` comfortable rather than optimistic. Diagram images are referenced by URL (`Image1Url`), never read locally.

#### 2c. `status` column on `content_entities`

```sql
ALTER TABLE content_entities ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'prod';
CREATE INDEX IF NOT EXISTS idx_ce_status ON content_entities(status);
```

`status` lives on `content_entities`, not on `portfolio_architectures`, so that every retrieval query (`search_embeddings`, `list_content_entities_filtered`) can filter without a per-source LEFT JOIN. Values use **Babylon's existing vocabulary** (`prod` / `event` / `dev`) — Babylon is the larger content set and defines the convention. All sources map into these values:

- **Babylon items** — `upsert_babylon_catalog_item` sets `status` from `bi.stage` at write time (`prod` / `event` / `dev`). The `bi.stage` column remains for curator stage filtering; `status` is the universal default-visibility gate.
- **OSSPA items** — `derive_osspa_status()` maps CSV booleans into the same vocabulary: `islive + showInCatalog` → `prod`; anything else → `dev`. The raw booleans stay on `portfolio_architectures` for diagnostics.
- **Future content sources** — set `status` at their own ingest time; the default (`prod`) means items are visible until explicitly marked otherwise.

Default visibility filter for all sources: `WHERE status = 'prod' AND retired_at IS NULL`.

**ELI5 — what this does to `content_entities`.** One new column plus a one-time backfill. No table is restructured, no data is deleted, and `babylon_items.stage` keeps working exactly as it does today.

1. **Add the column.** `ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'prod'`. Postgres applies this instantly (metadata-only default); every existing row reads `'prod'` until something writes it.

2. **Backfill the existing Babylon rows — one time, idempotent.** `DEFAULT 'prod'` is *wrong* for existing `dev` and `event` Babylon items, so the ALTER must be immediately followed in `SCHEMA_SQL` by:

```sql
UPDATE content_entities ce
SET    status = bi.stage
FROM   babylon_items bi
WHERE  bi.content_id = ce.content_id
  AND  bi.stage IS NOT NULL
  AND  ce.status IS DISTINCT FROM bi.stage;
```

This is safe to re-run on every `rcars init-db`: it touches only rows that have a `babylon_items` row, only when `status` disagrees with `stage`, and it re-derives a value that is derived anyway. It **must** ship in the same `SCHEMA_SQL` block as the ALTER — without it there is a window between `init-db` and the next nightly catalog refresh in which every `dev`/`event` Babylon item reads `status='prod'` and leaks through the 3i default-visibility filter.

3. **New and changed Babylon items — no migration needed.** `upsert_babylon_catalog_item` (`db/database.py`) already builds a `ce_data` dict written with `ON CONFLICT (content_id) DO UPDATE`; add `"status": item.get("stage")` to that dict. `status` is *not* in that function's insert-only exclusion list (`summary`, `products_json`, `topics_json`, `audience_json`, `difficulty`), so every catalog refresh re-derives it from the CRD. An item promoted `dev` → `prod` in Babylon flips `status` on the next nightly refresh, exactly as `bi.stage` does today. Net effect: the backfill covers items already in the DB; the upsert covers everything from then on, and the two agree by construction.

4. **OSSPA items** — `upsert_osspa_item` writes `status` from `derive_osspa_status()` on the same pass.

So `status` is a denormalized "what stage is this thing at" copy, written by whichever ingest owns the row and read by every retrieval query. `bi.stage` remains the Babylon source of truth and keeps powering the existing curator stage filters and the `stages` query parameter.

#### 2d. SCHEMA_SQL placement

Both tables go into `src/api/rcars/db/database.py` `SCHEMA_SQL` using `CREATE TABLE IF NOT EXISTS`. They are appended after the `overlap_candidates` block, before the reference tables (`workload_mapping`, `workload_aliases`). The `status` column ALTER **and its backfill `UPDATE`** (2c) go with the other `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements at the bottom of `SCHEMA_SQL`, backfill immediately after the ALTER. No Babylon table is restructured.

#### 2e. content_entities card fields for OSSPA items

Populated on ingest from CSV **on first insert only**, then owned by analysis from that point on:


| Field           | Initial value (CSV, INSERT only)      | Owner after first analysis |
| --------------- | -------------------------------------- | -------------------------- |
| `display_name`  | CSV `Heading`                          | CSV `Heading` (updated every sync — CSV-owned, not LLM-owned) |
| `summary`       | CSV `Summary`                          | `analyze_architecture_item` — LLM summary |
| `products_json` | CSV `Product` (comma-split)            | `analyze_architecture_item` — LLM products |
| `topics_json`   | Derived from `Solutions` + `Vertical`  | `analyze_architecture_item` — LLM topics |
| `audience_json` | `["architect", "developer"]` default   | `analyze_architecture_item` — LLM target audience |
| `difficulty`    | `null`                                 | `analyze_architecture_item` — LLM difficulty |

`recommender_audience_json` is stored on `architecture_analysis` (not `content_entities`) and generated by the LLM alongside `audience_json`. See vocabulary spec, Audience section.

**`upsert_osspa_item` never updates `summary`, `products_json`, `topics_json`, `audience_json`, or `difficulty` on conflict.** These five columns are set once on `INSERT` as a pre-analysis seed and excluded from the `ON CONFLICT DO UPDATE` clause entirely — only `analyze_architecture_item` writes to them after that. This matters because `upsert_osspa_item` runs on *every* sync (CSV-only, no analysis), while analysis only reruns when `content_hash` changes; without the exclusion, a routine CSV-only sync would silently overwrite good LLM output with the stale CSV seed values, and the following hash-unchanged skip (3b step 7d) would leave it that way indefinitely. `upsert_babylon_catalog_item` in `src/api/rcars/db/database.py` already applies this same insert-only pattern to `content_entities` for Babylon items — `upsert_osspa_item` follows the identical approach.




### 3. Ingest Pipeline



#### 3a. New service module: `src/api/rcars/services/osspa_sync.py`


| Function                                                                          | Responsibility                                                                                             |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `fetch_palist_csv(settings) -> list[dict]`                                        | HTTP GET PAList.csv, parse, normalize booleans                                                             |
| `scope_rows(rows) -> list[dict]`                                                  | Apply ingestion gate — any `ProductType` token ∈ {PA, VP, SP} (no IE token) AND `.adoc` DetailPage. Not a live/catalog filter |
| `derive_osspa_status(row) -> str`                                                  | Map raw `islive` + `showInCatalog` → `prod` / `dev` using Babylon's status vocabulary. Both TRUE → `prod`; anything else → `dev`. Named to avoid collision with `retirement.py:derive_status()` which derives workflow stages |
| `upsert_osspa_item(db, row) -> str`                                               | Write `content_entities` (card fields **except** `summary`/`products_json`/`topics_json`/`audience_json`/`difficulty`, which are INSERT-only — see 2e; includes `status` from `derive_osspa_status` using `prod`/`dev` vocabulary) + `portfolio_architectures` for one CSV row. Always resets `retired_at = NULL, retirement_reason = NULL` on conflict, mirroring `upsert_babylon_catalog_item`. Returns `content_id` |
| `retire_missing_osspa(db, active_content_ids) -> int`                             | Soft-retire `source='portfolio_arch'` items not in the current in-scope set — only when completeness + shrink-guard checks pass (see 3h)  |
| `clone_examples_repo(settings) -> Path`                                           | Shallow clone or fetch portfolio-architecture-examples at configured ref; bounded timeout; must succeed before any DB writes this sync (see 3h). When reusing an existing checkout, reset to configured ref and clean untracked files to ensure a known-good state |
| `read_detail_adoc(clone_path, detail_page) -> tuple[str, str]`                    | Safe path join with canonical real-path containment check; verify file is tracked at recorded HEAD (`git ls-tree`); read **full** `.adoc` text; expand repo-internal `include::` directives under the rules in 3c; compute `content_hash` from the fully expanded text; then truncate to `osspa_max_adoc_bytes` for the LLM prompt copy; strip `++++` passthrough blocks from the prompt copy; return `(full_text_for_hash, prompt_text)` (see 3h) |
| `analyze_architecture_item(db, content_id, adoc_text, csv_row, settings) -> dict` | Sets `is_stale=TRUE` before analysis → LLM → **vocabulary normalization** (product alias snap, solution/vertical/platform alias snap, topic fuzzy dedup, flag unknowns) → write `architecture_analysis` + denormalize to `content_entities` + generate embeddings → clears `is_stale` only after all three commit (see 3h) |
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
       derive_osspa_status (prod / dev) from islive + showInCatalog
       content_entities (ON CONFLICT DO UPDATE — card fields EXCEPT summary/products_json/
           topics_json/audience_json/difficulty, which are INSERT-only — see 2e;
           includes status from derive_osspa_status;
           always resets retired_at = NULL, retirement_reason = NULL on conflict)
       portfolio_architectures (ON CONFLICT DO UPDATE — extension fields)
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
       e. Else: set is_stale=TRUE first → LLM analyze
              → vocabulary normalization: product alias snap, solution/vertical/platform
                alias snap, topic fuzzy dedup, flag unknown products/solutions/verticals
              → write architecture_analysis (including recommender_audience_json)
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
- **Follow `include::` directives, repo-internal only.** No such directive exists in the examples repo today (verified: 0 `include::` lines across all 289 tracked `.adoc` files), so this changes nothing now — it is cheap insurance against a contributor splitting a long architecture into partials and RCARS silently analyzing a stub. Rules:
    - Resolve the target relative to the including file, then apply the same safe-join + real-path containment check as the DetailPage (3h#1). Anything resolving outside the clone root → skip that include, log a warning, continue with the rest of the document.
    - The target must be tracked at HEAD (`git ls-tree`) — same rule as the DetailPage itself.
    - Reject targets that are URLs (`http://`, `https://`) or that contain unresolved AsciiDoc attributes (`{...}`): no network fetches, no attribute evaluation. Log and skip.
    - Max depth 3, with a visited set to break cycles.
    - Included bytes count toward `osspa_max_adoc_bytes`; hitting the cap truncates and flags `enrichment_review_needed`, same as an oversized top-level adoc.
    - `include::` line/tag selectors (`lines=`, `tag=`) are not interpreted — the whole file is inlined; log when selectors are present.
    - **`content_hash` is computed over the fully expanded text.** Editing a shared partial therefore re-triggers analysis for every item that includes it (see 2b). This is the reason to build it now rather than bolt it on later: adding include expansion after launch changes the hash of every affected item and forces a re-analysis wave.
    - Sparse checkout (2b note) must include partials, not only the DetailPage targets — pattern on `*.adoc` rather than an explicit file list.



#### 3d. LLM analysis prompt

Reuse the structured JSON output format from Showroom analysis (same `parse_analysis_response()` helper). The model comes from `settings.osspa_analysis_model`, which defaults to the same model the Showroom analyzer uses (Section 5) — so Phase 1 behaviour is unchanged, but the model can be swapped for architecture analysis alone without a code change. *Which* model it should ultimately be (frontier vs. open-source, cost trade-offs) is deferred to Phase 2 pending a team discussion (see Out of Scope). Adapt the prompt:

- **Product names injected from vocabulary.** The canonical product list from `vocabulary.yaml` is interpolated into the prompt via `render_vocabulary_block(vocab, 'architecture')`. The model is instructed to prefer listed product names. No other vocabulary dimension is in the prompt — solutions, verticals, topics, and difficulty are normalized post-analysis.
- Provide CSV metadata as context: `Summary`, `Product`, `Solutions`, `Vertical`, `metaKeyword` (untrusted input — framed as data, not instructions; see 3h)
- Provide adoc prose as content body
- Request: `summary`, `products`, `topics`, `detailed_topics`, `audience`, `recommender_audience`, `difficulty`, `solution_areas`, `use_cases`, `key_components`
- `audience` = who the content is FOR (platform engineers, developers, etc.); `recommender_audience` = who at Red Hat should know about this content (solution architects, consultants, TAMs). Both are open — the LLM generates whatever fits.
- Topics are fully open — no enumerated list, no count cap. The LLM generates as many specific topic phrases as the content warrants. Format guidance: short phrases (2-4 words each), not sentences. Post-analysis fuzzy dedup collapses near-identical topics.
- `detailed_topics` is a richer, architecture-wide list of the specific topics the doc covers (technologies, integration points, design decisions) — more detailed than the short `topics`, applicable to the **whole** architecture, not per section. It enriches the single embedding (see 3e)
- Instruct the LLM to draw from both CSV metadata and adoc prose; prefer adoc for specifics
- For thin content (an adoc with mostly diagrams/embeds and a short intro): the prompt must produce a useful summary from CSV metadata alone — the adoc intro may only be 2-3 sentences
- Do **not** request `modules` or `learning_objectives` — these are architecture docs, not labs. Learning-objective verbs for architecture content use the `read_through` verb set from the vocabulary (see [vocabulary spec](2026-08-10-controlled-vocabulary-design.md), Action verbs section).

Prompt file: `src/api/rcars/prompts/architecture_analyze.txt`

#### 3e. Embeddings

One embedding per item — architecture-level, not per-section. Per-section
embeddings are **not** generated: searching or recommending an individual
section of an architecture document has no clear use, and per-section vectors
add complexity and noise. Instead, the single embedding is enriched with the
LLM-generated **detailed topics** so it captures more of the architecture than
the summary alone.


| `embed_type` | `content_text`                                                    | When                              |
| ------------ | ---------------------------------------------------------------- | --------------------------------- |
| `summary`    | `"Portfolio architecture: {summary}\nTopics: {detailed_topics}"` | Always — drives Advisor retrieval |


All embeddings: `source='portfolio_arch'`, `content_type` from the mapping table in this spec.

The type prefix `"Portfolio architecture: "` places these in slightly different vector space from the `"Hands-on lab: "` and `"Environment: "` prefixes used by Babylon items. Deliberately **not** `"Reference architecture: "` — see the terminology note in Asset types. The prefix is baked into every stored vector, so changing it after ingest requires a full re-embed of all `source='portfolio_arch'` rows.

#### 3f. Babylon safety

The Babylon CRD scan retires rows that disappear from Babylon. This must only apply to `source='babylon'` rows. Confirm (and fix if needed) that the retirement query filters by source:

```sql
-- Only retire Babylon items based on CRD disappearance
WHERE source = 'babylon' AND content_id NOT IN (...)
```

As part of this work, **rename the existing Babylon helper `retire_removed_items()` → `retire_missing_babylon()`** so it reads as a matched pair with `retire_missing_osspa()` — each source owns a clearly named retire helper. OSSPA lifecycle is owned exclusively by `retire_missing_osspa()` in this service; Babylon lifecycle by `retire_missing_babylon()`.

#### 3g. Controlled Vocabulary integration

This spec assumes the controlled vocabulary ([RHDPCD-507](2026-08-10-controlled-vocabulary-design.md)) is implemented. The vocabulary provides:

- **Product names** — injected into the analysis prompt via `render_vocabulary_block()`. The only dimension in the prompt.
- **Post-analysis normalization** — product alias snap, solution/vertical/platform alias snap, topic fuzzy dedup, unknown-term flagging. Runs between LLM response and DB write in `analyze_architecture_item`.
- **`read_through` action verbs** — the verb subset for architecture content (compare, evaluate, assess, identify, etc.). Used if/when learning objectives are requested for architecture items.
- **`recommender_audience_json`** — new field generated by the LLM alongside `audience_json`, stored on `architecture_analysis`.

The vocabulary file lives at `src/api/rcars/data/vocabulary.yaml` and is loaded via `vocabulary.py`. See the [vocabulary spec](2026-08-10-controlled-vocabulary-design.md) for the full contract.

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

10. **LLM-owned card fields survive routine CSV syncs.** `upsert_osspa_item` excludes `summary`, `products_json`, `topics_json`, `audience_json`, and `difficulty` from its `ON CONFLICT DO UPDATE` clause (2e) — they are seeded on `INSERT` only and owned by `analyze_architecture_item` afterward. Without this, the CSV-only upsert that runs on every sync would overwrite good LLM analysis with the CSV seed on the very next sync, and the hash-unchanged skip (item 2, above) would prevent analysis from ever restoring it. `upsert_osspa_item` also always resets `retired_at = NULL, retirement_reason = NULL` on conflict, so a row that reappears in the CSV after being retired is correctly un-retired on the next sync — matching the Lifecycle table (Section 6) and `upsert_babylon_catalog_item`'s existing behavior for Babylon.

#### 3i. Default visibility filter (Phase 1, not deferred)

Browse UI for architecture content **is in scope for Phase 1** (see 3j). Advisor UI (recommendation cards, rationale rendering, CTA) remains deferred. Either way the visibility filter is a data-safety concern, not a rendering one: non-`prod` OSSPA rows must be prevented from surfacing through the *existing* Advisor retrieval and Browse API paths, because embeddings for `dev`-status items exist the moment analysis runs (3e) and are visible to any vector-search query regardless of what the UI does or does not render.

To close that gap without waiting on the UI work, the shared candidate-retrieval query paths add one filter clause in Phase 1:

```sql
-- Applied by: Advisor vector-search candidate query, Browse default (non-curator) query
-- status lives on content_entities (see 2c) using Babylon's vocabulary, so no per-source JOIN is needed
WHERE ce.retired_at IS NULL
  AND ce.status = 'prod'
```

Because `status` uses Babylon's own vocabulary (`prod`/`event`/`dev`) and lives on `content_entities`, the filter is universal — no source-specific branches needed:

- **Babylon items** — `upsert_babylon_catalog_item` sets `status` from `bi.stage`, so `prod` items pass; `dev`/`event` items are filtered just like they are today via `bi.stage = 'prod'`.
- **OSSPA items** — `derive_osspa_status()` maps `islive + showInCatalog` → `prod`; anything else → `dev`.
- **Curator-facing queries** (Browse "Show non-prod" toggle, admin/curation endpoints) omit the `status = 'prod'` clause, mirroring the existing "Show Retired" pattern.
- This replaces the current `(bi.stage = 'prod' OR bi.content_id IS NULL)` pattern in `list_content_entities_filtered` and the stage-based EXISTS subquery in `search_embeddings` — one universal filter instead of per-source logic.

**Specific integration points** that need this filter:

1. **`search_embeddings`** (`database.py`, `Database.search_embeddings`) — the vector search candidate query. Currently filters on `retired_at IS NULL` plus Babylon-specific `stage` and ZT-namespace filters. Replace the stage-based EXISTS subquery with `ce.status = 'prod'`. Because `status` lives on `content_entities` (see 2c) and uses Babylon's vocabulary, this simplifies the query — no per-source JOIN required.

2. **`list_content_entities_filtered`** (`database.py`, `Database.list_content_entities_filtered`) — the Browse API query. This function LEFT JOINs `babylon_items` and has Babylon-centric stage logic (`bi.stage = 'prod' OR bi.content_id IS NULL`). Replace that with `ce.status = 'prod'` — same meaning, universal across sources, no `bi.content_id IS NULL` fallthrough needed. The curator "Show non-prod" toggle omits this clause. The existing `stages` parameter (for filtering to specific stages like `dev`/`event`) continues to work via `bi.stage` for Babylon items or via `ce.status` for all sources.

3. **`_format_single_candidate`** (`services/recommender/rationale.py`) — the rationale formatter. Currently handles `lab`/`demo` and `sandbox` content types only. `live` OSSPA items WILL reach this function via vector search in Phase 1. Without an `architecture` branch, they get bare-minimum formatting (no solution areas, use cases, or key components context). **Phase 1 must add a minimal `architecture` branch** that formats the available fields — this is not a UI concern; it's a data-quality concern for the rationale prompt.

### 3j. Browse integration (Phase 1)

Architecture items must be visible in the Browse catalog and accessible via the API as soon as they're ingested. Without this, validation requires raw SQL. Advisor integration (chat recommendations, rationale) is deferred — this section covers catalog browsing only.

**Behaviour.** Browse keeps working exactly as it does today by default: Babylon items only, same filters, same cards, no visual change for anyone who doesn't touch the new control. A **Content Format** filter group in the left sidebar adds architectures to the result set on demand. It is additive — architectures appear *alongside* labs, not instead of them.

| Control state                              | `content_type` sent to API      | Result                                   |
| ------------------------------------------- | ------------------------------- | ---------------------------------------- |
| Default (nothing selected)                 | `lab,demo,sandbox`              | Today's behaviour — Babylon items only   |
| "Architectures" selected                   | `lab,demo,sandbox,architecture` | Babylon items + portfolio architectures  |
| "Architectures" only (deselect Hands-on)   | `architecture`                  | Architectures only                       |

Sending an explicit `content_type` in the default case (rather than omitting it) keeps the default honest as new content types land: a future `interactive` source cannot silently appear in the default view.

#### API

**No new endpoints, no new query parameters.** `GET /api/v1/catalog` already accepts a comma-separated `content_type` param (`api/routes/catalog.py`, `list_catalog`) and passes it to `list_content_entities_filtered` as `content_types`, which applies `ce.content_type = ANY(...)`. Architecture rows live in `content_entities`, so they are returned by the existing `LEFT JOIN babylon_items` shape with `bi.*` columns NULL. `content_type`, `source`, `summary`, `products_json`, `topics_json`, `difficulty` and the new `status` all come through on `ce.*`.

Two DB-layer changes are required — without them architecture items are silently unreachable no matter what the frontend sends:

1. **Stage predicate → status predicate** (this is the 3i change; calling it out here because Browse is where it bites). `list_content_entities_filtered` currently gates every row on `babylon_items.stage`:

```sql
-- today
if stages:            bi.stage = ANY(%(stages)s)
elif babylon_specific: bi.stage = 'prod'
else:                 (bi.stage = 'prod' OR bi.content_id IS NULL)
```

   The Browse page **always** sends `stage` (`buildStageString()` in `BrowsePage.tsx` returns at minimum `'prod'`), so the first branch always wins, and `bi.stage = ANY(ARRAY['prod'])` evaluates to NULL for an OSSPA row with no `babylon_items` join partner — the item is dropped. Phase 1 swaps the predicate to the universal column from 2c:

```sql
-- Phase 1
if stages:            ce.status = ANY(%(stages)s)
elif babylon_specific: ce.status = 'prod'
else:                 ce.status = 'prod'
```

   Same semantics for Babylon (`ce.status` is written from `bi.stage`, see 2c), and the `bi.content_id IS NULL` fallthrough disappears. `bi.stage` stays in the SELECT list for display and for curator stage badges.

2. **`is_hands_on` in the response.** Add `ce.is_hands_on` to the returned fields so the frontend can branch card rendering without inferring it from `content_type`. It is already on `content_entities`; it just needs to survive into the API response model.

Babylon-specific facets (cloud provider, AgnosticD config, workloads, category) are meaningless for architectures. The existing `babylon_specific` flag already forces `status = 'prod'` and those filters join Babylon-only tables, so selecting one naturally yields zero architecture rows. That is correct behaviour — note it in the UI by graying the Content Format group when a Babylon-only facet is active, rather than returning a confusing empty result.

#### Content format filter (frontend)

Sidebar filter group, rendered above the existing facets in `BrowsePage.tsx`:

| Filter label      | `content_type` values    | `is_hands_on` | Phase 1     |
| ----------------- | ------------------------ | ------------- | ----------- |
| Hands-on Labs     | `lab`, `demo`, `sandbox` | `TRUE`        | On by default |
| Architectures     | `architecture`           | `FALSE`       | Off by default |
| Interactive Demos | (future — `interactive`) | `FALSE`       | Hidden until that content type ships |

Implementation notes, all in `src/frontend/src/pages/BrowsePage.tsx`:

- **State + URL sync.** New `formats` state (`Set<'hands_on' | 'architecture'>`, default `{'hands_on'}`), serialized into `searchParams` as `format=architecture` only when it differs from the default, mirroring how `stage` is only written when it is not plain `prod`. `fetchItems` maps the set to the `content_type` param.
- **Control.** Reuse the existing `StageToggle` component (already used for the `dev`/`event` toggles) — same visual language, no new component. It sits in the sidebar filter rail rather than the toolbar because it is a scope filter, not a curator toggle. Available to **all** users, not curator-gated.
- **Active-filter chips.** Push a "Architectures" chip into `activeFilters` when the toggle is on, and include it in `clearAllFilters` (which must reset to the default set, not to empty).
- **Identity — the one real refactor.** The card list is keyed on `item.ci_name` (`key={item.ci_name}`, `itemDetails[item.ci_name]`), the expand/detail path calls `api.getCatalogItem(ciName)`, and `isZtItem()` calls `item.ci_name.startsWith(...)`. Architecture rows have `ci_name = null`, so this crashes as written. Phase 1: make `ci_name` optional on the `CatalogItem` interface, key the list on `item.content_id` (present for every row, Babylon included), and guard `isZtItem`/`catalogUrl`/curator handlers on `ci_name` being present.
- **Card body.** Architecture rows expand exactly like Babylon rows, using the same component and the field map in "Architecture card template" below. That requires making the existing `GET /api/v1/catalog/{identifier}` route source-aware — three small changes, detailed in that section.

#### Vocabulary-based filters

Add filters for the vocabulary dimensions that have value for catalog browsing:

| Filter | Source field | Type | Notes |
| ------ | ----------- | ---- | ----- |
| **Solutions / TDPs** | `solutions` on `portfolio_architectures`, or `solution_areas_json` on analysis tables | Multi-select | Values from vocabulary. **Architecture items only** — Babylon labs are not tagged with solutions (see below). |
| **Verticals** | `verticals` on `portfolio_architectures` | Multi-select | Values from vocabulary. **Architecture items only** (see below). |
| **Target Audience** | `audience_json` on `content_entities` | Multi-select | Open dimension — filter values derived from the distinct values in the database, not the vocabulary file. Applies to all content types. |

These filters are additive — they refine the result set alongside existing filters (search, stage, cloud provider, workloads). Vocabulary-based filters apply across content types where the data exists; items without a value for a filter dimension are excluded when that filter is active.

> **Solutions and verticals do not extend to Babylon.** The [Controlled Vocabulary spec](2026-08-10-controlled-vocabulary-design.md) scopes `solutions`, `verticals`, and `platforms` to architecture items deliberately — Babylon labs are product-centric and industry-agnostic, so asking the analyzer for those dimensions would fill the columns with guesses. `showroom_analysis` has no columns for them and none are planned. Selecting either filter therefore narrows results to architecture items. Extending them to Babylon later is a column plus a field-map entry, not a redesign — but it is not part of either spec today.
>
> What Babylon items *do* gain from the vocabulary is normalization of the dimensions they already carry: canonical product names, snapped difficulty, and deduplicated topics. Those improve the existing Products and Difficulty filters rather than adding new ones.

#### Architecture card template

**Design rule: match the Babylon catalog card.** The architecture card is the *same component* with a different data map — same expand/collapse row, same section order, same badge/pill/label CSS classes, same spacing. A user scrolling a mixed result set should see one consistent list, not two designs. Where architecture content genuinely has no equivalent (modules, workloads, duration), the section is **omitted**, not replaced with an empty state or a placeholder. Where it has an analogue, it reuses the Babylon section's widget rather than inventing a new one.

This is a data-mapping exercise, not a design exercise: no new CSS classes, no new layout primitives. Every class named below already exists in `BrowsePage.tsx` / the Browse stylesheet.

**Collapsed row header** (`.browse-item-header`) — structurally identical:

| Element | Babylon | Architecture |
| ------- | ------- | ------------ |
| Expand caret | `.browse-expand-icon` ▶/▼ | Same |
| Title | `display_name \|\| ci_name` | `display_name` |
| Status badge | `stage.toUpperCase()` when `stage !== 'prod'` (`badge-dev` / `badge-event`) | `DEV` when `status !== 'prod'`, same `badge-dev` class |
| Type badge | `ZT`, `v2` | `Portfolio Architecture` / `Validated Pattern` / `Solution Pattern` from `asset_type`; falls back to `Architecture`. Never "Reference Architecture" (see terminology note in Asset types) |
| Failure badge | `FAILED` on `scan_status = 'failed'` | Omitted — `architecture_analysis` has no `scan_status` (7). A stale item shows nothing; failures surface in Recent Jobs |
| Review badge | `needs review` on `enrichment_review_needed` | Same, same class |
| Retired badge | `RETIRED {date}` | Same, same class |
| Subline | `.browse-item-ci` → `{ci_name} · {category}` | Same class → `{pa_name} · {primary solution}`, falling back to `{pa_name} · Architecture` |
| Curator Edit button | Opens `CuratorDrawer` | Same, reduced action set — see Curator controls |

**Expanded body** (`.browse-item-body`) — same numbered section order as the Babylon card:

| # | Babylon section | Architecture equivalent | Source |
| - | --------------- | ----------------------- | ------ |
| — | Scan Error block | **Omitted** | no `scan_status` |
| 1 | Type line + description (`.browse-type-line`, `.browse-description`) | Same widget: `{asset_type} · {difficulty}`, then summary paragraph. Duration segment omitted | `architecture_analysis.asset_type`, `content_entities.difficulty`, `content_entities.summary` |
| 2 | Learning Objectives (`SectionLabel` blue + `.browse-objectives` list, preview 5 + "Show N more") | **Use Cases** — same list widget, same preview/expand behaviour, label changed | `architecture_analysis.use_cases_json` |
| 3 | Content Analysis (`SectionLabel` purple, `.browse-pill-group` per dimension) | Same section, four pill groups: Products, Topics, **Solutions**, **Verticals** | `products_json`, `topics_json` (both on `content_entities`); `solutions`, `verticals` (on `portfolio_architectures`) |
| 4 | Modules (`CollapsibleSection` amber, count badge) | **Key Components** — same collapsible, same amber, count = number of components, rendered as a single `.browse-pill-row` | `architecture_analysis.key_components_json` |
| 5 | Workloads & Automation (`CollapsibleSection` green) | **Omitted** — not applicable to non-hands-on content (also Out of Scope) | — |
| 7 | Curator Tags (`.browse-pill-sublabel` + curator pills) | Same, unchanged | `enrichment_tags`, already keyed on `content_id` |
| 8 | Links (`.browse-links`) | Same row, two links: **"View Architecture"** → `https://www.redhat.com/architect/portfolio/detail/{pa_name}/`, and **"Source (.adoc)"** → `{osspa_examples_repo_url}/-/blob/{ref}/{detail_page}` | `portfolio_architectures.pa_name`, `detail_page` |

**Deliberately omitted, with reason:**

| Omitted | Why |
| ------- | --- |
| Duration | No `curated_duration_min` / `estimated_duration_min`; read-through content has no provisioning time. The type line simply drops that segment |
| Learning objectives | Not requested from the LLM (3d) — these are architecture docs, not labs. Use Cases occupies the slot |
| Modules | Single flat `.adoc`, no Antora module structure |
| Workloads, cloud provider, OCP version, instance counts, ACL groups | Nothing is provisioned |
| Showroom repo link, "Start Lab" / RHDP Catalog link | Not a Babylon catalog item |
| Performance / reporting block | RHDP reporting is Babylon-keyed (Out of Scope) |
| Diagram image (`image_url`) | Stored but not rendered in Phase 1 — the Babylon card has no image slot, and adding one only for architectures breaks row-height consistency in a dense mixed list. Easy follow-up if curators want it |
| `detailed_topics_json` | Embedding enrichment only (3e), not a display field — it would duplicate Topics visually |

**Detail endpoint — the card body needs it.** The Babylon card fetches its body from `GET /api/v1/catalog/{identifier}` on expand. Matching the card means architectures must resolve through the same route. Three surgical changes in `api/routes/catalog.py`, all of which the route's own naming already anticipates (the path param is `identifier`, not `ci_name`):

1. `_resolve_to_content_id()` currently hardcodes `f"babylon:{identifier}"` for any unprefixed value. Change: if the identifier already contains a `{source}:` prefix, use it as-is; otherwise keep the `babylon:` default for backward compatibility with every existing caller.
2. `_resolve_item()` calls `db.get_babylon_item*` unconditionally. Change: dispatch on prefix — `pa:` resolves via `content_entities` joined to `portfolio_architectures`.
3. `get_catalog_item()` calls `db.get_showroom_analysis(content_id)`. Change: dispatch on `ce.source` — `babylon` → `showroom_analysis`, `portfolio_arch` → `architecture_analysis`. The response key stays `analysis` so the frontend keeps one code path.

`get_workloads` / `get_acl_groups` are already gated on `is_agd_v2` (false here) and `get_performance_*` return empty for a non-Babylon `content_id`, so those need no change.

#### Curator controls

- **"Show non-prod" toggle** — surfaces `dev`-status architecture items, mirroring the existing "Show Retired" pattern. Non-`prod` items get a `Dev` status badge.
- **"Show Retired" toggle** — works as-is; soft-retired architecture items appear when toggled.
- **Enrichment review flag** — items with `enrichment_review_needed = TRUE` show a review indicator on the card (same pattern as Babylon items with review flags).
- **Curator drawer, reduced action set.** The drawer opens for architecture items with the actions that are already `content_id`-keyed and therefore source-agnostic once `_resolve_to_content_id` is fixed (see card template): **tags**, **notes**, and **flag for review**. Hidden for architectures: duration override, content-path override, Showroom URL override — all Babylon-specific. Hiding is by `source`, not by content type, so future sources inherit the same rule.

#### Testing (Browse)

| Test | Type | Assertion |
| ---- | ---- | --------- |
| API returns architecture items in catalog | Integration | `GET /api/v1/catalog` includes `source='portfolio_arch'` items |
| Content format filter: "Architectures" | Integration | Only `content_type='architecture'` items returned |
| Content format filter: "Hands-on Labs" | Integration | Only `lab`/`demo`/`sandbox` items returned |
| Solutions filter | Integration | Filter by solution returns matching items |
| Non-prod items hidden by default | Integration | `dev`-status items absent from default catalog response |
| Non-prod items visible with toggle | Integration | `dev`-status items appear when "Show non-prod" active |
| Architecture card CTA link | Unit | URL constructed correctly from `pa_name` |
| Architecture card hides lab-specific fields | Unit | No duration, no Showroom link, no stage badge |
| Default view excludes architectures | Integration | With no `content_type` selected, response contains only `lab`/`demo`/`sandbox` |
| Toggle is additive | Integration | `content_type=lab,demo,sandbox,architecture` returns both Babylon and OSSPA rows in one page |
| Stage param no longer drops architectures | Integration | `stage=prod` + `content_type=architecture` returns `prod` OSSPA rows (regression guard for the `bi.stage` → `ce.status` swap) |
| Null `ci_name` does not break rendering | Unit | Card list renders an architecture item keyed on `content_id`; `isZtItem` returns false without throwing |
| Detail route resolves a `pa:` identifier | Integration | `GET /api/v1/catalog/pa:275` returns the entity with `analysis` populated from `architecture_analysis` |
| Detail route unprefixed identifier still means Babylon | Integration | `GET /api/v1/catalog/{ci_name}` behaves exactly as before (regression guard for `_resolve_to_content_id`) |
| Architecture card expands with same section order | Unit | Type line, Use Cases, Content Analysis, Key Components, Curator Tags, Links — in that order |
| Architecture card omits inapplicable sections | Unit | No Modules, no Workloads & Automation, no duration segment, no Showroom link |
| Asset-type badge text | Unit | `PA` → `Portfolio Architecture`; `PA,VP` → `Validated Pattern`; `SP` → `Solution Pattern`; unset → `Architecture` |
| Curator drawer action set for architectures | Integration | Tags, notes and flag succeed on a `pa:` identifier; duration/content-path/URL overrides are not offered |

### 4. Worker Integration

**Queue:** `arq:queue:scan` (same as Babylon scan worker — reuses existing scan worker process)

**Job type:** `osspa_sync`

**Entry points:**


| Entry                           | Details                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| Nightly maintenance pipeline    | Separate pipeline dispatched by `run_nightly_pipeline` after the Babylon pipeline completes (see 4a). Never passes `confirm_empty_inventory` |
| `POST /api/v1/admin/sync-osspa` | Admin-only endpoint; enqueues job; accepts optional `confirm_empty_inventory: bool`; returns `{job_id}` |
| `rcars osspa sync [--force] [--confirm-empty-inventory]` | CLI command; synchronous; `--force` bypasses hash check; `--confirm-empty-inventory` permits retiring all items when the CSV has zero in-scope rows (see 3h) |


All three entry points funnel through `run_osspa_sync`, which is serialized by a Postgres advisory lock (see 3h) — a manual sync and the nightly pipeline cannot overlap.

#### 4a. Pipeline structure

The nightly maintenance pipeline (`run_nightly_pipeline` in `ops.py`) is restructured from a single flat sequence into two self-contained sub-pipelines dispatched sequentially:

```text
run_nightly_pipeline (orchestrator)
├── run_babylon_pipeline          # current Steps 1-5, extracted as-is
│   ├── 1. Catalog refresh from CRDs
│   ├── 2. Stale check (git refs)
│   ├── 3. Re-analyze stale items
│   ├── 4. Workload scan + config scan
│   ├── 4b. Sandbox summary
│   └── 5. Reporting metrics sync
└── run_osspa_pipeline            # new, self-contained
    ├── 1. CSV fetch + scope
    ├── 2. Clone examples repo
    ├── 3. Upsert items + retire missing
    └── 4. Analyze changed items
```

Each sub-pipeline:
- Reports its own progress messages (e.g. `pipeline:osspa:csv_fetch`, `pipeline:osspa:analyze`)
- Has its own step numbering — no renumbering across pipelines
- Can be triggered independently via CLI or admin API
- Returns its own stats dict

The orchestrator sequences them and collects combined stats. If the Babylon pipeline fails, the OSSPA pipeline still runs (same continue-on-error pattern as the current step-level `try/except`). There are no data dependencies between the two — OSSPA reads from GitLab, not from Babylon CRDs.

This structure prepares for future content sources (Interact Hub, etc.) — each gets its own pipeline block, no interleaving.


### 5. Configuration

All settings in `src/api/rcars/config.py` using existing `RCARS_` prefix pattern:


| Setting                   | Default                                                        | Purpose                     |
| ------------------------- | -------------------------------------------------------------- | --------------------------- |
| `osspa_sync_enabled`      | `true`                                                         | Gates OSSPA sub-pipeline in nightly run |
| `osspa_palist_url`        | PAList.csv raw URL                                             | Inventory source            |
| `osspa_examples_repo_url` | `https://gitlab.com/osspa/portfolio-architecture-examples.git` | Content repo                |
| `osspa_examples_ref`      | `main`                                                         | Git ref to clone/fetch      |
| `osspa_clone_dir`         | `{clone_dir}/osspa-examples`                                   | Working directory           |
| `osspa_csv_fetch_timeout_s` | `15`                                                        | Timeout for CSV HTTP fetch (see 3h) |
| `osspa_clone_timeout_s`   | `60`                                                          | Timeout for git clone/fetch (see 3h); separate from CSV fetch because shallow clone of the examples repo may be slow from OpenShift pods |
| `osspa_max_adoc_bytes`    | `200000`                                                      | Max adoc bytes (after include expansion) sent for analysis; larger is truncated + flagged (see 3h). Lowered from the originally-specified 1 MB: the largest `.adoc` in the repo today is 31 KB and all 289 files together are 1.2 MB, so a 1 MB per-file cap would never fire and offers no protection against a hostile or runaway document |
| `osspa_retire_shrink_guard_pct` | `0.5`                                                    | Minimum fraction of the current DB's active `source='portfolio_arch'` row count that the new active set must retain before `retire_missing_osspa` is allowed to run (see 3h) |
| `osspa_advisory_lock_id`  | `736372`                                                      | Postgres advisory lock ID for sync serialization (see 3h); chosen to avoid collision with other RCARS locks |
| `osspa_analysis_model`    | `""` (empty → falls back to `settings.model`)                  | Model used by `analyze_architecture_item`. Ships in Phase 1 as a lever with an unchanged default — see below |

**Why `osspa_analysis_model` exists in Phase 1.** The *choice* of a dedicated model is deferred (Out of Scope), but the *lever* costs almost nothing to add now and is expensive to retrofit later:

- **The house pattern already exists.** `config.py` carries `triage_model`, `rationale_model`, `overlap_model`, `chat_router_model`, `chat_answer_model`, and every call site passes `model=settings.<x>_model` explicitly. Two of those (`chat_router_model`, `chat_answer_model`) already use exactly this empty-string-means-inherit idiom, resolved in `Settings.model_post_init`. Adding `osspa_analysis_model` is one field plus a two-line fallback in `model_post_init`.
- **The analysis function is *not* shared.** `analyze_showroom()` (`services/analyzer.py`) is Showroom-specific end to end — it clones a repo, walks Antora modules and `nav.adoc`, filters boilerplate, and takes `model` as an explicit parameter. This spec already defines a **separate** `analyze_architecture_item` with its own prompt file (`prompts/architecture_analyze.txt`), its own reader (`read_detail_adoc`, 3c), and its own output shape. Only `parse_analysis_response()` and the embedding helper are shared, and neither selects a model. So there is no shared-call-site problem: the new function takes `model=settings.osspa_analysis_model` on day one.
- **It is immediately useful.** Architecture analysis can be evaluated against a different model without redeploying code or touching Babylon scanning — set `RCARS_OSSPA_ANALYSIS_MODEL` and re-run `rcars osspa sync --force` on a handful of items. That is the evaluation the Phase 2 discussion needs as input.
- **Default is unchanged.** Empty → `settings.model`, i.e. Phase 1 behaves exactly as "reuse the Showroom analysis model" with zero cost or quality delta.

No auth tokens required — both repos are public (HTTPS clone is intentional — these are GitLab repos, not GitHub, and public access does not require SSH). If GitLab rate-limits the clone, an optional `RCARS_GITLAB_TOKEN` can be wired later.

### 6. Lifecycle


| Event                                                    | Result                                                                              |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| New in-scope row appears                                 | Upserted on next sync; `status` derived (`prod` or `dev`); analysis runs            |
| `islive` and/or `showInCatalog` flips FALSE              | `status` re-derived to `dev`; item **stays ingested**, dropped from default Advisor/Browse — not retired |
| `islive` and `showInCatalog` both back to TRUE           | `status` re-derived to `prod`; item surfaces again by default                       |
| Row removed from CSV entirely                            | Not in active set → `retire_missing_osspa` soft-retires it                          |
| Asset type changes to Demo/IE                            | No longer in scope → treated as removed → soft-retired                              |
| Content of DetailPage `.adoc` changes                    | `content_hash` mismatch → re-analyzed on next sync                                  |
| CSV prompt-input changes (Summary, Product, Solutions, Vertical, metaKeyword) | Included in `content_hash` → re-analysis triggered on next sync (see 3h)  |
| CSV non-prompt field changes (e.g. Image1Url)            | Card/extension row updated on upsert; re-analysis not forced                        |
| Previously retired row reappears in CSV                  | `upsert_osspa_item` always clears `retired_at`/`retirement_reason` on conflict (3a/3h#8) — upserted with `retired_at = NULL` on next sync; `status` re-derived (`prod` or `dev`); treated as new |




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
| `Product` column empty for a row              | `products_json` seeded empty on INSERT only; LLM fills from adoc + other CSV fields; never reset by a later CSV-only sync (2e)               |
| Duplicate `ppid` in CSV                       | Should not happen; log warning; last row wins                                                                                                 |
| Path traversal / symlink escape in DetailPage | Real path resolves outside clone root → skip row; log warning (see 3h)                                                                        |
| adoc exceeds `osspa_max_adoc_bytes`           | Truncate to the cap for analysis; flag `enrichment_review_needed`; continue (see 3h)                                                          |
| CSV fetch incomplete / malformed header       | Completeness guard fails → retirement skipped; upsert whatever parsed; log (see 3h#4)                                                         |
| Prompt-injection text in adoc/CSV             | Treated as untrusted data, not instructions; output schema-validated; worst case a low-quality analysis flagged for review (see 3h)           |
| Concurrent sync (nightly + manual)            | Second run exits early — advisory lock already held (see 3h)                                                                                  |
| Crash mid embedding write                     | Atomic swap → prior vectors intact; item never left with zero/partial embeddings; `is_stale` stays TRUE, retried next sync (see 3h)           |
| Non-`prod` item's embedding exists but item hasn't shipped in UI yet | Excluded from Advisor/Browse default results by the 3i status filter regardless — not dependent on UI existing |




### 8. Testing


| Test                                                                 | Type        | Assertion                                              |
| -------------------------------------------------------------------- | ----------- | ------------------------------------------------------ |
| Ingestion gate: `Demo` and `IE` excluded                             | Unit        | Row not in active set                                  |
| Ingestion gate: `DetailPage` without `.adoc` excluded                | Unit        | Row not in active set                                  |
| Ingestion gate: in-scope row is ingested regardless of live status   | Unit        | `showInCatalog=FALSE` / `islive=FALSE` row still in active set |
| Status derivation: prod / dev                                        | Unit        | Both TRUE → `prod`; anything else → `dev` |
| Default visibility: non-`prod` items excluded from default queries (see 3i) | Integration | `dev`-status items absent from Advisor + Browse default queries unless "Show non-prod" set |
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
| Retrieval: non-`prod` OSSPA item excluded from Advisor default candidates (see 3i) | Integration | `dev`-status item embeddings exist but are filtered from the default candidate query |
| Vocabulary: product alias snap in analysis output | Unit | LLM returns "ACS" → stored as "Red Hat Advanced Cluster Security" |
| Vocabulary: unknown product flagged | Unit | LLM returns unrecognized product → `enrichment_review_needed` + `unknown_product` reason |
| Vocabulary: topic fuzzy dedup | Unit | "GitOps with ArgoCD" + "GitOps with Argo CD" collapse to one |
| Vocabulary: solution alias snap | Unit | "ApplicationPlatform" → "Application Platform" |
| Vocabulary: recommender_audience_json populated | Integration | Architecture analysis includes both `audience_json` and `recommender_audience_json` |
| Vocabulary: products injected into architecture prompt | Unit | Rendered prompt contains canonical product names from vocabulary |




### 9. Out of Scope (Phase 1)

- **Demo ingest** — `ProductType=Demo` items (~30 rows) are excluded from Phase 1. These may be migrating off OSSPA into Interact Hub; if they remain, they can be introduced in a later phase.
- **Interactive Experience ingest** — IE items (`ProductType=IE`) are excluded from Phase 1 entirely. The one IE in `showInCatalog=TRUE` (`ppid=64`) is not ingested. IE content requires a different analysis approach (Arcade embeds, thin adoc) and is a future spec.
- **Retirement scoring** — RHDP reporting is Babylon-keyed; OSSPA items do not get performance scores in Phase 1.
- **Workload / infrastructure facets** — not applicable to non-hands-on content.
- **Diagram image OCR** — image URLs stored but not analyzed.
- **Writing back to OSSPA GitLab** — read-only.
- **Interactive Labs performance channel** — separate spec.
- **Dedicated model *selection*** — the config lever ships in Phase 1 (`osspa_analysis_model`, Section 5), defaulting to the existing Showroom-analysis model so behaviour is unchanged. What is deferred is the *decision*: which model architecture analysis should actually run on (frontier now vs. open-source later, cost/quality trade-offs) needs a team discussion, including Ashok on open-source options, backed by an eval on real architecture content. Deferred to Phase 2.
- **Overlap detection** — architecture items are excluded from `generate_overlap_candidates`. The current overlap system is negative matching (duplicate detection within Babylon) and is still being refined. Cross-type "good similarity" (related content recommendations) is a separate future feature.
- **Advisor integration** — surfacing architecture items in the Advisor chat rationale flow is deferred. Items land in embeddings and are retrievable by vector search, but the Advisor UI (recommendation cards, rationale formatting, CTA rendering) ships separately. **Browse is *not* deferred** — basic catalog browsing with a Content Format filter is a Phase 1 deliverable, see 3j.
- **Advanced Browse filters** — additional filter dimensions beyond the Phase 1 set (see 3j) are future work. Candidates: recommender audience, platform, difficulty.
- **Curator editing beyond tags and notes** — the curator drawer's duration override, content-path override and Showroom URL override are Babylon-only and stay hidden for architecture items (3j, Curator controls). Architecture-specific curation (e.g. overriding the Architecture Center URL, 3h#9) is future work.



## Relationship to Other Specs

- **RHDPCD-359 (Generalized Content Model)** — prerequisite; deployed. This spec creates the tables that 359 planned but did not create.
- **Controlled vocabulary ([RHDPCD-507](2026-08-10-controlled-vocabulary-design.md))** — assumed implemented. This spec consumes it: product prompt injection, post-analysis normalization, `recommender_audience_json` field, `read_through` verb set.
- **Overlap analysis** — architecture items are **excluded** from overlap detection in Phase 1. The current overlap system is tuned for negative matching (duplicate detection within Babylon) and is still being iterated on. Adding a second content type would complicate that work. Cross-type similarity (an architecture and a hands-on lab covering the same product) is **good similarity**, not overlap — that's a different feature (content recommendations / "related content") with different UX, not part of the overlap pipeline. `generate_overlap_candidates` must filter `source = 'babylon'` to exclude architecture items until a deliberate cross-type or same-type-architecture overlap strategy is designed.
- **Interactive Experience ingest** — future spec. Phase 1 excludes all `ProductType=IE` rows.
- **Browse/Advisor UI *redesign*** — Phase 2. Phase 1 adds architecture cards and the Content Format filter to the **existing** Browse page (3j); a broader redesign to accommodate several new content types at once is separate.



## Next Steps

1. **Review and approve this spec** — share with the team; confirm scope (PA/PA,VP/SP only; Demo & IE deferred; ingest-all with `prod`/`dev` status tagging using Babylon's vocabulary) and the two new tables (`portfolio_architectures`, `architecture_analysis`) are acceptable before implementation begins.
2. **Write implementation plan** — once approved, create a step-by-step implementation plan (`docs/superpowers/plans/`) that breaks this spec into ordered, independently-testable tasks. Key tasks will include: schema additions (including `recommender_audience_json`, the `content_entities.status` column and its backfill), `osspa_sync.py` service, LLM prompt with vocabulary product injection, vocabulary normalization pass, worker/CLI/API wiring, the `bi.stage` → `ce.status` predicate swap, Browse Content Format filter, source-aware detail route, and the architecture card template (3j), and the Babylon safety fix. Browse integration (3j) is in scope; Advisor integration is deferred — see Out of Scope.)
3. **Verify Babylon retirement safety** — before writing any new code, confirm that the existing Babylon retire query (`retire_removed_items()`, to be renamed `retire_missing_babylon()`) already filters by `source='babylon'`. If not, that fix ships first as it is a data-safety prerequisite. Fold the rename into the same change.
4. **Pilot sync on dev** — after implementation, run `rcars osspa sync` on the dev environment against the live CSV and examples repo. Spot-check 3–5 analyzed items (one PA, one SP, one PA,VP) for summary quality and vector-search retrievability before enabling the nightly pipeline step.
5. **Phase 2 — Interactive Experience ingest** — separate spec and implementation cycle after Phase 1 is stable.

