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

- **Frontend** — React 19 SPA with PatternFly 6 and custom theme (light/dark mode). Pages: Advisor (chat + recommendations), History (past sessions), Browse (catalog + filter sidebar + curation), Workloads (curator infrastructure mappings), Content Analysis (Overlap + Retirement), System (Status, Sync & Analysis, Recent Jobs, Token Usage, Query History). Vite dev server proxies `/api` to backend.
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
│       │   ├── pages/        # AdvisorPage, HistoryPage, BrowsePage, WorkloadsPage, ContentAnalysisPage, RetirementPage, StatusPage, SyncPage, RecentJobsPage, AdminPage
│       │   ├── components/   # RcarsMasthead, RcarsSidebar, advisor/, admin/
│       │   ├── services/     # api.ts (API client)
│       │   └── hooks/        # useAuth, useJobStream, usePrivateMode
│       └── package.json
├── ansible/                  # OpenShift deployment (Ansible + Jinja2)
│   ├── deploy.yml            # Main playbook
│   ├── tasks/                # build-api, build-frontend, apply-manifests, etc.
│   ├── templates/            # manifests-app.yaml.j2, manifests-infra.yaml.j2
│   └── vars/                 # common.yml, dev.yml (gitignored), prod.yml (gitignored)
├── docs/                     # MkDocs Material → https://rhpds.github.io/rcars/
├── BACKLOG.md                # Historical backlog — active items tracked in Jira (RHDPCD-25)
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
- **CI name resolution:** Vector search detects references to catalog items in queries (LB numbers via regex, display names via keyword overlap) and searches by the referenced item's stored embedding. This handles "what's similar to LB2144?" queries that would otherwise return 0 results because lab numbers and event context dilute the query embedding.
- **Environment variables:** All prefixed with `RCARS_` (case-insensitive via Pydantic Settings). See `src/api/rcars/config.py` for full list.

## API Reference

45 endpoints across 6 route modules (advisor, catalog, analysis, admin, auth, health). All prefixed with `/api/v1`. Interactive docs at `/api/v1/docs` when running. Route files: `src/api/rcars/api/routes/`.

## Database

PostgreSQL with pgvector. Schema defined as `SCHEMA_SQL` in `src/api/rcars/db/database.py` — this is the single source of truth. `rcars init-db` runs `create_schema()` (all `CREATE TABLE IF NOT EXISTS`) on every deploy. For column additions to existing tables, add `ALTER TABLE ADD COLUMN IF NOT EXISTS` at the bottom of `SCHEMA_SQL`. For structural changes, use `rcars init-db --drop` to drop and recreate. No Alembic — removed in the content model migration (RHDPCD-359). Key tables: `content_entities` (universal entity registry, card fields for Browse/triage), `babylon_items` (Babylon-specific extension, 1:1 with content_entities), `showroom_analysis` (LLM results + content_hash), `embeddings` (384-dim vectors with content_type + source), `advisor_sessions` (query history), `babylon_item_workloads` + `workload_mapping` (infrastructure metadata), `performance_channels` + `performance_scores` (multi-channel performance metrics + retirement scoring), `retirement_workflow` (retirement lifecycle tracking).

**Soft-delete:** Items that disappear from Babylon CRDs get `retired_at = NOW()` instead of being deleted. All active-item queries filter on `retired_at IS NULL`. Items that reappear in a future scan are automatically un-retired. Browse page has a curator-only "Show Retired" toggle.

## Retirement Analysis — Key Implementation Details

Data flow: RHDP Reporting MCP → `run_reporting_sync()` → `reporting_metrics` table → `/analysis/retirement` endpoint → frontend.

**Cost methodology:** Cost queries include ALL environments (dev/event/prod) — no `PROVISION_FILTERS`. The `avg_cost_per_provision` is computed in Python as `total_cost / provisions` where provisions is PROD-only. This amortizes dev/event infrastructure costs into each production deployment, reflecting the full cost of maintaining an item.

**Query scoping:** Provisions, touched, closed, and dates queries apply `PROVISION_FILTERS` (PROD environment + real users). Cost queries do NOT apply this filter. The `PROVISION_FILTERS` constant in `reporting_sync.py` controls this.

**Catalog completeness:** After importing from the reporting MCP, `get_catalog_base_names()` pulls all unique base names from `catalog_items` (the local catalog — ALL Babylon items). Items in the catalog but missing from reporting data are backfilled with zero values. The orphan cleanup then removes items not in the current sync AND not in the current catalog. Result: Prod tab + Without Prod tab = total unique catalog items.

**Time window:** `windowed_metrics` JSONB column stores pre-computed metrics for each window (3m/6m/9m/12m). The API's `window` parameter (1q/2q/3q/1y) overlays the selected window's metrics and score. No MCP re-query needed.

**Scoring formula:** Four factors scored using percentile ranks among non-zero peers, plus an age discount. Higher score = stronger retirement candidate. Max achievable ~80.

| Factor | Max | Method | Points |
|---|---|---|---|
| Usage (provisions) | 25 | Percentile buckets | 0, 3, 10, 18, 22, 25 (fixed tiers) |
| Pipeline (touched) | 15 | Percentile buckets | 0, 4, 10, 15 (fixed tiers) |
| Closed Sales | 25 | Percentile buckets | 0, 5, 15, 25 (fixed tiers) |
| Cost Efficiency (ROI) | 15 | Continuous percentile | `round(15 * (1 - pct/100))` — smooth 0-15 |
| Age discount | -30/-10 | ≤90 days: -30, ≤180 days: -10 | Applied after sum, floor at 0 |

Zero-value items (no provisions, no pipeline, no sales, cost with no sales) always receive maximum points for that factor. The `score_breakdown` dict is stored alongside each score in `windowed_metrics`, containing per-factor points, levels, reasons with actual values and percentile ranks, and a one-line summary sentence.

**Score breakdown popover:** Clicking a score badge in the UI shows a popover with per-factor bars, points (e.g. "+10/25"), and plain-English explanations including raw values and percentile context (e.g. "28 provisions — below median (percentile 28 of items with activity)").

**Mute/ignore:** Curators can mute items for 30 days via "Mute 30d" button in the expanded row. Muted items are excluded from stats and counts. The "Muted" filter in the Status filter group shows only muted items. Stored as `ignored_until DATE` on `reporting_metrics`. API endpoints: `PUT /analysis/retirement/ignore/{base_name}` (sets 30-day mute), `DELETE /analysis/retirement/ignore/{base_name}` (unmutes).

**Scoring thresholds:** High ≥ 55, Review ≥ 35, Keepers < 35 (frontend and CLI).

**Ansible deployment:** Reporting MCP env vars must be on BOTH the API deployment and scan-worker deployment (template: `manifests-app.yaml.j2`). The secret is in `manifests-infra.yaml.j2`.

## CLI

Entry point: `rcars` (installed via `pip install -e ".[dev]"`). Run `rcars --help` for full command list. Key commands: `init-db`, `refresh`, `scan`, `status`, `serve`. Subgroups: `rcars infra`, `rcars workload`, `rcars reporting-db` (sync/show/status for reporting metrics).

## Build & Deploy

Every tag applies all manifests first (idempotent), so the BuildConfig always matches the branch in `git_ref`. No more tag ordering bugs.

```bash
# Full deploy (manifests + build API + build frontend + migrate + smoke test)
ansible-playbook ansible/deploy.yml -e env=dev --tags full

# API only (manifests + build API + migrate + smoke test, ~3min)
ansible-playbook ansible/deploy.yml -e env=dev --tags api

# Frontend only (manifests + build frontend + smoke test, ~30s)
ansible-playbook ansible/deploy.yml -e env=dev --tags frontend

# Config only (manifests only — env vars, user lists, secrets, no builds)
ansible-playbook ansible/deploy.yml -e env=dev --tags apply-config
```

**Schema setup** runs automatically after every API build (`--tags api` or `--tags full`). `rcars init-db` executes on the new pod, running `create_schema()` which uses `CREATE TABLE IF NOT EXISTS` — idempotent and safe to repeat. For structural schema changes, run `rcars init-db --drop` manually via port-forward (requires `RCARS_ALLOW_DROP=true` or localhost connection).

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

- **Jira Epic [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25)** — Active backlog. Source of truth for prioritization and tracking. `BACKLOG.md` retains completed item history only.
- **WORKLOG.md** — Session handoff notes. Before ending a session, document what was done, what's in progress, and what's next. Read this before starting work.
