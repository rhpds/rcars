# LLM Overlap Assessment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LLM-powered structured assessments to overlap pairs — verdict, shared topics, differentiators, recommendation — displayed in the existing ComparisonDrawer.

**Architecture:** New service module `overlap_assessment.py` calls `call_llm()` with analysis profiles from `showroom_analysis`, persists results as JSONB on `content_similarity`. New API endpoint returns cached or on-demand assessments. Frontend drawer gains an assessment section below summaries. Nightly pipeline batch-assesses >=95% pairs.

**Tech Stack:** Python 3.11 / FastAPI / psycopg / structlog (backend), React 19 / PatternFly 6 / TypeScript (frontend)

## Global Constraints

- All LLM responses must be structured JSON — use `parse_analysis_response()` for parsing
- `RCARS_` env var prefix for all settings (Pydantic Settings, case-insensitive)
- Prompt files live in `src/api/rcars/prompts/` as `.txt` with `{variable}` placeholders
- Auth: `require_curator` for overlap endpoints (curators + admins)
- Logging: structlog JSON with `component`, `action` fields
- Schema changes: `ALTER TABLE ADD COLUMN IF NOT EXISTS` at bottom of `SCHEMA_SQL`
- Working directory: `/Users/nstephan/devel/rcars-advisory/.worktrees/RHDPCD-614-llm-overlap-assessment`

---

### Task 1: Schema — Add `llm_assessment` and `assessed_at` columns

**Files:**
- Modify: `src/api/rcars/db/database.py:245-246` (after existing `ALTER TABLE` for `relationship_type`)

**Interfaces:**
- Consumes: nothing
- Produces: `content_similarity.llm_assessment JSONB` and `content_similarity.assessed_at TIMESTAMPTZ` columns, available to all downstream tasks

- [ ] **Step 1: Write failing test**

Create `src/api/tests/test_overlap_assessment.py` with the schema test:

```python
"""Tests for LLM overlap assessment."""

import os
import psycopg
from psycopg.rows import dict_row
import pytest
from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    """Create a fresh test database with schema."""
    with psycopg.connect(TEST_DB_URL, autocommit=True, row_factory=dict_row) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row['tablename']} CASCADE")

    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def test_content_similarity_has_assessment_columns(db):
    with db.pool.connection() as conn:
        cur = conn.execute(
            """SELECT column_name, data_type
               FROM information_schema.columns
               WHERE table_name = 'content_similarity'
                 AND column_name IN ('llm_assessment', 'assessed_at')
               ORDER BY column_name"""
        )
        cols = {row["column_name"]: row["data_type"] for row in cur.fetchall()}
    assert cols["llm_assessment"] == "jsonb"
    assert cols["assessed_at"] == "timestamp with time zone"
```

- [ ] **Step 2: Run test, verify it fails**

Run: `cd src/api && python -m pytest tests/test_overlap_assessment.py::test_content_similarity_has_assessment_columns -v`
Expected: FAIL — KeyError on `llm_assessment`

- [ ] **Step 3: Add ALTER TABLE statements to SCHEMA_SQL**

In `src/api/rcars/db/database.py`, after line 246 (the `idx_content_similarity_reltype` index), add:

```python
ALTER TABLE content_similarity ADD COLUMN IF NOT EXISTS llm_assessment JSONB;
ALTER TABLE content_similarity ADD COLUMN IF NOT EXISTS assessed_at TIMESTAMPTZ;
```

- [ ] **Step 4: Run test, verify it passes**

Run: `cd src/api && python -m pytest tests/test_overlap_assessment.py::test_content_similarity_has_assessment_columns -v`
Expected: PASS

- [ ] **Step 5: Run existing similarity tests to confirm no regression**

Run: `cd src/api && python -m pytest tests/test_similarity.py -v`
Expected: All 16 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/db/database.py src/api/tests/test_overlap_assessment.py
git commit -m "[RHDPCD-614] Add llm_assessment and assessed_at columns to content_similarity"
```

---

### Task 2: Config — Add `overlap_model` setting

**Files:**
- Modify: `src/api/rcars/config.py:96-99` (after existing content overlap settings)

**Interfaces:**
- Consumes: nothing
- Produces: `Settings.overlap_model: str` — used by Task 4 (`assess_overlap()`) to select the LLM model

- [ ] **Step 1: Add overlap_model setting**

In `src/api/rcars/config.py`, after line 99 (`similarity_storage_threshold`), add:

```python
    overlap_model: str = "claude-sonnet-4-6"
```

- [ ] **Step 2: Write test verifying config**

Add to `src/api/tests/test_overlap_assessment.py`:

```python
from rcars.config import Settings


def test_overlap_model_default():
    s = Settings()
    assert s.overlap_model == "claude-sonnet-4-6"


def test_overlap_model_from_env(monkeypatch):
    monkeypatch.setenv("RCARS_OVERLAP_MODEL", "claude-haiku-4-5")
    s = Settings()
    assert s.overlap_model == "claude-haiku-4-5"
```

- [ ] **Step 3: Run tests**

Run: `cd src/api && python -m pytest tests/test_overlap_assessment.py::test_overlap_model_default tests/test_overlap_assessment.py::test_overlap_model_from_env -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/api/rcars/config.py src/api/tests/test_overlap_assessment.py
git commit -m "[RHDPCD-614] Add overlap_model config setting"
```

---

### Task 3: Bundled fix — `_score_band` rename "related" → "moderate" and access level changes

**Files:**
- Modify: `src/api/rcars/db/similarity.py:221` (`_score_band` return value)
- Modify: `src/api/rcars/api/routes/admin.py:276,326` (`require_admin` → `require_curator`)
- Modify: `src/frontend/src/pages/ContentAnalysisPage.tsx:152,263-266` (band label and CSS class)

**Interfaces:**
- Consumes: nothing
- Produces: `_score_band()` returns `"moderate"` instead of `"related"` for scores 0.75–0.84; overlap endpoints accept curator auth

- [ ] **Step 1: Write failing test for _score_band rename**

Add to `src/api/tests/test_overlap_assessment.py`:

```python
from rcars.db.similarity import _score_band


def test_score_band_returns_moderate_not_related():
    assert _score_band(0.80) == "moderate"
    assert _score_band(0.75) == "moderate"
    assert _score_band(0.84) == "moderate"
    assert _score_band(0.95) == "near_duplicate"
    assert _score_band(0.90) == "high_overlap"
```

- [ ] **Step 2: Run test, verify it fails**

Run: `cd src/api && python -m pytest tests/test_overlap_assessment.py::test_score_band_returns_moderate_not_related -v`
Expected: FAIL — `assert 'related' == 'moderate'`

- [ ] **Step 3: Fix _score_band return value**

In `src/api/rcars/db/similarity.py`, change line 221:

Old: `return "related"`
New: `return "moderate"`

- [ ] **Step 4: Run test, verify it passes**

Run: `cd src/api && python -m pytest tests/test_overlap_assessment.py::test_score_band_returns_moderate_not_related -v`
Expected: PASS

- [ ] **Step 5: Change require_admin → require_curator on overlap endpoints**

In `src/api/rcars/api/routes/admin.py`:

Line 276: change `user: str = Depends(require_admin)` to `user: str = Depends(require_curator)`
Line 326: change `user: str = Depends(require_admin)` to `user: str = Depends(require_curator)`

Verify `require_curator` is already imported — check the imports at the top of the file. It should be imported alongside `require_admin` from `rcars.api.auth`.

- [ ] **Step 6: Update frontend band labels**

In `src/frontend/src/pages/ContentAnalysisPage.tsx`:

Line 152: change `bandItems('related')` to `bandItems('moderate')`

Lines 263-266: change the band section:

Old:
```tsx
          {relatedBand.length > 0 && (
            <details className="ca-band-section">
              <summary className="ca-band-header ca-band-muted">
                Related ({relatedBand.length}) · 75%–84%
```

New:
```tsx
          {relatedBand.length > 0 && (
            <details className="ca-band-section">
              <summary className="ca-band-header ca-band-muted">
                Moderate ({relatedBand.length}) · 75%–84%
```

- [ ] **Step 7: Run existing similarity tests**

Run: `cd src/api && python -m pytest tests/test_similarity.py -v`
Expected: All pass. The existing tests use `_score_band` internally via `get_overlap_items` — check if any assert on the string `"related"` as a band value. If `test_overlap_item_centric_returns_score_bands` asserts `"related"`, update it to `"moderate"`.

- [ ] **Step 8: Commit**

```bash
git add src/api/rcars/db/similarity.py src/api/rcars/api/routes/admin.py src/frontend/src/pages/ContentAnalysisPage.tsx
git commit -m "[RHDPCD-614] Rename 'related' score band to 'moderate', change overlap endpoints to require_curator"
```

---

### Task 4: Prompt file and assessment service

**Files:**
- Create: `src/api/rcars/prompts/overlap_assessment.txt`
- Create: `src/api/rcars/services/overlap_assessment.py`

**Interfaces:**
- Consumes: `Settings.overlap_model` (Task 2), `content_similarity.llm_assessment` column (Task 1), `call_llm()` from `rcars.config`, `parse_analysis_response()` from `rcars.services.analyzer`, `showroom_analysis` table fields
- Produces: `assess_overlap(pool, settings, content_id_a, content_id_b) -> dict | None`, `batch_assess_overlaps(pool, settings, min_score=0.95) -> dict`, and `_validate_assessment(parsed) -> dict | None` — used by Task 5 (API) and Task 6 (nightly pipeline). Constants `VALID_VERDICTS` and `VALID_RECOMMENDATIONS` define allowed enum values.

- [ ] **Step 1: Create prompt file**

Create `src/api/rcars/prompts/overlap_assessment.txt`:

```
You are a Red Hat Demo Platform (RHDP) content analyst. Two catalog items have been flagged as potentially overlapping based on embedding similarity. Assess whether they are truly redundant, complementary, or differentiated.

## Item A: {display_name_a}

**Learning Objectives:**
{learning_objectives_a}

**Modules:**
{modules_a}

**Products:**
{products_a}

**Summary:**
{summary_a}

**Supplementary context (LLM-inferred, may not reflect actual content):**
- Audience: {audience_a}
- Difficulty: {difficulty_a}
- Estimated duration: {duration_a} minutes
- Use cases: {use_cases_a}
- Topics: {topics_a}

## Item B: {display_name_b}

**Learning Objectives:**
{learning_objectives_b}

**Modules:**
{modules_b}

**Products:**
{products_b}

**Summary:**
{summary_b}

**Supplementary context (LLM-inferred, may not reflect actual content):**
- Audience: {audience_b}
- Difficulty: {difficulty_b}
- Estimated duration: {duration_b} minutes
- Use cases: {use_cases_b}
- Topics: {topics_b}

## Instructions

Compare primarily on learning objectives, module content, and products. Use audience, difficulty, and topics as supplementary context only — these are LLM-inferred during content scanning and may not accurately reflect the actual content.

Provide your assessment as a JSON object with these fields:

- verdict: One of "redundant", "complementary", or "differentiated"
  - "redundant" — both items teach essentially the same skills with the same products; one could replace the other
  - "complementary" — significant overlap but each adds unique value; together they cover more than either alone
  - "differentiated" — similar topic area but distinct learning outcomes, products, or depth
- shared_topics: Array of strings — specific topics/skills both items cover (be precise, not generic)
- differentiators_a: Array of strings — what Item A covers that Item B does not
- differentiators_b: Array of strings — what Item B covers that Item A does not
- recommendation: One of "merge", "keep_both", or "retire_one"
  - "merge" — content is redundant enough to combine into a single item
  - "keep_both" — items serve different enough purposes to justify both existing
  - "retire_one" — one item is a strict subset of the other; note which in rationale
- rationale: 1-2 sentences explaining your verdict and recommendation

Return ONLY valid JSON (no markdown fences):
{
  "verdict": "...",
  "shared_topics": ["..."],
  "differentiators_a": ["..."],
  "differentiators_b": ["..."],
  "recommendation": "...",
  "rationale": "..."
}
```

- [ ] **Step 2: Write tests for the assessment service**

Add to `src/api/tests/test_overlap_assessment.py`:

```python
import json
import math
from unittest.mock import patch, MagicMock
from rcars.services.overlap_assessment import (
    assess_overlap,
    batch_assess_overlaps,
    _build_assessment_prompt,
    _load_analysis_pair,
    _validate_assessment,
    VALID_VERDICTS,
    VALID_RECOMMENDATIONS,
)


def _make_vector(similarity_to_base: float, dim: int = 768) -> str:
    theta = math.acos(similarity_to_base)
    components = [0.0] * dim
    components[0] = math.cos(theta)
    components[1] = math.sin(theta)
    return "[" + ",".join(f"{c:.6f}" for c in components) + "]"


BASE_VECTOR = _make_vector(1.0)
VECTOR_96 = _make_vector(0.96)


def _seed_overlap_pair(db):
    """Seed two items with similarity, analysis data, and a computed overlap pair."""
    from rcars.db.similarity import compute_content_similarity

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            for cid, name in [
                ("babylon:ns.lab-x.prod", "OpenShift Deployment Lab"),
                ("babylon:ns.lab-y.prod", "OpenShift Troubleshooting Lab"),
            ]:
                cur.execute(
                    """INSERT INTO content_entities
                       (content_id, source, content_type, is_hands_on, display_name)
                       VALUES (%s, 'babylon', 'lab', TRUE, %s)""",
                    (cid, name),
                )
                cur.execute(
                    """INSERT INTO babylon_items
                       (content_id, ci_name, category, stage, is_published)
                       VALUES (%s, %s, 'workshop', 'prod', FALSE)""",
                    (cid, cid.split(":")[-1].rsplit(".", 1)[0]),
                )
                cur.execute(
                    """INSERT INTO showroom_analysis
                       (content_id, summary, products_json, topics_json,
                        modules_json, learning_objectives_json, audience_json,
                        difficulty, estimated_duration_min, use_cases_json)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        cid,
                        f"Summary for {name}",
                        json.dumps([{"name": "OpenShift"}]),
                        json.dumps(["containers", "kubernetes"]),
                        json.dumps([{"title": "Module 1"}, {"title": "Module 2"}]),
                        json.dumps(["Learn OCP basics"]),
                        json.dumps(["Platform engineers"]),
                        "intermediate",
                        60,
                        json.dumps(["workshop"]),
                    ),
                )

            for cid, vec in [
                ("babylon:ns.lab-x.prod", BASE_VECTOR),
                ("babylon:ns.lab-y.prod", VECTOR_96),
            ]:
                cur.execute(
                    """INSERT INTO embeddings
                       (content_id, content_type, source, embed_type, content_text, embedding)
                       VALUES (%s, 'lab', 'babylon', 'summary', 'test', %s::vector)""",
                    (cid, vec),
                )
        conn.commit()

    compute_content_similarity(db.pool, threshold=0.75)
    return "babylon:ns.lab-x.prod", "babylon:ns.lab-y.prod"


MOCK_LLM_RESPONSE = json.dumps({
    "verdict": "complementary",
    "shared_topics": ["OpenShift deployment"],
    "differentiators_a": ["GitOps workflow"],
    "differentiators_b": ["CLI troubleshooting"],
    "recommendation": "keep_both",
    "rationale": "Both cover OpenShift but from different angles.",
})


def test_validate_assessment_valid():
    parsed = {
        "verdict": "complementary",
        "shared_topics": ["OpenShift"],
        "differentiators_a": ["GitOps"],
        "differentiators_b": ["CLI"],
        "recommendation": "keep_both",
        "rationale": "Different angles.",
    }
    result = _validate_assessment(parsed)
    assert result is not None
    assert result["verdict"] == "complementary"
    assert result["recommendation"] == "keep_both"


def test_validate_assessment_invalid_verdict():
    parsed = {
        "verdict": "maybe",
        "shared_topics": [],
        "differentiators_a": [],
        "differentiators_b": [],
        "recommendation": "keep_both",
        "rationale": "Unclear.",
    }
    assert _validate_assessment(parsed) is None


def test_validate_assessment_invalid_recommendation():
    parsed = {
        "verdict": "redundant",
        "shared_topics": [],
        "differentiators_a": [],
        "differentiators_b": [],
        "recommendation": "delete_both",
        "rationale": "Bad.",
    }
    assert _validate_assessment(parsed) is None


def test_validate_assessment_missing_arrays_coerced():
    parsed = {
        "verdict": "differentiated",
        "recommendation": "keep_both",
        "rationale": "Totally different.",
    }
    result = _validate_assessment(parsed)
    assert result is not None
    assert result["shared_topics"] == []
    assert result["differentiators_a"] == []
    assert result["differentiators_b"] == []


def test_validate_assessment_missing_verdict_returns_none():
    parsed = {
        "shared_topics": ["OpenShift"],
        "recommendation": "keep_both",
        "rationale": "Missing verdict.",
    }
    assert _validate_assessment(parsed) is None


def test_validate_assessment_coerces_non_list_to_list():
    parsed = {
        "verdict": "redundant",
        "shared_topics": "OpenShift deployment",
        "differentiators_a": "GitOps",
        "differentiators_b": None,
        "recommendation": "merge",
        "rationale": "Same content.",
    }
    result = _validate_assessment(parsed)
    assert result is not None
    assert result["shared_topics"] == ["OpenShift deployment"]
    assert result["differentiators_a"] == ["GitOps"]
    assert result["differentiators_b"] == []


def test_valid_verdicts_and_recommendations_are_frozen():
    assert "redundant" in VALID_VERDICTS
    assert "complementary" in VALID_VERDICTS
    assert "differentiated" in VALID_VERDICTS
    assert "merge" in VALID_RECOMMENDATIONS
    assert "keep_both" in VALID_RECOMMENDATIONS
    assert "retire_one" in VALID_RECOMMENDATIONS


def test_build_assessment_prompt(db):
    cid_a, cid_b = _seed_overlap_pair(db)
    analysis_a, analysis_b = _load_analysis_pair(db.pool, cid_a, cid_b)
    prompt = _build_assessment_prompt(analysis_a, analysis_b)
    assert "OpenShift Deployment Lab" in prompt
    assert "OpenShift Troubleshooting Lab" in prompt
    assert "Learning Objectives" in prompt
    assert "Modules" in prompt


@patch("rcars.services.overlap_assessment.call_llm")
def test_assess_overlap_calls_llm_and_persists(mock_llm, db):
    cid_a, cid_b = _seed_overlap_pair(db)
    mock_llm.return_value = MagicMock(
        text=MOCK_LLM_RESPONSE, input_tokens=500, output_tokens=200
    )
    settings = Settings()
    result = assess_overlap(db.pool, settings, cid_a, cid_b)

    assert result is not None
    assert result["verdict"] == "complementary"
    assert result["recommendation"] == "keep_both"
    assert result["model"] == settings.overlap_model
    assert result["tokens"]["input"] == 500
    mock_llm.assert_called_once()

    # Verify persistence
    with db.pool.connection() as conn:
        cur = conn.execute(
            """SELECT llm_assessment, assessed_at FROM content_similarity
               WHERE content_id_a = %s AND content_id_b = %s""",
            (cid_a, cid_b),
        )
        row = cur.fetchone()
    assert row["llm_assessment"]["verdict"] == "complementary"
    assert row["assessed_at"] is not None


@patch("rcars.services.overlap_assessment.call_llm")
def test_assess_overlap_returns_cache_on_second_call(mock_llm, db):
    cid_a, cid_b = _seed_overlap_pair(db)
    mock_llm.return_value = MagicMock(
        text=MOCK_LLM_RESPONSE, input_tokens=500, output_tokens=200
    )
    settings = Settings()
    assess_overlap(db.pool, settings, cid_a, cid_b)
    result2 = assess_overlap(db.pool, settings, cid_a, cid_b)

    assert result2["verdict"] == "complementary"
    assert mock_llm.call_count == 1  # cached, no second LLM call


@patch("rcars.services.overlap_assessment.call_llm")
def test_assess_overlap_missing_analysis_returns_none(mock_llm, db):
    """Items without showroom_analysis should return None, not call LLM."""
    from rcars.db.similarity import compute_content_similarity

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            for cid, name, vec in [
                ("babylon:ns.no-analysis-a.prod", "No Analysis A", BASE_VECTOR),
                ("babylon:ns.no-analysis-b.prod", "No Analysis B", VECTOR_96),
            ]:
                cur.execute(
                    """INSERT INTO content_entities
                       (content_id, source, content_type, is_hands_on, display_name)
                       VALUES (%s, 'babylon', 'lab', TRUE, %s)""",
                    (cid, name),
                )
                cur.execute(
                    """INSERT INTO babylon_items
                       (content_id, ci_name, category, stage, is_published)
                       VALUES (%s, %s, 'workshop', 'prod', FALSE)""",
                    (cid, cid.split(":")[-1].rsplit(".", 1)[0]),
                )
                cur.execute(
                    """INSERT INTO embeddings
                       (content_id, content_type, source, embed_type, content_text, embedding)
                       VALUES (%s, 'lab', 'babylon', 'summary', 'test', %s::vector)""",
                    (cid, vec),
                )
        conn.commit()
    compute_content_similarity(db.pool, threshold=0.75)

    settings = Settings()
    result = assess_overlap(
        db.pool, settings, "babylon:ns.no-analysis-a.prod", "babylon:ns.no-analysis-b.prod"
    )
    assert result is None
    mock_llm.assert_not_called()


@patch("rcars.services.overlap_assessment.call_llm")
def test_assess_overlap_rejects_invalid_verdict(mock_llm, db):
    """LLM returns valid JSON but invalid verdict — should return None, not persist."""
    cid_a, cid_b = _seed_overlap_pair(db)
    mock_llm.return_value = MagicMock(
        text=json.dumps({
            "verdict": "maybe_similar",
            "shared_topics": ["OpenShift"],
            "differentiators_a": [],
            "differentiators_b": [],
            "recommendation": "keep_both",
            "rationale": "Unclear.",
        }),
        input_tokens=500, output_tokens=200,
    )
    settings = Settings()
    result = assess_overlap(db.pool, settings, cid_a, cid_b)
    assert result is None

    # Verify nothing was persisted
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT llm_assessment FROM content_similarity WHERE content_id_a = %s AND content_id_b = %s",
            (cid_a, cid_b),
        )
        row = cur.fetchone()
    assert row["llm_assessment"] is None


def test_parse_truncated_assessment_response():
    from rcars.services.analyzer import parse_analysis_response

    truncated = '{"verdict": "redundant", "shared_topics": ["OpenShift"], "differentiators_a": []'
    result = parse_analysis_response(truncated)
    assert result is not None
    assert result["verdict"] == "redundant"
```

- [ ] **Step 3: Create the assessment service module**

Create `src/api/rcars/services/overlap_assessment.py`:

```python
"""LLM overlap assessment — structured comparison of similar content pairs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from rcars.config import Settings, call_llm
from rcars.services.analyzer import parse_analysis_response

logger = structlog.get_logger(component="overlap_assessment")

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "overlap_assessment.txt"

VALID_VERDICTS = frozenset({"redundant", "complementary", "differentiated"})
VALID_RECOMMENDATIONS = frozenset({"merge", "keep_both", "retire_one"})


def _coerce_list(val: Any) -> list:
    """Coerce a value to a list — None→[], str→[str], list stays list."""
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return val
    return []


def _validate_assessment(parsed: dict) -> dict | None:
    """Validate LLM response shape. Returns cleaned dict or None if invalid.

    Rejects: missing/invalid verdict, missing/invalid recommendation.
    Coerces: missing array fields → [], string → [string], missing rationale → "".
    """
    verdict = parsed.get("verdict")
    if verdict not in VALID_VERDICTS:
        logger.warning("overlap_assessment_invalid_verdict", action="validation_failed",
                        verdict=verdict, valid=list(VALID_VERDICTS))
        return None

    recommendation = parsed.get("recommendation")
    if recommendation not in VALID_RECOMMENDATIONS:
        logger.warning("overlap_assessment_invalid_recommendation", action="validation_failed",
                        recommendation=recommendation, valid=list(VALID_RECOMMENDATIONS))
        return None

    return {
        "verdict": verdict,
        "shared_topics": _coerce_list(parsed.get("shared_topics")),
        "differentiators_a": _coerce_list(parsed.get("differentiators_a")),
        "differentiators_b": _coerce_list(parsed.get("differentiators_b")),
        "recommendation": recommendation,
        "rationale": parsed.get("rationale") or "",
    }


def _load_analysis_pair(
    pool: ConnectionPool, content_id_a: str, content_id_b: str
) -> tuple[dict | None, dict | None]:
    """Load showroom_analysis rows for both items."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT sa.*, ce.display_name
                   FROM showroom_analysis sa
                   JOIN content_entities ce ON ce.content_id = sa.content_id
                   WHERE sa.content_id IN (%s, %s)""",
                (content_id_a, content_id_b),
            )
            rows = {row["content_id"]: row for row in cur.fetchall()}
    return rows.get(content_id_a), rows.get(content_id_b)


def _fmt_json_field(val: Any) -> str:
    """Format a JSONB field for the prompt — list items or 'None available'."""
    if not val:
        return "None available"
    if isinstance(val, list):
        if val and isinstance(val[0], dict):
            # modules_json or products_json with dicts
            items = []
            for item in val:
                if isinstance(item, dict):
                    items.append(item.get("title") or item.get("name") or json.dumps(item))
                else:
                    items.append(str(item))
            return "\n".join(f"- {i}" for i in items)
        return "\n".join(f"- {i}" for i in val)
    return str(val)


def _build_assessment_prompt(analysis_a: dict, analysis_b: dict) -> str:
    """Format the overlap assessment prompt with both items' data."""
    template = PROMPT_PATH.read_text()
    return template.format(
        display_name_a=analysis_a.get("display_name", "Unknown"),
        learning_objectives_a=_fmt_json_field(analysis_a.get("learning_objectives_json")),
        modules_a=_fmt_json_field(analysis_a.get("modules_json")),
        products_a=_fmt_json_field(analysis_a.get("products_json")),
        summary_a=analysis_a.get("summary") or "No summary available",
        audience_a=_fmt_json_field(analysis_a.get("audience_json")),
        difficulty_a=analysis_a.get("difficulty") or "Unknown",
        duration_a=analysis_a.get("estimated_duration_min") or "Unknown",
        use_cases_a=_fmt_json_field(analysis_a.get("use_cases_json")),
        topics_a=_fmt_json_field(analysis_a.get("topics_json")),
        display_name_b=analysis_b.get("display_name", "Unknown"),
        learning_objectives_b=_fmt_json_field(analysis_b.get("learning_objectives_json")),
        modules_b=_fmt_json_field(analysis_b.get("modules_json")),
        products_b=_fmt_json_field(analysis_b.get("products_json")),
        summary_b=analysis_b.get("summary") or "No summary available",
        audience_b=_fmt_json_field(analysis_b.get("audience_json")),
        difficulty_b=analysis_b.get("difficulty") or "Unknown",
        duration_b=analysis_b.get("estimated_duration_min") or "Unknown",
        use_cases_b=_fmt_json_field(analysis_b.get("use_cases_json")),
        topics_b=_fmt_json_field(analysis_b.get("topics_json")),
    )


def assess_overlap(
    pool: ConnectionPool,
    settings: Settings,
    content_id_a: str,
    content_id_b: str,
) -> dict[str, Any] | None:
    """Assess overlap between two content items. Returns cached result or computes on-demand.

    Returns None if either item lacks analysis data.
    """
    # Normalize ordering to match content_similarity's a < b constraint
    if content_id_a > content_id_b:
        content_id_a, content_id_b = content_id_b, content_id_a

    # Check cache
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT llm_assessment, assessed_at FROM content_similarity
                   WHERE content_id_a = %s AND content_id_b = %s""",
                (content_id_a, content_id_b),
            )
            row = cur.fetchone()

    if row and row.get("llm_assessment"):
        logger.info("overlap_assessment_cached", action="cache_hit",
                     content_id_a=content_id_a, content_id_b=content_id_b)
        return row["llm_assessment"]

    # Load analysis data
    analysis_a, analysis_b = _load_analysis_pair(pool, content_id_a, content_id_b)
    if not analysis_a or not analysis_b:
        logger.info("overlap_assessment_skipped", action="missing_analysis",
                     content_id_a=content_id_a, content_id_b=content_id_b,
                     has_a=analysis_a is not None, has_b=analysis_b is not None)
        return None

    # Build prompt and call LLM
    prompt = _build_assessment_prompt(analysis_a, analysis_b)
    llm_result = call_llm(
        settings=settings,
        model=settings.overlap_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0,
    )

    parsed = parse_analysis_response(llm_result.text)
    if not parsed:
        logger.error("overlap_assessment_parse_failed", action="parse_error",
                      content_id_a=content_id_a, content_id_b=content_id_b,
                      raw_response=llm_result.text[:500])
        return None

    # Validate structure — reject invalid enums, coerce missing arrays
    validated = _validate_assessment(parsed)
    if not validated:
        logger.error("overlap_assessment_validation_failed", action="validation_error",
                      content_id_a=content_id_a, content_id_b=content_id_b,
                      raw_parsed=parsed)
        return None

    # Attach model metadata
    validated["model"] = settings.overlap_model
    validated["tokens"] = {
        "input": llm_result.input_tokens,
        "output": llm_result.output_tokens,
    }

    # Persist
    with pool.connection() as conn:
        conn.execute(
            """UPDATE content_similarity
               SET llm_assessment = %s::jsonb, assessed_at = NOW()
               WHERE content_id_a = %s AND content_id_b = %s""",
            (json.dumps(validated), content_id_a, content_id_b),
        )
        conn.commit()

    logger.info("overlap_assessment_complete", action="assessed",
                 content_id_a=content_id_a, content_id_b=content_id_b,
                 verdict=validated["verdict"],
                 tokens_in=llm_result.input_tokens, tokens_out=llm_result.output_tokens)
    return validated


def batch_assess_overlaps(
    pool: ConnectionPool,
    settings: Settings,
    min_score: float = 0.95,
) -> dict[str, Any]:
    """Batch-assess overlap pairs above min_score that lack an assessment."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT content_id_a, content_id_b, similarity_score
                   FROM content_similarity
                   WHERE relationship_type = 'overlap'
                     AND similarity_score >= %s
                     AND llm_assessment IS NULL
                   ORDER BY similarity_score DESC""",
                (min_score,),
            )
            pairs = cur.fetchall()

    assessed = 0
    skipped = 0
    errors = 0
    total_tokens_in = 0
    total_tokens_out = 0

    for pair in pairs:
        try:
            result = assess_overlap(pool, settings, pair["content_id_a"], pair["content_id_b"])
            if result:
                assessed += 1
                total_tokens_in += result.get("tokens", {}).get("input", 0)
                total_tokens_out += result.get("tokens", {}).get("output", 0)
            else:
                skipped += 1
        except Exception:
            errors += 1
            logger.exception("overlap_assessment_batch_error",
                             action="batch_error",
                             content_id_a=pair["content_id_a"],
                             content_id_b=pair["content_id_b"])

    summary = {
        "pairs_found": len(pairs),
        "assessed": assessed,
        "skipped": skipped,
        "errors": errors,
        "total_tokens": {"input": total_tokens_in, "output": total_tokens_out},
    }
    logger.info("overlap_assessment_batch_complete", action="batch_complete", **summary)
    return summary
```

- [ ] **Step 4: Run all assessment tests**

Run: `cd src/api && python -m pytest tests/test_overlap_assessment.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/prompts/overlap_assessment.txt src/api/rcars/services/overlap_assessment.py src/api/tests/test_overlap_assessment.py
git commit -m "[RHDPCD-614] Add overlap assessment service with prompt, caching, and batch mode"
```

---

### Task 5: API endpoint for on-demand assessment

**Files:**
- Modify: `src/api/rcars/api/routes/admin.py` (add new endpoint after compute-similarity)

**Interfaces:**
- Consumes: `assess_overlap(pool, settings, content_id_a, content_id_b) -> dict | None` (Task 4)
- Produces: `GET /admin/overlap/{content_id_a}/{content_id_b}/assessment` endpoint — used by frontend (Task 7)

- [ ] **Step 1: Write test for the endpoint**

Add to `src/api/tests/test_overlap_assessment.py`:

```python
def test_assessment_endpoint_returns_assessment(db):
    """Verify the endpoint response shape matches what the frontend expects."""
    cid_a, cid_b = _seed_overlap_pair(db)

    assessment = {
        "verdict": "complementary",
        "shared_topics": ["OpenShift"],
        "differentiators_a": ["GitOps"],
        "differentiators_b": ["Troubleshooting"],
        "recommendation": "keep_both",
        "rationale": "Different angles.",
        "model": "claude-sonnet-4-6",
        "tokens": {"input": 500, "output": 200},
    }

    # Simulate a persisted assessment
    with db.pool.connection() as conn:
        conn.execute(
            """UPDATE content_similarity
               SET llm_assessment = %s::jsonb, assessed_at = NOW()
               WHERE content_id_a = %s AND content_id_b = %s""",
            (json.dumps(assessment), cid_a, cid_b),
        )
        conn.commit()

    from rcars.services.overlap_assessment import assess_overlap
    result = assess_overlap(db.pool, Settings(), cid_a, cid_b)
    assert result is not None
    assert result["verdict"] == "complementary"
    assert "tokens" in result
```

- [ ] **Step 2: Add the endpoint**

In `src/api/rcars/api/routes/admin.py`, add the import at the top:

```python
from rcars.services.overlap_assessment import assess_overlap
```

After the `compute_similarity` endpoint (after line 334), add:

```python
@router.get(
    "/overlap/{content_id_a}/{content_id_b}/assessment",
    summary="Get or compute LLM overlap assessment for a pair",
    description="Returns cached assessment if available, otherwise computes on-demand. Returns null assessment with reason if either item lacks analysis data.",
)
async def overlap_assessment(
    request: Request,
    content_id_a: str,
    content_id_b: str,
    user: str = Depends(require_curator),
):
    db = request.app.state.db
    settings = Settings()

    import asyncio
    result = await asyncio.to_thread(
        assess_overlap, db.pool, settings, content_id_a, content_id_b
    )

    if result is None:
        return {"assessment": None, "assessed_at": None, "reason": "missing_analysis"}
    return {"assessment": result, "assessed_at": result.get("assessed_at")}
```

Note: We use `asyncio.to_thread` because `assess_overlap` makes a synchronous LLM call, following the same pattern used in the nightly pipeline for `compute_content_similarity`.

- [ ] **Step 3: Fix the assessed_at field — read from DB not from assessment dict**

The `assessed_at` timestamp is in the DB, not in the assessment dict. Update the endpoint to query it:

```python
@router.get(
    "/overlap/{content_id_a}/{content_id_b}/assessment",
    summary="Get or compute LLM overlap assessment for a pair",
)
async def overlap_assessment(
    request: Request,
    content_id_a: str,
    content_id_b: str,
    user: str = Depends(require_curator),
):
    db = request.app.state.db
    settings = Settings()

    import asyncio
    result = await asyncio.to_thread(
        assess_overlap, db.pool, settings, content_id_a, content_id_b
    )

    if result is None:
        return {"assessment": None, "assessed_at": None, "reason": "missing_analysis"}

    # Read assessed_at from DB
    a, b = (content_id_a, content_id_b) if content_id_a < content_id_b else (content_id_b, content_id_a)
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT assessed_at FROM content_similarity WHERE content_id_a = %s AND content_id_b = %s",
            (a, b),
        )
        row = cur.fetchone()

    return {"assessment": result, "assessed_at": row["assessed_at"] if row else None}
```

- [ ] **Step 4: Run tests**

Run: `cd src/api && python -m pytest tests/test_overlap_assessment.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/api/routes/admin.py src/api/tests/test_overlap_assessment.py
git commit -m "[RHDPCD-614] Add GET /admin/overlap/{a}/{b}/assessment endpoint"
```

---

### Task 6: Nightly pipeline integration

**Files:**
- Modify: `src/api/rcars/workers/ops.py:466` (after similarity step, before "Complete pipeline")

**Interfaces:**
- Consumes: `batch_assess_overlaps(pool, settings, min_score=0.95) -> dict` (Task 4)
- Produces: `assessment` key in the nightly pipeline result dict; progress messages via Redis pub/sub

- [ ] **Step 1: Add batch assessment step after similarity computation**

In `src/api/rcars/workers/ops.py`, add the import near the top where other service imports are:

```python
from rcars.services.overlap_assessment import batch_assess_overlaps
```

After line 465 (the similarity error progress publish), before line 467 (`# Complete pipeline`), add:

```python
    # ── Step 7: Batch LLM overlap assessment (near-duplicates only) ──
    assessment_result = {"status": "skipped"}
    if similarity_result.get("status") == "complete":
        try:
            await publish_progress(wctx.relay, job_id, wctx.db,
                                   phase="pipeline:assessment", status="running",
                                   message="Step 7: Assessing near-duplicate overlaps...")
            assessment_result = await asyncio.to_thread(
                batch_assess_overlaps,
                wctx.db.pool,
                wctx.settings,
                min_score=wctx.settings.similarity_high_threshold,
            )
            assessment_result["status"] = "complete"
            await publish_progress(wctx.relay, job_id, wctx.db,
                                   phase="pipeline:assessment", status="complete",
                                   message=f"Step 7 complete: {assessment_result.get('assessed', 0)} pairs assessed")
            log.info("pipeline_assessment_complete", action="pipeline_step_complete",
                     step="overlap_assessment", **assessment_result)
        except Exception as exc:
            msg = f"Step 7 failed (overlap assessment): {exc}"
            warnings.append(msg)
            log.error("pipeline_assessment_failed", action="pipeline_step_failed",
                      step="overlap_assessment", error=str(exc), traceback=traceback.format_exc())
            assessment_result = {"status": "error", "error": str(exc)}
            await publish_progress(wctx.relay, job_id, wctx.db,
                                   phase="pipeline:assessment", status="failed",
                                   message="Step 7 failed: Overlap assessment failed (non-fatal)")
```

- [ ] **Step 2: Add `assessment` to the pipeline result dict**

In the `result = {` dict (around line 468), add `"assessment": assessment_result,` after `"similarity": similarity_result,`.

- [ ] **Step 3: Run existing tests**

Run: `cd src/api && python -m pytest tests/ -v -k "not integration"`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add src/api/rcars/workers/ops.py
git commit -m "[RHDPCD-614] Add batch overlap assessment as Step 7 in nightly pipeline"
```

---

### Task 7: Frontend — Assessment section in ComparisonDrawer

**Files:**
- Modify: `src/frontend/src/services/api.ts` (add API call)
- Modify: `src/frontend/src/pages/ContentAnalysisPage.tsx` (DrawerPair type, openDrawer, ComparisonDrawer)
- Modify: `src/frontend/src/styles/rcars-app.css` (assessment section styles)

**Interfaces:**
- Consumes: `GET /admin/overlap/{content_id_a}/{content_id_b}/assessment` (Task 5)
- Produces: Assessment section in ComparisonDrawer UI — verdict badge, shared topics, differentiators, recommendation

- [ ] **Step 1: Add API call to api.ts**

In `src/frontend/src/services/api.ts`, after the `computeSimilarity` method (after line 232), add:

```typescript
  getOverlapAssessment: (contentIdA: string, contentIdB: string) =>
    request<{
      assessment: {
        verdict: string
        shared_topics: string[]
        differentiators_a: string[]
        differentiators_b: string[]
        recommendation: string
        rationale: string
        model: string
        tokens: { input: number; output: number }
      } | null
      assessed_at: string | null
      reason?: string
    }>(`/admin/overlap/${encodeURIComponent(contentIdA)}/${encodeURIComponent(contentIdB)}/assessment`),
```

- [ ] **Step 2: Add assessment types and state to DrawerPair**

In `src/frontend/src/pages/ContentAnalysisPage.tsx`, add a new interface after `DrawerPair` (after line 53):

```typescript
interface OverlapAssessment {
  verdict: string
  shared_topics: string[]
  differentiators_a: string[]
  differentiators_b: string[]
  recommendation: string
  rationale: string
}
```

Update the `DrawerPair` interface to add assessment fields:

```typescript
interface DrawerPair {
  item: OverlapItem
  neighbor: NeighborItem
  itemSummary: ItemSummary | null
  neighborSummary: ItemSummary | null
  loading: boolean
  assessment: OverlapAssessment | null
  assessmentLoading: boolean
  assessmentReason: string | null
}
```

- [ ] **Step 3: Update openDrawer to fetch assessment**

In `src/frontend/src/pages/ContentAnalysisPage.tsx`, update the `openDrawer` function (lines 121-141):

```typescript
  const openDrawer = async (item: OverlapItem, neighbor: NeighborItem) => {
    setDrawer({ item, neighbor, itemSummary: null, neighborSummary: null, loading: true,
                assessment: null, assessmentLoading: true, assessmentReason: null })

    const fetchSummary = async (contentId: string): Promise<ItemSummary> => {
      if (detailCache.current[contentId]) return detailCache.current[contentId]
      const detail = await api.getCatalogItem(contentId) as Record<string, unknown>
      const summary = extractSummary(detail)
      detailCache.current[contentId] = summary
      return summary
    }

    try {
      const [itemSummary, neighborSummary] = await Promise.all([
        fetchSummary(item.content_id),
        fetchSummary(neighbor.content_id),
      ])
      setDrawer(prev => prev ? { ...prev, itemSummary, neighborSummary, loading: false } : null)
    } catch {
      setDrawer(prev => prev ? { ...prev, loading: false } : null)
    }

    try {
      const resp = await api.getOverlapAssessment(item.content_id, neighbor.content_id)
      setDrawer(prev => prev ? {
        ...prev,
        assessment: resp.assessment as OverlapAssessment | null,
        assessmentLoading: false,
        assessmentReason: resp.reason || null,
      } : null)
    } catch {
      setDrawer(prev => prev ? { ...prev, assessmentLoading: false } : null)
    }
  }
```

- [ ] **Step 4: Add AssessmentSection component and update ComparisonDrawer**

In `src/frontend/src/pages/ContentAnalysisPage.tsx`, add a new component before the `SummarySection` function (before line 410):

```typescript
function AssessmentSection({ assessment, loading, reason, itemName, neighborName }: {
  assessment: OverlapAssessment | null
  loading: boolean
  reason: string | null
  itemName: string
  neighborName: string
}) {
  if (loading) {
    return (
      <div className="ca-assessment-section">
        <div className="browse-drawer-label">LLM Assessment</div>
        <div className="browse-loading"><Spinner size="sm" /> Analyzing overlap…</div>
      </div>
    )
  }
  if (!assessment) {
    return (
      <div className="ca-assessment-section">
        <div className="browse-drawer-label">LLM Assessment</div>
        <p className="ca-compare-summary" style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>
          {reason === 'missing_analysis' ? 'One or both items have not been analyzed yet.' : 'Assessment unavailable.'}
        </p>
      </div>
    )
  }

  const verdictColor: Record<string, string> = {
    redundant: 'var(--score-red)',
    complementary: 'var(--score-amber)',
    differentiated: 'var(--score-green, #2e7d32)',
  }
  const verdictBg: Record<string, string> = {
    redundant: 'var(--score-red-bg)',
    complementary: 'var(--score-amber-bg)',
    differentiated: 'var(--score-green-bg, #e8f5e9)',
  }

  return (
    <div className="ca-assessment-section">
      <div className="ca-assessment-header">
        <span className="browse-drawer-label">LLM Assessment</span>
        <span
          className="ca-score-badge"
          style={{ color: verdictColor[assessment.verdict] || 'inherit',
                   backgroundColor: verdictBg[assessment.verdict] || 'transparent' }}
        >
          {assessment.verdict}
        </span>
      </div>

      {assessment.shared_topics.length > 0 && (
        <div className="ca-assessment-group">
          <div className="ca-assessment-sublabel">Shared Topics</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {assessment.shared_topics.map(t => (
              <Badge key={t} className="browse-badge">{t}</Badge>
            ))}
          </div>
        </div>
      )}

      <div className="ca-assessment-diff-grid">
        {assessment.differentiators_a.length > 0 && (
          <div className="ca-assessment-group">
            <div className="ca-assessment-sublabel">Unique to {itemName}</div>
            <ul className="ca-assessment-list">
              {assessment.differentiators_a.map(d => <li key={d}>{d}</li>)}
            </ul>
          </div>
        )}
        {assessment.differentiators_b.length > 0 && (
          <div className="ca-assessment-group">
            <div className="ca-assessment-sublabel">Unique to {neighborName}</div>
            <ul className="ca-assessment-list">
              {assessment.differentiators_b.map(d => <li key={d}>{d}</li>)}
            </ul>
          </div>
        )}
      </div>

      <div className="ca-assessment-group">
        <div className="ca-assessment-sublabel">
          Recommendation: <strong>{assessment.recommendation.replace('_', ' ')}</strong>
        </div>
        <p className="ca-compare-summary">{assessment.rationale}</p>
      </div>
    </div>
  )
}
```

Update `ComparisonDrawer` to render `AssessmentSection` after the two `SummarySection` components (inside the `<>` fragment, after the second `SummarySection`):

```tsx
              <AssessmentSection
                assessment={drawer.assessment}
                loading={drawer.assessmentLoading}
                reason={drawer.assessmentReason}
                itemName={drawer.item.display_name}
                neighborName={drawer.neighbor.display_name}
              />
```

- [ ] **Step 5: Add CSS styles**

In `src/frontend/src/styles/rcars-app.css`, after the `.ca-compare-tags` rule (after line 826), add:

```css
.ca-assessment-section {
  padding: 16px 20px;
  border-top: 2px solid var(--border-color);
}
.ca-assessment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.ca-assessment-group { margin-top: 10px; }
.ca-assessment-sublabel {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.ca-assessment-diff-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.ca-assessment-list {
  margin: 4px 0 0 16px;
  padding: 0;
  font-size: 0.85rem;
}
.ca-assessment-list li { margin-bottom: 2px; }
```

- [ ] **Step 6: Verify frontend builds**

Run: `cd src/frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/services/api.ts src/frontend/src/pages/ContentAnalysisPage.tsx src/frontend/src/styles/rcars-app.css
git commit -m "[RHDPCD-614] Add LLM assessment section to ComparisonDrawer"
```

---

### Task 8: Manual integration test and deploy verification

**Files:**
- No new files

**Interfaces:**
- Consumes: All prior tasks
- Produces: Verified working feature end-to-end

- [ ] **Step 1: Run full test suite**

Run: `cd src/api && python -m pytest tests/ -v -k "not integration"`
Expected: All PASS

- [ ] **Step 2: Start dev services and test locally**

Run: `./dev-services.sh start`

1. Open http://localhost:3000, navigate to Content Analysis → Overlap
2. Verify "Moderate" band label (not "Related")
3. Click a score badge to open the ComparisonDrawer
4. Verify the assessment section appears (loading spinner → result or "not yet analyzed" message)
5. Verify verdict badge shows correct color (red/amber/green)

- [ ] **Step 3: Test the API endpoint directly**

Run: `curl -s http://localhost:8080/api/v1/admin/overlap | python -m json.tool | head -20`

Pick two content_ids from the response and test:

Run: `curl -s "http://localhost:8080/api/v1/admin/overlap/{content_id_a}/{content_id_b}/assessment" | python -m json.tool`

Verify response has `assessment` and `assessed_at` fields.

- [ ] **Step 4: Commit any fixes discovered during testing**

If any issues were found, fix and commit with appropriate message.
