"""Tests for LLM overlap assessment."""

import os
import psycopg
from psycopg.rows import dict_row
import pytest
from rcars.config import Settings
from rcars.db.database import Database
from rcars.db.similarity import _score_band

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


def test_content_similarity_has_assessment_columns(db):
    with db.pool.connection() as conn:
        cur = conn.execute(
            """SELECT column_name, data_type
               FROM information_schema.columns
               WHERE table_name = 'content_similarity'
                 AND column_name IN ('llm_assessment', 'assessed_at')
               ORDER BY column_name"""
        )
        cols = {row["column_name"]: row["data_type"] for row in cur.fetchall()}
    assert cols["llm_assessment"] == "jsonb"
    assert cols["assessed_at"] == "timestamp with time zone"


def test_overlap_model_default():
    s = Settings(database_url="postgresql://test:test@localhost/test")
    assert s.overlap_model == "claude-sonnet-4-6"


def test_overlap_model_from_env(monkeypatch):
    monkeypatch.setenv("RCARS_OVERLAP_MODEL", "claude-haiku-4-5")
    s = Settings(database_url="postgresql://test:test@localhost/test")
    assert s.overlap_model == "claude-haiku-4-5"


def test_score_band_returns_moderate_not_related():
    assert _score_band(0.80) == "moderate"
    assert _score_band(0.75) == "moderate"
    assert _score_band(0.84) == "moderate"
    assert _score_band(0.95) == "near_duplicate"
    assert _score_band(0.90) == "high_overlap"
