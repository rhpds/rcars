# RCARS Generalized Content Model

**Jira:** [RHDPCD-359](https://redhat.atlassian.net/browse/RHDPCD-359) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Date:** 2026-07-20
**Status:** Design

## Problem

RCARS was built for RHDP Babylon catalog items with Showroom content. Every table, query, and pipeline assumes "catalog item = Babylon CI with a Showroom." That assumption is no longer true.

The system needs to accommodate:

- **Babylon CIs without content** — hands-on environments (OpenShift clusters, AWS accounts) with no lab guide or demo script. They have infrastructure capabilities (workloads, cloud provider) but no guided content to analyze.
- **Portfolio Architectures** — reference architecture documents (AsciiDoc + diagrams) from the [OSSPA portfolio-architecture-examples](https://gitlab.com/osspa/portfolio-architecture-examples) repository. Not hands-on, but they describe solutions using the same products that labs cover.
- **Interactive Experiences** — click-through arcade/video content (e.g., [interact.redhat.com](https://interact.redhat.com)). Not hands-on, future ingestion.
- **Multiple performance channels** — the same Babylon CI can be provisioned through RHDP (sales-touch) or Interactive Labs (marketing-touch), with fundamentally different usage attribution.

The current schema forces all of these into Babylon-shaped tables. An early spec for Portfolio Architecture ingest proved the problem — it proposed jamming architecture docs into `showroom_analysis` and filling Babylon-specific columns with placeholder values, because the schema offered no clean alternative.

This design establishes the foundational data architecture for handling multiple content types and sources.

## Approach

Full normalization (Approach A). The system is young enough for a major structural change. A new `content_entities` table becomes the universal entity registry. Source-specific metadata moves to extension tables. The existing `catalog_items` table is decomposed — universal fields move up, Babylon-specific fields stay in a renamed extension table.

The migration is a fresh schema build with selective data preservation, not an incremental table-by-table migration. The nightly pipelines (CRD scan, Showroom analysis, reporting sync, workload scan) already know how to populate everything from source — we let them repopulate into the new schema.

## Design

### 1. Content Taxonomy

RCARS manages **content entities** — anything the platform knows about and can surface to users. Every content entity has a source, a content type, and an orderability flag.

#### Sources

| Source | Ingest Mechanism | Lifecycle Signal |
|--------|-----------------|------------------|
| **Babylon** | K8s CRD scan (CatalogItem + AgnosticVComponent) | CRD disappears → soft-delete |
| **Portfolio Architectures** | GitLab CSV manifest + AsciiDoc repo scan | Row removed from CSV or `islive` flipped |
| **Interactive Experiences** | TBD (markdown per experience) | TBD |

Each source has its own ingest pipeline, metadata shape, and lifecycle signals. Adding a new source means: write an ingest pipeline, create an extension table, define the lifecycle signal. The core entity model doesn't change.

#### Content Types

| Content Type | Source | Hands-On | Has Guided Content |
|-------------|--------|-----------|-------------------|
| `lab` | Babylon | Yes | Yes (Showroom) |
| `demo` | Babylon | Yes | Yes (Showroom) |
| `sandbox` | Babylon | Yes | No |
| `architecture` | Portfolio Arch | No | Yes (AsciiDoc) |
| `interactive_experience` | Portfolio Arch | No | Yes (arcade/video) |

Key distinctions:

- **Hands-on** means a user logs into a live environment and interacts with it. All Babylon items are hands-on (labs, demos, and sandboxes all provision a real environment). Architectures and interactive experiences are not — you read or click through them, but there's no live environment.
- **Hands-on vs. not** is tracked per-entity so future sources can be either.
- **Guided content vs. not** determines whether the entity has an analysis record. Sandboxes have no content to analyze but are searchable through infrastructure metadata.
- **Content type drives the analysis shape** — labs have modules/learning objectives, architectures have patterns/solution areas.
- BabyDev is not a content type — it's a stage/environment of Babylon items.
- Interactive Labs is not a content type — it's a channel through which Babylon items are consumed.
- Events are not entities — they're a consumption context.

### 2. Entity Model — content_entities

The universal registry. Every entity RCARS knows about gets one row. This table is what Browse queries, what triage reads, what embeddings FK to.

```sql
CREATE TABLE content_entities (
    content_id      TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    is_hands_on    BOOLEAN NOT NULL DEFAULT FALSE,

    -- The "card" — Browse listing + triage contract
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

CREATE INDEX idx_ce_source ON content_entities(source);
CREATE INDEX idx_ce_content_type ON content_entities(content_type);
CREATE INDEX idx_ce_retired ON content_entities(retired_at);
CREATE INDEX idx_ce_products ON content_entities USING gin(products_json);
```

#### Identity Scheme

`content_id` is a namespaced string, globally unique and deterministic from source data:

- Babylon items: `babylon:openshift-cnv.ocp4-getting-started.prod`
- Portfolio Architectures: `pa:275`
- Interactive Experiences: `ie:270`

The namespace prefix prevents collisions between sources and makes the source identifiable from the ID.

#### What Lives Here vs. Extension Tables

**On content_entities (the card):** Everything needed to render a Browse listing item. Everything triage needs to score relevance. Universal lifecycle (retired_at). Content type for UI grouping and pipeline routing.

**NOT on content_entities:** Source-specific metadata (stage, namespace, CRD fields, verticals, solutions). Full analysis detail (modules, learning objectives, architectural patterns). Performance metrics. Embeddings.

#### Denormalization

Summary, products, topics, audience, and difficulty are populated during content analysis and denormalized here from the source-specific analysis tables. They're updated whenever analysis runs. For sandboxes (no guided content), products_json is populated from infrastructure metadata (workload scanning).

This means triage and Browse listing queries hit ONE table with no JOINs. The analysis tables remain the source of truth for the full analysis; content_entities holds the triage-contract subset.

### 3. Source Extension Tables

Each source gets its own extension table with a 1:1 relationship to content_entities via `content_id`.

#### babylon_items

Everything currently on `catalog_items` that's Babylon-specific:

```sql
CREATE TABLE babylon_items (
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

CREATE INDEX idx_bi_ci_name ON babylon_items(ci_name);
CREATE INDEX idx_bi_stage ON babylon_items(stage);
CREATE INDEX idx_bi_is_prod ON babylon_items(is_prod);
CREATE INDEX idx_bi_showroom_url ON babylon_items(showroom_url);
CREATE INDEX idx_bi_cloud_provider ON babylon_items(cloud_provider);
```

`display_name`, `products_json`, `retired_at`, and `retirement_reason` move UP to content_entities. `ci_name` stays here for external system references (reporting MCP, Jira links, CLI commands).

#### Future Extension Tables (Illustrative — Not Created by This Migration)

The following tables are shown to illustrate the extension pattern. They are NOT created as part of this migration. Each is defined by its own ingest spec when that source is ready.

**portfolio_architectures** — created by the Portfolio Architecture ingest spec. Must FK to `content_entities.content_id`. Illustrative columns based on the [PAList.csv](https://gitlab.com/osspa/osspa-site/-/blob/main/src/app/ArchitectureList/PAList.csv) manifest:

```sql
-- ILLUSTRATIVE — final schema defined by PA ingest spec
CREATE TABLE portfolio_architectures (
    content_id      TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    ppid            INTEGER NOT NULL UNIQUE,
    pa_name         TEXT,
    verticals       TEXT[],
    solutions       TEXT[],
    detail_page     TEXT,
    image_url       TEXT,
    is_live         BOOLEAN DEFAULT TRUE,
    last_manifest_sync TIMESTAMPTZ DEFAULT NOW()
);
```

**interactive_experiences** — created by the IE ingest spec when ready:

```sql
-- ILLUSTRATIVE — final schema defined by IE ingest spec
CREATE TABLE interactive_experiences (
    content_id      TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    interact_id     TEXT NOT NULL UNIQUE,
    experience_url  TEXT,
    format          TEXT,
    last_source_sync TIMESTAMPTZ DEFAULT NOW()
);
```

#### Babylon-Specific Supporting Tables

These tables remain Babylon-specific (FK'd to content_entities via content_id of Babylon items):

- **babylon_item_workloads** — junction table for Ansible workload roles installed on Babylon environments. Workloads are about hands-on infrastructure, not reference content.
- **babylon_item_acl_groups** — access control groups for hands-on Babylon environments.
- **workload_mapping** and **workload_aliases** — reference tables mapping Ansible roles to products. Independent of any content entity.

### 4. Content Analysis Architecture

Each content type with guided content gets its own analysis table. Sandboxes (no guided content) skip analysis; their content_entities fields are populated from infrastructure metadata.

#### Shared Analysis Contract

Every analysis table MUST include these columns. They feed triage, embeddings, and the content_entities denormalization:

| Column | Type | Purpose |
|--------|------|---------|
| `content_id` | TEXT PK, FK → content_entities | Identity |
| `summary` | TEXT | One-paragraph description |
| `products_json` | JSONB | Products covered (controlled vocabulary) |
| `topics_json` | JSONB | Topic areas (controlled vocabulary) |
| `audience_json` | JSONB | Target audience (controlled vocabulary) |
| `difficulty` | TEXT | beginner / intermediate / advanced |
| `content_hash` | TEXT | Hash of source content for staleness detection |
| `last_analyzed` | TIMESTAMPTZ | When analysis last ran |
| `is_stale` | BOOLEAN | Content changed since last analysis |
| `stale_commit` | TEXT | The commit that made it stale |

These fields are copied to content_entities after every analysis run. The analysis table is the source of truth; content_entities is the denormalized read cache.

#### showroom_analysis (labs and demos)

```sql
CREATE TABLE showroom_analysis (
    content_id              TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,

    -- Shared contract
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
    notes                   TEXT
);
```

#### Future Analysis Tables (Illustrative — Not Created by This Migration)

**architecture_analysis** — created by the Portfolio Architecture ingest spec. Must include the shared contract columns. Architecture-specific columns are defined by that spec:

```sql
-- ILLUSTRATIVE — final schema defined by PA ingest spec
-- Shared contract columns (REQUIRED) shown; type-specific columns are TBD
CREATE TABLE architecture_analysis (
    content_id              TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,

    -- Shared contract (REQUIRED — feeds triage, embeddings, content_entities denormalization)
    summary                 TEXT,
    products_json           JSONB,
    topics_json             JSONB,
    audience_json           JSONB,
    difficulty              TEXT,
    content_hash            TEXT,
    last_analyzed           TIMESTAMPTZ,
    is_stale                BOOLEAN DEFAULT FALSE,
    stale_commit            TEXT,

    -- Architecture-specific (illustrative — PA ingest spec decides these)
    solution_areas_json     JSONB,
    architectural_patterns_json JSONB,
    components_json         JSONB,

    -- Curator
    enrichment_review_needed BOOLEAN DEFAULT FALSE,
    notes                   TEXT
);
```

#### Analysis Routing

The analyzer service routes by content type:

```python
ANALYSIS_CONFIG = {
    'lab':          {'table': 'showroom_analysis',     'prompt_builder': build_showroom_prompt,     'content_reader': read_showroom_content},
    'demo':         {'table': 'showroom_analysis',     'prompt_builder': build_showroom_prompt,     'content_reader': read_showroom_content},
    'architecture': {'table': 'architecture_analysis', 'prompt_builder': build_architecture_prompt, 'content_reader': read_architecture_content},
    'sandbox':      {'table': None,                    'summary_builder': build_sandbox_summary,    'content_reader': None},
}
```

Each source's prompt builder and content reader are separate functions. The output always includes the shared contract fields. The analyzer writes to the type-specific table and updates the denormalized fields on content_entities.

#### Sandbox Searchability

Sandboxes have no guided content but must be searchable. Their content_entities fields are populated from infrastructure metadata and the existing workload classification pipeline:

- `products_json` — from `babylon_item_workloads` → `workload_mapping` (Ansible roles already LLM-classified into product names, descriptions, and categories by the nightly workload scanner)
- `summary` — assembled from `workload_mapping` descriptions + CRD description + cloud provider + AgD config. The workload classifications are already done and stored — no additional LLM call needed per sandbox.
- `topics_json` — derived from `workload_mapping` categories and cloud provider

An embedding is generated from this metadata-derived summary, placing sandboxes in the same search space as analyzed content. A query like "I need an AWS environment with full credentials" matches against the sandbox's summary embedding alongside lab and architecture results.

#### Embedding Source by Content Type

Every content type produces embeddings through a different path, but all embeddings land in the same `embeddings` table and are searched the same way:

| Content Type | Embedding Source | Summary Text Comes From | Detail Embeddings From |
|-------------|-----------------|------------------------|----------------------|
| Lab | LLM analysis of Showroom AsciiDoc | `showroom_analysis.summary` | Module descriptions in `modules_json` |
| Demo | LLM analysis of Showroom AsciiDoc | `showroom_analysis.summary` | Module descriptions in `modules_json` |
| Sandbox | Workload classifications + CRD metadata | `content_entities.summary` (no analysis table) | None |
| Architecture | LLM analysis of architecture AsciiDoc | `architecture_analysis.summary` | Major section descriptions |
| Interactive Experience | LLM analysis of markdown/content | `ie_analysis.summary` | Step/screen descriptions |

The search flow for both Browse and Advisor:

1. **Vector search** — embed the query → search `embeddings` table → MAX(similarity) per content_id → return candidate content_ids with best-match metadata
2. **Triage** — read triage-contract fields from `content_entities` for those candidates (summary, products, topics, audience, difficulty — one table, no JOINs)
3. **Rationale** — read full detail from the type-specific analysis table based on `content_type` (or `babylon_items` infrastructure metadata for sandboxes)

#### Controlled Vocabulary

A `vocabularies.yaml` file (in `src/api/rcars/data/`) defines canonical values for products, topics, and audiences:

```yaml
products:
  - "Red Hat OpenShift Container Platform"
  - "Red Hat Ansible Automation Platform"
  - "Red Hat Advanced Cluster Security"
  # ...

topics:
  - "networking"
  - "security"
  - "storage"
  - "AI/ML"
  # ...

audiences:
  - "platform engineer"
  - "developer"
  - "architect"
  # ...
```

This is separate from the existing `product-terms.yaml` (query-time acronym/synonym expansion). The vocabulary file constrains analysis-time output — the LLM analysis prompts for ALL content types include the vocabulary, and the LLM must select from it. Values outside the vocabulary are accepted but the entity is flagged with `enrichment_review_needed = TRUE` for curator review. Nothing is silently dropped.

The two files are related and should share canonical product names. `product-terms.yaml` maps query-time shorthand to canonical names; `vocabularies.yaml` defines what those canonical names are.

#### Review Flagging Granularity

`enrichment_review_needed` on analysis tables must not become a catch-all bucket. When an analysis succeeds but produces results that need human review, the flag should be accompanied by a structured reason so curators can triage efficiently. The analysis tables include a `review_reasons` column:

```sql
enrichment_review_needed BOOLEAN DEFAULT FALSE,
review_reasons           JSONB,   -- e.g. [{"reason": "unknown_product", "detail": "OpenShift Pipelines not in vocabulary"}]
```

Known review reason types:

| Reason | Meaning |
|--------|---------|
| `unknown_product` | LLM produced a product name not in the controlled vocabulary |
| `unknown_topic` | Topic not in vocabulary |
| `unknown_audience` | Audience not in vocabulary |
| `low_confidence_classification` | LLM expressed uncertainty in its analysis |
| `missing_modules` | Showroom content parsed but no modules detected (unexpected structure) |
| `unexpected_content_structure` | Content didn't match expected format (e.g., non-standard nav.adoc, unfamiliar directory layout) |

This is distinct from scan failures (`scan_status` / `scan_error_class` on `babylon_items`), which mean the content couldn't be retrieved or analyzed at all (repo not found, clone timeout, LLM error). Review flags mean the analysis ran successfully but the output needs human validation.

The Browse UI should surface these differently: scan failures appear as error states, review flags appear as actionable items in the curator workflow.

### 5. Embeddings Design

One table for all content types. Entity retrieval uses MAX(similarity) per content_id to prevent count bias.

```sql
CREATE TABLE embeddings (
    id              SERIAL PRIMARY KEY,
    content_id      TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_type    TEXT NOT NULL,
    source          TEXT NOT NULL,
    embed_type      TEXT NOT NULL,   -- 'summary', 'module', 'section'
    module_title    TEXT,
    content_text    TEXT,
    embedding       vector(384)      -- dimension changes with model upgrade
);

CREATE INDEX idx_emb_content_id ON embeddings(content_id);
CREATE INDEX idx_emb_content_type ON embeddings(content_type);
CREATE INDEX idx_emb_embed_type ON embeddings(embed_type);
```

#### Embedding Volume Per Content Type

| Content Type | Summary Embedding | Detail Embeddings |
|-------------|-------------------|-------------------|
| Lab | 1 (analysis summary) | 1 per module |
| Demo | 1 (analysis summary) | 1 per module |
| Sandbox | 1 (metadata-derived summary) | None |
| Architecture | 1 (analysis summary) | 1 per major section |
| Interactive Experience | 1 (analysis summary) | 1 per step/screen |

#### MAX(similarity) Scoring

A 20-module lab has 21 embeddings; a sandbox has 1. Without correction, content-rich items dominate the retrieval window. The fix: score entities by their best-matching embedding, not by how many embeddings they have.

```sql
WITH candidates AS (
    -- Stage 1: retrieve a generous window of raw embedding matches
    -- Optional content_type filter narrows search to specific types
    SELECT content_id, embed_type, module_title,
           1 - (embedding <=> $query_vector) AS similarity
    FROM embeddings
    WHERE ($content_types IS NULL OR content_type = ANY($content_types))
    ORDER BY embedding <=> $query_vector
    LIMIT 200
)
-- Stage 2: group by entity, take best match, apply quality threshold
SELECT content_id,
       MAX(similarity) AS best_similarity,
       (ARRAY_AGG(embed_type ORDER BY similarity DESC))[1] AS best_match_type,
       (ARRAY_AGG(module_title ORDER BY similarity DESC))[1] AS best_match_module
FROM candidates
WHERE similarity >= 0.45                -- quality threshold (equivalent to current distance_cutoff 0.55)
GROUP BY content_id
ORDER BY best_similarity DESC
LIMIT 25;                               -- min entities passed to triage (configurable, may increase)
```

**Why 200 → 25:** The current search retrieves 25 embeddings, which is roughly 25 entities (mostly 1:1). With heterogeneous content, a single entity can have 20+ embeddings. The wider retrieval window (200) ensures diverse entity representation after grouping. The quality threshold drops poor matches before grouping, same as today's `distance_cutoff`. The entity limit (25) is a floor, not a ceiling — with typed result grouping (labs, architectures, interactive experiences), we may need to increase this so that each group has enough candidates. If labs take 20 of 25 spots, only 5 remain for other types. The limit should be tuned during implementation based on how typed grouping works in practice.

This gives the rationale phase useful context: "your best match in this lab was the 'Storage Configuration' module."

The summary embedding captures breadth ("what is this thing about"). Detail embeddings capture depth (specific topics within the content). The entity's search rank is determined by whichever embedding best matches the query. No entity is advantaged by having more embeddings.

#### Content Type Prefix in Embedded Text

The text passed to the embedding model includes a content type prefix: "Hands-on lab: ..." vs. "Reference architecture: ..." vs. "Environment: ...". This gives the embedding model a signal to place different content types in slightly different vector space regions, improving type-filtered search quality.

#### Model and Index Considerations

- **Vector dimension** is configurable. Currently 384 (all-MiniLM-L6-v2). Upgrade to 768 or 1024 dims is a one-time re-embed migration (change column type, re-embed all content), not a schema redesign.
- **Embedding model** may move from local sentence-transformers to a LiteMaaS-hosted model. The schema doesn't constrain this choice.
- **IVFFlat** index is current. HNSW (better recall, higher memory) is supported by pgvector. Index strategy is an operational decision, not a schema decision.

### 6. Performance Metrics

Replacing `reporting_metrics` with a model that supports multiple usage channels and combines sales-touch and marketing-touch data.

#### Channels

| Channel | Lens | What It Measures | Applies To |
|---------|------|-----------------|------------|
| `rhdp` | Sales-touch | Provisions, pipeline, closed deals, costs | Babylon items (today); any hands-on item (future) |
| `interactive_labs` | Marketing-touch | Provisions (same Babylon backend), campaign attribution | Any content type fronted by IL (today: Babylon; future: any) |
| `web` | Organic | Page views, downloads, unique visitors | Portfolio Architectures, Interactive Experiences |

Interactive Labs is NOT hardcoded to Babylon. Any content type could be fronted by Interactive Labs in the future.

#### Schema

```sql
CREATE TABLE performance_channels (
    id                      SERIAL PRIMARY KEY,
    content_id              TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    channel                 TEXT NOT NULL,

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

CREATE INDEX idx_ec_content_id ON performance_channels(content_id);
CREATE INDEX idx_ec_channel ON performance_channels(channel);
```

```sql
CREATE TABLE performance_scores (
    content_id      TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    performance_score INTEGER NOT NULL DEFAULT 0,
    score_breakdown JSONB,
    channel_scores  JSONB,   -- {"rhdp": {"score": 45, ...}, "interactive_labs": {"score": 72, ...}}
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    ignored_until   DATE
);

CREATE INDEX idx_es_score ON performance_scores(performance_score DESC);
```

Adding new metric columns in the future is a one-line Alembic migration (`ALTER TABLE ADD COLUMN` — metadata-only, no locking in PostgreSQL for nullable columns).

#### Three Views

**Sales lens:** Filter `performance_channels` to `channel = 'rhdp'`. Score using the current 4-factor formula (usage, pipeline, sales, ROI). Same data and logic as today's retirement analysis.

**Marketing lens:** Filter to `channel = 'interactive_labs'` or `channel = 'web'`. Score using marketing-appropriate factors.

**Combined view:** `performance_scores` holds a combined score considering ALL channels. Example: a Babylon CI with 50 RHDP provisions + 400 Interactive Labs launches = 450 total provisions. Through the sales lens alone (50), it looks like a retirement candidate. Combined (450 + $2M pipeline influenced), it's highly engaged — just through a different channel.

The UI shows per-channel breakdowns so users can see WHERE content is popular. Raw financial data (pipeline dollars, marketing spend) is curator+ only. Regular users see volume metrics and qualitative badges ("High Impact," "Popular").

#### Retirement Workflow

The existing `retirement_workflow` table stays, FK'd to `content_entities.content_id` instead of `catalog_base_name`. Retirement is one possible action informed by performance data, not a separate system. The workflow (approve → notify → start → retired steps, Jira integration) remains Babylon-specific — only hands-on items go through formal retirement.

```sql
CREATE TABLE retirement_workflow (
    content_id          TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    status              TEXT NOT NULL DEFAULT 'reviewed',
    step_reviewed_at    TIMESTAMPTZ,
    step_reviewed_by    TEXT,
    step_approved_at    TIMESTAMPTZ,
    step_approved_by    TEXT,
    step_notified_at    TIMESTAMPTZ,
    step_notified_by    TEXT,
    step_started_at     TIMESTAMPTZ,
    step_started_by     TEXT,
    step_retired_at     TIMESTAMPTZ,
    step_retired_by     TEXT,
    jira_key            TEXT,
    jira_url            TEXT,
    notes               TEXT,
    approval_snapshot   JSONB
);
```

### 7. Browse/Search Integration

#### Browse Listing

Every card renders from `content_entities` alone:

```
┌─────────────────────────────────────────────────────┐
│ [Lab]  OpenShift Getting Started                    │
│ Hands-on workshop covering OCP basics...            │
│ Products: OpenShift, RHACS    Difficulty: Beginner  │
│ ↓ Expand                                            │
├─────────────────────────────────────────────────────┤
│ [Architecture]  Hybrid Cloud App Platform           │
│ Reference architecture for multi-cloud application  │
│ Products: OpenShift, ACM, ACS    Difficulty: Adv    │
│ ↓ Expand                                            │
├─────────────────────────────────────────────────────┤
│ [Sandbox]  AWS Open Environment                     │
│ AWS environment with OpenShift 4.20, full creds     │
│ Products: OpenShift, Ansible     Cloud: AWS         │
│ ↓ Expand                                            │
└─────────────────────────────────────────────────────┘
```

Content type badge from `content_type`. Products show the top 3 (truncated with "+N more" overflow). Qualitative performance badges ("High Impact," "Popular") for high-performance items, visible to all users. Raw scores and financials are curator+ only.

#### Detail View (Expanded Card)

Consistent template structure — same sections in the same order, show/hide based on available data:

| Section | Appears For | Data Source |
|---------|-------------|-------------|
| **Overview** | All types | `content_entities` (summary, products, audience, difficulty) |
| **Content** | Types with guided content | Type-specific analysis table (modules, patterns, steps) |
| **Infrastructure** | All Babylon types (lab, demo, sandbox) | `babylon_items` (cloud, OCP version, AgD config, workloads) |
| **Similar Content** | All types | Embedding similarity |
| **Curator** | Curator+ only | Tags, notes, performance data, actions |

Expanding a card requires 1-2 primary-key lookups (analysis table + extension table). Sub-millisecond at the database level, well under 100ms including API overhead. Same pattern as today.

#### Filters

**Universal filters** (all content types): Content type checkboxes, products multi-select (controlled vocabulary), difficulty, search.

**Conditional filters** (appear based on selected content types): Babylon types selected → stage, cloud provider, AgD config, workloads. Architectures selected → verticals, solutions. "Hands-On only" toggle → hides non-hands-on types.

#### Search

Single search box. The user types, results appear. No mode toggle. Whether the implementation uses PostgreSQL full-text search (tsvector), vector search, or a hybrid is an implementation decision. Requirements:

- Searches across ALL content types by default
- Content type filters narrow results post-search
- Target latency: sub-200ms
- Searches against summary, display_name, and products on content_entities (one table, fast)

The API supports filtered search:

```
GET /catalog/items?search=openshift+networking
GET /catalog/items?search=openshift+networking&content_type=lab,architecture
```

Facet counts in the response reflect current filter state:

```json
{
  "facets": {
    "content_types": {"lab": 142, "demo": 38, "sandbox": 45, "architecture": 200},
    "products": {"OpenShift": 380, "Ansible": 95},
    "difficulty": {"beginner": 120, "intermediate": 200, "advanced": 120}
  }
}
```

### 8. Advisor Integration Path

#### Phase 1 (This Migration)

The data model changes. The pipeline code adapts to the new schema (`content_id` instead of `ci_name`, new table names/joins). The UI and user-visible behavior stay identical. Only Babylon content exists — no grouping headers, no type badges, no new card layouts. Everything looks and works exactly as today.

#### Phase 2 (When New Content Types Are Ingested)

Pipeline, UI, and UX changes are implemented alongside each content type's ingestion spec. The data model is already ready; the presentation layer evolves when there's something new to present.

#### Babylon Ingestion Pipeline Changes (Phase 1)

The nightly pipeline has 5 steps. Here is exactly what changes in each.

**Step 1 — Catalog Refresh (`ops.py → run_catalog_refresh`)**

Currently: `CatalogReader.refresh_catalog()` produces item dicts → `db.upsert_catalog_item(item)` writes all 30+ fields to `catalog_items` in one upsert → `db.sync_workloads()` → `db.sync_acl_groups()` → `db.retire_removed_items()`.

Changes:
- `CatalogReader` output stays the same — it still produces item dicts from CRDs.
- The single `upsert_catalog_item()` call becomes `upsert_babylon_catalog_item()`, which writes to both normalized tables in one transaction:
  1. `content_entities` — universal fields: `content_id` (generated as `f"babylon:{ci_name}"`), `source='babylon'`, `content_type` (heuristic: has showroom_url + Workshop/Lab category → `lab`, has showroom_url + Demo category → `demo`, no showroom_url → `sandbox`), `is_hands_on=True`, `display_name`, `retired_at=NULL`.
  2. `babylon_items` — Babylon-specific fields: ci_name, stage, namespace, showroom_url, cloud_provider, etc.
  This is the natural consequence of normalization — the data that used to go into one table now goes into two.
- `db.sync_workloads(content_id, workloads)` — FK changes from ci_name to content_id.
- `db.sync_acl_groups(content_id, acl_groups)` — FK changes from ci_name to content_id.
- `db.retire_removed_items(current_content_ids)` — operates on `content_entities.retired_at` instead of `catalog_items.retired_at`. Same soft-delete logic, different table.
- Content type classification runs ONCE during refresh and is stored on `content_entities`. Not re-computed on queries.

**Step 2 — Stale Check (`ops.py → run_stale_check`)**

Currently: Groups CIs by (showroom_url, showroom_ref) from `catalog_items`, checks git SHA, marks stale on `showroom_analysis`.

Changes:
- The grouping query joins `content_entities` + `babylon_items` to get showroom_url/ref (these fields are on `babylon_items` now).
- `db.mark_stale(content_id, new_commit)` and `db.clear_stale(content_id)` operate on `showroom_analysis` keyed by content_id instead of ci_name.
- Only items with `content_type IN ('lab', 'demo')` are checked — sandboxes have no Showroom content.

**Step 3 — Analysis Enqueue (`ops.py` + `scan.py → run_analysis`)**

Currently: `db.get_items_needing_analysis()` → SHA dedup → enqueue `run_analysis(ci_name)` → `analyze_showroom()` → `db.upsert_showroom_analysis()` → `db.clear_embeddings(ci_name)` → `db.store_embedding(ci_name, ...)` → sibling propagation.

Changes:
- `db.get_items_needing_analysis()` → joins `content_entities` + `babylon_items` + `showroom_analysis`. Filters to `content_type IN ('lab', 'demo')` (sandboxes are excluded).
- `run_analysis` receives `content_id` instead of `ci_name`. Internally looks up `babylon_items` to get showroom_url, ref, etc.
- `db.upsert_showroom_analysis(analysis_data)` — keyed by `content_id` instead of `ci_name`.
- **NEW: `db.update_content_entity_card(content_id, summary, products_json, topics_json, audience_json, difficulty)`** — after analysis succeeds, denormalize the triage-contract fields to `content_entities`. This is a new write that doesn't exist today. It runs inside the same transaction as the analysis upsert.
- `db.clear_embeddings(content_id)` + `db.store_embedding(content_id, content_type, source, embed_type, ...)` — keyed by `content_id`, adds `content_type` and `source` metadata on each embedding row.
- Sibling propagation — `db.get_siblings_by_showroom()` queries `babylon_items` (not `catalog_items`). Propagation writes to both `showroom_analysis` (by content_id) AND updates the sibling's `content_entities` card fields. Published CI promotion resolves `published_ci_name` from `babylon_items`.

**Step 4 — Workload Scan (`ops.py → run_workload_scan`)**

Currently: Scans AgnosticD v2 collection repos, LLM-classifies roles, writes to `workload_mapping`.

Changes: None to the scan logic itself. `workload_mapping` and `workload_aliases` are independent reference tables. The FK on `babylon_item_workloads` changes from ci_name to content_id, but the workload scanner doesn't write to that table — `sync_workloads()` in Step 1 does.

**NEW Step 4b — Sandbox Summary Generation**

This is entirely new. After workload scanning completes (so workload mappings are current):

1. Query all `content_entities` with `content_type = 'sandbox'` that need summary generation (summary is NULL or workloads have changed since last generation).
2. For each sandbox:
   - Look up its workloads: `babylon_item_workloads` → `workload_mapping` → get product names and descriptions.
   - Read infrastructure metadata from `babylon_items`: cloud_provider, ocp_version, agd_config, CRD description.
   - Assemble summary text from workload descriptions + infrastructure metadata. This is template-based assembly from already-classified data, not a fresh LLM call.
   - Write `summary`, `products_json` (from workload product names), and `topics_json` (from workload categories) to `content_entities`.
   - Generate and store a summary embedding in `embeddings` (content_type='sandbox', embed_type='summary').
3. This step runs AFTER workload scanning because workload mappings feed the summary.

**Step 5 — Reporting Sync (`reporting_sync.py → run_reporting_sync`)**

Currently: Queries RHDP Reporting MCP → computes metrics and retirement scores → `db.upsert_reporting_metrics(catalog_base_name, ...)`.

Changes:
- Output table changes from `reporting_metrics` to `performance_channels` with `channel = 'rhdp'`.
- Key mapping: `catalog_base_name` → resolve to `content_id` via `babylon_items.ci_name` (the base name extraction logic stays — it strips stage suffixes to find the base CI, then looks up the content_id).
- Score computation writes to `performance_scores` instead of `retirement_score` on `reporting_metrics`.
- The scoring formula itself is unchanged for Phase 1 — same 4-factor model, just writing to a different table. Multi-channel scoring is Phase 2.
- Published/base CI metric merging (`_merge_published_base_pairs()`) resolves through `babylon_items.published_ci_name` / `base_ci_name` instead of `catalog_items`.

#### Advisor Pipeline Changes (Phase 1)

**vector_search.py:**
- `search_embeddings()` in the Database class changes: joins `embeddings` → `content_entities` (instead of `catalog_items` + `showroom_analysis`). Returns `content_id`, `content_type`, `source`, `is_hands_on`, `display_name` alongside similarity scores.
- MAX(similarity) per content_id scoring replaces the current first-match dedup.
- Stage promotion (base → published) is gated on `source = 'babylon'` and resolves through `babylon_items.published_ci_name`.
- Content-hash-based dedup (same Showroom → same analysis) is handled at the entity level by content_id. Sibling propagation during analysis already ensures siblings share the same analysis — dedup at search time just needs content_id uniqueness.
- `Candidate` dataclass gains: `content_id`, `content_type`, `source`, `is_hands_on`, `ci_name` (nullable, for backward compat), `best_match_type`, `best_match_detail`.

**triage.py:**
- Reads triage-contract fields from `content_entities` (same single-table query, just different table name).
- `content_type` added to each candidate block in the triage prompt.
- For Phase 1 (Babylon only), all candidates are labs, demos, or sandboxes. The triage prompt gains awareness of sandboxes: "Sandboxes are environments without guided content — evaluate based on infrastructure capabilities and products available."

**rationale.py:**
- The formatter routes by content_type. For Phase 1, two paths:
  - Lab/Demo: fetches from `showroom_analysis` (same as today, keyed by content_id).
  - Sandbox: fetches from `babylon_items` (infrastructure metadata) + `babylon_item_workloads` → `workload_mapping` (installed products). Formats as capabilities, not modules.
- The rationale prompt for sandboxes: "This is an environment without a guided lab. Explain what's available and how the user could use it for their needs."

**pipeline.py:**
- `QueryState` gains `grouped_results` for typed grouping (prepared for Phase 2, but in Phase 1 all results are hands-on Babylon items, so grouping is a no-op).
- Usage boost (`_apply_usage_boost`) reads from `performance_channels` instead of `reporting_metrics`.

**models.py — Candidate additions:**
```python
content_id: str           # replaces ci_name as primary identifier
content_type: str         # 'lab', 'demo', 'sandbox', 'architecture', 'interactive_experience'
source: str               # 'babylon', 'portfolio_arch'
is_hands_on: bool
ci_name: str | None       # kept for backward compat, None for non-Babylon
best_match_type: str      # which embedding matched best
best_match_detail: str    # which specific module/section matched
```

**advisor_sessions:**
- Add `chosen_content_id` column alongside `chosen_ci_name` (keep both for backward compat with historical data).
- `results_json` stores new Candidate shape including content_type.

#### Database Layer Changes (Phase 1)

Key method changes in `database.py`:

| Current Method | New Method(s) | Change |
|---------------|--------------|--------|
| `upsert_catalog_item(item)` | `upsert_babylon_catalog_item(item)` | Splits item across `content_entities` + `babylon_items` in one transaction |
| `get_catalog_item(ci_name)` | `get_content_entity(content_id)` + `get_babylon_item(content_id)` | Also: `get_babylon_item_by_ci_name(ci_name)` for backward compat |
| `upsert_showroom_analysis(analysis)` | Same name, keyed by `content_id` | Plus: `update_content_entity_card()` for denormalization |
| `clear_embeddings(ci_name)` | `clear_embeddings(content_id)` | FK change |
| `store_embedding(ci_name, ...)` | `store_embedding(content_id, content_type, source, ...)` | Adds type metadata |
| `search_embeddings(...)` | Rewritten: joins content_entities, MAX(similarity) scoring, content_type filter | Major rewrite |
| `list_catalog_items_filtered(...)` | Rewritten: queries content_entities + babylon_items | Major rewrite |
| `retire_removed_items(ci_names)` | `retire_removed_items(content_ids)` | Operates on content_entities |
| `get_siblings_by_showroom(url, ref)` | Same logic, queries `babylon_items` | Table name change |
| `get_reporting_metrics(base_name)` | `get_performance_channels(content_id)` + `get_performance_score(content_id)` | New tables |

#### API Route Changes (Phase 1)

| Endpoint | Change |
|----------|--------|
| `GET /catalog` | Queries `content_entities` + `babylon_items` instead of `catalog_items`. Adds `content_type` filter. Response includes `content_id` and `content_type`. |
| `GET /catalog/{content_id}` | Path parameter is `content_id`. Detail response assembles from content_entities + babylon_items + showroom_analysis + workloads. CI name lookup available via query parameter: `GET /catalog?ci_name=...` if needed. |
| `GET /catalog/{identifier}/similar` | Uses new embedding search with MAX(similarity) scoring. |
| `GET /catalog/facets` | Adds `content_type` facet. Queries content_entities for universal facets, babylon_items for Babylon-specific facets. |
| `GET /catalog/stats` | Queries content_entities for total counts, breakdowns by content_type. |
| Curator endpoints (tags, notes, flag, override-url, duration) | Path parameter is `content_id`. |
| `GET /analysis/retirement` | Queries `performance_channels` + `performance_scores` instead of `reporting_metrics`. Response shape stays the same for Phase 1. |

#### RecCard Changes (Phase 2 Only)

- Content type badge in card header
- Conditional sections by content_type:
  - Lab/Demo: "Order" action, modules, duration, Showroom link
  - Architecture: "View architecture" action, patterns, solution areas, diagram
  - Sandbox: "Order" action, workloads, cloud/OCP info
  - IE: "Start experience" action, estimated time, step count
- `why_it_fits`, `how_to_use`, `caveats` render identically regardless of type

#### Grouped Results (Phase 2 Only)

Results appear under section headers ("Hands-On Content," "Reference Material," etc.). Empty groups omitted. Single-type results show no grouping headers.

#### Data Contract for Any Future Recommendation Engine

Whether the recommendation engine is pgvector + LLM (current), LightFM, or something else:

| Data Need | Source Table |
|-----------|-------------|
| Content features | `content_entities` |
| Content embeddings | `embeddings` |
| Full analysis detail | Type-specific analysis tables |
| Performance signals | `performance_channels` + `performance_scores` |
| User interaction history | `advisor_sessions` |
| Product/topic relationships | `content_entities.products_json` + controlled vocabulary |

The content model provides all six. The recommendation engine consumes them.

### 9. Migration Strategy

Fresh schema build with selective data preservation. The nightly pipelines repopulate everything from source.

#### What We Keep

| Data | Reason | Migration |
|------|--------|-----------|
| `advisor_sessions` | Query history for trend/gap data mining | Add `content_id` column, map via `'babylon:' \|\| ci_name` |
| `retirement_workflow` (active rows) | Don't lose in-progress retirements | Map `catalog_base_name` → `content_id`, carry status + notes |
| Curator notes from `showroom_analysis.notes` | Curator-written context | Restore after repopulation, matched by CI name |

#### What Regenerates

| Data | Regenerates From |
|------|-----------------|
| Catalog → `content_entities` + `babylon_items` | Next CRD scan |
| Showroom analysis | Next nightly scan pipeline |
| Embeddings | Generated during scan after analysis |
| Performance metrics | Next reporting sync from RHDP Reporting MCP |
| Workloads | Next workload scan |
| Content similarity | Recomputed after embeddings exist |

`content_similarity` (pre-computed pairwise entity similarities for Browse "Similar Content" section) is recreated with the new FK scheme:

```sql
CREATE TABLE content_similarity (
    id SERIAL PRIMARY KEY,
    content_id_a TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_id_b TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    similarity_score REAL NOT NULL,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id_a, content_id_b)
);
```

#### What We Drop (Historical Data Only)

- `enrichment_tags` — no meaningful curator tags exist
- `token_usage` — historical telemetry; table recreated empty
- `analysis_log` — historical audit trail; table recreated empty
- `jobs` — transient queue state; table recreated empty
- `api_keys` — table recreated as-is (no migration needed, keys re-created)

Operational tables (`jobs`, `token_usage`, `analysis_log`, `api_keys`) are part of the new schema — they just start empty. No historical data needs preserving.

#### Migration Sequence

**Step 1:** Create the new schema — `content_entities`, `babylon_items`, `showroom_analysis`, `embeddings`, `content_similarity`, performance tables, `retirement_workflow`, and operational tables (`jobs`, `token_usage`, `analysis_log`, `api_keys`). Portfolio Architecture and Interactive Experience tables are NOT created here — they are created by their respective ingest specs.

**Step 2:** Preserve the keepers — copy `advisor_sessions` with content_id mapping, export active `retirement_workflow` rows and curator notes.

**Step 3:** Swap schemas — drop old tables, new schema is active.

**Step 4:** Run the pipelines:
- Catalog refresh → populates `content_entities` + `babylon_items` (minutes)
- Scan pipeline → populates `showroom_analysis` + `embeddings` (hours — LLM analysis for ~200 items)
- Reporting sync → populates `performance_channels` + `performance_scores` (minutes)
- Workload scan → populates `babylon_item_workloads` (30 minutes)

**Step 5:** Restore curator notes — match by CI name, write to `showroom_analysis.notes`.

**Step 6:** Create `vocabularies.yaml` — bootstrap from freshly generated analysis data, curate. Existing analysis keeps current values; vocabulary enforcement starts on next re-analysis cycle.

Portfolio Architecture and Interactive Experience tables are NOT created during this migration. They are created by their respective ingest specs when those sources are ready. This migration delivers the foundation — `content_entities`, `babylon_items`, `showroom_analysis`, `embeddings`, performance tables — and the pattern for extending it.

#### Timeline

One nightly cycle and the system is fully populated. Dev environment first — validate everything repopulated correctly before any other environment.

#### Risks

| Risk | Mitigation |
|------|------------|
| Content type classification wrong for some items | Classification heuristic: has showroom_url + "Workshop"/"Lab" category → `lab`; has showroom_url + "Demo" category → `demo`; no showroom_url → `sandbox`. Curator spot-checks after Step 4 |
| Reporting sync mapping loses data | 1:1 mapping (reporting_metrics row → performance_channels row with channel='rhdp'). Validate row counts |
| External systems using ci_name break | No external API consumers exist yet (API keys not active). ci_name stays on babylon_items for reference and is available via query parameter lookup. CLI and frontend are updated as part of this migration. |
| Scan pipeline takes too long for full re-analysis | Pipeline already handles this — hash-based donor reuse and sibling propagation reduce redundant analysis |

## What This Spec Does NOT Define

- **Portfolio Architecture ingest pipeline** — downstream spec. Implements this model for one source.
- **Interactive Experience ingest** — future. Extension table and ingest pipeline defined when ready.
- **Performance scoring formula for marketing-touch data** — depends on available metrics from the marketing source.
- **Advisor pipeline redesign** — the current pipeline adapts to the new schema; a full recommendation engine evaluation is a separate effort.
- **Browse/Advisor UI redesign** — Phase 1 is invisible to users. UI changes happen alongside new content type ingestion.
- **Embedding model upgrade** — separate decision. Schema supports any dimension.
- **Graph database evaluation** — not required by this model, not prevented by it. `content_id` works as a graph node ID if a graph layer is added later.

## Relationship to Other Specs and Backlog Items

- **OSSPA/Portfolio Architecture ingest** — implements this model for the Portfolio Architecture source. Should be written AFTER this spec is approved.
- **Enhanced catalog search** (backlog) — uses the embeddings infrastructure defined here. Semantic search in Browse queries the same embedding table and scoring approach.
- **Recommendation system evaluation** (backlog) — this spec defines the data contract any recommendation engine needs. The evaluation can proceed independently.
- **Performance analysis** — evolves the current retirement analysis with multi-channel data. Scoring formula and UI are downstream.
