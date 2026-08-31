"""Admin routes — token usage, jobs, worker health, scheduled maintenance."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse
from rcars.api.middleware.auth import require_admin, require_curator, invalidate_role_assignments_cache
from rcars.api.schemas import (
    JobResponse, JobListResponse, TokenUsageResponse,
    WorkerHealthResponse, ScanProgressResponse, QueryHistoryResponse,
    ScheduleResponse, LlmProviderResponse,
    ReportingStatusResponse, RoleAssignmentsResponse, AddRoleAssignmentRequest,
    VocabularyResponse, UnknownTermsResponse, UnknownTerm, ResolveUnknownTermRequest,
)
from rcars.config import Settings

logger = structlog.get_logger()

router = APIRouter(prefix="/admin")


@router.get(
    "/token-usage",
    summary="LLM token consumption stats",
    description="Returns token usage statistics and recent query costs over the specified number of days. Admin-only.",
    response_model=TokenUsageResponse,
)
async def token_usage(
    request: Request,
    user: str = Depends(require_admin),
    days: int = Query(30, ge=1, le=365),
):
    db = request.app.state.db
    stats = db.get_token_stats(days=days)
    queries = db.get_recent_queries(days=days)
    return {"stats": stats, "recent_queries": queries, "days": days}


@router.get(
    "/jobs/{job_id}",
    summary="Get job details",
    description="Returns full details for a specific async job including status, result, and error. Admin-only.",
    responses={404: {"description": "Job not found"}},
)
async def get_job(job_id: str, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    job = db.get_job(job_id)
    if not job:
        return {"error": "not found"}
    return job


@router.get(
    "/jobs",
    summary="List recent jobs",
    description="Returns recent async jobs with optional type filter. Admin-only.",
    response_model=JobListResponse,
)
async def list_jobs(
    request: Request,
    user: str = Depends(require_admin),
    limit: int = Query(50, le=200),
    job_type: str | None = None,
):
    db = request.app.state.db
    jobs = db.list_jobs(limit=limit, job_type=job_type)
    return {"items": jobs, "total": len(jobs)}


@router.get(
    "/workers",
    summary="Worker health and queue depths",
    description="Returns arq queue depths, active job count, and currently running job details. Admin-only.",
    response_model=WorkerHealthResponse,
)
async def worker_health(request: Request, user: str = Depends(require_admin)):
    redis = request.app.state.redis
    db = request.app.state.db

    queue_depths = {}
    for queue_name in ["recommend", "analyze", "ops"]:
        depth = await redis.llen(f"arq:queue:{queue_name}")
        queue_depths[queue_name] = depth

    jobs = db.list_jobs(limit=100)
    running = [j for j in jobs if j["status"] == "running"]
    failed = [j for j in jobs if j["status"] == "failed"]

    running_details = []
    for j in running:
        ci = (j.get("progress_json") or {}).get("ci_name")
        running_details.append({
            "id": j["id"],
            "job_type": j["job_type"],
            "ci_name": ci,
            "created_at": j["created_at"],
        })

    return {
        "queue_depths": queue_depths,
        "active_jobs": len(running),
        "running_jobs": running_details,
        "failed_jobs_recent": len(failed),
    }


@router.get(
    "/scan-progress",
    summary="Current scan batch progress",
    description="Returns progress of the most recent scan or rescan-all batch. Admin-only.",
    response_model=ScanProgressResponse,
)
async def scan_progress(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db

    parent_jobs = db.list_jobs(limit=5, job_type="scan") + db.list_jobs(limit=5, job_type="rescan_all")
    since = None
    if parent_jobs:
        parent_jobs.sort(key=lambda j: j["created_at"], reverse=True)
        since = parent_jobs[0]["created_at"]

    all_jobs = db.list_jobs(limit=1000, job_type="analyze")
    jobs = [j for j in all_jobs if since is None or j["created_at"] >= since]

    queued = [j for j in jobs if j["status"] == "queued"]
    running = [j for j in jobs if j["status"] == "running"]
    complete = [j for j in jobs if j["status"] == "complete"]
    failed = [j for j in jobs if j["status"] == "failed"]

    recent = []
    for j in complete[-20:]:
        rj = j.get("result_json") or {}
        ci = rj.get("ci_name", "unknown")
        propagated = rj.get("propagated", 0)
        label = f"{ci} (+{propagated} siblings)" if propagated else ci
        recent.append(label)
    failed_names = []
    for j in failed[-10:]:
        ci = j.get("result_json", {}).get("ci_name") if j.get("result_json") else None
        error = j.get("error", "unknown")
        label = f"{ci}: {error}" if ci else error
        failed_names.append(label[:120])

    total_propagated = sum(
        (j.get("result_json") or {}).get("propagated", 0)
        for j in complete
    )

    return {
        "queued": len(queued),
        "running": len(running),
        "complete": len(complete),
        "failed": len(failed),
        "total": len(jobs),
        "total_propagated": total_propagated,
        "recent_complete": recent,
        "recent_failures": failed_names,
    }


@router.get(
    "/queries",
    summary="Query history",
    description="Returns advisor query sessions for the list view. Excludes heavy results_json. Admin-only.",
    response_model=QueryHistoryResponse,
)
async def query_history(
    request: Request,
    user: str = Depends(require_admin),
    limit: int = Query(50, le=200),
):
    db = request.app.state.db
    sessions = db.list_advisor_sessions(limit=limit)
    return {
        "items": [
            {
                "session_id": s["session_id"],
                "started_at": s["started_at"],
                "query_text": s.get("query_text"),
                "chosen_ci_name": s.get("chosen_ci_name"),
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get(
    "/queries/{session_id}",
    summary="Query session detail",
    description="Returns full turn details for a single advisor session, including results_json. Admin-only.",
)
async def query_session_detail(
    request: Request,
    session_id: str,
    user: str = Depends(require_admin),
):
    db = request.app.state.db
    turns = db.get_advisor_session(session_id)
    if not turns:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "turns": turns,
    }


@router.post(
    "/run-maintenance",
    summary="Trigger maintenance pipeline",
    description="Manually triggers the nightly maintenance pipeline (refresh → stale check → re-analyze). Admin-only.",
    response_model=JobResponse,
)
async def run_maintenance(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="maintenance", queue="ops", created_by=user)
    await arq_redis.enqueue_job(
        "run_nightly_pipeline", job_id=job_id, _queue_name="arq:queue:scan"
    )
    return {"job_id": job_id}


@router.post(
    "/sync-babylon",
    summary="Trigger Babylon maintenance pipeline",
    description="Manually triggers the Babylon sub-pipeline only (refresh → stale check → re-analyze → workload scan). Admin-only.",
    response_model=JobResponse,
)
async def sync_babylon(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="maintenance", queue="ops", created_by=user)
    try:
        await arq_redis.enqueue_job(
            "run_babylon_pipeline", job_id=job_id, _queue_name="arq:queue:scan"
        )
    except Exception:
        db.fail_job(job_id, error="Failed to enqueue job")
        raise
    return {"job_id": job_id}


@router.post(
    "/sync-reporting",
    summary="Sync reporting metrics",
    description="Syncs provision, cost, and sales metrics from the RHDP Reporting MCP server. Admin-only.",
    response_model=JobResponse,
)
async def sync_reporting(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="reporting_sync", queue="ops", created_by=user)
    try:
        await arq_redis.enqueue_job("run_reporting_sync_job", job_id=job_id, _queue_name="arq:queue:scan")
    except Exception:
        db.fail_job(job_id, error="Failed to enqueue job")
        raise
    return {"job_id": job_id}


class SyncOsspaRequest(BaseModel):
    force: bool = False
    confirm_empty_inventory: bool = False


@router.post(
    "/sync-osspa",
    summary="Sync portfolio architectures",
    description=(
        "Syncs Red Hat Architecture Center portfolio architectures from OSSPA GitLab. "
        "Admin-only. `force` re-analyzes items whose content has not changed. "
        "`confirm_empty_inventory` permits retiring every architecture when the "
        "inventory has zero in-scope rows — only set it after verifying that is real."
    ),
    response_model=JobResponse,
)
async def sync_osspa(
    request: Request,
    body: SyncOsspaRequest = SyncOsspaRequest(),
    user: str = Depends(require_admin),
):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="osspa_sync", queue="ops", created_by=user)
    try:
        await arq_redis.enqueue_job(
            "run_osspa_sync_job", job_id=job_id,
            force=body.force, confirm_empty_inventory=body.confirm_empty_inventory,
            _queue_name="arq:queue:scan",
        )
    except Exception:
        db.fail_job(job_id, error="Failed to enqueue job")
        raise
    logger.info("osspa_sync_enqueued", component="rcars", action="sync_osspa",
                job_id=job_id, created_by=user,
                force=body.force, confirm_empty_inventory=body.confirm_empty_inventory)
    return {"job_id": job_id}


@router.post(
    "/scan-workloads",
    summary="Scan workload repositories",
    description="Triggers a workload repo scan: clones AgnosticD v2 repos, analyzes Ansible roles, and updates workload mappings. Admin-only.",
    response_model=JobResponse,
)
async def scan_workloads(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="workload_scan", queue="ops", created_by=user)
    try:
        await arq_redis.enqueue_job(
            "run_workload_scan", job_id=job_id, _queue_name="arq:queue:scan"
        )
    except Exception:
        db.fail_job(job_id, error="Failed to enqueue job")
        raise
    logger.info("workload_scan_enqueued", component="rcars", action="scan_workloads",
                job_id=job_id, created_by=user)
    return {"job_id": job_id}


@router.get(
    "/schedule",
    summary="Maintenance schedule status",
    description="Returns the scheduled maintenance pipeline configuration and last run status. Admin-only.",
    response_model=ScheduleResponse,
)
async def schedule_status(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    settings = Settings()

    jobs = db.list_jobs(limit=5, job_type="maintenance")
    last_pipeline = None
    if jobs:
        job = jobs[0]
        last_pipeline = {
            "job_id": job["id"],
            "status": job["status"],
            "created_at": job["created_at"],
            "completed_at": job.get("completed_at"),
            "result": job.get("result_json"),
            "error": job.get("error"),
        }

    return {
        "pipeline_enabled": settings.pipeline_enabled,
        "pipeline_schedule": f"{settings.pipeline_hour:02d}:{settings.pipeline_minute:02d} UTC daily",
        "last_pipeline": last_pipeline,
    }


@router.get(
    "/llm-provider",
    summary="LLM provider configuration",
    description="Returns active LLM provider configuration (LiteMaaS/Vertex AI) and available models. Admin-only.",
    response_model=LlmProviderResponse,
)
async def llm_provider_status(request: Request, user: str = Depends(require_admin)):
    settings = Settings()
    from rcars.config import fetch_litemaas_models
    litemaas_models = sorted(fetch_litemaas_models(settings)) if settings.use_litemaas else []
    vertex_models = sorted({settings.model, settings.triage_model, settings.rationale_model}) if settings.use_vertex else []
    return {
        "litemaas_enabled": settings.use_litemaas,
        "litemaas_url": settings.litemaas_url or None,
        "litemaas_models": litemaas_models,
        "vertex_enabled": settings.use_vertex,
        "vertex_region": settings.cloud_ml_region if settings.use_vertex else None,
        "vertex_models": vertex_models,
        "analysis_model": settings.model,
        "triage_model": settings.triage_model,
        "rationale_model": settings.rationale_model,
        "scanning_model": settings.triage_model,
    }


@router.get(
    "/reporting-status",
    summary="Reporting sync status",
    description="Returns the status of the reporting metrics sync from the RHDP MCP server. Admin-only.",
    response_model=ReportingStatusResponse,
)
async def reporting_status(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    settings = Settings()
    status = db.get_reporting_sync_status()

    last_result = None
    for jt in ("reporting_sync", "maintenance"):
        for job in db.list_jobs(limit=5, job_type=jt):
            rj = job.get("result_json") or {}
            if jt == "reporting_sync":
                last_result = rj
                break
            elif rj.get("reporting_sync"):
                last_result = rj["reporting_sync"]
                break
        if last_result:
            break

    return {
        "configured": bool(settings.reporting_mcp_url and settings.reporting_mcp_token),
        "total": status["total"] if status else 0,
        "with_provisions": status["with_provisions"] if status else 0,
        "with_cost": status["with_cost"] if status else 0,
        "with_sales": status["with_sales"] if status else 0,
        "last_synced": status["last_synced"] if status else None,
    }


@router.get(
    "/role-assignments",
    summary="List role assignments",
    description="Returns all role assignments: DB-managed entries plus read-only entries derived from env var config. Admin-only.",
    response_model=RoleAssignmentsResponse,
)
async def list_role_assignments(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    settings: Settings = request.app.state.settings

    config_entries = [
        {"id": None, "type": "user", "value": v, "role": "curator", "source": "config", "added_by": None, "added_at": None}
        for v in settings.curator_emails
    ] + [
        {"id": None, "type": "user", "value": v, "role": "admin", "source": "config", "added_by": None, "added_at": None}
        for v in settings.admin_emails
    ]

    db_entries = [
        {**row, "source": "db"}
        for row in db.get_role_assignments()
    ]

    return {"assignments": config_entries + db_entries}


@router.post(
    "/role-assignments",
    summary="Add a role assignment",
    description="Adds a new role assignment (user or group). Returns 409 if the entry already exists. Admin-only.",
    status_code=201,
)
async def add_role_assignment(
    body: AddRoleAssignmentRequest,
    request: Request,
    user: str = Depends(require_admin),
):
    db = request.app.state.db
    try:
        row = db.add_role_assignment(body.type, body.value, body.role, added_by=user)
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Assignment for {body.type} '{body.value}' already exists")
        raise
    invalidate_role_assignments_cache()
    return {**row, "source": "db"}


@router.delete(
    "/role-assignments/{assignment_id}",
    summary="Remove a role assignment",
    description="Removes a DB-managed role assignment by ID. Returns 404 if not found. Admin-only.",
    status_code=204,
)
async def delete_role_assignment(
    assignment_id: int,
    request: Request,
    user: str = Depends(require_admin),
):
    db = request.app.state.db
    deleted = db.delete_role_assignment(assignment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    invalidate_role_assignments_cache()


# ── Controlled vocabulary (RHDPCD-507) ──


@router.get(
    "/vocabulary",
    summary="Current controlled vocabulary",
    response_model=VocabularyResponse,
)
async def get_vocabulary(user: str = Depends(require_admin)):
    from rcars.services.vocabulary import DIMENSIONS, load_vocabulary

    vocab = load_vocabulary()
    return {
        "dimensions": {
            dimension: [
                {
                    "name": e.name,
                    "aliases": list(e.aliases),
                    "search_terms": list(e.search_terms),
                    "is_tdp": e.is_tdp,
                }
                for e in vocab.entries(dimension)
            ]
            for dimension in DIMENSIONS
        },
        "content_modes": dict(vocab.content_modes),
        "ignored_terms": {
            d: list(vocab.ignored_originals.get(d, ())) for d in DIMENSIONS
        },
    }


@router.get(
    "/vocabulary/unknowns",
    summary="Unknown-term review queue",
    response_model=UnknownTermsResponse,
)
async def get_vocabulary_unknowns(
    request: Request,
    user: str = Depends(require_admin),
    status: str | None = Query("pending"),
    dimension: str | None = Query(None),
):
    db = request.app.state.db
    return {"terms": db.get_unknown_terms(status=status, dimension=dimension)}


@router.put(
    "/vocabulary/unknowns/{dimension}/{term:path}",
    summary="Record a decision on an unknown term",
    response_model=UnknownTerm,
)
async def resolve_vocabulary_unknown(
    dimension: str,
    term: str,
    body: ResolveUnknownTermRequest,
    request: Request,
    user: str = Depends(require_admin),
):
    from rcars.services.vocabulary import DIMENSIONS, load_vocabulary

    if dimension not in DIMENSIONS:
        raise HTTPException(status_code=400, detail=f"Unknown dimension '{dimension}'")

    if body.action == "alias":
        if not body.resolved_to:
            raise HTTPException(status_code=400, detail="alias requires resolved_to")
        if body.resolved_to not in load_vocabulary().canonical_names(dimension):
            raise HTTPException(
                status_code=400,
                detail=f"'{body.resolved_to}' is not a canonical name in {dimension}",
            )

    db = request.app.state.db
    row = db.resolve_unknown_term(dimension, term, body.action, body.resolved_to, user)
    if not row:
        raise HTTPException(status_code=404, detail=f"No queued term '{term}' in {dimension}")
    logger.info(
        "vocabulary_term_resolved", component="rcars", action="resolve_vocabulary_term",
        dimension=dimension, term=term, decision=body.action, resolved_by=user,
    )
    return row


@router.get(
    "/vocabulary/generate",
    summary="Download a merged vocabulary.yaml",
    response_class=PlainTextResponse,
)
async def generate_vocabulary(request: Request, user: str = Depends(require_admin)):
    from rcars.services.vocabulary import generate_vocabulary_yaml, load_vocabulary

    db = request.app.state.db
    decisions = [
        row
        for row in db.get_unknown_terms(status=None)
        if row.get("status") in ("aliased", "promoted", "rejected")
    ]
    content = generate_vocabulary_yaml(load_vocabulary(), decisions)
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": 'attachment; filename="vocabulary.yaml"'},
    )
