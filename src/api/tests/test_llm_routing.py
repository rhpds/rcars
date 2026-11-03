"""Tests for LiteMaaS call routing (RHDPCD-2226).

Claude 5.5 on LiteMaaS rejects the temperature parameter, so the LiteMaaS
call path must retry without it and remember the model.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import rcars.config as config_module
from rcars.config import Settings

TEST_DB_URL = "postgresql://rcars:dev@localhost:5432/rcars_test"
SEEDED_MODEL = "claude-sonnet-5-5-a46b"
UNSEEDED_MODEL = "claude-test-model"
SEEDED = set(config_module._models_without_temperature)


class FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "temperature" in kwargs:
            raise RuntimeError("temperature is deprecated for this model")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )


def _settings(monkeypatch, completions) -> Settings:
    monkeypatch.setattr(
        Settings,
        "get_litemaas_client",
        lambda self: SimpleNamespace(chat=SimpleNamespace(completions=completions)),
    )
    return Settings(database_url=TEST_DB_URL)


@pytest.fixture(autouse=True)
def reset_temperature_cache():
    config_module._models_without_temperature.clear()
    config_module._models_without_temperature.update(SEEDED)
    yield
    config_module._models_without_temperature.clear()
    config_module._models_without_temperature.update(SEEDED)


def test_seeded_model_skips_temperature_on_first_call(monkeypatch):
    completions = FakeCompletions()
    config_module._call_litemaas(
        _settings(monkeypatch, completions), SEEDED_MODEL,
        [{"role": "user", "content": "hi"}], 8, 0,
    )
    assert len(completions.calls) == 1
    assert "temperature" not in completions.calls[0]


def test_retries_without_temperature_when_model_rejects_it(monkeypatch):
    completions = FakeCompletions()
    result = config_module._call_litemaas(
        _settings(monkeypatch, completions), UNSEEDED_MODEL,
        [{"role": "user", "content": "hi"}], 8, 0,
    )
    assert result.text == "ok"
    assert result.provider == "litemaas"
    assert len(completions.calls) == 2
    assert "temperature" in completions.calls[0]
    assert "temperature" not in completions.calls[1]


def test_skips_temperature_on_later_calls_for_same_model(monkeypatch):
    completions = FakeCompletions()
    settings = _settings(monkeypatch, completions)
    config_module._call_litemaas(
        settings, UNSEEDED_MODEL, [{"role": "user", "content": "hi"}], 8, 0
    )
    completions.calls.clear()
    config_module._call_litemaas(
        settings, UNSEEDED_MODEL, [{"role": "user", "content": "hi"}], 8, 0
    )
    assert len(completions.calls) == 1
    assert "temperature" not in completions.calls[0]


def test_reraises_unrelated_errors(monkeypatch):
    class BrokenCompletions:
        def create(self, **kwargs):
            raise RuntimeError("model not found")

    settings = _settings(monkeypatch, BrokenCompletions())
    with pytest.raises(RuntimeError, match="model not found"):
        config_module._call_litemaas(
            settings, UNSEEDED_MODEL, [{"role": "user", "content": "hi"}], 8, 0
        )


def test_logs_model_and_usage_on_success(monkeypatch):
    from structlog.testing import capture_logs

    completions = FakeCompletions()
    with capture_logs() as logs:
        config_module._call_litemaas(
            _settings(monkeypatch, completions), SEEDED_MODEL,
            [{"role": "user", "content": "hi"}], 8, 0,
        )
    events = [e for e in logs if e["event"] == "llm_call_complete"]
    assert len(events) == 1
    event = events[0]
    assert event["model"] == SEEDED_MODEL
    assert event["provider"] == "litemaas"
    assert event["input_tokens"] == 1
    assert event["output_tokens"] == 1
    assert event["elapsed_ms"] >= 0


def test_logs_model_on_failure(monkeypatch):
    from structlog.testing import capture_logs

    class BrokenCompletions:
        def create(self, **kwargs):
            raise RuntimeError("model not found")

    settings = _settings(monkeypatch, BrokenCompletions())
    with capture_logs() as logs, pytest.raises(RuntimeError):
        config_module._call_litemaas(
            settings, UNSEEDED_MODEL, [{"role": "user", "content": "hi"}], 8, 0
        )
    events = [e for e in logs if e["event"] == "llm_call_failed"]
    assert len(events) == 1
    assert events[0]["model"] == UNSEEDED_MODEL
    assert events[0]["log_level"] == "warning"
    assert "model not found" in events[0]["error"]
