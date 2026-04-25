from rcars.services.recommender.models import Candidate, QueryState


def test_candidate_similarity_pct():
    assert Candidate.similarity_pct(0.0) == 100
    assert Candidate.similarity_pct(0.5) == 75
    assert Candidate.similarity_pct(1.0) == 50


def test_query_state_defaults():
    state = QueryState(phase="SUBMITTED", candidates=[])
    assert state.query == ""
    assert state.overall_assessment is None
    assert state.content_gaps is None


def test_candidate_tier_defaults():
    c = Candidate(
        ci_name="test.item",
        display_name="Test",
        category="Workshops",
        summary="A test item",
        topics=["openshift"],
        products=["OpenShift"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
    )
    assert c.tier == "white"
    assert c.relevance_score is None
    assert c.rationale is None


def test_imports():
    from rcars.services.recommender import run_query, Candidate, QueryState
    from rcars.services.analyzer import generate_embedding, parse_analysis_response, analyze_showroom
    from rcars.services.catalog import CatalogReader
    assert run_query is not None
    assert Candidate is not None
    assert generate_embedding is not None
    assert CatalogReader is not None
