"""Three-phase recommendation pipeline with async progress callbacks."""

from __future__ import annotations

import asyncio
import re
import time
from typing import Callable, Awaitable
from rcars.db import Database
from rcars.config import Settings
from rcars.services.recommender.models import Candidate, QueryState
from rcars.services.recommender.vector_search import search
from rcars.services.recommender.triage import triage
from rcars.services.recommender.rationale import generate_rationale
from rcars.services.event_parser import parse_event_url
import structlog

logger = structlog.get_logger()

NO_MATCH_GUIDANCE = (
    "I help with content recommendations, but I couldn't find a close match. "
    "Try broadening your query — focus on the core topic and technology rather "
    "than event names, lab numbers, or delivery constraints.\n\n"
    "I currently know about all RHDP items that have demo or lab guides."
)


_ACRONYMS = {
    "AAP": "Ansible Automation Platform",
    "ACM": "Advanced Cluster Management for Kubernetes",
    "RHACM": "Advanced Cluster Management for Kubernetes",
    "ACS": "Advanced Cluster Security for Kubernetes",
    "RHACS": "Red Hat Advanced Cluster Security for Kubernetes",
    "RHOAI": "Red Hat OpenShift AI",
    "OCP": "OpenShift Container Platform",
    "ARO": "Azure Red Hat OpenShift",
    "ROSA": "Red Hat OpenShift Service on AWS",
    "RHEL": "Red Hat Enterprise Linux",
    "RHDH": "Red Hat Developer Hub",
    "SNO": "Single Node OpenShift",
    "RHSSO": "Red Hat Single Sign-On",
    "EDA": "Event-Driven Ansible",
    "TAP": "Trusted Application Pipeline",
}

_ACRONYM_RE = re.compile(
    r'\b(' + '|'.join(sorted(_ACRONYMS, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)


def _expand_acronyms(query: str) -> str:
    """Expand Red Hat product acronyms to full names for better embedding match."""
    def _replace(m: re.Match) -> str:
        acro = m.group(0).upper()
        return f"{acro} ({_ACRONYMS[acro]})"
    return _ACRONYM_RE.sub(_replace, query)


_URL_RE = re.compile(r'(?:https?://\S+|www\.\S+\.\S+)', re.IGNORECASE)


def _extract_urls(query: str) -> tuple[list[str], str]:
    """Extract URLs from query, return (urls, remaining_text).

    Finds full URLs (http/https) and bare www. domains anywhere in the text.
    Bare domains get https:// prepended.
    """
    matches = _URL_RE.findall(query)
    urls = []
    for m in matches:
        url = m if m.lower().startswith("http") else f"https://{m}"
        url = url.rstrip(".,;:!?)")
        urls.append(url)
    remaining = _URL_RE.sub("", query).strip()
    remaining = " ".join(remaining.split())
    return urls, remaining


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
        if c.duration_source != "curated":
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
        c.relevance_score = max(0, min(100, round(old_score * multiplier)))
        logger.debug("duration_penalty", ci_name=c.ci_name,
                     duration=c.duration_min, target=target_min,
                     ratio=round(ratio, 1), multiplier=round(multiplier, 2),
                     old_score=old_score, new_score=c.relevance_score)


def _apply_usage_boost(candidates: list[Candidate], db) -> None:
    """Boost relevance scores for candidates with proven usage.

    Looks up provisions_quarter from reporting_metrics and applies a
    gentle multiplicative boost based on percentile rank among candidates
    with non-zero provisions. Max boost is 12% — enough to swap adjacent
    candidates but not enough to jump a tier.
    """
    import bisect
    from rcars.services.reporting_sync import extract_base_name

    for c in candidates:
        base = extract_base_name(c.ci_name)
        metrics = db.get_reporting_metrics(base)
        c.provisions_quarter = metrics["provisions_quarter"] if metrics else None

    prov_values = [c.provisions_quarter for c in candidates if c.provisions_quarter and c.provisions_quarter > 0]
    if not prov_values:
        return
    sorted_provs = sorted(prov_values)

    for c in candidates:
        if c.relevance_score is None or not c.provisions_quarter or c.provisions_quarter <= 0:
            continue
        pct = (bisect.bisect_right(sorted_provs, c.provisions_quarter) / len(sorted_provs)) * 100
        if pct >= 90:
            multiplier = 1.12
        elif pct >= 75:
            multiplier = 1.09
        elif pct >= 50:
            multiplier = 1.06
        else:
            multiplier = 1.03
        old_score = c.relevance_score
        c.relevance_score = max(0, min(100, round(old_score * multiplier)))
        logger.debug("usage_boost", ci_name=c.ci_name,
                     provisions_quarter=c.provisions_quarter, percentile=round(pct),
                     multiplier=multiplier, old_score=old_score, new_score=c.relevance_score)


async def run_query(
    query: str,
    db: Database,
    settings: Settings,
    stages: list[str] | None = None,
    include_zt: bool = True,
    on_progress: Callable[[dict], Awaitable[None]] | None = None,
) -> QueryState:
    async def emit(data: dict):
        if on_progress:
            await on_progress(data)

    t0 = time.monotonic()

    urls, remaining_text = _extract_urls(query)
    if urls:
        url = urls[0]
        logger.info("query_has_url", url=url[:200], has_text=bool(remaining_text))
        await emit({"phase": "event_parse", "status": "started", "url": url})
        try:
            event_profile = parse_event_url(url, settings=settings, model=settings.model)
        except Exception as e:
            logger.error("event_parse_failed", url=url[:200], error=str(e))
            event_profile = None
        if event_profile and event_profile.get("search_queries"):
            search_queries = event_profile["search_queries"]
            event_context = " ".join(search_queries)
            query = f"{remaining_text} {event_context}".strip() if remaining_text else event_context
            logger.info("event_parsed", event_name=event_profile.get("event_name"),
                         themes=event_profile.get("themes"), queries=search_queries)
            await emit({"phase": "event_parse", "status": "complete",
                         "event_name": event_profile.get("event_name"),
                         "search_queries": search_queries})
        elif not remaining_text:
            await emit({"phase": "complete", "results": 0})
            return QueryState(
                phase="NO_MATCHES",
                candidates=[],
                query=query,
                overall_assessment=f"Could not extract event content from {url}. "
                                   "Try describing what you're looking for in text instead.",
            )

    def serialize_candidates(candidates):
        return [
            {
                "ci_name": c.ci_name, "display_name": c.display_name, "tier": c.tier,
                "relevance_score": c.relevance_score, "vector_similarity_pct": c.vector_similarity_pct,
                "stage": c.stage, "catalog_namespace": c.catalog_namespace,
                "duration_min": c.duration_min, "duration_source": c.duration_source,
                "learning_objectives": c.learning_objectives,
                "why_it_fits": c.why_it_fits, "how_to_use": c.how_to_use,
                "suggested_format": c.suggested_format, "duration_notes": c.duration_notes,
                "caveats": c.caveats, "provisions_quarter": c.provisions_quarter,
            }
            for c in candidates
        ]

    # Expand acronyms for better embedding match
    search_query = _expand_acronyms(query)
    if search_query != query:
        logger.info("acronym_expansion", original=query[:200], expanded=search_query[:200])

    # Phase 1: Vector search
    await emit({"phase": "vector_search", "status": "started"})
    state = await asyncio.to_thread(search, search_query, db, distance_cutoff=settings.vector_cutoff, stages=stages or ["prod"], include_zt=include_zt)
    await emit({"phase": "vector_search", "status": "complete", "candidates": len(state.candidates),
                "candidate_data": serialize_candidates(state.candidates)})

    if state.phase == "NO_MATCHES":
        state.overall_assessment = NO_MATCH_GUIDANCE
        await emit({"phase": "complete", "results": 0})
        return state

    # Phase 2: Triage
    await emit({"phase": "triage", "status": "started", "total": len(state.candidates)})
    state = await asyncio.to_thread(triage, state, settings=settings, model=settings.triage_model, triage_cutoff=settings.triage_cutoff)
    relevant = len([c for c in state.candidates if c.tier in ("yellow", "green")])
    db.log_token_usage("triage", settings.triage_model, state.token_usage[-1]["input_tokens"], state.token_usage[-1]["output_tokens"], query_text=query, provider=state.token_usage[-1].get("provider", "anthropic")) if state.token_usage else None
    await emit({"phase": "triage", "status": "complete", "relevant": relevant,
                "candidate_data": serialize_candidates(state.candidates)})

    if state.phase == "NO_MATCHES":
        state.overall_assessment = NO_MATCH_GUIDANCE
        await emit({"phase": "complete", "results": 0})
        return state

    # Usage boost (between triage and rationale)
    _apply_usage_boost(state.candidates, db)

    # Duration re-ranking (between triage and rationale)
    duration_target, is_hard = _extract_duration_target(query)
    if duration_target:
        _apply_duration_penalty(state.candidates, duration_target, is_hard)

    # Re-sort after usage boost and duration penalty
    state.candidates.sort(key=lambda c: (
        0 if c.tier == "yellow" else 1,
        -(c.relevance_score or 0) if c.tier == "yellow" else -(c.vector_similarity_pct or 0),
    ))
    if duration_target:
        logger.info("duration_rerank", target=duration_target, hard=is_hard)

    # Phase 3: Rationale
    top_n = settings.rationale_top_n
    await emit({"phase": "rationale", "status": "started", "top_n": top_n})
    state = await asyncio.to_thread(generate_rationale, state, db, settings=settings, model=settings.rationale_model, top_n=top_n)

    # Assign green tier to the top N candidates by score (deterministic,
    # independent of whether the LLM generated why_it_fits for them)
    yellow_by_score = [c for c in state.candidates if c.tier == "yellow"]
    yellow_by_score.sort(key=lambda c: (-(c.relevance_score or 0), c.ci_name))
    for c in yellow_by_score[:top_n]:
        c.tier = "green"

    green_count = len([c for c in state.candidates if c.tier == "green"])
    for tu in state.token_usage:
        if tu.get("operation") in ("rationale", "synthesis"):
            db.log_token_usage(tu["operation"], tu["model"], tu["input_tokens"], tu["output_tokens"], query_text=query, provider=tu.get("provider", "anthropic"))
    await emit({"phase": "complete", "results": green_count})

    elapsed = round(time.monotonic() - t0, 2)
    logger.info("pipeline_complete", action="pipeline_complete", elapsed_s=elapsed, green=green_count, total=len(state.candidates))
    return state
