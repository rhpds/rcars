"""Tests for recommendation engine."""

from rcars.recommender import format_candidate


def test_format_candidate_basic():
    """Should format a basic candidate."""
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Test Item",
        "category": "Demos",
        "product": "OpenShift",
        "stage": "prod",
    }
    result = format_candidate(item, None)
    assert "test.item.prod" in result
    assert "Test Item" in result
    assert "Demos" in result


def test_format_candidate_with_analysis():
    """Should include analysis details."""
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Test Item",
        "category": "Demos",
        "product": "OpenShift",
        "stage": "prod",
    }
    analysis = {
        "content_type": "workshop",
        "summary": "A great workshop",
        "difficulty": "beginner",
        "estimated_duration_min": 60,
        "topics_json": ["kubernetes", "operators"],
        "products_json": ["OpenShift"],
        "audience_json": ["developers"],
        "learning_objectives_json": {
            "stated": ["Learn K8s"],
            "inferred": ["Understand operators"],
        },
    }
    result = format_candidate(item, analysis)
    assert "workshop" in result
    assert "beginner" in result
    assert "60 min" in result
    assert "Learn K8s" in result
    assert "Understand operators" in result


def test_format_candidate_published_vci():
    """Should note published VCI type."""
    item = {
        "ci_name": "published.test.prod",
        "display_name": "Test",
        "category": "Demos",
        "product": "OpenShift",
        "stage": "prod",
        "is_published": True,
        "base_ci_name": "openshift-cnv.test.prod",
    }
    result = format_candidate(item, None)
    assert "Virtual CI" in result
