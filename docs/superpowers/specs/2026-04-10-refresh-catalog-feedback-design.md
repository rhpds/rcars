# Design: Refresh Catalog Feedback

**Date:** 2026-04-10  
**Status:** Approved

## Problem

When an admin clicks "Refresh Catalog", the UI gives no feedback for ~30 seconds until the HTTP request completes. Users have no way to know the request was received or that work is in progress.

## Solution

Convert the synchronous blocking request to a fire-and-forget pattern with HTMX polling — the same pattern already used by the Rescan button in `admin.py`. On completion, automatically update the Catalog Status table via HTMX out-of-band swap so the admin sees fresh counts without a page reload.

## Architecture

### Approach chosen: Fire-and-Forget + HTMX Polling

1. `POST /admin/refresh` spawns a background thread and returns immediately with an HTML fragment carrying HTMX polling attributes.
2. `GET /admin/refresh/status` is polled every 2s. While running, it returns a "running" fragment (which preserves polling attributes, keeping the loop alive). When done, it returns a "complete" fragment (no polling attributes, stopping the loop) plus an OOB swap of the catalog status table.
3. In-memory state only — no database writes, consistent with `_rescan_status`.

### State machine

| State | Button | `#refresh-status` content |
|-------|--------|--------------------------|
| Idle | Enabled | Empty |
| Running | Disabled | Amber spinner + "Refreshing catalog…" |
| Success | Re-enabled | Green "Catalog refresh complete." |
| Error | Re-enabled | Red "Refresh failed: …" |

On success or error, the catalog status table also auto-updates with fresh counts from `db.get_status_summary()`.

## Components

### Backend: `src/rcars/web/routes/admin.py`

**New global state:**
```python
_refresh_status: dict = {"running": False, "result": None, "color": None}
```

**Refactored `_run_refresh`:**  
Updates `_refresh_status` in place (running → True on start, result/color set on completion, running → False on exit). No longer returns a tuple.

**Modified `POST /admin/refresh`:**  
- If `_refresh_status["running"]` is True, return an "already running" message.
- Otherwise, start a `threading.Thread(target=_run_refresh, daemon=True)` and immediately return an HTML fragment with:
  ```
  hx-get="/admin/refresh/status"
  hx-trigger="every 2s"
  hx-target="#refresh-status"
  hx-swap="outerHTML"
  ```
  The fragment includes the spinner and "Refreshing catalog…" text so feedback is instant.

**New `GET /admin/refresh/status`:**  
- **Running:** Return the same running fragment (with polling attrs) — self-perpetuating.
- **Done (result set):** Return the result fragment (green/red text, no polling attrs) plus an OOB-swapped `<table id="catalog-status-table" hx-swap-oob="true">` built from `db.get_status_summary()`. Then reset `_refresh_status["result"]` and `_refresh_status["color"]` to `None` so the next poll returns idle.
- **Idle:** Return an empty `<div id="refresh-status"></div>`.

The status endpoint requires `db: Database` as a dependency (needed for the OOB status table on completion).

### Frontend: `src/rcars/web/templates/admin.html`

- Add `id="catalog-status-table"` to the `<table>` in the Catalog Status section.
- No changes to the button or `#refresh-status` div — the button already posts to `/admin/refresh` and targets `#refresh-status`.

## Error handling

- If the subprocess times out or returns non-zero, `_refresh_status` is set with a red error message (first 200 chars of stderr), same as current behavior.
- If a second admin clicks "Refresh Catalog" while one is running, they immediately see an "already running" message.

## What is not changing

- The `jobs` database table is not used.
- The Rescan section is unchanged.
- No new dependencies.
