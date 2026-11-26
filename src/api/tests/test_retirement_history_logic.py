"""Retirement history logic for RHDPCD-2331: only the current row is visible.

A content_id can now hold one current workflow (revived_at IS NULL) plus any
number of revived history rows. Every reader and writer must use the current
row only: a history row must not show a badge, hide an item, duplicate a list
row, or be swept again.
"""

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import pytest

from rcars.db.database import Database
from rcars.services.retirement_jira_events import build_jira_event

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)

BASE = "test-history-logic.item"
PROD = f"babylon:{BASE}.prod"
DEV = f"babylon:{BASE}.dev"
CONTENT_IDS = (PROD, DEV)


@pytest.fixture
def db():
    if "test" not in urlparse(TEST_DB_URL).path:
        raise RuntimeError("Retirement history tests require a test database")
    database = Database(TEST_DB_URL)
    database.create_schema()
    _clean(database)
    yield database
    _clean(database)
    database.close()


def _clean(db):
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM retirement_jira_events WHERE content_id = ANY(%s)",
                     (list(CONTENT_IDS),))
        conn.execute("DELETE FROM analysis_log WHERE ci_name LIKE %s", (f"%{BASE}%",))
        conn.execute("DELETE FROM content_entities WHERE content_id = ANY(%s)",
                     (list(CONTENT_IDS),))
        conn.commit()


def _seed_item(db, stage="prod"):
    db.upsert_babylon_catalog_item({"ci_name": f"{BASE}.{stage}", "stage": stage})
    with db.pool.connection() as conn:
        conn.execute(
            "INSERT INTO nonprod_usage (content_id, catalog_base_name, provisions) VALUES (%s, %s, 3) "
            "ON CONFLICT (content_id) DO UPDATE SET provisions = 3",
            (f"babylon:{BASE}.{stage}", BASE),
        )
        conn.execute(
            "INSERT INTO performance_scores (content_id, performance_score) VALUES (%s, 10) "
            "ON CONFLICT (content_id) DO UPDATE SET performance_score = 10",
            (f"babylon:{BASE}.{stage}",),
        )
        conn.commit()


def _seed_family(db):
    for stage in ("prod", "dev"):
        _seed_item(db, stage)


def _insert_history_row(db, content_id, *, jira_key="RHDPCD-9002"):
    """Insert a revived (history) workflow row directly, as the next deploy's
    revive path would. updated_at is far in the future so that a reader that
    forgets revived_at IS NULL would visibly pick it over the current row."""
    with db.pool.connection() as conn:
        row = conn.execute(
            "INSERT INTO retirement_workflow "
            "(content_id, status, step_approved_at, step_retired_at, jira_key, created_at, updated_at, "
            " revived_at, revived_reason) "
            "VALUES (%s, 'retired', NOW() - INTERVAL '30 days', NOW() - INTERVAL '20 days', %s, "
            "        NOW() - INTERVAL '60 days', NOW() + INTERVAL '1 day', "
            "        NOW() - INTERVAL '10 days', 'CatalogItem returned (catalog refresh)') "
            "RETURNING *",
            (content_id, jira_key),
        ).fetchone()
        conn.commit()
        return row


def _other_babylon_ids(db):
    """Every Babylon content_id except this test's, so the sweep stays local."""
    with db.pool.connection() as conn:
        rows = conn.execute(
            "SELECT content_id FROM content_entities "
            "WHERE source = 'babylon' AND content_id != ALL(%s)",
            (list(CONTENT_IDS),),
        ).fetchall()
    # retire_missing_babylon refuses an empty scan on purpose.
    return {row["content_id"] for row in rows} or {"babylon:history-logic.placeholder.prod"}


def _workflow_rows(db, content_id):
    with db.pool.connection() as conn:
        return conn.execute(
            "SELECT id, status, step_retired_at, revived_at, revived_reason FROM retirement_workflow "
            "WHERE content_id = %s ORDER BY id",
            (content_id,),
        ).fetchall()


def _current_id(db, content_id):
    with db.pool.connection() as conn:
        return conn.execute(
            "SELECT id FROM retirement_workflow WHERE content_id = %s AND revived_at IS NULL",
            (content_id,),
        ).fetchone()["id"]


def test_path_b_retired_workflow_with_active_item_stays_hidden(db):
    """Removal PR merged but the CatalogItem still exists: not a revive."""
    _seed_item(db)
    db.upsert_retirement_workflow(PROD, {"step_approved_at": "NOW()", "step_retired_at": "NOW()"})

    assert db.list_nonprod_items() == []
    assert db.get_retirement_workflow(PROD)["status"] == "retired"


def test_new_retirement_after_revive_adds_a_second_row(db):
    _seed_item(db)
    history = _insert_history_row(db, PROD)

    first = db.upsert_retirement_workflow(PROD, {"status": "reviewed"})
    second = db.upsert_retirement_workflow(PROD, {"status": "approved", "step_approved_at": "NOW()"})

    rows = _workflow_rows(db, PROD)
    assert len(rows) == 2
    assert [row["revived_at"] is None for row in rows] == [False, True]
    assert first["id"] == second["id"] == _current_id(db, PROD)
    assert rows[0]["id"] == history["id"]
    assert db.get_retirement_workflow(PROD)["status"] == "approved"


def test_cancelling_the_new_workflow_keeps_history(db):
    _seed_item(db)
    history = _insert_history_row(db, PROD)
    db.upsert_retirement_workflow(PROD, {"step_approved_at": "NOW()"})

    assert db.finalize_retirement_cancellation(PROD) is True

    rows = _workflow_rows(db, PROD)
    assert [row["id"] for row in rows] == [history["id"]]
    assert rows[0]["revived_at"] is not None


def test_delete_workflow_keeps_history(db):
    _seed_item(db)
    history = _insert_history_row(db, PROD)
    db.upsert_retirement_workflow(PROD, {"status": "reviewed"})

    assert db.delete_retirement_workflow(PROD) is True
    assert [row["id"] for row in _workflow_rows(db, PROD)] == [history["id"]]
    assert db.delete_retirement_workflow(PROD) is False


def test_lists_return_one_row_per_item(db):
    _seed_family(db)
    _insert_history_row(db, PROD)
    db.upsert_retirement_workflow(PROD, {"step_approved_at": "NOW()", "status": "started",
                                         "step_started_at": "NOW()"})

    # Browse / catalog: the sibling join must see the current row only.
    status = db.get_sibling_retirement_status(DEV)
    assert status["workflow_status"] == "started"

    # Performance.
    performance = [row for row in db.list_performance_data() if row["content_id"] == PROD]
    assert len(performance) == 1
    assert performance[0]["workflow_status"] == "started"

    # NonProd.
    nonprod = [row for row in db.list_nonprod_items() if row["content_id"] == PROD]
    assert len(nonprod) == 1
    assert nonprod[0]["workflow_status"] == "started"

    # Retirement page.
    retirement = [row for row in db.list_retirement_items() if row["content_id"] == PROD]
    assert len(retirement) == 1
    assert retirement[0]["workflow_raw_status"] == "started"


def test_current_row_lists_skip_history_rows(db):
    _seed_item(db)
    _insert_history_row(db, PROD)

    # No current row exists, so every current-row read is empty.
    assert db.get_retirement_workflow(PROD) is None
    assert db.list_retirement_workflows() == []
    assert db.list_retirement_workflows(status="retired") == []
    assert db.list_retirement_ready_for_removal() == []
    assert db.auto_close_retired_workflows({PROD}) == 0
    assert db.update_retirement_cleanup(PROD, {"cleanup_error": "x"}) is None
    assert db.record_retirement_pr_state(PROD, "agv_retire_pr_url", {"merged": True}) is None


def test_due_dates_and_prs_ignore_history_rows(db):
    _seed_item(db)
    _insert_history_row(db, PROD)
    db.upsert_retirement_workflow(PROD, {
        "step_approved_at": "NOW()", "step_started_at": "NOW()",
        "retirement_target_date": (datetime.now(timezone.utc) - timedelta(days=1)).date(),
    })

    ready = db.list_retirement_ready_for_removal()
    assert [row["content_id"] for row in ready] == [PROD]

    pr = db.record_retirement_pr(PROD, "agv_retire_pr_url", {
        "pr_url": "https://github.com/rhpds/agnosticv/pull/101", "created_at": datetime.now(timezone.utc),
    })
    assert pr["id"] == _current_id(db, PROD)
    assert pr["agv_retire_pr_url"] == "https://github.com/rhpds/agnosticv/pull/101"


def test_jira_events_of_a_second_workflow_are_a_separate_stream(db):
    _seed_item(db)
    history = _insert_history_row(db, PROD)
    current = db.upsert_retirement_workflow(PROD, {"jira_key": "RHDPCD-9002", "step_retired_at": "NOW()"})

    at = datetime.now(timezone.utc)
    old_event = build_jira_event(dict(history), "workflow_completed", at)
    new_event = build_jira_event(dict(current), "workflow_completed", at)

    assert old_event and new_event
    assert old_event["workflow_created_at"] != new_event["workflow_created_at"]
    assert old_event["event_key"] != new_event["event_key"]


def test_returning_stage_revives_the_family_workflow(db):
    _seed_family(db)
    db.upsert_retirement_workflow(PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})

    # Every stage disappears from the CRD scan: both retire, the workflow closes.
    # Keep every other Babylon row in the "current" set so the database-wide
    # sweep only touches the rows this test owns.
    db.retire_missing_babylon(_other_babylon_ids(db))
    assert db.get_retirement_workflow(PROD)["status"] == "retired"
    assert db.list_nonprod_items() == []

    # One stage comes back. The family workflow closes as revived.
    db.upsert_babylon_catalog_item({"ci_name": f"{BASE}.dev", "stage": "dev"})

    assert db.get_retirement_workflow(PROD) is None
    rows = _workflow_rows(db, PROD)
    assert len(rows) == 1
    assert rows[0]["status"] == "retired"
    assert rows[0]["step_retired_at"] is not None
    assert rows[0]["revived_at"] is not None
    assert rows[0]["revived_reason"] == "CatalogItem returned (catalog refresh)"

    # The item is visible again with no retirement badge.
    nonprod = db.list_nonprod_items()
    assert {row["content_id"] for row in nonprod} == {PROD, DEV}
    assert all(row["workflow_status"] is None for row in nonprod)

    with db.pool.connection() as conn:
        logged = conn.execute(
            "SELECT details FROM analysis_log WHERE ci_name = %s AND action = 'retirement_revived'",
            (BASE,),
        ).fetchall()
    assert [row["details"] for row in logged] == ["Jira: None; workflow closed as revived"]


def test_refresh_does_not_revive_a_path_b_workflow(db):
    """Workflow retired, CatalogItem never retired: the item was not away."""
    _seed_item(db)
    db.upsert_retirement_workflow(PROD, {"step_approved_at": "NOW()", "step_retired_at": "NOW()"})

    db.upsert_babylon_catalog_item({"ci_name": f"{BASE}.prod", "stage": "prod"})

    wf = db.get_retirement_workflow(PROD)
    assert wf is not None
    assert wf["revived_at"] is None
    assert db.list_nonprod_items() == []


def test_returning_item_leaves_a_non_retired_workflow_alone(db):
    _seed_item(db)
    db.upsert_retirement_workflow(PROD, {"step_approved_at": "NOW()", "step_started_at": "NOW()"})
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET retired_at = NOW() WHERE content_id = %s", (PROD,))
        conn.commit()

    db.upsert_babylon_catalog_item({"ci_name": f"{BASE}.prod", "stage": "prod"})

    wf = db.get_retirement_workflow(PROD)
    assert wf is not None
    assert wf["revived_at"] is None
    assert wf["status"] == "started"


def test_stale_jira_closure_does_not_close_the_new_workflow(db):
    """The Jira call outlives the workflow it started on."""
    _seed_item(db)
    old = db.upsert_retirement_workflow(PROD, {"step_approved_at": "NOW()", "step_retired_at": "NOW()",
                                               "jira_key": "RHDPCD-9003"})
    with db.pool.connection() as conn:
        conn.execute("UPDATE retirement_workflow SET revived_at = NOW() WHERE id = %s", (old["id"],))
        conn.commit()
    new = db.upsert_retirement_workflow(PROD, {"jira_key": "RHDPCD-9004"})

    assert db.record_retirement_jira_closure(PROD, old["id"], cancelled=False) is None
    assert db.get_retirement_workflow(PROD)["jira_closed_at"] is None
    assert new["id"] == _current_id(db, PROD)
