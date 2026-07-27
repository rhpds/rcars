"""Data models for the recommendation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Candidate:
    """A content entity moving through the recommendation pipeline."""

    content_id: str
    display_name: str
    category: str
    summary: str
    topics: list[str]
    products: list[str]
    difficulty: str
    duration_min: int | None
    content_type: str
    ci_name: str | None = None  # nullable for future non-Babylon content
    source: str = "babylon"
    is_hands_on: bool = True
    best_match_type: str = ""
    best_match_detail: str | None = None
    stage: str = "prod"
    duration_source: str = "ai"  # "curated" | "ai"
    catalog_namespace: str = ""
    base_ci_name: str | None = None
    learning_objectives: list[str] = field(default_factory=list)
    tier: str = "white"  # white | yellow | green — set by pipeline phases
    vector_distance: float = 0.0
    vector_similarity_pct: int = 0

    # Populated between vector search and triage (from performance_channels)
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
    def from_similarity(similarity: float) -> int:
        """Convert similarity score (0.0-1.0) to percentage."""
        return round(similarity * 100)


@dataclass
class QueryState:
    """State of a recommendation query at a pipeline phase boundary."""

    phase: str  # SUBMITTED | VECTOR_DONE | TRIAGE_DONE | COMPLETE | NO_MATCHES
    candidates: list[Candidate]
    query: str = ""
    overall_assessment: str | None = None
    content_gaps: list[str] | None = None
    grouped_results: dict | None = None  # Phase 2: typed grouping by content_type
    timings: dict[str, float] = field(default_factory=dict)
    token_usage: list[dict] = field(default_factory=list)
