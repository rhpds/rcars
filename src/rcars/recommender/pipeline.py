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

    # Phase 2: Haiku triage
    state = triage_phase(
        state=state,
        anthropic_client=anthropic_client,
        model=settings.triage_model,
        triage_cutoff=settings.triage_cutoff,
    )
    yield state

    if state.phase == "NO_MATCHES":
        # Triage was called — persist its token usage even though no matches survived
        for entry in state.token_usage:
            db.log_token_usage(query_text=state.query[:200], **entry)
        return

    # Phase 3: Sonnet rationale
    state = generate_rationale(
        state=state,
        db=db,
        anthropic_client=anthropic_client,
        model=settings.rationale_model,
        top_n=settings.rationale_top_n,
    )
    yield state

    # Write query token usage to DB
    for entry in state.token_usage:
        db.log_token_usage(
            query_text=state.query[:200],
            **entry,
        )
