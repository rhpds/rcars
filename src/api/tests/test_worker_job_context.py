"""job_id is bound to structlog contextvars for the duration of every arq job."""
import asyncio
import json

import pytest
import structlog

from rcars.logging import setup_logging, get_logger
from rcars.workers.base import with_job_context
from rcars.workers.settings import WorkerSettings, RecommendWorkerSettings


def _lines(out: str) -> list[dict]:
    return [json.loads(l) for l in out.splitlines() if l.strip()]


@pytest.fixture(autouse=True)
def _clean():
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


async def test_bound_inside_job_and_cleared_after(capsys):
    setup_logging(level="INFO", component="scan-worker")

    @with_job_context
    async def run_x(ctx, job_id, other=1):
        get_logger().info("inside")  # no explicit job_id
        await asyncio.to_thread(lambda: get_logger().info("in_thread"))

    await run_x({}, "job-1")
    get_logger().info("after")
    lines = {l["event"]: l for l in _lines(capsys.readouterr().out)}
    assert lines["inside"]["job_id"] == "job-1"
    assert lines["in_thread"]["job_id"] == "job-1"
    assert "job_id" not in lines["after"]


async def test_job_id_as_kwarg_and_cleared_on_error(capsys):
    setup_logging(level="INFO", component="scan-worker")

    @with_job_context
    async def run_y(ctx, job_id):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await run_y({}, job_id="job-2")
    assert "job_id" not in structlog.contextvars.get_contextvars()


async def test_none_job_id_binds_nothing():
    @with_job_context
    async def run_z(ctx, job_id=None):
        return structlog.contextvars.get_contextvars()

    assert await run_z({}) == {}
    assert await run_z({}, job_id=None) == {}


async def test_concurrent_jobs_do_not_leak(capsys):
    setup_logging(level="INFO", component="scan-worker")

    @with_job_context
    async def run_c(ctx, job_id):
        await asyncio.sleep(0.01)
        get_logger().info("tick", who=job_id)

    await asyncio.gather(run_c({}, "a"), run_c({}, "b"))
    for l in _lines(capsys.readouterr().out):
        assert l["job_id"] == l["who"]


def test_all_registered_functions_wrapped():
    for settings in (WorkerSettings, RecommendWorkerSettings):
        for f in settings.functions:
            coro = getattr(f, "coroutine", f)
            assert getattr(coro, "__rcars_job_context__", False), coro.__name__
        for c in getattr(settings, "cron_jobs", []):
            if c.coroutine.__name__ != "cleanup_orphaned_jobs":
                assert getattr(c.coroutine, "__rcars_job_context__", False)


async def test_cron_nightly_pipeline_binds_created_job_id(monkeypatch):
    """Cron passes no job_id; the pipeline creates one and nested steps must see it."""
    from unittest.mock import AsyncMock, MagicMock
    from rcars.workers import ops

    seen = {}

    async def _babylon(ctx, job_id, **kwargs):
        seen["babylon"] = structlog.contextvars.get_contextvars().get("job_id")
        return {"warnings": []}

    async def _osspa(ctx, job_id, **kwargs):
        seen["osspa"] = structlog.contextvars.get_contextvars().get("job_id")
        return {"status": "complete"}

    monkeypatch.setattr(ops, "run_babylon_pipeline", _babylon)
    monkeypatch.setattr(ops, "run_osspa_pipeline", _osspa)

    db = MagicMock()
    db.create_job.return_value = "created-job"
    settings = MagicMock(github_app_id=None)
    monkeypatch.setattr("rcars.services.jira.jira_auth_configured", lambda s: False)
    wctx = MagicMock(db=db, relay=MagicMock(publish=AsyncMock()), settings=settings)

    wrapped = with_job_context(ops.run_nightly_pipeline)
    await wrapped({"worker_ctx": wctx})

    assert seen == {"babylon": "created-job", "osspa": "created-job"}
    assert "job_id" not in structlog.contextvars.get_contextvars()
