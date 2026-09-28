"""Driver for hands-on content: labs, demos, sandboxes."""

from __future__ import annotations

from typing import Any

from rcars.services.recommender.drivers.base import ContentTypeDriver
from rcars.services.recommender.models import Candidate


class HandsOnDriver(ContentTypeDriver):

    @property
    def content_types(self) -> list[str]:
        return ["lab", "demo", "sandbox"]

    @property
    def category_key(self) -> str:
        return "hands_on"

    def fetch_analysis(self, db: Any, candidate: Candidate) -> dict:
        raise NotImplementedError

    def triage_guidance(self) -> str:
        return ""

    def format_for_rationale(self, candidate: Candidate, analysis: dict) -> str:
        raise NotImplementedError

    def post_triage(self, candidates: list[Candidate], query: str, db: Any) -> list[Candidate]:
        return candidates

    def serialize(self, candidate: Candidate, include_performance: bool = False, db: Any | None = None) -> dict:
        raise NotImplementedError

    def display_config(self) -> dict:
        raise NotImplementedError
