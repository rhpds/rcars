---
title: Development Guide
description: How to set up and run RCARS locally
---

# Development Guide

!!! note "Most development happens on the dev cluster"
    Day-to-day feature work is tested by pushing to `main` and building in the `rcars-dev` namespace on OpenShift. The local setup described here is only needed for major architectural changes, database schema work, or debugging issues that are difficult to reproduce on the cluster.

## Prerequisites

- Python 3.11+ with a virtualenv at `~/.virtualenvs/rcars-v2`
- Node.js 20+ with npm
- Podman with the `agnosticd` machine running
- PostgreSQL (pgvector) and Redis — started automatically by `dev-services.sh`

## Quick Start

```bash
# One-time setup
python3 -m venv ~/.virtualenvs/rcars-v2
source ~/.virtualenvs/rcars-v2/bin/activate
cd src/api && pip install -e ".[dev]"
cd ../frontend && npm install

# Start everything
./dev-services.sh start
```

This starts:

| Service | URL | What it does |
|---|---|---|
| PostgreSQL | localhost:5432 | pgvector database (podman) |
| Redis | localhost:6379 | Task queue + pub/sub (podman) |
| API | localhost:8080 | FastAPI with auto-reload |
| Scan Worker | background | arq worker on `arq:queue:scan` (analysis, refresh, stale, maintenance) |
| Recommend Worker | background | arq worker on `arq:queue:recommend` (advisor queries) |
| Frontend | localhost:3000 | Vite dev server with HMR, proxies `/api` to localhost:8080 |

Logs are written to `/tmp/rcars-api.log`, `/tmp/rcars-scan-worker.log`, `/tmp/rcars-recommend-worker.log`, and `/tmp/rcars-frontend.log`.

Dev services set: `RCARS_DEV_USER=dev@redhat.com`, `RCARS_ADMIN_EMAILS_STR=dev@redhat.com`, `RCARS_CURATOR_EMAILS_STR=dev@redhat.com` (full admin+curator access locally).

- Frontend: [http://localhost:3000](http://localhost:3000)
- API docs: [http://localhost:8080/api/v1/docs](http://localhost:8080/api/v1/docs)

## Running Tests

```bash
source ~/.virtualenvs/rcars-v2/bin/activate
cd src/api
python -m pytest tests/ -v          # All tests
python -m pytest tests/test_db.py   # Just database tests
```

Tests require PostgreSQL and Redis running. The `dev-services.sh start` command handles this.

## Rebuilding Components

Each component runs independently. To restart just one:

```bash
# API — auto-restarts on Python changes (uvicorn --reload)

# Workers — kill and restart
pkill -f "arq rcars"
cd src/api
arq rcars.workers.WorkerSettings &           # scan/ops worker
arq rcars.workers.RecommendWorkerSettings &   # recommend worker

# Frontend — auto-refreshes on file changes (Vite HMR)
```

For OpenShift deployment, only build the changed component:

```bash
# Frontend only (~30s)
ansible-playbook ansible/deploy.yml -e env=dev --tags build-frontend

# API + workers (~3min, restarts api + both workers)
ansible-playbook ansible/deploy.yml -e env=dev --tags build-api
```

## Project Structure

```
src/api/rcars/    Python backend (FastAPI + arq workers)
src/frontend/     React frontend (Vite + TypeScript)
ansible/          OpenShift deployment (Ansible + Jinja2 templates)
alembic/          Database migrations
docs/             Documentation (MkDocs Material)
```

## CLI Usage

```bash
source ~/.virtualenvs/rcars-v2/bin/activate
cd src/api

rcars status                              # Catalog summary
rcars refresh                             # Sync from Babylon CRDs
rcars tag <ci_name> <type> <value>        # Add enrichment tag
rcars set-content-path <ci_name> <path>   # Set custom Showroom path
```
