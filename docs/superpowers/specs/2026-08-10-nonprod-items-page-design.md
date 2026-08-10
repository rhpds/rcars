# Non-Prod Items Page

**Date:** 2026-08-10
**Jira:** [RHDPCD-661](https://redhat.atlassian.net/browse/RHDPCD-661)
**Branch:** `feature/dev-items-page`

## Purpose

Provide visibility into catalog items that have no production stage variant. Today, filtering dev-only items from the Performance page (to remove noise) creates a blind spot — curators lose sight of items that exist only in dev/test/event stages. This page surfaces those items with usage metrics and supports retirement workflow actions.

Designed to serve multiple content types: Babylon items today, portfolio architectures and future content types later.

## Schema

One new table. No scoring, no cost, no channels.

```sql
CREATE TABLE IF NOT EXISTS nonprod_usage (
    content_id        TEXT PRIMARY KEY REFERENCES content_entities(content_id),
    catalog_base_name TEXT NOT NULL,
    provisions        INTEGER DEFAULT 0,
    requests          INTEGER DEFAULT 0,
    completions       INTEGER DEFAULT 0,
    unique_users      INTEGER DEFAULT 0,
    success_ratio     REAL DEFAULT 0,
    failure_ratio     REAL DEFAULT 0,
    first_provision   TEXT,
    last_provision    TEXT,
    windowed_metrics  JSONB DEFAULT '{}',
    ignored_until     DATE,
    synced_at         TIMESTAMPTZ DEFAULT NOW()
);
```

Display name, content type, namespace, and stages come from JOINs to `content_entities` / `babylon_items` at query time — no duplication. Retirement workflow reuses the existing `retirement_workflow` table keyed on `content_id`.

## Sync

### Identifying non-prod items

New DB method `get_nonprod_base_names()` queries `babylon_items` JOIN `content_entities` for base names where no active (non-retired) variant has `stage = 'prod'`. Returns `dict[str, str]` mapping `base_name → content_id`.

### MCP queries

Two windows (6m, 12m). One provisions query per window — same SQL shape as `_build_provisions_sql()` but **without `PROVISION_FILTERS`** (no environment or user_group restriction). Raw usage numbers for all environments.

Total: 2 additional MCP calls, appended to the existing `run_reporting_sync()`.

### Upsert flow

1. Call `get_nonprod_base_names()` to get the target set
2. Query MCP for 6m and 12m provisions (unfiltered)
3. Build `windowed_metrics` JSONB with both windows
4. Upsert into `nonprod_usage` — items with no MCP data get zero-backfilled
5. Orphan cleanup: remove rows whose `content_id` no longer exists in `content_entities` or whose item gained a prod stage since last sync

### Concurrency with performance sync

The `require_prod_stage=True` change to `get_catalog_base_names()` (already on this branch) ensures performance backfill excludes dev-only items. The nonprod sync picks up exactly the complement. No overlap.

## API

All endpoints under `/analysis/nonprod`, in `routes/analysis.py`.

### `GET /analysis/nonprod` — `require_curator`

Query parameters:

| Param | Default | Options |
|-------|---------|---------|
| `sort_by` | `provisions` | `provisions`, `unique_users`, `success_ratio`, `failure_ratio`, `display_name` |
| `sort_dir` | `desc` | `asc`, `desc` |
| `content_type` | — | Filter by content type |
| `stage` | — | Filter items whose stages contain this value |
| `namespace` | — | Filter by babylon_items namespace |
| `search` | — | Free text on display name / base name |
| `window` | `12m` | `6m`, `12m` |
| `status` | — | `muted`, `active` |

Returns list of items with:
- Metrics from `nonprod_usage` (overlaid from `windowed_metrics` based on selected window)
- `display_name`, `content_type`, `stages`, `namespace` from JOINs
- `retirement_workflow` status via LEFT JOIN

### `PUT /analysis/nonprod/ignore/{base_name}` — `require_curator`

Sets `ignored_until = NOW() + 30 days` on the `nonprod_usage` row. Same behavior as Performance mute.

### `DELETE /analysis/nonprod/ignore/{base_name}` — `require_curator`

Clears `ignored_until`. Same behavior as Performance unmute.

### Retirement workflow

No new endpoints. The existing `/analysis/performance/workflow/{base_name}/*` endpoints operate on `content_id` — they work for any item regardless of which metrics table it lives in. The Non-Prod Items page calls the same endpoints.

## Frontend

### Page: `NonProdItemsPage.tsx`

Same layout pattern as `PerformancePage.tsx`: left sidebar filters + main content area with sortable table.

### Sidebar filters

| Filter group | Type | Values |
|-------------|------|--------|
| Stage | Multi-select checkboxes | dev, event, test (populated from data) |
| Content Type | Multi-select checkboxes | babylon, portfolio_architecture, etc. (populated from data) |
| Namespace | Multi-select checkboxes | Populated from data |
| Provisions | Radio buttons | 0, 1-10, 10+ |
| Status | Radio buttons | All, Active, Muted |

Free-text search bar above filters.

### Table columns

| Column | Sortable | Notes |
|--------|----------|-------|
| Display Name | Yes | Links to Browse detail if available |
| Content Type | No | Badge |
| Stages | No | Chip badges (dev, event, test) |
| Namespace | No | |
| Provisions | Yes | |
| Unique Users | Yes | |
| Success Ratio | Yes | Percentage |
| Failure Ratio | Yes | Percentage |
| Last Provision | No | Date |
| Status | No | Retirement workflow badge + Muted badge |

### Window toggle

6m / 12m pill selector at top of page. Switches the overlaid metrics from `windowed_metrics`.

### Actions

- **Mute 30d** button — visible to curators, calls ignore endpoint
- **Start Retirement** button — opens existing `WorkflowDrawer` component
- Muted items excluded from default view; visible via Status → Muted filter

### Navigation

"Non-Prod Items" entry under Analysis section in `RcarsSidebar.tsx`, gated on `auth.isCurator`.

Route: `/analysis/nonprod` in `App.tsx`, gated on `auth.isCurator`.

## Files to modify

| File | Change |
|------|--------|
| `src/api/rcars/db/database.py` | Add `nonprod_usage` to `SCHEMA_SQL`, add `get_nonprod_base_names()`, `list_nonprod_items()`, `upsert_nonprod_usage()`, `set_nonprod_ignored()`, `clear_nonprod_ignored()`, orphan cleanup |
| `src/api/rcars/services/reporting_sync.py` | Add `_sync_nonprod_usage()`, call from `run_reporting_sync()` |
| `src/api/rcars/api/routes/analysis.py` | Add `GET /analysis/nonprod`, `PUT/DELETE /analysis/nonprod/ignore/{base_name}` |
| `src/frontend/src/pages/NonProdItemsPage.tsx` | New page component |
| `src/frontend/src/components/RcarsSidebar.tsx` | Add nav entry under Analysis |
| `src/frontend/src/App.tsx` | Add route |
| `src/frontend/src/services/api.ts` | Add API client methods |

## Not included

- Scoring — no cost data means no ROI factor; scoring dev items the same way as prod doesn't make sense
- Cost columns — explicitly excluded per requirements
- Channel tabs (S/M) — not relevant for non-prod
- Score breakdown popovers — no scoring
- Windowed metrics beyond 6m/12m — 2 windows sufficient for visibility
