# Browse Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Browse page's flat filter bar and client-side filtering with a collapsible filter panel, server-side filtering/pagination, and role-based curator filter separation.

**Architecture:** Extend `GET /catalog` with server-side search, stage, infrastructure, and content-state filter params. Replace the BrowsePage client-side load-all approach with per-page server requests. New collapsible filter panel with workload multi-select, numbered pagination, and curator-only filter panel.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript (frontend), psycopg3 (SQL), existing RCARS LCARS theme CSS.

**Spec:** `docs/superpowers/specs/2026-06-15-browse-page-redesign-design.md`

---

### Task 1: Backend — Server-Side Filtered Catalog Query

**Files:**
- Modify: `src/api/rcars/db/database.py` — add `list_catalog_items_filtered()` method
- Test: `src/api/tests/test_db.py` — add filtered query tests

This task adds a new database method that builds a filtered, paginated SQL query. It reuses `_resolve_workload_aliases()` from the existing infrastructure search for workload AND semantics.

- [ ] **Step 1: Write the failing tests**

Add to `src/api/tests/test_db.py`:

```python
def _seed_items(db):
    """Seed test data for filtered catalog queries."""
    items = [
        {"ci_name": "ns.ocp-ai-workshop.prod", "display_name": "OpenShift AI Workshop",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "is_agd_v2": True, "agd_config": "ocp-cnv",
         "cloud_provider": "ec2", "showroom_url": "https://github.com/example/ai"},
        {"ci_name": "ns.pipelines-lab.prod", "display_name": "Pipelines Lab",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "is_agd_v2": True, "agd_config": "ocp-workloads",
         "cloud_provider": "azure", "showroom_url": "https://github.com/example/pipe"},
        {"ci_name": "ns.getting-started.prod", "display_name": "Getting Started",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "is_agd_v2": False,
         "showroom_url": "https://github.com/example/start"},
        {"ci_name": "ns.ai-dev.dev", "display_name": "AI Dev Build",
         "stage": "dev", "catalog_namespace": "babylon-catalog-dev",
         "is_prod": False, "is_agd_v2": True, "agd_config": "ocp-cnv",
         "cloud_provider": "ec2"},
        {"ci_name": "zt-ns.zt-demo.prod", "display_name": "ZT Demo",
         "stage": "prod", "catalog_namespace": "zt-babylon-catalog-prod",
         "is_prod": True, "is_agd_v2": False,
         "showroom_url": "https://github.com/example/zt"},
        {"ci_name": "ns.stale-item.prod", "display_name": "Stale Item",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "showroom_url": "https://github.com/example/stale",
         "scan_status": "success"},
        {"ci_name": "ns.failed-item.prod", "display_name": "Failed Item",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "showroom_url": "https://github.com/example/failed",
         "scan_status": "failed"},
    ]
    for item in items:
        if "scan_status" not in item:
            item["scan_status"] = "not_scanned"
        db.upsert_catalog_item(item)
    # Mark stale item as stale via analysis
    db.upsert_showroom_analysis({"ci_name": "ns.stale-item.prod", "summary": "test", "is_stale": True})
    # Mark failed item with analysis that has review needed
    db.upsert_showroom_analysis({"ci_name": "ns.failed-item.prod", "summary": "test", "enrichment_review_needed": True})
    # Add workloads for the AI workshop
    with db.pool.connection() as conn:
        conn.execute(
            "INSERT INTO catalog_item_workloads (ci_name, workload_fqcn, workload_role, workload_collection) "
            "VALUES (%s, %s, %s, %s)",
            ("ns.ocp-ai-workshop.prod", "agnosticd.ai_workloads.openshift_ai", "openshift_ai", "ai_workloads"),
        )
        conn.execute(
            "INSERT INTO workload_mapping (workload_role, product_name, verified) VALUES (%s, %s, %s)",
            ("openshift_ai", "OpenShift AI", True),
        )
        conn.execute(
            "INSERT INTO workload_aliases (product_name, alias) VALUES (%s, %s)",
            ("OpenShift AI", "RHOAI"),
        )
        conn.commit()


def test_filtered_catalog_default(db):
    """Default query returns prod items only, paginated."""
    _seed_items(db)
    result = db.list_catalog_items_filtered()
    # Should return prod items only (5 prod items), not dev
    assert result["total"] >= 5
    assert all(item["stage"] == "prod" for item in result["items"])


def test_filtered_catalog_search(db):
    """Text search matches display_name case-insensitively."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(search="openshift ai")
    assert result["total"] >= 1
    assert any("AI" in item["display_name"] for item in result["items"])


def test_filtered_catalog_stage(db):
    """Stage filter includes dev items when requested."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(stages=["prod", "dev"])
    ci_names = [item["ci_name"] for item in result["items"]]
    assert "ns.ai-dev.dev" in ci_names


def test_filtered_catalog_cloud_provider(db):
    """Cloud provider filter narrows results."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(cloud_provider="ec2")
    assert result["total"] >= 1
    assert all(item.get("cloud_provider") == "ec2" for item in result["items"])


def test_filtered_catalog_agd_config(db):
    """AgnosticD config filter narrows results."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(agd_config="ocp-cnv")
    assert result["total"] >= 1
    assert all(item.get("agd_config") == "ocp-cnv" for item in result["items"])


def test_filtered_catalog_workloads(db):
    """Workload filter with alias resolution."""
    _seed_items(db)
    # Direct product name
    result = db.list_catalog_items_filtered(workloads=["OpenShift AI"])
    assert result["total"] >= 1
    assert any("ai-workshop" in item["ci_name"] for item in result["items"])
    # Via alias
    result2 = db.list_catalog_items_filtered(workloads=["RHOAI"])
    assert result2["total"] == result["total"]


def test_filtered_catalog_content_filter_failures(db):
    """Content filter for scan failures."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(content_filter="scan_failures")
    assert result["total"] >= 1
    assert all(item["scan_status"] == "failed" for item in result["items"])


def test_filtered_catalog_content_filter_stale(db):
    """Content filter for stale items."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(content_filter="stale")
    assert result["total"] >= 1
    assert all(item.get("is_stale") for item in result["items"])


def test_filtered_catalog_pagination(db):
    """Pagination returns correct slice and total."""
    _seed_items(db)
    page1 = db.list_catalog_items_filtered(limit=2, offset=0)
    page2 = db.list_catalog_items_filtered(limit=2, offset=2)
    assert len(page1["items"]) == 2
    assert len(page2["items"]) >= 1
    assert page1["total"] == page2["total"]
    assert page1["items"][0]["ci_name"] != page2["items"][0]["ci_name"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_db.py::test_filtered_catalog_default -v`
Expected: FAIL with `AttributeError: 'Database' object has no attribute 'list_catalog_items_filtered'`

- [ ] **Step 3: Implement `list_catalog_items_filtered()` in database.py**

Add this method to the `Database` class in `src/api/rcars/db/database.py`, after the existing `list_catalog_items()` method (after line 342):

```python
    def list_catalog_items_filtered(
        self,
        search: str | None = None,
        stages: list[str] | None = None,
        cloud_provider: str | None = None,
        agd_config: str | None = None,
        workloads: list[str] | None = None,
        content_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        conditions = []
        params: dict[str, Any] = {}
        joins = []

        # Stage filter — default to prod only
        if stages:
            conditions.append("ci.stage = ANY(%(stages)s)")
            params["stages"] = stages
        else:
            conditions.append("ci.stage = 'prod'")

        # Text search
        if search:
            conditions.append(
                "(ci.display_name ILIKE %(search)s OR ci.ci_name ILIKE %(search)s)"
            )
            params["search"] = f"%{search}%"

        # Infrastructure filters
        if cloud_provider:
            conditions.append("ci.cloud_provider = %(cloud_provider)s")
            params["cloud_provider"] = cloud_provider
        if agd_config:
            conditions.append("ci.agd_config = %(agd_config)s")
            params["agd_config"] = agd_config

        # Workload filter with AND semantics + alias resolution
        if workloads:
            resolved = self._resolve_workload_aliases(workloads)
            for i, wl in enumerate(resolved):
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

        # Content-state filters (curator-only, enforced at route level)
        if content_filter == "unanalyzed":
            conditions.append("ci.showroom_url IS NOT NULL")
            conditions.append("ci.is_published IS NOT TRUE")
            conditions.append("ci.scan_status NOT IN ('success', 'failed')")
        elif content_filter == "scan_failures":
            conditions.append("ci.scan_status = 'failed'")
        elif content_filter == "stale":
            joins.append(
                "JOIN showroom_analysis sa_stale ON sa_stale.ci_name = ci.ci_name "
                "AND sa_stale.is_stale = TRUE"
            )
        elif content_filter == "needs_review":
            joins.append(
                "JOIN showroom_analysis sa_review ON sa_review.ci_name = ci.ci_name "
                "AND sa_review.enrichment_review_needed = TRUE"
            )

        join_sql = "\n".join(joins)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Count query
        count_sql = f"""
            SELECT COUNT(DISTINCT ci.ci_name)
            FROM catalog_items ci
            LEFT JOIN showroom_analysis sa ON sa.ci_name = ci.ci_name
            {join_sql}
            {where}
        """

        # Data query
        data_sql = f"""
            SELECT DISTINCT ci.*, sa.is_stale, sa.enrichment_review_needed
            FROM catalog_items ci
            LEFT JOIN showroom_analysis sa ON sa.ci_name = ci.ci_name
            {join_sql}
            {where}
            ORDER BY ci.ci_name
            LIMIT %(limit)s OFFSET %(offset)s
        """
        params["limit"] = limit
        params["offset"] = offset

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(count_sql, params)
                total = cur.fetchone()["count"]
                cur.execute(data_sql, params)
                items = cur.fetchall()

        return {"items": items, "total": total}
```

- [ ] **Step 4: Run all filtered catalog tests**

Run: `cd src/api && python -m pytest tests/test_db.py -k "test_filtered_catalog" -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/database.py src/api/tests/test_db.py
git commit -m "db: Add list_catalog_items_filtered with server-side search and infra filters"
```

---

### Task 2: Backend — Extend GET /catalog Route with Filter Params

**Files:**
- Modify: `src/api/rcars/api/routes/catalog.py` — update `list_catalog()` endpoint signature and body

This task wires the new database method to the existing `GET /catalog` route, adding query parameters for search, stage, infrastructure filters, and content_filter.

- [ ] **Step 1: Update the `list_catalog` route in `src/api/rcars/api/routes/catalog.py`**

Replace the existing `list_catalog` function (lines 12-25) with:

```python
@router.get("")
async def list_catalog(
    request: Request,
    user: str = Depends(require_auth),
    search: str | None = Query(None, description="Case-insensitive text search on name and CI"),
    stage: str | None = Query(None, description="Comma-separated stages: prod,dev,event"),
    cloud_provider: str | None = Query(None, description="Filter by cloud provider"),
    workloads: str | None = Query(None, description="Comma-separated product names (AND semantics)"),
    agd_config: str | None = Query(None, description="Filter by AgnosticD config type"),
    content_filter: str | None = Query(None, description="Curator filter: unanalyzed, scan_failures, stale, needs_review"),
    category: str | None = None,
    limit: int = Query(50, le=2000),
    offset: int = Query(0, ge=0),
):
    db = request.app.state.db
    stage_list = [s.strip() for s in stage.split(",")] if stage else None
    workload_list = [w.strip() for w in workloads.split(",")] if workloads else None

    result = db.list_catalog_items_filtered(
        search=search,
        stages=stage_list,
        cloud_provider=cloud_provider,
        agd_config=agd_config,
        workloads=workload_list,
        content_filter=content_filter,
        limit=limit,
        offset=offset,
    )
    return result
```

- [ ] **Step 2: Verify the API starts and the endpoint works**

Run: `cd src/api && python -c "from rcars.api.routes.catalog import router; print('Import OK')"` 
Expected: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add src/api/rcars/api/routes/catalog.py
git commit -m "catalog: Extend GET /catalog with search, stage, infra, and content_filter params"
```

---

### Task 3: Frontend — Update API Client

**Files:**
- Modify: `src/frontend/src/services/api.ts` — update `listCatalog()` params

This task updates the frontend API client to pass the new filter parameters to `GET /catalog`.

- [ ] **Step 1: Update `listCatalog` in `src/frontend/src/services/api.ts`**

Replace the existing `listCatalog` method with:

```typescript
  listCatalog: (params?: {
    search?: string;
    stage?: string;
    cloud_provider?: string;
    workloads?: string;
    agd_config?: string;
    content_filter?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.search) qs.set('search', params.search);
    if (params?.stage) qs.set('stage', params.stage);
    if (params?.cloud_provider) qs.set('cloud_provider', params.cloud_provider);
    if (params?.workloads) qs.set('workloads', params.workloads);
    if (params?.agd_config) qs.set('agd_config', params.agd_config);
    if (params?.content_filter) qs.set('content_filter', params.content_filter);
    if (params?.category) qs.set('category', params.category);
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.offset) qs.set('offset', String(params.offset));
    return request<{ items: unknown[]; total: number }>(`/catalog?${qs}`);
  },
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors (or only pre-existing ones unrelated to api.ts)

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/services/api.ts
git commit -m "frontend: Update listCatalog API client with filter params"
```

---

### Task 4: Frontend — Pagination Component

**Files:**
- Create: `src/frontend/src/components/Pagination.tsx`
- Modify: `src/frontend/src/styles/lcars.css` — add pagination styles

A standalone pagination component that renders numbered pages with ellipsis. Used by BrowsePage.

- [ ] **Step 1: Create `src/frontend/src/components/Pagination.tsx`**

```tsx
interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

function getPageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)

  const pages: (number | '...')[] = [1]

  if (current > 3) pages.push('...')

  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  for (let i = start; i <= end; i++) pages.push(i)

  if (current < total - 2) pages.push('...')

  if (total > 1) pages.push(total)

  return pages
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null

  const pages = getPageNumbers(currentPage, totalPages)

  return (
    <div className="pagination">
      <button
        className="pagination-btn"
        disabled={currentPage === 1}
        onClick={() => onPageChange(currentPage - 1)}
      >
        &lt;
      </button>
      {pages.map((page, i) =>
        page === '...' ? (
          <span key={`ellipsis-${i}`} className="pagination-ellipsis">...</span>
        ) : (
          <button
            key={page}
            className={`pagination-btn${page === currentPage ? ' active' : ''}`}
            onClick={() => onPageChange(page)}
          >
            {page}
          </button>
        )
      )}
      <button
        className="pagination-btn"
        disabled={currentPage === totalPages}
        onClick={() => onPageChange(currentPage + 1)}
      >
        &gt;
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Add pagination styles to `src/frontend/src/styles/lcars.css`**

Add at the end of the file, before the closing animations section:

```css
/* ── Pagination ── */
.pagination {
  display: flex;
  gap: 4px;
  justify-content: center;
  align-items: center;
  margin-top: 20px;
  padding-bottom: 20px;
}
.pagination-btn {
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  min-width: 36px;
  text-align: center;
}
.pagination-btn:hover:not(:disabled) {
  color: var(--text-primary);
  border-color: var(--accent-blue);
}
.pagination-btn.active {
  background: var(--accent-blue);
  color: #fff;
  border-color: var(--accent-blue);
}
.pagination-btn:disabled {
  opacity: 0.3;
  cursor: default;
}
.pagination-ellipsis {
  color: var(--text-muted);
  padding: 6px 4px;
  font-size: 13px;
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | head -5`
Expected: No new errors

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/components/Pagination.tsx src/frontend/src/styles/lcars.css
git commit -m "frontend: Add numbered pagination component"
```

---

### Task 5: Frontend — WorkloadMultiSelect Component

**Files:**
- Create: `src/frontend/src/components/WorkloadMultiSelect.tsx`
- Modify: `src/frontend/src/styles/lcars.css` — add multi-select styles

A custom dropdown with checkboxes for selecting multiple workloads. Closes on click-outside or Escape.

- [ ] **Step 1: Create `src/frontend/src/components/WorkloadMultiSelect.tsx`**

```tsx
import { useState, useRef, useEffect } from 'react'

interface WorkloadOption {
  product_name: string
  category: string
}

interface WorkloadMultiSelectProps {
  options: WorkloadOption[]
  selected: string[]
  onChange: (selected: string[]) => void
}

export function WorkloadMultiSelect({ options, selected, onChange }: WorkloadMultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setIsOpen(false)
    }
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [])

  const toggle = (name: string) => {
    if (selected.includes(name)) {
      onChange(selected.filter(s => s !== name))
    } else {
      onChange([...selected, name])
    }
  }

  const sorted = [...options].sort((a, b) => a.product_name.localeCompare(b.product_name))
  const hasSelection = selected.length > 0
  const label = hasSelection ? `${selected.length} selected` : 'Select workloads...'

  return (
    <div className="wl-multiselect" ref={ref}>
      <div
        className={`wl-multiselect-trigger${hasSelection ? ' active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        {label} ▾
      </div>
      {isOpen && (
        <div className="wl-multiselect-panel">
          {sorted.map(opt => (
            <label key={opt.product_name} className="wl-multiselect-option">
              <input
                type="checkbox"
                checked={selected.includes(opt.product_name)}
                onChange={() => toggle(opt.product_name)}
              />
              <span>{opt.product_name}</span>
            </label>
          ))}
          {sorted.length === 0 && (
            <div style={{ padding: '8px 12px', color: '#555', fontSize: '12px' }}>
              No workload mappings available
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Add multi-select styles to `src/frontend/src/styles/lcars.css`**

Add after the pagination styles:

```css
/* ── Workload Multi-Select ── */
.wl-multiselect {
  position: relative;
  flex: 1;
  min-width: 140px;
}
.wl-multiselect-trigger {
  background: var(--bg-primary);
  border: 1px solid #2a4a6a;
  border-radius: 4px;
  padding: 5px 10px;
  color: #888;
  font-size: 11px;
  cursor: pointer;
}
.wl-multiselect-trigger.active {
  color: var(--accent-blue);
  border-color: var(--accent-blue);
}
.wl-multiselect-panel {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--bg-secondary);
  border: 1px solid #2a4a6a;
  border-top: none;
  border-radius: 0 0 4px 4px;
  max-height: 240px;
  overflow-y: auto;
  z-index: 10;
}
.wl-multiselect-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}
.wl-multiselect-option:hover {
  background: var(--bg-card);
}
.wl-multiselect-option input[type="checkbox"] {
  accent-color: var(--accent-blue);
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | head -5`
Expected: No new errors

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/components/WorkloadMultiSelect.tsx src/frontend/src/styles/lcars.css
git commit -m "frontend: Add workload multi-select dropdown component"
```

---

### Task 6: Frontend — Rewrite BrowsePage with Server-Side Filtering

**Files:**
- Modify: `src/frontend/src/pages/BrowsePage.tsx` — major rewrite
- Modify: `src/frontend/src/styles/lcars.css` — add filter panel and curator panel styles

This is the main task. Replaces client-side filtering with server-side, adds the collapsible filter panel, curator filter panel, URL state sync, and integrates the Pagination and WorkloadMultiSelect components.

- [ ] **Step 1: Add filter panel and curator panel styles to `src/frontend/src/styles/lcars.css`**

Add after the workload multi-select styles:

```css
/* ── Filter Panel ── */
.filter-panel {
  background: #111a2a;
  border: 1px solid #1a3050;
  border-radius: 6px;
  margin-bottom: 10px;
  overflow: hidden;
}
.filter-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  cursor: pointer;
}
.filter-panel-label {
  color: var(--accent-blue);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.filter-panel-clear {
  color: var(--accent-blue);
  font-size: 10px;
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
}
.filter-panel-clear:hover { text-decoration: underline; }
.filter-panel-body {
  padding: 0 14px 10px;
}
.filter-panel-dropdowns {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.filter-panel-dropdown {
  flex: 1;
  min-width: 140px;
}
.filter-panel-dropdown-label {
  color: #666;
  font-size: 10px;
  margin-bottom: 4px;
  text-transform: uppercase;
}
.filter-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #1a2a1a;
  color: #88bb88;
  border: 1px solid #2a4a2a;
  border-radius: 10px;
  padding: 3px 10px;
  font-size: 11px;
  cursor: pointer;
}
.filter-chip:hover { background: #2a3a2a; }
.filter-panel-collapsed {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}
.filter-panel-muted {
  color: #555;
  font-size: 10px;
}

/* ── Curator Filter Panel ── */
.curator-panel {
  background: #1a1a10;
  border: 1px solid #3a3a1a;
  border-radius: 6px;
  margin-bottom: 10px;
  overflow: hidden;
}
.curator-panel .filter-panel-label {
  color: var(--lcars-amber);
}
.curator-panel .filter-panel-clear {
  color: var(--lcars-amber);
}
.curator-filter-pills {
  display: flex;
  gap: 6px;
  padding: 0 14px 10px;
  flex-wrap: wrap;
}
.curator-filter-pill {
  background: #2a2a1a;
  border: 1px solid #4a4a2a;
  border-radius: 10px;
  padding: 3px 10px;
  font-size: 11px;
  color: #cc9933;
  cursor: pointer;
}
.curator-filter-pill:hover { background: #3a3a2a; }
.curator-filter-pill.active {
  background: #4a3a10;
  border-color: var(--lcars-amber);
  color: var(--lcars-amber);
}
```

- [ ] **Step 2: Rewrite `src/frontend/src/pages/BrowsePage.tsx`**

Replace the entire file content with:

```tsx
import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { LcarsButton } from '../components/lcars'
import { Pagination } from '../components/Pagination'
import { WorkloadMultiSelect } from '../components/WorkloadMultiSelect'

interface CatalogItem {
  ci_name: string
  display_name: string
  category: string
  stage: string
  catalog_namespace: string
  showroom_url: string | null
  scan_status: string
  is_published?: boolean
  is_stale?: boolean
  enrichment_review_needed?: boolean
  is_agd_v2?: boolean
  agd_config?: string | null
  cloud_provider?: string | null
}

interface Module {
  title: string
  topics?: string[]
  learning_objectives?: string[]
}

interface LearningObjectives {
  stated?: string[]
  inferred?: string[]
}

interface ItemDetail {
  ci_name: string
  display_name: string
  category: string
  stage: string
  catalog_namespace: string
  showroom_url: string | null
  scan_status: string
  content_path: string | null
  showroom_url_override: string | null
  scan_error_class: string | null
  scan_error: string | null
  scan_failed_at: string | null
  analysis: {
    summary: string | null
    content_type: string | null
    difficulty: string | null
    estimated_duration_min: number | null
    topics_json: string[] | null
    products_json: string[] | null
    audience_json: string[] | null
    modules_json: Module[] | null
    learning_objectives_json: LearningObjectives | null
    notes: string | null
    is_stale: boolean
    enrichment_review_needed: boolean
  } | null
  tags: Array<{ id: number; tag_type: string; tag_value: string; added_by: string | null }>
  is_agd_v2?: boolean
  agd_config?: string | null
  cloud_provider?: string | null
  ocp_version?: string | null
  os_image?: string | null
  worker_instance_count?: string | null
  control_plane_instance_count?: string | null
  workloads?: Array<{ workload_fqcn: string; workload_role: string; workload_collection: string | null }>
  acl_groups?: string[]
}

interface Facets {
  workloads: Array<{ product_name: string; category: string; ci_count: number }>
  configs: Array<{ agd_config: string; ci_count: number }>
  cloud_providers: Array<{ cloud_provider: string; ci_count: number }>
}

type ContentFilter = 'unanalyzed' | 'scan_failures' | 'stale' | 'needs_review'

const PAGE_SIZE = 50

function isZtItem(item: CatalogItem): boolean {
  return item.catalog_namespace?.startsWith('zt-') || item.ci_name.startsWith('zt-')
}

function LcarsToggle({ label, active, onToggle }: { label: string; active: boolean; onToggle: () => void }) {
  return (
    <div className={`lcars-toggle${active ? ' active' : ''}`} onClick={onToggle}>
      <div className="lcars-toggle-track">
        <div className="lcars-toggle-knob" />
      </div>
      <span>{label}</span>
    </div>
  )
}

function catalogUrl(ciName: string, namespace: string): string {
  return `https://catalog.demo.redhat.com/catalog?item=${namespace}/${ciName}`
}

export function BrowsePage() {
  const auth = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  // Filter state — initialized from URL
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [showDev, setShowDev] = useState(searchParams.get('stage')?.includes('dev') || false)
  const [showEvent, setShowEvent] = useState(searchParams.get('stage')?.includes('event') || false)
  const [cloudProvider, setCloudProvider] = useState(searchParams.get('cloud_provider') || '')
  const [agdConfig, setAgdConfig] = useState(searchParams.get('agd_config') || '')
  const [selectedWorkloads, setSelectedWorkloads] = useState<string[]>(
    searchParams.get('workloads')?.split(',').filter(Boolean) || []
  )
  const [contentFilter, setContentFilter] = useState<ContentFilter | ''>(
    (searchParams.get('content_filter') as ContentFilter) || ''
  )
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1)

  // Data state
  const [items, setItems] = useState<CatalogItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [facets, setFacets] = useState<Facets | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [curatorFiltersOpen, setCuratorFiltersOpen] = useState(false)

  // Expanded item state
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [itemDetails, setItemDetails] = useState<Record<string, ItemDetail>>({})
  const [newTags, setNewTags] = useState<Record<string, string>>({})
  const [noteTexts, setNoteTexts] = useState<Record<string, string>>({})
  const [contentPaths, setContentPaths] = useState<Record<string, string>>({})
  const [overrideUrls, setOverrideUrls] = useState<Record<string, string>>({})
  const [scanningPath, setScanningPath] = useState<Record<string, boolean>>({})
  const [flaggedItems, setFlaggedItems] = useState<Set<string>>(new Set())
  const [analyzing, setAnalyzing] = useState<string | null>(null)

  // Debounce timer for search
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Load facets once on mount
  useEffect(() => {
    api.getCatalogFacets().then(data => setFacets(data as Facets)).catch(() => {})
  }, [])

  // Build stage string from toggles
  const stageString = useCallback(() => {
    const stages = ['prod']
    if (showDev) stages.push('dev')
    if (showEvent) stages.push('event')
    return stages.join(',')
  }, [showDev, showEvent])

  // Fetch items from server
  const fetchItems = useCallback(async (currentPage: number) => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = {
        stage: stageString(),
        limit: PAGE_SIZE,
        offset: (currentPage - 1) * PAGE_SIZE,
      }
      if (search) params.search = search
      if (cloudProvider) params.cloud_provider = cloudProvider
      if (agdConfig) params.agd_config = agdConfig
      if (selectedWorkloads.length > 0) params.workloads = selectedWorkloads.join(',')
      if (contentFilter) params.content_filter = contentFilter

      const data = await api.listCatalog(params as Parameters<typeof api.listCatalog>[0])
      setItems(data.items as CatalogItem[])
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to load catalog:', err)
    }
    setLoading(false)
  }, [search, stageString, cloudProvider, agdConfig, selectedWorkloads, contentFilter])

  // Sync URL params
  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    const stage = stageString()
    if (stage !== 'prod') params.stage = stage
    if (cloudProvider) params.cloud_provider = cloudProvider
    if (agdConfig) params.agd_config = agdConfig
    if (selectedWorkloads.length > 0) params.workloads = selectedWorkloads.join(',')
    if (contentFilter) params.content_filter = contentFilter
    if (page > 1) params.page = String(page)
    setSearchParams(params, { replace: true })
  }, [search, showDev, showEvent, cloudProvider, agdConfig, selectedWorkloads, contentFilter, page, setSearchParams, stageString])

  // Fetch when filters change (reset to page 1)
  useEffect(() => {
    setPage(1)
    fetchItems(1)
  }, [stageString, cloudProvider, agdConfig, selectedWorkloads, contentFilter])

  // Fetch when page changes (without resetting page)
  useEffect(() => {
    fetchItems(page)
  }, [page])

  // Debounced search
  const handleSearchChange = (value: string) => {
    setSearch(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setPage(1)
      fetchItems(1)
    }, 300)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  // Active filter tracking
  const activeFilters: Array<{ label: string; onRemove: () => void }> = []
  if (cloudProvider) activeFilters.push({ label: cloudProvider, onRemove: () => setCloudProvider('') })
  if (agdConfig) activeFilters.push({ label: agdConfig, onRemove: () => setAgdConfig('') })
  selectedWorkloads.forEach(wl => {
    activeFilters.push({ label: wl, onRemove: () => setSelectedWorkloads(prev => prev.filter(w => w !== wl)) })
  })
  const hasActiveFilters = activeFilters.length > 0

  const clearAllFilters = () => {
    setCloudProvider('')
    setAgdConfig('')
    setSelectedWorkloads([])
  }

  // Item expand/detail handlers (unchanged from original)
  const handleExpand = async (ciName: string) => {
    const next = new Set(expandedItems)
    if (next.has(ciName)) {
      next.delete(ciName)
      setExpandedItems(next)
      return
    }
    next.add(ciName)
    setExpandedItems(next)
    if (!itemDetails[ciName]) {
      const detail = await api.getCatalogItem(ciName) as ItemDetail
      setItemDetails(prev => ({ ...prev, [ciName]: detail }))
      setNoteTexts(prev => ({ ...prev, [ciName]: detail.analysis?.notes || '' }))
      setContentPaths(prev => ({ ...prev, [ciName]: detail.content_path || '' }))
      setOverrideUrls(prev => ({ ...prev, [ciName]: detail.showroom_url_override || '' }))
      if (detail.analysis?.enrichment_review_needed) {
        setFlaggedItems(prev => new Set(prev).add(ciName))
      }
    }
  }

  const handleAnalyze = async (ciName: string) => {
    setAnalyzing(ciName)
    const { job_id } = await api.analyzeSingle(ciName)
    const poll = async () => {
      const result = await api.getJobStatus(job_id)
      if (result.status === 'complete' || result.status === 'failed') {
        setAnalyzing(null)
        fetchItems(page)
        if (expandedItems.has(ciName)) {
          const detail = await api.getCatalogItem(ciName) as ItemDetail
          setItemDetails(prev => ({ ...prev, [ciName]: detail }))
        }
      } else {
        setTimeout(poll, 3000)
      }
    }
    setTimeout(poll, 3000)
  }

  const handleAddTag = async (ciName: string) => {
    const tag = (newTags[ciName] || '').trim()
    if (!tag) return
    await api.addTag(ciName, 'label', tag)
    setNewTags(prev => ({ ...prev, [ciName]: '' }))
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetails(prev => ({ ...prev, [ciName]: detail }))
  }

  const handleRemoveTag = async (ciName: string, tagId: number) => {
    await api.removeTag(ciName, tagId)
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetails(prev => ({ ...prev, [ciName]: detail }))
  }

  const handleSaveNote = async (ciName: string) => {
    await api.setNote(ciName, noteTexts[ciName] || '')
  }

  const handleSetContentPath = async (ciName: string) => {
    const path = contentPaths[ciName]?.trim() || null
    setScanningPath(prev => ({ ...prev, [ciName]: true }))
    await api.setContentPath(ciName, path)
    setTimeout(async () => {
      const detail = await api.getCatalogItem(ciName) as ItemDetail
      setItemDetails(prev => ({ ...prev, [ciName]: detail }))
      setScanningPath(prev => ({ ...prev, [ciName]: false }))
      fetchItems(page)
    }, 5000)
  }

  const handleOverrideUrl = async (ciName: string) => {
    const url = overrideUrls[ciName]?.trim()
    if (!url) return
    await api.overrideUrl(ciName, url)
    const detail = await api.getCatalogItem(ciName) as ItemDetail
    setItemDetails(prev => ({ ...prev, [ciName]: detail }))
  }

  const handleFlag = async (ciName: string) => {
    await api.flagItem(ciName)
    setFlaggedItems(prev => new Set(prev).add(ciName))
    fetchItems(page)
  }

  return (
    <div className="curate-layout">
      {/* Primary bar */}
      <div className="filter-bar">
        <input
          className="filter-input"
          placeholder="Search by name or CI..."
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
        />
        <LcarsToggle label="dev" active={showDev} onToggle={() => setShowDev(!showDev)} />
        <LcarsToggle label="event" active={showEvent} onToggle={() => setShowEvent(!showEvent)} />
        <span style={{ color: '#666', fontSize: '14px', alignSelf: 'center' }}>
          {total} items
        </span>
      </div>

      {/* Filter panel */}
      <div className="filter-panel">
        <div className="filter-panel-header" onClick={() => setFiltersOpen(!filtersOpen)}>
          {filtersOpen ? (
            <>
              <span className="filter-panel-label">▾ Filters</span>
              {hasActiveFilters && (
                <button className="filter-panel-clear" onClick={(e) => { e.stopPropagation(); clearAllFilters() }}>
                  Clear all
                </button>
              )}
            </>
          ) : (
            <>
              <span className="filter-panel-label">▸ Filters</span>
              <div className="filter-panel-collapsed">
                {hasActiveFilters ? (
                  <div className="filter-chips">
                    {activeFilters.map(f => (
                      <span key={f.label} className="filter-chip" onClick={(e) => { e.stopPropagation(); f.onRemove() }}>
                        {f.label} ✕
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="filter-panel-muted">no filters active</span>
                )}
                {hasActiveFilters && (
                  <button className="filter-panel-clear" onClick={(e) => { e.stopPropagation(); clearAllFilters() }}>
                    Clear all
                  </button>
                )}
              </div>
            </>
          )}
        </div>
        {filtersOpen && (
          <div className="filter-panel-body">
            <div className="filter-panel-dropdowns">
              <div className="filter-panel-dropdown">
                <div className="filter-panel-dropdown-label">Cloud Provider</div>
                <select
                  className="filter-select"
                  value={cloudProvider}
                  onChange={(e) => setCloudProvider(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="">All providers</option>
                  {facets?.cloud_providers.map(cp => (
                    <option key={cp.cloud_provider} value={cp.cloud_provider}>{cp.cloud_provider}</option>
                  ))}
                </select>
              </div>
              <div className="filter-panel-dropdown">
                <div className="filter-panel-dropdown-label">Workloads</div>
                <WorkloadMultiSelect
                  options={facets?.workloads || []}
                  selected={selectedWorkloads}
                  onChange={setSelectedWorkloads}
                />
              </div>
              <div className="filter-panel-dropdown">
                <div className="filter-panel-dropdown-label">AgnosticD Config</div>
                <select
                  className="filter-select"
                  value={agdConfig}
                  onChange={(e) => setAgdConfig(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="">All configs</option>
                  {facets?.configs.map(c => (
                    <option key={c.agd_config} value={c.agd_config}>{c.agd_config}</option>
                  ))}
                </select>
              </div>
            </div>
            {hasActiveFilters && (
              <div className="filter-chips">
                {activeFilters.map(f => (
                  <span key={f.label} className="filter-chip" onClick={() => f.onRemove()}>
                    {f.label} ✕
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Curator filter panel — visible to curators/admins only */}
      {auth.isCurator && (
        <div className="curator-panel">
          <div className="filter-panel-header" onClick={() => setCuratorFiltersOpen(!curatorFiltersOpen)}>
            <span className="filter-panel-label">
              {curatorFiltersOpen ? '▾' : '▸'} Curator Filters
            </span>
            {contentFilter && (
              <button className="filter-panel-clear" onClick={(e) => { e.stopPropagation(); setContentFilter('') }}>
                Clear
              </button>
            )}
          </div>
          {curatorFiltersOpen && (
            <div className="curator-filter-pills">
              {(['unanalyzed', 'scan_failures', 'stale', 'needs_review'] as ContentFilter[]).map(cf => (
                <span
                  key={cf}
                  className={`curator-filter-pill${contentFilter === cf ? ' active' : ''}`}
                  onClick={() => setContentFilter(contentFilter === cf ? '' : cf)}
                >
                  {cf === 'scan_failures' ? 'Failures' : cf === 'needs_review' ? 'Needs Review' :
                   cf.charAt(0).toUpperCase() + cf.slice(1)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Results */}
      {loading ? (
        <div style={{ color: '#666', padding: '20px' }}>Loading...</div>
      ) : (
        <>
          {items.map(item => {
            const isExpanded = expandedItems.has(item.ci_name)
            const detail = itemDetails[item.ci_name]
            const isZt = isZtItem(item)

            return (
              <div key={item.ci_name} className="curate-item">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div
                      className="curate-item-title"
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleExpand(item.ci_name)}
                    >
                      {isExpanded ? '▾' : '▸'}{' '}
                      {item.display_name || item.ci_name}
                      {item.stage !== 'prod' && (
                        <span style={{
                          display: 'inline-block',
                          background: item.stage === 'dev' ? '#2a4a6a' : '#5a4a1a',
                          color: item.stage === 'dev' ? '#99ccff' : '#ffcc66',
                          borderRadius: '10px', padding: '2px 8px', fontSize: '10px',
                          fontWeight: 600, marginLeft: '6px',
                        }}>{item.stage.toUpperCase()}</span>
                      )}
                      {isZt && (
                        <span style={{ display: 'inline-block', background: '#1a3a2a', color: '#66cc99', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>ZT</span>
                      )}
                      {item.is_agd_v2 && (
                        <span style={{ display: 'inline-block', background: '#1a2a3a', color: '#73bcf7', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>v2</span>
                      )}
                      {item.scan_status === 'failed' && (
                        <span style={{ display: 'inline-block', background: '#5a2020', color: '#ff9999', borderRadius: '10px', padding: '2px 8px', fontSize: '10px', fontWeight: 600, marginLeft: '6px' }}>FAILED</span>
                      )}
                      {item.enrichment_review_needed && (
                        <span className="review-badge">needs review</span>
                      )}
                    </div>
                    <div className="curate-item-ci">{item.ci_name} · {item.category}</div>
                  </div>
                  {auth.isCurator && (
                    analyzing === item.ci_name ? (
                      <span style={{
                        color: '#e8a838', fontSize: '13px', padding: '5px 12px',
                        animation: 'pulse-bg 1.5s ease-in-out infinite',
                      }}>
                        Analyzing...
                      </span>
                    ) : (
                      <LcarsButton
                        variant="curator-secondary"
                        onClick={() => handleAnalyze(item.ci_name)}
                      >
                        Re-analyze
                      </LcarsButton>
                    )
                  )}
                </div>

                {isExpanded && detail && (
                  <div style={{ marginTop: '12px' }}>
                    {detail.scan_status === 'failed' && (
                      <div style={{ background: '#2a1515', border: '1px solid #5a2020', borderRadius: '6px', padding: '10px 14px', marginBottom: '12px' }}>
                        <div style={{ fontSize: '12px', color: '#ff9999', fontWeight: 600, marginBottom: '4px' }}>
                          Scan Error{detail.scan_error_class ? `: ${detail.scan_error_class}` : ''}
                        </div>
                        <div style={{ fontSize: '12px', color: '#cc8888', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                          {detail.scan_error || 'No error details available'}
                        </div>
                        {detail.scan_failed_at && (
                          <div style={{ fontSize: '11px', color: '#666', marginTop: '6px' }}>
                            Failed: {new Date(detail.scan_failed_at).toLocaleString()}
                          </div>
                        )}
                      </div>
                    )}
                    {detail.is_agd_v2 && (
                      <div style={{ background: '#111a2a', border: '1px solid #1a3050', borderRadius: '6px', padding: '10px 14px', marginBottom: '12px' }}>
                        <div style={{ fontSize: '11px', color: '#73bcf7', fontWeight: 600, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Infrastructure</div>
                        <div style={{ fontSize: '12px', color: '#ccc', display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '8px' }}>
                          <span>Config: <strong>{detail.agd_config || '—'}</strong></span>
                          {detail.cloud_provider && detail.cloud_provider !== 'none' && (
                            <span>Cloud: <strong>{detail.cloud_provider}</strong></span>
                          )}
                          {detail.ocp_version && <span>OCP: <strong>{detail.ocp_version}</strong></span>}
                          {detail.os_image && <span>OS: <strong>{detail.os_image}</strong></span>}
                          {detail.worker_instance_count && <span>Workers: <strong>{detail.worker_instance_count}</strong></span>}
                          {detail.control_plane_instance_count && <span>Control plane: <strong>{detail.control_plane_instance_count}</strong></span>}
                        </div>
                        {detail.workloads && detail.workloads.length > 0 && (
                          <div style={{ marginBottom: '6px' }}>
                            <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px' }}>Workloads ({detail.workloads.length})</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                              {detail.workloads.map((w, i) => (
                                <span key={i} style={{
                                  display: 'inline-block',
                                  background: '#1a2a1a', color: '#88bb88',
                                  border: '1px solid #2a4a2a',
                                  borderRadius: '10px', padding: '2px 8px', fontSize: '11px',
                                }}>{w.workload_role}</span>
                              ))}
                            </div>
                          </div>
                        )}
                        {detail.acl_groups && detail.acl_groups.length > 0 && (
                          <div style={{ fontSize: '11px', color: '#888' }}>
                            ACL: {detail.acl_groups.join(', ')}
                          </div>
                        )}
                      </div>
                    )}
                    {detail.analysis && (
                      <>
                        {detail.analysis.content_type && (
                          <div style={{ fontSize: '12px', color: '#73bcf7', marginBottom: '6px', display: 'flex', gap: '8px' }}>
                            <span>{detail.analysis.content_type}</span>
                            {detail.analysis.difficulty && <span style={{ color: '#888' }}>{detail.analysis.difficulty}</span>}
                            {detail.analysis.estimated_duration_min && <span style={{ color: '#888' }}>~{detail.analysis.estimated_duration_min} min</span>}
                          </div>
                        )}
                        {detail.analysis.summary && (
                          <p style={{ fontSize: '12px', color: '#aaa', marginBottom: '10px', lineHeight: '1.5' }}>
                            {detail.analysis.summary}
                          </p>
                        )}
                        {detail.analysis.products_json && detail.analysis.products_json.length > 0 && (
                          <div style={{ marginBottom: '6px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {detail.analysis.products_json.map((prod, i) => (
                              <span key={i} style={{
                                display: 'inline-block', background: '#2a1a3a',
                                color: '#9966CC', border: '1px solid #4a2a6a',
                                borderRadius: '10px', padding: '2px 8px', fontSize: '11px',
                              }}>{prod}</span>
                            ))}
                          </div>
                        )}
                        {detail.analysis.topics_json && detail.analysis.topics_json.length > 0 && (
                          <div style={{ marginBottom: '8px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {detail.analysis.topics_json.map((topic, i) => (
                              <span key={i} style={{
                                display: 'inline-block', background: '#1a2a3a',
                                color: '#73bcf7', border: '1px solid #2a4a6a',
                                borderRadius: '10px', padding: '2px 8px', fontSize: '11px',
                              }}>{topic}</span>
                            ))}
                          </div>
                        )}
                        {detail.analysis.learning_objectives_json && (
                          (() => {
                            const lo = detail.analysis.learning_objectives_json
                            const allObjectives = [...(lo.stated || []), ...(lo.inferred || [])]
                            if (allObjectives.length === 0) return null
                            return (
                              <div style={{ marginBottom: '10px' }}>
                                <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Learning Objectives</div>
                                <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12px', color: '#aaa', lineHeight: '1.6' }}>
                                  {allObjectives.map((obj, i) => (
                                    <li key={i}>{obj}</li>
                                  ))}
                                </ul>
                              </div>
                            )
                          })()
                        )}
                        {detail.analysis.modules_json && detail.analysis.modules_json.length > 0 && (
                          <div style={{ marginBottom: '10px' }}>
                            <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Modules ({detail.analysis.modules_json.length})</div>
                            {detail.analysis.modules_json.map((mod, i) => (
                              <div key={i} style={{ marginBottom: '6px', paddingLeft: '8px', borderLeft: '2px solid #2a2a3a' }}>
                                <div style={{ fontSize: '12px', color: '#ccc', fontWeight: 500 }}>{mod.title}</div>
                                {mod.topics && mod.topics.length > 0 && (
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px', marginTop: '3px' }}>
                                    {mod.topics.map((t, ti) => (
                                      <span key={ti} style={{
                                        display: 'inline-block', background: '#0d1520',
                                        color: '#5a9fd4', border: '1px solid #1e3350',
                                        borderRadius: '8px', padding: '1px 6px', fontSize: '10px',
                                      }}>{t}</span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}

                    {/* Curator tags */}
                    <div className="tag-list" style={{ marginBottom: '8px' }}>
                      {detail.tags.map(tag => (
                        <span
                          key={tag.id}
                          className="tag-pill-removable"
                          onClick={auth.isCurator ? () => handleRemoveTag(item.ci_name, tag.id) : undefined}
                          title={auth.isCurator ? 'Click to remove' : `Added by ${tag.added_by || 'unknown'}`}
                          style={{ cursor: auth.isCurator ? 'pointer' : 'default' }}
                        >
                          {tag.tag_value} {auth.isCurator && '×'}
                        </span>
                      ))}
                      {auth.isCurator && (
                        <input
                          type="text"
                          value={newTags[item.ci_name] || ''}
                          onChange={(e) => setNewTags(prev => ({ ...prev, [item.ci_name]: e.target.value }))}
                          onKeyDown={(e) => { if (e.key === 'Enter') handleAddTag(item.ci_name) }}
                          placeholder="+ add tag"
                          style={{
                            background: 'transparent', border: '1px dashed #3a5a3a',
                            color: '#5cb85c', padding: '3px 10px', borderRadius: '10px',
                            fontSize: '12px', width: '110px', outline: 'none',
                          }}
                        />
                      )}
                    </div>

                    {/* Curator controls */}
                    {auth.isCurator && (
                      <>
                        <input
                          type="text"
                          value={noteTexts[item.ci_name] || ''}
                          onChange={(e) => setNoteTexts(prev => ({ ...prev, [item.ci_name]: e.target.value }))}
                          onBlur={() => handleSaveNote(item.ci_name)}
                          onKeyDown={(e) => { if (e.key === 'Enter') handleSaveNote(item.ci_name) }}
                          placeholder="Add a note..."
                          style={{
                            background: 'var(--bg-card)', border: '1px solid #333',
                            color: '#aaa', padding: '6px 10px', borderRadius: '4px',
                            fontSize: '13px', width: '100%', fontStyle: 'italic',
                            marginBottom: '8px', outline: 'none',
                          }}
                        />
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                          <input
                            type="text"
                            value={overrideUrls[item.ci_name] ?? ''}
                            onChange={(e) => setOverrideUrls(prev => ({ ...prev, [item.ci_name]: e.target.value }))}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleOverrideUrl(item.ci_name) }}
                            placeholder="Override Showroom URL (full git repo URL)"
                            style={{
                              background: 'var(--bg-card)', border: '1px solid #333',
                              color: '#aaa', padding: '6px 10px', borderRadius: '4px',
                              fontSize: '13px', flex: 1, outline: 'none',
                            }}
                          />
                          <LcarsButton
                            variant="curator-secondary"
                            onClick={() => handleOverrideUrl(item.ci_name)}
                          >
                            Set URL
                          </LcarsButton>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                          <input
                            type="text"
                            value={contentPaths[item.ci_name] ?? ''}
                            onChange={(e) => setContentPaths(prev => ({ ...prev, [item.ci_name]: e.target.value }))}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleSetContentPath(item.ci_name) }}
                            placeholder="Content path (e.g. docs/labs/)"
                            style={{
                              background: 'var(--bg-card)', border: '1px solid #333',
                              color: '#aaa', padding: '6px 10px', borderRadius: '4px',
                              fontSize: '13px', flex: 1, outline: 'none',
                            }}
                          />
                          <LcarsButton
                            variant="curator-secondary"
                            onClick={() => handleSetContentPath(item.ci_name)}
                            disabled={scanningPath[item.ci_name]}
                          >
                            {scanningPath[item.ci_name] ? 'Scanning...' : 'Set & Scan'}
                          </LcarsButton>
                        </div>
                        {scanningPath[item.ci_name] && (
                          <div style={{ fontSize: '12px', color: '#e8a838', marginBottom: '8px', animation: 'pulse-bg 1.5s ease-in-out infinite' }}>
                            Content path updated — scanning with new path...
                          </div>
                        )}
                        <LcarsButton
                          variant="curator-secondary"
                          onClick={() => handleFlag(item.ci_name)}
                          disabled={flaggedItems.has(item.ci_name)}
                        >
                          {flaggedItems.has(item.ci_name) ? '✓ Flagged for review' : 'Flag for review'}
                        </LcarsButton>
                      </>
                    )}

                    {/* Links */}
                    <div style={{ marginTop: '10px', fontSize: '13px', display: 'flex', gap: '16px' }}>
                      <a
                        href={catalogUrl(item.ci_name, item.catalog_namespace || 'babylon-catalog-prod')}
                        target="_blank" rel="noopener noreferrer"
                        style={{ color: '#73bcf7' }}
                      >
                        RHDP Catalog
                      </a>
                      {item.showroom_url && (
                        <a href={item.showroom_url} target="_blank" rel="noopener noreferrer" style={{ color: '#73bcf7' }}>
                          Showroom Repo
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/pages/BrowsePage.tsx src/frontend/src/styles/lcars.css
git commit -m "browse: Rewrite with server-side filtering, collapsible panel, and pagination"
```

---

### Task 7: Update Admin Page Deep Links

**Files:**
- Modify: `src/frontend/src/pages/AdminPage.tsx` — update `navigate()` calls

The Admin page has clickable counts that deep-link to Browse with a `?filter=` param. These need to change to `?content_filter=`.

- [ ] **Step 1: Update the three `navigate()` calls in `AdminPage.tsx`**

Change line 507:
```
navigate('/browse?filter=unanalyzed')
```
to:
```
navigate('/browse?content_filter=unanalyzed')
```

Change line 516:
```
navigate('/browse?filter=stale')
```
to:
```
navigate('/browse?content_filter=stale')
```

Change line 525:
```
navigate('/browse?filter=scan_failures')
```
to:
```
navigate('/browse?content_filter=scan_failures')
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/pages/AdminPage.tsx
git commit -m "admin: Update Browse deep links to use content_filter param"
```

---

### Task 8: Manual Testing

No new files. This task verifies the full feature end-to-end in a browser.

- [ ] **Step 1: Start dev services**

Run: `cd /Users/nstephan/devel/rcars-advisory && ./dev-services.sh start`

- [ ] **Step 2: Test Browse page basic loading**

Open http://localhost:3000/browse. Verify:
- Page loads with items (should show ~350 prod items)
- Numbered pagination appears at the bottom
- Item count shows in the primary bar

- [ ] **Step 3: Test filter panel**

Click "Filters" to expand the panel. Verify:
- Three dropdowns appear: Cloud Provider, Workloads, AgnosticD Config
- Select "ec2" from Cloud Provider — items filter, count updates, green chip appears
- Select "OpenShift AI" from Workloads — results narrow further (AND semantics)
- Collapse the panel — chips remain visible in the collapsed bar
- Click ✕ on a chip — that filter is removed
- Click "Clear all" — all filters removed

- [ ] **Step 4: Test search**

Type "openshift" in the search box. Verify:
- Results update after ~300ms debounce
- URL updates with `?search=openshift`
- Page resets to 1

- [ ] **Step 5: Test stage toggles**

Click "dev" toggle. Verify:
- Dev items appear in the results
- URL updates with `?stage=prod,dev`

- [ ] **Step 6: Test pagination**

Navigate to a page with many results (clear all filters). Verify:
- Page numbers appear: `[1] 2 3 ... 20 >`
- Click page 10 — results change, URL shows `?page=10`
- Pagination shows: `< 1 ... 9 [10] 11 ... 20 >`
- Applying a filter resets to page 1

- [ ] **Step 7: Test curator filters (requires curator role)**

Verify the amber "Curator Filters" panel appears below the main filter panel. Click to expand. Verify:
- Four pills: Unanalyzed, Failures, Stale, Needs Review
- Click "Failures" — only failed items show
- Click "Failures" again — filter deactivates
- Regular users do NOT see this panel

- [ ] **Step 8: Test Admin deep links**

Go to Admin > Catalog Status. Click the failure count. Verify:
- Navigates to `/browse?content_filter=scan_failures`
- Browse page loads with curator filter panel open and "Failures" pill active

- [ ] **Step 9: Test URL state persistence**

Apply filters (e.g. cloud_provider=ec2, workloads=OpenShift AI, page=2). Copy the URL. Open in a new tab. Verify:
- Same filters are applied
- Same page is shown
