"""Retirement event identity/copy and durable Jira comment delivery."""
from __future__ import annotations

import hashlib
import json
import asyncio
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger(component="retirement_jira_events")
PR_KINDS = {"agv_notice_pr_url": "notice", "agv_retire_pr_url": "removal"}


def event_timestamp(value) -> datetime | None:
    if not value:
        return None
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        return None


def build_jira_event(wf: dict, event_type: str, event_at, pr_url: str | None = None) -> dict | None:
    """Build immutable event data; never infer historical GitHub event times."""
    if not wf.get("jira_key"):
        return None
    at = event_timestamp(event_at)
    cutoff = event_timestamp(wf.get("jira_event_tracking_started_at"))
    if at is None or cutoff is None:
        logger.warning("retirement_event_timestamp_missing", content_id=wf["content_id"], event_type=event_type)
        return None
    if at < cutoff:
        return None
    name = wf["content_id"].removeprefix("babylon:")
    for suffix in (".prod", ".event", ".dev", ".test"):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    if event_type in ("workflow_completed", "workflow_cancelled"):
        outcome = "completed" if event_type == "workflow_completed" else "cancelled"
        lines = [f"RCARS retirement workflow {outcome} for {name}."]
        for field, label in (("agv_notice_pr_url", "Notice PR"), ("agv_retire_pr_url", "Removal PR"), ("agv_revert_pr_url", "Cancellation revert PR")):
            if wf.get(field):
                lines.append(f"{label}: {wf[field]}")
        message = "\n".join(lines)
    else:
        kind, _, state = event_type.partition("_pr_")
        if kind not in ("notice", "removal") or state not in ("opened", "merged", "closed") or not pr_url:
            raise ValueError("Invalid retirement Jira event")
        outcome = "closed without merging" if state == "closed" else state
        message = f"RCARS retirement for {name}: {kind.capitalize()} PR {outcome}.\n{pr_url}"
    identity = [wf["content_id"], wf["created_at"].isoformat(), event_type, pr_url, at.isoformat()]
    return {
        "event_key": hashlib.sha256(json.dumps(identity).encode()).hexdigest(),
        "content_id": wf["content_id"], "workflow_created_at": wf["created_at"],
        "jira_key": wf["jira_key"], "event_type": event_type,
        "event_at": at, "pr_url": pr_url, "message": message,
    }


async def deliver_pending_events(db, settings, *, content_id: str | None = None) -> list[str]:
    """Notification errors cannot turn a successful lifecycle action into failure."""
    try:
        return await _deliver_pending_events(db, settings, content_id=content_id)
    except Exception as exc:
        logger.warning("retirement_jira_delivery_state_failed", error_type=type(exc).__name__)
        return ["Jira comments pending: delivery state unavailable"]


async def observe_pr_events(db, settings, wf: dict) -> dict[str, dict]:
    """Observe notice/removal transitions; return states for cleanup to reuse."""
    from rcars.services.agv_access import get_pr_state
    states = {}
    for field in PR_KINDS:
        url = wf.get(field)
        if not url:
            continue
        try:
            parts = url.rstrip("/").split("/")
            state = await get_pr_state(settings, f"{parts[-4]}/{parts[-3]}", int(parts[-1]))
            db.record_retirement_pr_state(wf["content_id"], field, {"url": url, **state})
            states[url] = state
        except Exception as exc:
            logger.warning("retirement_pr_observation_failed", content_id=wf["content_id"], error_type=type(exc).__name__)
            states[url] = {"error": "GitHub PR status observation failed; retry pending"}
    return states


async def _deliver_pending_events(db, settings, *, content_id: str | None = None) -> list[str]:
    """Best-effort delivery, durable retries, and independent per-incarnation ordering."""
    from rcars.services.jira import ensure_issue_event_comment

    pending = db.list_pending_retirement_jira_events(content_id=content_id)
    streams = dict.fromkeys((event["content_id"], event["workflow_created_at"]) for event in pending)
    errors = []
    for cid, created_at in streams:
        identity = f"retirement-jira-delivery:{cid}:{created_at.isoformat()}"
        lock_id = int.from_bytes(hashlib.blake2b(identity.encode(), digest_size=8).digest(), signed=True)
        with db.advisory_lock(lock_id) as acquired:
            if not acquired:
                continue
            # A concurrent sender may have finished while this caller waited.
            stream = [event for event in db.list_pending_retirement_jira_events(content_id=cid) if event["workflow_created_at"] == created_at]
            for event in stream[:20]:
                try:
                    comment_id = await asyncio.to_thread(
                        ensure_issue_event_comment, settings, event["jira_key"], event["event_key"], event["message"],
                    )
                    db.update_retirement_jira_event(event["event_key"], comment_id=comment_id)
                    logger.info("retirement_jira_comment_delivered", event_key=event["event_key"], jira_key=event["jira_key"], comment_id=comment_id)
                except Exception as exc:
                    configured = bool(settings.jira_api_email and settings.jira_api_token)
                    message = "Jira comment delivery failed; retry pending" if configured else "Jira comment delivery pending: integration not configured"
                    db.update_retirement_jira_event(event["event_key"], error=message)
                    errors.append(f"{event['jira_key']}: {message}")
                    logger.warning("retirement_jira_comment_deferred", event_key=event["event_key"], error_type=type(exc).__name__)
                    break
    return errors
