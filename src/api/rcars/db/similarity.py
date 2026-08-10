"""Content similarity computation and queries.

Extracted from database.py to start breaking up the monolith.
All functions accept a psycopg ConnectionPool as their first argument.
"""

from __future__ import annotations

import structlog
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from typing import Any

logger = structlog.get_logger(component="similarity")


def compute_content_similarity(
    pool: ConnectionPool,
    threshold: float = 0.75,
    stage: str | None = None,
) -> dict[str, Any]:
    """Compute pairwise content similarity from summary embeddings.

    - Overlap pairs: same source (e.g., Babylon↔Babylon)
    - Related pairs: different sources (e.g., Babylon↔portfolio_arch)
    """
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Clear existing pairs. If stage is specified, only clear Babylon items
            # in that stage. Otherwise clear all.
            if stage:
                cur.execute(
                    """
                    DELETE FROM content_similarity
                    WHERE content_id_a IN (
                        SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s
                    ) OR content_id_b IN (
                        SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s
                    )
                    """,
                    {"stage": stage},
                )
            else:
                cur.execute("DELETE FROM content_similarity")

            # Overlap pairs — same source
            babylon_stage_filter = ""
            if stage:
                babylon_stage_filter = """
                    AND (bi_a.content_id IS NULL OR bi_a.stage = %(stage)s)
                    AND (bi_b.content_id IS NULL OR bi_b.stage = %(stage)s)
                """

            cur.execute(
                f"""
                INSERT INTO content_similarity
                    (content_id_a, content_id_b, similarity_score, relationship_type, computed_at)
                SELECT a.content_id, b.content_id,
                       1.0 - (a.embedding <=> b.embedding),
                       'overlap',
                       NOW()
                FROM embeddings a
                JOIN embeddings b ON a.content_id < b.content_id
                JOIN content_entities ce_a ON ce_a.content_id = a.content_id
                JOIN content_entities ce_b ON ce_b.content_id = b.content_id
                LEFT JOIN babylon_items bi_a ON bi_a.content_id = a.content_id
                LEFT JOIN babylon_items bi_b ON bi_b.content_id = b.content_id
                WHERE a.embed_type = 'summary'
                  AND b.embed_type = 'summary'
                  AND ce_a.source = ce_b.source
                  AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
                  AND ce_a.retired_at IS NULL
                  AND ce_b.retired_at IS NULL
                  AND (bi_a.content_id IS NULL OR (bi_a.is_published IS NULL OR bi_a.is_published = FALSE))
                  AND (bi_b.content_id IS NULL OR (bi_b.is_published IS NULL OR bi_b.is_published = FALSE))
                  {babylon_stage_filter}
                ON CONFLICT (content_id_a, content_id_b) DO UPDATE
                  SET similarity_score = EXCLUDED.similarity_score,
                      relationship_type = EXCLUDED.relationship_type,
                      computed_at = EXCLUDED.computed_at
                """,
                {"threshold": threshold, "stage": stage},
            )
            overlap_count = cur.rowcount

            # Related pairs — different sources
            cur.execute(
                """
                INSERT INTO content_similarity
                    (content_id_a, content_id_b, similarity_score, relationship_type, computed_at)
                SELECT a.content_id, b.content_id,
                       1.0 - (a.embedding <=> b.embedding),
                       'related',
                       NOW()
                FROM embeddings a
                JOIN embeddings b ON a.content_id < b.content_id
                JOIN content_entities ce_a ON ce_a.content_id = a.content_id
                JOIN content_entities ce_b ON ce_b.content_id = b.content_id
                WHERE a.embed_type = 'summary'
                  AND b.embed_type = 'summary'
                  AND ce_a.source != ce_b.source
                  AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
                  AND ce_a.retired_at IS NULL
                  AND ce_b.retired_at IS NULL
                ON CONFLICT (content_id_a, content_id_b) DO UPDATE
                  SET similarity_score = EXCLUDED.similarity_score,
                      relationship_type = EXCLUDED.relationship_type,
                      computed_at = EXCLUDED.computed_at
                """,
                {"threshold": threshold},
            )
            related_count = cur.rowcount
        conn.commit()

    logger.info(
        "content_similarity_computed",
        overlap_pairs=overlap_count,
        related_pairs=related_count,
        threshold=threshold,
        stage=stage,
    )
    return {
        "overlap_pairs": overlap_count,
        "related_pairs": related_count,
        "pairs_stored": overlap_count + related_count,
        "threshold": threshold,
        "stage": stage,
    }


def get_similar_items(
    pool: ConnectionPool,
    content_id: str,
    min_score: float = 0.85,
    relationship_type: str = "overlap",
) -> list[dict[str, Any]]:
    """Return items similar to content_id, ordered by similarity_score DESC.

    relationship_type: 'overlap' (default), 'related', or 'all'.
    When 'all', each result includes 'relationship_type' field.
    """
    rel_filter = ""
    if relationship_type != "all":
        rel_filter = "AND cs.relationship_type = %(relationship_type)s"

    sql = f"""
        SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.computed_at,
               cs.relationship_type,
               ce.display_name, ce.content_type, ce.source,
               bi.category, bi.stage, bi.ci_name, bi.showroom_url, sa.summary
        FROM content_similarity cs
        JOIN content_entities ce ON ce.content_id = CASE
            WHEN cs.content_id_a = %(content_id)s THEN cs.content_id_b
            ELSE cs.content_id_a END
        LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
        LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
        WHERE (cs.content_id_a = %(content_id)s OR cs.content_id_b = %(content_id)s)
          AND cs.similarity_score >= %(min_score)s
          {rel_filter}
        ORDER BY cs.similarity_score DESC
    """
    params = {"content_id": content_id, "min_score": min_score, "relationship_type": relationship_type}

    # Look up the queried item's showroom_url for stage-variant dedup
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT bi.showroom_url FROM babylon_items bi WHERE bi.content_id = %s",
            (content_id,),
        )
        self_row = cur.fetchone()
        self_url = self_row["showroom_url"] if self_row else None

        cur = conn.execute(sql, params)
        rows = cur.fetchall()

    # Deduplicate stage variants by showroom_url, prefer prod
    seen_urls: dict[str, int] = {}
    results = []
    for row in rows:
        other_id = row["content_id_b"] if row["content_id_a"] == content_id else row["content_id_a"]
        neighbor_url = row.get("showroom_url")

        if self_url and neighbor_url and self_url == neighbor_url:
            continue
        if neighbor_url:
            if neighbor_url in seen_urls:
                existing_idx = seen_urls[neighbor_url]
                if row.get("stage") == "prod" and results[existing_idx].get("stage") != "prod":
                    results[existing_idx] = _build_similar_item(row, other_id, relationship_type)
                continue
            seen_urls[neighbor_url] = len(results)

        results.append(_build_similar_item(row, other_id, relationship_type))
    return results


def _build_similar_item(row: dict, other_id: str, relationship_type: str) -> dict[str, Any]:
    item = {
        "content_id": other_id,
        "ci_name": row.get("ci_name"),
        "display_name": row["display_name"],
        "content_type": row.get("content_type"),
        "source": row.get("source"),
        "category": row.get("category"),
        "stage": row.get("stage"),
        "summary": row.get("summary"),
        "similarity_score": round(row["similarity_score"], 4),
        "computed_at": row["computed_at"],
    }
    if relationship_type == "all":
        item["relationship_type"] = row["relationship_type"]
    return item


def _score_band(score: float, near_dup: float = 0.95, high: float = 0.85) -> str:
    if score >= near_dup:
        return "near_duplicate"
    elif score >= high:
        return "high_overlap"
    else:
        return "moderate"


def get_overlap_items(
    pool: ConnectionPool,
    min_score: float = 0.85,
    stage: str | None = None,
    content_type: str | None = None,
    source: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 100,
    relationship_type: str = "overlap",
    near_dup_threshold: float = 0.95,
    display_threshold: float = 0.85,
) -> dict[str, Any]:
    """Return item-centric overlap data, grouped by score bands.

    Each item includes its max similarity score, neighbor count, score band,
    and the full list of neighbors with their individual scores.
    """
    offset = (page - 1) * page_size

    # Build optional filters for the item-level query
    item_filters = []
    params: dict[str, Any] = {
        "min_score": min_score,
        "relationship_type": relationship_type,
        "page_size": page_size,
        "offset": offset,
    }

    if stage:
        item_filters.append("bi.stage = %(stage)s")
        params["stage"] = stage
    if content_type:
        item_filters.append("ce.content_type = %(content_type)s")
        params["content_type"] = content_type
    if source:
        item_filters.append("ce.source = %(source)s")
        params["source"] = source
    if search:
        item_filters.append("ce.display_name ILIKE %(search)s")
        params["search"] = f"%{search}%"

    item_where = (" AND " + " AND ".join(item_filters)) if item_filters else ""

    # Step 1: Get items with their max score and neighbor count
    items_sql = f"""
        WITH all_sides AS (
            SELECT content_id_a AS content_id, similarity_score
            FROM content_similarity
            WHERE similarity_score >= %(min_score)s AND relationship_type = %(relationship_type)s
            UNION ALL
            SELECT content_id_b AS content_id, similarity_score
            FROM content_similarity
            WHERE similarity_score >= %(min_score)s AND relationship_type = %(relationship_type)s
        ),
        item_scores AS (
            SELECT als.content_id,
                   MAX(als.similarity_score) AS max_score,
                   COUNT(*) AS neighbor_count
            FROM all_sides als
            JOIN content_entities ce ON ce.content_id = als.content_id
            LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
            WHERE 1=1 {item_where}
            GROUP BY als.content_id
        )
        SELECT COUNT(*) OVER() AS total_count,
               isc.content_id, isc.max_score, isc.neighbor_count,
               ce.display_name, ce.content_type, ce.source,
               bi.ci_name, bi.category, bi.stage, bi.showroom_url
        FROM item_scores isc
        JOIN content_entities ce ON ce.content_id = isc.content_id
        LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
        ORDER BY isc.max_score DESC, isc.neighbor_count DESC
        LIMIT %(page_size)s OFFSET %(offset)s
    """

    with pool.connection() as conn:
        cur = conn.execute(items_sql, params)
        item_rows = cur.fetchall()

    if not item_rows:
        return {
            "items": [],
            "total_items": 0,
            "page": page,
            "page_size": page_size,
        }

    total_items = item_rows[0]["total_count"]
    content_ids = [row["content_id"] for row in item_rows]

    # Build showroom_url lookup for deduplicating stage variants
    item_showroom_urls: dict[str, str | None] = {
        row["content_id"]: row.get("showroom_url") for row in item_rows
    }

    # Step 2: Get all neighbors for items on this page
    # Neighbors are NOT stage-filtered — a prod item needs to see dev/event overlaps
    # (the top-level items are stage-filtered, but neighbors show the full picture)
    neighbors_sql = """
        SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score,
               ce_a.display_name AS display_name_a, ce_a.content_type AS content_type_a,
               ce_a.source AS source_a, bi_a.ci_name AS ci_name_a, bi_a.category AS category_a, bi_a.stage AS stage_a, bi_a.showroom_url AS showroom_url_a,
               ce_b.display_name AS display_name_b, ce_b.content_type AS content_type_b,
               ce_b.source AS source_b, bi_b.ci_name AS ci_name_b, bi_b.category AS category_b, bi_b.stage AS stage_b, bi_b.showroom_url AS showroom_url_b
        FROM content_similarity cs
        JOIN content_entities ce_a ON ce_a.content_id = cs.content_id_a
        JOIN content_entities ce_b ON ce_b.content_id = cs.content_id_b
        LEFT JOIN babylon_items bi_a ON bi_a.content_id = cs.content_id_a
        LEFT JOIN babylon_items bi_b ON bi_b.content_id = cs.content_id_b
        WHERE (cs.content_id_a = ANY(%(content_ids)s) OR cs.content_id_b = ANY(%(content_ids)s))
          AND cs.similarity_score >= %(min_score)s
          AND cs.relationship_type = %(relationship_type)s
        ORDER BY cs.similarity_score DESC
    """

    with pool.connection() as conn:
        cur = conn.execute(
            neighbors_sql,
            {"content_ids": content_ids, "min_score": min_score, "relationship_type": relationship_type},
        )
        neighbor_rows = cur.fetchall()

    # Group neighbors by item — handle both directions when both sides are on the page.
    # Deduplicate stage variants: if a neighbor shares the same showroom_url as the
    # top-level item, it's the same content in a different stage (expected, not overlap).
    # Among remaining neighbors, keep only one entry per showroom_url — prefer prod
    # over dev/event so curators see the production version of similar content.
    neighbors_by_item: dict[str, list[dict]] = {cid: [] for cid in content_ids}
    seen_urls_by_item: dict[str, dict[str, int]] = {cid: {} for cid in content_ids}

    def _add_neighbor(item_id: str, neighbor: dict, neighbor_url: str | None) -> None:
        item_url = item_showroom_urls.get(item_id)
        if item_url and neighbor_url and item_url == neighbor_url:
            return
        if neighbor_url:
            if neighbor_url in seen_urls_by_item[item_id]:
                existing_idx = seen_urls_by_item[item_id][neighbor_url]
                existing = neighbors_by_item[item_id][existing_idx]
                if neighbor.get("stage") == "prod" and existing.get("stage") != "prod":
                    neighbors_by_item[item_id][existing_idx] = neighbor
                return
            seen_urls_by_item[item_id][neighbor_url] = len(neighbors_by_item[item_id])
        neighbors_by_item[item_id].append(neighbor)

    for row in neighbor_rows:
        a_id, b_id = row["content_id_a"], row["content_id_b"]
        score = round(row["similarity_score"], 4)

        if a_id in neighbors_by_item:
            _add_neighbor(a_id, {
                "content_id": b_id,
                "display_name": row["display_name_b"],
                "content_type": row["content_type_b"],
                "source": row["source_b"],
                "ci_name": row.get("ci_name_b"),
                "category": row.get("category_b"),
                "stage": row.get("stage_b"),
                "similarity_score": score,
            }, row.get("showroom_url_b"))

        if b_id in neighbors_by_item:
            _add_neighbor(b_id, {
                "content_id": a_id,
                "display_name": row["display_name_a"],
                "content_type": row["content_type_a"],
                "source": row["source_a"],
                "ci_name": row.get("ci_name_a"),
                "category": row.get("category_a"),
                "stage": row.get("stage_a"),
                "similarity_score": score,
            }, row.get("showroom_url_a"))

    items = []
    for row in item_rows:
        cid = row["content_id"]
        deduped = neighbors_by_item.get(cid, [])
        if not deduped:
            continue
        item_max = max(n["similarity_score"] for n in deduped)
        items.append({
            "content_id": cid,
            "display_name": row["display_name"],
            "content_type": row["content_type"],
            "source": row["source"],
            "ci_name": row.get("ci_name"),
            "category": row.get("category"),
            "stage": row.get("stage"),
            "max_score": item_max,
            "neighbor_count": len(deduped),
            "score_band": _score_band(item_max, near_dup=near_dup_threshold, high=display_threshold),
            "neighbors": deduped,
        })

    return {
        "items": items,
        "total_items": total_items,
        "page": page,
        "page_size": page_size,
    }


def get_similarity_stats(
    pool: ConnectionPool,
    stage: str | None = None,
    relationship_type: str | None = None,
    near_dup_threshold: float = 0.95,
    display_threshold: float = 0.85,
    storage_threshold: float = 0.75,
) -> dict[str, Any]:
    """Return aggregate similarity stats with score-band breakdowns."""
    filters = ["1=1"]
    params: dict[str, Any] = {
        "near_dup": near_dup_threshold,
        "display": display_threshold,
        "storage": storage_threshold,
    }

    if stage:
        filters.append(
            "cs.content_id_a IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)"
        )
        filters.append(
            "cs.content_id_b IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)"
        )
        params["stage"] = stage

    if relationship_type:
        filters.append("cs.relationship_type = %(relationship_type)s")
        params["relationship_type"] = relationship_type

    where = " AND ".join(filters)

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""SELECT
                        COUNT(*) AS total,
                        MAX(cs.computed_at) AS last_computed,
                        COUNT(*) FILTER (WHERE cs.similarity_score >= %(near_dup)s) AS near_duplicates,
                        COUNT(*) FILTER (WHERE cs.similarity_score >= %(display)s AND cs.similarity_score < %(near_dup)s) AS high_overlap,
                        COUNT(*) FILTER (WHERE cs.similarity_score >= %(storage)s AND cs.similarity_score < %(display)s) AS related_band
                    FROM content_similarity cs
                    WHERE {where}""",
                params,
            )
            row = cur.fetchone()

    return {
        "near_duplicates": row["near_duplicates"],
        "high_overlap": row["high_overlap"],
        "related_band": row["related_band"],
        "total_pairs_stored": row["total"],
        "last_computed": row["last_computed"],
    }
