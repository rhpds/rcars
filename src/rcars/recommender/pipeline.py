"""Three-phase recommendation pipeline orchestrator."""

import logging
from collections.abc import Generator

from rcars.config import Settings
from rcars.db import Database
from rcars.recommender.models import QueryState
from rcars.recommender.vector_search import search as vector_search
from rcars.recommender.triage import triage as triage_phase
from rcars.recommender.rationale import generate_rationale

log = logging.getLogger(__name__)


def run_query(
    query: str,
    db: Database,
    anthropic_client,
    settings: Settings,
    prod_only: bool = True,
) -> Generator[QueryState, None, None]:
    """Run the three-phase recommendation pipeline.

    Yields QueryState after each phase completes:
    1. VECTOR_DONE — candidates from pgvector with distance cutoff
    2. TRIAGE_DONE — candidates scored and filtered by Haiku
    3. COMPLETE — top candidates enriched with Sonnet rationale

    Stops early with NO_MATCHES if any phase produces zero candidates.
    """
    # Phase 1: Vector search
    state = vector_search(
        query=query,
        db=db,
        limit=10,
        prod_only=prod_only,
        distance_cutoff=settings.vector_cutoff,
    )
    yield state

    if state.phase == "NO_MATCHES":
        return

    # Phase 2: Haiku triage — annotates all candidates with tier, returns full list
    state = triage_phase(
        state=state,
        anthropic_client=anthropic_client,
        model=settings.triage_model,
        triage_cutoff=settings.triage_cutoff,
    )
    yield state

    if state.phase == "NO_MATCHES":
        # Triage ran but found nothing relevant — persist token usage and stop
        for entry in state.token_usage:
            db.log_token_usage(query_text=state.query[:200], **entry)
        return

    # Phase 3: Sonnet rationale — only on yellow (relevant) candidates to control cost
    all_candidates = state.candidates
    yellow_candidates = [c for c in all_candidates if c.tier == "yellow"]

    yellow_state = QueryState(
        phase=state.phase,
        candidates=yellow_candidates,
        query=state.query,
        timings=state.timings,
        token_usage=state.token_usage,
    )

    rationale_state = generate_rationale(
        state=yellow_state,
        db=db,
        anthropic_client=anthropic_client,
        model=settings.rationale_model,
        top_n=settings.rationale_top_n,
    )

    # Promote candidates that received a Sonnet rationale to green
    for c in rationale_state.candidates:
        if c.rationale:
            c.tier = "green"

    # Rebuild full list: green → remaining yellow → white
    green = [c for c in rationale_state.candidates if c.tier == "green"]
    remaining_yellow = [c for c in rationale_state.candidates if c.tier == "yellow"]
    white = [c for c in all_candidates if c.tier == "white"]

    final_state = QueryState(
        phase=rationale_state.phase,
        candidates=green + remaining_yellow + white,
        query=rationale_state.query,
        overall_assessment=rationale_state.overall_assessment,
        content_gaps=rationale_state.content_gaps,
        timings=rationale_state.timings,
        token_usage=rationale_state.token_usage,
    )
    yield final_state

    # Write query token usage to DB
    for entry in final_state.token_usage:
        db.log_token_usage(
            query_text=final_state.query[:200],
            **entry,
        )
