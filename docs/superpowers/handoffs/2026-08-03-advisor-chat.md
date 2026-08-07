# Handoff: Advisor Gen-2 Multi-Intent Chat

**Date:** 2026-08-03
**Branch:** `feature/advisor-chat` (26 commits ahead of main)
**Jira:** [RHDPCD-175](https://redhat.atlassian.net/browse/RHDPCD-175) — Advisor: Gen-2 multi-intent chat agent
**Status:** Deployed to dev, actively testing. Not yet merged to main or deployed to prod.

## What Was Built

The Advisor evolved from a single-intent recommend-only flow into a multi-intent chat agent. One LLM router call classifies each message into 5 intents, then deterministic handlers execute fixed tool plans — no agent loops.

### Architecture

```
User message → pattern_check (deterministic fast-path)
             → router LLM call (classify into intent)
             → resolve_and_verify (validate claims against catalog)
             → handler (fixed tool plan per intent)
             → evidence_pack (one-hop neighbor context)
             → compose_answer (scaffold + narrative LLM)
             → envelope (typed response + follow-up chips)
```

### Five Intents

| Intent | Handler | What it does |
|--------|---------|-------------|
| recommend | `handle_recommend` | Full recommend pipeline (vector → triage → rationale) |
| overlap | `handle_overlap` | Content similarity for a specific item |
| performance | `handle_performance` | Usage/provisions/cost metrics from reporting data |
| item_facts | `handle_item_facts` | Single item details (summary, products, modules, workloads) |
| out_of_scope | (none) | Deterministic "I can help with four things..." |

### Key Backend Files

- `src/api/rcars/services/chat/` — models, registry, router, handlers, evidence, answer, orchestrator
- `src/api/rcars/db/chat_sessions.py` — turn persistence, context builder, ownership
- `src/api/rcars/workers/chat.py` — arq task on the recommend queue
- `src/api/rcars/services/recommender/serialize.py` — extracted candidate serialization (shared by recommend worker + chat)

### Key Frontend Files

- `src/frontend/src/components/advisor/chatTypes.ts` — ChatEnvelope, ChatBlock, ChatChip
- `src/frontend/src/components/advisor/blocks/` — 6 block renderers + registry
- `src/frontend/src/pages/AdvisorPage.tsx` — rewired for envelope-driven transcript
- `src/frontend/src/pages/HistoryPage.tsx` — updated for non-recommend session preview

### API

- `POST /api/v1/advisor/chat` — `{message, session_id?, stages?, routed?}` → `{job_id, session_id}`
- Result and stream use existing `/advisor/query/{job_id}/result` and `/advisor/query/{job_id}/stream`

### Config (all `RCARS_` prefixed)

| Setting | Default | Purpose |
|---------|---------|---------|
| `CHAT_ROUTER_MODEL` | triage_model | Model for intent classification |
| `CHAT_ANSWER_MODEL` | rationale_model | Model for narrative answer |
| `CHAT_INTENT_ROLES_STR` | `performance:curator` | Role gates per intent |
| `CHAT_ROUTER_CONFIDENCE_THRESHOLD` | 0.6 | Below this → clarify |
| `CHAT_CONTEXT_TURNS` | 5 | Turns in router context window |

### Tests

- 28 backend tests (unit + integration with FakeLLM, no real LLM needed)
- 2 frontend vitest tests (block registry dispatch)
- 16 golden routing YAML cases (`-m llm_eval` — needs LLM credentials)
- 2 live integration tests (`-m integration`)

## Bugs Fixed During Dev Testing

These were found and fixed during hands-on testing in dev:

1. **SSE stream closing prematurely** — `run_query` emits `phase:"complete"` when the pipeline finishes, but the chat turn still has answer composition ahead. Handler now wraps `on_progress` to suppress pipeline's "complete" event.

2. **SSE race on fast jobs** — performance/overlap/item_facts handlers finish in milliseconds, before the frontend opens the SSE stream. Redis pub/sub is fire-and-forget. Fix: stream endpoint checks job status on connect and emits synthetic "complete" if already done.

3. **Missing curator/admin env vars on worker** — `RCARS_CURATOR_EMAILS_STR` and `RCARS_ADMIN_EMAILS_STR` were only on the API deployment, not the recommend worker. Chat role gates run on the worker, so `is_admin()` always returned False. Fixed in `manifests-app.yaml.j2`.

4. **Item resolution preferring base components over published VCIs** — "Introduction to AAP Self-Service Automation" resolved to the unpublished base component (0 provisions) instead of the published Virtual CI (186 provisions). Fixed: `find_catalog_item_by_display_name_prefix` and `find_catalog_item_by_keyword_overlap` now order by `is_published DESC`.

5. **Clarify chip item_ref not resolving** — Clarify chips carry `item_ref` in `args` but `item_refs` stays empty. Pre-routed chips skipped item resolution entirely. Fix: orchestrator promotes `args.item_ref` to `item_refs`.

## Known Issues / Next Steps

- **Group performance queries** — "how is our Ansible content performing?" currently asks for clarification (which specific item?). The system can't aggregate performance across a category yet. This is a feature gap, not a bug — needs a new handler or scoped search approach.

- **No PR yet** — branch is deployed to dev from `feature/advisor-chat`. Merge to main via PR when testing is complete. CodeRabbit will review.

- **Architecture question: worker vs inline** — Non-recommend intents (performance, overlap, item_facts) take <1s but run through the full arq worker → SSE → poll cycle. Could run inline on the API for fast intents. Current architecture works with the SSE race fix but is heavier than needed.

- **Deploy to prod** requires a PR to merge `feature/advisor-chat` → `main`, then `main` → `production`.

## How to Deploy

```bash
# Dev (from feature branch)
ansible-playbook ansible/deploy.yml -e env=dev --tags full

# After merging to main
ansible-playbook ansible/deploy.yml -e env=dev --tags full
# Then PR main → production, then:
ansible-playbook ansible/deploy.yml -e env=prod --tags full
```

## Spec & Plan References

- Design spec: `docs/superpowers/specs/2026-08-02-advisor-chat-design.md`
- Implementation plan: `docs/superpowers/plans/2026-08-02-advisor-chat.md`
- Architecture doc: `docs/architecture/advisor-chat.md`
