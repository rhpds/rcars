# Advisor List, Persistence & Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the full recommendation list visible throughout the pipeline with color-coded tiers, persist every query and its results to the DB, and let users mark their chosen recommendation.

**Architecture:** Three independently deployable features built in order. Feature 1 changes the pipeline data model and rendering. Feature 2 adds a new DB table and writes to it at query completion. Feature 3 adds a button on each complete card and a single POST route. Each feature gets its own commit batch so only Feature 1 triggers a rebuild while 2 and 3 can be batched.

**Tech Stack:** Python 3.11, FastAPI, HTMX, psycopg 3 + pool, Jinja2, Click, PostgreSQL, sentence-transformers

---

## Feature 1: Full Advisory List with Color Tiers

### Files

- Modify: `src/rcars/recommender/models.py` — add `tier` field to `Candidate`
- Modify: `src/rcars/recommender/triage.py` — annotate all candidates instead of dropping; mark tier
- Modify: `src/rcars/recommender/pipeline.py` — pass only yellow candidates to rationale; merge full list after
- Modify: `src/rcars/web/routes/advisor.py` — sort by tier in `_candidates_to_recs`; pass full list at each phase
- Modify: `src/rcars/web/templates/fragments/rec_card.html` — tier-based border color instead of score-based
- Modify: `src/rcars/web/templates/fragments/rec_list.html` — pass `turn_index` through
- Modify: `tests/recommender/test_triage.py` — update tests for new keep-all behavior
- Modify: `tests/recommender/test_pipeline.py` — update tests for full-list yielding

---

### Task 1: Add tier field to Candidate model

**Files:**
- Modify: `src/rcars/recommender/models.py`
- Test: `tests/recommender/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/recommender/test_models.py — create file

from rcars.recommender.models import Candidate


def test_candidate_default_tier():
    """New candidates default to 'white' tier."""
    c = Candidate(
        ci_name="test/lab", display_name="Test", category="demo",
        summary="s", topics=[], products=[], difficulty="easy",
        duration_min=30, content_type="demo",
    )
    assert c.tier == "white"


def test_candidate_tier_can_be_set():
    c = Candidate(
        ci_name="test/lab", display_name="Test", category="demo",
        summary="s", topics=[], products=[], difficulty="easy",
        duration_min=30, content_type="demo", tier="green",
    )
    assert c.tier == "green"
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd ~/devel/rcars-advisory
~/.virtualenvs/content-advisor/bin/python -m pytest tests/recommender/test_models.py -v
```
Expected: FAIL — `Candidate` has no `tier` field

- [ ] **Step 3: Add tier to Candidate**

In `src/rcars/recommender/models.py`, after the `stage` field:

```python
    stage: str = "prod"
    tier: str = "white"  # white | yellow | green — set by pipeline phases
    vector_distance: float = 0.0
```

- [ ] **Step 4: Run to verify it passes**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/recommender/test_models.py -v
```
Expected: PASS

- [ ] **Step 5: Run full recommender tests**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/recommender/ -v
```
Expected: All pass (tier has a default, existing tests unaffected)

- [ ] **Step 6: Commit**

```bash
cd ~/devel/rcars-advisory
git add src/rcars/recommender/models.py tests/recommender/test_models.py
git commit -m "recommender: Add tier field to Candidate (white|yellow|green)"
```

---

### Task 2: Rework triage to annotate all candidates instead of dropping

**Files:**
- Modify: `src/rcars/recommender/triage.py`
- Modify: `tests/recommender/test_triage.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/recommender/test_triage.py — add to existing file

def test_triage_keeps_all_candidates(mock_client):
    """Triage should keep ALL candidates — relevant ones as yellow, others as white."""
    from rcars.recommender.models import Candidate, QueryState
    from rcars.recommender.triage import triage

    candidates = [
        Candidate(ci_name="lab/a", display_name="A", category="demo",
                  summary="A", topics=[], products=[], difficulty="easy",
                  duration_min=30, content_type="demo"),
        Candidate(ci_name="lab/b", display_name="B", category="demo",
                  summary="B", topics=[], products=[], difficulty="easy",
                  duration_min=30, content_type="demo"),
    ]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="test")

    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='[{"ci_name":"lab/a","relevance_score":80,"relevant":true,"one_line_reason":"fits"}]')],
        usage=MagicMock(input_tokens=100, output_tokens=50),
    )

    result = triage(state, mock_client)

    assert result.phase == "TRIAGE_DONE"
    assert len(result.candidates) == 2  # BOTH kept
    by_ci = {c.ci_name: c for c in result.candidates}
    assert by_ci["lab/a"].tier == "yellow"
    assert by_ci["lab/a"].relevance_score == 80
    assert by_ci["lab/b"].tier == "white"
    assert by_ci["lab/b"].relevance_score is None


def test_triage_no_matches_when_zero_relevant(mock_client):
    """NO_MATCHES only when zero candidates are relevant — white ones still returned."""
    from rcars.recommender.models import Candidate, QueryState
    from rcars.recommender.triage import triage

    candidates = [
        Candidate(ci_name="lab/a", display_name="A", category="demo",
                  summary="A", topics=[], products=[], difficulty="easy",
                  duration_min=30, content_type="demo"),
    ]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="test")

    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='[{"ci_name":"lab/a","relevance_score":10,"relevant":false,"one_line_reason":"nope"}]')],
        usage=MagicMock(input_tokens=100, output_tokens=50),
    )

    result = triage(state, mock_client)

    assert result.phase == "NO_MATCHES"
    assert len(result.candidates) == 1  # still returned for context
    assert result.candidates[0].tier == "white"
```

- [ ] **Step 2: Run to verify they fail**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/recommender/test_triage.py::test_triage_keeps_all_candidates tests/recommender/test_triage.py::test_triage_no_matches_when_zero_relevant -v
```
Expected: FAIL

- [ ] **Step 3: Rewrite triage to annotate-and-keep**

Replace the `survivors` logic in `src/rcars/recommender/triage.py` (lines 73-95):

```python
    annotated = []
    relevant_count = 0
    for candidate in state.candidates:
        score_data = scores_by_ci.get(candidate.ci_name)
        if not score_data:
            log.info("  triage: not scored %s — marking white", candidate.ci_name)
            annotated.append(candidate)
            continue

        relevance = score_data.get("relevance_score", 0)
        relevant = score_data.get("relevant", False)
        reason = score_data.get("one_line_reason", "")

        candidate.relevance_score = relevance
        candidate.one_line_reason = reason

        if relevant and relevance >= triage_cutoff:
            candidate.tier = "yellow"
            candidate.relevant = True
            relevant_count += 1
            log.info("  triage: yellow %s — score=%d (%s)", candidate.ci_name, relevance, reason)
        else:
            candidate.tier = "white"
            candidate.relevant = False
            log.info("  triage: white %s — score=%d relevant=%s (%s)",
                     candidate.ci_name, relevance, relevant, reason)

        annotated.append(candidate)

    # Sort: yellow first (by score desc), white last (by vector similarity desc)
    annotated.sort(key=lambda c: (
        0 if c.tier == "yellow" else 1,
        -(c.relevance_score or 0) if c.tier == "yellow" else -(c.vector_similarity_pct or 0),
    ))

    elapsed = time.monotonic() - t0
    phase = "TRIAGE_DONE" if relevant_count > 0 else "NO_MATCHES"

    log.info(
        "triage: %d/%d relevant, %d total returned (cutoff=%d, elapsed=%.3fs)",
        relevant_count, len(state.candidates), len(annotated), triage_cutoff, elapsed,
    )
```

Also update the return statement (replace `candidates=survivors`):
```python
    return QueryState(
        phase=phase,
        candidates=annotated,
        query=state.query,
        timings={**state.timings, "triage": round(elapsed, 3)},
        token_usage=[*state.token_usage, new_token_entry],
    )
```

- [ ] **Step 4: Run triage tests**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/recommender/test_triage.py -v
```
Expected: All pass (new tests pass, old tests updated by the behavior change — fix any that assert on dropped candidates by updating them to assert tier instead)

- [ ] **Step 5: Commit**

```bash
git add src/rcars/recommender/triage.py tests/recommender/test_triage.py
git commit -m "triage: Annotate all candidates with tier instead of dropping"
```

---

### Task 3: Update pipeline to route only yellow candidates to rationale, then merge

**Files:**
- Modify: `src/rcars/recommender/pipeline.py`
- Modify: `tests/recommender/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/recommender/test_pipeline.py — add to existing file

def test_pipeline_full_list_at_complete(mock_vs, mock_triage, mock_rationale, db):
    """COMPLETE phase yields all candidates: green + yellow + white."""
    from rcars.recommender.pipeline import run_query
    from rcars.recommender.models import Candidate

    states = list(run_query("test query", db=db, anthropic_client=MagicMock(), settings=settings_fixture()))

    complete = next(s for s in states if s.phase == "COMPLETE")
    tiers = {c.tier for c in complete.candidates}
    # Must contain at least one green and the full set
    assert "green" in tiers
    # Total candidates should be >= candidates from VECTOR_DONE
    vector_done = next(s for s in states if s.phase == "VECTOR_DONE")
    assert len(complete.candidates) >= len(vector_done.candidates)
```

- [ ] **Step 2: Run to verify it fails**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/recommender/test_pipeline.py::test_pipeline_full_list_at_complete -v
```
Expected: FAIL

- [ ] **Step 3: Update pipeline to pass only yellow to rationale, merge after**

Replace the Phase 2 → Phase 3 section in `src/rcars/recommender/pipeline.py` (lines 45-75):

```python
    # Phase 2: Haiku triage — annotates all, returns full list
    state = triage_phase(
        state=state,
        anthropic_client=anthropic_client,
        model=settings.triage_model,
        triage_cutoff=settings.triage_cutoff,
    )
    yield state

    if state.phase == "NO_MATCHES":
        for entry in state.token_usage:
            db.log_token_usage(query_text=state.query[:200], **entry)
        return

    # Phase 3: Sonnet rationale — only on yellow (relevant) candidates
    all_candidates = state.candidates  # full list including whites
    yellow_candidates = [c for c in all_candidates if c.tier == "yellow"]

    from rcars.recommender.models import QueryState as QS
    yellow_state = QS(
        phase=state.phase,
        candidates=yellow_candidates,
        query=state.query,
        timings=state.timings,
        token_usage=state.token_usage,
    )

    rationale_state = generate_rationale(
        state=yellow_state,
        db=db,
        anthropic_client=anthropic_client,
        model=settings.rationale_model,
        top_n=settings.rationale_top_n,
    )

    # Mark green: yellow candidates that received a rationale
    rationale_ci_names = {c.ci_name for c in rationale_state.candidates if c.rationale}
    for c in rationale_state.candidates:
        if c.rationale:
            c.tier = "green"

    # Rebuild full list: green + remaining yellow + white
    green = [c for c in rationale_state.candidates if c.tier == "green"]
    remaining_yellow = [c for c in rationale_state.candidates if c.tier == "yellow"]
    white = [c for c in all_candidates if c.tier == "white"]

    full_candidates = green + remaining_yellow + white

    final_state = QS(
        phase=rationale_state.phase,
        candidates=full_candidates,
        query=rationale_state.query,
        overall_assessment=rationale_state.overall_assessment,
        content_gaps=rationale_state.content_gaps,
        timings=rationale_state.timings,
        token_usage=rationale_state.token_usage,
    )
    yield final_state

    for entry in final_state.token_usage:
        db.log_token_usage(query_text=final_state.query[:200], **entry)
```

- [ ] **Step 4: Run pipeline tests**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/recommender/test_pipeline.py -v
```
Expected: All pass

- [ ] **Step 5: Run full recommender suite**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/recommender/ -v
```
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/rcars/recommender/pipeline.py tests/recommender/test_pipeline.py
git commit -m "pipeline: Route only yellow candidates to Sonnet, merge full list at COMPLETE"
```

---

### Task 4: Update advisor route — tier sort and full list at each phase

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`

- [ ] **Step 1: Update `_candidates_to_recs` to include tier and apply sort**

In `src/rcars/web/routes/advisor.py`, replace `_candidates_to_recs` (lines 137-161):

```python
_TIER_ORDER = {"green": 0, "yellow": 1, "white": 2}


def _tier_sort_key(rec: dict) -> tuple:
    tier = rec.get("tier", "white")
    order = _TIER_ORDER.get(tier, 2)
    if tier == "green":
        score = -(rec.get("fit_score") or 0)
    elif tier == "yellow":
        score = -(rec.get("relevance_score") or rec.get("fit_score") or 0)
    else:
        score = -(rec.get("vector_similarity_pct") or 0)
    return (order, score)


def _candidates_to_recs(candidates: list, card_phase: str) -> list[dict]:
    """Convert Candidate dataclasses to rec dicts for templates, sorted by tier."""
    recs = []
    for c in candidates:
        tier = getattr(c, "tier", "white")
        rec = {
            "ci_name": c.ci_name,
            "display_name": c.display_name,
            "tier": tier,
            "fit_score": c.relevance_score if c.relevance_score is not None else c.vector_similarity_pct,
            "relevance_score": c.relevance_score,
            "vector_similarity_pct": c.vector_similarity_pct,
            "rationale": c.rationale or "",
            "why_it_fits": c.why_it_fits or "",
            "how_to_use": c.how_to_use or "",
            "suggested_format": c.suggested_format or "",
            "duration_notes": c.duration_notes or "",
            "caveats": c.caveats or "",
            "one_line_reason": c.one_line_reason or "",
            "card_phase": "complete" if c.rationale else (
                "triaged" if tier == "yellow" else card_phase
            ),
            "summary": c.summary,
            "topics": c.topics,
            "difficulty": c.difficulty,
            "duration_min": c.duration_min,
            "content_type": c.content_type,
            "stage": c.stage,
        }
        recs.append(rec)
    recs.sort(key=_tier_sort_key)
    return recs
```

- [ ] **Step 2: Update TRIAGE_DONE phase rendering to mark analyzing cards**

In `_run_advisor_query`, replace the `elif state.phase == "TRIAGE_DONE":` block (lines 216-231):

```python
            elif state.phase == "TRIAGE_DONE":
                recs = _candidates_to_recs(state.candidates, "triaged")
                recs = _enrich_recs(recs, db)
                # Mark top N yellow candidates as "analyzing" (going to Sonnet)
                yellow_count = 0
                for rec in recs:
                    if rec.get("tier") == "yellow" and yellow_count < settings.rationale_top_n:
                        rec["card_phase"] = "analyzing"
                        yellow_count += 1
                rec_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs, is_curator=is_curator, session_id=session_id,
                    turn_index=turn_index,
                    phase="rationale", status_message="Preparing detailed analysis...",
                )
                _query_status[session_id] = {
                    "phase": "triage_done", "running": True,
                    "rec_html": rec_html, "chat_html": None, "error": None,
                    "candidates": recs,
                }
```

- [ ] **Step 3: Update VECTOR_DONE and COMPLETE to pass turn_index**

In the `VECTOR_DONE` block, add `turn_index=turn_index` to the template render call:
```python
                rec_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs, is_curator=is_curator, session_id=session_id,
                    turn_index=turn_index,
                    phase="triaging", status_message="Evaluating relevance...",
                )
```

In the `COMPLETE` block, add `turn_index=turn_index`:
```python
                rec_html = templates.get_template("fragments/rec_list.html").render(
                    recs=recs, is_curator=is_curator, session_id=session_id,
                    turn_index=turn_index,
                    phase="complete", status_message=None,
                )
```

- [ ] **Step 4: Verify the web app imports cleanly**

```bash
cd ~/devel/rcars-advisory
PYTHONPATH=src ~/.virtualenvs/content-advisor/bin/python -c "from rcars.web.routes.advisor import router; print('OK')"
```
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add src/rcars/web/routes/advisor.py
git commit -m "advisor: Tier-sorted full candidate list, turn_index passed to templates"
```

---

### Task 5: Update rec_card.html for tier-based border color

**Files:**
- Modify: `src/rcars/web/templates/fragments/rec_card.html`
- Modify: `src/rcars/web/templates/fragments/rec_list.html`

- [ ] **Step 1: Replace score-based card class with tier-based**

In `src/rcars/web/templates/fragments/rec_card.html`, replace lines 1-10:

```html
{% set card_phase = rec.card_phase|default("complete") %}
{% set tier = rec.tier|default("white") %}
{% set score = rec.fit_score %}

<div class="rec-card {% if tier == 'green' %}tier-green{% elif tier == 'yellow' %}tier-yellow{% endif %}"
     data-phase="{{ card_phase }}"
     data-tier="{{ tier }}"
     x-data="{ expanded: false }"
     @click="expanded = !expanded">
```

- [ ] **Step 2: Add tier CSS to rcars.css**

Find the CSS file:
```bash
ls ~/devel/rcars-advisory/src/rcars/web/static/
```

Open the CSS file (e.g., `rcars.css`) and add:

```css
.rec-card.tier-green {
  border-left: 3px solid var(--score-green, #5cb85c);
}
.rec-card.tier-yellow {
  border-left: 3px solid var(--score-amber, #cc9900);
}
/* White tier: no special border — default card style */
```

- [ ] **Step 3: Update rec_list.html to accept and pass turn_index**

In `src/rcars/web/templates/fragments/rec_list.html`, no change needed — `rec_card.html` is included with `{% include %}` which inherits the parent template context including `turn_index`.

Verify `rec_list.html` passes `session_id` and `turn_index` correctly — the `{% include %}` block automatically exposes all parent vars to the included template.

- [ ] **Step 4: Commit**

```bash
cd ~/devel/rcars-advisory
git add src/rcars/web/templates/fragments/rec_card.html src/rcars/web/static/rcars.css
git commit -m "advisor: Tier-based card border colors (green/yellow/white)"
```

---

### Task 6: Push Feature 1 batch

- [ ] **Step 1: Run full test suite**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
```
Expected: All pass

- [ ] **Step 2: Push**

```bash
git push origin main
```

---

## Feature 2: Query Results Persistence

### Files

- Modify: `src/rcars/db.py` — migration 005, `log_advisor_session()` method
- Modify: `src/rcars/web/routes/advisor.py` — write session row at COMPLETE/NO_MATCHES
- Modify: `src/rcars/web/templates/advisor.html` — opt-out toggle

---

### Task 7: DB schema — advisor_sessions table

**Files:**
- Modify: `src/rcars/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py — add to existing file

def test_advisor_sessions_table_exists(db):
    """advisor_sessions table should exist after schema creation."""
    tables = db.list_tables()
    assert "advisor_sessions" in tables


def test_log_advisor_session(db):
    """log_advisor_session should insert a row and return its id."""
    row_id = db.log_advisor_session(
        session_id="sess-001",
        turn_index=0,
        user_email="test@test.com",
        query_text="show me ansible demos",
        event_url=None,
        results=[
            {"ci_name": "lab/a", "tier": "green", "fit_score": 90,
             "relevance_score": 85, "vector_similarity_pct": 78, "stage": "prod"}
        ],
        overall_assessment="Here are the best fits.",
        opted_out=False,
    )
    assert isinstance(row_id, int)
    assert row_id > 0


def test_log_advisor_session_opted_out(db):
    """Opted-out sessions store row with nulled sensitive fields."""
    row_id = db.log_advisor_session(
        session_id="sess-002",
        turn_index=0,
        user_email="test@test.com",
        query_text="confidential query",
        event_url=None,
        results=[{"ci_name": "lab/a", "tier": "green", "fit_score": 90,
                  "relevance_score": 85, "vector_similarity_pct": 78, "stage": "prod"}],
        overall_assessment="some assessment",
        opted_out=True,
    )
    assert row_id > 0
    # Verify sensitive fields are nulled in DB
    with db._pool.connection() as conn:
        cur = conn.execute(
            "SELECT query_text, results_json, overall_assessment, opted_out FROM advisor_sessions WHERE id = %s",
            (row_id,)
        )
        row = cur.fetchone()
    assert row["opted_out"] is True
    assert row["query_text"] is None
    assert row["results_json"] is None
    assert row["overall_assessment"] is None
```

- [ ] **Step 2: Run to verify they fail**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/test_db.py::test_advisor_sessions_table_exists tests/test_db.py::test_log_advisor_session tests/test_db.py::test_log_advisor_session_opted_out -v
```
Expected: FAIL

- [ ] **Step 3: Add migration 005 to create_schema**

In `src/rcars/db.py`, after migration 004 block and before `conn.commit()`:

```python
                # Migration 005: advisor_sessions table
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'advisor_sessions'
                    ) as exists
                """)
                if not cur.fetchone()["exists"]:
                    log.info("Migration 005: creating advisor_sessions table")
                    cur.execute("""
                        CREATE TABLE advisor_sessions (
                            id                 SERIAL PRIMARY KEY,
                            session_id         TEXT NOT NULL,
                            turn_index         INTEGER NOT NULL,
                            user_email         TEXT,
                            query_text         TEXT,
                            event_url          TEXT,
                            results_json       JSONB,
                            overall_assessment TEXT,
                            chosen_ci_name     TEXT,
                            chosen_at          TIMESTAMPTZ,
                            opted_out          BOOLEAN NOT NULL DEFAULT FALSE,
                            created_at         TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)
                    cur.execute(
                        "CREATE INDEX idx_advisor_sessions_session ON advisor_sessions(session_id)"
                    )
                    cur.execute(
                        "CREATE INDEX idx_advisor_sessions_user ON advisor_sessions(user_email)"
                    )
                    cur.execute(
                        "CREATE INDEX idx_advisor_sessions_created ON advisor_sessions(created_at)"
                    )
```

- [ ] **Step 4: Add log_advisor_session method**

In `src/rcars/db.py`, add after `get_db_currency`:

```python
    def log_advisor_session(
        self,
        session_id: str,
        turn_index: int,
        user_email: str | None,
        query_text: str | None,
        event_url: str | None,
        results: list[dict],
        overall_assessment: str | None,
        opted_out: bool = False,
    ) -> int:
        """Insert an advisor session turn. Returns the row id."""
        if opted_out:
            query_text = None
            results = None
            overall_assessment = None
        with self._pool.connection() as conn:
            cur = conn.execute("""
                INSERT INTO advisor_sessions
                    (session_id, turn_index, user_email, query_text, event_url,
                     results_json, overall_assessment, opted_out)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                session_id, turn_index, user_email, query_text, event_url,
                Jsonb(results) if results is not None else None,
                overall_assessment, opted_out,
            ))
            row_id = cur.fetchone()["id"]
            conn.commit()
        return row_id

    def update_advisor_session_choice(
        self, session_id: str, turn_index: int, chosen_ci_name: str
    ) -> None:
        """Record the user's chosen recommendation for a session turn."""
        with self._pool.connection() as conn:
            conn.execute("""
                UPDATE advisor_sessions
                SET chosen_ci_name = %s, chosen_at = NOW()
                WHERE session_id = %s AND turn_index = %s
            """, (chosen_ci_name, session_id, turn_index))
            conn.commit()
```

- [ ] **Step 5: Run tests**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/test_db.py::test_advisor_sessions_table_exists tests/test_db.py::test_log_advisor_session tests/test_db.py::test_log_advisor_session_opted_out -v
```
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/rcars/db.py tests/test_db.py
git commit -m "db: Add advisor_sessions table (migration 005) and log/update methods"
```

---

### Task 8: Write session row in advisor background thread

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`

- [ ] **Step 1: Add opt-out flag to _run_advisor_query signature**

In `src/rcars/web/routes/advisor.py`, update `_run_advisor_query` signature:

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
    prod_only: bool = True,
    opted_out: bool = False,
) -> None:
```

- [ ] **Step 2: Extract event_url from description for storage**

At the top of `_run_advisor_query`, after URL detection, capture the event URL:

```python
    event_url_stored: str | None = None
    urls = re.findall(r'https?://[^\s<>"]+', description)
    if urls:
        event_url_stored = urls[0]
        # ... existing event_profile code unchanged
```

- [ ] **Step 3: Write session row at COMPLETE phase**

In the `elif state.phase == "COMPLETE":` block, after `turns.append(...)` and before rendering `rec_html`, add:

```python
                # Persist session turn to DB
                if db:
                    results_for_storage = [
                        {
                            "ci_name": r["ci_name"],
                            "tier": r.get("tier", "white"),
                            "fit_score": r.get("fit_score"),
                            "relevance_score": r.get("relevance_score"),
                            "vector_similarity_pct": r.get("vector_similarity_pct"),
                            "stage": r.get("stage", "prod"),
                        }
                        for r in recs
                    ]
                    session_row_id = db.log_advisor_session(
                        session_id=session_id,
                        turn_index=turn_index,
                        user_email=user,
                        query_text=message if not opted_out else None,
                        event_url=event_url_stored,
                        results=results_for_storage,
                        overall_assessment=overall,
                        opted_out=opted_out,
                    )
                    _query_status[session_id]["session_row_id"] = session_row_id
```

- [ ] **Step 4: Write session row at NO_MATCHES phase**

In the `elif state.phase == "NO_MATCHES":` block, after `turns.append(...)`:

```python
                if db:
                    db.log_advisor_session(
                        session_id=session_id,
                        turn_index=turn_index,
                        user_email=user,
                        query_text=message if not opted_out else None,
                        event_url=event_url_stored,
                        results=[],
                        overall_assessment=no_match_msg,
                        opted_out=opted_out,
                    )
```

- [ ] **Step 5: Read opted_out from form in advisor_query route**

In the `advisor_query` POST handler, after reading `include_non_prod`:

```python
    opted_out = form.get("opted_out") == "true"
```

Update the `threading.Thread` call to pass `opted_out`:

```python
    t = threading.Thread(
        target=_run_advisor_query,
        args=(session_id, message, description, first_message, db, client, settings, user, prod_only, opted_out),
        daemon=True,
    )
```

- [ ] **Step 6: Verify import**

```bash
PYTHONPATH=src ~/.virtualenvs/content-advisor/bin/python -c "from rcars.web.routes.advisor import router; print('OK')"
```
Expected: OK

- [ ] **Step 7: Commit**

```bash
git add src/rcars/web/routes/advisor.py
git commit -m "advisor: Persist query + results to advisor_sessions at completion"
```

---

### Task 9: Add opt-out toggle to advisor.html

**Files:**
- Modify: `src/rcars/web/templates/advisor.html`

- [ ] **Step 1: Add toggle and wire to send JS**

In `src/rcars/web/templates/advisor.html`, in the toggles div (after the non-prod toggle `</label>`):

```html
        <label style="cursor:pointer;display:flex;align-items:center;gap:8px;user-select:none;">
          <span style="font-size:12px;color:var(--text-muted);">Don't save this query</span>
          <span style="position:relative;display:inline-block;width:36px;height:20px;flex-shrink:0;">
            <input type="checkbox" id="opted-out"
                   style="opacity:0;width:0;height:0;position:absolute;"
                   onchange="
                     var track = this.parentElement.querySelector('.oo-track');
                     var thumb = this.parentElement.querySelector('.oo-thumb');
                     if (this.checked) {
                       track.style.background = 'var(--score-amber, #cc9900)';
                       thumb.style.transform = 'translateX(16px)';
                     } else {
                       track.style.background = '#444';
                       thumb.style.transform = 'translateX(0)';
                     }">
            <span class="oo-track" style="position:absolute;inset:0;border-radius:20px;background:#444;transition:background 0.2s;"></span>
            <span class="oo-thumb" style="position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;transition:transform 0.2s;"></span>
          </span>
        </label>
```

In the `sendMessage()` JS function, after reading `nonProdCheckbox`:

```javascript
      var optedOutCheckbox = document.getElementById('opted-out');
      htmx.ajax('POST', '/advisor/query', {
        target: '#rec-pane',
        swap: 'outerHTML',
        values: {
          session_id: sessionId,
          message: sentMsg,
          include_non_prod: nonProdCheckbox && nonProdCheckbox.checked ? 'true' : 'false',
          opted_out: optedOutCheckbox && optedOutCheckbox.checked ? 'true' : 'false'
        }
      });
      // Reset opt-out after each send (one-time opt-out per message)
      if (optedOutCheckbox) optedOutCheckbox.checked = false;
```

Also reset the toggle visual after send — add after the JS reset line:

```javascript
      if (optedOutCheckbox) {
        var ooTrack = optedOutCheckbox.parentElement.querySelector('.oo-track');
        var ooThumb = optedOutCheckbox.parentElement.querySelector('.oo-thumb');
        if (ooTrack) ooTrack.style.background = '#444';
        if (ooThumb) ooThumb.style.transform = 'translateX(0)';
      }
```

- [ ] **Step 2: Commit**

```bash
git add src/rcars/web/templates/advisor.html
git commit -m "advisor: Add opt-out toggle for query persistence"
```

---

### Task 10: Push Feature 2 batch and run migration

- [ ] **Step 1: Run full test suite**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
```
Expected: All pass

- [ ] **Step 2: Push**

```bash
git push origin main
```

Migration 005 runs automatically on pod startup via `create_schema()`.

---

## Feature 3: "This Fits Best" Button

### Files

- Modify: `src/rcars/web/routes/advisor.py` — add `POST /advisor/select` route
- Modify: `src/rcars/web/templates/fragments/rec_card.html` — button on complete cards

---

### Task 11: POST /advisor/select route

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`
- Test: `tests/web/test_advisor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/web/test_advisor.py — add to existing file

def test_advisor_select_updates_session(client, db):
    """POST /advisor/select should update the chosen_ci_name on the session row."""
    # First create a session row directly
    row_id = db.log_advisor_session(
        session_id="sess-test", turn_index=0, user_email="test@test.com",
        query_text="test", event_url=None,
        results=[{"ci_name": "lab/a", "tier": "green", "fit_score": 90,
                  "relevance_score": 85, "vector_similarity_pct": 78, "stage": "prod"}],
        overall_assessment="Good fit.", opted_out=False,
    )
    assert row_id > 0

    response = client.post("/advisor/select", data={
        "session_id": "sess-test",
        "turn_index": "0",
        "ci_name": "lab/a",
    })
    assert response.status_code == 200
    assert "✓" in response.text or "fits best" in response.text.lower()

    # Verify DB update
    with db._pool.connection() as conn:
        cur = conn.execute(
            "SELECT chosen_ci_name FROM advisor_sessions WHERE id = %s", (row_id,)
        )
        row = cur.fetchone()
    assert row["chosen_ci_name"] == "lab/a"
```

- [ ] **Step 2: Run to verify it fails**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/web/test_advisor.py::test_advisor_select_updates_session -v
```
Expected: FAIL — route does not exist

- [ ] **Step 3: Add the route**

In `src/rcars/web/routes/advisor.py`, add after `advisor_query_status`:

```python
@router.post("/advisor/select", response_class=HTMLResponse)
async def advisor_select(
    request: Request,
    session_id: Annotated[str, Form()],
    turn_index: Annotated[str, Form()],
    ci_name: Annotated[str, Form()],
    user: str = Depends(get_current_user),
    db: Database | None = Depends(_get_db_dependency),
):
    if db:
        db.update_advisor_session_choice(session_id, int(turn_index), ci_name)
    return HTMLResponse(
        '<button style="background:var(--score-green);color:#000;border:none;'
        'padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600;cursor:default;">'
        '✓ Best fit selected</button>'
    )
```

Add `Annotated` to imports if not already present: `from typing import Annotated`.

- [ ] **Step 4: Run the test**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/web/test_advisor.py::test_advisor_select_updates_session -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/rcars/web/routes/advisor.py tests/web/test_advisor.py
git commit -m "advisor: Add POST /advisor/select to record chosen recommendation"
```

---

### Task 12: "This fits best" button on rec cards

**Files:**
- Modify: `src/rcars/web/templates/fragments/rec_card.html`

- [ ] **Step 1: Add button to complete green/yellow cards**

In `src/rcars/web/templates/fragments/rec_card.html`, at the end of the card body (before the closing `</div>`), add:

```html
  {# ── "This fits best" button — complete tier cards only ── #}
  {% if card_phase == "complete" and tier in ["green", "yellow"] and session_id is defined %}
  <div style="margin-top:8px;" @click.stop>
    <button
      hx-post="/advisor/select"
      hx-vals='{"session_id": "{{ session_id }}", "turn_index": "{{ turn_index|default(0) }}", "ci_name": {{ rec.ci_name | tojson }}}'
      hx-target="this"
      hx-swap="outerHTML"
      style="background:transparent;border:1px solid #444;color:var(--text-muted);
             padding:4px 10px;border-radius:4px;font-size:11px;cursor:pointer;">
      This fits best
    </button>
  </div>
  {% endif %}
```

- [ ] **Step 2: Verify the template renders without error**

```bash
PYTHONPATH=src ~/.virtualenvs/content-advisor/bin/python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('src/rcars/web/templates'))
t = env.get_template('fragments/rec_card.html')
print('template OK')
"
```
Expected: template OK

- [ ] **Step 3: Commit**

```bash
git add src/rcars/web/templates/fragments/rec_card.html
git commit -m "advisor: Add 'This fits best' button to complete recommendation cards"
```

---

### Task 13: Push Feature 3 batch

- [ ] **Step 1: Run full test suite**

```bash
~/.virtualenvs/content-advisor/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
```
Expected: All pass

- [ ] **Step 2: Push**

```bash
git push origin main
```
