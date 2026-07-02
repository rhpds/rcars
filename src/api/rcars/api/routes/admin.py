"""Admin routes — token usage, jobs, worker health, scheduled maintenance."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request, Query
from rcars.api.middleware.auth import require_admin
from rcars.api.schemas import (
    JobResponse, JobListResponse, TokenUsageResponse,
    WorkerHealthResponse, ScanProgressResponse, QueryHistoryResponse,
    OverlapResponse, ScheduleResponse, LlmProviderResponse,
    ReportingStatusResponse,
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
    description="Returns all advisor query sessions with full turn details for analytics. Admin-only.",
    response_model=QueryHistoryResponse,
)
async def query_history(
    request: Request,
    user: str = Depends(require_admin),
    limit: int = Query(50, le=200),
):
    db = request.app.state.db
    sessions = db.list_advisor_sessions(limit=limit)
    results = []
    for session in sessions:
        turns = db.get_advisor_session(session["session_id"])
        results.append({
            "session_id": session["session_id"],
            "started_at": session["started_at"],
            "turn_count": session["turns"],
            "turns": turns,
        })
    return {"items": results, "total": len(results)}


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
    "/overlap",
    summary="Content overlap report",
    description=(
        "Returns pairs of catalog items with high content similarity based on embedding cosine distance. "
        "Useful for identifying duplicate or near-duplicate content. Admin-only."
    ),
    response_model=OverlapResponse,
)
async def overlap_report(
    request: Request,
    user: str = Depends(require_admin),
    min_score: float = Query(0.75, ge=0.0, le=1.0),
    stage: str | None = Query(None, description="Filter by stage: prod, event, or dev"),
):
    db = request.app.state.db
    pairs = db.get_overlap_report(min_score=min_score, stage=stage)
    stats = db.get_similarity_stats(stage=stage)
    settings = Settings()
    return {
        "pairs": pairs,
        "total": len(pairs),
        "stats": stats,
        "thresholds": {
            "related": settings.similarity_threshold,
            "high_overlap": settings.similarity_high_threshold,
        },
    }


@router.post(
    "/compute-similarity",
    summary="Compute content similarity",
    description="Computes pairwise content embedding similarity for all items in a stage. Admin-only.",
)
async def compute_similarity(
    request: Request,
    user: str = Depends(require_admin),
    threshold: float = Query(0.75, ge=0.0, le=1.0),
    stage: str = Query("prod", description="Stage to compare: prod, event, or dev"),
):
    db = request.app.state.db
    logger.info("compute_similarity_started", component="rcars", action="compute_similarity",
                threshold=threshold, stage=stage, triggered_by=user)
    result = db.compute_content_similarity(threshold=threshold, stage=stage)
    return result


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
