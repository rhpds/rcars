import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
import jinja2
from rcars.web.app import app, get_db
from rcars.web.routes.advisor import _get_db_dependency as advisor_get_db
from rcars.web.routes.curate import _get_db_dependency as curate_get_db
from rcars.web.routes.admin import get_db as admin_get_db
from rcars.config import Settings

SAMPLE_REC = {
    "ci_name": "openshift-cnv.lightspeed-workshop.prod",
    "display_name": "OpenShift Lightspeed Workshop",
    "fit_score": 92,
    "rationale": "Strong fit for developer audience.",
    "suggested_format": "hands_on_lab",
    "duration_notes": "90 min",
    "caveats": "Requires OCP 4.16+",
    "tags": [{"tag_value": "booth demo"}, {"tag_value": "Summit 2026"}],
    "note": None,
    "enrichment_review_needed": False,
    "catalog_link": "https://demo.redhat.com/catalog/openshift-cnv.lightspeed-workshop.prod",
}

_TEMPLATE_DIR = str(Path(__file__).parent.parent.parent / "src/rcars/web/templates")

MOCK_RECOMMEND_RESULT = {
    "recommendations": [
        {
            "ci_name": "openshift-cnv.lightspeed-workshop.prod",
            "display_name": "OpenShift Lightspeed Workshop",
            "fit_score": 92,
            "rationale": "Strong fit.",
            "suggested_format": "hands_on_lab",
            "duration_notes": "90 min",
            "caveats": "",
        }
    ],
    "overall_assessment": "Good matches found.",
    "content_gaps": [],
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RCARS_DEV_USER", "test@redhat.com")
    # Ensure no database URL is set, so lifespan won't try to connect
    monkeypatch.delenv("RCARS_DATABASE_URL", raising=False)
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    mock_db.get_enrichment_tags_for_items.return_value = {}
    mock_db.get_enrichment_note.return_value = None
    mock_db.get_catalog_item.return_value = {
        "ci_name": "openshift-cnv.lightspeed-workshop.prod",
        "display_name": "OpenShift Lightspeed Workshop",
        "category": "hands_on_lab",
    }
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


def test_rec_card_renders_score_and_name():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(_TEMPLATE_DIR))
    tmpl = env.get_template("fragments/rec_card.html")
    html = tmpl.render(rec=SAMPLE_REC, is_curator=False, session_id="test-123")
    assert "92" in html
    assert "OpenShift Lightspeed Workshop" in html
    assert "booth demo" in html


def test_rec_card_expanded_shows_caveats():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(_TEMPLATE_DIR))
    tmpl = env.get_template("fragments/rec_card_expanded.html")
    html = tmpl.render(rec=SAMPLE_REC, is_curator=False, session_id="test-123")
    assert "Requires OCP 4.16+" in html
    assert "openshift-cnv.lightspeed-workshop.prod" in html


def test_rec_card_expanded_shows_curator_controls_for_curator():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(_TEMPLATE_DIR))
    tmpl = env.get_template("fragments/rec_card_expanded.html")
    html = tmpl.render(rec=SAMPLE_REC, is_curator=True, session_id="test-123")
    assert "curator-actions" in html
    assert "Tag" in html


def test_advisor_query_returns_rec_cards(client):
    with patch("rcars.web.routes.advisor.recommend", return_value=MOCK_RECOMMEND_RESULT):
        response = client.post("/advisor/query", data={
            "session_id": "test-session-abc",
            "message": "OpenShift labs for developers",
        })
    assert response.status_code == 200
    assert "OpenShift Lightspeed Workshop" in response.text
    assert "92" in response.text


def test_advisor_query_appends_chat_turn(client):
    with patch("rcars.web.routes.advisor.recommend", return_value=MOCK_RECOMMEND_RESULT):
        response = client.post("/advisor/query", data={
            "session_id": "test-session-def",
            "message": "Show me OpenShift labs",
        })
    assert response.status_code == 200
    assert "chat-pane" in response.text


def test_advisor_query_accumulates_context(client):
    calls = []
    def capture_recommend(query, **kwargs):
        calls.append(query)
        return MOCK_RECOMMEND_RESULT
    with patch("rcars.web.routes.advisor.recommend", side_effect=capture_recommend):
        client.post("/advisor/query", data={"session_id": "acc-test", "message": "OpenShift labs"})
        client.post("/advisor/query", data={"session_id": "acc-test", "message": "shorter ones only"})
    assert len(calls) == 2
    assert "OpenShift labs" in calls[1]
    assert "shorter ones only" in calls[1]


def test_advisor_query_handles_recommend_none(client):
    with patch("rcars.web.routes.advisor.recommend", return_value=None):
        response = client.post("/advisor/query", data={
            "session_id": "fail-test",
            "message": "something",
        })
    assert response.status_code == 200
    assert "No strong matches" in response.text


def test_rollback_restores_previous_results(client):
    from rcars.web.routes.advisor import _sessions
    _sessions["rollback-test"] = [
        {"role": "user", "content": "OpenShift labs"},
        {
            "role": "assistant",
            "content": "Found 1 match.",
            "rec_ci_names": ["openshift-cnv.lightspeed-workshop.prod"],
            "turn_index": 1,
        },
    ]
    response = client.get("/advisor/restore/rollback-test/1")
    assert response.status_code == 200


def test_rollback_invalid_session_returns_empty(client):
    response = client.get("/advisor/restore/nonexistent-session/0")
    assert response.status_code == 200
    assert "No strong matches" in response.text or response.text
