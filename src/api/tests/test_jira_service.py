"""Tests for the Jira retirement ticket service."""
from datetime import date
from unittest.mock import MagicMock, call, patch

from rcars.services.jira import build_retirement_description, create_retirement_ticket


def _make_workflow(**overrides):
    """Build a minimal workflow dict for testing."""
    base = {
        "catalog_base_name": "openshift_cnv.legacy_demo",
        "approval_reason": "Low usage and high cost",
        "curator_notes": "Replaced by newer demo",
        "replacement_ci": "openshift_cnv.new_demo",
        "replacement_name": "New OpenShift Demo",
        "retirement_target_date": date(2026, 9, 1),
        "jira_project": "GPTEINFRA",
        "approval_snapshot": {
            "provisions": 5,
            "experiences": 2,
            "unique_users": 3,
            "touched_amount": 15000,
            "closed_amount": 5000,
            "total_cost": 8500,
            "retirement_score": 85,
            "window": "90d",
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

    # Display name and base name
    assert "Legacy OpenShift Demo" in desc
    assert "openshift_cnv.legacy_demo" in desc

    # RHDP URL with base name
    assert "https://demo.redhat.com/catalog?search=openshift_cnv.legacy_demo" in desc

    # AgV path (dots replaced with slashes)
    assert "https://github.com/rhpds/agnosticv/tree/master/openshift_cnv/legacy_demo" in desc

    # Approval reason
    assert "Low usage and high cost" in desc

    # Curator notes
    assert "Replaced by newer demo" in desc

    # Replacement
    assert "New OpenShift Demo (openshift_cnv.new_demo)" in desc

    # Target date
    assert "2026-09-01" in desc

    # Metrics
    assert "85" in desc  # retirement score
    assert "5" in desc   # provisions
    assert "$15,000" in desc  # touched amount
    assert "$5,000" in desc   # closed amount
    assert "$8,500" in desc   # total cost
    assert "2026-06-15" in desc  # snapshot date


def test_no_replacement():
    """Verify 'N/A' appears when no replacement CI is set."""
    workflow = _make_workflow(replacement_ci=None, replacement_name=None)
    metrics = _make_metrics()
    desc = build_retirement_description(workflow, metrics)

    assert "**Replacement CI:** N/A" in desc


def test_no_notes():
    """Verify description works when curator_notes is None."""
    workflow = _make_workflow(curator_notes=None)
    metrics = _make_metrics()
    desc = build_retirement_description(workflow, metrics)

    # Reason should still appear
    assert "Low usage and high cost" in desc
    # There should be no second bullet for notes
    lines = [l.strip() for l in desc.splitlines() if l.strip().startswith("*")]
    reason_bullets = [l for l in lines if l.startswith("* ")]
    assert len(reason_bullets) == 1
    assert reason_bullets[0] == "* Low usage and high cost"


@patch("rcars.services.jira._jira_request")
def test_creates_ticket_and_returns_key(mock_request):
    """Verify ticket creation calls Jira API correctly and returns the key."""
    # First call (create issue) returns the key; second call (link) returns None
    mock_request.side_effect = [{"key": "RHDPCD-999"}, None]

    settings = MagicMock()
    settings.jira_retirement_template = "GPTEINFRA-14367"

    workflow = _make_workflow()
    metrics = _make_metrics()

    result = create_retirement_ticket(settings, workflow, metrics)

    assert result == "RHDPCD-999"
    assert mock_request.call_count == 2

    # Verify the create call
    create_call = mock_request.call_args_list[0]
    assert create_call[0][0] is settings
    assert create_call[0][1] == "/rest/api/3/issue"
    create_body = create_call[1]["body"] if "body" in create_call[1] else create_call[0][2] if len(create_call[0]) > 2 else create_call.kwargs.get("body")
    assert create_body["fields"]["project"]["key"] == "GPTEINFRA"
    assert create_body["fields"]["summary"] == 'Retire "Legacy OpenShift Demo"'
    assert "RHDP_RETIREMENT" in create_body["fields"]["labels"]
    assert create_body["fields"]["issuetype"]["id"] == "10014"

    # Verify the link call
    link_call = mock_request.call_args_list[1]
    assert link_call[0][1] == "/rest/api/3/issueLink"
    link_body = link_call[1]["body"] if "body" in link_call[1] else link_call[0][2] if len(link_call[0]) > 2 else link_call.kwargs.get("body")
    assert link_body["inwardIssue"]["key"] == "GPTEINFRA-14367"
    assert link_body["outwardIssue"]["key"] == "RHDPCD-999"
    assert link_body["type"]["name"] == "Cloners"
