# Portfolio Architecture Ingest — Design Spec

**Jira:** [RHDPCD-28](https://redhat.atlassian.net/browse/RHDPCD-28) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Date:** 2026-07-30
**Status:** Design
**Author:** M. Rudisill
**Depends on:** RHDPCD-359 (Generalized Content Model — deployed)

## Problem

RCARS can only recommend Babylon Showroom content. Red Hat's Architecture Center publishes ~70 curated assets — reference architectures and demos — that cover the same products and use cases that RHDP labs cover, but are not hands-on environments. Sales teams and learners who need a conceptual overview rather than a provisioned lab get nothing from RCARS today.

These assets come from OSSPA GitLab, are public, and have rich AsciiDoc content. The generalized content model (RHDPCD-359) deliberately left room for exactly this source: `portfolio_architectures` and `architecture_analysis` tables are defined as illustrative placeholders, ready to be created by this spec.

## Approach

Ingest the ~68 Architecture Center assets that pass the Phase 1 inclusion filter as first-class RCARS content entities. Each item gets a row in `content_entities` (the universal card), a row in `portfolio_architectures` (OSSPA-specific metadata), and after LLM analysis a row in `architecture_analysis`. Embeddings land in the shared `embeddings` table, making these items immediately searchable by Advisor and Browse alongside Babylon labs.

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
| `islive`                   | Must be `TRUE` for the row to exist in RCARS                                               |
| `showInCatalog`            | **Inclusion gate** — only `TRUE` rows are ingested                                         |
| `Summary`                  | Short description — seed for `content_entities.summary` before analysis                    |
| `metaDesc` / `metaKeyword` | Extra text for LLM prompt context                                                          |
| `Vertical`                 | Industry verticals → `portfolio_architectures.verticals`                                   |
| `Solutions`                | Solution areas → `portfolio_architectures.solutions`                                       |
| `Product`                  | Red Hat products mentioned → `content_entities.products_json` (initial)                    |
| `ProductType`              | `PA`, `PA,VP`, `Demo`, `SP`, `IE` → drives `content_type` mapping                          |
| `Image1Url`                | Relative image path under examples repo → `portfolio_architectures.image_url`              |
| `DetailPage`               | Relative `.adoc` path in examples repo — **required for inclusion**                        |
| `externalUrl`              | Not used — all 68 Phase 1 items have an empty `externalUrl`; CTA constructed from `PAName` |


Raw CSV URL: `https://gitlab.com/osspa/osspa-site/-/raw/main/src/app/ArchitectureList/PAList.csv`

### Inclusion Filter

```text
showInCatalog = TRUE
AND islive = TRUE
AND DetailPage is non-empty
AND DetailPage ends with ".adoc"
AND ProductType NOT IN ('IE')
```

This yields ~68 items (as of 2026-07): PA (34), Demo (30), PA,VP (3), SP (2). The remaining 2 exclusions from the 70 `showInCatalog=TRUE` rows are:

- `ppid=144` — empty `DetailPage` (links out to redhat.com instead)
- `ppid=64` — `ProductType=IE` (Interactive Experience — excluded from Phase 1)

`showInCatalog` — not `islive` — is the primary gate. The Architecture Center curates these 70; RCARS follows that curation for non-IE content.

### ProductType → content_type mapping


| ProductType   | `content_type` in RCARS |
| ------------- | ----------------------- |
| `PA`          | `architecture`          |
| `PA,VP`       | `architecture`          |
| `SP`          | `architecture`          |
| `Demo`        | `architecture`          |
| `IE`          | **excluded — Phase 2**  |
| anything else | `architecture`          |


All Phase 1 OSSPA items are `is_hands_on = FALSE` — they are reference/read-through content, not provisioned environments.

> **OSSPA Demo ≠ Babylon demo.** Babylon items with `content_type='demo'` are hands-on provisioned environments with Showroom content. OSSPA items with `ProductType=Demo` are Architecture Center reference demos — read-through AsciiDoc (or thin Arcade wrappers), not live environments. They map to `content_type='architecture'` to reflect this. The `source` field (`portfolio_arch` vs `babylon`) is the authoritative disambiguator.



### DetailPage path resolution

The examples repo has a flat root plus one `IE/` subdirectory:


| DetailPage value                                        | Resolved location      |
| ------------------------------------------------------- | ---------------------- |
| `rhacs-multitenant.adoc`                                | repo root              |
| `mockup/cloud-sovereignty.adoc`                         | nested path under repo |
| `IE/omnicloud-as-a-service-interactive-experience.adoc` | `IE/` subdirectory     |


**Safety rules:** Reject any path containing `..` or starting with `/`. Normalize to forward slashes. Join under clone root only.

Clone URL: `https://gitlab.com/osspa/portfolio-architecture-examples.git`
Default ref: `main`

## Design



### 1. Identity and Naming

`content_id` for each item: `pa:{ppid}`

Examples (all pass the inclusion filter):

- `pa:275` — Multitenant Setup for RHACS (PA)
- `pa:274` — Protect VMs with Veeam Kasten (Demo)
- `pa:273` — Open Sovereign AI Cloud with Red Hat and Netris (PA)

Excluded examples:

- `ppid=144` — empty `DetailPage`, excluded
- `ppid=64` — `ProductType=IE`, excluded (Phase 2)
- `ppid=272` — `showInCatalog=FALSE`, excluded

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
    is_live             BOOLEAN DEFAULT TRUE,
    last_manifest_sync  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pa_ppid ON portfolio_architectures(ppid);
CREATE INDEX IF NOT EXISTS idx_pa_is_live ON portfolio_architectures(is_live);
```

This is precisely the illustrative table from RHDPCD-359 — no additions needed for Phase 1.


| Column               | Source                                                       | Notes                                     |
| -------------------- | ------------------------------------------------------------ | ----------------------------------------- |
| `content_id`         | `pa:{ppid}`                                                  | FK to content_entities                    |
| `ppid`               | CSV `ppid`                                                   | Numeric, globally unique in OSSPA         |
| `pa_name`            | CSV `PAName`                                                 | Slug for diagnostics                      |
| `verticals`          | CSV `Vertical` (comma-split)                                 | Industry verticals                        |
| `solutions`          | CSV `Solutions` (comma-split)                                | Solution areas                            |
| `detail_page`        | CSV `DetailPage`                                             | Relative adoc path in examples repo       |
| `image_url`          | CSV `Image1Url`                                              | Relative image path in examples repo      |
| `is_live`            | `TRUE` only when both `islive=TRUE` AND `showInCatalog=TRUE` | FALSE triggers soft-retire on next sync   |
| `last_manifest_sync` | Set on each sync                                             | When this row was last seen in a live CSV |




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
| `product_type`        | Raw CSV ProductType (`PA`, `Demo`, `IE`, etc.) — stored for diagnostics        |


`content_hash`: SHA-256 of the DetailPage adoc body only. CSV-only changes update catalog/extension fields but do not force re-analysis unless `--force` is passed.

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
| `filter_catalog_rows(rows) -> list[dict]`                                         | Apply inclusion filter — `showInCatalog`, `islive`, `.adoc` DetailPage, `ProductType NOT IN ('IE')`        |
| `upsert_osspa_item(db, row) -> str`                                               | Write `content_entities` + `portfolio_architectures` for one CSV row; return `content_id`                  |
| `retire_missing_osspa(db, active_content_ids) -> int`                             | Soft-retire `source='portfolio_arch'` items not in the current live set                                    |
| `clone_examples_repo(settings) -> Path`                                           | Shallow clone or fetch portfolio-architecture-examples at configured ref                                   |
| `read_detail_adoc(clone_path, detail_page) -> str`                                | Safe path join; read `.adoc` text; strip `++++` passthrough blocks                                         |
| `analyze_architecture_item(db, content_id, adoc_text, csv_row, settings) -> dict` | Hash check → LLM → write `architecture_analysis` + denormalize to `content_entities` + generate embeddings |
| `run_osspa_sync(ctx, job_id, force=False) -> dict`                                | Orchestrator: CSV → upsert → retire → clone → analyze; return stats                                        |




#### 3b. Orchestrator flow

```text
1. Fetch and parse PAList.csv
2. Apply inclusion filter → active_rows (~68 items)
3. Guard: if active_rows is empty → abort (do not wipe existing items)
4. For each row → upsert_osspa_item:
       content_entities (ON CONFLICT DO UPDATE — card fields)
       portfolio_architectures (ON CONFLICT DO UPDATE — extension fields)
5. retire_missing_osspa: soft-retire source='portfolio_arch' items
   with content_id NOT IN active content_ids
6. Ensure examples repo clone at configured ref; record HEAD SHA
7. For each active item needing analysis:
       a. Resolve DetailPage under clone root (safe join)
       b. Read adoc text; strip ++++...++++ passthrough blocks
       c. Compute content_hash (SHA-256 of adoc body)
       d. If hash unchanged AND architecture_analysis row exists AND not force → skip
       e. Else: LLM analyze → write architecture_analysis
              → denormalize summary/products/topics/audience/difficulty to content_entities
              → clear old embeddings for this content_id
              → store summary embedding (embed_type='summary')
              → store per-section embeddings (embed_type='section') from major adoc sections
8. Return stats: upserted, retired, analyzed, skipped, failed
```



#### 3c. adoc reader

`read_detail_adoc` is **not** the Showroom reader. Key differences:

- Showroom uses Antora modules + `nav.adoc`; OSSPA uses a single flat `.adoc` per item
- Strip `++++` / `<!--ARCADE EMBED ... -->` HTML passthrough blocks — they add no text signal
- Keep all AsciiDoc section headings and prose
- Do not recurse; do not follow `include::` directives (not used in examples repo)



#### 3d. LLM analysis prompt

Reuse the structured JSON output format from Showroom analysis (same `parse_analysis_response()` helper). Adapt the prompt:

- Provide CSV metadata as trusted context: `Summary`, `Product`, `Solutions`, `Vertical`, `metaKeyword`
- Provide adoc prose as content body
- Request: `summary`, `products`, `topics`, `audience`, `difficulty`, `solution_areas`, `use_cases`, `key_components`
- Instruct the LLM to draw from both CSV metadata and adoc prose; prefer adoc for specifics
- For thin content (Demo/IE adocs with mostly Arcade embeds and a short intro): the prompt must produce a useful summary from CSV metadata alone — the adoc intro may only be 2-3 sentences
- Do **not** request `modules` or `learning_objectives` — these are architecture docs, not labs

Prompt file: `src/api/rcars/prompts/architecture_analyze.txt`

#### 3e. Embeddings

Two embedding types per item:


| `embed_type` | `content_text`                                                | When                                                            |
| ------------ | ------------------------------------------------------------- | --------------------------------------------------------------- |
| `summary`    | `"Reference architecture: {summary}"`                         | Always — drives Advisor retrieval                               |
| `section`    | `"Reference architecture: {section_heading}\n{section_text}"` | One per major `==` section in adoc, if section text > 100 chars |


All embeddings: `source='portfolio_arch'`, `content_type` from the mapping table in this spec.

The type prefix `"Reference architecture: "` places these in slightly different vector space from `"Hands-on lab: "` and `"Environment: "` prefixes used by Babylon items.

#### 3f. Babylon safety

The Babylon CRD scan calls `retire_removed_items()` on rows that disappear from Babylon. This must only apply to `source='babylon'` rows. Confirm (and fix if needed) that the retirement query filters by source:

```sql
-- Only retire Babylon items based on CRD disappearance
WHERE source = 'babylon' AND content_id NOT IN (...)
```

OSSPA lifecycle is owned exclusively by `retire_missing_osspa()` in this service.

### 4. Worker Integration

**Queue:** `arq:queue:scan` (same as Babylon scan worker — reuses existing scan worker process)

**Job type:** `osspa_sync`

**Entry points:**


| Entry                           | Details                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| Nightly maintenance pipeline    | New step in `run_maintenance_pipeline` after catalog refresh, before similarity recompute |
| `POST /api/v1/admin/sync-osspa` | Admin-only endpoint; enqueues job; returns `{job_id}`                                     |
| `rcars osspa sync [--force]`    | CLI command; synchronous; `--force` bypasses hash check                                   |




### 5. Configuration

All settings in `src/api/rcars/config.py` using existing `RCARS_` prefix pattern:


| Setting                   | Default                                                        | Purpose                     |
| ------------------------- | -------------------------------------------------------------- | --------------------------- |
| `osspa_sync_enabled`      | `true`                                                         | Gates nightly pipeline step |
| `osspa_palist_url`        | PAList.csv raw URL                                             | Inventory source            |
| `osspa_examples_repo_url` | `https://gitlab.com/osspa/portfolio-architecture-examples.git` | Content repo                |
| `osspa_examples_ref`      | `main`                                                         | Git ref to clone/fetch      |
| `osspa_clone_dir`         | `{clone_dir}/osspa-examples`                                   | Working directory           |


No auth tokens required — both repos are public. If GitLab rate-limits the clone, an optional `RCARS_GITLAB_TOKEN` can be wired later.

### 6. Advisor and Browse Integration



#### 6a. Advisor

OSSPA items appear in Advisor automatically once they have `summary` embeddings. Vector search already retrieves from `embeddings` filtered by `retired_at IS NULL` on `content_entities` — no query changes needed.

Rationale generation (`rationale.py`) currently branches on `lab`/`demo`/`sandbox`. Add an `architecture` branch:

```python
elif c.content_type == "architecture":
    # Read from architecture_analysis
    analysis = db.get_architecture_analysis(content_id)
    # Format: solution areas, use cases, key components
```

Rec card CTA: "View architecture" — always links to the Architecture Center detail page, constructed from `pa_name`:

```
https://www.redhat.com/architect/portfolio/detail/{pa_name}/
```

Example: `pa_name = 275-rhacs-multitenant` → `https://www.redhat.com/architect/portfolio/detail/275-rhacs-multitenant/`

All 68 Phase 1 items have an empty `externalUrl` in the CSV, so no stored URL is needed — `pa_name` in `portfolio_architectures` is always the source. The URL is constructed at display time, not stored.

#### 6b. Browse

OSSPA items appear in Browse automatically alongside Babylon items (same `list_content_entities_filtered` query). Additional Browse work when content types ship:

- Content type filter: `architecture` added to type filter UI
- OSSPA-specific Browse card: no Showroom link, no "Start lab" button; "View architecture" CTA instead
- Curator controls (duration, enrichment review) hidden or no-op for `source='portfolio_arch'`



#### 6c. Content Similarity

`compute_content_similarity` already handles cross-source `related` pairs. OSSPA items produce `related` pairs with Babylon items once embeddings exist (the similarity query is already written for this). No pipeline changes needed.

### 7. Lifecycle


| Event                                                    | Result                                                                         |
| -------------------------------------------------------- | ------------------------------------------------------------------------------ |
| New row appears with `showInCatalog=TRUE`                | Upserted on next sync; analysis runs                                           |
| `islive` flips FALSE                                     | Row no longer passes inclusion filter → `retire_missing_osspa` soft-retires it |
| `showInCatalog` flips FALSE                              | Same — no longer in active set → soft-retired                                  |
| Row removed from CSV entirely                            | Same — not in active set → soft-retired                                        |
| Content of DetailPage `.adoc` changes                    | `content_hash` mismatch → re-analyzed on next sync                             |
| CSV metadata changes (Summary, Products, etc.)           | Card fields updated on upsert; re-analysis not forced unless adoc also changed |
| Previously retired row reappears (`islive` back to TRUE) | Upserted with `retired_at = NULL` on next sync; treated as new                 |




### 8. Failure and Edge Cases


| Case                                          | Behavior                                                                                                                                      |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| CSV fetch fails                               | Abort sync; leave existing OSSPA rows intact; job fails                                                                                       |
| Active set is empty after filtering           | Abort sync (safety guard — never wipe all items on a bad CSV)                                                                                 |
| DetailPage file missing from clone            | Upsert catalog row; mark `is_stale=TRUE` on analysis record; log error; continue                                                              |
| LLM analysis fails                            | Same error patterns as Showroom scan failure; scan_status not set (architecture_analysis has no scan_status — log error, skip item, continue) |
| `ProductType=PA,VP`                           | Maps to `architecture`; `pa_name` slug uses full PAName                                                                                       |
| `Product` column empty (common for IE/Demo)   | `products_json` seeded empty; LLM fills from adoc + other CSV fields                                                                          |
| Duplicate `ppid` in CSV                       | Should not happen; log warning; last row wins                                                                                                 |
| Path traversal in DetailPage (`..`, absolute) | Skip row; log warning                                                                                                                         |




### 9. Testing


| Test                                                                 | Type        | Assertion                                              |
| -------------------------------------------------------------------- | ----------- | ------------------------------------------------------ |
| Inclusion filter: `showInCatalog=FALSE` excluded                     | Unit        | Row not in active set                                  |
| Inclusion filter: `islive=FALSE` excluded                            | Unit        | Row not in active set                                  |
| Inclusion filter: `DetailPage` without `.adoc` excluded              | Unit        | Row not in active set                                  |
| `content_id` format: `pa:{ppid}`                                     | Unit        | Correct for PA, Demo, and PA,VP rows                   |
| ProductType mapping: Demo → `architecture`, IE → excluded            | Unit        | IE rows not in active set; Demo maps to `architecture` |
| Path resolution: root, nested, IE/                                   | Unit        | Correct path; traversal rejected                       |
| Upsert: writes both `content_entities` and `portfolio_architectures` | Integration | Both rows exist after sync                             |
| Soft-retire: OSSPA item missing from next sync                       | Integration | `retired_at` set                                       |
| Babylon safety: Babylon CRD scan does not retire OSSPA items         | Integration | OSSPA row survives Babylon scan run                    |
| Analysis: produces summary embedding                                 | Integration | `embeddings` row with `embed_type='summary'`           |
| Empty active set guard                                               | Unit        | Sync aborts; no retirements                            |
| Advisor: OSSPA item returned for matching query                      | Integration | Candidate has `source='portfolio_arch'`                |




### 10. Out of Scope (Phase 1)

- **Interactive Experience ingest** — IE items (`ProductType=IE`) are excluded from Phase 1 entirely. The one IE in `showInCatalog=TRUE` (`ppid=64`) is not ingested. IE content requires a different analysis approach (Arcade embeds, thin adoc) and is a future spec.
- **Retirement scoring** — RHDP reporting is Babylon-keyed; OSSPA items do not get performance scores in Phase 1.
- **Workload / infrastructure facets** — not applicable to non-hands-on content.
- **Diagram image OCR** — image URLs stored but not analyzed.
- **Writing back to OSSPA GitLab** — read-only.
- **Interactive Labs performance channel** — separate spec.
- **Full Browse UI for architecture content type** — Phase 2, ships alongside actual items.



## Relationship to Other Specs

- **RHDPCD-359 (Generalized Content Model)** — prerequisite; deployed. This spec creates the tables that 359 left as illustrative placeholders.
- **Overlap analysis redesign** — `content_similarity` `related` pairs between Babylon and OSSPA will populate automatically once embeddings exist. No overlap spec changes needed.
- **Interactive Experience ingest** — future spec. Phase 1 excludes all `ProductType=IE` rows.
- **Browse/Advisor UI redesign** — Phase 2; architecture content type cards and filters ship alongside new content types.



## Next Steps

1. **Review and approve this spec** — share with the team; confirm scope (68 items, PA/Demo/SP only) and the two new tables (`portfolio_architectures`, `architecture_analysis`) are acceptable before implementation begins.
2. **Write implementation plan** — once approved, create a step-by-step implementation plan (`docs/superpowers/plans/`) that breaks this spec into ordered, independently-testable tasks. Key tasks will include: schema additions, `osspa_sync.py` service, LLM prompt, worker/CLI/API wiring, Babylon safety fix, and Browse/Advisor integration.
3. **Verify Babylon retirement safety** — before writing any new code, confirm that the existing `retire_removed_items()` query in the codebase already filters by `source='babylon'`. If not, that fix ships first as it is a data-safety prerequisite.
4. **Pilot sync on dev** — after implementation, run `rcars osspa sync` on the dev environment against the live CSV and examples repo. Spot-check 3–5 analyzed items (one PA, one Demo, one PA,VP) for summary quality and Advisor retrievability before enabling the nightly pipeline step.
5. **Phase 2 — Interactive Experience ingest** — separate spec and implementation cycle after Phase 1 is stable.

