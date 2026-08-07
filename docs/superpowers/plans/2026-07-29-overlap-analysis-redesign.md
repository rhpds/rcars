# Overlap Analysis Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dump-all 8.7MB overlap endpoint with a paginated, item-centric API grouped by score bands, and extract similarity code from the 2,741-line `database.py` into a standalone `db/similarity.py` module.

**Architecture:** Extract 4 similarity functions from the `Database` class into standalone functions that accept `ConnectionPool` as a parameter. Add a `relationship_type` column to `content_similarity` that distinguishes overlap (same-source) from related (cross-source) pairs based on `content_entities.source`. Rewrite the overlap page frontend to show items grouped by score bands instead of flat pair dumps.

**Tech Stack:** Python 3.11 (FastAPI 2.0, psycopg 3, psycopg_pool, pgvector), React 19 (TypeScript, PatternFly 6, Vite)

**Jira:** [RHDPCD-599](https://redhat.atlassian.net/browse/RHDPCD-599)

**Design spec:** `docs/superpowers/specs/2026-07-29-overlap-analysis-redesign-design.md`

## Global Constraints

- Storage threshold remains 0.75 (passed to `compute_content_similarity()`)
- Display default threshold changes to 0.85, near-duplicate boundary to 0.95
- `source` field on `content_entities` is the isolation boundary (same-source = overlap, cross-source = related)
- A pair is either overlap or related, never both — enforced by the existing UNIQUE constraint on `(content_id_a, content_id_b)`
- Cross-source "related" pairs will be empty today (only Babylon has embeddings) — the code handles this gracefully
- The `db/similarity.py` extraction uses standalone functions with `pool: ConnectionPool` parameter — NOT methods on the Database class
- All tests run against a real PostgreSQL+pgvector instance on `localhost:5432/rcars_test`
- Embeddings are `vector(768)` (nomic-embed-text-v1.5)
- No Alembic — schema changes via `SCHEMA_SQL` (CREATE TABLE IF NOT EXISTS) + ALTER TABLE at the end of SCHEMA_SQL

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/api/rcars/db/database.py` | Modify | Remove 4 similarity methods from Database class; add `relationship_type` column + index to SCHEMA_SQL; add ALTER TABLE for existing deployments |
| `src/api/rcars/db/similarity.py` | **Create** | 4 standalone similarity functions: `compute_content_similarity()`, `get_overlap_items()`, `get_similar_items()`, `get_similarity_stats()` |
| `src/api/rcars/db/__init__.py` | Modify | Export similarity functions |
| `src/api/rcars/config.py` | Modify | Update threshold defaults (0.75→0.85, 0.85→0.95) |
| `src/api/rcars/api/routes/admin.py` | Modify | Rewrite overlap endpoint to call `get_overlap_items()` from similarity module; update compute-similarity to call standalone function |
| `src/api/rcars/api/routes/catalog.py` | Modify | Update similar-items endpoint to pass `relationship_type` parameter |
| `src/api/rcars/api/schemas.py` | Modify | New `OverlapItemsResponse` schema; update `SimilarItemsResponse` and `SimilarityThresholds` |
| `src/api/rcars/workers/ops.py` | Modify | Add `compute_content_similarity()` as step 6 in nightly pipeline |
| `src/api/rcars/cli.py` | Modify | Update `compute-similarity` CLI command for relationship types |
| `src/api/tests/test_similarity.py` | **Create** | Tests for all 4 similarity functions |
| `src/frontend/src/pages/ContentAnalysisPage.tsx` | Modify | Rewrite to item-centric score-band layout |
| `src/frontend/src/services/api.ts` | Modify | Update overlap + similar-items API types and calls |
| `src/frontend/src/pages/BrowsePage.tsx` | Modify | Split "Similar Content" into Overlap vs Related subsections |
| `src/frontend/src/pages/SyncPage.tsx` | Modify | Add "Refresh Similarity" action card |

---

### Task 1: Schema + Config + Extract db/similarity.py

**Files:**
- Modify: `src/api/rcars/db/database.py:232-243` (SCHEMA_SQL content_similarity table), `:405-407` (end of SCHEMA_SQL), `:1498-1619` (similarity methods to remove)
- Create: `src/api/rcars/db/similarity.py`
- Modify: `src/api/rcars/db/__init__.py`
- Modify: `src/api/rcars/config.py:86-87` (threshold values)
- Modify: `src/api/rcars/api/routes/admin.py:264-309` (overlap + compute-similarity endpoints)
- Modify: `src/api/rcars/api/routes/catalog.py:229-242` (similar-items endpoint)
- Create: `src/api/tests/test_similarity.py`

**Interfaces:**
- Produces: `compute_content_similarity(pool, threshold, stage) -> dict`, `get_similar_items(pool, content_id, min_score) -> list[dict]`, `get_overlap_report(pool, min_score, stage) -> list[dict]`, `get_similarity_stats(pool, stage) -> dict` — all as standalone functions accepting `ConnectionPool`

This task moves the existing code as-is (no behavior changes yet) into the new module, updates all call sites, and verifies everything still works. Schema and config changes are included because they're required for the new module to compile and tests to pass.

- [ ] **Step 1: Add `relationship_type` column to SCHEMA_SQL**

In `src/api/rcars/db/database.py`, update the `content_similarity` CREATE TABLE (lines 232-243) to include `relationship_type`:

```sql
CREATE TABLE IF NOT EXISTS content_similarity (
    id SERIAL PRIMARY KEY,
    content_id_a TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_id_b TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    similarity_score REAL NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'overlap',
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id_a, content_id_b)
);

CREATE INDEX IF NOT EXISTS idx_content_similarity_a ON content_similarity(content_id_a);
CREATE INDEX IF NOT EXISTS idx_content_similarity_b ON content_similarity(content_id_b);
CREATE INDEX IF NOT EXISTS idx_content_similarity_score ON content_similarity(similarity_score DESC);
CREATE INDEX IF NOT EXISTS idx_content_similarity_reltype ON content_similarity(relationship_type);
```

Then add the ALTER TABLE at the very end of SCHEMA_SQL (before the closing `"""`), after line 406:

```sql
-- ═══════════════════════════════════════════════════════════════════
-- Incremental column additions (safe on existing deployments)
-- ═══════════════════════════════════════════════════════════════════
ALTER TABLE content_similarity ADD COLUMN IF NOT EXISTS relationship_type TEXT NOT NULL DEFAULT 'overlap';
CREATE INDEX IF NOT EXISTS idx_content_similarity_reltype ON content_similarity(relationship_type);
```

- [ ] **Step 2: Update config thresholds**

In `src/api/rcars/config.py`, update lines 86-87:

```python
    # Content overlap
    similarity_threshold: float = 0.85
    similarity_high_threshold: float = 0.95
```

- [ ] **Step 3: Create `src/api/rcars/db/similarity.py` with extracted functions**

This is a direct extraction — same SQL, same logic, but standalone functions accepting `pool: ConnectionPool` instead of methods on `self`. The only addition is the `relationship_type` column in queries.

```python
"""Content similarity computation and queries.

Extracted from database.py to start breaking up the monolith.
All functions accept a psycopg ConnectionPool as their first argument.
"""

from __future__ import annotations

import structlog
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from typing import Any

logger = structlog.get_logger(component="similarity")


def compute_content_similarity(
    pool: ConnectionPool,
    threshold: float = 0.75,
    stage: str = "prod",
) -> dict[str, Any]:
    """Compute pairwise content similarity from summary embeddings.

    All pairs are stored as relationship_type='overlap' (same-source).
    Cross-source 'related' pairs will be added when generalized in Task 2.
    """
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                DELETE FROM content_similarity
                WHERE content_id_a IN (
                    SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s
                )
                """,
                {"stage": stage},
            )

            cur.execute(
                """
                INSERT INTO content_similarity
                    (content_id_a, content_id_b, similarity_score, relationship_type, computed_at)
                SELECT a.content_id, b.content_id,
                       1.0 - (a.embedding <=> b.embedding) AS similarity,
                       'overlap',
                       NOW()
                FROM embeddings a
                JOIN embeddings b ON a.content_id < b.content_id
                JOIN content_entities ce_a ON ce_a.content_id = a.content_id
                JOIN content_entities ce_b ON ce_b.content_id = b.content_id
                JOIN babylon_items bi_a ON bi_a.content_id = a.content_id
                JOIN babylon_items bi_b ON bi_b.content_id = b.content_id
                WHERE a.embed_type = 'summary'
                  AND b.embed_type = 'summary'
                  AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
                  AND bi_a.stage = %(stage)s
                  AND bi_b.stage = %(stage)s
                  AND (bi_a.is_published IS NULL OR bi_a.is_published = FALSE)
                  AND (bi_b.is_published IS NULL OR bi_b.is_published = FALSE)
                  AND ce_a.retired_at IS NULL
                  AND ce_b.retired_at IS NULL
                """,
                {"threshold": threshold, "stage": stage},
            )
            inserted = cur.rowcount
        conn.commit()

    logger.info(
        "content_similarity_computed",
        pairs_stored=inserted,
        threshold=threshold,
        stage=stage,
    )
    return {"pairs_stored": inserted, "threshold": threshold, "stage": stage}


def get_similar_items(
    pool: ConnectionPool,
    content_id: str,
    min_score: float = 0.75,
) -> list[dict[str, Any]]:
    """Return items similar to content_id, ordered by similarity_score DESC."""
    sql = """
        SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.computed_at,
               ce.display_name, bi.category, bi.stage, bi.ci_name, sa.summary
        FROM content_similarity cs
        JOIN content_entities ce ON ce.content_id = CASE
            WHEN cs.content_id_a = %(content_id)s THEN cs.content_id_b
            ELSE cs.content_id_a END
        LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
        LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
        WHERE (cs.content_id_a = %(content_id)s OR cs.content_id_b = %(content_id)s)
          AND cs.similarity_score >= %(min_score)s
        ORDER BY cs.similarity_score DESC
    """
    with pool.connection() as conn:
        cur = conn.execute(sql, {"content_id": content_id, "min_score": min_score})
        rows = cur.fetchall()

    results = []
    for row in rows:
        other_id = row["content_id_b"] if row["content_id_a"] == content_id else row["content_id_a"]
        results.append({
            "content_id": other_id,
            "ci_name": row.get("ci_name"),
            "display_name": row["display_name"],
            "category": row.get("category"),
            "stage": row.get("stage"),
            "summary": row.get("summary"),
            "similarity_score": round(row["similarity_score"], 4),
            "computed_at": row["computed_at"],
        })
    return results


def get_overlap_report(
    pool: ConnectionPool,
    min_score: float = 0.75,
    stage: str | None = None,
) -> list[dict[str, Any]]:
    """Return all similarity pairs above min_score, optionally filtered by stage."""
    sql = """
        SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.computed_at,
               ce_a.display_name AS display_name_a, bi_a.category AS category_a, bi_a.stage AS stage_a,
               bi_a.ci_name AS ci_name_a, sa_a.summary AS summary_a,
               ce_b.display_name AS display_name_b, bi_b.category AS category_b, bi_b.stage AS stage_b,
               bi_b.ci_name AS ci_name_b, sa_b.summary AS summary_b
        FROM content_similarity cs
        JOIN content_entities ce_a ON ce_a.content_id = cs.content_id_a
        JOIN content_entities ce_b ON ce_b.content_id = cs.content_id_b
        LEFT JOIN babylon_items bi_a ON bi_a.content_id = cs.content_id_a
        LEFT JOIN babylon_items bi_b ON bi_b.content_id = cs.content_id_b
        LEFT JOIN showroom_analysis sa_a ON sa_a.content_id = cs.content_id_a
        LEFT JOIN showroom_analysis sa_b ON sa_b.content_id = cs.content_id_b
        WHERE cs.similarity_score >= %(min_score)s
    """
    params: dict[str, Any] = {"min_score": min_score}
    if stage:
        sql += " AND bi_a.stage = %(stage)s AND bi_b.stage = %(stage)s"
        params["stage"] = stage
    sql += " ORDER BY cs.similarity_score DESC"
    with pool.connection() as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall()


def get_similarity_stats(
    pool: ConnectionPool,
    stage: str | None = None,
) -> dict[str, Any]:
    """Return aggregate similarity stats, optionally filtered by stage."""
    stage_filter = ""
    params: dict[str, Any] = {}
    if stage:
        stage_filter = """
            AND cs.content_id_a IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)
            AND cs.content_id_b IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)
        """
        params["stage"] = stage
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE 1=1 {stage_filter}", params)
            total_pairs = cur.fetchone()["count"]
            cur.execute(f"SELECT MAX(cs.computed_at) AS last_computed FROM content_similarity cs WHERE 1=1 {stage_filter}", params)
            last = cur.fetchone()["last_computed"]
            cur.execute(f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE cs.similarity_score >= 0.85 {stage_filter}", params)
            high_overlap = cur.fetchone()["count"]
            cur.execute(f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE cs.similarity_score >= 0.75 AND cs.similarity_score < 0.85 {stage_filter}", params)
            related = cur.fetchone()["count"]
    return {
        "total_pairs": total_pairs,
        "high_overlap": high_overlap,
        "related": related,
        "last_computed": last,
    }
```

- [ ] **Step 4: Remove old methods from Database class**

In `src/api/rcars/db/database.py`, delete the `# ── Content similarity ──` section (lines 1498-1619) — the four methods `compute_content_similarity`, `get_similar_items`, `get_overlap_report`, `get_similarity_stats` and their section comment.

- [ ] **Step 5: Update `src/api/rcars/db/__init__.py`**

```python
from rcars.db.database import Database
from rcars.db.similarity import (
    compute_content_similarity,
    get_overlap_report,
    get_similar_items,
    get_similarity_stats,
)

__all__ = [
    "Database",
    "compute_content_similarity",
    "get_overlap_report",
    "get_similar_items",
    "get_similarity_stats",
]
```

- [ ] **Step 6: Update admin.py call sites**

In `src/api/rcars/api/routes/admin.py`, add the import near the top:

```python
from rcars.db.similarity import compute_content_similarity, get_overlap_report, get_similarity_stats
```

Update the overlap endpoint handler (around line 273) to call standalone functions:

```python
async def overlap_report(
    request: Request,
    user: str = Depends(require_admin),
    min_score: float = Query(0.75, ge=0.0, le=1.0),
    stage: str | None = Query(None, description="Filter by stage: prod, event, or dev"),
):
    db = request.app.state.db
    pairs = get_overlap_report(db.pool, min_score=min_score, stage=stage)
    stats = get_similarity_stats(db.pool, stage=stage)
    settings = Settings()
    return {
        "pairs": pairs,
        "total": len(pairs),
        "stats": stats,
        "thresholds": {
            "related": settings.similarity_threshold,
            "high_overlap": settings.similarity_high_threshold,
        },
    }
```

Update the compute-similarity endpoint handler (around line 299):

```python
async def compute_similarity(
    request: Request,
    user: str = Depends(require_admin),
    threshold: float = Query(0.75, ge=0.0, le=1.0),
    stage: str = Query("prod", description="Stage to compare: prod, event, or dev"),
):
    db = request.app.state.db
    result = compute_content_similarity(db.pool, threshold=threshold, stage=stage)
    return result
```

- [ ] **Step 7: Update catalog.py call site**

In `src/api/rcars/api/routes/catalog.py`, add the import:

```python
from rcars.db.similarity import get_similar_items as db_get_similar_items
```

Update the handler (around line 229) to call the standalone function:

```python
async def get_similar_items(
    identifier: str,
    request: Request,
    user: str = Depends(require_auth),
    min_score: float = Query(0.75, ge=0.0, le=1.0),
):
    db = request.app.state.db
    item = _resolve_item(identifier, db)
    content_id = item["content_id"]
    similar = db_get_similar_items(db.pool, content_id, min_score=min_score)
    return {"ci_name": item.get("ci_name", identifier), "content_id": content_id, "similar": similar, "count": len(similar)}
```

- [ ] **Step 8: Write tests for extracted functions**

Create `src/api/tests/test_similarity.py`:

```python
"""Tests for rcars.db.similarity — standalone similarity functions."""

import os
import psycopg
import pytest
from rcars.db.database import Database
from rcars.db.similarity import (
    compute_content_similarity,
    get_overlap_report,
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
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
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


def test_get_overlap_report_returns_pairs(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    pairs = get_overlap_report(db.pool, min_score=0.75)
    assert len(pairs) >= 1
    for pair in pairs:
        assert pair["similarity_score"] >= 0.75


def test_get_similarity_stats_returns_counts(db):
    compute_content_similarity(db.pool, threshold=0.75, stage="prod")
    stats = get_similarity_stats(db.pool)
    assert stats["total_pairs"] >= 1
    assert "high_overlap" in stats
    assert "related" in stats
    assert stats["last_computed"] is not None
```

- [ ] **Step 9: Run tests to verify extraction is correct**

Run: `cd src/api && python -m pytest tests/test_similarity.py -v`

Expected: All tests pass. The extracted functions behave identically to the old Database methods.

- [ ] **Step 10: Run full test suite to verify no regressions**

Run: `cd src/api && python -m pytest tests/ -v -m "not integration"`

Expected: All existing tests still pass. No imports break.

- [ ] **Step 11: Commit**

```bash
git add src/api/rcars/db/similarity.py src/api/rcars/db/__init__.py \
       src/api/rcars/db/database.py src/api/rcars/config.py \
       src/api/rcars/api/routes/admin.py src/api/rcars/api/routes/catalog.py \
       src/api/tests/test_similarity.py
git commit -m "[RHDPCD-599] Extract similarity code into db/similarity.py module

    - Create standalone functions (compute, get_similar, overlap_report, stats)
    - Remove old Database class methods, update all route call sites
    - Add relationship_type column + index to content_similarity table
    - Update config thresholds: display default 0.85, near-duplicate 0.95
    - Add test suite for similarity functions"
```

---

### Task 2: Generalize Similarity Computation

**Files:**
- Modify: `src/api/rcars/db/similarity.py` — rewrite `compute_content_similarity()` and `get_similarity_stats()`
- Modify: `src/api/tests/test_similarity.py` — add tests for overlap vs related pair generation and band-based stats

**Interfaces:**
- Consumes: `compute_content_similarity(pool, threshold, stage)` from Task 1
- Produces: `compute_content_similarity(pool, threshold, stage) -> dict` — now returns `{"overlap_pairs": int, "related_pairs": int, "threshold": float, "stage": str}`; `get_similarity_stats(pool, relationship_type, stage) -> dict` — now accepts optional `relationship_type` filter and returns band breakdowns

- [ ] **Step 1: Write failing tests for generalized compute**

Add to `src/api/tests/test_similarity.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_similarity.py::test_compute_returns_overlap_and_related_counts tests/test_similarity.py::test_compute_cross_source_marked_as_related -v`

Expected: FAIL — current compute doesn't return `overlap_pairs`/`related_pairs` keys, and doesn't handle cross-source items.

- [ ] **Step 3: Rewrite `compute_content_similarity()` in similarity.py**

Replace the function body with the generalized version that computes overlap and related pairs separately:

```python
def compute_content_similarity(
    pool: ConnectionPool,
    threshold: float = 0.75,
    stage: str | None = None,
) -> dict[str, Any]:
    """Compute pairwise content similarity from summary embeddings.

    - Overlap pairs: same source (e.g., Babylon↔Babylon)
    - Related pairs: different sources (e.g., Babylon↔portfolio_arch)
    """
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Clear existing pairs. If stage is specified, only clear Babylon items
            # in that stage. Otherwise clear all.
            if stage:
                cur.execute(
                    """
                    DELETE FROM content_similarity
                    WHERE content_id_a IN (
                        SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s
                    ) OR content_id_b IN (
                        SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s
                    )
                    """,
                    {"stage": stage},
                )
            else:
                cur.execute("DELETE FROM content_similarity")

            # Overlap pairs — same source
            babylon_stage_filter = ""
            if stage:
                babylon_stage_filter = """
                    AND (bi_a.content_id IS NULL OR bi_a.stage = %(stage)s)
                    AND (bi_b.content_id IS NULL OR bi_b.stage = %(stage)s)
                """

            cur.execute(
                f"""
                INSERT INTO content_similarity
                    (content_id_a, content_id_b, similarity_score, relationship_type, computed_at)
                SELECT a.content_id, b.content_id,
                       1.0 - (a.embedding <=> b.embedding),
                       'overlap',
                       NOW()
                FROM embeddings a
                JOIN embeddings b ON a.content_id < b.content_id
                JOIN content_entities ce_a ON ce_a.content_id = a.content_id
                JOIN content_entities ce_b ON ce_b.content_id = b.content_id
                LEFT JOIN babylon_items bi_a ON bi_a.content_id = a.content_id
                LEFT JOIN babylon_items bi_b ON bi_b.content_id = b.content_id
                WHERE a.embed_type = 'summary'
                  AND b.embed_type = 'summary'
                  AND ce_a.source = ce_b.source
                  AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
                  AND ce_a.retired_at IS NULL
                  AND ce_b.retired_at IS NULL
                  AND (bi_a.content_id IS NULL OR (bi_a.is_published IS NULL OR bi_a.is_published = FALSE))
                  AND (bi_b.content_id IS NULL OR (bi_b.is_published IS NULL OR bi_b.is_published = FALSE))
                  {babylon_stage_filter}
                """,
                {"threshold": threshold, "stage": stage},
            )
            overlap_count = cur.rowcount

            # Related pairs — different sources
            cur.execute(
                """
                INSERT INTO content_similarity
                    (content_id_a, content_id_b, similarity_score, relationship_type, computed_at)
                SELECT a.content_id, b.content_id,
                       1.0 - (a.embedding <=> b.embedding),
                       'related',
                       NOW()
                FROM embeddings a
                JOIN embeddings b ON a.content_id < b.content_id
                JOIN content_entities ce_a ON ce_a.content_id = a.content_id
                JOIN content_entities ce_b ON ce_b.content_id = b.content_id
                WHERE a.embed_type = 'summary'
                  AND b.embed_type = 'summary'
                  AND ce_a.source != ce_b.source
                  AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
                  AND ce_a.retired_at IS NULL
                  AND ce_b.retired_at IS NULL
                ON CONFLICT (content_id_a, content_id_b) DO UPDATE
                  SET similarity_score = EXCLUDED.similarity_score,
                      relationship_type = EXCLUDED.relationship_type,
                      computed_at = EXCLUDED.computed_at
                """,
                {"threshold": threshold},
            )
            related_count = cur.rowcount
        conn.commit()

    logger.info(
        "content_similarity_computed",
        overlap_pairs=overlap_count,
        related_pairs=related_count,
        threshold=threshold,
        stage=stage,
    )
    return {
        "overlap_pairs": overlap_count,
        "related_pairs": related_count,
        "pairs_stored": overlap_count + related_count,
        "threshold": threshold,
        "stage": stage,
    }
```

- [ ] **Step 4: Write failing tests for updated stats**

Add to `src/api/tests/test_similarity.py`:

```python
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
```

- [ ] **Step 5: Rewrite `get_similarity_stats()` with band breakdowns**

```python
def get_similarity_stats(
    pool: ConnectionPool,
    stage: str | None = None,
    relationship_type: str | None = None,
) -> dict[str, Any]:
    """Return aggregate similarity stats with score-band breakdowns."""
    filters = ["1=1"]
    params: dict[str, Any] = {}

    if stage:
        filters.append(
            "cs.content_id_a IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)"
        )
        filters.append(
            "cs.content_id_b IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)"
        )
        params["stage"] = stage

    if relationship_type:
        filters.append("cs.relationship_type = %(relationship_type)s")
        params["relationship_type"] = relationship_type

    where = " AND ".join(filters)

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE {where}",
                params,
            )
            total = cur.fetchone()["count"]

            cur.execute(
                f"SELECT MAX(cs.computed_at) AS last_computed FROM content_similarity cs WHERE {where}",
                params,
            )
            last = cur.fetchone()["last_computed"]

            cur.execute(
                f"""SELECT COUNT(*) AS count FROM content_similarity cs
                    WHERE {where} AND cs.relationship_type = 'overlap' AND cs.similarity_score >= 0.95""",
                params,
            )
            near_duplicates = cur.fetchone()["count"]

            cur.execute(
                f"""SELECT COUNT(*) AS count FROM content_similarity cs
                    WHERE {where} AND cs.relationship_type = 'overlap'
                    AND cs.similarity_score >= 0.85 AND cs.similarity_score < 0.95""",
                params,
            )
            high_overlap = cur.fetchone()["count"]

            cur.execute(
                f"""SELECT COUNT(*) AS count FROM content_similarity cs
                    WHERE {where} AND cs.similarity_score >= 0.75 AND cs.similarity_score < 0.85""",
                params,
            )
            related_band = cur.fetchone()["count"]

    return {
        "near_duplicates": near_duplicates,
        "high_overlap": high_overlap,
        "related_band": related_band,
        "total_pairs_stored": total,
        "last_computed": last,
    }
```

- [ ] **Step 6: Update admin.py to handle new return shape**

Update the overlap endpoint in `admin.py` to pass the new stats keys in the response. Update the `SimilarityThresholds` schema in `schemas.py`:

In `src/api/rcars/api/schemas.py`, update:
```python
class SimilarityThresholds(BaseModel):
    display: float
    near_duplicate: float
```

Update the overlap endpoint response construction in `admin.py`:
```python
    return {
        "pairs": pairs,
        "total": len(pairs),
        "stats": stats,
        "thresholds": {
            "display": settings.similarity_threshold,
            "near_duplicate": settings.similarity_high_threshold,
        },
    }
```

- [ ] **Step 7: Run tests**

Run: `cd src/api && python -m pytest tests/test_similarity.py -v`

Expected: All tests pass including the new generalization tests.

- [ ] **Step 8: Commit**

```bash
git add src/api/rcars/db/similarity.py src/api/tests/test_similarity.py \
       src/api/rcars/api/routes/admin.py src/api/rcars/api/schemas.py
git commit -m "[RHDPCD-599] Generalize similarity computation for overlap vs related pairs

    - Overlap pairs: same source, filtered by babylon stage/published
    - Related pairs: cross-source, ready for portfolio architectures
    - Stats now return band breakdowns (near-duplicate, high overlap, related)
    - SimilarityThresholds schema updated to display/near_duplicate"
```

---

### Task 3: Item-Centric Paginated Overlap API

**Files:**
- Modify: `src/api/rcars/db/similarity.py` — add `get_overlap_items()`, remove `get_overlap_report()`
- Modify: `src/api/rcars/api/routes/admin.py` — rewrite overlap endpoint
- Modify: `src/api/rcars/api/schemas.py` — new `OverlapItemsResponse` schema
- Modify: `src/api/rcars/db/__init__.py` — update exports
- Modify: `src/api/tests/test_similarity.py` — tests for new function

**Interfaces:**
- Consumes: `compute_content_similarity()` from Task 2 (to seed test data), `get_similarity_stats()` from Task 2
- Produces: `get_overlap_items(pool, min_score, stage, content_type, source, search, page, page_size, relationship_type) -> dict` — returns `{"items": [...], "total_items": int, "page": int, "page_size": int, "stats": dict, "thresholds": dict}`

- [ ] **Step 1: Write failing test for `get_overlap_items()`**

Add to `src/api/tests/test_similarity.py`:

```python
from rcars.db.similarity import get_overlap_items


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_similarity.py::test_get_overlap_items_returns_item_centric_results -v`

Expected: FAIL — `get_overlap_items` does not exist yet.

- [ ] **Step 3: Implement `get_overlap_items()` in similarity.py**

Add the new function and a helper for score banding:

```python
def _score_band(score: float) -> str:
    if score >= 0.95:
        return "near_duplicate"
    elif score >= 0.85:
        return "high_overlap"
    else:
        return "related"


def get_overlap_items(
    pool: ConnectionPool,
    min_score: float = 0.85,
    stage: str | None = None,
    content_type: str | None = None,
    source: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 100,
    relationship_type: str = "overlap",
) -> dict[str, Any]:
    """Return item-centric overlap data, grouped by score bands.

    Each item includes its max similarity score, neighbor count, score band,
    and the full list of neighbors with their individual scores.
    """
    offset = (page - 1) * page_size

    # Build optional filters for the item-level query
    item_filters = []
    params: dict[str, Any] = {
        "min_score": min_score,
        "relationship_type": relationship_type,
        "page_size": page_size,
        "offset": offset,
    }

    if stage:
        item_filters.append("bi.stage = %(stage)s")
        params["stage"] = stage
    if content_type:
        item_filters.append("ce.content_type = %(content_type)s")
        params["content_type"] = content_type
    if source:
        item_filters.append("ce.source = %(source)s")
        params["source"] = source
    if search:
        item_filters.append("ce.display_name ILIKE %(search)s")
        params["search"] = f"%{search}%"

    item_where = (" AND " + " AND ".join(item_filters)) if item_filters else ""

    # Step 1: Get items with their max score and neighbor count
    items_sql = f"""
        WITH all_sides AS (
            SELECT content_id_a AS content_id, similarity_score
            FROM content_similarity
            WHERE similarity_score >= %(min_score)s AND relationship_type = %(relationship_type)s
            UNION ALL
            SELECT content_id_b AS content_id, similarity_score
            FROM content_similarity
            WHERE similarity_score >= %(min_score)s AND relationship_type = %(relationship_type)s
        ),
        item_scores AS (
            SELECT als.content_id,
                   MAX(als.similarity_score) AS max_score,
                   COUNT(*) AS neighbor_count
            FROM all_sides als
            JOIN content_entities ce ON ce.content_id = als.content_id
            LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
            WHERE 1=1 {item_where}
            GROUP BY als.content_id
        )
        SELECT COUNT(*) OVER() AS total_count,
               isc.content_id, isc.max_score, isc.neighbor_count,
               ce.display_name, ce.content_type, ce.source,
               bi.category, bi.stage
        FROM item_scores isc
        JOIN content_entities ce ON ce.content_id = isc.content_id
        LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
        ORDER BY isc.max_score DESC, isc.neighbor_count DESC
        LIMIT %(page_size)s OFFSET %(offset)s
    """

    with pool.connection() as conn:
        cur = conn.execute(items_sql, params)
        item_rows = cur.fetchall()

    if not item_rows:
        return {
            "items": [],
            "total_items": 0,
            "page": page,
            "page_size": page_size,
        }

    total_items = item_rows[0]["total_count"]
    content_ids = [row["content_id"] for row in item_rows]

    # Step 2: Get all neighbors for items on this page
    neighbors_sql = """
        SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score,
               ce.display_name, ce.content_type, ce.source,
               bi.category, bi.stage
        FROM content_similarity cs
        JOIN content_entities ce ON ce.content_id = CASE
            WHEN cs.content_id_a = ANY(%(content_ids)s) THEN cs.content_id_b
            ELSE cs.content_id_a END
        LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
        WHERE (cs.content_id_a = ANY(%(content_ids)s) OR cs.content_id_b = ANY(%(content_ids)s))
          AND cs.similarity_score >= %(min_score)s
          AND cs.relationship_type = %(relationship_type)s
        ORDER BY cs.similarity_score DESC
    """
    with pool.connection() as conn:
        cur = conn.execute(
            neighbors_sql,
            {"content_ids": content_ids, "min_score": min_score, "relationship_type": relationship_type},
        )
        neighbor_rows = cur.fetchall()

    # Group neighbors by item
    neighbors_by_item: dict[str, list[dict]] = {cid: [] for cid in content_ids}
    for row in neighbor_rows:
        if row["content_id_a"] in neighbors_by_item:
            item_id = row["content_id_a"]
            other_id = row["content_id_b"]
        else:
            item_id = row["content_id_b"]
            other_id = row["content_id_a"]
        neighbors_by_item[item_id].append({
            "content_id": other_id,
            "display_name": row["display_name"],
            "content_type": row["content_type"],
            "source": row["source"],
            "category": row.get("category"),
            "stage": row.get("stage"),
            "similarity_score": round(row["similarity_score"], 4),
        })

    items = []
    for row in item_rows:
        cid = row["content_id"]
        items.append({
            "content_id": cid,
            "display_name": row["display_name"],
            "content_type": row["content_type"],
            "source": row["source"],
            "category": row.get("category"),
            "stage": row.get("stage"),
            "max_score": round(row["max_score"], 4),
            "neighbor_count": len(neighbors_by_item.get(cid, [])),
            "score_band": _score_band(row["max_score"]),
            "neighbors": neighbors_by_item.get(cid, []),
        })

    return {
        "items": items,
        "total_items": total_items,
        "page": page,
        "page_size": page_size,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_similarity.py -k "overlap_items" -v`

Expected: All `get_overlap_items` tests pass.

- [ ] **Step 5: Remove `get_overlap_report()` from similarity.py and update exports**

Delete the `get_overlap_report()` function from `src/api/rcars/db/similarity.py`.

Update `src/api/rcars/db/__init__.py` — replace `get_overlap_report` with `get_overlap_items`:

```python
from rcars.db.database import Database
from rcars.db.similarity import (
    compute_content_similarity,
    get_overlap_items,
    get_similar_items,
    get_similarity_stats,
)

__all__ = [
    "Database",
    "compute_content_similarity",
    "get_overlap_items",
    "get_similar_items",
    "get_similarity_stats",
]
```

- [ ] **Step 6: Update response schema and admin endpoint**

In `src/api/rcars/api/schemas.py`, replace `OverlapResponse` with:

```python
class OverlapItemsResponse(BaseModel):
    items: list[dict]
    total_items: int
    page: int
    page_size: int
    stats: dict | None = None
    thresholds: SimilarityThresholds
```

In `src/api/rcars/api/routes/admin.py`, rewrite the overlap endpoint import and handler:

```python
from rcars.db.similarity import compute_content_similarity, get_overlap_items, get_similarity_stats
```

```python
@router.get(
    "/overlap",
    summary="Content overlap report — item-centric, paginated",
    description=(
        "Returns catalog items grouped by their maximum similarity score, "
        "with neighbor lists for each item. Supports filtering by score, stage, "
        "content type, source, and search."
    ),
    response_model=OverlapItemsResponse,
)
async def overlap_report(
    request: Request,
    user: str = Depends(require_admin),
    min_score: float = Query(0.85, ge=0.0, le=1.0),
    stage: str | None = Query(None, description="Filter by stage"),
    content_type: str | None = Query(None, description="Filter by content type"),
    source: str | None = Query(None, description="Filter by source"),
    search: str | None = Query(None, description="Search by display name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    relationship_type: str = Query("overlap", description="overlap or related"),
):
    db = request.app.state.db
    result = get_overlap_items(
        db.pool,
        min_score=min_score,
        stage=stage,
        content_type=content_type,
        source=source,
        search=search,
        page=page,
        page_size=page_size,
        relationship_type=relationship_type,
    )
    stats = get_similarity_stats(db.pool, stage=stage, relationship_type=relationship_type)
    settings = Settings()
    return {
        **result,
        "stats": stats,
        "thresholds": {
            "display": settings.similarity_threshold,
            "near_duplicate": settings.similarity_high_threshold,
        },
    }
```

- [ ] **Step 7: Remove old test for `get_overlap_report()`**

Remove `test_get_overlap_report_returns_pairs` from `test_similarity.py` and remove `get_overlap_report` from the import.

- [ ] **Step 8: Run full test suite**

Run: `cd src/api && python -m pytest tests/ -v -m "not integration"`

Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/api/rcars/db/similarity.py src/api/rcars/db/__init__.py \
       src/api/rcars/api/routes/admin.py src/api/rcars/api/schemas.py \
       src/api/tests/test_similarity.py
git commit -m "[RHDPCD-599] Add item-centric paginated overlap API

    - New get_overlap_items() groups pairs by item with score bands
    - Replaces dump-all get_overlap_report() that returned 8.7MB
    - Supports pagination, filtering by stage/type/source/search
    - Response includes neighbors per item, max_score, score_band"
```

---

### Task 4: Similar Items Relationship Type Filter

**Files:**
- Modify: `src/api/rcars/db/similarity.py` — update `get_similar_items()` signature
- Modify: `src/api/rcars/api/routes/catalog.py` — add `relationship_type` query parameter
- Modify: `src/api/rcars/api/schemas.py` — update `SimilarItemsResponse`
- Modify: `src/api/tests/test_similarity.py` — add tests

**Interfaces:**
- Consumes: `get_similar_items(pool, content_id, min_score)` from Task 1
- Produces: `get_similar_items(pool, content_id, min_score, relationship_type) -> list[dict]` — each result now includes `relationship_type` field when `relationship_type='all'`

- [ ] **Step 1: Write failing tests**

Add to `src/api/tests/test_similarity.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_similarity.py::test_get_similar_items_filters_by_relationship_type -v`

Expected: FAIL — `relationship_type` parameter not accepted yet.

- [ ] **Step 3: Update `get_similar_items()` in similarity.py**

```python
def get_similar_items(
    pool: ConnectionPool,
    content_id: str,
    min_score: float = 0.85,
    relationship_type: str = "overlap",
) -> list[dict[str, Any]]:
    """Return items similar to content_id, ordered by similarity_score DESC.

    relationship_type: 'overlap' (default), 'related', or 'all'.
    When 'all', each result includes 'relationship_type' field.
    """
    rel_filter = ""
    if relationship_type != "all":
        rel_filter = "AND cs.relationship_type = %(relationship_type)s"

    sql = f"""
        SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.computed_at,
               cs.relationship_type,
               ce.display_name, ce.content_type, ce.source,
               bi.category, bi.stage, bi.ci_name, sa.summary
        FROM content_similarity cs
        JOIN content_entities ce ON ce.content_id = CASE
            WHEN cs.content_id_a = %(content_id)s THEN cs.content_id_b
            ELSE cs.content_id_a END
        LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
        LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
        WHERE (cs.content_id_a = %(content_id)s OR cs.content_id_b = %(content_id)s)
          AND cs.similarity_score >= %(min_score)s
          {rel_filter}
        ORDER BY cs.similarity_score DESC
    """
    params = {"content_id": content_id, "min_score": min_score, "relationship_type": relationship_type}

    with pool.connection() as conn:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()

    results = []
    for row in rows:
        other_id = row["content_id_b"] if row["content_id_a"] == content_id else row["content_id_a"]
        item = {
            "content_id": other_id,
            "ci_name": row.get("ci_name"),
            "display_name": row["display_name"],
            "content_type": row.get("content_type"),
            "source": row.get("source"),
            "category": row.get("category"),
            "stage": row.get("stage"),
            "summary": row.get("summary"),
            "similarity_score": round(row["similarity_score"], 4),
            "computed_at": row["computed_at"],
        }
        if relationship_type == "all":
            item["relationship_type"] = row["relationship_type"]
        results.append(item)
    return results
```

- [ ] **Step 4: Update catalog.py endpoint**

In `src/api/rcars/api/routes/catalog.py`, update the handler:

```python
async def get_similar_items(
    identifier: str,
    request: Request,
    user: str = Depends(require_auth),
    min_score: float = Query(0.85, ge=0.0, le=1.0),
    relationship_type: str = Query("overlap", description="overlap, related, or all"),
):
    db = request.app.state.db
    item = _resolve_item(identifier, db)
    content_id = item["content_id"]
    similar = db_get_similar_items(db.pool, content_id, min_score=min_score, relationship_type=relationship_type)
    return {"ci_name": item.get("ci_name", identifier), "content_id": content_id, "similar": similar, "count": len(similar)}
```

- [ ] **Step 5: Update SimilarItemsResponse schema**

In `src/api/rcars/api/schemas.py`:

```python
class SimilarItemsResponse(BaseModel):
    ci_name: str
    content_id: str
    similar: list[dict]
    count: int
```

- [ ] **Step 6: Run tests**

Run: `cd src/api && python -m pytest tests/test_similarity.py -v`

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/db/similarity.py src/api/rcars/api/routes/catalog.py \
       src/api/rcars/api/schemas.py src/api/tests/test_similarity.py
git commit -m "[RHDPCD-599] Add relationship_type filter to similar items endpoint

    - get_similar_items() accepts 'overlap', 'related', or 'all'
    - Default min_score raised to 0.85 (matching display threshold)
    - Each result includes content_type, source fields
    - 'all' mode includes relationship_type per result"
```

---

### Task 5: Pipeline + CLI Integration

**Files:**
- Modify: `src/api/rcars/workers/ops.py:436-438` — add step 6 to nightly pipeline
- Modify: `src/api/rcars/cli.py:357-375` — update compute-similarity command
- Modify: `src/api/tests/test_similarity.py` — add pipeline integration test

**Interfaces:**
- Consumes: `compute_content_similarity(pool, threshold, stage)` from Task 2
- Produces: Nightly pipeline runs similarity as final step; CLI outputs band breakdowns

- [ ] **Step 1: Add similarity computation to nightly pipeline**

In `src/api/rcars/workers/ops.py`, add the import near the top:

```python
from rcars.db.similarity import compute_content_similarity
```

Insert a new step block between the cleanup section (line 436) and the result assembly (line 438). Follow the same try/except + publish_progress pattern as other steps:

```python
        # ── Step 6: Compute content similarity ──
        similarity_result = {"status": "skipped"}
        try:
            publish_progress(
                wctx.arq_redis, job_id, pipeline_channel,
                "Computing content similarity...",
            )
            similarity_result = await asyncio.to_thread(
                compute_content_similarity,
                wctx.db.pool,
                threshold=0.75,
            )
            similarity_result["status"] = "complete"
            publish_progress(
                wctx.arq_redis, job_id, pipeline_channel,
                f"Content similarity computed: {similarity_result.get('pairs_stored', 0)} pairs stored",
            )
        except Exception as exc:
            logger.exception("content_similarity_failed")
            similarity_result = {"status": "error", "error": str(exc)}
            publish_progress(
                wctx.arq_redis, job_id, pipeline_channel,
                "Content similarity computation failed (non-fatal)",
            )
```

Add `"similarity": similarity_result` to the result dict that's assembled on the next line.

Note: `compute_content_similarity` is called with `stage=None` (no stage filter) to compute pairs across all stages. The storage threshold 0.75 is used.

- [ ] **Step 2: Update CLI command**

In `src/api/rcars/cli.py`, update the compute-similarity command (around line 357):

```python
@cli.command("compute-similarity")
@click.option("--threshold", "-t", default=0.75, type=float, help="Minimum similarity score to store")
@click.option("--stage", "-s", default=None, type=click.Choice(["prod", "event", "dev"]), help="Stage filter (Babylon only). Omit for all stages.")
def compute_similarity_cmd(threshold: float, stage: str | None):
    """Compute pairwise content similarity (overlap + related pairs)."""
    from rcars.db.similarity import compute_content_similarity, get_similarity_stats

    db = _get_db()
    result = compute_content_similarity(db.pool, threshold=threshold, stage=stage)

    click.echo(f"\nComputed similarity (threshold={threshold}, stage={stage or 'all'}):")
    click.echo(f"  Overlap pairs:  {result['overlap_pairs']}")
    click.echo(f"  Related pairs:  {result['related_pairs']}")
    click.echo(f"  Total stored:   {result['pairs_stored']}")

    stats = get_similarity_stats(db.pool)
    click.echo(f"\nScore band breakdown:")
    click.echo(f"  Near-duplicates (>=0.95):  {stats['near_duplicates']}")
    click.echo(f"  High overlap (0.85-0.94):  {stats['high_overlap']}")
    click.echo(f"  Related band (0.75-0.84):  {stats['related_band']}")
    click.echo(f"  Total pairs stored:        {stats['total_pairs_stored']}")
    if stats['last_computed']:
        click.echo(f"  Last computed:             {stats['last_computed']}")

    db.close()
```

- [ ] **Step 3: Run tests**

Run: `cd src/api && python -m pytest tests/ -v -m "not integration"`

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/api/rcars/workers/ops.py src/api/rcars/cli.py
git commit -m "[RHDPCD-599] Add similarity computation to nightly pipeline and update CLI

    - Pipeline step 6: compute_content_similarity() runs after all embeddings current
    - Computes both overlap and related pairs in one pass (threshold=0.75)
    - CLI updated: no stage filter = all stages, output shows band breakdown"
```

---

### Task 6: Frontend — Overlap Report Page Rewrite

**Files:**
- Modify: `src/frontend/src/services/api.ts:189-211` — update API types and functions
- Modify: `src/frontend/src/pages/ContentAnalysisPage.tsx` — full rewrite

**Interfaces:**
- Consumes: `GET /api/v1/admin/overlap` item-centric response from Task 3
- Produces: Rewritten overlap page with score-band sections, filters, and expandable item rows

- [ ] **Step 1: Update API service types and functions**

In `src/frontend/src/services/api.ts`, replace the overlap-related functions (around lines 189-211):

```typescript
  // Content similarity / overlap
  getSimilarItems: (identifier: string, minScore = 0.85, relationshipType = 'overlap') =>
    request<{
      ci_name: string
      content_id: string
      similar: Array<{
        content_id: string; ci_name: string | null; display_name: string
        content_type: string; source: string; category: string; stage: string
        summary: string | null; similarity_score: number; computed_at: string
        relationship_type?: string
      }>
      count: number
    }>(`/catalog/${encodeURIComponent(identifier)}/similar?min_score=${minScore}&relationship_type=${relationshipType}`),

  getOverlapReport: (minScore = 0.85, stage?: string, search?: string, relationshipType = 'overlap') =>
    request<{
      items: Array<{
        content_id: string; display_name: string; content_type: string; source: string
        category: string | null; stage: string | null; max_score: number
        neighbor_count: number; score_band: string
        neighbors: Array<{
          content_id: string; display_name: string; content_type: string
          source: string; category: string | null; stage: string | null
          similarity_score: number
        }>
      }>
      total_items: number; page: number; page_size: number
      stats: {
        near_duplicates: number; high_overlap: number; related_band: number
        total_pairs_stored: number; last_computed: string | null
      }
      thresholds: { display: number; near_duplicate: number }
    }>(`/admin/overlap?min_score=${minScore}${stage ? `&stage=${stage}` : ''}${search ? `&search=${encodeURIComponent(search)}` : ''}&relationship_type=${relationshipType}`),

  computeSimilarity: (threshold = 0.75, stage?: string) =>
    request<{ overlap_pairs: number; related_pairs: number; pairs_stored: number; threshold: number; stage: string }>(
      `/admin/compute-similarity?threshold=${threshold}${stage ? `&stage=${stage}` : ''}`, { method: 'POST' }),
```

- [ ] **Step 2: Rewrite ContentAnalysisPage.tsx**

Replace the entire contents of `src/frontend/src/pages/ContentAnalysisPage.tsx` with the item-centric, score-band layout. Key structural changes from the current pair-centric layout:

- **State:** Replace `pairs: OverlapPair[]` with `items` from the API response. Add `expandedItems` set (replacing `expandedPairs`). Keep `loading`, `computing`, `stage`, `search`.
- **Stats bar:** Three cards — Near-Duplicates (red), High Overlap (amber), Related Band (shown when threshold < 0.85).
- **Filter bar:** Min score input (default 0.85), stage dropdown, search input, "Compute Similarity" button.
- **Score-band sections:** Three collapsible `<details>` sections filtering items by `score_band`. Near-Duplicates (0.95+) open by default, High Overlap (0.85-0.94) open by default, Related (0.75-0.84) collapsed by default.
- **Item rows:** Each row shows display_name, content_type badge, category, stage badge, neighbor count badge, max score badge (color-coded). Click to expand shows neighbor list with individual scores and links to browse card.

```tsx
import { useState, useCallback, useEffect } from 'react'
import { Badge, Button, SearchInput, FormSelect, FormSelectOption, Spinner } from '@patternfly/react-core'
import api from '../services/api'

interface OverlapItem {
  content_id: string
  display_name: string
  content_type: string
  source: string
  category: string | null
  stage: string | null
  max_score: number
  neighbor_count: number
  score_band: string
  neighbors: Array<{
    content_id: string
    display_name: string
    content_type: string
    source: string
    category: string | null
    stage: string | null
    similarity_score: number
  }>
}

interface OverlapStats {
  near_duplicates: number
  high_overlap: number
  related_band: number
  total_pairs_stored: number
  last_computed: string | null
}

export function ContentOverlapPage() {
  const [items, setItems] = useState<OverlapItem[]>([])
  const [stats, setStats] = useState<OverlapStats | null>(null)
  const [thresholds, setThresholds] = useState({ display: 0.85, near_duplicate: 0.95 })
  const [loading, setLoading] = useState(true)
  const [computing, setComputing] = useState(false)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [minScore, setMinScore] = useState(0.85)
  const [stage, setStage] = useState<string>('')
  const [search, setSearch] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getOverlapReport(
        minScore,
        stage || undefined,
        search || undefined,
      )
      setItems(data.items)
      setStats(data.stats)
      setThresholds(data.thresholds)
    } finally {
      setLoading(false)
    }
  }, [minScore, stage, search])

  useEffect(() => { loadData() }, [loadData])

  const handleCompute = async () => {
    setComputing(true)
    try {
      await api.computeSimilarity(0.75, stage || undefined)
      await loadData()
    } finally {
      setComputing(false)
    }
  }

  const toggleExpand = (contentId: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      if (next.has(contentId)) next.delete(contentId)
      else next.add(contentId)
      return next
    })
  }

  const scoreColor = (score: number) =>
    score >= thresholds.near_duplicate ? 'var(--score-red)' : 'var(--score-amber)'
  const scoreBg = (score: number) =>
    score >= thresholds.near_duplicate ? 'var(--score-red-bg)' : 'var(--score-amber-bg)'
  const scorePct = (score: number) => `${Math.round(score * 100)}%`

  const bandItems = (band: string) => items.filter(i => i.score_band === band)
  const nearDupes = bandItems('near_duplicate')
  const highOverlap = bandItems('high_overlap')
  const relatedBand = bandItems('related')

  return (
    <div className="ca-page">
      <div className="ca-header">
        <h1>Content Overlap Detection</h1>
        <p className="ca-subtitle">
          {stats?.last_computed
            ? `Last computed ${new Date(stats.last_computed).toLocaleString()}`
            : 'Not yet computed'}
          {' · '}Items with similarity ≥ {scorePct(minScore)}
        </p>
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="ca-stats-grid">
          <div className="ca-stat-card ca-stat-red">
            <div className="ca-stat-value">{stats.near_duplicates}</div>
            <div className="ca-stat-label">Near-Duplicates</div>
            <div className="ca-stat-desc">≥ {scorePct(thresholds.near_duplicate)}</div>
          </div>
          <div className="ca-stat-card ca-stat-amber">
            <div className="ca-stat-value">{stats.high_overlap}</div>
            <div className="ca-stat-label">High Overlap</div>
            <div className="ca-stat-desc">{scorePct(thresholds.display)}–{scorePct(thresholds.near_duplicate - 0.01)}</div>
          </div>
          <div className="ca-stat-card ca-stat-blue">
            <div className="ca-stat-value">{stats.total_pairs_stored}</div>
            <div className="ca-stat-label">Total Pairs Stored</div>
            <div className="ca-stat-desc">≥ 75%</div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="ca-controls">
        <FormSelect value={stage} onChange={(_e, v) => setStage(v)} aria-label="Stage filter">
          <FormSelectOption value="" label="All stages" />
          <FormSelectOption value="prod" label="prod" />
          <FormSelectOption value="event" label="event" />
          <FormSelectOption value="dev" label="dev" />
        </FormSelect>

        <FormSelect
          value={String(minScore)}
          onChange={(_e, v) => setMinScore(parseFloat(v))}
          aria-label="Min score"
        >
          <FormSelectOption value="0.95" label="≥ 95% (near-duplicates)" />
          <FormSelectOption value="0.85" label="≥ 85% (high overlap)" />
          <FormSelectOption value="0.75" label="≥ 75% (all stored)" />
        </FormSelect>

        <SearchInput
          placeholder="Search by name…"
          value={search}
          onChange={(_e, v) => setSearch(v)}
          onClear={() => setSearch('')}
        />

        <Button
          variant="secondary"
          size="sm"
          isLoading={computing}
          onClick={handleCompute}
        >
          {computing ? 'Computing…' : 'Refresh Similarity'}
        </Button>
      </div>

      {loading ? (
        <div className="ca-loading"><Spinner size="lg" /> Loading overlap data…</div>
      ) : (
        <div className="ca-band-sections">
          {/* Near-Duplicates */}
          {nearDupes.length > 0 && (
            <details open className="ca-band-section">
              <summary className="ca-band-header ca-band-red">
                Near-Duplicates ({nearDupes.length}) · ≥ {scorePct(thresholds.near_duplicate)}
              </summary>
              {nearDupes.map(item => renderItem(item, expandedItems, toggleExpand, scoreColor, scoreBg, scorePct))}
            </details>
          )}

          {/* High Overlap */}
          {highOverlap.length > 0 && (
            <details open className="ca-band-section">
              <summary className="ca-band-header ca-band-amber">
                High Overlap ({highOverlap.length}) · {scorePct(thresholds.display)}–{scorePct(thresholds.near_duplicate - 0.01)}
              </summary>
              {highOverlap.map(item => renderItem(item, expandedItems, toggleExpand, scoreColor, scoreBg, scorePct))}
            </details>
          )}

          {/* Related band — only when threshold < 0.85 */}
          {relatedBand.length > 0 && (
            <details className="ca-band-section">
              <summary className="ca-band-header ca-band-muted">
                Related ({relatedBand.length}) · 75%–84%
              </summary>
              {relatedBand.map(item => renderItem(item, expandedItems, toggleExpand, scoreColor, scoreBg, scorePct))}
            </details>
          )}

          {items.length === 0 && (
            <div className="ca-empty">No items found above {scorePct(minScore)} similarity.</div>
          )}
        </div>
      )}
    </div>
  )
}

function renderItem(
  item: OverlapItem,
  expandedItems: Set<string>,
  toggleExpand: (id: string) => void,
  scoreColor: (s: number) => string,
  scoreBg: (s: number) => string,
  scorePct: (s: number) => string,
) {
  const expanded = expandedItems.has(item.content_id)
  return (
    <div key={item.content_id} className={`ca-item-card ${expanded ? 'expanded' : ''}`}>
      <div className="ca-item-header" onClick={() => toggleExpand(item.content_id)}>
        <span className="ca-item-name">{item.display_name}</span>
        <Badge className="badge-type">{item.content_type}</Badge>
        {item.category && <span className="ca-item-cat">{item.category}</span>}
        {item.stage && item.stage !== 'prod' && (
          <Badge className={item.stage === 'dev' ? 'badge-dev' : 'badge-event'}>{item.stage}</Badge>
        )}
        <span className="ca-item-spacer" />
        <Badge className="badge-count">{item.neighbor_count} similar</Badge>
        <span
          className="ca-score-badge"
          style={{ color: scoreColor(item.max_score), backgroundColor: scoreBg(item.max_score) }}
        >
          {scorePct(item.max_score)}
        </span>
        <span className="ca-expand-icon">{expanded ? '▾' : '▸'}</span>
      </div>
      {expanded && (
        <div className="ca-item-neighbors">
          {item.neighbors.map(n => (
            <div key={n.content_id} className="ca-neighbor-row">
              <span
                className="ca-score-badge"
                style={{ color: scoreColor(n.similarity_score), backgroundColor: scoreBg(n.similarity_score) }}
              >
                {scorePct(n.similarity_score)}
              </span>
              <a href={`/browse?search=${encodeURIComponent(n.display_name)}`} className="ca-neighbor-name">
                {n.display_name}
              </a>
              <Badge className="badge-type">{n.content_type}</Badge>
              {n.category && <span className="ca-neighbor-cat">{n.category}</span>}
              {n.stage && n.stage !== 'prod' && (
                <Badge className={n.stage === 'dev' ? 'badge-dev' : 'badge-event'}>{n.stage}</Badge>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Deploy to dev and verify in browser**

Run: `cd /Users/nstephan/devel/rcars-advisory && ./dev-services.sh start`

Open http://localhost:3000/analysis/overlap and verify:
1. Stats bar shows near-duplicate, high overlap, and total pair counts
2. Filter controls work (stage dropdown, min score, search)
3. Score-band sections are collapsible, near-duplicates and high overlap open by default
4. Item rows expand to show neighbor list
5. Clicking a neighbor name navigates to the browse page

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/pages/ContentAnalysisPage.tsx \
       src/frontend/src/services/api.ts
git commit -m "[RHDPCD-599] Rewrite overlap page with item-centric score-band layout

    - Three score-band sections: near-duplicates, high overlap, related
    - Each item expands to show neighbors with individual scores
    - Filters: min score, stage, search by name
    - Default threshold raised to 85%"
```

---

### Task 7: Frontend — Browse Card Split + SyncPage Refresh

**Files:**
- Modify: `src/frontend/src/pages/BrowsePage.tsx:539-548` (fetch trigger), `:922-952` (render section)
- Modify: `src/frontend/src/pages/SyncPage.tsx` — add refresh action card

**Interfaces:**
- Consumes: `getSimilarItems(identifier, minScore, relationshipType)` from Task 6 API update, `computeSimilarity()` from Task 6 API update
- Produces: Browse card with split Overlap / Related sections; SyncPage with similarity refresh button

- [ ] **Step 1: Update BrowsePage fetch to request relationship_type='all'**

In `src/frontend/src/pages/BrowsePage.tsx`, update the similar items state type (around line 403) to include `relationship_type`:

```typescript
const [similarItems, setSimilarItems] = useState<Record<string, Array<{
  content_id: string; ci_name: string | null; display_name: string
  content_type: string; source: string; category: string; stage: string
  summary: string | null; similarity_score: number
  relationship_type?: string
}>>>({})
```

Update the fetch call in `handleExpand` (around line 541) to pass `relationship_type='all'`:

```typescript
api.getSimilarItems(ciName, 0.85, 'all').then(data => {
```

- [ ] **Step 2: Split "Similar Content" into Overlap + Related sections**

Replace the single "Similar Content" `CollapsibleSection` (lines 922-952) with two sections:

```tsx
{/* 6a. Overlapping Content (same source) */}
{similarItems[item.ci_name] && similarItems[item.ci_name].filter(s => s.relationship_type === 'overlap' || !s.relationship_type).length > 0 && (
  <CollapsibleSection
    label="Overlapping Content"
    color="red"
    count={similarItems[item.ci_name].filter(s => s.relationship_type === 'overlap' || !s.relationship_type).length}
  >
    <p className="browse-similar-desc">These items cover very similar ground.</p>
    {similarItems[item.ci_name]
      .filter(s => s.relationship_type === 'overlap' || !s.relationship_type)
      .map(sim => (
        <div key={sim.content_id || sim.ci_name} className="browse-similar-row">
          <span className={`browse-similar-score ${sim.similarity_score >= 0.95 ? 'high' : 'medium'}`}>
            {Math.round(sim.similarity_score * 100)}%
          </span>
          <span
            className="browse-similar-name"
            onClick={() => { handleSearchChange(sim.ci_name || sim.display_name); window.scrollTo({ top: 0 }) }}
          >
            {sim.display_name || sim.ci_name}
          </span>
          <span className="browse-similar-cat">{sim.category}</span>
          {sim.stage !== 'prod' && (
            <Badge className={sim.stage === 'dev' ? 'badge-dev' : 'badge-event'}>
              {sim.stage}
            </Badge>
          )}
        </div>
      ))}
  </CollapsibleSection>
)}

{/* 6b. Related Content (cross-source) */}
{similarItems[item.ci_name] && similarItems[item.ci_name].filter(s => s.relationship_type === 'related').length > 0 && (
  <CollapsibleSection
    label="Related Content"
    color="blue"
    count={similarItems[item.ci_name].filter(s => s.relationship_type === 'related').length}
  >
    <p className="browse-similar-desc">Related content from other types.</p>
    {similarItems[item.ci_name]
      .filter(s => s.relationship_type === 'related')
      .map(sim => (
        <div key={sim.content_id || sim.ci_name} className="browse-similar-row">
          <span className={`browse-similar-score medium`}>
            {Math.round(sim.similarity_score * 100)}%
          </span>
          <span
            className="browse-similar-name"
            onClick={() => { handleSearchChange(sim.ci_name || sim.display_name); window.scrollTo({ top: 0 }) }}
          >
            {sim.display_name || sim.ci_name}
          </span>
          <Badge className="badge-type">{sim.content_type}</Badge>
          <span className="browse-similar-cat">{sim.category}</span>
        </div>
      ))}
  </CollapsibleSection>
)}

{similarLoading.has(item.ci_name) && (
  <div className="browse-loading-inline">Loading similar content…</div>
)}
```

- [ ] **Step 3: Add "Refresh Similarity" to SyncPage**

In `src/frontend/src/pages/SyncPage.tsx`, add a new `AdminAction` for similarity refresh. Insert after the last existing section (around line 450, before the closing `</div>`):

```tsx
<AdminAction
  title="Refresh Similarity"
  description="Recompute pairwise content similarity from current embeddings. Produces both overlap (same-source) and related (cross-source) pairs."
  buttonLabel="Compute Similarity"
  onRun={async (addLog) => {
    addLog('Computing content similarity…')
    const result = await api.computeSimilarity(0.75)
    addLog(`Done: ${result.overlap_pairs} overlap pairs, ${result.related_pairs} related pairs (${result.pairs_stored} total)`)
  }}
/>
```

Import `api` if not already imported at the top of SyncPage.

- [ ] **Step 4: Deploy to dev and verify in browser**

Run: `cd /Users/nstephan/devel/rcars-advisory && ./dev-services.sh start`

Verify:
1. **Browse page:** Expand a card with known overlap pairs → "Overlapping Content" section appears with red label. "Related Content" section is absent (no cross-source data yet).
2. **Sync page:** "Refresh Similarity" card appears. Click it → shows progress log and completion message with pair counts.

- [ ] **Step 5: Run TypeScript build check**

Run: `cd src/frontend && npx tsc --noEmit`

Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/pages/BrowsePage.tsx \
       src/frontend/src/pages/SyncPage.tsx
git commit -m "[RHDPCD-599] Split browse card similar content and add SyncPage refresh

    - Browse card: 'Overlapping Content' (same source) + 'Related Content' (cross-source)
    - Related section hidden until cross-source pairs exist
    - SyncPage: 'Refresh Similarity' action card with progress log"
```

---

## Dependency Graph

```
Task 1 (Schema + Config + Extract)
  ├── Task 2 (Generalize compute + stats)
  │     ├── Task 3 (Item-centric API)
  │     │     └── Task 6 (Frontend overlap page)
  │     └── Task 5 (Pipeline + CLI)
  └── Task 4 (Similar items filter)
        └── Task 7 (Frontend browse + sync)
```

Tasks 3+4 are independent of each other. Tasks 5, 6, 7 are independent of each other (after their respective dependencies).
