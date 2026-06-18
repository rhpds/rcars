"""Analysis routes — scan, stale check, rescan, single-item analysis, retirement."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from rcars.api.middleware.auth import require_admin, require_curator, require_auth
from rcars.api.streaming import JobProgressRelay, create_sse_response
from rcars.workers.ops import sha_dedup_scan_items

router = APIRouter(prefix="/analysis")


WINDOW_QUARTERS = {"1q": 1, "2q": 2, "3q": 3, "1y": 4}



@router.get("/retirement")
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
):
    db = request.app.state.db
    num_q = WINDOW_QUARTERS.get(window, 4)

    if num_q < 4:
        all_items = db.list_reporting_metrics(
            sort_by="retirement_score", sort_dir="desc",
            has_prod=has_prod,
        )

        import json as _json
        for item in all_items:
            qd = item.get("quarterly_data")
            if isinstance(qd, str):
                item["quarterly_data"] = _json.loads(qd)
            elif qd is None:
                item["quarterly_data"] = {}

        from rcars.services.reporting_sync import compute_windowed_scores
        all_items = compute_windowed_scores(all_items, num_q)

        items = all_items
        if search:
            search_lower = search.lower()
            items = [i for i in items if search_lower in (i.get("display_name") or "").lower()]
        if min_score is not None:
            items = [i for i in items if (i.get("retirement_score") or 0) >= min_score]
        if category:
            cat_lower = category.lower()
            items = [i for i in items if (i.get("category") or "").lower() == cat_lower]
    else:
        items = db.list_reporting_metrics(
            sort_by=sort_by, sort_dir=sort_dir, min_score=min_score,
            category=category, has_prod=has_prod, search=search,
        )
        import json as _json
        for item in items:
            qd = item.get("quarterly_data")
            if isinstance(qd, str):
                item["quarterly_data"] = _json.loads(qd)
            elif qd is None:
                item["quarterly_data"] = {}

    base_names = [i["catalog_base_name"] for i in items]
    stages_map = db.get_stages_for_base_names(base_names)

    from rcars.services.reporting_sync import compute_sales_impact
    for item in items:
        stages = stages_map.get(item["catalog_base_name"], [])
        item["stages"] = stages
        has_showroom = any(True for s in stages if s.get("has_showroom"))
        item["has_content"] = has_showroom
        if not has_showroom:
            item["catalog_url"] = f"https://demo.redhat.com/catalog?search={item['catalog_base_name']}"
        if "sales_impact" not in item:
            item["sales_impact"] = compute_sales_impact(float(item.get("closed_amount", 0) or 0))

    allowed_sorts = {"retirement_score", "provisions", "total_cost", "closed_amount", "touched_amount", "display_name"}
    if sort_by in allowed_sorts:
        reverse = sort_dir.lower() == "desc"
        default = "" if sort_by == "display_name" else 0
        items.sort(key=lambda i: (i.get(sort_by) or default), reverse=reverse)

    for item in items:
        item.pop("quarterly_data", None)

    sync_status = db.get_reporting_sync_status()
    return {
        "items": items,
        "total": len(items),
        "synced_at": sync_status.get("last_synced") if sync_status else None,
        "summary": sync_status,
        "window": window,
    }


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
