# Graph Report - rcars-advisory  (2026-11-19)

## Corpus Check
- 314 files · ~547,708 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 4008 nodes · 9949 edges · 203 communities (143 shown, 60 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1090 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1fe248c3`
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
- agv_access.py
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
- test_showroom_source.py
- schemas.py
- seed
- App.tsx
- settings.py
- _settings
- .is_admin
- JobProgressRelay
- router.py
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
- cli.py
- run_category
- test_test_content_exclusion.py
- content_owner
- test_nonprod.py
- test_retirement_pr_status.py
- jira.py
- middleware/auth.py
- ArchitectureDriver
- build_retirement_description
- test_agv_access.py
- System Design Architecture Doc
- AdocRead
- test_showroom_scan.py
- asyncio
- Showroom analysis isolation
- Scan Pipeline
- normalize_row
- Browse Page Redesign Plan
- API Authentication Design
- Description-Based Analysis for Items With No Showroom — Design
- Candidate
- TestVocabularyEndpoints
- rcars-login.sh
- hashlib
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- Advisor v2 — Content-Type Drivers
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- .pool
- create_app
- ResolvedShowroom
- content_entities Table
- .close
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- test_reporting.py
- StatusPage.tsx
- build_embedding_text
- ContentTypeDriver
- test_orphan_cleanup.py
- retirement_cleanup.py
- test_llm_routing.py
- test_workers.py
- effective_analysis_source
- Decisions
- pipeline.py
- Task 2: Union labels per base name
- vector_search.py
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
- answer.py
- Match Event Prompt Template
- extract_base_name
- Task 7: API endpoint + detail fields
- test_showroom_reuse.py
- test_vocabulary.py
- Python Requirements Entry Point
- File map and verification conventions
- ensure_issue_event_comment
- TestTokenExchange
- Controlled Vocabulary Design
- test_catalog_labels.py
- rationale.py
- extract_catalog_item
- mcp_query
- FastAPI
- TestGetNonprodBaseNames
- TestBuildWindowedMetrics
- Field Source Content
- TestRecordUnknownTerm
- Content-Type Drivers Implementation Plan
- build_sandbox_summary
- GitHubAPIError
- test_start_retirement_holds_lock_while_creating_ticket
- observe_pr_events
- test_refresh_merged_notice_does_not_complete_open_removal
- test_manual_analysis_endpoint_rejects_test_item_before_job_creation
- test_infrastructure.py
- Task 1: Database Schema and Methods
- Platform and Technical Decision Point filters — design
- build_infrastructure_embedding_text

## God Nodes (most connected - your core abstractions)
1. `Database` - 306 edges
2. `Settings` - 182 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `scan_babylon_item()` - 52 edges
6. `seed()` - 46 edges
7. `create_app()` - 41 edges
8. `run_retirement_sweep()` - 40 edges
9. `ResolvedShowroom` - 39 edges
10. `content_owner()` - 37 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Data and Audit Trail` --references--> `status()`  [INFERRED]
  docs/architecture/retirement-system.md → src/api/rcars/cli.py
- ``content_entities` (shared table — all types)` --references--> `status()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/cli.py
- `Global Constraints` --references--> `parse_analysis_response()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/analyzer.py
- `Open Questions / Risks` --references--> `build_retirement_description()`  [INFERRED]
  docs/superpowers/specs/agv-retire-integration.md → src/api/rcars/services/jira.py

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

## Communities (203 total, 60 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.11
Nodes (17): _jira_request(), _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry() (+9 more)

### Community 2 - "registry.ts"
Cohesion: 0.07
Nodes (36): BlockErrorBoundary, Props, State, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps (+28 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.19
Nodes (19): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis (+11 more)

### Community 4 - "test_description_analysis.py"
Cohesion: 0.18
Nodes (34): Task 2: `Database.set_analysis_source()` setter, Task 4: Candidate selection, analyze_description(), add_description_item(), add_item(), mock_analysis(), persist_result(), seed_artifacts() (+26 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (43): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, @types/react (+35 more)

### Community 6 - "cli.py"
Cohesion: 0.13
Nodes (7): cli(), infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 7 - "db/__init__.py"
Cohesion: 0.13
Nodes (13): overlap_report(), generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats() (+5 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.11
Nodes (31): Task 9: Curator edits on a stub write the owner's analysis row, add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+23 more)

### Community 9 - "admin.py"
Cohesion: 0.08
Nodes (36): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+28 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.09
Nodes (22): event_time(), test_comment_missing_credentials_does_not_call_http(), unexpected(), test_database_no_jira_and_deleted_workflow_do_not_queue(), test_database_open_event_is_atomic_and_deduplicated(), test_database_rollout_cutoff_and_repeat_closures(), test_database_workflow_and_event_write_roll_back_together(), test_delivery_concurrent_senders_cannot_overtake_stream() (+14 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.09
Nodes (21): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+13 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (3): derive_status(), retirement_label(), TestDeriveStatus

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "agv_access.py"
Cohesion: 0.13
Nodes (20): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+12 more)

### Community 17 - "ops.py"
Cohesion: 0.10
Nodes (20): jira_auth_configured(), scan_all_collections(), publish_progress(), WorkerContext, run_chat_turn(), on_progress(), _progress_bridge(), _publish() (+12 more)

### Community 18 - "workload_scanner.py"
Cohesion: 0.07
Nodes (16): ls_remote_sha(), regenerate_embeddings(), _resolve_ref_from_lookup(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products() (+8 more)

### Community 19 - "Task 4: Browse server-side filters and facets"
Cohesion: 0.13
Nodes (8): Task 4: Browse server-side filters and facets, test_facets_platforms_and_tdps(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none()

### Community 20 - "routes/auth.py"
Cohesion: 0.18
Nodes (16): invalidate_api_key_cache(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token(), _user_max_role() (+8 more)

### Community 21 - "test_db.py"
Cohesion: 0.09
Nodes (10): _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default(), test_filtered_catalog_pagination(), test_filtered_catalog_search() (+2 more)

### Community 22 - "test_content_owner.py"
Cohesion: 0.13
Nodes (31): Task 4: Reconcile stub artifacts at every scan entry point, rescan_all(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner() (+23 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.10
Nodes (24): Pure stub, compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough() (+16 more)

### Community 24 - "react"
Cohesion: 0.12
Nodes (28): Task 8: Frontend Refactor, 5. Frontend Card Rendering, Display Config Structure, react, CATEGORY_LABELS, RecCardsBlock(), buildUrl(), FALLBACK_FORMAT_LABELS (+20 more)

### Community 25 - "Settings"
Cohesion: 0.08
Nodes (29): list_role_assignments(), llm_provider_status(), workload_scan(), call_llm(), fetch_litemaas_models(), _parse_csv(), Settings, settings() (+21 more)

### Community 26 - "LLMResult"
Cohesion: 0.22
Nodes (10): LLMResult, route(), _fake(), llm_call(), test_call_error_falls_back(), test_hallucinated_intent_falls_back_to_recommend(), test_malformed_then_valid_retries_once(), test_pattern_check_skips_llm() (+2 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.20
Nodes (24): Task 1: Resolve content sources with explicit ownership, component_item_to_ci_name(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous(), test_curator_content_path_override_is_not_a_pure_stub() (+16 more)

### Community 28 - "schemas.py"
Cohesion: 0.09
Nodes (34): field_source_report(), AgvPrResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse, CatalogStatsResponse, ContentPathResponse (+26 more)

### Community 29 - "seed"
Cohesion: 0.13
Nodes (30): Task 2: Persist source provenance and enforce scoped analysis reuse, Task 6: Advisor shows the stub in place of its owner, add_stub(), search(), test_ci_reference_to_a_stub_resolves_through_its_owner(), test_dev_hit_promotes_to_the_prod_counterpart_stub(), test_each_owner_promotes_to_its_own_stub(), test_exact_same_item_prod_requires_complete_matching_signature() (+22 more)

### Community 30 - "App.tsx"
Cohesion: 0.06
Nodes (51): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), API_DOCS_URL (+43 more)

### Community 31 - "settings.py"
Cohesion: 0.13
Nodes (13): _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url() (+5 more)

### Community 32 - "_settings"
Cohesion: 0.15
Nodes (31): _file_content(), _mock_client(), _resp(), _settings(), _setup_client_for_pr(), side_effect(), _setup_client_for_revert(), test_close_pr_sends_patch() (+23 more)

### Community 33 - ".is_admin"
Cohesion: 0.13
Nodes (17): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+9 more)

### Community 34 - "JobProgressRelay"
Cohesion: 0.12
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 35 - "router.py"
Cohesion: 0.11
Nodes (11): _prefix_overlap(), _expand_vocab_aliases(), _find_keyword_ties(), _parse_catalog_url(), pattern_check(), resolve_item(), _result_turns(), _turn_chips() (+3 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.10
Nodes (21): Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy (+13 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.13
Nodes (5): load_vocabulary(), _noise_variants(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "_generate_key"
Cohesion: 0.15
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.15
Nodes (21): _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow() (+13 more)

### Community 42 - "recommendations.py"
Cohesion: 0.10
Nodes (7): _get_user_key(), get_recommendations(), RecommendationRequest, _run_low(), _run_medium(), RecommendationLowResponse, RecommendationMediumResponse

### Community 43 - "Any"
Cohesion: 0.06
Nodes (8): Advisor, Browse, Curator edits, Model, Overlap, Scan, search(), test_legacy_test_sourced_wrapper_is_not_recommended()

### Community 44 - "test_analyzer.py"
Cohesion: 0.10
Nodes (25): check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content(), test_content_path_antora_start_path_resolves_pages_and_nav() (+17 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (19): asset_type_tokens(), fetch_palist_csv(), OsspaSyncError, parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status() (+11 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.13
Nodes (5): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), TestComputePerformanceScore

### Community 47 - "api.ts"
Cohesion: 0.08
Nodes (58): Review Focus, Task 5: Shared frontend helpers and checkbox filter group, Task 6: Wire filters into Performance, Non-Prod and Retirement, Task 7: Browse UI (provisional style), Task 8: Run locally, check, and prepare the PR, CollapsibleFilterGroup(), CollapsibleFilterGroupProps, LabelFilterGroup() (+50 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.10
Nodes (5): normalize_analysis(), _record_unknowns(), TestReviewBadgeUntouched, TestIgnoredTermsSuppression, TestNormalizeAnalysis

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "_expand_query_terms"
Cohesion: 0.09
Nodes (7): _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 51 - "analysis.py"
Cohesion: 0.13
Nodes (29): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), check_pr_statuses(), check_stale(), edit_retirement(), EditRetirementRequest (+21 more)

### Community 52 - "test_auth_security.py"
Cohesion: 0.08
Nodes (10): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders, TestUnauthenticatedAccess, test_already_closed_issue_needs_no_transition() (+2 more)

### Community 53 - "chat_sessions.py"
Cohesion: 0.18
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 54 - "Vocabulary"
Cohesion: 0.20
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "Task 3: Return labels from the three analysis endpoints"
Cohesion: 0.09
Nodes (14): Task 3: Return labels from the three analysis endpoints, _extract_base_name_from_content_id(), nonprod_dashboard(), overlap_assessment_detail(), performance_dashboard(), retirement_dashboard(), _sort_empty_last(), stream_job() (+6 more)

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.25
Nodes (19): run_osspa_sync(), _csv(), db(), fake_analyze(), settings(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring() (+11 more)

### Community 58 - "loader.py"
Cohesion: 0.11
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
Cohesion: 0.14
Nodes (7): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "json"
Cohesion: 0.18
Nodes (9): _extract_json(), migrate(), cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token() (+1 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.23
Nodes (9): _row(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override(), test_upsert_osspa_item_never_overwrites_llm_owned_fields(), test_upsert_osspa_item_unretires_on_reappearance() (+1 more)

### Community 66 - "HandsOnDriver"
Cohesion: 0.17
Nodes (10): Task 3: Hands-on Driver, What Moves Into Drivers, _extract_duration_target(), HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming() (+2 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.13
Nodes (12): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _build_windowed_metrics(), _mcp_call() (+4 more)

### Community 68 - "pytest"
Cohesion: 0.19
Nodes (18): RouterOutput, Scope, build_router_prompt(), resolve_and_verify(), test_intent_enum_closed(), test_performance_args_window_closed(), test_scope_shapes(), test_examples_validate_as_router_output() (+10 more)

### Community 69 - "test_sweep_github_only_cancellation_preserves_revert_until_jira_available"
Cohesion: 0.09
Nodes (11): test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), test_required_cancel_retains_workflow_on_jira_failure(), test_retired_items_cannot_be_cancelled() (+3 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (30): Task 4: Frontend Page, findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName() (+22 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "sync_opl_vocabulary.py"
Cohesion: 0.14
Nodes (14): _fetch_oauth_token(), _get_access_token(), build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary() (+6 more)

### Community 73 - "migrate_to_content_model.py"
Cohesion: 0.13
Nodes (14): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+6 more)

### Community 74 - "analyzer.py"
Cohesion: 0.08
Nodes (30): Task 3: `analyze_description()` in the analyzer, 3. Scan pipeline branch, Open items for the builder, analysis_context_hash(), analysis_from_row(), analyze_showroom(), build_analysis_prompt(), build_description_prompt() (+22 more)

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (6): Retirement Analysis Integration Plan, Retirement Workflow Actions Plan, Generalized Content Model Plan, Overlap Analysis Redesign Plan, Advisor Multi-Intent Chat Plan, Performance Page Plan

### Community 76 - "test_status_visibility.py"
Cohesion: 0.17
Nodes (11): _arch(), _seed_nonprod(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators(), test_nonprod_list_hides_item_with_finished_retirement_workflow() (+3 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - ".upsert_babylon_catalog_item"
Cohesion: 0.11
Nodes (3): Constraints, _do(), _do()

### Community 79 - "cli.py"
Cohesion: 0.08
Nodes (24): flag(), get_db(), infra_stats(), init_db(), note(), osspa_sync_cmd(), overlap_candidates_cmd(), override_url() (+16 more)

### Community 80 - "run_category"
Cohesion: 0.18
Nodes (12): Modify, Task 6: Orchestrator + Pipeline Refactor, 2. Orchestrator and Pipeline, What Gets Deleted, registered_content_types(), run_category(), emit(), serialize_candidates() (+4 more)

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.10
Nodes (20): _content_fields(), extract_showroom_url(), _resolve_template_var(), _source_node(), ComponentLink, ContentDeclaration, is_content_excluded(), resolve_showroom_source() (+12 more)

### Community 82 - "content_owner"
Cohesion: 0.13
Nodes (14): Review Focus, Task 1: `content_owner` helper, Task 2: Database read and write methods for stubs, Task 3: Scan skips pure stubs, Task 5: Mirror card fields when an owner scan saves, Task 7: `get_display_analysis` and the three runtime read sites, Task 8: Browse detail shows the owner's analysis and names the owner, description_source() (+6 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.09
Nodes (10): get_workflow(), _nonprod_retirement_metrics(), _retirement_metrics(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestNonprodWindows (+2 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.10
Nodes (26): run_retirement_sweep(), _sweep_context(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancellation_does_not_mark_concurrently_retired_item(), test_manual_pr_creation_respects_cleanup_lock(), test_refresh_does_not_retire_unmerged_or_unknown_pr(), test_required_failed_cancel_is_excluded_from_removal_and_retried_by_sweep(), test_required_merged_revert_cannot_bypass_jira_failure() (+18 more)

### Community 85 - "jira.py"
Cohesion: 0.09
Nodes (11): _close_issue(), close_issue_done(), close_issue_wont_do(), _issue_is_closed(), _move_to_in_progress(), _oauth_config(), _reset_token_cache(), _clean_token_cache() (+3 more)

### Community 86 - "middleware/auth.py"
Cohesion: 0.05
Nodes (29): _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), _log_auth_decision(), _parse_sa_allowlist(), require_admin(), require_auth() (+21 more)

### Community 88 - "ArchitectureDriver"
Cohesion: 0.14
Nodes (12): ArchitectureDriver, format_triage_candidates(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance() (+4 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.10
Nodes (18): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+10 more)

### Community 90 - "test_agv_access.py"
Cohesion: 0.13
Nodes (16): get_pr_state(), _pr_state_data(), _remove_notice_block(), _resolve_repo(), test_branch_name_format(), test_close_pr_returns_confirmed_terminal_metadata(), test_created_and_reused_pr_results_keep_creation_time(), test_pr_state_retains_remote_event_timestamps() (+8 more)

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.20
Nodes (16): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, LLM Provider Routing (LiteMaaS / Vertex AI), Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API (+8 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.08
Nodes (41): Task 4: Unify scan persistence and remove cross-item fan-out, start_scan(), classify_scan_error(), InvalidShowroomRef, order_for_reuse(), reuse_key_from_signature(), showroom_reuse_key(), reuse_lock_id() (+33 more)

### Community 94 - "asyncio"
Cohesion: 0.12
Nodes (22): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+14 more)

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
Cohesion: 0.09
Nodes (10): Candidate, _run_catalog_second_pass(), test_candidate_similarity_pct(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published() (+2 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "hashlib"
Cohesion: 0.11
Nodes (7): build_jira_event(), _deliver_pending_events(), event_timestamp(), client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.15
Nodes (12): Task 2: Reporting Sync Job, _build_field_source_sql(), run_field_source_sync(), FakeSettings, _mock_mcp_query(), _row(), test_field_source_sync_captures_user_email(), test_field_source_sync_ignores_agd_v2_items() (+4 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (12): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+4 more)

### Community 108 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.10
Nodes (20): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers, Approach Decision, Architecture (+12 more)

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - ".pool"
Cohesion: 0.12
Nodes (6): db(), db(), test_database_explicit_test_schema_reset_includes_delivery_queue(), client(), db(), create()

### Community 112 - "create_app"
Cohesion: 0.04
Nodes (22): create_app(), lifespan(), RequestLoggingMiddleware, client(), client(), test_sync_osspa_endpoint_enqueues_a_job(), client(), test_auth_me_unauthenticated() (+14 more)

### Community 113 - "ResolvedShowroom"
Cohesion: 0.15
Nodes (14): Task 6: Add a narrowly scoped reset and verify the full rebuild contract, ResolvedShowroom, main(), snapshots(), test_dry_run_performs_no_writes(), test_execute_requires_scans_paused_confirmation(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data() (+6 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.06
Nodes (23): db(), seed_infrastructure(), db(), db(), db(), db(), db(), db() (+15 more)

### Community 120 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 121 - "StatusPage.tsx"
Cohesion: 0.19
Nodes (11): react-dom, vitest, LlmProviderCard(), LlmProviderStatus, LlmUse, status, USE_LABELS, render() (+3 more)

### Community 123 - "ContentTypeDriver"
Cohesion: 0.08
Nodes (17): Create, Delete, File Map, Task 1: Candidate Model Refactor, Task 2: Driver Base Class + Registry, Task 4: Architecture Driver, ContentTypeDriver, get_driver() (+9 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.17
Nodes (13): cancel_workflow(), _sweep(), _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr(), complete_retirement() (+5 more)

### Community 126 - "test_llm_routing.py"
Cohesion: 0.19
Nodes (11): _call_litemaas(), _call_litemaas_inner(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors() (+3 more)

### Community 127 - "test_workers.py"
Cohesion: 0.21
Nodes (10): WorkerSettings, test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes(), test_worker_context_has_required_fields() (+2 more)

### Community 128 - "effective_analysis_source"
Cohesion: 0.17
Nodes (14): Description-Based Analysis Implementation Plan, Global Constraints, Review Focus, Task 1: Schema columns + `effective_analysis_source()`, Task 5: Scan pipeline branch, Task 6: Stale check exclusion, Task 8: Frontend edit drawer, Task 9: Full verification (+6 more)

### Community 129 - "Decisions"
Cohesion: 0.18
Nodes (4): Global Constraints, Platform and TDP Filters Implementation Plan, Decisions, _get_label()

### Community 130 - "pipeline.py"
Cohesion: 0.21
Nodes (5): FakeLLM, _noop(), _settings(), test_out_of_scope_is_deterministic(), test_three_turn_session_scope_resolution()

### Community 131 - "Task 2: Union labels per base name"
Cohesion: 0.17
Nodes (6): Task 2: Union labels per base name, test_labels_empty_input(), test_labels_include_retired_stage(), test_labels_union_across_stages(), test_labels_union_tdp2_only(), test_labels_unlabeled_item_has_empty_lists()

### Community 132 - "vector_search.py"
Cohesion: 0.11
Nodes (18): Content Owner Model Implementation Plan, Global Constraints, Rollout, Content Owner Model for Virtual CIs — Design, Problem, Rollout, Root cause, Tests (+10 more)

### Community 133 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 134 - "handlers.py"
Cohesion: 0.10
Nodes (31): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+23 more)

### Community 136 - "test_retirement_edit.py"
Cohesion: 0.05
Nodes (20): client(), _jira_event_messages(), non_admin_client(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_rejected_for_retired_item() (+12 more)

### Community 139 - "showroom_source.py"
Cohesion: 0.12
Nodes (11): _apply_component_inheritance(), CatalogReader, collect(), load(), _collect_bases(), extract_base_ci_refs(), extract_infrastructure_metadata(), is_agnosticd_v2() (+3 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.20
Nodes (16): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+8 more)

### Community 169 - "answer.py"
Cohesion: 0.30
Nodes (7): build_scaffold(), compose_answer(), _strip_formatting(), test_answer_failure_degrades_to_scaffold(), test_compose_prepends_scaffold(), llm(), test_scaffold_deterministic()

### Community 173 - "Task 7: API endpoint + detail fields"
Cohesion: 0.47
Nodes (9): Task 7: API endpoint + detail fields, AnalysisSourceRequest, set_analysis_source(), route_request(), test_analysis_source_endpoint_curator_ok(), test_analysis_source_endpoint_custom_without_text_400(), test_analysis_source_endpoint_empty_description_400(), test_analysis_source_endpoint_requires_curator() (+1 more)

### Community 174 - "test_showroom_reuse.py"
Cohesion: 0.09
Nodes (21): Data Import, Task 3: Fetch the exact source and reject non-content inputs, git_repo(), git(), MemoryArtifacts, prime(), scan(), run() (+13 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "File map and verification conventions"
Cohesion: 0.25
Nodes (7): Execution handoff, File map and verification conventions, Global Constraints, Review Focus, Self-review, Showroom Analysis Isolation Implementation Plan, Task 5: Keep recommendation identities within authorized relationships

### Community 180 - "ensure_issue_event_comment"
Cohesion: 0.12
Nodes (11): ensure_issue_event_comment(), client(), comments(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response() (+3 more)

### Community 182 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 183 - "test_catalog_labels.py"
Cohesion: 0.27
Nodes (5): _seed_label_count_items(), test_label_counts_follow_other_filters(), test_label_counts_follow_search(), test_label_counts_unfiltered(), test_upsert_stores_labels()

### Community 184 - "rationale.py"
Cohesion: 0.15
Nodes (12): Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, _primary_asset_type(), QueryState, _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis(), _format_single_candidate() (+4 more)

### Community 185 - "extract_catalog_item"
Cohesion: 0.21
Nodes (7): Task 1: Read and store Platform/TDP labels, Non-goals, extract_catalog_item(), test_extract_keys_are_case_sensitive(), test_extract_missing_labels_are_none(), test_extract_reads_platform_and_tdps(), test_schema_adds_label_columns()

### Community 186 - "mcp_query"
Cohesion: 0.16
Nodes (8): Field Source Content Report — Implementation Plan, Global Constraints, Task 3: API Endpoint, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 187 - "FastAPI"
Cohesion: 0.29
Nodes (4): health(), readiness(), HealthResponse, ReadinessResponse

### Community 190 - "Field Source Content"
Cohesion: 0.50
Nodes (4): API, Data Source, Field Source Content, Frontend

### Community 192 - "Content-Type Drivers Implementation Plan"
Cohesion: 0.40
Nodes (4): Content-Type Drivers Implementation Plan, Execution Notes, Global Constraints, Review Focus

### Community 195 - "test_start_retirement_holds_lock_while_creating_ticket"
Cohesion: 0.50
Nodes (4): _approved_unstarted(), test_start_retirement_holds_lock_while_creating_ticket(), fake_create(), test_start_retirement_respects_workflow_lock()

### Community 202 - "Platform and Technical Decision Point filters — design"
Cohesion: 0.25
Nodes (7): Anti-goals, Constraints, Goals, Left to the builder, Platform and Technical Decision Point filters — design, Rollout, Why

### Community 205 - "build_infrastructure_embedding_text"
Cohesion: 0.28
Nodes (5): build_infrastructure_embedding_text(), build_module_embedding_text(), analysis_artifacts_complete(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

## Knowledge Gaps
- **105 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1344 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **60 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `effective_analysis_source`, `Decisions`, `pipeline.py`, `Task 2: Union labels per base name`, `vector_search.py`, `handlers.py`, `db/__init__.py`, `test_retirement_edit.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `derive_status`, `ops.py`, `workload_scanner.py`, `test_db.py`, `test_content_owner.py`, `Settings`, `seed`, `settings.py`, `router.py`, `_generate_key`, `Any`, `extract_base_name`, `chat_sessions.py`, `test_catalog_labels.py`, `rationale.py`, `run_osspa_sync`, `TestGetNonprodBaseNames`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `json`, `test_osspa_db.py`, `test_start_retirement_holds_lock_while_creating_ticket`, `pytest`, `test_infrastructure.py`, `Task 1: Database Schema and Methods`, `test_status_visibility.py`, `.upsert_babylon_catalog_item`, `cli.py`, `run_category`, `content_owner`, `test_nonprod.py`, `test_retirement_pr_status.py`, `.list_retirement_ready_for_removal`, `test_showroom_scan.py`, `asyncio`, `Description-Based Analysis for Items With No Showroom — Design`, `test_field_source_sync.py`, `.pool`, `create_app`, `ResolvedShowroom`, `.close`?**
  _High betweenness centrality (0.183) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `Database` (e.g. with `Settings` and `AnalysisSignature`) actually correct?**
  _`Database` has 53 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _105 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.1053763440860215 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `effective_analysis_source`, `Database`, `pipeline.py`, `test_description_analysis.py`, `handlers.py`, `routes/catalog.py`, `admin.py`, `test_retirement_edit.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `ops.py`, `routes/auth.py`, `LLMResult`, `seed`, `settings.py`, `.is_admin`, `JobProgressRelay`, `router.py`, `answer.py`, `recommendations.py`, `Task 7: API endpoint + detail fields`, `analysis.py`, `test_auth_security.py`, `ensure_issue_event_comment`, `Task 3: Return labels from the three analysis endpoints`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `json`, `pytest`, `analyzer.py`, `cli.py`, `run_category`, `test_test_content_exclusion.py`, `test_retirement_pr_status.py`, `middleware/auth.py`, `asyncio`, `hashlib`, `.pool`, `create_app`, `ResolvedShowroom`, `test_llm_routing.py`, `test_workers.py`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Are the 72 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 72 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.021616161616161617 - nodes in this community are weakly interconnected._