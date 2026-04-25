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
    stage: str | None = None,
    category: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    db = request.app.state.db
    items = db.list_catalog_items(stage=stage, category=category)
    total = len(items)
    page = items[offset : offset + limit]
    return {"items": page, "total": total}


@router.get("/stats")
async def catalog_stats(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    return db.get_db_currency()


@router.get("/{ci_name}")
async def get_catalog_item(ci_name: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    item = db.get_catalog_item(ci_name)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    analysis = db.get_showroom_analysis(ci_name)
    tags = db.get_enrichment_tags(ci_name)
    return {**item, "analysis": analysis, "tags": tags}


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
    await arq_redis.enqueue_job("run_catalog_refresh", job_id=job_id, _queue_name="ops")
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
    db.remove_enrichment_tag_by_id(tag_id)
    return {"status": "ok"}


class NoteRequest(BaseModel):
    note: str


@router.put("/{ci_name}/note")
async def set_note(ci_name: str, body: NoteRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_enrichment_note(ci_name, body.note, updated_by=user)
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
