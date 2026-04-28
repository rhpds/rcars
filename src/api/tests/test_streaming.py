import asyncio
import pytest
from redis.asyncio import Redis
from rcars.api.streaming import JobProgressRelay, translate_to_user_message


def test_translate_vector_search_started():
    msg = {"phase": "vector_search", "status": "started"}
    result = translate_to_user_message(msg)
    assert "Searching" in result


def test_translate_vector_search_complete():
    msg = {"phase": "vector_search", "status": "complete", "candidates": 42}
    result = translate_to_user_message(msg)
    assert "42" in result


def test_translate_triage_progress():
    msg = {"phase": "triage", "status": "progress", "current": 12, "total": 42}
    result = translate_to_user_message(msg)
    assert "12" in result
    assert "42" in result


def test_translate_triage_complete():
    msg = {"phase": "triage", "status": "complete", "relevant": 8}
    result = translate_to_user_message(msg)
    assert "8" in result


def test_translate_rationale_progress():
    msg = {"phase": "rationale", "status": "progress", "current": 2, "top_n": 5}
    result = translate_to_user_message(msg)
    assert "2" in result
    assert "5" in result


def test_translate_complete():
    msg = {"phase": "complete", "results": 5}
    result = translate_to_user_message(msg)
    assert "Complete" in result


def test_translate_failed():
    msg = {"phase": "failed", "error": "Vertex API 429"}
    result = translate_to_user_message(msg)
    assert "Vertex API 429" in result


@pytest.mark.asyncio
async def test_relay_publishes_and_receives():
    redis = Redis.from_url("redis://localhost:6379", decode_responses=True)
    relay = JobProgressRelay(redis)
    job_id = "test-job-relay"

    received = []

    async def collect():
        async for msg in relay.subscribe(job_id):
            if msg is None:
                continue
            received.append(msg)
            if msg.get("phase") == "complete":
                break

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.1)

    await relay.publish(job_id, {"phase": "vector_search", "status": "started"})
    await relay.publish(job_id, {"phase": "vector_search", "status": "complete", "candidates": 10})
    await relay.publish(job_id, {"phase": "complete", "results": 3})

    await asyncio.wait_for(task, timeout=5.0)
    await redis.aclose()

    assert len(received) == 3
    assert received[0]["phase"] == "vector_search"
    assert received[-1]["phase"] == "complete"
