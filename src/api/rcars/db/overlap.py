"""Deterministic overlap candidate generation via structured matching."""
from __future__ import annotations

import structlog
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = structlog.get_logger(component="overlap")

CANDIDATE_SQL = """
WITH deduped AS (
    SELECT DISTINCT ON (COALESCE(bi.showroom_url, ce.content_id))
        ce.content_id,
        COALESCE(sa.products_json, '[]'::jsonb) AS products,
        COALESCE(sa.topics_json, '[]'::jsonb) AS topics,
        sa.content_hash
    FROM content_entities ce
    JOIN showroom_analysis sa ON sa.content_id = ce.content_id
    LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
    WHERE ce.retired_at IS NULL
    ORDER BY COALESCE(bi.showroom_url, ce.content_id),
             CASE bi.stage WHEN 'prod' THEN 0 WHEN 'event' THEN 1 WHEN 'dev' THEN 2 ELSE 3 END
),
pairs AS (
    SELECT
        a.content_id AS content_id_a,
        b.content_id AS content_id_b,
        a.content_hash AS content_hash_a,
        b.content_hash AS content_hash_b,
        (SELECT COUNT(*) FROM (
            SELECT value FROM jsonb_array_elements_text(a.products)
            INTERSECT
            SELECT value FROM jsonb_array_elements_text(b.products)
        ) x)::int AS shared_products,
        (SELECT COUNT(*) FROM (
            SELECT value FROM jsonb_array_elements_text(a.topics)
            INTERSECT
            SELECT value FROM jsonb_array_elements_text(b.topics)
        ) x)::int AS shared_topics
    FROM deduped a
    JOIN deduped b ON a.content_id < b.content_id
)
SELECT * FROM pairs
WHERE shared_products >= %(min_products)s AND shared_topics >= %(min_topics)s
"""

UPSERT_SQL = """
INSERT INTO overlap_candidates
    (content_id_a, content_id_b, shared_products, shared_topics, content_hash_a, content_hash_b, computed_at)
VALUES (%(a)s, %(b)s, %(sp)s, %(st)s, %(ha)s, %(hb)s, NOW())
ON CONFLICT (content_id_a, content_id_b) DO UPDATE SET
    shared_products = EXCLUDED.shared_products,
    shared_topics = EXCLUDED.shared_topics,
    content_hash_a = EXCLUDED.content_hash_a,
    content_hash_b = EXCLUDED.content_hash_b,
    computed_at = NOW()
"""


def generate_overlap_candidates(
    pool: ConnectionPool,
    min_products: int = 1,
    min_topics: int = 2,
) -> dict:
    """Generate overlap candidates via deterministic structured matching.

    Returns {"pairs_inserted": int, "pairs_updated": int, "total_candidates": int}.
    """
    with pool.connection() as conn:
        conn.row_factory = dict_row
        pairs = conn.execute(
            CANDIDATE_SQL, {"min_products": min_products, "min_topics": min_topics}
        ).fetchall()

        inserted = 0
        updated = 0
        for p in pairs:
            cur = conn.execute(
                "SELECT id FROM overlap_candidates WHERE content_id_a = %s AND content_id_b = %s",
                (p["content_id_a"], p["content_id_b"]),
            )
            exists = cur.fetchone() is not None
            conn.execute(UPSERT_SQL, {
                "a": p["content_id_a"], "b": p["content_id_b"],
                "sp": p["shared_products"], "st": p["shared_topics"],
                "ha": p["content_hash_a"], "hb": p["content_hash_b"],
            })
            if exists:
                updated += 1
            else:
                inserted += 1
        conn.commit()

    logger.info("candidates_generated", inserted=inserted, updated=updated, total=len(pairs),
                min_products=min_products, min_topics=min_topics)
    return {"pairs_inserted": inserted, "pairs_updated": updated, "total_candidates": len(pairs)}


def prune_stale_candidates(pool: ConnectionPool) -> int:
    """Remove candidates where either item is retired or missing showroom_analysis."""
    with pool.connection() as conn:
        cur = conn.execute("""
            DELETE FROM overlap_candidates oc
            WHERE EXISTS (
                SELECT 1 FROM content_entities ce
                WHERE ce.content_id IN (oc.content_id_a, oc.content_id_b)
                  AND ce.retired_at IS NOT NULL
            )
            OR NOT EXISTS (
                SELECT 1 FROM showroom_analysis sa
                WHERE sa.content_id = oc.content_id_a
            )
            OR NOT EXISTS (
                SELECT 1 FROM showroom_analysis sa
                WHERE sa.content_id = oc.content_id_b
            )
        """)
        pruned = cur.rowcount
        conn.commit()
    logger.info("stale_candidates_pruned", pruned=pruned)
    return pruned
