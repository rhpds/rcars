"""Recommendation worker task."""

from __future__ import annotations

from rcars.workers.base import WorkerContext, publish_progress
from rcars.services.recommender.pipeline import run_query
from rcars.services.recommender.drivers import get_driver
import structlog

logger = structlog.get_logger()


async def run_recommendation(
    ctx: dict, job_id: str, query: str, stages: list[str] | None = None,
    prod_only: bool = True, include_zt: bool = True,
    user_email: str | None = None,
    depth: str = "high",
    content_types: list[str] | None = None,
) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("picked_up", action="picked_up", queue="recommend")
    wctx.db.update_job_status(job_id, "running")

    try:
        async def on_progress(data: dict):
            await publish_progress(wctx.relay, job_id, wctx.db, **data)

        category_states = await run_query(
            query=query,
            db=wctx.db,
            settings=wctx.settings,
            stages=stages or (["prod"] if prod_only else ["prod", "dev", "event"]),
            include_zt=include_zt,
            on_progress=on_progress,
            depth=depth,
            content_types=content_types,
        )

        candidates_json = []
        combined_assessment = None
        combined_gaps = None
        for cat, state in category_states.items():
            driver_inst = get_driver(state.candidates[0].content_type) if state.candidates else None
            if driver_inst:
                candidates_json.extend([driver_inst.serialize(c, include_performance=True, db=wctx.db)
                                        for c in state.candidates])
            if state.overall_assessment:
                combined_assessment = state.overall_assessment
            if state.content_gaps:
                combined_gaps = (combined_gaps or []) + state.content_gaps

        results = {
            "phase": "COMPLETE" if candidates_json else "NO_MATCHES",
            "candidates": candidates_json,
            "overall_assessment": combined_assessment,
            "content_gaps": combined_gaps,
        }

        wctx.db.complete_job(job_id, result_json=results)

        wctx.db.log_advisor_session(
            session_id=job_id,
            turn_index=0,
            user_email=user_email,
            query_text=query,
            event_url=None,
            results=candidates_json,
            overall_assessment=combined_assessment,
        )

        log.info("job_complete", action="job_complete",
                 results=len(candidates_json),
                 query=query[:120])
        return results

    except Exception as e:
        log.error("job_failed", action="job_failed", error=str(e))
        safe_error = "An internal error occurred while processing your query."
        wctx.db.fail_job(job_id, error=str(e))
        await wctx.relay.publish(job_id, {"phase": "failed", "error": safe_error})
        raise
