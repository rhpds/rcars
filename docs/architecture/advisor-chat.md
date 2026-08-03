---
title: Advisor Chat
description: Multi-intent chat architecture — router, handlers, evidence packs, and frontend rendering
---

# Advisor Chat

The Advisor chat is RCARS's natural-language interface for content questions. Users ask about catalog items, check performance metrics, explore content overlap, or get recommendations — all through a single conversational input. The system classifies each message into an intent, executes a deterministic handler, and returns a typed envelope that the frontend renders with structured blocks alongside a short narrative answer.

The chat layer sits beside the existing recommendation API. Direct integrators continue using `POST /advisor/query`; the chat endpoint adds multi-intent routing on top of the same underlying services. Every failure mode in the router falls back to a recommendation query, so the worst case is the behavior users already have.

## Turn Flow

Each chat message follows a fixed pipeline. The LLM makes two narrow calls (classify the intent, write a short narrative), but never sees tool results or picks a next step — the code path is determined once and executed deterministically.

```text
message + session_id
   │
   ▼
Load session context ──── advisor_sessions (last ≤5 turns:
   │                      query, intent, result IDs+names)
   ▼
Pattern check ──── deterministic; catches pasted URLs, explicit LB numbers.
   │               Narrow by design — the LLM router is the main path.
   ▼
Router LLM call ──── closed intent enum + symbolic scope + constraints
   │                 Pydantic-validated; retry once → fallback intent=recommend
   ▼
Resolve & verify ──── scope → content_ids from session turns; item refs →
   │                  catalog resolution. Failure → clarification turn with
   │                  chips. The router's claims are never trusted directly.
   ▼
Intent handler ──── fixed tool plan per intent; read-only calls to existing
   │                service/db functions
   ▼
Build evidence pack ──── one-hop graph expansion: content_similarity +
   │                     shared workloads (MAX_NEIGHBORS=15)
   ▼
Answer composer ──── deterministic scaffold + narrow per-intent LLM narrative
   │
   ▼
Envelope ──── {intent, scope_echo, answer, blocks[], suggested_followups[]}
   │
   └──▶ persist turn (advisor_sessions), complete job, SSE "complete"
```

**API endpoint:** `POST /api/v1/advisor/chat`
**arq task:** `run_chat_turn` on `arq:queue:recommend`
**Worker:** `rcars-recommend-worker` (shares the queue with direct recommendation queries)

## Intents

Five intents, defined as `IntentSpec` entries in the `INTENTS` dict (`services/chat/registry.py`):

| Intent | What it answers | Handler | Block Types | Role Gate |
|--------|----------------|---------|-------------|-----------|
| `recommend` | "Find me a lab for..." — catalog search with LLM triage | `handle_recommend` | `rec_cards` | any |
| `overlap` | "What overlaps with LB2144?" — content similarity for an item | `handle_overlap` | `item_card`, `overlap_table` | any |
| `performance` | "How is this performing?" — provisions, users, cost, sales | `handle_performance` | `performance_table` | curator or admin |
| `item_facts` | "What is the SAP HANA demo about?" — single item details | `handle_item_facts` | `item_card` | any |
| `out_of_scope` | "What's the weather?" — polite redirect | (none) | `notice` | any |

The `recommend` handler delegates to the full [recommendation pipeline](recommendation-engine.md) (`run_query`). The other three handlers run direct SQL queries against existing tables — they complete in milliseconds.

### Follow-up Chips

Each intent declares follow-up chip templates that appear below the answer. Chips are **pre-routed**: tapping one sends a request with `{intent, args, scope}` already filled in, skipping the router entirely. This makes follow-ups instant and deterministic.

For example, after a recommend turn: *Overlap for these · Performance of these · About #1*. After a performance turn: *Recommend from these · About the top item*.

### Scope Resolution

Users reference prior results with natural language — "which of these performed best?" or "tell me about the second one." The router emits a symbolic scope (`{type: "prior_results", turn: 0}` or `{type: "ordinal", turn: 0, index: 2}`), and the resolve-and-verify step maps that to concrete `content_id` values from the session history. Clarification turns (where the system asked a question) are skipped during scope resolution so stale references don't pollute the working set.

### Item Resolution

When the router names an item ("LB2144", "the SAP lab"), `resolve_item` validates the claim against the catalog using a cascade: LB-number regex → display name prefix match → keyword overlap → embedding similarity. Published Virtual CIs are preferred over unpublished base components. If no exact match is found, the system returns up to 3 guesses as clarification chips ("Did you mean...").

## Evidence Pack

The evidence pack provides bounded context for the answer narrative. Built by `build_evidence_pack()` in `services/chat/evidence.py`.

**Strategy:** One-hop expansion from anchor items (top results from the handler), capped at `MAX_NEIGHBORS=15`. Two edge types:

1. **Content similarity** — top-N neighbors by cosine similarity from `content_similarity`
2. **Shared workloads** — items sharing workload roles from `babylon_item_workloads`

The pack feeds the answer LLM's context so it can mention related items. It never adds, removes, or reorders results — an empty pack yields identical results with a blander narrative.

## Answer Composition

Every answer has two parts:

1. **Scaffold** — a deterministic first line built from handler facts. For a single-item performance query: "Introduction to AAP Self-Service Automation recorded 186 provisions over the last 3m." For multi-item: "Usage for 25 items over the last 3m; Getting started with Ansible Navigator leads with 1,515 provisions."

2. **Narrative** — a 2-4 sentence LLM response that explains the data, citing only items and numbers from the handler's facts and evidence pack. The prompt forbids inventing items or statistics.

If the narrative LLM call fails, the scaffold alone is the answer. The turn succeeds either way.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `chat_router_model` | triage_model (Haiku) | Model for intent classification |
| `chat_answer_model` | rationale_model (Sonnet) | Model for answer narrative |
| `chat_intent_roles_str` | `performance:curator` | Per-intent role gates (comma-separated `intent:role` pairs) |
| `chat_router_confidence_threshold` | `0.6` | Below this → clarification turn |
| `chat_context_turns` | `5` | Turns in the router's context window |

All settings are `RCARS_`-prefixed env vars (e.g., `RCARS_CHAT_ROUTER_MODEL`).

## Adding an Intent

1. **Registry entry** in `services/chat/registry.py`:
    - Add to `INTENT_NAMES` tuple and `IntentName` literal in `services/chat/models.py`
    - Create an args model (`BaseModel` subclass) in `models.py`
    - Write handler in `handlers.py` (signature: `async def handle_X(res, db, settings, stages, include_zt, on_progress) -> HandlerResult`)
    - Add `IntentSpec` to `INTENTS` with description, args_model, handler, block_types, followups, prompt_fragment, and ≥2 few-shot examples

2. **Golden test cases** in `tests/data/routing_golden.yaml` (marker: `llm_eval`)

3. **Frontend block renderer** (if new block type):
    - Create component in `src/frontend/src/components/advisor/blocks/`
    - Register in `blocks/registry.ts`
    - Unknown types automatically fall back to `UnknownBlock` (collapsible raw JSON)

## Backend Modules

| Module | Responsibility |
|--------|---------------|
| `services/chat/models.py` | Typed contracts: `RouterOutput`, `Envelope`, `Block`, `Chip`, per-intent args models |
| `services/chat/registry.py` | `INTENTS` dict — declarative intent definitions with prompt fragments and examples |
| `services/chat/router.py` | Pattern check, router LLM call with retry/fallback, `resolve_and_verify` ladder |
| `services/chat/handlers.py` | Four handler functions, each returning `HandlerResult` with blocks + scaffold facts |
| `services/chat/evidence.py` | `build_evidence_pack()` — bounded graph expansion for answer context |
| `services/chat/answer.py` | `build_scaffold()` + `compose_answer()` — deterministic intro + LLM narrative |
| `services/chat/orchestrator.py` | `process_turn()` — the turn pipeline: context → route → resolve → handle → compose → persist |
| `db/chat_sessions.py` | `log_chat_turn()`, `get_session_context()`, `next_turn_index()`, `session_owner_ok()` |
| `workers/chat.py` | `run_chat_turn()` arq task — thin wrapper around `process_turn()` |

## Frontend

The Advisor page (`pages/AdvisorPage.tsx`) is a two-pane layout: chat transcript on the left, evidence blocks on the right. It handles all intents in a single file.

**Block renderers** in `components/advisor/blocks/`:

| Component | Block Type | Renders |
|-----------|-----------|---------|
| `RecCardsBlock` | `rec_cards` | Recommendation cards grouped by tier |
| `OverlapTableBlock` | `overlap_table` | Similarity table with neighbor rows |
| `PerformanceTableBlock` | `performance_table` | Provisions, unique users, cost, sales impact |
| `ItemCardBlock` | `item_card` | Single item detail card with products, modules, workloads |
| `NoticeBlock` | `notice` | Out-of-scope, role redirect, or clarification labels |
| `UnknownBlock` | (fallback) | Graceful degradation with collapsible raw JSON |

The `resolveBlockRenderer()` function in `blocks/registry.ts` dispatches by block type. New backend block types never crash the frontend — they render as `UnknownBlock` until a dedicated renderer is added.

**Types** are in `components/advisor/chatTypes.ts`: `ChatEnvelope`, `ChatBlock`, `ChatChip`.

## Testing

| Tier | Files | What it covers | Marker |
|------|-------|---------------|--------|
| Unit | `test_chat_models.py`, `test_chat_answer.py`, `test_chat_registry.py` | Models, scaffold, registry completeness | (none) |
| Deterministic integration | `test_chat_turn_integration.py` | 3-turn session with scope resolution, injected fake LLM | (none) |
| DB integration | `test_chat_sessions_db.py`, `test_chat_depth.py`, `test_chat_resolve.py`, `test_chat_evidence.py`, `test_chat_handlers.py` | Session persistence, scoped search, item resolution, evidence pack, handlers | (none) |
| API | `test_chat_api.py` | Endpoint routing, ownership, validation | (none) |
| Golden routing eval | `test_chat_routing_golden.py` | 16 cases at temperature 0 — the acceptance gate for prompt/model changes | `llm_eval` |
| Live end-to-end | `test_chat_live.py` | Full turns with real LLM calls | `integration` |
| Frontend | `blocks/registry.test.ts` | Block dispatcher + fallback | vitest |
