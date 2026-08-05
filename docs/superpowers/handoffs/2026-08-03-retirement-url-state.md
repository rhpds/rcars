# Handoff: Retirement Page URL State Sync

**Date:** 2026-08-03
**Branch:** not started (create from `main` after `feature/advisor-chat` merges)
**Jira:** needs ticket (child of RHDPCD-25)
**Status:** Design only. Two options documented below.

## Problem

RetirementPage uses plain `useState` for all filter/search state. Refresh loses everything, URLs aren't shareable, browser back/forward doesn't work. BrowsePage already solved this with `useSearchParams` from react-router-dom.

## BrowsePage Pattern (reference)

```
src/frontend/src/pages/BrowsePage.tsx
```

1. Initialize state from `searchParams.get()` with fallback defaults
2. `useEffect` syncs state → URL params via `setSearchParams(params, { replace: true })`
3. Only non-default values are written to the URL (clean URLs when no filters active)
4. Page resets to 1 on filter change

## RetirementPage Filter State to Sync

```
src/frontend/src/pages/RetirementPage.tsx:285-321
```

| State | Type | Default | URL param name |
|-------|------|---------|---------------|
| `tab` | `'prod' \| 'no_prod'` | `'prod'` | `tab` |
| `search` | string | `''` | `search` |
| `window` | `'1q' \| '2q' \| '3q' \| '1y'` | `'1y'` | `window` |
| `sortBy` | SortField | `'retirement_score'` | `sort` |
| `sortDir` | `'asc' \| 'desc'` | `'asc'` | `dir` |
| `scoreFilter` | ScoreFilter | `'all'` | `score` |
| `ageFilter` | AgeFilter | `'all'` | `age` |
| `workflowFilter` | WorkflowFilter | `'all'` | `workflow` |
| `selectedNamespaces` | `Set<string>` | empty | `ns` (comma-separated) |
| `appliedRanges` | RangeFilters | all empty | `prov_min`, `prov_max`, etc. |

Ephemeral state that should NOT be synced: `expanded`, `drawerItem`, `drawerWorkflow`, `approvalReason`, `replacementCi`, `notesText`, `emailTemplate`, `scorePopover`, action loading/error states.

## Option 1: Full URL Sync (recommended)

Sync all filter state from the table above to URL params. Copy the BrowsePage pattern exactly.

### Changes

**RetirementPage.tsx only** (frontend-only, no backend changes):

1. Add `useSearchParams` import, replace `useState` for each filter with `searchParams.get()` initialization
2. Add a URL sync `useEffect` that writes non-default values to params
3. The existing tab-change `useEffect` (line 374) that resets filters should also clear URL params
4. Range filters: serialize as individual params (`prov_min=100&cost_max=500`), only non-empty values

### Effort

~100 lines changed in one file. Mechanical — the pattern is proven.

### Tradeoffs

- (+) Full shareability — "look at this filtered view" links work
- (+) Browser back/forward works across filter changes
- (+) Refresh preserves exact state
- (-) URL gets long with range filters active (cosmetic only)

## Option 3: Search + Tab Only (minimal)

Sync only `search` and `tab` to URL params. Everything else stays ephemeral.

### Changes

**RetirementPage.tsx only**:

1. Add `useSearchParams`, initialize `search` and `tab` from params
2. Small sync `useEffect` for just those two values
3. Tab-change reset clears `search` param

### Effort

~20 lines changed.

### Tradeoffs

- (+) Smallest diff, lowest risk
- (+) Covers the main annoyance (losing search on refresh)
- (-) Other filters (score, window, namespace, sort, ranges) still lost on refresh
- (-) Inconsistent UX — "why does search survive but my sort doesn't?"

## Recommendation

Option 1. The diff is small and mechanical, and partial URL state (Option 3) creates confusion about which filters are "sticky." The BrowsePage pattern is battle-tested.

## Related: History Page Bug

Multi-turn chat sessions display as separate 1-turn entries on the History page. The sessions should show all turns, but only the last turn is rendering. This is a separate bug — not related to retirement URL state — but was observed during the same testing session. Likely in `HistoryPage.tsx` session grouping or the `/advisor/sessions` API response.

## Key Files

- `src/frontend/src/pages/RetirementPage.tsx` — the only file that needs changes
- `src/frontend/src/pages/BrowsePage.tsx:361-474` — reference implementation to copy from
