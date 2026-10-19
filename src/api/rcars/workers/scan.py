"""Queue lifecycle for isolated, per-stage Showroom scans."""
from __future__ import annotations

import asyncio
import structlog

from rcars.services.showroom_scan import scan_babylon_item
from rcars.workers.base import WorkerContext

logger = structlog.get_logger()


async def run_analysis(ctx: dict, job_id: str, content_id: str,
                       sha_siblings: list[dict] | None = None, force: bool = False) -> dict:
    """Accept but ignore pre-rollout sibling payloads; write only the named target."""
    wctx: WorkerContext = ctx["worker_ctx"]
    wctx.db.update_job_status(job_id, "running", progress_json={"content_id": content_id})
    try:
        result = await asyncio.to_thread(scan_babylon_item, wctx.db, wctx.settings, content_id, force=force)
        if result.get("success") or result.get("outcome") == "superseded":
            wctx.db.complete_job(job_id, result_json=result)
        else:
            wctx.db.complete_job(job_id, error=result.get("message", result.get("error", "Scan failed")), result_json=result)
        logger.info("analysis_complete", component="worker", job_id=job_id, action=result["outcome"], **result)
        return result
    except Exception as exc:
        wctx.db.fail_job(job_id, error=str(exc))
        raise
