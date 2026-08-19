"""Declarative intent registry. Adding an intent = one entry here
(+ frontend block renderer if it introduces a new block type + golden cases)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from rcars.services.chat import handlers
from rcars.services.chat.models import (
    Chip, HelpArgs, InfrastructureArgs, ItemFactsArgs, OverlapArgs, PerformanceArgs, RecommendArgs,
)


@dataclass(frozen=True)
class IntentSpec:
    name: str
    description: str
    args_model: type
    handler: Callable | None
    block_types: tuple[str, ...]
    followups: tuple[dict, ...]
    prompt_fragment: str
    examples: tuple[dict, ...]


INTENTS: dict[str, IntentSpec] = {
    "recommend": IntentSpec(
        name="recommend",
        description="Find content for an event, audience, or topic. The answer is content to go use.",
        args_model=RecommendArgs, handler=handlers.handle_recommend,
        block_types=("rec_cards",),
        followups=({"label": "Overlap for these", "intent": "overlap", "scope_from": "results"},
                   {"label": "Performance of these", "intent": "performance", "scope_from": "results"},
                   {"label": "About #1", "intent": "item_facts", "scope_from": "ordinal1"}),
        prompt_fragment=("recommend: the user wants content suggestions (find/suggest/need a lab or "
                         "demo for X). Composite asks like 'high-usage Ansible for an EDA demo' are "
                         "recommend with constraints.performance='high_usage', NOT performance."),
        examples=(
            {"message": "I need a 2-hour OpenShift virtualization lab for platform engineers",
             "output": {"intent": "recommend", "args": {"search_query": "2-hour OpenShift virtualization lab for platform engineers"},
                        "scope": None, "item_refs": [], "confidence": 0.95, "clarify": None}},
            {"message": "high-usage Ansible content for an EDA demo",
             "output": {"intent": "recommend",
                        "args": {"search_query": "Ansible content for an EDA demo",
                                 "constraints": {"performance": "high_usage"}},
                        "scope": None, "item_refs": [], "confidence": 0.85, "clarify": None}},
        )),
    "overlap": IntentSpec(
        name="overlap",
        description="What overlaps with / is similar to a named item or prior results.",
        args_model=OverlapArgs, handler=handlers.handle_overlap,
        block_types=("item_card", "overlap_table"),
        followups=({"label": "About this item", "intent": "item_facts", "scope_from": "anchor"},
                   {"label": "Performance of these", "intent": "performance", "scope_from": "results"}),
        prompt_fragment="overlap: similarity/overlap/duplication questions about a specific item or set.",
        examples=(
            {"message": "what overlaps with LB2144?",
             "output": {"intent": "overlap", "args": {"item_ref": "LB2144"}, "scope": None,
                        "item_refs": ["LB2144"], "confidence": 0.95, "clarify": None}},
            {"message": "is the SAP lab similar to anything else we have?",
             "output": {"intent": "overlap", "args": {"item_ref": "the SAP lab"}, "scope": None,
                        "item_refs": ["the SAP lab"], "confidence": 0.8, "clarify": None}},
        )),
    "performance": IntentSpec(
        name="performance",
        description="How is X performing / which of these performed best. The answer is a fact about the portfolio (table), not content to use.",
        args_model=PerformanceArgs, handler=handlers.handle_performance,
        block_types=("performance_table",),
        followups=({"label": "Recommend from these", "intent": "recommend", "scope_from": "results"},
                   {"label": "About the top item", "intent": "item_facts", "scope_from": "ordinal1"}),
        prompt_fragment="performance: usage/provisions/cost/sales questions. Set window from any time expression.",
        examples=(
            {"message": "which of these performed best?",
             "output": {"intent": "performance", "args": {}, "scope": {"type": "prior_results", "turn": 0},
                        "item_refs": [], "confidence": 0.9, "clarify": None}},
            {"message": "how are our Ansible labs doing on provisions this year?",
             "output": {"intent": "performance", "args": {"window": "12m"}, "scope": None,
                        "item_refs": ["Ansible labs"], "confidence": 0.75, "clarify": None}},
        )),
    "item_facts": IntentSpec(
        name="item_facts",
        description="What is X / what's in it — one item's summary, modules, products, workloads.",
        args_model=ItemFactsArgs, handler=handlers.handle_item_facts,
        block_types=("item_card",),
        followups=({"label": "Overlap with this", "intent": "overlap", "scope_from": "anchor"},
                   {"label": "Performance of this", "intent": "performance", "scope_from": "anchor"}),
        prompt_fragment=("item_facts: describe one specific item (what is / tell me about / what's in). "
                         "Also use for variant-finding follow-ups ('is there one without X', "
                         "'is there a version with Y') — extract the base name from the prior turn "
                         "and put the modified name in item_refs. Do NOT use recommend for variants."),
        examples=(
            {"message": "what is the SAP HANA demo about?",
             "output": {"intent": "item_facts", "args": {"item_ref": "SAP HANA demo"}, "scope": None,
                        "item_refs": ["SAP HANA demo"], "confidence": 0.9, "clarify": None}},
            {"message": "tell me about the second one",
             "output": {"intent": "item_facts", "args": {}, "scope": {"type": "ordinal", "turn": 0, "index": 2},
                        "item_refs": [], "confidence": 0.85, "clarify": None}},
            {"message": "is there one without ARM?",
             "output": {"intent": "item_facts", "args": {"item_ref": "AWS Open Environment"}, "scope": None,
                        "item_refs": ["AWS Open Environment"], "confidence": 0.75, "clarify": None}},
        )),
    "infrastructure": IntentSpec(
        name="infrastructure",
        description="What does a workload role or base config do — its capabilities, products, and which catalog items use it.",
        args_model=InfrastructureArgs, handler=handlers.handle_infrastructure,
        block_types=("infra_detail",),
        followups=({"label": "Items using this", "intent": "recommend", "scope_from": "results"},),
        prompt_fragment=(
            "infrastructure: user asks about an automation component — a workload role or "
            "base config — by name or by what product it deploys/configures. Signal: the "
            "subject is automation (a role name like ocp4_workload_rhods, or 'workloads "
            "that deploy X', 'configs that provision Y'). NOT for product description "
            "questions ('what does OpenShift AI do?' is out_of_scope — that asks about "
            "a product, not RCARS automation). "
            "Do NOT put infrastructure names in item_refs — they are not catalog items."),
        examples=(
            {"message": "what does the ocp4_workload_amq_streams workload do?",
             "output": {"intent": "infrastructure", "args": {"search_query": "ocp4_workload_amq_streams"},
                        "scope": None, "item_refs": [], "confidence": 0.9, "clarify": None}},
            {"message": "what deploys RHOAI?",
             "output": {"intent": "infrastructure", "args": {"search_query": "RHOAI"},
                        "scope": None, "item_refs": [], "confidence": 0.9, "clarify": None}},
            {"message": "what does the ocp4_workload_openshift_ai role do?",
             "output": {"intent": "infrastructure", "args": {"search_query": "ocp4_workload_openshift_ai"},
                        "scope": None, "item_refs": [], "confidence": 0.95, "clarify": None}},
            {"message": "what automation configures an OpenShift cluster?",
             "output": {"intent": "infrastructure", "args": {"search_query": "OpenShift cluster provisioning"},
                        "scope": None, "item_refs": [], "confidence": 0.85, "clarify": None}},
        )),
    "help": IntentSpec(
        name="help",
        description="Meta-questions about what RCARS features mean or how they work.",
        args_model=HelpArgs, handler=handlers.handle_help, block_types=("notice",), followups=(),
        prompt_fragment=(
            "help: meta-questions about what an RCARS feature means or how it works — "
            "'what does performance mean', 'what can you do', 'how does scoring work', "
            "'what are workloads'. Put the feature keyword in args.topic. "
            "Do NOT use for actual queries (e.g. 'how is the SAP demo performing' is performance, not help)."),
        examples=(
            {"message": "what does performance mean?",
             "output": {"intent": "help", "args": {"topic": "performance"},
                        "scope": None, "item_refs": [], "confidence": 0.95, "clarify": None}},
            {"message": "what can you do?",
             "output": {"intent": "help", "args": {"topic": "general"},
                        "scope": None, "item_refs": [], "confidence": 0.95, "clarify": None}},
            {"message": "what are workloads?",
             "output": {"intent": "help", "args": {"topic": "workloads"},
                        "scope": None, "item_refs": [], "confidence": 0.9, "clarify": None}},
            {"message": "how does scoring work?",
             "output": {"intent": "help", "args": {"topic": "scoring"},
                        "scope": None, "item_refs": [], "confidence": 0.9, "clarify": None}},
        )),
    "out_of_scope": IntentSpec(
        name="out_of_scope",
        description="Not about RHDP content, overlap, performance, infrastructure, or item facts.",
        args_model=RecommendArgs, handler=None, block_types=("notice",), followups=(),
        prompt_fragment="out_of_scope: anything RCARS cannot answer from its catalog and metrics.",
        examples=(
            {"message": "what's the weather in Raleigh?",
             "output": {"intent": "out_of_scope", "args": {}, "scope": None, "item_refs": [],
                        "confidence": 0.95, "clarify": None}},
            {"message": "open a Jira to retire LB2144",
             "output": {"intent": "out_of_scope", "args": {}, "scope": None, "item_refs": [],
                        "confidence": 0.9, "clarify": None}},
        )),
}


def build_router_prompt(context: list[dict]) -> tuple[str, str]:
    intent_docs = "\n".join(f"- {s.prompt_fragment}" for s in INTENTS.values())
    shots = "\n".join(
        f"Message: {ex['message']}\nOutput: {json.dumps(ex['output'])}"
        for s in INTENTS.values() for ex in s.examples)
    system = (
        "You are the intent router for RCARS, the RHDP content advisory system. "
        "Classify the user's message into exactly one intent and emit ONLY a JSON object "
        "with keys: intent, args, scope, item_refs, confidence, clarify.\n"
        f"Intents:\n{intent_docs}\n"
        "Rules: scope refers to a prior turn by its number n; use type 'prior_results' for "
        "these/those/them and 'ordinal' (with 1-based index) for 'the second one'. Put free-text "
        "item mentions in item_refs — never invent catalog names. confidence is 0-1. If unsure, "
        "set clarify to {question, options} and lower confidence. "
        "When the user rejects clarification options ('none of these', 'not that') and restates "
        "what they want, keep the SAME intent as the prior turn — do NOT switch to recommend.\n"
        f"Examples:\n{shots}")
    ctx = json.dumps(context, default=str).replace('{', '{{').replace('}', '}}')
    user = ("Session context (prior turns, oldest first; 'n' is the turn number):\n"
            f"{ctx}\n\nUser message: {{message}}\n\nJSON:")
    return system, user


def followup_chips(intent: str, turn_index: int, anchor: dict | None) -> list[Chip]:
    chips = []
    for f in INTENTS[intent].followups:
        scope = None
        args: dict = {}
        if f["scope_from"] == "results":
            scope = {"type": "prior_results", "turn": turn_index}
        elif f["scope_from"] == "ordinal1":
            scope = {"type": "ordinal", "turn": turn_index, "index": 1}
        elif f["scope_from"] == "anchor" and anchor:
            args = {"item_ref": f"content_id:{anchor['content_id']}"}
        elif f["scope_from"] == "anchor":
            continue
        chips.append(Chip(label=f["label"], intent=f["intent"], args=args, scope=scope))
    return chips
