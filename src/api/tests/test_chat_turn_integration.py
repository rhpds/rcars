import asyncio
import functools
import json
import os
import pytest
from rcars.config import LLMResult, Settings
from rcars.db import chat_sessions
from rcars.db.database import Database
from rcars.services.chat import handlers, orchestrator
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
    return Settings(database_url=TEST_DB_URL, vector_cutoff=0.99, chat_intent_roles_str="")


class FakeLLM:
    """Queue of canned router/answer texts, FIFO."""
    def __init__(self, *texts):
        self.texts = list(texts)
    def __call__(self, settings, model, messages, max_tokens, temperature=0, system=None):
        return LLMResult(text=self.texts.pop(0), input_tokens=1, output_tokens=1, provider="t")


async def _noop(data):
    pass


def test_three_turn_session_scope_resolution(db, monkeypatch):
    ids = seed_chat_fixtures(db)
    monkeypatch.setattr("rcars.services.recommender.vector_search.generate_embedding",
                        lambda text, prefix="": fake_embedding(text))
    monkeypatch.setattr(handlers, "run_query",
                        functools.partial(pipeline.run_query, depth="low"))
    s = _settings()

    # Turn 0: recommend (fake router + fake answer)
    router_json = json.dumps({"intent": "recommend",
                              "args": {"search_query": "Event-Driven Ansible automation"},
                              "scope": None, "item_refs": [], "confidence": 0.9, "clarify": None})
    env0 = asyncio.run(orchestrator.process_turn(
        message="find me ansible eda content", session_id="sess-1", user_email="u@x.com",
        db=db, settings=s, on_progress=_noop, llm_call=FakeLLM(router_json, "narrative 0")))
    assert env0["intent"] == "recommend"
    turn0_ids = [c["content_id"] for c in env0["blocks"][0]["data"]["candidates"]]
    assert turn0_ids  # vector results present and persisted as the working set

    # Turn 1: performance scoped to turn 0 ("which of these performed best?")
    router_json = json.dumps({"intent": "performance", "args": {},
                              "scope": {"type": "prior_results", "turn": 0},
                              "item_refs": [], "confidence": 0.9, "clarify": None})
    env1 = asyncio.run(orchestrator.process_turn(
        message="which of these performed best?", session_id="sess-1", user_email="u@x.com",
        db=db, settings=s, on_progress=_noop, llm_call=FakeLLM(router_json, "narrative 1")))
    rows = env1["blocks"][0]["data"]["rows"]
    assert sorted(r["content_id"] for r in rows) == sorted(turn0_ids)  # exactly turn 0's ids
    assert "turn" not in env1["scope_echo"] or env1["scope_echo"]      # echo present
    assert env1["scope_echo"]

    # Turn 2: pre-routed chip (skips router — FakeLLM has only the answer text)
    env2 = asyncio.run(orchestrator.process_turn(
        message="Overlap for these", session_id="sess-1", user_email="u@x.com",
        routed={"intent": "overlap", "args": {}, "scope": {"type": "prior_results", "turn": 1}},
        db=db, settings=s, on_progress=_noop, llm_call=FakeLLM("narrative 2")))
    assert env2["intent"] == "overlap"

    turns = db.get_advisor_session("sess-1")
    assert [t["turn_index"] for t in turns] == [0, 1, 2]
    assert turns[1]["intent"] == "performance"
    assert turns[1]["scope_json"]["turn"] == 0            # audit trail
    assert turns[0]["envelope_json"]["blocks"]            # History replay payload


def test_out_of_scope_is_deterministic(db):
    seed_chat_fixtures(db)
    router_json = json.dumps({"intent": "out_of_scope", "args": {}, "scope": None,
                              "item_refs": [], "confidence": 0.95, "clarify": None})
    env = asyncio.run(orchestrator.process_turn(
        message="what's the weather?", session_id="sess-2", user_email="u@x.com",
        db=db, settings=_settings(), on_progress=_noop, llm_call=FakeLLM(router_json)))
    assert env["intent"] == "out_of_scope"
    assert env["blocks"][0]["type"] == "notice"
    assert "recommend" in env["answer"].lower() or "overlap" in env["answer"].lower()
