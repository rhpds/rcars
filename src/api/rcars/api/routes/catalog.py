"""Catalog routes — browsing, curation, refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator
from rcars.api.middleware.auth import require_auth, require_curator, require_admin
from rcars.api.schemas import (
    StatusResponse, JobResponse, CatalogItemResponse, CatalogStatsResponse,
    FacetsResponse,
    InfraStatsResponse, ContentPathResponse,
)
from rcars.config import Settings

router = APIRouter(prefix="/catalog")


# Identifiers may arrive as a bare Babylon ci_name (every existing caller) or as
# a prefixed content_id. Anything unprefixed still means Babylon.
_SOURCE_PREFIXES = ("babylon:", "pa:")


def _resolve_to_content_id(identifier: str, db=None) -> str:
    """Return content_id from an identifier that may be a ci_name or content_id.

    When db is provided, validates existence and raises 404 if not found.
    """
    content_id = identifier if identifier.startswith(_SOURCE_PREFIXES) else f"babylon:{identifier}"
    if db is not None:
        entity = db.get_content_entity(content_id)
        if not entity:
            raise HTTPException(status_code=404, detail=f"Item not found: {identifier}")
    return content_id


def _resolve_item(identifier: str, db) -> dict | None:
    """Resolve identifier to a full item dict, dispatching on the source prefix."""
    if identifier.startswith("pa:"):
        return db.get_portfolio_architecture(identifier)
    if identifier.startswith("babylon:"):
        return db.get_babylon_item(identifier)
    return db.get_babylon_item_by_ci_name(identifier)


@router.get(
    "",
    summary="List catalog items",
    description=(
        "Paginated catalog listing with filtering by content type, stage, cloud provider, "
        "workloads, AgnosticD config type, and curator content filters. "
        "Text search matches on CI name and display name (case-insensitive)."
    ),
)
async def list_catalog(
    request: Request,
    user: str = Depends(require_auth),
    search: str | None = Query(None, description="Case-insensitive text search on name and CI"),
    content_type: str | None = Query(None, description="Comma-separated content types: lab,demo,workshop"),
    stage: str | None = Query(None, description="Comma-separated stages: prod,dev,event"),
    cloud_provider: str | None = Query(None, description="Filter by cloud provider"),
    workloads: str | None = Query(None, description="Comma-separated product names (AND semantics)"),
    agd_config: str | None = Query(None, description="Filter by AgnosticD config type"),
    content_filter: str | None = Query(None, description="Curator filter: unanalyzed, scan_failures, stale, needs_review"),
    category: str | None = None,
    solutions: str | None = Query(None, description="Comma-separated solution areas (architecture items only)"),
    verticals: str | None = Query(None, description="Comma-separated industry verticals (architecture items only)"),
    audience: str | None = Query(None, description="Comma-separated target audiences"),
    include_retired: str = Query("false", description="Retired items: false (exclude), true (include), only (retired only)"),
    limit: int = Query(50, le=2000),
    offset: int = Query(0, ge=0),
):
    db = request.app.state.db
    settings: Settings = request.app.state.settings
    if stage:
        stage_list = [s.strip() for s in stage.split(",")]
        if not settings.is_curator(user) and not settings.is_admin(user):
            stage_list = [s for s in stage_list if s == "prod"]
            if not stage_list:
                stage_list = ["prod"]
    else:
        stage_list = None
    workload_list = [w.strip() for w in workloads.split(",")] if workloads else None
    content_type_list = [t.strip() for t in content_type.split(",")] if content_type else None
    solutions_list = [s.strip() for s in solutions.split(",")] if solutions else None
    verticals_list = [v.strip() for v in verticals.split(",")] if verticals else None
    audience_list = [a.strip() for a in audience.split(",")] if audience else None

    return db.list_content_entities_filtered(
        search=search,
        content_types=content_type_list,
        stages=stage_list,
        cloud_provider=cloud_provider,
        agd_config=agd_config,
        workloads=workload_list,
        content_filter=content_filter,
        category=category,
        solutions=solutions_list,
        verticals=verticals_list,
        audience=audience_list,
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
    "/facets",
    summary="Get filter facets",
    description="Returns distinct values for filter dropdowns: workloads, AgnosticD configs, cloud providers, OS images.",
    response_model=FacetsResponse,
)
async def catalog_facets(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return db.get_catalog_facets()


@router.get(
    "/infrastructure",
    summary="List infrastructure catalog",
    description=(
        "Returns the infrastructure catalog — Ansible workload roles and base configs scanned from AgnosticD v2 — "
        "with `item_count` showing how many catalog items deploy or use each entry.\n\n"
        "Two types of infrastructure entries:\n"
        "- **workload** — An Ansible role that installs a product on an existing cluster "
        "(e.g. `ocp4_workload_openshift_ai`, `ocp4_workload_acs`)\n"
        "- **config** — A base environment config that provisions infrastructure "
        "(e.g. `ocp4-cluster`, `cloud-vms-base`)\n\n"
        "Use the `type` filter to list only workloads or only configs. "
        "Use `has_mappings=true` to find entries linked to catalog items, or `false` to find orphans.\n\n"
        "For semantic search (e.g. 'what deploys OpenShift AI?'), use `POST /advisor/chat` instead — "
        "this endpoint only supports text-match filtering."
    ),
)
async def list_infrastructure(
    request: Request,
    user: str = Depends(require_auth),
    type: str | None = Query(None, description="Filter by type: 'workload' or 'config'", examples=["workload"]),
    category: str | None = Query(None, description="Filter by category (e.g. 'ai_ml', 'security', 'platform')", examples=["ai_ml"]),
    collection: str | None = Query(None, description="Filter by source collection (e.g. 'agnosticv_workloads')", examples=["agnosticv_workloads"]),
    search: str | None = Query(None, description="Text search across name, description, products, and capabilities", examples=["openshift ai"]),
    has_mappings: bool | None = Query(None, description="true = only entries linked to catalog items, false = orphans only"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum results to return"),
):
    db = request.app.state.db
    items = db.get_infrastructure_with_item_counts(
        type_filter=type, category_filter=category,
        collection_filter=collection, search=search,
        has_mappings=has_mappings, limit=limit,
    )
    return {"items": items, "total": len(items)}


@router.get(
    "/infra-stats",
    summary="Infrastructure catalog statistics",
    description=(
        "Returns statistics on the infrastructure catalog: total workload roles, "
        "total base configs, category breakdown, and how many entries are linked to catalog items."
    ),
    response_model=InfraStatsResponse,
)
async def infra_stats(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return db.get_infra_stats()


@router.get(
    "/infrastructure/{role_name}/items",
    summary="Catalog items linked to an infrastructure entry",
    description=(
        "Returns catalog items that deploy or use the given infrastructure entry.\n\n"
        "The `role_name` path parameter is the infrastructure entry's primary key:\n"
        "- For **workload** entries: the Ansible role name (e.g. `ocp4_workload_openshift_ai`)\n"
        "- For **config** entries: the config directory name (e.g. `ocp4-cluster`)\n\n"
        "Discover valid names from `GET /catalog/infrastructure`."
    ),
)
async def infrastructure_items(
    request: Request,
    role_name: str = Path(description="Infrastructure entry name — the Ansible role name (for workloads) or config directory name (for configs)", examples=["ocp4_workload_openshift_ai", "ocp4-cluster"]),
    user: str = Depends(require_auth),
):
    db = request.app.state.db
    infra = db.get_infrastructure(role_name)
    if not infra:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Infrastructure entry '{role_name}' not found")

    with db.pool.connection() as conn:
        if infra["type"] == "config":
            rows = conn.execute("""
                SELECT ce.content_id, ce.display_name, ce.content_type, bi.ci_name, bi.stage
                FROM babylon_items bi
                JOIN content_entities ce ON ce.content_id = bi.content_id AND ce.retired_at IS NULL
                WHERE bi.agd_config = %(role_name)s
                ORDER BY ce.display_name
            """, {"role_name": role_name}).fetchall()
        else:
            rows = conn.execute("""
                SELECT ce.content_id, ce.display_name, ce.content_type, bi.ci_name, bi.stage
                FROM babylon_item_workloads biw
                JOIN babylon_items bi ON bi.content_id = biw.content_id
                JOIN content_entities ce ON ce.content_id = bi.content_id AND ce.retired_at IS NULL
                WHERE biw.workload_role = %(role_name)s
                ORDER BY ce.display_name
            """, {"role_name": role_name}).fetchall()

    return {"role_name": role_name, "type": infra["type"], "items": rows, "total": len(rows)}


@router.get(
    "/{identifier}",
    summary="Get catalog item details",
    description=(
        "Returns full catalog item with LLM analysis, enrichment tags, "
        "workload mappings, ACL groups, and performance data (provisions, cost, sales impact). "
        "Accepts content_id (babylon:...) or legacy ci_name."
    ),
    response_model=CatalogItemResponse,
    responses={404: {"description": "Catalog item not found"}},
)
async def get_catalog_item(identifier: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    settings = request.app.state.settings
    item = _resolve_item(identifier, db)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    content_id = item["content_id"]

    if item.get("source") == "portfolio_arch":
        repo = settings.osspa_examples_repo_url.removesuffix(".git")
        detail_page = item.get("detail_page") or ""
        return {
            **item,
            "analysis": db.get_architecture_analysis(content_id),
            "tags": db.get_enrichment_tags(content_id),
            "workloads": [],
            "acl_groups": [],
            "reporting": None,
            "source_url": (
                f"{repo}/-/blob/{settings.osspa_examples_ref}/{detail_page}"
                if detail_page else None
            ),
        }

    analysis = db.get_showroom_analysis(content_id)
    tags = db.get_enrichment_tags(content_id)
    workloads = db.get_workloads(content_id) if item.get("is_agd_v2") else []
    acl_groups = db.get_acl_groups(content_id) if item.get("is_agd_v2") else []
    performance_channels = db.get_performance_channels(content_id)
    performance_score = db.get_performance_score(content_id)
    reporting = None
    if performance_channels or performance_score:
        # Build a reporting-compatible dict from performance data
        rhdp = next((ch for ch in performance_channels if ch.get("channel") == "rhdp"), None)
        reporting = {}
        if rhdp:
            reporting.update({
                "provisions": rhdp.get("provisions", 0),
                "unique_users": rhdp.get("unique_users", 0),
                "requests": rhdp.get("requests", 0),
                "experiences": rhdp.get("experiences", 0),
                "pipeline_touched": rhdp.get("pipeline_touched", 0),
                "closed_amount": rhdp.get("closed_amount", 0),
                "total_cost": rhdp.get("total_cost", 0),
                "avg_cost_per_provision": rhdp.get("avg_cost_per_provision", 0),
                "success_ratio": rhdp.get("success_ratio", 0),
            })
        if performance_score:
            reporting["performance_score"] = performance_score.get("performance_score", 0)
            reporting["score_breakdown"] = performance_score.get("score_breakdown")
        from rcars.services.reporting_sync import compute_sales_impact
        reporting["sales_impact"] = compute_sales_impact(float(reporting.get("closed_amount", 0) or 0))

    return {**item, "analysis": analysis, "tags": tags,
            "workloads": workloads, "acl_groups": acl_groups,
            "reporting": reporting}


@router.get(
    "/{identifier}/analysis",
    summary="Get content analysis",
    description="Returns the LLM-generated content analysis for a catalog item (summary, audience, topics, duration estimate).",
    responses={404: {"description": "No analysis found for this item"}},
)
async def get_analysis(identifier: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    content_id = _resolve_to_content_id(identifier, db)
    if content_id.startswith("pa:"):
        analysis = db.get_architecture_analysis(content_id)
    else:
        analysis = db.get_showroom_analysis(content_id)
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
    "/{identifier}/tags",
    summary="Add enrichment tag",
    description="Adds a curation tag to a catalog item (e.g., audience, use-case). Curator-only.",
    response_model=StatusResponse,
)
async def add_tag(identifier: str, body: TagRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _resolve_to_content_id(identifier, db)
    db.add_enrichment_tag(content_id, body.tag_type, body.tag_value, added_by=user)
    return {"status": "ok"}


@router.delete(
    "/{identifier}/tags/{tag_id}",
    summary="Remove enrichment tag",
    description="Removes a curation tag from a catalog item by tag ID. Curator-only.",
    response_model=StatusResponse,
)
async def remove_tag(identifier: str, tag_id: int, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _resolve_to_content_id(identifier, db)
    db.remove_enrichment_tag_by_id(tag_id, content_id=content_id)
    return {"status": "ok"}


class NoteRequest(BaseModel):
    note: str = Field(max_length=2000)


@router.put(
    "/{identifier}/note",
    summary="Set curator note",
    description="Sets or updates the curator's free-text note on a catalog item. Curator-only.",
    response_model=StatusResponse,
)
async def set_note(identifier: str, body: NoteRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _resolve_to_content_id(identifier, db)
    db.set_enrichment_note(content_id, body.note)
    return {"status": "ok"}


@router.post(
    "/{identifier}/flag",
    summary="Flag item for review",
    description="Flags a catalog item for curator review. Curator-only.",
    response_model=StatusResponse,
)
async def flag_item(identifier: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _resolve_to_content_id(identifier, db)
    db.set_enrichment_review_flag(content_id, True)
    return {"status": "ok"}


class OverrideUrlRequest(BaseModel):
    url: str = Field(max_length=500, pattern=r'^https?://')


@router.post(
    "/{identifier}/override-url",
    summary="Override Showroom URL",
    description="Sets a custom Showroom URL override for a catalog item (e.g., when auto-detection fails). Curator-only.",
    response_model=StatusResponse,
)
async def override_url(identifier: str, body: OverrideUrlRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _resolve_to_content_id(identifier, db)
    db.set_showroom_url_override(content_id, body.url)
    return {"status": "ok"}


class DurationRequest(BaseModel):
    duration_min: int | None = None


@router.put(
    "/{identifier}/duration",
    summary="Set curated duration",
    description="Sets a curator-curated duration estimate (in minutes) for a catalog item. Curator-only.",
    response_model=StatusResponse,
)
async def set_duration(identifier: str, body: DurationRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _resolve_to_content_id(identifier, db)
    db.set_curated_duration(content_id, body.duration_min, updated_by=user)
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
    "/{identifier}/content-path",
    summary="Set content path",
    description=(
        "Sets a custom content path within the Showroom repo for analysis. "
        "Use Re-analyze to scan with the new path. Curator-only."
    ),
    response_model=ContentPathResponse,
)
async def set_content_path(identifier: str, body: ContentPathRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    content_id = _resolve_to_content_id(identifier, db)
    path = body.path.strip().rstrip("/") if body.path else None
    db.set_content_path(content_id, path)
    return {"status": "ok", "content_path": path, "job_id": ""}
