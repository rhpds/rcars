# Design: Admin Action Feedback (Sync Catalog + Analyze Showroom Content)

**Date:** 2026-04-10  
**Status:** Approved

## Problem

The admin page has two long-running operations with poor feedback:

1. **Sync Catalog** (formerly "Refresh Catalog") — takes ~30 seconds, blocks silently with no indication that anything is happening.
2. **Analyze Showroom Content** (formerly "Trigger Rescan") — takes 30–60 minutes, shows nothing until the page is manually refreshed.

Additionally, the two operations have inconsistent names ("Refresh Catalog" vs "Trigger Rescan") that don't clearly convey their purpose or difference.

## Goals

- Both buttons give immediate visual feedback on click.
- Both operations show live status while running.
- "Analyze Showroom Content" shows actual log lines from the subprocess as it runs.
- The Catalog Status table auto-updates when either operation completes.
- Naming is consistent and self-explanatory.

## Naming

| Old | New button label | New section heading |
|-----|-----------------|---------------------|
| Refresh Catalog | Sync Catalog | Catalog Sync |
| Trigger Rescan | Analyze Showroom Content | Showroom Analysis |

"Sync" implies a quick pull of metadata. "Analyze" implies a deeper, slower process. The section headings add context; the button labels are action-oriented.

## Architecture

Both operations use the same pattern: fire-and-forget background thread + HTMX polling every 2s. The polling endpoint self-perpetuates while the operation runs, then stops and triggers an OOB swap of the Catalog Status table when done.

### HTMX polling pattern

1. Button click → `POST /admin/<action>` → spawns background thread, returns immediately with HTML fragment carrying `hx-get="/admin/<action>/status" hx-trigger="every 2s" hx-target="#<action>-status" hx-swap="outerHTML"`.
2. `GET /admin/<action>/status` while running → returns running fragment (same polling attrs, keeps loop alive).
3. `GET /admin/<action>/status` when done → returns result fragment (no polling attrs, stops loop) + OOB-swapped `#catalog-status-table` with fresh counts.

## Component: Catalog Sync

### Backend (`admin.py`)

**Global state:**
```python
_refresh_status: dict = {"running": False, "result": None, "color": None}
```

**`_run_refresh` (refactored):**  
Sets `running = True` on entry, runs `rcars refresh` via `subprocess.run` (unchanged — ~30s is fast enough that line-by-line streaming isn't needed), writes result/color on completion, sets `running = False` on exit.

**`POST /admin/refresh` (modified):**  
- If already running: return "Sync already in progress" message.
- Otherwise: start `threading.Thread(target=_run_refresh, daemon=True)`, return running fragment immediately.

**`GET /admin/refresh/status` (new):**  
- Running → running fragment (spinner + "Syncing catalog…", polling attrs).
- Done → result fragment (green/red, no polling attrs) + OOB status table. Reset result/color to None after serving.
- Idle → empty `<div id="refresh-status"></div>`.

### Frontend (`admin.html`)

- Section heading: "Catalog Sync"
- Button label: "Sync Catalog"
- Button disabled while running (via `hx-on::before-request` on the button, re-enabled by the completion fragment).

### Visual states

| State | Button | Status area |
|-------|--------|-------------|
| Idle | Enabled | Empty |
| Running | Disabled | Amber spinner + "Syncing catalog…" |
| Success | Re-enabled | Green "Catalog sync complete." + status table updates |
| Error | Re-enabled | Red "Sync failed: …" |

## Component: Analyze Showroom Content

### Backend (`admin.py`)

**Global state (extended):**
```python
_rescan_status: dict = {"running": False, "lines": [], "exit_ok": None}
```
`lines` is a list of strings accumulated from the subprocess in real time. `exit_ok` is `None` while running, `True`/`False` on completion.

**`_run_rescan` (refactored):**  
Switches from `subprocess.run` to `subprocess.Popen` with `stdout=PIPE, stderr=STDOUT, text=True`. Reads lines in a loop via `proc.stdout.readline()`, appending each to `_rescan_status["lines"]` (capped at 500 lines to avoid unbounded memory growth). Sets `exit_ok` based on `proc.returncode` after the process exits.

**`POST /admin/rescan` (modified):**  
- If already running: return "Analysis already in progress" message.
- Otherwise: reset `lines = []`, `exit_ok = None`, start thread, return running fragment immediately.

**`GET /admin/rescan/status` (new):**  
- Running → running fragment with last 20 lines rendered in a log box + polling attrs.
- Done → result fragment (green "Analysis complete" / red "Analysis failed", last 20 lines, no polling attrs) + OOB status table. Reset `exit_ok` to `None` after serving.
- Idle → empty `<div id="rescan-status"></div>`.

### Frontend (`admin.html`)

- Section heading: "Showroom Analysis"
- Button label: "Analyze Showroom Content"
- Remove the old `{% if rescan_running %}` template block — replaced by the polling pattern.
- The `#rescan-status` div renders the log box; no separate pre-rendered output area needed.

### Visual states

| State | Button | Status area |
|-------|--------|-------------|
| Idle | Enabled | Empty |
| Running | Disabled | Amber spinner + "Analysis running…" + live log box (last 20 lines) |
| Success | Re-enabled | Green "Analysis complete." + final log lines + status table updates |
| Error | Re-enabled | Red "Analysis failed." + final log lines + status table updates |

### Log box appearance

Monospace, small font, dark background — same styling as the current `<pre>` output block. Lines scroll from top; newest lines appear at the bottom. Each line is rendered as-is from the subprocess stdout.

## Shared: Catalog Status Table OOB Swap

- Add `id="catalog-status-table"` to the `<table>` in the Catalog Status section.
- Both status endpoints (refresh and rescan) include an OOB-swapped version of this table on completion, built from `db.get_status_summary()`.
- Both status endpoints require `db: Database` as a dependency.

## Error Handling

- Subprocess timeout (300s for sync, 3600s for analyze): caught as exception, sets error state.
- Second admin clicks while running: immediately sees "already in progress" message, operation continues unaffected.
- Pod restart mid-run: in-memory state is lost; both buttons return to idle state. The page will show no in-progress indicator. Acceptable trade-off — no DB dependency added.

## What Is Not Changing

- The `jobs` database table is not used.
- No new Python dependencies.
- Auth/access control is unchanged.
