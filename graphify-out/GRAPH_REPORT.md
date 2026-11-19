# Graph Report - rcars-advisory  (2026-11-19)

## Corpus Check
- 314 files · ~547,395 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 4002 nodes · 9921 edges · 198 communities (140 shown, 58 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1090 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a89da278`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _FakeResponse
- Database
- registry.ts
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
- derive_status
- Generalized Content Model Design
- test_agv_access.py
- ops.py
- workload_scanner.py
- test_catalog_labels.py
- routes/auth.py
- test_db.py
- test_content_owner.py
- test_osspa_adoc.py
- react
- Settings
- LLMResult
- test_showroom_source.py
- schemas.py
- seed
- App.tsx
- settings.py
- test_drivers.py
- .is_admin
- JobProgressRelay
- _make_request
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- test_jira_service.py
- recommendations.py
- Any
- test_analyzer.py
- test_osspa_csv.py
- compute_sales_impact
- api.ts
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- analysis.py
- test_auth_security.py
- chat_sessions.py
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
- json
- test_osspa_db.py
- HandsOnDriver
- reporting_sync.py
- pytest
- test_sweep_github_only_cancellation_preserves_revert_until_jira_available
- api.ts
- ECA Production Redesign Spec
- sync_opl_vocabulary.py
- migrate_to_content_model.py
- analyzer.py
- Reporting MCP Data Sync
- test_status_visibility.py
- TestValidation
- .upsert_babylon_catalog_item
- command
- pipeline.py
- test_test_content_exclusion.py
- test_catalog_content_owner_routes.py
- test_nonprod.py
- test_retirement_pr_status.py
- jira.py
- middleware/auth.py
- _print
- ArchitectureDriver
- build_retirement_description
- build_analysis_prompt
- System Design Architecture Doc
- AdocRead
- test_showroom_scan.py
- database.py
- Showroom analysis isolation
- Scan Pipeline
- normalize_row
- Browse Page Redesign Plan
- API Authentication Design
- Description-Based Analysis for Items With No Showroom — Design
- Candidate
- TestVocabularyEndpoints
- rcars-login.sh
- TestGroupLookup
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- Advisor v2 — Content-Type Drivers
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- ContentAnalysisPage.tsx
- create_app
- devDependencies
- content_entities Table
- .close
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- _extrapolate_count
- StatusPage.tsx
- build_embedding_text
- ContentTypeDriver
- test_orphan_cleanup.py
- retirement_cleanup.py
- build_retirement_description
- option
- effective_analysis_source
- Decisions
- get
- status
- order_for_reuse
- _sync_nonprod_usage
- handlers.py
- TestStepOrder
- test_retirement_edit.py
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
- Sweeps and Status Reconciliation
- Match Event Prompt Template
- extract_base_name
- test_already_closed_issue_needs_no_transition
- test_showroom_reuse.py
- test_vocabulary.py
- Python Requirements Entry Point
- File map and verification conventions
- ensure_issue_event_comment
- TestTokenExchange
- Controlled Vocabulary Design
- _window_start
- _format_single_candidate
- extract_catalog_item
- mcp_query
- TestGetNonprodBaseNames
- Field Source Content
- TestRecordUnknownTerm
- _reset_token_cache
- publish_progress
- test_retirement_pr_status.py
- test_infrastructure.py
- Task 1: Database Schema and Methods
- Platform and Technical Decision Point filters — design
- build_infrastructure_embedding_text

## God Nodes (most connected - your core abstractions)
1. `Database` - 306 edges
2. `Settings` - 182 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `scan_babylon_item()` - 51 edges
6. `seed()` - 46 edges
7. `create_app()` - 41 edges
8. `run_retirement_sweep()` - 40 edges
9. `ResolvedShowroom` - 39 edges
10. `content_owner()` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Global Constraints` --references--> `parse_analysis_response()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/analyzer.py
- `Task 1: Candidate Model Refactor` --references--> `Candidate`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/models.py
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Anti-goals` --references--> `is_content_excluded()`  [INFERRED]
  docs/superpowers/specs/2026-11-17-description-analysis-design.md → src/api/rcars/services/showroom_source.py

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

## Communities (198 total, 58 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.10
Nodes (16): _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen() (+8 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (3): Database, _do(), test_advisory_lock_is_not_reentrant_across_sessions()

### Community 2 - "registry.ts"
Cohesion: 0.14
Nodes (21): InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps (+13 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.21
Nodes (17): OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis, Nightly Maintenance Pipeline, OSSPA GitLab Repositories (+9 more)

### Community 4 - "test_description_analysis.py"
Cohesion: 0.16
Nodes (36): Task 2: `Database.set_analysis_source()` setter, Task 7: API endpoint + detail fields, AnalysisSourceRequest, set_analysis_source(), analyze_description(), add_description_item(), add_item(), mock_analysis() (+28 more)

### Community 5 - "devDependencies"
Cohesion: 0.06
Nodes (30): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, @types/react (+22 more)

### Community 6 - "cli.py"
Cohesion: 0.13
Nodes (7): infra_group(), osspa_group(), overlap_candidates_cmd(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 7 - "db/__init__.py"
Cohesion: 0.12
Nodes (13): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), seed_items(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats() (+5 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.19
Nodes (17): add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, flag_item(), get_analysis(), infra_stats(), infrastructure_items() (+9 more)

### Community 9 - "admin.py"
Cohesion: 0.08
Nodes (36): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs(), query_history() (+28 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.08
Nodes (22): event_time(), test_comment_missing_credentials_does_not_call_http(), unexpected(), test_database_no_jira_and_deleted_workflow_do_not_queue(), test_database_open_event_is_atomic_and_deduplicated(), test_database_rollout_cutoff_and_repeat_closures(), test_database_workflow_and_event_write_roll_back_together(), test_delivery_concurrent_senders_cannot_overtake_stream() (+14 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): Task 7: Browse UI (provisional style), getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline() (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.06
Nodes (34): _call_litemaas(), assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment() (+26 more)

### Community 14 - "derive_status"
Cohesion: 0.09
Nodes (3): derive_status(), retirement_label(), TestDeriveStatus

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 17 - "ops.py"
Cohesion: 0.09
Nodes (22): Decisions (Nate, 2026-11-19), build_sandbox_summary(), WorkerContext, _progress_bridge(), run_babylon_pipeline(), run_catalog_refresh(), run_field_source_sync_job(), run_nightly_pipeline() (+14 more)

### Community 18 - "workload_scanner.py"
Cohesion: 0.08
Nodes (14): analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products(), read_config_code(), read_role_code(), scan_all_collections() (+6 more)

### Community 19 - "test_catalog_labels.py"
Cohesion: 0.08
Nodes (22): Review Focus, Task 2: Union labels per base name, Task 4: Browse server-side filters and facets, Task 5: Shared frontend helpers and checkbox filter group, Task 8: Run locally, check, and prepare the PR, _seed_label_count_items(), test_facets_platforms_and_tdps(), test_filter_groups_and() (+14 more)

### Community 20 - "routes/auth.py"
Cohesion: 0.14
Nodes (16): invalidate_api_key_cache(), _get_user_key(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+8 more)

### Community 21 - "test_db.py"
Cohesion: 0.08
Nodes (11): db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default(), test_filtered_catalog_pagination() (+3 more)

### Community 22 - "test_content_owner.py"
Cohesion: 0.12
Nodes (32): Task 4: Reconcile stub artifacts at every scan entry point, rescan_all(), start_scan(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts() (+24 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.08
Nodes (38): Task 8: Frontend Refactor, 5. Frontend Card Rendering, Display Config Structure, CATEGORY_LABELS, RecCardsBlock(), RecCardsBlockProps, ChatChip, ChatEnvelope (+30 more)

### Community 25 - "Settings"
Cohesion: 0.08
Nodes (27): list_role_assignments(), llm_provider_status(), workload_scan(), fetch_litemaas_models(), _parse_csv(), Settings, _get_embedding_client(), settings() (+19 more)

### Community 26 - "LLMResult"
Cohesion: 0.09
Nodes (24): _call_litemaas_inner(), call_llm(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), _help_answer(), process_turn() (+16 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.16
Nodes (31): Task 1: Resolve content sources with explicit ownership, Task 1: `content_owner` helper, component_item_to_ci_name(), extract_showroom_url(), _source_node(), ComponentLink, content_owner(), ContentDeclaration (+23 more)

### Community 28 - "schemas.py"
Cohesion: 0.08
Nodes (38): field_source_report(), health(), readiness(), AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload (+30 more)

### Community 29 - "seed"
Cohesion: 0.08
Nodes (42): Task 2: Persist source provenance and enforce scoped analysis reuse, Task 6: Add a narrowly scoped reset and verify the full rebuild contract, Task 6: Advisor shows the stub in place of its owner, ResolvedShowroom, snapshots(), test_dry_run_performs_no_writes(), test_execute_requires_scans_paused_confirmation(), test_full_reset_preserves_non_showroom_sandbox_card() (+34 more)

### Community 30 - "App.tsx"
Cohesion: 0.09
Nodes (38): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), API_DOCS_URL (+30 more)

### Community 31 - "settings.py"
Cohesion: 0.11
Nodes (13): _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url() (+5 more)

### Community 32 - "test_drivers.py"
Cohesion: 0.13
Nodes (17): get_driver(), get_drivers_for_types(), format_triage_candidates(), _make_hands_on_candidate(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data() (+9 more)

### Community 33 - ".is_admin"
Cohesion: 0.11
Nodes (17): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+9 more)

### Community 34 - "JobProgressRelay"
Cohesion: 0.13
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 35 - "_make_request"
Cohesion: 0.16
Nodes (7): get_current_user(), _make_request(), TestApiKeyAuth, TestApiKeyRoleCeiling, TestGetCurrentUser, TestProxySecretEnforcement, TestRequirePerformanceView

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.10
Nodes (21): Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy (+13 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.15
Nodes (4): load_vocabulary(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "_generate_key"
Cohesion: 0.10
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.20
Nodes (18): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+10 more)

### Community 42 - "recommendations.py"
Cohesion: 0.18
Nodes (5): get_recommendations(), RecommendationRequest, _run_medium(), RecommendationLowResponse, RecommendationMediumResponse

### Community 43 - "Any"
Cohesion: 0.07
Nodes (6): Task 5: Mirror card fields when an owner scan saves, Task 7: `get_display_analysis` and the three runtime read sites, Scan, _prefix_overlap(), _find_keyword_ties(), resolve_item()

### Community 44 - "test_analyzer.py"
Cohesion: 0.10
Nodes (25): check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content(), test_content_path_antora_start_path_resolves_pages_and_nav() (+17 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (19): asset_type_tokens(), fetch_palist_csv(), OsspaSyncError, parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status() (+11 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.10
Nodes (7): _build_windowed_metrics(), compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), TestBuildWindowedMetrics, TestComputePerformanceScore

### Community 47 - "api.ts"
Cohesion: 0.09
Nodes (55): Task 6: Wire filters into Performance, Non-Prod and Retirement, CollapsibleFilterGroup(), CollapsibleFilterGroupProps, LabelFilterGroup(), LabelFilterGroupProps, fmtTargetDate(), isInProgress(), isRecommended() (+47 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.09
Nodes (6): normalize_analysis(), _record_unknowns(), _snap_values(), TestReviewBadgeUntouched, TestIgnoredTermsSuppression, TestNormalizeAnalysis

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "_expand_query_terms"
Cohesion: 0.09
Nodes (7): _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 51 - "analysis.py"
Cohesion: 0.13
Nodes (28): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), check_stale(), edit_retirement(), EditRetirementRequest, ignore_item() (+20 more)

### Community 52 - "test_auth_security.py"
Cohesion: 0.08
Nodes (8): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders, TestUnauthenticatedAccess, _row()

### Community 53 - "chat_sessions.py"
Cohesion: 0.17
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 54 - "Vocabulary"
Cohesion: 0.16
Nodes (5): generate_vocabulary(), generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "Task 3: Return labels from the three analysis endpoints"
Cohesion: 0.13
Nodes (9): Task 3: Return labels from the three analysis endpoints, _extract_base_name_from_content_id(), performance_dashboard(), retirement_dashboard(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists() (+1 more)

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.26
Nodes (18): run_osspa_sync(), _csv(), fake_analyze(), settings(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything() (+10 more)

### Community 58 - "loader.py"
Cohesion: 0.15
Nodes (9): _entries_to_dicts(), _as_tuple(), _build_lookups(), _parse_entries(), _validate(), VocabEntry, Vocabulary, VocabularyError (+1 more)

### Community 59 - "Retirement System"
Cohesion: 0.11
Nodes (19): AgV Access Layer, Architecture, Authentication and Scope, Cancellation and Recovery, Catalog Soft-Delete, Code Organization, Configuration and Operations, Notice PR (+11 more)

### Community 60 - "parse_analysis_response"
Cohesion: 0.13
Nodes (8): _expand_vocab_aliases(), _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), _strip_html(), _validate_url()

### Community 61 - "analyze_architecture_item"
Cohesion: 0.16
Nodes (11): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms(), test_analyze_uses_the_dedicated_model_when_configured() (+3 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.14
Nodes (7): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "SyncPage.tsx"
Cohesion: 0.15
Nodes (14): react, LogWindow(), LogWindowProps, BlockErrorBoundary, Props, State, ActionState, AdminAction() (+6 more)

### Community 64 - "json"
Cohesion: 0.16
Nodes (11): get_db(), init_db(), migrate(), main(), cmd_logout(), _load_credentials(), main(), cmd_login() (+3 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.23
Nodes (9): _row(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override(), test_upsert_osspa_item_never_overwrites_llm_owned_fields(), test_upsert_osspa_item_unretires_on_reappearance() (+1 more)

### Community 66 - "HandsOnDriver"
Cohesion: 0.18
Nodes (8): Modify, Task 3: Hands-on Driver, What Moves Into Drivers, _extract_duration_target(), HandsOnDriver, test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_triage_guidance()

### Community 67 - "reporting_sync.py"
Cohesion: 0.17
Nodes (10): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs(), _percentile_rank() (+2 more)

### Community 68 - "pytest"
Cohesion: 0.09
Nodes (35): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+27 more)

### Community 69 - "test_sweep_github_only_cancellation_preserves_revert_until_jira_available"
Cohesion: 0.12
Nodes (9): test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), test_retired_items_cannot_be_cancelled(), close_jira(), state() (+1 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): Task 5: Routing and Sidebar, findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName() (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "sync_opl_vocabulary.py"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 73 - "migrate_to_content_model.py"
Cohesion: 0.14
Nodes (14): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+6 more)

### Community 74 - "analyzer.py"
Cohesion: 0.11
Nodes (25): Task 3: `analyze_description()` in the analyzer, Task 4: Candidate selection, 4. Candidate selection and stale check, analysis_context_hash(), analysis_from_row(), analyze_showroom(), compute_analysis_context_hash(), compute_analysis_input_hash() (+17 more)

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (6): Retirement Analysis Integration Plan, Retirement Workflow Actions Plan, Generalized Content Model Plan, Overlap Analysis Redesign Plan, Advisor Multi-Intent Chat Plan, Performance Page Plan

### Community 76 - "test_status_visibility.py"
Cohesion: 0.17
Nodes (11): _arch(), _seed_nonprod(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators(), test_nonprod_list_hides_item_with_finished_retirement_workflow() (+3 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 79 - "command"
Cohesion: 0.13
Nodes (9): flag(), infra_stats(), note(), override_url(), set_content_path(), tag(), untag(), workload_alias() (+1 more)

### Community 80 - "pipeline.py"
Cohesion: 0.10
Nodes (19): Task 6: Orchestrator + Pipeline Refactor, 2. Orchestrator and Pipeline, What Gets Deleted, _run_low(), registered_content_types(), QueryState, extract_urls(), run_category() (+11 more)

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.08
Nodes (28): Root cause, _authorized_promotion(), eligible(), _eligible_stub(), _owner_scope_ids(), _resolve_ci_references(), _strip_embedding_filler(), _verified_signature() (+20 more)

### Community 82 - "test_catalog_content_owner_routes.py"
Cohesion: 0.25
Nodes (14): Task 9: Curator edits on a stub write the owner's analysis row, _curation_target(), DurationRequest, get_catalog_item(), NoteRequest, _resolve_item(), set_duration(), set_note() (+6 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.09
Nodes (10): get_workflow(), _nonprod_retirement_metrics(), _retirement_metrics(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestNonprodWindows (+2 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.12
Nodes (20): observe_pr_events(), run_retirement_sweep(), _sweep_context(), test_required_failed_cancel_is_excluded_from_removal_and_retried_by_sweep(), test_required_success_retries_jira_after_retirement_without_pr(), test_sweep_does_not_retire_from_merged_notice_alone(), test_sweep_github_only_cancels_when_no_jira_work_remains(), test_sweep_github_only_completes_when_no_jira_work_remains() (+12 more)

### Community 85 - "jira.py"
Cohesion: 0.10
Nodes (14): _close_issue(), close_issue_done(), close_issue_wont_do(), _fetch_oauth_token(), _get_access_token(), get_issue_status(), _issue_is_closed(), jira_auth_configured() (+6 more)

### Community 86 - "middleware/auth.py"
Cohesion: 0.11
Nodes (13): _check_api_key_role_ceiling(), _get_cached_role_assignments(), _log_auth_decision(), _parse_sa_allowlist(), require_admin(), require_auth(), require_curator(), require_performance_view() (+5 more)

### Community 87 - "_print"
Cohesion: 0.14
Nodes (6): _print(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 88 - "ArchitectureDriver"
Cohesion: 0.21
Nodes (7): ArchitectureDriver, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 89 - "build_retirement_description"
Cohesion: 0.12
Nodes (15): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+7 more)

### Community 90 - "build_analysis_prompt"
Cohesion: 0.14
Nodes (6): Open items for the builder, build_analysis_prompt(), build_description_prompt(), _canonical_content(), truncate_content(), TestPromptInjection

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (18): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, architecture_analysis DB Table, RCARS Authentication Model, content_entities Universal Entity Registry Table, LLM Provider Routing (LiteMaaS / Vertex AI), Performance Scoring System (+10 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.09
Nodes (40): Task 4: Unify scan persistence and remove cross-item fan-out, InvalidShowroomRef, reuse_key_from_signature(), showroom_reuse_key(), reuse_lock_id(), scan_babylon_item(), analysis_generation(), run_stale_check() (+32 more)

### Community 94 - "database.py"
Cohesion: 0.05
Nodes (25): build_evidence_pack(), build_jira_event(), _deliver_pending_events(), event_timestamp(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage() (+17 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.20
Nodes (10): Content Overlap Detection, Cosine Similarity for Overlap, Score Bands, Phase 1 Vector Search, Scan Pipeline, Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify (+2 more)

### Community 97 - "normalize_row"
Cohesion: 0.20
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 98 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (4): Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "Description-Based Analysis for Items With No Showroom — Design"
Cohesion: 0.14
Nodes (13): 1. Storage, 2. Source resolution, 5. API, 6. Frontend, 7. Coverage math, Anti-goals, Approaches considered, Deployment (+5 more)

### Community 101 - "Candidate"
Cohesion: 0.10
Nodes (11): Candidate, _run_catalog_second_pass(), test_candidate_similarity_pct(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published() (+3 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "TestGroupLookup"
Cohesion: 0.14
Nodes (9): _fetch_group_members(), _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response(), TestGroupLookup (+1 more)

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.15
Nodes (11): Task 2: Reporting Sync Job, _build_field_source_sql(), run_field_source_sync(), FakeSettings, _mock_mcp_query(), test_field_source_sync_captures_user_email(), test_field_source_sync_ignores_agd_v2_items(), tracking_mock() (+3 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (12): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+4 more)

### Community 108 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.12
Nodes (16): 1. Content-Type Drivers, 4. SSE Streaming, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy (+8 more)

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 112 - "create_app"
Cohesion: 0.03
Nodes (28): create_app(), lifespan(), RequestLoggingMiddleware, client(), client(), test_sync_osspa_endpoint_enqueues_a_job(), client(), test_auth_me_unauthenticated() (+20 more)

### Community 113 - "devDependencies"
Cohesion: 0.15
Nodes (13): devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @types/react, @types/react-dom (+5 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.05
Nodes (26): db(), seed_infrastructure(), db(), db(), db(), db(), db(), db() (+18 more)

### Community 121 - "StatusPage.tsx"
Cohesion: 0.13
Nodes (11): react-dom, vitest, LlmProviderCard(), LlmProviderStatus, LlmUse, status, USE_LABELS, render() (+3 more)

### Community 123 - "ContentTypeDriver"
Cohesion: 0.11
Nodes (9): Create, Delete, File Map, Task 1: Candidate Model Refactor, Task 2: Driver Base Class + Registry, Task 4: Architecture Driver, ContentTypeDriver, _init_drivers() (+1 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.16
Nodes (14): cancel_workflow(), check_pr_statuses(), _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr(), complete_retirement() (+6 more)

### Community 126 - "build_retirement_description"
Cohesion: 0.18
Nodes (6): Open Questions / Risks, References, _base_name_from_content_id(), build_retirement_adoc_notice(), build_retirement_description(), test_no_notes()

### Community 127 - "option"
Cohesion: 0.18
Nodes (5): cli(), osspa_sync_cmd(), serve(), vocab_stage_rescan(), vocab_unknowns()

### Community 128 - "effective_analysis_source"
Cohesion: 0.11
Nodes (19): Task 3: Scan skips pure stubs, Description-Based Analysis Implementation Plan, Global Constraints, Review Focus, Task 1: Schema columns + `effective_analysis_source()`, Task 5: Scan pipeline branch, Task 6: Stale check exclusion, Task 8: Frontend edit drawer (+11 more)

### Community 130 - "get"
Cohesion: 0.22
Nodes (6): nonprod_dashboard(), overlap_assessment_detail(), overlap_report(), _sort_empty_last(), stream_job(), TestSortEmptyLast

### Community 131 - "status"
Cohesion: 0.29
Nodes (6): Data and Audit Trail, 3. Candidate Model, Candidate Dataclass, `content_entities` (shared table — all types), Source-specific tables, status()

### Community 132 - "order_for_reuse"
Cohesion: 0.08
Nodes (20): Content Owner Model Implementation Plan, Global Constraints, Review Focus, Rollout, Task 2: Database read and write methods for stubs, Task 8: Browse detail shows the owner's analysis and names the owner, Advisor, Browse (+12 more)

### Community 133 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 134 - "handlers.py"
Cohesion: 0.15
Nodes (24): get_item_workloads(), get_performance_scores(), generate_embedding(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+16 more)

### Community 136 - "test_retirement_edit.py"
Cohesion: 0.06
Nodes (17): client(), _jira_event_messages(), non_admin_client(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_rejected_for_retired_item() (+9 more)

### Community 139 - "showroom_source.py"
Cohesion: 0.07
Nodes (18): Global Constraints, Non-goals, refresh(), _apply_component_inheritance(), CatalogReader, collect(), load(), _collect_bases() (+10 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.20
Nodes (16): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+8 more)

### Community 169 - "Sweeps and Status Reconciliation"
Cohesion: 0.40
Nodes (5): Automatic Removal Eligibility, Checking Merges, Execution Paths, Jira Lifecycle Comments, Sweeps and Status Reconciliation

### Community 173 - "test_already_closed_issue_needs_no_transition"
Cohesion: 0.40
Nodes (3): test_already_closed_issue_needs_no_transition(), test_required_closure_selects_resolution_and_verifies_result(), request()

### Community 174 - "test_showroom_reuse.py"
Cohesion: 0.11
Nodes (18): Task 3: Fetch the exact source and reject non-content inputs, MemoryArtifacts, prime(), scan(), run(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_embedding_only_changes_repair_only_affected_artifacts() (+10 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.11
Nodes (7): squash_key(), dedup_topics(), _noise_variants(), _rungs_1_2(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "File map and verification conventions"
Cohesion: 0.25
Nodes (7): Execution handoff, File map and verification conventions, Global Constraints, Review Focus, Self-review, Showroom Analysis Isolation Implementation Plan, Task 5: Keep recommendation identities within authorized relationships

### Community 180 - "ensure_issue_event_comment"
Cohesion: 0.13
Nodes (10): ensure_issue_event_comment(), comments(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response(), test_comment_malformed_page_does_not_prove_absence() (+2 more)

### Community 182 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 184 - "_format_single_candidate"
Cohesion: 0.22
Nodes (9): Content-Type Drivers Implementation Plan, Execution Notes, Global Constraints, Review Focus, Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, _primary_asset_type(), _call_rationale_single() (+1 more)

### Community 185 - "extract_catalog_item"
Cohesion: 0.22
Nodes (5): Task 1: Read and store Platform/TDP labels, test_extract_keys_are_case_sensitive(), test_extract_missing_labels_are_none(), test_extract_reads_platform_and_tdps(), test_schema_adds_label_columns()

### Community 186 - "mcp_query"
Cohesion: 0.14
Nodes (9): Field Source Content Report — Implementation Plan, Global Constraints, Task 3: API Endpoint, Task 4: Frontend Page, Task 6: End-to-End Verification, _mcp_call(), mcp_query(), TestMcpQueryOrdering (+1 more)

### Community 190 - "Field Source Content"
Cohesion: 0.25
Nodes (7): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git()

### Community 193 - "publish_progress"
Cohesion: 0.19
Nodes (7): publish_progress(), run_chat_turn(), on_progress(), _publish(), run_retirement_sweep_job(), run_recommendation(), on_progress()

### Community 195 - "test_retirement_pr_status.py"
Cohesion: 0.10
Nodes (14): _approved_unstarted(), test_cancel_audit_reports_jira_outcome(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancellation_does_not_mark_concurrently_retired_item(), test_manual_pr_creation_respects_cleanup_lock(), test_refresh_does_not_retire_unmerged_or_unknown_pr(), test_refresh_merged_notice_does_not_complete_open_removal(), test_required_cancel_retains_workflow_on_jira_failure() (+6 more)

### Community 202 - "Platform and Technical Decision Point filters — design"
Cohesion: 0.25
Nodes (7): Anti-goals, Constraints, Goals, Left to the builder, Platform and Technical Decision Point filters — design, Rollout, Why

### Community 205 - "build_infrastructure_embedding_text"
Cohesion: 0.28
Nodes (5): build_infrastructure_embedding_text(), build_module_embedding_text(), analysis_artifacts_complete(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

## Knowledge Gaps
- **105 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1344 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **58 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `effective_analysis_source`, `Decisions`, `order_for_reuse`, `handlers.py`, `db/__init__.py`, `test_retirement_edit.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `workload_scanner.py`, `test_catalog_labels.py`, `test_db.py`, `test_content_owner.py`, `Settings`, `LLMResult`, `seed`, `settings.py`, `_generate_key`, `Any`, `extract_base_name`, `test_auth_security.py`, `run_osspa_sync`, `TestGetNonprodBaseNames`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `json`, `publish_progress`, `test_osspa_db.py`, `test_retirement_pr_status.py`, `pytest`, `test_infrastructure.py`, `Task 1: Database Schema and Methods`, `analyzer.py`, `test_status_visibility.py`, `.upsert_babylon_catalog_item`, `pipeline.py`, `test_test_content_exclusion.py`, `test_nonprod.py`, `_print`, `test_showroom_scan.py`, `database.py`, `Description-Based Analysis for Items With No Showroom — Design`, `create_app`, `.close`, `option`?**
  _High betweenness centrality (0.180) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `Database` (e.g. with `Settings` and `AnalysisSignature`) actually correct?**
  _`Database` has 53 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _105 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.10344827586206896 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `Database`, `order_for_reuse`, `test_description_analysis.py`, `cli.py`, `handlers.py`, `routes/catalog.py`, `admin.py`, `test_retirement_edit.py`, `showroom_source.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `ops.py`, `routes/auth.py`, `LLMResult`, `seed`, `settings.py`, `.is_admin`, `JobProgressRelay`, `_make_request`, `recommendations.py`, `analysis.py`, `test_auth_security.py`, `Task 3: Return labels from the three analysis endpoints`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `json`, `test_retirement_pr_status.py`, `pytest`, `analyzer.py`, `pipeline.py`, `test_test_content_exclusion.py`, `test_catalog_content_owner_routes.py`, `test_retirement_pr_status.py`, `middleware/auth.py`, `_print`, `test_showroom_scan.py`, `database.py`, `create_app`, `option`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Are the 72 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 72 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.02132114981915096 - nodes in this community are weakly interconnected._