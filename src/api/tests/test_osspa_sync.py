import os
from pathlib import Path

import pytest

from rcars.config import Settings
from rcars.db.database import Database
from rcars.services import osspa_sync
from rcars.services.osspa_sync import run_osspa_sync

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)

CSV_HEADER = (
    "ppid,PAName,Heading,islive,showInCatalog,Summary,metaDesc,metaKeyword,"
    "Vertical,Solutions,Product,ProductType,Image1Url,DetailPage,externalUrl\n"
)


def _csv(*ppids, product_type="PA", islive="TRUE", catalog="TRUE"):
    rows = "".join(
        f"{p},{p}-item,Item {p},{islive},{catalog},Summary {p},d,k,"
        f"All,Security,OpenShift,{product_type},i.png,item{p}.adoc,\n"
        for p in ppids
    )
    return CSV_HEADER + rows


@pytest.fixture
def db():
    import psycopg
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


@pytest.fixture
def settings():
    return Settings(database_url=TEST_DB_URL)


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """A clone stand-in whose adoc files always read successfully."""
    root = tmp_path / "clone"
    root.mkdir()
    monkeypatch.setattr(osspa_sync, "clone_examples_repo", lambda s: root)
    monkeypatch.setattr(osspa_sync, "get_head_sha", lambda p: "headsha")
    monkeypatch.setattr(osspa_sync, "file_commit_sha", lambda p, r: "filesha")
    monkeypatch.setattr(
        osspa_sync, "read_detail_adoc",
        lambda root, detail, max_bytes: osspa_sync.AdocRead(f"body of {detail}", f"body of {detail}", False))
    return root


@pytest.fixture
def fake_analyze(monkeypatch):
    calls = []

    def _analyze(db, content_id, payload, adoc_text, content_hash, settings,
                 stale_commit=None, truncated=False):
        calls.append(content_id)
        db.upsert_architecture_analysis({"content_id": content_id, "content_hash": content_hash})
        db.replace_embeddings(content_id, [{
            "content_id": content_id, "content_type": "architecture",
            "source": "portfolio_arch", "embed_type": "summary",
            "content_text": "Portfolio architecture: x", "embedding": [0.01] * 768}])
        db.clear_architecture_stale(content_id)
        return {"status": "analyzed", "content_id": content_id}

    monkeypatch.setattr(osspa_sync, "analyze_architecture_item", _analyze)
    return calls


def _stub_csv(monkeypatch, text):
    monkeypatch.setattr(osspa_sync, "fetch_palist_csv",
                        lambda s: osspa_sync.parse_palist_csv(text))


def test_sync_upserts_and_analyzes(db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1, 2))

    result = run_osspa_sync(db, settings)

    assert result["status"] == "complete"
    assert result["upserted"] == 2
    assert result["analyzed"] == 2
    assert sorted(fake_analyze) == ["pa:1", "pa:2"]
    assert db.get_content_entity("pa:1")["status"] == "prod"


def test_sync_skips_items_whose_hash_has_not_moved(db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))
    run_osspa_sync(db, settings)
    fake_analyze.clear()

    result = run_osspa_sync(db, settings)

    assert fake_analyze == []
    assert result["analyzed"] == 0
    assert result["skipped"] == 1


def test_force_reanalyzes_unchanged_items(db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))
    run_osspa_sync(db, settings)
    fake_analyze.clear()

    run_osspa_sync(db, settings, force=True)

    assert fake_analyze == ["pa:1"]


def test_stale_item_is_reanalyzed_even_when_the_hash_matches(
        db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))
    run_osspa_sync(db, settings)
    fake_analyze.clear()
    db.mark_architecture_stale("pa:1")

    run_osspa_sync(db, settings)

    assert fake_analyze == ["pa:1"]


def test_missing_embedding_forces_reanalysis(db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))
    run_osspa_sync(db, settings)
    fake_analyze.clear()
    db.clear_embeddings("pa:1")

    run_osspa_sync(db, settings)

    assert fake_analyze == ["pa:1"]


def test_empty_active_set_aborts_without_retiring(db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))
    run_osspa_sync(db, settings)
    _stub_csv(monkeypatch, CSV_HEADER)

    result = run_osspa_sync(db, settings)

    assert result["status"] == "aborted_empty_inventory"
    assert result["retired"] == 0
    assert db.get_content_entity("pa:1")["retired_at"] is None


def test_empty_active_set_with_confirmation_retires_everything(
        db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))
    run_osspa_sync(db, settings)
    _stub_csv(monkeypatch, CSV_HEADER)

    result = run_osspa_sync(db, settings, confirm_empty_inventory=True)

    assert result["status"] == "complete"
    assert result["retired"] == 1
    assert db.get_content_entity("pa:1")["retired_at"] is not None


def test_shrink_guard_skips_retirement_but_still_upserts(
        db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1, 2, 3, 4))
    run_osspa_sync(db, settings)
    _stub_csv(monkeypatch, _csv(1))

    result = run_osspa_sync(db, settings)

    assert result["retired"] == 0
    assert result["retire_skipped_reason"] == "shrink_guard"
    assert db.get_content_entity("pa:4")["retired_at"] is None
    assert result["upserted"] == 1


def test_retirement_runs_when_the_drop_is_within_the_guard(
        db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1, 2, 3, 4))
    run_osspa_sync(db, settings)
    _stub_csv(monkeypatch, _csv(1, 2, 3))

    result = run_osspa_sync(db, settings)

    assert result["retired"] == 1
    assert db.get_content_entity("pa:4")["retired_at"] is not None


def test_clone_failure_aborts_before_any_db_write(db, settings, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))

    def _boom(s):
        raise osspa_sync.OsspaSyncError("clone timed out")

    monkeypatch.setattr(osspa_sync, "clone_examples_repo", _boom)

    with pytest.raises(osspa_sync.OsspaSyncError):
        run_osspa_sync(db, settings)

    assert db.count_active_osspa() == 0
    assert db.get_content_entity("pa:1") is None


def test_missing_detail_page_marks_stale_and_skips(db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))
    monkeypatch.setattr(osspa_sync, "read_detail_adoc", lambda root, detail, max_bytes: None)

    result = run_osspa_sync(db, settings)

    assert result["failed"] == 1
    assert fake_analyze == []
    assert db.get_architecture_analysis("pa:1")["is_stale"] is True


def test_second_concurrent_sync_exits_early(db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))
    other = Database(TEST_DB_URL)
    try:
        with other.advisory_lock(settings.osspa_advisory_lock_id) as held:
            assert held is True
            result = run_osspa_sync(db, settings)
        assert result["status"] == "locked"
        assert result["upserted"] == 0
    finally:
        other.close()


def test_progress_callback_receives_each_phase(db, settings, fake_repo, fake_analyze, monkeypatch):
    _stub_csv(monkeypatch, _csv(1))
    phases = []
    run_osspa_sync(db, settings, on_progress=lambda phase, msg: phases.append(phase))
    assert phases[:2] == ["pipeline:osspa:csv_fetch", "pipeline:osspa:clone"]
    assert "pipeline:osspa:analyze" in phases
