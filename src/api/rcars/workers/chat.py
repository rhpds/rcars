"""Chat turn worker task — runs on the recommend queue."""
from __future__ import annotations

import structlog

from rcars.services.chat.orchestrator import process_turn
from rcars.workers.base import WorkerContext, publish_progress

logger = structlog.get_logger()


async def run_chat_turn(
    ctx: dict, job_id: str, message: str, session_id: str,
    stages: list[str] | None = None, include_zt: bool = True,
    user_email: str | None = None, is_admin: bool = False,
    routed: dict | None = None,
) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id, component="chat")
    log.info("picked_up", action="picked_up", queue="recommend", job_type="chat")
    wctx.db.update_job_status(job_id, "running")
    try:
        async def on_progress(data: dict):
            await publish_progress(wctx.relay, job_id, wctx.db, **data)

        envelope = await process_turn(
            message=message, session_id=session_id, user_email=user_email,
            is_admin=is_admin, stages=stages, include_zt=include_zt,
            routed=routed,
            db=wctx.db, settings=wctx.settings, on_progress=on_progress)
        result = {**envelope, "session_id": session_id}
        wctx.db.complete_job(job_id, result_json=result)
        await on_progress({"phase": "complete", "results": len(envelope.get("blocks", []))})
        log.info("job_complete", action="job_complete", intent=envelope.get("intent"))
        return result
    except Exception as e:
        log.error("job_failed", action="job_failed", error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        await wctx.relay.publish(job_id, {"phase": "failed",
                                          "error": "An internal error occurred while processing your message."})
        raise
