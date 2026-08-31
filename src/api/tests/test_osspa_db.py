import os
import pytest
from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


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
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")

    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def test_osspa_tables_exist(db):
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = {row["table_name"] for row in cur.fetchall()}
    assert "portfolio_architectures" in tables
    assert "architecture_analysis" in tables


def test_content_entities_has_status_column(db):
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT column_name, column_default FROM information_schema.columns "
            "WHERE table_name = 'content_entities' AND column_name = 'status'")
        row = cur.fetchone()
    assert row is not None
    assert "prod" in (row["column_default"] or "")


def test_babylon_upsert_writes_status_from_stage(db):
    db.upsert_babylon_catalog_item({"ci_name": "a.dev", "display_name": "A", "stage": "dev"})
    assert db.get_content_entity("babylon:a.dev")["status"] == "dev"

    db.upsert_babylon_catalog_item({"ci_name": "a.dev", "display_name": "A", "stage": "prod"})
    assert db.get_content_entity("babylon:a.dev")["status"] == "prod"


def test_schema_backfills_status_from_stage(db):
    db.upsert_babylon_catalog_item({"ci_name": "b.event", "display_name": "B", "stage": "event"})
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET status = 'prod' WHERE content_id = 'babylon:b.event'")
        conn.commit()

    db.create_schema()  # idempotent re-run, as every deploy does

    assert db.get_content_entity("babylon:b.event")["status"] == "event"


def _row(ppid=275, status="prod", **overrides):
    row = {
        "content_id": f"pa:{ppid}",
        "ppid": ppid,
        "pa_name": f"{ppid}-rhacs-multitenant",
        "display_name": "Multitenant Setup for RHACS",
        "status": status,
        "summary": "CSV seed summary",
        "products": ["Red Hat Advanced Cluster Security"],
        "topics": ["Security", "All"],
        "audience": ["architect", "developer"],
        "verticals": ["All"],
        "solutions": ["Security"],
        "detail_page": "rhacs-multitenant.adoc",
        "image_url": "images/rhacs.png",
        "is_live": True,
        "show_in_catalog": True,
        "asset_type": "PA",
    }
    row.update(overrides)
    return row


def test_upsert_osspa_item_writes_all_three_rows(db):
    content_id = db.upsert_osspa_item(_row())
    assert content_id == "pa:275"

    entity = db.get_content_entity(content_id)
    assert entity["source"] == "portfolio_arch"
    assert entity["content_type"] == "architecture"
    assert entity["is_hands_on"] is False
    assert entity["status"] == "prod"
    assert entity["summary"] == "CSV seed summary"

    pa = db.get_portfolio_architecture(content_id)
    assert pa["ppid"] == 275
    assert pa["solutions"] == ["Security"]
    assert pa["is_live"] is True

    assert db.get_architecture_analysis(content_id)["asset_type"] == "PA"


def test_upsert_osspa_item_never_overwrites_llm_owned_fields(db):
    db.upsert_osspa_item(_row())
    db.update_content_entity_card(
        "pa:275", summary="LLM summary", products_json=["OpenShift"],
        topics_json=["gitops"], audience_json=["platform engineers"], difficulty="intermediate")

    db.upsert_osspa_item(_row(display_name="Renamed", image_url="images/new.png"))

    entity = db.get_content_entity("pa:275")
    assert entity["display_name"] == "Renamed"
    assert entity["summary"] == "LLM summary"
    assert entity["products_json"] == ["OpenShift"]
    assert entity["topics_json"] == ["gitops"]
    assert entity["audience_json"] == ["platform engineers"]
    assert entity["difficulty"] == "intermediate"
    assert db.get_portfolio_architecture("pa:275")["image_url"] == "images/new.png"


def test_upsert_osspa_item_unretires_on_reappearance(db):
    db.upsert_osspa_item(_row())
    db.retire_missing_osspa(set())
    assert db.get_content_entity("pa:275")["retired_at"] is not None

    db.upsert_osspa_item(_row())
    entity = db.get_content_entity("pa:275")
    assert entity["retired_at"] is None
    assert entity["retirement_reason"] is None


def test_retire_missing_osspa_only_touches_portfolio_arch(db):
    db.upsert_babylon_catalog_item({"ci_name": "keep.prod", "display_name": "Keep", "stage": "prod"})
    db.upsert_osspa_item(_row(ppid=1))
    db.upsert_osspa_item(_row(ppid=2))

    retired = db.retire_missing_osspa({"pa:1"})

    assert [r["content_id"] for r in retired] == ["pa:2"]
    assert db.get_content_entity("pa:1")["retired_at"] is None
    assert db.get_content_entity("babylon:keep.prod")["retired_at"] is None
    assert db.count_active_osspa() == 1


def test_architecture_analysis_staleness_round_trip(db):
    db.upsert_osspa_item(_row())
    db.mark_architecture_stale("pa:275", stale_commit="abc123")
    analysis = db.get_architecture_analysis("pa:275")
    assert analysis["is_stale"] is True
    assert analysis["stale_commit"] == "abc123"

    db.upsert_architecture_analysis({
        "content_id": "pa:275",
        "summary": "LLM summary",
        "products_json": ["OpenShift"],
        "topics_json": ["gitops"],
        "audience_json": ["architects"],
        "recommender_audience_json": ["solution architects"],
        "difficulty": "intermediate",
        "content_hash": "hash-1",
        "solution_areas_json": ["Application Platform"],
        "use_cases_json": ["Multi-tenant security"],
        "key_components_json": ["RHACS"],
        "detailed_topics_json": ["admission control", "image scanning"],
    })
    db.clear_architecture_stale("pa:275")

    analysis = db.get_architecture_analysis("pa:275")
    assert analysis["is_stale"] is False
    assert analysis["stale_commit"] is None
    assert analysis["content_hash"] == "hash-1"
    assert analysis["recommender_audience_json"] == ["solution architects"]
    assert analysis["asset_type"] == "PA"
    assert analysis["last_analyzed"] is not None


def test_ensure_architecture_analysis_row_is_stale(db):
    db.upsert_osspa_item(_row())
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM architecture_analysis WHERE content_id = 'pa:275'")
        conn.commit()

    db.ensure_architecture_analysis_row("pa:275")

    analysis = db.get_architecture_analysis("pa:275")
    assert analysis is not None
    assert analysis["is_stale"] is True


def test_advisory_lock_is_not_reentrant_across_sessions(db):
    from rcars.db.database import Database
    other = Database(TEST_DB_URL)
    try:
        with db.advisory_lock(736372) as first:
            assert first is True
            with other.advisory_lock(736372) as second:
                assert second is False
        with other.advisory_lock(736372) as third:
            assert third is True
    finally:
        other.close()


def test_curator_note_and_flag_are_source_aware(db):
    db.upsert_osspa_item(_row())
    db.set_enrichment_note("pa:275", "curator note")
    db.set_enrichment_review_flag("pa:275", True)

    analysis = db.get_architecture_analysis("pa:275")
    assert analysis["notes"] == "curator note"
    assert analysis["enrichment_review_needed"] is True

    db.upsert_babylon_catalog_item({"ci_name": "b.prod", "display_name": "B", "stage": "prod"})
    db.upsert_showroom_analysis({"content_id": "babylon:b.prod", "summary": "s"})
    db.set_enrichment_note("babylon:b.prod", "babylon note")
    assert db.get_showroom_analysis("babylon:b.prod")["notes"] == "babylon note"
