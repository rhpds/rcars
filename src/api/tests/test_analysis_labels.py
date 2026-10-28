"""Tests for Platform/TDP labels on analysis dashboard endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from rcars.api.app import create_app
from rcars.config import Settings
from rcars.db.database import Database

TEST_DB_URL = "postgresql://rcars:dev@localhost:5432/rcars_test"


@pytest.fixture(scope="module")
def db():
    """Create and seed test database."""
    import psycopg
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")

    database = Database(TEST_DB_URL)
    database.create_schema()

    # Seed catalog items with Platform and TDP labels
    database.upsert_babylon_catalog_item({
        "ci_name": "acct.x.prod",
        "display_name": "Account Management Demo",
        "category": "Demos",
        "stage": "prod",
        "platform": "OpenShift",
        "tdp1": "Virtualization",
        "tdp2": None,
    })

    database.upsert_babylon_catalog_item({
        "ci_name": "acct.x.event",
        "display_name": "Account Management Demo",
        "category": "Demos",
        "stage": "event",
        "platform": "OpenShift",
        "tdp1": "Virtualization",
        "tdp2": None,
    })

    # Item with no labels
    database.upsert_babylon_catalog_item({
        "ci_name": "unlabeled.prod",
        "display_name": "Unlabeled Demo",
        "category": "Demos",
        "stage": "prod",
        "platform": None,
        "tdp1": None,
        "tdp2": None,
    })

    # Seed performance data
    with database.pool.connection() as conn:
        conn.execute("""
            INSERT INTO performance_scores (content_id, performance_score)
            VALUES ('babylon:acct.x.prod', 60)
        """)
        conn.execute("""
            INSERT INTO performance_scores (content_id, performance_score)
            VALUES ('babylon:unlabeled.prod', 40)
        """)
        conn.execute("""
            INSERT INTO performance_channels (content_id, channel, provisions)
            VALUES ('babylon:acct.x.prod', 'rhdp', 100),
                   ('babylon:unlabeled.prod', 'rhdp', 50)
        """)
        conn.commit()

    # Seed nonprod usage data
    with database.pool.connection() as conn:
        conn.execute("""
            INSERT INTO nonprod_usage (content_id, catalog_base_name, provisions, requests, unique_users)
            VALUES ('babylon:acct.x.event', 'acct.x', 200, 220, 15)
        """)
        conn.commit()

    yield database
    database.close()


@pytest.fixture(scope="module")
def client(db):
    """Create test client with seeded database."""
    settings = Settings(
        database_url=TEST_DB_URL,
        redis_url="redis://localhost:6379",
        dev_user="curator@redhat.com",
        admin_emails_str="curator@redhat.com",
        curator_emails_str="curator@redhat.com",
        performance_public=True,
    )
    app = create_app(settings)
    # Override db in app state
    app.state.db = db
    with TestClient(app) as c:
        yield c


def test_performance_rows_have_labels(client):
    """Performance dashboard rows include platforms and tdps from labels."""
    resp = client.get("/api/v1/analysis/performance")
    assert resp.status_code == 200
    data = resp.json()

    items = data["items"]
    acct_item = next((i for i in items if i["catalog_base_name"] == "acct.x"), None)
    assert acct_item is not None
    assert "platforms" in acct_item
    assert "tdps" in acct_item
    assert acct_item["platforms"] == ["OpenShift"]
    assert acct_item["tdps"] == ["Virtualization"]


def test_nonprod_rows_have_labels(client):
    """Non-prod dashboard rows include platforms and tdps from labels."""
    resp = client.get("/api/v1/analysis/nonprod")
    assert resp.status_code == 200
    data = resp.json()

    items = data["items"]
    acct_item = next((i for i in items if i["catalog_base_name"] == "acct.x"), None)
    assert acct_item is not None
    assert "platforms" in acct_item
    assert "tdps" in acct_item
    assert acct_item["platforms"] == ["OpenShift"]
    assert acct_item["tdps"] == ["Virtualization"]


def test_retirement_rows_have_labels(client, db):
    """Retirement dashboard rows include platforms and tdps from labels."""
    # Add a retired item to retirement workflow
    with db.pool.connection() as conn:
        conn.execute("""
            UPDATE content_entities
            SET retired_at = NOW() - INTERVAL '10 days'
            WHERE content_id = 'babylon:acct.x.prod'
        """)
        conn.commit()

    resp = client.get("/api/v1/analysis/retirement")
    assert resp.status_code == 200
    data = resp.json()

    items = data["items"]
    acct_item = next((i for i in items if i["catalog_base_name"] == "acct.x"), None)
    assert acct_item is not None
    assert "platforms" in acct_item
    assert "tdps" in acct_item
    assert acct_item["platforms"] == ["OpenShift"]
    assert acct_item["tdps"] == ["Virtualization"]


def test_rows_without_labels_get_empty_lists(client):
    """Rows without labels return empty lists for platforms and tdps."""
    resp = client.get("/api/v1/analysis/performance")
    assert resp.status_code == 200
    data = resp.json()

    items = data["items"]
    unlabeled = next((i for i in items if i["catalog_base_name"] == "unlabeled"), None)
    assert unlabeled is not None
    assert "platforms" in unlabeled
    assert "tdps" in unlabeled
    assert unlabeled["platforms"] == []
    assert unlabeled["tdps"] == []
