"""Tests for the enriched workload scanner (Task 2)."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from rcars.services.workload_scanner import WORKLOAD_SYSTEM_PROMPT, analyze_role


def test_enriched_prompt_requests_structured_output():
    """The system prompt must request the full structured output fields."""
    assert "products" in WORKLOAD_SYSTEM_PROMPT
    assert "capabilities" in WORKLOAD_SYSTEM_PROMPT
    assert "requires" in WORKLOAD_SYSTEM_PROMPT
    assert "description" in WORKLOAD_SYSTEM_PROMPT


def test_analyze_role_returns_enriched_fields():
    """analyze_role should return the enriched field set from the LLM response."""
    mock_result = MagicMock()
    mock_result.text = json.dumps({
        "product_name": "OpenShift AI",
        "description": "Installs RHOAI operator with KServe support. Default auth is KeyCloak.",
        "products": ["OpenShift AI", "KServe"],
        "capabilities": ["model-serving", "notebook-hosting"],
        "category": "ai_ml",
        "requires": ["openshift 4.14+"],
    })
    mock_result.input_tokens = 100
    mock_result.output_tokens = 50
    mock_result.provider = "test"

    with patch("rcars.config.call_llm", return_value=mock_result), \
         patch("rcars.services.workload_scanner.generate_embedding", return_value=[0.0] * 768), \
         patch("rcars.services.workload_scanner.read_role_code", return_value="some code"):
        result = analyze_role(
            "ocp4_workload_rhods", Path("/fake"), "agnosticd.ai_workloads",
            MagicMock(), "test-model", db=None,
        )

    assert result is not None
    assert result["products"] == ["OpenShift AI", "KServe"]
    assert result["capabilities"] == ["model-serving", "notebook-hosting"]
    assert result["requires"] == ["openshift 4.14+"]
