"""Fixed tool plans per intent. Read-only. If any handler outgrows ~100 lines,
graduate it to handlers/<intent>.py."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from rcars.config import Settings
from rcars.db.database import Database
from rcars.db.chat_sessions import get_item_workloads, get_performance_scores
from rcars.services.chat.models import Block, InfrastructureArgs, ItemFactsArgs, PerformanceArgs, RecommendArgs
from rcars.services.chat.router import Resolution
from rcars.services.analyzer import generate_embedding
from rcars.services.recommender.pipeline import run_query
from rcars.services.recommender.serialize import candidates_with_performance
from rcars.services.reporting_sync import compute_sales_impact


@dataclass
class HandlerResult:
    blocks: list[Block]
    scaffold_facts: dict
    anchor_ids: list[str] = field(default_factory=list)
    session_results: list[dict] = field(default_factory=list)


def _item_card(db: Database, item: dict) -> dict:
    cid = item["content_id"]
    analysis = db.get_showroom_analysis(cid) or {}
    lo = analysis.get("learning_objectives_json") or {}
    return {
        "content_id": cid, "ci_name": item.get("ci_name"),
        "display_name": item.get("display_name", cid), "stage": item.get("stage"),
        "content_type": (db.get_content_entity(cid) or {}).get("content_type"),
        "summary": analysis.get("summary"),
        "products": analysis.get("products_json") or [],
        "modules": (lo.get("stated") if isinstance(lo, dict) else []) or [],
        "workloads": get_item_workloads(db.pool, cid),
        "neighbors": [],
    }


async def handle_recommend(res: Resolution, db: Database, settings: Settings,
                           stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    args = RecommendArgs.model_validate(res.output.args)
    query = res.message or args.search_query or " ".join(str(v) for v in args.constraints.values())
    if not query and res.scope_ids:
        query = " ".join(i.get("display_name", "") for i in (res.items or []) if i.get("display_name")) or "recommend similar content"
    # scoped working-set questions run medium; full-catalog turns run the full pipeline
    depth = "medium" if res.scope_ids else "high"

    async def _relay(data: dict):
        # run_query emits phase:"complete" when the pipeline finishes, but the
        # chat turn isn't done yet (answer composition follows). Suppress it so
        # only the chat worker's final "complete" closes the SSE stream.
        if data.get("phase") == "complete":
            return
        await on_progress(data)

    state = await run_query(query, db, settings, stages=stages, include_zt=include_zt,
                            on_progress=_relay, depth=depth,
                            scope_content_ids=res.scope_ids or None)
    cards = candidates_with_performance(state, db)
    green = [c for c in cards if c["tier"] == "green"]

    blocks: list[Block] = []
    scoped = bool(res.scope_ids)
    if scoped and not green:
        state = await run_query(query, db, settings, stages=stages, include_zt=include_zt,
                                on_progress=_relay, depth="high",
                                scope_content_ids=None)
        cards = candidates_with_performance(state, db)
        green = [c for c in cards if c["tier"] == "green"]
        scoped = False
        blocks.append(Block(type="notice", data={
            "kind": "scope_expanded",
            "message": "No strong matches in your prior results. Expanded to the full catalog."}))

    blocks.append(Block(type="rec_cards", data={"candidates": cards,
                                                "content_gaps": state.content_gaps}))
    return HandlerResult(
        blocks=blocks,
        scaffold_facts={"result_count": len(cards), "green_count": len(green),
                        "assessment": state.overall_assessment,
                        "top": [c["display_name"] for c in (green or cards)[:3]],
                        "scoped": scoped},
        anchor_ids=[c["content_id"] for c in (green or cards)[:5]],
        session_results=cards)


async def handle_overlap(res: Resolution, db: Database, settings: Settings,
                         stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    if not res.items and not res.scope_ids:
        return HandlerResult(
            blocks=[Block(type="notice", data={"kind": "no_items"})],
            scaffold_facts={"error": "No items specified"}, anchor_ids=[], session_results=[])
    anchors = res.items or [db.get_babylon_item(cid) or {"content_id": cid, "display_name": cid}
                            for cid in res.scope_ids]
    anchor = anchors[0]
    cid = anchor["content_id"]

    with db.pool.connection() as conn:
        from psycopg.rows import dict_row
        conn.row_factory = dict_row
        rows = conn.execute(
            """SELECT oc.content_id_a, oc.content_id_b,
                      oc.shared_products, oc.shared_topics, oc.llm_assessment,
                      ce.display_name, bi.ci_name, bi.stage
               FROM overlap_candidates oc
               JOIN content_entities ce ON ce.content_id =
                   CASE WHEN oc.content_id_a = %(cid)s THEN oc.content_id_b
                        ELSE oc.content_id_a END
               LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
               WHERE oc.content_id_a = %(cid)s OR oc.content_id_b = %(cid)s
               ORDER BY oc.shared_products DESC, oc.shared_topics DESC
               LIMIT 10""",
            {"cid": cid},
        ).fetchall()

    neighbors = []
    for r in rows:
        other_id = r["content_id_b"] if r["content_id_a"] == cid else r["content_id_a"]
        assessment = r["llm_assessment"] or {}
        neighbors.append({
            "content_id": other_id, "ci_name": r.get("ci_name"),
            "display_name": r["display_name"],
            "stage": r.get("stage"),
            "shared_products": r["shared_products"],
            "shared_topics": r["shared_topics"],
            "verdict": assessment.get("verdict"),
            "recommendation": assessment.get("recommendation"),
        })

    return HandlerResult(
        blocks=[Block(type="item_card", data=_item_card(db, anchor)),
                Block(type="overlap_table", data={"anchor": {"content_id": cid,
                                                              "display_name": anchor.get("display_name")},
                                                   "neighbors": neighbors})],
        scaffold_facts={"anchor": anchor.get("display_name"), "neighbor_count": len(neighbors)},
        anchor_ids=[cid],
        session_results=[{"content_id": n["content_id"], "display_name": n["display_name"]}
                         for n in neighbors])


async def handle_performance(res: Resolution, db: Database, settings: Settings,
                             stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    if not res.items and not res.scope_ids:
        return HandlerResult(
            blocks=[Block(type="notice", data={"kind": "no_items"})],
            scaffold_facts={"error": "No items specified"}, anchor_ids=[], session_results=[])
    args = PerformanceArgs.model_validate(res.output.args)
    window = args.window or "6m"
    triaged = [i for i in res.items if i.get("tier") in ("green", "yellow")]
    ids = res.scope_ids or [i["content_id"] for i in (triaged or res.items)]
    scores = get_performance_scores(db.pool, ids)
    rows = []
    for cid in ids:
        entity = db.get_content_entity(cid) or {}
        channels = db.get_performance_channels(cid) or []
        rhdp = next((ch for ch in channels if ch["channel"] == "rhdp"), None) or {}
        wm = rhdp.get("windowed_metrics") or {}
        if isinstance(wm, str):
            wm = json.loads(wm)
        w = wm.get(window) or {}
        last_activity = rhdp.get("last_activity")
        if last_activity and not isinstance(last_activity, str):
            last_activity = str(last_activity)
        rows.append({"content_id": cid, "display_name": entity.get("display_name", cid),
                     "provisions": w.get("provisions", 0),
                     "unique_users": w.get("unique_users", rhdp.get("unique_users", 0)),
                     "last_activity": last_activity,
                     "cost_per_provision": float(rhdp.get("avg_cost_per_provision") or 0) or None,
                     "sales_impact": compute_sales_impact(float(rhdp.get("closed_amount") or 0))
                                     if rhdp else None,
                     "score": (lambda s: s if s is not None else scores.get(cid))((w.get("score_breakdown") or {}).get("score"))})
    if not res.scope_ids:
        rows.sort(key=lambda r: -(r["provisions"] or 0))
    single = len(rows) == 1
    return HandlerResult(
        blocks=[Block(type="performance_table",
                      data={"window": window, "rows": rows})],
        scaffold_facts={"item_count": len(rows), "window": window,
                        "single": single,
                        "best": rows[0]["display_name"] if rows else None,
                        "best_provisions": rows[0]["provisions"] if rows else None},
        anchor_ids=[] if single else ids[:5],
        session_results=[{"content_id": r["content_id"], "display_name": r["display_name"]}
                         for r in rows])


async def handle_item_facts(res: Resolution, db: Database, settings: Settings,
                            stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    if not res.items and not res.scope_ids:
        return HandlerResult(
            blocks=[Block(type="notice", data={"kind": "no_items"})],
            scaffold_facts={"error": "No items specified"}, anchor_ids=[], session_results=[])
    item = (res.items[0] if res.items
            else (db.get_babylon_item(res.scope_ids[0])
                  or {"content_id": res.scope_ids[0], "display_name": res.scope_ids[0]}))
    card = _item_card(db, item)

    with db.pool.connection() as conn:
        from psycopg.rows import dict_row
        conn.row_factory = dict_row
        n_rows = conn.execute(
            """SELECT oc.content_id_a, oc.content_id_b, oc.shared_products, oc.shared_topics,
                      oc.llm_assessment, ce.display_name
               FROM overlap_candidates oc
               JOIN content_entities ce ON ce.content_id =
                   CASE WHEN oc.content_id_a = %(cid)s THEN oc.content_id_b ELSE oc.content_id_a END
               WHERE oc.content_id_a = %(cid)s OR oc.content_id_b = %(cid)s
               ORDER BY oc.shared_products DESC LIMIT 5""",
            {"cid": item["content_id"]},
        ).fetchall()
    card["neighbors"] = [
        {"content_id": r["content_id_b"] if r["content_id_a"] == item["content_id"] else r["content_id_a"],
         "display_name": r["display_name"],
         "verdict": (r["llm_assessment"] or {}).get("verdict")}
        for r in n_rows]
    return HandlerResult(
        blocks=[Block(type="item_card", data=card)],
        scaffold_facts={"display_name": card["display_name"], "stage": card["stage"],
                        "products": card["products"], "neighbor_count": len(card["neighbors"])},
        anchor_ids=[item["content_id"]],
        session_results=[{"content_id": item["content_id"],
                          "display_name": card["display_name"]}])


async def handle_infrastructure(res: Resolution, db: Database, settings: Settings,
                                stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    args = InfrastructureArgs.model_validate(res.output.args)
    query = args.search_query or res.message or ""

    query_vec = generate_embedding(query, prefix="search_query")
    matches = db.search_infrastructure_embeddings(query_vec, limit=10)
    results = [r for rn in [m["role_name"] for m in matches]
               if (r := db.get_infrastructure(rn))]

    if not results:
        return HandlerResult(
            blocks=[Block(type="notice", data={"kind": "no_items",
                    "message": f"No infrastructure entries match '{query}'."})],
            scaffold_facts={"error": "no_match", "query": query})

    top = results[0]
    linked = db.get_infrastructure_linked_items(top["role_name"], top["type"])
    linked_summary = [{"content_id": r["content_id"], "display_name": r["display_name"],
                       "ci_name": r.get("ci_name"), "stage": r.get("stage")} for r in linked]

    others = [{"role_name": r["role_name"], "type": r["type"],
               "description": (r.get("description") or "")[:120],
               "products": r.get("products", [])} for r in results[1:5]]

    return HandlerResult(
        blocks=[Block(type="infra_detail", data={
            "role_name": top["role_name"], "type": top["type"],
            "description": top.get("description"),
            "products": top.get("products", []),
            "capabilities": top.get("capabilities", []),
            "category": top.get("category"),
            "requires": top.get("requires", []),
            "collection": top.get("collection"),
            "items": linked_summary, "item_count": len(linked_summary),
            "other_matches": others,
        })],
        scaffold_facts={"role_name": top["role_name"], "type": top["type"],
                        "products": top.get("products", []),
                        "item_count": len(linked_summary),
                        "match_count": len(results)},
        session_results=[{"content_id": r["content_id"], "display_name": r["display_name"]}
                         for r in linked[:5]])


async def handle_help(res: Resolution, db: Database, settings: Settings,
                      stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    return HandlerResult(
        blocks=[Block(type="notice", data={"kind": "info"})],
        scaffold_facts={"intent": "help"})
