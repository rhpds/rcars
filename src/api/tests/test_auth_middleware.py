"""Tests for RCARS auth middleware — SA token validation and dual auth paths."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import HTTPException

from rcars.api.middleware.auth import (
    _parse_sa_allowlist,
    _validate_sa_token,
    get_current_user,
    require_auth,
    require_curator,
    require_admin,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _mock_token_review_response(authenticated: bool, username: str = "") -> MagicMock:
    """Build a mock httpx response for TokenReview."""
    resp = MagicMock()
    result: dict = {"status": {"authenticated": authenticated}}
    if authenticated and username:
        result["status"]["user"] = {"username": username}
    resp.json.return_value = result
    resp.raise_for_status = MagicMock()
    return resp


def _mock_async_client(post_return=None, post_side_effect=None) -> MagicMock:
    """Build a mock httpx.AsyncClient context manager."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    if post_side_effect:
        client.post = AsyncMock(side_effect=post_side_effect)
    else:
        client.post = AsyncMock(return_value=post_return)
    return client


# ---------------------------------------------------------------------------
# _parse_sa_allowlist
# ---------------------------------------------------------------------------


class TestParseSaAllowlist:
    def test_empty_string(self):
        assert _parse_sa_allowlist("") == set()

    def test_single_entry(self):
        result = _parse_sa_allowlist("system:serviceaccount:ns:sa")
        assert result == {"system:serviceaccount:ns:sa"}

    def test_multiple_entries(self):
        result = _parse_sa_allowlist("sa1,sa2,sa3")
        assert result == {"sa1", "sa2", "sa3"}

    def test_strips_whitespace(self):
        result = _parse_sa_allowlist(" sa1 , sa2 ")
        assert result == {"sa1", "sa2"}

    def test_skips_empty_entries(self):
        result = _parse_sa_allowlist("sa1,,sa2,")
        assert result == {"sa1", "sa2"}


# ---------------------------------------------------------------------------
# _validate_sa_token
# ---------------------------------------------------------------------------


class TestValidateSaToken:
    @patch("rcars.api.middleware.auth._K8S_TOKEN_PATH")
    @patch("rcars.api.middleware.auth._K8S_CA_PATH", "/fake/ca.crt")
    @patch("rcars.api.middleware.auth.httpx.AsyncClient")
    async def test_valid_token_in_allowlist(self, mock_client_cls, mock_token_path):
        mock_token_path.read_text.return_value = "pod-token"
        mock_client = _mock_async_client(
            post_return=_mock_token_review_response(True, "system:serviceaccount:ns:sa")
        )
        mock_client_cls.return_value = mock_client

        result = await _validate_sa_token("user-token", {"system:serviceaccount:ns:sa"})
        assert result == "system:serviceaccount:ns:sa"

    @patch("rcars.api.middleware.auth._K8S_TOKEN_PATH")
    @patch("rcars.api.middleware.auth._K8S_CA_PATH", "/fake/ca.crt")
    @patch("rcars.api.middleware.auth.httpx.AsyncClient")
    async def test_valid_token_not_in_allowlist(self, mock_client_cls, mock_token_path):
        mock_token_path.read_text.return_value = "pod-token"
        mock_client = _mock_async_client(
            post_return=_mock_token_review_response(True, "system:serviceaccount:other:sa")
        )
        mock_client_cls.return_value = mock_client

        result = await _validate_sa_token("user-token", {"system:serviceaccount:ns:sa"})
        assert result is None

    @patch("rcars.api.middleware.auth._K8S_TOKEN_PATH")
    @patch("rcars.api.middleware.auth._K8S_CA_PATH", "/fake/ca.crt")
    @patch("rcars.api.middleware.auth.httpx.AsyncClient")
    async def test_unauthenticated_token(self, mock_client_cls, mock_token_path):
        mock_token_path.read_text.return_value = "pod-token"
        mock_client = _mock_async_client(
            post_return=_mock_token_review_response(False)
        )
        mock_client_cls.return_value = mock_client

        result = await _validate_sa_token("bad-token", {"system:serviceaccount:ns:sa"})
        assert result is None

    @patch("rcars.api.middleware.auth._K8S_TOKEN_PATH")
    @patch("rcars.api.middleware.auth._K8S_CA_PATH", "/fake/ca.crt")
    @patch("rcars.api.middleware.auth.httpx.AsyncClient")
    async def test_network_error_returns_none(self, mock_client_cls, mock_token_path):
        mock_token_path.read_text.return_value = "pod-token"
        mock_client = _mock_async_client(
            post_side_effect=httpx.ConnectError("connection refused")
        )
        mock_client_cls.return_value = mock_client

        result = await _validate_sa_token("token", {"system:serviceaccount:ns:sa"})
        assert result is None

    @patch("rcars.api.middleware.auth._K8S_TOKEN_PATH")
    async def test_missing_pod_token_returns_none(self, mock_token_path):
        mock_token_path.read_text.side_effect = FileNotFoundError("not found")

        result = await _validate_sa_token("token", {"system:serviceaccount:ns:sa"})
        assert result is None


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    async def test_returns_dev_user_when_set(self):
        request = _make_request(dev_user="dev@example.com")
        result = await get_current_user(request)
        assert result == "dev@example.com"

    @patch("rcars.api.middleware.auth._validate_sa_token", new_callable=AsyncMock)
    async def test_bearer_sa_valid(self, mock_validate):
        mock_validate.return_value = "system:serviceaccount:ns:sa"
        request = _make_request(
            headers={"authorization": "Bearer some-token"},
            sa_allowlist_str="system:serviceaccount:ns:sa",
        )
        result = await get_current_user(request)
        assert result == "system:serviceaccount:ns:sa"

    @patch("rcars.api.middleware.auth._validate_sa_token", new_callable=AsyncMock)
    async def test_bearer_sa_invalid_falls_through_to_email(self, mock_validate):
        mock_validate.return_value = None
        request = _make_request(
            headers={
                "authorization": "Bearer bad-token",
                "X-Forwarded-Email": "user@redhat.com",
                "X-Proxy-Secret": "secret",
            },
            sa_allowlist_str="system:serviceaccount:ns:sa",
            proxy_verification_secret="secret",
        )
        result = await get_current_user(request)
        assert result == "user@redhat.com"

    async def test_falls_through_to_email(self):
        request = _make_request(
            headers={
                "X-Forwarded-Email": "user@redhat.com",
                "X-Proxy-Secret": "secret",
            },
            proxy_verification_secret="secret",
        )
        result = await get_current_user(request)
        assert result == "user@redhat.com"

    async def test_falls_through_to_forwarded_user(self):
        request = _make_request(
            headers={
                "X-Forwarded-User": "user@redhat.com",
                "X-Proxy-Secret": "secret",
            },
            proxy_verification_secret="secret",
        )
        result = await get_current_user(request)
        assert result == "user@redhat.com"

    async def test_empty_allowlist_skips_sa_validation(self):
        """Bearer token present but allowlist empty -- SA auth is disabled."""
        request = _make_request(
            headers={
                "authorization": "Bearer some-token",
                "X-Forwarded-Email": "user@redhat.com",
                "X-Proxy-Secret": "secret",
            },
            sa_allowlist_str="",
            proxy_verification_secret="secret",
        )
        result = await get_current_user(request)
        assert result == "user@redhat.com"

    async def test_no_auth_returns_none(self):
        request = _make_request(headers={})
        result = await get_current_user(request)
        assert result is None


# ---------------------------------------------------------------------------
# require_auth
# ---------------------------------------------------------------------------


class TestRequireAuth:
    async def test_raises_401_no_user(self):
        request = _make_request(headers={})
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(request)
        assert exc_info.value.status_code == 401

    async def test_returns_user_when_present(self):
        request = _make_request(
            headers={
                "X-Forwarded-Email": "user@redhat.com",
                "X-Proxy-Secret": "secret",
            },
            proxy_verification_secret="secret",
        )
        result = await require_auth(request)
        assert result == "user@redhat.com"


# ---------------------------------------------------------------------------
# API Key Auth
# ---------------------------------------------------------------------------


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
