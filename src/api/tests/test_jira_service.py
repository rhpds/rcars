"""Tests for the Jira retirement ticket service."""
import base64
import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs

import pytest

from rcars.services import jira
from rcars.services.jira import build_retirement_description, create_retirement_ticket


def _make_workflow(**overrides):
    """Build a minimal workflow dict for testing."""
    base = {
        "catalog_base_name": "openshift_cnv.legacy_demo",
        "approval_reason": "Low usage and high cost",
        "curator_notes": "Replaced by newer demo",
        "replacement_ci": "openshift_cnv.new_demo",
        "replacement_name": "New OpenShift Demo",
        "replacement_source": "babylon",
        "replacement_ci_full": "openshift_cnv.new_demo.prod",
        "target_days": 30,
        "jira_project": "GPTEINFRA",
        "approval_snapshot": {
            "provisions": 5,
            "experiences": 2,
            "unique_users": 3,
            "touched_amount": 15000,
            "closed_amount": 5000,
            "total_cost": 8500,
            "retirement_score": 85,
            "snapshot_date": "2026-06-15",
        },
    }
    base.update(overrides)
    return base


def _make_metrics(**overrides):
    """Build a minimal metrics dict for testing."""
    base = {"display_name": "Legacy OpenShift Demo"}
    base.update(overrides)
    return base


def test_basic_description():
    """Verify all key fields appear in the retirement description."""
    workflow = _make_workflow()
    metrics = _make_metrics()
    desc = build_retirement_description(workflow, metrics)

    assert "Legacy OpenShift Demo" in desc
    assert "openshift_cnv.legacy_demo" in desc
    assert "catalog.demo.redhat.com/catalog?item=babylon-catalog-prod/openshift_cnv.legacy_demo.prod" in desc
    assert "openshift_cnv/legacy_demo" in desc  # AgV ref
    assert "Low usage and high cost" in desc
    assert "Replaced by newer demo" in desc
    assert "catalog.demo.redhat.com/catalog?item=babylon-catalog-prod/openshift_cnv.new_demo" in desc
    assert "30 days" in desc
    assert "85" in desc
    assert "$15,000" in desc
    assert "$5,000" in desc
    assert "$8,500" in desc
    assert "2026-06-15" in desc


def test_no_replacement():
    """Verify 'N/A' appears when no replacement CI is set."""
    workflow = _make_workflow(replacement_ci=None, replacement_name=None)
    metrics = _make_metrics()
    desc = build_retirement_description(workflow, metrics)

    assert "*Replacement CI:* N/A" in desc


def test_no_notes():
    """Verify description works when curator_notes is None."""
    workflow = _make_workflow(curator_notes=None)
    metrics = _make_metrics()
    desc = build_retirement_description(workflow, metrics)

    assert "Low usage and high cost" in desc
    reason_bullets = [l.strip() for l in desc.splitlines() if l.strip().startswith("* ")]
    assert len(reason_bullets) == 1


def test_wiki_markup_format():
    """Verify Jira wiki markup syntax is used, not markdown."""
    workflow = _make_workflow()
    metrics = _make_metrics()
    desc = build_retirement_description(workflow, metrics)

    assert "*CI Name:*" in desc  # wiki bold
    assert "**CI Name:**" not in desc  # not markdown bold
    assert "||Metric||Value||" in desc  # wiki table header


def _settings(parent="RHDPCD-2191"):
    settings = MagicMock()
    settings.jira_retirement_parent = parent
    return settings


IN_PROGRESS_TRANSITIONS = {"transitions": [
    {"id": "11", "to": {"name": "New"}},
    {"id": "41", "to": {"name": "In Progress"}},
    {"id": "61", "to": {"name": "Closed"}},
]}


def _fake_jira(key="RHDPCD-999", transitions=IN_PROGRESS_TRANSITIONS):
    def fake(settings, path, method="POST", body=None):
        if path == "/rest/api/2/issue":
            return {"key": key}
        if path.endswith("/transitions") and method == "GET":
            return transitions
        return None
    return fake


@patch("rcars.services.jira._jira_request")
def test_creates_ticket_and_returns_key(mock_request):
    """Verify ticket creation calls Jira v2 API and returns the key."""
    mock_request.side_effect = _fake_jira()

    settings = _settings()
    workflow = _make_workflow()
    metrics = _make_metrics()

    result = create_retirement_ticket(settings, workflow, metrics)

    assert result == "RHDPCD-999"

    create_call = mock_request.call_args_list[0]
    assert create_call[0][0] is settings
    assert create_call[0][1] == "/rest/api/2/issue"
    body = create_call.kwargs.get("body") or create_call[0][2]
    assert body["fields"]["project"]["key"] == "GPTEINFRA"
    assert body["fields"]["summary"] == 'Retire "Legacy OpenShift Demo"'
    assert "RHDP_RETIREMENT" in body["fields"]["labels"]
    assert body["fields"]["issuetype"]["name"] == "Task"


@patch("rcars.services.jira._jira_request")
def test_project_key_uppercased(mock_request):
    """Verify lowercase project key is uppercased."""
    mock_request.side_effect = _fake_jira("RHDPCD-100")

    settings = _settings()
    workflow = _make_workflow(jira_project="rhdpcd")
    metrics = _make_metrics()

    create_retirement_ticket(settings, workflow, metrics)

    create_call = mock_request.call_args_list[0]
    body = create_call.kwargs.get("body") or create_call[0][2]
    assert body["fields"]["project"]["key"] == "RHDPCD"


def _create_body(mock_request):
    call = mock_request.call_args_list[0]
    return call.kwargs.get("body") or call[0][2]


@patch("rcars.services.jira._jira_request")
def test_ticket_parent_set_for_matching_project(mock_request):
    mock_request.side_effect = _fake_jira()

    create_retirement_ticket(_settings(), _make_workflow(jira_project="RHDPCD"), _make_metrics())

    assert _create_body(mock_request)["fields"]["parent"] == {"key": "RHDPCD-2191"}


@patch("rcars.services.jira._jira_request")
def test_ticket_parent_skipped_for_other_project(mock_request):
    mock_request.side_effect = _fake_jira("GPTEINFRA-1")

    create_retirement_ticket(_settings(), _make_workflow(jira_project="GPTEINFRA"), _make_metrics())

    assert "parent" not in _create_body(mock_request)["fields"]


@patch("rcars.services.jira._jira_request")
def test_ticket_parent_skipped_when_unset(mock_request):
    mock_request.side_effect = _fake_jira()

    create_retirement_ticket(_settings(parent=""), _make_workflow(jira_project="RHDPCD"), _make_metrics())

    assert "parent" not in _create_body(mock_request)["fields"]


@patch("rcars.services.jira._jira_request")
def test_new_ticket_moves_to_in_progress(mock_request):
    mock_request.side_effect = _fake_jira()

    create_retirement_ticket(_settings(), _make_workflow(jira_project="RHDPCD"), _make_metrics())

    transition_posts = [c for c in mock_request.call_args_list
                        if c[0][1] == "/rest/api/2/issue/RHDPCD-999/transitions"
                        and c.kwargs.get("method", "POST") == "POST"]
    assert len(transition_posts) == 1
    assert transition_posts[0].kwargs["body"] == {"transition": {"id": "41"}}


@patch("rcars.services.jira._jira_request")
def test_missing_in_progress_transition_still_returns_key(mock_request):
    mock_request.side_effect = _fake_jira(transitions={"transitions": [{"id": "61", "to": {"name": "Closed"}}]})

    result = create_retirement_ticket(_settings(), _make_workflow(jira_project="RHDPCD"), _make_metrics())

    assert result == "RHDPCD-999"
    assert not any(c[0][1].endswith("/transitions") and c.kwargs.get("method", "POST") == "POST"
                   for c in mock_request.call_args_list)


@patch("rcars.services.jira._jira_request")
def test_failed_in_progress_transition_still_returns_key(mock_request):
    def fake(settings, path, method="POST", body=None):
        if path == "/rest/api/2/issue":
            return {"key": "RHDPCD-999"}
        raise RuntimeError("Jira down")
    mock_request.side_effect = fake

    assert create_retirement_ticket(_settings(), _make_workflow(jira_project="RHDPCD"), _make_metrics()) == "RHDPCD-999"


# --- OAuth2 client credentials vs Basic auth fallback ---

TOKEN_URL = "https://auth.atlassian.com/oauth/token"


class _FakeResponse:
    """Minimal context-manager response for mocked urlopen calls."""

    def __init__(self, payload):
        self.status = 200
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _oauth_settings(**overrides):
    base = {
        "jira_base_url": "https://jira.example.com",
        "jira_api_email": "user@example.com",
        "jira_api_token": "basic-token",
        "jira_client_id": "client-id",
        "jira_client_secret": "client-secret",
        "jira_cloud_id": "cloud-123",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _token_payload(token="oauth-token", expires_in=3600):
    return {"access_token": token, "expires_in": expires_in, "token_type": "bearer", "scope": "read:jira"}


def _header(req, name):
    """Case-insensitive header lookup (urllib normalizes header case)."""
    for key, value in req.headers.items():
        if key.lower() == name.lower():
            return value
    return None


@pytest.fixture(autouse=True)
def _clean_token_cache():
    jira._reset_token_cache()
    yield
    jira._reset_token_cache()


def test_oauth_token_fetched_on_first_call_and_cached():
    """Second call within the token lifetime must not re-fetch the token."""
    requests_seen = []

    def fake_urlopen(req, **kwargs):
        requests_seen.append(req)
        if req.full_url == TOKEN_URL:
            return _FakeResponse(_token_payload())
        return _FakeResponse({"key": "EXAMPLE-1"})

    with patch("rcars.services.jira.urllib.request.urlopen", side_effect=fake_urlopen):
        first = jira._jira_request(_oauth_settings(), "/rest/api/2/issue/EXAMPLE-1", method="GET")
        second = jira._jira_request(_oauth_settings(), "/rest/api/2/issue/EXAMPLE-1", method="GET")

    assert first == {"key": "EXAMPLE-1"}
    assert second == {"key": "EXAMPLE-1"}
    assert len([r for r in requests_seen if r.full_url == TOKEN_URL]) == 1
    api_calls = [r for r in requests_seen if r.full_url != TOKEN_URL]
    assert [r.full_url for r in api_calls] == [
        "https://api.atlassian.com/ex/jira/cloud-123/rest/api/2/issue/EXAMPLE-1",
    ] * 2
    assert all(_header(r, "Authorization") == "Bearer oauth-token" for r in api_calls)


def test_oauth_token_request_format():
    """Token fetch must be a form-urlencoded client_credentials grant."""
    captured = []

    def fake_urlopen(req, **kwargs):
        captured.append(req)
        if req.full_url == TOKEN_URL:
            return _FakeResponse(_token_payload())
        return _FakeResponse({"key": "EXAMPLE-1"})

    with patch("rcars.services.jira.urllib.request.urlopen", side_effect=fake_urlopen):
        jira._jira_request(_oauth_settings(), "/rest/api/2/issue/EXAMPLE-1", method="GET")

    token_req = captured[0]
    assert token_req.full_url == TOKEN_URL
    assert token_req.method == "POST"
    assert _header(token_req, "Content-Type") == "application/x-www-form-urlencoded"
    assert parse_qs(token_req.data.decode("utf-8")) == {
        "client_id": ["client-id"],
        "client_secret": ["client-secret"],
        "grant_type": ["client_credentials"],
    }


@pytest.mark.parametrize("remaining_seconds", [30, 0, -60])
def test_oauth_token_refreshed_near_or_past_expiry(remaining_seconds):
    """A cached token within the 60s expiry margin must be re-fetched."""
    jira._token_cache["token"] = "stale-token"
    jira._token_cache["expires_at"] = time.monotonic() + remaining_seconds

    captured = []

    def fake_urlopen(req, **kwargs):
        captured.append(req)
        if req.full_url == TOKEN_URL:
            return _FakeResponse(_token_payload(token="fresh-token"))
        return _FakeResponse({"key": "EXAMPLE-1"})

    with patch("rcars.services.jira.urllib.request.urlopen", side_effect=fake_urlopen):
        jira._jira_request(_oauth_settings(), "/rest/api/2/issue/EXAMPLE-1", method="GET")

    token_calls = [r for r in captured if r.full_url == TOKEN_URL]
    assert len(token_calls) == 1
    api_call = next(r for r in captured if r.full_url != TOKEN_URL)
    assert _header(api_call, "Authorization") == "Bearer fresh-token"


def test_valid_cached_token_survives_settings_change():
    """The token cache is keyed on nothing; a valid token is reused as-is."""
    jira._token_cache["token"] = "cached-token"
    jira._token_cache["expires_at"] = time.monotonic() + 3600

    captured = []

    def fake_urlopen(req, **kwargs):
        captured.append(req)
        return _FakeResponse({"key": "EXAMPLE-1"})

    with patch("rcars.services.jira.urllib.request.urlopen", side_effect=fake_urlopen):
        jira._jira_request(_oauth_settings(), "/rest/api/2/issue/EXAMPLE-1", method="GET")

    assert len(captured) == 1
    assert _header(captured[0], "Authorization") == "Bearer cached-token"


@pytest.mark.parametrize("missing", ["jira_client_id", "jira_client_secret", "jira_cloud_id"])
def test_partial_oauth_config_falls_back_to_basic(missing):
    """Any missing OAuth2 field must keep the Basic auth path intact."""
    captured = []

    def fake_urlopen(req, **kwargs):
        captured.append(req)
        return _FakeResponse({"key": "EXAMPLE-1"})

    with patch("rcars.services.jira.urllib.request.urlopen", side_effect=fake_urlopen):
        jira._jira_request(_oauth_settings(**{missing: ""}), "/rest/api/2/issue/EXAMPLE-1", method="GET")

    assert len(captured) == 1
    assert captured[0].full_url == "https://jira.example.com/rest/api/2/issue/EXAMPLE-1"
    expected = base64.b64encode(b"user@example.com:basic-token").decode("ascii")
    assert _header(captured[0], "Authorization") == f"Basic {expected}"


def test_basic_auth_used_when_oauth_not_configured():
    """Without OAuth2 config, requests hit jira_base_url with Basic auth."""
    captured = []

    def fake_urlopen(req, **kwargs):
        captured.append(req)
        return _FakeResponse({"key": "EXAMPLE-1"})

    settings = _oauth_settings(jira_client_id="", jira_client_secret="", jira_cloud_id="")
    with patch("rcars.services.jira.urllib.request.urlopen", side_effect=fake_urlopen):
        jira._jira_request(settings, "/rest/api/2/issue/EXAMPLE-1", method="GET")

    assert len(captured) == 1
    assert captured[0].full_url == "https://jira.example.com/rest/api/2/issue/EXAMPLE-1"
    expected = base64.b64encode(b"user@example.com:basic-token").decode("ascii")
    assert _header(captured[0], "Authorization") == f"Basic {expected}"


def test_jira_auth_configured_accepts_either_auth():
    assert jira.jira_auth_configured(_oauth_settings())
    assert jira.jira_auth_configured(_oauth_settings(jira_api_email="", jira_api_token=""))
    assert not jira.jira_auth_configured(
        _oauth_settings(jira_client_id="", jira_client_secret="", jira_cloud_id="",
                        jira_api_email="", jira_api_token=""))
