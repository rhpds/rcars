"""Catalog routes — browsing, curation, refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel
from rcars.api.middleware.auth import require_auth, require_curator, require_admin

router = APIRouter(prefix="/catalog")


@router.get("")
async def list_catalog(
    request: Request,
    user: str = Depends(require_auth),
    search: str | None = Query(None, description="Case-insensitive text search on name and CI"),
    stage: str | None = Query(None, description="Comma-separated stages: prod,dev,event"),
    cloud_provider: str | None = Query(None, description="Filter by cloud provider"),
    workloads: str | None = Query(None, description="Comma-separated product names (AND semantics)"),
    agd_config: str | None = Query(None, description="Filter by AgnosticD config type"),
    content_filter: str | None = Query(None, description="Curator filter: unanalyzed, scan_failures, stale, needs_review"),
    category: str | None = None,
    include_retired: bool = Query(False, description="Include retired catalog items"),
    limit: int = Query(50, le=2000),
    offset: int = Query(0, ge=0),
):
    db = request.app.state.db
    stage_list = [s.strip() for s in stage.split(",")] if stage else None
    workload_list = [w.strip() for w in workloads.split(",")] if workloads else None

    return db.list_catalog_items_filtered(
        search=search,
        stages=stage_list,
        cloud_provider=cloud_provider,
        agd_config=agd_config,
        workloads=workload_list,
        content_filter=content_filter,
        category=category,
        limit=limit,
        offset=offset,
        include_retired=include_retired,
    )


@router.get("/stats")
async def catalog_stats(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return db.get_db_currency()


@router.get("/search/infrastructure")
async def search_infrastructure(
    request: Request,
    user: str = Depends(require_auth),
    workloads: str | None = Query(None, description="Comma-separated product names or aliases (AND)"),
    agd_config: str | None = Query(None, description="Config type: openshift-workloads, openshift-cluster, etc."),
    cloud_provider: str | None = Query(None),
    ocp_version: str | None = Query(None, description="OCP version prefix, e.g. 4.20"),
    os_image: str | None = Query(None, description="OS image prefix, e.g. rhel-9"),
    stage: str | None = None,
    limit: int = Query(50, le=200),
):
    db = request.app.state.db
    workload_list = [w.strip() for w in workloads.split(",")] if workloads else None
    items = db.search_by_infrastructure(
        workloads=workload_list,
        agd_config=agd_config,
        cloud_provider=cloud_provider,
        ocp_version=ocp_version,
        os_image=os_image,
        stage=stage,
        limit=limit,
    )
    mappings_by_role = {m["workload_role"]: m for m in db.list_workload_mappings()}
    for item in items:
        raw_workloads = db.get_workloads(item["ci_name"])
        item["workloads"] = [
            {
                "role": w["workload_role"],
                "product_name": mappings_by_role.get(w["workload_role"], {}).get("product_name"),
                "mapped": w["workload_role"] in mappings_by_role,
            }
            for w in raw_workloads
        ]
    return {"items": items, "total": len(items)}


@router.get("/facets")
async def catalog_facets(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return db.get_catalog_facets()


@router.get("/workload-mappings")
async def list_workload_mappings(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return {"mappings": db.list_workload_mappings(), "aliases": db.list_workload_aliases()}


@router.get("/workload-mappings/unmapped")
async def list_unmapped_workloads(request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    return {"unmapped": db.get_unmapped_workloads()}


class WorkloadMappingRequest(BaseModel):
    workload_role: str
    product_name: str
    description: str | None = None
    category: str | None = None


@router.post("/workload-mappings")
async def add_workload_mapping(
    body: WorkloadMappingRequest, request: Request, user: str = Depends(require_curator),
):
    db = request.app.state.db
    db.upsert_workload_mapping(
        workload_role=body.workload_role,
        product_name=body.product_name,
        description=body.description,
        category=body.category,
        added_by=user,
    )
    return {"status": "ok"}


@router.delete("/workload-mappings/{role}")
async def delete_workload_mapping(role: str, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    db.delete_workload_mapping(role)
    return {"status": "ok"}


@router.get("/infra-stats")
async def infra_stats(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return db.get_infra_stats()


@router.get("/{ci_name}/similar")
async def get_similar_items(
    ci_name: str,
    request: Request,
    user: str = Depends(require_auth),
    min_score: float = Query(0.75, ge=0.0, le=1.0),
):
    db = request.app.state.db
    item = db.get_catalog_item(ci_name)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    similar = db.get_similar_items(ci_name, min_score=min_score)
    return {"ci_name": ci_name, "similar": similar, "count": len(similar)}


@router.get("/{ci_name}")
async def get_catalog_item(ci_name: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    item = db.get_catalog_item(ci_name)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    analysis = db.get_showroom_analysis(ci_name)
    tags = db.get_enrichment_tags(ci_name)
    workloads = db.get_workloads(ci_name) if item.get("is_agd_v2") else []
    acl_groups = db.get_acl_groups(ci_name) if item.get("is_agd_v2") else []
    from rcars.services.reporting_sync import extract_base_name, compute_sales_impact
    base_name = extract_base_name(ci_name)
    reporting = db.get_reporting_metrics(base_name)
    if reporting:
        reporting["sales_impact"] = compute_sales_impact(float(reporting.get("closed_amount", 0) or 0))

    return {**item, "analysis": analysis, "tags": tags,
            "workloads": workloads, "acl_groups": acl_groups,
            "reporting": reporting}


@router.get("/{ci_name}/analysis")
async def get_analysis(ci_name: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    analysis = db.get_showroom_analysis(ci_name)
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found")
    return analysis


@router.post("/refresh")
async def refresh_catalog(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="refresh", queue="ops", created_by=user)
    await arq_redis.enqueue_job("run_catalog_refresh", job_id=job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


class TagRequest(BaseModel):
    tag_type: str
    tag_value: str


@router.post("/{ci_name}/tags")
async def add_tag(ci_name: str, body: TagRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.add_enrichment_tag(ci_name, body.tag_type, body.tag_value, added_by=user)
    return {"status": "ok"}


@router.delete("/{ci_name}/tags/{tag_id}")
async def remove_tag(ci_name: str, tag_id: int, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.remove_enrichment_tag_by_id(tag_id, ci_name=ci_name)
    return {"status": "ok"}


class NoteRequest(BaseModel):
    note: str


@router.put("/{ci_name}/note")
async def set_note(ci_name: str, body: NoteRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_enrichment_note(ci_name, body.note)
    return {"status": "ok"}


@router.post("/{ci_name}/flag")
async def flag_item(ci_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_enrichment_review_flag(ci_name, True)
    return {"status": "ok"}


class OverrideUrlRequest(BaseModel):
    url: str


@router.post("/{ci_name}/override-url")
async def override_url(ci_name: str, body: OverrideUrlRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_showroom_url_override(ci_name, body.url)
    return {"status": "ok"}


class DurationRequest(BaseModel):
    duration_min: int | None = None


@router.put("/{ci_name}/duration")
async def set_duration(ci_name: str, body: DurationRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_curated_duration(ci_name, body.duration_min, updated_by=user)
    return {"status": "ok"}


class ContentPathRequest(BaseModel):
    path: str | None


@router.post("/{ci_name}/content-path")
async def set_content_path(ci_name: str, body: ContentPathRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    path = body.path.strip().rstrip("/") if body.path else None
    db.set_content_path(ci_name, path)
    job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
    await arq_redis.enqueue_job("run_analysis", job_id=job_id, ci_name=ci_name, _queue_name="arq:queue:scan")
    return {"status": "ok", "content_path": path, "job_id": job_id}
