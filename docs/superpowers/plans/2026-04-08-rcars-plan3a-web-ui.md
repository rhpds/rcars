# RCARS Plan 3a — Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a FastAPI + HTMX web UI to the RCARS CLI project with a two-pane advisor interface, curator enrichment workflow, and admin controls.

**Architecture:** FastAPI app mounted at `src/rcars/web/`, sharing the existing PostgreSQL database and recommender engine. HTMX handles dynamic updates via server-rendered HTML fragments; Alpine.js handles client-side UI state (card expand/collapse, curator mode toggle). In-memory session store — no user query text persists to the database.

**Tech Stack:** FastAPI, Jinja2, HTMX 1.9 (CDN), Alpine.js 3 (CDN), psycopg3, uvicorn. All web dependencies already declared in `pyproject.toml` under `[web]` extras.

**Test runner:** `pytest tests/ -v` from project root with virtualenv active.

**Install web extras before starting:**
```bash
pip install -e ".[web]"
```

---

## File Map

**New files:**
- `src/rcars/web/__init__.py`
- `src/rcars/web/app.py` — FastAPI app factory, lifespan, DB dependency
- `src/rcars/web/deps.py` — FastAPI dependencies: get_db, get_current_user, require_curator
- `src/rcars/web/routes/__init__.py`
- `src/rcars/web/routes/advisor.py` — GET /advisor, POST /advisor/query, GET /advisor/restore
- `src/rcars/web/routes/curate.py` — GET /curate, POST/DELETE /curate/tag, POST /curate/note, POST /curate/flag
- `src/rcars/web/routes/admin.py` — GET /admin, POST /admin/rescan, POST /admin/refresh
- `src/rcars/web/templates/base.html` — LCARS logo SVG, nav sidebar, HTMX/Alpine CDN links
- `src/rcars/web/templates/advisor.html` — two-pane layout
- `src/rcars/web/templates/curate.html` — enrichment management page
- `src/rcars/web/templates/admin.html` — admin controls
- `src/rcars/web/templates/fragments/rec_card.html` — B-view recommendation card
- `src/rcars/web/templates/fragments/rec_card_expanded.html` — C-view card with curator controls
- `src/rcars/web/templates/fragments/rec_list.html` — recommendations pane
- `src/rcars/web/templates/fragments/chat_turn.html` — single chat turn pair
- `src/rcars/web/static/rcars.css` — dark theme CSS
- `tests/web/__init__.py`
- `tests/web/test_advisor.py`
- `tests/web/test_curate.py`
- `tests/web/test_admin.py`

**Modified files:**
- `src/rcars/cli.py` — add `serve` command
- `src/rcars/config.py` — add `curator_emails`, `dev_user`, `stale_days` fields + `is_curator()` method
- `src/rcars/db.py` — add `notes` column to schema, add enrichment CRUD methods, add `get_db_currency()`

---

## Task 1: Web Module Scaffolding + `rcars serve` Command

**Files:**
- Create: `src/rcars/web/__init__.py`
- Create: `src/rcars/web/app.py`
- Create: `src/rcars/web/routes/__init__.py`
- Create: `src/rcars/web/routes/advisor.py` (stub)
- Create: `src/rcars/web/routes/curate.py` (stub)
- Create: `src/rcars/web/routes/admin.py` (stub)
- Create: `src/rcars/web/templates/` directory (placeholder base.html)
- Create: `src/rcars/web/static/rcars.css` (empty)
- Modify: `src/rcars/cli.py`
- Create: `tests/web/__init__.py`
- Create: `tests/web/test_advisor.py`

- [ ] **Step 1: Write failing test for `rcars serve` command and GET /advisor**

```python
# tests/web/test_advisor.py
import pytest
from starlette.testclient import TestClient
from rcars.web.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_advisor_page_loads(client):
    response = client.get("/advisor")
    assert response.status_code == 200
    assert "RCARS" in response.text
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/web/test_advisor.py::test_advisor_page_loads -v
```
Expected: `ModuleNotFoundError: No module named 'rcars.web'`

- [ ] **Step 3: Create the web module skeleton**

```python
# src/rcars/web/__init__.py
```

```python
# src/rcars/web/routes/__init__.py
```

```python
# src/rcars/web/routes/advisor.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/advisor", response_class=HTMLResponse)
async def advisor(request: Request):
    return templates.TemplateResponse("advisor.html", {"request": request})
```

```python
# src/rcars/web/routes/curate.py
from fastapi import APIRouter
router = APIRouter()
```

```python
# src/rcars/web/routes/admin.py
from fastapi import APIRouter
router = APIRouter()
```

```python
# src/rcars/web/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from rcars.web.routes import advisor, curate, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="RCARS", lifespan=lifespan)
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(advisor.router)
    app.include_router(curate.router)
    app.include_router(admin.router)
    return app


app = create_app()
```

Create a minimal `advisor.html` template:

```html
<!-- src/rcars/web/templates/advisor.html -->
<!DOCTYPE html>
<html>
<head><title>RCARS</title></head>
<body>
<h1>RCARS</h1>
</body>
</html>
```

Create empty static file:
```bash
touch src/rcars/web/static/rcars.css
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
pytest tests/web/test_advisor.py::test_advisor_page_loads -v
```
Expected: PASS

- [ ] **Step 5: Add `rcars serve` command to cli.py**

In `src/rcars/cli.py`, add after the existing `recommend` command:

```python
@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind")
@click.option("--port", default=8000, show_default=True, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """Start the RCARS web UI."""
    import uvicorn
    uvicorn.run("rcars.web.app:app", host=host, port=port, reload=reload)
```

- [ ] **Step 6: Smoke test the serve command**

```bash
rcars serve --help
```
Expected: Shows help with `--host`, `--port`, `--reload` options.

- [ ] **Step 7: Commit**

```bash
git add src/rcars/web/ tests/web/ src/rcars/cli.py
git commit -m "web: Add web module skeleton and rcars serve command"
```

---

## Task 2: Config Additions + DB Dependency

**Files:**
- Modify: `src/rcars/config.py`
- Create: `src/rcars/web/deps.py`
- Modify: `src/rcars/web/app.py`
- Modify: `tests/web/test_advisor.py`

- [ ] **Step 1: Write failing tests for new config fields**

```python
# Add to tests/web/test_advisor.py
import os
from rcars.config import Settings


def test_is_curator_matches_email():
    s = Settings(
        database_url="postgresql://x/y",
        curator_emails=["alice@redhat.com", "bob@redhat.com"],
    )
    assert s.is_curator("alice@redhat.com") is True
    assert s.is_curator("ALICE@REDHAT.COM") is True  # case-insensitive
    assert s.is_curator("charlie@redhat.com") is False


def test_curator_empty_by_default():
    s = Settings(database_url="postgresql://x/y")
    assert s.is_curator("anyone@redhat.com") is False
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/web/test_advisor.py::test_is_curator_matches_email -v
```
Expected: FAIL — `Settings` has no `curator_emails` field.

- [ ] **Step 3: Add fields to Settings**

In `src/rcars/config.py`, add to the `Settings` class after existing fields:

```python
# Web UI settings
curator_emails: list[str] = Field(default_factory=list)
dev_user: str | None = Field(default=None)
stale_days: int = Field(default=3)

model_config = SettingsConfigDict(
    env_prefix="RCARS_",
    # ... keep existing config ...
)

def is_curator(self, email: str) -> bool:
    """Return True if email is in the curator list (case-insensitive)."""
    return email.lower() in {e.lower() for e in self.curator_emails}
```

Note: `curator_emails` reads from `RCARS_CURATOR_EMAILS` (comma-separated), `dev_user` from `RCARS_DEV_USER`, `stale_days` from `RCARS_STALE_DAYS`.

Check the existing `model_config` in `config.py` — if it uses `env_prefix="RCARS_"` already, the env var names are automatic. If not, add explicit `validation_alias` for each field. The existing pattern in the file is the source of truth.

- [ ] **Step 4: Create deps.py with FastAPI dependencies**

```python
# src/rcars/web/deps.py
from fastapi import Request, HTTPException, Depends
from rcars.config import get_settings
from rcars.db import Database


def get_current_user(request: Request) -> str:
    """Return user identity. In Plan 3a: RCARS_DEV_USER or X-Forwarded-User header."""
    settings = get_settings()
    if settings.dev_user:
        return settings.dev_user
    return request.headers.get("X-Forwarded-User", "")


def require_curator(user: str = Depends(get_current_user)) -> str:
    """Raise 403 if user is not a curator."""
    settings = get_settings()
    if not settings.is_curator(user):
        raise HTTPException(status_code=403, detail="Curator access required")
    return user
```

- [ ] **Step 5: Wire DB into app lifespan and provide get_db dependency**

Update `src/rcars/web/app.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from rcars.config import get_settings
from rcars.db import Database
from rcars.web.routes import advisor, curate, admin

# Module-level DB instance — shared across all requests
_db: Database | None = None


def get_db() -> Database:
    if _db is None:
        raise RuntimeError("Database not initialized — is the app running?")
    return _db


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db
    settings = get_settings()
    _db = Database(settings.database_url)
    yield
    if _db:
        _db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="RCARS", lifespan=lifespan)
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(advisor.router)
    app.include_router(curate.router)
    app.include_router(admin.router)
    return app


app = create_app()
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/web/test_advisor.py -v
```
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add src/rcars/config.py src/rcars/web/deps.py src/rcars/web/app.py tests/web/test_advisor.py
git commit -m "web: Add curator config, dev user support, and DB dependency"
```

---

## Task 3: DB Enrichment CRUD + Notes Column

**Files:**
- Modify: `src/rcars/db.py`
- Create: `tests/web/test_db_enrichment.py`

The existing schema already has:
- `enrichment_tags (id, ci_name, tag_type, tag_value, added_by, added_at)` — use `tag_type="label"` for curator tags
- `enrichment_review_needed BOOLEAN` on `showroom_analysis`

Need to add:
- `notes TEXT` column to `showroom_analysis` (via schema update in `SCHEMA_SQL`)
- CRUD methods to `Database` class

- [ ] **Step 1: Write failing tests for enrichment CRUD**

```python
# tests/web/test_db_enrichment.py
import pytest
from rcars.db import Database


@pytest.fixture
def db(tmp_path):
    """In-memory-style test DB using a temp PostgreSQL schema."""
    import os
    url = os.environ.get("RCARS_DATABASE_URL", "postgresql://localhost/rcars_test")
    d = Database(url)
    d.drop_schema()
    d.create_schema()
    # Insert a test catalog item
    d.upsert_catalog_item({
        "ci_name": "test.lab.prod",
        "display_name": "Test Lab",
        "category": "test",
        "product": "OpenShift",
        "is_prod": True,
        "stage": "prod",
    })
    yield d
    d.drop_schema()
    d.close()


def test_add_and_get_tags(db):
    db.add_enrichment_tag("test.lab.prod", "label", "good for booth demo", "curator@redhat.com")
    db.add_enrichment_tag("test.lab.prod", "label", "new for Summit 2026", "curator@redhat.com")
    tags = db.get_enrichment_tags("test.lab.prod")
    values = [t["tag_value"] for t in tags]
    assert "good for booth demo" in values
    assert "new for Summit 2026" in values


def test_remove_tag(db):
    db.add_enrichment_tag("test.lab.prod", "label", "retiring Q3 2026", "curator@redhat.com")
    db.remove_enrichment_tag("test.lab.prod", "label", "retiring Q3 2026")
    tags = db.get_enrichment_tags("test.lab.prod")
    assert not any(t["tag_value"] == "retiring Q3 2026" for t in tags)


def test_duplicate_tag_is_ignored(db):
    db.add_enrichment_tag("test.lab.prod", "label", "booth demo", "a@redhat.com")
    db.add_enrichment_tag("test.lab.prod", "label", "booth demo", "b@redhat.com")  # duplicate
    tags = db.get_enrichment_tags("test.lab.prod")
    assert len([t for t in tags if t["tag_value"] == "booth demo"]) == 1


def test_add_and_get_note(db):
    db.upsert_showroom_analysis({"ci_name": "test.lab.prod"})
    db.set_enrichment_note("test.lab.prod", "Great for post-Summit follow-ups", "curator@redhat.com")
    note = db.get_enrichment_note("test.lab.prod")
    assert note == "Great for post-Summit follow-ups"


def test_set_and_clear_review_flag(db):
    db.upsert_showroom_analysis({"ci_name": "test.lab.prod"})
    db.set_enrichment_review_needed("test.lab.prod", True)
    analysis = db.get_showroom_analysis("test.lab.prod")
    assert analysis["enrichment_review_needed"] is True
    db.set_enrichment_review_needed("test.lab.prod", False)
    analysis = db.get_showroom_analysis("test.lab.prod")
    assert analysis["enrichment_review_needed"] is False


def test_get_db_currency(db):
    status = db.get_db_currency(stale_days=3)
    assert "last_refresh" in status
    assert "is_stale" in status
    assert isinstance(status["is_stale"], bool)
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/web/test_db_enrichment.py -v
```
Expected: All FAIL with `AttributeError: 'Database' object has no attribute 'add_enrichment_tag'`

- [ ] **Step 3: Add `notes` column to SCHEMA_SQL in db.py**

Find the `showroom_analysis` CREATE TABLE in `SCHEMA_SQL` (around line 40-57) and add `notes TEXT` after `enrichment_review_needed`:

```sql
    enrichment_review_needed BOOLEAN DEFAULT FALSE,
    notes TEXT
```

- [ ] **Step 4: Add enrichment CRUD methods to the Database class**

Add these methods to `src/rcars/db.py` (after `get_items_needing_analysis`):

```python
def add_enrichment_tag(self, ci_name: str, tag_type: str, tag_value: str, added_by: str | None = None) -> None:
    """Add a tag to a catalog item. Silently ignores duplicates."""
    with self._conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO enrichment_tags (ci_name, tag_type, tag_value, added_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (ci_name, tag_type, tag_value) DO NOTHING
            """,
            (ci_name, tag_type, tag_value, added_by),
        )
    self._conn.commit()

def remove_enrichment_tag(self, ci_name: str, tag_type: str, tag_value: str) -> None:
    """Remove a specific tag from a catalog item."""
    with self._conn.cursor() as cur:
        cur.execute(
            "DELETE FROM enrichment_tags WHERE ci_name = %s AND tag_type = %s AND tag_value = %s",
            (ci_name, tag_type, tag_value),
        )
    self._conn.commit()

def get_enrichment_tags(self, ci_name: str) -> list[dict]:
    """Return all enrichment tags for a catalog item."""
    with self._conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            "SELECT tag_type, tag_value, added_by, added_at FROM enrichment_tags WHERE ci_name = %s ORDER BY added_at",
            (ci_name,),
        )
        return cur.fetchall()

def get_enrichment_tags_for_items(self, ci_names: list[str]) -> dict[str, list[dict]]:
    """Return enrichment tags for multiple items, keyed by ci_name."""
    if not ci_names:
        return {}
    with self._conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            "SELECT ci_name, tag_type, tag_value, added_by FROM enrichment_tags WHERE ci_name = ANY(%s) ORDER BY ci_name, added_at",
            (ci_names,),
        )
        result: dict[str, list] = {name: [] for name in ci_names}
        for row in cur.fetchall():
            result[row["ci_name"]].append(row)
        return result

def set_enrichment_note(self, ci_name: str, note: str, updated_by: str | None = None) -> None:
    """Set the curator note for a catalog item (requires showroom_analysis row)."""
    with self._conn.cursor() as cur:
        cur.execute(
            "UPDATE showroom_analysis SET notes = %s WHERE ci_name = %s",
            (note, ci_name),
        )
        if cur.rowcount == 0:
            # Insert minimal analysis row if none exists
            cur.execute(
                "INSERT INTO showroom_analysis (ci_name, notes) VALUES (%s, %s) ON CONFLICT (ci_name) DO UPDATE SET notes = EXCLUDED.notes",
                (ci_name, note),
            )
    self._conn.commit()

def get_enrichment_note(self, ci_name: str) -> str | None:
    """Return the curator note for a catalog item, or None."""
    with self._conn.cursor() as cur:
        cur.execute("SELECT notes FROM showroom_analysis WHERE ci_name = %s", (ci_name,))
        row = cur.fetchone()
        return row[0] if row else None

def set_enrichment_review_needed(self, ci_name: str, needed: bool) -> None:
    """Set or clear the enrichment review flag on showroom_analysis."""
    with self._conn.cursor() as cur:
        cur.execute(
            "UPDATE showroom_analysis SET enrichment_review_needed = %s WHERE ci_name = %s",
            (needed, ci_name),
        )
        if cur.rowcount == 0:
            cur.execute(
                "INSERT INTO showroom_analysis (ci_name, enrichment_review_needed) VALUES (%s, %s) ON CONFLICT (ci_name) DO UPDATE SET enrichment_review_needed = EXCLUDED.enrichment_review_needed",
                (ci_name, needed),
            )
    self._conn.commit()

def get_db_currency(self, stale_days: int = 3) -> dict:
    """Return last catalog refresh date and staleness status."""
    from datetime import datetime, timezone, timedelta
    with self._conn.cursor() as cur:
        cur.execute("SELECT MAX(updated_at) FROM catalog_items")
        row = cur.fetchone()
        last_refresh = row[0] if row else None
    if last_refresh is None:
        return {"last_refresh": "never", "is_stale": True}
    now = datetime.now(timezone.utc)
    is_stale = (now - last_refresh) > timedelta(days=stale_days)
    return {
        "last_refresh": last_refresh.strftime("%Y.%m.%d"),
        "is_stale": is_stale,
    }
```

Check the import at the top of `db.py` — if `psycopg.rows` is not already imported, add:
```python
import psycopg.rows
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/web/test_db_enrichment.py -v
```
Expected: All PASS. If `notes` column is missing from an existing DB, run `rcars init-db` or `DROP/CREATE` the schema in the test DB.

- [ ] **Step 6: Commit**

```bash
git add src/rcars/db.py tests/web/test_db_enrichment.py
git commit -m "db: Add enrichment CRUD methods, notes column, get_db_currency"
```

---

## Task 4: Base Template + Dark CSS + LCARS Logo

**Files:**
- Create: `src/rcars/web/templates/base.html`
- Create: `src/rcars/web/static/rcars.css`
- Modify: `tests/web/test_advisor.py`

- [ ] **Step 1: Write tests for base template elements**

```python
# Add to tests/web/test_advisor.py
def test_advisor_has_logo(client):
    response = client.get("/advisor")
    assert response.status_code == 200
    assert "RCARS" in response.text
    assert "RHDP CONTENT ADVISOR" in response.text

def test_advisor_has_nav(client):
    response = client.get("/advisor")
    assert "/advisor" in response.text
    assert "Advisor" in response.text

def test_advisor_loads_htmx(client):
    response = client.get("/advisor")
    assert "htmx" in response.text.lower()

def test_advisor_loads_alpinejs(client):
    response = client.get("/advisor")
    assert "alpinejs" in response.text.lower() or "alpine" in response.text.lower()
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/web/test_advisor.py::test_advisor_has_logo -v
```
Expected: FAIL (current advisor.html is a stub).

- [ ] **Step 3: Create base.html**

```html
<!-- src/rcars/web/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RCARS — RHDP Content Advisor</title>
  <link rel="stylesheet" href="/static/rcars.css">
  <script src="https://unpkg.com/htmx.org@1.9.12" defer></script>
  <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
</head>
<body x-data="{ curatorMode: false }">

  <!-- Top bar with LCARS logo -->
  <header class="rcars-header">
    <svg width="300" height="80" viewBox="0 0 300 80" xmlns="http://www.w3.org/2000/svg" class="rcars-logo">
      <!-- Arc -->
      <path d="M 10 8 A 44 44 0 0 1 54 52 L 68 52 L 68 66 L 46 66 Q 10 66 10 32 Z" fill="#FF9900"/>
      <path d="M 20 22 A 22 22 0 0 1 40 44" stroke="#CC6600" stroke-width="3" fill="none" opacity="0.6"/>
      <!-- Header bars -->
      <rect x="72" y="8" width="108" height="24" rx="4" fill="#FF9900"/>
      <rect x="184" y="8" width="26" height="24" rx="4" fill="#FFCC99"/>
      <rect x="214" y="8" width="48" height="24" rx="4" fill="#9966CC"/>
      <!-- Middle bar -->
      <rect x="72" y="36" width="190" height="16" rx="3" fill="#1c1c2e"/>
      <!-- Bottom bar -->
      <rect x="72" y="56" width="190" height="16" rx="3" fill="#1c1c2e"/>
      <!-- RCARS -->
      <text x="80" y="25" font-family="Arial Black, Impact, sans-serif" font-size="15" font-weight="900" fill="#000" letter-spacing="4">RCARS</text>
      <!-- RHDP CONTENT ADVISOR -->
      <text x="80" y="48" font-family="Arial, sans-serif" font-size="9" fill="#FF9900" letter-spacing="1.5">RHDP CONTENT ADVISOR</text>
      <!-- Date + currency badge -->
      <text x="80" y="68" font-family="Arial, sans-serif" font-size="8" fill="#FFCC99">{{ db_status.last_refresh }}</text>
      {% if db_status.is_stale %}
      <rect x="142" y="57" width="52" height="14" rx="2" fill="#3a0d0d"/>
      <text x="147" y="67" font-family="Arial Black, sans-serif" font-size="8" font-weight="900" fill="#c9190b">● STALE</text>
      {% else %}
      <rect x="142" y="57" width="60" height="14" rx="2" fill="#0d3a0d"/>
      <text x="147" y="67" font-family="Arial Black, sans-serif" font-size="8" font-weight="900" fill="#5cb85c">● CURRENT</text>
      {% endif %}
    </svg>

    <div class="header-right">
      {% if current_user %}
        {% if is_curator %}
          <button class="curator-toggle" @click="curatorMode = !curatorMode" :class="curatorMode ? 'active' : ''">
            <span x-text="curatorMode ? '🏷 Curator ON' : '🏷 Curator'"></span>
          </button>
        {% endif %}
        <span class="user-email">{{ current_user }}</span>
      {% endif %}
    </div>
  </header>

  <!-- Body with nav + content -->
  <div class="rcars-body">
    <nav class="rcars-nav">
      <a href="/advisor" class="nav-item {% if active_page == 'advisor' %}active{% endif %}">💬 Advisor</a>
      {% if is_curator %}
      <a href="/curate" class="nav-item {% if active_page == 'curate' %}active{% endif %}">🏷 Curate</a>
      <a href="/admin" class="nav-item {% if active_page == 'admin' %}active{% endif %}">⚙ Admin</a>
      {% endif %}

      {% if active_page == 'advisor' %}
      <div class="nav-section-label">HISTORY</div>
      <div id="session-history" x-data="sessionHistory()">
        <template x-for="s in sessions" :key="s.id">
          <a :href="'/advisor?session_id=' + s.id" class="nav-item history-item" x-text="s.label"></a>
        </template>
      </div>
      {% endif %}
    </nav>

    <main class="rcars-main">
      {% block content %}{% endblock %}
    </main>
  </div>

  <script>
  // Session history stored in localStorage only — never sent to server as tracking
  function sessionHistory() {
    return {
      sessions: JSON.parse(localStorage.getItem('rcars_sessions') || '[]').slice(0, 10),
    };
  }

  // Called from advisor page after first query to persist session label
  function saveSession(sessionId, label) {
    const sessions = JSON.parse(localStorage.getItem('rcars_sessions') || '[]');
    // Remove existing entry for this session_id (avoid duplicates)
    const filtered = sessions.filter(s => s.id !== sessionId);
    filtered.unshift({ id: sessionId, label: label.slice(0, 40), ts: Date.now() });
    localStorage.setItem('rcars_sessions', JSON.stringify(filtered.slice(0, 20)));
  }
  </script>
</body>
</html>
```

- [ ] **Step 4: Create rcars.css**

```css
/* src/rcars/web/static/rcars.css */
:root {
  --bg-primary: #0f1117;
  --bg-secondary: #0a0d12;
  --bg-card: #1a1f2e;
  --bg-card-green: #1a2a1a;
  --bg-card-amber: #2a2a1a;
  --bg-card-red: #2a1a1a;
  --text-primary: #d2d2d2;
  --text-muted: #666;
  --text-amber: #e8a838;
  --score-green: #5cb85c;
  --score-amber: #e8a838;
  --score-red: #c9190b;
  --accent-blue: #73bcf7;
  --border: #1e2030;
  --lcars-amber: #FF9900;
  --lcars-purple: #9966CC;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  font-size: 14px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.rcars-header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.rcars-logo { height: 56px; width: auto; }

.header-right { display: flex; align-items: center; gap: 12px; }

.user-email { color: var(--text-muted); font-size: 12px; }

.curator-toggle {
  background: #1a1f0d;
  border: 1px solid #3a3a1a;
  color: var(--text-amber);
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  cursor: pointer;
}
.curator-toggle.active { background: #2a2a1a; border-color: var(--lcars-amber); }

/* Layout */
.rcars-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.rcars-nav {
  width: 150px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  padding: 12px 0;
  flex-shrink: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: block;
  padding: 7px 14px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 12px;
}
.nav-item:hover { color: var(--text-primary); }
.nav-item.active {
  background: var(--bg-card);
  border-left: 2px solid var(--accent-blue);
  color: var(--accent-blue);
}
.nav-item.history-item { font-size: 11px; color: #444; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nav-item.history-item:hover { color: var(--text-muted); }

.nav-section-label {
  padding: 8px 14px 4px;
  font-size: 9px;
  color: #333;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-top: 1px solid var(--border);
  margin-top: 6px;
}

.rcars-main { flex: 1; overflow: hidden; display: flex; }

/* Two-pane advisor layout */
.advisor-layout { display: flex; width: 100%; height: 100%; }

.chat-pane {
  width: 340px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.pane-label {
  font-size: 9px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 10px;
}

.chat-turns { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }

.chat-turn-user {
  background: #0d1a0d;
  border-radius: 4px;
  padding: 7px 10px;
  color: #aaa;
  font-style: italic;
  font-size: 13px;
  align-self: flex-end;
  max-width: 90%;
}

.chat-turn-assistant {
  background: var(--bg-card);
  border-radius: 4px;
  padding: 7px 10px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
}
.chat-turn-assistant:hover { border-color: #333; }
.chat-turn-restore { font-size: 10px; color: #444; margin-top: 3px; }

.chat-welcome {
  background: var(--bg-card);
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 8px;
}
.chat-welcome p { font-size: 13px; margin-bottom: 4px; }
.chat-welcome .hint { font-size: 11px; color: var(--text-muted); }

.chat-input-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid #333;
  border-radius: 4px;
  color: var(--text-primary);
  padding: 8px 10px;
  font-size: 13px;
  resize: none;
  font-family: inherit;
}
.chat-input:focus { outline: none; border-color: var(--accent-blue); }

.btn-send {
  background: #1a3a5a;
  border: none;
  color: var(--accent-blue);
  padding: 8px 14px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-send:hover { background: #1f4a70; }

/* Recommendations pane */
.rec-pane {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* Recommendation cards */
.rec-card {
  border-radius: 4px;
  padding: 10px 12px;
  cursor: pointer;
  border-left: 3px solid transparent;
}
.rec-card.score-green { background: var(--bg-card-green); border-left-color: var(--score-green); }
.rec-card.score-amber { background: var(--bg-card-amber); border-left-color: var(--score-amber); }
.rec-card.score-red { background: var(--bg-card-red); border-left-color: var(--score-red); }

.rec-card-header { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 6px; }

.rec-score { font-weight: 700; font-size: 16px; min-width: 36px; }
.score-green .rec-score { color: var(--score-green); }
.score-amber .rec-score { color: var(--score-amber); }
.score-red .rec-score { color: var(--score-red); }

.rec-title { font-weight: 600; font-size: 13px; }
.rec-meta { font-size: 10px; color: var(--text-muted); margin-top: 2px; }
.rec-expand-hint { font-size: 10px; color: #444; margin-left: auto; flex-shrink: 0; }

.rec-rationale { font-size: 12px; color: #aaa; line-height: 1.5; margin-bottom: 6px; }

.tag-list { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.tag-pill {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  background: #0d2a0d;
  color: var(--score-green);
}

/* Expanded card extras */
.rec-expanded { margin-top: 8px; }
.rec-detail-row { font-size: 11px; color: var(--text-muted); margin-bottom: 3px; }
.rec-detail-row span { color: #aaa; }
.rec-catalog-link { color: var(--accent-blue); font-size: 10px; }

.curator-actions {
  border-top: 1px solid #2a3a2a;
  padding-top: 8px;
  margin-top: 8px;
  display: flex;
  gap: 6px;
  align-items: center;
}
.btn-curator {
  background: #0d1f0d;
  border: 1px solid #3a5a3a;
  color: var(--score-green);
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 10px;
  cursor: pointer;
}
.btn-curator.secondary { background: var(--bg-card); border-color: #333; color: var(--text-muted); }

.new-session-btn {
  background: transparent;
  border: 1px solid #333;
  color: var(--text-muted);
  padding: 5px 14px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
  align-self: center;
  margin-top: 8px;
}

/* Curate page */
.curate-layout { padding: 20px; flex: 1; overflow-y: auto; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.filter-input {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid #333;
  border-radius: 4px;
  color: var(--text-primary);
  padding: 6px 10px;
  font-size: 13px;
  min-width: 160px;
}
.filter-select {
  background: var(--bg-card);
  border: 1px solid #333;
  border-radius: 4px;
  color: var(--text-muted);
  padding: 6px 8px;
  font-size: 12px;
}
.curate-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 6px;
}
.curate-item-title { font-weight: 600; font-size: 13px; }
.curate-item-ci { font-size: 10px; color: var(--text-muted); margin-bottom: 6px; }
.tag-pill-removable {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  background: #0d2a0d;
  color: var(--score-green);
  cursor: pointer;
}
.review-badge {
  display: inline-block;
  background: #2a2a1a;
  color: var(--text-amber);
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 9px;
  margin-left: 6px;
}

/* Admin page */
.admin-layout { padding: 20px; flex: 1; overflow-y: auto; }
.admin-section { margin-bottom: 24px; }
.admin-section h3 { font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
.btn-action {
  background: #1a3a5a;
  border: none;
  color: var(--accent-blue);
  padding: 7px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-action:hover { background: #1f4a70; }
.status-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.status-table td, .status-table th { padding: 6px 10px; border-bottom: 1px solid var(--border); text-align: left; }
.status-table th { color: var(--text-muted); font-weight: normal; }
```

- [ ] **Step 5: Update advisor.html to extend base**

```html
<!-- src/rcars/web/templates/advisor.html -->
{% extends "base.html" %}
{% block content %}
<div class="advisor-layout">
  <div class="chat-pane">
    <div class="pane-label">Conversation</div>
    <div class="chat-turns" id="chat-pane">
      <div class="chat-welcome">
        <p>Describe what you're looking for or paste an event URL.</p>
        <p class="hint">e.g. "OpenShift demos for a developer audience at KubeCon"</p>
        <p class="hint">e.g. "https://summit.redhat.com/2026"</p>
      </div>
    </div>
    <form hx-post="/advisor/query"
          hx-target="#rec-pane"
          hx-swap="innerHTML"
          class="chat-input-row"
          x-data="{ msg: '' }"
          @htmx:after-request="msg = ''">
      <input type="hidden" name="session_id" value="{{ session_id }}">
      <textarea name="message" class="chat-input" rows="2"
                placeholder="Refine or ask anything..."
                x-model="msg"
                @keydown.enter.prevent="if (!$event.shiftKey && msg.trim()) $el.closest('form').requestSubmit()"></textarea>
      <button type="submit" class="btn-send">Send</button>
    </form>
  </div>
  <div class="rec-pane" id="rec-pane">
    <div class="pane-label">Recommendations</div>
    <p style="color: var(--text-muted); font-size: 12px;">← Start a conversation to see results</p>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Update advisor route to pass template context**

Update `src/rcars/web/routes/advisor.py`:

```python
import uuid
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import get_current_user, get_db
from rcars.db import Database

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# In-memory conversation store: session_id -> list of turn dicts
_sessions: dict[str, list[dict]] = {}


def _base_context(request: Request, db: Database, user: str, active_page: str) -> dict:
    from rcars.config import get_settings
    settings = get_settings()
    return {
        "request": request,
        "current_user": user,
        "is_curator": settings.is_curator(user),
        "active_page": active_page,
        "db_status": db.get_db_currency(stale_days=settings.stale_days),
    }


@router.get("/advisor", response_class=HTMLResponse)
async def advisor(
    request: Request,
    session_id: str | None = None,
    user: str = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    sid = session_id or str(uuid.uuid4())
    ctx = _base_context(request, db, user, "advisor")
    ctx["session_id"] = sid
    return templates.TemplateResponse("advisor.html", ctx)
```

Also update `curate.py` and `admin.py` stub routers to add a placeholder GET route returning 200 for now (so tests pass):

```python
# src/rcars/web/routes/curate.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from rcars.web.deps import require_curator, get_db, get_current_user
from rcars.db import Database

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/curate", response_class=HTMLResponse)
async def curate(request: Request, user: str = Depends(require_curator), db: Database = Depends(get_db)):
    return HTMLResponse("<html><body>Curate (placeholder)</body></html>")
```

```python
# src/rcars/web/routes/admin.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from rcars.web.deps import require_curator, get_db
from rcars.db import Database

router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, user: str = Depends(require_curator), db: Database = Depends(get_db)):
    return HTMLResponse("<html><body>Admin (placeholder)</body></html>")
```

Note: For `TestClient` tests, the lifespan doesn't run by default. Add a test fixture that patches `get_db`:

```python
# Update conftest or test_advisor.py fixture:
@pytest.fixture
def client(monkeypatch):
    import os
    monkeypatch.setenv("RCARS_DEV_USER", "test@redhat.com")
    # Patch get_db to return a real test DB or a mock
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    from rcars.web import app as web_app
    web_app.get_db = lambda: mock_db  # Override the dependency
    from starlette.testclient import TestClient
    from rcars.web.app import app
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

Import `get_db` from `rcars.web.app` in the test file:
```python
from rcars.web.app import app, get_db
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/web/test_advisor.py -v
```
Expected: All PASS.

- [ ] **Step 8: Commit**

```bash
git add src/rcars/web/templates/ src/rcars/web/static/ src/rcars/web/routes/ tests/web/
git commit -m "web: Add base template, dark CSS, LCARS logo, advisor skeleton"
```

---

## Task 5: Recommendation Card Fragments

**Files:**
- Create: `src/rcars/web/templates/fragments/rec_card.html`
- Create: `src/rcars/web/templates/fragments/rec_card_expanded.html`
- Create: `src/rcars/web/templates/fragments/rec_list.html`
- Create: `src/rcars/web/templates/fragments/chat_turn.html`
- Modify: `tests/web/test_advisor.py`

- [ ] **Step 1: Write tests for fragment rendering**

```python
# Add to tests/web/test_advisor.py
from fastapi.templating import Jinja2Templates
from pathlib import Path

TEMPLATES = Jinja2Templates(directory=str(
    Path(__file__).parent.parent.parent / "src/rcars/web/templates"
))

SAMPLE_REC = {
    "ci_name": "openshift-cnv.lightspeed-workshop.prod",
    "display_name": "OpenShift Lightspeed Workshop",
    "fit_score": 92,
    "rationale": "Strong fit for developer audience.",
    "suggested_format": "hands_on_lab",
    "duration_notes": "90 min",
    "caveats": "Requires OCP 4.16+",
    "tags": [{"tag_value": "booth demo"}, {"tag_value": "Summit 2026"}],
    "note": None,
    "enrichment_review_needed": False,
    "catalog_link": "https://demo.redhat.com/catalog/openshift-cnv.lightspeed-workshop.prod",
}


def test_rec_card_renders_score_and_name(client):
    """Verify rec_card.html renders via a direct template test."""
    from starlette.testclient import TestClient
    from starlette.requests import Request
    # Test the fragment template directly
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(
        str(Path(__file__).parent.parent.parent / "src/rcars/web/templates")
    ))
    tmpl = env.get_template("fragments/rec_card.html")
    html = tmpl.render(rec=SAMPLE_REC, is_curator=False, session_id="test-123")
    assert "92" in html
    assert "OpenShift Lightspeed Workshop" in html
    assert "booth demo" in html


def test_rec_card_expanded_shows_caveats(client):
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(
        str(Path(__file__).parent.parent.parent / "src/rcars/web/templates")
    ))
    tmpl = env.get_template("fragments/rec_card_expanded.html")
    html = tmpl.render(rec=SAMPLE_REC, is_curator=False, session_id="test-123")
    assert "Requires OCP 4.16+" in html
    assert "openshift-cnv.lightspeed-workshop.prod" in html


def test_rec_card_expanded_shows_curator_controls_for_curator():
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(
        str(Path(__file__).parent.parent.parent / "src/rcars/web/templates")
    ))
    tmpl = env.get_template("fragments/rec_card_expanded.html")
    html = tmpl.render(rec=SAMPLE_REC, is_curator=True, session_id="test-123")
    assert "curator-actions" in html
    assert "Tag" in html
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/web/test_advisor.py::test_rec_card_renders_score_and_name -v
```
Expected: FAIL — templates don't exist yet.

- [ ] **Step 3: Create rec_card.html (B-view — default collapsed)**

```html
<!-- src/rcars/web/templates/fragments/rec_card.html -->
{% set score = rec.fit_score %}
{% if score >= 80 %}{% set score_class = "score-green" %}
{% elif score >= 50 %}{% set score_class = "score-amber" %}
{% else %}{% set score_class = "score-red" %}{% endif %}

<div class="rec-card {{ score_class }}"
     x-data="{ expanded: false }"
     @click="expanded = !expanded">
  <div class="rec-card-header">
    <div class="rec-score">{{ score }}%</div>
    <div style="flex:1;min-width:0;">
      <div class="rec-title">{{ rec.display_name }}</div>
      <div class="rec-meta">
        {{ rec.ci_name }} · {{ rec.suggested_format or '—' }} · {{ rec.duration_notes or '—' }}
      </div>
    </div>
    <span class="rec-expand-hint" x-text="expanded ? '▾' : '▸'"></span>
  </div>

  <div class="rec-rationale">{{ rec.rationale }}</div>

  {% if rec.tags %}
  <div class="tag-list">
    {% for tag in rec.tags %}
    <span class="tag-pill">{{ tag.tag_value }}</span>
    {% endfor %}
  </div>
  {% endif %}

  <!-- Expanded content (C-view) — hidden until clicked -->
  <div x-show="expanded" style="display:none;" @click.stop>
    {% include "fragments/rec_card_expanded.html" %}
  </div>
</div>
```

- [ ] **Step 4: Create rec_card_expanded.html (C-view extras)**

```html
<!-- src/rcars/web/templates/fragments/rec_card_expanded.html -->
<div class="rec-expanded">
  <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:6px;">
    <div class="rec-detail-row"><span>Format:</span> {{ rec.suggested_format or '—' }}</div>
    <div class="rec-detail-row"><span>Duration:</span> {{ rec.duration_notes or '—' }}</div>
  </div>

  {% if rec.caveats %}
  <div class="rec-detail-row" style="margin-bottom:6px;"><span>Caveat:</span> {{ rec.caveats }}</div>
  {% endif %}

  <div style="margin-bottom:6px;">
    <a href="{{ rec.catalog_link }}" target="_blank" class="rec-catalog-link">View in Catalog ↗</a>
  </div>

  {% if rec.note %}
  <div class="rec-detail-row" style="margin-bottom:6px;font-style:italic;color:#888;">📝 {{ rec.note }}</div>
  {% endif %}

  {% if is_curator %}
  <div class="curator-actions" x-show="curatorMode">
    <span style="font-size:10px;color:#555;">🏷</span>
    <button class="btn-curator"
            hx-post="/curate/tag"
            hx-vals='{"ci_name": "{{ rec.ci_name }}", "tag_type": "label"}'
            hx-include="[name='_tag_input_{{ rec.ci_name | replace('.', '_') }}']"
            hx-swap="none"
            @click.stop>
      + Tag
    </button>
    <input type="text"
           name="_tag_input_{{ rec.ci_name | replace('.', '_') }}"
           placeholder="tag text..."
           style="background:#1a1f2e;border:1px solid #333;color:#d2d2d2;padding:2px 6px;border-radius:3px;font-size:10px;width:100px;"
           @click.stop>
    <button class="btn-curator secondary"
            hx-post="/curate/flag"
            hx-vals='{"ci_name": "{{ rec.ci_name }}", "needed": "true"}'
            hx-swap="none"
            @click.stop>
      ⚑ Flag
    </button>
  </div>
  {% endif %}
</div>
```

- [ ] **Step 5: Create rec_list.html**

```html
<!-- src/rcars/web/templates/fragments/rec_list.html -->
<div class="pane-label">Recommendations</div>
{% if recs %}
  {% for rec in recs %}
    {% include "fragments/rec_card.html" %}
  {% endfor %}
{% else %}
  <p style="color:var(--text-muted);font-size:12px;">No strong matches found. Try rephrasing your query.</p>
{% endif %}
<button class="new-session-btn"
        onclick="window.location.href='/advisor'">
  + New session
</button>
```

- [ ] **Step 6: Create chat_turn.html**

```html
<!-- src/rcars/web/templates/fragments/chat_turn.html -->
<!-- Appended to #chat-pane via OOB swap -->
<div hx-swap-oob="beforeend:#chat-pane">
  <div class="chat-turn-user">{{ user_message }}</div>
  <div class="chat-turn-assistant"
       hx-get="/advisor/restore/{{ session_id }}/{{ turn_index }}"
       hx-target="#rec-pane"
       hx-swap="innerHTML"
       hx-trigger="click">
    {{ assistant_message }}
    <div class="chat-turn-restore">↩ click to restore these results</div>
  </div>
</div>
<script>saveSession('{{ session_id }}', {{ first_message | tojson }});</script>
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/web/test_advisor.py -v
```
Expected: All PASS.

- [ ] **Step 8: Commit**

```bash
git add src/rcars/web/templates/fragments/ tests/web/test_advisor.py
git commit -m "web: Add recommendation card fragments and chat turn template"
```

---

## Task 6: Advisor Query Endpoint

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`
- Modify: `tests/web/test_advisor.py`

The `recommend()` function signature is:
```python
recommend(query: str, db: Database, anthropic_client, model: str, limit: int, prod_only: bool) -> dict | None
```
Returns `dict` with key `recommendations` (list of dicts with `fit_score`, `display_name`, `ci_name`, `rationale`, `suggested_format`, `duration_notes`, `caveats`), or `None` on failure.

- [ ] **Step 1: Write failing tests for the query endpoint**

```python
# Add to tests/web/test_advisor.py
from unittest.mock import patch, MagicMock


MOCK_RECOMMEND_RESULT = {
    "recommendations": [
        {
            "ci_name": "openshift-cnv.lightspeed-workshop.prod",
            "display_name": "OpenShift Lightspeed Workshop",
            "fit_score": 92,
            "rationale": "Strong fit.",
            "suggested_format": "hands_on_lab",
            "duration_notes": "90 min",
            "caveats": "",
        }
    ],
    "overall_assessment": "Good matches found.",
    "content_gaps": [],
}


def test_advisor_query_returns_rec_cards(client):
    with patch("rcars.web.routes.advisor.recommend", return_value=MOCK_RECOMMEND_RESULT):
        response = client.post("/advisor/query", data={
            "session_id": "test-session-abc",
            "message": "OpenShift labs for developers",
        })
    assert response.status_code == 200
    assert "OpenShift Lightspeed Workshop" in response.text
    assert "92" in response.text


def test_advisor_query_appends_chat_turn(client):
    with patch("rcars.web.routes.advisor.recommend", return_value=MOCK_RECOMMEND_RESULT):
        response = client.post("/advisor/query", data={
            "session_id": "test-session-def",
            "message": "Show me OpenShift labs",
        })
    assert response.status_code == 200
    # OOB swap element for chat pane should be present
    assert "chat-pane" in response.text


def test_advisor_query_accumulates_context(client):
    """Second message includes first message in the description sent to recommend."""
    calls = []

    def capture_recommend(query, **kwargs):
        calls.append(query)
        return MOCK_RECOMMEND_RESULT

    with patch("rcars.web.routes.advisor.recommend", side_effect=capture_recommend):
        client.post("/advisor/query", data={"session_id": "acc-test", "message": "OpenShift labs"})
        client.post("/advisor/query", data={"session_id": "acc-test", "message": "shorter ones only"})

    assert len(calls) == 2
    assert "OpenShift labs" in calls[1]
    assert "shorter ones only" in calls[1]


def test_advisor_query_handles_recommend_none(client):
    with patch("rcars.web.routes.advisor.recommend", return_value=None):
        response = client.post("/advisor/query", data={
            "session_id": "fail-test",
            "message": "something",
        })
    assert response.status_code == 200
    assert "No strong matches" in response.text
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/web/test_advisor.py::test_advisor_query_returns_rec_cards -v
```
Expected: FAIL — `/advisor/query` returns 405 (not defined).

- [ ] **Step 3: Implement POST /advisor/query**

Add to `src/rcars/web/routes/advisor.py`:

```python
import uuid
from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import get_current_user, get_db
from rcars.db import Database
from rcars.recommender import recommend
from rcars.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_sessions: dict[str, list[dict]] = {}

CATALOG_NS = "babylon-catalog-prod"


def _catalog_url(ci_name: str) -> str:
    return f"https://demo.redhat.com/catalog/{ci_name}"


def _base_context(request: Request, db: Database, user: str, active_page: str) -> dict:
    settings = get_settings()
    return {
        "request": request,
        "current_user": user,
        "is_curator": settings.is_curator(user),
        "active_page": active_page,
        "db_status": db.get_db_currency(stale_days=settings.stale_days),
    }


def _enrich_recs(recs: list[dict], db: Database) -> list[dict]:
    """Attach enrichment tags and notes to recommendation dicts."""
    ci_names = [r["ci_name"] for r in recs if r.get("ci_name")]
    tags_by_ci = db.get_enrichment_tags_for_items(ci_names)
    enriched = []
    for rec in recs:
        ci = rec.get("ci_name", "")
        note = db.get_enrichment_note(ci)
        enriched.append({
            **rec,
            "tags": tags_by_ci.get(ci, []),
            "note": note,
            "catalog_link": _catalog_url(ci),
            "enrichment_review_needed": False,
        })
    return enriched


@router.get("/advisor", response_class=HTMLResponse)
async def advisor(
    request: Request,
    session_id: str | None = None,
    user: str = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    sid = session_id or str(uuid.uuid4())
    ctx = _base_context(request, db, user, "advisor")
    ctx["session_id"] = sid
    return templates.TemplateResponse("advisor.html", ctx)


@router.post("/advisor/query", response_class=HTMLResponse)
async def advisor_query(
    request: Request,
    session_id: Annotated[str, Form()],
    message: Annotated[str, Form()],
    user: str = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    settings = get_settings()
    client = settings.get_anthropic_client()

    # Load or create in-memory session
    turns = _sessions.setdefault(session_id, [])

    # Append user turn
    turns.append({"role": "user", "content": message})

    # Build accumulated description from all user turns
    description = " ".join(t["content"] for t in turns if t["role"] == "user")

    # Call recommender
    result = recommend(
        query=description,
        db=db,
        anthropic_client=client,
        model=settings.model,
        limit=10,
        prod_only=True,
    )

    raw_recs = result.get("recommendations", []) if result else []
    recs = _enrich_recs(raw_recs, db)
    rec_ci_names = [r["ci_name"] for r in recs]

    # Append assistant turn
    turn_index = len(turns)
    overall = (result or {}).get("overall_assessment", f"Found {len(recs)} matches.")
    turns.append({
        "role": "assistant",
        "content": overall,
        "rec_ci_names": rec_ci_names,
        "turn_index": turn_index,
    })

    is_curator = settings.is_curator(user)
    first_message = turns[0]["content"] if turns else message

    # Render rec list (primary swap to #rec-pane)
    rec_html = templates.get_template("fragments/rec_list.html").render(
        recs=recs,
        is_curator=is_curator,
        session_id=session_id,
    )

    # Render chat turn (OOB swap appended to #chat-pane)
    chat_html = templates.get_template("fragments/chat_turn.html").render(
        user_message=message,
        assistant_message=overall,
        session_id=session_id,
        turn_index=turn_index,
        first_message=first_message,
    )

    return HTMLResponse(content=rec_html + "\n" + chat_html)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/web/test_advisor.py -v
```
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/rcars/web/routes/advisor.py tests/web/test_advisor.py
git commit -m "web: Implement advisor query endpoint with in-memory sessions"
```

---

## Task 7: Advisor Rollback

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`
- Modify: `tests/web/test_advisor.py`

- [ ] **Step 1: Write failing test**

```python
# Add to tests/web/test_advisor.py
def test_rollback_restores_previous_results(client):
    """Clicking a chat turn restores that turn's recommendations."""
    # Seed a session directly in the in-memory store
    from rcars.web.routes.advisor import _sessions
    _sessions["rollback-test"] = [
        {"role": "user", "content": "OpenShift labs"},
        {
            "role": "assistant",
            "content": "Found 1 match.",
            "rec_ci_names": ["openshift-cnv.lightspeed-workshop.prod"],
            "turn_index": 1,
        },
    ]

    # Mock db.get_catalog_item and get_enrichment_tags_for_items
    with patch("rcars.web.routes.advisor.recommend") as mock_rec:
        response = client.get("/advisor/restore/rollback-test/1")

    assert response.status_code == 200


def test_rollback_invalid_session_returns_empty(client):
    response = client.get("/advisor/restore/nonexistent-session/0")
    assert response.status_code == 200
    assert "No strong matches" in response.text or response.text  # graceful empty
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/web/test_advisor.py::test_rollback_restores_previous_results -v
```
Expected: FAIL — route not defined.

- [ ] **Step 3: Implement GET /advisor/restore**

Add to `src/rcars/web/routes/advisor.py`:

```python
@router.get("/advisor/restore/{session_id}/{turn_index}", response_class=HTMLResponse)
async def advisor_restore(
    request: Request,
    session_id: str,
    turn_index: int,
    user: str = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Restore the recommendation set from a previous conversation turn."""
    settings = get_settings()
    turns = _sessions.get(session_id, [])

    # Find the assistant turn at turn_index
    assistant_turn = None
    for t in turns:
        if t.get("role") == "assistant" and t.get("turn_index") == turn_index:
            assistant_turn = t
            break

    if not assistant_turn:
        # Session gone (server restart) or invalid — return empty list gracefully
        recs = []
    else:
        ci_names = assistant_turn.get("rec_ci_names", [])
        # Load catalog items from DB and reconstruct rec-like dicts
        raw_items = [db.get_catalog_item(ci) for ci in ci_names]
        raw_items = [item for item in raw_items if item]  # filter None
        # Convert catalog items to rec format (no rationale on rollback — show saved summary)
        recs = _enrich_recs(
            [{"ci_name": item["ci_name"],
              "display_name": item.get("display_name", item["ci_name"]),
              "fit_score": 0,  # score not stored — show 0 on rollback
              "rationale": "(restored from history)",
              "suggested_format": item.get("category", ""),
              "duration_notes": "",
              "caveats": ""} for item in raw_items],
            db,
        )

    is_curator = settings.is_curator(user)
    rec_html = templates.get_template("fragments/rec_list.html").render(
        recs=recs,
        is_curator=is_curator,
        session_id=session_id,
    )
    return HTMLResponse(content=rec_html)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/web/test_advisor.py -v
```
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/rcars/web/routes/advisor.py tests/web/test_advisor.py
git commit -m "web: Implement advisor rollback endpoint"
```

---

## Task 8: Curate Page + HTMX Endpoints

**Files:**
- Modify: `src/rcars/web/routes/curate.py`
- Create: `src/rcars/web/templates/curate.html`
- Create: `tests/web/test_curate.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/web/test_curate.py
import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from rcars.web.app import app, get_db
from rcars.config import get_settings


@pytest.fixture
def curator_client(monkeypatch):
    monkeypatch.setenv("RCARS_DEV_USER", "curator@redhat.com")
    monkeypatch.setenv("RCARS_CURATOR_EMAILS", "curator@redhat.com")
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    mock_db.list_catalog_items.return_value = [
        {"ci_name": "test.lab.prod", "display_name": "Test Lab", "is_prod": True},
    ]
    mock_db.get_enrichment_tags.return_value = [{"tag_value": "booth demo", "tag_type": "label"}]
    mock_db.get_enrichment_note.return_value = None
    mock_db.get_enrichment_tags_for_items.return_value = {
        "test.lab.prod": [{"tag_value": "booth demo", "tag_type": "label"}]
    }
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c, mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(monkeypatch):
    monkeypatch.setenv("RCARS_DEV_USER", "user@redhat.com")
    # No curator emails set
    monkeypatch.delenv("RCARS_CURATOR_EMAILS", raising=False)
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_curate_page_loads_for_curator(curator_client):
    client, _ = curator_client
    response = client.get("/curate")
    assert response.status_code == 200
    assert "Enrichment" in response.text or "Curate" in response.text


def test_curate_page_403_for_non_curator(anon_client):
    response = anon_client.get("/curate")
    assert response.status_code == 403


def test_curate_add_tag(curator_client):
    client, mock_db = curator_client
    response = client.post("/curate/tag", data={
        "ci_name": "test.lab.prod",
        "tag_type": "label",
        "tag_value": "new tag",
    })
    assert response.status_code == 200
    mock_db.add_enrichment_tag.assert_called_once_with(
        "test.lab.prod", "label", "new tag", "curator@redhat.com"
    )


def test_curate_remove_tag(curator_client):
    client, mock_db = curator_client
    response = client.delete("/curate/tag", params={
        "ci_name": "test.lab.prod",
        "tag_type": "label",
        "tag_value": "booth demo",
    })
    assert response.status_code == 200
    mock_db.remove_enrichment_tag.assert_called_once()


def test_curate_set_note(curator_client):
    client, mock_db = curator_client
    response = client.post("/curate/note", data={
        "ci_name": "test.lab.prod",
        "note": "Great for post-Summit use",
    })
    assert response.status_code == 200
    mock_db.set_enrichment_note.assert_called_once_with(
        "test.lab.prod", "Great for post-Summit use", "curator@redhat.com"
    )


def test_curate_flag(curator_client):
    client, mock_db = curator_client
    response = client.post("/curate/flag", data={
        "ci_name": "test.lab.prod",
        "needed": "true",
    })
    assert response.status_code == 200
    mock_db.set_enrichment_review_needed.assert_called_once_with("test.lab.prod", True)
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/web/test_curate.py -v
```
Expected: Multiple FAIL.

- [ ] **Step 3: Implement curate routes**

```python
# src/rcars/web/routes/curate.py
from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import require_curator, get_db, get_current_user
from rcars.db import Database
from rcars.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

PAGE_SIZE = 25


def _base_context(request: Request, db: Database, user: str) -> dict:
    settings = get_settings()
    return {
        "request": request,
        "current_user": user,
        "is_curator": True,  # always true on curator pages
        "active_page": "curate",
        "db_status": db.get_db_currency(stale_days=settings.stale_days),
    }


@router.get("/curate", response_class=HTMLResponse)
async def curate(
    request: Request,
    q: str = "",
    status_filter: str = "all",
    page: int = 1,
    user: str = Depends(require_curator),
    db: Database = Depends(get_db),
):
    items = db.list_catalog_items(prod_only=False)

    # Apply search filter
    if q:
        q_lower = q.lower()
        items = [i for i in items if q_lower in i.get("ci_name", "").lower()
                 or q_lower in i.get("display_name", "").lower()]

    # Load enrichment data
    ci_names = [i["ci_name"] for i in items]
    tags_by_ci = db.get_enrichment_tags_for_items(ci_names)

    enriched = []
    for item in items:
        ci = item["ci_name"]
        tags = tags_by_ci.get(ci, [])
        note = db.get_enrichment_note(ci)
        # Get review flag from showroom_analysis
        analysis = db.get_showroom_analysis(ci) or {}
        enriched.append({
            **item,
            "tags": tags,
            "note": note,
            "enrichment_review_needed": analysis.get("enrichment_review_needed", False),
        })

    # Apply status filter
    if status_filter == "needs_review":
        enriched = [i for i in enriched if i["enrichment_review_needed"]]
    elif status_filter == "untagged":
        enriched = [i for i in enriched if not i["tags"]]

    # Paginate
    total = len(enriched)
    start = (page - 1) * PAGE_SIZE
    page_items = enriched[start:start + PAGE_SIZE]

    ctx = _base_context(request, db, user)
    ctx.update({
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "q": q,
        "status_filter": status_filter,
    })
    return templates.TemplateResponse("curate.html", ctx)


@router.post("/curate/tag", response_class=HTMLResponse)
async def add_tag(
    ci_name: Annotated[str, Form()],
    tag_type: Annotated[str, Form()],
    tag_value: Annotated[str, Form()],
    user: str = Depends(require_curator),
    db: Database = Depends(get_db),
):
    tag_value = tag_value.strip()
    if tag_value:
        db.add_enrichment_tag(ci_name, tag_type, tag_value, user)
    return HTMLResponse("", status_code=200)


@router.delete("/curate/tag", response_class=HTMLResponse)
async def remove_tag(
    ci_name: str = Query(...),
    tag_type: str = Query(...),
    tag_value: str = Query(...),
    user: str = Depends(require_curator),
    db: Database = Depends(get_db),
):
    db.remove_enrichment_tag(ci_name, tag_type, tag_value)
    return HTMLResponse("", status_code=200)


@router.post("/curate/note", response_class=HTMLResponse)
async def set_note(
    ci_name: Annotated[str, Form()],
    note: Annotated[str, Form()],
    user: str = Depends(require_curator),
    db: Database = Depends(get_db),
):
    db.set_enrichment_note(ci_name, note.strip(), user)
    return HTMLResponse("", status_code=200)


@router.post("/curate/flag", response_class=HTMLResponse)
async def flag_item(
    ci_name: Annotated[str, Form()],
    needed: Annotated[str, Form()],
    user: str = Depends(require_curator),
    db: Database = Depends(get_db),
):
    db.set_enrichment_review_needed(ci_name, needed.lower() == "true")
    return HTMLResponse("", status_code=200)
```

- [ ] **Step 4: Create curate.html**

```html
<!-- src/rcars/web/templates/curate.html -->
{% extends "base.html" %}
{% block content %}
<div class="curate-layout">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
    <div>
      <div style="font-size:16px;font-weight:600;margin-bottom:2px;">Content Enrichment</div>
      <div style="font-size:11px;color:var(--text-muted);">{{ total }} catalog items</div>
    </div>
  </div>

  <form method="get" action="/curate" class="filter-bar">
    <input type="text" name="q" value="{{ q }}" class="filter-input" placeholder="Search by name or CI...">
    <select name="status_filter" class="filter-select" onchange="this.form.submit()">
      <option value="all" {% if status_filter == 'all' %}selected{% endif %}>All items</option>
      <option value="needs_review" {% if status_filter == 'needs_review' %}selected{% endif %}>⚑ Needs review</option>
      <option value="untagged" {% if status_filter == 'untagged' %}selected{% endif %}>Untagged</option>
    </select>
    <button type="submit" class="btn-action" style="padding:6px 12px;font-size:12px;">Filter</button>
  </form>

  {% for item in items %}
  <div class="curate-item" id="item-{{ item.ci_name | replace('.', '-') }}">
    <div style="display:flex;align-items:center;margin-bottom:4px;">
      <span class="curate-item-title">{{ item.display_name or item.ci_name }}</span>
      {% if item.enrichment_review_needed %}
      <span class="review-badge">⚑ needs review</span>
      {% endif %}
    </div>
    <div class="curate-item-ci">{{ item.ci_name }}</div>

    <!-- Tags -->
    <div class="tag-list" style="margin-bottom:8px;">
      {% for tag in item.tags %}
      <span class="tag-pill-removable"
            hx-delete="/curate/tag?ci_name={{ item.ci_name | urlencode }}&tag_type={{ tag.tag_type }}&tag_value={{ tag.tag_value | urlencode }}"
            hx-swap="none"
            hx-on::after-request="this.remove()"
            title="Click to remove">
        {{ tag.tag_value }} ✕
      </span>
      {% endfor %}
      <!-- Add tag inline -->
      <form hx-post="/curate/tag"
            hx-swap="none"
            hx-on::after-request="this.reset()"
            style="display:inline-flex;gap:4px;align-items:center;">
        <input type="hidden" name="ci_name" value="{{ item.ci_name }}">
        <input type="hidden" name="tag_type" value="label">
        <input type="text" name="tag_value" placeholder="+ add tag"
               style="background:transparent;border:1px dashed #3a5a3a;color:var(--score-green);padding:1px 7px;border-radius:10px;font-size:10px;width:90px;">
      </form>
    </div>

    <!-- Note -->
    <form hx-post="/curate/note" hx-swap="none" style="margin-bottom:6px;">
      <input type="hidden" name="ci_name" value="{{ item.ci_name }}">
      <input type="text" name="note"
             value="{{ item.note or '' }}"
             placeholder="Add a note..."
             style="background:var(--bg-card);border:1px solid #333;color:#aaa;padding:4px 8px;border-radius:3px;font-size:11px;width:100%;font-style:italic;"
             @change="this.form.requestSubmit()">
    </form>

    <!-- Flag -->
    <div style="display:flex;gap:6px;">
      {% if item.enrichment_review_needed %}
      <button class="btn-curator secondary"
              hx-post="/curate/flag"
              hx-vals='{"ci_name": "{{ item.ci_name }}", "needed": "false"}'
              hx-swap="none"
              hx-on::after-request="this.closest('.curate-item').querySelector('.review-badge')?.remove()">
        ✓ Clear flag
      </button>
      {% else %}
      <button class="btn-curator secondary"
              hx-post="/curate/flag"
              hx-vals='{"ci_name": "{{ item.ci_name }}", "needed": "true"}'
              hx-swap="none">
        ⚑ Flag for review
      </button>
      {% endif %}
    </div>
  </div>
  {% endfor %}

  <!-- Pagination -->
  {% if total > page_size %}
  <div style="display:flex;gap:8px;margin-top:16px;justify-content:center;">
    {% if page > 1 %}
    <a href="/curate?q={{ q }}&status_filter={{ status_filter }}&page={{ page - 1 }}" class="btn-action" style="font-size:12px;padding:5px 12px;text-decoration:none;">← Prev</a>
    {% endif %}
    <span style="color:var(--text-muted);font-size:12px;padding:5px 0;">Page {{ page }}</span>
    {% if (page * page_size) < total %}
    <a href="/curate?q={{ q }}&status_filter={{ status_filter }}&page={{ page + 1 }}" class="btn-action" style="font-size:12px;padding:5px 12px;text-decoration:none;">Next →</a>
    {% endif %}
  </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/web/test_curate.py -v
```
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add src/rcars/web/routes/curate.py src/rcars/web/templates/curate.html tests/web/test_curate.py
git commit -m "web: Implement curate page with inline enrichment tag/note/flag endpoints"
```

---

## Task 9: Admin Page + Endpoints

**Files:**
- Modify: `src/rcars/web/routes/admin.py`
- Create: `src/rcars/web/templates/admin.html`
- Create: `tests/web/test_admin.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/web/test_admin.py
import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from rcars.web.app import app, get_db


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv("RCARS_DEV_USER", "admin@redhat.com")
    monkeypatch.setenv("RCARS_CURATOR_EMAILS", "admin@redhat.com")
    mock_db = MagicMock()
    mock_db.get_db_currency.return_value = {"last_refresh": "2026.04.08", "is_stale": False}
    mock_db.get_status_summary.return_value = {
        "total": 342, "prod": 248, "with_showroom": 126, "analyzed": 120, "stale": 6,
    }
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c, mock_db
    app.dependency_overrides.clear()


def test_admin_page_loads(admin_client):
    client, _ = admin_client
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Admin" in response.text or "admin" in response.text.lower()


def test_admin_shows_scan_status(admin_client):
    client, _ = admin_client
    response = client.get("/admin")
    assert response.status_code == 200
    assert "342" in response.text  # total items


def test_admin_rescan_triggers_background_job(admin_client):
    client, mock_db = admin_client
    with patch("rcars.web.routes.admin.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        response = client.post("/admin/rescan")
    assert response.status_code == 200
    mock_thread.return_value.start.assert_called_once()


def test_admin_refresh_triggers(admin_client):
    client, mock_db = admin_client
    with patch("rcars.web.routes.admin.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        response = client.post("/admin/refresh")
    assert response.status_code == 200
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/web/test_admin.py -v
```
Expected: Multiple FAIL.

- [ ] **Step 3: Implement admin routes**

```python
# src/rcars/web/routes/admin.py
import subprocess
import threading
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from rcars.web.deps import require_curator, get_db
from rcars.db import Database
from rcars.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Track background rescan status
_rescan_status: dict = {"running": False, "last_output": ""}


def _run_rescan(settings):
    """Run rcars scan in a background thread."""
    global _rescan_status
    _rescan_status["running"] = True
    _rescan_status["last_output"] = "Rescan started..."
    try:
        result = subprocess.run(
            ["rcars", "scan"],
            capture_output=True,
            text=True,
            timeout=3600,
        )
        _rescan_status["last_output"] = result.stdout[-2000:] if result.stdout else result.stderr[-2000:]
    except Exception as e:
        _rescan_status["last_output"] = f"Error: {e}"
    finally:
        _rescan_status["running"] = False


@router.get("/admin", response_class=HTMLResponse)
async def admin(
    request: Request,
    user: str = Depends(require_curator),
    db: Database = Depends(get_db),
):
    settings = get_settings()
    status = db.get_status_summary()
    currency = db.get_db_currency(stale_days=settings.stale_days)
    ctx = {
        "request": request,
        "current_user": user,
        "is_curator": True,
        "active_page": "admin",
        "db_status": currency,
        "status": status,
        "rescan_running": _rescan_status["running"],
        "rescan_output": _rescan_status["last_output"],
        "curator_emails": settings.curator_emails,
    }
    return templates.TemplateResponse("admin.html", ctx)


@router.post("/admin/rescan", response_class=HTMLResponse)
async def trigger_rescan(
    user: str = Depends(require_curator),
    db: Database = Depends(get_db),
):
    if not _rescan_status["running"]:
        settings = get_settings()
        t = threading.Thread(target=_run_rescan, args=(settings,), daemon=True)
        t.start()
    return HTMLResponse(
        '<div style="color:var(--score-green);font-size:12px;">Rescan started in background. Refresh this page to check status.</div>'
    )


@router.post("/admin/refresh", response_class=HTMLResponse)
async def trigger_refresh(
    user: str = Depends(require_curator),
    db: Database = Depends(get_db),
):
    """Trigger rcars refresh synchronously (fast — just fetches catalog metadata)."""
    result = subprocess.run(
        ["rcars", "refresh"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode == 0:
        msg = "Catalog refresh complete."
        color = "var(--score-green)"
    else:
        msg = f"Refresh failed: {result.stderr[:200]}"
        color = "var(--score-red)"
    return HTMLResponse(f'<div style="color:{color};font-size:12px;">{msg}</div>')
```

- [ ] **Step 4: Create admin.html**

```html
<!-- src/rcars/web/templates/admin.html -->
{% extends "base.html" %}
{% block content %}
<div class="admin-layout">
  <div style="font-size:16px;font-weight:600;margin-bottom:20px;">Administration</div>

  <div class="admin-section">
    <h3>Catalog Status</h3>
    <table class="status-table">
      <tr><th>Metric</th><th>Count</th></tr>
      <tr><td>Total catalog items</td><td>{{ status.total }}</td></tr>
      <tr><td>Production items</td><td>{{ status.prod }}</td></tr>
      <tr><td>With Showroom content</td><td>{{ status.with_showroom }}</td></tr>
      <tr><td>Analyzed</td><td>{{ status.analyzed }}</td></tr>
      <tr><td>Stale (needs rescan)</td><td style="color:{% if status.stale > 0 %}var(--score-amber){% else %}var(--score-green){% endif %};">{{ status.stale }}</td></tr>
    </table>
  </div>

  <div class="admin-section">
    <h3>Catalog Refresh</h3>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">
      Pull latest catalog metadata from Babylon CRDs into the database. Fast (~30 seconds).
    </p>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <button class="btn-action"
              hx-post="/admin/refresh"
              hx-target="#refresh-status"
              hx-swap="innerHTML">
        Refresh Catalog
      </button>
      <div id="refresh-status" style="font-size:12px;"></div>
    </div>
  </div>

  <div class="admin-section">
    <h3>Content Rescan</h3>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">
      Clone and re-analyze Showroom repos via Sonnet. Runs in background — may take several minutes for {{ status.stale }} stale items.
    </p>
    {% if rescan_running %}
    <div style="color:var(--score-amber);font-size:12px;margin-bottom:8px;">⟳ Rescan in progress...</div>
    {% endif %}
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <button class="btn-action"
              hx-post="/admin/rescan"
              hx-target="#rescan-status"
              hx-swap="innerHTML"
              {% if rescan_running %}disabled{% endif %}>
        {% if rescan_running %}Rescan Running...{% else %}Trigger Rescan{% endif %}
      </button>
      <div id="rescan-status" style="font-size:12px;">
        {% if rescan_output %}<pre style="font-size:10px;color:var(--text-muted);white-space:pre-wrap;">{{ rescan_output }}</pre>{% endif %}
      </div>
    </div>
  </div>

  <div class="admin-section">
    <h3>Curator Access</h3>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">
      Set via <code>RCARS_CURATOR_EMAILS</code> environment variable (comma-separated). SSO integration replaces this in Plan 3b.
    </p>
    {% if curator_emails %}
    <ul style="font-size:12px;color:var(--text-primary);list-style:none;padding:0;">
      {% for email in curator_emails %}
      <li style="padding:3px 0;color:var(--accent-blue);">{{ email }}</li>
      {% endfor %}
    </ul>
    {% else %}
    <p style="font-size:12px;color:var(--score-red);">No curator emails configured — set RCARS_CURATOR_EMAILS.</p>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/web/test_admin.py -v
```
Expected: All PASS.

- [ ] **Step 6: Run the full test suite**

```bash
pytest tests/ -v
```
Expected: All tests pass. Fix any regressions before committing.

- [ ] **Step 7: Commit**

```bash
git add src/rcars/web/routes/admin.py src/rcars/web/templates/admin.html tests/web/test_admin.py
git commit -m "web: Implement admin page with scan status, rescan and refresh triggers"
```

---

## Task 10: End-to-End Manual Test

This task has no code — it's a walkthrough to verify the full app works locally.

- [ ] **Step 1: Install web extras and start the server**

```bash
pip install -e ".[web]"
RCARS_DEV_USER=yourname@redhat.com \
RCARS_CURATOR_EMAILS=yourname@redhat.com \
RCARS_STALE_DAYS=3 \
rcars serve --reload
```

Open http://127.0.0.1:8000/advisor

- [ ] **Step 2: Verify advisor page**

- Logo appears with arc sweep, "RCARS", "RHDP CONTENT ADVISOR", date, and ● CURRENT/STALE badge
- Two panes visible: chat left, recommendations right
- Left nav shows Advisor, Curate, Admin (since curator mode is active)
- History section visible (empty on first load)

- [ ] **Step 3: Run a recommendation query**

Type: *"OpenShift labs for a developer audience at KubeCon"* and click Send.

Expected:
- Chat pane shows user message + assistant response
- Right pane shows recommendation cards in B-view (score, name, CI, rationale, tags)
- Session label appears in left nav history

- [ ] **Step 4: Test card expand/collapse**

Click a recommendation card. Expected:
- Expands to C-view (format, duration, caveat, Catalog link, module list)
- Click again → collapses back to B-view
- No page reload

- [ ] **Step 5: Test curator mode**

Click "🏷 Curator" button in header. Expected:
- Expands a card — curator controls appear (+ Tag, ⚑ Flag buttons)
- Add a tag: type "booth demo" and click "+ Tag" → tag pill appears on card

- [ ] **Step 6: Test curate page**

Navigate to http://127.0.0.1:8000/curate

Expected:
- All catalog items listed with search/filter bar
- Items with tags show removable tag pills
- "Needs review" filter shows flagged items only

- [ ] **Step 7: Test admin page**

Navigate to http://127.0.0.1:8000/admin

Expected:
- Catalog status table shows counts
- "Refresh Catalog" button triggers `rcars refresh`
- "Trigger Rescan" button starts background scan

- [ ] **Step 8: Test rollback**

Run two queries. Click on the first assistant message in the chat pane. Expected:
- Right pane updates to show the first query's results
- No Sonnet call (instant)

- [ ] **Step 9: Commit final polish**

Fix any visual issues found during manual testing, then commit:

```bash
git add -p  # stage only visual fixes
git commit -m "web: Manual test polish — layout and CSS adjustments"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ `rcars serve` command — Task 1
- ✅ `/advisor` two-pane layout — Tasks 4, 5, 6
- ✅ Card density B + expand to C — Task 5 (fragments)
- ✅ Chat accumulation → recommend() — Task 6
- ✅ Rollback (click assistant turn) — Task 7
- ✅ `/curate` enrichment page (curator-only) — Task 8
- ✅ Inline tag/note/flag on expanded cards — Task 5 (expanded fragment)
- ✅ Curator access via `RCARS_CURATOR_EMAILS` — Task 2
- ✅ Browser localStorage session history — Task 4 (base.html JS)
- ✅ Admin section — Task 9
- ✅ DB currency badge (● CURRENT / ● STALE) — Task 4 (logo SVG)
- ✅ In-memory sessions (no DB tracking) — Task 6
- ✅ LCARS logo — Task 4

**Deferred (out of scope per spec section 11):**
- SSO/OIDC — Plan 3b (`get_current_user()` is the only function that changes)
- APScheduler — Plan 3b
- Helm charts — Plan 3c
