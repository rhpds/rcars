"""Abstract base class for content-type drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from rcars.services.recommender.models import Candidate


class ContentTypeDriver(ABC):

    @property
    @abstractmethod
    def content_types(self) -> list[str]:
        """Content type strings this driver handles."""

    @property
    @abstractmethod
    def category_key(self) -> str:
        """Short key for SSE category labels and frontend tab grouping."""

    @abstractmethod
    def fetch_analysis(self, db: Any, candidate: Candidate) -> dict:
        """Fetch full analysis data for the rationale prompt."""

    @abstractmethod
    def triage_guidance(self) -> str:
        """Extra text injected into the triage prompt for this type."""

    @abstractmethod
    def format_for_rationale(self, candidate: Candidate, analysis: dict) -> str:
        """Format one candidate with analysis data for the rationale LLM call."""

    @abstractmethod
    def post_triage(self, candidates: list[Candidate], query: str, db: Any) -> list[Candidate]:
        """Type-specific adjustments after triage."""

    @abstractmethod
    def serialize(self, candidate: Candidate, include_performance: bool = False, db: Any | None = None) -> dict:
        """Convert candidate to JSON for frontend. Includes display config."""

    @abstractmethod
    def display_config(self) -> dict:
        """Static display configuration for the frontend card renderer."""
