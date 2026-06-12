# Infrastructure-Aware Catalog Metadata — Design Spec

**Date:** 2026-06-12
**Status:** Design, pending review

## Overview

Extend the RCARS catalog reader to extract infrastructure metadata from AgnosticV Component CRDs during the existing nightly refresh. This enables Publishing House to query RCARS with faceted infrastructure filters — "give me a cluster with OpenShift AI and Pipelines installed" — without requiring vector search against Showroom content.

**Scope: AgnosticD v2 items only.** Identified by `__meta__.deployer.scm_url == https://github.com/agnosticd/agnosticd-v2` (exact match — forks are excluded as they're development items). V1 items (`redhat-cop/agnosticd.git` and forks) use inconsistent field names and conventions — they're not worth indexing for PH express mode. V2 items have a clean, consistent structure with FQCN workload references and standardized config types. Item counts from the dev Babylon environment are illustrative only — production will differ.

The core idea: **catalog everything, surface selectively.** All infra fields are extracted and stored for v2 items. But PH-facing queries only match against a curated workload mapping that translates raw role names (like `ocp4_workload_openshift_ai`) to human-readable product names (like `OpenShift AI`). Unknown workloads are stored but invisible to PH queries until a curator maps them.

No new data sources needed — this is purely an extension of what `extract_catalog_item()` and `CatalogReader.refresh_catalog()` already do with `spec.definition`.

### V2 item breakdown

Counts are from the dev Babylon environment (illustrative — production will differ):

| `config` type | What it is | OCP or RHEL? |
|---|---|---|
| `openshift-workloads` | Deploys workloads onto existing shared OCP clusters. `cloud_provider` always `none`. Workloads in flat `workloads` list | OCP |
| `openshift-cluster` | Provisions a dedicated OCP cluster. `cloud_provider` is `aws` or `openshift_cnv`. Has OCP version, worker/control plane sizing. Workloads in flat `workloads` list | OCP |
| `cloud-vms-base` | Provisions RHEL/cloud VMs. OS image in `bastion_instance_image` / `default_instance_image` (e.g., `rhel-9.6`, `rhel-10.0`). VM specs in `instances` list. Workloads in `software_workloads` / `post_software_workloads` dicts keyed by host group — **not** the flat `workloads` list | RHEL |
| `namespace` | Deploys into an existing namespace on a shared cluster. `cloud_provider` always `none`. Workloads in flat `workloads` list | OCP |

### Workload formats

**OCP items** (`openshift-workloads`, `openshift-cluster`, `namespace`) use a flat `workloads` list with Ansible FQCN format:
```yaml
workloads:
  - agnosticd.core_workloads.ocp4_workload_openshift_ai
  - agnosticd.core_workloads.ocp4_workload_pipelines
```

**RHEL/VM items** (`cloud-vms-base`) use dictionaries keyed by host group across multiple fields:
```yaml
software_workloads:
  bastions:
    - agnosticd.cloud_vm_workloads.control_user
    - bastion
  nodes:
    - agnosticd.cloud_vm_workloads.control_user
post_software_workloads:
  bastions:
    - infra.aap_configuration.dispatch
    - rhpds.ripu.cockpit
```

The role name (last segment of the FQCN) is the meaningful identifier for mapping, regardless of which config type or workload field it came from.

### Collection repos

All `agnosticd/*` repos are public (`github.com/agnosticd/`). Most `rhpds.*` repos are private. The scanner must clone from these remotes — not from local copies.

| Collection | Remote | Public? | Purpose |
|---|---|---|---|
| `agnosticd.core_workloads` | `github.com/agnosticd/core_workloads` | Yes | OCP operators, platform services (Pipelines, GitOps, RHACS, etc.) |
| `agnosticd.ai_workloads` | `github.com/agnosticd/ai_workloads` | Yes | AI/ML (OpenShift AI, NVIDIA GPU, OLS) |
| `agnosticd.cloud_vm_workloads` | `github.com/agnosticd/cloud_vm_workloads` | Yes | VM provisioning helpers (control_user, asset_injector, etc.) |
| `agnosticd.namespaced_workloads` | `github.com/agnosticd/namespaced_workloads` | Yes | Per-tenant resources (namespace, Gitea user, etc.) |
| `agnosticd.cnv_workloads` | `github.com/agnosticd/cnv_workloads` | Yes | CNV VM instances |
| `agnosticd.showroom` | `github.com/agnosticd/showroom` | Yes | Showroom deployment (not infra-relevant) |
| `rhpds.*` | `github.com/rhpds/*` | **Mostly no** | Lab-specific workloads (ADS, LiteLLM, AAP, RIPU, etc.). Only `rhpds/mcp_workloads` confirmed public. Flag private repos at scan time — we'll address access as needed |

---

## 1. Data Layer

### 1a. New columns on `catalog_items`

Add structured infrastructure metadata directly to the existing `catalog_items` table. These fields are specific to AgnosticD v2 items — v1 items will have NULLs for all of them.

```sql
ALTER TABLE catalog_items
    ADD COLUMN is_agd_v2 BOOLEAN DEFAULT FALSE,    -- identified by __meta__.deployer.scm_url
    ADD COLUMN agd_config TEXT,                    -- 'openshift-workloads', 'openshift-cluster', 'namespace', 'cloud-vms-base'
    ADD COLUMN cloud_provider TEXT,                 -- 'aws', 'openshift_cnv', 'none'
    ADD COLUMN ocp_version TEXT,                    -- from host_ocp4_installer_version (OCP cluster items)
    ADD COLUMN os_image TEXT,                       -- RHEL/OS image name, e.g. 'rhel-9.6', 'rhel-10.0' (VM items)
    ADD COLUMN worker_instance_count TEXT,          -- TEXT: can be Jinja2 template
    ADD COLUMN control_plane_instance_count TEXT,   -- TEXT: can be int or template ('1' for SNO, '3' for multi)
    ADD COLUMN instances_json JSONB;               -- VM instance specs (cloud-vms-base items): cores, memory, image, count
```

**Field rationale:**

| Field | In/Out | Reason |
|---|---|---|
| `is_agd_v2` | IN | Gate for infra queries — only v2 items have reliable infra data |
| `agd_config` | IN | Replaces v1 `env_type` (which is always `{{ config }}` in v2). Tells PH what kind of environment this is. Covers both OCP (`openshift-workloads`, `openshift-cluster`) and RHEL (`cloud-vms-base`) |
| `cloud_provider` | IN | Relevant for `openshift-cluster` (aws/openshift_cnv) and `cloud-vms-base`. Always `none` for `openshift-workloads` |
| `ocp_version` | IN | From `host_ocp4_installer_version`. Only meaningful for `openshift-cluster` configs |
| `os_image` | IN | Primary OS image — **only set for `cloud-vms-base` items** where the CI's purpose IS a RHEL environment. Not extracted for OCP items even though they may have a bastion with a RHEL image. Extracted from `bastion_instance_image` or `default_instance_image`. Captures RHEL version (e.g., `rhel-9.6`, `rhel-10.0`). Critical for PH — "give me a RHEL 10 environment" must return actual RHEL environments, not OCP clusters that happen to have a RHEL bastion |
| `worker_instance_count` | IN | Cluster/VM sizing. Can be Jinja2 template |
| `control_plane_instance_count` | IN | Distinguishes SNO (1) from multi-node (3) for `openshift-cluster` items |
| `instances_json` | IN | Full VM instance specs for `cloud-vms-base` items — cores, memory, image, count per VM. Stored as JSONB for Browse display; not used for faceted search |
| `env_type` | **OUT** | Always `{{ config }}` in v2 — useless. V1 concept |
| `software_to_deploy` | **OUT** | V1 concept. Not present in v2 |
| `worker_instance_type` | **OUT** | Inconsistent formats (AWS instance types vs vCPU counts for CNV). Not useful for PH queries |

**Why TEXT for counts:** Some CRDs use Jinja2 expressions for worker counts (e.g., `{{ [(num_users | int / 3.0) | round(0, 'ceil') | int, 3] | max }}`). Storing as TEXT preserves the original value for Browse/Admin display. Integer parsing can happen at query time where needed.

**RHEL coverage:** `cloud-vms-base` items provision RHEL VMs with specific OS images (`rhel-9.6`, `rhel-10.0`, etc.) and define their infrastructure via the `instances` list rather than `workloads`. The `os_image` column surfaces RHEL version for PH queries. The `instances_json` column stores the full VM topology (how many VMs, what specs) for Browse display. VM-based items also have their own workload fields — `software_workloads`, `pre_software_workloads`, `post_software_final_workloads` — which are dictionaries keyed by host group, not flat lists. See section 2b for extraction details.

### 1b. New table: `catalog_item_workloads`

Workloads are a many-to-many relationship (each CI has 0–N workloads). A junction table is cleaner than a JSONB array for faceted queries.

```sql
CREATE TABLE IF NOT EXISTS catalog_item_workloads (
    id SERIAL PRIMARY KEY,
    ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    workload_fqcn TEXT NOT NULL,       -- full FQCN, e.g. 'agnosticd.core_workloads.ocp4_workload_openshift_ai'
    workload_role TEXT NOT NULL,       -- last segment only, e.g. 'ocp4_workload_openshift_ai'
    workload_collection TEXT,          -- namespace.collection, e.g. 'agnosticd.core_workloads' (NULL for bare roles)
    UNIQUE(ci_name, workload_fqcn)
);

CREATE INDEX IF NOT EXISTS idx_ciw_ci_name ON catalog_item_workloads(ci_name);
CREATE INDEX IF NOT EXISTS idx_ciw_workload_role ON catalog_item_workloads(workload_role);
CREATE INDEX IF NOT EXISTS idx_ciw_workload_collection ON catalog_item_workloads(workload_collection);
```

Stores both the full FQCN and the extracted role name. The mapping table (1c) keys on `workload_role` — the role name is what identifies the operator/product regardless of which collection repo it lives in. The `workload_collection` column tracks provenance (which repo owns this workload) for the workload scanning feature (section 4a).

**Why a table instead of TEXT[]:** Faceted search needs `JOIN ... WHERE workload_role IN (...)` with AND semantics (CI must have ALL requested workloads). A junction table makes this a straightforward self-join. A TEXT[] column would require `@>` array containment which is less composable with other filters and harder to index for partial matches.

### 1c. New tables: `workload_mapping` + `workload_aliases`

The curated mapping from raw workload role names to human-readable product/operator names. This is the gate between "cataloged" and "surfaced to PH."

```sql
CREATE TABLE IF NOT EXISTS workload_mapping (
    id SERIAL PRIMARY KEY,
    workload_role TEXT NOT NULL UNIQUE,   -- e.g. 'ocp4_workload_openshift_ai'
    product_name TEXT NOT NULL,           -- canonical name, e.g. 'OpenShift AI'
    description TEXT,                     -- what the workload actually does (from code analysis, not README)
    category TEXT,                        -- optional grouping: 'ai_ml', 'security', 'networking', etc.
    source_collection TEXT,               -- which agDv2 collection repo, e.g. 'agnosticd.core_workloads'
    verified BOOLEAN DEFAULT FALSE,       -- TRUE = confirmed by reading the actual Ansible/GitOps code
    added_by TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_wm_product_name ON workload_mapping(product_name);

CREATE TABLE IF NOT EXISTS workload_aliases (
    id SERIAL PRIMARY KEY,
    product_name TEXT NOT NULL,           -- canonical product name (FK to workload_mapping.product_name conceptually)
    alias TEXT NOT NULL UNIQUE,           -- alternate name: acronym, abbreviation, common shorthand
    added_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wa_product_name ON workload_aliases(product_name);
```

**Why aliases?** People use many names for the same product — "OpenShift AI" vs "RHOAI" vs "Red Hat OpenShift AI", "Advanced Cluster Security" vs "RHACS" vs "ACS" vs "StackRox". PH queries need to match on any of these. The `workload_aliases` table maps alternate names back to the canonical `product_name`. When PH sends `workloads=RHOAI`, the faceted search resolves `RHOAI` → `OpenShift AI` before matching against `workload_mapping`. This is critical for a comprehensive and reliable query interface.

The `description` field stores what the workload actually does — sourced by reading the actual Ansible code, defaults, and task files (see section 4a). `meta/main.yml` descriptions and READMEs are **not trusted** as authoritative — only the code itself. The `verified` flag distinguishes "we read the code and confirmed this" from "name-based guess." Only verified mappings should be trusted by PH for express mode.

**Why a DB table instead of a config file:** The mapping needs to be editable by curators through the Browse UI without requiring a code deploy. A YAML seed file provides the initial data; the table is the runtime truth.

### 1d. New table: `catalog_item_acl_groups`

ACL groups from `__meta__.access_control.allow_groups`. Stored separately for future ACL-aware recommendations (BACKLOG item), but also useful for PH to understand ordering restrictions.

```sql
CREATE TABLE IF NOT EXISTS catalog_item_acl_groups (
    id SERIAL PRIMARY KEY,
    ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    group_name TEXT NOT NULL,
    UNIQUE(ci_name, group_name)
);

CREATE INDEX IF NOT EXISTS idx_ciag_ci_name ON catalog_item_acl_groups(ci_name);
CREATE INDEX IF NOT EXISTS idx_ciag_group_name ON catalog_item_acl_groups(group_name);
```

### 1e. Alembic migration

Create `alembic/versions/002_infrastructure_metadata.py`:

```python
"""Add infrastructure metadata to catalog items (AgnosticD v2 only).

Revision ID: 002
Revises: 001
Create Date: 2026-06-XX
"""

revision = "002"
down_revision = "001"

def upgrade():
    # New columns on catalog_items (v2 infra fields)
    op.execute("""
        ALTER TABLE catalog_items
            ADD COLUMN IF NOT EXISTS is_agd_v2 BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS agd_config TEXT,
            ADD COLUMN IF NOT EXISTS cloud_provider TEXT,
            ADD COLUMN IF NOT EXISTS ocp_version TEXT,
            ADD COLUMN IF NOT EXISTS os_image TEXT,
            ADD COLUMN IF NOT EXISTS worker_instance_count TEXT,
            ADD COLUMN IF NOT EXISTS control_plane_instance_count TEXT,
            ADD COLUMN IF NOT EXISTS instances_json JSONB;
    """)

    # Workload junction table (FQCN + extracted role)
    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog_item_workloads (
            id SERIAL PRIMARY KEY,
            ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
            workload_fqcn TEXT NOT NULL,
            workload_role TEXT NOT NULL,
            workload_collection TEXT,
            UNIQUE(ci_name, workload_fqcn)
        );
        CREATE INDEX IF NOT EXISTS idx_ciw_ci_name ON catalog_item_workloads(ci_name);
        CREATE INDEX IF NOT EXISTS idx_ciw_workload_role ON catalog_item_workloads(workload_role);
        CREATE INDEX IF NOT EXISTS idx_ciw_workload_collection ON catalog_item_workloads(workload_collection);
    """)

    # Curated workload mapping (with verification tracking)
    op.execute("""
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
        CREATE INDEX IF NOT EXISTS idx_wm_product_name ON workload_mapping(product_name);
    """)

    # Product name aliases (acronyms, abbreviations)
    op.execute("""
        CREATE TABLE IF NOT EXISTS workload_aliases (
            id SERIAL PRIMARY KEY,
            product_name TEXT NOT NULL,
            alias TEXT NOT NULL UNIQUE,
            added_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_wa_product_name ON workload_aliases(product_name);
    """)

    # ACL groups
    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog_item_acl_groups (
            id SERIAL PRIMARY KEY,
            ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
            group_name TEXT NOT NULL,
            UNIQUE(ci_name, group_name)
        );
        CREATE INDEX IF NOT EXISTS idx_ciag_ci_name ON catalog_item_acl_groups(ci_name);
        CREATE INDEX IF NOT EXISTS idx_ciag_group_name ON catalog_item_acl_groups(group_name);
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS catalog_item_acl_groups CASCADE")
    op.execute("DROP TABLE IF EXISTS workload_aliases CASCADE")
    op.execute("DROP TABLE IF EXISTS workload_mapping CASCADE")
    op.execute("DROP TABLE IF EXISTS catalog_item_workloads CASCADE")
    op.execute("""
        ALTER TABLE catalog_items
            DROP COLUMN IF EXISTS is_agd_v2,
            DROP COLUMN IF EXISTS agd_config,
            DROP COLUMN IF EXISTS cloud_provider,
            DROP COLUMN IF EXISTS ocp_version,
            DROP COLUMN IF EXISTS os_image,
            DROP COLUMN IF EXISTS worker_instance_count,
            DROP COLUMN IF EXISTS control_plane_instance_count,
            DROP COLUMN IF EXISTS instances_json;
    """)
```

Also update `SCHEMA_SQL` in `database.py` to include the new tables and columns (keeps `create_schema()` and `drop_schema()` working for fresh installs).

---

## 2. Catalog Reader Extraction

### 2a. V2 detection and field constants

Add a V2 detection function and the infra-specific field list in `catalog.py`:

```python
AGD_V2_SCM_URL = "https://github.com/agnosticd/agnosticd-v2"

V2_INFRA_FIELDS = [
    "config",                       # → agd_config column
    "cloud_provider",
    "host_ocp4_installer_version",  # → ocp_version column
    "worker_instance_count",
    "control_plane_instance_count",
]

ACL_PATH = ("__meta__", "access_control", "allow_groups")


def is_agnosticd_v2(component_crd: dict[str, Any]) -> bool:
    """Check if a component uses the canonical AgnosticD v2 deployer.

    Exact match only — forks are excluded (development items, not relevant
    for PH express mode).
    """
    definition = component_crd.get("spec", {}).get("definition", {}) or {}
    scm_url = definition.get("__meta__", {}).get("deployer", {}).get("scm_url", "")
    return scm_url == AGD_V2_SCM_URL
```

### 2b. New function: `extract_infrastructure_metadata()`

Only called for v2 items. Returns None for non-v2 items. Handles both OCP items (flat `workloads` list) and RHEL/VM items (dict-based workload fields + `instances`).

```python
# Workload fields for cloud-vms-base items — dicts keyed by host group
VM_WORKLOAD_FIELDS = [
    "software_workloads",
    "pre_software_workloads",
    "post_software_workloads",
    "post_software_final_workloads",
]


def extract_infrastructure_metadata(
    component_crd: dict[str, Any],
) -> dict[str, Any] | None:
    """Extract infrastructure metadata from an AgnosticD v2 component CRD.

    Returns None if the component is not AgnosticD v2.
    For v2 items, returns a dict with:
    - infra fields (agd_config, cloud_provider, os_image, etc.)
    - workloads — list of dicts: [{fqcn, role, collection}, ...]
    - acl_groups — list of group name strings
    - instances_json — VM instance specs for cloud-vms-base items
    """
    if not is_agnosticd_v2(component_crd):
        return None

    definition = component_crd.get("spec", {}).get("definition", {}) or {}

    result = {"is_agd_v2": True}

    # Flat infra fields with column name mapping
    field_mapping = {
        "config": "agd_config",
        "cloud_provider": "cloud_provider",
        "host_ocp4_installer_version": "ocp_version",
        "worker_instance_count": "worker_instance_count",
        "control_plane_instance_count": "control_plane_instance_count",
    }
    for crd_field, col_name in field_mapping.items():
        value = definition.get(crd_field)
        if value is not None:
            result[col_name] = str(value) if not isinstance(value, str) else value

    config = definition.get("config", "")

    # OS image — for cloud-vms-base items, extract RHEL version
    if config == "cloud-vms-base":
        os_image = (
            definition.get("bastion_instance_image")
            or definition.get("default_instance_image")
        )
        if os_image and isinstance(os_image, str):
            result["os_image"] = os_image

        # VM instance specs — store full topology for display
        instances = definition.get("instances")
        if isinstance(instances, list):
            result["instances_json"] = [
                {k: v for k, v in inst.items()
                 if k in ("name", "cores", "memory", "image", "image_size", "count")}
                for inst in instances if isinstance(inst, dict)
            ]

    # Workloads — different extraction depending on config type
    workloads = []
    seen_fqcns = set()

    if config == "cloud-vms-base":
        # RHEL/VM items: workloads spread across multiple dict fields
        for field in VM_WORKLOAD_FIELDS:
            raw = definition.get(field)
            if not isinstance(raw, dict):
                continue
            for host_group, wl_list in raw.items():
                if not isinstance(wl_list, list):
                    continue
                for entry in wl_list:
                    if isinstance(entry, str) and entry not in seen_fqcns:
                        seen_fqcns.add(entry)
                        fqcn, role, collection = parse_workload_fqcn(entry)
                        workloads.append({
                            "fqcn": fqcn, "role": role, "collection": collection,
                        })
        # Also check openshift_workload_deployer_workloads (hybrid VM+OCP items)
        owd = definition.get("openshift_workload_deployer_workloads")
        if isinstance(owd, list):
            for entry in owd:
                name = entry.get("name") if isinstance(entry, dict) else None
                if name and isinstance(name, str) and name not in seen_fqcns:
                    seen_fqcns.add(name)
                    fqcn, role, collection = parse_workload_fqcn(name)
                    workloads.append({
                        "fqcn": fqcn, "role": role, "collection": collection,
                    })
    else:
        # OCP items: flat workloads list
        raw = definition.get("workloads")
        if isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, str) and entry not in seen_fqcns:
                    seen_fqcns.add(entry)
                    fqcn, role, collection = parse_workload_fqcn(entry)
                    workloads.append({
                        "fqcn": fqcn, "role": role, "collection": collection,
                    })

    result["workloads"] = workloads

    # ACL groups
    meta = definition.get("__meta__", {})
    access_control = meta.get("access_control", {}) or {}
    acl_groups = access_control.get("allow_groups", []) or []
    result["acl_groups"] = [g for g in acl_groups if isinstance(g, str)]

    return result


def parse_workload_fqcn(fqcn: str) -> tuple[str, str, str | None]:
    """Parse an Ansible FQCN workload reference into (fqcn, role, collection).

    'agnosticd.core_workloads.ocp4_workload_openshift_ai'
        → ('agnosticd.core_workloads.ocp4_workload_openshift_ai',
           'ocp4_workload_openshift_ai', 'agnosticd.core_workloads')
    'ocp4_workload_showroom'
        → ('ocp4_workload_showroom', 'ocp4_workload_showroom', None)
    """
    parts = fqcn.rsplit(".", 1)
    if len(parts) == 2 and "." in parts[0]:
        # namespace.collection.role → 3+ segments
        return fqcn, parts[1], parts[0]
    elif len(parts) == 2:
        # collection.role → 2 segments (rare, treat collection as None)
        return fqcn, parts[1], parts[0]
    else:
        # bare role name
        return fqcn, fqcn, None
```

### 2c. Integration into `CatalogReader.refresh_catalog()`

In the existing loop where each CRD is processed (after `extract_showroom_url()`), call `extract_infrastructure_metadata()` for v2 items only:

```python
# Inside refresh_catalog(), after extract_showroom_url():
if component:
    url, ref = extract_showroom_url(component)
    item["showroom_url"] = url
    item["showroom_ref"] = ref

    # NEW: Extract infra metadata (v2 items only)
    infra = extract_infrastructure_metadata(component)
    if infra:
        item["is_agd_v2"] = True
        item["agd_config"] = infra.get("agd_config")
        item["cloud_provider"] = infra.get("cloud_provider")
        item["ocp_version"] = infra.get("ocp_version")
        item["os_image"] = infra.get("os_image")
        item["worker_instance_count"] = infra.get("worker_instance_count")
        item["control_plane_instance_count"] = infra.get("control_plane_instance_count")
        item["instances_json"] = infra.get("instances_json")
        item["_workloads"] = infra.get("workloads", [])
        item["_acl_groups"] = infra.get("acl_groups", [])
```

The `_workloads` and `_acl_groups` keys use underscore prefix to signal that `upsert_catalog_item()` should not try to write them to the `catalog_items` table — they go to their own tables. Non-v2 items get no infra fields (all NULLs).
```

---

## 3. Database Layer Changes

### 3a. Update `upsert_catalog_item()`

Add the new infra columns to the `fields` list in `Database.upsert_catalog_item()`:

```python
fields = [
    "ci_name", "display_name", "category", "product", "product_family",
    "primary_bu", "secondary_bu", "stage", "catalog_namespace",
    "keywords", "description", "icon_url", "owners_json",
    "showroom_url", "showroom_ref", "content_path",
    "last_crd_update", "is_prod", "is_published",
    "published_ci_name", "base_ci_name",
    # NEW v2 infra columns
    "is_agd_v2", "agd_config", "cloud_provider", "ocp_version",
    "os_image", "worker_instance_count", "control_plane_instance_count",
    "instances_json",
]
```

### 3b. New methods for workload and ACL management

```python
def sync_workloads(self, ci_name: str, workloads: list[dict]) -> None:
    """Replace all workloads for a CI with the given list.

    Each workload dict has: fqcn (str), role (str), collection (str|None).
    """
    with self._pool.connection() as conn:
        conn.execute(
            "DELETE FROM catalog_item_workloads WHERE ci_name = %s", (ci_name,)
        )
        for w in workloads:
            conn.execute(
                "INSERT INTO catalog_item_workloads (ci_name, workload_fqcn, workload_role, workload_collection) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (ci_name, w["fqcn"], w["role"], w.get("collection")),
            )
        conn.commit()

def sync_acl_groups(self, ci_name: str, groups: list[str]) -> None:
    """Replace all ACL groups for a CI with the given list."""
    with self._pool.connection() as conn:
        conn.execute(
            "DELETE FROM catalog_item_acl_groups WHERE ci_name = %s", (ci_name,)
        )
        for g in groups:
            conn.execute(
                "INSERT INTO catalog_item_acl_groups (ci_name, group_name) "
                "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (ci_name, g),
            )
        conn.commit()

def get_workloads(self, ci_name: str) -> list[dict]:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT workload_fqcn, workload_role, workload_collection "
            "FROM catalog_item_workloads "
            "WHERE ci_name = %s ORDER BY workload_role",
            (ci_name,),
        )
        return cur.fetchall()

def get_acl_groups(self, ci_name: str) -> list[str]:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT group_name FROM catalog_item_acl_groups "
            "WHERE ci_name = %s ORDER BY group_name",
            (ci_name,),
        )
        return [row["group_name"] for row in cur.fetchall()]
```

### 3c. Faceted search method

The key new query method for PH integration:

```python
def search_by_infrastructure(
    self,
    workloads: list[str] | None = None,
    agd_config: str | None = None,
    cloud_provider: str | None = None,
    ocp_version: str | None = None,
    os_image: str | None = None,
    stage: str | None = None,
    prod_only: bool = True,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Faceted search for CIs by infrastructure characteristics.

    Only searches AgnosticD v2 items (is_agd_v2 = TRUE).
    workloads: list of product names or aliases from workload_mapping/workload_aliases.
    All listed workloads must be present (AND semantics).
    Only curated (mapped) workloads are matched.
    Aliases are resolved before matching (e.g. 'RHOAI' → 'OpenShift AI').
    """
    conditions = ["ci.is_agd_v2 = TRUE"]
    params: dict[str, Any] = {}
    joins = []

    if prod_only:
        conditions.append("ci.is_prod = TRUE")
    if stage:
        conditions.append("ci.stage = %(stage)s")
        params["stage"] = stage
    if agd_config:
        conditions.append("ci.agd_config = %(agd_config)s")
        params["agd_config"] = agd_config
    if cloud_provider:
        conditions.append("ci.cloud_provider = %(cloud_provider)s")
        params["cloud_provider"] = cloud_provider
    if ocp_version:
        conditions.append("ci.ocp_version LIKE %(ocp_version)s")
        params["ocp_version"] = f"{ocp_version}%"
    if os_image:
        conditions.append("ci.os_image LIKE %(os_image)s")
        params["os_image"] = f"{os_image}%"

    if workloads:
        # Resolve aliases before matching
        workloads = self._resolve_workload_aliases(workloads)
        # AND semantics: CI must have ALL requested workloads
        # Join through workload_mapping to match on product_name (curated)
        for i, wl in enumerate(workloads):
            alias_w = f"w{i}"
            alias_m = f"m{i}"
            joins.append(
                f"JOIN catalog_item_workloads {alias_w} "
                f"ON {alias_w}.ci_name = ci.ci_name "
                f"JOIN workload_mapping {alias_m} "
                f"ON {alias_m}.workload_role = {alias_w}.workload_role "
                f"AND {alias_m}.product_name = %({alias_m}_name)s"
            )
            params[f"{alias_m}_name"] = wl

    join_sql = "\n".join(joins)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT DISTINCT ci.*, sa.summary, sa.content_type,
               sa.estimated_duration_min, sa.difficulty
        FROM catalog_items ci
        LEFT JOIN showroom_analysis sa ON sa.ci_name = ci.ci_name
        {join_sql}
        {where}
        ORDER BY ci.display_name
        LIMIT %(limit)s
    """
    params["limit"] = limit

    with self._pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
```

### 3d. Workload mapping CRUD

```python
def upsert_workload_mapping(
    self, workload_role: str, product_name: str,
    category: str | None = None, added_by: str | None = None,
) -> None:
    with self._pool.connection() as conn:
        conn.execute(
            "INSERT INTO workload_mapping (workload_role, product_name, category, added_by) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (workload_role) DO UPDATE SET "
            "product_name = EXCLUDED.product_name, category = EXCLUDED.category",
            (workload_role, product_name, category, added_by),
        )
        conn.commit()

def delete_workload_mapping(self, workload_role: str) -> None:
    with self._pool.connection() as conn:
        conn.execute(
            "DELETE FROM workload_mapping WHERE workload_role = %s",
            (workload_role,),
        )
        conn.commit()

def list_workload_mappings(self) -> list[dict]:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT * FROM workload_mapping ORDER BY product_name"
        )
        return cur.fetchall()

def get_unmapped_workloads(self) -> list[dict]:
    """Return workload roles that appear in catalog but have no mapping."""
    with self._pool.connection() as conn:
        cur = conn.execute("""
            SELECT ciw.workload_role, COUNT(DISTINCT ciw.ci_name) AS ci_count
            FROM catalog_item_workloads ciw
            LEFT JOIN workload_mapping wm ON wm.workload_role = ciw.workload_role
            WHERE wm.id IS NULL
            ORDER BY ci_count DESC
        """)
        return cur.fetchall()
```

### 3e. Infrastructure summary stats

Extend `get_status_summary()` or add a new method:

```python
def get_infra_stats(self) -> dict:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM catalog_items WHERE is_agd_v2 = TRUE"
        )
        v2_items = cur.fetchone()["count"]
        cur = conn.execute(
            "SELECT COUNT(DISTINCT ci_name) FROM catalog_item_workloads"
        )
        with_workloads = cur.fetchone()["count"]
        cur = conn.execute(
            "SELECT COUNT(*) FROM workload_mapping"
        )
        mapped_count = cur.fetchone()["count"]
        cur = conn.execute(
            "SELECT COUNT(*) FROM workload_mapping WHERE verified = TRUE"
        )
        verified_count = cur.fetchone()["count"]
        cur = conn.execute("""
            SELECT COUNT(DISTINCT ciw.workload_role)
            FROM catalog_item_workloads ciw
            LEFT JOIN workload_mapping wm ON wm.workload_role = ciw.workload_role
            WHERE wm.id IS NULL
        """)
        unmapped_count = cur.fetchone()["count"]
    return {
        "v2_items": v2_items,
        "with_workloads": with_workloads,
        "mapped_workloads": mapped_count,
        "verified_workloads": verified_count,
        "unmapped_workloads": unmapped_count,
    }
```

---

## 4. Curated Workload Mapping

### 4a. Workload repo scanning (one-time + infrequent refresh)

The point of the mapping is to know **for certain** what each workload actually installs. The role name `ocp4_workload_openshift_ai` *looks like* it sets up OpenShift AI, but we need to verify by reading the actual Ansible code. This is the "curated, not guessing" constraint.

**Source repos** — all under `github.com/agnosticd/` (public):

| Collection | Remote |
|---|---|
| `core_workloads` | `github.com/agnosticd/core_workloads` |
| `ai_workloads` | `github.com/agnosticd/ai_workloads` |
| `cloud_vm_workloads` | `github.com/agnosticd/cloud_vm_workloads` |
| `namespaced_workloads` | `github.com/agnosticd/namespaced_workloads` |
| `cnv_workloads` | `github.com/agnosticd/cnv_workloads` |

The scanner must clone from these remotes — never from local copies. For `rhpds.*` collections (mostly private), flag the repo as inaccessible at scan time and mark those mappings as unverified. We'll address access to private repos as they come up.

**What the scanner reads (code, not descriptions):**

READMEs, `meta/main.yml` descriptions, and `galaxy_info.description` are **not reliable** — people are lazy and don't maintain them. The only thing that matters is the actual code. For each role, the scanner should read:

1. `defaults/main.yml` (or `.yaml`) — what variables the role defines, with any comments explaining them. This is where you find operator channel names, namespace names, and configuration knobs that reveal what the role actually deploys.
2. `tasks/main.yml` — the actual task flow. Look for `k8s` / `kubernetes.core.k8s` resource creation (Subscriptions, CRDs, Deployments), `ansible.builtin.include_role` calls, operator group/subscription names.
3. `templates/` — Subscription manifests, CRD templates that name the actual operator being installed.

From this, an LLM analysis pass (similar to how we analyze Showroom content) can determine: what operator/product does this role install, what namespace does it use, what CRDs does it create. This produces a verified `product_name` and `description` for the mapping.

**Scan frequency and change detection:**

Workload repo scanning follows the same pattern as Showroom stale detection:

1. `git ls-remote` each collection repo to get HEAD SHA
2. Compare against stored SHA from last scan (store in a `workload_scan_status` table or similar)
3. Only clone + analyze repos where HEAD has changed
4. If a repo changed, scan only the roles whose files differ (or all roles in that repo if simpler)

Since the change detection makes scans cheap when nothing changed, this can run **daily** as part of the nightly maintenance pipeline — same logic as "if nothing changed, skip it." The scan interval should be configurable via `RCARS_WORKLOAD_SCAN_ENABLED` (bool, default `true`) and `RCARS_WORKLOAD_SCAN_INTERVAL_DAYS` (int, default `1`).

**Triggers:**

- **Scheduled:** Runs as a step in the nightly maintenance pipeline (after catalog refresh, before stale check). Skipped if no collection repos have new commits.
- **Admin UI button:** "Rescan Workload Repos" button on the Admin page (alongside existing "Refresh Catalog" and "Check Stale" buttons). Triggers the same scan via API.
- **CLI:**
```
rcars workload scan [--collection COLLECTION] [--role ROLE]
```

Clones the specified collection repo (or all), reads the role code, runs an LLM analysis pass, and upserts into `workload_mapping` with `verified = true`. Without arguments, scans all public agDv2 collection repos. Private repos that fail to clone are logged and skipped.

### 4b. Seed file format

A YAML file at `src/api/rcars/data/workload_mapping.yaml` seeds the initial mapping. Descriptions will be replaced with LLM-verified descriptions from code analysis (section 4a). These initial descriptions are placeholders from `meta/main.yml` — treat as unverified until the scanner runs.

```yaml
# Curated mapping: AgnosticD v2 workload roles → human-readable product names.
# Descriptions verified by reading the actual Ansible role code.
# Only verified+mapped workloads are queryable by Publishing House.
# Run `rcars sync-workload-mapping` to load changes into the database.

mappings:
  # === agnosticd.core_workloads (verified from repo meta) ===

  - role: ocp4_workload_openshift_gitops
    product: OpenShift GitOps
    description: Set up OpenShift GitOps (Operator)
    category: cicd
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_gitops_bootstrap
    product: OpenShift GitOps Bootstrap
    description: Bootstrap OpenShift resources from GitOps repositories
    category: cicd
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_pipelines
    product: OpenShift Pipelines
    description: Set up OpenShift Pipelines (Operator)
    category: cicd
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_rhacs
    product: Advanced Cluster Security
    description: Set up ACS on OpenShift 4
    category: security
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_cert_manager
    product: cert-manager Operator
    description: Requests and installs Let's Encrypt or ZeroSSL certificates using the Red Hat Cert Manager operator
    category: platform
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_openshift_virtualization
    product: OpenShift Virtualization
    description: Deploys OpenShift Virtualization on an OCP4 cluster
    category: virtualization
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_mtv
    product: Migration Toolkit for Virtualization
    description: Deploys Migration Toolkit for Virtualization on an OCP4 cluster
    category: virtualization
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_openshift_data_foundation
    product: OpenShift Data Foundation
    description: Deploys OpenShift Data Foundation (ODF)
    category: storage
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_external_odf
    product: OpenShift Data Foundation (External)
    description: Configure ODF after being installed
    category: storage
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_serverless
    product: OpenShift Serverless
    description: Set up OpenShift Serverless (KNative Serving, KNative Eventing)
    category: runtime
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_servicemesh2
    product: OpenShift Service Mesh 2
    description: Set up Red Hat OpenShift Service Mesh (OSSM)
    category: networking
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_servicemesh3
    product: OpenShift Service Mesh 3
    description: Set up Red Hat OpenShift Service Mesh 3 on OpenShift
    category: networking
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_rhacm
    product: Advanced Cluster Management
    description: Set up ACM on OpenShift 4
    category: management
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_devspaces
    product: OpenShift Dev Spaces
    description: Set up Red Hat OpenShift Dev Spaces
    category: developer_tools
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_web_terminal
    product: Web Terminal
    description: Set up Web Terminal on OpenShift Container Platform
    category: developer_tools
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_gitea_operator
    product: Gitea
    description: Deploys the Gitea Operator into a cluster
    category: developer_tools
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_gitlab
    product: GitLab
    description: Deploys GitLab on OpenShift
    category: developer_tools
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_quay_operator
    product: Quay
    description: Deploy the Quay Operator into OpenShift
    category: registry
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_metallb
    product: MetalLB
    description: Deploys MetalLB Operator to an OCP4 cluster
    category: networking
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_nfd
    product: Node Feature Discovery
    description: Set up OpenShift NFD Operator
    category: platform
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_nmstate
    product: NMState
    description: Deploys Kubernetes NMState Operator to an OCP4 cluster
    category: networking
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_minio
    product: MinIO
    description: Set up MinIO (S3 Storage) on an OpenShift Cluster
    category: storage
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_kiali
    product: Kiali
    description: Set up Red Hat Kiali Operator on OpenShift
    category: networking
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_builds
    product: OpenShift Builds
    description: Set up OpenShift Builds (Operator)
    category: cicd
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_amq_streams
    product: AMQ Streams
    description: Set up AMQ Streams on OpenShift
    category: messaging
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_ansible_automation_platform
    product: Ansible Automation Platform
    description: Set up AAP on OpenShift
    category: automation
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_machinesets
    product: Additional MachineSets
    description: Set up additional MachineSets for OpenShift
    category: platform
    collection: agnosticd.core_workloads
    verified: true

  # === agnosticd.ai_workloads (verified from repo meta) ===

  - role: ocp4_workload_openshift_ai
    product: OpenShift AI
    description: Set up OpenShift AI on an OpenShift Cluster
    category: ai_ml
    collection: agnosticd.ai_workloads
    verified: true

  - role: ocp4_workload_nvidia_gpu_operator
    product: NVIDIA GPU Operator
    description: Set up NVIDIA GPU on an OpenShift Cluster
    category: ai_ml
    collection: agnosticd.ai_workloads
    verified: true

  - role: ocp4_workload_ols
    product: OpenShift Lightspeed
    description: Set up OpenShift Lightspeed
    category: ai_ml
    collection: agnosticd.ai_workloads
    verified: true

  - role: ocp4_workload_toolhive
    product: ToolHive
    description: Deploy ToolHive MCP server manager
    category: ai_ml
    collection: agnosticd.ai_workloads
    verified: true

  # === Infrastructure/auth roles (not user-facing products, but infra-relevant) ===

  - role: ocp4_workload_authentication_htpasswd
    product: HTPasswd Authentication
    description: Set up htpasswd Authentication for OpenShift
    category: auth
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_authentication_keycloak
    product: Keycloak Authentication
    description: Installs Keycloak Operator on OpenShift and configures it for authentication
    category: auth
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_authentication_rhsso
    product: Red Hat SSO Authentication
    description: Set up Authentication on OpenShift using Red Hat SSO (KeyCloak)
    category: auth
    collection: agnosticd.core_workloads
    verified: true

  - role: ocp4_workload_authorino
    product: Authorino
    description: Deploy Authorino authorization service
    category: auth
    collection: agnosticd.core_workloads
    verified: true

  # === Workloads to EXCLUDE from PH surface (infra plumbing, not products) ===
  # These are cataloged but not mapped — they're infrastructure setup, not
  # user-facing products that PH would search for:
  #   - ocp4_workload_showroom (Showroom deployment)
  #   - ocp4_workload_showroom_ocp_integration (Showroom OCP integration)
  #   - ocp4_workload_ocp_console_embed (console embedding)
  #   - ocp4_workload_authentication (generic auth wrapper)
  #   - ocp4_workload_litellm_virtual_keys (LiteLLM proxy keys)
  #   - ocp4_workload_tenant_* (per-tenant namespace/resource setup)
  #   - ocp4_workload_kubernetes_image_puller
  #   - ocp4_workload_virt_network_config
  #   - control_user, bastion, asset_injector (VM provisioning plumbing)
  #   - agnosticv_userdata_import (data import helper)
  #   - vm_workload_showroom (VM Showroom deployment)

# Aliases — alternate names that resolve to canonical product_name.
# PH queries match on any alias or the canonical name.
aliases:
  - product: OpenShift AI
    aliases: [RHOAI, Red Hat OpenShift AI]

  - product: Advanced Cluster Security
    aliases: [RHACS, ACS, StackRox]

  - product: OpenShift Pipelines
    aliases: [Tekton]

  - product: OpenShift GitOps
    aliases: [ArgoCD, Argo CD]

  - product: OpenShift Virtualization
    aliases: [KubeVirt, CNV]

  - product: OpenShift Data Foundation
    aliases: [ODF]

  - product: OpenShift Serverless
    aliases: [KNative, Knative]

  - product: OpenShift Service Mesh 2
    aliases: [OSSM, Istio]

  - product: Advanced Cluster Management
    aliases: [RHACM, ACM]

  - product: OpenShift Dev Spaces
    aliases: [DevSpaces, CRW, CodeReady Workspaces]

  - product: OpenShift Lightspeed
    aliases: [OLS]

  - product: Ansible Automation Platform
    aliases: [AAP, AAP2]

  - product: Migration Toolkit for Virtualization
    aliases: [MTV]

  - product: Node Feature Discovery
    aliases: [NFD]
```

### 4c. CLI command to sync mapping

```
rcars sync-workload-mapping [--seed-only]
```

Reads `workload_mapping.yaml`, upserts all entries into the `workload_mapping` table. `--seed-only` skips entries where the role already exists in the DB (preserves curator edits). Without the flag, YAML values overwrite DB values (for bulk corrections). Sets `verified = true` and `verified_at = now()` for entries marked as verified in the YAML.

### 4d. Categories

Categories are a coarse grouping for UI facets. Based on the verified workload analysis:

| Category | Products |
|----------|----------|
| `ai_ml` | OpenShift AI, NVIDIA GPU Operator, OpenShift Lightspeed, ToolHive |
| `cicd` | OpenShift Pipelines, OpenShift GitOps, OpenShift GitOps Bootstrap, OpenShift Builds |
| `security` | Advanced Cluster Security |
| `storage` | OpenShift Data Foundation, MinIO |
| `virtualization` | OpenShift Virtualization, Migration Toolkit for Virtualization |
| `networking` | OpenShift Service Mesh 2/3, MetalLB, NMState, Kiali |
| `runtime` | OpenShift Serverless |
| `developer_tools` | Dev Spaces, Web Terminal, Gitea, GitLab |
| `registry` | Quay |
| `management` | Advanced Cluster Management |
| `automation` | Ansible Automation Platform |
| `messaging` | AMQ Streams |
| `auth` | HTPasswd, Keycloak, Red Hat SSO, Authorino |
| `platform` | cert-manager, NFD, Additional MachineSets |

---

## 5. Refresh Integration

### 5a. Upsert flow changes in `run_catalog_refresh()`

After `upsert_catalog_item()` for each item, sync the related tables:

```python
# In run_catalog_refresh(), inside the per-item loop:
wctx.db.upsert_catalog_item(item)
current_ci_names.add(item["ci_name"])

# NEW: Sync workloads and ACL groups
workloads = item.pop("_workloads", [])
acl_groups = item.pop("_acl_groups", [])
if workloads:
    wctx.db.sync_workloads(item["ci_name"], workloads)
if acl_groups:
    wctx.db.sync_acl_groups(item["ci_name"], acl_groups)
```

### 5b. Cleanup of deleted items

Update `delete_removed_items()` to also clean up the new junction tables. Since they have `ON DELETE CASCADE`, the existing `DELETE FROM catalog_items` already handles this — no code change needed.

### 5c. Performance

Current refresh processes ~1,210 CRDs. Infra extraction only fires for ~212 v2 items (checked via `is_agnosticd_v2()`). The junction table syncs add ~212 DELETE+INSERT batches with ~5 workloads each. Estimated total refresh time increase: <3 seconds.

---

## 6. API Endpoints

### 6a. Faceted infrastructure search (new endpoint)

```
GET /api/v1/catalog/search/infrastructure
```

Only searches AgnosticD v2 items. Query parameters:
- `workloads` — comma-separated product names or aliases (AND semantics). E.g., `?workloads=RHOAI,Pipelines`. Aliases resolved automatically
- `agd_config` — exact match, e.g., `openshift-workloads`, `openshift-cluster`, `cloud-vms-base`
- `cloud_provider` — exact match, e.g., `aws`, `openshift_cnv`
- `ocp_version` — prefix match, e.g., `4.20` matches `4.20`, `4.20.3`, etc. (OCP items)
- `os_image` — prefix match, e.g., `rhel-9` matches `rhel-9.6`, `rhel-9.7`, etc. (RHEL/VM items)
- `stage` — filter by stage
- `limit` — max results (default 50)

Response: array of v2 catalog items with analysis summary, infrastructure metadata, and resolved workload product names.

```python
@router.get("/search/infrastructure")
async def search_infrastructure(
    request: Request,
    user: str = Depends(require_auth),
    workloads: str | None = Query(None),
    agd_config: str | None = None,
    cloud_provider: str | None = None,
    ocp_version: str | None = None,
    os_image: str | None = None,
    stage: str | None = None,
    limit: int = Query(50, le=200),
):
    db = request.app.state.db
    workload_list = [w.strip() for w in workloads.split(",")] if workloads else None
    items = db.search_by_infrastructure(
        workloads=workload_list,
        agd_config=agd_config,
        cloud_provider=cloud_provider,
        ocp_version=ocp_version,
        os_image=os_image,
        stage=stage,
        limit=limit,
    )
    # Attach resolved workload names to each result
    for item in items:
        raw_workloads = db.get_workloads(item["ci_name"])
        mappings = {m["workload_role"]: m for m in db.list_workload_mappings()}
        item["workloads"] = [
            {
                "role": w["workload_role"],
                "product_name": mappings.get(w["workload_role"], {}).get("product_name"),
                "mapped": w["workload_role"] in mappings,
            }
            for w in raw_workloads
        ]
    return {"items": items, "total": len(items)}
```

**Optimization note:** The `list_workload_mappings()` call should be lifted outside the loop and cached per-request. In a later session, consider a single SQL query that joins everything.

### 6b. Available facet values (new endpoint)

PH needs to know what values are available for each facet to build dropdown UIs:

```
GET /api/v1/catalog/facets
```

Returns distinct values for each filterable field, with counts:

```python
@router.get("/facets")
async def catalog_facets(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    with db.pool.connection() as conn:
        cur = conn.execute("""
            SELECT wm.product_name, wm.category, COUNT(DISTINCT ciw.ci_name) AS ci_count
            FROM workload_mapping wm
            JOIN catalog_item_workloads ciw ON ciw.workload_role = wm.workload_role
            JOIN catalog_items ci ON ci.ci_name = ciw.ci_name AND ci.is_prod = TRUE
            GROUP BY wm.product_name, wm.category
            ORDER BY ci_count DESC
        """)
        workloads = cur.fetchall()

        cur = conn.execute("""
            SELECT agd_config, COUNT(*) AS ci_count
            FROM catalog_items WHERE is_agd_v2 = TRUE AND is_prod = TRUE
            GROUP BY agd_config ORDER BY ci_count DESC
        """)
        configs = cur.fetchall()

        cur = conn.execute("""
            SELECT cloud_provider, COUNT(*) AS ci_count
            FROM catalog_items WHERE is_agd_v2 = TRUE AND cloud_provider IS NOT NULL
              AND cloud_provider != 'none' AND is_prod = TRUE
            GROUP BY cloud_provider ORDER BY ci_count DESC
        """)
        cloud_providers = cur.fetchall()

        cur = conn.execute("""
            SELECT os_image, COUNT(*) AS ci_count
            FROM catalog_items WHERE is_agd_v2 = TRUE AND os_image IS NOT NULL
              AND is_prod = TRUE
            GROUP BY os_image ORDER BY ci_count DESC
        """)
        os_images = cur.fetchall()

    return {
        "workloads": workloads,
        "configs": configs,
        "cloud_providers": cloud_providers,
        "os_images": os_images,
    }
```

### 6c. Workload mapping management (admin/curator endpoints)

```
GET  /api/v1/catalog/workload-mappings           — list all mappings
POST /api/v1/catalog/workload-mappings           — add/update mapping (curator)
DELETE /api/v1/catalog/workload-mappings/{role}   — remove mapping (admin)
GET  /api/v1/catalog/workload-mappings/unmapped  — list unmapped workloads with CI counts
```

### 6d. Existing endpoint enrichment

`GET /catalog/{ci_name}` — add infra metadata, workloads (with product names), and ACL groups to the response. The infra columns are already on `catalog_items` so they come for free. Workloads and ACL groups need the extra queries:

```python
@router.get("/{ci_name}")
async def get_catalog_item(ci_name: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    item = db.get_catalog_item(ci_name)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    analysis = db.get_showroom_analysis(ci_name)
    tags = db.get_enrichment_tags(ci_name)
    workloads = db.get_workloads(ci_name)
    acl_groups = db.get_acl_groups(ci_name)
    return {**item, "analysis": analysis, "tags": tags,
            "workloads": workloads, "acl_groups": acl_groups}
```

---

## 7. Combined Queries (Faceted + Vector)

Today, the Advisor page does **content-based** recommendations: "find me a lab about fraud detection" → vector search against Showroom content → triage → rationale. The new faceted search (section 6a) does **infrastructure-based** queries: "find me something with OpenShift AI and Pipelines" → exact match against workload mappings. These are two separate endpoints.

A combined query is where a user asks for both at once: "OpenShift AI cluster for a fraud detection demo" = faceted filter (must have OpenShift AI workload) **AND** vector search (content about fraud detection). Neither search alone can answer this — the faceted search doesn't know about content topics, and the vector search doesn't know about installed workloads.

### 7a. Implementation approach

This would be a post-filter on the existing Advisor pipeline. The recommend worker already produces a candidate list via vector search → triage → rationale. Adding an infrastructure filter means narrowing that candidate list to only CIs that also match the infra criteria.

```python
class AdvisorQuery(BaseModel):
    query: str
    session_id: str | None = None
    stages: list[str] = ["prod"]
    include_zt: bool = True
    infra_filter: InfraFilter | None = None

class InfraFilter(BaseModel):
    workloads: list[str] | None = None      # product names or aliases (AND)
    agd_config: str | None = None
    cloud_provider: str | None = None
    ocp_version: str | None = None
    os_image: str | None = None
```

In `vector_search.py`, after generating candidates, filter out any that don't match the infra criteria. This keeps vector search unchanged (it still finds content-relevant items) and applies the infra filter as a post-processing step.

### 7b. Deferred to future session

The combined query should be implemented after the base faceted search is working and tested. For the initial implementation, PH calls the faceted search endpoint (`/catalog/search/infrastructure`) and the advisor endpoint (`/advisor/query`) as two separate queries. Once both are stable, combining them is straightforward — add the `infra_filter` parameter to the advisor query and apply it as a post-filter on vector search candidates.

---

## 8. Browse/Admin UI

### 8a. Browse page — infrastructure detail panel

When a v2 catalog item is expanded in Browse, show a new "Infrastructure" section below the existing analysis summary. Only shown for items where `is_agd_v2 = true`:

```
┌─────────────────────────────────────────────────────────────────┐
│ ▼ agd-v2.ocp4-lightspeed-cnv.prod                       [v2]   │
│                                                                   │
│   Config: openshift-cluster  |  Cloud: openshift_cnv  |  OCP: 4.20│
│   Workers: 3  |  Control plane: 3                                 │
│                                                                   │
│   Workloads: OpenShift AI ✓, Pipelines ✓, GitOps ✓, cert-manager ✓│
│              + 2 unmapped (ocp4_workload_lightspeed_demo, ...)    │
│                                                                   │
│   ACL: rhpds-devs-ai                                              │
│                                                                   │
│   Summary: A hands-on lab teaching OpenShift Lightspeed...        │
│   Modules: [1. Setup] [2. Prompting] [3. Customization]          │
└─────────────────────────────────────────────────────────────────┘
```

Verified workloads show their product name with a ✓ checkmark. Unverified mapped workloads show the product name without ✓. Unmapped workloads show with a dimmed style and raw role name. A `[v2]` badge on the item header identifies AgnosticD v2 items.

### 8b. Browse page — infrastructure filters

Add new filter dropdowns to the Browse filter bar:

- **Config** — dropdown of `agd_config` values (from `/facets`): openshift-workloads, openshift-cluster, namespace, cloud-vms-base
- **Cloud** — dropdown of `cloud_provider` values (excluding `none`)
- **OS image** — dropdown of `os_image` values (from `/facets`): rhel-9.6, rhel-10.0, etc. (for VM items)
- **Has workload** — multi-select of curated product names (aliases resolved automatically)
- **v2 only** — toggle to filter to AgnosticD v2 items only

These filters combine with existing stage/category filters via AND. The query hits `search_by_infrastructure()` when infra filters are active, falls back to `list_catalog_items()` when only existing filters are used.

### 8c. Admin page — workload mapping management

Add a "Workload Mappings" section to the Admin page (or a new Admin sub-page):

- Table of all mappings: role → product name → description → category → CI count → verified?
- "Unmapped workloads" table: role → collection → CI count → [Map] button
- Inline edit for product name, description, and category
- Mapping stats in the status bar: "35 mapped (32 verified), 89 unmapped"

### 8d. Admin page — infrastructure stats

Add v2/infra coverage stats to the existing catalog status panel:

```
Catalog: 1,210 items (212 v2)  |  Workloads: 188 with workloads, 35 mapped (32 verified)
```

---

## 9. CLI Commands

### 9a. New commands

Organized under `rcars infra` and `rcars workload` subcommand groups to keep the CLI structured as it grows.

**Infrastructure commands** (`rcars infra`):

| Command | Purpose |
|---------|---------|
| `rcars infra stats` | Show v2/infra coverage stats (v2 items, workload coverage, mapping status) |

**Workload commands** (`rcars workload`):

| Command | Purpose |
|---------|---------|
| `rcars workload sync [--seed-only]` | Load workload_mapping.yaml (mappings + aliases) into DB |
| `rcars workload scan [--collection X] [--role Y]` | Clone agDv2 repos, read Ansible code, LLM-analyze, upsert verified mappings |
| `rcars workload unmapped` | List workloads that appear in catalog but have no mapping, with CI counts |
| `rcars workload map ROLE PRODUCT [--category CAT] [--description DESC]` | Add/update a single workload mapping |
| `rcars workload alias PRODUCT ALIAS` | Add a product name alias |
| `rcars workload list` | List all current mappings with verified status |

---

## 10. Implementation Plan

### Session 1: Data layer + extraction

1. Alembic migration `002_infrastructure_metadata.py`
2. Update `SCHEMA_SQL` in `database.py` (new tables + columns including `workload_aliases`)
3. Update `drop_schema()` to include new tables
4. `is_agnosticd_v2()` and `extract_infrastructure_metadata()` in `catalog.py` (handles OCP + RHEL/VM items)
5. `parse_workload_fqcn()` helper
6. New `Database` methods: `sync_workloads()`, `sync_acl_groups()`, `get_workloads()`, `get_acl_groups()`, `_resolve_workload_aliases()`
7. Update `upsert_catalog_item()` field list (including `os_image`, `instances_json`)
8. Integration in `CatalogReader.refresh_catalog()` (v2-gated)
9. Create `workload_mapping.yaml` seed file (mappings + aliases)
10. CLI commands: `rcars workload sync`, `rcars infra stats`, `rcars workload unmapped`
11. Test: run refresh locally, verify v2 infra data populates (OCP + RHEL items), v1 items get NULLs

### Session 2: API + faceted search + workload scanning

1. `search_by_infrastructure()` in `database.py` (with alias resolution, `os_image` filter)
2. Workload mapping CRUD methods (with verified flag)
3. `get_unmapped_workloads()`, `get_infra_stats()`
4. New API endpoints: `/catalog/search/infrastructure`, `/catalog/facets` (includes `os_images`)
5. Workload mapping management endpoints
6. Enrich `GET /catalog/{ci_name}` response (workloads + ACL groups for v2 items)
7. Workload repo scanner: clone from remotes, read code, LLM analysis, upsert verified mappings
8. API endpoint to trigger workload repo scan (admin)
9. Integration into nightly maintenance pipeline (with ls-remote change detection)
10. CLI command: `rcars workload scan`
11. Config: `RCARS_WORKLOAD_SCAN_ENABLED`, `RCARS_WORKLOAD_SCAN_INTERVAL_DAYS`
12. Test: API integration tests for faceted search + workload scanning

### Session 3: Frontend + polish

1. Browse page — infrastructure detail panel in expanded v2 items (OCP and RHEL views)
2. Browse page — infrastructure filter dropdowns (config, cloud, OS image, workload) + v2 toggle
3. Admin page — workload mapping management UI (with verified column, description)
4. Admin page — "Rescan Workload Repos" button
5. Admin page — v2/infra stats in status bar
6. Combined query support (infra filter in advisor) — if time permits
7. Test: end-to-end Browse + Admin UI verification

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| V2 items only, exact scm_url match | V1 items use inconsistent conventions. Forks are dev items — only the canonical `agnosticd/agnosticd-v2` repo matters |
| `agd_config` not `env_type` | In v2, `env_type` is always `{{ config }}` — the `config` field is the actual platform type |
| `os_image` only for `cloud-vms-base` | Almost everything has a bastion with a RHEL image — but only `cloud-vms-base` items ARE RHEL environments. "Give me a RHEL 10 environment" must return actual RHEL CIs, not OCP clusters with a RHEL bastion |
| `instances_json` for VM topology | Full VM specs (cores, memory, count) stored as JSONB for display. Not used for faceted search — too heterogeneous |
| Store full FQCN + extracted role | FQCN preserves provenance (which collection repo). Role name is the key for mapping since the same operator can appear in different collections |
| VM workloads from dict fields | `cloud-vms-base` items use `software_workloads`, `post_software_workloads` etc. (dicts keyed by host group), not the flat `workloads` list. Extraction handles both formats |
| Verified via code analysis, not READMEs | PH express mode can't trust name-guessed mappings. READMEs and `meta/main.yml` descriptions are unreliable. The scanner reads `defaults/main.yml`, `tasks/main.yml`, and templates to determine what the role actually deploys |
| Product name aliases | People use many names for the same product (OpenShift AI / RHOAI / Red Hat OpenShift AI). Aliases ensure PH queries match regardless of which name is used |
| Clone from remotes, not local copies | Workload repos must be cloned from `github.com/agnosticd/*` remotes. Private `rhpds/*` repos flagged at scan time for manual resolution |
| Daily workload scan with change detection | ls-remote first, only clone+analyze repos with new commits. Configurable via `RCARS_WORKLOAD_SCAN_ENABLED` / `RCARS_WORKLOAD_SCAN_INTERVAL_DAYS`. No harm in daily since unchanged repos are skipped |
| CLI organized under `rcars infra` / `rcars workload` | CLI is growing — subcommand namespaces keep it structured and discoverable |
| Junction table for workloads, not TEXT[] | Enables efficient faceted JOIN queries with AND semantics; array containment is harder to compose and index |
| DB table for mapping, not config file | Curators need to manage mappings via UI without code deploys; YAML seeds initial data only |
| Store raw role names, resolve via mapping | Avoids data loss; new workloads appear in "unmapped" list automatically after refresh |
| TEXT for instance counts | Some CRDs use Jinja2 templates for worker counts; TEXT preserves the raw value |
| Separate ACL table | Prepares for the ACL-aware recommendations backlog item; no extra extraction cost since we're already reading `spec.definition` |
| Faceted search, not vector search for infra | "Has Pipelines and RHACS" is an exact match filter, not a similarity question; vector search remains for content/topic matching |
| Post-filter for combined queries | Keeps the existing recommend pipeline unchanged; infra filter narrows the candidate list after vector search |
