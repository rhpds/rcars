from types import SimpleNamespace

from tests.showroom_helpers import db
from rcars.services.showroom_source import ResolvedShowroom

URL = "https://github.com/example/content"


def add_item(db, name, *, owner_ci_name=None, paths=None, override_origins=None, repo=URL, **overrides):
    owner = owner_ci_name or name
    source = ResolvedShowroom("resolved", owner, name.rsplit(".", 1)[0], repo, "main",
                              paths=paths or ((name,),),
                              override_origins=override_origins or {})
    return db.upsert_babylon_catalog_item({
        "ci_name": name, "stage": name.rsplit(".", 1)[-1], "display_name": name,
        "category": "Workshop", "showroom_url": repo, "showroom_ref": "main",
        "showroom_source": source.to_dict(), **overrides})


def seed_stub_artifacts(db, content_id, summary="Own stub summary"):
    db.upsert_showroom_analysis({"content_id": content_id, "summary": summary,
                                 "modules_json": [], "content_hash": "content"})
    db.store_embedding(content_id, "lab", "babylon", "summary", summary, [0.1] * 768)


def test_get_pure_stubs_for_owner_returns_only_pure_stubs(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod",
                    paths=(("isolation-test.virtual.prod", "isolation-test.owner.prod"),))
    overridden = add_item(db, "isolation-test.override.prod", owner_ci_name="isolation-test.owner.prod",
                          paths=(("isolation-test.override.prod", "isolation-test.owner.prod"),),
                          override_origins={"ref": "isolation-test.middle.prod"})
    rows = db.get_pure_stubs_for_owner("isolation-test.owner.prod")
    assert [row["content_id"] for row in rows] == [stub]
    assert overridden not in [row["content_id"] for row in rows]


def test_get_pure_stubs_for_owner_honours_stages(db):
    add_item(db, "isolation-test.owner.prod")
    dev = add_item(db, "isolation-test.virtual.dev", owner_ci_name="isolation-test.owner.prod",
                   paths=(("isolation-test.virtual.dev", "isolation-test.owner.prod"),))
    assert [row["content_id"] for row in db.get_pure_stubs_for_owner(
        "isolation-test.owner.prod", stages=["prod"])] == []
    assert [row["content_id"] for row in db.get_pure_stubs_for_owner(
        "isolation-test.owner.prod", stages=["dev"])] == [dev]


def test_delete_stub_artifacts_removes_analysis_embeddings_and_overlaps(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    seed_stub_artifacts(db, stub)
    with db.pool.connection() as conn:
        conn.execute("INSERT INTO overlap_candidates (content_id_a, content_id_b, shared_products, "
                     "shared_topics, content_hash_a, content_hash_b) VALUES (%s, %s, 1, 1, 'a', 'b') "
                     "ON CONFLICT DO NOTHING", (owner, stub))
    result = db.delete_stub_artifacts(stub)
    assert result == {"analysis": 1, "embeddings": 1, "overlaps": 1}
    assert db.get_showroom_analysis(stub) is None
    assert db.get_embeddings_for_content(stub) == []


def test_mirror_content_owner_copies_card_fields_and_scan_status(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    db.update_content_entity_card(owner, summary="Owner summary", products_json=["OpenShift"],
                                  topics_json=["virt"], audience_json=["architect"],
                                  difficulty="intermediate")
    db.set_scan_status(owner, "success")
    db.mirror_content_owner(stub, "isolation-test.owner.prod")
    card = db.get_content_entity(stub)
    assert card["summary"] == "Owner summary"
    assert card["products_json"] == ["OpenShift"]
    assert card["topics_json"] == ["virt"]
    assert card["audience_json"] == ["architect"]
    assert card["difficulty"] == "intermediate"
    assert card["scan_status"] == "success"


def test_get_stub_reconciliation_candidates_includes_stubs(db):
    add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    ids = {row["content_id"] for row in db.get_stub_reconciliation_candidates()}
    assert stub in ids
