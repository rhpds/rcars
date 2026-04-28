"""Redis pub/sub relay and SSE streaming for job progress."""

from __future__ import annotations

import json
from typing import AsyncGenerator
from redis.asyncio import Redis
from starlette.responses import StreamingResponse
import structlog

logger = structlog.get_logger()


class JobProgressRelay:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def publish(self, job_id: str, message: dict) -> None:
        channel = f"job:{job_id}"
        await self.redis.publish(channel, json.dumps(message))

    async def subscribe(self, job_id: str, keepalive_interval: float = 15) -> AsyncGenerator[dict | None, None]:
        """Subscribe to job progress. Yields message dicts, or None as keepalive."""
        channel = f"job:{job_id}"
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=keepalive_interval)
                if message is None:
                    yield None
                    continue
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    yield data
                    if data.get("phase") in ("complete", "failed"):
                        break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


def translate_to_user_message(msg: dict) -> str:
    phase = msg.get("phase", "")
    status = msg.get("status", "")

    if phase == "catalog_refresh":
        return msg.get("message", f"Catalog refresh: {status}")

    if phase == "stale_check":
        return msg.get("message", f"Stale check: {status}")

    if phase == "vector_search":
        if status == "started":
            return "Searching content library..."
        if status == "complete":
            return f"Found {msg.get('candidates', 0)} candidates"

    if phase == "triage":
        if status == "started":
            return f"Evaluating relevance of {msg.get('total', '?')} candidates..."
        if status == "progress":
            return f"Evaluating relevance ({msg['current']} of {msg['total']})..."
        if status == "complete":
            return f"{msg.get('relevant', 0)} relevant items identified"

    if phase == "rationale":
        if status == "started":
            return f"Generating detailed analysis for top {msg.get('top_n', '?')} matches..."
        if status == "progress":
            return f"Generating detailed analysis ({msg['current']} of {msg['top_n']})..."
        if status == "complete":
            return "Analysis complete"

    if phase == "complete":
        return "Complete"

    if phase == "failed":
        return f"Error: {msg.get('error', 'Unknown error')}"

    return f"{phase}: {status}"


async def sse_stream(relay: JobProgressRelay, job_id: str) -> AsyncGenerator[str, None]:
    async for msg in relay.subscribe(job_id):
        if msg is None:
            yield ": keepalive\n\n"
            continue
        user_message = translate_to_user_message(msg)
        event_data = {**msg, "user_message": user_message}
        yield f"data: {json.dumps(event_data)}\n\n"


def create_sse_response(relay: JobProgressRelay, job_id: str) -> StreamingResponse:
    return StreamingResponse(
        sse_stream(relay, job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
