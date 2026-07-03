from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from rcars.api.middleware.auth import require_auth
from rcars.api.schemas import AuthMeResponse
from rcars.config import Settings

router = APIRouter()


@router.get(
    "/auth/me",
    summary="Get current user",
    description="Returns the authenticated user's email and granted roles (user, curator, admin).",
    response_model=AuthMeResponse,
)
async def auth_me(request: Request, user: str = Depends(require_auth)):
    settings: Settings = request.app.state.settings
    roles = ["user"]
    if settings.is_curator(user) or settings.is_admin(user):
        roles.append("curator")
    if settings.is_admin(user):
        roles.append("admin")
    return {"email": user, "roles": roles}
