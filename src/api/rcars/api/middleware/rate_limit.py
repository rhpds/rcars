"""Per-user rate limiting via slowapi + Redis."""

from __future__ import annotations

from slowapi import Limiter
from starlette.requests import Request


def _get_user_key(request: Request) -> str:
    # Use authenticated identity from request.state (set by auth middleware)
    # when available.  Falls back to client IP for unauthenticated endpoints
    # like /auth/token.  We must NOT read X-Forwarded-Email directly here
    # because the rate limiter runs before auth validates the proxy secret,
    # and an attacker could spoof the header to poison another user's quota.
    user = getattr(getattr(request, "state", None), "user", None)
    if user:
        return user
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_user_key, key_prefix="rcars:")
