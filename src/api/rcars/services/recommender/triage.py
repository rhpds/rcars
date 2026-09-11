"""Phase 2 — Haiku triage for relevance scoring."""

import time
from pathlib import Path

import structlog

from rcars.services.analyzer import parse_analysis_response
from rcars.services.recommender.models import Candidate, QueryState

log = structlog.get_logger()

TRIAGE_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "triage.txt"


def format_triage_candidates(candidates: list[Candidate]) -> str:
    """Format candidates compactly for the triage prompt."""
    parts = []
    for i, c in enumerate(candidates, 1):
        block = (
            f"--- Candidate {i} ---\n"
            f"Content ID: {c.content_id}\n"
            f"Content Type: {c.content_type}\n"
        )
        if c.ci_name:
            block += f"CI Name: {c.ci_name}\n"
        block += (
            f"Display Name: {c.display_name}\n"
            f"Summary: {c.summary}\n"
            f"Topics: {', '.join(c.topics)}\n"
            f"Products: {', '.join(c.products)}\n"
            f"Category: {c.category}\n"
            f"Duration: {c.duration_min or '?'} min"
        )
        parts.append(block)
    return "\n\n".join(parts)


def triage(
    state: QueryState,
    settings,
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

    # Separate system instructions from user-supplied data (security: M-1/M-4)
    data_start = template.index("\n## Request\n")
    instructions_start = template.index("\n## Instructions\n")
    system_prompt = template[:data_start].strip() + "\n\n" + template[instructions_start:].strip()
    user_message = f"## Request\n\n{state.query}\n\n## Candidates\n\n{candidates_text}"

    from rcars.config import call_llm
    result = call_llm(settings, model=model, messages=[{"role": "user", "content": user_message}], max_tokens=8192, system=system_prompt)

    response_text = result.text
    triage_results = parse_analysis_response(response_text)

    if triage_results is None:
        log.error("triage_parse_failed", raw=response_text[:500])

    scores_by_key: dict[str, dict] = {}
    if isinstance(triage_results, list):
        for r in triage_results:
            if isinstance(r, dict):
                if "content_id" in r:
                    scores_by_key[r["content_id"]] = r
                elif "ci_name" in r:
                    log.warning("triage_ci_name_fallback", ci_name=r["ci_name"])
                    scores_by_key[f"babylon:{r['ci_name']}"] = r
    elif isinstance(triage_results, dict) and "recommendations" in triage_results:
        for r in triage_results["recommendations"]:
            if isinstance(r, dict):
                if "content_id" in r:
                    scores_by_key[r["content_id"]] = r
                elif "ci_name" in r:
                    log.warning("triage_ci_name_fallback", ci_name=r["ci_name"])
                    scores_by_key[f"babylon:{r['ci_name']}"] = r
    else:
        log.warning("triage_unexpected_result",
                    result_type=type(triage_results).__name__,
                    keys=list(triage_results.keys()) if isinstance(triage_results, dict) else "N/A")

    annotated = []
    relevant_count = 0
    for candidate in state.candidates:
        score_data = scores_by_key.get(candidate.content_id)
        if not score_data:
            log.info("triage_not_scored", content_id=candidate.content_id, tier="white")
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
            log.info("triage_scored", content_id=candidate.content_id, tier="yellow", score=relevance, reason=reason)
        else:
            candidate.tier = "white"
            candidate.relevant = False
            log.info("triage_scored", content_id=candidate.content_id, tier="white",
                     score=relevance, relevant=relevant, reason=reason)

        annotated.append(candidate)

    # Sort: yellow first (by score desc), white last (by vector similarity desc)
    annotated.sort(key=lambda c: (
        0 if c.tier == "yellow" else 1,
        -(c.relevance_score or 0) if c.tier == "yellow" else -(c.vector_similarity_pct or 0),
    ))

    elapsed = time.monotonic() - t0
    phase = "TRIAGE_DONE" if relevant_count > 0 else "NO_MATCHES"

    log.info("triage_complete", relevant=relevant_count,
             candidates=len(state.candidates), returned=len(annotated),
             cutoff=triage_cutoff, elapsed=round(elapsed, 3))

    new_token_entry = {
        "operation": "triage",
        "model": model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "provider": result.provider,
    }

    return QueryState(
        phase=phase,
        candidates=annotated,
        query=state.query,
        timings={**state.timings, "triage": round(elapsed, 3)},
        token_usage=[*state.token_usage, new_token_entry],
    )
