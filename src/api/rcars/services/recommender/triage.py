"""Phase 2 — Haiku triage for relevance scoring."""

import logging
import time
from pathlib import Path

from rcars.services.analyzer import parse_analysis_response
from rcars.services.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)

TRIAGE_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "triage.txt"


def format_triage_candidates(candidates: list[Candidate]) -> str:
    """Format candidates compactly for the triage prompt."""
    parts = []
    for i, c in enumerate(candidates, 1):
        parts.append(
            f"--- Candidate {i} ---\n"
            f"CI Name: {c.ci_name}\n"
            f"Display Name: {c.display_name}\n"
            f"Summary: {c.summary}\n"
            f"Topics: {', '.join(c.topics)}\n"
            f"Products: {', '.join(c.products)}\n"
            f"Category: {c.category}\n"
            f"Content Type: {c.content_type}"
        )
    return "\n\n".join(parts)


def triage(
    state: QueryState,
    anthropic_client,
    model: str = "claude-haiku-4-5",
    triage_cutoff: int = 30,
) -> QueryState:
    """Send candidates to Haiku for relevance triage.

    Returns QueryState with phase TRIAGE_DONE or NO_MATCHES.
    Candidates below triage_cutoff or marked irrelevant are removed.
    Survivors are sorted by relevance_score descending.
    """
    t0 = time.monotonic()

    template = TRIAGE_PROMPT_PATH.read_text()
    candidates_text = format_triage_candidates(state.candidates)

    prompt = (
        template
        .replace("{request_description}", state.query)
        .replace("{candidates}", candidates_text)
    )

    response = anthropic_client.messages.create(
        model=model,
        max_tokens=2048,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text
    triage_results = parse_analysis_response(response_text)

    # Build lookup by ci_name
    if isinstance(triage_results, list):
        scores_by_ci = {r["ci_name"]: r for r in triage_results}
    elif isinstance(triage_results, dict) and "recommendations" in triage_results:
        scores_by_ci = {r["ci_name"]: r for r in triage_results["recommendations"]}
    else:
        scores_by_ci = {}

    annotated = []
    relevant_count = 0
    for candidate in state.candidates:
        score_data = scores_by_ci.get(candidate.ci_name)
        if not score_data:
            log.info("  triage: not scored %s — marking white", candidate.ci_name)
            annotated.append(candidate)
            continue

        relevance = score_data.get("relevance_score", 0)
        relevant = score_data.get("relevant", False)
        reason = score_data.get("one_line_reason", "")

        candidate.relevance_score = relevance
        candidate.one_line_reason = reason

        if relevant and relevance >= triage_cutoff:
            candidate.tier = "yellow"
            candidate.relevant = True
            relevant_count += 1
            log.info("  triage: yellow %s — score=%d (%s)", candidate.ci_name, relevance, reason)
        else:
            candidate.tier = "white"
            candidate.relevant = False
            log.info("  triage: white %s — score=%d relevant=%s (%s)",
                     candidate.ci_name, relevance, relevant, reason)

        annotated.append(candidate)

    # Sort: yellow first (by score desc), white last (by vector similarity desc)
    annotated.sort(key=lambda c: (
        0 if c.tier == "yellow" else 1,
        -(c.relevance_score or 0) if c.tier == "yellow" else -(c.vector_similarity_pct or 0),
    ))

    elapsed = time.monotonic() - t0
    phase = "TRIAGE_DONE" if relevant_count > 0 else "NO_MATCHES"

    log.info(
        "triage: %d/%d relevant, %d total returned (cutoff=%d, elapsed=%.3fs)",
        relevant_count, len(state.candidates), len(annotated), triage_cutoff, elapsed,
    )

    usage = getattr(response, "usage", None)
    new_token_entry = {
        "operation": "triage",
        "model": model,
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
    }

    return QueryState(
        phase=phase,
        candidates=annotated,
        query=state.query,
        timings={**state.timings, "triage": round(elapsed, 3)},
        token_usage=[*state.token_usage, new_token_entry],
    )
