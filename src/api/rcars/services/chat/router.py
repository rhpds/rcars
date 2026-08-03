"""Routing: pattern check, router LLM call (Task 9), resolve & verify ladder."""
from __future__ import annotations

import json as _json
import re
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import parse_qs, urlparse

import structlog
from pydantic import ValidationError

from rcars.config import Settings, call_llm
from rcars.db.database import Database
from rcars.services.analyzer import generate_embedding
from rcars.services.chat.models import Chip, Clarify, RouterOutput
from rcars.services.recommender.pipeline import extract_urls
from rcars.services.recommender.vector_search import STOP_WORDS

logger = structlog.get_logger(component="chat")

_LB_RE = re.compile(r"\bLB(\d{3,4})\b", re.IGNORECASE)
_SIMILARITY_RE = re.compile(r"\b(similar|overlap|like this|compare|versus)\b", re.IGNORECASE)
_PERFORMANCE_RE = re.compile(r"\b(performance|provisions?|usage|sales|cost|retirement|how is .+ doing)\b", re.IGNORECASE)


def _parse_catalog_url(url: str) -> str | None:
    """Extract ci_name from a demo.redhat.com catalog URL, or None."""
    parsed = urlparse(url)
    if not parsed.hostname or not parsed.hostname.endswith("demo.redhat.com"):
        return None
    item = parse_qs(parsed.query).get("item", [None])[0]
    if not item:
        return None
    # ?item=namespace/ci_name — strip the namespace
    return item.split("/", 1)[-1] if "/" in item else item


def pattern_check(message: str) -> RouterOutput | None:
    """Deterministic pre-router. Narrow by design — the LLM router is the main path."""
    urls, remaining = extract_urls(message)
    if urls:
        ci_name = _parse_catalog_url(urls[0])
        if ci_name:
            ref = f"content_id:babylon:{ci_name}"
            if _SIMILARITY_RE.search(remaining):
                return RouterOutput(intent="overlap", args={"item_ref": ref},
                                    item_refs=[ref], confidence=1.0)
            if _PERFORMANCE_RE.search(remaining):
                return RouterOutput(intent="performance",
                                    args={"item_refs": [ref]},
                                    item_refs=[ref], confidence=1.0)
            return RouterOutput(intent="item_facts", args={"item_ref": ref},
                                item_refs=[ref], confidence=1.0)
        return RouterOutput(intent="recommend", args={"search_query": message}, confidence=1.0)
    m = _LB_RE.search(message)
    if m and len(message.split()) <= 4 and "?" not in message:
        ref = m.group(0).upper()
        return RouterOutput(intent="item_facts", args={"item_ref": ref},
                            item_refs=[ref], confidence=1.0)
    return None


def resolve_item(ref: str, db: Database, stages: list[str] | None = None,
                 embed_fn=None) -> dict:
    """Catalog resolution: LB regex → name keyword overlap → embedding guesses.
    The router's belief that an item exists is never trusted."""
    stages = stages or ["prod"]
    if ref.startswith("content_id:"):  # pre-routed chip fast-path
        item = db.get_babylon_item(ref.removeprefix("content_id:"))
        if item:
            return {"item": item}
    m = _LB_RE.search(ref)
    if m:
        item = db.find_catalog_item_by_display_name_prefix(f"LB{m.group(1)}%", stages=stages)
        if item:
            return {"item": item}
    words = {w.lower() for w in re.findall(r"[a-zA-Z]{3,}", ref)} - STOP_WORDS
    if len(words) >= 2:
        item = db.find_catalog_item_by_keyword_overlap(words, stages=stages, min_overlap=3)
        if item:
            return {"item": item}
    embed = embed_fn or generate_embedding
    guesses = db.search_embeddings(embed(ref, prefix="search_query"),
                                   limit=3, stages=stages)
    return {"guesses": guesses}


@dataclass
class Resolution:
    kind: Literal["execute", "clarify", "redirect"]
    output: RouterOutput
    scope_ids: list[str] = field(default_factory=list)
    scope_turn: int | None = None
    items: list[dict] = field(default_factory=list)
    clarify: Clarify | None = None
    chips: list[Chip] = field(default_factory=list)
    redirect_message: str = ""


def _result_turns(context: list[dict]) -> list[dict]:
    """Turns that produced results — clarification turns are skipped when resolving."""
    return [t for t in context if t.get("results") and t.get("intent") != "clarify"]


def _turn_chips(context: list[dict], output: RouterOutput) -> list[Chip]:
    return [Chip(label=f'Use results from "{t["query"][:40]}" ({len(t["results"])} items)',
                 intent=output.intent, args=output.args,
                 scope={"type": "prior_results", "turn": t["n"]})
            for t in _result_turns(context)[-3:]]


def resolve_and_verify(output: RouterOutput, context: list[dict], db: Database,
                       settings: Settings, user_email: str) -> Resolution:
    # Ladder 2: symbolic scope → content_ids from session turns
    scope_ids: list[str] = []
    scope_turn: int | None = None
    items: list[dict] = []
    if output.scope is not None:
        turn = next((t for t in _result_turns(context) if t["n"] == output.scope.turn), None)
        if turn is None:
            return Resolution(kind="clarify", output=output,
                              clarify=Clarify(question="Which results should I use?"),
                              chips=_turn_chips(context, output))
        scope_turn = turn["n"]
        if output.scope.type == "ordinal":
            idx = (output.scope.index or 1) - 1
            if not (0 <= idx < len(turn["results"])):
                return Resolution(kind="clarify", output=output,
                                  clarify=Clarify(question=f"That turn has {len(turn['results'])} items — which one?"),
                                  chips=[Chip(label=r["name"], intent=output.intent, args=output.args,
                                              scope={"type": "ordinal", "turn": turn["n"], "index": i + 1})
                                         for i, r in enumerate(turn["results"][:5])])
            picked = turn["results"][idx]
            item = db.get_babylon_item(picked["id"]) or {"content_id": picked["id"],
                                                         "display_name": picked["name"]}
            items = [item]
            scope_ids = [picked["id"]]
        else:
            scope_ids = [r["id"] for r in turn["results"]]

    # Ladder 3: item refs → catalog resolution ("did you mean…" on miss)
    for ref in output.item_refs:
        resolved = resolve_item(ref, db)
        if "item" in resolved:
            items.append(resolved["item"])
        else:
            chips = [Chip(label=g.get("display_name", g["content_id"]), intent=output.intent,
                          args={**output.args, "item_ref": f"content_id:{g['content_id']}"})
                     for g in resolved["guesses"][:3]]
            return Resolution(kind="clarify", output=output,
                              clarify=Clarify(question=f'I couldn\'t find "{ref}". Did you mean:'),
                              chips=chips)

    # Ladder 4: confidence gate → router's own clarify question
    if output.confidence < settings.chat_router_confidence_threshold and output.clarify:
        chips = [Chip(label=opt, intent=output.intent, args={**output.args, "search_query": opt})
                 for opt in output.clarify.options[:4]]
        return Resolution(kind="clarify", output=output, clarify=output.clarify, chips=chips)

    # Ladder 5: role check on the resolved intent (demand is logged before opening up)
    required = settings.chat_intent_roles.get(output.intent, "any")
    allowed = (required == "any"
               or (required == "curator" and (settings.is_curator(user_email) or settings.is_admin(user_email)))
               or (required == "admin" and settings.is_admin(user_email)))
    if not allowed:
        logger.info("chat_role_redirect", component="chat", intent=output.intent,
                    required_role=required, user=user_email)
        return Resolution(kind="redirect", output=output,
                          redirect_message=(f"Performance and usage questions are currently "
                                            f"available to {required}s. Ask a curator, or use the "
                                            f"Browse page for catalog details."))

    return Resolution(kind="execute", output=output, scope_ids=scope_ids,
                      scope_turn=scope_turn, items=items)


def _extract_json(text: str) -> dict:
    """Strip code fences / leading prose, then parse. Raises on failure."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in router output")
    return _json.loads(text[start:text.rfind("}") + 1])


def route(message: str, context: list[dict], settings: Settings,
          llm_call=call_llm) -> tuple[RouterOutput, bool, dict | None]:
    patt = pattern_check(message)
    if patt is not None:
        return patt, False, None

    from rcars.services.chat.registry import build_router_prompt
    system, user_template = build_router_prompt(context)
    usage: dict | None = None
    for attempt in (1, 2):
        try:
            result = llm_call(settings, settings.chat_router_model,
                              [{"role": "user", "content": user_template.format(message=message)}],
                              max_tokens=500, temperature=0, system=system)
            usage = {"input": result.input_tokens, "output": result.output_tokens,
                     "provider": result.provider}
            return RouterOutput.model_validate(_extract_json(result.text)), False, usage
        except (ValidationError, ValueError, _json.JSONDecodeError, Exception) as e:
            logger.warning("chat_router_attempt_failed", component="chat",
                           attempt=attempt, error=str(e)[:300])
    return (RouterOutput(intent="recommend", args={"search_query": message}, confidence=0.0),
            True, usage)
