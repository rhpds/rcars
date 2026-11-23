"""start_retirement must run its blocking Jira call off the event loop."""

import os
import threading
from datetime import date, timedelta
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings
from rcars.db.database import Database
from rcars.services import jira

BASE_NAME = "test-retirement.offloop"
CONTENT_ID = f"babylon:{BASE_NAME}.prod"
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
        "step_approved_at": "NOW()",
        "retirement_target_date": date.today() + timedelta(days=5),
    })
    yield database
    with database.pool.connection() as conn:
        conn.execute("DELETE FROM content_entities WHERE content_id = %s", (CONTENT_ID,))
        conn.execute("DELETE FROM analysis_log WHERE ci_name = %s", (BASE_NAME,))
        conn.commit()
    database.close()


def test_start_retirement_creates_ticket_off_event_loop(db, monkeypatch):
    """The Jira ticket call must not run on the thread that serves the event loop."""
    seen = {}

    def fake_create(settings, workflow, metrics):
        seen["thread"] = threading.current_thread()
        return "RHDPCD-4243"

    monkeypatch.setattr(jira, "create_retirement_ticket", fake_create)
    app = create_app(Settings(
        database_url=TEST_DB_URL, dev_user="admin@example.com",
        admin_emails_str="admin@example.com",
    ))
    app.state.db = db
    loop_threads = set()

    @app.middleware("http")
    async def record_loop_thread(request, call_next):
        loop_threads.add(threading.current_thread())
        return await call_next(request)

    resp = TestClient(app).put(
        f"/api/v1/analysis/retirement/workflow/{BASE_NAME}/start",
        json={"target_days": 30},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["jira_key"] == "RHDPCD-4243"
    assert loop_threads, "middleware never ran"
    assert seen["thread"] not in loop_threads
