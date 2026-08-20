"""Tests for the vocabulary_unknown_terms queue. Requires a live PostgreSQL."""

from __future__ import annotations

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

    parsed = urlparse(TEST_DB_URL)
    db_name = parsed.path.lstrip("/")
    if "test" not in db_name:
        raise RuntimeError(
            f"Refusing to run: database '{db_name}' does not contain 'test' in its name. "
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


class TestUnknownTermsSchema:
    def test_table_created(self, db):
        with db.pool.connection() as conn:
            cur = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'vocabulary_unknown_terms'"
            )
            assert cur.fetchone() is not None

    def test_recommender_audience_column_added(self, db):
        with db.pool.connection() as conn:
            cur = conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'showroom_analysis' "
                "AND column_name = 'recommender_audience_json'"
            )
            assert cur.fetchone() is not None


class TestRecordUnknownTerm:
    def test_records_one_row(self, db):
        db.record_unknown_term("products", "Wombat Server", example_content_id="babylon:lb1")
        rows = db.get_unknown_terms()
        assert len(rows) == 1
        assert rows[0]["dimension"] == "products"
        assert rows[0]["term"] == "Wombat Server"
        assert rows[0]["occurrences"] == 1
        assert rows[0]["status"] == "pending"
        assert rows[0]["example_content_id"] == "babylon:lb1"

    def test_reseeing_bumps_counter_not_rows(self, db):
        db.record_unknown_term("products", "Wombat Server")
        db.record_unknown_term("products", "Wombat Server")
        rows = db.get_unknown_terms()
        assert len(rows) == 1
        assert rows[0]["occurrences"] == 2
        assert rows[0]["last_seen"] >= rows[0]["first_seen"]

    def test_same_term_different_dimensions_are_separate_rows(self, db):
        db.record_unknown_term("products", "Edge")
        db.record_unknown_term("platforms", "Edge")
        assert len(db.get_unknown_terms()) == 2

    def test_rejected_term_is_not_reupserted(self, db):
        db.record_unknown_term("products", "Wombat Server")
        db.resolve_unknown_term("products", "Wombat Server", "reject", None, "admin@redhat.com")
        db.record_unknown_term("products", "Wombat Server")
        rows = db.get_unknown_terms(status=None)
        assert len(rows) == 1
        assert rows[0]["status"] == "rejected"
        assert rows[0]["occurrences"] == 1

    def test_rejected_term_excluded_from_pending_queue(self, db):
        db.record_unknown_term("products", "Wombat Server")
        db.resolve_unknown_term("products", "Wombat Server", "reject", None, "admin@redhat.com")
        assert db.get_unknown_terms(status="pending") == []


class TestGetUnknownTerms:
    def test_ranked_by_occurrences_desc(self, db):
        db.record_unknown_term("products", "Rare")
        for _ in range(3):
            db.record_unknown_term("products", "Common")
        terms = [r["term"] for r in db.get_unknown_terms()]
        assert terms == ["Common", "Rare"]

    def test_filter_by_dimension(self, db):
        db.record_unknown_term("products", "P")
        db.record_unknown_term("verticals", "V")
        rows = db.get_unknown_terms(dimension="verticals")
        assert [r["term"] for r in rows] == ["V"]


class TestResolveUnknownTerm:
    def test_alias_records_target(self, db):
        db.record_unknown_term("products", "RHOCP")
        row = db.resolve_unknown_term(
            "products", "RHOCP", "alias",
            "Red Hat OpenShift Container Platform", "admin@redhat.com",
        )
        assert row["status"] == "aliased"
        assert row["resolved_to"] == "Red Hat OpenShift Container Platform"
        assert row["resolved_by"] == "admin@redhat.com"
        assert row["resolved_at"] is not None

    def test_promote_sets_status(self, db):
        db.record_unknown_term("products", "Brand New Product")
        row = db.resolve_unknown_term(
            "products", "Brand New Product", "promote", None, "admin@redhat.com"
        )
        assert row["status"] == "promoted"

    def test_missing_term_returns_none(self, db):
        assert db.resolve_unknown_term(
            "products", "Nope", "reject", None, "admin@redhat.com"
        ) is None


class TestReviewBadgeUntouched:
    def test_normalization_never_sets_review_flags(self, db):
        """Vocabulary work never sets enrichment_review_needed or review_reasons."""
        from rcars.services.vocabulary import normalize_analysis

        db.upsert_babylon_catalog_item({
            "ci_name": "lb1",
            "display_name": "Lab One",
            "category": "workshop",
            "stage": "prod",
            "showroom_url": "https://example.com/showroom.git",
        })
        db.upsert_showroom_analysis({
            "content_id": "babylon:lb1",
            "summary": "A lab",
            "enrichment_review_needed": False,
            "review_reasons": None,
        })

        normalize_analysis(
            {"products": ["Wombat Server 3000"], "topics": ["a", "A"]},
            "lab",
            db=db,
            content_id="babylon:lb1",
        )

        with db.pool.connection() as conn:
            cur = conn.execute(
                "SELECT enrichment_review_needed, review_reasons "
                "FROM showroom_analysis WHERE content_id = 'babylon:lb1'"
            )
            row = cur.fetchone()
        assert row["enrichment_review_needed"] is False
        assert row["review_reasons"] is None
        assert len(db.get_unknown_terms()) == 1
