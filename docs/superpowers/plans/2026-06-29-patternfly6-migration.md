# PatternFly 6 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate RCARS frontend from custom LCARS theme to PatternFly 6 with light/dark mode toggle, preserving the RCARS visual identity and RecCard design.

**Architecture:** Clean-break migration on a feature branch. PF6 provides the component library and base theme; RCARS CSS custom properties layer on top for branded dark/light modes. The LCARS-style SVG logo is preserved with theme-adaptive fills. Navigation is restructured from nested parents to flattened role-gated sections. AdminPage is split into focused pages.

**Tech Stack:** React 19, Vite 8, TypeScript 5.7, PatternFly 6 (`@patternfly/react-core`, `@patternfly/react-icons`, `@patternfly/react-table`), React Router 7.

## Global Constraints

- **Frontend only** — no backend/API changes. All existing API contracts, SSE streaming, auth unchanged.
- **No new dependencies** beyond the three PF6 packages.
- **Jira key:** `[RHDPCD-98]` in all commit messages.
- **Branch:** `feature/pf6-migration` off `main`.
- **Typography:** Red Hat Display (headings), Red Hat Text (body), Red Hat Mono (tabular). All ship with PF6 — no extra font loading.
- **Scoring colors must remain distinct** in both themes. Green/amber/red for tiers; purple/blue/green/amber/soft-red for pills.
- **Expand/collapse only on title click** — clicking inside expanded card bodies must NOT collapse them.
- **Sticky table headers** — all scrollable tables use `position: sticky; top: 0` on `<thead>`.

---

### Task 1: Feature Branch + PF6 Dependencies

**Files:**
- Modify: `src/frontend/package.json`
- Modify: `src/frontend/src/main.tsx`

**Produces:**
- Feature branch `feature/pf6-migration` with PF6 installed and its base CSS imported.
- App renders with PF6 styles available globally.

- [ ] **Step 1: Create feature branch**

```bash
cd /Users/nstephan/devel/rcars-advisory
git checkout -b feature/pf6-migration
```

- [ ] **Step 2: Install PF6 packages**

```bash
cd src/frontend
npm install @patternfly/react-core @patternfly/react-icons @patternfly/react-table
```

- [ ] **Step 3: Import PF6 base CSS in main.tsx**

Add PF6 CSS imports at the top of `src/frontend/src/main.tsx`, before the App import:

```tsx
import '@patternfly/react-core/dist/styles/base.css'
import '@patternfly/react-core/dist/styles/base-no-reset.css'
```

The file should read:

```tsx
import '@patternfly/react-core/dist/styles/base.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 4: Verify it builds**

```bash
cd /Users/nstephan/devel/rcars-advisory/src/frontend
npm run build
```

Expected: Build succeeds with no errors. PF6 CSS is bundled.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/package.json src/frontend/package-lock.json src/frontend/src/main.tsx
git commit -m "[RHDPCD-98] Add PF6 dependencies and import base CSS"
```

---

### Task 2: Theme Architecture — CSS + useTheme Hook

**Files:**
- Create: `src/frontend/src/styles/rcars-variables.css`
- Create: `src/frontend/src/styles/rcars-dark-overrides.css`
- Create: `src/frontend/src/styles/rcars-light-overrides.css`
- Create: `src/frontend/src/hooks/useTheme.ts`
- Modify: `src/frontend/src/main.tsx` — import new CSS files

**Produces:**
- `useTheme()` hook returning `{ theme: 'dark' | 'light', toggle: () => void }`
- `ThemeContext` for providing theme state
- `useThemeProvider()` for initializing at app root
- CSS custom properties available for all RCARS tokens in both modes
- `data-theme` attribute set on `<html>` element

- [ ] **Step 1: Create rcars-variables.css**

Create `src/frontend/src/styles/rcars-variables.css` with shared tokens used in both modes:

```css
:root {
  /* ── RCARS Brand ── */
  --rcars-amber-vivid: #FF9900;
  --rcars-purple: #9966CC;

  /* ── Spacing ── */
  --sp-xs: 4px;
  --sp-sm: 8px;
  --sp-md: 16px;
  --sp-lg: 24px;
  --sp-xl: 32px;

  /* ── Radius ── */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* ── Transitions ── */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;

  /* ── Typography ── */
  --ff-display: 'Red Hat Display', var(--pf-t--global--font--family--heading);
  --ff-body: 'Red Hat Text', var(--pf-t--global--font--family--body);
  --ff-mono: 'Red Hat Mono', var(--pf-t--global--font--family--mono);

  /* ── Pill colors (consistent across pages) ── */
  --pill-product-text: #b088d4;
  --pill-topic-text: #73bcf7;
  --pill-workload-text: #88bb88;
  --pill-module-text: #d4a04a;
  --pill-curator-text: #cc6666;

  /* ── SVG logo fills (overridden per theme below) ── */
  --logo-arc: #FF9900;
  --logo-arc-stroke: #CC6600;
  --logo-bar1: #FF9900;
  --logo-bar2: #FFCC99;
  --logo-bar3: #9966CC;
  --logo-bar-b1: #9966CC;
  --logo-bar-b2: #FF9900;
  --logo-bar-b3: #FFCC99;
  --logo-mid: #1c1c2e;
  --logo-title-fill: #000;
  --logo-subtitle: #FF9900;
}
```

- [ ] **Step 2: Create rcars-dark-overrides.css**

Create `src/frontend/src/styles/rcars-dark-overrides.css`:

```css
[data-theme="dark"] {
  --bg-page: #0f1117;
  --bg-sidebar: #0a0d12;
  --bg-masthead: #0a0d12;
  --bg-card: #1a1f2e;
  --bg-card-hover: #1f2538;
  --bg-input: #151822;
  --bg-elevated: #242a3a;
  --bg-table-header: #141824;
  --bg-table-stripe: rgba(115, 188, 247, 0.03);

  --border-default: #1e2438;
  --border-subtle: #161a28;
  --border-focus: #73bcf7;

  --text-primary: #e8e8ea;
  --text-secondary: #b8bcc8;
  --text-muted: #6b7080;
  --text-inverse: #0f1117;
  --text-link: #73bcf7;

  --score-green: #5cb85c;
  --score-green-bg: rgba(62, 134, 53, 0.12);
  --score-green-border: rgba(92, 184, 92, 0.4);
  --score-amber: #e8a838;
  --score-amber-bg: rgba(232, 168, 56, 0.1);
  --score-amber-border: rgba(232, 168, 56, 0.35);
  --score-red: #e04848;
  --score-red-bg: rgba(201, 25, 11, 0.1);
  --score-red-border: rgba(224, 72, 72, 0.35);

  --nav-active-bg: rgba(115, 188, 247, 0.08);
  --nav-active-border: #73bcf7;
  --nav-hover-bg: rgba(255, 255, 255, 0.04);

  --shadow-card: 0 1px 4px rgba(0, 0, 0, 0.3);
  --shadow-elevated: 0 4px 16px rgba(0, 0, 0, 0.4);

  --pill-product-bg: rgba(176, 136, 212, 0.12);
  --pill-product-border: rgba(176, 136, 212, 0.3);
  --pill-topic-bg: rgba(115, 188, 247, 0.1);
  --pill-topic-border: rgba(115, 188, 247, 0.25);
  --pill-workload-bg: rgba(92, 184, 92, 0.1);
  --pill-workload-border: rgba(92, 184, 92, 0.25);
  --pill-module-bg: rgba(232, 168, 56, 0.08);
  --pill-module-border: rgba(232, 168, 56, 0.2);
  --pill-curator-bg: rgba(204, 102, 102, 0.1);
  --pill-curator-border: rgba(204, 102, 102, 0.25);

  --badge-blue-bg: #1a3a5a;
  --badge-blue-text: #73bcf7;
  --badge-amber-bg: #2a2a1a;
  --badge-amber-text: #e8a838;

  --chat-user-bg: #0d1a0d;
  --chat-user-border: rgba(92, 184, 92, 0.15);

  /* Logo overrides for dark */
  --logo-arc: #FF9900;
  --logo-arc-stroke: #CC6600;
  --logo-bar1: #FF9900;
  --logo-bar2: #FFCC99;
  --logo-bar3: #9966CC;
  --logo-bar-b1: #9966CC;
  --logo-bar-b2: #FF9900;
  --logo-bar-b3: #FFCC99;
  --logo-mid: #1c1c2e;
  --logo-title-fill: #000;
  --logo-subtitle: #FF9900;
}
```

- [ ] **Step 3: Create rcars-light-overrides.css**

Create `src/frontend/src/styles/rcars-light-overrides.css`:

```css
[data-theme="light"] {
  --bg-page: #f4f1ec;
  --bg-sidebar: #ffffff;
  --bg-masthead: #ffffff;
  --bg-card: #ffffff;
  --bg-card-hover: #f9f7f4;
  --bg-input: #ffffff;
  --bg-elevated: #ffffff;
  --bg-table-header: #f4f1ec;
  --bg-table-stripe: rgba(0, 0, 0, 0.02);

  --border-default: #d2d1cc;
  --border-subtle: #e8e6e0;
  --border-focus: #0066cc;

  --text-primary: #1a1a1a;
  --text-secondary: #4a4a4a;
  --text-muted: #6a6a6a;
  --text-inverse: #ffffff;
  --text-link: #0066cc;

  --score-green: #2e7d32;
  --score-green-bg: rgba(46, 125, 50, 0.08);
  --score-green-border: rgba(46, 125, 50, 0.3);
  --score-amber: #b8860b;
  --score-amber-bg: rgba(184, 134, 11, 0.08);
  --score-amber-border: rgba(184, 134, 11, 0.3);
  --score-red: #c62828;
  --score-red-bg: rgba(198, 40, 40, 0.06);
  --score-red-border: rgba(198, 40, 40, 0.3);

  --nav-active-bg: rgba(0, 102, 204, 0.06);
  --nav-active-border: #0066cc;
  --nav-hover-bg: rgba(0, 0, 0, 0.04);

  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.04);
  --shadow-elevated: 0 4px 16px rgba(0, 0, 0, 0.1);

  --pill-product-bg: #f0e6f6;
  --pill-product-border: rgba(106, 61, 154, 0.2);
  --pill-product-text: #6a3d9a;
  --pill-topic-bg: #e7f1ff;
  --pill-topic-border: rgba(0, 76, 153, 0.2);
  --pill-topic-text: #004c99;
  --pill-workload-bg: #e6f4e6;
  --pill-workload-border: rgba(27, 94, 32, 0.2);
  --pill-workload-text: #1b5e20;
  --pill-module-bg: #fef3d5;
  --pill-module-border: rgba(140, 104, 0, 0.2);
  --pill-module-text: #8c6800;
  --pill-curator-bg: #fde8e8;
  --pill-curator-border: rgba(160, 48, 48, 0.2);
  --pill-curator-text: #a03030;

  --badge-blue-bg: #e7f1ff;
  --badge-blue-text: #004c99;
  --badge-amber-bg: #fef3d5;
  --badge-amber-text: #8c6800;

  --chat-user-bg: #e8f5e9;
  --chat-user-border: rgba(46, 125, 50, 0.2);

  /* Logo overrides for light */
  --logo-arc: #c77c00;
  --logo-arc-stroke: #a06600;
  --logo-bar1: #c77c00;
  --logo-bar2: #d4a84a;
  --logo-bar3: #7a5aaa;
  --logo-bar-b1: #7a5aaa;
  --logo-bar-b2: #c77c00;
  --logo-bar-b3: #d4a84a;
  --logo-mid: #e0ddd6;
  --logo-title-fill: #fff;
  --logo-subtitle: #8a6200;
}
```

- [ ] **Step 4: Create useTheme hook**

Create `src/frontend/src/hooks/useTheme.ts`:

```ts
import { useState, useEffect, createContext, useContext, useCallback } from 'react'

type Theme = 'dark' | 'light'

interface ThemeState {
  theme: Theme
  toggle: () => void
}

const STORAGE_KEY = 'rcars-theme'

function getInitialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark' || stored === 'light') return stored
  if (window.matchMedia('(prefers-color-scheme: light)').matches) return 'light'
  return 'dark'
}

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme)
  if (theme === 'dark') {
    document.documentElement.classList.add('pf-v6-theme-dark')
  } else {
    document.documentElement.classList.remove('pf-v6-theme-dark')
  }
}

export const ThemeContext = createContext<ThemeState>({
  theme: 'dark',
  toggle: () => {},
})

export function useTheme() {
  return useContext(ThemeContext)
}

export function useThemeProvider(): ThemeState {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  const toggle = useCallback(() => {
    setTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }, [])

  return { theme, toggle }
}
```

- [ ] **Step 5: Import CSS files in main.tsx**

Update `src/frontend/src/main.tsx` to import the RCARS CSS files after PF6 base:

```tsx
import '@patternfly/react-core/dist/styles/base.css'
import './styles/rcars-variables.css'
import './styles/rcars-dark-overrides.css'
import './styles/rcars-light-overrides.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 6: Verify build**

```bash
cd /Users/nstephan/devel/rcars-advisory/src/frontend
npm run build
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/styles/ src/frontend/src/hooks/useTheme.ts src/frontend/src/main.tsx
git commit -m "[RHDPCD-98] Add RCARS theme architecture — CSS tokens + useTheme hook"
```

---

### Task 3: App Shell — Masthead, Sidebar, Page Layout

**Files:**
- Create: `src/frontend/src/components/RcarsMasthead.tsx`
- Create: `src/frontend/src/components/RcarsSidebar.tsx`
- Create: `src/frontend/src/styles/rcars-app.css`
- Modify: `src/frontend/src/App.tsx` — replace LCARS shell with PF6
- Delete: `src/frontend/src/components/lcars/` (entire directory)

**Consumes:** `useTheme()` from Task 2, `useAuth()` from existing hooks, `api.ts` for status/sessions.

**Produces:**
- `<RcarsMasthead />` — PF6 Masthead with LCARS SVG logo (theme-adaptive fills), status dots, theme toggle, user avatar
- `<RcarsSidebar />` — PF6 PageSidebar with flattened nav (role-gated), collapsible History under Advisor
- `<App />` — PF6 `Page` wrapper with `ThemeContext`, `AuthContext`, `PrivateModeContext`, updated routes

This is the largest task. The subagent implementing it should read the design spec's Masthead, Navigation, and SVG logo sections carefully. Key details:

**Masthead SVG:** The logo SVG from the mockup at `/tmp/rcars-pf6-design-mockup.html` uses CSS classes like `rcars-svg-arc`, `rcars-svg-bar1`, etc., each mapped to `fill: var(--logo-arc)`, `fill: var(--logo-bar1)`, etc. These CSS custom properties are already defined in the dark/light override files from Task 2. The SVG must be inline in the component (not an external file) so CSS custom properties work.

**Sidebar nav structure:**

```
── Top (everyone) ──
Advisor
  History (collapsible, indented)
Browse
  Catalog
  Workloads (curator only)

── Analysis (admin) ──
Overlap
Retirement

── System (admin) ──
Status
Sync & Analysis
Recent Jobs
Token Usage
Query History
```

Clicking "Advisor" navigates to `/advisor` (new session). History toggle shows recent sessions fetched from `api.listSessions()`.

**Routes to add (new pages created in later tasks — use placeholder components for now):**

| Route | Component | Access |
|-------|-----------|--------|
| `/advisor` | `AdvisorPage` | everyone |
| `/browse` | `BrowsePage` | everyone |
| `/browse/workloads` | `WorkloadsPage` (placeholder) | curator |
| `/analysis/overlap` | `ContentOverlapPage` | admin |
| `/analysis/retirement` | `RetirementPage` | admin |
| `/system/status` | `StatusPage` (placeholder) | admin |
| `/system/sync` | `SyncPage` (placeholder) | admin |
| `/system/jobs` | `RecentJobsPage` (placeholder) | admin |
| `/system/tokens` | `AdminTokensPage` | admin |
| `/system/queries` | `AdminQueriesPage` | admin |

**Placeholder pattern** — for pages not yet migrated, create a one-line component:

```tsx
export function WorkloadsPage() {
  return <div style={{ padding: 24, color: 'var(--text-muted)' }}>Workloads — coming in Task N</div>
}
```

**`rcars-app.css`** should contain the app-level layout styles: page background, sidebar width, masthead height, card hover effects, sticky headers, scrollbar styling, and any PF6 overrides for the app shell (e.g., overriding PF6 Masthead background color with `var(--bg-masthead)`).

- [ ] **Step 1: Create `rcars-app.css`** with app shell styles (masthead, sidebar, page layout, card hover, sticky headers). Reference the design mockup CSS for exact values.

- [ ] **Step 2: Create `RcarsMasthead.tsx`** with the LCARS SVG logo (theme-adaptive via CSS custom property fills), status indicators, theme toggle button, user avatar. Use PF6 `Masthead`, `MastheadMain`, `MastheadContent`. Fetch catalog/analysis status from `api.getCatalogStats()`.

- [ ] **Step 3: Create `RcarsSidebar.tsx`** with flattened nav. Use PF6 `Nav`, `NavGroup`, `NavItem`, `NavExpandable`. Role-gate Analysis/System sections with `useAuth().isAdmin` and Browse/Workloads with `useAuth().isCurator`. Implement collapsible History under Advisor with session fetching.

- [ ] **Step 4: Create placeholder page components** for routes not yet migrated (`WorkloadsPage`, `StatusPage`, `SyncPage`, `RecentJobsPage`).

- [ ] **Step 5: Rewrite `App.tsx`** — replace LCARS shell with PF6 `Page` component. Wire `ThemeContext.Provider` and `useThemeProvider()`. Update all routes per the table above. Remove `import './styles/lcars.css'`. Import `./styles/rcars-app.css` instead.

- [ ] **Step 6: Delete `src/frontend/src/components/lcars/` directory** (all 7 files + index.ts).

- [ ] **Step 7: Import rcars-app.css in main.tsx** after the theme override files.

- [ ] **Step 8: Verify build and dev server**

```bash
cd /Users/nstephan/devel/rcars-advisory/src/frontend
npm run build
npm run dev
```

Open `http://localhost:3000`. Verify: masthead renders with logo, sidebar shows nav items, theme toggle switches between dark/light, placeholder pages load at their routes. Existing pages (Advisor, Browse, etc.) will look broken at this point — that's expected since LCARS CSS is gone.

- [ ] **Step 9: Commit**

```bash
git add -A src/frontend/src/
git commit -m "[RHDPCD-98] Replace LCARS shell with PF6 Masthead + Sidebar + Page layout"
```

---

### Task 4: Advisor Page + RecCard Migration

**Files:**
- Modify: `src/frontend/src/pages/AdvisorPage.tsx`
- Modify: `src/frontend/src/components/advisor/RecCard.tsx`
- Modify: `src/frontend/src/components/advisor/ProgressStream.tsx`

**Consumes:** Theme CSS tokens from Task 2, `useTheme()` from Task 2, all existing hooks (`useAuth`, `useJobStream`), `api.ts` unchanged.

**Produces:** Fully styled Advisor page with PF6 components and preserved RecCard layout.

Key requirements from the spec:
- **RecCard layout is structurally identical** to current: score left, title+meta center, duration right, expand caret far right. Same two-column rows, same tier-tinted backgrounds, same collapsible tiers.
- **Refinements only:** Red Hat fonts, subtle card shadow + hover lift, body separator, `★ Best fit?` badge moved inline next to `$ High Sales Impact` in usage row, new "View in RCARS" link.
- **Collapsible settings panel** near the chat input (gear icon) for dev/event toggles. Collapsed by default.
- **Expand/collapse only on title click** in RecCards (same as current behavior — already implemented this way).

The subagent should read the current `AdvisorPage.tsx`, `RecCard.tsx`, and `ProgressStream.tsx` carefully and migrate them using CSS custom properties from Task 2 instead of hardcoded LCARS colors. Replace `LcarsButton` with PF6 `Button`, `LcarsCard` usage in RecCard with a plain `<div>` styled via CSS custom properties (PF6 Card is not needed here — the current structure is better).

All inline styles referencing hardcoded colors (e.g., `#0d1a0d`, `#73bcf7`, `#666`) should be replaced with `var(--token-name)` references.

- [ ] **Step 1: Migrate `ProgressStream.tsx`** — replace hardcoded colors with CSS variables.

- [ ] **Step 2: Migrate `RecCard.tsx`** — replace `LcarsCard` import with a plain div. Use CSS custom properties for all colors. Add "View in RCARS" link (`/browse?search=${ci_name}`). Move `★ Best fit?` to inline badge in usage metrics row next to `$ High Sales Impact`. Add `$ ` prefix to sales impact badge text.

- [ ] **Step 3: Migrate `AdvisorPage.tsx`** — replace `LcarsToggle` with PF6 `Switch`. Wrap dev/event toggles in a collapsible panel (gear icon). Replace all hardcoded colors with CSS variables. Remove `LcarsButton` import.

- [ ] **Step 4: Verify in browser**

```bash
cd /Users/nstephan/devel/rcars-advisory/src/frontend && npm run dev
```

Open `http://localhost:3000/advisor`. Verify: chat renders, rec cards display with correct tier colors in dark mode, toggle to light mode and verify scoring colors adapt, click theme toggle, expand/collapse rec cards, check "View in RCARS" link exists.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/pages/AdvisorPage.tsx src/frontend/src/components/advisor/
git commit -m "[RHDPCD-98] Migrate Advisor page and RecCard to PF6 theme tokens"
```

---

### Task 5: Browse Page Redesign

**Files:**
- Modify: `src/frontend/src/pages/BrowsePage.tsx`
- Modify: `src/frontend/src/components/Pagination.tsx`
- Modify: `src/frontend/src/components/WorkloadMultiSelect.tsx`

**Consumes:** Theme CSS tokens, `useAuth()`, `api.ts` unchanged.

**Produces:** Redesigned Browse page with unified PF6 Toolbar, restructured expandable cards, and curator Drawer.

This is the most complex page. Key requirements from the spec:

**Toolbar:** Replace the three stacked panels (filter-bar + filter-panel + curator-panel) with a single PF6 `Toolbar`. Contains: `SearchInput`, PF6 `Switch` for dev/event, `Select` dropdowns for cloud provider / workloads / config, `Chip`/`ChipGroup` for active filters, item count. Curator filters (unanalyzed/failures/stale/retired) appear as additional filter pills when `isCurator`.

**Expanded card sections** — consistent order:
1. Description (always visible)
2. Learning Objectives (always visible, first 5 + "Show N more...")
3. Content Analysis (always visible) — products (purple pills) + topics (blue pills)
4. Modules (collapsible, collapsed default) — amber pills
5. Infrastructure (collapsible, collapsed default) — green pills, label "Mapped Workloads", "Access" instead of "ACL"
6. Similar Content (collapsible, collapsed default)
7. Curator Tags (always visible) — soft red pills
8. Links

**Expand/collapse:** Only clicking the item display name toggles expansion. The rest of the card body is click-safe for text selection.

**Curator Drawer:** PF6 `Drawer` from the right. Triggered by "Edit" button on expanded items (curator only). Contains all editing controls currently inline: tags, notes, curated duration, URL override, content path, flag, re-analyze.

**Pagination and WorkloadMultiSelect:** Restyle with PF6 tokens. `Pagination` can use PF6's `Pagination` component directly. `WorkloadMultiSelect` can use PF6 `Select` with typeaheadMulti variant.

- [ ] **Step 1: Build the unified Toolbar** at the top of BrowsePage replacing all three panels. Use PF6 `Toolbar`, `ToolbarContent`, `ToolbarItem`, `ToolbarFilter`, `SearchInput`, `Switch`, `Select`, `Chip`, `ChipGroup`.

- [ ] **Step 2: Build the restructured expandable card** template. Create a helper component or inline the section structure. Each section uses CSS variables for backgrounds and borders. Collapsible sections use local state.

- [ ] **Step 3: Build the curator Drawer** using PF6 `Drawer`, `DrawerContent`, `DrawerPanelContent`. Move all editing controls from inline expansion into the drawer. Wire up existing handler functions (`handleAddTag`, `handleSaveNote`, `handleSetDuration`, `handleOverrideUrl`, `handleSetContentPath`, `handleFlag`, `handleAnalyze`).

- [ ] **Step 4: Migrate Pagination** — replace custom Pagination component with PF6 `Pagination` or restyle existing with CSS variables.

- [ ] **Step 5: Verify in browser**

Open `http://localhost:3000/browse`. Verify: toolbar renders with search + filters, items expand with correct section order, collapsible sections work, curator drawer opens (test with dev user), text is selectable inside expanded cards, filter chips appear and are removable, pagination works.

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/pages/BrowsePage.tsx src/frontend/src/components/Pagination.tsx src/frontend/src/components/WorkloadMultiSelect.tsx
git commit -m "[RHDPCD-98] Redesign Browse page — unified toolbar, structured cards, curator drawer"
```

---

### Task 6: AdminPage Split — Status, Sync, RecentJobs, Workloads Pages

**Files:**
- Create: `src/frontend/src/pages/StatusPage.tsx`
- Create: `src/frontend/src/pages/SyncPage.tsx`
- Create: `src/frontend/src/pages/RecentJobsPage.tsx`
- Create: `src/frontend/src/pages/WorkloadsPage.tsx` (replace placeholder)
- Modify: `src/frontend/src/pages/AdminPage.tsx` — extract helper functions, keep TokensPage + QueriesPage
- Modify: `src/frontend/src/components/admin/LogWindow.tsx` — restyle with CSS variables
- Modify: `src/frontend/src/App.tsx` — replace placeholder imports with real components

**Consumes:** Theme CSS tokens, `api.ts`, existing AdminPage helper functions (`AdminAction`, `ScanMonitor`, `RescanAllSection`, `ScheduledMaintenance`, `WorkloadScanSection`, `WorkloadMappingSection`, `RecentJobsSection`).

**Produces:** Four new focused pages replacing the monolithic AdminPage tabs, plus restyled TokensPage and QueriesPage.

The subagent should read the current `AdminPage.tsx` (1,105 lines) and extract:

**StatusPage** (from `tab === 'status'` block, lines 656-755):
- Stat cards grid (Catalog, Analysis, Infrastructure, LLM Provider, Reporting Sync)
- ScheduledMaintenance section
- Read-only — no action buttons here
- Use PF6 `Card` for stat cards, CSS variables for all colors

**SyncPage** (from `tab === 'sync'` block, lines 757-796):
- AdminAction for Catalog Sync
- ScanMonitor
- RescanAllSection
- WorkloadScanSection (moved from `tab === 'workloads'`)
- Each uses button + LogWindow pattern

**RecentJobsPage** (from `RecentJobsSection`, lines 825-891):
- Job history table with auto-refresh
- Use PF6 `Table` with sticky headers

**WorkloadsPage** (from `WorkloadMappingSection`, lines 472-618):
- Workload mapping table with add/edit/delete
- Curator-gated (already handled by route guards in App.tsx)

**TokensPage and QueriesPage** stay in AdminPage.tsx but get restyled with CSS variables and PF6 table components.

- [ ] **Step 1: Create `StatusPage.tsx`** — extract stat cards and ScheduledMaintenance from AdminCatalogPage. Restyle with PF6 Card + CSS variables.

- [ ] **Step 2: Create `SyncPage.tsx`** — extract AdminAction, ScanMonitor, RescanAllSection, WorkloadScanSection. Restyle LogWindow with CSS variables.

- [ ] **Step 3: Create `RecentJobsPage.tsx`** — extract RecentJobsSection as a standalone page. Use PF6 Table with sticky headers.

- [ ] **Step 4: Create `WorkloadsPage.tsx`** — extract WorkloadMappingSection as a standalone page. Replace placeholder.

- [ ] **Step 5: Restyle `AdminTokensPage` and `AdminQueriesPage`** — replace hardcoded colors with CSS variables, replace `<table className="status-table">` with PF6-styled tables.

- [ ] **Step 6: Update `App.tsx`** — replace placeholder imports with real page components.

- [ ] **Step 7: Restyle `LogWindow.tsx`** — replace hardcoded colors with CSS variables.

- [ ] **Step 8: Clean up `AdminPage.tsx`** — remove extracted code. File should only contain shared helper functions (if any remain referenced), `AdminTokensPage`, and `AdminQueriesPage`.

- [ ] **Step 9: Verify in browser**

Navigate to each System page:
- `/system/status` — stat cards render, data loads
- `/system/sync` — action buttons work, log windows open
- `/system/jobs` — job table loads and auto-refreshes
- `/browse/workloads` — mapping table renders (curator only)
- `/system/tokens` — token usage table renders
- `/system/queries` — query history renders

- [ ] **Step 10: Commit**

```bash
git add src/frontend/src/pages/ src/frontend/src/components/admin/LogWindow.tsx src/frontend/src/App.tsx
git commit -m "[RHDPCD-98] Split AdminPage into Status, Sync, RecentJobs, Workloads pages"
```

---

### Task 7: Analysis Pages — Overlap + Retirement Restyling

**Files:**
- Modify: `src/frontend/src/pages/ContentAnalysisPage.tsx`
- Modify: `src/frontend/src/pages/RetirementPage.tsx`

**Consumes:** Theme CSS tokens, `api.ts`.

**Produces:** Both analysis pages restyled with CSS variables and PF6 components. No structural changes — just theme migration.

The subagent should read each page and:
1. Replace all hardcoded color values with `var(--token)` references
2. Replace `LcarsButton` with PF6 `Button`
3. Replace custom `ca-*` class styles with inline styles using CSS variables (or add them to `rcars-app.css`)
4. Ensure sticky headers on all scrollable tables
5. Verify the expand/collapse only triggers on title click (both pages already implement this)

- [ ] **Step 1: Migrate `ContentAnalysisPage.tsx`** — replace hardcoded colors with CSS variables, replace `LcarsButton` with PF6 `Button`.

- [ ] **Step 2: Migrate `RetirementPage.tsx`** — same approach. Read the current file first (not shown in this plan — the subagent must read it).

- [ ] **Step 3: Verify in browser**

- `/analysis/overlap` — stat cards, filter controls, pair list all render with correct theme colors in both dark and light
- `/analysis/retirement` — dashboard and table render correctly

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/pages/ContentAnalysisPage.tsx src/frontend/src/pages/RetirementPage.tsx
git commit -m "[RHDPCD-98] Restyle Overlap and Retirement pages with PF6 theme tokens"
```

---

### Task 8: Polish — Remove Dead CSS, Visual QA, Final Cleanup

**Files:**
- Delete: `src/frontend/src/styles/lcars.css` (if not already deleted in Task 3)
- Modify: `src/frontend/src/styles/rcars-app.css` — any remaining layout fixes
- Modify: any files with remaining hardcoded colors or LCARS references

**Produces:** Clean codebase with no LCARS remnants, all pages rendering correctly in both themes.

- [ ] **Step 1: Search for remaining LCARS references**

```bash
cd /Users/nstephan/devel/rcars-advisory/src/frontend
grep -rn "lcars\|LCARS\|lcars.css" src/ --include='*.tsx' --include='*.ts' --include='*.css'
```

Expected: No results. If any remain, fix them.

- [ ] **Step 2: Search for hardcoded color values**

```bash
grep -rn '#0f1117\|#0a0d12\|#1a1f2e\|#73bcf7\|#5cb85c\|#e8a838\|#c9190b\|#666\b' src/ --include='*.tsx' --include='*.ts' | grep -v node_modules | grep -v 'rcars-'
```

Any hardcoded colors in `.tsx` files should be replaced with CSS variable references. Colors in the `rcars-*.css` files are expected.

- [ ] **Step 3: Visual QA — dark mode**

Open `http://localhost:3000` in dark mode. Visit every page:
- [ ] Advisor — chat, rec cards, settings panel
- [ ] Browse — toolbar, expanded cards, drawer
- [ ] Browse Workloads — mapping table
- [ ] Overlap — stat cards, pair list
- [ ] Retirement — dashboard, table
- [ ] Status — stat cards
- [ ] Sync — action buttons, log windows
- [ ] Recent Jobs — job table
- [ ] Token Usage — usage table
- [ ] Query History — session list

Verify: no white-on-white text, no invisible elements, scoring colors distinct, pills correctly colored, sticky headers work, theme toggle visible.

- [ ] **Step 4: Visual QA — light mode**

Toggle to light mode and repeat all page visits. Pay attention to:
- Muted text contrast (should be `#6a6a6a` not `#8a8a8a`)
- Logo adapts (darker amber)
- Scoring badges readable on light backgrounds
- Card shadows visible but not harsh

- [ ] **Step 5: Verify build**

```bash
cd /Users/nstephan/devel/rcars-advisory/src/frontend
npm run build
npm run lint
```

Both should pass with no errors.

- [ ] **Step 6: Commit**

```bash
git add -A src/frontend/
git commit -m "[RHDPCD-98] Polish — remove dead CSS, visual QA fixes"
```

---

## Summary

| Task | Description | Key Files |
|------|-------------|-----------|
| 1 | Feature branch + PF6 deps | `package.json`, `main.tsx` |
| 2 | Theme CSS + useTheme hook | `styles/rcars-*.css`, `hooks/useTheme.ts` |
| 3 | App shell — Masthead, Sidebar, routing | `RcarsMasthead.tsx`, `RcarsSidebar.tsx`, `App.tsx` |
| 4 | Advisor + RecCard migration | `AdvisorPage.tsx`, `RecCard.tsx` |
| 5 | Browse page redesign | `BrowsePage.tsx`, `Pagination.tsx` |
| 6 | AdminPage split | `StatusPage.tsx`, `SyncPage.tsx`, `RecentJobsPage.tsx`, `WorkloadsPage.tsx` |
| 7 | Analysis pages restyling | `ContentAnalysisPage.tsx`, `RetirementPage.tsx` |
| 8 | Polish + visual QA | All files — cleanup pass |
