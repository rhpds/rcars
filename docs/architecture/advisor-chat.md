# Advisor Chat — Multi-Intent Architecture

The Advisor UI evolved from a recommendation-only chat into a multi-intent "chat with RCARS" — natural-language questions over RCARS capabilities, grounded in RCARS data.

**Design spec:** [`docs/superpowers/specs/2026-08-02-advisor-chat-design.md`](../superpowers/specs/2026-08-02-advisor-chat-design.md)

## Core Principles

- **LLM has no write path into results.** Router output selects which deterministic code path runs; tool results come from SQL/vector queries over existing tables; the answer LLM writes prose next to data it cannot alter.
- **Direct API endpoints remain first-class.** The chat layer sits beside the existing API. External integrators keep hitting `/advisor/query` and never touch the router.
- **Worst case is today's product.** Every router failure mode falls back to the current recommend behavior or an explicit clarification.
- **Extensible by registry.** Adding an intent = one registry entry (enum value, args model, handler, block types, chips, prompt fragment, golden-set examples). No router rewrite, no frontend redesign.

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
Answer composer ──── deterministic scaffold + narrow per-intent LLM narrative
   │
   ▼
Envelope ──── {intent, scope_echo, answer, blocks[], suggested_followups[]}
   │
   └──▶ persist turn (advisor_sessions), complete job, SSE "complete"
```

## Intent Registry

Five intents in v1:

| Intent | Description | Handler | Block Types | Role Gate |
|--------|-------------|---------|-------------|-----------|
| `recommend` | Vector search + LLM triage for catalog recommendations | `handle_recommend` | `rec_cards` (RecCard list) | any authenticated user |
| `overlap` | Content overlap analysis between two or more items | `handle_overlap` | `overlap_table` (pair-by-pair similarity matrix) | any authenticated user |
| `performance` | Performance metrics (provisions, pipeline, sales, cost) | `handle_performance` | `perf_table` (multi-channel metrics table) | curator or admin |
| `item_facts` | Detailed information about specific catalog items | `handle_item_facts` | `item_cards` (full item details with links) | any authenticated user |
| `out_of_scope` | Polite redirect for questions RCARS cannot answer | `handle_out_of_scope` | `notice` (informational message) | any authenticated user |

## Adding an Intent

Checklist:

1. **Add to registry** (`src/api/rcars/services/chat/registry.py`):
   - Add enum value to `ChatIntent`
   - Create args model (subclass of `BaseModel`)
   - Write handler function (signature: `async def handle_X(args, ctx, log) -> HandlerResult`)
   - Add entry to `INTENT_REGISTRY` dict with:
     - `args_model` (for Pydantic validation)
     - `handler` (function reference)
     - `block_types` (list of block type strings)
     - `followup_templates` (optional chips to show under the turn)
     - `prompt_fragment` (intent description for router)
     - `examples` (few-shot examples for router)
     - `requires_role` (optional: `curator` or `admin`)

2. **Add golden test cases** to `tests/test_chat_orchestrator.py` in the `@pytest.mark.llm_eval` suite

3. **Add frontend block renderer** (if new block type):
   - Create component in `src/frontend/src/components/advisor/blocks/`
   - Register in `src/frontend/src/components/advisor/AdvisorBlocks.tsx`
   - Unknown block types automatically get fallback rendering (narrative + "view data" expando)

## Configuration

Five `chat_*` settings in `src/api/rcars/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `chat_router_model` | `granite3.1-8b-instruct` | Model for intent classification (router call) |
| `chat_answer_model` | `granite3.1-8b-instruct` | Model for answer narrative composition |
| `chat_context_turns` | `10` | Maximum turns in session context window for follow-ups |
| `chat_max_scope_items` | `5` | Maximum items in a scoped follow-up query |
| `chat_intent_roles_str` | `""` | Per-intent role overrides (JSON dict); empty = use registry defaults |

All settings are runtime-configurable via env vars (e.g., `RCARS_CHAT_ROUTER_MODEL=llama3.1-70b-instruct`).

## Backend Modules

- `services/chat/registry.py` — Intent registry (declarative data): enum value → args model, handler, block types, followup templates, prompt fragment + few-shot examples
- `services/chat/router.py` — Pattern check, router LLM call, validation/fallback ladder
- `services/chat/handlers.py` — Intent handler functions (one per intent)
- `services/chat/answer.py` — Scaffold + narrative call
- `services/chat/orchestrator.py` — Turn orchestration (loads context → routes → resolves → handles → composes → persists)
- `services/chat/models.py` — RouterOutput, Envelope, Block, HandlerResult schemas
- `services/chat/evidence.py` — Evidence-pack builder (graph expansion for context)
- `db/chat_sessions.py` — Turn persistence, context builder, session ownership checks
- `workers/chat.py` — arq task (thin wrapper around orchestrator)

## Frontend Structure

- `pages/AdvisorPage.tsx` — Resizable transcript + evidence pane layout
- `components/advisor/AdvisorTranscript.tsx` — Turn list with user/assistant messages
- `components/advisor/AdvisorBlocks.tsx` — Block renderer registry (type → React component)
- `components/advisor/blocks/` — Block components (`RecCards`, `OverlapTable`, `PerfTable`, `ItemCards`, `Notice`)
- `components/advisor/FollowUpChips.tsx` — Suggested follow-up chip row
- `hooks/useJobStream.ts` — SSE streaming for job progress
