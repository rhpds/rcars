"""Phase 1 — vector search with distance cutoff."""

import logging
import re
import time

from rcars.config import STAGE_PRIORITY
from rcars.services.analyzer import generate_embedding
from rcars.db import Database
from rcars.services.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)

_CI_REF_PATTERN = re.compile(r'\bLB(\d{3,4})\b', re.IGNORECASE)

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "it", "to", "for", "of", "and", "or", "in", "on",
    "with", "that", "this", "be", "are", "was", "i", "we", "my", "our", "me",
    "do", "does", "not", "no", "but", "have", "has", "had", "can", "could",
    "should", "would", "will", "what", "which", "how", "about", "like",
    "similar", "looking", "need", "want", "find", "search", "show", "get",
    "any", "some", "more", "also", "just", "very", "too", "so", "than",
    "content", "item", "lab", "demo", "workshop", "something", "anything",
    "current", "existing", "new", "better", "best", "good", "make", "sure",
    "try", "currently", "suggestion", "minute", "minutes", "hour", "hours",
})


def _resolve_ci_references(query: str, db: Database, stages: list[str], include_zt: bool) -> list[dict]:
    """Find CI references in the query and return neighbors based on the referenced CI's embedding.

    Two strategies:
    1. Lab number pattern (LB1234) — exact prefix match on display_name
    2. Keyword overlap — extract significant words from the query, search display_names
       for items with high word overlap (3+ matching words)
    """
    resolved_items = []

    # Strategy 1: LB number patterns
    for lab_num in _CI_REF_PATTERN.findall(query):
        item = db.find_catalog_item_by_display_name_prefix(f"LB{lab_num}%", stages=stages)
        if item:
            log.info("ci_resolve: LB%s → %s (%s)", lab_num, item["ci_name"], item.get("display_name", ""))
            resolved_items.append(item)
        else:
            log.info("ci_resolve: LB%s not found in catalog", lab_num)

    # Strategy 2: keyword overlap against display_names (only if no LB match)
    if not resolved_items:
        query_words = {w.lower() for w in re.findall(r'[a-zA-Z]{3,}', query)} - _STOP_WORDS
        if len(query_words) >= 2:
            item = db.find_catalog_item_by_keyword_overlap(query_words, stages=stages, min_overlap=3)
            if item:
                log.info("ci_resolve: keyword match → %s (%s)", item["ci_name"], item.get("display_name", ""))
                resolved_items.append(item)

    results = []
    for item in resolved_items:
        embedding = db.get_embedding(item["ci_name"], embed_type="ci_summary")
        if not embedding:
            log.info("ci_resolve: no embedding for %s, skipping", item["ci_name"])
            continue

        neighbors = db.search_embeddings(
            query_embedding=embedding, limit=25, stages=stages, include_zt=include_zt,
        )
        for row in neighbors:
            if row["ci_name"] != item["ci_name"]:
                results.append(row)

    return results


def search(
    query: str,
    db: Database,
    limit: int = 25,
    stages: list[str] | None = None,
    distance_cutoff: float = 0.55,
    include_zt: bool = True,
) -> QueryState:
    """Generate query embedding, search pgvector, apply distance cutoff.

    Returns QueryState with phase VECTOR_DONE or NO_MATCHES.
    """
    t0 = time.monotonic()
    effective_stages = stages or ["prod"]

    query_embedding = generate_embedding(query)

    rows = db.search_embeddings(
        query_embedding=query_embedding,
        limit=limit,
        stages=effective_stages,
        include_zt=include_zt,
    )

    ci_ref_rows = _resolve_ci_references(query, db, effective_stages, include_zt)
    if ci_ref_rows:
        log.info("ci_resolve: adding %d neighbor results from CI references", len(ci_ref_rows))
        seen = {r["ci_name"] for r in rows}
        for row in ci_ref_rows:
            if row["ci_name"] not in seen:
                rows.append(row)
                seen.add(row["ci_name"])

    # Deduplicate by showroom content.  Multiple CIs can share the same
    # showroom repo+ref (prod/dev/event variants, published/base pairs).
    # Group by (showroom_url, showroom_ref) and keep the best representative:
    #   1. Prefer prod over dev/event (prod is orderable by all users)
    #   2. Prefer published over base (published is the orderable CI)
    #   3. Break ties by vector distance
    rows_by_content: dict[tuple, dict] = {}
    for row in rows:
        if row["distance"] > distance_cutoff:
            continue

        content_hash = row.get("content_hash")
        url = row.get("showroom_url") or ""
        ref = row.get("showroom_ref") or ""
        if ref in ("", "main", "master", "HEAD"):
            ref = ""
        # Prefer content_hash for dedup — same hash means identical content
        # regardless of ref (e.g. main vs v1.0.1 tagged from same commit).
        # Fall back to (url, ref) when hash is unavailable (unanalyzed items).
        if content_hash:
            content_key = (content_hash,)
        elif url:
            content_key = (url, ref)
        else:
            content_key = (row["ci_name"],)

        existing = rows_by_content.get(content_key)
        if existing is None:
            rows_by_content[content_key] = row
        else:
            row_stage = STAGE_PRIORITY.get(row.get("stage", "prod"), 9)
            ex_stage = STAGE_PRIORITY.get(existing.get("stage", "prod"), 9)
            row_pub = 0 if row.get("is_published") else 1
            ex_pub = 0 if existing.get("is_published") else 1
            row_rank = (row_stage, row_pub, row["distance"])
            ex_rank = (ex_stage, ex_pub, existing["distance"])
            if row_rank < ex_rank:
                rows_by_content[content_key] = row

    candidates = []
    for row in rows_by_content.values():
        ci_name = row["ci_name"]

        # Base CI with a published counterpart: promote to the published CI.
        # Embeddings live on the base CI (it owns the Showroom), but users
        # can only order the published CI, so present that identity instead.
        if row.get("published_ci_name") and not row.get("is_published"):
            published_item = db.get_catalog_item(row["published_ci_name"])
            if published_item:
                log.debug("vector search: promoting base CI %s → published %s",
                           ci_name, row["published_ci_name"])
                base_ci_name = ci_name
                ci_name = published_item["ci_name"]
                row = {**row,
                       "ci_name": ci_name,
                       "display_name": published_item.get("display_name", ci_name),
                       "category": published_item.get("category", row.get("category", "")),
                       "is_published": True,
                       "base_ci_name": base_ci_name}
            else:
                log.debug("vector search: base CI %s has published_ci_name=%s but not in DB, keeping base",
                           ci_name, row["published_ci_name"])

        # Analysis is stored on the base CI — look it up there
        analysis_ci = row.get("base_ci_name") if row.get("is_published") else ci_name
        analysis = db.get_showroom_analysis(analysis_ci or ci_name)

        lo = (analysis or {}).get("learning_objectives_json") or {}
        learning_objs = (lo.get("stated", []) if isinstance(lo, dict) else []) or []

        candidates.append(Candidate(
            ci_name=ci_name,
            display_name=row.get("display_name", ci_name),
            category=row.get("category", ""),
            summary=(analysis or {}).get("summary", ""),
            topics=(analysis or {}).get("topics_json", []) or [],
            products=(analysis or {}).get("products_json", []) or [],
            difficulty=(analysis or {}).get("difficulty", ""),
            duration_min=(analysis or {}).get("curated_duration_min") if (analysis or {}).get("curated_duration_min") is not None else (analysis or {}).get("estimated_duration_min"),
            duration_source="curated" if (analysis or {}).get("curated_duration_min") is not None else "ai",
            content_type=(analysis or {}).get("content_type", ""),
            stage=row.get("stage", "prod"),
            catalog_namespace=row.get("catalog_namespace", ""),
            learning_objectives=learning_objs,
            vector_distance=row["distance"],
            vector_similarity_pct=Candidate.similarity_pct(row["distance"]),
        ))

    # Sort by vector distance (rows_by_content loses ordering)
    candidates.sort(key=lambda c: c.vector_distance)

    elapsed = time.monotonic() - t0
    phase = "VECTOR_DONE" if candidates else "NO_MATCHES"

    log.info(
        "vector search: %d candidates (cutoff=%.2f, elapsed=%.3fs)",
        len(candidates), distance_cutoff, elapsed,
    )
    for c in candidates:
        log.info("  vector: %s (%s) dist=%.3f sim=%d%%",
                 c.ci_name, c.display_name, c.vector_distance, c.vector_similarity_pct)

    return QueryState(
        phase=phase,
        candidates=candidates,
        query=query,
        timings={"vector_search": round(elapsed, 3)},
    )
