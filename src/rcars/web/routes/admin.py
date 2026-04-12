import subprocess
import threading
import html as _html
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import require_admin
from rcars.db import Database
from rcars.config import Settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_rescan_status: dict = {"running": False, "lines": [], "exit_ok": None}
_refresh_status: dict = {"running": False, "result": None, "color": None}


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
  <tr><td>With Showroom content</td><td>{s["with_showroom"]}</td></tr>
  <tr><td>Analyzed</td><td>{s["analyzed"]}</td></tr>
  <tr><td>Stale (needs rescan)</td><td style="color:{stale_color};">{s["stale"]}</td></tr>
</table>"""


def _refresh_section_running() -> str:
    return """<div id="refresh-section"
     hx-get="/admin/refresh/status"
     hx-trigger="every 2s"
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


def _rescan_section_running(lines: list[str]) -> str:
    recent = lines[-20:] if lines else []
    log_html = "\n".join(f'<div>{_html.escape(line)}</div>' for line in recent) if recent else ""
    log_block = f"""<div style="margin-top:10px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:4px;padding:8px 10px;font-size:10px;font-family:monospace;color:var(--text-muted);white-space:pre-wrap;max-height:200px;overflow-y:auto;">{log_html}</div>""" if log_html else ""
    return f"""<div id="rescan-section"
     hx-get="/admin/rescan/status"
     hx-trigger="every 2s"
     hx-target="this"
     hx-swap="outerHTML">
  <button class="btn-action" disabled style="opacity:0.5;cursor:not-allowed;">Analyze Showroom Content</button>
  <span style="font-size:12px;color:var(--score-amber);margin-left:10px;">&#8635; Analysis running\u2026</span>
  {log_block}
</div>"""


def _rescan_section_idle(msg: str = "", color: str = "", lines: list[str] | None = None) -> str:
    status_span = f'<span style="font-size:12px;color:{color};margin-left:10px;">{msg}</span>' if msg else ""
    log_html = ""
    if lines:
        recent = lines[-20:]
        log_content = "\n".join(f'<div>{_html.escape(line)}</div>' for line in recent)
        log_html = f"""<div style="margin-top:10px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:4px;padding:8px 10px;font-size:10px;font-family:monospace;color:var(--text-muted);white-space:pre-wrap;max-height:200px;overflow-y:auto;">{log_content}</div>"""
    return f"""<div id="rescan-section">
  <button class="btn-action"
          hx-post="/admin/rescan"
          hx-target="#rescan-section"
          hx-swap="outerHTML">Analyze Showroom Content</button>
  {status_span}
  {log_html}
</div>"""


def _run_rescan():
    global _rescan_status
    _rescan_status["lines"] = ["Starting analysis\u2026"]
    _rescan_status["exit_ok"] = None
    try:
        proc = subprocess.Popen(
            ["rcars", "scan"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            line = line.rstrip("\n")
            if line:
                _rescan_status["lines"].append(line)
                if len(_rescan_status["lines"]) > 500:
                    _rescan_status["lines"] = _rescan_status["lines"][-500:]
        proc.wait(timeout=3600)
        _rescan_status["exit_ok"] = proc.returncode == 0
    except Exception as e:
        _rescan_status["lines"].append(f"Error: {e}")
        _rescan_status["exit_ok"] = False
    finally:
        _rescan_status["running"] = False


@router.get("/admin", response_class=HTMLResponse)
async def admin(
    request: Request,
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    settings = Settings()
    status = db.get_status_summary()
    currency = db.get_db_currency(stale_days=settings.stale_days)
    ctx = {
        "request": request,
        "current_user": user,
        "is_curator": settings.is_curator(user),
        "is_admin": True,
        "active_page": "admin",
        "db_status": currency,
        "status": status,
        "curator_emails": settings.curator_emails,
    }
    return templates.TemplateResponse(request=request, name="admin.html", context=ctx)


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
