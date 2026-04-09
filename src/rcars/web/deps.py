# src/rcars/web/deps.py
from fastapi import Request, HTTPException, Depends
from rcars.config import Settings


def get_current_user(request: Request) -> str:
    """Return user identity. In Plan 3a: RCARS_DEV_USER or X-Forwarded-User header."""
    settings = Settings()
    if settings.dev_user:
        return settings.dev_user
    return request.headers.get("X-Forwarded-User", "")


def require_curator(user: str = Depends(get_current_user)) -> str:
    """Raise 403 if user is not a curator."""
    settings = Settings()
    if not settings.is_curator(user):
        raise HTTPException(status_code=403, detail="Curator access required")
    return user
