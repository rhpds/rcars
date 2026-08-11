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


def get_overlap_stats(pool: ConnectionPool) -> dict:
    """Aggregate stats by verdict."""
    with pool.connection() as conn:
        conn.row_factory = dict_row
        row = conn.execute("""
            SELECT
                COUNT(*) AS total_pairs,
                COUNT(*) FILTER (WHERE llm_assessment->>'verdict' = 'redundant') AS redundant,
                COUNT(*) FILTER (WHERE llm_assessment->>'verdict' = 'complementary') AS complementary,
                COUNT(*) FILTER (WHERE llm_assessment->>'verdict' = 'differentiated') AS differentiated,
                COUNT(*) FILTER (WHERE llm_assessment IS NULL) AS unassessed,
                MAX(computed_at) AS last_computed
            FROM overlap_candidates
        """).fetchone()
    return dict(row)


def get_overlap_items(
    pool: ConnectionPool,
    verdict: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 100,
    min_shared_products: int | None = None,
    min_shared_topics: int | None = None,
) -> dict:
    """Item-centric overlap report grouped by verdict."""
    with pool.connection() as conn:
        conn.row_factory = dict_row

        # Build WHERE clauses for the candidates
        conditions = []
        params: dict = {}
        if verdict == "unassessed":
            conditions.append("oc.llm_assessment IS NULL")
        elif verdict:
            conditions.append("oc.llm_assessment->>'verdict' = %(verdict)s")
            params["verdict"] = verdict
        if min_shared_products is not None:
            conditions.append("oc.shared_products >= %(min_sp)s")
            params["min_sp"] = min_shared_products
        if min_shared_topics is not None:
            conditions.append("oc.shared_topics >= %(min_st)s")
            params["min_st"] = min_shared_topics

        where = (" AND " + " AND ".join(conditions)) if conditions else ""

        # Step 1: Find distinct items that appear in matching candidates
        search_cond = ""
        if search:
            search_cond = " AND ce.display_name ILIKE %(search)s"
            params["search"] = f"%{search}%"

        count_sql = f"""
            SELECT COUNT(DISTINCT item_id) FROM (
                SELECT content_id_a AS item_id FROM overlap_candidates oc {where and 'WHERE ' + where.lstrip(' AND ') or ''}
                UNION
                SELECT content_id_b AS item_id FROM overlap_candidates oc {where and 'WHERE ' + where.lstrip(' AND ') or ''}
            ) ids
            JOIN content_entities ce ON ce.content_id = ids.item_id
            WHERE 1=1 {search_cond}
        """
        total = conn.execute(count_sql, params).fetchone()["count"]

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        items_sql = f"""
            SELECT DISTINCT ce.content_id, ce.display_name, ce.content_type, ce.source,
                   bi.ci_name, bi.category, bi.stage
            FROM (
                SELECT content_id_a AS item_id FROM overlap_candidates oc {where and 'WHERE ' + where.lstrip(' AND ') or ''}
                UNION
                SELECT content_id_b AS item_id FROM overlap_candidates oc {where and 'WHERE ' + where.lstrip(' AND ') or ''}
            ) ids
            JOIN content_entities ce ON ce.content_id = ids.item_id
            LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
            WHERE 1=1 {search_cond}
            ORDER BY ce.display_name
            LIMIT %(limit)s OFFSET %(offset)s
        """
        item_rows = conn.execute(items_sql, params).fetchall()

        # Step 2: For each item, fetch its neighbors from matching candidates
        items = []
        for ir in item_rows:
            cid = ir["content_id"]
            neighbor_sql = f"""
                SELECT oc.content_id_a, oc.content_id_b,
                       oc.shared_products, oc.shared_topics,
                       oc.llm_assessment, oc.assessed_at,
                       ce.display_name, ce.content_type, ce.source,
                       bi.ci_name, bi.category, bi.stage
                FROM overlap_candidates oc
                JOIN content_entities ce ON ce.content_id =
                    CASE WHEN oc.content_id_a = %(cid)s THEN oc.content_id_b
                         ELSE oc.content_id_a END
                LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
                WHERE (oc.content_id_a = %(cid)s OR oc.content_id_b = %(cid)s)
                {where}
                ORDER BY oc.shared_products DESC, oc.shared_topics DESC
            """
            n_params = {**params, "cid": cid}
            n_rows = conn.execute(neighbor_sql, n_params).fetchall()

            neighbors = []
            for nr in n_rows:
                assessment = nr["llm_assessment"] or {}
                neighbors.append({
                    "content_id": nr["content_id_a"] if nr["content_id_a"] != cid else nr["content_id_b"],
                    "display_name": nr["display_name"],
                    "content_type": nr["content_type"],
                    "source": nr["source"],
                    "ci_name": nr["ci_name"],
                    "category": nr["category"],
                    "stage": nr["stage"],
                    "shared_products": nr["shared_products"],
                    "shared_topics": nr["shared_topics"],
                    "verdict": assessment.get("verdict"),
                    "recommendation": assessment.get("recommendation"),
                    "assessed_at": str(nr["assessed_at"]) if nr["assessed_at"] else None,
                })

            items.append({
                **dict(ir),
                "neighbor_count": len(neighbors),
                "neighbors": neighbors,
            })

    return {"items": items, "total_items": total, "page": page, "page_size": page_size}


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
