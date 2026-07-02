"""Jira REST API client for retirement ticket creation.

Uses urllib (consistent with RCARS HTTP patterns in reporting_sync.py)
to create retirement tickets and link them to the template issue.
"""
from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request
from datetime import date

import structlog

logger = structlog.get_logger(component="jira")


def _jira_request(
    settings,
    path: str,
    method: str = "POST",
    body: dict | None = None,
) -> dict | None:
    """Make an HTTP request to the Jira REST API v3 with Basic auth.

    Returns parsed JSON for responses with a body, None for 204 No Content.
    """
    url = f"{settings.jira_base_url}{path}"
    credentials = f"{settings.jira_api_email}:{settings.jira_api_token}"
    auth = base64.b64encode(credentials.encode("utf-8")).decode("ascii")

    data = json.dumps(body).encode("utf-8") if body else None

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Basic {auth}",
        },
        method=method,
    )

    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            if resp.status == 204:
                return None
            body = resp.read().decode("utf-8")
            if not body.strip():
                return None
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        logger.error(
            "jira_request_failed",
            url=url,
            status=exc.code,
            error=error_body[:500],
        )
        raise
    except urllib.error.URLError as exc:
        logger.error("jira_request_error", url=url, error=str(exc))
        raise


def build_retirement_description(workflow: dict, metrics: dict) -> str:
    """Build the Jira ticket description markdown for a retirement ticket."""
    base_name = workflow.get("catalog_base_name", "unknown")
    display_name = metrics.get("display_name", base_name)
    reason = workflow.get("approval_reason", "No reason provided")
    notes = workflow.get("curator_notes")
    replacement_ci = workflow.get("replacement_ci")
    replacement_name = workflow.get("replacement_name")
    target_date = workflow.get("retirement_target_date")

    # Format target date
    if isinstance(target_date, date):
        target_date_str = target_date.isoformat()
    else:
        target_date_str = str(target_date) if target_date else "TBD"

    # AgV path: dots become slashes
    agv_path = base_name.replace(".", "/")

    # Replacement line
    if replacement_ci and replacement_name:
        replacement_line = f"{replacement_name} ({replacement_ci})"
    elif replacement_ci:
        replacement_line = replacement_ci
    else:
        replacement_line = "N/A"

    # Reason & Notes section
    notes_lines = [f"* {reason}"]
    if notes:
        notes_lines.append(f"* {notes}")

    # Metrics snapshot
    snapshot = workflow.get("approval_snapshot", {})
    score = snapshot.get("retirement_score", "N/A")
    provisions = snapshot.get("provisions", "N/A")
    experiences = snapshot.get("experiences", "N/A")
    unique_users = snapshot.get("unique_users", "N/A")
    touched = snapshot.get("touched_amount", "N/A")
    closed = snapshot.get("closed_amount", "N/A")
    cost = snapshot.get("total_cost", "N/A")
    snapshot_date = snapshot.get("snapshot_date", "N/A")

    # Format dollar amounts
    def fmt_dollar(val):
        if isinstance(val, (int, float)):
            return f"${val:,.0f}"
        if isinstance(val, str) and val != "N/A":
            return f"${val}"
        return str(val)

    # Build the AsciiDoc retirement notice template
    adoc_replacement_line = ""
    if replacement_ci and replacement_name:
        adoc_replacement_line = (
            f' Please use this as an alternative: link:https://demo.redhat.com/catalog?search={replacement_ci}'
            f'[{replacement_name}, window="_blank"]'
        )
    elif replacement_ci:
        adoc_replacement_line = (
            f' Please use this as an alternative: link:https://demo.redhat.com/catalog?search={replacement_ci}'
            f'[replacement item, window="_blank"]'
        )

    adoc_template = (
        "[IMPORTANT]\n"
        ".RETIREMENT NOTICE\n"
        "****\n"
        f"This item will be retired on **[DATE TBD]**.{adoc_replacement_line}\n"
        "\n"
        "For any questions regarding this retirement, please contact "
        "Nate Stephany at mailto:nstephan@redhat.com[nstephan@redhat.com].\n"
        "****"
    )

    description = f"""**CI Name:** {display_name}

**RHDP URL:** https://demo.redhat.com/catalog?search={base_name}

**AgV:** https://github.com/rhpds/agnosticv/tree/master/{agv_path}

**Retirement Notice:** {target_date_str}

**Replacement CI:** {replacement_line}

**Reason & Notes:**

{chr(10).join(notes_lines)}

**Metrics at approval (snapshot {snapshot_date}):**

| Metric | Value |
|--------|-------|
| Retirement Score | {score} |
| Provisions | {provisions} |
| Experiences | {experiences} |
| Unique Users | {unique_users} |
| Touched Amount | {fmt_dollar(touched)} |
| Closed Amount | {fmt_dollar(closed)} |
| Total Cost | {fmt_dollar(cost)} |

---

**Suggested adoc template** _(replace_ `[DATE TBD]` _with the actual retirement date before pasting into the CI)_**:**

```
{adoc_template}
```"""

    return description


def create_retirement_ticket(
    settings,
    workflow: dict,
    metrics: dict,
) -> str:
    """Create a Jira retirement ticket and link it to the template issue.

    Returns the new Jira issue key (e.g. "RHDPCD-999").
    """
    display_name = metrics.get("display_name", workflow.get("catalog_base_name", "unknown"))
    project_key = workflow.get("jira_project", "GPTEINFRA").upper()
    description = build_retirement_description(workflow, metrics)

    logger.info(
        "creating_retirement_ticket",
        display_name=display_name,
        project=project_key,
    )

    # Step 1: Create the issue
    create_body = {
        "fields": {
            "project": {"key": project_key},
            "issuetype": {"name": "Task"},
            "summary": f'Retire "{display_name}"',
            "description": description,
            "labels": ["RHDP_RETIREMENT"],
        }
    }

    result = _jira_request(settings, "/rest/api/2/issue", body=create_body)
    issue_key = result["key"]

    logger.info("retirement_ticket_created", issue_key=issue_key)

    # Step 2: Link to the template issue
    link_body = {
        "type": {"name": "Cloners"},
        "inwardIssue": {"key": settings.jira_retirement_template},
        "outwardIssue": {"key": issue_key},
    }

    _jira_request(settings, "/rest/api/2/issueLink", body=link_body)

    logger.info(
        "retirement_ticket_linked",
        issue_key=issue_key,
        template=settings.jira_retirement_template,
    )

    return issue_key
