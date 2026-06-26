"""arq worker settings — startup, shutdown, and task registration."""

from __future__ import annotations

import os
from urllib.parse import unquote, urlparse
from arq.connections import RedisSettings
from redis.asyncio import Redis

from rcars.config import Settings


def _redis_settings_from_url(url: str) -> RedisSettings:
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=unquote(parsed.password) if parsed.password else None,
        database=int(parsed.path.lstrip("/") or 0) if parsed.path and parsed.path != "/" else 0,
    )
from rcars.db import Database
from rcars.logging import setup_logging, get_logger
from rcars.api.streaming import JobProgressRelay
from rcars.workers.base import WorkerContext
from rcars.workers.recommend import run_recommendation
from rcars.workers.scan import run_analysis
from arq import cron, func
from rcars.workers.ops import run_catalog_refresh, run_stale_check, run_nightly_pipeline, run_workload_scan, run_reporting_sync_job


async def startup(ctx: dict) -> None:
    setup_logging(level="INFO", component="worker")
    log = get_logger()

    settings = Settings()
    db = Database(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    relay = JobProgressRelay(redis)

    ctx["worker_ctx"] = WorkerContext(db=db, redis=redis, relay=relay, settings=settings)

    orphaned = db.cleanup_orphaned_jobs()
    if orphaned:
        log.info("orphaned_jobs_cleaned", action="orphaned_jobs_cleaned", count=orphaned)

    if settings.use_litemaas:
        from rcars.config import fetch_litemaas_models
        models = fetch_litemaas_models(settings)
        log.info("litemaas_models_loaded", action="litemaas_init",
                 model_count=len(models), models=sorted(models))

    log.info("worker_started", action="worker_started")


async def shutdown(ctx: dict) -> None:
    worker_ctx: WorkerContext = ctx["worker_ctx"]
    worker_ctx.db.close()
    await worker_ctx.redis.aclose()
    get_logger().info("worker_stopped", action="worker_stopped")


async def cleanup_orphaned_jobs(ctx: dict) -> int:
    wctx: WorkerContext = ctx["worker_ctx"]
    count = wctx.db.cleanup_orphaned_jobs()
    if count:
        get_logger().info("orphaned_jobs_sweep", action="orphaned_jobs_sweep", count=count)
    return count


_pipeline_enabled = os.environ.get("RCARS_PIPELINE_ENABLED", "true").lower() == "true"
_pipeline_hour = int(os.environ.get("RCARS_PIPELINE_HOUR", "4"))
_pipeline_minute = int(os.environ.get("RCARS_PIPELINE_MINUTE", "0"))


class WorkerSettings:
    """Scan/ops worker — handles analysis, catalog operations, and scheduled maintenance."""
    functions = [
        run_analysis,
        run_catalog_refresh,
        func(run_stale_check, timeout=3600),
        func(run_nightly_pipeline, timeout=7200),
        func(run_workload_scan, timeout=3600),
        func(run_reporting_sync_job, timeout=600),
    ]
    cron_jobs = ([
        cron(run_nightly_pipeline, hour=_pipeline_hour, minute=_pipeline_minute,
             timeout=7200, unique=True),
    ] if _pipeline_enabled else []) + [
        cron(cleanup_orphaned_jobs, minute={0, 30}, timeout=60, unique=True),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings_from_url(os.environ.get("RCARS_REDIS_URL", "redis://localhost:6379"))
    max_jobs = int(os.environ.get("RCARS_SCAN_MAX_JOBS", "5"))
    job_timeout = 600
    queue_name = "arq:queue:scan"


class RecommendWorkerSettings:
    """Recommendation worker — handles advisor queries. Separate from scan to avoid starvation."""
    functions = [run_recommendation]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings_from_url(os.environ.get("RCARS_REDIS_URL", "redis://localhost:6379"))
    max_jobs = int(os.environ.get("RCARS_RECOMMEND_MAX_JOBS", "10"))
    job_timeout = 120
    queue_name = "arq:queue:recommend"
