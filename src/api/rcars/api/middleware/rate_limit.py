"""Per-user rate limiting via slowapi + Redis."""

from __future__ import annotations

from slowapi import Limiter
from starlette.requests import Request


def _get_user_key(request: Request) -> str:
    return request.headers.get(
        "X-Forwarded-Email",
        request.client.host if request.client else "unknown",
    )


limiter = Limiter(key_func=_get_user_key, key_prefix="rcars:")
