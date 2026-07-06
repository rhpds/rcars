from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from rcars.api.middleware.auth import require_auth, require_admin, invalidate_api_key_cache
from rcars.api.schemas import (
    AuthMeResponse,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ApiKeyInfo,
    ApiKeyListResponse,
    RevokeApiKeyResponse,
)
from rcars.config import Settings

router = APIRouter()

_ROLE_LEVELS = {"user": 0, "curator": 1, "admin": 2}


def _user_max_role(settings: Settings, user: str) -> str:
    if settings.is_admin(user):
        return "admin"
    if settings.is_curator(user):
        return "curator"
    return "user"


def _generate_api_key() -> tuple[str, str, str]:
    raw = "rcars_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[:14]
    return raw, key_hash, key_prefix


@router.get(
    "/auth/me",
    summary="Get current user",
    description="Returns the authenticated user's email and granted roles.",
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


@router.post(
    "/auth/keys",
    summary="Create API key",
    description="Create a long-lived API key for programmatic access. Admin only.",
    response_model=CreateApiKeyResponse,
)
async def create_api_key(
    body: CreateApiKeyRequest, request: Request, user: str = Depends(require_admin)
):
    settings: Settings = request.app.state.settings
    creator_max = _user_max_role(settings, user)
    if _ROLE_LEVELS.get(body.role, 0) > _ROLE_LEVELS[creator_max]:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot create key with role '{body.role}' — your max role is '{creator_max}'",
        )

    raw_key, key_hash, key_prefix = _generate_api_key()
    expires_at = None
    if body.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    db = request.app.state.db
    key_id = db.create_api_key(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=body.name,
        created_by=user,
        role=body.role,
        expires_at=expires_at,
    )

    return CreateApiKeyResponse(
        api_key=raw_key,
        id=key_id,
        name=body.name,
        role=body.role,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get(
    "/auth/keys",
    summary="List API keys",
    description="List all API keys with metadata. Never returns raw keys or hashes. Admin only.",
    response_model=ApiKeyListResponse,
)
async def list_api_keys(
    request: Request,
    user: str = Depends(require_admin),
    active: bool = Query(True, description="Filter to active (non-revoked, non-expired) keys"),
):
    db = request.app.state.db
    rows = db.list_api_keys(active_only=active)
    keys = []
    now = datetime.now(timezone.utc)
    for r in rows:
        is_active = r["revoked_at"] is None and (
            r["expires_at"] is None or r["expires_at"] > now
        )
        keys.append(ApiKeyInfo(
            id=r["id"],
            key_prefix=r["key_prefix"],
            name=r["name"],
            created_by=r["created_by"],
            role=r["role"],
            created_at=r["created_at"].isoformat() if r["created_at"] else "",
            expires_at=r["expires_at"].isoformat() if r["expires_at"] else None,
            last_used_at=r["last_used_at"].isoformat() if r["last_used_at"] else None,
            is_active=is_active,
        ))
    return ApiKeyListResponse(keys=keys)


@router.delete(
    "/auth/keys/{key_id}",
    summary="Revoke API key",
    description="Soft-revoke an API key. Row preserved for audit trail. Admin only.",
    response_model=RevokeApiKeyResponse,
)
async def revoke_api_key(
    key_id: int, request: Request, user: str = Depends(require_admin)
):
    db = request.app.state.db
    result = db.revoke_api_key(key_id)
    if not result:
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    return RevokeApiKeyResponse(
        id=result["id"],
        revoked_at=result["revoked_at"].isoformat(),
    )
