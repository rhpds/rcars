"""Advisor routes — recommendation queries, sessions, selections."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from rcars.api.middleware.auth import require_auth, require_admin
from rcars.api.middleware.rate_limit import limiter
from rcars.api.schemas import (
    QuerySubmitResponse, QueryResultResponse,
    SessionListResponse, SessionDetailResponse, StatusResponse,
)
from rcars.api.streaming import JobProgressRelay, create_sse_response
from rcars.config import Settings

router = APIRouter(prefix="/advisor")


class QueryRequest(BaseModel):
    query: str = Field(max_length=2000)
    event_url: str | None = None
    stages: list[str] = ["prod"]
    include_zt: bool = True
    opted_out: bool = False


class SelectRequest(BaseModel):
    turn_index: int
    ci_name: str


def _advisor_limit() -> str:
    import os
    return f"{os.environ.get('RCARS_ADVISOR_RATE_LIMIT_PER_USER_PER_HOUR', '50')}/hour"


@router.post(
    "/query",
    summary="Submit a recommendation query",
    description=(
        "Submits a natural-language query for content recommendations. "
        "Returns a job_id for tracking progress. Use the stream endpoint for real-time SSE updates "
        "or the result endpoint to poll for completion. "
        "Rate-limited per user (default: 50/hour)."
    ),
    response_model=QuerySubmitResponse,
    responses={429: {"description": "Rate limit exceeded or query already running"}},
)
@limiter.limit(_advisor_limit)
async def submit_query(body: QueryRequest, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    settings: Settings = request.app.state.settings

    if not settings.is_curator(user) and not settings.is_admin(user):
        if db.has_active_recommend_job(user):
            raise HTTPException(status_code=429, detail="You already have a query running. Please wait for it to complete.")

    stages = body.stages
    if "dev" in stages and not settings.is_curator(user) and not settings.is_admin(user):
        stages = [s for s in stages if s != "dev"]

    job_id = db.create_job(job_type="recommend", queue="recommend", created_by=user)
    await arq_redis.enqueue_job(
        "run_recommendation",
        job_id=job_id,
        query=body.query,
        stages=stages,
        include_zt=body.include_zt,
        user_email=user,
        opted_out=body.opted_out,
        _queue_name="arq:queue:recommend",
    )
    return {"job_id": job_id}


@router.get(
    "/query/{job_id}/stream",
    summary="Stream query progress (SSE)",
    description=(
        "Server-Sent Events stream for real-time recommendation progress. "
        "Events include: triage results, rationale generation, and final recommendations. "
        "Connect with EventSource in the browser or any SSE client."
    ),
    responses={404: {"description": "Job not found or not owned by user"}},
)
async def stream_query(job_id: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    settings: Settings = request.app.state.settings
    job = db.get_job(job_id)
    if not job or (job["created_by"] != user and not settings.is_admin(user)):
        raise HTTPException(status_code=404, detail="Job not found")
    relay = JobProgressRelay(request.app.state.redis)
    return create_sse_response(relay, job_id)


@router.get(
    "/query/{job_id}/result",
    summary="Get query result",
    description="Returns the recommendation result for a completed job, or current status if still running.",
    response_model=QueryResultResponse,
    responses={404: {"description": "Job not found or not owned by user"}},
)
async def get_query_result(job_id: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    settings: Settings = request.app.state.settings
    job = db.get_job(job_id)
    if not job or (job["created_by"] != user and not settings.is_admin(user)):
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "status": job["status"],
        "result": job.get("result_json"),
        "error": job.get("error"),
    }


@router.get(
    "/sessions",
    summary="List recommendation sessions",
    description="Returns the authenticated user's past recommendation query sessions, newest first.",
    response_model=SessionListResponse,
)
async def list_sessions(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    sessions = db.list_advisor_sessions(user_email=user)
    for s in sessions:
        if s.get("started_at") and not isinstance(s["started_at"], str):
            s["started_at"] = str(s["started_at"])
    return {"items": sessions, "total": len(sessions)}


@router.get(
    "/sessions/{session_id}",
    summary="Get session details",
    description="Returns all turns (queries and results) for a specific recommendation session.",
    response_model=SessionDetailResponse,
    responses={404: {"description": "Session not found or not owned by user"}},
)
async def get_session(session_id: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    turns = db.get_advisor_session(session_id, user_email=user)
    if not turns:
        raise HTTPException(status_code=404, detail="Session not found")
    for t in turns:
        if t.get("created_at") and not isinstance(t["created_at"], str):
            t["created_at"] = str(t["created_at"])
    return {"session_id": session_id, "turns": turns}


@router.post(
    "/sessions/{session_id}/select",
    summary="Record recommendation selection",
    description="Records which catalog item the user selected from a recommendation turn. Used for feedback and analytics.",
    response_model=StatusResponse,
    responses={404: {"description": "Session not found or not owned by user"}},
)
async def select_recommendation(
    session_id: str, body: SelectRequest, request: Request, user: str = Depends(require_auth)
):
    db = request.app.state.db
    turns = db.get_advisor_session(session_id, user_email=user)
    if not turns:
        raise HTTPException(status_code=404, detail="Session not found")
    db.update_advisor_session_choice(
        session_id=session_id,
        turn_index=body.turn_index,
        chosen_ci_name=body.ci_name,
    )
    return {"status": "ok"}
