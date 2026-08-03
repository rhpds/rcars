---
title: Advisor Chat
description: Multi-intent chat architecture — router, handlers, evidence packs, and frontend rendering
---

# Advisor Chat — Multi-Intent Architecture

The Advisor evolved from a recommendation-only interface into a multi-intent "chat with RCARS" — natural-language questions over RCARS capabilities, grounded in RCARS data.

**Design spec:** [`docs/superpowers/specs/2026-08-02-advisor-chat-design.md`](../superpowers/specs/2026-08-02-advisor-chat-design.md)

## Core Principles

- **LLM has no write path into results.** Router output selects which deterministic code path runs; tool results come from SQL/vector queries over existing tables; the answer LLM writes prose next to data it cannot alter.
- **Direct API endpoints remain first-class.** The chat layer sits beside the existing API. External integrators keep hitting `/advisor/query` and never touch the router.
- **Worst case is today's product.** Every router failure mode falls back to the current recommend behavior or an explicit clarification.
- **Extensible by registry.** Adding an intent = one registry entry (`IntentSpec` with args model, handler, block types, chips, prompt fragment, golden examples). No router rewrite, no frontend redesign.

## Turn Flow

```text
message + session_id
   │
   ▼
Load session context ──── advisor_sessions (last ≤ chat_context_turns turns:
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

## Intent Registry

Five intents in v1, defined in `src/api/rcars/services/chat/registry.py` as `IntentSpec` entries in the `INTENTS` dict:

| Intent | Description | Handler | Block Types | Role Gate |
|--------|-------------|---------|-------------|-----------|
| `recommend` | Vector search + LLM triage for catalog recommendations | `handle_recommend` | `rec_cards` | any authenticated user |
| `overlap` | Content overlap analysis between items | `handle_overlap` | `item_card`, `overlap_table` | any authenticated user |
| `performance` | Performance metrics (provisions, pipeline, sales, cost) | `handle_performance` | `performance_table` | curator or admin (configurable) |
| `item_facts` | Detailed information about a specific catalog item | `handle_item_facts` | `item_card` | any authenticated user |
| `out_of_scope` | Polite redirect for questions RCARS cannot answer | (no handler) | `notice` | any authenticated user |

Each `IntentSpec` contains:
- `name` — intent identifier
- `description` — human-readable summary
- `args_model` — Pydantic model for argument validation (e.g., `RecommendArgs`, `OverlapArgs`)
- `handler` — async function reference (signature: `async def handle_X(args, ctx, log) -> HandlerResult`)
- `block_types` — tuple of block type strings produced by this intent
- `followups` — tuple of follow-up chip templates (scope-from presets: `results`, `ordinal1`, `anchor`)
- `prompt_fragment` — intent description for the router prompt
- `examples` — tuple of few-shot examples (message + expected router output)

## Evidence Pack

The evidence pack is a bounded graph expansion that provides context for the answer narrative. Built by `build_evidence_pack()` in `src/api/rcars/services/chat/evidence.py`.

**Strategy:** One-hop expansion from anchor items (result set from the handler), capped at `MAX_NEIGHBORS=15` total. Two edge types:

1. **Content similarity** — top-N neighbors by cosine similarity score from `content_similarity` table
2. **Shared workloads** — items sharing workload roles from `babylon_item_workloads`

Each edge includes: neighbor `content_id`, display name, stage, products, provisions (when available), and relationship type or workload role. The pack is serialized as JSON and passed to the answer composer LLM for context. An empty pack yields identical results with a blander narrative.

## Adding an Intent

Checklist:

1. **Add to registry** (`src/api/rcars/services/chat/registry.py`):
   - Create args model (Pydantic `BaseModel` subclass) in `src/api/rcars/services/chat/models.py`
   - Write handler function in `src/api/rcars/services/chat/handlers.py` (signature: `async def handle_X(args: XArgs, ctx: dict, log) -> HandlerResult`)
   - Add `IntentSpec` entry to `INTENTS` dict with all fields
   - Set `requires_role` via `chat_intent_roles_str` config if needed (e.g., `"new_intent:curator"`)

2. **Add golden test cases** to `tests/data/routing_golden.yaml` with marker `@pytest.mark.llm_eval`

3. **Add frontend block renderer** (if new block type):
   - Create component in `src/frontend/src/components/advisor/blocks/` (e.g., `NewBlock.tsx`)
   - Register in `src/frontend/src/components/advisor/blocks/registry.ts` `RENDERERS` dict
   - Unknown block types automatically fall back to `UnknownBlock` (narrative + "view data" expando)

## Configuration

Five `chat_*` settings in `src/api/rcars/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `chat_router_model` | `triage_model` | Model for intent classification (router call). Defaults to Haiku. |
| `chat_answer_model` | `rationale_model` | Model for answer narrative composition. Defaults to Sonnet. |
| `chat_intent_roles_str` | `"performance:curator"` | Per-intent role overrides (colon-separated pairs). Example: `"performance:curator,overlap:admin"` |
| `chat_router_confidence_threshold` | `0.6` | Minimum confidence to accept a router classification. Below threshold → clarification turn. |
| `chat_context_turns` | `5` | Maximum turns in session context window for follow-ups |

All settings are runtime-configurable via env vars (e.g., `RCARS_CHAT_ROUTER_MODEL=claude-sonnet-4-6`).

## Backend Modules

- `services/chat/registry.py` — Intent registry (declarative data): `INTENTS` dict maps intent name → `IntentSpec`
- `services/chat/router.py` — Pattern check, router LLM call, validation/fallback ladder, scope/item-ref resolution
- `services/chat/handlers.py` — Intent handler functions (one per intent, returns `HandlerResult`)
- `services/chat/answer.py` — Scaffold + narrative call (`compose_answer()`)
- `services/chat/orchestrator.py` — Turn orchestration (`process_turn()`: loads context → routes → resolves → handles → composes → persists)
- `services/chat/models.py` — Typed contracts: `RouterOutput`, `Envelope`, `Block`, `Chip`, `HandlerResult`, args models
- `services/chat/evidence.py` — Evidence-pack builder (one-hop graph expansion)
- `db/chat_sessions.py` — Turn persistence (`log_chat_turn()`), context builder (`get_session_context()`), session ownership checks
- `workers/chat.py` — arq task (`run_chat_turn()` — thin wrapper around `process_turn()`)

## Frontend Structure

- `pages/AdvisorPage.tsx` — Single-file implementation: resizable transcript + evidence pane layout, message handling, block rendering, chip actions, session resume
- `components/advisor/blocks/` — Block components: `RecCardsBlock.tsx`, `OverlapTableBlock.tsx`, `PerformanceTableBlock.tsx`, `ItemCardBlock.tsx`, `NoticeBlock.tsx`, `UnknownBlock.tsx`
- `components/advisor/blocks/registry.ts` — Block renderer dispatcher (`resolveBlockRenderer()`) with fallback to `UnknownBlock`
- `components/advisor/chatTypes.ts` — Frontend types: `ChatEnvelope`, `ChatBlock`, `ChatChip`
- `hooks/useJobStream.ts` — SSE streaming for job progress

## Testing

**Golden routing cases:** `tests/data/routing_golden.yaml` — real LLM calls at temperature 0, parametrized by message and expected `(intent, scope_type)`. Run with `pytest -m llm_eval`.

**Deterministic integration:** `tests/test_chat_turn_integration.py` — three-turn session with scope resolution, uses injected mock LLM client to avoid non-determinism.

**Live integration:** `tests/test_chat_live.py` — end-to-end turns with real LLM calls (marked `integration`, requires live Babylon cluster and LiteMaaS/Vertex access).
