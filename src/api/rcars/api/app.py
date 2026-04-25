from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis.asyncio import Redis

from rcars.config import Settings
from rcars.db import Database
from rcars.logging import setup_logging
from rcars.api.middleware.request_logging import RequestLoggingMiddleware
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
        version="2.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(advisor.router, prefix="/api/v1")
    app.include_router(catalog.router, prefix="/api/v1")
    app.include_router(analysis.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    return app
