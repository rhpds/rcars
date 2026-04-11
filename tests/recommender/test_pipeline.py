"""Tests for the three-phase pipeline orchestrator."""

from unittest.mock import MagicMock, patch

from rcars.recommender.pipeline import run_query
from rcars.recommender.models import Candidate, QueryState
from rcars.config import Settings


def _mock_settings():
    s = MagicMock(spec=Settings)
    s.vector_cutoff = 0.55
    s.triage_model = "claude-haiku-4-5"
    s.triage_cutoff = 30
    s.rationale_model = "claude-sonnet-4-6"
    s.rationale_top_n = 5
    return s


def _make_vector_state(n_candidates=3):
    candidates = [
        Candidate(
            ci_name=f"ci-{i}", display_name=f"CI {i}", category="workshop",
            summary=f"Summary {i}", topics=["openshift"], products=["OCP"],
            difficulty="beginner", duration_min=60, content_type="workshop",
            vector_distance=0.3, vector_similarity_pct=85,
        )
        for i in range(n_candidates)
    ]
    return QueryState(phase="VECTOR_DONE", candidates=candidates, query="test query")


@patch("rcars.recommender.pipeline.generate_rationale")
@patch("rcars.recommender.pipeline.triage_phase")
@patch("rcars.recommender.pipeline.vector_search")
def test_pipeline_yields_three_states(mock_vs, mock_triage, mock_rationale):
    vector_state = _make_vector_state(3)
    triage_state = QueryState(
        phase="TRIAGE_DONE", candidates=vector_state.candidates[:2], query="test query",
    )
    complete_state = QueryState(
        phase="COMPLETE", candidates=triage_state.candidates, query="test query",
        overall_assessment="Assessment.",
    )

    mock_vs.return_value = vector_state
    mock_triage.return_value = triage_state
    mock_rationale.return_value = complete_state

    settings = _mock_settings()
    states = list(run_query("test query", MagicMock(), MagicMock(), settings))

    assert len(states) == 3
    assert states[0].phase == "VECTOR_DONE"
    assert states[1].phase == "TRIAGE_DONE"
    assert states[2].phase == "COMPLETE"


@patch("rcars.recommender.pipeline.vector_search")
def test_pipeline_stops_at_no_matches_phase1(mock_vs):
    mock_vs.return_value = QueryState(phase="NO_MATCHES", candidates=[], query="test")

    settings = _mock_settings()
    states = list(run_query("bad query", MagicMock(), MagicMock(), settings))

    assert len(states) == 1
    assert states[0].phase == "NO_MATCHES"


@patch("rcars.recommender.pipeline.triage_phase")
@patch("rcars.recommender.pipeline.vector_search")
def test_pipeline_stops_at_no_matches_phase2(mock_vs, mock_triage):
    mock_vs.return_value = _make_vector_state(2)
    mock_triage.return_value = QueryState(phase="NO_MATCHES", candidates=[], query="test")

    settings = _mock_settings()
    states = list(run_query("filtered query", MagicMock(), MagicMock(), settings))

    assert len(states) == 2
    assert states[0].phase == "VECTOR_DONE"
    assert states[1].phase == "NO_MATCHES"
