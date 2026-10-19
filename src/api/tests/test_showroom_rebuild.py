"""Reset only disposable artifacts: compare all protected data, not just counts."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tests.showroom_helpers import db
from tests.test_showroom_scope_db import seed


def snapshots(db, tables):
    with db.pool.connection() as conn:
        return {table: conn.execute(f"SELECT to_jsonb(t) AS data FROM {table} t ORDER BY to_jsonb(t)::text").fetchall()
                for table in tables}


def test_reset_preserves_all_curated_historical_and_architecture_data(db):
    from dataclasses import replace
    from rcars.services.showroom_source import effective_showroom_source
    target, signature, provenance = seed(db)
    other, _, _ = seed(db, "isolation-test.other.prod")
    architecture = db.upsert_osspa_item({"content_id": "pa:987654321", "ppid": 987654321,
        "display_name": "Architecture fixture", "status": "prod", "summary": "Architecture summary"})
    db.upsert_architecture_analysis({"content_id": architecture, "summary": "Preserved architecture"})
    db.store_embedding(architecture, "architecture", "portfolio_arch", "summary", "Architecture summary", [0.2] * 768)
    db.set_content_path(target, "curated/pages")
    db.set_showroom_url_override(target, "https://github.com/example/curated")
    # Overrides correctly invalidate previous generated content. Seed the
    # post-override artifacts that this maintenance reset will actually clear.
    source = effective_showroom_source(db.get_babylon_item(target))
    provenance["source"] = source.to_dict()
    provenance["signature"] = replace(signature, scope_key=source.scope_key, repo=source.repo, content_path=source.content_path).to_dict()
    db.upsert_showroom_analysis({"content_id": target, "summary": "Old generated summary", "content_hash": "content",
        "last_repo_commit": "a" * 40, "modules_json": [{"title": "TLS", "topics": ["security"]}],
        "analysis_provenance_json": provenance})
    db.store_embedding(target, "lab", "babylon", "summary", "Old generated summary", [0.1] * 768)
    db.store_embedding(target, "lab", "babylon", "module", "TLS module", [0.1] * 768, "TLS")
    db.store_embedding(target, "lab", "babylon", "infrastructure", "Unrelated vector", [0.1] * 768)
    with db.pool.connection() as conn:
        conn.execute("UPDATE showroom_analysis SET curated_duration_min = 37, notes = 'Curated note', "
                     "enrichment_review_needed = TRUE, review_reasons = '[\"review\"]' WHERE content_id = %s", (target,))
        conn.execute("UPDATE content_entities SET retired_at = NOW(), retirement_reason = 'Preserve retirement', "
                     "summary = 'Old generated summary', difficulty = 'beginner' WHERE content_id = %s", (target,))
        conn.execute("INSERT INTO performance_channels (content_id, channel, provisions) VALUES (%s, 'sales', 12)", (target,))
        conn.execute("INSERT INTO performance_scores (content_id, performance_score) VALUES (%s, 55)", (target,))
        conn.execute("INSERT INTO nonprod_usage (content_id, catalog_base_name, provisions) VALUES (%s, 'isolation-test.item', 7)", (target,))
        conn.execute("INSERT INTO retirement_workflow (content_id, jira_key, curator_notes, agv_notice_pr_url) "
                     "VALUES (%s, 'RHDPCD-123', 'Preserve workflow', 'https://github.com/example/catalog/pull/1')", (target,))
        conn.execute("INSERT INTO enrichment_tags (content_id, tag_type, tag_value) VALUES (%s, 'product', 'Curated')", (target,))
        conn.execute("INSERT INTO advisor_sessions (session_id, turn_index, chosen_content_id) VALUES ('isolation-test-session', 0, %s)", (target,))
        conn.execute("INSERT INTO analysis_log (ci_name, action) VALUES ('isolation-test.item.prod', 'curated')")
        conn.execute("INSERT INTO overlap_candidates (content_id_a, content_id_b) VALUES (%s, %s), (%s, %s)",
                     (target, other, other, architecture))
    db.upsert_field_source_provisions([{"catalog_item": "isolation-test", "git_repo": "https://github.com/example/content",
        "git_ref": "main", "provision_uuid": "isolation-test-provision", "provisioned_at": "2026-10-01T00:00:00Z",
        "retired_at": None, "cloud_provider": "cnv", "cluster_size": "sno", "node_size": None}])
    job = db.create_job(job_type="analyze", queue="analyze", created_by="isolation-test")
    db.complete_job(job, result_json={"old": "history"})
    db.log_token_usage("scan", "example-model", 12, 10, ci_name="isolation-test.item.prod")
    protected = ["performance_channels", "performance_scores", "nonprod_usage", "field_source_provisions",
                 "retirement_workflow", "enrichment_tags", "advisor_sessions", "analysis_log", "token_usage", "jobs",
                 "babylon_items", "babylon_item_workloads", "babylon_item_acl_groups", "infrastructure",
                 "vocabulary_unknown_terms", "role_assignments", "api_keys", "architecture_analysis", "portfolio_architectures"]
    before = snapshots(db, protected)
    old_entity = db.get_content_entity(target)
    other_analysis = db.get_showroom_analysis(other)
    other_embeddings = db.get_embeddings_for_content(other)
    architecture_embeddings = db.get_embeddings_for_content(architecture)
    curated = {key: db.get_showroom_analysis(target)[key] for key in
               ("notes", "curated_duration_min", "enrichment_review_needed", "review_reasons")}
    counts = db.reset_babylon_scan_artifacts([target])
    assert counts["analysis"] == 1
    assert counts["embeddings"] == 2
    assert counts["overlaps"] == 1
    assert snapshots(db, protected) == before
    analysis = db.get_showroom_analysis(target)
    assert {key: analysis[key] for key in curated} == curated
    for key in ("summary", "content_hash", "last_analyzed", "last_repo_commit", "analysis_provenance_json", "modules_json"):
        assert analysis[key] is None
    entity = db.get_content_entity(target)
    for key in ("retired_at", "retirement_reason", "created_at", "content_id", "content_type", "display_name", "status"):
        assert entity[key] == old_entity[key]
    assert entity["summary"] is None
    assert entity["scan_status"] == "not_scanned"
    assert [row["embed_type"] for row in db.get_embeddings_for_content(target)] == ["infrastructure"]
    assert db.get_showroom_analysis(other) == other_analysis
    assert db.get_embeddings_for_content(other) == other_embeddings
    assert db.get_embeddings_for_content(architecture) == architecture_embeddings
    with db.pool.connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM overlap_candidates WHERE content_id_a = %s", (other,)).fetchone()["n"] == 1
        conn.execute("DELETE FROM embeddings WHERE content_id = %s", (architecture,))
        conn.execute("DELETE FROM content_entities WHERE content_id = %s", (architecture,))
        conn.execute("DELETE FROM advisor_sessions WHERE session_id = 'isolation-test-session'")
        conn.execute("DELETE FROM field_source_provisions WHERE provision_uuid = 'isolation-test-provision'")


@pytest.mark.parametrize("status", ["running", "queued"])
@pytest.mark.parametrize("kind", ["analyze", "maintenance", "check_stale", "refresh", "sandbox_summary"])
def test_reset_rejects_running_or_queued_analysis_jobs(db, status, kind):
    target, _, _ = seed(db)
    job = db.create_job(job_type=kind, queue="ops", created_by="isolation-test")
    db.update_job_status(job, status)
    before = db.get_showroom_analysis(target)
    with pytest.raises(RuntimeError, match="outstanding"):
        db.reset_babylon_scan_artifacts([target])
    assert db.get_showroom_analysis(target) == before


def test_reset_rejects_non_babylon_or_missing_ids_atomically(db):
    target, _, _ = seed(db)
    before = db.get_showroom_analysis(target)
    for invalid in ("pa:123", "babylon:missing.prod"):
        with pytest.raises(ValueError):
            db.reset_babylon_scan_artifacts([target, invalid])
    assert db.get_showroom_analysis(target) == before


def test_full_reset_preserves_non_showroom_sandbox_card(db):
    from rcars.services.showroom_source import ResolvedShowroom
    cid = db.upsert_babylon_catalog_item({"ci_name": "isolation-test.sandbox.prod", "stage": "prod",
        "showroom_source": ResolvedShowroom("none").to_dict()})
    db.update_content_entity_card(cid, summary="Sandbox infrastructure summary", products_json=["OpenShift"])
    before = db.get_content_entity(cid)
    counts = db.preview_babylon_scan_artifacts([cid])
    assert counts["items"] == 0
    assert db.reset_babylon_scan_artifacts([cid])["items"] == 0
    assert db.get_content_entity(cid) == before


def test_execute_requires_scans_paused_confirmation(monkeypatch):
    from scripts import rebuild_babylon_analysis as script
    connect = Mock(side_effect=AssertionError("must reject before connecting"))
    monkeypatch.setattr(script, "Database", connect)
    with pytest.raises(SystemExit) as error:
        script.main(["--content-id", "babylon:isolation-test.item.prod", "--execute"])
    assert error.value.code == 2
    assert connect.call_count == 0


def test_dry_run_performs_no_writes(db, monkeypatch, capsys):
    from scripts import rebuild_babylon_analysis as script
    target, _, _ = seed(db)
    before = snapshots(db, ["showroom_analysis", "embeddings", "content_entities", "jobs"])
    monkeypatch.setattr(script, "Settings", lambda: SimpleNamespace(database_url=db._url))
    monkeypatch.setattr(script, "Database", lambda _: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(db, "reset_babylon_scan_artifacts", Mock(side_effect=AssertionError("dry run wrote")))
    assert script.main(["--content-id", target]) == 0
    assert "dry_run" in capsys.readouterr().out
    assert snapshots(db, ["showroom_analysis", "embeddings", "content_entities", "jobs"]) == before
