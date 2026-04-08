"""Tests for RCARS database layer."""

import os
import pytest
from rcars.db import Database


TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    """Create a fresh test database with schema."""
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.drop_schema()
    database.close()


def test_create_schema(db):
    """Schema creation should create all expected tables."""
    tables = db.list_tables()
    assert "catalog_items" in tables
    assert "showroom_analysis" in tables
    assert "enrichment_tags" in tables
    assert "embeddings" in tables
    assert "analysis_log" in tables
    assert "jobs" in tables


def test_upsert_catalog_item(db):
    """Should insert a new catalog item and return it."""
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Test Item",
        "category": "Demos",
        "product": "Red_Hat_OpenShift_Container_Platform",
        "product_family": "Red_Hat_Cloud",
        "primary_bu": "Hybrid_Platforms",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "keywords": ["openshift", "demo"],
        "description": "A test demo item",
        "showroom_url": "https://github.com/example/showroom-test.git",
        "showroom_ref": "main",
        "is_prod": True,
    }
    db.upsert_catalog_item(item)
    result = db.get_catalog_item("test.item.prod")
    assert result is not None
    assert result["display_name"] == "Test Item"
    assert result["category"] == "Demos"
    assert result["is_prod"] is True
    assert result["keywords"] == ["openshift", "demo"]


def test_upsert_catalog_item_updates(db):
    """Upsert should update existing items, not duplicate."""
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Original Name",
        "category": "Demos",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
    }
    db.upsert_catalog_item(item)

    item["display_name"] = "Updated Name"
    db.upsert_catalog_item(item)

    result = db.get_catalog_item("test.item.prod")
    assert result["display_name"] == "Updated Name"

    all_items = db.list_catalog_items()
    assert len(all_items) == 1


def test_list_catalog_items_filter_prod(db):
    """Should filter catalog items by prod status."""
    db.upsert_catalog_item({
        "ci_name": "prod.item",
        "display_name": "Prod Item",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
    })
    db.upsert_catalog_item({
        "ci_name": "dev.item",
        "display_name": "Dev Item",
        "stage": "dev",
        "catalog_namespace": "babylon-catalog-dev",
        "is_prod": False,
    })

    prod_only = db.list_catalog_items(prod_only=True)
    assert len(prod_only) == 1
    assert prod_only[0]["ci_name"] == "prod.item"

    all_items = db.list_catalog_items(prod_only=False)
    assert len(all_items) == 2


def test_log_action(db):
    """Should log an action and retrieve it."""
    db.log_action("test.item", "refresh", user_id=None, details="Initial scan")
    logs = db.get_recent_logs(limit=10)
    assert len(logs) == 1
    assert logs[0]["ci_name"] == "test.item"
    assert logs[0]["action"] == "refresh"
    assert logs[0]["details"] == "Initial scan"


def test_get_status_summary(db):
    """Should return summary counts."""
    db.upsert_catalog_item({
        "ci_name": "item1",
        "display_name": "Item 1",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
        "showroom_url": "https://github.com/example/showroom.git",
    })
    db.upsert_catalog_item({
        "ci_name": "item2",
        "display_name": "Item 2",
        "stage": "dev",
        "catalog_namespace": "babylon-catalog-dev",
        "is_prod": False,
    })

    summary = db.get_status_summary()
    assert summary["total"] == 2
    assert summary["prod"] == 1
    assert summary["with_showroom"] == 1
