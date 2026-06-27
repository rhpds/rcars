"""Phase 3 — Sonnet rationale generation for top candidates."""

import logging
import time
from pathlib import Path
from typing import Any

from rcars.services.analyzer import parse_analysis_response
from rcars.db import Database
from rcars.services.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)

RATIONALE_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "rationale.txt"


def format_rationale_candidates(
    candidates: list[Candidate],
    analyses: dict[str, dict[str, Any]],
) -> str:
    """Format candidates with full analysis data for the rationale prompt."""
    parts = []
    for i, c in enumerate(candidates, 1):
        analysis = analyses.get(c.ci_name, {})
        lines = [
            f"--- Candidate {i} (relevance: {c.relevance_score or 0}%) ---",
            f"CI Name: {c.ci_name}",
            f"Display Name: {c.display_name}",
            f"Category: {c.category}",
            f"Content Type: {c.content_type}",
            f"Summary: {c.summary}",
            f"Difficulty: {c.difficulty}",
            f"Duration: {c.duration_min or '?'} min",
            f"Topics: {', '.join(c.topics)}",
            f"Products: {', '.join(c.products)}",
        ]

        audience = analysis.get("audience_json", [])
        if audience:
            lines.append(f"Audience: {', '.join(audience)}")

        objectives = analysis.get("learning_objectives_json", {})
        if isinstance(objectives, dict):
            stated = objectives.get("stated", [])
            inferred = objectives.get("inferred", [])
            if stated:
                lines.append(f"Stated Objectives: {'; '.join(stated)}")
            if inferred:
                lines.append(f"Inferred Objectives: {'; '.join(inferred)}")

        modules = analysis.get("modules_json", [])
        if modules:
            mod_titles = [m.get("title", "") for m in modules if m.get("title")]
            if mod_titles:
                lines.append(f"Modules: {'; '.join(mod_titles)}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def generate_rationale(
    state: QueryState,
    db: Database,
    settings,
    model: str = "claude-sonnet-4-6",
    top_n: int = 5,
) -> QueryState:
    """Generate Sonnet rationale for top candidates.

    Only the top_n candidates (by relevance_score) are sent to Sonnet.
    All candidates are preserved in the result — non-top-n keep their
    triage data but get no rationale.

    Returns QueryState with phase COMPLETE.
    """
    t0 = time.monotonic()

    top_candidates = state.candidates[:top_n]
    remaining = state.candidates[top_n:]

    # Fetch full analysis for top candidates (published CIs store analysis on their base CI)
    analyses = {}
    for c in top_candidates:
        analysis_ci = c.base_ci_name or c.ci_name
        analysis = db.get_showroom_analysis(analysis_ci)
        if analysis:
            analyses[c.ci_name] = analysis

    template = RATIONALE_PROMPT_PATH.read_text()
    candidates_text = format_rationale_candidates(top_candidates, analyses)

    # Separate system instructions from user-supplied data (security: M-1/M-4)
    data_start = template.index("\n## Request\n")
    instructions_start = template.index("\n## Instructions\n")
    system_prompt = template[:data_start].strip() + "\n\n" + template[instructions_start:].strip()
    user_message = f"## Request\n\n{state.query}\n\n## Candidates\n\n{candidates_text}"

    from rcars.config import call_llm
    llm_result = call_llm(settings, model=model, messages=[{"role": "user", "content": user_message}], max_tokens=8192, system=system_prompt)

    result = parse_analysis_response(llm_result.text)

    if result is None:
        log.error("rationale: failed to parse LLM response, raw=%s", llm_result.text[:500])

    # Build lookup by ci_name — handle both list (truncation recovery) and dict
    if isinstance(result, list):
        recs_by_ci = {r["ci_name"]: r for r in result if isinstance(r, dict) and "ci_name" in r}
    elif isinstance(result, dict) and "recommendations" in result:
        recs_by_ci = {r["ci_name"]: r for r in result["recommendations"] if isinstance(r, dict) and "ci_name" in r}
    else:
        if result is not None:
            log.warning("rationale: unexpected result type=%s, keys=%s", type(result).__name__,
                        list(result.keys()) if isinstance(result, dict) else "N/A")
        recs_by_ci = {}

    expected_names = {c.ci_name for c in top_candidates}
    returned_names = set(recs_by_ci.keys())
    missing = expected_names - returned_names
    extra = returned_names - expected_names
    if missing:
        log.warning("rationale: LLM dropped candidates", missing=sorted(missing))
    if extra:
        log.warning("rationale: LLM returned unexpected ci_names", extra=sorted(extra),
                     expected=sorted(expected_names))
        # Try fuzzy match: LLM may have truncated ".prod"/".dev" suffix
        for extra_name in extra:
            for c in top_candidates:
                if c.ci_name.startswith(extra_name) or extra_name.startswith(c.ci_name):
                    log.info("rationale: fuzzy match %s → %s", extra_name, c.ci_name)
                    recs_by_ci[c.ci_name] = recs_by_ci.pop(extra_name)
                    break

    if recs_by_ci:
        for c in top_candidates:
            rec = recs_by_ci.get(c.ci_name, {})
            c.why_it_fits = rec.get("why_it_fits")
            c.how_to_use = rec.get("how_to_use")
            c.rationale = c.why_it_fits or rec.get("rationale")
            c.suggested_format = rec.get("suggested_format")
            c.duration_notes = rec.get("duration_notes")
            c.caveats = rec.get("caveats")

    elapsed = time.monotonic() - t0

    log.info(
        "rationale: generated for %d candidates (elapsed=%.3fs)",
        len(top_candidates), elapsed,
    )

    new_token_entry = {
        "operation": "rationale",
        "model": model,
        "input_tokens": llm_result.input_tokens,
        "output_tokens": llm_result.output_tokens,
        "provider": llm_result.provider,
    }

    return QueryState(
        phase="COMPLETE",
        candidates=top_candidates + remaining,
        query=state.query,
        overall_assessment=result.get("overall_assessment") if isinstance(result, dict) else None,
        content_gaps=result.get("content_gaps") if isinstance(result, dict) else None,
        timings={**state.timings, "rationale": round(elapsed, 3)},
        token_usage=[*state.token_usage, new_token_entry],
    )
