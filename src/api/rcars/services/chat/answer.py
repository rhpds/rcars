"""Deterministic scaffold + narrow narrative call. Worst case: mediocre prose
next to correct data; call failure → template intro."""
from __future__ import annotations

import json

import structlog

from rcars.config import Settings, call_llm

logger = structlog.get_logger(component="chat")

_SCAFFOLDS = {
    "recommend": lambda f: (f"Found {f.get('green_count', 0)} strong matches out of "
                            f"{f.get('result_count', 0)} candidates"
                            + (" within your prior results." if f.get("scoped") else ".")),
    "overlap": lambda f: (f"{f.get('anchor', 'This item')} has {f.get('neighbor_count', 0)} "
                          f"related items (top similarity {f.get('top_similarity')}%)."),
    "performance": lambda f: (
        f"{f.get('best', '—')} recorded {f.get('best_provisions', 0)} provisions "
        f"over the last {f.get('window', '3m')}."
        if f.get("single") else
        f"Usage for {f.get('item_count', 0)} items over the last "
        f"{f.get('window', '3m')}; {f.get('best', '—')} leads with "
        f"{f.get('best_provisions', 0)} provisions."
    ),
    "item_facts": lambda f: (f"{f.get('display_name', 'Item')} ({f.get('stage', '?')}) — "
                             f"{f.get('neighbor_count', 0)} related items in the catalog."),
}


def build_scaffold(intent: str, facts: dict) -> str:
    fn = _SCAFFOLDS.get(intent)
    return fn(facts) if fn else ""


def compose_answer(intent: str, facts: dict, evidence_pack: list[dict], question: str,
                   settings: Settings, llm_call=call_llm) -> tuple[str, dict | None]:
    scaffold = build_scaffold(intent, facts)
    prompt = (
        "Explain this data for the user in 2-4 sentences. If the data doesn't answer the "
        "question, say so. Cite items only by the names given here — never invent items, "
        "numbers, or reasons.\n\n"
        f"Facts: {json.dumps(facts, default=str)}\n"
        f"Related items (context only): {json.dumps(evidence_pack, default=str)}\n"
        f"User question: {question}")
    try:
        result = llm_call(settings, settings.chat_answer_model,
                          [{"role": "user", "content": prompt}],
                          max_tokens=600, temperature=0)
        usage = {"input": result.input_tokens, "output": result.output_tokens,
                 "provider": result.provider}
        return f"{scaffold}\n\n{result.text.strip()}", usage
    except Exception as e:
        logger.warning("chat_answer_failed_using_template", component="chat", error=str(e)[:300])
        return scaffold, None
