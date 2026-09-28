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
from rcars.services.recommender.rationale import generate_rationale, generate_content_gaps
from rcars.services.recommender.drivers.base import ContentTypeDriver
from rcars.services.event_parser import parse_event_url
import structlog

logger = structlog.get_logger()

NO_MATCH_GUIDANCE = (
    "I help with content recommendations, but I couldn't find a close match. "
    "Try broadening your query — focus on the core topic and technology rather "
    "than event names, lab numbers, or delivery constraints.\n\n"
    "I currently know about all RHDP items that have demo or lab guides."
)


def _build_expansion_map() -> dict[str, str]:
    """Invert the vocabulary's product aliases into term -> canonical name."""
    from rcars.services.vocabulary import load_vocabulary

    expansion: dict[str, str] = {}
    for entry in load_vocabulary().entries("products"):
        extras = " ".join(entry.search_terms)
        target = f"{entry.name} {extras}".strip() if extras else entry.name
        expansion.setdefault(entry.name, entry.name)
        for term in (*entry.aliases, *entry.search_terms):
            expansion.setdefault(term, target)
    return expansion


def _expand_query_terms(query: str) -> str:
    """Expand product names, acronyms, and synonyms for better embedding match."""
    expansion = _build_expansion_map()
    if not expansion:
        return query

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(t) for t in sorted(expansion, key=len, reverse=True)) + r")\b",
        re.IGNORECASE,
    )
    lookup = {t.casefold(): v for t, v in expansion.items()}

    def _replace(m: re.Match) -> str:
        matched = m.group(0)
        target = lookup[matched.casefold()]
        if target.casefold() == matched.casefold():
            return matched
        return f"{matched} ({target})"

    return pattern.sub(_replace, query)


_URL_RE = re.compile(r'(?:https?://\S+|www\.\S+\.\S+)', re.IGNORECASE)


def extract_urls(query: str) -> tuple[list[str], str]:
    """Extract URLs from query, return (urls, remaining_text)."""
    matches = _URL_RE.findall(query)
    urls = []
    for m in matches:
        url = m if m.lower().startswith("http") else f"https://{m}"
        url = url.rstrip(".,;:!?)")
        urls.append(url)
    remaining = _URL_RE.sub("", query).strip()
    remaining = " ".join(remaining.split())
    return urls, remaining


async def run_query(
    query: str,
    db: Database,
    settings: Settings,
    stages: list[str] | None = None,
    include_zt: bool = True,
    on_progress: Callable[[dict], Awaitable[None]] | None = None,
    depth: str = "high",
    scope_content_ids: list[str] | None = None,
    content_types: list[str] | None = None,
) -> dict[str, QueryState]:
    """Orchestrate parallel pipeline runs, one per content-type driver.

    Returns {category_key: QueryState}.
    """
    from rcars.services.recommender.drivers import get_drivers_for_types, registered_content_types

    types = content_types or registered_content_types()
    drivers = get_drivers_for_types(types)

    if len(drivers) == 1:
        cat, driver = next(iter(drivers.items()))
        state = await run_category(
            query, db, settings, driver=driver, category="",
            stages=stages, include_zt=include_zt, on_progress=on_progress,
            depth=depth, scope_content_ids=scope_content_ids,
        )
        return {cat: state}

    async def _run_one(cat: str, drv: ContentTypeDriver):
        return cat, await run_category(
            query, db, settings, driver=drv, category=cat,
            stages=stages, include_zt=include_zt, on_progress=on_progress,
            depth=depth, scope_content_ids=scope_content_ids,
        )

    results = await asyncio.gather(*[_run_one(cat, drv) for cat, drv in drivers.items()])
    return dict(results)


async def run_category(
    query: str,
    db: Database,
    settings: Settings,
    driver: ContentTypeDriver,
    category: str = "",
    stages: list[str] | None = None,
    include_zt: bool = True,
    on_progress: Callable[[dict], Awaitable[None]] | None = None,
    depth: str = "high",
    scope_content_ids: list[str] | None = None,
) -> QueryState:
    """Run the full pipeline for one content-type driver."""

    async def emit(data: dict):
        if category:
            data["category"] = category
        if on_progress:
            await on_progress(data)

    t0 = time.monotonic()

    urls, remaining_text = extract_urls(query)
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
        return [driver.serialize(c) for c in candidates]

    search_query = _expand_query_terms(query)
    if search_query != query:
        logger.info("query_term_expansion", original=query[:200], expanded=search_query[:200])

    # Phase 1: Vector search
    await emit({"phase": "vector_search", "status": "started"})
    state = await asyncio.to_thread(
        search, search_query, db, distance_cutoff=settings.vector_cutoff,
        stages=stages or ["prod"], include_zt=include_zt,
        scope_content_ids=scope_content_ids,
        content_types=driver.content_types,
    )
    await emit({"phase": "vector_search", "status": "complete", "candidates": len(state.candidates),
                "candidate_data": serialize_candidates(state.candidates)})

    if depth == "low":
        await emit({"phase": "complete", "results": len(state.candidates)})
        return state

    if state.phase == "NO_MATCHES":
        state.overall_assessment = NO_MATCH_GUIDANCE
        await emit({"phase": "complete", "results": 0})
        return state

    # Phase 2: Triage
    await emit({"phase": "triage", "status": "started", "total": len(state.candidates)})
    state = await asyncio.to_thread(
        triage, state, settings=settings, model=settings.triage_model,
        triage_cutoff=settings.triage_cutoff,
        guidance=driver.triage_guidance(),
    )
    relevant = len([c for c in state.candidates if c.tier in ("yellow", "green")])
    if state.token_usage:
        db.log_token_usage("triage", settings.triage_model,
                          state.token_usage[-1]["input_tokens"],
                          state.token_usage[-1]["output_tokens"],
                          query_text=query,
                          provider=state.token_usage[-1].get("provider", "anthropic"))
    await emit({"phase": "triage", "status": "complete", "relevant": relevant,
                "candidate_data": serialize_candidates(state.candidates)})

    if state.phase == "NO_MATCHES":
        content_gaps, gap_tokens = await asyncio.to_thread(
            generate_content_gaps, state.query, state.candidates[:5], settings,
        )
        if gap_tokens:
            db.log_token_usage("synthesis", settings.triage_model,
                              gap_tokens.get("input", 0), gap_tokens.get("output", 0),
                              query_text=query, provider=gap_tokens.get("provider", "anthropic"))
        state.overall_assessment = NO_MATCH_GUIDANCE
        state.content_gaps = content_gaps
        await emit({"phase": "complete", "results": 0})
        return state

    if depth == "medium":
        await emit({"phase": "complete",
                    "results": len([c for c in state.candidates if c.tier in ("yellow", "green")])})
        return state

    # Driver-specific post-triage adjustments
    state.candidates = driver.post_triage(state.candidates, query, db)
    state.candidates.sort(key=lambda c: (
        0 if c.tier == "yellow" else 1,
        -(c.relevance_score or 0) if c.tier == "yellow" else -(c.vector_similarity_pct or 0),
    ))

    # Phase 3: Rationale
    top_n = settings.rationale_top_n
    await emit({"phase": "rationale", "status": "started", "top_n": top_n})
    state = await asyncio.to_thread(
        generate_rationale, state, db, settings=settings,
        driver=driver, model=settings.rationale_model, top_n=top_n,
    )

    yellow_by_score = [c for c in state.candidates if c.tier == "yellow"]
    yellow_by_score.sort(key=lambda c: (-(c.relevance_score or 0), c.content_id))
    for c in yellow_by_score[:top_n]:
        c.tier = "green"

    green_count = len([c for c in state.candidates if c.tier == "green"])
    for tu in state.token_usage:
        if tu.get("operation") in ("rationale", "synthesis"):
            db.log_token_usage(tu["operation"], tu["model"],
                              tu["input_tokens"], tu["output_tokens"],
                              query_text=query, provider=tu.get("provider", "anthropic"))
    await emit({"phase": "complete", "results": green_count})

    elapsed = round(time.monotonic() - t0, 2)
    logger.info("pipeline_complete", action="pipeline_complete",
                elapsed_s=elapsed, green=green_count, total=len(state.candidates))
    return state
