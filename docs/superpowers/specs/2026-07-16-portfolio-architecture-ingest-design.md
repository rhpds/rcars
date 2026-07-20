# Portfolio Architecture Ingest — Design Spec

**Date:** 2026-07-16  
**Status:** Draft, pending review  
**Scope:** Phase 1 — all live OSSPA assets (`islive=TRUE`) from PAList → DetailPage `.adoc` in portfolio-architecture-examples (root **or** `IE/`)  
**Related backlog:** Portfolio Architecture ingest from OSSPA GitLab (RHDPCD-25)

## Overview

Ingest Red Hat Architecture Center assets from OSSPA into RCARS so Advisor and Browse can recommend them alongside Babylon Showroom labs.

Data comes from two public GitLab sources:

1. **Inventory** — [`PAList.csv`](https://gitlab.com/osspa/osspa-site/-/blob/main/src/app/ArchitectureList/PAList.csv) in [`osspa/osspa-site`](https://gitlab.com/osspa/osspa-site) (which assets exist, `islive`, metadata, and the `DetailPage` pointer).
2. **Content** — AsciiDoc bodies in [`osspa/portfolio-architecture-examples`](https://gitlab.com/osspa/portfolio-architecture-examples), including the [`IE/`](https://gitlab.com/osspa/portfolio-architecture-examples/-/tree/main/IE) tree. The CSV `DetailPage` column is the path into this repo.

RCARS does not scrape the Architecture Center UI. The CSV is the system of record for **which rows are live**; `DetailPage` is the system of record for **which `.adoc` to pull**.

### Goals

1. **Catalog presence** — Every live row with a resolvable `DetailPage` appears as a first-class RCARS item (Browse + detail).
2. **Content from DetailPage** — Sync clones [`portfolio-architecture-examples`](https://gitlab.com/osspa/portfolio-architecture-examples) once and reads the file at `DetailPage` whether it is a root/nested PA adoc (e.g. `rhacs-multitenant.adoc`) or an IE path (e.g. `IE/omnicloud-as-a-service-interactive-experience.adoc`).
3. **Semantic retrieval** — Analyzed/embedded content so Advisor can recommend these assets.
4. **Safe coexistence** — OSSPA items survive Babylon catalog refresh (must not be soft-retired as “disappeared from CRDs”).
5. **Repeatable sync** — Nightly (or on-demand) job upserts from CSV + git; orphans from prior syncs are retired.

### Non-Goals (Phase 1)

- **Rows with `islive=FALSE`** — Never ingested; if previously ingested, soft-retired on next sync.
- **Rows with empty / non-`.adoc` `DetailPage`** — Skipped (catalog upsert optional as failed; default: skip entirely).
- **Retirement scoring / reporting metrics** — RHDP reporting is Babylon-keyed; OSSPA items do not get retirement scores in Phase 1.
- **Workload / infrastructure faceting** — agDv2-only; not applicable to OSSPA.
- **Diagram image OCR / drawio analysis** — Text from `.adoc` (+ CSV metadata) only; image URLs may be stored for display but not analyzed.
- **Writing back to OSSPA** — Read-only ingest.
- **Fetching external interactive runtimes** — For IE rows, we ingest the `DetailPage` adoc (and CSV text), not the embedded demo player / redirected experience binary.

---

## 1. Source Model

### 1a. PAList.csv columns (relevant)

| Column | Use |
|--------|-----|
| `ppid` | Numeric id; diagnostics |
| `PAName` | Slug id (e.g. `275-rhacs-multitenant`, `272-omnicloud-as-a-service-interactive-experience`) |
| `Heading` | Display name |
| `islive` | **Primary gate** — must be `TRUE` |
| `showInCatalog` | Stored as metadata / Browse signal only — **not** an inclusion filter |
| `Summary` | Short description → `catalog_items.description` / analysis seed |
| `metaDesc` / `metaKeyword` | Extra text for embedding / keywords |
| `Vertical` / `Solutions` / `Platform` / `Product` | Facets → products, topics, keywords |
| `ProductType` | Labels content class (`PA`, `IE`, `Demo`, …) — **not** an inclusion filter |
| `Image1Url` | Relative image path under examples repo |
| `DetailPage` | **Content pointer** — relative `.adoc` path in examples repo |
| `Status` | Prefer Active; archived live rows still follow `islive` (if `islive=FALSE` they are out) |
| `externalUrl` / `isRedirected` | Stored for CTA when present (common on IE) |

Approximate live corpus (as of 2026-07): **~252** rows with `islive=TRUE` (mix of PA, IE, Demo, etc.). Exact count after DetailPage validation will be slightly lower if some live rows lack a usable `.adoc` path.

### 1b. Inclusion filter (Phase 1)

```text
islive = TRUE
AND DetailPage is non-empty
AND DetailPage ends with ".adoc"
```

That is the full inclusion rule. **Do not** require `showInCatalog=TRUE`. **Do not** restrict to `ProductType=PA`.

**Path resolution** (always against one clone of portfolio-architecture-examples @ configured ref):

| `DetailPage` example | Resolves to |
|----------------------|-------------|
| `rhacs-multitenant.adoc` | repo root adoc ([examples repo](https://gitlab.com/osspa/portfolio-architecture-examples)) |
| `mockup/cloud-sovereignty.adoc` | nested path under repo |
| `IE/omnicloud-as-a-service-interactive-experience.adoc` | file under [`IE/`](https://gitlab.com/osspa/portfolio-architecture-examples/-/tree/main/IE) |

Reject path traversal (`..`, absolute paths). Normalize to forward slashes; join under clone root only.

### 1c. Content repo layout

Unlike Showrooms (Antora `content/modules/ROOT/pages/` + `nav.adoc`), examples use a **flat / lightly nested** layout plus an **`IE/`** directory for interactive-experience adocs:

- Root PA/Demo: `rhacs-multitenant.adoc`
- Nested: `mockup/cloud-sovereignty.adoc`
- IE: `IE/<name>-interactive-experience.adoc`

Images live under `images/` in the same repo.

Clone URL (HTTPS): `https://gitlab.com/osspa/portfolio-architecture-examples.git`  
Default ref: `main`

CSV raw URL:  
`https://gitlab.com/osspa/osspa-site/-/raw/main/src/app/ArchitectureList/PAList.csv`

---

## 2. Approaches Considered

| Approach | Pros | Cons |
|----------|------|------|
| **A. Reuse `catalog_items` + `showroom_analysis` + `embeddings` with `source=osspa`** | Advisor/Browse/overlap work with minimal query changes; one corpus | Table name `showroom_analysis` is a misnomer; need source-aware retirement |
| **B. New `architecture_items` + `architecture_analysis` tables** | Clean separation | Duplicate vector search, Browse, Advisor paths; large surface area |
| **C. CSV-only metadata (no DetailPage adoc)** | Fast | Ignores user requirement to pull from DetailPage; weak for rich PA adocs |

**Decision: Approach A.** Live OSSPA rows are another content class in the same recommendation corpus. Content body always comes from `DetailPage` in the examples repo. Protect them via an explicit `source` column and retirement rules.

---

## 3. Data Layer

### 3a. Schema changes

**`catalog_items` — new columns:**

```sql
ALTER TABLE catalog_items
    ADD COLUMN source TEXT NOT NULL DEFAULT 'babylon',
    -- 'babylon' | 'osspa'
    ADD COLUMN external_id TEXT,
    -- OSSPA: PAName for upsert/debug
    ADD COLUMN content_url TEXT,
    -- Public CTA (Architecture Center / externalUrl / GitLab blob)
    ADD COLUMN detail_page TEXT;
    -- Relative path in examples repo (CSV DetailPage) — required for osspa
```

Constraints / indexes:

```sql
CREATE INDEX idx_catalog_items_source ON catalog_items(source);
CREATE UNIQUE INDEX uq_catalog_items_source_external_id
    ON catalog_items(source, external_id)
    WHERE external_id IS NOT NULL;
```

**`ci_name` convention (stable PK):**

```text
osspa.{product_type_slug}.{PAName}
```

Examples:

- `osspa.pa.275-rhacs-multitenant`
- `osspa.ie.272-omnicloud-as-a-service-interactive-experience`
- `osspa.demo.274-protect-your-virtual-machines-on-red-hat-openshift-with-veeam-kasten`

`product_type_slug`: lowercase primary token from `ProductType` before comma (`PA`→`pa`, `IE`→`ie`, `Demo`→`demo`, `PA,VP`→`pa`). Unknown → `asset`.

- Always `stage = 'prod'`, `is_prod = TRUE`, `is_published = FALSE`
- `catalog_namespace = 'osspa'`
- `category` = human label from ProductType (`Architecture`, `Interactive Experience`, `Demo`, …)
- `showroom_url` = examples repo HTTPS URL (clone target) — same for all OSSPA rows
- `showroom_ref` = configured ref (default `main`)
- `detail_page` = exact CSV `DetailPage` (e.g. `IE/foo.adoc` or `bar.adoc`)
- `content_path` unused for Antora; reader uses `detail_page` relative to clone root
- `product` = first product from CSV `Product` (comma-split) or full string
- `keywords` = union of `metaKeyword`, `Solutions`, `Vertical` tokens
- `description` = CSV `Summary`
- `icon_url` = absolute URL to `Image1Url` under examples repo raw path when present
- `retired_at` = NULL while in live sync set; set when row no longer passes inclusion filter

**`showroom_analysis` — reuse as-is:**

- `content_type` from ProductType mapping:
  - `PA` / `PA,VP` → `architecture`
  - `IE` → `interactive_experience`
  - `Demo` → `demo` (or `architecture_demo` if we need to distinguish Showroom demos — prefer `demo` with `source=osspa` for disambiguation)
  - other → `osspa_other` or map conservatively to `architecture`
- Summary, products, topics, audience, use_cases from LLM (seeded with CSV metadata)
- For **thin IE adocs** (intro + iframe + links): prompt must weight CSV `Summary` / `metaDesc` / keywords heavily; still **read the DetailPage file** so any prose in-repo is included
- `content_hash` = hash of the DetailPage adoc body (+ optional normalized CSV summary blob if we want CSV-only edits to retrigger — Phase 1: **adoc body only**; CSV-only changes update catalog fields without forced re-embed unless `--force`)
- `last_repo_commit` = examples repo HEAD SHA at analyze time

**`embeddings` — reuse:**

- `embed_type = 'ci_summary'` required for Advisor
- Embedding input text = analysis summary (which already incorporates CSV + adoc)

### 3b. Babylon retirement safety (critical)

Today `retire_removed_items()` retires **any** `catalog_items` row missing from the Babylon scan set. That would wipe OSSPA items every night.

**Change:** Only consider Babylon-sourced rows for CRD disappearance retirement:

```text
retire candidates = catalog_items WHERE source = 'babylon' (or source IS NULL for backfill)
  AND ci_name NOT IN current_babylon_scan_set
```

OSSPA lifecycle is owned exclusively by the OSSPA sync job (see §4): soft-retire when `islive` flips false or the row disappears / fails DetailPage validation.

Alembic: backfill existing rows `source = 'babylon'` where NULL after adding column with default.

---

## 4. Sync & Analysis Pipeline

### 4a. New service module

`src/api/rcars/services/osspa_sync.py` (name flexible):

| Function | Role |
|----------|------|
| `fetch_palist_csv(settings) -> list[dict]` | HTTP GET CSV, parse, normalize booleans |
| `filter_live_detail_rows(rows) -> list[dict]` | `islive` + valid `DetailPage` |
| `resolve_detail_page(clone_path, detail_page) -> Path` | Safe join under clone; root or `IE/` |
| `upsert_osspa_catalog(db, rows) -> stats` | Map CSV → `catalog_items` upserts |
| `retire_missing_osspa(db, active_ci_names) -> list` | Soft-retire `source=osspa` not in set |
| `clone_examples_repo(...)` | Shallow clone / fetch of examples repo |
| `read_detail_adoc(clone_path, detail_page) -> str` | Flat-path adoc reader (not Antora) |
| `analyze_osspa_item(...)` | Hash → LLM structured JSON → embeddings |
| `run_osspa_sync(db, settings) -> dict` | Orchestrator |

### 4b. Orchestrator flow

```text
1. Fetch + parse PAList.csv
2. Filter: islive=TRUE AND DetailPage ends with .adoc
3. Upsert catalog_items (source=osspa) from filtered rows
4. Soft-retire source=osspa items missing from filtered set
   (includes formerly live rows now islive=FALSE)
5. Ensure examples repo clone at configured ref; record HEAD SHA
6. For each active row needing analysis:
     - Resolve DetailPage under clone (root or IE/)
     - Read that single .adoc
     - If content_hash unchanged and not forced → skip
     - Else LLM analyze (CSV metadata + adoc text) + store
       showroom_analysis + embeddings
7. Return counts: upserted, retired, analyzed, skipped, failed
   (optionally break down by ProductType / IE vs non-IE path)
```

**Needs analysis when:** no `showroom_analysis` row, `is_stale=TRUE`, `scan_status != success`, or DetailPage content_hash changed.

**Stale detection:** Per-file content hash of `DetailPage` (not whole-repo HEAD alone), so unrelated commits do not force full re-analyze. Still store HEAD for diagnostics.

### 4c. Adoc reader differences vs Showroom

| Showroom | OSSPA (via DetailPage) |
|----------|-------------------------|
| Antora pages + `nav.adoc` | **Single file** at `DetailPage` |
| Fixed pages directory | Root, nested, or [`IE/`](https://gitlab.com/osspa/portfolio-architecture-examples/-/tree/main/IE) |
| Boilerplate filename filters | Strip noisy `++++` passthrough / empty iframe shells for IE when hashing/prompting |
| Sibling SHA dedup | One CI ↔ one DetailPage; no sibling propagation |

Do **not** call `read_showroom_content()`. Add `read_detail_adoc(clone_path, detail_page)`.

### 4d. LLM analysis prompt

Reuse structured JSON shape from Showroom analysis where possible, with adaptations:

- Set `content_type` from ProductType mapping (§3a)
- Emphasize use cases, products, platforms, solution patterns
- Always include CSV `Summary`, `Product`, `Solutions`, `Vertical`, `metaKeyword` as trusted metadata
- For paths under `IE/`: note that the adoc may be a thin wrapper around an interactive experience; do not invent lab modules; ground claims in CSV + adoc text only
- `estimated_duration_min` may be null/0
- `format_suitability` — leave sparse or extend sanitizer; do not force Showroom-only keys

### 4e. Worker / CLI / API entry points

| Entry | Behavior |
|-------|----------|
| Nightly pipeline | New step after catalog refresh: `run_osspa_sync` if enabled |
| `POST /api/v1/admin/sync-osspa` | Admin enqueue job on scan queue |
| `rcars osspa sync [--force]` | CLI synchronous sync |

Config (`RCARS_` / Settings):

| Setting | Default | Purpose |
|---------|---------|---------|
| `osspa_sync_enabled` | `true` | Gate nightly step |
| `osspa_palist_url` | raw PAList.csv URL | Inventory |
| `osspa_examples_repo_url` | portfolio-architecture-examples git URL | Content root (includes `IE/`) |
| `osspa_examples_ref` | `main` | Git ref |
| `osspa_clone_dir` | under existing `clone_dir` | Working tree |

Job type: `osspa_sync` on `arq:queue:scan`.

---

## 5. Advisor & Browse Integration

### 5a. Advisor

Vector search already joins `embeddings` ↔ `catalog_items` where `retired_at IS NULL`. Once OSSPA rows have `ci_summary` embeddings, they appear in candidates automatically.

**Adjustments:**

- Triage/rationale prompts: recognize `architecture` and `interactive_experience` (reference architectures vs guided interactive demos — not hands-on RHDP labs).
- Default `stages=["prod"]` — OSSPA rows stored as prod.
- Rec cards: content-type pill from analysis; CTA prefers `externalUrl` when `isRedirected` / present, else Architecture Center / GitLab blob for `DetailPage`.

### 5b. Browse

- List OSSPA items with Babylon items (`retired_at IS NULL`).
- Filters: content type (Architecture / Interactive Experience / Demo / Workshop) via `source` + `content_type`.
- Optional chip for `showInCatalog` (informational only).
- Detail drawer: Summary, products, solutions, link via `content_url`; Showroom-only curator controls no-op or hidden for `source=osspa`.

### 5c. Overlap

`compute_content_similarity` can include OSSPA once embeddings exist. Stage `prod` still applies.

---

## 6. Failure & Edge Cases

| Case | Behavior |
|------|----------|
| CSV fetch failure | Abort sync; leave prior OSSPA rows intact; job failed |
| `islive=TRUE` but DetailPage missing on disk | Upsert catalog row; `scan_status=failed`, error_class `missing_adoc` |
| `islive=FALSE` | Not in filtered set → soft-retire if previously present |
| LLM failure | Same as Showroom scan failure patterns |
| Empty filtered set | Do **not** retire all OSSPA items (empty-scan safety guard) |
| `DetailPage` with `..` or absolute path | Reject row; log warning |
| `ProductType=PA,VP` | Slug `pa`, content_type `architecture` |
| Duplicate `PAName` | Last-write wins; log warning |
| Babylon `ci_name` collision | Prevented by `osspa.` prefix |

---

## 7. Security & Ops

- Public GitLab HTTPS — no token required for clone/fetch of these repos (verify at implement time; if rate-limited, optional `RCARS_GITLAB_TOKEN`).
- No PII in PAList.
- structlog fields: `component=osspa_sync`, `action`, counts, `job_id`, `detail_page`.
- Token usage: record LLM calls under operation `osspa_analyze` (or reuse `analyze` with `ci_name`).

---

## 8. Testing

1. **Unit:** Inclusion filter — only `islive=TRUE` + valid DetailPage; `islive=FALSE` excluded even if `showInCatalog=TRUE`.
2. **Unit:** Path resolution — root adoc, nested adoc, `IE/*.adoc`; reject `../` traversal.
3. **Unit:** `ci_name` mapping for PA vs IE; Babylon retire skips `source=osspa`.
4. **Integration:** Fixture CSV with one PA DetailPage + one IE DetailPage → both analyzed; vector search can hit either.
5. **Regression:** Catalog refresh does not retire fixture OSSPA rows; flipping `islive` to FALSE retires on OSSPA sync.

---

## 9. Rollout

1. Migrate schema (`source`, `external_id`, `content_url`, `detail_page`); backfill Babylon.
2. Ship sync service + CLI; run once on dev; verify live count (~hundreds) and sample PA + IE Advisor hits.
3. Wire admin endpoint + nightly step behind `osspa_sync_enabled`.
4. Frontend: content-type pills + Browse filters + outbound links.
5. Docs: architecture page under `docs/architecture/` + WORKLOG note.

---

## 10. Success Criteria

- [ ] Every `islive=TRUE` row with a valid `DetailPage` upserted as `source=osspa`
- [ ] Content body read from `DetailPage` under [portfolio-architecture-examples](https://gitlab.com/osspa/portfolio-architecture-examples), including [`IE/`](https://gitlab.com/osspa/portfolio-architecture-examples/-/tree/main/IE) paths
- [ ] `islive=FALSE` rows are not ingested / are soft-retired on sync
- [ ] Babylon nightly refresh does not retire OSSPA items
- [ ] Successful analysis produces embeddings for both a root PA adoc and an `IE/` adoc
- [ ] Advisor can return OSSPA hits for queries aligned to known live assets
- [ ] Browse can distinguish Architecture vs Interactive Experience (via ProductType / content_type)

---

## 11. Open Questions

1. **Public CTA URL** — Prefer Architecture Center detail URLs vs `externalUrl` vs GitLab blob for `content_url`?
2. **`format_suitability` sanitizer** — Extend allowed keys, or leave null for OSSPA?
3. **Nightly step order** — After catalog refresh (recommended) vs after reporting sync?
4. **Status=Archived but islive=TRUE** — Include (per strict `islive` rule) or also require Active? **Default: include if islive=TRUE.**

---

## Appendix A — Example row mappings

### A1. Portfolio Architecture (root DetailPage)

```text
islive=TRUE
ProductType=PA
DetailPage=rhacs-multitenant.adoc
PAName=275-rhacs-multitenant
```

→ `ci_name=osspa.pa.275-rhacs-multitenant`  
→ read `{clone}/rhacs-multitenant.adoc`  
→ `content_type=architecture`

### A2. Interactive Experience (`IE/` DetailPage)

```text
islive=TRUE
ProductType=IE
DetailPage=IE/omnicloud-as-a-service-interactive-experience.adoc
PAName=272-omnicloud-as-a-service-interactive-experience
isRedirected=TRUE
```

→ `ci_name=osspa.ie.272-omnicloud-as-a-service-interactive-experience`  
→ read `{clone}/IE/omnicloud-as-a-service-interactive-experience.adoc`  
→ `content_type=interactive_experience`  
→ CTA may prefer `externalUrl` when set
