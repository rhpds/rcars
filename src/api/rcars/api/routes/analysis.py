"""Analysis routes — scan, stale check, rescan, single-item analysis, retirement."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from rcars.api.middleware.auth import require_admin, require_curator, require_auth, require_performance_view
from rcars.api.schemas import (
    JobResponse, PerformanceDashboardResponse, RetirementDashboardResponse,
    WorkflowResponse, WorkflowGetResponse, StartRetirementResponse,
    CancelWorkflowResponse, AgvPrResponse, RetirementPrStatusResponse, ScanResponse, RescanResponse,
    FieldSourceResponse, FieldSourceRepo, FieldSourceProvision,
)
from rcars.api.streaming import JobProgressRelay, create_sse_response
from rcars.config import Settings
from rcars.db.overlap import get_overlap_items, get_overlap_stats
from rcars.services.overlap_assessment import assess_overlap
from rcars.services.analyzer import order_for_reuse
import structlog

logger = structlog.get_logger(component="api")

router = APIRouter(prefix="/analysis")


WINDOWS = {"3m", "6m", "9m", "12m"}
CHANNEL_SOURCES = {"sales": "rhdp", "marketing": "interactive_labs"}


def _sort_empty_last(items: list[dict], key, reverse: bool) -> None:
    """Sort in place by a string key; items whose key is empty stay at the end in either direction."""
    keyed = [i for i in items if key(i)]
    empty = [i for i in items if not key(i)]
    keyed.sort(key=key, reverse=reverse)
    items[:] = keyed + empty


def _base_name_to_content_id(base_name: str, db, *, include_retired: bool = False) -> str | None:
    """Resolve a catalog base name (e.g. 'ocp4-getting-started') to a content_id.

    Tries common stage suffixes via the DB lookup. Returns content_id or None.
    """
    result = db.resolve_base_names_to_content_ids({base_name}, include_retired=include_retired)
    return result.get(base_name)


def _extract_base_name_from_content_id(content_id: str) -> str:
    """Derive a catalog_base_name from a content_id for backward compatibility.

    content_id format: 'babylon:some-name.stage' → base_name: 'some-name'
    """
    name = content_id
    if name.startswith("babylon:"):
        name = name[len("babylon:"):]
    # Strip known stage suffixes
    for suffix in (".prod", ".event", ".dev", ".test"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def _resolve_replacement_source(db, replacement_ci: str) -> tuple[str | None, str | None]:
    """Look up source and full CI name for a replacement item.

    Returns (replacement_source, replacement_ci_full).
    """
    repl = db.get_content_entity(replacement_ci)
    if repl:
        return repl["source"], None
    bi = db.get_babylon_item_by_ci_name(replacement_ci)
    if not bi:
        for sfx in (".prod", ".event", ".dev"):
            bi = db.get_babylon_item_by_ci_name(f"{replacement_ci}{sfx}")
            if bi:
                break
    if bi:
        return "babylon", bi["ci_name"]
    return None, None


class ApproveRequest(BaseModel):
    reason: str = Field(min_length=1)
    replacement_ci: str | None = None
    replacement_name: str | None = None

class StartRequest(BaseModel):
    target_days: int = Field(default=30, description="Days until the target date; zero requests immediate retirement")
    jira_project: str = "RHDPCD"

class NotesRequest(BaseModel):
    notes: str = Field(max_length=5000)

class LinkJiraRequest(BaseModel):
    jira_key: str = Field(min_length=1, pattern=r"^[A-Z][A-Z0-9]+-\d+$")


@router.get(
    "/performance",
    tags=["Performance"],
    summary="Performance dashboard",
    description=(
        "Returns catalog items scored for performance based on usage, cost, and sales impact. "
        "Supports filtering by score threshold, category, production status, time window (3m/6m/9m/12m), and channel (sales/marketing)."
    ),
    response_model=PerformanceDashboardResponse,
)
async def performance_dashboard(
    request: Request,
    user: str = Depends(require_performance_view),
    sort_by: str = Query("performance_score"),
    sort_dir: str = Query("desc"),
    min_score: int | None = Query(None),
    category: str | None = Query(None),
    has_prod: bool | None = Query(None),
    search: str | None = Query(None),
    window: str = Query("12m"),
    channel: str = Query("sales"),
    workflow_status: str | None = Query(None),
    include_retired: str = Query("false"),
):
    if window not in WINDOWS:
        raise HTTPException(400, f"window must be one of {sorted(WINDOWS)}")
    if channel not in CHANNEL_SOURCES:
        raise HTTPException(400, f"channel must be one of {sorted(CHANNEL_SOURCES)}")
    source = CHANNEL_SOURCES[channel]

    db = request.app.state.db

    settings: Settings = request.app.state.settings
    if not settings.is_curator(user) and not settings.is_admin(user):
        include_retired = "false"

    items = db.list_performance_data(
        sort_by=sort_by, sort_dir=sort_dir,
        category=category,
        has_prod=has_prod, search=search,
        workflow_status=workflow_status,
        channel=source,
        include_retired=include_retired,
    )

    import json as _json
    for item in items:
        # Backward-compat: derive catalog_base_name from content_id
        item["catalog_base_name"] = _extract_base_name_from_content_id(item.get("content_id", ""))

        # Apply windowed metrics overlay
        wm = item.get("windowed_metrics") or {}
        if isinstance(wm, str):
            try:
                wm = _json.loads(wm)
            except (ValueError, TypeError):
                wm = {}
        item["windowed_metrics"] = wm
        w = wm.get(window, {})
        if w:
            item["provisions"] = w.get("provisions", 0)
            item["experiences"] = w.get("experiences", 0)
            item["requests"] = w.get("requests", 0)
            item["unique_users"] = w.get("unique_users", 0)
            item["success_ratio"] = w.get("success_ratio", 0)
            item["failure_ratio"] = w.get("failure_ratio", 0)
            item["pipeline_touched"] = w.get("pipeline_touched", 0)
            item["closed_amount"] = w.get("closed_amount", 0)
            item["total_cost"] = w.get("total_cost", 0)
            item["avg_cost_per_provision"] = w.get("avg_cost_per_provision", 0)
            item["performance_score"] = w.get("performance_score", 0)
            item["sales_impact"] = w.get("sales_impact", "low")
            item["extrapolated"] = w.get("extrapolated", False)
            item["active_months"] = w.get("active_months")
        else:
            item["provisions"] = 0
            item["experiences"] = 0
            item["requests"] = 0
            item["unique_users"] = 0
            item["success_ratio"] = 0
            item["failure_ratio"] = 0
            item["pipeline_touched"] = 0
            item["closed_amount"] = 0
            item["total_cost"] = 0
            item["avg_cost_per_provision"] = 0
            item["performance_score"] = 0
            item["sales_impact"] = "low"

        if channel != "sales":
            item["performance_score"] = w.get("performance_score", 0)

    base_names = [i["catalog_base_name"] for i in items]
    stages_map = db.get_stages_for_base_names(base_names, include_retired=include_retired in ("true", "only", True))
    owners_map = db.get_owners_for_base_names(base_names)

    from rcars.services.reporting_sync import compute_sales_impact
    for item in items:
        stages = stages_map.get(item["catalog_base_name"], [])
        item["stages"] = stages
        item["owners"] = owners_map.get(item["catalog_base_name"], [])
        if "sales_impact" not in item:
            item["sales_impact"] = compute_sales_impact(float(item.get("closed_amount", 0) or 0))

    # Re-sort by frontend sort names (DB sorted by DB column names, may differ)
    allowed_sorts = {"performance_score", "provisions", "total_cost", "closed_amount", "pipeline_touched", "display_name",
                     "touched_roi", "closed_roi", "channels"}
    if sort_by in allowed_sorts:
        reverse = sort_dir.lower() == "desc"
        if sort_by == "channels":
            items.sort(key=lambda i: (len(i.get("channels_present") or []), ",".join(sorted(i.get("channels_present") or []))),
                       reverse=reverse)
        elif sort_by == "touched_roi":
            items.sort(key=lambda i: (i.get("pipeline_touched") or 0) / max(i.get("total_cost") or 1, 0.01), reverse=reverse)
        elif sort_by == "closed_roi":
            items.sort(key=lambda i: (i.get("closed_amount") or 0) / max(i.get("total_cost") or 1, 0.01), reverse=reverse)
        elif sort_by == "display_name":
            items.sort(key=lambda i: (i.get(sort_by) or ""), reverse=reverse)
        else:
            items.sort(key=lambda i: (i.get(sort_by) or 0), reverse=reverse)

    if min_score is not None:
        items = [i for i in items if (i.get("performance_score") or 0) >= min_score]

    from datetime import date as _date
    today = _date.today()
    for item in items:
        wm = item.pop("windowed_metrics", None) or {}
        if isinstance(wm, str):
            wm = _json.loads(wm)
        w = wm.get(window, {})
        item["score_breakdown"] = w.get("score_breakdown") or item.get("score_breakdown")

        iu = item.get("ignored_until")
        if iu and isinstance(iu, _date) and iu >= today:
            item["ignored_until"] = iu.isoformat()
        elif iu and isinstance(iu, str) and iu >= today.isoformat():
            pass
        else:
            item["ignored_until"] = None

    # Marketing addendum: when viewing sales channel, add marketing metrics if available
    if channel == "sales":
        marketing_ids = [i["content_id"] for i in items
                         if "interactive_labs" in (i.get("channels_present") or [])]
        marketing_map = db.get_channel_metrics_map(marketing_ids, "interactive_labs")
        for item in items:
            mrow = marketing_map.get(item["content_id"])
            item["marketing"] = None
            if mrow:
                mrow_wm = mrow.get("windowed_metrics") or {}
                if isinstance(mrow_wm, str):
                    try:
                        mrow_wm = _json.loads(mrow_wm)
                    except (ValueError, TypeError):
                        mrow_wm = {}
                mw = mrow_wm.get(window, {})
                item["marketing"] = {
                    "provisions": mw.get("provisions", mrow.get("provisions", 0)),
                    "unique_users": mw.get("unique_users", mrow.get("unique_users", 0)),
                    "experiences": mw.get("experiences", mrow.get("experiences", 0)),
                    "page_views": mrow.get("page_views", 0),
                    "score": mw.get("performance_score"),
                }
    else:
        # When viewing marketing channel, add sales metrics if available
        sales_ids = [i["content_id"] for i in items
                     if "rhdp" in (i.get("channels_present") or [])]
        sales_map = db.get_channel_metrics_map(sales_ids, "rhdp")
        for item in items:
            srow = sales_map.get(item["content_id"])
            item["sales"] = None
            if srow:
                srow_wm = srow.get("windowed_metrics") or {}
                if isinstance(srow_wm, str):
                    try:
                        srow_wm = _json.loads(srow_wm)
                    except (ValueError, TypeError):
                        srow_wm = {}
                sw = srow_wm.get(window, {})
                item["sales"] = {
                    "provisions": sw.get("provisions", srow.get("provisions", 0)),
                    "unique_users": sw.get("unique_users", srow.get("unique_users", 0)),
                    "experiences": sw.get("experiences", srow.get("experiences", 0)),
                    "page_views": srow.get("page_views", 0),
                    "pipeline_touched": float(sw.get("pipeline_touched") or 0),
                    "closed_amount": float(sw.get("closed_amount") or 0),
                    "total_cost": float(sw.get("total_cost") or 0),
                    "score": sw.get("performance_score"),
                }

    sync_status = db.get_reporting_sync_status()
    return {
        "items": items,
        "total": len(items),
        "synced_at": str(sync_status["last_synced"]) if sync_status and sync_status.get("last_synced") else None,
        "summary": sync_status,
        "window": window,
        "channel": channel,
    }


@router.get(
    "/retirement/workflow/{base_name}",
    tags=["Retirement"],
    summary="Get retirement workflow",
    description="Returns the current retirement workflow state for a catalog item. Curator-only.",
    response_model=WorkflowGetResponse,
)
async def get_workflow(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    wf = db.get_retirement_workflow(content_id) if content_id else None
    return {"workflow": wf}


@router.put(
    "/retirement/workflow/{base_name}/review",
    tags=["Retirement"],
    summary="Mark item as reviewed",
    description="Marks a catalog item as reviewed in the retirement workflow. Curator-only.",
    response_model=WorkflowResponse,
)
async def review_item(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"No content found for base name: {base_name}")
    fields = {
        "step_reviewed_at": "NOW()",
        "step_reviewed_by": user,
        "status": "reviewed",
    }
    result = db.upsert_retirement_workflow(content_id, fields)
    db.log_action(base_name, "retirement_reviewed", user, "Marked as reviewed")
    return {"status": "ok", "workflow": result}


@router.put(
    "/retirement/workflow/{base_name}/approve",
    tags=["Retirement"],
    summary="Recommend item for retirement",
    description=(
        "Records a retirement recommendation with a reason and optional replacement; does not authorize removal. "
        "Captures a snapshot of current metrics at approval time. Curator-only."
    ),
    response_model=WorkflowResponse,
)
async def approve_item(base_name: str, body: ApproveRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    from datetime import datetime

    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"No content found for base name: {base_name}")

    # Build channel-keyed approval snapshot from performance data
    perf_score = db.get_performance_score(content_id)
    perf_channels = db.get_performance_channels(content_id) or []
    channel_scores = (perf_score or {}).get("channel_scores") or {}
    snapshot: dict = {"snapshot_at": datetime.now().isoformat()}
    for ch in perf_channels:
        key = "sales" if ch.get("channel") == "rhdp" else "marketing"
        snapshot[key] = {
            "score": ((perf_score or {}).get("performance_score", 0) if key == "sales"
                      else (channel_scores.get(ch.get("channel"), {}) or {}).get("score", 0)),
            "provisions": ch.get("provisions", 0),
            "unique_users": ch.get("unique_users", 0),
            "experiences": ch.get("experiences", 0),
            "pipeline_touched": float(ch.get("pipeline_touched") or 0),
            "closed_amount": float(ch.get("closed_amount") or 0),
            "total_cost": float(ch.get("total_cost") or 0),
            "page_views": ch.get("page_views", 0),
        }

    fields = {
        "step_reviewed_at": "NOW()",
        "step_reviewed_by": user,
        "step_approved_at": "NOW()",
        "step_approved_by": user,
        "approval_reason": body.reason,
        "approval_snapshot": snapshot,
        "status": "approved",
    }
    if body.replacement_ci:
        fields["replacement_ci"] = body.replacement_ci
        fields["replacement_name"] = body.replacement_name

    result = db.upsert_retirement_workflow(content_id, fields)
    db.log_action(base_name, "retirement_approved", user, f"Reason: {body.reason}")
    return {"status": "ok", "workflow": result}


@router.put(
    "/retirement/workflow/{base_name}/notify",
    tags=["Retirement"],
    summary="Mark owner as notified",
    description="Records manual owner notification; does not send email or chat. Admin-only.",
    response_model=WorkflowResponse,
)
async def notify_owner(base_name: str, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"No content found for base name: {base_name}")
    fields = {
        "step_notified_at": "NOW()",
        "step_notified_by": user,
        "status": "notified",
    }
    result = db.upsert_retirement_workflow(content_id, fields)
    db.log_action(base_name, "retirement_notified", user, "Owner notified")
    return {"status": "ok", "workflow": result}


@router.put(
    "/retirement/workflow/{base_name}/start",
    tags=["Retirement"],
    summary="Start retirement process",
    description=(
        "Starts the retirement process: creates a Jira ticket and sets a target retirement date. "
        "Requires a prior recommendation. Does not open a notice PR automatically. Admin-only."
    ),
    response_model=StartRetirementResponse,
    responses={400: {"description": "Item must be approved before starting retirement"}},
)
async def start_retirement(base_name: str, body: StartRequest, request: Request, user: str = Depends(require_admin)):
    from rcars.services.retirement_cleanup import workflow_lock_id
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        raise HTTPException(404, f"No content found for base name: {base_name}")
    # API workers run as separate processes: without the lock, two starts can
    # both pass the not-started check and each create a Jira ticket.
    with db.advisory_lock(workflow_lock_id(content_id)) as acquired:
        if not acquired:
            raise HTTPException(409, "Retirement start or cleanup is already running")
        return _start_retirement_locked(base_name, content_id, body, request, user)


def _start_retirement_locked(base_name: str, content_id: str, body: StartRequest, request: Request, user: str):
    db = request.app.state.db
    settings = request.app.state.settings
    from datetime import datetime, timedelta

    wf = db.get_retirement_workflow(content_id)
    if not wf or not wf.get("step_approved_at"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Item must be approved before starting retirement")
    if wf.get("step_started_at"):
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=f"Retirement already started (Jira: {wf.get('jira_key', 'unknown')})")

    target_date = (datetime.now() + timedelta(days=body.target_days)).date()

    # Build metrics dict from performance data for Jira ticket
    perf_channels = db.get_performance_channels(content_id)
    rhdp = next((ch for ch in perf_channels if ch.get("channel") == "rhdp"), None) if perf_channels else None
    metrics = dict(rhdp) if rhdp else {}
    entity = db.get_content_entity(content_id)
    if entity and entity.get("display_name"):
        metrics["display_name"] = entity["display_name"]

    replacement_source, replacement_ci_full = None, None
    repl_ci = wf.get("replacement_ci")
    if repl_ci:
        replacement_source, replacement_ci_full = _resolve_replacement_source(db, repl_ci)

    wf_for_jira = {**wf, "jira_project": body.jira_project, "retirement_target_date": target_date, "target_days": body.target_days, "replacement_source": replacement_source, "replacement_ci_full": replacement_ci_full}

    from rcars.services.jira import create_retirement_ticket
    try:
        jira_key = create_retirement_ticket(settings, wf_for_jira, metrics)
    except Exception as exc:
        logger.error("retirement_jira_failed", base_name=base_name, content_id=content_id, error=str(exc))
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail=f"Failed to create Jira ticket: {exc}")

    fields = {
        "step_started_at": "NOW()",
        "step_started_by": user,
        "retirement_target_date": target_date.isoformat(),
        "jira_key": jira_key,
        "jira_project": body.jira_project,
        "status": "started",
    }
    result = db.upsert_retirement_workflow(content_id, fields)
    db.log_action(base_name, "retirement_started", user, f"Jira: {jira_key}, target: {target_date}")
    return {"status": "ok", "workflow": result, "jira_key": jira_key}


@router.put(
    "/retirement/workflow/{base_name}/link-jira",
    tags=["Retirement"],
    summary="Link existing Jira ticket",
    description="Links an existing Jira ticket and advances to started status. Requires a prior recommendation. Does not compute a target date. Admin-only.",
    response_model=WorkflowResponse,
    responses={400: {"description": "Item must be approved before linking Jira"}},
)
async def link_jira(base_name: str, body: LinkJiraRequest, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"No content found for base name: {base_name}")

    wf = db.get_retirement_workflow(content_id)
    if not wf or not wf.get("step_approved_at"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Item must be approved before linking a Jira ticket")
    if wf.get("step_started_at"):
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=f"Retirement already started (Jira: {wf.get('jira_key', 'unknown')})")

    fields = {
        "step_started_at": "NOW()",
        "step_started_by": user,
        "jira_key": body.jira_key,
        "status": "started",
    }
    result = db.upsert_retirement_workflow(content_id, fields)
    db.log_action(base_name, "retirement_jira_linked", user, f"Linked existing Jira: {body.jira_key}")
    return {"status": "ok", "workflow": result}


@router.put(
    "/retirement/workflow/{base_name}/notes",
    tags=["Retirement"],
    summary="Update curator notes",
    description="Sets or updates curator notes on a retirement workflow item. Curator-only.",
    response_model=WorkflowResponse,
)
async def update_notes(base_name: str, body: NotesRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"No content found for base name: {base_name}")
    fields = {"curator_notes": body.notes}
    result = db.upsert_retirement_workflow(content_id, fields)
    return {"status": "ok", "workflow": result}


@router.delete(
    "/retirement/workflow/{base_name}",
    tags=["Retirement"],
    summary="Cancel retirement workflow",
    description=(
        "Closes open removal/notice PRs and opens a notice revert if needed. GitHub cleanup failures return 502 "
        "and retain the workflow for retry. A pending revert returns pending_revert with deleted=false; "
        "reconciliation deletes the workflow only after GitHub cleanup and required Jira closure succeed. "
        "Already-retired catalog items or completed workflows cannot be cancelled (409). Admin-only."
    ),
    response_model=CancelWorkflowResponse,
    responses={
        409: {"description": "Item is already retired; cancellation is not allowed"},
        502: {"description": "Required Jira/GitHub cleanup failed; workflow retained for retry"},
    },
)
async def cancel_workflow(base_name: str, request: Request, user: str = Depends(require_admin)):
    from rcars.services.retirement_cleanup import cancel_retirement, CleanupError, RetirementAlreadyCompleted
    from rcars.services.retirement_jira_events import deliver_pending_events

    db = request.app.state.db
    settings = request.app.state.settings
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        raise HTTPException(404, f"No content found for base name: {base_name}")

    try:
        result = await cancel_retirement(db, settings, content_id, user)
    except RetirementAlreadyCompleted as exc:
        raise HTTPException(409, str(exc)) from exc
    except CleanupError as exc:
        await deliver_pending_events(db, settings, content_id=content_id)
        raise HTTPException(502, str(exc)) from exc
    result["jira_comment_errors"] = await deliver_pending_events(db, settings, content_id=content_id)
    return result


@router.post(
    "/retirement/workflow/{base_name}/agv-notice",
    tags=["Retirement"],
    summary="Open agnosticv retirement notice PR",
    description=(
        "Creates a branch on the relevant agnosticv repo, prepends the AsciiDoc "
        "retirement notice to description.adoc, and opens a PR. Idempotent: if a "
        "notice PR URL is already stored, returns it without creating a duplicate. "
        "Admin-only."
    ),
    response_model=AgvPrResponse,
)
async def open_agv_notice_pr(base_name: str, request: Request, user: str = Depends(require_admin)):
    from rcars.services.retirement_cleanup import workflow_lock_id
    from rcars.services.retirement_jira_events import deliver_pending_events
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        raise HTTPException(404, f"No content found for base name: {base_name}")
    with db.advisory_lock(workflow_lock_id(content_id)) as acquired:
        if not acquired:
            raise HTTPException(409, "Retirement cleanup or PR creation is already running")
        result = await _open_agv_notice_pr_locked(base_name, request, user)
    result["jira_comment_errors"] = await deliver_pending_events(db, request.app.state.settings, content_id=content_id)
    return result


async def _open_agv_notice_pr_locked(base_name: str, request: Request, user: str):
    from rcars.services.agv_access import create_notice_pr

    db = request.app.state.db
    settings = request.app.state.settings

    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        raise HTTPException(404, f"No content found for base name: {base_name}")

    wf = db.get_retirement_workflow(content_id)
    entity = db.get_content_entity(content_id)
    if (entity and entity.get("retired_at")) or (wf and (wf.get("step_retired_at") or wf.get("status") == "retired")):
        raise HTTPException(409, "This item is already retired; new retirement PRs cannot be created")
    if not wf or not wf.get("step_started_at"):
        raise HTTPException(400, "Retirement must be started (Jira ticket created) before opening the notice PR")
    if wf.get("cancellation_requested_at") or wf.get("agv_revert_pr_url"):
        raise HTTPException(409, "Cancellation cleanup is pending")

    if wf.get("agv_notice_pr_url"):
        return {
            "status": "ok",
            "workflow": wf,
            "pr_url": wf["agv_notice_pr_url"],
            "pr_number": 0,
            "repo": "",
        }

    repl_ci = wf.get("replacement_ci")
    if repl_ci:
        repl_source, repl_full = _resolve_replacement_source(db, repl_ci)
        if repl_source:
            wf = {**wf, "replacement_source": repl_source, "replacement_ci_full": repl_full}

    jira_key = wf.get("jira_key", "")
    try:
        result = await create_notice_pr(settings, base_name, jira_key, wf)
    except Exception as exc:
        logger.error("agv_notice_pr_failed", base_name=base_name, error=str(exc))
        raise HTTPException(502, f"Failed to create notice PR: {exc}") from exc

    updated = db.record_retirement_pr(content_id, "agv_notice_pr_url", result)
    db.log_action(base_name, "agv_notice_pr_opened", user, f"PR: {result['pr_url']}")
    return {"status": "ok", "workflow": updated, **result}


@router.post(
    "/retirement/workflow/{base_name}/agv-retire",
    tags=["Retirement"],
    summary="Open agnosticv removal PR",
    description=(
        "Creates a branch on the relevant agnosticv repo that deletes the CI folder. "
        "Opens a PR for human review. Admins may open it before the target date "
        "once retirement is started and a Jira ticket is linked. Admin-only."
    ),
    response_model=AgvPrResponse,
)
async def open_agv_retire_pr(base_name: str, request: Request, user: str = Depends(require_admin)):
    from rcars.services.retirement_cleanup import workflow_lock_id
    from rcars.services.retirement_jira_events import deliver_pending_events
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        raise HTTPException(404, f"No content found for base name: {base_name}")
    with db.advisory_lock(workflow_lock_id(content_id)) as acquired:
        if not acquired:
            raise HTTPException(409, "Retirement cleanup or PR creation is already running")
        result = await _open_agv_retire_pr_locked(base_name, request, user)
    result["jira_comment_errors"] = await deliver_pending_events(db, request.app.state.settings, content_id=content_id)
    return result


async def _open_agv_retire_pr_locked(base_name: str, request: Request, user: str):
    from rcars.services.agv_access import create_retire_pr

    db = request.app.state.db
    settings = request.app.state.settings

    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        raise HTTPException(404, f"No content found for base name: {base_name}")

    wf = db.get_retirement_workflow(content_id)
    entity = db.get_content_entity(content_id)
    if (entity and entity.get("retired_at")) or (wf and (wf.get("step_retired_at") or wf.get("status") == "retired")):
        raise HTTPException(409, "This item is already retired; new retirement PRs cannot be created")
    if not wf or not wf.get("step_started_at"):
        raise HTTPException(400, "Retirement must be started before opening the removal PR")
    if wf.get("cancellation_requested_at") or wf.get("agv_revert_pr_url"):
        raise HTTPException(409, "Cancellation cleanup is pending")

    if wf.get("agv_retire_pr_url"):
        return {
            "status": "ok",
            "workflow": wf,
            "pr_url": wf["agv_retire_pr_url"],
            "pr_number": 0,
            "repo": "",
        }

    jira_key = wf.get("jira_key", "")
    if not jira_key:
        raise HTTPException(400, "A Jira ticket must be linked before opening the removal PR")
    try:
        result = await create_retire_pr(settings, base_name, jira_key)
    except Exception as exc:
        logger.error("agv_retire_pr_failed", base_name=base_name, error=str(exc))
        raise HTTPException(502, f"Failed to create removal PR: {exc}") from exc

    updated = db.record_retirement_pr(content_id, "agv_retire_pr_url", result)
    db.log_action(base_name, "agv_retire_pr_opened", user, f"PR: {result['pr_url']}")
    return {"status": "ok", "workflow": updated, **result}


@router.post(
    "/retirement/workflow/{base_name}/check-prs",
    tags=["Retirement"],
    summary="Check agnosticv PR statuses",
    description="Checks PRs and reconciles required cleanup. Retirement closes Jira as Done; cancellation closes Jira as Won't Do and retains tracking until GitHub cleanup and any revert merge complete. Cleanup errors are returned with the retained workflow for retry. Admin-only.",
    response_model=RetirementPrStatusResponse,
)
async def check_pr_statuses(base_name: str, request: Request, user: str = Depends(require_admin)):
    from rcars.services.agv_access import get_pr_state
    from rcars.services.retirement_jira_events import deliver_pending_events, PR_KINDS

    db = request.app.state.db
    settings = request.app.state.settings
    content_id = _base_name_to_content_id(base_name, db, include_retired=True)
    if not content_id:
        raise HTTPException(404, f"No content found for base name: {base_name}")

    wf = db.get_retirement_workflow(content_id)
    if not wf:
        raise HTTPException(404, "No workflow found")

    def _parse_pr_url(url: str) -> tuple[str, int]:
        parts = url.rstrip("/").split("/")
        return f"{parts[-4]}/{parts[-3]}", int(parts[-1])

    pr_statuses: dict[str, dict] = {}
    for key in ("agv_notice_pr_url", "agv_retire_pr_url", "agv_revert_pr_url"):
        url = wf.get(key)
        if not url:
            continue
        try:
            repo_full, pr_number = _parse_pr_url(url)
            state = await get_pr_state(settings, repo_full, pr_number)
            pr_statuses[key] = {"url": url, "pr_number": pr_number, **state}
            if key in PR_KINDS:
                db.record_retirement_pr_state(content_id, key, {"url": url, **state})
        except Exception as exc:
            pr_statuses[key] = {"url": url, "error": str(exc)}

    jira_status = None
    jira_key = wf.get("jira_key")
    if jira_key:
        try:
            from rcars.services.jira import get_issue_status
            jira_status = await asyncio.to_thread(get_issue_status, settings, jira_key)
        except Exception as exc:
            jira_status = {"error": str(exc)}

    from rcars.services.retirement_cleanup import cancel_retirement, complete_retirement, CleanupError
    cleanup_error = None
    deleted = False
    try:
        if wf.get("cancellation_requested_at") or wf.get("agv_revert_pr_url"):
            result = await cancel_retirement(db, settings, content_id, user)
            deleted = result["deleted"]
        elif pr_statuses.get("agv_retire_pr_url", {}).get("merged") or wf.get("step_retired_at"):
            await complete_retirement(db, settings, content_id, user)
    except CleanupError as exc:
        cleanup_error = str(exc)
    wf = db.get_retirement_workflow(content_id)
    comment_errors = await deliver_pending_events(db, settings, content_id=content_id)
    return {"status": "ok", "deleted": deleted, "pr_statuses": pr_statuses, "jira_status": jira_status,
            "workflow": wf, "cleanup_error": cleanup_error, "jira_comment_errors": comment_errors}


@router.post(
    "/retirement/sweep",
    tags=["Retirement"],
    summary="Queue retirement PR creation and merge reconciliation",
    description=(
        "Scans retirement workflows for items whose target date has passed and "
        "no removal PR exists. Opens removal PRs on agnosticv for each. "
        "Reconciles merged removal PRs and cancellation reverts even when no removals are due. "
        "Returns a job_id; the scan worker performs the work and reports per-item errors. "
        "Also runs as part of the nightly maintenance pipeline. Admin-only."
    ),
    response_model=JobResponse,
)
async def retirement_sweep(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="retirement_sweep", queue="scan", created_by=user)
    await arq_redis.enqueue_job("run_retirement_sweep_job", job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


@router.post(
    "/scan",
    tags=["Content Analysis"],
    summary="Scan items needing analysis",
    description=(
        "Enqueues analysis jobs for all catalog items that need (re-)analysis. "
        "Schedules each eligible item stage independently, skipping complete unchanged items. Admin-only."
    ),
    response_model=ScanResponse,
)
async def start_scan(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis

    dedup_stats = db.get_scan_dedup_stats()
    settings = request.app.state.settings
    # Group leaders first so stage siblings reuse a finished donor instead of racing it.
    items = order_for_reuse(db.get_items_needing_analysis(settings), settings)

    parent_job_id = db.create_job(job_type="scan", queue="analyze", created_by=user)

    for item in items:
        sub_job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user,
                                   progress_json={"content_id": item["content_id"]})
        await arq_redis.enqueue_job(
            "run_analysis", job_id=sub_job_id, content_id=item["content_id"],
            _job_id=sub_job_id, _queue_name="arq:queue:scan"
        )

    result = {"enqueued": len(items), **dedup_stats}
    db.complete_job(parent_job_id, result_json=result)
    return {"job_id": parent_job_id, **result}


@router.post(
    "/check-stale",
    tags=["Content Analysis"],
    summary="Check for stale content",
    description="Checks all catalog items for content changes since last analysis. Admin-only.",
    response_model=JobResponse,
)
async def check_stale(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="check_stale", queue="ops", created_by=user)
    await arq_redis.enqueue_job("run_stale_check", job_id=job_id, _job_id=job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


@router.post(
    "/rescan-all",
    tags=["Content Analysis"],
    summary="Force rescan of entire catalog",
    description="Enqueues forced re-analysis for every resolved Babylon item stage. Admin-only.",
    response_model=RescanResponse,
)
async def rescan_all(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis

    items = db.get_items_needing_analysis(force=True)

    parent_job_id = db.create_job(job_type="rescan_all", queue="analyze", created_by=user)

    for item in items:
        sub_job_id = db.create_job(job_type="analyze", queue="analyze", created_by="rescan-all",
                                   progress_json={"content_id": item["content_id"]})
        await arq_redis.enqueue_job(
            "run_analysis", job_id=sub_job_id, content_id=item["content_id"],
            force=True,
            _job_id=sub_job_id, _queue_name="arq:queue:scan"
        )

    result = {"marked_stale": 0, "enqueued": len(items), "stage_jobs": len(items)}
    db.complete_job(parent_job_id, result_json=result)
    return {"job_id": parent_job_id, **result}


@router.put(
    "/performance/ignore/{base_name}",
    tags=["Performance"],
    summary="Ignore item for 30 days",
    description="Mutes a catalog item from the performance dashboard for 30 days. Curator-only.",
)
async def ignore_item(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    from datetime import date, timedelta
    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"Item not found: {base_name}")
    until = (date.today() + timedelta(days=30)).isoformat()
    ok = db.set_ignored_until(content_id, until)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(404, f"Item not found: {base_name}")
    db.log_action(base_name, "retirement_ignored", user, f"Muted until {until}")
    return {"status": "ok", "ignored_until": until}


@router.delete(
    "/performance/ignore/{base_name}",
    tags=["Performance"],
    summary="Un-ignore item",
    description="Removes the mute/ignore from a catalog item. Curator-only.",
)
async def unignore_item(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"Item not found: {base_name}")
    ok = db.clear_ignored(content_id)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(404, f"Item not found: {base_name}")
    db.log_action(base_name, "retirement_unignored", user, "Unmuted")
    return {"status": "ok"}


RETIREMENT_WINDOWS = {"6m", "12m"}


@router.get(
    "/retirement",
    tags=["Retirement"],
    summary="Retirement report dashboard",
    description="Returns items in retirement workflow or already retired, with usage metrics.",
    response_model=RetirementDashboardResponse,
)
async def retirement_dashboard(
    request: Request,
    user: str = Depends(require_curator),
    search: str | None = Query(None),
    window: str = Query("12m"),
):
    if window not in RETIREMENT_WINDOWS:
        raise HTTPException(400, f"window must be one of {sorted(RETIREMENT_WINDOWS)}")

    db = request.app.state.db
    raw_items = db.list_retirement_items(search=search)

    import json as _json

    # Derive base_name and deduplicate
    seen: dict[str, dict] = {}
    for item in raw_items:
        bn = _extract_base_name_from_content_id(item.get("content_id", ""))
        item["catalog_base_name"] = bn

        existing = seen.get(bn)
        if not existing:
            seen[bn] = item
        else:
            candidate_rank = (bool(item.get("workflow_raw_status")), item.get("provisions") or item.get("np_provisions") or 0)
            existing_rank = (bool(existing.get("workflow_raw_status")), existing.get("provisions") or existing.get("np_provisions") or 0)
            if candidate_rank > existing_rank:
                seen[bn] = item

    items = list(seen.values())

    # Apply windowed metrics + compute effective status
    for item in items:
        wm = item.pop("perf_windowed_metrics", None) or item.pop("np_windowed_metrics", None) or {}
        item.pop("perf_windowed_metrics", None)
        item.pop("np_windowed_metrics", None)
        if isinstance(wm, str):
            try:
                wm = _json.loads(wm)
            except (ValueError, TypeError):
                wm = {}
        w = wm.get(window, {})

        # Merge metrics: prefer perf, fall back to nonprod, then windowed
        # Use `is not None` — `or` treats 0 as falsy and pulls wrong values
        def _pref(a, b):
            return a if a is not None else (b if b is not None else 0)
        item["provisions"] = w.get("provisions", _pref(item.get("provisions"), item.get("np_provisions")))
        item["unique_users"] = w.get("unique_users", _pref(item.get("unique_users"), item.get("np_unique_users")))
        item["experiences"] = w.get("experiences", _pref(item.get("experiences"), item.get("np_experiences")))
        item["success_ratio"] = w.get("success_ratio", _pref(item.get("success_ratio"), item.get("np_success_ratio")))
        item["first_activity"] = item.get("first_activity") or item.get("first_provision")
        item["last_activity"] = item.get("last_activity") or item.get("last_provision")

        # Clean up intermediate fields
        for k in ("np_provisions", "np_unique_users", "np_experiences", "np_success_ratio",
                   "first_provision", "last_provision"):
            item.pop(k, None)

        # Score breakdown from windowed metrics if available
        item["score_breakdown"] = w.get("score_breakdown") or item.get("score_breakdown")
        ws = w.get("performance_score")
        item["performance_score"] = ws if ws is not None else item.get("performance_score")

        # Effective status for the frontend
        if item.get("retired_at") or item.get("step_retired_at"):
            item["effective_status"] = "retired"
        elif item.get("workflow_raw_status") in ("started",):
            item["effective_status"] = "in_progress"
        elif item.get("workflow_raw_status") in ("approved", "notified"):
            item["effective_status"] = "recommended"
        else:
            item["effective_status"] = "retired"

        # Serialize dates
        for key in ("retired_at", "step_reviewed_at", "step_approved_at", "step_notified_at",
                     "step_started_at", "step_retired_at", "retirement_target_date",
                     "workflow_created_at", "workflow_updated_at"):
            v = item.get(key)
            if v and not isinstance(v, str):
                item[key] = str(v)

        if item.get("approval_snapshot") and isinstance(item["approval_snapshot"], str):
            try:
                item["approval_snapshot"] = _json.loads(item["approval_snapshot"])
            except (ValueError, TypeError):
                pass

    # Enrich with stages
    base_names = [i["catalog_base_name"] for i in items]
    stages_map = db.get_stages_for_base_names(base_names, include_retired=True)
    for item in items:
        item["stages"] = stages_map.get(item["catalog_base_name"], [])

    earliest = db.get_earliest_retired_at()

    return {
        "items": items,
        "total": len(items),
        "earliest_retired_at": earliest,
        "window": window,
    }


NONPROD_WINDOWS = {"6m", "12m"}


@router.get(
    "/nonprod",
    tags=["Non-Prod Items"],
    summary="Non-prod items dashboard",
    description="Returns catalog items with no production stage, with usage metrics. Curator-only.",
)
async def nonprod_dashboard(
    request: Request,
    user: str = Depends(require_curator),
    sort_by: str = Query("provisions"),
    sort_dir: str = Query("desc"),
    content_type: str | None = Query(None),
    stage: str | None = Query(None),
    search: str | None = Query(None),
    window: str = Query("12m"),
    status: str | None = Query(None),
):
    if window not in NONPROD_WINDOWS:
        raise HTTPException(400, f"window must be one of {sorted(NONPROD_WINDOWS)}")

    db = request.app.state.db
    items = db.list_nonprod_items(
        sort_by=sort_by, sort_dir=sort_dir,
        content_type=content_type, stage=stage,
        search=search,
        status=status,
    )

    import json as _json
    from datetime import date as _date
    today = _date.today()

    # Collect all base_names for stage lookup
    base_names = [i["catalog_base_name"] for i in items]
    stages_map = db.get_stages_for_base_names(base_names, include_retired=False)

    for item in items:
        # Apply windowed metrics overlay
        wm = item.get("windowed_metrics") or {}
        if isinstance(wm, str):
            try:
                wm = _json.loads(wm)
            except (ValueError, TypeError):
                wm = {}
        w = wm.get(window, {})
        item["provisions"] = w.get("provisions", 0)
        item["total_provisions"] = w.get("total_provisions", 0)
        item["by_env"] = w.get("by_env", {})
        item["requests"] = w.get("requests", 0)
        item["experiences"] = w.get("experiences", 0)
        item["unique_users"] = w.get("unique_users", 0)
        item["success_ratio"] = w.get("success_ratio", 0)
        item["failure_ratio"] = w.get("failure_ratio", 0)
        item["extrapolated"] = w.get("extrapolated", False)
        item["active_months"] = w.get("active_months")

        # Enrich with stages from all variants of this base name
        item["stages"] = stages_map.get(item["catalog_base_name"], [])

        # Handle ignored_until
        iu = item.get("ignored_until")
        if iu and isinstance(iu, _date) and iu >= today:
            item["ignored_until"] = iu.isoformat()
        elif iu and isinstance(iu, str) and iu >= today.isoformat():
            pass
        else:
            item["ignored_until"] = None

    # Re-sort after windowed overlay
    allowed_sorts = {"provisions", "total_provisions", "experiences", "unique_users", "success_ratio", "failure_ratio",
                     "display_name", "content_type", "stages", "first_provision", "last_provision"}
    if sort_by in allowed_sorts:
        reverse = sort_dir.lower() == "desc"
        if sort_by == "display_name":
            items.sort(key=lambda i: (i.get(sort_by) or ""), reverse=reverse)
        elif sort_by == "content_type":
            _sort_empty_last(items, lambda i: (i.get("content_type") or "").lower(), reverse)
        elif sort_by == "stages":
            _sort_empty_last(items, lambda i: ", ".join(sorted(s["stage"] for s in i["stages"])), reverse)
        elif sort_by in ("first_provision", "last_provision"):
            _sort_empty_last(items, lambda i: str(i.get(sort_by) or ""), reverse)
        else:
            items.sort(key=lambda i: (i.get(sort_by) or 0), reverse=reverse)

    synced_at = max((i["synced_at"] for i in items if i.get("synced_at")), default=None) if items else None

    return {
        "items": items,
        "total": len(items),
        "synced_at": str(synced_at) if synced_at else None,
        "window": window,
    }


@router.put(
    "/nonprod/ignore/{base_name}",
    tags=["Non-Prod Items"],
    summary="Mute non-prod item for 30 days",
    description="Suppress a non-prod item from reports for 30 days. Curator only.",
)
async def nonprod_ignore(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    from datetime import date, timedelta
    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        raise HTTPException(404, f"Item not found: {base_name}")
    until = (date.today() + timedelta(days=30)).isoformat()
    ok = db.set_nonprod_ignored(content_id, until)
    if not ok:
        raise HTTPException(404, f"Item not found in nonprod_usage: {base_name}")
    db.log_action(base_name, "nonprod_muted", user, f"Muted until {until}")
    return {"status": "ok", "ignored_until": until}


@router.delete(
    "/nonprod/ignore/{base_name}",
    tags=["Non-Prod Items"],
    summary="Unmute non-prod item",
    description="Remove the 30-day mute from a non-prod item. Curator only.",
)
async def nonprod_unignore(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        raise HTTPException(404, f"Item not found: {base_name}")
    ok = db.clear_nonprod_ignored(content_id)
    if not ok:
        raise HTTPException(404, f"Item not found in nonprod_usage: {base_name}")
    db.log_action(base_name, "nonprod_unmuted", user, "Unmuted")
    return {"status": "ok"}


@router.get(
    "/overlap",
    summary="Content overlap report — verdict-based, paginated",
    description="Returns paginated overlap pairs with optional filters by verdict, stage, and shared product/topic counts.",
    tags=["Content Analysis"],
)
async def overlap_report(
    request: Request,
    user: str = Depends(require_auth),
    verdict: str | None = Query(None, description="redundant/complementary/differentiated/unassessed"),
    search: str | None = Query(None, description="Search by display name"),
    stage: str | None = Query(None, description="prod/event/dev"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    min_shared_products: int | None = Query(None, ge=0),
    min_shared_topics: int | None = Query(None, ge=0),
):
    db = request.app.state.db
    result = get_overlap_items(
        db.pool, verdict=verdict, search=search, stage=stage,
        page=page, page_size=page_size,
        min_shared_products=min_shared_products,
        min_shared_topics=min_shared_topics,
    )
    stats = get_overlap_stats(db.pool)
    return {**result, "stats": stats}


@router.post(
    "/overlap/assess",
    summary="On-demand overlap assessment for a pair",
    description="Triggers an LLM assessment of two items' overlap. Returns verdict (redundant/complementary/differentiated) and reasoning. Curator only.",
    tags=["Content Analysis"],
)
async def overlap_assess(
    request: Request,
    content_id_a: str = Query(...),
    content_id_b: str = Query(...),
    user: str = Depends(require_curator),
):
    db = request.app.state.db
    settings = Settings()
    import asyncio
    result, reason = await asyncio.to_thread(
        assess_overlap, db.pool, settings, content_id_a, content_id_b
    )
    return {"assessment": result, "reason": reason}


@router.get(
    "/overlap/{content_id_a}/{content_id_b}",
    summary="Get cached LLM overlap assessment for a pair",
    description="Returns the stored LLM assessment for an overlap pair, if one exists. Does not trigger a new assessment.",
    tags=["Content Analysis"],
)
async def overlap_assessment_detail(
    request: Request,
    content_id_a: str,
    content_id_b: str,
    user: str = Depends(require_auth),
):
    db = request.app.state.db
    a, b = (content_id_a, content_id_b) if content_id_a < content_id_b else (content_id_b, content_id_a)
    with db.pool.connection() as conn:
        from psycopg.rows import dict_row
        conn.row_factory = dict_row
        row = conn.execute(
            "SELECT llm_assessment, assessed_at FROM overlap_candidates WHERE content_id_a = %s AND content_id_b = %s",
            (a, b),
        ).fetchone()
    if not row:
        return {"assessment": None, "assessed_at": None, "reason": "not_overlap"}
    return {"assessment": row["llm_assessment"], "assessed_at": row["assessed_at"]}


@router.get(
    "/field-source",
    tags=["Field Source Content"],
    summary="Field source content report",
    description=(
        "Returns provisioned git repos grouped by catalog item, "
        "showing which external content sources are being used in the field. "
        "Fixed 12-month window. Filter by catalog_item or pass 'all'."
    ),
    response_model=FieldSourceResponse,
)
async def field_source_report(
    request: Request,
    user: str = Depends(require_curator),
    catalog_item: str = Query("all"),
):
    db = request.app.state.db
    cat_filter = catalog_item if catalog_item != "all" else None
    rows = db.get_field_source_summary(catalog_item=cat_filter)

    def _is_multinode(size: str | None) -> bool:
        if size == "multinode":
            return True
        if size and size.isdigit() and int(size) > 1:
            return True
        return False

    # Group by (git_repo, git_ref, catalog_item)
    groups: dict[tuple, list] = {}
    for row in rows:
        key = (row["git_repo"], row.get("git_ref"), row["catalog_item"])
        groups.setdefault(key, []).append(row)

    repos = []
    for (repo, ref, cat), provisions in groups.items():
        dates = [p["provisioned_at"] for p in provisions]
        repos.append(FieldSourceRepo(
            git_repo=repo,
            git_ref=ref,
            catalog_item=cat,
            provision_count=len(provisions),
            cnv_count=sum(1 for p in provisions if p.get("cloud_provider") == "cnv"),
            aws_count=sum(1 for p in provisions if p.get("cloud_provider") == "aws"),
            sno_count=sum(1 for p in provisions if p.get("cluster_size") in ("sno", "1")),
            multinode_count=sum(1 for p in provisions if _is_multinode(p.get("cluster_size"))),
            first_seen=min(dates),
            last_seen=max(dates),
            provisions=[FieldSourceProvision(
                provisioned_at=p["provisioned_at"],
                retired_at=p.get("retired_at"),
                cloud_provider=p.get("cloud_provider"),
                cluster_size=p.get("cluster_size"),
                node_size=p.get("node_size"),
            ) for p in provisions],
        ))

    repos.sort(key=lambda r: r.provision_count, reverse=True)
    return FieldSourceResponse(
        repos=repos,
        total_repos=len(repos),
        total_provisions=sum(r.provision_count for r in repos),
    )


@router.post(
    "/{identifier}",
    tags=["Content Analysis"],
    summary="Analyze single item",
    description="Triggers content analysis for a single catalog item. Accepts content_id or ci_name. Curator-only.",
    response_model=JobResponse,
)
async def analyze_single(identifier: str, request: Request, force: bool = True, user: str = Depends(require_curator)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    content_id = identifier if identifier.startswith("babylon:") else f"babylon:{identifier}"
    entity = db.get_content_entity(content_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Item not found: {identifier}")
    from rcars.services.showroom_source import is_content_excluded
    if is_content_excluded(content_id):
        raise HTTPException(status_code=400, detail="Content analysis is disabled for AgnosticV tests/ items")
    job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user,
                           progress_json={"content_id": content_id})
    await arq_redis.enqueue_job("run_analysis", job_id=job_id, content_id=content_id, force=force, _job_id=job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


@router.get(
    "/jobs/{job_id}/stream",
    tags=["Content Analysis"],
    summary="Stream analysis job progress (SSE)",
    description="Server-Sent Events stream for real-time analysis job progress updates.",
)
async def stream_job(job_id: str, request: Request, user: str = Depends(require_auth)):
    relay = JobProgressRelay(request.app.state.redis)
    return create_sse_response(relay, job_id)
