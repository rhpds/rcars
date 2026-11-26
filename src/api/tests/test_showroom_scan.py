from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from click.testing import CliRunner

from tests.showroom_helpers import db
from tests.test_showroom_reuse import scan, git_repo
from rcars.services.showroom_source import ResolvedShowroom
from rcars.services.showroom_scan import scan_babylon_item


def add_item(db, scan, name="isolation-test.a.prod", scope=None, ref=None, **fields):
    source = replace(scan.source, owner_ci_name=name, scope_key=scope or name.rsplit(".", 1)[0], paths=((name,),),
                     **({"ref": ref} if ref else {}))
    return db.upsert_babylon_catalog_item({"ci_name": name, "stage": name.rsplit(".", 1)[-1],
        "display_name": "TLS workshop", "category": "Workshop", "showroom_url": source.repo,
        "showroom_ref": source.ref, "showroom_source": source.to_dict(), **fields})


def test_scanning_a_never_writes_identical_unrelated_b(db, scan):
    a = add_item(db, scan)
    b = add_item(db, scan, "isolation-test.b.prod")
    result = scan_babylon_item(db, scan.settings, a)
    assert result["outcome"] == "analyzed"
    assert db.get_showroom_analysis(a)["summary"] == "Configure TLS"
    assert db.get_content_entity(a)["summary"] == "Configure TLS"
    assert db.get_showroom_analysis(b) is None
    assert db.get_embeddings_for_content(b) == []
    assert db.get_babylon_item(b)["scan_status"] == "not_scanned"


def test_four_level_virtual_is_a_stub_with_no_artifacts_of_its_own(db, scan):
    owner = add_item(db, scan, "isolation-test.owner.prod")
    scan_babylon_item(db, scan.settings, owner)
    source = replace(scan.source, owner_ci_name="isolation-test.owner.prod", scope_key="isolation-test.owner",
        paths=(("isolation-test.virtual.prod", "example.wrapper.prod", "example.content.prod", "isolation-test.owner.prod"),))
    target = db.upsert_babylon_catalog_item({"ci_name": "isolation-test.virtual.prod", "stage": "prod",
        "display_name": "TLS workshop", "category": "Workshop", "keywords": ["target-only"],
        "showroom_url": source.repo, "showroom_ref": source.ref, "showroom_source": source.to_dict(), "is_published": True})
    scan.llm.reset_mock()
    result = scan_babylon_item(db, scan.settings, target)
    assert result["outcome"] == "content_owner_stub"
    assert scan.llm.call_count == 0
    assert db.get_showroom_analysis(target) is None
    assert db.get_embeddings_for_content(target) == []
    assert db.get_content_entity(target)["summary"] == "Configure TLS"


def test_source_changed_during_analysis_discards_result(db, scan, monkeypatch):
    from rcars.services import showroom_scan
    content_id = add_item(db, scan)
    analyze = showroom_scan.analyze_showroom

    def change_source(**kwargs):
        result = analyze(**kwargs)
        db.set_content_path(content_id, "different/pages")
        return result

    monkeypatch.setattr(showroom_scan, "analyze_showroom", change_source)
    result = scan_babylon_item(db, scan.settings, content_id)
    assert result["outcome"] == "superseded"
    assert result["success"] is False
    assert db.get_showroom_analysis(content_id) is None
    assert db.get_embeddings_for_content(content_id) == []


def test_analysis_card_and_embeddings_roll_back_together(db, scan, monkeypatch):
    content_id = add_item(db, scan)
    monkeypatch.setattr(db, "replace_embeddings", Mock(side_effect=RuntimeError("storage failed")))
    result = scan_babylon_item(db, scan.settings, content_id)
    assert not result["success"]
    assert db.get_showroom_analysis(content_id) is None
    assert db.get_content_entity(content_id)["summary"] is None


def test_unchanged_scan_does_not_replace_artifacts_or_generation_time(db, scan, monkeypatch):
    content_id = add_item(db, scan)
    scan_babylon_item(db, scan.settings, content_id)
    before = db.get_showroom_analysis(content_id)
    embeddings = db.get_embeddings_for_content(content_id)
    monkeypatch.setattr(db, "upsert_showroom_analysis", Mock(side_effect=AssertionError("unchanged analysis rewritten")))
    monkeypatch.setattr(db, "replace_embeddings", Mock(side_effect=AssertionError("unchanged embeddings rewritten")))
    assert scan_babylon_item(db, scan.settings, content_id)["outcome"] == "unchanged"
    assert db.get_showroom_analysis(content_id) == before
    assert db.get_embeddings_for_content(content_id) == embeddings


def test_failed_resolution_is_visible_without_borrowing_analysis(db, scan):
    content_id = add_item(db, scan)
    db.upsert_babylon_catalog_item({"ci_name": "isolation-test.a.prod", "stage": "prod", "showroom_url": None,
                                   "showroom_source": ResolvedShowroom("invalid", error="missing_dependency").to_dict()})
    result = scan_babylon_item(db, scan.settings, content_id)
    assert result["error"] == "invalid_source"
    assert db.get_babylon_item(content_id)["scan_error_class"] == "invalid_source"
    assert db.get_showroom_analysis(content_id) is None
    assert scan.llm.call_count == scan.embed.call_count == 0


@pytest.mark.parametrize("status", ["none", "invalid", "ambiguous"])
def test_curator_url_resolves_target_and_is_selected_after_catalog_refresh(db, scan, status):
    name = "isolation-test.curated.prod"
    source = ResolvedShowroom(status, error=None if status == "none" else "unresolved graph").to_dict()
    cid = db.upsert_babylon_catalog_item({"ci_name": name, "stage": "prod", "category": "Workshop", "showroom_source": source})
    db.set_showroom_url_override(cid, scan.source.repo)
    assert cid in {row["content_id"] for row in db.get_items_needing_analysis(scan.settings)}
    db.upsert_babylon_catalog_item({"ci_name": name, "stage": "prod", "category": "Workshop", "showroom_source": source})
    item = db.get_babylon_item(cid)
    assert item["content_type"] == "lab"
    result = scan_babylon_item(db, scan.settings, cid)
    assert result["success"]
    assert result["signature"]["scope_key"] == "isolation-test.curated"
    assert result["source"]["owner_ci_name"] == name


def test_exception_invalidates_only_generated_target_artifacts(db, scan):
    cid = add_item(db, scan)
    other = add_item(db, scan, "isolation-test.other.prod")
    scan_babylon_item(db, scan.settings, cid)
    scan_babylon_item(db, scan.settings, other)
    with db.pool.connection() as conn:
        conn.execute("UPDATE showroom_analysis SET notes = 'Human', curated_duration_min = 37 WHERE content_id = %s", (cid,))
    other_before = db.get_embeddings_for_content(other)
    scan.llm.side_effect = RuntimeError("LLM transport failed")
    result = scan_babylon_item(db, scan.settings, cid, force=True)
    assert result["success"] is False
    assert db.get_embeddings_for_content(cid) == []
    assert db.get_content_entity(cid)["summary"] is None
    analysis = db.get_showroom_analysis(cid)
    assert analysis["summary"] is None
    assert analysis["notes"] == "Human"
    assert analysis["curated_duration_min"] == 37
    assert db.get_embeddings_for_content(other) == other_before


def test_catalog_resolution_failure_invalidates_previous_vectors_without_scan(db, scan):
    cid = add_item(db, scan)
    scan_babylon_item(db, scan.settings, cid)
    db.upsert_babylon_catalog_item({"ci_name": "isolation-test.a.prod", "stage": "prod", "showroom_url": None,
                                   "showroom_source": ResolvedShowroom("invalid", error="missing_dependency").to_dict()})
    assert db.get_embeddings_for_content(cid) == []
    assert db.get_content_entity(cid)["summary"] is None
    assert db.get_babylon_item(cid)["scan_status"] == "failed"


@pytest.mark.parametrize("old_fails", [False, True])
def test_older_scan_cannot_overwrite_newer_completed_generation(db, scan, monkeypatch, old_fails):
    from rcars.services import showroom_scan
    cid = add_item(db, scan)
    analyze = showroom_scan.analyze_showroom

    def overlapping(**kwargs):
        older_result = analyze(**kwargs)
        scan.llm.return_value.text = '{"summary":"Newer analysis","modules":[]}'
        monkeypatch.setattr(showroom_scan, "analyze_showroom", analyze)
        newer_result = scan_babylon_item(db, scan.settings, cid, force=True)
        assert newer_result["success"]
        if old_fails:
            raise RuntimeError("Older operation failed late")
        return older_result

    monkeypatch.setattr(showroom_scan, "analyze_showroom", overlapping)
    result = scan_babylon_item(db, scan.settings, cid)
    assert result["outcome"] == "superseded"
    assert result["success"] is False
    assert db.get_showroom_analysis(cid)["summary"] == "Newer analysis"
    assert db.get_babylon_item(cid)["scan_status"] == "success"
    assert db.get_embeddings_for_content(cid)


@pytest.mark.asyncio
async def test_stale_lookup_failure_cannot_fail_newer_source(db, scan, monkeypatch):
    from rcars.workers import ops
    from rcars.services.analyzer import InvalidShowroomRef
    from tests.test_workers import _worker_ctx
    cid = add_item(db, scan)
    scan_babylon_item(db, scan.settings, cid)

    def repaired_while_checking(*args):
        db.set_content_path(cid, "content/modules/ROOT/pages")
        assert scan_babylon_item(db, scan.settings, cid, force=True)["success"]
        raise InvalidShowroomRef("Old ref vanished")

    monkeypatch.setattr(ops, "ls_remote_sha", repaired_while_checking)
    ctx = _worker_ctx()
    ctx["worker_ctx"].db = db
    await ops.run_stale_check(ctx, "fixture-old-ref-check")
    assert db.get_babylon_item(cid)["scan_status"] == "success"
    assert db.get_showroom_analysis(cid)["summary"] == "Configure TLS"
    assert db.get_embeddings_for_content(cid)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["path", "prompt"])
async def test_stale_check_validates_source_and_context_before_reporting_unchanged(db, scan, monkeypatch, change):
    from rcars.workers import ops
    from tests.test_workers import _worker_ctx
    cid = add_item(db, scan)
    scan_babylon_item(db, scan.settings, cid)
    ctx = _worker_ctx()
    ctx["worker_ctx"].db = db
    ctx["worker_ctx"].settings.model = scan.settings.model
    ctx["worker_ctx"].settings.embedding_model = scan.settings.embedding_model
    if change == "path":
        db.set_content_path(cid, "content/modules/ROOT/pages")
    else:
        ctx["worker_ctx"].settings.model = "changed-analysis-model"
    result = await ops.run_stale_check(ctx, "fixture-source-context-check")
    assert result["skipped"] == 0
    assert result["stale"] == 1
    assert db.get_showroom_analysis(cid)["is_stale"] is True


@pytest.mark.asyncio
async def test_stale_lookup_failure_invalidates_unchanged_targets_old_vectors(db, scan, monkeypatch):
    from rcars.workers import ops
    from rcars.services.analyzer import InvalidShowroomRef
    from tests.test_workers import _worker_ctx
    cid = add_item(db, scan)
    scan_babylon_item(db, scan.settings, cid)
    # Invalidating lookups must not touch other items in the shared test database.
    candidates = db.get_stale_check_candidates
    monkeypatch.setattr(db, "get_stale_check_candidates", lambda: [i for i in candidates() if i["content_id"] == cid])
    monkeypatch.setattr(ops, "ls_remote_sha", Mock(side_effect=InvalidShowroomRef("Missing ref")))
    ctx = _worker_ctx()
    ctx["worker_ctx"].db = db
    await ops.run_stale_check(ctx, "fixture-failed-ref-check")
    assert db.get_embeddings_for_content(cid) == []
    assert db.get_content_entity(cid)["summary"] is None
    assert db.get_babylon_item(cid)["scan_status"] == "failed"


def test_template_only_rescan_removes_searchable_artifacts_but_keeps_curated_analysis(db, scan, git_repo):
    content_id = add_item(db, scan)
    scan_babylon_item(db, scan.settings, content_id)
    with db.pool.connection() as conn:
        conn.execute("UPDATE showroom_analysis SET notes = 'Human note', curated_duration_min = 45 WHERE content_id = %s", (content_id,))
    repo, git, _, _ = git_repo
    (repo / "content/modules/ROOT/pages/index.adoc").write_text("= Home\n* xref:other.adoc[Next]")
    git("add", ".")
    git("commit", "-m", "Navigation only")
    scan.llm.reset_mock()
    scan.embed.reset_mock()
    result = scan_babylon_item(db, scan.settings, content_id)
    assert result["error"] == "no_content"
    assert db.get_embeddings_for_content(content_id) == []
    assert db.get_content_entity(content_id)["summary"] is None
    assert db.get_showroom_analysis(content_id)["notes"] == "Human note"
    assert db.get_showroom_analysis(content_id)["curated_duration_min"] == 45
    assert scan.llm.call_count == scan.embed.call_count == 0


@pytest.mark.asyncio
async def test_legacy_queue_sibling_payload_cannot_write_other_items(db, scan):
    from rcars.workers.scan import run_analysis
    a = add_item(db, scan)
    b = add_item(db, scan, "isolation-test.b.prod")
    job_id = db.create_job(job_type="analyze", queue="analyze", created_by="isolation-test")
    ctx = {"worker_ctx": SimpleNamespace(db=db, settings=scan.settings)}
    result = await run_analysis(ctx, job_id, a, sha_siblings=[{"content_id": b}])
    assert result["success"]
    assert db.get_job(job_id)["result_json"]["outcome"] == "analyzed"
    assert db.get_showroom_analysis(b) is None
    assert db.get_embeddings_for_content(b) == []


@pytest.mark.asyncio
async def test_stale_check_never_clears_unrelated_stale_item(db, scan):
    from rcars.workers import ops
    from tests.test_workers import _worker_ctx
    a = add_item(db, scan)
    b = add_item(db, scan, "isolation-test.b.prod")
    scan_babylon_item(db, scan.settings, a)
    scan_babylon_item(db, scan.settings, b)
    db.mark_stale(b)
    ctx = _worker_ctx()
    ctx["worker_ctx"].db = db
    ctx["worker_ctx"].settings.model = scan.settings.model
    ctx["worker_ctx"].settings.embedding_model = scan.settings.embedding_model
    result = await ops.run_stale_check(ctx, "fixture-stale-check")
    assert result["skipped"] == 1
    assert result["stale"] == 1
    assert db.get_showroom_analysis(b)["is_stale"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("forced", [False, True])
async def test_scan_endpoints_submit_each_stage_without_llm_or_fanout(db, scan, forced):
    from rcars.api.routes.analysis import start_scan, rescan_all
    ids = [add_item(db, scan, name) for name in ("isolation-test.a.prod", "isolation-test.a.dev", "isolation-test.virtual.prod")]
    redis = SimpleNamespace(enqueue_job=AsyncMock())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db, arq_redis=redis, settings=scan.settings)))
    result = await (rescan_all if forced else start_scan)(request, user="test@example.com")
    jobs = redis.enqueue_job.call_args_list
    assert {call.kwargs["content_id"] for call in jobs} == set(ids)
    assert all(call.kwargs.get("force", False) == forced for call in jobs)
    assert all("sha_siblings" not in call.kwargs for call in jobs)
    assert result["enqueued"] == 3
    assert scan.llm.call_count == scan.embed.call_count == 0
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM jobs WHERE created_by IN ('test@example.com', 'rescan-all')")


def test_cli_scans_independent_stages_and_reuses_shared_content(db, scan, monkeypatch):
    from rcars import cli as cli_module
    ids = [add_item(db, scan, name) for name in ("isolation-test.a.prod", "isolation-test.virtual.dev")]
    scan.settings.max_parallel = 1
    scan.settings.use_litemaas = False
    monkeypatch.setattr(cli_module, "Settings", lambda: scan.settings)
    monkeypatch.setattr(cli_module, "get_db", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    result = CliRunner().invoke(cli_module.cli, ["scan"])
    assert result.exit_code == 0, result.output
    assert all(db.get_babylon_item(cid)["scan_status"] == "success" for cid in ids)
    # Same files and content type, so the second stage reuses the first analysis.
    assert scan.llm.call_count == 1


@pytest.mark.asyncio
async def test_unchanged_maintenance_enqueues_no_analysis_jobs(db, scan, monkeypatch):
    from rcars.workers import ops
    from tests.test_workers import _worker_ctx
    content_id = add_item(db, scan)
    scan_babylon_item(db, scan.settings, content_id)
    scan.llm.reset_mock()
    scan.embed.reset_mock()
    ctx = _worker_ctx(workload_scan_enabled=False)
    ctx["worker_ctx"].db = db
    ctx["worker_ctx"].settings.model = scan.settings.model
    ctx["worker_ctx"].settings.embedding_model = scan.settings.embedding_model
    monkeypatch.setattr(ops, "publish_progress", AsyncMock())
    monkeypatch.setattr(ops, "run_catalog_refresh", AsyncMock(return_value={"total_items": 1}))
    monkeypatch.setattr(ops, "run_sandbox_summary", AsyncMock(return_value={"total": 0}))
    monkeypatch.setattr(ops, "prune_stale_candidates", lambda *a: 0)
    monkeypatch.setattr(ops, "generate_overlap_candidates", lambda *a, **k: {"total_candidates": 0})
    monkeypatch.setattr(ops, "batch_assess_overlaps", lambda *a, **k: {"assessed": 0})
    from structlog.testing import capture_logs
    with capture_logs() as logs:
        result = await ops.run_babylon_pipeline(ctx, "fixture-parent", own_lifecycle=False)
    assert result["analysis_enqueued"] == 0
    assert result["warnings"] == []
    assert ctx["redis"].enqueue_job.call_count == 0
    assert scan.llm.call_count == scan.embed.call_count == 0
    summary = [row for row in logs if row["event"] == "scan_reuse_summary"]
    assert len(summary) == 1
    assert {"analyses", "llm_runs", "reused", "distinct_content", "extra_llm_runs"} <= summary[0].keys()


@pytest.mark.asyncio
async def test_transient_stale_lookup_failure_keeps_artifacts(db, scan, monkeypatch):
    import subprocess
    from rcars.workers import ops
    from tests.test_workers import _worker_ctx
    cid = add_item(db, scan)
    scan_babylon_item(db, scan.settings, cid)
    monkeypatch.setattr(ops, "ls_remote_sha", Mock(side_effect=subprocess.CalledProcessError(
        128, ["git", "ls-remote"], stderr="fatal: unable to access: Could not resolve host")))
    ctx = _worker_ctx()
    ctx["worker_ctx"].db = db
    result = await ops.run_stale_check(ctx, "fixture-transient-ref-check")
    assert result["failed"] >= 1
    assert db.get_embeddings_for_content(cid)
    assert db.get_content_entity(cid)["summary"]
    assert db.get_babylon_item(cid)["scan_status"] == "success"


@pytest.mark.asyncio
async def test_missing_repo_stale_lookup_invalidates_artifacts(db, scan, monkeypatch):
    import subprocess
    from rcars.workers import ops
    from tests.test_workers import _worker_ctx
    cid = add_item(db, scan)
    scan_babylon_item(db, scan.settings, cid)
    # Invalidating lookups must not touch other items in the shared test database.
    candidates = db.get_stale_check_candidates
    monkeypatch.setattr(db, "get_stale_check_candidates", lambda: [i for i in candidates() if i["content_id"] == cid])
    monkeypatch.setattr(ops, "ls_remote_sha", Mock(side_effect=subprocess.CalledProcessError(
        128, ["git", "ls-remote"], stderr="remote: Repository not found.")))
    ctx = _worker_ctx()
    ctx["worker_ctx"].db = db
    await ops.run_stale_check(ctx, "fixture-missing-repo-check")
    assert db.get_embeddings_for_content(cid) == []
    assert db.get_babylon_item(cid)["scan_status"] == "failed"
    assert db.get_babylon_item(cid)["scan_error_class"] == "http_404"


def commit_of(db, cid):
    from rcars.services.analyzer import ls_remote_sha
    source = db.get_babylon_item(cid)["showroom_source_json"]
    return ls_remote_sha(source["repo"], source["ref"])


def test_reuse_key_ignores_ref_name_ci_and_display_name(db, scan, git_repo):
    from rcars.services.analysis_identity import pre_clone_key
    from rcars.services.analyzer import showroom_reuse_key
    git_repo[1]("tag", "v1")  # another ref name on the same commit as main
    prod, dev = add_item(db, scan, "isolation-test.a.prod"), add_item(db, scan, "isolation-test.a.dev", ref="v1")
    renamed = add_item(db, scan, "isolation-test.a.event", display_name="TLS workshop (event)")
    other = add_item(db, scan, "isolation-test.b.prod")
    key = lambda cid: showroom_reuse_key(db.get_babylon_item(cid), scan.settings, commit_of(db, cid))
    assert key(prod) == key(dev) == key(renamed) == key(other)
    scan_babylon_item(db, scan.settings, prod)
    signature = db.get_showroom_analysis(prod)["analysis_provenance_json"]["signature"]
    # Guards against the pre-clone key drifting from analyze_showroom's signature inputs.
    assert pre_clone_key(signature["repo"], signature["commit"], signature["content_path"],
                         signature["context_hash"], "lab") == key(prod)


def test_reuse_key_is_shared_across_cis(db, scan):
    from rcars.services.analyzer import showroom_reuse_key
    one, two = add_item(db, scan, "isolation-test.a.prod"), add_item(db, scan, "isolation-test.b.dev",
                                                                     display_name="Another name")
    key = lambda cid: showroom_reuse_key(db.get_babylon_item(cid), scan.settings, commit_of(db, cid))
    assert key(one) == key(two)


def test_reuse_key_differs_by_commit_and_content_path(db, scan):
    from rcars.services.analyzer import showroom_reuse_key
    cid = add_item(db, scan)
    item = db.get_babylon_item(cid)
    base = showroom_reuse_key(item, scan.settings, "a" * 40)
    assert showroom_reuse_key(item, scan.settings, "b" * 40) != base
    db.set_content_path(cid, "other/pages")
    assert showroom_reuse_key(db.get_babylon_item(cid), scan.settings, "a" * 40) != base


def test_reuse_key_is_none_for_unresolved_source_or_unresolved_commit(db, scan):
    from rcars.services.analyzer import showroom_reuse_key
    cid = add_item(db, scan, "isolation-test.broken.prod", showroom_source=ResolvedShowroom("invalid", error="x").to_dict())
    assert showroom_reuse_key(db.get_babylon_item(cid), scan.settings, "a" * 40) is None
    good = add_item(db, scan, "isolation-test.good.prod")
    assert showroom_reuse_key(db.get_babylon_item(good), scan.settings, None) is None


def test_resolve_commits_makes_one_ls_remote_per_repo_and_skips_bad_refs(db, scan, git_repo, monkeypatch):
    from rcars.services import analyzer
    git_repo[1]("tag", "v1")
    items = [db.get_babylon_item(add_item(db, scan, name, ref=ref)) for name, ref in
             (("isolation-test.a.prod", "main"), ("isolation-test.a.dev", "v1"), ("isolation-test.a.event", "missing"))]
    calls = Mock(wraps=analyzer.ls_remote_refs)
    monkeypatch.setattr(analyzer, "ls_remote_refs", calls)
    commits = analyzer.resolve_commits(items)
    assert calls.call_count == 1
    url = scan.source.repo
    assert commits[(url, "main")] == commits[(url, "v1")] == git_repo[3]
    assert (url, "missing") not in commits


def test_resolve_commits_leaves_a_failing_repo_out(db, scan, monkeypatch):
    from rcars.services import analyzer
    items = [db.get_babylon_item(add_item(db, scan))]
    monkeypatch.setattr(analyzer, "ls_remote_refs", Mock(side_effect=RuntimeError("network down")))
    assert analyzer.resolve_commits(items) == {}


def test_order_for_reuse_puts_one_prod_preferred_leader_per_group_first(db, scan):
    from rcars.services.analyzer import order_for_reuse
    names = ["isolation-test.a.dev", "isolation-test.a.event", "isolation-test.a.prod",
             "isolation-test.b.dev", "isolation-test.c.event", "isolation-test.c.dev"]
    items = [db.get_babylon_item(add_item(db, scan, name)) for name in names]
    ordered = [item["ci_name"] for item in order_for_reuse(items, scan.settings)]
    # All share repo, commit, path and analysis_config, so only one leader runs the LLM.
    assert ordered == ["isolation-test.a.prod", "isolation-test.a.event", "isolation-test.c.event",
                       "isolation-test.a.dev", "isolation-test.b.dev", "isolation-test.c.dev"]


def test_order_for_reuse_groups_stages_with_other_ref_names_and_other_cis(db, scan, git_repo):
    from rcars.services.analyzer import order_for_reuse
    git_repo[1]("tag", "v1")
    specs = [("isolation-test.a.dev", "v1"), ("isolation-test.b.prod", "main"), ("isolation-test.a.prod", "main"),
             ("isolation-test.c.dev", "light")]  # `light` is the earlier commit: its own group
    items = [db.get_babylon_item(add_item(db, scan, name, ref=ref)) for name, ref in specs]
    ordered = [item["ci_name"] for item in order_for_reuse(items, scan.settings)]
    assert ordered == ["isolation-test.a.prod", "isolation-test.c.dev", "isolation-test.b.prod",
                       "isolation-test.a.dev"]


@pytest.mark.parametrize("second,second_ref", [
    ("isolation-test.a.dev", None),         # stage sibling, same ref
    ("isolation-test.a.dev", "v1"),         # stage sibling, another ref name on the same commit
    ("isolation-test.b.prod", None),        # another CI on the same files
])
def test_concurrent_sibling_scans_make_one_llm_call(db, scan, git_repo, monkeypatch, second, second_ref):
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor
    git_repo[1]("tag", "v1")
    prod, dev = add_item(db, scan, "isolation-test.a.prod"), add_item(db, scan, second, ref=second_ref)
    reply, both_started = scan.llm.return_value, threading.Barrier(2, timeout=10)
    from rcars.services import showroom_scan
    analyze = showroom_scan.analyze_showroom

    def slow_llm(*args, **kwargs):
        time.sleep(1)
        return reply

    def started_together(**kwargs):
        try:
            both_started.wait(timeout=2)  # without serialization both reach this point together
        except threading.BrokenBarrierError:
            pass
        return analyze(**kwargs)

    scan.llm.side_effect = slow_llm
    showroom_scan.analyze_showroom = started_together
    try:
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda cid: scan_babylon_item(db, scan.settings, cid), (prod, dev)))
    finally:
        showroom_scan.analyze_showroom = analyze
    assert sorted(r["outcome"] for r in results) == ["analyzed", "reused"]
    assert scan.llm.call_count == 1


def test_scan_lock_is_taken_on_the_pre_clone_key_not_the_ref_name(db, scan, git_repo, monkeypatch):
    from rcars.services import showroom_scan
    git_repo[1]("tag", "v1")
    prod, dev = add_item(db, scan, "isolation-test.a.prod"), add_item(db, scan, "isolation-test.a.dev", ref="v1")
    keys = [showroom_scan.item_reuse_key(db.get_babylon_item(cid), scan.settings) for cid in (prod, dev)]
    assert keys[0] is not None and keys[0] == keys[1]
    assert showroom_scan.reuse_lock_id(keys[0]) == showroom_scan.reuse_lock_id(keys[1])


def test_item_without_a_resolvable_commit_takes_no_lock_and_still_scans(db, scan, monkeypatch):
    from rcars.services import showroom_scan
    cid = add_item(db, scan)
    monkeypatch.setattr(showroom_scan, "ls_remote_sha", Mock(side_effect=RuntimeError("network down")))
    assert showroom_scan.item_reuse_key(db.get_babylon_item(cid), scan.settings) is None


def test_pure_stub_and_description_items_take_no_lock(db, scan):
    from rcars.services import showroom_scan
    owner = add_item(db, scan, "isolation-test.owner.prod")
    source = replace(scan.source, owner_ci_name="isolation-test.owner.prod", scope_key="isolation-test.owner",
                     paths=(("isolation-test.virtual.prod", "isolation-test.owner.prod"),))
    stub = db.upsert_babylon_catalog_item({"ci_name": "isolation-test.virtual.prod", "stage": "prod",
        "showroom_url": source.repo, "showroom_ref": source.ref, "showroom_source": source.to_dict()})
    assert showroom_scan.item_reuse_key(db.get_babylon_item(stub), scan.settings) is None
    assert showroom_scan.item_reuse_key(db.get_babylon_item(owner), scan.settings) is not None
    described = add_item(db, scan, "isolation-test.described.prod")
    db.set_analysis_source(described, "custom_description", "A curator-written description")
    assert showroom_scan.item_reuse_key(db.get_babylon_item(described), scan.settings) is None


def test_reuse_lock_wait_times_out_and_reports_not_acquired(db):
    import psycopg
    with psycopg.connect(db._url, autocommit=True) as holder:
        holder.execute("SELECT pg_advisory_lock(%s)", (4242,))
        with db.wait_advisory_lock(4242, wait_seconds=1) as acquired:
            assert acquired is False
    with db.wait_advisory_lock(4242, wait_seconds=1) as acquired:
        assert acquired is True


@pytest.mark.asyncio
async def test_scan_endpoint_enqueues_the_single_group_leader_first(db, scan):
    from rcars.api.routes.analysis import start_scan
    ids = [add_item(db, scan, name) for name in ("isolation-test.a.dev", "isolation-test.a.prod", "isolation-test.b.dev")]
    redis = SimpleNamespace(enqueue_job=AsyncMock())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db, arq_redis=redis, settings=scan.settings)))
    await start_scan(request, user="test@example.com")
    order = [call.kwargs["content_id"] for call in redis.enqueue_job.call_args_list if call.kwargs["content_id"] in ids]
    # All three share one pre-clone key, so only the prod leader runs the LLM first.
    assert order == [ids[1], ids[0], ids[2]]
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM jobs WHERE created_by = 'test@example.com'")
