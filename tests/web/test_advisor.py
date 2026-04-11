import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
import jinja2
from rcars.web.app import app, get_db
from rcars.web.routes.advisor import _get_db_dependency as advisor_get_db
from rcars.web.routes.curate import _get_db_dependency as curate_get_db
from rcars.web.routes.admin import _get_db_dependency as admin_get_db
from rcars.config import Settings

from rcars.recommender.models import Candidate, QueryState

SAMPLE_REC = {
    "ci_name": "openshift-cnv.lightspeed-workshop.prod",
    "display_name": "OpenShift Lightspeed Workshop",
    "fit_score": 92,
    "rationale": "Strong fit for developer audience.",
    "suggested_format": "hands_on_lab",
    "duration_notes": "90 min",
    "caveats": "Requires OCP 4.16+",
    "card_phase": "complete",
    "one_line_reason": "",
    "summary": "A workshop about OpenShift Lightspeed",
    "topics": ["openshift"],
    "difficulty": "beginner",
    "duration_min": 90,
    "content_type": "workshop",
    "tags": [{"tag_value": "booth demo"}, {"tag_value": "Summit 2026"}],
    "note": None,
    "enrichment_review_needed": False,
    "catalog_link": "https://demo.redhat.com/catalog/openshift-cnv.lightspeed-workshop.prod",
}

_TEMPLATE_DIR = str(Path(__file__).parent.parent.parent / "src/rcars/web/templates")


def _mock_run_query_generator(*args, **kwargs):
    """Mock run_query that yields VECTOR_DONE then COMPLETE."""
    c = Candidate(
        ci_name="openshift-cnv.lightspeed-workshop.prod",
        display_name="OpenShift Lightspeed Workshop",
        category="hands_on_lab",
        summary="A workshop about OpenShift Lightspeed",
        topics=["openshift"],
        products=["OCP"],
        difficulty="beginner",
        duration_min=90,
        content_type="workshop",
        vector_distance=0.2,
        vector_similarity_pct=90,
        relevance_score=92,
        relevant=True,
        one_line_reason="Direct OpenShift workshop match",
        rationale="Strong fit.",
        suggested_format="hands_on_lab",
        duration_notes="90 min",
        caveats="",
    )
    yield QueryState(phase="VECTOR_DONE", candidates=[c], query="test")
    yield QueryState(phase="TRIAGE_DONE", candidates=[c], query="test")
    yield QueryState(
        phase="COMPLETE", candidates=[c], query="test",
        overall_assessment="Good matches found.", content_gaps=[],
    )


@pytest.fixture(autouse=True)
def clear_advisor_state():
    """Clear module-level advisor state between tests to prevent bleed-through."""
    from rcars.web.routes.advisor import _sessions, _query_status
    yield
    _sessions.clear()
    _query_status.clear()


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


def _make_template_env():
    """Create a Jinja2 env with the same filters as the app."""
    from rcars.web.routes.advisor import _format_message
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(_TEMPLATE_DIR))
    env.filters['format_message'] = _format_message
    return env


def test_rec_card_renders_score_and_name():
    env = _make_template_env()
    tmpl = env.get_template("fragments/rec_card.html")
    html = tmpl.render(rec=SAMPLE_REC, is_curator=False, session_id="test-123")
    assert "92" in html
    assert "OpenShift Lightspeed Workshop" in html
    assert "booth demo" in html


def test_rec_card_expanded_shows_caveats():
    env = _make_template_env()
    tmpl = env.get_template("fragments/rec_card_expanded.html")
    html = tmpl.render(rec=SAMPLE_REC, is_curator=False, session_id="test-123")
    assert "Requires OCP 4.16+" in html
    assert "openshift-cnv.lightspeed-workshop.prod" in html


def test_rec_card_expanded_shows_curator_controls_for_curator():
    env = _make_template_env()
    tmpl = env.get_template("fragments/rec_card_expanded.html")
    html = tmpl.render(rec=SAMPLE_REC, is_curator=True, session_id="test-123")
    assert "curator-actions" in html
    assert "Tag" in html


def test_advisor_query_returns_spinner_then_rec_cards(client):
    """POST returns spinner immediately; status endpoint returns rec cards when done."""
    from rcars.web.routes.advisor import _query_status
    import time

    with patch("rcars.web.routes.advisor.run_query", side_effect=_mock_run_query_generator):
        response = client.post("/advisor/query", data={
            "session_id": "async-test-1",
            "message": "OpenShift labs for developers",
        })
        assert response.status_code == 200
        assert "rec-pane" in response.text
        assert "every 2s" in response.text

        for _ in range(20):
            if "async-test-1" in _query_status and not _query_status["async-test-1"]["running"]:
                break
            time.sleep(0.1)

    status_resp = client.get("/advisor/query/status?session_id=async-test-1")
    assert status_resp.status_code == 200
    assert "OpenShift Lightspeed Workshop" in status_resp.text
    assert "92" in status_resp.text
    assert "every 2s" not in status_resp.text
    assert "advisor-result-ready" in status_resp.text


def test_advisor_query_appends_chat_turn(client):
    """Status endpoint done response includes OOB chat-pane swap."""
    from rcars.web.routes.advisor import _query_status
    import time

    with patch("rcars.web.routes.advisor.run_query", side_effect=_mock_run_query_generator):
        client.post("/advisor/query", data={
            "session_id": "chat-turn-test",
            "message": "Show me OpenShift labs",
        })

        for _ in range(20):
            if "chat-turn-test" in _query_status and not _query_status["chat-turn-test"]["running"]:
                break
            time.sleep(0.1)

    status_resp = client.get("/advisor/query/status?session_id=chat-turn-test")
    assert status_resp.status_code == 200
    assert "chat-pane" in status_resp.text
    assert "hx-swap-oob" in status_resp.text
    assert "Good matches found." in status_resp.text


def test_advisor_query_accumulates_context(client):
    import time
    from rcars.web.routes.advisor import _query_status

    calls = []
    def capture_run_query(query, **kwargs):
        calls.append(query)
        yield from _mock_run_query_generator(query, **kwargs)

    with patch("rcars.web.routes.advisor.run_query", side_effect=capture_run_query):
        client.post("/advisor/query", data={"session_id": "acc-test2", "message": "OpenShift labs"})
        for _ in range(20):
            if "acc-test2" in _query_status and not _query_status["acc-test2"]["running"]:
                break
            time.sleep(0.1)
        client.get("/advisor/query/status?session_id=acc-test2")  # consume done state

        client.post("/advisor/query", data={"session_id": "acc-test2", "message": "shorter ones only"})
        for _ in range(20):
            if "acc-test2" in _query_status and not _query_status["acc-test2"]["running"]:
                break
            time.sleep(0.1)

    assert len(calls) == 2
    assert "OpenShift labs" in calls[1]
    assert "shorter ones only" in calls[1]


def test_advisor_query_handles_no_matches(client):
    from rcars.web.routes.advisor import _query_status
    import time

    def no_matches_generator(*args, **kwargs):
        yield QueryState(phase="NO_MATCHES", candidates=[], query="test")

    with patch("rcars.web.routes.advisor.run_query", side_effect=no_matches_generator):
        client.post("/advisor/query", data={
            "session_id": "fail-test2",
            "message": "something",
        })

        for _ in range(20):
            if "fail-test2" in _query_status and not _query_status["fail-test2"]["running"]:
                break
            time.sleep(0.1)

    status_resp = client.get("/advisor/query/status?session_id=fail-test2")
    assert status_resp.status_code == 200
    assert "Nothing in the catalog" in status_resp.text


def test_advisor_query_status_while_running(client):
    """Status endpoint returns spinner while thread is running."""
    from rcars.web.routes.advisor import _query_status
    _query_status["running-session"] = {"running": True, "rec_html": None, "chat_html": None, "error": None}

    resp = client.get("/advisor/query/status?session_id=running-session")
    assert resp.status_code == 200
    assert "every 2s" in resp.text
    assert "rec-pane" in resp.text


def test_advisor_query_status_when_done(client):
    """Status endpoint returns done fragment and clears state."""
    from rcars.web.routes.advisor import _query_status
    _query_status["done-session"] = {
        "running": False,
        "rec_html": '<div class="pane-label">Recommendations</div><p>Result content</p>',
        "chat_html": '<div hx-swap-oob="beforeend:#chat-pane"><div class="chat-turn-assistant">Good match.</div></div>',
        "error": None,
    }

    resp = client.get("/advisor/query/status?session_id=done-session")
    assert resp.status_code == 200
    assert "Result content" in resp.text
    assert "advisor-result-ready" in resp.text  # sentinel present
    assert "chat-pane" in resp.text
    assert "every 2s" not in resp.text  # no polling
    assert "done-session" not in _query_status  # state cleared


def test_advisor_query_status_with_error(client):
    """Status endpoint renders error message when thread failed during rendering."""
    from rcars.web.routes.advisor import _query_status
    _query_status["error-session"] = {
        "running": False,
        "rec_html": None,
        "chat_html": None,
        "error": "An internal error occurred rendering results.",
    }

    resp = client.get("/advisor/query/status?session_id=error-session")
    assert resp.status_code == 200
    assert "An internal error occurred rendering results." in resp.text
    assert "advisor-result-ready" in resp.text
    assert "every 2s" not in resp.text
    assert "error-session" not in _query_status


def test_advisor_query_status_unknown_session(client):
    """Unknown session_id returns spinner gracefully (no crash)."""
    resp = client.get("/advisor/query/status?session_id=does-not-exist")
    assert resp.status_code == 200
    assert "rec-pane" in resp.text


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


def test_spinner_fragment_contains_polling_trigger():
    from rcars.web.routes.advisor import _query_spinner_fragment
    html = _query_spinner_fragment("test-sid")
    assert 'hx-trigger="every 2s"' in html
    assert "session_id=test-sid" in html
    assert 'id="rec-pane"' in html


def test_done_fragment_contains_sentinel():
    from rcars.web.routes.advisor import _query_done_fragment
    html = _query_done_fragment("<p>recs</p>", "<div>chat</div>")
    assert 'id="advisor-result-ready"' in html
    assert "<p>recs</p>" in html
    assert "<div>chat</div>" in html


def test_error_fragment_appends_to_turns(client):
    from rcars.web.routes.advisor import _query_error_fragment
    turns = [{"role": "user", "content": "hello"}]
    _query_error_fragment("DB error", "hello", "sid", "hello", turns)
    assert len(turns) == 2
    assert turns[1]["role"] == "assistant"
    assert turns[1]["turn_index"] == 1
