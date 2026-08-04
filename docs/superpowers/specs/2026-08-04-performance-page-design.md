# Performance Page Design

**Jira:** [RHDPCD-662](https://redhat.atlassian.net/browse/RHDPCD-662) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Date:** 2026-08-04
**Status:** Design
**Related:** [Generalized Content Model](2026-07-20-generalized-content-model-design.md), [RHDPCD-661](https://redhat.atlassian.net/browse/RHDPCD-661) (Without Prod standalone page)

## Problem

The current Retirement Analysis page at `/analysis/retirement` was designed to identify retirement candidates. The data model has evolved — `performance_channels` and `performance_scores` replace `reporting_metrics`, supporting multiple data channels (sales, marketing) and content types beyond Babylon. The UI needs to reflect this shift:

1. **Branding mismatch** — the page is called "Retirement Analysis" but the underlying model is about performance measurement. Higher scores should mean better performance, not stronger retirement candidates.
2. **Layout inconsistency** — Browse uses a sidebar filter pattern with expandable rows. Retirement uses a different layout with inline filter chips and a separate expanded filters panel. These should be unified.
3. **Single-channel assumption** — the current page only shows RHDP sales data. The data model supports multiple channels (sales, marketing), each with different metrics and scoring formulas.
4. **No URL state** — all filter state is ephemeral. The advisor's deep-link to `?search=...` is silently ignored because the page never reads `useSearchParams`.
5. **"Without Prod" conflation** — the page mixes performance analysis (Prod tab) with a catalog-owner tool (Without Prod tab) that serves a different purpose.

## Design

### 1. Route & Navigation

| Current | New |
|---------|-----|
| `/analysis/retirement` | `/analysis/performance` |
| Nav: "Retirement" under Analysis | Nav: "Performance" under Analysis |

The frontend route `/analysis/retirement` is removed (no redirect needed — internal only). All retirement workflow API endpoints move under `/analysis/performance/workflow/...`. Overlap stays at `/analysis/overlap`. Both remain under the Analysis nav section.

### 2. Access Control

| Role | Can See | Cannot See |
|------|---------|------------|
| Authenticated user | Performance scores, volume metrics (provisions, users, experiences), Data column (S/M tags), expanded row metrics, marketing addendum | Retirement workflow controls, Retirement Status filter |
| Curator | Everything above + Retirement Workflow (stepper, mute, notes), Retirement Status filter | — |
| Admin | Everything above + admin toggle to disable page visibility for non-curators | — |

Financial metrics (touched, closed, cost) are visible to all authenticated users. These are aggregate platform metrics, not individual deal data — the same visibility level as the advisor's performance summary blocks.

The admin toggle is an environment variable (`RCARS_PERFORMANCE_PUBLIC`, default `true`). When `false`, the page reverts to curator-only access (same as current retirement page).

### 3. Page Layout

Unified with Browse — sidebar filters on left, main content on right.

```
┌──────────────────────────────────────────────────────────────────┐
│  Performance                                          Synced 2h │
├──────────┬───────────────────────────────────────────────────────┤
│          │  [Sales]  [Marketing]              [3Mo][6Mo][9Mo][1Y]│
│ FILTERS  │                                                      │
│          │  ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐   │
│ Perf     │  │Total ││Strong││Moder.││ Low  ││ Cost ││Closed│   │
│ Strong   │  │ 135  ││  89  ││  34  ││  12  ││$284K ││$4.2M │   │
│ Moderate │  └──────┘└──────┘└──────┘└──────┘└──────┘└──────┘   │
│ Low      │                                                      │
│          │  [Search________________________]  135 items  [CSV]  │
│ ──────── │                                                      │
│ Metrics  │  Name            Score  Provs  Touch  T-ROI ...  Data│
│ Provs    │  ────────────────────────────────────────────────────│
│ Exper    │  AAP Workshop      76    612   $3.8M  6.2x  ...  S M│
│ Users    │  ▸ OCP4 Getting    48     78   $1.2M 15.4x  ...  S M│
│ Touch $  │  ┌──────────────────────────────────────────────┐    │
│ Closed $ │  │ Provisions: 78    Users: 45    Exper: 92    │    │
│ Cost $   │  │ Touched: $1.2M   Closed: $340K  Cost: $6.8K│    │
│          │  │ Cost/Prov: $87   Success: 92%               │    │
│ ──────── │  │ First: 2024-03   Last: 2026-07              │    │
│ Namespace│  │ [dev] [prod] [event]                         │    │
│ ☐ agd-v2 │  │                                              │    │
│ ☐ ansible│  │ ┌─ M Marketing Data ──────────── Score: 72 ┐│    │
│ ☐ azure  │  │ │ IL Provs: 400  Users: 320  Compls: 180  ││    │
│ ☐ cluster│  │ │ Page Views: 2,140                        ││    │
│ ...      │  │ └──────────────────────────────────────────┘│    │
│          │  │                                              │    │
│ ──────── │  │ Retirement Workflow: No action  [Mute][Review]│   │
│ Ret.     │  └──────────────────────────────────────────────┘    │
│ Status   │  Adv OCP Troubl.    18      23   $180K  7.8x  ...  S│
│ (Curator)│  RHEL 9 Migration   12       8    $45K  5.6x  ...  S│
│          │                                                      │
└──────────┴───────────────────────────────────────────────────────┘
```

### 4. Scoring Model — Inverted

**Higher score = better performance.** This is the fundamental change from retirement scoring.

| Level | Range | Color | Meaning |
|-------|-------|-------|---------|
| Strong | >= 55 | Green | Top performers |
| Moderate | 35-54 | Amber | Average performance |
| Low | < 35 | Red | Underperforming, may need attention |

#### Sales Scoring Formula (Inverted)

Same 4 factors, same weights, inverted direction. Items with high usage, pipeline, and sales score high. Items with zero activity score low.

| Factor | Max | Method | Direction Change |
|--------|-----|--------|-----------------|
| Usage (provisions) | 25 | Percentile buckets | High provisions → high points (was: high provisions → low points) |
| Pipeline (touched) | 15 | Percentile buckets | High touched → high points |
| Closed Sales | 25 | Percentile buckets | High closed → high points |
| Cost Efficiency (ROI) | 15 | Continuous percentile | Low cost/provision → high points |
| Age discount | n/a | Removed | New items are not penalized — performance speaks for itself |

Zero-value items (no provisions, no pipeline, no sales) receive **minimum** points for that factor (was: maximum). An item with zero everything scores ~0 (was: ~80).

The `score_breakdown` dict stores per-factor points, levels, and reasons with actual values and percentile context — same structure as today, just inverted language ("strong usage" instead of "low usage suggests retirement").

#### Marketing Scoring Formula

**Backlogged** — no marketing data exists yet. When marketing channel data arrives, a scoring formula will be defined based on available metrics (provisions, page views, completions, unique users). The `performance_scores.channel_scores` JSONB column already supports per-channel scores. The formula will be a separate design ticket.

#### Per-Channel Scores

Each channel has its own score, stored in `performance_scores.channel_scores`:

```json
{
  "rhdp": {"score": 48, "breakdown": {...}},
  "interactive_labs": {"score": 72, "breakdown": {...}}
}
```

The `performance_score` column in the database holds the default (sales) score. The API's `channel` query parameter controls which channel's score is returned in the response — `sales` returns `performance_score`, other channels return the corresponding value from `channel_scores`.

#### Score Breakdown Popover

Click to open, click to close (not hover). Shows per-factor bars with points, percentile context, and plain-English explanations. Each channel's score badge has its own popover with channel-appropriate factors.

### 5. Channel Tabs

Two tabs above the stats cards: **Sales** (default, active) and **Marketing** (disabled until data exists).

No Combined tab. The metrics are fundamentally different between channels — Touched/Closed vs Page Views/Completions. Each tab shows channel-specific columns, stats cards, and scoring. Cross-channel visibility is provided by:

- The **Data column** (S/M tags) showing which channels have data per item
- The **marketing addendum** in expanded rows showing the other channel's metrics and score

When the Marketing tab becomes active (data exists), switching tabs changes:

- Table columns (IL Provs, Users, Views, Completions instead of Provs, Touched, Closed, Cost)
- Stats cards (Total Page Views, Users, Completions instead of Total Cost, Closed, Touched)
- Score values (marketing formula scores)
- Sidebar metric filters (adapt to marketing-relevant ranges)
- Expanded row shows a **Sales addendum** instead of Marketing addendum

#### Time Window

Stays at top right: 3 Mo, 6 Mo, 9 Mo, 1 Yr toggle buttons. Same behavior as today — selects the windowed metrics slice. Applies regardless of channel tab.

### 6. Sidebar Filters

All filters in the left sidebar, consistent with Browse. The sidebar scrolls independently.

| Filter Group | Type | Notes |
|-------------|------|-------|
| **Performance** | Pill buttons: All / Strong / Moderate / Low | With item counts |
| **Metrics** | Min/Max range inputs | Provisions, Experiences, Unique Users, Touched ($), Closed ($), Cost ($) |
| **Namespace** | Checkbox list with counts | Scrollable with right padding for scrollbar. Multi-select. |
| **Retirement Status** | Pill buttons: All / No Action / In Process / Muted | Curator-only. Hidden for regular users. |

Future filter groups (Business Unit, Platform, Labels) are added as new sidebar sections with the same patterns — pills for categorical, checkboxes for multi-select, ranges for numeric.

Sidebar metric filters adapt when the Marketing tab is active — Touched/Closed ranges are replaced with Page Views/Completions ranges.

### 7. Collapsed Row (Sales Tab)

Same columns as today's retirement table:

| Column | Description |
|--------|-------------|
| Name | Display name + ci_name |
| Score | Performance score badge (color-coded, clickable for popover) |
| Provs | Provision count |
| Touched | Pipeline touched amount |
| T-ROI | Touched / Cost ratio |
| Closed | Closed sales amount |
| C-ROI | Closed / Cost ratio |
| Cost | Total cost |
| Data | S/M letter tags showing channel data availability |

Sortable by any numeric column (click header to toggle sort direction).

### 8. Expanded Row

Clicking a row expands it inline (same as today). The expanded area contains:

1. **Metrics grid** — same as today: provisions, unique users, experiences, touched, closed, cost, cost/prov, success rate, first/last provision. Responsive grid layout.

2. **Environment tags** — clickable links to Browse filtered by that environment name.

3. **Marketing addendum** (conditional) — only shown if the item has marketing channel data. Contains:
   - Header with M tag, "Marketing Data" title, source label (e.g. "Interactive Labs"), and marketing score badge (clickable for marketing-specific score breakdown popover)
   - Metrics: IL Provisions, Unique Users, Completions, Page Views
   - Collapsible (click header to expand/collapse)

4. **Retirement Workflow** — bottom bar. Curator-only controls. Same stepper as today (Review → Notify → Start → Retired). Clicking "Start Review" opens the side drawer/tray with the full workflow interface.

When on the Marketing tab, the layout mirrors but inverts — marketing metrics in the main grid, sales addendum as the conditional section.

### 9. Retirement Workflow

Unchanged from current behavior:

- Same stepper: Review → Owner Notified → Start Retirement → Retired
- Same side drawer with usage data, stepper steps, approval snapshot, curator notes
- Approval snapshot captures metrics from **both channels** at the time of approval
- Jira integration unchanged
- Mute (30-day ignore) unchanged

The only change is that the approval snapshot now stores channel-keyed data:

```json
{
  "sales": {"score": 48, "provisions": 78, "touched": 1200000, ...},
  "marketing": {"score": 72, "provisions": 400, "page_views": 2140, ...},
  "snapshot_at": "2026-08-04T12:00:00Z"
}
```

### 10. URL State Management

Full `useSearchParams` bidirectional sync, matching Browse's pattern:

| Param | Type | Default | Example |
|-------|------|---------|---------|
| `search` | string | empty | `?search=openshift` |
| `channel` | string | `sales` | `?channel=marketing` |
| `window` | string | `6m` | `?window=1y` |
| `performance` | string | `all` | `?performance=low` |
| `status` | string | `all` | `?status=muted` |
| `namespace` | string (comma-sep) | empty | `?namespace=agd-v2,gpte` |
| `provs_min` / `provs_max` | number | empty | `?provs_min=10` |
| `touched_min` / `touched_max` | number | empty | `?touched_min=100000` |
| `closed_min` / `closed_max` | number | empty | `?closed_min=50000` |
| `cost_min` / `cost_max` | number | empty | |
| `users_min` / `users_max` | number | empty | |
| `exper_min` / `exper_max` | number | empty | |
| `sort` | string | `score` | `?sort=provisions` |
| `order` | string | `desc` | `?order=asc` |

All filter changes update the URL via `setSearchParams({ replace: true })`. Page loads initialize state from URL params.

### 11. Advisor Integration

`PerformanceTableBlock` changes:

| Current | New |
|---------|-----|
| Links to `/analysis/retirement?search=...` | Links to `/analysis/performance?search=...` |
| `retirement_flavored` flag | `performance_flavored` flag (or remove flag, always show performance styling) |
| Score colors: high=red, low=green | Score colors: high=green, low=red (inverted) |

The deep-link now works because the Performance page reads `useSearchParams` and initializes the search filter from `?search=`.

### 12. API Changes

| Current Endpoint | New Endpoint | Change |
|-----------------|-------------|--------|
| `GET /analysis/retirement` | `GET /analysis/performance` | Same query params + `channel` param. Returns performance-scored data. |
| `GET /analysis/retirement/workflow/{baseName}` | `GET /analysis/performance/workflow/{baseName}` | Unchanged behavior |
| `PUT .../review`, `approve`, `notify`, `start` | Same under `/analysis/performance/...` | Unchanged behavior |
| `PUT /analysis/retirement/ignore/{baseName}` | `PUT /analysis/performance/ignore/{baseName}` | Unchanged behavior |
| `DELETE /analysis/retirement/ignore/{baseName}` | `DELETE /analysis/performance/ignore/{baseName}` | Unchanged behavior |

The response shape adds `channel_scores` and the inverted scoring. The `channel` query parameter (default `sales`) controls which channel's scores and metrics are returned.

Backward compatibility: the old `/analysis/retirement` endpoints redirect to `/analysis/performance` equivalents for any external callers (CLI, scripts).

### 13. Frontend File Changes

| Current | Action |
|---------|--------|
| `RetirementPage.tsx` (1632 lines) | Rewrite as `PerformancePage.tsx` with Browse-style layout, sidebar filters, URL state |
| `ContentAnalysisPage.tsx` | Unchanged (overlap only) |
| `RcarsSidebar.tsx` | Rename "Retirement" → "Performance", update route, adjust access gate |
| `PerformanceTableBlock.tsx` | Update link target and score colors |
| `api.ts` | Rename retirement API methods, update endpoint paths, add `channel` param |

The rewrite extracts shared patterns from Browse where practical (drawer shell, filter sidebar layout) but does not create a shared component library — that's premature until a third page needs the same pattern.

### 14. Scope

**In scope:**
- Performance page with Browse-style layout (sidebar filters, expandable rows, drawer)
- Sales channel with inverted scoring formula
- All existing filters moved to sidebar + namespace checkbox list
- Marketing tab (disabled/greyed out, no data)
- Marketing addendum in expanded rows (structural support, renders when data exists)
- Per-channel score badges and popovers (click to open/close)
- URL state management with deep-link support
- Advisor deep-link update
- API endpoint rename and `channel` parameter
- Approval snapshot captures both channels

**Out of scope:**
- Marketing scoring formula (no data — backlog when data arrives)
- Combined view tab (add later if needed)
- Without Prod page (RHDPCD-661)
- Shared component extraction between Browse and Performance (premature)
- Score threshold tuning (keep 55/35 for now, adjust with real data)
