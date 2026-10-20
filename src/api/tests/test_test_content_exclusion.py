"""The AgnosticV tests folder is infrastructure/testing, never content inventory."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from tests.showroom_helpers import db
from tests.test_showroom_scope_db import seed
from rcars.config import Settings
from rcars.services.showroom_source import (
    ContentDeclaration, SourceNode, ComponentLink, effective_showroom_source, resolve_showroom_source,
)

TEST_NAME = "tests.rcars-isolation-exclusion.prod"
TEST_ID = "babylon:" + TEST_NAME
URL = "https://github.com/example/content"


@pytest.fixture
def legacy_test_item(db):
    # Seed existing analysis/vectors, including status=success, as on pre-policy dev.
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM embeddings WHERE content_id = %s", (TEST_ID,))
        conn.execute("DELETE FROM content_entities WHERE content_id = %s", (TEST_ID,))
    cid, _, _ = seed(db, TEST_NAME)
    yield cid
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM embeddings WHERE content_id = %s", (TEST_ID,))
        conn.execute("DELETE FROM content_entities WHERE content_id = %s", (TEST_ID,))


def node(name, *, repo=None, links=()):
    return SourceNode(name, name.rsplit(".", 1)[-1],
        ContentDeclaration(repo, "main", None, frozenset({"repo", "ref"}) if repo else frozenset()),
        tuple(ComponentLink(link, {}) for link in links))


def test_tests_root_is_excluded_even_with_declared_and_curator_showroom():
    root = node(TEST_NAME, repo=URL, links=("missing.component.prod",))
    assert resolve_showroom_source(TEST_NAME, {TEST_NAME: root}).status == "excluded"
    item = {"ci_name": TEST_NAME, "stage": "prod", "showroom_source": {
        "status": "resolved", "repo": URL, "ref": "main"}, "showroom_url_override": URL + "/override"}
    assert effective_showroom_source(item).status == "excluded"


def test_tests_dependency_cannot_supply_content_to_published_wrapper():
    root = node("published.example.prod", links=(TEST_NAME,))
    result = resolve_showroom_source(root.ci_name, {root.ci_name: root, TEST_NAME: node(TEST_NAME, repo=URL)})
    assert result.status == "none"
    assert result.repo is None


def test_tests_exclusion_is_not_a_fuzzy_name_filter():
    root = node("example.tests-workshop.prod", repo=URL)
    assert resolve_showroom_source(root.ci_name, {root.ci_name: root}).status == "resolved"


@pytest.mark.parametrize("force", [False, True])
def test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(db, legacy_test_item, monkeypatch, force):
    from rcars.services import showroom_scan
    before = db.get_showroom_analysis(TEST_ID)
    vectors = db.get_embeddings_for_content(TEST_ID)
    monkeypatch.setattr(showroom_scan, "analyze_showroom", Mock(side_effect=AssertionError("test content reached analysis")))
    result = showroom_scan.scan_babylon_item(db, Settings(database_url=db._url), TEST_ID, force=force)
    assert result["outcome"] == "excluded"
    assert result["success"] is True
    assert db.get_showroom_analysis(TEST_ID) == before
    assert db.get_embeddings_for_content(TEST_ID) == vectors


@pytest.mark.parametrize("force", [False, True])
def test_test_items_are_not_selected_for_scans_or_freshness_checks(db, legacy_test_item, force):
    db.mark_stale(TEST_ID)
    assert TEST_ID not in {i["content_id"] for i in db.get_items_needing_analysis(Settings(database_url=db._url), force=force)}
    assert TEST_ID not in {i["content_id"] for i in db.get_stale_check_candidates()}


def test_test_sandbox_is_not_selected_for_generated_content_summary(db, legacy_test_item):
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET content_type='sandbox',summary=NULL WHERE content_id=%s", (TEST_ID,))
    assert TEST_ID not in {i["content_id"] for i in db.get_sandboxes_needing_summary()}


@pytest.mark.parametrize("scoped", [False, True])
def test_existing_test_vectors_never_enter_content_retrieval(db, legacy_test_item, scoped):
    normal, _, _ = seed(db, "isolation-test.real-content.prod")
    rows = db.search_embeddings([0.1] * 768, quality_threshold=0, limit=100,
        stages=["prod"], scope_content_ids=[TEST_ID] if scoped else None)
    ids = {r["content_id"] for r in rows}
    assert TEST_ID not in ids
    if not scoped:
        assert normal in ids
    # Filtering is not deletion: historical artifacts and identity remain available.
    assert db.get_embeddings_for_content(TEST_ID)
    assert db.get_content_entity(TEST_ID)


def test_test_item_cannot_seed_recommendation_neighbor_expansion(db, legacy_test_item):
    from rcars.services.recommender.vector_search import _resolve_ci_references
    seed(db, "isolation-test.real-content.prod")
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET display_name='LB9876 test-only content' WHERE content_id=%s", (TEST_ID,))
    assert _resolve_ci_references("similar to LB9876", db, ["prod"], True) == []


def test_catalog_refresh_marks_test_content_excluded_without_deleting_history(db, legacy_test_item):
    before = db.get_showroom_analysis(TEST_ID)
    vectors = db.get_embeddings_for_content(TEST_ID)
    db.upsert_babylon_catalog_item({"ci_name": TEST_NAME, "stage": "prod", "showroom_url": URL,
        "showroom_source": {"status": "excluded"}})
    item = db.get_babylon_item(TEST_ID)
    assert item["scan_status"] == "excluded"
    assert item["scan_error_class"] is None
    assert item["scan_failed_at"] is None
    assert db.get_showroom_analysis(TEST_ID) == before
    assert db.get_embeddings_for_content(TEST_ID) == vectors


@pytest.mark.asyncio
async def test_manual_analysis_endpoint_rejects_test_item_before_job_creation(db, legacy_test_item):
    from rcars.api.routes.analysis import analyze_single
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db, arq_redis=AsyncMock())))
    with db.pool.connection() as conn:
        before = conn.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"]
    with pytest.raises(HTTPException) as exc:
        await analyze_single(TEST_NAME, request, force=True, user="curator@example.com")
    assert exc.value.status_code == 400
    with db.pool.connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"] == before


def test_test_item_cannot_enter_overlap_candidate_generation(db, legacy_test_item):
    from rcars.db.overlap import generate_overlap_candidates
    normal, _, _ = seed(db, "isolation-test.real-content.prod", showroom_url=URL + "/real")
    for cid, content_hash in ((normal, "real"), (TEST_ID, "test")):
        db.upsert_showroom_analysis({"content_id": cid, "products_json": ["OpenShift"],
            "topics_json": ["security", "TLS"], "content_hash": content_hash})
    generate_overlap_candidates(db.pool)
    with db.pool.connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM overlap_candidates WHERE content_id_a=%s OR content_id_b=%s",
            (TEST_ID, TEST_ID)).fetchone()["n"] == 0


def test_cached_overlap_cannot_bypass_test_content_exclusion(db, legacy_test_item):
    from rcars.services.overlap_assessment import assess_overlap
    from psycopg.types.json import Jsonb
    normal, _, _ = seed(db, "isolation-test.real-content.prod")
    a, b = sorted((normal, TEST_ID))
    with db.pool.connection() as conn:
        conn.execute("INSERT INTO overlap_candidates (content_id_a,content_id_b,llm_assessment,content_hash_a,content_hash_b) "
            "VALUES (%s,%s,%s,'content','content')", (a,b,Jsonb({"verdict":"redundant"})))
    result, reason = assess_overlap(db.pool, Settings(database_url=db._url), a, b)
    assert result is None
    assert reason == "excluded_content"


def test_old_test_overlap_does_not_enter_advisor_evidence(db, legacy_test_item):
    from rcars.services.chat.evidence import build_evidence_pack
    normal, _, _ = seed(db, "isolation-test.real-content.prod")
    a, b = sorted((normal, TEST_ID))
    with db.pool.connection() as conn:
        conn.execute("INSERT INTO overlap_candidates (content_id_a,content_id_b,shared_products,shared_topics) VALUES (%s,%s,3,4)", (a,b))
    assert build_evidence_pack(db, [normal]) == []


def test_ignored_test_dependency_does_not_block_a_real_content_branch():
    root = node("published.example.prod", links=(TEST_NAME, "example.content.prod"))
    result = resolve_showroom_source(root.ci_name, {root.ci_name: root,
        TEST_NAME: node(TEST_NAME, repo=URL + "/test"),
        "example.content.prod": node("example.content.prod", repo=URL)})
    assert result.status == "resolved"
    item = {"ci_name": root.ci_name, "stage": "prod", "showroom_source": result.to_dict()}
    assert effective_showroom_source(item).status == "resolved"


def test_legacy_test_sourced_wrapper_is_not_recommended(db, legacy_test_item, monkeypatch):
    from psycopg.types.json import Jsonb
    from rcars.services.recommender import vector_search
    cid, _, provenance = seed(db, "isolation-test.virtual.prod")
    source = {**provenance["source"], "owner_ci_name": TEST_NAME,
        "paths": [["isolation-test.virtual.prod", TEST_NAME]]}
    with db.pool.connection() as conn:
        conn.execute("UPDATE babylon_items SET showroom_source_json=%s WHERE content_id=%s", (Jsonb(source),cid))
    monkeypatch.setattr(vector_search, "generate_embedding", lambda *a, **k: [0.1] * 768)
    assert vector_search.search("TLS", db, stages=["prod"], scope_content_ids=[cid]).candidates == []


def test_non_test_curator_override_can_replace_old_test_content_source():
    item = {"ci_name": "published.real.prod", "stage": "prod", "showroom_url_override": URL,
        "showroom_source": {"status": "resolved", "owner_ci_name": TEST_NAME,
            "repo": URL + "/test", "paths": [["published.real.prod", TEST_NAME]]}}
    source = effective_showroom_source(item)
    assert source.status == "resolved"
    assert source.owner_ci_name == "published.real.prod"
    assert source.repo == URL


def test_old_test_failures_are_not_reported_as_content_scan_failures(db, legacy_test_item):
    db.set_scan_status(TEST_ID, "failed", "invalid_source", "Old test config")
    assert TEST_ID not in {i["content_id"] for i in db.get_scan_failures()}
