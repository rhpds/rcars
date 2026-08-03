"""Result serialization shared by the recommend worker and the chat layer."""
from __future__ import annotations

import json

from rcars.services.reporting_sync import compute_sales_impact


def candidates_with_performance(state, db) -> list[dict]:
    """Convert QueryState candidates to JSON dicts with performance metrics.

    Exact shape matches the inline code from workers/recommend.py — shared by
    both the recommend worker and chat handlers.
    """
    candidates_json = [
        {
            "content_id": c.content_id,
            "ci_name": c.ci_name,
            "display_name": c.display_name,
            "tier": c.tier,
            "relevance_score": c.relevance_score,
            "vector_similarity_pct": c.vector_similarity_pct,
            "stage": c.stage,
            "catalog_namespace": c.catalog_namespace,
            "duration_min": c.duration_min,
            "duration_source": c.duration_source,
            "learning_objectives": c.learning_objectives,
            "why_it_fits": c.why_it_fits,
            "how_to_use": c.how_to_use,
            "suggested_format": c.suggested_format,
            "duration_notes": c.duration_notes,
            "caveats": c.caveats,
        }
        for c in state.candidates
    ]

    for candidate in candidates_json:
        content_id = candidate["content_id"]
        channels = db.get_performance_channels(content_id)
        rhdp = next((ch for ch in channels if ch["channel"] == "rhdp"), None) if channels else None
        if rhdp:
            wm = rhdp.get("windowed_metrics") or {}
            if isinstance(wm, str):
                wm = json.loads(wm)
            q = wm.get("3m", {})
            candidate["provisions_quarter"] = q.get("provisions", 0)
            candidate["avg_cost_per_provision"] = float(rhdp.get("avg_cost_per_provision") or 0)
            candidate["sales_impact"] = compute_sales_impact(float(rhdp.get("closed_amount") or 0))
        else:
            candidate["provisions_quarter"] = candidate.get("provisions_quarter")
            candidate["avg_cost_per_provision"] = None
            candidate["sales_impact"] = None

    return candidates_json
