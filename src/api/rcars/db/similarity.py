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
    stage: str = "prod",
) -> dict[str, Any]:
    """Compute pairwise content similarity from summary embeddings.

    All pairs are stored as relationship_type='overlap' (same-source).
    Cross-source 'related' pairs will be added when generalized in Task 2.
    """
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                DELETE FROM content_similarity
                WHERE content_id_a IN (
                    SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s
                )
                """,
                {"stage": stage},
            )

            cur.execute(
                """
                INSERT INTO content_similarity
                    (content_id_a, content_id_b, similarity_score, relationship_type, computed_at)
                SELECT a.content_id, b.content_id,
                       1.0 - (a.embedding <=> b.embedding) AS similarity,
                       'overlap',
                       NOW()
                FROM embeddings a
                JOIN embeddings b ON a.content_id < b.content_id
                JOIN content_entities ce_a ON ce_a.content_id = a.content_id
                JOIN content_entities ce_b ON ce_b.content_id = b.content_id
                JOIN babylon_items bi_a ON bi_a.content_id = a.content_id
                JOIN babylon_items bi_b ON bi_b.content_id = b.content_id
                WHERE a.embed_type = 'summary'
                  AND b.embed_type = 'summary'
                  AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
                  AND bi_a.stage = %(stage)s
                  AND bi_b.stage = %(stage)s
                  AND (bi_a.is_published IS NULL OR bi_a.is_published = FALSE)
                  AND (bi_b.is_published IS NULL OR bi_b.is_published = FALSE)
                  AND ce_a.retired_at IS NULL
                  AND ce_b.retired_at IS NULL
                """,
                {"threshold": threshold, "stage": stage},
            )
            inserted = cur.rowcount
        conn.commit()

    logger.info(
        "content_similarity_computed",
        pairs_stored=inserted,
        threshold=threshold,
        stage=stage,
    )
    return {"pairs_stored": inserted, "threshold": threshold, "stage": stage}


def get_similar_items(
    pool: ConnectionPool,
    content_id: str,
    min_score: float = 0.75,
) -> list[dict[str, Any]]:
    """Return items similar to content_id, ordered by similarity_score DESC."""
    sql = """
        SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.computed_at,
               ce.display_name, bi.category, bi.stage, bi.ci_name, sa.summary
        FROM content_similarity cs
        JOIN content_entities ce ON ce.content_id = CASE
            WHEN cs.content_id_a = %(content_id)s THEN cs.content_id_b
            ELSE cs.content_id_a END
        LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
        LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
        WHERE (cs.content_id_a = %(content_id)s OR cs.content_id_b = %(content_id)s)
          AND cs.similarity_score >= %(min_score)s
        ORDER BY cs.similarity_score DESC
    """
    with pool.connection() as conn:
        cur = conn.execute(sql, {"content_id": content_id, "min_score": min_score})
        rows = cur.fetchall()

    results = []
    for row in rows:
        other_id = row["content_id_b"] if row["content_id_a"] == content_id else row["content_id_a"]
        results.append({
            "content_id": other_id,
            "ci_name": row.get("ci_name"),
            "display_name": row["display_name"],
            "category": row.get("category"),
            "stage": row.get("stage"),
            "summary": row.get("summary"),
            "similarity_score": round(row["similarity_score"], 4),
            "computed_at": row["computed_at"],
        })
    return results


def get_overlap_report(
    pool: ConnectionPool,
    min_score: float = 0.75,
    stage: str | None = None,
) -> list[dict[str, Any]]:
    """Return all similarity pairs above min_score, optionally filtered by stage."""
    sql = """
        SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.computed_at,
               ce_a.display_name AS display_name_a, bi_a.category AS category_a, bi_a.stage AS stage_a,
               bi_a.ci_name AS ci_name_a, sa_a.summary AS summary_a,
               ce_b.display_name AS display_name_b, bi_b.category AS category_b, bi_b.stage AS stage_b,
               bi_b.ci_name AS ci_name_b, sa_b.summary AS summary_b
        FROM content_similarity cs
        JOIN content_entities ce_a ON ce_a.content_id = cs.content_id_a
        JOIN content_entities ce_b ON ce_b.content_id = cs.content_id_b
        LEFT JOIN babylon_items bi_a ON bi_a.content_id = cs.content_id_a
        LEFT JOIN babylon_items bi_b ON bi_b.content_id = cs.content_id_b
        LEFT JOIN showroom_analysis sa_a ON sa_a.content_id = cs.content_id_a
        LEFT JOIN showroom_analysis sa_b ON sa_b.content_id = cs.content_id_b
        WHERE cs.similarity_score >= %(min_score)s
    """
    params: dict[str, Any] = {"min_score": min_score}
    if stage:
        sql += " AND bi_a.stage = %(stage)s AND bi_b.stage = %(stage)s"
        params["stage"] = stage
    sql += " ORDER BY cs.similarity_score DESC"
    with pool.connection() as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall()


def get_similarity_stats(
    pool: ConnectionPool,
    stage: str | None = None,
) -> dict[str, Any]:
    """Return aggregate similarity stats, optionally filtered by stage."""
    stage_filter = ""
    params: dict[str, Any] = {}
    if stage:
        stage_filter = """
            AND cs.content_id_a IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)
            AND cs.content_id_b IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)
        """
        params["stage"] = stage
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE 1=1 {stage_filter}", params)
            total_pairs = cur.fetchone()["count"]
            cur.execute(f"SELECT MAX(cs.computed_at) AS last_computed FROM content_similarity cs WHERE 1=1 {stage_filter}", params)
            last = cur.fetchone()["last_computed"]
            cur.execute(f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE cs.similarity_score >= 0.85 {stage_filter}", params)
            high_overlap = cur.fetchone()["count"]
            cur.execute(f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE cs.similarity_score >= 0.75 AND cs.similarity_score < 0.85 {stage_filter}", params)
            related = cur.fetchone()["count"]
    return {
        "total_pairs": total_pairs,
        "high_overlap": high_overlap,
        "related": related,
        "last_computed": last,
    }
