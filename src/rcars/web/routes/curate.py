from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import require_curator, get_current_user
from rcars.db import Database
from rcars.config import Settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

PAGE_SIZE = 25


def _get_db_dependency() -> Database:
    from rcars.web.app import get_db
    return get_db()


def _base_context(request: Request, db: Database, user: str) -> dict:
    settings = Settings()
    return {
        "request": request,
        "current_user": user,
        "is_curator": True,
        "active_page": "curate",
        "db_status": db.get_db_currency(stale_days=settings.stale_days),
    }


@router.get("/curate", response_class=HTMLResponse)
async def curate(
    request: Request,
    q: str = "",
    status_filter: str = "all",
    page: int = 1,
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    items = db.list_catalog_items(prod_only=False)

    if q:
        q_lower = q.lower()
        items = [i for i in items if q_lower in i.get("ci_name", "").lower()
                 or q_lower in i.get("display_name", "").lower()]

    ci_names = [i["ci_name"] for i in items]
    tags_by_ci = db.get_enrichment_tags_for_items(ci_names)

    enriched = []
    for item in items:
        ci = item["ci_name"]
        tags = tags_by_ci.get(ci, [])
        note = db.get_enrichment_note(ci)
        analysis = db.get_showroom_analysis(ci) or {}
        enriched.append({
            **item,
            "tags": tags,
            "note": note,
            "enrichment_review_needed": analysis.get("enrichment_review_needed", False),
        })

    if status_filter == "needs_review":
        enriched = [i for i in enriched if i["enrichment_review_needed"]]
    elif status_filter == "untagged":
        enriched = [i for i in enriched if not i["tags"]]

    total = len(enriched)
    start = (page - 1) * PAGE_SIZE
    page_items = enriched[start:start + PAGE_SIZE]

    ctx = _base_context(request, db, user)
    ctx.update({
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "q": q,
        "status_filter": status_filter,
    })
    return templates.TemplateResponse(request=request, name="curate.html", context=ctx)


@router.post("/curate/tag", response_class=HTMLResponse)
async def add_tag(
    ci_name: Annotated[str, Form()],
    tag_type: Annotated[str, Form()],
    tag_value: Annotated[str, Form()],
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    tag_value = tag_value.strip()
    if tag_value:
        db.add_enrichment_tag(ci_name, tag_type, tag_value, user)
    return HTMLResponse("", status_code=200)


@router.delete("/curate/tag", response_class=HTMLResponse)
async def remove_tag(
    ci_name: str = Query(...),
    tag_type: str = Query(...),
    tag_value: str = Query(...),
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    db.remove_enrichment_tag(ci_name, tag_type, tag_value)
    return HTMLResponse("", status_code=200)


@router.post("/curate/note", response_class=HTMLResponse)
async def set_note(
    ci_name: Annotated[str, Form()],
    note: Annotated[str, Form()],
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    db.set_enrichment_note(ci_name, note.strip(), user)
    return HTMLResponse("", status_code=200)


@router.post("/curate/flag", response_class=HTMLResponse)
async def flag_item(
    ci_name: Annotated[str, Form()],
    needed: Annotated[str, Form()],
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    db.set_enrichment_review_needed(ci_name, needed.lower() == "true")
    return HTMLResponse("", status_code=200)
