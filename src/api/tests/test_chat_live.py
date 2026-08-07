"""End-to-end chat integration tests — real LLM calls against seeded DB.
Tests marked 'integration' require RCARS_CHAT_ROUTER_MODEL and embeddings LLM creds."""
import asyncio
import os

import pytest

from rcars.config import Settings
from rcars.db.database import Database
from rcars.services.chat import orchestrator
from tests.chat_fixtures import seed_chat_fixtures

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
    return Settings(database_url=TEST_DB_URL, vector_cutoff=0.99, chat_intent_roles_str="")


async def _noop(data):
    pass


@pytest.mark.integration
def test_live_item_facts_turn(db):
    """Query a specific item by LB number — expect item_facts intent and item card."""
    seed_chat_fixtures(db)
    env = asyncio.run(orchestrator.process_turn(
        message="what is LB2144 about?", session_id="live-1", user_email="u@x.com",
        db=db, settings=_settings(), on_progress=_noop))
    assert env["intent"] in ("item_facts", "recommend")   # recommend = honest fallback
    if env["intent"] == "item_facts":
        assert env["blocks"][0]["type"] == "item_card"
        assert "LB2144" in env["blocks"][0]["data"]["display_name"]


@pytest.mark.integration
def test_live_out_of_scope(db):
    """Query outside RCARS scope — expect out_of_scope intent."""
    seed_chat_fixtures(db)
    env = asyncio.run(orchestrator.process_turn(
        message="what's a good pizza place in Boston?", session_id="live-2",
        user_email="u@x.com", db=db, settings=_settings(), on_progress=_noop))
    assert env["intent"] == "out_of_scope"
