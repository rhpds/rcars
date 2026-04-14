# Token Usage Tracking — Design Spec

**Date:** 2026-04-14
**Status:** Approved

## Overview

Add persistent token usage tracking to RCARS covering all Anthropic API calls (Showroom scan analysis, Haiku triage, Sonnet rationale). Expose aggregated stats in the admin view with time-windowed summaries broken down by model and operation type, plus a per-query detail table.

---

## 1. Data Layer

### New table: `token_usage`

```sql
CREATE TABLE IF NOT EXISTS token_usage (
    id            SERIAL PRIMARY KEY,
    operation     TEXT NOT NULL,         -- 'scan' | 'triage' | 'rationale'
    model         TEXT NOT NULL,         -- e.g. 'claude-sonnet-4-6'
    ci_name       TEXT,                  -- populated for scan ops, NULL for query ops
    query_text    TEXT,                  -- populated for triage/rationale, NULL for scan (truncated ~200 chars)
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_operation  ON token_usage(operation);
```

**Design notes:**
- No FK on `ci_name` — scan CIs may be deleted/refreshed; token history should outlive them.
- `query_text` is truncated to ~200 chars before storage — enough to identify the query in the UI.
- Added as **migration 003** in `db.create_schema()`, consistent with the existing numbered migration pattern.

### New `Database` methods

| Method | Purpose |
|--------|---------|
| `log_token_usage(operation, model, input_tokens, output_tokens, ci_name=None, query_text=None)` | Single-row insert; called after each API response |
| `get_token_stats(days=30)` | Aggregated rows grouped by `(operation, model)` for the given window; `days=None` means all-time |
| `get_recent_queries(days=30, limit=50)` | Per-query rows (triage + rationale grouped by `query_text` + time bucket) |

---

## 2. Instrumentation

Token counts are read from `response.usage` after every `anthropic_client.messages.create()` call. The write path is split into two patterns depending on context:

### Scan tokens — `analyzer.py`

`analyze_showroom()` already reads `response.usage.input_tokens` / `output_tokens` (for logging only). After the API call, it will write directly to DB:

```python
if db is not None:
    db.log_token_usage(
        operation='scan', model=model,
        input_tokens=input_tokens, output_tokens=output_tokens,
        ci_name=ci_name,
    )
```

`db` is added as an optional parameter to `analyze_showroom()` (default `None`). When `None`, token logging is silently skipped — existing tests require no changes.

### Query tokens — `triage.py` + `rationale.py` → `pipeline.py`

Individual phase modules don't have access to `db`, so they carry token counts on `QueryState` and the pipeline orchestrator writes them.

**`models.py` change:**

```python
@dataclass
class QueryState:
    ...
    token_usage: list[dict] = field(default_factory=list)
    # Each dict: {operation, model, input_tokens, output_tokens}
```

**`triage.py`** carries token usage forward in the returned `QueryState` (same pattern as `timings`):

```python
new_entry = {
    'operation': 'triage', 'model': model,
    'input_tokens': response.usage.input_tokens,
    'output_tokens': response.usage.output_tokens,
}
# returned in the new QueryState:
token_usage=[*state.token_usage, new_entry]
```

**`rationale.py`** does the same (same pattern, `operation='rationale'`).

**`pipeline.py`** writes all query tokens after `generate_rationale()` returns:

```python
for entry in state.token_usage:
    db.log_token_usage(
        query_text=state.query[:200],
        **entry,
    )
```

This keeps DB writes out of phase modules and centralises the concern in the orchestrator.

---

## 3. Admin View

### New section in `admin.html`

"Token Usage" section added below "Content Updates", above "Curator Access". Contains:
- A time window `<select>` (7 days / 30 days / 90 days / All time), default 30 days
- Summary table (by model × operation)
- Per-query table (recent queries)

The section is rendered as an HTMX fragment via `GET /admin/token-usage?days=N`, swapped on `<select>` change. Same structural pattern as the existing status sections.

### Summary table

| Model | Operation | Calls | Input Tokens | Output Tokens | Total |
|-------|-----------|------:|-------------:|--------------:|------:|
| claude-sonnet-4-6 | scan | 95 | 12.4M | 380K | 12.8M |
| claude-sonnet-4-6 | rationale | 42 | 890K | 168K | 1.1M |
| claude-haiku-4-5 | triage | 42 | 240K | 84K | 324K |

Token counts formatted as K/M suffixes in the summary table.

### Per-query table

| Query | Haiku in | Haiku out | Sonnet in | Sonnet out | Total | Time |
|-------|----------|-----------|-----------|------------|-------|------|
| "OpenShift booth for..." | 12K | 1.2K | 45K | 3.8K | 62K | 2026-04-13 14:22 |

Raw counts shown (not K/M) since per-query volumes are smaller.

Queries are grouped by matching `query_text` + a 1-minute time bucket to pair triage and rationale rows from the same pipeline run. Implementation may choose to instead pass a `session_id` UUID through the pipeline and store it on each row — simpler and more reliable grouping, at the cost of a slightly wider schema. Either approach is valid; the implementer should choose at build time.

### New route

`GET /admin/token-usage` in `admin.py`:
- Accepts `days` query param (int, default 30; `0` = all time)
- Calls `db.get_token_stats(days)` and `db.get_recent_queries(days)`
- Returns standalone HTML fragment (no full page render)

---

## 4. Out of Scope

- Cost estimation (no per-token pricing logic in this iteration)
- Per-user token attribution
- Token usage alerts or budgets
