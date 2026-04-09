import pytest
from unittest.mock import MagicMock
from starlette.testclient import TestClient
from rcars.web.app import app, get_db
from rcars.web.routes.advisor import _get_db_dependency as advisor_get_db
from rcars.web.routes.curate import get_db as curate_get_db
from rcars.web.routes.admin import get_db as admin_get_db
from rcars.config import Settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RCARS_DEV_USER", "test@redhat.com")
    # Ensure no database URL is set, so lifespan won't try to connect
    monkeypatch.delenv("RCARS_DATABASE_URL", raising=False)
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    # Override all get_db dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[advisor_get_db] = lambda: mock_db
    app.dependency_overrides[curate_get_db] = lambda: mock_db
    app.dependency_overrides[admin_get_db] = lambda: mock_db
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


def test_advisor_has_logo(client):
    response = client.get("/advisor")
    assert response.status_code == 200
    assert "RCARS" in response.text
    assert "RHDP CONTENT ADVISOR" in response.text


def test_advisor_has_nav(client):
    response = client.get("/advisor")
    assert "/advisor" in response.text
    assert "Advisor" in response.text


def test_advisor_loads_htmx(client):
    response = client.get("/advisor")
    assert "htmx" in response.text.lower()


def test_advisor_loads_alpinejs(client):
    response = client.get("/advisor")
    assert "alpinejs" in response.text.lower() or "alpine" in response.text.lower()
