"""Typed contracts for the chat layer. All LLM output is validated here."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

INTENT_NAMES = ("recommend", "overlap", "performance", "item_facts", "out_of_scope")
IntentName = Literal["recommend", "overlap", "performance", "item_facts", "out_of_scope"]


class Scope(BaseModel):
    type: Literal["prior_results", "ordinal"]
    turn: int
    index: int | None = None  # 1-based position, ordinal only


class Clarify(BaseModel):
    question: str
    options: list[str] = Field(default_factory=list)


class RouterOutput(BaseModel):
    intent: IntentName
    args: dict = Field(default_factory=dict)
    scope: Scope | None = None
    item_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    clarify: Clarify | None = None


class Chip(BaseModel):
    """Pre-routed follow-up: tapping it skips the router entirely."""
    label: str
    intent: str
    args: dict = Field(default_factory=dict)
    scope: dict | None = None


class Block(BaseModel):
    type: str  # rec_cards | overlap_table | performance_table | item_card | notice
    data: dict = Field(default_factory=dict)


class Envelope(BaseModel):
    intent: str
    scope_echo: str = ""
    answer: str = ""
    blocks: list[Block] = Field(default_factory=list)
    suggested_followups: list[Chip] = Field(default_factory=list)


# ── Per-intent args (router "args" payload, validated by handlers) ──

class RecommendArgs(BaseModel):
    search_query: str = ""
    constraints: dict = Field(default_factory=dict)  # duration, format_hint, performance, stages


class OverlapArgs(BaseModel):
    item_ref: str | None = None


class PerformanceArgs(BaseModel):
    item_refs: list[str] = Field(default_factory=list)
    window: Literal["3m", "6m", "9m", "12m"] = "3m"
    retirement_flavored: bool = False


class ItemFactsArgs(BaseModel):
    item_ref: str | None = None
