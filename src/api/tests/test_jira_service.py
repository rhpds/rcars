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
    assert "{code}" in desc
    assert "[IMPORTANT]" in desc
    assert ".RETIREMENT NOTICE" in desc


def test_no_replacement():
    """Verify 'N/A' appears when no replacement CI is set."""
    workflow = _make_workflow(replacement_ci=None, replacement_name=None)
    metrics = _make_metrics()
    desc = build_retirement_description(workflow, metrics)

    assert "*Replacement CI:* N/A" in desc
    assert "[DATE TBD]" in desc


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
    assert "----" in desc  # wiki horizontal rule


@patch("rcars.services.jira._jira_request")
def test_creates_ticket_and_returns_key(mock_request):
    """Verify ticket creation calls Jira v2 API and returns the key."""
    mock_request.return_value = {"key": "RHDPCD-999"}

    settings = MagicMock()
    workflow = _make_workflow()
    metrics = _make_metrics()

    result = create_retirement_ticket(settings, workflow, metrics)

    assert result == "RHDPCD-999"
    assert mock_request.call_count == 1

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
    mock_request.return_value = {"key": "RHDPCD-100"}

    settings = MagicMock()
    workflow = _make_workflow(jira_project="rhdpcd")
    metrics = _make_metrics()

    create_retirement_ticket(settings, workflow, metrics)

    body = mock_request.call_args.kwargs.get("body") or mock_request.call_args[0][2]
    assert body["fields"]["project"]["key"] == "RHDPCD"
