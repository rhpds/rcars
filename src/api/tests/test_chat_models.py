import pytest
from pydantic import ValidationError
from rcars.services.chat.models import (
    RouterOutput, Scope, Envelope, Block, Chip, PerformanceArgs, INTENT_NAMES,
)


def test_intent_enum_closed():
    with pytest.raises(ValidationError):
        RouterOutput(intent="write_jira", confidence=0.9)
    out = RouterOutput(intent="recommend", confidence=0.9)
    assert out.args == {} and out.item_refs == [] and out.scope is None


def test_scope_shapes():
    out = RouterOutput.model_validate({
        "intent": "performance", "args": {}, "confidence": 0.8,
        "scope": {"type": "ordinal", "turn": 2, "index": 2}, "item_refs": [], "clarify": None})
    assert out.scope.type == "ordinal" and out.scope.index == 2
    with pytest.raises(ValidationError):
        Scope(type="everything", turn=1)


def test_envelope_round_trip():
    env = Envelope(intent="overlap", scope_echo="Overlap for LB2144", answer="text",
                   blocks=[Block(type="overlap_table", data={"neighbors": []})],
                   suggested_followups=[Chip(label="performance of these", intent="performance",
                                             args={}, scope={"type": "prior_results", "turn": 0})])
    assert Envelope.model_validate(env.model_dump()) == env


def test_performance_args_window_closed():
    assert PerformanceArgs().window == "3m"
    with pytest.raises(ValidationError):
        PerformanceArgs(window="90d")


def test_intent_names_complete():
    assert INTENT_NAMES == ("recommend", "overlap", "performance", "item_facts", "infrastructure", "help", "out_of_scope")
