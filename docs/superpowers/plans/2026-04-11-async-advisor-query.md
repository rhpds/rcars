# Async Advisor Query Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Implemented (2026-04-11) — 8 commits, 48 tests passing.

**Goal:** Refactor `POST /advisor/query` from a blocking synchronous call into a fire-and-forget + HTMX polling pattern so it survives OpenShift HAProxy's ~60s connection timeout.

**Architecture:** The POST handler validates inputs, stores a "running" entry in a module-level dict keyed by `session_id`, spawns a daemon thread to call `recommend()`, and returns an HTMX spinner fragment immediately. A new `GET /advisor/query/status` endpoint polls every 2 seconds and returns either another spinner (running) or the final results (done). The JS in `advisor.html` is updated to use `outerHTML` swap and detect completion via a hidden sentinel element.

**Tech Stack:** Python 3.11, FastAPI, Jinja2, HTMX 1.9.12, `threading.Thread` (stdlib), `pytest` + `starlette.testclient`

**Spec:** `docs/superpowers/specs/2026-04-11-async-advisor-query-design.md`

**Test command:** `source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/web/ -q`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/rcars/web/routes/advisor.py` | Modify | Add `_query_status` dict, `_run_advisor_query` thread fn, spinner/done fragment helpers, refactor POST, add GET status endpoint |
| `src/rcars/web/templates/advisor.html` | Modify | Change `htmx.ajax` swap to `outerHTML`; update `htmx:afterSwap` handler to use sentinel |
| `tests/web/test_advisor.py` | Modify | Update 4 existing tests; add 3 new status endpoint tests |

No new files. No other files touched.

---

### Task 1: Add `_query_status` dict and thread function to `advisor.py`

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`

This task adds the state container and background worker. No endpoints change yet — tests stay green.

- [ ] **Step 1: Add `import threading` at the top of `advisor.py`**

Open `src/rcars/web/routes/advisor.py`. The imports block is at lines 1–18. Add `import threading` after `import logging`:

```python
import logging
import re
import threading
import uuid
```

- [ ] **Step 2: Add `_query_status` dict below `_sessions`**

`_sessions` is defined at line 72. Add `_query_status` immediately after it:

```python
_sessions: dict[str, list[dict]] = {}
_query_status: dict[str, dict] = {}
# shape: session_id → {"running": bool, "rec_html": str|None, "chat_html": str|None, "error": str|None}
```

- [ ] **Step 3: Add `_run_advisor_query` function**

Add this function after `_base_context` (currently ending around line 116). Place it before the route handlers:

```python
def _run_advisor_query(
    session_id: str,
    message: str,
    description: str,
    first_message: str,
    db,
    client,
    settings,
    user: str,
) -> None:
    """Background thread: call recommend(), render fragments, store in _query_status."""
    turn_index = len(_sessions.get(session_id, []))
    try:
        log.info("advisor bg: generating embedding and searching candidates session=%s", session_id)
        result = recommend(
            query=description,
            db=db,
            anthropic_client=client,
            model=settings.model,
            limit=10,
            prod_only=True,
        )
        recs_count = len((result or {}).get("recommendations", []))
        log.info("advisor bg: recommend() returned %d recommendations session=%s", recs_count, session_id)
    except Exception:
        log.exception("advisor bg: recommend() failed session=%s", session_id)
        result = None

    raw_recs = result.get("recommendations", []) if result else []
    recs = _enrich_recs(raw_recs, db)

    overall = (result or {}).get("overall_assessment", f"Found {len(recs)} matches.")
    turns = _sessions.setdefault(session_id, [])
    turns.append({
        "role": "assistant",
        "content": overall,
        "rec_ci_names": [r["ci_name"] for r in recs],
        "recs": recs,
        "turn_index": turn_index,
    })

    is_curator = settings.is_curator(user)

    rec_html = templates.get_template("fragments/rec_list.html").render(
        recs=recs,
        is_curator=is_curator,
        session_id=session_id,
    )
    chat_html = templates.get_template("fragments/chat_turn.html").render(
        user_message=message,
        assistant_message=overall,
        session_id=session_id,
        turn_index=turn_index,
        first_message=first_message,
    )

    _query_status[session_id] = {
        "running": False,
        "rec_html": rec_html,
        "chat_html": chat_html,
        "error": None,
    }
```

- [ ] **Step 4: Run existing tests — they must still pass**

```bash
source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/web/ -q
```

Expected: all tests pass (no endpoint has changed yet).

- [ ] **Step 5: Commit**

```bash
cd /Users/nstephan/devel/working/rcars-advisory
git add src/rcars/web/routes/advisor.py
git commit -m "advisor: Add async query state dict and background thread function"
```

---

### Task 2: Add spinner and done fragment helpers to `advisor.py`

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`

These helpers produce the HTML fragments returned by the POST and GET status endpoints. No endpoint logic yet.

- [ ] **Step 1: Add `_query_spinner_fragment` helper**

Add after `_run_advisor_query`:

```python
def _query_spinner_fragment(session_id: str) -> str:
    """HTMX polling spinner that replaces #rec-pane while query runs."""
    return (
        f'<div id="rec-pane"'
        f' hx-get="/advisor/query/status?session_id={session_id}"'
        f' hx-trigger="every 2s"'
        f' hx-swap="outerHTML">'
        f'<div class="pane-label">Recommendations</div>'
        f'<div class="rec-pane-loading">'
        f'<span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span>'
        f' Analyzing your request'
        f' <span style="color:#555;">(this may take a minute)</span>'
        f'</div>'
        f'</div>'
    )
```

- [ ] **Step 2: Add `_query_done_fragment` helper**

Add after `_query_spinner_fragment`:

```python
def _query_done_fragment(rec_html: str, chat_html: str) -> str:
    """Done response: rec pane content + OOB chat turn. Sentinel stops JS polling detection."""
    return (
        f'<div id="rec-pane">'
        f'{rec_html}'
        f'<span id="advisor-result-ready" hidden></span>'
        f'</div>'
        f'\n{chat_html}'
    )
```

- [ ] **Step 3: Add `_query_error_fragment` helper**

Add after `_query_done_fragment`:

```python
def _query_error_fragment(error_msg: str, message: str, session_id: str, first_message: str, turns: list) -> str:
    """Immediate error response (no thread). Same shape as done fragment."""
    turn_index = len(turns)
    turns.append({"role": "assistant", "content": error_msg, "rec_ci_names": [], "turn_index": turn_index})
    rec_html = (
        '<div class="pane-label">Recommendations</div>'
        f'<p style="color:var(--score-red);font-size:14px;">{error_msg}</p>'
    )
    chat_html = templates.get_template("fragments/chat_turn.html").render(
        user_message=message,
        assistant_message=error_msg,
        session_id=session_id,
        turn_index=turn_index,
        first_message=first_message,
    )
    return _query_done_fragment(rec_html, chat_html)
```

- [ ] **Step 4: Run existing tests — still passing**

```bash
source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/web/ -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/rcars/web/routes/advisor.py
git commit -m "advisor: Add spinner, done, and error fragment helpers for async query"
```

---

### Task 3: Refactor `POST /advisor/query` and add `GET /advisor/query/status`

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`

This is the core behaviour change. The POST now returns immediately; the GET status polls until done.

- [ ] **Step 1: Replace the `advisor_query` route handler**

The current handler is at lines 169–250. Replace the entire function with:

```python
@router.post("/advisor/query", response_class=HTMLResponse)
async def advisor_query(
    request: Request,
    session_id: Annotated[str, Form()],
    message: Annotated[str, Form()],
    user: str = Depends(get_current_user),
    db: Database | None = Depends(_get_db_dependency),
):
    settings = Settings()
    turns = _sessions.setdefault(session_id, [])
    turns.append({"role": "user", "content": message})
    first_message = turns[0]["content"] if turns else message

    if not db:
        return HTMLResponse(_query_error_fragment(
            "Database not configured. Set RCARS_DATABASE_URL.",
            message, session_id, first_message, turns,
        ))

    client = settings.get_anthropic_client()
    if not client:
        return HTMLResponse(_query_error_fragment(
            "No Anthropic credentials configured. Set ANTHROPIC_VERTEX_PROJECT_ID or ANTHROPIC_API_KEY.",
            message, session_id, first_message, turns,
        ))

    description = " ".join(t["content"] for t in turns if t["role"] == "user")
    log.info("advisor: spawning background query user=%s session=%s query=%r", user, session_id, description[:120])

    _query_status[session_id] = {"running": True, "rec_html": None, "chat_html": None, "error": None}
    t = threading.Thread(
        target=_run_advisor_query,
        args=(session_id, message, description, first_message, db, client, settings, user),
        daemon=True,
    )
    t.start()

    return HTMLResponse(_query_spinner_fragment(session_id))
```

- [ ] **Step 2: Add `GET /advisor/query/status` route**

Add this route immediately after `advisor_query`:

```python
@router.get("/advisor/query/status", response_class=HTMLResponse)
async def advisor_query_status(
    session_id: str,
    user: str = Depends(get_current_user),
):
    status = _query_status.get(session_id)
    if status is None or status["running"]:
        return HTMLResponse(_query_spinner_fragment(session_id))

    # Done — pop and return result
    _query_status.pop(session_id, None)

    if status.get("error"):
        rec_html = (
            '<div class="pane-label">Recommendations</div>'
            f'<p style="color:var(--score-red);font-size:14px;">{status["error"]}</p>'
        )
        chat_html = ""
        return HTMLResponse(_query_done_fragment(rec_html, chat_html))

    return HTMLResponse(_query_done_fragment(status["rec_html"], status["chat_html"]))
```

- [ ] **Step 3: Run existing tests — expect some failures**

```bash
source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/web/ -q
```

Expected: `test_advisor_query_returns_rec_cards`, `test_advisor_query_appends_chat_turn`, `test_advisor_query_accumulates_context`, `test_advisor_query_handles_recommend_none` will fail — POST now returns a spinner, not rec cards. This is expected. Proceed.

- [ ] **Step 4: Commit**

```bash
git add src/rcars/web/routes/advisor.py
git commit -m "advisor: Refactor POST /advisor/query to async fire-and-forget; add GET /advisor/query/status"
```

---

### Task 4: Update tests to match the new async pattern

**Files:**
- Modify: `tests/web/test_advisor.py`

Update the four broken tests and add three new ones for the status endpoint.

- [ ] **Step 1: Replace `test_advisor_query_returns_rec_cards`**

The POST now returns a spinner. The rec cards arrive via the status endpoint after the thread completes. We run the thread inline using `threading.Thread` side-effect via `patch`.

Replace the existing test:

```python
def test_advisor_query_returns_spinner_then_rec_cards(client):
    """POST returns spinner immediately; status endpoint returns rec cards when done."""
    from rcars.web.routes.advisor import _query_status

    with patch("rcars.web.routes.advisor.recommend", return_value=MOCK_RECOMMEND_RESULT):
        response = client.post("/advisor/query", data={
            "session_id": "async-test-1",
            "message": "OpenShift labs for developers",
        })
    assert response.status_code == 200
    assert "rec-pane" in response.text
    assert "every 2s" in response.text  # spinner has polling trigger
    assert "OpenShift Lightspeed Workshop" not in response.text  # not yet

    # Wait for background thread to finish (TestClient is sync, thread runs concurrently)
    import time
    for _ in range(20):
        if "async-test-1" in _query_status and not _query_status["async-test-1"]["running"]:
            break
        time.sleep(0.1)

    status_resp = client.get("/advisor/query/status?session_id=async-test-1")
    assert status_resp.status_code == 200
    assert "OpenShift Lightspeed Workshop" in status_resp.text
    assert "92" in status_resp.text
    assert "every 2s" not in status_resp.text  # done, no more polling
    assert "advisor-result-ready" in status_resp.text  # sentinel present
```

- [ ] **Step 2: Replace `test_advisor_query_appends_chat_turn`**

```python
def test_advisor_query_appends_chat_turn(client):
    """Status endpoint done response includes OOB chat-pane swap."""
    from rcars.web.routes.advisor import _query_status
    import time

    with patch("rcars.web.routes.advisor.recommend", return_value=MOCK_RECOMMEND_RESULT):
        client.post("/advisor/query", data={
            "session_id": "chat-turn-test",
            "message": "Show me OpenShift labs",
        })

    for _ in range(20):
        if "chat-turn-test" in _query_status and not _query_status["chat-turn-test"]["running"]:
            break
        time.sleep(0.1)

    status_resp = client.get("/advisor/query/status?session_id=chat-turn-test")
    assert status_resp.status_code == 200
    assert "chat-pane" in status_resp.text
    assert "hx-swap-oob" in status_resp.text
```

- [ ] **Step 3: Update `test_advisor_query_accumulates_context`**

The accumulation happens before spawning the thread (user messages added to `_sessions` in the POST handler), so the `calls` capture still works. We just need to poll to completion:

```python
def test_advisor_query_accumulates_context(client):
    import time
    from rcars.web.routes.advisor import _query_status

    calls = []
    def capture_recommend(query, **kwargs):
        calls.append(query)
        return MOCK_RECOMMEND_RESULT

    with patch("rcars.web.routes.advisor.recommend", side_effect=capture_recommend):
        client.post("/advisor/query", data={"session_id": "acc-test2", "message": "OpenShift labs"})
        for _ in range(20):
            if "acc-test2" in _query_status and not _query_status["acc-test2"]["running"]:
                break
            time.sleep(0.1)
        client.get("/advisor/query/status?session_id=acc-test2")  # consume done state

        client.post("/advisor/query", data={"session_id": "acc-test2", "message": "shorter ones only"})
        for _ in range(20):
            if "acc-test2" in _query_status and not _query_status["acc-test2"]["running"]:
                break
            time.sleep(0.1)

    assert len(calls) == 2
    assert "OpenShift labs" in calls[1]
    assert "shorter ones only" in calls[1]
```

- [ ] **Step 4: Update `test_advisor_query_handles_recommend_none`**

```python
def test_advisor_query_handles_recommend_none(client):
    import time
    from rcars.web.routes.advisor import _query_status

    with patch("rcars.web.routes.advisor.recommend", return_value=None):
        client.post("/advisor/query", data={
            "session_id": "fail-test2",
            "message": "something",
        })

    for _ in range(20):
        if "fail-test2" in _query_status and not _query_status["fail-test2"]["running"]:
            break
        time.sleep(0.1)

    status_resp = client.get("/advisor/query/status?session_id=fail-test2")
    assert status_resp.status_code == 200
    # recommend() returning None → 0 recs, overall_assessment default text
    assert "Found 0 matches" in status_resp.text or "No strong matches" in status_resp.text
```

- [ ] **Step 5: Add `test_advisor_query_status_while_running`**

```python
def test_advisor_query_status_while_running(client):
    """Status endpoint returns spinner while thread is running."""
    from rcars.web.routes.advisor import _query_status
    _query_status["running-session"] = {"running": True, "rec_html": None, "chat_html": None, "error": None}

    resp = client.get("/advisor/query/status?session_id=running-session")
    assert resp.status_code == 200
    assert "every 2s" in resp.text
    assert "rec-pane" in resp.text

    del _query_status["running-session"]  # cleanup
```

- [ ] **Step 6: Add `test_advisor_query_status_when_done`**

```python
def test_advisor_query_status_when_done(client):
    """Status endpoint returns done fragment and clears state."""
    from rcars.web.routes.advisor import _query_status
    _query_status["done-session"] = {
        "running": False,
        "rec_html": '<div class="pane-label">Recommendations</div><p>Result content</p>',
        "chat_html": '<div hx-swap-oob="beforeend:#chat-pane"><div class="chat-turn-assistant">Good match.</div></div>',
        "error": None,
    }

    resp = client.get("/advisor/query/status?session_id=done-session")
    assert resp.status_code == 200
    assert "Result content" in resp.text
    assert "advisor-result-ready" in resp.text  # sentinel present
    assert "chat-pane" in resp.text
    assert "every 2s" not in resp.text  # no polling
    assert "done-session" not in _query_status  # state cleared
```

- [ ] **Step 7: Add `test_advisor_query_status_unknown_session`**

```python
def test_advisor_query_status_unknown_session(client):
    """Unknown session_id returns spinner gracefully (no crash)."""
    resp = client.get("/advisor/query/status?session_id=does-not-exist")
    assert resp.status_code == 200
    assert "rec-pane" in resp.text
```

- [ ] **Step 8: Run all tests — must pass**

```bash
source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/web/ -q
```

Expected: all tests pass. If `test_advisor_query_handles_recommend_none` fails on the assertion text, check what `overall_assessment` the route returns for `None` result and adjust the assertion to match.

- [ ] **Step 9: Commit**

```bash
git add tests/web/test_advisor.py
git commit -m "tests: Update advisor query tests for async fire-and-forget pattern"
```

---

### Task 5: Update `advisor.html` JS for polling swap

**Files:**
- Modify: `src/rcars/web/templates/advisor.html`

Two targeted JS changes. The visible UI does not change.

- [ ] **Step 1: Change `htmx.ajax` swap mode to `outerHTML`**

In `advisor.html`, find the `htmx.ajax` call (around line 108–115):

```javascript
      htmx.ajax('POST', '/advisor/query', {
        target: '#rec-pane',
        swap: 'innerHTML',
        values: {
          session_id: sessionId,
          message: sentMsg
        }
      });
```

Change `swap: 'innerHTML'` to `swap: 'outerHTML'`:

```javascript
      htmx.ajax('POST', '/advisor/query', {
        target: '#rec-pane',
        swap: 'outerHTML',
        values: {
          session_id: sessionId,
          message: sentMsg
        }
      });
```

**Why:** The POST now returns a `<div id="rec-pane" hx-trigger="every 2s" ...>` that must *replace* the existing `#rec-pane` element entirely so HTMX picks up the polling attributes. With `innerHTML`, the spinner would be placed *inside* `#rec-pane` and HTMX would not poll it correctly.

- [ ] **Step 2: Update `htmx:afterSwap` listener to use sentinel**

Find the existing `htmx:afterSwap` listener (lines 98–107):

```javascript
      document.body.addEventListener('htmx:afterSwap', function restoreBtn(e) {
        if (e.detail.target && e.detail.target.id === 'rec-pane') {
          document.body.removeEventListener('htmx:afterSwap', restoreBtn);
          var el = document.getElementById('thinking-indicator');
          if (el) el.remove();
          sendBtn.disabled = false;
          sendBtn.textContent = 'Send';
          sendBtn.classList.remove('sending');
        }
      });
```

Replace with:

```javascript
      document.body.addEventListener('htmx:afterSwap', function restoreBtn(e) {
        if (document.getElementById('advisor-result-ready')) {
          document.body.removeEventListener('htmx:afterSwap', restoreBtn);
          var el = document.getElementById('thinking-indicator');
          if (el) el.remove();
          sendBtn.disabled = false;
          sendBtn.textContent = 'Send';
          sendBtn.classList.remove('sending');
          chatPane.scrollTop = chatPane.scrollHeight;
        }
      });
```

**Why:** With polling, `htmx:afterSwap` fires every 2 seconds as the spinner replaces itself. The old check (`target.id === 'rec-pane'`) would restore the button on the first poll, not completion. The sentinel element `#advisor-result-ready` only exists in the done fragment, so the check is reliable.

- [ ] **Step 3: Run all tests**

```bash
source /Users/nstephan/.virtualenvs/content-advisor/bin/activate && python -m pytest tests/web/ -q
```

Expected: all pass (the JS changes are not tested by the server-side tests, but the tests must still pass to confirm no regressions).

- [ ] **Step 4: Commit**

```bash
git add src/rcars/web/templates/advisor.html
git commit -m "advisor: Update JS swap mode and afterSwap sentinel for polling pattern"
```

---

### Task 6: Manual smoke test

**Files:** None — verification only.

- [ ] **Step 1: Start the dev server**

```bash
source /Users/nstephan/.virtualenvs/content-advisor/bin/activate
cd /Users/nstephan/devel/working/rcars-advisory
uvicorn rcars.web.app:app --reload
```

- [ ] **Step 2: Open the advisor page**

Navigate to `http://localhost:8000/advisor` in a browser.

- [ ] **Step 3: Send a query**

Type a message and click Send. Verify:
- User bubble appears immediately in chat pane
- "..." thinking indicator appears in chat pane
- Rec pane shows loading spinner
- Send button is disabled and shows "Thinking..."
- After 5–60 seconds, rec pane replaces with results
- Chat turn appears in chat pane
- Send button re-enables

- [ ] **Step 4: Send a follow-up**

Send a second message in the same session. Verify the spinner re-appears and a new result arrives.

- [ ] **Step 5: Note any issues**

If the spinner never resolves, check server logs (`uvicorn` stdout) for errors from the background thread. The log lines from `_run_advisor_query` (`advisor bg: ...`) confirm the thread is running.

---

### Task 7: Update documentation

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-async-advisor-query-design.md` (mark implemented)
- Check: any other docs referencing `/advisor/query` behaviour

- [ ] **Step 1: Mark the spec as implemented**

Open `docs/superpowers/specs/2026-04-11-async-advisor-query-design.md`. Change the Status line:

```markdown
**Status:** Implemented
```

- [ ] **Step 2: Check for other docs referencing the advisor endpoint**

```bash
grep -r "advisor/query\|advisor_query\|recommend()" docs/ --include="*.md" -l
```

Review any hits and update if they describe the old synchronous behaviour.

- [ ] **Step 3: Commit**

```bash
git add docs/
git commit -m "docs: Mark async advisor query spec as implemented"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Module-level `_query_status` dict | Task 1 |
| `POST /advisor/query` → spinner immediately | Task 3 |
| Background thread calls `recommend()` | Task 1 (`_run_advisor_query`) |
| `GET /advisor/query/status` returns spinner or done | Task 3 |
| Done fragment: rec_html + sentinel + OOB chat | Task 2 (`_query_done_fragment`) |
| Error cases return done-shaped fragment immediately | Task 2 (`_query_error_fragment`) |
| JS: `outerHTML` swap | Task 5 |
| JS: sentinel-based `htmx:afterSwap` handler | Task 5 |
| Tests: POST returns spinner | Task 4 |
| Tests: status running → spinner | Task 4 |
| Tests: status done → rec cards + chat OOB | Task 4 |
| Tests: unknown session → graceful | Task 4 |
| Docs updated | Task 7 |
| Scale caveat documented | In spec |

**Placeholder scan:** None found — all steps contain actual code.

**Type consistency:** `_run_advisor_query` stores `{"running": False, "rec_html": str, "chat_html": str, "error": None}`. `advisor_query_status` reads `status["running"]`, `status["error"]`, `status["rec_html"]`, `status["chat_html"]` — consistent. `_query_done_fragment(rec_html, chat_html)` called with both string args in all three callsites — consistent.
