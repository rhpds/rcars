# Rec Card: Duration Labels + Best Fit Button

**Date:** 2026-06-15
**Status:** Approved

## Overview

Three changes to recommendation cards in the Advisor UI, plus two bug fixes discovered during investigation.

## 1. Duration Field Labeling

Duration data quality is poor — `estimated_duration_min` is an LLM guess with no ground truth. This adds a curated override and labels the source on rec cards.

### Backend

**Database — Alembic migration `003_curated_duration.py`:**
- Add `curated_duration_min` (nullable INTEGER) column to `showroom_analysis` table
- Add column to `SCHEMA_SQL` in `database.py` for new installs

**Database — new method on `Database` class:**
- `set_curated_duration(ci_name: str, duration_min: int | None, updated_by: str)` — UPDATE `showroom_analysis` SET `curated_duration_min`

**API — new curator endpoint in `routes/catalog.py`:**
- `PUT /catalog/{ci_name}/duration` — requires `require_curator`
- Pydantic body: `DurationRequest { duration_min: int | None }`
- Calls `db.set_curated_duration(ci_name, body.duration_min, user)`
- Returns `{"status": "ok"}`
- Follows the existing note/flag/content-path pattern

**Candidate model (`services/recommender/models.py`):**
- Add field: `duration_source: str = "ai"` — either `"curated"` or `"ai"`

**Vector search (`services/recommender/vector_search.py`):**
- When building `Candidate` at line ~115: read `curated_duration_min` from analysis
- If `curated_duration_min` is not None: use it for `duration_min`, set `duration_source = "curated"`
- Otherwise: use `estimated_duration_min`, set `duration_source = "ai"`

**Duration penalty (`services/recommender/pipeline.py:_apply_duration_penalty`):**
- Add guard: skip penalty when `c.duration_source != "curated"`
- AI guesses should never affect scoring — only curated durations are trustworthy enough to penalize

**Serialization (`workers/recommend.py` + `pipeline.py:serialize_candidates`):**
- Add `duration_min` and `duration_source` to the candidate JSON dict in both serialization points

### Frontend

**StreamCandidate type (`hooks/useJobStream.ts`):**
- Add `duration_min: number | null`
- Add `duration_source: string | null`

**RecCard candidate interface (`components/advisor/RecCard.tsx`):**
- Add `duration_min: number | null`
- Add `duration_source: string | null`

**RecCard header row:**
- Show `~{duration_min} min` right-aligned in the header, next to the expand hint
- No source label in header — just the number, clean and scannable
- Only show when `duration_min` is not null

**RecCard pill row (expanded):**
- Add a duration+source pill before the existing pills
- Format: `"~120 min (AI estimate)"` when `duration_source === "ai"`
- Format: `"~120 min (estimated)"` when `duration_source === "curated"`
- Keep `duration_notes` from the LLM as a separate pill after format (it contains adaptation advice like "drop Module 3 for 45 min")

**Browse page detail card:**
- Add inline number input for curated duration, curator-only
- Placement: near existing note/content_path curator fields
- Label: "Duration (min)"
- On blur or Enter: call `PUT /catalog/{ci_name}/duration`
- Show current value from `analysis.curated_duration_min`, fall back to placeholder showing `analysis.estimated_duration_min` with "(AI)" suffix

## 2. Best Fit Button Redesign

Current `btn-curator` styled button looks like a passive label and gets lost.

**RecCard changes (`components/advisor/RecCard.tsx`):**
- Rename button text from `"Best fit"` to `"★ This is the best fit"`
- Add new CSS class `btn-best-fit` (don't modify `btn-curator` which is used elsewhere)
- Selected state remains: `"✓ Best fit"` as green text (no button)

**CSS (`styles/lcars.css`) — new `.btn-best-fit` class:**
```css
.btn-best-fit {
  background: transparent;
  border: 2px solid #5cb85c;
  color: #5cb85c;
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
```

## 3. Bug Fixes (already applied)

**Acronym case sensitivity (`services/recommender/pipeline.py`):**
- `_ACRONYM_RE` compiled with `re.IGNORECASE`
- `_expand_acronyms` normalizes match to uppercase via `m.group(0).upper()` for dict lookup
- Fixes: "rhoai" now matches like "RHOAI"

**Card copy/paste (`components/advisor/RecCard.tsx`):**
- `onClick` handler moved from `LcarsCard` to `rec-card-header` div only
- `cursor: pointer` moved from `.rec-card` CSS to inline on header
- Expanded card content is now freely selectable for copy/paste

## Files Changed

| File | Change |
|------|--------|
| `src/api/alembic/versions/003_curated_duration.py` | New migration: add `curated_duration_min` column |
| `src/api/rcars/db/database.py` | Add column to SCHEMA_SQL, add `set_curated_duration()` method |
| `src/api/rcars/api/routes/catalog.py` | Add `PUT /{ci_name}/duration` endpoint |
| `src/api/rcars/services/recommender/models.py` | Add `duration_source` field to `Candidate` |
| `src/api/rcars/services/recommender/vector_search.py` | Use curated duration when available, set source |
| `src/api/rcars/services/recommender/pipeline.py` | Guard duration penalty on `duration_source == "curated"`, acronym fix (done) |
| `src/api/rcars/workers/recommend.py` | Add `duration_min` + `duration_source` to serialized JSON |
| `src/frontend/src/hooks/useJobStream.ts` | Add `duration_min`, `duration_source` to `StreamCandidate` |
| `src/frontend/src/components/advisor/RecCard.tsx` | Duration in header + pills, best fit button, copy/paste fix (done) |
| `src/frontend/src/styles/lcars.css` | Add `.btn-best-fit` class, remove cursor from `.rec-card` (done) |
| `src/frontend/src/pages/BrowsePage.tsx` | Add curator duration input field |
| `src/frontend/src/services/api.ts` | Add `setCuratedDuration()` method |
