from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path

import httpx
import structlog
from fastapi import Request, HTTPException
from rcars.config import Settings

logger = structlog.get_logger(component="auth")

_K8S_TOKEN_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
_K8S_CA_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
_TOKEN_REVIEW_URL = (
    "https://kubernetes.default.svc/apis/authentication.k8s.io/v1/tokenreviews"
)

# In-memory cache: key_hash → (user_email, role, expires_at_ts, cached_at)
_api_key_cache: dict[str, tuple[str, str, float | None, float]] = {}
_CACHE_TTL = 60.0


def _log_auth_decision(
    request: Request,
    auth_method: str,
    user: str | None,
    outcome: str,
    key_id: int | None = None,
):
    source_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not source_ip and request.client:
        source_ip = request.client.host
    logger.info(
        "auth_decision",
        auth_method=auth_method,
        user=user or "",
        key_id=key_id,
        source_ip=source_ip or "unknown",
        outcome=outcome,
    )


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
            return None

        username = status.get("user", {}).get("username", "")
        if username not in allowlist:
            return None

        return username

    except Exception:
        logger.warning("SA token validation failed", exc_info=True)
        return None


def _validate_api_key_cached(request: Request, raw_key: str) -> tuple[str, str, int] | None:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    now = time.monotonic()

    cached = _api_key_cache.get(key_hash)
    if cached:
        user, role, expires_ts, cached_at = cached
        if now - cached_at < _CACHE_TTL:
            if expires_ts and time.time() > expires_ts:
                _api_key_cache.pop(key_hash, None)
                return None
            return user, role, None  # No key_id for cached lookups
        _api_key_cache.pop(key_hash, None)

    db = request.app.state.db
    row = db.get_api_key_by_hash(key_hash)
    if not row:
        return None

    expires_ts = row["expires_at"].timestamp() if row.get("expires_at") else None
    _api_key_cache[key_hash] = (row["created_by"], row["role"], expires_ts, now)
    db.touch_api_key(row["id"])
    return row["created_by"], row["role"], row["id"]


def invalidate_api_key_cache(key_hash: str) -> None:
    _api_key_cache.pop(key_hash, None)


async def get_current_user(request: Request) -> str | None:
    settings: Settings = request.app.state.settings
    request.state.auth_method = None
    request.state.api_key_role = None

    # 1. Dev bypass
    if settings.dev_user:
        request.state.auth_method = "dev_bypass"
        _log_auth_decision(request, "dev_bypass", settings.dev_user, "success")
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
                _log_auth_decision(request, "sa_token", sa_identity, "success")
                return sa_identity

    # 3. API key
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        result = _validate_api_key_cached(request, api_key)
        if result:
            user, role, key_id = result
            request.state.auth_method = "api_key"
            request.state.api_key_role = role
            _log_auth_decision(request, "api_key", user, "success", key_id=key_id)
            return user

    # 4. OAuth proxy headers — require proxy secret
    expected_secret = settings.proxy_verification_secret
    if not expected_secret:
        # Check if proxy headers are present before logging rejection
        if request.headers.get("X-Forwarded-Email") or request.headers.get("X-Forwarded-User"):
            _log_auth_decision(request, "oauth_proxy", None, "rejected_no_proxy_secret")
        # Fall through to no credentials case
    else:
        actual_secret = request.headers.get("X-Proxy-Secret", "")
        if not hmac.compare_digest(actual_secret, expected_secret):
            _log_auth_decision(request, "oauth_proxy", None, "rejected_proxy_secret_mismatch")
            # Fall through to no credentials case
        else:
            email = request.headers.get("X-Forwarded-Email", "")
            if not email:
                email = request.headers.get("X-Forwarded-User", "")
            if email:
                request.state.auth_method = "oauth_proxy"
                _log_auth_decision(request, "oauth_proxy", email, "success")
                return email

    # No credentials matched
    _log_auth_decision(request, "none", None, "rejected_no_credentials")
    return None


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
