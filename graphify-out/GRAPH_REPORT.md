# Graph Report - rcars-advisory  (2026-11-04)

## Corpus Check
- 310 files · ~537,974 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 3859 nodes · 9482 edges · 190 communities (135 shown, 55 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 974 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `21d2cc2d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _FakeResponse
- Database
- registry.ts
- Portfolio Architecture Ingest Design Spec
- handlers.py
- devDependencies
- test_test_content_exclusion.py
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
- Content Owner Model for Virtual CIs — Design
- workload_scanner.py
- test_catalog_labels.py
- routes/auth.py
- test_db.py
- test_content_owner.py
- test_osspa_adoc.py
- react
- Settings
- LLMResult
- pytest
- schemas.py
- seed
- App.tsx
- ops.py
- sync_opl_vocabulary.py
- advisor.py
- JobProgressRelay
- middleware/auth.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- test_jira_service.py
- orchestrator.py
- handlers.py
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
- generate_vocabulary_yaml
- Task 3: Return labels from the three analysis endpoints
- Path
- run_osspa_sync
- loader.py
- Retirement System
- parse_analysis_response
- analyze_architecture_item
- test_catalog_osspa_routes.py
- effective_showroom_source
- Design
- test_osspa_db.py
- HandsOnDriver
- reporting_sync.py
- router.py
- test_sweep_github_only_cancellation_preserves_revert_until_jira_available
- api.ts
- ECA Production Redesign Spec
- TestVocabularyEndpoints
- migrate_to_content_model.py
- analyzer.py
- Reporting MCP Data Sync
- test_status_visibility.py
- TestValidation
- SyncPage.tsx
- cli.py
- test_auth_routes.py
- services/catalog.py
- pipeline.py
- test_nonprod.py
- test_retirement_pr_status.py
- jira.py
- services/__init__.py
- test_drivers.py
- test_llm_routing.py
- build_retirement_description
- Global Constraints
- System Design Architecture Doc
- AdocRead
- test_showroom_scan.py
- seed_chat_fixtures
- Showroom analysis isolation
- Scan Pipeline
- osspa_sync.py
- Browse Page Redesign Plan
- API Authentication Design
- test_showroom_source.py
- Candidate
- _format_single_candidate
- rcars-login.sh
- ._set_showroom_override
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- search
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- Controlled Vocabulary Design
- app.py
- test_chat_live.py
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
- settings.py
- test_refresh_merged_notice_does_not_complete_open_removal
- ArchitectureDriver
- Decisions
- test_showroom_rebuild.py
- group
- Any
- _sync_nonprod_usage
- test_chat_handlers.py
- _window_start
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
- ContentAnalysisPage.tsx
- Match Event Prompt Template
- extract_base_name
- Review Focus
- test_showroom_reuse.py
- test_vocabulary.py
- Python Requirements Entry Point
- _build_windowed_metrics
- hashlib
- _reset_token_cache
- TestTokenExchange
- _owner_scope_ids
- mcp_query
- TestGetNonprodBaseNames
- Field Source Content
- test_vocabulary_db.py
- test_start_retirement_holds_lock_while_creating_ticket
- scan_candidates

## God Nodes (most connected - your core abstractions)
1. `Database` - 302 edges
2. `Settings` - 176 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `seed()` - 46 edges
6. `scan_babylon_item()` - 44 edges
7. `run_retirement_sweep()` - 40 edges
8. `ResolvedShowroom` - 37 edges
9. `create_app()` - 36 edges
10. `react` - 35 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Data and Audit Trail` --references--> `status()`  [INFERRED]
  docs/architecture/retirement-system.md → src/api/rcars/cli.py
- ``content_entities` (shared table — all types)` --references--> `status()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/cli.py
- `Global Constraints` --references--> `parse_analysis_response()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/analyzer.py
- `Non-goals` --references--> `extract_catalog_item()`  [INFERRED]
  docs/superpowers/specs/2026-10-28-platform-tdp-filters-design.md → src/api/rcars/services/catalog.py

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

## Communities (190 total, 55 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.10
Nodes (16): _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen() (+8 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (4): Task 1: Database Schema and Methods, Database, _do(), test_advisory_lock_is_not_reentrant_across_sessions()

### Community 2 - "registry.ts"
Cohesion: 0.14
Nodes (21): InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps (+13 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.19
Nodes (19): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis (+11 more)

### Community 4 - "handlers.py"
Cohesion: 0.18
Nodes (13): Clarify, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs, PerformanceArgs, RecommendArgs (+5 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (43): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, @types/react (+35 more)

### Community 6 - "test_test_content_exclusion.py"
Cohesion: 0.12
Nodes (15): resolve_showroom_source(), unresolved(), walk(), legacy_test_item(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(), test_cached_overlap_cannot_bypass_test_content_exclusion(), test_existing_test_vectors_never_enter_content_retrieval() (+7 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.12
Nodes (13): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), seed_items(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats() (+5 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.11
Nodes (31): Task 9: Curator edits on a stub write the owner's analysis row, add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+23 more)

### Community 9 - "admin.py"
Cohesion: 0.13
Nodes (25): add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs(), list_role_assignments() (+17 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.07
Nodes (29): client(), comments(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_malformed_page_does_not_prove_absence(), test_comment_missing_credentials_does_not_call_http() (+21 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (38): Review Focus, Task 5: Shared frontend helpers and checkbox filter group, Task 7: Browse UI (provisional style), Task 8: Run locally, check, and prepare the PR, getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect() (+30 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (23): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+15 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (4): derive_status(), retirement_label(), TestDeriveStatus, TestStepOrder

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_agv_access.py"
Cohesion: 0.06
Nodes (70): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+62 more)

### Community 17 - "Content Owner Model for Virtual CIs — Design"
Cohesion: 0.17
Nodes (10): Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Rollout (+2 more)

### Community 18 - "workload_scanner.py"
Cohesion: 0.06
Nodes (22): build_infrastructure_embedding_text(), generate_embedding(), _get_embedding_client(), ls_remote_sha(), regenerate_embeddings(), _resolve_ref_from_lookup(), analyze_config(), analyze_role() (+14 more)

### Community 19 - "test_catalog_labels.py"
Cohesion: 0.07
Nodes (19): Task 2: Union labels per base name, Task 4: Browse server-side filters and facets, _seed_label_count_items(), test_facets_platforms_and_tdps(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value() (+11 more)

### Community 20 - "routes/auth.py"
Cohesion: 0.17
Nodes (16): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+8 more)

### Community 21 - "test_db.py"
Cohesion: 0.08
Nodes (11): db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default(), test_filtered_catalog_pagination() (+3 more)

### Community 22 - "test_content_owner.py"
Cohesion: 0.14
Nodes (30): analyze_single(), reconcile_pure_stubs(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner(), test_browse_difficulty_filter_finds_a_stub_by_its_mirrored_card(), test_browse_shows_the_owner_review_flags_on_a_stub() (+22 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.10
Nodes (24): Pure stub, compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough() (+16 more)

### Community 24 - "react"
Cohesion: 0.07
Nodes (43): Task 8: Frontend Refactor, 5. Frontend Card Rendering, Display Config Structure, react, BlockErrorBoundary, Props, State, CATEGORY_LABELS (+35 more)

### Community 25 - "Settings"
Cohesion: 0.09
Nodes (23): fetch_litemaas_models(), _parse_csv(), Settings, _FakeModels, _litemaas_settings(), _patch_litemaas_client(), test_admin_check(), test_call_llm_propagates_litemaas_error() (+15 more)

### Community 26 - "LLMResult"
Cohesion: 0.23
Nodes (12): _call_litemaas_inner(), LLMResult, _extract_json(), route(), llm(), _fake(), llm_call(), test_call_error_falls_back() (+4 more)

### Community 27 - "pytest"
Cohesion: 0.18
Nodes (7): Envelope, test_envelope_round_trip(), test_intent_enum_closed(), test_performance_args_window_closed(), test_scope_shapes(), settings(), test_routing_golden()

### Community 28 - "schemas.py"
Cohesion: 0.06
Nodes (59): field_source_report(), health(), readiness(), AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload (+51 more)

### Community 29 - "seed"
Cohesion: 0.13
Nodes (29): Task 2: Persist source provenance and enforce scoped analysis reuse, Task 6: Advisor shows the stub in place of its owner, db(), add_stub(), search(), test_ci_reference_to_a_stub_resolves_through_its_owner(), test_dev_hit_promotes_to_the_prod_counterpart_stub(), test_each_owner_promotes_to_its_own_stub() (+21 more)

### Community 30 - "App.tsx"
Cohesion: 0.08
Nodes (37): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), API_DOCS_URL (+29 more)

### Community 31 - "ops.py"
Cohesion: 0.06
Nodes (31): build_sandbox_summary(), publish_progress(), WorkerContext, run_chat_turn(), on_progress(), _progress_bridge(), _publish(), run_babylon_pipeline() (+23 more)

### Community 32 - "sync_opl_vocabulary.py"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 33 - "advisor.py"
Cohesion: 0.10
Nodes (15): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+7 more)

### Community 34 - "JobProgressRelay"
Cohesion: 0.09
Nodes (24): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Frontend Progress Display, Goals, Non-Goals (+16 more)

### Community 35 - "middleware/auth.py"
Cohesion: 0.05
Nodes (30): _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), invalidate_role_assignments_cache(), _log_auth_decision(), _parse_sa_allowlist(), require_admin() (+22 more)

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

### Community 41 - "test_jira_service.py"
Cohesion: 0.18
Nodes (19): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+11 more)

### Community 42 - "orchestrator.py"
Cohesion: 0.22
Nodes (10): build_scaffold(), compose_answer(), _strip_formatting(), _help_answer(), process_turn(), _scope_echo(), followup_chips(), test_answer_failure_degrades_to_scaffold() (+2 more)

### Community 43 - "handlers.py"
Cohesion: 0.12
Nodes (18): get_item_workloads(), get_performance_scores(), _prefix_overlap(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+10 more)

### Community 44 - "test_analyzer.py"
Cohesion: 0.10
Nodes (26): check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), hash_showroom_content(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content() (+18 more)

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
Cohesion: 0.15
Nodes (28): approve_item(), ApproveRequest, _base_name_to_content_id(), check_stale(), get_workflow(), ignore_item(), link_jira(), LinkJiraRequest (+20 more)

### Community 52 - "test_auth_security.py"
Cohesion: 0.11
Nodes (7): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders, TestUnauthenticatedAccess

### Community 53 - "chat_sessions.py"
Cohesion: 0.19
Nodes (8): get_session_context(), log_chat_turn(), next_turn_index(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership(), test_turn_index_increments()

### Community 54 - "generate_vocabulary_yaml"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "Task 3: Return labels from the three analysis endpoints"
Cohesion: 0.13
Nodes (10): Task 3: Return labels from the three analysis endpoints, _extract_base_name_from_content_id(), nonprod_dashboard(), performance_dashboard(), retirement_dashboard(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels() (+2 more)

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.37
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
Cohesion: 0.14
Nodes (7): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "effective_showroom_source"
Cohesion: 0.13
Nodes (17): Content Owner Model Implementation Plan, Global Constraints, Rollout, Root cause, _authorized_promotion(), eligible(), _eligible_stub(), _resolve_ci_references() (+9 more)

### Community 64 - "Design"
Cohesion: 0.20
Nodes (10): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 6. Unified Serialization, Adding a New Content Type, Candidate Dataclass, `content_entities` (shared table — all types), Design (+2 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.23
Nodes (9): _row(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override(), test_upsert_osspa_item_never_overwrites_llm_owned_fields(), test_upsert_osspa_item_unretires_on_reappearance() (+1 more)

### Community 66 - "HandsOnDriver"
Cohesion: 0.17
Nodes (10): Task 3: Hands-on Driver, What Moves Into Drivers, _extract_duration_target(), HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming() (+2 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.17
Nodes (10): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs(), _percentile_rank() (+2 more)

### Community 68 - "router.py"
Cohesion: 0.19
Nodes (18): Chip, RouterOutput, Scope, _expand_vocab_aliases(), _parse_catalog_url(), pattern_check(), resolve_and_verify(), _result_turns() (+10 more)

### Community 69 - "test_sweep_github_only_cancellation_preserves_revert_until_jira_available"
Cohesion: 0.09
Nodes (11): test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), test_required_cancel_retains_workflow_on_jira_failure(), test_retired_items_cannot_be_cancelled() (+3 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (27): Task 5: Routing and Sidebar, findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName() (+19 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 73 - "migrate_to_content_model.py"
Cohesion: 0.07
Nodes (22): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+14 more)

### Community 74 - "analyzer.py"
Cohesion: 0.09
Nodes (21): analysis_context_hash(), analysis_from_row(), analyze_showroom(), build_analysis_prompt(), build_module_embedding_text(), _canonical_content(), compute_analysis_context_hash(), compute_analysis_input_hash() (+13 more)

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (6): Retirement Analysis Integration Plan, Retirement Workflow Actions Plan, Generalized Content Model Plan, Overlap Analysis Redesign Plan, Advisor Multi-Intent Chat Plan, Performance Page Plan

### Community 76 - "test_status_visibility.py"
Cohesion: 0.17
Nodes (11): _arch(), _seed_nonprod(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators(), test_nonprod_list_hides_item_with_finished_retirement_workflow() (+3 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 79 - "cli.py"
Cohesion: 0.06
Nodes (26): cli(), flag(), get_db(), infra_stats(), init_db(), note(), osspa_sync_cmd(), overlap_candidates_cmd() (+18 more)

### Community 80 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (4): client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 81 - "services/catalog.py"
Cohesion: 0.15
Nodes (10): Global Constraints, component_item_to_ci_name(), _content_fields(), extract_showroom_url(), _get_label(), _resolve_template_var(), _source_node(), ContentDeclaration (+2 more)

### Community 82 - "pipeline.py"
Cohesion: 0.11
Nodes (19): Modify, Task 6: Orchestrator + Pipeline Refactor, Task 7: Caller Integration + Cleanup, 2. Orchestrator and Pipeline, What Gets Deleted, call_llm(), registered_content_types(), QueryState (+11 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.08
Nodes (11): _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestNonprodWindows (+3 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.10
Nodes (26): run_retirement_sweep(), _sweep_context(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancellation_does_not_mark_concurrently_retired_item(), test_manual_pr_creation_respects_cleanup_lock(), test_refresh_does_not_retire_unmerged_or_unknown_pr(), test_required_failed_cancel_is_excluded_from_removal_and_retried_by_sweep(), test_required_merged_revert_cannot_bypass_jira_failure() (+18 more)

### Community 85 - "jira.py"
Cohesion: 0.13
Nodes (10): _close_issue(), close_issue_done(), _fetch_oauth_token(), _get_access_token(), get_issue_status(), _issue_is_closed(), _jira_request(), _move_to_in_progress() (+2 more)

### Community 86 - "services/__init__.py"
Cohesion: 0.19
Nodes (6): close_issue_wont_do(), test_already_closed_issue_needs_no_transition(), test_closure_requires_a_terminal_result(), test_required_closure_selects_resolution_and_verifies_result(), request(), test_jira_close_reports_whether_it_transitioned()

### Community 87 - "test_drivers.py"
Cohesion: 0.14
Nodes (14): get_driver(), get_drivers_for_types(), format_triage_candidates(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_get_driver_architecture() (+6 more)

### Community 88 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.09
Nodes (19): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+11 more)

### Community 90 - "Global Constraints"
Cohesion: 0.22
Nodes (7): Field Source Content Report — Implementation Plan, Global Constraints, Task 2: Reporting Sync Job, Task 3: API Endpoint, Task 4: Frontend Page, Task 6: End-to-End Verification, _build_field_source_sql()

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.20
Nodes (16): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, LLM Provider Routing (LiteMaaS / Vertex AI), Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API (+8 more)

### Community 92 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.08
Nodes (44): Task 4: Unify scan persistence and remove cross-item fan-out, Task 5: Mirror card fields when an owner scan saves, classify_scan_error(), InvalidShowroomRef, order_for_reuse(), reuse_key_from_signature(), showroom_reuse_key(), reuse_lock_id() (+36 more)

### Community 94 - "seed_chat_fixtures"
Cohesion: 0.14
Nodes (16): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+8 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.20
Nodes (10): Content Overlap Detection, Cosine Similarity for Overlap, Score Bands, Phase 1 Vector Search, Scan Pipeline, Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify (+2 more)

### Community 97 - "osspa_sync.py"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 98 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (4): Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "test_showroom_source.py"
Cohesion: 0.21
Nodes (25): Task 1: Resolve content sources with explicit ownership, Task 1: `content_owner` helper, ComponentLink, content_owner(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage() (+17 more)

### Community 101 - "Candidate"
Cohesion: 0.14
Nodes (10): _apply_component_inheritance(), _collect_bases(), _run_catalog_second_pass(), test_candidate_tier_defaults(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published(), test_query_state_defaults() (+2 more)

### Community 102 - "_format_single_candidate"
Cohesion: 0.20
Nodes (7): Content-Type Drivers Implementation Plan, Execution Notes, Global Constraints, Review Focus, _call_rationale_single(), _format_single_candidate(), test_format_single_candidate_handles_architecture()

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.24
Nodes (6): run_field_source_sync(), FakeSettings, _mock_mcp_query(), test_field_source_sync_inserts_rows(), test_field_source_sync_no_mcp(), test_field_source_sync_replaces_on_rerun()

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (12): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+4 more)

### Community 108 - "search"
Cohesion: 0.29
Nodes (3): search(), _strip_embedding_filler(), test_candidate_similarity_pct()

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 112 - "app.py"
Cohesion: 0.04
Nodes (23): create_app(), lifespan(), _get_user_key(), RequestLoggingMiddleware, client(), client(), test_sync_osspa_endpoint_enqueues_a_job(), client() (+15 more)

### Community 113 - "test_chat_live.py"
Cohesion: 0.36
Nodes (4): _noop(), _settings(), test_live_item_facts_turn(), test_live_out_of_scope()

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.05
Nodes (27): migrate(), db(), seed_infrastructure(), db(), db(), db(), db(), db() (+19 more)

### Community 121 - "StatusPage.tsx"
Cohesion: 0.22
Nodes (10): react-dom, vitest, LlmProviderCard(), LlmProviderStatus, LlmUse, status, USE_LABELS, CatalogStatus (+2 more)

### Community 123 - "ContentTypeDriver"
Cohesion: 0.10
Nodes (3): ContentTypeDriver, _init_drivers(), _register()

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.15
Nodes (15): cancel_workflow(), check_pr_statuses(), _sweep(), _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr() (+7 more)

### Community 126 - "settings.py"
Cohesion: 0.21
Nodes (10): _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), recommend_startup(), scan_startup(), _startup() (+2 more)

### Community 128 - "ArchitectureDriver"
Cohesion: 0.15
Nodes (16): Create, Delete, File Map, Task 1: Candidate Model Refactor, Task 2: Driver Base Class + Registry, Task 4: Architecture Driver, Task 5: Triage + Rationale Driver Hooks, ArchitectureDriver (+8 more)

### Community 129 - "Decisions"
Cohesion: 0.09
Nodes (10): Platform and TDP Filters Implementation Plan, Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design (+2 more)

### Community 130 - "test_showroom_rebuild.py"
Cohesion: 0.10
Nodes (19): Execution handoff, File map and verification conventions, Global Constraints, Review Focus, Self-review, Showroom Analysis Isolation Implementation Plan, Task 6: Add a narrowly scoped reset and verify the full rebuild contract, ResolvedShowroom (+11 more)

### Community 131 - "group"
Cohesion: 0.15
Nodes (6): infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 132 - "Any"
Cohesion: 0.07
Nodes (4): Task 5: Keep recommendation identities within authorized relationships, Task 3: Scan skips pure stubs, Task 7: `get_display_analysis` and the three runtime read sites, Scan

### Community 133 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 134 - "test_chat_handlers.py"
Cohesion: 0.47
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 139 - "CatalogReader"
Cohesion: 0.09
Nodes (15): Task 1: Read and store Platform/TDP labels, CatalogReader, collect(), load(), extract_base_ci_refs(), extract_catalog_item(), extract_infrastructure_metadata(), is_agnosticd_v2() (+7 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.20
Nodes (16): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+8 more)

### Community 169 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 173 - "Review Focus"
Cohesion: 0.40
Nodes (4): Review Focus, Task 2: Database read and write methods for stubs, Task 8: Browse detail shows the owner's analysis and names the owner, ItemDetail

### Community 174 - "test_showroom_reuse.py"
Cohesion: 0.09
Nodes (21): Data Import, Task 3: Fetch the exact source and reject non-content inputs, git_repo(), git(), MemoryArtifacts, prime(), scan(), run() (+13 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 180 - "hashlib"
Cohesion: 0.15
Nodes (9): ensure_issue_event_comment(), jira_auth_configured(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response() (+1 more)

### Community 186 - "mcp_query"
Cohesion: 0.22
Nodes (4): _mcp_call(), mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 190 - "Field Source Content"
Cohesion: 0.50
Nodes (4): API, Data Source, Field Source Content, Frontend

### Community 191 - "test_vocabulary_db.py"
Cohesion: 0.10
Nodes (5): TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched, TestUnknownTermsSchema

### Community 195 - "test_start_retirement_holds_lock_while_creating_ticket"
Cohesion: 0.50
Nodes (4): _approved_unstarted(), test_start_retirement_holds_lock_while_creating_ticket(), fake_create(), test_start_retirement_respects_workflow_lock()

### Community 198 - "scan_candidates"
Cohesion: 0.38
Nodes (4): Task 4: Reconcile stub artifacts at every scan entry point, rescan_all(), start_scan(), scan_candidates()

## Knowledge Gaps
- **105 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1299 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **55 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `Decisions`, `test_showroom_rebuild.py`, `Any`, `db/__init__.py`, `test_field_source_db.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `derive_status`, `Content Owner Model for Virtual CIs — Design`, `workload_scanner.py`, `test_catalog_labels.py`, `test_db.py`, `Settings`, `seed`, `ops.py`, `_generate_key`, `orchestrator.py`, `handlers.py`, `extract_base_name`, `Review Focus`, `chat_sessions.py`, `run_osspa_sync`, `TestGetNonprodBaseNames`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `effective_showroom_source`, `test_vocabulary_db.py`, `test_osspa_db.py`, `test_start_retirement_holds_lock_while_creating_ticket`, `router.py`, `scan_candidates`, `migrate_to_content_model.py`, `test_status_visibility.py`, `cli.py`, `pipeline.py`, `test_nonprod.py`, `test_retirement_pr_status.py`, `seed_chat_fixtures`, `._set_showroom_override`, `test_field_source_sync.py`, `search`, `app.py`, `test_chat_live.py`, `.close`, `settings.py`?**
  _High betweenness centrality (0.171) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `Database` (e.g. with `Settings` and `AnalysisSignature`) actually correct?**
  _`Database` has 52 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _105 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.10344827586206896 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `Database`, `Any`, `test_chat_handlers.py`, `test_test_content_exclusion.py`, `routes/catalog.py`, `admin.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `workload_scanner.py`, `routes/auth.py`, `LLMResult`, `pytest`, `seed`, `ops.py`, `advisor.py`, `middleware/auth.py`, `orchestrator.py`, `handlers.py`, `analysis.py`, `test_auth_security.py`, `Task 3: Return labels from the three analysis endpoints`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `effective_showroom_source`, `router.py`, `migrate_to_content_model.py`, `analyzer.py`, `cli.py`, `test_auth_routes.py`, `pipeline.py`, `test_retirement_pr_status.py`, `test_llm_routing.py`, `AdocRead`, `test_showroom_scan.py`, `seed_chat_fixtures`, `app.py`, `test_chat_live.py`, `.close`, `settings.py`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 69 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 69 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.02147124719940254 - nodes in this community are weakly interconnected._