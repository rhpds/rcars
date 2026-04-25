# RCARS Rearchitecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Break the RCARS monolith into a three-tier architecture (React frontend, FastAPI JSON API, arq workers) with Redis for task queuing and SSE-based real-time progress streaming.

**Architecture:** Clean-break rebuild. The API serves JSON only — no HTML rendering. The React frontend consumes the API via `/api/v1/*`. Background workers handle all LLM operations (recommendations, analysis, scanning) via arq task queues on Redis. The API enqueues jobs and relays worker progress to browsers via SSE. All containers use Red Hat UBI base images.

**Tech Stack:** Python 3.11 (FastAPI, arq, psycopg, sentence-transformers), TypeScript/React 19 (Vite, React Router), Redis 7, PostgreSQL 16 + pgvector, nginx (UBI), Ansible for OpenShift deployment.

**Spec:** `docs/superpowers/specs/2026-04-25-rearchitecture-api-design.md`

**Existing code reference:** The current monolith at `src/rcars/` contains business logic (recommender pipeline, analyzer, catalog reader, embeddings, prompts) that should be ported — not rewritten — into the new project structure. Read the existing code before implementing each service module.

---

## Phase 1: Project Structure & Foundation

### Task 1: Create new project directory structure

**Files:**
- Create: `src/api/pyproject.toml`
- Create: `src/api/requirements.txt`
- Create: `src/api/rcars/__init__.py`
- Create: `src/api/rcars/config.py`
- Create: `src/frontend/package.json`
- Create: `src/frontend/tsconfig.json`
- Create: `src/frontend/vite.config.ts`

This task scaffolds the new directory layout without deleting any existing code. The old `src/rcars/` stays in place as a reference throughout the migration.

- [ ] **Step 1: Create API project skeleton**

```bash
mkdir -p src/api/rcars/{api/routes,api/middleware,workers,services/recommender,db/queries,prompts}
mkdir -p src/api/tests
```

- [ ] **Step 2: Create `src/api/pyproject.toml`**

```toml
[project]
name = "rcars"
version = "2.0.0"
requires-python = ">=3.11"

dependencies = [
    "alembic>=1.13",
    "arq>=0.26",
    "click>=8.1",
    "fastapi>=0.115.0",
    "httpx>=0.27.0",
    "kubernetes>=29.0",
    "psycopg[binary]>=3.1",
    "psycopg-pool>=3.2",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "redis>=5.0",
    "rich>=13.0",
    "structlog>=24.0",
    "uvicorn>=0.30.0",
    "anthropic[vertex]>=0.40.0",
    "sentence-transformers>=3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.5",
    "httpx>=0.27.0",
]

[project.scripts]
rcars = "rcars.cli:cli"

[tool.setuptools.packages.find]
where = ["."]

[tool.setuptools.package-data]
rcars = ["prompts/*"]

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Create `src/api/requirements.txt`** (for Containerfile pip install)

```
-e .[dev]
```

- [ ] **Step 4: Create frontend project skeleton**

```bash
mkdir -p src/frontend/src/{pages,components/{lcars,advisor,browse,admin},hooks,services,styles}
mkdir -p src/frontend/public
```

- [ ] **Step 5: Initialize frontend with Vite**

```bash
cd src/frontend && npm create vite@latest . -- --template react-ts
```

Then update `package.json` to add dependencies:

```bash
cd src/frontend && npm install react-router-dom@7
cd src/frontend && npm install -D @types/react-router-dom
```

- [ ] **Step 6: Create `src/frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
```

- [ ] **Step 7: Commit**

```bash
git add src/api/ src/frontend/
git commit -m "project: Scaffold new three-tier directory structure"
```

---

### Task 2: Configuration module

**Files:**
- Create: `src/api/rcars/config.py`
- Create: `src/api/tests/test_config.py`

Port the existing `src/rcars/config.py` settings to use Pydantic Settings with env var loading. Add new settings for Redis and arq.

- [ ] **Step 1: Write config tests**

```python
# src/api/tests/test_config.py
import os
import pytest
from rcars.config import Settings


def test_defaults():
    s = Settings(database_url="postgresql://test:test@localhost/test", redis_url="redis://localhost:6379")
    assert s.model == "claude-sonnet-4-6"
    assert s.triage_model == "claude-haiku-4-5"
    assert s.vector_cutoff == 0.55
    assert s.rationale_top_n == 5
    assert s.triage_cutoff == 30


def test_curator_check():
    s = Settings(
        database_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379",
        curator_emails=["alice@redhat.com", "Bob@REDHAT.COM"],
    )
    assert s.is_curator("alice@redhat.com")
    assert s.is_curator("bob@redhat.com")
    assert not s.is_curator("charlie@redhat.com")


def test_admin_check():
    s = Settings(
        database_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379",
        admin_emails=["admin@redhat.com"],
    )
    assert s.is_admin("admin@redhat.com")
    assert not s.is_admin("user@redhat.com")


def test_use_vertex():
    s = Settings(
        database_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379",
        vertex_project_id="my-project",
    )
    assert s.use_vertex is True

    s2 = Settings(
        database_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379",
    )
    assert s2.use_vertex is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_config.py -v`
Expected: FAIL — `rcars.config` does not exist yet.

- [ ] **Step 3: Implement config module**

```python
# src/api/rcars/config.py
from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "RCARS_", "case_sensitive": False}

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # LLM
    model: str = "claude-sonnet-4-6"
    vertex_project_id: str = ""
    cloud_ml_region: str = "us-east5"
    anthropic_api_key: str = ""

    # Scanning
    max_parallel: int = 5
    clone_dir: str = "/tmp/rcars-clones"

    # Recommender pipeline
    vector_cutoff: float = 0.55
    triage_model: str = "claude-haiku-4-5"
    triage_cutoff: int = 30
    rationale_model: str = "claude-sonnet-4-6"
    rationale_top_n: int = 5

    # Babylon K8s
    kubeconfig_path: str = ""
    agnosticv_component_namespace: str = "babylon-config"
    catalog_namespaces: list[str] = [
        "babylon-catalog-prod",
        "babylon-catalog-dev",
        "babylon-catalog-event",
    ]

    # Showroom URL variable names
    showroom_url_vars: list[str] = [
        "ocp4_workload_showroom_content_git_repo",
        "showroom_git_repo",
    ]
    showroom_ref_vars: list[str] = [
        "ocp4_workload_showroom_content_git_repo_ref",
        "showroom_git_repo_ref",
    ]

    # Auth / roles
    curator_emails: list[str] = []
    admin_emails: list[str] = []
    dev_user: str = ""
    sa_allowlist: list[str] = []

    # Ops
    stale_days: int = 3

    @property
    def use_vertex(self) -> bool:
        return bool(self.vertex_project_id)

    def is_curator(self, email: str) -> bool:
        return email.lower() in [e.lower() for e in self.curator_emails]

    def is_admin(self, email: str) -> bool:
        return email.lower() in [e.lower() for e in self.admin_emails]

    def get_anthropic_client(self):
        if self.vertex_project_id:
            from anthropic import AnthropicVertex
            return AnthropicVertex(project_id=self.vertex_project_id, region=self.cloud_ml_region)
        if self.anthropic_api_key:
            from anthropic import Anthropic
            return Anthropic(api_key=self.anthropic_api_key)
        return None
```

- [ ] **Step 4: Create `src/api/rcars/__init__.py`**

```python
# src/api/rcars/__init__.py
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_config.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/config.py src/api/rcars/__init__.py src/api/tests/test_config.py
git commit -m "config: Add Pydantic Settings with Redis and arq support"
```

---

### Task 3: Structured logging module

**Files:**
- Create: `src/api/rcars/logging.py`
- Create: `src/api/tests/test_logging.py`

Set up structlog with JSON output, component tagging, and job correlation IDs per the spec's observability requirements.

- [ ] **Step 1: Write logging tests**

```python
# src/api/tests/test_logging.py
import json
import io
import structlog
from rcars.logging import setup_logging, get_logger


def test_logger_outputs_json(capsys):
    setup_logging(level="INFO", component="api")
    logger = get_logger()
    logger.info("test_event", action="test", detail="hello")
    captured = capsys.readouterr()
    line = json.loads(captured.out.strip())
    assert line["component"] == "api"
    assert line["action"] == "test"
    assert line["detail"] == "hello"
    assert "timestamp" in line


def test_logger_with_job_id(capsys):
    setup_logging(level="INFO", component="worker")
    logger = get_logger().bind(job_id="abc123")
    logger.info("picked_up", action="picked_up")
    captured = capsys.readouterr()
    line = json.loads(captured.out.strip())
    assert line["job_id"] == "abc123"
    assert line["component"] == "worker"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_logging.py -v`
Expected: FAIL — `rcars.logging` does not exist.

- [ ] **Step 3: Implement logging module**

```python
# src/api/rcars/logging.py
from __future__ import annotations

import structlog


def setup_logging(level: str = "INFO", component: str = "api") -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.CallsiteParameterAdder(
                [structlog.processors.CallsiteParameter.FUNC_NAME],
            ),
            _add_component(component),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_name(level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _add_component(component: str):
    def processor(logger, method_name, event_dict):
        event_dict["component"] = component
        return event_dict
    return processor


def get_logger() -> structlog.BoundLogger:
    return structlog.get_logger()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_logging.py -v`
Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/logging.py src/api/tests/test_logging.py
git commit -m "logging: Add structlog JSON logging with component and job_id tagging"
```

---

### Task 4: Database layer — schema and connection pool

**Files:**
- Create: `src/api/rcars/db/database.py`
- Create: `src/api/rcars/db/models.py`
- Create: `src/api/rcars/db/__init__.py`
- Create: `src/api/alembic/` (baseline migration)
- Create: `src/api/tests/test_db.py`

Port the database layer from the existing `src/rcars/db.py`. Use psycopg_pool for connection management. All tables created via Alembic baseline migration. The existing `db.py` has ~1015 lines of SQL queries — port them into focused query modules.

- [ ] **Step 1: Write database connection and schema tests**

```python
# src/api/tests/test_db.py
import os
import pytest
from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.drop_schema()
    database.close()


def test_schema_creation(db):
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        )
        tables = [row["table_name"] for row in cur.fetchall()]
    assert "catalog_items" in tables
    assert "showroom_analysis" in tables
    assert "embeddings" in tables
    assert "enrichment_tags" in tables
    assert "token_usage" in tables
    assert "advisor_sessions" in tables
    assert "jobs" in tables
    assert "analysis_log" in tables
    assert "api_keys" in tables


def test_upsert_and_get_catalog_item(db):
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Test Item",
        "category": "Workshops",
        "stage": "prod",
    }
    db.upsert_catalog_item(item)
    result = db.get_catalog_item("test.item.prod")
    assert result is not None
    assert result["display_name"] == "Test Item"


def test_job_lifecycle(db):
    job_id = db.create_job(
        job_type="recommend",
        queue="recommend",
        created_by="test@redhat.com",
    )
    assert job_id is not None

    job = db.get_job(job_id)
    assert job["status"] == "queued"

    db.update_job_status(job_id, "running")
    job = db.get_job(job_id)
    assert job["status"] == "running"

    db.complete_job(job_id, result_json={"results": 5})
    job = db.get_job(job_id)
    assert job["status"] == "complete"
    assert job["result_json"]["results"] == 5
    assert job["completed_at"] is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_db.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement database module**

Port the existing `src/rcars/db.py` into `src/api/rcars/db/database.py`. The Database class should keep the same method signatures for catalog, analysis, embeddings, enrichment, and token_usage operations — they're well-tested and correct. Add new methods for the `jobs` table:

```python
# src/api/rcars/db/database.py
# Key additions beyond ported code:

import uuid
from datetime import datetime, timezone


class Database:
    # ... (port existing __init__, pool management, catalog, analysis,
    #      embeddings, enrichment, token_usage methods from src/rcars/db.py)

    # NEW: Job management methods
    def create_job(self, job_type: str, queue: str, created_by: str | None = None) -> str:
        job_id = str(uuid.uuid4())
        with self.pool.connection() as conn:
            conn.execute(
                """INSERT INTO jobs (id, job_type, status, queue, created_by, created_at)
                   VALUES (%s, %s, 'queued', %s, %s, %s)""",
                (job_id, job_type, queue, created_by, datetime.now(timezone.utc)),
            )
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        with self.pool.connection() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            return cur.fetchone()

    def update_job_status(self, job_id: str, status: str, progress_json: dict | None = None) -> None:
        with self.pool.connection() as conn:
            if status == "running":
                conn.execute(
                    "UPDATE jobs SET status = %s, started_at = %s WHERE id = %s",
                    (status, datetime.now(timezone.utc), job_id),
                )
            else:
                conn.execute(
                    "UPDATE jobs SET status = %s, progress_json = %s WHERE id = %s",
                    (status, Json(progress_json) if progress_json else None, job_id),
                )

    def complete_job(self, job_id: str, result_json: dict | None = None, error: str | None = None) -> None:
        status = "failed" if error else "complete"
        with self.pool.connection() as conn:
            conn.execute(
                """UPDATE jobs SET status = %s, result_json = %s, error = %s, completed_at = %s
                   WHERE id = %s""",
                (status, Json(result_json) if result_json else None, error,
                 datetime.now(timezone.utc), job_id),
            )

    def fail_job(self, job_id: str, error: str) -> None:
        self.complete_job(job_id, error=error)

    def list_jobs(self, limit: int = 50, job_type: str | None = None) -> list[dict]:
        with self.pool.connection() as conn:
            if job_type:
                cur = conn.execute(
                    "SELECT * FROM jobs WHERE job_type = %s ORDER BY created_at DESC LIMIT %s",
                    (job_type, limit),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT %s", (limit,)
                )
            return cur.fetchall()
```

The `create_schema()` method should include the full schema from the spec. Port all existing table definitions and add the new `jobs` and `api_keys` tables. Add `scope` column to `catalog_items` and `content_path` column for non-standard Showroom repos.

Read the existing `src/rcars/db.py` carefully — it has ~50 methods. Port them all. Do not rewrite query logic that already works.

- [ ] **Step 4: Create `src/api/rcars/db/__init__.py`**

```python
# src/api/rcars/db/__init__.py
from rcars.db.database import Database

__all__ = ["Database"]
```

- [ ] **Step 5: Create Pydantic models for API responses**

```python
# src/api/rcars/db/models.py
from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime


class CatalogItemSummary(BaseModel):
    ci_name: str
    display_name: str | None = None
    category: str | None = None
    stage: str | None = None
    scope: str | None = None
    showroom_url: str | None = None
    is_stale: bool | None = False
    has_analysis: bool = False


class CatalogItemDetail(CatalogItemSummary):
    product: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    showroom_ref: str | None = None
    content_path: str | None = None
    analysis: ShowroomAnalysis | None = None
    tags: list[EnrichmentTag] = []


class ShowroomAnalysis(BaseModel):
    summary: str | None = None
    content_type: str | None = None
    products: list[str] = []
    audience: list[str] = []
    topics: list[str] = []
    difficulty: str | None = None
    estimated_duration_min: int | None = None
    modules: list[dict] = []
    learning_objectives: dict | None = None
    event_fit: dict | None = None
    last_analyzed: datetime | None = None
    is_stale: bool = False


class EnrichmentTag(BaseModel):
    id: int
    tag_type: str
    tag_value: str
    added_by: str | None = None
    added_at: datetime | None = None


class JobResponse(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    id: str
    job_type: str
    status: str
    queue: str
    created_by: str | None = None
    progress_json: dict | None = None
    result_json: dict | None = None
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PaginatedResponse(BaseModel):
    items: list
    total: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_db.py -v`
Expected: All 3 tests PASS (requires PostgreSQL running locally).

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/db/ src/api/tests/test_db.py
git commit -m "db: Port database layer with job management and Pydantic models"
```

---

## Phase 2: API & Workers Core

### Task 5: FastAPI application shell with auth middleware

**Files:**
- Create: `src/api/rcars/api/app.py`
- Create: `src/api/rcars/api/deps.py`
- Create: `src/api/rcars/api/middleware/auth.py`
- Create: `src/api/rcars/api/middleware/logging.py`
- Create: `src/api/rcars/api/routes/health.py`
- Create: `src/api/rcars/api/routes/auth.py`
- Create: `src/api/tests/test_app.py`

- [ ] **Step 1: Write app and auth tests**

```python
# src/api/tests/test_app.py
import pytest
from fastapi.testclient import TestClient
from rcars.api.app import create_app
from rcars.config import Settings


@pytest.fixture
def client():
    settings = Settings(
        database_url="postgresql://rcars:dev@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="test@redhat.com",
        admin_emails=["test@redhat.com"],
        curator_emails=["test@redhat.com"],
    )
    app = create_app(settings)
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_auth_me(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@redhat.com"
    assert "admin" in data["roles"]
    assert "curator" in data["roles"]


def test_auth_me_unauthenticated():
    settings = Settings(
        database_url="postgresql://rcars:dev@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
    )
    app = create_app(settings)
    client = TestClient(app)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_app.py -v`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement auth middleware**

```python
# src/api/rcars/api/middleware/auth.py
from __future__ import annotations

from fastapi import Request, HTTPException
from rcars.config import Settings


def get_current_user(request: Request) -> str:
    settings: Settings = request.app.state.settings
    if settings.dev_user:
        return settings.dev_user
    email = request.headers.get("X-Forwarded-Email", "")
    if not email:
        email = request.headers.get("X-Forwarded-User", "")
    return email


def require_auth(request: Request) -> str:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_curator(request: Request) -> str:
    user = require_auth(request)
    settings: Settings = request.app.state.settings
    if not settings.is_curator(user) and not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Curator role required")
    return user


def require_admin(request: Request) -> str:
    user = require_auth(request)
    settings: Settings = request.app.state.settings
    if not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
```

- [ ] **Step 4: Implement logging middleware**

```python
# src/api/rcars/api/middleware/logging.py
from __future__ import annotations

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000)

        logger.info(
            "request_complete",
            action="request_complete",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        return response
```

- [ ] **Step 5: Implement health and auth routes**

```python
# src/api/rcars/api/routes/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request):
    # Check DB and Redis connectivity
    db = request.app.state.db
    redis = request.app.state.redis
    checks = {"database": False, "redis": False}
    try:
        with db.pool.connection() as conn:
            conn.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        pass
    try:
        await redis.ping()
        checks["redis"] = True
    except Exception:
        pass

    all_ok = all(checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}
```

```python
# src/api/rcars/api/routes/auth.py
from fastapi import APIRouter, Depends, Request
from rcars.api.middleware.auth import require_auth
from rcars.config import Settings

router = APIRouter()


@router.get("/auth/me")
async def auth_me(request: Request, user: str = Depends(require_auth)):
    settings: Settings = request.app.state.settings
    roles = ["user"]
    if settings.is_curator(user):
        roles.append("curator")
    if settings.is_admin(user):
        roles.append("admin")
    return {"email": user, "roles": roles}
```

- [ ] **Step 6: Implement FastAPI app factory**

```python
# src/api/rcars/api/app.py
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis.asyncio import Redis

from rcars.config import Settings
from rcars.db import Database
from rcars.logging import setup_logging
from rcars.api.middleware.logging import RequestLoggingMiddleware
from rcars.api.routes import health, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    setup_logging(level="INFO", component="api")

    app.state.db = Database(settings.database_url)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    yield

    app.state.db.close()
    await app.state.redis.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="RCARS API",
        version="2.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")

    return app
```

- [ ] **Step 7: Create `__init__.py` files**

```python
# src/api/rcars/api/__init__.py
# src/api/rcars/api/routes/__init__.py
# src/api/rcars/api/middleware/__init__.py
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_app.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 9: Commit**

```bash
git add src/api/rcars/api/ src/api/tests/test_app.py
git commit -m "api: FastAPI app shell with auth middleware and health routes"
```

---

### Task 6: Redis integration and job streaming (SSE)

**Files:**
- Create: `src/api/rcars/api/streaming.py`
- Create: `src/api/tests/test_streaming.py`

This is the core plumbing — the API's ability to enqueue jobs, subscribe to Redis pub/sub, and relay progress as SSE events.

- [ ] **Step 1: Write streaming tests**

```python
# src/api/tests/test_streaming.py
import asyncio
import json
import pytest
from redis.asyncio import Redis
from rcars.api.streaming import JobProgressRelay, translate_to_user_message


def test_translate_vector_search():
    msg = {"phase": "vector_search", "status": "complete", "candidates": 42}
    result = translate_to_user_message(msg)
    assert "42" in result
    assert "candidates" in result.lower() or "found" in result.lower()


def test_translate_triage_progress():
    msg = {"phase": "triage", "status": "progress", "current": 12, "total": 42}
    result = translate_to_user_message(msg)
    assert "12" in result
    assert "42" in result


def test_translate_complete():
    msg = {"phase": "complete", "results": 5}
    result = translate_to_user_message(msg)
    assert "complete" in result.lower() or "Complete" in result


@pytest.mark.asyncio
async def test_relay_publishes_and_receives():
    redis = Redis.from_url("redis://localhost:6379", decode_responses=True)
    relay = JobProgressRelay(redis)
    job_id = "test-job-123"

    received = []

    async def collect():
        async for msg in relay.subscribe(job_id):
            received.append(msg)
            if msg.get("phase") == "complete":
                break

    task = asyncio.create_task(collect())

    await asyncio.sleep(0.1)
    await relay.publish(job_id, {"phase": "vector_search", "status": "started"})
    await relay.publish(job_id, {"phase": "complete", "results": 3})

    await asyncio.wait_for(task, timeout=5.0)
    await redis.close()

    assert len(received) == 2
    assert received[-1]["phase"] == "complete"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/api && python -m pytest tests/test_streaming.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement job progress relay and SSE translation**

```python
# src/api/rcars/api/streaming.py
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
from redis.asyncio import Redis
from starlette.responses import StreamingResponse
import structlog

logger = structlog.get_logger()


class JobProgressRelay:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def publish(self, job_id: str, message: dict) -> None:
        channel = f"job:{job_id}"
        await self.redis.publish(channel, json.dumps(message))

    async def subscribe(self, job_id: str) -> AsyncGenerator[dict, None]:
        channel = f"job:{job_id}"
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    yield data
                    if data.get("phase") == "complete" or data.get("phase") == "failed":
                        break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()


def translate_to_user_message(msg: dict) -> str:
    phase = msg.get("phase", "")
    status = msg.get("status", "")

    if phase == "vector_search":
        if status == "started":
            return "Searching content library..."
        if status == "complete":
            return f"Found {msg.get('candidates', 0)} candidates"

    if phase == "triage":
        if status == "started":
            return f"Evaluating relevance of {msg.get('total', '?')} candidates..."
        if status == "progress":
            return f"Evaluating relevance ({msg['current']} of {msg['total']})..."
        if status == "complete":
            return f"{msg.get('relevant', 0)} relevant items identified"

    if phase == "rationale":
        if status == "started":
            return f"Generating detailed analysis for top {msg.get('top_n', '?')} matches..."
        if status == "progress":
            return f"Generating detailed analysis ({msg['current']} of {msg['top_n']})..."
        if status == "complete":
            return "Analysis complete"

    if phase == "complete":
        return "Complete"

    if phase == "failed":
        return f"Error: {msg.get('error', 'Unknown error')}"

    return f"{phase}: {status}"


async def sse_stream(relay: JobProgressRelay, job_id: str) -> AsyncGenerator[str, None]:
    async for msg in relay.subscribe(job_id):
        user_message = translate_to_user_message(msg)
        event_data = {**msg, "user_message": user_message}
        yield f"data: {json.dumps(event_data)}\n\n"


def create_sse_response(relay: JobProgressRelay, job_id: str) -> StreamingResponse:
    return StreamingResponse(
        sse_stream(relay, job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/api && python -m pytest tests/test_streaming.py -v`
Expected: All 4 tests PASS (requires Redis running locally).

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/api/streaming.py src/api/tests/test_streaming.py
git commit -m "streaming: Job progress relay via Redis pub/sub with SSE translation"
```

---

### Task 7: arq worker settings and base task infrastructure

**Files:**
- Create: `src/api/rcars/workers/settings.py`
- Create: `src/api/rcars/workers/base.py`
- Create: `src/api/rcars/workers/__init__.py`
- Create: `src/api/tests/test_workers.py`

- [ ] **Step 1: Write worker base tests**

```python
# src/api/tests/test_workers.py
import pytest
from rcars.workers.base import WorkerContext


def test_worker_context_fields():
    ctx = WorkerContext.__dataclass_fields__
    assert "db" in ctx or hasattr(WorkerContext, "db")
```

This is a minimal test — the real worker tests come in Task 9 when we implement task functions.

- [ ] **Step 2: Implement worker base context**

```python
# src/api/rcars/workers/base.py
from __future__ import annotations

import json
from dataclasses import dataclass
from redis.asyncio import Redis
from rcars.db import Database
from rcars.config import Settings
from rcars.api.streaming import JobProgressRelay
import structlog

logger = structlog.get_logger()


@dataclass
class WorkerContext:
    db: Database
    redis: Redis
    relay: JobProgressRelay
    settings: Settings


async def publish_progress(relay: JobProgressRelay, job_id: str, db: Database, **kwargs) -> None:
    await relay.publish(job_id, kwargs)
    db.update_job_status(job_id, "running", progress_json=kwargs)
    logger.info(
        "phase_progress",
        action="phase_progress",
        job_id=job_id,
        **kwargs,
    )
```

- [ ] **Step 3: Implement arq worker settings**

```python
# src/api/rcars/workers/settings.py
from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings
from redis.asyncio import Redis

from rcars.config import Settings
from rcars.db import Database
from rcars.logging import setup_logging, get_logger
from rcars.api.streaming import JobProgressRelay
from rcars.workers.base import WorkerContext


async def startup(ctx: dict) -> None:
    setup_logging(level="INFO", component="worker")
    logger = get_logger()

    settings = Settings()
    db = Database(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    relay = JobProgressRelay(redis)

    ctx["worker_ctx"] = WorkerContext(db=db, redis=redis, relay=relay, settings=settings)
    logger.info("worker_started", action="worker_started")


async def shutdown(ctx: dict) -> None:
    worker_ctx: WorkerContext = ctx["worker_ctx"]
    worker_ctx.db.close()
    await worker_ctx.redis.close()
    get_logger().info("worker_stopped", action="worker_stopped")


class WorkerSettings:
    functions = []  # Populated as task modules are added
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings()  # Defaults to localhost:6379
    max_jobs = 5
    job_timeout = 600  # 10 minutes
    queue_name = "default"
```

- [ ] **Step 4: Create `__init__.py`**

```python
# src/api/rcars/workers/__init__.py
from rcars.workers.settings import WorkerSettings

__all__ = ["WorkerSettings"]
```

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/workers/ src/api/tests/test_workers.py
git commit -m "workers: arq worker settings with startup/shutdown lifecycle"
```

---

### Task 8: Port service layer (recommender, analyzer, catalog reader)

**Files:**
- Create: `src/api/rcars/services/recommender/` (port from `src/rcars/recommender/`)
- Create: `src/api/rcars/services/analyzer.py` (port from `src/rcars/analyzer.py`)
- Create: `src/api/rcars/services/catalog.py` (port from `src/rcars/catalog_reader.py`)
- Create: `src/api/rcars/services/embeddings.py` (extracted from analyzer)
- Copy: `src/rcars/prompts/` → `src/api/rcars/prompts/`
- Create: `src/api/tests/test_services.py`

This task ports existing, working business logic. The key change is that the recommender pipeline's generator-based progress is replaced with Redis pub/sub publishing. The actual LLM call logic, prompt templates, and parsing code should be copied unchanged.

- [ ] **Step 1: Copy prompt templates**

```bash
cp -r src/rcars/prompts/* src/api/rcars/prompts/
```

- [ ] **Step 2: Port the recommender pipeline**

Copy `src/rcars/recommender/models.py`, `vector_search.py`, `triage.py`, `rationale.py` into `src/api/rcars/services/recommender/`. The models, prompts, and LLM call logic stay the same. The main change is in `pipeline.py` — instead of yielding `QueryState` as a generator, it accepts a progress callback:

```python
# src/api/rcars/services/recommender/pipeline.py
from __future__ import annotations

from typing import Callable, Awaitable
from rcars.db import Database
from rcars.config import Settings
from rcars.services.recommender.models import QueryState, Candidate
from rcars.services.recommender.vector_search import search
from rcars.services.recommender.triage import triage
from rcars.services.recommender.rationale import generate_rationale
import structlog

logger = structlog.get_logger()


async def run_query(
    query: str,
    db: Database,
    anthropic_client,
    settings: Settings,
    prod_only: bool = True,
    on_progress: Callable[[dict], Awaitable[None]] | None = None,
) -> QueryState:
    async def emit(data: dict):
        if on_progress:
            await on_progress(data)

    # Phase 1: Vector search
    await emit({"phase": "vector_search", "status": "started"})
    state = search(query, db, distance_cutoff=settings.vector_cutoff, prod_only=prod_only)
    await emit({"phase": "vector_search", "status": "complete", "candidates": len(state.candidates)})

    if state.phase == "NO_MATCHES":
        await emit({"phase": "complete", "results": 0})
        return state

    # Phase 2: Triage
    await emit({"phase": "triage", "status": "started", "total": len(state.candidates)})
    state = triage(state, anthropic_client, model=settings.triage_model, triage_cutoff=settings.triage_cutoff)
    relevant = len([c for c in state.candidates if c.tier in ("yellow", "green")])
    await emit({"phase": "triage", "status": "complete", "relevant": relevant})

    if state.phase == "NO_MATCHES":
        await emit({"phase": "complete", "results": 0})
        return state

    # Phase 3: Rationale
    top_n = settings.rationale_top_n
    await emit({"phase": "rationale", "status": "started", "top_n": top_n})
    state = generate_rationale(state, db, anthropic_client, model=settings.rationale_model, top_n=top_n)
    green_count = len([c for c in state.candidates if c.tier == "green"])
    await emit({"phase": "complete", "results": green_count})

    return state
```

- [ ] **Step 3: Port analyzer, catalog reader, and embeddings**

Copy `src/rcars/analyzer.py` → `src/api/rcars/services/analyzer.py`. The code is correct and well-tested. Update imports to match new package layout. Add support for the `content_path` field — when set on a catalog item, use it instead of the default Antora path.

Copy `src/rcars/catalog_reader.py` → `src/api/rcars/services/catalog.py`. No logic changes needed.

Extract embedding generation from analyzer into `src/api/rcars/services/embeddings.py` for reuse.

- [ ] **Step 4: Write service tests**

```python
# src/api/tests/test_services.py
from rcars.services.recommender.models import Candidate, QueryState


def test_candidate_similarity_pct():
    assert Candidate.similarity_pct(0.0) == 100
    assert Candidate.similarity_pct(0.5) == 75
    assert Candidate.similarity_pct(1.0) == 50


def test_query_state_defaults():
    state = QueryState(phase="SUBMITTED", candidates=[])
    assert state.query == ""
    assert state.overall_assessment is None
    assert state.content_gaps is None
```

- [ ] **Step 5: Run tests**

Run: `cd src/api && python -m pytest tests/test_services.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/services/ src/api/rcars/prompts/ src/api/tests/test_services.py
git commit -m "services: Port recommender pipeline, analyzer, and catalog reader"
```

---

### Task 9: Implement worker task functions

**Files:**
- Create: `src/api/rcars/workers/recommend.py`
- Create: `src/api/rcars/workers/scan.py`
- Create: `src/api/rcars/workers/ops.py`
- Modify: `src/api/rcars/workers/settings.py` (register task functions)
- Create: `src/api/tests/test_worker_tasks.py`

- [ ] **Step 1: Implement recommendation worker task**

```python
# src/api/rcars/workers/recommend.py
from __future__ import annotations

from rcars.workers.base import WorkerContext, publish_progress
from rcars.services.recommender.pipeline import run_query
import structlog

logger = structlog.get_logger()


async def run_recommendation(ctx: dict, job_id: str, query: str, prod_only: bool = True) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("picked_up", action="picked_up", queue="recommend")
    wctx.db.update_job_status(job_id, "running")

    try:
        client = wctx.settings.get_anthropic_client()
        if client is None:
            raise RuntimeError("No Anthropic client configured")

        async def on_progress(data: dict):
            await publish_progress(wctx.relay, job_id, wctx.db, **data)

        state = await run_query(
            query=query,
            db=wctx.db,
            anthropic_client=client,
            settings=wctx.settings,
            prod_only=prod_only,
            on_progress=on_progress,
        )

        results = {
            "phase": state.phase,
            "candidates": [
                {
                    "ci_name": c.ci_name,
                    "display_name": c.display_name,
                    "tier": c.tier,
                    "fit_score": c.relevance_score,
                    "relevance_score": c.relevance_score,
                    "vector_similarity_pct": c.vector_similarity_pct,
                    "stage": c.stage,
                    "why_it_fits": c.why_it_fits,
                    "how_to_use": c.how_to_use,
                    "suggested_format": c.suggested_format,
                    "duration_notes": c.duration_notes,
                    "caveats": c.caveats,
                }
                for c in state.candidates
            ],
            "overall_assessment": state.overall_assessment,
            "content_gaps": state.content_gaps,
        }

        wctx.db.complete_job(job_id, result_json=results)
        log.info("job_complete", action="job_complete", results=len(state.candidates))
        return results

    except Exception as e:
        log.error("job_failed", action="job_failed", error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        await wctx.relay.publish(job_id, {"phase": "failed", "error": str(e)})
        raise
```

- [ ] **Step 2: Implement scan worker tasks**

```python
# src/api/rcars/workers/scan.py
from __future__ import annotations

from rcars.workers.base import WorkerContext, publish_progress
from rcars.services.analyzer import analyze_showroom
import structlog

logger = structlog.get_logger()


async def run_analysis(ctx: dict, job_id: str, ci_name: str) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id, ci_name=ci_name)

    log.info("picked_up", action="picked_up", queue="analyze")
    wctx.db.update_job_status(job_id, "running")

    try:
        item = wctx.db.get_catalog_item(ci_name)
        if not item:
            raise ValueError(f"Catalog item not found: {ci_name}")

        if not item.get("showroom_url"):
            raise ValueError(f"No Showroom URL for: {ci_name}")

        client = wctx.settings.get_anthropic_client()
        result = analyze_showroom(
            ci_name=ci_name,
            display_name=item.get("display_name", ""),
            category=item.get("category", ""),
            product=item.get("product", ""),
            showroom_url=item["showroom_url"],
            showroom_ref=item.get("showroom_ref"),
            anthropic_client=client,
            model=wctx.settings.model,
            clone_dir=wctx.settings.clone_dir,
            db=wctx.db,
            content_path=item.get("content_path"),
        )

        if result:
            wctx.db.upsert_showroom_analysis(result["analysis"])
            wctx.db.store_embedding(
                ci_name=ci_name,
                embed_type="ci_summary",
                content_text=result["ci_embedding_text"],
                embedding=result["ci_embedding"],
            )
            for mod_emb in result.get("module_embeddings", []):
                wctx.db.store_embedding(
                    ci_name=ci_name,
                    embed_type="module",
                    content_text=mod_emb["text"],
                    embedding=mod_emb["embedding"],
                    module_title=mod_emb["title"],
                )
            wctx.db.complete_job(job_id, result_json={"ci_name": ci_name, "status": "analyzed"})
            log.info("analysis_complete", action="job_complete", ci_name=ci_name)
        else:
            wctx.db.fail_job(job_id, error="Analysis returned no results")

        return {"ci_name": ci_name, "success": result is not None}

    except Exception as e:
        log.error("analysis_failed", action="job_failed", error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        raise
```

- [ ] **Step 3: Implement ops worker tasks**

```python
# src/api/rcars/workers/ops.py
from __future__ import annotations

from rcars.workers.base import WorkerContext, publish_progress
from rcars.services.catalog import CatalogReader
import structlog

logger = structlog.get_logger()


async def run_catalog_refresh(ctx: dict, job_id: str) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("picked_up", action="picked_up", queue="ops")
    wctx.db.update_job_status(job_id, "running")

    try:
        reader = CatalogReader(kubeconfig_path=wctx.settings.kubeconfig_path)
        items = reader.refresh_catalog(
            namespaces=wctx.settings.catalog_namespaces,
            component_namespace=wctx.settings.agnosticv_component_namespace,
        )

        current_ci_names = set()
        for item in items:
            wctx.db.upsert_catalog_item(item)
            current_ci_names.add(item["ci_name"])

        removed = wctx.db.delete_removed_items(current_ci_names)

        result = {
            "total_items": len(items),
            "removed_items": len(removed),
        }
        wctx.db.complete_job(job_id, result_json=result)
        log.info("refresh_complete", action="job_complete", **result)
        return result

    except Exception as e:
        log.error("refresh_failed", action="job_failed", error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        raise


async def run_stale_check(ctx: dict, job_id: str) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("picked_up", action="picked_up", queue="ops")
    wctx.db.update_job_status(job_id, "running")

    try:
        from rcars.services.analyzer import clone_showroom, check_showroom_stale
        items = wctx.db.list_catalog_items()
        stale_count = 0

        for item in items:
            analysis = wctx.db.get_showroom_analysis(item["ci_name"])
            if not analysis or not item.get("showroom_url"):
                continue
            clone_path = clone_showroom(item["showroom_url"], item.get("showroom_ref"), wctx.settings.clone_dir)
            if not clone_path:
                continue
            try:
                result = check_showroom_stale(clone_path, analysis.get("content_hash"))
                if result["is_stale"]:
                    wctx.db.mark_stale(item["ci_name"], result.get("head_sha"))
                    stale_count += 1
                else:
                    wctx.db.clear_stale(item["ci_name"])
            finally:
                import shutil
                shutil.rmtree(clone_path, ignore_errors=True)

        result = {"checked": len(items), "stale": stale_count}
        wctx.db.complete_job(job_id, result_json=result)
        log.info("stale_check_complete", action="job_complete", **result)
        return result

    except Exception as e:
        log.error("stale_check_failed", action="job_failed", error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        raise
```

- [ ] **Step 4: Register tasks in WorkerSettings**

Update `src/api/rcars/workers/settings.py`:

```python
# Add to imports:
from rcars.workers.recommend import run_recommendation
from rcars.workers.scan import run_analysis
from rcars.workers.ops import run_catalog_refresh, run_stale_check

# Update WorkerSettings:
class WorkerSettings:
    functions = [run_recommendation, run_analysis, run_catalog_refresh, run_stale_check]
    # ... rest unchanged
```

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/workers/
git commit -m "workers: Implement recommendation, scan, and ops task functions"
```

---

### Task 10: API route modules (advisor, catalog, analysis, admin)

**Files:**
- Create: `src/api/rcars/api/routes/advisor.py`
- Create: `src/api/rcars/api/routes/catalog.py`
- Create: `src/api/rcars/api/routes/analysis.py`
- Create: `src/api/rcars/api/routes/admin.py`
- Modify: `src/api/rcars/api/app.py` (register routers)
- Create: `src/api/tests/test_routes.py`

Each route module is focused — it validates input, creates a job record, enqueues work, and either returns a `job_id` or queries the database directly for reads.

- [ ] **Step 1: Implement advisor routes**

```python
# src/api/rcars/api/routes/advisor.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from arq.connections import ArqRedis
from rcars.api.middleware.auth import require_auth
from rcars.api.streaming import JobProgressRelay, create_sse_response
from rcars.db.models import JobResponse

router = APIRouter(prefix="/advisor")


class QueryRequest(BaseModel):
    query: str
    event_url: str | None = None
    prod_only: bool = True
    opted_out: bool = False


@router.post("/query", response_model=JobResponse)
async def submit_query(body: QueryRequest, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    arq_redis: ArqRedis = request.app.state.arq_redis

    job_id = db.create_job(job_type="recommend", queue="recommend", created_by=user)
    await arq_redis.enqueue_job(
        "run_recommendation",
        job_id=job_id,
        query=body.query,
        prod_only=body.prod_only,
        _queue_name="recommend",
    )
    return JobResponse(job_id=job_id)


@router.get("/query/{job_id}/stream")
async def stream_query(job_id: str, request: Request, user: str = Depends(require_auth)):
    relay = JobProgressRelay(request.app.state.redis)
    return create_sse_response(relay, job_id)


@router.get("/query/{job_id}/result")
async def get_query_result(job_id: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "status": job["status"],
        "result": job.get("result_json"),
        "error": job.get("error"),
    }


@router.get("/sessions")
async def list_sessions(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    sessions = db.list_advisor_sessions(user_email=user)
    return {"items": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    session = db.get_advisor_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/select")
async def select_recommendation(
    session_id: str, request: Request, user: str = Depends(require_auth)
):
    body = await request.json()
    db = request.app.state.db
    db.update_advisor_session_choice(
        session_id=session_id,
        turn_index=body["turn_index"],
        chosen_ci_name=body["ci_name"],
    )
    return {"status": "ok"}
```

- [ ] **Step 2: Implement catalog routes**

```python
# src/api/rcars/api/routes/catalog.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from rcars.api.middleware.auth import require_auth, require_curator
from rcars.db.models import JobResponse, PaginatedResponse
from pydantic import BaseModel

router = APIRouter(prefix="/catalog")


@router.get("")
async def list_catalog(
    request: Request,
    user: str = Depends(require_auth),
    stage: str | None = None,
    category: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    db = request.app.state.db
    items = db.list_catalog_items(stage=stage, category=category)
    total = len(items)
    page = items[offset : offset + limit]
    return {"items": page, "total": total}


@router.get("/stats")
async def catalog_stats(request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    currency = db.get_db_currency()
    return currency


@router.get("/{ci_name}")
async def get_catalog_item(ci_name: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    item = db.get_catalog_item(ci_name)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    analysis = db.get_showroom_analysis(ci_name)
    tags = db.get_enrichment_tags(ci_name)
    return {**item, "analysis": analysis, "tags": tags}


@router.get("/{ci_name}/analysis")
async def get_analysis(ci_name: str, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    analysis = db.get_showroom_analysis(ci_name)
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found")
    return analysis


@router.post("/refresh", response_model=JobResponse)
async def refresh_catalog(request: Request, user: str = Depends(require_auth)):
    from rcars.api.middleware.auth import require_admin
    require_admin(request)
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="refresh", queue="ops", created_by=user)
    await arq_redis.enqueue_job("run_catalog_refresh", job_id=job_id, _queue_name="ops")
    return JobResponse(job_id=job_id)


class TagRequest(BaseModel):
    tag_type: str
    tag_value: str


@router.post("/{ci_name}/tags")
async def add_tag(ci_name: str, body: TagRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.add_enrichment_tag(ci_name, body.tag_type, body.tag_value, added_by=user)
    return {"status": "ok"}


@router.delete("/{ci_name}/tags/{tag_id}")
async def remove_tag(ci_name: str, tag_id: int, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.remove_enrichment_tag_by_id(tag_id)
    return {"status": "ok"}


class NoteRequest(BaseModel):
    note: str


@router.put("/{ci_name}/note")
async def set_note(ci_name: str, body: NoteRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_enrichment_note(ci_name, body.note, updated_by=user)
    return {"status": "ok"}


@router.post("/{ci_name}/flag")
async def flag_item(ci_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_enrichment_review_flag(ci_name, True)
    return {"status": "ok"}


class OverrideUrlRequest(BaseModel):
    url: str


@router.post("/{ci_name}/override-url")
async def override_url(ci_name: str, body: OverrideUrlRequest, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    db.set_showroom_url_override(ci_name, body.url)
    return {"status": "ok"}
```

- [ ] **Step 3: Implement analysis routes**

```python
# src/api/rcars/api/routes/analysis.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from rcars.api.middleware.auth import require_admin, require_curator, require_auth
from rcars.api.streaming import JobProgressRelay, create_sse_response
from rcars.db.models import JobResponse

router = APIRouter(prefix="/analysis")


@router.post("/scan", response_model=JobResponse)
async def start_scan(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="scan", queue="analyze", created_by=user)

    items = db.get_items_needing_analysis()
    for item in items:
        sub_job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
        await arq_redis.enqueue_job(
            "run_analysis", job_id=sub_job_id, ci_name=item["ci_name"], _queue_name="analyze"
        )

    db.complete_job(job_id, result_json={"enqueued": len(items)})
    return JobResponse(job_id=job_id)


@router.post("/check-stale", response_model=JobResponse)
async def check_stale(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="check_stale", queue="ops", created_by=user)
    await arq_redis.enqueue_job("run_stale_check", job_id=job_id, _queue_name="ops")
    return JobResponse(job_id=job_id)


@router.post("/rescan-stale", response_model=JobResponse)
async def rescan_stale(request: Request, user: str = Depends(require_admin)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="rescan_stale", queue="ops", created_by=user)

    items = db.list_catalog_items()
    stale_items = [i for i in items if i.get("is_stale")]
    for item in stale_items:
        sub_job_id = db.create_job(job_type="analyze", queue="analyze", created_by="rescan")
        await arq_redis.enqueue_job(
            "run_analysis", job_id=sub_job_id, ci_name=item["ci_name"], _queue_name="analyze"
        )

    db.complete_job(job_id, result_json={"enqueued": len(stale_items)})
    return JobResponse(job_id=job_id)


@router.post("/{ci_name}", response_model=JobResponse)
async def analyze_single(ci_name: str, request: Request, user: str = Depends(require_curator)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    job_id = db.create_job(job_type="analyze", queue="analyze", created_by=user)
    await arq_redis.enqueue_job("run_analysis", job_id=job_id, ci_name=ci_name, _queue_name="analyze")
    return JobResponse(job_id=job_id)


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str, request: Request, user: str = Depends(require_auth)):
    relay = JobProgressRelay(request.app.state.redis)
    return create_sse_response(relay, job_id)
```

- [ ] **Step 4: Implement admin routes**

```python
# src/api/rcars/api/routes/admin.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Query
from rcars.api.middleware.auth import require_admin

router = APIRouter(prefix="/admin")


@router.get("/token-usage")
async def token_usage(
    request: Request,
    user: str = Depends(require_admin),
    days: int = Query(30, ge=1, le=365),
):
    db = request.app.state.db
    stats = db.get_token_stats(days=days)
    queries = db.get_recent_queries(days=days)
    return {"stats": stats, "recent_queries": queries, "days": days}


@router.get("/jobs")
async def list_jobs(
    request: Request,
    user: str = Depends(require_admin),
    limit: int = Query(50, le=200),
    job_type: str | None = None,
):
    db = request.app.state.db
    jobs = db.list_jobs(limit=limit, job_type=job_type)
    return {"items": jobs, "total": len(jobs)}


@router.get("/workers")
async def worker_health(request: Request, user: str = Depends(require_admin)):
    redis = request.app.state.redis
    db = request.app.state.db

    queue_depths = {}
    for queue in ["recommend", "analyze", "ops"]:
        depth = await redis.llen(f"arq:queue:{queue}")
        queue_depths[queue] = depth

    active_jobs = db.list_jobs(limit=100)
    running = [j for j in active_jobs if j["status"] == "running"]
    failed_24h = [j for j in active_jobs if j["status"] == "failed"]

    return {
        "queue_depths": queue_depths,
        "active_jobs": len(running),
        "running_jobs": running,
        "failed_24h": len(failed_24h),
    }
```

- [ ] **Step 5: Register all routers in app.py**

Update `src/api/rcars/api/app.py` to include the new routers:

```python
# Add imports:
from rcars.api.routes import advisor, catalog, analysis, admin
from arq.connections import ArqRedis, RedisSettings

# In create_app, add routers:
app.include_router(advisor.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

# In lifespan, add arq connection:
app.state.arq_redis = await ArqRedis.from_url(settings.redis_url)
# In shutdown:
await app.state.arq_redis.close()
```

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/api/routes/ src/api/rcars/api/app.py
git commit -m "api: Implement all route modules (advisor, catalog, analysis, admin)"
```

---

### Task 11: CLI tool

**Files:**
- Create: `src/api/rcars/cli.py`
- Create: `src/api/tests/test_cli.py`

Port and extend the existing CLI with curation commands.

- [ ] **Step 1: Implement CLI**

Port `src/rcars/cli.py` and add new curation commands per the spec. Operations commands (`refresh`, `scan`, `check-stale`) should enqueue arq jobs via Redis rather than running inline. Status and curation commands query/write the database directly.

Read the existing `src/rcars/cli.py` for the Click command patterns. Extend with:

```python
@cli.command()
@click.argument("ci_name")
@click.argument("tag_type")
@click.argument("tag_value")
def tag(ci_name, tag_type, tag_value):
    """Add an enrichment tag to a catalog item."""
    db = Database(Settings().database_url)
    db.add_enrichment_tag(ci_name, tag_type, tag_value)
    click.echo(f"Tagged {ci_name}: {tag_type}={tag_value}")
    db.close()


@cli.command()
@click.argument("ci_name")
@click.argument("tag_type")
@click.argument("tag_value")
def untag(ci_name, tag_type, tag_value):
    """Remove an enrichment tag from a catalog item."""
    db = Database(Settings().database_url)
    db.remove_enrichment_tag(ci_name, tag_type, tag_value)
    click.echo(f"Removed tag {tag_type}={tag_value} from {ci_name}")
    db.close()


@cli.command()
@click.argument("ci_name")
@click.argument("note")
def note(ci_name, note):
    """Set a curator note on a catalog item."""
    db = Database(Settings().database_url)
    db.set_enrichment_note(ci_name, note)
    click.echo(f"Note set on {ci_name}")
    db.close()


@cli.command("set-content-path")
@click.argument("ci_name")
@click.argument("path")
def set_content_path(ci_name, path):
    """Set custom content path for non-standard Showroom repos."""
    db = Database(Settings().database_url)
    db.set_content_path(ci_name, path)
    click.echo(f"Content path set for {ci_name}: {path}")
    db.close()
```

- [ ] **Step 2: Commit**

```bash
git add src/api/rcars/cli.py src/api/tests/test_cli.py
git commit -m "cli: Port CLI with new curation commands (tag, untag, note, flag, set-content-path)"
```

---

## Phase 3: React Frontend

### Task 12: LCARS CSS port and component library

**Files:**
- Create: `src/frontend/src/styles/lcars.css` (port from `src/rcars/web/static/rcars.css`)
- Create: `src/frontend/src/components/lcars/LcarsHeader.tsx`
- Create: `src/frontend/src/components/lcars/LcarsCard.tsx`
- Create: `src/frontend/src/components/lcars/LcarsButton.tsx`
- Create: `src/frontend/src/components/lcars/LcarsInput.tsx`
- Create: `src/frontend/src/components/lcars/LcarsBadge.tsx`

- [ ] **Step 1: Port CSS**

Copy `src/rcars/web/static/rcars.css` to `src/frontend/src/styles/lcars.css`. Adapt selectors from Jinja2 template classes to React component classes. Keep all design tokens (colors, fonts, spacing) identical.

- [ ] **Step 2: Implement LCARS components**

Create thin styled wrapper components. These are CSS + layout only — no business logic. Read the existing templates (`base.html`, `advisor.html`, `curate.html`) to understand the current HTML structure and replicate it with React components.

Each component should have a corresponding TypeScript interface for its props.

- [ ] **Step 3: Verify components render**

Run: `cd src/frontend && npm run dev`
Open `http://localhost:3000` and verify the LCARS header, buttons, and cards render with the correct theme.

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/styles/ src/frontend/src/components/lcars/
git commit -m "frontend: Port LCARS CSS and create component library"
```

---

### Task 13: API service layer and hooks

**Files:**
- Create: `src/frontend/src/services/api.ts`
- Create: `src/frontend/src/hooks/useAuth.ts`
- Create: `src/frontend/src/hooks/useJobStream.ts`

- [ ] **Step 1: Implement typed API client**

```typescript
// src/frontend/src/services/api.ts
const BASE = '/api/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(error.detail || error.error || resp.statusText);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json();
}

export const api = {
  // Auth
  getMe: () => request<{ email: string; roles: string[] }>('/auth/me'),

  // Advisor
  submitQuery: (query: string, prodOnly = true) =>
    request<{ job_id: string }>('/advisor/query', {
      method: 'POST',
      body: JSON.stringify({ query, prod_only: prodOnly }),
    }),
  getQueryResult: (jobId: string) =>
    request<{ status: string; result: any; error: string | null }>(`/advisor/query/${jobId}/result`),
  listSessions: () => request<{ items: any[]; total: number }>('/advisor/sessions'),
  getSession: (sessionId: string) => request<any>(`/advisor/sessions/${sessionId}`),
  selectRecommendation: (sessionId: string, turnIndex: number, ciName: string) =>
    request<{ status: string }>(`/advisor/sessions/${sessionId}/select`, {
      method: 'POST',
      body: JSON.stringify({ turn_index: turnIndex, ci_name: ciName }),
    }),

  // Catalog
  listCatalog: (params?: { stage?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.stage) qs.set('stage', params.stage);
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.offset) qs.set('offset', String(params.offset));
    return request<{ items: any[]; total: number }>(`/catalog?${qs}`);
  },
  getCatalogItem: (ciName: string) => request<any>(`/catalog/${encodeURIComponent(ciName)}`),
  getCatalogStats: () => request<any>('/catalog/stats'),
  refreshCatalog: () => request<{ job_id: string }>('/catalog/refresh', { method: 'POST' }),

  // Curation
  addTag: (ciName: string, tagType: string, tagValue: string) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/tags`, {
      method: 'POST',
      body: JSON.stringify({ tag_type: tagType, tag_value: tagValue }),
    }),
  removeTag: (ciName: string, tagId: number) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/tags/${tagId}`, { method: 'DELETE' }),
  setNote: (ciName: string, note: string) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/note`, {
      method: 'PUT',
      body: JSON.stringify({ note }),
    }),

  // Analysis
  startScan: () => request<{ job_id: string }>('/analysis/scan', { method: 'POST' }),
  checkStale: () => request<{ job_id: string }>('/analysis/check-stale', { method: 'POST' }),
  rescanStale: () => request<{ job_id: string }>('/analysis/rescan-stale', { method: 'POST' }),
  analyzeSingle: (ciName: string) =>
    request<{ job_id: string }>(`/analysis/${encodeURIComponent(ciName)}`, { method: 'POST' }),

  // Admin
  getTokenUsage: (days = 30) => request<any>(`/admin/token-usage?days=${days}`),
  listJobs: (limit = 50) => request<{ items: any[]; total: number }>(`/admin/jobs?limit=${limit}`),
  getWorkerHealth: () => request<any>('/admin/workers'),
};
```

- [ ] **Step 2: Implement auth hook**

```typescript
// src/frontend/src/hooks/useAuth.ts
import { useState, useEffect, createContext, useContext } from 'react';
import { api } from '../services/api';

interface AuthState {
  email: string;
  roles: string[];
  isLoading: boolean;
  isCurator: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthState>({
  email: '', roles: [], isLoading: true, isCurator: false, isAdmin: false,
});

export function useAuth() {
  return useContext(AuthContext);
}

export { AuthContext };

export function useAuthProvider(): AuthState {
  const [state, setState] = useState<AuthState>({
    email: '', roles: [], isLoading: true, isCurator: false, isAdmin: false,
  });

  useEffect(() => {
    api.getMe()
      .then(data => setState({
        email: data.email,
        roles: data.roles,
        isLoading: false,
        isCurator: data.roles.includes('curator'),
        isAdmin: data.roles.includes('admin'),
      }))
      .catch(() => setState(prev => ({ ...prev, isLoading: false })));
  }, []);

  return state;
}
```

- [ ] **Step 3: Implement SSE job stream hook**

```typescript
// src/frontend/src/hooks/useJobStream.ts
import { useState, useEffect, useCallback } from 'react';

interface StreamState {
  phase: string;
  progress: { current?: number; total?: number } | null;
  userMessage: string;
  results: any | null;
  isComplete: boolean;
  error: string | null;
  messages: Array<{ phase: string; message: string; done: boolean }>;
}

export function useJobStream(jobId: string | null) {
  const [state, setState] = useState<StreamState>({
    phase: '', progress: null, userMessage: '', results: null,
    isComplete: false, error: null, messages: [],
  });

  useEffect(() => {
    if (!jobId) return;

    const eventSource = new EventSource(`/api/v1/advisor/query/${jobId}/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setState(prev => {
        const newMessage = {
          phase: data.phase,
          message: data.user_message,
          done: data.status === 'complete' || data.phase === 'complete',
        };
        return {
          phase: data.phase,
          progress: data.current ? { current: data.current, total: data.total } : null,
          userMessage: data.user_message,
          results: data.results || prev.results,
          isComplete: data.phase === 'complete' || data.phase === 'failed',
          error: data.phase === 'failed' ? data.error : null,
          messages: [...prev.messages, newMessage],
        };
      });

      if (data.phase === 'complete' || data.phase === 'failed') {
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setState(prev => ({ ...prev, isComplete: true, error: 'Connection lost' }));
      eventSource.close();
    };

    return () => eventSource.close();
  }, [jobId]);

  return state;
}
```

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/services/ src/frontend/src/hooks/
git commit -m "frontend: API service layer, auth hook, and SSE job stream hook"
```

---

### Task 14: Page components (Advisor, Browse, Admin)

**Files:**
- Create: `src/frontend/src/App.tsx`
- Create: `src/frontend/src/pages/AdvisorPage.tsx`
- Create: `src/frontend/src/pages/BrowsePage.tsx`
- Create: `src/frontend/src/pages/AdminPage.tsx`
- Create: `src/frontend/src/components/advisor/ChatPanel.tsx`
- Create: `src/frontend/src/components/advisor/RecPanel.tsx`
- Create: `src/frontend/src/components/advisor/RecCard.tsx`
- Create: `src/frontend/src/components/advisor/ProgressStream.tsx`
- Create: `src/frontend/src/components/admin/LogWindow.tsx`

This is the largest frontend task. Read the existing Jinja2 templates to understand the current UI behavior, then rebuild in React.

- [ ] **Step 1: Implement App.tsx with routing**

```typescript
// src/frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthContext, useAuthProvider } from './hooks/useAuth';
import { LcarsHeader } from './components/lcars/LcarsHeader';
import { AdvisorPage } from './pages/AdvisorPage';
import { BrowsePage } from './pages/BrowsePage';
import { AdminPage } from './pages/AdminPage';
import './styles/lcars.css';

export default function App() {
  const auth = useAuthProvider();

  return (
    <AuthContext.Provider value={auth}>
      <BrowserRouter>
        <LcarsHeader />
        <Routes>
          <Route path="/" element={<Navigate to="/advisor" replace />} />
          <Route path="/advisor" element={<AdvisorPage />} />
          <Route path="/browse" element={<BrowsePage />} />
          {auth.isAdmin && <Route path="/admin" element={<AdminPage />} />}
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
```

- [ ] **Step 2: Implement AdvisorPage with split panels**

Build the split-panel layout per the spec: chat on the left, rec cards on the right with turn navigation. Use `useJobStream` for real-time progress. Read `src/rcars/web/templates/advisor.html` for the current behavior to replicate.

- [ ] **Step 3: Implement RecCard component with tier colors**

Port the rec card design from `src/rcars/web/templates/fragments/rec_card.html` and `rec_card_expanded.html`. Green/yellow/white borders, fit scores, "This fits best" button. The CSS classes map from `rcars.css`.

- [ ] **Step 4: Implement ProgressStream component**

Renders the streaming progress messages in the chat panel:
- Bullet with spinner for in-progress phase
- Checkmark for completed phases
- Text from `useJobStream.messages`

- [ ] **Step 5: Implement BrowsePage**

Port from `src/rcars/web/templates/curate.html`. Paginated catalog list, search/filter, enrichment tags displayed. If user has curator role, show edit controls (tag, note, flag, re-analyze buttons). Otherwise read-only.

- [ ] **Step 6: Implement AdminPage with LogWindow**

Port from `src/rcars/web/templates/admin.html`. Token usage stats, job list, catalog refresh/scan/stale-check triggers. The LogWindow component implements scroll-position-aware auto-scroll per the spec:

```typescript
// src/frontend/src/components/admin/LogWindow.tsx
import { useRef, useEffect, useState } from 'react';

interface LogWindowProps {
  lines: string[];
  isOpen: boolean;
  onToggle: () => void;
}

export function LogWindow({ lines, isOpen, onToggle }: LogWindowProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const threshold = 30;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    setIsAtBottom(atBottom);
  };

  useEffect(() => {
    if (isAtBottom && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [lines, isAtBottom]);

  return (
    <div className="log-window">
      <button onClick={onToggle} className="log-toggle">
        {isOpen ? '▾' : '▸'} Log ({lines.length} lines)
      </button>
      {isOpen && (
        <div
          ref={containerRef}
          className="log-content"
          onScroll={handleScroll}
        >
          {lines.map((line, i) => (
            <div key={i} className="log-line">{line}</div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Add worker health panel to AdminPage**

Display queue depths, active jobs, and failed jobs from `/api/v1/admin/workers`. Auto-refresh every 10 seconds when the admin page is visible.

- [ ] **Step 8: Verify all pages work end-to-end**

Run backend: `cd src/api && uvicorn rcars.api.app:create_app --factory --reload --port 8080`
Run frontend: `cd src/frontend && npm run dev`
Test: submit a query, browse catalog, view admin dashboard.

- [ ] **Step 9: Commit**

```bash
git add src/frontend/src/
git commit -m "frontend: Implement Advisor, Browse, and Admin pages with LCARS theme"
```

---

## Phase 4: Containers & Deployment

### Task 15: Containerfiles

**Files:**
- Create: `src/api/Containerfile`
- Create: `src/frontend/Containerfile`
- Create: `src/frontend/nginx.conf`

- [ ] **Step 1: Create API Containerfile**

```dockerfile
# src/api/Containerfile
FROM registry.access.redhat.com/ubi9/python-311 AS builder

USER 0
WORKDIR /opt/app-root/src

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e .

# Pre-download sentence-transformers model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

FROM registry.access.redhat.com/ubi9/python-311

USER 0
RUN dnf install -y git-core && dnf clean all
USER 1001

COPY --from=builder /opt/app-root/lib /opt/app-root/lib
COPY --from=builder /opt/app-root/bin /opt/app-root/bin
COPY --from=builder /opt/app-root/.cache /opt/app-root/.cache

WORKDIR /opt/app-root/src
COPY . .

ENV HF_HOME=/opt/app-root/.cache/huggingface
ENV TQDM_DISABLE=1
ENV TRANSFORMERS_VERBOSITY=error

EXPOSE 8080
CMD ["uvicorn", "rcars.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
```

- [ ] **Step 2: Create frontend nginx.conf**

```nginx
# src/frontend/nginx.conf
server {
    listen 8080;
    server_name _;
    root /opt/app-root/src/dist;
    index index.html;

    location /api/ {
        proxy_pass http://rcars-api:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Email $http_x_forwarded_email;
        proxy_set_header X-Forwarded-User $http_x_forwarded_user;
        proxy_buffering off;
        proxy_cache off;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 3: Create frontend Containerfile**

```dockerfile
# src/frontend/Containerfile
FROM registry.access.redhat.com/ubi9/nodejs-20 AS builder

USER 0
WORKDIR /opt/app-root/src
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM registry.access.redhat.com/ubi9/nginx-122

COPY --from=builder /opt/app-root/src/dist /opt/app-root/src/dist
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 4: Commit**

```bash
git add src/api/Containerfile src/frontend/Containerfile src/frontend/nginx.conf
git commit -m "containers: Add UBI-based Containerfiles for API and frontend"
```

---

### Task 16: Ansible deployment manifests

**Files:**
- Modify: `ansible/deploy.yml`
- Modify: `ansible/templates/manifests.yaml.j2`
- Modify: `ansible/vars/common.yml`

This task modifies the existing Ansible playbook — not a rewrite. Add new resources (frontend Deployment, Redis StatefulSet, worker Deployment, separate BuildConfigs) while keeping the existing playbook structure and tag conventions.

- [ ] **Step 1: Update manifests template**

Add to `ansible/templates/manifests.yaml.j2`:
- Redis StatefulSet with persistent volume
- `rcars-frontend` Deployment (nginx, 1 replica)
- `rcars-api` Deployment (FastAPI, 2 replicas, resource limits from spec)
- `rcars-worker` Deployment (arq, 1 replica, resource limits from spec)
- Separate BuildConfigs for frontend and API
- `rcars-api` Service (ClusterIP)
- `rcars-api` Route (conditional on `rcars_api_external_route`)
- ConfigMap with app settings
- Updated Secrets

Follow the resource limits from the spec:
- Frontend: 100m/500m CPU, 128Mi/256Mi memory
- API: 500m/2 CPU, 512Mi/2Gi memory
- Worker: 500m/2 CPU, 1Gi/4Gi memory
- Redis: 100m/500m CPU, 256Mi/512Mi memory

- [ ] **Step 2: Add new Ansible tags**

Add `build-frontend`, `build-api`, `bootstrap` tags to `ansible/deploy.yml` per the spec.

- [ ] **Step 3: Update vars files**

Add new variables to `ansible/vars/common.yml`:
```yaml
rcars_api_external_route: false
rcars_redis_storage_size: 1Gi
rcars_worker_replicas: 1
rcars_api_replicas: 2
```

- [ ] **Step 4: Commit**

```bash
git add ansible/
git commit -m "ansible: Add multi-component deployment (frontend, API, worker, Redis)"
```

---

### Task 17: Local development script

**Files:**
- Create: `dev-services.sh`

- [ ] **Step 1: Create dev-services.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

PODMAN_MACHINE="agnosticd"
PG_CONTAINER="rcars-postgres"
REDIS_CONTAINER="rcars-redis"

start() {
    echo "Starting PostgreSQL (podman)..."
    podman start "$PG_CONTAINER" 2>/dev/null || \
        podman run -d --name "$PG_CONTAINER" \
            -e POSTGRES_USER=rcars -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=rcars \
            -p 5432:5432 postgres:16
    echo "  ✓  localhost:5432"

    echo "Starting Redis (podman)..."
    podman start "$REDIS_CONTAINER" 2>/dev/null || \
        podman run -d --name "$REDIS_CONTAINER" -p 6379:6379 redis:7
    echo "  ✓  localhost:6379"

    echo "Starting API (uvicorn --reload)..."
    cd src/api
    RCARS_DATABASE_URL="postgresql://rcars:dev@localhost:5432/rcars" \
    RCARS_REDIS_URL="redis://localhost:6379" \
    RCARS_DEV_USER="${RCARS_DEV_USER:-dev@redhat.com}" \
    uvicorn rcars.api.app:create_app --factory --reload --port 8080 \
        > /tmp/rcars-api.log 2>&1 &
    echo "  ✓  localhost:8080"
    cd ../..

    echo "Starting Worker (arq)..."
    cd src/api
    RCARS_DATABASE_URL="postgresql://rcars:dev@localhost:5432/rcars" \
    RCARS_REDIS_URL="redis://localhost:6379" \
    arq rcars.workers.WorkerSettings \
        > /tmp/rcars-worker.log 2>&1 &
    echo "  ✓  localhost (background)"
    cd ../..

    echo "Starting Frontend (vite dev)..."
    cd src/frontend && npm run dev > /tmp/rcars-frontend.log 2>&1 &
    cd ../..
    echo "  ✓  localhost:3000"

    echo ""
    echo "RCARS dev environment ready."
    echo "Frontend:  http://localhost:3000"
    echo "API docs:  http://localhost:8080/api/v1/docs"
    echo "Logs:      /tmp/rcars-*.log"
}

stop() {
    echo "Stopping services..."
    pkill -f "uvicorn rcars" 2>/dev/null || true
    pkill -f "arq rcars" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    podman stop "$REDIS_CONTAINER" 2>/dev/null || true
    podman stop "$PG_CONTAINER" 2>/dev/null || true
    echo "Stopped."
}

case "${1:-start}" in
    start) start ;;
    stop) stop ;;
    restart) stop; sleep 1; start ;;
    *) echo "Usage: $0 {start|stop|restart}" ;;
esac
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x dev-services.sh
git add dev-services.sh
git commit -m "dev: Add local development services script"
```

---

## Phase 5: Migration & Documentation

### Task 18: Database migration

**Files:**
- Create: `src/api/scripts/migrate_token_usage.py`

- [ ] **Step 1: Create migration script**

Write a script that:
1. Connects to the existing database
2. Exports `token_usage` rows to a JSON dump file
3. Drops all existing tables
4. Runs Alembic baseline migration (new schema)
5. Imports `token_usage` rows
6. Verifies row counts

```python
# src/api/scripts/migrate_token_usage.py
"""One-time migration: export token_usage from old schema, create new schema, reimport."""
import json
import sys
from rcars.db import Database
from rcars.config import Settings


def migrate():
    settings = Settings()
    db = Database(settings.database_url)

    # Export
    print("Exporting token_usage...")
    with db.pool.connection() as conn:
        cur = conn.execute("SELECT * FROM token_usage ORDER BY created_at")
        rows = cur.fetchall()
    print(f"  Exported {len(rows)} rows")

    dump_path = "/tmp/rcars_token_usage_backup.json"
    with open(dump_path, "w") as f:
        json.dump([dict(r) for r in rows], f, default=str)
    print(f"  Saved to {dump_path}")

    # Drop and recreate
    print("Dropping old schema...")
    db.drop_schema()
    print("Creating new schema...")
    db.create_schema()

    # Import
    print("Importing token_usage...")
    with open(dump_path) as f:
        saved_rows = json.load(f)

    with db.pool.connection() as conn:
        for row in saved_rows:
            conn.execute(
                """INSERT INTO token_usage (operation, model, input_tokens, output_tokens,
                   ci_name, query_text, created_at)
                   VALUES (%(operation)s, %(model)s, %(input_tokens)s, %(output_tokens)s,
                   %(ci_name)s, %(query_text)s, %(created_at)s)""",
                row,
            )

    # Verify
    with db.pool.connection() as conn:
        cur = conn.execute("SELECT COUNT(*) AS cnt FROM token_usage")
        count = cur.fetchone()["cnt"]
    print(f"  Imported {count} rows (expected {len(saved_rows)})")
    assert count == len(saved_rows), "Row count mismatch!"

    print("Migration complete.")
    db.close()


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 2: Commit**

```bash
git add src/api/scripts/
git commit -m "migration: Add token_usage data migration script"
```

---

### Task 19: Documentation updates

**Files:**
- Modify: `docs/architecture.md`
- Modify: `OPERATIONS.md`
- Create: `docs/api-guide.md`
- Create: `docs/workers.md`
- Create: `docs/development.md`
- Create: `docs/migration.md`
- Modify: `CLAUDE.md`

Each doc should follow the existing style — read the current `docs/architecture.md` and `OPERATIONS.md` for tone and format.

- [ ] **Step 1: Update architecture.md**

Replace the system diagram and component descriptions with the new three-tier architecture. Keep the same sections (Data Sources, CI Hierarchy, Catalog Reader, PostgreSQL Schema, Scan Pipeline, Recommendation Engine) but update them to reflect the new worker-based execution model.

- [ ] **Step 2: Update OPERATIONS.md**

Add multi-component build/deploy commands, worker management, Redis operations. Keep the existing sections that still apply.

- [ ] **Step 3: Create api-guide.md**

API usage guide with curl examples for common operations: submit a query, poll results, stream progress, browse catalog, add a tag. Not a code reference — Swagger at `/api/v1/docs` handles that.

- [ ] **Step 4: Create workers.md**

How to run workers, split queues, scale, monitor queue depth, troubleshoot failed jobs. Task-oriented.

- [ ] **Step 5: Create development.md**

How to set up the local dev environment, run each component, run tests, rebuild a single component.

- [ ] **Step 6: Create migration.md**

One-time guide for migrating from the monolith. Disposable after migration.

- [ ] **Step 7: Update CLAUDE.md**

Update project-level instructions for the new codebase structure — new file paths, how to run things, how the pieces connect.

- [ ] **Step 8: Commit**

```bash
git add docs/ OPERATIONS.md CLAUDE.md
git commit -m "docs: Update architecture, operations, and add API/worker/dev guides"
```

---

### Task 20: End-to-end verification and cleanup

**Files:**
- No new files — verification of the full system

- [ ] **Step 1: Start local dev environment**

```bash
./dev-services.sh start
```

- [ ] **Step 2: Run database migration**

```bash
cd src/api && python scripts/migrate_token_usage.py
```

- [ ] **Step 3: Verify API health**

```bash
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/health/ready
```

- [ ] **Step 4: Verify Swagger docs**

Open `http://localhost:8080/api/v1/docs` — all endpoints should be listed with schemas.

- [ ] **Step 5: Test full recommendation flow**

```bash
# Submit a query
curl -X POST http://localhost:8080/api/v1/advisor/query \
  -H "Content-Type: application/json" \
  -d '{"query": "OpenShift virtualization booth demo"}'

# Stream results (replace JOB_ID)
curl -N http://localhost:8080/api/v1/advisor/query/JOB_ID/stream
```

- [ ] **Step 6: Test frontend**

Open `http://localhost:3000`:
- Submit a query in the advisor
- Verify streaming progress shows in chat
- Verify rec cards appear with green/yellow/white tiers
- Navigate to Browse page — verify catalog loads
- Navigate to Admin page — verify token usage and job list

- [ ] **Step 7: Run full test suite**

```bash
cd src/api && python -m pytest tests/ -v
```

- [ ] **Step 8: Commit any fixes**

```bash
git add -A
git commit -m "verification: End-to-end testing fixes"
```

---

## Summary

| Phase | Tasks | What it produces |
|---|---|---|
| **1: Foundation** | 1-4 | Project structure, config, logging, database layer |
| **2: API & Workers** | 5-11 | Full REST API, arq workers, SSE streaming, CLI |
| **3: Frontend** | 12-14 | React SPA with LCARS theme, all pages |
| **4: Containers & Deploy** | 15-17 | Containerfiles, Ansible manifests, dev script |
| **5: Migration & Docs** | 18-20 | Data migration, documentation, end-to-end verification |

Each phase produces independently testable software. Phase 2 can be tested via curl/Swagger before Phase 3 begins. Phase 3 can be developed against the running API from Phase 2.
