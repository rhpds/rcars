"""Base worker context and progress helpers."""

from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass
from redis.asyncio import Redis
from rcars.db import Database
from rcars.config import Settings
from rcars.api.streaming import JobProgressRelay
import structlog

logger = structlog.get_logger()


@dataclass
class WorkerContext:
    db: Database
    redis: Redis
    relay: JobProgressRelay
    settings: Settings


async def publish_progress(relay: JobProgressRelay, job_id: str, db: Database, **kwargs) -> None:
    await relay.publish(job_id, kwargs)
    db.append_job_progress(job_id, kwargs)
    logger.info(
        "phase_progress",
        action="phase_progress",
        job_id=job_id,
        **kwargs,
    )


def with_job_context(fn):
    """Bind the RCARS ``job_id`` to structlog contextvars while a job runs.

    Every ``run_*`` job takes ``job_id`` as an argument. arq's own job id is not
    always the same (some enqueues omit ``_job_id``), so read the argument.
    Contextvars are copied into ``asyncio.to_thread``, so sync LLM code is covered.
    The binding is always cleared afterwards so it cannot leak into the next job.
    """
    sig = inspect.signature(fn)

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            job_id = sig.bind_partial(*args, **kwargs).arguments.get("job_id")
        except TypeError:
            job_id = None
        if not job_id:
            return await fn(*args, **kwargs)
        tokens = structlog.contextvars.bind_contextvars(job_id=job_id)
        try:
            return await fn(*args, **kwargs)
        finally:
            structlog.contextvars.reset_contextvars(**tokens)

    wrapper.__rcars_job_context__ = True
    return wrapper
