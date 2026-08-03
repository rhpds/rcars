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
    "I can help with four things: recommending RHDP content for an event or audience, "
    "showing what overlaps with an item, reporting how items are performing, and "
    "describing what's in a catalog item. Try one of those.")


def _scope_echo(output: RouterOutput, res: Resolution, message: str) -> str:
    if res.scope_turn is not None and res.scope_ids:
        return (f"{output.intent.replace('_', ' ').title()} for the "
                f"{len(res.scope_ids)} item(s) from turn {res.scope_turn + 1}'s results")
    if res.items:
        return f"{output.intent.replace('_', ' ').title()} for {res.items[0].get('display_name')}"
    if output.intent == "recommend":
        q = output.args.get("search_query") or message
        return f'Searched the full catalog for "{q[:80]}"'
    return output.intent.replace("_", " ").title()


async def process_turn(*, message: str, session_id: str, user_email: str,
                       is_admin: bool = False, stages: list[str] | None = None,
                       include_zt: bool = True, routed: dict | None = None,
                       opted_out: bool = False, db: Database, settings: Settings,
                       on_progress, llm_call=call_llm) -> dict:
    stages = stages or ["prod"]
    await on_progress({"phase": "routing", "status": "started"})
    context = chat_sessions.get_session_context(
        db.pool, session_id, max_turns=settings.chat_context_turns)

    fallback = False
    if routed is not None:  # pre-routed chip: zero router involvement
        output = RouterOutput.model_validate(routed)
        output.confidence = 1.0
    else:
        output, fallback, usage = route(message, context, settings, llm_call=llm_call)
        if usage:
            db.log_token_usage("chat_router", settings.chat_router_model,
                               usage["input"], usage["output"], query_text=message,
                               provider=usage.get("provider", "anthropic"), opted_out=opted_out)

    turn_index = chat_sessions.next_turn_index(db.pool, session_id)
    intent_for_log = output.intent
    session_results: list[dict] = []
    assessment: str | None = None
    scope_dump = output.scope.model_dump() if output.scope else None

    if output.intent == "out_of_scope":
        envelope = Envelope(intent="out_of_scope", scope_echo="Out of scope",
                            answer=OUT_OF_SCOPE_ANSWER,
                            blocks=[Block(type="notice", data={"kind": "out_of_scope"})])
    else:
        res = resolve_and_verify(output, context, db, settings, user_email)
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
                                   provider=ausage.get("provider", "anthropic"),
                                   opted_out=opted_out)
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
        intent=intent_for_log, envelope=envelope.model_dump(), scope=scope_dump,
        opted_out=opted_out)
    logger.info("chat_turn", component="chat", session_id=session_id, turn=turn_index,
                intent=intent_for_log, confidence=output.confidence,
                scope_type=output.scope.type if output.scope else None,
                fallback_used=fallback)
    return envelope.model_dump()
