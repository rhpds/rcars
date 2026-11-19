# Description-Based Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let curators analyze Babylon lab/demo items from their catalog description or custom text instead of a Showroom repo, per item, from the Browse edit drawer.

**Architecture:** A per-item `analysis_source_override` column on `babylon_items` selects the analysis input. The scan worker branches before showroom resolution and runs `analyze_description()`, which reuses the existing hash/signature/compare-and-swap persistence machinery with a synthetic per-item source. Staleness is a content-hash + context-hash comparison, so nightly refresh (description changed) and once-only refresh (custom text) fall out of one predicate.

**Tech Stack:** Python 3.11 / FastAPI / arq / psycopg + PostgreSQL, React 19 + PatternFly + TypeScript, pytest.

**Spec:** `docs/superpowers/specs/2026-11-17-description-analysis-design.md` (approved; Jira RHDPCD-2264)

## Global Constraints

- Commit subjects: `[RHDPCD-2264] Imperative description`, ≤75 chars after the key, no trailing period; end body with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.
- Tests run from `src/api` with `source ~/.virtualenvs/rcars-v2/bin/activate`; DB tests use the `db` fixture from `tests/showroom_helpers.py` (real `rcars_test` database, isolation namespace `babylon:isolation-test.*`). Mark live-cluster tests `@pytest.mark.integration`.
- LLM mocking: `monkeypatch.setattr("rcars.config.call_llm", llm)` with a `Mock(return_value=SimpleNamespace(text='<structured JSON>', input_tokens=1, output_tokens=1, provider='test'))`; embedding transport via monkeypatched `analyzer.generate_embedding` — copy the pattern from `tests/test_showroom_reuse.py` (fixture `scan`, lines 53-70).
- All LLM responses go through `parse_analysis_response()`; no prose parsing.
- Schema changes: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` at the bottom of `SCHEMA_SQL` in `src/api/rcars/db/database.py` only.
- Structlog on every new log line: `component="scanner"`, `action=...`, `content_id=...`.
- Overrides survive artifact clears and resets: `clear_babylon_generated_artifacts` must never touch `babylon_items` columns.
- No frontend unit test runner exists; frontend verification is `npm run build` in `src/frontend` (tsc + vite).

## Review Focus

1. **Empty or whitespace-only description with `agnosticv_description`** — the endpoint must reject at save time (400), and a pre-existing override whose description later becomes empty must fail the scan with error class `no_content`, not an opaque crash. Test: Task 2 (rejection) and Task 3 (`no_content` error result).
2. **Curator flips the source while a scan is running** — the compare-and-swap must see the override change and return `superseded`, not persist a stale generation. Test: Task 5 (`_snapshot` includes the new columns; a snapshot taken before the flip differs from after).
3. **Description edited upstream in AgnosticV** — the nightly candidate selection must re-run analysis because the content hash changed. Test: Task 4 (edited text makes `get_items_needing_analysis` select the item again).
4. **Item renamed or recategorized** — context-hash mismatch must re-trigger analysis even with identical text. Test: Task 3 (`display_name` change re-runs the LLM).
5. **Stale check must not touch description items** — a description-analyzed item must never be marked stale by `git ls-remote` logic (the field-asset items carry broken showroom sources). Test: Task 6 (override items are absent from `get_stale_check_candidates` output).

---

### Task 1: Schema columns + `effective_analysis_source()`

**Files:**
- Modify: `src/api/rcars/db/database.py` (bottom of `SCHEMA_SQL`, after line ~645)
- Modify: `src/api/rcars/services/showroom_source.py`
- Test: `src/api/tests/test_description_analysis.py` (new file)

**Interfaces:**
- Consumes: nothing new.
- Produces: `effective_analysis_source(item: dict) -> str` in `rcars.services.showroom_source`, returning `"showroom"` (when the column is NULL or holds an unknown value), `"agnosticv_description"`, or `"custom_description"`. DB columns `babylon_items.analysis_source_override TEXT NULL` and `babylon_items.custom_description TEXT NULL`.

- [ ] **Step 1: Write the failing tests** in `src/api/tests/test_description_analysis.py`

```python
from rcars.services.showroom_source import effective_analysis_source

def test_effective_analysis_source_defaults_to_showroom():
    assert effective_analysis_source({}) == "showroom"
    assert effective_analysis_source({"analysis_source_override": None}) == "showroom"
    assert effective_analysis_source({"analysis_source_override": "bogus"}) == "showroom"

def test_effective_analysis_source_returns_override():
    assert effective_analysis_source({"analysis_source_override": "agnosticv_description"}) == "agnosticv_description"
    assert effective_analysis_source({"analysis_source_override": "custom_description"}) == "custom_description"
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_description_analysis.py -v` → FAIL, `ImportError`/`AttributeError`.
- [ ] **Step 3: Implement** — add `effective_analysis_source()` to `showroom_source.py` (unknown values degrade to `"showroom"`); append the two `ALTER TABLE babylon_items ADD COLUMN IF NOT EXISTS` statements at the bottom of `SCHEMA_SQL`.
- [ ] **Step 4: Run tests** — expected PASS (the function is pure; the schema lands with the `db` fixture in later tasks).
- [ ] **Step 5: Commit** — `git add src/api/rcars/db/database.py src/api/rcars/services/showroom_source.py src/api/tests/test_description_analysis.py && git commit -m "[RHDPCD-2264] Add analysis source override columns and resolver"`

### Task 2: `Database.set_analysis_source()` setter

**Files:**
- Modify: `src/api/rcars/db/database.py` (near `_set_showroom_override`, ~line 1575)
- Test: `src/api/tests/test_description_analysis.py`

**Interfaces:**
- Consumes: Task 1 columns; existing `lock_babylon_item`, `clear_babylon_generated_artifacts`.
- Produces: `set_analysis_source(self, content_id: str, source: str, custom_description: str | None = None) -> None`. Raises `ValueError` on: unknown `source`; missing item; `custom_description` absent/blank when `source == "custom_description"`; blank stored `babylon_items.description` when `source == "agnosticv_description"`. On any actual change: updates both columns (custom text cleared to NULL unless source is custom) and calls `clear_babylon_generated_artifacts([content_id], conn=conn)`. No-op when the effective values are unchanged.

- [ ] **Step 1: Write failing tests** (use the `db` fixture; insert items with `db.upsert_babylon_catalog_item({"ci_name": "isolation-test.desc-a.prod", "stage": "prod", "description": "Provides a cluster.", ...})`):

`test_set_analysis_source_custom_requires_text` (ValueError on None/blank), `test_set_analysis_source_description_requires_stored_description` (item with empty description → ValueError), `test_set_analysis_source_updates_columns_and_clears_artifacts` (seed a `showroom_analysis` row + embedding, set `agnosticv_description`, assert summary/embeddings gone, `scan_status == 'not_scanned'`, columns set), `test_set_analysis_source_reverting_to_showroom_clears_artifacts`, `test_set_analysis_source_is_noop_when_unchanged` (artifacts survive), `test_clear_babylon_generated_artifacts_preserves_override` (set override, call `db.invalidate_babylon_scan_failure`, assert override columns intact).

- [ ] **Step 2: Run** → FAIL (`AttributeError: set_analysis_source`).
- [ ] **Step 3: Implement** following `_set_showroom_override`'s lock-then-update shape; do NOT touch `_set_showroom_override`'s allowlist.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `[RHDPCD-2264] Add curator setter for per-item analysis source`

### Task 3: `analyze_description()` in the analyzer

**Files:**
- Modify: `src/api/rcars/services/analyzer.py`
- Test: `src/api/tests/test_description_analysis.py`

**Interfaces:**
- Consumes: `hash_showroom_content`, `_canonical_content`, `_item_context_hash`, `_finish_showroom_result`, `_embedding_specs`, `_valid_embedding`, `call_llm`, `parse_analysis_response`, `normalize_analysis`, `AnalysisSignature`, `ResolvedShowroom`, `item_family_key`, `effective_analysis_source`.
- Produces:
  - `description_content_hash(text: str) -> str` — `hash_showroom_content({"description.adoc": text})`.
  - `build_description_prompt(ci_name: str, display_name: str, category: str, product: str, description_text: str, entity_content_type: str = "lab") -> tuple[str, str]` — same output-JSON contract as `build_analysis_prompt` (call it for the schema block if practical), framing the input as a short catalog description rather than lab modules.
  - `description_work_needed(item: dict, row: dict, embeddings: list[dict], settings) -> bool` — True when no row/summary, `row["content_hash"] != description_content_hash(current text)`, context hash differs, or any embedding invalid (reuse `_embedding_specs`/`_valid_embedding` as `showroom_work_needed` does). Current text = `item["custom_description"]` when the override is custom, else `item["description"]`.
  - `analyze_description(item: dict, settings, *, force: bool = False) -> dict | None` — synthetic source `ResolvedShowroom("resolved", owner_ci_name=ci_name, scope_key=item_family_key(ci_name, item.get("stage", "")), repo=f"description:{ci_name}")`; signature `AnalysisSignature(scope_key, f"description:{ci_name}", None, None, content_hash, content_hash, context_hash, input_hash, SHOWROOM_ANALYSIS_POLICY_VERSION)` — note `commit = content_hash` so every signature field stays truthy; short-circuit to `unchanged` via `description_work_needed` unless `force`; on new text run the LLM, parse, `normalize_analysis`, and return `_finish_showroom_result(..., fresh_generation=True, force=force, content_file_count=1)`; then set `result["analysis_provenance"]["source_type"] = effective_analysis_source(item)`. Blank text → `{"error": "no_content", "message": ...}`.

- [ ] **Step 1: Write failing tests** (db fixture; monkeypatch `rcars.config.call_llm` and `analyzer.generate_embedding` per the Global Constraints pattern; settings as `SimpleNamespace(model=..., embedding_model=..., embedding_dim=768)`):

`test_analyze_description_first_run_analyzes` (outcome `analyzed`, LLM called once, provenance has `source_type`, signature repo is the sentinel), `test_analyze_description_second_run_unchanged` (no second LLM call), `test_analyze_description_force_bypasses_shortcircuit`, `test_analyze_description_changed_text_reruns`, `test_analyze_description_rename_reruns` (same text, new `display_name`), `test_analyze_description_blank_text_returns_no_content`.

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the four functions. Body hint: the unchanged short-circuit mirrors `_own_analysis_current` but compares against the synthetic source and the text hash.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `[RHDPCD-2264] Analyze items from description text with hash staleness`

### Task 4: Candidate selection

**Files:**
- Modify: `src/api/rcars/db/database.py` (`get_items_needing_analysis`, ~line 2782)
- Test: `src/api/tests/test_description_analysis.py`

**Interfaces:**
- Consumes: `effective_analysis_source`, `description_work_needed` (Task 3).
- Produces: `get_items_needing_analysis` includes lab/demo items whose effective source is not `showroom` — selected when `force or description_work_needed(...)` — regardless of showroom source status, still skipped when `content_owner(item) is not None`.

- [ ] **Step 1: Write failing tests** (db fixture; item with `analysis_source_override='agnosticv_description'`, no showroom URL, `content_type='lab'`): `test_needing_analysis_includes_description_item_without_showroom`, `test_needing_analysis_skips_current_description_item` (after a successful `analyze_description`, the item is not selected), `test_needing_analysis_still_skips_content_owner_stubs`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — in the per-item loop, branch on `effective_analysis_source(item) != "showroom"` after the `content_owner` check and before `source.status != "resolved"`; apply `description_work_needed` instead of `showroom_work_needed`, then `continue`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `[RHDPCD-2264] Select description items in scan candidates`

### Task 5: Scan pipeline branch

**Files:**
- Modify: `src/api/rcars/services/showroom_scan.py` (`_snapshot` line 17, `scan_babylon_item` line 30, `_scan_babylon_item` line 44)
- Test: `src/api/tests/test_description_analysis.py`

**Interfaces:**
- Consumes: `analyze_description` (Task 3), `effective_analysis_source`.
- Produces: `_snapshot` tuples include `"analysis_source_override"` and `"custom_description"`; `scan_babylon_item` skips the reuse advisory lock for non-showroom sources; `_scan_babylon_item` routes non-showroom items through `analyze_description(item, settings, force=force)` into the existing compare-and-swap persistence block (no repo clone, no `classify_scan_error` git path).

- [ ] **Step 1: Write failing tests** (db fixture, LLM + embedding mocked): `test_scan_description_item_succeeds` (insert failed-scan item with override, run `scan_babylon_item`, assert `scan_status == 'success'`, `showroom_analysis` row written with `source_type`, card fields on `content_entities`, summary embedding present), `test_snapshot_includes_analysis_source_fields` (two dicts differing only in `analysis_source_override` produce different `_snapshot` tuples), `test_scan_description_error_marks_failed` (LLM returns unparseable text → outcome `failed`, `scan_error_class == 'parse_failed'`).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — branch after the content-owner check and before the `source.status == "none"` early return; keep the CAS block untouched so its superseded/failed/persist paths apply unchanged.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `[RHDPCD-2264] Route description items through the scan pipeline`

### Task 6: Stale check exclusion

**Files:**
- Modify: `src/api/rcars/db/database.py` (`get_stale_check_candidates`, ~line 2820)
- Test: `src/api/tests/test_description_analysis.py`

**Interfaces:**
- Consumes: `effective_analysis_source`.
- Produces: `get_stale_check_candidates` returns only showroom-source items (`effective_analysis_source(row) == "showroom"`), in addition to the existing content-owner filter.

- [ ] **Step 1: Write failing test** — `test_stale_check_candidates_exclude_description_items`: a description-analyzed item with a broken showroom source is absent from the result.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — extend the existing list comprehension filter.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `[RHDPCD-2264] Exclude description items from stale checks`

### Task 7: API endpoint + detail fields

**Files:**
- Modify: `src/api/rcars/api/routes/catalog.py` (near `override_url`, ~line 414)
- Modify: `src/api/rcars/api/schemas.py` (`CatalogItemResponse`)
- Modify: `src/api/rcars/db/database.py` (detail SELECT, ~line 1394)
- Test: `src/api/tests/test_description_analysis.py` (or the existing route-test file pattern from `tests/test_catalog_content_owner_routes.py`)

**Interfaces:**
- Consumes: `set_analysis_source` (Task 2), `require_curator`, `_resolve_to_content_id`, job creation pattern from `analyze_single` (`routes/analysis.py:1455`).
- Produces: `PUT /api/v1/catalog/{identifier}/analysis-source`, curator-only, body `AnalysisSourceRequest(source: Literal["showroom","agnosticv_description","custom_description"], custom_description: str | None = Field(default=None, max_length=20000))`. Calls `db.set_analysis_source` (map `ValueError` → HTTP 400 with its message), then enqueues `run_analysis` for the content_id with `force=False` and returns `{"job_id": job_id}`. Detail responses expose `analysis_source_override` and `custom_description`.

- [ ] **Step 1: Write failing tests** (FastAPI TestClient with the app's auth bypass — copy the dev-user pattern from `tests/test_app.py` / `test_catalog_content_owner_routes.py`): `test_analysis_source_endpoint_curator_ok` (200, job_id present, columns set), `test_analysis_source_endpoint_requires_curator` (regular user → 403), `test_analysis_source_endpoint_custom_without_text_400`, `test_analysis_source_endpoint_empty_description_400`, `test_catalog_detail_includes_analysis_source_fields`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the endpoint, request model, and the two detail-SELECT/schema additions.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `[RHDPCD-2264] Add curator endpoint for analysis source`

### Task 8: Frontend edit drawer

**Files:**
- Modify: `src/frontend/src/services/api.ts` (next to `overrideUrl`, ~line 113)
- Modify: `src/frontend/src/pages/BrowsePage.tsx` (EditDrawer props ~line 233, drawer body inside `babylonOnlyActions` after the URL Override block ~line 339)

**Interfaces:**
- Consumes: `PUT /catalog/{identifier}/analysis-source` (Task 7); detail fields `analysis_source_override`, `custom_description`.
- Produces: `api.setAnalysisSource(ciName: string, source: 'showroom' | 'agnosticv_description' | 'custom_description', customDescription?: string)`; an "Analysis Source" field in the edit drawer — three radio options labeled "Showroom (default)", "Use catalog description", "Custom description", a textarea shown only for custom (placeholder explaining it is analyzed once on save), and a "Set Source" button following the `flashSave` pattern of the neighboring URL Override control.

- [ ] **Step 1: Implement the api.ts client function.**
- [ ] **Step 2: Implement the drawer UI** — prefilled from `detail.analysis_source_override ?? 'showroom'` and `detail.custom_description`; state local to the drawer like `overrideUrl`; on save call `setAnalysisSource` then flash "Saved".
- [ ] **Step 3: Verify** — `cd src/frontend && npm run build`; expected: clean tsc + vite build.
- [ ] **Step 4: Commit** — `[RHDPCD-2264] Add analysis source control to Browse edit drawer`

### Task 9: Full verification

- [ ] **Step 1: Run the full suite** — from `src/api`: `python -m pytest tests/ -v -m "not integration"`; expected: all PASS (pre-existing failures, if any, must be unrelated and reported, not fixed silently).
- [ ] **Step 2: Update the knowledge graph** — `graphify update .` from the repo root (repo rule), commit the result.
- [ ] **Step 3: Commit any remaining pieces** — `[RHDPCD-2264] Complete description analysis feature` (only if loose ends remain; otherwise skip).
- [ ] **Step 4: Report** — update RHDPCD-2264 with a milestone comment (files changed, test evidence) and note the follow-up: deploy to dev with `--tags full`, set the override on a field-asset item, verify end to end. Deployment itself is outside this plan.
