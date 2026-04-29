"""Phase 1 — vector search with distance cutoff."""

import logging
import time

from rcars.services.analyzer import generate_embedding
from rcars.db import Database
from rcars.services.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)


def search(
    query: str,
    db: Database,
    limit: int = 25,
    prod_only: bool = True,
    distance_cutoff: float = 0.55,
    include_zt: bool = True,
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
        include_zt=include_zt,
    )

    # Deduplicate by showroom content.  Multiple CIs can share the same
    # showroom repo+ref (prod/dev/event variants, published/base pairs).
    # Group by (showroom_url, showroom_ref) and keep the best representative:
    #   1. Prefer prod over dev/event (prod is orderable by all users)
    #   2. Prefer published over base (published is the orderable CI)
    #   3. Break ties by vector distance
    stage_priority = {"prod": 0, "event": 1, "dev": 2}
    rows_by_content: dict[tuple, dict] = {}
    for row in rows:
        if row["distance"] > distance_cutoff:
            continue

        url = row.get("showroom_url") or ""
        ref = row.get("showroom_ref") or ""
        if ref in ("", "main", "master", "HEAD"):
            ref = ""
        content_key = (url, ref) if url else (row["ci_name"],)

        existing = rows_by_content.get(content_key)
        if existing is None:
            rows_by_content[content_key] = row
        else:
            row_stage = stage_priority.get(row.get("stage", "prod"), 9)
            ex_stage = stage_priority.get(existing.get("stage", "prod"), 9)
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
            duration_min=(analysis or {}).get("estimated_duration_min"),
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
