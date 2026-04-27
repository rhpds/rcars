"""Analysis routes — scan, stale check, rescan, single-item analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from rcars.api.middleware.auth import require_admin, require_curator, require_auth
from rcars.api.streaming import JobProgressRelay, create_sse_response

router = APIRouter(prefix="/analysis")


@router.post("/scan")
async def start_scan(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis

    dedup_stats = db.get_scan_dedup_stats()
    items = db.get_items_needing_analysis()
    parent_job_id = db.create_job(job_type="scan", queue="analyze", created_by=user)

    for item in items:
        sub_job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
        await arq_redis.enqueue_job(
            "run_analysis", job_id=sub_job_id, ci_name=item["ci_name"], _queue_name="arq:queue:scan"
        )

    db.complete_job(parent_job_id, result_json={"enqueued": len(items), **dedup_stats})
    return {"job_id": parent_job_id, "enqueued": len(items), **dedup_stats}


@router.post("/check-stale")
async def check_stale(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="check_stale", queue="ops", created_by=user)
    await arq_redis.enqueue_job("run_stale_check", job_id=job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


@router.post("/rescan-stale")
async def rescan_stale(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    parent_job_id = db.create_job(job_type="rescan_stale", queue="ops", created_by=user)

    items = db.list_catalog_items()
    stale_items = [i for i in items if db.get_showroom_analysis(i["ci_name"]) and db.get_showroom_analysis(i["ci_name"]).get("is_stale")]

    for item in stale_items:
        sub_job_id = db.create_job(job_type="analyze", queue="analyze", created_by="rescan")
        await arq_redis.enqueue_job(
            "run_analysis", job_id=sub_job_id, ci_name=item["ci_name"], _queue_name="arq:queue:scan"
        )

    db.complete_job(parent_job_id, result_json={"enqueued": len(stale_items)})
    return {"job_id": parent_job_id, "enqueued": len(stale_items)}


@router.post("/{ci_name}")
async def analyze_single(ci_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
    await arq_redis.enqueue_job("run_analysis", job_id=job_id, ci_name=ci_name, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str, request: Request, user: str = Depends(require_auth)):
    relay = JobProgressRelay(request.app.state.redis)
    return create_sse_response(relay, job_id)
