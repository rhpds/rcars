"""Recommendations endpoint for external integrations.

Low effort runs inline (vector search only, <2s).
Medium effort goes through the job queue (vector search + triage, 5-10s).
For full pipeline with rationale, use POST /advisor/chat instead.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from rcars.api.middleware.auth import require_auth
from rcars.api.middleware.rate_limit import limiter
from rcars.api.schemas import RecommendationLowResponse, RecommendationMediumResponse
from rcars.config import Settings
from rcars.services.recommender.pipeline import run_query
from rcars.services.recommender.serialize import candidates_with_performance
import structlog

logger = structlog.get_logger()

LOW_EFFORT_TIMEOUT_S = 10.0

router = APIRouter(prefix="/recommendations")


class RecommendationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000, description="Natural-language search query (e.g. 'OpenShift AI workshop for beginners')")
    effort: Literal["low", "medium"] = Field(
        default="medium",
        description="low = vector search only, returns inline (~1-2s). medium = vector search + LLM triage, returns job_id (~5-10s).",
    )
    stages: list[Literal["prod", "event", "dev"]] = Field(default=["prod"], description="Lifecycle stages to search. Non-curator users cannot access dev.")
    include_zt: bool = Field(default=True, description="Include zero-touch (fully automated) items in results")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of candidates to return (low effort only)")


def _recommendation_limit() -> str:
    import os
    return f"{os.environ.get('RCARS_RECOMMENDATION_RATE_LIMIT_PER_USER_PER_HOUR', '100')}/hour"


@router.post(
    "",
    summary="Get content recommendations",
    description=(
        "Endpoint for external integrations (chatbots, dashboards, etc.) that need "
        "content recommendations without intent routing.\n\n"
        "**Effort levels:**\n"
        "- `low` — vector search only (~1-2s). Returns results inline as a "
        "`RecommendationLowResponse`. Fast semantic match, unranked.\n"
        "- `medium` — vector search + LLM triage (~5-10s). Returns a "
        "`RecommendationMediumResponse` with a `job_id`. "
        "Poll `GET /advisor/query/{job_id}/result` for ranked results, "
        "or stream via `GET /advisor/query/{job_id}/stream`.\n\n"
        "For the full pipeline with rationale (20-30s), use `POST /advisor/chat` instead — "
        "it handles all intents (recommend, performance, overlap, etc.).\n\n"
        "**Auth:** API keys (`X-API-Key`), K8s ServiceAccount bearer tokens, or OAuth."
    ),
    response_model=RecommendationLowResponse | RecommendationMediumResponse,
    responses={
        200: {
            "description": "Low effort: inline results. Medium effort: job_id for polling.",
            "content": {
                "application/json": {
                    "examples": {
                        "low_effort": {
                            "summary": "Low effort — inline results",
                            "value": {
                                "candidates": [
                                    {
                                        "content_id": "babylon:ocp4-workshop.prod",
                                        "ci_name": "ocp4-workshop.prod",
                                        "display_name": "OpenShift 4 Workshop",
                                        "tier": "white",
                                        "relevance_score": None,
                                        "vector_similarity_pct": 82,
                                        "stage": "prod",
                                        "duration_min": 120,
                                    }
                                ],
                                "overall_assessment": None,
                                "metadata": {
                                    "effort": "low",
                                    "elapsed_s": 1.2,
                                    "total_candidates": 15,
                                    "returned": 10,
                                },
                            },
                        },
                        "medium_effort": {
                            "summary": "Medium effort — job_id for polling",
                            "value": {
                                "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
                            },
                        },
                    }
                }
            },
        },
        429: {"description": "Rate limit exceeded or query already running"},
        504: {"description": "Low-effort search timed out"},
    },
)
@limiter.limit(_recommendation_limit)
async def get_recommendations(
    body: RecommendationRequest, request: Request, user: str = Depends(require_auth),
):
    db = request.app.state.db
    settings: Settings = request.app.state.settings

    is_limited = not settings.is_curator(user) and not settings.is_admin(user)
    stages = list(body.stages)
    if "dev" in stages and is_limited:
        stages = [s for s in stages if s != "dev"]

    if body.effort == "low":
        return await _run_low(body, db, settings, stages)

    return await _run_medium(body, request, db, settings, stages, user, is_limited)


async def _run_low(body, db, settings, stages):
    t0 = time.monotonic()
    try:
        state = await asyncio.wait_for(
            run_query(
                query=body.query, db=db, settings=settings,
                stages=stages, include_zt=body.include_zt, depth="low",
            ),
            timeout=LOW_EFFORT_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Recommendation search timed out. Retry with effort=medium.")
    candidates_json = candidates_with_performance(state, db)[:body.limit]
    elapsed = round(time.monotonic() - t0, 2)
    return {
        "candidates": candidates_json,
        "overall_assessment": state.overall_assessment,
        "metadata": {
            "effort": "low",
            "elapsed_s": elapsed,
            "total_candidates": len(state.candidates),
            "returned": len(candidates_json),
        },
    }


async def _run_medium(body, request, db, settings, stages, user, is_limited):
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="recommend", queue="recommend", created_by=user, limit_active=is_limited)
    if job_id is None:
        raise HTTPException(status_code=429, detail="You already have a query running. Please wait for it to complete.")
    try:
        await arq_redis.enqueue_job(
            "run_recommendation",
            job_id=job_id,
            query=body.query,
            stages=stages,
            depth="medium",
            include_zt=body.include_zt,
            user_email=user,
            _queue_name="arq:queue:recommend",
        )
    except Exception:
        logger.error("enqueue_failed", job_id=job_id, action="enqueue_failed")
        db.fail_job(job_id, error="Failed to enqueue recommendation job")
        raise HTTPException(status_code=503, detail="Job queue unavailable. Please retry.")
    return {"job_id": job_id}
