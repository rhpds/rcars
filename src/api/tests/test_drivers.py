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


from rcars.services.recommender.drivers import get_driver, get_drivers_for_types
from rcars.services.recommender.drivers.base import ContentTypeDriver


def test_get_driver_lab():
    driver = get_driver("lab")
    assert isinstance(driver, ContentTypeDriver)
    assert "lab" in driver.content_types


def test_get_driver_architecture():
    driver = get_driver("architecture")
    assert isinstance(driver, ContentTypeDriver)
    assert "architecture" in driver.content_types


def test_get_drivers_for_types_groups():
    drivers = get_drivers_for_types(["lab", "demo", "architecture"])
    assert len(drivers) == 2


def test_get_driver_unknown_raises():
    import pytest
    with pytest.raises(KeyError):
        get_driver("unknown_type")
