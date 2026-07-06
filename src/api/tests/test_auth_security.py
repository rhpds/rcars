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
