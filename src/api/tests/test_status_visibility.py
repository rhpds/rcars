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


def test_browse_reports_retirement_workflow_status(db):
    for name in ("a", "b", "c", "d"):
        db.upsert_babylon_catalog_item({"ci_name": f"{name}.prod", "display_name": name.upper(),
                                        "stage": "prod", "showroom_url": "https://example.com/r"})
    db.upsert_retirement_workflow("babylon:a.prod", {"status": "approved", "step_approved_at": "NOW()"})
    db.upsert_retirement_workflow("babylon:b.prod", {
        "status": "started", "step_approved_at": "NOW()", "retirement_target_date": "2026-11-22"})
    db.upsert_retirement_workflow("babylon:c.prod", {"status": "reviewed"})

    result = db.list_content_entities_filtered(stages=["prod"], limit=50)
    by_id = {i["content_id"]: i for i in result["items"]}

    assert by_id["babylon:a.prod"]["workflow_status"] == "approved"
    assert by_id["babylon:b.prod"]["workflow_status"] == "started"
    assert str(by_id["babylon:b.prod"]["retirement_target_date"]) == "2026-11-22"
    assert by_id["babylon:c.prod"]["workflow_status"] is None
    assert by_id["babylon:d.prod"]["workflow_status"] is None


def test_browse_maps_retirement_to_sibling_stages(db):
    # Stages of one CI share a description, so retiring one stage retires them all.
    for ci in ("cluster.dev", "cluster.event", "combined.dev", "combined.prod", "other.dev"):
        stage = ci.rsplit(".", 1)[1]
        db.upsert_babylon_catalog_item({"ci_name": ci, "display_name": ci, "stage": stage,
                                        "showroom_url": "https://example.com/r"})
    db.upsert_retirement_workflow("babylon:cluster.event", {
        "status": "started", "step_approved_at": "NOW()", "retirement_target_date": "2026-11-22"})
    db.upsert_retirement_workflow("babylon:combined.prod", {"status": "approved", "step_approved_at": "NOW()"})

    result = db.list_content_entities_filtered(stages=["prod", "event", "dev"], limit=50)
    by_id = {i["content_id"]: i for i in result["items"]}

    for cid in ("babylon:cluster.dev", "babylon:cluster.event"):
        assert by_id[cid]["workflow_status"] == "started"
        assert str(by_id[cid]["retirement_target_date"]) == "2026-11-22"
        assert by_id[cid]["retirement_label"] == "in_progress"
    for cid in ("babylon:combined.dev", "babylon:combined.prod"):
        assert by_id[cid]["workflow_status"] == "approved"
        assert by_id[cid]["retirement_label"] == "recommended"
    assert by_id["babylon:other.dev"]["workflow_status"] is None
    assert by_id["babylon:other.dev"]["retirement_label"] is None


def test_browse_sibling_retirement_ignores_unapproved_own_row(db):
    for ci in ("x.dev", "x.event"):
        db.upsert_babylon_catalog_item({"ci_name": ci, "display_name": ci, "stage": ci.split(".")[1],
                                        "showroom_url": "https://example.com/r"})
    db.upsert_retirement_workflow("babylon:x.dev", {"status": "reviewed"})
    db.upsert_retirement_workflow("babylon:x.event", {"status": "started", "step_approved_at": "NOW()"})

    result = db.list_content_entities_filtered(stages=["event", "dev"], limit=50)
    by_id = {i["content_id"]: i for i in result["items"]}

    assert by_id["babylon:x.dev"]["workflow_status"] == "started"


def test_nonprod_list_hides_items_retired_from_babylon(db):
    # Usage rows stay until the next reporting sync, but a catalog refresh
    # that soft-deletes the item must hide it right away.
    for ci in ("keep.event", "gone.event"):
        db.upsert_babylon_catalog_item({"ci_name": ci, "display_name": ci, "stage": "event",
                                        "showroom_url": "https://example.com/r"})
    with db._pool.connection() as conn:
        for ci in ("keep.event", "gone.event"):
            conn.execute(
                "INSERT INTO nonprod_usage (content_id, catalog_base_name, provisions) VALUES (%s, %s, 5)",
                (f"babylon:{ci}", ci.split(".")[0]),
            )
        conn.commit()
    db.retire_missing_babylon({"babylon:keep.event"})

    ids = {i["content_id"] for i in db.list_nonprod_items()}

    assert ids == {"babylon:keep.event"}
