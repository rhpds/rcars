"""Tests for Phase 3 — Sonnet rationale generation."""

import json
from unittest.mock import MagicMock

from rcars.recommender.rationale import generate_rationale, format_rationale_candidates
from rcars.recommender.models import Candidate, QueryState


def _candidate(ci_name, relevance_score=85):
    return Candidate(
        ci_name=ci_name,
        display_name=ci_name.replace("-", " ").title(),
        category="workshop",
        summary=f"Workshop about {ci_name}",
        topics=["openshift"],
        products=["OCP"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
        vector_distance=0.3,
        vector_similarity_pct=85,
        relevance_score=relevance_score,
        relevant=True,
        one_line_reason="Good match",
    )


def _mock_analysis():
    return {
        "content_type": "workshop",
        "summary": "A workshop",
        "difficulty": "beginner",
        "estimated_duration_min": 60,
        "topics_json": ["openshift"],
        "products_json": ["OCP"],
        "audience_json": ["developers"],
        "learning_objectives_json": {"stated": ["Learn OCP"], "inferred": []},
        "event_fit_json": {"summit": "good"},
        "modules_json": [{"title": "Module 1", "topics": ["basics"]}],
    }


def _mock_client(response_json, input_tokens=40000, output_tokens=3500):
    client = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps(response_json)
    response = MagicMock()
    response.content = [content_block]
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    client.messages.create.return_value = response
    return client


def _mock_db():
    db = MagicMock()
    db.get_showroom_analysis.return_value = _mock_analysis()
    return db


def test_generate_rationale_enriches_candidates():
    candidates = [_candidate("good-ci")]
    state = QueryState(phase="TRIAGE_DONE", candidates=candidates, query="openshift workshop")

    sonnet_response = {
        "recommendations": [
            {
                "ci_name": "good-ci",
                "rationale": "This workshop covers core OpenShift concepts.",
                "suggested_format": "hands_on_lab",
                "duration_notes": "90 min full, 45 min abbreviated",
                "caveats": "",
            }
        ],
        "overall_assessment": "**Top Pick:** good-ci covers the request well.",
        "content_gaps": [],
    }
    client = _mock_client(sonnet_response)
    db = _mock_db()

    result = generate_rationale(state, db, client, top_n=5)

    assert result.phase == "COMPLETE"
    assert result.candidates[0].rationale == "This workshop covers core OpenShift concepts."
    assert result.candidates[0].suggested_format == "hands_on_lab"
    assert result.candidates[0].duration_notes == "90 min full, 45 min abbreviated"
    assert result.overall_assessment == "**Top Pick:** good-ci covers the request well."
    assert result.content_gaps == []
    assert "rationale" in result.timings


def test_generate_rationale_limits_to_top_n():
    candidates = [_candidate(f"ci-{i}", 90 - i * 10) for i in range(6)]
    state = QueryState(phase="TRIAGE_DONE", candidates=candidates, query="test")

    sonnet_response = {
        "recommendations": [
            {"ci_name": f"ci-{i}", "rationale": f"Analysis {i}",
             "suggested_format": "hands_on_lab", "duration_notes": "", "caveats": ""}
            for i in range(3)
        ],
        "overall_assessment": "Assessment.",
        "content_gaps": [],
    }
    client = _mock_client(sonnet_response)
    db = _mock_db()

    result = generate_rationale(state, db, client, top_n=3)

    # All 6 candidates should be in the result
    assert len(result.candidates) == 6
    # Only top 3 should have rationale
    with_rationale = [c for c in result.candidates if c.rationale is not None]
    assert len(with_rationale) == 3


def test_format_rationale_candidates_includes_full_analysis():
    c = _candidate("test-ci")
    analysis = _mock_analysis()
    text = format_rationale_candidates([c], {"test-ci": analysis})
    assert "test-ci" in text
    assert "Learn OCP" in text
    assert "Module 1" in text


def test_generate_rationale_captures_token_usage():
    """Returned QueryState should carry rationale token entry."""
    candidates = [_candidate("good-ci")]
    state = QueryState(phase="TRIAGE_DONE", candidates=candidates, query="openshift")

    sonnet_response = {
        "recommendations": [
            {"ci_name": "good-ci", "rationale": "Good match.",
             "suggested_format": "hands_on_lab", "duration_notes": "", "caveats": ""},
        ],
        "overall_assessment": "Good.",
        "content_gaps": [],
    }
    client = _mock_client(sonnet_response, input_tokens=40000, output_tokens=3500)
    db = _mock_db()

    result = generate_rationale(state, db, client, model="claude-sonnet-4-6", top_n=5)

    assert len(result.token_usage) == 1
    entry = result.token_usage[0]
    assert entry["operation"] == "rationale"
    assert entry["model"] == "claude-sonnet-4-6"
    assert entry["input_tokens"] == 40000
    assert entry["output_tokens"] == 3500


def test_generate_rationale_carries_forward_token_usage():
    """Prior token_usage entries should be preserved in returned state."""
    prior = {
        "operation": "triage", "model": "claude-haiku-4-5",
        "input_tokens": 1200, "output_tokens": 300,
    }
    candidates = [_candidate("good-ci")]
    state = QueryState(
        phase="TRIAGE_DONE", candidates=candidates,
        query="openshift", token_usage=[prior],
    )

    sonnet_response = {
        "recommendations": [
            {"ci_name": "good-ci", "rationale": "Matches well.",
             "suggested_format": "hands_on_lab", "duration_notes": "", "caveats": ""},
        ],
        "overall_assessment": "Good.",
        "content_gaps": [],
    }
    client = _mock_client(sonnet_response)
    db = _mock_db()

    result = generate_rationale(state, db, client, model="claude-sonnet-4-6", top_n=5)

    assert len(result.token_usage) == 2
    assert result.token_usage[0]["operation"] == "triage"
    assert result.token_usage[1]["operation"] == "rationale"
