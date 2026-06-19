# RCARS — Project Instructions

RHDP Content Advisory & Recommendation System. Matches Red Hat Demo Platform catalog items to events, opportunities, and user queries using vector search + LLM triage + LLM rationale.

## Architecture

Four deployments on OpenShift. React frontend → FastAPI API → arq workers + Redis → PostgreSQL with pgvector.

```text
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

- **Frontend** — React 19 SPA with LCARS theme. Pages: Advisor (chat + recommendations), Browse (catalog + curation), Content Analysis (overlap detection), Admin (4 sub-pages: catalog ops, workers, tokens, queries). Vite dev server proxies `/api` to backend.
- **API** — FastAPI 2.0 with uvicorn. Receives requests, creates jobs, relays SSE progress from Redis pub/sub. Never processes LLM calls directly.
- **Scan Worker** — arq worker on `arq:queue:scan`. Handles showroom analysis, catalog refresh, stale checks, nightly maintenance pipeline. Max 5 concurrent jobs, 600s timeout.
- **Recommend Worker** — arq worker on `arq:queue:recommend`. Handles advisor queries only (prevents starvation from long-running scans). Max 3 concurrent jobs per replica, 120s timeout. Sync LLM calls run in thread pool (`asyncio.to_thread`). Scale via `recommend_worker_replicas` in Ansible vars.
- **PostgreSQL** — pgvector extension for 384-dim embeddings (all-MiniLM-L6-v2). 15 tables.
- **Redis** — Job queue (arq), pub/sub relay for SSE streaming, job progress channel.

## Repository Structure

```text
rcars-advisory/
├── src/
│   ├── api/                  # FastAPI backend + arq workers (Python 3.11)
│   │   ├── rcars/            # Main package
│   │   ├── alembic/          # Database migrations (runs in container)
│   │   ├── tests/            # pytest test suite
│   │   └── scripts/          # One-off migration scripts
│   └── frontend/             # React SPA (Vite + TypeScript)
│       ├── src/
│       │   ├── pages/        # AdvisorPage, BrowsePage, ContentAnalysisPage, AdminPage
│       │   ├── components/   # lcars/ (design system), advisor/, admin/
│       │   ├── services/     # api.ts (API client)
│       │   └── hooks/        # useAuth, useJobStream, usePrivateMode
│       └── package.json
├── ansible/                  # OpenShift deployment (Ansible + Jinja2)
│   ├── deploy.yml            # Main playbook
│   ├── tasks/                # build-api, build-frontend, apply-manifests, etc.
│   ├── templates/            # manifests-app.yaml.j2, manifests-infra.yaml.j2
│   └── vars/                 # common.yml, dev.yml (gitignored), prod.yml (gitignored)
├── docs/                     # MkDocs Material → https://rhpds.github.io/rcars/
├── BACKLOG.md                # Project roadmap — open items by priority
├── WORKLOG.md                # Session handoff notes between developers
├── dev-services.sh           # Local development launcher
└── pyproject.toml            # Python project config (rcars package)
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
- **Scan deduplication:** Refs are resolved to commit SHAs via batch `git ls-remote`. CIs sharing the same effective URL + SHA are scanned once and propagated. Falls back to ref-based grouping on resolution failure.
- **Environment variables:** All prefixed with `RCARS_` (case-insensitive via Pydantic Settings). See `src/api/rcars/config.py` for full list.

## API Reference

45 endpoints across 6 route modules (advisor, catalog, analysis, admin, auth, health). All prefixed with `/api/v1`. Interactive docs at `/api/v1/docs` when running. Route files: `src/api/rcars/api/routes/`.

## Database

15 tables in PostgreSQL with pgvector. Schema defined in `src/api/rcars/db/database.py`. Migrations in `src/api/alembic/versions/` (currently 001-008). Key tables: `catalog_items` (CRD metadata — ALL Babylon items, not just Showroom; soft-deleted via `retired_at` column), `showroom_analysis` (LLM results + content_hash), `embeddings` (384-dim vectors), `advisor_sessions` (query history), `catalog_item_workloads` + `workload_mapping` (infrastructure metadata), `reporting_metrics` (retirement scoring + quarterly JSONB breakdowns).

**Soft-delete:** Items that disappear from Babylon CRDs get `retired_at = NOW()` instead of being deleted. All active-item queries filter on `retired_at IS NULL`. Items that reappear in a future scan are automatically un-retired. Browse page has a curator-only "Show Retired" toggle.

## Retirement Analysis — Key Implementation Details

Data flow: RHDP Reporting MCP → `run_reporting_sync()` → `reporting_metrics` table → `/analysis/retirement` endpoint → frontend.

**Cost methodology:** Cost queries include ALL environments (dev/event/prod) — no `PROVISION_FILTERS`. The `avg_cost_per_provision` is computed in Python as `total_cost / provisions` where provisions is PROD-only. This amortizes dev/event infrastructure costs into each production deployment, reflecting the full cost of maintaining an item.

**Query scoping:** Provisions, touched, closed, and dates queries apply `PROVISION_FILTERS` (PROD environment + real users). Cost queries do NOT apply this filter. The `PROVISION_FILTERS` constant in `reporting_sync.py` controls this.

**Catalog completeness:** After importing from the reporting MCP, `get_catalog_base_names()` pulls all unique base names from `catalog_items` (the local catalog — ALL Babylon items). Items in the catalog but missing from reporting data are backfilled with zero values. The orphan cleanup then removes items not in the current sync AND not in the current catalog. Result: Prod tab + Without Prod tab = total unique catalog items.

**Time window:** `quarterly_data` JSONB column stores per-quarter breakdowns. The API's `window` parameter (1q/2q/3q/1y) triggers `compute_windowed_scores()` which sums relevant quarters, recomputes percentile rankings, and rescores. No MCP re-query needed.

**Scoring thresholds:** High ≥ 55, Review ≥ 35, Keepers < 35 (frontend and CLI).

**Ansible deployment:** Reporting MCP env vars must be on BOTH the API deployment and scan-worker deployment (template: `manifests-app.yaml.j2`). The secret is in `manifests-infra.yaml.j2`.

## CLI

Entry point: `rcars` (installed via `pip install -e ".[dev]"`). Run `rcars --help` for full command list. Key commands: `init-db`, `refresh`, `scan`, `status`, `serve`. Subgroups: `rcars infra`, `rcars workload`, `rcars reporting-db` (sync/show/status for reporting metrics).

## Build & Deploy

```bash
# Frontend only (~30s)
ansible-playbook ansible/deploy.yml -e env=dev --tags build-frontend

# API + workers (~3min, restarts api + scan-worker + recommend-worker)
ansible-playbook ansible/deploy.yml -e env=dev --tags build-api

# Config changes only (user lists, env vars, no builds)
ansible-playbook ansible/deploy.yml -e env=dev --tags apply

# Database migrations only (runs rcars init-db + alembic upgrade head)
# NOTE: migrations run on the CURRENT pod — if you have schema changes in new code,
# build the API first so the pod has the new migration files
ansible-playbook ansible/deploy.yml -e env=dev --tags migrate

# Build all + migrate (correct order: build API, build frontend, then run migrations)
# Use this when changes span API code + schema — it ensures migrations run on the new code
ansible-playbook ansible/deploy.yml -e env=dev --tags update
```

**Migration ordering:** Migrations execute on the running API pod, so the pod must have the new code. When deploying changes that include schema modifications, use `--tags update` — never run `--tags migrate` before `--tags build-api`. For new tables, `create_schema()` handles them; for column additions to existing tables, Alembic is required.

Only build the changed component. Never do a full deploy for frontend-only or API-only changes.

**There is no webhook for automatic builds.** Pushing to git does NOT trigger a build. Always run the appropriate `ansible-playbook` command after pushing changes that need deployment.

Ansible vars files (`ansible/vars/dev.yml`, `ansible/vars/prod.yml`) contain secrets and are gitignored. Use `ansible/vars/common.yml` for shared config.

## Git Workflow

- **Direct pushes to `main` are allowed** for routine changes (docs, backlog, small fixes).
- **Feature branches with PRs are preferred** for non-trivial changes. Create a branch, open a PR, and let CodeRabbit review before merging.
- **Production deploys require a PR.** Merging `main` → `production` must always go through a pull request — never push directly to `production`.
- **CodeRabbit** is installed on this repo and provides automated code reviews on PRs. Wait for its review before merging.
- **Batch commits, push at milestones.** Each build pulls the latest from git, so batch related changes into one push before triggering.
- **Commit and push before building.** Never use `oc start-build --from-dir` with uncommitted changes.
- **Deploy to dev to test changes.** Except for unit tests, always deploy to the dev environment to verify changes work end-to-end. Don't rely solely on local testing.

## Collaboration

- **BACKLOG.md** — Project roadmap. Open items by priority at top, completed items at bottom. Treat as the source of truth for what to work on next.
- **WORKLOG.md** — Session handoff notes. Before ending a session, document what was done, what's in progress, and what's next. Read this before starting work.
