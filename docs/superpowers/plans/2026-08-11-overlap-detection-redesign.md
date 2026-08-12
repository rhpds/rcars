# Overlap Detection Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace cosine-similarity candidate funnel with deterministic structured matching on products/topics, saving ~1.9M tokens/night and surfacing verdict-based overlap instead of meaningless cosine percentages.

**Architecture:** New `overlap_candidates` table replaces `content_similarity`. Candidate generation uses SQL set intersection on `showroom_analysis.products_json` and `topics_json` with stage deduplication via `COALESCE(showroom_url, content_id)`. LLM assessment logic (`assess_overlap()`) is reused with changed storage target. Pipeline merges steps 6+7 into a single idempotent step. Frontend switches from score-band grouping to verdict-based grouping.

**Tech Stack:** Python 3.11, FastAPI 2.0, PostgreSQL/pgvector, React 19, PatternFly 6, TypeScript

## Global Constraints

- Embeddings table and advisor vector search are untouched
- Scan pipeline (showroom analysis, content_hash computation) is untouched
- LLM assessment prompt (`prompts/overlap_assessment.txt`) and validation logic are reused as-is
- ComparisonDrawer component structure stays — just drops cosine score
- `overlap_model` config setting is kept (currently `claude-haiku-4-5`)
- Minimum thresholds: `RCARS_OVERLAP_MIN_PRODUCTS=1`, `RCARS_OVERLAP_MIN_TOPICS=2`
- All `content_similarity` references must be fully scrubbed — no dead code left behind

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/api/rcars/db/overlap.py` | Candidate generation, overlap queries, stats |
| Create | `src/api/tests/test_overlap_candidates.py` | Tests for candidate generation + overlap queries |
| Modify | `src/api/rcars/db/database.py:253-271` | Replace `content_similarity` with `overlap_candidates` in SCHEMA_SQL; update `drop_schema()` list at line 516 |
| Modify | `src/api/rcars/db/__init__.py` | Replace similarity exports with overlap exports |
| Modify | `src/api/rcars/config.py:96-136` | Replace similarity thresholds with `overlap_min_products`, `overlap_min_topics`; remove threshold validation |
| Modify | `src/api/rcars/services/overlap_assessment.py:117-257` | Read/write `overlap_candidates` instead of `content_similarity`; content_hash-based cache invalidation |
| Modify | `src/api/rcars/workers/ops.py:1-12,441-508` | Replace steps 6+7 imports and logic with new overlap step |
| Modify | `src/api/rcars/api/routes/analysis.py` | Add overlap endpoints (moved from admin) |
| Modify | `src/api/rcars/api/routes/admin.py:1-20,265-369` | Remove overlap/similarity endpoints and imports |
| Modify | `src/api/rcars/api/routes/catalog.py:232-253` | Remove `/{identifier}/similar` endpoint |
| Modify | `src/api/rcars/api/schemas.py:143-154` | Remove `SimilarItem`, `SimilarItemsResponse` |
| Modify | `src/api/rcars/services/chat/handlers.py:91-125,174-195` | Update `handle_overlap()`, `handle_item_facts()` to use `overlap_candidates` |
| Modify | `src/api/rcars/services/chat/evidence.py:19-33` | Query `overlap_candidates` instead of `content_similarity` |
| Modify | `src/frontend/src/services/api.ts:196-248` | Remove `getSimilarItems`, `computeSimilarity`; update `getOverlapReport`, `getOverlapAssessment` URL paths |
| Modify | `src/frontend/src/pages/ContentAnalysisPage.tsx` | Full redesign: verdict-based stats, filters, grouping |
| Modify | `src/frontend/src/pages/BrowsePage.tsx:403-409,541-550,924-997` | Remove `similarItems`/`similarLoading` state and sections 6a/6b |
| Modify | `src/frontend/src/components/advisor/blocks/OverlapTableBlock.tsx` | Remove similarity percentage; show verdict + shared counts |
| Modify | `src/api/tests/test_overlap_assessment.py` | Update to use `overlap_candidates` table |
| Delete | `src/api/rcars/db/similarity.py` | Entire file — replaced by `db/overlap.py` |
| Delete | `src/api/tests/test_similarity.py` | Entire file — replaced by `test_overlap_candidates.py` |

---

### Task 1: Schema + Config Foundation

**Files:**
- Modify: `src/api/rcars/db/database.py:250-271` (replace `content_similarity` DDL)
- Modify: `src/api/rcars/db/database.py:516` (update `drop_schema()` table list)
- Modify: `src/api/rcars/config.py:96-100` (replace settings)
- Modify: `src/api/rcars/config.py:131-136` (replace validation)

**Interfaces:**
- Produces: `overlap_candidates` table in SCHEMA_SQL; `Settings.overlap_min_products: int` (default 1), `Settings.overlap_min_topics: int` (default 2); `Settings.overlap_model: str` (kept, unchanged)

- [ ] **Step 1: Replace `content_similarity` DDL with `overlap_candidates` in SCHEMA_SQL**

In `src/api/rcars/db/database.py`, replace lines 250-271 (the `content_similarity` block including ALTER TABLEs) with:

```python
-- ═══════════════════════════════════════════════════════════════════
-- overlap_candidates — deterministic structured matching
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS overlap_candidates (
    id SERIAL PRIMARY KEY,
    content_id_a TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_id_b TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    shared_products INTEGER NOT NULL DEFAULT 0,
    shared_topics INTEGER NOT NULL DEFAULT 0,
    content_hash_a TEXT,
    content_hash_b TEXT,
    llm_assessment JSONB,
    assessed_at TIMESTAMPTZ,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id_a, content_id_b)
);
CREATE INDEX IF NOT EXISTS idx_overlap_candidates_a ON overlap_candidates(content_id_a);
CREATE INDEX IF NOT EXISTS idx_overlap_candidates_b ON overlap_candidates(content_id_b);
CREATE INDEX IF NOT EXISTS idx_overlap_candidates_assessed ON overlap_candidates(assessed_at);
```

- [ ] **Step 2: Update `drop_schema()` table list**

In `src/api/rcars/db/database.py`, in the `drop_schema()` method's `tables` list (around line 516), replace `"content_similarity"` with `"overlap_candidates"`.

- [ ] **Step 3: Replace config settings**

In `src/api/rcars/config.py`, replace lines 96-100:

```python
    # Content overlap
    similarity_threshold: float = 0.85
    similarity_high_threshold: float = 0.95
    similarity_storage_threshold: float = 0.75
    overlap_model: str = "claude-haiku-4-5"
```

with:

```python
    # Content overlap
    overlap_min_products: int = 1
    overlap_min_topics: int = 2
    overlap_model: str = "claude-haiku-4-5"
```

- [ ] **Step 4: Replace config validation**

In `src/api/rcars/config.py`, replace lines 131-136:

```python
        if not (0 <= self.similarity_threshold <= 1):
            raise ValueError(f"similarity_threshold must be in [0, 1], got {self.similarity_threshold}")
        if not (0 <= self.similarity_high_threshold <= 1):
            raise ValueError(f"similarity_high_threshold must be in [0, 1], got {self.similarity_high_threshold}")
        if self.similarity_high_threshold < self.similarity_threshold:
            raise ValueError(f"similarity_high_threshold ({self.similarity_high_threshold}) must be >= similarity_threshold ({self.similarity_threshold})")
```

with:

```python
        if self.overlap_min_products < 0:
            raise ValueError(f"overlap_min_products must be >= 0, got {self.overlap_min_products}")
        if self.overlap_min_topics < 0:
            raise ValueError(f"overlap_min_topics must be >= 0, got {self.overlap_min_topics}")
```

- [ ] **Step 5: Run tests to verify nothing breaks yet**

Run: `cd src/api && python -m pytest tests/test_overlap_assessment.py -v -k "test_overlap_model_default or test_schema" --tb=short`

Expected: Tests that check schema and config defaults should still pass (they'll still find `content_similarity` in the running DB from test fixtures). These will be updated in Task 3.

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/db/database.py src/api/rcars/config.py
git commit -m "[JIRA-KEY] Add overlap_candidates schema and config settings

Replace content_similarity DDL with overlap_candidates table.
Replace similarity_threshold/similarity_high_threshold/similarity_storage_threshold
config with overlap_min_products and overlap_min_topics."
```

---

### Task 2: Candidate Generation Module

**Files:**
- Create: `src/api/rcars/db/overlap.py`
- Create: `src/api/tests/test_overlap_candidates.py`

**Interfaces:**
- Consumes: `overlap_candidates` table (Task 1); `showroom_analysis.products_json`, `showroom_analysis.topics_json`, `showroom_analysis.content_hash` columns; `babylon_items.showroom_url`, `babylon_items.stage`; `content_entities.content_id`, `content_entities.retired_at`
- Produces: `generate_overlap_candidates(pool, min_products: int = 1, min_topics: int = 2) -> dict` — returns `{"pairs_inserted": int, "pairs_updated": int, "pairs_pruned": int}`; `prune_stale_candidates(pool) -> int` — returns count of pruned pairs

- [ ] **Step 1: Write failing test for candidate generation**

Create `src/api/tests/test_overlap_candidates.py`:

```python
"""Tests for deterministic overlap candidate generation."""
import pytest
from rcars.db.overlap import generate_overlap_candidates, prune_stale_candidates


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_overlap_candidates.py -v --tb=short`

Expected: FAIL — `ImportError: cannot import name 'generate_overlap_candidates' from 'rcars.db.overlap'`

- [ ] **Step 3: Implement `generate_overlap_candidates` and `prune_stale_candidates`**

Create `src/api/rcars/db/overlap.py`:

```python
"""Deterministic overlap candidate generation via structured matching."""
from __future__ import annotations

import structlog
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = structlog.get_logger(component="overlap")

CANDIDATE_SQL = """
WITH deduped AS (
    SELECT DISTINCT ON (COALESCE(bi.showroom_url, ce.content_id))
        ce.content_id,
        COALESCE(sa.products_json, '[]'::jsonb) AS products,
        COALESCE(sa.topics_json, '[]'::jsonb) AS topics,
        sa.content_hash
    FROM content_entities ce
    JOIN showroom_analysis sa ON sa.content_id = ce.content_id
    LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
    WHERE ce.retired_at IS NULL
    ORDER BY COALESCE(bi.showroom_url, ce.content_id),
             CASE bi.stage WHEN 'prod' THEN 0 WHEN 'event' THEN 1 WHEN 'dev' THEN 2 ELSE 3 END
),
pairs AS (
    SELECT
        a.content_id AS content_id_a,
        b.content_id AS content_id_b,
        a.content_hash AS content_hash_a,
        b.content_hash AS content_hash_b,
        (SELECT COUNT(*) FROM (
            SELECT value FROM jsonb_array_elements_text(a.products)
            INTERSECT
            SELECT value FROM jsonb_array_elements_text(b.products)
        ) x)::int AS shared_products,
        (SELECT COUNT(*) FROM (
            SELECT value FROM jsonb_array_elements_text(a.topics)
            INTERSECT
            SELECT value FROM jsonb_array_elements_text(b.topics)
        ) x)::int AS shared_topics
    FROM deduped a
    JOIN deduped b ON a.content_id < b.content_id
)
SELECT * FROM pairs
WHERE shared_products >= %(min_products)s AND shared_topics >= %(min_topics)s
"""

UPSERT_SQL = """
INSERT INTO overlap_candidates
    (content_id_a, content_id_b, shared_products, shared_topics, content_hash_a, content_hash_b, computed_at)
VALUES (%(a)s, %(b)s, %(sp)s, %(st)s, %(ha)s, %(hb)s, NOW())
ON CONFLICT (content_id_a, content_id_b) DO UPDATE SET
    shared_products = EXCLUDED.shared_products,
    shared_topics = EXCLUDED.shared_topics,
    content_hash_a = EXCLUDED.content_hash_a,
    content_hash_b = EXCLUDED.content_hash_b,
    computed_at = NOW()
"""


def generate_overlap_candidates(
    pool: ConnectionPool,
    min_products: int = 1,
    min_topics: int = 2,
) -> dict:
    """Generate overlap candidates via deterministic structured matching.

    Returns {"pairs_inserted": int, "pairs_updated": int, "total_candidates": int}.
    """
    with pool.connection() as conn:
        conn.row_factory = dict_row
        pairs = conn.execute(
            CANDIDATE_SQL, {"min_products": min_products, "min_topics": min_topics}
        ).fetchall()

        inserted = 0
        updated = 0
        for p in pairs:
            cur = conn.execute(
                "SELECT id FROM overlap_candidates WHERE content_id_a = %s AND content_id_b = %s",
                (p["content_id_a"], p["content_id_b"]),
            )
            exists = cur.fetchone() is not None
            conn.execute(UPSERT_SQL, {
                "a": p["content_id_a"], "b": p["content_id_b"],
                "sp": p["shared_products"], "st": p["shared_topics"],
                "ha": p["content_hash_a"], "hb": p["content_hash_b"],
            })
            if exists:
                updated += 1
            else:
                inserted += 1
        conn.commit()

    logger.info("candidates_generated", inserted=inserted, updated=updated, total=len(pairs),
                min_products=min_products, min_topics=min_topics)
    return {"pairs_inserted": inserted, "pairs_updated": updated, "total_candidates": len(pairs)}


def prune_stale_candidates(pool: ConnectionPool) -> int:
    """Remove candidates where either item is retired or missing showroom_analysis."""
    with pool.connection() as conn:
        cur = conn.execute("""
            DELETE FROM overlap_candidates oc
            WHERE EXISTS (
                SELECT 1 FROM content_entities ce
                WHERE ce.content_id IN (oc.content_id_a, oc.content_id_b)
                  AND ce.retired_at IS NOT NULL
            )
            OR NOT EXISTS (
                SELECT 1 FROM showroom_analysis sa
                WHERE sa.content_id = oc.content_id_a
            )
            OR NOT EXISTS (
                SELECT 1 FROM showroom_analysis sa
                WHERE sa.content_id = oc.content_id_b
            )
        """)
        pruned = cur.rowcount
        conn.commit()
    logger.info("stale_candidates_pruned", pruned=pruned)
    return pruned
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_overlap_candidates.py -v --tb=short`

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/overlap.py src/api/tests/test_overlap_candidates.py
git commit -m "[JIRA-KEY] Add deterministic overlap candidate generation

Generate overlap candidates via product/topic set intersection on
showroom_analysis, with stage dedup via showroom_url. Replaces
cosine similarity funnel."
```

---

### Task 3: Assessment Migration

**Files:**
- Modify: `src/api/rcars/services/overlap_assessment.py:117-207` (`assess_overlap`)
- Modify: `src/api/rcars/services/overlap_assessment.py:210-257` (`batch_assess_overlaps`)
- Modify: `src/api/tests/test_overlap_assessment.py`

**Interfaces:**
- Consumes: `overlap_candidates` table (Task 1), `_load_analysis_pair()` (unchanged), `_validate_assessment()` (unchanged), `_build_assessment_prompt()` (unchanged)
- Produces: Updated `assess_overlap(pool, settings, content_id_a, content_id_b) -> tuple[dict | None, str]` — now reads/writes `overlap_candidates`; returns `"stale"` reason when content_hash differs. Updated `batch_assess_overlaps(pool, settings) -> dict` — finds candidates where `llm_assessment IS NULL` OR content_hash differs.

- [ ] **Step 1: Update `assess_overlap()` to use `overlap_candidates`**

In `src/api/rcars/services/overlap_assessment.py`, replace lines 129-146 (the normalize + cache check block):

```python
    # Normalize order to match overlap_candidates constraint
    if content_id_a > content_id_b:
        content_id_a, content_id_b = content_id_b, content_id_a

    # Check cache — re-assess if content_hash changed
    with pool.connection() as conn:
        cur = conn.execute(
            """SELECT llm_assessment, content_hash_a, content_hash_b
               FROM overlap_candidates
               WHERE content_id_a = %s AND content_id_b = %s""",
            (content_id_a, content_id_b),
        )
        row = cur.fetchone()
        if not row:
            logger.warning("not_candidate_pair", content_id_a=content_id_a, content_id_b=content_id_b)
            return None, "not_overlap"

    # Check if cached and content unchanged
    if row["llm_assessment"]:
        cur_a = conn.execute(
            "SELECT content_hash FROM showroom_analysis WHERE content_id = %s", (content_id_a,)
        )
        cur_b = conn.execute(
            "SELECT content_hash FROM showroom_analysis WHERE content_id = %s", (content_id_b,)
        )
        hash_a = (cur_a.fetchone() or {}).get("content_hash")
        hash_b = (cur_b.fetchone() or {}).get("content_hash")
        if hash_a == row["content_hash_a"] and hash_b == row["content_hash_b"]:
            logger.debug("overlap_assessment_cached", content_id_a=content_id_a, content_id_b=content_id_b)
            return row["llm_assessment"], "cached"
        logger.info("content_changed_reassessing", content_id_a=content_id_a, content_id_b=content_id_b)
```

Note: The hash check queries must happen inside the same `with pool.connection()` block. Restructure the function so the connection stays open for the hash reads. The simplest approach: move the hash check inside the existing `with` block, then fall through to the LLM call.

- [ ] **Step 2: Update the persist block**

Replace lines 196-204 (the persist block that writes to `content_similarity`):

```python
    # Persist
    import json as json_module
    # Get current content hashes for storage
    with pool.connection() as conn:
        ha = conn.execute(
            "SELECT content_hash FROM showroom_analysis WHERE content_id = %s", (content_id_a,)
        ).fetchone()
        hb = conn.execute(
            "SELECT content_hash FROM showroom_analysis WHERE content_id = %s", (content_id_b,)
        ).fetchone()
        conn.execute(
            """UPDATE overlap_candidates
               SET llm_assessment = %s::jsonb, assessed_at = NOW(),
                   content_hash_a = %s, content_hash_b = %s
               WHERE content_id_a = %s AND content_id_b = %s""",
            (json_module.dumps(validated),
             ha["content_hash"] if ha else None,
             hb["content_hash"] if hb else None,
             content_id_a, content_id_b),
        )
        conn.commit()
```

- [ ] **Step 3: Update `batch_assess_overlaps()`**

Replace lines 210-257. Remove the `min_score` parameter. Find candidates where `llm_assessment IS NULL` OR content_hash differs:

```python
def batch_assess_overlaps(pool, settings: Settings) -> dict:
    """Assess all unassessed or stale overlap candidates.

    Returns summary: pairs_found, assessed, cached, skipped, errors, total_tokens.
    """
    logger.info("batch_assess_start")

    with pool.connection() as conn:
        cur = conn.execute(
            """SELECT oc.content_id_a, oc.content_id_b
               FROM overlap_candidates oc
               LEFT JOIN showroom_analysis sa_a ON sa_a.content_id = oc.content_id_a
               LEFT JOIN showroom_analysis sa_b ON sa_b.content_id = oc.content_id_b
               WHERE oc.llm_assessment IS NULL
                  OR oc.content_hash_a IS DISTINCT FROM sa_a.content_hash
                  OR oc.content_hash_b IS DISTINCT FROM sa_b.content_hash
               ORDER BY oc.computed_at DESC""",
        )
        pairs = [(row["content_id_a"], row["content_id_b"]) for row in cur.fetchall()]

    pairs_found = len(pairs)
    assessed = 0
    cached = 0
    skipped = 0
    errors = 0
    total_tokens = 0

    for content_id_a, content_id_b in pairs:
        try:
            result, reason = assess_overlap(pool, settings, content_id_a, content_id_b)
            if reason == "ok":
                assessed += 1
                total_tokens += result["tokens"]["input"] + result["tokens"]["output"]
            elif reason == "cached":
                cached += 1
            elif reason in {"missing_analysis", "not_overlap"}:
                skipped += 1
            else:
                errors += 1
        except Exception as e:
            logger.error("batch_assess_error", content_id_a=content_id_a,
                         content_id_b=content_id_b, error=str(e))
            errors += 1

    logger.info("batch_assess_complete", pairs_found=pairs_found, assessed=assessed,
                cached=cached, skipped=skipped, errors=errors, total_tokens=total_tokens)
    return {
        "pairs_found": pairs_found,
        "assessed": assessed,
        "cached": cached,
        "skipped": skipped,
        "errors": errors,
        "total_tokens": total_tokens,
    }
```

- [ ] **Step 4: Update test fixtures in `test_overlap_assessment.py`**

The existing tests insert into `content_similarity`. Update all fixtures and assertions to use `overlap_candidates` instead. Key changes:

- Replace all `INSERT INTO content_similarity` with `INSERT INTO overlap_candidates` using the new column set (`content_id_a, content_id_b, shared_products, shared_topics, content_hash_a, content_hash_b`)
- Replace all `SELECT ... FROM content_similarity` with `SELECT ... FROM overlap_candidates`
- Remove references to `similarity_score`, `relationship_type`
- Update the schema verification test to check for `overlap_candidates` columns instead of `content_similarity`
- Remove the `_score_band` test (function no longer exists)
- Update `batch_assess_overlaps` call to remove `min_score` parameter

- [ ] **Step 5: Run tests**

Run: `cd src/api && python -m pytest tests/test_overlap_assessment.py -v --tb=short`

Expected: All tests PASS with updated table.

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/services/overlap_assessment.py src/api/tests/test_overlap_assessment.py
git commit -m "[JIRA-KEY] Migrate assessment to overlap_candidates table

assess_overlap() and batch_assess_overlaps() now read/write
overlap_candidates instead of content_similarity. Cache invalidation
uses content_hash comparison instead of relationship_type filter."
```

---

### Task 4: Pipeline Step

**Files:**
- Modify: `src/api/rcars/workers/ops.py:1-12` (imports)
- Modify: `src/api/rcars/workers/ops.py:441-508` (replace steps 6+7)

**Interfaces:**
- Consumes: `generate_overlap_candidates(pool, min_products, min_topics)` (Task 2), `prune_stale_candidates(pool)` (Task 2), `batch_assess_overlaps(pool, settings)` (Task 3), `Settings.overlap_min_products`, `Settings.overlap_min_topics` (Task 1)
- Produces: Updated `run_nightly_pipeline()` with single overlap step replacing steps 6+7. Result dict keys change from `"similarity"` + `"assessment"` to `"overlap"`.

- [ ] **Step 1: Update imports**

In `src/api/rcars/workers/ops.py`, replace lines 11-12:

```python
from rcars.db.similarity import compute_content_similarity
from rcars.services.overlap_assessment import batch_assess_overlaps
```

with:

```python
from rcars.db.overlap import generate_overlap_candidates, prune_stale_candidates
from rcars.services.overlap_assessment import batch_assess_overlaps
```

- [ ] **Step 2: Replace steps 6+7 with single overlap step**

Replace lines 441-496 (steps 6 and 7) with:

```python
    # ── Step 6: Overlap detection (candidates + assessment) ──
    overlap_result = {"status": "skipped"}
    try:
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="pipeline:overlap", status="running",
                               message="Step 6: Generating overlap candidates...")
        import asyncio

        # 6a: Prune stale pairs
        pruned = await asyncio.to_thread(prune_stale_candidates, wctx.db.pool)

        # 6b: Generate candidates
        gen_result = await asyncio.to_thread(
            generate_overlap_candidates,
            wctx.db.pool,
            min_products=wctx.settings.overlap_min_products,
            min_topics=wctx.settings.overlap_min_topics,
        )

        # 6c: Assess unassessed/stale candidates
        assess_result = await asyncio.to_thread(
            batch_assess_overlaps, wctx.db.pool, wctx.settings,
        )

        overlap_result = {
            "status": "complete",
            "pruned": pruned,
            **gen_result,
            **assess_result,
        }
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="pipeline:overlap", status="complete",
                               message=f"Step 6 complete: {gen_result['total_candidates']} candidates, "
                                       f"{assess_result['assessed']} assessed, {pruned} pruned")
        log.info("pipeline_overlap_complete", action="pipeline_step_complete",
                 step="overlap", **overlap_result)
    except Exception as exc:
        msg = f"Step 6 failed (overlap detection): {exc}"
        warnings.append(msg)
        log.error("pipeline_overlap_failed", action="pipeline_step_failed", step="overlap",
                  error=str(exc), traceback=traceback.format_exc())
        overlap_result = {"status": "error", "error": str(exc)}
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="pipeline:overlap", status="failed",
                               message="Step 6 failed: Overlap detection failed (non-fatal)")
```

- [ ] **Step 3: Update result dict**

In the result dict (around line 499-508), replace:

```python
        "similarity": similarity_result,
        "assessment": assessment_result,
```

with:

```python
        "overlap": overlap_result,
```

- [ ] **Step 4: Run tests**

Run: `cd src/api && python -m pytest tests/ -v -k "pipeline or nightly" --tb=short`

Expected: Any pipeline-related tests pass. If no direct pipeline tests exist, verify import resolution: `cd src/api && python -c "from rcars.workers.ops import run_nightly_pipeline; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/workers/ops.py
git commit -m "[JIRA-KEY] Replace pipeline steps 6+7 with single overlap step

Merge cosine similarity computation and batch LLM assessment into
one step: prune stale → generate candidates → assess. Token cost
drops from ~1.9M/night to near-zero for unchanged content."
```

---

### Task 5: Overlap Query Function + API Endpoints

**Files:**
- Modify: `src/api/rcars/db/overlap.py` (add `get_overlap_items`, `get_overlap_stats`)
- Modify: `src/api/rcars/api/routes/analysis.py` (add overlap endpoints)
- Modify: `src/api/rcars/api/routes/admin.py:265-369` (remove overlap/similarity endpoints + imports)
- Modify: `src/api/rcars/api/routes/catalog.py:232-253` (remove similar endpoint)
- Modify: `src/api/rcars/api/schemas.py:143-154` (remove `SimilarItem`, `SimilarItemsResponse`)
- Modify: `src/api/rcars/db/__init__.py` (update exports)
- Add test: `src/api/tests/test_overlap_candidates.py` (add query tests)

**Interfaces:**
- Consumes: `overlap_candidates` table, `Settings.overlap_min_products`, `Settings.overlap_min_topics`
- Produces: `get_overlap_items(pool, verdict=None, search=None, page=1, page_size=100, min_shared_products=None, min_shared_topics=None) -> dict`; `get_overlap_stats(pool) -> dict`; `GET /analysis/overlap` endpoint; `POST /analysis/overlap/assess` endpoint; `GET /analysis/overlap/{a}/{b}` endpoint

- [ ] **Step 1: Write failing test for overlap query**

Add to `src/api/tests/test_overlap_candidates.py`:

```python
from rcars.db.overlap import get_overlap_items, get_overlap_stats


def test_get_overlap_items_groups_by_item(db, seed_items):
    generate_overlap_candidates(db.pool, min_products=1, min_topics=2)
    # Simulate an LLM assessment
    with db.pool.connection() as conn:
        conn.execute(
            """UPDATE overlap_candidates
               SET llm_assessment = '{"verdict": "redundant", "recommendation": "merge",
                   "shared_topics": ["containers"], "differentiators_a": [], "differentiators_b": [],
                   "rationale": "test"}'::jsonb, assessed_at = NOW()""",
        )
        conn.commit()

    result = get_overlap_items(db.pool, verdict="redundant")
    assert result["total_items"] >= 1
    item = result["items"][0]
    assert "content_id" in item
    assert "display_name" in item
    assert "neighbors" in item
    assert len(item["neighbors"]) >= 1
    neighbor = item["neighbors"][0]
    assert "shared_products" in neighbor
    assert "shared_topics" in neighbor
    assert "verdict" in neighbor


def test_get_overlap_stats(db, seed_items):
    generate_overlap_candidates(db.pool, min_products=1, min_topics=2)
    stats = get_overlap_stats(db.pool)
    assert "unassessed" in stats
    assert "total_pairs" in stats
    assert stats["unassessed"] == 1
    assert stats["total_pairs"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/api && python -m pytest tests/test_overlap_candidates.py::test_get_overlap_items_groups_by_item -v --tb=short`

Expected: FAIL — `ImportError: cannot import name 'get_overlap_items'`

- [ ] **Step 3: Implement `get_overlap_items` and `get_overlap_stats`**

Add to `src/api/rcars/db/overlap.py`:

```python
def get_overlap_stats(pool: ConnectionPool) -> dict:
    """Aggregate stats by verdict."""
    with pool.connection() as conn:
        conn.row_factory = dict_row
        row = conn.execute("""
            SELECT
                COUNT(*) AS total_pairs,
                COUNT(*) FILTER (WHERE llm_assessment->>'verdict' = 'redundant') AS redundant,
                COUNT(*) FILTER (WHERE llm_assessment->>'verdict' = 'complementary') AS complementary,
                COUNT(*) FILTER (WHERE llm_assessment->>'verdict' = 'differentiated') AS differentiated,
                COUNT(*) FILTER (WHERE llm_assessment IS NULL) AS unassessed,
                MAX(computed_at) AS last_computed
            FROM overlap_candidates
        """).fetchone()
    return dict(row)


def get_overlap_items(
    pool: ConnectionPool,
    verdict: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 100,
    min_shared_products: int | None = None,
    min_shared_topics: int | None = None,
) -> dict:
    """Item-centric overlap report grouped by verdict."""
    with pool.connection() as conn:
        conn.row_factory = dict_row

        # Build WHERE clauses for the candidates
        conditions = []
        params: dict = {}
        if verdict == "unassessed":
            conditions.append("oc.llm_assessment IS NULL")
        elif verdict:
            conditions.append("oc.llm_assessment->>'verdict' = %(verdict)s")
            params["verdict"] = verdict
        if min_shared_products is not None:
            conditions.append("oc.shared_products >= %(min_sp)s")
            params["min_sp"] = min_shared_products
        if min_shared_topics is not None:
            conditions.append("oc.shared_topics >= %(min_st)s")
            params["min_st"] = min_shared_topics

        where = (" AND " + " AND ".join(conditions)) if conditions else ""

        # Step 1: Find distinct items that appear in matching candidates
        search_cond = ""
        if search:
            search_cond = " AND ce.display_name ILIKE %(search)s"
            params["search"] = f"%{search}%"

        count_sql = f"""
            SELECT COUNT(DISTINCT item_id) FROM (
                SELECT content_id_a AS item_id FROM overlap_candidates oc {where and 'WHERE ' + where.lstrip(' AND ') or ''}
                UNION
                SELECT content_id_b AS item_id FROM overlap_candidates oc {where and 'WHERE ' + where.lstrip(' AND ') or ''}
            ) ids
            JOIN content_entities ce ON ce.content_id = ids.item_id
            WHERE 1=1 {search_cond}
        """
        total = conn.execute(count_sql, params).fetchone()["count"]

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        items_sql = f"""
            SELECT DISTINCT ce.content_id, ce.display_name, ce.content_type, ce.source,
                   bi.ci_name, bi.category, bi.stage
            FROM (
                SELECT content_id_a AS item_id FROM overlap_candidates oc {where and 'WHERE ' + where.lstrip(' AND ') or ''}
                UNION
                SELECT content_id_b AS item_id FROM overlap_candidates oc {where and 'WHERE ' + where.lstrip(' AND ') or ''}
            ) ids
            JOIN content_entities ce ON ce.content_id = ids.item_id
            LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
            WHERE 1=1 {search_cond}
            ORDER BY ce.display_name
            LIMIT %(limit)s OFFSET %(offset)s
        """
        item_rows = conn.execute(items_sql, params).fetchall()

        # Step 2: For each item, fetch its neighbors from matching candidates
        items = []
        for ir in item_rows:
            cid = ir["content_id"]
            neighbor_sql = f"""
                SELECT oc.content_id_a, oc.content_id_b,
                       oc.shared_products, oc.shared_topics,
                       oc.llm_assessment, oc.assessed_at,
                       ce.display_name, ce.content_type, ce.source,
                       bi.ci_name, bi.category, bi.stage
                FROM overlap_candidates oc
                JOIN content_entities ce ON ce.content_id =
                    CASE WHEN oc.content_id_a = %(cid)s THEN oc.content_id_b
                         ELSE oc.content_id_a END
                LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
                WHERE (oc.content_id_a = %(cid)s OR oc.content_id_b = %(cid)s)
                {where}
                ORDER BY oc.shared_products DESC, oc.shared_topics DESC
            """
            n_params = {**params, "cid": cid}
            n_rows = conn.execute(neighbor_sql, n_params).fetchall()

            neighbors = []
            for nr in n_rows:
                assessment = nr["llm_assessment"] or {}
                neighbors.append({
                    "content_id": nr["content_id_a"] if nr["content_id_a"] != cid else nr["content_id_b"],
                    "display_name": nr["display_name"],
                    "content_type": nr["content_type"],
                    "source": nr["source"],
                    "ci_name": nr["ci_name"],
                    "category": nr["category"],
                    "stage": nr["stage"],
                    "shared_products": nr["shared_products"],
                    "shared_topics": nr["shared_topics"],
                    "verdict": assessment.get("verdict"),
                    "recommendation": assessment.get("recommendation"),
                    "assessed_at": str(nr["assessed_at"]) if nr["assessed_at"] else None,
                })

            items.append({
                **dict(ir),
                "neighbor_count": len(neighbors),
                "neighbors": neighbors,
            })

    return {"items": items, "total_items": total, "page": page, "page_size": page_size}
```

- [ ] **Step 4: Run query tests**

Run: `cd src/api && python -m pytest tests/test_overlap_candidates.py -v --tb=short`

Expected: All tests PASS.

- [ ] **Step 5: Update `db/__init__.py` exports**

Replace the contents of `src/api/rcars/db/__init__.py`:

```python
from rcars.db.database import Database
from rcars.db.overlap import (
    generate_overlap_candidates,
    get_overlap_items,
    get_overlap_stats,
    prune_stale_candidates,
)

__all__ = [
    "Database",
    "generate_overlap_candidates",
    "get_overlap_items",
    "get_overlap_stats",
    "prune_stale_candidates",
]
```

- [ ] **Step 6: Add overlap endpoints to analysis routes**

In `src/api/rcars/api/routes/analysis.py`, add imports at the top:

```python
from rcars.db.overlap import get_overlap_items, get_overlap_stats
from rcars.services.overlap_assessment import assess_overlap
```

Add three endpoints (after the performance endpoints, before the retirement workflow endpoints):

```python
@router.get(
    "/overlap",
    summary="Content overlap report — verdict-based, paginated",
)
async def overlap_report(
    request: Request,
    user: str = Depends(require_auth),
    verdict: str | None = Query(None, description="redundant/complementary/differentiated/unassessed"),
    search: str | None = Query(None, description="Search by display name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    min_shared_products: int | None = Query(None, ge=0),
    min_shared_topics: int | None = Query(None, ge=0),
):
    db = request.app.state.db
    result = get_overlap_items(
        db.pool, verdict=verdict, search=search,
        page=page, page_size=page_size,
        min_shared_products=min_shared_products,
        min_shared_topics=min_shared_topics,
    )
    stats = get_overlap_stats(db.pool)
    return {**result, "stats": stats}


@router.post(
    "/overlap/assess",
    summary="On-demand overlap assessment for a pair",
)
async def overlap_assess(
    request: Request,
    content_id_a: str = Query(...),
    content_id_b: str = Query(...),
    user: str = Depends(require_curator),
):
    db = request.app.state.db
    settings = Settings()
    import asyncio
    result, reason = await asyncio.to_thread(
        assess_overlap, db.pool, settings, content_id_a, content_id_b
    )
    return {"assessment": result, "reason": reason}


@router.get(
    "/overlap/{content_id_a}/{content_id_b}",
    summary="Get or compute LLM overlap assessment for a pair",
)
async def overlap_assessment_detail(
    request: Request,
    content_id_a: str,
    content_id_b: str,
    user: str = Depends(require_auth),
):
    db = request.app.state.db
    settings = Settings()
    import asyncio
    result, reason = await asyncio.to_thread(
        assess_overlap, db.pool, settings, content_id_a, content_id_b
    )
    if result is None:
        return {"assessment": None, "assessed_at": None, "reason": reason}
    a, b = (content_id_a, content_id_b) if content_id_a < content_id_b else (content_id_b, content_id_a)
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT assessed_at FROM overlap_candidates WHERE content_id_a = %s AND content_id_b = %s",
            (a, b),
        )
        row = cur.fetchone()
    return {"assessment": result, "assessed_at": row["assessed_at"] if row else None}
```

Add `Settings` import if not already present:

```python
from rcars.config import Settings
```

- [ ] **Step 7: Remove old endpoints from admin routes**

In `src/api/rcars/api/routes/admin.py`:

1. Remove from the imports (line 15): `from rcars.db.similarity import compute_content_similarity, get_overlap_items, get_similarity_stats`
2. Remove the import (line 16): `from rcars.services.overlap_assessment import assess_overlap`
3. Remove `OverlapItemsResponse` from the schemas import (line 11)
4. Delete the `overlap_report` function (lines 265-317)
5. Delete the `compute_similarity` function (lines 320-335)
6. Delete the `overlap_assessment` function (lines 338-368)

- [ ] **Step 8: Remove similar endpoint from catalog routes**

In `src/api/rcars/api/routes/catalog.py`:

1. Remove the import (line 15): `from rcars.db.similarity import get_similar_items as db_get_similar_items`
2. Remove the `SimilarItemsResponse` from schemas import
3. Delete the `get_similar_items` endpoint (lines 232-253)

- [ ] **Step 9: Remove `SimilarItem` and `SimilarItemsResponse` from schemas**

In `src/api/rcars/api/schemas.py`, delete lines 143-154 (the `SimilarItem` and `SimilarItemsResponse` classes). Also remove `OverlapItemsResponse` if it exists and is no longer referenced (the new endpoint returns a plain dict).

- [ ] **Step 10: Run full test suite**

Run: `cd src/api && python -m pytest tests/ -v --tb=short -x`

Expected: All tests pass. Import errors from removed modules should be caught here.

- [ ] **Step 11: Commit**

```bash
git add src/api/rcars/db/overlap.py src/api/rcars/db/__init__.py \
  src/api/rcars/api/routes/analysis.py src/api/rcars/api/routes/admin.py \
  src/api/rcars/api/routes/catalog.py src/api/rcars/api/schemas.py \
  src/api/tests/test_overlap_candidates.py
git commit -m "[JIRA-KEY] Add verdict-based overlap API, remove similarity endpoints

Move overlap endpoints from /admin to /analysis/overlap with verdict-based
filtering. Remove GET /catalog/{id}/similar, GET /admin/overlap,
POST /admin/compute-similarity, GET /admin/overlap/{a}/{b}/assessment."
```

---

### Task 6: Backend Cleanup — Remove `similarity.py` and `content_similarity`

**Files:**
- Delete: `src/api/rcars/db/similarity.py`
- Delete: `src/api/tests/test_similarity.py`
- Modify: `src/api/rcars/db/database.py` (remove `content_similarity` from SCHEMA_SQL if any residual references remain — should already be gone from Task 1)

**Interfaces:**
- Consumes: Completed Tasks 1-5 (all imports already updated)
- Produces: Clean codebase with no `content_similarity` or `similarity.py` references

- [ ] **Step 1: Delete `similarity.py`**

```bash
rm src/api/rcars/db/similarity.py
```

- [ ] **Step 2: Delete `test_similarity.py`**

```bash
rm src/api/tests/test_similarity.py
```

- [ ] **Step 3: Grep for any remaining `content_similarity` or `similarity.py` references**

```bash
grep -rn "content_similarity\|from rcars.db.similarity\|from rcars.db import.*get_similar\|from rcars.db import.*compute_content" src/api/rcars/ src/api/tests/ --include="*.py"
```

Fix any remaining references found. Common locations: stale imports, SQL strings, test fixtures.

- [ ] **Step 4: Run full test suite**

Run: `cd src/api && python -m pytest tests/ -v --tb=short`

Expected: All tests PASS. No import errors.

- [ ] **Step 5: Commit**

```bash
git add -A src/api/rcars/db/similarity.py src/api/tests/test_similarity.py
git commit -m "[JIRA-KEY] Remove similarity.py and content_similarity references

Full scrub of cosine similarity code. db/overlap.py is the sole
overlap module now."
```

---

### Task 7: Chat Handler Updates

**Files:**
- Modify: `src/api/rcars/services/chat/handlers.py:91-125` (`handle_overlap`)
- Modify: `src/api/rcars/services/chat/handlers.py:174-195` (`handle_item_facts`)
- Modify: `src/api/rcars/services/chat/evidence.py:19-33` (`build_evidence_pack`)
- Modify: `src/frontend/src/components/advisor/blocks/OverlapTableBlock.tsx`

**Interfaces:**
- Consumes: `overlap_candidates` table, `get_overlap_items()` from `db/overlap.py` (Task 5)
- Produces: Updated chat handlers returning overlap data from `overlap_candidates`; updated `OverlapTableBlock` showing verdict + shared counts instead of similarity percentage

- [ ] **Step 1: Update `handle_overlap()` in handlers.py**

Replace lines 91-125 with a version that queries `overlap_candidates` instead of `get_similar_items()`:

```python
async def handle_overlap(res: Resolution, db: Database, settings: Settings,
                         stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    if not res.items and not res.scope_ids:
        return HandlerResult(
            blocks=[Block(type="notice", data={"kind": "no_items"})],
            scaffold_facts={"error": "No items specified"}, anchor_ids=[], session_results=[])
    anchors = res.items or [db.get_babylon_item(cid) or {"content_id": cid, "display_name": cid}
                            for cid in res.scope_ids]
    anchor = anchors[0]
    cid = anchor["content_id"]

    with db.pool.connection() as conn:
        from psycopg.rows import dict_row
        conn.row_factory = dict_row
        rows = conn.execute(
            """SELECT oc.content_id_a, oc.content_id_b,
                      oc.shared_products, oc.shared_topics, oc.llm_assessment,
                      ce.display_name, bi.ci_name, bi.stage
               FROM overlap_candidates oc
               JOIN content_entities ce ON ce.content_id =
                   CASE WHEN oc.content_id_a = %(cid)s THEN oc.content_id_b
                        ELSE oc.content_id_a END
               LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
               WHERE oc.content_id_a = %(cid)s OR oc.content_id_b = %(cid)s
               ORDER BY oc.shared_products DESC, oc.shared_topics DESC
               LIMIT 10""",
            {"cid": cid},
        ).fetchall()

    neighbors = []
    for r in rows:
        other_id = r["content_id_b"] if r["content_id_a"] == cid else r["content_id_a"]
        assessment = r["llm_assessment"] or {}
        neighbors.append({
            "content_id": other_id, "ci_name": r.get("ci_name"),
            "display_name": r["display_name"],
            "stage": r.get("stage"),
            "shared_products": r["shared_products"],
            "shared_topics": r["shared_topics"],
            "verdict": assessment.get("verdict"),
            "recommendation": assessment.get("recommendation"),
        })

    return HandlerResult(
        blocks=[Block(type="item_card", data=_item_card(db, anchor)),
                Block(type="overlap_table", data={"anchor": {"content_id": cid,
                                                              "display_name": anchor.get("display_name")},
                                                   "neighbors": neighbors})],
        scaffold_facts={"anchor": anchor.get("display_name"), "neighbor_count": len(neighbors)},
        anchor_ids=[cid],
        session_results=[{"content_id": n["content_id"], "display_name": n["display_name"]}
                         for n in neighbors])
```

- [ ] **Step 2: Update `handle_item_facts()` in handlers.py**

Replace lines 184-188 (the neighbors block):

```python
    card["neighbors"] = [
        {"content_id": n["content_id"], "display_name": n["display_name"],
         "similarity_pct": round(n["similarity_score"] * 100)}
        for n in get_similar_items(db.pool, item["content_id"],
                                   min_score=settings.similarity_threshold)[:5]]
```

with:

```python
    with db.pool.connection() as conn:
        from psycopg.rows import dict_row
        conn.row_factory = dict_row
        n_rows = conn.execute(
            """SELECT oc.content_id_a, oc.content_id_b, oc.shared_products, oc.shared_topics,
                      oc.llm_assessment, ce.display_name
               FROM overlap_candidates oc
               JOIN content_entities ce ON ce.content_id =
                   CASE WHEN oc.content_id_a = %(cid)s THEN oc.content_id_b ELSE oc.content_id_a END
               WHERE oc.content_id_a = %(cid)s OR oc.content_id_b = %(cid)s
               ORDER BY oc.shared_products DESC LIMIT 5""",
            {"cid": item["content_id"]},
        ).fetchall()
    card["neighbors"] = [
        {"content_id": r["content_id_b"] if r["content_id_a"] == item["content_id"] else r["content_id_a"],
         "display_name": r["display_name"],
         "verdict": (r["llm_assessment"] or {}).get("verdict")}
        for r in n_rows]
```

- [ ] **Step 3: Remove `get_similar_items` import from handlers.py**

Remove the import (line 11 or similar): `from rcars.db.similarity import get_similar_items`

- [ ] **Step 4: Update `build_evidence_pack()` in evidence.py**

Replace the `content_similarity` query (lines 19-33) with an `overlap_candidates` query:

```python
        sim_rows = conn.execute(
            """SELECT oc.content_id_a, oc.content_id_b, oc.shared_products, oc.shared_topics,
                      oc.llm_assessment,
                      ce.display_name, bi.stage, sa.products_json,
                      (SELECT pc.provisions FROM performance_channels pc
                       WHERE pc.content_id = ce.content_id AND pc.channel = 'rhdp') AS provisions
               FROM overlap_candidates oc
               JOIN content_entities ce ON ce.content_id =
                    CASE WHEN oc.content_id_a = ANY(%(ids)s) THEN oc.content_id_b
                         ELSE oc.content_id_a END
               LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
               LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
               WHERE oc.content_id_a = ANY(%(ids)s) OR oc.content_id_b = ANY(%(ids)s)
               ORDER BY oc.shared_products DESC, oc.shared_topics DESC
               LIMIT %(cap)s""",
            {"ids": anchor_ids, "cap": MAX_NEIGHBORS}).fetchall()
```

Update the pack-building loop (lines 49-62) to use the new fields:

```python
    for r in sim_rows:
        other = r["content_id_b"] if r["content_id_a"] in anchor_ids else r["content_id_a"]
        anchor = r["content_id_a"] if r["content_id_a"] in anchor_ids else r["content_id_b"]
        seen.add(other)
        products = r["products_json"]
        if isinstance(products, str):
            products = json.loads(products)
        products = (products or [])[:3]
        assessment = r["llm_assessment"] or {}
        pack.append({"anchor": anchor, "name": r["display_name"], "stage": r["stage"],
                     "shared_products": r["shared_products"],
                     "shared_topics": r["shared_topics"],
                     "verdict": assessment.get("verdict"),
                     "relationship": "overlap",
                     "products": products,
                     "provisions": r["provisions"]})
```

- [ ] **Step 5: Update `OverlapTableBlock.tsx`**

In `src/frontend/src/components/advisor/blocks/OverlapTableBlock.tsx`, update the `OverlapNeighbor` interface and table columns:

Replace the interface (lines 9-17):

```typescript
interface OverlapNeighbor {
  display_name: string
  ci_name?: string
  shared_products?: number
  shared_topics?: number
  verdict?: string
  recommendation?: string
  stage?: string
}
```

Update the table header row (lines 59-66) — replace "Similarity" and "Type" columns:

```typescript
<th style={{ padding: '8px 12px', textAlign: 'left' }}>Item</th>
<th style={{ padding: '8px 12px', textAlign: 'center' }}>Verdict</th>
<th style={{ padding: '8px 12px', textAlign: 'right' }}>Products</th>
<th style={{ padding: '8px 12px', textAlign: 'right' }}>Topics</th>
<th style={{ padding: '8px 12px', textAlign: 'left' }}>Stage</th>
<th style={{ padding: '8px 12px', textAlign: 'left' }}>Recommendation</th>
```

Update the table body cells to show verdict badge, shared counts, and recommendation instead of similarity percentage and relationship type. Remove the `relationshipBadgeStyle` function. Use verdict-based colors instead:

```typescript
const verdictStyle = (v?: string) => {
  if (v === 'redundant') return { bg: 'var(--score-red-bg)', color: 'var(--score-red)' }
  if (v === 'complementary') return { bg: 'var(--score-amber-bg)', color: 'var(--score-amber)' }
  if (v === 'differentiated') return { bg: 'var(--score-green-bg, #e8f5e9)', color: 'var(--score-green, #2e7d32)' }
  return { bg: 'var(--bg-card)', color: 'var(--text-muted)' }
}
```

Update the header text from "Similar to:" to "Overlaps with:".

- [ ] **Step 6: Run backend tests**

Run: `cd src/api && python -m pytest tests/ -v --tb=short`

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/services/chat/handlers.py src/api/rcars/services/chat/evidence.py \
  src/frontend/src/components/advisor/blocks/OverlapTableBlock.tsx
git commit -m "[JIRA-KEY] Update chat handlers and evidence to use overlap_candidates

handle_overlap(), handle_item_facts(), and build_evidence_pack() now
query overlap_candidates. OverlapTableBlock shows verdict + shared
counts instead of similarity percentage."
```

---

### Task 8: Frontend — API Client + ContentAnalysisPage Redesign

**Files:**
- Modify: `src/frontend/src/services/api.ts:196-248`
- Modify: `src/frontend/src/pages/ContentAnalysisPage.tsx` (full redesign)

**Interfaces:**
- Consumes: `GET /analysis/overlap` (Task 5), `GET /analysis/overlap/{a}/{b}` (Task 5)
- Produces: Updated `api.getOverlapReport()` calling `/analysis/overlap` with verdict params; updated `ContentOverlapPage` with verdict-based stats/filters/grouping

- [ ] **Step 1: Update API client**

In `src/frontend/src/services/api.ts`, replace lines 196-248 (the similarity/overlap section):

```typescript
  // Content overlap
  getOverlapReport: (params?: {
    verdict?: string; search?: string; page?: number; page_size?: number;
    min_shared_products?: number; min_shared_topics?: number;
  }) => {
    const p = new URLSearchParams()
    if (params?.verdict) p.set('verdict', params.verdict)
    if (params?.search) p.set('search', params.search)
    if (params?.page) p.set('page', String(params.page))
    if (params?.page_size) p.set('page_size', String(params.page_size))
    if (params?.min_shared_products != null) p.set('min_shared_products', String(params.min_shared_products))
    if (params?.min_shared_topics != null) p.set('min_shared_topics', String(params.min_shared_topics))
    const qs = p.toString()
    return request<{
      items: Array<{
        content_id: string; display_name: string; content_type: string; source: string
        ci_name: string | null; category: string | null; stage: string | null
        neighbor_count: number
        neighbors: Array<{
          content_id: string; display_name: string; content_type: string
          source: string; ci_name: string | null; category: string | null
          stage: string | null; shared_products: number; shared_topics: number
          verdict: string | null; recommendation: string | null; assessed_at: string | null
        }>
      }>
      total_items: number; page: number; page_size: number
      stats: {
        redundant: number; complementary: number; differentiated: number
        unassessed: number; total_pairs: number; last_computed: string | null
      }
    }>(`/analysis/overlap${qs ? `?${qs}` : ''}`)
  },

  getOverlapAssessment: (contentIdA: string, contentIdB: string) =>
    request<{
      assessment: {
        verdict: string; shared_topics: string[]; differentiators_a: string[]
        differentiators_b: string[]; recommendation: string; rationale: string
        model: string; tokens: { input: number; output: number }
      } | null
      assessed_at: string | null
      reason?: string
    }>(`/analysis/overlap/${encodeURIComponent(contentIdA)}/${encodeURIComponent(contentIdB)}`),
```

Remove `getSimilarItems` and `computeSimilarity` methods entirely.

- [ ] **Step 2: Redesign ContentAnalysisPage interfaces**

Replace the interfaces at the top of `ContentAnalysisPage.tsx` (lines 6-65):

```typescript
interface OverlapItem {
  content_id: string
  display_name: string
  content_type: string
  source: string
  ci_name: string | null
  category: string | null
  stage: string | null
  neighbor_count: number
  neighbors: Array<NeighborItem>
}

interface NeighborItem {
  content_id: string
  display_name: string
  content_type: string
  source: string
  ci_name: string | null
  category: string | null
  stage: string | null
  shared_products: number
  shared_topics: number
  verdict: string | null
  recommendation: string | null
  assessed_at: string | null
}

interface OverlapStats {
  redundant: number
  complementary: number
  differentiated: number
  unassessed: number
  total_pairs: number
  last_computed: string | null
}
```

Keep `ItemSummary`, `OverlapAssessment`, `DrawerPair` interfaces mostly as-is. In `DrawerPair`, change `neighbor: NeighborItem` to use the updated type.

- [ ] **Step 3: Redesign ContentOverlapPage state and data loading**

Replace the state variables and `loadData` function. Key changes:
- Remove `minScore`, `thresholds`, `computing` state
- Add `verdict` filter state (default: no filter)
- `loadData` calls `api.getOverlapReport({ verdict, search })`
- Remove `handleCompute` function

```typescript
export function ContentOverlapPage() {
  const [searchParams] = useSearchParams()
  const [items, setItems] = useState<OverlapItem[]>([])
  const [stats, setStats] = useState<OverlapStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [verdict, setVerdict] = useState<string>(searchParams.get('verdict') || '')
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [drawer, setDrawer] = useState<DrawerPair | null>(null)
  const detailCache = useRef<Record<string, ItemSummary>>({})

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getOverlapReport({
        verdict: verdict || undefined,
        search: search || undefined,
      })
      setItems(data.items)
      setStats(data.stats)
    } finally {
      setLoading(false)
    }
  }, [verdict, search])

  useEffect(() => { loadData() }, [loadData])
```

- [ ] **Step 4: Redesign stats cards**

Replace the stats grid (lines 194-212) with verdict-based counts:

```typescript
{stats && (
  <div className="ca-stats-grid">
    <div className="ca-stat-card ca-stat-red" onClick={() => setVerdict('redundant')} style={{ cursor: 'pointer' }}>
      <div className="ca-stat-value">{stats.redundant}</div>
      <div className="ca-stat-label">Redundant</div>
    </div>
    <div className="ca-stat-card ca-stat-amber" onClick={() => setVerdict('complementary')} style={{ cursor: 'pointer' }}>
      <div className="ca-stat-value">{stats.complementary}</div>
      <div className="ca-stat-label">Complementary</div>
    </div>
    <div className="ca-stat-card" onClick={() => setVerdict('differentiated')} style={{ cursor: 'pointer' }}>
      <div className="ca-stat-value">{stats.differentiated}</div>
      <div className="ca-stat-label">Differentiated</div>
    </div>
    <div className="ca-stat-card ca-stat-blue" onClick={() => setVerdict('unassessed')} style={{ cursor: 'pointer' }}>
      <div className="ca-stat-value">{stats.unassessed}</div>
      <div className="ca-stat-label">Unassessed</div>
    </div>
  </div>
)}
```

- [ ] **Step 5: Redesign controls**

Replace the controls (lines 214-245). Remove `FormSelect` for min score and "Refresh Similarity" button. Add verdict dropdown:

```typescript
<div className="ca-controls">
  <FormSelect value={verdict} onChange={(_e, v) => setVerdict(v)} aria-label="Verdict filter">
    <FormSelectOption value="" label="All verdicts" />
    <FormSelectOption value="redundant" label="Redundant" />
    <FormSelectOption value="complementary" label="Complementary" />
    <FormSelectOption value="differentiated" label="Differentiated" />
    <FormSelectOption value="unassessed" label="Unassessed" />
  </FormSelect>

  <SearchInput
    placeholder="Search by name…"
    value={search}
    onChange={(_e, v) => setSearch(v)}
    onClear={() => setSearch('')}
  />
</div>
```

- [ ] **Step 6: Redesign item list — flat list instead of score bands**

Replace the band sections (lines 250-315) with a flat item list:

```typescript
{loading ? (
  <div className="browse-loading"><Spinner size="lg" /> Loading overlap data…</div>
) : items.length === 0 ? (
  <div className="browse-loading">No overlap candidates found{verdict ? ` with verdict "${verdict}"` : ''}.</div>
) : (
  <div className="ca-band-sections">
    {items.map(item => (
      <OverlapItemRow
        key={item.content_id}
        item={item}
        expanded={expandedItems.has(item.content_id)}
        onToggle={toggleExpand}
        onCompare={openDrawer}
      />
    ))}
  </div>
)}
```

- [ ] **Step 7: Update `OverlapItemRow` component**

Replace the `OverlapItemRow` function (lines 324-384). Remove score-related props and display. Show neighbor count and top verdict instead:

```typescript
function OverlapItemRow({
  item, expanded, onToggle, onCompare,
}: {
  item: OverlapItem
  expanded: boolean
  onToggle: (id: string) => void
  onCompare: (item: OverlapItem, neighbor: NeighborItem) => void
}) {
  return (
    <div className={`browse-item ${expanded ? 'expanded' : ''}`}>
      <div className="browse-item-header" onClick={() => onToggle(item.content_id)}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <span className="browse-item-title">{item.display_name}</span>
          {item.ci_name && <div className="browse-item-ci">{item.ci_name}</div>}
        </div>
        <Badge className="browse-badge">{item.content_type}</Badge>
        {item.stage && item.stage !== 'prod' && (
          <Badge className={item.stage === 'dev' ? 'badge-dev' : 'badge-event'}>{item.stage}</Badge>
        )}
        <Badge className="browse-badge">{item.neighbor_count} overlap{item.neighbor_count !== 1 ? 's' : ''}</Badge>
        <span className="browse-expand-icon">{expanded ? '▾' : '▸'}</span>
      </div>
      {expanded && (
        <div className="ca-item-neighbors">
          {item.neighbors.map(n => (
            <div key={n.content_id} className="browse-similar-row">
              <VerdictBadge
                verdict={n.verdict}
                onClick={(e) => { e.stopPropagation(); onCompare(item, n) }}
                style={{ cursor: 'pointer' }}
                title="Compare details"
              />
              <a
                href={`/browse?search=${encodeURIComponent(n.ci_name || n.display_name)}`}
                target="_blank" rel="noopener noreferrer"
                className="browse-similar-name"
              >
                {n.display_name}
              </a>
              <span className="browse-similar-cat" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                {n.shared_products}p / {n.shared_topics}t
              </span>
              {n.recommendation && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  {n.recommendation.replace('_', ' ')}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 8: Add `VerdictBadge` helper and update `ComparisonDrawer`**

Add a small helper above the main component:

```typescript
const VERDICT_COLORS: Record<string, { color: string; bg: string }> = {
  redundant: { color: 'var(--score-red)', bg: 'var(--score-red-bg)' },
  complementary: { color: 'var(--score-amber)', bg: 'var(--score-amber-bg)' },
  differentiated: { color: 'var(--score-green, #2e7d32)', bg: 'var(--score-green-bg, #e8f5e9)' },
}

function VerdictBadge({ verdict, onClick, style, title }: {
  verdict: string | null; onClick?: (e: React.MouseEvent) => void; style?: React.CSSProperties; title?: string
}) {
  const colors = VERDICT_COLORS[verdict || ''] || { color: 'var(--text-muted)', bg: 'var(--bg-card)' }
  return (
    <span className="ca-score-badge" style={{ color: colors.color, backgroundColor: colors.bg, ...style }}
          onClick={onClick} title={title}>
      {verdict || 'unassessed'}
    </span>
  )
}
```

Update `ComparisonDrawer` (lines 387-443):
- Remove `scorePct`, `scoreColor`, `scoreBg` props
- Replace the similarity score display in the header with a verdict badge
- Change "Similarity Comparison" title to "Overlap Comparison"

Update the `openDrawer` function to use the updated `api.getOverlapAssessment` URL path (already done by API client update).

- [ ] **Step 9: Test in browser**

Start dev server: `cd src/frontend && npm run dev`

Verify:
1. Content Analysis → Overlap page loads
2. Stats show verdict counts (redundant, complementary, differentiated, unassessed)
3. Verdict filter works
4. Search filter works
5. Clicking an item expands to show neighbors with verdict badges and shared counts
6. Clicking a verdict badge opens the comparison drawer
7. Drawer shows LLM assessment details

- [ ] **Step 10: Commit**

```bash
git add src/frontend/src/services/api.ts src/frontend/src/pages/ContentAnalysisPage.tsx
git commit -m "[JIRA-KEY] Redesign overlap page with verdict-based display

Replace cosine score bands with verdict-based stats and filtering.
Remove getSimilarItems, computeSimilarity API methods. Overlap
endpoint now at /analysis/overlap."
```

---

### Task 9: Frontend — BrowsePage Cleanup

**Files:**
- Modify: `src/frontend/src/pages/BrowsePage.tsx:403-409,541-550,924-997`

**Interfaces:**
- Consumes: Removal of `api.getSimilarItems()` (Task 8)
- Produces: BrowsePage without similar/related content sections

- [ ] **Step 1: Remove `similarItems` and `similarLoading` state**

In `src/frontend/src/pages/BrowsePage.tsx`, delete lines 403-409 (the state declarations for `similarItems` and `similarLoading`):

```typescript
  const [similarItems, setSimilarItems] = useState<Record<string, Array<{...}>>>({})
  const [similarLoading, setSimilarLoading] = useState<Set<string>>(new Set())
```

- [ ] **Step 2: Remove the `getSimilarItems` call on card expand**

Delete lines 541-550 (the block that calls `api.getSimilarItems()` and sets state):

```typescript
    if (similarItems[ciName] === undefined && !similarLoading.has(ciName)) {
      setSimilarLoading(prev => new Set(prev).add(ciName))
      api.getSimilarItems(ciName, 0.85, 'all').then(data => { ... }).catch(() => { ... })
    }
```

- [ ] **Step 3: Remove sections 6a and 6b**

Delete lines 924-997 (the "Similar Content" and "Related Content" CollapsibleSection blocks). Also delete the `similarLoading` spinner block that follows (around line 999).

- [ ] **Step 4: Remove any remaining `similarItems` / `similarLoading` references**

Search the file for any remaining references to `similarItems` or `similarLoading` and remove them.

- [ ] **Step 5: Test in browser**

Verify:
1. Browse page loads without errors
2. Expanding a card shows details but no "Similar Content" or "Related Content" sections
3. No console errors related to `getSimilarItems`

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/pages/BrowsePage.tsx
git commit -m "[JIRA-KEY] Remove similar/related content sections from Browse page

Remove getSimilarItems calls, similarItems/similarLoading state,
and sections 6a (Similar Content) and 6b (Related Content).
Overlap detection is now solely on the Content Analysis page."
```

---

## Self-Review Checklist

**1. Spec coverage:**
- [x] New `overlap_candidates` table → Task 1
- [x] Stage dedup via `COALESCE(showroom_url, content_id)` → Task 2 (CANDIDATE_SQL)
- [x] Deterministic matching on products + topics → Task 2
- [x] INSERT ... ON CONFLICT DO UPDATE (no DELETE) → Task 2 (UPSERT_SQL)
- [x] Prune stale pairs → Task 2 (`prune_stale_candidates`)
- [x] Assessment reads from `overlap_candidates` → Task 3
- [x] Content_hash-based re-assessment → Task 3
- [x] Pipeline merges steps 6+7 → Task 4
- [x] `GET /analysis/overlap` with verdict params → Task 5
- [x] `POST /analysis/overlap/assess` kept → Task 5
- [x] `GET /analysis/overlap/{a}/{b}` kept → Task 5
- [x] Removed `GET /analysis/similarity/stats` → Task 5 (never existed separately, was part of admin overlap)
- [x] Removed `GET /analysis/similarity` → Task 5
- [x] Removed `GET /catalog/{ci_name}/similar` → Task 5
- [x] `RCARS_OVERLAP_MIN_PRODUCTS`, `RCARS_OVERLAP_MIN_TOPICS` settings → Task 1
- [x] Frontend: verdict-based stats → Task 8
- [x] Frontend: verdict filter → Task 8
- [x] Frontend: verdict badge + recommendation → Task 8
- [x] Frontend: ComparisonDrawer drops cosine score → Task 8
- [x] Browse: remove Similar/Related sections → Task 9
- [x] Code removal: `similarity.py` → Task 6
- [x] Code removal: `content_similarity` schema → Task 1 (replaced)
- [x] Code removal: similarity config settings → Task 1
- [x] Chat handler updates → Task 7
- [x] Evidence pack updates → Task 7
- [x] `OverlapTableBlock` updates → Task 7
- [x] Embeddings/vector search untouched → verified (no tasks modify them)
- [x] LLM assessment prompt reused as-is → verified (no changes to `overlap_assessment.txt`)

**2. Placeholder scan:** No TBD, TODO, or "implement later" found.

**3. Type consistency:**
- `generate_overlap_candidates()` signature consistent across Task 2 (definition) and Task 4 (call site)
- `batch_assess_overlaps()` signature updated consistently in Task 3 (definition) and Task 4 (call site) — `min_score` parameter removed from both
- `get_overlap_items()` signature consistent across Task 5 (definition) and no other call sites
- `get_overlap_stats()` signature consistent across Task 5 (definition) and Task 5 (analysis route call)
- `prune_stale_candidates()` consistent across Task 2 (definition) and Task 4 (call site)
- Frontend `NeighborItem` interface matches API response shape in Task 8
