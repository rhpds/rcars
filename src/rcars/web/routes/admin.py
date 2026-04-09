import subprocess
import threading
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import require_curator
from rcars.db import Database
from rcars.config import Settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_rescan_status: dict = {"running": False, "last_output": ""}


def _get_db_dependency() -> Database:
    from rcars.web.app import get_db
    return get_db()


def _run_rescan(settings):
    global _rescan_status
    _rescan_status["running"] = True
    _rescan_status["last_output"] = "Rescan started..."
    try:
        result = subprocess.run(
            ["rcars", "scan"],
            capture_output=True,
            text=True,
            timeout=3600,
        )
        _rescan_status["last_output"] = result.stdout[-2000:] if result.stdout else result.stderr[-2000:]
    except Exception as e:
        _rescan_status["last_output"] = f"Error: {e}"
    finally:
        _rescan_status["running"] = False


@router.get("/admin", response_class=HTMLResponse)
async def admin(
    request: Request,
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    settings = Settings()
    status = db.get_status_summary()
    currency = db.get_db_currency(stale_days=settings.stale_days)
    ctx = {
        "request": request,
        "current_user": user,
        "is_curator": True,
        "active_page": "admin",
        "db_status": currency,
        "status": status,
        "rescan_running": _rescan_status["running"],
        "rescan_output": _rescan_status["last_output"],
        "curator_emails": settings.curator_emails,
    }
    return templates.TemplateResponse(request=request, name="admin.html", context=ctx)


@router.post("/admin/rescan", response_class=HTMLResponse)
async def trigger_rescan(
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    if not _rescan_status["running"]:
        settings = Settings()
        t = threading.Thread(target=_run_rescan, args=(settings,), daemon=True)
        t.start()
    return HTMLResponse(
        '<div style="color:var(--score-green);font-size:12px;">Rescan started in background. Refresh this page to check status.</div>'
    )


def _run_refresh() -> tuple[str, str]:
    """Run rcars refresh in a thread-safe way."""
    result = subprocess.run(
        ["rcars", "refresh"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode == 0:
        return "Catalog refresh complete.", "var(--score-green)"
    return f"Refresh failed: {result.stderr[:200]}", "var(--score-red)"


@router.post("/admin/refresh", response_class=HTMLResponse)
async def trigger_refresh(
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    import asyncio
    loop = asyncio.get_event_loop()
    msg, color = await loop.run_in_executor(None, _run_refresh)
    return HTMLResponse(f'<div style="color:{color};font-size:12px;">{msg}</div>')
