# Token Usage Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist all Anthropic API token usage (scan, triage, rationale) to PostgreSQL and display time-windowed stats broken down by model and operation type in the admin view.

**Architecture:** A new `token_usage` table stores one row per API call. Scan tokens are written directly in `analyze_showroom()`. Query tokens (triage + rationale) are carried through `QueryState` and written by the pipeline orchestrator after the full query completes. The admin view loads a new HTMX fragment at `/admin/token-usage` with a time-window selector.

**Tech Stack:** psycopg v3 (direct SQL, no SQLAlchemy), FastAPI + HTMX, pytest + unittest.mock

---

## File Map

| File | Change |
|------|--------|
| `src/rcars/db.py` | Migration 003, `log_token_usage()`, `get_token_stats()`, `get_recent_queries()`, add `token_usage` to `drop_schema()` |
| `src/rcars/recommender/models.py` | Add `token_usage: list[dict]` field to `QueryState` |
| `src/rcars/recommender/triage.py` | Read `response.usage`, carry tokens in returned `QueryState` |
| `src/rcars/recommender/rationale.py` | Read `response.usage`, carry tokens in returned `QueryState` |
| `src/rcars/analyzer.py` | Add optional `db` param, call `db.log_token_usage()` after API call |
| `src/rcars/recommender/pipeline.py` | Write all query tokens to DB after `generate_rationale()` |
| `src/rcars/cli.py` | Pass `db` to `analyze_showroom()` in `scan` command |
| `src/rcars/web/routes/admin.py` | `_fmt_tokens()`, `_token_usage_html()`, `GET /admin/token-usage` route |
| `src/rcars/web/templates/admin.html` | New Token Usage section with HTMX load trigger |
| `tests/test_db.py` | Add token usage DB tests, update `test_create_schema` |
| `tests/recommender/test_models.py` | Add `token_usage` field test |
| `tests/recommender/test_triage.py` | Update `_mock_client` to set `usage`, add token capture test |
| `tests/recommender/test_rationale.py` | Update `_mock_client` to set `usage`, add token capture test |
| `tests/recommender/test_pipeline.py` | Add token write-to-DB test |
| `tests/test_analyzer.py` | Add scan token logging test |
| `tests/web/test_admin.py` | Add token-usage route tests |

---

## Task 1: DB Layer — `token_usage` table and methods

**Files:**
- Modify: `src/rcars/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_db.py`:

```python
def test_log_token_usage(db):
    """Should insert a token usage row."""
    db.log_token_usage(
        operation="scan",
        model="claude-sonnet-4-6",
        input_tokens=5000,
        output_tokens=800,
        ci_name="test.lab.prod",
    )
    with db._conn.cursor() as cur:
        cur.execute("SELECT * FROM token_usage")
        rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0]["operation"] == "scan"
    assert rows[0]["model"] == "claude-sonnet-4-6"
    assert rows[0]["input_tokens"] == 5000
    assert rows[0]["output_tokens"] == 800
    assert rows[0]["ci_name"] == "test.lab.prod"
    assert rows[0]["query_text"] is None


def test_log_token_usage_query(db):
    """Should insert a query token usage row with query_text."""
    db.log_token_usage(
        operation="triage",
        model="claude-haiku-4-5",
        input_tokens=1200,
        output_tokens=300,
        query_text="openshift booth demo",
    )
    with db._conn.cursor() as cur:
        cur.execute("SELECT * FROM token_usage WHERE operation = 'triage'")
        row = cur.fetchone()
    assert row is not None
    assert row["query_text"] == "openshift booth demo"
    assert row["ci_name"] is None


def test_get_token_stats_empty(db):
    """Should return empty list when no usage data."""
    stats = db.get_token_stats(days=30)
    assert stats == []


def test_get_token_stats_aggregates(db):
    """Should aggregate tokens by operation and model."""
    db.log_token_usage("scan", "claude-sonnet-4-6", 10000, 1000)
    db.log_token_usage("scan", "claude-sonnet-4-6", 8000, 900)
    db.log_token_usage("triage", "claude-haiku-4-5", 2000, 400)

    stats = db.get_token_stats(days=30)
    by_op = {(r["operation"], r["model"]): r for r in stats}

    scan_row = by_op[("scan", "claude-sonnet-4-6")]
    assert scan_row["calls"] == 2
    assert scan_row["input_tokens"] == 18000
    assert scan_row["output_tokens"] == 1900
    assert scan_row["total_tokens"] == 19900

    triage_row = by_op[("triage", "claude-haiku-4-5")]
    assert triage_row["calls"] == 1
    assert triage_row["total_tokens"] == 2400


def test_get_token_stats_all_time(db):
    """days=None should return all records regardless of age."""
    db.log_token_usage("rationale", "claude-sonnet-4-6", 50000, 4000)
    stats = db.get_token_stats(days=None)
    assert len(stats) >= 1


def test_get_recent_queries(db):
    """Should return per-query grouped rows."""
    db.log_token_usage("triage", "claude-haiku-4-5", 1200, 300, query_text="ansible demo booth")
    db.log_token_usage("rationale", "claude-sonnet-4-6", 45000, 3800, query_text="ansible demo booth")

    queries = db.get_recent_queries(days=30)
    assert len(queries) == 1
    row = queries[0]
    assert row["query_text"] == "ansible demo booth"
    assert row["triage_input"] == 1200
    assert row["triage_output"] == 300
    assert row["rationale_input"] == 45000
    assert row["rationale_output"] == 3800
    assert row["total_tokens"] == 50300


def test_get_recent_queries_excludes_scan(db):
    """Scan ops should not appear in get_recent_queries."""
    db.log_token_usage("scan", "claude-sonnet-4-6", 10000, 1000, ci_name="test.ci")
    queries = db.get_recent_queries(days=30)
    assert queries == []
```

Also update `test_create_schema`:

```python
def test_create_schema(db):
    """Schema creation should create all expected tables."""
    tables = db.list_tables()
    assert "catalog_items" in tables
    assert "showroom_analysis" in tables
    assert "enrichment_tags" in tables
    assert "embeddings" in tables
    assert "analysis_log" in tables
    assert "jobs" in tables
    assert "token_usage" in tables  # migration 003
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/nstephan/devel/working/rcars-advisory
pytest tests/test_db.py::test_log_token_usage tests/test_db.py::test_get_token_stats_empty tests/test_db.py::test_create_schema -v
```

Expected: FAIL — `token_usage` table does not exist.

- [ ] **Step 3: Add migration 003 to `create_schema()` in `src/rcars/db.py`**

In `create_schema()`, after the migration 002 block (content_hash column check), add:

```python
        # Migration 003: add token_usage table
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'token_usage'
            ) as exists
        """)
        result = cur.fetchone()
        if not result["exists"]:
            cur.execute("""
                CREATE TABLE token_usage (
                    id            SERIAL PRIMARY KEY,
                    operation     TEXT NOT NULL,
                    model         TEXT NOT NULL,
                    ci_name       TEXT,
                    query_text    TEXT,
                    input_tokens  INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    created_at    TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute(
                "CREATE INDEX idx_token_usage_created_at ON token_usage(created_at)"
            )
            cur.execute(
                "CREATE INDEX idx_token_usage_operation ON token_usage(operation)"
            )
```

- [ ] **Step 4: Add `token_usage` to `drop_schema()` table list**

In `drop_schema()`, update the `tables` list to include `"token_usage"`:

```python
        tables = [
            "embeddings", "enrichment_tags", "showroom_analysis",
            "analysis_log", "jobs", "token_usage", "catalog_items", "alembic_version",
        ]
```

- [ ] **Step 5: Add `log_token_usage()` method to `Database`**

Add after `get_recent_logs()`:

```python
    def log_token_usage(
        self,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        ci_name: str | None = None,
        query_text: str | None = None,
    ) -> None:
        """Log a single API token usage event."""
        with self._conn.cursor() as cur:
            cur.execute(
                """INSERT INTO token_usage
                   (operation, model, input_tokens, output_tokens, ci_name, query_text)
                   VALUES (%(operation)s, %(model)s, %(input_tokens)s, %(output_tokens)s,
                           %(ci_name)s, %(query_text)s)""",
                {
                    "operation": operation,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "ci_name": ci_name,
                    "query_text": query_text,
                },
            )
        self._conn.commit()
```

- [ ] **Step 6: Add `get_token_stats()` method to `Database`**

```python
    def get_token_stats(self, days: int | None = 30) -> list[dict[str, Any]]:
        """Return token usage aggregated by (operation, model).

        days=None means all-time; otherwise limits to the last N days.
        """
        if days is not None:
            where = "WHERE created_at >= NOW() - %(days)s * INTERVAL '1 day'"
            params: dict[str, Any] = {"days": days}
        else:
            where = ""
            params = {}

        sql = f"""
            SELECT operation, model,
                   COUNT(*) AS calls,
                   SUM(input_tokens) AS input_tokens,
                   SUM(output_tokens) AS output_tokens,
                   SUM(input_tokens + output_tokens) AS total_tokens
            FROM token_usage
            {where}
            GROUP BY operation, model
            ORDER BY total_tokens DESC
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
```

- [ ] **Step 7: Add `get_recent_queries()` method to `Database`**

```python
    def get_recent_queries(
        self, days: int | None = 30, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return per-query token usage for triage + rationale ops.

        Groups triage and rationale rows from the same pipeline run by
        query_text + 1-minute time bucket. Returns most recent first.
        """
        if days is not None:
            time_filter = "AND created_at >= NOW() - %(days)s * INTERVAL '1 day'"
            params: dict[str, Any] = {"days": days, "limit": limit}
        else:
            time_filter = ""
            params = {"limit": limit}

        sql = f"""
            SELECT
                query_text,
                date_trunc('minute', created_at) AS query_time,
                SUM(CASE WHEN operation = 'triage' THEN input_tokens ELSE 0 END)
                    AS triage_input,
                SUM(CASE WHEN operation = 'triage' THEN output_tokens ELSE 0 END)
                    AS triage_output,
                SUM(CASE WHEN operation = 'rationale' THEN input_tokens ELSE 0 END)
                    AS rationale_input,
                SUM(CASE WHEN operation = 'rationale' THEN output_tokens ELSE 0 END)
                    AS rationale_output,
                SUM(input_tokens + output_tokens) AS total_tokens
            FROM token_usage
            WHERE operation IN ('triage', 'rationale')
              AND query_text IS NOT NULL
              {time_filter}
            GROUP BY query_text, date_trunc('minute', created_at)
            ORDER BY query_time DESC
            LIMIT %(limit)s
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
```

- [ ] **Step 8: Run all DB tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: ALL PASS.

- [ ] **Step 9: Commit**

```bash
git add src/rcars/db.py tests/test_db.py
git commit -m "feat: Add token_usage table and DB methods

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Add `token_usage` field to `QueryState`

**Files:**
- Modify: `src/rcars/recommender/models.py`
- Test: `tests/recommender/test_models.py`

- [ ] **Step 1: Write failing test**

In `tests/recommender/test_models.py`, add:

```python
from rcars.recommender.models import Candidate, QueryState


def test_query_state_token_usage_defaults_to_empty_list():
    """token_usage should default to an empty list."""
    state = QueryState(phase="VECTOR_DONE", candidates=[], query="test")
    assert state.token_usage == []


def test_query_state_token_usage_carries_entries():
    """token_usage should store and preserve token entries."""
    entry = {
        "operation": "triage",
        "model": "claude-haiku-4-5",
        "input_tokens": 1000,
        "output_tokens": 200,
    }
    state = QueryState(phase="TRIAGE_DONE", candidates=[], query="test", token_usage=[entry])
    assert len(state.token_usage) == 1
    assert state.token_usage[0]["operation"] == "triage"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/recommender/test_models.py -v
```

Expected: FAIL — `QueryState` has no `token_usage` field (or import error if file doesn't exist yet).

- [ ] **Step 3: Add `token_usage` field to `QueryState` in `src/rcars/recommender/models.py`**

Add after `timings`:

```python
    token_usage: list[dict] = field(default_factory=list)
```

The full `QueryState` dataclass should now read:

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
    token_usage: list[dict] = field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/recommender/test_models.py -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/rcars/recommender/models.py tests/recommender/test_models.py
git commit -m "feat: Add token_usage field to QueryState

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Triage — capture token usage

**Files:**
- Modify: `src/rcars/recommender/triage.py`
- Test: `tests/recommender/test_triage.py`

- [ ] **Step 1: Update `_mock_client` in `tests/recommender/test_triage.py` to include usage**

Replace the existing `_mock_client` function:

```python
def _mock_client(response_json, input_tokens=1000, output_tokens=200):
    client = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps(response_json)
    response = MagicMock()
    response.content = [content_block]
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    client.messages.create.return_value = response
    return client
```

- [ ] **Step 2: Write failing test**

Add to `tests/recommender/test_triage.py`:

```python
def test_triage_captures_token_usage():
    """Returned QueryState should carry triage token usage entry."""
    candidates = [_candidate("good-ci")]
    state = QueryState(phase="VECTOR_DONE", candidates=candidates, query="ansible")

    haiku_response = [
        {"ci_name": "good-ci", "relevance_score": 85, "relevant": True,
         "one_line_reason": "Match"},
    ]
    client = _mock_client(haiku_response, input_tokens=1500, output_tokens=250)

    result = triage(state, client, model="claude-haiku-4-5", triage_cutoff=30)

    assert len(result.token_usage) == 1
    entry = result.token_usage[0]
    assert entry["operation"] == "triage"
    assert entry["model"] == "claude-haiku-4-5"
    assert entry["input_tokens"] == 1500
    assert entry["output_tokens"] == 250


def test_triage_carries_forward_existing_token_usage():
    """Existing token_usage from prior state should be preserved."""
    prior_entry = {"operation": "scan", "model": "claude-sonnet-4-6",
                   "input_tokens": 9000, "output_tokens": 800}
    candidates = [_candidate("good-ci")]
    state = QueryState(
        phase="VECTOR_DONE", candidates=candidates,
        query="ansible", token_usage=[prior_entry],
    )

    haiku_response = [
        {"ci_name": "good-ci", "relevance_score": 80, "relevant": True,
         "one_line_reason": "Match"},
    ]
    client = _mock_client(haiku_response)
    result = triage(state, client, triage_cutoff=30)

    assert len(result.token_usage) == 2
    assert result.token_usage[0]["operation"] == "scan"
    assert result.token_usage[1]["operation"] == "triage"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/recommender/test_triage.py::test_triage_captures_token_usage tests/recommender/test_triage.py::test_triage_carries_forward_existing_token_usage -v
```

Expected: FAIL — `result.token_usage` is empty.

- [ ] **Step 4: Update `triage()` in `src/rcars/recommender/triage.py` to capture tokens**

Replace the final `return QueryState(...)` call with:

```python
    new_token_entry = {
        "operation": "triage",
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    return QueryState(
        phase=phase,
        candidates=survivors,
        query=state.query,
        timings={**state.timings, "triage": round(elapsed, 3)},
        token_usage=[*state.token_usage, new_token_entry],
    )
```

- [ ] **Step 5: Run all triage tests to verify they pass**

```bash
pytest tests/recommender/test_triage.py -v
```

Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
git add src/rcars/recommender/triage.py tests/recommender/test_triage.py
git commit -m "feat: Capture Haiku triage token usage in QueryState

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Rationale — capture token usage

**Files:**
- Modify: `src/rcars/recommender/rationale.py`
- Test: `tests/recommender/test_rationale.py`

- [ ] **Step 1: Update `_mock_client` in `tests/recommender/test_rationale.py` to set `usage`**

Replace the existing `_mock_client` function:

```python
def _mock_client(response_json, input_tokens=40000, output_tokens=3500):
    client = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps(response_json)
    response = MagicMock()
    response.content = [content_block]
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    client.messages.create.return_value = response
    return client
```

- [ ] **Step 2: Write failing tests**

Add to `tests/recommender/test_rationale.py` (after the existing tests):

```python
def test_generate_rationale_captures_token_usage():
    """Returned QueryState should carry rationale token entry."""
    candidates = [_candidate("good-ci")]
    state = QueryState(phase="TRIAGE_DONE", candidates=candidates, query="openshift")

    sonnet_response = {
        "recommendations": [
            {"ci_name": "good-ci", "rationale": "Good match.",
             "suggested_format": "hands_on_lab", "duration_notes": "", "caveats": ""},
        ],
        "overall_assessment": "Good.",
        "content_gaps": [],
    }
    client = _mock_client(sonnet_response, input_tokens=40000, output_tokens=3500)
    db = _mock_db()

    result = generate_rationale(state, db, client, model="claude-sonnet-4-6", top_n=5)

    assert len(result.token_usage) == 1
    entry = result.token_usage[0]
    assert entry["operation"] == "rationale"
    assert entry["model"] == "claude-sonnet-4-6"
    assert entry["input_tokens"] == 40000
    assert entry["output_tokens"] == 3500


def test_generate_rationale_carries_forward_token_usage():
    """Prior token_usage entries should be preserved in returned state."""
    prior = {
        "operation": "triage", "model": "claude-haiku-4-5",
        "input_tokens": 1200, "output_tokens": 300,
    }
    candidates = [_candidate("good-ci")]
    state = QueryState(
        phase="TRIAGE_DONE", candidates=candidates,
        query="openshift", token_usage=[prior],
    )

    sonnet_response = {
        "recommendations": [
            {"ci_name": "good-ci", "rationale": "Matches well.",
             "suggested_format": "hands_on_lab", "duration_notes": "", "caveats": ""},
        ],
        "overall_assessment": "Good.",
        "content_gaps": [],
    }
    client = _mock_client(sonnet_response)
    db = _mock_db()

    result = generate_rationale(state, db, client, model="claude-sonnet-4-6", top_n=5)

    assert len(result.token_usage) == 2
    assert result.token_usage[0]["operation"] == "triage"
    assert result.token_usage[1]["operation"] == "rationale"
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
pytest tests/recommender/test_rationale.py::test_rationale_captures_token_usage tests/recommender/test_rationale.py::test_rationale_carries_forward_token_usage -v
```

Expected: FAIL — `result.token_usage` is empty.

- [ ] **Step 5: Update `generate_rationale()` in `src/rcars/recommender/rationale.py` to capture tokens**

Read `response.usage` after the API call and carry tokens forward. Replace the final `return QueryState(...)` with:

```python
    new_token_entry = {
        "operation": "rationale",
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    return QueryState(
        phase="COMPLETE",
        candidates=top_candidates + remaining,
        query=state.query,
        overall_assessment=result.get("overall_assessment") if result else None,
        content_gaps=result.get("content_gaps") if result else None,
        timings={**state.timings, "rationale": round(elapsed, 3)},
        token_usage=[*state.token_usage, new_token_entry],
    )
```

- [ ] **Step 6: Run all rationale tests to verify they pass**

```bash
pytest tests/recommender/test_rationale.py -v
```

Expected: ALL PASS.

- [ ] **Step 7: Commit**

```bash
git add src/rcars/recommender/rationale.py tests/recommender/test_rationale.py
git commit -m "feat: Capture Sonnet rationale token usage in QueryState

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Pipeline — write query tokens to DB

**Files:**
- Modify: `src/rcars/recommender/pipeline.py`
- Test: `tests/recommender/test_pipeline.py`

- [ ] **Step 1: Write failing test**

Add to `tests/recommender/test_pipeline.py`:

```python
@patch("rcars.recommender.pipeline.generate_rationale")
@patch("rcars.recommender.pipeline.triage_phase")
@patch("rcars.recommender.pipeline.vector_search")
def test_pipeline_writes_query_tokens_to_db(mock_vs, mock_triage, mock_rationale):
    """After COMPLETE phase, pipeline should write all token_usage entries to db."""
    vector_state = _make_vector_state(2)
    triage_state = QueryState(
        phase="TRIAGE_DONE", candidates=vector_state.candidates, query="test query",
        token_usage=[
            {"operation": "triage", "model": "claude-haiku-4-5",
             "input_tokens": 1000, "output_tokens": 200},
        ],
    )
    complete_state = QueryState(
        phase="COMPLETE", candidates=triage_state.candidates, query="test query",
        token_usage=[
            {"operation": "triage", "model": "claude-haiku-4-5",
             "input_tokens": 1000, "output_tokens": 200},
            {"operation": "rationale", "model": "claude-sonnet-4-6",
             "input_tokens": 45000, "output_tokens": 3800},
        ],
    )

    mock_vs.return_value = vector_state
    mock_triage.return_value = triage_state
    mock_rationale.return_value = complete_state

    mock_db = MagicMock()
    settings = _mock_settings()
    states = list(run_query("test query", mock_db, MagicMock(), settings))

    assert states[-1].phase == "COMPLETE"
    assert mock_db.log_token_usage.call_count == 2

    calls = mock_db.log_token_usage.call_args_list
    triage_call = calls[0]
    assert triage_call.kwargs["operation"] == "triage"
    assert triage_call.kwargs["query_text"] == "test query"
    assert triage_call.kwargs["input_tokens"] == 1000

    rationale_call = calls[1]
    assert rationale_call.kwargs["operation"] == "rationale"
    assert rationale_call.kwargs["input_tokens"] == 45000


@patch("rcars.recommender.pipeline.vector_search")
def test_pipeline_no_token_write_on_no_matches(mock_vs):
    """If pipeline stops early (NO_MATCHES), no token writes should occur."""
    mock_vs.return_value = QueryState(phase="NO_MATCHES", candidates=[], query="test")
    mock_db = MagicMock()
    settings = _mock_settings()
    list(run_query("test", mock_db, MagicMock(), settings))
    mock_db.log_token_usage.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/recommender/test_pipeline.py::test_pipeline_writes_query_tokens_to_db tests/recommender/test_pipeline.py::test_pipeline_no_token_write_on_no_matches -v
```

Expected: FAIL — `mock_db.log_token_usage` never called.

- [ ] **Step 3: Update `run_query()` in `src/rcars/recommender/pipeline.py` to write tokens**

After the `yield state` at the end (after `generate_rationale`), add:

```python
    # Write query token usage to DB
    for entry in state.token_usage:
        db.log_token_usage(
            query_text=state.query[:200],
            **entry,
        )
```

The full updated pipeline after phase 3 should read:

```python
    # Phase 3: Sonnet rationale
    state = generate_rationale(
        state=state,
        db=db,
        anthropic_client=anthropic_client,
        model=settings.rationale_model,
        top_n=settings.rationale_top_n,
    )
    yield state

    # Write query token usage to DB
    for entry in state.token_usage:
        db.log_token_usage(
            query_text=state.query[:200],
            **entry,
        )
```

- [ ] **Step 4: Run all pipeline tests to verify they pass**

```bash
pytest tests/recommender/test_pipeline.py -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/rcars/recommender/pipeline.py tests/recommender/test_pipeline.py
git commit -m "feat: Write query token usage to DB after pipeline completes

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Analyzer + CLI — scan token capture

**Files:**
- Modify: `src/rcars/analyzer.py`
- Modify: `src/rcars/cli.py`
- Test: `tests/test_analyzer.py`

- [ ] **Step 1: Read existing `tests/test_analyzer.py` to understand test patterns**

```bash
cat tests/test_analyzer.py
```

- [ ] **Step 2: Write failing test**

Add to `tests/test_analyzer.py` (after reading existing structure):

```python
def test_analyze_showroom_logs_scan_tokens(monkeypatch):
    """analyze_showroom should call db.log_token_usage with scan tokens when db provided."""
    from unittest.mock import MagicMock, patch
    from rcars.analyzer import analyze_showroom

    mock_db = MagicMock()
    mock_client = MagicMock()

    # Mock clone, read content, and API response
    mock_response = MagicMock()
    mock_response.content[0].text = '{"content_type": "workshop", "summary": "Test", "products": [], "audience": [], "topics": [], "modules": [], "learning_objectives": {}, "difficulty": "beginner", "estimated_duration_min": 60, "event_fit": {}, "use_cases": []}'
    mock_response.usage.input_tokens = 12000
    mock_response.usage.output_tokens = 900
    mock_client.messages.create.return_value = mock_response

    with patch("rcars.analyzer.clone_showroom") as mock_clone, \
         patch("rcars.analyzer.read_showroom_content") as mock_read, \
         patch("rcars.analyzer.get_repo_head") as mock_head, \
         patch("rcars.analyzer.generate_embedding") as mock_embed:

        mock_clone.return_value = MagicMock()  # non-None path
        mock_read.return_value = {"module1.adoc": "= OpenShift Workshop\nLearn OpenShift basics here."}
        mock_head.return_value = ("abc123def", "2026-04-01T10:00:00+00:00")
        mock_embed.return_value = [0.1] * 384

        result = analyze_showroom(
            ci_name="test.ci.prod",
            display_name="Test CI",
            category="workshop",
            product="OCP",
            showroom_url="https://github.com/example/test.git",
            showroom_ref="main",
            anthropic_client=mock_client,
            model="claude-sonnet-4-6",
            db=mock_db,
        )

    assert result is not None
    mock_db.log_token_usage.assert_called_once_with(
        operation="scan",
        model="claude-sonnet-4-6",
        input_tokens=12000,
        output_tokens=900,
        ci_name="test.ci.prod",
    )


def test_analyze_showroom_no_db_does_not_fail():
    """analyze_showroom should work fine when db=None (no token logging)."""
    from unittest.mock import MagicMock, patch
    from rcars.analyzer import analyze_showroom

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content[0].text = '{"content_type": "demo", "summary": "Demo", "products": [], "audience": [], "topics": [], "modules": [], "learning_objectives": {}, "difficulty": "intermediate", "estimated_duration_min": 30, "event_fit": {}, "use_cases": []}'
    mock_response.usage.input_tokens = 5000
    mock_response.usage.output_tokens = 400
    mock_client.messages.create.return_value = mock_response

    with patch("rcars.analyzer.clone_showroom") as mock_clone, \
         patch("rcars.analyzer.read_showroom_content") as mock_read, \
         patch("rcars.analyzer.get_repo_head") as mock_head, \
         patch("rcars.analyzer.generate_embedding") as mock_embed:

        mock_clone.return_value = MagicMock()
        mock_read.return_value = {"module1.adoc": "= Demo\nContent here."}
        mock_head.return_value = ("abc123", "2026-04-01T10:00:00+00:00")
        mock_embed.return_value = [0.1] * 384

        # Should not raise even with db=None
        result = analyze_showroom(
            ci_name="test.ci",
            display_name="Test",
            category="demo",
            product="OCP",
            showroom_url="https://github.com/example/test.git",
            showroom_ref=None,
            anthropic_client=mock_client,
            model="claude-sonnet-4-6",
            db=None,
        )
    assert result is not None
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_analyzer.py::test_analyze_showroom_logs_scan_tokens tests/test_analyzer.py::test_analyze_showroom_no_db_does_not_fail -v
```

Expected: FAIL — `analyze_showroom` has no `db` parameter.

- [ ] **Step 4: Update `analyze_showroom()` signature in `src/rcars/analyzer.py`**

Add `db=None` as the last parameter:

```python
def analyze_showroom(
    ci_name: str,
    display_name: str,
    category: str,
    product: str,
    showroom_url: str,
    showroom_ref: str | None,
    anthropic_client,
    model: str = "claude-sonnet-4-6",
    clone_dir: str = "/tmp",
    db=None,
) -> dict[str, Any] | None:
```

- [ ] **Step 5: Add token logging after the API call in `analyze_showroom()`**

The API call is at line ~419. After reading `input_tokens` and `output_tokens` (which already happens at lines 426-428), add:

```python
        if db is not None:
            db.log_token_usage(
                operation="scan",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                ci_name=ci_name,
            )
```

This goes immediately after the existing log statement on line 429.

- [ ] **Step 6: Update `process_item` in `src/rcars/cli.py` to pass `db`**

Find the `process_item` inner function inside the `scan` command (~line 274). Change the `analyze_showroom(...)` call to include `db=db`:

```python
    def process_item(item):
        _print(f"  start: {item['ci_name']}")
        return analyze_showroom(
            ci_name=item["ci_name"],
            display_name=item.get("display_name", ""),
            category=item.get("category", ""),
            product=item.get("product", ""),
            showroom_url=item["showroom_url"],
            showroom_ref=item.get("showroom_ref"),
            anthropic_client=anthropic_client,
            model=settings.model,
            clone_dir=settings.clone_dir,
            db=db,
        )
```

- [ ] **Step 7: Run all analyzer tests to verify they pass**

```bash
pytest tests/test_analyzer.py -v
```

Expected: ALL PASS.

- [ ] **Step 8: Commit**

```bash
git add src/rcars/analyzer.py src/rcars/cli.py tests/test_analyzer.py
git commit -m "feat: Log scan token usage to DB in analyze_showroom

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Admin route and template

**Files:**
- Modify: `src/rcars/web/routes/admin.py`
- Modify: `src/rcars/web/templates/admin.html`
- Test: `tests/web/test_admin.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/web/test_admin.py`:

```python
def test_token_usage_route_returns_summary(admin_client):
    """GET /admin/token-usage should return model/operation breakdown."""
    client, mock_db = admin_client
    mock_db.get_token_stats.return_value = [
        {
            "operation": "scan", "model": "claude-sonnet-4-6",
            "calls": 10, "input_tokens": 50000, "output_tokens": 5000,
            "total_tokens": 55000,
        },
        {
            "operation": "triage", "model": "claude-haiku-4-5",
            "calls": 5, "input_tokens": 6000, "output_tokens": 1500,
            "total_tokens": 7500,
        },
    ]
    mock_db.get_recent_queries.return_value = []

    response = client.get("/admin/token-usage?days=30")

    assert response.status_code == 200
    assert "claude-sonnet-4-6" in response.text
    assert "claude-haiku-4-5" in response.text
    assert "scan" in response.text
    assert "triage" in response.text
    assert "token-usage-section" in response.text


def test_token_usage_route_empty_state(admin_client):
    """GET /admin/token-usage with no data should show empty message."""
    client, mock_db = admin_client
    mock_db.get_token_stats.return_value = []
    mock_db.get_recent_queries.return_value = []

    response = client.get("/admin/token-usage?days=30")

    assert response.status_code == 200
    assert "No token usage data" in response.text


def test_token_usage_shows_recent_queries(admin_client):
    """GET /admin/token-usage should render per-query rows."""
    from datetime import datetime, timezone
    client, mock_db = admin_client
    mock_db.get_token_stats.return_value = []
    mock_db.get_recent_queries.return_value = [
        {
            "query_text": "OpenShift booth demo for Summit",
            "query_time": datetime(2026, 4, 13, 14, 22, tzinfo=timezone.utc),
            "triage_input": 1200, "triage_output": 300,
            "rationale_input": 45000, "rationale_output": 3800,
            "total_tokens": 50300,
        }
    ]

    response = client.get("/admin/token-usage?days=30")

    assert response.status_code == 200
    assert "OpenShift booth demo for Summit" in response.text
    assert "50,300" in response.text


def test_token_usage_all_time_param(admin_client):
    """GET /admin/token-usage?days=0 should call get_token_stats with days=None."""
    client, mock_db = admin_client
    mock_db.get_token_stats.return_value = []
    mock_db.get_recent_queries.return_value = []

    response = client.get("/admin/token-usage?days=0")

    assert response.status_code == 200
    mock_db.get_token_stats.assert_called_once_with(days=None)
    mock_db.get_recent_queries.assert_called_once_with(days=None)


def test_token_usage_window_selector_present(admin_client):
    """Token usage section should include the time window selector."""
    client, mock_db = admin_client
    mock_db.get_token_stats.return_value = []
    mock_db.get_recent_queries.return_value = []

    response = client.get("/admin/token-usage?days=30")

    assert "Last 7 days" in response.text
    assert "Last 30 days" in response.text
    assert "All time" in response.text
    assert "/admin/token-usage" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/web/test_admin.py::test_token_usage_route_returns_summary tests/web/test_admin.py::test_token_usage_route_empty_state -v
```

Expected: FAIL — route `/admin/token-usage` does not exist (404).

- [ ] **Step 3: Add `_fmt_tokens()` helper to `src/rcars/web/routes/admin.py`**

Add after the existing imports and module-level state dicts:

```python
def _fmt_tokens(n: int) -> str:
    """Format token count with K/M suffix for summary display."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
```

- [ ] **Step 4: Add `_token_usage_html()` helper to `src/rcars/web/routes/admin.py`**

```python
def _token_usage_html(stats: list, queries: list, days: int) -> str:
    """Render the token usage section as an HTML fragment."""
    # Window selector
    select_html = (
        '<select hx-get="/admin/token-usage" hx-target="#token-usage-section" '
        'hx-swap="outerHTML" hx-trigger="change" name="days" '
        'style="background:var(--bg-secondary);color:var(--text-primary);'
        'border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:12px;">'
    )
    for val, label in [(7, "Last 7 days"), (30, "Last 30 days"), (90, "Last 90 days"), (0, "All time")]:
        selected = " selected" if val == days else ""
        select_html += f'<option value="{val}"{selected}>{label}</option>'
    select_html += "</select>"

    # Summary table
    if stats:
        rows = "".join(
            f'<tr><td>{row["model"]}</td><td>{row["operation"]}</td>'
            f'<td>{row["calls"]}</td>'
            f'<td>{_fmt_tokens(row["input_tokens"])}</td>'
            f'<td>{_fmt_tokens(row["output_tokens"])}</td>'
            f'<td>{_fmt_tokens(row["total_tokens"])}</td></tr>'
            for row in stats
        )
        summary_html = (
            '<table class="status-table" style="margin-top:8px;">'
            "<tr><th>Model</th><th>Operation</th><th>Calls</th>"
            "<th>Input</th><th>Output</th><th>Total</th></tr>"
            f"{rows}</table>"
        )
    else:
        summary_html = (
            '<p style="font-size:12px;color:var(--text-muted);">'
            "No token usage data for this period.</p>"
        )

    # Per-query table
    if queries:
        query_rows = ""
        for row in queries:
            q_full = row.get("query_text") or ""
            q_display = q_full[:60] + ("…" if len(q_full) > 60 else "")
            qt = row["query_time"].strftime("%Y-%m-%d %H:%M") if row.get("query_time") else ""
            total = row.get("total_tokens", 0)
            query_rows += (
                f'<tr>'
                f'<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;'
                f'white-space:nowrap;" title="{_html.escape(q_full)}">'
                f"{_html.escape(q_display)}</td>"
                f'<td>{row.get("triage_input", 0):,}</td>'
                f'<td>{row.get("triage_output", 0):,}</td>'
                f'<td>{row.get("rationale_input", 0):,}</td>'
                f'<td>{row.get("rationale_output", 0):,}</td>'
                f'<td>{total:,}</td>'
                f'<td style="font-size:10px;color:var(--text-muted);">{qt}</td>'
                f"</tr>"
            )
        query_html = (
            '<div style="font-size:12px;font-weight:600;margin:12px 0 6px;">'
            "Recent Queries</div>"
            '<table class="status-table" style="font-size:11px;">'
            "<tr><th>Query</th><th>Haiku In</th><th>Haiku Out</th>"
            "<th>Sonnet In</th><th>Sonnet Out</th><th>Total</th><th>Time</th></tr>"
            f"{query_rows}</table>"
        )
    else:
        query_html = ""

    return (
        f'<div id="token-usage-section">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f'<span style="font-size:12px;color:var(--text-muted);">Window:</span>'
        f"{select_html}"
        f"</div>"
        f"{summary_html}"
        f"{query_html}"
        f"</div>"
    )
```

- [ ] **Step 5: Add the `/admin/token-usage` route to `src/rcars/web/routes/admin.py`**

Add after the `refresh_status` route handler:

```python
@router.get("/admin/token-usage", response_class=HTMLResponse)
async def token_usage_fragment(
    days: int = 30,
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    days_arg = days if days > 0 else None
    stats = db.get_token_stats(days=days_arg)
    queries = db.get_recent_queries(days=days_arg)
    return HTMLResponse(_token_usage_html(stats, queries, days))
```

- [ ] **Step 6: Add the Token Usage section to `src/rcars/web/templates/admin.html`**

Insert between the "Content Updates" section and the "Curator Access" section:

```html
  <div class="admin-section">
    <h3>Token Usage</h3>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">
      Claude API token consumption by model and operation.
    </p>
    <div id="token-usage-section"
         hx-get="/admin/token-usage"
         hx-trigger="load"
         hx-swap="outerHTML">
      <span style="font-size:12px;color:var(--text-muted);">Loading…</span>
    </div>
  </div>
```

- [ ] **Step 7: Run all admin tests to verify they pass**

```bash
pytest tests/web/test_admin.py -v
```

Expected: ALL PASS.

- [ ] **Step 8: Run the full test suite**

```bash
pytest -v
```

Expected: ALL PASS.

- [ ] **Step 9: Commit**

```bash
git add src/rcars/web/routes/admin.py src/rcars/web/templates/admin.html tests/web/test_admin.py
git commit -m "feat: Add Token Usage section to admin view

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```
