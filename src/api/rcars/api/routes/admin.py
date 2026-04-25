"""Admin routes — token usage, jobs, worker health."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Query
from rcars.api.middleware.auth import require_admin

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

    return {
        "queue_depths": queue_depths,
        "active_jobs": len(running),
        "running_jobs": running,
        "failed_jobs_recent": len(failed),
    }
