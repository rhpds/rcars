from dataclasses import replace
from unittest.mock import Mock

import pytest
from psycopg.types.json import Jsonb

from tests.showroom_helpers import db
from tests.test_showroom_scope_db import seed
from rcars.services.recommender import vector_search
from rcars.services.showroom_source import ResolvedShowroom


def search(db, monkeypatch, content_ids, *, stages=None, scope=None, include_zt=True):
    rows = [{**db.get_babylon_item(cid), "content_hash": "content", "best_similarity": 0.9 - index * 0.05}
            for index, cid in enumerate(content_ids)]
    monkeypatch.setattr(db, "search_embeddings", Mock(return_value=rows))
    monkeypatch.setattr(vector_search, "generate_embedding", lambda *a, **k: [0.1] * 768)
    return vector_search.search("TLS", db, stages=stages or ["dev", "prod"], include_zt=include_zt,
                                scope_content_ids=scope).candidates


def test_unrelated_same_hash_prod_cannot_replace_dev(db, monkeypatch):
    dev, _, _ = seed(db, "isolation-test.dev-only.dev")
    prod, _, _ = seed(db, "isolation-test.other.prod")
    candidates = search(db, monkeypatch, [dev])
    assert [c.content_id for c in candidates] == [dev]


def test_a_stage_copy_is_never_swapped_in_when_it_was_not_a_hit(db, monkeypatch):
    dev, _, _ = seed(db, "isolation-test.item.dev")
    seed(db)  # the prod copy exists, but the search did not return it
    assert [c.content_id for c in search(db, monkeypatch, [dev], stages=["prod", "dev"])] == [dev]


def test_scoped_queries_never_promote_outside_requested_ids(db, monkeypatch):
    dev, _, _ = seed(db, "isolation-test.item.dev")
    seed(db)
    assert search(db, monkeypatch, [dev], scope=[dev])[0].content_id == dev
    assert search(db, monkeypatch, [dev], stages=["dev"])[0].content_id == dev


def add_stub(db, owner_ci_name, name, *, stage="prod"):
    source = ResolvedShowroom("resolved", owner_ci_name, owner_ci_name.rsplit(".", 1)[0],
                              "https://github.com/example/content", "main",
                              paths=((name, owner_ci_name),))
    return db.upsert_babylon_catalog_item({
        "ci_name": name, "stage": stage, "display_name": name,
        "showroom_url": source.repo, "showroom_ref": "main",
        "showroom_source": source.to_dict(), "is_published": True})


def link(db, virtual, member, role="anchor", depth=1):
    """One catalog_family_members row (what the catalog refresh stores)."""
    with db.pool.connection() as conn:
        conn.execute("INSERT INTO catalog_family_members (virtual_content_id, member_content_id, role, depth) "
                     "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING", (virtual, member, role, depth))


def test_owner_hit_is_shown_as_its_only_stub(db, monkeypatch):
    owner, _, _ = seed(db)
    stub = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    link(db, stub, owner)
    candidates = search(db, monkeypatch, [owner], stages=["prod"])
    assert [c.content_id for c in candidates] == [stub]
    assert candidates[0].vector_similarity_pct == 90  # the owner hit's score is kept


def test_owner_without_a_stub_is_shown_as_the_owner(db, monkeypatch):
    owner, _, _ = seed(db)
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"])] == [owner]


def test_owner_with_two_stubs_shows_each_stub_as_its_own_card_never_the_owner(db, monkeypatch):
    owner, _, _ = seed(db)
    first = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.first.prod")
    second = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.second.prod")
    link(db, first, owner)
    link(db, second, owner)
    assert sorted(c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"])) == [first, second]


def test_stub_outside_the_requested_stage_is_not_shown(db, monkeypatch):
    owner, _, _ = seed(db)
    stub = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.dev", stage="dev")
    link(db, stub, owner)
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"])] == [owner]


def test_stub_outside_the_requested_scope_is_not_shown(db, monkeypatch):
    owner, _, _ = seed(db)
    stub = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    link(db, stub, owner)
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"], scope=[owner])] == [owner]


def test_each_owner_promotes_to_its_own_stub(db, monkeypatch):
    a, _, _ = seed(db)
    b, _, _ = seed(db, "isolation-test.b.prod")
    stub_a = add_stub(db, "isolation-test.item.prod", "isolation-test.virtual-a.prod")
    stub_b = add_stub(db, "isolation-test.b.prod", "isolation-test.virtual-b.prod")
    link(db, stub_a, a)
    link(db, stub_b, b)
    candidates = search(db, monkeypatch, [a, b], stages=["prod"])
    assert [c.content_id for c in candidates] == [stub_a, stub_b]


def test_independent_ids_keep_their_own_scores(db, monkeypatch):
    a, _, _ = seed(db, "isolation-test.a.prod")
    b, _, _ = seed(db, "isolation-test.b.prod")
    candidates = search(db, monkeypatch, [a, b], stages=["prod"])
    assert [c.content_id for c in candidates] == [a, b]
    assert candidates[0].vector_distance < candidates[1].vector_distance


def test_promoted_stub_card_hydrates_the_owner_analysis(db, monkeypatch):
    owner, _, _ = seed(db)
    stub = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    link(db, stub, owner)
    candidate = search(db, monkeypatch, [owner], stages=["prod"])[0]
    assert candidate.content_id == "babylon:isolation-test.virtual.prod"
    assert candidate.summary == "A real lab"
    from rcars.services.recommender.drivers.hands_on import HandsOnDriver
    assert HandsOnDriver().fetch_analysis(db, candidate)["summary"] == "A real lab"


def test_scoped_query_expands_stub_ids_to_their_owner(db, monkeypatch):
    owner, _, _ = seed(db)
    stub = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    link(db, stub, owner)
    captured = {}
    rows = [{**db.get_babylon_item(owner), "content_hash": "content", "best_similarity": 0.9}]

    def fake_search_embeddings(**kwargs):
        captured["scope"] = kwargs.get("scope_content_ids")
        return rows

    monkeypatch.setattr(db, "search_embeddings", fake_search_embeddings)
    monkeypatch.setattr(vector_search, "generate_embedding", lambda *a, **k: [0.1] * 768)
    candidates = vector_search.search("TLS", db, stages=["prod"], scope_content_ids=[stub]).candidates
    assert captured["scope"] == [owner]
    assert [c.content_id for c in candidates] == [stub]


def test_ci_reference_to_a_stub_resolves_through_its_owner(db, monkeypatch):
    owner, _, _ = seed(db)
    stub = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    stub_item = db.get_babylon_item(stub)
    monkeypatch.setattr(db, "find_catalog_item_by_display_name_prefix", lambda *a, **k: stub_item)
    recorded = []

    def fake_get_embedding(content_id, embed_type="summary"):
        recorded.append(content_id)
        return [0.1] * 768 if content_id == owner else None

    monkeypatch.setattr(db, "get_embedding", fake_get_embedding)
    monkeypatch.setattr(db, "search_embeddings", lambda **kwargs: [])
    vector_search._resolve_ci_references("similar to LB2391", db, ["prod"], True)
    assert recorded == [owner]


def test_zt_stub_is_not_promoted_when_zt_is_excluded(db, monkeypatch):
    owner, _, _ = seed(db)
    stub = add_stub(db, owner.removeprefix("babylon:"), "zt-isolation-test.virtual.prod")
    link(db, stub, owner)
    candidates = search(db, monkeypatch, [owner], stages=["prod"], include_zt=False)
    assert [c.content_id for c in candidates] == [owner]
