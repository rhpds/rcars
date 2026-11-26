from dataclasses import replace

import pytest

from tests.showroom_helpers import db
from rcars.services.showroom_source import AnalysisSignature, ResolvedShowroom

URL = "https://github.com/example/content"


def CONFIG_FOR_EXAMPLE(model):
    from rcars.services.analysis_identity import compute_analysis_config
    return compute_analysis_config("isolation-test.item", "Example", "", "", "lab", model)


def by_commit(db, signature, **changes):
    args = dict(repo=signature.repo, commit=signature.commit, content_path=signature.content_path,
                analysis_config=signature.analysis_config, entity_content_type="lab",
                exclude_content_id="babylon:isolation-test.item.dev")
    return db.find_showroom_donor_by_commit(**{**args, **changes})


def by_content(db, signature, **changes):
    args = dict(content_hash=signature.content_hash, analysis_config=signature.analysis_config,
                entity_content_type="lab", exclude_content_id="babylon:isolation-test.item.dev")
    return db.find_showroom_donor_by_content(**{**args, **changes})


def seed(db, name="isolation-test.item.prod", **overrides):
    from rcars.config import Settings
    from rcars.services.analysis_identity import compute_analysis_config
    from rcars.services.analyzer import compute_embedding_fingerprint
    settings = Settings(database_url=db._url)
    source = ResolvedShowroom("resolved", name, "isolation-test.item", URL, "main",
                              paths=((name,),)).to_dict()
    content_id = db.upsert_babylon_catalog_item({
        "ci_name": name, "stage": name.rsplit(".", 1)[-1], "display_name": "Example",
        "showroom_url": URL, "showroom_ref": "main", "showroom_source": source,
        **overrides,
    })
    signature = AnalysisSignature("isolation-test.item", URL, "main", None, "a" * 40,
                                   "content", CONFIG_FOR_EXAMPLE(settings.model), "input", 1)
    provenance = {"signature": signature.to_dict(), "source": source,
                  "generated_for": content_id, "generated_commit": "a" * 40,
                  "reused_from": None, "embedding_fingerprints": {"summary": compute_embedding_fingerprint(
                      "A real lab Example", settings.embedding_model, {"prefix": "search_document", "dimensions": settings.embedding_dim}), "modules": {}}}
    db.upsert_showroom_analysis({"content_id": content_id, "summary": "A real lab",
                                "modules_json": [], "content_hash": "content",
                                "analysis_provenance_json": provenance})
    db.set_scan_status(content_id, "success")
    db.store_embedding(content_id, "lab", "babylon", "summary", "A real lab Example", [0.1] * 768)
    return content_id, signature, provenance


def test_other_stage_of_the_same_ci_is_a_donor_for_both_lookups(db):
    content_id, signature, _ = seed(db)
    assert by_commit(db, signature)["content_id"] == content_id
    assert by_content(db, signature)["content_id"] == content_id


def test_another_ci_is_a_donor_when_it_has_the_same_analysis_config(db):
    content_id, signature, _ = seed(db)
    other = "babylon:isolation-test.other.dev"
    assert by_commit(db, signature, exclude_content_id=other)["content_id"] == content_id
    assert by_content(db, signature, exclude_content_id=other)["content_id"] == content_id


def test_ref_name_and_ci_scope_never_decide(db):
    """Same files under another ref name or CI scope: the donor is still found."""
    from psycopg.types.json import Jsonb
    content_id, signature, provenance = seed(db)
    provenance["signature"].update(ref="v1.2", scope_key="isolation-test.other", input_hash="another")
    provenance["source"] = {**provenance["source"], "ref": "v1.2", "scope_key": "isolation-test.other"}
    with db.pool.connection() as conn:
        conn.execute("UPDATE showroom_analysis SET analysis_provenance_json = %s WHERE content_id = %s",
                     (Jsonb(provenance), content_id))
        conn.execute("UPDATE babylon_items SET showroom_source_json = %s WHERE content_id = %s",
                     (Jsonb(provenance["source"]), content_id))
    assert by_commit(db, signature)["content_id"] == content_id
    assert by_content(db, signature)["content_id"] == content_id


@pytest.mark.parametrize("changes", [{"repo": URL + "/other"}, {"commit": "b" * 40}, {"content_path": "other"},
                                     {"analysis_config": "other"}, {"entity_content_type": "architecture"}])
def test_pre_clone_lookup_needs_repo_commit_path_config_and_type(db, changes):
    _, signature, _ = seed(db)
    assert by_commit(db, signature, **changes) is None


@pytest.mark.parametrize("changes", [{"content_hash": "other"}, {"analysis_config": "other"},
                                     {"entity_content_type": "architecture"}])
def test_post_clone_lookup_needs_content_hash_config_and_type(db, changes):
    _, signature, _ = seed(db)
    assert by_content(db, signature, **changes) is None


def test_the_item_never_donates_to_itself(db):
    content_id, signature, _ = seed(db)
    assert by_commit(db, signature, exclude_content_id=content_id) is None
    assert by_content(db, signature, exclude_content_id=content_id) is None


def test_description_analysis_is_never_a_showroom_donor(db):
    content_id, signature, provenance = seed(db)
    from psycopg.types.json import Jsonb
    provenance["signature"]["repo"] = "description:isolation-test.item.prod"
    with db.pool.connection() as conn:
        conn.execute("UPDATE showroom_analysis SET analysis_provenance_json = %s WHERE content_id = %s",
                     (Jsonb(provenance), content_id))
    assert by_content(db, signature) is None


def test_prod_donor_is_preferred_over_dev(db):
    dev_id, signature, _ = seed(db, "isolation-test.item.dev")
    prod_id, _, _ = seed(db, "isolation-test.item.prod")
    assert by_content(db, signature, exclude_content_id="babylon:isolation-test.item.event")["content_id"] == prod_id
    assert by_commit(db, signature, exclude_content_id="babylon:isolation-test.item.event")["content_id"] == prod_id


@pytest.mark.parametrize("state", ["stale", "failed", "retired", "legacy", "missing_summary", "missing_module"])
def test_stale_failed_retired_or_legacy_donor_is_rejected(db, state):
    content_id, signature, _ = seed(db)
    with db.pool.connection() as conn:
        if state == "stale":
            conn.execute("UPDATE showroom_analysis SET is_stale = TRUE WHERE content_id = %s", (content_id,))
        elif state in ("failed", "retired"):
            conn.execute("UPDATE content_entities SET " + ("scan_status = 'failed'" if state == "failed" else "retired_at = NOW()") + " WHERE content_id = %s", (content_id,))
        elif state == "legacy":
            conn.execute("UPDATE showroom_analysis SET analysis_provenance_json = NULL WHERE content_id = %s", (content_id,))
        elif state == "missing_summary":
            conn.execute("DELETE FROM embeddings WHERE content_id = %s", (content_id,))
        else:
            from psycopg.types.json import Jsonb
            conn.execute("UPDATE showroom_analysis SET modules_json = %s WHERE content_id = %s",
                         (Jsonb([{"title": "Missing", "topics": ["security"]}]), content_id))
    assert by_commit(db, signature) is None
    assert by_content(db, signature) is None


def test_reuse_stats_count_llm_runs_against_distinct_content(db):
    from psycopg.types.json import Jsonb
    before = db.get_scan_reuse_stats()
    first, _, provenance = seed(db, "isolation-test.a.prod")
    second, _, _ = seed(db, "isolation-test.b.prod")           # same content, own LLM run: an extra run
    third, _, reused = seed(db, "isolation-test.c.prod")       # same content, copied from a donor
    reused["reused_from"] = first
    with db.pool.connection() as conn:
        conn.execute("UPDATE showroom_analysis SET analysis_provenance_json = %s WHERE content_id = %s",
                     (Jsonb(reused), third))
    after = db.get_scan_reuse_stats()
    assert after["analyses"] - before["analyses"] == 3
    assert after["llm_runs"] - before["llm_runs"] == 2
    assert after["reused"] - before["reused"] == 1
    assert after["extra_llm_runs"] - before["extra_llm_runs"] == 1
    assert after["extra_llm_runs_hash_only"] >= after["extra_llm_runs"]


def test_source_and_analysis_provenance_round_trip_and_schema_idempotence(db):
    content_id, _, provenance = seed(db)
    db.create_schema()
    db.create_schema()
    assert db.get_babylon_item(content_id)["showroom_source_json"] == provenance["source"]
    assert db.get_showroom_analysis(content_id)["analysis_provenance_json"] == provenance


def test_independent_items_and_virtual_stages_are_not_deduplicated(db):
    for name in ("isolation-test.a.prod", "isolation-test.b.prod", "isolation-test.virtual.dev"):
        db.upsert_babylon_catalog_item({"ci_name": name, "stage": name.rsplit(".", 1)[-1],
            "showroom_url": URL, "showroom_source": ResolvedShowroom("resolved", name, name, URL).to_dict(),
            "is_published": "virtual" in name})
    selected = {row["ci_name"] for row in db.get_items_needing_analysis()}
    assert selected >= {"isolation-test.a.prod", "isolation-test.b.prod", "isolation-test.virtual.dev"}


def test_resolution_failure_keeps_curated_fields_and_is_visible(db):
    content_id, _, _ = seed(db)
    with db.pool.connection() as conn:
        conn.execute("UPDATE showroom_analysis SET curated_duration_min = 45, notes = 'Human note' WHERE content_id = %s", (content_id,))
    db.upsert_babylon_catalog_item({"ci_name": "isolation-test.item.prod", "stage": "prod",
                                   "showroom_url": None,
                                   "showroom_source": ResolvedShowroom("ambiguous", error="multiple_content_sources").to_dict()})
    assert db.get_babylon_item(content_id)["scan_error_class"] == "ambiguous_source"
    analysis = db.get_showroom_analysis(content_id)
    assert analysis["notes"] == "Human note"
    assert analysis["curated_duration_min"] == 45


def test_unchanged_complete_item_is_not_selected(db):
    content_id, _, _ = seed(db)
    assert content_id not in {row["content_id"] for row in db.get_items_needing_analysis()}


def test_missing_embedding_is_selected_for_repair(db):
    content_id, _, _ = seed(db)
    db.clear_embeddings(content_id)
    assert content_id in {row["content_id"] for row in db.get_items_needing_analysis()}
