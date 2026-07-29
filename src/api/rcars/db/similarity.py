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
               bi.category, bi.stage, bi.ci_name, sa.summary
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

    with pool.connection() as conn:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()

    results = []
    for row in rows:
        other_id = row["content_id_b"] if row["content_id_a"] == content_id else row["content_id_a"]
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
        results.append(item)
    return results


def _score_band(score: float) -> str:
    if score >= 0.95:
        return "near_duplicate"
    elif score >= 0.85:
        return "high_overlap"
    else:
        return "related"


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
               bi.category, bi.stage
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

    # Step 2: Get all neighbors for items on this page
    neighbors_sql = """
        SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score,
               ce.display_name, ce.content_type, ce.source,
               bi.category, bi.stage
        FROM content_similarity cs
        JOIN content_entities ce ON ce.content_id = CASE
            WHEN cs.content_id_a = ANY(%(content_ids)s) THEN cs.content_id_b
            ELSE cs.content_id_a END
        LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
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

    # Group neighbors by item
    neighbors_by_item: dict[str, list[dict]] = {cid: [] for cid in content_ids}
    for row in neighbor_rows:
        if row["content_id_a"] in neighbors_by_item:
            item_id = row["content_id_a"]
            other_id = row["content_id_b"]
        else:
            item_id = row["content_id_b"]
            other_id = row["content_id_a"]
        neighbors_by_item[item_id].append({
            "content_id": other_id,
            "display_name": row["display_name"],
            "content_type": row["content_type"],
            "source": row["source"],
            "category": row.get("category"),
            "stage": row.get("stage"),
            "similarity_score": round(row["similarity_score"], 4),
        })

    items = []
    for row in item_rows:
        cid = row["content_id"]
        items.append({
            "content_id": cid,
            "display_name": row["display_name"],
            "content_type": row["content_type"],
            "source": row["source"],
            "category": row.get("category"),
            "stage": row.get("stage"),
            "max_score": round(row["max_score"], 4),
            "neighbor_count": len(neighbors_by_item.get(cid, [])),
            "score_band": _score_band(row["max_score"]),
            "neighbors": neighbors_by_item.get(cid, []),
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
) -> dict[str, Any]:
    """Return aggregate similarity stats with score-band breakdowns."""
    filters = ["1=1"]
    params: dict[str, Any] = {}

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
                f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE {where}",
                params,
            )
            total = cur.fetchone()["count"]

            cur.execute(
                f"SELECT MAX(cs.computed_at) AS last_computed FROM content_similarity cs WHERE {where}",
                params,
            )
            last = cur.fetchone()["last_computed"]

            cur.execute(
                f"""SELECT COUNT(*) AS count FROM content_similarity cs
                    WHERE {where} AND cs.relationship_type = 'overlap' AND cs.similarity_score >= 0.95""",
                params,
            )
            near_duplicates = cur.fetchone()["count"]

            cur.execute(
                f"""SELECT COUNT(*) AS count FROM content_similarity cs
                    WHERE {where} AND cs.relationship_type = 'overlap'
                    AND cs.similarity_score >= 0.85 AND cs.similarity_score < 0.95""",
                params,
            )
            high_overlap = cur.fetchone()["count"]

            cur.execute(
                f"""SELECT COUNT(*) AS count FROM content_similarity cs
                    WHERE {where} AND cs.similarity_score >= 0.75 AND cs.similarity_score < 0.85""",
                params,
            )
            related_band = cur.fetchone()["count"]

    return {
        "near_duplicates": near_duplicates,
        "high_overlap": high_overlap,
        "related_band": related_band,
        "total_pairs_stored": total,
        "last_computed": last,
    }
