"""Catalog routes — browsing, curation, refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from rcars.api.middleware.auth import require_auth, require_curator, require_admin
from rcars.api.schemas import (
    StatusResponse, JobResponse, CatalogItemResponse, CatalogStatsResponse,
    SimilarItemsResponse, InfraSearchResponse, FacetsResponse,
    WorkloadMappingsResponse, UnmappedWorkloadsResponse,
    InfraStatsResponse, ContentPathResponse,
)

router = APIRouter(prefix="/catalog")


@router.get(
    "",
    summary="List catalog items",
    description=(
        "Paginated catalog listing with filtering by stage, cloud provider, workloads, "
        "AgnosticD config type, and curator content filters. "
        "Text search matches on CI name and display name (case-insensitive)."
    ),
)
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
    include_retired: str = Query("false", description="Retired items: false (exclude), true (include), only (retired only)"),
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


@router.get(
    "/stats",
    summary="Catalog statistics",
    description="Returns catalog-wide statistics: total items, analyzed count, Showroom coverage, staleness.",
    response_model=CatalogStatsResponse,
)
async def catalog_stats(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return db.get_db_currency()


@router.get(
    "/search/infrastructure",
    summary="Search by infrastructure metadata",
    description=(
        "Searches catalog items by infrastructure attributes: workload products, "
        "AgnosticD config type, cloud provider, OCP version, and OS image. "
        "Returns items with their resolved workload mappings."
    ),
    response_model=InfraSearchResponse,
)
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


@router.get(
    "/facets",
    summary="Get filter facets",
    description="Returns distinct values for filter dropdowns: workloads, AgnosticD configs, cloud providers, OS images.",
    response_model=FacetsResponse,
)
async def catalog_facets(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return db.get_catalog_facets()


@router.get(
    "/workload-mappings",
    summary="List workload mappings",
    description="Returns all workload role-to-product mappings and aliases used for infrastructure search.",
    response_model=WorkloadMappingsResponse,
)
async def list_workload_mappings(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return {"mappings": db.list_workload_mappings(), "aliases": db.list_workload_aliases()}


@router.get(
    "/workload-mappings/unmapped",
    summary="List unmapped workload roles",
    description="Returns workload roles discovered in catalog items that have no product mapping yet. Curator-only.",
    response_model=UnmappedWorkloadsResponse,
)
async def list_unmapped_workloads(request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    return {"unmapped": db.get_unmapped_workloads()}


class WorkloadMappingRequest(BaseModel):
    workload_role: str = Field(max_length=200)
    product_name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=100)


@router.post(
    "/workload-mappings",
    summary="Add or update workload mapping",
    description="Creates or updates a workload role-to-product mapping. Curator-only.",
    response_model=StatusResponse,
)
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


@router.delete(
    "/workload-mappings/{role}",
    summary="Delete workload mapping",
    description="Removes a workload role-to-product mapping. Admin-only.",
    response_model=StatusResponse,
)
async def delete_workload_mapping(role: str, request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    db.delete_workload_mapping(role)
    return {"status": "ok"}


@router.get(
    "/infra-stats",
    summary="Infrastructure metadata coverage",
    description="Returns statistics on infrastructure metadata coverage across the catalog.",
    response_model=InfraStatsResponse,
)
async def infra_stats(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return db.get_infra_stats()


@router.get(
    "/{ci_name}/similar",
    summary="Find similar catalog items",
    description="Returns catalog items with similar content based on vector embedding similarity.",
    response_model=SimilarItemsResponse,
    responses={404: {"description": "Catalog item not found"}},
)
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


@router.get(
    "/{ci_name}",
    summary="Get catalog item details",
    description=(
        "Returns full catalog item with LLM analysis, enrichment tags, "
        "workload mappings, ACL groups, and reporting metrics (provisions, cost, sales impact)."
    ),
    response_model=CatalogItemResponse,
    responses={404: {"description": "Catalog item not found"}},
)
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


@router.get(
    "/{ci_name}/analysis",
    summary="Get content analysis",
    description="Returns the LLM-generated content analysis for a catalog item (summary, audience, topics, duration estimate).",
    responses={404: {"description": "No analysis found for this item"}},
)
async def get_analysis(ci_name: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    analysis = db.get_showroom_analysis(ci_name)
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found")
    return analysis


@router.post(
    "/refresh",
    summary="Refresh catalog from Babylon",
    description="Triggers a full catalog refresh from the Babylon cluster CRDs. Admin-only. Returns a job_id for tracking.",
    response_model=JobResponse,
)
async def refresh_catalog(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="refresh", queue="ops", created_by=user)
    await arq_redis.enqueue_job("run_catalog_refresh", job_id=job_id, _queue_name="arq:queue:scan")
    return {"job_id": job_id}


class TagRequest(BaseModel):
    tag_type: str = Field(max_length=100)
    tag_value: str = Field(max_length=100)


@router.post(
    "/{ci_name}/tags",
    summary="Add enrichment tag",
    description="Adds a curation tag to a catalog item (e.g., audience, use-case). Curator-only.",
    response_model=StatusResponse,
)
async def add_tag(ci_name: str, body: TagRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.add_enrichment_tag(ci_name, body.tag_type, body.tag_value, added_by=user)
    return {"status": "ok"}


@router.delete(
    "/{ci_name}/tags/{tag_id}",
    summary="Remove enrichment tag",
    description="Removes a curation tag from a catalog item by tag ID. Curator-only.",
    response_model=StatusResponse,
)
async def remove_tag(ci_name: str, tag_id: int, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.remove_enrichment_tag_by_id(tag_id, ci_name=ci_name)
    return {"status": "ok"}


class NoteRequest(BaseModel):
    note: str = Field(max_length=2000)


@router.put(
    "/{ci_name}/note",
    summary="Set curator note",
    description="Sets or updates the curator's free-text note on a catalog item. Curator-only.",
    response_model=StatusResponse,
)
async def set_note(ci_name: str, body: NoteRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_enrichment_note(ci_name, body.note)
    return {"status": "ok"}


@router.post(
    "/{ci_name}/flag",
    summary="Flag item for review",
    description="Flags a catalog item for curator review. Curator-only.",
    response_model=StatusResponse,
)
async def flag_item(ci_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_enrichment_review_flag(ci_name, True)
    return {"status": "ok"}


class OverrideUrlRequest(BaseModel):
    url: str = Field(max_length=500, pattern=r'^https?://')


@router.post(
    "/{ci_name}/override-url",
    summary="Override Showroom URL",
    description="Sets a custom Showroom URL override for a catalog item (e.g., when auto-detection fails). Curator-only.",
    response_model=StatusResponse,
)
async def override_url(ci_name: str, body: OverrideUrlRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_showroom_url_override(ci_name, body.url)
    return {"status": "ok"}


class DurationRequest(BaseModel):
    duration_min: int | None = None


@router.put(
    "/{ci_name}/duration",
    summary="Set curated duration",
    description="Sets a curator-curated duration estimate (in minutes) for a catalog item. Curator-only.",
    response_model=StatusResponse,
)
async def set_duration(ci_name: str, body: DurationRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_curated_duration(ci_name, body.duration_min, updated_by=user)
    return {"status": "ok"}


class ContentPathRequest(BaseModel):
    path: str | None = Field(default=None, max_length=500)

    @field_validator("path")
    @classmethod
    def reject_traversal(cls, v: str | None) -> str | None:
        if v and (".." in v or v.startswith("/")):
            raise ValueError("Path must not contain '..' or start with '/'")
        return v


@router.post(
    "/{ci_name}/content-path",
    summary="Set content path",
    description=(
        "Sets a custom content path within the Showroom repo for analysis. "
        "Use Re-analyze to scan with the new path. Curator-only."
    ),
    response_model=ContentPathResponse,
)
async def set_content_path(ci_name: str, body: ContentPathRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    path = body.path.strip().rstrip("/") if body.path else None
    db.set_content_path(ci_name, path)
    return {"status": "ok", "content_path": path, "job_id": ""}
