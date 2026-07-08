# API Authentication for External Access — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable authenticated external access to the RCARS API via API keys, with an OAuth-based login flow for interactive users and an admin UI for key management.

**Architecture:** API keys (SHA-256 hashed, DB-stored) are the single external credential. Interactive users get 24h keys via an OpenShift OAuth login ceremony; admins create long-lived service keys via the API/UI. A second OpenShift Route exposes the API directly (bypassing OAuth proxy). The proxy verification secret becomes mandatory on all deployed environments.

**Tech Stack:** Python 3.11 / FastAPI 2.0 / psycopg / Alembic / slowapi / httpx / React 19 / PatternFly 6 / TypeScript / Ansible / Jinja2

## Global Constraints

- Jira: RHDPCD-109
- Spec: `docs/superpowers/specs/2026-07-03-api-authentication-design.md`
- Key format: `rcars_` + 64 hex chars (32 random bytes). 256-bit entropy.
- Hash algorithm: SHA-256 (stdlib `hashlib.sha256`). No bcrypt — keys are high-entropy.
- Header: `X-API-Key` (not `Authorization: Bearer` — that's reserved for SA tokens).
- Proxy verification secret: mandatory on all non-local environments.
- Role ceiling: API key's `role` column caps effective permissions, never exceeds creator's role.
- Cache TTL: 60 seconds for validated API key lookups.
- Rate limit on `/auth/token`: 5 per IP per minute via slowapi.
- All new DB methods go in `src/api/rcars/db/database.py` (existing `Database` class).
- All new Pydantic schemas go in `src/api/rcars/api/schemas.py`.
- Alembic migrations in `src/api/alembic/versions/` — next revision is `013`.
- Frontend components follow existing PatternFly 6 patterns and CSS custom properties.
- Tests: `src/api/tests/` — pytest with `unittest.mock`, no external dependencies.

---

### Task 1: Database Schema Migration + CRUD Methods

**Files:**
- Modify: `src/api/rcars/db/database.py` (SCHEMA_SQL + new methods)
- Create: `src/api/alembic/versions/013_api_keys_external_auth.py`
- Test: `src/api/tests/test_api_keys_db.py`

**Interfaces:**
- Produces:
  - `Database.create_api_key(key_hash: str, key_prefix: str, name: str, created_by: str, role: str, expires_at: datetime | None) -> int` — returns the new row `id`
  - `Database.get_api_key_by_hash(key_hash: str) -> dict | None` — returns full row dict or None. Only returns non-revoked, non-expired keys.
  - `Database.list_api_keys(active_only: bool = True) -> list[dict]` — all keys, optionally filtered
  - `Database.revoke_api_key(key_id: int) -> dict | None` — sets `revoked_at`, returns updated row
  - `Database.touch_api_key(key_id: int) -> None` — updates `last_used_at`

- [ ] **Step 1: Write the failing tests**

Create `src/api/tests/test_api_keys_db.py`:

```python
"""Tests for API key database CRUD operations."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import pytest

from rcars.db.database import Database


@pytest.fixture
def db():
    """Ephemeral test database — uses RCARS_DATABASE_URL from env (rcars_test)."""
    database = Database("postgresql://rcars:rcars@localhost:5432/rcars_test")
    database.create_schema()
    with database.pool.connection() as conn:
        conn.execute("DELETE FROM api_keys")
    yield database
    database.close()


def _generate_key() -> tuple[str, str, str]:
    """Generate a raw key, its hash, and its prefix."""
    raw = "rcars_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[:14]
    return raw, key_hash, key_prefix


class TestCreateApiKey:
    def test_creates_and_returns_id(self, db: Database):
        _, key_hash, key_prefix = _generate_key()
        key_id = db.create_api_key(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Test key",
            created_by="user@redhat.com",
            role="user",
            expires_at=None,
        )
        assert isinstance(key_id, int)
        assert key_id > 0

    def test_duplicate_hash_raises(self, db: Database):
        _, key_hash, key_prefix = _generate_key()
        db.create_api_key(key_hash, key_prefix, "Key 1", "user@redhat.com", "user", None)
        with pytest.raises(Exception):
            db.create_api_key(key_hash, key_prefix, "Key 2", "user@redhat.com", "user", None)


class TestGetApiKeyByHash:
    def test_returns_valid_key(self, db: Database):
        _, key_hash, key_prefix = _generate_key()
        db.create_api_key(key_hash, key_prefix, "Test", "user@redhat.com", "curator", None)
        result = db.get_api_key_by_hash(key_hash)
        assert result is not None
        assert result["name"] == "Test"
        assert result["created_by"] == "user@redhat.com"
        assert result["role"] == "curator"

    def test_returns_none_for_unknown_hash(self, db: Database):
        assert db.get_api_key_by_hash("nonexistent") is None

    def test_returns_none_for_revoked_key(self, db: Database):
        _, key_hash, key_prefix = _generate_key()
        key_id = db.create_api_key(key_hash, key_prefix, "Test", "user@redhat.com", "user", None)
        db.revoke_api_key(key_id)
        assert db.get_api_key_by_hash(key_hash) is None

    def test_returns_none_for_expired_key(self, db: Database):
        _, key_hash, key_prefix = _generate_key()
        expired = datetime.now(timezone.utc) - timedelta(hours=1)
        db.create_api_key(key_hash, key_prefix, "Test", "user@redhat.com", "user", expired)
        assert db.get_api_key_by_hash(key_hash) is None

    def test_returns_key_with_future_expiry(self, db: Database):
        _, key_hash, key_prefix = _generate_key()
        future = datetime.now(timezone.utc) + timedelta(hours=24)
        db.create_api_key(key_hash, key_prefix, "Test", "user@redhat.com", "user", future)
        assert db.get_api_key_by_hash(key_hash) is not None


class TestListApiKeys:
    def test_returns_all_keys(self, db: Database):
        for i in range(3):
            _, kh, kp = _generate_key()
            db.create_api_key(kh, kp, f"Key {i}", "user@redhat.com", "user", None)
        assert len(db.list_api_keys(active_only=False)) >= 3

    def test_active_only_excludes_revoked(self, db: Database):
        _, kh1, kp1 = _generate_key()
        _, kh2, kp2 = _generate_key()
        db.create_api_key(kh1, kp1, "Active", "user@redhat.com", "user", None)
        key_id = db.create_api_key(kh2, kp2, "Revoked", "user@redhat.com", "user", None)
        db.revoke_api_key(key_id)
        active = db.list_api_keys(active_only=True)
        names = [k["name"] for k in active]
        assert "Active" in names
        assert "Revoked" not in names


class TestRevokeApiKey:
    def test_sets_revoked_at(self, db: Database):
        _, key_hash, key_prefix = _generate_key()
        key_id = db.create_api_key(key_hash, key_prefix, "Test", "user@redhat.com", "user", None)
        result = db.revoke_api_key(key_id)
        assert result is not None
        assert result["revoked_at"] is not None

    def test_nonexistent_key_returns_none(self, db: Database):
        assert db.revoke_api_key(99999) is None


class TestTouchApiKey:
    def test_updates_last_used_at(self, db: Database):
        _, key_hash, key_prefix = _generate_key()
        key_id = db.create_api_key(key_hash, key_prefix, "Test", "user@redhat.com", "user", None)
        db.touch_api_key(key_id)
        key = db.get_api_key_by_hash(key_hash)
        assert key["last_used_at"] is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src/api && python -m pytest tests/test_api_keys_db.py -v
```

Expected: failures on missing methods (`AttributeError: 'Database' object has no attribute 'create_api_key'`).

- [ ] **Step 3: Update SCHEMA_SQL in database.py**

In `src/api/rcars/db/database.py`, replace the existing `api_keys` table definition in `SCHEMA_SQL`:

```python
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL,
    created_by TEXT NOT NULL,
    scopes TEXT[],
    role TEXT NOT NULL DEFAULT 'user',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_created_by ON api_keys(created_by);
```

- [ ] **Step 4: Create the Alembic migration**

Create `src/api/alembic/versions/013_api_keys_external_auth.py`:

```python
"""Extend api_keys table for external auth.

Adds key_prefix, role, expires_at columns. Makes created_by NOT NULL.

Revision ID: 013
Revises: 012
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_prefix TEXT NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'")
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ")
    op.execute("ALTER TABLE api_keys ALTER COLUMN created_by SET NOT NULL")
    op.execute("ALTER TABLE api_keys ALTER COLUMN created_by SET DEFAULT ''")
    op.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_created_by ON api_keys(created_by)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_api_keys_created_by")
    op.execute("DROP INDEX IF EXISTS idx_api_keys_hash")
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS expires_at")
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS role")
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS key_prefix")
```

- [ ] **Step 5: Add CRUD methods to Database class**

Add these methods at the end of the `Database` class in `src/api/rcars/db/database.py`:

```python
    # ── API Keys ──

    def create_api_key(
        self,
        key_hash: str,
        key_prefix: str,
        name: str,
        created_by: str,
        role: str,
        expires_at: datetime | None,
    ) -> int:
        with self.pool.connection() as conn:
            row = conn.execute(
                """INSERT INTO api_keys (key_hash, key_prefix, name, created_by, role, expires_at)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (key_hash, key_prefix, name, created_by, role, expires_at),
            ).fetchone()
            return row["id"]

    def get_api_key_by_hash(self, key_hash: str) -> dict | None:
        with self.pool.connection() as conn:
            row = conn.execute(
                """SELECT * FROM api_keys
                   WHERE key_hash = %s
                     AND revoked_at IS NULL
                     AND (expires_at IS NULL OR expires_at > NOW())""",
                (key_hash,),
            ).fetchone()
            return dict(row) if row else None

    def list_api_keys(self, active_only: bool = True) -> list[dict]:
        with self.pool.connection() as conn:
            if active_only:
                rows = conn.execute(
                    """SELECT id, key_prefix, name, created_by, role, scopes,
                              created_at, expires_at, last_used_at, revoked_at
                       FROM api_keys
                       WHERE revoked_at IS NULL
                         AND (expires_at IS NULL OR expires_at > NOW())
                       ORDER BY created_at DESC"""
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, key_prefix, name, created_by, role, scopes,
                              created_at, expires_at, last_used_at, revoked_at
                       FROM api_keys ORDER BY created_at DESC"""
                ).fetchall()
            return [dict(r) for r in rows]

    def revoke_api_key(self, key_id: int) -> dict | None:
        with self.pool.connection() as conn:
            row = conn.execute(
                """UPDATE api_keys SET revoked_at = NOW()
                   WHERE id = %s AND revoked_at IS NULL
                   RETURNING id, revoked_at""",
                (key_id,),
            ).fetchone()
            return dict(row) if row else None

    def touch_api_key(self, key_id: int) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                "UPDATE api_keys SET last_used_at = NOW() WHERE id = %s",
                (key_id,),
            )
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd src/api && python -m pytest tests/test_api_keys_db.py -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/db/database.py src/api/alembic/versions/013_api_keys_external_auth.py src/api/tests/test_api_keys_db.py
git commit -m "[RHDPCD-109] Add API key schema migration and CRUD methods"
```

---

### Task 2: Auth Middleware — API Key Validation + Proxy Secret Enforcement

**Files:**
- Modify: `src/api/rcars/api/middleware/auth.py`
- Modify: `src/api/rcars/config.py` (add `oauth_server_url` setting)
- Test: `src/api/tests/test_auth_middleware.py` (extend existing)

**Interfaces:**
- Consumes: `Database.get_api_key_by_hash(key_hash)`, `Database.touch_api_key(key_id)`
- Produces:
  - `get_current_user(request) -> str | None` — updated to check API keys (step 3) and enforce proxy secret
  - `request.state.auth_method` — set to `"api_key"`, `"sa_token"`, `"oauth_proxy"`, or `"dev_bypass"`
  - `request.state.api_key_role` — set to the key's `role` value when auth_method is `"api_key"`, else `None`

- [ ] **Step 1: Write new tests for API key auth and proxy secret enforcement**

Append to `src/api/tests/test_auth_middleware.py`:

```python
from rcars.api.middleware.auth import require_curator, require_admin


def _make_request(
    headers: dict | None = None,
    dev_user: str = "",
    sa_allowlist_str: str = "",
    proxy_verification_secret: str = "",
    db: MagicMock | None = None,
) -> MagicMock:
    """Build a mock Request with headers, settings, and optional db."""
    request = MagicMock()
    request.headers = headers or {}
    settings = MagicMock()
    settings.dev_user = dev_user
    settings.sa_allowlist_str = sa_allowlist_str
    settings.proxy_verification_secret = proxy_verification_secret
    settings.is_curator = MagicMock(return_value=False)
    settings.is_admin = MagicMock(return_value=False)
    request.app.state.settings = settings
    request.app.state.db = db or MagicMock()
    request.state = MagicMock()
    return request


class TestApiKeyAuth:
    async def test_valid_api_key_returns_user(self):
        db = MagicMock()
        db.get_api_key_by_hash.return_value = {
            "id": 1, "created_by": "user@redhat.com", "role": "user"
        }
        db.touch_api_key = MagicMock()
        request = _make_request(
            headers={"X-API-Key": "rcars_abc123"},
            db=db,
        )
        result = await get_current_user(request)
        assert result == "user@redhat.com"

    async def test_invalid_api_key_falls_through(self):
        db = MagicMock()
        db.get_api_key_by_hash.return_value = None
        request = _make_request(
            headers={"X-API-Key": "rcars_bad", "X-Forwarded-Email": "proxy@redhat.com"},
            proxy_verification_secret="secret",
            db=db,
        )
        request.headers = {
            "X-API-Key": "rcars_bad",
            "X-Forwarded-Email": "proxy@redhat.com",
            "X-Proxy-Secret": "secret",
        }
        result = await get_current_user(request)
        assert result == "proxy@redhat.com"


class TestProxySecretEnforcement:
    async def test_rejects_email_without_proxy_secret(self):
        request = _make_request(
            headers={"X-Forwarded-Email": "spoofed@redhat.com"},
            proxy_verification_secret="real-secret",
        )
        result = await get_current_user(request)
        assert result is None

    async def test_rejects_email_when_no_secret_configured_and_no_dev_user(self):
        request = _make_request(
            headers={"X-Forwarded-Email": "spoofed@redhat.com"},
            proxy_verification_secret="",
            dev_user="",
        )
        result = await get_current_user(request)
        assert result is None

    async def test_accepts_email_with_correct_proxy_secret(self):
        request = _make_request(
            headers={
                "X-Forwarded-Email": "real@redhat.com",
                "X-Proxy-Secret": "my-secret",
            },
            proxy_verification_secret="my-secret",
        )
        result = await get_current_user(request)
        assert result == "real@redhat.com"


class TestApiKeyRoleCeiling:
    async def test_user_key_blocked_from_curator_endpoint(self):
        db = MagicMock()
        db.get_api_key_by_hash.return_value = {
            "id": 1, "created_by": "curator@redhat.com", "role": "user"
        }
        db.touch_api_key = MagicMock()
        request = _make_request(headers={"X-API-Key": "rcars_abc"}, db=db)
        request.state.auth_method = None
        request.state.api_key_role = None

        # Simulate the full auth flow
        user = await get_current_user(request)
        assert user == "curator@redhat.com"

        # Now require_curator should check api_key_role
        settings = request.app.state.settings
        settings.is_curator.return_value = True
        with pytest.raises(HTTPException) as exc_info:
            await require_curator(request)
        assert exc_info.value.status_code == 403
```

- [ ] **Step 2: Run tests to verify new ones fail**

```bash
cd src/api && python -m pytest tests/test_auth_middleware.py -v -k "ApiKey or ProxySecret"
```

Expected: failures because `get_current_user` doesn't check API keys yet and `_make_request` signature changed.

- [ ] **Step 3: Update the existing `_make_request` helper**

In `src/api/tests/test_auth_middleware.py`, update the existing `_make_request` function to match the new signature (add `proxy_verification_secret` and `db` params). Update existing tests that call it to pass `proxy_verification_secret=""` explicitly. Also update any tests that rely on OAuth proxy headers working without a proxy secret — those should now set `proxy_verification_secret=""` and `dev_user="dev@example.com"` to preserve the dev bypass path instead.

- [ ] **Step 4: Implement API key validation and proxy secret enforcement in auth.py**

Replace the content of `src/api/rcars/api/middleware/auth.py`:

```python
from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import httpx
from fastapi import Request, HTTPException
from rcars.config import Settings

logger = logging.getLogger(__name__)

_K8S_TOKEN_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
_K8S_CA_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
_TOKEN_REVIEW_URL = (
    "https://kubernetes.default.svc/apis/authentication.k8s.io/v1/tokenreviews"
)

# In-memory cache: key_hash → (user_email, role, expires_at_ts, cached_at)
_api_key_cache: dict[str, tuple[str, str, float | None, float]] = {}
_CACHE_TTL = 60.0


def _parse_sa_allowlist(allowlist_str: str) -> set[str]:
    if not allowlist_str:
        return set()
    return {sa.strip() for sa in allowlist_str.split(",") if sa.strip()}


async def _validate_sa_token(token: str, allowlist: set[str]) -> str | None:
    try:
        pod_token = _K8S_TOKEN_PATH.read_text().strip()
        ca_path = str(_K8S_CA_PATH)

        async with httpx.AsyncClient(
            verify=ca_path, timeout=5.0
        ) as client:
            resp = await client.post(
                _TOKEN_REVIEW_URL,
                json={
                    "apiVersion": "authentication.k8s.io/v1",
                    "kind": "TokenReview",
                    "spec": {"token": token},
                },
                headers={
                    "Authorization": f"Bearer {pod_token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()

        data = resp.json()
        status = data.get("status", {})

        if not status.get("authenticated"):
            logger.debug("SA token not authenticated by TokenReview")
            return None

        username = status.get("user", {}).get("username", "")
        if username not in allowlist:
            logger.warning("SA identity %s not in allowlist", username)
            return None

        logger.info("SA token validated for identity: %s", username)
        return username

    except Exception:
        logger.warning("SA token validation failed", exc_info=True)
        return None


def _validate_api_key_cached(request: Request, raw_key: str) -> tuple[str, str] | None:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    now = time.monotonic()

    cached = _api_key_cache.get(key_hash)
    if cached:
        user, role, expires_ts, cached_at = cached
        if now - cached_at < _CACHE_TTL:
            if expires_ts and time.time() > expires_ts:
                _api_key_cache.pop(key_hash, None)
                return None
            return user, role
        _api_key_cache.pop(key_hash, None)

    db = request.app.state.db
    row = db.get_api_key_by_hash(key_hash)
    if not row:
        return None

    expires_ts = row["expires_at"].timestamp() if row.get("expires_at") else None
    _api_key_cache[key_hash] = (row["created_by"], row["role"], expires_ts, now)
    db.touch_api_key(row["id"])
    logger.info(
        "API key authenticated",
        extra={"auth_method": "api_key", "user": row["created_by"], "key_id": row["id"]},
    )
    return row["created_by"], row["role"]


def invalidate_api_key_cache(key_hash: str) -> None:
    _api_key_cache.pop(key_hash, None)


async def get_current_user(request: Request) -> str | None:
    settings: Settings = request.app.state.settings
    request.state.auth_method = None
    request.state.api_key_role = None

    # 1. Dev bypass
    if settings.dev_user:
        request.state.auth_method = "dev_bypass"
        return settings.dev_user

    # 2. K8s SA bearer token
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        allowlist = _parse_sa_allowlist(settings.sa_allowlist_str)
        if allowlist:
            sa_identity = await _validate_sa_token(token, allowlist)
            if sa_identity:
                request.state.auth_method = "sa_token"
                return sa_identity

    # 3. API key
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        result = _validate_api_key_cached(request, api_key)
        if result:
            user, role = result
            request.state.auth_method = "api_key"
            request.state.api_key_role = role
            return user

    # 4. OAuth proxy headers — require proxy secret
    expected_secret = settings.proxy_verification_secret
    if not expected_secret:
        logger.debug("no proxy_verification_secret configured — rejecting proxy headers")
        return None

    actual_secret = request.headers.get("X-Proxy-Secret", "")
    if actual_secret != expected_secret:
        logger.warning("proxy secret mismatch — rejecting forwarded headers")
        return None

    email = request.headers.get("X-Forwarded-Email", "")
    if not email:
        email = request.headers.get("X-Forwarded-User", "")
    if email:
        request.state.auth_method = "oauth_proxy"
    return email or None


async def require_auth(request: Request) -> str:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _check_api_key_role_ceiling(request: Request, required_role: str) -> None:
    if getattr(request.state, "auth_method", None) == "api_key":
        key_role = getattr(request.state, "api_key_role", "user")
        role_levels = {"user": 0, "curator": 1, "admin": 2}
        if role_levels.get(key_role, 0) < role_levels[required_role]:
            raise HTTPException(
                status_code=403,
                detail=f"API key role '{key_role}' insufficient — {required_role} required",
            )


async def require_curator(request: Request) -> str:
    user = await require_auth(request)
    _check_api_key_role_ceiling(request, "curator")
    settings: Settings = request.app.state.settings
    if not settings.is_curator(user) and not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Curator role required")
    return user


async def require_admin(request: Request) -> str:
    user = await require_auth(request)
    _check_api_key_role_ceiling(request, "admin")
    settings: Settings = request.app.state.settings
    if not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
```

- [ ] **Step 5: Run all auth tests**

```bash
cd src/api && python -m pytest tests/test_auth_middleware.py -v
```

Expected: all tests PASS (both existing and new). Fix any tests that relied on proxy headers working without a proxy secret — those need `dev_user` set or a proxy secret configured.

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/api/middleware/auth.py src/api/tests/test_auth_middleware.py
git commit -m "[RHDPCD-109] Add API key auth and mandatory proxy secret enforcement"
```

---

### Task 3: Auth API Endpoints — Key Management + Pydantic Schemas

**Files:**
- Modify: `src/api/rcars/api/routes/auth.py`
- Modify: `src/api/rcars/api/schemas.py`
- Test: `src/api/tests/test_auth_routes.py`

**Interfaces:**
- Consumes: `Database.create_api_key(...)`, `Database.list_api_keys(...)`, `Database.revoke_api_key(...)`, `require_auth`, `require_admin`, `invalidate_api_key_cache`
- Produces:
  - `POST /api/v1/auth/keys` — create long-lived API key (admin)
  - `GET /api/v1/auth/keys` — list API keys (admin)
  - `DELETE /api/v1/auth/keys/{key_id}` — revoke a key (admin)

- [ ] **Step 1: Add Pydantic schemas**

Append to `src/api/rcars/api/schemas.py`:

```python
# ── API Keys ───────────────────────────────────────────────────────

class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200, description="Human-readable label for the key")
    role: str = Field(default="user", pattern="^(user|curator|admin)$", description="Maximum role: user, curator, or admin")
    expires_in_days: int | None = Field(default=None, ge=1, le=365, description="Days until expiry. Null = never expires.")


class CreateApiKeyResponse(BaseModel):
    api_key: str = Field(description="Raw API key — shown exactly once, never retrievable again")
    id: int
    name: str
    role: str
    expires_at: str | None


class ApiKeyInfo(BaseModel):
    id: int
    key_prefix: str
    name: str
    created_by: str
    role: str
    created_at: str
    expires_at: str | None
    last_used_at: str | None
    is_active: bool


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyInfo]


class RevokeApiKeyResponse(BaseModel):
    id: int
    revoked_at: str
```

- [ ] **Step 2: Write failing tests**

Create `src/api/tests/test_auth_routes.py`:

```python
"""Tests for API key management endpoints."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings


@pytest.fixture
def client():
    settings = Settings(
        database_url="postgresql://rcars:rcars@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="admin@redhat.com",
        admin_emails_str="admin@redhat.com",
        curator_emails_str="admin@redhat.com,curator@redhat.com",
    )
    app = create_app(settings)
    app.state.db = MagicMock()
    app.state.redis = MagicMock()
    app.state.arq_redis = MagicMock()
    return TestClient(app)


class TestCreateApiKey:
    def test_creates_key_returns_raw(self, client):
        client.app.state.db.create_api_key.return_value = 42
        resp = client.post("/api/v1/auth/keys", json={"name": "Test key", "role": "user"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["api_key"].startswith("rcars_")
        assert len(data["api_key"]) == 70
        assert data["id"] == 42
        assert data["name"] == "Test key"

    def test_rejects_role_above_creator(self, client):
        # dev_user is admin, so admin role should work
        # Switch to a curator-only user
        client.app.state.settings.dev_user = "curator@redhat.com"
        resp = client.post("/api/v1/auth/keys", json={"name": "Overreach", "role": "admin"})
        assert resp.status_code == 403


class TestListApiKeys:
    def test_returns_keys(self, client):
        client.app.state.db.list_api_keys.return_value = [
            {"id": 1, "key_prefix": "rcars_abcd", "name": "Test", "created_by": "user@redhat.com",
             "role": "user", "created_at": datetime.now(timezone.utc), "expires_at": None,
             "last_used_at": None, "revoked_at": None}
        ]
        resp = client.get("/api/v1/auth/keys")
        assert resp.status_code == 200
        assert len(resp.json()["keys"]) == 1


class TestRevokeApiKey:
    def test_revokes_key(self, client):
        client.app.state.db.revoke_api_key.return_value = {
            "id": 1, "revoked_at": datetime.now(timezone.utc)
        }
        resp = client.delete("/api/v1/auth/keys/1")
        assert resp.status_code == 200

    def test_returns_404_for_missing_key(self, client):
        client.app.state.db.revoke_api_key.return_value = None
        resp = client.delete("/api/v1/auth/keys/999")
        assert resp.status_code == 404
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd src/api && python -m pytest tests/test_auth_routes.py -v
```

Expected: 404 errors or import failures.

- [ ] **Step 4: Implement the auth key management routes**

Replace `src/api/rcars/api/routes/auth.py`:

```python
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from rcars.api.middleware.auth import require_auth, require_admin, invalidate_api_key_cache
from rcars.api.schemas import (
    AuthMeResponse,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ApiKeyInfo,
    ApiKeyListResponse,
    RevokeApiKeyResponse,
)
from rcars.config import Settings

router = APIRouter()

_ROLE_LEVELS = {"user": 0, "curator": 1, "admin": 2}


def _user_max_role(settings: Settings, user: str) -> str:
    if settings.is_admin(user):
        return "admin"
    if settings.is_curator(user):
        return "curator"
    return "user"


def _generate_api_key() -> tuple[str, str, str]:
    raw = "rcars_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[:14]
    return raw, key_hash, key_prefix


@router.get(
    "/auth/me",
    summary="Get current user",
    description="Returns the authenticated user's email and granted roles.",
    response_model=AuthMeResponse,
)
async def auth_me(request: Request, user: str = Depends(require_auth)):
    settings: Settings = request.app.state.settings
    roles = ["user"]
    if settings.is_curator(user) or settings.is_admin(user):
        roles.append("curator")
    if settings.is_admin(user):
        roles.append("admin")
    return {"email": user, "roles": roles}


@router.post(
    "/auth/keys",
    summary="Create API key",
    description="Create a long-lived API key for programmatic access. Admin only.",
    response_model=CreateApiKeyResponse,
)
async def create_api_key(
    body: CreateApiKeyRequest, request: Request, user: str = Depends(require_admin)
):
    settings: Settings = request.app.state.settings
    creator_max = _user_max_role(settings, user)
    if _ROLE_LEVELS.get(body.role, 0) > _ROLE_LEVELS[creator_max]:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot create key with role '{body.role}' — your max role is '{creator_max}'",
        )

    raw_key, key_hash, key_prefix = _generate_api_key()
    expires_at = None
    if body.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    db = request.app.state.db
    key_id = db.create_api_key(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=body.name,
        created_by=user,
        role=body.role,
        expires_at=expires_at,
    )

    return CreateApiKeyResponse(
        api_key=raw_key,
        id=key_id,
        name=body.name,
        role=body.role,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get(
    "/auth/keys",
    summary="List API keys",
    description="List all API keys with metadata. Never returns raw keys or hashes. Admin only.",
    response_model=ApiKeyListResponse,
)
async def list_api_keys(
    request: Request,
    user: str = Depends(require_admin),
    active: bool = Query(True, description="Filter to active (non-revoked, non-expired) keys"),
):
    db = request.app.state.db
    rows = db.list_api_keys(active_only=active)
    keys = []
    now = datetime.now(timezone.utc)
    for r in rows:
        is_active = r["revoked_at"] is None and (
            r["expires_at"] is None or r["expires_at"] > now
        )
        keys.append(ApiKeyInfo(
            id=r["id"],
            key_prefix=r["key_prefix"],
            name=r["name"],
            created_by=r["created_by"],
            role=r["role"],
            created_at=r["created_at"].isoformat() if r["created_at"] else "",
            expires_at=r["expires_at"].isoformat() if r["expires_at"] else None,
            last_used_at=r["last_used_at"].isoformat() if r["last_used_at"] else None,
            is_active=is_active,
        ))
    return ApiKeyListResponse(keys=keys)


@router.delete(
    "/auth/keys/{key_id}",
    summary="Revoke API key",
    description="Soft-revoke an API key. Row preserved for audit trail. Admin only.",
    response_model=RevokeApiKeyResponse,
)
async def revoke_api_key(
    key_id: int, request: Request, user: str = Depends(require_admin)
):
    db = request.app.state.db
    result = db.revoke_api_key(key_id)
    if not result:
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    return RevokeApiKeyResponse(
        id=result["id"],
        revoked_at=result["revoked_at"].isoformat(),
    )
```

- [ ] **Step 5: Run tests**

```bash
cd src/api && python -m pytest tests/test_auth_routes.py -v
```

Expected: all PASS.

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
cd src/api && python -m pytest tests/ -v -m "not integration"
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/api/routes/auth.py src/api/rcars/api/schemas.py src/api/tests/test_auth_routes.py
git commit -m "[RHDPCD-109] Add API key management endpoints (create, list, revoke)"
```

---

### Task 4: Security Test Suite

**Files:**
- Create: `src/api/tests/test_auth_security.py`

**Interfaces:**
- Consumes: all auth middleware + key management endpoints from Tasks 2-3

- [ ] **Step 1: Write the security test suite**

Create `src/api/tests/test_auth_security.py`:

```python
"""Security test suite for RCARS API authentication.

Validates that all auth mechanisms enforce boundaries correctly:
- Unauthenticated requests get 401
- Expired/revoked keys get 401
- Spoofed proxy headers without secret get 401
- Role ceiling enforcement works
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings


@pytest.fixture
def app_no_auth():
    """App with NO dev_user — all auth enforced."""
    settings = Settings(
        database_url="postgresql://rcars:rcars@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="",
        admin_emails_str="admin@redhat.com",
        curator_emails_str="admin@redhat.com,curator@redhat.com",
        proxy_verification_secret="test-proxy-secret",
    )
    app = create_app(settings)
    app.state.db = MagicMock()
    app.state.db.get_api_key_by_hash.return_value = None
    app.state.redis = MagicMock()
    app.state.arq_redis = MagicMock()
    return app


@pytest.fixture
def client(app_no_auth):
    return TestClient(app_no_auth)


PROTECTED_ENDPOINTS = [
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/auth/keys"),
    ("POST", "/api/v1/auth/keys"),
    ("GET", "/api/v1/catalog/items"),
]


class TestUnauthenticatedAccess:
    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_returns_401_with_no_credentials(self, client, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}"


class TestExpiredApiKey:
    def test_expired_key_returns_401(self, client):
        client.app.state.db.get_api_key_by_hash.return_value = None
        resp = client.get("/api/v1/auth/me", headers={"X-API-Key": "rcars_expired"})
        assert resp.status_code == 401


class TestRevokedApiKey:
    def test_revoked_key_returns_401(self, client):
        client.app.state.db.get_api_key_by_hash.return_value = None
        resp = client.get("/api/v1/auth/me", headers={"X-API-Key": "rcars_revoked"})
        assert resp.status_code == 401


class TestSpoofedProxyHeaders:
    def test_email_without_proxy_secret_returns_401(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"X-Forwarded-Email": "spoofed@redhat.com"},
        )
        assert resp.status_code == 401

    def test_email_with_wrong_proxy_secret_returns_401(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={
                "X-Forwarded-Email": "spoofed@redhat.com",
                "X-Proxy-Secret": "wrong-secret",
            },
        )
        assert resp.status_code == 401

    def test_email_with_correct_proxy_secret_succeeds(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={
                "X-Forwarded-Email": "admin@redhat.com",
                "X-Proxy-Secret": "test-proxy-secret",
            },
        )
        assert resp.status_code == 200


class TestRoleCeiling:
    def test_user_key_cannot_access_admin_endpoint(self, client):
        client.app.state.db.get_api_key_by_hash.return_value = {
            "id": 1, "created_by": "admin@redhat.com", "role": "user"
        }
        client.app.state.db.touch_api_key = MagicMock()
        resp = client.get(
            "/api/v1/auth/keys",
            headers={"X-API-Key": "rcars_user_key"},
        )
        assert resp.status_code == 403

    def test_admin_key_can_access_admin_endpoint(self, client):
        client.app.state.db.get_api_key_by_hash.return_value = {
            "id": 2, "created_by": "admin@redhat.com", "role": "admin"
        }
        client.app.state.db.touch_api_key = MagicMock()
        client.app.state.db.list_api_keys.return_value = []
        resp = client.get(
            "/api/v1/auth/keys",
            headers={"X-API-Key": "rcars_admin_key"},
        )
        assert resp.status_code == 200
```

- [ ] **Step 2: Run the security tests**

```bash
cd src/api && python -m pytest tests/test_auth_security.py -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add src/api/tests/test_auth_security.py
git commit -m "[RHDPCD-109] Add security test suite for auth boundaries"
```

---

### Task 5: Deployment — Direct API Route + Proxy Secret Infrastructure

**Files:**
- Modify: `ansible/templates/manifests-app.yaml.j2` (add API Route)
- Modify: `ansible/templates/manifests-infra.yaml.j2` (add proxy-verification Secret)
- Modify: `ansible/vars/common.yml` (add `api_host` default)
- Modify: `src/frontend/nginx.conf` (inject secret, stop pass-through)
- Modify: `src/frontend/Containerfile` (add entrypoint for envsubst)
- Create: `src/frontend/docker-entrypoint.sh`

**Interfaces:**
- Consumes: `proxy_verification_secret` from Ansible vars (gitignored)
- Produces: externally accessible API Route at `api_host`

- [ ] **Step 1: Add the proxy-verification Secret to infra template**

In `ansible/templates/manifests-infra.yaml.j2`, add before the PostgreSQL PVC section:

```yaml
{% if rcars_proxy_verification_secret is defined and rcars_proxy_verification_secret != '' %}
---
# Proxy verification shared secret (frontend nginx + API)
apiVersion: v1
kind: Secret
metadata:
  name: {{ app_name }}-proxy-verification
  labels:
    app: {{ app_name }}
type: Opaque
stringData:
  proxy-verification-secret: "{{ rcars_proxy_verification_secret }}"
{% endif %}
```

- [ ] **Step 2: Add the direct API Route to app template**

In `ansible/templates/manifests-app.yaml.j2`, add after the existing Route (after the `insecureEdgeTerminationPolicy: Redirect` line at the end):

```yaml
{% if api_host is defined and api_host != '' %}
---
# Direct API Route (bypasses OAuth proxy — auth handled by middleware)
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ app_name }}-api
  labels:
    app: {{ app_name }}
    component: api
  annotations:
    haproxy.router.openshift.io/timeout: 180s
spec:
  host: "{{ api_host }}"
  to:
    kind: Service
    name: {{ app_name }}-api
  port:
    targetPort: {{ app_port }}
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
{% endif %}
```

- [ ] **Step 3: Add OAuthClient CRD to infra template**

In `ansible/templates/manifests-infra.yaml.j2`, add after the ServiceAccount:

```yaml
---
# OAuthClient for CLI login flow (cluster-scoped)
apiVersion: oauth.openshift.io/v1
kind: OAuthClient
metadata:
  name: rcars-cli
redirectURIs:
  - "http://127.0.0.1"
grantMethod: auto
```

- [ ] **Step 4: Update frontend nginx.conf for secret injection**

Replace `src/frontend/nginx.conf` — change the proxy_set_header line for X-Proxy-Secret:

```nginx
proxy_set_header X-Proxy-Secret "${PROXY_SECRET}";
```

(Replace the existing `proxy_set_header X-Proxy-Secret $http_x_proxy_secret;` line.)

- [ ] **Step 5: Create frontend entrypoint script**

Create `src/frontend/docker-entrypoint.sh`:

```bash
#!/bin/sh
# Read proxy secret from mounted file if available, substitute into nginx.conf
if [ -f /etc/rcars/proxy-verification-secret ]; then
    export PROXY_SECRET=$(cat /etc/rcars/proxy-verification-secret)
else
    export PROXY_SECRET=""
fi
envsubst '${PROXY_SECRET}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
```

- [ ] **Step 6: Update frontend Containerfile**

Replace `src/frontend/Containerfile`:

```dockerfile
# RCARS Frontend — multi-stage build on UBI9 Node.js 22 + nginx
FROM registry.access.redhat.com/ubi9/nodejs-22 AS builder

USER 0
WORKDIR /opt/app-root/src

COPY package*.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build

FROM registry.access.redhat.com/ubi9/nginx-122

COPY --from=builder /opt/app-root/src/dist /opt/app-root/src/dist
COPY nginx.conf /etc/nginx/nginx.conf.template
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

USER 0
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
USER 1001

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
```

- [ ] **Step 7: Add frontend secret mount to app template**

In `ansible/templates/manifests-app.yaml.j2`, in the frontend Deployment, add a volumeMount and volume for the proxy secret. Under the existing `volumeMounts:` for the frontend container, add:

```yaml
            - name: proxy-secret
              mountPath: /etc/rcars
              readOnly: true
```

Under the existing `volumes:` for the frontend deployment, add:

```yaml
{% if rcars_proxy_verification_secret is defined %}
        - name: proxy-secret
          secret:
            secretName: {{ app_name }}-proxy-verification
{% endif %}
```

- [ ] **Step 8: Update the API deployment env var**

In `ansible/templates/manifests-app.yaml.j2`, change the `RCARS_PROXY_VERIFICATION_SECRET` env var on the API deployment to reference the new dedicated secret instead of `{{ app_name }}-secrets`:

```yaml
{% if rcars_proxy_verification_secret is defined %}
            - name: RCARS_PROXY_VERIFICATION_SECRET
              valueFrom:
                secretKeyRef:
                  name: {{ app_name }}-proxy-verification
                  key: proxy-verification-secret
{% endif %}
```

- [ ] **Step 9: Add `api_host` to common.yml**

In `ansible/vars/common.yml`, add:

```yaml
# External API access (set in env-specific vars, empty = no direct API route)
# api_host: rcars-api.apps.{{ cluster_domain }}
```

- [ ] **Step 10: Commit**

```bash
git add ansible/templates/manifests-app.yaml.j2 ansible/templates/manifests-infra.yaml.j2 \
    ansible/vars/common.yml src/frontend/nginx.conf src/frontend/Containerfile \
    src/frontend/docker-entrypoint.sh
git commit -m "[RHDPCD-109] Add direct API Route, proxy secret delivery, OAuthClient CRD"
```

---

### Task 6: OAuth Login Endpoint + Helper Script

**Files:**
- Modify: `src/api/rcars/api/routes/auth.py` (add `/auth/token` endpoint)
- Modify: `src/api/rcars/api/schemas.py` (add token request/response schemas)
- Modify: `src/api/rcars/config.py` (add `oauth_server_url` setting)
- Create: `tools/rcars-login.py`
- Test: `src/api/tests/test_auth_token.py`

**Interfaces:**
- Consumes: `Database.create_api_key(...)`, OpenShift OAuth token endpoint (server-side)
- Produces:
  - `POST /api/v1/auth/token` — unauthenticated endpoint, rate-limited
  - `tools/rcars-login.py` — standalone login helper script

- [ ] **Step 1: Add schemas**

Append to `src/api/rcars/api/schemas.py`:

```python
class TokenExchangeRequest(BaseModel):
    code: str = Field(description="OAuth authorization code from callback")
    code_verifier: str = Field(description="PKCE code verifier")
    redirect_uri: str = Field(description="Redirect URI used in the authorize request")


class TokenExchangeResponse(BaseModel):
    api_key: str = Field(description="24h API key — shown once")
    expires_at: str
    user: str = Field(description="Authenticated user's email")
```

- [ ] **Step 2: Add `oauth_server_url` to Settings**

In `src/api/rcars/config.py`, in the `# Auth / roles` section:

```python
    oauth_server_url: str = ""
    oauth_client_id: str = "rcars-cli"
```

- [ ] **Step 3: Write failing test for /auth/token**

Create `src/api/tests/test_auth_token.py`:

```python
"""Tests for OAuth token exchange endpoint."""

from __future__ import annotations

from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings


@pytest.fixture
def client():
    settings = Settings(
        database_url="postgresql://rcars:rcars@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="",
        oauth_server_url="https://oauth.example.com",
        oauth_client_id="rcars-cli",
    )
    app = create_app(settings)
    app.state.db = MagicMock()
    app.state.db.create_api_key.return_value = 1
    app.state.redis = MagicMock()
    app.state.arq_redis = MagicMock()
    return TestClient(app)


class TestTokenExchange:
    @patch("rcars.api.routes.auth.httpx.AsyncClient")
    def test_valid_code_returns_api_key(self, mock_client_cls, client):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "ocp-token-123"}
        mock_resp.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        # Mock the userinfo call
        mock_user_resp = MagicMock()
        mock_user_resp.json.return_value = {
            "metadata": {"name": "user@redhat.com"},
            "fullName": "Test User",
        }
        mock_user_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_user_resp)

        resp = client.post("/api/v1/auth/token", json={
            "code": "auth-code-123",
            "code_verifier": "verifier-abc",
            "redirect_uri": "http://127.0.0.1:12345/callback",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["api_key"].startswith("rcars_")
        assert data["user"] == "user@redhat.com"

    def test_missing_oauth_server_returns_503(self, client):
        client.app.state.settings.oauth_server_url = ""
        resp = client.post("/api/v1/auth/token", json={
            "code": "code", "code_verifier": "verifier",
            "redirect_uri": "http://127.0.0.1:12345/callback",
        })
        assert resp.status_code == 503
```

- [ ] **Step 4: Run test to verify it fails**

```bash
cd src/api && python -m pytest tests/test_auth_token.py -v
```

- [ ] **Step 5: Implement the /auth/token endpoint**

Add to `src/api/rcars/api/routes/auth.py`:

```python
import httpx
from rcars.api.middleware.rate_limit import limiter

@router.post(
    "/auth/token",
    summary="Exchange OAuth code for API key",
    description="Exchanges an OpenShift OAuth authorization code for a 24h API key. "
                "Unauthenticated — this IS the login endpoint. Rate-limited to 5/min per IP.",
)
@limiter.limit("5/minute")
async def exchange_token(body: TokenExchangeRequest, request: Request):
    settings: Settings = request.app.state.settings
    if not settings.oauth_server_url:
        raise HTTPException(status_code=503, detail="OAuth login not configured")

    # Exchange auth code for access token with OpenShift
    token_url = f"{settings.oauth_server_url}/oauth/token"
    async with httpx.AsyncClient(verify=True, timeout=10.0) as client:
        token_resp = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": body.code,
                "redirect_uri": body.redirect_uri,
                "code_verifier": body.code_verifier,
                "client_id": settings.oauth_client_id,
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="OAuth code exchange failed")
        token_data = token_resp.json()

    # Get user identity from OpenShift
    access_token = token_data.get("access_token", "")
    user_url = f"{settings.oauth_server_url}/apis/user.openshift.io/v1/users/~"
    async with httpx.AsyncClient(verify=True, timeout=10.0) as client:
        user_resp = await client.get(
            user_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        user_data = user_resp.json()

    user_email = user_data.get("metadata", {}).get("name", "")
    if not user_email:
        raise HTTPException(status_code=401, detail="Could not determine user identity")

    # Create 24h API key
    raw_key, key_hash, key_prefix = _generate_api_key()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    db = request.app.state.db
    db.create_api_key(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=f"CLI session {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        created_by=user_email,
        role="user",
        expires_at=expires_at,
    )

    return TokenExchangeResponse(
        api_key=raw_key,
        expires_at=expires_at.isoformat(),
        user=user_email,
    )
```

Add the import for `TokenExchangeRequest` and `TokenExchangeResponse` to the imports at the top of the file.

- [ ] **Step 6: Run tests**

```bash
cd src/api && python -m pytest tests/test_auth_token.py -v
```

Expected: PASS.

- [ ] **Step 7: Create the helper script**

Create `tools/rcars-login.py`:

```python
#!/usr/bin/env python3
"""RCARS API login helper — authenticates via OpenShift OAuth and obtains an API key.

Usage:
    python rcars-login.py --server https://rcars-api.apps.example.com
    python rcars-login.py token     # print current key
    python rcars-login.py status    # show expiry and user

Zero external dependencies — stdlib only.
"""

import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

CREDENTIALS_DIR = Path.home() / ".config" / "rcars"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"


def _generate_pkce():
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def _load_credentials():
    if CREDENTIALS_FILE.exists():
        return json.loads(CREDENTIALS_FILE.read_text())
    return None


def _save_credentials(data):
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))
    os.chmod(CREDENTIALS_FILE, 0o600)


def _discover_oauth_server(api_server):
    """Discover the OpenShift OAuth server URL from the API's well-known endpoint."""
    url = f"{api_server}/api/v1/health/ready"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except Exception:
        pass
    # For now, prompt the user or use a known default
    return None


def cmd_login(args):
    server = args.server.rstrip("/")
    oauth_server = args.oauth_server

    if not oauth_server:
        print("Error: --oauth-server is required (e.g., https://oauth-openshift.apps.example.com)")
        sys.exit(1)

    verifier, challenge = _generate_pkce()
    oauth_state = secrets.token_hex(32)
    received_code = {"code": None}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            returned_state = params.get("state", [None])[0]
            if returned_state != oauth_state:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h2>Login failed</h2>"
                                 b"<p>State mismatch — possible CSRF attack.</p></body></html>")
                return
            received_code["code"] = params.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Login successful!</h2>"
                             b"<p>You can close this tab.</p></body></html>")

        def log_message(self, format, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), CallbackHandler)
    port = httpd.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    authorize_url = (
        f"{oauth_server}/oauth/authorize?"
        f"client_id=rcars-cli&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"response_type=code&"
        f"code_challenge={challenge}&"
        f"code_challenge_method=S256&"
        f"state={oauth_state}"
    )

    print(f"Opening browser for login...")
    print(f"If browser doesn't open, visit: {authorize_url}")
    webbrowser.open(authorize_url)

    # Wait for callback
    httpd.timeout = 120
    httpd.handle_request()
    httpd.server_close()

    if not received_code["code"]:
        print("Error: no authorization code received (state mismatch or timeout)")
        sys.exit(1)

    # Exchange code for API key
    token_url = f"{server}/api/v1/auth/token"
    payload = json.dumps({
        "code": received_code["code"],
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
    }).encode()

    req = urllib.request.Request(
        token_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error: {e.code} — {body}")
        sys.exit(1)

    _save_credentials({
        "server": server,
        "api_key": data["api_key"],
        "expires_at": data["expires_at"],
        "user": data["user"],
    })

    print(f"Logged in as {data['user']}")
    print(f"Key expires: {data['expires_at']}")
    print(f"Credentials saved to {CREDENTIALS_FILE}")


def cmd_token(args):
    creds = _load_credentials()
    if not creds:
        print("Not logged in. Run: python rcars-login.py --server URL --oauth-server URL", file=sys.stderr)
        sys.exit(1)
    print(creds["api_key"])


def cmd_status(args):
    creds = _load_credentials()
    if not creds:
        print("Not logged in.")
        sys.exit(1)
    print(f"Server:  {creds['server']}")
    print(f"User:    {creds['user']}")
    print(f"Expires: {creds['expires_at']}")


def main():
    parser = argparse.ArgumentParser(description="RCARS API login helper")
    sub = parser.add_subparsers(dest="command")

    login_p = sub.add_parser("login", help="Authenticate and obtain an API key")
    login_p.add_argument("--server", required=True, help="RCARS API server URL")
    login_p.add_argument("--oauth-server", required=True, help="OpenShift OAuth server URL")

    sub.add_parser("token", help="Print current API key")
    sub.add_parser("status", help="Show login status")

    # Default to login if --server is provided as a top-level arg
    parser.add_argument("--server", dest="top_server", help=argparse.SUPPRESS)
    parser.add_argument("--oauth-server", dest="top_oauth_server", help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args)
    elif args.command == "token":
        cmd_token(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.top_server:
        # Allow: python rcars-login.py --server URL --oauth-server URL
        args.server = args.top_server
        args.oauth_server = args.top_oauth_server
        cmd_login(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Run full test suite**

```bash
cd src/api && python -m pytest tests/ -v -m "not integration"
```

Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add src/api/rcars/api/routes/auth.py src/api/rcars/api/schemas.py \
    src/api/rcars/config.py src/api/tests/test_auth_token.py tools/rcars-login.py
git commit -m "[RHDPCD-109] Add OAuth token exchange endpoint and CLI login script"
```

---

### Task 7: Admin UI — API Key Management Panel

**Files:**
- Create: `src/frontend/src/components/admin/ApiKeysPanel.tsx`
- Modify: `src/frontend/src/services/api.ts` (add key management API calls)
- Modify: `src/frontend/src/App.tsx` (add route)
- Modify: `src/frontend/src/components/RcarsSidebar.tsx` (add nav item)

**Interfaces:**
- Consumes: `GET /api/v1/auth/keys`, `POST /api/v1/auth/keys`, `DELETE /api/v1/auth/keys/{id}`

- [ ] **Step 1: Add API client methods**

Append to the `api` object in `src/frontend/src/services/api.ts`:

```typescript
  // API Keys
  listApiKeys: (active = true) =>
    request<{ keys: Array<{ id: number; key_prefix: string; name: string; created_by: string; role: string; created_at: string; expires_at: string | null; last_used_at: string | null; is_active: boolean }> }>(
      `/auth/keys?active=${active}`
    ),
  createApiKey: (name: string, role: string, expiresInDays: number | null) =>
    request<{ api_key: string; id: number; name: string; role: string; expires_at: string | null }>(
      '/auth/keys',
      { method: 'POST', body: JSON.stringify({ name, role, expires_in_days: expiresInDays }) }
    ),
  revokeApiKey: (keyId: number) =>
    request<{ id: number; revoked_at: string }>(`/auth/keys/${keyId}`, { method: 'DELETE' }),
```

- [ ] **Step 2: Create the ApiKeysPanel component**

Create `src/frontend/src/components/admin/ApiKeysPanel.tsx`:

```tsx
import { useState, useEffect, useCallback } from 'react'
import { api } from '../../services/api'

interface ApiKeyRow {
  id: number
  key_prefix: string
  name: string
  created_by: string
  role: string
  created_at: string
  expires_at: string | null
  last_used_at: string | null
  is_active: boolean
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function expiryLabel(iso: string | null): string {
  if (!iso) return 'Never'
  const diff = new Date(iso).getTime() - Date.now()
  if (diff <= 0) return 'Expired'
  const hours = Math.floor(diff / 3600000)
  if (hours < 24) return `${hours}h left`
  const days = Math.floor(hours / 24)
  return `${days}d left`
}

export function ApiKeysPanel() {
  const [keys, setKeys] = useState<ApiKeyRow[]>([])
  const [showAll, setShowAll] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyRole, setNewKeyRole] = useState('user')
  const [newKeyExpiry, setNewKeyExpiry] = useState<string>('')
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [revokeConfirm, setRevokeConfirm] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchKeys = useCallback(() => {
    api.listApiKeys(!showAll)
      .then(data => setKeys(data.keys))
      .catch(e => setError(e.message))
  }, [showAll])

  useEffect(() => { fetchKeys() }, [fetchKeys])

  const handleCreate = async () => {
    try {
      const expiresInDays = newKeyExpiry ? parseInt(newKeyExpiry) : null
      const result = await api.createApiKey(newKeyName, newKeyRole, expiresInDays)
      setCreatedKey(result.api_key)
      setShowCreate(false)
      setNewKeyName('')
      setNewKeyRole('user')
      setNewKeyExpiry('')
      fetchKeys()
    } catch (e: any) {
      setError(e.message)
    }
  }

  const handleRevoke = async (keyId: number) => {
    try {
      await api.revokeApiKey(keyId)
      setRevokeConfirm(null)
      fetchKeys()
    } catch (e: any) {
      setError(e.message)
    }
  }

  return (
    <div className="admin-layout admin-layout--wide">
      <div className="admin-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3>API Keys</h3>
          <div style={{ display: 'flex', gap: '8px' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <input type="checkbox" checked={showAll} onChange={() => setShowAll(!showAll)} />
              Show revoked/expired
            </label>
            <button className="action-button" onClick={() => setShowCreate(true)}>Create Key</button>
          </div>
        </div>

        {error && (
          <div style={{ color: 'var(--score-red)', marginBottom: '8px', fontSize: '13px' }}>
            {error}
            <button onClick={() => setError(null)} style={{ marginLeft: '8px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>dismiss</button>
          </div>
        )}

        {createdKey && (
          <div style={{
            background: 'var(--status-bg-warning)',
            border: '1px solid var(--score-amber)',
            borderRadius: '4px',
            padding: '12px',
            marginBottom: '12px',
            fontSize: '13px',
          }}>
            <strong>API key created — copy it now, it won't be shown again:</strong>
            <div style={{ fontFamily: 'monospace', marginTop: '6px', wordBreak: 'break-all', userSelect: 'all' }}>
              {createdKey}
            </div>
            <button
              className="action-button"
              style={{ marginTop: '8px' }}
              onClick={() => { navigator.clipboard.writeText(createdKey); setCreatedKey(null) }}
            >
              Copy & Dismiss
            </button>
          </div>
        )}

        {showCreate && (
          <div style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            padding: '12px',
            marginBottom: '12px',
          }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              <input
                placeholder="Key name (e.g. Babylon integration)"
                value={newKeyName}
                onChange={e => setNewKeyName(e.target.value)}
                style={{ flex: 1, minWidth: '200px' }}
                className="filter-input"
              />
              <select className="filter-select" value={newKeyRole} onChange={e => setNewKeyRole(e.target.value)}>
                <option value="user">user</option>
                <option value="curator">curator</option>
                <option value="admin">admin</option>
              </select>
              <select className="filter-select" value={newKeyExpiry} onChange={e => setNewKeyExpiry(e.target.value)}>
                <option value="">Never expires</option>
                <option value="7">7 days</option>
                <option value="30">30 days</option>
                <option value="90">90 days</option>
                <option value="365">1 year</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="action-button" onClick={handleCreate} disabled={!newKeyName.trim()}>Create</button>
              <button className="action-button" onClick={() => setShowCreate(false)} style={{ background: 'transparent', color: 'var(--text-muted)' }}>Cancel</button>
            </div>
          </div>
        )}

        {keys.length > 0 ? (
          <table className="status-table">
            <thead>
              <tr>
                <th>Prefix</th>
                <th>Name</th>
                <th>Created by</th>
                <th>Role</th>
                <th>Created</th>
                <th>Expires</th>
                <th>Last used</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {keys.map(k => (
                <tr key={k.id} style={{ opacity: k.is_active ? 1 : 0.5 }}>
                  <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{k.key_prefix}...</td>
                  <td>{k.name}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{k.created_by}</td>
                  <td>{k.role}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{timeAgo(k.created_at)}</td>
                  <td>{expiryLabel(k.expires_at)}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{timeAgo(k.last_used_at)}</td>
                  <td>
                    <span style={{
                      color: k.is_active ? 'var(--score-green)' : 'var(--score-red)',
                      fontSize: '12px',
                    }}>
                      {k.is_active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td>
                    {k.is_active && (
                      revokeConfirm === k.id ? (
                        <span style={{ fontSize: '12px' }}>
                          Revoke?{' '}
                          <button onClick={() => handleRevoke(k.id)} style={{ color: 'var(--score-red)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>Yes</button>
                          {' / '}
                          <button onClick={() => setRevokeConfirm(null)} style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>No</button>
                        </span>
                      ) : (
                        <button
                          onClick={() => setRevokeConfirm(k.id)}
                          style={{ color: 'var(--score-red)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', fontSize: '12px' }}
                        >
                          Revoke
                        </button>
                      )
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color: 'var(--text-muted)' }}>No API keys found.</div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add the route and sidebar nav**

In `src/frontend/src/App.tsx`, add the import:

```tsx
import { ApiKeysPanel } from './components/admin/ApiKeysPanel'
```

Add the route alongside the other system routes:

```tsx
<Route path="/system/api-keys" element={<ApiKeysPanel />} />
```

In `src/frontend/src/components/RcarsSidebar.tsx`, add a nav link in the System section (after "Query History"):

```tsx
              <NavLink
                to="/system/api-keys"
                className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
              >
                API Keys
              </NavLink>
```

- [ ] **Step 4: Test in browser**

```bash
cd /Users/nstephan/devel/rcars-advisory && ./dev-services.sh start
```

Open http://localhost:3000/system/api-keys. Verify:
- Key list loads (empty state shown)
- Create form opens and creates a key (key displayed once)
- Revoke button works with confirmation
- Show revoked/expired toggle works

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/admin/ApiKeysPanel.tsx src/frontend/src/services/api.ts \
    src/frontend/src/App.tsx src/frontend/src/components/RcarsSidebar.tsx
git commit -m "[RHDPCD-109] Add API key management panel to admin UI"
```

---

### Task 8: Update OpenAPI Docs + App Description

**Files:**
- Modify: `src/api/rcars/api/app.py` (update description to mention API key auth)

**Interfaces:**
- None — documentation only

- [ ] **Step 1: Update the FastAPI app description**

In `src/api/rcars/api/app.py`, update the `description` in `create_app()`:

```python
    app = FastAPI(
        title="RCARS API",
        description=(
            "RHDP Content Advisory & Recommendation System. "
            "Matches catalog items to events, opportunities, and user queries "
            "using vector search, LLM triage, and LLM-generated rationale.\n\n"
            "**Authentication:** API keys (`X-API-Key` header), "
            "Kubernetes ServiceAccount bearer tokens, or "
            "OAuth proxy headers (web UI only).\n\n"
            "**API keys:** Obtain via `POST /api/v1/auth/token` (OAuth login) "
            "or create via `POST /api/v1/auth/keys` (admin). "
            "Roles: `user` (read-only), `curator` (curation + analysis), `admin` (full access).\n\n"
            "**Async jobs:** Long-running operations return a `job_id` immediately. "
            "Poll results via the result endpoint or stream progress via SSE."
        ),
        version="1.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )
```

- [ ] **Step 2: Add OpenAPI security scheme**

After `app.state.settings = settings` in `create_app()`, add:

```python
    from fastapi.openapi.utils import get_openapi

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key obtained via OAuth login or admin creation",
            }
        }
        schema["security"] = [{"ApiKeyAuth": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
```

This makes the Swagger UI show an "Authorize" button where users can paste their API key.

- [ ] **Step 3: Commit**

```bash
git add src/api/rcars/api/app.py
git commit -m "[RHDPCD-109] Update OpenAPI docs with API key auth scheme"
```
