"""Analysis routes — scan, stale check, rescan, single-item analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from rcars.api.middleware.auth import require_admin, require_curator, require_auth
from rcars.api.streaming import JobProgressRelay, create_sse_response
from rcars.workers.ops import sha_dedup_scan_items

router = APIRouter(prefix="/analysis")


@router.post("/scan")
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


@router.post("/check-stale")
async def check_stale(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="check_stale", queue="ops", created_by=user)
    await arq_redis.enqueue_job("run_stale_check", job_id=job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


@router.post("/rescan-all")
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
