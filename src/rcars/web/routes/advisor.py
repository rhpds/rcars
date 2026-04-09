import re
import uuid
from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from pathlib import Path

from rcars.web.deps import get_current_user
from rcars.db import Database
from rcars.config import Settings
from rcars.recommender import recommend

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _format_message(text: str) -> Markup:
    """Convert plain/markdown-ish text to formatted HTML."""
    if not text:
        return Markup("")

    # Split into paragraphs on double newlines
    paragraphs = re.split(r'\n{2,}', text.strip())
    html_parts = []

    for para in paragraphs:
        lines = para.strip().split('\n')

        # Check if this paragraph is a bullet list
        if all(re.match(r'^[\-\*•]\s', line.strip()) for line in lines if line.strip()):
            items = []
            for line in lines:
                item = re.sub(r'^[\-\*•]\s+', '', line.strip())
                item = _inline_format(item)
                items.append(f'<li>{item}</li>')
            html_parts.append(f'<ul>{"".join(items)}</ul>')
        # Check if this is a numbered list
        elif all(re.match(r'^\d+[\.\)]\s', line.strip()) for line in lines if line.strip()):
            items = []
            for line in lines:
                item = re.sub(r'^\d+[\.\)]\s+', '', line.strip())
                item = _inline_format(item)
                items.append(f'<li>{item}</li>')
            html_parts.append(f'<ol>{"".join(items)}</ol>')
        else:
            # Regular paragraph — join lines with <br>
            formatted_lines = [_inline_format(line) for line in lines]
            html_parts.append(f'<p>{"<br>".join(formatted_lines)}</p>')

    return Markup('\n'.join(html_parts))


def _inline_format(text: str) -> str:
    """Handle bold, italic, and inline code."""
    # **bold**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # *italic* (but not inside URLs or already-processed tags)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    # `code`
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Colon-terminated phrases at start of line → bold label
    text = re.sub(r'^([A-Z][^:]{2,30}:)\s', r'<strong>\1</strong> ', text)
    return text


templates.env.filters['format_message'] = _format_message

_sessions: dict[str, list[dict]] = {}


def _get_db_dependency() -> Database | None:
    """Import get_db at runtime to avoid circular import."""
    from rcars.web.app import get_db
    return get_db()


def _catalog_url(ci_name: str, namespace: str = "babylon-catalog-prod") -> str:
    return f"https://catalog.demo.redhat.com/catalog?item={namespace}/{ci_name}"


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
            "catalog_link": _catalog_url(ci, rec.get("catalog_namespace", "babylon-catalog-prod")),
            "enrichment_review_needed": False,
        })
    return enriched


def _base_context(request: Request, db: Database | None, user: str, active_page: str) -> dict:
    settings = Settings()
    if db:
        db_status = db.get_db_currency(stale_days=settings.stale_days)
    else:
        db_status = {"last_refresh": "no database", "is_stale": True}
    return {
        "request": request,
        "current_user": user,
        "is_curator": settings.is_curator(user),
        "is_admin": settings.is_admin(user),
        "active_page": active_page,
        "db_status": db_status,
    }


@router.get("/advisor", response_class=HTMLResponse)
async def advisor(
    request: Request,
    session_id: str | None = None,
    user: str = Depends(get_current_user),
    db: Database | None = Depends(_get_db_dependency),
):
    sid = session_id or str(uuid.uuid4())
    ctx = _base_context(request, db, user, "advisor")
    ctx["session_id"] = sid

    # Restore previous conversation if session exists
    turns = _sessions.get(sid, [])
    ctx["turns"] = turns

    # Restore last recommendations if session has them
    last_recs_html = ""
    if turns and db:
        # Find last assistant turn with rec_ci_names
        for t in reversed(turns):
            if t.get("role") == "assistant" and t.get("rec_ci_names"):
                ci_names = t["rec_ci_names"]
                raw_items = [db.get_catalog_item(ci) for ci in ci_names]
                raw_items = [item for item in raw_items if item]
                recs = _enrich_recs(
                    [{"ci_name": item["ci_name"],
                      "display_name": item.get("display_name", item["ci_name"]),
                      "catalog_namespace": item.get("catalog_namespace", "babylon-catalog-prod"),
                      "fit_score": 0,
                      "rationale": "(restored from history)",
                      "suggested_format": item.get("category", ""),
                      "duration_notes": "",
                      "caveats": ""} for item in raw_items],
                    db,
                )
                settings = Settings()
                last_recs_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs,
                    is_curator=settings.is_curator(user),
                    session_id=sid,
                )
                break
    ctx["restored_recs_html"] = last_recs_html

    return templates.TemplateResponse(request=request, name="advisor.html", context=ctx)


@router.post("/advisor/query", response_class=HTMLResponse)
async def advisor_query(
    request: Request,
    session_id: Annotated[str, Form()],
    message: Annotated[str, Form()],
    user: str = Depends(get_current_user),
    db: Database | None = Depends(_get_db_dependency),
):
    settings = Settings()
    turns = _sessions.setdefault(session_id, [])
    turns.append({"role": "user", "content": message})
    first_message = turns[0]["content"] if turns else message

    def _error_response(error_msg: str) -> HTMLResponse:
        turn_index = len(turns)
        turns.append({"role": "assistant", "content": error_msg, "rec_ci_names": [], "turn_index": turn_index})
        rec_html = (
            '<div class="pane-label">Recommendations</div>'
            f'<p style="color:var(--score-red);font-size:14px;">{error_msg}</p>'
        )
        chat_html = templates.get_template("fragments/chat_turn.html").render(
            user_message=message, assistant_message=error_msg,
            session_id=session_id, turn_index=turn_index, first_message=first_message,
        )
        return HTMLResponse(content=rec_html + "\n" + chat_html)

    if not db:
        return _error_response("Database not configured. Set RCARS_DATABASE_URL.")

    client = settings.get_anthropic_client()
    if not client:
        return _error_response("No Anthropic credentials configured. Set ANTHROPIC_VERTEX_PROJECT_ID or ANTHROPIC_API_KEY.")

    description = " ".join(t["content"] for t in turns if t["role"] == "user")

    try:
        result = recommend(
            query=description,
            db=db,
            anthropic_client=client,
            model=settings.model,
            limit=10,
            prod_only=True,
        )
    except Exception as e:
        import logging
        logging.getLogger("rcars.web").exception("Recommendation failed")
        result = None

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
    db: Database | None = Depends(_get_db_dependency),
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
              "catalog_namespace": item.get("catalog_namespace", "babylon-catalog-prod"),
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
