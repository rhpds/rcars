# Rec Card: Duration Labels + Best Fit Button — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add curated duration overrides with source labeling to recommendation cards, redesign the "Best Fit" button to be visually prominent, and fix acronym case sensitivity + card copy/paste bugs.

**Architecture:** New `curated_duration_min` column on `showroom_analysis` with Alembic migration, curator REST endpoint, and `duration_source` field threaded through the recommendation pipeline → SSE → frontend. Frontend changes to RecCard header/pills, Best Fit button styling, and Browse page curator input.

**Tech Stack:** Python 3.11 / FastAPI / Alembic / PostgreSQL, React 19 / TypeScript / Vite

---

### Task 1: Alembic Migration — `curated_duration_min` column

**Files:**
- Create: `src/api/alembic/versions/003_curated_duration.py`
- Modify: `src/api/rcars/db/database.py` (SCHEMA_SQL block, lines 57-78)

- [ ] **Step 1: Create migration file**

```python
# src/api/alembic/versions/003_curated_duration.py
"""Add curated_duration_min to showroom_analysis.

Revision ID: 003
Revises: 002
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE showroom_analysis
            ADD COLUMN IF NOT EXISTS curated_duration_min INTEGER;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE showroom_analysis
            DROP COLUMN IF EXISTS curated_duration_min;
    """)
```

- [ ] **Step 2: Add column to SCHEMA_SQL in database.py**

In `src/api/rcars/db/database.py`, add `curated_duration_min INTEGER,` after the existing `estimated_duration_min INTEGER,` line inside the `CREATE TABLE IF NOT EXISTS showroom_analysis` block. This ensures new installs (via `rcars init-db`) get the column without running migrations.

- [ ] **Step 3: Run migration locally**

```bash
cd /Users/nstephan/devel/rcars-advisory/src/api
source ~/.virtualenvs/rcars-v2/bin/activate
alembic upgrade head
```

Expected: migration applies cleanly, column exists.

- [ ] **Step 4: Verify column exists**

```bash
psql rcars -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'showroom_analysis' AND column_name = 'curated_duration_min';"
```

Expected: one row returned.

- [ ] **Step 5: Commit**

```bash
git add src/api/alembic/versions/003_curated_duration.py src/api/rcars/db/database.py
git commit -m "database: Add curated_duration_min column to showroom_analysis"
```

---

### Task 2: Database Method + API Endpoint for Curated Duration

**Files:**
- Modify: `src/api/rcars/db/database.py` (add method after `set_enrichment_note` around line 650)
- Modify: `src/api/rcars/api/routes/catalog.py` (add endpoint after `set_content_path` around line 269)
- Modify: `src/frontend/src/services/api.ts` (add client method)

- [ ] **Step 1: Add `set_curated_duration` method to Database class**

In `src/api/rcars/db/database.py`, add after the `set_enrichment_review_flag` method (line ~657):

```python
    def set_curated_duration(self, ci_name: str, duration_min: int | None, updated_by: str | None = None) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET curated_duration_min = %s WHERE ci_name = %s",
                (duration_min, ci_name),
            )
            conn.commit()
        logger.info("curated_duration_set", ci_name=ci_name, duration_min=duration_min, updated_by=updated_by)
```

- [ ] **Step 2: Add API endpoint in catalog routes**

In `src/api/rcars/api/routes/catalog.py`, add after the `set_content_path` endpoint (line ~269):

```python
class DurationRequest(BaseModel):
    duration_min: int | None = None


@router.put("/{ci_name}/duration")
async def set_duration(ci_name: str, body: DurationRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_curated_duration(ci_name, body.duration_min, updated_by=user)
    return {"status": "ok"}
```

- [ ] **Step 3: Add API client method**

In `src/frontend/src/services/api.ts`, add after the `overrideUrl` method (line ~91):

```typescript
  setCuratedDuration: (ciName: string, durationMin: number | null) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/duration`, {
      method: 'PUT',
      body: JSON.stringify({ duration_min: durationMin }),
    }),
```

- [ ] **Step 4: Verify endpoint works**

```bash
curl -s -X PUT http://localhost:8080/api/v1/catalog/parasol-insurance-rosa/duration \
  -H 'Content-Type: application/json' \
  -d '{"duration_min": 120}' | python3 -m json.tool
```

Expected: `{"status": "ok"}`

```bash
psql rcars -c "SELECT ci_name, curated_duration_min FROM showroom_analysis WHERE ci_name = 'parasol-insurance-rosa';"
```

Expected: `curated_duration_min = 120`

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/database.py src/api/rcars/api/routes/catalog.py src/frontend/src/services/api.ts
git commit -m "catalog: Add curator endpoint for curated duration"
```

---

### Task 3: Thread `duration_source` Through the Recommendation Pipeline

**Files:**
- Modify: `src/api/rcars/services/recommender/models.py` (add field)
- Modify: `src/api/rcars/services/recommender/vector_search.py` (lines ~107-122, set source)
- Modify: `src/api/rcars/services/recommender/pipeline.py` (lines ~94-117, guard penalty)
- Modify: `src/api/rcars/workers/recommend.py` (lines ~41-58, serialize)
- Modify: `src/api/rcars/services/recommender/pipeline.py` (`serialize_candidates` function, lines ~164-176)

- [ ] **Step 1: Add `duration_source` to Candidate model**

In `src/api/rcars/services/recommender/models.py`, add after `duration_min: int | None` (line 19):

```python
    duration_source: str = "ai"  # "curated" | "ai"
```

- [ ] **Step 2: Set `duration_source` in vector search**

In `src/api/rcars/services/recommender/vector_search.py`, replace the `duration_min` assignment inside the `Candidate(...)` constructor (line ~115):

Change:
```python
            duration_min=(analysis or {}).get("estimated_duration_min"),
```

To:
```python
            duration_min=(analysis or {}).get("curated_duration_min") or (analysis or {}).get("estimated_duration_min"),
            duration_source="curated" if (analysis or {}).get("curated_duration_min") is not None else "ai",
```

- [ ] **Step 3: Guard duration penalty on curated source**

In `src/api/rcars/services/recommender/pipeline.py`, in `_apply_duration_penalty`, add a source check. Change the existing guard (lines ~100-103):

```python
    for c in candidates:
        if c.relevance_score is None or c.duration_min is None:
            continue
        if c.duration_min <= target_min:
            continue
```

To:
```python
    for c in candidates:
        if c.relevance_score is None or c.duration_min is None:
            continue
        if c.duration_source != "curated":
            continue
        if c.duration_min <= target_min:
            continue
```

- [ ] **Step 4: Add `duration_min` and `duration_source` to `serialize_candidates`**

In `src/api/rcars/services/recommender/pipeline.py`, in the `serialize_candidates` function (line ~164), add two fields to the dict. After `"catalog_namespace": c.catalog_namespace,` add:

```python
                "duration_min": c.duration_min, "duration_source": c.duration_source,
```

- [ ] **Step 5: Add `duration_min` and `duration_source` to worker serialization**

In `src/api/rcars/workers/recommend.py`, in the `candidates_json` list comprehension (line ~41), add two fields to the dict. After `"catalog_namespace": c.catalog_namespace,` add:

```python
                "duration_min": c.duration_min,
                "duration_source": c.duration_source,
```

- [ ] **Step 6: Verify pipeline end-to-end**

Restart the recommend worker, submit a query, and check the job result JSON includes `duration_min` and `duration_source` for each candidate:

```bash
curl -s http://localhost:8080/api/v1/advisor/query/JOB_ID/result | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data.get('result', {}).get('candidates', [])[:3]:
    print(f\"{c['ci_name']}: duration_min={c.get('duration_min')}, source={c.get('duration_source')}\")
"
```

Expected: each candidate has `duration_min` (int or null) and `duration_source` ("ai" or "curated").

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/services/recommender/models.py src/api/rcars/services/recommender/vector_search.py src/api/rcars/services/recommender/pipeline.py src/api/rcars/workers/recommend.py
git commit -m "recommender: Thread duration_source through pipeline and serialization"
```

---

### Task 4: Frontend — Duration on Rec Cards

**Files:**
- Modify: `src/frontend/src/hooks/useJobStream.ts` (StreamCandidate interface, lines ~9-23)
- Modify: `src/frontend/src/components/advisor/RecCard.tsx` (Candidate interface + rendering)

- [ ] **Step 1: Add fields to `StreamCandidate` type**

In `src/frontend/src/hooks/useJobStream.ts`, add two fields to the `StreamCandidate` interface after `caveats: string | null` (line 22):

```typescript
  duration_min: number | null
  duration_source: string | null
```

- [ ] **Step 2: Add fields to RecCard's `Candidate` interface**

In `src/frontend/src/components/advisor/RecCard.tsx`, add two fields to the `Candidate` interface after `caveats: string | null` (line 18):

```typescript
  duration_min: number | null
  duration_source: string | null
```

- [ ] **Step 3: Add duration to rec card header**

In `src/frontend/src/components/advisor/RecCard.tsx`, in the `rec-card-header` div, add a duration display between the title/meta div and the expand hint span. Replace:

```tsx
        <span className="rec-expand-hint">{expanded ? '▾' : '▸'}</span>
```

With:

```tsx
        {candidate.duration_min && (
          <span style={{ fontSize: '14px', color: '#999', fontWeight: 500, flexShrink: 0 }}>
            ~{candidate.duration_min} min
          </span>
        )}
        <span className="rec-expand-hint">{expanded ? '▾' : '▸'}</span>
```

- [ ] **Step 4: Add duration+source pill in expanded view**

In `src/frontend/src/components/advisor/RecCard.tsx`, in the pill row section where `suggested_format` is rendered (lines ~88-92), add a duration pill. Replace:

```tsx
          {candidate.suggested_format && (
            <div className="rec-pill-row">
              <span className="rec-pill pill-format">{candidate.suggested_format}</span>
              {candidate.duration_notes && <span className="rec-pill">{candidate.duration_notes}</span>}
            </div>
          )}
```

With:

```tsx
          {(candidate.suggested_format || candidate.duration_min) && (
            <div className="rec-pill-row">
              {candidate.duration_min && (
                <span className="rec-pill">
                  ~{candidate.duration_min} min ({candidate.duration_source === 'curated' ? 'estimated' : 'AI estimate'})
                </span>
              )}
              {candidate.suggested_format && <span className="rec-pill pill-format">{candidate.suggested_format}</span>}
              {candidate.duration_notes && <span className="rec-pill">{candidate.duration_notes}</span>}
            </div>
          )}
```

- [ ] **Step 5: Verify in browser**

Open http://localhost:3000, submit a query. Verify:
- Duration appears right-aligned in card header (e.g. "~120 min")
- When expanded, a pill shows "~120 min (AI estimate)" alongside the format pill
- Cards without duration show no duration elements

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/hooks/useJobStream.ts src/frontend/src/components/advisor/RecCard.tsx
git commit -m "frontend: Add duration labels to recommendation cards"
```

---

### Task 5: Frontend — Best Fit Button Redesign

**Files:**
- Modify: `src/frontend/src/components/advisor/RecCard.tsx` (button markup, lines ~120-131)
- Modify: `src/frontend/src/styles/lcars.css` (add new class)

- [ ] **Step 1: Add `.btn-best-fit` CSS class**

In `src/frontend/src/styles/lcars.css`, add after the `.btn-curator.secondary` rule (line ~388):

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

- [ ] **Step 2: Update button in RecCard**

In `src/frontend/src/components/advisor/RecCard.tsx`, replace the Best Fit button section (lines ~120-131):

```tsx
            {isComplete && (tier === 'green' || tier === 'yellow') && (
              selected ? (
                <span style={{ color: '#5cb85c', fontSize: '13px' }}>✓ Best fit</span>
              ) : (
                <button
                  className="btn-curator"
                  title="Helps us improve recommendations by tracking which results are most useful"
                  onClick={(e) => { e.stopPropagation(); handleSelect() }}
                >
                  Best fit
                </button>
              )
            )}
```

With:

```tsx
            {isComplete && (tier === 'green' || tier === 'yellow') && (
              selected ? (
                <span style={{ color: '#5cb85c', fontSize: '14px', fontWeight: 600 }}>✓ Best fit</span>
              ) : (
                <button
                  className="btn-best-fit"
                  title="Helps us improve recommendations by tracking which results are most useful"
                  onClick={(e) => { e.stopPropagation(); handleSelect() }}
                >
                  ★ This is the best fit
                </button>
              )
            )}
```

- [ ] **Step 3: Verify in browser**

Open http://localhost:3000, submit a query, expand a green-tier card. Verify:
- Button reads "★ THIS IS THE BEST FIT" (uppercase, bold green outline)
- Clicking it shows "✓ Best fit" confirmation text
- Button is visually prominent — clearly an action, not a label

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/components/advisor/RecCard.tsx src/frontend/src/styles/lcars.css
git commit -m "frontend: Redesign Best Fit button with bold outline treatment"
```

---

### Task 6: Browse Page — Curator Duration Input

**Files:**
- Modify: `src/frontend/src/pages/BrowsePage.tsx` (add state + input field + handler)

- [ ] **Step 1: Add `curated_duration_min` to `ItemDetail.analysis` interface**

In `src/frontend/src/pages/BrowsePage.tsx`, in the `analysis` property of `ItemDetail` (line ~49), add after `estimated_duration_min: number | null`:

```typescript
    curated_duration_min: number | null
```

- [ ] **Step 2: Add `curatedDurations` state**

In `src/frontend/src/pages/BrowsePage.tsx`, add after the `overrideUrls` state (line ~133):

```typescript
  const [curatedDurations, setCuratedDurations] = useState<Record<string, string>>({})
```

- [ ] **Step 3: Initialize duration state when detail loads**

In `src/frontend/src/pages/BrowsePage.tsx`, in the `handleExpand` function, add after the `setOverrideUrls` line (line ~238):

```typescript
      setCuratedDurations(prev => ({
        ...prev,
        [ciName]: detail.analysis?.curated_duration_min != null ? String(detail.analysis.curated_duration_min) : '',
      }))
```

- [ ] **Step 4: Add duration save handler**

In `src/frontend/src/pages/BrowsePage.tsx`, add after the `handleOverrideUrl` function (line ~301):

```typescript
  const handleSetDuration = async (ciName: string) => {
    const val = curatedDurations[ciName]?.trim()
    const durationMin = val ? parseInt(val, 10) : null
    if (val && isNaN(durationMin!)) return
    await api.setCuratedDuration(ciName, durationMin)
  }
```

- [ ] **Step 5: Add duration input field in curator section**

In `src/frontend/src/pages/BrowsePage.tsx`, in the curator section (inside `{auth.isCurator && ( ... )}`), add after the note input (line ~584) and before the override URL input:

```tsx
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                          <input
                            type="number"
                            value={curatedDurations[item.ci_name] ?? ''}
                            onChange={(e) => setCuratedDurations(prev => ({ ...prev, [item.ci_name]: e.target.value }))}
                            onBlur={() => handleSetDuration(item.ci_name)}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleSetDuration(item.ci_name) }}
                            placeholder={detail.analysis?.estimated_duration_min ? `${detail.analysis.estimated_duration_min} (AI)` : 'Duration (min)'}
                            style={{ background: 'var(--bg-card)', border: '1px solid #333', color: '#aaa', padding: '6px 10px', borderRadius: '4px', fontSize: '13px', width: '160px', outline: 'none' }}
                          />
                          <span style={{ fontSize: '12px', color: '#666' }}>Duration (min)</span>
                        </div>
```

- [ ] **Step 6: Verify in browser**

Open http://localhost:3000/browse, expand a CI that has analysis. Verify:
- Duration input shows in curator section
- Placeholder shows AI estimate (e.g. "120 (AI)") when no curated value exists
- Typing a number and pressing Enter or clicking away saves it
- Clearing the field and blurring sends `null` (clears curated duration)

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/pages/BrowsePage.tsx
git commit -m "browse: Add curator duration input field"
```

---

### Task 7: Bug Fix Commits (Already Applied)

The acronym case sensitivity fix and card copy/paste fix were already applied during brainstorming. They just need to be committed.

**Files (already modified):**
- `src/api/rcars/services/recommender/pipeline.py` (acronym `re.IGNORECASE` + `.upper()`)
- `src/frontend/src/components/advisor/RecCard.tsx` (onClick on header only)
- `src/frontend/src/styles/lcars.css` (removed `cursor: pointer` from `.rec-card`)

- [ ] **Step 1: Commit acronym fix**

```bash
git add src/api/rcars/services/recommender/pipeline.py
git commit -m "recommender: Fix case-insensitive acronym matching in query expansion"
```

- [ ] **Step 2: Commit card copy/paste fix**

```bash
git add src/frontend/src/components/advisor/RecCard.tsx src/frontend/src/styles/lcars.css
git commit -m "frontend: Fix rec card copy/paste by scoping click handler to header"
```

---

### Task 8: Full Integration Test

- [ ] **Step 1: Restart all services**

```bash
cd /Users/nstephan/devel/rcars-advisory
./dev-services.sh stop && ./dev-services.sh start
```

- [ ] **Step 2: Test acronym fix**

In the browser at http://localhost:3000, submit query: "fraud detection using rhoai"
Expected: results returned (not "No matching content found")

- [ ] **Step 3: Test duration display on rec cards**

Submit any query. Verify:
- Card headers show duration right-aligned (e.g. "~120 min")
- Expanded cards show duration pill with source label
- Cards with no duration data show no duration elements

- [ ] **Step 4: Test Best Fit button**

Expand a green-tier card. Verify:
- Button shows "★ THIS IS THE BEST FIT" with bold green outline
- Click toggles to "✓ Best fit" text

- [ ] **Step 5: Test card copy/paste**

Expand a card, try to select and copy text from "Why it fits" or "How to use". Verify:
- Text is selectable without collapsing the card
- Clicking the header still toggles expand/collapse

- [ ] **Step 6: Test curator duration on Browse page**

Go to http://localhost:3000/browse, expand a CI. Verify:
- Duration input appears in curator section
- Setting a value persists (refresh and re-expand to confirm)
- After setting a curated duration, run a new advisor query — the card should show the curated value

- [ ] **Step 7: Test duration penalty guard**

Set a curated duration on one CI to something very short (e.g. 15 min). Submit a query mentioning "30 minute" with hard limit. Verify:
- The curated-duration CI gets penalized if it exceeds the target
- CIs with only AI-estimated durations are NOT penalized (their scores are unchanged)
