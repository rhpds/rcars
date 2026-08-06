import os
import pytest
from rcars.db.database import Database
from rcars.services.chat import router as chat_router
from rcars.services.chat.models import RouterOutput, Scope
from rcars.config import Settings
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


SETTINGS = lambda **kw: Settings(database_url=TEST_DB_URL, **kw)

CTX = [
    {"n": 0, "intent": "recommend", "query": "ansible labs",
     "results": [{"id": "babylon:lb2144-ansible-eda", "name": "LB2144 Event-Driven Ansible"},
                 {"id": "babylon:lb2145-ansible-basics", "name": "LB2145 Ansible Automation Basics"}]},
    {"n": 1, "intent": "clarify", "query": "", "results": []},
]


def test_pattern_check_url_and_lb():
    out = chat_router.pattern_check("https://summit.example.com/cfp what fits?")
    assert out.intent == "recommend" and out.confidence == 1.0
    out = chat_router.pattern_check("LB2144")
    assert out.intent == "item_facts" and out.item_refs == ["LB2144"]
    assert chat_router.pattern_check("what overlaps with LB2144 and why?") is None
    assert chat_router.pattern_check("find me an ansible lab") is None


@pytest.mark.asyncio
async def test_scope_prior_results_resolves_and_skips_clarify_turns(db):
    seed_chat_fixtures(db)
    out = RouterOutput(intent="performance", confidence=0.9,
                       scope=Scope(type="prior_results", turn=0))
    res = await chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "execute"
    assert res.scope_ids == ["babylon:lb2144-ansible-eda", "babylon:lb2145-ansible-basics"]


@pytest.mark.asyncio
async def test_scope_ordinal(db):
    seed_chat_fixtures(db)
    out = RouterOutput(intent="item_facts", confidence=0.9,
                       scope=Scope(type="ordinal", turn=0, index=2))
    res = await chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "execute"
    assert [i["content_id"] for i in res.items] == ["babylon:lb2145-ansible-basics"]


@pytest.mark.asyncio
async def test_stale_scope_clarifies(db):
    out = RouterOutput(intent="performance", confidence=0.9,
                       scope=Scope(type="prior_results", turn=99))
    res = await chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "clarify" and res.chips


@pytest.mark.asyncio
async def test_unresolvable_ref_offers_guesses(db, monkeypatch):
    seed_chat_fixtures(db)
    monkeypatch.setattr(chat_router, "generate_embedding",
                        lambda text, prefix="": fake_embedding(text))
    out = RouterOutput(intent="overlap", confidence=0.9, item_refs=["the quantum blockchain lab"])
    res = await chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "clarify"
    assert res.clarify and "mean" in res.clarify.question.lower()
    assert 0 < len(res.chips) <= 3


@pytest.mark.asyncio
async def test_lb_ref_resolves(db):
    ids = seed_chat_fixtures(db)
    out = RouterOutput(intent="overlap", confidence=0.9, item_refs=["LB2144"])
    res = await chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "execute"
    assert res.items[0]["content_id"] == ids["lb2144-ansible-eda"]


@pytest.mark.asyncio
async def test_low_confidence_clarifies(db):
    out = RouterOutput(intent="recommend", confidence=0.3,
                       clarify={"question": "Lab or demo?", "options": ["Lab", "Demo"]})
    res = await chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "clarify" and res.clarify.question == "Lab or demo?"


@pytest.mark.asyncio
async def test_role_gate_redirects(db):
    out = RouterOutput(intent="performance", confidence=0.9,
                       scope=Scope(type="prior_results", turn=0))
    res = await chat_router.resolve_and_verify(out, CTX, db, SETTINGS(), "notcurator@x.com")
    assert res.kind == "redirect" and "curator" in res.redirect_message.lower()
