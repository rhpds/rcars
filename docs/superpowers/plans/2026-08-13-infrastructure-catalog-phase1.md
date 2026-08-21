# Infrastructure Catalog — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the curator-managed `workload_mapping` system with a scanner-populated `infrastructure` table covering both workload roles and base configs, generate embeddings for infrastructure, and rebuild the Workloads page as a read-only browse view of the infrastructure catalog.

**Architecture:** New `infrastructure` table replaces `workload_mapping` + `workload_scan_state`. The existing workload scanner writes richer LLM-generated data into this table; a new config scanner handles the agnosticd-v2 configs repo. Embeddings go into the shared `embeddings` table with `content_type = 'infrastructure'`. The Workloads page is rebuilt as a read-only catalog browser. All old CRUD (manual mapping, verified badges, unmapped concepts) is deleted.

**Tech Stack:** Python 3.11, FastAPI 2.0, psycopg, PostgreSQL + pgvector, React 19, TypeScript, Vite

**Spec:** `docs/superpowers/specs/2026-08-13-infrastructure-catalog-design.md`

## Global Constraints

- All data from public AgnosticD repos only — no private repos, no AgnosticV variable data
- v2 only — no AgnosticD v1 items
- `workload_aliases` table retained as-is — it resolves user-facing names to canonical `products` values
- `babylon_item_workloads` join table retained as-is — it maps CIs to their deployed workloads
- Embeddings use content_type `'infrastructure'` in the shared `embeddings` table
- The `infrastructure` table PK is `role_name` (TEXT), matching existing `workload_role` values for workloads and directory names for configs

---

### Task 1: Add `infrastructure` table to schema and migrate existing data

**Files:**
- Modify: `src/api/rcars/db/database.py:24-329` (SCHEMA_SQL) and methods section (~1347-1600)

**Interfaces:**
- Produces: `infrastructure` table DDL in `SCHEMA_SQL`, `db.upsert_infrastructure()`, `db.list_infrastructure()`, `db.get_infrastructure()`, `db.get_infrastructure_with_item_counts()`

- [ ] **Step 1: Write failing test for infrastructure table operations**

```python
# tests/test_infrastructure.py
import pytest
from rcars.db.database import Database


@pytest.fixture
def db(test_db_pool):
    return Database(test_db_pool)


def test_upsert_infrastructure_insert(db):
    db.upsert_infrastructure(
        role_name="ocp4_workload_rhods",
        fqcn="agnosticd.ai_workloads.ocp4_workload_rhods",
        collection="agnosticd.ai_workloads",
        type="workload",
        description="Installs OpenShift AI (RHOAI) operator and components.",
        products=["OpenShift AI", "KServe"],
        capabilities=["model-serving", "notebook-hosting"],
        category="ai_ml",
        requires=["openshift 4.14+", "gpu-nodes"],
        source_sha="abc123",
    )
    row = db.get_infrastructure("ocp4_workload_rhods")
    assert row is not None
    assert row["type"] == "workload"
    assert row["description"] == "Installs OpenShift AI (RHOAI) operator and components."
    assert row["products"] == ["OpenShift AI", "KServe"]
    assert row["capabilities"] == ["model-serving", "notebook-hosting"]
    assert row["category"] == "ai_ml"


def test_upsert_infrastructure_update(db):
    db.upsert_infrastructure(
        role_name="ocp4_workload_rhods", fqcn=None, collection="agnosticd.ai_workloads",
        type="workload", description="v1", products=[], capabilities=[], category="ai_ml",
        requires=[], source_sha="sha1",
    )
    db.upsert_infrastructure(
        role_name="ocp4_workload_rhods", fqcn=None, collection="agnosticd.ai_workloads",
        type="workload", description="v2", products=["RHOAI"], capabilities=["notebooks"],
        category="ai_ml", requires=[], source_sha="sha2",
    )
    row = db.get_infrastructure("ocp4_workload_rhods")
    assert row["description"] == "v2"
    assert row["products"] == ["RHOAI"]
    assert row["source_sha"] == "sha2"


def test_list_infrastructure_with_type_filter(db):
    db.upsert_infrastructure(
        role_name="ocp4_workload_acs", fqcn=None, collection="agnosticd.core_workloads",
        type="workload", description="ACS", products=["ACS"], capabilities=[],
        category="security", requires=[], source_sha="sha1",
    )
    db.upsert_infrastructure(
        role_name="openshift-cluster", fqcn=None, collection=None,
        type="config", description="Base OpenShift cluster", products=["OpenShift"],
        capabilities=["cluster-provisioning"], category="platform", requires=[],
        source_sha="sha2",
    )
    all_rows = db.list_infrastructure()
    assert len(all_rows) == 2

    workloads = db.list_infrastructure(type_filter="workload")
    assert len(workloads) == 1
    assert workloads[0]["role_name"] == "ocp4_workload_acs"

    configs = db.list_infrastructure(type_filter="config")
    assert len(configs) == 1
    assert configs[0]["role_name"] == "openshift-cluster"


def test_get_infrastructure_with_item_counts(db):
    # Insert infrastructure + content entity + babylon item + link via babylon_item_workloads
    db.upsert_infrastructure(
        role_name="ocp4_workload_rhods", fqcn="agnosticd.ai_workloads.ocp4_workload_rhods",
        collection="agnosticd.ai_workloads", type="workload", description="RHOAI",
        products=["OpenShift AI"], capabilities=[], category="ai_ml", requires=[],
        source_sha="sha1",
    )
    rows = db.get_infrastructure_with_item_counts()
    # Should return the row with item_count = 0 (no linked CIs in test DB)
    assert any(r["role_name"] == "ocp4_workload_rhods" for r in rows)
    row = next(r for r in rows if r["role_name"] == "ocp4_workload_rhods")
    assert row["item_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/api && python -m pytest tests/test_infrastructure.py -v`
Expected: FAIL — `infrastructure` table does not exist, `upsert_infrastructure` method not found

- [ ] **Step 3: Add infrastructure table DDL to SCHEMA_SQL**

In `database.py`, add to `SCHEMA_SQL` after the `workload_scan_state` block (line ~329), before `enrichment_tags`:

```sql
-- ═══════════════════════════════════════════════════════════════════
-- infrastructure — unified workload roles + base configs catalog
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS infrastructure (
    role_name   TEXT PRIMARY KEY,
    fqcn        TEXT,
    collection  TEXT,
    type        TEXT NOT NULL,
    description TEXT,
    products    JSONB DEFAULT '[]',
    capabilities JSONB DEFAULT '[]',
    category    TEXT,
    requires    JSONB DEFAULT '[]',
    source_sha  TEXT,
    scanned_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_infrastructure_type ON infrastructure(type);
CREATE INDEX IF NOT EXISTS idx_infrastructure_category ON infrastructure(category);
```

- [ ] **Step 4: Add database methods for infrastructure**

Add to the `Database` class, in a new section after the existing workload methods:

```python
# ── Infrastructure catalog ──

def upsert_infrastructure(
    self, role_name: str, fqcn: str | None, collection: str | None,
    type: str, description: str | None, products: list, capabilities: list,
    category: str | None, requires: list, source_sha: str | None,
) -> None:
    with self._pool.connection() as conn:
        conn.execute(
            "INSERT INTO infrastructure "
            "(role_name, fqcn, collection, type, description, products, capabilities, "
            "category, requires, source_sha, scanned_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()) "
            "ON CONFLICT (role_name) DO UPDATE SET "
            "fqcn = EXCLUDED.fqcn, collection = EXCLUDED.collection, type = EXCLUDED.type, "
            "description = EXCLUDED.description, products = EXCLUDED.products, "
            "capabilities = EXCLUDED.capabilities, category = EXCLUDED.category, "
            "requires = EXCLUDED.requires, source_sha = EXCLUDED.source_sha, "
            "scanned_at = EXCLUDED.scanned_at",
            (role_name, fqcn, collection, type, description,
             Jsonb(products), Jsonb(capabilities), category, Jsonb(requires), source_sha),
        )
        conn.commit()

def get_infrastructure(self, role_name: str) -> dict | None:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT * FROM infrastructure WHERE role_name = %s", (role_name,)
        )
        return cur.fetchone()

def list_infrastructure(
    self, type_filter: str | None = None, category_filter: str | None = None,
    collection_filter: str | None = None, search: str | None = None,
    has_mappings: bool | None = None, limit: int = 500,
) -> list[dict]:
    conditions = []
    params: dict[str, Any] = {}
    if type_filter:
        conditions.append("i.type = %(type)s")
        params["type"] = type_filter
    if category_filter:
        conditions.append("i.category = %(category)s")
        params["category"] = category_filter
    if collection_filter:
        conditions.append("i.collection = %(collection)s")
        params["collection"] = collection_filter
    if search:
        conditions.append(
            "(i.role_name ILIKE %(search)s OR i.description ILIKE %(search)s "
            "OR i.products::text ILIKE %(search)s OR i.capabilities::text ILIKE %(search)s)"
        )
        params["search"] = f"%{search}%"
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM infrastructure i {where} ORDER BY i.role_name LIMIT %(limit)s"
    params["limit"] = limit
    with self._pool.connection() as conn:
        return conn.execute(sql, params).fetchall()

def get_infrastructure_with_item_counts(
    self, type_filter: str | None = None, category_filter: str | None = None,
    collection_filter: str | None = None, search: str | None = None,
    has_mappings: bool | None = None, limit: int = 500,
) -> list[dict]:
    conditions = []
    params: dict[str, Any] = {}
    if type_filter:
        conditions.append("i.type = %(type)s")
        params["type"] = type_filter
    if category_filter:
        conditions.append("i.category = %(category)s")
        params["category"] = category_filter
    if collection_filter:
        conditions.append("i.collection = %(collection)s")
        params["collection"] = collection_filter
    if search:
        conditions.append(
            "(i.role_name ILIKE %(search)s OR i.description ILIKE %(search)s "
            "OR i.products::text ILIKE %(search)s OR i.capabilities::text ILIKE %(search)s)"
        )
        params["search"] = f"%{search}%"
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Count linked CIs: workloads via babylon_item_workloads, configs via babylon_items.agd_config
    sql = f"""
        SELECT i.*,
            COALESCE(wc.cnt, 0) + COALESCE(cc.cnt, 0) AS item_count
        FROM infrastructure i
        LEFT JOIN (
            SELECT biw.workload_role AS role_name, COUNT(DISTINCT biw.content_id) AS cnt
            FROM babylon_item_workloads biw
            JOIN content_entities ce ON ce.content_id = biw.content_id AND ce.retired_at IS NULL
            GROUP BY biw.workload_role
        ) wc ON wc.role_name = i.role_name AND i.type = 'workload'
        LEFT JOIN (
            SELECT bi.agd_config AS role_name, COUNT(DISTINCT bi.content_id) AS cnt
            FROM babylon_items bi
            JOIN content_entities ce ON ce.content_id = bi.content_id AND ce.retired_at IS NULL
            WHERE bi.agd_config IS NOT NULL
            GROUP BY bi.agd_config
        ) cc ON cc.role_name = i.role_name AND i.type = 'config'
        {where}
        ORDER BY i.role_name
        LIMIT %(limit)s
    """
    params["limit"] = limit
    if has_mappings is True:
        sql = sql.replace("ORDER BY", "HAVING COALESCE(wc.cnt, 0) + COALESCE(cc.cnt, 0) > 0 ORDER BY")
    elif has_mappings is False:
        sql = sql.replace("ORDER BY", "HAVING COALESCE(wc.cnt, 0) + COALESCE(cc.cnt, 0) = 0 ORDER BY")

    with self._pool.connection() as conn:
        return conn.execute(sql, params).fetchall()
```

Note: The `has_mappings` filter using HAVING won't work with the current SQL structure — there's no GROUP BY. Revise to use a subquery or CTE wrapping. The implementation should use:

```python
    if has_mappings is not None:
        having = "> 0" if has_mappings else "= 0"
        # Wrap in CTE and filter
        sql = f"WITH infra AS ({sql}) SELECT * FROM infra WHERE item_count {having}"
```

- [ ] **Step 5: Add data migration in create_schema()**

At the end of `create_schema()`, add a one-time migration to copy existing `workload_mapping` rows into `infrastructure`:

```python
# Migrate workload_mapping → infrastructure (idempotent)
conn.execute("""
    INSERT INTO infrastructure (role_name, fqcn, collection, type, description,
        products, capabilities, category, requires, source_sha, scanned_at)
    SELECT wm.workload_role, NULL, wm.source_collection, 'workload', wm.description,
        jsonb_build_array(wm.product_name), '[]'::jsonb, wm.category, '[]'::jsonb,
        NULL, wm.added_at
    FROM workload_mapping wm
    WHERE NOT EXISTS (SELECT 1 FROM infrastructure i WHERE i.role_name = wm.workload_role)
""")
conn.commit()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_infrastructure.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/db/database.py src/api/tests/test_infrastructure.py
git commit -m "[JIRA-KEY] Add infrastructure table and DB methods with data migration"
```

---

### Task 2: Enrich workload scanner to write richer data to infrastructure table

**Files:**
- Modify: `src/api/rcars/services/workload_scanner.py`

**Interfaces:**
- Consumes: `db.upsert_infrastructure(role_name, fqcn, collection, type, description, products, capabilities, category, requires, source_sha)` from Task 1
- Produces: enriched scanner that writes to `infrastructure` table instead of `workload_mapping`; SHA skip logic reads `infrastructure.source_sha` instead of `workload_scan_state`

- [ ] **Step 1: Write failing test for enriched workload scan output**

```python
# tests/test_workload_scanner.py
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from rcars.services.workload_scanner import (
    WORKLOAD_SYSTEM_PROMPT, analyze_role,
)


def test_enriched_prompt_requests_structured_output():
    """The system prompt must request the full structured output fields."""
    assert "products" in WORKLOAD_SYSTEM_PROMPT
    assert "capabilities" in WORKLOAD_SYSTEM_PROMPT
    assert "requires" in WORKLOAD_SYSTEM_PROMPT
    assert "description" in WORKLOAD_SYSTEM_PROMPT


def test_analyze_role_returns_enriched_fields():
    """analyze_role should return the enriched field set."""
    mock_result = MagicMock()
    mock_result.text = json.dumps({
        "product_name": "OpenShift AI",
        "description": "Installs RHOAI operator with KServe support. Default auth is KeyCloak.",
        "products": ["OpenShift AI", "KServe"],
        "capabilities": ["model-serving", "notebook-hosting"],
        "category": "ai_ml",
        "requires": ["openshift 4.14+"],
        "is_infrastructure_plumbing": False,
    })
    mock_result.input_tokens = 100
    mock_result.output_tokens = 50
    mock_result.provider = "test"

    with patch("rcars.services.workload_scanner.call_llm", return_value=mock_result):
        with patch("rcars.services.workload_scanner.read_role_code", return_value="some code"):
            result = analyze_role(
                "ocp4_workload_rhods", Path("/fake"), "agnosticd.ai_workloads",
                MagicMock(), "test-model", db=None,
            )

    assert result is not None
    assert result["products"] == ["OpenShift AI", "KServe"]
    assert result["capabilities"] == ["model-serving", "notebook-hosting"]
    assert result["requires"] == ["openshift 4.14+"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/api && python -m pytest tests/test_workload_scanner.py -v`
Expected: FAIL — prompt doesn't contain "products"/"capabilities"/"requires", result may not have those keys

- [ ] **Step 3: Update LLM prompt for richer structured output**

Replace `WORKLOAD_SYSTEM_PROMPT` (line 22) with:

```python
WORKLOAD_SYSTEM_PROMPT = """\
You are analyzing an Ansible role from the AgnosticD v2 automation framework.
Your job is to determine what this role installs, configures, or enables on an OpenShift cluster or RHEL system.

Use ONLY the code provided to determine what the role does — do not guess from the name.

Respond with a JSON object:
{
  "product_name": "Human-readable product name (e.g. 'OpenShift AI', 'Advanced Cluster Security')",
  "description": "Multi-sentence narrative covering what this role installs, configures, and enables, including default configuration choices discovered from the code (e.g. 'default authentication provider is KeyCloak')",
  "products": ["Array of products/operators/services this installs"],
  "capabilities": ["Array of capabilities this enables (e.g. 'model-serving', 'notebook-hosting')"],
  "category": "One of: ai_ml, cicd, security, storage, virtualization, networking, runtime, developer_tools, registry, management, automation, messaging, auth, platform, monitoring, other",
  "requires": ["Array of prerequisites (e.g. 'openshift 4.14+', 'gpu-nodes')"],
  "is_infrastructure_plumbing": true/false
}

Set is_infrastructure_plumbing to true if this role is internal setup (authentication, showroom deployment, bastion configuration, namespace creation, certificate management) rather than a user-facing product that someone would search for.

Return ONLY the JSON object, no other text."""
```

- [ ] **Step 4: Update scan_collection to write to infrastructure table**

In `scan_collection()` (line 154), replace the `db.upsert_workload_mapping()` call (line 209-217) with:

```python
fqcn = f"{collection_name}.{role_name}"
db.upsert_infrastructure(
    role_name=role_name,
    fqcn=fqcn,
    collection=collection_name,
    type="workload",
    description=result.get("description"),
    products=result.get("products", [result["product_name"]]),
    capabilities=result.get("capabilities", []),
    category=result.get("category"),
    requires=result.get("requires", []),
    source_sha=local_sha,
)
```

- [ ] **Step 5: Update SHA skip logic to use infrastructure table**

Replace the SHA check in `scan_collection()` (lines 166-172). Instead of `db.get_scan_state()`, query the `infrastructure` table:

```python
if not force:
    remote_sha = ls_remote_sha(collection_url, "main")
    if remote_sha:
        existing = db.get_infrastructure_scan_sha(collection_name)
        if existing == remote_sha:
            rlog.info("workload_scan: unchanged (SHA %s), skipping", remote_sha[:12])
            return {"collection": collection_name, "status": "unchanged", "roles_scanned": 0}
```

Add `get_infrastructure_scan_sha()` to `Database`:

```python
def get_infrastructure_scan_sha(self, collection: str) -> str | None:
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT source_sha FROM infrastructure WHERE collection = %s LIMIT 1",
            (collection,),
        )
        row = cur.fetchone()
        return row["source_sha"] if row else None
```

And replace `db.upsert_scan_state(collection_name, local_sha)` (line 221) — remove it. The SHA is now stored per-row on `infrastructure.source_sha`, set during `upsert_infrastructure()`.

- [ ] **Step 6: Run tests**

Run: `cd src/api && python -m pytest tests/test_workload_scanner.py tests/test_infrastructure.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/services/workload_scanner.py src/api/tests/test_workload_scanner.py
git commit -m "[JIRA-KEY] Enrich workload scanner to write structured data to infrastructure table"
```

---

### Task 3: Add config scanner

**Files:**
- Modify: `src/api/rcars/services/workload_scanner.py` (add config scanning functions at bottom)

**Interfaces:**
- Consumes: `db.upsert_infrastructure(...)` from Task 1, `clone_showroom()` and `ls_remote_sha()` from `analyzer.py`
- Produces: `scan_configs(clone_dir, settings, model, db, force)` → `dict` with scan stats

- [ ] **Step 1: Write failing test for config scanning**

```python
# tests/test_config_scanner.py
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from rcars.services.workload_scanner import (
    CONFIG_SYSTEM_PROMPT, read_config_code, scan_configs,
)


def test_config_prompt_requests_structured_output():
    assert "products" in CONFIG_SYSTEM_PROMPT
    assert "capabilities" in CONFIG_SYSTEM_PROMPT
    assert "category" in CONFIG_SYSTEM_PROMPT


def test_read_config_code():
    """read_config_code should read key files from a config directory."""
    with patch("pathlib.Path.is_dir", return_value=True):
        with patch("pathlib.Path.iterdir", return_value=[]):
            with patch("pathlib.Path.exists", return_value=False):
                result = read_config_code(Path("/fake/openshift-cluster"))
    # Should return empty or minimal when no files found
    assert isinstance(result, str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/api && python -m pytest tests/test_config_scanner.py -v`
Expected: FAIL — `CONFIG_SYSTEM_PROMPT`, `read_config_code`, `scan_configs` do not exist

- [ ] **Step 3: Implement config scanning**

Add to `workload_scanner.py`:

```python
AGDV2_CONFIGS_REPO = {
    "name": "agnosticd-v2-configs",
    "url": "https://github.com/rhpds/agnosticd-v2.git",
    "configs_path": "ansible/configs",
}

EXCLUDE_CONFIGS = {"test-empty-config"}

CONFIG_SYSTEM_PROMPT = """\
You are analyzing a base infrastructure configuration from the AgnosticD v2 automation framework.
This is NOT an Ansible role — it is a full environment configuration that provisions cloud infrastructure
and installs a base platform (e.g. an OpenShift cluster, a set of cloud VMs, a namespace).

Use ONLY the code provided to determine what this config provisions and what it provides.

Respond with a JSON object:
{
  "description": "Multi-sentence narrative covering what this config provisions, what platform it provides, what cloud providers it supports, and key configuration options",
  "products": ["Array of products/platforms this provides (e.g. 'OpenShift', 'RHEL')"],
  "capabilities": ["Array of capabilities (e.g. 'cluster-provisioning', 'gpu-support', 'multi-node')"],
  "category": "One of: platform, virtualization, cloud, namespace, other",
  "requires": ["Array of prerequisites (e.g. 'AWS account', 'Azure subscription')"]
}

Return ONLY the JSON object, no other text."""

CONFIG_USER_TEMPLATE = """\
Config name: {config_name}

{code_content}"""


def read_config_code(config_path: Path, max_chars: int = 15000) -> str:
    """Read key files from a config directory for LLM analysis."""
    sections = []
    files_to_read = [
        ("default_vars.yml", "DEFAULT VARS"),
        ("default_vars.yaml", "DEFAULT VARS"),
        ("README.adoc", "README"),
        ("README.md", "README"),
        ("software.yml", "SOFTWARE PLAYBOOK"),
        ("software.yaml", "SOFTWARE PLAYBOOK"),
        ("post_software.yml", "POST SOFTWARE"),
        ("post_software.yaml", "POST SOFTWARE"),
    ]
    for rel_path, label in files_to_read:
        fp = config_path / rel_path
        if fp.exists() and fp.is_file():
            content = fp.read_text(errors="replace")[:4000]
            sections.append(f"=== {label} ({rel_path}) ===\n{content}")

    # Provider-specific default_vars
    for subdir in sorted(config_path.iterdir()) if config_path.is_dir() else []:
        if subdir.is_dir() and subdir.name not in (".", ".."):
            for name in ("default_vars.yml", "default_vars.yaml"):
                fp = subdir / name
                if fp.exists() and fp.is_file():
                    content = fp.read_text(errors="replace")[:3000]
                    sections.append(f"=== PROVIDER VARS ({subdir.name}/{name}) ===\n{content}")

    combined = "\n\n".join(sections)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n... (truncated)"
    return combined


def analyze_config(
    config_name: str,
    config_path: Path,
    settings,
    model: str,
    db: Database | None = None,
) -> dict | None:
    """Analyze a single config via LLM and return structured data."""
    code_content = read_config_code(config_path)
    if not code_content.strip():
        log.info("config_scan_skip", component="config_scan", action="skipping",
                 config=config_name, reason="no readable code")
        return None

    user_message = CONFIG_USER_TEMPLATE.format(
        config_name=config_name, code_content=code_content,
    )

    try:
        from rcars.config import call_llm
        llm_result = call_llm(settings, model=model,
                              messages=[{"role": "user", "content": user_message}],
                              max_tokens=1024, system=CONFIG_SYSTEM_PROMPT)

        if db is not None:
            db.log_token_usage(
                operation="config_scan", model=model,
                input_tokens=llm_result.input_tokens,
                output_tokens=llm_result.output_tokens,
                ci_name=config_name, provider=llm_result.provider,
            )

        text = llm_result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]

        result = json.loads(text)
        log.info("config_scan_analyzed", component="config_scan", action="analyzed",
                 config=config_name, category=result.get("category"))
        return result

    except (json.JSONDecodeError, IndexError, KeyError) as e:
        log.warning("config_scan_parse_error", component="config_scan", action="failed_to_parse",
                    config=config_name, error=str(e))
        return None
    except Exception as e:
        log.error("config_scan_llm_error", component="config_scan", action="llm_error",
                  config=config_name, error=str(e))
        return None


def scan_configs(
    clone_dir: str,
    settings,
    model: str,
    db: Database,
    force: bool = False,
) -> dict:
    """Scan AgnosticD v2 configs directory."""
    repo = AGDV2_CONFIGS_REPO
    rlog = log.bind(component="config_scan")

    if not force:
        remote_sha = ls_remote_sha(repo["url"], "main")
        if remote_sha:
            existing = db.get_infrastructure_scan_sha(repo["name"])
            if existing == remote_sha:
                rlog.info("config_scan: unchanged, skipping")
                return {"status": "unchanged", "configs_scanned": 0}

    clone_path = clone_showroom(repo["url"], "main", clone_dir)
    if not clone_path:
        rlog.error("config_scan: clone failed")
        return {"status": "clone_failed", "configs_scanned": 0}

    try:
        import subprocess
        local_sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(clone_path),
            capture_output=True, text=True,
        )
        local_sha = local_sha_result.stdout.strip() if local_sha_result.returncode == 0 else None

        configs_dir = clone_path / Path(repo["configs_path"])
        if not configs_dir.is_dir():
            rlog.error("config_scan: configs path not found: %s", configs_dir)
            return {"status": "no_configs_dir", "configs_scanned": 0}

        config_dirs = sorted([
            d for d in configs_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name not in EXCLUDE_CONFIGS
        ])
        rlog.info("config_scan: found %d configs", len(config_dirs))

        scanned = 0
        for config_dir in config_dirs:
            config_name = config_dir.name
            result = analyze_config(config_name, config_dir, settings, model, db)
            scanned += 1

            if result:
                db.upsert_infrastructure(
                    role_name=config_name,
                    fqcn=None,
                    collection=repo["name"],
                    type="config",
                    description=result.get("description"),
                    products=result.get("products", []),
                    capabilities=result.get("capabilities", []),
                    category=result.get("category"),
                    requires=result.get("requires", []),
                    source_sha=local_sha,
                )

        return {"status": "scanned", "configs_found": len(config_dirs), "configs_scanned": scanned}

    finally:
        shutil.rmtree(clone_path, ignore_errors=True)
```

- [ ] **Step 4: Run tests**

Run: `cd src/api && python -m pytest tests/test_config_scanner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/workload_scanner.py src/api/tests/test_config_scanner.py
git commit -m "[JIRA-KEY] Add config scanner for AgnosticD v2 base configs"
```

---

### Task 4: Generate embeddings for infrastructure rows

**Files:**
- Modify: `src/api/rcars/services/analyzer.py` (add `build_infrastructure_embedding_text()`)
- Modify: `src/api/rcars/workers/ops.py` (add embedding generation step after scans)
- Modify: `src/api/rcars/db/database.py` (add `get_infrastructure_needing_embeddings()`)

**Interfaces:**
- Consumes: `infrastructure` table from Task 1, `generate_embedding()` and `store_embedding()` from existing code
- Produces: `build_infrastructure_embedding_text(row) -> str`, infrastructure embeddings stored in `embeddings` table with `content_type='infrastructure'`

- [ ] **Step 1: Write failing test for embedding text builder**

```python
# tests/test_infra_embeddings.py
from rcars.services.analyzer import build_infrastructure_embedding_text


def test_build_infrastructure_embedding_text():
    row = {
        "role_name": "ocp4_workload_rhods",
        "description": "Installs OpenShift AI with KServe support.",
        "products": ["OpenShift AI", "KServe"],
        "capabilities": ["model-serving", "notebook-hosting"],
        "category": "ai_ml",
    }
    text = build_infrastructure_embedding_text(row)
    assert "OpenShift AI" in text
    assert "KServe" in text
    assert "model-serving" in text
    assert "ai_ml" in text
    assert "ocp4_workload_rhods" in text


def test_build_infrastructure_embedding_text_minimal():
    row = {
        "role_name": "namespace",
        "description": None,
        "products": [],
        "capabilities": [],
        "category": None,
    }
    text = build_infrastructure_embedding_text(row)
    assert "namespace" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/api && python -m pytest tests/test_infra_embeddings.py -v`
Expected: FAIL — `build_infrastructure_embedding_text` not found

- [ ] **Step 3: Implement embedding text builder**

Add to `analyzer.py` after `build_module_embedding_text()` (line ~590):

```python
def build_infrastructure_embedding_text(row: dict[str, Any]) -> str:
    """Build text for infrastructure embedding from an infrastructure table row."""
    parts = []
    if row.get("description"):
        parts.append(row["description"])
    for field in ("products", "capabilities"):
        val = row.get(field, [])
        if isinstance(val, list):
            parts.extend(val)
    if row.get("category"):
        parts.append(row["category"])
    parts.append(row["role_name"])
    return " ".join(str(p) for p in parts if p)
```

- [ ] **Step 4: Add db method to find infrastructure needing embeddings**

Add to `Database`:

```python
def get_infrastructure_needing_embeddings(self) -> list[dict]:
    """Return infrastructure rows that have been scanned more recently than their embedding."""
    with self._pool.connection() as conn:
        cur = conn.execute("""
            SELECT i.* FROM infrastructure i
            LEFT JOIN embeddings e ON e.content_id = i.role_name
                AND e.content_type = 'infrastructure' AND e.embed_type = 'summary'
            WHERE e.id IS NULL AND i.description IS NOT NULL
        """)
        return cur.fetchall()
```

Note: The `embeddings` table has a FK to `content_entities(content_id)`. Infrastructure rows are NOT content entities — they don't have a `content_id` in `content_entities`. We need to handle this. Two options:
1. Remove the FK constraint on `embeddings.content_id` (breaking change, not recommended)
2. Store infrastructure embeddings in a separate column or use a sentinel approach

**Best approach:** Add `ON DELETE CASCADE` is already there, but the FK itself means we can't insert an embedding with `content_id = 'ocp4_workload_rhods'` unless that exists in `content_entities`. The cleanest fix: make the FK optional by dropping it and relying on application-level integrity, OR create a parallel `infrastructure_embeddings` table.

**Simplest approach:** Use the existing `embeddings` table but drop the FK constraint. Add `ALTER TABLE embeddings DROP CONSTRAINT IF EXISTS embeddings_content_id_fkey` to schema. This is consistent with the spec's intent ("Infrastructure embeddings go into the existing shared embeddings table").

Add to `SCHEMA_SQL` after the infrastructure table DDL:

```sql
-- Allow infrastructure embeddings (no content_entities row)
ALTER TABLE embeddings DROP CONSTRAINT IF EXISTS embeddings_content_id_fkey;
```

- [ ] **Step 5: Add infrastructure embedding generation to nightly pipeline**

In `ops.py`, after the workload scan step (Step 4, ~line 364) and before sandbox summary (Step 4b), add:

```python
# Step 4a: Generate embeddings for new/updated infrastructure
try:
    from rcars.services.analyzer import build_infrastructure_embedding_text, generate_embedding
    infra_rows = wctx.db.get_infrastructure_needing_embeddings()
    if infra_rows:
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="pipeline:infra_embeddings", status="running",
                               message=f"Step 4a: Generating embeddings for {len(infra_rows)} infrastructure items...")
        embedded = 0
        for row in infra_rows:
            text = build_infrastructure_embedding_text(row)
            if text.strip():
                emb = generate_embedding(text, prefix="search_document")
                wctx.db.store_embedding(
                    content_id=row["role_name"],
                    content_type="infrastructure",
                    source="agnosticd",
                    embed_type="summary",
                    content_text=text,
                    embedding=emb,
                )
                embedded += 1
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="pipeline:infra_embeddings", status="complete",
                               message=f"Step 4a complete: {embedded} infrastructure embeddings generated")
    else:
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="pipeline:infra_embeddings", status="complete",
                               message="Step 4a complete: All infrastructure embeddings current")
except Exception as e:
    msg = f"Step 4a failed (infrastructure embeddings): {e}"
    warnings.append(msg)
    log.error("pipeline_infra_embeddings_failed", action="pipeline_step_failed",
              step="infra_embeddings", error=str(e), traceback=traceback.format_exc())
```

- [ ] **Step 6: Run tests**

Run: `cd src/api && python -m pytest tests/test_infra_embeddings.py tests/test_infrastructure.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/services/analyzer.py src/api/rcars/workers/ops.py src/api/rcars/db/database.py src/api/tests/test_infra_embeddings.py
git commit -m "[JIRA-KEY] Generate embeddings for infrastructure catalog entries"
```

---

### Task 5: Add config scan to nightly pipeline

**Files:**
- Modify: `src/api/rcars/workers/ops.py:336-364` (nightly pipeline Step 4 area)

**Interfaces:**
- Consumes: `scan_configs(clone_dir, settings, model, db, force)` from Task 3
- Produces: configs scanned as part of the nightly pipeline, between workload scan and embedding generation

- [ ] **Step 1: Write failing test for config scan pipeline step**

```python
# tests/test_pipeline_config_scan.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from rcars.workers.ops import run_nightly_pipeline


@pytest.mark.asyncio
async def test_nightly_pipeline_includes_config_scan(mock_worker_ctx):
    """The nightly pipeline should call scan_configs after workload scan."""
    with patch("rcars.workers.ops.run_catalog_refresh", new_callable=AsyncMock) as mock_refresh, \
         patch("rcars.workers.ops.run_stale_check", new_callable=AsyncMock) as mock_stale, \
         patch("rcars.workers.ops.run_workload_scan", new_callable=AsyncMock) as mock_wl_scan, \
         patch("rcars.services.workload_scanner.scan_configs") as mock_config_scan, \
         patch("rcars.workers.ops.run_sandbox_summary", new_callable=AsyncMock):
        mock_refresh.return_value = {"total_items": 0, "retired_items": 0}
        mock_stale.return_value = {"checked": 0, "skipped": 0, "stale": 0, "stale_cis": 0}
        mock_wl_scan.return_value = {"collections": []}
        mock_config_scan.return_value = {"status": "scanned", "configs_scanned": 5}

        await run_nightly_pipeline(mock_worker_ctx)

        mock_config_scan.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/api && python -m pytest tests/test_pipeline_config_scan.py -v`
Expected: FAIL — pipeline doesn't call `scan_configs`

- [ ] **Step 3: Add config scan step to nightly pipeline**

In `ops.py`, after Step 4 (workload repo scan, ~line 364) and before Step 4a (infrastructure embeddings from Task 4), add:

```python
# Step 4 (continued): Config scan
if wctx.settings.workload_scan_enabled:
    try:
        from rcars.services.workload_scanner import scan_configs
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="pipeline:config_scan", status="running",
                               message="Step 4 (config): Scanning AgnosticD v2 configs...")
        import asyncio
        config_result = await asyncio.to_thread(
            scan_configs, "/tmp", wctx.settings,
            wctx.settings.scanning_model or "claude-sonnet-4-6",
            wctx.db, force=False,
        )
        scanned = config_result.get("configs_scanned", 0)
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="pipeline:config_scan", status="complete",
                               message=f"Step 4 (config) complete: {scanned} configs scanned")
        log.info("pipeline_config_scan_complete", action="pipeline_step_complete",
                 step="config_scan", **config_result)
    except Exception as e:
        msg = f"Step 4 (config scan) failed: {e}"
        warnings.append(msg)
        log.error("pipeline_config_scan_failed", action="pipeline_step_failed",
                  step="config_scan", error=str(e), traceback=traceback.format_exc())
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="pipeline:config_scan", status="failed", message=msg)
```

- [ ] **Step 4: Run tests**

Run: `cd src/api && python -m pytest tests/test_pipeline_config_scan.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/workers/ops.py src/api/tests/test_pipeline_config_scan.py
git commit -m "[JIRA-KEY] Add config scan step to nightly pipeline"
```

---

### Task 6: Update sandbox_summary.py to read from infrastructure table

**Files:**
- Modify: `src/api/rcars/services/sandbox_summary.py`
- Modify: `src/api/rcars/db/database.py` (update `get_workload_classifications`)

**Interfaces:**
- Consumes: `db.get_workload_classifications(content_id)` — modify to read from `infrastructure` instead of `workload_mapping`
- Produces: `sandbox_summary.py` works identically but sources product data from `infrastructure` table

- [ ] **Step 1: Write failing test**

```python
# tests/test_sandbox_summary_infra.py
from rcars.services.sandbox_summary import build_sandbox_summary


def test_sandbox_summary_with_infrastructure_products():
    """build_sandbox_summary should work with richer product data from infrastructure table."""
    workload_products = [
        {"product_name": "OpenShift AI", "description": "RHOAI operator", "category": "ai_ml"},
        {"product_name": "KServe", "description": "Model serving", "category": "ai_ml"},
    ]
    result = build_sandbox_summary(
        display_name="AI Sandbox", description="An AI-ready sandbox",
        cloud_provider="AWS", ocp_version="4.20",
        agd_config="openshift-cluster", workload_products=workload_products,
    )
    assert "OpenShift AI" in result["summary"]
    assert "KServe" in result["summary"]
    assert "ai_ml" in result["topics_json"]
```

- [ ] **Step 2: Run test to verify it passes (sandbox_summary.py doesn't need structural changes)**

Run: `cd src/api && python -m pytest tests/test_sandbox_summary_infra.py -v`
Expected: PASS — `build_sandbox_summary` is a pure function that takes workload_products dicts, it doesn't care where they came from

- [ ] **Step 3: Update get_workload_classifications to read from infrastructure**

In `database.py`, replace `get_workload_classifications()` (line 1347):

```python
def get_workload_classifications(self, content_id: str) -> list[dict]:
    sql = """
        SELECT i.products->0 AS product_name, i.description, i.category
        FROM babylon_item_workloads biw
        JOIN infrastructure i ON i.role_name = biw.workload_role AND i.type = 'workload'
        WHERE biw.content_id = %(content_id)s
    """
    with self._pool.connection() as conn:
        return conn.execute(sql, {"content_id": content_id}).fetchall()
```

Note: The old query joined `workload_mapping` and filtered `verified = TRUE`. With scanner-populated data, all rows are "verified" by default — no filter needed. The `products->0` extracts the first (primary) product name to maintain the same `product_name` key the caller expects.

- [ ] **Step 4: Run existing sandbox summary tests + new test**

Run: `cd src/api && python -m pytest tests/test_sandbox_summary_infra.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/database.py src/api/tests/test_sandbox_summary_infra.py
git commit -m "[JIRA-KEY] Update workload classifications to read from infrastructure table"
```

---

### Task 7: Replace API endpoints — remove old CRUD, add infrastructure endpoint

**Files:**
- Modify: `src/api/rcars/api/routes/catalog.py:159-217` (remove old endpoints, add new)
- Modify: `src/api/rcars/services/chat/handlers.py:36` (update `get_item_workloads` to use infrastructure)

**Interfaces:**
- Consumes: `db.get_infrastructure_with_item_counts(...)`, `db.list_infrastructure(...)` from Task 1
- Produces: `GET /catalog/infrastructure` endpoint replacing `GET /catalog/workload-mappings`; removed `POST /catalog/workload-mappings`, `DELETE /catalog/workload-mappings/{role}`, `GET /catalog/workload-mappings/unmapped`

- [ ] **Step 1: Write failing test for new infrastructure endpoint**

```python
# tests/test_api_infrastructure.py
import pytest


@pytest.mark.asyncio
async def test_get_infrastructure(async_client, seed_infrastructure):
    resp = await async_client.get("/api/v1/catalog/infrastructure")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) > 0
    assert "item_count" in data["items"][0]


@pytest.mark.asyncio
async def test_get_infrastructure_type_filter(async_client, seed_infrastructure):
    resp = await async_client.get("/api/v1/catalog/infrastructure?type=workload")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["type"] == "workload"


@pytest.mark.asyncio
async def test_old_workload_mappings_removed(async_client):
    resp = await async_client.post("/api/v1/catalog/workload-mappings",
                                   json={"workload_role": "x", "product_name": "y"})
    assert resp.status_code in (404, 405)

    resp = await async_client.delete("/api/v1/catalog/workload-mappings/x")
    assert resp.status_code in (404, 405)

    resp = await async_client.get("/api/v1/catalog/workload-mappings/unmapped")
    assert resp.status_code in (404, 405)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/api && python -m pytest tests/test_api_infrastructure.py -v`
Expected: FAIL — old endpoints still exist, new endpoint doesn't

- [ ] **Step 3: Remove old endpoints, add new infrastructure endpoint**

In `catalog.py`, remove the following endpoints:
- `list_workload_mappings()` (line 165)
- `list_unmapped_workloads()` (line 176)
- `WorkloadMappingRequest` model (line 181)
- `add_workload_mapping()` (line 194)
- `delete_workload_mapping()` (line 214)

Replace with:

```python
@router.get(
    "/infrastructure",
    summary="List infrastructure catalog",
    description=(
        "Returns the infrastructure catalog (workload roles and base configs) "
        "with item counts showing how many catalog items use each entry."
    ),
)
async def list_infrastructure(
    request: Request,
    user: str = Depends(require_auth),
    type: str | None = Query(None, description="Filter by type: 'workload' or 'config'"),
    category: str | None = Query(None, description="Filter by category"),
    collection: str | None = Query(None, description="Filter by collection"),
    search: str | None = Query(None, description="Search across role name, description, products, capabilities"),
    has_mappings: bool | None = Query(None, description="True = only with linked CIs, False = orphans only"),
    limit: int = Query(500, le=1000),
):
    db = request.app.state.db
    items = db.get_infrastructure_with_item_counts(
        type_filter=type, category_filter=category,
        collection_filter=collection, search=search,
        has_mappings=has_mappings, limit=limit,
    )
    return {"items": items, "total": len(items)}
```

Also update `get_catalog_facets()` in `database.py` to source workload product names from `infrastructure` instead of `workload_mapping`:

```python
# In get_catalog_facets(), replace the workloads query:
cur = conn.execute("""
    SELECT i.role_name, i.products, i.category, COUNT(DISTINCT biw.content_id) AS ci_count
    FROM infrastructure i
    JOIN babylon_item_workloads biw ON biw.workload_role = i.role_name
    JOIN babylon_items bi ON bi.content_id = biw.content_id AND bi.is_prod = TRUE
    JOIN content_entities ce ON ce.content_id = bi.content_id AND ce.retired_at IS NULL
    WHERE i.type = 'workload'
    GROUP BY i.role_name, i.products, i.category
    ORDER BY ci_count DESC
""")
```

And update `get_infra_stats()` to use `infrastructure` instead of `workload_mapping`:

```python
def get_infra_stats(self) -> dict:
    with self._pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS count FROM babylon_items bi "
                "JOIN content_entities ce ON ce.content_id = bi.content_id "
                "WHERE bi.is_agd_v2 = TRUE AND ce.retired_at IS NULL"
            )
            v2_items = cur.fetchone()["count"]
            cur.execute(
                "SELECT COUNT(DISTINCT biw.content_id) AS count FROM babylon_item_workloads biw "
                "JOIN content_entities ce ON ce.content_id = biw.content_id WHERE ce.retired_at IS NULL"
            )
            with_workloads = cur.fetchone()["count"]
            cur.execute("SELECT COUNT(*) AS count FROM infrastructure WHERE type = 'workload'")
            workload_count = cur.fetchone()["count"]
            cur.execute("SELECT COUNT(*) AS count FROM infrastructure WHERE type = 'config'")
            config_count = cur.fetchone()["count"]
    return {
        "v2_items": v2_items,
        "with_workloads": with_workloads,
        "infrastructure_workloads": workload_count,
        "infrastructure_configs": config_count,
    }
```

- [ ] **Step 4: Update search_by_infrastructure to join infrastructure instead of workload_mapping**

In `database.py`, `search_by_infrastructure()` (line 1518), replace the workloads join logic:

```python
if workloads:
    resolved = self._resolve_workload_aliases(workloads)
    for i, wl in enumerate(resolved):
        alias_w = f"w{i}"
        alias_i = f"i{i}"
        joins.append(
            f"JOIN babylon_item_workloads {alias_w} "
            f"ON {alias_w}.content_id = ce.content_id "
            f"JOIN infrastructure {alias_i} "
            f"ON {alias_i}.role_name = {alias_w}.workload_role "
            f"AND {alias_i}.type = 'workload' "
            f"AND {alias_i}.products @> %({alias_i}_name)s::jsonb"
        )
        params[f"{alias_i}_name"] = json.dumps([wl])
```

- [ ] **Step 5: Run tests**

Run: `cd src/api && python -m pytest tests/test_api_infrastructure.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/api/routes/catalog.py src/api/rcars/db/database.py src/api/tests/test_api_infrastructure.py
git commit -m "[JIRA-KEY] Replace workload mapping endpoints with infrastructure catalog API"
```

---

### Task 8: Remove old CLI commands and seed data

**Files:**
- Modify: `src/api/rcars/cli.py:483-632` (workload subgroup)
- Delete: `src/api/rcars/data/workload_mapping.yaml`

**Interfaces:**
- Consumes: `scan_configs()` from Task 3
- Produces: `rcars workload` subgroup with only `scan` and `list` commands; old `sync`, `unmapped`, `map`, `alias` commands removed; `scan` command gains `--include-configs` flag

- [ ] **Step 1: Update CLI — remove dead commands, update scan**

In `cli.py`, remove these commands from the `workload_group`:
- `workload_sync` (line 489) — loaded from YAML seed file, no longer needed
- `workload_unmapped` (line 536) — unmapped concept gone
- `workload_map` (line 557) — manual mapping gone
- `workload_alias` (line 573) — keep as-is (aliases still used for query resolution)

Update `workload_scan` to add `--include-configs`:

```python
@workload_group.command("scan")
@click.option("--collection", "-c", default=None, help="Scan only this collection")
@click.option("--force", is_flag=True, default=False, help="Skip SHA check, rescan everything")
@click.option("--include-configs", is_flag=True, default=False, help="Also scan AgnosticD v2 base configs")
def workload_scan(collection: str | None, force: bool, include_configs: bool):
    """Scan agDv2 workload repos and optionally base configs via LLM."""
    from rcars.services.workload_scanner import scan_all_collections, scan_configs
    # ... existing setup ...
    results = scan_all_collections("/tmp", settings, model, db, force=force, collection_filter=collection)
    # ... existing result display ...
    if include_configs:
        console.print("\n[bold]Scanning base configs...[/bold]")
        config_result = scan_configs("/tmp", settings, model, db, force=force)
        console.print(f"Configs: {config_result}")
    db.close()
```

Update `workload_list` to show infrastructure table data instead of `workload_mapping`:

```python
@workload_group.command("list")
def workload_list():
    """List infrastructure catalog entries."""
    db = get_db()
    rows = db.list_infrastructure()
    table = Table(title=f"Infrastructure Catalog ({len(rows)})")
    table.add_column("Role Name", style="cyan")
    table.add_column("Type")
    table.add_column("Products")
    table.add_column("Category")
    table.add_column("Collection")
    for row in rows:
        products = ", ".join(row.get("products") or [])
        table.add_row(
            row["role_name"], row["type"],
            products[:60], row.get("category") or "—",
            row.get("collection") or "—",
        )
    console.print(table)
    db.close()
```

- [ ] **Step 2: Delete seed data file**

```bash
rm src/api/rcars/data/workload_mapping.yaml
```

- [ ] **Step 3: Run CLI help to verify commands are correct**

Run: `cd src/api && python -m rcars workload --help`
Expected: Shows `scan`, `list`, `alias` commands only — no `sync`, `unmapped`, `map`

- [ ] **Step 4: Commit**

```bash
git add src/api/rcars/cli.py
git rm src/api/rcars/data/workload_mapping.yaml
git commit -m "[JIRA-KEY] Remove old workload CLI commands and seed data"
```

---

### Task 9: Remove old database methods and DDL

**Files:**
- Modify: `src/api/rcars/db/database.py`

**Interfaces:**
- Consumes: nothing new
- Produces: clean database layer with no references to `workload_mapping` or `workload_scan_state` (except the migration in `create_schema`)

- [ ] **Step 1: Remove old workload_mapping methods from Database class**

Remove these methods:
- `upsert_workload_mapping()` (line 1358)
- `delete_workload_mapping()` (line 1379)
- `list_workload_mappings()` (line 1387)
- `get_unmapped_workloads()` (line 1394)
- `get_scan_state()` (line 1588)
- `upsert_scan_state()` (line 1596)

Keep these (still used):
- `sync_workloads()` — writes to `babylon_item_workloads`, still needed
- `get_workloads()` — reads `babylon_item_workloads`, still needed
- `get_workload_classifications()` — updated in Task 6 to read from `infrastructure`
- `upsert_workload_alias()` — writes to `workload_aliases`, still needed
- `list_workload_aliases()` — reads `workload_aliases`, still needed
- `_resolve_workload_aliases()` — used by `search_by_infrastructure`, still needed

- [ ] **Step 2: Remove old DDL from SCHEMA_SQL**

Remove the `workload_mapping` table DDL (lines 302-313), `workload_scan_state` table DDL (lines 325-329), and their indexes (lines 322-323). Keep `workload_aliases` DDL (lines 315-320).

Add drop statements at the end of SCHEMA_SQL for cleanup:

```sql
-- Cleanup: drop replaced tables (safe after migration in create_schema)
DROP TABLE IF EXISTS workload_scan_state;
-- workload_mapping dropped after migration has run
```

Note: Don't drop `workload_mapping` in SCHEMA_SQL — the migration in `create_schema()` reads from it. Add the drop AFTER the migration code:

```python
# In create_schema(), after the migration INSERT:
conn.execute("DROP TABLE IF EXISTS workload_mapping CASCADE")
conn.commit()
```

- [ ] **Step 3: Run full test suite to catch any remaining references**

Run: `cd src/api && python -m pytest tests/ -v --ignore=tests/test_chat_live.py -m "not integration"`
Expected: PASS — no remaining references to removed methods

- [ ] **Step 4: Grep for remaining references and fix**

```bash
grep -rn "workload_mapping\|workload_scan_state\|list_workload_mappings\|get_unmapped_workloads\|upsert_workload_mapping\|delete_workload_mapping\|get_scan_state\|upsert_scan_state" src/api/rcars/ --include="*.py" | grep -v __pycache__ | grep -v ".pyc"
```

Fix any remaining references found.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/database.py
git commit -m "[JIRA-KEY] Remove workload_mapping and workload_scan_state DDL and methods"
```

---

### Task 10: Rebuild WorkloadsPage as infrastructure browse view

**Files:**
- Rewrite: `src/frontend/src/pages/WorkloadsPage.tsx`
- Modify: `src/frontend/src/services/api.ts` (replace workload API methods)

**Interfaces:**
- Consumes: `GET /catalog/infrastructure` API from Task 7
- Produces: read-only infrastructure browse page with filters, no CRUD actions

- [ ] **Step 1: Update api.ts — remove old methods, add new**

In `api.ts`, remove:
- `getWorkloadMappings()`
- `addWorkloadMapping()`
- `deleteWorkloadMapping()`
- `getUnmappedWorkloads()`

Replace with:

```typescript
getInfrastructureCatalog: (params?: {
  type?: string; category?: string; collection?: string;
  search?: string; has_mappings?: boolean; limit?: number;
}) => {
  const qs = new URLSearchParams();
  if (params?.type) qs.set('type', params.type);
  if (params?.category) qs.set('category', params.category);
  if (params?.collection) qs.set('collection', params.collection);
  if (params?.search) qs.set('search', params.search);
  if (params?.has_mappings !== undefined) qs.set('has_mappings', String(params.has_mappings));
  if (params?.limit) qs.set('limit', String(params.limit));
  return request<{
    items: Array<{
      role_name: string; fqcn: string | null; collection: string | null;
      type: string; description: string | null;
      products: string[]; capabilities: string[];
      category: string | null; requires: string[];
      source_sha: string | null; scanned_at: string | null;
      item_count: number;
    }>;
    total: number;
  }>(`/catalog/infrastructure?${qs}`);
},
```

- [ ] **Step 2: Rewrite WorkloadsPage.tsx**

Complete rewrite — the page becomes a read-only browse view. Use the same `browse-layout` CSS patterns already used by BrowsePage for consistency.

```tsx
import { useState, useCallback, useMemo, useEffect } from 'react'
import { api } from '../services/api'

interface InfrastructureItem {
  role_name: string
  fqcn: string | null
  collection: string | null
  type: string
  description: string | null
  products: string[]
  capabilities: string[]
  category: string | null
  requires: string[]
  scanned_at: string | null
  item_count: number
}

export function WorkloadsPage() {
  const [items, setItems] = useState<InfrastructureItem[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())

  // Filters
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [collectionFilter, setCollectionFilter] = useState('')
  const [mappingsFilter, setMappingsFilter] = useState<string>('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getInfrastructureCatalog()
      setItems(data.items)
      setLoaded(true)
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  useEffect(() => { loadData() }, [loadData])

  // Derived filter options
  const uniqueCategories = useMemo(() => {
    const cats = new Set<string>()
    items.forEach(i => { if (i.category) cats.add(i.category) })
    return Array.from(cats).sort()
  }, [items])

  const uniqueCollections = useMemo(() => {
    const colls = new Set<string>()
    items.forEach(i => { if (i.collection) colls.add(i.collection) })
    return Array.from(colls).sort()
  }, [items])

  // Client-side filtering
  const searchLower = search.toLowerCase()
  const filtered = useMemo(() => {
    return items.filter(i => {
      if (searchLower && !(
        i.role_name.toLowerCase().includes(searchLower) ||
        (i.description && i.description.toLowerCase().includes(searchLower)) ||
        i.products.some(p => p.toLowerCase().includes(searchLower)) ||
        i.capabilities.some(c => c.toLowerCase().includes(searchLower))
      )) return false
      if (typeFilter && i.type !== typeFilter) return false
      if (categoryFilter && i.category !== categoryFilter) return false
      if (collectionFilter && i.collection !== collectionFilter) return false
      if (mappingsFilter === 'with' && i.item_count === 0) return false
      if (mappingsFilter === 'without' && i.item_count > 0) return false
      return true
    })
  }, [items, searchLower, typeFilter, categoryFilter, collectionFilter, mappingsFilter])

  const handleExpand = (name: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  // Active filter chips
  const activeFilters: Array<{ label: string; onRemove: () => void }> = []
  if (typeFilter) activeFilters.push({ label: `Type: ${typeFilter}`, onRemove: () => setTypeFilter('') })
  if (categoryFilter) activeFilters.push({ label: `Category: ${categoryFilter}`, onRemove: () => setCategoryFilter('') })
  if (collectionFilter) activeFilters.push({ label: `Collection: ${collectionFilter}`, onRemove: () => setCollectionFilter('') })
  if (mappingsFilter) activeFilters.push({ label: mappingsFilter === 'with' ? 'Has CIs' : 'No CIs', onRemove: () => setMappingsFilter('') })

  if (loading && !loaded) {
    return (
      <div className="browse-layout">
        <div className="browse-toolbar">
          <span className="browse-loading">Loading infrastructure catalog...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="browse-layout">
      <div className="browse-toolbar">
        <input
          type="text" className="browse-search"
          placeholder="Search by role, description, products, capabilities..."
          value={search} onChange={(e) => setSearch(e.target.value)}
        />
        {activeFilters.length > 0 && (
          <>
            <div className="browse-toolbar-divider" />
            {activeFilters.map(f => (
              <span key={f.label} className="browse-chip" onClick={f.onRemove}>
                {f.label} <span className="browse-chip-x">&times;</span>
              </span>
            ))}
            <button className="browse-chip browse-chip--clear"
              onClick={() => { setTypeFilter(''); setCategoryFilter(''); setCollectionFilter(''); setMappingsFilter('') }}>
              Clear all
            </button>
          </>
        )}
        <span className="browse-item-count">{filtered.length} items</span>
      </div>

      <div className="browse-content">
        <div className="browse-filter-sidebar">
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Type</div>
            <div className="wl-status-pills">
              {['', 'workload', 'config'].map(t => (
                <button key={t || 'all'}
                  className={`browse-curator-pill${typeFilter === t ? ' active' : ''}`}
                  onClick={() => setTypeFilter(t)}>
                  {t ? t.charAt(0).toUpperCase() + t.slice(1) : 'All'}
                </button>
              ))}
            </div>
          </div>
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Category</div>
            <select className="browse-filter-select" value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}>
              <option value="">All categories</option>
              {uniqueCategories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Collection</div>
            <select className="browse-filter-select" value={collectionFilter}
              onChange={(e) => setCollectionFilter(e.target.value)}>
              <option value="">All collections</option>
              {uniqueCollections.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Catalog Items</div>
            <div className="wl-status-pills">
              {[['', 'All'], ['with', 'Has CIs'], ['without', 'Orphans']].map(([v, l]) => (
                <button key={v}
                  className={`browse-curator-pill${mappingsFilter === v ? ' active' : ''}`}
                  onClick={() => setMappingsFilter(v)}>
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="browse-list">
          {filtered.length === 0 ? (
            <div className="wl-empty">No infrastructure items match the current filters.</div>
          ) : filtered.map(item => {
            const isExpanded = expandedItems.has(item.role_name)
            return (
              <div key={item.role_name} className={`browse-item${isExpanded ? ' expanded' : ''}`}>
                <div className="browse-item-header">
                  <div className="browse-item-header-left">
                    <div className="browse-item-title" onClick={() => handleExpand(item.role_name)}
                      role="button" tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleExpand(item.role_name) } }}>
                      <span className="browse-expand-icon">{isExpanded ? '▼' : '▶'}</span>
                      <span className="wl-role-name">{item.role_name}</span>
                      <span className={`stage-badge stage-badge--${item.type === 'config' ? 'prod' : 'dev'}`}>
                        {item.type}
                      </span>
                      {item.item_count > 0 && (
                        <span className="wl-ci-count-badge">
                          Used by {item.item_count} item{item.item_count !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="browse-item-body" onClick={(e) => e.stopPropagation()}>
                    {item.description && <p className="browse-description">{item.description}</p>}

                    {item.products.length > 0 && (
                      <div className="browse-pills">
                        {item.products.map(p => (
                          <span key={p} className="browse-pill browse-pill--product">{p}</span>
                        ))}
                      </div>
                    )}

                    {item.capabilities.length > 0 && (
                      <div className="browse-pills">
                        {item.capabilities.map(c => (
                          <span key={c} className="browse-pill browse-pill--topic">{c}</span>
                        ))}
                      </div>
                    )}

                    <div className="wl-detail-grid">
                      <div className="wl-detail-item">
                        <span className="wl-detail-label">Category</span>
                        <span className="wl-detail-value">{item.category || '—'}</span>
                      </div>
                      <div className="wl-detail-item">
                        <span className="wl-detail-label">Collection</span>
                        <span className="wl-detail-value">{item.collection || '—'}</span>
                      </div>
                      {item.fqcn && (
                        <div className="wl-detail-item">
                          <span className="wl-detail-label">FQCN</span>
                          <span className="wl-detail-value">{item.fqcn}</span>
                        </div>
                      )}
                      {item.requires.length > 0 && (
                        <div className="wl-detail-item">
                          <span className="wl-detail-label">Requires</span>
                          <span className="wl-detail-value">{item.requires.join(', ')}</span>
                        </div>
                      )}
                      {item.scanned_at && (
                        <div className="wl-detail-item">
                          <span className="wl-detail-label">Last scanned</span>
                          <span className="wl-detail-value">
                            {new Date(item.scanned_at).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify frontend builds**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 4: Start dev server and test the page**

Run: `cd /Users/nstephan/devel/rcars-advisory && ./dev-services.sh start`

Test in browser at http://localhost:3000:
1. Navigate to the Workloads page
2. Verify it loads and shows infrastructure items (may be empty if scanner hasn't run)
3. Verify type filter (All / Workload / Config) works
4. Verify category and collection dropdowns populate
5. Verify search filters across role names, descriptions, products
6. Verify expand/collapse shows full details with products/capabilities pills
7. Verify no CRUD buttons exist (no "Map this workload", "Remove mapping")

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/pages/WorkloadsPage.tsx src/frontend/src/services/api.ts
git commit -m "[JIRA-KEY] Rebuild Workloads page as read-only infrastructure catalog browser"
```

---

### Task 11: Update existing tests and final cleanup

**Files:**
- Modify: `src/api/tests/test_app.py` (if workload endpoint tests exist)
- Modify: `src/api/tests/test_db.py` (if workload mapping tests exist)
- Modify: `src/api/tests/test_workers.py` (if workload scan tests exist)

**Interfaces:**
- Consumes: all prior tasks
- Produces: passing test suite, no references to removed methods/tables

- [ ] **Step 1: Find and fix broken tests**

```bash
cd src/api && python -m pytest tests/ -v --ignore=tests/test_chat_live.py -m "not integration" 2>&1 | head -100
```

Fix any failures caused by:
- References to `db.upsert_workload_mapping()`, `db.delete_workload_mapping()`, `db.list_workload_mappings()`, `db.get_unmapped_workloads()`, `db.get_scan_state()`, `db.upsert_scan_state()`
- References to `api.addWorkloadMapping()`, `api.deleteWorkloadMapping()`, `api.getUnmappedWorkloads()`
- References to `/catalog/workload-mappings` endpoints
- Missing `infrastructure` table in test fixtures

For each broken test: if it tests old CRUD behavior that no longer exists, delete it. If it tests infrastructure search or facets, update it to use the new table/methods.

- [ ] **Step 2: Grep for any remaining references to removed code**

```bash
grep -rn "workload_mapping\b\|workload_scan_state\|upsert_workload_mapping\|delete_workload_mapping\|list_workload_mappings\|get_unmapped_workloads\|addWorkloadMapping\|deleteWorkloadMapping\|getUnmappedWorkloads\|getWorkloadMappings" src/ --include="*.py" --include="*.ts" --include="*.tsx" | grep -v __pycache__ | grep -v node_modules | grep -v ".pyc"
```

Fix any remaining references. This grep should return zero results (aside from migration code in `create_schema` and possibly test migration helpers).

- [ ] **Step 3: Run full test suite**

Run: `cd src/api && python -m pytest tests/ -v --ignore=tests/test_chat_live.py -m "not integration"`
Expected: All tests PASS

- [ ] **Step 4: Run frontend build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "[JIRA-KEY] Update tests and remove all references to old workload mapping system"
```

---

## Verification Checklist

After all tasks are complete, verify:

1. `infrastructure` table exists with both workload and config entries
2. `workload_mapping` and `workload_scan_state` tables are dropped
3. `workload_aliases` table still exists and works
4. `babylon_item_workloads` join table unchanged
5. `GET /catalog/infrastructure` returns items with `item_count`
6. Old CRUD endpoints return 404
7. Workloads page renders as read-only browse view
8. `rcars workload scan --include-configs` works
9. Nightly pipeline runs workload scan → config scan → embeddings → sandbox summary
10. All tests pass
