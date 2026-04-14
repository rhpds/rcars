import logging
import subprocess
import threading
import html as _html
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from markupsafe import Markup

from rcars.web.deps import require_admin
from rcars.db import Database
from rcars.config import Settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
log = logging.getLogger(__name__)

_rescan_status: dict = {"running": False, "lines": [], "exit_ok": None}
_refresh_status: dict = {"running": False, "result": None, "color": None}
_stale_check_status: dict = {"running": False, "lines": [], "exit_ok": None}


def _fmt_tokens(n: int) -> str:
    """Format token count with K/M suffix for summary display."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _token_usage_html(stats: list, queries: list, days: int) -> str:
    """Render the token usage section as an HTML fragment."""
    # Window selector
    select_html = (
        '<select hx-get="/admin/token-usage" hx-target="#token-usage-section" '
        'hx-swap="outerHTML" hx-trigger="change" name="days" '
        'style="background:var(--bg-secondary);color:var(--text-primary);'
        'border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:12px;">'
    )
    for val, label in [(7, "Last 7 days"), (30, "Last 30 days"), (90, "Last 90 days"), (0, "All time")]:
        selected = " selected" if val == days else ""
        select_html += f'<option value="{val}"{selected}>{label}</option>'
    select_html += "</select>"

    # Summary table
    if stats:
        rows = "".join(
            f'<tr><td>{_html.escape(row["model"])}</td><td>{_html.escape(row["operation"])}</td>'
            f'<td>{row["calls"]}</td>'
            f'<td>{_fmt_tokens(row["input_tokens"])}</td>'
            f'<td>{_fmt_tokens(row["output_tokens"])}</td>'
            f'<td>{_fmt_tokens(row["total_tokens"])}</td></tr>'
            for row in stats
        )
        summary_html = (
            '<table class="status-table" style="margin-top:8px;">'
            "<tr><th>Model</th><th>Operation</th><th>Calls</th>"
            "<th>Input</th><th>Output</th><th>Total</th></tr>"
            f"{rows}</table>"
        )
    else:
        summary_html = (
            '<p style="font-size:12px;color:var(--text-muted);">'
            "No token usage data for this period.</p>"
        )

    # Per-query table
    if queries:
        query_rows = ""
        for row in queries:
            q_full = row.get("query_text") or ""
            q_display = q_full[:60] + ("…" if len(q_full) > 60 else "")
            qt = row["query_time"].strftime("%Y-%m-%d %H:%M") if row.get("query_time") else ""
            total = row.get("total_tokens", 0)
            query_rows += (
                f'<tr>'
                f'<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;'
                f'white-space:nowrap;" title="{_html.escape(q_full)}">'
                f"{_html.escape(q_display)}</td>"
                f'<td>{row.get("triage_input", 0):,}</td>'
                f'<td>{row.get("triage_output", 0):,}</td>'
                f'<td>{row.get("rationale_input", 0):,}</td>'
                f'<td>{row.get("rationale_output", 0):,}</td>'
                f'<td>{total:,}</td>'
                f'<td style="font-size:10px;color:var(--text-muted);">{_html.escape(qt)}</td>'
                f"</tr>"
            )
        query_html = (
            '<div style="font-size:12px;font-weight:600;margin:12px 0 6px;">'
            "Recent Queries</div>"
            '<table class="status-table" style="font-size:11px;">'
            "<tr><th>Query</th><th>Haiku In</th><th>Haiku Out</th>"
            "<th>Sonnet In</th><th>Sonnet Out</th><th>Total</th><th>Time</th></tr>"
            f"{query_rows}</table>"
        )
    else:
        query_html = ""

    return (
        f'<div id="token-usage-section">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f'<span style="font-size:12px;color:var(--text-muted);">Window:</span>'
        f"{select_html}"
        f"</div>"
        f"{summary_html}"
        f"{query_html}"
        f"</div>"
    )


def _get_db_dependency() -> Database | None:
    from rcars.web.app import get_db
    return get_db()


def _status_table_oob(db: Database) -> str:
    """Render the catalog status table as an HTMX OOB swap fragment."""
    s = db.get_status_summary()
    stale_color = "var(--score-amber)" if s["stale"] > 0 else "var(--score-green)"
    return f"""<table id="catalog-status-table" class="status-table" hx-swap-oob="true">
  <tr><th>Metric</th><th>Count</th></tr>
  <tr><td>Total catalog items</td><td>{s["total"]}</td></tr>
  <tr><td>Production items</td><td>{s["prod"]}</td></tr>
  <tr><td>With Showroom (scannable)</td><td>{s["with_showroom"]}</td></tr>
  <tr><td>Analyzed</td><td>{s["analyzed"]}</td></tr>
  <tr><td>Stale (needs rescan)</td><td style="color:{stale_color};">{s["stale"]}</td></tr>
</table>"""


def _refresh_section_running() -> str:
    return """<div id="refresh-section"
     hx-get="/admin/refresh/status"
     hx-trigger="every 3s"
     hx-target="this"
     hx-swap="outerHTML">
  <button class="btn-action" disabled style="opacity:0.5;cursor:not-allowed;">Sync Catalog</button>
  <span style="font-size:12px;color:var(--score-amber);margin-left:10px;">&#8635; Syncing catalog\u2026</span>
</div>"""


def _refresh_section_idle(msg: str = "", color: str = "") -> str:
    status_span = f'<span style="font-size:12px;color:{color};margin-left:10px;">{msg}</span>' if msg else ""
    return f"""<div id="refresh-section">
  <button class="btn-action"
          hx-post="/admin/refresh"
          hx-target="#refresh-section"
          hx-swap="outerHTML">Sync Catalog</button>
  {status_span}
</div>"""


def _run_refresh():
    global _refresh_status
    try:
        result = subprocess.run(
            ["rcars", "refresh"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            _refresh_status["result"] = "Catalog sync complete."
            _refresh_status["color"] = "var(--score-green)"
        else:
            _refresh_status["result"] = f"Sync failed: {result.stderr[:200]}"
            _refresh_status["color"] = "var(--score-red)"
    except Exception as e:
        _refresh_status["result"] = f"Sync error: {str(e)[:200]}"
        _refresh_status["color"] = "var(--score-red)"
    finally:
        _refresh_status["running"] = False


def _log_block_html(lines: list[str], div_id: str = "") -> str:
    """Render a scrollable log block that auto-scrolls to the bottom."""
    if not lines:
        return ""
    recent = lines[-100:]
    log_content = "\n".join(f'<div>{_html.escape(line)}</div>' for line in recent)
    id_attr = f' id="{div_id}"' if div_id else ""
    return (
        f'<div{id_attr} style="margin-top:10px;background:var(--bg-secondary);'
        f'border:1px solid var(--border);border-radius:4px;padding:8px 10px;'
        f'font-size:11px;font-family:monospace;color:var(--text-muted);'
        f'white-space:pre-wrap;max-height:350px;overflow-y:auto;">'
        f'{log_content}</div>'
        f'<script>(() => {{ let el = document.getElementById("{div_id}"); '
        f'if (el) el.scrollTop = el.scrollHeight; }})()</script>'
    )


def _rescan_section_running(lines: list[str]) -> str:
    return (
        f'<div id="rescan-section"'
        f' hx-get="/admin/rescan/status"'
        f' hx-trigger="every 3s"'
        f' hx-target="this"'
        f' hx-swap="outerHTML">'
        f'<button class="btn-action" disabled style="opacity:0.5;cursor:not-allowed;">Analyze Showroom Content</button>'
        f'<span style="font-size:12px;color:var(--score-amber);margin-left:10px;">&#8635; Analysis running\u2026</span>'
        f'{_log_block_html(lines, "rescan-log")}'
        f'</div>'
    )


def _rescan_section_idle(msg: str = "", color: str = "", lines: list[str] | None = None) -> str:
    status_span = f'<span style="font-size:12px;color:{color};margin-left:10px;">{_html.escape(msg)}</span>' if msg else ""
    return (
        f'<div id="rescan-section">'
        f'<button class="btn-action"'
        f' hx-post="/admin/rescan"'
        f' hx-target="#rescan-section"'
        f' hx-swap="outerHTML">Analyze Showroom Content</button>'
        f'{status_span}'
        f'{_log_block_html(lines or [], "rescan-log")}'
        f'</div>'
    )


def _stale_section_running(lines: list[str]) -> str:
    return (
        f'<div id="stale-section"'
        f' hx-get="/admin/check-stale/status"'
        f' hx-trigger="every 3s"'
        f' hx-target="this"'
        f' hx-swap="outerHTML">'
        f'<button class="btn-action" disabled style="opacity:0.5;cursor:not-allowed;">Check for Updates</button>'
        f'<span style="font-size:12px;color:var(--score-amber);margin-left:10px;">&#8635; Checking Showrooms\u2026</span>'
        f'{_log_block_html(lines, "stale-log")}'
        f'</div>'
    )


def _stale_section_idle(msg: str = "", color: str = "", lines: list[str] | None = None) -> str:
    status_span = f'<span style="font-size:12px;color:{color};margin-left:10px;">{_html.escape(msg)}</span>' if msg else ""
    return (
        f'<div id="stale-section">'
        f'<button class="btn-action"'
        f' hx-post="/admin/check-stale"'
        f' hx-target="#stale-section"'
        f' hx-swap="outerHTML">Check for Updates</button>'
        f'{status_span}'
        f'{_log_block_html(lines or [], "stale-log")}'
        f'</div>'
    )


def _run_subprocess(cmd: list[str], status_dict: dict, label: str):
    """Run a CLI command in background, streaming output to status_dict and pod log."""
    status_dict["lines"] = [f"Starting {label}\u2026"]
    status_dict["exit_ok"] = None
    log.info("admin: starting %s subprocess: %s", label, " ".join(cmd))
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            line = line.rstrip("\n")
            if line:
                log.info("[%s] %s", label, line)
                status_dict["lines"].append(line)
                if len(status_dict["lines"]) > 500:
                    status_dict["lines"] = status_dict["lines"][-500:]
        proc.wait(timeout=3600)
        status_dict["exit_ok"] = proc.returncode == 0
        if proc.returncode == 0:
            log.info("admin: %s completed successfully", label)
        else:
            log.error("admin: %s exited with code %d", label, proc.returncode)
    except Exception as e:
        log.exception("admin: %s failed", label)
        status_dict["lines"].append(f"Error: {e}")
        status_dict["exit_ok"] = False
    finally:
        status_dict["running"] = False


def _run_rescan():
    _run_subprocess(["rcars", "scan"], _rescan_status, "scan")


def _run_stale_check():
    _run_subprocess(["rcars", "check-stale"], _stale_check_status, "check-stale")


@router.get("/admin", response_class=HTMLResponse)
async def admin(
    request: Request,
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    settings = Settings()
    status = db.get_status_summary()
    currency = db.get_db_currency(stale_days=settings.stale_days)
    # Render current state of background operations so navigating
    # back to the admin page shows running jobs, not idle buttons.
    if _refresh_status["running"]:
        refresh_html = _refresh_section_running()
    elif _refresh_status.get("result"):
        refresh_html = _refresh_section_idle(_refresh_status["result"], _refresh_status.get("color", ""))
    else:
        refresh_html = _refresh_section_idle()

    if _rescan_status["running"]:
        rescan_html = _rescan_section_running(_rescan_status["lines"])
    elif _rescan_status.get("exit_ok") is not None:
        msg = "Analysis complete." if _rescan_status["exit_ok"] else "Analysis failed — check logs above."
        color = "var(--score-green)" if _rescan_status["exit_ok"] else "var(--score-red)"
        rescan_html = _rescan_section_idle(msg, color, _rescan_status["lines"])
    else:
        rescan_html = _rescan_section_idle()

    if _stale_check_status["running"]:
        stale_html = _stale_section_running(_stale_check_status["lines"])
    elif _stale_check_status.get("exit_ok") is not None:
        msg = "Check complete." if _stale_check_status["exit_ok"] else "Check failed — see logs above."
        color = "var(--score-green)" if _stale_check_status["exit_ok"] else "var(--score-red)"
        stale_html = _stale_section_idle(msg, color, _stale_check_status["lines"])
    else:
        stale_html = _stale_section_idle()

    ctx = {
        "request": request,
        "current_user": user,
        "is_curator": settings.is_curator(user),
        "is_admin": True,
        "active_page": "admin",
        "db_status": currency,
        "status": status,
        "curator_emails": settings.curator_emails,
        "refresh_html": Markup(refresh_html),
        "rescan_html": Markup(rescan_html),
        "stale_html": Markup(stale_html),
    }
    return templates.TemplateResponse(request=request, name="admin.html", context=ctx)


@router.post("/admin/check-stale", response_class=HTMLResponse)
async def trigger_stale_check(
    user: str = Depends(require_admin),
):
    if _stale_check_status["running"]:
        return HTMLResponse(_stale_section_running(_stale_check_status["lines"]))
    _stale_check_status["running"] = True
    _stale_check_status["lines"] = []
    _stale_check_status["exit_ok"] = None
    t = threading.Thread(target=_run_stale_check, daemon=True)
    t.start()
    return HTMLResponse(_stale_section_running([]))


@router.get("/admin/check-stale/status", response_class=HTMLResponse)
async def stale_check_status(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if _stale_check_status["running"]:
        return HTMLResponse(_stale_section_running(_stale_check_status["lines"]))
    if _stale_check_status["exit_ok"] is not None:
        exit_ok = _stale_check_status["exit_ok"]
        lines = list(_stale_check_status["lines"])
        msg = "Check complete." if exit_ok else "Check failed — see logs above."
        color = "var(--score-green)" if exit_ok else "var(--score-red)"
        return HTMLResponse(_stale_section_idle(msg, color, lines) + _status_table_oob(db))
    return HTMLResponse(_stale_section_idle())


@router.post("/admin/rescan", response_class=HTMLResponse)
async def trigger_rescan(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if _rescan_status["running"]:
        return HTMLResponse(_rescan_section_running(_rescan_status["lines"]))
    _rescan_status["running"] = True
    _rescan_status["lines"] = []
    _rescan_status["exit_ok"] = None
    t = threading.Thread(target=_run_rescan, daemon=True)
    t.start()
    return HTMLResponse(_rescan_section_running([]))


@router.get("/admin/rescan/status", response_class=HTMLResponse)
async def rescan_status(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if _rescan_status["running"]:
        return HTMLResponse(_rescan_section_running(_rescan_status["lines"]))
    if _rescan_status["exit_ok"] is not None:
        exit_ok = _rescan_status["exit_ok"]
        lines = list(_rescan_status["lines"])
        # Don't clear exit_ok here — keep the result visible until the next scan starts.
        msg = "Analysis complete." if exit_ok else "Analysis failed — check logs above."
        color = "var(--score-green)" if exit_ok else "var(--score-red)"
        return HTMLResponse(_rescan_section_idle(msg, color, lines) + _status_table_oob(db))
    return HTMLResponse(_rescan_section_idle())


@router.post("/admin/refresh", response_class=HTMLResponse)
async def trigger_refresh(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if _refresh_status["running"]:
        return HTMLResponse(_refresh_section_running())
    _refresh_status["running"] = True
    _refresh_status["result"] = None
    _refresh_status["color"] = None
    t = threading.Thread(target=_run_refresh, daemon=True)
    t.start()
    return HTMLResponse(_refresh_section_running())


@router.get("/admin/refresh/status", response_class=HTMLResponse)
async def refresh_status(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if _refresh_status["running"]:
        return HTMLResponse(_refresh_section_running())
    if _refresh_status["result"] is not None:
        msg = _refresh_status["result"]
        color = _refresh_status["color"]
        _refresh_status["result"] = None
        _refresh_status["color"] = None
        return HTMLResponse(_refresh_section_idle(msg, color) + _status_table_oob(db))
    return HTMLResponse(_refresh_section_idle())


@router.get("/admin/token-usage", response_class=HTMLResponse)
async def token_usage_fragment(
    days: int = 30,
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    days_arg = days if days > 0 else None
    stats = db.get_token_stats(days=days_arg)
    queries = db.get_recent_queries(days=days_arg)
    return HTMLResponse(_token_usage_html(stats, queries, days))
