"""Advisor routes — recommendation queries, sessions, selections."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from rcars.api.middleware.auth import require_auth
from rcars.api.streaming import JobProgressRelay, create_sse_response

router = APIRouter(prefix="/advisor")


class QueryRequest(BaseModel):
    query: str
    event_url: str | None = None
    prod_only: bool = True
    opted_out: bool = False


class SelectRequest(BaseModel):
    turn_index: int
    ci_name: str


@router.post("/query")
async def submit_query(body: QueryRequest, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis

    job_id = db.create_job(job_type="recommend", queue="recommend", created_by=user)
    await arq_redis.enqueue_job(
        "run_recommendation",
        job_id=job_id,
        query=body.query,
        prod_only=body.prod_only,
        user_email=user,
        opted_out=body.opted_out,
        _queue_name="arq:queue:recommend",
    )
    return {"job_id": job_id}


@router.get("/query/{job_id}/stream")
async def stream_query(job_id: str, request: Request, user: str = Depends(require_auth)):
    relay = JobProgressRelay(request.app.state.redis)
    return create_sse_response(relay, job_id)


@router.get("/query/{job_id}/result")
async def get_query_result(job_id: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "status": job["status"],
        "result": job.get("result_json"),
        "error": job.get("error"),
    }


@router.get("/sessions")
async def list_sessions(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    sessions = db.list_advisor_sessions(user_email=user)
    return {"items": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    turns = db.get_advisor_session(session_id)
    if not turns:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "turns": turns}


@router.post("/sessions/{session_id}/select")
async def select_recommendation(
    session_id: str, body: SelectRequest, request: Request, user: str = Depends(require_auth)
):
    db = request.app.state.db
    db.update_advisor_session_choice(
        session_id=session_id,
        turn_index=body.turn_index,
        chosen_ci_name=body.ci_name,
    )
    return {"status": "ok"}
