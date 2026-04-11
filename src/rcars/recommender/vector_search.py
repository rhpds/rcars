"""Phase 1 — vector search with distance cutoff."""

import logging
import time

from rcars.analyzer import generate_embedding
from rcars.db import Database
from rcars.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)


def search(
    query: str,
    db: Database,
    limit: int = 10,
    prod_only: bool = True,
    distance_cutoff: float = 0.55,
) -> QueryState:
    """Generate query embedding, search pgvector, apply distance cutoff.

    Returns QueryState with phase VECTOR_DONE or NO_MATCHES.
    """
    t0 = time.monotonic()

    query_embedding = generate_embedding(query)

    rows = db.search_embeddings(
        query_embedding=query_embedding,
        limit=limit,
        prod_only=prod_only,
    )

    # Deduplicate published/base CI pairs — keep the one with better distance.
    # A published CI and its base CI share the same Showroom content, so
    # showing both is misleading.  Track which base CIs we've already seen.
    seen_bases: set[str] = set()

    candidates = []
    for row in rows:
        distance = row["distance"]
        if distance > distance_cutoff:
            continue

        ci_name = row["ci_name"]

        # Determine the "content key" — base CI name if this is a published
        # CI, or the CI's own name if it IS the base.  Skip if we already
        # have a candidate for this content.
        base = row.get("base_ci_name") or ci_name
        if row.get("published_ci_name"):
            # This is a base CI that has a published counterpart
            base = ci_name
        if base in seen_bases:
            log.debug("vector search: skipping duplicate %s (base=%s)", ci_name, base)
            continue
        seen_bases.add(base)

        # For published CIs, fetch analysis from the base CI (where it's stored)
        analysis_ci = row.get("base_ci_name") if row.get("is_published") else ci_name
        analysis = db.get_showroom_analysis(analysis_ci or ci_name)

        candidates.append(Candidate(
            ci_name=ci_name,
            display_name=row.get("display_name", ci_name),
            category=row.get("category", ""),
            summary=(analysis or {}).get("summary", ""),
            topics=(analysis or {}).get("topics_json", []) or [],
            products=(analysis or {}).get("products_json", []) or [],
            difficulty=(analysis or {}).get("difficulty", ""),
            duration_min=(analysis or {}).get("estimated_duration_min"),
            content_type=(analysis or {}).get("content_type", ""),
            vector_distance=distance,
            vector_similarity_pct=Candidate.similarity_pct(distance),
        ))

    elapsed = time.monotonic() - t0
    phase = "VECTOR_DONE" if candidates else "NO_MATCHES"

    log.info(
        "vector search: %d candidates (cutoff=%.2f, elapsed=%.3fs)",
        len(candidates), distance_cutoff, elapsed,
    )

    return QueryState(
        phase=phase,
        candidates=candidates,
        query=query,
        timings={"vector_search": round(elapsed, 3)},
    )
