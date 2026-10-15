# Graph Report - rcars-advisory  (2026-10-15)

## Corpus Check
- 273 files · ~493,365 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 3046 nodes · 7146 edges · 165 communities (110 shown, 55 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 692 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dfa1dd2f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_auth_middleware.py
- Database
- registry.ts
- Portfolio Architecture Ingest Design Spec
- cli.py
- devDependencies
- services/catalog.py
- Request
- routes/catalog.py
- admin.py
- analyzer.py
- Infrastructure Catalog
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_agv_access.py
- typing
- ops.py
- migrate_to_content_model.py
- create_app
- test_db.py
- RouterOutput
- test_osspa_adoc.py
- workload_scanner.py
- Settings
- settings.py
- rationale.py
- schemas.py
- handlers.py
- App.tsx
- routes/auth.py
- orchestrator.py
- db/__init__.py
- JobProgressRelay
- test_jira_service.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- parse_analysis_response
- test_nonprod.py
- test_vocabulary_db.py
- config.py
- test_osspa_csv.py
- reporting_sync.py
- PerformancePage.tsx
- normalize_analysis
- dev-services.sh
- test_product_terms.py
- structlog
- test_auth_security.py
- test_chat_sessions_db.py
- generate_vocabulary_yaml
- test_drivers.py
- Path
- run_osspa_sync
- vocabulary/__init__.py
- Retirement System
- parse_analysis_response
- analyze_architecture_item
- test_catalog_osspa_routes.py
- .complete_job
- scan
- test_osspa_db.py
- RcarsMasthead.tsx
- test_reporting.py
- ContentAnalysisPage.tsx
- AdvisorPage.tsx
- api.ts
- ECA Production Redesign Spec
- group
- _base_name_to_content_id
- test_auth_routes.py
- Reporting MCP Data Sync
- test_status_visibility.py
- TestValidation
- SyncPage.tsx
- recommendations.py
- extract_base_name
- build_analysis_prompt
- _reconcile_queued_orphans
- mcp_query
- test_retirement_pr_status.py
- Candidate
- pytest
- ArchitectureDriver
- performance_dashboard
- _extrapolate_count
- Candidate
- System Design Architecture Doc
- AdocRead
- _build_windowed_metrics
- test_chat_turn_integration.py
- test_vocabulary_admin.py
- RCARS × agv-retire: Automated Retirement Pipeline
- osspa_sync.py
- Browse Page Redesign Plan
- API Authentication Design
- route
- test_workers.py
- devDependencies
- rcars-login.sh
- app.py
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- TestTokenExchange
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- Controlled Vocabulary Design
- cancel_workflow
- test_chat_handlers.py
- content_entities Table
- .close
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- Design
- test_api_infrastructure.py
- test_field_source_api.py
- test_infrastructure.py
- readiness
- _window_start
- OsspaSyncError
- docker-entrypoint.sh
- Webhook Configuration Task
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
- Match Event Prompt Template
- Field Source Content
- Python Requirements Entry Point
- Task 1: Database Schema and Methods

## God Nodes (most connected - your core abstractions)
1. `Database` - 258 edges
2. `Settings` - 159 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `react` - 33 edges
6. `run_osspa_sync()` - 31 edges
7. `ContentTypeDriver` - 31 edges
8. `create_app()` - 30 edges
9. `normalize_analysis()` - 30 edges
10. `WorkerContext` - 30 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Data and Audit Trail` --references--> `status()`  [INFERRED]
  docs/architecture/retirement-system.md → src/api/rcars/cli.py
- ``content_entities` (shared table — all types)` --references--> `status()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/cli.py
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Task 6: Orchestrator + Pipeline Refactor` --references--> `emit()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/pipeline.py

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

## Communities (165 total, 55 thin omitted)

### Community 0 - "test_auth_middleware.py"
Cohesion: 0.05
Nodes (29): _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), _log_auth_decision(), _parse_sa_allowlist(), require_admin(), require_auth() (+21 more)

### Community 2 - "registry.ts"
Cohesion: 0.12
Nodes (24): InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps (+16 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.21
Nodes (17): OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis, Nightly Maintenance Pipeline, OSSPA GitLab Repositories (+9 more)

### Community 4 - "cli.py"
Cohesion: 0.06
Nodes (29): cli(), flag(), get_db(), infra_stats(), init_db(), note(), osspa_sync_cmd(), overlap_candidates_cmd() (+21 more)

### Community 5 - "devDependencies"
Cohesion: 0.06
Nodes (30): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, @types/react (+22 more)

### Community 6 - "services/catalog.py"
Cohesion: 0.09
Nodes (14): _apply_component_inheritance(), CatalogReader, _collect_bases(), component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata() (+6 more)

### Community 7 - "Request"
Cohesion: 0.20
Nodes (11): analyze_single(), check_pr_statuses(), check_stale(), open_agv_notice_pr(), open_agv_retire_pr(), overlap_assess(), rescan_all(), retirement_sweep() (+3 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.13
Nodes (23): add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis(), get_catalog_item() (+15 more)

### Community 9 - "admin.py"
Cohesion: 0.12
Nodes (26): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+18 more)

### Community 10 - "analyzer.py"
Cohesion: 0.08
Nodes (17): process_item(), analyze_showroom(), build_infrastructure_embedding_text(), build_module_embedding_text(), check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), get_repo_head() (+9 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.07
Nodes (42): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Goals, Non-Goals, Parallel Pipeline Instances (+34 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (22): assess_overlap(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector(), _seed_overlap_pair() (+14 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (3): derive_status(), TestDeriveStatus, TestStepOrder

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_agv_access.py"
Cohesion: 0.06
Nodes (60): _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree(), _find_open_pr() (+52 more)

### Community 18 - "ops.py"
Cohesion: 0.09
Nodes (25): ls_remote_sha(), resolve_refs_to_shas(), batch_assess_overlaps(), build_sandbox_summary(), publish_progress(), WorkerContext, run_chat_turn(), on_progress() (+17 more)

### Community 19 - "migrate_to_content_model.py"
Cohesion: 0.06
Nodes (33): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+25 more)

### Community 20 - "create_app"
Cohesion: 0.10
Nodes (8): create_app(), client(), test_auth_me_unauthenticated(), client(), client(), non_admin_client(), test_retirement_contract_is_discoverable_in_swagger(), client()

### Community 21 - "test_db.py"
Cohesion: 0.09
Nodes (12): db(), db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default() (+4 more)

### Community 22 - "RouterOutput"
Cohesion: 0.20
Nodes (17): RouterOutput, Scope, resolve_and_verify(), _result_turns(), _turn_chips(), fake_embedding(), seed_chat_fixtures(), _settings() (+9 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "workload_scanner.py"
Cohesion: 0.07
Nodes (14): analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products(), read_config_code(), read_role_code(), scan_all_collections() (+6 more)

### Community 25 - "Settings"
Cohesion: 0.09
Nodes (27): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+19 more)

### Community 26 - "settings.py"
Cohesion: 0.21
Nodes (11): lifespan(), _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), recommend_startup(), scan_startup() (+3 more)

### Community 27 - "rationale.py"
Cohesion: 0.17
Nodes (9): Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, _primary_asset_type(), _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis(), _format_single_candidate(), generate_content_gaps() (+1 more)

### Community 28 - "schemas.py"
Cohesion: 0.06
Nodes (56): AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse, CatalogStatsResponse, ChatSubmitResponse (+48 more)

### Community 29 - "handlers.py"
Cohesion: 0.14
Nodes (16): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+8 more)

### Community 30 - "App.tsx"
Cohesion: 0.10
Nodes (24): @patternfly/react-core, react-dom, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo() (+16 more)

### Community 31 - "routes/auth.py"
Cohesion: 0.17
Nodes (15): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+7 more)

### Community 32 - "orchestrator.py"
Cohesion: 0.15
Nodes (12): build_evidence_pack(), _help_answer(), process_turn(), _scope_echo(), followup_chips(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted(), test_pack_includes_shared_workload_note() (+4 more)

### Community 33 - "db/__init__.py"
Cohesion: 0.14
Nodes (13): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), db(), seed_items(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item() (+5 more)

### Community 34 - "JobProgressRelay"
Cohesion: 0.11
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 35 - "test_jira_service.py"
Cohesion: 0.12
Nodes (12): Open Questions / Risks, _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _make_metrics(), _make_workflow(), test_basic_description(), test_creates_ticket_and_returns_key() (+4 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.10
Nodes (21): Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy (+13 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.13
Nodes (5): load_vocabulary(), _noise_variants(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "_generate_key"
Cohesion: 0.11
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "parse_analysis_response"
Cohesion: 0.18
Nodes (14): Content-Type Drivers Implementation Plan, Execution Notes, Global Constraints, Review Focus, parse_analysis_response(), test_dict(), test_empty_returns_none(), test_fenced_json() (+6 more)

### Community 42 - "test_nonprod.py"
Cohesion: 0.09
Nodes (7): TestGetNonprodBaseNames, TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestSyncNonprodUsage, TestUpsertNonprodUsage

### Community 43 - "test_vocabulary_db.py"
Cohesion: 0.09
Nodes (6): db(), TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched, TestUnknownTermsSchema

### Community 44 - "config.py"
Cohesion: 0.20
Nodes (12): _call_anthropic(), _call_litemaas(), call_llm(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), test_answer_failure_degrades_to_scaffold() (+4 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.25
Nodes (16): asset_type_tokens(), parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status(), test_normalize_row_builds_the_upsert_payload(), test_normalize_row_dedups_topics_from_solutions_and_verticals() (+8 more)

### Community 46 - "reporting_sync.py"
Cohesion: 0.12
Nodes (14): _jira_request(), _build_closed_sql(), _build_cost_sql(), _build_nonprod_provisions_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql() (+6 more)

### Community 47 - "PerformancePage.tsx"
Cohesion: 0.09
Nodes (38): fmt(), fmtRoi(), num(), scoreBg(), ScoreBreakdownPopover(), scoreColor(), ReplacementPicker(), stageBadgeClass (+30 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.12
Nodes (4): normalize_analysis(), _record_unknowns(), TestIgnoredTermsSuppression, TestNormalizeAnalysis

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "test_product_terms.py"
Cohesion: 0.08
Nodes (9): build_embedding_text(), _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestBuildEmbeddingText, TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone (+1 more)

### Community 51 - "structlog"
Cohesion: 0.12
Nodes (15): Modify, 2. Orchestrator and Pipeline, What Gets Deleted, generate_embedding(), registered_content_types(), QueryState, extract_urls(), run_category() (+7 more)

### Community 52 - "test_auth_security.py"
Cohesion: 0.11
Nodes (7): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders, TestUnauthenticatedAccess

### Community 53 - "test_chat_sessions_db.py"
Cohesion: 0.15
Nodes (10): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), db(), _log(), test_context_builder_shape_and_window() (+2 more)

### Community 54 - "generate_vocabulary_yaml"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "test_drivers.py"
Cohesion: 0.10
Nodes (21): HandsOnDriver, get_driver(), get_drivers_for_types(), format_triage_candidates(), _make_hands_on_candidate(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_format_triage_candidates_architecture() (+13 more)

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.25
Nodes (19): run_osspa_sync(), _csv(), db(), fake_analyze(), settings(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring() (+11 more)

### Community 58 - "vocabulary/__init__.py"
Cohesion: 0.12
Nodes (12): _entries_to_dicts(), _as_tuple(), _build_lookups(), _parse_entries(), _validate(), squash_key(), VocabEntry, Vocabulary (+4 more)

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
Cohesion: 0.17
Nodes (7): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 64 - "scan"
Cohesion: 0.23
Nodes (5): classify_scan_error(), regenerate_embeddings(), _propagate_to_sibling(), run_analysis(), _sanitize_format_suitability()

### Community 65 - "test_osspa_db.py"
Cohesion: 0.18
Nodes (9): _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_upsert_osspa_item_never_overwrites_llm_owned_fields(), test_upsert_osspa_item_unretires_on_reappearance() (+1 more)

### Community 66 - "RcarsMasthead.tsx"
Cohesion: 0.20
Nodes (13): API_DOCS_URL, DbStatus, formatAge(), getInitials(), HelpMenu(), RcarsMasthead(), applyTheme(), getInitialTheme() (+5 more)

### Community 67 - "test_reporting.py"
Cohesion: 0.13
Nodes (5): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), TestComputePerformanceScore

### Community 68 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 69 - "AdvisorPage.tsx"
Cohesion: 0.07
Nodes (40): Task 8: Frontend Refactor, 5. Frontend Card Rendering, Display Config Structure, react, BlockErrorBoundary, Props, State, ChatChip (+32 more)

### Community 70 - "api.ts"
Cohesion: 0.08
Nodes (25): vitest, hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField, Tab, Job (+17 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "group"
Cohesion: 0.15
Nodes (6): infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 73 - "_base_name_to_content_id"
Cohesion: 0.18
Nodes (17): approve_item(), ApproveRequest, _base_name_to_content_id(), get_workflow(), ignore_item(), link_jira(), LinkJiraRequest, nonprod_ignore() (+9 more)

### Community 74 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (4): client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (6): Retirement Analysis Integration Plan, Retirement Workflow Actions Plan, Generalized Content Model Plan, Overlap Analysis Redesign Plan, Advisor Multi-Intent Chat Plan, Performance Page Plan

### Community 76 - "test_status_visibility.py"
Cohesion: 0.27
Nodes (9): _arch(), db(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators(), test_search_embeddings_excludes_non_prod_by_default() (+1 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 79 - "recommendations.py"
Cohesion: 0.21
Nodes (4): get_recommendations(), RecommendationRequest, _run_low(), _run_medium()

### Community 81 - "build_analysis_prompt"
Cohesion: 0.09
Nodes (7): build_analysis_prompt(), truncate_content(), dedup_topics(), clear_vocabulary_cache(), TestPromptInjection, TestSquashKey, TestTopicDedup

### Community 82 - "_reconcile_queued_orphans"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 83 - "mcp_query"
Cohesion: 0.18
Nodes (8): Field Source Content Report — Implementation Plan, Global Constraints, Task 3: API Endpoint, Task 4: Frontend Page, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, mcp_query(), TestMcpPagination

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.07
Nodes (13): run_retirement_sweep(), test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), state(), test_cancel_stops_removal_before_creating_revert(), test_refresh_does_not_retire_unmerged_or_unknown_pr() (+5 more)

### Community 85 - "Candidate"
Cohesion: 0.14
Nodes (10): _run_catalog_second_pass(), test_candidate_similarity_pct(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published(), test_query_state_defaults() (+2 more)

### Community 86 - "pytest"
Cohesion: 0.14
Nodes (17): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+9 more)

### Community 87 - "ArchitectureDriver"
Cohesion: 0.21
Nodes (7): ArchitectureDriver, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 88 - "performance_dashboard"
Cohesion: 0.18
Nodes (8): _extract_base_name_from_content_id(), field_source_report(), nonprod_dashboard(), overlap_assessment_detail(), overlap_report(), performance_dashboard(), retirement_dashboard(), stream_job()

### Community 90 - "Candidate"
Cohesion: 0.11
Nodes (12): Create, Delete, File Map, Task 1: Candidate Model Refactor, Task 2: Driver Base Class + Registry, Task 3: Hands-on Driver, Task 4: Architecture Driver, Task 6: Orchestrator + Pipeline Refactor (+4 more)

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (18): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, architecture_analysis DB Table, RCARS Authentication Model, content_entities Universal Entity Registry Table, LLM Provider Routing (LiteMaaS / Vertex AI), Performance Scoring System (+10 more)

### Community 94 - "test_chat_turn_integration.py"
Cohesion: 0.39
Nodes (5): FakeLLM, _noop(), _settings(), test_out_of_scope_is_deterministic(), test_three_turn_session_scope_resolution()

### Community 95 - "test_vocabulary_admin.py"
Cohesion: 0.14
Nodes (4): clear_vocabulary_cache(), client(), TestRoleGating, TestVocabularyEndpoints

### Community 96 - "RCARS × agv-retire: Automated Retirement Pipeline"
Cohesion: 0.11
Nodes (17): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+9 more)

### Community 97 - "osspa_sync.py"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 98 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (4): Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "route"
Cohesion: 0.09
Nodes (17): _prefix_overlap(), build_router_prompt(), _expand_vocab_aliases(), _extract_json(), _find_keyword_ties(), _parse_catalog_url(), pattern_check(), route() (+9 more)

### Community 101 - "test_workers.py"
Cohesion: 0.16
Nodes (11): RecommendWorkerSettings, WorkerSettings, test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes() (+3 more)

### Community 102 - "devDependencies"
Cohesion: 0.15
Nodes (13): devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @types/react, @types/react-dom (+5 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.19
Nodes (8): Task 2: Reporting Sync Job, _build_field_source_sql(), run_field_source_sync(), FakeSettings, _mock_mcp_query(), test_field_source_sync_inserts_rows(), test_field_source_sync_no_mcp(), test_field_source_sync_replaces_on_rerun()

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.18
Nodes (14): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+6 more)

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 112 - "cancel_workflow"
Cohesion: 0.25
Nodes (3): cancel_workflow(), close_issue_wont_do(), test_jira_close_reports_whether_it_transitioned()

### Community 113 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.08
Nodes (14): migrate(), db(), db(), db(), db(), db(), db(), db() (+6 more)

### Community 120 - "Design"
Cohesion: 0.20
Nodes (10): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 6. Unified Serialization, Adding a New Content Type, Candidate Dataclass, `content_entities` (shared table — all types), Design (+2 more)

### Community 121 - "test_api_infrastructure.py"
Cohesion: 0.22
Nodes (3): client(), seed_infrastructure(), test_sync_osspa_endpoint_enqueues_a_job()

### Community 122 - "test_field_source_api.py"
Cohesion: 0.25
Nodes (3): client(), db(), test_field_source_route_registered()

### Community 126 - "OsspaSyncError"
Cohesion: 0.33
Nodes (3): fetch_palist_csv(), OsspaSyncError, _boom()

### Community 143 - "retirement-system.md"
Cohesion: 0.18
Nodes (19): Token Usage Tracking (5 Operation Types), CLI Admin Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference, Content Overlap Detection, Cosine Similarity for Overlap (+11 more)

### Community 174 - "Field Source Content"
Cohesion: 0.40
Nodes (5): API, Data Import, Data Source, Field Source Content, Frontend

## Knowledge Gaps
- **105 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1066 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **55 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `test_auth_middleware.py`, `cli.py`, `Request`, `routes/catalog.py`, `admin.py`, `analyzer.py`, `test_overlap_assessment.py`, `ops.py`, `create_app`, `RouterOutput`, `workload_scanner.py`, `settings.py`, `handlers.py`, `routes/auth.py`, `orchestrator.py`, `JobProgressRelay`, `config.py`, `structlog`, `test_auth_security.py`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `_base_name_to_content_id`, `test_auth_routes.py`, `recommendations.py`, `test_retirement_pr_status.py`, `performance_dashboard`, `test_chat_turn_integration.py`, `test_vocabulary_admin.py`, `route`, `test_workers.py`, `app.py`, `test_chat_handlers.py`, `.close`, `test_api_infrastructure.py`, `test_field_source_api.py`?**
  _High betweenness centrality (0.163) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `Database` (e.g. with `build_evidence_pack()` and `handle_help()`) actually correct?**
  _`Database` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _105 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_auth_middleware.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05396825396825397 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Database` to `cli.py`, `test_overlap_assessment.py`, `ops.py`, `test_db.py`, `RouterOutput`, `workload_scanner.py`, `settings.py`, `rationale.py`, `handlers.py`, `orchestrator.py`, `db/__init__.py`, `_generate_key`, `test_nonprod.py`, `test_vocabulary_db.py`, `structlog`, `test_chat_sessions_db.py`, `Task 1: Database Schema and Methods`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `.complete_job`, `test_osspa_db.py`, `test_status_visibility.py`, `extract_base_name`, `test_retirement_pr_status.py`, `test_chat_turn_integration.py`, `route`, `test_field_source_sync.py`, `.close`, `test_api_infrastructure.py`, `test_field_source_api.py`, `test_infrastructure.py`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Are the 67 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.02071563088512241 - nodes in this community are weakly interconnected._