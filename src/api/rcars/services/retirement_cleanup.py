"""Required, retryable external cleanup shared by API and nightly maintenance."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone

import structlog

from rcars.services import agv_access, jira

logger = structlog.get_logger(component="retirement_cleanup")


class CleanupError(RuntimeError):
    """External cleanup is incomplete; tracking must be retained."""


def workflow_lock_id(content_id: str) -> int:
    return int.from_bytes(hashlib.blake2b(f"retirement:{content_id}".encode(), digest_size=8).digest(), signed=True)


def _base_name(content_id: str) -> str:
    name = content_id.removeprefix("babylon:")
    for suffix in (".prod", ".dev", ".event", ".test"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


async def _pr_state(settings, url: str) -> dict:
    parts = url.rstrip("/").split("/")
    return await agv_access.get_pr_state(settings, f"{parts[-4]}/{parts[-3]}", int(parts[-1]))


async def _close_open_pr(settings, url: str) -> dict:
    state = await _pr_state(settings, url)
    if state["state"] == "open":
        parts = url.rstrip("/").split("/")
        await agv_access.close_pr(settings, f"{parts[-4]}/{parts[-3]}", int(parts[-1]))
    return state


async def _close_jira(db, settings, wf: dict, *, cancelled: bool, jira_available: bool = True) -> None:
    if not wf.get("jira_key") or wf.get("jira_closed_at"):
        return
    if not jira_available:
        raise CleanupError("Jira cleanup pending: integration not configured")
    close = jira.close_issue_wont_do if cancelled else jira.close_issue_done
    if not await asyncio.to_thread(close, settings, wf["jira_key"]):
        raise CleanupError("Jira has no available closing transition; cleanup retained for retry")
    db.update_retirement_cleanup(wf["content_id"], {"jira_closed_at": datetime.now(timezone.utc)})
    db.log_action(_base_name(wf["content_id"]), "retirement_jira_closed", "cleanup",
                  f"Jira: closed ({wf['jira_key']}); outcome: {'cancelled' if cancelled else 'retired'}")


async def cancel_retirement(
    db, settings, content_id: str, actor: str, *,
    github_available: bool = True, jira_available: bool = True,
) -> dict:
    """Retain intent until PR cleanup AND Jira closure are complete."""
    wf = db.get_retirement_workflow(content_id)
    if not wf:
        return {"status": "ok", "deleted": True, "revert_pr_urls": []}
    if not wf.get("cancellation_requested_at"):
        db.update_retirement_cleanup(content_id, {"cancellation_requested_at": datetime.now(timezone.utc)})
    with db.advisory_lock(workflow_lock_id(content_id)) as acquired:
        if not acquired:
            raise CleanupError("Retirement cleanup is already running; retry shortly")
        wf = db.get_retirement_workflow(content_id)
        if not wf:
            return {"status": "ok", "deleted": True, "revert_pr_urls": []}
        try:
            if not github_available and any(wf.get(key) for key in (
                "agv_retire_pr_url", "agv_notice_pr_url", "agv_revert_pr_url",
            )):
                raise CleanupError("GitHub cleanup pending: integration not configured")
            # Always stop the destructive proposal before exposing a cancellation revert.
            if wf.get("agv_retire_pr_url"):
                await _close_open_pr(settings, wf["agv_retire_pr_url"])
            revert_url = wf.get("agv_revert_pr_url")
            if wf.get("agv_notice_pr_url"):
                notice = await _close_open_pr(settings, wf["agv_notice_pr_url"])
                if notice["merged"] and not revert_url:
                    result = await agv_access.revert_notice_pr(settings, _base_name(content_id), wf.get("jira_key") or "")
                    if result:
                        revert_url = result["pr_url"]
                        db.update_retirement_cleanup(content_id, {"agv_revert_pr_url": revert_url})
            await _close_jira(db, settings, wf, cancelled=True, jira_available=jira_available)
            if db.get_retirement_workflow(content_id) is None:
                return {"status": "ok", "deleted": True, "revert_pr_urls": [revert_url] if revert_url else []}
            pending = False
            if revert_url:
                revert = await _pr_state(settings, revert_url)
                pending = not revert["merged"]
                if pending and revert["state"] != "open":
                    raise CleanupError("Cancellation revert is closed without merging; manual recovery required")
            updated = db.update_retirement_cleanup(content_id, {"cleanup_error": None})
            if pending and updated:
                return {"status": "pending_revert", "deleted": False, "revert_pr_urls": [revert_url], "workflow": updated}
            deleted = db.delete_retirement_workflow(content_id)
            if deleted:
                db.log_action(_base_name(content_id), "retirement_cancelled", actor,
                              f"GitHub cleanup complete; Jira: {'closed' if wf.get('jira_key') else 'not linked'}")
            return {"status": "ok", "deleted": True, "revert_pr_urls": [revert_url] if revert_url else []}
        except Exception as exc:
            message = str(exc) if isinstance(exc, CleanupError) else "External cleanup failed; workflow retained for retry"
            db.update_retirement_cleanup(content_id, {"cleanup_error": message})
            logger.warning("retirement_cancel_cleanup_failed", content_id=content_id, error=str(exc))
            raise CleanupError(message) from exc


async def complete_retirement(
    db, settings, content_id: str, actor: str, *, jira_available: bool = True,
) -> bool:
    """Record physical retirement and close Jira, including retries of retired rows."""
    with db.advisory_lock(workflow_lock_id(content_id)) as acquired:
        if not acquired:
            raise CleanupError("Retirement cleanup is already running; retry shortly")
        wf = db.get_retirement_workflow(content_id)
        if not wf or wf.get("cancellation_requested_at") or wf.get("agv_revert_pr_url"):
            return False
        completed = bool(db.auto_close_retired_workflows({content_id}))
        try:
            await _close_jira(db, settings, wf, cancelled=False, jira_available=jira_available)
            db.update_retirement_cleanup(content_id, {"cleanup_error": None})
        except Exception as exc:
            message = str(exc) if isinstance(exc, CleanupError) else "Jira retirement closure failed; retry required"
            db.update_retirement_cleanup(content_id, {"cleanup_error": message})
            logger.warning("retirement_jira_completion_failed", content_id=content_id, error=str(exc))
            raise CleanupError(message) from exc
        if completed:
            db.log_action(_base_name(content_id), "retirement_completed", actor, "Retirement and Jira cleanup complete")
        return completed
