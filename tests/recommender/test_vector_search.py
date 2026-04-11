"""Tests for Phase 1 — vector search with distance cutoff."""

from unittest.mock import MagicMock, patch

from rcars.recommender.vector_search import search
from rcars.recommender.models import Candidate


def _mock_db(rows):
    """Create a mock Database that returns given rows from search_embeddings."""
    db = MagicMock()
    db.search_embeddings.return_value = rows
    def mock_analysis(ci_name):
        return {
            "content_type": "workshop",
            "summary": f"Summary for {ci_name}",
            "difficulty": "beginner",
            "estimated_duration_min": 60,
            "topics_json": ["openshift"],
            "products_json": ["OCP"],
            "audience_json": ["developers"],
        }
    db.get_showroom_analysis.side_effect = mock_analysis
    return db


def _row(ci_name, distance):
    return {
        "ci_name": ci_name,
        "display_name": ci_name.replace("-", " ").title(),
        "category": "workshop",
        "stage": "prod",
        "is_published": False,
        "published_ci_name": None,
        "base_ci_name": None,
        "content_text": "some text",
        "module_title": None,
        "distance": distance,
    }


@patch("rcars.recommender.vector_search.generate_embedding", return_value=[0.1] * 384)
def test_search_returns_candidates_under_cutoff(mock_emb):
    rows = [_row("good-ci", 0.3), _row("ok-ci", 0.5), _row("bad-ci", 0.8)]
    db = _mock_db(rows)

    state = search("test query", db, limit=10, distance_cutoff=0.55)

    assert state.phase == "VECTOR_DONE"
    assert len(state.candidates) == 2
    assert state.candidates[0].ci_name == "good-ci"
    assert state.candidates[1].ci_name == "ok-ci"
    assert state.candidates[0].vector_similarity_pct == Candidate.similarity_pct(0.3)
    assert "vector_search" in state.timings


@patch("rcars.recommender.vector_search.generate_embedding", return_value=[0.1] * 384)
def test_search_no_matches_returns_no_matches_phase(mock_emb):
    rows = [_row("bad-ci", 0.8), _row("worse-ci", 0.9)]
    db = _mock_db(rows)

    state = search("test query", db, limit=10, distance_cutoff=0.55)

    assert state.phase == "NO_MATCHES"
    assert len(state.candidates) == 0


@patch("rcars.recommender.vector_search.generate_embedding", return_value=[0.1] * 384)
def test_search_empty_db_returns_no_matches(mock_emb):
    db = _mock_db([])

    state = search("test query", db, limit=10, distance_cutoff=0.55)

    assert state.phase == "NO_MATCHES"
    assert len(state.candidates) == 0


@patch("rcars.recommender.vector_search.generate_embedding", return_value=[0.1] * 384)
def test_search_enriches_candidates_with_analysis(mock_emb):
    rows = [_row("my-ci", 0.4)]
    db = _mock_db(rows)

    state = search("test query", db, limit=10, distance_cutoff=0.55)

    c = state.candidates[0]
    assert c.summary == "Summary for my-ci"
    assert c.topics == ["openshift"]
    assert c.products == ["OCP"]
    assert c.difficulty == "beginner"
    assert c.duration_min == 60
    assert c.content_type == "workshop"
