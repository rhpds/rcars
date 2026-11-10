"""Editing active retirement workflows (target date + replacement CI)."""

import os
from datetime import date, timedelta
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings
from rcars.db.database import Database
from rcars.services import jira

BASE_NAME = "test-retirement.edit"
CONTENT_ID = f"babylon:{BASE_NAME}.prod"
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
        "step_approved_at": "NOW()",
        "step_started_at": "NOW()",
        "jira_key": "RHDPCD-4242",
        "retirement_target_date": date.today() + timedelta(days=5),
        "replacement_ci": "old-replacement",
        "replacement_name": "Old Replacement",
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


@pytest.fixture
def non_admin_client(db, monkeypatch):
    monkeypatch.setattr(jira, "get_issue_status", lambda *args: {"status": "Open", "resolution": None})
    app = create_app(Settings(
        database_url=TEST_DB_URL, dev_user="user@example.com",
        admin_emails_str="admin@example.com",
    ))
    app.state.db = db
    return TestClient(app)


def _jira_event_messages(db):
    with db.pool.connection() as conn:
        rows = conn.execute(
            "SELECT message, comment_id FROM retirement_jira_events WHERE content_id = %s",
            (CONTENT_ID,),
        ).fetchall()
    return [dict(r) for r in rows]


def test_edit_moves_target_date(client, db):
    new_date = date.today() + timedelta(days=12)

    response = client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/edit",
                          json={"retirement_target_date": new_date.isoformat()})

    assert response.status_code == 200
    wf = db.get_retirement_workflow(CONTENT_ID)
    assert wf["retirement_target_date"] == new_date
    # The change is recorded as a durable Jira event and delivered immediately.
    events = _jira_event_messages(db)
    assert len(events) == 1
    assert str(new_date) in events[0]["message"]
    assert "target date" in events[0]["message"].lower()
    assert events[0]["comment_id"] == "synthetic-comment"


def test_edit_changes_replacement_ci(client, db):
    response = client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/edit",
                          json={"replacement_ci": "new-replacement", "replacement_name": "New Replacement"})

    assert response.status_code == 200
    wf = db.get_retirement_workflow(CONTENT_ID)
    assert wf["replacement_ci"] == "new-replacement"
    assert wf["replacement_name"] == "New Replacement"
    events = _jira_event_messages(db)
    assert len(events) == 1
    assert "replacement" in events[0]["message"].lower()
    assert "new-replacement" in events[0]["message"]


def test_edit_without_jira_key_records_no_event(client, db):
    db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": None})
    response = client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/edit",
                          json={"retirement_target_date": (date.today() + timedelta(days=1)).isoformat()})
    assert response.status_code == 200
    assert _jira_event_messages(db) == []


def test_edit_rejected_for_retired_item(client, db):
    db.upsert_retirement_workflow(CONTENT_ID, {"step_retired_at": "NOW()"})
    response = client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/edit",
                          json={"retirement_target_date": (date.today() + timedelta(days=1)).isoformat()})
    assert response.status_code == 409
    assert "retired" in response.json()["detail"].lower()


def test_edit_rejected_while_cancellation_pending(client, db):
    db.upsert_retirement_workflow(CONTENT_ID, {"cancellation_requested_at": "NOW()"})
    response = client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/edit",
                          json={"retirement_target_date": (date.today() + timedelta(days=1)).isoformat()})
    assert response.status_code == 409
    assert "cancellation" in response.json()["detail"].lower()


def test_edit_requires_admin(non_admin_client, db):
    response = non_admin_client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/edit",
                                    json={"retirement_target_date": (date.today() + timedelta(days=1)).isoformat()})
    assert response.status_code == 403
    assert _jira_event_messages(db) == []


def test_edit_without_fields_is_rejected(client, db):
    response = client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/edit", json={})
    assert response.status_code == 400


def test_edit_unknown_base_name_returns_404(client, db):
    response = client.put("/api/v1/analysis/retirement/workflow/does-not.exist/edit",
                          json={"retirement_target_date": "2026-11-22"})
    assert response.status_code == 404


def test_edit_without_change_records_no_event(client, db):
    current = db.get_retirement_workflow(CONTENT_ID)
    response = client.put(f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/edit",
                          json={"retirement_target_date": current["retirement_target_date"].isoformat(),
                                "replacement_ci": current["replacement_ci"]})
    assert response.status_code == 200
    assert _jira_event_messages(db) == []
