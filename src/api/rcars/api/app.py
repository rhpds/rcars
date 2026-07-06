from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from redis.asyncio import Redis
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from rcars.config import Settings
from rcars.db import Database
from rcars.logging import setup_logging
from rcars.api.middleware.request_logging import RequestLoggingMiddleware
from rcars.api.middleware.rate_limit import limiter
from arq.connections import ArqRedis
from rcars.api.routes import health, auth, advisor, catalog, analysis, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    setup_logging(level="INFO", component="api")

    app.state.db = Database(settings.database_url)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.arq_redis = ArqRedis.from_url(settings.redis_url)

    yield

    app.state.db.close()
    await app.state.redis.aclose()
    await app.state.arq_redis.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="RCARS API",
        description=(
            "RHDP Content Advisory & Recommendation System. "
            "Matches catalog items to events, opportunities, and user queries "
            "using vector search, LLM triage, and LLM-generated rationale.\n\n"
            "**Authentication:** API keys (`X-API-Key` header), "
            "Kubernetes ServiceAccount bearer tokens, or "
            "OAuth proxy headers (web UI only).\n\n"
            "**API keys:** Obtain via `POST /api/v1/auth/token` (OAuth login) "
            "or create via `POST /api/v1/auth/keys` (admin). "
            "Roles: `user` (read-only), `curator` (curation + analysis), `admin` (full access).\n\n"
            "**Async jobs:** Long-running operations return a `job_id` immediately. "
            "Poll results via the result endpoint or stream progress via SSE."
        ),
        version="1.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key obtained via OAuth login or admin creation",
            }
        }
        schema["security"] = [{"ApiKeyAuth": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    app.add_middleware(RequestLoggingMiddleware)

    limiter._storage_uri = settings.redis_url
    limiter._swallow_errors = True
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
    app.include_router(advisor.router, prefix="/api/v1", tags=["Advisor"])
    app.include_router(catalog.router, prefix="/api/v1", tags=["Catalog"])
    app.include_router(analysis.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1", tags=["Administration"])

    return app
