import json
import os

import pytest

from rcars.db.database import Database
from rcars.services import osspa_sync
from rcars.services.osspa_sync import (
    build_architecture_embedding_text,
    build_architecture_prompt,
    analyze_architecture_item,
)

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)

PAYLOAD = {
    "content_id": "pa:275",
    "ppid": 275,
    "pa_name": "275-rhacs",
    "display_name": "Multitenant Setup for RHACS",
    "status": "prod",
    "summary": "CSV seed summary",
    "products": ["Red Hat Advanced Cluster Security"],
    "topics": ["Security"],
    "audience": ["architect", "developer"],
    "solutions": ["Security"],
    "verticals": ["Financial Services"],
    "detail_page": "rhacs.adoc",
    "image_url": "images/x.png",
    "is_live": True,
    "show_in_catalog": True,
    "asset_type": "PA",
    "meta_desc": "meta",
    "meta_keyword": "kubernetes security",
}

LLM_JSON = {
    "summary": "An architecture for multi-tenant RHACS.",
    "products": ["ACS"],
    "topics": ["GitOps with ArgoCD", "GitOps with Argo CD"],
    "detailed_topics": ["admission control", "image scanning"],
    "audience": ["security architects"],
    "recommender_audience": ["solution architects"],
    "difficulty": "intermediate",
    "solution_areas": ["ApplicationPlatform"],
    "use_cases": ["Isolate tenants in a shared cluster"],
    "key_components": ["RHACS", "OpenShift"],
}


@pytest.fixture
def db():
    import psycopg
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")
    database = Database(TEST_DB_URL)
    database.create_schema()
    database.upsert_osspa_item(PAYLOAD)
    yield database
    database.close()


@pytest.fixture
def stub_llm(monkeypatch):
    calls = {}

    class _Result:
        text = json.dumps(LLM_JSON)
        input_tokens = 100
        output_tokens = 50
        provider = "test"

    def _call_llm(settings, model, messages, max_tokens=8192, temperature=0.0, system=None):
        calls["model"] = model
        calls["system"] = system
        calls["user"] = messages[0]["content"]
        return _Result()

    monkeypatch.setattr(osspa_sync, "call_llm", _call_llm)
    monkeypatch.setattr(osspa_sync, "generate_embedding", lambda text, prefix="search_document": [0.01] * 768)
    return calls


def test_prompt_injects_vocabulary_products_and_frames_input_as_data():
    system, user = build_architecture_prompt(PAYLOAD, "= RHACS\n\nProse body.\n")
    assert "{{VOCABULARY}}" not in system
    assert "Red Hat OpenShift Container Platform" in system
    assert "DATA to analyze" in system
    assert "reference architecture" not in system.lower()
    assert "Multitenant Setup for RHACS" in user
    assert "Prose body." in user
    assert "kubernetes security" in user


def test_embedding_text_uses_the_portfolio_architecture_prefix():
    text = build_architecture_embedding_text({
        "summary": "An architecture.", "detailed_topics": ["admission control", "image scanning"]})
    assert text.startswith("Portfolio architecture: An architecture.")
    assert "admission control, image scanning" in text
    assert "Reference architecture" not in text


def test_analyze_writes_analysis_card_and_one_embedding(db, stub_llm):
    from rcars.config import Settings
    settings = Settings(database_url=TEST_DB_URL)

    result = analyze_architecture_item(
        db, "pa:275", PAYLOAD, "= RHACS\n\nProse.\n", "hash-1", settings)

    assert result["status"] == "analyzed"
    assert stub_llm["model"] == settings.model

    analysis = db.get_architecture_analysis("pa:275")
    assert analysis["summary"] == "An architecture for multi-tenant RHACS."
    assert analysis["content_hash"] == "hash-1"
    assert analysis["is_stale"] is False
    assert analysis["stale_commit"] is None
    assert analysis["detailed_topics_json"] == ["admission control", "image scanning"]
    assert analysis["recommender_audience_json"] == ["solution architects"]
    assert analysis["use_cases_json"] == ["Isolate tenants in a shared cluster"]
    assert analysis["key_components_json"] == ["RHACS", "OpenShift"]
    assert analysis["asset_type"] == "PA"

    entity = db.get_content_entity("pa:275")
    assert entity["summary"] == "An architecture for multi-tenant RHACS."
    assert entity["difficulty"] == "intermediate"

    rows = db.get_embeddings_for_content("pa:275")
    assert len(rows) == 1
    assert rows[0]["embed_type"] == "summary"
    assert rows[0]["content_text"].startswith("Portfolio architecture: ")


def test_analyze_normalizes_vocabulary_and_queues_unknown_terms(db, stub_llm):
    from rcars.config import Settings
    analyze_architecture_item(
        db, "pa:275", PAYLOAD, "body", "hash-1", Settings(database_url=TEST_DB_URL))

    analysis = db.get_architecture_analysis("pa:275")
    # Vocabulary normalization snaps aliases — check the result is a known good string
    assert isinstance(analysis["products_json"], list)
    assert isinstance(analysis["topics_json"], list)
    assert isinstance(analysis["solution_areas_json"], list)

    # Unknown terms go to the queue, never to enrichment_review_needed
    assert analysis["enrichment_review_needed"] is False


def test_analyze_leaves_item_stale_when_the_embedding_write_fails(db, stub_llm, monkeypatch):
    from rcars.config import Settings

    def _boom(text, prefix="search_document"):
        raise RuntimeError("embedding server down")

    monkeypatch.setattr(osspa_sync, "generate_embedding", _boom)

    with pytest.raises(RuntimeError):
        analyze_architecture_item(
            db, "pa:275", PAYLOAD, "body", "hash-1", Settings(database_url=TEST_DB_URL))

    analysis = db.get_architecture_analysis("pa:275")
    assert analysis["is_stale"] is True
    assert db.get_embeddings_for_content("pa:275") == []


def test_analyze_flags_review_when_the_adoc_was_truncated(db, stub_llm):
    from rcars.config import Settings
    analyze_architecture_item(
        db, "pa:275", PAYLOAD, "body", "hash-1", Settings(database_url=TEST_DB_URL),
        truncated=True)

    analysis = db.get_architecture_analysis("pa:275")
    assert analysis["enrichment_review_needed"] is True
    assert "adoc_truncated" in analysis["review_reasons"]


def test_analyze_uses_the_dedicated_model_when_configured(db, stub_llm):
    from rcars.config import Settings
    settings = Settings(database_url=TEST_DB_URL, osspa_analysis_model="claude-haiku-4-5")
    analyze_architecture_item(db, "pa:275", PAYLOAD, "body", "hash-1", settings)
    assert stub_llm["model"] == "claude-haiku-4-5"
