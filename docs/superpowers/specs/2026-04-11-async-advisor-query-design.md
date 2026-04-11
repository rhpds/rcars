# Async Advisor Query — Design Spec

**Date:** 2026-04-11
**Status:** Approved

## Problem

`POST /advisor/query` calls `recommend()` synchronously. This takes 50+ seconds (Vertex AI + sentence-transformers). OpenShift HAProxy has a ~60s connection timeout and drops the connection before the response arrives. The UI receives nothing.

## Solution

Fire-and-forget + HTMX polling, identical to the pattern already used by `POST /admin/rescan` and `POST /admin/refresh`.

## Architecture

```
Browser                         Server
  |                               |
  |-- POST /advisor/query ------->|  (validates, spawns thread, returns immediately)
  |<-- spinner fragment ----------|  (rec-pane replaced by polling div)
  |                               |
  |-- GET /advisor/query/status ->|  (every 2s while running)
  |<-- spinner fragment ----------|
  |-- GET /advisor/query/status ->|
  |<-- spinner fragment ----------|
  |         ...                   |
  |-- GET /advisor/query/status ->|  (when done)
  |<-- rec_html + OOB chat_turn --| (no polling attrs → stops)
```

## Components

### State dict — `_query_status` in `advisor.py`

Module-level dict, keyed by `session_id`:

```python
_query_status: dict[str, dict] = {}
# value shape:
# {
#   "running": bool,
#   "rec_html": str | None,
#   "chat_html": str | None,
#   "error": str | None,
# }
```

**Scale note:** This dict lives in-process. For the target scale (≤100 users, single OpenShift replica) this is safe. If the deployment is ever scaled to multiple replicas, polling requests may land on a different pod than the one running the query. At that point, replace with a shared store (e.g. Redis or a DB-backed job table). This does not need to change now.

### `POST /advisor/query` (refactored)

1. Validate: db present, Anthropic client present. If not → return error immediately in "done" format (no thread, no polling).
2. Add user message to `_sessions[session_id]`.
3. Store `_query_status[session_id] = {"running": True, "rec_html": None, "chat_html": None, "error": None}`.
4. Spawn `threading.Thread(target=_run_advisor_query, args=(...), daemon=True).start()`.
5. Return spinner fragment immediately (HTTP 200).

### `_run_advisor_query(...)` (background thread)

1. Calls `recommend()`.
2. Enriches results, renders `rec_list.html` and `chat_turn.html` templates.
3. Stores rendered HTML in `_query_status[session_id]`, sets `running=False`.

Uses the module-level `templates` object (Jinja2 rendering is thread-safe).

### Spinner fragment

Replaces `#rec-pane` entirely (outer-HTML swap):

```html
<div id="rec-pane"
     hx-get="/advisor/query/status?session_id=SESSION_ID"
     hx-trigger="every 2s"
     hx-swap="outerHTML">
  <div class="pane-label">Recommendations</div>
  <div class="rec-pane-loading">
    <span class="thinking-dots">...</span>
    Analyzing your request <span style="color:#555;">(this may take a minute)</span>
  </div>
</div>
```

### `GET /advisor/query/status?session_id=...` (new endpoint)

- `session_id` not found in dict → return spinner (graceful; shouldn't happen in normal flow)
- `running == True` → return spinner
- `running == False` → pop entry from dict; return done fragment

### Done fragment

```html
<div id="rec-pane">
  {rec_html}
  <span id="advisor-result-ready" hidden></span>
</div>
{chat_turn OOB — hx-swap-oob="beforeend:#chat-pane"}
```

The hidden sentinel `#advisor-result-ready` signals the JS that the query is complete.

### Error cases

Immediate errors (no db, no client): return done-shaped fragment directly from the POST handler — `<div id="rec-pane">` with error text + sentinel + OOB chat turn. No thread spawned. No polling.

Background errors (recommend() throws): thread stores `error` string in `_query_status`. Status endpoint renders error text in the done fragment.

### JS changes in `advisor.html`

Two changes only:

1. **`htmx.ajax` swap mode:** `'innerHTML'` → `'outerHTML'` so the spinner replaces the entire `#rec-pane` element.

2. **`htmx:afterSwap` listener:** Instead of matching `e.detail.target.id === 'rec-pane'` (fires every 2s during polling), check for the sentinel:

```javascript
document.body.addEventListener('htmx:afterSwap', function restoreBtn(e) {
  if (document.getElementById('advisor-result-ready')) {
    document.body.removeEventListener('htmx:afterSwap', restoreBtn);
    document.getElementById('thinking-indicator')?.remove();
    sendBtn.disabled = false;
    sendBtn.textContent = 'Send';
    sendBtn.classList.remove('sending');
    chatPane.scrollTop = chatPane.scrollHeight;
  }
});
```

The thinking-indicator in the chat pane (shown immediately by JS) is removed when the sentinel is detected.

## Tests

Existing tests to update (POST now returns spinner, not rec cards):
- `test_advisor_query_returns_rec_cards` → assert spinner returned; assert status endpoint returns rec cards
- `test_advisor_query_appends_chat_turn` → assert status endpoint response contains chat-pane OOB
- `test_advisor_query_accumulates_context` → unchanged logic, but POST → status flow; mock threading to run inline
- `test_advisor_query_handles_recommend_none` → check status endpoint returns error text

New tests to add:
- `test_advisor_query_status_while_running` — manually set `_query_status[sid]["running"] = True`, assert spinner returned
- `test_advisor_query_status_when_done` — manually populate completed `_query_status[sid]`, assert done fragment
- `test_advisor_query_status_unknown_session` — assert graceful spinner returned

## Files Changed

| File | Change |
|------|--------|
| `src/rcars/web/routes/advisor.py` | Add `_query_status`, `_run_advisor_query`, spinner/done helpers, refactor POST, add GET status |
| `src/rcars/web/templates/advisor.html` | Two JS changes: swap mode + afterSwap sentinel check |
| `tests/web/test_advisor.py` | Update existing tests, add status endpoint tests |

## Files NOT Changed

- `chat_turn.html` — OOB pattern already correct
- `rec_list.html` — unchanged
- `admin.py` — reference pattern only
- All other routes
