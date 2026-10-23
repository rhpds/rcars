"""Tests for the Jira retirement ticket service."""
from unittest.mock import MagicMock, patch

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
