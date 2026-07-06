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
