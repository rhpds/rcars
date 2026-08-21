import json
from rcars.services.chat import registry
from rcars.services.chat.models import INTENT_NAMES, RouterOutput


def test_registry_complete():
    assert set(registry.INTENTS) == set(INTENT_NAMES)
    for name, spec in registry.INTENTS.items():
        assert spec.description and spec.prompt_fragment
        assert len(spec.examples) >= 2
        if name != "out_of_scope":
            assert spec.handler is not None
            assert spec.block_types
        if name not in ("out_of_scope", "help"):
            assert spec.followups


def test_examples_validate_as_router_output():
    for spec in registry.INTENTS.values():
        for ex in spec.examples:
            out = RouterOutput.model_validate(ex["output"])
            assert out.intent == spec.name


def test_prompt_contains_every_intent_and_context():
    system, user = registry.build_router_prompt(
        [{"n": 0, "intent": "recommend", "query": "ansible",
          "results": [{"id": "babylon:x", "name": "X"}]}])
    for name in INTENT_NAMES:
        assert name in system
    assert "turn 0" in user.lower() or '"n": 0' in user
    assert "{message}" in user


def test_followup_chips_are_pre_routed():
    chips = registry.followup_chips("recommend", turn_index=3, anchor=None)
    assert chips and all(c.intent in INTENT_NAMES for c in chips)
    assert any(c.scope == {"type": "prior_results", "turn": 3} for c in chips)
