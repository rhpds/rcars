import uuid
from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import get_current_user
from rcars.db import Database
from rcars.config import Settings
from rcars.recommender import recommend

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_sessions: dict[str, list[dict]] = {}


def _get_db_dependency() -> Database:
    """Import get_db at runtime to avoid circular import."""
    from rcars.web.app import get_db
    return get_db()


def _catalog_url(ci_name: str) -> str:
    return f"https://demo.redhat.com/catalog/{ci_name}"


def _enrich_recs(recs: list[dict], db: Database) -> list[dict]:
    """Attach enrichment tags and notes to recommendation dicts."""
    ci_names = [r["ci_name"] for r in recs if r.get("ci_name")]
    tags_by_ci = db.get_enrichment_tags_for_items(ci_names)
    enriched = []
    for rec in recs:
        ci = rec.get("ci_name", "")
        note = db.get_enrichment_note(ci)
        enriched.append({
            **rec,
            "tags": tags_by_ci.get(ci, []),
            "note": note,
            "catalog_link": _catalog_url(ci),
            "enrichment_review_needed": False,
        })
    return enriched


def _base_context(request: Request, db: Database, user: str, active_page: str) -> dict:
    settings = Settings()
    return {
        "request": request,
        "current_user": user,
        "is_curator": settings.is_curator(user),
        "active_page": active_page,
        "db_status": db.get_db_currency(stale_days=settings.stale_days),
    }


@router.get("/advisor", response_class=HTMLResponse)
async def advisor(
    request: Request,
    session_id: str | None = None,
    user: str = Depends(get_current_user),
    db: Database = Depends(_get_db_dependency),
):
    sid = session_id or str(uuid.uuid4())
    ctx = _base_context(request, db, user, "advisor")
    ctx["session_id"] = sid
    return templates.TemplateResponse(request=request, name="advisor.html", context=ctx)


@router.post("/advisor/query", response_class=HTMLResponse)
async def advisor_query(
    request: Request,
    session_id: Annotated[str, Form()],
    message: Annotated[str, Form()],
    user: str = Depends(get_current_user),
    db: Database = Depends(_get_db_dependency),
):
    settings = Settings()
    client = settings.get_anthropic_client()

    turns = _sessions.setdefault(session_id, [])
    turns.append({"role": "user", "content": message})

    description = " ".join(t["content"] for t in turns if t["role"] == "user")

    result = recommend(
        query=description,
        db=db,
        anthropic_client=client,
        model=settings.model,
        limit=10,
        prod_only=True,
    )

    raw_recs = result.get("recommendations", []) if result else []
    recs = _enrich_recs(raw_recs, db)

    turn_index = len(turns)
    overall = (result or {}).get("overall_assessment", f"Found {len(recs)} matches.")
    turns.append({
        "role": "assistant",
        "content": overall,
        "rec_ci_names": [r["ci_name"] for r in recs],
        "turn_index": turn_index,
    })

    is_curator = settings.is_curator(user)
    first_message = turns[0]["content"] if turns else message

    rec_html = templates.get_template("fragments/rec_list.html").render(
        recs=recs,
        is_curator=is_curator,
        session_id=session_id,
    )

    chat_html = templates.get_template("fragments/chat_turn.html").render(
        user_message=message,
        assistant_message=overall,
        session_id=session_id,
        turn_index=turn_index,
        first_message=first_message,
    )

    return HTMLResponse(content=rec_html + "\n" + chat_html)


@router.get("/advisor/restore/{session_id}/{turn_index}", response_class=HTMLResponse)
async def advisor_restore(
    request: Request,
    session_id: str,
    turn_index: int,
    user: str = Depends(get_current_user),
    db: Database = Depends(_get_db_dependency),
):
    """Restore the recommendation set from a previous conversation turn."""
    settings = Settings()
    turns = _sessions.get(session_id, [])

    assistant_turn = None
    for t in turns:
        if t.get("role") == "assistant" and t.get("turn_index") == turn_index:
            assistant_turn = t
            break

    if not assistant_turn:
        recs = []
    else:
        ci_names = assistant_turn.get("rec_ci_names", [])
        raw_items = [db.get_catalog_item(ci) for ci in ci_names]
        raw_items = [item for item in raw_items if item]
        recs = _enrich_recs(
            [{"ci_name": item["ci_name"],
              "display_name": item.get("display_name", item["ci_name"]),
              "fit_score": 0,
              "rationale": "(restored from history)",
              "suggested_format": item.get("category", ""),
              "duration_notes": "",
              "caveats": ""} for item in raw_items],
            db,
        )

    is_curator = settings.is_curator(user)
    rec_html = templates.get_template("fragments/rec_list.html").render(
        recs=recs,
        is_curator=is_curator,
        session_id=session_id,
    )
    return HTMLResponse(content=rec_html)
