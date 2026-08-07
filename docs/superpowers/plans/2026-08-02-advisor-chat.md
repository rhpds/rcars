# Advisor Multi-Intent Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the Advisor chat from recommend-only into intent → tools → grounded answer: one router LLM call selects a deterministic handler, handlers run fixed tool plans over existing SQL/vector functions, a narrow answer call writes prose next to typed evidence blocks.

**Architecture:** New `POST /advisor/chat` endpoint follows the existing job pattern (job_id + SSE on the recommend worker). New backend package `services/chat/` (registry, router, handlers, answer, evidence, models) + `db/chat_sessions.py` + `workers/chat.py`. Frontend keeps the AdvisorPage layout and gains a block-renderer registry, follow-up chips, and interpretation echo. Spec: `docs/superpowers/specs/2026-08-02-advisor-chat-design.md`.

**Tech Stack:** Python 3.11, FastAPI, arq + Redis, PostgreSQL/pgvector (psycopg3), Pydantic v2, structlog; React 19 + TypeScript + Vite (custom theme, no PatternFly in Advisor pane); pytest.

## Global Constraints

- **Environment:** This plan was written on a laptop with no dev environment. Every "Run" step must be executed on a machine with `./dev-services.sh start` running (Postgres w/ pgvector on 5432, Redis on 6379, venv `~/.virtualenvs/rcars-v2`). Do not skip test runs — defer them, never fake them.
- **Zero new methods on `database.py`** (`src/api/rcars/db/database.py`). New chat queries go in `src/api/rcars/db/chat_sessions.py` (module functions taking the pool, like `db/similarity.py`). Modifying an *existing* method (e.g. adding an optional param to `search_embeddings`) is allowed — that is a pipeline change, not chat-layer growth.
- **LLM output is always Pydantic-validated JSON.** Retry once → deterministic fallback. Worst case for any router failure = today's recommend behavior. The LLM never determines data content, only which code path runs.
- **No agent loops.** The router decides once; code runs a fixed tool plan; the LLM never sees tool results and picks a next step.
- **All settings are `RCARS_`-prefixed** on `Settings` (`src/api/rcars/config.py`). No LLM call site hardcodes a model. New call sites log tokens via `db.log_token_usage()` with operations `chat_router` / `chat_answer`.
- **`depth` default is `high`; omitted parameter = byte-for-byte today's behavior** for `run_query()` and `POST /advisor/query`.
- **Evidence pack caps are code constants** (≤15 neighbors, ≤6 fields), not config. The pack only affects narrative context, never results.
- **Chips are pre-routed:** each carries `{intent, args, scope}`; tapping one skips the router.
- **Naming/copy:** chat answers use "usage"/"performance" language; retirement language only when the user asks about retirement. Default role gate: `performance:curator`.
- **Structlog:** every turn logs `component=chat, intent, confidence, scope_type, fallback_used`.
- **Git:** feature branch + PR (non-trivial change). Commit per task; push at milestones. After code changes run `graphify update .`.

## File Map

New files:

| File | Responsibility |
|---|---|
| `src/api/rcars/services/chat/__init__.py` | package marker |
| `src/api/rcars/services/chat/models.py` | RouterOutput, Scope, Clarify, Chip, Block, Envelope, per-intent args models |
| `src/api/rcars/services/chat/registry.py` | declarative intent registry + router prompt assembly |
| `src/api/rcars/services/chat/router.py` | pattern check, router LLM call, resolve & verify, fallback ladder |
| `src/api/rcars/services/chat/handlers.py` | four thin handlers (graduate to `handlers/<intent>.py` past ~100 lines) |
| `src/api/rcars/services/chat/answer.py` | deterministic scaffold + narrative LLM call |
| `src/api/rcars/services/chat/evidence.py` | evidence-pack builder (one-hop, bounded) |
| `src/api/rcars/services/chat/orchestrator.py` | `process_turn()` — the turn flow, LLM client injectable |
| `src/api/rcars/db/chat_sessions.py` | turn persistence, context builder, ownership, small chat reads |
| `src/api/rcars/workers/chat.py` | `run_chat_turn` arq task |
| `src/api/rcars/services/recommender/serialize.py` | shared candidate→dict serialization (extracted from recommend worker) |
| `src/api/tests/chat_fixtures.py` | seeded fixture catalog + deterministic fake embeddings |
| `src/api/tests/data/routing_golden.yaml` | golden routing cases |
| `src/api/tests/test_chat_*.py` | test files per tier |
| `src/frontend/src/components/advisor/chatTypes.ts` | Envelope/Block/Chip TS types |
| `src/frontend/src/components/advisor/RecCardList.tsx` | RecCardList + CollapsibleTier (moved out of AdvisorPage) |
| `src/frontend/src/components/advisor/blocks/*.tsx` + `registry.ts` | block renderers + dispatch with unknown-block fallback |

Modified: `config.py`, `db/database.py` (SCHEMA_SQL columns + `search_embeddings` scope param only), `services/recommender/pipeline.py` (+`vector_search.py`), `api/routes/advisor.py`, `api/schemas.py`, `api/streaming.py`, `workers/settings.py`, `workers/recommend.py`, `pyproject.toml` (marker), `frontend: api.ts, AdvisorPage.tsx, ProgressStream.tsx, package.json`, `CLAUDE.md`.

## Task Sequence

**Execute tasks strictly in order 1 → 17.** Later tasks import symbols defined in earlier ones (each task's Interfaces block says which). The shape, for orientation:

- **Foundations (1–3):** config settings → session columns + `db/chat_sessions.py` + seeded fixture catalog → typed envelope/router models. Tasks 1, 2, 3 are mutually independent, but everything after 3 needs all of them.
- **Deterministic core (4–8):** `depth`/scoped search in the pipeline (4) → resolve-and-verify ladder (5) → evidence pack (6) → handlers (7, needs 4+5) → intent registry (8, needs 7).
- **LLM seams (9–11):** router `route()` (9, needs 5+8) → answer composer (10) → orchestrator + 3-turn deterministic test (11, needs everything above).
- **Surface (12–13):** worker + `POST /advisor/chat` + SSE (12, needs 11) → golden eval + live tier (13, needs 9+11; requires LLM credentials).
- **Frontend (14–16):** types/api/blocks (14, needs the envelope contract frozen by 12) → AdvisorPage rewiring (15) → vitest (16). 14–16 may run in parallel with 13 — nothing else is safely parallel.
- **Wrap-up (17):** docs, full test gate, PR, dev deploy, Jira.

Do not reorder to "get the UI working first" — the frontend renders the envelope contract that tasks 3/11/12 define and test.

---

### Task 1: Chat settings in `config.py`

**Files:**
- Modify: `src/api/rcars/config.py` (Settings fields ~line 46-52 area, `model_post_init` at line 111, properties at line 128)
- Test: `src/api/tests/test_config.py`

**Interfaces:**
- Produces: `settings.chat_router_model: str` (defaults to `triage_model`), `settings.chat_answer_model: str` (defaults to `rationale_model`), `settings.chat_intent_roles: dict[str, str]` (property, e.g. `{"performance": "curator"}`), `settings.chat_router_confidence_threshold: float = 0.6`, `settings.chat_context_turns: int = 5`. All later tasks read these.
- Note: the raw field is `chat_intent_roles_str` (env `RCARS_CHAT_INTENT_ROLES_STR`), following the `curator_emails_str` precedent; the spec's `chat_intent_roles` name is the parsed property.

- [ ] **Step 1: Write the failing tests** (append to `src/api/tests/test_config.py`; it already imports `Settings` and `pytest`)

```python
def test_chat_model_defaults_follow_triage_and_rationale():
    s = Settings(database_url="postgresql://x/x",
                 triage_model="m-triage", rationale_model="m-rationale")
    assert s.chat_router_model == "m-triage"
    assert s.chat_answer_model == "m-rationale"


def test_chat_models_explicit_override():
    s = Settings(database_url="postgresql://x/x",
                 chat_router_model="open-model", chat_answer_model="other")
    assert s.chat_router_model == "open-model"
    assert s.chat_answer_model == "other"


def test_chat_intent_roles_parse():
    s = Settings(database_url="postgresql://x/x",
                 chat_intent_roles_str="performance:curator, item_facts:any")
    assert s.chat_intent_roles == {"performance": "curator", "item_facts": "any"}
    assert Settings(database_url="postgresql://x/x").chat_intent_roles == {"performance": "curator"}


def test_chat_intent_roles_invalid_role_rejected():
    with pytest.raises(ValueError):
        Settings(database_url="postgresql://x/x", chat_intent_roles_str="performance:sudo")


def test_chat_router_threshold_validated():
    with pytest.raises(ValueError):
        Settings(database_url="postgresql://x/x", chat_router_confidence_threshold=1.5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_config.py -v`
Expected: new tests FAIL (`ValidationError`/`AttributeError` — fields don't exist).

- [ ] **Step 3: Implement.** In `Settings`, after the recommender block (`rationale_top_n`, config.py:51):

```python
    # Advisor chat (multi-intent)
    chat_router_model: str = ""          # empty → defaults to triage_model
    chat_answer_model: str = ""          # empty → defaults to rationale_model
    chat_intent_roles_str: str = "performance:curator"
    chat_router_confidence_threshold: float = 0.6
    chat_context_turns: int = 5
```

In `model_post_init` (after existing validations, config.py:126):

```python
        if not self.chat_router_model:
            self.chat_router_model = self.triage_model
        if not self.chat_answer_model:
            self.chat_answer_model = self.rationale_model
        if not (0 <= self.chat_router_confidence_threshold <= 1):
            raise ValueError(f"chat_router_confidence_threshold must be in [0, 1], got {self.chat_router_confidence_threshold}")
        if self.chat_context_turns < 1:
            raise ValueError(f"chat_context_turns must be >= 1, got {self.chat_context_turns}")
        for part in _parse_csv(self.chat_intent_roles_str):
            intent, sep, role = part.partition(":")
            if not sep or role.strip() not in ("any", "curator", "admin"):
                raise ValueError(f"chat_intent_roles entries must be 'intent:any|curator|admin', got {part!r}")
```

New property next to `admin_emails` (config.py:133):

```python
    @property
    def chat_intent_roles(self) -> dict[str, str]:
        roles: dict[str, str] = {}
        for part in _parse_csv(self.chat_intent_roles_str):
            intent, _, role = part.partition(":")
            roles[intent.strip()] = role.strip()
        return roles
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v` — Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git checkout -b feature/advisor-chat
git add src/api/rcars/config.py src/api/tests/test_config.py
git commit -m "feat(chat): per-call-site chat model settings + intent role gates"
```

---

### Task 2: Session columns, `db/chat_sessions.py`, seeded fixture catalog

**Files:**
- Modify: `src/api/rcars/db/database.py` — bottom of `SCHEMA_SQL` (before the closing `"""` at line 411)
- Create: `src/api/rcars/db/chat_sessions.py`
- Create: `src/api/tests/chat_fixtures.py`
- Test: `src/api/tests/test_chat_sessions_db.py`

**Interfaces:**
- Produces (all take `pool` — pass `db.pool`):
  - `next_turn_index(pool, session_id) -> int`
  - `session_owner_ok(pool, session_id, user_email, is_admin=False) -> bool`
  - `log_chat_turn(pool, *, session_id, turn_index, user_email, query_text, results, overall_assessment, intent, envelope, scope, opted_out=False) -> int`
  - `get_session_context(pool, session_id, user_email=None, max_turns=5) -> list[dict]` — turns as `{"n": int, "intent": str, "query": str, "results": [{"id": str, "name": str}]}`
  - `get_performance_scores(pool, content_ids) -> dict[str, int]` and `get_item_workloads(pool, content_id) -> list[str]` (chat reads that have no existing accessor; live here per the zero-new-methods rule)
  - `tests/chat_fixtures.py`: `seed_chat_fixtures(db) -> dict[str, str]` (ci_name → content_id) and `fake_embedding(text) -> list[float]` (deterministic 768-dim unit vector)

- [ ] **Step 1: Add columns.** At the bottom of `SCHEMA_SQL` (after the index block, database.py:409), following the existing `ALTER TABLE ADD COLUMN IF NOT EXISTS` pattern (see line 245):

```sql
-- Advisor chat (multi-intent) — RHDPCD-599
ALTER TABLE advisor_sessions ADD COLUMN IF NOT EXISTS intent TEXT;
ALTER TABLE advisor_sessions ADD COLUMN IF NOT EXISTS envelope_json JSONB;
ALTER TABLE advisor_sessions ADD COLUMN IF NOT EXISTS scope_json JSONB;
```

- [ ] **Step 2: Write the failing tests** — `src/api/tests/test_chat_sessions_db.py`. Reuse the `db` fixture pattern from `test_db.py:11-26` (drop all tables, `Database(TEST_DB_URL)`, `create_schema()`).

```python
import os
import pytest
from rcars.db.database import Database
from rcars.db import chat_sessions

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    import psycopg
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def _log(db, session_id, turn, intent="recommend", results=None, user="u@x.com"):
    return chat_sessions.log_chat_turn(
        db.pool, session_id=session_id, turn_index=turn, user_email=user,
        query_text=f"q{turn}", results=results, overall_assessment=None,
        intent=intent, envelope={"intent": intent, "answer": "a", "blocks": []},
        scope=None)


def test_chat_columns_exist(db):
    with db.pool.connection() as conn:
        cols = {r["column_name"] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'advisor_sessions'").fetchall()}
    assert {"intent", "envelope_json", "scope_json"} <= cols


def test_turn_index_increments(db):
    assert chat_sessions.next_turn_index(db.pool, "s1") == 0
    _log(db, "s1", 0)
    assert chat_sessions.next_turn_index(db.pool, "s1") == 1


def test_ownership(db):
    _log(db, "s1", 0, user="owner@x.com")
    assert chat_sessions.session_owner_ok(db.pool, "s1", "owner@x.com")
    assert not chat_sessions.session_owner_ok(db.pool, "s1", "other@x.com")
    assert chat_sessions.session_owner_ok(db.pool, "s1", "other@x.com", is_admin=True)
    assert not chat_sessions.session_owner_ok(db.pool, "missing", "owner@x.com")


def test_context_builder_shape_and_window(db):
    for i in range(7):
        _log(db, "s1", i, results=[{"content_id": f"babylon:c{i}", "display_name": f"C{i}"}])
    ctx = chat_sessions.get_session_context(db.pool, "s1", max_turns=5)
    assert [t["n"] for t in ctx] == [2, 3, 4, 5, 6]          # window, oldest→newest
    assert ctx[-1]["results"] == [{"id": "babylon:c6", "name": "C6"}]
    assert ctx[-1]["query"] == "q6"


def test_opted_out_scrubs_envelope(db):
    chat_sessions.log_chat_turn(
        db.pool, session_id="s2", turn_index=0, user_email="u@x.com",
        query_text="secret", results=[{"content_id": "x"}], overall_assessment="a",
        intent="recommend", envelope={"answer": "secret"}, scope={"type": "prior_results"},
        opted_out=True)
    with db.pool.connection() as conn:
        row = conn.execute("SELECT * FROM advisor_sessions WHERE session_id = 's2'").fetchone()
    assert row["query_text"] is None and row["envelope_json"] is None and row["scope_json"] is None
    assert row["user_email"] != "u@x.com"
```

- [ ] **Step 3: Run to verify failure** — `python -m pytest tests/test_chat_sessions_db.py -v` → FAIL (`ModuleNotFoundError: rcars.db.chat_sessions`).

- [ ] **Step 4: Implement `src/api/rcars/db/chat_sessions.py`**

```python
"""Chat-session persistence and context building.

Follows the db/similarity.py precedent: module functions over the pool.
Hard rule: the chat layer adds zero methods to database.py.
"""
from __future__ import annotations

import hashlib
from typing import Any

from psycopg.types.json import Jsonb


def next_turn_index(pool, session_id: str) -> int:
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT COALESCE(MAX(turn_index), -1) + 1 AS next FROM advisor_sessions WHERE session_id = %s",
            (session_id,))
        return cur.fetchone()["next"]


def session_owner_ok(pool, session_id: str, user_email: str, is_admin: bool = False) -> bool:
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT user_email FROM advisor_sessions WHERE session_id = %s LIMIT 1",
            (session_id,))
        row = cur.fetchone()
    if row is None:
        return False
    return is_admin or row["user_email"] == user_email


def log_chat_turn(
    pool, *, session_id: str, turn_index: int, user_email: str | None,
    query_text: str | None, results: list[dict] | None,
    overall_assessment: str | None, intent: str | None,
    envelope: dict | None, scope: dict | None, opted_out: bool = False,
) -> int:
    # Privacy handling mirrors Database.log_advisor_session (database.py:1796)
    if opted_out:
        query_text = None
        results = None
        overall_assessment = None
        envelope = None
        scope = None
        if user_email:
            user_email = hashlib.sha256(user_email.encode()).hexdigest()[:16]
    with pool.connection() as conn:
        cur = conn.execute(
            """INSERT INTO advisor_sessions
               (session_id, turn_index, user_email, query_text, results_json,
                overall_assessment, intent, envelope_json, scope_json, opted_out)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (session_id, turn_index, user_email, query_text,
             Jsonb(results) if results is not None else None,
             overall_assessment, intent,
             Jsonb(envelope) if envelope is not None else None,
             Jsonb(scope) if scope is not None else None,
             opted_out))
        row_id = cur.fetchone()["id"]
        conn.commit()
    return row_id


def get_session_context(pool, session_id: str, user_email: str | None = None,
                        max_turns: int = 5) -> list[dict[str, Any]]:
    """The router's view: last <=max_turns turns, fixed shape, no prose."""
    sql = ("SELECT turn_index, intent, query_text, results_json "
           "FROM advisor_sessions WHERE session_id = %s")
    params: list = [session_id]
    if user_email is not None:
        sql += " AND user_email = %s"
        params.append(user_email)
    sql += " ORDER BY turn_index DESC LIMIT %s"
    params.append(max_turns)
    with pool.connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    context = []
    for row in reversed(rows):
        results = [{"id": r["content_id"], "name": r.get("display_name") or r["content_id"]}
                   for r in (row["results_json"] or []) if r.get("content_id")]
        context.append({"n": row["turn_index"], "intent": row["intent"] or "recommend",
                        "query": row["query_text"] or "", "results": results})
    return context


def get_performance_scores(pool, content_ids: list[str]) -> dict[str, int]:
    if not content_ids:
        return {}
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT content_id, performance_score FROM performance_scores WHERE content_id = ANY(%s)",
            (content_ids,)).fetchall()
    return {r["content_id"]: r["performance_score"] for r in rows}


def get_item_workloads(pool, content_id: str) -> list[str]:
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT workload_role FROM babylon_item_workloads WHERE content_id = %s ORDER BY workload_role",
            (content_id,)).fetchall()
    return [r["workload_role"] for r in rows]
```

- [ ] **Step 5: Implement `src/api/tests/chat_fixtures.py`** (used from Task 5 on; deterministic — no LLM, no embedding server, no cluster)

```python
"""Seeded fixture catalog for chat tests (also a foundation for the broader
testing backlog item — keep it generic)."""
import hashlib

from rcars.db.database import Database

FIXTURE_ITEMS = [
    # (ci_name, display_name, category, summary, products)
    ("lb2144-ansible-eda", "LB2144 Event-Driven Ansible", "Labs",
     "Hands-on lab for Event-Driven Ansible automation.", ["Ansible Automation Platform"]),
    ("lb2145-ansible-basics", "LB2145 Ansible Automation Basics", "Labs",
     "Intro lab covering Ansible playbooks and roles.", ["Ansible Automation Platform"]),
    ("ocpvirt-migration", "OpenShift Virtualization Migration", "Labs",
     "Migrate VMs from VMware to OpenShift Virtualization.", ["OpenShift Virtualization"]),
    ("ocpvirt-roadshow", "OpenShift Virtualization Roadshow", "Demos",
     "Demo of OpenShift Virtualization features.", ["OpenShift Virtualization"]),
    ("rhel-security", "RHEL Security Hardening", "Labs",
     "RHEL system hardening and compliance lab.", ["Red Hat Enterprise Linux"]),
    ("sap-hana-demo", "SAP HANA on RHEL Demo", "Demos",
     "Demo of SAP HANA deployment on RHEL.", ["Red Hat Enterprise Linux", "SAP"]),
]


def fake_embedding(text: str, prefix: str = "") -> list[float]:
    """Deterministic 768-dim unit vector from the text hash. Signature is
    monkeypatch-compatible with analyzer.generate_embedding(text, prefix=...)."""
    h = hashlib.sha256(text.encode()).digest()
    vals = [((h[i % 32] + i * 7) % 97) / 97.0 for i in range(768)]
    norm = sum(v * v for v in vals) ** 0.5
    return [v / norm for v in vals]


def seed_chat_fixtures(db: Database) -> dict[str, str]:
    ids: dict[str, str] = {}
    for ci_name, display, category, summary, products in FIXTURE_ITEMS:
        cid = db.upsert_babylon_catalog_item({
            "ci_name": ci_name, "display_name": display, "category": category,
            "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
            "showroom_url": f"https://github.com/example/{ci_name}",
            "is_prod": True, "is_published": False,
        })
        ids[ci_name] = cid
        db.upsert_showroom_analysis({
            "content_id": cid, "ci_name": ci_name, "summary": summary,
            "products_json": products, "topics_json": [category.lower()],
            "content_hash": f"hash-{ci_name}",
        })
        db.store_embedding(cid, "lab", "babylon", "summary", summary, fake_embedding(summary))

    edges = [
        (ids["lb2144-ansible-eda"], ids["lb2145-ansible-basics"], 0.91, "overlap"),
        (ids["ocpvirt-migration"], ids["ocpvirt-roadshow"], 0.87, "overlap"),
        (ids["rhel-security"], ids["sap-hana-demo"], 0.78, "related"),
    ]
    with db.pool.connection() as conn:
        for a, b, score, rel in edges:
            conn.execute(
                """INSERT INTO content_similarity (content_id_a, content_id_b, similarity_score, relationship_type)
                   VALUES (%s, %s, %s, %s) ON CONFLICT (content_id_a, content_id_b) DO NOTHING""",
                (a, b, score, rel))
        conn.execute(
            """INSERT INTO babylon_item_workloads (content_id, workload_fqcn, workload_role, workload_collection)
               VALUES (%s, %s, %s, %s) ON CONFLICT (content_id, workload_fqcn) DO NOTHING""",
            (ids["ocpvirt-migration"], "rhpds.ocpvirt.setup", "setup_virt", "rhpds.ocpvirt"))
        for ci, provisions, cost in [("lb2144-ansible-eda", 40, 12.5), ("lb2145-ansible-basics", 8, 30.0),
                                     ("ocpvirt-migration", 120, 9.0)]:
            conn.execute(
                """INSERT INTO performance_channels
                   (content_id, channel, provisions, avg_cost_per_provision, closed_amount, windowed_metrics)
                   VALUES (%s, 'rhdp', %s, %s, 50000, %s::jsonb)
                   ON CONFLICT (content_id, channel) DO NOTHING""",
                (ids[ci], provisions, cost,
                 f'{{"3m": {{"provisions": {provisions}}}, "12m": {{"provisions": {provisions * 3}}}}}'))
        conn.commit()
    return ids
```

Note: if `upsert_showroom_analysis` (database.py:891) requires other mandatory keys, supply minimal dummy values — read that method before writing the fixture.

- [ ] **Step 6: Run** — `python -m pytest tests/test_chat_sessions_db.py tests/test_db.py -v` → all PASS (test_db still green proves schema change is additive).

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/db/database.py src/api/rcars/db/chat_sessions.py src/api/tests/chat_fixtures.py src/api/tests/test_chat_sessions_db.py
git commit -m "feat(chat): session columns, chat_sessions db module, seeded fixture catalog"
```

---

### Task 3: Envelope & router models (`services/chat/models.py`)

**Files:**
- Create: `src/api/rcars/services/chat/__init__.py` (empty), `src/api/rcars/services/chat/models.py`
- Test: `src/api/tests/test_chat_models.py`

**Interfaces:**
- Produces (Pydantic v2, all later tasks import from here): `Scope`, `Clarify`, `RouterOutput`, `Chip`, `Block`, `Envelope`, `RecommendArgs`, `OverlapArgs`, `PerformanceArgs`, `ItemFactsArgs`, `INTENT_NAMES`.

- [ ] **Step 1: Write the failing tests** — `src/api/tests/test_chat_models.py`

```python
import pytest
from pydantic import ValidationError
from rcars.services.chat.models import (
    RouterOutput, Scope, Envelope, Block, Chip, PerformanceArgs, INTENT_NAMES,
)


def test_intent_enum_closed():
    with pytest.raises(ValidationError):
        RouterOutput(intent="write_jira", confidence=0.9)
    out = RouterOutput(intent="recommend", confidence=0.9)
    assert out.args == {} and out.item_refs == [] and out.scope is None


def test_scope_shapes():
    out = RouterOutput.model_validate({
        "intent": "performance", "args": {}, "confidence": 0.8,
        "scope": {"type": "ordinal", "turn": 2, "index": 2}, "item_refs": [], "clarify": None})
    assert out.scope.type == "ordinal" and out.scope.index == 2
    with pytest.raises(ValidationError):
        Scope(type="everything", turn=1)


def test_envelope_round_trip():
    env = Envelope(intent="overlap", scope_echo="Overlap for LB2144", answer="text",
                   blocks=[Block(type="overlap_table", data={"neighbors": []})],
                   suggested_followups=[Chip(label="performance of these", intent="performance",
                                             args={}, scope={"type": "prior_results", "turn": 0})])
    assert Envelope.model_validate(env.model_dump()) == env


def test_performance_args_window_closed():
    assert PerformanceArgs().window == "3m"
    with pytest.raises(ValidationError):
        PerformanceArgs(window="90d")


def test_intent_names_complete():
    assert INTENT_NAMES == ("recommend", "overlap", "performance", "item_facts", "out_of_scope")
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_chat_models.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement `src/api/rcars/services/chat/models.py`**

```python
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
```

- [ ] **Step 4: Run** — `python -m pytest tests/test_chat_models.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add src/api/rcars/services/chat src/api/tests/test_chat_models.py && git commit -m "feat(chat): typed router/envelope contracts"`

---

### Task 4: `depth` + scoped search in the recommend pipeline

**Files:**
- Modify: `src/api/rcars/db/database.py:1064` (`search_embeddings` — add `scope_content_ids` param; the only database.py change besides SCHEMA_SQL)
- Modify: `src/api/rcars/services/recommender/vector_search.py:86` (`search`)
- Modify: `src/api/rcars/services/recommender/pipeline.py:187` (`run_query`)
- Modify: `src/api/rcars/api/routes/advisor.py:19` (`QueryRequest`), `src/api/rcars/workers/recommend.py:12` (`run_recommendation`)
- Test: `src/api/tests/test_chat_depth.py`

**Interfaces:**
- Produces: `run_query(..., depth: str = "high", scope_content_ids: list[str] | None = None)` — `low` stops after vector search, `medium` after triage, `high` unchanged full pipeline. `search(..., scope_content_ids=None)`; `db.search_embeddings(..., scope_content_ids=None)`. `POST /advisor/query` accepts `depth: "low"|"medium"|"high" = "high"`.
- Omitted parameters = byte-for-byte today's behavior.

- [ ] **Step 1: Write the failing tests** — `src/api/tests/test_chat_depth.py`

```python
import asyncio
import os
import pytest
from rcars.db.database import Database
from rcars.services.recommender import pipeline
from tests.chat_fixtures import seed_chat_fixtures, fake_embedding

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL", "postgresql://rcars:dev@localhost:5432/rcars_test")


@pytest.fixture
def db():
    import psycopg
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        for row in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def _settings():
    from rcars.config import Settings
    return Settings(database_url=TEST_DB_URL, vector_cutoff=0.99)  # cutoff wide open for fake vectors


def test_scope_filter_restricts_pool(db):
    ids = seed_chat_fixtures(db)
    emb = fake_embedding("Hands-on lab for Event-Driven Ansible automation.")
    all_rows = db.search_embeddings(emb, limit=25, quality_threshold=0.0)
    scoped = db.search_embeddings(emb, limit=25, quality_threshold=0.0,
                                  scope_content_ids=[ids["rhel-security"]])
    assert len(all_rows) > 1
    assert [r["content_id"] for r in scoped] == [ids["rhel-security"]]


def test_depth_low_stops_before_triage(db, monkeypatch):
    seed_chat_fixtures(db)
    monkeypatch.setattr("rcars.services.recommender.vector_search.generate_embedding",
                        lambda text, prefix="": fake_embedding(text))

    def boom(*a, **k):
        raise AssertionError("triage must not run at depth=low")
    monkeypatch.setattr(pipeline, "triage", boom)

    state = asyncio.run(pipeline.run_query(
        "Event-Driven Ansible automation", db, _settings(), depth="low"))
    assert state.candidates  # vector results present, no triage/rationale
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_chat_depth.py -v` → FAIL (`unexpected keyword argument`).

- [ ] **Step 3: Implement.**

`database.py:1064` — add parameter `scope_content_ids: list[str] | None = None` to `search_embeddings`, and next to `ct_filter` build:

```python
        scope_filter = ""
        scope_params: list = []
        if scope_content_ids:
            scope_filter = "AND e.content_id = ANY(%s)"
            scope_params = [scope_content_ids]
```

Insert `{scope_filter}` in the CTE WHERE clause after `{zt_filter}` and add `scope_params` to the query params tuple in the same position order (follow how `ct_params`/`stage_params` are interleaved in the existing `execute` call at the end of the method).

`vector_search.py:86` — `search(..., scope_content_ids: list[str] | None = None)`, pass through to `db.search_embeddings(...)`. Skip `_resolve_ci_references` when `scope_content_ids` is set (a working set is already fixed; CI-reference expansion would break scoping).

`pipeline.py:187` — signature becomes:

```python
async def run_query(
    query: str, db: Database, settings: Settings,
    stages: list[str] | None = None, include_zt: bool = True,
    on_progress: Callable[[dict], Awaitable[None]] | None = None,
    depth: str = "high", scope_content_ids: list[str] | None = None,
) -> QueryState:
```

Pass `scope_content_ids` into the `search` call (line 254). After the vector-search emit (line 256):

```python
    if depth == "low":
        await emit({"phase": "complete", "results": len(state.candidates)})
        return state
```

After the triage emit + NO_MATCHES guard (line 281):

```python
    if depth == "medium":
        await emit({"phase": "complete",
                    "results": len([c for c in state.candidates if c.tier in ("yellow", "green")])})
        return state
```

`routes/advisor.py:19` — add `depth: Literal["low", "medium", "high"] = "high"` to `QueryRequest` (`from typing import Literal`), and pass `depth=body.depth` in the `enqueue_job` call (line 65). `workers/recommend.py:12` — add `depth: str = "high"` parameter, pass `depth=depth` to `run_query`.

- [ ] **Step 4: Run** — `python -m pytest tests/test_chat_depth.py tests/test_workers.py -v` → PASS (test_workers proves existing callers unaffected).
- [ ] **Step 5: Commit** — `git add -A src/api && git commit -m "feat(advisor): depth stop-after + scoped vector search on run_query"`

---

### Task 5: Pattern check, item resolution, resolve & verify (`router.py` deterministic parts)

**Files:**
- Create: `src/api/rcars/services/chat/router.py` (LLM `route()` added in Task 9)
- Test: `src/api/tests/test_chat_resolve.py`

**Interfaces:**
- Produces:
  - `pattern_check(message: str) -> RouterOutput | None` — narrow by design: pasted URLs → recommend; bare LB-number message (≤4 words) → item_facts.
  - `resolve_item(ref: str, db, stages=None, embed_fn=None) -> dict` — `{"item": {...}}` or `{"guesses": [row, ...]}` (≤3). Honors `ref` of the form `content_id:babylon:<name>` as an exact fast-path (used by pre-routed chips).
  - `Resolution` dataclass: `kind: Literal["execute","clarify","redirect"]`, `output: RouterOutput`, `scope_ids: list[str]`, `scope_turn: int | None`, `items: list[dict]`, `clarify: Clarify | None`, `chips: list[Chip]`, `redirect_message: str`.
  - `resolve_and_verify(output, context, db, settings, user_email) -> Resolution` — ladder steps 2–5 (spec "Validation & fallback ladder"). The router's claims are never trusted directly.

- [ ] **Step 1: Write the failing tests** — `src/api/tests/test_chat_resolve.py` (uses the Task 2 `db` fixture pattern + `seed_chat_fixtures`; import fixture/db boilerplate as in test_chat_depth.py)

```python
from rcars.services.chat import router as chat_router
from rcars.services.chat.models import RouterOutput, Scope
from rcars.config import Settings
from tests.chat_fixtures import seed_chat_fixtures, fake_embedding
# ... db fixture + TEST_DB_URL as in test_chat_depth.py ...

SETTINGS = lambda **kw: Settings(database_url=TEST_DB_URL, **kw)

CTX = [
    {"n": 0, "intent": "recommend", "query": "ansible labs",
     "results": [{"id": "babylon:lb2144-ansible-eda", "name": "LB2144 Event-Driven Ansible"},
                 {"id": "babylon:lb2145-ansible-basics", "name": "LB2145 Ansible Automation Basics"}]},
    {"n": 1, "intent": "clarify", "query": "", "results": []},
]


def test_pattern_check_url_and_lb():
    out = chat_router.pattern_check("https://summit.example.com/cfp what fits?")
    assert out.intent == "recommend" and out.confidence == 1.0
    out = chat_router.pattern_check("LB2144")
    assert out.intent == "item_facts" and out.item_refs == ["LB2144"]
    assert chat_router.pattern_check("what overlaps with LB2144 and why?") is None
    assert chat_router.pattern_check("find me an ansible lab") is None


def test_scope_prior_results_resolves_and_skips_clarify_turns(db):
    seed_chat_fixtures(db)
    out = RouterOutput(intent="performance", confidence=0.9,
                       scope=Scope(type="prior_results", turn=0))
    res = chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "execute"
    assert res.scope_ids == ["babylon:lb2144-ansible-eda", "babylon:lb2145-ansible-basics"]


def test_scope_ordinal(db):
    seed_chat_fixtures(db)
    out = RouterOutput(intent="item_facts", confidence=0.9,
                       scope=Scope(type="ordinal", turn=0, index=2))
    res = chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "execute"
    assert [i["content_id"] for i in res.items] == ["babylon:lb2145-ansible-basics"]


def test_stale_scope_clarifies(db):
    out = RouterOutput(intent="performance", confidence=0.9,
                       scope=Scope(type="prior_results", turn=99))
    res = chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "clarify" and res.chips


def test_unresolvable_ref_offers_guesses(db, monkeypatch):
    seed_chat_fixtures(db)
    monkeypatch.setattr(chat_router, "generate_embedding",
                        lambda text, prefix="": fake_embedding(text))
    out = RouterOutput(intent="overlap", confidence=0.9, item_refs=["the quantum blockchain lab"])
    res = chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "clarify"
    assert res.clarify and "mean" in res.clarify.question.lower()
    assert 0 < len(res.chips) <= 3


def test_lb_ref_resolves(db):
    ids = seed_chat_fixtures(db)
    out = RouterOutput(intent="overlap", confidence=0.9, item_refs=["LB2144"])
    res = chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "execute"
    assert res.items[0]["content_id"] == ids["lb2144-ansible-eda"]


def test_low_confidence_clarifies(db):
    out = RouterOutput(intent="recommend", confidence=0.3,
                       clarify={"question": "Lab or demo?", "options": ["Lab", "Demo"]})
    res = chat_router.resolve_and_verify(out, CTX, db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "clarify" and res.clarify.question == "Lab or demo?"


def test_role_gate_redirects(db):
    out = RouterOutput(intent="performance", confidence=0.9,
                       scope=Scope(type="prior_results", turn=0))
    res = chat_router.resolve_and_verify(out, CTX, db, SETTINGS(), "notcurator@x.com")
    assert res.kind == "redirect" and "curator" in res.redirect_message.lower()
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_chat_resolve.py -v` → FAIL.

- [ ] **Step 3: Implement `src/api/rcars/services/chat/router.py`** (deterministic half)

```python
"""Routing: pattern check, router LLM call (Task 9), resolve & verify ladder."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

import structlog

from rcars.config import Settings
from rcars.db.database import Database
from rcars.services.analyzer import generate_embedding
from rcars.services.chat.models import Chip, Clarify, RouterOutput
from rcars.services.recommender.pipeline import _extract_urls
from rcars.services.recommender.vector_search import _STOP_WORDS

logger = structlog.get_logger(component="chat")

_LB_RE = re.compile(r"\bLB(\d{3,4})\b", re.IGNORECASE)


def pattern_check(message: str) -> RouterOutput | None:
    """Deterministic pre-router. Narrow by design — the LLM router is the main path."""
    urls, _ = _extract_urls(message)
    if urls:
        return RouterOutput(intent="recommend", args={"search_query": message}, confidence=1.0)
    m = _LB_RE.search(message)
    if m and len(message.split()) <= 4 and "?" not in message:
        ref = m.group(0).upper()
        return RouterOutput(intent="item_facts", args={"item_ref": ref},
                            item_refs=[ref], confidence=1.0)
    return None


def resolve_item(ref: str, db: Database, stages: list[str] | None = None,
                 embed_fn=None) -> dict:
    """Catalog resolution: LB regex → name keyword overlap → embedding guesses.
    The router's belief that an item exists is never trusted."""
    stages = stages or ["prod"]
    if ref.startswith("content_id:"):  # pre-routed chip fast-path
        item = db.get_babylon_item(ref.removeprefix("content_id:"))
        if item:
            return {"item": item}
    m = _LB_RE.search(ref)
    if m:
        item = db.find_catalog_item_by_display_name_prefix(f"LB{m.group(1)}%", stages=stages)
        if item:
            return {"item": item}
    words = {w.lower() for w in re.findall(r"[a-zA-Z]{3,}", ref)} - _STOP_WORDS
    if len(words) >= 2:
        item = db.find_catalog_item_by_keyword_overlap(words, stages=stages, min_overlap=3)
        if item:
            return {"item": item}
    embed = embed_fn or generate_embedding
    guesses = db.search_embeddings(embed(ref, prefix="search_query"),
                                   limit=3, stages=stages)
    return {"guesses": guesses}


@dataclass
class Resolution:
    kind: Literal["execute", "clarify", "redirect"]
    output: RouterOutput
    scope_ids: list[str] = field(default_factory=list)
    scope_turn: int | None = None
    items: list[dict] = field(default_factory=list)
    clarify: Clarify | None = None
    chips: list[Chip] = field(default_factory=list)
    redirect_message: str = ""


def _result_turns(context: list[dict]) -> list[dict]:
    """Turns that produced results — clarification turns are skipped when resolving."""
    return [t for t in context if t.get("results") and t.get("intent") != "clarify"]


def _turn_chips(context: list[dict], output: RouterOutput) -> list[Chip]:
    return [Chip(label=f'Use results from "{t["query"][:40]}" ({len(t["results"])} items)',
                 intent=output.intent, args=output.args,
                 scope={"type": "prior_results", "turn": t["n"]})
            for t in _result_turns(context)[-3:]]


def resolve_and_verify(output: RouterOutput, context: list[dict], db: Database,
                       settings: Settings, user_email: str) -> Resolution:
    # Ladder 2: symbolic scope → content_ids from session turns
    scope_ids: list[str] = []
    scope_turn: int | None = None
    items: list[dict] = []
    if output.scope is not None:
        turn = next((t for t in _result_turns(context) if t["n"] == output.scope.turn), None)
        if turn is None:
            return Resolution(kind="clarify", output=output,
                              clarify=Clarify(question="Which results should I use?"),
                              chips=_turn_chips(context, output))
        scope_turn = turn["n"]
        if output.scope.type == "ordinal":
            idx = (output.scope.index or 1) - 1
            if not (0 <= idx < len(turn["results"])):
                return Resolution(kind="clarify", output=output,
                                  clarify=Clarify(question=f"That turn has {len(turn['results'])} items — which one?"),
                                  chips=[Chip(label=r["name"], intent=output.intent, args=output.args,
                                              scope={"type": "ordinal", "turn": turn["n"], "index": i + 1})
                                         for i, r in enumerate(turn["results"][:5])])
            picked = turn["results"][idx]
            item = db.get_babylon_item(picked["id"]) or {"content_id": picked["id"],
                                                         "display_name": picked["name"]}
            items = [item]
            scope_ids = [picked["id"]]
        else:
            scope_ids = [r["id"] for r in turn["results"]]

    # Ladder 3: item refs → catalog resolution ("did you mean…" on miss)
    for ref in output.item_refs:
        resolved = resolve_item(ref, db)
        if "item" in resolved:
            items.append(resolved["item"])
        else:
            chips = [Chip(label=g.get("display_name", g["content_id"]), intent=output.intent,
                          args={**output.args, "item_ref": f"content_id:{g['content_id']}"})
                     for g in resolved["guesses"][:3]]
            return Resolution(kind="clarify", output=output,
                              clarify=Clarify(question=f'I couldn\'t find "{ref}". Did you mean:'),
                              chips=chips)

    # Ladder 4: confidence gate → router's own clarify question
    if output.confidence < settings.chat_router_confidence_threshold and output.clarify:
        chips = [Chip(label=opt, intent=output.intent, args={**output.args, "search_query": opt})
                 for opt in output.clarify.options[:4]]
        return Resolution(kind="clarify", output=output, clarify=output.clarify, chips=chips)

    # Ladder 5: role check on the resolved intent (demand is logged before opening up)
    required = settings.chat_intent_roles.get(output.intent, "any")
    allowed = (required == "any"
               or (required == "curator" and (settings.is_curator(user_email) or settings.is_admin(user_email)))
               or (required == "admin" and settings.is_admin(user_email)))
    if not allowed:
        logger.info("chat_role_redirect", component="chat", intent=output.intent,
                    required_role=required, user=user_email)
        return Resolution(kind="redirect", output=output,
                          redirect_message=(f"Performance and usage questions are currently "
                                            f"available to {required}s. Ask a curator, or use the "
                                            f"Browse page for catalog details."))

    return Resolution(kind="execute", output=output, scope_ids=scope_ids,
                      scope_turn=scope_turn, items=items)
```

- [ ] **Step 4: Run** — `python -m pytest tests/test_chat_resolve.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add src/api/rcars/services/chat/router.py src/api/tests/test_chat_resolve.py && git commit -m "feat(chat): pattern check, catalog resolution, resolve-and-verify ladder"`

---

### Task 6: Evidence-pack builder (`services/chat/evidence.py`)

**Files:**
- Create: `src/api/rcars/services/chat/evidence.py`
- Test: `src/api/tests/test_chat_evidence.py`

**Interfaces:**
- Produces: `build_evidence_pack(db, anchor_ids: list[str]) -> list[dict]` — one hop over `content_similarity` + shared workloads, top-k by edge score, code constants `MAX_NEIGHBORS = 15`, ≤6 fields per neighbor. Empty list on no anchors/edges. **Only feeds the answer narrative — never adds, removes, or reorders results.**

- [ ] **Step 1: Write the failing tests** — `src/api/tests/test_chat_evidence.py` (db fixture + `seed_chat_fixtures` as before)

```python
from rcars.services.chat.evidence import build_evidence_pack, MAX_NEIGHBORS


def test_pack_bounded_and_sorted(db):
    ids = seed_chat_fixtures(db)
    pack = build_evidence_pack(db, [ids["lb2144-ansible-eda"]])
    assert 1 <= len(pack) <= MAX_NEIGHBORS
    assert pack[0]["name"] == "LB2145 Ansible Automation Basics"
    assert pack[0]["similarity_pct"] == 91
    assert set(pack[0]) <= {"anchor", "name", "stage", "similarity_pct", "relationship",
                            "products", "provisions"}


def test_pack_includes_shared_workload_note(db):
    ids = seed_chat_fixtures(db)
    # ocpvirt-roadshow shares no workload row; add one so the pair shares setup_virt
    with db.pool.connection() as conn:
        conn.execute(
            """INSERT INTO babylon_item_workloads (content_id, workload_fqcn, workload_role, workload_collection)
               VALUES (%s, 'rhpds.ocpvirt.setup', 'setup_virt', 'rhpds.ocpvirt')
               ON CONFLICT (content_id, workload_fqcn) DO NOTHING""",
            (ids["ocpvirt-roadshow"],))
        conn.commit()
    pack = build_evidence_pack(db, [ids["ocpvirt-migration"]])
    shared = [p for p in pack if p.get("relationship") == "shared_workload"]
    assert shared and shared[0]["name"] == "OpenShift Virtualization Roadshow"


def test_empty_anchor_empty_pack(db):
    seed_chat_fixtures(db)
    assert build_evidence_pack(db, []) == []
    assert build_evidence_pack(db, ["babylon:nonexistent"]) == []
```

- [ ] **Step 2: Run to verify failure** → FAIL (module missing).

- [ ] **Step 3: Implement `src/api/rcars/services/chat/evidence.py`**

```python
"""Evidence pack: v1 graph expansion — one hop, code-driven, bounded.

The budget affects only the answer narrative's context; an empty pack yields
identical results with a blander narrative. Caps are code constants, not config.
"""
from __future__ import annotations

from rcars.db.database import Database

MAX_NEIGHBORS = 15


def build_evidence_pack(db: Database, anchor_ids: list[str]) -> list[dict]:
    if not anchor_ids:
        return []
    with db.pool.connection() as conn:
        sim_rows = conn.execute(
            """SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.relationship_type,
                      ce.display_name, bi.stage, sa.products_json,
                      (SELECT pc.provisions FROM performance_channels pc
                       WHERE pc.content_id = ce.content_id AND pc.channel = 'rhdp') AS provisions
               FROM content_similarity cs
               JOIN content_entities ce ON ce.content_id =
                    CASE WHEN cs.content_id_a = ANY(%(ids)s) THEN cs.content_id_b
                         ELSE cs.content_id_a END
               LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
               LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
               WHERE cs.content_id_a = ANY(%(ids)s) OR cs.content_id_b = ANY(%(ids)s)
               ORDER BY cs.similarity_score DESC
               LIMIT %(cap)s""",
            {"ids": anchor_ids, "cap": MAX_NEIGHBORS}).fetchall()

        wl_rows = conn.execute(
            """SELECT w1.content_id AS anchor, w2.content_id AS other,
                      ce.display_name, bi.stage, w1.workload_role
               FROM babylon_item_workloads w1
               JOIN babylon_item_workloads w2
                 ON w1.workload_fqcn = w2.workload_fqcn AND w1.content_id <> w2.content_id
               JOIN content_entities ce ON ce.content_id = w2.content_id
               LEFT JOIN babylon_items bi ON bi.content_id = w2.content_id
               WHERE w1.content_id = ANY(%(ids)s)
               LIMIT 20""",
            {"ids": anchor_ids}).fetchall()

    pack: list[dict] = []
    seen: set[str] = set()
    for r in sim_rows:
        other = r["content_id_b"] if r["content_id_a"] in anchor_ids else r["content_id_a"]
        anchor = r["content_id_a"] if r["content_id_a"] in anchor_ids else r["content_id_b"]
        seen.add(other)
        pack.append({"anchor": anchor, "name": r["display_name"], "stage": r["stage"],
                     "similarity_pct": round(r["similarity_score"] * 100),
                     "relationship": r["relationship_type"],
                     "products": (r["products_json"] or [])[:3],
                     "provisions": r["provisions"]})
    for r in wl_rows:
        if len(pack) >= MAX_NEIGHBORS:
            break
        if r["other"] in seen or r["other"] in anchor_ids:
            continue
        seen.add(r["other"])
        pack.append({"anchor": r["anchor"], "name": r["display_name"], "stage": r["stage"],
                     "similarity_pct": None, "relationship": "shared_workload",
                     "products": [r["workload_role"]], "provisions": None})
    return pack[:MAX_NEIGHBORS]
```

Note: `products_json` may come back as a JSON string depending on the psycopg row factory — if the first test fails on that, `json.loads` it when `isinstance(..., str)` (same guard as `workers/recommend.py:66`).

- [ ] **Step 4: Run** — `python -m pytest tests/test_chat_evidence.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add src/api/rcars/services/chat/evidence.py src/api/tests/test_chat_evidence.py && git commit -m "feat(chat): bounded one-hop evidence pack"`

---

### Task 7: Candidate serialization extraction + the four handlers

**Files:**
- Create: `src/api/rcars/services/recommender/serialize.py` (extract from `workers/recommend.py:36-76` — DRY, both chat and recommend worker use it)
- Modify: `src/api/rcars/workers/recommend.py` (use the extracted function)
- Create: `src/api/rcars/services/chat/handlers.py`
- Test: `src/api/tests/test_chat_handlers.py`

**Interfaces:**
- Produces:
  - `serialize.candidates_with_performance(state, db) -> list[dict]` — exactly the dict shape currently built inline in `run_recommendation` (content_id, ci_name, display_name, tier, relevance_score, vector_similarity_pct, stage, catalog_namespace, duration_min, duration_source, learning_objectives, why_it_fits, how_to_use, suggested_format, duration_notes, caveats, provisions_quarter, avg_cost_per_provision, sales_impact).
  - `HandlerResult` dataclass: `blocks: list[Block]`, `scaffold_facts: dict`, `anchor_ids: list[str]`, `session_results: list[dict]` (goes to `results_json` — must contain `content_id` + `display_name` so later scopes resolve).
  - `async handle_recommend(res, db, settings, stages, include_zt, on_progress) -> HandlerResult`
  - `async handle_overlap(res, db, settings, stages, include_zt, on_progress) -> HandlerResult`
  - `async handle_performance(...)`, `async handle_item_facts(...)` — same signature (uniform for the registry; sync work runs inline, they only await `run_query`).
- Consumes: `Resolution` (Task 5), `run_query` depth/scope (Task 4), `get_similar_items` (`db/similarity.py:131`), `db.get_performance_channels` (database.py:2064), `chat_sessions.get_performance_scores` / `get_item_workloads` (Task 2), `compute_sales_impact` (`services/reporting_sync.py`).

- [ ] **Step 1: Extract serialization.** Move the `candidates_json` construction and the performance-enrichment loop from `workers/recommend.py:36-76` verbatim into:

```python
# src/api/rcars/services/recommender/serialize.py
"""Result serialization shared by the recommend worker and the chat layer."""
from __future__ import annotations

import json

from rcars.services.reporting_sync import compute_sales_impact


def candidates_with_performance(state, db) -> list[dict]:
    candidates_json = [ ... exact list-comp from workers/recommend.py:36-56 ... ]
    for candidate in candidates_json:
        ... exact enrichment loop from workers/recommend.py:60-76 ...
    return candidates_json
```

Replace the inlined code in `run_recommendation` with `candidates_json = candidates_with_performance(state, wctx.db)`.

Run: `python -m pytest tests/test_workers.py -v` → PASS before continuing. Commit: `git commit -am "refactor(recommender): extract candidate serialization"`.

- [ ] **Step 2: Write the failing handler tests** — `src/api/tests/test_chat_handlers.py` (db fixture + fixtures as before). These are the "integration — deterministic layer" tier: real SQL, no LLM (recommend handler is covered by the Task 11 turn test; here test the three pure-SQL handlers).

```python
import asyncio
from rcars.services.chat import handlers
from rcars.services.chat.models import RouterOutput
from rcars.services.chat.router import Resolution


async def _noop(data):
    pass


def _res(intent, ids=None, items=None, args=None):
    return Resolution(kind="execute",
                      output=RouterOutput(intent=intent, confidence=1.0, args=args or {}),
                      scope_ids=ids or [], items=items or [])


def test_overlap_handler(db):
    ids = seed_chat_fixtures(db)
    anchor = db.get_babylon_item(ids["lb2144-ansible-eda"])
    r = asyncio.run(handlers.handle_overlap(
        _res("overlap", items=[anchor]), db, _settings(), ["prod"], True, _noop))
    types = [b.type for b in r.blocks]
    assert types == ["item_card", "overlap_table"]
    neighbors = r.blocks[1].data["neighbors"]
    assert neighbors[0]["display_name"] == "LB2145 Ansible Automation Basics"
    assert neighbors[0]["similarity_pct"] == 91
    assert neighbors[0]["why"] is None            # overlap honesty: no invented why
    assert r.anchor_ids == [ids["lb2144-ansible-eda"]]
    assert r.session_results[0]["content_id"] == ids["lb2145-ansible-basics"]


def test_performance_handler_rows_match_scope(db):
    ids = seed_chat_fixtures(db)
    scope = [ids["lb2144-ansible-eda"], ids["lb2145-ansible-basics"]]
    r = asyncio.run(handlers.handle_performance(
        _res("performance", ids=scope), db, _settings(), ["prod"], True, _noop))
    rows = r.blocks[0].data["rows"]
    assert [row["content_id"] for row in rows] == scope
    assert rows[0]["provisions"] == 40
    assert r.blocks[0].data["window"] == "3m"
    assert rows[0]["score"] is None               # not retirement-flavored


def test_item_facts_handler(db):
    ids = seed_chat_fixtures(db)
    item = db.get_babylon_item(ids["ocpvirt-migration"])
    r = asyncio.run(handlers.handle_item_facts(
        _res("item_facts", items=[item]), db, _settings(), ["prod"], True, _noop))
    card = r.blocks[0].data
    assert r.blocks[0].type == "item_card"
    assert card["display_name"] == "OpenShift Virtualization Migration"
    assert "setup_virt" in card["workloads"]
    assert card["neighbors"][0]["display_name"] == "OpenShift Virtualization Roadshow"
```

- [ ] **Step 3: Run to verify failure** → FAIL.

- [ ] **Step 4: Implement `src/api/rcars/services/chat/handlers.py`**

```python
"""Fixed tool plans per intent. Read-only. If any handler outgrows ~100 lines,
graduate it to handlers/<intent>.py."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from rcars.config import Settings
from rcars.db.database import Database
from rcars.db.chat_sessions import get_item_workloads, get_performance_scores
from rcars.db.similarity import get_similar_items
from rcars.services.chat.models import Block, ItemFactsArgs, PerformanceArgs, RecommendArgs
from rcars.services.chat.router import Resolution
from rcars.services.recommender.pipeline import run_query
from rcars.services.recommender.serialize import candidates_with_performance
from rcars.services.reporting_sync import compute_sales_impact


@dataclass
class HandlerResult:
    blocks: list[Block]
    scaffold_facts: dict
    anchor_ids: list[str] = field(default_factory=list)
    session_results: list[dict] = field(default_factory=list)


def _item_card(db: Database, item: dict) -> dict:
    cid = item["content_id"]
    analysis = db.get_showroom_analysis(cid) or {}
    lo = analysis.get("learning_objectives_json") or {}
    return {
        "content_id": cid, "ci_name": item.get("ci_name"),
        "display_name": item.get("display_name", cid), "stage": item.get("stage"),
        "content_type": (db.get_content_entity(cid) or {}).get("content_type"),
        "summary": analysis.get("summary"),
        "products": analysis.get("products_json") or [],
        "modules": (lo.get("stated") if isinstance(lo, dict) else []) or [],
        "workloads": get_item_workloads(db.pool, cid),
        "neighbors": [],
    }


async def handle_recommend(res: Resolution, db: Database, settings: Settings,
                           stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    args = RecommendArgs.model_validate(res.output.args)
    query = args.search_query or " ".join(str(v) for v in args.constraints.values())
    # scoped working-set questions run medium; full-catalog turns run the full pipeline
    depth = "medium" if res.scope_ids else "high"
    state = await run_query(query, db, settings, stages=stages, include_zt=include_zt,
                            on_progress=on_progress, depth=depth,
                            scope_content_ids=res.scope_ids or None)
    cards = candidates_with_performance(state, db)
    green = [c for c in cards if c["tier"] == "green"]
    return HandlerResult(
        blocks=[Block(type="rec_cards", data={"candidates": cards,
                                              "content_gaps": state.content_gaps})],
        scaffold_facts={"result_count": len(cards), "green_count": len(green),
                        "assessment": state.overall_assessment,
                        "top": [c["display_name"] for c in (green or cards)[:3]],
                        "scoped": bool(res.scope_ids)},
        anchor_ids=[c["content_id"] for c in (green or cards)[:5]],
        session_results=cards)


async def handle_overlap(res: Resolution, db: Database, settings: Settings,
                         stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    anchors = res.items or [db.get_babylon_item(cid) or {"content_id": cid, "display_name": cid}
                            for cid in res.scope_ids]
    anchor = anchors[0]
    anchor_analysis = db.get_showroom_analysis(anchor["content_id"]) or {}
    anchor_products = set(anchor_analysis.get("products_json") or [])
    raw = get_similar_items(db.pool, anchor["content_id"],
                            min_score=settings.similarity_storage_threshold,
                            relationship_type="all")
    neighbors = []
    for n in raw:
        n_products = set((db.get_showroom_analysis(n["content_id"]) or {}).get("products_json") or [])
        neighbors.append({
            "content_id": n["content_id"], "display_name": n["display_name"],
            "stage": n.get("stage"), "similarity_pct": round(n["similarity_score"] * 100),
            "relationship_type": n.get("relationship_type", "overlap"),
            "shared_products": sorted(anchor_products & n_products),
            "why": None,  # populated by the future overlap-summary batch job
        })
    return HandlerResult(
        blocks=[Block(type="item_card", data=_item_card(db, anchor)),
                Block(type="overlap_table", data={"anchor": {"content_id": anchor["content_id"],
                                                             "display_name": anchor.get("display_name")},
                                                  "neighbors": neighbors})],
        scaffold_facts={"anchor": anchor.get("display_name"), "neighbor_count": len(neighbors),
                        "top_similarity": neighbors[0]["similarity_pct"] if neighbors else None},
        anchor_ids=[anchor["content_id"]],
        session_results=[{"content_id": n["content_id"], "display_name": n["display_name"]}
                         for n in neighbors])


async def handle_performance(res: Resolution, db: Database, settings: Settings,
                             stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    args = PerformanceArgs.model_validate(res.output.args)
    ids = res.scope_ids or [i["content_id"] for i in res.items]
    scores = get_performance_scores(db.pool, ids) if args.retirement_flavored else {}
    rows = []
    for cid in ids:
        entity = db.get_content_entity(cid) or {}
        channels = db.get_performance_channels(cid) or []
        rhdp = next((ch for ch in channels if ch["channel"] == "rhdp"), None) or {}
        wm = rhdp.get("windowed_metrics") or {}
        if isinstance(wm, str):
            wm = json.loads(wm)
        w = wm.get(args.window) or {}
        rows.append({"content_id": cid, "display_name": entity.get("display_name", cid),
                     "provisions": w.get("provisions", 0),
                     "cost_per_provision": float(rhdp.get("avg_cost_per_provision") or 0) or None,
                     "sales_impact": compute_sales_impact(float(rhdp.get("closed_amount") or 0))
                                     if rhdp else None,
                     "score": scores.get(cid)})
    rows.sort(key=lambda r: -(r["provisions"] or 0))
    return HandlerResult(
        blocks=[Block(type="performance_table",
                      data={"window": args.window, "rows": rows,
                            "retirement_flavored": args.retirement_flavored})],
        scaffold_facts={"item_count": len(rows), "window": args.window,
                        "best": rows[0]["display_name"] if rows else None,
                        "best_provisions": rows[0]["provisions"] if rows else None},
        anchor_ids=ids[:5],
        session_results=[{"content_id": r["content_id"], "display_name": r["display_name"]}
                         for r in rows])


async def handle_item_facts(res: Resolution, db: Database, settings: Settings,
                            stages: list[str], include_zt: bool, on_progress) -> HandlerResult:
    item = res.items[0]
    card = _item_card(db, item)
    card["neighbors"] = [
        {"content_id": n["content_id"], "display_name": n["display_name"],
         "similarity_pct": round(n["similarity_score"] * 100)}
        for n in get_similar_items(db.pool, item["content_id"],
                                   min_score=settings.similarity_threshold)[:5]]
    return HandlerResult(
        blocks=[Block(type="item_card", data=card)],
        scaffold_facts={"display_name": card["display_name"], "stage": card["stage"],
                        "products": card["products"], "neighbor_count": len(card["neighbors"])},
        anchor_ids=[item["content_id"]],
        session_results=[{"content_id": item["content_id"],
                          "display_name": card["display_name"]}])
```

- [ ] **Step 5: Run** — `python -m pytest tests/test_chat_handlers.py tests/test_workers.py -v` → PASS.
- [ ] **Step 6: Commit** — `git add -A src/api && git commit -m "feat(chat): intent handlers with fixed tool plans"`

---

### Task 8: Intent registry + router prompt assembly (`registry.py`)

**Files:**
- Create: `src/api/rcars/services/chat/registry.py`
- Test: `src/api/tests/test_chat_registry.py`

**Interfaces:**
- Produces:
  - `IntentSpec` (frozen dataclass): `name`, `description`, `args_model`, `handler` (None for `out_of_scope`), `block_types: tuple`, `followups: tuple[dict, ...]` (`{"label", "intent", "scope_from": "results"|"anchor"|None}`), `prompt_fragment: str`, `examples: tuple[dict, ...]`.
  - `INTENTS: dict[str, IntentSpec]` — adding an intent = one new entry here (+ golden cases).
  - `build_router_prompt(context: list[dict]) -> tuple[str, str]` — `(system_prompt, user_template)` where user_template has a `{message}` placeholder; assembled from registry descriptions + few-shot examples so a new intent automatically teaches the router.
  - `followup_chips(intent: str, turn_index: int, anchor: dict | None) -> list[Chip]`.

- [ ] **Step 1: Write the failing tests** — `src/api/tests/test_chat_registry.py`

```python
import json
from rcars.services.chat import registry
from rcars.services.chat.models import INTENT_NAMES, RouterOutput


def test_registry_complete():
    assert set(registry.INTENTS) == set(INTENT_NAMES)
    for name, spec in registry.INTENTS.items():
        assert spec.description and spec.prompt_fragment
        assert len(spec.examples) >= 2
        if name != "out_of_scope":
            assert spec.handler is not None
            assert spec.block_types
            assert spec.followups


def test_examples_validate_as_router_output():
    for spec in registry.INTENTS.values():
        for ex in spec.examples:
            out = RouterOutput.model_validate(ex["output"])
            assert out.intent == spec.name


def test_prompt_contains_every_intent_and_context():
    system, user = registry.build_router_prompt(
        [{"n": 0, "intent": "recommend", "query": "ansible",
          "results": [{"id": "babylon:x", "name": "X"}]}])
    for name in INTENT_NAMES:
        assert name in system
    assert "turn 0" in user.lower() or '"n": 0' in user
    assert "{message}" in user


def test_followup_chips_are_pre_routed():
    chips = registry.followup_chips("recommend", turn_index=3, anchor=None)
    assert chips and all(c.intent in INTENT_NAMES for c in chips)
    assert any(c.scope == {"type": "prior_results", "turn": 3} for c in chips)
```

- [ ] **Step 2: Run to verify failure** → FAIL.

- [ ] **Step 3: Implement `src/api/rcars/services/chat/registry.py`.** Chips per the spec table (recommend → "overlap for these · performance of these · about #1"; overlap → "about item · performance of these"; performance → "recommend from these · about item"; item_facts → "overlap with this · performance of this").

```python
"""Declarative intent registry. Adding an intent = one entry here
(+ frontend block renderer if it introduces a new block type + golden cases)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from rcars.services.chat import handlers
from rcars.services.chat.models import (
    Chip, ItemFactsArgs, OverlapArgs, PerformanceArgs, RecommendArgs,
)


@dataclass(frozen=True)
class IntentSpec:
    name: str
    description: str
    args_model: type
    handler: Callable | None
    block_types: tuple[str, ...]
    followups: tuple[dict, ...]
    prompt_fragment: str
    examples: tuple[dict, ...]


INTENTS: dict[str, IntentSpec] = {
    "recommend": IntentSpec(
        name="recommend",
        description="Find content for an event, audience, or topic. The answer is content to go use.",
        args_model=RecommendArgs, handler=handlers.handle_recommend,
        block_types=("rec_cards",),
        followups=({"label": "Overlap for these", "intent": "overlap", "scope_from": "results"},
                   {"label": "Performance of these", "intent": "performance", "scope_from": "results"},
                   {"label": "About #1", "intent": "item_facts", "scope_from": "ordinal1"}),
        prompt_fragment=("recommend: the user wants content suggestions (find/suggest/need a lab or "
                         "demo for X). Composite asks like 'high-usage Ansible for an EDA demo' are "
                         "recommend with constraints.performance='high_usage', NOT performance."),
        examples=(
            {"message": "I need a 2-hour OpenShift virtualization lab for platform engineers",
             "output": {"intent": "recommend", "args": {"search_query": "2-hour OpenShift virtualization lab for platform engineers"},
                        "scope": None, "item_refs": [], "confidence": 0.95, "clarify": None}},
            {"message": "high-usage Ansible content for an EDA demo",
             "output": {"intent": "recommend",
                        "args": {"search_query": "Ansible content for an EDA demo",
                                 "constraints": {"performance": "high_usage"}},
                        "scope": None, "item_refs": [], "confidence": 0.85, "clarify": None}},
        )),
    "overlap": IntentSpec(
        name="overlap",
        description="What overlaps with / is similar to a named item or prior results.",
        args_model=OverlapArgs, handler=handlers.handle_overlap,
        block_types=("item_card", "overlap_table"),
        followups=({"label": "About this item", "intent": "item_facts", "scope_from": "anchor"},
                   {"label": "Performance of these", "intent": "performance", "scope_from": "results"}),
        prompt_fragment="overlap: similarity/overlap/duplication questions about a specific item or set.",
        examples=(
            {"message": "what overlaps with LB2144?",
             "output": {"intent": "overlap", "args": {"item_ref": "LB2144"}, "scope": None,
                        "item_refs": ["LB2144"], "confidence": 0.95, "clarify": None}},
            {"message": "is the SAP lab similar to anything else we have?",
             "output": {"intent": "overlap", "args": {"item_ref": "the SAP lab"}, "scope": None,
                        "item_refs": ["the SAP lab"], "confidence": 0.8, "clarify": None}},
        )),
    "performance": IntentSpec(
        name="performance",
        description="How is X performing / which of these performed best. The answer is a fact about the portfolio (table), not content to use.",
        args_model=PerformanceArgs, handler=handlers.handle_performance,
        block_types=("performance_table",),
        followups=({"label": "Recommend from these", "intent": "recommend", "scope_from": "results"},
                   {"label": "About the top item", "intent": "item_facts", "scope_from": "ordinal1"}),
        prompt_fragment=("performance: usage/provisions/cost/sales questions. Set "
                         "retirement_flavored=true only when the user mentions retirement."),
        examples=(
            {"message": "which of these performed best?",
             "output": {"intent": "performance", "args": {}, "scope": {"type": "prior_results", "turn": 0},
                        "item_refs": [], "confidence": 0.9, "clarify": None}},
            {"message": "how are our Ansible labs doing on provisions this year?",
             "output": {"intent": "performance", "args": {"window": "12m"}, "scope": None,
                        "item_refs": ["Ansible labs"], "confidence": 0.75, "clarify": None}},
        )),
    "item_facts": IntentSpec(
        name="item_facts",
        description="What is X / what's in it — one item's summary, modules, products, workloads.",
        args_model=ItemFactsArgs, handler=handlers.handle_item_facts,
        block_types=("item_card",),
        followups=({"label": "Overlap with this", "intent": "overlap", "scope_from": "anchor"},
                   {"label": "Performance of this", "intent": "performance", "scope_from": "anchor"}),
        prompt_fragment="item_facts: describe one specific item (what is / tell me about / what's in).",
        examples=(
            {"message": "what is the SAP HANA demo about?",
             "output": {"intent": "item_facts", "args": {"item_ref": "SAP HANA demo"}, "scope": None,
                        "item_refs": ["SAP HANA demo"], "confidence": 0.9, "clarify": None}},
            {"message": "tell me about the second one",
             "output": {"intent": "item_facts", "args": {}, "scope": {"type": "ordinal", "turn": 0, "index": 2},
                        "item_refs": [], "confidence": 0.85, "clarify": None}},
        )),
    "out_of_scope": IntentSpec(
        name="out_of_scope",
        description="Not about RHDP content, overlap, performance, or item facts.",
        args_model=RecommendArgs, handler=None, block_types=("notice",), followups=(),
        prompt_fragment="out_of_scope: anything RCARS cannot answer from its catalog and metrics.",
        examples=(
            {"message": "what's the weather in Raleigh?",
             "output": {"intent": "out_of_scope", "args": {}, "scope": None, "item_refs": [],
                        "confidence": 0.95, "clarify": None}},
            {"message": "open a Jira to retire LB2144",
             "output": {"intent": "out_of_scope", "args": {}, "scope": None, "item_refs": [],
                        "confidence": 0.9, "clarify": None}},
        )),
}


def build_router_prompt(context: list[dict]) -> tuple[str, str]:
    intent_docs = "\n".join(f"- {s.prompt_fragment}" for s in INTENTS.values())
    shots = "\n".join(
        f"Message: {ex['message']}\nOutput: {json.dumps(ex['output'])}"
        for s in INTENTS.values() for ex in s.examples)
    system = (
        "You are the intent router for RCARS, the RHDP content advisory system. "
        "Classify the user's message into exactly one intent and emit ONLY a JSON object "
        "with keys: intent, args, scope, item_refs, confidence, clarify.\n"
        f"Intents:\n{intent_docs}\n"
        "Rules: scope refers to a prior turn by its number n; use type 'prior_results' for "
        "these/those/them and 'ordinal' (with 1-based index) for 'the second one'. Put free-text "
        "item mentions in item_refs — never invent catalog names. confidence is 0-1. If unsure, "
        "set clarify to {question, options} and lower confidence.\n"
        f"Examples:\n{shots}")
    ctx = json.dumps(context, default=str)
    user = ("Session context (prior turns, oldest first; 'n' is the turn number):\n"
            f"{ctx}\n\nUser message: {{message}}\n\nJSON:")
    return system, user


def followup_chips(intent: str, turn_index: int, anchor: dict | None) -> list[Chip]:
    chips = []
    for f in INTENTS[intent].followups:
        scope = None
        args: dict = {}
        if f["scope_from"] == "results":
            scope = {"type": "prior_results", "turn": turn_index}
        elif f["scope_from"] == "ordinal1":
            scope = {"type": "ordinal", "turn": turn_index, "index": 1}
        elif f["scope_from"] == "anchor" and anchor:
            args = {"item_ref": f"content_id:{anchor['content_id']}"}
        elif f["scope_from"] == "anchor":
            continue
        chips.append(Chip(label=f["label"], intent=f["intent"], args=args, scope=scope))
    return chips
```

- [ ] **Step 4: Run** — `python -m pytest tests/test_chat_registry.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add src/api/rcars/services/chat/registry.py src/api/tests/test_chat_registry.py && git commit -m "feat(chat): declarative intent registry + router prompt assembly"`

---

### Task 9: Router LLM call + validation ladder step 1 (`route()`)

**Files:**
- Modify: `src/api/rcars/services/chat/router.py` (add `route()`)
- Test: `src/api/tests/test_chat_route_llm.py`

**Interfaces:**
- Produces: `route(message, context, settings, llm_call=call_llm) -> tuple[RouterOutput, bool, dict | None]` — `(output, fallback_used, token_usage)` where token_usage is `{"input", "output", "provider"}` or None. JSON/schema failure **and** call errors (timeout, provider down): retry once → fallback `RouterOutput(intent="recommend", args={"search_query": message}, confidence=0.0)` — a dead router model degrades to today's Advisor, never an outage.
- Consumes: `call_llm` (config.py:203, returns `LLMResult(text, input_tokens, output_tokens, provider)`), `build_router_prompt` (Task 8), `pattern_check` (Task 5).

- [ ] **Step 1: Write the failing tests** — `src/api/tests/test_chat_route_llm.py` (no DB needed)

```python
import json
import pytest
from rcars.config import LLMResult, Settings
from rcars.services.chat import router as chat_router

S = Settings(database_url="postgresql://x/x")
GOOD = json.dumps({"intent": "overlap", "args": {"item_ref": "LB2144"}, "scope": None,
                   "item_refs": ["LB2144"], "confidence": 0.9, "clarify": None})


def _fake(*texts):
    calls = {"n": 0}
    def llm_call(settings, model, messages, max_tokens, temperature=0, system=None):
        t = texts[min(calls["n"], len(texts) - 1)]
        calls["n"] += 1
        if isinstance(t, Exception):
            raise t
        return LLMResult(text=t, input_tokens=10, output_tokens=5, provider="test")
    llm_call.calls = calls
    return llm_call


def test_valid_output_first_try():
    out, fallback, usage = chat_router.route("what overlaps with LB2144?", [], S, llm_call=_fake(GOOD))
    assert out.intent == "overlap" and not fallback and usage["input"] == 10


def test_malformed_then_valid_retries_once():
    llm = _fake("not json {", GOOD)
    out, fallback, _ = chat_router.route("x", [], S, llm_call=llm)
    assert out.intent == "overlap" and not fallback and llm.calls["n"] == 2


def test_hallucinated_intent_falls_back_to_recommend():
    bad = json.dumps({"intent": "delete_catalog", "confidence": 0.99})
    out, fallback, _ = chat_router.route("do it", [], S, llm_call=_fake(bad, bad))
    assert out.intent == "recommend" and fallback
    assert out.args["search_query"] == "do it"


def test_call_error_falls_back():
    out, fallback, _ = chat_router.route("x", [], S,
                                         llm_call=_fake(RuntimeError("down"), RuntimeError("down")))
    assert out.intent == "recommend" and fallback


def test_pattern_check_skips_llm():
    def boom(*a, **k):
        raise AssertionError("router LLM must not be called for pasted URLs")
    out, fallback, usage = chat_router.route("https://ev.example.com/agenda", [], S, llm_call=boom)
    assert out.intent == "recommend" and usage is None
```

- [ ] **Step 2: Run to verify failure** → FAIL (`route` doesn't exist).

- [ ] **Step 3: Implement** — append to `router.py`:

```python
import json as _json

from pydantic import ValidationError

from rcars.config import call_llm


def _extract_json(text: str) -> dict:
    """Strip code fences / leading prose, then parse. Raises on failure."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in router output")
    return _json.loads(text[start:text.rfind("}") + 1])


def route(message: str, context: list[dict], settings: Settings,
          llm_call=call_llm) -> tuple[RouterOutput, bool, dict | None]:
    patt = pattern_check(message)
    if patt is not None:
        return patt, False, None

    from rcars.services.chat.registry import build_router_prompt
    system, user_template = build_router_prompt(context)
    usage: dict | None = None
    for attempt in (1, 2):
        try:
            result = llm_call(settings, settings.chat_router_model,
                              [{"role": "user", "content": user_template.format(message=message)}],
                              max_tokens=500, temperature=0, system=system)
            usage = {"input": result.input_tokens, "output": result.output_tokens,
                     "provider": result.provider}
            return RouterOutput.model_validate(_extract_json(result.text)), False, usage
        except (ValidationError, ValueError, _json.JSONDecodeError, Exception) as e:
            logger.warning("chat_router_attempt_failed", component="chat",
                           attempt=attempt, error=str(e)[:300])
    return (RouterOutput(intent="recommend", args={"search_query": message}, confidence=0.0),
            True, usage)
```

(Registry import is deferred inside `route()` to avoid a registry→handlers→router import cycle.)

- [ ] **Step 4: Run** — `python -m pytest tests/test_chat_route_llm.py tests/test_chat_resolve.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add -A src/api && git commit -m "feat(chat): router LLM call with retry-once + recommend fallback"`

---

### Task 10: Answer composer (`answer.py`)

**Files:**
- Create: `src/api/rcars/services/chat/answer.py`
- Test: `src/api/tests/test_chat_answer.py`

**Interfaces:**
- Produces:
  - `build_scaffold(intent: str, facts: dict) -> str` — deterministic first line per intent (counts, scope).
  - `compose_answer(intent, facts, evidence_pack, question, settings, llm_call=call_llm) -> tuple[str, dict | None]` — `(answer_text, token_usage)`. Prompt contains exactly three things: scaffold facts, evidence pack, user question. On LLM failure → scaffold alone (deterministic template intro; the turn still succeeds).
- Consumes: `call_llm`, `settings.chat_answer_model`.

- [ ] **Step 1: Write the failing tests** — `src/api/tests/test_chat_answer.py`

```python
from rcars.config import LLMResult, Settings
from rcars.services.chat.answer import build_scaffold, compose_answer

S = Settings(database_url="postgresql://x/x")
FACTS = {"result_count": 8, "green_count": 3, "top": ["A", "B"], "scoped": False}


def test_scaffold_deterministic():
    line = build_scaffold("recommend", FACTS)
    assert "3" in line and "8" in line
    assert build_scaffold("performance", {"item_count": 2, "window": "3m", "best": "A",
                                          "best_provisions": 40})


def test_compose_prepends_scaffold():
    def llm(settings, model, messages, max_tokens, temperature=0, system=None):
        assert model == S.chat_answer_model
        body = messages[0]["content"]
        assert "8" in body and "narrative question?" in body  # facts + question present
        return LLMResult(text="Great picks.", input_tokens=5, output_tokens=2, provider="t")
    text, usage = compose_answer("recommend", FACTS, [], "narrative question?", S, llm_call=llm)
    assert text.startswith(build_scaffold("recommend", FACTS))
    assert "Great picks." in text and usage["output"] == 2


def test_answer_failure_degrades_to_scaffold():
    def boom(*a, **k):
        raise RuntimeError("model down")
    text, usage = compose_answer("recommend", FACTS, [], "q", S, llm_call=boom)
    assert text == build_scaffold("recommend", FACTS) and usage is None
```

- [ ] **Step 2: Run to verify failure** → FAIL.

- [ ] **Step 3: Implement `src/api/rcars/services/chat/answer.py`**

```python
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
    "performance": lambda f: (f"Usage for {f.get('item_count', 0)} items over the last "
                              f"{f.get('window', '3m')}; {f.get('best', '—')} leads with "
                              f"{f.get('best_provisions', 0)} provisions."),
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
```

- [ ] **Step 4: Run** — `python -m pytest tests/test_chat_answer.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add src/api/rcars/services/chat/answer.py src/api/tests/test_chat_answer.py && git commit -m "feat(chat): grounded answer composer with template fallback"`

---

### Task 11: Orchestrator (`process_turn`) + 3-turn deterministic integration test

**Files:**
- Create: `src/api/rcars/services/chat/orchestrator.py`
- Test: `src/api/tests/test_chat_turn_integration.py`

**Interfaces:**
- Produces:

```python
async def process_turn(*, message: str, session_id: str, user_email: str,
                       is_admin: bool = False, stages: list[str] | None = None,
                       include_zt: bool = True, routed: dict | None = None,
                       opted_out: bool = False, db, settings,
                       on_progress, llm_call=call_llm) -> dict   # Envelope.model_dump()
```

  Turn flow per the spec diagram: context → route (skipped when `routed` given — pre-routed chips) → resolve & verify → handler → evidence pack → compose → envelope → persist turn → return. Logs `chat_router`/`chat_answer` token usage; logs `chat_turn` structlog line; persists via `log_chat_turn` with `intent="clarify"` for clarification turns (so reference resolution skips them).
- Consumes: everything from Tasks 2–10.

- [ ] **Step 1: Write the failing test** — `src/api/tests/test_chat_turn_integration.py`. Fake LLM client; everything else real (seeded Postgres, real handlers/SQL/envelope/persistence). Monkeypatch `generate_embedding` → `fake_embedding` (no vLLM locally) and force the recommend turn to `depth="low"` (no triage/rationale LLM inside `run_query`).

```python
import asyncio
import functools
import json
import os
import pytest
from rcars.config import LLMResult, Settings
from rcars.db import chat_sessions
from rcars.db.database import Database
from rcars.services.chat import handlers, orchestrator
from rcars.services.recommender import pipeline
from tests.chat_fixtures import seed_chat_fixtures, fake_embedding
# ... db fixture + TEST_DB_URL as in test_chat_depth.py ...


def _settings():
    return Settings(database_url=TEST_DB_URL, vector_cutoff=0.99, chat_intent_roles_str="")


class FakeLLM:
    """Queue of canned router/answer texts, FIFO."""
    def __init__(self, *texts):
        self.texts = list(texts)
    def __call__(self, settings, model, messages, max_tokens, temperature=0, system=None):
        return LLMResult(text=self.texts.pop(0), input_tokens=1, output_tokens=1, provider="t")


async def _noop(data):
    pass


def test_three_turn_session_scope_resolution(db, monkeypatch):
    ids = seed_chat_fixtures(db)
    monkeypatch.setattr("rcars.services.recommender.vector_search.generate_embedding",
                        lambda text, prefix="": fake_embedding(text))
    monkeypatch.setattr(handlers, "run_query",
                        functools.partial(pipeline.run_query, depth="low"))
    s = _settings()

    # Turn 0: recommend (fake router + fake answer)
    router_json = json.dumps({"intent": "recommend",
                              "args": {"search_query": "Event-Driven Ansible automation"},
                              "scope": None, "item_refs": [], "confidence": 0.9, "clarify": None})
    env0 = asyncio.run(orchestrator.process_turn(
        message="find me ansible eda content", session_id="sess-1", user_email="u@x.com",
        db=db, settings=s, on_progress=_noop, llm_call=FakeLLM(router_json, "narrative 0")))
    assert env0["intent"] == "recommend"
    turn0_ids = [c["content_id"] for c in env0["blocks"][0]["data"]["candidates"]]
    assert turn0_ids  # vector results present and persisted as the working set

    # Turn 1: performance scoped to turn 0 ("which of these performed best?")
    router_json = json.dumps({"intent": "performance", "args": {},
                              "scope": {"type": "prior_results", "turn": 0},
                              "item_refs": [], "confidence": 0.9, "clarify": None})
    env1 = asyncio.run(orchestrator.process_turn(
        message="which of these performed best?", session_id="sess-1", user_email="u@x.com",
        db=db, settings=s, on_progress=_noop, llm_call=FakeLLM(router_json, "narrative 1")))
    rows = env1["blocks"][0]["data"]["rows"]
    assert sorted(r["content_id"] for r in rows) == sorted(turn0_ids)  # exactly turn 0's ids
    assert "turn" not in env1["scope_echo"] or env1["scope_echo"]      # echo present
    assert env1["scope_echo"]

    # Turn 2: pre-routed chip (skips router — FakeLLM has only the answer text)
    env2 = asyncio.run(orchestrator.process_turn(
        message="Overlap for these", session_id="sess-1", user_email="u@x.com",
        routed={"intent": "overlap", "args": {}, "scope": {"type": "prior_results", "turn": 1}},
        db=db, settings=s, on_progress=_noop, llm_call=FakeLLM("narrative 2")))
    assert env2["intent"] == "overlap"

    turns = db.get_advisor_session("sess-1")
    assert [t["turn_index"] for t in turns] == [0, 1, 2]
    assert turns[1]["intent"] == "performance"
    assert turns[1]["scope_json"]["turn"] == 0            # audit trail
    assert turns[0]["envelope_json"]["blocks"]            # History replay payload


def test_out_of_scope_is_deterministic(db):
    seed_chat_fixtures(db)
    router_json = json.dumps({"intent": "out_of_scope", "args": {}, "scope": None,
                              "item_refs": [], "confidence": 0.95, "clarify": None})
    env = asyncio.run(orchestrator.process_turn(
        message="what's the weather?", session_id="sess-2", user_email="u@x.com",
        db=db, settings=_settings(), on_progress=_noop, llm_call=FakeLLM(router_json)))
    assert env["intent"] == "out_of_scope"
    assert env["blocks"][0]["type"] == "notice"
    assert "recommend" in env["answer"].lower() or "overlap" in env["answer"].lower()
```

- [ ] **Step 2: Run to verify failure** → FAIL.

- [ ] **Step 3: Implement `src/api/rcars/services/chat/orchestrator.py`**

```python
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
            await on_progress({"phase": "fetching", "status": "started"})
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
```

- [ ] **Step 4: Run** — `python -m pytest tests/test_chat_turn_integration.py -v` → PASS. Then the whole chat suite: `python -m pytest tests/test_chat*.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add -A src/api && git commit -m "feat(chat): turn orchestrator with injectable LLM client"`

---

### Task 12: arq task, worker registration, `POST /advisor/chat`, SSE labels

**Files:**
- Create: `src/api/rcars/workers/chat.py`
- Modify: `src/api/rcars/workers/settings.py:112` (`RecommendWorkerSettings.functions`)
- Modify: `src/api/rcars/api/routes/advisor.py` (new endpoint), `src/api/rcars/api/schemas.py` (`ChatSubmitResponse`)
- Modify: `src/api/rcars/api/streaming.py:52` (`translate_to_user_message` — labels for `routing`/`fetching`/`composing`)
- Test: `src/api/tests/test_chat_api.py`

**Interfaces:**
- Produces: `POST /api/v1/advisor/chat` `{message, session_id?, stages?, include_zt?, routed?, opted_out?}` → `{job_id, session_id}`. Shares `/advisor/query`'s rate-limit bucket and stream/result endpoints (chat turns are jobs). arq task name `run_chat_turn` on `arq:queue:recommend`.
- Consumes: `process_turn` (Task 11), `session_owner_ok` (Task 2), job pattern from `routes/advisor.py:51-75` and `workers/recommend.py`.

- [ ] **Step 1: Write the failing API tests** — `src/api/tests/test_chat_api.py`. Copy the app/client fixture style from `tests/test_app.py` (dev-user auth via `Settings(dev_user=...)`), with a stub `arq_redis` capturing `enqueue_job` calls:

```python
class FakeArq:
    def __init__(self):
        self.calls = []
    async def enqueue_job(self, name, **kwargs):
        self.calls.append((name, kwargs))


def test_chat_new_session_generates_id(client, fake_arq):
    resp = client.post("/api/v1/advisor/chat", json={"message": "find ansible content"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] and body["session_id"]
    name, kwargs = fake_arq.calls[0]
    assert name == "run_chat_turn"
    assert kwargs["session_id"] == body["session_id"]
    assert kwargs["_queue_name"] == "arq:queue:recommend"


def test_chat_append_checks_ownership(client, db):
    from rcars.db import chat_sessions
    chat_sessions.log_chat_turn(db.pool, session_id="other-sess", turn_index=0,
                                user_email="someoneelse@x.com", query_text="q", results=None,
                                overall_assessment=None, intent="recommend",
                                envelope=None, scope=None)
    resp = client.post("/api/v1/advisor/chat",
                       json={"message": "more", "session_id": "other-sess"})
    assert resp.status_code == 404


def test_chat_message_length_capped(client):
    resp = client.post("/api/v1/advisor/chat", json={"message": "x" * 2001})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run to verify failure** → FAIL (404 route not found on the first test).

- [ ] **Step 3: Implement.**

`src/api/rcars/workers/chat.py` (mirrors `workers/recommend.py` shape):

```python
"""Chat turn worker task — runs on the recommend queue."""
from __future__ import annotations

import structlog

from rcars.services.chat.orchestrator import process_turn
from rcars.workers.base import WorkerContext, publish_progress

logger = structlog.get_logger()


async def run_chat_turn(
    ctx: dict, job_id: str, message: str, session_id: str,
    stages: list[str] | None = None, include_zt: bool = True,
    user_email: str | None = None, is_admin: bool = False,
    routed: dict | None = None, opted_out: bool = False,
) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id, component="chat")
    log.info("picked_up", action="picked_up", queue="recommend", job_type="chat")
    wctx.db.update_job_status(job_id, "running")
    try:
        async def on_progress(data: dict):
            await publish_progress(wctx.relay, job_id, wctx.db, **data)

        envelope = await process_turn(
            message=message, session_id=session_id, user_email=user_email,
            is_admin=is_admin, stages=stages, include_zt=include_zt,
            routed=routed, opted_out=opted_out,
            db=wctx.db, settings=wctx.settings, on_progress=on_progress)
        result = {**envelope, "session_id": session_id}
        wctx.db.complete_job(job_id, result_json=result)
        await on_progress({"phase": "complete", "results": len(envelope.get("blocks", []))})
        log.info("job_complete", action="job_complete", intent=envelope.get("intent"))
        return result
    except Exception as e:
        log.error("job_failed", action="job_failed", error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        await wctx.relay.publish(job_id, {"phase": "failed",
                                          "error": "An internal error occurred while processing your message."})
        raise
```

`workers/settings.py:110-118` — `from rcars.workers.chat import run_chat_turn` and `functions = [run_recommendation, run_chat_turn]`.

`api/schemas.py` — add:

```python
class ChatSubmitResponse(BaseModel):
    job_id: str
    session_id: str
```

`routes/advisor.py` — after `submit_query`:

```python
import uuid

from rcars.db import chat_sessions


class ChatRequest(BaseModel):
    message: str = Field(max_length=2000)
    session_id: str | None = None
    stages: list[str] = ["prod"]
    include_zt: bool = True
    routed: dict | None = None   # pre-routed chip payload {intent, args, scope}
    opted_out: bool = False


@router.post(
    "/chat",
    summary="Submit a chat message (multi-intent advisor)",
    description=("Routes a natural-language message to a deterministic intent handler. "
                 "Returns a job_id (use the existing stream/result endpoints) and the "
                 "session_id for follow-up turns. Rate-limited per user with /advisor/query."),
    response_model=ChatSubmitResponse,
    responses={404: {"description": "session_id not found or not owned by user"},
               429: {"description": "Rate limit exceeded or query already running"}},
)
@limiter.limit(_advisor_limit)
async def submit_chat(body: ChatRequest, request: Request, user: str = Depends(require_auth)):
    db = request.app.state.db
    arq_redis = request.app.state.arq_redis
    settings: Settings = request.app.state.settings

    is_admin = settings.is_admin(user)
    session_id = body.session_id
    if session_id:
        if not chat_sessions.session_owner_ok(db.pool, session_id, user, is_admin=is_admin):
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session_id = str(uuid.uuid4())

    if not settings.is_curator(user) and not is_admin:
        if db.has_active_recommend_job(user):
            raise HTTPException(status_code=429, detail="You already have a query running. Please wait for it to complete.")

    stages = body.stages
    if "dev" in stages and not settings.is_curator(user) and not is_admin:
        stages = [s for s in stages if s != "dev"]

    job_id = db.create_job(job_type="chat", queue="recommend", created_by=user)
    await arq_redis.enqueue_job(
        "run_chat_turn", job_id=job_id, message=body.message, session_id=session_id,
        stages=stages, include_zt=body.include_zt, user_email=user, is_admin=is_admin,
        routed=body.routed, opted_out=body.opted_out,
        _queue_name="arq:queue:recommend")
    return {"job_id": job_id, "session_id": session_id}
```

`api/streaming.py` — in `translate_to_user_message` (line 52), add phase labels alongside the existing ones:

```python
    "routing": "Understanding your question...",
    "fetching": "Fetching data...",
    "composing": "Writing the answer...",
```

(Match the existing dict/if-chain structure in that function.)

- [ ] **Step 4: Run** — `python -m pytest tests/test_chat_api.py tests/test_app.py tests/test_streaming.py -v` → PASS.
- [ ] **Step 5: Commit + push milestone**

```bash
git add -A src/api
git commit -m "feat(chat): POST /advisor/chat endpoint + run_chat_turn worker + SSE labels"
git push -u origin feature/advisor-chat
```

---

### Task 13: Golden routing eval (`llm_eval`) + live integration tier

**Files:**
- Modify: `pyproject.toml:48` (markers)
- Create: `src/api/tests/data/routing_golden.yaml`
- Create: `src/api/tests/test_chat_routing_golden.py`
- Create: `src/api/tests/test_chat_live.py`

**Interfaces:**
- Produces: the acceptance gate for prompt changes and open-source model swaps. Adding a case = one YAML entry. `RCARS_CHAT_ROUTER_MODEL=<candidate> python -m pytest tests/ -m llm_eval` evaluates a candidate model.

- [ ] **Step 1: Add the marker** in `pyproject.toml`:

```toml
markers = [
    "integration: tests requiring live Babylon cluster (deselect with '-m not integration')",
    "llm_eval: live-LLM routing eval — the acceptance gate for prompt/model changes",
]
```

- [ ] **Step 2: Create `src/api/tests/data/routing_golden.yaml`** — starter set below (~16 cases). Grow to ~40 during rollout; every production misroute from Query History becomes a new case. `context` entries use the context-builder shape.

```yaml
# {message, context?, expect: {intent, scope_type?}}
- message: "I need a 2-hour hands-on OpenShift virtualization lab for platform engineers"
  expect: {intent: recommend}
- message: "something for an Ansible automation workshop at a financial services customer"
  expect: {intent: recommend}
- message: "high-usage Ansible content for an EDA demo"          # adversarial pair (a)
  expect: {intent: recommend}
- message: "how is our Ansible EDA content performing?"          # adversarial pair (b)
  expect: {intent: performance}
- message: "what overlaps with LB2144?"
  expect: {intent: overlap}
- message: "is the SAP lab similar to anything else we have?"
  expect: {intent: overlap}
- message: "do we have duplicate OpenShift Virtualization labs?"
  expect: {intent: overlap}
- message: "which of these performed best?"
  context: &ctx
    - n: 0
      intent: recommend
      query: "ansible labs"
      results: [{id: "babylon:a", name: "Lab A"}, {id: "babylon:b", name: "Lab B"}]
  expect: {intent: performance, scope_type: prior_results}
- message: "what's the cost per provision on these?"
  context: *ctx
  expect: {intent: performance, scope_type: prior_results}
- message: "tell me about the second one"
  context: *ctx
  expect: {intent: item_facts, scope_type: ordinal}
- message: "what overlaps with the first result?"
  context: *ctx
  expect: {intent: overlap, scope_type: ordinal}
- message: "what is the SAP HANA demo about?"
  expect: {intent: item_facts}
- message: "what modules are in LB2145 and what products does it cover?"
  expect: {intent: item_facts}
- message: "what's the weather in Raleigh?"
  expect: {intent: out_of_scope}
- message: "open a Jira ticket to retire LB2144"
  expect: {intent: out_of_scope}
- message: "who won the world cup?"
  expect: {intent: out_of_scope}
```

- [ ] **Step 3: Create `src/api/tests/test_chat_routing_golden.py`**

```python
"""Golden routing eval — real prompt assembly, real model, real validation.
Hard-asserts at temperature 0. ~40 calls ≈ cents. THE gate for model swaps."""
import pathlib

import pytest
import yaml

from rcars.config import Settings
from rcars.services.chat.router import route

CASES = yaml.safe_load(
    (pathlib.Path(__file__).parent / "data" / "routing_golden.yaml").read_text())


@pytest.fixture(scope="module")
def settings():
    import os
    return Settings(database_url=os.environ.get(
        "RCARS_TEST_DATABASE_URL", "postgresql://rcars:dev@localhost:5432/rcars_test"))


@pytest.mark.llm_eval
@pytest.mark.parametrize("case", CASES, ids=[c["message"][:50] for c in CASES])
def test_routing_golden(case, settings):
    output, fallback, _ = route(case["message"], case.get("context", []), settings)
    assert not fallback, "router call failed — eval requires a live model"
    assert output.intent == case["expect"]["intent"]
    if "scope_type" in case["expect"]:
        assert output.scope is not None and output.scope.type == case["expect"]["scope_type"]
```

- [ ] **Step 4: Create `src/api/tests/test_chat_live.py`** — a handful of end-to-end turns with real LLM calls against the seeded DB, marked `integration`:

```python
import asyncio

import pytest

from rcars.services.chat.orchestrator import process_turn
# ... db fixture + seed_chat_fixtures + _settings as in test_chat_turn_integration.py,
#     but WITHOUT the FakeLLM / generate_embedding monkeypatches ...


@pytest.mark.integration
def test_live_item_facts_turn(db):
    seed_chat_fixtures(db)

    async def noop(data):
        pass
    env = asyncio.run(process_turn(
        message="what is LB2144 about?", session_id="live-1", user_email="u@x.com",
        db=db, settings=_settings(), on_progress=noop))
    assert env["intent"] in ("item_facts", "recommend")   # recommend = honest fallback
    if env["intent"] == "item_facts":
        assert env["blocks"][0]["type"] == "item_card"
        assert "LB2144" in env["blocks"][0]["data"]["display_name"]


@pytest.mark.integration
def test_live_out_of_scope(db):
    seed_chat_fixtures(db)

    async def noop(data):
        pass
    env = asyncio.run(process_turn(
        message="what's a good pizza place in Boston?", session_id="live-2",
        user_email="u@x.com", db=db, settings=_settings(), on_progress=noop))
    assert env["intent"] == "out_of_scope"
```

- [ ] **Step 5: Run the tiers** (needs `RCARS_` LLM credentials in the environment):

```bash
python -m pytest tests/ -m "not integration and not llm_eval"   # fast suite still green
python -m pytest tests/ -m llm_eval -v                          # golden eval — expect 100%
python -m pytest tests/ -m "llm_eval or integration" -v         # pre-deploy gate
```

If golden cases fail, fix the registry prompt fragments/examples (not the test) until 100%, then re-run.

- [ ] **Step 6: Commit** — `git add pyproject.toml src/api/tests && git commit -m "test(chat): golden routing eval gate + live integration tier"`

---

### Task 14: Frontend chat types, API client, block renderers

**Files:**
- Create: `src/frontend/src/components/advisor/chatTypes.ts`
- Modify: `src/frontend/src/services/api.ts` (add `submitChat`)
- Create: `src/frontend/src/components/advisor/RecCardList.tsx` (move `RecCardList` + `CollapsibleTier` out of `AdvisorPage.tsx:437-513`, unchanged except `export`)
- Create: `src/frontend/src/components/advisor/blocks/registry.ts`, `RecCardsBlock.tsx`, `OverlapTableBlock.tsx`, `PerformanceTableBlock.tsx`, `ItemCardBlock.tsx`, `NoticeBlock.tsx`, `UnknownBlock.tsx`

**Interfaces:**
- Produces:
  - `chatTypes.ts`: `ChatChip { label, intent, args, scope }`, `ChatBlock { type, data }`, `ChatEnvelope { intent, scope_echo, answer, blocks, suggested_followups, session_id? }`.
  - `api.submitChat(message, sessionId?, stages?, includeZt?, routed?)` → `Promise<{ job_id: string; session_id: string }>` (POST `/advisor/chat`).
  - `resolveBlockRenderer(type: string): ComponentType<{ block: ChatBlock; sessionId?: string; turnIndex: number }>` — unknown types get `UnknownBlock` (narrative stays visible + collapsible raw JSON "view data"), so new backend block types never crash an older frontend.
- Consumes: envelope JSON from Task 11/12; `RecCard` (`components/advisor/RecCard.tsx`); style tokens (`var(--bg-card)`, `var(--border-subtle)`, `var(--text-muted)` etc.) as used throughout `AdvisorPage.tsx`.

- [ ] **Step 1: `chatTypes.ts`**

```typescript
export interface ChatChip {
  label: string
  intent: string
  args: Record<string, unknown>
  scope: Record<string, unknown> | null
}

export interface ChatBlock {
  type: string
  data: Record<string, unknown>
}

export interface ChatEnvelope {
  intent: string
  scope_echo: string
  answer: string
  blocks: ChatBlock[]
  suggested_followups: ChatChip[]
  session_id?: string
}
```

- [ ] **Step 2: `api.ts`** — after `submitQuery` (line 28):

```typescript
  submitChat: (message: string, sessionId?: string | null, stages: string[] = ['prod'],
               includeZt = true, routed?: Record<string, unknown>) =>
    request<{ job_id: string; session_id: string }>('/advisor/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId ?? null, stages,
                             include_zt: includeZt, routed: routed ?? null }),
    }),
```

- [ ] **Step 3: Move `RecCardList`.** Cut `RecCardList` and `CollapsibleTier` from `AdvisorPage.tsx:437-513` into `components/advisor/RecCardList.tsx`; add `export` to `RecCardList`, import `RecCard`/`StreamCandidate`; import it back in `AdvisorPage.tsx`. Run `npm run build` in `src/frontend` → compiles.

- [ ] **Step 4: Block components.** Each takes `{ block, sessionId, turnIndex }`. Keep styling consistent with the existing inline-style approach (no PatternFly in this pane). Implementations:

`RecCardsBlock.tsx` — `<RecCardList candidates={block.data.candidates} isComplete sessionId={sessionId} />` plus the content-gaps list if `block.data.content_gaps` is non-empty. If any candidate has a `content_type` other than `lab`/`demo`, render the secondary strip: a muted header `Also similar, though not labs:` above those cards (filter by content_type).

`OverlapTableBlock.tsx` — anchor header (`block.data.anchor.display_name`) + one row per neighbor: `display_name`, `similarity_pct%`, `relationship_type` badge, `stage`, `shared_products.join(', ')`, and `why` when non-null. Footer link `Open in Content Analysis → Overlap` — use the Content Analysis route path registered in `src/frontend/src/App.tsx`.

`PerformanceTableBlock.tsx` — window echo (`Last {window}`), rows: `display_name`, `provisions`, `cost_per_provision` (2 decimals or —), `sales_impact`, and a score badge only when `block.data.retirement_flavored` and `row.score != null`. Footer link to the Retirement page route.

`ItemCardBlock.tsx` — `display_name` + stage/content_type badges, `summary`, products chips, modules list, `workloads.join(', ')`, and a `neighbors` strip (name + %). Two links per the card link rule: primary → the external catalog entry (reuse the `catalogUrl()` logic from `RecCard.tsx:36` for Babylon items), secondary → the RCARS Browse item detail route.

`NoticeBlock.tsx` — muted bordered box; body text comes from the envelope `answer` rendered in the transcript, so this block only shows the `kind` icon/label (`out_of_scope` → "Out of scope", `role_redirect` → "Restricted", `clarify` → "Needs clarification").

`UnknownBlock.tsx`:

```tsx
export function UnknownBlock({ block }: { block: ChatBlock }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)',
                  padding: '10px', color: 'var(--text-muted)', fontSize: '13px' }}>
      This response includes a "{block.type}" view this version of the UI can't render yet.
      <button onClick={() => setOpen(!open)} style={{ marginLeft: 8 }}>view data</button>
      {open && <pre style={{ fontSize: '11px', overflow: 'auto' }}>{JSON.stringify(block.data, null, 2)}</pre>}
    </div>
  )
}
```

`registry.ts`:

```typescript
import type { ComponentType } from 'react'
import type { ChatBlock } from '../chatTypes'
import { RecCardsBlock } from './RecCardsBlock'
import { OverlapTableBlock } from './OverlapTableBlock'
import { PerformanceTableBlock } from './PerformanceTableBlock'
import { ItemCardBlock } from './ItemCardBlock'
import { NoticeBlock } from './NoticeBlock'
import { UnknownBlock } from './UnknownBlock'

export interface BlockProps { block: ChatBlock; sessionId?: string; turnIndex: number }

const RENDERERS: Record<string, ComponentType<BlockProps>> = {
  rec_cards: RecCardsBlock,
  overlap_table: OverlapTableBlock,
  performance_table: PerformanceTableBlock,
  item_card: ItemCardBlock,
  notice: NoticeBlock,
}

export function resolveBlockRenderer(type: string): ComponentType<BlockProps> {
  return RENDERERS[type] ?? UnknownBlock
}
```

- [ ] **Step 5: Verify** — `cd src/frontend && npm run build && npm run lint` → clean.
- [ ] **Step 6: Commit** — `git add src/frontend && git commit -m "feat(chat-ui): chat types, submitChat, block renderer registry"`

---

### Task 15: AdvisorPage rewiring — chat flow, echo, chips, resume

**Files:**
- Modify: `src/frontend/src/pages/AdvisorPage.tsx`
- Modify: `src/frontend/src/components/advisor/ProgressStream.tsx` (only if it maps phase names — labels come from the backend `user_message`, so likely no change; verify)

**Interfaces:**
- Consumes: `api.submitChat`, `resolveBlockRenderer`, `ChatEnvelope` (Task 14). Result payload = envelope + `session_id` (Task 12). Session detail turns now include `intent`, `envelope_json`, `scope_json` (Task 2).

- [ ] **Step 1: State changes.** Delete `cleanAssessment()` (lines 67-71) — structure now comes from typed envelope fields. Change state:
  - `ChatMessage` gains `envelope?: ChatEnvelope` for assistant turns.
  - `turns: TurnResults[]` becomes `turns: ChatEnvelope[]`.
  - Add `const [sessionId, setSessionId] = useState<string | null>(null)`; `resetSession()` clears it.

- [ ] **Step 2: Send path** (`handleSend`, lines 224-251). Remove the query-concat hack (lines 233-239 — multi-turn is now the backend's job). Submit:

```typescript
const { job_id, session_id } = await api.submitChat(query, sessionId, stages, showZt)
setSessionId(session_id)
setActiveJobId(job_id)
```

Add `const handleChip = (chip: ChatChip) => { ... }` — inserts `chip.label` as the user message and calls `api.submitChat(chip.label, sessionId, stages, showZt, { intent: chip.intent, args: chip.args, scope: chip.scope })` (pre-routed: zero router involvement).

- [ ] **Step 3: Completion path** (effect at lines 198-218). The result is now a `ChatEnvelope`:

```typescript
api.getQueryResult(activeJobId).then(data => {
  const env = data.result as ChatEnvelope
  if (env && env.intent) {
    setTurns(prev => [...prev, env])
    setActiveTurn(turns.length)
    setMessages(prev => [...prev, { role: 'assistant', content: env.answer, envelope: env, jobId: activeJobId }])
  }
  setActiveJobId(null)
  setSending(false)
})
```

- [ ] **Step 4: Assistant turn rendering** (lines 297-305). For turns with an envelope render, top to bottom: interpretation echo (muted line, always present — the misroute tripwire), narrative via `renderMarkdown(env.answer)`, then chips:

```tsx
{msg.envelope && (
  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', marginBottom: 6 }}>
    {msg.envelope.scope_echo}
  </div>
)}
<div className="assistant-content">{renderMarkdown(msg.content)}</div>
{msg.envelope && msg.envelope.suggested_followups.length > 0 && (
  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
    {msg.envelope.suggested_followups.map((chip, ci) => (
      <button key={ci} onClick={() => handleChip(chip)} disabled={sending}
              style={{ border: '1px solid var(--border-default)', background: 'transparent',
                       color: 'var(--text-link)', borderRadius: 12, padding: '3px 10px',
                       fontSize: 12, cursor: 'pointer' }}>
        {chip.label}
      </button>
    ))}
  </div>
)}
```

- [ ] **Step 5: Evidence pane** (lines 394-432). Rename the pane label from "Recommendations" to "Evidence". Keep the streaming branch (`streamingCandidates` → `RecCardList`) for live recommend turns; for completed turns render the active envelope's blocks through the registry:

```tsx
{currentResults?.blocks.map((b, i) => {
  const Renderer = resolveBlockRenderer(b.type)
  return <Renderer key={i} block={b} sessionId={sessionId ?? undefined} turnIndex={activeTurn} />
})}
```

Turn selector buttons (lines 398-418) already generalize — keep, label stays `Rec N`/`Current` → rename to `Turn N`/`Current`.

- [ ] **Step 6: Session resume** (effect at lines 159-196). For each turn from `api.getSession`: if `turn.envelope_json` exists, push user message + assistant message with `envelope: turn.envelope_json` and push the envelope into `turns`; else fall back to the existing legacy path (results_json/overall_assessment — pre-chat single-turn sessions are valid working sets). Also `setSessionId(sid)` so typing continues the session.

- [ ] **Step 7: Welcome screen + long-session nudge.** Rewrite the welcome copy (lines 269-296) around the four intents, one example prompt each (use golden-set phrasings — the cheapest routing aid): *find content* ("I need a 2-hour hands-on lab for platform engineers covering OpenShift virtualization"), *check overlap* ("What overlaps with LB2144?"), *check performance* ("Which of these performed best?" — note: after a search), *item facts* ("What is the SAP HANA demo about?"). Keep the beta line. Add the nudge above the input when `turns.length > 5`:

```tsx
{turns.length > 5 && (
  <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '4px 2px' }}>
    Long session — references only reach the last 5 turns. Fresh often works better
    (use New Session).
  </div>
)}
```

Never a block — input stays enabled.

- [ ] **Step 8: Verify** — `npm run build && npm run lint` → clean. Manual check happens after deploy (Task 17); nothing runnable locally on this laptop.
- [ ] **Step 9: Commit** — `git add src/frontend && git commit -m "feat(chat-ui): envelope-driven transcript, chips, echo, session resume"`

---

### Task 16: Frontend test harness (vitest) + block registry test

**Files:**
- Modify: `src/frontend/package.json`
- Create: `src/frontend/src/components/advisor/blocks/registry.test.ts`

- [ ] **Step 1: Add vitest** (unit-only, no DOM libs needed — the registry resolver is a pure function):

```bash
cd src/frontend && npm install -D vitest
```

Add to `package.json` scripts: `"test": "vitest run"`.

- [ ] **Step 2: Write `registry.test.ts`**

```typescript
import { describe, expect, it } from 'vitest'
import { resolveBlockRenderer } from './registry'
import { UnknownBlock } from './UnknownBlock'
import { RecCardsBlock } from './RecCardsBlock'

describe('block renderer registry', () => {
  it('dispatches known block types', () => {
    expect(resolveBlockRenderer('rec_cards')).toBe(RecCardsBlock)
    for (const t of ['overlap_table', 'performance_table', 'item_card', 'notice']) {
      expect(resolveBlockRenderer(t)).not.toBe(UnknownBlock)
    }
  })

  it('falls back for unknown block types', () => {
    expect(resolveBlockRenderer('portfolio_gaps')).toBe(UnknownBlock)
    expect(resolveBlockRenderer('')).toBe(UnknownBlock)
  })
})
```

- [ ] **Step 3: Run** — `npm test` → PASS. `npm run build` still clean.
- [ ] **Step 4: Commit** — `git add src/frontend && git commit -m "test(chat-ui): vitest + block registry dispatch/fallback"`

---

### Task 17: Docs, graph, full verification, deploy to dev

**Files:**
- Modify: `CLAUDE.md` (API Reference section: 45 → 46 endpoints; add one line to Key Patterns: "Chat routing: LLM router output selects deterministic handlers; see `services/chat/registry.py` to add intents"; add `chat_*` settings mention in the Configuration context if listed)
- Modify: `docs/` — add `docs/architecture/advisor-chat.md` containing a short overview + link to the spec, and add it to the MkDocs nav (`mkdocs.yml`)

- [ ] **Step 1: Docs.** Write `docs/architecture/advisor-chat.md` (~1 page): turn flow diagram (copy from spec), intent table, "adding an intent" checklist (registry entry + golden cases + block renderer if new type), settings table. Update `CLAUDE.md` as above.

- [ ] **Step 2: Full local verification** (on the dev machine):

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api
python -m pytest tests/ -m "not integration and not llm_eval" -v   # fast suite
python -m pytest tests/ -m "llm_eval or integration" -v            # pre-deploy gate
cd ../frontend && npm run build && npm run lint && npm test
cd ../.. && graphify update .
```

All green before proceeding. Report any failure honestly — do not deploy on red.

- [ ] **Step 3: Commit, push, PR**

```bash
git add -A && git commit -m "docs(chat): architecture page + project instructions update"
git push
gh pr create --title "Advisor multi-intent chat (RHDPCD-599)" --body "Implements docs/superpowers/specs/2026-08-02-advisor-chat-design.md ..."
```

Wait for CodeRabbit review before merging (repo rule). Address findings via superpowers:receiving-code-review.

- [ ] **Step 4: Deploy to dev and smoke-test** (after merge to main):

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags api
ansible-playbook ansible/deploy.yml -e env=dev --tags frontend
```

Manual smoke on dev: (1) new chat "find me an ansible lab" → cards + echo + chips; (2) tap "Performance of these" as non-curator → role redirect (or as curator → table); (3) "what overlaps with LB2144?" → overlap table; (4) "tell me about the second one" → item card; (5) out-of-scope question → notice; (6) reload with `?session=` → transcript replays; (7) System → Token Usage shows `chat_router`/`chat_answer` rows; (8) `POST /advisor/query` without `depth` behaves exactly as before.

- [ ] **Step 5: Jira.** Update the RHDPCD chat issue (link PR, note the three reusable testing artifacts — fixture catalog, fake-LLM fixture, `llm_eval` marker — for the testing backlog item), per the collaboration rules in CLAUDE.md.

---

## Self-Review Notes

Checked against the spec:

- **Covered:** all four intents + out_of_scope (T7/T8/T11); router contract + full 5-step fallback ladder (T5/T9); pre-routed chips end to end (T8 backend → T15 UI → T12 `routed` param); depth + scoped search with byte-for-byte default (T4); evidence pack with code-constant caps (T6); session model (turn_index increments, context window ≠ session limit, clarify-turn skipping, ownership 404, resume incl. pre-chat sessions) (T2/T5/T11/T12/T15); grounding rule (T10); token ops `chat_router`/`chat_answer` + structlog fields (T11); SSE phases (T12); all five test tiers incl. the golden-eval model-swap gate (T13/T16); config incl. per-call-site models + role gates (T1); overlap honesty — `why` stays null until the batch job lands (T7); mixed content types via badges + secondary strip (T14); card two-link rule (T14); welcome-screen routing aid + long-session nudge (T15); no new deployments (T12 registers on the recommend worker).
- **Known deviations (intentional):** `chat_intent_roles_str` field name (codebase `_str` precedent; the spec's name is the parsed property); `orchestrator.py` added to the spec's module list (keeps `workers/chat.py` a thin arq wrapper and gives the tests the injectable seam the spec requires); the deterministic 3-turn test forces the recommend turn to `depth="low"` so no LLM runs inside `run_query` (the spec's fake-client tier can't reach LLM calls buried in the pipeline; the live tier covers full-depth recommend).
- **Deferred to follow-on (per spec):** portfolio/gaps intent, overlap "why" batch job, declarative planner, new content sources.





