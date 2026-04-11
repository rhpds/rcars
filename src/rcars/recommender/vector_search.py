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

    candidates = []
    for row in rows:
        distance = row["distance"]
        if distance > distance_cutoff:
            continue

        ci_name = row["ci_name"]
        analysis = db.get_showroom_analysis(ci_name)

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
