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
