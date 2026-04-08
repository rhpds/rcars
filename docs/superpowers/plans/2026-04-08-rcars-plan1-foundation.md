# RCARS Plan 1: Foundation & Catalog Reader

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the RCARS project from scratch — repo scaffold, PostgreSQL+pgvector schema, config, Babylon CRD catalog reader, and CLI — so that `rcars refresh` reads catalog data from the Babylon K8s API and stores it in PostgreSQL.

**Architecture:** FastAPI Python app using the `kubernetes` Python client to query CatalogItem and AgnosticVComponent CRDs from the Babylon cluster. Data stored in PostgreSQL with pgvector extension. Click CLI for local development. Config via environment variables.

**Tech Stack:** Python 3.11+, Click, PostgreSQL 16 + pgvector, psycopg 3 (direct SQL, no ORM), kubernetes Python client, httpx, pytest, RHEL UBI 9 base image.

---

## File Structure

```
rcars-advisory/
├── pyproject.toml                          # Project metadata, dependencies, entry points
├── Dockerfile                              # RHEL UBI 9 multi-stage build
├── .gitignore                              # Python, data, IDE, .env exclusions
├── README.md                               # Project overview, quick start
├── src/
│   └── rcars/
│       ├── __init__.py                     # Package init, version
│       ├── config.py                       # Env var config, client factories
│       ├── db.py                           # PostgreSQL connection, schema, migrations
│       ├── catalog_reader.py               # Babylon CRD client (replaces scanner.py)
│       └── cli.py                          # Click CLI: refresh, status, list, show
├── tests/
│   ├── conftest.py                         # Shared fixtures (test DB, mock K8s)
│   ├── test_config.py                      # Config loading tests
│   ├── test_db.py                          # Schema creation, CRUD tests
│   ├── test_catalog_reader.py              # CRD parsing, field extraction tests
│   └── test_cli.py                         # CLI integration tests
└── docs/
    └── superpowers/
        ├── specs/
        └── plans/
```

Each file has one responsibility:
- `config.py` — reads environment, creates clients (K8s, Anthropic, DB)
- `db.py` — schema DDL, connection pool, CRUD functions
- `catalog_reader.py` — queries K8s API, extracts allowlisted fields, returns dicts
- `cli.py` — user-facing commands that compose the above

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/rcars/__init__.py`
- Create: `README.md`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "rcars"
version = "0.1.0"
description = "RHDP Content Advisory & Recommendation System"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "Apache-2.0"}
dependencies = [
    "click>=8.1",
    "httpx>=0.27.0",
    "kubernetes>=29.0",
    "psycopg[binary]>=3.1",
    "rich>=13.0",
]

[project.optional-dependencies]
web = [
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
]
analysis = [
    "anthropic[vertex]>=0.40.0",
    "sentence-transformers>=3.0",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]

[project.scripts]
rcars = "rcars.cli:cli"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
*.egg

# Virtual environments
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Data (never commit)
data/
*.db
*.sqlite

# Environment
.env
.env.*

# OS
.DS_Store

# Superpowers brainstorm artifacts
.superpowers/
```

- [ ] **Step 3: Create src/rcars/__init__.py**

```python
"""RCARS — RHDP Content Advisory & Recommendation System."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Create README.md**

```markdown
# RCARS — RHDP Content Advisory & Recommendation System

Recommendation engine that matches RHDP catalog items to events, booth opportunities,
and field requests. Analyzes Showroom content and uses semantic search + LLM reasoning
to recommend the best assets for any given use case.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up PostgreSQL (local dev)
podman run -d --name rcars-db -p 5432:5432 \
  -e POSTGRESQL_USER=rcars -e POSTGRESQL_PASSWORD=dev \
  -e POSTGRESQL_DATABASE=rcars \
  registry.redhat.io/rhel9/postgresql-16:latest

# Configure
export RCARS_DATABASE_URL="postgresql://rcars:dev@localhost:5432/rcars"

# Refresh catalog from Babylon CRDs (requires oc login)
rcars refresh

# Check status
rcars status
```
```

- [ ] **Step 5: Install in dev mode and verify**

Run: `cd ~/devel/working/rcars-advisory && pip install -e ".[dev]"`
Expected: Installs successfully, `rcars --help` shows the CLI (will fail until cli.py exists, that's fine)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore src/rcars/__init__.py README.md
git commit -m "rcars: Add project scaffold with pyproject.toml and package structure"
```

---

## Task 2: Configuration Module

**Files:**
- Create: `src/rcars/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
"""Tests for RCARS configuration."""

import os
import pytest
from rcars.config import Settings


def test_settings_defaults():
    """Settings should have sensible defaults for non-secret values."""
    settings = Settings()
    assert settings.database_url == ""
    assert settings.model == "claude-sonnet-4-6"
    assert settings.max_parallel == 5
    assert settings.clone_dir == "/tmp"
    assert settings.cloud_ml_region == "us-east5"


def test_settings_from_env(monkeypatch):
    """Settings should read from environment variables."""
    monkeypatch.setenv("RCARS_DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("RCARS_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("RCARS_MAX_PARALLEL", "10")
    settings = Settings()
    assert settings.database_url == "postgresql://test:test@localhost/test"
    assert settings.model == "claude-haiku-4-5-20251001"
    assert settings.max_parallel == 10


def test_settings_vertex_preferred(monkeypatch):
    """Vertex AI should be preferred when project ID is set."""
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "my-project")
    monkeypatch.setenv("CLOUD_ML_REGION", "us-central1")
    settings = Settings()
    assert settings.vertex_project_id == "my-project"
    assert settings.cloud_ml_region == "us-central1"
    assert settings.use_vertex is True


def test_settings_vertex_not_used_without_project(monkeypatch):
    """Should fall back to direct API when no Vertex project."""
    monkeypatch.delenv("ANTHROPIC_VERTEX_PROJECT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings()
    assert settings.use_vertex is False


def test_catalog_namespaces_prod_only():
    """Default catalog namespaces should be prod only."""
    settings = Settings()
    assert settings.catalog_namespaces_prod == ["babylon-catalog-prod"]


def test_catalog_namespaces_all():
    """All namespaces should include prod, dev, and event."""
    settings = Settings()
    expected = [
        "babylon-catalog-prod",
        "babylon-catalog-dev",
        "babylon-catalog-event",
    ]
    assert settings.catalog_namespaces_all == expected


def test_showroom_url_variables():
    """Should have the allowlisted Showroom URL variable names."""
    settings = Settings()
    assert "ocp4_workload_showroom_content_git_repo" in settings.showroom_url_vars
    assert "showroom_git_repo" in settings.showroom_url_vars
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rcars.config'`

- [ ] **Step 3: Create conftest.py and implement config.py**

Create `tests/conftest.py`:

```python
"""Shared test fixtures for RCARS."""
```

Create `src/rcars/config.py`:

```python
"""RCARS configuration from environment variables."""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings, all from environment variables."""

    # Database
    database_url: str = field(
        default_factory=lambda: os.environ.get("RCARS_DATABASE_URL", "")
    )

    # LLM
    model: str = field(
        default_factory=lambda: os.environ.get("RCARS_MODEL", "claude-sonnet-4-6")
    )
    vertex_project_id: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID", "")
    )
    cloud_ml_region: str = field(
        default_factory=lambda: os.environ.get("CLOUD_ML_REGION", "us-east5")
    )
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )

    # Scanning
    max_parallel: int = field(
        default_factory=lambda: int(os.environ.get("RCARS_MAX_PARALLEL", "5"))
    )
    clone_dir: str = field(
        default_factory=lambda: os.environ.get("RCARS_CLONE_DIR", "/tmp")
    )

    # Babylon K8s
    kubeconfig_path: str = field(
        default_factory=lambda: os.environ.get("RCARS_KUBECONFIG", "")
    )
    agnosticv_component_namespace: str = field(
        default_factory=lambda: os.environ.get(
            "RCARS_AGNOSTICV_NAMESPACE", "babylon-config"
        )
    )

    # Catalog namespaces
    catalog_namespaces_prod: list[str] = field(
        default_factory=lambda: ["babylon-catalog-prod"]
    )
    catalog_namespaces_all: list[str] = field(
        default_factory=lambda: [
            "babylon-catalog-prod",
            "babylon-catalog-dev",
            "babylon-catalog-event",
        ]
    )

    # Showroom URL variable names to extract from AgnosticVComponent
    showroom_url_vars: list[str] = field(
        default_factory=lambda: [
            "ocp4_workload_showroom_content_git_repo",
            "showroom_git_repo",
        ]
    )
    showroom_ref_vars: list[str] = field(
        default_factory=lambda: [
            "ocp4_workload_showroom_content_git_repo_ref",
            "showroom_git_repo_ref",
        ]
    )

    @property
    def use_vertex(self) -> bool:
        """Whether to use Vertex AI (preferred) or direct Anthropic API."""
        return bool(self.vertex_project_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_config.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/rcars/config.py tests/conftest.py tests/test_config.py
git commit -m "rcars: Add configuration module with env var settings"
```

---

## Task 3: Database Schema & Connection

**Files:**
- Create: `src/rcars/db.py`
- Create: `tests/test_db.py`

This task requires a running PostgreSQL with pgvector. Tests use a real test database.

- [ ] **Step 1: Write the failing test**

Create `tests/test_db.py`:

```python
"""Tests for RCARS database layer."""

import os
import pytest
from rcars.db import Database


# Use a test database — set RCARS_TEST_DATABASE_URL or skip
TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    """Create a fresh test database with schema."""
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.drop_schema()
    database.close()


def test_create_schema(db):
    """Schema creation should create all expected tables."""
    tables = db.list_tables()
    assert "catalog_items" in tables
    assert "showroom_analysis" in tables
    assert "enrichment_tags" in tables
    assert "embeddings" in tables
    assert "analysis_log" in tables
    assert "jobs" in tables


def test_upsert_catalog_item(db):
    """Should insert a new catalog item and return it."""
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Test Item",
        "category": "Demos",
        "product": "Red_Hat_OpenShift_Container_Platform",
        "product_family": "Red_Hat_Cloud",
        "primary_bu": "Hybrid_Platforms",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "keywords": ["openshift", "demo"],
        "description": "A test demo item",
        "showroom_url": "https://github.com/example/showroom-test.git",
        "showroom_ref": "main",
        "is_prod": True,
    }
    db.upsert_catalog_item(item)
    result = db.get_catalog_item("test.item.prod")
    assert result is not None
    assert result["display_name"] == "Test Item"
    assert result["category"] == "Demos"
    assert result["is_prod"] is True
    assert result["keywords"] == ["openshift", "demo"]


def test_upsert_catalog_item_updates(db):
    """Upsert should update existing items, not duplicate."""
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Original Name",
        "category": "Demos",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
    }
    db.upsert_catalog_item(item)

    item["display_name"] = "Updated Name"
    db.upsert_catalog_item(item)

    result = db.get_catalog_item("test.item.prod")
    assert result["display_name"] == "Updated Name"

    all_items = db.list_catalog_items()
    assert len(all_items) == 1


def test_list_catalog_items_filter_prod(db):
    """Should filter catalog items by prod status."""
    db.upsert_catalog_item({
        "ci_name": "prod.item",
        "display_name": "Prod Item",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
    })
    db.upsert_catalog_item({
        "ci_name": "dev.item",
        "display_name": "Dev Item",
        "stage": "dev",
        "catalog_namespace": "babylon-catalog-dev",
        "is_prod": False,
    })

    prod_only = db.list_catalog_items(prod_only=True)
    assert len(prod_only) == 1
    assert prod_only[0]["ci_name"] == "prod.item"

    all_items = db.list_catalog_items(prod_only=False)
    assert len(all_items) == 2


def test_log_action(db):
    """Should log an action and retrieve it."""
    db.log_action("test.item", "refresh", user_id=None, details="Initial scan")
    logs = db.get_recent_logs(limit=10)
    assert len(logs) == 1
    assert logs[0]["ci_name"] == "test.item"
    assert logs[0]["action"] == "refresh"
    assert logs[0]["details"] == "Initial scan"


def test_get_status_summary(db):
    """Should return summary counts."""
    db.upsert_catalog_item({
        "ci_name": "item1",
        "display_name": "Item 1",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
        "showroom_url": "https://github.com/example/showroom.git",
    })
    db.upsert_catalog_item({
        "ci_name": "item2",
        "display_name": "Item 2",
        "stage": "dev",
        "catalog_namespace": "babylon-catalog-dev",
        "is_prod": False,
    })

    summary = db.get_status_summary()
    assert summary["total"] == 2
    assert summary["prod"] == 1
    assert summary["with_showroom"] == 1
```

- [ ] **Step 2: Create test database**

Run:
```bash
# Ensure PostgreSQL is running with pgvector
podman run -d --name rcars-db -p 5432:5432 \
  -e POSTGRES_USER=rcars -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=rcars \
  pgvector/pgvector:pg16

# Create test database
PGPASSWORD=dev psql -h localhost -U rcars -d rcars -c "CREATE DATABASE rcars_test;"

# Enable pgvector extension in test database
PGPASSWORD=dev psql -h localhost -U rcars -d rcars_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Note: Using `pgvector/pgvector:pg16` for local dev convenience (pgvector pre-installed). Production uses RHEL-based image per spec.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rcars.db'`

- [ ] **Step 4: Implement db.py**

Create `src/rcars/db.py`:

```python
"""PostgreSQL + pgvector database layer for RCARS."""

import logging
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

log = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS catalog_items (
    ci_name TEXT PRIMARY KEY,
    display_name TEXT,
    category TEXT,
    product TEXT,
    product_family TEXT,
    primary_bu TEXT,
    secondary_bu TEXT,
    stage TEXT,
    catalog_namespace TEXT,
    keywords TEXT[],
    description TEXT,
    icon_url TEXT,
    owners_json JSONB,
    showroom_url TEXT,
    showroom_ref TEXT,
    last_crd_update TIMESTAMPTZ,
    last_refreshed TIMESTAMPTZ DEFAULT NOW(),
    is_prod BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS showroom_analysis (
    ci_name TEXT PRIMARY KEY REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    content_type TEXT,
    summary TEXT,
    products_json JSONB,
    audience_json JSONB,
    topics_json JSONB,
    modules_json JSONB,
    learning_objectives_json JSONB,
    difficulty TEXT,
    estimated_duration_min INTEGER,
    event_fit_json JSONB,
    use_cases_json JSONB,
    last_repo_commit TEXT,
    last_repo_updated TIMESTAMPTZ,
    last_analyzed TIMESTAMPTZ,
    is_stale BOOLEAN DEFAULT FALSE,
    stale_commit TEXT,
    enrichment_review_needed BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS enrichment_tags (
    id SERIAL PRIMARY KEY,
    ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    added_by TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ci_name, tag_type, tag_value)
);

CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    embed_type TEXT NOT NULL,
    module_title TEXT,
    content_text TEXT,
    embedding vector(384)
);

CREATE TABLE IF NOT EXISTS analysis_log (
    id SERIAL PRIMARY KEY,
    ci_name TEXT,
    action TEXT NOT NULL,
    user_id TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    triggered_by TEXT,
    progress_current INTEGER DEFAULT 0,
    progress_total INTEGER DEFAULT 0,
    result_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_catalog_items_stage ON catalog_items(stage);
CREATE INDEX IF NOT EXISTS idx_catalog_items_is_prod ON catalog_items(is_prod);
CREATE INDEX IF NOT EXISTS idx_catalog_items_category ON catalog_items(category);
CREATE INDEX IF NOT EXISTS idx_catalog_items_showroom_url ON catalog_items(showroom_url);
CREATE INDEX IF NOT EXISTS idx_enrichment_tags_ci_name ON enrichment_tags(ci_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_ci_name ON embeddings(ci_name);
CREATE INDEX IF NOT EXISTS idx_analysis_log_ci_name ON analysis_log(ci_name);
CREATE INDEX IF NOT EXISTS idx_analysis_log_created_at ON analysis_log(created_at);
"""


class Database:
    """PostgreSQL database connection and operations."""

    def __init__(self, database_url: str):
        self._url = database_url
        self._conn = psycopg.connect(database_url, row_factory=dict_row)
        self._conn.autocommit = False

    def close(self):
        """Close the database connection."""
        self._conn.close()

    def create_schema(self):
        """Create all tables if they don't exist."""
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(SCHEMA_SQL)
        self._conn.commit()

    def drop_schema(self):
        """Drop all tables. Only for testing."""
        tables = [
            "embeddings", "enrichment_tags", "showroom_analysis",
            "analysis_log", "jobs", "catalog_items",
        ]
        with self._conn.cursor() as cur:
            for table in tables:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        self._conn.commit()

    def list_tables(self) -> list[str]:
        """List all tables in the public schema."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            return [row["tablename"] for row in cur.fetchall()]

    def upsert_catalog_item(self, item: dict[str, Any]):
        """Insert or update a catalog item."""
        fields = [
            "ci_name", "display_name", "category", "product", "product_family",
            "primary_bu", "secondary_bu", "stage", "catalog_namespace",
            "keywords", "description", "icon_url", "owners_json",
            "showroom_url", "showroom_ref", "last_crd_update", "is_prod",
        ]
        present = {k: item.get(k) for k in fields if k in item}
        present["last_refreshed"] = datetime.now(timezone.utc)

        columns = list(present.keys())
        placeholders = [f"%({k})s" for k in columns]
        updates = [f"{k} = EXCLUDED.{k}" for k in columns if k != "ci_name"]

        sql = f"""
            INSERT INTO catalog_items ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (ci_name) DO UPDATE SET {', '.join(updates)}
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, present)
        self._conn.commit()

    def get_catalog_item(self, ci_name: str) -> dict[str, Any] | None:
        """Get a single catalog item by name."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM catalog_items WHERE ci_name = %(ci_name)s",
                {"ci_name": ci_name},
            )
            return cur.fetchone()

    def list_catalog_items(
        self, prod_only: bool = False, category: str | None = None
    ) -> list[dict[str, Any]]:
        """List catalog items with optional filters."""
        conditions = []
        params: dict[str, Any] = {}

        if prod_only:
            conditions.append("is_prod = TRUE")
        if category:
            conditions.append("category = %(category)s")
            params["category"] = category

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM catalog_items {where} ORDER BY ci_name"

        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def log_action(
        self,
        ci_name: str,
        action: str,
        user_id: str | None = None,
        details: str | None = None,
    ):
        """Log an action to the audit trail."""
        with self._conn.cursor() as cur:
            cur.execute(
                """INSERT INTO analysis_log (ci_name, action, user_id, details)
                   VALUES (%(ci_name)s, %(action)s, %(user_id)s, %(details)s)""",
                {
                    "ci_name": ci_name,
                    "action": action,
                    "user_id": user_id,
                    "details": details,
                },
            )
        self._conn.commit()

    def get_recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent log entries."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM analysis_log ORDER BY created_at DESC LIMIT %(limit)s",
                {"limit": limit},
            )
            return cur.fetchall()

    def get_status_summary(self) -> dict[str, int]:
        """Get summary counts for the catalog."""
        with self._conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM catalog_items")
            total = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE is_prod = TRUE")
            prod = cur.fetchone()["count"]

            cur.execute(
                "SELECT COUNT(*) as count FROM catalog_items WHERE showroom_url IS NOT NULL AND showroom_url != ''"
            )
            with_showroom = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) as count FROM showroom_analysis")
            analyzed = cur.fetchone()["count"]

            cur.execute(
                "SELECT COUNT(*) as count FROM showroom_analysis WHERE is_stale = TRUE"
            )
            stale = cur.fetchone()["count"]

        return {
            "total": total,
            "prod": prod,
            "with_showroom": with_showroom,
            "analyzed": analyzed,
            "stale": stale,
        }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/rcars/db.py tests/test_db.py
git commit -m "rcars: Add PostgreSQL+pgvector database layer with schema and CRUD"
```

---

## Task 4: Catalog Reader — CRD Parsing

**Files:**
- Create: `src/rcars/catalog_reader.py`
- Create: `tests/test_catalog_reader.py`

This task implements the CRD field extraction logic. Tests use mock CRD data (no live cluster needed).

- [ ] **Step 1: Write the failing test**

Create `tests/test_catalog_reader.py`:

```python
"""Tests for Babylon CRD catalog reader."""

import pytest
from rcars.catalog_reader import (
    extract_catalog_item,
    extract_showroom_url,
    CRD_FIELD_ALLOWLIST,
)


SAMPLE_CATALOG_ITEM = {
    "apiVersion": "babylon.gpte.redhat.com/v1",
    "kind": "CatalogItem",
    "metadata": {
        "name": "openshift-cnv.ocp4-lightspeed-cnv.prod",
        "namespace": "babylon-catalog-prod",
        "labels": {
            "babylon.gpte.redhat.com/Product": "Red_Hat_OpenShift_Container_Platform",
            "babylon.gpte.redhat.com/Product_Family": "Red_Hat_Cloud",
            "babylon.gpte.redhat.com/category": "Demos",
            "babylon.gpte.redhat.com/stage": "prod",
            "demo.redhat.com/primaryBU": "Hybrid_Platforms",
            "demo.redhat.com/secondaryBU": "Artificial_Intelligence",
        },
    },
    "spec": {
        "displayName": "OpenShift Lightspeed Demo (CNV)",
        "category": "Demos",
        "keywords": ["openshift", "ocp", "lightspeed", "ols"],
        "description": {
            "content": "This environment provides an OpenShift cluster with Lightspeed.",
            "format": "asciidoc",
        },
        "icon": {
            "url": "https://gpte-public.s3.amazonaws.com/catalog-icon-openshift.svg"
        },
        "owners": {
            "maintainer": [
                {"email": "your-email@redhat.com", "name": "Test User"},
            ]
        },
        "lastUpdate": {
            "git": {
                "when_committer": "2026-03-18T15:40:37Z",
                "hash": "e09ad80d",
            }
        },
    },
}


SAMPLE_AGNOSTICV_COMPONENT = {
    "spec": {
        "definition": {
            "ocp4_workload_showroom_content_git_repo": "https://github.com/dialvare/showroom-openshift-lightspeed.git",
            "ocp4_workload_showroom_content_git_repo_ref": "main",
            "ocp4_workload_ols_api_token": "$ANSIBLE_VAULT;1.2;AES256;secret_data",
            "ssh_authorized_keys": [{"key": "ssh-rsa AAAA..."}],
            "agnosticd_save_output_dir_s3_secret_access_key": "$ANSIBLE_VAULT;data",
        }
    }
}


SAMPLE_COMPONENT_SHOWROOM_GIT_REPO = {
    "spec": {
        "definition": {
            "showroom_git_repo": "https://github.com/example/showroom-alt.git",
            "showroom_git_repo_ref": "v2.0",
        }
    }
}


SAMPLE_COMPONENT_NO_SHOWROOM = {
    "spec": {
        "definition": {
            "cloud_provider": "aws",
            "env_type": "ocp4-workshop",
        }
    }
}


def test_extract_catalog_item_basic_fields():
    """Should extract display name, category, product from CatalogItem."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert result["ci_name"] == "openshift-cnv.ocp4-lightspeed-cnv.prod"
    assert result["display_name"] == "OpenShift Lightspeed Demo (CNV)"
    assert result["category"] == "Demos"
    assert result["product"] == "Red_Hat_OpenShift_Container_Platform"
    assert result["product_family"] == "Red_Hat_Cloud"
    assert result["primary_bu"] == "Hybrid_Platforms"
    assert result["secondary_bu"] == "Artificial_Intelligence"
    assert result["stage"] == "prod"
    assert result["is_prod"] is True


def test_extract_catalog_item_keywords():
    """Should extract keywords as a list."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert result["keywords"] == ["openshift", "ocp", "lightspeed", "ols"]


def test_extract_catalog_item_description():
    """Should extract description content."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert "OpenShift cluster with Lightspeed" in result["description"]


def test_extract_catalog_item_owners():
    """Should extract owners as JSON."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert result["owners_json"]["maintainer"][0]["name"] == "Test User"


def test_extract_catalog_item_namespace():
    """Should preserve the catalog namespace."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert result["catalog_namespace"] == "babylon-catalog-prod"


def test_extract_catalog_item_dev_stage():
    """Dev items should have is_prod=False."""
    item = {
        "metadata": {
            "name": "test.dev",
            "namespace": "babylon-catalog-dev",
            "labels": {"babylon.gpte.redhat.com/stage": "dev"},
        },
        "spec": {"displayName": "Dev Item"},
    }
    result = extract_catalog_item(item)
    assert result["stage"] == "dev"
    assert result["is_prod"] is False


def test_extract_showroom_url_primary_var():
    """Should extract Showroom URL from ocp4_workload_ variable."""
    url, ref = extract_showroom_url(SAMPLE_AGNOSTICV_COMPONENT)
    assert url == "https://github.com/dialvare/showroom-openshift-lightspeed.git"
    assert ref == "main"


def test_extract_showroom_url_alternate_var():
    """Should extract from showroom_git_repo variable name."""
    url, ref = extract_showroom_url(SAMPLE_COMPONENT_SHOWROOM_GIT_REPO)
    assert url == "https://github.com/example/showroom-alt.git"
    assert ref == "v2.0"


def test_extract_showroom_url_missing():
    """Should return None when no Showroom URL found."""
    url, ref = extract_showroom_url(SAMPLE_COMPONENT_NO_SHOWROOM)
    assert url is None
    assert ref is None


def test_extract_showroom_url_no_secrets_leaked():
    """Extraction must never return sensitive fields."""
    url, ref = extract_showroom_url(SAMPLE_AGNOSTICV_COMPONENT)
    # The function should only return URL and ref, never secrets
    assert "ANSIBLE_VAULT" not in str(url)
    assert "ANSIBLE_VAULT" not in str(ref)


def test_crd_field_allowlist_excludes_secrets():
    """The allowlist should only contain safe field names."""
    for field_name in CRD_FIELD_ALLOWLIST:
        assert "secret" not in field_name.lower()
        assert "password" not in field_name.lower()
        assert "token" not in field_name.lower()
        assert "vault" not in field_name.lower()
        assert "ssh" not in field_name.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_catalog_reader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rcars.catalog_reader'`

- [ ] **Step 3: Implement catalog_reader.py**

Create `src/rcars/catalog_reader.py`:

```python
"""Babylon CRD catalog reader.

Reads CatalogItem and AgnosticVComponent CRDs from the Babylon K8s API
and extracts catalog metadata and Showroom URLs using a strict allowlist.
"""

import logging
from datetime import datetime
from typing import Any

from kubernetes import client, config as k8s_config

log = logging.getLogger(__name__)

# Only these fields are extracted from AgnosticVComponent spec.definition.
# Everything else (vault secrets, SSH keys, credentials) is discarded.
CRD_FIELD_ALLOWLIST = [
    "ocp4_workload_showroom_content_git_repo",
    "ocp4_workload_showroom_content_git_repo_ref",
    "showroom_git_repo",
    "showroom_git_repo_ref",
]

LABEL_PREFIX = "babylon.gpte.redhat.com/"
DEMO_LABEL_PREFIX = "demo.redhat.com/"


def _get_label(metadata: dict, key: str, prefix: str = LABEL_PREFIX) -> str:
    """Get a label value from CRD metadata, or empty string."""
    labels = metadata.get("labels", {}) or {}
    return labels.get(f"{prefix}{key}", "")


def extract_catalog_item(crd: dict[str, Any]) -> dict[str, Any]:
    """Extract catalog metadata from a CatalogItem CRD.

    Returns a dict suitable for db.upsert_catalog_item().
    """
    metadata = crd.get("metadata", {})
    spec = crd.get("spec", {})
    labels = metadata.get("labels", {}) or {}

    stage = _get_label(metadata, "stage")

    # Description can be a string or a dict with content/format
    description = spec.get("description", "")
    if isinstance(description, dict):
        description = description.get("content", "")

    # Last update timestamp
    last_update = spec.get("lastUpdate", {})
    last_crd_update = None
    if last_update and "git" in last_update:
        when = last_update["git"].get("when_committer")
        if when:
            try:
                last_crd_update = datetime.fromisoformat(
                    when.replace("Z", "+00:00")
                )
            except ValueError:
                pass

    return {
        "ci_name": metadata.get("name", ""),
        "display_name": spec.get("displayName", ""),
        "category": spec.get("category", _get_label(metadata, "category")),
        "product": _get_label(metadata, "Product"),
        "product_family": _get_label(metadata, "Product_Family"),
        "primary_bu": labels.get(f"{DEMO_LABEL_PREFIX}primaryBU", ""),
        "secondary_bu": labels.get(f"{DEMO_LABEL_PREFIX}secondaryBU", ""),
        "stage": stage,
        "catalog_namespace": metadata.get("namespace", ""),
        "keywords": spec.get("keywords", []) or [],
        "description": description,
        "icon_url": (spec.get("icon") or {}).get("url", ""),
        "owners_json": spec.get("owners"),
        "last_crd_update": last_crd_update,
        "is_prod": stage == "prod",
    }


def extract_showroom_url(
    component_crd: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Extract Showroom URL and ref from an AgnosticVComponent CRD.

    Uses a strict allowlist — only Showroom URL/ref variables are read.
    All other fields in spec.definition (secrets, credentials, SSH keys)
    are ignored.

    Returns (url, ref) tuple. Both are None if no Showroom URL found.
    """
    definition = (
        component_crd.get("spec", {}).get("definition", {}) or {}
    )

    url_vars = [
        "ocp4_workload_showroom_content_git_repo",
        "showroom_git_repo",
    ]
    ref_vars = [
        "ocp4_workload_showroom_content_git_repo_ref",
        "showroom_git_repo_ref",
    ]

    url = None
    ref = None

    for var in url_vars:
        value = definition.get(var)
        if value and isinstance(value, str) and not value.startswith("{{"):
            url = value
            break

    for var in ref_vars:
        value = definition.get(var)
        if value and isinstance(value, str) and not value.startswith("{{"):
            ref = value
            break

    return url, ref


class CatalogReader:
    """Reads catalog data from Babylon K8s CRDs."""

    CATALOG_ITEM_GROUP = "babylon.gpte.redhat.com"
    CATALOG_ITEM_VERSION = "v1"
    CATALOG_ITEM_PLURAL = "catalogitems"

    COMPONENT_GROUP = "gpte.redhat.com"
    COMPONENT_VERSION = "v1"
    COMPONENT_PLURAL = "agnosticvcomponents"

    def __init__(self, kubeconfig_path: str = ""):
        """Initialize with kubeconfig. Empty string uses default (~/.kube/config)."""
        if kubeconfig_path:
            k8s_config.load_kube_config(config_file=kubeconfig_path)
        else:
            try:
                k8s_config.load_incluster_config()
            except k8s_config.ConfigException:
                k8s_config.load_kube_config()

        self._custom_api = client.CustomObjectsApi()

    def list_catalog_items(self, namespace: str) -> list[dict[str, Any]]:
        """List all CatalogItems in a namespace."""
        result = self._custom_api.list_namespaced_custom_object(
            group=self.CATALOG_ITEM_GROUP,
            version=self.CATALOG_ITEM_VERSION,
            namespace=namespace,
            plural=self.CATALOG_ITEM_PLURAL,
        )
        return result.get("items", [])

    def get_agnosticv_component(
        self, name: str, namespace: str
    ) -> dict[str, Any] | None:
        """Get a single AgnosticVComponent by name."""
        try:
            return self._custom_api.get_namespaced_custom_object(
                group=self.COMPONENT_GROUP,
                version=self.COMPONENT_VERSION,
                namespace=namespace,
                plural=self.COMPONENT_PLURAL,
                name=name,
            )
        except client.ApiException as e:
            if e.status == 404:
                log.debug("AgnosticVComponent %s not found in %s", name, namespace)
                return None
            raise

    def refresh_catalog(
        self,
        namespaces: list[str],
        component_namespace: str = "babylon-config",
    ) -> list[dict[str, Any]]:
        """Refresh catalog from CRDs. Returns list of extracted items.

        For each CatalogItem, fetches the matching AgnosticVComponent
        to extract the Showroom URL.
        """
        items = []

        for ns in namespaces:
            log.info("Reading CatalogItems from %s", ns)
            try:
                crds = self.list_catalog_items(ns)
            except client.ApiException as e:
                log.error("Failed to list CatalogItems in %s: %s", ns, e.reason)
                continue

            for crd in crds:
                item = extract_catalog_item(crd)
                ci_name = item["ci_name"]

                # Fetch matching AgnosticVComponent for Showroom URL
                component = self.get_agnosticv_component(
                    ci_name, component_namespace
                )
                if component:
                    url, ref = extract_showroom_url(component)
                    item["showroom_url"] = url
                    item["showroom_ref"] = ref

                items.append(item)

            log.info("Found %d CatalogItems in %s", len(crds), ns)

        return items
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_catalog_reader.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/rcars/catalog_reader.py tests/test_catalog_reader.py
git commit -m "rcars: Add Babylon CRD catalog reader with allowlisted field extraction"
```

---

## Task 5: CLI — refresh, status, list, show

**Files:**
- Create: `src/rcars/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
"""Tests for RCARS CLI."""

import os
import pytest
from click.testing import CliRunner
from rcars.cli import cli


TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def runner(monkeypatch):
    """CLI test runner with test database."""
    monkeypatch.setenv("RCARS_DATABASE_URL", TEST_DB_URL)
    return CliRunner()


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure clean schema for each test."""
    from rcars.db import Database
    db = Database(TEST_DB_URL)
    db.create_schema()
    yield
    db.drop_schema()
    db.close()


def test_cli_help(runner):
    """CLI should show help text."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "RCARS" in result.output or "rcars" in result.output


def test_status_empty_db(runner):
    """Status should work on empty database."""
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "0" in result.output


def test_list_empty_db(runner):
    """List should work on empty database."""
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0


def test_show_nonexistent(runner):
    """Show should handle missing CI gracefully."""
    result = runner.invoke(cli, ["show", "nonexistent.item"])
    assert result.exit_code == 0
    assert "not found" in result.output.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rcars.cli'`

- [ ] **Step 3: Implement cli.py**

Create `src/rcars/cli.py`:

```python
"""RCARS CLI — RHDP Content Advisory & Recommendation System."""

import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from rcars.config import Settings
from rcars.db import Database

console = Console()
log = logging.getLogger("rcars")


def get_db() -> Database:
    """Get database connection from settings."""
    settings = Settings()
    if not settings.database_url:
        console.print("[red]Error:[/red] RCARS_DATABASE_URL not set")
        sys.exit(1)
    db = Database(settings.database_url)
    db.create_schema()
    return db


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(verbose: bool):
    """RCARS — RHDP Content Advisory & Recommendation System."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


@cli.command()
@click.option(
    "--include-dev",
    is_flag=True,
    default=False,
    help="Include dev and event catalog items (default: prod only)",
)
def refresh(include_dev: bool):
    """Refresh catalog from Babylon CRDs."""
    from rcars.catalog_reader import CatalogReader

    settings = Settings()
    db = get_db()

    namespaces = (
        settings.catalog_namespaces_all if include_dev
        else settings.catalog_namespaces_prod
    )

    console.print(f"[bold]Refreshing catalog from {len(namespaces)} namespace(s)...[/bold]")

    try:
        reader = CatalogReader(settings.kubeconfig_path)
        items = reader.refresh_catalog(
            namespaces=namespaces,
            component_namespace=settings.agnosticv_component_namespace,
        )
    except Exception as e:
        console.print(f"[red]Error connecting to cluster:[/red] {e}")
        db.close()
        sys.exit(1)

    count_with_showroom = 0
    for item in items:
        db.upsert_catalog_item(item)
        db.log_action(item["ci_name"], "refresh")
        if item.get("showroom_url"):
            count_with_showroom += 1

    console.print(f"[green]Done.[/green] {len(items)} items refreshed, {count_with_showroom} with Showroom URLs")
    db.close()


@cli.command()
def status():
    """Show catalog status summary."""
    db = get_db()
    summary = db.get_status_summary()

    table = Table(title="RCARS Catalog Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Total catalog items", str(summary["total"]))
    table.add_row("Production items", str(summary["prod"]))
    table.add_row("With Showroom URL", str(summary["with_showroom"]))
    table.add_row("Analyzed", str(summary["analyzed"]))
    table.add_row("Stale", str(summary["stale"]))

    console.print(table)
    db.close()


@cli.command("list")
@click.option("--prod-only", is_flag=True, default=False, help="Show only prod items")
@click.option("--with-showroom", is_flag=True, default=False, help="Only items with Showroom URLs")
@click.option("--category", type=str, default=None, help="Filter by category")
def list_items(prod_only: bool, with_showroom: bool, category: str | None):
    """List catalog items."""
    db = get_db()
    items = db.list_catalog_items(prod_only=prod_only, category=category)

    if with_showroom:
        items = [i for i in items if i.get("showroom_url")]

    table = Table(title=f"Catalog Items ({len(items)})")
    table.add_column("CI Name", style="cyan", max_width=50)
    table.add_column("Display Name", max_width=40)
    table.add_column("Category")
    table.add_column("Stage")
    table.add_column("Showroom", justify="center")

    for item in items:
        showroom = "[green]Yes[/green]" if item.get("showroom_url") else "[dim]-[/dim]"
        table.add_row(
            item["ci_name"],
            item.get("display_name", ""),
            item.get("category", ""),
            item.get("stage", ""),
            showroom,
        )

    console.print(table)
    db.close()


@cli.command()
@click.argument("ci_name")
def show(ci_name: str):
    """Show details for a specific catalog item."""
    db = get_db()
    item = db.get_catalog_item(ci_name)

    if not item:
        console.print(f"[yellow]Not found:[/yellow] {ci_name}")
        db.close()
        return

    console.print(f"\n[bold]{item.get('display_name', ci_name)}[/bold]")
    console.print(f"  CI Name:    {item['ci_name']}")
    console.print(f"  Category:   {item.get('category', '-')}")
    console.print(f"  Product:    {item.get('product', '-')}")
    console.print(f"  Stage:      {item.get('stage', '-')}")
    console.print(f"  Keywords:   {', '.join(item.get('keywords') or [])}")
    console.print(f"  Showroom:   {item.get('showroom_url', '-')}")
    console.print(f"  Ref:        {item.get('showroom_ref', '-')}")

    if item.get("description"):
        console.print(f"\n  [dim]{item['description'][:200]}...[/dim]")

    console.print()
    db.close()
```

- [ ] **Step 4: Reinstall package and run tests**

Run:
```bash
cd ~/devel/working/rcars-advisory && pip install -e ".[dev]"
python -m pytest tests/test_cli.py -v
```
Expected: All 4 tests PASS

- [ ] **Step 5: Run all tests together**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/ -v`
Expected: All tests PASS (config + db + catalog_reader + cli)

- [ ] **Step 6: Commit**

```bash
git add src/rcars/cli.py tests/test_cli.py
git commit -m "rcars: Add CLI with refresh, status, list, and show commands"
```

---

## Task 6: Integration Test — Live Cluster

**Files:**
- Create: `tests/test_integration.py`

This test runs against a real Babylon cluster (requires `oc login`). It's marked with `@pytest.mark.integration` so it can be skipped in CI.

- [ ] **Step 1: Write the integration test**

Create `tests/test_integration.py`:

```python
"""Integration tests against live Babylon cluster.

Run with: pytest tests/test_integration.py -v -m integration
Requires: oc login to a Babylon cluster
"""

import os
import pytest
from rcars.catalog_reader import CatalogReader, extract_catalog_item, extract_showroom_url
from rcars.config import Settings
from rcars.db import Database

pytestmark = pytest.mark.integration

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def reader():
    """CatalogReader connected to real cluster."""
    settings = Settings()
    return CatalogReader(settings.kubeconfig_path)


@pytest.fixture
def db():
    """Clean test database."""
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.drop_schema()
    database.close()


def test_list_prod_catalog_items(reader):
    """Should list CatalogItems from babylon-catalog-prod."""
    items = reader.list_catalog_items("babylon-catalog-prod")
    assert len(items) > 0
    # Verify structure of first item
    first = items[0]
    assert "metadata" in first
    assert "spec" in first
    assert "name" in first["metadata"]


def test_extract_real_catalog_item(reader):
    """Should extract fields from a real CatalogItem."""
    items = reader.list_catalog_items("babylon-catalog-prod")
    assert len(items) > 0
    result = extract_catalog_item(items[0])
    assert result["ci_name"] != ""
    assert result["catalog_namespace"] == "babylon-catalog-prod"
    assert result["is_prod"] is True


def test_get_agnosticv_component(reader):
    """Should fetch a matching AgnosticVComponent."""
    items = reader.list_catalog_items("babylon-catalog-prod")
    assert len(items) > 0
    ci_name = items[0]["metadata"]["name"]
    component = reader.get_agnosticv_component(ci_name, "babylon-config")
    # Component may or may not exist, but the call should not error
    if component:
        assert "spec" in component
        assert "definition" in component["spec"]


def test_full_refresh_to_db(reader, db):
    """Full refresh should populate the database."""
    items = reader.refresh_catalog(
        namespaces=["babylon-catalog-prod"],
        component_namespace="babylon-config",
    )
    assert len(items) > 0

    for item in items:
        db.upsert_catalog_item(item)

    summary = db.get_status_summary()
    assert summary["total"] > 0
    assert summary["prod"] > 0

    # At least some items should have Showroom URLs
    assert summary["with_showroom"] > 0


def test_showroom_url_extraction_no_secrets(reader):
    """Showroom URL extraction must never return vault/secret data."""
    items = reader.list_catalog_items("babylon-catalog-prod")
    for crd in items[:10]:
        ci_name = crd["metadata"]["name"]
        component = reader.get_agnosticv_component(ci_name, "babylon-config")
        if component:
            url, ref = extract_showroom_url(component)
            if url:
                assert "ANSIBLE_VAULT" not in url
                assert "ssh-rsa" not in url
            if ref:
                assert "ANSIBLE_VAULT" not in ref
```

- [ ] **Step 2: Add pytest marker configuration**

Add to `pyproject.toml` at the end:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: tests requiring live Babylon cluster (deselect with '-m not integration')",
]
```

- [ ] **Step 3: Run integration tests (requires oc login)**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_integration.py -v -m integration`
Expected: All integration tests PASS (assuming `oc login` is active)

- [ ] **Step 4: Run all non-integration tests to verify nothing broke**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/ -v -m "not integration"`
Expected: All unit tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_integration.py pyproject.toml
git commit -m "rcars: Add integration tests for live Babylon cluster catalog reader"
```

---

## Task 7: Dockerfile

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# RCARS — RHDP Content Advisory & Recommendation System
# Multi-stage build using RHEL UBI 9

FROM registry.access.redhat.com/ubi9/python-311:latest AS builder

USER 0
WORKDIR /opt/app-root/src

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[web,analysis]"

FROM registry.access.redhat.com/ubi9/python-311:latest AS runtime

USER 0

# Install git for shallow Showroom clones
RUN dnf install -y --nodocs git-core && \
    dnf clean all

USER 1001
WORKDIR /opt/app-root/src

COPY --from=builder /opt/app-root/lib /opt/app-root/lib
COPY --from=builder /opt/app-root/bin /opt/app-root/bin
COPY src/ src/
COPY prompts/ prompts/

ENV PATH="/opt/app-root/bin:$PATH"

EXPOSE 8080

CMD ["uvicorn", "rcars.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Verify Dockerfile builds (optional — arm64 local, amd64 target)**

Run:
```bash
cd ~/devel/working/rcars-advisory && podman build -t rcars:dev .
```
Expected: Build succeeds (web/analysis deps not yet needed, but structure is valid). May warn about missing `prompts/` directory — that's fine, it comes in Plan 2.

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "rcars: Add RHEL UBI 9 multi-stage Dockerfile"
```

---

## Summary

After completing Plan 1, you will have:

- **Project scaffold** — `pyproject.toml`, `.gitignore`, `README.md`, package structure
- **Configuration** — env var-based settings with Vertex AI and K8s support
- **Database** — PostgreSQL+pgvector schema with all tables, CRUD operations, connection management
- **Catalog reader** — Babylon CRD client with allowlisted field extraction, security-safe Showroom URL extraction
- **CLI** — `rcars refresh`, `rcars status`, `rcars list`, `rcars show`
- **Tests** — Unit tests for all modules + integration test against live cluster
- **Dockerfile** — RHEL UBI 9 multi-stage build

**What comes next in Plan 2:**
- Showroom analyzer (improved prompts, learning objectives)
- Recommender (pgvector semantic search + Sonnet ranking)
- Embeddings generation (sentence-transformers)
- `rcars scan` and `rcars recommend` commands
