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


from rcars.services.showroom_scan import scan_babylon_item
from tests.test_showroom_reuse import scan, git_repo  # noqa: F401  (LLM/embedding mocks + local git)


def test_pure_stub_is_not_selected_and_scan_makes_no_llm_call(db, scan):
    owner = add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                    paths=(("isolation-test.virtual.prod", "isolation-test.a.prod"),),
                    repo=scan.source.repo)
    assert stub not in {row["content_id"] for row in db.get_items_needing_analysis(scan.settings)}
    seed_stub_artifacts(db, stub)
    scan.llm.reset_mock()
    scan.embed.reset_mock()
    result = scan_babylon_item(db, scan.settings, stub)
    assert result["outcome"] == "content_owner_stub"
    assert result["success"] is True
    assert scan.llm.call_count == scan.embed.call_count == 0
    assert db.get_showroom_analysis(stub) is None
    assert db.get_embeddings_for_content(stub) == []


def test_stub_with_a_mid_chain_override_is_scanned(db, scan):
    add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    overridden = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                          paths=(("isolation-test.virtual.prod", "isolation-test.a.prod"),),
                          override_origins={"ref": "isolation-test.middle.prod"},
                          repo=scan.source.repo)
    assert overridden in {row["content_id"] for row in db.get_items_needing_analysis(scan.settings)}
    scan.llm.reset_mock()
    assert scan_babylon_item(db, scan.settings, overridden)["outcome"] in ("analyzed", "reused")
    assert scan.llm.call_count == 1


def test_stub_with_a_curator_content_path_is_scanned(db, scan):
    add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    overridden = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                          repo=scan.source.repo)
    db.set_content_path(overridden, "content/modules/ROOT/pages")
    assert overridden in {row["content_id"] for row in db.get_items_needing_analysis(scan.settings)}


def test_stale_check_candidates_exclude_pure_stubs(db):
    add_item(db, "isolation-test.a.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod")
    seed_stub_artifacts(db, stub)
    ids = {row["content_id"] for row in db.get_stale_check_candidates()}
    assert stub not in ids


def test_mirror_content_owner_is_a_no_op_while_the_owner_has_no_summary(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    db.update_content_entity_card(stub, summary="Stub keeps this")
    db.mirror_content_owner(stub, "isolation-test.owner.prod")
    assert db.get_content_entity(stub)["summary"] == "Stub keeps this"


from rcars.services.showroom_scan import reconcile_pure_stubs, scan_candidates


def test_reconcile_clears_stub_artifacts_and_mirrors_owner_card(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    db.update_content_entity_card(owner, summary="Owner summary", products_json=["OpenShift"])
    db.set_scan_status(owner, "success")
    seed_stub_artifacts(db, stub)
    result = reconcile_pure_stubs(db)
    assert result["cleared"] >= 1
    assert db.get_showroom_analysis(stub) is None
    assert db.get_embeddings_for_content(stub) == []
    assert db.get_content_entity(stub)["summary"] == "Owner summary"
    assert db.get_content_entity(stub)["scan_status"] == "success"


def test_reconcile_leaves_the_owner_analysis_alone(db):
    owner = add_item(db, "isolation-test.owner.prod")
    add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    seed_stub_artifacts(db, owner, summary="Owner analysis")
    reconcile_pure_stubs(db)
    assert db.get_showroom_analysis(owner)["summary"] == "Owner analysis"
    assert db.get_embeddings_for_content(owner)


def test_scan_candidates_reconciles_before_selecting(db, scan):
    owner = add_item(db, "isolation-test.owner.prod", repo=scan.source.repo)
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod",
                    repo=scan.source.repo)
    seed_stub_artifacts(db, stub)
    ids = {row["content_id"] for row in scan_candidates(db, scan.settings)}
    assert stub not in ids
    assert db.get_showroom_analysis(stub) is None


def test_rescan_all_never_enqueues_a_pure_stub(db, scan):
    import asyncio
    from unittest.mock import AsyncMock
    from rcars.api.routes.analysis import rescan_all
    add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                    repo=scan.source.repo)
    redis = SimpleNamespace(enqueue_job=AsyncMock())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        db=db, arq_redis=redis, settings=scan.settings)))
    asyncio.run(rescan_all(request, user="isolation-test@example.com"))
    enqueued = {call.kwargs["content_id"] for call in redis.enqueue_job.call_args_list}
    assert stub not in enqueued
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM jobs WHERE created_by IN ('isolation-test@example.com', 'rescan-all')")


def test_owner_scan_mirrors_card_fields_to_its_stub(db, scan):
    owner = add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                    repo=scan.source.repo)
    assert scan_babylon_item(db, scan.settings, owner)["success"]
    card = db.get_content_entity(stub)
    assert card["summary"] == "Configure TLS"
    assert card["scan_status"] == "success"


def test_unchanged_owner_scan_still_mirrors_a_newly_added_stub(db, scan):
    owner = add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    assert scan_babylon_item(db, scan.settings, owner)["outcome"] == "analyzed"
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                    repo=scan.source.repo)
    result = scan_babylon_item(db, scan.settings, owner)
    assert result["outcome"] == "unchanged"
    assert db.get_content_entity(stub)["summary"] == "Configure TLS"
    assert db.get_content_entity(stub)["scan_status"] == "success"


def test_display_analysis_of_a_stub_is_the_owner_analysis(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    seed_stub_artifacts(db, owner, summary="Owner analysis")
    assert db.get_display_analysis(stub)["summary"] == "Owner analysis"


def test_display_analysis_of_an_owner_is_its_own_analysis(db):
    owner = add_item(db, "isolation-test.owner.prod")
    seed_stub_artifacts(db, owner, summary="Owner analysis")
    assert db.get_display_analysis(owner)["summary"] == "Owner analysis"
