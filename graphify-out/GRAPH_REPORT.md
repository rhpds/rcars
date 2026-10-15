# Graph Report - rcars-advisory  (2026-10-15)

## Corpus Check
- 269 files · ~489,163 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 2986 nodes · 7018 edges · 185 communities (112 shown, 73 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 677 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7298eca7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _make_request
- Database Layer
- Advisor Frontend
- Portfolio Architecture Ingest Design Spec
- cli.py
- Frontend Config
- Catalog Service
- Analysis API Routes
- Catalog API Routes
- Admin API Routes
- analyzer.py
- Architecture Docs
- Browse UI Components
- Overlap Assessment
- Retirement Workflow
- Design Specs
- jira.py
- _format_single_candidate
- ops.py
- Migration Scripts
- app.py
- Test Fixtures
- router.py
- OSSPA Sync
- unittest_mock
- Configuration
- structlog
- Jira Integration
- schemas.py
- chat/models.py
- App.tsx
- routes/auth.py
- seed_chat_fixtures
- db/__init__.py
- JobProgressRelay
- handlers.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- test_api_keys_db.py
- compilerOptions
- recommendations.py
- test_nonprod.py
- test_vocabulary_db.py
- config.py
- test_osspa_csv.py
- reporting_sync.py
- PerformancePage.tsx
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- test_agv_access.py
- test_auth_security.py
- chat_sessions.py
- Vocabulary
- Any
- Path
- run_osspa_sync
- loader.py
- sync_opl_vocabulary.py
- event_parser.py
- test_osspa_analysis.py
- test_catalog_osspa_routes.py
- ArchitectureDriver
- scan.py
- test_osspa_db.py
- RcarsMasthead.tsx
- compute_sales_impact
- ContentAnalysisPage.tsx
- react
- api.ts
- ECA Production Redesign Spec
- middleware/auth.py
- test_auth_routes.py
- test_drivers.py
- Reporting MCP Data Sync
- test_status_visibility.py
- TestValidation
- SyncPage.tsx
- reporting_db_show
- extract_base_name
- test_vocabulary.py
- test_orphan_cleanup.py
- mcp_query
- test_chat_live.py
- Candidate
- ContentTypeDriver
- pipeline.py
- .is_admin
- test_reporting.py
- create_app
- .close
- osspa_sync.py
- test_vocabulary.py
- test_vocabulary_admin.py
- json
- Browse Page Redesign Plan
- API Authentication Design
- test_auth_middleware.py
- test_workers.py
- _user_has_db_role
- rcars-login.sh
- System Design Architecture Doc
- RCARS × agv-retire: Automated Retirement Pipeline
- API Key Authentication
- Performance Analysis
- TestTokenExchange
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- Controlled Vocabulary Design
- test_field_source_sync.py
- RCARS OCP Deployment Playbook
- route
- patch
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- test_chat_handlers.py
- content_entities Table
- Task 1: Database Schema and Methods
- test_api_infrastructure.py
- FastAPI
- run_category
- BlockErrorBoundary
- .complete_job
- _parse_sa_allowlist
- TestBuildWindowedMetrics
- OsspaSyncError
- db
- AdocRead
- .advisory_lock
- db
- docker-entrypoint.sh
- Webhook Configuration Task
- OpenShift OAuth Proxy (Red Hat SSO)
- Follow-up Chips
- Item Facts Intent
- API Reference
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
- test_retirement_pr_status.py
- Python Requirements Entry Point

## God Nodes (most connected - your core abstractions)
1. `Database` - 257 edges
2. `Settings` - 157 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `react` - 32 edges
6. `run_osspa_sync()` - 31 edges
7. `ContentTypeDriver` - 31 edges
8. `normalize_analysis()` - 30 edges
9. `WorkerContext` - 30 edges
10. `run_category()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- ``content_entities` (shared table — all types)` --references--> `status()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/cli.py
- `Global Constraints` --references--> `parse_analysis_response()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/analyzer.py
- `Task 1: Candidate Model Refactor` --references--> `Candidate`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/models.py
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py

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

## Communities (185 total, 73 thin omitted)

### Community 0 - "_make_request"
Cohesion: 0.21
Nodes (5): get_current_user(), _make_request(), TestApiKeyAuth, TestGetCurrentUser, TestProxySecretEnforcement

### Community 2 - "Advisor Frontend"
Cohesion: 0.09
Nodes (35): react, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock() (+27 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.21
Nodes (17): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis, OSSPA GitLab Repositories (+9 more)

### Community 4 - "cli.py"
Cohesion: 0.06
Nodes (31): cli(), flag(), get_db(), infra_group(), infra_stats(), init_db(), note(), osspa_group() (+23 more)

### Community 5 - "Frontend Config"
Cohesion: 0.05
Nodes (43): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, @types/react (+35 more)

### Community 6 - "Catalog Service"
Cohesion: 0.09
Nodes (14): _apply_component_inheritance(), CatalogReader, _collect_bases(), component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata() (+6 more)

### Community 7 - "Analysis API Routes"
Cohesion: 0.08
Nodes (41): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), check_pr_statuses(), check_stale(), _extract_base_name_from_content_id(), field_source_report() (+33 more)

### Community 8 - "Catalog API Routes"
Cohesion: 0.14
Nodes (22): add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis(), get_catalog_item() (+14 more)

### Community 9 - "Admin API Routes"
Cohesion: 0.09
Nodes (37): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+29 more)

### Community 10 - "analyzer.py"
Cohesion: 0.05
Nodes (29): process_item(), analyze_showroom(), build_infrastructure_embedding_text(), build_module_embedding_text(), check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), generate_embedding() (+21 more)

### Community 11 - "Architecture Docs"
Cohesion: 0.11
Nodes (22): Advisor Chat System, Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, Content Overlap Detection (+14 more)

### Community 12 - "Browse UI Components"
Cohesion: 0.10
Nodes (34): Summary, vitest, getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl() (+26 more)

### Community 13 - "Overlap Assessment"
Cohesion: 0.07
Nodes (33): parse_analysis_response(), assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment() (+25 more)

### Community 14 - "Retirement Workflow"
Cohesion: 0.07
Nodes (3): derive_status(), TestDeriveStatus, TestStepOrder

### Community 15 - "Design Specs"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "jira.py"
Cohesion: 0.19
Nodes (4): close_issue_wont_do(), get_issue_status(), _jira_request(), _mcp_call()

### Community 17 - "_format_single_candidate"
Cohesion: 0.27
Nodes (7): Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, _primary_asset_type(), _build_deterministic_assessment(), _call_rationale_single(), _format_single_candidate(), generate_rationale()

### Community 18 - "ops.py"
Cohesion: 0.08
Nodes (26): resolve_refs_to_shas(), build_sandbox_summary(), scan_all_collections(), publish_progress(), WorkerContext, run_chat_turn(), on_progress(), _progress_bridge() (+18 more)

### Community 19 - "Migration Scripts"
Cohesion: 0.13
Nodes (14): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+6 more)

### Community 21 - "Test Fixtures"
Cohesion: 0.09
Nodes (11): db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default(), test_filtered_catalog_pagination() (+3 more)

### Community 22 - "router.py"
Cohesion: 0.14
Nodes (20): _prefix_overlap(), RouterOutput, Scope, _expand_vocab_aliases(), _find_keyword_ties(), _parse_catalog_url(), pattern_check(), resolve_and_verify() (+12 more)

### Community 23 - "OSSPA Sync"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 25 - "Configuration"
Cohesion: 0.14
Nodes (16): _parse_csv(), Settings, settings(), test_admin_check(), test_chat_intent_roles_invalid_role_rejected(), test_chat_intent_roles_parse(), test_chat_model_defaults_follow_triage_and_rationale(), test_chat_models_explicit_override() (+8 more)

### Community 26 - "structlog"
Cohesion: 0.21
Nodes (10): lifespan(), _add_component(), get_logger(), _reorder_keys(), setup_logging(), recommend_startup(), scan_startup(), _startup() (+2 more)

### Community 27 - "Jira Integration"
Cohesion: 0.14
Nodes (11): _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _make_metrics(), _make_workflow(), test_basic_description(), test_creates_ticket_and_returns_key(), test_no_notes() (+3 more)

### Community 28 - "schemas.py"
Cohesion: 0.10
Nodes (31): AuthMeResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse, CatalogStatsResponse, ChatSubmitResponse, ContentPathResponse, ErrorDetail (+23 more)

### Community 29 - "chat/models.py"
Cohesion: 0.19
Nodes (14): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+6 more)

### Community 30 - "App.tsx"
Cohesion: 0.09
Nodes (28): @patternfly/react-core, react-dom, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo() (+20 more)

### Community 31 - "routes/auth.py"
Cohesion: 0.16
Nodes (16): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+8 more)

### Community 32 - "seed_chat_fixtures"
Cohesion: 0.15
Nodes (14): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+6 more)

### Community 33 - "db/__init__.py"
Cohesion: 0.11
Nodes (13): overlap_report(), overlap_candidates_cmd(), generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item() (+5 more)

### Community 34 - "JobProgressRelay"
Cohesion: 0.09
Nodes (24): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Frontend Progress Display, Goals, Non-Goals (+16 more)

### Community 35 - "handlers.py"
Cohesion: 0.21
Nodes (15): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+7 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.10
Nodes (21): Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy (+13 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.12
Nodes (6): load_vocabulary(), _noise_variants(), snap_term(), _normalize_products(), TestLoadPackagedDefault, TestMatchLadder

### Community 38 - "render_vocabulary_block"
Cohesion: 0.20
Nodes (3): _mode_for(), render_vocabulary_block(), TestRenderVocabularyBlock

### Community 39 - "test_api_keys_db.py"
Cohesion: 0.16
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "recommendations.py"
Cohesion: 0.24
Nodes (4): get_recommendations(), RecommendationRequest, _run_low(), _run_medium()

### Community 42 - "test_nonprod.py"
Cohesion: 0.10
Nodes (6): TestGetNonprodBaseNames, TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestUpsertNonprodUsage

### Community 43 - "test_vocabulary_db.py"
Cohesion: 0.10
Nodes (5): TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched, TestUnknownTermsSchema

### Community 44 - "config.py"
Cohesion: 0.17
Nodes (14): _call_anthropic(), _call_litemaas(), call_llm(), LLMResult, build_scaffold(), compose_answer(), _help_answer(), process_turn() (+6 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.25
Nodes (16): asset_type_tokens(), parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status(), test_normalize_row_builds_the_upsert_payload(), test_normalize_row_dedups_topics_from_solutions_and_verticals() (+8 more)

### Community 46 - "reporting_sync.py"
Cohesion: 0.11
Nodes (16): Task 2: Reporting Sync Job, _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_nonprod_provisions_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql() (+8 more)

### Community 47 - "PerformancePage.tsx"
Cohesion: 0.10
Nodes (36): fmt(), fmtRoi(), num(), scoreBg(), ScoreBreakdownPopover(), scoreColor(), ReplacementPicker(), stageBadgeClass (+28 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.12
Nodes (4): normalize_analysis(), _record_unknowns(), TestIgnoredTermsSuppression, TestNormalizeAnalysis

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "_expand_query_terms"
Cohesion: 0.08
Nodes (9): build_embedding_text(), _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestBuildEmbeddingText, TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone (+1 more)

### Community 51 - "test_agv_access.py"
Cohesion: 0.06
Nodes (59): cancel_workflow(), _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+51 more)

### Community 52 - "test_auth_security.py"
Cohesion: 0.11
Nodes (7): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders, TestUnauthenticatedAccess

### Community 53 - "chat_sessions.py"
Cohesion: 0.18
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 54 - "Vocabulary"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.37
Nodes (16): run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items(), test_missing_detail_page_marks_stale_and_skips() (+8 more)

### Community 58 - "loader.py"
Cohesion: 0.13
Nodes (11): _entries_to_dicts(), _as_tuple(), _build_lookups(), _parse_entries(), _validate(), squash_key(), VocabEntry, Vocabulary (+3 more)

### Community 59 - "sync_opl_vocabulary.py"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 60 - "event_parser.py"
Cohesion: 0.15
Nodes (7): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), _strip_html(), _validate_url()

### Community 61 - "test_osspa_analysis.py"
Cohesion: 0.16
Nodes (11): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms(), test_analyze_uses_the_dedicated_model_when_configured() (+3 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.17
Nodes (7): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "ArchitectureDriver"
Cohesion: 0.21
Nodes (7): ArchitectureDriver, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 64 - "scan.py"
Cohesion: 0.22
Nodes (6): _cli_propagate(), classify_scan_error(), regenerate_embeddings(), _propagate_to_sibling(), run_analysis(), _sanitize_format_suitability()

### Community 65 - "test_osspa_db.py"
Cohesion: 0.24
Nodes (8): _row(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_upsert_osspa_item_never_overwrites_llm_owned_fields(), test_upsert_osspa_item_unretires_on_reappearance(), test_upsert_osspa_item_writes_all_three_rows()

### Community 66 - "RcarsMasthead.tsx"
Cohesion: 0.20
Nodes (13): API_DOCS_URL, DbStatus, formatAge(), getInitials(), HelpMenu(), RcarsMasthead(), applyTheme(), getInitialTheme() (+5 more)

### Community 67 - "compute_sales_impact"
Cohesion: 0.13
Nodes (5): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), TestComputePerformanceScore

### Community 68 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 69 - "react"
Cohesion: 0.11
Nodes (26): Task 8: Frontend Refactor, 5. Frontend Card Rendering, Display Config Structure, buildUrl(), FALLBACK_FORMAT_LABELS, FORMAT_COLORS, RecCard(), RecCardProps (+18 more)

### Community 70 - "api.ts"
Cohesion: 0.10
Nodes (21): FieldSourcePage(), formatDate(), repoDisplayName(), SortField, Tab, FieldSourceData, FieldSourceProvision, FieldSourceRepo (+13 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "middleware/auth.py"
Cohesion: 0.19
Nodes (10): _check_api_key_role_ceiling(), _get_cached_role_assignments(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), require_performance_view(), _validate_api_key_cached() (+2 more)

### Community 73 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (4): client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 74 - "test_drivers.py"
Cohesion: 0.09
Nodes (21): HandsOnDriver, get_driver(), get_drivers_for_types(), format_triage_candidates(), _make_hands_on_candidate(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_format_triage_candidates_architecture() (+13 more)

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (6): Retirement Analysis Integration Plan, Retirement Workflow Actions Plan, Generalized Content Model Plan, Overlap Analysis Redesign Plan, Advisor Multi-Intent Chat Plan, Performance Page Plan

### Community 76 - "test_status_visibility.py"
Cohesion: 0.36
Nodes (8): _arch(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators(), test_search_embeddings_excludes_non_prod_by_default(), test_search_embeddings_includes_dev_when_asked()

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 81 - "test_vocabulary.py"
Cohesion: 0.20
Nodes (3): build_analysis_prompt(), truncate_content(), TestPromptInjection

### Community 82 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 83 - "mcp_query"
Cohesion: 0.18
Nodes (8): Field Source Content Report — Implementation Plan, Global Constraints, Task 3: API Endpoint, Task 4: Frontend Page, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, mcp_query(), TestMcpPagination

### Community 84 - "test_chat_live.py"
Cohesion: 0.17
Nodes (8): build_router_prompt(), _noop(), _settings(), test_live_item_facts_turn(), test_live_out_of_scope(), test_examples_validate_as_router_output(), test_followup_chips_are_pre_routed(), test_prompt_contains_every_intent_and_context()

### Community 85 - "Candidate"
Cohesion: 0.15
Nodes (11): Candidate, _run_catalog_second_pass(), test_candidate_similarity_pct(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published() (+3 more)

### Community 86 - "ContentTypeDriver"
Cohesion: 0.07
Nodes (13): Content-Type Drivers Implementation Plan, Create, Delete, Execution Notes, File Map, Global Constraints, Review Focus, Task 1: Candidate Model Refactor (+5 more)

### Community 87 - "pipeline.py"
Cohesion: 0.10
Nodes (6): registered_content_types(), QueryState, _call_synthesis(), generate_content_gaps(), search(), _strip_embedding_filler()

### Community 88 - ".is_admin"
Cohesion: 0.19
Nodes (12): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+4 more)

### Community 89 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 90 - "create_app"
Cohesion: 0.09
Nodes (8): create_app(), client(), test_auth_me_unauthenticated(), client(), client(), non_admin_client(), client(), test_field_source_route_registered()

### Community 92 - ".close"
Cohesion: 0.06
Nodes (23): migrate(), seed_infrastructure(), db(), db(), db(), db(), db(), db() (+15 more)

### Community 93 - "osspa_sync.py"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 94 - "test_vocabulary.py"
Cohesion: 0.13
Nodes (5): dedup_topics(), clear_vocabulary_cache(), TestAnalyzerNormalizesOnce, TestSquashKey, TestTopicDedup

### Community 95 - "test_vocabulary_admin.py"
Cohesion: 0.14
Nodes (4): clear_vocabulary_cache(), client(), TestRoleGating, TestVocabularyEndpoints

### Community 97 - "json"
Cohesion: 0.25
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 98 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (4): Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "test_auth_middleware.py"
Cohesion: 0.16
Nodes (6): _fetch_group_members(), _user_in_groups(), _mock_async_client_get(), _mock_group_response(), TestApiKeyRoleCeiling, TestGroupLookup

### Community 101 - "test_workers.py"
Cohesion: 0.16
Nodes (11): RecommendWorkerSettings, WorkerSettings, test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes() (+3 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (18): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Babylon CRD Catalog Pipeline, LLM Provider Routing (LiteMaaS / Vertex AI), Nightly Maintenance Pipeline, Performance Scoring System (+10 more)

### Community 105 - "RCARS × agv-retire: Automated Retirement Pipeline"
Cohesion: 0.11
Nodes (17): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+9 more)

### Community 107 - "Performance Analysis"
Cohesion: 0.15
Nodes (14): Token Usage Tracking (5 Operation Types), Worker Management, Token Usage Tracking Guide, API, Data Import, Data Source, Field Source Content, Frontend (+6 more)

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 112 - "test_field_source_sync.py"
Cohesion: 0.24
Nodes (6): run_field_source_sync(), FakeSettings, _mock_mcp_query(), test_field_source_sync_inserts_rows(), test_field_source_sync_no_mcp(), test_field_source_sync_replaces_on_rerun()

### Community 113 - "RCARS OCP Deployment Playbook"
Cohesion: 0.16
Nodes (15): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+7 more)

### Community 114 - "route"
Cohesion: 0.18
Nodes (10): _extract_json(), route(), _fake(), llm_call(), test_call_error_falls_back(), test_hallucinated_intent_falls_back_to_recommend(), test_malformed_then_valid_retries_once(), test_pattern_check_skips_llm() (+2 more)

### Community 115 - "patch"
Cohesion: 0.36
Nodes (4): _validate_sa_token(), _mock_async_client(), _mock_token_review_response(), TestValidateSaToken

### Community 120 - "test_chat_handlers.py"
Cohesion: 0.47
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 121 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 124 - "FastAPI"
Cohesion: 0.29
Nodes (4): health(), readiness(), HealthResponse, ReadinessResponse

### Community 125 - "run_category"
Cohesion: 0.11
Nodes (24): Modify, Task 3: Hands-on Driver, Task 6: Orchestrator + Pipeline Refactor, 1. Content-Type Drivers, 2. Orchestrator and Pipeline, 3. Candidate Model, 4. SSE Streaming, 6. Unified Serialization (+16 more)

### Community 126 - "BlockErrorBoundary"
Cohesion: 0.25
Nodes (3): BlockErrorBoundary, Props, State

### Community 130 - "OsspaSyncError"
Cohesion: 0.33
Nodes (3): fetch_palist_csv(), OsspaSyncError, _boom()

### Community 132 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 172 - "test_retirement_pr_status.py"
Cohesion: 0.14
Nodes (8): run_retirement_sweep(), client(), test_refresh_does_not_retire_unmerged_or_unknown_pr(), test_refresh_merged_notice_does_not_complete_open_removal(), test_sweep_does_not_retire_from_merged_notice_alone(), test_sweep_does_not_retire_unmerged_or_unknown_pr(), test_sweep_reconciles_merged_removal_without_new_prs_due(), test_sweep_reconciles_merged_revert_without_new_prs_due()

## Knowledge Gaps
- **106 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+101 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1036 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **73 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database Layer` to `db`, `cli.py`, `.advisory_lock`, `.retire_missing_babylon`, `db`, `.get_channel_metrics_map`, `analyzer.py`, `.get_queued_job_ids`, `Overlap Assessment`, `_format_single_candidate`, `ops.py`, `Test Fixtures`, `router.py`, `structlog`, `seed_chat_fixtures`, `db/__init__.py`, `handlers.py`, `test_api_keys_db.py`, `.list_nonprod_items`, `test_nonprod.py`, `test_vocabulary_db.py`, `config.py`, `.list_retirement_items`, `.list_retirement_pending_revert`, `.prune_expired_api_keys`, `test_retirement_pr_status.py`, `.prune_old_jobs`, `.record_unknown_term`, `.replace_embeddings`, `.retire_missing_osspa`, `Any`, `.revoke_user_cli_keys`, `.upsert_nonprod_usage`, `chat_sessions.py`, `run_osspa_sync`, `test_osspa_analysis.py`, `test_catalog_osspa_routes.py`, `test_osspa_db.py`, `test_status_visibility.py`, `reporting_db_show`, `extract_base_name`, `test_chat_live.py`, `pipeline.py`, `create_app`, `.list_retirement_ready_for_removal`, `.close`, `datetime`, `test_field_source_sync.py`, `Task 1: Database Schema and Methods`, `test_api_infrastructure.py`, `run_category`, `.complete_job`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `Database` (e.g. with `build_evidence_pack()` and `handle_help()`) actually correct?**
  _`Database` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _106 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Database Layer` be split into smaller, more focused modules?**
  _Cohesion score 0.028560250391236306 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Configuration` to `_make_request`, `cli.py`, `AdocRead`, `Analysis API Routes`, `Catalog API Routes`, `Admin API Routes`, `analyzer.py`, `Overlap Assessment`, `ops.py`, `app.py`, `router.py`, `structlog`, `schemas.py`, `routes/auth.py`, `seed_chat_fixtures`, `db/__init__.py`, `handlers.py`, `recommendations.py`, `config.py`, `test_retirement_pr_status.py`, `test_auth_security.py`, `run_osspa_sync`, `test_osspa_analysis.py`, `test_catalog_osspa_routes.py`, `middleware/auth.py`, `test_auth_routes.py`, `reporting_db_show`, `test_chat_live.py`, `pipeline.py`, `.is_admin`, `create_app`, `.close`, `test_vocabulary_admin.py`, `test_workers.py`, `route`, `test_chat_handlers.py`, `test_api_infrastructure.py`, `run_category`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Are the 67 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Should `Advisor Frontend` be split into smaller, more focused modules?**
  _Cohesion score 0.08973172987974098 - nodes in this community are weakly interconnected._