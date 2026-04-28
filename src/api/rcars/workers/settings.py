"""arq worker settings — startup, shutdown, and task registration."""

from __future__ import annotations

import os
from urllib.parse import urlparse
from arq.connections import RedisSettings
from redis.asyncio import Redis

from rcars.config import Settings


def _redis_settings_from_url(url: str) -> RedisSettings:
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0) if parsed.path and parsed.path != "/" else 0,
    )
from rcars.db import Database
from rcars.logging import setup_logging, get_logger
from rcars.api.streaming import JobProgressRelay
from rcars.workers.base import WorkerContext
from rcars.workers.recommend import run_recommendation
from rcars.workers.scan import run_analysis
from arq import func
from rcars.workers.ops import run_catalog_refresh, run_stale_check


async def startup(ctx: dict) -> None:
    setup_logging(level="INFO", component="worker")
    log = get_logger()

    settings = Settings()
    db = Database(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    relay = JobProgressRelay(redis)

    ctx["worker_ctx"] = WorkerContext(db=db, redis=redis, relay=relay, settings=settings)
    log.info("worker_started", action="worker_started")


async def shutdown(ctx: dict) -> None:
    worker_ctx: WorkerContext = ctx["worker_ctx"]
    worker_ctx.db.close()
    await worker_ctx.redis.aclose()
    get_logger().info("worker_stopped", action="worker_stopped")


class WorkerSettings:
    """Scan/ops worker — handles analysis and catalog operations."""
    functions = [run_analysis, run_catalog_refresh, func(run_stale_check, timeout=3600)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings_from_url(os.environ.get("RCARS_REDIS_URL", "redis://localhost:6379"))
    max_jobs = 5
    job_timeout = 600
    queue_name = "arq:queue:scan"


class RecommendWorkerSettings:
    """Recommendation worker — handles advisor queries. Separate from scan to avoid starvation."""
    functions = [run_recommendation]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings_from_url(os.environ.get("RCARS_REDIS_URL", "redis://localhost:6379"))
    max_jobs = 3
    job_timeout = 120
    queue_name = "arq:queue:recommend"
