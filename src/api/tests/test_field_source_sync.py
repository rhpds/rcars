"""Tests for run_field_source_sync. Requires a live PostgreSQL test DB."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from rcars.db.database import Database
from rcars.services.reporting_sync import run_field_source_sync

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
            f"Refusing to run: database '{db_name}' does not contain 'test'. "
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


class FakeSettings:
    reporting_mcp_url = "http://fake-mcp"
    reporting_mcp_token = "fake-token"  # noqa: S105


_OCP_ROWS = [
    {
        "git_repo": "https://github.com/rh-field/ocp-content",
        "git_ref": "main",
        "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "retired_at": None,
        "provision_uuid": "sync-ocp-uuid-1",
    },
    {
        "git_repo": "https://github.com/rh-field/ocp-content",
        "git_ref": "main",
        "provisioned_at": datetime(2026, 7, 15, tzinfo=timezone.utc),
        "retired_at": datetime(2026, 7, 20, tzinfo=timezone.utc),
        "provision_uuid": "sync-ocp-uuid-2",
    },
]

_RHEL_ROWS = [
    {
        "git_repo": "https://github.com/rh-field/rhel-content",
        "git_ref": "v1.0",
        "provisioned_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "retired_at": None,
        "provision_uuid": "sync-rhel-uuid-1",
    },
]


def _mock_mcp_query(sql, url, token, **kwargs):
    """Return OCP rows for the OCP catalog_id, RHEL rows for the RHEL catalog_id."""
    if "1969802" in sql:
        return _OCP_ROWS
    if "1970262" in sql:
        return _RHEL_ROWS
    return []


def test_field_source_sync_inserts_rows(db):
    """Sync populates field_source_provisions for both catalog items."""
    with patch("rcars.services.reporting_sync.mcp_query", side_effect=_mock_mcp_query):
        result = run_field_source_sync(db, FakeSettings())

    assert result["ocp"] == 2
    assert result["rhel"] == 1
    assert result["total"] == 3

    rows = db.get_field_source_summary()
    assert len(rows) == 3
    catalog_items = {r["catalog_item"] for r in rows}
    assert catalog_items == {"ocp", "rhel"}


def test_field_source_sync_replaces_on_rerun(db):
    """Re-running the sync replaces old data (full replace, not accumulate)."""
    with patch("rcars.services.reporting_sync.mcp_query", side_effect=_mock_mcp_query):
        run_field_source_sync(db, FakeSettings())
        # Second run returns same rows — total should still be 3, not 6
        run_field_source_sync(db, FakeSettings())

    rows = db.get_field_source_summary()
    assert len(rows) == 3


def test_field_source_sync_no_mcp(db):
    """Returns error dict when MCP is not configured; does not touch DB."""
    class NoMCPSettings:
        reporting_mcp_url = None
        reporting_mcp_token = None

    result = run_field_source_sync(db, NoMCPSettings())
    assert "error" in result
    assert db.get_field_source_summary() == []
