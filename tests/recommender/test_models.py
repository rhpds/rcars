"""Tests for recommender data models."""

from rcars.recommender.models import Candidate, QueryState


def test_candidate_defaults():
    c = Candidate(
        ci_name="test-ci",
        display_name="Test CI",
        category="workshop",
        summary="A test workshop",
        topics=["openshift"],
        products=["OCP"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
        vector_distance=0.3,
        vector_similarity_pct=85,
    )
    assert c.ci_name == "test-ci"
    assert c.vector_similarity_pct == 85
    assert c.relevance_score is None
    assert c.relevant is None
    assert c.one_line_reason is None
    assert c.rationale is None
    assert c.suggested_format is None
    assert c.duration_notes is None
    assert c.caveats is None


def test_candidate_vector_similarity_calculation():
    assert Candidate.similarity_pct(0.0) == 100
    assert Candidate.similarity_pct(0.55) == 72
    assert Candidate.similarity_pct(1.0) == 50


def test_query_state_defaults():
    state = QueryState(phase="SUBMITTED", candidates=[])
    assert state.phase == "SUBMITTED"
    assert state.candidates == []
    assert state.overall_assessment is None
    assert state.content_gaps is None
    assert state.timings == {}


def test_query_state_with_candidates():
    c = Candidate(
        ci_name="x", display_name="X", category="demo",
        summary="s", topics=[], products=[], difficulty="",
        duration_min=None, content_type="demo",
        vector_distance=0.4, vector_similarity_pct=80,
    )
    state = QueryState(phase="VECTOR_DONE", candidates=[c])
    assert len(state.candidates) == 1
    assert state.candidates[0].ci_name == "x"
