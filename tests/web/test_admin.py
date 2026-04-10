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
    with patch("rcars.web.routes.admin.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        response = client.post("/admin/refresh")
    assert response.status_code == 200
    mock_thread.return_value.start.assert_called_once()


def test_sync_catalog_returns_running_fragment(admin_client):
    """POST /admin/refresh returns immediately with HTMX polling markup."""
    client, mock_db = admin_client
    with patch("rcars.web.routes.admin.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        response = client.post("/admin/refresh")
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "/admin/refresh/status" in response.text
    assert "Syncing" in response.text


def test_sync_catalog_status_idle(admin_client):
    """GET /admin/refresh/status while idle returns empty div."""
    client, mock_db = admin_client
    import rcars.web.routes.admin as admin_mod
    admin_mod._refresh_status = {"running": False, "result": None, "color": None}
    response = client.get("/admin/refresh/status")
    assert response.status_code == 200
    assert "refresh-section" in response.text
    assert "every 2s" not in response.text


def test_sync_catalog_status_running(admin_client):
    """GET /admin/refresh/status while running returns polling fragment."""
    client, mock_db = admin_client
    import rcars.web.routes.admin as admin_mod
    admin_mod._refresh_status = {"running": True, "result": None, "color": None}
    response = client.get("/admin/refresh/status")
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "Syncing" in response.text
    admin_mod._refresh_status = {"running": False, "result": None, "color": None}


def test_sync_catalog_status_done(admin_client):
    """GET /admin/refresh/status when done returns result + OOB table."""
    client, mock_db = admin_client
    mock_db.get_status_summary.return_value = {
        "total": 350, "prod": 250, "with_showroom": 130, "analyzed": 125, "stale": 0,
    }
    import rcars.web.routes.admin as admin_mod
    admin_mod._refresh_status = {
        "running": False,
        "result": "Catalog sync complete.",
        "color": "var(--score-green)",
    }
    response = client.get("/admin/refresh/status")
    assert response.status_code == 200
    assert "Catalog sync complete." in response.text
    assert "catalog-status-table" in response.text
    assert "hx-swap-oob" in response.text
    assert "350" in response.text
    # State should be reset after serving
    assert admin_mod._refresh_status["result"] is None


def test_analyze_returns_running_fragment(admin_client):
    """POST /admin/rescan returns immediately with HTMX polling markup."""
    client, mock_db = admin_client
    with patch("rcars.web.routes.admin.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        response = client.post("/admin/rescan")
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "/admin/rescan/status" in response.text
    assert "Analysis" in response.text


def test_analyze_status_idle(admin_client):
    """GET /admin/rescan/status while idle returns idle section."""
    client, mock_db = admin_client
    import rcars.web.routes.admin as admin_mod
    admin_mod._rescan_status = {"running": False, "lines": [], "exit_ok": None}
    response = client.get("/admin/rescan/status")
    assert response.status_code == 200
    assert "every 2s" not in response.text
    assert "rescan-section" in response.text


def test_analyze_status_running_shows_lines(admin_client):
    """GET /admin/rescan/status while running shows log lines."""
    client, mock_db = admin_client
    import rcars.web.routes.admin as admin_mod
    admin_mod._rescan_status = {
        "running": True,
        "lines": ["Cloning lb1024...", "Analyzing content..."],
        "exit_ok": None,
    }
    response = client.get("/admin/rescan/status")
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "Cloning lb1024" in response.text
    admin_mod._rescan_status = {"running": False, "lines": [], "exit_ok": None}


def test_analyze_status_done_success(admin_client):
    """GET /admin/rescan/status when done shows result + OOB table."""
    client, mock_db = admin_client
    mock_db.get_status_summary.return_value = {
        "total": 342, "prod": 248, "with_showroom": 126, "analyzed": 126, "stale": 0,
    }
    import rcars.web.routes.admin as admin_mod
    admin_mod._rescan_status = {
        "running": False,
        "lines": ["Done."],
        "exit_ok": True,
    }
    response = client.get("/admin/rescan/status")
    assert response.status_code == 200
    assert "Analysis complete" in response.text
    assert "catalog-status-table" in response.text
    assert "hx-swap-oob" in response.text
    assert admin_mod._rescan_status["exit_ok"] is None


def test_analyze_status_done_failure(admin_client):
    """GET /admin/rescan/status when done with failure shows error."""
    client, mock_db = admin_client
    mock_db.get_status_summary.return_value = {
        "total": 342, "prod": 248, "with_showroom": 126, "analyzed": 120, "stale": 6,
    }
    import rcars.web.routes.admin as admin_mod
    admin_mod._rescan_status = {
        "running": False,
        "lines": ["Error: something failed"],
        "exit_ok": False,
    }
    response = client.get("/admin/rescan/status")
    assert response.status_code == 200
    assert "failed" in response.text.lower()
    assert admin_mod._rescan_status["exit_ok"] is None
