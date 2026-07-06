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
