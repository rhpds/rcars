"""Evidence pack: v1 graph expansion — one hop, code-driven, bounded.

The budget affects only the answer narrative's context; an empty pack yields
identical results with a blander narrative. Caps are code constants, not config.
"""
from __future__ import annotations

import json

from rcars.db.database import Database

MAX_NEIGHBORS = 15


def build_evidence_pack(db: Database, anchor_ids: list[str]) -> list[dict]:
    if not anchor_ids:
        return []
    from psycopg.rows import dict_row
    with db.pool.connection() as conn:
        conn.row_factory = dict_row
        sim_rows = conn.execute(
            """SELECT oc.content_id_a, oc.content_id_b,
                      oc.shared_products, oc.shared_topics, oc.llm_assessment,
                      ce.display_name, bi.stage, sa.products_json,
                      (SELECT pc.provisions FROM performance_channels pc
                       WHERE pc.content_id = ce.content_id AND pc.channel = 'rhdp') AS provisions
               FROM overlap_candidates oc
               JOIN content_entities ce ON ce.content_id =
                    CASE WHEN oc.content_id_a = ANY(%(ids)s) THEN oc.content_id_b
                         ELSE oc.content_id_a END
               LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
               LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
               WHERE oc.content_id_a = ANY(%(ids)s) OR oc.content_id_b = ANY(%(ids)s)
               ORDER BY oc.shared_products DESC, oc.shared_topics DESC
               LIMIT %(cap)s""",
            {"ids": anchor_ids, "cap": MAX_NEIGHBORS}).fetchall()

        wl_rows = conn.execute(
            """SELECT w1.content_id AS anchor, w2.content_id AS other,
                      ce.display_name, bi.stage, w1.workload_role
               FROM babylon_item_workloads w1
               JOIN babylon_item_workloads w2
                 ON w1.workload_fqcn = w2.workload_fqcn AND w1.content_id <> w2.content_id
               JOIN content_entities ce ON ce.content_id = w2.content_id
               LEFT JOIN babylon_items bi ON bi.content_id = w2.content_id
               WHERE w1.content_id = ANY(%(ids)s)
               LIMIT 20""",
            {"ids": anchor_ids}).fetchall()

    pack: list[dict] = []
    seen: set[str] = set()
    for r in sim_rows:
        other = r["content_id_b"] if r["content_id_a"] in anchor_ids else r["content_id_a"]
        anchor = r["content_id_a"] if r["content_id_a"] in anchor_ids else r["content_id_b"]
        seen.add(other)
        products = r["products_json"]
        # Guard: products_json may come back as JSON string
        if isinstance(products, str):
            products = json.loads(products)
        products = (products or [])[:3]
        assessment = r["llm_assessment"] or {}
        pack.append({"anchor": anchor, "name": r["display_name"], "stage": r["stage"],
                     "shared_products": r["shared_products"],
                     "shared_topics": r["shared_topics"],
                     "verdict": assessment.get("verdict"),
                     "relationship": "overlap",
                     "products": products,
                     "provisions": r["provisions"]})
    for r in wl_rows:
        if len(pack) >= MAX_NEIGHBORS:
            break
        if r["other"] in seen or r["other"] in anchor_ids:
            continue
        seen.add(r["other"])
        pack.append({"anchor": r["anchor"], "name": r["display_name"], "stage": r["stage"],
                     "similarity_pct": None, "relationship": "shared_workload",
                     "products": [r["workload_role"]], "provisions": None})
    return pack[:MAX_NEIGHBORS]
