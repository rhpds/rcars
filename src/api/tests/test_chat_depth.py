import asyncio
import os
import pytest
from rcars.db.database import Database
from rcars.services.recommender import pipeline
from tests.chat_fixtures import seed_chat_fixtures, fake_embedding

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL", "postgresql://rcars:dev@localhost:5432/rcars_test")


@pytest.fixture
def db():
    import psycopg
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        for row in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def _settings():
    from rcars.config import Settings
    return Settings(database_url=TEST_DB_URL, vector_cutoff=0.99)  # cutoff wide open for fake vectors


def test_scope_filter_restricts_pool(db):
    ids = seed_chat_fixtures(db)
    emb = fake_embedding("Hands-on lab for Event-Driven Ansible automation.")
    all_rows = db.search_embeddings(emb, limit=25, quality_threshold=0.0)
    scoped = db.search_embeddings(emb, limit=25, quality_threshold=0.0,
                                  scope_content_ids=[ids["rhel-security"]])
    assert len(all_rows) > 1
    assert [r["content_id"] for r in scoped] == [ids["rhel-security"]]


def test_depth_low_stops_before_triage(db, monkeypatch):
    seed_chat_fixtures(db)
    monkeypatch.setattr("rcars.services.recommender.vector_search.generate_embedding",
                        lambda text, prefix="": fake_embedding(text))

    def boom(*a, **k):
        raise AssertionError("triage must not run at depth=low")
    monkeypatch.setattr(pipeline, "triage", boom)

    state = asyncio.run(pipeline.run_query(
        "Event-Driven Ansible automation", db, _settings(), depth="low"))
    assert state.candidates  # vector results present, no triage/rationale
