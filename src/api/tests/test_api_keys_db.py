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
