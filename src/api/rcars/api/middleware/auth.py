from __future__ import annotations

import logging
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


def _parse_sa_allowlist(allowlist_str: str) -> set[str]:
    """Parse comma-separated SA allowlist string into a set."""
    if not allowlist_str:
        return set()
    return {sa.strip() for sa in allowlist_str.split(",") if sa.strip()}


async def _validate_sa_token(token: str, allowlist: set[str]) -> str | None:
    """Validate a Kubernetes ServiceAccount token via TokenReview API.

    Returns the SA identity string on success, None on failure.
    Never logs the raw token — only the SA identity on successful validation.
    """
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
            logger.warning(
                "SA identity %s not in allowlist", username
            )
            return None

        logger.info("SA token validated for identity: %s", username)
        return username

    except Exception:
        logger.warning("SA token validation failed", exc_info=True)
        return None


async def get_current_user(request: Request) -> str | None:
    settings: Settings = request.app.state.settings
    if settings.dev_user:
        return settings.dev_user

    # Check for SA token auth (Bearer token from service accounts)
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        allowlist = _parse_sa_allowlist(settings.sa_allowlist_str)
        if allowlist:
            sa_identity = await _validate_sa_token(token, allowlist)
            if sa_identity:
                return sa_identity

    # Fallback to OAuth proxy headers
    email = request.headers.get("X-Forwarded-Email", "")
    if not email:
        email = request.headers.get("X-Forwarded-User", "")
    return email or None


async def require_auth(request: Request) -> str:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_curator(request: Request) -> str:
    user = await require_auth(request)
    settings: Settings = request.app.state.settings
    if not settings.is_curator(user) and not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Curator role required")
    return user


async def require_admin(request: Request) -> str:
    user = await require_auth(request)
    settings: Settings = request.app.state.settings
    if not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
