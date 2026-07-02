"""Phase 3 — per-candidate Sonnet rationale + Haiku content gap synthesis."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from rcars.services.analyzer import parse_analysis_response
from rcars.db import Database
from rcars.services.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)

SINGLE_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "rationale_single.txt"
SYNTHESIS_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "rationale_synthesis.txt"


def _format_single_candidate(c: Candidate, analysis: dict[str, Any]) -> str:
    """Format one candidate with full analysis data for the per-candidate prompt."""
    lines = [
        f"CI Name: {c.ci_name}",
        f"Display Name: {c.display_name}",
        f"Category: {c.category}",
        f"Content Type: {c.content_type}",
        f"Relevance Score: {c.relevance_score or 0}%",
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

    return "\n".join(lines)


def _call_rationale_single(
    c: Candidate, analysis: dict[str, Any], query: str, settings, model: str,
) -> dict:
    """Generate rationale for a single candidate. Returns the parsed result dict."""
    from rcars.config import call_llm

    template = SINGLE_PROMPT_PATH.read_text()
    candidate_text = _format_single_candidate(c, analysis)

    data_start = template.index("\n## Request\n")
    instructions_start = template.index("\n## Instructions\n")
    system_prompt = template[:data_start].strip() + "\n\n" + template[instructions_start:].strip()
    user_message = f"## Request\n\n{query}\n\n## Candidate\n\n{candidate_text}"

    llm_result = call_llm(settings, model=model, messages=[{"role": "user", "content": user_message}], max_tokens=2048, system=system_prompt)

    result = parse_analysis_response(llm_result.text)
    if result is None:
        log.warning("rationale_single: failed to parse response for %s", c.ci_name)
        return {"ci_name": c.ci_name, "tokens": {"input": llm_result.input_tokens, "output": llm_result.output_tokens, "provider": llm_result.provider}}

    if isinstance(result, list) and result:
        result = result[0]

    result["ci_name"] = c.ci_name
    result["tokens"] = {"input": llm_result.input_tokens, "output": llm_result.output_tokens, "provider": llm_result.provider}
    return result


def _build_deterministic_assessment(candidates: list[Candidate], max_picks: int = 3) -> str:
    """Build overall_assessment deterministically from per-candidate Sonnet results."""
    with_rationale = [c for c in candidates if c.why_it_fits]
    if not with_rationale:
        picks = candidates[:max_picks]
        lines = [f"{c.display_name} ({c.relevance_score or 0}%) matched your query." for c in picks]
    else:
        lines = []
        for i, c in enumerate(with_rationale[:max_picks]):
            if i == 0:
                lines.append(f"{c.display_name} is the top pick because {c.why_it_fits}")
            else:
                lines.append(f"{c.display_name} fits because {c.why_it_fits}")
    return "\n".join(lines)


def _call_synthesis(
    query: str, candidates: list[Candidate], settings, model: str,
) -> dict:
    """Identify content gaps via Haiku synthesis."""
    from rcars.config import call_llm

    template = SYNTHESIS_PROMPT_PATH.read_text()

    lines = []
    for c in candidates:
        why = c.why_it_fits or ""
        lines.append(f"- {c.display_name} ({c.relevance_score or 0}%): {why}")
    recs_text = "\n".join(lines)

    data_start = template.index("\n## Request\n")
    instructions_start = template.index("\n## Instructions\n")
    system_prompt = template[:data_start].strip() + "\n\n" + template[instructions_start:].strip()
    user_message = f"## Request\n\n{query}\n\n## Recommendations (in score order, highest first)\n\n{recs_text}"

    llm_result = call_llm(settings, model=model, messages=[{"role": "user", "content": user_message}], max_tokens=1024, system=system_prompt)

    result = parse_analysis_response(llm_result.text)
    if result is None:
        log.warning("synthesis: failed to parse response")
        result = {}
    elif isinstance(result, list):
        result = result[0] if result else {}

    if "content_gaps" not in result:
        result["content_gaps"] = []

    result["tokens"] = {"input": llm_result.input_tokens, "output": llm_result.output_tokens, "provider": llm_result.provider}
    return result


def generate_content_gaps(
    query: str,
    candidates: list[Candidate],
    settings,
    model: str | None = None,
) -> tuple[list[str], dict]:
    """Run synthesis for content gaps only (no per-candidate rationale).

    Used when triage returns NO_MATCHES — we still want to tell the user
    what topics are missing from the catalog.
    """
    synthesis_model = model or settings.triage_model
    result = _call_synthesis(query, candidates, settings, synthesis_model)
    tokens = result.pop("tokens", {})
    return result.get("content_gaps", []), tokens


def generate_rationale(
    state: QueryState,
    db: Database,
    settings,
    model: str = "claude-sonnet-4-6",
    top_n: int = 5,
) -> QueryState:
    """Generate per-candidate Sonnet rationale + Haiku content gap synthesis.

    1. Fire parallel Sonnet calls for each of the top N candidates
    2. Apply results to candidates
    3. Build overall_assessment deterministically from per-candidate results
    4. Run a Haiku synthesis call for content_gaps only

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

    # Phase 3a: Parallel per-candidate Sonnet calls
    tokens_by_provider: dict[str, dict[str, int]] = {}
    rationale_results = {}

    with ThreadPoolExecutor(max_workers=min(top_n, 5)) as executor:
        futures = {}
        for c in top_candidates:
            analysis = analyses.get(c.ci_name, {})
            future = executor.submit(_call_rationale_single, c, analysis, state.query, settings, model)
            futures[future] = c.ci_name

        for future in as_completed(futures):
            ci_name = futures[future]
            try:
                result = future.result()
                tokens = result.pop("tokens", {})
                provider = tokens.get("provider", "unknown")
                bucket = tokens_by_provider.setdefault(provider, {"input": 0, "output": 0})
                bucket["input"] += tokens.get("input", 0)
                bucket["output"] += tokens.get("output", 0)
                rationale_results[ci_name] = result
            except Exception as e:
                log.error("rationale_single: failed for %s: %s", ci_name, e)

    # Apply rationale results to candidates
    for c in top_candidates:
        rec = rationale_results.get(c.ci_name, {})
        c.why_it_fits = rec.get("why_it_fits")
        c.how_to_use = rec.get("how_to_use")
        c.rationale = c.why_it_fits or rec.get("rationale")
        c.suggested_format = rec.get("suggested_format")
        c.duration_notes = rec.get("duration_notes")
        c.caveats = rec.get("caveats")

    matched = sum(1 for c in top_candidates if c.why_it_fits)
    if matched < len(top_candidates):
        missing = [c.ci_name for c in top_candidates if not c.why_it_fits]
        log.warning("rationale: %d/%d candidates missing why_it_fits", len(missing), len(top_candidates), missing=missing)

    rationale_elapsed = time.monotonic() - t0
    log.info("rationale: %d/%d candidates completed (%.1fs)", matched, len(top_candidates), rationale_elapsed)

    # Build overall_assessment deterministically from per-candidate results
    deterministic_assessment = _build_deterministic_assessment(top_candidates)

    # Phase 3b: Haiku synthesis for content_gaps only
    synthesis_model = settings.triage_model
    synthesis_result = _call_synthesis(state.query, top_candidates, settings, synthesis_model)
    synthesis_tokens = synthesis_result.pop("tokens", {})

    elapsed = time.monotonic() - t0
    log.info("synthesis: complete (%.1fs, model=%s)", time.monotonic() - t0 - rationale_elapsed, synthesis_model)

    token_entries = [
        {
            "operation": "rationale",
            "model": model,
            "input_tokens": bucket["input"],
            "output_tokens": bucket["output"],
            "provider": provider,
        }
        for provider, bucket in tokens_by_provider.items()
    ] + [
        {
            "operation": "synthesis",
            "model": synthesis_model,
            "input_tokens": synthesis_tokens.get("input", 0),
            "output_tokens": synthesis_tokens.get("output", 0),
            "provider": synthesis_tokens.get("provider", "unknown"),
        },
    ]

    return QueryState(
        phase="COMPLETE",
        candidates=top_candidates + remaining,
        query=state.query,
        overall_assessment=deterministic_assessment,
        content_gaps=synthesis_result.get("content_gaps"),
        timings={**state.timings, "rationale": round(elapsed, 3)},
        token_usage=[*state.token_usage, *token_entries],
    )
