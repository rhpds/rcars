# Graph Report - rcars-advisory  (2026-10-15)

## Corpus Check
- 277 files · ~500,766 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 3206 nodes · 7590 edges · 187 communities (119 shown, 68 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 744 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8d1e9c77`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- middleware/auth.py
- Database
- registry.ts
- Portfolio Architecture Ingest Design Spec
- command
- devDependencies
- services/catalog.py
- database.py
- routes/catalog.py
- admin.py
- test_retirement_jira_events.py
- Infrastructure Catalog
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_agv_access.py
- Any
- time
- migrate_to_content_model.py
- app.py
- test_db.py
- RCARS × agv-retire: Automated Retirement Pipeline
- test_osspa_adoc.py
- run_category
- advisor.py
- config.py
- rationale.py
- schemas.py
- handlers.py
- App.tsx
- routes/auth.py
- ops.py
- rcars-login.py
- JobProgressRelay
- structlog
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- jira.py
- test_nonprod.py
- test_infrastructure.py
- parse_analysis_response
- test_osspa_csv.py
- reporting_sync.py
- PerformancePage.tsx
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- db/__init__.py
- test_auth_security.py
- test_chat_sessions_db.py
- generate_vocabulary_yaml
- HandsOnDriver
- Path
- run_osspa_sync
- vocabulary/__init__.py
- Retirement System
- parse_analysis_response
- analyze_architecture_item
- test_catalog_osspa_routes.py
- .complete_job
- settings.py
- test_osspa_db.py
- FastAPI
- test_reporting.py
- ContentAnalysisPage.tsx
- HistoryPage.tsx
- api.ts
- ECA Production Redesign Spec
- group
- analysis.py
- workload_scanner.py
- Reporting MCP Data Sync
- test_status_visibility.py
- TestValidation
- SyncPage.tsx
- app.py
- extract_base_name
- test_vocabulary.py
- TestGetNonprodBaseNames
- mcp_query
- test_retirement_pr_status.py
- test_sweep_github_only_cancellation_preserves_revert_until_jira_available
- pytest
- ArchitectureDriver
- _print
- _extrapolate_count
- ContentTypeDriver
- System Design Architecture Doc
- AdocRead
- _build_windowed_metrics
- seed_chat_fixtures
- TestVocabularyEndpoints
- scan
- osspa_sync.py
- Browse Page Redesign Plan
- API Authentication Design
- retirement_cleanup.py
- structlog
- test_auth_routes.py
- rcars-login.sh
- db
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- Candidate
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- Controlled Vocabulary Design
- unittest_mock
- analyze_showroom
- content_entities Table
- .create_schema
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- Advisor v2 — Content-Type Drivers
- scan.py
- TestTokenExchange
- analyzer.py
- scan_configs
- ensure_issue_event_comment
- option
- test_vocabulary_db.py
- post
- test_orphan_cleanup.py
- hashlib
- build_embedding_text
- _extrapolate_count
- status
- rate_limit.py
- _sync_nonprod_usage
- docker-entrypoint.sh
- Webhook Configuration Task
- build_infrastructure_embedding_text
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
- build_sandbox_summary
- Match Event Prompt Template
- TestNonprodIgnore
- seed_items
- Field Source Content
- Python Requirements Entry Point
- TestListNonprodItems
- TestUpsertNonprodUsage
- Task 1: Database Schema and Methods
- test_refresh_merged_notice_does_not_complete_open_removal

## God Nodes (most connected - your core abstractions)
1. `Database` - 270 edges
2. `Settings` - 158 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `run_retirement_sweep()` - 39 edges
6. `react` - 33 edges
7. `create_app()` - 32 edges
8. `run_osspa_sync()` - 31 edges
9. `ContentTypeDriver` - 31 edges
10. `normalize_analysis()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Data and Audit Trail` --references--> `status()`  [INFERRED]
  docs/architecture/retirement-system.md → src/api/rcars/cli.py
- `Global Constraints` --references--> `parse_analysis_response()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/analyzer.py
- `Open Questions / Risks` --references--> `build_retirement_description()`  [INFERRED]
  docs/superpowers/specs/agv-retire-integration.md → src/api/rcars/services/jira.py
- `Create` --references--> `ContentTypeDriver`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/drivers/base.py

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

## Communities (187 total, 68 thin omitted)

### Community 0 - "middleware/auth.py"
Cohesion: 0.05
Nodes (30): _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), invalidate_role_assignments_cache(), _log_auth_decision(), _parse_sa_allowlist(), require_admin() (+22 more)

### Community 2 - "registry.ts"
Cohesion: 0.13
Nodes (24): react, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock() (+16 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.21
Nodes (17): OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis, Nightly Maintenance Pipeline, OSSPA GitLab Repositories (+9 more)

### Community 4 - "command"
Cohesion: 0.13
Nodes (12): flag(), get_db(), infra_stats(), init_db(), note(), override_url(), refresh(), set_content_path() (+4 more)

### Community 5 - "devDependencies"
Cohesion: 0.04
Nodes (44): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, react-dom (+36 more)

### Community 6 - "services/catalog.py"
Cohesion: 0.09
Nodes (14): _apply_component_inheritance(), CatalogReader, _collect_bases(), component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata() (+6 more)

### Community 7 - "database.py"
Cohesion: 0.07
Nodes (19): _prefix_overlap(), _expand_vocab_aliases(), _extract_json(), _find_keyword_ties(), _parse_catalog_url(), pattern_check(), resolve_item(), route() (+11 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.13
Nodes (23): add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis(), get_catalog_item() (+15 more)

### Community 9 - "admin.py"
Cohesion: 0.08
Nodes (37): add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs(), list_role_assignments() (+29 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.08
Nodes (24): client(), comments(), event_time(), settings(), test_comment_missing_credentials_does_not_call_http(), unexpected(), test_database_no_jira_and_deleted_workflow_do_not_queue(), test_database_open_event_is_atomic_and_deduplicated() (+16 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.11
Nodes (32): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+24 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (23): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+15 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (3): derive_status(), TestDeriveStatus, TestStepOrder

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 18 - "time"
Cohesion: 0.18
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 19 - "migrate_to_content_model.py"
Cohesion: 0.13
Nodes (14): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+6 more)

### Community 20 - "app.py"
Cohesion: 0.05
Nodes (28): create_app(), RequestLoggingMiddleware, _parse_csv(), Settings, client(), test_sync_osspa_endpoint_enqueues_a_job(), client(), test_auth_me_unauthenticated() (+20 more)

### Community 21 - "test_db.py"
Cohesion: 0.09
Nodes (11): db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default(), test_filtered_catalog_pagination() (+3 more)

### Community 22 - "RCARS × agv-retire: Automated Retirement Pipeline"
Cohesion: 0.10
Nodes (18): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+10 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "run_category"
Cohesion: 0.13
Nodes (19): Modify, Task 3: Hands-on Driver, Task 6: Orchestrator + Pipeline Refactor, 1. Content-Type Drivers, 2. Orchestrator and Pipeline, 4. SSE Streaming, 6. Unified Serialization, Adding a New Content Type (+11 more)

### Community 25 - "advisor.py"
Cohesion: 0.13
Nodes (17): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+9 more)

### Community 26 - "config.py"
Cohesion: 0.12
Nodes (19): _call_anthropic(), _call_litemaas(), call_llm(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), _help_answer() (+11 more)

### Community 27 - "rationale.py"
Cohesion: 0.18
Nodes (9): Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, _primary_asset_type(), _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis(), _format_single_candidate(), generate_content_gaps() (+1 more)

### Community 28 - "schemas.py"
Cohesion: 0.10
Nodes (33): AgvPrResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse, CatalogStatsResponse, ContentPathResponse, ErrorDetail (+25 more)

### Community 29 - "handlers.py"
Cohesion: 0.14
Nodes (23): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+15 more)

### Community 30 - "App.tsx"
Cohesion: 0.08
Nodes (33): @patternfly/react-core, react-router-dom, App(), API_DOCS_URL, DbStatus, formatAge(), getInitials(), HelpMenu() (+25 more)

### Community 31 - "routes/auth.py"
Cohesion: 0.16
Nodes (17): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+9 more)

### Community 32 - "ops.py"
Cohesion: 0.12
Nodes (19): scan_all_collections(), publish_progress(), WorkerContext, run_chat_turn(), on_progress(), _progress_bridge(), _publish(), run_babylon_pipeline() (+11 more)

### Community 33 - "rcars-login.py"
Cohesion: 0.19
Nodes (8): migrate(), cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 34 - "JobProgressRelay"
Cohesion: 0.13
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 35 - "structlog"
Cohesion: 0.15
Nodes (8): QueryState, format_triage_candidates(), triage(), search(), _strip_embedding_filler(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_query_state_no_grouped_results()

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.10
Nodes (21): Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy (+13 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.13
Nodes (5): load_vocabulary(), _noise_variants(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 38 - "render_vocabulary_block"
Cohesion: 0.13
Nodes (4): build_analysis_prompt(), render_vocabulary_block(), TestPromptInjection, TestRenderVocabularyBlock

### Community 39 - "_generate_key"
Cohesion: 0.15
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "jira.py"
Cohesion: 0.10
Nodes (16): _base_name_from_content_id(), build_retirement_description(), _close_issue(), close_issue_wont_do(), create_retirement_ticket(), get_issue_status(), _issue_is_closed(), _jira_request() (+8 more)

### Community 44 - "parse_analysis_response"
Cohesion: 0.29
Nodes (10): parse_analysis_response(), test_dict(), test_empty_returns_none(), test_fenced_json(), test_list(), test_scalar_bool_returns_none(), test_scalar_int_returns_none(), test_scalar_string_returns_none() (+2 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (19): asset_type_tokens(), fetch_palist_csv(), OsspaSyncError, parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status() (+11 more)

### Community 46 - "reporting_sync.py"
Cohesion: 0.14
Nodes (10): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _mcp_call(), _merge_published_base_pairs() (+2 more)

### Community 47 - "PerformancePage.tsx"
Cohesion: 0.10
Nodes (36): fmt(), fmtRoi(), num(), scoreBg(), ScoreBreakdownPopover(), scoreColor(), ReplacementPicker(), stageBadgeClass (+28 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.10
Nodes (5): normalize_analysis(), _record_unknowns(), TestReviewBadgeUntouched, TestIgnoredTermsSuppression, TestNormalizeAnalysis

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "_expand_query_terms"
Cohesion: 0.09
Nodes (7): _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 51 - "db/__init__.py"
Cohesion: 0.16
Nodes (11): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats(), test_idempotent_upsert() (+3 more)

### Community 52 - "test_auth_security.py"
Cohesion: 0.11
Nodes (7): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders, TestUnauthenticatedAccess

### Community 53 - "test_chat_sessions_db.py"
Cohesion: 0.17
Nodes (8): get_session_context(), log_chat_turn(), next_turn_index(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership(), test_turn_index_increments()

### Community 54 - "generate_vocabulary_yaml"
Cohesion: 0.11
Nodes (8): _entries_to_dicts(), generate_vocabulary_yaml(), _header_comment(), _resolve_path(), clear_vocabulary_cache(), client(), TestGenerator, TestRoleGating

### Community 55 - "HandsOnDriver"
Cohesion: 0.21
Nodes (7): HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming(), test_hands_on_serialize_with_performance(), test_hands_on_triage_guidance()

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.37
Nodes (16): run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items(), test_missing_detail_page_marks_stale_and_skips() (+8 more)

### Community 58 - "vocabulary/__init__.py"
Cohesion: 0.13
Nodes (11): _as_tuple(), _build_lookups(), _parse_entries(), _validate(), squash_key(), VocabEntry, Vocabulary, VocabularyError (+3 more)

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
Cohesion: 0.17
Nodes (7): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 64 - "settings.py"
Cohesion: 0.13
Nodes (14): lifespan(), _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings (+6 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.18
Nodes (9): _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_upsert_osspa_item_never_overwrites_llm_owned_fields(), test_upsert_osspa_item_unretires_on_reappearance() (+1 more)

### Community 66 - "FastAPI"
Cohesion: 0.29
Nodes (4): health(), readiness(), HealthResponse, ReadinessResponse

### Community 67 - "test_reporting.py"
Cohesion: 0.12
Nodes (6): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), _recompute_windowed_scores(), TestComputePerformanceScore

### Community 68 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 69 - "HistoryPage.tsx"
Cohesion: 0.07
Nodes (40): Task 8: Frontend Refactor, 5. Frontend Card Rendering, Display Config Structure, BlockErrorBoundary, Props, State, resolveBlockRenderer(), ChatChip (+32 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (32): Task 4: Frontend Page, vitest, ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), findButton(), hooks (+24 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "group"
Cohesion: 0.13
Nodes (7): infra_group(), osspa_group(), overlap_candidates_cmd(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 73 - "analysis.py"
Cohesion: 0.12
Nodes (31): approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), _extract_base_name_from_content_id(), field_source_report(), get_workflow(), ignore_item() (+23 more)

### Community 74 - "workload_scanner.py"
Cohesion: 0.10
Nodes (12): generate_embedding(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products(), read_config_code(), read_role_code() (+4 more)

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

### Community 79 - "app.py"
Cohesion: 0.17
Nodes (4): get_recommendations(), RecommendationRequest, _run_low(), _run_medium()

### Community 81 - "test_vocabulary.py"
Cohesion: 0.17
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 83 - "mcp_query"
Cohesion: 0.20
Nodes (7): Field Source Content Report — Implementation Plan, Global Constraints, Task 3: API Endpoint, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, mcp_query(), TestMcpPagination

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.10
Nodes (24): run_retirement_sweep(), _sweep_context(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_manual_pr_creation_respects_cleanup_lock(), test_refresh_does_not_retire_unmerged_or_unknown_pr(), test_required_failed_cancel_is_excluded_from_removal_and_retried_by_sweep(), test_required_merged_revert_cannot_bypass_jira_failure(), test_required_success_retries_jira_after_retirement_without_pr() (+16 more)

### Community 85 - "test_sweep_github_only_cancellation_preserves_revert_until_jira_available"
Cohesion: 0.10
Nodes (9): test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), state(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), test_required_cancel_retains_workflow_on_jira_failure() (+1 more)

### Community 86 - "pytest"
Cohesion: 0.12
Nodes (20): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+12 more)

### Community 87 - "ArchitectureDriver"
Cohesion: 0.21
Nodes (7): ArchitectureDriver, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 88 - "_print"
Cohesion: 0.14
Nodes (6): _print(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 90 - "ContentTypeDriver"
Cohesion: 0.10
Nodes (12): ContentTypeDriver, get_driver(), get_drivers_for_types(), _init_drivers(), _register(), run_recommendation(), test_get_driver_architecture(), test_get_driver_lab() (+4 more)

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (18): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, architecture_analysis DB Table, RCARS Authentication Model, content_entities Universal Entity Registry Table, LLM Provider Routing (LiteMaaS / Vertex AI), Performance Scoring System (+10 more)

### Community 92 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 94 - "seed_chat_fixtures"
Cohesion: 0.16
Nodes (21): build_evidence_pack(), RouterOutput, Scope, resolve_and_verify(), _result_turns(), _turn_chips(), fake_embedding(), seed_chat_fixtures() (+13 more)

### Community 96 - "scan"
Cohesion: 0.16
Nodes (8): llm_provider_status(), scan(), _cli_propagate(), process_item(), workload_scan(), fetch_litemaas_models(), classify_scan_error(), regenerate_embeddings()

### Community 97 - "osspa_sync.py"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 98 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (4): Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "retirement_cleanup.py"
Cohesion: 0.25
Nodes (9): check_pr_statuses(), _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _pr_state() (+1 more)

### Community 101 - "structlog"
Cohesion: 0.21
Nodes (10): WorkerSettings, test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes(), test_worker_context_has_required_fields() (+2 more)

### Community 102 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (4): client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "db"
Cohesion: 0.18
Nodes (4): db(), test_database_explicit_test_schema_reset_includes_delivery_queue(), db(), create()

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.19
Nodes (8): Task 2: Reporting Sync Job, _build_field_source_sql(), run_field_source_sync(), FakeSettings, _mock_mcp_query(), test_field_source_sync_inserts_rows(), test_field_source_sync_no_mcp(), test_field_source_sync_replaces_on_rerun()

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.18
Nodes (14): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+6 more)

### Community 108 - "Candidate"
Cohesion: 0.06
Nodes (23): Content-Type Drivers Implementation Plan, Create, Delete, Execution Notes, File Map, Global Constraints, Review Focus, Task 1: Candidate Model Refactor (+15 more)

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 112 - "unittest_mock"
Cohesion: 0.15
Nodes (7): close_issue_done(), test_already_closed_issue_needs_no_transition(), test_closure_requires_a_terminal_result(), test_new_closure_requires_the_requested_resolution(), test_required_closure_selects_resolution_and_verifies_result(), request(), test_jira_close_reports_whether_it_transitioned()

### Community 113 - "analyze_showroom"
Cohesion: 0.15
Nodes (8): analyze_showroom(), build_module_embedding_text(), check_showroom_stale(), filter_boilerplate_files(), get_repo_head(), hash_showroom_content(), read_showroom_content(), TestAnalyzerNormalizesOnce

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".create_schema"
Cohesion: 0.08
Nodes (21): seed_infrastructure(), db(), db(), db(), db(), db(), db(), db() (+13 more)

### Community 120 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.18
Nodes (10): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Goals, Non-Goals, Parallel Pipeline Instances (+2 more)

### Community 121 - "scan.py"
Cohesion: 0.36
Nodes (3): _propagate_to_sibling(), run_analysis(), _sanitize_format_suitability()

### Community 123 - "analyzer.py"
Cohesion: 0.14
Nodes (6): _get_embedding_client(), _is_github_throttle(), _parse_nav_includes(), _resolve_ref_from_lookup(), _run_git_with_retry(), truncate_content()

### Community 124 - "scan_configs"
Cohesion: 0.22
Nodes (4): clone_showroom(), ls_remote_sha(), scan_collection(), scan_configs()

### Community 126 - "ensure_issue_event_comment"
Cohesion: 0.20
Nodes (8): ensure_issue_event_comment(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_failed_lookup_does_not_post(), test_comment_malformed_page_does_not_prove_absence(), test_comment_unknown_post_outcome_recovers_remote_event(), test_comment_uses_adf_and_event_property(), test_delivery_survives_workflow_deletion_and_runs_off_loop()

### Community 127 - "option"
Cohesion: 0.18
Nodes (5): cli(), osspa_sync_cmd(), serve(), vocab_stage_rescan(), vocab_unknowns()

### Community 128 - "test_vocabulary_db.py"
Cohesion: 0.08
Nodes (8): _noop(), _settings(), test_live_item_facts_turn(), test_live_out_of_scope(), TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestUnknownTermsSchema

### Community 129 - "post"
Cohesion: 0.20
Nodes (8): analyze_single(), check_stale(), overlap_assess(), rescan_all(), retirement_sweep(), start_scan(), resolve_refs_to_shas(), sha_dedup_scan_items()

### Community 130 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 131 - "hashlib"
Cohesion: 0.29
Nodes (4): build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events()

### Community 134 - "status"
Cohesion: 0.33
Nodes (5): 3. Candidate Model, Candidate Dataclass, `content_entities` (shared table — all types), Source-specific tables, status()

### Community 136 - "_sync_nonprod_usage"
Cohesion: 0.33
Nodes (3): _build_nonprod_provisions_sql(), _sync_nonprod_usage(), TestSyncNonprodUsage

### Community 139 - "build_infrastructure_embedding_text"
Cohesion: 0.60
Nodes (3): build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

### Community 143 - "retirement-system.md"
Cohesion: 0.18
Nodes (19): Token Usage Tracking (5 Operation Types), CLI Admin Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference, Content Overlap Detection, Cosine Similarity for Overlap (+11 more)

### Community 174 - "Field Source Content"
Cohesion: 0.40
Nodes (5): API, Data Import, Data Source, Field Source Content, Frontend

## Knowledge Gaps
- **105 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1119 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **68 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `test_vocabulary_db.py`, `command`, `database.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `Any`, `app.py`, `test_db.py`, `run_category`, `config.py`, `rationale.py`, `handlers.py`, `ops.py`, `rcars-login.py`, `structlog`, `_generate_key`, `test_nonprod.py`, `test_infrastructure.py`, `TestNonprodIgnore`, `.get_channel_metrics_map`, `.list_nonprod_items`, `db/__init__.py`, `.list_retirement_items`, `.prune_expired_api_keys`, `.update_retirement_cleanup`, `test_chat_sessions_db.py`, `TestListNonprodItems`, `Task 1: Database Schema and Methods`, `TestUpsertNonprodUsage`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `.complete_job`, `settings.py`, `test_osspa_db.py`, `workload_scanner.py`, `test_status_visibility.py`, `extract_base_name`, `TestGetNonprodBaseNames`, `test_retirement_pr_status.py`, `_print`, `seed_chat_fixtures`, `db`, `test_field_source_sync.py`, `.create_schema`, `scan_configs`, `test_field_source_db.py`, `option`?**
  _High betweenness centrality (0.163) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `Database` (e.g. with `build_evidence_pack()` and `handle_help()`) actually correct?**
  _`Database` has 46 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _105 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `middleware/auth.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05282842449742871 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `app.py` to `middleware/auth.py`, `post`, `test_vocabulary_db.py`, `command`, `database.py`, `routes/catalog.py`, `admin.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `run_category`, `advisor.py`, `config.py`, `handlers.py`, `routes/auth.py`, `ops.py`, `rcars-login.py`, `JobProgressRelay`, `structlog`, `test_auth_security.py`, `generate_vocabulary_yaml`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `settings.py`, `group`, `analysis.py`, `workload_scanner.py`, `app.py`, `test_retirement_pr_status.py`, `_print`, `AdocRead`, `seed_chat_fixtures`, `scan`, `structlog`, `test_auth_routes.py`, `analyzer.py`, `option`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Are the 64 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 64 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.022206638616175785 - nodes in this community are weakly interconnected._