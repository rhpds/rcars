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


def _primary_key(db):
    with db.pool.connection() as conn:
        return conn.execute(
            "SELECT pg_get_constraintdef(oid) AS definition FROM pg_constraint "
            "WHERE conrelid = 'retirement_workflow'::regclass AND contype = 'p'"
        ).fetchone()["definition"]


def _index_keys(db, index_name):
    """Key columns of one index, in order, from pg_index."""
    with db.pool.connection() as conn:
        return conn.execute(
            "SELECT array_agg(a.attname ORDER BY k.ord) AS keys "
            "FROM pg_index i "
            "CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum "
            "WHERE i.indexrelid = %s::regclass",
            (index_name,),
        ).fetchone()["keys"]


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
    # Keyed on content_id, not on id: ON CONFLICT (content_id) can only infer this one.
    assert _index_keys(db, "uq_rw_current_content") == ["content_id"]
    # Step 2 moved the primary key to id and dropped the now-redundant index.
    assert _primary_key(db) == "PRIMARY KEY (id)"
    assert "uq_rw_id" not in indexes
    assert "idx_rw_content" in indexes


def test_upgrade_is_idempotent(db):
    db.create_schema()
    first_columns = _columns(db)
    first_indexes = _indexes(db)
    first_rows = _rows(db)

    db.create_schema()

    assert _columns(db) == first_columns
    assert _indexes(db) == first_indexes
    assert _rows(db) == first_rows


# The upsert the next deploy will use. It must update the current row only.
UPSERT_CURRENT_SQL = (
    "INSERT INTO retirement_workflow (content_id, status) VALUES (%s, 'approved') "
    "ON CONFLICT (content_id) WHERE revived_at IS NULL DO UPDATE SET status = EXCLUDED.status"
)


def test_current_row_index_keeps_history_rows_out_of_the_upsert(db):
    """One current row and one history row can share a content_id; the upsert
    updates the current one and leaves the history row alone."""
    db.create_schema()
    with db.pool.connection() as conn:
        before = conn.execute(
            "SELECT id FROM retirement_workflow WHERE content_id = %s", (CONTENT_IDS[0],)
        ).fetchone()
        conn.execute(
            "UPDATE retirement_workflow SET revived_at = NOW() WHERE content_id = %s",
            (CONTENT_IDS[0],),
        )
        conn.execute(
            "INSERT INTO retirement_workflow (content_id, status) VALUES (%s, 'reviewed')",
            (CONTENT_IDS[0],),
        )
        conn.execute(UPSERT_CURRENT_SQL, (CONTENT_IDS[0],))
        rows = conn.execute(
            "SELECT id, status, revived_at FROM retirement_workflow "
            "WHERE content_id = %s ORDER BY id",
            (CONTENT_IDS[0],),
        ).fetchall()

    history = [row for row in rows if row["revived_at"] is not None]
    current = [row for row in rows if row["revived_at"] is None]
    assert len(history) == 1
    assert history[0]["id"] == before["id"]
    assert history[0]["status"] == "retired"
    assert len(current) == 1
    assert current[0]["id"] != before["id"]
    assert current[0]["status"] == "approved"


# The shape one deploy behind: primary key still on content_id, with the step-1
# history columns and index. New code can run against it until init-db finishes.
PR1_SHAPE_DDL = """
CREATE TABLE retirement_workflow (
    content_id          TEXT PRIMARY KEY,
    status              TEXT NOT NULL DEFAULT 'reviewed',
    step_approved_at    TIMESTAMPTZ,
    step_started_at     TIMESTAMPTZ,
    step_retired_at     TIMESTAMPTZ,
    curator_notes       TEXT,
    approval_snapshot   JSONB,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revived_at          TIMESTAMPTZ,
    revived_reason      TEXT,
    id                  BIGSERIAL
);
CREATE UNIQUE INDEX uq_rw_current_content
    ON retirement_workflow(content_id) WHERE revived_at IS NULL;
"""


def _schema_dsn(schema):
    parts = urlparse(TEST_DB_URL)
    password = f" password={parts.password}" if parts.password else ""
    return (f"host={parts.hostname} port={parts.port or 5432} dbname={parts.path.lstrip('/')} "
            f"user={parts.username}{password} options='-csearch_path={schema}'")


def test_upsert_cannot_overwrite_a_history_row_on_the_pr1_shape():
    """Mixed-schema deploy window: the old primary key still matches the content_id."""
    schema = "pr1_shape_2331"
    dsn = _schema_dsn(schema)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        conn.execute(f"CREATE SCHEMA {schema}")
        conn.execute(PR1_SHAPE_DDL)
        conn.execute(
            "INSERT INTO retirement_workflow (content_id, status, step_retired_at, revived_at) "
            "VALUES (%s, 'retired', NOW(), NOW())",
            (CONTENT_IDS[0],),
        )
    database = Database(dsn)
    try:
        with pytest.raises(RuntimeError, match="changed concurrently"):
            database.upsert_retirement_workflow(CONTENT_IDS[0], {"status": "approved"})
        with database.pool.connection() as conn:
            row = conn.execute(
                "SELECT status, revived_at FROM retirement_workflow WHERE content_id = %s",
                (CONTENT_IDS[0],),
            ).fetchone()
        assert row["status"] == "retired"
        assert row["revived_at"] is not None
    finally:
        database.close()
        with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
            conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
