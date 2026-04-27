"""Three-phase recommendation pipeline with async progress callbacks."""

from __future__ import annotations

import re
import time
from typing import Callable, Awaitable

from rcars.db import Database
from rcars.config import Settings
from rcars.services.recommender.models import Candidate, QueryState
from rcars.services.recommender.vector_search import search
from rcars.services.recommender.triage import triage
from rcars.services.recommender.rationale import generate_rationale
import structlog

logger = structlog.get_logger()


def _extract_duration_target(query: str) -> tuple[int | None, bool]:
    """Extract a duration target (minutes) and whether it's a hard constraint."""
    hard_keywords = ("hard limit", "strict", "maximum", "no more than", "at most", "cannot exceed", "must be under")
    is_hard = any(k in query.lower() for k in hard_keywords)

    patterns = [
        r'(\d+)\s*[-–]?\s*hour',
        r'(\d+)\s*[-–]?\s*min',
        r'(\d+)\s*[-–]?\s*hr',
    ]
    for pat in patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 'min' in pat:
                return val, is_hard
            return val * 60, is_hard
    return None, is_hard


def _apply_duration_penalty(candidates: list[Candidate], target_min: int, hard: bool) -> None:
    """Apply a soft score penalty based on duration overshoot.

    Gentle: a 2x overshoot loses ~15% (soft) or ~25% (hard).
    This reorders but doesn't remove candidates from contention.
    """
    for c in candidates:
        if c.relevance_score is None or c.duration_min is None:
            continue
        if c.duration_min <= target_min:
            continue
        ratio = c.duration_min / target_min
        # Soft: 1 - 0.08 * ln(ratio), capped at 0.7
        # Hard: 1 - 0.15 * ln(ratio), capped at 0.6
        import math
        coeff = 0.15 if hard else 0.08
        floor = 0.6 if hard else 0.7
        multiplier = max(floor, 1.0 - coeff * math.log(ratio))
        old_score = c.relevance_score
        c.relevance_score = round(old_score * multiplier)
        logger.debug("duration_penalty", ci_name=c.ci_name,
                     duration=c.duration_min, target=target_min,
                     ratio=round(ratio, 1), multiplier=round(multiplier, 2),
                     old_score=old_score, new_score=c.relevance_score)


async def run_query(
    query: str,
    db: Database,
    anthropic_client,
    settings: Settings,
    prod_only: bool = True,
    include_zt: bool = True,
    on_progress: Callable[[dict], Awaitable[None]] | None = None,
) -> QueryState:
    async def emit(data: dict):
        if on_progress:
            await on_progress(data)

    t0 = time.monotonic()

    def serialize_candidates(candidates):
        return [
            {
                "ci_name": c.ci_name, "display_name": c.display_name, "tier": c.tier,
                "relevance_score": c.relevance_score, "vector_similarity_pct": c.vector_similarity_pct,
                "stage": c.stage, "catalog_namespace": c.catalog_namespace,
                "learning_objectives": c.learning_objectives,
                "why_it_fits": c.why_it_fits, "how_to_use": c.how_to_use,
                "suggested_format": c.suggested_format, "duration_notes": c.duration_notes,
                "caveats": c.caveats,
            }
            for c in candidates
        ]

    # Phase 1: Vector search
    await emit({"phase": "vector_search", "status": "started"})
    state = search(query, db, distance_cutoff=settings.vector_cutoff, prod_only=prod_only, include_zt=include_zt)
    await emit({"phase": "vector_search", "status": "complete", "candidates": len(state.candidates),
                "candidate_data": serialize_candidates(state.candidates)})

    if state.phase == "NO_MATCHES":
        await emit({"phase": "complete", "results": 0})
        return state

    # Phase 2: Triage
    await emit({"phase": "triage", "status": "started", "total": len(state.candidates)})
    state = triage(state, anthropic_client, model=settings.triage_model, triage_cutoff=settings.triage_cutoff)
    relevant = len([c for c in state.candidates if c.tier in ("yellow", "green")])
    db.log_token_usage("triage", settings.triage_model, state.token_usage[-1]["input_tokens"], state.token_usage[-1]["output_tokens"], query_text=query) if state.token_usage else None
    await emit({"phase": "triage", "status": "complete", "relevant": relevant,
                "candidate_data": serialize_candidates(state.candidates)})

    if state.phase == "NO_MATCHES":
        await emit({"phase": "complete", "results": 0})
        return state

    # Duration re-ranking (between triage and rationale)
    duration_target, is_hard = _extract_duration_target(query)
    if duration_target:
        _apply_duration_penalty(state.candidates, duration_target, is_hard)
        state.candidates.sort(key=lambda c: (
            0 if c.tier == "yellow" else 1,
            -(c.relevance_score or 0) if c.tier == "yellow" else -(c.vector_similarity_pct or 0),
        ))
        logger.info("duration_rerank", target=duration_target, hard=is_hard)

    # Phase 3: Rationale
    top_n = settings.rationale_top_n
    await emit({"phase": "rationale", "status": "started", "top_n": top_n})
    state = generate_rationale(state, db, anthropic_client, model=settings.rationale_model, top_n=top_n)

    # Promote candidates with full rationale to green tier
    for c in state.candidates:
        if c.why_it_fits and c.tier == "yellow":
            c.tier = "green"

    green_count = len([c for c in state.candidates if c.tier == "green"])
    db.log_token_usage("rationale", settings.rationale_model, state.token_usage[-1]["input_tokens"], state.token_usage[-1]["output_tokens"], query_text=query) if len(state.token_usage) > 1 else None
    await emit({"phase": "complete", "results": green_count})

    elapsed = round(time.monotonic() - t0, 2)
    logger.info("pipeline_complete", action="pipeline_complete", elapsed_s=elapsed, green=green_count, total=len(state.candidates))
    return state
