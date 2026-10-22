from dataclasses import replace

import pytest

from tests.showroom_helpers import db
from rcars.services.showroom_source import AnalysisSignature, ResolvedShowroom

URL = "https://github.com/example/content"


def seed(db, name="isolation-test.item.prod", **overrides):
    from rcars.config import Settings
    from rcars.services.analyzer import build_analysis_prompt, compute_analysis_context_hash, compute_embedding_fingerprint
    settings = Settings(database_url=db._url)
    source = ResolvedShowroom("resolved", name, "isolation-test.item", URL, "main",
                              paths=((name,),)).to_dict()
    content_id = db.upsert_babylon_catalog_item({
        "ci_name": name, "stage": name.rsplit(".", 1)[-1], "display_name": "Example",
        "showroom_url": URL, "showroom_ref": "main", "showroom_source": source,
        **overrides,
    })
    system, info = build_analysis_prompt("isolation-test.item", "Example", "", "", {})
    signature = AnalysisSignature("isolation-test.item", URL, "main", None, "a" * 40,
                                   "content", compute_analysis_context_hash(system, info, settings.model), "input", 1)
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


def test_same_item_matching_signature_reuses_stage(db):
    content_id, signature, _ = seed(db)
    donor = db.find_showroom_donor(signature, exclude_content_id="babylon:isolation-test.item.dev")
    assert donor["content_id"] == content_id


def test_unrelated_identical_repo_ref_sha_hash_is_not_donor(db):
    _, signature, _ = seed(db)
    assert db.find_showroom_donor(replace(signature, scope_key="isolation-test.other"),
                                   exclude_content_id="babylon:isolation-test.other.dev") is None


@pytest.mark.parametrize("field,value", [("scope_key", "other"), ("repo", URL + "/other"),
    ("ref", None), ("content_path", "other"), ("commit", "b" * 40), ("content_hash", "other"),
    ("context_hash", "other"), ("input_hash", "other"), ("policy_version", 2)])
def test_every_signature_field_must_match(db, field, value):
    _, signature, _ = seed(db)
    assert db.find_showroom_donor(replace(signature, **{field: value}), exclude_content_id="target") is None


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
    assert db.find_showroom_donor(signature, exclude_content_id="target") is None


def test_source_and_analysis_provenance_round_trip_and_schema_idempotence(db):
    content_id, _, provenance = seed(db)
    db.create_schema()
    db.create_schema()
    assert db.get_babylon_item(content_id)["showroom_source_json"] == provenance["source"]
    assert db.get_showroom_analysis(content_id)["analysis_provenance_json"] == provenance


def test_stage_counterpart_does_not_match_lab_numbers_or_infrastructure_base(db):
    content_id, _, _ = seed(db)
    db.upsert_babylon_catalog_item({"ci_name": "isolation-test.item.dev", "stage": "dev"})
    db.upsert_babylon_catalog_item({"ci_name": "isolation-test.other.prod", "stage": "prod",
                                   "base_ci_name": "isolation-test.item.dev"})
    assert db.get_stage_counterpart("babylon:isolation-test.item.dev", "prod")["content_id"] == content_id
    assert db.get_stage_counterpart("babylon:isolation-test.missing.dev", "prod") is None


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
