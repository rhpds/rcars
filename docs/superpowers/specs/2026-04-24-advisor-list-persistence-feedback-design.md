# Advisor List, Query Persistence & Feedback Design

**Date:** 2026-04-24
**Status:** Design approved, pending implementation

## Summary

Three sequential features for the RCARS advisor, each independently deployable:

1. **Full advisory list with color tiers** — stop dropping results after triage; keep all candidates visible throughout, annotated by tier (green/yellow/white), sorted by tier then score.
2. **Query results persistence** — store every query and its full result list in the DB per turn, with opt-out support.
3. **"This fits best" button** — one-click selection logging on rec cards, linked back to the persisted session turn.

---

## Spec 1: Full Advisory List with Color Tiers

### Tier definitions

| Tier | Condition | Visual |
|------|-----------|--------|
| `green` | Relevant (Haiku) + rationale generated (Sonnet) | Green card border/header |
| `yellow` | Relevant (Haiku) but below Sonnet top-N cut | Amber card border/header |
| `white` | Surfaced by vector search, Haiku said not relevant | Neutral, no highlight |

**Sort order:** Green first → Yellow → White. Within each tier: green by `fit_score` (Sonnet), yellow by `relevance_score` (Haiku), white by `vector_similarity_pct`.

### Pipeline changes

Currently, non-relevant candidates are **dropped** after Haiku triage. The change: carry **all candidates through every phase**. Nothing is removed — items are annotated with a tier.

**Phase-by-phase behavior:**
- `VECTOR_DONE` → all candidates shown as `white`, sorted by vector similarity
- `TRIAGE_DONE` → relevant items promoted to `yellow`, non-relevant stay `white`, list resorts
- `COMPLETE` → top Sonnet picks promoted to `green`, list resorts again

Sonnet rationale still only runs on the top N relevant items — no change to cost or logic there.

### Files

| File | Change |
|------|--------|
| `src/rcars/recommender/models.py` | Add `tier: str = "white"` field to `Candidate` |
| `src/rcars/recommender/triage.py` | Remove filter that drops non-relevant candidates; set `tier = "yellow"` on relevant ones |
| `src/rcars/recommender/pipeline.py` | Pass full candidate list at each phase; assign `tier = "green"` on Sonnet survivors |
| `src/rcars/web/routes/advisor.py` | `_candidates_to_recs()`: add tier-based sort; `_run_advisor_query()`: pass full list at each phase |
| `src/rcars/web/templates/fragments/rec_card.html` | Tier-based border/header color |
| `src/rcars/web/templates/fragments/rec_list.html` | Remove any list-level filtering |

---

## Spec 2: Query Results Persistence

### Schema

New `advisor_sessions` table:

```sql
CREATE TABLE advisor_sessions (
    id              SERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL,
    turn_index      INTEGER NOT NULL,
    user_email      TEXT,
    query_text      TEXT,
    event_url       TEXT,
    results_json    JSONB,
    overall_assessment TEXT,
    chosen_ci_name  TEXT,
    chosen_at       TIMESTAMPTZ,
    opted_out       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_advisor_sessions_session ON advisor_sessions(session_id);
CREATE INDEX idx_advisor_sessions_user ON advisor_sessions(user_email);
CREATE INDEX idx_advisor_sessions_created ON advisor_sessions(created_at);
```

**Per-turn storage:** one row per query/response pair, linked by `session_id`. A 3-turn conversation = 3 rows.

**`results_json` structure:**
```json
[
  {
    "ci_name": "openshift-cnv.some-lab.prod",
    "display_name": "Some Lab",
    "tier": "green",
    "fit_score": 92,
    "relevance_score": 85,
    "vector_similarity_pct": 78,
    "stage": "prod"
  }
]
```

**Opted-out rows:** write the row with `opted_out=TRUE`, NULL for `query_text`, `results_json`, and `overall_assessment`. We know a query happened without knowing what it was.

**NO_MATCHES:** write a row even with no results — useful to know what queries find nothing.

### Opt-out UI

Small "Don't save this query" toggle next to the Send button in the advisor. Default: **opted in**. Toggle applies to the next sent message only (resets after each send).

### Write timing

At `COMPLETE` (or `NO_MATCHES`) phase in `_run_advisor_query()`, after all results are final. One `db.log_advisor_session()` call.

### DB method

```python
def log_advisor_session(
    self, session_id: str, turn_index: int, user_email: str,
    query_text: str | None, event_url: str | None,
    results: list[dict], overall_assessment: str | None,
    opted_out: bool = False,
) -> int:
    """Insert a session turn row. Returns the row id."""
```

### Migration

Migration 005: create `advisor_sessions` table.

### Files

| File | Change |
|------|--------|
| `src/rcars/db.py` | Migration 005, `log_advisor_session()`, `update_advisor_session_choice()` |
| `src/rcars/web/routes/advisor.py` | Call `log_advisor_session()` at COMPLETE/NO_MATCHES; store row `id` in `_query_status` for feedback use |
| `src/rcars/web/templates/advisor.html` | "Don't save this query" toggle next to Send button |

---

## Spec 3: "This Fits Best" Button

### Behavior

Button on each completed rec card (green or yellow tier, after `COMPLETE` phase). On click:
- Immediate visual: button turns into green checkmark, no modal
- POST to `/advisor/select` with `{session_id, turn_index, ci_name}`
- If another card in the same turn was previously selected, that card reverts to unselected
- Only one selection per turn

### Data model

Two columns on the existing `advisor_sessions` row (not a separate table for v1):
- `chosen_ci_name TEXT` — which CI was selected
- `chosen_at TIMESTAMPTZ` — when

### API endpoint

```
POST /advisor/select
Body: session_id, turn_index, ci_name
Response: updated button HTML (green checkmark)
```

Updates `advisor_sessions` row for the given `session_id + turn_index`.

### Template requirements

Each rec card needs `session_id` and `turn_index` in its render context to construct the POST payload. Both are already available in the advisor's result rendering.

Button only rendered on cards where `card_phase == "complete"` — not during streaming or on white-tier cards.

### Files

| File | Change |
|------|--------|
| `src/rcars/db.py` | `update_advisor_session_choice(session_id, turn_index, ci_name)` |
| `src/rcars/web/routes/advisor.py` | `POST /advisor/select` route |
| `src/rcars/web/templates/fragments/rec_card.html` | "This fits best" button + selected state |
