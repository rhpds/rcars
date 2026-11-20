# RCARS — Agent Instructions

RHDP Content Advisory & Recommendation System. Matches Red Hat Demo Platform catalog items (and OSSPA portfolio architectures) to events, opportunities, and user queries using vector search, LLM triage, and LLM rationale.

This file is the single source of truth for agent guidance. `CLAUDE.md` only imports it.

## Architecture

Four deployments on OpenShift: React SPA → FastAPI API → arq workers + Redis → PostgreSQL with pgvector.

- **Frontend** (`src/frontend`) — React 19, PatternFly 6, Vite + TypeScript, light/dark theme. Routes are in `src/App.tsx`: Advisor (+ History), Browse (+ Workloads), Analysis (Overlap, NonProd, Performance, Retirement, Field Source), System (Status, Sync, Jobs, Tokens, Queries, API Keys, Roles, Vocabulary). Vite proxies `/api` to the backend.
- **API** (`src/api/rcars/api`) — FastAPI + uvicorn. Creates jobs and relays progress over SSE from Redis pub/sub. It never calls the LLM itself. Routes live in `src/api/rcars/api/routes/`; interactive docs at `/api/v1/docs`.
- **Scan worker** — arq queue `arq:queue:scan`. Showroom analysis, catalog refresh, stale checks, nightly maintenance (Babylon and OSSPA sub-pipelines), OSSPA sync. 5 jobs, 600s timeout.
- **Recommend worker** — arq queue `arq:queue:recommend`. Advisor queries and chat only, so long scans cannot starve it. 120s timeout; `RCARS_RECOMMEND_MAX_JOBS` (default 15) per replica; scale with `recommend_worker_replicas` in Ansible vars. Sync LLM calls run via `asyncio.to_thread`.
- **PostgreSQL** — pgvector, 768-dim embeddings (nomic-embed-text-v1.5 served by vLLM).
- **Redis** — arq queues, SSE pub/sub, job progress.
- **LLM** — LiteMaaS (RHDP MaaS) only. The Vertex/Anthropic fallback was removed (RHDPCD-2226); do not reintroduce it. Settings are in `src/api/rcars/config.py`.

## Repository Layout

```text
src/api/rcars/        # Python 3.11 package: api/, workers/, services/, db/, prompts/, cli.py, config.py
src/api/tests/        # pytest suite
src/api/scripts/      # Opt-in maintenance scripts (rebuild_babylon_analysis.py)
src/frontend/         # React SPA (pages/, components/, hooks/, services/api.ts)
ansible/              # deploy.yml, tasks/, templates/*.j2, vars/ (dev.yml and prod.yml are gitignored)
docs/                 # MkDocs Material → https://rhpds.github.io/rcars/ (docs/superpowers/specs/ is excluded from the site)
tools/                # API login scripts, OPL vocabulary sync, pgvector image build notes
dev-services.sh       # Local launcher
graphify-out/         # Knowledge graph (committed)
```

## Running Locally

```bash
./dev-services.sh start [--role admin|curator|user]   # default: admin
./dev-services.sh stop | restart | status | frontend | db-pull
```

`start` runs PostgreSQL, Redis, and the embedding server in podman, then `init-db`, the API, both workers, and the frontend. `db-pull` restores the dev database locally (needs `RCARS_DEV_KUBECONFIG`).

- Frontend http://localhost:3000, API docs http://localhost:8080/api/v1/docs
- Logs: `/tmp/rcars-{api,scan-worker,recommend-worker,frontend}.log`
- `RCARS_DEV_USER=dev@redhat.com` is set. `--role` picks access: `admin` (all), `curator` (catalog + analysis), `user` (catalog, advisor, performance).

## Tests and Builds

```bash
source ~/.virtualenvs/rcars-v2/bin/activate
(cd src/api && python -m pytest tests/ -q -m "not integration")
(cd src/frontend && npm run build)        # also: npm test
```

Needs PostgreSQL+pgvector on localhost:5432 and Redis on localhost:6379. Create the `rcars_test` database once (`dev-services.sh` does not); override with `RCARS_TEST_DATABASE_URL`. Always point it at a database with `test` in its name: many fixtures drop or delete tables, and not all of them check the name. `integration` tests need a live Babylon cluster.

## Key Patterns

- **Structured JSON from every LLM call.** No prose parsing. Use `parse_analysis_response()` (handles truncation).
- **Long jobs return `{job_id}`.** Workers do the work; the API relays SSE.
- **Auth** (`api/middleware/auth.py`, checked in order): dev bypass (`RCARS_DEV_USER`), API keys (`X-API-Key`), K8s ServiceAccount bearer tokens via TokenReview, OAuth proxy headers (`X-Forwarded-Email`). Dependencies: `require_auth`, `require_curator`, `require_admin`. Roles come from `RCARS_CURATOR_EMAILS_STR` / `RCARS_ADMIN_EMAILS_STR` and the `role_assignments` table (OpenShift groups).
- **Chat routing.** An LLM router picks one of 8 intents (recommend, overlap, performance, item_facts, item_chat, infrastructure, help, out_of_scope). Each has a deterministic handler. Add intents in `services/chat/registry.py`. `RCARS_CHAT_INTENT_ROLES_STR` gates intents by role.
- **Content-type drivers** (`services/recommender/drivers/`): `HandsOnDriver` (labs/demos) and `ArchitectureDriver` (portfolio architectures) own triage guidance, rationale input, and card format.
- **Sibling propagation.** CIs sharing a Showroom (same URL + commit SHA, resolved by batch `git ls-remote`) are scanned once and analysis plus embeddings are copied to the siblings. Falls back to ref grouping if resolution fails.
- **CI name resolution.** Vector search spots catalog references in a query (LB numbers, display names) and searches by that item's stored embedding.
- **Default visibility.** `content_entities.status` (`prod`/`event`/`dev`) gates Advisor and Browse for every source. Default filter: `status = 'prod' AND retired_at IS NULL`. Curator views skip the status clause.
- **Soft delete.** Items missing from Babylon get `retired_at = NOW()`; they are un-retired if they return. Active queries filter `retired_at IS NULL`.
- **Malformed Babylon data is an upstream bug.** Do not add defensive guards for it.
- **Logging.** structlog JSON with `component`, `job_id`, `action`. Verbose is preferred.
- **Config.** All env vars use the `RCARS_` prefix (Pydantic Settings).

Performance scoring, retirement, overlap, and field-source details are in `docs/architecture/`. Read those before changing the scoring or retirement code. Two rules worth remembering: the Performance page is public by default (`RCARS_PERFORMANCE_PUBLIC`; to restrict it, see the access model in `docs/architecture/performance-analysis.md`), and cost queries include all environments while provision queries are PROD-only.

## Database

`SCHEMA_SQL` in `src/api/rcars/db/database.py` is the single source of truth. `rcars init-db` runs `create_schema()` (`CREATE TABLE IF NOT EXISTS`) on every API deploy. Add columns with `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` at the bottom of `SCHEMA_SQL`. For structural changes, run `rcars init-db --drop` by hand (needs `RCARS_ALLOW_DROP=true` or a localhost connection). There is no Alembic. Rebuilds of analysis data must be dry-run first and never use table drops (see `docs/operations/showroom-analysis-rebuild.md`).

The core tables are `content_entities` (universal registry), `babylon_items` and `portfolio_architectures` (source extensions), `showroom_analysis` and `architecture_analysis`, and `embeddings`.

## CLI

`rcars --help` lists everything. Main commands: `init-db`, `refresh`, `scan`, `status`, `serve`. Groups: `infra`, `workload`, `reporting-db`, `osspa`, `vocab`.

## Build and Deploy

Always deploy to **dev first**, verify, then prod. Only build the component you changed.

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags api           # manifests + API build + init-db + smoke test
ansible-playbook ansible/deploy.yml -e env=dev --tags frontend      # manifests + frontend build + smoke test
ansible-playbook ansible/deploy.yml -e env=dev --tags full          # both
ansible-playbook ansible/deploy.yml -e env=dev --tags apply-config  # manifests only (env vars, secrets)
```

- Every tag except `mgmt-rbac` applies all manifests first, so the BuildConfig always matches `git_ref`.
- Dev uses `git_ref: main`. Prod uses a git tag (`ansible/vars/prod.yml`); update it before a prod deploy.
- **Pushing does not trigger a build.** There is no webhook. Commit and push first, then run Ansible. Never use `oc start-build --from-dir` with uncommitted changes.
- Reporting MCP env vars must be set on both the API and the scan-worker deployments (`manifests-app.yaml.j2`); the secret is in `manifests-infra.yaml.j2`.
- Vars files hold secrets and are gitignored. Shared config goes in `ansible/vars/common.yml`.
- Use `~/devel/secrets/rcars-mgmt-{dev,prod}.kubeconfig` if personal `oc` contexts have expired.

## Git Workflow

- Feature branch → PR → CodeRabbit review → squash merge into `main`. No direct pushes to `main`.
- Commit subject: `[RHDPCD-123] Imperative description` (Jira key required; ask if unsure).
- Batch commits; push at milestones.
- Before a PR is merge-ready, run `graphify update .` and commit `graphify-out/` on the branch.
- Production release: test on dev → tag `main` (`vX.Y.Z`) → GitHub release → set `git_ref` in `ansible/vars/prod.yml` → deploy with `-e env=prod`. There is no `production` branch.
- Deploy to dev to verify end-to-end; unit tests alone are not enough.

## Backlog and Docs

- **Jira epic [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25)** is the backlog. Keep issues current as work moves. Retirement tickets go under RHDPCD-2191.
- Design specs live in `docs/superpowers/specs/`. Update the user-facing docs in `docs/` when behavior changes.

## graphify

`graphify-out/graph.json` is a knowledge graph of this repo. For codebase questions, run `graphify query "<question>"` first. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for one concept. Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review. After code changes, run `graphify update .` (AST-only, no API cost).
