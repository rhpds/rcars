"""Tests for field_source_provisions DB methods. Requires a live PostgreSQL."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    import psycopg
    from urllib.parse import urlparse

    parsed = urlparse(TEST_DB_URL)
    db_name = parsed.path.lstrip("/")
    if "test" not in db_name:
        raise RuntimeError(
            f"Refusing to run: database '{db_name}' does not contain 'test' in its name. "
            f"Set RCARS_TEST_DATABASE_URL to a test database."
        )

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


_ROWS = [
    {
        "catalog_item": "ocp",
        "git_repo": "https://github.com/example/repo1",
        "git_ref": "main",
        "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "retired_at": None,
        "provision_uuid": "uuid-001",
    },
    {
        "catalog_item": "ocp",
        "git_repo": "https://github.com/example/repo1",
        "git_ref": "main",
        "provisioned_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
        "retired_at": datetime(2026, 7, 5, tzinfo=timezone.utc),
        "provision_uuid": "uuid-002",
    },
    {
        "catalog_item": "rhel",
        "git_repo": "https://github.com/example/repo2",
        "git_ref": "v1.0",
        "provisioned_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "retired_at": None,
        "provision_uuid": "uuid-003",
    },
]


def test_upsert_and_query_field_source(db):
    count = db.upsert_field_source_provisions(_ROWS)
    assert count == 3

    # Query all within default 12-month window
    results = db.get_field_source_summary()
    assert len(results) == 3

    # Filter by catalog_item
    ocp_results = db.get_field_source_summary(catalog_item="ocp")
    assert len(ocp_results) == 2
    assert all(r["catalog_item"] == "ocp" for r in ocp_results)

    rhel_results = db.get_field_source_summary(catalog_item="rhel")
    assert len(rhel_results) == 1
    assert rhel_results[0]["git_repo"] == "https://github.com/example/repo2"

    # Dedup: re-upsert same rows should not grow the table
    count2 = db.upsert_field_source_provisions(_ROWS)
    assert count2 == 3
    assert len(db.get_field_source_summary()) == 3


def test_upsert_updates_retired_at(db):
    row = {
        "catalog_item": "ocp",
        "git_repo": "https://github.com/example/repo1",
        "git_ref": "main",
        "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "retired_at": None,
        "provision_uuid": "uuid-retire-test",
    }
    db.upsert_field_source_provisions([row])

    # Now update retired_at
    row["retired_at"] = datetime(2026, 6, 10, tzinfo=timezone.utc)
    db.upsert_field_source_provisions([row])

    results = db.get_field_source_summary(catalog_item="ocp")
    match = next(r for r in results if r["provision_uuid"] == "uuid-retire-test")
    assert match["retired_at"] is not None


def test_delete_field_source(db):
    rows = [
        {
            "catalog_item": "ocp",
            "git_repo": "https://github.com/example/repo1",
            "git_ref": "main",
            "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
            "retired_at": None,
            "provision_uuid": "uuid-del-001",
        }
    ]
    db.upsert_field_source_provisions(rows)
    deleted = db.delete_field_source_provisions()
    assert deleted >= 1
    assert db.get_field_source_summary() == []


def test_empty_upsert(db):
    assert db.upsert_field_source_provisions([]) == 0
