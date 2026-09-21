"""API tests for GET /api/v1/analysis/field-source."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings
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


@pytest.fixture
def client(db):
    settings = Settings(
        database_url=TEST_DB_URL,
        redis_url="redis://localhost:6379",
        dev_user="test@redhat.com",
        admin_emails_str="test@redhat.com",
        curator_emails_str="test@redhat.com",
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def test_field_source_endpoint(client, db):
    db.upsert_field_source_provisions([
        {"catalog_item": "ocp", "git_repo": "https://github.com/ex/r1",
         "git_ref": "main", "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "api-uuid-1"},
        {"catalog_item": "ocp", "git_repo": "https://github.com/ex/r1",
         "git_ref": "main", "provisioned_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "api-uuid-2"},
    ])
    resp = client.get("/api/v1/analysis/field-source")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_repos"] == 1
    assert data["total_provisions"] == 2
    assert data["repos"][0]["provision_count"] == 2


def test_field_source_filter(client, db):
    db.upsert_field_source_provisions([
        {"catalog_item": "ocp", "git_repo": "https://github.com/ex/r1",
         "git_ref": "main", "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "filt-uuid-1"},
        {"catalog_item": "rhel", "git_repo": "https://github.com/ex/r2",
         "git_ref": "v1.0", "provisioned_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
         "retired_at": None, "provision_uuid": "filt-uuid-2"},
    ])
    resp = client.get("/api/v1/analysis/field-source?catalog_item=ocp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_repos"] == 1
    assert data["repos"][0]["catalog_item"] == "ocp"


def test_field_source_route_registered():
    """Verify the endpoint is registered on the analysis router."""
    from rcars.api.routes.analysis import router
    paths = [r.path for r in router.routes]
    assert "/analysis/field-source" in paths
