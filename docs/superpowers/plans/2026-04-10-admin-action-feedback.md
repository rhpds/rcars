# Admin Action Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add live feedback to Sync Catalog, Analyze Showroom Content (admin page), and per-item Re-analyze (curate page) using fire-and-forget background threads + HTMX polling.

**Architecture:** Each button click hits a POST endpoint that spawns a background thread and immediately returns an HTMX-pollable HTML fragment. A companion GET status endpoint is polled every 2s; the fragment it returns either continues polling (running) or stops and displays a result (done). On completion, admin operations also OOB-swap the Catalog Status table with fresh counts.

**Tech Stack:** FastAPI, HTMX, Jinja2, Python threading, subprocess.Popen (for Analyze), starlette TestClient for tests.

---

## File Map

| File | Changes |
|------|---------|
| `src/rcars/web/routes/admin.py` | New `_refresh_status` dict; refactor `_run_refresh` + `trigger_refresh`; add `GET /admin/refresh/status`; refactor `_run_rescan` to use Popen; refactor `trigger_rescan`; add `GET /admin/rescan/status`; add `_status_table_oob()` helper |
| `src/rcars/web/routes/curate.py` | New `_item_analyze_status` dict; add `POST /curate/analyze`; add `GET /curate/analyze/status`; add `_run_item_analyze` background function |
| `src/rcars/web/templates/admin.html` | Rename sections/buttons; add `id="catalog-status-table"`; wrap Sync and Analyze sections in `id="refresh-section"` and `id="rescan-section"` divs |
| `src/rcars/web/templates/curate.html` | Add per-item `id="analyze-section-{ci_name_safe}"` wrapper with Re-analyze button |
| `tests/web/test_admin.py` | Update existing tests; add status endpoint tests |
| `tests/web/test_curate.py` | Add per-item analyze endpoint tests |

---

## Task 1: Rename admin labels and add structural IDs

**Files:**
- Modify: `src/rcars/web/templates/admin.html`
- Test: `tests/web/test_admin.py`

- [ ] **Step 1: Update admin.html — rename sections and wrap buttons**

Replace the content of `src/rcars/web/templates/admin.html` with:

```html
{% extends "base.html" %}
{% block content %}
<div class="admin-layout">
  <div style="font-size:16px;font-weight:600;margin-bottom:20px;">Administration</div>

  <div class="admin-section">
    <h3>Catalog Status</h3>
    <table id="catalog-status-table" class="status-table">
      <tr><th>Metric</th><th>Count</th></tr>
      <tr><td>Total catalog items</td><td>{{ status.total }}</td></tr>
      <tr><td>Production items</td><td>{{ status.prod }}</td></tr>
      <tr><td>With Showroom content</td><td>{{ status.with_showroom }}</td></tr>
      <tr><td>Analyzed</td><td>{{ status.analyzed }}</td></tr>
      <tr><td>Stale (needs rescan)</td><td style="color:{% if status.stale > 0 %}var(--score-amber){% else %}var(--score-green){% endif %};">{{ status.stale }}</td></tr>
    </table>
  </div>

  <div class="admin-section">
    <h3>Catalog Sync</h3>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">
      Pull latest catalog metadata from Babylon CRDs into the database. Fast (~30 seconds).
    </p>
    <div id="refresh-section">
      <button class="btn-action"
              hx-post="/admin/refresh"
              hx-target="#refresh-section"
              hx-swap="outerHTML">
        Sync Catalog
      </button>
    </div>
  </div>

  <div class="admin-section">
    <h3>Showroom Analysis</h3>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">
      Clone and re-analyze Showroom repos via Sonnet. Runs in background (~30–60 min).
    </p>
    <div id="rescan-section">
      <button class="btn-action"
              hx-post="/admin/rescan"
              hx-target="#rescan-section"
              hx-swap="outerHTML">
        Analyze Showroom Content
      </button>
    </div>
  </div>

  <div class="admin-section">
    <h3>Curator Access</h3>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">
      Set via <code>RCARS_CURATOR_EMAILS</code> environment variable (comma-separated).
    </p>
    {% if curator_emails %}
    <ul style="font-size:12px;color:var(--text-primary);list-style:none;padding:0;">
      {% for email in curator_emails %}
      <li style="padding:3px 0;color:var(--accent-blue);">{{ email }}</li>
      {% endfor %}
    </ul>
    {% else %}
    <p style="font-size:12px;color:var(--score-red);">No curator emails configured.</p>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Update tests to match new labels**

In `tests/web/test_admin.py`, update `test_admin_shows_scan_status` and add a label check:

```python
def test_admin_shows_scan_status(admin_client):
    client, _ = admin_client
    response = client.get("/admin")
    assert response.status_code == 200
    assert "342" in response.text


def test_admin_shows_new_labels(admin_client):
    client, _ = admin_client
    response = client.get("/admin")
    assert "Catalog Sync" in response.text
    assert "Sync Catalog" in response.text
    assert "Showroom Analysis" in response.text
    assert "Analyze Showroom Content" in response.text
    assert "catalog-status-table" in response.text
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/nstephan/devel/working/rcars-advisory
source ~/.virtualenvs/content-advisor/bin/activate
pytest tests/web/test_admin.py -v
```

Expected: all tests pass (the renamed labels match; `test_admin_refresh_triggers` and `test_admin_rescan_triggers_background_job` still pass since the routes haven't changed yet).

- [ ] **Step 4: Commit**

```bash
git add src/rcars/web/templates/admin.html tests/web/test_admin.py
git commit -m "admin: Rename Refresh→Sync, Rescan→Analyze; add structural IDs for HTMX feedback"
```

---

## Task 2: Sync Catalog — fire-and-forget + status endpoint

**Files:**
- Modify: `src/rcars/web/routes/admin.py`
- Test: `tests/web/test_admin.py`

- [ ] **Step 1: Write failing tests for new Sync Catalog behavior**

Add to `tests/web/test_admin.py`:

```python
def test_sync_catalog_returns_running_fragment(admin_client):
    """POST /admin/refresh returns immediately with HTMX polling markup."""
    client, mock_db = admin_client
    with patch("rcars.web.routes.admin.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        response = client.post("/admin/refresh")
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "/admin/refresh/status" in response.text
    assert "Syncing" in response.text


def test_sync_catalog_status_idle(admin_client):
    """GET /admin/refresh/status while idle returns empty div."""
    client, mock_db = admin_client
    import rcars.web.routes.admin as admin_mod
    admin_mod._refresh_status = {"running": False, "result": None, "color": None}
    response = client.get("/admin/refresh/status")
    assert response.status_code == 200
    assert "refresh-section" in response.text
    assert "every 2s" not in response.text


def test_sync_catalog_status_running(admin_client):
    """GET /admin/refresh/status while running returns polling fragment."""
    client, mock_db = admin_client
    import rcars.web.routes.admin as admin_mod
    admin_mod._refresh_status = {"running": True, "result": None, "color": None}
    response = client.get("/admin/refresh/status")
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "Syncing" in response.text
    admin_mod._refresh_status = {"running": False, "result": None, "color": None}


def test_sync_catalog_status_done(admin_client):
    """GET /admin/refresh/status when done returns result + OOB table."""
    client, mock_db = admin_client
    mock_db.get_status_summary.return_value = {
        "total": 350, "prod": 250, "with_showroom": 130, "analyzed": 125, "stale": 0,
    }
    import rcars.web.routes.admin as admin_mod
    admin_mod._refresh_status = {
        "running": False,
        "result": "Catalog sync complete.",
        "color": "var(--score-green)",
    }
    response = client.get("/admin/refresh/status")
    assert response.status_code == 200
    assert "Catalog sync complete." in response.text
    assert "catalog-status-table" in response.text
    assert "hx-swap-oob" in response.text
    assert "350" in response.text
    # State should be reset after serving
    assert admin_mod._refresh_status["result"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/web/test_admin.py::test_sync_catalog_returns_running_fragment tests/web/test_admin.py::test_sync_catalog_status_idle tests/web/test_admin.py::test_sync_catalog_status_running tests/web/test_admin.py::test_sync_catalog_status_done -v
```

Expected: all FAIL (endpoints don't exist yet / behavior differs).

- [ ] **Step 3: Implement the new Sync Catalog logic in admin.py**

Replace the `_refresh_status`, `_run_refresh`, and `trigger_refresh` sections, and add `_status_table_oob` helper and `refresh_status` endpoint. The full updated top portion of `admin.py` (keep everything else unchanged):

```python
import subprocess
import threading
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import require_admin
from rcars.db import Database
from rcars.config import Settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_rescan_status: dict = {"running": False, "lines": [], "exit_ok": None}
_refresh_status: dict = {"running": False, "result": None, "color": None}
_item_analyze_status: dict = {}


def _get_db_dependency() -> Database | None:
    from rcars.web.app import get_db
    return get_db()


def _status_table_oob(db: Database) -> str:
    """Render the catalog status table as an HTMX OOB swap fragment."""
    s = db.get_status_summary()
    stale_color = "var(--score-amber)" if s["stale"] > 0 else "var(--score-green)"
    return f"""<table id="catalog-status-table" class="status-table" hx-swap-oob="true">
  <tr><th>Metric</th><th>Count</th></tr>
  <tr><td>Total catalog items</td><td>{s["total"]}</td></tr>
  <tr><td>Production items</td><td>{s["prod"]}</td></tr>
  <tr><td>With Showroom content</td><td>{s["with_showroom"]}</td></tr>
  <tr><td>Analyzed</td><td>{s["analyzed"]}</td></tr>
  <tr><td>Stale (needs rescan)</td><td style="color:{stale_color};">{s["stale"]}</td></tr>
</table>"""


def _refresh_section_running() -> str:
    return """<div id="refresh-section"
     hx-get="/admin/refresh/status"
     hx-trigger="every 2s"
     hx-target="this"
     hx-swap="outerHTML">
  <button class="btn-action" disabled style="opacity:0.5;cursor:not-allowed;">Sync Catalog</button>
  <span style="font-size:12px;color:var(--score-amber);margin-left:10px;">&#8635; Syncing catalog\u2026</span>
</div>"""


def _refresh_section_idle(msg: str = "", color: str = "") -> str:
    status_span = f'<span style="font-size:12px;color:{color};margin-left:10px;">{msg}</span>' if msg else ""
    return f"""<div id="refresh-section">
  <button class="btn-action"
          hx-post="/admin/refresh"
          hx-target="#refresh-section"
          hx-swap="outerHTML">Sync Catalog</button>
  {status_span}
</div>"""


def _run_refresh():
    global _refresh_status
    try:
        result = subprocess.run(
            ["rcars", "refresh"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            _refresh_status["result"] = "Catalog sync complete."
            _refresh_status["color"] = "var(--score-green)"
        else:
            _refresh_status["result"] = f"Sync failed: {result.stderr[:200]}"
            _refresh_status["color"] = "var(--score-red)"
    except Exception as e:
        _refresh_status["result"] = f"Sync error: {str(e)[:200]}"
        _refresh_status["color"] = "var(--score-red)"
    finally:
        _refresh_status["running"] = False


@router.post("/admin/refresh", response_class=HTMLResponse)
async def trigger_refresh(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if _refresh_status["running"]:
        return HTMLResponse(_refresh_section_running())
    _refresh_status["running"] = True
    _refresh_status["result"] = None
    _refresh_status["color"] = None
    t = threading.Thread(target=_run_refresh, daemon=True)
    t.start()
    return HTMLResponse(_refresh_section_running())


@router.get("/admin/refresh/status", response_class=HTMLResponse)
async def refresh_status(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if _refresh_status["running"]:
        return HTMLResponse(_refresh_section_running())
    if _refresh_status["result"] is not None:
        msg = _refresh_status["result"]
        color = _refresh_status["color"]
        _refresh_status["result"] = None
        _refresh_status["color"] = None
        return HTMLResponse(_refresh_section_idle(msg, color) + _status_table_oob(db))
    return HTMLResponse(_refresh_section_idle())
```

- [ ] **Step 4: Run the new tests**

```bash
pytest tests/web/test_admin.py -v
```

Expected: all pass, including the four new ones. `test_admin_refresh_triggers` should also still pass (it checks `threading.Thread` is called, which still happens).

- [ ] **Step 5: Commit**

```bash
git add src/rcars/web/routes/admin.py tests/web/test_admin.py
git commit -m "admin: Sync Catalog fire-and-forget with HTMX polling status + OOB table update"
```

---

## Task 3: Analyze Showroom Content — Popen line streaming + status endpoint

**Files:**
- Modify: `src/rcars/web/routes/admin.py`
- Test: `tests/web/test_admin.py`

- [ ] **Step 1: Write failing tests for new Analyze behavior**

Add to `tests/web/test_admin.py`:

```python
def test_analyze_returns_running_fragment(admin_client):
    """POST /admin/rescan returns immediately with HTMX polling markup."""
    client, mock_db = admin_client
    with patch("rcars.web.routes.admin.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        response = client.post("/admin/rescan")
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "/admin/rescan/status" in response.text
    assert "Analysis" in response.text


def test_analyze_status_idle(admin_client):
    """GET /admin/rescan/status while idle returns idle section."""
    client, mock_db = admin_client
    import rcars.web.routes.admin as admin_mod
    admin_mod._rescan_status = {"running": False, "lines": [], "exit_ok": None}
    response = client.get("/admin/rescan/status")
    assert response.status_code == 200
    assert "every 2s" not in response.text
    assert "rescan-section" in response.text


def test_analyze_status_running_shows_lines(admin_client):
    """GET /admin/rescan/status while running shows log lines."""
    client, mock_db = admin_client
    import rcars.web.routes.admin as admin_mod
    admin_mod._rescan_status = {
        "running": True,
        "lines": ["Cloning lb1024...", "Analyzing content..."],
        "exit_ok": None,
    }
    response = client.get("/admin/rescan/status")
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "Cloning lb1024" in response.text
    admin_mod._rescan_status = {"running": False, "lines": [], "exit_ok": None}


def test_analyze_status_done_success(admin_client):
    """GET /admin/rescan/status when done shows result + OOB table."""
    client, mock_db = admin_client
    mock_db.get_status_summary.return_value = {
        "total": 342, "prod": 248, "with_showroom": 126, "analyzed": 126, "stale": 0,
    }
    import rcars.web.routes.admin as admin_mod
    admin_mod._rescan_status = {
        "running": False,
        "lines": ["Done."],
        "exit_ok": True,
    }
    response = client.get("/admin/rescan/status")
    assert response.status_code == 200
    assert "Analysis complete" in response.text
    assert "catalog-status-table" in response.text
    assert "hx-swap-oob" in response.text
    assert admin_mod._rescan_status["exit_ok"] is None


def test_analyze_status_done_failure(admin_client):
    """GET /admin/rescan/status when done with failure shows error."""
    client, mock_db = admin_client
    mock_db.get_status_summary.return_value = {
        "total": 342, "prod": 248, "with_showroom": 126, "analyzed": 120, "stale": 6,
    }
    import rcars.web.routes.admin as admin_mod
    admin_mod._rescan_status = {
        "running": False,
        "lines": ["Error: something failed"],
        "exit_ok": False,
    }
    response = client.get("/admin/rescan/status")
    assert response.status_code == 200
    assert "failed" in response.text.lower()
    assert admin_mod._rescan_status["exit_ok"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/web/test_admin.py::test_analyze_returns_running_fragment tests/web/test_admin.py::test_analyze_status_idle tests/web/test_admin.py::test_analyze_status_running_shows_lines tests/web/test_admin.py::test_analyze_status_done_success tests/web/test_admin.py::test_analyze_status_done_failure -v
```

Expected: all FAIL.

- [ ] **Step 3: Implement Analyze Showroom Content logic in admin.py**

Replace the `_run_rescan`, `trigger_rescan` section in `admin.py` and add the new status endpoint and rendering helpers. Add these functions after `_refresh_section_idle`:

```python
def _rescan_section_running(lines: list[str]) -> str:
    recent = lines[-20:] if lines else []
    log_html = "\n".join(f'<div>{line}</div>' for line in recent) if recent else ""
    log_block = f"""<div style="margin-top:10px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:4px;padding:8px 10px;font-size:10px;font-family:monospace;color:var(--text-muted);white-space:pre-wrap;max-height:200px;overflow-y:auto;">{log_html}</div>""" if log_html else ""
    return f"""<div id="rescan-section"
     hx-get="/admin/rescan/status"
     hx-trigger="every 2s"
     hx-target="this"
     hx-swap="outerHTML">
  <button class="btn-action" disabled style="opacity:0.5;cursor:not-allowed;">Analyze Showroom Content</button>
  <span style="font-size:12px;color:var(--score-amber);margin-left:10px;">&#8635; Analysis running\u2026</span>
  {log_block}
</div>"""


def _rescan_section_idle(msg: str = "", color: str = "", lines: list[str] | None = None) -> str:
    status_span = f'<span style="font-size:12px;color:{color};margin-left:10px;">{msg}</span>' if msg else ""
    log_html = ""
    if lines:
        recent = lines[-20:]
        log_content = "\n".join(f'<div>{line}</div>' for line in recent)
        log_html = f"""<div style="margin-top:10px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:4px;padding:8px 10px;font-size:10px;font-family:monospace;color:var(--text-muted);white-space:pre-wrap;max-height:200px;overflow-y:auto;">{log_content}</div>"""
    return f"""<div id="rescan-section">
  <button class="btn-action"
          hx-post="/admin/rescan"
          hx-target="#rescan-section"
          hx-swap="outerHTML">Analyze Showroom Content</button>
  {status_span}
  {log_html}
</div>"""


def _run_rescan():
    global _rescan_status
    _rescan_status["lines"] = ["Starting analysis\u2026"]
    _rescan_status["exit_ok"] = None
    try:
        proc = subprocess.Popen(
            ["rcars", "scan"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            line = line.rstrip("\n")
            if line:
                _rescan_status["lines"].append(line)
                if len(_rescan_status["lines"]) > 500:
                    _rescan_status["lines"] = _rescan_status["lines"][-500:]
        proc.wait(timeout=3600)
        _rescan_status["exit_ok"] = proc.returncode == 0
    except Exception as e:
        _rescan_status["lines"].append(f"Error: {e}")
        _rescan_status["exit_ok"] = False
    finally:
        _rescan_status["running"] = False


@router.post("/admin/rescan", response_class=HTMLResponse)
async def trigger_rescan(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if _rescan_status["running"]:
        return HTMLResponse(_rescan_section_running(_rescan_status["lines"]))
    _rescan_status["running"] = True
    _rescan_status["lines"] = []
    _rescan_status["exit_ok"] = None
    t = threading.Thread(target=_run_rescan, daemon=True)
    t.start()
    return HTMLResponse(_rescan_section_running([]))


@router.get("/admin/rescan/status", response_class=HTMLResponse)
async def rescan_status(
    user: str = Depends(require_admin),
    db: Database = Depends(_get_db_dependency),
):
    if _rescan_status["running"]:
        return HTMLResponse(_rescan_section_running(_rescan_status["lines"]))
    if _rescan_status["exit_ok"] is not None:
        exit_ok = _rescan_status["exit_ok"]
        lines = list(_rescan_status["lines"])
        _rescan_status["exit_ok"] = None
        msg = "Analysis complete." if exit_ok else "Analysis failed."
        color = "var(--score-green)" if exit_ok else "var(--score-red)"
        return HTMLResponse(_rescan_section_idle(msg, color, lines) + _status_table_oob(db))
    return HTMLResponse(_rescan_section_idle())
```

Also remove the old `_get_db_dependency`, `_run_rescan(settings)` (the one that took settings), and `trigger_rescan` definitions — they are replaced by the code above.

- [ ] **Step 4: Run all admin tests**

```bash
pytest tests/web/test_admin.py -v
```

Expected: all pass. `test_admin_rescan_triggers_background_job` checks that `threading.Thread` is called — this still holds.

- [ ] **Step 5: Commit**

```bash
git add src/rcars/web/routes/admin.py tests/web/test_admin.py
git commit -m "admin: Analyze Showroom Content Popen streaming + HTMX polling status endpoint"
```

---

## Task 4: Per-item Re-analyze on curate page

**Files:**
- Modify: `src/rcars/web/routes/curate.py`
- Modify: `src/rcars/web/templates/curate.html`
- Test: `tests/web/test_curate.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/web/test_curate.py`:

```python
def test_curate_page_shows_reanalyze_button(curator_client):
    """Each curate item card includes a Re-analyze button."""
    client, _ = curator_client
    response = client.get("/curate")
    assert response.status_code == 200
    assert "Re-analyze" in response.text
    assert "/curate/analyze" in response.text


def test_curate_analyze_returns_running_fragment(curator_client):
    """POST /curate/analyze returns running fragment with polling."""
    client, mock_db = curator_client
    mock_db.list_catalog_items.return_value = [
        {
            "ci_name": "test.lab.prod",
            "display_name": "Test Lab",
            "is_prod": True,
            "showroom_url": "https://github.com/rhpds/test-lab",
            "showroom_ref": None,
            "category": "OpenShift",
            "product": "OCP",
        }
    ]
    with patch("rcars.web.routes.curate.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        response = client.post("/curate/analyze", data={"ci_name": "test.lab.prod"})
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "/curate/analyze/status" in response.text


def test_curate_analyze_status_idle(curator_client):
    """GET /curate/analyze/status for unknown ci_name returns idle div."""
    client, _ = curator_client
    import rcars.web.routes.curate as curate_mod
    curate_mod._item_analyze_status = {}
    response = client.get("/curate/analyze/status?ci_name=test.lab.prod")
    assert response.status_code == 200
    assert "every 2s" not in response.text


def test_curate_analyze_status_running(curator_client):
    """GET /curate/analyze/status while running returns polling fragment."""
    client, _ = curator_client
    import rcars.web.routes.curate as curate_mod
    curate_mod._item_analyze_status["test.lab.prod"] = {
        "running": True, "result": None, "color": None,
    }
    response = client.get("/curate/analyze/status?ci_name=test.lab.prod")
    assert response.status_code == 200
    assert "every 2s" in response.text
    assert "Analyzing" in response.text
    curate_mod._item_analyze_status = {}


def test_curate_analyze_status_done(curator_client):
    """GET /curate/analyze/status when done shows result and resets state."""
    client, _ = curator_client
    import rcars.web.routes.curate as curate_mod
    curate_mod._item_analyze_status["test.lab.prod"] = {
        "running": False,
        "result": "Analysis complete.",
        "color": "var(--score-green)",
    }
    response = client.get("/curate/analyze/status?ci_name=test.lab.prod")
    assert response.status_code == 200
    assert "Analysis complete." in response.text
    assert "every 2s" not in response.text
    assert "test.lab.prod" not in curate_mod._item_analyze_status
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/web/test_curate.py::test_curate_page_shows_reanalyze_button tests/web/test_curate.py::test_curate_analyze_returns_running_fragment tests/web/test_curate.py::test_curate_analyze_status_idle tests/web/test_curate.py::test_curate_analyze_status_running tests/web/test_curate.py::test_curate_analyze_status_done -v
```

Expected: all FAIL.

- [ ] **Step 3: Add imports and state to curate.py**

At the top of `src/rcars/web/routes/curate.py`, add `threading` to imports and add the global state dict after the existing imports:

```python
import threading
from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import require_curator, get_current_user
from rcars.db import Database
from rcars.config import Settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

PAGE_SIZE = 25

_item_analyze_status: dict = {}
# key: ci_name → {"running": bool, "result": str | None, "color": str | None}
```

- [ ] **Step 4: Add `_ci_safe` helper and HTML rendering helpers to curate.py**

Add after the global state:

```python
def _ci_safe(ci_name: str) -> str:
    """Convert ci_name to a safe HTML id fragment."""
    return ci_name.replace(".", "-").replace("/", "-")


def _analyze_section_running(ci_name: str) -> str:
    ci_safe = _ci_safe(ci_name)
    return f"""<div id="analyze-section-{ci_safe}"
     hx-get="/curate/analyze/status?ci_name={ci_name}"
     hx-trigger="every 2s"
     hx-target="this"
     hx-swap="outerHTML"
     style="display:flex;flex-direction:column;gap:4px;">
  <button style="background:#2a1a40;color:#b794f4;border:1px solid #4a2a70;padding:5px 12px;border-radius:4px;font-size:12px;opacity:0.5;cursor:not-allowed;" disabled>Re-analyze &#8635;</button>
  <span style="font-size:11px;color:#b794f4;">&#8635; Analyzing\u2026</span>
</div>"""


def _analyze_section_idle(ci_name: str, msg: str = "", color: str = "") -> str:
    ci_safe = _ci_safe(ci_name)
    status_span = f'<span style="font-size:11px;color:{color};">{msg}</span>' if msg else ""
    return f"""<div id="analyze-section-{ci_safe}" style="display:flex;flex-direction:column;gap:4px;">
  <button style="background:#2a1a40;color:#b794f4;border:1px solid #4a2a70;padding:5px 12px;border-radius:4px;font-size:12px;cursor:pointer;"
          hx-post="/curate/analyze"
          hx-vals='{{"ci_name": "{ci_name}"}}'
          hx-target="#analyze-section-{ci_safe}"
          hx-swap="outerHTML">Re-analyze &#8635;</button>
  {status_span}
</div>"""
```

- [ ] **Step 5: Add `_run_item_analyze` background function to curate.py**

Add after `_analyze_section_idle`:

```python
def _run_item_analyze(ci_name: str, item: dict, db: Database, settings: Settings):
    global _item_analyze_status
    try:
        from rcars.analyzer import analyze_showroom
        anthropic_client = settings.get_anthropic_client()
        if not anthropic_client:
            _item_analyze_status[ci_name] = {
                "running": False,
                "result": "No Anthropic credentials configured.",
                "color": "var(--score-red)",
            }
            return
        result = analyze_showroom(
            ci_name=ci_name,
            display_name=item.get("display_name", ""),
            category=item.get("category", ""),
            product=item.get("product", ""),
            showroom_url=item["showroom_url"],
            showroom_ref=item.get("showroom_ref"),
            anthropic_client=anthropic_client,
            model=settings.model,
            clone_dir=settings.clone_dir,
        )
        if result:
            analysis = result["analysis"]
            db.upsert_showroom_analysis({
                "ci_name": result["ci_name"],
                "content_type": analysis.get("content_type"),
                "summary": analysis.get("summary"),
                "products_json": analysis.get("products"),
                "audience_json": analysis.get("audience"),
                "topics_json": analysis.get("topics"),
                "modules_json": analysis.get("modules"),
                "learning_objectives_json": analysis.get("learning_objectives"),
                "difficulty": analysis.get("difficulty"),
                "estimated_duration_min": analysis.get("estimated_duration_min"),
                "event_fit_json": analysis.get("event_fit"),
                "use_cases_json": analysis.get("use_cases"),
                "last_repo_commit": result.get("last_repo_commit"),
                "last_repo_updated": result.get("last_repo_updated"),
            })
            if result.get("ci_embedding"):
                db.store_embedding(
                    ci_name=ci_name,
                    embed_type="ci_summary",
                    content_text=result.get("ci_embedding_text", ""),
                    embedding=result["ci_embedding"],
                )
            for mod_emb in result.get("module_embeddings", []):
                db.store_embedding(
                    ci_name=ci_name,
                    embed_type="module",
                    module_title=mod_emb["module_title"],
                    content_text=mod_emb["content_text"],
                    embedding=mod_emb["embedding"],
                )
            _item_analyze_status[ci_name] = {
                "running": False,
                "result": "Analysis complete.",
                "color": "var(--score-green)",
            }
        else:
            _item_analyze_status[ci_name] = {
                "running": False,
                "result": "Analysis failed.",
                "color": "var(--score-red)",
            }
    except Exception as e:
        _item_analyze_status[ci_name] = {
            "running": False,
            "result": f"Error: {str(e)[:200]}",
            "color": "var(--score-red)",
        }
```

- [ ] **Step 6: Add `POST /curate/analyze` and `GET /curate/analyze/status` endpoints to curate.py**

Add after the existing `flag_item` route:

```python
@router.post("/curate/analyze", response_class=HTMLResponse)
async def trigger_item_analyze(
    ci_name: Annotated[str, Form()],
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    status = _item_analyze_status.get(ci_name, {})
    if status.get("running"):
        return HTMLResponse(_analyze_section_running(ci_name))

    # Look up the item for its metadata
    items = [i for i in db.list_catalog_items() if i["ci_name"] == ci_name]
    if not items or not items[0].get("showroom_url"):
        return HTMLResponse(_analyze_section_idle(
            ci_name,
            msg="No Showroom URL for this item.",
            color="var(--score-red)",
        ))

    _item_analyze_status[ci_name] = {"running": True, "result": None, "color": None}
    settings = Settings()
    t = threading.Thread(
        target=_run_item_analyze,
        args=(ci_name, items[0], db, settings),
        daemon=True,
    )
    t.start()
    return HTMLResponse(_analyze_section_running(ci_name))


@router.get("/curate/analyze/status", response_class=HTMLResponse)
async def item_analyze_status(
    ci_name: str = Query(...),
    user: str = Depends(require_curator),
):
    status = _item_analyze_status.get(ci_name, {})
    if status.get("running"):
        return HTMLResponse(_analyze_section_running(ci_name))
    if status.get("result") is not None:
        msg = status["result"]
        color = status["color"]
        del _item_analyze_status[ci_name]
        return HTMLResponse(_analyze_section_idle(ci_name, msg=msg, color=color))
    return HTMLResponse(_analyze_section_idle(ci_name))
```

- [ ] **Step 7: Update curate.html — add Re-analyze button per item**

In `src/rcars/web/templates/curate.html`, replace the button row (lines 71–98) with:

```html
    <div style="display:flex;gap:6px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;">
      <button class="btn-curator secondary"
              data-ci="{{ item.ci_name }}"
              data-flagged="{{ 'true' if item.enrichment_review_needed else 'false' }}"
              onclick="var btn = this;
                       var ci = btn.dataset.ci;
                       var isFlagged = btn.dataset.flagged === 'true';
                       var needed = isFlagged ? 'false' : 'true';
                       var badge = document.getElementById('badge-' + ci.replace(/\./g, '-'));
                       var fd = new FormData();
                       fd.append('ci_name', ci);
                       fd.append('needed', needed);
                       fetch('/curate/flag', {method: 'POST', body: fd}).then(function(r) {
                         if (r.ok) {
                           if (needed === 'true') {
                             badge.style.display = 'inline-block';
                             btn.textContent = 'Clear flag';
                             btn.dataset.flagged = 'true';
                           } else {
                             badge.style.display = 'none';
                             btn.textContent = 'Flag for review';
                             btn.dataset.flagged = 'false';
                           }
                         }
                       });">
        {{ 'Clear flag' if item.enrichment_review_needed else 'Flag for review' }}
      </button>
      <div id="analyze-section-{{ item.ci_name | replace('.', '-') | replace('/', '-') }}"
           style="display:flex;flex-direction:column;gap:4px;">
        <button style="background:#2a1a40;color:#b794f4;border:1px solid #4a2a70;padding:5px 12px;border-radius:4px;font-size:12px;cursor:pointer;"
                hx-post="/curate/analyze"
                hx-vals='{"ci_name": "{{ item.ci_name }}"}'
                hx-target="#analyze-section-{{ item.ci_name | replace('.', '-') | replace('/', '-') }}"
                hx-swap="outerHTML">Re-analyze &#8635;</button>
      </div>
    </div>
```

- [ ] **Step 8: Run all curate tests**

```bash
pytest tests/web/test_curate.py -v
```

Expected: all pass, including the five new ones.

- [ ] **Step 9: Run full test suite**

```bash
pytest tests/web/ -v
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add src/rcars/web/routes/curate.py src/rcars/web/templates/curate.html tests/web/test_curate.py
git commit -m "curate: Add per-item Re-analyze button with fire-and-forget + HTMX polling feedback"
```
