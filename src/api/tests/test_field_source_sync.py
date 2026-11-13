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


def _row(uuid: str, repo: str, ref: str, email: str,
         provisioned: datetime, retired: datetime | None = None) -> dict:
    return {
        "git_repo": repo,
        "git_ref": ref,
        "user_email": email,
        "provisioned_at": provisioned,
        "retired_at": retired,
        "provision_uuid": uuid,
    }


_OCP_ROWS = [
    _row("sync-ocp-uuid-1", "https://github.com/rh-field/ocp-content", "main",
         "user1@redhat.com", datetime(2026, 6, 1, tzinfo=timezone.utc)),
    _row("sync-ocp-uuid-2", "https://github.com/rh-field/ocp-content", "main",
         "user2@redhat.com", datetime(2026, 7, 15, tzinfo=timezone.utc),
         datetime(2026, 7, 20, tzinfo=timezone.utc)),
]

_OCP_SHARED_ROWS = [
    _row("sync-shared-uuid-1", "https://github.com/rh-field/ocp-content", "main",
         "user3@redhat.com", datetime(2026, 9, 1, tzinfo=timezone.utc)),
]

_OCP_CLOUD_ROWS = [
    _row("sync-cloud-uuid-1", "https://github.com/rh-field/cloud-content", "main",
         "user4@redhat.com", datetime(2026, 10, 1, tzinfo=timezone.utc)),
]

_RHEL_ROWS = [
    _row("sync-rhel-uuid-1", "https://github.com/rh-field/rhel-content", "v1.0",
         "user5@redhat.com", datetime(2026, 8, 1, tzinfo=timezone.utc)),
]


def _mock_mcp_query(sql, url, token, **kwargs):
    """Return rows for each tracked published catalog_id."""
    if "1969802" in sql:  # published.ocp-field-asset (dedicated)
        return _OCP_ROWS
    if "1970339" in sql:  # published.ocp-field-asset-shared
        return _OCP_SHARED_ROWS
    if "1970297" in sql:  # published.ocp-cloud-ssa-field-asset
        return _OCP_CLOUD_ROWS
    if "1970276" in sql:  # published.rhel-field-asset
        return _RHEL_ROWS
    return []


def test_field_source_sync_inserts_rows(db):
    """Sync populates field_source_provisions for all four published catalog items."""
    with patch("rcars.services.reporting_sync.mcp_query", side_effect=_mock_mcp_query):
        result = run_field_source_sync(db, FakeSettings())

    assert result["ocp"] == 2
    assert result["ocp_shared"] == 1
    assert result["ocp_cloud"] == 1
    assert result["rhel"] == 1
    assert result["total"] == 5

    rows = db.get_field_source_summary()
    assert len(rows) == 5
    catalog_items = {r["catalog_item"] for r in rows}
    assert catalog_items == {"ocp", "ocp_shared", "ocp_cloud", "rhel"}


def test_field_source_sync_ignores_agd_v2_items(db):
    """Only the published catalog items are queried; agd-v2 IDs are not."""
    queried_ids: list[str] = []

    def tracking_mock(sql, url, token, **kwargs):
        queried_ids.append(sql)
        return _mock_mcp_query(sql, url, token, **kwargs)

    with patch("rcars.services.reporting_sync.mcp_query", side_effect=tracking_mock):
        run_field_source_sync(db, FakeSettings())

    joined = "\n".join(queried_ids)
    assert "1969772" not in joined  # agd-v2.ocp-field-asset-cnv
    assert "1970262" not in joined  # agd-v2.rhel-field-asset-cnv
    assert "1970236" not in joined  # agd-v2.ocp-field-asset-aws


def test_field_source_sync_captures_user_email(db):
    """The user who ordered each provision is stored."""
    with patch("rcars.services.reporting_sync.mcp_query", side_effect=_mock_mcp_query):
        run_field_source_sync(db, FakeSettings())

    rows = db.get_field_source_summary()
    by_uuid = {r["provision_uuid"]: r for r in rows}
    assert by_uuid["sync-ocp-uuid-1"]["user_email"] == "user1@redhat.com"
    assert by_uuid["sync-rhel-uuid-1"]["user_email"] == "user5@redhat.com"


def test_field_source_sync_replaces_on_rerun(db):
    """Re-running the sync replaces old data (full replace, not accumulate)."""
    with patch("rcars.services.reporting_sync.mcp_query", side_effect=_mock_mcp_query):
        run_field_source_sync(db, FakeSettings())
        # Second run returns same rows — total should still be 5, not 10
        run_field_source_sync(db, FakeSettings())

    rows = db.get_field_source_summary()
    assert len(rows) == 5


def test_field_source_sync_no_mcp(db):
    """Returns error dict when MCP is not configured; does not touch DB."""
    class NoMCPSettings:
        reporting_mcp_url = None
        reporting_mcp_token = None

    result = run_field_source_sync(db, NoMCPSettings())
    assert "error" in result
    assert db.get_field_source_summary() == []
