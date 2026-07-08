"""Analysis routes — scan, stale check, rescan, single-item analysis, retirement."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from rcars.api.middleware.auth import require_admin, require_curator, require_auth
from rcars.api.schemas import (
    JobResponse, RetirementDashboardResponse, WorkflowResponse,
    WorkflowGetResponse, StartRetirementResponse, CancelWorkflowResponse,
    ScanResponse, RescanResponse,
)
from rcars.api.streaming import JobProgressRelay, create_sse_response
from rcars.workers.ops import sha_dedup_scan_items
import structlog

logger = structlog.get_logger(component="api")

router = APIRouter(prefix="/analysis")


WINDOW_KEYS = {"1q": "3m", "2q": "6m", "3q": "9m", "1y": "12m"}


class ApproveRequest(BaseModel):
    reason: str = Field(min_length=1)
    replacement_ci: str | None = None
    replacement_name: str | None = None

class StartRequest(BaseModel):
    target_days: int = 30
    jira_project: str = "RHDPCD"

class NotesRequest(BaseModel):
    notes: str = Field(max_length=5000)


@router.get(
    "/retirement",
    tags=["Retirement"],
    summary="Retirement dashboard",
    description=(
        "Returns catalog items scored for retirement potential based on usage, cost, and sales impact. "
        "Supports filtering by score threshold, category, production status, and time window (1q/2q/3q/1y). "
        "Curator-only."
    ),
    response_model=RetirementDashboardResponse,
)
async def retirement_dashboard(
    request: Request,
    user: str = Depends(require_curator),
    sort_by: str = Query("retirement_score"),
    sort_dir: str = Query("desc"),
    min_score: int | None = Query(None),
    category: str | None = Query(None),
    has_prod: bool | None = Query(None),
    search: str | None = Query(None),
    window: str = Query("1y"),
    workflow_status: str | None = Query(None),
):
    db = request.app.state.db
    window_key = WINDOW_KEYS.get(window, "12m")

    items = db.list_reporting_metrics(
        sort_by="retirement_score", sort_dir="desc",
        workflow_status=workflow_status,
    )

    import json as _json
    for item in items:
        wm = item.get("windowed_metrics") or {}
        if isinstance(wm, str):
            wm = _json.loads(wm)
        w = wm.get(window_key, {})
        if w:
            item["provisions"] = w.get("provisions", 0)
            item["experiences"] = w.get("experiences", 0)
            item["requests"] = w.get("requests", 0)
            item["unique_users"] = w.get("unique_users", 0)
            item["success_ratio"] = w.get("success_ratio", 0)
            item["failure_ratio"] = w.get("failure_ratio", 0)
            item["touched_amount"] = w.get("touched_amount", 0)
            item["closed_amount"] = w.get("closed_amount", 0)
            item["total_cost"] = w.get("total_cost", 0)
            item["avg_cost_per_provision"] = w.get("avg_cost_per_provision", 0)
            item["retirement_score"] = w.get("retirement_score", 0)
            item["sales_impact"] = w.get("sales_impact", "low")

    if has_prod is True:
        prod_names = db.get_all_base_names_with_prod()
        items = [i for i in items if i["catalog_base_name"] in prod_names]
    elif has_prod is False:
        prod_names = db.get_all_base_names_with_prod()
        items = [i for i in items if i["catalog_base_name"] not in prod_names]
    if search:
        words = search.lower().split()
        def _matches(item: dict) -> bool:
            text = f"{item.get('display_name', '')} {item.get('catalog_base_name', '')}".lower()
            return all(w in text for w in words)
        items = [i for i in items if _matches(i)]
    if min_score is not None:
        items = [i for i in items if (i.get("retirement_score") or 0) >= min_score]
    if category:
        cat_lower = category.lower()
        items = [i for i in items if (i.get("category") or "").lower() == cat_lower]

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

    allowed_sorts = {"retirement_score", "provisions", "total_cost", "closed_amount", "touched_amount", "display_name"}
    if sort_by in allowed_sorts:
        reverse = sort_dir.lower() == "desc"
        default = "" if sort_by == "display_name" else 0
        items.sort(key=lambda i: (i.get(sort_by) or default), reverse=reverse)

    from datetime import date as _date
    today = _date.today()
    for item in items:
        wm = item.pop("windowed_metrics", None) or {}
        if isinstance(wm, str):
            wm = _json.loads(wm)
        w = wm.get(window_key, {})
        item["score_breakdown"] = w.get("score_breakdown")

        iu = item.get("ignored_until")
        if iu and isinstance(iu, _date) and iu >= today:
            item["ignored_until"] = iu.isoformat()
        elif iu and isinstance(iu, str) and iu >= today.isoformat():
            pass
        else:
            item["ignored_until"] = None

    sync_status = db.get_reporting_sync_status()
    return {
        "items": items,
        "total": len(items),
        "synced_at": str(sync_status["last_synced"]) if sync_status and sync_status.get("last_synced") else None,
        "summary": sync_status,
        "window": window,
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
    wf = db.get_retirement_workflow(base_name)
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
    fields = {
        "step_reviewed_at": "NOW()",
        "step_reviewed_by": user,
        "status": "reviewed",
    }
    result = db.upsert_retirement_workflow(base_name, fields)
    db.log_action(base_name, "retirement_reviewed", user, "Marked as reviewed")
    return {"status": "ok", "workflow": result}


@router.put(
    "/retirement/workflow/{base_name}/approve",
    tags=["Retirement"],
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

    metrics = db.get_reporting_metrics(base_name)
    snapshot = {
        "provisions": metrics.get("provisions", 0) if metrics else 0,
        "experiences": metrics.get("experiences", 0) if metrics else 0,
        "unique_users": metrics.get("unique_users", 0) if metrics else 0,
        "touched_amount": float(metrics.get("touched_amount", 0) or 0) if metrics else 0,
        "closed_amount": float(metrics.get("closed_amount", 0) or 0) if metrics else 0,
        "total_cost": float(metrics.get("total_cost", 0) or 0) if metrics else 0,
        "retirement_score": metrics.get("retirement_score", 0) if metrics else 0,
        "window": "12m",
        "snapshot_date": datetime.now().strftime("%Y-%m-%d"),
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

    result = db.upsert_retirement_workflow(base_name, fields)
    db.log_action(base_name, "retirement_approved", user, f"Reason: {body.reason}")
    return {"status": "ok", "workflow": result}


@router.put(
    "/retirement/workflow/{base_name}/notify",
    tags=["Retirement"],
    summary="Mark owner as notified",
    description="Records that the content owner has been notified about the retirement. Curator-only.",
    response_model=WorkflowResponse,
)
async def notify_owner(base_name: str, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    fields = {
        "step_notified_at": "NOW()",
        "step_notified_by": user,
        "status": "notified",
    }
    result = db.upsert_retirement_workflow(base_name, fields)
    db.log_action(base_name, "retirement_notified", user, "Owner notified")
    return {"status": "ok", "workflow": result}


@router.put(
    "/retirement/workflow/{base_name}/start",
    tags=["Retirement"],
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

    wf = db.get_retirement_workflow(base_name)
    if not wf or not wf.get("step_approved_at"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Item must be approved before starting retirement")
    if wf.get("step_started_at"):
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=f"Retirement already started (Jira: {wf.get('jira_key', 'unknown')})")

    target_date = (datetime.now() + timedelta(days=body.target_days)).date()
    metrics = db.get_reporting_metrics(base_name) or {}

    wf_for_jira = {**wf, "jira_project": body.jira_project, "retirement_target_date": target_date, "target_days": body.target_days}

    from rcars.services.jira import create_retirement_ticket
    try:
        jira_key = create_retirement_ticket(settings, wf_for_jira, metrics)
    except Exception as exc:
        logger.error("retirement_jira_failed", base_name=base_name, error=str(exc))
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
    result = db.upsert_retirement_workflow(base_name, fields)
    db.log_action(base_name, "retirement_started", user, f"Jira: {jira_key}, target: {target_date}")
    return {"status": "ok", "workflow": result, "jira_key": jira_key}


@router.put(
    "/retirement/workflow/{base_name}/notes",
    tags=["Retirement"],
    summary="Update curator notes",
    description="Sets or updates curator notes on a retirement workflow item. Curator-only.",
    response_model=WorkflowResponse,
)
async def update_notes(base_name: str, body: NotesRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    fields = {"curator_notes": body.notes}
    result = db.upsert_retirement_workflow(base_name, fields)
    return {"status": "ok", "workflow": result}


@router.delete(
    "/retirement/workflow/{base_name}",
    tags=["Retirement"],
    summary="Cancel retirement workflow",
    description="Cancels and removes the retirement workflow for a catalog item. Curator-only.",
    response_model=CancelWorkflowResponse,
)
async def cancel_workflow(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    deleted = db.delete_retirement_workflow(base_name)
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
            "run_analysis", job_id=sub_job_id, ci_name=item["ci_name"],
            sha_siblings=sha_siblings_map.get(item["ci_name"]),
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
            "run_analysis", job_id=sub_job_id, ci_name=item["ci_name"],
            sha_siblings=sha_siblings_map.get(item["ci_name"]),
            _queue_name="arq:queue:scan"
        )

    result = {"marked_stale": marked, "enqueued": len(scan_items), **dedup_stats, **sha_stats}
    db.complete_job(parent_job_id, result_json=result)
    return {"job_id": parent_job_id, **result}


@router.put(
    "/retirement/ignore/{base_name}",
    tags=["Retirement"],
    summary="Ignore item for 30 days",
    description="Mutes a catalog item from the retirement dashboard for 30 days. Curator-only.",
)
async def ignore_item(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    from datetime import date, timedelta
    until = (date.today() + timedelta(days=30)).isoformat()
    ok = db.set_ignored_until(base_name, until)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(404, f"Item not found: {base_name}")
    db.log_action(base_name, "retirement_ignored", user, f"Muted until {until}")
    return {"status": "ok", "ignored_until": until}


@router.delete(
    "/retirement/ignore/{base_name}",
    tags=["Retirement"],
    summary="Un-ignore item",
    description="Removes the mute/ignore from a catalog item. Curator-only.",
)
async def unignore_item(base_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.clear_ignored(base_name)
    db.log_action(base_name, "retirement_unignored", user, "Unmuted")
    return {"status": "ok"}


@router.post(
    "/{ci_name}",
    tags=["Content Analysis"],
    summary="Analyze single item",
    description="Triggers content analysis for a single catalog item. Curator-only.",
    response_model=JobResponse,
)
async def analyze_single(ci_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
    await arq_redis.enqueue_job("run_analysis", job_id=job_id, ci_name=ci_name, _queue_name="arq:queue:scan")
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
