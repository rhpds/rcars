import pytest
from unittest.mock import MagicMock
from starlette.testclient import TestClient
from rcars.web.app import app, get_db
from rcars.config import Settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RCARS_DEV_USER", "test@redhat.com")
    # Ensure no database URL is set, so lifespan won't try to connect
    monkeypatch.delenv("RCARS_DATABASE_URL", raising=False)
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_advisor_page_loads(client):
    response = client.get("/advisor")
    assert response.status_code == 200
    assert "RCARS" in response.text


def test_is_curator_matches_email(monkeypatch):
    monkeypatch.setenv("RCARS_CURATOR_EMAILS", "alice@redhat.com,bob@redhat.com")
    s = Settings()
    assert s.is_curator("alice@redhat.com") is True
    assert s.is_curator("ALICE@REDHAT.COM") is True  # case-insensitive
    assert s.is_curator("charlie@redhat.com") is False


def test_curator_empty_by_default(monkeypatch):
    monkeypatch.delenv("RCARS_CURATOR_EMAILS", raising=False)
    s = Settings()
    assert s.is_curator("anyone@redhat.com") is False
