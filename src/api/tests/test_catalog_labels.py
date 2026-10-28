import os
import pytest
from rcars.services.catalog import extract_catalog_item
from rcars.db.database import Database, SCHEMA_SQL

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
        cur = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")

    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def test_extract_reads_platform_and_tdps():
    """Platform and TDP labels are extracted to platform, tdp1, tdp2 keys."""
    crd = {
        "metadata": {
            "name": "test.item.prod",
            "labels": {
                "babylon.gpte.redhat.com/Platform": "OpenShift",
                "babylon.gpte.redhat.com/TDP1": "Virtualization",
                "babylon.gpte.redhat.com/TDP2": "Application_Platform",
                "babylon.gpte.redhat.com/stage": "prod",
            },
        },
        "spec": {
            "displayName": "Test Item",
        },
    }
    result = extract_catalog_item(crd)
    assert result["platform"] == "OpenShift"
    assert result["tdp1"] == "Virtualization"
    assert result["tdp2"] == "Application_Platform"


def test_extract_missing_labels_are_none():
    """Missing or empty label values result in None."""
    # No labels at all
    crd = {
        "metadata": {"name": "test.item.prod"},
        "spec": {"displayName": "Test Item"},
    }
    result = extract_catalog_item(crd)
    assert result["platform"] is None
    assert result["tdp1"] is None
    assert result["tdp2"] is None

    # Empty string values
    crd_empty = {
        "metadata": {
            "name": "test.item.prod",
            "labels": {
                "babylon.gpte.redhat.com/Platform": "",
                "babylon.gpte.redhat.com/TDP1": "",
                "babylon.gpte.redhat.com/TDP2": "",
            },
        },
        "spec": {"displayName": "Test Item"},
    }
    result = extract_catalog_item(crd_empty)
    assert result["platform"] is None
    assert result["tdp1"] is None
    assert result["tdp2"] is None


def test_extract_keys_are_case_sensitive():
    """Label keys are case-sensitive - lowercase 'platform' should not match."""
    crd = {
        "metadata": {
            "name": "test.item.prod",
            "labels": {
                "babylon.gpte.redhat.com/platform": "OpenShift",  # lowercase
            },
        },
        "spec": {"displayName": "Test Item"},
    }
    result = extract_catalog_item(crd)
    assert result["platform"] is None


def test_schema_adds_label_columns():
    """SCHEMA_SQL includes ALTER TABLE statements for the new columns."""
    assert "ALTER TABLE babylon_items ADD COLUMN IF NOT EXISTS platform TEXT" in SCHEMA_SQL
    assert "ALTER TABLE babylon_items ADD COLUMN IF NOT EXISTS tdp1 TEXT" in SCHEMA_SQL
    assert "ALTER TABLE babylon_items ADD COLUMN IF NOT EXISTS tdp2 TEXT" in SCHEMA_SQL


def test_upsert_stores_labels(db):
    """upsert_babylon_catalog_item stores platform/tdp1/tdp2 and updates work."""
    item = {
        "ci_name": "acct.item.prod",
        "display_name": "Test Item",
        "stage": "prod",
        "platform": "RHEL",
        "tdp1": "Server_Cloud_OS",
        "tdp2": None,
    }
    db.upsert_babylon_catalog_item(item)

    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT platform, tdp1, tdp2 FROM babylon_items WHERE ci_name = 'acct.item.prod'"
        )
        row = cur.fetchone()

    assert row is not None
    assert row["platform"] == "RHEL"
    assert row["tdp1"] == "Server_Cloud_OS"
    assert row["tdp2"] is None

    # Update platform
    item["platform"] = "AI"
    db.upsert_babylon_catalog_item(item)

    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT platform, tdp1, tdp2 FROM babylon_items WHERE ci_name = 'acct.item.prod'"
        )
        row = cur.fetchone()

    assert row is not None
    assert row["platform"] == "AI"
    assert row["tdp1"] == "Server_Cloud_OS"
    assert row["tdp2"] is None


def test_labels_union_across_stages(db):
    """Platform and TDP values are unioned across all stages of a base name."""
    # acct.x.dev with OpenShift + Virtualization
    db.upsert_babylon_catalog_item({
        "ci_name": "acct.x.dev",
        "display_name": "Test X Dev",
        "stage": "dev",
        "platform": "OpenShift",
        "tdp1": "Virtualization",
        "tdp2": None,
    })
    # acct.x.prod with AI + AI_Platform
    db.upsert_babylon_catalog_item({
        "ci_name": "acct.x.prod",
        "display_name": "Test X Prod",
        "stage": "prod",
        "platform": "AI",
        "tdp1": "AI_Platform",
        "tdp2": None,
    })

    result = db.get_labels_for_base_names(["acct.x"])

    assert result == {
        "acct.x": {
            "platforms": ["AI", "OpenShift"],
            "tdps": ["AI_Platform", "Virtualization"],
        }
    }


def test_labels_union_tdp2_only(db):
    """tdps list includes tdp2 values when tdp1 is NULL."""
    db.upsert_babylon_catalog_item({
        "ci_name": "acct.y.prod",
        "display_name": "Test Y Prod",
        "stage": "prod",
        "platform": None,
        "tdp1": None,
        "tdp2": "Automation",
    })

    result = db.get_labels_for_base_names(["acct.y"])

    assert result == {
        "acct.y": {
            "platforms": [],
            "tdps": ["Automation"],
        }
    }


def test_labels_include_retired_stage(db):
    """Retired stages are included in the label union."""
    db.upsert_babylon_catalog_item({
        "ci_name": "acct.z.prod",
        "display_name": "Test Z Prod",
        "stage": "prod",
        "platform": "RHEL",
        "tdp1": None,
        "tdp2": None,
    })

    # Retire the item
    with db.pool.connection() as conn:
        conn.execute(
            "UPDATE content_entities SET retired_at = NOW() "
            "WHERE content_id = (SELECT content_id FROM babylon_items WHERE ci_name = 'acct.z.prod')"
        )
        conn.commit()

    result = db.get_labels_for_base_names(["acct.z"])

    assert result == {
        "acct.z": {
            "platforms": ["RHEL"],
            "tdps": [],
        }
    }


def test_labels_unlabeled_item_has_empty_lists(db):
    """Items with all NULL labels still appear in results with empty lists."""
    db.upsert_babylon_catalog_item({
        "ci_name": "acct.n.prod",
        "display_name": "Test N Prod",
        "stage": "prod",
        "platform": None,
        "tdp1": None,
        "tdp2": None,
    })

    result = db.get_labels_for_base_names(["acct.n"])

    assert result == {
        "acct.n": {
            "platforms": [],
            "tdps": [],
        }
    }


def test_labels_empty_input(db):
    """Empty input list returns empty dict."""
    result = db.get_labels_for_base_names([])
    assert result == {}
