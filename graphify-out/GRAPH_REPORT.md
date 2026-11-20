# Graph Report - rhdpcd-2266  (2026-11-20)

## Corpus Check
- 330 files · ~548,376 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4218 nodes · 10510 edges · 221 communities (156 shown, 65 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 1291 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c7ffeef5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _FakeResponse
- Database
- patch
- Portfolio Architecture Ingest Design Spec
- test_description_analysis.py
- devDependencies
- cli.py
- db/__init__.py
- routes/catalog.py
- admin.py
- test_retirement_jira_events.py
- Infrastructure Catalog
- BrowsePage.tsx
- test_overlap_assessment.py
- TestStepOrder
- Generalized Content Model Design
- common.yml
- ops.py
- generate_embedding
- with
- routes/auth.py
- .upsert_babylon_catalog_item
- test_content_owner.py
- test_osspa_adoc.py
- react
- Settings
- re
- test_showroom_source.py
- schemas.py
- seed
- App.tsx
- settings.py
- test_agv_access.py
- _generate_key
- JobProgressRelay
- ContentAnalysisPage.tsx
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- Review Focus
- compilerOptions
- test_jira_service.py
- advisor.py
- handlers.py
- test_analyzer.py
- test_osspa_csv.py
- compute_sales_impact
- api.ts
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- analysis.py
- TestSpoofedProxyHeaders
- sync_opl_vocabulary.py
- Vocabulary
- Task 3: Return labels from the three analysis endpoints
- Path
- run_osspa_sync
- loader.py
- Retirement System
- parse_analysis_response
- analyze_architecture_item
- test_catalog_osspa_routes.py
- SyncPage.tsx
- Candidate
- search
- HandsOnDriver
- reporting_sync.py
- json
- test_workers.py
- api.ts
- ECA Production Redesign Spec
- vocabulary.yaml
- migrate_to_content_model.py
- analyzer.py
- Reporting MCP Data Sync
- pre_tasks
- TestValidation
- _user_has_db_role
- cli.py
- pipeline.py
- test_test_content_exclusion.py
- build_retirement_description
- test_nonprod.py
- test_retirement_pr_status.py
- jira.py
- middleware/auth.py
- AnalysisSignature
- ArchitectureDriver
- build_retirement_description
- block
- System Design Architecture Doc
- AdocRead
- test_showroom_scan.py
- asyncio
- Showroom analysis isolation
- Scan Pipeline
- normalize_row
- Browse Page Redesign Plan
- API Authentication Design
- is_content_excluded
- Candidate
- test_vocabulary_admin.py
- rcars-login.sh
- workload_scanner.py
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- Advisor v2 — Content-Type Drivers
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- post_tasks
- Task 2: Union labels per base name
- Platform and Technical Decision Point filters — design
- content_entities Table
- .close
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- test_reporting.py
- action_verbs
- build_embedding_text
- ContentTypeDriver
- test_orphan_cleanup.py
- retirement_cleanup.py
- test_llm_routing.py
- .create_job
- content_owner
- .list_content_entities_filtered
- Python Dependency Manifest (requirements.lock)
- reporting_db_show
- _FakeResponse
- TestVocabularyEndpoints
- router.py
- File map and verification conventions
- database.py
- docker-entrypoint.sh
- Webhook Configuration Task
- showroom_source.py
- OpenShift OAuth Proxy (Red Hat SSO)
- Follow-up Chips
- Item Facts Intent
- retirement-system.md
- advisor_sessions Table
- Base Config Type
- Workload Role Type
- Time Windows
- CI Name Resolution
- Duration-Aware Reranking
- Event URL Mode
- Phase 2 Haiku Triage
- Phase 3 Sonnet Rationale
- Scan Deduplication and Propagation
- Plan 1: Foundation and Catalog Reader
- Plan 2: Analysis and Recommendations
- Plan 3c: OpenShift Deployment
- Plan: Async Advisor Query
- Plan: Recommender Redesign (Three-Phase Pipeline)
- Plan: Token Usage Tracking
- Plan: Advisor List Persistence and Feedback
- Plan: Scan Failures and Catalog Visibility
- Plan: Rearchitecture to Three-Tier
- LLM Overlap Assessment Plan
- LLM Overlap Assessment Design
- rcars
- rcars
- _parse_sa_allowlist
- Match Event Prompt Template
- extract_base_name
- deploy.yml
- test_showroom_reuse.py
- test_vocabulary.py
- Python Requirements Entry Point
- MemoryArtifacts
- hashlib
- TestTokenExchange
- tasks
- _sync_nonprod_usage
- rationale.py
- test_catalog_labels.py
- mcp_query
- readiness
- Path
- test_config_scanner.py
- Field Source Content
- .get_unknown_terms
- recommend.py
- git_repo
- workflow_lock_id
- .get_babylon_item_by_ci_name
- ignored_terms
- Controlled Vocabulary Design
- .upsert_infrastructure
- order_for_reuse
- content_modes
- build_infrastructure_embedding_text
- TestPromptInjection
- db_with_perf_data
- clone_showroom
- _reset_token_cache
- test_drivers.py
- kubernetes.core.k8s_exec
- collections
- solutions
- _jira_event_messages
- ansible.builtin.assert
- CatalogReader

## God Nodes (most connected - your core abstractions)
1. `Database` - 306 edges
2. `Settings` - 181 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `seed()` - 46 edges
6. `scan_babylon_item()` - 45 edges
7. `create_app()` - 41 edges
8. `run_retirement_sweep()` - 40 edges
9. `ResolvedShowroom` - 39 edges
10. `content_owner()` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Review Focus` --references--> `run_category()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/pipeline.py
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Summary` --references--> `isArchitecture()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/frontend/src/pages/browse/helpers.ts
- `Curator edits` --references--> `content_owner()`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Content Analysis Pipeline (Vocabulary + Showroom Analysis + Overlap Assessment)** — src_api_rcars_data_vocabulary_controlled_vocabulary, src_api_rcars_prompts_analyze_showroom_analysis_prompt, src_api_rcars_prompts_overlap_assessment_overlap_prompt, src_api_rcars_prompts_analyze_showroom_learning_objectives [EXTRACTED 0.95]
- **System Evolution from Monolith to Multi-Tier** — docs_superpowers_specs_2026-04-07-eca-production-redesign-design, docs_superpowers_specs_2026-04-08-rcars-plan3a-web-ui-design, docs_superpowers_specs_2026-04-25-rearchitecture-api-design, concept_rearchitecture [EXTRACTED 0.95]
- **OSSPA Ingest Stack — CSV + Clone + Upsert + Analyze + Embed** — claude_md_osspa_sync_pipeline, claude_md_palist_csv, claude_md_osspa_gitlab_repos, claude_md_portfolio_architectures_table, claude_md_architecture_analysis_table, claude_md_content_entities_table, claude_md_llm_architecture_analysis, claude_md_embedding_model_nomic [EXTRACTED 0.95]
- **Performance Analysis Feature Stack** — concept_reporting_mcp_sync, concept_performance_scoring, concept_retirement_workflow, docs_superpowers_plans_2026-08-04-performance-page [EXTRACTED 0.95]
- **Multi-Intent Chat System** — docs_architecture_advisor_chat_router, docs_architecture_advisor_chat_intent_recommend, docs_architecture_advisor_chat_intent_overlap, docs_architecture_advisor_chat_intent_performance, docs_architecture_advisor_chat_intent_infrastructure, docs_architecture_advisor_chat_intent_item_facts [EXTRACTED 1.00]
- **Ansible Deployment Pipeline** — ansible_deploy_playbook, ansible_tasks_apply_infra, ansible_tasks_apply_manifests, ansible_tasks_build_api, ansible_tasks_build_frontend, ansible_tasks_smoke_test, ansible_tasks_namespace, ansible_vars_common [EXTRACTED 1.00]
- **Generalized Content Model Core Tables** — docs_superpowers_specs_2026_07_20_generalized_content_model_design_content_entities, docs_superpowers_specs_2026_07_20_generalized_content_model_design_babylon_items, docs_superpowers_specs_2026_07_20_generalized_content_model_design_embeddings, docs_superpowers_specs_2026_07_20_generalized_content_model_design_performance_channels [EXTRACTED 1.00]
- **RCARS Core Four Deployments on OpenShift** — claude_md_rcars_react_spa, claude_md_rcars_fastapi_api, claude_md_rcars_scan_worker, claude_md_rcars_recommend_worker, claude_md_rcars_postgresql, claude_md_rcars_redis [EXTRACTED 1.00]
- **Three-Phase Recommendation Pipeline** — docs_architecture_recommendation_engine_vector_search, docs_architecture_recommendation_engine_haiku_triage, docs_architecture_recommendation_engine_sonnet_rationale [EXTRACTED 1.00]
- **RCARS Taxonomy System (Products, Solutions, Verticals, Platforms, Difficulty)** — src_api_rcars_data_vocabulary_products_taxonomy, src_api_rcars_data_vocabulary_solutions_taxonomy, src_api_rcars_data_vocabulary_verticals_taxonomy, src_api_rcars_data_vocabulary_platforms_taxonomy, src_api_rcars_data_vocabulary_difficulty_levels [EXTRACTED 1.00]
- **Authentication and Authorization Evolution** — concept_api_key_auth, concept_openshift_group_auth, docs_superpowers_plans_2026-07-03-api-authentication, docs_superpowers_plans_2026-08-05-openshift-group-auth [INFERRED 0.85]
- **Content Visibility Gate — Status + Vector Search + Browse** — claude_md_content_entities_status, claude_md_vector_similarity_search, claude_md_browse_integration, claude_md_content_entities_table [INFERRED 0.85]
- **LLM Infrastructure (Anthropic + OpenAI SDKs + Prompt Templates)** — src_api_requirements_lock_anthropic, src_api_requirements_lock_openai, src_api_rcars_prompts_analyze_showroom_analysis_prompt, src_api_rcars_prompts_overlap_assessment_overlap_prompt [INFERRED 0.85]
- **Authentication and Access Control System** — docs_superpowers_specs_2026_07_03_api_authentication_design_api_keys, docs_superpowers_specs_2026_07_03_api_authentication_design_oauth_login, docs_superpowers_specs_2026_07_03_api_authentication_design_proxy_verification, docs_superpowers_specs_2026_08_05_role_assignments_design_role_assignments_table [INFERRED 0.95]
- **Recommendation Pipeline LLM Prompts** — src_api_rcars_prompts_triage, src_api_rcars_prompts_rationale, src_api_rcars_prompts_rationale_single, src_api_rcars_prompts_rationale_synthesis [INFERRED 0.95]

## Communities (221 total, 65 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.13
Nodes (14): _jira_request(), _move_to_in_progress(), _oauth_config(), _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen() (+6 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (5): Database, _do(), test_advisor_session(), test_enrichment_tags(), test_database_explicit_test_schema_reset_includes_delivery_queue()

### Community 2 - "patch"
Cohesion: 0.14
Nodes (9): _fetch_group_members(), _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response(), TestGroupLookup (+1 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.21
Nodes (16): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis, OSSPA GitLab Repositories (+8 more)

### Community 4 - "test_description_analysis.py"
Cohesion: 0.12
Nodes (46): Task 2: `Database.set_analysis_source()` setter, Task 4: Candidate selection, Task 7: API endpoint + detail fields, AnalysisSourceRequest, set_analysis_source(), add_description_item(), add_item(), analyzed_description_item() (+38 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (49): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, react-dom (+41 more)

### Community 6 - "cli.py"
Cohesion: 0.12
Nodes (10): concurrency, cancel-in-progress, group, cli(), infra_group(), osspa_group(), reporting_db_group(), retirement_group() (+2 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.13
Nodes (13): overlap_report(), generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), seed_items(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item() (+5 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.10
Nodes (30): Task 9: Curator edits on a stub write the owner's analysis row, add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+22 more)

### Community 9 - "admin.py"
Cohesion: 0.12
Nodes (26): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+18 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.07
Nodes (39): ensure_issue_event_comment(), deliver_pending_events(), client(), comments(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request() (+31 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.11
Nodes (35): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+27 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (24): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+16 more)

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "common.yml"
Cohesion: 0.03
Nodes (58): admin_emails, api_cpu_limit, api_cpu_request, api_memory_limit, api_memory_request, api_replicas, app_name, app_port (+50 more)

### Community 17 - "ops.py"
Cohesion: 0.12
Nodes (17): Decisions (Nate, 2026-11-19), run_field_source_sync(), build_sandbox_summary(), publish_progress(), WorkerContext, _progress_bridge(), _publish(), run_babylon_pipeline() (+9 more)

### Community 18 - "generate_embedding"
Cohesion: 0.16
Nodes (7): generate_embedding(), _get_embedding_client(), analyze_config(), analyze_role(), _normalize_products(), _vocabulary_product_hint(), test_analyze_role_returns_enriched_fields()

### Community 19 - "with"
Cohesion: 0.07
Nodes (31): runs-on, steps, environment, needs, runs-on, steps, name, url (+23 more)

### Community 20 - "routes/auth.py"
Cohesion: 0.19
Nodes (15): invalidate_api_key_cache(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token(), _user_max_role() (+7 more)

### Community 21 - ".upsert_babylon_catalog_item"
Cohesion: 0.12
Nodes (20): test_content_path(), test_list_catalog_items(), test_retire_missing_babylon_ignores_other_sources(), _arch(), _seed_nonprod(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_maps_retirement_to_sibling_stages() (+12 more)

### Community 22 - "test_content_owner.py"
Cohesion: 0.14
Nodes (32): Task 4: Reconcile stub artifacts at every scan entry point, rescan_all(), start_scan(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts() (+24 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.05
Nodes (62): Task 8: Frontend Refactor, react, BlockErrorBoundary, Props, State, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl() (+54 more)

### Community 25 - "Settings"
Cohesion: 0.04
Nodes (47): create_app(), submit_chat(), submit_query(), auth_me(), list_catalog(), fetch_litemaas_models(), _parse_csv(), Settings (+39 more)

### Community 26 - "re"
Cohesion: 0.11
Nodes (20): _call_litemaas_inner(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), _expand_vocab_aliases(), _extract_json(), route() (+12 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.25
Nodes (22): Task 1: Resolve content sources with explicit ownership, ComponentLink, node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_converging_paths_to_one_owner_are_unambiguous(), test_curator_content_path_override_is_not_a_pure_stub(), test_depth_32_allowed_33_invalid() (+14 more)

### Community 28 - "schemas.py"
Cohesion: 0.06
Nodes (57): field_source_report(), AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse, CatalogStatsResponse (+49 more)

### Community 29 - "seed"
Cohesion: 0.08
Nodes (43): Task 2: Persist source provenance and enforce scoped analysis reuse, Task 6: Add a narrowly scoped reset and verify the full rebuild contract, Task 6: Advisor shows the stub in place of its owner, ResolvedShowroom, main(), snapshots(), test_dry_run_performs_no_writes(), test_execute_requires_scans_paused_confirmation() (+35 more)

### Community 30 - "App.tsx"
Cohesion: 0.07
Nodes (41): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), LlmProviderCard() (+33 more)

### Community 31 - "settings.py"
Cohesion: 0.10
Nodes (15): _add_component(), get_logger(), _reorder_keys(), setup_logging(), run_chat_turn(), on_progress(), cleanup_orphaned_jobs(), recommend_startup() (+7 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (71): References, AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr() (+63 more)

### Community 33 - "_generate_key"
Cohesion: 0.17
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 34 - "JobProgressRelay"
Cohesion: 0.13
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 35 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.23
Nodes (10): Controlled Vocabulary, Difficulty Levels Taxonomy, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy, Learning Objectives Extraction (Stated + Inferred), Module-Level Analysis Output (+2 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.13
Nodes (5): load_vocabulary(), _noise_variants(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "Review Focus"
Cohesion: 0.12
Nodes (13): Global Constraints, Platform and TDP Filters Implementation Plan, Review Focus, Task 4: Browse server-side filters and facets, Task 5: Shared frontend helpers and checkbox filter group, Task 7: Browse UI (provisional style), Task 8: Run locally, check, and prepare the PR, test_facets_platforms_and_tdps() (+5 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.26
Nodes (15): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_creates_ticket_and_returns_key() (+7 more)

### Community 42 - "advisor.py"
Cohesion: 0.09
Nodes (13): _get_user_key(), ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest (+5 more)

### Community 43 - "handlers.py"
Cohesion: 0.08
Nodes (26): get_item_workloads(), get_performance_scores(), get_session_context(), next_turn_index(), session_owner_ok(), _prefix_overlap(), _detect_type_hint(), handle_help() (+18 more)

### Community 44 - "test_analyzer.py"
Cohesion: 0.11
Nodes (23): check_showroom_stale(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content(), test_content_path_antora_start_path_resolves_pages_and_nav(), test_content_path_containment() (+15 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (19): asset_type_tokens(), fetch_palist_csv(), OsspaSyncError, parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status() (+11 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.13
Nodes (5): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), TestComputePerformanceScore

### Community 47 - "api.ts"
Cohesion: 0.08
Nodes (56): Task 6: Wire filters into Performance, Non-Prod and Retirement, CollapsibleFilterGroup(), CollapsibleFilterGroupProps, render(), LabelFilterGroup(), LabelFilterGroupProps, fmtTargetDate(), isInProgress() (+48 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.12
Nodes (4): normalize_analysis(), _record_unknowns(), TestIgnoredTermsSuppression, TestNormalizeAnalysis

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "_expand_query_terms"
Cohesion: 0.09
Nodes (7): _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 51 - "analysis.py"
Cohesion: 0.11
Nodes (33): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_pr_statuses(), check_stale(), edit_retirement() (+25 more)

### Community 53 - "sync_opl_vocabulary.py"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 54 - "Vocabulary"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "Task 3: Return labels from the three analysis endpoints"
Cohesion: 0.13
Nodes (10): Task 3: Return labels from the three analysis endpoints, _extract_base_name_from_content_id(), nonprod_dashboard(), performance_dashboard(), retirement_dashboard(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels() (+2 more)

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.33
Nodes (16): run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items(), test_missing_detail_page_marks_stale_and_skips() (+8 more)

### Community 58 - "loader.py"
Cohesion: 0.12
Nodes (12): _entries_to_dicts(), _as_tuple(), _build_lookups(), _parse_entries(), _validate(), squash_key(), VocabEntry, Vocabulary (+4 more)

### Community 59 - "Retirement System"
Cohesion: 0.08
Nodes (25): AgV Access Layer, Architecture, Authentication and Scope, Automatic Removal Eligibility, Cancellation and Recovery, Catalog Soft-Delete, Checking Merges, Code Organization (+17 more)

### Community 60 - "parse_analysis_response"
Cohesion: 0.15
Nodes (7): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), _strip_html(), _validate_url()

### Community 61 - "analyze_architecture_item"
Cohesion: 0.16
Nodes (11): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms(), test_analyze_uses_the_dedicated_model_when_configured() (+3 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.13
Nodes (9): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures() (+1 more)

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "Candidate"
Cohesion: 0.13
Nodes (7): Delete, File Map, Task 1: Candidate Model Refactor, Task 2: Driver Base Class + Registry, Task 4: Architecture Driver, Candidate, test_candidate_similarity_pct()

### Community 65 - "search"
Cohesion: 0.13
Nodes (11): _row(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override(), test_schema_backfills_status_from_stage() (+3 more)

### Community 66 - "HandsOnDriver"
Cohesion: 0.17
Nodes (9): Task 3: Hands-on Driver, _extract_duration_target(), HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming(), test_hands_on_serialize_with_performance() (+1 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.09
Nodes (15): Task 2: Reporting Sync Job, _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql() (+7 more)

### Community 68 - "json"
Cohesion: 0.23
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 69 - "test_workers.py"
Cohesion: 0.21
Nodes (9): WorkerSettings, test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes(), test_worker_context_has_required_fields() (+1 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (28): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+20 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 73 - "migrate_to_content_model.py"
Cohesion: 0.13
Nodes (14): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+6 more)

### Community 74 - "analyzer.py"
Cohesion: 0.10
Nodes (30): Task 3: `analyze_description()` in the analyzer, 3. Scan pipeline branch, call_llm(), analysis_context_hash(), analysis_from_row(), analyze_description(), analyze_showroom(), build_analysis_prompt() (+22 more)

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (6): Retirement Analysis Integration Plan, Retirement Workflow Actions Plan, Generalized Content Model Plan, Overlap Analysis Redesign Plan, Advisor Multi-Intent Chat Plan, Performance Page Plan

### Community 76 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "_user_has_db_role"
Cohesion: 0.25
Nodes (3): _get_cached_role_assignments(), _user_has_db_role(), TestDbRoleCheck

### Community 79 - "cli.py"
Cohesion: 0.09
Nodes (24): command, flag(), get_db(), infra_stats(), init_db(), note(), osspa_sync_cmd(), overlap_candidates_cmd() (+16 more)

### Community 80 - "pipeline.py"
Cohesion: 0.08
Nodes (21): Modify, Task 6: Orchestrator + Pipeline Refactor, 2. Orchestrator and Pipeline, What Gets Deleted, RequestLoggingMiddleware, registered_content_types(), QueryState, extract_urls() (+13 more)

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.12
Nodes (16): resolve_showroom_source(), unresolved(), walk(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(), test_cached_overlap_cannot_bypass_test_content_exclusion(), test_existing_test_vectors_never_enter_content_retrieval(), test_ignored_test_dependency_does_not_block_a_real_content_branch() (+8 more)

### Community 82 - "build_retirement_description"
Cohesion: 0.14
Nodes (7): Open Questions / Risks, _base_name_from_content_id(), build_retirement_description(), test_basic_description(), test_no_notes(), test_no_replacement(), test_wiki_markup_format()

### Community 83 - "test_nonprod.py"
Cohesion: 0.06
Nodes (15): get_workflow(), _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), _build_nonprod_provisions_sql(), TestGetNonprodBaseNames, TestListNonprodItems, TestNonprodIgnore (+7 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.07
Nodes (45): run_retirement_sweep(), test_lifecycle_old_closed_workflows_do_not_backfill(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close() (+37 more)

### Community 85 - "jira.py"
Cohesion: 0.11
Nodes (12): _close_issue(), close_issue_done(), close_issue_wont_do(), _fetch_oauth_token(), _get_access_token(), _issue_is_closed(), test_already_closed_issue_needs_no_transition(), test_closure_requires_a_terminal_result() (+4 more)

### Community 86 - "middleware/auth.py"
Cohesion: 0.12
Nodes (15): _check_api_key_role_ceiling(), get_current_user(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), require_performance_view(), _validate_api_key_cached() (+7 more)

### Community 87 - "AnalysisSignature"
Cohesion: 0.10
Nodes (23): Content Owner Model Implementation Plan, Global Constraints, Rollout, Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model (+15 more)

### Community 88 - "ArchitectureDriver"
Cohesion: 0.19
Nodes (8): What Moves Into Drivers, ArchitectureDriver, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 89 - "build_retirement_description"
Cohesion: 0.12
Nodes (15): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+7 more)

### Community 90 - "block"
Cohesion: 0.18
Nodes (11): cmd, migrate_pod, ansible.builtin.command, ansible.builtin.set_fact, changed_when, delay, name, register (+3 more)

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (19): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Babylon CRD Catalog Pipeline, LLM Provider Routing (LiteMaaS / Vertex AI), Nightly Maintenance Pipeline, Performance Scoring System (+11 more)

### Community 92 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.10
Nodes (37): Task 4: Unify scan persistence and remove cross-item fan-out, InvalidShowroomRef, reuse_key_from_signature(), showroom_reuse_key(), scan_babylon_item(), run_stale_check(), run_analysis(), db() (+29 more)

### Community 94 - "asyncio"
Cohesion: 0.08
Nodes (29): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+21 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "normalize_row"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 98 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (4): Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "is_content_excluded"
Cohesion: 0.09
Nodes (19): 1. Storage, 2. Source resolution, 4. Candidate selection and stale check, 5. API, 6. Frontend, 7. Coverage math, Anti-goals, Approaches considered (+11 more)

### Community 101 - "Candidate"
Cohesion: 0.17
Nodes (9): _run_catalog_second_pass(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published(), test_query_state_defaults(), test_three_layer_workload_propagation() (+1 more)

### Community 102 - "test_vocabulary_admin.py"
Cohesion: 0.32
Nodes (3): clear_vocabulary_cache(), client(), TestRoleGating

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "workload_scanner.py"
Cohesion: 0.22
Nodes (4): regenerate_embeddings(), scan_all_collections(), scan_collection(), scan_configs()

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.09
Nodes (15): test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at(), FakeSettings (+7 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (10): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+2 more)

### Community 108 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.09
Nodes (22): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers, Approach Decision (+14 more)

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "post_tasks"
Cohesion: 0.18
Nodes (11): msg, kind, kubeconfig, label_selectors, namespace, post_tasks, ansible.builtin.debug, kubernetes.core.k8s_info (+3 more)

### Community 112 - "Task 2: Union labels per base name"
Cohesion: 0.21
Nodes (6): Task 2: Union labels per base name, test_labels_empty_input(), test_labels_include_retired_stage(), test_labels_union_across_stages(), test_labels_union_tdp2_only(), test_labels_unlabeled_item_has_empty_lists()

### Community 113 - "Platform and Technical Decision Point filters — design"
Cohesion: 0.17
Nodes (10): Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+2 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.05
Nodes (29): migrate(), db(), seed_infrastructure(), db(), db(), db(), db(), db() (+21 more)

### Community 120 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 121 - "action_verbs"
Cohesion: 0.20
Nodes (10): action_verbs, hands_on, interactive, read_through, rejected, valid, rejected, valid (+2 more)

### Community 123 - "ContentTypeDriver"
Cohesion: 0.12
Nodes (7): Create, ContentTypeDriver, get_driver(), _init_drivers(), _register(), test_get_driver_architecture(), test_get_driver_lab()

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.22
Nodes (10): _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable() (+2 more)

### Community 126 - "test_llm_routing.py"
Cohesion: 0.19
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 127 - ".create_job"
Cohesion: 0.24
Nodes (6): _do(), test_job_failure(), test_job_lifecycle(), test_list_jobs(), test_list_jobs_shows_running_before_newer_queued(), test_queued_job_keeps_progress_json()

### Community 128 - "content_owner"
Cohesion: 0.09
Nodes (26): Review Focus, Task 1: `content_owner` helper, Task 2: Database read and write methods for stubs, Task 3: Scan skips pure stubs, Task 5: Mirror card fields when an owner scan saves, Task 7: `get_display_analysis` and the three runtime read sites, Task 8: Browse detail shows the owner's analysis and names the owner, Description-Based Analysis Implementation Plan (+18 more)

### Community 129 - ".list_content_entities_filtered"
Cohesion: 0.20
Nodes (11): _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default(), test_filtered_catalog_pagination(), test_filtered_catalog_search() (+3 more)

### Community 130 - "Python Dependency Manifest (requirements.lock)"
Cohesion: 0.22
Nodes (9): Anthropic SDK Dependency (v0.120.0), arq Dependency (v0.28.0), Python Dependency Manifest (requirements.lock), FastAPI Dependency (v0.140.7), OpenAI SDK Dependency (v2.49.0), psycopg Dependency (v3.3.4), Pydantic Dependency (v2.13.4), Redis Client Dependency (v5.3.1) (+1 more)

### Community 131 - "reporting_db_show"
Cohesion: 0.18
Nodes (3): reporting_db_show(), reporting_db_status(), reporting_db_sync()

### Community 132 - "_FakeResponse"
Cohesion: 0.22
Nodes (5): _FakeResponse, fake_urlopen(), fake_urlopen(), fake_urlopen(), _token_payload()

### Community 134 - "router.py"
Cohesion: 0.09
Nodes (39): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+31 more)

### Community 135 - "File map and verification conventions"
Cohesion: 0.25
Nodes (7): Execution handoff, File map and verification conventions, Global Constraints, Review Focus, Self-review, Showroom Analysis Isolation Implementation Plan, Task 5: Keep recommendation identities within authorized relationships

### Community 136 - "database.py"
Cohesion: 0.02
Nodes (25): lifespan(), derive_status(), retirement_label(), client(), test_sync_osspa_endpoint_enqueues_a_job(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey (+17 more)

### Community 139 - "showroom_source.py"
Cohesion: 0.13
Nodes (11): _apply_component_inheritance(), _collect_bases(), component_item_to_ci_name(), _content_fields(), extract_showroom_url(), _resolve_template_var(), _source_node(), ContentDeclaration (+3 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.16
Nodes (21): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+13 more)

### Community 173 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 174 - "test_showroom_reuse.py"
Cohesion: 0.23
Nodes (15): Task 3: Fetch the exact source and reject non-content inputs, prime(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_embedding_only_changes_repair_only_affected_artifacts(), test_every_changed_signature_input_prevents_donor_reuse(), test_force_bypasses_unchanged_fast_path_and_donors(), test_identical_revision_and_context_skips_clone_llm_and_embeddings() (+7 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "MemoryArtifacts"
Cohesion: 0.17
Nodes (3): MemoryArtifacts, scan(), run()

### Community 180 - "hashlib"
Cohesion: 0.22
Nodes (6): jira_auth_configured(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), reuse_lock_id()

### Community 182 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 183 - "_sync_nonprod_usage"
Cohesion: 0.33
Nodes (3): _nonprod_metrics(), _sync_nonprod_usage(), TestSyncNonprodUsage

### Community 184 - "rationale.py"
Cohesion: 0.22
Nodes (9): Content-Type Drivers Implementation Plan, Execution Notes, Global Constraints, Review Focus, Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, _primary_asset_type(), _call_rationale_single() (+1 more)

### Community 185 - "test_catalog_labels.py"
Cohesion: 0.12
Nodes (11): Task 1: Read and store Platform/TDP labels, _seed_label_count_items(), test_extract_keys_are_case_sensitive(), test_extract_missing_labels_are_none(), test_extract_reads_platform_and_tdps(), test_filter_tdp_none(), test_label_counts_follow_other_filters(), test_label_counts_follow_search() (+3 more)

### Community 186 - "mcp_query"
Cohesion: 0.14
Nodes (10): Field Source Content Report — Implementation Plan, Global Constraints, Task 1: Database Schema and Methods, Task 3: API Endpoint, Task 4: Frontend Page, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, mcp_query() (+2 more)

### Community 188 - "Path"
Cohesion: 0.33
Nodes (3): discover_roles(), _follow_task_includes(), read_role_code()

### Community 190 - "Field Source Content"
Cohesion: 0.50
Nodes (4): API, Data Source, Field Source Content, Frontend

### Community 191 - ".get_unknown_terms"
Cohesion: 0.20
Nodes (3): TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm

### Community 193 - "git_repo"
Cohesion: 0.50
Nodes (3): Data Import, git_repo(), git()

### Community 194 - "workflow_lock_id"
Cohesion: 0.18
Nodes (9): workflow_lock_id(), test_advisory_lock_is_not_reentrant_across_sessions(), _approved_unstarted(), test_start_retirement_holds_lock_while_creating_ticket(), fake_create(), test_start_retirement_respects_workflow_lock(), _prepare(), test_route_rejects_when_workflow_lock_held() (+1 more)

### Community 196 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 197 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 199 - ".upsert_infrastructure"
Cohesion: 0.29
Nodes (4): test_get_infrastructure_with_item_counts(), test_list_infrastructure_with_type_filter(), test_upsert_infrastructure_insert(), test_upsert_infrastructure_update()

### Community 201 - "content_modes"
Cohesion: 0.40
Nodes (5): content_modes, architecture, demo, lab, sandbox

### Community 202 - "build_infrastructure_embedding_text"
Cohesion: 0.60
Nodes (3): build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

### Community 206 - "clone_showroom"
Cohesion: 0.22
Nodes (5): clone_showroom(), _is_github_throttle(), ls_remote_sha(), _resolve_ref_from_lookup(), _run_git_with_retry()

### Community 208 - "test_drivers.py"
Cohesion: 0.15
Nodes (11): get_drivers_for_types(), format_triage_candidates(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_get_driver_unknown_raises(), test_get_drivers_for_types_groups() (+3 more)

### Community 209 - "kubernetes.core.k8s_exec"
Cohesion: 0.50
Nodes (4): kubernetes.core.k8s_exec, kubeconfig, namespace, pod

### Community 210 - "collections"
Cohesion: 0.50
Nodes (3): collections, name, version

### Community 211 - "solutions"
Cohesion: 0.50
Nodes (4): solutions, aliases, is_tdp, name

### Community 212 - "_jira_event_messages"
Cohesion: 0.10
Nodes (9): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_requires_admin(), test_edit_update_skips_cancelled_workflows(), test_edit_without_change_records_no_event() (+1 more)

### Community 213 - "ansible.builtin.assert"
Cohesion: 0.67
Nodes (3): fail_msg, that, ansible.builtin.assert

### Community 214 - "CatalogReader"
Cohesion: 0.14
Nodes (10): CatalogReader, collect(), load(), extract_base_ci_refs(), extract_catalog_item(), extract_infrastructure_metadata(), is_agnosticd_v2(), parse_workload_fqcn() (+2 more)

## Knowledge Gaps
- **92 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+87 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1409 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **65 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `content_owner`, `.list_content_entities_filtered`, `reporting_db_show`, `router.py`, `db/__init__.py`, `database.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `ops.py`, `generate_embedding`, `.upsert_babylon_catalog_item`, `Settings`, `seed`, `settings.py`, `_generate_key`, `Review Focus`, `handlers.py`, `extract_base_name`, `run_osspa_sync`, `test_catalog_labels.py`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `.get_unknown_terms`, `search`, `workflow_lock_id`, `.get_babylon_item_by_ci_name`, `._catalog_label_counts`, `.upsert_infrastructure`, `cli.py`, `pipeline.py`, `test_nonprod.py`, `_jira_event_messages`, `test_retirement_pr_status.py`, `AnalysisSignature`, `test_showroom_scan.py`, `asyncio`, `is_content_excluded`, `workload_scanner.py`, `test_field_source_sync.py`, `Task 2: Union labels per base name`, `.close`, `.create_job`?**
  _High betweenness centrality (0.197) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `Database` (e.g. with `Settings` and `AnalysisSignature`) actually correct?**
  _`Database` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _92 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.12666666666666668 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `content_owner`, `Database`, `reporting_db_show`, `test_description_analysis.py`, `router.py`, `database.py`, `admin.py`, `routes/catalog.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `ops.py`, `generate_embedding`, `routes/auth.py`, `re`, `schemas.py`, `seed`, `settings.py`, `JobProgressRelay`, `advisor.py`, `handlers.py`, `analysis.py`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `test_workers.py`, `analyzer.py`, `cli.py`, `pipeline.py`, `test_test_content_exclusion.py`, `test_retirement_pr_status.py`, `middleware/auth.py`, `AdocRead`, `test_showroom_scan.py`, `asyncio`, `test_vocabulary_admin.py`, `.close`, `test_llm_routing.py`?**
  _High betweenness centrality (0.138) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.024752475247524754 - nodes in this community are weakly interconnected._