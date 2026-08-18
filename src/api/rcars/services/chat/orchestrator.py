"""The chat turn flow. LLM client injectable for the deterministic test tier."""
from __future__ import annotations

import asyncio

import structlog

from rcars.config import Settings, call_llm
from rcars.db import chat_sessions
from rcars.db.database import Database
from rcars.services.chat.answer import compose_answer
from rcars.services.chat.evidence import build_evidence_pack
from rcars.services.chat.models import Block, Chip, Envelope, RouterOutput
from rcars.services.chat.registry import INTENTS, followup_chips
from rcars.services.chat.router import Resolution, resolve_and_verify, route

logger = structlog.get_logger(component="chat")

OUT_OF_SCOPE_ANSWER = (
    "I can help with five things: recommending RHDP content for an event or audience, "
    "showing what overlaps with an item, reporting how items are performing, "
    "describing what's in a catalog item, and explaining what a workload or base config does. "
    "Try one of those.")

_HELP_TOPICS = {
    "general": (
        "I'm the RCARS advisor — I help you find, understand, and evaluate RHDP catalog content. "
        "I can: **recommend** content for an event or audience, show **overlap** between items, "
        "report **performance** across usage, cost, and sales, describe what's in a **catalog item**, "
        "and explain what **infrastructure & automation** components do. "
        "Just ask a question about any of these."),
    "recommend": (
        "**Recommend** searches the RHDP catalog to find the best content for your situation. "
        "Tell me about your event, audience, or topic and I'll find matching labs, demos, and "
        "workshops. Results are ranked by relevance and can be filtered by stage (prod/dev/event). "
        "Example: \"I need a 2-hour OpenShift virtualization lab for platform engineers\""),
    "performance": (
        "**Performance** tracks how catalog items are doing across four factors: "
        "usage (provisions), pipeline influence (opportunities touched), closed sales, and cost efficiency. "
        "Each item gets a score from 0-80 based on percentile ranks among peers. "
        "Strong >= 55, Moderate >= 35, Low < 35. "
        "You can ask about a specific item, a set of items, or filter by time window (3m/6m/9m/12m). "
        "Example: \"How is our OpenShift Virtualization content performing?\""),
    "overlap": (
        "**Overlap** identifies catalog items that cover similar content — same products, topics, "
        "or learning objectives. This helps spot duplication and consolidation opportunities. "
        "I compare items using shared products, shared topics, and an LLM assessment of their similarity. "
        "Example: \"What overlaps with LB2144?\""),
    "item_facts": (
        "**Catalog Items** — I can describe what's in a specific lab, demo, or workshop: "
        "its summary, learning objectives, and related items in the catalog. "
        "You can ask by name or refer to items from a previous search. "
        "Example: \"What is the OpenShift Virtualization workshop about?\""),
    "infrastructure": (
        "**Infrastructure & Automation** — these are the building blocks that catalog items "
        "are assembled from. Workload roles are Ansible automation (from AgnosticD v2 collections) "
        "that install specific products onto a cluster — things like OpenShift AI, "
        "Advanced Cluster Security, or OpenShift Virtualization. Base configs provision the "
        "underlying platform (an OpenShift cluster, cloud VMs, etc.). "
        "You can ask what a component does, what installs a given product, or which catalog "
        "items use a particular workload or config. "
        "Example: \"What does the RHODS workload do?\" or \"What installs OpenShift AI?\""),
    "workload": None,  # merged into infrastructure
    "scoring": (
        "**Scoring** rates each catalog item on a 0-80 scale across four factors: "
        "Usage/provisions (max 25), Pipeline/opportunities touched (max 15), "
        "Closed sales (max 25), and Cost efficiency/ROI (max 15). "
        "Points are awarded by percentile rank among items with non-zero activity. "
        "Items with zero activity in a factor get 0 points for that factor. "
        "Thresholds: Strong >= 55, Moderate >= 35, Low < 35."),
    "sales_impact": (
        "**Sales impact** shows whether deployments of this item correlate with closed sales. "
        "It's derived from Salesforce opportunity data — we look at which catalog items were "
        "provisioned in the trailing year and whether those accounts had closed-won deals. "
        "**High** means this item is in the top tier for sales correlation across the catalog. "
        "**Moderate** means above average. No badge means low or no measurable correlation. "
        "This is a correlation signal, not a guarantee — it tells you this item tends to "
        "show up in accounts that buy, not that using it causes the sale."),
}


def _help_answer(topic: str) -> str:
    t = topic.lower().strip().replace(" ", "_").replace("-", "_")
    if t in _HELP_TOPICS and _HELP_TOPICS[t] is not None:
        return _HELP_TOPICS[t]
    for key in ("workload", "infrastructure", "performance", "overlap",
                "recommend", "item_facts", "scoring", "sales_impact"):
        if key in t or t in key:
            answer = _HELP_TOPICS[key]
            if answer is None:
                answer = _HELP_TOPICS["infrastructure"]
            return answer
    return _HELP_TOPICS["general"]


def _scope_echo(output: RouterOutput, res: Resolution, message: str) -> str:
    if res.scope_turn is not None and res.scope_ids:
        return (f"{output.intent.replace('_', ' ').title()} for the "
                f"{len(res.scope_ids)} item(s) from turn {res.scope_turn + 1}'s results")
    if res.items:
        return f"{output.intent.replace('_', ' ').title()} for {res.items[0].get('display_name')}"
    if output.intent == "recommend":
        return f'Searched the full catalog for "{message[:80]}"'
    return output.intent.replace("_", " ").title()


async def process_turn(*, message: str, session_id: str, user_email: str,
                       is_admin: bool = False, stages: list[str] | None = None,
                       include_zt: bool = True, routed: dict | None = None,
                       db: Database, settings: Settings,
                       on_progress, llm_call=call_llm) -> dict:
    stages = stages or ["prod"]
    await on_progress({"phase": "routing", "status": "started"})
    context = chat_sessions.get_session_context(
        db.pool, session_id, max_turns=settings.chat_context_turns)

    fallback = False
    if routed is not None:  # pre-routed chip: zero router involvement
        output = RouterOutput.model_validate(routed)
        output.confidence = 1.0
        # Clarify chips carry item_ref in args — promote to item_refs for resolution
        if not output.item_refs and output.args.get("item_ref"):
            output.item_refs = [output.args["item_ref"]]
    else:
        output, fallback, usage = await asyncio.to_thread(
            route, message, context, settings, llm_call=llm_call)
        if usage:
            db.log_token_usage("chat_router", settings.chat_router_model,
                               usage["input"], usage["output"], query_text=message,
                               provider=usage.get("provider", "anthropic"))

    turn_index = chat_sessions.next_turn_index(db.pool, session_id)
    intent_for_log = output.intent
    session_results: list[dict] = []
    assessment: str | None = None
    scope_dump = output.scope.model_dump() if output.scope else None

    if output.intent == "out_of_scope":
        envelope = Envelope(intent="out_of_scope", scope_echo="Out of scope",
                            answer=OUT_OF_SCOPE_ANSWER,
                            blocks=[Block(type="notice", data={"kind": "out_of_scope"})])
    elif output.intent == "help":
        topic = output.args.get("topic", "")
        answer = _help_answer(topic)
        envelope = Envelope(intent="help", scope_echo="Help",
                            answer=answer,
                            blocks=[Block(type="notice", data={"kind": "help"})])
    else:
        res = await resolve_and_verify(output, context, db, settings, user_email,
                                       message=message)
        if res.kind == "clarify":
            intent_for_log = "clarify"
            envelope = Envelope(intent="clarify", scope_echo="Needs clarification",
                                answer=res.clarify.question if res.clarify else "Which did you mean?",
                                blocks=[Block(type="notice", data={"kind": "clarify"})],
                                suggested_followups=res.chips)
        elif res.kind == "redirect":
            envelope = Envelope(intent=output.intent, scope_echo="Role-gated",
                                answer=res.redirect_message,
                                blocks=[Block(type="notice", data={"kind": "role_redirect"})])
        else:
            await on_progress({"phase": "fetching", "status": "started", "intent": output.intent})
            handler = INTENTS[output.intent].handler
            hres = await handler(res, db, settings, stages, include_zt, on_progress)
            pack = build_evidence_pack(db, hres.anchor_ids)
            await on_progress({"phase": "composing", "status": "started"})
            answer, ausage = await asyncio.to_thread(
                compose_answer, output.intent, hres.scaffold_facts, pack, message,
                settings, llm_call)
            if ausage:
                db.log_token_usage("chat_answer", settings.chat_answer_model,
                                   ausage["input"], ausage["output"], query_text=message,
                                   provider=ausage.get("provider", "anthropic"))
            anchor = (hres.session_results or [None])[0]
            envelope = Envelope(intent=output.intent,
                                scope_echo=_scope_echo(output, res, message),
                                answer=answer, blocks=hres.blocks,
                                suggested_followups=followup_chips(
                                    output.intent, turn_index, anchor))
            session_results = hres.session_results
            assessment = hres.scaffold_facts.get("assessment")

    chat_sessions.log_chat_turn(
        db.pool, session_id=session_id, turn_index=turn_index, user_email=user_email,
        query_text=message, results=session_results or None,
        overall_assessment=assessment or envelope.answer[:500],
        intent=intent_for_log, envelope=envelope.model_dump(), scope=scope_dump)
    logger.info("chat_turn", component="chat", session_id=session_id, turn=turn_index,
                intent=intent_for_log, confidence=output.confidence,
                scope_type=output.scope.type if output.scope else None,
                fallback_used=fallback)
    return envelope.model_dump()
