# RCARS Plan 3a — Web UI Design Spec

**Date:** 2026-04-08  
**Status:** Approved for implementation  
**Scope:** Web application + enrichment UI (local testing). SSO, scheduler, Helm deferred to Plans 3b/3c.

---

## 1. Overview

Plan 3a adds a FastAPI web application to the existing RCARS CLI project. The web UI exposes the same recommendation engine built in Plan 2 through a conversational two-pane interface, and adds a curator enrichment workflow. It runs locally first; OpenShift deployment is Plan 3c.

**What Plan 3a ships:**
- `rcars serve` CLI command to start the app locally
- `/advisor` — two-pane chat + recommendation interface
- `/curate` — enrichment management page (curator-only)
- `/admin` — operational controls (rescan trigger, scan status, curator management)
- LCARS-inspired logo with live DB currency status
- Enrichment tag inline editing on expanded recommendation cards

**What is deferred:**
- Red Hat SSO (Plan 3b) — curator access via `RCARS_CURATOR_EMAILS` env var for now
- APScheduler automated rescans (Plan 3b)
- Helm charts and OpenShift deployment (Plan 3c)
- Documentation (Plan 3c)

---

## 2. Stack

| Layer | Choice | Rationale |
|---|---|---|
| Framework | FastAPI | Already in project, async, Jinja2 templates built-in |
| Dynamic UI | HTMX | Server-rendered HTML fragments, no build step, no SPA complexity |
| UI micro-state | Alpine.js (CDN, 15KB) | Card expand/collapse and curator mode toggle without round-trips |
| Templating | Jinja2 | FastAPI native, logo SVG embeds directly |
| CSS | Custom dark theme | No external CSS framework dependency; easy to iterate |
| Database | PostgreSQL (existing) | Adds `conversations` and `enrichment_tags` tables |

The web module lives at `src/rcars/web/` and imports directly from the existing `rcars` package (db, recommender, config).

---

## 3. Visual Design

### Theme
Dark background (`#0f1117`), light text, colour-coded recommendation scores:
- `≥80%` → green (`#5cb85c`)
- `50–79%` → amber (`#e8a838`)
- `<50%` → red (`#c9190b`)

Enrichment tags: green pills on dark green background. Lifecycle tags (retiring, new): red/blue pills. All font: system sans-serif stack.

### Logo
LCARS-inspired SVG embedded directly in the Jinja2 base template. No image files — scales perfectly at any size.

Structure: quarter-circle amber arc (left) + three segmented header bars (amber / tan / purple) + two dark content bars.

Content:
- Header bar: **RCARS** (black text on amber, bold, letter-spaced)
- Middle bar: **RHDP CONTENT ADVISOR** (amber text on dark)
- Bottom bar: `2026.04.08` (date) + currency badge

Currency badge (server-rendered conditionally):
- **● CURRENT** — green badge (`#0d3a0d` background, `#5cb85c` text) — last `rcars refresh` within `RCARS_STALE_DAYS` (default: 3)
- **● STALE** — red badge (`#3a0d0d` background, `#c9190b` text) — older than threshold

---

## 4. Application Structure

```
src/rcars/web/
├── __init__.py
├── app.py              # FastAPI app factory, mounts routes
├── routes/
│   ├── advisor.py      # /advisor, /advisor/query, /advisor/card/{ci_name}
│   ├── curate.py       # /curate, /curate/tag, /curate/note, /curate/flag
│   └── admin.py        # /admin, /admin/rescan, /admin/status
├── templates/
│   ├── base.html       # Logo SVG, nav, Alpine.js/HTMX CDN links, dark CSS
│   ├── advisor.html    # Two-pane layout
│   ├── curate.html     # Enrichment management page
│   ├── admin.html      # Admin controls
│   └── fragments/
│       ├── rec_card.html        # Single recommendation card (B view)
│       ├── rec_card_expanded.html  # Expanded card (C view + curator controls)
│       ├── rec_list.html        # Full recommendations pane
│       └── chat_turn.html       # Single conversation turn
└── static/
    └── rcars.css       # Dark theme, card styles, tag pills, logo sizing
```

`src/rcars/cli.py` gains a `serve` command:
```
rcars serve [--host 0.0.0.0] [--port 8000] [--reload]
```

---

## 5. Page Layouts

### 5.1 `/advisor` — Two-pane layout

Always-split: no landing page transition. Chat pane left, recommendations right, present from first load.

```
┌─────────────────────────────────────────────────────────────┐
│ [RCARS logo + currency badge]              [user] [curator?] │
├──────────────────────┬──────────────────────────────────────┤
│ 💬 Advisor           │                                      │
│ 🏷 Curate            │  CONVERSATION         RECOMMENDATIONS │
│ ⚙ Admin              │                                      │
│ ─────────────────    │  [welcome message]    [rec card 1]   │
│ HISTORY              │  [user turn]          [rec card 2]   │
│ KubeCon dev labs     │  [asst turn ↩]        [rec card 3]   │
│ AAP booth demos      │  [user refinement]                   │
│ RHEL 45min workshop  │  [asst turn ↩]    [+ New session]    │
│                      │  [input          ] [Send]            │
└──────────────────────┴──────────────────────────────────────┘
```

**Left nav sections:**
- `💬 Advisor` — active page indicator
- `🏷 Curate` — only visible to curators
- `⚙ Admin` — only visible to curators/admins
- `HISTORY` — recent sessions from browser `localStorage` (never server-stored)

**Session history:** Stored in `localStorage` under `rcars_sessions`. Each entry: `{id, label, timestamp}`. Label = first 40 chars of the user's first message. Clicking a history entry restores that session from the server (session ID passed as query param). History is per-browser, never tracked server-side.

**Conversation turns:** Each assistant turn renders with a faint `↩ click to restore` hint. Clicking an assistant turn re-fetches that turn's recommendation set via `GET /advisor/restore/{session_id}/{turn_index}` and swaps the recommendations pane — the rollback mechanism.

**Input:** Text area + Send button. `hx-post="/advisor/query"` targeting the recommendations pane and appending a new turn to the chat pane.

### 5.2 Recommendation Cards

**Default (B view):** Score, name, CI name, format, duration, difficulty, 1–2 sentence rationale, enrichment tags. `▸` expand indicator.

**Expanded (C view):** All of B + caveat, catalog link, module list. Curator controls visible if curator mode is active (Alpine.js `curatorMode` state).

**Curator controls (expanded card, curator mode on):**
- `+ Tag` — inline tag input, submits via `hx-post="/curate/tag"`
- `+ Note` — textarea inline, submits via `hx-post="/curate/note"`
- `⚑ Flag` — marks `enrichment_review_needed = true`

Card expand/collapse is client-side via Alpine.js `x-show` — no round-trip for the toggle. The expanded content is pre-rendered server-side in the card fragment and hidden until clicked.

### 5.3 `/curate` — Enrichment management

Curator-only page (redirects non-curators to `/advisor`).

Features:
- Filter bar: text search, product dropdown, status filter (`All` / `⚑ Needs review` / `Untagged`)
- Paginated list of all 342 catalog items (not just current recommendation results)
- Per-item: inline tag add/remove, note edit, flag/unflag
- Tags display as coloured removable pills; `✕` on each submits `DELETE /curate/tag`
- Bulk actions: "Clear all flags", "Export tagged items as CSV"

### 5.4 `/admin` — Admin controls

Curator-only. Sections:
- **Scan status:** Table showing items pending scan, last scan timestamp, failure count
- **Trigger rescan:** Button → `hx-post="/admin/rescan"` runs `rcars scan` in a background thread, streams progress via SSE to a status div
- **Curator access:** List of emails in `RCARS_CURATOR_EMAILS`; note that SSO replaces this in Plan 3b
- **DB currency:** Shows last refresh date, manual `rcars refresh` trigger button

---

## 6. Data Model Additions

New tables added via `rcars init-db` (extends the existing schema management command).

### Conversation storage — in-memory (Plan 3a)

Conversations are stored in a server-side Python dict keyed by `session_id`. No conversation content is written to the database in Plan 3a.

```python
# In-memory store in app.py
_conversations: dict[str, list[dict]] = {}
# Each entry: [{role, content, rec_ci_names}, ...]
```

**Why in-memory:** Avoids persisting user query text entirely — no audit trail, no retention concerns. Sessions survive for the lifetime of the `rcars serve` process; a server restart clears them. For local testing this is acceptable. Plan 3b can introduce DB-backed sessions with an explicit retention policy if needed.

**Implication for rollback:** Rollback works within a server session. If the server restarts, localStorage history entries become dead links (the label still displays, the session is gone). This is acceptable for Plan 3a.

### `enrichment_tags`
```sql
CREATE TABLE enrichment_tags (
    id          SERIAL PRIMARY KEY,
    ci_name     TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    tag         TEXT NOT NULL,
    added_by    TEXT,           -- email from RCARS_CURATOR_EMAILS (SSO subject in Plan 3b)
    added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ci_name, tag)       -- union semantics, no duplicates
);

CREATE TABLE enrichment_notes (
    id          SERIAL PRIMARY KEY,
    ci_name     TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    note        TEXT NOT NULL,
    added_by    TEXT,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`enrichment_review_needed` flag is added to `showroom_analysis`:
```sql
ALTER TABLE showroom_analysis ADD COLUMN enrichment_review_needed BOOLEAN NOT NULL DEFAULT FALSE;
```

---

## 7. Recommendation Flow (Web)

```
User types message → POST /advisor/query
  │
  ├── Load conversation from in-memory store by session_id
  ├── Append user turn to conversation
  ├── Build description = join all turn contents (accumulated context)
  ├── Call recommend(description, limit=10) [Plan 2 recommender]
  │     └── pgvector search → top 15 → Sonnet ranking → results
  ├── Append assistant turn (summary + rec_ci_names snapshot)
  ├── Update in-memory store (no DB write)
  └── Return two HTMX fragments:
        - chat_turn.html (new user + assistant turns) → appended to #chat-pane
        - rec_list.html (recommendation cards) → swapped into #rec-pane
```

**Rollback:** `GET /advisor/restore/{session_id}/{turn_index}` re-fetches the `rec_ci_names` from the stored turn, loads those catalog items from the DB, and re-renders `rec_list.html` — no Sonnet call required.

**Cost:** Each user message = 1 Sonnet call regardless of catalog size. Rollback = 0 Sonnet calls.

---

## 8. Curator Access Control

Plan 3a uses a simple email-list check. The authenticated user's identity comes from an HTTP header (for local dev, a `RCARS_DEV_USER` env var that fakes the header).

```python
# settings.py addition
curator_emails: list[str] = Field(default_factory=list, env="RCARS_CURATOR_EMAILS")
dev_user: str | None = Field(default=None, env="RCARS_DEV_USER")

def is_curator(self, email: str) -> bool:
    return email.lower() in [e.lower() for e in self.curator_emails]
```

A FastAPI dependency `get_current_user()` reads the user identity from the request header (or `RCARS_DEV_USER` in dev mode) and attaches it to every request. Pages that require curator access call `require_curator()` which raises HTTP 403 for non-curators.

Plan 3b replaces this with Red Hat SSO OIDC — the `get_current_user()` dependency is the only thing that changes.

---

## 9. DB Currency Logic

```python
def get_db_status(settings: Settings, db_conn) -> dict:
    last_refresh = db_conn.execute(
        "SELECT MAX(updated_at) FROM catalog_items"
    ).scalar()
    stale_threshold = timedelta(days=settings.stale_days)  # default 3
    is_stale = (datetime.utcnow() - last_refresh) > stale_threshold
    return {
        "last_refresh": last_refresh.strftime("%Y.%m.%d"),
        "is_stale": is_stale,
    }
```

This is injected into every page render via a Jinja2 global context processor. The logo SVG conditionally renders `● CURRENT` (green) or `● STALE` (red).

---

## 10. `rcars serve` Command

Added to `src/rcars/cli.py`:

```
rcars serve [--host TEXT]   Host to bind (default: 127.0.0.1)
            [--port INT]    Port (default: 8000)
            [--reload]      Enable auto-reload for development
```

Internally calls `uvicorn.run("rcars.web.app:app", ...)`. Uvicorn is added as a dependency in `pyproject.toml` under `[web]` extras alongside `fastapi`, `htmx` (no package — just CDN), `python-multipart`.

---

## 11. Out of Scope for Plan 3a

| Feature | Plan |
|---|---|
| Red Hat SSO / OIDC authentication | 3b |
| APScheduler automated daily rescans | 3b |
| Helm charts for OpenShift | 3c |
| User documentation | 3c |
| Catalog browse page (all items, not just recs) | TBD |
| Export / report generation | TBD |

---

## 12. Testing Plan

- Unit tests for new route handlers (mock DB, mock recommender)
- Integration test: full advisor query flow against test PostgreSQL
- Manual local testing: `rcars serve --reload`, run queries, verify enrichment tag persistence
- Curator mode: set `RCARS_CURATOR_EMAILS=your@email.com RCARS_DEV_USER=your@email.com`
