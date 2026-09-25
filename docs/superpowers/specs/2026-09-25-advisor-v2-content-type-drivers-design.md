# Advisor v2 — Content-Type Drivers

**Jira:** [RHDPCD-1953](https://redhat.atlassian.net/browse/RHDPCD-1953)
**Date:** 2026-09-25
**Status:** Design
**Supersedes:** `2026-09-24-advisor-v15-portfolio-arch-design.md` (bolt-on approach)

## Summary

The recommendation pipeline was built for one content type (Babylon labs/demos). The v1.5 branch (`feature/advisor-v15-arch-filters-itemchat`) bolted architecture support onto every layer — inline triage exceptions, content-type conditionals in rationale formatting, dual serialization paths, frontend `isArchitecture` checks, and a `run_pipelines` wrapper that splits, runs, and merges results after the fact.

This design replaces the bolt-on approach with **content-type drivers**: per-type strategy objects that provide scoring guidance, data fetching, formatting, serialization, and display configuration. The pipeline calls driver hooks at defined extension points instead of branching on `content_type`. Multiple content-type categories run as **parallel pipeline instances** — one per driver — with no post-hoc merge.

Adding a new content type (interactive experiences, sandboxes, anything) requires one driver file. Zero changes to the pipeline, SSE streaming, or frontend rendering.

## Goals

- Content-type drivers with a defined interface: any content type is a single Python file implementing 7 hooks.
- Parallel pipeline instances per content-type category, with category-labeled SSE events — no merge.
- Candidate model with universal fields verified against live data, type-specific data in a `type_data` dict.
- Backend-driven card rendering — the driver defines what the frontend displays, the frontend renders generically.
- Unified serialization — one serializer per driver, two modes (streaming, final with performance).

## Non-Goals

- New content-type ingestion pipelines (OSSPA sync, Babylon scan are separate work).
- Changes to the chat intent system (router, answer composition, blocks registry).
- `item_chat` intent (independent of the pipeline; layered in after the redesign).
- Changes to vector search SQL (already handles `content_types` filtering correctly).
- Changes to the recommendations API contract (already accepts `content_types`).

## Approach Decision

Three approaches were considered:

1. **Config-driven registry (recipe cards).** One pipeline reads per-type config for scoring criteria, display fields, capabilities. Problem: the differences between types are behavioral (different DB calls, different prompt content, different scoring adjustments), not just data. Config that contains functions and templates is code disguised as data — harder to debug and test.

2. **Content-type drivers / strategy pattern (chosen).** Each type provides implementations for defined extension points. The pipeline stays generic; behavior varies per type through clean interfaces. Honest about the fact that types are behaviorally different. One driver file per type. Testable in isolation.

3. **Data-driven flat model (let the data speak).** Keep one flat pipeline, make every field optional, skip what's missing. This pushes "what does this type look like?" into scattered null-checks — which is exactly the problem the v1.5 branch has. Rejected.

## Architecture

### Parallel Pipeline Instances

Content types cannot share a single pipeline run because:

- **Volume dominance.** Labs outnumber architectures ~12:1. In a mixed triage, architectures get buried.
- **Scoring criteria conflict.** Labs are penalized for duration mismatch; architectures have no duration. One triage prompt cannot apply both rules coherently.
- **Fair representation.** Each type needs its own triage pass to surface its best candidates independently.

When multiple content-type categories are requested, the orchestrator launches parallel pipeline instances — one per driver — via `asyncio.gather`. Each instance runs with its own driver. Results stay separate all the way to the frontend, where tabs display each category independently.

```text
User query + [lab, demo, architecture]
         │
    run_query()  ← orchestrator (replaces run_pipelines)
         │
    Split by driver category
         │
   ┌─────┴──────────────────┐
   │                        │
   ▼                        ▼
run_category()         run_category()
driver=hands_on        driver=architecture
   │                        │
 vector search           vector search
 triage (+ guidance)     triage (+ guidance)
 post_triage             post_triage
   (duration, usage)       (no-op)
 rationale               rationale
   (driver format)         (driver format)
 serialize               serialize
   (driver)                (driver)
   │                        │
   ▼                        ▼
category results        category results
(labeled SSE)           (labeled SSE)
         │                  │
         └──────┬───────────┘
                ▼
         Frontend tabs
```

### Entry Points

Both API paths converge at the orchestrator:

```text
Chat path:
  AdvisorPage → api.submitChat → chat worker → router
    → handle_recommend → run_query()

Recommendations API:
  POST /advisor/recommendations → recommend worker → run_query()
```

The recommendations API already accepts `content_types: list[Literal["lab", "demo", "architecture"]]`. No API contract changes needed. Depth levels (`low`/`medium`/`high`) are respected by `run_category()` — early return after the requested phase. Drivers don't need to know about depth.

Single-category shortcut: if only one driver is needed, the orchestrator runs one `run_category()` directly — no split overhead.

## Design

### 1. Content-Type Drivers

Location: `src/api/rcars/services/recommender/drivers/`

```text
drivers/
├── __init__.py        # registry: maps content_type string → driver instance
├── base.py            # ContentTypeDriver interface (abstract base)
├── hands_on.py        # handles "lab" and "demo"
└── architecture.py    # handles "architecture"
```

#### Driver Interface

| Hook | Signature | Purpose |
|------|-----------|---------|
| `content_types` | `-> list[str]` | Types this driver handles (`["lab", "demo"]` or `["architecture"]`) |
| `fetch_analysis` | `(db, candidate) -> dict` | Get full analysis data from the right DB table |
| `triage_guidance` | `() -> str` | Extra text injected into the triage prompt for this type |
| `format_for_rationale` | `(candidate, analysis) -> str` | Format one candidate for the per-candidate rationale LLM call |
| `post_triage` | `(candidates, query, db) -> list[Candidate]` | Type-specific adjustments after triage |
| `serialize` | `(candidate, include_performance?, db?) -> dict` | Convert candidate to JSON for frontend (one serializer, two modes) |
| `display_config` | `() -> dict` | Tells the frontend what fields to render and in what layout |

#### What Moves Into Drivers

| Current location | What | Destination |
|-----------------|------|-------------|
| `rationale.py:52-104` | `_format_single_candidate` content-type branches | `driver.format_for_rationale` |
| `rationale.py:228-250` | Analysis fetch per content_type | `driver.fetch_analysis` |
| `pipeline.py:114-139` | `_apply_duration_penalty` | `hands_on.post_triage` |
| `pipeline.py:142-183` | `_apply_usage_boost` | `hands_on.post_triage` |
| `triage.txt:29` | "Architecture content has no duration" inline exception | `architecture.triage_guidance` |
| `pipeline.py:232-249` | `serialize_candidates` (inline SSE) | `driver.serialize` |
| `serialize.py:9-58` | `candidates_with_performance` | `driver.serialize(include_performance=True)` |

#### Adding a New Content Type

1. Create `drivers/<type>.py` implementing the 7 hooks.
2. Register it in `drivers/__init__.py`.
3. Done. No pipeline, prompt, or frontend changes.

### 2. Orchestrator and Pipeline

**`run_query()`** — the orchestrator. Replaces `run_pipelines`. Groups requested content types by driver, launches `run_category()` per group via `asyncio.gather`, returns per-category results with no merge.

**`run_category()`** — the actual pipeline. Replaces today's `run_query`. Takes one driver instance. Runs:

1. **Vector search** — `search()` with the driver's content types. Unchanged.
2. **Triage** — `triage()` with driver's `triage_guidance()` injected into the prompt. The guidance replaces the inline exception in `triage.txt`.
3. **Post-triage** — `driver.post_triage()`. For hands_on: usage boost + duration penalty + re-sort. For architecture: no-op.
4. **Rationale** — `generate_rationale()` calls `driver.fetch_analysis()` and `driver.format_for_rationale()` instead of branching on content_type.
5. **Serialize** — `driver.serialize()` for SSE streaming. `driver.serialize(include_performance=True)` for final results.

Depth levels work as before: `low` returns after vector search, `medium` after triage, `high` runs the full pipeline. Drivers don't need to know about depth.

#### What Gets Deleted

| Current code | Replacement |
|-------------|-------------|
| `run_pipelines()` (pipeline.py:369-402) | `run_query()` orchestrator |
| `_merge_query_states()` (pipeline.py:343-366) | Deleted — no merge needed |
| `_CONTENT_CATEGORIES` dict (pipeline.py:335-338) | Drivers register their content types |
| `serialize_candidates()` (pipeline.py:232-249) | `driver.serialize()` |
| `candidates_with_performance()` (serialize.py:9-58) | `driver.serialize(include_performance=True)` |

### 3. Candidate Model

Verified against the live database. Field population by content type:

#### `content_entities` (shared table — all types)

| Field | Lab | Demo | Sandbox | Architecture |
|-------|-----|------|---------|-------------|
| `content_id` | `babylon:...` | `babylon:...` | `babylon:...` | `pa:25` |
| `display_name` | yes | yes | yes | yes |
| `source` | `babylon` | `babylon` | `babylon` | `portfolio_arch` |
| `content_type` | `lab` | `demo` | `sandbox` | `architecture` |
| `is_hands_on` | true | true | true | false |
| `status` | prod/dev/event | prod/dev/event | prod/dev/event | prod/dev |
| `difficulty` | yes | yes | yes | None |
| `products_json` | yes | yes | yes | yes |
| `topics_json` | yes | yes | yes | yes |
| `audience_json` | yes | yes | yes | yes |

#### Source-specific tables

| Field | Lab/Demo (`babylon_items`) | Architecture (`architecture_analysis`) |
|-------|---------------------------|---------------------------------------|
| `ci_name` | yes | does not exist |
| `stage` | yes | does not exist (uses `content_entities.status`) |
| `catalog_namespace` | yes | does not exist |
| `base_ci_name` | yes | does not exist |
| `duration` | yes (`showroom_analysis`) | does not exist |
| `learning_objectives` | yes (`showroom_analysis`) | does not exist |
| `modules` | yes (`showroom_analysis`) | does not exist |
| `solution_areas_json` | no | yes |
| `use_cases_json` | no | yes |
| `key_components_json` | no | yes |
| `asset_type` | no | yes (PA/VP/SP) |

Architectures have 0 rows in `babylon_items`. 66 rows in `content_entities`, 60 in `embeddings`.

#### Candidate Dataclass

```python
@dataclass
class Candidate:
    # Universal — verified present in content_entities for all types
    content_id: str
    display_name: str
    content_type: str
    source: str
    summary: str
    products: list[str]
    topics: list[str]
    status: str = "prod"
    difficulty: str | None = None   # None for architectures
    is_hands_on: bool = True

    # Pipeline state — set by pipeline phases, universal
    tier: str = "white"
    vector_distance: float = 0.0
    vector_similarity_pct: int = 0
    relevance_score: int | None = None
    one_line_reason: str | None = None

    # Rationale — set by Phase 3, same structure for all types
    why_it_fits: str | None = None
    how_to_use: str | None = None
    caveats: str | None = None

    # Type-specific — populated by the driver
    type_data: dict = field(default_factory=dict)
```

**`type_data` for hands_on:**
```python
{"ci_name": "...", "catalog_namespace": "...", "base_ci_name": "...",
 "stage": "dev", "category": "...",
 "duration_min": 120, "duration_source": "curated",
 "learning_objectives": [...],
 "provisions_quarter": 42, "suggested_format": "hands_on_lab",
 "duration_notes": "..."}
```

**`type_data` for architecture:**
```python
{"solution_areas": [...], "use_cases": [...],
 "key_components": [...], "asset_type": "VP"}
```

### 4. SSE Streaming

Each pipeline instance emits progress events with a `category` field when multiple categories are running. Events interleave naturally as parallel instances progress.

**Single category:**
```json
{"phase": "vector_search", "status": "started"}
{"phase": "vector_search", "status": "complete", "candidates": 15, "candidate_data": [...]}
```

**Multiple categories:**
```json
{"phase": "vector_search", "status": "started", "category": "hands_on"}
{"phase": "vector_search", "status": "started", "category": "architecture"}
{"phase": "vector_search", "status": "complete", "category": "hands_on", "candidates": 15, "candidate_data": [...]}
```

The orchestrator passes a `category` label to `run_category()`, which includes it in every `on_progress` callback.

#### Frontend Progress Display

`ProgressStream` component shows nested collapsible progress (inspired by Parsec's query-running UI):

```text
While running (expanded):
  ▾ Searching 2 content types...
      ◉ Labs & Demos — triage (12 candidates)
      ◉ Architectures — vector search...

When complete (collapsed):
  ▸ Searched 2 content types (20 results)
```

`useJobStream.ts` changes:
- Delete `mergeCandidatesByCategory` function.
- Store candidates as `Map<string, StreamCandidate[]>` keyed by category.
- When an event has `category`, update that category's list. Without `category` (single category), use a default key.

**Unchanged:** SSE transport (Redis pub/sub → EventSource), `JobProgressRelay`, `sse_stream()`, `create_sse_response()`.

### 5. Frontend Card Rendering

The driver's `serialize()` method includes a `display` configuration in the candidate JSON. `RecCard` reads it to know what to show — no content-type conditionals.

#### Display Config Structure

```json
{
  "display": {
    "format_badge": {"label": "Hands-on Lab", "key": "hands_on_lab"},
    "header_right": {"value": "~120 min", "tooltip": "Curated duration"},
    "detail_rows": [
      {"label": "Why it fits", "field": "why_it_fits"},
      {"label": "Objectives", "field": "learning_objectives", "type": "list", "max": 5},
      {"label": "How to use", "field": "how_to_use"}
    ],
    "footer_metrics": [
      {"label": "deployments (last 90d)", "field": "provisions_quarter"},
      {"label": "sales_impact", "field": "sales_impact", "type": "badge"}
    ],
    "links": [
      {"label": "View in RHDP Catalog", "url": "https://demo.redhat.com/catalog?item=..."},
      {"label": "View in RCARS", "url": "/browse?search=..."}
    ]
  }
}
```

Architecture display config omits `header_right` (no duration), has `solution_areas` and `use_cases` in `detail_rows`, has no `footer_metrics` (no provisions), and links to RCARS Browse only (no RHDP catalog link).

`RecCard` becomes a generic renderer:
- Header: score + name + format badge + `header_right`
- Expanded: iterate `detail_rows`, render each by type (text, list)
- Footer: iterate `footer_metrics`
- Links: iterate `links`

`RecCardsBlock` tab grouping stays — already works cleanly. Gets cleaner input since results arrive pre-categorized by the orchestrator.

### 6. Unified Serialization

**Delete both:**
- `pipeline.py:serialize_candidates()` (lines 232-249) — inline SSE serialization
- `serialize.py:candidates_with_performance()` (lines 9-58) — final result serialization

**Replace with** each driver's `serialize()` method. Two modes:

| Mode | Call | Use case |
|------|------|----------|
| Streaming | `driver.serialize(candidate)` | SSE `candidate_data` mid-pipeline |
| Final | `driver.serialize(candidate, include_performance=True, db=db)` | Final result with provisions, cost, sales impact |

Performance metrics (`provisions_quarter`, `avg_cost_per_provision`, `sales_impact`) are in the `hands_on` driver only. Architectures don't have provisions data. If a future type has performance data, its driver implements its own performance attachment.

## Branch Strategy

- New branch from `main`: `feature/advisor-v2-content-type-drivers`.
- Build everything fresh — no cherry-picking from the current branch. The current branch's commits are too intertwined to safely cherry-pick individual features.
- `item_chat` (RHDPCD-2067) is layered in after the redesign is complete. It's fully independent of the pipeline — separate handler, separate component, separate registry entry. No cherry-pick needed.
- Filter chip toggle UI is rebuilt as part of the frontend card rendering work.
- Current branch (`feature/advisor-v15-arch-filters-itemchat`) stays as reference until the new branch is merged.

## What Stays Unchanged

- **Vector search** — already accepts `content_types`, filters in SQL, handles architecture-specific embedding fields.
- **`content_entities` data model** — designed correctly in RHDPCD-359. The problem is the layers above it.
- **Router content-type awareness** — the deterministic override (don't route to `out_of_scope` when filters changed) is correct.
- **`asyncio.gather` for parallel execution** — the right approach, just needs to be native to the orchestrator.
- **SSE transport** — Redis pub/sub → EventSource, `JobProgressRelay`, `sse_stream()`, `create_sse_response()`.
- **`item_chat` intent** — fully independent of the recommendation pipeline.
- **`RecCardsBlock` tab grouping logic** — `getCategoryKey` → Map → tabs is clean.
- **Recommendations API contract** — already accepts `content_types`.

## Reference Specs

| Spec | Relevance |
|------|-----------|
| `2026-07-20-generalized-content-model-design.md` | DB-layer content model. Done right. This design brings the API/pipeline/frontend up to the same standard. |
| `2026-08-02-advisor-chat-design.md` | Chat architecture (intent → handler → blocks → answer). The registry-based intent system is extensible — drivers follow the same pattern. |
| `2026-09-24-advisor-v15-portfolio-arch-design.md` | The v1.5 bolt-on spec. Documents what needs to exist, even though the implementation approach is replaced. |
| `2026-04-11-recommender-redesign-design.md` | Original pipeline design. Assumes single content type. |
