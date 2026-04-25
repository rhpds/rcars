from __future__ import annotations

from fastapi import Request, HTTPException
from rcars.config import Settings


def get_current_user(request: Request) -> str:
    settings: Settings = request.app.state.settings
    if settings.dev_user:
        return settings.dev_user
    email = request.headers.get("X-Forwarded-Email", "")
    if not email:
        email = request.headers.get("X-Forwarded-User", "")
    return email


def require_auth(request: Request) -> str:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_curator(request: Request) -> str:
    user = require_auth(request)
    settings: Settings = request.app.state.settings
    if not settings.is_curator(user) and not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Curator role required")
    return user


def require_admin(request: Request) -> str:
    user = require_auth(request)
    settings: Settings = request.app.state.settings
    if not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
