import os
import pytest
from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)

VECTOR = [0.01] * 768


@pytest.fixture
def db():
    import psycopg
    from urllib.parse import urlparse
    db_name = urlparse(TEST_DB_URL).path.lstrip("/")
    if "test" not in db_name:
        raise RuntimeError(
            f"Refusing to run: database '{db_name}' does not contain 'test'. "
            f"Set RCARS_TEST_DATABASE_URL to a test database."
        )
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        effective_db = conn.execute("SELECT current_database()").fetchone()[0]
        if "test" not in effective_db:
            raise RuntimeError(
                f"Refusing to run: effective database '{effective_db}' does not contain 'test'."
            )
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def _arch(db, ppid, status):
    db.upsert_osspa_item({
        "content_id": f"pa:{ppid}", "ppid": ppid, "pa_name": f"{ppid}-x",
        "display_name": f"Architecture {ppid}", "status": status,
        "summary": "s", "products": [], "topics": [], "audience": [],
        "solutions": ["Security"], "verticals": ["All"],
        "detail_page": f"{ppid}.adoc", "image_url": None,
        "is_live": status == "prod", "show_in_catalog": status == "prod",
        "asset_type": "PA",
    })
    db.store_embedding(f"pa:{ppid}", "architecture", "portfolio_arch",
                       "summary", "Portfolio architecture: x", VECTOR)


def test_search_embeddings_excludes_non_prod_by_default(db):
    _arch(db, 1, "prod")
    _arch(db, 2, "dev")

    rows = db.search_embeddings(VECTOR, limit=10, stages=["prod"], quality_threshold=0.0)

    assert [r["content_id"] for r in rows] == ["pa:1"]


def test_search_embeddings_includes_dev_when_asked(db):
    _arch(db, 1, "prod")
    _arch(db, 2, "dev")

    rows = db.search_embeddings(VECTOR, limit=10, stages=["prod", "dev"], quality_threshold=0.0)

    assert {r["content_id"] for r in rows} == {"pa:1", "pa:2"}


def test_search_embeddings_still_filters_babylon_stages(db):
    db.upsert_babylon_catalog_item({"ci_name": "a.dev", "display_name": "A", "stage": "dev",
                                    "showroom_url": "https://example.com/r"})
    db.store_embedding("babylon:a.dev", "lab", "babylon", "summary", "Hands-on lab: x", VECTOR)

    rows = db.search_embeddings(VECTOR, limit=10, stages=["prod"], quality_threshold=0.0)

    assert rows == []


def test_browse_returns_prod_architectures_with_stage_prod(db):
    _arch(db, 1, "prod")
    _arch(db, 2, "dev")

    result = db.list_content_entities_filtered(
        content_types=["architecture"], stages=["prod"], limit=50)

    assert [i["content_id"] for i in result["items"]] == ["pa:1"]
    assert result["total"] == 1


def test_browse_shows_dev_architectures_for_curators(db):
    _arch(db, 1, "prod")
    _arch(db, 2, "dev")

    result = db.list_content_entities_filtered(
        content_types=["architecture"], stages=["prod", "dev"], limit=50)

    assert {i["content_id"] for i in result["items"]} == {"pa:1", "pa:2"}


def test_browse_default_content_types_exclude_architectures(db):
    _arch(db, 1, "prod")
    db.upsert_babylon_catalog_item({"ci_name": "a.prod", "display_name": "A", "stage": "prod",
                                    "showroom_url": "https://example.com/r"})

    result = db.list_content_entities_filtered(
        content_types=["lab", "demo", "sandbox"], stages=["prod"], limit=50)

    assert [i["content_id"] for i in result["items"]] == ["babylon:a.prod"]


def test_browse_mixed_content_types_return_both_sources(db):
    _arch(db, 1, "prod")
    db.upsert_babylon_catalog_item({"ci_name": "a.prod", "display_name": "A", "stage": "prod",
                                    "showroom_url": "https://example.com/r"})

    result = db.list_content_entities_filtered(
        content_types=["lab", "demo", "sandbox", "architecture"], stages=["prod"], limit=50)

    assert {i["content_id"] for i in result["items"]} == {"pa:1", "babylon:a.prod"}


def test_browse_babylon_only_facet_still_works(db):
    _arch(db, 1, "prod")
    db.upsert_babylon_catalog_item({
        "ci_name": "a.prod", "display_name": "A", "stage": "prod",
        "showroom_url": "https://example.com/r", "is_agd_v2": True, "cloud_provider": "aws"})

    result = db.list_content_entities_filtered(cloud_provider="aws", limit=50)

    assert [i["content_id"] for i in result["items"]] == ["babylon:a.prod"]
