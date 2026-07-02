"""Per-user rate limiting via slowapi + Redis."""

from __future__ import annotations

from slowapi import Limiter
from starlette.requests import Request


def _get_user_key(request: Request) -> str:
    # Key off X-Forwarded-Email — trusted when proxy_verification_secret is
    # configured (auth.py validates X-Proxy-Secret before trusting this header).
    # Falls back to client IP for unauthenticated requests.
    return request.headers.get(
        "X-Forwarded-Email",
        request.client.host if request.client else "unknown",
    )


limiter = Limiter(key_func=_get_user_key, key_prefix="rcars:")
