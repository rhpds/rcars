"""Three-phase recommendation pipeline with async progress callbacks."""

from __future__ import annotations

import time
from typing import Callable, Awaitable

from rcars.db import Database
from rcars.config import Settings
from rcars.services.recommender.models import QueryState
from rcars.services.recommender.vector_search import search
from rcars.services.recommender.triage import triage
from rcars.services.recommender.rationale import generate_rationale
import structlog

logger = structlog.get_logger()


async def run_query(
    query: str,
    db: Database,
    anthropic_client,
    settings: Settings,
    prod_only: bool = True,
    on_progress: Callable[[dict], Awaitable[None]] | None = None,
) -> QueryState:
    async def emit(data: dict):
        if on_progress:
            await on_progress(data)

    t0 = time.monotonic()

    # Phase 1: Vector search
    await emit({"phase": "vector_search", "status": "started"})
    state = search(query, db, distance_cutoff=settings.vector_cutoff, prod_only=prod_only)
    await emit({"phase": "vector_search", "status": "complete", "candidates": len(state.candidates)})

    if state.phase == "NO_MATCHES":
        await emit({"phase": "complete", "results": 0})
        return state

    # Phase 2: Triage
    await emit({"phase": "triage", "status": "started", "total": len(state.candidates)})
    state = triage(state, anthropic_client, model=settings.triage_model, triage_cutoff=settings.triage_cutoff)
    relevant = len([c for c in state.candidates if c.tier in ("yellow", "green")])
    db.log_token_usage("triage", settings.triage_model, state.token_usage[-1]["input_tokens"], state.token_usage[-1]["output_tokens"], query_text=query) if state.token_usage else None
    await emit({"phase": "triage", "status": "complete", "relevant": relevant})

    if state.phase == "NO_MATCHES":
        await emit({"phase": "complete", "results": 0})
        return state

    # Phase 3: Rationale
    top_n = settings.rationale_top_n
    await emit({"phase": "rationale", "status": "started", "top_n": top_n})
    state = generate_rationale(state, db, anthropic_client, model=settings.rationale_model, top_n=top_n)
    green_count = len([c for c in state.candidates if c.tier == "green"])
    db.log_token_usage("rationale", settings.rationale_model, state.token_usage[-1]["input_tokens"], state.token_usage[-1]["output_tokens"], query_text=query) if len(state.token_usage) > 1 else None
    await emit({"phase": "complete", "results": green_count})

    elapsed = round(time.monotonic() - t0, 2)
    logger.info("pipeline_complete", action="pipeline_complete", elapsed_s=elapsed, green=green_count, total=len(state.candidates))
    return state
