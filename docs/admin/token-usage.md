---
title: Token Usage Tracking
description: How RCARS tracks and reports Anthropic API token consumption
---

# Token Usage Tracking

RCARS logs every Anthropic API call to PostgreSQL so that operators can see cumulative costs, identify expensive queries, and understand model utilization over time. The data is surfaced in the admin view as a time-windowed summary table and a per-query breakdown.

## What Is Tracked

Four types of operations produce token usage records:

| Operation | Model | When it fires |
|-----------|-------|---------------|
| `scan` | claude-sonnet-4-6 | Each Showroom analysis run by the scan worker |
| `triage` | claude-haiku-4-5 | Each advisor query (phase 2 — relevance scoring) |
| `rationale` | claude-sonnet-4-6 | Each advisor query that produces results (phase 3 — rationale generation) |
| `event_parse` | claude-sonnet-4-6 | When an advisor query contains a URL and event content is extracted |

A single advisor query produces two to three records: one triage, one rationale (if matches found), and one event_parse (if the query contained a URL). A triage call that returns no matches still logs its tokens — the API was called and resources were consumed regardless of outcome.

Catalog sync (`rcars refresh`) and stale checks (`rcars check-stale`) make no Anthropic API calls and produce no token records.

## Database Schema

```sql
CREATE TABLE token_usage (
    id            SERIAL PRIMARY KEY,
    operation     TEXT NOT NULL,        -- 'scan' | 'triage' | 'rationale' | 'event_parse'
    model         TEXT NOT NULL,        -- e.g. 'claude-sonnet-4-6'
    ci_name       TEXT,                 -- scan ops: the CI being analyzed
    query_text    TEXT,                 -- query ops: the user's question (≤200 chars)
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

`ci_name` and `query_text` are mutually exclusive: scan records populate `ci_name`, query records populate `query_text`. Neither has a foreign key — token history is preserved even if a CI is later removed from the catalog.

## Data Flow

### Scan tokens

When `rcars scan` calls `analyze_showroom()`, the Anthropic response includes a `usage` object. The analyzer reads `input_tokens` and `output_tokens` and writes a row immediately after the API call completes:

```
rcars scan
  → analyze_showroom(ci_name=..., db=db, ...)
    → anthropic_client.messages.create(...)
    → db.log_token_usage(operation="scan", model=..., ci_name=..., ...)
```

### Query tokens

The advisor recommendation pipeline runs in three phases. Token capture happens in phases 2 and 3 without requiring direct database access in the individual phase modules:

```
run_query(query, db, ...)
  → phase 1: vector search (no API call)
  → phase 2: triage(state, ...)
      → anthropic_client.messages.create(...)     # Haiku call
      → returns QueryState(token_usage=[triage_entry])
  → phase 3: generate_rationale(state, ...)
      → anthropic_client.messages.create(...)     # Sonnet call
      → returns QueryState(token_usage=[triage_entry, rationale_entry])
  → for entry in state.token_usage:
      db.log_token_usage(query_text=query[:200], **entry)
```

Token entries accumulate on `QueryState.token_usage` as the pipeline progresses. The pipeline orchestrator writes them all to the database in a single pass after the final phase, ensuring that query text is attached to both the triage and rationale records for that query.

If triage returns no matches (NO_MATCHES), the pipeline writes the triage tokens before exiting — the API call happened and should be accounted for even though no recommendations were returned.

## Admin View Queries

Two database methods back the admin view:

**`get_token_stats(days=30)`** — aggregates by `(operation, model)` for the selected time window:

```sql
SELECT operation, model,
       COUNT(*) AS calls,
       SUM(input_tokens) AS input_tokens,
       SUM(output_tokens) AS output_tokens,
       SUM(input_tokens + output_tokens) AS total_tokens
FROM token_usage
WHERE created_at >= NOW() - <days> * INTERVAL '1 day'
GROUP BY operation, model
ORDER BY total_tokens DESC
```

Pass `days=None` for all-time totals.

**`get_recent_queries(days=30, limit=50)`** — groups triage and rationale records from the same pipeline run by `(query_text, 1-minute bucket)`, pivoting them into side-by-side Haiku and Sonnet columns:

```sql
SELECT query_text, date_trunc('minute', created_at) AS query_time,
       SUM(CASE WHEN operation = 'triage' THEN input_tokens ELSE 0 END) AS triage_input,
       ...
FROM token_usage
WHERE operation IN ('triage', 'rationale')
GROUP BY query_text, date_trunc('minute', created_at)
ORDER BY query_time DESC
```

> **Grouping note:** Two identical queries submitted within the same calendar minute will be merged into one row in the per-query table. This is acceptable for typical traffic volumes. A future revision could add a `pipeline_run_id` column for exact grouping if needed.

## Cost Estimation

Token pricing is not currently applied — the admin view shows raw token counts only. Cost figures can be derived externally using the Anthropic pricing page:

- **Haiku 4.5** — triage operations (lower cost, high volume)
- **Sonnet 4.6** — scan and rationale operations (higher cost, lower volume)

The summary table's model × operation breakdown makes this calculation straightforward.
