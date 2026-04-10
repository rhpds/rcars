import subprocess
import threading
from fastapi import APIRouter, Request, Depends, Query
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
_item_analyze_status: dict = {}


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


def _run_rescan(settings):
    global _rescan_status
    _rescan_status["running"] = True
    _rescan_status["lines"] = ["Rescan started..."]
    _rescan_status["exit_ok"] = None
    try:
        result = subprocess.run(
            ["rcars", "scan"],
            capture_output=True,
            text=True,
            timeout=3600,
        )
        output = result.stdout[-2000:] if result.stdout else result.stderr[-2000:]
        _rescan_status["lines"] = output.splitlines()
        _rescan_status["exit_ok"] = result.returncode == 0
    except Exception as e:
        _rescan_status["lines"] = [f"Error: {e}"]
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
        "rescan_running": _rescan_status["running"],
        "rescan_output": "\n".join(_rescan_status["lines"]),
        "curator_emails": settings.curator_emails,
    }
    return templates.TemplateResponse(request=request, name="admin.html", context=ctx)


@router.post("/admin/rescan", response_class=HTMLResponse)
async def trigger_rescan(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if not _rescan_status["running"]:
        settings = Settings()
        t = threading.Thread(target=_run_rescan, args=(settings,), daemon=True)
        t.start()
    return HTMLResponse(
        '<div style="color:var(--score-green);font-size:12px;">Rescan started in background. Refresh this page to check status.</div>'
    )


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
