"""arq worker settings — startup, shutdown, and task registration."""

from __future__ import annotations

from arq.connections import RedisSettings
from redis.asyncio import Redis

from rcars.config import Settings
from rcars.db import Database
from rcars.logging import setup_logging, get_logger
from rcars.api.streaming import JobProgressRelay
from rcars.workers.base import WorkerContext


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
    functions = []
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings()
    max_jobs = 5
    job_timeout = 600
    queue_name = "default"
