"""Tests for recommender pipeline configuration."""

import os
from unittest.mock import patch

from rcars.config import Settings


def test_default_pipeline_settings():
    s = Settings()
    assert s.vector_cutoff == 0.55
    assert s.triage_model == "claude-haiku-4-5"
    assert s.triage_cutoff == 30
    assert s.rationale_model == "claude-sonnet-4-6"
    assert s.rationale_top_n == 5


def test_pipeline_settings_from_env():
    env = {
        "RCARS_VECTOR_CUTOFF": "0.7",
        "RCARS_TRIAGE_MODEL": "claude-3-5-haiku",
        "RCARS_TRIAGE_CUTOFF": "50",
        "RCARS_RATIONALE_MODEL": "claude-sonnet-4-6",
        "RCARS_RATIONALE_TOP_N": "3",
    }
    with patch.dict(os.environ, env):
        s = Settings()
    assert s.vector_cutoff == 0.7
    assert s.triage_model == "claude-3-5-haiku"
    assert s.triage_cutoff == 50
    assert s.rationale_model == "claude-sonnet-4-6"
    assert s.rationale_top_n == 3
