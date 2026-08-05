"""Golden routing eval — real prompt assembly, real model, real validation.
Hard-asserts at temperature 0. ~40 calls ≈ cents. THE gate for model swaps."""
import os
import pathlib

import pytest
import yaml

from rcars.config import Settings
from rcars.services.chat.router import route

CASES = yaml.safe_load(
    (pathlib.Path(__file__).parent / "data" / "routing_golden.yaml").read_text())


@pytest.fixture(scope="module")
def settings():
    return Settings(database_url=os.environ.get(
        "RCARS_TEST_DATABASE_URL", "postgresql://rcars:dev@localhost:5432/rcars_test"))


@pytest.mark.llm_eval
@pytest.mark.parametrize("case", CASES, ids=[c["message"][:50] for c in CASES])
def test_routing_golden(case, settings):
    output, fallback, _ = route(case["message"], case.get("context", []), settings)
    assert not fallback, "router call failed — eval requires a live model"
    assert output.intent == case["expect"]["intent"]
    if "scope_type" in case["expect"]:
        assert output.scope is not None and output.scope.type == case["expect"]["scope_type"]
