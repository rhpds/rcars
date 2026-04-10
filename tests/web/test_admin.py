import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from rcars.web.app import app, get_db


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv("RCARS_DEV_USER", "admin@redhat.com")
    monkeypatch.setenv("RCARS_ADMIN_EMAILS", "admin@redhat.com")
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    mock_db.get_status_summary.return_value = {
        "total": 342, "prod": 248, "with_showroom": 126, "analyzed": 120, "stale": 6,
    }
    app.dependency_overrides[get_db] = lambda: mock_db
    # Override route-level dependency too
    from rcars.web.routes.admin import _get_db_dependency as admin_get_db
    app.dependency_overrides[admin_get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c, mock_db
    app.dependency_overrides.clear()


def test_admin_page_loads(admin_client):
    client, _ = admin_client
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Admin" in response.text or "admin" in response.text.lower()


def test_admin_shows_scan_status(admin_client):
    client, _ = admin_client
    response = client.get("/admin")
    assert response.status_code == 200
    assert "342" in response.text


def test_admin_shows_new_labels(admin_client):
    client, _ = admin_client
    response = client.get("/admin")
    assert "Catalog Sync" in response.text
    assert "Sync Catalog" in response.text
    assert "Showroom Analysis" in response.text
    assert "Analyze Showroom Content" in response.text
    assert "catalog-status-table" in response.text


def test_admin_rescan_triggers_background_job(admin_client):
    client, mock_db = admin_client
    with patch("rcars.web.routes.admin.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        response = client.post("/admin/rescan")
    assert response.status_code == 200
    mock_thread.return_value.start.assert_called_once()


def test_admin_refresh_triggers(admin_client):
    client, mock_db = admin_client
    with patch("rcars.web.routes.admin.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        response = client.post("/admin/refresh")
    assert response.status_code == 200
