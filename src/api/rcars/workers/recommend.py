"""Recommendation worker task."""

from __future__ import annotations

from rcars.workers.base import WorkerContext, publish_progress
from rcars.services.recommender.pipeline import run_query
import structlog

logger = structlog.get_logger()


async def run_recommendation(
    ctx: dict, job_id: str, query: str, stages: list[str] | None = None,
    prod_only: bool = True, include_zt: bool = True,
    user_email: str | None = None, opted_out: bool = False,
) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("picked_up", action="picked_up", queue="recommend")
    wctx.db.update_job_status(job_id, "running")

    try:
        async def on_progress(data: dict):
            await publish_progress(wctx.relay, job_id, wctx.db, **data)

        state = await run_query(
            query=query,
            db=wctx.db,
            settings=wctx.settings,
            stages=stages or (["prod"] if prod_only else ["prod", "dev", "event"]),
            include_zt=include_zt,
            on_progress=on_progress,
        )

        candidates_json = [
            {
                "ci_name": c.ci_name,
                "display_name": c.display_name,
                "tier": c.tier,
                "relevance_score": c.relevance_score,
                "vector_similarity_pct": c.vector_similarity_pct,
                "stage": c.stage,
                "catalog_namespace": c.catalog_namespace,
                "duration_min": c.duration_min,
                "duration_source": c.duration_source,
                "learning_objectives": c.learning_objectives,
                "why_it_fits": c.why_it_fits,
                "how_to_use": c.how_to_use,
                "suggested_format": c.suggested_format,
                "duration_notes": c.duration_notes,
                "caveats": c.caveats,
            }
            for c in state.candidates
        ]

        from rcars.services.reporting_sync import compute_sales_impact

        for candidate in candidates_json:
            content_id = candidate.get("content_id") or f"babylon:{candidate['ci_name']}"
            channels = wctx.db.get_performance_channels(content_id)
            rhdp = next((ch for ch in channels if ch["channel"] == "rhdp"), None) if channels else None
            if rhdp:
                import json as _json
                wm = rhdp.get("windowed_metrics") or {}
                if isinstance(wm, str):
                    wm = _json.loads(wm)
                q = wm.get("3m", {})
                candidate["provisions_quarter"] = q.get("provisions", 0)
                candidate["avg_cost_per_provision"] = float(rhdp.get("avg_cost_per_provision") or 0)
                candidate["sales_impact"] = compute_sales_impact(float(rhdp.get("closed_amount") or 0))
            else:
                candidate["provisions_quarter"] = candidate.get("provisions_quarter")
                candidate["avg_cost_per_provision"] = None
                candidate["sales_impact"] = None

        results = {
            "phase": state.phase,
            "candidates": candidates_json,
            "overall_assessment": state.overall_assessment,
            "content_gaps": state.content_gaps,
        }

        wctx.db.complete_job(job_id, result_json=results)

        # Log to advisor_sessions for query history
        wctx.db.log_advisor_session(
            session_id=job_id,
            turn_index=0,
            user_email=user_email,
            query_text=query,
            event_url=None,
            results=candidates_json,
            overall_assessment=state.overall_assessment,
            opted_out=opted_out,
        )

        log.info("job_complete", action="job_complete", results=len(state.candidates))
        return results

    except Exception as e:
        log.error("job_failed", action="job_failed", error=str(e))
        safe_error = "An internal error occurred while processing your query."
        wctx.db.fail_job(job_id, error=str(e))
        await wctx.relay.publish(job_id, {"phase": "failed", "error": safe_error})
        raise
