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
from rcars.recommender import run_query, Candidate

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
# shape: session_id → {
#   "phase": str,           # "searching" | "vector_done" | "triaging" | "triage_done" | "rationale" | "complete" | "no_matches" | "error"
#   "running": bool,
#   "rec_html": str|None,
#   "chat_html": str|None,
#   "error": str|None,
#   "candidates": list[dict],  # serialized candidates for session storage
# }


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
        db_status = {
            "last_refresh": "no database", "is_stale": True,
            "catalog_stale": True, "catalog_date": "never",
            "analysis_stale": True, "analysis_date": "never",
        }
    return {
        "request": request,
        "current_user": user,
        "is_curator": settings.is_curator(user),
        "is_admin": settings.is_admin(user),
        "active_page": active_page,
        "db_status": db_status,
    }


_TIER_ORDER = {"green": 0, "yellow": 1, "white": 2}


def _tier_sort_key(rec: dict) -> tuple:
    tier = rec.get("tier", "white")
    order = _TIER_ORDER.get(tier, 2)
    if tier == "green":
        score = -(rec.get("fit_score") or 0)
    elif tier == "yellow":
        score = -(rec.get("relevance_score") or rec.get("fit_score") or 0)
    else:
        score = -(rec.get("vector_similarity_pct") or 0)
    return (order, score)


def _candidates_to_recs(candidates: list, card_phase: str) -> list[dict]:
    """Convert Candidate dataclasses to rec dicts for templates, sorted by tier."""
    recs = []
    for c in candidates:
        tier = getattr(c, "tier", "white")
        rec = {
            "ci_name": c.ci_name,
            "display_name": c.display_name,
            "tier": tier,
            "fit_score": c.relevance_score if c.relevance_score is not None else c.vector_similarity_pct,
            "relevance_score": c.relevance_score,
            "vector_similarity_pct": c.vector_similarity_pct,
            "rationale": c.rationale or "",
            "why_it_fits": c.why_it_fits or "",
            "how_to_use": c.how_to_use or "",
            "suggested_format": c.suggested_format or "",
            "duration_notes": c.duration_notes or "",
            "caveats": c.caveats or "",
            "one_line_reason": c.one_line_reason or "",
            "card_phase": "complete" if c.rationale else (
                "triaged" if tier == "yellow" else card_phase
            ),
            "summary": c.summary,
            "topics": c.topics,
            "difficulty": c.difficulty,
            "duration_min": c.duration_min,
            "content_type": c.content_type,
            "stage": c.stage,
        }
        recs.append(rec)
    recs.sort(key=_tier_sort_key)
    return recs


def _run_advisor_query(
    session_id: str,
    message: str,
    description: str,
    first_message: str,
    db,
    client,
    settings,
    user: str,
    prod_only: bool = True,
    opted_out: bool = False,
) -> None:
    """Background thread: run three-phase pipeline, update _query_status at each phase."""
    turn_index = len(_sessions.get(session_id, []))
    is_curator = settings.is_curator(user)

    try:
        # Detect URLs in the query and enhance with event context
        event_url_stored: str | None = None
        urls = re.findall(r'https?://[^\s<>"]+', description)
        if urls:
            event_url_stored = urls[0]
            from rcars.event_parser import parse_event_url
            for url in urls[:1]:  # Only parse the first URL
                log.info("advisor: detected URL %s, fetching event profile", url)
                event_profile = parse_event_url(url, client, settings.model)
                if event_profile:
                    themes = event_profile.get("themes", [])
                    queries = event_profile.get("search_queries", [])
                    event_name = event_profile.get("event_name", "")
                    log.info("advisor: event=%s themes=%s", event_name, themes)
                    description = f"{description}. Event: {event_name}. Themes: {', '.join(themes)}. {' '.join(queries)}"
                else:
                    log.warning("advisor: failed to parse event URL %s", url)

        for state in run_query(
            query=description,
            db=db,
            anthropic_client=client,
            settings=settings,
            prod_only=prod_only,
        ):
            if state.phase == "VECTOR_DONE":
                recs = _candidates_to_recs(state.candidates, "vector")
                recs = _enrich_recs(recs, db)
                rec_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs, is_curator=is_curator, session_id=session_id,
                    turn_index=turn_index,
                    phase="triaging", status_message="Evaluating relevance...",
                )
                _query_status[session_id] = {
                    "phase": "vector_done", "running": True,
                    "rec_html": rec_html, "chat_html": None, "error": None,
                    "candidates": recs,
                }

            elif state.phase == "TRIAGE_DONE":
                recs = _candidates_to_recs(state.candidates, "triaged")
                recs = _enrich_recs(recs, db)
                # Mark top N yellow candidates as "analyzing" (going to Sonnet)
                yellow_count = 0
                for rec in recs:
                    if rec.get("tier") == "yellow" and yellow_count < settings.rationale_top_n:
                        rec["card_phase"] = "analyzing"
                        yellow_count += 1
                rec_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs, is_curator=is_curator, session_id=session_id,
                    turn_index=turn_index,
                    phase="rationale", status_message="Preparing detailed analysis...",
                )
                _query_status[session_id] = {
                    "phase": "triage_done", "running": True,
                    "rec_html": rec_html, "chat_html": None, "error": None,
                    "candidates": recs,
                }

            elif state.phase == "COMPLETE":
                recs = _candidates_to_recs(state.candidates, "complete")
                recs = _enrich_recs(recs, db)
                overall = state.overall_assessment or f"Found {len(recs)} matches."

                # Ensure content gaps are surfaced even if Sonnet
                # omitted them from the overall_assessment text
                if state.content_gaps and "Content Gaps" not in (overall or ""):
                    gaps_text = "\n".join(f"- {g}" for g in state.content_gaps)
                    overall += f"\n\n**Content Gaps:**\n{gaps_text}"

                turns = _sessions.setdefault(session_id, [])
                turns.append({
                    "role": "assistant", "content": overall,
                    "rec_ci_names": [r["ci_name"] for r in recs],
                    "recs": recs, "turn_index": turn_index,
                })

                # Persist session turn to DB
                if db:
                    results_for_storage = [
                        {
                            "ci_name": r["ci_name"],
                            "tier": r.get("tier", "white"),
                            "fit_score": r.get("fit_score"),
                            "relevance_score": r.get("relevance_score"),
                            "vector_similarity_pct": r.get("vector_similarity_pct"),
                            "stage": r.get("stage", "prod"),
                        }
                        for r in recs
                    ]
                    db.log_advisor_session(
                        session_id=session_id,
                        turn_index=turn_index,
                        user_email=user,
                        query_text=message,
                        event_url=event_url_stored,
                        results=results_for_storage,
                        overall_assessment=overall,
                        opted_out=opted_out,
                    )

                rec_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs, is_curator=is_curator, session_id=session_id,
                    turn_index=turn_index,
                    phase="complete", status_message=None,
                )
                chat_html = templates.get_template("fragments/chat_turn.html").render(
                    user_message=message, assistant_message=overall,
                    session_id=session_id, turn_index=turn_index,
                    first_message=first_message,
                )
                _query_status[session_id] = {
                    "phase": "complete", "running": False,
                    "rec_html": rec_html, "chat_html": chat_html, "error": None,
                    "candidates": recs,
                }

            elif state.phase == "NO_MATCHES":
                no_match_msg = "Nothing in the catalog is a strong fit for this query. Try broadening your terms or describing what you need differently."
                if db:
                    db.log_advisor_session(
                        session_id=session_id,
                        turn_index=turn_index,
                        user_email=user,
                        query_text=message,
                        event_url=event_url_stored,
                        results=[],
                        overall_assessment=no_match_msg,
                        opted_out=opted_out,
                    )
                turns = _sessions.setdefault(session_id, [])
                turns.append({
                    "role": "assistant", "content": no_match_msg,
                    "rec_ci_names": [], "recs": [], "turn_index": turn_index,
                })
                rec_html = (
                    '<div class="pane-label">Recommendations</div>'
                    f'<p style="color:var(--text-muted);font-size:14px;">{no_match_msg}</p>'
                )
                chat_html = templates.get_template("fragments/chat_turn.html").render(
                    user_message=message, assistant_message=no_match_msg,
                    session_id=session_id, turn_index=turn_index,
                    first_message=first_message,
                )
                _query_status[session_id] = {
                    "phase": "no_matches", "running": False,
                    "rec_html": rec_html, "chat_html": chat_html, "error": None,
                    "candidates": [],
                }

    except Exception:
        log.exception("advisor bg: pipeline failed session=%s", session_id)
        _query_status[session_id] = {
            "phase": "error", "running": False,
            "rec_html": None, "chat_html": None,
            "error": "An internal error occurred. Please try again.",
            "candidates": [],
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
        f' Searching the catalog'
        f' <span style="color:#555;">(results appear as they\'re ready)</span>'
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

    # Read form toggles
    form = await request.form()
    include_non_prod = form.get("include_non_prod") == "true"
    opted_out = form.get("opted_out") == "true"
    prod_only = not include_non_prod

    log.info("advisor: spawning background query user=%s session=%s prod_only=%s opted_out=%s query=%r",
             user, session_id, prod_only, opted_out, description[:120])

    _query_status[session_id] = {"running": True, "rec_html": None, "chat_html": None, "error": None}
    t = threading.Thread(
        target=_run_advisor_query,
        args=(session_id, message, description, first_message, db, client, settings, user, prod_only, opted_out),
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

    if status is None:
        return HTMLResponse(_query_spinner_fragment(session_id))

    # Still running — return latest rec_html with polling trigger
    if status["running"]:
        if status.get("rec_html"):
            # We have intermediate results (vector or triage phase) — show them with continued polling
            html = (
                f'<div id="rec-pane" class="rec-pane"'
                f' hx-get="/advisor/query/status?session_id={escape(session_id)}"'
                f' hx-trigger="every 2s"'
                f' hx-swap="outerHTML">'
                f'{status["rec_html"]}'
                f'</div>'
            )
            return HTMLResponse(html)
        return HTMLResponse(_query_spinner_fragment(session_id))

    # Done — pop and return final result
    _query_status.pop(session_id, None)

    if status.get("error"):
        rec_html = (
            '<div class="pane-label">Recommendations</div>'
            f'<p style="color:var(--score-red);font-size:14px;">{escape(status["error"])}</p>'
        )
        return HTMLResponse(_query_done_fragment(rec_html, ""))

    return HTMLResponse(_query_done_fragment(status["rec_html"], status.get("chat_html", "")))


@router.post("/advisor/select", response_class=HTMLResponse)
async def advisor_select(
    session_id: Annotated[str, Form()],
    turn_index: Annotated[str, Form()],
    ci_name: Annotated[str, Form()],
    user: str = Depends(get_current_user),
    db: Database | None = Depends(_get_db_dependency),
):
    if db:
        db.update_advisor_session_choice(session_id, int(turn_index), ci_name)
    return HTMLResponse(
        '<button style="background:var(--score-green);color:#000;border:none;'
        'padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600;cursor:default;">'
        '✓ Best fit selected</button>'
    )


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
