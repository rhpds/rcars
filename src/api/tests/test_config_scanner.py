"""Tests for the config scanner (Task 3)."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from rcars.services.workload_scanner import (
    CONFIG_SYSTEM_PROMPT, read_config_code, scan_configs,
)


def test_config_prompt_requests_structured_output():
    assert "products" in CONFIG_SYSTEM_PROMPT
    assert "capabilities" in CONFIG_SYSTEM_PROMPT
    assert "category" in CONFIG_SYSTEM_PROMPT


def test_read_config_code():
    """read_config_code should read key files from a config directory."""
    with patch("pathlib.Path.is_dir", return_value=True):
        with patch("pathlib.Path.iterdir", return_value=[]):
            with patch("pathlib.Path.exists", return_value=False):
                result = read_config_code(Path("/fake/openshift-cluster"))
    # Should return empty or minimal when no files found
    assert isinstance(result, str)
