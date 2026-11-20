# Graph Report - rhdpcd-2265  (2026-11-20)

## Corpus Check
- 330 files · ~548,190 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4207 nodes · 10511 edges · 220 communities (156 shown, 64 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 1303 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f2cd4c78`
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
- common.yml
- settings.py
- workload_scanner.py
- with
- routes/auth.py
- test_db.py
- test_content_owner.py
- test_osspa_adoc.py
- react
- Settings
- re
- test_showroom_source.py
- schemas.py
- seed
- App.tsx
- structlog
- test_agv_access.py
- Request
- JobProgressRelay
- ContentAnalysisPage.tsx
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- json
- compilerOptions
- test_jira_service.py
- app.py
- .get_content_entity
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
- osspa_sync.py
- run_osspa_sync
- loader.py
- Retirement System
- parse_analysis_response
- pytest
- test_catalog_osspa_routes.py
- SyncPage.tsx
- build_retirement_description
- patch
- HandsOnDriver
- reporting_sync.py
- pytest
- test_sweep_github_only_cancellation_preserves_revert_until_jira_available
- api.ts
- ECA Production Redesign Spec
- pipeline.py
- migrate_to_content_model.py
- analyzer.py
- Reporting MCP Data Sync
- sync_opl_vocabulary.py
- TestValidation
- ._set_showroom_override
- command
- run_category
- test_test_content_exclusion.py
- ._artifact_connection
- test_nonprod.py
- test_retirement_pr_status.py
- jira.py
- middleware/auth.py
- _print
- ArchitectureDriver
- build_retirement_description
- publish_progress
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
- vocabulary.yaml
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- Advisor v2 — Content-Type Drivers
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- pre_tasks
- create_app
- .create_job
- content_entities Table
- .close
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- test_reporting.py
- test_retirement_edit.py
- build_embedding_text
- ContentTypeDriver
- test_orphan_cleanup.py
- ops.py
- Content Owner Model for Virtual CIs — Design
- option
- effective_analysis_source
- block
- post_tasks
- action_verbs
- vector_search.py
- _sync_nonprod_usage
- handlers.py
- TestStepOrder
- _jira_event_messages
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
- content_owner
- Match Event Prompt Template
- test_catalog_labels.py
- close_issue_wont_do
- test_showroom_reuse.py
- test_vocabulary.py
- Python Requirements Entry Point
- MemoryArtifacts
- ensure_issue_event_comment
- Python Dependency Manifest (requirements.lock)
- deploy.yml
- tasks
- rationale.py
- pathlib
- mcp_query
- readiness
- TestGetNonprodBaseNames
- TestBuildWindowedMetrics
- Field Source Content
- .get_unknown_terms
- Design
- _parse_sa_allowlist
- test_start_retirement_holds_lock_while_creating_ticket
- workload_scan
- _window_start
- BaseModel
- test_infrastructure.py
- ignored_terms
- Global Constraints
- Platform and Technical Decision Point filters — design
- TestPromptInjection
- performance_dashboard
- OsspaSyncError
- scan
- _reset_token_cache
- test_drivers.py
- content_modes
- build_infrastructure_embedding_text
- TestNonprodSchema
- kubernetes.core.k8s_exec
- collections
- solutions
- ansible.builtin.assert
- test_lifecycle_cancellation_closures_and_outcome_survive_comment_failure
- test_edit_rejects_name_without_replacement_ci
- test_edit_rejected_for_retired_item
- test_edit_rejected_while_cancellation_pending

## God Nodes (most connected - your core abstractions)
1. `Database` - 308 edges
2. `Settings` - 184 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `seed()` - 46 edges
6. `scan_babylon_item()` - 45 edges
7. `create_app()` - 43 edges
8. `run_retirement_sweep()` - 40 edges
9. `ResolvedShowroom` - 39 edges
10. `content_owner()` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Global Constraints` --references--> `parse_analysis_response()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/analyzer.py
- `Non-goals` --references--> `extract_catalog_item()`  [INFERRED]
  docs/superpowers/specs/2026-10-28-platform-tdp-filters-design.md → src/api/rcars/services/catalog.py
- `Task 1: Candidate Model Refactor` --references--> `Candidate`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/models.py
- `Review Focus` --references--> `run_category()`  [INFERRED]
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

## Communities (220 total, 64 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.10
Nodes (16): _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen() (+8 more)

### Community 1 - "Database"
Cohesion: 0.03
Nodes (12): Database, _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey, test_advisor_session() (+4 more)

### Community 2 - "registry.ts"
Cohesion: 0.12
Nodes (25): react, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock() (+17 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.17
Nodes (19): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis, OSSPA GitLab Repositories (+11 more)

### Community 4 - "test_description_analysis.py"
Cohesion: 0.12
Nodes (47): Task 2: `Database.set_analysis_source()` setter, Task 4: Candidate selection, Task 7: API endpoint + detail fields, AnalysisSourceRequest, set_analysis_source(), analyze_description(), add_description_item(), add_item() (+39 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (53): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, react-dom (+45 more)

### Community 6 - "cli.py"
Cohesion: 0.15
Nodes (7): group, infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 7 - "db/__init__.py"
Cohesion: 0.12
Nodes (13): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), seed_items(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats() (+5 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.12
Nodes (28): add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis(), get_catalog_item() (+20 more)

### Community 9 - "admin.py"
Cohesion: 0.13
Nodes (24): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+16 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.09
Nodes (33): deliver_pending_events(), client(), comments(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_malformed_page_does_not_prove_absence() (+25 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): Task 7: Browse UI (provisional style), getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline() (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (24): assess_overlap(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector(), _seed_overlap_pair() (+16 more)

### Community 14 - "derive_status"
Cohesion: 0.09
Nodes (3): derive_status(), retirement_label(), TestDeriveStatus

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "common.yml"
Cohesion: 0.03
Nodes (58): admin_emails, api_cpu_limit, api_cpu_request, api_memory_limit, api_memory_request, api_replicas, app_name, app_port (+50 more)

### Community 17 - "settings.py"
Cohesion: 0.09
Nodes (21): WorkerContext, run_nightly_pipeline(), run_osspa_pipeline(), run_retirement_sweep_job(), cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url() (+13 more)

### Community 18 - "workload_scanner.py"
Cohesion: 0.09
Nodes (14): ls_remote_sha(), regenerate_embeddings(), _resolve_ref_from_lookup(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products() (+6 more)

### Community 19 - "with"
Cohesion: 0.06
Nodes (33): runs-on, steps, concurrency, cancel-in-progress, environment, needs, runs-on, steps (+25 more)

### Community 20 - "routes/auth.py"
Cohesion: 0.26
Nodes (10): invalidate_api_key_cache(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token(), _user_max_role() (+2 more)

### Community 21 - "test_db.py"
Cohesion: 0.06
Nodes (41): Task 4: Browse server-side filters and facets, test_facets_platforms_and_tdps(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none() (+33 more)

### Community 22 - "test_content_owner.py"
Cohesion: 0.08
Nodes (41): Task 4: Reconcile stub artifacts at every scan entry point, rescan_all(), _call_litemaas(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts() (+33 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.13
Nodes (20): compute_content_hash(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git(), repo(), test_content_hash_covers_full_body_past_the_prompt_cap(), test_content_hash_covers_prompt_input_csv_fields() (+12 more)

### Community 24 - "react"
Cohesion: 0.07
Nodes (36): Task 8: Frontend Refactor, BlockErrorBoundary, Props, State, ChatChip, ChatEnvelope, ProgressMessage, ProgressStream() (+28 more)

### Community 25 - "Settings"
Cohesion: 0.08
Nodes (29): list_role_assignments(), llm_provider_status(), submit_chat(), submit_query(), auth_me(), list_catalog(), fetch_litemaas_models(), _parse_csv() (+21 more)

### Community 26 - "re"
Cohesion: 0.09
Nodes (24): _call_litemaas_inner(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), _help_answer(), process_turn(), _scope_echo() (+16 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.23
Nodes (23): Task 1: Resolve content sources with explicit ownership, ComponentLink, node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous(), test_curator_content_path_override_is_not_a_pure_stub() (+15 more)

### Community 28 - "schemas.py"
Cohesion: 0.05
Nodes (66): ChatRequest, QueryRequest, select_recommendation(), SelectRequest, field_source_report(), AgvPrResponse, AuthMeResponse, CancelWorkflowResponse (+58 more)

### Community 29 - "seed"
Cohesion: 0.07
Nodes (49): Execution handoff, File map and verification conventions, Global Constraints, Review Focus, Self-review, Showroom Analysis Isolation Implementation Plan, Task 2: Persist source provenance and enforce scoped analysis reuse, Task 5: Keep recommendation identities within authorized relationships (+41 more)

### Community 30 - "App.tsx"
Cohesion: 0.08
Nodes (38): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), API_DOCS_URL (+30 more)

### Community 31 - "structlog"
Cohesion: 0.26
Nodes (6): _add_component(), get_logger(), _reorder_keys(), setup_logging(), test_logger_outputs_json(), test_logger_with_job_id()

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 33 - "Request"
Cohesion: 0.53
Nodes (4): get_query_result(), get_session(), list_sessions(), stream_query()

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

### Community 39 - "json"
Cohesion: 0.21
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.20
Nodes (18): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+10 more)

### Community 42 - "app.py"
Cohesion: 0.08
Nodes (7): lifespan(), _get_user_key(), RequestLoggingMiddleware, get_recommendations(), RecommendationRequest, _run_low(), _run_medium()

### Community 43 - ".get_content_entity"
Cohesion: 0.06
Nodes (24): resolve_item(), analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), test_token_usage(), db(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated() (+16 more)

### Community 44 - "test_analyzer.py"
Cohesion: 0.10
Nodes (25): check_showroom_stale(), classify_scan_error(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content() (+17 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.22
Nodes (18): asset_type_tokens(), content_id_for(), parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_content_id_format(), test_derive_osspa_status() (+10 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.12
Nodes (6): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), _recompute_windowed_scores(), TestComputePerformanceScore

### Community 47 - "api.ts"
Cohesion: 0.08
Nodes (59): Review Focus, Task 5: Shared frontend helpers and checkbox filter group, Task 6: Wire filters into Performance, Non-Prod and Retirement, Task 8: Run locally, check, and prepare the PR, CollapsibleFilterGroup(), CollapsibleFilterGroupProps, render(), LabelFilterGroup() (+51 more)

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
Cohesion: 0.18
Nodes (23): approve_item(), _base_name_to_content_id(), cancel_workflow(), check_stale(), edit_retirement(), ignore_item(), link_jira(), nonprod_ignore() (+15 more)

### Community 52 - "test_auth_security.py"
Cohesion: 0.11
Nodes (7): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders, TestUnauthenticatedAccess

### Community 53 - "chat_sessions.py"
Cohesion: 0.17
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 54 - "Vocabulary"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "Task 3: Return labels from the three analysis endpoints"
Cohesion: 0.14
Nodes (8): Task 3: Return labels from the three analysis endpoints, nonprod_dashboard(), _sort_empty_last(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists(), TestSortEmptyLast

### Community 56 - "osspa_sync.py"
Cohesion: 0.17
Nodes (7): clone_examples_repo(), expand_includes(), _expand(), file_commit_sha(), get_head_sha(), is_tracked_at_head(), _run_git()

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

### Community 61 - "pytest"
Cohesion: 0.08
Nodes (12): Envelope, client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey, test_envelope_round_trip(), test_intent_enum_closed(), test_performance_args_window_closed() (+4 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.12
Nodes (10): client(), db(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience() (+2 more)

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "build_retirement_description"
Cohesion: 0.18
Nodes (6): Open Questions / Risks, References, _base_name_from_content_id(), build_retirement_adoc_notice(), build_retirement_description(), test_wiki_markup_format()

### Community 65 - "patch"
Cohesion: 0.14
Nodes (8): _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response(), TestGroupLookup, TestValidateSaToken

### Community 66 - "HandsOnDriver"
Cohesion: 0.19
Nodes (6): Task 3: Hands-on Driver, _extract_duration_target(), HandsOnDriver, test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_triage_guidance()

### Community 67 - "reporting_sync.py"
Cohesion: 0.17
Nodes (9): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs(), _percentile_rank() (+1 more)

### Community 68 - "pytest"
Cohesion: 0.18
Nodes (17): RouterOutput, Scope, _parse_catalog_url(), pattern_check(), resolve_and_verify(), extract_urls(), test_examples_validate_as_router_output(), test_followup_chips_are_pre_routed() (+9 more)

### Community 69 - "test_sweep_github_only_cancellation_preserves_revert_until_jira_available"
Cohesion: 0.11
Nodes (9): test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), test_required_cancel_retains_workflow_on_jira_failure(), close_jira() (+1 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): Task 4: Frontend Page, findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName() (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "pipeline.py"
Cohesion: 0.16
Nodes (7): call_llm(), QueryState, _build_deterministic_assessment(), _call_synthesis(), generate_content_gaps(), generate_rationale(), triage()

### Community 73 - "migrate_to_content_model.py"
Cohesion: 0.14
Nodes (14): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+6 more)

### Community 74 - "analyzer.py"
Cohesion: 0.09
Nodes (30): Task 3: `analyze_description()` in the analyzer, 3. Scan pipeline branch, analysis_context_hash(), analysis_from_row(), analyze_showroom(), build_analysis_prompt(), build_description_prompt(), build_module_embedding_text() (+22 more)

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (6): Retirement Analysis Integration Plan, Retirement Workflow Actions Plan, Generalized Content Model Plan, Overlap Analysis Redesign Plan, Advisor Multi-Intent Chat Plan, Performance Page Plan

### Community 76 - "sync_opl_vocabulary.py"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 79 - "command"
Cohesion: 0.15
Nodes (12): command, flag(), get_db(), infra_stats(), init_db(), note(), override_url(), set_content_path() (+4 more)

### Community 80 - "run_category"
Cohesion: 0.22
Nodes (10): Modify, Task 6: Orchestrator + Pipeline Refactor, 2. Orchestrator and Pipeline, What Gets Deleted, registered_content_types(), run_category(), emit(), serialize_candidates() (+2 more)

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.13
Nodes (15): analyze_single(), resolve_showroom_source(), unresolved(), walk(), legacy_test_item(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(), test_existing_test_vectors_never_enter_content_retrieval() (+7 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.11
Nodes (9): get_workflow(), _nonprod_retirement_metrics(), _retirement_metrics(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodWindows, TestRetirementMetrics (+1 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.09
Nodes (38): run_retirement_sweep(), test_database_schema_setup_does_not_move_cutoff(), client(), db(), _sweep_context(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), create(), test_cancellation_does_not_mark_concurrently_retired_item() (+30 more)

### Community 85 - "jira.py"
Cohesion: 0.14
Nodes (10): _close_issue(), close_issue_done(), _fetch_oauth_token(), _get_access_token(), get_issue_status(), _issue_is_closed(), _jira_request(), _move_to_in_progress() (+2 more)

### Community 86 - "middleware/auth.py"
Cohesion: 0.09
Nodes (19): _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), _log_auth_decision(), require_admin(), require_auth(), require_curator() (+11 more)

### Community 87 - "_print"
Cohesion: 0.14
Nodes (8): osspa_sync_cmd(), _print(), refresh(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 88 - "ArchitectureDriver"
Cohesion: 0.18
Nodes (10): ArchitectureDriver, Candidate, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance() (+2 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.12
Nodes (15): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+7 more)

### Community 90 - "publish_progress"
Cohesion: 0.18
Nodes (7): publish_progress(), run_chat_turn(), on_progress(), _progress_bridge(), _publish(), run_recommendation(), on_progress()

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (19): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Babylon CRD Catalog Pipeline, LLM Provider Routing (LiteMaaS / Vertex AI), Nightly Maintenance Pipeline, Performance Scoring System (+11 more)

### Community 92 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.10
Nodes (38): Task 4: Unify scan persistence and remove cross-item fan-out, start_scan(), InvalidShowroomRef, order_for_reuse(), reuse_key_from_signature(), showroom_reuse_key(), scan_babylon_item(), run_stale_check() (+30 more)

### Community 94 - "asyncio"
Cohesion: 0.07
Nodes (21): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+13 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "normalize_row"
Cohesion: 0.36
Nodes (4): _as_bool(), derive_osspa_status(), normalize_row(), _split_list()

### Community 98 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (4): Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "Description-Based Analysis for Items With No Showroom — Design"
Cohesion: 0.20
Nodes (8): Anti-goals, Approaches considered, Deployment, Description-Based Analysis for Items With No Showroom — Design, Goals, Intent, Non-goals, Open items for the builder

### Community 101 - "Candidate"
Cohesion: 0.14
Nodes (10): _run_catalog_second_pass(), test_candidate_similarity_pct(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published(), test_query_state_defaults() (+2 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.09
Nodes (17): run_field_source_sync(), test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at() (+9 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (10): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+2 more)

### Community 108 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.18
Nodes (10): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Goals, Non-Goals, Parallel Pipeline Instances (+2 more)

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 112 - "create_app"
Cohesion: 0.04
Nodes (18): create_app(), client(), client(), test_sync_osspa_endpoint_enqueues_a_job(), client(), test_auth_me_unauthenticated(), client(), TestTokenExchange (+10 more)

### Community 113 - ".create_job"
Cohesion: 0.22
Nodes (6): _do(), test_job_failure(), test_job_lifecycle(), test_list_jobs(), test_list_jobs_shows_running_before_newer_queued(), test_queued_job_keeps_progress_json()

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.06
Nodes (24): migrate(), db(), db(), db(), db(), db(), db(), db() (+16 more)

### Community 121 - "test_retirement_edit.py"
Cohesion: 0.17
Nodes (5): client(), non_admin_client(), test_edit_returns_409_when_workflow_disappears(), test_edit_unknown_base_name_returns_404(), test_edit_without_fields_is_rejected()

### Community 123 - "ContentTypeDriver"
Cohesion: 0.11
Nodes (9): Create, Delete, File Map, Task 1: Candidate Model Refactor, Task 2: Driver Base Class + Registry, Task 4: Architecture Driver, ContentTypeDriver, _init_drivers() (+1 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "ops.py"
Cohesion: 0.08
Nodes (20): Decisions (Nate, 2026-11-19), check_pr_statuses(), batch_assess_overlaps(), _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr() (+12 more)

### Community 126 - "Content Owner Model for Virtual CIs — Design"
Cohesion: 0.17
Nodes (11): Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Pure stub, Rollout (+3 more)

### Community 127 - "option"
Cohesion: 0.18
Nodes (5): cli(), serve(), status(), vocab_stage_rescan(), vocab_unknowns()

### Community 128 - "effective_analysis_source"
Cohesion: 0.10
Nodes (20): Description-Based Analysis Implementation Plan, Global Constraints, Review Focus, Task 1: Schema columns + `effective_analysis_source()`, Task 5: Scan pipeline branch, Task 6: Stale check exclusion, Task 8: Frontend edit drawer, Task 9: Full verification (+12 more)

### Community 129 - "block"
Cohesion: 0.18
Nodes (11): cmd, migrate_pod, ansible.builtin.command, ansible.builtin.set_fact, changed_when, delay, name, register (+3 more)

### Community 130 - "post_tasks"
Cohesion: 0.18
Nodes (11): msg, kind, kubeconfig, label_selectors, namespace, post_tasks, ansible.builtin.debug, kubernetes.core.k8s_info (+3 more)

### Community 131 - "action_verbs"
Cohesion: 0.20
Nodes (10): action_verbs, hands_on, interactive, read_through, rejected, valid, rejected, valid (+2 more)

### Community 132 - "vector_search.py"
Cohesion: 0.10
Nodes (21): Content Owner Model Implementation Plan, Global Constraints, Rollout, Advisor, Root cause, _authorized_promotion(), eligible(), _eligible_stub() (+13 more)

### Community 133 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 134 - "handlers.py"
Cohesion: 0.09
Nodes (39): get_item_workloads(), get_performance_scores(), _prefix_overlap(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+31 more)

### Community 136 - "_jira_event_messages"
Cohesion: 0.10
Nodes (9): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_requires_admin(), test_edit_update_skips_cancelled_workflows(), test_edit_without_change_records_no_event() (+1 more)

### Community 139 - "showroom_source.py"
Cohesion: 0.08
Nodes (20): _apply_component_inheritance(), CatalogReader, collect(), load(), _collect_bases(), component_item_to_ci_name(), _content_fields(), extract_base_ci_refs() (+12 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.16
Nodes (21): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+13 more)

### Community 169 - "content_owner"
Cohesion: 0.15
Nodes (15): Review Focus, Task 1: `content_owner` helper, Task 2: Database read and write methods for stubs, Task 3: Scan skips pure stubs, Task 5: Mirror card fields when an owner scan saves, Task 7: `get_display_analysis` and the three runtime read sites, Task 8: Browse detail shows the owner's analysis and names the owner, Task 9: Curator edits on a stub write the owner's analysis row (+7 more)

### Community 172 - "test_catalog_labels.py"
Cohesion: 0.07
Nodes (18): Task 1: Read and store Platform/TDP labels, Task 2: Union labels per base name, extract_base_name(), _seed_label_count_items(), test_extract_keys_are_case_sensitive(), test_extract_missing_labels_are_none(), test_extract_reads_platform_and_tdps(), test_label_counts_follow_other_filters() (+10 more)

### Community 173 - "close_issue_wont_do"
Cohesion: 0.20
Nodes (6): close_issue_wont_do(), test_already_closed_issue_needs_no_transition(), test_closure_requires_a_terminal_result(), test_required_closure_selects_resolution_and_verifies_result(), request(), test_jira_close_reports_whether_it_transitioned()

### Community 174 - "test_showroom_reuse.py"
Cohesion: 0.21
Nodes (15): Task 3: Fetch the exact source and reject non-content inputs, prime(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_embedding_only_changes_repair_only_affected_artifacts(), test_every_changed_signature_input_prevents_donor_reuse(), test_force_bypasses_unchanged_fast_path_and_donors(), test_identical_revision_and_context_skips_clone_llm_and_embeddings() (+7 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "MemoryArtifacts"
Cohesion: 0.17
Nodes (3): MemoryArtifacts, scan(), run()

### Community 180 - "ensure_issue_event_comment"
Cohesion: 0.12
Nodes (11): ensure_issue_event_comment(), jira_auth_configured(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), reuse_lock_id(), test_comment_failed_lookup_does_not_post() (+3 more)

### Community 181 - "Python Dependency Manifest (requirements.lock)"
Cohesion: 0.22
Nodes (9): Anthropic SDK Dependency (v0.120.0), arq Dependency (v0.28.0), Python Dependency Manifest (requirements.lock), FastAPI Dependency (v0.140.7), OpenAI SDK Dependency (v2.49.0), psycopg Dependency (v3.3.4), Pydantic Dependency (v2.13.4), Redis Client Dependency (v5.3.1) (+1 more)

### Community 182 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 183 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 184 - "rationale.py"
Cohesion: 0.22
Nodes (9): Content-Type Drivers Implementation Plan, Execution Notes, Global Constraints, Review Focus, Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, _primary_asset_type(), _call_rationale_single() (+1 more)

### Community 186 - "mcp_query"
Cohesion: 0.22
Nodes (4): _mcp_call(), mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 190 - "Field Source Content"
Cohesion: 0.25
Nodes (7): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git()

### Community 191 - ".get_unknown_terms"
Cohesion: 0.20
Nodes (3): TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm

### Community 192 - "Design"
Cohesion: 0.15
Nodes (13): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Candidate Dataclass, `content_entities` (shared table — all types) (+5 more)

### Community 195 - "test_start_retirement_holds_lock_while_creating_ticket"
Cohesion: 0.47
Nodes (6): workflow_lock_id(), _approved_unstarted(), test_manual_pr_creation_respects_cleanup_lock(), test_start_retirement_holds_lock_while_creating_ticket(), fake_create(), test_start_retirement_respects_workflow_lock()

### Community 198 - "BaseModel"
Cohesion: 0.33
Nodes (4): ApproveRequest, EditRetirementRequest, LinkJiraRequest, NotesRequest

### Community 199 - "test_infrastructure.py"
Cohesion: 0.20
Nodes (7): seed_infrastructure(), clean_infra(), db(), test_get_infrastructure_with_item_counts(), test_list_infrastructure_with_type_filter(), test_upsert_infrastructure_insert(), test_upsert_infrastructure_update()

### Community 200 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 201 - "Global Constraints"
Cohesion: 0.20
Nodes (8): Field Source Content Report — Implementation Plan, Global Constraints, Task 1: Database Schema and Methods, Task 2: Reporting Sync Job, Task 3: API Endpoint, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, _build_field_source_sql()

### Community 202 - "Platform and Technical Decision Point filters — design"
Cohesion: 0.13
Nodes (12): Global Constraints, Platform and TDP Filters Implementation Plan, Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals (+4 more)

### Community 204 - "performance_dashboard"
Cohesion: 0.20
Nodes (7): _extract_base_name_from_content_id(), overlap_assessment_detail(), overlap_report(), performance_dashboard(), retirement_dashboard(), stream_job(), TestRetirementDashboardMetrics

### Community 205 - "OsspaSyncError"
Cohesion: 0.33
Nodes (3): fetch_palist_csv(), OsspaSyncError, _boom()

### Community 208 - "test_drivers.py"
Cohesion: 0.14
Nodes (15): get_driver(), get_drivers_for_types(), format_triage_candidates(), _make_hands_on_candidate(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_get_driver_architecture(), test_get_driver_lab() (+7 more)

### Community 209 - "content_modes"
Cohesion: 0.40
Nodes (5): content_modes, architecture, demo, lab, sandbox

### Community 210 - "build_infrastructure_embedding_text"
Cohesion: 0.60
Nodes (3): build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

### Community 212 - "kubernetes.core.k8s_exec"
Cohesion: 0.50
Nodes (4): kubernetes.core.k8s_exec, kubeconfig, namespace, pod

### Community 213 - "collections"
Cohesion: 0.50
Nodes (3): collections, name, version

### Community 214 - "solutions"
Cohesion: 0.50
Nodes (4): solutions, aliases, is_tdp, name

### Community 215 - "ansible.builtin.assert"
Cohesion: 0.67
Nodes (3): fail_msg, that, ansible.builtin.assert

## Knowledge Gaps
- **92 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+87 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1402 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **64 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `effective_analysis_source`, `vector_search.py`, `handlers.py`, `db/__init__.py`, `_jira_event_messages`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `settings.py`, `workload_scanner.py`, `test_db.py`, `Settings`, `re`, `seed`, `json`, `app.py`, `.get_content_entity`, `test_catalog_labels.py`, `chat_sessions.py`, `run_osspa_sync`, `TestGetNonprodBaseNames`, `test_catalog_osspa_routes.py`, `.get_unknown_terms`, `test_start_retirement_holds_lock_while_creating_ticket`, `pytest`, `workload_scan`, `test_infrastructure.py`, `pipeline.py`, `._set_showroom_override`, `command`, `run_category`, `._artifact_connection`, `test_nonprod.py`, `test_retirement_pr_status.py`, `_print`, `publish_progress`, `asyncio`, `Description-Based Analysis for Items With No Showroom — Design`, `test_field_source_sync.py`, `create_app`, `.create_job`, `.close`, `test_retirement_edit.py`?**
  _High betweenness centrality (0.205) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `Database` (e.g. with `Settings` and `AnalysisSignature`) actually correct?**
  _`Database` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _92 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.10344827586206896 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `Database`, `test_description_analysis.py`, `cli.py`, `handlers.py`, `routes/catalog.py`, `admin.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `settings.py`, `routes/auth.py`, `test_content_owner.py`, `re`, `schemas.py`, `seed`, `Request`, `JobProgressRelay`, `json`, `app.py`, `.get_content_entity`, `analysis.py`, `test_auth_security.py`, `run_osspa_sync`, `pytest`, `test_catalog_osspa_routes.py`, `workload_scan`, `pytest`, `pipeline.py`, `analyzer.py`, `performance_dashboard`, `scan`, `command`, `run_category`, `test_test_content_exclusion.py`, `test_retirement_pr_status.py`, `middleware/auth.py`, `_print`, `AdocRead`, `asyncio`, `create_app`, `.close`, `test_retirement_edit.py`, `ops.py`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Are the 36 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.02726201002063071 - nodes in this community are weakly interconnected._