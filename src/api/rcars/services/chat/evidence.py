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
    with db.pool.connection() as conn:
        sim_rows = conn.execute(
            """SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.relationship_type,
                      ce.display_name, bi.stage, sa.products_json,
                      (SELECT pc.provisions FROM performance_channels pc
                       WHERE pc.content_id = ce.content_id AND pc.channel = 'rhdp') AS provisions
               FROM content_similarity cs
               JOIN content_entities ce ON ce.content_id =
                    CASE WHEN cs.content_id_a = ANY(%(ids)s) THEN cs.content_id_b
                         ELSE cs.content_id_a END
               LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
               LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
               WHERE cs.content_id_a = ANY(%(ids)s) OR cs.content_id_b = ANY(%(ids)s)
               ORDER BY cs.similarity_score DESC
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
        pack.append({"anchor": anchor, "name": r["display_name"], "stage": r["stage"],
                     "similarity_pct": round(r["similarity_score"] * 100),
                     "relationship": r["relationship_type"],
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
