# Retirement Workflow Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a checklist-style retirement workflow to the RCARS retirement dashboard so curators can review, approve, and start retirement of catalog items — creating a Jira ticket and auto-closing when items leave Babylon.

**Architecture:** New `retirement_workflow` table stores per-item workflow state (reviewed → approved → notified → started → retired). API endpoints mutate workflow state. The existing retirement dashboard endpoint is enriched via LEFT JOIN. A new Jira service module (`jira.py`) creates tickets via direct REST API. The nightly CRD sync auto-closes workflows when items disappear from Babylon. Frontend adds a slide-out drawer with workflow checklist and an inline "Retirement In Process" badge.

**Tech Stack:** Python 3.11 / FastAPI 2.0 / PostgreSQL / React 19 / TypeScript / Vite

## Global Constraints

- Migration numbering: next is 012 (011 is the sliding window change on this branch)
- All API endpoints require `require_curator` auth
- Jira integration uses direct REST API v3 with Basic auth (urllib), no MCP tools, no LLM tokens
- Follow existing patterns: Pydantic request bodies, `request.app.state.db`, `dict_row` cursors
- Frontend follows existing LCARS/PF6 styling patterns and the BrowsePage drawer structure

---

### Task 1: Migration + Schema + DB Methods

**Files:**
- Create: `src/api/alembic/versions/012_retirement_workflow.py`
- Modify: `src/api/rcars/db/database.py` — SCHEMA_SQL + 5 new methods
- Create: `src/api/tests/test_retirement_workflow.py`

**Interfaces:**
- Produces:
  - `Database.get_retirement_workflow(base_name: str) -> dict | None`
  - `Database.upsert_retirement_workflow(base_name: str, fields: dict) -> dict`
  - `Database.delete_retirement_workflow(base_name: str) -> bool`
  - `Database.list_retirement_workflows(status: str | None = None) -> list[dict]`
  - `Database.auto_close_retired_workflows(retired_base_names: set[str]) -> int`

- [ ] **Step 1: Create migration 012**

Create `src/api/alembic/versions/012_retirement_workflow.py`:

```python
"""Add retirement_workflow table for curator-driven retirement tracking.

Revision ID: 012
Revises: 011
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS retirement_workflow (
            catalog_base_name    TEXT PRIMARY KEY,
            status               TEXT NOT NULL DEFAULT 'reviewed',
            step_reviewed_at     TIMESTAMPTZ,
            step_reviewed_by     TEXT,
            step_approved_at     TIMESTAMPTZ,
            step_approved_by     TEXT,
            approval_reason      TEXT,
            approval_snapshot    JSONB,
            step_notified_at     TIMESTAMPTZ,
            step_notified_by     TEXT,
            step_started_at      TIMESTAMPTZ,
            step_started_by      TEXT,
            retirement_target_date DATE,
            step_retired_at      TIMESTAMPTZ,
            replacement_ci       TEXT,
            replacement_name     TEXT,
            curator_notes        TEXT,
            jira_key             TEXT,
            jira_project         TEXT NOT NULL DEFAULT 'RHDPCD',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_retirement_workflow_status
            ON retirement_workflow (status);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS retirement_workflow;")
```

- [ ] **Step 2: Add table DDL to SCHEMA_SQL in database.py**

Add after the `reporting_metrics` table definition in `SCHEMA_SQL` (around line 277):

```sql
CREATE TABLE IF NOT EXISTS retirement_workflow (
    catalog_base_name    TEXT PRIMARY KEY,
    status               TEXT NOT NULL DEFAULT 'reviewed',
    step_reviewed_at     TIMESTAMPTZ,
    step_reviewed_by     TEXT,
    step_approved_at     TIMESTAMPTZ,
    step_approved_by     TEXT,
    approval_reason      TEXT,
    approval_snapshot    JSONB,
    step_notified_at     TIMESTAMPTZ,
    step_notified_by     TEXT,
    step_started_at      TIMESTAMPTZ,
    step_started_by      TEXT,
    retirement_target_date DATE,
    step_retired_at      TIMESTAMPTZ,
    replacement_ci       TEXT,
    replacement_name     TEXT,
    curator_notes        TEXT,
    jira_key             TEXT,
    jira_project         TEXT NOT NULL DEFAULT 'RHDPCD',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_retirement_workflow_status
    ON retirement_workflow (status);
```

- [ ] **Step 3: Write failing tests for DB methods**

Create `src/api/tests/test_retirement_workflow.py`:

```python
"""Tests for retirement workflow DB methods and status logic."""

import json
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch

import pytest


def _make_db_mock():
    """Create a mock that tracks workflow records in memory."""
    store = {}

    class MockDB:
        def get_retirement_workflow(self, base_name):
            return store.get(base_name)

        def upsert_retirement_workflow(self, base_name, fields):
            existing = store.get(base_name, {})
            existing.update(fields)
            existing["catalog_base_name"] = base_name
            existing.setdefault("created_at", datetime.now().isoformat())
            existing["updated_at"] = datetime.now().isoformat()
            store[base_name] = existing
            return existing

        def delete_retirement_workflow(self, base_name):
            return store.pop(base_name, None) is not None

        def list_retirement_workflows(self, status=None):
            rows = list(store.values())
            if status:
                rows = [r for r in rows if r.get("status") == status]
            return rows

        def auto_close_retired_workflows(self, retired_base_names):
            count = 0
            for name in retired_base_names:
                wf = store.get(name)
                if wf and not wf.get("step_retired_at"):
                    wf["step_retired_at"] = datetime.now().isoformat()
                    wf["status"] = "retired"
                    count += 1
            return count

    return MockDB(), store


class TestRetirementWorkflowDB:
    def test_get_nonexistent_returns_none(self):
        db, _ = _make_db_mock()
        assert db.get_retirement_workflow("nonexistent") is None

    def test_upsert_creates_new(self):
        db, store = _make_db_mock()
        result = db.upsert_retirement_workflow("test-item", {
            "status": "reviewed",
            "step_reviewed_at": "2026-07-02T10:00:00",
            "step_reviewed_by": "curator@redhat.com",
        })
        assert result["catalog_base_name"] == "test-item"
        assert result["status"] == "reviewed"
        assert "test-item" in store

    def test_upsert_updates_existing(self):
        db, _ = _make_db_mock()
        db.upsert_retirement_workflow("test-item", {"status": "reviewed"})
        db.upsert_retirement_workflow("test-item", {"status": "approved", "approval_reason": "low usage"})
        result = db.get_retirement_workflow("test-item")
        assert result["status"] == "approved"
        assert result["approval_reason"] == "low usage"

    def test_delete_returns_true_when_exists(self):
        db, _ = _make_db_mock()
        db.upsert_retirement_workflow("test-item", {"status": "reviewed"})
        assert db.delete_retirement_workflow("test-item") is True
        assert db.get_retirement_workflow("test-item") is None

    def test_delete_returns_false_when_missing(self):
        db, _ = _make_db_mock()
        assert db.delete_retirement_workflow("nonexistent") is False

    def test_list_all(self):
        db, _ = _make_db_mock()
        db.upsert_retirement_workflow("item-a", {"status": "reviewed"})
        db.upsert_retirement_workflow("item-b", {"status": "approved"})
        assert len(db.list_retirement_workflows()) == 2

    def test_list_filtered_by_status(self):
        db, _ = _make_db_mock()
        db.upsert_retirement_workflow("item-a", {"status": "reviewed"})
        db.upsert_retirement_workflow("item-b", {"status": "approved"})
        result = db.list_retirement_workflows(status="approved")
        assert len(result) == 1
        assert result[0]["status"] == "approved"

    def test_auto_close_sets_retired(self):
        db, _ = _make_db_mock()
        db.upsert_retirement_workflow("item-a", {"status": "started"})
        db.upsert_retirement_workflow("item-b", {"status": "started"})
        closed = db.auto_close_retired_workflows({"item-a"})
        assert closed == 1
        assert db.get_retirement_workflow("item-a")["status"] == "retired"
        assert db.get_retirement_workflow("item-b")["status"] == "started"

    def test_auto_close_skips_already_retired(self):
        db, _ = _make_db_mock()
        db.upsert_retirement_workflow("item-a", {
            "status": "retired",
            "step_retired_at": "2026-06-01T00:00:00",
        })
        closed = db.auto_close_retired_workflows({"item-a"})
        assert closed == 0


class TestDeriveStatus:
    """Test the status derivation helper."""

    def test_derive_from_steps(self):
        from rcars.services.retirement import derive_status

        assert derive_status({}) == "reviewed"
        assert derive_status({"step_reviewed_at": "x"}) == "reviewed"
        assert derive_status({"step_reviewed_at": "x", "step_approved_at": "x"}) == "approved"
        assert derive_status({"step_reviewed_at": "x", "step_approved_at": "x",
                              "step_notified_at": "x"}) == "notified"
        assert derive_status({"step_reviewed_at": "x", "step_approved_at": "x",
                              "step_started_at": "x"}) == "started"
        assert derive_status({"step_retired_at": "x"}) == "retired"
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_retirement_workflow.py -v`
Expected: First class passes (mock-based), second class fails with `ModuleNotFoundError: No module named 'rcars.services.retirement'`

- [ ] **Step 5: Add DB methods to Database class**

Add the five methods to `src/api/rcars/db/database.py` in the `# ── Reporting ──` section (after the existing reporting methods, around line 1900+):

```python
    # ── Retirement Workflow ──

    def get_retirement_workflow(self, base_name: str) -> dict | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT * FROM retirement_workflow WHERE catalog_base_name = %s",
                    (base_name,),
                )
                return cur.fetchone()

    def upsert_retirement_workflow(self, base_name: str, fields: dict) -> dict:
        fields["catalog_base_name"] = base_name
        fields["updated_at"] = "NOW()"
        columns = list(fields.keys())
        values_clause = ", ".join(
            f"NOW()" if fields[c] == "NOW()" else f"%({c})s"
            for c in columns
        )
        update_clause = ", ".join(
            f"{c} = NOW()" if fields[c] == "NOW()" else f"{c} = EXCLUDED.{c}"
            for c in columns if c != "catalog_base_name"
        )
        params = {c: v for c, v in fields.items() if v != "NOW()"}
        params["catalog_base_name"] = base_name
        if "approval_snapshot" in params and isinstance(params["approval_snapshot"], dict):
            import json
            params["approval_snapshot"] = json.dumps(params["approval_snapshot"])

        col_list = ", ".join(columns)
        sql = f"""
            INSERT INTO retirement_workflow ({col_list})
            VALUES ({values_clause})
            ON CONFLICT (catalog_base_name) DO UPDATE SET {update_clause}
            RETURNING *
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
            conn.commit()
        return row

    def delete_retirement_workflow(self, base_name: str) -> bool:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM retirement_workflow WHERE catalog_base_name = %s",
                    (base_name,),
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def list_retirement_workflows(self, status: str | None = None) -> list[dict]:
        conditions = []
        params: dict = {}
        if status:
            conditions.append("status = %(status)s")
            params["status"] = status
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM retirement_workflow {where} ORDER BY updated_at DESC"
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def auto_close_retired_workflows(self, retired_base_names: set[str]) -> int:
        if not retired_base_names:
            return 0
        placeholders = ", ".join(["%s"] * len(retired_base_names))
        sql = f"""
            UPDATE retirement_workflow
            SET step_retired_at = NOW(), status = 'retired', updated_at = NOW()
            WHERE catalog_base_name IN ({placeholders})
              AND step_retired_at IS NULL
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, list(retired_base_names))
                count = cur.rowcount
            conn.commit()
        return count
```

- [ ] **Step 6: Create status derivation helper**

Create `src/api/rcars/services/retirement.py`:

```python
"""Retirement workflow business logic."""

from __future__ import annotations

STEP_ORDER = [
    ("step_retired_at", "retired"),
    ("step_started_at", "started"),
    ("step_notified_at", "notified"),
    ("step_approved_at", "approved"),
    ("step_reviewed_at", "reviewed"),
]


def derive_status(fields: dict) -> str:
    """Derive the workflow status from the highest completed step."""
    for step_field, status in STEP_ORDER:
        if fields.get(step_field):
            return status
    return "reviewed"
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_retirement_workflow.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/api/alembic/versions/012_retirement_workflow.py \
        src/api/rcars/db/database.py \
        src/api/rcars/services/retirement.py \
        src/api/tests/test_retirement_workflow.py
git commit -m "[RHDPCD-27] Add retirement_workflow table, DB methods, and status logic"
```

---

### Task 2: Jira Service Module

**Files:**
- Create: `src/api/rcars/services/jira.py`
- Modify: `src/api/rcars/config.py` — add Jira settings
- Create: `src/api/tests/test_jira_service.py`

**Interfaces:**
- Consumes: workflow dict, reporting_metrics dict, settings object
- Produces:
  - `create_retirement_ticket(settings, workflow: dict, metrics: dict) -> str` — returns Jira key
  - `link_to_template(settings, jira_key: str) -> None`
  - `build_retirement_description(workflow: dict, metrics: dict) -> str`

- [ ] **Step 1: Add Jira config settings**

In `src/api/rcars/config.py`, add to the `Settings` class (after the `reporting_*` fields, around line 89):

```python
    jira_base_url: str = "https://redhat.atlassian.net"
    jira_api_email: str = ""
    jira_api_token: str = ""
    jira_retirement_template: str = "GPTEINFRA-14367"
```

- [ ] **Step 2: Write failing test for description builder**

Create `src/api/tests/test_jira_service.py`:

```python
"""Tests for Jira retirement ticket creation."""

import json
from unittest.mock import patch, MagicMock
from datetime import date

from rcars.services.jira import build_retirement_description, create_retirement_ticket


class TestBuildRetirementDescription:
    def test_basic_description(self):
        workflow = {
            "catalog_base_name": "openshift_cnv.ocp-virt-demo",
            "approval_reason": "Low usage, outdated content",
            "curator_notes": "Replaced by newer workshop",
            "replacement_ci": "openshift_cnv.ocp4-getting-started",
            "replacement_name": "OCP4 Getting Started",
            "retirement_target_date": date(2026, 8, 1),
            "approval_snapshot": {
                "provisions": 6,
                "experiences": 12,
                "unique_users": 4,
                "touched_amount": 50000.0,
                "closed_amount": 0,
                "total_cost": 8500.0,
                "retirement_score": 72,
                "window": "12m",
                "snapshot_date": "2026-07-02",
            },
        }
        metrics = {"display_name": "OCP Virt Demo"}
        desc = build_retirement_description(workflow, metrics)
        assert "OCP Virt Demo" in desc
        assert "openshift_cnv.ocp-virt-demo" in desc
        assert "Low usage, outdated content" in desc
        assert "OCP4 Getting Started" in desc
        assert "72" in desc
        assert "2026-08-01" in desc
        assert "demo.redhat.com" in desc

    def test_no_replacement(self):
        workflow = {
            "catalog_base_name": "test.item",
            "approval_reason": "Obsolete",
            "curator_notes": None,
            "replacement_ci": None,
            "replacement_name": None,
            "retirement_target_date": date(2026, 8, 1),
            "approval_snapshot": {
                "provisions": 0, "experiences": 0, "unique_users": 0,
                "touched_amount": 0, "closed_amount": 0, "total_cost": 0,
                "retirement_score": 85, "window": "12m", "snapshot_date": "2026-07-02",
            },
        }
        desc = build_retirement_description(workflow, {"display_name": "Test Item"})
        assert "N/A" in desc


class TestCreateRetirementTicket:
    @patch("rcars.services.jira._jira_request")
    def test_creates_ticket_and_returns_key(self, mock_request):
        mock_request.side_effect = [
            {"key": "RHDPCD-999"},
            None,
        ]
        settings = MagicMock()
        settings.jira_base_url = "https://redhat.atlassian.net"
        settings.jira_api_email = "svc@redhat.com"
        settings.jira_api_token = "tok"
        settings.jira_retirement_template = "GPTEINFRA-14367"

        workflow = {
            "catalog_base_name": "test.item",
            "approval_reason": "Obsolete",
            "curator_notes": None,
            "replacement_ci": None,
            "replacement_name": None,
            "jira_project": "RHDPCD",
            "retirement_target_date": date(2026, 8, 1),
            "approval_snapshot": {
                "provisions": 0, "experiences": 0, "unique_users": 0,
                "touched_amount": 0, "closed_amount": 0, "total_cost": 0,
                "retirement_score": 85, "window": "12m", "snapshot_date": "2026-07-02",
            },
        }
        metrics = {"display_name": "Test Item"}

        key = create_retirement_ticket(settings, workflow, metrics)

        assert key == "RHDPCD-999"
        assert mock_request.call_count == 2

        create_call = mock_request.call_args_list[0]
        assert create_call[0][1] == "/rest/api/3/issue"
        body = create_call[0][3]
        assert body["fields"]["project"]["key"] == "RHDPCD"
        assert body["fields"]["summary"] == 'Retire "Test Item"'
        assert "RHDP_RETIREMENT" in body["fields"]["labels"]

        link_call = mock_request.call_args_list[1]
        assert link_call[0][1] == "/rest/api/3/issueLink"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_jira_service.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 4: Implement Jira service**

Create `src/api/rcars/services/jira.py`:

```python
"""Jira REST API client for retirement ticket creation.

Direct REST API v3 calls with Basic auth. No MCP tools, no LLM tokens.
Follows the same pattern as Publishing House Central's jira_client.py.
"""

from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request
from datetime import date

import structlog

logger = structlog.get_logger(component="jira")


def _jira_request(settings, path: str, method: str = "POST", body: dict | None = None) -> dict | None:
    """Make a Jira REST API request with Basic auth."""
    url = f"{settings.jira_base_url}{path}"
    credentials = base64.b64encode(
        f"{settings.jira_api_email}:{settings.jira_api_token}".encode()
    ).decode()

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        logger.error("jira_request_failed", path=path, status=e.code, body=body_text[:500])
        raise RuntimeError(f"Jira API error {e.code}: {body_text[:200]}")


def build_retirement_description(workflow: dict, metrics: dict) -> str:
    """Build the Jira ticket description markdown."""
    base_name = workflow["catalog_base_name"]
    display_name = metrics.get("display_name", base_name)
    reason = workflow.get("approval_reason", "")
    notes = workflow.get("curator_notes")
    replacement_ci = workflow.get("replacement_ci")
    replacement_name = workflow.get("replacement_name")
    target_date = workflow.get("retirement_target_date")
    snapshot = workflow.get("approval_snapshot") or {}

    if isinstance(target_date, date):
        target_date = target_date.isoformat()

    replacement_text = f"{replacement_name} ({replacement_ci})" if replacement_ci else "N/A"

    notes_line = f"\n* {notes}" if notes else ""

    snapshot_date = snapshot.get("snapshot_date", "")
    provisions = snapshot.get("provisions", 0)
    experiences = snapshot.get("experiences", 0)
    unique_users = snapshot.get("unique_users", 0)
    touched = snapshot.get("touched_amount", 0)
    closed = snapshot.get("closed_amount", 0)
    cost = snapshot.get("total_cost", 0)
    score = snapshot.get("retirement_score", 0)

    replacement_adoc = ""
    if replacement_ci:
        rhdp_replacement = f"https://demo.redhat.com/catalog?search={replacement_ci}"
        replacement_adoc = (
            f" Please use this as an alternative: "
            f"link:{rhdp_replacement}[{replacement_name}, window=\"_blank\"]\n\n"
        )

    return f"""**CI Name:** {display_name}

**RHDP URL:** https://demo.redhat.com/catalog?search={base_name}

**AgV:** https://github.com/rhpds/agnosticv/tree/master/{base_name.replace('.', '/')}

**Retirement Notice:** Target date: {target_date}

**Replacement CI:** {replacement_text}

**Reason & Notes:**

* {reason}{notes_line}

**Metrics at approval (snapshot {snapshot_date}):**

| Metric | Value |
|--------|-------|
| Retirement Score | {score} |
| Provisions | {provisions} |
| Experiences | {experiences} |
| Unique Users | {unique_users} |
| Touched Amount | ${touched:,.0f} |
| Closed Amount | ${closed:,.0f} |
| Total Cost | ${cost:,.0f} |

---

**Suggested adoc template:**

```
[IMPORTANT]
.RETIREMENT NOTICE
****
This item will be retired on **{target_date}**.{replacement_adoc}For any questions regarding this retirement, please contact Nate Stephany at mailto:nstephan@redhat.com[nstephan@redhat.com].
****
```"""


def create_retirement_ticket(settings, workflow: dict, metrics: dict) -> str:
    """Create a Jira retirement ticket and link to template. Returns the Jira key."""
    display_name = metrics.get("display_name", workflow["catalog_base_name"])
    project = workflow.get("jira_project", "RHDPCD")

    description = build_retirement_description(workflow, metrics)

    issue_body = {
        "fields": {
            "project": {"key": project},
            "issuetype": {"id": "10014"},
            "summary": f'Retire "{display_name}"',
            "description": description,
            "labels": ["RHDP_RETIREMENT"],
        }
    }
    result = _jira_request(settings, "/rest/api/3/issue", body=issue_body)
    jira_key = result["key"]
    logger.info("jira_ticket_created", jira_key=jira_key, base_name=workflow["catalog_base_name"])

    link_body = {
        "type": {"name": "Cloners"},
        "inwardIssue": {"key": settings.jira_retirement_template},
        "outwardIssue": {"key": jira_key},
    }
    _jira_request(settings, "/rest/api/3/issueLink", body=link_body)
    logger.info("jira_template_linked", jira_key=jira_key, template=settings.jira_retirement_template)

    return jira_key
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_jira_service.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/config.py \
        src/api/rcars/services/jira.py \
        src/api/tests/test_jira_service.py
git commit -m "[RHDPCD-27] Add Jira service for retirement ticket creation via REST API"
```

---

### Task 3: API Endpoints + Dashboard Enrichment

**Files:**
- Modify: `src/api/rcars/api/routes/analysis.py` — add 7 workflow endpoints + enrich dashboard
- Modify: `src/api/rcars/db/database.py` — update `list_reporting_metrics` for LEFT JOIN + `retire_removed_items` for auto-close

**Interfaces:**
- Consumes: `Database` methods from Task 1, `jira.py` from Task 2, `derive_status` from Task 1
- Produces: 7 REST endpoints under `/api/v1/analysis/retirement/workflow/`

- [ ] **Step 1: Update `list_reporting_metrics` to LEFT JOIN retirement_workflow**

In `src/api/rcars/db/database.py`, modify the `list_reporting_metrics()` method. Add a `workflow_status` parameter and update the SQL:

Add parameter:
```python
def list_reporting_metrics(
    self,
    sort_by: str = "retirement_score",
    sort_dir: str = "desc",
    min_score: int | None = None,
    category: str | None = None,
    has_prod: bool | None = None,
    search: str | None = None,
    workflow_status: str | None = None,
) -> list[dict]:
```

Add workflow_status filter condition (after the existing `has_prod` block):
```python
    if workflow_status == "none":
        conditions.append("rw.catalog_base_name IS NULL")
    elif workflow_status == "in_process":
        conditions.append("rw.status IN ('reviewed', 'approved', 'notified')")
    elif workflow_status:
        conditions.append("rw.status = %(workflow_status)s")
        params["workflow_status"] = workflow_status
```

Update the SQL query to add the LEFT JOIN and select workflow columns:
```sql
    sql = f"""
        SELECT rm.*,
               ci.category, ci.product, ci.product_family,
               rw.status AS workflow_status,
               rw.jira_key,
               rw.retirement_target_date
        FROM reporting_metrics rm
        LEFT JOIN LATERAL (
            SELECT category, product, product_family
            FROM catalog_items
            WHERE ci_name LIKE rm.catalog_base_name || '.%%'
            ORDER BY CASE WHEN retired_at IS NULL THEN 0 ELSE 1 END,
                     CASE stage WHEN 'prod' THEN 0 WHEN 'event' THEN 1 ELSE 2 END
            LIMIT 1
        ) ci ON true
        LEFT JOIN retirement_workflow rw ON rw.catalog_base_name = rm.catalog_base_name
        {where}
        ORDER BY rm.{sort_by} {direction}
    """
```

- [ ] **Step 2: Update `retire_removed_items` to auto-close workflows**

In `src/api/rcars/db/database.py`, at the end of `retire_removed_items()` (before the return statement), add:

```python
        if newly_retired:
            retired_base_names = set()
            for item in newly_retired:
                ci = item["ci_name"]
                for suffix in (".prod", ".dev", ".event", ".test"):
                    if ci.endswith(suffix):
                        retired_base_names.add(ci[:-len(suffix)])
                        break
            if retired_base_names:
                closed = self.auto_close_retired_workflows(retired_base_names)
                if closed:
                    logger.info("auto_closed_retirement_workflows",
                                component="rcars", action="auto_close",
                                count=closed)
```

- [ ] **Step 3: Add workflow endpoints to analysis.py**

Add Pydantic models and endpoints to `src/api/rcars/api/routes/analysis.py`. Add the imports at the top:

```python
from pydantic import BaseModel, Field
```

Add Pydantic models after the `WINDOW_KEYS` constant:

```python
class ApproveRequest(BaseModel):
    reason: str = Field(min_length=1)
    replacement_ci: str | None = None
    replacement_name: str | None = None

class StartRequest(BaseModel):
    target_days: int = 30
    jira_project: str = "RHDPCD"

class NotesRequest(BaseModel):
    notes: str = Field(max_length=5000)
```

Add the workflow endpoints after the retirement_dashboard function:

```python
@router.get("/workflow/{base_name}")
async def get_workflow(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    wf = db.get_retirement_workflow(base_name)
    if not wf:
        return {"workflow": None}
    return {"workflow": wf}


@router.put("/workflow/{base_name}/review")
async def review_item(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    from rcars.services.retirement import derive_status
    fields = {
        "step_reviewed_at": "NOW()",
        "step_reviewed_by": user,
    }
    fields["status"] = derive_status({**fields, "step_reviewed_at": "set"})
    result = db.upsert_retirement_workflow(base_name, fields)
    db.log_action(base_name, "retirement_reviewed", user, f"Marked as reviewed")
    return {"status": "ok", "workflow": result}


@router.put("/workflow/{base_name}/approve")
async def approve_item(base_name: str, body: ApproveRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    from rcars.services.retirement import derive_status
    from datetime import datetime

    metrics = db.get_reporting_metrics(base_name)
    snapshot = {
        "provisions": metrics.get("provisions", 0) if metrics else 0,
        "experiences": metrics.get("experiences", 0) if metrics else 0,
        "unique_users": metrics.get("unique_users", 0) if metrics else 0,
        "touched_amount": float(metrics.get("touched_amount", 0) or 0) if metrics else 0,
        "closed_amount": float(metrics.get("closed_amount", 0) or 0) if metrics else 0,
        "total_cost": float(metrics.get("total_cost", 0) or 0) if metrics else 0,
        "retirement_score": metrics.get("retirement_score", 0) if metrics else 0,
        "window": "12m",
        "snapshot_date": datetime.now().strftime("%Y-%m-%d"),
    }

    fields = {
        "step_reviewed_at": "NOW()",
        "step_reviewed_by": user,
        "step_approved_at": "NOW()",
        "step_approved_by": user,
        "approval_reason": body.reason,
        "approval_snapshot": snapshot,
    }
    if body.replacement_ci:
        fields["replacement_ci"] = body.replacement_ci
        fields["replacement_name"] = body.replacement_name

    fields["status"] = "approved"
    result = db.upsert_retirement_workflow(base_name, fields)
    db.log_action(base_name, "retirement_approved", user, f"Reason: {body.reason}")
    return {"status": "ok", "workflow": result}


@router.put("/workflow/{base_name}/notify")
async def notify_owner(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    fields = {
        "step_notified_at": "NOW()",
        "step_notified_by": user,
        "status": "notified",
    }
    result = db.upsert_retirement_workflow(base_name, fields)
    db.log_action(base_name, "retirement_notified", user, "Owner notified")
    return {"status": "ok", "workflow": result}


@router.put("/workflow/{base_name}/start")
async def start_retirement(base_name: str, body: StartRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    settings = request.app.state.settings
    from datetime import datetime, timedelta

    wf = db.get_retirement_workflow(base_name)
    if not wf or not wf.get("step_approved_at"):
        return {"status": "error", "detail": "Item must be approved before starting retirement"}

    target_date = (datetime.now() + timedelta(days=body.target_days)).date()
    metrics = db.get_reporting_metrics(base_name) or {}

    wf_for_jira = {**wf, "jira_project": body.jira_project, "retirement_target_date": target_date}

    from rcars.services.jira import create_retirement_ticket
    jira_key = create_retirement_ticket(settings, wf_for_jira, metrics)

    fields = {
        "step_started_at": "NOW()",
        "step_started_by": user,
        "retirement_target_date": target_date.isoformat(),
        "jira_key": jira_key,
        "jira_project": body.jira_project,
        "status": "started",
    }
    result = db.upsert_retirement_workflow(base_name, fields)
    db.log_action(base_name, "retirement_started", user, f"Jira: {jira_key}, target: {target_date}")
    return {"status": "ok", "workflow": result, "jira_key": jira_key}


@router.put("/workflow/{base_name}/notes")
async def update_notes(base_name: str, body: NotesRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    fields = {"curator_notes": body.notes}
    result = db.upsert_retirement_workflow(base_name, fields)
    return {"status": "ok", "workflow": result}


@router.delete("/workflow/{base_name}")
async def cancel_workflow(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    deleted = db.delete_retirement_workflow(base_name)
    if deleted:
        db.log_action(base_name, "retirement_cancelled", user, "Workflow cancelled")
    return {"status": "ok", "deleted": deleted}
```

- [ ] **Step 4: Add `workflow_status` query param to retirement dashboard**

In the existing `retirement_dashboard` function in `analysis.py`, add the parameter and pass it through:

Add to function signature:
```python
    workflow_status: str | None = Query(None),
```

Pass to the DB query:
```python
    items = db.list_reporting_metrics(
        sort_by="retirement_score", sort_dir="desc",
        workflow_status=workflow_status,
    )
```

- [ ] **Step 5: Run existing tests to check for regressions**

Run: `cd src/api && python -m pytest tests/test_reporting.py tests/test_retirement_workflow.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/api/routes/analysis.py \
        src/api/rcars/db/database.py
git commit -m "[RHDPCD-27] Add workflow API endpoints and dashboard enrichment"
```

---

### Task 4: Frontend — API Client + Drawer + Inline Badge + Filter

**Files:**
- Modify: `src/frontend/src/services/api.ts` — add workflow API methods + types
- Modify: `src/frontend/src/pages/RetirementPage.tsx` — drawer, badge, filter

**Interfaces:**
- Consumes: API endpoints from Task 3
- Produces: Complete retirement workflow UI

- [ ] **Step 1: Add TypeScript types and API methods**

In `src/frontend/src/services/api.ts`, add the workflow interface (after `ReportingMetricsItem`):

```typescript
export interface RetirementWorkflow {
  catalog_base_name: string
  status: string
  step_reviewed_at: string | null
  step_reviewed_by: string | null
  step_approved_at: string | null
  step_approved_by: string | null
  approval_reason: string | null
  approval_snapshot: Record<string, number | string> | null
  step_notified_at: string | null
  step_notified_by: string | null
  step_started_at: string | null
  step_started_by: string | null
  retirement_target_date: string | null
  step_retired_at: string | null
  replacement_ci: string | null
  replacement_name: string | null
  curator_notes: string | null
  jira_key: string | null
  jira_project: string
  created_at: string
  updated_at: string
}
```

Add `workflow_status` fields to `ReportingMetricsItem`:
```typescript
  workflow_status?: string | null
  jira_key?: string | null
  retirement_target_date?: string | null
```

Add `workflow_status` to the dashboard params type and the API methods:

```typescript
  getRetirementWorkflow: (baseName: string) =>
    request<{ workflow: RetirementWorkflow | null }>(`/analysis/retirement/workflow/${encodeURIComponent(baseName)}`),

  reviewRetirementItem: (baseName: string) =>
    request<{ status: string; workflow: RetirementWorkflow }>(`/analysis/retirement/workflow/${encodeURIComponent(baseName)}/review`, { method: 'PUT' }),

  approveRetirementItem: (baseName: string, reason: string, replacementCi?: string, replacementName?: string) =>
    request<{ status: string; workflow: RetirementWorkflow }>(`/analysis/retirement/workflow/${encodeURIComponent(baseName)}/approve`, {
      method: 'PUT',
      body: JSON.stringify({ reason, replacement_ci: replacementCi || null, replacement_name: replacementName || null }),
    }),

  notifyRetirementOwner: (baseName: string) =>
    request<{ status: string; workflow: RetirementWorkflow }>(`/analysis/retirement/workflow/${encodeURIComponent(baseName)}/notify`, { method: 'PUT' }),

  startRetirement: (baseName: string, targetDays?: number, jiraProject?: string) =>
    request<{ status: string; workflow: RetirementWorkflow; jira_key: string }>(`/analysis/retirement/workflow/${encodeURIComponent(baseName)}/start`, {
      method: 'PUT',
      body: JSON.stringify({ target_days: targetDays ?? 30, jira_project: jiraProject ?? 'RHDPCD' }),
    }),

  updateRetirementNotes: (baseName: string, notes: string) =>
    request<{ status: string; workflow: RetirementWorkflow }>(`/analysis/retirement/workflow/${encodeURIComponent(baseName)}/notes`, {
      method: 'PUT',
      body: JSON.stringify({ notes }),
    }),

  cancelRetirementWorkflow: (baseName: string) =>
    request<{ status: string; deleted: boolean }>(`/analysis/retirement/workflow/${encodeURIComponent(baseName)}`, { method: 'DELETE' }),
```

- [ ] **Step 2: Add inline "Retirement In Process" badge to RetirementPage.tsx**

In the table row rendering (around line 241 in the display name cell), add the badge after the name:

```tsx
{item.workflow_status && item.workflow_status !== 'retired' && (
  <span className="ca-badge ca-badge--process" style={{
    fontSize: '9px', padding: '1px 6px', marginLeft: '8px',
    background: 'var(--pf-t--global--color--status--info--default)',
    color: '#fff', borderRadius: '3px', whiteSpace: 'nowrap',
  }}>Retirement In Process</span>
)}
```

- [ ] **Step 3: Add workflow status filter**

Add state for the workflow filter (near the other filter state):

```typescript
type WorkflowFilter = 'all' | 'none' | 'in_process' | 'started' | 'retired'
const [workflowFilter, setWorkflowFilter] = useState<WorkflowFilter>('all')
```

Add the filter buttons in the UI (after the score filter section):

```tsx
<div className="ca-controls" style={{ margin: 0, padding: 0 }}>
  {([['all', 'All'], ['none', 'No Action'], ['in_process', 'In Process'], ['started', 'Started'], ['retired', 'Retired']] as [WorkflowFilter, string][]).map(([f, label]) => (
    <button key={f} onClick={() => setWorkflowFilter(f)}
      className={`ca-filter-btn${workflowFilter === f ? ' active' : ''}`}
      style={{ fontSize: '11px', padding: '3px 8px' }}>
      {label}
    </button>
  ))}
</div>
```

Pass the filter to the API call in `loadData`:

```typescript
workflow_status: workflowFilter !== 'all' ? workflowFilter : undefined,
```

Add `workflowFilter` to the `useEffect` dependency array alongside `window` and `tab`.

- [ ] **Step 4: Add the slide-out drawer component**

Add the drawer component to `RetirementPage.tsx`. This follows the BrowsePage drawer pattern. Add state:

```typescript
const [drawerItem, setDrawerItem] = useState<string | null>(null)
const [drawerWorkflow, setDrawerWorkflow] = useState<RetirementWorkflow | null>(null)
const [approvalReason, setApprovalReason] = useState('')
const [replacementCi, setReplacementCi] = useState('')
const [replacementName, setReplacementName] = useState('')
const [notesText, setNotesText] = useState('')
const [targetDays, setTargetDays] = useState(30)
const [jiraProject, setJiraProject] = useState('RHDPCD')
const [drawerLoading, setDrawerLoading] = useState(false)
```

Add drawer open handler (loads workflow state):

```typescript
const openDrawer = async (baseName: string) => {
  setDrawerItem(baseName)
  setDrawerLoading(true)
  try {
    const { workflow } = await api.getRetirementWorkflow(baseName)
    setDrawerWorkflow(workflow)
    setApprovalReason(workflow?.approval_reason || '')
    setReplacementCi(workflow?.replacement_ci || '')
    setReplacementName(workflow?.replacement_name || '')
    setNotesText(workflow?.curator_notes || '')
    setTargetDays(30)
    setJiraProject(workflow?.jira_project || 'RHDPCD')
  } catch { setDrawerWorkflow(null) }
  setDrawerLoading(false)
}
```

Add step action handlers (review, approve, notify, start, cancel, save notes) that call the API and refresh the drawer workflow state.

Add the drawer JSX at the end of the component (before the closing fragment), with:
- Overlay div for click-to-close
- Drawer panel with header (item name + close button)
- Top section: item context metrics from the current row
- Middle section: workflow checklist with step checkboxes, approval reason textarea, replacement fields, start retirement button with target days and project inputs
- Bottom section: curator notes textarea with auto-save, Jira link

Wire the row click handler to open the drawer instead of (or in addition to) expanding the row.

- [ ] **Step 5: Test the UI manually**

Start the dev server: `./dev-services.sh start` from the repo root.
Open http://localhost:3000, navigate to Content Analysis → Retirement.
Verify:
- Status filter buttons appear and filter items
- Clicking an item opens the drawer
- Workflow checklist shows correct state
- Review/Approve/Notify/Start actions work
- "Retirement In Process" badge appears on items with active workflows
- Curator notes save on blur
- Jira link appears after starting retirement (if Jira credentials configured)

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/services/api.ts \
        src/frontend/src/pages/RetirementPage.tsx
git commit -m "[RHDPCD-27] Add retirement workflow UI: drawer, badges, and status filter"
```
