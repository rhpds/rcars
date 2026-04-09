from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from rcars.web.deps import require_curator
from rcars.db import Database

router = APIRouter()


def get_db() -> Database:
    """Import get_db at runtime to avoid circular import."""
    from rcars.web.app import get_db as _get_db
    return _get_db()


@router.get("/curate", response_class=HTMLResponse)
async def curate(request: Request, user: str = Depends(require_curator), db: Database = Depends(get_db)):
    return HTMLResponse("<html><body>Curate (placeholder)</body></html>")
