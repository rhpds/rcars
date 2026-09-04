"""Advisor routes — recommendation queries, sessions, selections."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from rcars.api.middleware.auth import require_auth, require_admin
from rcars.api.middleware.rate_limit import limiter
from rcars.api.schemas import (
    QuerySubmitResponse, QueryResultResponse, ChatSubmitResponse,
    SessionListResponse, SessionDetailResponse, StatusResponse,
)
from rcars.api.streaming import JobProgressRelay, create_sse_response
from rcars.config import Settings
from rcars.db import chat_sessions

router = APIRouter(prefix="/advisor")


class QueryRequest(BaseModel):
    query: str = Field(max_length=2000)
    event_url: str | None = None
    stages: list[str] = ["prod"]
    include_zt: bool = True
    depth: Literal["low", "medium", "high"] = "high"


class SelectRequest(BaseModel):
    turn_index: int
    ci_name: str | None = None
    content_id: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(max_length=2000, description="Natural-language message. Always required — used for logging even when routed is set.")
    session_id: str | None = Field(default=None, description="Pass back from a previous response to maintain conversation context")
    stages: list[str] = Field(default=["prod"], description="Lifecycle stages to search: prod, event, dev")
    include_zt: bool = Field(default=True, description="Include zero-touch (fully automated) items in results")
    routed: dict | None = Field(
        default=None,
        description=(
            "Optional. Skip the intent router and go directly to a handler. "
            "If omitted, the LLM router classifies the message automatically. "
            "Intents: recommend, overlap, performance, item_facts, infrastructure."
        ),
        json_schema_extra={
            "examples": [
                None,
                {"intent": "recommend", "args": {"search_query": "OpenShift AI demos"}},
            ]
        },
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Find labs about OpenShift AI",
                    "stages": ["prod"],
                    "include_zt": True,
                },
                {
                    "message": "OpenShift AI demos for beginners",
                    "routed": {"intent": "recommend", "args": {"search_query": "OpenShift AI demos for beginners"}},
                },
                {
                    "message": "How is the OpenShift Virtualization Roadshow performing?",
                    "routed": {"intent": "performance", "args": {"window": "6m"}, "item_refs": ["Experience OpenShift Virtualization Roadshow"]},
                },
                {
                    "message": "Tell me about the OpenShift AI workshop",
                    "routed": {"intent": "item_facts", "args": {"item_ref": "Hands-on with Red Hat OpenShift AI"}},
                },
            ]
        }
    }


def _advisor_limit() -> str:
    import os
    return f"{os.environ.get('RCARS_ADVISOR_RATE_LIMIT_PER_USER_PER_HOUR', '50')}/hour"


@router.post(
    "/query",
    summary="[Deprecated] Submit a recommendation query",
    description=(
        "**Deprecated — use `POST /advisor/chat` instead.** This endpoint will be removed in a future release.\n\n"
        "Submits a natural-language query for content recommendations using the legacy single-intent pipeline. "
        "Always runs the recommend flow (vector search → triage → rationale). "
        "Does not support multi-intent routing (performance, overlap, infrastructure, help).\n\n"
        "Returns a `job_id`. Use `GET /advisor/query/{job_id}/stream` for real-time SSE updates "
        "or `GET /advisor/query/{job_id}/result` to poll for completion. "
        "Rate-limited per user (default: 50/hour)."
    ),
    response_model=QuerySubmitResponse,
    responses={429: {"description": "Rate limit exceeded or query already running"}},
    deprecated=True,
)
@limiter.limit(_advisor_limit)
async def submit_query(body: QueryRequest, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    settings: Settings = request.app.state.settings

    is_limited = not settings.is_curator(user) and not settings.is_admin(user)

    stages = body.stages
    if "dev" in stages and is_limited:
        stages = [s for s in stages if s != "dev"]

    job_id = db.create_job(job_type="recommend", queue="recommend", created_by=user, limit_active=is_limited)
    if job_id is None:
        raise HTTPException(status_code=429, detail="You already have a query running. Please wait for it to complete.")
    await arq_redis.enqueue_job(
        "run_recommendation",
        job_id=job_id,
        query=body.query,
        stages=stages,
        depth=body.depth,
        include_zt=body.include_zt,
        user_email=user,
        _queue_name="arq:queue:recommend",
    )
    return {"job_id": job_id}


@router.post(
    "/chat",
    summary="Submit a chat message",
    description=(
        "The primary advisor endpoint. Routes a natural-language message to a deterministic intent handler "
        "based on LLM classification.\n\n"
        "Returns a `job_id` and `session_id`. Use `GET /advisor/query/{job_id}/stream` for real-time SSE updates "
        "or `GET /advisor/query/{job_id}/result` to poll. Pass the `session_id` back on subsequent messages "
        "to maintain conversation context.\n\n"
        "## Intents\n\n"
        "When `routed` is omitted, the LLM router classifies the message automatically. "
        "To bypass the router, pass `routed` with the intent and args shown below.\n\n"
        "### recommend\n"
        "Find content for a topic, event, or audience.\n"
        "```json\n"
        '{"intent": "recommend", "args": {"search_query": "OpenShift AI demos for beginners"}}\n'
        "```\n"
        "`args.search_query` (required): the search text. "
        "`args.constraints` (optional): `{\"performance\": \"high_usage\"}` or `{\"duration\": \"2 hours\"}`.\n\n"
        "### performance\n"
        "Usage, cost, and sales metrics for specific items.\n"
        "```json\n"
        '{"intent": "performance", "args": {"window": "6m"}, "item_refs": ["Experience OpenShift Virtualization Roadshow"]}\n'
        "```\n"
        "`item_refs` (required, **top-level**): display names of items to look up. "
        "`args.window` (optional): `3m`, `6m`, `9m`, or `12m` (default `6m`). "
        "Performance is the only intent that requires top-level `item_refs`.\n\n"
        "### overlap\n"
        "Find content similar to a specific item.\n"
        "```json\n"
        '{"intent": "overlap", "args": {"item_ref": "Red Hat Enterprise Linux Workshop"}}\n'
        "```\n"
        "`args.item_ref` (required): display name of the item to compare.\n\n"
        "### item_facts\n"
        "Details about a specific catalog item (summary, modules, products).\n"
        "```json\n"
        '{"intent": "item_facts", "args": {"item_ref": "Hands-on with Red Hat OpenShift AI"}}\n'
        "```\n"
        "`args.item_ref` (required): display name of the item.\n\n"
        "### infrastructure\n"
        "Workload roles and base configs for a technology.\n"
        "```json\n"
        '{"intent": "infrastructure", "args": {"search_query": "OpenShift AI"}}\n'
        "```\n"
        "`args.search_query` (required): technology or workload to look up.\n\n"
        "**Note:** Use display names for items, not CI names like `my-demo.prod`. "
        "The resolver matches references to catalog items.\n\n"
        "Rate-limited per user (default: 50/hour, shared with the deprecated /query endpoint)."
    ),
    response_model=ChatSubmitResponse,
    responses={404: {"description": "session_id not found or not owned by user"},
               429: {"description": "Rate limit exceeded or query already running"}},
)
@limiter.limit(_advisor_limit)
async def submit_chat(body: ChatRequest, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    settings: Settings = request.app.state.settings

    is_admin = settings.is_admin(user)
    session_id = body.session_id
    if session_id:
        if not chat_sessions.session_owner_ok(db.pool, session_id, user, is_admin=is_admin):
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session_id = str(uuid.uuid4())

    is_limited = not settings.is_curator(user) and not is_admin

    stages = body.stages
    if "dev" in stages and is_limited:
        stages = [s for s in stages if s != "dev"]

    job_id = db.create_job(job_type="chat", queue="recommend", created_by=user, limit_active=is_limited)
    if job_id is None:
        raise HTTPException(status_code=429, detail="You already have a query running. Please wait for it to complete.")
    await arq_redis.enqueue_job(
        "run_chat_turn", job_id=job_id, message=body.message, session_id=session_id,
        stages=stages, include_zt=body.include_zt, user_email=user, is_admin=is_admin,
        routed=body.routed,
        _queue_name="arq:queue:recommend")
    return {"job_id": job_id, "session_id": session_id}


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
    return create_sse_response(relay, job_id, job_status=job["status"])


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
    # Derive content_id from ci_name if not provided
    content_id = body.content_id
    if not content_id and body.ci_name:
        content_id = f"babylon:{body.ci_name}"
    db.update_advisor_session_choice(
        session_id=session_id,
        turn_index=body.turn_index,
        chosen_ci_name=body.ci_name,
        chosen_content_id=content_id,
        user_email=user,
    )
    return {"status": "ok"}
