# RCARS Generalized Content Model — Implementation Plan

**Jira:** [RHDPCD-359](https://redhat.atlassian.net/browse/RHDPCD-359) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Spec:** `docs/superpowers/specs/2026-07-20-generalized-content-model-design.md`
**Date:** 2026-07-20
**Approach:** Full normalization (Approach A) — fresh schema build, pipelines repopulate

## Branch Strategy

**All work happens on a feature branch.** This is a major structural change — main stays untouched until the migration is validated end-to-end in dev.

```
Branch: feature/content-model
Base: main
```

- Create the feature branch before starting Task 1.
- All commits reference RHDPCD-359.
- Deploy to dev from the feature branch for testing. The dev environment is where things break — that's what it's for.
- Only merge to main via PR after: schema is deployed to dev, all pipelines run successfully, Browse/Advisor/Retirement UI all work, data is validated.
- CodeRabbit reviews the PR before merge.

## Overview

This plan decomposes the generalized content model migration into implementable tasks. The migration replaces the `catalog_items`-centric schema with a normalized `content_entities` + source extension table model. It is a fresh schema build: old tables are dropped, new tables are created, and the nightly pipelines repopulate data from source systems. Three categories of data are preserved across the swap: advisor sessions, active retirement workflows, and curator notes.

The plan is divided into three parts:
- **Part 1 (Tasks 1-4):** Schema DDL, migration script, entity/item CRUD, analysis/embeddings methods
- **Part 2 (Tasks 5-8):** Pipeline adaptation (catalog refresh, stale check, analysis, reporting sync)
- **Part 3 (Tasks 9-12):** API routes, frontend, Advisor pipeline, deploy/validate

---

## Part 1 — Database Foundation

### Task 1: New Schema DDL

**Files to modify:**
- `src/api/rcars/db/database.py` — replace `SCHEMA_SQL` constant

**Dependencies:** None (this is the foundation)

**What to do:**

Replace the entire `SCHEMA_SQL` constant in `database.py` with the new normalized schema. The new schema contains these tables, in this order (respecting FK dependencies):

#### 1a. content_entities (NEW — replaces catalog_items as the universal entity registry)

```sql
CREATE TABLE IF NOT EXISTS content_entities (
    content_id      TEXT PRIMARY KEY,
    source          TEXT NOT NULL,            -- 'babylon', 'portfolio_arch', 'interactive_exp'
    content_type    TEXT NOT NULL,            -- 'lab', 'demo', 'sandbox', 'architecture', 'interactive_experience'
    is_hands_on     BOOLEAN NOT NULL DEFAULT FALSE,

    -- The "card" — Browse listing + triage contract (denormalized from analysis)
    display_name    TEXT NOT NULL,
    summary         TEXT,
    products_json   JSONB,
    topics_json     JSONB,
    audience_json   JSONB,
    difficulty      TEXT,

    -- Lifecycle
    retired_at      TIMESTAMPTZ,
    retirement_reason TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ce_source ON content_entities(source);
CREATE INDEX IF NOT EXISTS idx_ce_content_type ON content_entities(content_type);
CREATE INDEX IF NOT EXISTS idx_ce_retired ON content_entities(retired_at);
CREATE INDEX IF NOT EXISTS idx_ce_products ON content_entities USING gin(products_json);
```

#### 1b. babylon_items (NEW — Babylon-specific extension, 1:1 with content_entities)

```sql
CREATE TABLE IF NOT EXISTS babylon_items (
    content_id      TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    ci_name         TEXT NOT NULL UNIQUE,

    -- CRD identity
    category        TEXT,
    stage           TEXT,
    catalog_namespace TEXT,
    is_prod         BOOLEAN DEFAULT FALSE,
    is_published    BOOLEAN DEFAULT FALSE,
    published_ci_name TEXT,
    base_ci_name    TEXT,

    -- Content pointers
    showroom_url    TEXT,
    showroom_ref    TEXT,
    content_path    TEXT,
    showroom_url_override TEXT,

    -- Infrastructure metadata
    is_agd_v2       BOOLEAN DEFAULT FALSE,
    agd_config      TEXT,
    cloud_provider  TEXT,
    ocp_version     TEXT,
    os_image        TEXT,
    worker_instance_count TEXT,
    control_plane_instance_count TEXT,
    instances_json  JSONB,

    -- CRD metadata
    keywords        TEXT[],
    description     TEXT,
    owners_json     JSONB,
    icon_url        TEXT,
    last_crd_update TIMESTAMPTZ,
    last_refreshed  TIMESTAMPTZ DEFAULT NOW(),

    -- Scan tracking
    scan_status     TEXT NOT NULL DEFAULT 'not_scanned',
    scan_error_class TEXT,
    scan_error      TEXT,
    scan_failed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_bi_ci_name ON babylon_items(ci_name);
CREATE INDEX IF NOT EXISTS idx_bi_stage ON babylon_items(stage);
CREATE INDEX IF NOT EXISTS idx_bi_is_prod ON babylon_items(is_prod);
CREATE INDEX IF NOT EXISTS idx_bi_showroom_url ON babylon_items(showroom_url);
CREATE INDEX IF NOT EXISTS idx_bi_cloud_provider ON babylon_items(cloud_provider);
CREATE INDEX IF NOT EXISTS idx_bi_category ON babylon_items(category);
```

Note: Fields that moved UP to content_entities: `display_name`, `retired_at`, `retirement_reason`, `products_json` (was not on catalog_items, but now lives on content_entities). Fields that are NOT carried over from catalog_items: `product`, `product_family`, `primary_bu`, `secondary_bu` (these were never populated by the CRD scanner and have no data — they were vestiges of an early schema that predated the workload classification pipeline).

#### 1c. showroom_analysis (RE-KEYED from ci_name to content_id)

```sql
CREATE TABLE IF NOT EXISTS showroom_analysis (
    content_id              TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,

    -- Shared analysis contract (feeds triage, embeddings, content_entities denormalization)
    summary                 TEXT,
    products_json           JSONB,
    topics_json             JSONB,
    audience_json           JSONB,
    difficulty              TEXT,
    content_hash            TEXT,
    last_analyzed           TIMESTAMPTZ,
    is_stale                BOOLEAN DEFAULT FALSE,
    stale_commit            TEXT,

    -- Lab/demo-specific
    content_type            TEXT,
    modules_json            JSONB,
    learning_objectives_json JSONB,
    estimated_duration_min  INTEGER,
    curated_duration_min    INTEGER CHECK (curated_duration_min >= 0),
    format_suitability_json JSONB,
    use_cases_json          JSONB,

    -- Git tracking
    last_repo_commit        TEXT,
    last_repo_updated       TIMESTAMPTZ,

    -- Curator
    enrichment_review_needed BOOLEAN DEFAULT FALSE,
    review_reasons           JSONB,
    notes                   TEXT
);
```

Changes from current: PK is `content_id` instead of `ci_name`. Added `review_reasons JSONB` column per spec section 4 (structured review flagging). All other columns are unchanged.

#### 1d. embeddings (RE-KEYED, new columns)

```sql
CREATE TABLE IF NOT EXISTS embeddings (
    id              SERIAL PRIMARY KEY,
    content_id      TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_type    TEXT NOT NULL,        -- NEW: 'lab', 'demo', 'sandbox', etc.
    source          TEXT NOT NULL,        -- NEW: 'babylon', 'portfolio_arch', etc.
    embed_type      TEXT NOT NULL,        -- 'summary', 'module', 'section'
    module_title    TEXT,
    content_text    TEXT,
    embedding       vector(384)
);

CREATE INDEX IF NOT EXISTS idx_emb_content_id ON embeddings(content_id);
CREATE INDEX IF NOT EXISTS idx_emb_content_type ON embeddings(content_type);
CREATE INDEX IF NOT EXISTS idx_emb_embed_type ON embeddings(embed_type);
```

Changes from current: FK is `content_id` instead of `ci_name`. Added `content_type` and `source` columns. Renamed `ci_summary` embed_type convention to `summary` (but the value is just data, not schema — the code will use the new convention).

#### 1e. performance_channels (NEW — replaces reporting_metrics)

```sql
CREATE TABLE IF NOT EXISTS performance_channels (
    id                      SERIAL PRIMARY KEY,
    content_id              TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    channel                 TEXT NOT NULL,          -- 'rhdp', 'interactive_labs', 'web'

    -- Volume metrics
    provisions              INTEGER DEFAULT 0,
    unique_users            INTEGER DEFAULT 0,
    requests                INTEGER DEFAULT 0,
    page_views              INTEGER DEFAULT 0,
    downloads               INTEGER DEFAULT 0,
    completions             INTEGER DEFAULT 0,

    -- Financial attribution
    pipeline_touched        NUMERIC,
    closed_amount           NUMERIC,
    marketing_spend         NUMERIC,
    total_cost              NUMERIC,
    avg_cost_per_provision  NUMERIC,
    success_ratio           NUMERIC,

    -- Time range
    first_activity          DATE,
    last_activity           DATE,

    -- Windowed breakdowns
    windowed_metrics        JSONB DEFAULT '{}'::jsonb,

    synced_at               TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_pc_content_id ON performance_channels(content_id);
CREATE INDEX IF NOT EXISTS idx_pc_channel ON performance_channels(channel);
```

#### 1f. performance_scores (NEW — replaces retirement_score on reporting_metrics)

```sql
CREATE TABLE IF NOT EXISTS performance_scores (
    content_id      TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    performance_score INTEGER NOT NULL DEFAULT 0,
    score_breakdown JSONB,
    channel_scores  JSONB,
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    ignored_until   DATE
);

CREATE INDEX IF NOT EXISTS idx_ps_score ON performance_scores(performance_score DESC);
```

#### 1g. retirement_workflow (RE-KEYED from catalog_base_name to content_id)

```sql
CREATE TABLE IF NOT EXISTS retirement_workflow (
    content_id          TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    status              TEXT NOT NULL DEFAULT 'reviewed',
    step_reviewed_at    TIMESTAMPTZ,
    step_reviewed_by    TEXT,
    step_approved_at    TIMESTAMPTZ,
    step_approved_by    TEXT,
    approval_reason     TEXT,
    approval_snapshot   JSONB,
    step_notified_at    TIMESTAMPTZ,
    step_notified_by    TEXT,
    step_started_at     TIMESTAMPTZ,
    step_started_by     TEXT,
    retirement_target_date DATE,
    step_retired_at     TIMESTAMPTZ,
    replacement_ci      TEXT,
    replacement_name    TEXT,
    curator_notes       TEXT,
    jira_key            TEXT,
    jira_project        TEXT NOT NULL DEFAULT 'RHDPCD',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rw_status ON retirement_workflow(status);
```

Changes from current: PK and FK changed from `catalog_base_name TEXT` to `content_id TEXT REFERENCES content_entities`. All other columns preserved exactly (including `approval_reason`, `retirement_target_date`, `replacement_ci`, `replacement_name`, `curator_notes`, `jira_project`, `created_at`, `updated_at` which exist on current schema). The spec's illustrative DDL omitted some of these columns — the implementation preserves them all.

#### 1h. content_similarity (RE-KEYED from ci_name_a/b to content_id_a/b)

```sql
CREATE TABLE IF NOT EXISTS content_similarity (
    id SERIAL PRIMARY KEY,
    content_id_a TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_id_b TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    similarity_score REAL NOT NULL,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id_a, content_id_b)
);

CREATE INDEX IF NOT EXISTS idx_content_similarity_a ON content_similarity(content_id_a);
CREATE INDEX IF NOT EXISTS idx_content_similarity_b ON content_similarity(content_id_b);
CREATE INDEX IF NOT EXISTS idx_content_similarity_score ON content_similarity(similarity_score DESC);
```

#### 1i. babylon_item_workloads (RE-KEYED from ci_name to content_id)

```sql
CREATE TABLE IF NOT EXISTS babylon_item_workloads (
    id SERIAL PRIMARY KEY,
    content_id TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    workload_fqcn TEXT NOT NULL,
    workload_role TEXT NOT NULL,
    workload_collection TEXT,
    UNIQUE(content_id, workload_fqcn)
);

CREATE INDEX IF NOT EXISTS idx_biw_content_id ON babylon_item_workloads(content_id);
CREATE INDEX IF NOT EXISTS idx_biw_workload_role ON babylon_item_workloads(workload_role);
CREATE INDEX IF NOT EXISTS idx_biw_workload_collection ON babylon_item_workloads(workload_collection);
```

#### 1j. babylon_item_acl_groups (RE-KEYED from ci_name to content_id)

```sql
CREATE TABLE IF NOT EXISTS babylon_item_acl_groups (
    id SERIAL PRIMARY KEY,
    content_id TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    group_name TEXT NOT NULL,
    UNIQUE(content_id, group_name)
);

CREATE INDEX IF NOT EXISTS idx_biacl_content_id ON babylon_item_acl_groups(content_id);
CREATE INDEX IF NOT EXISTS idx_biacl_group_name ON babylon_item_acl_groups(group_name);
```

#### 1k. workload_mapping and workload_aliases (UNCHANGED — independent reference tables)

```sql
CREATE TABLE IF NOT EXISTS workload_mapping (
    id SERIAL PRIMARY KEY,
    workload_role TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    source_collection TEXT,
    verified BOOLEAN DEFAULT FALSE,
    added_by TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS workload_aliases (
    id SERIAL PRIMARY KEY,
    product_name TEXT NOT NULL,
    alias TEXT NOT NULL UNIQUE,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wm_product_name ON workload_mapping(product_name);
CREATE INDEX IF NOT EXISTS idx_wa_product_name ON workload_aliases(product_name);
```

#### 1l. enrichment_tags (RE-KEYED from ci_name to content_id)

```sql
CREATE TABLE IF NOT EXISTS enrichment_tags (
    id SERIAL PRIMARY KEY,
    content_id TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    added_by TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id, tag_type, tag_value)
);

CREATE INDEX IF NOT EXISTS idx_et_content_id ON enrichment_tags(content_id);
```

#### 1m. Operational tables (recreated empty, unchanged structure)

```sql
CREATE TABLE IF NOT EXISTS analysis_log (
    id SERIAL PRIMARY KEY,
    ci_name TEXT,                 -- kept as ci_name for backward compat with historical data
    action TEXT NOT NULL,
    user_id TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS token_usage (
    id SERIAL PRIMARY KEY,
    operation TEXT NOT NULL,
    model TEXT NOT NULL,
    ci_name TEXT,
    query_text TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    provider TEXT DEFAULT 'anthropic',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    queue TEXT NOT NULL DEFAULT 'default',
    created_by TEXT,
    progress_json JSONB,
    result_json JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL,
    created_by TEXT NOT NULL,
    scopes TEXT[],
    role TEXT NOT NULL DEFAULT 'user',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS workload_scan_state (
    collection TEXT PRIMARY KEY,
    last_sha TEXT,
    last_scanned TIMESTAMPTZ DEFAULT NOW()
);

-- Operational indexes
CREATE INDEX IF NOT EXISTS idx_analysis_log_ci_name ON analysis_log(ci_name);
CREATE INDEX IF NOT EXISTS idx_analysis_log_created_at ON analysis_log(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_operation ON token_usage(operation);
CREATE INDEX IF NOT EXISTS idx_token_usage_provider ON token_usage(provider);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_created_by ON api_keys(created_by);
```

#### 1n. advisor_sessions (PRESERVED with new column)

```sql
CREATE TABLE IF NOT EXISTS advisor_sessions (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    user_email TEXT,
    query_text TEXT,
    event_url TEXT,
    results_json JSONB,
    overall_assessment TEXT,
    chosen_ci_name TEXT,
    chosen_content_id TEXT,          -- NEW: content_id for new-model sessions
    chosen_at TIMESTAMPTZ,
    opted_out BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_advisor_sessions_session ON advisor_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_advisor_sessions_user ON advisor_sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_advisor_sessions_created ON advisor_sessions(created_at);
```

Changes from current: Added `chosen_content_id TEXT` column. Both `chosen_ci_name` and `chosen_content_id` coexist for backward compatibility — historical rows have `chosen_ci_name` only, new rows populate both.

#### 1o. Update drop_schema()

Update the `drop_schema()` method's table list to reflect the new table names:

```python
tables = [
    "retirement_workflow",
    "content_similarity",
    "performance_scores", "performance_channels",
    "embeddings", "enrichment_tags", "showroom_analysis",
    "analysis_log", "jobs", "token_usage", "advisor_sessions",
    "api_keys",
    "babylon_item_workloads", "babylon_item_acl_groups",
    "workload_aliases", "workload_mapping", "workload_scan_state",
    "babylon_items", "content_entities",
    # Legacy tables (ensure clean drop if they exist from previous schema)
    "catalog_item_workloads", "catalog_item_acl_groups",
    "reporting_metrics", "catalog_items",
    "alembic_version",
]
```

**Validation criteria:**
- `create_schema()` runs without errors on a fresh database
- `drop_schema()` followed by `create_schema()` succeeds
- All FK relationships are valid (CASCADE deletes propagate correctly)
- All indexes are created
- `python -m pytest tests/ -v -k "test_schema or test_create"` passes (after updating test fixtures)

---

### Task 2: Data Preservation and Migration Script

**Files to create:**
- `src/api/scripts/migrate_to_content_model.py`

**Dependencies:** Task 1 (new SCHEMA_SQL must exist)

**What to do:**

Create a standalone migration script with two phases: EXPORT (runs against old schema) and IMPORT (runs against new schema). The script is run manually during migration — it is not part of the nightly pipeline.

#### 2a. Export phase — `export_keeper_data(db_url) -> dict`

Connects to the database with the OLD schema still in place. Exports three categories of data to an in-memory dict (or JSON file at `/tmp/rcars-migration-export.json`):

1. **advisor_sessions** — Export ALL rows from `advisor_sessions`. These are preserved across the migration intact. The table structure is the same except for the new `chosen_content_id` column.

   ```sql
   SELECT * FROM advisor_sessions ORDER BY id
   ```

2. **Active retirement workflows** — Export rows from `retirement_workflow` where the workflow is in progress (not yet fully complete). "Active" means `status NOT IN ('retired', 'reviewed')` — i.e., any workflow that has progressed beyond initial review but hasn't completed retirement. Also include `status = 'reviewed'` rows that have a `jira_key` (Jira ticket was created).

   ```sql
   SELECT * FROM retirement_workflow
   WHERE status NOT IN ('retired')
      OR jira_key IS NOT NULL
   ```

   For each row, also capture the `catalog_base_name` for later content_id mapping.

3. **Curator notes** — Export `ci_name` and `notes` from `showroom_analysis` where `notes IS NOT NULL AND notes != ''`.

   ```sql
   SELECT ci_name, notes FROM showroom_analysis
   WHERE notes IS NOT NULL AND notes != ''
   ```

The export function returns a dict:
```python
{
    "exported_at": "2026-07-20T...",
    "advisor_sessions": [...],          # list of row dicts
    "retirement_workflows": [...],       # list of row dicts with catalog_base_name
    "curator_notes": [...],              # list of {ci_name, notes}
}
```

Write this to `/tmp/rcars-migration-export.json` as backup, and return the dict.

#### 2b. Import phase — `import_keeper_data(db_url, keeper_data: dict)`

Runs AFTER the schema swap (old tables dropped, new tables created, pipelines have NOT yet run). The new schema is empty except for `advisor_sessions` (which was preserved via `CREATE TABLE IF NOT EXISTS` — but if the table was dropped and recreated, we need to re-insert).

**Strategy:** The script handles both cases — if advisor_sessions was preserved in place (table existed and was not dropped), it adds the `chosen_content_id` column. If the table is empty (fresh create), it re-inserts the exported rows.

1. **advisor_sessions** — If the table has rows, just add the mapping column. If empty, bulk insert from export. For all rows where `chosen_ci_name` is not null, compute `chosen_content_id = 'babylon:' || chosen_ci_name`.

   ```sql
   UPDATE advisor_sessions
   SET chosen_content_id = 'babylon:' || chosen_ci_name
   WHERE chosen_ci_name IS NOT NULL AND chosen_content_id IS NULL
   ```

2. **retirement_workflows** — Cannot import until content_entities are populated (the FK requires the content_id to exist). This import runs AFTER the first catalog refresh pipeline. The mapping logic:

   - `catalog_base_name` like `openshift-cnv.ocp4-getting-started` maps to content_id `babylon:openshift-cnv.ocp4-getting-started.prod` (append `.prod` and prefix with `babylon:`).
   - If the `.prod` content_id doesn't exist in content_entities, try `.dev`, then `.event`.
   - If no match found, log a warning and skip the row (the underlying CI was fully retired and is gone).
   - Insert into `retirement_workflow` with the mapped `content_id` as PK. Copy all step timestamps, status, jira fields, notes, and approval_snapshot.

3. **curator_notes** — Also runs AFTER the first analysis pipeline (so `showroom_analysis` rows exist to update). The mapping:

   - `ci_name` maps to content_id `babylon:{ci_name}`.
   - Look up the content_id in `showroom_analysis`. If the row exists, update `notes`.
   - If no showroom_analysis row exists yet (analysis hasn't run for this item), log and skip — the note can be manually re-added later. This is an edge case for items that were analyzed under the old schema but not yet under the new one.

#### 2c. Script CLI interface

The script should be runnable as:

```bash
# Phase 1: Export (run BEFORE schema swap)
python scripts/migrate_to_content_model.py export --db-url "$DATABASE_URL"

# Phase 2: Import advisor sessions (run AFTER schema swap, before or after pipelines)
python scripts/migrate_to_content_model.py import-sessions --db-url "$DATABASE_URL"

# Phase 3: Import retirement workflows (run AFTER first catalog refresh)
python scripts/migrate_to_content_model.py import-workflows --db-url "$DATABASE_URL"

# Phase 4: Import curator notes (run AFTER first analysis pipeline)
python scripts/migrate_to_content_model.py import-notes --db-url "$DATABASE_URL"

# All-in-one with prompts (interactive)
python scripts/migrate_to_content_model.py migrate --db-url "$DATABASE_URL"
```

Each subcommand reads from `/tmp/rcars-migration-export.json` (written by the export phase).

**Validation criteria:**
- Export produces valid JSON with all three data categories
- Import-sessions correctly maps `chosen_ci_name` to `chosen_content_id` using `babylon:` prefix
- Import-workflows correctly maps `catalog_base_name` to `content_id`, preferring `.prod` suffix
- Import-notes matches by `babylon:{ci_name}` and updates existing showroom_analysis rows
- Round-trip test: export from dev, create new schema, run catalog refresh + analysis, import — verify data integrity
- Script is idempotent: running import twice does not create duplicate rows (use ON CONFLICT or check-before-insert)

---

### Task 3: Content Entity and Babylon Item CRUD Methods

**Files to modify:**
- `src/api/rcars/db/database.py` — Database class methods

**Dependencies:** Task 1 (schema must exist)

**What to do:**

Replace the catalog_items CRUD methods with content_entities + babylon_items methods. Remove the old methods; add the new ones. The method signatures change because the primary identifier changes from `ci_name` to `content_id`.

#### 3a. NEW: `upsert_babylon_catalog_item(item: dict)` — replaces `upsert_catalog_item()`

This is the core change. The single `upsert_catalog_item()` call that wrote 30+ fields to `catalog_items` becomes a two-table write in one transaction.

```python
def upsert_babylon_catalog_item(self, item: dict[str, Any]):
    """Upsert a Babylon catalog item across content_entities + babylon_items in one transaction."""
```

Implementation:

1. Generate `content_id`:
   ```python
   ci_name = item["ci_name"]
   content_id = f"babylon:{ci_name}"
   ```

2. Classify content_type using the heuristic from the spec:
   ```python
   showroom_url = item.get("showroom_url")
   category = (item.get("category") or "").lower()
   if showroom_url and category in ("workshop", "lab"):
       content_type = "lab"
   elif showroom_url and category == "demo":
       content_type = "demo"
   else:
       content_type = "sandbox"
   ```
   Note: The category values from CRDs are "Workshop", "Lab", "Demo", and others. Check the actual values used in the current catalog_items data. The heuristic should be case-insensitive. Items with a showroom_url but a category that doesn't match "Workshop", "Lab", or "Demo" should default to "lab" if they have showroom content (conservative default — better to over-classify as lab than sandbox).

   Refined heuristic:
   ```python
   if showroom_url:
       if category in ("demo",):
           content_type = "demo"
       else:
           content_type = "lab"   # Workshop, Lab, or any other category with Showroom
   else:
       content_type = "sandbox"
   ```

3. Write to `content_entities` first (parent table):
   ```python
   # Fields for content_entities
   ce_data = {
       "content_id": content_id,
       "source": "babylon",
       "content_type": content_type,
       "is_hands_on": True,  # All Babylon items are hands-on
       "display_name": item.get("display_name") or ci_name,
       "retired_at": None,       # Un-retire if reappears
       "retirement_reason": None,
       "updated_at": datetime.now(timezone.utc),
   }
   ```
   Use `INSERT ... ON CONFLICT (content_id) DO UPDATE SET ...` — update everything except `content_id`, `source`, `created_at`. Do NOT overwrite `summary`, `products_json`, `topics_json`, `audience_json`, `difficulty` — those are written by the analysis denormalization step, not by catalog refresh.

4. Write to `babylon_items` (extension table):
   ```python
   # Fields for babylon_items — everything that was on catalog_items minus the fields that moved up
   bi_fields = [
       "ci_name", "category", "stage", "catalog_namespace",
       "keywords", "description", "icon_url", "owners_json",
       "showroom_url", "showroom_ref", "content_path",
       "last_crd_update", "is_prod", "is_published",
       "published_ci_name", "base_ci_name",
       "is_agd_v2", "agd_config", "cloud_provider", "ocp_version",
       "os_image", "worker_instance_count", "control_plane_instance_count",
       "instances_json",
   ]
   ```
   Use `INSERT ... ON CONFLICT (content_id) DO UPDATE SET ...` with all fields except `content_id`.

5. Both writes happen in ONE `with conn:` transaction block. If either fails, both roll back.

6. Handle JSONB fields the same way as current code: wrap `owners_json` and `instances_json` with `Jsonb()`.

7. Remove `showroom_url_override` from the upsert — it is a curator-set override, not a CRD field. It should be preserved across upserts (not overwritten to NULL). Add it to the babylon_items schema but exclude it from the upsert's ON CONFLICT update list.

#### 3b. NEW: `get_content_entity(content_id: str) -> dict | None`

Simple PK lookup on `content_entities`.

```python
def get_content_entity(self, content_id: str) -> dict[str, Any] | None:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT * FROM content_entities WHERE content_id = %(content_id)s",
            {"content_id": content_id},
        )
        return cur.fetchone()
```

#### 3c. NEW: `get_babylon_item(content_id: str) -> dict | None`

Returns the joined content_entities + babylon_items row for a Babylon item, looked up by content_id. This is the equivalent of the old `get_catalog_item()`.

```python
def get_babylon_item(self, content_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT ce.*, bi.*
        FROM content_entities ce
        JOIN babylon_items bi ON bi.content_id = ce.content_id
        WHERE ce.content_id = %(content_id)s
    """
    with self._pool.connection() as conn:
        cur = conn.execute(sql, {"content_id": content_id})
        return cur.fetchone()
```

#### 3d. NEW: `get_babylon_item_by_ci_name(ci_name: str) -> dict | None`

Backward-compatibility lookup. Many parts of the codebase (CLI, reporting sync, external references) still use `ci_name`. This method looks up via `babylon_items.ci_name` and returns the same joined row.

```python
def get_babylon_item_by_ci_name(self, ci_name: str) -> dict[str, Any] | None:
    sql = """
        SELECT ce.*, bi.*
        FROM content_entities ce
        JOIN babylon_items bi ON bi.content_id = ce.content_id
        WHERE bi.ci_name = %(ci_name)s
    """
    with self._pool.connection() as conn:
        cur = conn.execute(sql, {"ci_name": ci_name})
        return cur.fetchone()
```

#### 3e. UPDATE: `retire_removed_items(current_content_ids: set[str])` — re-keyed

The parameter changes from `current_ci_names: set[str]` to `current_content_ids: set[str]`. The method operates on `content_entities.retired_at` instead of `catalog_items.retired_at`.

Key changes:
- Query `content_entities` for all items with `source = 'babylon'` (only retire Babylon items during Babylon scan)
- Compare against `current_content_ids`
- Set `retired_at = NOW()` and `retirement_reason = 'Disappeared from Babylon CRDs'` on content_entities
- Un-retire items that reappear (set `retired_at = NULL, retirement_reason = NULL`)
- Auto-close retirement workflows: extract base name from content_id (strip `babylon:` prefix, then strip `.prod`/`.dev`/`.event`/`.test` suffix), then look up in `retirement_workflow` by content_id pattern

The auto-close logic needs updating: currently it uses `catalog_base_name` on `retirement_workflow`, but the new schema uses `content_id`. The retirement workflow content_id format is `babylon:{base_name}.prod` (or whichever stage the workflow was created for). The auto-close should check if ALL stage variants of a base name are retired by querying `content_entities WHERE content_id LIKE 'babylon:{base}%' AND retired_at IS NULL`.

#### 3f. UPDATE: `list_content_entities_filtered()` — replaces `list_catalog_items_filtered()`

This is a major rewrite. The method queries `content_entities` as the primary table, with optional JOINs to `babylon_items` for Babylon-specific filters.

New signature:
```python
def list_content_entities_filtered(
    self,
    search: str | None = None,
    content_types: list[str] | None = None,   # NEW: filter by content type
    stages: list[str] | None = None,          # Babylon-specific
    cloud_provider: str | None = None,        # Babylon-specific
    agd_config: str | None = None,            # Babylon-specific
    workloads: list[str] | None = None,       # Babylon-specific
    content_filter: str | None = None,        # unanalyzed, scan_failures, stale, needs_review
    category: str | None = None,              # Babylon-specific
    limit: int = 50,
    offset: int = 0,
    include_retired: str | bool = False,
) -> dict[str, Any]:
```

Query structure:
- Primary table: `content_entities ce`
- LEFT JOIN `babylon_items bi ON bi.content_id = ce.content_id` (always join — needed for stage filter default and Babylon-specific columns in the response)
- LEFT JOIN `showroom_analysis sa ON sa.content_id = ce.content_id` (for stale/review flags)
- Conditional JOINs for workload filters (same pattern as current, but FK is `babylon_item_workloads.content_id`)

When Babylon-specific filters are applied (stages, cloud_provider, agd_config, workloads, category), add `ce.source = 'babylon'` condition implicitly.

The search filter queries `ce.display_name` and `bi.ci_name` (same ILIKE pattern as current).

The `content_filter` values map to:
- `unanalyzed`: `bi.showroom_url IS NOT NULL AND bi.is_published IS NOT TRUE AND bi.scan_status NOT IN ('success', 'failed')`
- `scan_failures`: `bi.scan_status = 'failed'`
- `stale`: `sa.is_stale = TRUE`
- `needs_review`: `sa.enrichment_review_needed = TRUE`

Response shape stays the same: `{"items": [...], "total": count}`.

Default `stages` filter: when `stages` is None and the request includes Babylon-specific filters, default to `['prod']` (same as current behavior).

#### 3g. UPDATE: `sync_workloads(content_id, workloads)` and `sync_acl_groups(content_id, groups)`

Parameter changes from `ci_name` to `content_id`. Table names change from `catalog_item_workloads` to `babylon_item_workloads` and `catalog_item_acl_groups` to `babylon_item_acl_groups`. FK column changes from `ci_name` to `content_id`.

```python
def sync_workloads(self, content_id: str, workloads: list[dict]) -> None:
    with self._pool.connection() as conn:
        conn.execute("DELETE FROM babylon_item_workloads WHERE content_id = %s", (content_id,))
        for w in workloads:
            conn.execute(
                "INSERT INTO babylon_item_workloads (content_id, workload_fqcn, workload_role, workload_collection) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (content_id, w["fqcn"], w["role"], w.get("collection")),
            )
        conn.commit()
```

Same pattern for `sync_acl_groups`.

#### 3h. UPDATE: `get_workloads(content_id)` and `get_acl_groups(content_id)`

Parameter changes from `ci_name` to `content_id`. Table name changes. Same query pattern.

#### 3i. UPDATE: Other methods that reference catalog_items

The following methods need parameter and table name updates. Keep the method signatures but change internal queries:

- `find_catalog_item_by_display_name_prefix()` — query `content_entities ce JOIN babylon_items bi` instead of `catalog_items`. Filter by `ce.retired_at IS NULL`. Stage filter on `bi.stage`.
- `find_catalog_item_by_keyword_overlap()` — same table change pattern.
- `get_embedding()` — change `ci_name` parameter to `content_id`, query `embeddings` by `content_id`.
- `get_unmapped_workloads()` — change table references from `catalog_item_workloads`/`catalog_items` to `babylon_item_workloads`/`content_entities`.
- `get_infra_stats()` — change `catalog_items` to `content_entities ce JOIN babylon_items bi`, update all references.
- `get_catalog_facets()` — same table change pattern.
- `search_by_infrastructure()` — same table change pattern.
- `get_status_summary()` — query `content_entities` for total/prod/retired counts, join `babylon_items` for showroom/scan stats.
- `get_db_currency()` — same approach as `get_status_summary()`.
- `set_content_path()` — update `babylon_items` instead of `catalog_items`.
- `set_showroom_url_override()` — update `babylon_items`.
- `set_scan_status()` — update `babylon_items` by content_id instead of ci_name. Method signature changes to accept `content_id`.
- `get_scan_failures()` — query `babylon_items bi JOIN content_entities ce`.
- `list_catalog_items()` — if still needed, rewrite to query `content_entities + babylon_items`. Consider whether this method is still called anywhere or if `list_content_entities_filtered()` supersedes it.

#### 3j. REMOVE: Old methods that are fully replaced

- `upsert_catalog_item()` — replaced by `upsert_babylon_catalog_item()`
- `get_catalog_item()` — replaced by `get_content_entity()` + `get_babylon_item()` + `get_babylon_item_by_ci_name()`

**Validation criteria:**
- `upsert_babylon_catalog_item()` writes to both tables atomically — verify with a read-back
- Content type classification produces expected results: item with showroom_url + "Workshop" category = "lab", item with showroom_url + "Demo" category = "demo", item without showroom_url = "sandbox"
- `get_babylon_item_by_ci_name()` returns the same data as `get_babylon_item()` for the same underlying item
- `retire_removed_items()` correctly retires and un-retires items based on content_id set
- `list_content_entities_filtered()` returns correct results for all filter combinations (search, stages, cloud_provider, workloads, content_filter)
- `sync_workloads()` and `sync_acl_groups()` correctly use content_id FK
- Existing tests updated and passing

---

### Task 4: Analysis and Embeddings Database Methods

**Files to modify:**
- `src/api/rcars/db/database.py` — Database class methods

**Dependencies:** Task 1 (schema), Task 3 (content entity methods must exist for FK resolution)

**What to do:**

Update all analysis, embedding, and performance-related database methods to use `content_id` as the primary key and to work with the new table structures.

#### 4a. UPDATE: `upsert_showroom_analysis(analysis: dict)` — re-keyed to content_id

The method signature stays the same (takes a dict), but the dict now uses `content_id` as the key field instead of `ci_name`.

Changes:
- Replace `"ci_name"` with `"content_id"` in the `fields` list
- ON CONFLICT key changes from `(ci_name)` to `(content_id)`
- Add `"review_reasons"` to the fields list (new JSONB column)
- Add `review_reasons` to the `jsonb_fields` list for Jsonb() wrapping

```python
fields = [
    "content_id", "content_type", "summary",    # content_id replaces ci_name
    "products_json", "audience_json", "topics_json",
    "modules_json", "learning_objectives_json",
    "difficulty", "estimated_duration_min",
    "format_suitability_json", "use_cases_json",
    "last_repo_commit", "last_repo_updated",
    "last_analyzed", "is_stale", "stale_commit", "content_hash",
    "enrichment_review_needed", "review_reasons",  # review_reasons is new
]
```

#### 4b. NEW: `update_content_entity_card(content_id, summary, products_json, topics_json, audience_json, difficulty)`

This method does NOT exist in the current codebase. It denormalizes the triage-contract fields from analysis to content_entities. Called after every successful analysis.

```python
def update_content_entity_card(
    self, content_id: str,
    summary: str | None = None,
    products_json: Any = None,
    topics_json: Any = None,
    audience_json: Any = None,
    difficulty: str | None = None,
) -> None:
    """Denormalize triage-contract fields from analysis to content_entities card."""
    with self._pool.connection() as conn:
        conn.execute(
            """UPDATE content_entities
               SET summary = %s, products_json = %s, topics_json = %s,
                   audience_json = %s, difficulty = %s, updated_at = NOW()
               WHERE content_id = %s""",
            (summary,
             Jsonb(products_json) if products_json is not None else None,
             Jsonb(topics_json) if topics_json is not None else None,
             Jsonb(audience_json) if audience_json is not None else None,
             difficulty, content_id),
        )
        conn.commit()
```

This method is called:
1. After `upsert_showroom_analysis()` succeeds for a lab/demo
2. After sandbox summary generation assembles metadata-derived fields
3. During sibling propagation, for each sibling's content_entities row

#### 4c. UPDATE: `get_showroom_analysis(content_id)` — re-keyed

Parameter changes from `ci_name` to `content_id`. Query changes to `WHERE content_id = %(content_id)s`.

Add a convenience method for ci_name lookup:
```python
def get_showroom_analysis_by_ci_name(self, ci_name: str) -> dict[str, Any] | None:
    content_id = f"babylon:{ci_name}"
    return self.get_showroom_analysis(content_id)
```

#### 4d. UPDATE: `clear_embeddings(content_id)` — re-keyed

Parameter changes from `ci_name` to `content_id`. Query changes to `DELETE FROM embeddings WHERE content_id = %s`.

#### 4e. UPDATE: `store_embedding(content_id, content_type, source, embed_type, content_text, embedding, module_title)`

New signature adds `content_type` and `source` parameters:

```python
def store_embedding(
    self, content_id: str, content_type: str, source: str,
    embed_type: str, content_text: str,
    embedding: list[float], module_title: str | None = None,
):
```

The INSERT statement adds the new columns:
```sql
INSERT INTO embeddings (content_id, content_type, source, embed_type, module_title, content_text, embedding)
VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
```

The dedup DELETE before INSERT also changes from `ci_name` to `content_id`.

#### 4f. REWRITE: `search_embeddings()` — major rewrite with MAX(similarity) scoring

This is the most complex method change. The current implementation does a simple distance-ordered query joining catalog_items. The new implementation uses the two-stage MAX(similarity) per content_id approach from the spec.

New signature:
```python
def search_embeddings(
    self, query_embedding: list[float],
    limit: int = 25,
    content_types: list[str] | None = None,   # NEW: replaces embed_type filter
    stages: list[str] | None = None,          # Babylon-specific stage filter
    include_zt: bool = True,                  # Keep for backward compat
    quality_threshold: float = 0.45,          # Similarity floor (equivalent to distance 0.55)
    retrieval_window: int = 200,              # Raw embedding candidates before grouping
) -> list[dict[str, Any]]:
```

Implementation using the spec's SQL pattern:
```sql
WITH candidates AS (
    SELECT e.content_id, e.embed_type, e.module_title, e.content_type, e.source,
           1 - (e.embedding <=> %(query_vec)s::vector) AS similarity
    FROM embeddings e
    JOIN content_entities ce ON ce.content_id = e.content_id
    WHERE ce.retired_at IS NULL
      -- Optional content_type filter
      AND (%(content_types)s IS NULL OR e.content_type = ANY(%(content_types)s))
      -- Optional stage filter (Babylon-specific)
      AND (%(stages)s IS NULL OR EXISTS (
          SELECT 1 FROM babylon_items bi
          WHERE bi.content_id = e.content_id AND bi.stage = ANY(%(stages)s)
      ))
      -- Optional ZT exclusion (Babylon-specific)
      {zt_filter}
    ORDER BY e.embedding <=> %(query_vec)s::vector
    LIMIT %(retrieval_window)s
)
SELECT content_id, content_type, source,
       MAX(similarity) AS best_similarity,
       (ARRAY_AGG(embed_type ORDER BY similarity DESC))[1] AS best_match_type,
       (ARRAY_AGG(module_title ORDER BY similarity DESC))[1] AS best_match_module
FROM candidates
WHERE similarity >= %(quality_threshold)s
GROUP BY content_id, content_type, source
ORDER BY best_similarity DESC
LIMIT %(limit)s
```

The return value for each row includes:
- `content_id`, `content_type`, `source`
- `best_similarity` (float, 0-1 scale where 1 = identical)
- `best_match_type` (which embedding type matched best: 'summary', 'module', etc.)
- `best_match_module` (the module_title of the best match, if applicable)

Additional data needed by the caller (display_name, stage, showroom_url, etc.) is fetched in a second query by the pipeline code, not by this method. This keeps the embedding search query focused on vector math.

However, for backward compatibility with the current pipeline, also fetch key fields from content_entities and babylon_items. Include a JOIN to get:
- `ce.display_name`, `ce.is_hands_on`
- `bi.ci_name`, `bi.stage`, `bi.showroom_url`, `bi.showroom_ref`, `bi.is_published`, `bi.published_ci_name`, `bi.base_ci_name`, `bi.catalog_namespace`
- `sa.content_hash`

This is done as a second query joining the grouped results back to the metadata tables, or as a CTE chain.

The ZT filter for Babylon items: `AND NOT EXISTS (SELECT 1 FROM babylon_items bi WHERE bi.content_id = e.content_id AND (bi.catalog_namespace LIKE 'zt-%%' OR bi.ci_name LIKE 'zt-%%'))` — only applied when `include_zt = False`.

#### 4g. UPDATE: `find_donor_by_content_hash()` — re-keyed

Parameter `exclude_ci` changes to `exclude_content_id`. Query joins `showroom_analysis sa JOIN content_entities ce ON ce.content_id = sa.content_id JOIN babylon_items bi ON bi.content_id = sa.content_id JOIN embeddings e ON e.content_id = sa.content_id AND e.embed_type = 'summary'`. Stage preference comes from `bi.stage`.

```python
def find_donor_by_content_hash(self, content_hash: str, exclude_content_id: str | None = None) -> dict[str, Any] | None:
```

#### 4h. UPDATE: `get_embeddings_for_ci()` — re-keyed to `get_embeddings_for_content(content_id)`

Rename and re-key. Returns all embeddings for a content_id.

```python
def get_embeddings_for_content(self, content_id: str) -> list[dict[str, Any]]:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT embed_type, content_type, source, content_text, module_title, embedding::text as embedding_text "
            "FROM embeddings WHERE content_id = %s",
            (content_id,),
        )
        return cur.fetchall()
```

#### 4i. UPDATE: `mark_stale()` / `clear_stale()` / `mark_all_stale()` — re-keyed

Parameter changes from `ci_name` to `content_id`. Query updates on `showroom_analysis` using `content_id`.

#### 4j. UPDATE: Enrichment methods — re-keyed

All enrichment methods change `ci_name` parameter to `content_id`:
- `add_enrichment_tag(content_id, ...)`
- `remove_enrichment_tag(content_id, ...)`
- `get_enrichment_tags(content_id)`
- `get_enrichment_tags_for_items(content_ids: list[str])`
- `set_enrichment_note(content_id, note)`
- `set_enrichment_review_flag(content_id, needed)`
- `set_curated_duration(content_id, duration_min, ...)`

Table references change from `enrichment_tags.ci_name` to `enrichment_tags.content_id` and from `showroom_analysis.ci_name` to `showroom_analysis.content_id`.

#### 4k. NEW: Performance methods — replace reporting_metrics methods

**`upsert_performance_channels(rows: list[dict])`** — replaces `upsert_reporting_metrics()`

Takes a list of dicts, each with `content_id`, `channel`, and metric fields. Upserts into `performance_channels` with `ON CONFLICT (content_id, channel) DO UPDATE`.

The field mapping from old to new:
- `catalog_base_name` -> `content_id` (mapped by caller)
- `display_name` -> removed (lives on content_entities now)
- `provisions` -> `provisions`
- `provisions_quarter` -> moved into `windowed_metrics`
- `requests` -> `requests`
- `experiences` -> `completions` (renamed for generality)
- `unique_users` -> `unique_users`
- `success_ratio` -> `success_ratio`
- `failure_ratio` -> removed (derivable: 1 - success_ratio)
- `touched_amount` -> `pipeline_touched`
- `closed_amount` -> `closed_amount`
- `total_cost` -> `total_cost`
- `avg_cost_per_provision` -> `avg_cost_per_provision`
- `first_provision` -> `first_activity`
- `last_provision` -> `last_activity`
- `retirement_score` -> moves to `performance_scores` table
- `windowed_metrics` -> `windowed_metrics`

```python
def upsert_performance_channels(self, rows: list[dict]) -> int:
    if not rows:
        return 0
    sql = """
        INSERT INTO performance_channels (
            content_id, channel,
            provisions, unique_users, requests, completions,
            pipeline_touched, closed_amount, total_cost, avg_cost_per_provision,
            success_ratio, first_activity, last_activity,
            windowed_metrics, synced_at
        ) VALUES (
            %(content_id)s, %(channel)s,
            %(provisions)s, %(unique_users)s, %(requests)s, %(completions)s,
            %(pipeline_touched)s, %(closed_amount)s, %(total_cost)s, %(avg_cost_per_provision)s,
            %(success_ratio)s, %(first_activity)s, %(last_activity)s,
            %(windowed_metrics)s::jsonb, NOW()
        )
        ON CONFLICT (content_id, channel) DO UPDATE SET
            provisions = EXCLUDED.provisions,
            unique_users = EXCLUDED.unique_users,
            requests = EXCLUDED.requests,
            completions = EXCLUDED.completions,
            pipeline_touched = EXCLUDED.pipeline_touched,
            closed_amount = EXCLUDED.closed_amount,
            total_cost = EXCLUDED.total_cost,
            avg_cost_per_provision = EXCLUDED.avg_cost_per_provision,
            success_ratio = EXCLUDED.success_ratio,
            first_activity = EXCLUDED.first_activity,
            last_activity = EXCLUDED.last_activity,
            windowed_metrics = EXCLUDED.windowed_metrics,
            synced_at = NOW()
    """
    with self._pool.connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(sql, row)
        conn.commit()
    return len(rows)
```

**`upsert_performance_score(content_id, score, breakdown, channel_scores)`** — replaces the retirement_score column

```python
def upsert_performance_score(self, content_id: str, score: int,
                              breakdown: dict | None = None,
                              channel_scores: dict | None = None) -> None:
    with self._pool.connection() as conn:
        conn.execute(
            """INSERT INTO performance_scores (content_id, performance_score, score_breakdown, channel_scores, computed_at)
               VALUES (%s, %s, %s, %s, NOW())
               ON CONFLICT (content_id) DO UPDATE SET
                   performance_score = EXCLUDED.performance_score,
                   score_breakdown = EXCLUDED.score_breakdown,
                   channel_scores = EXCLUDED.channel_scores,
                   computed_at = NOW()""",
            (content_id, score,
             Jsonb(breakdown) if breakdown else None,
             Jsonb(channel_scores) if channel_scores else None),
        )
        conn.commit()
```

**`get_performance_channels(content_id)`** — replaces `get_reporting_metrics()`

```python
def get_performance_channels(self, content_id: str) -> list[dict]:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT * FROM performance_channels WHERE content_id = %s ORDER BY channel",
            (content_id,),
        )
        return cur.fetchall()
```

**`get_performance_score(content_id)`** — replaces reading retirement_score from reporting_metrics

```python
def get_performance_score(self, content_id: str) -> dict | None:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT * FROM performance_scores WHERE content_id = %s",
            (content_id,),
        )
        return cur.fetchone()
```

**`set_ignored_until(content_id, until_date)`** — moved from reporting_metrics to performance_scores

```python
def set_ignored_until(self, content_id: str, until_date: str) -> bool:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "UPDATE performance_scores SET ignored_until = %s WHERE content_id = %s",
            (until_date, content_id),
        )
        conn.commit()
        return cur.rowcount > 0
```

**`clear_ignored(content_id)`** — same pattern

#### 4l. UPDATE: `list_reporting_metrics()` -> `list_performance_data()`

This is a major rewrite. The method currently joins `reporting_metrics` with `catalog_items` and `retirement_workflow`. The new version joins `performance_channels` + `performance_scores` with `content_entities` + `babylon_items` + `retirement_workflow`.

The method is used by the retirement dashboard. Keep the same filter capabilities (sort, min_score, category, has_prod, search, workflow_status) but adapt to the new table structure.

Key changes:
- Primary table: `performance_scores ps`
- JOIN `performance_channels pc ON pc.content_id = ps.content_id AND pc.channel = 'rhdp'` (Phase 1: RHDP channel only for retirement analysis)
- JOIN `content_entities ce ON ce.content_id = ps.content_id`
- LEFT JOIN `babylon_items bi ON bi.content_id = ps.content_id`
- LEFT JOIN `retirement_workflow rw ON rw.content_id = ps.content_id`
- The `has_prod` filter checks `bi.is_prod` or `bi.stage = 'prod'` instead of constructing ci_name patterns
- The `category` filter checks `bi.category`

#### 4m. UPDATE: Content similarity methods — re-keyed

- `compute_content_similarity()` — change `ci_name_a`/`ci_name_b` to `content_id_a`/`content_id_b`, join `content_entities` instead of `catalog_items`, filter by `bi.stage` via `babylon_items` join
- `get_similar_items()` — change parameter from `ci_name` to `content_id`, update column references
- `get_overlap_report()` — update all table and column references
- `get_similarity_stats()` — update table references

#### 4n. UPDATE: Retirement workflow methods — re-keyed

All retirement workflow methods change `base_name`/`catalog_base_name` to `content_id`:

- `get_retirement_workflow(content_id)` — query by `content_id` PK
- `upsert_retirement_workflow(content_id, fields)` — `content_id` replaces `catalog_base_name` in insert/update
- `delete_retirement_workflow(content_id)` — delete by `content_id`
- `list_retirement_workflows()` — no parameter change, query unchanged except table column name
- `auto_close_retired_workflows(retired_content_ids: set[str])` — parameter is now a set of content_ids

The `upsert_retirement_workflow()` internal logic stays the same (dynamic column building, NOW() handling, approval_snapshot serialization). Only the PK column name changes from `catalog_base_name` to `content_id`.

#### 4o. UPDATE: Reporting helper methods — re-keyed or replaced

- `get_catalog_base_names()` — rewrite to extract base names from `babylon_items.ci_name` instead of `catalog_items.ci_name`. Uses the same `substring` pattern.
- `get_published_base_mapping()` — same logic, query `babylon_items` instead of `catalog_items`
- `delete_orphan_reporting_metrics()` -> `delete_orphan_performance_data()` — delete from `performance_channels` and `performance_scores` where content_id has no matching content_entity
- `get_reporting_sync_status()` — query `performance_scores` and `performance_channels` instead of `reporting_metrics`
- `has_prod_stage(base_name)` — query `babylon_items` for `ci_name = '{base_name}.prod'` joined with `content_entities` for `retired_at IS NULL`
- `get_all_base_names_with_prod()` — same pattern via `babylon_items`
- `get_fully_retired_base_names()` — query `babylon_items` grouped by base name, check `content_entities.retired_at`
- `get_stages_for_base_names()` — query `babylon_items bi JOIN content_entities ce`
- `get_owners_for_base_names()` — query `babylon_items` for `owners_json`

#### 4p. UPDATE: Advisor session methods

- `update_advisor_session_choice()` — accept both `chosen_ci_name` and `chosen_content_id`, write both columns
- `log_advisor_session()` — no changes needed (results_json is opaque JSONB)

#### 4q. UPDATE: Scan management methods

- `get_items_needing_analysis()` — join `content_entities ce` + `babylon_items bi` + `showroom_analysis sa` instead of `catalog_items` + `showroom_analysis`. Filter by `ce.content_type IN ('lab', 'demo')` (sandboxes excluded). Return `content_id` alongside all bi fields.
- `get_scan_dedup_stats()` — same approach, query `babylon_items` + `content_entities`
- `get_siblings_by_showroom()` — query `babylon_items bi JOIN content_entities ce` instead of `catalog_items`
- `complete_scan()` — update `babylon_items` scan_status by content_id

**Validation criteria:**
- `upsert_showroom_analysis()` correctly uses `content_id` as PK
- `update_content_entity_card()` successfully writes denormalized fields to content_entities
- `store_embedding()` writes `content_type` and `source` columns
- `search_embeddings()` returns MAX(similarity) per content_id — test with a multi-module lab (verify it returns one row per entity, not one per embedding)
- `search_embeddings()` respects `content_types` filter (e.g., filter to labs only)
- `search_embeddings()` respects quality_threshold (low-similarity results excluded)
- Performance methods (upsert/get channels and scores) round-trip correctly
- Retirement workflow methods work with content_id PK
- All enrichment methods work with content_id
- `get_items_needing_analysis()` excludes sandboxes (content_type = 'sandbox')
- `find_donor_by_content_hash()` finds donors by content hash across the new schema
- Existing pytest suite updated and passing

---

## Part 2 — Pipeline Adaptation

### Task 5: Catalog Ingest Pipeline (CatalogReader + catalog refresh)

**Files to modify:**
- `src/api/rcars/services/catalog.py` — CatalogReader output adjustments
- `src/api/rcars/workers/ops.py` — `run_catalog_refresh()` rewrite

**Dependencies:** Task 1 (schema), Task 3 (`upsert_babylon_catalog_item()`, `retire_removed_items()`, `sync_workloads()`, `sync_acl_groups()`)

**What to do:**

The catalog ingest pipeline reads CRDs from the Babylon K8s API and writes them to the database. The CatalogReader itself does NOT change (it still produces the same item dicts from CRDs). What changes is how `run_catalog_refresh()` processes those dicts.

#### 5a. CatalogReader output — no changes needed

`CatalogReader.refresh_catalog()` continues to return `list[dict]` where each dict has keys like `ci_name`, `display_name`, `category`, `showroom_url`, `showroom_ref`, `cloud_provider`, `_workloads`, `_acl_groups`, etc. The CatalogReader is a CRD reader — it should not know about content models or content_ids. The caller generates the content_id.

The following fields that CatalogReader currently emits are vestigial and ignored by the new schema (they were never populated by CRDs anyway):
- `product` — always empty string from `_get_label(metadata, "Product")`
- `product_family` — always empty string
- `primary_bu` — always empty string
- `secondary_bu` — always empty string

These fields can remain in the CatalogReader output dict for now — `upsert_babylon_catalog_item()` simply ignores them. Cleaning them out is cosmetic, not structural.

#### 5b. UPDATE: `run_catalog_refresh()` in ops.py

The current flow:

```python
for item in items:
    workloads = item.pop("_workloads", [])
    acl_groups = item.pop("_acl_groups", [])
    wctx.db.upsert_catalog_item(item)
    current_ci_names.add(item["ci_name"])
    wctx.db.sync_workloads(item["ci_name"], workloads)
    wctx.db.sync_acl_groups(item["ci_name"], acl_groups)
```

Changes to:

```python
for item in items:
    workloads = item.pop("_workloads", [])
    acl_groups = item.pop("_acl_groups", [])
    content_id = f"babylon:{item['ci_name']}"
    wctx.db.upsert_babylon_catalog_item(item)       # <-- Task 3 method
    current_content_ids.add(content_id)
    wctx.db.sync_workloads(content_id, workloads)    # <-- content_id, not ci_name
    wctx.db.sync_acl_groups(content_id, acl_groups)  # <-- content_id, not ci_name
```

Specific changes in `run_catalog_refresh()`:

1. **Replace `current_ci_names` with `current_content_ids`** — Track `set[str]` of content_ids (`babylon:{ci_name}`) instead of ci_names.

2. **Call `upsert_babylon_catalog_item(item)` instead of `upsert_catalog_item(item)`** — The item dict from CatalogReader is passed through. `upsert_babylon_catalog_item()` (defined in Task 3a) handles:
   - Generating `content_id = f"babylon:{ci_name}"`
   - Classifying `content_type` via the heuristic (showroom_url + category)
   - Writing to `content_entities` + `babylon_items` atomically

3. **Call `sync_workloads(content_id, workloads)` and `sync_acl_groups(content_id, acl_groups)`** — Pass `content_id` instead of `ci_name`.

4. **Call `retire_removed_items(current_content_ids)`** — Pass the set of content_ids instead of ci_names.

5. **Update result dict and progress messages** — Change `"total_items"` / `"retired_items"` logging. No semantic change, but ensure log messages reference content_ids or item counts correctly.

#### 5c. Content type classification heuristic — implemented in Task 3, validated here

The content type classification is implemented inside `upsert_babylon_catalog_item()` (Task 3a), but this is the pipeline step where it actually executes. The heuristic for reference:

```python
if showroom_url:
    if category.lower() in ("demo",):
        content_type = "demo"
    else:
        content_type = "lab"   # Workshop, Lab, or any other category with Showroom
else:
    content_type = "sandbox"
```

After the first catalog refresh runs with the new code, validate the classification by querying:

```sql
SELECT content_type, COUNT(*) FROM content_entities WHERE source = 'babylon' GROUP BY content_type;
```

Expected distribution (approximate, based on current data):
- `lab`: ~200 (items with showroom_url and category Workshop/Lab/Other)
- `demo`: ~40 (items with showroom_url and category Demo)
- `sandbox`: ~200 (items without showroom_url)

If the `sandbox` count seems too high, spot-check items — some may have showroom_url on a different stage variant.

#### 5d. UPDATE: `retire_removed_items()` — behavioral validation

The method itself was rewritten in Task 3e. Here we validate the pipeline integration:

- Items present in the CRD scan get `retired_at = NULL` (un-retired if previously retired).
- Items NOT in the CRD scan get `retired_at = NOW()`, `retirement_reason = 'Disappeared from Babylon CRDs'`.
- Auto-close of retirement workflows checks whether ALL stage variants of a base name are retired before closing.
- The `current_content_ids` set contains one entry per CRD item across all scanned namespaces.

#### 5e. Pipeline step ordering — no change

The catalog refresh remains Step 1 of the nightly pipeline (before stale check, analysis, workload scan, reporting sync). The ordering is critical: subsequent steps depend on `content_entities` + `babylon_items` being populated.

**Validation criteria:**
- `run_catalog_refresh()` populates both `content_entities` and `babylon_items` for each CRD item
- Every item in `babylon_items` has a corresponding row in `content_entities` (FK integrity)
- `content_type` classification produces expected distribution: labs (~200), demos (~40), sandboxes (~200)
- Items that disappear from CRDs get soft-deleted on `content_entities.retired_at`
- Items that reappear get un-retired (`retired_at = NULL`)
- `babylon_item_workloads` and `babylon_item_acl_groups` have content_id FK references
- Round-trip: scan → retire → re-scan → un-retire works correctly
- Progress messages and result dict are accurate
- `python -m pytest tests/ -v -k "test_refresh or test_catalog"` passes

---

### Task 6: Scan Pipeline (analysis + stale check + sibling propagation)

**Files to modify:**
- `src/api/rcars/workers/scan.py` — `run_analysis()` and `_propagate_to_sibling()`
- `src/api/rcars/workers/ops.py` — `run_stale_check()`, `sha_dedup_scan_items()`, nightly pipeline analysis enqueue

**Dependencies:** Task 1 (schema), Task 3 (content entity CRUD), Task 4 (analysis + embeddings methods), Task 5 (catalog refresh must populate content_entities first)

**What to do:**

The scan pipeline has three parts: stale check (which repos have new commits), analysis (LLM analysis of Showroom content), and sibling propagation (copy analysis to CIs sharing the same content). All three need re-keying from `ci_name` to `content_id`.

#### 6a. UPDATE: `run_stale_check()` in ops.py

Current flow (lines 140-232 of ops.py):
```python
items = wctx.db.list_catalog_items()
checkable = [i for i in items if i.get("showroom_url") and wctx.db.get_showroom_analysis(i["ci_name"])]
```

Changes:

1. **Replace `list_catalog_items()` with a targeted query** — The stale check only needs items with showroom content. Use a new or adapted query that:
   - Joins `content_entities ce` + `babylon_items bi` + `showroom_analysis sa`
   - Filters to `ce.content_type IN ('lab', 'demo')` — sandboxes have no Showroom content and are excluded
   - Filters to `ce.retired_at IS NULL` — don't check retired items
   - Filters to `sa.content_id IS NOT NULL` — only items that have been analyzed at least once
   - Returns `content_id`, `ci_name`, `showroom_url`, `showroom_ref`, `showroom_url_override`, and `sa.content_hash`, `sa.last_repo_commit`

   This replaces the current two-step pattern of listing all items then filtering with `get_showroom_analysis()` per item. A single JOIN query is more efficient.

   Add a new database method: `get_stale_check_candidates()`:
   ```python
   def get_stale_check_candidates(self) -> list[dict]:
       sql = """
           SELECT ce.content_id, bi.ci_name, bi.showroom_url, bi.showroom_ref,
                  bi.showroom_url_override, sa.content_hash, sa.last_repo_commit
           FROM content_entities ce
           JOIN babylon_items bi ON bi.content_id = ce.content_id
           JOIN showroom_analysis sa ON sa.content_id = ce.content_id
           WHERE ce.content_type IN ('lab', 'demo')
             AND ce.retired_at IS NULL
       """
       with self._pool.connection() as conn:
           return conn.execute(sql).fetchall()
   ```

2. **Group by (showroom_url, showroom_ref) using content_id** — The dedup grouping logic stays the same, but items carry `content_id` alongside `ci_name`:
   ```python
   for item in checkable:
       url = item.get("showroom_url_override") or item["showroom_url"]
       ref = item.get("showroom_ref")
       groups.setdefault((url, ref), []).append(item)
   ```

3. **Call `mark_stale(content_id, ...)` and `clear_stale(content_id)`** — These methods were re-keyed in Task 4i. Change all calls from `item["ci_name"]` to `item["content_id"]`.

4. **Analysis lookup for stored SHA** — Currently `wctx.db.get_showroom_analysis(group_items[0]["ci_name"])`. Change to use the pre-fetched `content_hash` and `last_repo_commit` from the query (already available on the item dict from step 1). No separate `get_showroom_analysis()` call needed.

#### 6b. UPDATE: `sha_dedup_scan_items()` in ops.py

This function deduplicates scan items by resolving git refs to commit SHAs. The current implementation uses `ci_name` as the key. Changes:

1. **Items carry `content_id`** — Each item dict in the input list now has a `content_id` field alongside `ci_name`. The function uses `ci_name` for the representative key and sibling tracking, which still works because `ci_name` is just an identifier. However, the sha_siblings output should also include `content_id`:
   ```python
   skipped.append({
       "ci_name": item["ci_name"],
       "content_id": item["content_id"],        # NEW
       "effective_url": effective_url,
       "showroom_ref": item.get("showroom_ref"),
   })
   ```

2. **Representative sorting** — Still sorts by `STAGE_PRIORITY` using `item.get("stage")`. Stage is available on the item dict from the stale check candidate query (add `bi.stage` to the query in 6a if needed, or from the analysis items query in 6c).

#### 6c. UPDATE: `run_analysis()` in scan.py — major re-keying

Current signature: `run_analysis(ctx, job_id, ci_name, sha_siblings=None)`
New signature: `run_analysis(ctx, job_id, content_id, sha_siblings=None)`

The parameter change from `ci_name` to `content_id` cascades through the entire function. Here are all the changes:

1. **Parameter rename** — `ci_name` parameter becomes `content_id`. Extract `ci_name` from content_id for display/logging: `ci_name = content_id.removeprefix("babylon:")`.

2. **Item lookup** — Change `wctx.db.get_catalog_item(ci_name)` to `wctx.db.get_babylon_item(content_id)` (Task 3c). The returned dict has both content_entity and babylon_item fields.

3. **Job progress** — Change `progress_json={"ci_name": ci_name}` to `progress_json={"content_id": content_id, "ci_name": ci_name}`.

4. **Analysis data dict** — Replace `"ci_name": ci_name` with `"content_id": content_id`:
   ```python
   analysis_data = {
       "content_id": content_id,                  # was ci_name
       "content_type": analysis.get("content_type"),
       "summary": analysis.get("summary"),
       # ... rest unchanged ...
   }
   ```

5. **Upsert analysis** — `wctx.db.upsert_showroom_analysis(analysis_data)` — the method was re-keyed in Task 4a to expect `content_id`.

6. **NEW: Denormalize card fields to content_entities** — After `upsert_showroom_analysis()` succeeds, call `update_content_entity_card()` (Task 4b):
   ```python
   wctx.db.upsert_showroom_analysis(analysis_data)
   wctx.db.update_content_entity_card(
       content_id,
       summary=analysis.get("summary"),
       products_json=analysis.get("products"),
       topics_json=analysis.get("topics"),
       audience_json=analysis.get("audience"),
       difficulty=analysis.get("difficulty"),
   )
   ```
   This is the key new write that populates the "card" on content_entities for Browse listing and triage.

7. **Embeddings** — Change `clear_embeddings(ci_name)` to `clear_embeddings(content_id)`. Change `store_embedding(ci_name=ci_name, ...)` to `store_embedding(content_id=content_id, content_type=item["content_type"], source="babylon", ...)`. Note the new `content_type` and `source` parameters (Task 4e).

   Also change `embed_type="ci_summary"` to `embed_type="summary"` (new convention from Task 1d).

   ```python
   wctx.db.clear_embeddings(content_id)
   wctx.db.store_embedding(
       content_id=content_id,
       content_type=item["content_type"],          # NEW: 'lab' or 'demo'
       source="babylon",                            # NEW
       embed_type="summary",                        # was "ci_summary"
       content_text=result["ci_embedding_text"],
       embedding=result["ci_embedding"],
   )
   for mod_emb in result.get("module_embeddings", []):
       wctx.db.store_embedding(
           content_id=content_id,
           content_type=item["content_type"],      # NEW
           source="babylon",                        # NEW
           embed_type="module",
           module_title=mod_emb["module_title"],
           content_text=mod_emb["content_text"],
           embedding=mod_emb["embedding"],
       )
   ```

8. **Scan status** — Change `wctx.db.set_scan_status(ci_name, "success")` to `wctx.db.set_scan_status(content_id, "success")` (Task 3i re-keyed this method).

9. **Complete scan** — Change `wctx.db.complete_scan(ci_name, ...)` to `wctx.db.complete_scan(content_id, ...)`.

10. **Content hash donor lookup** — Change `db.find_donor_by_content_hash(content_hash, exclude_ci=ci_name)` to `db.find_donor_by_content_hash(content_hash, exclude_content_id=content_id)` (Task 4g).

11. **Return value** — Add `content_id` alongside `ci_name` in return dicts:
    ```python
    return {"content_id": content_id, "ci_name": ci_name, "success": True}
    ```

#### 6d. UPDATE: `_propagate_to_sibling()` in scan.py — re-keyed + card denormalization

Current signature: `_propagate_to_sibling(db, sib_name, analysis_data, result)`
New signature: `_propagate_to_sibling(db, sib_content_id, sib_content_type, analysis_data, result)`

Changes:

1. **Re-key analysis_data for the sibling** — Replace `sib_data["ci_name"] = sib_name` with `sib_data["content_id"] = sib_content_id`.

2. **Upsert analysis** — `db.upsert_showroom_analysis(sib_data)` — already re-keyed in Task 4a.

3. **NEW: Denormalize card to sibling's content_entities** — After upserting showroom_analysis for the sibling, also update its content_entities card:
   ```python
   db.update_content_entity_card(
       sib_content_id,
       summary=analysis_data.get("summary"),
       products_json=analysis_data.get("products_json"),
       topics_json=analysis_data.get("topics_json"),
       audience_json=analysis_data.get("audience_json"),
       difficulty=analysis_data.get("difficulty"),
   )
   ```
   This ensures that siblings get the same card data on content_entities as the primary item.

4. **Embeddings** — Change `db.clear_embeddings(sib_name)` to `db.clear_embeddings(sib_content_id)`. Change `db.store_embedding(ci_name=sib_name, ...)` to `db.store_embedding(content_id=sib_content_id, content_type=sib_content_type, source="babylon", ...)`.

5. **Scan status** — Change `db.set_scan_status(sib_name, "success")` to `db.set_scan_status(sib_content_id, "success")`.

#### 6e. UPDATE: Sibling propagation in `run_analysis()` — content_id throughout

The sibling propagation block (lines 127-173 of scan.py) iterates through three sibling sources: ref-based siblings, SHA siblings, and published CI promotion. All need re-keying:

1. **Ref-based siblings** — `wctx.db.get_siblings_by_showroom(effective_url, ref)` returns a list of dicts. The returned dicts now include `content_id` alongside `ci_name` (the method was updated in Task 4q). Change the loop:
   ```python
   siblings = wctx.db.get_siblings_by_showroom(effective_url, item.get("showroom_ref"))
   for sibling in siblings:
       sib_content_id = sibling["content_id"]
       if sib_content_id in propagated_set:
           continue
       _propagate_to_sibling(wctx.db, sib_content_id, sibling.get("content_type", "lab"), analysis_data, result)
       propagated_set.add(sib_content_id)
   ```

2. **SHA siblings** — The `sha_siblings` list items now carry `content_id` (from 6b). Change:
   ```python
   for sha_sib in sha_siblings:
       sib_content_id = sha_sib["content_id"]
       if sib_content_id in propagated_set:
           continue
       sib_item = wctx.db.get_babylon_item(sib_content_id)
       sib_content_type = (sib_item or {}).get("content_type", "lab")
       _propagate_to_sibling(wctx.db, sib_content_id, sib_content_type, analysis_data, result)
       propagated_set.add(sib_content_id)
   ```

3. **Published CI promotion** — Currently uses `wctx.db.get_catalog_item(scanned_name)` to look up `published_ci_name`. Change to `wctx.db.get_babylon_item(scanned_content_id)` and derive `pub_content_id = f"babylon:{pub_name}"`:
   ```python
   for scanned_content_id in list(propagated_set):
       scanned_item = wctx.db.get_babylon_item(scanned_content_id) if scanned_content_id != content_id else item
       pub_name = (scanned_item or {}).get("published_ci_name")
       if pub_name:
           pub_content_id = f"babylon:{pub_name}"
           if pub_content_id not in propagated_set:
               pub_item = wctx.db.get_babylon_item(pub_content_id)
               if not pub_item:
                   log.info("published_ci_skipped", base=scanned_content_id, published=pub_name, reason="not found")
                   continue
               _propagate_to_sibling(wctx.db, pub_content_id, pub_item.get("content_type", "lab"), analysis_data, result)
               propagated_set.add(pub_content_id)
   ```

4. **`propagated_set` uses content_ids** — Change from tracking ci_names to tracking content_ids. Initialize with `{content_id}` instead of `{ci_name}`.

#### 6f. UPDATE: Analysis enqueue in nightly pipeline (ops.py)

The nightly pipeline Step 3 (lines 296-330 of ops.py) enqueues analysis jobs:

```python
items = wctx.db.get_items_needing_analysis()
# ...
await arq_redis.enqueue_job(
    "run_analysis", job_id=sub_job_id, ci_name=item["ci_name"],
    sha_siblings=sha_siblings_map.get(item["ci_name"]),
    _queue_name="arq:queue:scan"
)
```

Changes:

1. **`get_items_needing_analysis()`** — Updated in Task 4q. Returns items with `content_id` alongside `ci_name`. Filters to `content_type IN ('lab', 'demo')` (sandboxes excluded).

2. **Enqueue with content_id** — Change `ci_name=item["ci_name"]` to `content_id=item["content_id"]`:
   ```python
   await arq_redis.enqueue_job(
       "run_analysis", job_id=sub_job_id,
       content_id=item["content_id"],                    # was ci_name
       sha_siblings=sha_siblings_map.get(item["ci_name"]),
       _queue_name="arq:queue:scan"
   )
   ```

3. **SHA siblings map key** — `sha_dedup_scan_items()` still keys the siblings map by `ci_name` (for compatibility with the dedup logic). The lookup `sha_siblings_map.get(item["ci_name"])` still works because the map is keyed by the representative's ci_name. However, the sibling entries now include `content_id` (per 6b).

#### 6g. UPDATE: `get_items_needing_analysis()` return shape

The database method (updated in Task 4q) returns items needing analysis. The response must include both `content_id` and all fields needed by `run_analysis()`:

```python
# Returned fields per item:
{
    "content_id": "babylon:openshift-cnv.ocp4-getting-started.prod",
    "ci_name": "openshift-cnv.ocp4-getting-started.prod",
    "content_type": "lab",
    "display_name": "OpenShift Getting Started",
    "category": "Workshop",
    "showroom_url": "https://github.com/...",
    "showroom_ref": "main",
    "showroom_url_override": None,
    "content_path": None,
    "stage": "prod",
    "keywords": [...],
    "scan_status": "not_scanned",
    "content_hash": None,          # from showroom_analysis, for donor lookup
    "last_repo_commit": None,      # from showroom_analysis
}
```

The query joins `content_entities` + `babylon_items` + LEFT JOIN `showroom_analysis`:
- Filters: `ce.content_type IN ('lab', 'demo')`, `ce.retired_at IS NULL`, `bi.showroom_url IS NOT NULL`
- Condition: `sa.content_id IS NULL` (never analyzed) OR `sa.is_stale = TRUE` (content changed) OR `bi.scan_status = 'not_scanned'`
- Excludes published CIs that have a base CI with analysis (published CIs get analysis through propagation)

**Validation criteria:**
- `run_stale_check()` only checks `content_type IN ('lab', 'demo')` items — no sandboxes
- `run_stale_check()` correctly calls `mark_stale(content_id)` and `clear_stale(content_id)`
- `run_analysis()` accepts `content_id` parameter and works end-to-end
- After analysis, both `showroom_analysis` and `content_entities` have the card fields populated
- Embeddings stored with `content_type` and `source` columns
- Embed type for summary is `"summary"` (not `"ci_summary"`)
- Sibling propagation updates BOTH `showroom_analysis` AND `content_entities` card fields for each sibling
- Published CI promotion resolves through `babylon_items.published_ci_name`
- SHA dedup siblings carry `content_id` in the sibling entries
- `get_items_needing_analysis()` excludes sandboxes and returns correct fields
- Propagated count is accurate in job results
- `python -m pytest tests/ -v -k "test_analysis or test_scan or test_stale"` passes

---

### Task 7: Sandbox Summary Generation (NEW pipeline step)

**Files to create:**
- `src/api/rcars/services/sandbox_summary.py` — summary assembly logic

**Files to modify:**
- `src/api/rcars/workers/ops.py` — new `run_sandbox_summary()` function, integrate into nightly pipeline

**Dependencies:** Task 1 (schema), Task 3 (content entity methods), Task 4 (`update_content_entity_card()`, `store_embedding()`), Task 5 (catalog refresh must populate content_entities with `content_type='sandbox'`)

**What to do:**

This is an entirely new pipeline step. Sandboxes have no Showroom content to analyze, but they must be searchable. Their card fields on content_entities are populated from infrastructure metadata and the existing workload classification data in `workload_mapping`.

#### 7a. NEW: `services/sandbox_summary.py` — summary assembly service

Create a new service module with the core summary generation logic. This service is stateless — it takes data in, returns structured data out. The worker function handles database reads/writes.

```python
"""Sandbox summary generation from infrastructure metadata and workload classifications.

Assembles summary, products, and topics for sandbox-type content entities
using data already stored in workload_mapping (LLM-classified Ansible roles)
and babylon_items (CRD infrastructure metadata). No additional LLM calls.
"""

def build_sandbox_summary(
    display_name: str,
    description: str | None,
    cloud_provider: str | None,
    ocp_version: str | None,
    agd_config: str | None,
    workload_products: list[dict],   # [{product_name, description, category}, ...]
) -> dict:
    """Assemble a sandbox summary from infrastructure metadata.

    Returns dict with: summary, products_json, topics_json
    """
```

The `workload_products` parameter comes from joining `babylon_item_workloads` with `workload_mapping`. Each entry has `product_name`, `description`, and `category` from the workload_mapping table (these are already LLM-classified by the nightly workload scanner — no fresh LLM call needed).

**Summary assembly logic:**

```python
def build_sandbox_summary(...) -> dict:
    # Build products list from workload classifications
    products = sorted(set(wp["product_name"] for wp in workload_products if wp.get("product_name")))

    # Build topics from workload categories + cloud provider
    topics = set()
    for wp in workload_products:
        if wp.get("category"):
            topics.add(wp["category"])
    if cloud_provider:
        topics.add(f"{cloud_provider} infrastructure")
    if ocp_version:
        topics.add("OpenShift")
    topics = sorted(topics)

    # Assemble summary text
    parts = []
    if description:
        parts.append(description.strip().rstrip(".") + ".")

    if cloud_provider and ocp_version:
        parts.append(f"Runs on {cloud_provider} with OpenShift {ocp_version}.")
    elif cloud_provider:
        parts.append(f"Runs on {cloud_provider}.")
    elif ocp_version:
        parts.append(f"Runs on OpenShift {ocp_version}.")

    if agd_config:
        parts.append(f"Infrastructure config: {agd_config}.")

    if products:
        if len(products) <= 3:
            parts.append(f"Includes: {', '.join(products)}.")
        else:
            parts.append(f"Includes {len(products)} products: {', '.join(products[:3])}, and {len(products) - 3} more.")

    summary = " ".join(parts) if parts else f"Sandbox environment: {display_name}."

    return {
        "summary": summary,
        "products_json": products,
        "topics_json": topics,
    }
```

This is template-based assembly from already-classified data. The workload scanner has already done the hard work of LLM-classifying Ansible roles into product names and categories. We are just assembling human-readable text from those classifications.

#### 7b. NEW: `run_sandbox_summary()` in ops.py

Add a new async function to ops.py that orchestrates the sandbox summary generation:

```python
async def run_sandbox_summary(ctx: dict, job_id: str) -> dict:
    """Generate summaries for sandbox-type content entities from infrastructure metadata."""
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("picked_up", action="picked_up", queue="ops")
    wctx.db.update_job_status(job_id, "running")

    try:
        # Query sandboxes needing summary generation
        sandboxes = wctx.db.get_sandboxes_needing_summary()
        # ...
```

**Database method needed: `get_sandboxes_needing_summary()`**

Add to `database.py`:

```python
def get_sandboxes_needing_summary(self) -> list[dict]:
    """Get sandbox content entities that need summary generation.

    Returns sandboxes where:
    - summary is NULL (never generated), OR
    - updated_at on content_entities is older than last workload sync
      (workloads may have changed since last summary)
    """
    sql = """
        SELECT ce.content_id, ce.display_name, ce.summary,
               bi.ci_name, bi.description, bi.cloud_provider,
               bi.ocp_version, bi.agd_config
        FROM content_entities ce
        JOIN babylon_items bi ON bi.content_id = ce.content_id
        WHERE ce.content_type = 'sandbox'
          AND ce.retired_at IS NULL
          AND (ce.summary IS NULL
               OR ce.updated_at < (
                   SELECT COALESCE(MAX(wss.last_scanned), '1970-01-01')
                   FROM workload_scan_state wss
               ))
    """
    with self._pool.connection() as conn:
        return conn.execute(sql).fetchall()
```

**`run_sandbox_summary()` flow:**

1. Call `get_sandboxes_needing_summary()` to get the list.
2. For each sandbox:
   a. Look up its workloads: `get_workloads(content_id)` returns `[{workload_fqcn, workload_role, workload_collection}, ...]`.
   b. For each workload_role, look up the classification: query `workload_mapping` by `workload_role` to get `product_name`, `description`, `category`.
   c. Call `build_sandbox_summary()` with the assembled data.
   d. Call `update_content_entity_card(content_id, summary, products_json, topics_json)`.
   e. Generate a summary embedding:
      ```python
      from rcars.services.analyzer import generate_embedding
      embed_text = f"Environment: {summary}"  # content type prefix per spec section 5
      embedding = generate_embedding(embed_text)
      db.clear_embeddings(content_id)
      db.store_embedding(
          content_id=content_id,
          content_type="sandbox",
          source="babylon",
          embed_type="summary",
          content_text=embed_text,
          embedding=embedding,
      )
      ```
   f. Log the result.

3. Return summary dict with counts.

**Database method needed: `get_workload_classifications(content_id)`**

This joins `babylon_item_workloads` with `workload_mapping` to get the product classifications for a content entity's workloads:

```python
def get_workload_classifications(self, content_id: str) -> list[dict]:
    """Get workload classifications for a content entity via workload_mapping."""
    sql = """
        SELECT wm.product_name, wm.description, wm.category
        FROM babylon_item_workloads biw
        JOIN workload_mapping wm ON wm.workload_role = biw.workload_role
        WHERE biw.content_id = %(content_id)s
          AND wm.verified = TRUE
    """
    with self._pool.connection() as conn:
        return conn.execute(sql, {"content_id": content_id}).fetchall()
```

Only verified workload mappings are included — unverified LLM classifications are excluded to avoid propagating low-confidence data.

#### 7c. Integrate into nightly pipeline as Step 4b

Insert the sandbox summary step into `run_nightly_pipeline()` in ops.py, AFTER Step 4 (workload scan) and BEFORE Step 5 (reporting sync):

```python
# Step 4b: Sandbox summary generation (after workload scan, before reporting sync)
sandbox_summary_result = None
try:
    await publish_progress(wctx.relay, job_id, wctx.db,
                           phase="pipeline:sandbox_summary", status="running",
                           message="Step 4b: Generating sandbox summaries from workload metadata...")
    sandbox_job_id = wctx.db.create_job(job_type="sandbox_summary", queue="ops", created_by="maintenance")
    sandbox_summary_result = await run_sandbox_summary(ctx, sandbox_job_id)
    generated = sandbox_summary_result.get("generated", 0)
    skipped = sandbox_summary_result.get("skipped", 0)
    step4b_msg = f"Step 4b complete: {generated} sandbox summaries generated, {skipped} unchanged"
    await publish_progress(wctx.relay, job_id, wctx.db,
                           phase="pipeline:sandbox_summary", status="complete",
                           message=step4b_msg)
    log.info("pipeline_sandbox_summary_complete", action="pipeline_step_complete",
             step="sandbox_summary", generated=generated, skipped=skipped)
except Exception as e:
    msg = f"Step 4b failed (sandbox summary): {e}"
    warnings.append(msg)
    log.error("pipeline_sandbox_summary_failed", action="pipeline_step_failed",
              step="sandbox_summary", error=str(e), traceback=traceback.format_exc())
    await publish_progress(wctx.relay, job_id, wctx.db,
                           phase="pipeline:sandbox_summary", status="failed", message=msg)
```

Add `"sandbox_summary": sandbox_summary_result` to the pipeline result dict.

#### 7d. Embedding text prefix for sandboxes

Per spec section 5, the text passed to the embedding model includes a content type prefix. For sandboxes:

```python
embed_text = f"Environment: {summary}"
```

This places sandbox embeddings in a distinguishable region of vector space while still allowing cross-type search. A query like "I need an AWS environment with OpenShift" will match both the sandbox's summary embedding AND any lab that covers AWS+OpenShift.

#### 7e. Edge cases

- **Sandbox with no workloads** — If `babylon_item_workloads` has no entries for this content_id (the CRD had no workloads field or it was empty), the summary is assembled from CRD metadata alone (display_name, description, cloud_provider, ocp_version). The `products_json` will be empty. This is fine — the item is still searchable by its infrastructure description.

- **Sandbox with unverified workloads only** — If all workload mappings are `verified = FALSE`, they are excluded (per 7b). Same treatment as "no workloads." Curators can verify workload mappings via the Workloads page to improve sandbox coverage.

- **Sandbox with no metadata at all** — If the sandbox has no CRD description, no cloud_provider, no ocp_version, and no workloads, the summary degenerates to `"Sandbox environment: {display_name}."`. The embedding will have minimal semantic content but the item is at least present in the search space.

**Validation criteria:**
- `build_sandbox_summary()` produces correct summary text for:
  - Sandbox with full metadata: cloud_provider + ocp_version + 3 workload products = rich summary
  - Sandbox with partial metadata: cloud_provider only = partial summary
  - Sandbox with no metadata: display_name-only fallback
- `run_sandbox_summary()` correctly joins `babylon_item_workloads` with `workload_mapping` to get product classifications
- Only `verified = TRUE` workload mappings are used
- `update_content_entity_card()` is called for each sandbox with summary, products_json, topics_json
- Summary embedding is stored with `content_type='sandbox'`, `source='babylon'`, `embed_type='summary'`
- Embedding text has the `"Environment: "` prefix
- `get_sandboxes_needing_summary()` returns sandboxes where summary is NULL or workloads changed
- Step 4b runs AFTER Step 4 (workload scan) in the nightly pipeline — ordering is critical because workload mappings feed the summary
- Pipeline does not fail if no sandboxes need summarization (graceful empty case)
- `python -m pytest tests/ -v -k "test_sandbox"` passes

---

### Task 8: Reporting Sync to Performance Metrics

**Files to modify:**
- `src/api/rcars/services/reporting_sync.py` — `run_reporting_sync()`, `_merge_published_base_pairs()`

**Dependencies:** Task 1 (schema), Task 3 (content entity methods), Task 4 (`upsert_performance_channels()`, `upsert_performance_score()`, `delete_orphan_performance_data()`), Task 5 (catalog refresh must populate babylon_items with ci_name for base-name resolution)

**What to do:**

The reporting sync fetches data from the RHDP Reporting MCP server, computes metrics and retirement scores, and writes them locally. The data source and scoring formula are unchanged for Phase 1 — only the output tables change from `reporting_metrics` to `performance_channels` + `performance_scores`.

#### 8a. UPDATE: `run_reporting_sync()` — output table changes

The function structure stays the same: fetch MCP data, merge, compute scores, upsert. The changes are at the boundary where data is written to the database.

**Key change: `catalog_base_name` to `content_id` resolution**

The reporting MCP returns data keyed by `catalog_base_name` (e.g., `openshift-cnv.ocp4-getting-started`). This is a base name WITHOUT a stage suffix. The new schema needs a `content_id` which has the `babylon:` prefix and INCLUDES the stage suffix.

Resolution strategy — find the content_id for a base name:

```python
def _resolve_base_name_to_content_id(db, base_name: str) -> str | None:
    """Resolve a reporting base name to a content_id via babylon_items.

    Tries stages in priority order: prod > event > dev > test.
    Returns the content_id of the first match, or None.
    """
    for suffix in (".prod", ".event", ".dev", ".test"):
        ci_name = f"{base_name}{suffix}"
        item = db.get_babylon_item_by_ci_name(ci_name)
        if item and not item.get("retired_at"):
            return item["content_id"]
    # Fall back to any retired variant (data should still be tracked)
    for suffix in (".prod", ".event", ".dev", ".test"):
        ci_name = f"{base_name}{suffix}"
        item = db.get_babylon_item_by_ci_name(ci_name)
        if item:
            return item["content_id"]
    return None
```

This is called once per unique `catalog_base_name` in the sync data. Cache the results to avoid repeated lookups:

```python
content_id_cache: dict[str, str | None] = {}
for name in filtered_names:
    content_id_cache[name] = _resolve_base_name_to_content_id(db, name)
```

Items that cannot be resolved (orphaned reporting data with no corresponding Babylon CI) are logged and skipped.

**Alternative: Batch resolution via a single SQL query**

For better performance, add a database method that resolves all base names at once:

```python
def resolve_base_names_to_content_ids(self, base_names: set[str]) -> dict[str, str]:
    """Resolve reporting base names to content_ids via babylon_items.

    For each base name, finds the best babylon_item (preferring prod, then event, dev, test).
    Returns {base_name: content_id} for items that have a match.
    """
    if not base_names:
        return {}
    sql = """
        SELECT bi.ci_name, bi.content_id, ce.retired_at,
               CASE bi.stage
                   WHEN 'prod' THEN 1 WHEN 'event' THEN 2
                   WHEN 'dev' THEN 3 WHEN 'test' THEN 4
                   ELSE 5
               END AS stage_priority
        FROM babylon_items bi
        JOIN content_entities ce ON ce.content_id = bi.content_id
        ORDER BY stage_priority, ce.retired_at NULLS FIRST
    """
    result = {}
    with self._pool.connection() as conn:
        rows = conn.execute(sql).fetchall()
    for row in rows:
        ci_name = row["ci_name"]
        for suffix in STAGE_SUFFIXES:
            if ci_name.endswith(suffix):
                base = ci_name[:-len(suffix)]
                if base in base_names and base not in result:
                    result[base] = row["content_id"]
                break
    return result
```

#### 8b. UPDATE: Merged row format — add content_id, drop display_name

The `merged_rows` list currently has dicts with `catalog_base_name` as the key. Add `content_id` to each row after resolution:

```python
resolved_ids = db.resolve_base_names_to_content_ids(filtered_names)

merged_rows = []
unresolved_count = 0
for name in filtered_names:
    content_id = resolved_ids.get(name)
    if not content_id:
        log.warning("unresolved_base_name", base_name=name, reason="no babylon_item found")
        unresolved_count += 1
        continue
    # ... build row as before, but add content_id and rename fields ...
    merged_rows.append({
        "content_id": content_id,              # NEW
        "catalog_base_name": name,             # kept for merge logic
        "channel": "rhdp",                     # NEW: always 'rhdp' for Phase 1
        "provisions": provisions,
        "unique_users": int(prov.get("unique_users", 0)),
        "requests": int(prov.get("requests", 0)),
        "completions": int(prov.get("experiences", 0)),    # renamed: experiences → completions
        "pipeline_touched": touched_data.get(name, 0.0),   # renamed: touched_amount → pipeline_touched
        "closed_amount": closed_data.get(name, 0.0),
        "total_cost": total_cost,
        "avg_cost_per_provision": round(total_cost / provisions, 2) if provisions > 0 else 0,
        "success_ratio": float(prov.get("success_ratio", 0) or 0),
        "first_activity": first_provisions.get(name),       # renamed: first_provision → first_activity
        "last_activity": (dates.get("last_provision", "") or None),  # renamed
        "windowed_metrics": json.dumps(windowed.get(name, {})),
    })
```

#### 8c. UPDATE: `_merge_published_base_pairs()` — resolve through babylon_items

The current function uses `pub_base_map` from `db.get_published_base_mapping()`. This method queries `catalog_items` for `published_ci_name`/`base_ci_name` relationships.

Changes:

1. **`get_published_base_mapping()`** — Already updated in Task 4o to query `babylon_items` instead of `catalog_items`. Returns `{base_name: published_name}` where names are still catalog base names (stage suffix stripped).

2. **`_merge_published_base_pairs()`** — The function operates on `merged_rows` keyed by `catalog_base_name`. The `catalog_base_name` field is kept on the rows specifically for this merge step. After the merge, the `catalog_base_name` field is no longer needed — only `content_id` matters for the database write.

   The function body needs minimal changes: it already merges by `catalog_base_name`. The only structural change is that after merge, the surviving row (the published CI row) keeps its `content_id` and the base CI row is removed. This is correct because the reporting data should be attributed to the published CI's content_id.

3. **Post-merge content_id resolution for backfill items** — Items added via catalog backfill (items in babylon_items but not in reporting data) also need content_id resolution. These are resolved the same way: `catalog_base_name` → `content_id` via `resolve_base_names_to_content_ids()`.

#### 8d. UPDATE: Score computation — write to performance_scores

Currently the score is written as a column on `reporting_metrics`:

```python
row["retirement_score"] = compute_retirement_score(...)
```

Change to write scores to the separate `performance_scores` table after upserting channels:

```python
# 1. Upsert channel data
channel_rows = [{
    "content_id": row["content_id"],
    "channel": "rhdp",
    "provisions": row["provisions"],
    "unique_users": row["unique_users"],
    "requests": row["requests"],
    "completions": row["completions"],
    "pipeline_touched": row["pipeline_touched"],
    "closed_amount": row["closed_amount"],
    "total_cost": row["total_cost"],
    "avg_cost_per_provision": row["avg_cost_per_provision"],
    "success_ratio": row["success_ratio"],
    "first_activity": row["first_activity"],
    "last_activity": row["last_activity"],
    "windowed_metrics": row["windowed_metrics"],
} for row in merged_rows]
upserted = db.upsert_performance_channels(channel_rows)

# 2. Upsert scores
for row in merged_rows:
    score = row["retirement_score"]
    # Extract windowed breakdown for score_breakdown
    wm = json.loads(row["windowed_metrics"]) if isinstance(row["windowed_metrics"], str) else row["windowed_metrics"]
    # Use the 12m window breakdown as the primary breakdown
    breakdown_12m = wm.get("12m", {}).get("score_breakdown")
    db.upsert_performance_score(
        content_id=row["content_id"],
        score=score,
        breakdown=breakdown_12m,
        channel_scores={"rhdp": {"score": score}},   # Phase 1: single channel
    )
```

#### 8e. UPDATE: Orphan cleanup

Replace `db.delete_orphan_reporting_metrics(synced_names)` with `db.delete_orphan_performance_data(synced_content_ids)`:

```python
synced_content_ids = {r["content_id"] for r in merged_rows}
orphans = db.delete_orphan_performance_data(synced_content_ids)
```

The `delete_orphan_performance_data()` method (defined in Task 4o) deletes from both `performance_channels` and `performance_scores` where `content_id` is not in the synced set AND not in the current `content_entities` catalog.

#### 8f. UPDATE: Windowed metrics score recomputation

`_recompute_windowed_scores()` stays the same internally — it computes per-window retirement scores using the same formula. The only change is that windowed metrics now also include score data that will be written to `performance_scores.score_breakdown`. No field renaming needed inside the windowed metrics JSONB (the `retirement_score` key inside windowed metrics is fine — it is the same 4-factor score).

#### 8g. UPDATE: Catalog base names backfill

The current code calls `db.get_catalog_base_names()` to find items in the local catalog that are missing from reporting data. This method (updated in Task 4o) now queries `babylon_items` instead of `catalog_items`. It returns `{base_name: display_name}` by stripping stage suffixes from `babylon_items.ci_name`.

The backfill loop creates zero-value rows for missing items. These rows also need content_id resolution via `resolve_base_names_to_content_ids()`.

#### 8h. Scoring formula — UNCHANGED for Phase 1

The four-factor model (usage, pipeline, sales, ROI) with age discount is identical. The functions `compute_retirement_score()`, `compute_retirement_score_breakdown()`, and `compute_sales_impact()` are not modified. The same percentile-rank logic applies, using the same peer groups (non-zero items in the sync set).

Multi-channel scoring (combining RHDP + Interactive Labs + Web) is Phase 2. For Phase 1, `channel_scores` on `performance_scores` always contains `{"rhdp": {"score": N}}`.

#### 8i. Summary dict updates

Update the return dict to reflect the new table names and include unresolved count:

```python
summary = {
    "synced": upserted,
    "scores_written": len(merged_rows),
    "orphans_removed": orphans,
    "unresolved": unresolved_count,
    "catalog_backfilled": len(missing),
    "published_base_merged": merged_pairs,
    "provisions_rows": len(prov_data),
    "touched_rows": len(touched_data),
    "closed_rows": len(closed_data),
    "cost_rows": len(cost_data),
    "date_rows": len(date_data),
}
```

**Validation criteria:**
- `run_reporting_sync()` writes to `performance_channels` (channel='rhdp') instead of `reporting_metrics`
- `run_reporting_sync()` writes scores to `performance_scores` instead of `reporting_metrics.retirement_score`
- `catalog_base_name` to `content_id` resolution correctly prefers `.prod` variants
- Unresolved base names (no matching babylon_item) are logged and skipped, not silently dropped
- `_merge_published_base_pairs()` correctly merges metrics from base CI into published CI
- Row counts: `performance_channels` rows = merged_rows count, `performance_scores` rows = merged_rows count
- Scoring formula produces identical scores as the old code for the same input data (regression test)
- `delete_orphan_performance_data()` cleans up items not in the sync set and not in the catalog
- Windowed metrics JSONB structure is preserved (same keys, same per-window scores)
- Pipeline completes without errors when reporting MCP is configured
- `python -m pytest tests/ -v -k "test_reporting or test_sync"` passes

---

## Part 3 — Advisor Pipeline, API Routes, Frontend, Deploy/Validate

### Task 9: Advisor Pipeline (vector_search, triage, rationale, pipeline, models)

**Files to modify:**
- `src/api/rcars/services/recommender/models.py` — Candidate and QueryState dataclasses
- `src/api/rcars/services/recommender/vector_search.py` — search function and CI reference resolution
- `src/api/rcars/services/recommender/triage.py` — candidate formatting and triage scoring
- `src/api/rcars/services/recommender/rationale.py` — per-candidate rationale formatting
- `src/api/rcars/services/recommender/pipeline.py` — usage boost and query orchestration

**Dependencies:** Task 1 (schema), Task 3 (content entity CRUD), Task 4 (`search_embeddings()`, `get_showroom_analysis()`, performance methods), Task 5 (catalog refresh populates content_entities)

**What to do:**

The advisor pipeline has four phases: vector search, triage, rationale, and synthesis. All four need re-keying from `ci_name` to `content_id`, and the Candidate dataclass needs new fields for the generalized model. Phase 1 behavior is identical — only Babylon content exists, no new card layouts or grouping.

#### 9a. UPDATE: `models.py` — Candidate dataclass additions

Add new fields to the `Candidate` dataclass. `content_id` becomes the primary identifier; `ci_name` becomes nullable for backward compatibility with non-Babylon content types.

```python
@dataclass
class Candidate:
    """A content entity moving through the recommendation pipeline."""

    # Primary identity (new)
    content_id: str
    content_type: str                        # 'lab', 'demo', 'sandbox', 'architecture', etc.
    source: str                              # 'babylon', 'portfolio_arch', etc.
    is_hands_on: bool = True

    # Backward compat and display
    ci_name: str | None = None               # Nullable — None for non-Babylon content
    display_name: str = ""
    category: str = ""
    summary: str = ""
    topics: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    difficulty: str = ""
    duration_min: int | None = None
    content_type: str = ""                   # NOTE: content_type appears above; this duplicate is intentional in the current code for analysis content_type vs entity content_type. Reconcile: use a single field.
    stage: str = "prod"
    duration_source: str = "ai"
    catalog_namespace: str = ""
    base_ci_name: str | None = None
    learning_objectives: list[str] = field(default_factory=list)

    # Vector search metadata (new)
    best_match_type: str = ""                # which embedding matched best: 'summary', 'module'
    best_match_detail: str | None = None     # module_title or section that matched

    # Existing pipeline fields (unchanged)
    tier: str = "white"
    vector_distance: float = 0.0
    vector_similarity_pct: int = 0
    provisions_quarter: int | None = None
    relevance_score: int | None = None
    relevant: bool | None = None
    one_line_reason: str | None = None
    rationale: str | None = None
    why_it_fits: str | None = None
    how_to_use: str | None = None
    suggested_format: str | None = None
    duration_notes: str | None = None
    caveats: str | None = None
```

**Reconciliation:** The current `Candidate` has a `content_type` field populated from `showroom_analysis.content_type`. The new model has `content_type` from `content_entities.content_type`. These should be the same field — remove the duplicate. The value comes from `content_entities` at search time and flows through the pipeline.

Also update `similarity_pct()` — the new search returns similarity (0-1) directly instead of distance. Add a new static method:

```python
@staticmethod
def from_similarity(similarity: float) -> int:
    """Convert cosine similarity (0-1) to percentage."""
    return round(similarity * 100)
```

Keep the existing `similarity_pct(distance)` for any remaining code paths that use distance.

**QueryState additions:**

```python
@dataclass
class QueryState:
    phase: str
    candidates: list[Candidate]
    query: str = ""
    overall_assessment: str | None = None
    content_gaps: list[str] | None = None
    grouped_results: dict[str, list[Candidate]] | None = None   # NEW: typed grouping for Phase 2
    timings: dict[str, float] = field(default_factory=dict)
    token_usage: list[dict] = field(default_factory=list)
```

The `grouped_results` field is prepared for Phase 2 typed grouping. In Phase 1 it is `None` (all results are hands-on Babylon items, no grouping needed).

#### 9b. UPDATE: `vector_search.py` — `search()` function rewrite

The search function changes significantly because the underlying `db.search_embeddings()` was rewritten in Task 4f to return MAX(similarity) per content_id instead of raw distance-ordered rows.

**New search flow:**

1. **Generate query embedding** — unchanged.

2. **Call `db.search_embeddings()`** — the rewritten method (Task 4f) returns grouped results with `content_id`, `content_type`, `source`, `best_similarity`, `best_match_type`, `best_match_module`, plus metadata from content_entities and babylon_items JOINs. Results are already grouped by content_id (MAX similarity), so the manual `rows_by_content` dedup loop is eliminated.

3. **CI reference resolution** — `_resolve_ci_references()` needs updating:
   - `db.find_catalog_item_by_display_name_prefix()` becomes a query against `content_entities ce JOIN babylon_items bi` (already updated in Task 3i). Returns the item with `content_id`.
   - `db.get_embedding(embed_ci, embed_type="ci_summary")` changes to `db.get_embedding(content_id, embed_type="summary")` — the embed_type name changed from `ci_summary` to `summary` (Task 1d/6c).
   - The neighbor search calls `db.search_embeddings()` with the referenced item's embedding. The returned neighbors have `content_id`, so dedup uses `content_id` instead of `ci_name`.
   - The `seen` set tracks `content_id` instead of `ci_name`.

4. **Content-based dedup** — The old manual dedup by `(showroom_url, showroom_ref)` and `content_hash` is **removed**. The new `search_embeddings()` already groups by `content_id`, and sibling propagation during analysis (Task 6) ensures each content_id has its own embeddings. Content dedup at the entity level is handled by `content_id` uniqueness. No more `rows_by_content` dict.

5. **Stage promotion** — Still needed but simplified. The current code calls `db.find_prod_ci_by_content_hash()` to swap non-prod CIs to their prod counterpart. In the new model, this is gated on `source = 'babylon'` (only Babylon items have stages):

   ```python
   if "prod" in effective_stages:
       for candidate in candidates:
           if candidate.source != "babylon" or candidate.stage == "prod":
               continue
           # Look up if a prod variant exists with the same content
           content_hash = candidate._content_hash  # carried from search results
           if not content_hash:
               continue
           prod_ci = db.find_prod_ci_by_content_hash(content_hash)
           if prod_ci and prod_ci["content_id"] != candidate.content_id:
               # Promote to prod identity
               log.info("stage_promote: %s → %s (prod)", candidate.content_id, prod_ci["content_id"])
               candidate.content_id = prod_ci["content_id"]
               candidate.ci_name = prod_ci["ci_name"]
               candidate.display_name = prod_ci.get("display_name", candidate.display_name)
               candidate.stage = "prod"
               candidate.catalog_namespace = prod_ci.get("catalog_namespace", "")
   ```

   Note: `find_prod_ci_by_content_hash()` needs updating (Task 3i already re-keyed it) to query `babylon_items bi JOIN content_entities ce JOIN showroom_analysis sa` and return `content_id` alongside `ci_name`.

6. **Published CI promotion** — The base-to-published promotion currently calls `db.get_catalog_item(row["published_ci_name"])`. This changes to `db.get_babylon_item(f"babylon:{row['published_ci_name']}")` (using the `published_ci_name` from `babylon_items`):

   ```python
   if row.get("published_ci_name") and not row.get("is_published"):
       pub_content_id = f"babylon:{row['published_ci_name']}"
       published_item = db.get_babylon_item(pub_content_id)
       if published_item:
           base_content_id = content_id
           content_id = pub_content_id
           ci_name = published_item["ci_name"]
           # ... update display fields ...
   ```

7. **Candidate construction** — Each candidate now uses `content_id` as primary identity:

   ```python
   candidates.append(Candidate(
       content_id=content_id,
       content_type=row.get("content_type", ""),
       source=row.get("source", "babylon"),
       is_hands_on=row.get("is_hands_on", True),
       ci_name=row.get("ci_name"),
       display_name=row.get("display_name", ""),
       category=row.get("category", ""),
       summary=(analysis or {}).get("summary", ""),
       topics=(analysis or {}).get("topics_json", []) or [],
       products=(analysis or {}).get("products_json", []) or [],
       difficulty=(analysis or {}).get("difficulty", ""),
       duration_min=...,  # same logic as current
       duration_source=...,
       stage=row.get("stage", "prod"),
       catalog_namespace=row.get("catalog_namespace", ""),
       base_ci_name=row.get("base_ci_name"),
       learning_objectives=learning_objs,
       best_match_type=row.get("best_match_type", "summary"),
       best_match_detail=row.get("best_match_module"),
       vector_distance=1.0 - row["best_similarity"],  # backward compat
       vector_similarity_pct=Candidate.from_similarity(row["best_similarity"]),
   ))
   ```

8. **Analysis lookup** — Currently `db.get_showroom_analysis(analysis_ci)`. Change to `db.get_showroom_analysis(analysis_content_id)` where `analysis_content_id` is the base CI's content_id (for published CIs, look up `base_ci_name` and prefix with `babylon:`). For sandboxes (no showroom_analysis), the summary/products/topics come from `content_entities` card fields directly — no analysis table lookup needed. Route the lookup by content_type:

   ```python
   if content_type in ("lab", "demo"):
       analysis_content_id = f"babylon:{row.get('base_ci_name')}" if row.get("is_published") else content_id
       analysis = db.get_showroom_analysis(analysis_content_id)
   elif content_type == "sandbox":
       # Sandbox: no analysis table — card fields on content_entities are the analysis
       entity = db.get_content_entity(content_id)
       analysis = {
           "summary": entity.get("summary", ""),
           "products_json": entity.get("products_json", []),
           "topics_json": entity.get("topics_json", []),
           "audience_json": entity.get("audience_json", []),
           "difficulty": entity.get("difficulty", ""),
       }
   else:
       analysis = {}
   ```

9. **Sort** — Sort by `best_similarity` descending (was distance ascending). The sort key changes:

   ```python
   candidates.sort(key=lambda c: -c.vector_similarity_pct)
   ```

10. **Content type filter** — Add an optional `content_types` parameter to `search()` and pass through to `db.search_embeddings()`:

    ```python
    def search(
        query: str,
        db: Database,
        limit: int = 25,
        stages: list[str] | None = None,
        content_types: list[str] | None = None,   # NEW
        distance_cutoff: float = 0.55,
        include_zt: bool = True,
    ) -> QueryState:
    ```

    The `distance_cutoff` is converted to a `quality_threshold` for the new search: `quality_threshold = 1.0 - distance_cutoff`.

#### 9c. UPDATE: `triage.py` — candidate formatting

The `format_triage_candidates()` function formats candidates for the triage prompt. Add `content_id` and `content_type` to each candidate block:

```python
def format_triage_candidates(candidates: list[Candidate]) -> str:
    parts = []
    for i, c in enumerate(candidates, 1):
        lines = [
            f"--- Candidate {i} ---",
            f"Content ID: {c.content_id}",                   # NEW
            f"Display Name: {c.display_name}",
            f"Content Type: {c.content_type}",               # existing, now from content_entities
            f"Summary: {c.summary}",
            f"Topics: {', '.join(c.topics)}",
            f"Products: {', '.join(c.products)}",
            f"Duration: {c.duration_min or '?'} min",
        ]
        # Include ci_name for Babylon items (backward compat with triage prompt)
        if c.ci_name:
            lines.insert(2, f"CI Name: {c.ci_name}")
            lines.append(f"Category: {c.category}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
```

**Triage scoring lookup key change:** The current triage response parsing uses `ci_name` to match scores back to candidates:

```python
scores_by_ci = {r["ci_name"]: r for r in triage_results ...}
```

For Phase 1, the triage prompt still includes `ci_name` for Babylon items, and the LLM returns `ci_name` in its response. No prompt change needed yet. But update the lookup to also check `content_id`:

```python
for candidate in state.candidates:
    # Try ci_name first (backward compat), then content_id
    score_data = scores_by_ci.get(candidate.ci_name) if candidate.ci_name else None
    if not score_data:
        score_data = scores_by_ci.get(candidate.content_id)
    ...
```

This handles the future case where non-Babylon content types have no `ci_name` and the triage LLM returns `content_id` instead.

**Sandbox awareness in triage prompt:** For Phase 1, add a note to the triage system prompt about sandboxes. This is a prompt file change (`src/api/rcars/prompts/triage.txt`), not a code change. Append to the instructions section:

```
Some candidates may be "sandbox" type — environments without guided content.
Evaluate these based on their infrastructure capabilities and products available,
not on learning objectives or modules (which they lack).
```

#### 9d. UPDATE: `rationale.py` — type-aware formatter routing

The `_format_single_candidate()` function formats a candidate with full analysis data for the per-candidate rationale prompt. Add type-aware routing:

```python
def _format_single_candidate(c: Candidate, analysis: dict[str, Any]) -> str:
    """Format one candidate with full analysis data for the per-candidate prompt."""
    lines = [
        f"Content ID: {c.content_id}",
        f"Display Name: {c.display_name}",
        f"Content Type: {c.content_type}",
        f"Relevance Score: {c.relevance_score or 0}%",
        f"Summary: {c.summary}",
    ]

    if c.content_type in ("lab", "demo"):
        # Lab/Demo: full showroom_analysis data
        lines.extend([
            f"Category: {c.category}",
            f"Difficulty: {c.difficulty}",
            f"Duration: {c.duration_min or '?'} min",
            f"Topics: {', '.join(c.topics)}",
            f"Products: {', '.join(c.products)}",
        ])
        audience = analysis.get("audience_json", [])
        if audience:
            lines.append(f"Audience: {', '.join(audience)}")
        objectives = analysis.get("learning_objectives_json", {})
        if isinstance(objectives, dict):
            stated = objectives.get("stated", [])
            inferred = objectives.get("inferred", [])
            if stated:
                lines.append(f"Stated Objectives: {'; '.join(stated)}")
            if inferred:
                lines.append(f"Inferred Objectives: {'; '.join(inferred)}")
        modules = analysis.get("modules_json", [])
        if modules:
            mod_titles = [m.get("title", "") for m in modules if m.get("title")]
            if mod_titles:
                lines.append(f"Modules: {'; '.join(mod_titles)}")

    elif c.content_type == "sandbox":
        # Sandbox: infrastructure metadata + workloads
        lines.extend([
            f"Topics: {', '.join(c.topics)}",
            f"Products: {', '.join(c.products)}",
        ])
        # Infrastructure details from analysis dict (populated from babylon_items)
        if analysis.get("cloud_provider"):
            lines.append(f"Cloud Provider: {analysis['cloud_provider']}")
        if analysis.get("ocp_version"):
            lines.append(f"OpenShift Version: {analysis['ocp_version']}")
        if analysis.get("agd_config"):
            lines.append(f"Infrastructure Config: {analysis['agd_config']}")
        workloads = analysis.get("workloads", [])
        if workloads:
            wl_names = [w.get("product_name") or w.get("workload_role", "") for w in workloads]
            lines.append(f"Available Workloads: {'; '.join(wl_names)}")

    else:
        # Future content types: generic format
        lines.extend([
            f"Topics: {', '.join(c.topics)}",
            f"Products: {', '.join(c.products)}",
        ])

    return "\n".join(lines)
```

**Analysis data fetching in `generate_rationale()`:** Update the analysis lookup to route by content type:

```python
analyses = {}
for c in top_candidates:
    if c.content_type in ("lab", "demo"):
        # Published CIs store analysis on their base CI
        analysis_content_id = f"babylon:{c.base_ci_name}" if c.base_ci_name and c.ci_name else c.content_id
        analysis = db.get_showroom_analysis(analysis_content_id)
        if analysis:
            analyses[c.content_id] = analysis
    elif c.content_type == "sandbox":
        # Sandbox: fetch from babylon_items + workloads
        bi = db.get_babylon_item(c.content_id)
        workload_classifications = db.get_workload_classifications(c.content_id)
        analyses[c.content_id] = {
            "cloud_provider": (bi or {}).get("cloud_provider"),
            "ocp_version": (bi or {}).get("ocp_version"),
            "agd_config": (bi or {}).get("agd_config"),
            "workloads": workload_classifications,
        }
    # Future: elif c.content_type == "architecture": ...
```

**Key change in rationale result mapping:** Replace `ci_name` with `content_id` throughout:

```python
# Before: rationale_results[ci_name] = result
# After:
rationale_results[c.content_id] = result

# Before: for c in top_candidates: rec = rationale_results.get(c.ci_name, {})
# After:
for c in top_candidates:
    rec = rationale_results.get(c.content_id, {})
```

Also update `_call_rationale_single()`:

```python
result["content_id"] = c.content_id  # was ci_name
result["ci_name"] = c.ci_name        # keep for backward compat
```

And `_build_deterministic_assessment()` — no change needed (it reads `c.display_name` and `c.why_it_fits`, which are on Candidate regardless of the identifier).

#### 9e. UPDATE: `pipeline.py` — usage boost and serialization

**`_apply_usage_boost()`** — Currently reads from `db.get_reporting_metrics(base)` via `extract_base_name(c.ci_name)`. Change to read from `performance_channels`:

```python
def _apply_usage_boost(candidates: list[Candidate], db) -> None:
    import bisect

    for c in candidates:
        # Fetch from performance_channels instead of reporting_metrics
        channels = db.get_performance_channels(c.content_id)
        if channels:
            # Sum provisions across all channels, use windowed quarterly value
            rhdp = next((ch for ch in channels if ch["channel"] == "rhdp"), None)
            if rhdp:
                wm = rhdp.get("windowed_metrics") or {}
                if isinstance(wm, str):
                    import json
                    wm = json.loads(wm)
                q = wm.get("3m", {})
                c.provisions_quarter = q.get("provisions", 0)
            else:
                c.provisions_quarter = None
        else:
            c.provisions_quarter = None

    # Rest of the function is unchanged — same percentile-based boost logic
    prov_values = [c.provisions_quarter for c in candidates if c.provisions_quarter and c.provisions_quarter > 0]
    if not prov_values:
        return
    sorted_provs = sorted(prov_values)
    # ... same boost multiplier logic ...
```

Remove the `from rcars.services.reporting_sync import extract_base_name` import — base name extraction is no longer needed because we look up directly by `content_id`.

**`serialize_candidates()`** — Update the progress serialization to include `content_id`:

```python
def serialize_candidates(candidates):
    return [
        {
            "content_id": c.content_id,                    # NEW
            "ci_name": c.ci_name,
            "display_name": c.display_name,
            "content_type": c.content_type,                # NEW
            "tier": c.tier,
            "relevance_score": c.relevance_score,
            "vector_similarity_pct": c.vector_similarity_pct,
            "stage": c.stage,
            "catalog_namespace": c.catalog_namespace,
            "duration_min": c.duration_min,
            "duration_source": c.duration_source,
            "learning_objectives": c.learning_objectives,
            "why_it_fits": c.why_it_fits,
            "how_to_use": c.how_to_use,
            "suggested_format": c.suggested_format,
            "duration_notes": c.duration_notes,
            "caveats": c.caveats,
            "provisions_quarter": c.provisions_quarter,
            "best_match_type": c.best_match_type,          # NEW
            "best_match_detail": c.best_match_detail,      # NEW
        }
        for c in candidates
    ]
```

**Green tier assignment** — Currently sorts by `c.ci_name` as tiebreaker. Change to `c.content_id`:

```python
yellow_by_score.sort(key=lambda c: (-(c.relevance_score or 0), c.content_id))
```

**`_apply_duration_penalty()`** — No structural changes needed. It reads `c.duration_min` and `c.duration_source` which are still on Candidate. Update the debug log to include `content_id`:

```python
logger.debug("duration_penalty", content_id=c.content_id, ci_name=c.ci_name, ...)
```

**Validation criteria:**
- `Candidate` dataclass has `content_id`, `content_type`, `source`, `is_hands_on`, `best_match_type`, `best_match_detail` fields
- `search()` returns candidates keyed by `content_id` with MAX(similarity) scoring — no duplicate content_ids in results
- CI reference resolution (`_resolve_ci_references()`) works with `content_id` and `embed_type="summary"`
- Stage promotion and published CI promotion use `content_id` lookups
- Sandbox candidates are constructed with card fields from `content_entities` (no showroom_analysis lookup)
- Triage formatting includes `content_id` and `content_type` in candidate blocks
- Rationale fetches analysis from `showroom_analysis` for lab/demo, from `babylon_items + workloads` for sandbox
- Usage boost reads from `performance_channels` instead of `reporting_metrics`
- Serialized candidate data includes `content_id` and `content_type`
- `python -m pytest tests/ -v -k "test_vector or test_triage or test_rationale or test_pipeline"` passes

---

### Task 10: API Routes

**Files to modify:**
- `src/api/rcars/api/routes/catalog.py` — catalog browsing and curation endpoints
- `src/api/rcars/api/routes/analysis.py` — retirement and analysis endpoints
- `src/api/rcars/api/routes/advisor.py` — advisor query and session endpoints

**Dependencies:** Task 1 (schema), Task 3 (`list_content_entities_filtered()`, `get_babylon_item()`), Task 4 (performance methods, retirement workflow methods), Task 9 (advisor pipeline returns `content_id`)

**What to do:**

All API routes that reference `catalog_items`, `ci_name` as path parameter, or `reporting_metrics` need updating. The routing URLs stay the same for Phase 1 — backward compatibility for frontends that haven't updated yet.

#### 10a. UPDATE: `catalog.py` — `GET /catalog` (list)

Change `db.list_catalog_items_filtered()` to `db.list_content_entities_filtered()`:

```python
@router.get("")
async def list_catalog(
    request: Request,
    user: str = Depends(require_auth),
    search: str | None = Query(None),
    stage: str | None = Query(None),
    content_type: str | None = Query(None),          # NEW parameter
    cloud_provider: str | None = Query(None),
    workloads: str | None = Query(None),
    agd_config: str | None = Query(None),
    content_filter: str | None = Query(None),
    category: str | None = None,
    include_retired: str = Query("false"),
    limit: int = Query(50, le=2000),
    offset: int = Query(0, ge=0),
):
    db = request.app.state.db
    stage_list = [s.strip() for s in stage.split(",")] if stage else None
    workload_list = [w.strip() for w in workloads.split(",")] if workloads else None
    content_type_list = [t.strip() for t in content_type.split(",")] if content_type else None

    return db.list_content_entities_filtered(
        search=search,
        content_types=content_type_list,               # NEW
        stages=stage_list,
        cloud_provider=cloud_provider,
        agd_config=agd_config,
        workloads=workload_list,
        content_filter=content_filter,
        category=category,
        limit=limit,
        offset=offset,
        include_retired=include_retired,
    )
```

The response shape (`{"items": [...], "total": N}`) stays the same. The items now come from `content_entities LEFT JOIN babylon_items` instead of `catalog_items`, but the response includes the same fields.

#### 10b. UPDATE: `catalog.py` — `GET /catalog/{ci_name}` (detail)

For Phase 1, keep `ci_name` as the path parameter name for URL backward compatibility, but accept either a `ci_name` or a `content_id`. The detail endpoint assembles data from multiple tables:

```python
@router.get("/{identifier}")
async def get_catalog_item(identifier: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db

    # Accept either content_id (e.g. "babylon:my-ci.prod") or ci_name (e.g. "my-ci.prod")
    if identifier.startswith("babylon:") or identifier.startswith("pa:") or identifier.startswith("ie:"):
        item = db.get_babylon_item(identifier)
        content_id = identifier
    else:
        item = db.get_babylon_item_by_ci_name(identifier)
        content_id = f"babylon:{identifier}" if item else None

    if not item:
        raise HTTPException(status_code=404, detail="Content entity not found")

    content_id = item["content_id"]
    analysis = db.get_showroom_analysis(content_id)
    tags = db.get_enrichment_tags(content_id)
    workloads = db.get_workloads(content_id) if item.get("is_agd_v2") else []
    acl_groups = db.get_acl_groups(content_id) if item.get("is_agd_v2") else []

    # Performance data (replaces reporting metrics)
    channels = db.get_performance_channels(content_id)
    perf_score = db.get_performance_score(content_id)
    reporting = None
    if channels:
        rhdp = next((ch for ch in channels if ch["channel"] == "rhdp"), None)
        if rhdp:
            from rcars.services.reporting_sync import compute_sales_impact
            reporting = {**rhdp}
            reporting["sales_impact"] = compute_sales_impact(float(rhdp.get("closed_amount", 0) or 0))
            if perf_score:
                reporting["retirement_score"] = perf_score.get("performance_score", 0)
                reporting["score_breakdown"] = perf_score.get("score_breakdown")

    return {**item, "analysis": analysis, "tags": tags,
            "workloads": workloads, "acl_groups": acl_groups,
            "reporting": reporting}
```

#### 10c. UPDATE: `catalog.py` — `GET /catalog/{ci_name}/similar`

Change to accept either identifier format:

```python
@router.get("/{identifier}/similar")
async def get_similar_items(identifier: str, request: Request, ...):
    db = request.app.state.db
    # Resolve identifier to content_id
    if identifier.startswith("babylon:"):
        content_id = identifier
        item = db.get_content_entity(content_id)
    else:
        item = db.get_babylon_item_by_ci_name(identifier)
        content_id = item["content_id"] if item else None
    if not item:
        raise HTTPException(status_code=404, detail="Content entity not found")
    similar = db.get_similar_items(content_id, min_score=min_score)
    return {"content_id": content_id, "ci_name": identifier, "similar": similar, "count": len(similar)}
```

#### 10d. UPDATE: `catalog.py` — curator endpoints (tags, notes, flag, override-url, duration, content-path)

All curator endpoints use `ci_name` as the path parameter. For Phase 1, keep the URL path as `/{ci_name}/...` but resolve to `content_id` internally:

```python
# Helper for all curator endpoints
def _resolve_to_content_id(identifier: str, db) -> str:
    """Resolve a path parameter to a content_id. Accepts ci_name or content_id."""
    if identifier.startswith("babylon:"):
        return identifier
    return f"babylon:{identifier}"
```

Then each curator endpoint changes from passing `ci_name` directly to passing `content_id`:

```python
@router.post("/{ci_name}/tags")
async def add_tag(ci_name: str, body: TagRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _resolve_to_content_id(ci_name, db)
    db.add_enrichment_tag(content_id, body.tag_type, body.tag_value, added_by=user)
    return {"status": "ok"}
```

Same pattern for: `remove_tag`, `set_note`, `flag_item`, `override_url`, `set_duration`, `set_content_path`.

#### 10e. UPDATE: `catalog.py` — infrastructure search and facets

**`GET /catalog/search/infrastructure`** — Change `db.get_workloads(item["ci_name"])` to `db.get_workloads(item["content_id"])`:

```python
for item in items:
    raw_workloads = db.get_workloads(item["content_id"])   # was item["ci_name"]
    ...
```

**`GET /catalog/facets`** — `db.get_catalog_facets()` already updated in Task 3i.

**`GET /catalog/infra-stats`** — `db.get_infra_stats()` already updated in Task 3i.

**`POST /catalog/refresh`** — No changes needed (it just enqueues the job).

#### 10f. UPDATE: `analysis.py` — `GET /analysis/retirement` (dashboard)

The retirement dashboard currently reads from `db.list_reporting_metrics()`. Change to `db.list_performance_data()` (Task 4l):

```python
@router.get("/retirement")
async def retirement_dashboard(request: Request, user: str = Depends(require_curator), ...):
    db = request.app.state.db
    window_key = WINDOW_KEYS.get(window, "12m")

    items = db.list_performance_data(
        sort_by="performance_score", sort_dir="desc",
        workflow_status=workflow_status,
    )

    # Windowed metric overlay — same logic, field names updated
    import json as _json
    for item in items:
        wm = item.get("windowed_metrics") or {}
        if isinstance(wm, str):
            wm = _json.loads(wm)
        w = wm.get(window_key, {})
        if w:
            item["provisions"] = w.get("provisions", 0)
            item["completions"] = w.get("completions", 0)     # was "experiences"
            item["requests"] = w.get("requests", 0)
            item["unique_users"] = w.get("unique_users", 0)
            item["success_ratio"] = w.get("success_ratio", 0)
            item["pipeline_touched"] = w.get("pipeline_touched", 0)  # was "touched_amount"
            item["closed_amount"] = w.get("closed_amount", 0)
            item["total_cost"] = w.get("total_cost", 0)
            item["avg_cost_per_provision"] = w.get("avg_cost_per_provision", 0)
            item["retirement_score"] = w.get("retirement_score", 0)
            item["sales_impact"] = w.get("sales_impact", "low")
            # Backward compat — keep old field names in response for frontend
            item["touched_amount"] = item["pipeline_touched"]
            item["experiences"] = item["completions"]
```

**Key change:** Items now have `content_id` as the primary key instead of `catalog_base_name`. For Phase 1 backward compatibility with the frontend, add `catalog_base_name` as a derived field in the response:

```python
for item in items:
    # Backward compat: derive catalog_base_name from content_id for frontend
    cid = item.get("content_id", "")
    if cid.startswith("babylon:"):
        base = cid.removeprefix("babylon:")
        # Strip stage suffix to get base name
        for suffix in (".prod", ".event", ".dev", ".test"):
            if base.endswith(suffix):
                base = base[:-len(suffix)]
                break
        item["catalog_base_name"] = base
    else:
        item["catalog_base_name"] = cid
```

**Stage and owner lookups:** Change `db.get_stages_for_base_names()` and `db.get_owners_for_base_names()` — these are already updated in Task 4o to work with the new schema. The parameter type is still base names.

**`has_prod` filter:** Change to use `content_id`-based lookup:

```python
if has_prod is True:
    prod_names = db.get_all_base_names_with_prod()
    items = [i for i in items if i.get("catalog_base_name") in prod_names]
```

This works because the backward compat `catalog_base_name` field is derived above.

**Score breakdown and ignored_until:** These come from `performance_scores` instead of inline on `reporting_metrics`. The `list_performance_data()` method JOINs them already.

**`get_reporting_sync_status()`** — Updated in Task 4o to query `performance_scores` and `performance_channels`.

#### 10g. UPDATE: `analysis.py` — retirement workflow endpoints

All retirement workflow endpoints use `base_name` as the path parameter. For Phase 1, keep the URL path but resolve to `content_id` internally using the same resolution logic as the reporting sync:

```python
def _base_name_to_content_id(base_name: str, db) -> str:
    """Resolve retirement base_name to content_id for workflow operations."""
    # Try known stage suffixes
    for suffix in (".prod", ".event", ".dev", ".test"):
        ci_name = f"{base_name}{suffix}"
        item = db.get_babylon_item_by_ci_name(ci_name)
        if item:
            return item["content_id"]
    # Fall back to direct content_id if it looks like one
    if base_name.startswith("babylon:"):
        return base_name
    return f"babylon:{base_name}.prod"   # best guess for retirement context
```

Then each workflow endpoint resolves before calling the DB:

```python
@router.put("/retirement/workflow/{base_name}/review")
async def review_item(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
    fields = {
        "step_reviewed_at": "NOW()",
        "step_reviewed_by": user,
        "status": "reviewed",
    }
    result = db.upsert_retirement_workflow(content_id, fields)
    db.log_action(content_id, "retirement_reviewed", user, "Marked as reviewed")
    return {"status": "ok", "workflow": result}
```

Same pattern for: `approve_item` (also update `db.get_reporting_metrics()` → `db.get_performance_channels()` + `db.get_performance_score()` for snapshot), `notify_owner`, `start_retirement`, `link_jira`, `update_notes`, `cancel_workflow`.

**`ignore_item` and `unignore_item`:** Change `db.set_ignored_until(base_name, until)` to `db.set_ignored_until(content_id, until)`:

```python
@router.put("/retirement/ignore/{base_name}")
async def ignore_item(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
    from datetime import date, timedelta
    until = (date.today() + timedelta(days=30)).isoformat()
    ok = db.set_ignored_until(content_id, until)
    ...
```

#### 10h. UPDATE: `analysis.py` — scan and rescan endpoints

**`POST /analysis/scan`** and **`POST /analysis/rescan-all`**: These enqueue `run_analysis` with `ci_name=item["ci_name"]`. Change to `content_id=item["content_id"]`:

```python
for item in scan_items:
    sub_job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
    await arq_redis.enqueue_job(
        "run_analysis", job_id=sub_job_id,
        content_id=item["content_id"],                     # was ci_name
        sha_siblings=sha_siblings_map.get(item["ci_name"]),
        _queue_name="arq:queue:scan"
    )
```

**`POST /analysis/{ci_name}`** (analyze single): Accept either ci_name or content_id:

```python
@router.post("/{identifier}")
async def analyze_single(identifier: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    # Resolve to content_id
    if identifier.startswith("babylon:"):
        content_id = identifier
    else:
        content_id = f"babylon:{identifier}"
    job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
    await arq_redis.enqueue_job("run_analysis", job_id=job_id, content_id=content_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}
```

#### 10i. UPDATE: `advisor.py` — session selection

**`POST /advisor/sessions/{session_id}/select`**: The `SelectRequest` body has `ci_name`. For Phase 1, keep accepting `ci_name` but also accept `content_id`. Store both:

```python
class SelectRequest(BaseModel):
    turn_index: int
    ci_name: str | None = None
    content_id: str | None = None

@router.post("/advisor/sessions/{session_id}/select")
async def select_recommendation(session_id: str, body: SelectRequest, ...):
    ...
    content_id = body.content_id or (f"babylon:{body.ci_name}" if body.ci_name else None)
    db.update_advisor_session_choice(
        session_id=session_id,
        turn_index=body.turn_index,
        chosen_ci_name=body.ci_name,
        chosen_content_id=content_id,
    )
    return {"status": "ok"}
```

**Validation criteria:**
- `GET /catalog` supports `content_type` filter parameter
- `GET /catalog` calls `list_content_entities_filtered()` instead of `list_catalog_items_filtered()`
- `GET /catalog/{identifier}` accepts both `ci_name` and `content_id` path parameters
- Detail endpoint assembles from content_entities + babylon_items + showroom_analysis + performance_channels
- Curator endpoints (tags, notes, flag, etc.) resolve `ci_name` to `content_id` before DB calls
- Retirement dashboard reads from `performance_channels` + `performance_scores` instead of `reporting_metrics`
- Retirement dashboard response includes backward-compat `catalog_base_name` field
- Retirement workflow endpoints resolve `base_name` to `content_id`
- Scan endpoints enqueue with `content_id` instead of `ci_name`
- Advisor session selection stores both `chosen_ci_name` and `chosen_content_id`
- `python -m pytest tests/ -v -k "test_catalog or test_analysis or test_advisor or test_route"` passes

---

### Task 11: Frontend Updates (Phase 1 — Minimal, Keep UI Identical)

**Files to modify:**
- `src/frontend/src/services/api.ts` — API client types and function signatures
- `src/frontend/src/pages/BrowsePage.tsx` — catalog browsing page
- `src/frontend/src/pages/RetirementPage.tsx` — retirement analysis page
- `src/frontend/src/components/advisor/RecCard.tsx` — recommendation card component

**Dependencies:** Task 10 (API routes must return new response shapes)

**What to do:**

Phase 1 frontend changes are strictly schema adaptation. The UI looks and behaves identically. No new visual elements, no content type badges, no grouped results. The changes are:
1. Types updated to reflect new API response shapes
2. Data access paths updated (`content_id` alongside `ci_name`)
3. Backward compatibility with existing field names in API responses

#### 11a. UPDATE: `api.ts` — type updates

**Add `content_id` to interfaces where needed:**

Update `RetirementWorkflow` interface:

```typescript
export interface RetirementWorkflow {
  content_id: string                    // NEW — primary key in new schema
  catalog_base_name: string             // KEPT — backward compat from API
  status: string
  // ... all existing step fields unchanged ...
}
```

Update `ReportingMetricsItem` interface to add new fields while keeping old ones:

```typescript
export interface ReportingMetricsItem {
  content_id: string                     // NEW
  catalog_base_name: string              // KEPT — backward compat
  display_name: string
  provisions: number
  provisions_quarter: number
  requests: number
  experiences: number                    // KEPT — API maps completions → experiences for compat
  unique_users: number
  success_ratio: number
  failure_ratio: number
  touched_amount: number                 // KEPT — API maps pipeline_touched → touched_amount for compat
  closed_amount: number
  total_cost: number
  avg_cost_per_provision: number
  first_provision: string | null
  last_provision: string | null
  retirement_score: number
  synced_at: string
  // ... rest unchanged ...
}
```

**Update catalog API functions to accept either `ciName` or `contentId`:**

For Phase 1, keep all existing function signatures that use `ciName`. The API now accepts both, so no URL changes are needed on the frontend. The key change is that responses may include `content_id` which the frontend should be prepared to handle.

**Update `Candidate` type in RecCard and advisor components:**

```typescript
interface Candidate {
  content_id?: string                    // NEW — optional for backward compat with SSE data
  ci_name: string
  display_name: string
  content_type?: string                  // NEW — 'lab', 'demo', 'sandbox'
  tier: string
  // ... all existing fields unchanged ...
  best_match_type?: string               // NEW
  best_match_detail?: string | null      // NEW
}
```

#### 11b. UPDATE: `BrowsePage.tsx` — use content_id as key where available

**Item list rendering:** The `items.map()` currently uses `item.ci_name` as the React key and for expand/detail lookups. For Phase 1, continue using `ci_name` as the key since every Babylon item has one. Add `content_id` to the `CatalogItem` interface for forward compatibility:

```typescript
interface CatalogItem {
  content_id?: string                    // NEW — may be present in responses
  ci_name: string
  display_name: string
  // ... rest unchanged ...
}
```

**Detail fetching:** `handleExpand` calls `api.getCatalogItem(ciName)`. The backend now accepts both `ci_name` and `content_id`. No change needed for Phase 1.

**Curator actions:** All curator actions (`handleAnalyze`, `handleAddTag`, `handleRemoveTag`, `handleSaveNote`, etc.) pass `ci_name` to the API. The API resolves to `content_id` internally (Task 10d). No frontend change needed.

**Similar items:** `api.getSimilarItems(ciName)` — API accepts both. No change needed.

**No UI changes:** The card layout, badges, filters, sidebar, and pagination all stay identical. The `content_type` field is available in the response but not rendered in Phase 1.

#### 11c. UPDATE: `RetirementPage.tsx` — backward-compatible field access

The retirement page reads `ReportingMetricsItem` data from `api.getRetirementDashboard()`. The API response (Task 10f) includes backward-compatible field names (`catalog_base_name`, `touched_amount`, `experiences`, etc.) so the frontend continues working without changes.

**Items that reference `catalog_base_name`:** The retirement page uses `item.catalog_base_name` extensively — for display, workflow lookups, ignore/unignore calls, and URL parameters. The API continues providing this field (derived from `content_id` in Task 10f). No frontend change needed for Phase 1.

**Workflow API calls:** `api.getRetirementWorkflow(baseName)`, `api.reviewRetirementItem(baseName)`, etc. all pass `baseName` (which is `catalog_base_name`). The API endpoints resolve to `content_id` internally (Task 10g). No frontend change needed.

**Ignore/unignore:** `api.ignoreRetirementItem(baseName)` and `api.unignoreRetirementItem(baseName)` — same pattern, API resolves.

**No UI changes:** Score colors, workflow badges, stat cards, filters, and the entire table layout stay identical.

#### 11d. UPDATE: `RecCard.tsx` — add content_id awareness

The `RecCard` component receives a `Candidate` from the advisor pipeline. For Phase 1, the candidate data flows through SSE progress events. The serialized candidate (Task 9e) now includes `content_id` and `content_type`.

**Add `content_id` to the `Candidate` interface:**

```typescript
interface Candidate {
  content_id?: string                    // NEW
  ci_name: string
  display_name: string
  content_type?: string                  // NEW
  tier: string
  // ... all existing fields unchanged ...
}
```

**Selection handler:** `handleSelect` calls `api.selectRecommendation(sessionId, turnIndex, candidate.ci_name)`. For Phase 1, keep sending `ci_name`. The API accepts both (Task 10i). No change needed.

**`chosenCiName` comparison:** `useState(chosenCiName === candidate.ci_name)` — continue using `ci_name` comparison. No change needed.

**Catalog URL:** `catalogUrl(candidate.ci_name, candidate.catalog_namespace)` — still correct, the RHDP catalog uses `ci_name` in its URL format.

**No UI changes:** The card layout, score display, tier colors, duration info, sales impact badges, and "Best fit" button all stay identical. `content_type` is available on the candidate but not rendered in Phase 1.

#### 11e. Summary of frontend non-changes (explicit)

The following are explicitly NOT changed in Phase 1:
- No content type badge in Browse or RecCard headers
- No content type filter in the Browse sidebar
- No grouped results headers in advisor results
- No sandbox-specific card sections
- No architecture-specific card layouts
- No changes to the filter sidebar
- No changes to the retirement table columns
- No changes to the advisor query input or flow

All of these are Phase 2 work when new content types are actually ingested and visible.

**Validation criteria:**
- BrowsePage loads and renders items correctly (same visual output)
- Expanding a card shows detail, analysis, infrastructure, similar content — same as before
- Curator actions (tag, note, flag, re-analyze, override URL, content path, duration) all work
- RetirementPage loads and renders the dashboard correctly — same stat cards, same table
- Retirement workflow actions (review, approve, notify, start, link Jira) all work
- Ignore/unignore works
- RecCard renders advisor recommendations correctly — same layout, score, badges
- "Best fit" selection works
- No visual regressions in any page
- `npm run build` succeeds without TypeScript errors
- No console errors in development mode

---

### Task 12: Migration Execution and Validation

**Files to reference:**
- `src/api/scripts/migrate_to_content_model.py` (Task 2)
- `ansible/deploy.yml` — deployment playbook
- `ansible/vars/dev.yml` — dev environment vars (gitignored)

**Dependencies:** ALL previous tasks (1-11) must be complete and committed

**What to do:**

This task is the operational execution of the migration on the dev environment. It is a sequence of manual steps, not code changes. The validation checklist ensures nothing was missed.

#### 12a. Pre-migration: Data preservation (dev environment)

1. **SSH to dev environment** or use the dev kubeconfig to connect.

2. **Run the export phase** (Task 2) against the dev database:
   ```bash
   # From the API pod or local with port-forward to dev PostgreSQL
   python scripts/migrate_to_content_model.py export --db-url "$DATABASE_URL"
   ```
   This writes `/tmp/rcars-migration-export.json` with advisor_sessions, active retirement workflows, and curator notes.

3. **Verify the export:**
   - `jq '.advisor_sessions | length' /tmp/rcars-migration-export.json` — should be > 0
   - `jq '.retirement_workflows | length' /tmp/rcars-migration-export.json` — active workflows
   - `jq '.curator_notes | length' /tmp/rcars-migration-export.json` — curator notes count

4. **Back up the export file** to a safe location (e.g., `/tmp/` on your local machine via `oc cp`).

#### 12b. Deploy new schema (dev environment)

1. **Commit all code changes (Tasks 1-11)** to the feature branch. Push to remote.

2. **Deploy to dev:**
   ```bash
   ansible-playbook ansible/deploy.yml -e env=dev --tags full
   ```
   This deploys the new schema (via `create_schema()` which drops old tables and creates new ones), builds the API and frontend, and runs database initialization.

3. **Verify schema creation:**
   ```bash
   # Port-forward to dev PostgreSQL and run:
   psql -c "\dt" | grep -E 'content_entities|babylon_items|performance_channels|performance_scores'
   ```
   All four new tables should exist. Old tables (`catalog_items`, `reporting_metrics`, `catalog_item_workloads`, `catalog_item_acl_groups`) should be gone.

#### 12c. Import preserved data

1. **Import advisor sessions:**
   ```bash
   python scripts/migrate_to_content_model.py import-sessions --db-url "$DATABASE_URL"
   ```
   This re-inserts advisor_sessions and maps `chosen_ci_name` to `chosen_content_id`.

2. **Wait for first catalog refresh** — either trigger manually:
   ```bash
   # Via the API
   curl -X POST https://rcars-dev.apps.../api/v1/catalog/refresh -H "Authorization: Bearer ..."
   ```
   Or wait for the nightly pipeline to run.

3. **Verify catalog refresh populated both tables:**
   ```sql
   SELECT COUNT(*) FROM content_entities WHERE source = 'babylon';
   SELECT COUNT(*) FROM babylon_items;
   SELECT content_type, COUNT(*) FROM content_entities WHERE source = 'babylon' GROUP BY content_type;
   ```
   Expected: ~440 content_entities, ~440 babylon_items, content_type distribution of ~200 labs, ~40 demos, ~200 sandboxes.

4. **Import retirement workflows** (after catalog refresh):
   ```bash
   python scripts/migrate_to_content_model.py import-workflows --db-url "$DATABASE_URL"
   ```

5. **Wait for first analysis pipeline** — this takes hours (LLM analysis of ~200 items). Either trigger manually or wait for nightly.

6. **Import curator notes** (after analysis):
   ```bash
   python scripts/migrate_to_content_model.py import-notes --db-url "$DATABASE_URL"
   ```

#### 12d. Trigger and validate pipeline steps

After the nightly pipeline completes (or after manual triggers of each step):

1. **Catalog refresh validation:**
   ```sql
   -- All babylon_items have a parent content_entity
   SELECT COUNT(*) FROM babylon_items bi
   WHERE NOT EXISTS (SELECT 1 FROM content_entities ce WHERE ce.content_id = bi.content_id);
   -- Expected: 0

   -- Content type distribution is reasonable
   SELECT content_type, COUNT(*) FROM content_entities WHERE source = 'babylon' AND retired_at IS NULL GROUP BY content_type;
   -- Expected: lab ~200, demo ~40, sandbox ~200

   -- Workloads have content_id FK
   SELECT COUNT(*) FROM babylon_item_workloads;
   -- Expected: > 0
   ```

2. **Analysis pipeline validation:**
   ```sql
   -- Showroom analysis rows use content_id
   SELECT COUNT(*) FROM showroom_analysis;
   -- Expected: > 0 (after analysis runs)

   -- Content entities card fields are populated
   SELECT COUNT(*) FROM content_entities WHERE summary IS NOT NULL AND source = 'babylon' AND content_type IN ('lab', 'demo');
   -- Expected: matches showroom_analysis count

   -- Embeddings have content_type and source columns
   SELECT content_type, source, COUNT(*) FROM embeddings GROUP BY content_type, source;
   -- Expected: babylon source, lab/demo/sandbox content types
   ```

3. **Sandbox summary validation:**
   ```sql
   -- Sandboxes with summaries
   SELECT COUNT(*) FROM content_entities WHERE content_type = 'sandbox' AND summary IS NOT NULL;
   -- Expected: > 0 (after sandbox summary step runs)

   -- Sandbox embeddings exist
   SELECT COUNT(*) FROM embeddings WHERE content_type = 'sandbox';
   -- Expected: matches sandbox-with-summary count
   ```

4. **Reporting sync validation:**
   ```sql
   -- Performance channels populated
   SELECT COUNT(*) FROM performance_channels WHERE channel = 'rhdp';
   -- Expected: > 0 (after reporting sync)

   -- Performance scores populated
   SELECT COUNT(*) FROM performance_scores;
   -- Expected: matches performance_channels count

   -- Score values are reasonable
   SELECT MIN(performance_score), MAX(performance_score), AVG(performance_score) FROM performance_scores;
   -- Expected: 0-80 range, average ~30-40
   ```

5. **Advisor query validation:**
   - Open the RCARS dev UI
   - Submit an advisor query (e.g., "I need a workshop about OpenShift networking")
   - Verify: vector search returns results, triage scores them, rationale is generated
   - Verify: RecCards display correctly with scores, duration, "Best fit" button

6. **Browse page validation:**
   - Navigate to Browse
   - Verify: items load, search works, stage toggles work
   - Expand a card: verify analysis, infrastructure, similar content sections render
   - Curator actions: tag, note, flag, re-analyze — all should work

7. **Retirement page validation:**
   - Navigate to Content Analysis > Retirement
   - Verify: dashboard loads, score colors correct, stat cards populated
   - Verify: workflow actions work (review, approve)
   - Verify: ignore/unignore works
   - Verify: time window filter works (1q, 2q, 3q, 1y)

8. **Preserved data validation:**
   ```sql
   -- Advisor sessions preserved
   SELECT COUNT(*) FROM advisor_sessions;
   -- Expected: matches pre-migration count

   -- chosen_content_id populated for historical sessions
   SELECT COUNT(*) FROM advisor_sessions WHERE chosen_ci_name IS NOT NULL AND chosen_content_id IS NOT NULL;

   -- Retirement workflows preserved
   SELECT COUNT(*) FROM retirement_workflow;
   -- Expected: matches exported active workflows

   -- Curator notes preserved
   SELECT COUNT(*) FROM showroom_analysis WHERE notes IS NOT NULL AND notes != '';
   -- Expected: matches exported curator notes count
   ```

#### 12e. Validation checklist

| Category | Check | Expected |
|----------|-------|----------|
| Schema | `content_entities` table exists | Yes |
| Schema | `babylon_items` table exists with FK to content_entities | Yes |
| Schema | `performance_channels` replaces `reporting_metrics` | Yes |
| Schema | `performance_scores` table exists | Yes |
| Schema | Old tables (`catalog_items`, `reporting_metrics`) dropped | Yes |
| Catalog | content_entities populated after refresh | ~440 rows |
| Catalog | Content type distribution | lab ~200, demo ~40, sandbox ~200 |
| Catalog | Retired items have `retired_at` set on content_entities | Yes |
| Analysis | showroom_analysis keyed by content_id | Yes |
| Analysis | content_entities card fields populated (summary, products, topics) | Yes |
| Analysis | Embeddings have content_type and source | Yes |
| Sandbox | Sandbox summaries generated from workload metadata | Yes |
| Sandbox | Sandbox embeddings exist with content_type='sandbox' | Yes |
| Reporting | performance_channels has 'rhdp' channel data | Yes |
| Reporting | performance_scores has scores with breakdowns | Yes |
| Advisor | Query returns results | Yes |
| Advisor | RecCards display correctly | Yes |
| Advisor | "Best fit" selection stores chosen_content_id | Yes |
| Browse | Page loads with items | Yes |
| Browse | Search, filters, pagination work | Yes |
| Browse | Card expand shows analysis + infrastructure | Yes |
| Browse | Curator actions work | Yes |
| Retirement | Dashboard loads with scores | Yes |
| Retirement | Workflow actions work | Yes |
| Retirement | Time window filter works | Yes |
| Migration | advisor_sessions preserved | Row count matches |
| Migration | retirement_workflows preserved | Active workflows preserved |
| Migration | curator_notes preserved | Notes restored |

---

## Task Dependency Graph

```
Task 1: Schema DDL
  ├── Task 2: Migration Script (needs schema to exist)
  ├── Task 3: Content Entity CRUD (needs schema)
  │     └── Task 5: Catalog Refresh Pipeline (needs CRUD methods)
  │     └── Task 7: Sandbox Summary (needs CRUD methods)
  └── Task 4: Analysis & Embeddings Methods (needs schema + Task 3)
        ├── Task 6: Scan Pipeline (needs analysis methods + Task 5 for data)
        ├── Task 7: Sandbox Summary (needs embeddings methods + Task 5 for data)
        ├── Task 8: Reporting Sync (needs performance methods + Task 5 for data)
        └── Task 9: Advisor Pipeline (needs search_embeddings + Task 5 for data)

Tasks 5-8 (Pipeline Adaptation) can proceed in parallel after Tasks 3-4 complete:
  Task 5: Catalog Refresh  ─┐
  Task 6: Scan Pipeline     ├── Independent pipeline modules
  Task 7: Sandbox Summary   │   (but execution order matters at runtime:
  Task 8: Reporting Sync    ─┘    5 → 6 → 7 → 8 in the nightly pipeline)

Task 9: Advisor Pipeline (depends on Tasks 3, 4; data from Tasks 5-8)
Task 10: API Routes (depends on Tasks 3, 4, 9)
Task 11: Frontend (depends on Task 10)
Task 12: Migration Execution (depends on ALL Tasks 1-11)
```

**Parallel work streams:**

- **Stream A (Database):** Task 1 → Task 3 → Task 4
- **Stream B (Pipelines):** Task 5, Task 6, Task 7, Task 8 (after Stream A completes)
- **Stream C (Advisor):** Task 9 (after Stream A completes, validates with Stream B data)
- **Stream D (API + UI):** Task 10 → Task 11 (after Stream C)
- **Stream E (Migration):** Task 2 (after Task 1), Task 12 (after ALL)

**Critical path:** Task 1 → Task 3 → Task 4 → Task 9 → Task 10 → Task 11 → Task 12

---

## Implementation Notes

- **Jira:** [RHDPCD-359](https://redhat.atlassian.net/browse/RHDPCD-359)
- **Spec:** `docs/superpowers/specs/2026-07-20-generalized-content-model-design.md`
- **All work on a feature branch** with PR to main. Branch name: `feature/generalized-content-model`.
- **Deploy to dev environment first.** Validate thoroughly before any other environment. The dev environment is expendable — the prod data is not.
- **Git workflow:** Batch commits at task boundaries. Push at milestones (e.g., after Tasks 1-4, after Tasks 5-8, after Tasks 9-11). NEVER push without explicit user approval.
- **Test continuously:** Run `python -m pytest tests/ -v` after each task. Update test fixtures as needed — many tests reference `catalog_items` table and `ci_name` fields.
- **Database method naming:** New methods use `content_id` parameter names. Backward-compat methods (e.g., `get_babylon_item_by_ci_name()`) are provided for code paths that still use `ci_name`.
- **No Alembic migrations:** This is a full schema swap via `create_schema()`. Alembic version table is dropped and recreated. Future incremental changes (e.g., adding Portfolio Architecture tables) will use Alembic.
- **Frontend TypeScript:** All new fields added as optional (`?`) to interfaces. No breaking type changes. `npm run build` must pass without errors.
