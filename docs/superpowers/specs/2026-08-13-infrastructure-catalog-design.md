# Infrastructure Catalog Design

Enrich RCARS with a parallel catalog of AgnosticD v2 infrastructure — workload roles and base configs — so the system can answer questions about what environments provide, recommend sandboxes alongside guided content, and surface cross-type connections through overlap/similarity.

## Problem

RCARS catalogs content (labs, demos) well but is blind to infrastructure. A sandbox with OpenShift AI pre-installed can never be recommended because RCARS only understands Showroom-analyzed guided content. Workload roles have single-sentence descriptions. Base configs (openshift-cluster, cloud-vms-base) have no descriptions at all. The advisor cannot route infrastructure queries ("I need an environment with AAP") and has no embeddings to search against.

## Constraints

- **All data must come from public AgnosticD repos.** The workload collection repos (core_workloads, ai_workloads, cloud_vm_workloads, namespaced_workloads, cnv_workloads, showroom) and the configs repo (agnosticd-v2/ansible/configs). No private repos.
- **AgnosticV is off-limits for variable data.** The only data pulled from AgnosticV is the workload list on each catalog item's CRD (which workloads a component deploys). No key-value pairs, no variable overrides, no secrets.
- **v2 only.** AgnosticD v1 items are not tracked.

## Data Model

### `infrastructure` table (new)

Unified table for both workload roles and base configs, distinguished by `type`.

```sql
CREATE TABLE IF NOT EXISTS infrastructure (
    role_name   TEXT PRIMARY KEY,
    fqcn        TEXT,
    collection  TEXT,
    type        TEXT NOT NULL,       -- 'config' or 'workload'
    description TEXT,                -- LLM-generated rich narrative
    products    JSONB DEFAULT '[]',  -- what it installs: ["OpenShift AI", "KServe"]
    capabilities JSONB DEFAULT '[]', -- what it enables: ["model-serving", "notebook-hosting"]
    category    TEXT,                -- ai_ml, security, networking, storage, etc.
    requires    JSONB DEFAULT '[]',  -- prerequisites: ["openshift 4.14+", "gpu-nodes"]
    source_sha  TEXT,
    scanned_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_infrastructure_type ON infrastructure(type);
CREATE INDEX IF NOT EXISTS idx_infrastructure_category ON infrastructure(category);
```

**Replaces:** `workload_mapping` and `workload_scan_state`. The `workload_aliases` table is retained — aliases resolve user queries to canonical `products` values before searching.

### Join model

Two join paths, both already established:

- **Configs → catalog items:** `babylon_items.agd_config` → `infrastructure.role_name` WHERE `type = 'config'`. No schema change needed. Every v2 catalog item already stores its config name.
- **Workloads → catalog items:** `babylon_item_workloads.workload_role` → `infrastructure.role_name` WHERE `type = 'workload'`. Existing join table, unchanged.

### Embeddings

Infrastructure embeddings go into the existing shared `embeddings` table with `content_type = 'infrastructure'` and `content_id` set to `role_name`. The embedding text is built from the `description`, `products`, `capabilities`, and `category` fields — same pattern as `build_embedding_text()` for content entities.

Vector search is always type-filtered:
- Content queries: `WHERE content_type IN ('lab', 'demo', ...)`
- Infrastructure queries: `WHERE content_type = 'infrastructure'`
- Never combined in a single unfiltered search

## Scanning & Ingestion

### Workload roles

Extends the existing scanner (`workload_scanner.py`). Today it clones 6 collection repos, reads role code (defaults/main.yml, tasks/main.yml, meta/main.yml, templates), and asks an LLM to identify the product and write one sentence.

**Changes:**
- Richer LLM prompt that produces the full structured output: `description` (multi-sentence narrative covering what it installs, configures, and enables, including default configuration choices), `products` (array), `capabilities` (array), `category`, `requires` (array).
- The description should mention key configuration options and their defaults as discovered from the public role code (e.g., "default authentication provider is KeyCloak"), but these are embedded in the narrative text, not stored as structured variable data.
- Output targets the `infrastructure` table with `type = 'workload'` instead of `workload_mapping`.
- SHA-based skip logic retained via `source_sha` on the `infrastructure` row (replaces `workload_scan_state`).

### Base configs

New scan target: the configs directory at `agnosticd-v2/ansible/configs/`. Same pattern as workload scanning:

1. Clone/pull the repo, check SHA against stored `source_sha` per config.
2. For each config directory (excluding `test-empty-config`), read `default_vars.yml`, provider-specific `default_vars.yml`, `README.adoc`, and key playbooks (`software.yml`, `post_software.yml`).
3. LLM analyzes the code and produces the same structured output.
4. Upsert into `infrastructure` with `type = 'config'`, `role_name` matching the directory name (e.g., `openshift-cluster`, `cloud-vms-base`, `namespace`).

### Nightly pipeline

Both scans run as part of the existing nightly pipeline. Configs scan is cheap (6 configs, rarely change). Workload scan is the existing Step 4, writing to the new table.

After scanning, embeddings are generated for any `infrastructure` rows with `scanned_at` newer than the most recent embedding.

## Advisor Integration

### Target dimension on recommend

The `recommend` intent gains a `target` field. Infrastructure is not a separate intent — the intent is always "recommend," the target specifies what kind of thing to recommend.

```python
class RecommendArgs(BaseModel):
    search_query: str = ""
    constraints: dict = {}
    target: str | None = None  # "content", "infrastructure", or None
```

Router classification:
- "I need a lab that teaches OpenShift AI" → `target: "content"`
- "I need an environment with OpenShift AI installed" → `target: "infrastructure"`
- "What do you have for OpenShift AI?" → `target: null` → clarification

When `target` is null and the query is ambiguous, the advisor asks: "Are you looking for guided content (labs/demos) or an environment with this installed?"

### UI target control

The advisor page gets a target toggle/filter that lets users pre-select what they're looking for (All, Guided Content, Environments). When set, this value is sent with the chat message and overrides the router's classification for the target dimension. The LLM still handles intent classification (recommend vs overlap vs performance), but the target is settled by the UI.

This avoids forcing every query through the probabilistic router for a dimension the user can simply declare.

### Recommend handler changes

The `handle_recommend` handler dispatches based on `target`:

- **`target: "content"`** — Today's behavior. Search content embeddings, run through the recommendation pipeline.
- **`target: "infrastructure"`** — Search infrastructure embeddings. Results are `infrastructure` rows (workloads/configs), not catalog items. Join through `babylon_item_workloads` and `babylon_items.agd_config` to find which catalog items deploy the matched infrastructure. Return catalog items grouped by the infrastructure match.
- **`target: null`** — Ask clarification before searching.

### Cross-type discovery

The overlap/similarity system can bridge across types as a "see also" mechanism. After returning primary results for one target, the advisor can note related items of the other type: "Here are 4 labs covering OpenShift AI. There are also 2 sandbox environments with it pre-installed."

This is a presentational enhancement, not a mixed search — primary results stay type-pure, cross-type connections are secondary suggestions.

## Workloads Page Redesign

The current Workloads page (`WorkloadsPage.tsx`) is a curator management tool built around a mapped/unmapped paradigm — curators manually map workload roles to product names, toggle verified status, and track who added each mapping. With scanner-generated data, that workflow is obsolete. The page becomes a browse/explore view of the infrastructure catalog.

### What goes away

- **Mapped vs unmapped sections.** Everything in the `infrastructure` table is scanner-populated. No manual mapping forms.
- **Verified badges and added_by.** All entries come from the scanner. No human-in-the-loop verification.
- **Manual "Map this workload" and "Remove mapping" actions.** The scanner is the source of truth.

### What the page shows

Two browsable sections, filterable by type:

**Infrastructure catalog** — each entry shows:
- **Role name** and **FQCN** (identity)
- **Type** badge — "Config" or "Workload"
- **Description** — the rich LLM-generated narrative
- **Products** — rendered as pills/tags (e.g., "OpenShift AI", "KServe")
- **Capabilities** — rendered as pills (e.g., "model-serving", "notebook-hosting")
- **Category** — e.g., ai_ml, security, networking
- **Requires** — prerequisites rendered as pills
- **Collection** — which AgnosticD collection it came from
- **Last scanned** — timestamp from `scanned_at`

**Catalog item mappings** — expandable per entry:
- For workloads: list of catalog items that deploy this workload (from `babylon_item_workloads` join), with display name, stage badge, and link to the item in Browse.
- For configs: list of catalog items using this config (from `babylon_items.agd_config` join), same presentation.
- Item count shown on the collapsed row (e.g., "Used by 23 items").

### Filters

- **Text search** — searches across role name, description, products, capabilities
- **Type** — Config, Workload, or All
- **Category** — dropdown from distinct categories
- **Collection** — dropdown from distinct collections
- **Has mappings** — toggle to show only entries that map to at least one catalog item, or entries with no mappings (orphan infrastructure)

### Access

The page remains accessible to all authenticated users (not curator-gated). The data is read-only — no edit actions. Curators see the same view as everyone else.

### API changes

The existing `/catalog/workload-mappings` endpoint is replaced (or aliased) by a new `/catalog/infrastructure` endpoint that returns the full `infrastructure` table rows with item counts. The `/catalog/workload-mappings/unmapped` endpoint is removed — the concept of "unmapped" no longer applies.

### Phase

This is part of **Phase 3 (UI)** but could ship with Phase 1 if the page is built as a simple read-only view of the `infrastructure` table before advisor integration lands.

## Migration

### Schema migration

- Add `infrastructure` table via `CREATE TABLE IF NOT EXISTS` in `SCHEMA_SQL`.
- Migrate existing `workload_mapping` data into `infrastructure` with `type = 'workload'`. One-time migration in `create_schema()` or a migration script.
- `workload_mapping` and `workload_scan_state` can be dropped after migration (or retained temporarily with the scanner writing to both during transition).
- `workload_aliases` retained as-is — it resolves user-facing names to canonical product names, independent of the backing table.

### Code changes

- `workload_scanner.py` → writes to `infrastructure` instead of `workload_mapping`.
- New config scanner (can live in same file or `config_scanner.py`).
- `database.py` — new queries for infrastructure search, join queries for "which items deploy this workload/config."
- `sandbox_summary.py` — reads from `infrastructure` instead of `workload_mapping` for product classifications.
- `handlers.py` — `handle_recommend` gains target dispatch logic.
- `registry.py` — updated prompt fragment and examples for the `target` dimension.
- `models.py` — `RecommendArgs` gains `target` field.
- Frontend — advisor page target toggle, infrastructure result rendering.

### Dead code removal

The old workload mapping system is fully replaced. Remove all of the following as part of this work — no dead code left behind:

**Database:**
- Drop `workload_mapping` table (after data migration to `infrastructure`).
- Drop `workload_scan_state` table (replaced by `source_sha` on `infrastructure` rows).
- Remove all `workload_mapping`/`workload_scan_state` DDL from `SCHEMA_SQL`.
- Remove `database.py` methods: `upsert_workload_mapping()`, `get_workload_mappings()`, `get_unmapped_workloads()`, `delete_workload_mapping()`, `get_workload_classifications()`, and any other methods that query the old tables. Replace with equivalent methods against `infrastructure`.

**API endpoints:**
- Remove `POST /catalog/workload-mappings` (manual mapping — scanner is source of truth).
- Remove `DELETE /catalog/workload-mappings/{role}` (manual deletion).
- Remove `GET /catalog/workload-mappings/unmapped` (unmapped concept gone).
- Replace `GET /catalog/workload-mappings` with `GET /catalog/infrastructure` returning the new table data with item counts.

**CLI:**
- Remove `rcars workload sync` command (loaded from `workload_mapping.yaml` seed file — no longer needed).
- Remove or repurpose `rcars workload` subgroup if no commands remain.

**Seed data:**
- Remove `src/api/rcars/data/workload_mapping.yaml` (34 curated mappings, superseded by scanner).

**Frontend:**
- Remove manual mapping form, "Map this workload" / "Remove mapping" actions, verified badge rendering, added_by display, and the mapped/unmapped section split from `WorkloadsPage.tsx`.
- Remove `api.addWorkloadMapping()`, `api.deleteWorkloadMapping()`, `api.getUnmappedWorkloads()` from `api.ts`. Replace `api.getWorkloadMappings()` with `api.getInfrastructure()`.

**Tests:**
- Update or remove tests that exercise the old mapping CRUD (manual add/delete/unmapped queries). Replace with tests against the `infrastructure` table and new API endpoints.

### Phased implementation

1. **Phase 1: Data model + scanner + Workloads page** — `infrastructure` table, migrate existing workload data, enrich scanner for richer descriptions, add config scanning, embeddings generated. Redesigned Workloads page as a read-only browse view of the infrastructure catalog with item mappings. This phase populates the catalog and gives immediate visibility into what was scanned.
2. **Phase 2: Advisor integration** — `target` dimension on recommend, handler dispatch, infrastructure search path, clarification flow.
3. **Phase 3: Advisor UI + cross-type** — Advisor page target toggle, infrastructure result cards, cross-type "see also" suggestions via overlap/similarity.

## What This Does NOT Cover

- **Workload-as-deployed variable mapping.** We cannot determine what specific configuration choices a catalog item makes (e.g., "this item uses KeyCloak") because that data lives in AgnosticV. We can only say "this item uses the authentication workload, which supports KeyCloak, LDAP, or htpasswd."
- **Portfolio architectures.** A separate content type that will use the same `target` mechanism on recommend when implemented.
- **v1 items.** Only AgnosticD v2 configs and workloads are tracked.
- **Private workload repos.** Only public AgnosticD collection repos are scanned.
