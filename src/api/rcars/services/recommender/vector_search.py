"""Phase 1 — vector search with quality threshold."""

import re
import time

import structlog

from rcars.services.analyzer import generate_embedding
from rcars.db import Database
from rcars.services.recommender.models import Candidate, QueryState
from rcars.services.showroom_source import (
    AnalysisSignature, effective_showroom_source, signature_matches_source, signatures_match,
    is_content_excluded,
)

log = structlog.get_logger()

_CI_REF_PATTERN = re.compile(r'\bLB(\d{3,4})\b', re.IGNORECASE)

STOP_WORDS = frozenset({
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

# Grammatical filler only — stripped before embedding to prevent dilution.
# Keeps content-type words (lab, demo, workshop) and action words (show, find)
# that carry search signal for the embedding model.
EMBEDDING_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "it", "to", "for", "of", "and", "or", "in", "on",
    "with", "that", "this", "be", "are", "was", "i", "we", "my", "our", "me",
    "do", "does", "but", "have", "has", "had", "can", "could",
    "should", "would", "will", "what", "which", "how", "about",
    "any", "some", "more", "also", "just", "very", "too", "so", "than",
    "something", "anything", "there",
})


def _strip_embedding_filler(query: str) -> str:
    """Remove grammatical filler words before embedding to reduce dilution."""
    words = query.split()
    kept = [w for w in words if w.lower() not in EMBEDDING_STOP_WORDS]
    return " ".join(kept) if kept else query


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
            log.info("ci_resolve_match", lab_num=lab_num, content_id=item["content_id"], display_name=item.get("display_name", ""))
            resolved_items.append(item)
        else:
            log.info("ci_resolve_miss", lab_num=lab_num)

    # Strategy 2: keyword overlap against display_names (only if no LB match)
    if not resolved_items:
        query_words = {w.lower() for w in re.findall(r'[a-zA-Z]{3,}', query)} - STOP_WORDS
        if len(query_words) >= 2:
            item = db.find_catalog_item_by_keyword_overlap(query_words, stages=stages, min_overlap=3)
            if item:
                log.info("ci_resolve_keyword_match", content_id=item["content_id"], display_name=item.get("display_name", ""))
                resolved_items.append(item)

    results = []
    seen = set()
    for item in resolved_items:
        if (is_content_excluded(item["content_id"])
                or effective_showroom_source(item).status == "excluded"):
            continue
        # Virtual items own materialized artifacts too; infra links are irrelevant.
        embed_content_id = item["content_id"]
        embedding = db.get_embedding(embed_content_id, embed_type="summary")
        if not embedding:
            log.info("ci_resolve_no_embedding", content_id=item["content_id"], embed_content_id=embed_content_id)
            continue

        neighbors = db.search_embeddings(
            query_embedding=embedding, limit=25, stages=stages,
            include_zt=include_zt, content_types=content_types,
            quality_threshold=0.45,
        )
        for row in neighbors:
            if row["content_id"] != item["content_id"] and row["content_id"] not in seen:
                results.append(row)
                seen.add(row["content_id"])

    return results


def _verified_signature(db, content_id):
    item = db.get_babylon_item(content_id)
    analysis = db.get_showroom_analysis(content_id)
    if not item or item.get("retired_at") or item.get("scan_status") != "success" or not analysis or analysis.get("is_stale"):
        return None
    provenance = analysis.get("analysis_provenance_json") or {}
    signature = provenance.get("signature") or {}
    source = effective_showroom_source(item)
    if (not signature_matches_source(signature, source) or provenance.get("source") != source.to_dict()
            or signature.get("content_hash") != analysis.get("content_hash")):
        return None
    try:
        return AnalysisSignature(**signature)
    except (TypeError, ValueError):
        return None


def _authorized_promotion(db, row, stages, include_zt, scope):
    if is_content_excluded(row["content_id"]):
        return None
    if row.get("source") != "babylon":
        return row
    item = db.get_babylon_item(row["content_id"])
    if item and effective_showroom_source(item).status == "excluded":
        return None
    original_signature = _verified_signature(db, row["content_id"])
    if not original_signature:
        return row

    def eligible(target):
        if not target or target.get("stage") not in stages or (scope and target["content_id"] not in scope):
            return False
        if not include_zt and ((target.get("ci_name") or "").startswith("zt-") or (target.get("catalog_namespace") or "").startswith("zt-")):
            return False
        signature = _verified_signature(db, target["content_id"])
        return signature is not None and signatures_match(original_signature, signature)

    if "prod" in stages and row.get("stage") != "prod":
        target = db.get_stage_counterpart(row["content_id"], "prod")
        if eligible(target):
            row = {**target, "best_similarity": row["best_similarity"]}
    aliases = [alias for alias in db.get_virtual_content_aliases(row["content_id"]) if eligible(alias)]
    if len(aliases) == 1:
        row = {**aliases[0], "best_similarity": row["best_similarity"]}
    return row


def search(
    query: str,
    db: Database,
    limit: int = 25,
    stages: list[str] | None = None,
    distance_cutoff: float = 0.55,
    include_zt: bool = True,
    content_types: list[str] | None = None,
    scope_content_ids: list[str] | None = None,
) -> QueryState:
    """Generate query embedding, search pgvector, apply quality threshold.

    The DB returns MAX(similarity) per content_id — no manual dedup needed.
    Returns QueryState with phase VECTOR_DONE or NO_MATCHES.
    """
    t0 = time.monotonic()
    effective_stages = stages or ["prod"]
    quality_threshold = 1.0 - distance_cutoff

    embed_text = _strip_embedding_filler(query)
    log.info("embedding_query", query=query, embed_text=embed_text)
    query_embedding = generate_embedding(embed_text, prefix="search_query")

    rows = db.search_embeddings(
        query_embedding=query_embedding,
        limit=limit,
        stages=effective_stages,
        include_zt=include_zt,
        content_types=content_types,
        quality_threshold=quality_threshold,
        scope_content_ids=scope_content_ids,
    )

    ci_ref_rows = [] if scope_content_ids else _resolve_ci_references(query, db, effective_stages, include_zt, content_types)
    if ci_ref_rows:
        log.info("ci_resolve_neighbors", count=len(ci_ref_rows))
        seen = {r["content_id"] for r in rows}
        for row in ci_ref_rows:
            if row["content_id"] not in seen:
                rows.append(row)
                seen.add(row["content_id"])

    # Filter by quality threshold — DB returns similarity (1.0 = best)
    rows = [r for r in rows if r["best_similarity"] >= quality_threshold]

    rows = [promoted for row in rows
            if (promoted := _authorized_promotion(db, row, effective_stages, include_zt, scope_content_ids)) is not None]

    # Dedup by content_id after all promotions — keep the highest similarity
    seen_ids: dict[str, int] = {}
    deduped_rows: list[dict] = []
    for row in rows:
        cid = row["content_id"]
        if cid in seen_ids:
            existing_idx = seen_ids[cid]
            if row["best_similarity"] > deduped_rows[existing_idx]["best_similarity"]:
                deduped_rows[existing_idx] = row
        else:
            seen_ids[cid] = len(deduped_rows)
            deduped_rows.append(row)
    rows = deduped_rows

    candidates = []
    for row in rows:
        content_id = row["content_id"]
        content_type = row.get("content_type", "")
        ci_name = row.get("ci_name")

        type_data: dict = {}
        if content_type in ("lab", "demo"):
            analysis = db.get_showroom_analysis(content_id)

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

            type_data = {
                "ci_name": ci_name,
                "stage": row.get("stage", "prod"),
                "catalog_namespace": row.get("catalog_namespace", ""),
                "base_ci_name": row.get("base_ci_name"),
                "category": row.get("category", ""),
                "duration_min": duration_min,
                "duration_source": duration_source,
                "learning_objectives": learning_objs,
            }
        elif content_type == "sandbox":
            entity = db.get_content_entity(content_id)
            summary = (entity or {}).get("summary", "")
            topics = (entity or {}).get("topics_json", []) or []
            products = (entity or {}).get("products_json", []) or []
            difficulty = (entity or {}).get("difficulty", "")

            type_data = {
                "ci_name": ci_name,
                "stage": row.get("stage", "prod"),
                "catalog_namespace": row.get("catalog_namespace", ""),
                "base_ci_name": row.get("base_ci_name"),
                "category": row.get("category", ""),
            }
        elif content_type == "architecture":
            pa = db.get_portfolio_architecture(content_id) or {}
            summary = pa.get("summary", "")
            topics = pa.get("topics_json", []) or []
            products = pa.get("products_json", []) or []
            difficulty = pa.get("difficulty", "")
            arch_analysis = db.get_architecture_analysis(content_id) or {}
            type_data = {"asset_type": arch_analysis.get("asset_type", ""), "pa_name": pa.get("pa_name")}
        else:
            summary = row.get("summary", "")
            topics = []
            products = []
            difficulty = ""

        best_similarity = row["best_similarity"]
        vector_distance = 1.0 - best_similarity

        candidates.append(Candidate(
            content_id=content_id,
            display_name=row.get("display_name", content_id),
            content_type=content_type,
            source=row.get("source", "babylon"),
            summary=summary,
            products=products,
            topics=topics,
            status=row.get("stage", "prod"),
            difficulty=difficulty,
            is_hands_on=row.get("is_hands_on", True),
            vector_distance=vector_distance,
            vector_similarity_pct=Candidate.from_similarity(best_similarity),
            type_data=type_data,
        ))

    # Sort by vector distance (ascending — smaller = better)
    candidates.sort(key=lambda c: c.vector_distance)

    elapsed = time.monotonic() - t0
    phase = "VECTOR_DONE" if candidates else "NO_MATCHES"

    log.info("vector_search_complete", candidates=len(candidates),
             threshold=quality_threshold, elapsed=round(elapsed, 3))
    for c in candidates:
        log.info("vector_search_candidate", content_id=c.content_id,
                 ci_name=c.type_data.get("ci_name") or "-", display_name=c.display_name,
                 distance=round(c.vector_distance, 3), similarity_pct=c.vector_similarity_pct)

    return QueryState(
        phase=phase,
        candidates=candidates,
        query=query,
        timings={"vector_search": round(elapsed, 3)},
    )
