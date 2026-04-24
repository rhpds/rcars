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


def _mock_client(response_json, input_tokens=1000, output_tokens=200):
    client = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps(response_json)
    response = MagicMock()
    response.content = [content_block]
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    client.messages.create.return_value = response
    return client


def test_triage_filters_irrelevant_candidates():
    """Irrelevant candidates are kept but marked white; relevant ones are yellow."""
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
    assert len(result.candidates) == 2  # all kept
    by_ci = {c.ci_name: c for c in result.candidates}
    assert by_ci["good-ci"].tier == "yellow"
    assert by_ci["good-ci"].relevance_score == 85
    assert by_ci["good-ci"].one_line_reason == "Direct Ansible match"
    assert by_ci["bad-ci"].tier == "white"
    assert "triage" in result.timings
    # Yellow before white in sort order
    assert result.candidates[0].ci_name == "good-ci"


def test_triage_all_irrelevant_returns_no_matches():
    """NO_MATCHES when zero relevant — white candidates still returned."""
    candidates = [_candidate("bad-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="ansible")

    haiku_response = [
        {"ci_name": "bad-ci", "relevance_score": 10, "relevant": False,
         "one_line_reason": "No match"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert result.phase == "NO_MATCHES"
    assert len(result.candidates) == 1  # still returned as white
    assert result.candidates[0].tier == "white"


def test_triage_sorts_by_relevance_score():
    """Yellow candidates sorted by relevance score desc; white candidates after."""
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

    # Both yellow — sorted by relevance score desc
    assert result.candidates[0].ci_name == "a-ci"
    assert result.candidates[0].tier == "yellow"
    assert result.candidates[1].ci_name == "b-ci"
    assert result.candidates[1].tier == "yellow"


def test_format_triage_candidates_compact():
    c = _candidate("test-ci", summary="Learn OpenShift basics", topics=["openshift", "containers"])
    text = format_triage_candidates([c])
    assert "test-ci" in text
    assert "Learn OpenShift basics" in text
    assert "openshift" in text
    assert "objectives" not in text.lower()


def test_triage_handles_missing_ci_in_response():
    """Candidates missing from Haiku response are kept as white tier."""
    candidates = [_candidate("a-ci"), _candidate("b-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="test")

    haiku_response = [
        {"ci_name": "a-ci", "relevance_score": 80, "relevant": True,
         "one_line_reason": "Good match"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert len(result.candidates) == 2  # b-ci kept as white
    by_ci = {c.ci_name: c for c in result.candidates}
    assert by_ci["a-ci"].tier == "yellow"
    assert by_ci["b-ci"].tier == "white"


def test_triage_keeps_all_candidates():
    """Triage should keep ALL candidates — relevant ones as yellow, others as white."""
    candidates = [_candidate("lab/a"), _candidate("lab/b")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="test")

    haiku_response = [
        {"ci_name": "lab/a", "relevance_score": 80, "relevant": True,
         "one_line_reason": "fits"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert result.phase == "TRIAGE_DONE"
    assert len(result.candidates) == 2
    by_ci = {c.ci_name: c for c in result.candidates}
    assert by_ci["lab/a"].tier == "yellow"
    assert by_ci["lab/a"].relevance_score == 80
    assert by_ci["lab/b"].tier == "white"
    assert by_ci["lab/b"].relevance_score is None


def test_triage_no_matches_when_zero_relevant():
    """NO_MATCHES only when zero candidates are relevant."""
    candidates = [_candidate("lab/a")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="test")

    haiku_response = [
        {"ci_name": "lab/a", "relevance_score": 10, "relevant": False,
         "one_line_reason": "nope"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert result.phase == "NO_MATCHES"
    assert len(result.candidates) == 1
    assert result.candidates[0].tier == "white"


def test_triage_captures_token_usage():
    """Returned QueryState should carry triage token usage entry."""
    candidates = [_candidate("good-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="ansible")

    haiku_response = [
        {"ci_name": "good-ci", "relevance_score": 85, "relevant": True,
         "one_line_reason": "Match"},
    ]
    client = _mock_client(haiku_response, input_tokens=1500, output_tokens=250)

    result = triage(state, client, model="claude-haiku-4-5", triage_cutoff=30)

    assert len(result.token_usage) == 1
    entry = result.token_usage[0]
    assert entry["operation"] == "triage"
    assert entry["model"] == "claude-haiku-4-5"
    assert entry["input_tokens"] == 1500
    assert entry["output_tokens"] == 250


def test_triage_carries_forward_existing_token_usage():
    """Existing token_usage from prior state should be preserved."""
    prior_entry = {"operation": "scan", "model": "claude-sonnet-4-6",
                   "input_tokens": 9000, "output_tokens": 800}
    candidates = [_candidate("good-ci")]
    state = QueryState(
        phase="VECTOR_DONE", candidates=candidates,
        query="ansible", token_usage=[prior_entry],
    )

    haiku_response = [
        {"ci_name": "good-ci", "relevance_score": 80, "relevant": True,
         "one_line_reason": "Match"},
    ]
    client = _mock_client(haiku_response)
    result = triage(state, client, triage_cutoff=30)

    assert len(result.token_usage) == 2
    assert result.token_usage[0]["operation"] == "scan"
    assert result.token_usage[1]["operation"] == "triage"
