# Design: Admin Action Feedback + Per-Item Re-analyze

**Date:** 2026-04-10  
**Status:** Approved

## Problem

Three operations across two pages give poor or no feedback:

1. **Sync Catalog** (admin) — takes ~30 seconds, blocks silently.
2. **Analyze Showroom Content** (admin) — takes 30–60 minutes, shows nothing until page is manually refreshed.
3. **Per-item re-analyze** (curate) — doesn't exist yet. Curators have no way to trigger re-analysis of a single Showroom after content changes.

Additionally, the admin buttons had inconsistent names ("Refresh Catalog" vs "Trigger Rescan") that didn't clearly convey their purpose or difference.

## Goals

- All three operations give immediate visual feedback on click.
- Running operations show live status (Sync: spinner; Analyze: live log lines; Per-item: spinner + status text).
- The Catalog Status table auto-updates when Sync or Analyze completes.
- Naming is consistent and self-explanatory across the admin page.

## Naming

| Old | New button label | New section heading |
|-----|-----------------|---------------------|
| Refresh Catalog | Sync Catalog | Catalog Sync |
| Trigger Rescan | Analyze Showroom Content | Showroom Analysis |
| *(new)* | Re-analyze ↺ | *(per-item, curate page)* |

"Sync" = quick metadata pull. "Analyze" = deep content crawl. "Re-analyze" = re-run analysis for one item.

---

## Architecture: Shared Pattern

All three use the same fire-and-forget + HTMX polling approach:

1. Button click → `POST` endpoint → spawns background thread, returns immediately with HTML fragment carrying `hx-get="…/status" hx-trigger="every 2s" hx-target="#<status-div>" hx-swap="outerHTML"`.
2. Status endpoint while running → returns running fragment (same polling attrs, keeps loop alive).
3. Status endpoint when done → returns result fragment (no polling attrs, stops loop) + any OOB swaps.

---

## Component 1: Catalog Sync (admin page)

### Backend — `src/rcars/web/routes/admin.py`

**Global state:**
```python
_refresh_status: dict = {"running": False, "result": None, "color": None}
```

**`_run_refresh` (refactored):**
Sets `running = True`, runs `rcars refresh` via `subprocess.run` (~30s — fast enough that line-by-line streaming isn't needed), writes `result`/`color` on completion, sets `running = False` on exit.

**`POST /admin/refresh` (modified):**
- Already running → return "Sync already in progress" message.
- Otherwise → start `threading.Thread(target=_run_refresh, daemon=True)`, return running fragment immediately.

**`GET /admin/refresh/status` (new):**
- Running → running fragment (spinner + "Syncing catalog…", polling attrs preserved).
- Done → result fragment (green/red, no polling attrs) + OOB-swapped `#catalog-status-table`. Reset `result`/`color` to `None` after serving.
- Idle → empty `<div id="refresh-status"></div>`.

### Frontend — `src/rcars/web/templates/admin.html`

- Section heading: "Catalog Sync"; button: "Sync Catalog".
- Button disabled while running via `hx-on::before-request`.
- Add `id="catalog-status-table"` to the status table (shared with Analyze).

### Visual states

| State | Button | Status |
|-------|--------|--------|
| Idle | Enabled | Empty |
| Running | Disabled | Amber spinner + "Syncing catalog…" |
| Success | Re-enabled | Green "Catalog sync complete." + table updates |
| Error | Re-enabled | Red "Sync failed: …" |

---

## Component 2: Analyze Showroom Content (admin page)

### Backend — `src/rcars/web/routes/admin.py`

**Global state (replaces old `_rescan_status`):**
```python
_rescan_status: dict = {"running": False, "lines": [], "exit_ok": None}
```
`lines` is a list of strings accumulated from the subprocess in real time. `exit_ok` is `None` while running, `True`/`False` on completion.

**`_run_rescan` (refactored):**
Switches from `subprocess.run` to `subprocess.Popen(stdout=PIPE, stderr=STDOUT, text=True)`. Reads lines via `proc.stdout.readline()` in a loop, appending each to `_rescan_status["lines"]` (capped at 500 lines). Sets `exit_ok` based on `proc.returncode` after exit.

**`POST /admin/rescan` (modified):**
- Already running → return "Analysis already in progress" message.
- Otherwise → reset `lines = []`, `exit_ok = None`, start thread, return running fragment immediately.

**`GET /admin/rescan/status` (new):**
- Running → running fragment (spinner + "Analysis running…" + last 20 lines in log box, polling attrs).
- Done → result fragment (green/red header + last 20 lines, no polling attrs) + OOB-swapped `#catalog-status-table`. Reset `exit_ok` to `None` after serving.
- Idle → empty `<div id="rescan-status"></div>`.

Both status endpoints require `db: Database` as a dependency for the OOB status table.

### Frontend — `src/rcars/web/templates/admin.html`

- Section heading: "Showroom Analysis"; button: "Analyze Showroom Content".
- Remove the existing `{% if rescan_running %}` template block — replaced by the polling pattern.
- Log box: monospace, small font, dark background. Lines appear top-to-bottom; newest at the bottom.

### Visual states

| State | Button | Status |
|-------|--------|--------|
| Idle | Enabled | Empty |
| Running | Disabled | Amber spinner + "Analysis running…" + live log box |
| Success | Re-enabled | Green "Analysis complete." + final log lines + table updates |
| Error | Re-enabled | Red "Analysis failed." + final log lines + table updates |

---

## Component 3: Per-item Re-analyze (curate page)

### Backend — `src/rcars/web/routes/curate.py`

**Global state:**
```python
_item_analyze_status: dict[str, dict] = {}
# key: ci_name → {"running": bool, "result": str | None, "color": str | None}
```
Keyed by `ci_name` so multiple curators can trigger different items concurrently.

**`POST /curate/analyze` (new):**
- Accepts `ci_name` as form field.
- If already running for that item → return "Already analyzing" message.
- Otherwise → set status entry, start `threading.Thread`, return running fragment immediately.
  Fragment targets `#analyze-status-{ci_name_safe}` (where `ci_name_safe` = `ci_name` with dots replaced by dashes).

**`GET /curate/analyze/status` (new):**
- Accepts `ci_name` as query param.
- Running → running fragment (spinner + "Analyzing…", polling attrs).
- Done → result fragment (green "Analysis complete." / red "Analysis failed.", no polling attrs). Reset entry after serving.
- Idle/unknown → empty div.

**Background thread:**
Imports and calls `analyze_showroom()` directly (same function the CLI uses) then calls `db.upsert_showroom_analysis()` and `db.store_embedding()`. No subprocess — this is a direct Python call, so no Popen needed. Status is set to result/color on completion.

Requires `settings` and `db` to be passed to the thread function (captured at dispatch time, not accessed inside the thread via dependency injection).

### Frontend — `src/rcars/web/templates/curate.html`

- Add "Re-analyze ↺" button to each item card, **right-aligned** (pushed to the far right of the button row via `justify-content: space-between`).
- Button styled distinctly from curator actions (purple tint: `#2a1a40` bg, `#b794f4` text) to signal it's a different kind of action.
- Button disabled while analysis for that item is running.
- Add per-item status div below the button row: `<div id="analyze-status-{ci_name_safe}"></div>`.
- Status appears inline within the item card — no page navigation or modal.

### Visual states (per item)

| State | Button | Status |
|-------|--------|--------|
| Idle | Enabled | Empty |
| Running | Disabled | Purple spinner + "Analyzing…" |
| Success | Re-enabled | Green "✓ Analysis complete." |
| Error | Re-enabled | Red "Analysis failed." |

---

## Shared: Catalog Status Table OOB Swap

- `id="catalog-status-table"` on the `<table>` in the Catalog Status section of admin.html.
- Both `/admin/refresh/status` and `/admin/rescan/status` include an `hx-swap-oob="true"` version of this table on completion, built from `db.get_status_summary()`.
- Per-item re-analyze does **not** OOB-swap the status table (the curate page doesn't show those counts).

---

## Error Handling

- Subprocess/function timeout: caught as exception, sets error state with message.
- Second trigger while running: "already in progress" message; operation continues.
- Pod restart mid-run: in-memory state is lost; all operations return to idle on next poll. Acceptable — no DB dependency added.
- Concurrent per-item re-analyzes of different items: supported via the keyed `_item_analyze_status` dict.

## What Is Not Changing

- The `jobs` database table is not used.
- "Analyze only changed showrooms" (staleness detection via `is_stale`/`stale_commit`) is deferred to a future iteration.
- No new Python dependencies.
- Auth/access control is unchanged (`require_admin` for admin routes, `require_curator` for curate routes).
