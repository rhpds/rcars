from rcars.workers.base import WorkerContext
from rcars.workers.settings import WorkerSettings


def test_worker_context_has_required_fields():
    fields = {f.name for f in WorkerContext.__dataclass_fields__.values()}
    assert "db" in fields
    assert "redis" in fields
    assert "relay" in fields
    assert "settings" in fields


def test_worker_settings_has_lifecycle():
    assert WorkerSettings.on_startup is not None
    assert WorkerSettings.on_shutdown is not None
    assert WorkerSettings.max_jobs == 5
    assert WorkerSettings.job_timeout == 600


from unittest.mock import AsyncMock, MagicMock
from rcars.config import Settings


def _worker_ctx(**setting_overrides):
    """Minimal ctx dict for testing ops pipeline functions."""
    settings = Settings(
        database_url="postgresql://rcars:dev@localhost:5432/rcars_test",
        **setting_overrides,
    )
    db = MagicMock()
    db.create_job.return_value = "test-job-id"
    db.append_job_progress.return_value = None
    db.update_job_status.return_value = None
    db.complete_job.return_value = None
    db.fail_job.return_value = None

    relay = MagicMock()
    relay.publish = AsyncMock()

    redis = MagicMock()
    redis.enqueue_job = AsyncMock()

    from rcars.workers.base import WorkerContext
    wctx = WorkerContext(db=db, redis=redis, relay=relay, settings=settings)
    return {"worker_ctx": wctx, "redis": redis}


import pytest


@pytest.mark.asyncio
async def test_run_osspa_sync_job_completes(monkeypatch):
    from rcars.workers import ops

    stats = {"status": "complete", "upserted": 2, "analyzed": 1,
             "skipped": 1, "retired": 0, "failed": 0}
    monkeypatch.setattr(ops, "run_osspa_sync", lambda *a, **kw: stats)

    ctx = _worker_ctx()
    result = await ops.run_osspa_sync_job(ctx, job_id="job-1")

    assert result == stats


@pytest.mark.asyncio
async def test_nightly_pipeline_runs_osspa_after_babylon(monkeypatch):
    from rcars.workers import ops

    order = []

    async def _babylon(ctx, job_id):
        order.append("babylon")
        return {"refresh": None, "warnings": []}

    async def _osspa(ctx, job_id):
        order.append("osspa")
        return {"status": "complete"}

    monkeypatch.setattr(ops, "run_babylon_pipeline", _babylon)
    monkeypatch.setattr(ops, "run_osspa_pipeline", _osspa)

    result = await ops.run_nightly_pipeline(_worker_ctx(), job_id="job-2")

    assert order == ["babylon", "osspa"]
    assert result["osspa"] == {"status": "complete"}


@pytest.mark.asyncio
async def test_osspa_pipeline_runs_even_when_babylon_fails(monkeypatch):
    from rcars.workers import ops

    async def _babylon(ctx, job_id):
        raise RuntimeError("babylon exploded")

    async def _osspa(ctx, job_id):
        return {"status": "complete"}

    monkeypatch.setattr(ops, "run_babylon_pipeline", _babylon)
    monkeypatch.setattr(ops, "run_osspa_pipeline", _osspa)

    result = await ops.run_nightly_pipeline(_worker_ctx(), job_id="job-3")

    assert result["osspa"] == {"status": "complete"}
    assert any("babylon exploded" in w for w in result["warnings"])


@pytest.mark.asyncio
async def test_osspa_pipeline_respects_the_enable_flag(monkeypatch):
    from rcars.workers import ops

    called = []
    monkeypatch.setattr(ops, "run_osspa_sync", lambda *a, **kw: called.append(1))

    ctx = _worker_ctx(osspa_sync_enabled=False)
    result = await ops.run_osspa_pipeline(ctx, job_id="job-4")

    assert called == []
    assert result["status"] == "disabled"
