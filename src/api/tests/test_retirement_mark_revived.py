"""Backfill CLI for retirement history (RHDPCD-2331).

`rcars retirement mark-revived` closes the current retired workflow of a family
as revived, for items that came back before revive tracking existed. It is a
dry run unless --apply is given, and it only touches families the operator
names explicitly.
"""

import os
from urllib.parse import urlparse

import pytest
from click.testing import CliRunner

from rcars import cli as cli_module
from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)

A_BASE = "test-mark-revived.a"
B_BASE = "test-mark-revived.b"
A_PROD = f"babylon:{A_BASE}.prod"
A_DEV = f"babylon:{A_BASE}.dev"
A_EVENT = f"babylon:{A_BASE}.event"
B_PROD = f"babylon:{B_BASE}.prod"
CONTENT_IDS = (A_PROD, A_DEV, A_EVENT, B_PROD)


@pytest.fixture
def db(monkeypatch):
    if "test" not in urlparse(TEST_DB_URL).path:
        raise RuntimeError("Retirement backfill tests require a test database")
    database = Database(TEST_DB_URL)
    database.create_schema()
    _clean(database)
    for content_id in CONTENT_IDS:
        stage = content_id.rsplit(".", 1)[1]
        database.upsert_babylon_catalog_item(
            {"ci_name": content_id.removeprefix("babylon:"), "stage": stage})
    monkeypatch.setattr(cli_module, "get_db", lambda: Database(TEST_DB_URL))
    yield database
    _clean(database)
    database.close()


def _clean(db):
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM analysis_log WHERE ci_name IN (%s, %s)", (A_BASE, B_BASE))
        conn.execute("DELETE FROM content_entities WHERE content_id = ANY(%s)", (list(CONTENT_IDS),))
        conn.commit()


def _other_babylon_ids(db):
    """Every Babylon content_id except this test's, so the sweep stays local."""
    with db.pool.connection() as conn:
        rows = conn.execute(
            "SELECT content_id FROM content_entities "
            "WHERE source = 'babylon' AND content_id != ALL(%s)",
            (list(CONTENT_IDS),),
        ).fetchall()
    return {row["content_id"] for row in rows} or {"babylon:mark-revived.placeholder.prod"}


def _retire_everything(db):
    db.retire_missing_babylon(_other_babylon_ids(db))


def _item_returns(db, content_id):
    """The CatalogItem is back, but nothing recorded the revive."""
    with db.pool.connection() as conn:
        conn.execute(
            "UPDATE content_entities SET retired_at = NULL, retirement_reason = NULL "
            "WHERE content_id = %s", (content_id,))
        conn.commit()


def _workflows(db, content_id):
    with db.pool.connection() as conn:
        return conn.execute(
            "SELECT id, status, step_retired_at, revived_at, revived_reason, agv_retire_pr_url "
            "FROM retirement_workflow WHERE content_id = %s ORDER BY id", (content_id,)
        ).fetchall()


def _run(*args):
    return CliRunner().invoke(cli_module.cli, ["retirement", "mark-revived", *args])


def test_dry_run_reports_the_change_and_writes_nothing(db):
    db.upsert_retirement_workflow(A_PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    _retire_everything(db)
    _item_returns(db, A_DEV)

    result = _run("--content-id", A_DEV)

    assert result.exit_code == 0, result.output
    assert "DRY RUN" in result.output
    assert "would mark" in result.output
    assert A_PROD in result.output
    row = _workflows(db, A_PROD)[0]
    assert row["revived_at"] is None
    assert row["revived_reason"] is None


def test_apply_marks_the_family_once(db):
    db.upsert_retirement_workflow(A_PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    _retire_everything(db)
    _item_returns(db, A_DEV)

    result = _run("--content-id", A_DEV, "--apply")

    assert result.exit_code == 0, result.output
    rows = _workflows(db, A_PROD)
    assert len(rows) == 1
    assert rows[0]["revived_at"] is not None
    assert rows[0]["revived_reason"] == "Backfill: item returned before history tracking"
    assert rows[0]["status"] == "retired"
    assert db.get_retirement_workflow(A_PROD) is None
    with db.pool.connection() as conn:
        logged = conn.execute(
            "SELECT action FROM analysis_log WHERE ci_name = %s", (A_BASE,)
        ).fetchall()
    assert [row["action"] for row in logged] == ["retirement_revived"]


def test_apply_leaves_other_families_alone(db):
    db.upsert_retirement_workflow(A_PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    _retire_everything(db)
    _item_returns(db, A_DEV)
    _item_returns(db, B_PROD)

    result = _run("--content-id", A_DEV, "--apply")

    assert result.exit_code == 0, result.output
    assert _workflows(db, A_PROD)[0]["revived_at"] is not None
    assert _workflows(db, B_PROD) == []


def test_path_b_workflow_is_refused_unless_forced(db):
    """Removal PR merged while the CatalogItem stayed: not a revive."""
    db.upsert_retirement_workflow(B_PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    db.record_retirement_pr(B_PROD, "agv_retire_pr_url", {
        "pr_url": "https://github.com/rhpds/agnosticv/pull/77"})
    db.auto_close_retired_workflows({B_PROD})

    refused = _run("--content-id", B_PROD, "--apply")
    assert refused.exit_code == 1
    assert "removal PR" in refused.output and "--force" in refused.output
    assert _workflows(db, B_PROD)[0]["revived_at"] is None

    forced = _run("--content-id", B_PROD, "--apply", "--force")
    assert forced.exit_code == 0, forced.output
    assert _workflows(db, B_PROD)[0]["revived_at"] is not None


def test_non_retired_workflow_is_not_marked(db):
    db.upsert_retirement_workflow(A_PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    _retire_everything(db)
    _item_returns(db, A_DEV)
    with db.pool.connection() as conn:  # back to an active retirement
        conn.execute(
            "UPDATE retirement_workflow SET status = 'started', step_retired_at = NULL "
            "WHERE content_id = %s", (A_PROD,))
        conn.commit()

    result = _run("--content-id", A_DEV, "--apply")

    assert result.exit_code == 1
    assert "no current retired workflow" in result.output
    assert _workflows(db, A_PROD)[0]["revived_at"] is None


def test_still_retired_item_is_refused(db):
    db.upsert_retirement_workflow(A_PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    _retire_everything(db)

    result = _run("--content-id", A_DEV, "--apply")

    assert result.exit_code == 1
    assert "still retired" in result.output
    assert _workflows(db, A_PROD)[0]["revived_at"] is None


def test_unknown_content_id_is_refused(db):
    result = _run("--content-id", "babylon:nope.prod", "--apply")

    assert result.exit_code == 1
    assert "no content entity" in result.output


def test_second_apply_is_a_no_op(db):
    db.upsert_retirement_workflow(A_PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    _retire_everything(db)
    _item_returns(db, A_DEV)
    assert _run("--content-id", A_DEV, "--apply").exit_code == 0
    first = _workflows(db, A_PROD)[0]

    second = _run("--content-id", A_DEV, "--apply")

    assert second.exit_code == 0, second.output
    assert "already marked revived" in second.output
    assert _workflows(db, A_PROD) == [first]


def test_reason_option_is_recorded(db):
    db.upsert_retirement_workflow(A_PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    _retire_everything(db)
    _item_returns(db, A_DEV)

    result = _run("--content-id", A_DEV, "--apply", "--reason", "Backfill: after RHDPCD-2256")

    assert result.exit_code == 0, result.output
    assert _workflows(db, A_PROD)[0]["revived_reason"] == "Backfill: after RHDPCD-2256"


def _two_current_workflows(db):
    with db.pool.connection() as conn:
        conn.execute(
            "INSERT INTO retirement_workflow (content_id, status, step_retired_at) "
            "VALUES (%s, 'retired', NOW())", (A_PROD,))
        conn.execute(
            "INSERT INTO retirement_workflow (content_id, status, step_retired_at) "
            "VALUES (%s, 'retired', NOW() - INTERVAL '1 day')", (A_DEV,))
        conn.commit()


def test_repeat_apply_revives_the_named_workflow_and_then_stops(db):
    """Two stage rows share a family: the named one is the stable target."""
    _two_current_workflows(db)

    first = _run("--content-id", A_DEV, "--apply")

    assert first.exit_code == 0, first.output
    assert first.output.count("marked babylon:") == 1
    assert _workflows(db, A_DEV)[0]["revived_at"] is not None
    assert _workflows(db, A_PROD)[0]["revived_at"] is None

    second = _run("--content-id", A_DEV, "--apply")

    assert second.exit_code == 0, second.output
    assert "already marked revived" in second.output
    assert _workflows(db, A_PROD)[0]["revived_at"] is None


def test_ambiguous_family_is_refused(db):
    """No workflow on the named content_id and two siblings: never guess."""
    _two_current_workflows(db)

    result = _run("--content-id", A_EVENT, "--apply")

    assert result.exit_code == 1
    assert "2 current retired workflows" in result.output
    assert A_DEV in result.output and A_PROD in result.output
    assert _workflows(db, A_DEV)[0]["revived_at"] is None
    assert _workflows(db, A_PROD)[0]["revived_at"] is None


def test_failed_audit_insert_leaves_the_workflow_current(db, monkeypatch):
    db.upsert_retirement_workflow(A_PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    _retire_everything(db)
    _item_returns(db, A_DEV)

    def boom(*args, **kwargs):
        raise RuntimeError("audit insert failed")

    monkeypatch.setattr(Database, "log_action", boom)
    result = _run("--content-id", A_DEV, "--apply")

    assert result.exit_code != 0
    assert _workflows(db, A_PROD)[0]["revived_at"] is None
