# RCARS — Project Instructions

RHDP Content Advisory & Recommendation System. Matches Red Hat Demo Platform catalog items to events, opportunities, and user queries using vector search + LLM triage + LLM rationale.

## Architecture

Four deployments on OpenShift. React frontend → FastAPI API → arq workers + Redis → PostgreSQL with pgvector.

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│  React SPA  │────▶│  FastAPI API │────▶│  arq Workers     │────▶│  PostgreSQL  │
│  (Vite+TS)  │     │  (uvicorn)  │     │  scan + recommend│     │  + pgvector  │
│  port 3000  │     │  port 8080  │     │                  │     │  port 5432   │
└─────────────┘     └──────┬──────┘     └────────┬─────────┘     └──────────────┘
                           │                     │
                           └─────────┬───────────┘
                                     ▼
                              ┌─────────────┐
                              │    Redis     │
                              │  port 6379   │
                              └─────────────┘
```

- **Frontend** — React 19 SPA with LCARS theme. Three pages: Advisor (chat + recommendations), Browse (catalog + curation), Admin (operations + monitoring). Vite dev server proxies `/api` to backend.
- **API** — FastAPI 2.0 with uvicorn. Receives requests, creates jobs, relays SSE progress from Redis pub/sub. Never processes LLM calls directly.
- **Scan Worker** — arq worker on `arq:queue:scan`. Handles showroom analysis, catalog refresh, stale checks, nightly maintenance pipeline. Max 5 concurrent jobs, 600s timeout.
- **Recommend Worker** — arq worker on `arq:queue:recommend`. Handles advisor queries only (prevents starvation from long-running scans). Max 3 concurrent jobs, 120s timeout.
- **PostgreSQL** — pgvector extension for 384-dim embeddings (all-MiniLM-L6-v2). 9 tables.
- **Redis** — Job queue (arq), pub/sub relay for SSE streaming, job progress channel.

## Repository Structure

```
rcars-advisory/
├── src/
│   ├── api/                  # FastAPI backend + arq workers (Python 3.11)
│   │   ├── rcars/            # Main package
│   │   ├── tests/            # pytest test suite
│   │   └── scripts/          # One-off migration scripts
│   └── frontend/             # React SPA (Vite + TypeScript)
│       ├── src/
│       │   ├── pages/        # AdvisorPage, BrowsePage, AdminPage (4 sub-pages)
│       │   ├── components/   # lcars/ (design system), advisor/, admin/
│       │   ├── services/     # api.ts (API client)
│       │   └── hooks/        # useAuth, useJobStream, usePrivateMode
│       └── package.json
├── ansible/                  # OpenShift deployment (Ansible + Jinja2)
│   ├── deploy.yml            # Main playbook
│   ├── tasks/                # build-api, build-frontend, apply-manifests, etc.
│   ├── templates/            # manifests-app.yaml.j2, manifests-infra.yaml.j2
│   └── vars/                 # common.yml, dev.yml (gitignored), prod.yml (gitignored)
├── alembic/                  # Database migrations
├── docs/                     # MkDocs documentation (see docs/ structure below)
├── BACKLOG.md                # Project roadmap — open items by priority, completed at bottom
├── WORKLOG.md                # Session handoff notes between developers
├── dev-services.sh           # Local development launcher
├── mkdocs.yml                # MkDocs configuration
└── pyproject.toml            # Python project config (rcars package)
```

## Backend Layout

```
src/api/rcars/
├── api/
│   ├── app.py                # App factory (create_app), lifespan, route registration
│   ├── streaming.py          # JobProgressRelay: Redis pub/sub → SSE, keepalive
│   ├── routes/
│   │   ├── advisor.py        # POST /advisor/query, GET stream/result/sessions
│   │   ├── catalog.py        # GET /catalog, POST refresh, curator endpoints (tags/note/flag)
│   │   ├── analysis.py       # POST scan/check-stale/rescan-stale/rescan-all, GET stream
│   │   ├── admin.py          # GET token-usage/jobs/workers/scan-progress/queries/schedule
│   │   ├── auth.py           # GET /auth/me (email + roles)
│   │   └── health.py         # GET /health, /health/ready
│   └── middleware/
│       ├── auth.py           # OAuth headers, SA token validation, role enforcement
│       └── request_logging.py
├── workers/
│   ├── settings.py           # WorkerSettings (scan queue) + RecommendWorkerSettings (recommend queue)
│   ├── scan.py               # run_analysis — clone, analyze, embed, propagate to siblings
│   ├── recommend.py          # run_recommendation — 3-phase pipeline, session logging
│   ├── ops.py                # run_catalog_refresh, run_stale_check, run_nightly_pipeline
│   └── base.py               # WorkerContext dataclass, publish_progress helper
├── services/
│   ├── recommender/
│   │   ├── pipeline.py       # run_query — orchestrates vector→triage→rationale, URL/duration extraction
│   │   ├── vector_search.py  # search — pgvector query, content dedup, base-to-published promotion
│   │   ├── triage.py         # triage — Haiku scores candidates, filters by relevance+cutoff
│   │   ├── rationale.py      # generate_rationale — Sonnet writes why_it_fits, how_to_use, caveats
│   │   └── models.py         # Candidate, QueryState, Phase enums
│   ├── analyzer.py           # clone_showroom, read_showroom_content, analyze_showroom, generate_embedding
│   ├── catalog.py            # CatalogReader (K8s CRDs), extract_showroom_url (3-point extraction)
│   └── event_parser.py       # parse_event_url — fetch page, extract themes via Sonnet
├── db/
│   └── database.py           # Connection pool, all SQL queries, 9 tables, job management
├── config.py                 # Pydantic Settings with RCARS_ prefix
├── logging.py                # structlog JSON setup
├── cli.py                    # Click CLI: init-db, refresh, scan, status, serve, tag/untag/note/flag
└── prompts/                  # LLM prompt templates (analysis, triage, rationale, event matching)
```

## Running Locally

```bash
./dev-services.sh start    # PostgreSQL (pgvector), Redis, API, Scan Worker, Recommend Worker, Frontend
./dev-services.sh stop     # Stop all
./dev-services.sh status   # Check what's running
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8080/api/v1/docs
- Logs: /tmp/rcars-api.log, /tmp/rcars-scan-worker.log, /tmp/rcars-recommend-worker.log, /tmp/rcars-frontend.log

Dev services set: `RCARS_DEV_USER=dev@redhat.com`, `RCARS_ADMIN_EMAILS_STR=dev@redhat.com`, `RCARS_CURATOR_EMAILS_STR=dev@redhat.com` (full access locally).

## Running Tests

```bash
source ~/.virtualenvs/rcars-v2/bin/activate
cd src/api
python -m pytest tests/ -v
```

Requires PostgreSQL with pgvector on localhost:5432 and Redis on localhost:6379. Test database: `rcars_test` (auto-created by dev-services.sh). Tests marked `integration` require a live Babylon cluster (deselect with `-m "not integration"`).

## Key Patterns

- **All LLM responses must be structured JSON.** No prose parsing. Use `parse_analysis_response()` for safe extraction with truncation recovery.
- **Long-running operations** return `{job_id}` immediately. Workers process via arq + Redis queues.
- **Progress streaming** via Redis pub/sub → SSE. API relays messages; it never processes LLM calls itself.
- **Auth model:** Three modes checked in order: (1) dev bypass via `RCARS_DEV_USER`, (2) K8s ServiceAccount bearer tokens validated via TokenReview API against SA allowlist, (3) OAuth proxy headers (`X-Forwarded-Email`).
- **Role enforcement:** `require_auth` (any authenticated user), `require_curator` (curator or admin), `require_admin` (admin only). Roles derived from `RCARS_CURATOR_EMAILS` and `RCARS_ADMIN_EMAILS` config.
- **Logging:** structlog JSON with `component`, `job_id`, `action` fields on every line. Verbose logging is preferred — too much is better than too little.
- **Sibling propagation:** When multiple CIs share the same Showroom (same URL+ref), scan once and propagate analysis + embeddings to all siblings.

## Environment Variables

All prefixed with `RCARS_` (case-insensitive via Pydantic Settings).

| Variable | Default | Purpose |
|----------|---------|---------|
| `RCARS_DATABASE_URL` | (required) | PostgreSQL connection string |
| `RCARS_REDIS_URL` | `redis://localhost:6379` | Redis URL |
| `RCARS_DEV_USER` | `""` | Bypass auth for local development |
| `RCARS_MODEL` | `claude-sonnet-4-6` | Default LLM model for analysis |
| `RCARS_TRIAGE_MODEL` | `claude-haiku-4-5` | Triage phase model (fast, cheap) |
| `RCARS_RATIONALE_MODEL` | `claude-sonnet-4-6` | Rationale phase model |
| `RCARS_VECTOR_CUTOFF` | `0.55` | Minimum vector similarity (0-1) |
| `RCARS_TRIAGE_CUTOFF` | `30` | Minimum triage relevance score (0-100) |
| `RCARS_RATIONALE_TOP_N` | `5` | Max candidates for rationale generation |
| `RCARS_MAX_PARALLEL` | `5` | Max parallel scan operations |
| `RCARS_CURATOR_EMAILS_STR` | `""` | Comma-separated curator emails |
| `RCARS_ADMIN_EMAILS_STR` | `""` | Comma-separated admin emails |
| `RCARS_SA_ALLOWLIST_STR` | `""` | Comma-separated SA identities for API access |
| `RCARS_STALE_DAYS` | `3` | Days before content considered stale |
| `RCARS_PIPELINE_ENABLED` | `true` | Enable nightly maintenance cron |
| `RCARS_PIPELINE_HOUR` | `4` | UTC hour for nightly pipeline |
| `RCARS_PIPELINE_MINUTE` | `0` | Minute for nightly pipeline |
| `ANTHROPIC_VERTEX_PROJECT_ID` | `""` | Vertex AI project (fallback from env) |
| `CLOUD_ML_REGION` | `us-east5` | Vertex AI region |

## API Endpoints

27 endpoints across 6 route modules. All prefixed with `/api/v1`.

**Advisor** (require_auth):
- `POST /advisor/query` — Submit recommendation query, returns job_id
- `GET /advisor/query/{job_id}/stream` — SSE stream of job progress
- `GET /advisor/query/{job_id}/result` — Completed query result
- `GET /advisor/sessions` — List user's advisor sessions
- `GET /advisor/sessions/{session_id}` — Get session with all turns
- `POST /advisor/sessions/{session_id}/select` — Mark chosen recommendation

**Catalog** (mixed auth):
- `GET /catalog` — List catalog items (paginated, filterable)
- `GET /catalog/stats` — Database currency/staleness stats
- `GET /catalog/{ci_name}` — Single CI with analysis + tags
- `GET /catalog/{ci_name}/analysis` — Showroom analysis only
- `POST /catalog/refresh` — Trigger catalog refresh (admin)
- `POST /catalog/{ci_name}/tags` — Add enrichment tag (curator)
- `DELETE /catalog/{ci_name}/tags/{tag_id}` — Remove tag (curator)
- `PUT /catalog/{ci_name}/note` — Set curator note (curator)
- `POST /catalog/{ci_name}/flag` — Flag for review (curator)
- `POST /catalog/{ci_name}/override-url` — Override showroom URL (curator)
- `POST /catalog/{ci_name}/content-path` — Set content path + trigger rescan (curator)

**Analysis** (require_admin except stream):
- `POST /analysis/scan` — Start full scan of unanalyzed items
- `POST /analysis/check-stale` — Check for stale content via git
- `POST /analysis/rescan-stale` — Rescan stale items only
- `POST /analysis/rescan-all` — Mark all stale + full rescan
- `POST /analysis/{ci_name}` — Analyze single CI (curator)
- `GET /analysis/jobs/{job_id}/stream` — Stream analysis job progress

**Admin** (require_admin):
- `GET /admin/token-usage` — Token stats by operation/model
- `GET /admin/jobs/{job_id}` — Single job details
- `GET /admin/jobs` — Recent jobs list
- `GET /admin/workers` — Worker health (queue depths, job counts)
- `GET /admin/scan-progress` — Scan batch progress
- `GET /admin/queries` — Advisor query history
- `POST /admin/run-maintenance` — Trigger nightly pipeline manually
- `GET /admin/schedule` — Pipeline schedule status + last run

**Auth/Health**:
- `GET /auth/me` — Current user email + roles
- `GET /health` — Basic health check
- `GET /health/ready` — Readiness probe (DB + Redis)

## Database Schema

9 tables in PostgreSQL with pgvector extension:

| Table | Purpose |
|-------|---------|
| `catalog_items` | CatalogItem CRDs from Babylon. PK: ci_name. Metadata, stage, showroom URL/ref, scan status |
| `showroom_analysis` | LLM analysis results. PK: ci_name (FK). Summary, modules, learning objectives, content_hash, stale tracking |
| `enrichment_tags` | Curator-added tags (tag_type, tag_value). Unique per (ci_name, tag_type, tag_value) |
| `embeddings` | 384-dim vectors (vector(384)). Types: ci_summary, module. Used for pgvector cosine search |
| `analysis_log` | Audit trail of analysis actions |
| `token_usage` | LLM token tracking per operation (scan/triage/rationale/event_parse) |
| `advisor_sessions` | User queries + results. Keyed by (session_id, turn_index) for multi-turn |
| `jobs` | Background job tracking. Types: recommend, analyze, refresh, scan, rescan, maintenance |
| `api_keys` | API key management (future, not yet active) |

## Recommendation Pipeline

Three-phase pipeline executed by the recommend worker:

```
Query → [URL extraction] → [Duration extraction] → Phase 1 → Phase 2 → Phase 3 → Results
```

**Pre-processing:**
- If query contains URLs: fetch page, extract event profile (themes + search queries) via Sonnet, merge into query text
- If query mentions duration: extract target minutes and hard/soft limit flag

**Phase 1 — Vector Search** (`vector_search.py`):
- Generate 384-dim query embedding via sentence-transformers
- Search pgvector (cosine distance, limit=25, cutoff=0.55)
- Deduplicate by content_hash — keep best representative per unique content (prefer prod > event > dev, published > base)
- Promote base CIs to their published identity (users can only order published CIs)

**Phase 2 — Triage** (`triage.py`):
- Send candidates + query to Claude Haiku (fast, cheap)
- Returns: relevance_score (0-100), relevant (bool), one_line_reason per candidate
- Filter: keep candidates where relevant=true AND score >= 30
- Assign tiers: yellow (relevant) or white (below cutoff)
- If duration target: apply soft/hard penalty reranking

**Phase 3 — Rationale** (`rationale.py`):
- Generate detailed rationale for top N candidates via Claude Sonnet
- Fields: why_it_fits, how_to_use, suggested_format, duration_notes, caveats
- Promote yellow → green tier when full rationale generated

**Tiers:** Green (best fit, full rationale) → Yellow (relevant, scored) → White (reviewed, below cutoff)

## Showroom Extraction

Showroom URLs and refs extracted from AgnosticVComponent CRDs during catalog refresh. Three extraction paths, checked in order:

1. **Top-level definition** — `ocp4_workload_showroom_content_git_repo`, `showroom_git_repo`, `bookbag_git_repo` in `spec.definition`
2. **Template variable resolution** — if ref contains `{{ var }}`, resolve from `spec.definition` values and catalog parameter defaults
3. **Component parameter_values** — ZT (zero-tier) Virtual CIs pass showroom URL to base component via `__meta__.components[].parameter_values`

Template/placeholder repos are skipped: `showroom_template_default`, `showroom_template_nookbag`, `showroom_template_zero`.

## Scan Deduplication

Scanning deduplicates by `(showroom_url, showroom_ref)`. Multiple CIs sharing the same URL and ref are scanned once, and analysis is propagated to all siblings.

- Different ref = different scan (e.g. dev `ref=main` vs prod `ref=v1.0.0`)
- Same ref = scan once, propagate analysis + embeddings to all siblings
- Each CI gets its own `showroom_analysis` row and `embeddings` rows — every CI is independently searchable
- `ref=NULL` (HEAD) is treated as its own group, separate from `ref=main`

## Nightly Maintenance Pipeline

Three-step pipeline, runs daily at 04:00 UTC (configurable). Triggered via arq cron or manually via `POST /admin/run-maintenance`.

1. **Catalog refresh** — read all AgnosticV CRDs, upsert to database, remove deleted items
2. **Stale check** — `git ls-remote` first (skip unchanged repos), clone only repos with new commits, compare content hash
3. **Re-analysis** — enqueue stale items to scan worker for fresh analysis

## Build & Deploy

```bash
# Frontend only (~30s)
ansible-playbook ansible/deploy.yml -e env=dev --tags build-frontend

# API + workers (~3min, restarts api + scan-worker + recommend-worker)
ansible-playbook ansible/deploy.yml -e env=dev --tags build-api

# Config changes only (user lists, env vars, no builds)
ansible-playbook ansible/deploy.yml -e env=dev --tags apply

# Full infrastructure + app update
ansible-playbook ansible/deploy.yml -e env=dev --tags update
```

Only build the changed component. Never do a full deploy for frontend-only or API-only changes.

**There is no webhook for automatic builds.** Pushing to git does NOT trigger a build. Builds must be triggered manually via Ansible or `oc start-build`. Always run the appropriate `ansible-playbook` command after pushing changes that need deployment.

Ansible vars files (`ansible/vars/dev.yml`, `ansible/vars/prod.yml`) contain secrets and are gitignored. Use `ansible/vars/common.yml` for shared config.

## CLI Commands

Entry point: `rcars` (installed via `pip install -e ".[dev]"`).

| Command | Purpose |
|---------|---------|
| `rcars init-db [--drop]` | Initialize or reset database schema |
| `rcars refresh` | Refresh catalog from Babylon CRDs |
| `rcars scan [--max N]` | Analyze showroom content (parallel) |
| `rcars status [--failures]` | Show catalog status summary |
| `rcars serve [--port 8080] [--reload]` | Start API server |
| `rcars tag CI_NAME TYPE VALUE` | Add enrichment tag |
| `rcars untag CI_NAME TYPE VALUE` | Remove enrichment tag |
| `rcars note CI_NAME TEXT` | Set curator note |
| `rcars flag CI_NAME` | Flag for enrichment review |
| `rcars override-url CI_NAME URL` | Override showroom URL |
| `rcars set-content-path CI_NAME PATH` | Set custom content path |

## Frontend Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/advisor` (default `/`) | AdvisorPage | Chat interface + streaming recommendation cards |
| `/browse` | BrowsePage | Catalog browser with filters, expandable details, curator tools |
| `/admin/catalog` | AdminCatalogPage | Catalog sync, content analysis, maintenance scheduling |
| `/admin/workers` | AdminWorkersPage | Job queue monitoring, worker health |
| `/admin/tokens` | AdminTokensPage | LLM token usage by operation/model |
| `/admin/queries` | AdminQueriesPage | Query history with session details and tier visualization |

## Development Guidelines

- **Verbose logging always.** Every worker operation, every LLM call, every database mutation should log with structured fields.
- **Only build changed components.** Frontend change = `--tags build-frontend`. API change = `--tags build-api`.
- **Commit and push before building.** OpenShift builds from git. Never use `--from-dir` with uncommitted changes.
- **Batch commits, push at milestones.** Every push triggers an OpenShift build — don't push individual commits.
- **JSON responses from LLMs.** All prompts must request structured JSON output. Use `parse_analysis_response()` for safe extraction.
- **No direct LLM calls in API.** API creates jobs, workers call LLMs. This keeps the API responsive.

## Git Workflow

- **Direct pushes to `main` are allowed** for routine changes (docs, backlog, small fixes).
- **Feature branches with PRs are preferred** for non-trivial changes. Create a branch, open a PR, and let CodeRabbit review before merging.
- **Production deploys require a PR.** Merging `main` → `production` must always go through a pull request — never push directly to `production`.
- **CodeRabbit** is installed on this repo and provides automated code reviews on PRs. Wait for its review before merging.

## Collaboration

- **BACKLOG.md** — Project roadmap. Open items by priority at top, completed items at bottom. Treat as the source of truth for what to work on next.
- **WORKLOG.md** — Session handoff notes. Before ending a session, document what was done, what's in progress, and what's next. Read this before starting work.

## Documentation

Published docs via MkDocs Material at https://rhpds.github.io/rcars/. Source in `docs/`.

```
docs/
├── index.md                    # Landing page
├── overview.md                 # System overview
├── architecture/               # Technical design
│   ├── system-design.md        # Architecture deep dive
│   └── deployment.md           # OpenShift deployment details
├── user/                       # End-user guides
│   └── web-guide.md            # Web UI walkthrough
├── admin/                      # Operator guides
│   ├── cli-guide.md            # CLI reference
│   ├── token-usage.md          # Token usage tracking
│   ├── operations.md           # Workers, maintenance, monitoring
│   └── development.md          # Local development setup
├── stylesheets/rcars.css       # Theme customization
└── superpowers/                # Internal specs/plans (excluded from published docs)
```

## Design Specs

Historical design documents in `docs/superpowers/specs/`. Key reference:

| Spec | Topic |
|------|-------|
| `2026-04-25-rearchitecture-api-design.md` | Current v2 architecture (FastAPI + arq + React) |
| `2026-04-11-recommender-redesign-design.md` | 3-phase recommendation pipeline |
| `2026-04-14-token-usage-tracking-design.md` | Token usage tracking system |
| `2026-04-07-eca-production-redesign-design.md` | Original production redesign |
