# Recommender Redesign — Three-Phase Pipeline

**Date:** 2026-04-11
**Status:** Draft
**Scope:** Replace single-call `recommend()` with a three-phase progressive pipeline (vector search → Haiku triage → Sonnet rationale), restructure recommender code into a module, and overhaul the advisor UI for progressive result delivery.

## Problem

The current recommendation engine has two critical issues:

1. **Speed:** A query like "ansible content for ansiblefest" takes 50+ seconds across only 6 scanned CIs. The bottleneck is a single Sonnet API call that receives all 15 candidates with full metadata and must produce structured JSON reasoning for each. With 200+ CIs in the catalog, this will only get worse.

2. **Quality:** Results include recommendations with 5% match scores for content that has "no Ansible content at all." There is no threshold at any stage — the vector search returns the top-N by cosine distance regardless of absolute quality, and the LLM dutifully ranks everything it's given, even garbage.

## Design

### Three-Phase Query Pipeline

Each phase produces progressively richer results. The web UI updates after each phase completes. Each phase is independently useful — if a later phase is slow or fails, the user still has results from earlier phases.

#### Phase 1 — Vector Search + Instant Results (~200ms)

1. Generate query embedding using sentence-transformers (`all-MiniLM-L6-v2`, already cached in-process).
2. pgvector cosine similarity search across all `ci_summary` embeddings.
3. Apply a **hard distance cutoff** — candidates with cosine distance > 0.55 are discarded. This threshold is configurable via `RCARS_VECTOR_CUTOFF` environment variable.
4. Return top 10 survivors ranked by vector similarity.
5. Cards display immediately using pre-stored metadata from `showroom_analysis`: display name, summary, topics, difficulty, duration, content type.
6. Score badge shows vector similarity percentage, converted from cosine distance: `round((1 - distance / 2) * 100)`.
7. If zero candidates survive the cutoff, return immediately: *"Nothing in the catalog is a strong fit for this query. Try broadening your terms or describing what you need differently."* — no LLM calls are made.

#### Phase 2 — Haiku Triage (~3-5s)

1. Send Phase 1 survivors to Claude Haiku with a compact prompt: query text + candidate summaries (name, summary, topics, products — not full analysis).
2. Haiku returns a JSON array: `{ci_name, relevance_score (0-100), relevant (bool), one_line_reason}`.
3. Candidates with `relevant: false` or `relevance_score < 30` are removed from the UI with a CSS opacity transition (300ms fade-out).
4. Remaining cards re-sort by Haiku score. Score badge updates from vector similarity to Haiku relevance score.
5. If Haiku determines nothing is relevant, update UI: *"After evaluating the top results, none are a strong match for this query."*
6. Top candidates (3-5, score ≥ 70%) that will receive Sonnet analysis show the status text *"Preparing detailed analysis..."* in their rationale area.

#### Phase 3 — Sonnet Rationale (~5-10s)

1. Send top 3-5 Haiku-validated candidates to Claude Sonnet with the full analysis context (objectives, modules, event fit, audience, difficulty).
2. Sonnet returns per-candidate: `rationale`, `suggested_format`, `duration_notes`, `caveats`.
3. Sonnet also returns an `overall_assessment` for the chat pane.
4. Cards update in-place: *"Preparing detailed analysis..."* is replaced with the rationale text, format, duration notes, and caveats.
5. Chat pane receives the `overall_assessment`.
6. Candidates that received Sonnet analysis keep their Haiku relevance score (Sonnet validates but does not re-score).

### Pipeline State Machine

The pipeline is modeled as a state machine with the following states:

```
SUBMITTED → VECTOR_DONE → TRIAGE_DONE → COMPLETE
                ↓              ↓
           NO_MATCHES     NO_MATCHES
```

The pipeline generator yields `QueryState` at each "done" transition. Running states are implicit — the web layer knows a phase is in progress because it hasn't received the next yield. The `QueryState` dataclass holds the current phase, candidates at each stage, and timing information.

### Progressive UI Status

The user always knows what is happening. Status messages are explicit and phase-aware:

| Phase | Rec Pane Status | Card State |
|-------|----------------|------------|
| Query submitted | *"Searching the catalog..."* | No cards |
| Phase 1 complete | Cards appear, ranked by similarity | Score badge: vector %, metadata visible, no rationale |
| Phase 2 running | Status line: *"Evaluating relevance..."* | Cards unchanged |
| Phase 2 complete | Low-relevance cards fade out (300ms) | Surviving cards re-sort, scores update. Top picks show: *"Preparing detailed analysis..."* |
| Phase 3 running | No change to status line | Top 3-5 cards show *"Preparing detailed analysis..."* |
| Phase 3 complete | Chat pane: overall assessment | Rationale text replaces placeholder |
| No matches (Phase 1) | *"Nothing in the catalog is a strong fit for this query. Try broadening your terms or describing what you need differently."* | No cards |
| No matches (Phase 2) | *"After evaluating the top results, none are a strong match for this query."* | All cards removed |

### Rec Card States

Each recommendation card has a `phase` attribute that controls its rendering:

- **`vector`**: Initial state. Shows display name, summary, topics, difficulty, duration, content type, vector similarity score. No rationale section.
- **`triaged`**: After Haiku. Score updates to Haiku relevance score. One-line reason shown as a subtitle.
- **`analyzing`**: Top picks waiting for Sonnet. Rationale area shows *"Preparing detailed analysis..."* with a subtle animation.
- **`complete`**: After Sonnet. Full rationale, suggested format, duration notes, caveats all rendered.
- **`removed`**: Failed Haiku triage. Card fades out via CSS transition and is removed from the DOM.

## Code Structure

### Recommender Module

The current single-file `recommender.py` is replaced by a `recommender/` package:

```
src/rcars/
├── recommender/
│   ├── __init__.py          # Public API: run_query(), QueryResult, QueryState
│   ├── pipeline.py          # Three-phase orchestrator, state machine, phase transitions
│   ├── vector_search.py     # Phase 1: embedding generation + pgvector search + distance cutoff
│   ├── triage.py            # Phase 2: Haiku scoring prompt construction + response parsing
│   ├── rationale.py         # Phase 3: Sonnet rationale prompt construction + response parsing
│   └── models.py            # Dataclasses: Candidate, TriageResult, Rationale, QueryState, QueryResult
├── prompts/
│   ├── triage.txt           # Haiku triage prompt (compact, ~500 token template)
│   ├── rationale.txt        # Sonnet rationale prompt (rich, for top picks)
│   └── recommend.txt        # Removed (replaced by triage.txt + rationale.txt)
```

Each phase is a pure function: takes typed input, returns typed output. The pipeline orchestrator in `pipeline.py` manages state transitions and is what the web route calls.

### Key Interfaces

```python
# models.py
@dataclass
class Candidate:
    ci_name: str
    display_name: str
    category: str
    summary: str
    topics: list[str]
    products: list[str]
    difficulty: str
    duration_min: int | None
    content_type: str
    vector_distance: float
    vector_similarity_pct: int
    # Populated after triage
    relevance_score: int | None = None
    relevant: bool | None = None
    one_line_reason: str | None = None
    # Populated after rationale
    rationale: str | None = None
    suggested_format: str | None = None
    duration_notes: str | None = None
    caveats: str | None = None

@dataclass
class QueryState:
    phase: str  # SUBMITTED | VECTOR_DONE | TRIAGE_DONE | COMPLETE | NO_MATCHES
    candidates: list[Candidate]
    overall_assessment: str | None = None
    content_gaps: list[str] | None = None
    timings: dict[str, float] = field(default_factory=dict)  # phase_name → seconds

# vector_search.py
def search(query: str, db: Database, limit: int = 10,
           prod_only: bool = True, distance_cutoff: float = 0.55) -> QueryState

# triage.py
def triage(state: QueryState, anthropic_client, model: str = "claude-haiku-4-5") -> QueryState

# rationale.py
def generate_rationale(state: QueryState, db: Database, anthropic_client,
                       model: str = "claude-sonnet-4-6", top_n: int = 5) -> QueryState

# pipeline.py
def run_query(query: str, db: Database, anthropic_client, settings: Settings) -> Generator[QueryState, None, None]:
    """Yield QueryState after each phase completes."""
```

The `run_query()` generator yields `QueryState` after each phase, allowing the web layer to push updates to the client as each phase finishes.

### Web Layer Changes

**Advisor route** (`web/routes/advisor.py`):

The background thread currently calls `recommend()` once and renders a single HTML response. It changes to:

1. Call `run_query()` which yields `QueryState` after each phase.
2. After each yield, render the appropriate HTML fragment and store it in `_query_status[session_id]`.
3. The status dict gains a `phase` field so the polling endpoint knows which fragment to return.
4. The polling endpoint (`/advisor/query/status`) returns the latest fragment, which HTMX swaps into the rec-pane using `outerHTML`.

**HTMX polling** continues at the current 2-second interval. Each poll returns the latest state by replacing the full `#rec-pane` via `outerHTML` swap — the same pattern used today. This is simpler than per-card OOB swaps and avoids partial-update edge cases:
- During Phase 1: spinner with *"Searching the catalog..."*
- After Phase 1: full rec-pane with cards + continued polling trigger for Phase 2
- After Phase 2: re-rendered rec-pane with surviving cards re-sorted + continued polling for Phase 3
- After Phase 3: final rec-pane with rationales filled in + OOB chat turn with overall assessment. Polling stops.

**Templates**:
- `fragments/rec_card.html` gains a `data-phase` attribute and conditional rendering for each card state (vector, triaged, analyzing, complete)
- `fragments/rec_list.html` gains a status line element for phase messaging
- New: `fragments/rec_card_update.html` — partial card content for OOB swaps during Phase 2/3

### Prompt Design

**Haiku Triage Prompt** (`prompts/triage.txt`):

```
You are evaluating catalog items for relevance to a user's request.
Be strict: a partial topic overlap is not relevance. If the content
does not meaningfully address the request, mark it as not relevant.

## Request
{request_description}

## Candidates
{candidates}

Return ONLY valid JSON (no markdown fences):
[
  {
    "ci_name": "the-ci-name",
    "relevance_score": 85,
    "relevant": true,
    "one_line_reason": "Direct Ansible automation workshop with AAP 2.x labs"
  }
]
```

Candidate format for triage is compact — name, summary, topics, products only. No full analysis, no modules, no objectives. This keeps the prompt small (~1-2K tokens for 10 candidates) and Haiku fast.

**Sonnet Rationale Prompt** (`prompts/rationale.txt`):

Receives full analysis data for the top 3-5 candidates (objectives, modules, event fit, audience). This is a refined version of the current `recommend.txt` but scoped to fewer candidates and focused on explanation rather than ranking (Haiku already ranked).

```
You are a Red Hat Demo Platform (RHDP) content advisor. These candidates
have been pre-screened as relevant to the request below. For each one,
provide a detailed analysis.

## Request
{request_description}

## Candidates
{candidates}

For each candidate, provide:
- rationale: 2-3 sentences explaining why this fits and how to use it
- suggested_format: "booth_demo", "hands_on_lab", or "presentation"
- duration_notes: How to adapt timing for the context
- caveats: Any concerns, gaps, or things to watch for

Also provide:
- overall_assessment: Structured summary using markdown (bold labels, bullet lists)
- content_gaps: Topics requested but not well covered by any candidate

Return ONLY valid JSON (no markdown fences):
{
  "recommendations": [...],
  "overall_assessment": "...",
  "content_gaps": [...]
}
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `RCARS_VECTOR_CUTOFF` | `0.55` | Cosine distance threshold for Phase 1. Higher = more permissive. |
| `RCARS_TRIAGE_MODEL` | `claude-haiku-4-5` | Model for Phase 2 triage. |
| `RCARS_TRIAGE_CUTOFF` | `30` | Minimum Haiku relevance score to survive triage. |
| `RCARS_RATIONALE_MODEL` | `claude-sonnet-4-6` | Model for Phase 3 rationale. |
| `RCARS_RATIONALE_TOP_N` | `5` | Maximum candidates sent to Sonnet for rationale. |
| `RCARS_MODEL` | `claude-sonnet-4-6` | Existing setting, now used as fallback for rationale model. |

## Scaling Considerations

**pgvector at 200+ CIs:** Sequential scan is sub-second for thousands of rows. If needed, add an IVFFlat index:
```sql
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
```

**Haiku triage stays fast** because the vector cutoff caps input at ~10-15 candidates regardless of catalog size.

**Sonnet rationale is fixed** at 3-5 candidates — constant cost and latency regardless of catalog growth.

**Cost per query:** ~$0.001 (Haiku triage) + ~$0.01-0.03 (Sonnet rationale for 3-5 items) = ~$0.01-0.03 total. Comparable to current single-call cost but with much better results.

## Testing Strategy

- **Unit tests** for each phase function (vector_search, triage, rationale) with mocked DB and API responses.
- **Integration test** for the full pipeline using a test database with known embeddings and mocked LLM responses.
- **Threshold tuning** tests: run the pipeline against known-good and known-bad queries with the full catalog to calibrate `RCARS_VECTOR_CUTOFF` and `RCARS_TRIAGE_CUTOFF`.
- **UI tests**: verify progressive rendering — cards appear, update, and remove correctly across phases.

## Follow-ups (Out of Scope)

### Scan Pipeline Resilience (Important)

The `rcars scan` pipeline currently processes CIs via `ThreadPoolExecutor` with no progress persistence. At 200+ CIs, a full scan takes ~30 minutes. If the pod restarts mid-scan, all progress is lost and the scan must restart from the beginning.

The `jobs` table in the database schema was designed for this but is not yet wired up. The follow-up should:

1. Track per-CI scan progress in the `jobs` table (or a dedicated `scan_progress` table).
2. On restart, resume from the last completed CI rather than starting over.
3. Add a `--batch` flag to scan a subset of CIs (e.g., `rcars scan --batch 50`).
4. Add idempotency guards so accidental double-triggers from the admin UI don't duplicate work.
5. Consider a dedicated worker container if scan workload grows to justify it.

### Analyzer Refactor

`analyzer.py` is 393 lines mixing git operations, file I/O, LLM calls, and embedding generation. A future cleanup should split it similarly to the recommender module. Not blocking for this work.

### Vector Index

Add IVFFlat or HNSW index on the embeddings table once the catalog exceeds ~500 CIs and sequential scan latency becomes measurable.
