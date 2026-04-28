"""Base worker context and progress helpers."""

from __future__ import annotations

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
