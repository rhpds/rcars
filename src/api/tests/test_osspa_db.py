import os
import pytest
from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


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


def test_osspa_tables_exist(db):
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = {row["table_name"] for row in cur.fetchall()}
    assert "portfolio_architectures" in tables
    assert "architecture_analysis" in tables


def test_content_entities_has_status_column(db):
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT column_name, column_default FROM information_schema.columns "
            "WHERE table_name = 'content_entities' AND column_name = 'status'")
        row = cur.fetchone()
    assert row is not None
    assert "prod" in (row["column_default"] or "")


def test_babylon_upsert_writes_status_from_stage(db):
    db.upsert_babylon_catalog_item({"ci_name": "a.dev", "display_name": "A", "stage": "dev"})
    assert db.get_content_entity("babylon:a.dev")["status"] == "dev"

    db.upsert_babylon_catalog_item({"ci_name": "a.dev", "display_name": "A", "stage": "prod"})
    assert db.get_content_entity("babylon:a.dev")["status"] == "prod"


def test_schema_backfills_status_from_stage(db):
    db.upsert_babylon_catalog_item({"ci_name": "b.event", "display_name": "B", "stage": "event"})
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET status = 'prod' WHERE content_id = 'babylon:b.event'")
        conn.commit()

    db.create_schema()  # idempotent re-run, as every deploy does

    assert db.get_content_entity("babylon:b.event")["status"] == "event"
