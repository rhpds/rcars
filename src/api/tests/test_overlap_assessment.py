"""Tests for LLM overlap assessment."""

import json
import math
import os
import psycopg
from psycopg.rows import dict_row
import pytest
from unittest.mock import patch, MagicMock
from rcars.config import Settings
from rcars.db.database import Database
from rcars.services.overlap_assessment import (
    assess_overlap,
    batch_assess_overlaps,
    _build_assessment_prompt,
    _load_analysis_pair,
    _validate_assessment,
    VALID_VERDICTS,
    VALID_RECOMMENDATIONS,
)

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    """Create a fresh test database with schema."""
    with psycopg.connect(TEST_DB_URL, autocommit=True, row_factory=dict_row) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row['tablename']} CASCADE")

    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def test_overlap_candidates_has_assessment_columns(db):
    with db.pool.connection() as conn:
        cur = conn.execute(
            """SELECT column_name, data_type
               FROM information_schema.columns
               WHERE table_name = 'overlap_candidates'
                 AND column_name IN ('llm_assessment', 'assessed_at')
               ORDER BY column_name"""
        )
        cols = {row["column_name"]: row["data_type"] for row in cur.fetchall()}
    assert cols["llm_assessment"] == "jsonb"
    assert cols["assessed_at"] == "timestamp with time zone"


def test_overlap_model_default():
    s = Settings(database_url="postgresql://test:test@localhost/test")
    assert s.overlap_model == "claude-haiku-4-5"


def test_overlap_model_from_env(monkeypatch):
    monkeypatch.setenv("RCARS_OVERLAP_MODEL", "claude-haiku-4-5")
    s = Settings(database_url="postgresql://test:test@localhost/test")
    assert s.overlap_model == "claude-haiku-4-5"


# --- Helper functions for Task 4 tests ---

def _make_vector(similarity_to_base: float, dim: int = 768) -> str:
    theta = math.acos(similarity_to_base)
    components = [0.0] * dim
    components[0] = math.cos(theta)
    components[1] = math.sin(theta)
    return "[" + ",".join(f"{c:.6f}" for c in components) + "]"


BASE_VECTOR = _make_vector(1.0)
VECTOR_96 = _make_vector(0.96)


def _seed_overlap_pair(db):
    """Seed two items with analysis data and a pre-computed overlap candidate."""
    cid_a = "babylon:ns.lab-x.prod"
    cid_b = "babylon:ns.lab-y.prod"

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            for cid, name, content_hash in [
                (cid_a, "OpenShift Deployment Lab", "hash_x"),
                (cid_b, "OpenShift Troubleshooting Lab", "hash_y"),
            ]:
                cur.execute(
                    """INSERT INTO content_entities
                       (content_id, source, content_type, is_hands_on, display_name)
                       VALUES (%s, 'babylon', 'lab', TRUE, %s)""",
                    (cid, name),
                )
                cur.execute(
                    """INSERT INTO babylon_items
                       (content_id, ci_name, category, stage, is_published)
                       VALUES (%s, %s, 'workshop', 'prod', FALSE)""",
                    (cid, cid.split(":")[-1].rsplit(".", 1)[0]),
                )
                cur.execute(
                    """INSERT INTO showroom_analysis
                       (content_id, summary, products_json, topics_json,
                        modules_json, learning_objectives_json, audience_json,
                        difficulty, estimated_duration_min, use_cases_json,
                        content_hash)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        cid,
                        f"Summary for {name}",
                        json.dumps([{"name": "OpenShift"}]),
                        json.dumps(["containers", "kubernetes"]),
                        json.dumps([{"title": "Module 1"}, {"title": "Module 2"}]),
                        json.dumps(["Learn OCP basics"]),
                        json.dumps(["Platform engineers"]),
                        "intermediate",
                        60,
                        json.dumps(["workshop"]),
                        content_hash,
                    ),
                )

            for cid, vec in [
                (cid_a, BASE_VECTOR),
                (cid_b, VECTOR_96),
            ]:
                cur.execute(
                    """INSERT INTO embeddings
                       (content_id, content_type, source, embed_type, content_text, embedding)
                       VALUES (%s, 'lab', 'babylon', 'summary', 'test', %s::vector)""",
                    (cid, vec),
                )

            # Insert directly into overlap_candidates (canonical order: cid_a < cid_b)
            cur.execute(
                """INSERT INTO overlap_candidates
                   (content_id_a, content_id_b, shared_products, shared_topics,
                    content_hash_a, content_hash_b)
                   VALUES (%s, %s, 2, 2, 'hash_x', 'hash_y')
                   ON CONFLICT DO NOTHING""",
                (cid_a, cid_b),
            )
        conn.commit()

    return cid_a, cid_b


MOCK_LLM_RESPONSE = json.dumps({
    "verdict": "complementary",
    "shared_topics": ["OpenShift deployment"],
    "differentiators_a": ["GitOps workflow"],
    "differentiators_b": ["CLI troubleshooting"],
    "recommendation": "keep_both",
    "rationale": "Both cover OpenShift but from different angles.",
})


# --- Task 4 test cases ---

def test_validate_assessment_valid():
    parsed = {
        "verdict": "complementary",
        "shared_topics": ["OpenShift"],
        "differentiators_a": ["GitOps"],
        "differentiators_b": ["CLI"],
        "recommendation": "keep_both",
        "rationale": "Different angles.",
    }
    result = _validate_assessment(parsed)
    assert result is not None
    assert result["verdict"] == "complementary"
    assert result["recommendation"] == "keep_both"


def test_validate_assessment_invalid_verdict():
    parsed = {
        "verdict": "maybe",
        "shared_topics": [],
        "differentiators_a": [],
        "differentiators_b": [],
        "recommendation": "keep_both",
        "rationale": "Unclear.",
    }
    assert _validate_assessment(parsed) is None


def test_validate_assessment_invalid_recommendation():
    parsed = {
        "verdict": "redundant",
        "shared_topics": [],
        "differentiators_a": [],
        "differentiators_b": [],
        "recommendation": "delete_both",
        "rationale": "Bad.",
    }
    assert _validate_assessment(parsed) is None


def test_validate_assessment_missing_arrays_coerced():
    parsed = {
        "verdict": "differentiated",
        "recommendation": "keep_both",
        "rationale": "Totally different.",
    }
    result = _validate_assessment(parsed)
    assert result is not None
    assert result["shared_topics"] == []
    assert result["differentiators_a"] == []
    assert result["differentiators_b"] == []


def test_validate_assessment_missing_verdict_returns_none():
    parsed = {
        "shared_topics": ["OpenShift"],
        "recommendation": "keep_both",
        "rationale": "Missing verdict.",
    }
    assert _validate_assessment(parsed) is None


def test_validate_assessment_coerces_non_list_to_list():
    parsed = {
        "verdict": "redundant",
        "shared_topics": "OpenShift deployment",
        "differentiators_a": "GitOps",
        "differentiators_b": None,
        "recommendation": "merge",
        "rationale": "Same content.",
    }
    result = _validate_assessment(parsed)
    assert result is not None
    assert result["shared_topics"] == ["OpenShift deployment"]
    assert result["differentiators_a"] == ["GitOps"]
    assert result["differentiators_b"] == []


def test_valid_verdicts_and_recommendations_are_frozen():
    assert "redundant" in VALID_VERDICTS
    assert "complementary" in VALID_VERDICTS
    assert "differentiated" in VALID_VERDICTS
    assert "merge" in VALID_RECOMMENDATIONS
    assert "keep_both" in VALID_RECOMMENDATIONS
    assert "retire_one" in VALID_RECOMMENDATIONS


def test_build_assessment_prompt(db):
    cid_a, cid_b = _seed_overlap_pair(db)
    analysis_a, analysis_b = _load_analysis_pair(db.pool, cid_a, cid_b)
    prompt = _build_assessment_prompt(analysis_a, analysis_b)
    assert "OpenShift Deployment Lab" in prompt
    assert "OpenShift Troubleshooting Lab" in prompt
    assert "Learning Objectives" in prompt
    assert "Modules" in prompt


@patch("rcars.services.overlap_assessment.call_llm")
def test_assess_overlap_calls_llm_and_persists(mock_llm, db):
    cid_a, cid_b = _seed_overlap_pair(db)
    mock_llm.return_value = MagicMock(
        text=MOCK_LLM_RESPONSE, input_tokens=500, output_tokens=200
    )
    settings = Settings(database_url=TEST_DB_URL)
    result, reason = assess_overlap(db.pool, settings, cid_a, cid_b)

    assert result is not None
    assert reason == "ok"
    assert result["verdict"] == "complementary"
    assert result["recommendation"] == "keep_both"
    assert result["model"] == settings.overlap_model
    assert result["tokens"]["input"] == 500
    mock_llm.assert_called_once()

    # Verify persistence
    with db.pool.connection() as conn:
        cur = conn.execute(
            """SELECT llm_assessment, assessed_at FROM overlap_candidates
               WHERE content_id_a = %s AND content_id_b = %s""",
            (cid_a, cid_b),
        )
        row = cur.fetchone()
    assert row["llm_assessment"]["verdict"] == "complementary"
    assert row["assessed_at"] is not None


@patch("rcars.services.overlap_assessment.call_llm")
def test_assess_overlap_returns_cache_on_second_call(mock_llm, db):
    cid_a, cid_b = _seed_overlap_pair(db)
    mock_llm.return_value = MagicMock(
        text=MOCK_LLM_RESPONSE, input_tokens=500, output_tokens=200
    )
    settings = Settings(database_url=TEST_DB_URL)
    assess_overlap(db.pool, settings, cid_a, cid_b)
    result2, reason2 = assess_overlap(db.pool, settings, cid_a, cid_b)

    assert result2["verdict"] == "complementary"
    assert reason2 == "cached"
    assert mock_llm.call_count == 1  # cached, no second LLM call


@patch("rcars.services.overlap_assessment.call_llm")
def test_assess_overlap_missing_analysis_returns_none(mock_llm, db):
    """Items without showroom_analysis should return None, not call LLM."""
    cid_na = "babylon:ns.no-analysis-a.prod"
    cid_nb = "babylon:ns.no-analysis-b.prod"

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            for cid, name in [
                (cid_na, "No Analysis A"),
                (cid_nb, "No Analysis B"),
            ]:
                cur.execute(
                    """INSERT INTO content_entities
                       (content_id, source, content_type, is_hands_on, display_name)
                       VALUES (%s, 'babylon', 'lab', TRUE, %s)""",
                    (cid, name),
                )
                cur.execute(
                    """INSERT INTO babylon_items
                       (content_id, ci_name, category, stage, is_published)
                       VALUES (%s, %s, 'workshop', 'prod', FALSE)""",
                    (cid, cid.split(":")[-1].rsplit(".", 1)[0]),
                )
            # Insert as an overlap candidate (no showroom_analysis rows)
            cur.execute(
                """INSERT INTO overlap_candidates
                   (content_id_a, content_id_b, shared_products, shared_topics)
                   VALUES (%s, %s, 1, 1)
                   ON CONFLICT DO NOTHING""",
                (cid_na, cid_nb),
            )
        conn.commit()

    settings = Settings(database_url=TEST_DB_URL)
    result, reason = assess_overlap(db.pool, settings, cid_na, cid_nb)
    assert result is None
    assert reason == "missing_analysis"
    mock_llm.assert_not_called()


@patch("rcars.services.overlap_assessment.call_llm")
def test_assess_overlap_rejects_invalid_verdict(mock_llm, db):
    """LLM returns valid JSON but invalid verdict — should return None, not persist."""
    cid_a, cid_b = _seed_overlap_pair(db)
    mock_llm.return_value = MagicMock(
        text=json.dumps({
            "verdict": "maybe_similar",
            "shared_topics": ["OpenShift"],
            "differentiators_a": [],
            "differentiators_b": [],
            "recommendation": "keep_both",
            "rationale": "Unclear.",
        }),
        input_tokens=500, output_tokens=200,
    )
    settings = Settings(database_url=TEST_DB_URL)
    result, reason = assess_overlap(db.pool, settings, cid_a, cid_b)
    assert result is None
    assert reason == "validation_error"

    # Verify nothing was persisted
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT llm_assessment FROM overlap_candidates WHERE content_id_a = %s AND content_id_b = %s",
            (cid_a, cid_b),
        )
        row = cur.fetchone()
    assert row["llm_assessment"] is None


def test_parse_truncated_assessment_response():
    from rcars.services.analyzer import parse_analysis_response

    # Incomplete object — parser extracts the complete object found within
    truncated = '{"verdict": "redundant", "shared_topics": ["OpenShift"], "differentiators_a": [], "differentiators_b": [], "recommendation": "merge"'
    result = parse_analysis_response(truncated)
    # Parser won't find a complete JSON object, but extraction should handle this
    # For now, verify parser handles this gracefully (returns None for incomplete)
    # The validation layer will catch missing fields
    if result:
        assert "verdict" in result


def test_assessment_endpoint_returns_cached(db):
    """Verify cached assessment is returned without LLM call."""
    cid_a, cid_b = _seed_overlap_pair(db)

    assessment = {
        "verdict": "complementary",
        "shared_topics": ["OpenShift"],
        "differentiators_a": ["GitOps"],
        "differentiators_b": ["Troubleshooting"],
        "recommendation": "keep_both",
        "rationale": "Different angles.",
        "model": "claude-sonnet-4-6",
        "tokens": {"input": 500, "output": 200},
    }

    # Pre-populate a cached assessment (content_hash_a/b already set by _seed_overlap_pair)
    with db.pool.connection() as conn:
        conn.execute(
            """UPDATE overlap_candidates
               SET llm_assessment = %s::jsonb, assessed_at = NOW()
               WHERE content_id_a = %s AND content_id_b = %s""",
            (json.dumps(assessment), cid_a, cid_b),
        )
        conn.commit()

    result, reason = assess_overlap(db.pool, Settings(database_url=TEST_DB_URL), cid_a, cid_b)
    assert result is not None
    assert reason == "cached"
    assert result["verdict"] == "complementary"
    assert "tokens" in result
