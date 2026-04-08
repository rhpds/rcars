"""Integration tests against live Babylon cluster.

Run with: pytest tests/test_integration.py -v -m integration
Requires: oc login to a Babylon cluster
"""

import os
import pytest
from rcars.catalog_reader import CatalogReader, extract_catalog_item, extract_showroom_url
from rcars.config import Settings
from rcars.db import Database

pytestmark = pytest.mark.integration

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def reader():
    """CatalogReader connected to real cluster."""
    settings = Settings()
    return CatalogReader(settings.kubeconfig_path)


@pytest.fixture
def db():
    """Clean test database."""
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.drop_schema()
    database.close()


def test_list_prod_catalog_items(reader):
    """Should list CatalogItems from babylon-catalog-prod."""
    items = reader.list_catalog_items("babylon-catalog-prod")
    assert len(items) > 0
    first = items[0]
    assert "metadata" in first
    assert "spec" in first
    assert "name" in first["metadata"]


def test_extract_real_catalog_item(reader):
    """Should extract fields from a real CatalogItem."""
    items = reader.list_catalog_items("babylon-catalog-prod")
    assert len(items) > 0
    result = extract_catalog_item(items[0])
    assert result["ci_name"] != ""
    assert result["catalog_namespace"] == "babylon-catalog-prod"
    assert result["is_prod"] is True


def test_get_agnosticv_component(reader):
    """Should fetch a matching AgnosticVComponent."""
    items = reader.list_catalog_items("babylon-catalog-prod")
    assert len(items) > 0
    ci_name = items[0]["metadata"]["name"]
    component = reader.get_agnosticv_component(ci_name, "babylon-config")
    if component:
        assert "spec" in component
        assert "definition" in component["spec"]


def test_full_refresh_to_db(reader, db):
    """Full refresh should populate the database."""
    items = reader.refresh_catalog(
        namespaces=["babylon-catalog-prod"],
        component_namespace="babylon-config",
    )
    assert len(items) > 0

    for item in items:
        db.upsert_catalog_item(item)

    summary = db.get_status_summary()
    assert summary["total"] > 0
    assert summary["prod"] > 0
    assert summary["with_showroom"] > 0


def test_showroom_url_extraction_no_secrets(reader):
    """Showroom URL extraction must never return vault/secret data."""
    items = reader.list_catalog_items("babylon-catalog-prod")
    for crd in items[:10]:
        ci_name = crd["metadata"]["name"]
        component = reader.get_agnosticv_component(ci_name, "babylon-config")
        if component:
            url, ref = extract_showroom_url(component)
            if url:
                assert "ANSIBLE_VAULT" not in url
                assert "ssh-rsa" not in url
            if ref:
                assert "ANSIBLE_VAULT" not in ref
