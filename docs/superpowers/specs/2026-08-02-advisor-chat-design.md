# Advisor Chat — Multi-Intent Design

**Date:** 2026-08-02
**Status:** Design complete — sections approved in review dialogue; spec pending final review
**Scope:** Evolve the Advisor from a recommendation-only chat into a multi-intent "chat with RCARS" — natural-language questions over RCARS capabilities, grounded in RCARS data.

## Summary

The Advisor UI looks like chat, but every turn is hardcoded to the recommend pipeline. This design keeps the chat surface and replaces the backend with **intent → tools → grounded answer**: a single LLM router call classifies each message into a closed intent set, deterministic handlers run fixed tool plans over existing service/DB functions, and a narrow answer call writes the narrative next to typed evidence blocks the frontend renders itself.

Core properties:

- **The LLM has no write path into results.** Router output selects which deterministic code path runs; tool results come from SQL/vector queries over existing tables; the answer LLM writes prose next to data it cannot alter.
- **Direct API endpoints remain first-class.** The chat layer sits *beside* the existing API, never in front of it. External integrators keep hitting `/advisor/query` (which gains an opt-in `depth` parameter) and never touch the router.
- **Worst case is today's product.** Every router failure mode falls back to the current recommend behavior or an explicit clarification — never a fabricated answer.
- **Extensible by registry.** Adding an intent = one registry entry (enum value, args model, handler, block types, chips, prompt fragment, golden-set examples). No router rewrite, no frontend redesign.

## Goals

- V1 intents: `recommend`, `overlap`, `performance`, `item_facts`, plus `out_of_scope` handling.
- Real multi-turn sessions: follow-ups like "which of these performed best?" resolve deterministically against prior results.
- Evidence-first UX: typed blocks (cards, tables) rendered by React components, deep-linked into Browse/Overlap/Retirement.
- Read-only. Role-gated where needed, opening up via config.
- Per-call-site model configuration to enable open-source model adoption for basic tasks.

## Non-Goals

- Portfolio/gaps intent (fast-follow; see Follow-On Work).
- Microsoft GraphRAG, Neo4j, or any second knowledge-graph pipeline.
- Agentic tool-calling loops (LLM choosing tools iteratively).
- Write actions (Jira, retire) — explicit later design + HITL.
- Replacing Curator/Overlap/Retirement pages — chat complements and deep-links into them.
- New content-source ingestion (e.g. Portfolio Architectures) — the design accommodates mixed content types structurally, but ingestion is separate work.

## Approach Decision

Three approaches were considered:

1. **Single-shot router + fixed per-intent plans (chosen).** One router call; each intent maps to a hand-written handler with a fixed tool order. Most deterministic, most testable, fits existing patterns (structured JSON, sync LLM in thread pool, arq, SSE).
2. **Tool-calling agent loop** (Pydantic AI / native function calling). Handles novel compositions but nondeterministic tool sequences, weak testability, latency variance. Rejected for v1.
3. **Declarative planner** (router emits an ordered tool plan; deterministic executor runs it). Middle ground; deferred until usage logs show real demand for chained single-message questions (e.g. "top 3 X, overlap for each, and which overlapping items perform better"). Such questions are served in v1 across multiple turns via scoped follow-ups, with an honest partial answer on the single message.

Tools are the reusable unit, so Approach 3 can be added on top of the same tool layer without redesign.

## Architecture

One new endpoint, `POST /advisor/chat`, following the existing job pattern: returns `{job_id, session_id}` immediately, processes on the recommend worker (`arq:queue:recommend`), streams progress over Redis pub/sub → SSE, result lands in `result_json`. No new deployments or queues.

### Turn flow (in the worker)

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

### Backend modules

New code mirrors the `services/recommender/` layout. **Hard rule: the chat layer adds zero methods to `database.py`** — new queries go in a focused `db/chat_sessions.py`, following the `db/similarity.py` precedent.

- `services/chat/registry.py` — intent registry (declarative data): enum value → args model, handler, block types, followup templates, prompt fragment + few-shot examples.
- `services/chat/router.py` — pattern check, router LLM call, validation/fallback ladder.
- `services/chat/handlers.py` — four thin handler functions. If any handler outgrows ~100 lines it graduates to `handlers/<intent>.py`.
- `services/chat/answer.py` — scaffold + narrative call.
- `services/chat/models.py` — RouterOutput, Envelope, Block schemas.
- `services/chat/evidence.py` — evidence-pack builder (graph expansion).
- `db/chat_sessions.py` — turn persistence, context builder, session ownership checks.
- `workers/chat.py` — the arq task.

The orchestrator takes its LLM client as an injectable dependency (testability; see Testing).

### Frontend

`AdvisorPage` keeps the resizable transcript + evidence-pane layout. Additions:

- **Block renderer registry**: block `type` → React component. `rec_cards` maps to the existing RecCard list; new types get new components. Unknown block types render a fallback (narrative + raw "view data"), so new backend block types never crash an older frontend.
- **Follow-up chips** under each assistant turn (see UX).
- `cleanAssessment()` is deleted — structure comes from typed envelope fields, not parsed prose.

## Intents & Router Contract

### V1 intent registry

| | `recommend` | `overlap` | `performance` | `item_facts` |
|---|---|---|---|---|
| **Answers** | "Find me content for…" | "What overlaps with / is similar to X?" | "How is X / are these performing?" | "What is X? What's in it?" |
| **Args** | `search_query`, `constraints` (duration, format_hint, performance, stages) | `item_ref` *or* scope | `item_ref(s)` *or* scope *or* facet filters | `item_ref` |
| **Tool plan** | `run_query()` (scoped variant when scope present) | resolve ref → `get_overlap_items` / `get_similar_items` | resolve → `performance_channels` (+ `performance_scores` only if retirement-flavored) | resolve → catalog item + `showroom_analysis` + workloads |
| **Blocks** | `rec_cards` | `overlap_table` (+ `item_card` anchor) | `performance_table` | `item_card` |
| **Chips** | overlap for these · performance of these · about #1 | about item · performance of these | recommend from these · about item | overlap with this · performance of this |
| **Role** | any | any | `curator` (config) | any |

Plus **`out_of_scope`**: a pseudo-intent with no tool plan — deterministic response listing what RCARS can help with. No improvising.

Composite queries resolve to a primary intent plus structured constraints (e.g. "high-usage Ansible for an EDA demo" → `recommend` with `constraints.performance=high_usage`), not to multiple intents. The distinction between `recommend`-with-usage-constraint and standalone `performance` is what the answer is *about*: content to go use (cards) vs. a fact about the portfolio (table). Both shapes are in the golden set.

Naming: chat answers use "usage"/"performance" language generally and invoke retirement language only when the user asks about retirement.

### Router contract

Input: the user message, the structured session context (last ≤5 turns), nothing else. Output, Pydantic-validated:

```json
{
  "intent": "recommend | overlap | performance | item_facts | out_of_scope",
  "args": { },
  "scope": null | {"type": "prior_results", "turn": 2} | {"type": "ordinal", "turn": 2, "index": 2},
  "item_refs": ["free-text mentions, e.g. 'the SAP lab', 'LB2144'"],
  "confidence": 0.0,
  "clarify": null | {"question": "...", "options": ["..."]}
}
```

The router prompt is assembled from the registry (descriptions + few-shot examples per intent), so adding an intent automatically teaches the router.

### Validation & fallback ladder (all deterministic)

1. JSON parse / schema failure → retry once → **fallback `recommend`** with the raw message as `search_query` (= today's behavior). Router call *errors* (timeout, provider down) are treated identically — a dead router model degrades to today's Advisor, not an outage.
2. `scope` names a turn not in context → clarification turn with chips.
3. Each `item_refs` entry goes through catalog resolution (existing LB-regex + name-overlap + embedding lookup). Unresolvable → "did you mean…" turn with top vector matches as chips. The router's belief that an item exists is never trusted.
4. `confidence` below `chat_router_confidence_threshold` → the router's own `clarify` question renders with chips instead of executing.
5. Role check on the resolved intent → polite redirect naming the gated capability.

Chips are **pre-routed**: each carries `{intent, args, scope}`, so tapping one skips the router entirely — clarification loops cannot compound routing error.

### What LLMs decide vs. what code decides

| Decision | Who makes it | Containment |
|---|---|---|
| Which intent | Router (or pattern check) | Closed enum, validated; fallback `recommend` |
| Which items ("these", "the second one") | Never the LLM — symbolic scope + DB lookup | Scope must name an existing turn |
| Whether a named item exists | Never the LLM — catalog resolution | "Did you mean…" on miss |
| Which rows come back | Never the LLM — SQL/vector queries | Deterministic given router output |
| What's on cards/tables | Never the LLM — React renders tool rows | N/A |
| The narrative paragraph | Answer LLM | Worst case: mediocre prose next to correct data; call failure → template intro |

## Tools, Grounding & Graph-Shaped Retrieval

### Tool layer

No new retrieval infrastructure — no graph database, no new tables (beyond columns), no new embeddings, no background pipelines. Tools are a manifest of existing functions, all read-only:

| Tool | Existing code | Returns |
|---|---|---|
| `search_content(query, stages, depth, scope_ids?)` | `recommender/pipeline.run_query()` | candidates (tiered if depth ≥ medium) |
| `resolve_item(ref)` | CI-name/LB resolution + embedding lookup | content_id or ranked guesses |
| `get_item(content_id)` | catalog + `showroom_analysis` + workloads queries | full item record |
| `get_neighbors(content_id, kinds)` | `similarity.get_overlap_items` / `get_similar_items` | edges with scores + relationship_type |
| `get_performance(content_ids \| filters, window)` | `performance_channels` / `performance_scores` queries | metric rows |

New code in this section, in full: (1) the `depth` stop-after argument in `run_query()`; (2) scoped search — a WHERE clause restricting the candidate pool to working-set content_ids; (3) the evidence-pack builder — a batched SQL query over three existing tables plus assembly.

### `depth` parameter

`run_query()` gains a stop-after-phase argument, exposed on `POST /advisor/query`:

- `low` — vector search only (seconds)
- `medium` — + triage
- `high` — full pipeline including rationale (**default; omitted parameter = byte-for-byte today's behavior — existing callers unaffected**)

This exists primarily for external integrators who want to trade completeness for latency. The chat layer uses it too: full-catalog recommend turns run `high`; scoped working-set questions run `medium` (the answer composer writes the narrative anyway). The existing vector-search candidate limit (25) is unchanged.

### Evidence pack (v1 graph expansion: one hop, code-driven, bounded)

After a handler gets its primary results, it optionally expands each anchor item one hop through edges that already exist in Postgres: `content_similarity` (both `overlap` and `related`, with scores), shared products/topics (`showroom_analysis`), shared workloads (`babylon_item_workloads`).

Hard budget: ≤15 neighbor items total, ≤6 fields each (name, stage, similarity %, relationship type, key products, provisions). Caps are code constants, not config. Which neighbors make the pack is deterministic (top-k by edge score), never an LLM choice.

**The budget affects only the answer narrative's context.** It never adds, removes, or reorders results; an empty pack yields identical results with a blander narrative.

What it buys: `item_facts` answers place the item in context ("closely overlaps 2 other prod items, shares an OpenShift Virt workload with X"); `recommend` narratives can flag cross-result insight ("your top 2 picks overlap 78% — consider pairing #1 with #3"). Multi-hop traversal, clustering, and theme summaries are deferred to the portfolio/gaps intent.

### Grounding rule

The answer composer's prompt contains exactly three things: the deterministic scaffold facts, the evidence pack, and the user's question. Instruction: "explain this data; if the data doesn't answer the question, say so." Items are cited only by evidence-pack reference, and the narrative renders next to blocks built from the same rows — every claim is checkable against the table beside it.

### Scale posture (vector + relational vs. graph DB)

The current model (pgvector + `content_similarity` edges in Postgres) is comfortable far beyond plausible catalog growth: pgvector/HNSW handles millions of vectors; 1–2-hop joins are ordinary indexed queries efficient into millions of edges; clustering at catalog scale is an offline batch job. The first pressure point is the O(n²) *similarity computation* job (~50M pairs at 10k items), fixed by top-k thresholding — a batch-job optimization, not a data-model change. A graph database becomes justified only under a different workload (open-world corpora, entity extraction, online multi-hop traversal over 100k+ densely connected nodes), which is out of scope. The tool layer is the firewall: if that ever changed, tool implementations swap; router, intents, envelope, and frontend are unaffected.

## Session Model & Multi-Turn

### Session ≠ job

Each *turn* is an arq job (keeping job/SSE infrastructure). `POST /advisor/chat` takes an optional `session_id`: absent on the first message (server generates and returns one), present on follow-ups. `advisor_sessions` keys stay (`session_id`, `turn_index`); `turn_index` finally increments. Direct `/advisor/query` sessions are unchanged (session_id = job_id, single turn).

### Persisted per turn (`db/chat_sessions.py`; columns via `ALTER TABLE ADD COLUMN IF NOT EXISTS`)

- Existing: `query_text`, `results_json` (result IDs + names — what makes scopes resolvable), `overall_assessment`, timestamps.
- New: `intent` TEXT, `envelope_json` JSONB (blocks + chips — History replays a turn exactly as rendered), `scope_json` JSONB (audit: "turn 3 ran against turn 2's results").

### Context builder

Produces the router's view: last ≤`chat_context_turns` (default 5) turns, each reduced to `{n, intent, query, results: [{id, name}]}` — a few hundred tokens, fixed shape, no transcript prose.

### Reference-resolution conventions (fixed rules)

- "these / those / them" → most recent turn that produced results.
- Ordinals ("the second one") → position in that result list.
- Clarification-only turns are skipped when resolving references.
- **The 5-turn window is a context window, not a session limit.** Sessions may run arbitrarily long; references resolve only within the window. Turn 6+ works; it cannot reach turn 1's results. The UI shows an advisory nudge ("long session — fresh often works better") with the existing New Session action; never a block.

### Resuming sessions

The `?session=` load path restores transcript + evidence from `envelope_json`; typing into a resumed session continues `turn_index` and the context window applies from the current position. Pre-chat single-turn sessions are resumable — their `results_json` is a valid working set.

### Ownership

Every read filters by `user_email` (existing pattern); admins bypass. New check: `POST /advisor/chat` with a `session_id` verifies the session belongs to the caller before appending — 404 otherwise, mirroring the job-ownership check.

### History page

Chat sessions appear in the existing listing (turns-count query already handles multi-turn). Loading one replays from `envelope_json` through the block renderers. `/select` keeps working per turn.

## UX

### Transcript (left pane)

An assistant turn renders, top to bottom:

1. **Interpretation echo** — muted line generated from validated router output ("Comparing performance of the 8 items from your last results"). Always present; this is the misroute tripwire.
2. **Narrative** — deterministic scaffold line (counts, scope) + composed paragraph.
3. **Follow-up chips** — pre-routed; tapping inserts the action as a user turn and submits with zero router involvement.

Clarification turns are chips-only. The welcome screen is rewritten around the four intents with example prompts for each — the cheapest routing aid available, teaching phrasings the router is tested on.

### Evidence pane (right)

| Block | Renders as | Deep-links to |
|---|---|---|
| `rec_cards` | existing RecCard tiers + **content-type badge** | see link rule below |
| `overlap_table` | anchor header + neighbor rows: similarity %, relationship type, stage, shared products/modules, nullable `why` | Content Analysis → Overlap |
| `performance_table` | metric rows w/ window echo (provisions, cost/provision, sales impact; score badge only when retirement-flavored) | Retirement page |
| `item_card` | summary, products, modules/objectives, workloads, neighbors strip | RCARS catalog entry |
| `notice` | out-of-scope / role-redirect / clarification framing | relevant page |

**Card link rule (two links):** primary → the actual external thing, type-appropriate (RHDP catalog item on demo.redhat.com for Babylon items; Portfolio Architecture page, Interactive Demo, etc. for future types); secondary → the RCARS catalog entry (Browse item detail), which is the drill-down home for Showroom, tags, embeddings, analysis. Showroom drops off the card itself. The envelope carries a per-card `links` object populated per source.

**Mixed content types:** candidates already carry `content_type`. Cards render type badges; the block supports a secondary strip ("Also similar, though not labs: …") when non-lab types appear in results. When new sources are ingested (separate work), chat requires zero redesign.

**Overlap honesty:** v1 renders the deterministic parts only (score, relationship type, shared attributes computed from `showroom_analysis`); the answer composer may describe shared attributes but may not explain *why* items overlap beyond them. The per-edge `why` field populates when the overlap-summary batch job lands (see Follow-On Work) — chat upgrades automatically, no coupling.

**Turn selector:** today's "Rec 1 / Current" buttons generalize to per-turn evidence history — flipping back to turn 1's cards while reading turn 3's answer.

### Progress streaming

SSE phase vocabulary extends: chat turns emit `routing`, then the handler's phases. `recommend` keeps its full existing stream; other intents (~2–4s) show `routing → fetching → composing`. `ProgressStream` gains labels; no structural change.

## API Surface

| Endpoint | Change |
|---|---|
| `POST /advisor/chat` | **New.** `{message, session_id?, stages?, include_zt?}` → `{job_id, session_id}`. Verifies session ownership on append. Shares the per-user advisor rate-limit bucket. |
| `GET /advisor/query/{job_id}/stream`, `/result` | Unchanged — chat turns are jobs. |
| `POST /advisor/query` | Adds optional `depth: low\|medium\|high`, default `high`. |
| `GET /advisor/sessions`, `/sessions/{id}` | Unchanged shape; detail includes new per-turn fields. |
| `POST /sessions/{id}/select` | Unchanged. |

All `/catalog/*` and `/analysis/*` endpoints untouched — direct integration paths preserved.

## Configuration

All in `Settings`, `RCARS_`-prefixed. No LLM call site hardcodes a model; swapping models is a config change (`--tags apply-config`).

| Setting | Default | Purpose |
|---|---|---|
| `chat_router_model` | value of `triage_model` | Routing — prime open-source candidate (closed-schema classification) |
| `chat_answer_model` | value of `rationale_model` | Narrative composition |
| `chat_intent_roles` | `performance:curator` | Intent → minimum role tier (`any`/`curator`/`admin`), against existing email-list roles. Opening up later = config change. Users below tier get an honest redirect (and the ask is logged — demand is visible before opening). |
| `chat_router_confidence_threshold` | `0.6` | Below → clarify instead of execute |
| `chat_context_turns` | `5` | Router context window |

Existing `triage_model` / `rationale_model` are untouched.

## Error Handling & Observability

- Router parse failure or call error → retry once → fallback `recommend`.
- Answer-call failure → deterministic template intro; blocks render; turn succeeds.
- Tool/SQL failure → job fails honestly via existing path (`fail_job` + safe SSE error). Never a partial answer pretending to be complete.
- Token accounting: `log_token_usage` with operations `chat_router`, `chat_answer` — appears on the Token Usage page with no page changes.
- Logging: every turn logs structlog with `component=chat, intent, confidence, scope_type, fallback_used`. Query History becomes the routing audit trail; production misroutes become golden-set cases.

## Testing

### Tiers

1. **Unit (fast, every CI run).** Scope resolution against fixture sessions (ordinals, "these", clarify-skipping, stale refs); registry completeness (every intent has handler + blocks + chips + prompt fragment); envelope schema round-trips; role gating; router *validation* logic with canned LLM outputs (malformed JSON, hallucinated intents, bad turn refs).
2. **Golden routing eval (marked `llm_eval`, live LLM).** Cases in `src/api/tests/data/routing_golden.yaml` — `{message, context?, expect: {intent, scope_type}}` — so adding a case is a one-line PR. `test_chat_routing_golden.py` parametrizes over the YAML, calls the real `router.route()` (real prompt assembly, real model, real validation), hard-asserts at temperature 0. ~40 cases including adversarial pairs (recommend-with-usage-constraint vs. standalone performance). **This is the acceptance gate for prompt changes and open-source model swaps.**
3. **Integration — deterministic layer (every CI run).** The orchestrator's LLM client is injectable; tests inject a fake client returning canned router/answer JSON. Everything else is real: `rcars_test` Postgres, seeded fixture catalog (~a dozen `content_entities`, deterministic synthetic 768-dim embeddings, `content_similarity` edges, `performance_channels` rows), real handlers/SQL/envelope/persistence. A 3-turn session test drives `run_chat_turn()` in-process and asserts scope resolution end to end (turn 2's table contains exactly turn 1's content_ids).
4. **Integration — live layer (marked `integration`).** A handful of end-to-end turns with real LLM calls against the seeded DB. Run with the golden eval before deploys.
5. **Frontend.** Block renderer registry: type dispatch + unknown-block fallback.

### Running the tests

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api

# Fast suite — what CI runs on every commit (no LLM calls; needs local Postgres+Redis)
python -m pytest tests/ -m "not integration and not llm_eval"

# Golden routing eval — live LLM calls to the configured router model (~40 calls, cents)
python -m pytest tests/ -m llm_eval -v

# Pre-deploy / pre-model-swap gate — eval + live end-to-end turns
python -m pytest tests/ -m "llm_eval or integration" -v

# Chat tests only, during development
python -m pytest tests/test_chat*.py -v

# Evaluate a candidate open-source router model
RCARS_CHAT_ROUTER_MODEL=<candidate> python -m pytest tests/ -m llm_eval
```

Prereqs match today's test setup: `dev-services.sh` provides Postgres/Redis (`rcars_test` auto-created); marked tiers need the normal `RCARS_` LLM credentials in the environment.

### Relation to the testing backlog item

Three artifacts here are reusable foundations for the broader "proper testing" backlog item: the seeded fixture catalog, the fake-LLM-client fixture, and the `llm_eval` marker convention. Link the Jira items when this ships.

## Deployment

No new deployments, queues, or services. `workers/chat.py` registers on the existing recommend worker. `init-db` picks up new columns idempotently. Normal flow: dev first via `--tags api` / `--tags frontend`.

## Follow-On Work (not in v1)

1. **Portfolio/gaps intent.** Standalone "what are we missing for AI?" gets an honest "here's what exists in that space" in v1; gap statements still surface within thin recommend results via `generate_content_gaps()`. The real intent needs coverage/clustering work and becomes the first test of the registry's extensibility.
2. **Overlap "why" summaries.** Batch LLM pair-analysis on `content_similarity` pairs ≥0.85: input is both items' stored analysis; output is structured JSON on the edge (`overlap_summary` — 2–3 sentence summary, `distinction`, `verdict` enum: redundant/complementary/superset-subset), keyed to both items' `content_hash` for invalidation on rescan. Consumers ready on day one: the Overlap page and the chat `overlap_table.why` field. Dedicated model setting; open-source candidate. (Tracked as its own Jira item.)
3. **Declarative planner (Approach 3)** — only if usage logs show chained single-message questions.
4. **New content sources** (Portfolio Architectures, Interactive Demos) — ingestion work; chat consumes them via `content_type` with zero redesign.
5. **Open-source model adoption** — per-call-site settings + golden eval as the acceptance gate, starting with `chat_router_model`.
