# RCARS PatternFly 6 Migration — Design Spec

**Jira:** [RHDPCD-98](https://redhat.atlassian.net/browse/RHDPCD-98)
**Date:** 2026-06-29
**Mockups:** `/tmp/rcars-pf6-design-mockup.html`, `/tmp/rcars-browse-card-mockup.html`, `/tmp/rcars-reccard-mockup.html`

## Overview

Migrate the RCARS frontend from its custom LCARS theme to PatternFly 6, adding light/dark mode toggle while preserving the RCARS visual identity. Clean-break migration on a feature branch — no progressive LCARS/PF6 coexistence.

## Migration Strategy

**Clean break on a feature branch.** The entire frontend (~4k lines, 24 files) is rebuilt on PF6 in one branch. The LCARS CSS file (`lcars.css`, 1,060 lines) and all `components/lcars/` wrappers are replaced entirely. One PR to review and merge.

**No backend changes.** This is a frontend-only migration. API contracts, SSE streaming, and auth are unchanged.

## Theme Architecture

### CSS Structure

```
src/frontend/src/styles/
  rcars-variables.css       # Shared tokens: amber palette, spacing, radii, transitions, pill colors
  rcars-dark-overrides.css  # Dark: backgrounds, surfaces, scoring colors, shadows
  rcars-light-overrides.css # Light: warm parchment, white cards, contrast-boosted scoring
```

PF6's `.pf-v6-theme-dark` class on `<html>` controls the base theme. RCARS overrides layer on top via CSS custom properties scoped to `[data-theme="dark"]` and `[data-theme="light"]`.

### Theme Toggle

React `ThemeContext` with `useTheme` hook:
- Toggles `data-theme` attribute on `<html>`
- Persists choice to `localStorage`
- Respects `prefers-color-scheme` on first visit (no stored preference)
- Default: dark mode
- Toggle control: sun/moon icon button in the masthead

### Typography

- **Red Hat Display** — headings, labels, RCARS wordmark, score numbers. Weight 600-900.
- **Red Hat Text** — body copy, navigation, form elements, buttons.
- **Red Hat Mono** — scores, CI names, durations, tabular data.

All three are PF6's native fonts. No additional font loading required.

### Color System

#### Dark Mode (default — preserves current RCARS palette)

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `#0f1117` | Page background |
| `--bg-sidebar` | `#0a0d12` | Sidebar, masthead |
| `--bg-card` | `#1a1f2e` | Card backgrounds |
| `--text-primary` | `#e8e8ea` | Primary text |
| `--text-link` | `#73bcf7` | Links, active nav |
| `--rcars-amber` | `#FF9900` | Logo, brand accent |
| `--score-green` | `#5cb85c` | Best-fit tier |
| `--score-amber` | `#e8a838` | Review tier |
| `--score-red` | `#e04848` | Retirement/danger |

#### Light Mode

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `#f4f1ec` | Warm parchment (not cold white) |
| `--bg-card` | `#ffffff` | Cards |
| `--text-primary` | `#1a1a1a` | Primary text |
| `--text-muted` | `#6a6a6a` | Muted text (darkened for contrast) |
| `--text-link` | `#0066cc` | Links |
| `--rcars-amber` | `#c77c00` | Logo (darkened for light bg) |
| `--score-green` | `#2e7d32` | Best-fit tier |
| `--score-amber` | `#b8860b` | Review tier |
| `--score-red` | `#c62828` | Retirement/danger |

#### Pill Color System (consistent across all pages)

| Color | Usage |
|-------|-------|
| Purple | Products |
| Blue | Topics |
| Green | Workloads |
| Amber | Module-level topics |
| Soft red | Curator tags |
| Gray | Neutral/system |

## Masthead

- **RCARS LCARS-style SVG logo preserved** — arc, header bars (amber/cream/purple), bottom bars (purple/amber/cream), "RCARS" wordmark, "RHDP CONTENT ADVISOR" subtitle
- SVG uses CSS custom properties for fills — adapts automatically per theme (vivid in dark, muted in light)
- **Status indicators** moved from inside the SVG to HTML text alongside the logo — "CATALOG · 2h ago" and "ANALYSIS · 1h ago" with green/red status dots
- **Theme toggle** — sun/moon icon button, right side of masthead
- **User avatar** — initials badge, right side of masthead
- PF6 `Masthead` + `MastheadMain` + `MastheadContent` components

## Navigation Restructure

Flattened nav with role-gated sections. PF6 `Nav` with `NavGroup` for section labels, `NavItem` for entries, `NavExpandable` for History.

```
── Top (everyone) ──
Advisor
  History (collapsible, indented)      ← past sessions, collapsed by default
Browse
  Catalog                              ← everyone; curators see extra filters + edit drawer
  Workloads                            ← curators only; workload mapping table (moved from Admin)

── Analysis (admin) ──
Overlap
Retirement

── System (admin) ──
Status                                 ← stat cards dashboard (read-only)
Sync & Analysis                        ← catalog refresh, scan, rescan-all, workload repo scan
Recent Jobs                            ← promoted from embedded tab to top-level
Token Usage
Query History
```

**Key changes from current:**
- "Content Analysis" parent removed — Overlap and Retirement are top-level
- "Admin" parent removed — all System items are top-level
- Workload mappings move from System to Browse (curator-gated)
- Recent Jobs promoted to its own System page
- Clicking "Advisor" starts a new session (no separate "+ New Session" button)
- "History" is a collapsible toggle indented under Advisor

## Page Designs

### Advisor Page

**Layout:** Same two-pane structure (chat left, recommendations right). No structural change.

**Query settings:** Collapsible settings panel triggered by a gear/sliders icon near the chat input. Contains dev/event stage toggles and future filter switches. Collapsed by default.

**RecCard design (preserved):**
- Same layout: score left, title+meta center, duration right, expand caret far right
- Same two-column label/value rows (Why it fits, Objectives, How to use)
- Same tier-tinted backgrounds with border-left accent
- Same collapsible tier sections (Best fit → Other options → Also reviewed)
- Same caveat styling (amber warning text with truncate/expand)
- Same usage metrics row with deployments count

**RecCard refinements:**
- Red Hat Display/Text/Mono typography
- Subtle card shadow + hover lift (translateY -1px)
- Body separator line between header and expanded content
- "Best fit?" moved inline as a badge in the usage metrics row (next to sales impact badge). Format: `★ Best fit?` badge, same visual treatment as `$ High Sales Impact` badge
- **New link:** "View in RCARS" in footer alongside "View in RHDP Catalog". Links to `/browse?search={ci_name}` for full analysis detail.

### Browse Page

**Toolbar:** Single PF6 `Toolbar` replaces three stacked panels. Contains:
- Search input
- Stage toggles (dev, event)
- Filter dropdowns (cloud provider, workloads, config)
- Active filter chips (removable PF6 `Chip` components)
- Item count
- Curator filters (unanalyzed/failures/stale/retired) as additional chips when `isCurator`

**Item list:** PF6 expandable rows. Collapsed rows show: name + badges, CI name, category.

**Expanded card — consistent section order:**

1. **Description** (always visible) — type/difficulty/duration line, then analysis summary
2. **Learning Objectives** (always visible) — first 5 shown, "Show N more..." to expand
3. **Content Analysis** (always visible) — Products (purple pills) + Topics (blue pills)
4. **Modules** (collapsible, collapsed default) — module titles with amber topic pills
5. **Infrastructure** (collapsible, collapsed default) — config, workers, mapped workloads (green pills), access groups
6. **Similar Content** (collapsible, collapsed default) — similarity scores with color-coded percentages
7. **Curator Tags** (always visible) — soft red pills, labeled "Curator Tags" to distinguish from LLM-generated analysis. Read-only in card.
8. **Links** — RHDP Catalog + Showroom Repo

**Interaction details:**
- **Expand/collapse only on title click** — clicking the item title (display name) toggles the expansion. Clicking anywhere else inside the expanded card body does NOT collapse it. Users need to select and copy text (descriptions, objectives, CI names) without accidentally closing the card.
- **Sticky column headers** — all scrollable tables (Browse list, Overlap, Retirement, Similar Content) use `position: sticky; top: 0` on `<thead>` so column headers remain visible when scrolling.

**Curator editing:** PF6 `Drawer` slides in from the right when curator clicks "Edit". Contains: tags (add/remove), notes, curated duration, URL override, content path, flag for review, re-analyze.

### Browse Workloads Page (new)

Workload mapping table moved from Admin. Curator-gated. PF6 `Table` showing FQCN → product name mappings with add/edit/delete controls.

### System — Status Page

Read-only dashboard. PF6 `Card` stat cards in a grid:
- Catalog (total, by stage, with showroom, unique, last sync)
- Analysis (analyzed, unanalyzed, stale, failures, last run)
- Infrastructure (AgD v2 items, workload counts, unmapped)
- LLM Provider (LiteMaaS/Vertex status, model assignments)
- Reporting Sync (status, asset counts, last synced)

### System — Sync & Analysis Page

Operational actions with log output:
- Catalog Sync (refresh from Babylon)
- Scan Monitor (progress tracking)
- Rescan All
- Workload Repo Scan
- Each action uses `AdminAction` pattern: button + collapsible `LogWindow`

### System — Recent Jobs Page (new)

Promoted from embedded section in Sync tab. PF6 `Table` showing recent job history with status, type, duration.

### System — Token Usage Page

PF6 restyling only. No structural changes.

### System — Query History Page

PF6 restyling only. No structural changes.

### Analysis — Overlap Page

PF6 restyling only (Table, filters). No structural changes. Future improvements deferred.

### Analysis — Retirement Page

PF6 restyling only (Table, stat cards). No structural changes. Future improvements deferred.

## Component Mapping

| Current | PF6 Replacement |
|---------|----------------|
| `LcarsHeader` | `Masthead` + `MastheadMain` + `MastheadContent` |
| `LcarsSidebar` | `PageSidebar` + `Nav` + `NavGroup` + `NavItem` + `NavExpandable` |
| `LcarsButton` | `Button` (variant mapping: primary, secondary, link) |
| `LcarsCard` | `Card` + `CardHeader` + `CardBody` + `CardExpandableContent` |
| `LcarsInput` | `TextInput` / `TextArea` |
| `LcarsBadge` | `Label` (custom color variants for scoring) |
| `Pagination` | PF6 `Pagination` |
| `WorkloadMultiSelect` | PF6 `Select` (typeaheadMulti) |
| `LogWindow` | `CodeBlock` (read-only) |
| `ProgressStream` | Custom (SSE streaming unchanged) |
| Custom tables | PF6 composable `Table` |
| Filter panels | `Toolbar` + `ToolbarFilter` + `SearchInput` + `Chip` |
| Toggle switch | PF6 `Switch` |
| Curator editing | PF6 `Drawer` (slide-out panel) |
| Admin tabs | Separate pages (nav restructure eliminates tabs) |

## File Structure Changes

### New files
- `src/frontend/src/styles/rcars-variables.css`
- `src/frontend/src/styles/rcars-dark-overrides.css`
- `src/frontend/src/styles/rcars-light-overrides.css`
- `src/frontend/src/hooks/useTheme.ts`
- `src/frontend/src/pages/WorkloadsPage.tsx`
- `src/frontend/src/pages/StatusPage.tsx`
- `src/frontend/src/pages/SyncPage.tsx`
- `src/frontend/src/pages/RecentJobsPage.tsx`

### Deleted files
- `src/frontend/src/styles/lcars.css`
- `src/frontend/src/components/lcars/LcarsHeader.tsx`
- `src/frontend/src/components/lcars/LcarsSidebar.tsx`
- `src/frontend/src/components/lcars/LcarsCard.tsx`
- `src/frontend/src/components/lcars/LcarsButton.tsx`
- `src/frontend/src/components/lcars/LcarsInput.tsx`
- `src/frontend/src/components/lcars/LcarsBadge.tsx`
- `src/frontend/src/components/lcars/index.ts`

### Modified files
- `src/frontend/package.json` — add `@patternfly/react-core`, `@patternfly/react-icons`, `@patternfly/react-table`
- `src/frontend/src/App.tsx` — new shell with PF6 `Page`, `ThemeProvider`, updated routing
- `src/frontend/src/pages/AdvisorPage.tsx` — PF6 components, collapsible settings, RecCard link addition
- `src/frontend/src/pages/BrowsePage.tsx` — full restructure (toolbar, card layout, drawer)
- `src/frontend/src/pages/AdminPage.tsx` — split into StatusPage, SyncPage, RecentJobsPage
- `src/frontend/src/pages/ContentAnalysisPage.tsx` — PF6 Table restyling
- `src/frontend/src/pages/RetirementPage.tsx` — PF6 Table/Card restyling
- `src/frontend/src/components/advisor/RecCard.tsx` — PF6 Card, "View in RCARS" link, inline best-fit badge

## Out of Scope

- Backend API changes
- Feature additions beyond theme toggle and nav restructure
- SSE streaming logic changes
- Retirement/Overlap page structural changes (deferred)
- Mobile-first responsive design (PF6 breakpoints provide basic responsiveness)
