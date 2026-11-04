from dataclasses import replace
from unittest.mock import Mock

import pytest
from psycopg.types.json import Jsonb

from tests.showroom_helpers import db
from tests.test_showroom_scope_db import seed
from rcars.services.recommender import vector_search
from rcars.services.showroom_source import ResolvedShowroom


def search(db, monkeypatch, content_ids, *, stages=None, scope=None):
    rows = [{**db.get_babylon_item(cid), "content_hash": "content", "best_similarity": 0.9 - index * 0.05}
            for index, cid in enumerate(content_ids)]
    monkeypatch.setattr(db, "search_embeddings", Mock(return_value=rows))
    monkeypatch.setattr(vector_search, "generate_embedding", lambda *a, **k: [0.1] * 768)
    return vector_search.search("TLS", db, stages=stages or ["dev", "prod"], scope_content_ids=scope).candidates


def test_unrelated_same_hash_prod_cannot_replace_dev(db, monkeypatch):
    dev, _, _ = seed(db, "isolation-test.dev-only.dev")
    prod, _, _ = seed(db, "isolation-test.other.prod")
    candidates = search(db, monkeypatch, [dev])
    assert [c.content_id for c in candidates] == [dev]


@pytest.mark.parametrize("field,value", [(None, None), ("ref", "other"), ("content_path", "other/pages"),
                                         ("content_hash", "other"), ("scope_key", "other"), ("commit", "b" * 40)])
def test_exact_same_item_prod_requires_complete_matching_signature(db, monkeypatch, field, value):
    dev, _, _ = seed(db, "isolation-test.item.dev")
    prod, _, provenance = seed(db)
    if field:
        provenance["signature"][field] = value
        with db.pool.connection() as conn:
            conn.execute("UPDATE showroom_analysis SET analysis_provenance_json = %s WHERE content_id = %s", (Jsonb(provenance), prod))
    candidates = search(db, monkeypatch, [dev])
    assert [c.content_id for c in candidates] == ([prod] if field is None else [dev])


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


def test_owner_hit_is_shown_as_its_only_stub(db, monkeypatch):
    owner, _, _ = seed(db)
    stub = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    candidates = search(db, monkeypatch, [owner], stages=["prod"])
    assert [c.content_id for c in candidates] == [stub]
    assert candidates[0].vector_similarity_pct == 90  # the owner hit's score is kept


def test_owner_without_a_stub_is_shown_as_the_owner(db, monkeypatch):
    owner, _, _ = seed(db)
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"])] == [owner]


def test_owner_with_two_stubs_is_shown_as_the_owner(db, monkeypatch):
    owner, _, _ = seed(db)
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.first.prod")
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.second.prod")
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"])] == [owner]


def test_stub_outside_the_requested_stage_is_not_shown(db, monkeypatch):
    owner, _, _ = seed(db)
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.dev", stage="dev")
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"])] == [owner]


def test_stub_outside_the_requested_scope_is_not_shown(db, monkeypatch):
    owner, _, _ = seed(db)
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"], scope=[owner])] == [owner]


def test_each_owner_promotes_to_its_own_stub(db, monkeypatch):
    a, _, _ = seed(db)
    b, _, _ = seed(db, "isolation-test.b.prod")
    stub_a = add_stub(db, "isolation-test.item.prod", "isolation-test.virtual-a.prod")
    stub_b = add_stub(db, "isolation-test.b.prod", "isolation-test.virtual-b.prod")
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
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    candidate = search(db, monkeypatch, [owner], stages=["prod"])[0]
    assert candidate.content_id == "babylon:isolation-test.virtual.prod"
    assert candidate.summary == "A real lab"
    from rcars.services.recommender.drivers.hands_on import HandsOnDriver
    assert HandsOnDriver().fetch_analysis(db, candidate)["summary"] == "A real lab"
