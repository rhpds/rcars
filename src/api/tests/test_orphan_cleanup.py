"""Tests for queued-job orphan reconciliation (RHDPCD-258)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from rcars.workers.settings import _reconcile_queued_orphans


def _mock_db(jobs, fail_return=0):
    db = MagicMock()
    db.get_queued_job_ids.return_value = jobs
    db.fail_queued_orphans.return_value = fail_return
    return db


@pytest.mark.asyncio
async def test_orphan_not_in_redis_is_failed():
    db = _mock_db(
        [{"id": "aaa", "queue": "analyze"}, {"id": "bbb", "queue": "analyze"}],
        fail_return=1,
    )
    redis = AsyncMock()
    redis.zrange.return_value = ["bbb"]  # bbb present, aaa missing

    count = await _reconcile_queued_orphans(db, redis)

    db.fail_queued_orphans.assert_called_once_with(["aaa"])
    assert count == 1


@pytest.mark.asyncio
async def test_job_present_in_redis_is_not_failed():
    db = _mock_db([{"id": "aaa", "queue": "analyze"}])
    redis = AsyncMock()
    redis.zrange.return_value = ["aaa"]

    count = await _reconcile_queued_orphans(db, redis)

    db.fail_queued_orphans.assert_called_once_with([])
    assert count == 0


@pytest.mark.asyncio
async def test_recommend_job_checked_against_recommend_queue():
    db = _mock_db(
        [{"id": "scan-1", "queue": "analyze"}, {"id": "rec-1", "queue": "recommend"}],
        fail_return=0,
    )
    redis = AsyncMock()
    redis.zrange.side_effect = lambda queue, *_: {
        "arq:queue:scan": ["scan-1"],
        "arq:queue:recommend": ["rec-1"],
    }[queue]

    count = await _reconcile_queued_orphans(db, redis)

    calls = {call.args[0] for call in redis.zrange.call_args_list}
    assert "arq:queue:scan" in calls
    assert "arq:queue:recommend" in calls
    db.fail_queued_orphans.assert_called_once_with([])
    assert count == 0


@pytest.mark.asyncio
async def test_orphaned_recommend_job_is_failed():
    db = _mock_db([{"id": "rec-orphan", "queue": "recommend"}], fail_return=1)
    redis = AsyncMock()
    redis.zrange.return_value = []  # nothing in recommend queue

    count = await _reconcile_queued_orphans(db, redis)

    db.fail_queued_orphans.assert_called_once_with(["rec-orphan"])
    assert count == 1


@pytest.mark.asyncio
async def test_no_queued_jobs_skips_redis():
    db = _mock_db([])
    redis = AsyncMock()

    count = await _reconcile_queued_orphans(db, redis)

    redis.zrange.assert_not_called()
    db.fail_queued_orphans.assert_not_called()
    assert count == 0
