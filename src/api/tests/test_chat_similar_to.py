"""RHDPCD-2298 fix 1: a NAMED item the user wants "similar to" is a reference, however it is named.

The router (LLM) marks it in args.similar_to; resolve_item() resolves it; the
resolved content_id travels to the pipeline as reference_ids. No lab-number special case.
"""
import asyncio

import pytest
from unittest.mock import Mock

from rcars.services.chat import handlers, registry
from rcars.services.chat import router as chat_router
from rcars.services.chat.models import RecommendArgs, RouterOutput
from rcars.services.chat.router import Resolution
from tests.chat_fixtures import fake_embedding, seed_chat_fixtures
from tests.test_chat_resolve import CTX, SETTINGS, db  # noqa: F401  (fixture)


async def resolve(db, **args):
    out = RouterOutput(intent="recommend", confidence=0.9, args=args)
    return await chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")


@pytest.mark.asyncio
@pytest.mark.parametrize("named_as", [
    "LB2144 Event-Driven Ansible",  # display name
    "LB2144",  # lab number
    "lb2144-ansible-eda",  # CI name
    "https://catalog.demo.redhat.com/catalog?item=babylon-catalog-prod/lb2144-ansible-eda",  # catalog URL
    "content_id:babylon:lb2144-ansible-eda",  # chip
])
async def test_every_way_of_naming_the_item_gives_the_same_reference(db, named_as):
    ids = seed_chat_fixtures(db)
    res = await resolve(db, search_query="similar to it", similar_to=named_as)
    assert res.kind == "execute"
    assert res.reference_ids == [ids["lb2144-ansible-eda"]]


@pytest.mark.asyncio
async def test_no_similar_to_means_no_reference_even_when_the_query_names_an_item(db):
    seed_chat_fixtures(db)
    res = await resolve(db, search_query="OpenShift Virtualization Migration")
    assert res.kind == "execute" and res.reference_ids == []
    res = await resolve(db, search_query="what is LB2144 about")
    assert res.reference_ids == []


@pytest.mark.asyncio
async def test_ambiguous_reference_clarifies_and_excludes_nothing_until_picked(db, monkeypatch):
    ids = seed_chat_fixtures(db)
    monkeypatch.setattr(chat_router, "generate_embedding", lambda text, prefix="": fake_embedding(text))
    res = await resolve(db, search_query="similar to the quantum blockchain lab",
                        similar_to="the quantum blockchain lab")
    assert res.kind == "clarify" and res.reference_ids == []
    assert res.chips
    # The chip carries the pick back as the reference.
    chip = res.chips[0]
    assert chip.args["similar_to"].startswith("content_id:")
    picked = await resolve(db, **{**chip.args, "similar_to": f"content_id:{ids['lb2144-ansible-eda']}"})
    assert picked.kind == "execute" and picked.reference_ids == [ids["lb2144-ansible-eda"]]


@pytest.mark.asyncio
async def test_similar_to_is_only_read_for_recommend(db):
    seed_chat_fixtures(db)
    out = RouterOutput(intent="overlap", confidence=0.9, args={"similar_to": "LB2144"})
    res = await chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.reference_ids == []


def test_handler_passes_the_resolved_references_to_the_pipeline(monkeypatch):
    seen = {}

    async def fake_run_query(query, db, settings, **kwargs):
        seen.update(kwargs)
        return {}

    monkeypatch.setattr(handlers, "run_query", fake_run_query)
    monkeypatch.setattr(handlers, "_serialize_category_states",
                        lambda states, db, query: ([], Mock(content_gaps=None, overall_assessment=None)))
    res = Resolution(kind="execute", reference_ids=["babylon:x"],
                     output=RouterOutput(intent="recommend", confidence=1.0,
                                         args={"search_query": "similar to x", "similar_to": "x"}))

    async def noop(data):
        pass

    asyncio.run(handlers.handle_recommend(res, Mock(), Mock(), ["prod"], True, noop))
    assert seen["reference_ids"] == ["babylon:x"]


def test_handler_passes_no_reference_for_a_topic_search(monkeypatch):
    seen = {}

    async def fake_run_query(query, db, settings, **kwargs):
        seen.update(kwargs)
        return {}

    monkeypatch.setattr(handlers, "run_query", fake_run_query)
    monkeypatch.setattr(handlers, "_serialize_category_states",
                        lambda states, db, query: ([], Mock(content_gaps=None, overall_assessment=None)))
    res = Resolution(kind="execute", output=RouterOutput(intent="recommend", confidence=1.0,
                                                         args={"search_query": "OpenShift Virtualization Networking"}))

    async def noop(data):
        pass

    asyncio.run(handlers.handle_recommend(res, Mock(), Mock(), ["prod"], True, noop))
    assert seen["reference_ids"] is None


def test_router_examples_cover_name_lab_number_url_and_a_plain_topic():
    examples = [ex["output"]["args"] for ex in registry.INTENTS["recommend"].examples]
    for args in examples:
        RecommendArgs.model_validate(args)
    named = [a["similar_to"] for a in examples if a.get("similar_to")]
    assert any(n.startswith("LB") for n in named)
    assert any(n.startswith("https://") for n in named)
    assert any(not n.startswith("LB") and not n.startswith("https://") for n in named)  # a display name
    assert any("similar_to" not in a for a in examples)  # a topic search with no reference
    system, _ = registry.build_router_prompt([])
    assert "similar_to" in system
