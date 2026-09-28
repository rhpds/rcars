"""Driver for portfolio architecture content."""

from __future__ import annotations

from typing import Any

import structlog

from rcars.services.recommender.drivers.base import ContentTypeDriver
from rcars.services.recommender.models import Candidate

log = structlog.get_logger()

ASSET_TYPE_LABELS = {
    "VP": "Validated Pattern",
    "SP": "Solution Pattern",
    "PA": "Portfolio Architecture",
}


def _primary_asset_type(raw: str | None) -> str:
    tokens = [t.strip().upper() for t in str(raw or "").split(",") if t.strip()]
    for candidate in ("VP", "SP", "PA"):
        if candidate in tokens:
            return candidate
    return ""


class ArchitectureDriver(ContentTypeDriver):

    @property
    def content_types(self) -> list[str]:
        return ["architecture"]

    @property
    def category_key(self) -> str:
        return "architecture"

    def fetch_analysis(self, db: Any, candidate: Candidate) -> dict:
        return db.get_architecture_analysis(candidate.content_id) or {}

    def triage_guidance(self) -> str:
        return (
            "Architecture content (Validated Patterns, Solution Patterns, Portfolio Architectures) "
            "has no duration and cannot be provisioned. Ignore the Duration field for architecture "
            "candidates. Evaluate based on topic relevance, solution areas, and use cases."
        )

    def format_for_rationale(self, candidate: Candidate, analysis: dict) -> str:
        lines = [
            f"Content ID: {candidate.content_id}",
            f"Display Name: {candidate.display_name}",
            f"Content Type: {candidate.content_type}",
            f"Relevance Score: {candidate.relevance_score or 0}%",
            f"Summary: {candidate.summary}",
            f"Difficulty: {candidate.difficulty}",
            f"Topics: {', '.join(candidate.topics)}",
            f"Products: {', '.join(candidate.products)}",
        ]
        asset = _primary_asset_type(analysis.get("asset_type"))
        lines.append(f"Asset Type: {ASSET_TYPE_LABELS.get(asset, 'Architecture')}")
        audience = analysis.get("audience_json", [])
        if audience:
            lines.append(f"Audience: {', '.join(audience)}")
        for key, label in (("solution_areas_json", "Solution Areas"),
                           ("use_cases_json", "Use Cases"),
                           ("key_components_json", "Key Components")):
            values = analysis.get(key) or []
            if values:
                lines.append(f"{label}: {'; '.join(str(v) for v in values)}")
        return "\n".join(lines)

    def post_triage(self, candidates: list[Candidate], query: str, db: Any) -> list[Candidate]:
        return candidates

    def serialize(self, candidate: Candidate, include_performance: bool = False, db: Any | None = None) -> dict:
        return {
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
            "provisions_quarter": None,
            "sales_impact": None,
            "display": self._build_display(candidate),
        }

    def _build_display(self, candidate: Candidate) -> dict:
        config = self.display_config()
        asset = candidate.type_data.get("asset_type", "")
        primary = _primary_asset_type(asset)
        config["format_badge"] = {
            "label": ASSET_TYPE_LABELS.get(primary, "Architecture"),
            "key": f"architecture_{primary.lower()}" if primary else "architecture",
        }
        return config

    def display_config(self) -> dict:
        return {
            "detail_rows": [
                {"label": "Why it fits", "field": "why_it_fits"},
                {"label": "How to use", "field": "how_to_use"},
            ],
            "links": [
                {"label": "View in RCARS", "url_template": "browse"},
            ],
        }
