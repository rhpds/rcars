"""Analysis routes — scan, stale check, rescan, single-item analysis, retirement."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from rcars.api.middleware.auth import require_admin, require_curator, require_auth, require_performance_view
from rcars.api.schemas import (
    JobResponse, PerformanceDashboardResponse, WorkflowResponse,
    WorkflowGetResponse, StartRetirementResponse, CancelWorkflowResponse,
    ScanResponse, RescanResponse,
)
from rcars.api.streaming import JobProgressRelay, create_sse_response
from rcars.workers.ops import sha_dedup_scan_items
import structlog

logger = structlog.get_logger(component="api")

router = APIRouter(prefix="/analysis")


WINDOWS = {"3m", "6m", "9m", "12m"}
CHANNEL_SOURCES = {"sales": "rhdp", "marketing": "interactive_labs"}


def _base_name_to_content_id(base_name: str, db) -> str | None:
    """Resolve a catalog base name (e.g. 'ocp4-getting-started') to a content_id.

    Tries common stage suffixes via the DB lookup. Returns content_id or None.
    """
    result = db.resolve_base_names_to_content_ids({base_name})
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


class ApproveRequest(BaseModel):
    reason: str = Field(min_length=1)
    replacement_ci: str | None = None
    replacement_name: str | None = None

class StartRequest(BaseModel):
    target_days: int = 30
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
):
    if window not in WINDOWS:
        raise HTTPException(400, f"window must be one of {sorted(WINDOWS)}")
    if channel not in CHANNEL_SOURCES:
        raise HTTPException(400, f"channel must be one of {sorted(CHANNEL_SOURCES)}")
    source = CHANNEL_SOURCES[channel]

    db = request.app.state.db

    items = db.list_performance_data(
        sort_by=sort_by, sort_dir=sort_dir,
        category=category,
        has_prod=has_prod, search=search,
        workflow_status=workflow_status,
        channel=source,
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
            item["completions"] = w.get("completions", 0)
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
        else:
            item["provisions"] = 0
            item["completions"] = 0
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
    stages_map = db.get_stages_for_base_names(base_names)
    owners_map = db.get_owners_for_base_names(base_names)

    from rcars.services.reporting_sync import compute_sales_impact
    for item in items:
        stages = stages_map.get(item["catalog_base_name"], [])
        item["stages"] = stages
        has_showroom = any(True for s in stages if s.get("has_showroom"))
        item["has_content"] = has_showroom
        if not has_showroom:
            item["catalog_url"] = f"https://demo.redhat.com/catalog?search={item['catalog_base_name']}"
        item["owners"] = owners_map.get(item["catalog_base_name"], [])
        if "sales_impact" not in item:
            item["sales_impact"] = compute_sales_impact(float(item.get("closed_amount", 0) or 0))

    # Re-sort by frontend sort names (DB sorted by DB column names, may differ)
    allowed_sorts = {"performance_score", "provisions", "total_cost", "closed_amount", "pipeline_touched", "display_name", "touched_roi", "closed_roi"}
    if sort_by in allowed_sorts:
        reverse = sort_dir.lower() == "desc"
        if sort_by == "touched_roi":
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
                    "completions": mw.get("completions", mrow.get("completions", 0)),
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
                    "completions": sw.get("completions", srow.get("completions", 0)),
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
    "/performance/workflow/{base_name}",
    tags=["Performance"],
    summary="Get retirement workflow",
    description="Returns the current retirement workflow state for a catalog item. Curator-only.",
    response_model=WorkflowGetResponse,
)
async def get_workflow(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
    wf = db.get_retirement_workflow(content_id) if content_id else None
    return {"workflow": wf}


@router.put(
    "/performance/workflow/{base_name}/review",
    tags=["Performance"],
    summary="Mark item as reviewed",
    description="Marks a catalog item as reviewed in the retirement workflow. Curator-only.",
    response_model=WorkflowResponse,
)
async def review_item(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
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
    "/performance/workflow/{base_name}/approve",
    tags=["Performance"],
    summary="Approve item for retirement",
    description=(
        "Approves a catalog item for retirement with a reason and optional replacement. "
        "Captures a snapshot of current metrics at approval time. Curator-only."
    ),
    response_model=WorkflowResponse,
)
async def approve_item(base_name: str, body: ApproveRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    from datetime import datetime

    content_id = _base_name_to_content_id(base_name, db)
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
            "completions": ch.get("completions", 0),
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
    "/performance/workflow/{base_name}/notify",
    tags=["Performance"],
    summary="Mark owner as notified",
    description="Records that the content owner has been notified about the retirement. Curator-only.",
    response_model=WorkflowResponse,
)
async def notify_owner(base_name: str, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
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
    "/performance/workflow/{base_name}/start",
    tags=["Performance"],
    summary="Start retirement process",
    description=(
        "Starts the retirement process: creates a Jira ticket and sets a target retirement date. "
        "Requires prior approval. Curator-only."
    ),
    response_model=StartRetirementResponse,
    responses={400: {"description": "Item must be approved before starting retirement"}},
)
async def start_retirement(base_name: str, body: StartRequest, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    settings = request.app.state.settings
    from datetime import datetime, timedelta

    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"No content found for base name: {base_name}")

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

    wf_for_jira = {**wf, "jira_project": body.jira_project, "retirement_target_date": target_date, "target_days": body.target_days}

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
    "/performance/workflow/{base_name}/link-jira",
    tags=["Performance"],
    summary="Link existing Jira ticket",
    description="Links an existing Jira ticket to the retirement workflow and advances to started status. Requires prior approval.",
    response_model=WorkflowResponse,
    responses={400: {"description": "Item must be approved before linking Jira"}},
)
async def link_jira(base_name: str, body: LinkJiraRequest, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
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
    "/performance/workflow/{base_name}/notes",
    tags=["Performance"],
    summary="Update curator notes",
    description="Sets or updates curator notes on a retirement workflow item. Curator-only.",
    response_model=WorkflowResponse,
)
async def update_notes(base_name: str, body: NotesRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"No content found for base name: {base_name}")
    fields = {"curator_notes": body.notes}
    result = db.upsert_retirement_workflow(content_id, fields)
    return {"status": "ok", "workflow": result}


@router.delete(
    "/performance/workflow/{base_name}",
    tags=["Performance"],
    summary="Cancel retirement workflow",
    description="Cancels and removes the retirement workflow for a catalog item. Admin-only.",
    response_model=CancelWorkflowResponse,
)
async def cancel_workflow(base_name: str, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"No content found for base name: {base_name}")
    deleted = db.delete_retirement_workflow(content_id)
    if deleted:
        db.log_action(base_name, "retirement_cancelled", user, "Workflow cancelled")
    return {"status": "ok", "deleted": deleted}


@router.post(
    "/scan",
    tags=["Content Analysis"],
    summary="Scan items needing analysis",
    description=(
        "Enqueues analysis jobs for all catalog items that need (re-)analysis. "
        "Uses SHA-based deduplication to avoid scanning identical content twice. Admin-only."
    ),
    response_model=ScanResponse,
)
async def start_scan(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis

    dedup_stats = db.get_scan_dedup_stats()
    items = db.get_items_needing_analysis()
    scan_items, sha_siblings_map = sha_dedup_scan_items(items)
    sha_stats = {"ref_groups": len(items), "sha_groups": len(scan_items), "sha_merged": len(items) - len(scan_items)}

    parent_job_id = db.create_job(job_type="scan", queue="analyze", created_by=user)

    for item in scan_items:
        sub_job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
        await arq_redis.enqueue_job(
            "run_analysis", job_id=sub_job_id, content_id=item["content_id"],
            sha_siblings=sha_siblings_map.get(item["content_id"]),
            _queue_name="arq:queue:scan"
        )

    result = {"enqueued": len(scan_items), **dedup_stats, **sha_stats}
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
    await arq_redis.enqueue_job("run_stale_check", job_id=job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


@router.post(
    "/rescan-all",
    tags=["Content Analysis"],
    summary="Force rescan of entire catalog",
    description="Marks all items as stale and enqueues re-analysis for the entire catalog. Admin-only.",
    response_model=RescanResponse,
)
async def rescan_all(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis

    marked = db.mark_all_stale()
    dedup_stats = db.get_scan_dedup_stats()
    items = db.get_items_needing_analysis()
    scan_items, sha_siblings_map = sha_dedup_scan_items(items)
    sha_stats = {"ref_groups": len(items), "sha_groups": len(scan_items), "sha_merged": len(items) - len(scan_items)}

    parent_job_id = db.create_job(job_type="rescan_all", queue="analyze", created_by=user)

    for item in scan_items:
        sub_job_id = db.create_job(job_type="analyze", queue="analyze", created_by="rescan-all")
        await arq_redis.enqueue_job(
            "run_analysis", job_id=sub_job_id, content_id=item["content_id"],
            sha_siblings=sha_siblings_map.get(item["content_id"]),
            _queue_name="arq:queue:scan"
        )

    result = {"marked_stale": marked, "enqueued": len(scan_items), **dedup_stats, **sha_stats}
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
    namespace: str | None = Query(None),
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
        namespace=namespace, search=search,
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
        if w:
            item["provisions"] = w.get("provisions", 0)
            item["requests"] = w.get("requests", 0)
            item["completions"] = w.get("completions", 0)
            item["unique_users"] = w.get("unique_users", 0)
            item["success_ratio"] = w.get("success_ratio", 0)
            item["failure_ratio"] = w.get("failure_ratio", 0)

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
    allowed_sorts = {"provisions", "unique_users", "success_ratio", "failure_ratio", "display_name"}
    if sort_by in allowed_sorts:
        reverse = sort_dir.lower() == "desc"
        if sort_by == "display_name":
            items.sort(key=lambda i: (i.get(sort_by) or ""), reverse=reverse)
        else:
            items.sort(key=lambda i: (i.get(sort_by) or 0), reverse=reverse)

    synced_at = items[0]["synced_at"] if items and items[0].get("synced_at") else None

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


@router.post(
    "/{identifier}",
    tags=["Content Analysis"],
    summary="Analyze single item",
    description="Triggers content analysis for a single catalog item. Accepts content_id or ci_name. Curator-only.",
    response_model=JobResponse,
)
async def analyze_single(identifier: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    content_id = identifier if identifier.startswith("babylon:") else f"babylon:{identifier}"
    entity = db.get_content_entity(content_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Item not found: {identifier}")
    job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
    await arq_redis.enqueue_job("run_analysis", job_id=job_id, content_id=content_id, _queue_name="arq:queue:scan")
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
