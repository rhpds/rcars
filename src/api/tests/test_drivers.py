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


# --- Task 3: HandsOnDriver tests ---

from rcars.services.recommender.drivers.hands_on import HandsOnDriver


def _make_hands_on_candidate(**overrides) -> Candidate:
    defaults = dict(
        content_id="babylon:test-lab",
        display_name="Test Lab",
        content_type="lab",
        source="babylon",
        summary="A test lab about OpenShift",
        products=["OpenShift"],
        topics=["containers"],
        type_data={
            "ci_name": "test-lab",
            "stage": "prod",
            "catalog_namespace": "babylon-catalog-prod",
            "base_ci_name": None,
            "duration_min": 120,
            "duration_source": "curated",
            "learning_objectives": ["Deploy an app"],
            "category": "Hands-on Lab",
        },
    )
    defaults.update(overrides)
    return Candidate(**defaults)


def test_hands_on_triage_guidance():
    driver = HandsOnDriver()
    guidance = driver.triage_guidance()
    assert guidance == ""


def test_hands_on_format_for_rationale():
    driver = HandsOnDriver()
    c = _make_hands_on_candidate()
    analysis = {
        "audience_json": ["developers"],
        "learning_objectives_json": {"stated": ["Deploy an app"], "inferred": []},
        "modules_json": [{"title": "Setup"}, {"title": "Deploy"}],
    }
    text = driver.format_for_rationale(c, analysis)
    assert "Test Lab" in text
    assert "Duration: 120 min" in text
    assert "Deploy an app" in text


def test_hands_on_serialize_streaming():
    driver = HandsOnDriver()
    c = _make_hands_on_candidate(relevance_score=85, tier="yellow")
    result = driver.serialize(c)
    assert result["content_id"] == "babylon:test-lab"
    assert result["content_type"] == "lab"
    assert "display" in result
    assert result["display"]["format_badge"]["key"] in ("hands_on_lab", "lab")


def test_hands_on_serialize_with_performance():
    from unittest.mock import MagicMock
    driver = HandsOnDriver()
    c = _make_hands_on_candidate(relevance_score=85, tier="green")
    mock_db = MagicMock()
    mock_db.get_performance_channels.return_value = [{
        "channel": "rhdp",
        "windowed_metrics": {"3m": {"provisions": 42}},
        "avg_cost_per_provision": "15.50",
        "closed_amount": "50000",
    }]
    result = driver.serialize(c, include_performance=True, db=mock_db)
    assert result["provisions_quarter"] == 42
    assert result["sales_impact"] is not None


def test_hands_on_display_config():
    driver = HandsOnDriver()
    config = driver.display_config()
    assert "format_badge" not in config  # format_badge is built dynamically
    assert "detail_rows" in config
