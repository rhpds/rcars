import uuid
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import get_current_user
from rcars.db import Database
from rcars.config import Settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_sessions: dict[str, list[dict]] = {}


def _get_db_dependency() -> Database:
    """Import get_db at runtime to avoid circular import."""
    from rcars.web.app import get_db
    return get_db()


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
