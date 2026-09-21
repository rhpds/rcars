# Field Source Content Report — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only "Field Source Content" report page under the Analysis menu showing which git repos are used with the Field Sourced Content catalog items (OCP and RHEL), with expandable rows for individual provision dates.

**Architecture:** Data flows from the Reporting DB MCP → sync job (reusing existing `mcp_query()`) → local `field_source_provisions` table → API endpoint → React frontend page. Follows the same pattern as the Performance page.

**Tech Stack:** Python/FastAPI (backend), PostgreSQL (storage), React/TypeScript/PatternFly 6 (frontend)

**Spec:** Jira [RHDPCD-2028](https://redhat.atlassian.net/browse/RHDPCD-2028). Handoff: `ai-handoffs/2026-09-21-field-source-content-report.md`

## Global Constraints

- No PII — do not store or serve user emails or names
- Fixed 12-month rolling window — no configurable time ranges
- Two catalog items: OCP field asset (`published.ocp-field-asset`, catalog_items.id = 1969802) and RHEL field asset (discover catalog_id during Task 2)
- Auth: visible to all authenticated users (`require_auth`)
- Reuse `mcp_query()` from `reporting_sync.py` — do not duplicate
- JSONB field for OCP git repo: `resource_claim_log.resource_claim_json -> 'spec' -> 'provider' -> 'parameterValues' ->> 'ocp4_workload_field_content_gitops_repo_url'`
- RHEL git repo JSONB field name must be discovered (may differ from OCP)

---

### Task 1: Database Schema and Methods

**Files:**
- Modify: `src/api/rcars/db/database.py` (SCHEMA_SQL ~line 190, methods ~line 2800)
- Test: `src/api/tests/test_field_source_db.py`

**Interfaces:**
- Consumes: nothing (foundation task)
- Produces: `Database.upsert_field_source_provisions(rows: list[dict]) -> int`, `Database.get_field_source_summary(catalog_item: str | None = None) -> list[dict]`, `Database.delete_field_source_provisions() -> int`

- [ ] **Step 1: Add CREATE TABLE to SCHEMA_SQL**

Add after the `performance_scores` table definition (~line 210):

```sql
CREATE TABLE IF NOT EXISTS field_source_provisions (
    id SERIAL PRIMARY KEY,
    catalog_item TEXT NOT NULL,
    git_repo TEXT NOT NULL,
    git_ref TEXT,
    provisioned_at TIMESTAMPTZ NOT NULL,
    retired_at TIMESTAMPTZ,
    provision_uuid TEXT NOT NULL UNIQUE,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fsp_catalog_item ON field_source_provisions(catalog_item);
CREATE INDEX IF NOT EXISTS idx_fsp_git_repo ON field_source_provisions(git_repo);
```

`catalog_item` is `'ocp'` or `'rhel'`. `provision_uuid` is the unique key for dedup.

- [ ] **Step 2: Add `upsert_field_source_provisions` method**

Follow the `upsert_performance_channels` pattern (line 2747). Insert rows, ON CONFLICT(provision_uuid) DO UPDATE on retired_at and synced_at only (provision details don't change, but retired_at may update).

```python
def upsert_field_source_provisions(self, rows: list[dict]) -> int:
    sql = """
        INSERT INTO field_source_provisions
            (catalog_item, git_repo, git_ref, provisioned_at, retired_at, provision_uuid, synced_at)
        VALUES
            (%(catalog_item)s, %(git_repo)s, %(git_ref)s, %(provisioned_at)s, %(retired_at)s, %(provision_uuid)s, NOW())
        ON CONFLICT (provision_uuid) DO UPDATE SET
            retired_at = EXCLUDED.retired_at,
            synced_at = NOW()
    """
    with self.conn.cursor() as cur:
        for row in rows:
            cur.execute(sql, row)
    self.conn.commit()
    return len(rows)
```

- [ ] **Step 3: Add `delete_field_source_provisions` method**

For full-replace sync strategy (delete all, re-insert). Simple DELETE.

```python
def delete_field_source_provisions(self) -> int:
    with self.conn.cursor() as cur:
        cur.execute("DELETE FROM field_source_provisions")
        count = cur.fetchone() if cur.description else None
        self.conn.commit()
        return cur.rowcount
```

- [ ] **Step 4: Add `get_field_source_summary` method**

Returns rows grouped by repo+ref with aggregate stats, plus individual provision dates. Two queries: one for the summary rows, one for the detail rows. Or a single query with all rows — let the API layer group them.

```python
def get_field_source_summary(self, catalog_item: str | None = None, months: int = 12) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    sql = """
        SELECT catalog_item, git_repo, git_ref, provisioned_at, retired_at, provision_uuid
        FROM field_source_provisions
        WHERE provisioned_at >= %s
    """
    params: list = [cutoff]
    if catalog_item:
        sql += " AND catalog_item = %s"
        params.append(catalog_item)
    sql += " ORDER BY git_repo, git_ref, provisioned_at DESC"
    with self.conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchall()
```

- [ ] **Step 5: Write test for DB methods**

```python
# tests/test_field_source_db.py
import pytest
from datetime import datetime, timezone

def test_upsert_and_query_field_source(db):
    rows = [
        {"catalog_item": "ocp", "git_repo": "https://github.com/example/repo1",
         "git_ref": "main", "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "uuid-001"},
        {"catalog_item": "ocp", "git_repo": "https://github.com/example/repo1",
         "git_ref": "main", "provisioned_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
         "retired_at": datetime(2026, 7, 5, tzinfo=timezone.utc), "provision_uuid": "uuid-002"},
        {"catalog_item": "rhel", "git_repo": "https://github.com/example/repo2",
         "git_ref": "v1.0", "provisioned_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "uuid-003"},
    ]
    count = db.upsert_field_source_provisions(rows)
    assert count == 3

    # Query all
    results = db.get_field_source_summary()
    assert len(results) == 3

    # Filter by catalog_item
    ocp_results = db.get_field_source_summary(catalog_item="ocp")
    assert len(ocp_results) == 2
    assert all(r["catalog_item"] == "ocp" for r in ocp_results)

    # Dedup on re-upsert
    count = db.upsert_field_source_provisions(rows)
    assert count == 3
    results = db.get_field_source_summary()
    assert len(results) == 3  # still 3, not 6

def test_delete_field_source(db):
    rows = [{"catalog_item": "ocp", "git_repo": "https://github.com/example/repo1",
             "git_ref": "main", "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
             "retired_at": None, "provision_uuid": "uuid-del-001"}]
    db.upsert_field_source_provisions(rows)
    deleted = db.delete_field_source_provisions()
    assert deleted >= 1
    assert db.get_field_source_summary() == []
```

- [ ] **Step 6: Run tests**

```bash
cd src/api && python -m pytest tests/test_field_source_db.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/db/database.py src/api/tests/test_field_source_db.py
git commit -m "[RHDPCD-2028] Add field_source_provisions table and DB methods"
```

---

### Task 2: Reporting Sync Job

**Files:**
- Modify: `src/api/rcars/services/reporting_sync.py` (~line 730, after `run_reporting_sync`)
- Modify: `src/api/rcars/workers/ops.py` (pipeline step, ~line 450; standalone job, ~line 670)
- Modify: `src/api/rcars/workers/settings.py` (job registration, ~line 42)
- Test: `src/api/tests/test_field_source_sync.py`

**Interfaces:**
- Consumes: `Database.upsert_field_source_provisions(rows)` from Task 1, `mcp_query(sql, url, token)` from existing code
- Produces: `run_field_source_sync(db, settings) -> dict` (returns `{"ocp": n, "rhel": n, "total": n}`)

- [ ] **Step 1: Discover RHEL catalog item**

Before writing the sync function, query the reporting DB to find the RHEL field asset catalog item ID and its JSONB parameter name for the git repo URL. Use the reporting DB MCP tools:

```sql
SELECT id, name, display_name
FROM catalog_items
WHERE name LIKE '%field%' AND name LIKE '%rhel%'
ORDER BY id DESC LIMIT 5;
```

Also check what JSONB parameter keys exist for the RHEL item:

```sql
SELECT DISTINCT
  jsonb_object_keys(rcl.resource_claim_json->'spec'->'provider'->'parameterValues') AS param_key
FROM provisions p
JOIN resource_claim_log rcl ON rcl.provision_uuid = p.uuid
WHERE p.catalog_id = <rhel_catalog_id>
LIMIT 1;
```

Record the catalog ID and the git repo parameter name. If the RHEL item doesn't exist in prod yet, use the dev catalog_id for now and note it.

- [ ] **Step 2: Add `_build_field_source_sql` helper**

Add after the existing `_build_*_sql` helpers in `reporting_sync.py`:

```python
FIELD_SOURCE_ITEMS = {
    "ocp": {"catalog_id": 1969802, "repo_param": "ocp4_workload_field_content_gitops_repo_url"},
    "rhel": {"catalog_id": <DISCOVERED_ID>, "repo_param": "<DISCOVERED_PARAM>"},
}

def _build_field_source_sql(catalog_id: int, repo_param: str) -> str:
    return f"""
        SELECT
          rcl.resource_claim_json->'spec'->'provider'->'parameterValues'->>'{repo_param}' AS git_repo,
          rcl.resource_claim_json->'spec'->'provider'->'parameterValues'->>'git_ref' AS git_ref,
          p.provisioned_at,
          p.retired_at,
          p.uuid AS provision_uuid
        FROM provisions p
        JOIN resource_claim_log rcl ON rcl.provision_uuid = p.uuid
        WHERE p.catalog_id = {catalog_id}
          AND p.environment = 'PROD'
          AND p.provisioned_at >= NOW() - INTERVAL '12 months'
        ORDER BY p.provisioned_at DESC
    """
```

Note: the `git_ref` parameter name may differ — discover in Step 1. If it doesn't exist as a separate param, it may be embedded in the repo URL or not available. Adjust accordingly.

- [ ] **Step 3: Add `run_field_source_sync` function**

```python
def run_field_source_sync(db, settings) -> dict:
    url = settings.reporting_mcp_url
    token = settings.reporting_mcp_token
    if not url or not token:
        return {"error": "reporting MCP not configured"}

    results = {}
    all_rows = []
    for item_key, item_cfg in FIELD_SOURCE_ITEMS.items():
        sql = _build_field_source_sql(item_cfg["catalog_id"], item_cfg["repo_param"])
        rows = mcp_query(sql, url, token)
        for row in rows:
            row["catalog_item"] = item_key
        all_rows.extend(rows)
        results[item_key] = len(rows)

    # Full replace: delete old, insert new
    db.delete_field_source_provisions()
    if all_rows:
        db.upsert_field_source_provisions(all_rows)

    results["total"] = len(all_rows)
    return results
```

- [ ] **Step 4: Wire into the nightly pipeline**

In `ops.py`, add a step in the nightly pipeline (after the reporting sync step, ~line 450). Follow the existing guard pattern:

```python
# Field source content sync
if settings.reporting_mcp_url and settings.reporting_mcp_token:
    try:
        fs_result = await asyncio.to_thread(run_field_source_sync, wctx.db, wctx.settings)
        log.info("field_source_sync_complete", **fs_result)
    except Exception as e:
        log.warning("field_source_sync_failed", error=str(e))
        warnings.append(f"Field source sync failed: {e}")
```

- [ ] **Step 5: Add standalone job**

In `ops.py`, add a standalone arq job (~line 670):

```python
async def run_field_source_sync_job(ctx: dict, job_id: str) -> dict:
    wctx = WorkerContext(ctx)
    log.info("field_source_sync_start", job_id=job_id)
    result = await asyncio.to_thread(run_field_source_sync, wctx.db, wctx.settings)
    log.info("field_source_sync_complete", job_id=job_id, **result)
    return result
```

Register in `settings.py` alongside the other jobs:

```python
func(run_field_source_sync_job, timeout=600),
```

- [ ] **Step 6: Write sync test**

```python
# tests/test_field_source_sync.py
from unittest.mock import patch, MagicMock
from rcars.services.reporting_sync import run_field_source_sync

def test_field_source_sync_processes_rows(db, settings):
    mock_rows = [
        {"git_repo": "https://github.com/example/repo1", "git_ref": "main",
         "provisioned_at": "2026-06-01T00:00:00Z", "retired_at": None, "provision_uuid": "uuid-s1"},
    ]
    with patch("rcars.services.reporting_sync.mcp_query", return_value=mock_rows):
        result = run_field_source_sync(db, settings)
    assert result["total"] >= 1
    rows = db.get_field_source_summary()
    assert len(rows) >= 1
```

- [ ] **Step 7: Run tests**

```bash
cd src/api && python -m pytest tests/test_field_source_sync.py -v
```

- [ ] **Step 8: Commit**

```bash
git add src/api/rcars/services/reporting_sync.py src/api/rcars/workers/ops.py \
        src/api/rcars/workers/settings.py src/api/tests/test_field_source_sync.py
git commit -m "[RHDPCD-2028] Add field source content reporting sync job"
```

---

### Task 3: API Endpoint

**Files:**
- Modify: `src/api/rcars/api/routes/analysis.py` (add endpoint after `/performance`)
- Modify: `src/api/rcars/api/schemas.py` (add response model)
- Test: `src/api/tests/test_field_source_api.py`

**Interfaces:**
- Consumes: `Database.get_field_source_summary(catalog_item)` from Task 1
- Produces: `GET /api/v1/analysis/field-source?catalog_item=ocp|rhel|all` returning `FieldSourceResponse`

- [ ] **Step 1: Add response model to schemas.py**

```python
class FieldSourceProvision(BaseModel):
    provisioned_at: datetime
    retired_at: datetime | None

class FieldSourceRepo(BaseModel):
    git_repo: str
    git_ref: str | None
    catalog_item: str
    provision_count: int
    first_seen: datetime
    last_seen: datetime
    provisions: list[FieldSourceProvision]

class FieldSourceResponse(BaseModel):
    repos: list[FieldSourceRepo]
    total_repos: int
    total_provisions: int
```

- [ ] **Step 2: Add the endpoint**

```python
@router.get("/field-source", tags=["Field Source Content"], response_model=FieldSourceResponse)
async def field_source_report(
    request: Request,
    user: str = Depends(require_auth),
    catalog_item: str = Query("all"),
):
    db = request.app.state.db
    cat_filter = catalog_item if catalog_item != "all" else None
    rows = db.get_field_source_summary(catalog_item=cat_filter)

    # Group by (git_repo, git_ref, catalog_item)
    groups: dict[tuple, list] = {}
    for row in rows:
        key = (row["git_repo"], row.get("git_ref"), row["catalog_item"])
        groups.setdefault(key, []).append(row)

    repos = []
    for (repo, ref, cat), provisions in groups.items():
        dates = [p["provisioned_at"] for p in provisions]
        repos.append(FieldSourceRepo(
            git_repo=repo,
            git_ref=ref,
            catalog_item=cat,
            provision_count=len(provisions),
            first_seen=min(dates),
            last_seen=max(dates),
            provisions=[FieldSourceProvision(
                provisioned_at=p["provisioned_at"],
                retired_at=p.get("retired_at"),
            ) for p in provisions],
        ))

    repos.sort(key=lambda r: r.provision_count, reverse=True)
    return FieldSourceResponse(
        repos=repos,
        total_repos=len(repos),
        total_provisions=sum(r.provision_count for r in repos),
    )
```

- [ ] **Step 3: Write API test**

```python
# tests/test_field_source_api.py
import pytest
from datetime import datetime, timezone

def test_field_source_endpoint(client, db):
    # Seed data
    db.upsert_field_source_provisions([
        {"catalog_item": "ocp", "git_repo": "https://github.com/ex/r1",
         "git_ref": "main", "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "api-uuid-1"},
        {"catalog_item": "ocp", "git_repo": "https://github.com/ex/r1",
         "git_ref": "main", "provisioned_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "api-uuid-2"},
    ])
    resp = client.get("/api/v1/analysis/field-source")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_repos"] == 1
    assert data["total_provisions"] == 2
    assert data["repos"][0]["provision_count"] == 2

def test_field_source_filter(client, db):
    db.upsert_field_source_provisions([
        {"catalog_item": "ocp", "git_repo": "https://github.com/ex/r1",
         "git_ref": "main", "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "filt-uuid-1"},
        {"catalog_item": "rhel", "git_repo": "https://github.com/ex/r2",
         "git_ref": "v1.0", "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "filt-uuid-2"},
    ])
    resp = client.get("/api/v1/analysis/field-source?catalog_item=ocp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_repos"] == 1
    assert data["repos"][0]["catalog_item"] == "ocp"
```

- [ ] **Step 4: Run tests**

```bash
cd src/api && python -m pytest tests/test_field_source_api.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/api/routes/analysis.py src/api/rcars/api/schemas.py \
        src/api/tests/test_field_source_api.py
git commit -m "[RHDPCD-2028] Add field source content API endpoint"
```

---

### Task 4: Frontend Page

**Files:**
- Create: `src/frontend/src/pages/FieldSourcePage.tsx`
- Test: manual browser verification

**Interfaces:**
- Consumes: `GET /api/v1/analysis/field-source?catalog_item=all|ocp|rhel` from Task 3
- Produces: React component `FieldSourcePage` (default export)

- [ ] **Step 1: Create FieldSourcePage.tsx**

Follow the PerformancePage pattern: custom `<table>`, `useState<Set<string>>` for expand, filter state, `api.get()` on mount.

```tsx
import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

interface Provision {
  provisioned_at: string;
  retired_at: string | null;
}

interface RepoEntry {
  git_repo: string;
  git_ref: string | null;
  catalog_item: string;
  provision_count: number;
  first_seen: string;
  last_seen: string;
  provisions: Provision[];
}

interface FieldSourceData {
  repos: RepoEntry[];
  total_repos: number;
  total_provisions: number;
}

export default function FieldSourcePage() {
  const [data, setData] = useState<FieldSourceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = filter !== 'all' ? `?catalog_item=${filter}` : '';
      const resp = await api.get<FieldSourceData>(`/analysis/field-source${params}`);
      setData(resp);
    } catch (e: any) {
      setError(e.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const toggleExpand = (key: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const repoName = (url: string) => {
    try { return new URL(url).pathname.replace(/^\//, '').replace(/\.git$/, ''); }
    catch { return url; }
  };

  const formatDate = (iso: string) => new Date(iso).toLocaleDateString();

  if (loading) return <div className="ca-loading">Loading…</div>;
  if (error) return <div className="ca-error">{error}</div>;
  if (!data) return null;

  return (
    <div className="ca-performance-page">
      <div className="ca-page-header">
        <h1>Field Source Content</h1>
        <div className="ca-filters">
          <select value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="ocp">OCP</option>
            <option value="rhel">RHEL</option>
          </select>
        </div>
      </div>

      <div className="ca-stats-row">
        <span>{data.total_repos} repos</span>
        <span>{data.total_provisions} total provisions</span>
      </div>

      <table className="ca-table">
        <thead>
          <tr>
            <th></th>
            <th>Repository</th>
            <th>Ref</th>
            <th>Type</th>
            <th>Provisions</th>
            <th>First Used</th>
            <th>Last Used</th>
          </tr>
        </thead>
        <tbody>
          {data.repos.map(repo => {
            const key = `${repo.git_repo}|${repo.git_ref}|${repo.catalog_item}`;
            const isExpanded = expanded.has(key);
            return (
              <>
                <tr key={key} className="ca-row-clickable" onClick={() => toggleExpand(key)}>
                  <td>{isExpanded ? '▾' : '▸'}</td>
                  <td><a href={repo.git_repo} target="_blank" rel="noreferrer">{repoName(repo.git_repo)}</a></td>
                  <td><code>{repo.git_ref || '—'}</code></td>
                  <td><span className={`ca-badge ca-badge--${repo.catalog_item}`}>{repo.catalog_item.toUpperCase()}</span></td>
                  <td>{repo.provision_count}</td>
                  <td>{formatDate(repo.first_seen)}</td>
                  <td>{formatDate(repo.last_seen)}</td>
                </tr>
                {isExpanded && (
                  <tr key={`${key}-detail`} className="ca-detail-row">
                    <td colSpan={7}>
                      <table className="ca-detail-table">
                        <thead><tr><th>Provisioned</th><th>Retired</th><th>Duration</th></tr></thead>
                        <tbody>
                          {repo.provisions.map((p, i) => (
                            <tr key={i}>
                              <td>{formatDate(p.provisioned_at)}</td>
                              <td>{p.retired_at ? formatDate(p.retired_at) : 'Active'}</td>
                              <td>{p.retired_at
                                ? `${Math.round((new Date(p.retired_at).getTime() - new Date(p.provisioned_at).getTime()) / 86400000)}d`
                                : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/pages/FieldSourcePage.tsx
git commit -m "[RHDPCD-2028] Add Field Source Content frontend page"
```

---

### Task 5: Routing and Sidebar

**Files:**
- Modify: `src/frontend/src/App.tsx` (~line 50, analysis routes)
- Modify: `src/frontend/src/components/RcarsSidebar.tsx` (~line 70, analysis nav)

**Interfaces:**
- Consumes: `FieldSourcePage` component from Task 4
- Produces: `/analysis/field-source` route + sidebar nav entry

- [ ] **Step 1: Add route to App.tsx**

Add inside the analysis route group. Since this is visible to all authenticated users (not curator-only), add it alongside the performance route:

```tsx
import FieldSourcePage from './pages/FieldSourcePage';

// In the route definitions, near the performance route:
<Route path="/analysis/field-source" element={<FieldSourcePage />} />
```

- [ ] **Step 2: Add sidebar entry to RcarsSidebar.tsx**

Add a NavLink inside the Analysis section. Visible to all authenticated users:

```tsx
<NavLink to="/analysis/field-source"
  className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}>
  Field Source Content
</NavLink>
```

- [ ] **Step 3: Verify in browser**

Start dev server (`./dev-services.sh start`), navigate to `/analysis/field-source`, confirm:
- Page loads without errors
- Sidebar shows "Field Source Content" under Analysis
- Filter dropdown works (All / OCP / RHEL)
- If data exists, rows render and expand on click

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/App.tsx src/frontend/src/components/RcarsSidebar.tsx
git commit -m "[RHDPCD-2028] Wire Field Source Content page into routes and sidebar"
```

---

### Task 6: End-to-End Verification

**Files:** none (verification only)

- [ ] **Step 1: Run all backend tests**

```bash
cd src/api && python -m pytest tests/ -v -m "not integration"
```

Expected: all pass, including new field source tests.

- [ ] **Step 2: Trigger a sync**

Either run the standalone job via CLI or trigger via the nightly pipeline. Verify data appears in the `field_source_provisions` table.

- [ ] **Step 3: Verify frontend with real data**

Navigate to `/analysis/field-source`. Confirm:
- Repos appear with correct counts
- OCP/RHEL filter works
- Expand shows provision dates
- No PII visible anywhere

- [ ] **Step 4: Commit any fixes, then final commit**

If any fixes were needed, commit them. Then verify all tests still pass.
