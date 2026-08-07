"""Tests for POST /advisor/chat endpoint."""
import pytest
from fastapi.testclient import TestClient
from rcars.api.app import create_app
from rcars.config import Settings
from rcars.db import Database


@pytest.fixture
def client():
    settings = Settings(
        database_url="postgresql://rcars:dev@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="test@redhat.com",
        admin_emails_str="test@redhat.com",
        curator_emails_str="test@redhat.com",
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def non_admin_client():
    settings = Settings(
        database_url="postgresql://rcars:dev@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="user@redhat.com",
        admin_emails_str="",
        curator_emails_str="",
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def test_chat_new_session_generates_id(client):
    resp = client.post("/api/v1/advisor/chat", json={"message": "find ansible content"})
    assert resp.status_code == 200
    body = resp.json()
    assert "job_id" in body
    assert "session_id" in body
    assert len(body["session_id"]) > 0


def test_chat_append_checks_ownership(non_admin_client):
    # Create a session owned by another user
    from rcars.db import chat_sessions
    db = non_admin_client.app.state.db
    chat_sessions.log_chat_turn(db.pool, session_id="other-sess", turn_index=0,
                                user_email="someoneelse@x.com", query_text="q", results=None,
                                overall_assessment=None, intent="recommend",
                                envelope=None, scope=None)
    resp = non_admin_client.post("/api/v1/advisor/chat",
                                 json={"message": "more", "session_id": "other-sess"})
    assert resp.status_code == 404


def test_chat_message_length_capped(client):
    resp = client.post("/api/v1/advisor/chat", json={"message": "x" * 2001})
    assert resp.status_code == 422
