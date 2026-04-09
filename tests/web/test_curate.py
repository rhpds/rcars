import pytest
from unittest.mock import MagicMock
from starlette.testclient import TestClient
from rcars.web.app import app, get_db


@pytest.fixture
def curator_client(monkeypatch):
    monkeypatch.setenv("RCARS_DEV_USER", "curator@redhat.com")
    monkeypatch.setenv("RCARS_CURATOR_EMAILS", "curator@redhat.com")
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    mock_db.list_catalog_items.return_value = [
        {"ci_name": "test.lab.prod", "display_name": "Test Lab", "is_prod": True},
    ]
    mock_db.get_enrichment_tags.return_value = [{"tag_value": "booth demo", "tag_type": "label"}]
    mock_db.get_enrichment_note.return_value = None
    mock_db.get_enrichment_tags_for_items.return_value = {
        "test.lab.prod": [{"tag_value": "booth demo", "tag_type": "label"}]
    }
    mock_db.get_showroom_analysis.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db
    # Also override the route-level get_db
    from rcars.web.routes.curate import _get_db_dependency as curate_get_db
    app.dependency_overrides[curate_get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c, mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(monkeypatch):
    monkeypatch.setenv("RCARS_DEV_USER", "user@redhat.com")
    monkeypatch.delenv("RCARS_CURATOR_EMAILS", raising=False)
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    app.dependency_overrides[get_db] = lambda: mock_db
    from rcars.web.routes.curate import _get_db_dependency as curate_get_db
    app.dependency_overrides[curate_get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_curate_page_loads_for_curator(curator_client):
    client, _ = curator_client
    response = client.get("/curate")
    assert response.status_code == 200
    assert "Enrichment" in response.text or "Curate" in response.text


def test_curate_page_403_for_non_curator(anon_client):
    response = anon_client.get("/curate")
    assert response.status_code == 403


def test_curate_add_tag(curator_client):
    client, mock_db = curator_client
    response = client.post("/curate/tag", data={
        "ci_name": "test.lab.prod",
        "tag_type": "label",
        "tag_value": "new tag",
    })
    assert response.status_code == 200
    mock_db.add_enrichment_tag.assert_called_once_with(
        "test.lab.prod", "label", "new tag", "curator@redhat.com"
    )


def test_curate_remove_tag(curator_client):
    client, mock_db = curator_client
    response = client.request("DELETE", "/curate/tag", params={
        "ci_name": "test.lab.prod",
        "tag_type": "label",
        "tag_value": "booth demo",
    })
    assert response.status_code == 200
    mock_db.remove_enrichment_tag.assert_called_once()


def test_curate_set_note(curator_client):
    client, mock_db = curator_client
    response = client.post("/curate/note", data={
        "ci_name": "test.lab.prod",
        "note": "Great for post-Summit use",
    })
    assert response.status_code == 200
    mock_db.set_enrichment_note.assert_called_once_with(
        "test.lab.prod", "Great for post-Summit use", "curator@redhat.com"
    )


def test_curate_flag(curator_client):
    client, mock_db = curator_client
    response = client.post("/curate/flag", data={
        "ci_name": "test.lab.prod",
        "needed": "true",
    })
    assert response.status_code == 200
    mock_db.set_enrichment_review_needed.assert_called_once_with("test.lab.prod", True)
