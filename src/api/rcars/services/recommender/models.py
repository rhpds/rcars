"""Data models for the recommendation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Candidate:
    """A content entity moving through the recommendation pipeline."""

    # Universal — present in content_entities for all types
    content_id: str
    display_name: str
    content_type: str
    source: str
    summary: str
    products: list[str]
    topics: list[str]
    status: str = "prod"
    difficulty: str | None = None
    is_hands_on: bool = True

    # Pipeline state — set by pipeline phases, universal
    tier: str = "white"
    vector_distance: float = 0.0
    vector_similarity_pct: int = 0
    relevance_score: int | None = None
    one_line_reason: str | None = None

    # Rationale — set by Phase 3, same structure for all types
    why_it_fits: str | None = None
    how_to_use: str | None = None
    caveats: str | None = None

    # Type-specific — populated by vector_search and driver hooks
    type_data: dict = field(default_factory=dict)

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
    timings: dict[str, float] = field(default_factory=dict)
    token_usage: list[dict] = field(default_factory=list)
