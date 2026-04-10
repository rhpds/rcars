import html as _html
import threading
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

_item_analyze_status: dict = {}
# key: ci_name → {"running": bool, "result": str | None, "color": str | None}


def _get_db_dependency() -> Database | None:
    from rcars.web.app import get_db
    return get_db()


def _base_context(request: Request, db: Database, user: str) -> dict:
    settings = Settings()
    return {
        "request": request,
        "current_user": user,
        "is_curator": True,
        "is_admin": settings.is_admin(user),
        "active_page": "curate",
        "db_status": db.get_db_currency(stale_days=settings.stale_days),
    }


def _ci_safe(ci_name: str) -> str:
    """Convert ci_name to a safe HTML id fragment."""
    return ci_name.replace(".", "-").replace("/", "-")


def _analyze_section_running(ci_name: str) -> str:
    ci_safe = _ci_safe(ci_name)
    return f"""<div id="analyze-section-{ci_safe}"
     hx-get="/curate/analyze/status?ci_name={ci_name}"
     hx-trigger="every 2s"
     hx-target="this"
     hx-swap="outerHTML"
     style="display:flex;flex-direction:column;gap:4px;">
  <button style="background:#2a1a40;color:#b794f4;border:1px solid #4a2a70;padding:5px 12px;border-radius:4px;font-size:12px;opacity:0.5;cursor:not-allowed;" disabled>Re-analyze &#8635;</button>
  <span style="font-size:11px;color:#b794f4;">&#8635; Analyzing\u2026</span>
</div>"""


def _analyze_section_idle(ci_name: str, msg: str = "", color: str = "") -> str:
    ci_safe = _ci_safe(ci_name)
    status_span = f'<span style="font-size:11px;color:{color};">{_html.escape(msg)}</span>' if msg else ""
    return f"""<div id="analyze-section-{ci_safe}" style="display:flex;flex-direction:column;gap:4px;">
  <button style="background:#2a1a40;color:#b794f4;border:1px solid #4a2a70;padding:5px 12px;border-radius:4px;font-size:12px;cursor:pointer;"
          hx-post="/curate/analyze"
          hx-vals='{{"ci_name": "{ci_name}"}}'
          hx-target="#analyze-section-{ci_safe}"
          hx-swap="outerHTML">Re-analyze &#8635;</button>
  {status_span}
</div>"""


def _run_item_analyze(ci_name: str, item: dict, db: Database, settings: Settings):
    global _item_analyze_status
    try:
        from rcars.analyzer import analyze_showroom
        anthropic_client = settings.get_anthropic_client()
        if not anthropic_client:
            _item_analyze_status[ci_name] = {
                "running": False,
                "result": "No Anthropic credentials configured.",
                "color": "var(--score-red)",
            }
            return
        result = analyze_showroom(
            ci_name=ci_name,
            display_name=item.get("display_name", ""),
            category=item.get("category", ""),
            product=item.get("product", ""),
            showroom_url=item["showroom_url"],
            showroom_ref=item.get("showroom_ref"),
            anthropic_client=anthropic_client,
            model=settings.model,
            clone_dir=settings.clone_dir,
        )
        if result:
            analysis = result["analysis"]
            db.upsert_showroom_analysis({
                "ci_name": result["ci_name"],
                "content_type": analysis.get("content_type"),
                "summary": analysis.get("summary"),
                "products_json": analysis.get("products"),
                "audience_json": analysis.get("audience"),
                "topics_json": analysis.get("topics"),
                "modules_json": analysis.get("modules"),
                "learning_objectives_json": analysis.get("learning_objectives"),
                "difficulty": analysis.get("difficulty"),
                "estimated_duration_min": analysis.get("estimated_duration_min"),
                "event_fit_json": analysis.get("event_fit"),
                "use_cases_json": analysis.get("use_cases"),
                "last_repo_commit": result.get("last_repo_commit"),
                "last_repo_updated": result.get("last_repo_updated"),
            })
            if result.get("ci_embedding"):
                db.store_embedding(
                    ci_name=ci_name,
                    embed_type="ci_summary",
                    content_text=result.get("ci_embedding_text", ""),
                    embedding=result["ci_embedding"],
                )
            for mod_emb in result.get("module_embeddings", []):
                db.store_embedding(
                    ci_name=ci_name,
                    embed_type="module",
                    module_title=mod_emb["module_title"],
                    content_text=mod_emb["content_text"],
                    embedding=mod_emb["embedding"],
                )
            _item_analyze_status[ci_name] = {
                "running": False,
                "result": "Analysis complete.",
                "color": "var(--score-green)",
            }
        else:
            _item_analyze_status[ci_name] = {
                "running": False,
                "result": "Analysis failed.",
                "color": "var(--score-red)",
            }
    except Exception as e:
        _item_analyze_status[ci_name] = {
            "running": False,
            "result": f"Error: {str(e)[:200]}",
            "color": "var(--score-red)",
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


@router.post("/curate/analyze", response_class=HTMLResponse)
async def trigger_item_analyze(
    ci_name: Annotated[str, Form()],
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    status = _item_analyze_status.get(ci_name, {})
    if status.get("running"):
        return HTMLResponse(_analyze_section_running(ci_name))

    # Look up the item for its metadata
    items = [i for i in db.list_catalog_items() if i["ci_name"] == ci_name]
    if not items or not items[0].get("showroom_url"):
        return HTMLResponse(_analyze_section_idle(
            ci_name,
            msg="No Showroom URL for this item.",
            color="var(--score-red)",
        ))

    _item_analyze_status[ci_name] = {"running": True, "result": None, "color": None}
    settings = Settings()
    t = threading.Thread(
        target=_run_item_analyze,
        args=(ci_name, items[0], db, settings),
        daemon=True,
    )
    t.start()
    return HTMLResponse(_analyze_section_running(ci_name))


@router.get("/curate/analyze/status", response_class=HTMLResponse)
async def item_analyze_status(
    ci_name: str = Query(...),
    user: str = Depends(require_curator),
):
    status = _item_analyze_status.get(ci_name, {})
    if status.get("running"):
        return HTMLResponse(_analyze_section_running(ci_name))
    if status.get("result") is not None:
        msg = status["result"]
        color = status["color"]
        del _item_analyze_status[ci_name]
        return HTMLResponse(_analyze_section_idle(ci_name, msg=msg, color=color))
    return HTMLResponse(_analyze_section_idle(ci_name))
