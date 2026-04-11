"""Tests for progressive advisor query flow."""

from rcars.recommender.models import Candidate, QueryState
from rcars.web.routes.advisor import _candidates_to_recs


def _candidate(ci_name, **kwargs):
    defaults = dict(
        ci_name=ci_name,
        display_name=ci_name.replace("-", " ").title(),
        category="workshop",
        summary=f"Summary for {ci_name}",
        topics=["openshift"],
        products=["OCP"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
        vector_distance=0.3,
        vector_similarity_pct=85,
    )
    defaults.update(kwargs)
    return Candidate(**defaults)


def test_candidates_to_recs_vector_phase():
    candidates = [_candidate("test-ci")]
    recs = _candidates_to_recs(candidates, "vector")

    assert len(recs) == 1
    assert recs[0]["ci_name"] == "test-ci"
    assert recs[0]["fit_score"] == 85  # vector_similarity_pct
    assert recs[0]["card_phase"] == "vector"
    assert recs[0]["summary"] == "Summary for test-ci"


def test_candidates_to_recs_triaged_phase():
    c = _candidate("test-ci", relevance_score=90, one_line_reason="Great match")
    recs = _candidates_to_recs([c], "triaged")

    assert recs[0]["fit_score"] == 90  # relevance_score takes precedence
    assert recs[0]["card_phase"] == "triaged"
    assert recs[0]["one_line_reason"] == "Great match"


def test_candidates_to_recs_complete_phase():
    c = _candidate(
        "test-ci",
        relevance_score=90,
        rationale="This is a great workshop.",
        suggested_format="hands_on_lab",
    )
    recs = _candidates_to_recs([c], "complete")

    assert recs[0]["card_phase"] == "complete"  # rationale present overrides
    assert recs[0]["rationale"] == "This is a great workshop."
