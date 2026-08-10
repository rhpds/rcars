"""Tests for LLM overlap assessment."""

import os
import psycopg
from psycopg.rows import dict_row
import pytest
from rcars.db.database import Database

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
