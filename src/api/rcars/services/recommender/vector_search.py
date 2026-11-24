"""Phase 1 — vector search with quality threshold."""

import re
import time

import structlog

from rcars.services.analyzer import generate_embedding
from rcars.db import Database
from rcars.services.recommender.models import Candidate, QueryState
from rcars.services.catalog_identity import collapse_to_cards, exclusion_set_for
from rcars.services.showroom_source import (
    content_owner, effective_showroom_source, is_content_excluded,
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


def _embedding_owner_id(item: dict) -> str:
    """A pure stub's embedding lives on its owner."""
    owner = content_owner(item)
    return f"babylon:{owner}" if owner else item["content_id"]


def _neighbor_rows(
    db: Database, item: dict, stages: list[str], include_zt: bool,
    content_types: list[str] | None,
) -> list[dict]:
    """Search neighbours of ``item``'s summary embedding (the item's own embedding row left out)."""
    if (is_content_excluded(item["content_id"])
            or effective_showroom_source(item).status == "excluded"):
        return []
    embed_content_id = _embedding_owner_id(item)
    embedding = db.get_embedding(embed_content_id, embed_type="summary")
    if not embedding:
        log.info("ci_resolve_no_embedding", content_id=item["content_id"], embed_content_id=embed_content_id)
        return []
    neighbors = db.search_embeddings(
        query_embedding=embedding, limit=25, stages=stages,
        include_zt=include_zt, content_types=content_types,
        quality_threshold=0.45,
    )
    return [row for row in neighbors if row["content_id"] != embed_content_id]


def _resolve_ci_references(
    query: str, db: Database, stages: list[str], include_zt: bool,
    content_types: list[str] | None = None,
) -> list[dict]:
    """Find CI mentions in the query and return neighbors based on the mentioned item's embedding.

    Detection only adds neighbour rows. It never decides what is excluded: that comes
    from the references the user named (``reference_ids``, RHDPCD-2298), however the
    item was named. Two strategies:
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
        for row in _neighbor_rows(db, item, stages, include_zt, content_types):
            if row["content_id"] not in seen:
                results.append(row)
                seen.add(row["content_id"])
    return results


def _reference_context(db: Database, reference_ids: list[str]) -> tuple[list[dict], list[dict], set[str]]:
    """Items the user named as "similar to": (items, references, exclusion set).

    The exclusion set is each item's family and stage copies in every stage
    (``catalog_identity.exclusion_set_for``), plus the stage copies of the stub owner
    that holds its embedding. A reference is {content_id, display_name, summary}; the
    summary is the card analysis (a virtual CI without one uses its anchor's).
    """
    items: list[dict] = []
    references: list[dict] = []
    excluded: set[str] = set()
    for content_id in reference_ids:
        entity = db.get_content_entity(content_id)
        if not entity:
            log.warning("reference_not_found", action="reference_not_found", content_id=content_id)
            continue
        item = {**entity, **(db.get_babylon_item(content_id) or {})}
        items.append(item)
        excluded |= exclusion_set_for(db, content_id) | db.get_stage_copy_ids({_embedding_owner_id(item)})
        references.append({"content_id": content_id,
                           "display_name": item.get("display_name") or content_id,
                           "summary": (db.get_card_analysis(content_id) or {}).get("summary") or ""})
    return items, references, excluded


def _is_excluded(db, row: dict) -> bool:
    """Test content and items whose Showroom source is excluded never show."""
    if is_content_excluded(row["content_id"]):
        return True
    if row.get("source") != "babylon":
        return False
    item = db.get_babylon_item(row["content_id"])
    return bool(item and effective_showroom_source(item).status == "excluded")


def _collapse_families(db, rows, *, stages, include_zt, content_types, scope_content_ids,
                       excluded=frozenset()):
    """Apply the card identity rules (rcars.services.catalog_identity) to search rows.

    ``excluded`` (a "similar to X" exclusion set) are never eligible as the virtual CI
    that absorbs a member: a sibling component then shows as itself.
    """
    covers = db.get_family_covers([r["content_id"] for r in rows])
    candidate_vcis = sorted({v for vcis in covers.values() for v in vcis})
    eligible_rows = {
        cid: vci_row for cid, vci_row in db.get_eligible_card_rows(
            candidate_vcis, content_types=content_types, stages=stages, include_zt=include_zt,
            scope_content_ids=scope_content_ids).items()
        if not _is_excluded(db, vci_row) and cid not in excluded
    }

    def displayed_hash(content_id):
        return ((db.get_card_analysis(content_id) or {}).get("content_hash"))

    return collapse_to_cards(rows, covers, eligible_rows, stages, displayed_hash)


def _owner_scope_ids(db, scope_content_ids: list[str] | None) -> list[str] | None:
    """Scope ids may name pure stubs; their embeddings live on the owner."""
    if not scope_content_ids:
        return scope_content_ids
    expanded = []
    for content_id in scope_content_ids:
        item = db.get_babylon_item(content_id)
        owner = content_owner(item) if item else None
        expanded.append(f"babylon:{owner}" if owner else content_id)
    return expanded


def search(
    query: str,
    db: Database,
    limit: int = 25,
    stages: list[str] | None = None,
    distance_cutoff: float = 0.55,
    include_zt: bool = True,
    content_types: list[str] | None = None,
    scope_content_ids: list[str] | None = None,
    reference_ids: list[str] | None = None,
) -> QueryState:
    """Generate query embedding, search pgvector, apply quality threshold.

    The DB returns MAX(similarity) per content_id. Card identity (families, stage
    copies) is decided by rcars.services.catalog_identity before the top-K cut.
    reference_ids: items the user named as "similar to". They, their family and their
    stage copies are dropped before the family collapse and the top-K cut.
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
        limit=None,  # whole retrieval window; the cut to `limit` comes after the family collapse
        stages=effective_stages,
        include_zt=include_zt,
        content_types=content_types,
        quality_threshold=quality_threshold,
        scope_content_ids=_owner_scope_ids(db, scope_content_ids),
    )

    reference_items, references, excluded = _reference_context(db, reference_ids or [])
    ci_ref_rows = [] if scope_content_ids else _resolve_ci_references(query, db, effective_stages, include_zt, content_types)
    if not scope_content_ids:
        for item in reference_items:
            ci_ref_rows += _neighbor_rows(db, item, effective_stages, include_zt, content_types)
    if ci_ref_rows:
        log.info("ci_resolve_neighbors", count=len(ci_ref_rows))
        seen = {r["content_id"] for r in rows}
        for row in ci_ref_rows:
            if row["content_id"] not in seen:
                rows.append(row)
                seen.add(row["content_id"])

    if excluded:
        # RHDPCD-2298: before the family collapse and the top-K cut, so no slot is left empty.
        kept = [r for r in rows if r["content_id"] not in excluded]
        log.info("ci_reference_exclusion", action="ci_reference_exclusion",
                 referenced=[r["content_id"] for r in references],
                 exclusion_set_size=len(excluded), rows_dropped=len(rows) - len(kept))
        rows = kept

    # Filter by quality threshold — DB returns similarity (1.0 = best)
    rows = [r for r in rows if r["best_similarity"] >= quality_threshold]
    rows = [r for r in rows if not _is_excluded(db, r)]
    raw_hits = len(rows)

    # One card per family and per stage-copy group, BEFORE the final top-K cut.
    rows, collapse = _collapse_families(
        db, rows, stages=effective_stages, include_zt=include_zt,
        content_types=content_types, scope_content_ids=scope_content_ids, excluded=excluded)
    if scope_content_ids:
        # Scope ids that are pure stubs are searched through their owner; an owner left
        # as a card (no family rows yet, or its stub not eligible) is outside the scope.
        in_scope = set(scope_content_ids)
        rows = [r for r in rows if r["content_id"] in in_scope]
    cards_before_cut = len(rows)
    rows = rows[:limit]
    log.info(
        "advisor_family_collapse", action="advisor_family_collapse",
        raw_hits=raw_hits, cards_before_cut=cards_before_cut,
        cards=len(rows), dropped_by_family=len(collapse.dropped_members),
        dropped_members=[{"member": m, "covered_by": v} for m, v in collapse.dropped_members],
        kept_members_no_eligible_virtual_ci=[{"member": m, "covering": v} for m, v in collapse.kept_members],
        merged_stage_copies=[{"dropped": d, "kept": k} for d, k in collapse.merged_stage_copies],
        reason_dropped="member_covered_by_eligible_virtual_ci",
        reason_merged="same_stage_key_same_content_hash_several_stages")

    candidates = []
    for row in rows:
        content_id = row["content_id"]
        content_type = row.get("content_type", "")
        ci_name = row.get("ci_name")

        type_data: dict = {}
        if content_type in ("lab", "demo"):
            analysis = db.get_card_analysis(content_id)

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
        references=references,
    )
