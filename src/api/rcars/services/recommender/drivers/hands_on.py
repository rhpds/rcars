"""Driver for hands-on content: labs, demos, sandboxes."""

from __future__ import annotations

import bisect
import json
import math
import re
from typing import Any

import structlog

from rcars.services.recommender.drivers.base import ContentTypeDriver
from rcars.services.recommender.models import Candidate

log = structlog.get_logger()

_FORMAT_LABELS = {
    "hands_on_lab": "Hands-on Lab",
    "demo": "Demo",
    "sandbox": "Sandbox",
}


def _extract_duration_target(query: str) -> tuple[int | None, bool]:
    hard_keywords = ("hard limit", "strict", "maximum", "no more than", "at most", "cannot exceed", "must be under")
    is_hard = any(k in query.lower() for k in hard_keywords)
    patterns = [
        r'(\d+)\s*[-–]?\s*hour',
        r'(\d+)\s*[-–]?\s*min',
        r'(\d+)\s*[-–]?\s*hr',
    ]
    for pat in patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 'min' in pat:
                return val, is_hard
            return val * 60, is_hard
    return None, is_hard


class HandsOnDriver(ContentTypeDriver):

    @property
    def content_types(self) -> list[str]:
        return ["lab", "demo", "sandbox"]

    @property
    def category_key(self) -> str:
        return "hands_on"

    def fetch_analysis(self, db: Any, candidate: Candidate) -> dict:
        if candidate.content_type in ("lab", "demo"):
            base = candidate.type_data.get("base_ci_name")
            analysis_cid = f"babylon:{base}" if base else candidate.content_id
            return db.get_showroom_analysis(analysis_cid) or {}
        # sandbox
        item = db.get_babylon_item(candidate.content_id) or {}
        workloads = db.get_workload_classifications(candidate.content_id)
        if workloads:
            item["workload_classifications"] = workloads
        return item

    def triage_guidance(self) -> str:
        return ""

    def format_for_rationale(self, candidate: Candidate, analysis: dict) -> str:
        td = candidate.type_data
        lines = [
            f"Content ID: {candidate.content_id}",
            f"Display Name: {candidate.display_name}",
            f"Category: {td.get('category', '')}",
            f"Content Type: {candidate.content_type}",
            f"Relevance Score: {candidate.relevance_score or 0}%",
            f"Summary: {candidate.summary}",
            f"Difficulty: {candidate.difficulty}",
            f"Duration: {td.get('duration_min') or '?'} min",
            f"Topics: {', '.join(candidate.topics)}",
            f"Products: {', '.join(candidate.products)}",
        ]
        if candidate.content_type in ("lab", "demo"):
            audience = analysis.get("audience_json", [])
            if audience:
                lines.append(f"Audience: {', '.join(audience)}")
            objectives = analysis.get("learning_objectives_json", {})
            if isinstance(objectives, dict):
                stated = objectives.get("stated", [])
                inferred = objectives.get("inferred", [])
                if stated:
                    lines.append(f"Stated Objectives: {'; '.join(stated)}")
                if inferred:
                    lines.append(f"Inferred Objectives: {'; '.join(inferred)}")
            modules = analysis.get("modules_json", [])
            if modules:
                mod_titles = [m.get("title", "") for m in modules if m.get("title")]
                if mod_titles:
                    lines.append(f"Modules: {'; '.join(mod_titles)}")
        elif candidate.content_type == "sandbox":
            cloud = analysis.get("cloud_provider", "")
            if cloud:
                lines.append(f"Cloud Provider: {cloud}")
            ocp = analysis.get("ocp_version", "")
            if ocp:
                lines.append(f"OpenShift Version: {ocp}")
            workloads = analysis.get("workload_classifications", [])
            if workloads:
                wl_names = [w.get("product_name", "") for w in workloads if w.get("product_name")]
                if wl_names:
                    lines.append(f"Workloads: {'; '.join(wl_names)}")
        return "\n".join(lines)

    def post_triage(self, candidates: list[Candidate], query: str, db: Any) -> list[Candidate]:
        self._apply_usage_boost(candidates, db)
        duration_target, is_hard = _extract_duration_target(query)
        if duration_target:
            self._apply_duration_penalty(candidates, duration_target, is_hard)
        return candidates

    def _apply_usage_boost(self, candidates: list[Candidate], db: Any) -> None:
        for c in candidates:
            channels = db.get_performance_channels(c.content_id)
            rhdp = next((ch for ch in (channels or []) if ch.get("channel") == "rhdp"), None)
            if rhdp:
                wm = rhdp.get("windowed_metrics") or {}
                q_data = wm.get("3m") or {}
                c.type_data["provisions_quarter"] = q_data.get("provisions")
            else:
                c.type_data["provisions_quarter"] = None

        prov_values = [c.type_data.get("provisions_quarter") for c in candidates
                       if c.type_data.get("provisions_quarter") and c.type_data["provisions_quarter"] > 0]
        if not prov_values:
            return
        sorted_provs = sorted(prov_values)

        for c in candidates:
            pq = c.type_data.get("provisions_quarter")
            if c.relevance_score is None or not pq or pq <= 0:
                continue
            pct = (bisect.bisect_right(sorted_provs, pq) / len(sorted_provs)) * 100
            if pct >= 90:
                multiplier = 1.12
            elif pct >= 75:
                multiplier = 1.09
            elif pct >= 50:
                multiplier = 1.06
            else:
                multiplier = 1.03
            old_score = c.relevance_score
            c.relevance_score = max(0, min(100, round(old_score * multiplier)))
            log.debug("usage_boost", content_id=c.content_id,
                      provisions_quarter=pq, percentile=round(pct),
                      multiplier=multiplier, old_score=old_score, new_score=c.relevance_score)

    def _apply_duration_penalty(self, candidates: list[Candidate], target_min: int, hard: bool) -> None:
        for c in candidates:
            dur = c.type_data.get("duration_min")
            if c.relevance_score is None or dur is None:
                continue
            if c.type_data.get("duration_source") != "curated":
                continue
            if dur <= target_min:
                continue
            ratio = dur / target_min
            coeff = 0.15 if hard else 0.08
            floor = 0.6 if hard else 0.7
            multiplier = max(floor, 1.0 - coeff * math.log(ratio))
            old_score = c.relevance_score
            c.relevance_score = max(0, min(100, round(old_score * multiplier)))
            log.debug("duration_penalty", content_id=c.content_id,
                      duration=dur, target=target_min,
                      ratio=round(ratio, 1), multiplier=round(multiplier, 2),
                      old_score=old_score, new_score=c.relevance_score)

    def serialize(self, candidate: Candidate, include_performance: bool = False, db: Any | None = None) -> dict:
        td = candidate.type_data
        result = {
            "content_id": candidate.content_id,
            "content_type": candidate.content_type,
            "display_name": candidate.display_name,
            "tier": candidate.tier,
            "relevance_score": candidate.relevance_score,
            "vector_similarity_pct": candidate.vector_similarity_pct,
            "status": candidate.status,
            "why_it_fits": candidate.why_it_fits,
            "how_to_use": candidate.how_to_use,
            "caveats": candidate.caveats,
            "ci_name": td.get("ci_name"),
            "stage": td.get("stage", candidate.status),
            "catalog_namespace": td.get("catalog_namespace", ""),
            "duration_min": td.get("duration_min"),
            "duration_source": td.get("duration_source"),
            "learning_objectives": td.get("learning_objectives", []),
            "suggested_format": td.get("suggested_format"),
            "duration_notes": td.get("duration_notes"),
            "provisions_quarter": td.get("provisions_quarter"),
            "display": self._build_display(candidate),
        }
        if include_performance and db:
            self._attach_performance(result, candidate.content_id, db)
        return result

    def _build_display(self, candidate: Candidate) -> dict:
        td = candidate.type_data
        fmt = td.get("suggested_format", "hands_on_lab" if candidate.content_type == "lab" else candidate.content_type)
        config = self.display_config()
        config["format_badge"] = {"label": _FORMAT_LABELS.get(fmt, fmt.replace("_", " ").title()), "key": fmt}
        if td.get("duration_min"):
            source = "Curated duration" if td.get("duration_source") == "curated" else "AI duration estimate"
            config["header_right"] = {"value": f"~{td['duration_min']} min", "tooltip": source}
        return config

    def _attach_performance(self, result: dict, content_id: str, db: Any) -> None:
        from rcars.services.reporting_sync import compute_sales_impact
        channels = db.get_performance_channels(content_id)
        rhdp = next((ch for ch in (channels or []) if ch.get("channel") == "rhdp"), None)
        if rhdp:
            wm = rhdp.get("windowed_metrics") or {}
            if isinstance(wm, str):
                wm = json.loads(wm)
            q = wm.get("3m", {})
            result["provisions_quarter"] = q.get("provisions", 0)
            result["avg_cost_per_provision"] = float(rhdp.get("avg_cost_per_provision") or 0)
            result["sales_impact"] = compute_sales_impact(float(rhdp.get("closed_amount") or 0))
        else:
            result["avg_cost_per_provision"] = None
            result["sales_impact"] = None

    def display_config(self) -> dict:
        return {
            "detail_rows": [
                {"label": "Why it fits", "field": "why_it_fits"},
                {"label": "Objectives", "field": "learning_objectives", "type": "list", "max": 5},
                {"label": "How to use", "field": "how_to_use"},
            ],
            "footer_metrics": [
                {"label": "deployments (last 90d)", "field": "provisions_quarter"},
                {"label": "sales_impact", "field": "sales_impact", "type": "badge"},
            ],
            "links": [
                {"label": "View in RHDP Catalog", "url_template": "catalog"},
                {"label": "View in RCARS", "url_template": "browse"},
            ],
        }
