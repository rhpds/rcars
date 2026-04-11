"""Tests for Phase 2 — Haiku triage."""

import json
from unittest.mock import MagicMock

from rcars.recommender.triage import triage, format_triage_candidates
from rcars.recommender.models import Candidate, QueryState


def _candidate(ci_name, summary="A workshop", topics=None):
    return Candidate(
        ci_name=ci_name,
        display_name=ci_name.replace("-", " ").title(),
        category="workshop",
        summary=summary,
        topics=topics or ["openshift"],
        products=["OCP"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
        vector_distance=0.3,
        vector_similarity_pct=85,
    )


def _mock_client(response_json):
    client = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps(response_json)
    response = MagicMock()
    response.content = [content_block]
    client.messages.create.return_value = response
    return client


def test_triage_filters_irrelevant_candidates():
    candidates = [_candidate("good-ci"), _candidate("bad-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="ansible workshop")

    haiku_response = [
        {"ci_name": "good-ci", "relevance_score": 85, "relevant": True,
         "one_line_reason": "Direct Ansible match"},
        {"ci_name": "bad-ci", "relevance_score": 15, "relevant": False,
         "one_line_reason": "No Ansible content"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert result.phase == "TRIAGE_DONE"
    assert len(result.candidates) == 1
    assert result.candidates[0].ci_name == "good-ci"
    assert result.candidates[0].relevance_score == 85
    assert result.candidates[0].one_line_reason == "Direct Ansible match"
    assert "triage" in result.timings


def test_triage_all_irrelevant_returns_no_matches():
    candidates = [_candidate("bad-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="ansible")

    haiku_response = [
        {"ci_name": "bad-ci", "relevance_score": 10, "relevant": False,
         "one_line_reason": "No match"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert result.phase == "NO_MATCHES"
    assert len(result.candidates) == 0


def test_triage_sorts_by_relevance_score():
    candidates = [_candidate("b-ci"), _candidate("a-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="test")

    haiku_response = [
        {"ci_name": "b-ci", "relevance_score": 60, "relevant": True,
         "one_line_reason": "Partial match"},
        {"ci_name": "a-ci", "relevance_score": 90, "relevant": True,
         "one_line_reason": "Strong match"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert result.candidates[0].ci_name == "a-ci"
    assert result.candidates[1].ci_name == "b-ci"


def test_format_triage_candidates_compact():
    c = _candidate("test-ci", summary="Learn OpenShift basics", topics=["openshift", "containers"])
    text = format_triage_candidates([c])
    assert "test-ci" in text
    assert "Learn OpenShift basics" in text
    assert "openshift" in text
    assert "objectives" not in text.lower()


def test_triage_handles_missing_ci_in_response():
    candidates = [_candidate("a-ci"), _candidate("b-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="test")

    haiku_response = [
        {"ci_name": "a-ci", "relevance_score": 80, "relevant": True,
         "one_line_reason": "Good match"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert len(result.candidates) == 1
    assert result.candidates[0].ci_name == "a-ci"
