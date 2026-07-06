from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import httpx
from fastapi import Request, HTTPException
from rcars.config import Settings

logger = logging.getLogger(__name__)

_K8S_TOKEN_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
_K8S_CA_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
_TOKEN_REVIEW_URL = (
    "https://kubernetes.default.svc/apis/authentication.k8s.io/v1/tokenreviews"
)

# In-memory cache: key_hash → (user_email, role, expires_at_ts, cached_at)
_api_key_cache: dict[str, tuple[str, str, float | None, float]] = {}
_CACHE_TTL = 60.0


def _parse_sa_allowlist(allowlist_str: str) -> set[str]:
    if not allowlist_str:
        return set()
    return {sa.strip() for sa in allowlist_str.split(",") if sa.strip()}


async def _validate_sa_token(token: str, allowlist: set[str]) -> str | None:
    try:
        pod_token = _K8S_TOKEN_PATH.read_text().strip()
        ca_path = str(_K8S_CA_PATH)

        async with httpx.AsyncClient(
            verify=ca_path, timeout=5.0
        ) as client:
            resp = await client.post(
                _TOKEN_REVIEW_URL,
                json={
                    "apiVersion": "authentication.k8s.io/v1",
                    "kind": "TokenReview",
                    "spec": {"token": token},
                },
                headers={
                    "Authorization": f"Bearer {pod_token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()

        data = resp.json()
        status = data.get("status", {})

        if not status.get("authenticated"):
            logger.debug("SA token not authenticated by TokenReview")
            return None

        username = status.get("user", {}).get("username", "")
        if username not in allowlist:
            logger.warning("SA identity %s not in allowlist", username)
            return None

        logger.info("SA token validated for identity: %s", username)
        return username

    except Exception:
        logger.warning("SA token validation failed", exc_info=True)
        return None


def _validate_api_key_cached(request: Request, raw_key: str) -> tuple[str, str] | None:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    now = time.monotonic()

    cached = _api_key_cache.get(key_hash)
    if cached:
        user, role, expires_ts, cached_at = cached
        if now - cached_at < _CACHE_TTL:
            if expires_ts and time.time() > expires_ts:
                _api_key_cache.pop(key_hash, None)
                return None
            return user, role
        _api_key_cache.pop(key_hash, None)

    db = request.app.state.db
    row = db.get_api_key_by_hash(key_hash)
    if not row:
        return None

    expires_ts = row["expires_at"].timestamp() if row.get("expires_at") else None
    _api_key_cache[key_hash] = (row["created_by"], row["role"], expires_ts, now)
    db.touch_api_key(row["id"])
    logger.info(
        "API key authenticated",
        extra={"auth_method": "api_key", "user": row["created_by"], "key_id": row["id"]},
    )
    return row["created_by"], row["role"]


def invalidate_api_key_cache(key_hash: str) -> None:
    _api_key_cache.pop(key_hash, None)


async def get_current_user(request: Request) -> str | None:
    settings: Settings = request.app.state.settings
    request.state.auth_method = None
    request.state.api_key_role = None

    # 1. Dev bypass
    if settings.dev_user:
        request.state.auth_method = "dev_bypass"
        return settings.dev_user

    # 2. K8s SA bearer token
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        allowlist = _parse_sa_allowlist(settings.sa_allowlist_str)
        if allowlist:
            sa_identity = await _validate_sa_token(token, allowlist)
            if sa_identity:
                request.state.auth_method = "sa_token"
                return sa_identity

    # 3. API key
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        result = _validate_api_key_cached(request, api_key)
        if result:
            user, role = result
            request.state.auth_method = "api_key"
            request.state.api_key_role = role
            return user

    # 4. OAuth proxy headers — require proxy secret
    expected_secret = settings.proxy_verification_secret
    if not expected_secret:
        logger.debug("no proxy_verification_secret configured — rejecting proxy headers")
        return None

    actual_secret = request.headers.get("X-Proxy-Secret", "")
    if actual_secret != expected_secret:
        logger.warning("proxy secret mismatch — rejecting forwarded headers")
        return None

    email = request.headers.get("X-Forwarded-Email", "")
    if not email:
        email = request.headers.get("X-Forwarded-User", "")
    if email:
        request.state.auth_method = "oauth_proxy"
    return email or None


async def require_auth(request: Request) -> str:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _check_api_key_role_ceiling(request: Request, required_role: str) -> None:
    if getattr(request.state, "auth_method", None) == "api_key":
        key_role = getattr(request.state, "api_key_role", "user")
        role_levels = {"user": 0, "curator": 1, "admin": 2}
        if role_levels.get(key_role, 0) < role_levels[required_role]:
            raise HTTPException(
                status_code=403,
                detail=f"API key role '{key_role}' insufficient — {required_role} required",
            )


async def require_curator(request: Request) -> str:
    user = await require_auth(request)
    _check_api_key_role_ceiling(request, "curator")
    settings: Settings = request.app.state.settings
    if not settings.is_curator(user) and not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Curator role required")
    return user


async def require_admin(request: Request) -> str:
    user = await require_auth(request)
    _check_api_key_role_ceiling(request, "admin")
    settings: Settings = request.app.state.settings
    if not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
