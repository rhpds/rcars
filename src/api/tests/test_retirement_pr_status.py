"""Retirement PR reconciliation against real workflow persistence."""

import os
import asyncio
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings
from rcars.db.database import Database
from rcars.services import agv_access, jira
from rcars.workers.ops import run_retirement_sweep

BASE_NAME = "test-retirement.pr-status"
CONTENT_ID = f"babylon:{BASE_NAME}.prod"
REMOVAL_URL = "https://github.com/rhpds/agnosticv/pull/42"
REVERT_URL = "https://github.com/rhpds/agnosticv/pull/43"
TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL", "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db(monkeypatch):
    # All integration side effects in these persistence tests remain synthetic.
    monkeypatch.setattr(jira, "ensure_issue_event_comment", lambda *args: "synthetic-comment")
    if "test" not in urlparse(TEST_DB_URL).path:
        raise RuntimeError("Retirement tests require a test database")
    database = Database(TEST_DB_URL)
    database.create_schema()
    database.delete_retirement_workflow(CONTENT_ID)
    database.upsert_babylon_catalog_item({"ci_name": f"{BASE_NAME}.prod", "stage": "prod"})
    database.upsert_retirement_workflow(CONTENT_ID, {
        "step_started_at": "NOW()",
        "retirement_target_date": date.today() + timedelta(days=30),
        "agv_retire_pr_url": REMOVAL_URL,
    })
    yield database
    with database.pool.connection() as conn:
        conn.execute("DELETE FROM retirement_jira_events WHERE content_id = %s", (CONTENT_ID,))
        conn.execute("DELETE FROM content_entities WHERE content_id = ANY(%s)",
                     ([f"babylon:{BASE_NAME}.{stage}" for stage in ("prod", "dev", "event")],))
        conn.execute("DELETE FROM analysis_log WHERE ci_name = %s", (BASE_NAME,))
        conn.commit()
    database.close()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(jira, "get_issue_status", lambda *args: {"status": "Open", "resolution": None})
    app = create_app(Settings(
        database_url=TEST_DB_URL, dev_user="admin@example.com",
        admin_emails_str="admin@example.com",
    ))
    app.state.db = db
    return TestClient(app)


def _sweep_context(db, **credentials):
    """Keep credential-dependent sweeps deterministic and external calls mocked."""
    configured = {
        "github_app_id": "12345",
        "github_app_private_key": "synthetic-key",
        "github_app_installation_id": "99999",
        "jira_api_email": "admin@example.com",
        "jira_api_token": "synthetic-token",
    }
    configured.update(credentials)
    return {"worker_ctx": SimpleNamespace(db=db, settings=Settings(
        database_url=TEST_DB_URL, **configured,
    ))}


@pytest.mark.parametrize("action,helper", [("agv-notice", "create_notice_pr"), ("agv-retire", "create_retire_pr")])
@pytest.mark.parametrize("retirement", ["workflow", "catalog", "catalog_no_workflow", "catalog_dev_sibling", "catalog_event_sibling"])
def test_retired_items_cannot_create_prs(client, db, monkeypatch, action, helper, retirement):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "jira_key": "EXAMPLE-1", "agv_retire_pr_url": None,
        **({"step_retired_at": "NOW()"} if retirement == "workflow" else {}),
    })
    if retirement.startswith("catalog"):
        if retirement.endswith("_sibling"):
            stage = retirement.split("_")[1]
            db.upsert_babylon_catalog_item({"ci_name": f"{BASE_NAME}.{stage}", "stage": stage})
        if retirement == "catalog_no_workflow":
            db.delete_retirement_workflow(CONTENT_ID)
        with db.pool.connection() as conn:
            conn.execute("UPDATE content_entities SET retired_at = NOW() WHERE content_id = %s", (CONTENT_ID,))
            conn.commit()
    create_pr = AsyncMock(return_value={"pr_url": REMOVAL_URL, "pr_number": 42, "repo": "rhpds/agnosticv"})
    monkeypatch.setattr(agv_access, helper, create_pr)

    response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/{action}")

    assert response.status_code == 409
    assert "retired" in response.json()["detail"].lower()
    create_pr.assert_not_called()
    wf = db.get_retirement_workflow(CONTENT_ID)
    if retirement == "catalog_no_workflow":
        assert wf is None
    else:
        assert wf["agv_notice_pr_url"] is None
        assert wf["agv_retire_pr_url"] is None


@pytest.mark.parametrize("retirement", ["workflow", "workflow_status", "catalog", "catalog_no_workflow", "catalog_dev_sibling", "catalog_event_sibling"])
def test_retired_items_cannot_be_cancelled(client, db, monkeypatch, retirement):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "jira_key": "EXAMPLE-1",
        **({"step_retired_at": "NOW()"} if retirement == "workflow" else {}),
    })
    if retirement == "workflow_status":
        with db.pool.connection() as conn:
            conn.execute("UPDATE retirement_workflow SET status = 'retired' WHERE content_id = %s", (CONTENT_ID,))
            conn.commit()
    if retirement.startswith("catalog"):
        if retirement.endswith("_sibling"):
            stage = retirement.split("_")[1]
            db.upsert_babylon_catalog_item({"ci_name": f"{BASE_NAME}.{stage}", "stage": stage})
        if retirement == "catalog_no_workflow":
            db.delete_retirement_workflow(CONTENT_ID)
        with db.pool.connection() as conn:
            conn.execute("UPDATE content_entities SET retired_at = NOW() WHERE content_id = %s", (CONTENT_ID,))
            conn.commit()
    before = db.get_retirement_workflow(CONTENT_ID)
    external_calls = []
    async def state(*args):
        external_calls.append("github")
        return {"state": "closed", "merged": False}
    def close_jira(*args):
        external_calls.append("jira")
        return True
    monkeypatch.setattr(agv_access, "get_pr_state", state)
    monkeypatch.setattr(jira, "close_issue_wont_do", close_jira)

    response = client.delete(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}")

    assert response.status_code == 409
    assert "retired" in response.json()["detail"].lower()
    assert db.get_retirement_workflow(CONTENT_ID) == before
    assert external_calls == []


@pytest.mark.parametrize("retirement", ["workflow", "catalog"])
def test_cancellation_does_not_mark_concurrently_retired_item(client, db, monkeypatch, retirement):
    original_get_entity = db.get_content_entity
    completed = []
    def get_entity(content_id):
        entity = original_get_entity(content_id)
        if not completed:
            if retirement == "workflow":
                db.upsert_retirement_workflow(content_id, {"step_retired_at": "NOW()"})
            else:
                with db.pool.connection() as conn:
                    conn.execute("UPDATE content_entities SET retired_at = NOW() WHERE content_id = %s", (content_id,))
                    conn.commit()
            completed.append(db.get_retirement_workflow(content_id))
        return entity
    monkeypatch.setattr(db, "get_content_entity", get_entity)

    response = client.delete(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}")

    assert response.status_code == 409
    assert db.get_retirement_workflow(CONTENT_ID) == completed[0]
    assert db.get_retirement_workflow(CONTENT_ID)["cancellation_requested_at"] is None


@pytest.mark.parametrize("failure", ["notice_lookup", "notice_close", "removal_lookup", "removal_close", "revert"])
def test_cancel_preserves_tracking_on_github_failure(client, db, monkeypatch, failure):
    notice_url = "https://github.com/rhpds/agnosticv/pull/41"
    db.upsert_retirement_workflow(CONTENT_ID, {"agv_notice_pr_url": notice_url, "jira_key": "EXAMPLE-1"})
    async def state(settings, repo, number):
        if failure == ("notice_lookup" if number == 41 else "removal_lookup"):
            raise RuntimeError("GitHub unavailable")
        return {"state": "closed" if failure == "revert" else "open", "merged": failure == "revert"}
    async def close(settings, repo, number):
        if failure == ("notice_close" if number == 41 else "removal_close"):
            raise RuntimeError("GitHub unavailable")
    monkeypatch.setattr(agv_access, "get_pr_state", state)
    monkeypatch.setattr(agv_access, "close_pr", close)
    monkeypatch.setattr(agv_access, "revert_notice_pr", AsyncMock(side_effect=RuntimeError("GitHub unavailable")))
    def unexpected_jira_close(*args):
        pytest.fail("Jira must not be closed before GitHub cleanup succeeds")
    monkeypatch.setattr(jira, "close_issue_wont_do", unexpected_jira_close)

    response = client.delete(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}")

    assert response.status_code == 502
    persisted = db.get_retirement_workflow(CONTENT_ID)
    assert persisted["agv_notice_pr_url"] == notice_url
    assert persisted["agv_retire_pr_url"] == REMOVAL_URL


def test_cancel_stops_removal_before_creating_revert(client, db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"agv_notice_pr_url": "https://github.com/rhpds/agnosticv/pull/41"})
    events = []
    async def state(settings, repo, number):
        return {"state": "closed" if number == 41 else "open", "merged": number == 41}
    async def close(*args):
        events.append("close removal")
    async def revert(*args):
        events.append("create revert")
        return {"pr_url": REVERT_URL}
    monkeypatch.setattr(agv_access, "get_pr_state", state)
    monkeypatch.setattr(agv_access, "close_pr", close)
    monkeypatch.setattr(agv_access, "revert_notice_pr", revert)

    response = client.delete(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}")

    assert response.status_code == 200
    assert events == ["close removal", "create revert"]
    assert db.get_retirement_workflow(CONTENT_ID)["agv_revert_pr_url"] == REVERT_URL


def test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(client, db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "agv_notice_pr_url": "https://github.com/rhpds/agnosticv/pull/41", "jira_key": "EXAMPLE-1",
    })
    async def state(settings, repo, number):
        return {"state": "closed", "merged": number == 41}
    def close_jira(*args):
        assert db.get_retirement_workflow(CONTENT_ID)["agv_revert_pr_url"] == REVERT_URL
        # The sweep reconciles the revert merge while the external Jira call runs.
        db.delete_retirement_workflow(CONTENT_ID)
        return True
    monkeypatch.setattr(agv_access, "get_pr_state", state)
    monkeypatch.setattr(agv_access, "revert_notice_pr", AsyncMock(return_value={"pr_url": REVERT_URL}))
    monkeypatch.setattr(jira, "close_issue_wont_do", close_jira)

    response = client.delete(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}")

    assert db.get_retirement_workflow(CONTENT_ID) is None
    assert response.status_code == 200
    assert response.json()["deleted"] is True


@pytest.mark.parametrize("outcome", [True, None])
def test_cancel_audit_reports_jira_outcome(client, db, monkeypatch, outcome):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1" if outcome is not None else None})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": False}))
    def close(*args):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    monkeypatch.setattr(jira, "close_issue_wont_do", close)

    response = client.delete(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}")

    assert response.status_code == 200
    assert db.get_retirement_workflow(CONTENT_ID) is None
    with db.pool.connection() as conn:
        details = conn.execute("SELECT details FROM analysis_log WHERE ci_name = %s AND action = 'retirement_cancelled' ORDER BY id DESC LIMIT 1", (BASE_NAME,)).fetchone()["details"]
    expected = "failed" if isinstance(outcome, Exception) else "closed" if outcome else "skipped" if outcome is False else "not linked"
    assert f"Jira: {expected}" in details


@pytest.mark.parametrize("outcome", [False, RuntimeError("Jira unavailable")])
def test_required_cancel_retains_workflow_on_jira_failure(client, db, monkeypatch, outcome):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1"})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": False}))
    def close(*args):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    monkeypatch.setattr(jira, "close_issue_wont_do", close)
    response = client.delete(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}")
    assert response.status_code == 502
    wf = db.get_retirement_workflow(CONTENT_ID)
    assert wf["cancellation_requested_at"] is not None
    assert wf["cleanup_error"]
    assert wf["jira_closed_at"] is None


def test_required_cancel_jira_runs_off_event_loop(client, db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1"})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": False}))
    seen = []
    def close(*args):
        try:
            asyncio.get_running_loop()
            seen.append("blocked loop")
        except RuntimeError:
            seen.append("worker thread")
        return True
    monkeypatch.setattr(jira, "close_issue_wont_do", close)
    assert client.delete(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}").status_code == 200
    assert seen == ["worker thread"]


@pytest.mark.asyncio
async def test_required_success_retries_jira_after_retirement_without_pr(db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1", "step_retired_at": "NOW()", "agv_retire_pr_url": None})
    outcomes = [False, True]
    events = []
    def close(*args):
        events.append("Done")
        return outcomes.pop(0)
    monkeypatch.setattr(jira, "close_issue_done", close)
    ctx = _sweep_context(db)
    first = await run_retirement_sweep(ctx)
    assert first["errors"]
    wf = db.get_retirement_workflow(CONTENT_ID)
    retired_at = wf["step_retired_at"]
    assert wf["cleanup_error"] and wf["jira_closed_at"] is None
    await run_retirement_sweep(ctx)
    wf = db.get_retirement_workflow(CONTENT_ID)
    assert wf["jira_closed_at"] and wf["cleanup_error"] is None
    assert wf["step_retired_at"] == retired_at
    await run_retirement_sweep(ctx)
    assert events == ["Done", "Done"]


@pytest.mark.parametrize("entry", ["refresh", "sweep"])
def test_required_merged_revert_cannot_bypass_jira_failure(client, db, monkeypatch, entry):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1", "agv_revert_pr_url": REVERT_URL})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": True}))
    monkeypatch.setattr(jira, "close_issue_wont_do", lambda *args: False)
    if entry == "refresh":
        response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/check-prs")
        assert response.json()["deleted"] is False
        assert response.json()["cleanup_error"]
    else:
        result = asyncio.run(run_retirement_sweep(_sweep_context(db)))
        assert result["reverts_completed"] == 0
        assert result["errors"]
    assert db.get_retirement_workflow(CONTENT_ID) is not None


def test_required_failed_cancel_is_excluded_from_removal_and_retried_by_sweep(client, db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "jira_key": "EXAMPLE-1", "agv_retire_pr_url": None,
        "retirement_target_date": date.today() - timedelta(days=1),
    })
    monkeypatch.setattr(jira, "close_issue_wont_do", lambda *args: False)
    assert client.delete(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}").status_code == 502
    assert not db.list_retirement_ready_for_removal()
    assert db.auto_close_retired_workflows({CONTENT_ID}) == 0
    async def no_removal(*args):
        pytest.fail("Cancelled workflows must not produce new removal PRs")
    monkeypatch.setattr(agv_access, "create_retire_pr", no_removal)
    monkeypatch.setattr(jira, "close_issue_wont_do", lambda *args: True)
    result = asyncio.run(run_retirement_sweep(_sweep_context(db)))
    assert not result["errors"]
    assert db.get_retirement_workflow(CONTENT_ID) is None


def test_required_success_refresh_reports_and_retries_jira_error(client, db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1"})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": True}))
    monkeypatch.setattr(jira, "close_issue_done", lambda *args: False)
    first = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/check-prs").json()
    assert first["cleanup_error"]
    assert first["workflow"]["step_retired_at"]
    assert first["workflow"]["jira_closed_at"] is None
    monkeypatch.setattr(jira, "close_issue_done", lambda *args: True)
    second = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/check-prs").json()
    assert second["cleanup_error"] is None
    assert second["workflow"]["jira_closed_at"]
    assert second["workflow"]["step_retired_at"] == first["workflow"]["step_retired_at"]


def test_required_cleanup_migration_backfills_legacy_reverts_idempotently(db):
    db.upsert_retirement_workflow(CONTENT_ID, {"agv_revert_pr_url": REVERT_URL})
    db.create_schema()
    requested_at = db.get_retirement_workflow(CONTENT_ID)["cancellation_requested_at"]
    assert requested_at is not None
    db.create_schema()
    assert db.get_retirement_workflow(CONTENT_ID)["cancellation_requested_at"] == requested_at
    db.delete_retirement_workflow(CONTENT_ID)
    assert db.update_retirement_cleanup(CONTENT_ID, {"cleanup_error": "failed"}) is None
    assert db.get_retirement_workflow(CONTENT_ID) is None


def test_required_closed_unmerged_revert_is_not_cancellation_success(client, db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"agv_revert_pr_url": REVERT_URL})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": False}))
    result = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/check-prs").json()
    assert result["deleted"] is False
    assert "manual recovery" in result["cleanup_error"]
    assert db.get_retirement_workflow(CONTENT_ID) is not None


@pytest.mark.parametrize("action,helper", [("agv-notice", "create_notice_pr"), ("agv-retire", "create_retire_pr")])
def test_manual_pr_creation_respects_cleanup_lock(client, db, monkeypatch, action, helper):
    from rcars.services.retirement_cleanup import workflow_lock_id
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1", "agv_retire_pr_url": None})
    monkeypatch.setattr(agv_access, helper, AsyncMock(return_value={"pr_url": REMOVAL_URL, "pr_number": 42, "repo": "rhpds/agnosticv"}))
    with db.advisory_lock(workflow_lock_id(CONTENT_ID)) as acquired:
        assert acquired
        response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/{action}")
    assert response.status_code == 409
    assert db.get_retirement_workflow(CONTENT_ID)["agv_notice_pr_url"] is None
    assert db.get_retirement_workflow(CONTENT_ID)["agv_retire_pr_url"] is None


@pytest.mark.parametrize("action,helper", [("agv-notice", "create_notice_pr"), ("agv-retire", "create_retire_pr")])
def test_cancel_cannot_delete_tracking_during_manual_pr_creation(client, db, monkeypatch, action, helper):
    from rcars.services.retirement_cleanup import cancel_retirement, CleanupError
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1", "agv_retire_pr_url": None})
    monkeypatch.setattr(jira, "close_issue_wont_do", lambda *args: True)
    outcomes = []
    async def create(settings, *args):
        try:
            await cancel_retirement(db, settings, CONTENT_ID, "admin")
            outcomes.append("deleted")
        except CleanupError:
            outcomes.append("retained")
        return {"pr_url": REMOVAL_URL, "pr_number": 42, "repo": "rhpds/agnosticv"}
    monkeypatch.setattr(agv_access, helper, create)
    response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/{action}")
    assert response.status_code == 200
    assert outcomes == ["retained"]
    wf = db.get_retirement_workflow(CONTENT_ID)
    assert wf["jira_key"] == "EXAMPLE-1"
    assert wf["cancellation_requested_at"]


def test_refresh_completes_merged_removal_before_target_date(client, db, monkeypatch):
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(
        return_value={"state": "closed", "merged": True},
    ))

    response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/check-prs")

    assert response.status_code == 200
    result = response.json()
    assert result["workflow"]["status"] == "retired"
    assert result["workflow"]["step_retired_at"] is not None
    assert result["pr_statuses"]["agv_retire_pr_url"]["merged"] is True
    persisted = db.get_retirement_workflow(CONTENT_ID)
    assert persisted["status"] == "retired"
    # Workflow completion must not bypass Babylon's catalog refresh/soft-delete.
    assert db.get_babylon_item_by_ci_name(f"{BASE_NAME}.prod")["retired_at"] is None


@pytest.mark.parametrize("state", [
    {"state": "open", "merged": False},
    {"state": "closed", "merged": False},
    RuntimeError("GitHub unavailable"),
])
def test_refresh_does_not_retire_unmerged_or_unknown_pr(client, db, monkeypatch, state):
    lookup = AsyncMock(side_effect=state) if isinstance(state, Exception) else AsyncMock(return_value=state)
    monkeypatch.setattr(agv_access, "get_pr_state", lookup)

    response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/check-prs")

    assert response.status_code == 200
    assert response.json()["workflow"]["status"] == "started"
    assert db.get_retirement_workflow(CONTENT_ID)["step_retired_at"] is None


def test_refresh_preserves_existing_retirement_timestamp(client, db, monkeypatch):
    retired_at = datetime(2026, 10, 1, tzinfo=timezone.utc)
    db.upsert_retirement_workflow(CONTENT_ID, {"step_retired_at": retired_at})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(
        return_value={"state": "closed", "merged": True},
    ))

    response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/check-prs")

    assert response.status_code == 200
    assert db.get_retirement_workflow(CONTENT_ID)["step_retired_at"] == retired_at


def test_refresh_merged_notice_does_not_complete_open_removal(client, db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "agv_notice_pr_url": "https://github.com/rhpds/agnosticv/pull/41",
    })

    async def get_state(settings, repo_full, pr_number):
        assert repo_full == "rhpds/agnosticv"
        return {
            41: {"state": "closed", "merged": True},
            42: {"state": "open", "merged": False},
        }[pr_number]

    monkeypatch.setattr(agv_access, "get_pr_state", get_state)

    response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/check-prs")

    assert response.status_code == 200
    assert response.json()["pr_statuses"]["agv_notice_pr_url"]["merged"] is True
    assert response.json()["workflow"]["status"] == "started"
    assert db.get_retirement_workflow(CONTENT_ID)["step_retired_at"] is None


def test_merged_revert_still_deletes_workflow(client, db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"agv_revert_pr_url": REVERT_URL})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(
        return_value={"state": "closed", "merged": True},
    ))

    response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/check-prs")

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert db.get_retirement_workflow(CONTENT_ID) is None


@pytest.mark.asyncio
async def test_sweep_reconciles_merged_removal_without_new_prs_due(db, monkeypatch):
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(
        return_value={"state": "closed", "merged": True},
    ))
    ctx = _sweep_context(db)

    result = await run_retirement_sweep(ctx)

    assert result["prs_opened"] == 0
    assert result["retirements_completed"] == 1
    assert db.get_retirement_workflow(CONTENT_ID)["status"] == "retired"
    retired_at = db.get_retirement_workflow(CONTENT_ID)["step_retired_at"]
    again = await run_retirement_sweep(ctx)
    assert again["retirements_completed"] == 0
    assert db.get_retirement_workflow(CONTENT_ID)["step_retired_at"] == retired_at


@pytest.mark.asyncio
@pytest.mark.parametrize("state", [
    {"state": "open", "merged": False},
    {"state": "closed", "merged": False},
    RuntimeError("GitHub unavailable"),
])
async def test_sweep_does_not_retire_unmerged_or_unknown_pr(db, monkeypatch, state):
    lookup = AsyncMock(side_effect=state) if isinstance(state, Exception) else AsyncMock(return_value=state)
    monkeypatch.setattr(agv_access, "get_pr_state", lookup)
    ctx = _sweep_context(db)

    result = await run_retirement_sweep(ctx)

    assert result["retirements_completed"] == 0
    assert db.get_retirement_workflow(CONTENT_ID)["step_retired_at"] is None
    if isinstance(state, Exception):
        assert any("GitHub unavailable" in error for error in result["errors"])


@pytest.mark.asyncio
async def test_sweep_does_not_retire_from_merged_notice_alone(db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "agv_notice_pr_url": "https://github.com/rhpds/agnosticv/pull/41",
        "agv_retire_pr_url": None,
    })
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(
        return_value={"state": "closed", "merged": True},
    ))
    ctx = _sweep_context(db)

    result = await run_retirement_sweep(ctx)

    assert result["retirements_completed"] == 0
    assert db.get_retirement_workflow(CONTENT_ID)["status"] == "started"


@pytest.mark.asyncio
async def test_sweep_reconciles_merged_revert_without_new_prs_due(db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"agv_revert_pr_url": REVERT_URL})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(
        return_value={"state": "closed", "merged": True},
    ))
    ctx = _sweep_context(db)

    result = await run_retirement_sweep(ctx)

    assert result["reverts_completed"] == 1
    assert db.get_retirement_workflow(CONTENT_ID) is None


@pytest.mark.asyncio
async def test_sweep_github_only_opens_due_removal(db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "jira_key": "EXAMPLE-1", "agv_retire_pr_url": None,
        "retirement_target_date": date.today() - timedelta(days=1),
    })
    monkeypatch.setattr(agv_access, "create_retire_pr", AsyncMock(return_value={"pr_url": REMOVAL_URL}))
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "open", "merged": False}))

    result = await run_retirement_sweep(_sweep_context(db, jira_api_email="", jira_api_token=""))

    assert result["prs_opened"] == 1
    assert result["errors"] == []
    assert db.get_retirement_workflow(CONTENT_ID)["agv_retire_pr_url"] == REMOVAL_URL


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["github_app_id", "github_app_private_key", "github_app_installation_id"])
async def test_sweep_partial_github_defers_removal_with_targeted_error(db, monkeypatch, missing):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "jira_key": "EXAMPLE-1", "agv_retire_pr_url": None,
        "retirement_target_date": date.today() - timedelta(days=1),
    })
    async def unexpected(*args):
        pytest.fail("Missing GitHub credentials must defer without calling GitHub")
    monkeypatch.setattr(agv_access, "create_retire_pr", unexpected)

    result = await run_retirement_sweep(_sweep_context(db, **{missing: ""}))

    wf = db.get_retirement_workflow(CONTENT_ID)
    assert result["prs_opened"] == 0
    assert any("GitHub" in error and "configured" in error for error in result["errors"])
    assert "GitHub" in wf["cleanup_error"]
    assert wf["agv_retire_pr_url"] is None
    assert wf["step_retired_at"] is None


@pytest.mark.asyncio
async def test_sweep_jira_only_defers_unknown_removal_state(db, monkeypatch):
    async def unexpected(*args):
        pytest.fail("Missing GitHub credentials must not trigger PR status lookups")
    monkeypatch.setattr(agv_access, "get_pr_state", unexpected)

    result = await run_retirement_sweep(_sweep_context(
        db, github_app_id="", github_app_private_key="", github_app_installation_id="",
    ))

    wf = db.get_retirement_workflow(CONTENT_ID)
    assert result["retirements_completed"] == 0
    assert any("GitHub" in error for error in result["errors"])
    assert "GitHub" in wf["cleanup_error"]
    assert wf["step_retired_at"] is None
    assert wf["agv_retire_pr_url"] == REMOVAL_URL


@pytest.mark.asyncio
async def test_sweep_restored_github_clears_configuration_error_for_open_removal(db, monkeypatch):
    await run_retirement_sweep(_sweep_context(db, github_app_private_key=""))
    assert "GitHub" in db.get_retirement_workflow(CONTENT_ID)["cleanup_error"]
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "open", "merged": False}))

    result = await run_retirement_sweep(_sweep_context(db))

    wf = db.get_retirement_workflow(CONTENT_ID)
    assert result["errors"] == []
    assert wf["cleanup_error"] is None
    assert wf["step_retired_at"] is None
    assert wf["agv_retire_pr_url"] == REMOVAL_URL


@pytest.mark.asyncio
async def test_sweep_successful_lookup_keeps_unrelated_cleanup_errors(db, monkeypatch):
    db.update_retirement_cleanup(CONTENT_ID, {"cleanup_error": "Jira retirement closure failed; retry required"})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "open", "merged": False}))

    await run_retirement_sweep(_sweep_context(db))

    assert db.get_retirement_workflow(CONTENT_ID)["cleanup_error"] == "Jira retirement closure failed; retry required"


@pytest.mark.asyncio
async def test_sweep_lock_loser_does_not_overwrite_concurrent_completion(db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1"})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": True}))
    @contextmanager
    def contended_lock(lock_id):
        # The lock owner finishes just before this sweep observes contention.
        db.auto_close_retired_workflows({CONTENT_ID})
        db.update_retirement_cleanup(CONTENT_ID, {
            "jira_closed_at": datetime.now(timezone.utc), "cleanup_error": None,
        })
        yield False
    monkeypatch.setattr(db, "advisory_lock", contended_lock)

    await run_retirement_sweep(_sweep_context(db))

    wf = db.get_retirement_workflow(CONTENT_ID)
    assert wf["status"] == "retired"
    assert wf["jira_closed_at"] is not None
    assert wf["cleanup_error"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["jira_api_email", "jira_api_token"])
async def test_sweep_partial_jira_records_retirement_and_retries_cleanup(db, monkeypatch, missing):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1"})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": True}))
    def unexpected(*args):
        pytest.fail("Missing Jira credentials must defer without calling Jira")
    monkeypatch.setattr(jira, "close_issue_done", unexpected)
    ctx = _sweep_context(db, **{missing: ""})

    result = await run_retirement_sweep(ctx)

    wf = db.get_retirement_workflow(CONTENT_ID)
    retired_at = wf["step_retired_at"]
    assert retired_at is not None
    assert wf["jira_closed_at"] is None
    assert "Jira" in wf["cleanup_error"] and "configured" in wf["cleanup_error"]
    assert any("Jira" in error and "configured" in error for error in result["errors"])

    monkeypatch.setattr(jira, "close_issue_done", lambda *args: True)
    ctx["worker_ctx"].settings = _sweep_context(db)["worker_ctx"].settings
    retried = await run_retirement_sweep(ctx)

    wf = db.get_retirement_workflow(CONTENT_ID)
    assert retried["errors"] == []
    assert retried["jira_closed"] == 1
    assert wf["jira_closed_at"] is not None
    assert wf["cleanup_error"] is None
    assert wf["step_retired_at"] == retired_at


@pytest.mark.asyncio
@pytest.mark.parametrize("closed", [False, True])
async def test_sweep_github_only_completes_when_no_jira_work_remains(db, monkeypatch, closed):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "jira_key": "EXAMPLE-1" if closed else None,
    })
    if closed:
        db.update_retirement_cleanup(CONTENT_ID, {"jira_closed_at": datetime.now(timezone.utc)})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": True}))
    def unexpected(*args):
        pytest.fail("No Jira closure should be attempted")
    monkeypatch.setattr(jira, "close_issue_done", unexpected)

    result = await run_retirement_sweep(_sweep_context(db, jira_api_email="", jira_api_token=""))

    assert result["errors"] == []
    assert result["retirements_completed"] == 1
    assert db.get_retirement_workflow(CONTENT_ID)["status"] == "retired"


@pytest.mark.asyncio
@pytest.mark.parametrize("closed", [False, True])
async def test_sweep_github_only_cancels_when_no_jira_work_remains(db, monkeypatch, closed):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1" if closed else None})
    fields = {"cancellation_requested_at": datetime.now(timezone.utc)}
    if closed:
        fields["jira_closed_at"] = datetime.now(timezone.utc)
    db.update_retirement_cleanup(CONTENT_ID, fields)
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": False}))
    def unexpected(*args):
        pytest.fail("No Jira closure should be attempted")
    monkeypatch.setattr(jira, "close_issue_wont_do", unexpected)

    result = await run_retirement_sweep(_sweep_context(db, jira_api_email="", jira_api_token=""))

    assert result["errors"] == []
    assert result["reverts_completed"] == 1
    assert db.get_retirement_workflow(CONTENT_ID) is None


@pytest.mark.asyncio
async def test_sweep_github_only_cancellation_preserves_revert_until_jira_available(db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {
        "jira_key": "EXAMPLE-1", "agv_notice_pr_url": "https://github.com/rhpds/agnosticv/pull/41",
    })
    db.update_retirement_cleanup(CONTENT_ID, {"cancellation_requested_at": datetime.now(timezone.utc)})
    events = []
    async def state(settings, repo, number):
        return {"state": "open" if number == 42 else "closed", "merged": number != 42}
    async def close(settings, repo, number):
        events.append((repo, number))
    monkeypatch.setattr(agv_access, "get_pr_state", state)
    monkeypatch.setattr(agv_access, "close_pr", close)
    monkeypatch.setattr(agv_access, "revert_notice_pr", AsyncMock(return_value={"pr_url": REVERT_URL}))
    def unexpected(*args):
        pytest.fail("Missing Jira credentials must not trigger Jira closure")
    monkeypatch.setattr(jira, "close_issue_wont_do", unexpected)

    result = await run_retirement_sweep(_sweep_context(db, jira_api_email="", jira_api_token=""))

    wf = db.get_retirement_workflow(CONTENT_ID)
    assert events == [("rhpds/agnosticv", 42)]
    assert wf["agv_revert_pr_url"] == REVERT_URL
    assert wf["jira_closed_at"] is None
    assert "Jira" in wf["cleanup_error"] and "configured" in wf["cleanup_error"]
    assert result["reverts_completed"] == 0
    assert any("Jira" in error for error in result["errors"])


@pytest.mark.asyncio
async def test_sweep_jira_only_preserves_cancellation_with_github_work(db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1"})
    db.update_retirement_cleanup(CONTENT_ID, {"cancellation_requested_at": datetime.now(timezone.utc)})
    async def unexpected_github(*args):
        pytest.fail("Missing GitHub credentials must not trigger cancellation PR cleanup")
    def unexpected_jira(*args):
        pytest.fail("Jira must not close before the required GitHub cleanup")
    monkeypatch.setattr(agv_access, "get_pr_state", unexpected_github)
    monkeypatch.setattr(jira, "close_issue_wont_do", unexpected_jira)

    result = await run_retirement_sweep(_sweep_context(
        db, github_app_id="", github_app_private_key="", github_app_installation_id="",
    ))

    wf = db.get_retirement_workflow(CONTENT_ID)
    assert result["reverts_completed"] == 0
    assert any("GitHub" in error for error in result["errors"])
    assert "GitHub" in wf["cleanup_error"]
    assert wf["jira_closed_at"] is None
    assert wf["agv_retire_pr_url"] == REMOVAL_URL


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["nightly", "queued"])
async def test_sweep_jira_only_entry_retries_recorded_retirement_without_github(db, monkeypatch, entry):
    from rcars.workers import ops

    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1", "step_retired_at": "NOW()"})
    ctx = _sweep_context(db, github_app_id="", github_app_private_key="", github_app_installation_id="")
    ctx["worker_ctx"].relay = SimpleNamespace(publish=AsyncMock())
    async def unexpected(*args):
        pytest.fail("Recorded retirements need no GitHub lookup")
    monkeypatch.setattr(agv_access, "get_pr_state", unexpected)
    monkeypatch.setattr(jira, "close_issue_done", lambda *args: True)
    monkeypatch.setattr(ops, "run_babylon_pipeline", AsyncMock(return_value={}))
    monkeypatch.setattr(ops, "run_osspa_pipeline", AsyncMock(return_value={}))
    job_id = db.create_job(job_type="retirement_sweep", queue="scan", created_by="test")
    try:
        if entry == "nightly":
            result = (await ops.run_nightly_pipeline(ctx, job_id))["retirement"]
        else:
            result = await ops.run_retirement_sweep_job(ctx, job_id)

        assert result["errors"] == []
        assert result["jira_closed"] == 1
        assert db.get_retirement_workflow(CONTENT_ID)["jira_closed_at"] is not None
    finally:
        with db.pool.connection() as conn:
            conn.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
            conn.commit()


def _approved_unstarted(db):
    db.delete_retirement_workflow(CONTENT_ID)
    db.upsert_retirement_workflow(CONTENT_ID, {"status": "approved", "step_approved_at": "NOW()"})


def test_start_retirement_respects_workflow_lock(client, db, monkeypatch):
    # A start already running in another API worker holds the lock: no second ticket.
    from rcars.services.retirement_cleanup import workflow_lock_id
    _approved_unstarted(db)
    created = []
    monkeypatch.setattr(jira, "create_retirement_ticket", lambda *args: created.append(1) or "EXAMPLE-2")
    with db.advisory_lock(workflow_lock_id(CONTENT_ID)) as acquired:
        assert acquired
        response = client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/start", json={})
    assert response.status_code == 409
    assert created == []
    assert db.get_retirement_workflow(CONTENT_ID)["step_started_at"] is None


def test_start_retirement_holds_lock_while_creating_ticket(client, db, monkeypatch):
    from rcars.services.retirement_cleanup import workflow_lock_id
    _approved_unstarted(db)
    other = Database(TEST_DB_URL)
    lock_free_during_create = []

    def fake_create(*args):
        with other.advisory_lock(workflow_lock_id(CONTENT_ID)) as got:
            lock_free_during_create.append(got)
        return "EXAMPLE-2"

    monkeypatch.setattr(jira, "create_retirement_ticket", fake_create)
    try:
        response = client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/start", json={})
    finally:
        other.close()
    assert response.status_code == 200
    assert lock_free_during_create == [False]
    assert db.get_retirement_workflow(CONTENT_ID)["jira_key"] == "EXAMPLE-2"
