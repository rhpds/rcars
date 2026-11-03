"""Tests for the admin LLM provider status endpoint (RHDPCD-2226).

Covers the status payload: the active provider (LiteMaaS) and the model
used for every LLM use in RCARS.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import rcars.config as config_module
from rcars.api.app import create_app
from rcars.config import Settings

TEST_DB_URL = "postgresql://rcars:dev@localhost:5432/rcars_test"

ALL_USES = {
    "analysis",
    "triage",
    "rationale",
    "scanning",
    "chat_router",
    "chat_answer",
    "overlap",
    "osspa_analysis",
}


def _make_client(**settings_kwargs) -> TestClient:
    settings = Settings(
        database_url=TEST_DB_URL,
        redis_url="redis://localhost:6379",
        dev_user="admin@redhat.com",
        admin_emails_str="admin@redhat.com",
        **settings_kwargs,
    )
    app = create_app(settings)
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_litemaas_fetch(monkeypatch):
    """Never hit the real LiteMaaS /v1/models endpoint from tests."""
    monkeypatch.setattr(config_module, "fetch_litemaas_models", lambda settings: set())


def test_lists_model_for_every_llm_use():
    with _make_client() as client:
        resp = client.get("/api/v1/admin/llm-provider")
    assert resp.status_code == 200
    uses = {u["use"]: u["model"] for u in resp.json()["uses"]}
    assert set(uses) == ALL_USES

    sonnet = "claude-sonnet-5-5-a46b"
    haiku = "claude-haiku-5-5-a8b"
    assert uses["analysis"] == sonnet
    assert uses["rationale"] == sonnet
    assert uses["chat_answer"] == sonnet
    assert uses["osspa_analysis"] == sonnet
    assert uses["triage"] == haiku
    assert uses["scanning"] == sonnet
    assert uses["chat_router"] == haiku
    assert uses["overlap"] == haiku


def test_litemaas_active_with_models(monkeypatch):
    monkeypatch.setattr(
        config_module,
        "fetch_litemaas_models",
        lambda settings: {"claude-haiku-5-5-a8b", "claude-sonnet-5-5-a46b"},
    )
    with _make_client(
        litemaas_url="https://maas.example.com/v1", litemaas_api_key="test-key"
    ) as client:
        body = client.get("/api/v1/admin/llm-provider").json()
    assert body["litemaas_enabled"] is True
    assert body["litemaas_models"] == ["claude-haiku-5-5-a8b", "claude-sonnet-5-5-a46b"]
