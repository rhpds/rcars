"""Data models for the recommendation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Candidate:
    """A catalog item moving through the recommendation pipeline."""

    ci_name: str
    display_name: str
    category: str
    summary: str
    topics: list[str]
    products: list[str]
    difficulty: str
    duration_min: int | None
    content_type: str
    stage: str = "prod"
    duration_source: str = "ai"  # "curated" | "ai"
    catalog_namespace: str = ""
    learning_objectives: list[str] = field(default_factory=list)
    tier: str = "white"  # white | yellow | green — set by pipeline phases
    vector_distance: float = 0.0
    vector_similarity_pct: int = 0

    # Populated between vector search and triage (from reporting_metrics)
    provisions_quarter: int | None = None

    # Populated after Phase 2 (Haiku triage)
    relevance_score: int | None = None
    relevant: bool | None = None
    one_line_reason: str | None = None

    # Populated after Phase 3 (Sonnet rationale)
    rationale: str | None = None
    why_it_fits: str | None = None
    how_to_use: str | None = None
    suggested_format: str | None = None
    duration_notes: str | None = None
    caveats: str | None = None

    @staticmethod
    def similarity_pct(distance: float) -> int:
        """Convert cosine distance to similarity percentage."""
        return round((1 - distance / 2) * 100)


@dataclass
class QueryState:
    """State of a recommendation query at a pipeline phase boundary."""

    phase: str  # SUBMITTED | VECTOR_DONE | TRIAGE_DONE | COMPLETE | NO_MATCHES
    candidates: list[Candidate]
    query: str = ""
    overall_assessment: str | None = None
    content_gaps: list[str] | None = None
    timings: dict[str, float] = field(default_factory=dict)
    token_usage: list[dict] = field(default_factory=list)
