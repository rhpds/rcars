# Retirement Analysis Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate RHDP reporting data into RCARS for a retirement triage dashboard, recommendation card enrichment, and Browse view enrichment.

**Architecture:** Nightly sync pulls provisions/sales/cost data from the RHDP reporting MCP server via HTTP JSON-RPC, stores in a local `reporting_metrics` table, computes retirement scores. API serves data to a new Content Analysis > Retirement page and enriches recommendation candidates. MCP client uses stdlib `urllib` wrapped in `asyncio.to_thread()`.

**Tech Stack:** Python 3.11, FastAPI, psycopg, Alembic, Click, React 19, TypeScript, Vite

**Spec:** `docs/superpowers/specs/2026-06-15-retirement-analysis-integration-design.md`

---

## File Map

### New Files
| File | Responsibility |
|------|---------------|
| `src/api/alembic/versions/005_reporting_metrics.py` | Alembic migration for `reporting_metrics` table |
| `src/api/rcars/services/reporting_sync.py` | MCP client, SQL queries, sync orchestration, retirement scoring |
| `src/api/tests/test_reporting.py` | Tests for base name extraction, retirement scoring, MCP pagination |
| `src/frontend/src/pages/RetirementPage.tsx` | Retirement dashboard page component |

### Modified Files
| File | Changes |
|------|---------|
| `src/api/rcars/config.py` | Add 4 reporting config variables |
| `src/api/rcars/db/database.py` | Add reporting_metrics CRUD methods |
| `src/api/rcars/workers/ops.py` | Add step 5 (reporting sync) to nightly pipeline |
| `src/api/rcars/cli.py` | Add `reporting-db` command group (sync, status, show) |
| `src/api/rcars/api/routes/analysis.py` | Add `GET /analysis/retirement` endpoint |
| `src/api/rcars/api/routes/admin.py` | Add `POST /admin/sync-reporting` endpoint |
| `src/api/rcars/api/routes/catalog.py` | Extend `GET /catalog/{ci_name}` with reporting data |
| `src/api/rcars/workers/recommend.py` | Attach reporting metrics to recommendation candidates |
| `src/frontend/src/services/api.ts` | Add retirement API calls + types |
| `src/frontend/src/App.tsx` | Add `/analysis/retirement` route |
| `src/frontend/src/components/lcars/LcarsSidebar.tsx` | Add "Retirement" nav item under Content Analysis |
| `src/frontend/src/components/advisor/RecCard.tsx` | Add metrics line (provisions, cost, sales badge) |

---

## Task 1: Alembic Migration + Config Variables

**Files:**
- Create: `src/api/alembic/versions/005_reporting_metrics.py`
- Modify: `src/api/rcars/config.py`

- [ ] **Step 1: Create the Alembic migration**

Check the current latest revision number first — another session may have added migrations:

```bash
ls src/api/alembic/versions/
```

Then create the migration file. Adjust `revision` and `down_revision` based on the latest file found:

```python
"""Add reporting_metrics table for RHDP reporting data.

Revision ID: 005
Revises: 004
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS reporting_metrics (
            catalog_base_name  TEXT PRIMARY KEY,
            display_name       TEXT NOT NULL,
            provisions         INTEGER NOT NULL DEFAULT 0,
            provisions_quarter INTEGER NOT NULL DEFAULT 0,
            requests           INTEGER NOT NULL DEFAULT 0,
            experiences        INTEGER NOT NULL DEFAULT 0,
            unique_users       INTEGER NOT NULL DEFAULT 0,
            success_ratio      NUMERIC NOT NULL DEFAULT 0,
            failure_ratio      NUMERIC NOT NULL DEFAULT 0,
            touched_amount     NUMERIC NOT NULL DEFAULT 0,
            closed_amount      NUMERIC NOT NULL DEFAULT 0,
            total_cost         NUMERIC NOT NULL DEFAULT 0,
            avg_cost_per_provision NUMERIC NOT NULL DEFAULT 0,
            first_provision    DATE,
            last_provision     DATE,
            retirement_score   INTEGER NOT NULL DEFAULT 0,
            synced_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_reporting_metrics_retirement_score
            ON reporting_metrics (retirement_score DESC);
        CREATE INDEX IF NOT EXISTS ix_reporting_metrics_display_name
            ON reporting_metrics (display_name);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reporting_metrics CASCADE;")
```

- [ ] **Step 2: Add config variables**

In `src/api/rcars/config.py`, add these fields to the `Settings` class after the `pipeline_minute` field (around line 76):

```python
    # Reporting MCP integration
    reporting_mcp_url: str = ""
    reporting_mcp_token: str = ""
    reporting_provisions_days: int = 90
    reporting_sales_days: int = 365
```

- [ ] **Step 3: Run migration locally**

```bash
cd src/api
alembic upgrade head
```

Expected: Migration applies successfully, `reporting_metrics` table created.

- [ ] **Step 4: Verify table exists**

```bash
cd src/api
python -c "from rcars.db.database import Database; from rcars.config import Settings; s = Settings(); db = Database(s.database_url); print(db.execute_query('SELECT COUNT(*) FROM reporting_metrics'))"
```

Expected: Returns `[{'count': 0}]` or similar.

- [ ] **Step 5: Commit**

```bash
git add src/api/alembic/versions/005_reporting_metrics.py src/api/rcars/config.py
git commit -m "Add reporting_metrics migration and config variables"
```

---

## Task 2: Base Name Utility + Retirement Scoring + Tests

**Files:**
- Create: `src/api/rcars/services/reporting_sync.py` (partial — utility functions only)
- Create: `src/api/tests/test_reporting.py`

- [ ] **Step 1: Write tests for base name extraction**

```python
# src/api/tests/test_reporting.py
"""Tests for reporting sync utilities."""

from rcars.services.reporting_sync import extract_base_name, compute_retirement_score


class TestExtractBaseName:
    def test_prod_suffix(self):
        assert extract_base_name("sandboxes-gpte.sandbox-open.prod") == "sandboxes-gpte.sandbox-open"

    def test_dev_suffix(self):
        assert extract_base_name("openshift-cnv.ocp-virt-advanced.dev") == "openshift-cnv.ocp-virt-advanced"

    def test_event_suffix(self):
        assert extract_base_name("partner.ocp-virt-roadshow.event") == "partner.ocp-virt-roadshow"

    def test_test_suffix(self):
        assert extract_base_name("agd-v2.something.test") == "agd-v2.something"

    def test_no_suffix(self):
        assert extract_base_name("some-name-without-stage") == "some-name-without-stage"

    def test_dotted_name_with_suffix(self):
        assert extract_base_name("a.b.c.prod") == "a.b.c"


class TestRetirementScore:
    def test_perfect_retirement_candidate(self):
        """No prod, zero usage, zero sales, high cost."""
        score = compute_retirement_score(
            provisions=0, experiences=0, touched_amount=0, closed_amount=0,
            total_cost=10000, has_prod=False, first_provision="",
        )
        assert score >= 85

    def test_healthy_asset(self):
        """Prod, high usage, high sales, reasonable cost."""
        score = compute_retirement_score(
            provisions=500, experiences=2000, touched_amount=100_000_000,
            closed_amount=20_000_000, total_cost=50000, has_prod=True,
            first_provision="2024-01-01",
        )
        assert score < 30

    def test_new_item_discount(self):
        """Recently published items get score reduction."""
        from datetime import datetime, timedelta
        recent = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        score = compute_retirement_score(
            provisions=5, experiences=5, touched_amount=0, closed_amount=0,
            total_cost=100, has_prod=True, first_provision=recent,
        )
        assert score <= 40

    def test_no_prod_adds_twenty(self):
        """Missing prod environment adds 20 points."""
        score_with = compute_retirement_score(
            provisions=200, experiences=1000, touched_amount=50_000_000,
            closed_amount=10_000_000, total_cost=30000, has_prod=True,
            first_provision="2024-01-01",
        )
        score_without = compute_retirement_score(
            provisions=200, experiences=1000, touched_amount=50_000_000,
            closed_amount=10_000_000, total_cost=30000, has_prod=False,
            first_provision="2024-01-01",
        )
        assert score_without == score_with + 20

    def test_high_cost_zero_sales(self):
        """High cost with zero closed sales adds 15 points."""
        score = compute_retirement_score(
            provisions=200, experiences=1000, touched_amount=50_000_000,
            closed_amount=0, total_cost=10000, has_prod=True,
            first_provision="2024-01-01",
        )
        assert score >= 15

    def test_score_capped_at_100(self):
        """Score should never exceed 100."""
        score = compute_retirement_score(
            provisions=0, experiences=0, touched_amount=0, closed_amount=0,
            total_cost=100000, has_prod=False, first_provision="2020-01-01",
        )
        assert score <= 100

    def test_sales_impact_high(self):
        from rcars.services.reporting_sync import compute_sales_impact
        assert compute_sales_impact(1_500_000) == "high"

    def test_sales_impact_moderate(self):
        from rcars.services.reporting_sync import compute_sales_impact
        assert compute_sales_impact(500_000) == "moderate"

    def test_sales_impact_low(self):
        from rcars.services.reporting_sync import compute_sales_impact
        assert compute_sales_impact(50_000) == "low"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src/api && python -m pytest tests/test_reporting.py -v
```

Expected: ImportError — `rcars.services.reporting_sync` does not exist yet.

- [ ] **Step 3: Implement the utility functions**

```python
# src/api/rcars/services/reporting_sync.py
"""RHDP reporting MCP sync — utilities, MCP client, and sync orchestration."""

from __future__ import annotations

from datetime import datetime

STAGE_SUFFIXES = (".prod", ".dev", ".event", ".test")


def extract_base_name(ci_name: str) -> str:
    """Strip stage suffix from an RCARS ci_name to get the reporting DB base name."""
    for suffix in STAGE_SUFFIXES:
        if ci_name.endswith(suffix):
            return ci_name[: -len(suffix)]
    return ci_name


def compute_retirement_score(
    provisions: int,
    experiences: int,
    touched_amount: float,
    closed_amount: float,
    total_cost: float,
    has_prod: bool,
    first_provision: str,
) -> int:
    """Compute retirement score 0-100. Higher = stronger retirement candidate."""
    score = 0

    if not has_prod:
        score += 20

    if provisions < 60:
        score += 20
    elif provisions < 120:
        score += 8

    if experiences < 300:
        score += 10
    elif experiences < 600:
        score += 4

    if touched_amount < 10_000_000:
        score += 15
    elif touched_amount < 50_000_000:
        score += 6

    if closed_amount < 1_000_000:
        score += 20
    elif closed_amount < 5_000_000:
        score += 8

    if total_cost > 0 and closed_amount > 0:
        roi = closed_amount / total_cost
        if roi < 10:
            score += 15
        elif roi < 50:
            score += 5
    elif total_cost > 5000 and closed_amount == 0:
        score += 15

    if first_provision:
        try:
            first_date = datetime.strptime(first_provision, "%Y-%m-%d")
            age_days = (datetime.now() - first_date).days
            if age_days <= 90:
                score = max(0, score - 40)
            elif age_days <= 180:
                score = max(0, score - 15)
        except ValueError:
            pass

    return min(score, 100)


def compute_sales_impact(closed_amount: float) -> str:
    """Compute sales impact tier from closed amount."""
    if closed_amount >= 1_000_000:
        return "high"
    if closed_amount >= 100_000:
        return "moderate"
    return "low"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd src/api && python -m pytest tests/test_reporting.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/reporting_sync.py src/api/tests/test_reporting.py
git commit -m "Add base name extraction, retirement scoring, and sales impact utilities"
```

---

## Task 3: MCP Client

**Files:**
- Modify: `src/api/rcars/services/reporting_sync.py`
- Modify: `src/api/tests/test_reporting.py`

- [ ] **Step 1: Write tests for MCP client pagination**

Add to `src/api/tests/test_reporting.py`:

```python
import json
from unittest.mock import patch, MagicMock
from rcars.services.reporting_sync import mcp_query


class TestMcpPagination:
    def _mock_response(self, rows: list[dict], row_count: int | None = None):
        """Build a mock urllib response for an MCP query result."""
        text = json.dumps({
            "columns": list(rows[0].keys()) if rows else [],
            "rows": rows,
            "row_count": row_count or len(rows),
            "truncated": len(rows) >= 500,
        })
        body = json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "result": {"content": [{"type": "text", "text": text}]},
        }).encode()
        resp = MagicMock()
        resp.read.return_value = body
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    @patch("rcars.services.reporting_sync.urllib.request.urlopen")
    def test_single_page(self, mock_urlopen):
        rows = [{"name": f"item-{i}"} for i in range(100)]
        mock_urlopen.return_value = self._mock_response(rows)
        result = mcp_query("SELECT 1", url="http://test", token="tok")
        assert len(result) == 100

    @patch("rcars.services.reporting_sync.urllib.request.urlopen")
    def test_auto_pagination(self, mock_urlopen):
        page1 = [{"name": f"item-{i}"} for i in range(500)]
        page2 = [{"name": f"item-{i}"} for i in range(500, 623)]
        mock_urlopen.side_effect = [
            self._mock_response(page1),
            self._mock_response(page2),
        ]
        result = mcp_query("SELECT 1", url="http://test", token="tok")
        assert len(result) == 623
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src/api && python -m pytest tests/test_reporting.py::TestMcpPagination -v
```

Expected: ImportError — `mcp_query` not defined yet.

- [ ] **Step 3: Implement MCP client**

Add to `src/api/rcars/services/reporting_sync.py`, after the existing functions:

```python
import json
import ssl
import urllib.error
import urllib.request

import structlog

logger = structlog.get_logger(component="reporting_sync")


def _mcp_call(
    tool_name: str,
    arguments: dict,
    url: str,
    token: str,
    timeout: int = 180,
) -> dict:
    """Call an MCP tool via HTTP JSON-RPC, return parsed JSON result."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if "error" in body:
        raise RuntimeError(f"MCP error: {body['error']}")

    text = body["result"]["content"][0]["text"]
    idx = text.find("{")
    if idx > 0:
        text = text[idx:]
    return json.loads(text)


def mcp_query(
    sql: str,
    url: str,
    token: str,
    timeout: int = 180,
) -> list[dict]:
    """Execute SQL via MCP server, auto-paginating past 500-row cap."""
    PAGE = 500
    all_rows: list[dict] = []
    offset = 0
    while True:
        paged = f"WITH _q AS ({sql}) SELECT * FROM _q ORDER BY 1 LIMIT {PAGE} OFFSET {offset}"
        result = _mcp_call(
            "query",
            {"sql": paged, "output_format": "json", "limit": PAGE},
            url=url, token=token, timeout=timeout,
        )
        rows = result["rows"]
        all_rows.extend(rows)
        if len(rows) < PAGE:
            break
        offset += PAGE
    return all_rows
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd src/api && python -m pytest tests/test_reporting.py -v
```

Expected: All tests pass (including new pagination tests).

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/reporting_sync.py src/api/tests/test_reporting.py
git commit -m "Add MCP HTTP client with auto-pagination"
```

---

## Task 4: Database Methods

**Files:**
- Modify: `src/api/rcars/db/database.py`

- [ ] **Step 1: Add upsert method for reporting metrics**

Add the following methods to the `Database` class in `src/api/rcars/db/database.py`. Place them after the existing `compute_content_similarity` method (near the end of the file):

```python
    # ── Reporting metrics ──

    def upsert_reporting_metrics(self, rows: list[dict]):
        """Bulk upsert reporting metrics. Each dict must have 'catalog_base_name'."""
        if not rows:
            return 0
        sql = """
            INSERT INTO reporting_metrics (
                catalog_base_name, display_name, provisions, provisions_quarter,
                requests, experiences, unique_users, success_ratio, failure_ratio,
                touched_amount, closed_amount, total_cost, avg_cost_per_provision,
                first_provision, last_provision, retirement_score, synced_at
            ) VALUES (
                %(catalog_base_name)s, %(display_name)s, %(provisions)s, %(provisions_quarter)s,
                %(requests)s, %(experiences)s, %(unique_users)s, %(success_ratio)s, %(failure_ratio)s,
                %(touched_amount)s, %(closed_amount)s, %(total_cost)s, %(avg_cost_per_provision)s,
                %(first_provision)s, %(last_provision)s, %(retirement_score)s, NOW()
            )
            ON CONFLICT (catalog_base_name) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                provisions = EXCLUDED.provisions,
                provisions_quarter = EXCLUDED.provisions_quarter,
                requests = EXCLUDED.requests,
                experiences = EXCLUDED.experiences,
                unique_users = EXCLUDED.unique_users,
                success_ratio = EXCLUDED.success_ratio,
                failure_ratio = EXCLUDED.failure_ratio,
                touched_amount = EXCLUDED.touched_amount,
                closed_amount = EXCLUDED.closed_amount,
                total_cost = EXCLUDED.total_cost,
                avg_cost_per_provision = EXCLUDED.avg_cost_per_provision,
                first_provision = EXCLUDED.first_provision,
                last_provision = EXCLUDED.last_provision,
                retirement_score = EXCLUDED.retirement_score,
                synced_at = NOW()
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                for row in rows:
                    cur.execute(sql, row)
            conn.commit()
        return len(rows)

    def delete_orphan_reporting_metrics(self) -> int:
        """Delete reporting_metrics rows with no matching catalog_items entry."""
        sql = """
            DELETE FROM reporting_metrics rm
            WHERE NOT EXISTS (
                SELECT 1 FROM catalog_items ci
                WHERE ci.ci_name LIKE rm.catalog_base_name || '.%'
            )
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                deleted = cur.rowcount
            conn.commit()
        return deleted

    def get_reporting_metrics(self, catalog_base_name: str) -> dict | None:
        """Get reporting metrics for a single catalog base name."""
        sql = "SELECT * FROM reporting_metrics WHERE catalog_base_name = %s"
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, (catalog_base_name,))
                return cur.fetchone()

    def list_reporting_metrics(
        self,
        sort_by: str = "retirement_score",
        sort_dir: str = "desc",
        min_score: int | None = None,
        category: str | None = None,
        has_prod: bool | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """List reporting metrics joined with catalog metadata for the retirement dashboard."""
        allowed_sorts = {
            "retirement_score", "provisions", "total_cost",
            "closed_amount", "touched_amount", "display_name",
        }
        if sort_by not in allowed_sorts:
            sort_by = "retirement_score"
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

        conditions = []
        params: dict = {}

        if min_score is not None:
            conditions.append("rm.retirement_score >= %(min_score)s")
            params["min_score"] = min_score

        if search:
            conditions.append("rm.display_name ILIKE %(search)s")
            params["search"] = f"%{search}%"

        if category:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM catalog_items ci2
                    WHERE ci2.ci_name LIKE rm.catalog_base_name || '.%%'
                    AND ci2.category = %(category)s
                )
            """)
            params["category"] = category

        if has_prod is True:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM catalog_items ci3
                    WHERE ci3.ci_name = rm.catalog_base_name || '.prod'
                )
            """)
        elif has_prod is False:
            conditions.append("""
                NOT EXISTS (
                    SELECT 1 FROM catalog_items ci3
                    WHERE ci3.ci_name = rm.catalog_base_name || '.prod'
                )
            """)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT rm.*,
                   ci.category, ci.product, ci.product_family
            FROM reporting_metrics rm
            LEFT JOIN LATERAL (
                SELECT category, product, product_family
                FROM catalog_items
                WHERE ci_name LIKE rm.catalog_base_name || '.%%'
                ORDER BY CASE stage WHEN 'prod' THEN 0 WHEN 'event' THEN 1 ELSE 2 END
                LIMIT 1
            ) ci ON true
            {where}
            ORDER BY rm.{sort_by} {direction}
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def get_stages_for_base_names(self, base_names: list[str]) -> dict[str, list[dict]]:
        """Get all stages and catalog URLs for a list of base names."""
        if not base_names:
            return {}
        placeholders = ",".join(["%s"] * len(base_names))
        sql = f"""
            SELECT ci_name, catalog_namespace, stage
            FROM catalog_items
            WHERE substring(ci_name FROM '^(.+)\\.[^.]+$') IN ({placeholders})
            ORDER BY ci_name
        """
        result: dict[str, list[dict]] = {}
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, base_names)
                for row in cur.fetchall():
                    base = extract_base_name(row["ci_name"])
                    stage_info = {
                        "stage": row["stage"],
                        "ci_name": row["ci_name"],
                        "catalog_url": f"https://catalog.demo.redhat.com/catalog?item={row['catalog_namespace']}/{row['ci_name']}",
                    }
                    result.setdefault(base, []).append(stage_info)
        return result

    def get_reporting_sync_status(self) -> dict:
        """Get sync status: last synced, row count, score distribution."""
        sql = """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE retirement_score >= 75) AS high,
                COUNT(*) FILTER (WHERE retirement_score >= 50 AND retirement_score < 75) AS review,
                COUNT(*) FILTER (WHERE retirement_score < 50) AS keepers,
                MAX(synced_at) AS last_synced
            FROM reporting_metrics
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return cur.fetchone()

    def has_prod_stage(self, base_name: str) -> bool:
        """Check if a base name has a prod-stage catalog item."""
        sql = "SELECT 1 FROM catalog_items WHERE ci_name = %s LIMIT 1"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (f"{base_name}.prod",))
                return cur.fetchone() is not None

    def get_all_base_names_with_prod(self) -> set[str]:
        """Return set of base names that have a .prod entry in catalog_items."""
        sql = """
            SELECT DISTINCT substring(ci_name FROM '^(.+)\\.prod$')
            FROM catalog_items
            WHERE ci_name LIKE '%.prod'
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return {row[0] for row in cur.fetchall() if row[0]}
```

Add this import at the top of `database.py` if not already present:

```python
from rcars.services.reporting_sync import extract_base_name
```

- [ ] **Step 2: Verify compilation**

```bash
cd src/api && python -c "from rcars.db.database import Database; print('OK')"
```

Expected: `OK` (no import errors).

- [ ] **Step 3: Commit**

```bash
git add src/api/rcars/db/database.py
git commit -m "Add reporting_metrics database methods"
```

---

## Task 5: Reporting Sync Service + Ops Worker Integration

**Files:**
- Modify: `src/api/rcars/services/reporting_sync.py`
- Modify: `src/api/rcars/workers/ops.py`

- [ ] **Step 1: Add SQL queries and sync orchestrator**

Add the following to `src/api/rcars/services/reporting_sync.py`, after the `mcp_query` function:

```python
from rcars.config import Settings
from rcars.db.database import Database


def _build_provisions_sql(start_date: str) -> str:
    return f"""
        SELECT
            ci.name AS catalog_base_name,
            ci.display_name,
            COUNT(DISTINCT p.uuid) AS provisions,
            COUNT(DISTINCT p.request_id) AS requests,
            SUM(p.user_experiences) AS experiences,
            COUNT(DISTINCT p.user_id) AS unique_users,
            ROUND(
                COUNT(DISTINCT CASE WHEN p.provision_result = 'success' THEN p.uuid END)::numeric
                / NULLIF(COUNT(DISTINCT p.uuid), 0), 4
            ) AS success_ratio,
            ROUND(
                COUNT(DISTINCT CASE WHEN p.provision_result = 'failure' THEN p.uuid END)::numeric
                / NULLIF(COUNT(DISTINCT p.uuid), 0), 4
            ) AS failure_ratio
        FROM provisions p
        JOIN catalog_items ci ON ci.id = p.catalog_id
        WHERE p.provisioned_at >= '{start_date}'
        GROUP BY ci.name, ci.display_name
    """


def _build_provisions_quarter_sql(start_date: str) -> str:
    return f"""
        SELECT ci.name AS catalog_base_name, COUNT(DISTINCT p.uuid) AS provisions_quarter
        FROM provisions p
        JOIN catalog_items ci ON ci.id = p.catalog_id
        WHERE p.provisioned_at >= '{start_date}'
        GROUP BY ci.name
    """


def _build_sales_sql(start_date: str) -> str:
    return f"""
        WITH unique_opps AS (
            SELECT DISTINCT
                ci.name AS catalog_base_name, so.number, so.amount,
                so.is_closed, so.stage
            FROM provisions p
            JOIN catalog_items ci ON ci.id = p.catalog_id
            JOIN provision_sales ps ON ps.provision_uuid = p.uuid
            JOIN sales_opportunity so ON so.number = ps.sales_opportunity_number
            WHERE p.provisioned_at >= '{start_date}'
              AND ps.sales_opportunity_number IS NOT NULL
        )
        SELECT
            catalog_base_name,
            SUM(amount) AS touched_amount,
            SUM(CASE WHEN is_closed = true
                      AND stage IN ('Closed Won', 'Closed Booked')
                 THEN amount ELSE 0 END) AS closed_amount
        FROM unique_opps
        GROUP BY catalog_base_name
    """


def _build_cost_sql(start_date: str) -> str:
    return f"""
        WITH costs AS (
            SELECT provision_uuid, SUM(total_cost) AS total_cost
            FROM provision_cost
            WHERE month_ts >= '{start_date}'
            GROUP BY provision_uuid
        )
        SELECT
            ci.name AS catalog_base_name,
            SUM(c.total_cost) AS total_cost,
            ROUND(SUM(c.total_cost) / NULLIF(COUNT(*), 0), 2) AS avg_cost_per_provision
        FROM costs c
        JOIN provisions p ON p.uuid = c.provision_uuid
        JOIN catalog_items ci ON ci.id = p.catalog_id
        GROUP BY ci.name
    """


DATES_SQL = """
    SELECT
        ci.name AS catalog_base_name,
        MIN(p.provisioned_at)::date::text AS first_provision,
        MAX(p.provisioned_at)::date::text AS last_provision
    FROM provisions p
    JOIN catalog_items ci ON ci.id = p.catalog_id
    GROUP BY ci.name
"""


def run_reporting_sync(db: Database, settings: Settings) -> dict:
    """Pull reporting data from MCP server, compute scores, upsert locally.

    Returns summary dict with counts. Raises on MCP connection failure.
    """
    url = settings.reporting_mcp_url
    token = settings.reporting_mcp_token
    log = logger.bind(action="reporting_sync")

    from datetime import datetime, timedelta
    sales_start = (datetime.now() - timedelta(days=settings.reporting_sales_days)).strftime("%Y-%m-%d")
    quarter_start = (datetime.now() - timedelta(days=settings.reporting_provisions_days)).strftime("%Y-%m-%d")

    log.info("fetching_provisions", sales_start=sales_start)
    prov_rows = mcp_query(_build_provisions_sql(sales_start), url=url, token=token)
    prov_data = {r["catalog_base_name"]: r for r in prov_rows}
    log.info("fetched_provisions", count=len(prov_data))

    log.info("fetching_provisions_quarter", quarter_start=quarter_start)
    quarter_rows = mcp_query(_build_provisions_quarter_sql(quarter_start), url=url, token=token)
    quarter_data = {r["catalog_base_name"]: int(r["provisions_quarter"]) for r in quarter_rows}
    log.info("fetched_provisions_quarter", count=len(quarter_data))

    log.info("fetching_sales", sales_start=sales_start)
    sales_rows = mcp_query(_build_sales_sql(sales_start), url=url, token=token)
    sales_data = {r["catalog_base_name"]: r for r in sales_rows}
    log.info("fetched_sales", count=len(sales_data))

    log.info("fetching_cost", sales_start=sales_start)
    cost_rows = mcp_query(_build_cost_sql(sales_start), url=url, token=token)
    cost_data = {r["catalog_base_name"]: r for r in cost_rows}
    log.info("fetched_cost", count=len(cost_data))

    log.info("fetching_dates")
    date_rows = mcp_query(DATES_SQL, url=url, token=token, timeout=60)
    date_data = {r["catalog_base_name"]: r for r in date_rows}
    log.info("fetched_dates", count=len(date_data))

    prod_base_names = db.get_all_base_names_with_prod()

    all_names = set(prov_data) | set(sales_data) | set(cost_data) | set(date_data)
    log.info("merging", total_base_names=len(all_names))

    merged_rows = []
    for name in all_names:
        prov = prov_data.get(name, {})
        sales = sales_data.get(name, {})
        cost = cost_data.get(name, {})
        dates = date_data.get(name, {})

        provisions = int(prov.get("provisions", 0))
        experiences = int(prov.get("experiences", 0))
        touched = float(sales.get("touched_amount", 0) or 0)
        closed = float(sales.get("closed_amount", 0) or 0)
        total_cost = float(cost.get("total_cost", 0) or 0)
        first_prov = dates.get("first_provision", "") or ""
        has_prod = name in prod_base_names

        score = compute_retirement_score(
            provisions=provisions, experiences=experiences,
            touched_amount=touched, closed_amount=closed,
            total_cost=total_cost, has_prod=has_prod,
            first_provision=first_prov,
        )

        merged_rows.append({
            "catalog_base_name": name,
            "display_name": prov.get("display_name", "") or dates.get("display_name", "") or name,
            "provisions": provisions,
            "provisions_quarter": quarter_data.get(name, 0),
            "requests": int(prov.get("requests", 0)),
            "experiences": experiences,
            "unique_users": int(prov.get("unique_users", 0)),
            "success_ratio": float(prov.get("success_ratio", 0) or 0),
            "failure_ratio": float(prov.get("failure_ratio", 0) or 0),
            "touched_amount": touched,
            "closed_amount": closed,
            "total_cost": total_cost,
            "avg_cost_per_provision": float(cost.get("avg_cost_per_provision", 0) or 0),
            "first_provision": first_prov or None,
            "last_provision": (dates.get("last_provision", "") or None),
            "retirement_score": score,
        })

    upserted = db.upsert_reporting_metrics(merged_rows)
    orphans = db.delete_orphan_reporting_metrics()

    summary = {
        "synced": upserted,
        "orphans_removed": orphans,
        "provisions_rows": len(prov_data),
        "sales_rows": len(sales_data),
        "cost_rows": len(cost_data),
        "date_rows": len(date_data),
    }
    log.info("sync_complete", **summary)
    return summary
```

- [ ] **Step 2: Add step 5 to the nightly pipeline**

In `src/api/rcars/workers/ops.py`, add the reporting sync step after Step 4 (workload scan). Find the `# Complete pipeline` comment (around line 358) and insert before it:

```python
    # Step 5: Reporting metrics sync (if configured)
    reporting_result = None
    if wctx.settings.reporting_mcp_url and wctx.settings.reporting_mcp_token:
        try:
            await publish_progress(wctx.relay, job_id, wctx.db,
                                   phase="pipeline:reporting_sync", status="running",
                                   message="Step 5: Syncing reporting metrics from MCP server...")
            import asyncio
            from rcars.services.reporting_sync import run_reporting_sync
            reporting_result = await asyncio.to_thread(
                run_reporting_sync, wctx.db, wctx.settings,
            )
            await publish_progress(wctx.relay, job_id, wctx.db,
                                   phase="pipeline:reporting_sync", status="complete",
                                   message=f"Step 5 complete: {reporting_result['synced']} metrics synced, {reporting_result['orphans_removed']} orphans removed")
            log.info("pipeline_reporting_sync_complete", action="pipeline_step_complete",
                     step="reporting_sync", **reporting_result)
        except Exception as e:
            msg = f"Step 5 failed (reporting sync): {e}"
            warnings.append(msg)
            log.error("pipeline_reporting_sync_failed", action="pipeline_step_failed",
                      step="reporting_sync", error=str(e), traceback=traceback.format_exc())
            await publish_progress(wctx.relay, job_id, wctx.db,
                                   phase="pipeline:reporting_sync", status="failed", message=msg)
    else:
        log.info("pipeline_reporting_sync_skipped", action="pipeline_step_skipped",
                 step="reporting_sync", reason="MCP URL or token not configured")
```

Also add `"reporting_sync": reporting_result,` to the `result` dict in the `# Complete pipeline` section.

Update the step labels in progress messages from "Step N/3" to "Step N/5" or remove the "/N" counts to avoid hardcoding. The simplest fix: change the existing step messages from `Step 1/3` → `Step 1`, `Step 2/3` → `Step 2`, etc. (remove the denominator since step count is now dynamic).

- [ ] **Step 3: Add `run_reporting_sync` as a standalone arq job**

Add this function to `ops.py` so it can be triggered independently via the admin API:

```python
async def run_reporting_sync_job(ctx: dict, job_id: str) -> dict:
    """Sync reporting metrics from MCP server (standalone, not part of pipeline)."""
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("reporting_sync_started", action="reporting_sync_started")
    wctx.db.update_job_status(job_id, "running")

    try:
        import asyncio
        from rcars.services.reporting_sync import run_reporting_sync
        result = await asyncio.to_thread(run_reporting_sync, wctx.db, wctx.settings)
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="complete", status="complete",
                               message=f"Reporting sync complete: {result['synced']} synced, {result['orphans_removed']} orphans removed")
        wctx.db.complete_job(job_id, result_json=result)
        log.info("reporting_sync_complete", action="reporting_sync_complete", **result)
        return result
    except Exception as e:
        log.error("reporting_sync_failed", action="reporting_sync_failed",
                  error=str(e), traceback=traceback.format_exc())
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="failed", status="failed", message=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        raise
```

Register it in `src/api/rcars/workers/settings.py` — add `run_reporting_sync_job` to the `WorkerSettings.functions` list.

- [ ] **Step 4: Commit**

```bash
git add src/api/rcars/services/reporting_sync.py src/api/rcars/workers/ops.py src/api/rcars/workers/settings.py
git commit -m "Add reporting sync service and nightly pipeline step 5"
```

---

## Task 6: CLI Commands

**Files:**
- Modify: `src/api/rcars/cli.py`

- [ ] **Step 1: Add the reporting-db command group**

Add to `src/api/rcars/cli.py`, after the existing `workload_group` (near the end of the file, before `if __name__`):

```python
@cli.group(name="reporting-db")
def reporting_db_group():
    """Reporting database metrics commands."""
    pass


@reporting_db_group.command("sync")
@click.pass_context
def reporting_db_sync(ctx):
    """Sync reporting metrics from RHDP MCP server."""
    from rcars.config import Settings
    from rcars.db.database import Database
    from rcars.services.reporting_sync import run_reporting_sync

    settings = Settings()
    if not settings.reporting_mcp_url or not settings.reporting_mcp_token:
        _print("ERROR: RCARS_REPORTING_MCP_URL and RCARS_REPORTING_MCP_TOKEN must be set.")
        raise SystemExit(1)

    db = Database(settings.database_url)
    _print("Syncing reporting metrics from MCP server...")
    try:
        result = run_reporting_sync(db, settings)
        _print(f"  Synced: {result['synced']} metrics")
        _print(f"  Orphans removed: {result['orphans_removed']}")
        _print(f"  Provisions: {result['provisions_rows']}, Sales: {result['sales_rows']}, "
               f"Cost: {result['cost_rows']}, Dates: {result['date_rows']}")
    except Exception as e:
        _print(f"ERROR: {e}")
        raise SystemExit(1)


@reporting_db_group.command("status")
@click.pass_context
def reporting_db_status(ctx):
    """Show reporting sync status and score distribution."""
    from rcars.config import Settings
    from rcars.db.database import Database

    settings = Settings()
    db = Database(settings.database_url)
    status = db.get_reporting_sync_status()

    if not status or status["total"] == 0:
        _print("No reporting metrics synced yet.")
        return

    _print(f"  Last synced:    {status['last_synced']}")
    _print(f"  Total items:    {status['total']}")
    _print(f"  High (≥75):     {status['high']}")
    _print(f"  Review (50-74): {status['review']}")
    _print(f"  Keepers (<50):  {status['keepers']}")


@reporting_db_group.command("show")
@click.argument("ci_name")
@click.pass_context
def reporting_db_show(ctx, ci_name: str):
    """Show reporting metrics for a specific CI (accepts ci_name or base name)."""
    from rcars.config import Settings
    from rcars.db.database import Database
    from rcars.services.reporting_sync import extract_base_name

    settings = Settings()
    db = Database(settings.database_url)
    base_name = extract_base_name(ci_name)
    metrics = db.get_reporting_metrics(base_name)

    if not metrics:
        _print(f"No reporting metrics found for: {base_name}")
        return

    _print(f"  Base name:         {metrics['catalog_base_name']}")
    _print(f"  Display name:      {metrics['display_name']}")
    _print(f"  Retirement score:  {metrics['retirement_score']}")
    _print(f"  Provisions:        {metrics['provisions']} (quarter: {metrics['provisions_quarter']})")
    _print(f"  Experiences:       {metrics['experiences']}")
    _print(f"  Unique users:      {metrics['unique_users']}")
    _print(f"  Touched amount:    ${metrics['touched_amount']:,.0f}")
    _print(f"  Closed amount:     ${metrics['closed_amount']:,.0f}")
    _print(f"  Total cost:        ${metrics['total_cost']:,.0f}")
    _print(f"  Avg cost/prov:     ${metrics['avg_cost_per_provision']:,.2f}")
    _print(f"  First provision:   {metrics['first_provision'] or 'N/A'}")
    _print(f"  Last provision:    {metrics['last_provision'] or 'N/A'}")
    _print(f"  Synced at:         {metrics['synced_at']}")
```

- [ ] **Step 2: Test CLI locally**

```bash
cd src/api && rcars reporting-db status
```

Expected: "No reporting metrics synced yet." (table is empty).

- [ ] **Step 3: Commit**

```bash
git add src/api/rcars/cli.py
git commit -m "Add reporting-db CLI commands (sync, status, show)"
```

---

## Task 7: API Endpoints

**Files:**
- Modify: `src/api/rcars/api/routes/analysis.py`
- Modify: `src/api/rcars/api/routes/admin.py`
- Modify: `src/api/rcars/api/routes/catalog.py`
- Modify: `src/api/rcars/workers/recommend.py`

- [ ] **Step 1: Add retirement dashboard endpoint**

Add to `src/api/rcars/api/routes/analysis.py`:

```python
from fastapi import Query


@router.get("/retirement")
async def retirement_dashboard(
    request: Request,
    user: str = Depends(require_curator),
    sort_by: str = Query("retirement_score"),
    sort_dir: str = Query("desc"),
    min_score: int | None = Query(None),
    category: str | None = Query(None),
    has_prod: bool | None = Query(None),
    search: str | None = Query(None),
):
    db = request.app.state.db
    items = db.list_reporting_metrics(
        sort_by=sort_by, sort_dir=sort_dir, min_score=min_score,
        category=category, has_prod=has_prod, search=search,
    )

    base_names = [i["catalog_base_name"] for i in items]
    stages_map = db.get_stages_for_base_names(base_names)

    from rcars.services.reporting_sync import compute_retirement_score, compute_sales_impact
    for item in items:
        item["stages"] = stages_map.get(item["catalog_base_name"], [])
        item["sales_impact"] = compute_sales_impact(float(item.get("closed_amount", 0) or 0))

    sync_status = db.get_reporting_sync_status()
    return {
        "items": items,
        "total": len(items),
        "synced_at": sync_status.get("last_synced") if sync_status else None,
        "summary": sync_status,
    }
```

**Important:** This endpoint must be defined BEFORE the existing `@router.post("/{ci_name}")` route (line 73) — otherwise FastAPI will try to match "retirement" as a `ci_name` parameter. Move it above that route.

- [ ] **Step 2: Add manual sync trigger to admin routes**

Add to `src/api/rcars/api/routes/admin.py`:

```python
@router.post("/sync-reporting")
async def sync_reporting(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="reporting_sync", queue="ops", created_by=user)
    await arq_redis.enqueue_job("run_reporting_sync_job", job_id=job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}
```

- [ ] **Step 3: Extend single CI detail with reporting data**

In `src/api/rcars/api/routes/catalog.py`, find the `GET /catalog/{ci_name}` endpoint. After the existing data assembly (tags, analysis, workloads, ACL groups), add:

```python
    from rcars.services.reporting_sync import extract_base_name, compute_sales_impact
    base_name = extract_base_name(ci_name)
    reporting = db.get_reporting_metrics(base_name)
    if reporting:
        reporting["sales_impact"] = compute_sales_impact(float(reporting.get("closed_amount", 0) or 0))
```

And include `"reporting": reporting` in the response dict.

- [ ] **Step 4: Extend recommendation results with reporting metrics**

In `src/api/rcars/workers/recommend.py`, after the candidates are built (in the `candidates_json` list comprehension), add a lookup:

```python
        from rcars.services.reporting_sync import extract_base_name, compute_sales_impact

        for candidate in candidates_json:
            base_name = extract_base_name(candidate["ci_name"])
            metrics = wctx.db.get_reporting_metrics(base_name)
            if metrics:
                candidate["provisions_quarter"] = metrics["provisions_quarter"]
                candidate["avg_cost_per_provision"] = float(metrics["avg_cost_per_provision"])
                candidate["sales_impact"] = compute_sales_impact(float(metrics["closed_amount"] or 0))
            else:
                candidate["provisions_quarter"] = None
                candidate["avg_cost_per_provision"] = None
                candidate["sales_impact"] = None
```

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/api/routes/analysis.py src/api/rcars/api/routes/admin.py \
        src/api/rcars/api/routes/catalog.py src/api/rcars/workers/recommend.py
git commit -m "Add retirement dashboard, sync trigger, and reporting enrichment endpoints"
```

---

## Task 8: Frontend — Retirement Dashboard Page + Nav

**Files:**
- Create: `src/frontend/src/pages/RetirementPage.tsx`
- Modify: `src/frontend/src/services/api.ts`
- Modify: `src/frontend/src/App.tsx`
- Modify: `src/frontend/src/components/lcars/LcarsSidebar.tsx`

- [ ] **Step 1: Add API types and calls**

Add to `src/frontend/src/services/api.ts`:

```typescript
export interface ReportingMetricsItem {
  catalog_base_name: string
  display_name: string
  provisions: number
  provisions_quarter: number
  requests: number
  experiences: number
  unique_users: number
  success_ratio: number
  failure_ratio: number
  touched_amount: number
  closed_amount: number
  total_cost: number
  avg_cost_per_provision: number
  first_provision: string | null
  last_provision: string | null
  retirement_score: number
  synced_at: string
  category: string | null
  product: string | null
  product_family: string | null
  sales_impact: string | null
  stages: Array<{ stage: string; ci_name: string; catalog_url: string }>
}

export interface RetirementDashboardResponse {
  items: ReportingMetricsItem[]
  total: number
  synced_at: string | null
  summary: { total: number; high: number; review: number; keepers: number; last_synced: string | null } | null
}
```

Add to the `api` object:

```typescript
  getRetirementDashboard: (params?: {
    sort_by?: string; sort_dir?: string; min_score?: number;
    category?: string; has_prod?: boolean; search?: string;
  }) => {
    const qs = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
      })
    }
    const query = qs.toString()
    return request<RetirementDashboardResponse>(`/analysis/retirement${query ? '?' + query : ''}`)
  },

  syncReporting: () =>
    request<{ job_id: string }>('/admin/sync-reporting', { method: 'POST' }),
```

- [ ] **Step 2: Create the RetirementPage component**

Create `src/frontend/src/pages/RetirementPage.tsx`:

```tsx
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ReportingMetricsItem } from '../services/api'

type SortField = 'retirement_score' | 'provisions' | 'total_cost' | 'closed_amount' | 'touched_amount' | 'display_name'
type ScoreFilter = 'all' | 'high' | 'review' | 'keepers'

const fmt = (n: number) => {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toFixed(0)}`
}

const fmtRoi = (amount: number, cost: number) => {
  if (cost <= 0 || amount <= 0) return '—'
  return `${(amount / cost).toFixed(1)}x`
}

const scoreColor = (score: number) => {
  if (score >= 75) return '#c9190b'
  if (score >= 50) return '#e8a838'
  return '#3e8635'
}

const stageBadgeColor: Record<string, string> = {
  prod: '#3e8635', event: '#0066cc', dev: '#e8a838', test: '#6a6e73',
}

export function RetirementPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<ReportingMetricsItem[]>([])
  const [summary, setSummary] = useState<{ total: number; high: number; review: number; keepers: number } | null>(null)
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortField>('retirement_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>('all')
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const minScore = scoreFilter === 'high' ? 75 : scoreFilter === 'review' ? 50 : scoreFilter === 'keepers' ? 0 : undefined
      const maxForKeepers = scoreFilter === 'keepers'
      const data = await api.getRetirementDashboard({
        sort_by: sortBy, sort_dir: sortDir,
        min_score: minScore,
        search: search || undefined,
      })
      let filtered = data.items
      if (maxForKeepers) {
        filtered = filtered.filter(i => i.retirement_score < 50)
      } else if (scoreFilter === 'review') {
        filtered = filtered.filter(i => i.retirement_score < 75)
      }
      setItems(filtered)
      setSummary(data.summary)
      setSyncedAt(data.synced_at)
    } finally {
      setLoading(false)
    }
  }, [sortBy, sortDir, scoreFilter, search])

  useEffect(() => { loadData() }, [loadData])

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(field)
      setSortDir('desc')
    }
  }

  const toggleExpand = (name: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const sortArrow = (field: SortField) => sortBy === field ? (sortDir === 'desc' ? ' ▼' : ' ▲') : ''

  const syncAge = syncedAt
    ? `${Math.round((Date.now() - new Date(syncedAt).getTime()) / 3600000)}h ago`
    : 'never'

  return (
    <div style={{ padding: '1.5rem', color: '#c8ccd0', maxWidth: '100%', overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0 }}>Retirement Analysis</h3>
        <span style={{ fontSize: '0.85rem', color: '#6a6e73' }}>Last synced: {syncAge}</span>
      </div>

      {summary && (
        <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', fontSize: '0.9rem' }}>
          <span>Total: <strong>{summary.total}</strong></span>
          <span style={{ color: '#c9190b' }}>High (≥75): <strong>{summary.high}</strong></span>
          <span style={{ color: '#e8a838' }}>Review (50-74): <strong>{summary.review}</strong></span>
          <span style={{ color: '#3e8635' }}>Keepers ({'<'}50): <strong>{summary.keepers}</strong></span>
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {(['all', 'high', 'review', 'keepers'] as ScoreFilter[]).map(f => (
          <button key={f} onClick={() => setScoreFilter(f)}
            style={{
              padding: '0.3rem 0.8rem', borderRadius: '4px', cursor: 'pointer',
              border: scoreFilter === f ? '1px solid #e8a838' : '1px solid #2a2d35',
              background: scoreFilter === f ? '#1e2030' : '#0d1117', color: '#c8ccd0',
            }}>
            {f === 'all' ? 'All' : f === 'high' ? 'High ≥75' : f === 'review' ? 'Review 50-74' : 'Keepers <50'}
          </button>
        ))}
        <input
          type="text" placeholder="Search display name..."
          value={search} onChange={e => setSearch(e.target.value)}
          style={{
            padding: '0.3rem 0.6rem', borderRadius: '4px', marginLeft: 'auto',
            border: '1px solid #2a2d35', background: '#0d1117', color: '#c8ccd0', width: '220px',
          }}
        />
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2a2d35', textAlign: 'left' }}>
              <th style={{ padding: '0.5rem', cursor: 'pointer' }} onClick={() => toggleSort('display_name')}>
                Name{sortArrow('display_name')}
              </th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('retirement_score')}>
                Score{sortArrow('retirement_score')}
              </th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('provisions')}>
                Provisions{sortArrow('provisions')}
              </th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('touched_amount')}>
                Touched{sortArrow('touched_amount')}
              </th>
              <th style={{ padding: '0.5rem', textAlign: 'right' }}>T-ROI</th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('closed_amount')}>
                Closed{sortArrow('closed_amount')}
              </th>
              <th style={{ padding: '0.5rem', textAlign: 'right' }}>C-ROI</th>
              <th style={{ padding: '0.5rem', cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('total_cost')}>
                Cost{sortArrow('total_cost')}
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => {
              const isExpanded = expanded.has(item.catalog_base_name)
              return (
                <>
                  <tr key={item.catalog_base_name}
                    onClick={() => toggleExpand(item.catalog_base_name)}
                    style={{ borderBottom: '1px solid #1a1d25', cursor: 'pointer' }}>
                    <td style={{ padding: '0.5rem', maxWidth: '350px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span onClick={e => { e.stopPropagation(); navigate(`/browse?search=${encodeURIComponent(item.display_name)}`) }}
                        style={{ color: '#58a6ff', cursor: 'pointer' }} title={item.display_name}>
                        {item.display_name}
                      </span>
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>
                      <span style={{ color: scoreColor(item.retirement_score), fontWeight: 'bold' }}>
                        {item.retirement_score}
                      </span>
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>{item.provisions.toLocaleString()}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>{fmt(item.touched_amount)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right', color: '#6a6e73' }}>{fmtRoi(item.touched_amount, item.total_cost)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>{fmt(item.closed_amount)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right', color: '#6a6e73' }}>{fmtRoi(item.closed_amount, item.total_cost)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>{fmt(item.total_cost)}</td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${item.catalog_base_name}-detail`} style={{ background: '#0d1117' }}>
                      <td colSpan={8} style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', fontSize: '0.85rem' }}>
                          <div>
                            <strong>Environments:</strong>{' '}
                            {item.stages.map(s => (
                              <a key={s.ci_name} href={s.catalog_url} target="_blank" rel="noreferrer"
                                style={{
                                  display: 'inline-block', padding: '0.15rem 0.5rem', borderRadius: '3px', marginRight: '0.3rem',
                                  background: stageBadgeColor[s.stage] || '#6a6e73', color: '#fff', fontSize: '0.75rem',
                                  textDecoration: 'none',
                                }}>
                                {s.stage}
                              </a>
                            ))}
                            {item.stages.length === 0 && <span style={{ color: '#6a6e73' }}>none in RCARS</span>}
                          </div>
                          <div><strong>Unique Users:</strong> {item.unique_users.toLocaleString()}</div>
                          <div><strong>Experiences:</strong> {item.experiences.toLocaleString()}</div>
                          <div><strong>Cost/Provision:</strong> ${item.avg_cost_per_provision.toFixed(2)}</div>
                          <div><strong>Success:</strong> {(item.success_ratio * 100).toFixed(1)}%</div>
                          <div><strong>Failure:</strong> {(item.failure_ratio * 100).toFixed(1)}%</div>
                          <div><strong>First Provision:</strong> {item.first_provision || 'N/A'}</div>
                          <div><strong>Last Provision:</strong> {item.last_provision || 'N/A'}</div>
                          <div><strong>Category:</strong> {item.category || '—'}</div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Add route to App.tsx**

In `src/frontend/src/App.tsx`, add the import and route:

```typescript
import { RetirementPage } from './pages/RetirementPage'
```

Add inside the `{auth.isAdmin && (` block, after the overlap route:

```typescript
<Route path="/analysis/retirement" element={<RetirementPage />} />
```

- [ ] **Step 4: Add nav item to sidebar**

In `src/frontend/src/components/lcars/LcarsSidebar.tsx`, find the "Overlap" NavLink inside the `{isAnalysisSection && (` block. Add the "Retirement" link after it:

```tsx
<NavLink to="/analysis/retirement" className={({ isActive }) =>
  `nav-item history-item${isActive ? ' active' : ''}`}>
  Retirement
</NavLink>
```

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/pages/RetirementPage.tsx src/frontend/src/services/api.ts \
        src/frontend/src/App.tsx src/frontend/src/components/lcars/LcarsSidebar.tsx
git commit -m "Add retirement dashboard page under Content Analysis"
```

---

## Task 9: Recommendation Card Enrichment

**Files:**
- Modify: `src/frontend/src/components/advisor/RecCard.tsx`

- [ ] **Step 1: Add metrics display to rec card**

In `src/frontend/src/components/advisor/RecCard.tsx`, find where the card content is rendered (after `caveats` or the last content section). Add a reporting metrics line:

```tsx
{candidate.provisions_quarter !== null && candidate.provisions_quarter !== undefined && (
  <div style={{
    display: 'flex', gap: '1rem', padding: '0.5rem 0', marginTop: '0.5rem',
    borderTop: '1px solid #2a2d35', fontSize: '0.8rem', color: '#8b949e',
  }}>
    <span>{candidate.provisions_quarter.toLocaleString()} provisions (last 90d)</span>
    {candidate.avg_cost_per_provision != null && (
      <span>${candidate.avg_cost_per_provision.toFixed(2)} / provision</span>
    )}
    {candidate.sales_impact && candidate.sales_impact !== 'low' && (
      <span title="Based on closed sales opportunities linked to provisions of this asset over the trailing year."
        style={{
          padding: '0.1rem 0.4rem', borderRadius: '3px', fontSize: '0.75rem',
          background: candidate.sales_impact === 'high' ? '#1a4731' : '#3d2e00',
          color: candidate.sales_impact === 'high' ? '#3e8635' : '#e8a838',
          cursor: 'help',
        }}>
        {candidate.sales_impact === 'high' ? 'High Sales Impact' : 'Moderate Sales Impact'}
      </span>
    )}
  </div>
)}
```

Ensure the candidate type interface includes the new fields. In `api.ts` or wherever the candidate type is defined, add:

```typescript
  provisions_quarter?: number | null
  avg_cost_per_provision?: number | null
  sales_impact?: string | null
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/components/advisor/RecCard.tsx src/frontend/src/services/api.ts
git commit -m "Add reporting metrics to recommendation cards"
```

---

## Task 10: Deploy + Verify

- [ ] **Step 1: Add MCP credentials to Ansible vars**

Add to `ansible/vars/dev.yml` (gitignored):

```yaml
rcars_reporting_mcp_url: "{{ vault_reporting_mcp_url }}"
rcars_reporting_mcp_token: "{{ vault_reporting_mcp_token }}"
```

The actual URL and token values are stored in Ansible Vault — see the team secrets repository for current values.

Add corresponding environment variables to the scan worker deployment template so they're injected as `RCARS_REPORTING_MCP_URL` and `RCARS_REPORTING_MCP_TOKEN`.

- [ ] **Step 2: Push and build**

```bash
git push origin main
ansible-playbook ansible/deploy.yml -e env=dev --tags update
```

- [ ] **Step 3: Run initial sync via CLI**

SSH to the dev environment or exec into the API pod:

```bash
rcars reporting-db sync
```

Expected: Metrics synced, row count printed.

- [ ] **Step 4: Verify CLI status**

```bash
rcars reporting-db status
```

Expected: Shows last synced timestamp, total items, score distribution.

- [ ] **Step 5: Verify retirement dashboard in browser**

Navigate to the RCARS dev URL → Content Analysis → Retirement. Verify:
- Table loads with data
- Sorting works (click column headers)
- Score filter buttons work
- Row expansion shows environments, details
- Stage badges link to catalog.demo.redhat.com

- [ ] **Step 6: Verify rec card enrichment**

Run an advisor query. Check that rec cards show provisions count, cost per provision, and sales impact badge (if applicable).

- [ ] **Step 7: Commit any fixes**

If any adjustments are needed from manual testing, fix and commit.
