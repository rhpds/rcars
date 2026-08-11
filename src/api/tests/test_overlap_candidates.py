"""Tests for deterministic overlap candidate generation."""
import os
import psycopg
import pytest
from rcars.db.database import Database
from rcars.db.overlap import generate_overlap_candidates, prune_stale_candidates

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
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


@pytest.fixture
def seed_items(db):
    """Seed three items: A and B share 1 product + 2 topics, C shares nothing."""
    with db.pool.connection() as conn:
        for cid, name in [("test:a", "Item A"), ("test:b", "Item B"), ("test:c", "Item C")]:
            conn.execute(
                "INSERT INTO content_entities (content_id, source, content_type, display_name) "
                "VALUES (%s, 'test', 'lab', %s) ON CONFLICT DO NOTHING",
                (cid, name),
            )
        conn.execute(
            "INSERT INTO showroom_analysis (content_id, products_json, topics_json, content_hash) "
            "VALUES (%s, %s::jsonb, %s::jsonb, %s) ON CONFLICT (content_id) DO UPDATE "
            "SET products_json = EXCLUDED.products_json, topics_json = EXCLUDED.topics_json, "
            "content_hash = EXCLUDED.content_hash",
            ("test:a", '["OpenShift", "Ansible"]', '["containers", "automation", "networking"]', "hash_a"),
        )
        conn.execute(
            "INSERT INTO showroom_analysis (content_id, products_json, topics_json, content_hash) "
            "VALUES (%s, %s::jsonb, %s::jsonb, %s) ON CONFLICT (content_id) DO UPDATE "
            "SET products_json = EXCLUDED.products_json, topics_json = EXCLUDED.topics_json, "
            "content_hash = EXCLUDED.content_hash",
            ("test:b", '["OpenShift", "RHEL"]', '["containers", "automation", "security"]', "hash_b"),
        )
        conn.execute(
            "INSERT INTO showroom_analysis (content_id, products_json, topics_json, content_hash) "
            "VALUES (%s, %s::jsonb, %s::jsonb, %s) ON CONFLICT (content_id) DO UPDATE "
            "SET products_json = EXCLUDED.products_json, topics_json = EXCLUDED.topics_json, "
            "content_hash = EXCLUDED.content_hash",
            ("test:c", '["RHEL"]', '["storage"]', "hash_c"),
        )
        conn.commit()


def test_generates_candidates_above_threshold(db, seed_items):
    result = generate_overlap_candidates(db.pool, min_products=1, min_topics=2)
    assert result["pairs_inserted"] == 1  # only A-B meets threshold

    with db.pool.connection() as conn:
        rows = conn.execute("SELECT * FROM overlap_candidates").fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert {row["content_id_a"], row["content_id_b"]} == {"test:a", "test:b"}
    assert row["shared_products"] == 1  # OpenShift
    assert row["shared_topics"] == 2  # containers, automation
    assert row["content_hash_a"] is not None
    assert row["content_hash_b"] is not None


def test_idempotent_upsert(db, seed_items):
    generate_overlap_candidates(db.pool, min_products=1, min_topics=2)
    result = generate_overlap_candidates(db.pool, min_products=1, min_topics=2)
    assert result["pairs_updated"] >= 0

    with db.pool.connection() as conn:
        rows = conn.execute("SELECT * FROM overlap_candidates").fetchall()
    assert len(rows) == 1


def test_stage_dedup(db, seed_items):
    """Items sharing a showroom_url collapse to one representative."""
    with db.pool.connection() as conn:
        # Add babylon_items with same showroom_url for A (prod) and a new item D (dev)
        conn.execute(
            "INSERT INTO content_entities (content_id, source, content_type, display_name) "
            "VALUES ('test:d', 'babylon', 'lab', 'Item A Dev') ON CONFLICT DO NOTHING",
        )
        conn.execute(
            "INSERT INTO babylon_items (content_id, ci_name, showroom_url, stage) "
            "VALUES ('test:a', 'ci-a.prod', 'https://git/repo-a', 'prod') ON CONFLICT DO NOTHING",
        )
        conn.execute(
            "INSERT INTO babylon_items (content_id, ci_name, showroom_url, stage) "
            "VALUES ('test:d', 'ci-a.dev', 'https://git/repo-a', 'dev') ON CONFLICT DO NOTHING",
        )
        # D has same analysis as A (it's a stage copy)
        conn.execute(
            "INSERT INTO showroom_analysis (content_id, products_json, topics_json, content_hash) "
            "VALUES ('test:d', %s::jsonb, %s::jsonb, 'hash_a') ON CONFLICT (content_id) DO UPDATE "
            "SET products_json = EXCLUDED.products_json, topics_json = EXCLUDED.topics_json",
            ('["OpenShift", "Ansible"]', '["containers", "automation", "networking"]'),
        )
        conn.commit()

    result = generate_overlap_candidates(db.pool, min_products=1, min_topics=2)
    with db.pool.connection() as conn:
        rows = conn.execute("SELECT * FROM overlap_candidates").fetchall()
    # D should be deduped with A (same showroom_url, A wins as prod)
    # Only A-B pair should exist, not D-B
    assert len(rows) == 1
    pair_ids = {rows[0]["content_id_a"], rows[0]["content_id_b"]}
    assert "test:d" not in pair_ids


def test_prune_stale_retired(db, seed_items):
    """Pruning removes pairs where either item is retired."""
    generate_overlap_candidates(db.pool, min_products=1, min_topics=2)
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET retired_at = NOW() WHERE content_id = 'test:a'")
        conn.commit()
    pruned = prune_stale_candidates(db.pool)
    assert pruned == 1
    with db.pool.connection() as conn:
        rows = conn.execute("SELECT * FROM overlap_candidates").fetchall()
    assert len(rows) == 0
