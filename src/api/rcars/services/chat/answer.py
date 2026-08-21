"""Deterministic scaffold + narrow narrative call. Worst case: mediocre prose
next to correct data; call failure → template intro."""
from __future__ import annotations

import json

import structlog

from rcars.config import Settings, call_llm

logger = structlog.get_logger(component="chat")

_SCAFFOLDS = {
    "recommend": lambda f: (f"Found {f.get('green_count', 0)} best-fit results out of "
                            f"{f.get('result_count', 0)} candidates"
                            + (" within your prior results." if f.get("scoped") else ".")),
    "overlap": lambda f: (
        f"{f.get('anchor') or 'This item'} has {f.get('neighbor_count', 0)} "
        "related items"
        + (f" (top similarity {f['top_similarity']}%)." if f.get('top_similarity') is not None else ".")),
    "performance": lambda f: (
        "No usage data found for the selected items."
        if not f.get("has_data") else
        (f"{f['best']} had {f.get('best_provisions') or 0} provisions over the last {f.get('window') or '3m'}. "
         f"The Score column summarizes overall performance — click it to see the full details."
         if f.get("best") and f.get("single") else
         f"The table shows usage for {f.get('item_count', 0)} items over the last {f.get('window') or '3m'}. "
         f"Provisions and unique users show reach; the Score column summarizes overall performance. "
         f"Click a score to see details for that item, or Open Performance Analysis at the bottom for the full report."
    )),
    "item_facts": lambda f: (
        f"Here are the details for **{f.get('display_name', 'this item')}**"
        + (f" ({f['stage']})" if f.get("stage") else "")
        + ". The panel on the right shows the description, products, and learning objectives. "
        + (f"{f['neighbor_count']} related items are listed under Overlapping Items — click any to explore similar content."
           if f.get("neighbor_count") else "No overlapping items were found in the catalog.")
    ),
    "infrastructure": lambda f: (
        f"**{f.get('role_name', 'Unknown')}** is a {f.get('type', 'workload')} role"
        + (f" — products: {', '.join(f['products'][:3])}" if f.get("products") else "")
        + f". It is used by {f.get('item_count', 0)} catalog item(s)."
        + (" Click **Items using this** to browse them." if f.get("item_count") else "")
        + (f" {f['match_count'] - 1} other match(es) found." if f.get("match_count", 1) > 1 else "")
    ),
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
