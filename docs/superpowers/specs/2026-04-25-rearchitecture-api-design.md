# RCARS Rearchitecture & API Design

**Date:** 2026-04-25
**Status:** Design approved, pending implementation

## Summary

Break the RCARS monolith into three tiers — a React frontend, a FastAPI JSON API, and arq background workers — connected by Redis for task queuing and real-time progress streaming. The result: frontend changes build in ~30 seconds (down from ~10 minutes), a clean REST API that external consumers like Publishing House can call, and an architecture that scales horizontally for the workload growth we know is coming.

This is a clean-break rebuild. The LCARS visual identity, recommendation card design (green/yellow/white tiers), and token usage data are preserved. Everything else is rebuilt from scratch.

---

## Why Now

Every UI change — a CSS tweak, a template string, a card layout adjustment — triggers a full Docker build that downloads ML model weights and installs the entire Python backend. This takes ~10 minutes. For a tool under active UI development, this is not workable.

Publishing House needs to query RCARS for content vetting and prototyping workflows. Today there is no API — everything is HTML-over-HTMX, unusable by a programmatic client. PH and RCARS sit on the same OpenShift cluster and will become tightly integrated.

The current single-process architecture also limits scale. LLM calls (Sonnet rationale, Haiku triage) run in the request path. Under concurrent load, the API process bogs down and even simple page loads slow. Moving heavy work to background workers keeps the API responsive and lets workers scale independently.

---

## Architecture

### System Components

Four components, three container images, one database. All containers use Red Hat UBI base images:

| Component | Image | Base | Role |
|---|---|---|---|
| **Frontend** | `rcars-frontend` | `registry.access.redhat.com/ubi9/nginx-122` | Vite + React SPA, LCARS theme, SSE consumer |
| **API** | `rcars-api` | `registry.access.redhat.com/ubi9/python-311` | JSON REST API, SSE relay, auth middleware, job orchestration |
| **Workers** | `rcars-api` (same image, different entrypoint) | (shares API image) | arq workers — LLM operations, Showroom cloning, content analysis, scanning |
| **Redis** | `rcars-redis` | `registry.redhat.io/rhel9/redis-7` | Task queue, pub/sub for real-time progress, caching, LLM rate limiting |
| **PostgreSQL** | existing `rcars-db` | (existing, unchanged) | All persistent state — catalog, analysis, embeddings, sessions, token usage, jobs |

Workers use the same container image as the API. The only difference is the entrypoint: the API runs `uvicorn`, workers run `arq`. No separate build. The sentence-transformers model (`all-MiniLM-L6-v2`) is baked into this shared image — it's needed by workers for embedding generation and by the API for query embedding during vector search.

### CLI Tool

The `rcars` CLI continues to exist as an ops tool for running commands directly in the API/worker pod. In the new architecture, commands that trigger heavy operations enqueue arq jobs rather than running inline. Lightweight commands query the database directly.

**Operations:**

- `rcars status` — catalog/analysis summary stats (direct DB read)
- `rcars refresh` — enqueue catalog sync from Babylon CRDs
- `rcars scan [--max N]` — enqueue scan of unanalyzed items
- `rcars check-stale` — enqueue stale content detection

**Curation (direct DB writes, no worker needed):**

- `rcars tag <ci_name> <type> <value>` — add enrichment tag
- `rcars untag <ci_name> <type> <value>` — remove enrichment tag
- `rcars note <ci_name> "text"` — set curator note
- `rcars flag <ci_name>` — flag for enrichment review
- `rcars override-url <ci_name> <url>` — override Showroom URL
- `rcars set-content-path <ci_name> <path>` — set custom content path for non-standard repos

Curation CLI commands enable batch operations — e.g., tagging all RHEL items via a shell loop or scripted workflow.

### System Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│  RHDP Infrastructure                                                     │
│                                                                          │
│  Babylon K8s Cluster            Showroom Git Repos                       │
│  ┌──────────────────────────┐   ┌──────────────────┐                    │
│  │ AgnosticVComponent       │   │ .adoc lab content │                    │
│  │ CatalogItem CRDs         │   │ (Antora layout)  │                    │
│  └────────────┬─────────────┘   └────────┬─────────┘                    │
└───────────────┼──────────────────────────┼──────────────────────────────┘
                │                          │
                ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  OpenShift — rcars namespace                                             │
│                                                                          │
│  ┌─────────────────────────────────────┐                                │
│  │  rcars-frontend (UBI nginx)         │                                │
│  │  React SPA + LCARS theme            │                                │
│  │  /api/* → proxy to rcars-api svc    │                                │
│  │  OAuth proxy sidecar on Route       │                                │
│  └──────────────┬──────────────────────┘                                │
│                 │ /api/v1/*                                              │
│  ┌──────────────▼──────────────────────┐    ┌────────────────────────┐  │
│  │  rcars-api (FastAPI)                │    │  rcars-worker (arq)    │  │
│  │                                     │    │                        │  │
│  │  REST endpoints + SSE streaming     │    │  Recommender pipeline  │  │
│  │  Auth middleware                    │    │  Showroom analyzer     │  │
│  │  Job creation + result relay        │    │  Catalog scanner       │  │
│  │  Swagger docs at /api/v1/docs       │    │  Stale checker         │  │
│  └──────┬──────────────┬───────────────┘    └───┬──────────┬─────────┘  │
│         │              │                        │          │            │
│         │ SQL/pgvector │ enqueue/subscribe      │ dequeue  │ SQL/write  │
│         │              │                        │ publish  │            │
│         ▼              ▼                        ▼          ▼            │
│  ┌──────────────────┐  ┌────────────────────────────────────────────┐   │
│  │  PostgreSQL      │  │  Redis                                    │   │
│  │  + pgvector      │  │                                           │   │
│  │                  │  │  Task queues: recommend, analyze, ops     │   │
│  │  catalog_items   │  │  Pub/sub channels: job:{id}               │   │
│  │  showroom_analysis  │  Cache + rate limiting                    │   │
│  │  embeddings      │  │                                           │   │
│  │  advisor_sessions│  │  API enqueues jobs + subscribes to        │   │
│  │  jobs            │  │  progress channels.                       │   │
│  │  token_usage     │  │  Workers dequeue jobs + publish progress. │   │
│  └──────────────────┘  │  No direct API ↔ worker communication.   │   │
│                        └────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  Service consumers (cluster-internal)                            │    │
│  │  Publishing House → rcars-api.rcars.svc:8080/api/v1/*           │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### Request Flows

**Browser user submits a recommendation query:**

1. Browser → nginx (serves React SPA from static files)
2. React app → `POST /api/v1/advisor/query` → API (proxied through nginx)
3. API validates auth (OAuth proxy headers), creates job record in PostgreSQL, enqueues task directly in Redis, returns `{job_id}`
4. React app opens `GET /api/v1/advisor/query/{job_id}/stream` (SSE connection)
5. API subscribes to Redis pub/sub channel `job:{job_id}` to relay progress
6. arq worker independently picks up job from Redis queue, begins pipeline execution
7. Worker publishes progress to Redis pub/sub channel `job:{job_id}` at each phase
8. API receives pub/sub messages and relays each as an SSE event to the browser
9. Worker writes final results to PostgreSQL, publishes `complete` event
10. React app renders results as they stream in — progress indicators in chat, rec cards in right panel

The API and worker never communicate directly. Both are Redis clients — the API enqueues and subscribes, the worker dequeues and publishes. Redis is the sole communication channel between them.

**Publishing House queries RCARS (cluster-internal):**

1. PH pod → `POST http://rcars-api.rcars.svc:8080/api/v1/advisor/query` (direct Service call, no Route)
2. Same flow from step 3 onward
3. PH can either stream via SSE or poll `GET /api/v1/advisor/query/{job_id}/result` for final results

**User browses the catalog:**

1. React app → `GET /api/v1/catalog?stage=prod&limit=50` → API
2. API queries PostgreSQL directly — no worker needed for reads
3. If user has curator role, edit controls render in the UI; API enforces role on write endpoints

---

## Workers & Task Queue

### Why arq

arq is a lightweight async task queue built on Redis. It matches FastAPI's async model natively — both use Python's `asyncio`, so task code is identical to the service layer code it replaces. No threading translation, no sync/async bridge.

arq was created by Samuel Colvin (the author of Pydantic, which FastAPI is also built on). It has a small API surface, clear documentation, and minimal operational overhead.

### How Workers Operate

Workers are long-running processes that poll Redis for queued tasks. When a task arrives, the worker executes it and publishes progress via Redis pub/sub. The API subscribes to the pub/sub channel for the relevant job and relays events to the browser via SSE.

Each worker runs in its own pod (or as one of several replicas in a Deployment). Workers are stateless — all state lives in PostgreSQL and Redis. Any worker can pick up any job. If a worker crashes mid-job, the job's status in PostgreSQL remains `running` and can be detected as stale by a health check.

### Queue Specialization

Workers listen on one or more Redis queues. By default, a single worker handles all task types. As load patterns emerge, you can split into specialized workers by changing the startup command — no code changes required:

```yaml
# Generic worker — picks up everything
args: ["arq", "rcars.workers.WorkerSettings"]

# Recommendation-only worker
args: ["arq", "rcars.workers.WorkerSettings", "--queue", "recommend"]

# Scan/analysis-only worker
args: ["arq", "rcars.workers.WorkerSettings", "--queue", "scan"]
```

This is a deployment configuration change. The same container image serves all worker roles. Scale each Deployment independently — 1 recommendation worker and 3 scan workers during a bulk re-scan, for example.

### Task Types

Three queues, split by workload profile:

| Queue | Task | What it does | Profile |
|---|---|---|---|
| `recommend` | `run_recommendation` | Full 3-phase pipeline: vector search → Haiku triage → Sonnet rationale | LLM-heavy, user-facing latency |
| `analyze` | `run_analysis` | Clone Showroom repo, analyze with Sonnet, generate embeddings | LLM + I/O heavy, bulk |
| `analyze` | `run_single_analysis` | Curator-triggered analysis of one item | LLM + I/O, single item |
| `ops` | `run_catalog_refresh` | Sync catalog from Babylon CRDs | Lightweight, K8s API calls |
| `ops` | `run_stale_check` | Compare stored commit SHAs against current repo HEADs | Lightweight, git ls-remote |
| `ops` | `run_rescan_stale` | Re-analyze all items flagged as stale (enqueues individual analyze jobs) | Orchestrator |

The `analyze` queue gets its own split from `ops` because analysis tasks are LLM-heavy and long-running (30-60s each), while ops tasks are fast metadata operations. A bulk rescan shouldn't block a catalog refresh.

### Progress Streaming

Workers publish granular progress to Redis pub/sub as they execute. Each publish is a JSON message on channel `job:{job_id}`:

```json
{"phase": "vector_search", "status": "started"}
{"phase": "vector_search", "status": "complete", "candidates": 42}
{"phase": "triage", "status": "started", "total": 42}
{"phase": "triage", "status": "progress", "current": 12, "total": 42}
{"phase": "triage", "status": "complete", "relevant": 8}
{"phase": "rationale", "status": "started", "top_n": 5}
{"phase": "rationale", "status": "progress", "current": 2, "top_n": 5}
{"phase": "rationale", "status": "complete"}
{"phase": "complete", "results": 5}
```

The API translates these into user-friendly SSE events for the browser:

| Worker publishes | Browser receives (SSE `data:`) |
|---|---|
| `phase: vector_search, complete, 42` | `Searching content library... found 42 candidates` |
| `phase: triage, progress, 12/42` | `Evaluating relevance (12 of 42)...` |
| `phase: triage, complete, 8` | `8 relevant items identified` |
| `phase: rationale, progress, 2/5` | `Generating detailed analysis (2 of 5)...` |
| `phase: complete` | `Complete` |

Worker log messages (structured JSON to stdout) and user-facing progress messages (via Redis pub/sub → SSE) are completely separate channels with different content. Operational logs are never shown to users.

---

## API Design

All endpoints live under `/api/v1/` and return JSON. Swagger UI is served at `/api/v1/docs`, ReDoc at `/api/v1/redoc`.

### Advisor

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/advisor/query` | Submit a recommendation query; returns `{job_id}` |
| `GET` | `/api/v1/advisor/query/{job_id}/stream` | SSE stream of progress + results |
| `GET` | `/api/v1/advisor/query/{job_id}/result` | Poll for final results (service clients) |
| `GET` | `/api/v1/advisor/sessions` | List user's past sessions |
| `GET` | `/api/v1/advisor/sessions/{session_id}` | Retrieve a full session (all turns) |
| `POST` | `/api/v1/advisor/sessions/{session_id}/select` | Log "this fits best" selection |

### Catalog

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/catalog` | List catalog items (filterable by stage, category, scope) |
| `GET` | `/api/v1/catalog/{ci_name}` | Full detail for one CI (analysis, tags, metadata) |
| `GET` | `/api/v1/catalog/{ci_name}/analysis` | Showroom analysis for a CI |
| `POST` | `/api/v1/catalog/refresh` | Trigger catalog sync from Babylon CRDs; returns `{job_id}` |
| `GET` | `/api/v1/catalog/stats` | Summary stats (total, scanned, stale, by stage) |

### Curation

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/catalog/{ci_name}/tags` | Curator | Add enrichment tag |
| `DELETE` | `/api/v1/catalog/{ci_name}/tags/{tag_id}` | Curator | Remove tag |
| `PUT` | `/api/v1/catalog/{ci_name}/note` | Curator | Set curator note |
| `POST` | `/api/v1/catalog/{ci_name}/flag` | Curator | Flag for review |
| `POST` | `/api/v1/catalog/{ci_name}/override-url` | Curator | Override Showroom URL |

### Analysis

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/analysis/scan` | Admin | Scan unanalyzed items; returns `{job_id}` |
| `POST` | `/api/v1/analysis/check-stale` | Admin | Detect stale content; returns `{job_id}` |
| `POST` | `/api/v1/analysis/rescan-stale` | Admin | Re-analyze stale items; returns `{job_id}` |
| `POST` | `/api/v1/analysis/{ci_name}` | Curator | Analyze a single CI; returns `{job_id}` |
| `GET` | `/api/v1/analysis/jobs/{job_id}/stream` | Any | SSE stream for any analysis job |

### Admin

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/admin/token-usage` | Admin | Token usage stats (filterable by date range, model, operation) |
| `GET` | `/api/v1/admin/jobs` | Admin | List recent jobs (status, duration, errors) |
| `GET` | `/api/v1/admin/workers` | Admin | Queue depths, active jobs, worker health metrics |
| `GET` | `/api/v1/health` | Public | Liveness probe |
| `GET` | `/api/v1/health/ready` | Public | Readiness probe (DB + Redis connected) |

### Auth

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/auth/me` | Current user identity + roles |

### API Patterns

- **Long-running operations** return `{job_id}` immediately. Clients choose SSE streaming or polling.
- **Error format:** `{"error": "message", "detail": "optional context"}` with HTTP status codes.
- **Pagination:** list endpoints support `?limit=` and `?offset=` with `{"items": [...], "total": N}`.
- **Role enforcement:** server-side on every request. Curator/admin endpoints return 403 for insufficient roles.
- **Extensible:** new capabilities (Showroom live-read, content comparison) are added as new route modules under the same `/api/v1/` prefix — same patterns, same auth, same job/streaming infrastructure.

---

## Frontend

### Tech Stack

- **Vite** — build tool with hot module replacement (sub-second refreshes during development)
- **React 19** — component framework
- **TypeScript** — type safety
- **Custom LCARS CSS** — ported from the current `rcars.css`, no external design system
- **React Router** — client-side page navigation

### Pages

| Route | Purpose | Access |
|---|---|---|
| `/` | Redirect to `/advisor` | All users |
| `/advisor` | Chat + recommendations (split panel) | All users |
| `/browse` | Catalog browsing + curation controls | All users; edit controls curator-only |
| `/admin` | Token usage, jobs, catalog refresh | Admin only |

### Advisor Layout

The advisor uses a split-panel layout: chat conversation on the left, recommendation cards on the right. Turn navigation lets users flip between previous result sets.

```
┌──────────────────────────────────────────────────────────────────┐
│  RCARS ▌ Advisor   Browse   Admin                                │
├─────────────────────────────┬────────────────────────────────────┤
│  CHAT                       │  RECOMMENDATIONS        Turn 1 ▸  │
│                             │                                    │
│  ┌─ user ────────────────┐  │  ┌─ green ──────────────────────┐  │
│  │ Find me content for a │  │  │ CNV Migration Workshop       │  │
│  │ 2-hour booth demo on  │  │  │ 92% match · prod · 2hr      │  │
│  │ OCP virtualization    │  │  │ [This fits best]             │  │
│  └───────────────────────┘  │  └──────────────────────────────┘  │
│                             │  ┌─ green ──────────────────────┐  │
│  ┌─ rcars ───────────────┐  │  │ OCP Virt Getting Started     │  │
│  │ ● Searching...        │  │  │ 87% match · prod · 1.5hr    │  │
│  │ ✓ 38 candidates       │  │  │ [This fits best]             │  │
│  │ ✓ 8 relevant          │  │  └──────────────────────────────┘  │
│  │ ✓ Top 5 analyzed      │  │                                    │
│  │                       │  │  ▸ Yellow (3 more)                 │
│  │ Found 5 strong matches│  │  ▸ White (30 more)                 │
│  │ for OCP virt booth    │  │                                    │
│  │ demos. The top pick...│  │                                    │
│  └───────────────────────┘  │                                    │
│                             │                                    │
│  ┌────────────────┐ [Send]  │                                    │
│  │ Follow up...    │        │                                    │
│  └────────────────┘         │                                    │
│  ☐ Don't save this query    │                                    │
└─────────────────────────────┴────────────────────────────────────┘
```

### Recommendation Cards

The rec card design from the existing spec carries forward as React components:

- **Green tier** — Sonnet-analyzed top picks. Green border/header. Sorted by `fit_score`.
- **Yellow tier** — Haiku-relevant but below Sonnet top-N cut. Amber border/header. Sorted by `relevance_score`.
- **White tier** — Vector search results, Haiku said not relevant. Neutral. Sorted by `vector_similarity_pct`.
- **Collapsible tiers** — green expanded by default, yellow and white collapsed with count.
- **"This fits best" button** — on green and yellow cards after `COMPLETE` phase. One selection per turn.
- **Live card promotion** — cards appear as white during vector search, promote to yellow at triage, promote to green at rationale. The right panel updates in real time.

### LCARS Component Library

A small set of styled React components that encapsulate the LCARS theme:

- `LcarsHeader` — top navigation bar with the LCARS sweep
- `LcarsCard` — base card component (used by rec cards, catalog items)
- `LcarsButton` — styled buttons
- `LcarsInput` — form inputs and text areas
- `LcarsBadge` — tier badges, status indicators
- `LcarsSidebar` — nav sidebar or session history panel

These are thin wrappers — just CSS and layout. No business logic.

### Admin Log Window

Admin tasks (catalog refresh, scan, stale check, rescan) display a collapsible log window showing real-time progress. The current implementation has this but forces the user to the bottom of the log on every update. The new implementation fixes this:

- **Auto-scroll only when at bottom.** If the user is reading the bottom of the log, new lines scroll in automatically. If the user has scrolled up to read earlier output, auto-scroll stops.
- **Resume auto-scroll** when the user scrolls back to the bottom (within a small threshold).
- **Collapsible** — toggle open/closed without losing position or content.
- **Scroll position preserved** across new log entries while the user is reading.

This is standard chat log behavior — the current implementation just didn't implement the scroll-position check.

### Key React Patterns

- **`useJobStream(jobId)`** — custom hook that subscribes to SSE and exposes `{ phase, progress, userMessage, results, isComplete }` as reactive state.
- **API service layer** — typed fetch wrapper for all `/api/v1/*` calls, similar to labagator's `api.ts`.
- **Role-conditional rendering** — components check user role from `/api/v1/auth/me` and conditionally show curator/admin controls.

### Container

Vite builds to static files → copied into an nginx UBI container. nginx serves the SPA and proxies `/api/*` to the `rcars-api` Service. Build time: ~30 seconds.

---

## Authentication & Authorization

### Three Auth Paths

The API middleware checks inbound requests in priority order:

| Priority | Method | Consumer | How it works |
|---|---|---|---|
| 1 | OAuth proxy headers | Browser users | `X-Forwarded-User` + `X-Forwarded-Email` injected by OAuth proxy sidecar on the frontend Route |
| 2 | ServiceAccount token | PH, cluster services | `Authorization: Bearer <sa-token>` validated via K8s TokenReview API, SA name checked against allowlist |
| 3 | API key | Future external clients | `X-API-Key` header validated against `api_keys` table |

No match → `401 Unauthorized`.

### Roles

| Role | Determined by | Access |
|---|---|---|
| **user** | Any authenticated identity | Advisor, catalog read, own sessions |
| **curator** | Email in `RCARS_CURATOR_EMAILS` | Above + tagging, notes, flags, single-item analysis |
| **admin** | Email in `RCARS_ADMIN_EMAILS` | Above + catalog refresh, bulk scan, token usage, job history |
| **service** | Valid SA token on allowlist | Advisor, catalog read, analysis — scoped per config |

Service accounts authenticate as themselves (e.g., `system:serviceaccount:ph:ph-rcars`), not as fake users.

### Phased Rollout

- **Phase 1:** OAuth proxy headers only. API is cluster-internal (Service, no Route), so PH calls it directly without auth.
- **Phase 2:** Add SA token validation when PH integration goes live.
- **Phase 3:** Add API key auth when external Route is created.

The API Route is defined in the Ansible manifests but disabled by default (`rcars_api_external_route: false`).

---

## Database

### Approach

Clean-break schema. Drop all existing tables, create new ones with Alembic baseline migration. Migrate `token_usage` data.

### Tables

| Table | Purpose | Status |
|---|---|---|
| `catalog_items` | CI metadata from Babylon CRDs | Redesigned — adds `scope` column for prod/dev/event filtering, `content_path` for non-standard repos |
| `showroom_analysis` | LLM analysis results | Redesigned — `content_hash` as first-class column |
| `embeddings` | pgvector 384-dim vectors | Same structure |
| `enrichment_tags` | Curator-applied tags | Same structure |
| `token_usage` | LLM API call tracking | **Migrated from old DB** |
| `advisor_sessions` | Chat turns, results, selections | Per the persistence & feedback design spec |
| `jobs` | Worker job tracking | New — replaces in-memory status dicts |
| `analysis_log` | Audit trail | Same structure |
| `api_keys` | External client API keys | New — for Phase 3 external auth |

### Jobs Table

The backbone of the worker architecture. Every async operation creates a job record:

| Column | Type | Purpose |
|---|---|---|
| `id` | TEXT (PK) | UUID |
| `job_type` | TEXT | `recommend`, `scan`, `analyze`, `refresh`, `check_stale` |
| `status` | TEXT | `queued`, `running`, `complete`, `failed` |
| `queue` | TEXT | `recommend`, `scan`, `default` |
| `created_by` | TEXT | User email or service account identity |
| `progress_json` | JSONB | Phase, current, total, user-facing message |
| `result_json` | JSONB | Final output |
| `error` | TEXT | Failure message |
| `created_at` | TIMESTAMPTZ | ISO 8601 |
| `started_at` | TIMESTAMPTZ | When worker picked it up |
| `completed_at` | TIMESTAMPTZ | When it finished |

### Non-Standard Showroom Support

A small number of Showroom repositories don't follow the standard Antora layout (`content/modules/ROOT/pages/*.adoc`). These currently fail during scan. The `catalog_items` table adds an optional `content_path` column:

- **Default (NULL):** analyzer uses the standard Antora path
- **Custom path set:** analyzer uses the specified path instead — can point to a directory (`docs/labs/`) or a specific nav file (`modules/ROOT/nav.adoc`)
- **Set via:** CLI (`rcars set-content-path <ci_name> <path>`), browse page curator controls, or API (`POST /api/v1/catalog/{ci_name}/override-url`)

This recovers failed scans where the content exists but isn't in the expected location.

### LLM Response Format

All LLM interactions — analysis, triage, rationale — require structured JSON responses. No prose output that requires parsing or guesswork:

- **Analysis (Sonnet):** JSON schema enforced via prompt + response validation. Failed parses retry once, then error.
- **Triage (Haiku):** JSON array of scored candidates. Schema validated before use.
- **Rationale (Sonnet):** JSON with `why_it_fits`, `how_to_use`, `suggested_format`, `duration_notes`, `caveats`. Schema validated.

If a model returns prose instead of JSON, the task logs the raw response at DEBUG level and retries with a stricter prompt. After 2 failures, the task fails with a clear error.

### Migration Plan

1. Export `token_usage` rows to a dump file (safety net)
2. Drop all existing tables — clean slate
3. Alembic baseline migration creates the new schema
4. Import `token_usage` rows into the new table
5. Verify row counts, delete dump
6. `rcars refresh` + `rcars scan` repopulates catalog and analysis from live sources

---

## Logging & Observability

### Structured Logging

Every component emits structured JSON log lines to stdout. Every log line includes:

| Field | Purpose |
|---|---|
| `timestamp` | ISO 8601 (`2026-04-25T14:30:45.123Z`) |
| `component` | `api`, `worker`, `frontend-nginx` |
| `job_id` | Correlation ID tracing a request through the system |
| `user` | Who initiated the action (email or SA identity) |
| `action` | What happened: `enqueued`, `picked_up`, `phase_complete`, `failed` |
| `detail` | Context: phase name, candidate count, elapsed_ms, error message |

### Handoff Logging

Every component boundary crossing is logged:

```
[api]    job=abc123 user=nate@redhat.com action=request_received endpoint=/api/v1/advisor/query
[api]    job=abc123 action=enqueued queue=recommend
[worker] job=abc123 action=picked_up worker=rcars-worker-7x2k queue=recommend
[worker] job=abc123 action=phase_started phase=vector_search
[worker] job=abc123 action=phase_complete phase=vector_search candidates=42 elapsed_ms=320
[worker] job=abc123 action=phase_started phase=triage model=claude-haiku-4-5
[worker] job=abc123 action=phase_progress phase=triage current=12 total=42
[worker] job=abc123 action=phase_complete phase=triage relevant=8 elapsed_ms=4200
[worker] job=abc123 action=phase_started phase=rationale model=claude-sonnet-4-6
[worker] job=abc123 action=phase_complete phase=rationale top_n=5 elapsed_ms=3800
[worker] job=abc123 action=job_complete total_elapsed_ms=8320 results=5
[api]    job=abc123 action=sse_delivered events=12 client=browser session=xyz
```

### Log Levels

| Level | What |
|---|---|
| `INFO` | Every handoff, phase start/complete, job lifecycle. The "story" of each request. |
| `WARNING` | Retries, rate limit delays, stale cache fallbacks, slow queries (>5s) |
| `ERROR` | Job failures, connection failures, auth rejections |
| `DEBUG` | LLM prompt/response snippets (truncated), Redis messages, SQL queries. Off by default, enabled per-component via env var. |

---

## Build & Deployment

### Container Builds

| BuildConfig | Source | Build time | Triggers |
|---|---|---|---|
| `rcars-frontend-build` | `src/frontend/Containerfile` | ~30 seconds | Frontend code changes |
| `rcars-api-build` | `src/api/Containerfile` | ~3 minutes | Python code, dependency changes |

Workers use the API image with a different entrypoint — no separate build.

Build triggers are manual via Ansible tags. No GitHub webhook — you control when each component rebuilds:

```bash
# Rebuild frontend only
ansible-playbook ansible/deploy.yml -e env=dev --tags build-frontend

# Rebuild API + workers
ansible-playbook ansible/deploy.yml -e env=dev --tags build-api

# Full update (build all + migrate + restart)
ansible-playbook ansible/deploy.yml -e env=dev --tags update
```

### Ansible Tags

The existing `ansible/deploy.yml` playbook is modified (not replaced) to support the new multi-component architecture:

| Tag | What it does |
|---|---|
| `mgmt-rbac` | Bootstrap ServiceAccount + RBAC (one-time) |
| `bootstrap` | Infrastructure: Redis StatefulSet, Secrets, ImageStreams, BuildConfigs |
| `apply` | Apply all manifests (no build) |
| `update` | Full: apply + build all + migrate + restart workers |
| `build-frontend` | Rebuild + rollout frontend only |
| `build-api` | Rebuild + rollout API + workers |
| `migrate` | Run Alembic migrations in API pod |
| `webhooks` | Display webhook configuration |

### Deployment Resources

| Resource | Type | Purpose |
|---|---|---|
| `rcars-frontend` | Deployment | nginx serving React SPA, 1+ replicas |
| `rcars-api` | Deployment | FastAPI, 2+ replicas (stateless) |
| `rcars-worker` | Deployment | arq workers, 1+ replicas (scalable per queue) |
| `rcars-redis` | StatefulSet | Redis 7, persistent volume |
| `rcars-db` | StatefulSet | Existing PostgreSQL 16 + pgvector |
| `rcars-frontend` | Route | Public, OAuth proxy sidecar |
| `rcars-api` | Route | **Disabled by default** (`rcars_api_external_route: false`) |
| `rcars-api` | Service | ClusterIP for frontend proxy + cluster consumers |
| Secrets | Secret | DB creds, OAuth, SA allowlist |
| Config | ConfigMap | Model names, queue settings, curator/admin emails |

Credentials and sensitive data belong in gitignored `ansible/vars/dev.yml` and `ansible/vars/prod.yml` files, same as today.

### Resource Limits

All pods define resource requests and limits — generous but reasonable:

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---|---|---|---|---|
| `rcars-frontend` | 100m | 500m | 128Mi | 256Mi |
| `rcars-api` | 500m | 2 | 512Mi | 2Gi |
| `rcars-worker` | 500m | 2 | 1Gi | 4Gi |
| `rcars-redis` | 100m | 500m | 256Mi | 512Mi |

Workers get the most memory — sentence-transformers model loading + LLM response handling. API pods are lighter since they've offloaded heavy work. These are starting points; adjust based on observed usage.

### Scaling Guidance

Manual scaling only — no HPA. The admin dashboard surfaces the information needed to decide when to add a worker replica:

**Admin dashboard — worker health panel:**

| Metric | Source | Purpose |
|---|---|---|
| Queue depth per queue (`recommend`, `analyze`, `ops`) | Redis `LLEN` | Are jobs waiting? How many? |
| Active jobs per worker | `jobs` table (`status = 'running'`) | What's running right now? |
| Average job duration by type | `jobs` table (completed_at - started_at) | How long are things taking? |
| Failed jobs (last 24h) | `jobs` table (`status = 'failed'`) | Are workers struggling? |
| Worker pod count | Displayed for awareness | How many workers do we have? |

If the queue depth panel shows jobs consistently backing up, you add another worker replica in the Ansible vars and redeploy. The dashboard gives you the signal; the decision and action are yours.

### Local Development

`dev-services.sh` starts everything locally:

```
$ ./dev-services.sh start

Starting PostgreSQL (podman)...    ✓  localhost:5432
Starting Redis (podman)...         ✓  localhost:6379
Starting API (uvicorn --reload)... ✓  localhost:8080
Starting Worker (arq)...           ✓  localhost (background)
Starting Frontend (vite dev)...    ✓  localhost:3000

RCARS dev environment ready.
Frontend:  http://localhost:3000
API docs:  http://localhost:8080/api/v1/docs
Logs:      /tmp/rcars-*.log
```

- **Frontend:** Vite dev server with HMR — sub-second UI refreshes
- **API:** uvicorn with `--reload` — auto-restarts on Python changes
- **Worker:** arq with watch mode — auto-restarts on task code changes
- **PostgreSQL + Redis:** podman containers using the `agnosticd` machine
- **Auth bypass:** `RCARS_DEV_USER` env var

---

## Documentation

Documentation is a deliverable with the same priority as code. New docs follow the style and tone of the existing RCARS documentation — task-oriented, concise, practical. Existing docs are updated where their content changes.

### Documentation Plan

| Document | Action | Purpose |
|---|---|---|
| `docs/architecture.md` | Update | Revised system diagram, component descriptions, data flow for the new three-tier architecture |
| `OPERATIONS.md` | Update | Add multi-component build/deploy commands, worker management, Redis operations |
| `docs/api-guide.md` | New | API usage guide with examples — how to query, how to stream, how to authenticate. Not a code reference (Swagger handles that). |
| `docs/workers.md` | New | How to run generic vs specialized workers, how to split queues, how to scale, how to monitor, how to troubleshoot. Task-oriented, not API reference. |
| `docs/development.md` | New | Local dev setup, how to run each component, how to run tests, how to rebuild a single component. |
| `docs/migration.md` | New | One-time: how to migrate from monolith, export/import token_usage, verify. Disposable after migration. |
| `CLAUDE.md` | Update | Project-level instructions for the new codebase structure |

### Documentation Principles

- **Task-oriented.** "How to add a new worker queue" not "Worker class API surface."
- **Match existing tone.** The current docs are clear and direct with good diagrams. New docs follow the same standard.
- **Comments in code + CLAUDE.md can be dry and detailed.** User-facing docs are practical and concise.
- **Kept current.** When code changes, the relevant doc is updated in the same PR.

---

## Project Structure

```
rcars-advisory/
├── src/
│   ├── api/                        # FastAPI backend
│   │   ├── Containerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── alembic/                # DB migrations
│   │   ├── rcars/
│   │   │   ├── api/
│   │   │   │   ├── app.py          # FastAPI app + lifespan
│   │   │   │   ├── routes/         # advisor.py, catalog.py, analysis.py, admin.py, auth.py
│   │   │   │   ├── middleware/     # auth.py, logging.py
│   │   │   │   └── deps.py        # Shared dependencies
│   │   │   ├── workers/
│   │   │   │   ├── settings.py     # arq worker configuration
│   │   │   │   ├── recommend.py    # Recommendation pipeline task
│   │   │   │   ├── scan.py         # Analysis/scan tasks
│   │   │   │   └── refresh.py      # Catalog refresh task
│   │   │   ├── services/           # Business logic
│   │   │   │   ├── recommender/    # 3-phase pipeline (vector, triage, rationale)
│   │   │   │   ├── analyzer.py     # Showroom content analysis
│   │   │   │   ├── catalog.py      # Babylon CRD reader
│   │   │   │   └── embeddings.py   # Sentence-transformers
│   │   │   ├── db/
│   │   │   │   ├── database.py     # Connection pool, session management
│   │   │   │   ├── models.py       # Pydantic models for all tables
│   │   │   │   └── queries/        # SQL query modules by domain
│   │   │   ├── config.py           # Settings from env vars
│   │   │   └── prompts/            # LLM prompt templates
│   │   └── tests/
│   │
│   └── frontend/                   # React SPA
│       ├── Containerfile
│       ├── nginx.conf
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       ├── src/
│       │   ├── main.tsx            # App entry point
│       │   ├── App.tsx             # Router + layout
│       │   ├── pages/             # Advisor, Browse, Admin
│       │   ├── components/
│       │   │   ├── lcars/          # LCARS design system components
│       │   │   ├── advisor/        # Chat, RecCard, ProgressStream
│       │   │   ├── browse/         # CatalogList, CatalogDetail, CuratorControls
│       │   │   └── admin/          # TokenUsage, JobsList, CatalogRefresh
│       │   ├── hooks/
│       │   │   ├── useJobStream.ts  # SSE subscription hook
│       │   │   └── useAuth.ts       # Auth context hook
│       │   ├── services/
│       │   │   └── api.ts           # Typed API client
│       │   └── styles/
│       │       └── lcars.css        # LCARS theme (ported from current)
│       └── public/                 # Static assets
│
├── ansible/                        # Deployment (modified, not replaced)
│   ├── deploy.yml
│   ├── templates/manifests.yaml.j2
│   └── vars/
│       ├── common.yml
│       ├── dev.yml                 # gitignored
│       └── prod.yml                # gitignored
│
├── docs/                           # User-facing documentation
├── dev-services.sh                 # Local dev environment script
├── CLAUDE.md
└── OPERATIONS.md
```

---

## Deferred to Backlog

These are real requirements discussed during design but not part of this rearchitecture. They build on top of the new architecture once it's in place.

### RCARS Backlog

- **Showroom live-read endpoint** (`POST /api/v1/catalog/{ci_name}/read-showroom`) — on-demand Showroom content retrieval. PH needs this for "unpacking" — reading Showroom modules and automation details in real time, not just the cached analysis summary.
- **Content overlap/comparison endpoint** (`POST /api/v1/analysis/compare`) — the "Analyze Content" feature. Two sub-functions: proposal vs. catalog overlap detection, and direct lab-to-lab comparison.
- **Dev/event catalog visibility** — configurable scope filtering in the advisor and browse pages. Includes "not yet available" callout on dev/event cards.
- **Conversational advisor** — multi-turn refinement, memory across turns, interactive event URL parsing ("which tracks are you targeting?").
- **Multi-vector event search** — multiple queries per category for broad events (app dev, platform, security) to ensure balanced results.
- **Scan dedup by commit SHA** — resolve refs to commit SHAs via `git ls-remote` before scanning to avoid duplicate analysis.

### Publishing House Backlog

- **RCARS API integration for vetting** — PH calls RCARS to check content overlap when someone creates something new.
- **Prototyping workflow** — PH queries RCARS for closest-match content, reads the Showroom and automation, then orders and modifies an environment on the requestor's behalf.
- **RCARS as Showroom unpacking service** — PH delegates content reading to RCARS rather than cloning repos itself.
