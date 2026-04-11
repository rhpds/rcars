"""Phase 3 — Sonnet rationale generation for top candidates."""

import json
import logging
import time
from pathlib import Path
from typing import Any

from rcars.analyzer import parse_analysis_response
from rcars.db import Database
from rcars.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)

RATIONALE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "rationale.txt"


def format_rationale_candidates(
    candidates: list[Candidate],
    analyses: dict[str, dict[str, Any]],
) -> str:
    """Format candidates with full analysis data for the rationale prompt."""
    parts = []
    for i, c in enumerate(candidates, 1):
        analysis = analyses.get(c.ci_name, {})
        lines = [
            f"--- Candidate {i} ---",
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

        event_fit = analysis.get("event_fit_json", {})
        if event_fit:
            lines.append(f"Event Fit: {json.dumps(event_fit)}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def generate_rationale(
    state: QueryState,
    db: Database,
    anthropic_client,
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

    # Fetch full analysis for top candidates
    analyses = {}
    for c in top_candidates:
        analysis = db.get_showroom_analysis(c.ci_name)
        if analysis:
            analyses[c.ci_name] = analysis

    template = RATIONALE_PROMPT_PATH.read_text()
    candidates_text = format_rationale_candidates(top_candidates, analyses)

    prompt = (
        template
        .replace("{request_description}", state.query)
        .replace("{candidates}", candidates_text)
    )

    response = anthropic_client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    result = parse_analysis_response(response.content[0].text)

    if result:
        recs_by_ci = {
            r["ci_name"]: r
            for r in result.get("recommendations", [])
        }
        for c in top_candidates:
            rec = recs_by_ci.get(c.ci_name, {})
            c.rationale = rec.get("rationale")
            c.suggested_format = rec.get("suggested_format")
            c.duration_notes = rec.get("duration_notes")
            c.caveats = rec.get("caveats")

    elapsed = time.monotonic() - t0

    log.info(
        "rationale: generated for %d candidates (elapsed=%.3fs)",
        len(top_candidates), elapsed,
    )

    return QueryState(
        phase="COMPLETE",
        candidates=top_candidates + remaining,
        query=state.query,
        overall_assessment=result.get("overall_assessment") if result else None,
        content_gaps=result.get("content_gaps") if result else None,
        timings={**state.timings, "rationale": round(elapsed, 3)},
    )
