import logging
import re
import threading
import uuid
from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from pathlib import Path

from rcars.web.deps import get_current_user
from rcars.db import Database
from rcars.config import Settings
from rcars.recommender import recommend

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
log = logging.getLogger(__name__)


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

# Session and query state — module-level, in-process only.
# CPython's GIL makes individual dict/list operations safe under concurrent requests,
# but these dicts are NOT safe for multi-replica deployments. If OpenShift is ever
# scaled beyond one replica, replace with a shared store (Redis or DB-backed job table).
_sessions: dict[str, list[dict]] = {}
_query_status: dict[str, dict] = {}
# shape: session_id → {"running": bool, "rec_html": str|None, "chat_html": str|None, "error": str|None}


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


def _run_advisor_query(
    session_id: str,
    message: str,
    description: str,
    first_message: str,
    db,
    client,
    settings,
    user: str,
) -> None:
    """Background thread: call recommend(), render fragments, store in _query_status."""
    turn_index = len(_sessions.get(session_id, []))
    try:
        log.info("advisor bg: generating embedding and searching candidates session=%s", session_id)
        result = recommend(
            query=description,
            db=db,
            anthropic_client=client,
            model=settings.model,
            limit=10,
            prod_only=True,
        )
        recs_count = len((result or {}).get("recommendations", []))
        log.info("advisor bg: recommend() returned %d recommendations session=%s", recs_count, session_id)
    except Exception:
        log.exception("advisor bg: recommend() failed session=%s", session_id)
        result = None

    raw_recs = result.get("recommendations", []) if result else []
    recs = _enrich_recs(raw_recs, db)

    overall = (result or {}).get("overall_assessment", f"Found {len(recs)} matches.")
    turns = _sessions.setdefault(session_id, [])
    turns.append({
        "role": "assistant",
        "content": overall,
        "rec_ci_names": [r["ci_name"] for r in recs],
        "recs": recs,
        "turn_index": turn_index,
    })

    is_curator = settings.is_curator(user)

    try:
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
        _query_status[session_id] = {
            "running": False,
            "rec_html": rec_html,
            "chat_html": chat_html,
            "error": None,
        }
    except Exception:
        log.exception("advisor bg: fragment rendering failed session=%s", session_id)
        _query_status[session_id] = {
            "running": False,
            "rec_html": None,
            "chat_html": None,
            "error": "An internal error occurred rendering results.",
        }


def _query_spinner_fragment(session_id: str) -> str:
    """HTMX polling spinner that replaces #rec-pane while query runs."""
    return (
        f'<div id="rec-pane" class="rec-pane"'
        f' hx-get="/advisor/query/status?session_id={escape(session_id)}"'
        f' hx-trigger="every 2s"'
        f' hx-swap="outerHTML">'
        f'<div class="pane-label">Recommendations</div>'
        f'<div class="rec-pane-loading">'
        f'<span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span>'
        f' Analyzing your request'
        f' <span style="color:#555;">(this may take a minute)</span>'
        f'</div>'
        f'</div>'
    )


def _query_done_fragment(rec_html: str, chat_html: str) -> str:
    """Done response: rec pane content + OOB chat turn. Sentinel lets JS detect completion."""
    return (
        f'<div id="rec-pane" class="rec-pane">'
        f'{rec_html}'
        f'<span id="advisor-result-ready" hidden></span>'
        f'</div>'
        f'\n{chat_html}'
    )


def _query_error_fragment(error_msg: str, message: str, session_id: str, first_message: str, turns: list) -> str:
    """Immediate error response (no thread). Same shape as done fragment."""
    turn_index = len(turns)
    turns.append({"role": "assistant", "content": error_msg, "rec_ci_names": [], "turn_index": turn_index})
    rec_html = (
        '<div class="pane-label">Recommendations</div>'
        f'<p style="color:var(--score-red);font-size:14px;">{escape(error_msg)}</p>'
    )
    chat_html = templates.get_template("fragments/chat_turn.html").render(
        user_message=message,
        assistant_message=error_msg,
        session_id=session_id,
        turn_index=turn_index,
        first_message=first_message,
    )
    return _query_done_fragment(rec_html, chat_html)


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
    ctx["session_expired"] = bool(session_id and not turns)

    # Restore last recommendations if session has them
    last_recs_html = ""
    if turns:
        for t in reversed(turns):
            if t.get("role") == "assistant" and (t.get("recs") or t.get("rec_ci_names")):
                recs = t.get("recs", [])
                if not recs and db:
                    ci_names = t.get("rec_ci_names", [])
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
                if recs:
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

    if not db:
        return HTMLResponse(_query_error_fragment(
            "Database not configured. Set RCARS_DATABASE_URL.",
            message, session_id, first_message, turns,
        ))

    client = settings.get_anthropic_client()
    if not client:
        return HTMLResponse(_query_error_fragment(
            "No Anthropic credentials configured. Set ANTHROPIC_VERTEX_PROJECT_ID or ANTHROPIC_API_KEY.",
            message, session_id, first_message, turns,
        ))

    description = " ".join(t["content"] for t in turns if t["role"] == "user")
    log.info("advisor: spawning background query user=%s session=%s query=%r", user, session_id, description[:120])

    _query_status[session_id] = {"running": True, "rec_html": None, "chat_html": None, "error": None}
    # daemon=True: thread is killed on process exit. If shutdown occurs mid-query the
    # exception handler in _run_advisor_query will catch any OperationalError from the
    # closing DB connection and produce a graceful "Found 0 matches." result.
    t = threading.Thread(
        target=_run_advisor_query,
        args=(session_id, message, description, first_message, db, client, settings, user),
        daemon=True,
    )
    t.start()

    return HTMLResponse(_query_spinner_fragment(session_id))


@router.get("/advisor/query/status", response_class=HTMLResponse)
async def advisor_query_status(
    session_id: str,
    user: str = Depends(get_current_user),
):
    status = _query_status.get(session_id)
    if status is None or status["running"]:
        return HTMLResponse(_query_spinner_fragment(session_id))

    # Done — pop and return result
    _query_status.pop(session_id, None)

    if status.get("error"):
        rec_html = (
            '<div class="pane-label">Recommendations</div>'
            f'<p style="color:var(--score-red);font-size:14px;">{escape(status["error"])}</p>'
        )
        return HTMLResponse(_query_done_fragment(rec_html, ""))

    return HTMLResponse(_query_done_fragment(status["rec_html"], status["chat_html"]))


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
        # Use stored full recs if available, fall back to catalog lookup
        recs = assistant_turn.get("recs", [])
        if not recs and db:
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
