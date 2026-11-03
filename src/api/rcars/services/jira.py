"""Jira REST API client for retirement ticket creation.

Uses urllib (consistent with RCARS HTTP patterns in reporting_sync.py)
to create retirement tickets.

Authentication: OAuth2 client credentials (Bearer token against
api.atlassian.com) — the only supported method. Requires
jira_client_id, jira_client_secret, and jira_cloud_id to be configured.
"""
from __future__ import annotations

import json
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

import structlog

logger = structlog.get_logger(component="jira")

_ATLASSIAN_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
_ATLASSIAN_API_BASE = "https://api.atlassian.com/ex/jira"
_TOKEN_EXPIRY_MARGIN_SECONDS = 60.0

# Module-level OAuth2 token cache. Refreshed lazily on demand only — Jira is
# idle most of the time, so nothing runs while no Jira call is being made.
_token_cache: dict = {"token": "", "expires_at": 0.0}
_token_lock = threading.Lock()


def _reset_token_cache() -> None:
    """Drop the cached access token so the next call fetches a fresh one."""
    with _token_lock:
        _token_cache["token"] = ""
        _token_cache["expires_at"] = 0.0


def _oauth_config(settings) -> tuple[str, str, str] | None:
    """Return (client_id, client_secret, cloud_id) when OAuth2 is fully configured."""
    client_id = settings.jira_client_id
    client_secret = settings.jira_client_secret
    cloud_id = settings.jira_cloud_id
    if client_id and client_secret and cloud_id:
        return client_id, client_secret, cloud_id
    return None


def jira_auth_configured(settings) -> bool:
    """True when OAuth2 client credentials are fully configured."""
    return _oauth_config(settings) is not None


def _fetch_oauth_token(client_id: str, client_secret: str) -> None:
    """Fetch a new access token from auth.atlassian.com into the module cache."""
    form = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }).encode("utf-8")

    req = urllib.request.Request(
        _ATLASSIAN_TOKEN_URL,
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )

    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        logger.error(
            "jira_oauth_token_fetch_failed",
            url=_ATLASSIAN_TOKEN_URL,
            status=exc.code,
            error=error_body[:500],
        )
        raise
    except urllib.error.URLError as exc:
        logger.error("jira_oauth_token_fetch_error", url=_ATLASSIAN_TOKEN_URL, error=str(exc))
        raise

    token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    if not token or not isinstance(expires_in, (int, float)):
        raise RuntimeError("Invalid OAuth2 token response from auth.atlassian.com")

    _token_cache["token"] = token
    _token_cache["expires_at"] = time.monotonic() + float(expires_in)
    logger.info("jira_oauth_token_fetched", expires_in=expires_in)


def _get_access_token(client_id: str, client_secret: str) -> str:
    """Return a valid access token, lazily fetching one when missing or near expiry.

    The lock covers the fetch so concurrent senders share a single token request.
    """
    with _token_lock:
        now = time.monotonic()
        if _token_cache["token"] and now < _token_cache["expires_at"] - _TOKEN_EXPIRY_MARGIN_SECONDS:
            return _token_cache["token"]
        _fetch_oauth_token(client_id, client_secret)
        return _token_cache["token"]


def _jira_request(
    settings,
    path: str,
    method: str = "POST",
    body: dict | None = None,
) -> dict | None:
    """Make an HTTP request to the Jira REST API with an OAuth2 Bearer token.

    Calls go to api.atlassian.com/ex/jira/{cloud_id}. Raises RuntimeError when
    OAuth2 client credentials are not configured, so unconfigured environments
    fail fast instead of sending authenticated-less traffic.

    Returns parsed JSON for responses with a body, None for 204 No Content.
    """
    oauth = _oauth_config(settings)
    if not oauth:
        raise RuntimeError("Jira integration not configured: OAuth2 client credentials required")
    client_id, client_secret, cloud_id = oauth

    data = json.dumps(body).encode("utf-8") if body else None
    token = _get_access_token(client_id, client_secret)
    url = f"{_ATLASSIAN_API_BASE}/{cloud_id}{path}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
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


def _base_name_from_content_id(content_id: str) -> str:
    """Derive catalog base name from content_id (e.g. 'babylon:foo.prod' → 'foo')."""
    name = content_id.removeprefix("babylon:")
    for suffix in (".prod", ".event", ".dev", ".test"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def ensure_issue_event_comment(settings, jira_key: str, event_key: str, message: str) -> str:
    """Recover an existing event comment before posting, including ambiguous retries."""
    if not jira_auth_configured(settings):
        raise RuntimeError("Jira comment delivery pending: integration not configured")
    property_key = "rcars.retirement.event"
    start = 0
    while True:
        page = _jira_request(settings, f"/rest/api/3/issue/{jira_key}/comment?expand=properties&startAt={start}&maxResults=100", method="GET")
        if not isinstance(page, dict) or not isinstance(page.get("comments"), list):
            raise RuntimeError("Invalid Jira comments page")
        comments, total = page["comments"], page.get("total")
        if type(total) is not int or total < start + len(comments) or page.get("startAt") != start:
            raise RuntimeError("Invalid Jira comments pagination")
        for comment in comments:
            if not isinstance(comment, dict) or not isinstance(comment.get("properties", []), list):
                raise RuntimeError("Invalid Jira comment properties")
            if any(
                isinstance(prop, dict) and prop.get("key") == property_key
                and prop.get("value") in ({"event_key": event_key}, event_key)
                for prop in comment.get("properties", [])
            ):
                if not comment.get("id"):
                    raise RuntimeError("Jira event comment has no ID")
                return str(comment["id"])
        start += len(comments)
        if start >= total:
            break
        if not comments:
            raise RuntimeError("Jira comments pagination made no progress")
    paragraphs = []
    for line in message.splitlines():
        content = []
        for text in re.split(r"(https?://\S+)", line):
            if not text:
                continue
            node = {"type": "text", "text": text}
            if text.startswith(("https://", "http://")):
                node["marks"] = [{"type": "link", "attrs": {"href": text}}]
            content.append(node)
        paragraphs.append({"type": "paragraph", "content": content})
    result = _jira_request(settings, f"/rest/api/3/issue/{jira_key}/comment", body={
        "body": {"type": "doc", "version": 1, "content": paragraphs},
        # Jira rejects scalar entity-property values; keep the marker in an object.
        "properties": [{"key": property_key, "value": {"event_key": event_key}}],
    })
    if not isinstance(result, dict) or not result.get("id"):
        raise RuntimeError("Jira comment response has no ID; reconcile before retry")
    return str(result["id"])


def build_retirement_adoc_notice(workflow: dict) -> str:
    """Return the AsciiDoc retirement notice block for inclusion in description.adoc.

    Uses the actual retirement target date if available, otherwise [DATE TBD].
    """
    replacement_ci = workflow.get("replacement_ci")
    replacement_name = workflow.get("replacement_name")
    replacement_source = workflow.get("replacement_source")
    replacement_ci_full = workflow.get("replacement_ci_full")
    catalog_base = "https://catalog.demo.redhat.com/catalog?item=babylon-catalog-prod"

    target_date = workflow.get("retirement_target_date")
    date_str = str(target_date) if target_date else "[DATE TBD]"

    adoc_replacement_line = ""
    if replacement_ci and replacement_source == "babylon":
        repl_ci_url = replacement_ci_full or (replacement_ci if replacement_ci.endswith(".prod") else f"{replacement_ci}.prod")
        adoc_replacement_line = (
            f" Please use this as an alternative: "
            f"link:{catalog_base}/{repl_ci_url}[{replacement_name or replacement_ci}, window=\"_blank\"]"
        )
    elif replacement_ci:
        adoc_replacement_line = f" Please use this as an alternative: {replacement_name or replacement_ci}"

    return (
        "[IMPORTANT]\n"
        ".RETIREMENT NOTICE\n"
        "****\n"
        f"This item will be retired on *{date_str}*.{adoc_replacement_line}\n"
        "\n"
        "For any questions regarding this retirement, please contact "
        "Nate Stephany at mailto:nstephan@redhat.com[nstephan@redhat.com].\n"
        "****"
    )


def build_retirement_description(workflow: dict, metrics: dict) -> str:
    """Build the Jira ticket description in Jira wiki markup."""
    base_name = (_base_name_from_content_id(workflow.get("content_id", ""))
                 or workflow.get("catalog_base_name")
                 or "unknown")
    display_name = metrics.get("display_name", base_name)
    reason = workflow.get("approval_reason", "No reason provided")
    notes = workflow.get("curator_notes")
    replacement_ci = workflow.get("replacement_ci")
    replacement_name = workflow.get("replacement_name")
    target_days = workflow.get("target_days", 30)

    # AgV component/item from CI base name — reverse Babylon's _ → - normalization on the namespace
    agv_ref = base_name.replace(".", "/", 1) if "." in base_name else base_name
    parts = agv_ref.split("/", 1)
    if len(parts) == 2 and "-" in parts[0]:
        agv_ref = parts[0].replace("-", "_") + "/" + parts[1]

    catalog_base = "https://catalog.demo.redhat.com/catalog?item=babylon-catalog-prod"

    replacement_source = workflow.get("replacement_source")
    replacement_ci_full = workflow.get("replacement_ci_full")
    if replacement_ci and replacement_source == "babylon":
        repl_ci_url = replacement_ci_full or (replacement_ci if replacement_ci.endswith(".prod") else f"{replacement_ci}.prod")
        replacement_line = f"{catalog_base}/{repl_ci_url}"
    elif replacement_ci:
        replacement_line = replacement_name or replacement_ci
    else:
        replacement_line = "N/A"

    # Reason & Notes — split multi-line reasons into individual bullets
    notes_lines = [f"* {line.strip()}" for line in reason.splitlines() if line.strip()]
    if notes:
        for line in notes.splitlines():
            if line.strip():
                notes_lines.append(f"* {line.strip()}")

    # Metrics snapshot
    raw_snapshot = workflow.get("approval_snapshot", {})
    snapshot = raw_snapshot.get("sales", raw_snapshot)
    score = snapshot.get("score")
    if score is None:
        score = snapshot.get("retirement_score", "N/A")
    provisions = snapshot.get("provisions", "N/A")
    experiences = snapshot.get("experiences", "N/A")
    unique_users = snapshot.get("unique_users", "N/A")
    touched = snapshot.get("pipeline_touched")
    if touched is None:
        touched = snapshot.get("touched_amount", "N/A")
    closed = snapshot.get("closed_amount", "N/A")
    cost = snapshot.get("total_cost", "N/A")
    snapshot_date = raw_snapshot.get("snapshot_at") or raw_snapshot.get("snapshot_date", "N/A")

    def fmt_dollar(val):
        if isinstance(val, (int, float)):
            return f"${val:,.0f}"
        if isinstance(val, str) and val != "N/A":
            return f"${val}"
        return str(val)

    description = (
        f"*CI Name:* {display_name}\n\n"
        f"*RHDP URL:* {catalog_base}/{base_name}.prod\n\n"
        f"*AgV:* {agv_ref}\n\n"
        f"*Retirement Notice:* {target_days} days\n\n"
        f"*Replacement CI:* {replacement_line}\n\n"
        f"*Reason & Notes:*\n\n"
        f"{chr(10).join(notes_lines)}\n\n"
        f"*Metrics at approval (snapshot {snapshot_date}):*\n\n"
        f"||Metric||Value||\n"
        f"|Performance Score|{score}|\n"
        f"|Provisions|{provisions}|\n"
        f"|Experiences|{experiences}|\n"
        f"|Unique Users|{unique_users}|\n"
        f"|Pipeline Touched|{fmt_dollar(touched)}|\n"
        f"|Closed Amount|{fmt_dollar(closed)}|\n"
        f"|Total Cost|{fmt_dollar(cost)}|"
    )

    return description


def create_retirement_ticket(
    settings,
    workflow: dict,
    metrics: dict,
) -> str:
    """Create a Jira retirement ticket.

    Returns the new Jira issue key (e.g. "RHDPCD-999").
    """
    display_name = metrics.get("display_name", _base_name_from_content_id(workflow.get("content_id", "")) or "unknown")
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
    parent = settings.jira_retirement_parent
    if parent and parent.upper().startswith(f"{project_key}-"):
        create_body["fields"]["parent"] = {"key": parent}

    result = _jira_request(settings, "/rest/api/2/issue", body=create_body)
    issue_key = result["key"]

    logger.info("retirement_ticket_created", issue_key=issue_key, parent=create_body["fields"].get("parent"))

    # The retirement is underway once the ticket exists; it stays In Progress until closed.
    _move_to_in_progress(settings, issue_key)

    return issue_key


def _move_to_in_progress(settings, jira_key: str) -> None:
    """Best effort: the ticket already exists, so a failed transition must not fail the start."""
    try:
        resp = _jira_request(settings, f"/rest/api/2/issue/{jira_key}/transitions", method="GET")
        target = next((t for t in (resp or {}).get("transitions", [])
                       if t["to"]["name"].lower() == "in progress"), None)
        if not target:
            logger.warning("jira_no_in_progress_transition", jira_key=jira_key)
            return
        _jira_request(settings, f"/rest/api/2/issue/{jira_key}/transitions",
                      body={"transition": {"id": target["id"]}})
        logger.info("jira_moved_to_in_progress", jira_key=jira_key)
    except Exception as exc:
        logger.warning("jira_in_progress_transition_failed", jira_key=jira_key, error=str(exc))


def _issue_is_closed(issue: dict) -> bool:
    fields = (issue or {}).get("fields", {})
    status = fields.get("status") or {}
    terminal = (status.get("statusCategory") or {}).get("key") == "done" or status.get("name", "").lower() in ("done", "closed")
    return terminal and bool(fields.get("resolution"))


def _close_issue(settings, jira_key: str, resolution: str) -> bool:
    """Confirm closure, preserving an already-closed issue's resolution."""
    issue_path = f"/rest/api/2/issue/{jira_key}?fields=status,resolution"
    if _issue_is_closed(_jira_request(settings, issue_path, method="GET")):
        return True
    resp = _jira_request(settings, f"/rest/api/2/issue/{jira_key}/transitions", method="GET")
    target = None
    for t in (resp or {}).get("transitions", []):
        if (t["to"].get("statusCategory") or {}).get("key") == "done" or t["to"]["name"].lower() in ("done", "closed"):
            target = t
            break
    if not target:
        logger.warning("jira_no_closing_transition", jira_key=jira_key)
        return False

    _jira_request(settings, f"/rest/api/2/issue/{jira_key}/transitions", body={
        "transition": {"id": target["id"]},
        "fields": {"resolution": {"name": resolution}},
    })
    confirmed = _jira_request(settings, issue_path, method="GET")
    actual_resolution = ((confirmed or {}).get("fields", {}).get("resolution") or {}).get("name")
    if not _issue_is_closed(confirmed) or actual_resolution != resolution:
        raise RuntimeError(f"Jira closure not confirmed for {jira_key}")
    logger.info("jira_closed", jira_key=jira_key, resolution=resolution)
    return True


def close_issue_wont_do(settings, jira_key: str) -> bool:
    """Confirm cancellation closure; False means no closing transition exists."""
    return _close_issue(settings, jira_key, "Won't Do")


def close_issue_done(settings, jira_key: str) -> bool:
    """Confirm successful-retirement closure with the Done resolution."""
    return _close_issue(settings, jira_key, "Done")


def get_issue_status(settings, jira_key: str) -> dict:
    """Return {status, resolution} for a Jira issue."""
    resp = _jira_request(settings, f"/rest/api/2/issue/{jira_key}?fields=status,resolution", method="GET")
    fields = (resp or {}).get("fields", {})
    status = (fields.get("status") or {}).get("name")
    resolution = (fields.get("resolution") or {}).get("name")
    return {"status": status, "resolution": resolution}
