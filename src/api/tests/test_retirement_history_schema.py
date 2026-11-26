"""Schema step 1 for RHDPCD-2331: retirement history columns.

These tests start from the OLD retirement_workflow shape (content_id primary
key, no history columns), insert rows, and run create_schema() the way every
deploy does. The upgrade must keep the old rows, give every row a unique id,
add the history columns, and build the partial unique index that lets several
rows share a content_id as long as only one of them is current.
"""

import os
from urllib.parse import urlparse

import psycopg
import pytest

from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)

BASE = "test-history-schema.upgrade"
CONTENT_IDS = (f"babylon:{BASE}.prod", f"babylon:{BASE}.dev")

# The retirement_workflow shape shipped before RHDPCD-2331.
OLD_TABLE_SQL = """
CREATE TABLE retirement_workflow (
    content_id          TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    status              TEXT NOT NULL DEFAULT 'reviewed',
    step_reviewed_at    TIMESTAMPTZ,
    step_reviewed_by    TEXT,
    step_approved_at    TIMESTAMPTZ,
    step_approved_by    TEXT,
    approval_reason     TEXT,
    approval_snapshot   JSONB,
    step_notified_at    TIMESTAMPTZ,
    step_notified_by    TEXT,
    step_started_at     TIMESTAMPTZ,
    step_started_by     TEXT,
    retirement_target_date DATE,
    step_retired_at     TIMESTAMPTZ,
    replacement_ci      TEXT,
    replacement_name    TEXT,
    curator_notes       TEXT,
    jira_key            TEXT,
    jira_project        TEXT NOT NULL DEFAULT 'RHDPCD',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


@pytest.fixture
def db():
    if "test" not in urlparse(TEST_DB_URL).path:
        raise RuntimeError("Retirement schema tests require a test database")
    database = Database(TEST_DB_URL)
    database.create_schema()
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS retirement_workflow CASCADE")
        conn.execute(OLD_TABLE_SQL)
        for content_id in CONTENT_IDS:
            conn.execute(
                "INSERT INTO content_entities (content_id, source, content_type, display_name) "
                "VALUES (%s, 'babylon', 'lab', %s) ON CONFLICT (content_id) DO NOTHING",
                (content_id, BASE),
            )
            conn.execute(
                "INSERT INTO retirement_workflow (content_id, status, step_retired_at, jira_key) "
                "VALUES (%s, 'retired', NOW(), 'RHDPCD-9001')",
                (content_id,),
            )
    yield database
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
        conn.execute(
            "DELETE FROM content_entities WHERE content_id = ANY(%s)", (list(CONTENT_IDS),)
        )
    # Leave the shared test database in the new shape for the other tests.
    database.create_schema()
    database.close()


def _columns(db):
    with db.pool.connection() as conn:
        rows = conn.execute(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'retirement_workflow'"
        ).fetchall()
    return {row["column_name"]: row["is_nullable"] for row in rows}


def _indexes(db):
    with db.pool.connection() as conn:
        rows = conn.execute(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename = 'retirement_workflow'"
        ).fetchall()
    return {row["indexname"]: row["indexdef"] for row in rows}


def _rows(db):
    with db.pool.connection() as conn:
        return conn.execute(
            "SELECT content_id, status, jira_key, step_retired_at, id, revived_at, revived_reason "
            "FROM retirement_workflow WHERE content_id = ANY(%s) ORDER BY content_id",
            (list(CONTENT_IDS),),
        ).fetchall()


def test_old_shape_is_upgraded_and_rows_are_kept(db):
    db.create_schema()

    columns = _columns(db)
    assert "revived_at" in columns
    assert "revived_reason" in columns
    assert "id" in columns and columns["id"] == "NO"

    rows = _rows(db)
    assert [row["content_id"] for row in rows] == sorted(CONTENT_IDS)
    assert all(row["status"] == "retired" for row in rows)
    assert all(row["jira_key"] == "RHDPCD-9001" for row in rows)
    assert all(row["step_retired_at"] is not None for row in rows)
    assert all(row["revived_at"] is None for row in rows)
    assert all(row["revived_reason"] is None for row in rows)
    ids = [row["id"] for row in rows]
    assert all(identity is not None for identity in ids)
    assert len(set(ids)) == len(ids)

    indexes = _indexes(db)
    current_index = indexes["uq_rw_current_content"]
    assert current_index.startswith("CREATE UNIQUE INDEX")
    assert "(revived_at IS NULL)" in current_index


def test_upgrade_is_idempotent(db):
    db.create_schema()
    first_columns = _columns(db)
    first_indexes = _indexes(db)
    first_rows = _rows(db)

    db.create_schema()

    assert _columns(db) == first_columns
    assert _indexes(db) == first_indexes
    assert _rows(db) == first_rows


def test_current_row_index_serves_the_upsert_predicate(db):
    """The next deploy's upsert infers this index from (content_id) WHERE revived_at IS NULL."""
    db.create_schema()
    with db.pool.connection() as conn:
        conn.execute(
            "INSERT INTO retirement_workflow (content_id, status) VALUES (%s, 'reviewed') "
            "ON CONFLICT (content_id) WHERE revived_at IS NULL DO UPDATE SET status = EXCLUDED.status",
            (CONTENT_IDS[0],),
        )
        rows = conn.execute(
            "SELECT status FROM retirement_workflow WHERE content_id = %s", (CONTENT_IDS[0],)
        ).fetchall()
    assert [row["status"] for row in rows] == ["reviewed"]
