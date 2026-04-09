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


def test_upsert_showroom_analysis(db):
    """Should store and retrieve analysis results."""
    # Need a catalog item first (FK constraint)
    db.upsert_catalog_item({
        "ci_name": "test.item.prod",
        "display_name": "Test",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
    })

    analysis = {
        "ci_name": "test.item.prod",
        "content_type": "workshop",
        "summary": "A test workshop",
        "products_json": ["OpenShift"],
        "audience_json": ["developers"],
        "topics_json": ["kubernetes"],
        "modules_json": [{"title": "Intro", "topics": ["k8s"]}],
        "learning_objectives_json": {
            "stated": ["Learn Kubernetes"],
            "inferred": ["Understand container orchestration"],
        },
        "difficulty": "beginner",
        "estimated_duration_min": 60,
        "last_repo_commit": "abc123",
        "last_repo_updated": "2026-01-01T00:00:00+00:00",
    }
    db.upsert_showroom_analysis(analysis)

    result = db.get_showroom_analysis("test.item.prod")
    assert result is not None
    assert result["content_type"] == "workshop"
    assert result["summary"] == "A test workshop"
    assert result["difficulty"] == "beginner"


def test_store_and_search_embeddings(db):
    """Should store embeddings and search by vector similarity."""
    db.upsert_catalog_item({
        "ci_name": "test.item.prod",
        "display_name": "Test",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
    })

    # Store a CI-level embedding (384 dims)
    embedding = [0.1] * 384
    db.store_embedding(
        ci_name="test.item.prod",
        embed_type="ci_summary",
        content_text="OpenShift Kubernetes workshop for developers",
        embedding=embedding,
    )

    # Search should find it
    results = db.search_embeddings(
        query_embedding=embedding,
        limit=5,
        prod_only=False,
    )
    assert len(results) >= 1
    assert results[0]["ci_name"] == "test.item.prod"


def test_get_items_needing_analysis(db):
    """Should return items with Showroom URLs but no analysis."""
    db.upsert_catalog_item({
        "ci_name": "analyzed.item",
        "display_name": "Analyzed",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
        "showroom_url": "https://github.com/example/repo1.git",
    })
    db.upsert_catalog_item({
        "ci_name": "pending.item",
        "display_name": "Pending",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
        "showroom_url": "https://github.com/example/repo2.git",
    })
    # Only analyze the first one
    db.upsert_showroom_analysis({
        "ci_name": "analyzed.item",
        "content_type": "demo",
        "summary": "Already analyzed",
    })

    pending = db.get_items_needing_analysis()
    ci_names = [p["ci_name"] for p in pending]
    assert "pending.item" in ci_names
    assert "analyzed.item" not in ci_names


def test_add_and_get_tags(db):
    db.upsert_catalog_item({
        "ci_name": "test.lab.prod",
        "display_name": "Test Lab",
        "category": "test",
        "is_prod": True,
        "stage": "prod",
    })
    db.add_enrichment_tag("test.lab.prod", "label", "good for booth demo", "curator@redhat.com")
    db.add_enrichment_tag("test.lab.prod", "label", "new for Summit 2026", "curator@redhat.com")
    tags = db.get_enrichment_tags("test.lab.prod")
    values = [t["tag_value"] for t in tags]
    assert "good for booth demo" in values
    assert "new for Summit 2026" in values


def test_remove_tag(db):
    db.upsert_catalog_item({
        "ci_name": "test.lab.prod",
        "display_name": "Test Lab",
        "stage": "prod",
        "is_prod": True,
    })
    db.add_enrichment_tag("test.lab.prod", "label", "retiring Q3 2026", "curator@redhat.com")
    db.remove_enrichment_tag("test.lab.prod", "label", "retiring Q3 2026")
    tags = db.get_enrichment_tags("test.lab.prod")
    assert not any(t["tag_value"] == "retiring Q3 2026" for t in tags)


def test_duplicate_tag_is_ignored(db):
    db.upsert_catalog_item({
        "ci_name": "test.lab.prod",
        "display_name": "Test Lab",
        "stage": "prod",
        "is_prod": True,
    })
    db.add_enrichment_tag("test.lab.prod", "label", "booth demo", "a@redhat.com")
    db.add_enrichment_tag("test.lab.prod", "label", "booth demo", "b@redhat.com")
    tags = db.get_enrichment_tags("test.lab.prod")
    assert len([t for t in tags if t["tag_value"] == "booth demo"]) == 1


def test_add_and_get_note(db):
    db.upsert_catalog_item({
        "ci_name": "test.lab.prod",
        "display_name": "Test Lab",
        "stage": "prod",
        "is_prod": True,
    })
    db.upsert_showroom_analysis({"ci_name": "test.lab.prod"})
    db.set_enrichment_note("test.lab.prod", "Great for post-Summit follow-ups", "curator@redhat.com")
    note = db.get_enrichment_note("test.lab.prod")
    assert note == "Great for post-Summit follow-ups"


def test_set_and_clear_review_flag(db):
    db.upsert_catalog_item({
        "ci_name": "test.lab.prod",
        "display_name": "Test Lab",
        "stage": "prod",
        "is_prod": True,
    })
    db.upsert_showroom_analysis({"ci_name": "test.lab.prod"})
    db.set_enrichment_review_needed("test.lab.prod", True)
    analysis = db.get_showroom_analysis("test.lab.prod")
    assert analysis["enrichment_review_needed"] is True
    db.set_enrichment_review_needed("test.lab.prod", False)
    analysis = db.get_showroom_analysis("test.lab.prod")
    assert analysis["enrichment_review_needed"] is False


def test_get_db_currency(db):
    status = db.get_db_currency(stale_days=3)
    assert "last_refresh" in status
    assert "is_stale" in status
    assert isinstance(status["is_stale"], bool)


def test_get_enrichment_tags_for_items(db):
    db.upsert_catalog_item({"ci_name": "a.prod", "display_name": "A", "stage": "prod", "is_prod": True})
    db.upsert_catalog_item({"ci_name": "b.prod", "display_name": "B", "stage": "prod", "is_prod": True})
    db.add_enrichment_tag("a.prod", "label", "tag1", "user@test.com")
    db.add_enrichment_tag("b.prod", "label", "tag2", "user@test.com")
    result = db.get_enrichment_tags_for_items(["a.prod", "b.prod"])
    assert "a.prod" in result
    assert "b.prod" in result
    assert len(result["a.prod"]) == 1
    assert result["a.prod"][0]["tag_value"] == "tag1"
