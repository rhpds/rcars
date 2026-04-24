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


def test_catalog_namespaces():
    """Catalog namespaces should include prod, dev, and event."""
    settings = Settings()
    expected = [
        "babylon-catalog-prod",
        "babylon-catalog-dev",
        "babylon-catalog-event",
    ]
    assert settings.catalog_namespaces == expected


def test_showroom_url_variables():
    """Should have the allowlisted Showroom URL variable names."""
    settings = Settings()
    assert "ocp4_workload_showroom_content_git_repo" in settings.showroom_url_vars
    assert "showroom_git_repo" in settings.showroom_url_vars


def test_get_anthropic_client_vertex(monkeypatch):
    """Should return AnthropicVertex when project ID is set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "test-project")
    monkeypatch.setenv("CLOUD_ML_REGION", "us-east5")
    settings = Settings()
    client = settings.get_anthropic_client()
    from anthropic import AnthropicVertex
    assert isinstance(client, AnthropicVertex)


def test_get_anthropic_client_direct(monkeypatch):
    """Should return Anthropic when API key is set."""
    monkeypatch.delenv("ANTHROPIC_VERTEX_PROJECT_ID", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    settings = Settings()
    client = settings.get_anthropic_client()
    from anthropic import Anthropic
    assert isinstance(client, Anthropic)


def test_get_anthropic_client_none(monkeypatch):
    """Should return None when no credentials."""
    monkeypatch.delenv("ANTHROPIC_VERTEX_PROJECT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings()
    client = settings.get_anthropic_client()
    assert client is None
