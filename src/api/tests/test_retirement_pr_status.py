"""Retirement PR reconciliation against real workflow persistence."""

import os
import asyncio
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
def db():
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
        conn.execute("DELETE FROM content_entities WHERE content_id = %s", (CONTENT_ID,))
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
    ctx = {"worker_ctx": SimpleNamespace(db=db, settings=Settings(database_url=TEST_DB_URL))}
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
        result = asyncio.run(run_retirement_sweep({"worker_ctx": SimpleNamespace(db=db, settings=Settings(database_url=TEST_DB_URL))}))
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
    result = asyncio.run(run_retirement_sweep({"worker_ctx": SimpleNamespace(db=db, settings=Settings(database_url=TEST_DB_URL))}))
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
    ctx = {"worker_ctx": SimpleNamespace(db=db, settings=Settings(database_url=TEST_DB_URL))}

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
    ctx = {"worker_ctx": SimpleNamespace(db=db, settings=Settings(database_url=TEST_DB_URL))}

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
    ctx = {"worker_ctx": SimpleNamespace(db=db, settings=Settings(database_url=TEST_DB_URL))}

    result = await run_retirement_sweep(ctx)

    assert result["retirements_completed"] == 0
    assert db.get_retirement_workflow(CONTENT_ID)["status"] == "started"


@pytest.mark.asyncio
async def test_sweep_reconciles_merged_revert_without_new_prs_due(db, monkeypatch):
    db.upsert_retirement_workflow(CONTENT_ID, {"agv_revert_pr_url": REVERT_URL})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(
        return_value={"state": "closed", "merged": True},
    ))
    ctx = {"worker_ctx": SimpleNamespace(db=db, settings=Settings(database_url=TEST_DB_URL))}

    result = await run_retirement_sweep(ctx)

    assert result["reverts_completed"] == 1
    assert db.get_retirement_workflow(CONTENT_ID) is None
