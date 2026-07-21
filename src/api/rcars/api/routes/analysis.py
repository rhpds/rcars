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

    # Map frontend sort names to DB column names
    sort_map = {"retirement_score": "performance_score", "touched_amount": "pipeline_touched"}
    db_sort_by = sort_map.get(sort_by, sort_by)

    items = db.list_performance_data(
        sort_by=db_sort_by, sort_dir=sort_dir,
        min_score=min_score, category=category,
        has_prod=has_prod, search=search,
        workflow_status=workflow_status,
    )

    import json as _json
    for item in items:
        # Backward-compat: derive catalog_base_name from content_id
        item["catalog_base_name"] = _extract_base_name_from_content_id(item.get("content_id", ""))

        # Field name aliases for frontend compat
        item["touched_amount"] = item.get("pipeline_touched", 0)
        item["experiences"] = item.get("completions", 0)
        item["retirement_score"] = item.get("performance_score", 0)

        # Apply windowed metrics overlay
        wm = item.get("windowed_metrics") or {}
        if isinstance(wm, str):
            wm = _json.loads(wm)
        w = wm.get(window_key, {})
        if w:
            item["provisions"] = w.get("provisions", 0)
            item["experiences"] = w.get("experiences", w.get("completions", 0))
            item["requests"] = w.get("requests", 0)
            item["unique_users"] = w.get("unique_users", 0)
            item["success_ratio"] = w.get("success_ratio", 0)
            item["failure_ratio"] = w.get("failure_ratio", 0)
            item["touched_amount"] = w.get("touched_amount", w.get("pipeline_touched", 0))
            item["closed_amount"] = w.get("closed_amount", 0)
            item["total_cost"] = w.get("total_cost", 0)
            item["avg_cost_per_provision"] = w.get("avg_cost_per_provision", 0)
            item["retirement_score"] = w.get("retirement_score", w.get("performance_score", 0))
            item["sales_impact"] = w.get("sales_impact", "low")

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
    allowed_sorts = {"retirement_score", "provisions", "total_cost", "closed_amount", "touched_amount", "display_name", "touched_roi", "closed_roi"}
    if sort_by in allowed_sorts:
        reverse = sort_dir.lower() == "desc"
        if sort_by == "touched_roi":
            items.sort(key=lambda i: (i.get("touched_amount") or 0) / max(i.get("total_cost") or 1, 0.01), reverse=reverse)
        elif sort_by == "closed_roi":
            items.sort(key=lambda i: (i.get("closed_amount") or 0) / max(i.get("total_cost") or 1, 0.01), reverse=reverse)
        elif sort_by == "display_name":
            items.sort(key=lambda i: (i.get(sort_by) or ""), reverse=reverse)
        else:
            items.sort(key=lambda i: (i.get(sort_by) or 0), reverse=reverse)

    from datetime import date as _date
    today = _date.today()
    for item in items:
        wm = item.pop("windowed_metrics", None) or {}
        if isinstance(wm, str):
            wm = _json.loads(wm)
        w = wm.get(window_key, {})
        item["score_breakdown"] = w.get("score_breakdown") or item.get("score_breakdown")

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
    content_id = _base_name_to_content_id(base_name, db)
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

    content_id = _base_name_to_content_id(base_name, db)
    if not content_id:
        from fastapi import HTTPException
        raise HTTPException(404, f"No content found for base name: {base_name}")

    # Build approval snapshot from performance data
    perf_score = db.get_performance_score(content_id)
    perf_channels = db.get_performance_channels(content_id)
    rhdp = next((ch for ch in perf_channels if ch.get("channel") == "rhdp"), None) if perf_channels else None
    snapshot = {
        "provisions": rhdp.get("provisions", 0) if rhdp else 0,
        "experiences": rhdp.get("completions", 0) if rhdp else 0,
        "unique_users": rhdp.get("unique_users", 0) if rhdp else 0,
        "touched_amount": float(rhdp.get("pipeline_touched", 0) or 0) if rhdp else 0,
        "closed_amount": float(rhdp.get("closed_amount", 0) or 0) if rhdp else 0,
        "total_cost": float(rhdp.get("total_cost", 0) or 0) if rhdp else 0,
        "retirement_score": perf_score.get("performance_score", 0) if perf_score else 0,
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

    result = db.upsert_retirement_workflow(content_id, fields)
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
    "/retirement/workflow/{base_name}/link-jira",
    tags=["Retirement"],
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
    "/retirement/workflow/{base_name}/notes",
    tags=["Retirement"],
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
    "/retirement/workflow/{base_name}",
    tags=["Retirement"],
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
    "/retirement/ignore/{base_name}",
    tags=["Retirement"],
    summary="Ignore item for 30 days",
    description="Mutes a catalog item from the retirement dashboard for 30 days. Curator-only.",
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
    "/retirement/ignore/{base_name}",
    tags=["Retirement"],
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
