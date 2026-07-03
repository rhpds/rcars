# Database Schema Reference

Complete column-level reference for all RCARS database tables. For an overview of how these tables relate to each other and the system architecture, see [System Design](system-design.md).

Schema is managed with two complementary mechanisms:

- **`db.create_schema()`** — `CREATE TABLE IF NOT EXISTS` for all tables. Handles fresh installs.
- **Alembic** — `ALTER TABLE` migrations for schema changes to existing tables. Migration files live in `src/api/alembic/versions/`.

---

## `catalog_items`

One row per catalog item. The primary source of truth for everything read from the Babylon CRDs, including infrastructure metadata for AgnosticD v2 items.

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
| `content_path` | TEXT | Custom content path override (default: `content/modules/ROOT/pages/`) |
| `last_crd_update` | TIMESTAMPTZ | Timestamp of the last CRD change in Babylon |
| `last_refreshed` | TIMESTAMPTZ | Timestamp of the last catalog refresh for this item |
| `is_prod` | BOOLEAN | True if stage is prod |
| `is_published` | BOOLEAN | True if this is a Published Virtual CI |
| `published_ci_name` | TEXT | For Base CIs: the Published VCI that references them |
| `base_ci_name` | TEXT | For Published VCIs: the Base CI they reference |
| `scan_status` | TEXT | Scan state: `not_scanned`, `success`, `failed` |
| `scan_error_class` | TEXT | Error classification when scan failed |
| `scan_error` | TEXT | Error message when scan failed |
| `scan_failed_at` | TIMESTAMPTZ | When the last scan failure occurred |
| `showroom_url_override` | TEXT | Curator-set override for the Showroom URL |
| `is_agd_v2` | BOOLEAN | True if this item uses the AgnosticD v2 deployer |
| `agd_config` | TEXT | V2 config type: `openshift-workloads`, `openshift-cluster`, `namespace`, `cloud-vms-base` |
| `cloud_provider` | TEXT | Cloud provider: `aws`, `openshift_cnv`, `none` |
| `ocp_version` | TEXT | OCP version for cluster-provisioning configs (e.g. `4.20`) |
| `os_image` | TEXT | OS image for `cloud-vms-base` items only (e.g. `rhel-9.6`, `rhel-10.0`) |
| `worker_instance_count` | TEXT | Cluster/VM sizing (TEXT because it can be a Jinja2 template) |
| `control_plane_instance_count` | TEXT | Control plane nodes — `1` for SNO, `3` for multi-node |
| `instances_json` | JSONB | VM instance specs for `cloud-vms-base` items (cores, memory, image, count) |
| `retired_at` | TIMESTAMPTZ | When this item was soft-deleted (disappeared from Babylon). NULL = active. Partial index on `retired_at IS NOT NULL` |
| `retirement_reason` | TEXT | Why the item was retired (e.g., "Disappeared from Babylon CRDs"). NULL = active |

---

## `showroom_analysis`

One row per analyzed catalog item. Stores the structured LLM analysis output plus staleness tracking.

| Column | Type | Description |
|---|---|---|
| `ci_name` | TEXT (PK, FK) | References `catalog_items.ci_name` |
| `content_type` | TEXT | `"workshop"` or `"demo"` |
| `summary` | TEXT | 2-3 sentence summary of the lab |
| `products_json` | JSONB | Red Hat products covered, e.g. `["OpenShift", "RHEL"]` |
| `audience_json` | JSONB | Target audience descriptors |
| `topics_json` | JSONB | Technical topics covered |
| `modules_json` | JSONB | Array of module objects with title, topics, learning objectives, duration |
| `learning_objectives_json` | JSONB | `{stated: [...], inferred: [...]}` |
| `difficulty` | TEXT | `"beginner"`, `"intermediate"`, or `"advanced"` |
| `estimated_duration_min` | INTEGER | Estimated time to complete, in minutes |
| `event_fit_json` | JSONB | Suitability assessments for booth demos, labs, presentations |
| `use_cases_json` | JSONB | Business problems or scenarios this content addresses |
| `last_repo_commit` | TEXT | Git HEAD SHA at time of analysis |
| `last_repo_updated` | TIMESTAMPTZ | Commit date of HEAD at time of analysis |
| `last_analyzed` | TIMESTAMPTZ | When RCARS last analyzed this item |
| `is_stale` | BOOLEAN | True if content has changed since last analysis |
| `stale_commit` | TEXT | HEAD SHA when staleness was detected |
| `content_hash` | TEXT | SHA-256 of filtered .adoc content for change detection |
| `enrichment_review_needed` | BOOLEAN | Curator flag for manual review |
| `notes` | TEXT | Free-text curator note |

---

## `catalog_item_workloads`

Junction table linking catalog items to the workload roles they deploy. Only populated for AgnosticD v2 items. One row per workload per CI.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `ci_name` | TEXT (FK) | References `catalog_items.ci_name` (CASCADE delete) |
| `workload_fqcn` | TEXT | Full Ansible FQCN, e.g. `agnosticd.core_workloads.ocp4_workload_openshift_ai` |
| `workload_role` | TEXT | Role name only (last segment of FQCN), e.g. `ocp4_workload_openshift_ai` |
| `workload_collection` | TEXT | Collection namespace, e.g. `agnosticd.core_workloads` (NULL for bare role names) |

Unique constraint on `(ci_name, workload_fqcn)`. Indexed on `workload_role` for faceted search joins.

---

## `workload_mapping`

Curated mapping from workload role names to human-readable product names. This is the gate between "cataloged" and "queryable by Publishing House." Only mapped workloads surface in faceted search results.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `workload_role` | TEXT (UNIQUE) | Role name, e.g. `ocp4_workload_openshift_ai` |
| `product_name` | TEXT | Canonical product name, e.g. `OpenShift AI` |
| `description` | TEXT | What the workload actually does (from code analysis) |
| `category` | TEXT | Grouping: `ai_ml`, `cicd`, `security`, `storage`, etc. |
| `source_collection` | TEXT | Which agDv2 collection, e.g. `agnosticd.core_workloads` |
| `verified` | BOOLEAN | True if confirmed by reading the actual Ansible code |
| `added_by` | TEXT | Who created/updated the mapping (`seed`, `workload_scanner`, or user email) |
| `added_at` | TIMESTAMPTZ | When the mapping was created |
| `verified_at` | TIMESTAMPTZ | When the mapping was last verified by the scanner |

---

## `workload_aliases`

Alternate names for products so PH queries match regardless of which name is used (e.g. "RHOAI" and "OpenShift AI" both resolve to the same product).

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `product_name` | TEXT | Canonical product name from `workload_mapping` |
| `alias` | TEXT (UNIQUE) | Alternate name (e.g. `RHOAI`, `ACS`, `KubeVirt`) |
| `added_at` | TIMESTAMPTZ | When the alias was added |

---

## `catalog_item_acl_groups`

ACL groups from `__meta__.access_control.allow_groups` in AgnosticD v2 CRDs. Tracks which groups can order each catalog item.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `ci_name` | TEXT (FK) | References `catalog_items.ci_name` (CASCADE delete) |
| `group_name` | TEXT | ACL group name, e.g. `rhpds-devs-ai` |

Unique constraint on `(ci_name, group_name)`.

---

## `workload_scan_state`

Tracks the last-scanned git SHA per agDv2 collection repo. Used by the workload scanner to skip unchanged repos.

| Column | Type | Description |
|---|---|---|
| `collection` | TEXT (PK) | Collection name, e.g. `agnosticd.core_workloads` |
| `last_sha` | TEXT | HEAD SHA from the last successful scan |
| `last_scanned` | TIMESTAMPTZ | When the last scan completed |

---

## `embeddings`

Vector embeddings for semantic search. Each row is one embedded piece of content for one catalog item.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `ci_name` | TEXT (FK) | References `catalog_items.ci_name` |
| `embed_type` | TEXT | `"ci_summary"` (item-level) or `"module"` (per-module) |
| `module_title` | TEXT | Module name — populated only for `embed_type = 'module'` |
| `content_text` | TEXT | The text fed to the embedding model |
| `embedding` | vector(384) | 384-dimensional vector from sentence-transformers |

---

## `enrichment_tags`

Curator-applied labels attached to catalog items.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `ci_name` | TEXT (FK) | References `catalog_items.ci_name` |
| `tag_type` | TEXT | Label category, e.g. `"lifecycle"`, `"event"`, `"quality"` |
| `tag_value` | TEXT | Label value, e.g. `"retiring"`, `"kubecon-2026"` |
| `added_by` | TEXT | Email of the curator who added the tag |
| `added_at` | TIMESTAMPTZ | When the tag was added |

Unique constraint on `(ci_name, tag_type, tag_value)`.

---

## `analysis_log`

Append-only audit trail of operations.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `ci_name` | TEXT | Catalog item involved (not FK — preserved if item deleted) |
| `action` | TEXT | `"refresh"`, `"analyze"`, or `"error"` |
| `user_id` | TEXT | Who or what triggered the action |
| `details` | TEXT | Extra context — error messages, commit SHAs |
| `created_at` | TIMESTAMPTZ | When the action was recorded |

---

## `token_usage`

LLM token consumption tracking per operation and model.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `operation` | TEXT | Operation type: `scan`, `triage`, `rationale`, `event_parse`, `workload_scan` |
| `model` | TEXT | LLM model used |
| `ci_name` | TEXT | Catalog item — for scan/workload_scan operations |
| `query_text` | TEXT | Query text — for triage/rationale operations |
| `input_tokens` | INTEGER | Input tokens consumed |
| `output_tokens` | INTEGER | Output tokens consumed |
| `created_at` | TIMESTAMPTZ | When recorded |

---

## `advisor_sessions`

Advisor conversation sessions and user selections.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `session_id` | TEXT | Groups turns in a conversation |
| `turn_index` | INTEGER | Turn number within session (0-indexed) |
| `user_email` | TEXT | User who submitted the query |
| `query_text` | TEXT | User's query text for this turn |
| `event_url` | TEXT | Event URL extracted from query |
| `results_json` | JSONB | Full recommendation results |
| `overall_assessment` | TEXT | Sonnet's overall assessment |
| `chosen_ci_name` | TEXT | CI the user selected |
| `chosen_at` | TIMESTAMPTZ | When the user selected |
| `opted_out` | BOOLEAN | True if dismissed without selecting |
| `created_at` | TIMESTAMPTZ | When this turn was recorded |

---

## `jobs`

Background async job tracking.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT (PK) | Job ID for client polling |
| `job_type` | TEXT | `recommend`, `analyze`, `refresh`, `scan`, `rescan`, `maintenance`, `workload_scan` |
| `status` | TEXT | `queued`, `running`, `complete`, `failed` |
| `queue` | TEXT | Redis queue (`scan` or `recommend`) |
| `created_by` | TEXT | Who triggered the job |
| `progress_json` | JSONB | Structured progress data |
| `result_json` | JSONB | Final result payload |
| `error` | TEXT | Error message on failure |
| `created_at` | TIMESTAMPTZ | When queued |
| `started_at` | TIMESTAMPTZ | When execution began |
| `completed_at` | TIMESTAMPTZ | When finished |

---

## `retirement_workflow`

Tracks the retirement lifecycle for catalog items. One row per catalog base name. Created by Alembic migration 012.

| Column | Type | Description |
|---|---|---|
| `catalog_base_name` | TEXT (PK) | Matches `reporting_metrics.catalog_base_name` |
| `status` | TEXT | Derived from highest step: `approved`, `notified`, `started`, `retired` |
| `step_approved_at` | TIMESTAMPTZ | When retirement was approved |
| `step_approved_by` | TEXT | Email of approving curator |
| `approval_reason` | TEXT | Required reason for retirement |
| `approval_snapshot` | JSONB | Frozen metrics at approval time (provisions, cost, touched, closed, score, etc.) |
| `step_notified_at` | TIMESTAMPTZ | When owner was notified (optional step) |
| `step_notified_by` | TEXT | Email of notifying curator |
| `step_started_at` | TIMESTAMPTZ | When Jira ticket was created |
| `step_started_by` | TEXT | Email of admin who started |
| `retirement_target_date` | DATE | Computed target date (approval date + target days) |
| `step_retired_at` | TIMESTAMPTZ | Auto-set when item disappears from Babylon CRDs |
| `replacement_ci` | TEXT | Base name of replacement catalog item (optional) |
| `replacement_name` | TEXT | Display name of replacement (optional) |
| `curator_notes` | TEXT | Free-form curator notes |
| `jira_key` | TEXT | Created Jira ticket key (e.g., GPTEINFRA-17135) |
| `jira_project` | TEXT | Jira project key (default RHDPCD) |
| `created_at` | TIMESTAMPTZ | Row creation time |
| `updated_at` | TIMESTAMPTZ | Last modification time |

---

## `api_keys` (future)

API key management for programmatic access. Schema defined but not yet active.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing row ID |
| `key_hash` | TEXT (UNIQUE) | SHA-256 hash of the API key |
| `name` | TEXT | Human-readable key name |
| `created_by` | TEXT | Admin who created the key |
| `scopes` | TEXT[] | Allowed scopes |
| `created_at` | TIMESTAMPTZ | When created |
| `last_used_at` | TIMESTAMPTZ | Last usage |
| `revoked_at` | TIMESTAMPTZ | When revoked (NULL if active) |
