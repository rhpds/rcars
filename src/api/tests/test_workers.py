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
