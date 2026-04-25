---
title: Development Guide
description: How to set up and run RCARS locally
---

# Development Guide

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
| Worker | background | arq worker processing jobs |
| Frontend | localhost:3000 | Vite dev server with HMR |

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
# Worker — kill and restart
pkill -f "arq rcars" && cd src/api && arq rcars.workers.WorkerSettings &

# Frontend — auto-refreshes on file changes (Vite HMR)
```

## Project Structure

```
src/api/          Python backend (FastAPI + arq workers)
src/frontend/     React frontend (Vite + TypeScript)
src/rcars/        Legacy monolith (reference only)
ansible/          OpenShift deployment
docs/             Documentation (MkDocs)
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
