"""Tests for rcars.db.similarity — standalone similarity functions."""

import os
import psycopg
from psycopg.rows import dict_row
import pytest
from rcars.db.database import Database
from rcars.db.similarity import (
    compute_content_similarity,
    get_overlap_items,
    get_similar_items,
    get_similarity_stats,
)

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


def _make_vector(similarity_to_base: float, dim: int = 768) -> str:
    """Create a vector with known cosine similarity to the base vector [1, 0, 0, ...].

    Uses cos(θ), sin(θ) in the first two components, zeros elsewhere.
    """
    import math
    theta = math.acos(similarity_to_base)
    components = [0.0] * dim
    components[0] = math.cos(theta)
    components[1] = math.sin(theta)
    return "[" + ",".join(f"{c:.6f}" for c in components) + "]"


BASE_VECTOR = _make_vector(1.0)       # [1, 0, 0, ...]
VECTOR_96 = _make_vector(0.96)        # cosine sim ~0.96 to base
VECTOR_88 = _make_vector(0.88)        # cosine sim ~0.88 to base
VECTOR_78 = _make_vector(0.78)        # cosine sim ~0.78 to base
VECTOR_50 = _make_vector(0.50)        # cosine sim ~0.50 to base (below storage threshold)


@pytest.fixture
def db():
    """Create a fresh test database with schema and seed data."""
    with psycopg.connect(TEST_DB_URL, autocommit=True, row_factory=dict_row) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Drop all public tables for a clean slate
        cur = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row['tablename']} CASCADE")

    database = Database(TEST_DB_URL)
    database.create_schema()
    _seed_test_data(database)
    yield database
    database.close()


def _seed_test_data(db: Database):
    """Insert content_entities, babylon_items, and embeddings for testing."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            # 4 Babylon content entities — all source='babylon', same stage
            for i, (cid, name, ctype) in enumerate([
                ("babylon:ns.item-a.prod", "Item A", "lab"),
                ("babylon:ns.item-b.prod", "Item B", "lab"),
                ("babylon:ns.item-c.prod", "Item C", "demo"),
                ("babylon:ns.item-d.prod", "Item D", "lab"),
            ]):
                cur.execute(
                    """INSERT INTO content_entities
                       (content_id, source, content_type, is_hands_on, display_name)
                       VALUES (%s, 'babylon', %s, TRUE, %s)""",
                    (cid, ctype, name),
                )
                cur.execute(
                    """INSERT INTO babylon_items
                       (content_id, ci_name, category, stage, is_published)
                       VALUES (%s, %s, 'workshop', 'prod', FALSE)""",
                    (cid, f"ns.item-{chr(97+i)}.prod"),
                )

            # Summary embeddings — known cosine similarities to Item A's base vector
            vectors = [
                ("babylon:ns.item-a.prod", BASE_VECTOR),
                ("babylon:ns.item-b.prod", VECTOR_96),   # ~0.96 sim to A
                ("babylon:ns.item-c.prod", VECTOR_88),   # ~0.88 sim to A
                ("babylon:ns.item-d.prod", VECTOR_78),   # ~0.78 sim to A
            ]
            for cid, vec in vectors:
                cur.execute(
                    """INSERT INTO embeddings
                       (content_id, content_type, source, embed_type, content_text, embedding)
                       VALUES (%s, 'lab', 'babylon', 'summary', 'test', %s::vector)""",
                    (cid, vec),
                )
        conn.commit()


def test_compute_stores_pairs_above_threshold(db):
    result = compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    assert result["pairs_stored"] >= 2
    assert result["threshold"] == 0.75
    assert result["stage"] == "prod"


def test_compute_respects_threshold(db):
    high = compute_content_similarity(db.pool, threshold=0.90, stage="prod")
    low = compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    assert high["pairs_stored"] <= low["pairs_stored"]


def test_get_similar_items_returns_neighbors(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    items = get_similar_items(db.pool, "babylon:ns.item-a.prod", min_score=0.75)
    assert len(items) >= 1
    assert all(item["similarity_score"] >= 0.75 for item in items)
    assert items[0]["similarity_score"] >= items[-1]["similarity_score"]


def test_get_similar_items_min_score_filters(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    all_items = get_similar_items(db.pool, "babylon:ns.item-a.prod", min_score=0.75)
    high_items = get_similar_items(db.pool, "babylon:ns.item-a.prod", min_score=0.90)
    assert len(high_items) <= len(all_items)


def test_get_similarity_stats_returns_counts(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    stats = get_similarity_stats(db.pool)
    assert stats["total_pairs_stored"] >= 1
    assert "high_overlap" in stats
    assert "related_band" in stats
    assert "near_duplicates" in stats
    assert stats["last_computed"] is not None


def test_compute_marks_same_source_as_overlap(db):
    """All seeded items are source='babylon' — pairs should be relationship_type='overlap'."""
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    with db.pool.connection() as conn:
        cur = conn.execute("SELECT DISTINCT relationship_type FROM content_similarity")
        types = {row["relationship_type"] for row in cur.fetchall()}
    assert types == {"overlap"}


def test_compute_returns_overlap_and_related_counts(db):
    result = compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    assert "overlap_pairs" in result
    assert "related_pairs" in result
    assert result["overlap_pairs"] >= 1
    assert result["related_pairs"] == 0  # no cross-source items seeded


def test_compute_cross_source_marked_as_related(db):
    """Insert a non-Babylon item with a similar embedding — should produce 'related' pairs."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO content_entities
                   (content_id, source, content_type, is_hands_on, display_name)
                   VALUES ('pa:999', 'portfolio_arch', 'architecture', FALSE, 'Test Architecture')"""
            )
            cur.execute(
                """INSERT INTO embeddings
                   (content_id, content_type, source, embed_type, content_text, embedding)
                   VALUES ('pa:999', 'architecture', 'portfolio_arch', 'summary', 'test', %s::vector)""",
                (VECTOR_88,),
            )
        conn.commit()

    result = compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    assert result["related_pairs"] >= 1

    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT relationship_type FROM content_similarity WHERE content_id_a = 'pa:999' OR content_id_b = 'pa:999'"
        )
        types = {row["relationship_type"] for row in cur.fetchall()}
    assert types == {"related"}


def test_stats_returns_band_breakdowns(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    stats = get_similarity_stats(db.pool)
    assert "near_duplicates" in stats
    assert "high_overlap" in stats
    assert "related_band" in stats
    assert "total_pairs_stored" in stats
    assert stats["last_computed"] is not None


def test_stats_filters_by_relationship_type(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    overlap_stats = get_similarity_stats(db.pool, relationship_type="overlap")
    assert overlap_stats["total_pairs_stored"] >= 1


def test_get_overlap_items_returns_item_centric_results(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    result = get_overlap_items(db.pool, min_score=0.75)
    assert "items" in result
    assert "total_items" in result
    assert "page" in result
    assert "page_size" in result

    for item in result["items"]:
        assert "content_id" in item
        assert "display_name" in item
        assert "max_score" in item
        assert "neighbor_count" in item
        assert "score_band" in item
        assert "neighbors" in item
        assert len(item["neighbors"]) == item["neighbor_count"]


def test_get_overlap_items_sorted_by_max_score(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    result = get_overlap_items(db.pool, min_score=0.75)
    scores = [item["max_score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)


def test_get_overlap_items_min_score_filters(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    all_items = get_overlap_items(db.pool, min_score=0.75)
    high_items = get_overlap_items(db.pool, min_score=0.90)
    assert high_items["total_items"] <= all_items["total_items"]


def test_get_overlap_items_search_filters_by_name(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    result = get_overlap_items(db.pool, min_score=0.75, search="Item A")
    assert all("Item A" in item["display_name"] for item in result["items"])


def test_get_overlap_items_pagination(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    page1 = get_overlap_items(db.pool, min_score=0.75, page=1, page_size=2)
    assert page1["page"] == 1
    assert page1["page_size"] == 2


def test_get_similar_items_filters_by_relationship_type(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    overlap = get_similar_items(db.pool, "babylon:ns.item-a.prod", min_score=0.75, relationship_type="overlap")
    related = get_similar_items(db.pool, "babylon:ns.item-a.prod", min_score=0.75, relationship_type="related")
    # All seeded items are same-source, so related should be empty
    assert len(overlap) >= 1
    assert len(related) == 0


def test_get_similar_items_all_includes_relationship_type(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    items = get_similar_items(db.pool, "babylon:ns.item-a.prod", min_score=0.75, relationship_type="all")
    assert len(items) >= 1
    assert all("relationship_type" in item for item in items)


def test_get_similar_items_default_min_score_is_085(db):
    """Default min_score should now be 0.85 (matching updated config)."""
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    default_items = get_similar_items(db.pool, "babylon:ns.item-a.prod")
    all_items = get_similar_items(db.pool, "babylon:ns.item-a.prod", min_score=0.75)
    assert len(default_items) <= len(all_items)
