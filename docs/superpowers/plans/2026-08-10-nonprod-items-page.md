# Non-Prod Items Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface catalog items that have no production stage variant with usage metrics and retirement workflow actions, giving curators visibility into the dev/event/test-only tail of the catalog.

**Architecture:** New `nonprod_usage` table stores windowed usage metrics (6m/12m) synced from the reporting MCP during `run_reporting_sync()`. Three new API endpoints (`GET /analysis/nonprod`, `PUT/DELETE /analysis/nonprod/ignore/{base_name}`) serve a new `NonProdItemsPage` that reuses the existing sidebar filter + sortable table layout from `PerformancePage`. Retirement workflow reuses existing endpoints and `WorkflowDrawer` component.

**Tech Stack:** Python 3.11 (FastAPI 2.0, psycopg, structlog), React 19 (TypeScript, PatternFly 6), PostgreSQL + pgvector.

## Global Constraints

- Jira: RHDPCD-661
- Branch: `feature/dev-items-page`
- No scoring, no cost columns, no channel tabs — explicitly excluded per spec
- Non-prod sync uses **unfiltered** MCP queries (no `PROVISION_FILTERS`) — all environments, all users
- Only two windows: 6m and 12m (not 3m/9m)
- All endpoints `require_curator`
- Retirement workflow reuses existing `/analysis/performance/workflow/{base_name}/*` endpoints — no new workflow endpoints

---

### Task 1: Schema — Add `nonprod_usage` Table to `SCHEMA_SQL`

**Files:**
- Modify: `src/api/rcars/db/database.py:25-230` (SCHEMA_SQL block)

**Interfaces:**
- Consumes: Nothing — this is the foundational schema change
- Produces: `nonprod_usage` table available for all subsequent tasks

- [ ] **Step 1: Write failing test**

```python
# tests/test_nonprod.py
import pytest
from rcars.db.database import SCHEMA_SQL

class TestNonprodSchema:
    def test_nonprod_usage_table_in_schema(self):
        assert "CREATE TABLE IF NOT EXISTS nonprod_usage" in SCHEMA_SQL

    def test_nonprod_usage_has_windowed_metrics(self):
        assert "windowed_metrics" in SCHEMA_SQL.split("nonprod_usage")[1].split(");")[0]

    def test_nonprod_usage_has_ignored_until(self):
        assert "ignored_until" in SCHEMA_SQL.split("nonprod_usage")[1].split(");")[0]
```

- [ ] **Step 2: Run test, verify fails**

Run: `cd src/api && python -m pytest tests/test_nonprod.py -v`
Expected: FAIL — `nonprod_usage` not in SCHEMA_SQL

- [ ] **Step 3: Add nonprod_usage table to SCHEMA_SQL**

In `database.py`, add after the `retirement_workflow` table definition (after line ~227, before the `content_similarity` table):

```python
-- ═══════════════════════════════════════════════════════════════════
-- nonprod_usage — usage metrics for items without a prod stage
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS nonprod_usage (
    content_id        TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    catalog_base_name TEXT NOT NULL,
    provisions        INTEGER DEFAULT 0,
    requests          INTEGER DEFAULT 0,
    completions       INTEGER DEFAULT 0,
    unique_users      INTEGER DEFAULT 0,
    success_ratio     REAL DEFAULT 0,
    failure_ratio     REAL DEFAULT 0,
    first_provision   TEXT,
    last_provision    TEXT,
    windowed_metrics  JSONB DEFAULT '{}'::jsonb,
    ignored_until     DATE,
    synced_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nu_base_name ON nonprod_usage(catalog_base_name);
```

Also add `"nonprod_usage"` to the `TABLES` list (around line 489, the list used by `create_schema` drop logic).

- [ ] **Step 4: Run test, verify passes**

Run: `cd src/api && python -m pytest tests/test_nonprod.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/database.py src/api/tests/test_nonprod.py
git commit -m "[RHDPCD-661] Add nonprod_usage table to SCHEMA_SQL"
```

---

### Task 2: DB Methods — `get_nonprod_base_names()`, `upsert_nonprod_usage()`, `list_nonprod_items()`, ignore/clear

**Files:**
- Modify: `src/api/rcars/db/database.py` (add methods to Database class, after the performance methods section ~line 2460)
- Modify: `src/api/tests/test_nonprod.py` (add tests)

**Interfaces:**
- Consumes: `nonprod_usage` table from Task 1, existing `content_entities` and `babylon_items` tables
- Produces:
  - `get_nonprod_base_names() -> dict[str, str]` — returns `{base_name: content_id}` for items where no active variant has `stage = 'prod'`
  - `upsert_nonprod_usage(rows: list[dict]) -> int` — upserts into `nonprod_usage`, returns count
  - `list_nonprod_items(sort_by, sort_dir, content_type, stage, namespace, search, window, status) -> list[dict]` — returns items joined with entity/babylon data
  - `set_nonprod_ignored(content_id: str, until: str) -> bool`
  - `clear_nonprod_ignored(content_id: str) -> bool`
  - `delete_orphan_nonprod_data(valid_content_ids: set[str]) -> int`

- [ ] **Step 1: Write failing tests**

```python
# Add to tests/test_nonprod.py
class TestGetNonprodBaseNames:
    """Tests for get_nonprod_base_names — requires live DB with test data."""

    def test_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "get_nonprod_base_names")

    def test_returns_dict(self):
        from rcars.db.database import Database
        assert callable(getattr(Database, "get_nonprod_base_names"))


class TestUpsertNonprodUsage:
    def test_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "upsert_nonprod_usage")


class TestListNonprodItems:
    def test_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "list_nonprod_items")


class TestNonprodIgnore:
    def test_set_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "set_nonprod_ignored")

    def test_clear_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "clear_nonprod_ignored")
```

- [ ] **Step 2: Run tests, verify fails**

Run: `cd src/api && python -m pytest tests/test_nonprod.py -v`
Expected: FAIL — methods don't exist

- [ ] **Step 3: Implement DB methods**

Add to `Database` class in `database.py`, after the existing `get_fully_retired_base_names()` method (~line 2477):

```python
    # ── Non-Prod Usage ──

    def get_nonprod_base_names(self) -> dict[str, str]:
        """Return {base_name: content_id} for items with no active prod-stage variant."""
        sql = """
            WITH base_stages AS (
                SELECT
                    substring(bi.ci_name FROM '^(.+)\\.[^.]+$') AS base_name,
                    bi.content_id,
                    bi.stage,
                    ce.retired_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY substring(bi.ci_name FROM '^(.+)\\.[^.]+$')
                        ORDER BY CASE bi.stage WHEN 'dev' THEN 0 WHEN 'event' THEN 1 WHEN 'test' THEN 2 ELSE 3 END
                    ) AS rn
                FROM babylon_items bi
                JOIN content_entities ce ON ce.content_id = bi.content_id
                WHERE ce.retired_at IS NULL
            )
            SELECT base_name, content_id
            FROM base_stages
            WHERE rn = 1
              AND base_name NOT IN (
                  SELECT DISTINCT substring(bi2.ci_name FROM '^(.+)\\.[^.]+$')
                  FROM babylon_items bi2
                  JOIN content_entities ce2 ON ce2.content_id = bi2.content_id
                  WHERE bi2.stage = 'prod' AND ce2.retired_at IS NULL
              )
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return {r["base_name"]: r["content_id"] for r in cur.fetchall() if r["base_name"]}

    def upsert_nonprod_usage(self, rows: list[dict]) -> int:
        """Upsert rows into nonprod_usage. Returns count of rows upserted."""
        if not rows:
            return 0
        sql = """
            INSERT INTO nonprod_usage (
                content_id, catalog_base_name,
                provisions, requests, completions, unique_users,
                success_ratio, failure_ratio,
                first_provision, last_provision,
                windowed_metrics, synced_at
            ) VALUES (
                %(content_id)s, %(catalog_base_name)s,
                %(provisions)s, %(requests)s, %(completions)s, %(unique_users)s,
                %(success_ratio)s, %(failure_ratio)s,
                %(first_provision)s, %(last_provision)s,
                %(windowed_metrics)s, NOW()
            )
            ON CONFLICT (content_id) DO UPDATE SET
                catalog_base_name = EXCLUDED.catalog_base_name,
                provisions = EXCLUDED.provisions,
                requests = EXCLUDED.requests,
                completions = EXCLUDED.completions,
                unique_users = EXCLUDED.unique_users,
                success_ratio = EXCLUDED.success_ratio,
                failure_ratio = EXCLUDED.failure_ratio,
                first_provision = EXCLUDED.first_provision,
                last_provision = EXCLUDED.last_provision,
                windowed_metrics = EXCLUDED.windowed_metrics,
                synced_at = NOW()
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                for row in rows:
                    cur.execute(sql, row)
            conn.commit()
        return len(rows)

    def list_nonprod_items(
        self,
        sort_by: str = "provisions",
        sort_dir: str = "desc",
        content_type: str | None = None,
        stage: str | None = None,
        namespace: str | None = None,
        search: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """List non-prod items with joined entity/babylon data."""
        conditions = []
        params: dict = {}

        if content_type:
            conditions.append("ce.content_type = %(content_type)s")
            params["content_type"] = content_type
        if stage:
            conditions.append("bi.stage = %(stage)s")
            params["stage"] = stage
        if namespace:
            conditions.append("bi.catalog_namespace = %(namespace)s")
            params["namespace"] = namespace
        if search:
            conditions.append("(ce.display_name ILIKE %(search)s OR nu.catalog_base_name ILIKE %(search)s)")
            params["search"] = f"%{search}%"
        if status == "muted":
            conditions.append("nu.ignored_until IS NOT NULL AND nu.ignored_until >= CURRENT_DATE")
        elif status == "active":
            conditions.append("(nu.ignored_until IS NULL OR nu.ignored_until < CURRENT_DATE)")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

        allowed_sorts = {"provisions", "unique_users", "success_ratio", "failure_ratio", "display_name"}
        if sort_by == "display_name":
            order_expr = "ce.display_name"
        elif sort_by in allowed_sorts:
            order_expr = f"nu.{sort_by}"
        else:
            order_expr = "nu.provisions"

        sql = f"""
            SELECT nu.content_id, nu.catalog_base_name,
                   nu.provisions, nu.requests, nu.completions, nu.unique_users,
                   nu.success_ratio, nu.failure_ratio,
                   nu.first_provision, nu.last_provision,
                   nu.windowed_metrics, nu.ignored_until, nu.synced_at,
                   ce.display_name, ce.content_type,
                   bi.stage, bi.catalog_namespace, bi.ci_name,
                   CASE WHEN rw.step_approved_at IS NOT NULL THEN rw.status END AS workflow_status,
                   rw.jira_key, rw.retirement_target_date
            FROM nonprod_usage nu
            JOIN content_entities ce ON ce.content_id = nu.content_id
            LEFT JOIN babylon_items bi ON bi.content_id = nu.content_id
            LEFT JOIN retirement_workflow rw ON rw.content_id = nu.content_id
            {where}
            ORDER BY {order_expr} {direction} NULLS LAST
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def set_nonprod_ignored(self, content_id: str, until: str) -> bool:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE nonprod_usage SET ignored_until = %s WHERE content_id = %s",
                    (until, content_id),
                )
                ok = cur.rowcount > 0
            conn.commit()
        return ok

    def clear_nonprod_ignored(self, content_id: str) -> bool:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE nonprod_usage SET ignored_until = NULL WHERE content_id = %s",
                    (content_id,),
                )
                ok = cur.rowcount > 0
            conn.commit()
        return ok

    def delete_orphan_nonprod_data(self, valid_content_ids: set[str]) -> int:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                if valid_content_ids:
                    cur.execute(
                        "DELETE FROM nonprod_usage WHERE content_id != ALL(%s)",
                        (list(valid_content_ids),),
                    )
                else:
                    cur.execute("DELETE FROM nonprod_usage WHERE content_id NOT IN (SELECT content_id FROM content_entities)")
                deleted = cur.rowcount
            conn.commit()
        return deleted
```

- [ ] **Step 4: Run tests, verify passes**

Run: `cd src/api && python -m pytest tests/test_nonprod.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/database.py src/api/tests/test_nonprod.py
git commit -m "[RHDPCD-661] Add nonprod_usage DB methods"
```

---

### Task 3: Sync — Add `_sync_nonprod_usage()` to Reporting Sync

**Files:**
- Modify: `src/api/rcars/services/reporting_sync.py` (add helper + call from `run_reporting_sync`)
- Modify: `src/api/tests/test_nonprod.py` (add test)

**Interfaces:**
- Consumes: `db.get_nonprod_base_names()` from Task 2, `mcp_query()` and `_build_provisions_sql()` from `reporting_sync.py`, `db.upsert_nonprod_usage()` and `db.delete_orphan_nonprod_data()` from Task 2
- Produces: `_sync_nonprod_usage(db, url: str, token: str) -> dict` — called at end of `run_reporting_sync()`, returns summary dict with `nonprod_synced` count

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_nonprod.py
class TestSyncNonprodUsage:
    def test_function_exists(self):
        from rcars.services.reporting_sync import _sync_nonprod_usage
        assert callable(_sync_nonprod_usage)
```

- [ ] **Step 2: Run test, verify fails**

Run: `cd src/api && python -m pytest tests/test_nonprod.py::TestSyncNonprodUsage -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement `_sync_nonprod_usage`**

Add to `reporting_sync.py`, before `run_reporting_sync()`:

```python
NONPROD_WINDOWS = {"6m": 182, "12m": 365}


def _build_nonprod_provisions_sql(start_date: str) -> str:
    """Like _build_provisions_sql but WITHOUT PROVISION_FILTERS — all envs, all users."""
    return f"""
        SELECT
            ci.name AS catalog_base_name,
            COUNT(DISTINCT ps.uuid) AS provisions,
            COUNT(DISTINCT ps.request_id) AS requests,
            COALESCE(SUM(ps.user_experiences), 0) AS completions,
            COUNT(DISTINCT ps.user_id) AS unique_users,
            ROUND(
                SUM(ps.provision_success)::numeric
                / NULLIF(SUM(ps.provision_success) + SUM(ps.provision_failure), 0), 4
            ) AS success_ratio,
            ROUND(
                SUM(ps.provision_failure)::numeric
                / NULLIF(SUM(ps.provision_success) + SUM(ps.provision_failure), 0), 4
            ) AS failure_ratio,
            MIN(ps.provisioned_at)::date::text AS first_provision,
            MAX(ps.provisioned_at)::date::text AS last_provision
        FROM provisions_summary ps
        JOIN catalog_items ci ON ci.id = ps.catalog_id
        WHERE ps.provisioned_at >= '{start_date}'
        GROUP BY ci.name
    """


def _sync_nonprod_usage(db, url: str, token: str) -> dict:
    """Sync usage metrics for items that have no prod stage."""
    log = logger.bind(action="nonprod_sync")

    nonprod_map = db.get_nonprod_base_names()
    if not nonprod_map:
        log.info("no_nonprod_items")
        return {"nonprod_synced": 0, "nonprod_orphans": 0}

    log.info("nonprod_items_found", count=len(nonprod_map))

    w_data: dict[str, dict[str, dict]] = {}
    for wk, days in NONPROD_WINDOWS.items():
        w_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        log.info("fetching_nonprod_window", window=wk, start=w_start)
        rows = mcp_query(_build_nonprod_provisions_sql(w_start), url=url, token=token)
        w_data[wk] = {r["catalog_base_name"]: r for r in rows}
        log.info("fetched_nonprod_window", window=wk, rows=len(rows))

    upsert_rows = []
    data_12m = w_data.get("12m", {})
    for base_name, content_id in nonprod_map.items():
        row_12m = data_12m.get(base_name, {})

        windowed = {}
        for wk in NONPROD_WINDOWS:
            r = w_data.get(wk, {}).get(base_name, {})
            windowed[wk] = {
                "provisions": int(r.get("provisions", 0)),
                "requests": int(r.get("requests", 0)),
                "completions": int(r.get("completions", 0)),
                "unique_users": int(r.get("unique_users", 0)),
                "success_ratio": float(r.get("success_ratio", 0) or 0),
                "failure_ratio": float(r.get("failure_ratio", 0) or 0),
            }

        upsert_rows.append({
            "content_id": content_id,
            "catalog_base_name": base_name,
            "provisions": int(row_12m.get("provisions", 0)),
            "requests": int(row_12m.get("requests", 0)),
            "completions": int(row_12m.get("completions", 0)),
            "unique_users": int(row_12m.get("unique_users", 0)),
            "success_ratio": float(row_12m.get("success_ratio", 0) or 0),
            "failure_ratio": float(row_12m.get("failure_ratio", 0) or 0),
            "first_provision": row_12m.get("first_provision"),
            "last_provision": row_12m.get("last_provision"),
            "windowed_metrics": json.dumps(windowed),
        })

    upserted = db.upsert_nonprod_usage(upsert_rows)
    valid_ids = set(nonprod_map.values())
    orphans = db.delete_orphan_nonprod_data(valid_ids)

    summary = {"nonprod_synced": upserted, "nonprod_orphans": orphans}
    log.info("nonprod_sync_complete", **summary)
    return summary
```

Then at the end of `run_reporting_sync()`, before the `summary = {` line (~line 814), add:

```python
    # Sync non-prod usage (items without a prod stage)
    nonprod_summary = _sync_nonprod_usage(db, url, token)
```

And merge `nonprod_summary` into the returned summary dict:

```python
    summary = {
        # ... existing keys ...
        **nonprod_summary,
    }
```

- [ ] **Step 4: Run test, verify passes**

Run: `cd src/api && python -m pytest tests/test_nonprod.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/reporting_sync.py src/api/tests/test_nonprod.py
git commit -m "[RHDPCD-661] Add nonprod usage sync to reporting pipeline"
```

---

### Task 4: API Endpoints — GET, PUT/DELETE ignore

**Files:**
- Modify: `src/api/rcars/api/routes/analysis.py` (add 3 endpoints)
- Modify: `src/api/tests/test_nonprod.py` (add test)

**Interfaces:**
- Consumes: `db.list_nonprod_items()`, `db.set_nonprod_ignored()`, `db.clear_nonprod_ignored()`, `_base_name_to_content_id()` from Task 2
- Produces:
  - `GET /analysis/nonprod` — returns `{"items": [...], "total": N, "synced_at": "...", "window": "12m"}`
  - `PUT /analysis/nonprod/ignore/{base_name}` — sets 30-day mute
  - `DELETE /analysis/nonprod/ignore/{base_name}` — clears mute

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_nonprod.py
class TestNonprodRouteExists:
    def test_nonprod_endpoint_registered(self):
        """Verify the nonprod routes exist on the analysis router."""
        from rcars.api.routes.analysis import router
        paths = [r.path for r in router.routes]
        assert "/nonprod" in paths
        assert "/nonprod/ignore/{base_name}" in paths
```

- [ ] **Step 2: Run test, verify fails**

Run: `cd src/api && python -m pytest tests/test_nonprod.py::TestNonprodRouteExists -v`
Expected: FAIL — routes not registered

- [ ] **Step 3: Implement endpoints**

Add to `src/api/rcars/api/routes/analysis.py`, after the existing `unignore_item` endpoint (~line 628) and before the `analyze_single` endpoint:

```python
NONPROD_WINDOWS = {"6m", "12m"}


@router.get(
    "/nonprod",
    tags=["Non-Prod Items"],
    summary="Non-prod items dashboard",
    description="Returns catalog items with no production stage, with usage metrics. Curator-only.",
)
async def nonprod_dashboard(
    request: Request,
    user: str = Depends(require_curator),
    sort_by: str = Query("provisions"),
    sort_dir: str = Query("desc"),
    content_type: str | None = Query(None),
    stage: str | None = Query(None),
    namespace: str | None = Query(None),
    search: str | None = Query(None),
    window: str = Query("12m"),
    status: str | None = Query(None),
):
    if window not in NONPROD_WINDOWS:
        raise HTTPException(400, f"window must be one of {sorted(NONPROD_WINDOWS)}")

    db = request.app.state.db
    items = db.list_nonprod_items(
        sort_by=sort_by, sort_dir=sort_dir,
        content_type=content_type, stage=stage,
        namespace=namespace, search=search,
        status=status,
    )

    import json as _json
    from datetime import date as _date
    today = _date.today()

    # Collect all base_names for stage lookup
    base_names = [i["catalog_base_name"] for i in items]
    stages_map = db.get_stages_for_base_names(base_names, include_retired=False)

    for item in items:
        # Apply windowed metrics overlay
        wm = item.get("windowed_metrics") or {}
        if isinstance(wm, str):
            try:
                wm = _json.loads(wm)
            except (ValueError, TypeError):
                wm = {}
        w = wm.get(window, {})
        if w:
            item["provisions"] = w.get("provisions", 0)
            item["requests"] = w.get("requests", 0)
            item["completions"] = w.get("completions", 0)
            item["unique_users"] = w.get("unique_users", 0)
            item["success_ratio"] = w.get("success_ratio", 0)
            item["failure_ratio"] = w.get("failure_ratio", 0)

        # Enrich with stages from all variants of this base name
        item["stages"] = stages_map.get(item["catalog_base_name"], [])

        # Handle ignored_until
        iu = item.get("ignored_until")
        if iu and isinstance(iu, _date) and iu >= today:
            item["ignored_until"] = iu.isoformat()
        elif iu and isinstance(iu, str) and iu >= today.isoformat():
            pass
        else:
            item["ignored_until"] = None

    # Re-sort after windowed overlay
    allowed_sorts = {"provisions", "unique_users", "success_ratio", "failure_ratio", "display_name"}
    if sort_by in allowed_sorts:
        reverse = sort_dir.lower() == "desc"
        if sort_by == "display_name":
            items.sort(key=lambda i: (i.get(sort_by) or ""), reverse=reverse)
        else:
            items.sort(key=lambda i: (i.get(sort_by) or 0), reverse=reverse)

    synced_at = items[0]["synced_at"] if items and items[0].get("synced_at") else None

    return {
        "items": items,
        "total": len(items),
        "synced_at": str(synced_at) if synced_at else None,
        "window": window,
    }


@router.put(
    "/nonprod/ignore/{base_name}",
    tags=["Non-Prod Items"],
    summary="Mute non-prod item for 30 days",
)
async def nonprod_ignore(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    from datetime import date, timedelta
    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        raise HTTPException(404, f"Item not found: {base_name}")
    until = (date.today() + timedelta(days=30)).isoformat()
    ok = db.set_nonprod_ignored(content_id, until)
    if not ok:
        raise HTTPException(404, f"Item not found in nonprod_usage: {base_name}")
    db.log_action(base_name, "nonprod_muted", user, f"Muted until {until}")
    return {"status": "ok", "ignored_until": until}


@router.delete(
    "/nonprod/ignore/{base_name}",
    tags=["Non-Prod Items"],
    summary="Unmute non-prod item",
)
async def nonprod_unignore(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        raise HTTPException(404, f"Item not found: {base_name}")
    ok = db.clear_nonprod_ignored(content_id)
    if not ok:
        raise HTTPException(404, f"Item not found in nonprod_usage: {base_name}")
    db.log_action(base_name, "nonprod_unmuted", user, "Unmuted")
    return {"status": "ok"}
```

**Important:** The `/nonprod` GET route must be defined BEFORE the existing `/{identifier}` POST route (line ~632), otherwise FastAPI will match "nonprod" as an `{identifier}` path parameter. Place these three endpoints between the `unignore_item` endpoint and the `analyze_single` endpoint.

- [ ] **Step 4: Run test, verify passes**

Run: `cd src/api && python -m pytest tests/test_nonprod.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/api/routes/analysis.py src/api/tests/test_nonprod.py
git commit -m "[RHDPCD-661] Add nonprod API endpoints"
```

---

### Task 5: Frontend API Client — Add nonprod methods to `api.ts`

**Files:**
- Modify: `src/frontend/src/services/api.ts`

**Interfaces:**
- Consumes: API endpoints from Task 4
- Produces:
  - `api.getNonprodItems(params)` — calls `GET /analysis/nonprod`
  - `api.ignoreNonprodItem(baseName)` — calls `PUT /analysis/nonprod/ignore/{baseName}`
  - `api.unignoreNonprodItem(baseName)` — calls `DELETE /analysis/nonprod/ignore/{baseName}`
  - `NonProdItem` interface
  - `NonProdDashboardResponse` interface

- [ ] **Step 1: Add interfaces and methods**

Add the `NonProdItem` and `NonProdDashboardResponse` interfaces after the existing `PerformanceDashboardResponse` interface, and add the API methods to the `api` object:

```typescript
// Add to interfaces section (after PerformanceDashboardResponse)
export interface NonProdItem {
  content_id: string
  catalog_base_name: string
  display_name: string
  content_type: string | null
  stage: string | null
  catalog_namespace: string | null
  ci_name: string | null
  provisions: number
  requests: number
  completions: number
  unique_users: number
  success_ratio: number
  failure_ratio: number
  first_provision: string | null
  last_provision: string | null
  stages: Array<{ stage: string; ci_name: string; catalog_url: string; has_showroom: boolean }>
  workflow_status?: string | null
  jira_key?: string | null
  retirement_target_date?: string | null
  ignored_until?: string | null
}

export interface NonProdDashboardResponse {
  items: NonProdItem[]
  total: number
  synced_at: string | null
  window: string
}
```

```typescript
// Add to api object, after the ignoreItem/unignoreItem entries

  // Non-prod items
  getNonprodItems: (params?: {
    sort_by?: string; sort_dir?: string; content_type?: string;
    stage?: string; namespace?: string; search?: string;
    window?: string; status?: string;
  }) => {
    const qs = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
      })
    }
    const query = qs.toString()
    return request<NonProdDashboardResponse>(`/analysis/nonprod${query ? '?' + query : ''}`)
  },

  ignoreNonprodItem: (baseName: string) =>
    request<{ status: string; ignored_until: string }>(`/analysis/nonprod/ignore/${encodeURIComponent(baseName)}`, { method: 'PUT' }),

  unignoreNonprodItem: (baseName: string) =>
    request<{ status: string }>(`/analysis/nonprod/ignore/${encodeURIComponent(baseName)}`, { method: 'DELETE' }),
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No new errors related to the added code

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/services/api.ts
git commit -m "[RHDPCD-661] Add nonprod API client methods"
```

---

### Task 6: Frontend Page — `NonProdItemsPage.tsx`

**Files:**
- Create: `src/frontend/src/pages/NonProdItemsPage.tsx`

**Interfaces:**
- Consumes: `api.getNonprodItems()`, `api.ignoreNonprodItem()`, `api.unignoreNonprodItem()`, `NonProdItem` interface from Task 5. `WorkflowDrawer` component from `../components/performance/WorkflowDrawer`. `useAuth` hook.
- Produces: `NonProdItemsPage` React component — page with sidebar filters, sortable table, window toggle, mute/unmute actions, retirement workflow drawer

This is the largest task. The page follows the same layout pattern as `PerformancePage.tsx` (Browse layout with filter sidebar + sortable table) but is simpler: no scoring, no cost columns, no channels, no range filters, no score popovers.

- [ ] **Step 1: Create the page component**

Create `src/frontend/src/pages/NonProdItemsPage.tsx`:

```tsx
import { useState, useEffect, useCallback, useRef, Fragment } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, NonProdItem } from '../services/api'
import { WorkflowDrawer } from '../components/performance/WorkflowDrawer'
import { useAuth } from '../hooks/useAuth'

type TimeWindow = '6m' | '12m'
type StatusFilter = 'all' | 'active' | 'muted'
type SortField = 'provisions' | 'unique_users' | 'success_ratio' | 'failure_ratio' | 'display_name'

const stageBadgeClass: Record<string, string> = {
  prod: 'ca-env-prod', event: 'ca-env-event', dev: 'ca-env-dev', test: 'ca-env-test',
}

function WorkflowInlineBadge({ status }: { status: string }) {
  const labels: Record<string, string> = { approved: 'recommended', notified: 'recommended', started: 'in progress' }
  return <span className="ret-inline-badge">{labels[status] || status}</span>
}

export function NonProdItemsPage() {
  const { isCurator } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [searchDisplay, setSearchDisplay] = useState(search)
  const [window_, setWindow] = useState<TimeWindow>((searchParams.get('window') as TimeWindow) || '12m')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>((searchParams.get('status') as StatusFilter) || 'all')
  const [sortBy, setSortBy] = useState<SortField>((searchParams.get('sort') as SortField) || 'provisions')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>(searchParams.get('order') === 'asc' ? 'asc' : 'desc')

  const [selectedStages, setSelectedStages] = useState<Set<string>>(
    new Set(searchParams.get('stages')?.split(',').filter(Boolean) || []))
  const [selectedContentTypes, setSelectedContentTypes] = useState<Set<string>>(
    new Set(searchParams.get('content_types')?.split(',').filter(Boolean) || []))
  const [selectedNamespaces, setSelectedNamespaces] = useState<Set<string>>(
    new Set(searchParams.get('namespace')?.split(',').filter(Boolean) || []))
  const [provFilter, setProvFilter] = useState<string>(searchParams.get('provs') || 'all')

  const [allItems, setAllItems] = useState<NonProdItem[]>([])
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [drawerItem, setDrawerItem] = useState<NonProdItem | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getNonprodItems({
        sort_by: sortBy, sort_dir: sortDir,
        search: search || undefined,
        window: window_,
        status: statusFilter !== 'all' ? statusFilter : undefined,
      })
      setAllItems(data.items)
      setSyncedAt(data.synced_at)
    } finally { setLoading(false) }
  }, [sortBy, sortDir, search, window_, statusFilter])

  useEffect(() => { loadData() }, [loadData])

  // URL sync
  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    if (window_ !== '12m') params.window = window_
    if (statusFilter !== 'all') params.status = statusFilter
    if (sortBy !== 'provisions') params.sort = sortBy
    if (sortDir !== 'desc') params.order = sortDir
    if (selectedStages.size > 0) params.stages = Array.from(selectedStages).sort().join(',')
    if (selectedContentTypes.size > 0) params.content_types = Array.from(selectedContentTypes).sort().join(',')
    if (selectedNamespaces.size > 0) params.namespace = Array.from(selectedNamespaces).sort().join(',')
    if (provFilter !== 'all') params.provs = provFilter
    setSearchParams(params, { replace: true })
  }, [search, window_, statusFilter, sortBy, sortDir, selectedStages, selectedContentTypes, selectedNamespaces, provFilter, setSearchParams])

  const handleSearchChange = (value: string) => {
    setSearchDisplay(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => setSearch(value), 300)
  }

  const handleIgnore = async (baseName: string) => {
    try {
      const { ignored_until } = await api.ignoreNonprodItem(baseName)
      setAllItems(prev => prev.map(i => i.catalog_base_name === baseName ? { ...i, ignored_until } : i))
    } catch (e) { setActionError(e instanceof Error ? e.message : 'Mute failed') }
  }

  const handleUnignore = async (baseName: string) => {
    try {
      await api.unignoreNonprodItem(baseName)
      setAllItems(prev => prev.map(i => i.catalog_base_name === baseName ? { ...i, ignored_until: null } : i))
    } catch (e) { setActionError(e instanceof Error ? e.message : 'Unmute failed') }
  }

  const toggleExpand = (name: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const toggleSort = (field: SortField) => {
    if (sortBy === field) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortBy(field); setSortDir('desc') }
  }

  const clearFilters = () => {
    setStatusFilter('all')
    setSelectedStages(new Set())
    setSelectedContentTypes(new Set())
    setSelectedNamespaces(new Set())
    setProvFilter('all')
  }

  const isIgnored = (i: NonProdItem) => !!i.ignored_until

  // Client-side filters
  const filteredItems = allItems.filter(i => {
    if (selectedStages.size > 0) {
      const itemStages = i.stages.map(s => s.stage)
      if (!itemStages.some(s => selectedStages.has(s))) return false
    }
    if (selectedContentTypes.size > 0 && i.content_type && !selectedContentTypes.has(i.content_type)) return false
    if (selectedNamespaces.size > 0 && i.catalog_namespace && !selectedNamespaces.has(i.catalog_namespace)) return false
    if (provFilter === '0' && i.provisions !== 0) return false
    if (provFilter === '1-10' && (i.provisions < 1 || i.provisions > 10)) return false
    if (provFilter === '10+' && i.provisions <= 10) return false
    return true
  })

  // Derive facet values from data
  const availableStages = (() => {
    const counts: Record<string, number> = {}
    for (const i of allItems) {
      for (const s of i.stages) {
        counts[s.stage] = (counts[s.stage] || 0) + 1
      }
    }
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]))
  })()

  const availableContentTypes = (() => {
    const counts: Record<string, number> = {}
    for (const i of allItems) {
      if (i.content_type) counts[i.content_type] = (counts[i.content_type] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]))
  })()

  const availableNamespaces = (() => {
    const counts: Record<string, number> = {}
    for (const i of allItems) {
      if (i.catalog_namespace) counts[i.catalog_namespace] = (counts[i.catalog_namespace] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]))
  })()

  const toggleSet = (setter: React.Dispatch<React.SetStateAction<Set<string>>>, value: string) => {
    setter(prev => {
      const next = new Set(prev)
      next.has(value) ? next.delete(value) : next.add(value)
      return next
    })
  }

  const syncAge = syncedAt
    ? `${Math.round((Date.now() - new Date(syncedAt).getTime()) / 3600000)}h ago`
    : 'never'

  if (!isCurator) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <h3>Access Restricted</h3>
        <p>Non-Prod Items is available to curators only.</p>
      </div>
    )
  }

  return (
    <div className="browse-layout">
      <div className="browse-content">
      <div className="browse-filter-sidebar">
        <div className="browse-filter-group">
          <div className="browse-filter-group-label">Stage</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {availableStages.map(([stage, count]) => (
              <label key={stage} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 0', cursor: 'pointer', fontSize: '11px' }}>
                <input type="checkbox" checked={selectedStages.has(stage)} onChange={() => toggleSet(setSelectedStages, stage)} />
                <span className={`ca-env-tag ${stageBadgeClass[stage] || 'ca-env-test'}`}>{stage}</span>
                <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>
              </label>
            ))}
          </div>
        </div>

        {availableContentTypes.length > 1 && (
          <div className="browse-filter-group">
            <div className="browse-filter-group-label">Content Type</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {availableContentTypes.map(([ct, count]) => (
                <label key={ct} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 0', cursor: 'pointer', fontSize: '11px' }}>
                  <input type="checkbox" checked={selectedContentTypes.has(ct)} onChange={() => toggleSet(setSelectedContentTypes, ct)} />
                  <span>{ct}</span>
                  <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="browse-filter-group">
          <div className="browse-filter-group-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            Namespace
            {selectedNamespaces.size > 0 && (
              <button onClick={() => setSelectedNamespaces(new Set())}
                style={{ background: 'none', border: 'none', color: 'var(--score-amber)', fontSize: '11px', cursor: 'pointer', padding: 0 }}>
                Clear ({selectedNamespaces.size})
              </button>
            )}
          </div>
          <div style={{
            maxHeight: '200px', overflowY: 'auto', paddingRight: '8px',
            border: '1px solid var(--border-section)', borderRadius: 'var(--radius-sm)', background: 'var(--bg-page)',
          }}>
            {availableNamespaces.map(([ns, count]) => (
              <label key={ns} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 8px', cursor: 'pointer', fontSize: '11px' }}>
                <input type="checkbox" checked={selectedNamespaces.has(ns)} onChange={() => toggleSet(setSelectedNamespaces, ns)} />
                <span>{ns}</span>
                <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>({count})</span>
              </label>
            ))}
          </div>
        </div>

        <div className="browse-filter-group">
          <div className="browse-filter-group-label">Provisions</div>
          <div className="ret-filter-group">
            {(['all', '0', '1-10', '10+'] as const).map(f => (
              <button key={f} onClick={() => setProvFilter(f)}
                className={`ret-filter-group__btn${provFilter === f ? ' active' : ''}`}>
                {f === 'all' ? 'All' : f}
              </button>
            ))}
          </div>
        </div>

        <div className="browse-filter-group">
          <div className="browse-filter-group-label">Status</div>
          <div className="ret-filter-group">
            {(['all', 'active', 'muted'] as StatusFilter[]).map(f => (
              <button key={f} onClick={() => setStatusFilter(f)}
                className={`ret-filter-group__btn${statusFilter === f ? ' active' : ''}`}>
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginTop: '16px' }}>
          <button onClick={clearFilters}
            style={{ background: 'none', border: 'none', color: 'var(--score-amber)', fontSize: '11px', cursor: 'pointer', padding: 0 }}>
            Clear filters
          </button>
        </div>
      </div>

      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'auto', padding: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Non-Prod Items</h3>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Synced {syncAge}</span>
        </div>

        <div className="ca-tab-bar">
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', gap: '4px' }}>
            {([['6m', '6 Mo'], ['12m', '1 Yr']] as [TimeWindow, string][]).map(([w, label]) => (
              <button key={w} onClick={() => setWindow(w)}
                className={`ca-filter-btn${window_ === w ? ' active' : ''}`}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="ca-stats-grid">
          <div className="ret-stat-card ret-stat-card--blue">
            <div className="ret-stat-label">Total Items</div>
            <div className="ret-stat-value ca-color-blue">{allItems.filter(i => !isIgnored(i)).length}</div>
          </div>
          <div className="ret-stat-card">
            <div className="ret-stat-label">With Provisions</div>
            <div className="ret-stat-value">{allItems.filter(i => !isIgnored(i) && i.provisions > 0).length}</div>
          </div>
          <div className="ret-stat-card">
            <div className="ret-stat-label">Zero Provisions</div>
            <div className="ret-stat-value">{allItems.filter(i => !isIgnored(i) && i.provisions === 0).length}</div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <input type="text" placeholder="Search by name..."
            value={searchDisplay} onChange={e => handleSearchChange(e.target.value)}
            className="ca-search" />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
            {filteredItems.length} of {allItems.length} items
          </span>
        </div>

        {actionError && (
          <div style={{ padding: '8px 12px', background: 'var(--score-red-bg)', color: 'var(--score-red)',
            borderRadius: 'var(--radius-sm)', fontSize: '11px' }}>
            {actionError}
          </div>
        )}

        {loading ? (
          <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="ca-table" style={{ tableLayout: 'auto', minWidth: '900px' }}>
              <thead>
                <tr>
                  <th className="clickable" style={{ maxWidth: '300px' }} onClick={() => toggleSort('display_name')}>
                    Name {sortBy === 'display_name' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th>Type</th>
                  <th>Stages</th>
                  <th>Namespace</th>
                  <th className="clickable num" onClick={() => toggleSort('provisions')}>
                    Provs {sortBy === 'provisions' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('unique_users')}>
                    Users {sortBy === 'unique_users' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('success_ratio')}>
                    Success {sortBy === 'success_ratio' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th className="clickable num" onClick={() => toggleSort('failure_ratio')}>
                    Failure {sortBy === 'failure_ratio' && (sortDir === 'desc' ? '↓' : '↑')}
                  </th>
                  <th>Last Prov</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map(item => {
                  const isExpanded = expanded.has(item.catalog_base_name)
                  const muted = isIgnored(item)
                  return (
                    <Fragment key={item.catalog_base_name}>
                      <tr className="clickable" onClick={() => toggleExpand(item.catalog_base_name)}
                        style={muted ? { opacity: 0.45 } : undefined}>
                        <td className="name" title={item.display_name} style={{ maxWidth: '300px' }}>
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {item.display_name}
                            {muted && <span className="ret-inline-badge ret-inline-badge--muted">muted</span>}
                          </div>
                          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--ff-mono)', marginTop: '1px' }}>
                            {item.catalog_base_name}
                          </div>
                        </td>
                        <td><span className="ca-env-tag ca-env-test">{item.content_type || '—'}</span></td>
                        <td>
                          {item.stages.map(s => (
                            <span key={s.ci_name} className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}>
                              {s.stage}
                            </span>
                          ))}
                        </td>
                        <td style={{ fontSize: '11px' }}>{item.catalog_namespace || '—'}</td>
                        <td className="num">{item.provisions.toLocaleString()}</td>
                        <td className="num">{item.unique_users.toLocaleString()}</td>
                        <td className="num">{(item.success_ratio * 100).toFixed(1)}%</td>
                        <td className="num">{(item.failure_ratio * 100).toFixed(1)}%</td>
                        <td style={{ fontSize: '11px' }}>{item.last_provision || '—'}</td>
                        <td>
                          {item.workflow_status && <WorkflowInlineBadge status={item.workflow_status} />}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="ca-expanded-row">
                          <td colSpan={10}>
                            <div className="ca-detail">
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Requests</span>
                                <span className="ca-detail-value">{item.requests.toLocaleString()}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Completions</span>
                                <span className="ca-detail-value">{item.completions.toLocaleString()}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">First Provision</span>
                                <span className="ca-detail-value">{item.first_provision || 'N/A'}</span>
                              </div>
                              <div className="ca-detail-item">
                                <span className="ca-detail-label">Environments</span>
                                <span className="ca-detail-value">
                                  {item.stages.map(s => (
                                    <a key={s.ci_name} href={s.catalog_url} target="_blank" rel="noreferrer"
                                      className={`ca-env-tag ${stageBadgeClass[s.stage] || 'ca-env-test'}`}
                                      onClick={e => e.stopPropagation()}>
                                      {s.ci_name}
                                    </a>
                                  ))}
                                </span>
                              </div>
                            </div>
                            <div style={{ marginTop: '8px', display: 'flex', gap: '8px', alignItems: 'center',
                              borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
                              {muted ? (
                                <button className="ret-action-btn" onClick={(e) => { e.stopPropagation(); handleUnignore(item.catalog_base_name) }}>
                                  Unmute
                                </button>
                              ) : (
                                <button className="ret-action-btn" onClick={(e) => { e.stopPropagation(); handleIgnore(item.catalog_base_name) }}
                                  title="Mute for 30 days">
                                  Mute 30d
                                </button>
                              )}
                              <button className="ret-action-btn ret-action-btn--primary"
                                onClick={(e) => { e.stopPropagation(); setDrawerItem(item as any) }}>
                                Retirement Workflow
                              </button>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      </div>{/* end browse-content */}
      {drawerItem && <WorkflowDrawer item={drawerItem as any} onClose={() => setDrawerItem(null)} onChanged={loadData} />}
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/pages/NonProdItemsPage.tsx
git commit -m "[RHDPCD-661] Add NonProdItemsPage component"
```

---

### Task 7: Frontend Wiring — Route + Sidebar Navigation

**Files:**
- Modify: `src/frontend/src/App.tsx` (add route)
- Modify: `src/frontend/src/components/RcarsSidebar.tsx` (add nav entry)

**Interfaces:**
- Consumes: `NonProdItemsPage` from Task 6, `auth.isCurator` from useAuth hook
- Produces: `/analysis/nonprod` route accessible to curators, "Non-Prod Items" nav entry under Analysis section

- [ ] **Step 1: Add route to App.tsx**

In `App.tsx`, add the import at the top:

```tsx
import { NonProdItemsPage } from './pages/NonProdItemsPage'
```

Add the route inside the `auth.isCurator` block (after the overlap route, around line 54):

```tsx
<Route path="/analysis/nonprod" element={<NonProdItemsPage />} />
```

- [ ] **Step 2: Add nav entry to RcarsSidebar.tsx**

In `RcarsSidebar.tsx`, add the "Non-Prod Items" NavLink inside the `auth.isCurator` section, after the existing Overlap link (around line 67):

```tsx
          {auth.isCurator && (
            <NavLink
              to="/analysis/nonprod"
              className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
            >
              Non-Prod Items
            </NavLink>
          )}
```

- [ ] **Step 3: Verify TypeScript compiles and dev server starts**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/App.tsx src/frontend/src/components/RcarsSidebar.tsx
git commit -m "[RHDPCD-661] Wire NonProdItemsPage route and sidebar nav"
```

---

### Task 8: Run Full Test Suite

**Files:**
- No modifications

**Interfaces:**
- Consumes: All changes from Tasks 1-7
- Produces: Passing test suite confirming no regressions

- [ ] **Step 1: Run backend tests**

Run: `cd src/api && python -m pytest tests/ -v --tb=short -m "not integration" 2>&1 | tail -30`
Expected: All tests pass, including the new `test_nonprod.py` tests

- [ ] **Step 2: Run frontend TypeScript check**

Run: `cd src/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Fix any failures and commit**

If any tests fail, fix the root cause and commit the fix:

```bash
git add -A
git commit -m "[RHDPCD-661] Fix test failures from nonprod items integration"
```
