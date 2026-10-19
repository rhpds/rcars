# Showroom Analysis Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The user has not selected an execution method; obtain that choice before implementation.

**Goal:** Isolate Showroom analysis to one item and its verified stages or explicit virtual content-owner relationship, then support rebuilding disposable Babylon scan artifacts without losing history.

**Architecture:** Resolve stage-specific content ownership independently of infrastructure inheritance. Schedule each resolved item stage independently; reuse analysis only after fetching and verifying an authorized scoped signature. Remove global content-based propagation and identity promotion, and offer a separately confirmed derived-artifact reset.

**Tech Stack:** Existing Python 3.11+, FastAPI/arq, psycopg/PostgreSQL/pgvector, pytest/pytest-asyncio; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-16-showroom-analysis-isolation-design.md` (approved conversation policy plus labeled engineering recommendations).

## Global Constraints

- RHDPCD-74 is the commit key only. Do not update its description, comments, or status.
- Different items scan independently even if all repository/ref/hash values match.
- Resolve each stage's component graph independently. Different stage configuration or content gets independent analysis.
- Explicit virtual/published-to-content-component relationships may share analysis. Do not restrict this to the `published` folder or to a fixed chain length.
- No source anywhere is a distinct, ordinary no-Showroom outcome.
- A missing or unresolvable requested ref fails; never silently clone the default branch.
- Routine unchanged items are not reanalyzed or re-embedded; explicit force/rebuild is the exception.
- Rebuild execution is an operational step requiring separate confirmation, not an automatic deploy/startup migration.
- Do not run `init-db --drop` or drop/truncate tables. Preserve all historical and curated data enumerated in the spec.
- Use feature branches; confirm Jira key before each commit; subjects start `[RHDPCD-74]`; include `Generated with OpenCode (openai/gpt-6.1-sol)` in commit bodies. Obtain explicit branch/remote/commit push approval. Do not include test results in commit messages.
- Never put real credentials or environment-specific endpoints in repository files. Fixtures use `https://github.com/example/...` or `https://api.example.com`.

## Review Focus

- Components without CatalogItems and four-level wrapper chains must resolve without requiring a content-entity row (Task 1).
- A ref-only override must retain its origin and must not reuse the base component's default-ref analysis (Tasks 1–3).
- Identical content hashes across independent items, including stale legacy donors, must never authorize reuse or promotion (Tasks 2–5).
- Branch/tag name collisions, annotated tags, full commit refs, moving HEAD, and vanished refs must never silently change the fetched source (Tasks 3–4).
- Reset must preserve curated duration/notes and history and reject outstanding scans; its runbook must require stopped producers/workers and drained old work before reset (Task 6).

## File map and verification conventions

New focused units: `services/showroom_source.py` for graph/source policy and `services/showroom_scan.py` for the shared non-queue scan/persistence orchestration. Retain database SQL in `db/database.py`; do not refactor unrelated database methods.

Modify `services/catalog.py`, `services/analyzer.py`, `workers/scan.py`, `workers/ops.py`, `cli.py`, `api/routes/analysis.py`, and `services/recommender/vector_search.py` only where they consume that policy. Add an operational reset script under `src/api/scripts/`, not a new dashboard.

Tests currently use module-local fixtures, not `tests/conftest.py`. New database test fixtures must require a database whose configured and effective names contain `test`; follow the safety checks in `tests/test_osspa_db.py`. Run database suites serially. All commands below run from `src/api` using `~/.virtualenvs/rcars-v2/bin/python`; set `RCARS_TEST_DATABASE_URL` outside repository files.

These tasks are sequential slices of one correctness change; do not deploy partial slices. Checkbox verification/commit steps require actual evidence and approval, not automatic commits.

---

### Task 1: Resolve content sources with explicit ownership

**Files:** Create `src/api/rcars/services/showroom_source.py`, `src/api/tests/test_showroom_source.py`; modify `src/api/rcars/services/catalog.py` (`extract_showroom_url`, component collection, `_apply_component_inheritance`); retain infra tests in `src/api/tests/test_services.py`.

**Interfaces:** Define frozen dataclasses `ComponentLink(target_ci_name: str, overrides: dict[str, str | None])`, `ContentDeclaration(repo: str | None, ref: str | None, content_path: str | None, provided_fields: frozenset[str])`, `SourceNode(ci_name: str, stage: str, declaration: ContentDeclaration, links: tuple[ComponentLink, ...])`, and `ResolvedShowroom(status: str, owner_ci_name: str | None, scope_key: str | None, repo: str | None, ref: str | None, content_path: str | None, paths: tuple[tuple[str, ...], ...], override_origins: dict[str, str], error: str | None)` in `showroom_source.py`.

`item_family_key(ci_name: str, stage: str) -> str` strips only an exact known stage suffix, keeping the namespace. `resolve_showroom_source(root_ci_name: str, nodes: dict[str, SourceNode], *, max_depth: int = 32) -> ResolvedShowroom` returns `resolved`, `none`, `ambiguous`, or `invalid`. `ResolvedShowroom.to_dict() -> dict` / `from_dict(data: dict) -> ResolvedShowroom` provide the persistence boundary.

- [ ] **Write failing resolver tests:** `test_four_level_chain_stops_at_content_owner` asserts the owner is `example.content.prod`, not `example.infra.prod`; `test_independent_roots_with_own_same_url_have_distinct_scopes` asserts unequal scope keys; `test_stage_paths_resolve_independently` asserts dev/event/prod retain their selected refs; `test_ref_override_creates_requester_scope` asserts the changed effective ref and overriding component's scope, not the unmodified owner's scope. Parameterize explicit repo/path overrides similarly; `test_explicit_default_head_does_not_inherit_deeper_ref` asserts `ref is None` for an explicitly defaulted ref.
- [ ] **Write graph boundary tests:** `test_owner_need_not_have_catalogitem`, `test_branch_with_two_sources_is_ambiguous`, `test_converging_paths_to_one_owner_are_unambiguous`, `test_cycle_is_invalid`, `test_missing_dependency_is_invalid`, `test_depth_32_allowed_33_invalid`, and `test_no_source_is_none`. Assert deterministic statuses/errors and complete provenance paths. A declaration with unresolved template variables is invalid, not no-source or permission to skip to a deeper default.
- [ ] **Run:** `~/.virtualenvs/rcars-v2/bin/python -m pytest tests/test_showroom_source.py -q` — expect failures before implementation.
- [ ] **Implement resolver and catalog adapter:** collect allowlisted declarations and edge overrides before mutating inherited fields. Fetch missing component CRDs recursively through the existing client even without CatalogItems, cache per refresh, and select stage-specific names. Apply nearer overrides field-by-field using the existing safe variable-resolution rules; never evaluate arbitrary Jinja or persist complete CRD definitions. Resolve each branch to its nearest declaration, merging only convergent identical owners. Preserve existing infra/workload inheritance separately and emit `showroom_source` plus effective URL/ref/path on each catalog item.
- [ ] **Run:** `~/.virtualenvs/rcars-v2/bin/python -m pytest tests/test_showroom_source.py tests/test_services.py -q` — expect PASS, including unchanged infra/workload tests. Add an adapter test with shuffled CRD order proving resolution is order-independent.
- [ ] **Commit after key confirmation:** `[RHDPCD-74] Resolve explicit Showroom content ownership` with required attribution; no push without approval.

### Task 2: Persist source provenance and enforce scoped analysis reuse

**Files:** Modify `src/api/rcars/db/database.py`; create `src/api/tests/test_showroom_scope_db.py`; extend `services/showroom_source.py`.

**Interfaces:** Add `babylon_items.showroom_source_json JSONB` and `showroom_analysis.analysis_provenance_json JSONB` with idempotent ALTER statements. Define `AnalysisSignature(scope_key: str, repo: str, ref: str | None, content_path: str | None, commit: str, content_hash: str, context_hash: str, input_hash: str, policy_version: int)` with `to_dict()`; `SHOWROOM_ANALYSIS_POLICY_VERSION = 1`. `context_hash` fingerprints non-content analysis inputs so unchanged-revision checks need not clone just to recompute the full `input_hash`.

Replace `Database.find_donor_by_content_hash` with `find_showroom_donor(signature: AnalysisSignature, *, exclude_content_id: str) -> dict | None`. Add `get_stage_counterpart(content_id: str, stage: str) -> dict | None`. All persisted source dictionaries use Task 1's shape; provenance contains `signature`, `source`, `generated_for`, `generated_commit`, `reused_from`, and `embedding_fingerprints` (summary and per-module hashes of actual text plus embedding model/configuration). `signature.commit` is the latest verified content revision; `generated_commit` and `last_analyzed` retain the original LLM generation revision/time when a newer commit changes no relevant content.

- [ ] **Write failing DB tests:** `test_same_item_matching_signature_reuses_stage` finds the prod donor for dev; `test_unrelated_identical_repo_ref_sha_hash_is_not_donor` returns None; parameterize every signature field mismatch; `test_stale_failed_retired_or_legacy_donor_is_rejected` returns None. `test_source_and_analysis_provenance_round_trip` compares complete dictionaries. `test_stage_counterpart_does_not_match_lab_numbers_or_infrastructure_base` returns only the exact family counterpart.
- [ ] **Run:** `~/.virtualenvs/rcars-v2/bin/python -m pytest tests/test_showroom_scope_db.py -q` — expect FAIL against current schema/interfaces.
- [ ] **Implement additive schema/upsert/read support:** persist source metadata, allow provenance through analysis upsert, match the complete signature, require active successful donors with complete summary/module artifacts, and return the exact namespace-qualified stage counterpart. Legacy analyses without versioned provenance cannot donate.
- [ ] **Remove URL/ref dedup from `get_items_needing_analysis`:** return each eligible resolved stage that needs work, including virtual rows, not every catalog stage. Require current valid provenance, matching source/context, and complete up-to-date embeddings to skip an item; schedule only analysis or embedding repair actually needed. Add `test_unchanged_complete_item_is_not_selected` and `test_missing_embedding_is_selected_for_repair`. Explicitly surface ambiguous/invalid source status without turning it into an ordinary sandbox or deleting curated fields. `get_scan_dedup_stats` must describe actual stage jobs rather than imply cross-item fan-out.
- [ ] **Run the new suite serially**, then existing `tests/test_db.py`, and verify calling `create_schema()` twice preserves data and new columns.
- [ ] **Commit after key confirmation:** `[RHDPCD-74] Scope Showroom reuse to verified content owners` with required attribution.

### Task 3: Fetch the exact source and reject non-content inputs

**Files:** Modify `src/api/rcars/services/analyzer.py`, `src/api/tests/test_analyzer.py`; create `src/api/tests/test_showroom_reuse.py`.

**Interfaces:** Extend `analyze_showroom(..., source: ResolvedShowroom, force: bool = False)` with required keyword-only resolved source while preserving existing item metadata arguments. Return `analysis_provenance` alongside existing analysis/embedding fields. Add `compute_analysis_input_hash(system_prompt: str, user_message: str, model: str) -> str`, `compute_analysis_context_hash(system_prompt: str, canonical_item_info: str, model: str) -> str`, and `compute_embedding_fingerprint(text: str, model: str, configuration: dict) -> str`. These use the actual effective inputs, not only configuration names. Extend `check_showroom_stale(..., content_path: str | None = None)` to use the scan's selected path.

- [ ] **Write failing source tests:** branch and lightweight/annotated tag fetches produce the expected commit; a full commit-ID ref fetches that commit; a missing ref returns a classified `invalid_ref` failure without fetching default HEAD; ambiguous short branch/tag names fail until qualified. Use temporary local Git repositories, not network services.
- [ ] **Write filtering tests:** `test_substantive_index_is_retained`, `test_nav_and_publishing_house_stub_return_no_content_before_lookup_or_llm`, `test_valid_short_overview_is_analyzable`, and `test_scan_and_stale_check_use_identical_content_path`. Assert the nav-only failure never calls the donor lookup, LLM, or embedder. Include containment rejection for `../` paths and symlinks leaving the clone.
- [ ] **Write reuse tests:** exact same scoped signature reuses analysis with zero LLM calls; changing scope/repo/ref/commit/path/content/prompt/model prevents reuse; force bypasses every donor; copied analysis generates the target's own summary embedding text with its display name/keywords. `test_curator_url_or_path_override_is_target_scoped` asserts the existing target override wins and cannot borrow the unmodified base analysis. Assert complete returned provenance and no lookup through the removed global method.
- [ ] **Write incremental tests:** `test_identical_revision_and_context_skips_clone_llm_and_embeddings` asserts zero calls to all three; `test_new_commit_same_selected_content_only_advances_verified_revision` asserts zero LLM/embedding calls and unchanged `generated_commit`/`last_analyzed`; `test_second_check_of_verified_revision_skips_clone` proves the irrelevant commit is not refetched repeatedly. `test_keyword_only_change_repairs_summary_embedding_without_llm`, `test_embedding_model_change_repairs_embeddings_without_llm`, and `test_missing_module_embedding_repairs_only_missing_artifact` assert narrowly scoped repair. `test_changed_prompt_context_invalidates_unchanged_git_revision` asserts analysis is not incorrectly skipped; `test_force_bypasses_unchanged_fast_path` asserts fresh analysis and embedding calls.
- [ ] **Run:** `~/.virtualenvs/rcars-v2/bin/python -m pytest tests/test_analyzer.py tests/test_showroom_reuse.py -q` — capture red results before implementation.
- [ ] **Implement strict Git fetch/checkout and source validation:** resolve the requested branch/tag/commit, fetch and verify the exact detached commit, and remove default-branch fallback. Stop navigation/template-only inputs before hashing/reuse. Keep substantive index pages, use the canonical stage-independent scope name in the prompt, and hash the actual full system/user prompts plus model. Construct Task 2's signature only after reading the verified checkout, then use the scoped donor method. Preserve raw target identity in logs and embedding metadata.
- [ ] **Implement incremental decisions before expensive work:** verify the current source/revision and non-content analysis context against that item's own provenance first. Reuse its own valid analysis/embeddings without cloning when unchanged; on a new revision compare selected content and context before deciding to call the LLM. Advance verified-revision metadata without altering generation history on content-identical commits. Evaluate embedding fingerprints independently; only missing/changed artifacts call the embedder. The separate scoped donor lookup still requires its complete authorized signature and cannot become an unrestricted self-cache shortcut.
- [ ] **Run the suites to PASS** and verify no new real LLM calls or external endpoints are needed by the tests.
- [ ] **Commit after key confirmation:** `[RHDPCD-74] Verify exact Showroom inputs before analysis reuse` with required attribution.

### Task 4: Unify scan persistence and remove cross-item fan-out

**Files:** Create `src/api/rcars/services/showroom_scan.py`, `src/api/tests/test_showroom_scan.py`; modify `workers/scan.py`, `workers/ops.py`, `cli.py`, `api/routes/analysis.py`, and scan-management SQL in `db/database.py`.

**Interfaces:** `scan_babylon_item(db, settings, content_id: str, *, force: bool = False) -> dict` in `showroom_scan.py` owns source loading, analyzer invocation, analysis/card/embedding persistence, and per-item outcome. Queue/job lifecycle stays in `run_analysis`. Persistence locks and rechecks the target's source metadata inside its write transaction; work whose source changed returns `superseded`, not success. Add optional transaction connection arguments to the existing artifact writers so signature, analysis, card, and embeddings commit together. Never hold a database lock during Git/LLM calls.

- [ ] **Write failing orchestration tests:** running item A cannot write item B even with identical URL/ref/SHA; an explicit four-level virtual item materializes its own analysis using the allowed owner scope; failed/template-only items do not gain donor content; target card/embeddings and durable donor provenance correspond to the target. Test changed source configuration during a scan discards results. Mock LLM/Git/embedding services and capture writes.
- [ ] **Write queue/CLI tests:** scan-all, maintenance, CLI scan, and individual rescan enqueue/process each eligible stage needing work, not every valid stage; `test_unchanged_maintenance_enqueues_no_analysis_jobs` asserts zero scan submissions and zero LLM/embedding calls; rescan-all passes `force=True`; failed source resolution is visible. Use `click.testing.CliRunner` and mocked Redis; never launch real maintenance.
- [ ] **Run:** `~/.virtualenvs/rcars-v2/bin/python -m pytest tests/test_showroom_scan.py -q` — expect FAIL.
- [ ] **Implement shared orchestration:** worker and CLI call the same persistence service. Remove `_propagate_to_sibling`, URL/ref sibling fan-out, SHA sibling fan-out, unconditional published fan-out, and `sha_dedup_scan_items` from all callers. During rollout, accept but ignore legacy `sha_siblings` job payloads. Virtual items get their own stage jobs only when needed and verified scoped reuse; no arbitrary published-prefix exclusion. Stale checks operate per item's verified source/path/context with Task 3's incremental rules, never clear another item's stale state solely because it shares a URL/ref. Embedding-only changes do not require fresh analysis. Record `unchanged`, `revision_verified`, `embeddings_repaired`, `analyzed`, `reused_from`, source/signature, and superseded outcomes in job results/logs; unchanged paths do not rewrite generated artifacts.
- [ ] **Run scan, analyzer, resolver, and DB suites serially to PASS.** Search all callers for removed global donor/sibling/SHA helpers and update endpoint/docstrings/stats to match actual behavior; assert no request handler performs an LLM call.
- [ ] **Commit after key confirmation:** `[RHDPCD-74] Remove cross-item scan propagation` with required attribution.

### Task 5: Keep recommendation identities within authorized relationships

**Files:** Modify `src/api/rcars/services/recommender/vector_search.py`, `src/api/rcars/db/database.py`; create `src/api/tests/test_showroom_recommendation_isolation.py`.

**Interfaces:** Consume Task 2's `get_stage_counterpart` and stored signatures. Add `Database.get_virtual_content_aliases(content_id: str) -> list[dict]`, returning only resolved, active, explicit content-delegation aliases in that stage; do not derive aliases from shared infra bases. `signatures_match(left: AnalysisSignature, right: AnalysisSignature) -> bool` lives in `showroom_source.py` and checks all signature fields.

- [ ] **Write failing recommendation tests:** unrelated same-hash prod identity cannot replace dev; exact same-item prod can replace dev only with matching signatures and requested prod access; different ref/hash/path remains independent; scoped queries never promote outside requested content IDs; explicit multi-hop virtual aliases are recognized; common infrastructure bases are not aliases. Multiple eligible virtual identities are not resolved by arbitrary first-row selection (retain separately scoped requested identities instead).
- [ ] **Run:** `~/.virtualenvs/rcars-v2/bin/python -m pytest tests/test_showroom_recommendation_isolation.py -q` — expect FAIL against global promotion.
- [ ] **Replace `find_prod_ci_by_content_hash` use and remove the method:** compare only verified exact stage counterparts. Resolve virtual promotion through recorded source relationships and matching signatures, respecting stages and scopes. Hydrate the selected row's own materialized analysis instead of guessing through generic `base_ci_name`. Preserve independent content IDs and their scores through deduplication.
- [ ] **Run the new suite and existing recommendation/chat tests serially to PASS.** Inspect both vector-search entry points and item hydration consumers for residual content-hash identity substitution.
- [ ] **Commit after key confirmation:** `[RHDPCD-74] Restrict recommendation promotion to verified item links` with required attribution.

### Task 6: Add a narrowly scoped reset and verify the full rebuild contract

**Files:** Create `src/api/scripts/rebuild_babylon_analysis.py`, `src/api/tests/test_showroom_rebuild.py`, `docs/operations/showroom-analysis-rebuild.md`; modify `db/database.py` for reset/generation operations.

**Interfaces:** `Database.reset_babylon_scan_artifacts(content_ids: list[str]) -> dict[str, int]` resets only enumerated Babylon-derived fields, summary/module embeddings, and overlap candidates involving those IDs in one transaction. Script `main(argv: list[str] | None = None) -> int` defaults to dry run; `--execute --confirm-scans-paused` explicitly authorizes reset and attests to the maintenance prerequisites, not a general schema drop. Reuse the existing CLI scan after refreshed sources and reset rather than adding another scanner.

- [ ] **Write failing preservation tests:** seed a target's analysis/card/summary+module embeddings, curated duration/notes/review metadata, performance/nonprod/field-source data, advisor/job/token history, retirement workflow, retired status, enrichment, and an unrelated architecture. Assert reset clears only generated target fields/artifacts, keeps curated and historical values byte-for-byte, leaves OSSPA artifacts untouched, rejects non-Babylon IDs, and invalidates relevant overlap results. Add `test_reset_rejects_running_or_queued_analysis_jobs`, `test_execute_requires_scans_paused_confirmation`, and `test_dry_run_performs_no_writes`.
- [ ] **Run:** `~/.virtualenvs/rcars-v2/bin/python -m pytest tests/test_showroom_rebuild.py -q` — expect FAIL.
- [ ] **Implement explicit field-level reset:** retain analysis rows containing human fields while nulling generated analysis/provenance/freshness fields; clear the corresponding generated entity-card fields and reset scan state. Do not delete content entities, Babylon metadata, histories, or curated fields. Reject queued/running scan-related work. Document stopping all scheduled/manual producers and scan processes (including CLI scans), draining old jobs, refreshing catalog sources, dry-running the selected reset, explicit execution approval, rebuilding per-stage scans, and recomputing overlaps after scan completion. A DB job check alone cannot prove the system is quiescent: require the operator's explicit maintenance confirmation and do not claim race safety while producers are running.
- [ ] **Run the complete local non-integration suite serially:** `~/.virtualenvs/rcars-v2/bin/python -m pytest tests/ -m 'not integration and not llm_eval' -q`. Run `graphify update .` after implementation and inspect tracked diffs for unintended files or sensitive values. Do not run additional secret scanners; rely on the installed pre-commit hook.
- [ ] **Commit after key confirmation:** `[RHDPCD-74] Rebuild Babylon scan artifacts without losing history` with required attribution. Before any push state branch, remote, and commit list, and obtain explicit approval. Follow PR template and attribution rules; wait for CodeRabbit before merge.
- [ ] **After push/deployment approval, deploy API only to dev:** use the existing Ansible API deployment with a securely supplied feature ref or approved merge; do not change committed environment endpoints or use uncommitted binary builds. Verify schema additions and a small four-level/same-item/different-item fixture set before the bulk rebuild. No frontend build is needed.
- [ ] **After separate reset/rebuild confirmation:** record preservation snapshots, execute the dry-run-reviewed reset in the supplied dev environment, rebuild, and verify LB2081b/c report insufficient content rather than Ansible while LB2081a retains correct PQC analysis. Verify different stage refs and an explicit multi-hop virtual CI, fresh embeddings, and preserved history. Production rebuild is not authorized by this plan.

## Self-review

All approved boundaries map to Tasks 1–5; disposable-artifact recreation and historical preservation map to Task 6. Review-focus failures have named owning tests. Source dictionaries, analysis signatures, and helper names are defined before downstream use. Existing infra inheritance remains outside content resolution; no general-purpose migration, generation-tracking subsystem, infrastructure classifier, cross-item fetch optimization, frontend feature, automatic reset, or production operation is included.

## Execution handoff

Review the proposed engineering choices in the spec: 32-level limit, structured provenance, one job per item stage, versioned signatures, atomic source-checked persistence, and an opt-in reset tool used only in a maintenance window. Choose native execution or subagent-driven execution before implementation. Native is recommended: tasks share the resolver/signature/persistence interfaces, so keeping that context in one implementation session avoids repeated handoffs; obtain a whole-branch independent review afterward.
