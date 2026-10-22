from copy import deepcopy
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


def add_alias(db, owner, name, provenance, *, explicit=True):
    source = deepcopy(provenance["source"])
    source["paths"] = [[name, "example.wrapper.prod", "example.middle.prod", owner.removeprefix("babylon:")]]
    cid = db.upsert_babylon_catalog_item({"ci_name": name, "stage": "prod", "display_name": name,
        "showroom_url": source["repo"], "showroom_ref": source["ref"], "base_ci_name": owner.removeprefix("babylon:"),
        "showroom_source": source if explicit else ResolvedShowroom("none").to_dict(), "is_published": True})
    alias_provenance = {**provenance, "source": source, "reused_from": owner}
    db.upsert_showroom_analysis({"content_id": cid, "summary": "Own virtual analysis", "modules_json": [],
        "content_hash": "content", "analysis_provenance_json": alias_provenance})
    db.set_scan_status(cid, "success")
    db.store_embedding(cid, "lab", "babylon", "summary", "Own virtual analysis", [0.1] * 768)
    return cid


def test_explicit_multihop_virtual_alias_is_recognized_and_hydrates_own_analysis(db, monkeypatch):
    owner, _, provenance = seed(db)
    target = add_alias(db, owner, "isolation-test.virtual.prod", provenance)
    assert [row["content_id"] for row in db.get_virtual_content_aliases(owner)] == [target]
    candidate = search(db, monkeypatch, [owner], stages=["prod"])[0]
    assert candidate.content_id == target
    assert candidate.summary == "Own virtual analysis"
    from rcars.services.recommender.drivers.hands_on import HandsOnDriver
    assert HandsOnDriver().fetch_analysis(db, candidate)["content_id"] == target


def test_infrastructure_base_is_not_a_content_alias(db, monkeypatch):
    owner, _, provenance = seed(db)
    add_alias(db, owner, "isolation-test.virtual.prod", provenance, explicit=False)
    assert db.get_virtual_content_aliases(owner) == []
    assert search(db, monkeypatch, [owner])[0].content_id == owner


def test_multiple_virtual_targets_are_not_selected_arbitrarily(db, monkeypatch):
    owner, _, provenance = seed(db)
    first = add_alias(db, owner, "isolation-test.first.prod", provenance)
    second = add_alias(db, owner, "isolation-test.second.prod", provenance)
    candidates = search(db, monkeypatch, [first, second], stages=["prod"], scope=[first, second])
    assert [c.content_id for c in candidates] == [first, second]
    assert search(db, monkeypatch, [owner], stages=["prod"])[0].content_id == owner


def test_independent_ids_keep_their_own_scores(db, monkeypatch):
    a, _, _ = seed(db, "isolation-test.a.prod")
    b, _, _ = seed(db, "isolation-test.b.prod")
    candidates = search(db, monkeypatch, [a, b], stages=["prod"])
    assert [c.content_id for c in candidates] == [a, b]
    assert candidates[0].vector_distance < candidates[1].vector_distance
