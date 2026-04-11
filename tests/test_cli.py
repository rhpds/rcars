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


def test_scan_no_credentials(runner, monkeypatch):
    """Scan should exit with error when no Anthropic credentials."""
    monkeypatch.delenv("ANTHROPIC_VERTEX_PROJECT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(cli, ["scan"])
    assert result.exit_code == 1
    assert "credentials" in result.output.lower() or "error" in result.output.lower()


def test_scan_nothing_to_analyze(runner, monkeypatch):
    """Scan should report nothing to analyze when catalog has no Showroom URLs."""
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "test-project")
    # DB has no items with showroom_url → nothing pending
    result = runner.invoke(cli, ["scan"])
    assert result.exit_code == 0
    assert "nothing to analyze" in result.output.lower()


def test_recommend_no_credentials(runner, monkeypatch):
    """Recommend should exit with error when no Anthropic credentials."""
    monkeypatch.delenv("ANTHROPIC_VERTEX_PROJECT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(cli, ["recommend", "OpenShift demos for developers"])
    assert result.exit_code == 1
    assert "credentials" in result.output.lower() or "error" in result.output.lower()


def test_recommend_no_results(runner, monkeypatch):
    """Recommend should handle no candidates gracefully."""
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "test-project")
    import unittest.mock as mock
    from rcars.recommender.models import QueryState

    # Mock run_query to yield NO_MATCHES
    def no_matches_generator(*args, **kwargs):
        yield QueryState(phase="NO_MATCHES", candidates=[], query="test")

    with mock.patch("rcars.recommender.pipeline.run_query", side_effect=no_matches_generator):
        result = runner.invoke(cli, ["recommend", "OpenShift demos for developers"])
    assert result.exit_code == 0
    assert "no relevant matches" in result.output.lower()
