# Browse Page Redesign — Design Spec

**Date:** 2026-06-15
**Status:** Design
**Scope:** Browse page filter system, pagination, server-side data architecture

## Problem

The Browse page filter bar is a flat horizontal row mixing text search, a content-state dropdown, and stage toggles. Adding infrastructure filter dropdowns (cloud provider, workloads, AgnosticD config) would make it a cluttered, wrapping mess. The content-state filters (unanalyzed, scan failures, stale) are admin/curator concerns that shouldn't be shown to regular users. Pagination is prev/next only with no way to jump to a specific page, making navigation painful across ~1000 items. The page loads all items client-side and filters in-browser, but infrastructure filters require server-side queries — maintaining two code paths is worse than switching entirely to server-side.

## Design

### Filter Layout

Two-tier layout replacing the current flat filter bar:

**Primary bar** (always visible):
- Text search input (searches by display name and CI name)
- Stage toggles: `dev` and `event` as pill toggles (same LcarsToggle component)
- Result count (e.g. "989 items")

**Filter panel** (collapsible, below primary bar):
- Header: "Filters" label (clickable to expand/collapse) + "Clear all" link (visible when any filter is active)
- Three dropdowns in a responsive flex row:
  - **Cloud Provider** — single-select. Values from `/catalog/facets` `cloud_providers` array. Options: ec2, azure, gcp, openstack, etc. Default: "All providers"
  - **Workloads** — multi-select with checkboxes. Values from `/catalog/facets` `workloads` array (product names from curated mappings, not raw role names). AND semantics: selecting "OpenShift AI" + "Pipelines" returns only items that have both. Default: "Select workloads..."
  - **AgnosticD Config** — single-select. Values from `/catalog/facets` `configs` array. Options: ocp-cnv, ocp-workloads, cloud-vms-base, ocp-base, etc. Default: "All configs"
- Active filter chips below the dropdowns: green dismissable pills showing each active filter value with ✕ to remove

**Collapsed state:** When collapsed, the panel shrinks to a single line showing "Filters" label + active filter chips inline + "Clear all". Chips remain visible and dismissable without expanding. When no filters are active and panel is collapsed, it shows "Filters" + "no filters active" in muted text.

**Default state:** Panel starts collapsed on page load.

**Curator filter panel** (only visible to curators/admins, below the main filter panel):
- Amber/gold themed to distinguish from the blue infrastructure panel
- Header: "Curator Filters" label (collapsible)
- Content-state filter buttons as toggleable pills: Unanalyzed, Failures, Stale, Needs Review
- Only one curator filter active at a time (they are mutually exclusive states)
- These replace the current `<select>` dropdown that mixed content-state with content-type filters

**Removed from the filter bar:**
- The "All items" / "Has Showroom" / "Analyzed" content-filter `<select>` dropdown — split into curator-only filters (unanalyzed, failures, stale, needs review) and removed entirely for regular users. "Has Showroom", "Analyzed", and "Untagged" are dropped as standalone filters — they're not useful discovery filters.
- The `v2` toggle — no longer needed. Infrastructure filters implicitly scope to v2 items when active, and when no infra filters are set, all items (v1 and v2) show. The v2 badge on items remains.

### Server-Side Filtering and Pagination

**Current approach (being replaced):** Load all ~1000 items via `api.listCatalog({ limit: 1000 })`, filter and paginate client-side in React state.

**New approach:** Every filter change triggers a server request. The API returns one page of results at a time.

**API changes required:**

Extend `GET /catalog` to accept filter parameters:
- `search` (string) — case-insensitive text search on display_name and ci_name (ILIKE)
- `stage` (string, comma-separated) — e.g. "prod", "prod,event", "prod,dev,event". Default: "prod" (prod only, unless dev/event toggles are on). ZT items (zt-* namespaces) are always included — they are prod-stage items and don't need a separate toggle
- `cloud_provider` (string) — filter by cloud provider
- `workloads` (string, comma-separated) — filter by workload product names, AND semantics with alias resolution
- `agd_config` (string) — filter by AgnosticD config type
- `content_filter` (string) — curator-only: "unanalyzed", "scan_failures", "stale", "needs_review"
- `limit` (int) — page size, default 50
- `offset` (int) — pagination offset

The existing `GET /catalog/search/infrastructure` endpoint handles workload AND semantics and alias resolution. Rather than duplicating that logic, the main `GET /catalog` endpoint should incorporate the infrastructure filtering directly. The `/catalog/search/infrastructure` endpoint remains available for programmatic use (e.g. Publishing House API calls) but the Browse page uses the unified `/catalog` endpoint.

**Response shape** (unchanged, but with `total` reflecting filtered count):
```json
{
  "items": [...],
  "total": 23
}
```

**Facets loading:** On page mount, call `GET /catalog/facets` once to populate dropdown options. Cache in component state — facet values change rarely (only after catalog refresh).

**Debouncing:** Text search input debounced at 300ms to avoid excessive API calls while typing. Dropdown and toggle changes fire immediately.

### Pagination

Replace the current prev/next buttons with numbered page navigation:

**Layout:** Centered below the results list.
```
< 1 2 3 ... 18 19 20 >
```

**Behavior:**
- Always show first page, last page, and current page ± 1 neighbor
- Ellipsis (`...`) between non-contiguous ranges
- `<` and `>` arrows for prev/next, disabled at boundaries
- Current page highlighted (accent blue)
- 50 items per page (fixed, no selector)
- Page resets to 1 when any filter changes

**Examples:**
- Page 1 of 20: `[1] 2 3 ... 20 >`
- Page 10 of 20: `< 1 ... 9 [10] 11 ... 20 >`
- Page 20 of 20: `< 1 ... 18 19 [20]`
- Page 3 of 5: `< 1 2 [3] 4 5 >`
- Page 1 of 1: `[1]` (no arrows)

### Role-Based Visibility

| Element | Regular User | Curator | Admin |
|---------|-------------|---------|-------|
| Search input | ✓ | ✓ | ✓ |
| Stage toggles (dev/event) | ✓ | ✓ | ✓ |
| Filter panel (cloud/workloads/config) | ✓ | ✓ | ✓ |
| Curator filter panel | — | ✓ | ✓ |
| Per-item Re-analyze button | — | ✓ | ✓ |
| Per-item curator tools (tags, notes, URL override, content path, flag) | — | ✓ | ✓ |

### Workload Multi-Select Dropdown

The workload dropdown needs a custom component since native `<select>` doesn't support multi-select with checkboxes well. Design:

- Click the dropdown to open a scrollable checklist panel below it
- Each option is a checkbox + product name
- Selected items update the dropdown label: "Select workloads..." → "1 selected" → "2 selected" → etc.
- Clicking outside or pressing Escape closes the panel
- The dropdown border highlights (accent blue) when any workloads are selected
- Options sorted alphabetically by product name
- Panel max-height with scroll for long lists

### URL State

Active filters are reflected in the URL query string so filtered views can be linked and shared:
- `?search=openshift+ai`
- `?cloud_provider=ec2`
- `?workloads=OpenShift+AI,Pipelines`
- `?agd_config=ocp-cnv`
- `?stage=prod,dev`
- `?content_filter=scan_failures` (curator-only, from Admin page deep links)
- `?page=3`

On page load, read URL params and apply as initial filter state. This preserves the existing Admin page → Browse deep linking (e.g. clicking "9 failures" on Admin navigates to `/browse?content_filter=scan_failures`). The current `?filter=scan_failures` param is renamed to `?content_filter=scan_failures` for clarity.

### What Stays the Same

- Item card layout (display name, CI name, category, badges)
- Expanded item detail (analysis summary, modules, learning objectives, products, topics, infrastructure panel, curator tools)
- The v2 badge, ZT badge, FAILED badge, stage badges on items
- Curator tools inside expanded items (tags, notes, URL override, content path, flag, re-analyze)
- All existing API endpoints — this adds parameters to `GET /catalog`, doesn't change other endpoints

## Components Affected

**Frontend:**
- `BrowsePage.tsx` — major rewrite: remove client-side filtering, add server-side fetch with filter params, new filter panel component, new pagination component, role-based curator panel
- `api.ts` — update `listCatalog()` to accept filter params, no new methods needed (already has `getCatalogFacets()`)
- `lcars.css` — new styles for filter panel, filter chips, pagination, workload multi-select dropdown, curator filter panel

**Backend:**
- `routes/catalog.py` — extend `GET /catalog` with search, stage, cloud_provider, workloads, agd_config, content_filter query params
- `db/database.py` — new query method that builds filtered+paginated SQL with optional infrastructure joins. Workload filtering reuses the alias resolution and AND semantics from `search_by_infrastructure()`

## Migration Notes

- The `?filter=` URL param used by Admin deep links changes to `?content_filter=`. Update the Admin page `navigate()` calls in `AdminCatalogPage` (the clickable unanalyzed/stale/failure counts) and remove the `searchParams.get('filter')` reader in BrowsePage.
- The `showV2Only` toggle state and `contentFilter` select are removed from BrowsePage — replaced by the new filter system.
- No database schema changes.
- No new API endpoints — extends existing `GET /catalog`.
