# Graph Report - rcars-advisory  (2026-11-11)

## Corpus Check
- 311 files · ~540,443 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 3904 nodes · 9568 edges · 203 communities (142 shown, 61 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 983 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `91217eaa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _FakeResponse
- Database
- registry.ts
- Portfolio Architecture Ingest Design Spec
- handlers.py
- devDependencies
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
- Task 4: Browse server-side filters and facets
- routes/auth.py
- test_db.py
- test_content_owner.py
- test_osspa_adoc.py
- react
- Settings
- LLMResult
- _print
- schemas.py
- seed
- App.tsx
- settings.py
- test_drivers.py
- advisor.py
- JobProgressRelay
- test_auth_middleware.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- test_jira_service.py
- build_retirement_description
- Any
- test_analyzer.py
- test_osspa_csv.py
- compute_sales_impact
- api.ts
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- analysis.py
- TestSpoofedProxyHeaders
- chat_sessions.py
- generate_vocabulary_yaml
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
- router.py
- test_sweep_github_only_cancellation_preserves_revert_until_jira_available
- api.ts
- ECA Production Redesign Spec
- sync_opl_vocabulary.py
- migrate_to_content_model.py
- cli.py
- Reporting MCP Data Sync
- test_status_visibility.py
- TestValidation
- router.py
- command
- pipeline.py
- request
- run_category
- test_nonprod.py
- test_retirement_pr_status.py
- jira.py
- ContentAnalysisPage.tsx
- ArchitectureDriver
- test_llm_routing.py
- build_retirement_description
- _build_windowed_metrics
- System Design Architecture Doc
- AdocRead
- test_showroom_scan.py
- os
- Showroom analysis isolation
- Scan Pipeline
- normalize_row
- Browse Page Redesign Plan
- API Authentication Design
- option
- Candidate
- TestVocabularyEndpoints
- rcars-login.sh
- ._set_showroom_override
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- Advisor v2 — Content-Type Drivers
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- Controlled Vocabulary Design
- config.py
- test_chat_handlers.py
- content_entities Table
- .close
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- test_reporting.py
- StatusPage.tsx
- build_embedding_text
- Candidate
- test_orphan_cleanup.py
- retirement_cleanup.py
- Review Focus
- test_refresh_merged_notice_does_not_complete_open_removal
- scan_configs
- Decisions
- test_api_infrastructure.py
- orchestrator.py
- database.py
- _sync_nonprod_usage
- handlers.py
- test_database_explicit_test_schema_reset_includes_delivery_queue
- test_retirement_edit.py
- docker-entrypoint.sh
- Webhook Configuration Task
- CatalogReader
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
- _base_name_to_content_id
- Match Event Prompt Template
- extract_base_name
- test_workers.py
- test_showroom_reuse.py
- test_vocabulary.py
- Python Requirements Entry Point
- File map and verification conventions
- hashlib
- retirement_dashboard
- order_for_reuse
- .test_ignored_term_creates_no_row
- Content-Type Drivers Implementation Plan
- extract_catalog_item
- mcp_query
- status
- TestGetNonprodBaseNames
- start_retirement
- Field Source Content
- test_vocabulary_db.py
- _reset_token_cache
- TestTokenExchange
- Task 2: Union labels per base name
- test_start_retirement_holds_lock_while_creating_ticket
- test_catalog_labels.py
- test_sweep_jira_only_preserves_cancellation_with_github_work
- test_infrastructure.py
- Task 1: Database Schema and Methods
- Platform and Technical Decision Point filters — design
- TestPromptInjection
- build_infrastructure_embedding_text

## God Nodes (most connected - your core abstractions)
1. `Database` - 305 edges
2. `Settings` - 179 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `seed()` - 46 edges
6. `scan_babylon_item()` - 44 edges
7. `run_retirement_sweep()` - 40 edges
8. `create_app()` - 39 edges
9. `ResolvedShowroom` - 37 edges
10. `react` - 35 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Global Constraints` --references--> `parse_analysis_response()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/analyzer.py
- `Create` --references--> `ContentTypeDriver`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/drivers/base.py
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Execution Notes` --references--> `_format_single_candidate()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/rationale.py

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

## Communities (203 total, 61 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.11
Nodes (16): _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen() (+8 more)

### Community 2 - "registry.ts"
Cohesion: 0.13
Nodes (22): InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps (+14 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.21
Nodes (17): OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis, Nightly Maintenance Pipeline, OSSPA GitLab Repositories (+9 more)

### Community 4 - "handlers.py"
Cohesion: 0.13
Nodes (18): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+10 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (43): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, @types/react (+35 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.11
Nodes (14): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), db(), seed_items(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item() (+6 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.11
Nodes (31): Task 9: Curator edits on a stub write the owner's analysis row, add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+23 more)

### Community 9 - "admin.py"
Cohesion: 0.13
Nodes (26): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+18 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.09
Nodes (21): run_retirement_sweep(), event_time(), test_comment_missing_credentials_does_not_call_http(), unexpected(), test_database_no_jira_and_deleted_workflow_do_not_queue(), test_database_open_event_is_atomic_and_deduplicated(), test_database_rollout_cutoff_and_repeat_closures(), test_database_workflow_and_event_write_roll_back_together() (+13 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.11
Nodes (34): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+26 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (25): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+17 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (3): derive_status(), TestDeriveStatus, TestStepOrder

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 17 - "ops.py"
Cohesion: 0.10
Nodes (19): build_sandbox_summary(), publish_progress(), WorkerContext, run_chat_turn(), on_progress(), _progress_bridge(), _publish(), run_babylon_pipeline() (+11 more)

### Community 18 - "workload_scanner.py"
Cohesion: 0.09
Nodes (12): generate_embedding(), _get_embedding_client(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), read_config_code(), read_role_code() (+4 more)

### Community 19 - "Task 4: Browse server-side filters and facets"
Cohesion: 0.18
Nodes (6): Task 4: Browse server-side filters and facets, test_facets_platforms_and_tdps(), test_filter_groups_and(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_none()

### Community 20 - "routes/auth.py"
Cohesion: 0.18
Nodes (16): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+8 more)

### Community 21 - "test_db.py"
Cohesion: 0.08
Nodes (12): db(), db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default() (+4 more)

### Community 22 - "test_content_owner.py"
Cohesion: 0.15
Nodes (29): reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner(), test_browse_difficulty_filter_finds_a_stub_by_its_mirrored_card(), test_browse_shows_the_owner_review_flags_on_a_stub() (+21 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.07
Nodes (41): Task 8: Frontend Refactor, 5. Frontend Card Rendering, Display Config Structure, BlockErrorBoundary, Props, State, RecCardsBlock(), resolveBlockRenderer() (+33 more)

### Community 25 - "Settings"
Cohesion: 0.07
Nodes (27): workload_scan(), fetch_litemaas_models(), _parse_csv(), Settings, settings(), _FakeModels, _litemaas_settings(), _patch_litemaas_client() (+19 more)

### Community 26 - "LLMResult"
Cohesion: 0.16
Nodes (13): _call_litemaas_inner(), LLMResult, _extract_json(), route(), llm(), _fake(), llm_call(), test_call_error_falls_back() (+5 more)

### Community 27 - "_print"
Cohesion: 0.11
Nodes (8): _print(), refresh(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep(), vocab_unknowns()

### Community 28 - "schemas.py"
Cohesion: 0.06
Nodes (59): field_source_report(), health(), readiness(), AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload (+51 more)

### Community 29 - "seed"
Cohesion: 0.08
Nodes (46): File map and verification conventions, Task 2: Persist source provenance and enforce scoped analysis reuse, Task 5: Keep recommendation identities within authorized relationships, Task 6: Add a narrowly scoped reset and verify the full rebuild contract, Task 6: Advisor shows the stub in place of its owner, ResolvedShowroom, main(), db() (+38 more)

### Community 30 - "App.tsx"
Cohesion: 0.08
Nodes (37): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), API_DOCS_URL (+29 more)

### Community 31 - "settings.py"
Cohesion: 0.12
Nodes (13): _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url() (+5 more)

### Community 32 - "test_drivers.py"
Cohesion: 0.10
Nodes (14): ContentTypeDriver, get_driver(), get_drivers_for_types(), _init_drivers(), _register(), format_triage_candidates(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data() (+6 more)

### Community 33 - "advisor.py"
Cohesion: 0.08
Nodes (21): _check_api_key_role_ceiling(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), _validate_api_key_cached(), _get_user_key(), ChatRequest (+13 more)

### Community 34 - "JobProgressRelay"
Cohesion: 0.13
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 35 - "test_auth_middleware.py"
Cohesion: 0.05
Nodes (23): _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), _parse_sa_allowlist(), require_performance_view(), _user_has_db_role(), _user_in_groups(), _validate_sa_token() (+15 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.10
Nodes (21): Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy (+13 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.14
Nodes (5): load_vocabulary(), snap_term(), _normalize_products(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "_generate_key"
Cohesion: 0.15
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.25
Nodes (15): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_creates_ticket_and_returns_key() (+7 more)

### Community 42 - "build_retirement_description"
Cohesion: 0.14
Nodes (7): Open Questions / Risks, _base_name_from_content_id(), build_retirement_description(), test_basic_description(), test_no_notes(), test_no_replacement(), test_wiki_markup_format()

### Community 43 - "Any"
Cohesion: 0.06
Nodes (12): Advisor, Browse, Curator edits, Model, Overlap, Pure stub, Scan, _resolve_ci_references() (+4 more)

### Community 44 - "test_analyzer.py"
Cohesion: 0.06
Nodes (44): analysis_context_hash(), analysis_from_row(), analyze_showroom(), build_module_embedding_text(), _canonical_content(), check_showroom_stale(), classify_scan_error(), clone_showroom() (+36 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (19): asset_type_tokens(), fetch_palist_csv(), OsspaSyncError, parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status() (+11 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.12
Nodes (6): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), _recompute_windowed_scores(), TestComputePerformanceScore

### Community 47 - "api.ts"
Cohesion: 0.08
Nodes (57): Task 6: Wire filters into Performance, Non-Prod and Retirement, CollapsibleFilterGroup(), CollapsibleFilterGroupProps, render(), LabelFilterGroup(), LabelFilterGroupProps, fmtTargetDate(), isInProgress() (+49 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.15
Nodes (5): _noise_variants(), normalize_analysis(), _record_unknowns(), _snap_values(), TestNormalizeAnalysis

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "_expand_query_terms"
Cohesion: 0.09
Nodes (7): _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 51 - "analysis.py"
Cohesion: 0.20
Nodes (18): analyze_single(), check_stale(), get_workflow(), nonprod_dashboard(), nonprod_unignore(), open_agv_notice_pr(), _open_agv_notice_pr_locked(), open_agv_retire_pr() (+10 more)

### Community 53 - "chat_sessions.py"
Cohesion: 0.18
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 55 - "Task 3: Return labels from the three analysis endpoints"
Cohesion: 0.22
Nodes (5): Task 3: Return labels from the three analysis endpoints, test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists()

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.25
Nodes (19): run_osspa_sync(), _csv(), db(), fake_analyze(), settings(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring() (+11 more)

### Community 58 - "loader.py"
Cohesion: 0.10
Nodes (13): _entries_to_dicts(), _header_comment(), _as_tuple(), _build_lookups(), _parse_entries(), _resolve_path(), _validate(), squash_key() (+5 more)

### Community 59 - "Retirement System"
Cohesion: 0.08
Nodes (24): AgV Access Layer, Architecture, Authentication and Scope, Automatic Removal Eligibility, Cancellation and Recovery, Catalog Soft-Delete, Checking Merges, Code Organization (+16 more)

### Community 60 - "parse_analysis_response"
Cohesion: 0.15
Nodes (7): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), _strip_html(), _validate_url()

### Community 61 - "analyze_architecture_item"
Cohesion: 0.16
Nodes (11): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms(), test_analyze_uses_the_dedicated_model_when_configured() (+3 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.14
Nodes (7): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "SyncPage.tsx"
Cohesion: 0.31
Nodes (11): react, LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance() (+3 more)

### Community 64 - "json"
Cohesion: 0.17
Nodes (8): migrate(), cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 65 - "test_osspa_db.py"
Cohesion: 0.18
Nodes (10): _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override(), test_upsert_osspa_item_never_overwrites_llm_owned_fields() (+2 more)

### Community 66 - "HandsOnDriver"
Cohesion: 0.17
Nodes (10): Task 3: Hands-on Driver, What Moves Into Drivers, _extract_duration_target(), HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming() (+2 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.15
Nodes (10): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _mcp_call(), _merge_published_base_pairs() (+2 more)

### Community 68 - "router.py"
Cohesion: 0.35
Nodes (14): RouterOutput, Scope, resolve_and_verify(), _result_turns(), _turn_chips(), test_scope_shapes(), test_lb_ref_resolves(), test_low_confidence_clarifies() (+6 more)

### Community 69 - "test_sweep_github_only_cancellation_preserves_revert_until_jira_available"
Cohesion: 0.10
Nodes (10): test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), test_required_success_retries_jira_after_retirement_without_pr(), test_retired_items_cannot_be_cancelled(), close_jira() (+2 more)

### Community 70 - "api.ts"
Cohesion: 0.08
Nodes (26): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+18 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "sync_opl_vocabulary.py"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 73 - "migrate_to_content_model.py"
Cohesion: 0.14
Nodes (14): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+6 more)

### Community 74 - "cli.py"
Cohesion: 0.14
Nodes (7): cli(), infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (6): Retirement Analysis Integration Plan, Retirement Workflow Actions Plan, Generalized Content Model Plan, Overlap Analysis Redesign Plan, Advisor Multi-Intent Chat Plan, Performance Page Plan

### Community 76 - "test_status_visibility.py"
Cohesion: 0.17
Nodes (11): _arch(), _seed_nonprod(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators(), test_nonprod_list_hides_item_with_finished_retirement_workflow() (+3 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "router.py"
Cohesion: 0.16
Nodes (7): _prefix_overlap(), _expand_vocab_aliases(), _find_keyword_ties(), _parse_catalog_url(), pattern_check(), resolve_item(), test_pattern_check_url_and_lb()

### Community 79 - "command"
Cohesion: 0.16
Nodes (10): flag(), get_db(), infra_stats(), note(), override_url(), set_content_path(), tag(), untag() (+2 more)

### Community 80 - "pipeline.py"
Cohesion: 0.12
Nodes (13): Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, call_llm(), _primary_asset_type(), QueryState, _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis() (+5 more)

### Community 81 - "request"
Cohesion: 0.14
Nodes (9): client(), comments(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_malformed_page_does_not_prove_absence(), test_comment_unknown_post_outcome_recovers_remote_event(), test_delivery_survives_workflow_deletion_and_runs_off_loop() (+1 more)

### Community 82 - "run_category"
Cohesion: 0.13
Nodes (17): Modify, Task 6: Orchestrator + Pipeline Refactor, 1. Content-Type Drivers, 2. Orchestrator and Pipeline, 4. SSE Streaming, 6. Unified Serialization, Adding a New Content Type, Design (+9 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.08
Nodes (11): _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestNonprodWindows (+3 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.09
Nodes (25): _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancellation_does_not_mark_concurrently_retired_item(), test_manual_pr_creation_respects_cleanup_lock(), test_refresh_does_not_retire_unmerged_or_unknown_pr(), test_required_cancel_retains_workflow_on_jira_failure(), test_required_failed_cancel_is_excluded_from_removal_and_retried_by_sweep() (+17 more)

### Community 85 - "jira.py"
Cohesion: 0.09
Nodes (15): _close_issue(), close_issue_done(), close_issue_wont_do(), _fetch_oauth_token(), _get_access_token(), _issue_is_closed(), _jira_request(), _move_to_in_progress() (+7 more)

### Community 86 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 87 - "ArchitectureDriver"
Cohesion: 0.21
Nodes (7): ArchitectureDriver, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 88 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.11
Nodes (17): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+9 more)

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (18): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, architecture_analysis DB Table, RCARS Authentication Model, content_entities Universal Entity Registry Table, LLM Provider Routing (LiteMaaS / Vertex AI), Performance Scoring System (+10 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.10
Nodes (37): Task 4: Unify scan persistence and remove cross-item fan-out, InvalidShowroomRef, reuse_key_from_signature(), showroom_reuse_key(), scan_babylon_item(), run_stale_check(), run_analysis(), add_item() (+29 more)

### Community 94 - "os"
Cohesion: 0.10
Nodes (20): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+12 more)

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

### Community 100 - "option"
Cohesion: 0.15
Nodes (6): init_db(), osspa_sync_cmd(), overlap_candidates_cmd(), scan(), serve(), vocab_stage_rescan()

### Community 101 - "Candidate"
Cohesion: 0.17
Nodes (9): _run_catalog_second_pass(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published(), test_query_state_defaults(), test_three_layer_workload_propagation() (+1 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.19
Nodes (8): Task 2: Reporting Sync Job, _build_field_source_sql(), run_field_source_sync(), FakeSettings, _mock_mcp_query(), test_field_source_sync_inserts_rows(), test_field_source_sync_no_mcp(), test_field_source_sync_replaces_on_rerun()

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (12): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+4 more)

### Community 108 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.18
Nodes (10): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Goals, Non-Goals, Parallel Pipeline Instances (+2 more)

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 112 - "config.py"
Cohesion: 0.03
Nodes (29): create_app(), lifespan(), RequestLoggingMiddleware, client(), client(), test_auth_me_unauthenticated(), client(), TestCreateApiKey (+21 more)

### Community 113 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.06
Nodes (22): db(), db(), db(), db(), db(), db(), db(), db() (+14 more)

### Community 120 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 121 - "StatusPage.tsx"
Cohesion: 0.22
Nodes (10): react-dom, vitest, LlmProviderCard(), LlmProviderStatus, LlmUse, status, USE_LABELS, CatalogStatus (+2 more)

### Community 123 - "Candidate"
Cohesion: 0.11
Nodes (10): Create, Delete, File Map, Task 1: Candidate Model Refactor, Task 2: Driver Base Class + Registry, Task 4: Architecture Driver, Candidate, test_candidate_universal_fields() (+2 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.15
Nodes (14): cancel_workflow(), check_pr_statuses(), get_issue_status(), _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr() (+6 more)

### Community 126 - "Review Focus"
Cohesion: 0.20
Nodes (7): Review Focus, Task 5: Shared frontend helpers and checkbox filter group, Task 7: Browse UI (provisional style), Task 8: Run locally, check, and prepare the PR, test_filter_platform_none_excludes_architectures(), test_filter_tdp_matches_tdp2(), test_labels_union_tdp2_only()

### Community 128 - "scan_configs"
Cohesion: 0.15
Nodes (6): ls_remote_sha(), regenerate_embeddings(), _resolve_ref_from_lookup(), scan_all_collections(), scan_collection(), scan_configs()

### Community 129 - "Decisions"
Cohesion: 0.12
Nodes (3): Platform and TDP Filters Implementation Plan, Decisions, retirement_label()

### Community 130 - "test_api_infrastructure.py"
Cohesion: 0.22
Nodes (3): client(), seed_infrastructure(), test_sync_osspa_endpoint_enqueues_a_job()

### Community 131 - "orchestrator.py"
Cohesion: 0.22
Nodes (10): build_scaffold(), compose_answer(), _strip_formatting(), _help_answer(), process_turn(), _scope_echo(), followup_chips(), test_answer_failure_degrades_to_scaffold() (+2 more)

### Community 132 - "database.py"
Cohesion: 0.08
Nodes (27): Content Owner Model Implementation Plan, Global Constraints, Review Focus, Rollout, Task 1: `content_owner` helper, Task 2: Database read and write methods for stubs, Task 3: Scan skips pure stubs, Task 4: Reconcile stub artifacts at every scan entry point (+19 more)

### Community 133 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 134 - "handlers.py"
Cohesion: 0.19
Nodes (15): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+7 more)

### Community 136 - "test_retirement_edit.py"
Cohesion: 0.08
Nodes (15): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_rejected_for_retired_item(), test_edit_rejected_while_cancellation_pending(), test_edit_rejects_name_without_replacement_ci() (+7 more)

### Community 139 - "CatalogReader"
Cohesion: 0.05
Nodes (58): Task 1: Resolve content sources with explicit ownership, Global Constraints, _apply_component_inheritance(), CatalogReader, collect(), load(), _collect_bases(), component_item_to_ci_name() (+50 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.20
Nodes (16): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+8 more)

### Community 169 - "_base_name_to_content_id"
Cohesion: 0.18
Nodes (13): approve_item(), ApproveRequest, _base_name_to_content_id(), edit_retirement(), EditRetirementRequest, ignore_item(), link_jira(), LinkJiraRequest (+5 more)

### Community 173 - "test_workers.py"
Cohesion: 0.21
Nodes (9): WorkerSettings, test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes(), test_worker_context_has_required_fields() (+1 more)

### Community 174 - "test_showroom_reuse.py"
Cohesion: 0.10
Nodes (18): Task 3: Fetch the exact source and reject non-content inputs, MemoryArtifacts, prime(), scan(), run(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_embedding_only_changes_repair_only_affected_artifacts() (+10 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "File map and verification conventions"
Cohesion: 0.33
Nodes (5): Execution handoff, Global Constraints, Review Focus, Self-review, Showroom Analysis Isolation Implementation Plan

### Community 180 - "hashlib"
Cohesion: 0.14
Nodes (10): ensure_issue_event_comment(), jira_auth_configured(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), reuse_lock_id(), test_comment_failed_lookup_does_not_post() (+2 more)

### Community 181 - "retirement_dashboard"
Cohesion: 0.33
Nodes (3): _extract_base_name_from_content_id(), retirement_dashboard(), TestRetirementDashboardMetrics

### Community 182 - "order_for_reuse"
Cohesion: 0.25
Nodes (6): Content Owner Model for Virtual CIs — Design, Problem, Rollout, Tests, What gets removed, order_for_reuse()

### Community 184 - "Content-Type Drivers Implementation Plan"
Cohesion: 0.40
Nodes (4): Content-Type Drivers Implementation Plan, Execution Notes, Global Constraints, Review Focus

### Community 185 - "extract_catalog_item"
Cohesion: 0.21
Nodes (7): Task 1: Read and store Platform/TDP labels, Non-goals, extract_catalog_item(), test_extract_keys_are_case_sensitive(), test_extract_missing_labels_are_none(), test_extract_reads_platform_and_tdps(), test_schema_adds_label_columns()

### Community 186 - "mcp_query"
Cohesion: 0.15
Nodes (9): Field Source Content Report — Implementation Plan, Global Constraints, Task 3: API Endpoint, Task 4: Frontend Page, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, mcp_query(), TestMcpQueryOrdering (+1 more)

### Community 187 - "status"
Cohesion: 0.29
Nodes (6): Data and Audit Trail, 3. Candidate Model, Candidate Dataclass, `content_entities` (shared table — all types), Source-specific tables, status()

### Community 189 - "start_retirement"
Cohesion: 0.50
Nodes (4): _resolve_replacement_source(), start_retirement(), _start_retirement_locked(), StartRequest

### Community 190 - "Field Source Content"
Cohesion: 0.25
Nodes (7): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git()

### Community 191 - "test_vocabulary_db.py"
Cohesion: 0.10
Nodes (5): TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched, TestUnknownTermsSchema

### Community 194 - "Task 2: Union labels per base name"
Cohesion: 0.20
Nodes (5): Task 2: Union labels per base name, test_labels_empty_input(), test_labels_include_retired_stage(), test_labels_union_across_stages(), test_labels_unlabeled_item_has_empty_lists()

### Community 195 - "test_start_retirement_holds_lock_while_creating_ticket"
Cohesion: 0.50
Nodes (4): _approved_unstarted(), test_start_retirement_holds_lock_while_creating_ticket(), fake_create(), test_start_retirement_respects_workflow_lock()

### Community 196 - "test_catalog_labels.py"
Cohesion: 0.27
Nodes (5): _seed_label_count_items(), test_label_counts_follow_other_filters(), test_label_counts_follow_search(), test_label_counts_unfiltered(), test_upsert_stores_labels()

### Community 202 - "Platform and Technical Decision Point filters — design"
Cohesion: 0.25
Nodes (7): Anti-goals, Constraints, Goals, Left to the builder, Platform and Technical Decision Point filters — design, Rollout, Why

### Community 203 - "TestPromptInjection"
Cohesion: 0.20
Nodes (3): build_analysis_prompt(), truncate_content(), TestPromptInjection

### Community 205 - "build_infrastructure_embedding_text"
Cohesion: 0.60
Nodes (3): build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

## Knowledge Gaps
- **105 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1321 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `scan_configs`, `Decisions`, `test_api_infrastructure.py`, `orchestrator.py`, `database.py`, `handlers.py`, `test_database_explicit_test_schema_reset_includes_delivery_queue`, `test_field_source_db.py`, `db/__init__.py`, `test_retirement_edit.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `ops.py`, `workload_scanner.py`, `test_db.py`, `Settings`, `_print`, `seed`, `settings.py`, `_generate_key`, `Any`, `extract_base_name`, `chat_sessions.py`, `run_osspa_sync`, `TestGetNonprodBaseNames`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `test_vocabulary_db.py`, `json`, `test_osspa_db.py`, `Task 2: Union labels per base name`, `test_start_retirement_holds_lock_while_creating_ticket`, `router.py`, `test_catalog_labels.py`, `test_infrastructure.py`, `Task 1: Database Schema and Methods`, `test_status_visibility.py`, `router.py`, `command`, `pipeline.py`, `run_category`, `test_nonprod.py`, `test_retirement_pr_status.py`, `os`, `option`, `._set_showroom_override`, `test_field_source_sync.py`, `config.py`, `.close`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `Database` (e.g. with `Settings` and `AnalysisSignature`) actually correct?**
  _`Database` has 53 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _105 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.11491935483870967 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `Database`, `test_api_infrastructure.py`, `orchestrator.py`, `database.py`, `handlers.py`, `routes/catalog.py`, `admin.py`, `test_retirement_edit.py`, `test_retirement_jira_events.py`, `CatalogReader`, `test_overlap_assessment.py`, `ops.py`, `workload_scanner.py`, `routes/auth.py`, `LLMResult`, `_print`, `seed`, `settings.py`, `advisor.py`, `JobProgressRelay`, `test_auth_middleware.py`, `Any`, `test_analyzer.py`, `test_workers.py`, `analysis.py`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `json`, `router.py`, `cli.py`, `router.py`, `command`, `pipeline.py`, `request`, `run_category`, `test_retirement_pr_status.py`, `test_llm_routing.py`, `test_showroom_scan.py`, `os`, `option`, `config.py`, `test_chat_handlers.py`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Are the 71 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 71 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.020808080808080807 - nodes in this community are weakly interconnected._