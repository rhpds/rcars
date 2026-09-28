"""Tests for content-type drivers and refactored models."""

from rcars.services.recommender.models import Candidate, QueryState


def test_candidate_universal_fields():
    c = Candidate(
        content_id="babylon:test-ci",
        display_name="Test Lab",
        content_type="lab",
        source="babylon",
        summary="A test lab",
        products=["OpenShift"],
        topics=["containers"],
    )
    assert c.status == "prod"
    assert c.is_hands_on is True
    assert c.tier == "white"
    assert c.type_data == {}


def test_candidate_with_type_data():
    c = Candidate(
        content_id="babylon:test-ci",
        display_name="Test Lab",
        content_type="lab",
        source="babylon",
        summary="A test lab",
        products=["OpenShift"],
        topics=["containers"],
        type_data={"ci_name": "test-ci", "duration_min": 120, "duration_source": "curated"},
    )
    assert c.type_data["ci_name"] == "test-ci"
    assert c.type_data["duration_min"] == 120


def test_query_state_no_grouped_results():
    qs = QueryState(phase="COMPLETE", candidates=[])
    assert not hasattr(qs, "grouped_results") or "grouped_results" not in qs.__dataclass_fields__
