"""Fixed tool plans per intent. Read-only. If any handler outgrows ~100 lines,
graduate it to handlers/<intent>.py."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from rcars.config import Settings
from rcars.db.database import Database
from rcars.db.chat_sessions import get_item_workloads, get_performance_scores
from rcars.db.similarity import get_similar_items
from rcars.services.chat.models import Block, ItemFactsArgs, PerformanceArgs, RecommendArgs
from rcars.services.chat.router import Resolution
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
    query = args.search_query or " ".join(str(v) for v in args.constraints.values())
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
    anchor_analysis = db.get_showroom_analysis(anchor["content_id"]) or {}
    anchor_products = set(anchor_analysis.get("products_json") or [])
    raw = get_similar_items(db.pool, anchor["content_id"],
                            min_score=settings.similarity_storage_threshold,
                            relationship_type="all")[:10]
    neighbors = []
    for n in raw:
        n_products = set((db.get_showroom_analysis(n["content_id"]) or {}).get("products_json") or [])
        neighbors.append({
            "content_id": n["content_id"], "ci_name": n.get("ci_name"),
            "display_name": n["display_name"],
            "stage": n.get("stage"), "similarity_pct": round(n["similarity_score"] * 100),
            "relationship_type": n.get("relationship_type", "overlap"),
            "shared_products": sorted(anchor_products & n_products),
            "why": None,  # populated by the future overlap-summary batch job
        })
    return HandlerResult(
        blocks=[Block(type="item_card", data=_item_card(db, anchor)),
                Block(type="overlap_table", data={"anchor": {"content_id": anchor["content_id"],
                                                             "display_name": anchor.get("display_name")},
                                                  "neighbors": neighbors})],
        scaffold_facts={"anchor": anchor.get("display_name"), "neighbor_count": len(neighbors),
                        "top_similarity": neighbors[0]["similarity_pct"] if neighbors else None},
        anchor_ids=[anchor["content_id"]],
        session_results=[{"content_id": n["content_id"], "display_name": n["display_name"]}
                         for n in neighbors])


async def handle_performance(res: Resolution, db: Database, settings: Settings,
                             stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    if not res.items and not res.scope_ids:
        return HandlerResult(
            blocks=[Block(type="notice", data={"kind": "no_items"})],
            scaffold_facts={"error": "No items specified"}, anchor_ids=[], session_results=[])
    args = PerformanceArgs.model_validate(res.output.args)
    window = args.window or "3m"
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
                     "score": scores.get(cid)})
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
        anchor_ids=ids[:5],
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
    card["neighbors"] = [
        {"content_id": n["content_id"], "display_name": n["display_name"],
         "similarity_pct": round(n["similarity_score"] * 100)}
        for n in get_similar_items(db.pool, item["content_id"],
                                   min_score=settings.similarity_threshold)[:5]]
    return HandlerResult(
        blocks=[Block(type="item_card", data=card)],
        scaffold_facts={"display_name": card["display_name"], "stage": card["stage"],
                        "products": card["products"], "neighbor_count": len(card["neighbors"])},
        anchor_ids=[item["content_id"]],
        session_results=[{"content_id": item["content_id"],
                          "display_name": card["display_name"]}])
