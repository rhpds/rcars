"""Admin routes — token usage, jobs, worker health, scheduled maintenance."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request, Query
from rcars.api.middleware.auth import require_admin
from rcars.config import Settings

logger = structlog.get_logger()

router = APIRouter(prefix="/admin")


@router.get("/token-usage")
async def token_usage(
    request: Request,
    user: str = Depends(require_admin),
    days: int = Query(30, ge=1, le=365),
):
    db = request.app.state.db
    stats = db.get_token_stats(days=days)
    queries = db.get_recent_queries(days=days)
    return {"stats": stats, "recent_queries": queries, "days": days}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    job = db.get_job(job_id)
    if not job:
        return {"error": "not found"}
    return job


@router.get("/jobs")
async def list_jobs(
    request: Request,
    user: str = Depends(require_admin),
    limit: int = Query(50, le=200),
    job_type: str | None = None,
):
    db = request.app.state.db
    jobs = db.list_jobs(limit=limit, job_type=job_type)
    return {"items": jobs, "total": len(jobs)}


@router.get("/workers")
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


@router.get("/scan-progress")
async def scan_progress(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db

    # Scope to the most recent scan/rescan batch by finding the latest parent job
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


@router.get("/queries")
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


@router.post("/run-maintenance")
async def run_maintenance(request: Request, user: str = Depends(require_admin)):
    """Manually trigger the nightly maintenance pipeline (refresh → stale check → re-analyze)."""
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="maintenance", queue="ops", created_by=user)
    await arq_redis.enqueue_job(
        "run_nightly_pipeline", job_id=job_id, _queue_name="arq:queue:scan"
    )
    return {"job_id": job_id}


@router.post("/sync-reporting")
async def sync_reporting(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="reporting_sync", queue="ops", created_by=user)
    await arq_redis.enqueue_job("run_reporting_sync_job", job_id=job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


@router.post("/scan-workloads")
async def scan_workloads(request: Request, user: str = Depends(require_admin)):
    """Trigger workload repo scan (clone agDv2 repos, analyze roles, update mappings)."""
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


@router.get("/overlap")
async def overlap_report(
    request: Request,
    user: str = Depends(require_admin),
    min_score: float = Query(0.75, ge=0.0, le=1.0),
):
    db = request.app.state.db
    pairs = db.get_overlap_report(min_score=min_score)
    stats = db.get_similarity_stats()
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


@router.post("/compute-similarity")
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


@router.get("/schedule")
async def schedule_status(request: Request, user: str = Depends(require_admin)):
    """Return scheduled maintenance pipeline status and last run info."""
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


@router.get("/llm-provider")
async def llm_provider_status(request: Request, user: str = Depends(require_admin)):
    """Return active LLM provider configuration and available models."""
    settings = Settings()
    from rcars.config import fetch_litemaas_models
    litemaas_models = sorted(fetch_litemaas_models(settings)) if settings.use_litemaas else []
    return {
        "litemaas_enabled": settings.use_litemaas,
        "litemaas_url": settings.litemaas_url or None,
        "litemaas_models": litemaas_models,
        "vertex_enabled": settings.use_vertex,
        "vertex_region": settings.cloud_ml_region if settings.use_vertex else None,
        "analysis_model": settings.model,
        "triage_model": settings.triage_model,
        "rationale_model": settings.rationale_model,
    }


@router.get("/reporting-status")
async def reporting_status(request: Request, user: str = Depends(require_admin)):
    """Return reporting sync status and configuration."""
    db = request.app.state.db
    settings = Settings()
    status = db.get_reporting_sync_status()
    from datetime import datetime, timedelta
    sales_start = (datetime.now() - timedelta(days=settings.reporting_sales_days)).strftime("%Y-%m-%d")
    quarter_start = (datetime.now() - timedelta(days=settings.reporting_provisions_days)).strftime("%Y-%m-%d")
    return {
        "configured": bool(settings.reporting_mcp_url),
        "total": status["total"] if status else 0,
        "last_synced": status["last_synced"] if status else None,
        "provisions_window": f"{settings.reporting_sales_days}d (from {sales_start})",
        "quarter_window": f"{settings.reporting_provisions_days}d (from {quarter_start})",
        "sales_window": f"{settings.reporting_sales_days}d (from {sales_start})",
    }
