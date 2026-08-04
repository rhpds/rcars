# Data Design

How RCARS stores, relates, and scores content. Read this to understand the data model conceptually, then point an AI agent at the [full schema reference](#full-schema-reference) at the bottom for implementation details.

## Content Model

Everything in RCARS is a **content entity** -- a source-agnostic record representing a piece of RHDP content. The system stores labs, demos, sandboxes, and (in the future) architectures, interactive experiences, or content from non-Babylon sources.

```
content_entities          babylon_items (1:1 extension)
┌──────────────────┐      ┌──────────────────────┐
│ content_id (PK)  │◄─────│ content_id (PK, FK)  │
│ source           │      │ ci_name (UNIQUE)      │
│ content_type     │      │ stage, category       │
│ display_name     │      │ showroom_url/ref      │
│ summary          │      │ cloud_provider        │
│ products_json    │      │ scan_status           │
│ retired_at       │      │ ...30 more fields     │
│ ...              │      └──────────────────────┘
└──────────────────┘
```

### Two-table design

- **`content_entities`** holds fields that apply to *any* content source: identity (`content_id`, `source`, `content_type`), card-level metadata (display name, summary, products, topics, audience, difficulty), and lifecycle state (`retired_at`).
- **`babylon_items`** extends `content_entities` 1:1 for Babylon-sourced content. It holds everything CRD-specific: `ci_name`, stage, category, Showroom URL/ref, cloud provider, OCP version, AgnosticD config, scan status, and infrastructure metadata.

### Why this split

The old `catalog_items` table baked Babylon assumptions into the primary key (`ci_name`) and mixed source-specific fields with universal ones. The normalized model lets RCARS ingest content from other sources (Confluence, external labs, architecture docs) without schema changes to the core entity table -- just add a new extension table alongside `babylon_items`.

### content_id

Every entity has a stable `content_id` as its primary key -- a text identifier with a source prefix:

- Babylon items: `babylon:<ci_name>` (e.g., `babylon:ocp4-getting-started.prod`)

All foreign keys throughout the schema reference `content_entities.content_id`. The old `ci_name` is preserved on `babylon_items` as a UNIQUE column for backward compatibility and CRD correlation, but it is never used as a foreign key.

### Content types and sources

- `source`: Where the content came from (`babylon`, and future values like `confluence`, `external`)
- `content_type`: What kind of content it is (`lab`, `demo`, `sandbox`, and future values like `architecture`, `interactive_experience`)

### Soft-delete and retirement

Items that disappear from Babylon CRDs get `content_entities.retired_at = NOW()` instead of being deleted. All active-item queries filter on `retired_at IS NULL`. Items that reappear in a future scan are automatically un-retired (set `retired_at = NULL`).

## Analysis and Embeddings

### Content analysis

When a content entity has Showroom content (labs and demos), the scan pipeline clones the repo, reads the AsciiDoc, and sends it to an LLM for structured analysis. Results are stored in **`showroom_analysis`** (1:1 with `content_entities`):

- Structured fields: summary, products, topics, audience, difficulty, modules, learning objectives, duration estimate, format suitability, use cases
- Change detection: `content_hash` tracks the SHA of the analyzed content; `is_stale` flags when the repo has new commits
- Curator enrichment: `notes` (free text), `curated_duration_min` (manual override), `review_reasons` (vocabulary flagging)

### Embeddings

After analysis, RCARS generates **768-dimensional vector embeddings** using the `nomic-embed-text-v1.5` model, served by a dedicated **vLLM HTTP server** (OpenAI-compatible `/v1/embeddings` API).

Each content entity can have multiple embeddings in the **`embeddings`** table:

| `embed_type` | What it embeds | Used for |
|---|---|---|
| `summary` | The full analysis summary | Advisor vector search, content overlap |
| `module` | Individual module titles + descriptions | Fine-grained matching |

Key columns:

- `content_type` and `source`: Enable filtered searches (e.g., only search labs, or only Babylon content)
- `content_text`: The original text that was embedded (for debugging and re-embedding)

Nomic requires task prefixes: `search_document:` when indexing content, `search_query:` when embedding a user query. RCARS applies these automatically.

## Performance and Retirement

### Performance data

Performance metrics flow from the **RHDP Reporting MCP Server** into two tables:

- **`performance_channels`**: Raw metrics per (content_id, channel). One row per content entity per data channel (e.g., `rhdp` for provisioning data). Stores provisions, unique users, cost, pipeline touched/closed amounts, success ratios, and `windowed_metrics` (JSONB with time-bucketed snapshots for 3m/6m/9m/12m views).
- **`performance_scores`**: Computed performance score per content entity. Stores the overall `performance_score` (0-100 percentile, higher = better), `score_breakdown` (JSONB with component scores), and `ignored_until` (curator mute).

This replaces the old monolithic `reporting_metrics` table, separating raw channel data from computed scores.

### Retirement workflow

The **`retirement_workflow`** table tracks the lifecycle of content being retired, keyed by `content_id`:

```
reviewed → approved → notified → started → retired
```

Each step has `step_<name>_at` / `step_<name>_by` timestamps and actor fields. Additional fields track the approval reason, a snapshot of the item's state at approval time, Jira ticket linkage, and curator notes.

## Supporting Tables

### Workloads and ACL

- **`babylon_item_workloads`**: Maps content entities to infrastructure workload roles (Ansible roles deployed by the content). Joined with `workload_mapping` to resolve human-readable product names.
- **`babylon_item_acl_groups`**: Tracks which ACL groups have access to each content entity.
- **`workload_mapping`**: Reference table mapping `workload_role` → `product_name` with verification status.
- **`workload_aliases`**: Alternative names for workload products (for search flexibility).
- **`workload_scan_state`**: Tracks the last scanned commit SHA per Ansible collection (for incremental scanning).

### Enrichment and curation

- **`enrichment_tags`**: Curator-applied tags (tag_type + tag_value) on content entities -- audience, use-case, and custom classifications.
- **`content_similarity`**: Pairwise cosine similarity scores between content entities, computed from summary embeddings. Used by the content overlap analysis.

### Sessions and jobs

- **`advisor_sessions`**: Query history -- each row is one turn in an advisor conversation. Tracks the query, results, and which recommendation the user chose (`chosen_content_id`).
- **`jobs`**: Async job tracking for long-running operations (scans, refreshes, queries). Stores status, progress, and results.

### Auth and operational

- **`api_keys`**: External API authentication -- hashed keys with prefixes, roles, scopes, and expiry.
- **`analysis_log`**: Audit trail of curator actions and system events.
- **`token_usage`**: LLM token consumption tracking per operation, model, and provider. The `provider` column distinguishes between backends (e.g., `anthropic`, `litemaas`).

## Schema Management

The schema is defined as `SCHEMA_SQL` in `src/api/rcars/db/database.py` -- this is the single source of truth. There is no Alembic or external migration tool.

- **Fresh installs**: All tables use `CREATE TABLE IF NOT EXISTS`
- **Adding columns**: Append `ALTER TABLE <table> ADD COLUMN IF NOT EXISTS <col> <type>` at the bottom of `SCHEMA_SQL`
- **Structural changes**: Run `rcars init-db --drop` to drop and recreate all tables (destructive -- requires data re-population via pipelines)

`rcars init-db` runs `create_schema()` on every deploy. The entire block is idempotent.

## Full Schema Reference

The complete `CREATE TABLE` statements from `SCHEMA_SQL`. This is what an AI agent should parse for column-level details.

```sql
-- ═══════════════════════════════════════════════════════════════════
-- content_entities — universal entity registry
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS content_entities (
    content_id      TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    is_hands_on     BOOLEAN NOT NULL DEFAULT FALSE,

    display_name    TEXT NOT NULL,
    summary         TEXT,
    products_json   JSONB,
    topics_json     JSONB,
    audience_json   JSONB,
    difficulty      TEXT,

    retired_at      TIMESTAMPTZ,
    retirement_reason TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════
-- babylon_items — Babylon-specific extension (1:1 with content_entities)
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS babylon_items (
    content_id      TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    ci_name         TEXT NOT NULL UNIQUE,

    category        TEXT,
    stage           TEXT,
    catalog_namespace TEXT,
    is_prod         BOOLEAN DEFAULT FALSE,
    is_published    BOOLEAN DEFAULT FALSE,
    published_ci_name TEXT,
    base_ci_name    TEXT,

    showroom_url    TEXT,
    showroom_ref    TEXT,
    content_path    TEXT,
    showroom_url_override TEXT,

    is_agd_v2       BOOLEAN DEFAULT FALSE,
    agd_config      TEXT,
    cloud_provider  TEXT,
    ocp_version     TEXT,
    os_image        TEXT,
    worker_instance_count TEXT,
    control_plane_instance_count TEXT,
    instances_json  JSONB,

    keywords        TEXT[],
    description     TEXT,
    owners_json     JSONB,
    icon_url        TEXT,
    last_crd_update TIMESTAMPTZ,
    last_refreshed  TIMESTAMPTZ DEFAULT NOW(),

    scan_status     TEXT NOT NULL DEFAULT 'not_scanned',
    scan_error_class TEXT,
    scan_error      TEXT,
    scan_failed_at  TIMESTAMPTZ
);

-- ═══════════════════════════════════════════════════════════════════
-- showroom_analysis — LLM-generated content analysis
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS showroom_analysis (
    content_id              TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,

    summary                 TEXT,
    products_json           JSONB,
    topics_json             JSONB,
    audience_json           JSONB,
    difficulty              TEXT,
    content_hash            TEXT,
    last_analyzed           TIMESTAMPTZ,
    is_stale                BOOLEAN DEFAULT FALSE,
    stale_commit            TEXT,

    content_type            TEXT,
    modules_json            JSONB,
    learning_objectives_json JSONB,
    estimated_duration_min  INTEGER,
    curated_duration_min    INTEGER CHECK (curated_duration_min >= 0),
    format_suitability_json JSONB,
    use_cases_json          JSONB,

    last_repo_commit        TEXT,
    last_repo_updated       TIMESTAMPTZ,

    enrichment_review_needed BOOLEAN DEFAULT FALSE,
    review_reasons           JSONB,
    notes                   TEXT
);

-- ═══════════════════════════════════════════════════════════════════
-- embeddings — 768-dim vectors from nomic-embed-text-v1.5 via vLLM
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS embeddings (
    id              SERIAL PRIMARY KEY,
    content_id      TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_type    TEXT NOT NULL,
    source          TEXT NOT NULL,
    embed_type      TEXT NOT NULL,
    module_title    TEXT,
    content_text    TEXT,
    embedding       vector(768)
);

-- ═══════════════════════════════════════════════════════════════════
-- performance_channels — per-channel performance metrics
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS performance_channels (
    id                      SERIAL PRIMARY KEY,
    content_id              TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    channel                 TEXT NOT NULL,

    provisions              INTEGER DEFAULT 0,
    unique_users            INTEGER DEFAULT 0,
    requests                INTEGER DEFAULT 0,
    page_views              INTEGER DEFAULT 0,
    downloads               INTEGER DEFAULT 0,
    completions             INTEGER DEFAULT 0,

    pipeline_touched        NUMERIC,
    closed_amount           NUMERIC,
    marketing_spend         NUMERIC,
    total_cost              NUMERIC,
    avg_cost_per_provision  NUMERIC,
    success_ratio           NUMERIC,

    first_activity          DATE,
    last_activity           DATE,

    windowed_metrics        JSONB DEFAULT '{}'::jsonb,

    synced_at               TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id, channel)
);

-- ═══════════════════════════════════════════════════════════════════
-- performance_scores — computed retirement scores
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS performance_scores (
    content_id      TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    performance_score INTEGER NOT NULL DEFAULT 0,
    score_breakdown JSONB,
    channel_scores  JSONB,
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    ignored_until   DATE
);

-- ═══════════════════════════════════════════════════════════════════
-- retirement_workflow — retirement lifecycle tracking
-- ═══════════════════════════════════════════════════════════════════
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

-- ═══════════════════════════════════════════════════════════════════
-- content_similarity — pairwise embedding similarity
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS content_similarity (
    id SERIAL PRIMARY KEY,
    content_id_a TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_id_b TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    similarity_score REAL NOT NULL,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id_a, content_id_b)
);

-- ═══════════════════════════════════════════════════════════════════
-- babylon_item_workloads — workload role associations
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS babylon_item_workloads (
    id SERIAL PRIMARY KEY,
    content_id TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    workload_fqcn TEXT NOT NULL,
    workload_role TEXT NOT NULL,
    workload_collection TEXT,
    UNIQUE(content_id, workload_fqcn)
);

-- ═══════════════════════════════════════════════════════════════════
-- babylon_item_acl_groups — ACL group membership
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS babylon_item_acl_groups (
    id SERIAL PRIMARY KEY,
    content_id TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    group_name TEXT NOT NULL,
    UNIQUE(content_id, group_name)
);

-- ═══════════════════════════════════════════════════════════════════
-- Reference tables
-- ═══════════════════════════════════════════════════════════════════
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

CREATE TABLE IF NOT EXISTS workload_scan_state (
    collection TEXT PRIMARY KEY,
    last_sha TEXT,
    last_scanned TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════
-- Enrichment and curation
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS enrichment_tags (
    id SERIAL PRIMARY KEY,
    content_id TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    added_by TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id, tag_type, tag_value)
);

-- ═══════════════════════════════════════════════════════════════════
-- Operational tables
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS analysis_log (
    id SERIAL PRIMARY KEY,
    ci_name TEXT,
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
    chosen_content_id TEXT,
    chosen_at TIMESTAMPTZ,
    opted_out BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
