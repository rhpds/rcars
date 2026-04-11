# Recommender Redesign — Three-Phase Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace single-call `recommend()` with a three-phase progressive pipeline (vector search → Haiku triage → Sonnet rationale) that returns results in <1s with LLM-refined analysis arriving progressively over ~10s.

**Architecture:** The monolithic `recommender.py` becomes a `recommender/` package with one module per phase. A pipeline generator yields `QueryState` after each phase. The web layer polls for updates and swaps in new HTML at each transition. Hard distance and relevance cutoffs eliminate low-quality results. Haiku does fast triage; Sonnet generates rationale only for top picks.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, HTMX 1.9.12, pgvector, sentence-transformers, Claude Haiku 4.5 (triage), Claude Sonnet 4.6 (rationale), pytest

**Spec:** `docs/superpowers/specs/2026-04-11-recommender-redesign-design.md`

**Test command:** `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/ -q`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/rcars/recommender.py` | Delete | Replaced by `recommender/` package |
| `src/rcars/recommender/__init__.py` | Create | Public API: re-exports `run_query`, `QueryState`, `Candidate` |
| `src/rcars/recommender/models.py` | Create | Dataclasses: `Candidate`, `QueryState` |
| `src/rcars/recommender/vector_search.py` | Create | Phase 1: embedding + pgvector + distance cutoff |
| `src/rcars/recommender/triage.py` | Create | Phase 2: Haiku triage prompt + parsing |
| `src/rcars/recommender/rationale.py` | Create | Phase 3: Sonnet rationale prompt + parsing |
| `src/rcars/recommender/pipeline.py` | Create | Three-phase generator orchestrator |
| `src/rcars/prompts/triage.txt` | Create | Haiku triage prompt template |
| `src/rcars/prompts/rationale.txt` | Create | Sonnet rationale prompt template |
| `src/rcars/prompts/recommend.txt` | Delete | Replaced by triage.txt + rationale.txt |
| `src/rcars/config.py` | Modify | Add vector_cutoff, triage_model, triage_cutoff, rationale_model, rationale_top_n settings |
| `src/rcars/cli.py` | Modify | Update `recommend` command: use `run_query`, add `--cutoff` and `--triage-cutoff` flags |
| `src/rcars/web/routes/advisor.py` | Modify | Replace `recommend()` with `run_query()` generator, progressive `_query_status` updates |
| `src/rcars/web/templates/fragments/rec_card.html` | Modify | Phase-aware card rendering (vector/triaged/analyzing/complete) |
| `src/rcars/web/templates/fragments/rec_list.html` | Modify | Phase status line, fade-out support |
| `src/rcars/web/static/rcars.css` | Modify | Card fade-out transition, analyzing animation |
| `tests/recommender/__init__.py` | Create | Test package |
| `tests/recommender/test_models.py` | Create | Tests for Candidate and QueryState |
| `tests/recommender/test_vector_search.py` | Create | Tests for Phase 1 |
| `tests/recommender/test_triage.py` | Create | Tests for Phase 2 |
| `tests/recommender/test_rationale.py` | Create | Tests for Phase 3 |
| `tests/recommender/test_pipeline.py` | Create | Tests for full pipeline generator |
| `tests/web/test_advisor_progressive.py` | Create | Tests for progressive UI updates |

---

### Task 1: Create `recommender/models.py` — Dataclasses

**Files:**
- Create: `src/rcars/recommender/__init__.py`
- Create: `src/rcars/recommender/models.py`
- Create: `tests/recommender/__init__.py`
- Create: `tests/recommender/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/recommender/__init__.py` (empty file) and `tests/recommender/test_models.py`:

```python
"""Tests for recommender data models."""

from rcars.recommender.models import Candidate, QueryState


def test_candidate_defaults():
    c = Candidate(
        ci_name="test-ci",
        display_name="Test CI",
        category="workshop",
        summary="A test workshop",
        topics=["openshift"],
        products=["OCP"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
        vector_distance=0.3,
        vector_similarity_pct=85,
    )
    assert c.ci_name == "test-ci"
    assert c.vector_similarity_pct == 85
    # Triage fields default to None
    assert c.relevance_score is None
    assert c.relevant is None
    assert c.one_line_reason is None
    # Rationale fields default to None
    assert c.rationale is None
    assert c.suggested_format is None
    assert c.duration_notes is None
    assert c.caveats is None


def test_candidate_vector_similarity_calculation():
    """Verify the similarity % formula: round((1 - distance/2) * 100)."""
    # distance=0.0 → 100%, distance=0.55 → 72%, distance=1.0 → 50%
    assert Candidate.similarity_pct(0.0) == 100
    assert Candidate.similarity_pct(0.55) == 72
    assert Candidate.similarity_pct(1.0) == 50


def test_query_state_defaults():
    state = QueryState(phase="SUBMITTED", candidates=[])
    assert state.phase == "SUBMITTED"
    assert state.candidates == []
    assert state.overall_assessment is None
    assert state.content_gaps is None
    assert state.timings == {}


def test_query_state_with_candidates():
    c = Candidate(
        ci_name="x", display_name="X", category="demo",
        summary="s", topics=[], products=[], difficulty="",
        duration_min=None, content_type="demo",
        vector_distance=0.4, vector_similarity_pct=80,
    )
    state = QueryState(phase="VECTOR_DONE", candidates=[c])
    assert len(state.candidates) == 1
    assert state.candidates[0].ci_name == "x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rcars.recommender.models'`

- [ ] **Step 3: Create the models module**

Create `src/rcars/recommender/__init__.py`:

```python
"""RCARS recommendation engine — three-phase pipeline."""
```

Create `src/rcars/recommender/models.py`:

```python
"""Data models for the recommendation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Candidate:
    """A catalog item moving through the recommendation pipeline.

    Fields are populated progressively: vector fields first, then triage,
    then rationale.
    """

    ci_name: str
    display_name: str
    category: str
    summary: str
    topics: list[str]
    products: list[str]
    difficulty: str
    duration_min: int | None
    content_type: str
    vector_distance: float
    vector_similarity_pct: int

    # Populated after Phase 2 (Haiku triage)
    relevance_score: int | None = None
    relevant: bool | None = None
    one_line_reason: str | None = None

    # Populated after Phase 3 (Sonnet rationale)
    rationale: str | None = None
    suggested_format: str | None = None
    duration_notes: str | None = None
    caveats: str | None = None

    @staticmethod
    def similarity_pct(distance: float) -> int:
        """Convert cosine distance to similarity percentage."""
        return round((1 - distance / 2) * 100)


@dataclass
class QueryState:
    """State of a recommendation query at a pipeline phase boundary.

    Yielded by the pipeline generator after each phase completes.
    """

    phase: str  # SUBMITTED | VECTOR_DONE | TRIAGE_DONE | COMPLETE | NO_MATCHES
    candidates: list[Candidate]
    overall_assessment: str | None = None
    content_gaps: list[str] | None = None
    timings: dict[str, float] = field(default_factory=dict)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_models.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/rcars/recommender/__init__.py src/rcars/recommender/models.py \
        tests/recommender/__init__.py tests/recommender/test_models.py
git commit -m "recommender: Add Candidate and QueryState data models"
```

---

### Task 2: Add Pipeline Configuration to `config.py`

**Files:**
- Modify: `src/rcars/config.py`
- Create: `tests/recommender/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/recommender/test_config.py`:

```python
"""Tests for recommender pipeline configuration."""

import os
from unittest.mock import patch

from rcars.config import Settings


def test_default_pipeline_settings():
    s = Settings()
    assert s.vector_cutoff == 0.55
    assert s.triage_model == "claude-haiku-4-5"
    assert s.triage_cutoff == 30
    assert s.rationale_model == "claude-sonnet-4-6"
    assert s.rationale_top_n == 5


def test_pipeline_settings_from_env():
    env = {
        "RCARS_VECTOR_CUTOFF": "0.7",
        "RCARS_TRIAGE_MODEL": "claude-3-5-haiku",
        "RCARS_TRIAGE_CUTOFF": "50",
        "RCARS_RATIONALE_MODEL": "claude-sonnet-4-6",
        "RCARS_RATIONALE_TOP_N": "3",
    }
    with patch.dict(os.environ, env):
        s = Settings()
    assert s.vector_cutoff == 0.7
    assert s.triage_model == "claude-3-5-haiku"
    assert s.triage_cutoff == 50
    assert s.rationale_model == "claude-sonnet-4-6"
    assert s.rationale_top_n == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_config.py -v`
Expected: FAIL — `AttributeError: 'Settings' has no attribute 'vector_cutoff'`

- [ ] **Step 3: Add pipeline settings to config.py**

Add the following fields to the `Settings` dataclass in `src/rcars/config.py`, after the `clone_dir` field (line 36):

```python
    # Recommender pipeline
    vector_cutoff: float = field(
        default_factory=lambda: float(os.environ.get("RCARS_VECTOR_CUTOFF", "0.55"))
    )
    triage_model: str = field(
        default_factory=lambda: os.environ.get("RCARS_TRIAGE_MODEL", "claude-haiku-4-5")
    )
    triage_cutoff: int = field(
        default_factory=lambda: int(os.environ.get("RCARS_TRIAGE_CUTOFF", "30"))
    )
    rationale_model: str = field(
        default_factory=lambda: os.environ.get("RCARS_RATIONALE_MODEL", "claude-sonnet-4-6")
    )
    rationale_top_n: int = field(
        default_factory=lambda: int(os.environ.get("RCARS_RATIONALE_TOP_N", "5"))
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_config.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/rcars/config.py tests/recommender/test_config.py
git commit -m "config: Add recommender pipeline settings (cutoffs, models)"
```

---

### Task 3: Create `recommender/vector_search.py` — Phase 1

**Files:**
- Create: `src/rcars/recommender/vector_search.py`
- Create: `tests/recommender/test_vector_search.py`

- [ ] **Step 1: Write the failing test**

Create `tests/recommender/test_vector_search.py`:

```python
"""Tests for Phase 1 — vector search with distance cutoff."""

from unittest.mock import MagicMock, patch

from rcars.recommender.vector_search import search
from rcars.recommender.models import Candidate


def _mock_db(rows):
    """Create a mock Database that returns given rows from search_embeddings."""
    db = MagicMock()
    db.search_embeddings.return_value = rows
    # Mock get_showroom_analysis to return analysis data for each CI
    def mock_analysis(ci_name):
        return {
            "content_type": "workshop",
            "summary": f"Summary for {ci_name}",
            "difficulty": "beginner",
            "estimated_duration_min": 60,
            "topics_json": ["openshift"],
            "products_json": ["OCP"],
            "audience_json": ["developers"],
        }
    db.get_showroom_analysis.side_effect = mock_analysis
    return db


def _row(ci_name, distance):
    return {
        "ci_name": ci_name,
        "display_name": ci_name.replace("-", " ").title(),
        "category": "workshop",
        "stage": "prod",
        "is_published": False,
        "published_ci_name": None,
        "base_ci_name": None,
        "content_text": "some text",
        "module_title": None,
        "distance": distance,
    }


@patch("rcars.recommender.vector_search.generate_embedding", return_value=[0.1] * 384)
def test_search_returns_candidates_under_cutoff(mock_emb):
    rows = [_row("good-ci", 0.3), _row("ok-ci", 0.5), _row("bad-ci", 0.8)]
    db = _mock_db(rows)

    state = search("test query", db, limit=10, distance_cutoff=0.55)

    assert state.phase == "VECTOR_DONE"
    assert len(state.candidates) == 2
    assert state.candidates[0].ci_name == "good-ci"
    assert state.candidates[1].ci_name == "ok-ci"
    assert state.candidates[0].vector_similarity_pct == Candidate.similarity_pct(0.3)
    assert "vector_search" in state.timings


@patch("rcars.recommender.vector_search.generate_embedding", return_value=[0.1] * 384)
def test_search_no_matches_returns_no_matches_phase(mock_emb):
    rows = [_row("bad-ci", 0.8), _row("worse-ci", 0.9)]
    db = _mock_db(rows)

    state = search("test query", db, limit=10, distance_cutoff=0.55)

    assert state.phase == "NO_MATCHES"
    assert len(state.candidates) == 0


@patch("rcars.recommender.vector_search.generate_embedding", return_value=[0.1] * 384)
def test_search_empty_db_returns_no_matches(mock_emb):
    db = _mock_db([])

    state = search("test query", db, limit=10, distance_cutoff=0.55)

    assert state.phase == "NO_MATCHES"
    assert len(state.candidates) == 0


@patch("rcars.recommender.vector_search.generate_embedding", return_value=[0.1] * 384)
def test_search_enriches_candidates_with_analysis(mock_emb):
    rows = [_row("my-ci", 0.4)]
    db = _mock_db(rows)

    state = search("test query", db, limit=10, distance_cutoff=0.55)

    c = state.candidates[0]
    assert c.summary == "Summary for my-ci"
    assert c.topics == ["openshift"]
    assert c.products == ["OCP"]
    assert c.difficulty == "beginner"
    assert c.duration_min == 60
    assert c.content_type == "workshop"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_vector_search.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rcars.recommender.vector_search'`

- [ ] **Step 3: Implement vector_search.py**

Create `src/rcars/recommender/vector_search.py`:

```python
"""Phase 1 — vector search with distance cutoff."""

import logging
import time

from rcars.analyzer import generate_embedding
from rcars.db import Database
from rcars.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)


def search(
    query: str,
    db: Database,
    limit: int = 10,
    prod_only: bool = True,
    distance_cutoff: float = 0.55,
) -> QueryState:
    """Generate query embedding, search pgvector, apply distance cutoff.

    Returns QueryState with phase VECTOR_DONE or NO_MATCHES.
    """
    t0 = time.monotonic()

    query_embedding = generate_embedding(query)

    rows = db.search_embeddings(
        query_embedding=query_embedding,
        limit=limit,
        prod_only=prod_only,
    )

    candidates = []
    for row in rows:
        distance = row["distance"]
        if distance > distance_cutoff:
            continue

        ci_name = row["ci_name"]
        analysis = db.get_showroom_analysis(ci_name)

        candidates.append(Candidate(
            ci_name=ci_name,
            display_name=row.get("display_name", ci_name),
            category=row.get("category", ""),
            summary=(analysis or {}).get("summary", ""),
            topics=(analysis or {}).get("topics_json", []) or [],
            products=(analysis or {}).get("products_json", []) or [],
            difficulty=(analysis or {}).get("difficulty", ""),
            duration_min=(analysis or {}).get("estimated_duration_min"),
            content_type=(analysis or {}).get("content_type", ""),
            vector_distance=distance,
            vector_similarity_pct=Candidate.similarity_pct(distance),
        ))

    elapsed = time.monotonic() - t0
    phase = "VECTOR_DONE" if candidates else "NO_MATCHES"

    log.info(
        "vector search: %d candidates (cutoff=%.2f, elapsed=%.3fs)",
        len(candidates), distance_cutoff, elapsed,
    )

    return QueryState(
        phase=phase,
        candidates=candidates,
        timings={"vector_search": round(elapsed, 3)},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_vector_search.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/rcars/recommender/vector_search.py tests/recommender/test_vector_search.py
git commit -m "recommender: Add Phase 1 — vector search with distance cutoff"
```

---

### Task 4: Create Triage Prompt and `recommender/triage.py` — Phase 2

**Files:**
- Create: `src/rcars/prompts/triage.txt`
- Create: `src/rcars/recommender/triage.py`
- Create: `tests/recommender/test_triage.py`

- [ ] **Step 1: Create the triage prompt template**

Create `src/rcars/prompts/triage.txt`:

```
You are evaluating Red Hat Demo Platform (RHDP) catalog items for relevance to a user's request.

Be strict: a partial topic overlap is not relevance. If the content does not meaningfully address what the user is asking for, mark it as not relevant. A workshop about OpenShift is not relevant to a request for Ansible content just because both are Red Hat products.

## Request

{request_description}

## Candidates

{candidates}

For each candidate, evaluate whether its content directly addresses the request. Return ONLY valid JSON (no markdown fences, no explanation):

[
  {
    "ci_name": "the-ci-name",
    "relevance_score": 85,
    "relevant": true,
    "one_line_reason": "Direct match — Ansible automation workshop with AAP 2.x hands-on labs"
  }
]

Rules:
- relevance_score: 0–100. Score based on how well the content matches the request, not general quality.
- relevant: true if score >= 30, false otherwise.
- one_line_reason: One sentence explaining the score. Be specific about what matches or doesn't match.
- Return an entry for EVERY candidate, even if not relevant.
```

- [ ] **Step 2: Write the failing test**

Create `tests/recommender/test_triage.py`:

```python
"""Tests for Phase 2 — Haiku triage."""

import json
from unittest.mock import MagicMock

from rcars.recommender.triage import triage, format_triage_candidates
from rcars.recommender.models import Candidate, QueryState


def _candidate(ci_name, summary="A workshop", topics=None):
    return Candidate(
        ci_name=ci_name,
        display_name=ci_name.replace("-", " ").title(),
        category="workshop",
        summary=summary,
        topics=topics or ["openshift"],
        products=["OCP"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
        vector_distance=0.3,
        vector_similarity_pct=85,
    )


def _mock_client(response_json):
    """Create a mock Anthropic client that returns given JSON."""
    client = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps(response_json)
    response = MagicMock()
    response.content = [content_block]
    client.messages.create.return_value = response
    return client


def test_triage_filters_irrelevant_candidates():
    candidates = [_candidate("good-ci"), _candidate("bad-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates)

    haiku_response = [
        {"ci_name": "good-ci", "relevance_score": 85, "relevant": True,
         "one_line_reason": "Direct Ansible match"},
        {"ci_name": "bad-ci", "relevance_score": 15, "relevant": False,
         "one_line_reason": "No Ansible content"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert result.phase == "TRIAGE_DONE"
    assert len(result.candidates) == 1
    assert result.candidates[0].ci_name == "good-ci"
    assert result.candidates[0].relevance_score == 85
    assert result.candidates[0].one_line_reason == "Direct Ansible match"
    assert "triage" in result.timings


def test_triage_all_irrelevant_returns_no_matches():
    candidates = [_candidate("bad-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates)

    haiku_response = [
        {"ci_name": "bad-ci", "relevance_score": 10, "relevant": False,
         "one_line_reason": "No match"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert result.phase == "NO_MATCHES"
    assert len(result.candidates) == 0


def test_triage_sorts_by_relevance_score():
    candidates = [_candidate("b-ci"), _candidate("a-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates)

    haiku_response = [
        {"ci_name": "b-ci", "relevance_score": 60, "relevant": True,
         "one_line_reason": "Partial match"},
        {"ci_name": "a-ci", "relevance_score": 90, "relevant": True,
         "one_line_reason": "Strong match"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert result.candidates[0].ci_name == "a-ci"
    assert result.candidates[1].ci_name == "b-ci"


def test_format_triage_candidates_compact():
    c = _candidate("test-ci", summary="Learn OpenShift basics", topics=["openshift", "containers"])
    text = format_triage_candidates([c])
    assert "test-ci" in text
    assert "Learn OpenShift basics" in text
    assert "openshift" in text
    # Should NOT contain full analysis fields like learning objectives
    assert "objectives" not in text.lower()


def test_triage_handles_missing_ci_in_response():
    """If Haiku omits a candidate from its response, treat it as irrelevant."""
    candidates = [_candidate("a-ci"), _candidate("b-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates)

    # Haiku only returns one entry
    haiku_response = [
        {"ci_name": "a-ci", "relevance_score": 80, "relevant": True,
         "one_line_reason": "Good match"},
    ]
    client = _mock_client(haiku_response)

    result = triage(state, client, triage_cutoff=30)

    assert len(result.candidates) == 1
    assert result.candidates[0].ci_name == "a-ci"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_triage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rcars.recommender.triage'`

- [ ] **Step 4: Implement triage.py**

Create `src/rcars/recommender/triage.py`:

```python
"""Phase 2 — Haiku triage for relevance scoring."""

import json
import logging
import time
from pathlib import Path

from rcars.analyzer import parse_analysis_response
from rcars.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)

TRIAGE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "triage.txt"


def format_triage_candidates(candidates: list[Candidate]) -> str:
    """Format candidates compactly for the triage prompt."""
    parts = []
    for i, c in enumerate(candidates, 1):
        parts.append(
            f"--- Candidate {i} ---\n"
            f"CI Name: {c.ci_name}\n"
            f"Display Name: {c.display_name}\n"
            f"Summary: {c.summary}\n"
            f"Topics: {', '.join(c.topics)}\n"
            f"Products: {', '.join(c.products)}\n"
            f"Category: {c.category}\n"
            f"Content Type: {c.content_type}"
        )
    return "\n\n".join(parts)


def triage(
    state: QueryState,
    anthropic_client,
    model: str = "claude-haiku-4-5",
    triage_cutoff: int = 30,
) -> QueryState:
    """Send candidates to Haiku for relevance triage.

    Returns QueryState with phase TRIAGE_DONE or NO_MATCHES.
    Candidates below triage_cutoff or marked irrelevant are removed.
    Survivors are sorted by relevance_score descending.
    """
    t0 = time.monotonic()

    template = TRIAGE_PROMPT_PATH.read_text()
    candidates_text = format_triage_candidates(state.candidates)

    prompt = (
        template
        .replace("{request_description}", state.query if hasattr(state, "query") else "")
        .replace("{candidates}", candidates_text)
    )

    response = anthropic_client.messages.create(
        model=model,
        max_tokens=2048,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text
    triage_results = parse_analysis_response(response_text)

    # Build lookup by ci_name
    if isinstance(triage_results, list):
        scores_by_ci = {r["ci_name"]: r for r in triage_results}
    elif isinstance(triage_results, dict) and "recommendations" in triage_results:
        scores_by_ci = {r["ci_name"]: r for r in triage_results["recommendations"]}
    else:
        scores_by_ci = {}

    survivors = []
    for candidate in state.candidates:
        score_data = scores_by_ci.get(candidate.ci_name)
        if not score_data:
            log.debug("triage: %s not in Haiku response, treating as irrelevant", candidate.ci_name)
            continue

        relevance = score_data.get("relevance_score", 0)
        relevant = score_data.get("relevant", False)

        if not relevant or relevance < triage_cutoff:
            log.debug("triage: %s filtered (score=%d, relevant=%s)", candidate.ci_name, relevance, relevant)
            continue

        candidate.relevance_score = relevance
        candidate.relevant = True
        candidate.one_line_reason = score_data.get("one_line_reason", "")
        survivors.append(candidate)

    # Sort by relevance score descending
    survivors.sort(key=lambda c: c.relevance_score or 0, reverse=True)

    elapsed = time.monotonic() - t0
    phase = "TRIAGE_DONE" if survivors else "NO_MATCHES"

    log.info(
        "triage: %d/%d candidates survived (cutoff=%d, elapsed=%.3fs)",
        len(survivors), len(state.candidates), triage_cutoff, elapsed,
    )

    return QueryState(
        phase=phase,
        candidates=survivors,
        timings={**state.timings, "triage": round(elapsed, 3)},
    )
```

- [ ] **Step 5: The triage function references `state.query` but QueryState doesn't have a `query` field. Add it.**

Edit `src/rcars/recommender/models.py` — add `query` field to `QueryState`:

```python
@dataclass
class QueryState:
    """State of a recommendation query at a pipeline phase boundary."""

    phase: str  # SUBMITTED | VECTOR_DONE | TRIAGE_DONE | COMPLETE | NO_MATCHES
    candidates: list[Candidate]
    query: str = ""
    overall_assessment: str | None = None
    content_gaps: list[str] | None = None
    timings: dict[str, float] = field(default_factory=dict)
```

Update `src/rcars/recommender/vector_search.py` — pass query to QueryState:

In the `return QueryState(...)` call at the end of `search()`, add `query=query`:

```python
    return QueryState(
        phase=phase,
        candidates=candidates,
        query=query,
        timings={"vector_search": round(elapsed, 3)},
    )
```

Update `triage()` in `src/rcars/recommender/triage.py` — carry query forward:

In the `return QueryState(...)` call, add `query=state.query`:

```python
    return QueryState(
        phase=phase,
        candidates=survivors,
        query=state.query,
        timings={**state.timings, "triage": round(elapsed, 3)},
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_triage.py tests/recommender/test_vector_search.py tests/recommender/test_models.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/rcars/prompts/triage.txt src/rcars/recommender/triage.py \
        src/rcars/recommender/models.py src/rcars/recommender/vector_search.py \
        tests/recommender/test_triage.py
git commit -m "recommender: Add Phase 2 — Haiku triage with relevance cutoff"
```

---

### Task 5: Create Rationale Prompt and `recommender/rationale.py` — Phase 3

**Files:**
- Create: `src/rcars/prompts/rationale.txt`
- Create: `src/rcars/recommender/rationale.py`
- Create: `tests/recommender/test_rationale.py`

- [ ] **Step 1: Create the rationale prompt template**

Create `src/rcars/prompts/rationale.txt`:

```
You are a Red Hat Demo Platform (RHDP) content advisor. These candidates have been pre-screened as relevant to the request below. For each one, provide a detailed analysis explaining why it fits and how to use it effectively.

## Request

{request_description}

## Candidates

{candidates}

For each candidate, provide:
- rationale: 2-3 sentences explaining why this is a good fit and how to use it for the request
- suggested_format: one of "booth_demo", "hands_on_lab", or "presentation"
- duration_notes: How to adapt timing for the context (e.g. "Full 90-min workshop or truncate to 45-min highlights")
- caveats: Any concerns, gaps, prerequisite knowledge, or things to watch for. Empty string if none.

Also provide:
- overall_assessment: Structured summary using markdown. Start with 1-2 sentence overview, then use **bold labels** and bullet lists to organize key points. Include **Top Picks:** with bullets, **Content Gaps:** if any topics are missing, and **Suggestions:** with actionable next steps.
- content_gaps: Array of topics the user requested but no candidate covers well. Empty array if all topics are covered.

Return ONLY valid JSON (no markdown fences):
{
  "recommendations": [
    {
      "ci_name": "the-ci-name",
      "rationale": "...",
      "suggested_format": "hands_on_lab",
      "duration_notes": "...",
      "caveats": ""
    }
  ],
  "overall_assessment": "...",
  "content_gaps": []
}
```

- [ ] **Step 2: Write the failing test**

Create `tests/recommender/test_rationale.py`:

```python
"""Tests for Phase 3 — Sonnet rationale generation."""

import json
from unittest.mock import MagicMock

from rcars.recommender.rationale import generate_rationale, format_rationale_candidates
from rcars.recommender.models import Candidate, QueryState


def _candidate(ci_name, relevance_score=85):
    return Candidate(
        ci_name=ci_name,
        display_name=ci_name.replace("-", " ").title(),
        category="workshop",
        summary=f"Workshop about {ci_name}",
        topics=["openshift"],
        products=["OCP"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
        vector_distance=0.3,
        vector_similarity_pct=85,
        relevance_score=relevance_score,
        relevant=True,
        one_line_reason="Good match",
    )


def _mock_analysis():
    return {
        "content_type": "workshop",
        "summary": "A workshop",
        "difficulty": "beginner",
        "estimated_duration_min": 60,
        "topics_json": ["openshift"],
        "products_json": ["OCP"],
        "audience_json": ["developers"],
        "learning_objectives_json": {"stated": ["Learn OCP"], "inferred": []},
        "event_fit_json": {"summit": "good"},
        "modules_json": [{"title": "Module 1", "topics": ["basics"]}],
    }


def _mock_client(response_json):
    client = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps(response_json)
    response = MagicMock()
    response.content = [content_block]
    client.messages.create.return_value = response
    return client


def _mock_db():
    db = MagicMock()
    db.get_showroom_analysis.return_value = _mock_analysis()
    return db


def test_generate_rationale_enriches_candidates():
    candidates = [_candidate("good-ci")]
    state = QueryState(phase="TRIAGE_DONE", candidates=candidates, query="openshift workshop")

    sonnet_response = {
        "recommendations": [
            {
                "ci_name": "good-ci",
                "rationale": "This workshop covers core OpenShift concepts.",
                "suggested_format": "hands_on_lab",
                "duration_notes": "90 min full, 45 min abbreviated",
                "caveats": "",
            }
        ],
        "overall_assessment": "**Top Pick:** good-ci covers the request well.",
        "content_gaps": [],
    }
    client = _mock_client(sonnet_response)
    db = _mock_db()

    result = generate_rationale(state, db, client, top_n=5)

    assert result.phase == "COMPLETE"
    assert result.candidates[0].rationale == "This workshop covers core OpenShift concepts."
    assert result.candidates[0].suggested_format == "hands_on_lab"
    assert result.candidates[0].duration_notes == "90 min full, 45 min abbreviated"
    assert result.overall_assessment == "**Top Pick:** good-ci covers the request well."
    assert result.content_gaps == []
    assert "rationale" in result.timings


def test_generate_rationale_limits_to_top_n():
    candidates = [_candidate(f"ci-{i}", 90 - i * 10) for i in range(6)]
    state = QueryState(phase="TRIAGE_DONE", candidates=candidates, query="test")

    sonnet_response = {
        "recommendations": [
            {"ci_name": f"ci-{i}", "rationale": f"Analysis {i}",
             "suggested_format": "hands_on_lab", "duration_notes": "", "caveats": ""}
            for i in range(3)
        ],
        "overall_assessment": "Assessment.",
        "content_gaps": [],
    }
    client = _mock_client(sonnet_response)
    db = _mock_db()

    result = generate_rationale(state, db, client, top_n=3)

    # All 6 candidates should be in the result (non-top-n keep triage data)
    assert len(result.candidates) == 6
    # Only top 3 should have rationale
    with_rationale = [c for c in result.candidates if c.rationale is not None]
    assert len(with_rationale) == 3


def test_format_rationale_candidates_includes_full_analysis():
    c = _candidate("test-ci")
    analysis = _mock_analysis()
    text = format_rationale_candidates([c], {"test-ci": analysis})
    assert "test-ci" in text
    assert "Learn OCP" in text
    assert "Module 1" in text
```

- [ ] **Step 3: Run test to verify it fails**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_rationale.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rcars.recommender.rationale'`

- [ ] **Step 4: Implement rationale.py**

Create `src/rcars/recommender/rationale.py`:

```python
"""Phase 3 — Sonnet rationale generation for top candidates."""

import json
import logging
import time
from pathlib import Path
from typing import Any

from rcars.analyzer import parse_analysis_response
from rcars.db import Database
from rcars.recommender.models import Candidate, QueryState

log = logging.getLogger(__name__)

RATIONALE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "rationale.txt"


def format_rationale_candidates(
    candidates: list[Candidate],
    analyses: dict[str, dict[str, Any]],
) -> str:
    """Format candidates with full analysis data for the rationale prompt."""
    parts = []
    for i, c in enumerate(candidates, 1):
        analysis = analyses.get(c.ci_name, {})
        lines = [
            f"--- Candidate {i} ---",
            f"CI Name: {c.ci_name}",
            f"Display Name: {c.display_name}",
            f"Category: {c.category}",
            f"Content Type: {c.content_type}",
            f"Summary: {c.summary}",
            f"Difficulty: {c.difficulty}",
            f"Duration: {c.duration_min or '?'} min",
            f"Topics: {', '.join(c.topics)}",
            f"Products: {', '.join(c.products)}",
        ]

        audience = analysis.get("audience_json", [])
        if audience:
            lines.append(f"Audience: {', '.join(audience)}")

        objectives = analysis.get("learning_objectives_json", {})
        if isinstance(objectives, dict):
            stated = objectives.get("stated", [])
            inferred = objectives.get("inferred", [])
            if stated:
                lines.append(f"Stated Objectives: {'; '.join(stated)}")
            if inferred:
                lines.append(f"Inferred Objectives: {'; '.join(inferred)}")

        modules = analysis.get("modules_json", [])
        if modules:
            mod_titles = [m.get("title", "") for m in modules if m.get("title")]
            if mod_titles:
                lines.append(f"Modules: {'; '.join(mod_titles)}")

        event_fit = analysis.get("event_fit_json", {})
        if event_fit:
            lines.append(f"Event Fit: {json.dumps(event_fit)}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def generate_rationale(
    state: QueryState,
    db: Database,
    anthropic_client,
    model: str = "claude-sonnet-4-6",
    top_n: int = 5,
) -> QueryState:
    """Generate Sonnet rationale for top candidates.

    Only the top_n candidates (by relevance_score) are sent to Sonnet.
    All candidates are preserved in the result — non-top-n keep their
    triage data but get no rationale.

    Returns QueryState with phase COMPLETE.
    """
    t0 = time.monotonic()

    # Select top candidates for rationale
    top_candidates = state.candidates[:top_n]
    remaining = state.candidates[top_n:]

    # Fetch full analysis for top candidates
    analyses = {}
    for c in top_candidates:
        analysis = db.get_showroom_analysis(c.ci_name)
        if analysis:
            analyses[c.ci_name] = analysis

    # Build prompt
    template = RATIONALE_PROMPT_PATH.read_text()
    candidates_text = format_rationale_candidates(top_candidates, analyses)

    prompt = (
        template
        .replace("{request_description}", state.query)
        .replace("{candidates}", candidates_text)
    )

    response = anthropic_client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    result = parse_analysis_response(response.content[0].text)

    # Apply rationale to candidates
    if result:
        recs_by_ci = {
            r["ci_name"]: r
            for r in result.get("recommendations", [])
        }
        for c in top_candidates:
            rec = recs_by_ci.get(c.ci_name, {})
            c.rationale = rec.get("rationale")
            c.suggested_format = rec.get("suggested_format")
            c.duration_notes = rec.get("duration_notes")
            c.caveats = rec.get("caveats")

    elapsed = time.monotonic() - t0

    log.info(
        "rationale: generated for %d candidates (elapsed=%.3fs)",
        len(top_candidates), elapsed,
    )

    return QueryState(
        phase="COMPLETE",
        candidates=top_candidates + remaining,
        query=state.query,
        overall_assessment=result.get("overall_assessment") if result else None,
        content_gaps=result.get("content_gaps") if result else None,
        timings={**state.timings, "rationale": round(elapsed, 3)},
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_rationale.py -v`
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/rcars/prompts/triage.txt src/rcars/prompts/rationale.txt \
        src/rcars/recommender/rationale.py tests/recommender/test_rationale.py
git commit -m "recommender: Add Phase 3 — Sonnet rationale for top picks"
```

---

### Task 6: Create `recommender/pipeline.py` — Three-Phase Orchestrator

**Files:**
- Create: `src/rcars/recommender/pipeline.py`
- Modify: `src/rcars/recommender/__init__.py`
- Create: `tests/recommender/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

Create `tests/recommender/test_pipeline.py`:

```python
"""Tests for the three-phase pipeline orchestrator."""

import json
from unittest.mock import MagicMock, patch

from rcars.recommender.pipeline import run_query
from rcars.recommender.models import Candidate, QueryState
from rcars.config import Settings


def _mock_settings():
    s = MagicMock(spec=Settings)
    s.vector_cutoff = 0.55
    s.triage_model = "claude-haiku-4-5"
    s.triage_cutoff = 30
    s.rationale_model = "claude-sonnet-4-6"
    s.rationale_top_n = 5
    return s


def _make_vector_state(n_candidates=3):
    candidates = [
        Candidate(
            ci_name=f"ci-{i}", display_name=f"CI {i}", category="workshop",
            summary=f"Summary {i}", topics=["openshift"], products=["OCP"],
            difficulty="beginner", duration_min=60, content_type="workshop",
            vector_distance=0.3, vector_similarity_pct=85,
        )
        for i in range(n_candidates)
    ]
    return QueryState(phase="VECTOR_DONE", candidates=candidates, query="test query")


@patch("rcars.recommender.pipeline.generate_rationale")
@patch("rcars.recommender.pipeline.triage_phase")
@patch("rcars.recommender.pipeline.vector_search")
def test_pipeline_yields_three_states(mock_vs, mock_triage, mock_rationale):
    vector_state = _make_vector_state(3)
    triage_state = QueryState(
        phase="TRIAGE_DONE", candidates=vector_state.candidates[:2], query="test query",
    )
    complete_state = QueryState(
        phase="COMPLETE", candidates=triage_state.candidates, query="test query",
        overall_assessment="Assessment.",
    )

    mock_vs.return_value = vector_state
    mock_triage.return_value = triage_state
    mock_rationale.return_value = complete_state

    settings = _mock_settings()
    states = list(run_query("test query", MagicMock(), MagicMock(), settings))

    assert len(states) == 3
    assert states[0].phase == "VECTOR_DONE"
    assert states[1].phase == "TRIAGE_DONE"
    assert states[2].phase == "COMPLETE"


@patch("rcars.recommender.pipeline.vector_search")
def test_pipeline_stops_at_no_matches_phase1(mock_vs):
    mock_vs.return_value = QueryState(phase="NO_MATCHES", candidates=[], query="test")

    settings = _mock_settings()
    states = list(run_query("bad query", MagicMock(), MagicMock(), settings))

    assert len(states) == 1
    assert states[0].phase == "NO_MATCHES"


@patch("rcars.recommender.pipeline.triage_phase")
@patch("rcars.recommender.pipeline.vector_search")
def test_pipeline_stops_at_no_matches_phase2(mock_vs, mock_triage):
    mock_vs.return_value = _make_vector_state(2)
    mock_triage.return_value = QueryState(phase="NO_MATCHES", candidates=[], query="test")

    settings = _mock_settings()
    states = list(run_query("filtered query", MagicMock(), MagicMock(), settings))

    assert len(states) == 2
    assert states[0].phase == "VECTOR_DONE"
    assert states[1].phase == "NO_MATCHES"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rcars.recommender.pipeline'`

- [ ] **Step 3: Implement pipeline.py**

Create `src/rcars/recommender/pipeline.py`:

```python
"""Three-phase recommendation pipeline orchestrator."""

import logging
from collections.abc import Generator

from rcars.config import Settings
from rcars.db import Database
from rcars.recommender.models import QueryState
from rcars.recommender.vector_search import search as vector_search
from rcars.recommender.triage import triage as triage_phase
from rcars.recommender.rationale import generate_rationale

log = logging.getLogger(__name__)


def run_query(
    query: str,
    db: Database,
    anthropic_client,
    settings: Settings,
    prod_only: bool = True,
) -> Generator[QueryState, None, None]:
    """Run the three-phase recommendation pipeline.

    Yields QueryState after each phase completes:
    1. VECTOR_DONE — candidates from pgvector with distance cutoff
    2. TRIAGE_DONE — candidates scored and filtered by Haiku
    3. COMPLETE — top candidates enriched with Sonnet rationale

    Stops early with NO_MATCHES if any phase produces zero candidates.
    """
    # Phase 1: Vector search
    state = vector_search(
        query=query,
        db=db,
        limit=10,
        prod_only=prod_only,
        distance_cutoff=settings.vector_cutoff,
    )
    yield state

    if state.phase == "NO_MATCHES":
        return

    # Phase 2: Haiku triage
    state = triage_phase(
        state=state,
        anthropic_client=anthropic_client,
        model=settings.triage_model,
        triage_cutoff=settings.triage_cutoff,
    )
    yield state

    if state.phase == "NO_MATCHES":
        return

    # Phase 3: Sonnet rationale
    state = generate_rationale(
        state=state,
        db=db,
        anthropic_client=anthropic_client,
        model=settings.rationale_model,
        top_n=settings.rationale_top_n,
    )
    yield state
```

- [ ] **Step 4: Update `__init__.py` to export public API**

Replace `src/rcars/recommender/__init__.py`:

```python
"""RCARS recommendation engine — three-phase pipeline.

Public API:
    run_query()  — generator yielding QueryState after each phase
    QueryState   — pipeline state at a phase boundary
    Candidate    — a catalog item moving through the pipeline
"""

from rcars.recommender.models import Candidate, QueryState
from rcars.recommender.pipeline import run_query

__all__ = ["run_query", "QueryState", "Candidate"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/recommender/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/rcars/recommender/pipeline.py src/rcars/recommender/__init__.py \
        tests/recommender/test_pipeline.py
git commit -m "recommender: Add three-phase pipeline orchestrator"
```

---

### Task 7: Update CLI `recommend` Command

**Files:**
- Modify: `src/rcars/cli.py`
- Delete: `src/rcars/recommender.py`
- Delete: `src/rcars/prompts/recommend.txt`

- [ ] **Step 1: Update the CLI recommend command**

In `src/rcars/cli.py`, find the `recommend` command (line ~304). Replace it with:

Change the Click decorator to add `--cutoff` and `--triage-cutoff`:

```python
@cli.command()
@click.argument("query")
@click.option("--url", "event_url", type=str, default=None, help="Event URL to analyze")
@click.option("--include-dev", is_flag=True, default=False, help="Include dev items")
@click.option("--limit", type=int, default=10, help="Max candidates to consider")
@click.option("--cutoff", type=float, default=None, help="Vector distance cutoff (default: from RCARS_VECTOR_CUTOFF)")
@click.option("--triage-cutoff", type=int, default=None, help="Min Haiku relevance score (default: from RCARS_TRIAGE_CUTOFF)")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON")
```

Replace the function body. The import changes from `from rcars.recommender import recommend as run_recommend` to `from rcars.recommender import run_query`. The function iterates the generator and prints progressive output:

```python
def recommend(query, event_url, include_dev, limit, cutoff, triage_cutoff, json_output):
    """Get content recommendations for an event or use case."""
    import json as json_mod
    from rcars.recommender import run_query
    from rcars.event_parser import parse_event_url

    settings = Settings()
    db = get_db()

    anthropic_client = settings.get_anthropic_client()
    if not anthropic_client:
        console.print("[red]Error:[/red] No Anthropic credentials")
        db.close()
        sys.exit(1)

    # Apply CLI overrides
    if cutoff is not None:
        settings.vector_cutoff = cutoff
    if triage_cutoff is not None:
        settings.triage_cutoff = triage_cutoff

    # If event URL provided, parse it and enhance query
    if event_url:
        console.print("[bold]Parsing event URL...[/bold]")
        event_profile = parse_event_url(event_url, anthropic_client, settings.model)
        if event_profile:
            queries = event_profile.get("search_queries", [])
            themes = event_profile.get("themes", [])
            query = f"{query}. Event themes: {', '.join(themes)}. {' '.join(queries)}"
            console.print(f"  Event: {event_profile.get('event_name', 'Unknown')}")

    console.print("[bold]Searching for recommendations...[/bold]")

    final_state = None
    for state in run_query(
        query=query,
        db=db,
        anthropic_client=anthropic_client,
        settings=settings,
        prod_only=not include_dev,
    ):
        final_state = state
        if state.phase == "VECTOR_DONE":
            console.print(f"  Phase 1: {len(state.candidates)} candidates from vector search ({state.timings.get('vector_search', 0):.1f}s)")
        elif state.phase == "TRIAGE_DONE":
            console.print(f"  Phase 2: {len(state.candidates)} candidates survived triage ({state.timings.get('triage', 0):.1f}s)")
        elif state.phase == "COMPLETE":
            console.print(f"  Phase 3: Rationale generated ({state.timings.get('rationale', 0):.1f}s)")
        elif state.phase == "NO_MATCHES":
            console.print("[yellow]No relevant matches found.[/yellow]")
            db.close()
            return

    if not final_state or not final_state.candidates:
        console.print("[yellow]No recommendations found.[/yellow]")
        db.close()
        return

    if json_output:
        output = {
            "recommendations": [
                {
                    "ci_name": c.ci_name,
                    "display_name": c.display_name,
                    "relevance_score": c.relevance_score,
                    "rationale": c.rationale,
                    "suggested_format": c.suggested_format,
                    "duration_notes": c.duration_notes,
                    "caveats": c.caveats,
                }
                for c in final_state.candidates
            ],
            "overall_assessment": final_state.overall_assessment,
            "content_gaps": final_state.content_gaps,
            "timings": final_state.timings,
        }
        console.print(json_mod.dumps(output, indent=2))
    else:
        console.print("\n[bold]Recommendations[/bold]\n")
        for c in final_state.candidates:
            score = c.relevance_score or c.vector_similarity_pct
            color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            console.print(f"  [{color}]{score}%[/{color}] [bold]{c.display_name}[/bold]")
            console.print(f"        {c.ci_name}")
            if c.rationale:
                console.print(f"        {c.rationale}")
            elif c.one_line_reason:
                console.print(f"        {c.one_line_reason}")
            console.print()

        if final_state.overall_assessment:
            console.print(f"\n[bold]Assessment[/bold]\n{final_state.overall_assessment}")

    db.close()
```

- [ ] **Step 2: Delete the old recommender.py and recommend.txt**

```bash
git rm src/rcars/recommender.py src/rcars/prompts/recommend.txt
```

- [ ] **Step 3: Run existing tests to verify nothing else broke**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/ -v`
Expected: All tests PASS (no tests depended on the old recommender.py directly — they used mocks)

- [ ] **Step 4: Commit**

```bash
git add src/rcars/cli.py
git commit -m "cli: Update recommend command for three-phase pipeline

Add --cutoff and --triage-cutoff flags for tuning. Remove old
single-call recommender.py and recommend.txt prompt."
```

---

### Task 8: Update Web Advisor Route for Progressive Updates

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`

This is the largest task. The background thread changes from calling `recommend()` once to iterating `run_query()` and updating `_query_status` after each phase.

- [ ] **Step 1: Update imports**

In `src/rcars/web/routes/advisor.py`, replace:

```python
from rcars.recommender import recommend
```

with:

```python
from rcars.recommender import run_query, Candidate
```

- [ ] **Step 2: Update `_query_status` shape**

The status dict gains a `phase` field and stores the latest `QueryState`. Replace the comment on line 79:

```python
# shape: session_id → {
#   "phase": str,           # "searching" | "vector_done" | "triaging" | "triage_done" | "rationale" | "complete" | "no_matches" | "error"
#   "running": bool,
#   "rec_html": str|None,
#   "chat_html": str|None,
#   "error": str|None,
#   "candidates": list[dict],  # serialized candidates for session storage
# }
```

- [ ] **Step 3: Rewrite `_run_advisor_query`**

Replace the `_run_advisor_query` function with this progressive version:

```python
def _run_advisor_query(
    session_id: str,
    message: str,
    description: str,
    first_message: str,
    db,
    client,
    settings,
    user: str,
) -> None:
    """Background thread: run three-phase pipeline, update _query_status at each phase."""
    turn_index = len(_sessions.get(session_id, []))
    is_curator = settings.is_curator(user)

    try:
        for state in run_query(
            query=description,
            db=db,
            anthropic_client=client,
            settings=settings,
            prod_only=True,
        ):
            if state.phase == "VECTOR_DONE":
                recs = _candidates_to_recs(state.candidates, "vector")
                recs = _enrich_recs(recs, db)
                rec_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs, is_curator=is_curator, session_id=session_id,
                    phase="triaging", status_message="Evaluating relevance...",
                )
                _query_status[session_id] = {
                    "phase": "vector_done", "running": True,
                    "rec_html": rec_html, "chat_html": None, "error": None,
                    "candidates": recs,
                }

            elif state.phase == "TRIAGE_DONE":
                recs = _candidates_to_recs(state.candidates, "triaged")
                recs = _enrich_recs(recs, db)
                # Mark top N for rationale
                for i, rec in enumerate(recs):
                    if i < settings.rationale_top_n and (rec.get("relevance_score", 0) >= 70):
                        rec["card_phase"] = "analyzing"
                rec_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs, is_curator=is_curator, session_id=session_id,
                    phase="rationale", status_message="Preparing detailed analysis...",
                )
                _query_status[session_id] = {
                    "phase": "triage_done", "running": True,
                    "rec_html": rec_html, "chat_html": None, "error": None,
                    "candidates": recs,
                }

            elif state.phase == "COMPLETE":
                recs = _candidates_to_recs(state.candidates, "complete")
                recs = _enrich_recs(recs, db)
                overall = state.overall_assessment or f"Found {len(recs)} matches."

                turns = _sessions.setdefault(session_id, [])
                turns.append({
                    "role": "assistant", "content": overall,
                    "rec_ci_names": [r["ci_name"] for r in recs],
                    "recs": recs, "turn_index": turn_index,
                })

                rec_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs, is_curator=is_curator, session_id=session_id,
                    phase="complete", status_message=None,
                )
                chat_html = templates.get_template("fragments/chat_turn.html").render(
                    user_message=message, assistant_message=overall,
                    session_id=session_id, turn_index=turn_index,
                    first_message=first_message,
                )
                _query_status[session_id] = {
                    "phase": "complete", "running": False,
                    "rec_html": rec_html, "chat_html": chat_html, "error": None,
                    "candidates": recs,
                }

            elif state.phase == "NO_MATCHES":
                no_match_msg = "Nothing in the catalog is a strong fit for this query. Try broadening your terms or describing what you need differently."
                turns = _sessions.setdefault(session_id, [])
                turns.append({
                    "role": "assistant", "content": no_match_msg,
                    "rec_ci_names": [], "recs": [], "turn_index": turn_index,
                })
                rec_html = (
                    '<div class="pane-label">Recommendations</div>'
                    f'<p style="color:var(--text-muted);font-size:14px;">{no_match_msg}</p>'
                )
                chat_html = templates.get_template("fragments/chat_turn.html").render(
                    user_message=message, assistant_message=no_match_msg,
                    session_id=session_id, turn_index=turn_index,
                    first_message=first_message,
                )
                _query_status[session_id] = {
                    "phase": "no_matches", "running": False,
                    "rec_html": rec_html, "chat_html": chat_html, "error": None,
                    "candidates": [],
                }

    except Exception:
        log.exception("advisor bg: pipeline failed session=%s", session_id)
        _query_status[session_id] = {
            "phase": "error", "running": False,
            "rec_html": None, "chat_html": None,
            "error": "An internal error occurred. Please try again.",
            "candidates": [],
        }
```

- [ ] **Step 4: Add `_candidates_to_recs` helper**

Add this function before `_run_advisor_query`:

```python
def _candidates_to_recs(candidates: list, card_phase: str) -> list[dict]:
    """Convert Candidate dataclasses to rec dicts for templates."""
    recs = []
    for c in candidates:
        rec = {
            "ci_name": c.ci_name,
            "display_name": c.display_name,
            "fit_score": c.relevance_score if c.relevance_score is not None else c.vector_similarity_pct,
            "rationale": c.rationale or "",
            "suggested_format": c.suggested_format or "",
            "duration_notes": c.duration_notes or "",
            "caveats": c.caveats or "",
            "one_line_reason": c.one_line_reason or "",
            "card_phase": c.rationale and "complete" or card_phase,
            "summary": c.summary,
            "topics": c.topics,
            "difficulty": c.difficulty,
            "duration_min": c.duration_min,
            "content_type": c.content_type,
        }
        recs.append(rec)
    return recs
```

- [ ] **Step 5: Update the polling endpoint for progressive responses**

Replace the `advisor_query_status` function:

```python
@router.get("/advisor/query/status", response_class=HTMLResponse)
async def advisor_query_status(
    session_id: str,
    user: str = Depends(get_current_user),
):
    status = _query_status.get(session_id)

    if status is None:
        return HTMLResponse(_query_spinner_fragment(session_id))

    # Still running — return latest rec_html with polling trigger
    if status["running"]:
        if status.get("rec_html"):
            # We have intermediate results (vector or triage phase) — show them with continued polling
            html = (
                f'<div id="rec-pane" class="rec-pane"'
                f' hx-get="/advisor/query/status?session_id={escape(session_id)}"'
                f' hx-trigger="every 2s"'
                f' hx-swap="outerHTML">'
                f'{status["rec_html"]}'
                f'</div>'
            )
            return HTMLResponse(html)
        return HTMLResponse(_query_spinner_fragment(session_id))

    # Done — pop and return final result
    _query_status.pop(session_id, None)

    if status.get("error"):
        rec_html = (
            '<div class="pane-label">Recommendations</div>'
            f'<p style="color:var(--score-red);font-size:14px;">{escape(status["error"])}</p>'
        )
        return HTMLResponse(_query_done_fragment(rec_html, ""))

    return HTMLResponse(_query_done_fragment(status["rec_html"], status.get("chat_html", "")))
```

- [ ] **Step 6: Update the spinner text**

Update `_query_spinner_fragment` to say "Searching the catalog..." instead of "Analyzing your request":

```python
def _query_spinner_fragment(session_id: str) -> str:
    """HTMX polling spinner that replaces #rec-pane while query runs."""
    return (
        f'<div id="rec-pane" class="rec-pane"'
        f' hx-get="/advisor/query/status?session_id={escape(session_id)}"'
        f' hx-trigger="every 2s"'
        f' hx-swap="outerHTML">'
        f'<div class="pane-label">Recommendations</div>'
        f'<div class="rec-pane-loading">'
        f'<span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span>'
        f' Searching the catalog'
        f'</div>'
        f'</div>'
    )
```

- [ ] **Step 7: Commit**

```bash
git add src/rcars/web/routes/advisor.py
git commit -m "advisor: Progressive pipeline updates via HTMX polling

Background thread iterates run_query() generator and updates
_query_status after each phase. Polling endpoint returns latest
HTML fragment including intermediate vector/triage results."
```

---

### Task 9: Update Templates for Phase-Aware Card Rendering

**Files:**
- Modify: `src/rcars/web/templates/fragments/rec_card.html`
- Modify: `src/rcars/web/templates/fragments/rec_list.html`
- Modify: `src/rcars/web/static/rcars.css`

- [ ] **Step 1: Update rec_list.html for phase status line**

Replace `src/rcars/web/templates/fragments/rec_list.html`:

```html
<div class="pane-label">Recommendations</div>
{% if status_message %}
<div class="rec-status-line">
  <span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span>
  {{ status_message }}
</div>
{% endif %}
{% if recs %}
  {% for rec in recs %}
    {% include "fragments/rec_card.html" %}
  {% endfor %}
{% elif not status_message %}
  <p style="color:var(--text-muted);font-size:12px;">No strong matches found. Try rephrasing your query.</p>
{% endif %}
<button class="new-session-btn"
        onclick="window.location.href='/advisor'">
  + New session
</button>
```

- [ ] **Step 2: Update rec_card.html for phase-aware rendering**

Replace `src/rcars/web/templates/fragments/rec_card.html`:

```html
{% set score = rec.fit_score %}
{% set card_phase = rec.get("card_phase", "complete") if rec.get is defined else rec.card_phase|default("complete") %}
{% if score >= 80 %}{% set score_class = "score-green" %}
{% elif score >= 50 %}{% set score_class = "score-amber" %}
{% else %}{% set score_class = "score-red" %}{% endif %}

<div class="rec-card {{ score_class }}"
     data-phase="{{ card_phase }}"
     x-data="{ expanded: false }"
     @click="expanded = !expanded">
  <div class="rec-card-header">
    <div class="rec-score">{{ score }}%</div>
    <div style="flex:1;min-width:0;">
      <div class="rec-title">{{ rec.display_name }}</div>
      <div class="rec-meta">{{ rec.ci_name }}</div>
      {% if card_phase == "vector" %}
        <div class="rec-meta">{{ rec.content_type }} · {{ rec.difficulty }} · {{ rec.duration_min or '?' }} min</div>
        <div class="rec-meta">{{ rec.topics | join(', ') }}</div>
      {% endif %}
      {% if card_phase in ("triaged", "analyzing", "complete") and rec.one_line_reason %}
        <div class="rec-meta">{{ rec.one_line_reason }}</div>
      {% endif %}
      {% if rec.suggested_format %}
      <div class="rec-meta">Format: {{ rec.suggested_format }}</div>
      {% endif %}
      {% if rec.duration_notes %}
      <div class="rec-meta">Duration: {{ rec.duration_notes }}</div>
      {% endif %}
    </div>
    <span class="rec-expand-hint" x-text="expanded ? '▾' : '▸'"></span>
  </div>

  {% if card_phase == "analyzing" %}
    <div class="rec-rationale rec-analyzing">
      <span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span>
      Preparing detailed analysis...
    </div>
  {% elif card_phase == "complete" and rec.rationale %}
    <div class="rec-rationale">{{ rec.rationale | format_message }}</div>
  {% elif card_phase == "vector" and rec.summary %}
    <div class="rec-rationale rec-summary-preview">{{ rec.summary }}</div>
  {% endif %}

  {% if rec.caveats %}
  <div class="rec-meta" style="color:var(--score-amber);">⚠ {{ rec.caveats }}</div>
  {% endif %}

  {% if rec.tags %}
  <div class="tag-list">
    {% for tag in rec.tags %}
    <span class="tag-pill">{{ tag.tag_value }}</span>
    {% endfor %}
  </div>
  {% endif %}

  <div x-show="expanded" style="display:none;" @click.stop>
    {% include "fragments/rec_card_expanded.html" %}
  </div>
</div>
```

- [ ] **Step 3: Add CSS for new card states**

Add to the end of `src/rcars/web/static/rcars.css`:

```css
/* Phase status line */
.rec-status-line {
  font-size: 13px;
  color: var(--score-amber);
  padding: 8px 0;
  margin-bottom: 4px;
}

/* Card phase: analyzing — subtle pulse */
.rec-analyzing {
  color: var(--score-amber) !important;
  font-style: italic;
}

/* Summary preview in vector phase — dimmer than full rationale */
.rec-summary-preview {
  color: #777 !important;
  font-style: italic;
}

/* Card fade-out transition for removed cards */
.rec-card[data-phase="removed"] {
  opacity: 0;
  transition: opacity 0.3s ease-out;
  pointer-events: none;
}
```

- [ ] **Step 4: Commit**

```bash
git add src/rcars/web/templates/fragments/rec_card.html \
        src/rcars/web/templates/fragments/rec_list.html \
        src/rcars/web/static/rcars.css
git commit -m "templates: Phase-aware rec cards with progressive status"
```

---

### Task 10: Create Web Advisor Progressive Tests

**Files:**
- Create: `tests/web/__init__.py`
- Create: `tests/web/test_advisor_progressive.py`

- [ ] **Step 1: Write tests for progressive advisor flow**

Create `tests/web/__init__.py` (empty file) and `tests/web/test_advisor_progressive.py`:

```python
"""Tests for progressive advisor query flow."""

import json
from unittest.mock import MagicMock, patch

from rcars.recommender.models import Candidate, QueryState
from rcars.web.routes.advisor import _candidates_to_recs


def _candidate(ci_name, **kwargs):
    defaults = dict(
        ci_name=ci_name,
        display_name=ci_name.replace("-", " ").title(),
        category="workshop",
        summary=f"Summary for {ci_name}",
        topics=["openshift"],
        products=["OCP"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
        vector_distance=0.3,
        vector_similarity_pct=85,
    )
    defaults.update(kwargs)
    return Candidate(**defaults)


def test_candidates_to_recs_vector_phase():
    candidates = [_candidate("test-ci")]
    recs = _candidates_to_recs(candidates, "vector")

    assert len(recs) == 1
    assert recs[0]["ci_name"] == "test-ci"
    assert recs[0]["fit_score"] == 85  # vector_similarity_pct
    assert recs[0]["card_phase"] == "vector"
    assert recs[0]["summary"] == "Summary for test-ci"


def test_candidates_to_recs_triaged_phase():
    c = _candidate("test-ci", relevance_score=90, one_line_reason="Great match")
    recs = _candidates_to_recs([c], "triaged")

    assert recs[0]["fit_score"] == 90  # relevance_score takes precedence
    assert recs[0]["card_phase"] == "triaged"
    assert recs[0]["one_line_reason"] == "Great match"


def test_candidates_to_recs_complete_phase():
    c = _candidate(
        "test-ci",
        relevance_score=90,
        rationale="This is a great workshop.",
        suggested_format="hands_on_lab",
    )
    recs = _candidates_to_recs([c], "complete")

    assert recs[0]["card_phase"] == "complete"  # rationale present overrides
    assert recs[0]["rationale"] == "This is a great workshop."
```

- [ ] **Step 2: Run tests**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/web/test_advisor_progressive.py -v`
Expected: 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/web/__init__.py tests/web/test_advisor_progressive.py
git commit -m "tests: Add progressive advisor query tests"
```

---

### Task 11: Run Full Test Suite and Verify

**Files:**
- None (verification only)

- [ ] **Step 1: Run all tests**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Verify imports work end-to-end**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -c "from rcars.recommender import run_query, QueryState, Candidate; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Verify CLI help shows new flags**

Run: `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && rcars recommend --help`
Expected: Shows `--cutoff` and `--triage-cutoff` flags alongside existing flags

- [ ] **Step 4: Verify old recommender.py is gone**

Run: `test -f src/rcars/recommender.py && echo "STILL EXISTS" || echo "REMOVED"`
Expected: `REMOVED`

---

## Self-Review Findings

**Spec coverage check:**
- Phase 1 (vector search + cutoff) → Task 3 ✓
- Phase 2 (Haiku triage) → Task 4 ✓
- Phase 3 (Sonnet rationale) → Task 5 ✓
- Pipeline orchestrator → Task 6 ✓
- Config env vars → Task 2 ✓
- CLI --cutoff/--triage-cutoff flags → Task 7 ✓
- Progressive web UI → Tasks 8, 9 ✓
- Card phase states (vector/triaged/analyzing/complete) → Task 9 ✓
- Phase status messages → Tasks 8, 9 ✓
- Code structure (recommender/ package) → Tasks 1, 3-6 ✓
- Prompt files (triage.txt, rationale.txt) → Tasks 4, 5 ✓
- Tests → Tasks 1-6, 10 ✓

**Type consistency check:**
- `Candidate` dataclass used consistently across all modules ✓
- `QueryState.query` field added in Task 4, used in Tasks 5-8 ✓
- `run_query` generator signature consistent between pipeline.py and callers ✓
- `_candidates_to_recs` return format matches template expectations ✓

**Placeholder scan:** No TBD/TODO found ✓
