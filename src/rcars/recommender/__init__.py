"""RCARS recommendation engine — three-phase pipeline.

Public API:
    run_query()  — generator yielding QueryState after each phase
    QueryState   — pipeline state at a phase boundary
    Candidate    — a catalog item moving through the pipeline
"""

from rcars.recommender.models import Candidate, QueryState
from rcars.recommender.pipeline import run_query

__all__ = ["run_query", "QueryState", "Candidate"]
