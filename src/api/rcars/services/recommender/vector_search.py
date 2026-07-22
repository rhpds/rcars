"""Phase 1 — vector search with quality threshold."""

import logging
import re
import time

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


def _resolve_ci_references(
    query: str, db: Database, stages: list[str], include_zt: bool,
    content_types: list[str] | None = None,
) -> list[dict]:
    """Find CI references in the query and return neighbors based on the referenced item's embedding.

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
            log.info("ci_resolve: LB%s → %s (%s)", lab_num, item["content_id"], item.get("display_name", ""))
            resolved_items.append(item)
        else:
            log.info("ci_resolve: LB%s not found in catalog", lab_num)

    # Strategy 2: keyword overlap against display_names (only if no LB match)
    if not resolved_items:
        query_words = {w.lower() for w in re.findall(r'[a-zA-Z]{3,}', query)} - _STOP_WORDS
        if len(query_words) >= 2:
            item = db.find_catalog_item_by_keyword_overlap(query_words, stages=stages, min_overlap=3)
            if item:
                log.info("ci_resolve: keyword match → %s (%s)", item["content_id"], item.get("display_name", ""))
                resolved_items.append(item)

    results = []
    seen = set()
    for item in resolved_items:
        # For published CIs, look up embedding on the base CI
        if item.get("is_published") and item.get("base_ci_name"):
            embed_content_id = f"babylon:{item['base_ci_name']}"
        else:
            embed_content_id = item["content_id"]
        embedding = db.get_embedding(embed_content_id, embed_type="summary")
        if not embedding:
            log.info("ci_resolve: no embedding for %s (looked up %s), skipping",
                     item["content_id"], embed_content_id)
            continue

        neighbors = db.search_embeddings(
            query_embedding=embedding, limit=25, stages=stages,
            include_zt=include_zt, content_types=content_types,
        )
        for row in neighbors:
            if row["content_id"] != item["content_id"] and row["content_id"] not in seen:
                results.append(row)
                seen.add(row["content_id"])

    return results


def search(
    query: str,
    db: Database,
    limit: int = 25,
    stages: list[str] | None = None,
    distance_cutoff: float = 0.55,
    include_zt: bool = True,
    content_types: list[str] | None = None,
) -> QueryState:
    """Generate query embedding, search pgvector, apply quality threshold.

    The DB returns MAX(similarity) per content_id — no manual dedup needed.
    Returns QueryState with phase VECTOR_DONE or NO_MATCHES.
    """
    t0 = time.monotonic()
    effective_stages = stages or ["prod"]
    quality_threshold = 1.0 - distance_cutoff

    query_embedding = generate_embedding(query, prefix="search_query")

    rows = db.search_embeddings(
        query_embedding=query_embedding,
        limit=limit,
        stages=effective_stages,
        include_zt=include_zt,
        content_types=content_types,
    )

    ci_ref_rows = _resolve_ci_references(query, db, effective_stages, include_zt, content_types)
    if ci_ref_rows:
        log.info("ci_resolve: adding %d neighbor results from CI references", len(ci_ref_rows))
        seen = {r["content_id"] for r in rows}
        for row in ci_ref_rows:
            if row["content_id"] not in seen:
                rows.append(row)
                seen.add(row["content_id"])

    # Filter by quality threshold — DB returns similarity (1.0 = best)
    rows = [r for r in rows if r["best_similarity"] >= quality_threshold]

    # Stage promotion: for any non-prod Babylon CI, check if a prod CI with
    # the same content_hash exists. If so, swap to the prod version. This handles
    # cases where the LIMIT excluded the prod base CI from vector results —
    # the content is identical, so always prefer the prod identity.
    if "prod" in effective_stages:
        promoted_rows = []
        for row in rows:
            if row.get("source") != "babylon" or row.get("stage") == "prod":
                promoted_rows.append(row)
                continue
            content_hash = row.get("content_hash")
            if not content_hash:
                promoted_rows.append(row)
                continue
            prod_item = db.find_prod_ci_by_content_hash(content_hash)
            if not prod_item or prod_item["content_id"] == row["content_id"]:
                promoted_rows.append(row)
                continue
            prod_content_id = prod_item["content_id"]
            prod_ci_name = prod_item.get("ci_name", "")
            if not include_zt and (prod_ci_name.startswith("zt-") or prod_item.get("catalog_namespace", "").startswith("zt-")):
                promoted_rows.append(row)
                continue
            log.info("stage_promote: %s (stage=%s) → %s (prod, same content_hash)",
                     row["content_id"], row.get("stage"), prod_content_id)
            row = {**row,
                   "content_id": prod_content_id,
                   "ci_name": prod_ci_name,
                   "display_name": prod_item.get("display_name", prod_content_id),
                   "stage": "prod",
                   "catalog_namespace": prod_item.get("catalog_namespace", row.get("catalog_namespace", "")),
                   "published_ci_name": prod_item.get("published_ci_name"),
                   "is_published": prod_item.get("is_published", False)}
            promoted_rows.append(row)
        rows = promoted_rows

    candidates = []
    for row in rows:
        content_id = row["content_id"]
        content_type = row.get("content_type", "")
        ci_name = row.get("ci_name")

        # Base CI with a published counterpart: promote to the published CI.
        # Embeddings live on the base CI (it owns the Showroom), but users
        # can only order the published CI, so present that identity instead.
        if row.get("published_ci_name") and not row.get("is_published"):
            pub_content_id = f"babylon:{row['published_ci_name']}"
            published_item = db.get_babylon_item(pub_content_id)
            if published_item:
                log.debug("vector search: promoting base CI %s → published %s",
                          content_id, pub_content_id)
                base_ci_name = ci_name
                content_id = pub_content_id
                ci_name = published_item.get("ci_name", row["published_ci_name"])
                row = {**row,
                       "content_id": content_id,
                       "ci_name": ci_name,
                       "display_name": published_item.get("display_name", ci_name),
                       "category": published_item.get("category", row.get("category", "")),
                       "is_published": True,
                       "base_ci_name": base_ci_name}
            else:
                log.debug("vector search: base CI %s has published_ci_name=%s but not in DB, keeping base",
                          content_id, row["published_ci_name"])

        # Fetch analysis/card data based on content type
        if content_type in ("lab", "demo"):
            # Analysis is stored on the base CI for published items
            if row.get("is_published") and row.get("base_ci_name"):
                analysis_content_id = f"babylon:{row['base_ci_name']}"
            else:
                analysis_content_id = content_id
            analysis = db.get_showroom_analysis(analysis_content_id)

            lo = (analysis or {}).get("learning_objectives_json") or {}
            learning_objs = (lo.get("stated", []) if isinstance(lo, dict) else []) or []

            summary = (analysis or {}).get("summary", "")
            topics = (analysis or {}).get("topics_json", []) or []
            products = (analysis or {}).get("products_json", []) or []
            difficulty = (analysis or {}).get("difficulty", "")
            duration_min = (
                (analysis or {}).get("curated_duration_min")
                if (analysis or {}).get("curated_duration_min") is not None
                else (analysis or {}).get("estimated_duration_min")
            )
            duration_source = "curated" if (analysis or {}).get("curated_duration_min") is not None else "ai"
        elif content_type == "sandbox":
            # Sandboxes: card fields from content_entities (no showroom analysis)
            entity = db.get_content_entity(content_id)
            summary = (entity or {}).get("summary", "")
            topics = (entity or {}).get("topics_json", []) or []
            products = (entity or {}).get("products_json", []) or []
            difficulty = (entity or {}).get("difficulty", "")
            duration_min = None
            duration_source = "ai"
            learning_objs = []
        else:
            # Fallback for unknown content types
            summary = row.get("summary", "")
            topics = []
            products = []
            difficulty = ""
            duration_min = None
            duration_source = "ai"
            learning_objs = []

        # Convert similarity to distance for backward compat
        best_similarity = row["best_similarity"]
        vector_distance = 1.0 - best_similarity

        candidates.append(Candidate(
            content_id=content_id,
            display_name=row.get("display_name", content_id),
            category=row.get("category", ""),
            summary=summary,
            topics=topics,
            products=products,
            difficulty=difficulty,
            duration_min=duration_min,
            content_type=content_type,
            ci_name=ci_name,
            source=row.get("source", "babylon"),
            is_hands_on=row.get("is_hands_on", True),
            best_match_type=row.get("best_match_type", ""),
            best_match_detail=row.get("best_match_module"),
            stage=row.get("stage", "prod"),
            duration_source=duration_source,
            catalog_namespace=row.get("catalog_namespace", ""),
            base_ci_name=row.get("base_ci_name"),
            learning_objectives=learning_objs,
            vector_distance=vector_distance,
            vector_similarity_pct=Candidate.from_similarity(best_similarity),
        ))

    # Sort by vector distance (ascending — smaller = better)
    candidates.sort(key=lambda c: c.vector_distance)

    elapsed = time.monotonic() - t0
    phase = "VECTOR_DONE" if candidates else "NO_MATCHES"

    log.info(
        "vector search: %d candidates (threshold=%.2f, elapsed=%.3fs)",
        len(candidates), quality_threshold, elapsed,
    )
    for c in candidates:
        log.info("  vector: %s [%s] (%s) dist=%.3f sim=%d%%",
                 c.content_id, c.ci_name or "-", c.display_name,
                 c.vector_distance, c.vector_similarity_pct)

    return QueryState(
        phase=phase,
        candidates=candidates,
        query=query,
        timings={"vector_search": round(elapsed, 3)},
    )
