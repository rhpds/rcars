"""Retirement PR reconciliation against real workflow persistence."""

import os
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings
from rcars.db.database import Database
from rcars.services import agv_access
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
def client(db):
    app = create_app(Settings(
        database_url=TEST_DB_URL, dev_user="admin@example.com",
        admin_emails_str="admin@example.com",
    ))
    app.state.db = db
    return TestClient(app)


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
