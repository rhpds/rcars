"""Durable, deduplicated Jira lifecycle comments using real local persistence."""

import os
import asyncio
import json
from io import BytesIO
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlparse
from urllib.error import HTTPError

import pytest

from rcars.db.database import Database
from rcars.services import jira, retirement_jira_events

BASE = "test-jira-events.lifecycle"
CID = f"babylon:{BASE}.prod"
NOTICE = "https://github.com/rhpds/agnosticv/pull/101"
REMOVAL = "https://github.com/rhpds/agnosticv/pull/102"
TEST_DB_URL = os.environ.get("RCARS_TEST_DATABASE_URL", "postgresql://rcars:dev@localhost:5432/rcars_test")


@pytest.fixture
def db():
    assert "test" in urlparse(TEST_DB_URL).path, "Lifecycle tests require a test database"
    database = Database(TEST_DB_URL)
    database.create_schema()
    database.delete_retirement_workflow(CID)
    database.upsert_babylon_catalog_item({"ci_name": f"{BASE}.prod", "stage": "prod"})
    database.upsert_retirement_workflow(CID, {"step_started_at": "NOW()", "jira_key": "EXAMPLE-1"})
    yield database
    with database.pool.connection() as conn:
        if conn.execute("SELECT to_regclass('retirement_jira_events') AS name").fetchone()["name"]:
            conn.execute("DELETE FROM retirement_jira_events WHERE content_id = %s", (CID,))
        conn.execute("DELETE FROM content_entities WHERE content_id = %s", (CID,))
        conn.execute("DELETE FROM analysis_log WHERE ci_name = %s", (BASE,))
        conn.commit()
    database.close()


def event_time(db):
    wf = db.get_retirement_workflow(CID)
    return wf.get("jira_event_tracking_started_at", datetime.now(timezone.utc)) + timedelta(seconds=5)


def test_database_open_event_is_atomic_and_deduplicated(db):
    pr = {"pr_url": NOTICE, "created_at": event_time(db).isoformat()}
    db.record_retirement_pr(CID, "agv_notice_pr_url", pr)
    db.record_retirement_pr(CID, "agv_notice_pr_url", pr)
    events = db.list_pending_retirement_jira_events(content_id=CID)
    assert db.get_retirement_workflow(CID)["agv_notice_pr_url"] == NOTICE
    assert len(events) == 1
    assert events[0]["event_type"] == "notice_pr_opened"
    assert events[0]["jira_key"] == "EXAMPLE-1"
    assert NOTICE in events[0]["message"] and "opened" in events[0]["message"]


def test_database_no_jira_and_deleted_workflow_do_not_queue(db):
    db.upsert_retirement_workflow(CID, {"jira_key": None})
    db.record_retirement_pr(CID, "agv_notice_pr_url", {"pr_url": NOTICE, "created_at": event_time(db)})
    assert db.list_pending_retirement_jira_events(content_id=CID) == []
    db.delete_retirement_workflow(CID)
    assert db.record_retirement_pr(CID, "agv_retire_pr_url", {"pr_url": REMOVAL, "created_at": datetime.now(timezone.utc)}) is None
    assert db.get_retirement_workflow(CID) is None


def test_database_cancellation_event_survives_deletion_and_new_incarnation(db):
    assert db.finalize_retirement_cancellation(CID) is True
    assert db.get_retirement_workflow(CID) is None
    first = db.list_pending_retirement_jira_events(content_id=CID)
    assert len(first) == 1 and first[0]["event_type"] == "workflow_cancelled"
    db.update_retirement_jira_event(first[0]["event_key"], error="Jira comment delivery failed; retry pending")
    db.upsert_retirement_workflow(CID, {"step_started_at": "NOW()", "jira_key": "EXAMPLE-2"})
    assert db.finalize_retirement_cancellation(CID) is True
    events = db.list_pending_retirement_jira_events(content_id=CID)
    assert len(events) == 2
    assert events[0]["event_key"] != events[1]["event_key"]
    assert [event["jira_key"] for event in events] == ["EXAMPLE-1", "EXAMPLE-2"]
    assert events[0]["last_error"]


def test_database_jira_closure_queues_completion_once(db):
    db.auto_close_retired_workflows({CID})
    db.record_retirement_jira_closure(CID, cancelled=False)
    db.record_retirement_jira_closure(CID, cancelled=False)
    events = db.list_pending_retirement_jira_events(content_id=CID)
    assert len(events) == 1 and events[0]["event_type"] == "workflow_completed"
    assert db.get_retirement_workflow(CID)["jira_closed_at"] is not None
    db.update_retirement_jira_event(events[0]["event_key"], comment_id="12345")
    assert db.list_pending_retirement_jira_events(content_id=CID) == []


def test_database_cancellation_jira_closure_is_not_final_completion(db):
    db.record_retirement_jira_closure(CID, cancelled=True)
    assert db.list_pending_retirement_jira_events(content_id=CID) == []


def test_database_cancellation_intent_prevents_completed_event(db):
    db.auto_close_retired_workflows({CID})
    db.update_retirement_cleanup(CID, {"cancellation_requested_at": datetime.now(timezone.utc)})
    db.record_retirement_jira_closure(CID, cancelled=False)
    assert db.list_pending_retirement_jira_events(content_id=CID) == []


def test_database_local_outcome_uses_database_clock(db, monkeypatch):
    from rcars.db import database as database_module
    clock = Mock(wraps=datetime)
    clock.now.return_value = db.get_retirement_workflow(CID)["jira_event_tracking_started_at"] - timedelta(seconds=10)
    monkeypatch.setattr(database_module, "datetime", clock)
    db.finalize_retirement_cancellation(CID)
    events = db.list_pending_retirement_jira_events(content_id=CID)
    assert len(events) == 1 and events[0]["event_type"] == "workflow_cancelled"


def test_database_rollout_cutoff_and_repeat_closures(db):
    now = event_time(db)
    db.record_retirement_pr(CID, "agv_notice_pr_url", {"pr_url": NOTICE, "created_at": now - timedelta(days=1)})
    state = {"state": "closed", "merged": False, "closed_at": now - timedelta(days=1)}
    db.record_retirement_pr_state(CID, "agv_notice_pr_url", state)
    assert db.list_pending_retirement_jira_events(content_id=CID) == []
    state["closed_at"] = now
    db.record_retirement_pr_state(CID, "agv_notice_pr_url", state)
    db.record_retirement_pr_state(CID, "agv_notice_pr_url", state)
    db.record_retirement_pr_state(CID, "agv_notice_pr_url", {"state": "open", "merged": False})
    state["closed_at"] = now + timedelta(seconds=10)
    db.record_retirement_pr_state(CID, "agv_notice_pr_url", state)
    events = db.list_pending_retirement_jira_events(content_id=CID)
    assert [event["event_type"] for event in events] == ["notice_pr_closed", "notice_pr_closed"]
    assert events[0]["event_key"] != events[1]["event_key"]


def test_database_schema_setup_does_not_move_cutoff(db):
    before = db.get_retirement_workflow(CID).get("jira_event_tracking_started_at")
    assert before is not None
    db.create_schema()
    assert db.get_retirement_workflow(CID)["jira_event_tracking_started_at"] == before


def test_database_explicit_test_schema_reset_includes_delivery_queue():
    assert "test" in urlparse(TEST_DB_URL).path
    database = Database(TEST_DB_URL)
    database.create_schema()
    database.upsert_babylon_catalog_item({"ci_name": f"{BASE}.prod", "stage": "prod"})
    database.upsert_retirement_workflow(CID, {"jira_key": "EXAMPLE-1"})
    database.finalize_retirement_cancellation(CID)
    database.drop_schema()
    # drop_schema intentionally terminates the old pool's other connections.
    database.close()
    database = Database(TEST_DB_URL)
    try:
        with database.pool.connection() as conn:
            assert conn.execute("SELECT to_regclass('retirement_jira_events') AS name").fetchone()["name"] is None
    finally:
        database.create_schema()
        with database.pool.connection() as conn:
            conn.execute("DELETE FROM retirement_jira_events WHERE content_id = %s", (CID,))
            conn.commit()
        database.close()


def test_database_workflow_and_event_write_roll_back_together(db):
    # A database event write failure must not leave an untracked PR URL.
    with db.pool.connection() as conn:
        conn.execute("ALTER TABLE retirement_jira_events ADD CONSTRAINT test_reject_event CHECK (event_type <> 'notice_pr_opened')")
        conn.commit()
    try:
        with pytest.raises(Exception):
            db.record_retirement_pr(CID, "agv_notice_pr_url", {"pr_url": NOTICE, "created_at": event_time(db)})
        assert db.get_retirement_workflow(CID)["agv_notice_pr_url"] is None
    finally:
        with db.pool.connection() as conn:
            conn.execute("ALTER TABLE retirement_jira_events DROP CONSTRAINT test_reject_event")
            conn.commit()


@pytest.fixture
def settings():
    return SimpleNamespace(jira_api_email="test@example.com", jira_api_token="synthetic-token", github_app_id="123", github_app_private_key="synthetic-key", github_app_installation_id="456")


def test_comment_uses_adf_and_event_property(settings, monkeypatch):
    request = Mock(side_effect=[{"comments": [], "startAt": 0, "total": 0}, {"id": "123"}])
    monkeypatch.setattr(jira, "_jira_request", request)
    assert jira.ensure_issue_event_comment(settings, "EXAMPLE-1", "event-1", f"Notice PR opened.\n{NOTICE}") == "123"
    assert request.call_args.kwargs["body"] == {
        "body": {"type": "doc", "version": 1, "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Notice PR opened."}]},
            {"type": "paragraph", "content": [{"type": "text", "text": NOTICE, "marks": [{"type": "link", "attrs": {"href": NOTICE}}]}]},
        ]},
        "properties": [{"key": "rcars.retirement.event", "value": {"event_key": "event-1"}}],
    }


def test_comment_http_payload_accepts_object_marker_and_recovers_lost_response(settings, monkeypatch):
    """Exercise serialization: Jira rejects scalar entity properties (HTTP 400)."""
    settings.jira_base_url = "https://jira.example.com"
    remote = []
    posts = []

    def urlopen(request, **kwargs):
        if request.method == "GET":
            payload = {"comments": remote, "startAt": 0, "total": len(remote)}
            response = Mock(status=200)
            response.read.return_value = json.dumps(payload).encode()
            context = Mock()
            context.__enter__ = Mock(return_value=response)
            context.__exit__ = Mock(return_value=False)
            return context
        body = json.loads(request.data)
        posts.append(body)
        if not isinstance(body["properties"][0]["value"], dict):
            raise HTTPError(
                request.full_url, 400, "Bad Request", {},
                BytesIO(b'{"errorMessages":["Invalid entity property JSON"]}'),
            )
        remote.append({"id": "42", "properties": body["properties"]})
        raise TimeoutError("Response lost after Jira accepted the comment")

    monkeypatch.setattr(jira.urllib.request, "urlopen", urlopen)
    with pytest.raises(TimeoutError):
        jira.ensure_issue_event_comment(settings, "EXAMPLE-1", "event-1", "Notice PR opened.")
    assert jira.ensure_issue_event_comment(settings, "EXAMPLE-1", "event-1", "Notice PR opened.") == "42"
    assert len(posts) == 1
    assert posts[0]["properties"] == [{"key": "rcars.retirement.event", "value": {"event_key": "event-1"}}]


@pytest.mark.parametrize("property_value", [{"event_key": "event-1"}, "event-1"])
def test_comment_existing_event_on_later_page_prevents_post(settings, monkeypatch, property_value):
    paths = []
    def request(settings, path, method="POST", body=None):
        assert method == "GET", "Existing remote event must not be posted again"
        paths.append(path)
        if "startAt=0" in path:
            return {"comments": [{"id": "1", "properties": []}], "startAt": 0, "total": 2}
        return {"comments": [{"id": "2", "properties": [{"key": "rcars.retirement.event", "value": property_value}]}], "startAt": 1, "total": 2}
    monkeypatch.setattr(jira, "_jira_request", request)
    assert jira.ensure_issue_event_comment(settings, "EXAMPLE-1", "event-1", "message") == "2"
    assert len(paths) == 2 and "startAt=1" in paths[-1] and "expand=properties" in paths[0]


@pytest.mark.parametrize("page", [{}, {"comments": [], "total": None}, {"comments": [], "total": 1, "startAt": 0}, {"comments": ["bad"], "total": 1, "startAt": 0}])
def test_comment_malformed_page_does_not_prove_absence(settings, monkeypatch, page):
    def request(settings, path, method="POST", body=None):
        assert method == "GET", "Malformed lookup must never cause a POST"
        return page
    monkeypatch.setattr(jira, "_jira_request", request)
    with pytest.raises(RuntimeError):
        jira.ensure_issue_event_comment(settings, "EXAMPLE-1", "event-1", "message")


def test_comment_failed_lookup_does_not_post(settings, monkeypatch):
    monkeypatch.setattr(jira, "_jira_request", Mock(side_effect=RuntimeError("lookup failed")))
    with pytest.raises(RuntimeError):
        jira.ensure_issue_event_comment(settings, "EXAMPLE-1", "event-1", "message")


def test_comment_unknown_post_outcome_recovers_remote_event(settings, monkeypatch):
    remote = []
    posts = []
    def request(settings, path, method="POST", body=None):
        if method == "GET":
            return {"comments": remote, "startAt": 0, "total": len(remote)}
        posts.append(body)
        remote.append({"id": "42", "properties": body["properties"]})
        raise TimeoutError("Response lost after Jira accepted the comment")
    monkeypatch.setattr(jira, "_jira_request", request)
    with pytest.raises(TimeoutError):
        jira.ensure_issue_event_comment(settings, "EXAMPLE-1", "event-1", "message")
    assert jira.ensure_issue_event_comment(settings, "EXAMPLE-1", "event-1", "message") == "42"
    assert len(posts) == 1


@pytest.mark.parametrize("missing", ["jira_api_email", "jira_api_token"])
def test_comment_missing_credentials_does_not_call_http(settings, monkeypatch, missing):
    setattr(settings, missing, "")
    def unexpected(*args, **kwargs):
        pytest.fail("Unavailable Jira must not be invoked")
    monkeypatch.setattr(jira, "_jira_request", unexpected)
    with pytest.raises(RuntimeError):
        jira.ensure_issue_event_comment(settings, "EXAMPLE-1", "event-1", "message")


@pytest.mark.asyncio
async def test_delivery_retains_failed_events_without_overwriting_cleanup(db, settings, monkeypatch):
    db.record_retirement_pr(CID, "agv_notice_pr_url", {"pr_url": NOTICE, "created_at": event_time(db)})
    db.update_retirement_cleanup(CID, {"cleanup_error": "Required cleanup still pending"})
    monkeypatch.setattr(jira, "_jira_request", Mock(side_effect=RuntimeError("secret response body")))
    errors = await retirement_jira_events.deliver_pending_events(db, settings, content_id=CID)
    pending = db.list_pending_retirement_jira_events(content_id=CID)
    assert len(pending) == 1 and pending[0]["last_error"]
    assert errors and "secret response body" not in str(errors) + pending[0]["last_error"]
    assert db.get_retirement_workflow(CID)["cleanup_error"] == "Required cleanup still pending"


@pytest.mark.asyncio
async def test_delivery_survives_workflow_deletion_and_runs_off_loop(db, settings, monkeypatch):
    db.finalize_retirement_cancellation(CID)
    threads = []
    def request(settings, path, method="POST", body=None):
        with pytest.raises(RuntimeError):
            asyncio.get_running_loop()
        threads.append("worker thread")
        return {"comments": [], "startAt": 0, "total": 0} if method == "GET" else {"id": "123"}
    monkeypatch.setattr(jira, "_jira_request", request)
    assert await retirement_jira_events.deliver_pending_events(db, settings, content_id=CID) == []
    assert db.get_retirement_workflow(CID) is None
    assert db.list_pending_retirement_jira_events(content_id=CID) == []
    assert threads == ["worker thread", "worker thread"]
    assert await retirement_jira_events.deliver_pending_events(db, settings, content_id=CID) == []
    assert len(threads) == 2


@pytest.mark.asyncio
async def test_delivery_failure_defers_later_events_but_not_another_incarnation(db, settings, monkeypatch):
    db.record_retirement_pr(CID, "agv_notice_pr_url", {"pr_url": NOTICE, "created_at": event_time(db)})
    db.finalize_retirement_cancellation(CID)
    db.upsert_retirement_workflow(CID, {"jira_key": "EXAMPLE-2"})
    db.finalize_retirement_cancellation(CID)
    def request(settings, path, method="POST", body=None):
        if "EXAMPLE-1" in path:
            raise RuntimeError("First issue unavailable")
        return {"comments": [], "startAt": 0, "total": 0} if method == "GET" else {"id": "456"}
    monkeypatch.setattr(jira, "_jira_request", request)
    errors = await retirement_jira_events.deliver_pending_events(db, settings, content_id=CID)
    pending = db.list_pending_retirement_jira_events(content_id=CID)
    assert len(errors) == 1
    assert len(pending) == 2 and all(event["jira_key"] == "EXAMPLE-1" for event in pending)


@pytest.mark.asyncio
async def test_delivery_missing_credentials_retains_queue_without_http(db, settings, monkeypatch):
    db.finalize_retirement_cancellation(CID)
    settings.jira_api_token = ""
    def unexpected(*args, **kwargs):
        pytest.fail("No HTTP while Jira is unavailable")
    monkeypatch.setattr(jira, "_jira_request", unexpected)
    errors = await retirement_jira_events.deliver_pending_events(db, settings, content_id=CID)
    assert errors and "configured" in errors[0]
    assert len(db.list_pending_retirement_jira_events(content_id=CID)) == 1


@pytest.fixture
def comments(monkeypatch):
    recorder = SimpleNamespace(rows=[], fail=False)
    def request(settings, path, method="POST", body=None):
        assert "/comment" in path, "Lifecycle tests must not make other Jira requests"
        if recorder.fail:
            raise RuntimeError("Jira unavailable")
        if method == "GET":
            rows = [row for row in recorder.rows if row["issue"] in path]
            return {"comments": rows, "startAt": 0, "total": len(rows)}
        message = "\n".join("".join(node["text"] for node in paragraph["content"]) for paragraph in body["body"]["content"])
        row = {"id": str(len(recorder.rows) + 1), "issue": path.split("/")[-2], "message": message, "properties": body["properties"]}
        recorder.rows.append(row)
        return row
    monkeypatch.setattr(jira, "_jira_request", request)
    monkeypatch.setattr(jira, "get_issue_status", lambda *args: {"status": "Open", "resolution": None})
    monkeypatch.setattr(jira, "close_issue_done", lambda *args: True)
    monkeypatch.setattr(jira, "close_issue_wont_do", lambda *args: True)
    return recorder


@pytest.fixture
def client(db, settings, comments):
    from fastapi.testclient import TestClient
    from rcars.api.app import create_app
    from rcars.config import Settings
    app = create_app(Settings(database_url=TEST_DB_URL, dev_user="test@example.com", admin_emails_str="test@example.com", **vars(settings)))
    app.state.db = db
    return TestClient(app)


@pytest.mark.parametrize("action,helper,url,kind", [("agv-notice", "create_notice_pr", NOTICE, "Notice"), ("agv-retire", "create_retire_pr", REMOVAL, "Removal")])
def test_lifecycle_manual_pr_open_comments_once(client, db, comments, monkeypatch, action, helper, url, kind):
    from unittest.mock import AsyncMock
    from rcars.services import agv_access
    create = AsyncMock(return_value={"pr_url": url, "pr_number": 101, "repo": "rhpds/agnosticv", "created_at": event_time(db).isoformat()})
    monkeypatch.setattr(agv_access, helper, create)
    for _ in range(2):
        response = client.post(f"/api/v1/analysis/retirement/workflow/{BASE}/{action}")
        assert response.status_code == 200
        assert response.json().get("jira_comment_errors", []) == []
    assert create.await_count == 1
    assert len(comments.rows) == 1
    assert f"{kind} PR opened" in comments.rows[0]["message"] and url in comments.rows[0]["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["refresh", "sweep"])
@pytest.mark.parametrize("merged", [False, True])
async def test_lifecycle_notice_terminal_comments_once(client, db, settings, comments, monkeypatch, entry, merged):
    from unittest.mock import AsyncMock
    from rcars.services import agv_access
    from rcars.workers.ops import run_retirement_sweep
    db.upsert_retirement_workflow(CID, {"agv_notice_pr_url": NOTICE})
    at = event_time(db).isoformat()
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": merged, "closed_at": at, "merged_at": at if merged else None}))
    for _ in range(2):
        if entry == "refresh":
            assert client.post(f"/api/v1/analysis/retirement/workflow/{BASE}/check-prs").status_code == 200
        else:
            await run_retirement_sweep({"worker_ctx": SimpleNamespace(db=db, settings=settings)})
    assert len(comments.rows) == 1
    assert ("merged" if merged else "closed without merging") in comments.rows[0]["message"]
    assert db.get_retirement_workflow(CID)["step_retired_at"] is None


@pytest.mark.asyncio
async def test_lifecycle_automatic_removal_open_comment(db, settings, comments, monkeypatch):
    from datetime import date
    from unittest.mock import AsyncMock
    from rcars.services import agv_access
    from rcars.workers.ops import run_retirement_sweep
    db.upsert_retirement_workflow(CID, {"retirement_target_date": date.today() - timedelta(days=1)})
    monkeypatch.setattr(agv_access, "create_retire_pr", AsyncMock(return_value={"pr_url": REMOVAL, "created_at": event_time(db)}))
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "open", "merged": False}))
    result = await run_retirement_sweep({"worker_ctx": SimpleNamespace(db=db, settings=settings)})
    assert result["prs_opened"] == 1
    assert len(comments.rows) == 1 and "Removal PR opened" in comments.rows[0]["message"]


@pytest.mark.asyncio
async def test_lifecycle_completion_retry_comments_only_after_jira_cleanup(db, settings, comments, monkeypatch):
    from unittest.mock import AsyncMock
    from rcars.services import agv_access
    from rcars.workers.ops import run_retirement_sweep
    db.upsert_retirement_workflow(CID, {"agv_retire_pr_url": REMOVAL})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": True, "merged_at": event_time(db)}))
    monkeypatch.setattr(jira, "close_issue_done", Mock(side_effect=[False, True]))
    ctx = {"worker_ctx": SimpleNamespace(db=db, settings=settings)}
    await run_retirement_sweep(ctx)
    assert db.get_retirement_workflow(CID)["cleanup_error"]
    assert len(comments.rows) == 1 and "PR merged" in comments.rows[0]["message"]
    await run_retirement_sweep(ctx)
    await run_retirement_sweep(ctx)
    assert len(comments.rows) == 2 and "workflow completed" in comments.rows[1]["message"]
    assert not db.get_retirement_workflow(CID)["cleanup_error"]


def test_lifecycle_cancellation_closures_and_outcome_survive_comment_failure(client, db, settings, comments, monkeypatch):
    from rcars.services import agv_access
    from rcars.workers.ops import run_retirement_sweep
    db.upsert_retirement_workflow(CID, {"agv_notice_pr_url": NOTICE, "agv_retire_pr_url": REMOVAL})
    states = {101: {"state": "open", "merged": False}, 102: {"state": "open", "merged": False}}
    async def get_state(settings, repo, number):
        return dict(states[number])
    async def close(settings, repo, number):
        states[number] = {"state": "closed", "merged": False, "closed_at": event_time(db)}
        return dict(states[number])
    monkeypatch.setattr(agv_access, "get_pr_state", get_state)
    monkeypatch.setattr(agv_access, "close_pr", close)
    comments.fail = True
    response = client.delete(f"/api/v1/analysis/retirement/workflow/{BASE}")
    assert response.status_code == 200 and response.json()["deleted"] is True
    assert response.json().get("jira_comment_errors")
    assert db.get_retirement_workflow(CID) is None
    assert len(db.list_pending_retirement_jira_events(content_id=CID)) == 3
    comments.fail = False
    asyncio.run(run_retirement_sweep({"worker_ctx": SimpleNamespace(db=db, settings=settings)}))
    assert len(comments.rows) == 3 and "workflow cancelled" in comments.rows[-1]["message"]
    assert db.list_pending_retirement_jira_events(content_id=CID) == []


def test_lifecycle_comment_failure_does_not_repeat_pr_creation(client, db, comments, monkeypatch):
    from unittest.mock import AsyncMock
    from rcars.services import agv_access
    create = AsyncMock(return_value={"pr_url": NOTICE, "pr_number": 101, "repo": "rhpds/agnosticv", "created_at": event_time(db)})
    monkeypatch.setattr(agv_access, "create_notice_pr", create)
    comments.fail = True
    first = client.post(f"/api/v1/analysis/retirement/workflow/{BASE}/agv-notice")
    assert first.status_code == 200 and first.json().get("jira_comment_errors")
    assert db.get_retirement_workflow(CID)["cleanup_error"] is None
    comments.fail = False
    second = client.post(f"/api/v1/analysis/retirement/workflow/{BASE}/agv-notice")
    assert second.status_code == 200
    assert create.await_count == 1 and len(comments.rows) == 1


def test_lifecycle_cli_removal_queues_comment(db, settings, comments, monkeypatch):
    from datetime import date
    from unittest.mock import AsyncMock
    from rcars import cli as cli_module
    from rcars.services import agv_access
    db.upsert_retirement_workflow(CID, {"retirement_target_date": date.today() - timedelta(days=1)})
    settings.database_url = TEST_DB_URL
    monkeypatch.setattr(cli_module, "Settings", lambda: settings)
    monkeypatch.setattr(cli_module, "Database", lambda *args: Database(TEST_DB_URL))
    monkeypatch.setattr(agv_access, "create_retire_pr", AsyncMock(return_value={"pr_url": REMOVAL, "created_at": event_time(db)}))
    cli_module.retirement_sweep_cmd.callback()
    assert len(comments.rows) == 1 and "Removal PR opened" in comments.rows[0]["message"]


def test_database_first_second_event_and_missing_timestamps(db):
    cutoff = db.get_retirement_workflow(CID)["jira_event_tracking_started_at"]
    db.record_retirement_pr(CID, "agv_notice_pr_url", {"pr_url": NOTICE, "created_at": cutoff})
    db.record_retirement_pr_state(CID, "agv_notice_pr_url", {"state": "closed", "merged": False})
    events = db.list_pending_retirement_jira_events(content_id=CID)
    assert len(events) == 1 and events[0]["event_type"] == "notice_pr_opened"


@pytest.mark.asyncio
async def test_lifecycle_old_closed_workflows_do_not_backfill(db, settings, comments, monkeypatch):
    from unittest.mock import AsyncMock
    from rcars.services import agv_access
    from rcars.workers.ops import run_retirement_sweep
    old = db.get_retirement_workflow(CID)["jira_event_tracking_started_at"] - timedelta(days=1)
    db.upsert_retirement_workflow(CID, {"agv_notice_pr_url": NOTICE, "agv_retire_pr_url": REMOVAL, "step_retired_at": old})
    db.update_retirement_cleanup(CID, {"jira_closed_at": old})
    monkeypatch.setattr(agv_access, "get_pr_state", AsyncMock(return_value={"state": "closed", "merged": True, "merged_at": old, "closed_at": old}))
    await run_retirement_sweep({"worker_ctx": SimpleNamespace(db=db, settings=settings)})
    assert comments.rows == [] and db.list_pending_retirement_jira_events(content_id=CID) == []


@pytest.mark.asyncio
async def test_lifecycle_catalog_retirement_emits_completion_without_github(db, settings, comments, monkeypatch):
    from rcars.services import agv_access
    from rcars.workers.ops import run_retirement_sweep
    db.auto_close_retired_workflows({CID})
    settings.github_app_id = ""
    async def unexpected(*args):
        pytest.fail("Recorded catalog retirement needs no GitHub lookup")
    monkeypatch.setattr(agv_access, "get_pr_state", unexpected)
    ctx = {"worker_ctx": SimpleNamespace(db=db, settings=settings)}
    await run_retirement_sweep(ctx)
    await run_retirement_sweep(ctx)
    assert len(comments.rows) == 1 and "workflow completed" in comments.rows[0]["message"]


@pytest.mark.asyncio
async def test_delivery_concurrent_senders_cannot_overtake_stream(db, settings, comments, monkeypatch):
    import threading
    db.record_retirement_pr(CID, "agv_notice_pr_url", {"pr_url": NOTICE, "created_at": event_time(db)})
    db.finalize_retirement_cancellation(CID)
    original_request = jira._jira_request
    entered, release = threading.Event(), threading.Event()
    def blocked_request(*args, **kwargs):
        if not entered.is_set():
            entered.set()
            assert release.wait(5), "Timed out waiting for concurrent delivery probe"
        return original_request(*args, **kwargs)
    monkeypatch.setattr(jira, "_jira_request", blocked_request)
    first = asyncio.create_task(retirement_jira_events.deliver_pending_events(db, settings, content_id=CID))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        assert await retirement_jira_events.deliver_pending_events(db, settings, content_id=CID) == []
        assert comments.rows == []
    finally:
        release.set()
        await first
    assert len(comments.rows) == 2
    assert "PR opened" in comments.rows[0]["message"] and "workflow cancelled" in comments.rows[1]["message"]
