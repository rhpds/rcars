# Graph Report - rhdpcd-963  (2026-11-20)

## Corpus Check
- 329 files · ~548,202 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4207 nodes · 10491 edges · 223 communities (155 shown, 68 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 1300 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `40d555d4`
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
- middleware/auth.py
- routes/auth.py
- test_catalog_labels.py
- test_content_owner.py
- test_osspa_adoc.py
- react
- Settings
- re
- test_test_content_exclusion.py
- schemas.py
- seed
- App.tsx
- settings.py
- common.yml
- advisor.py
- JobProgressRelay
- ContentAnalysisPage.tsx
- Controlled Vocabulary
- load_vocabulary
- patch
- compilerOptions
- test_jira_service.py
- pipeline.py
- test_api_keys_db.py
- test_analyzer.py
- test_osspa_csv.py
- compute_sales_impact
- api.ts
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- analysis.py
- hashlib
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
- with
- test_osspa_db.py
- HandsOnDriver
- test_drivers.py
- RouterOutput
- sync_opl_vocabulary.py
- api.ts
- ECA Production Redesign Spec
- sys
- migrate_to_content_model.py
- analyzer.py
- Reporting MCP Data Sync
- test_llm_routing.py
- TestValidation
- .upsert_babylon_catalog_item
- command
- reporting_sync.py
- test_cancel_preserves_tracking_on_github_failure
- vocabulary.yaml
- test_nonprod.py
- test_retirement_pr_status.py
- jira.py
- _parse_sa_allowlist
- test_workers.py
- ArchitectureDriver
- build_retirement_description
- pre_tasks
- System Design Architecture Doc
- .list_content_entities_filtered
- test_showroom_scan.py
- asyncio
- Showroom analysis isolation
- Scan Pipeline
- orchestrator.py
- Browse Page Redesign Plan
- API Authentication Design
- Description-Based Analysis for Items With No Showroom — Design
- Candidate
- TestVocabularyEndpoints
- rcars-login.sh
- handlers.py
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- Advisor v2 — Content-Type Drivers
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- block
- database.py
- ResolvedShowroom
- content_entities Table
- test_vocabulary.py
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- test_reporting.py
- _print
- setup_logging
- ContentTypeDriver
- test_orphan_cleanup.py
- retirement_cleanup.py
- test_showroom_reuse.py
- post_tasks
- effective_analysis_source
- .create_job
- RequestLoggingMiddleware
- action_verbs
- content_owner
- _sync_nonprod_usage
- chat/models.py
- TestStepOrder
- _jira_event_messages
- docker-entrypoint.sh
- Webhook Configuration Task
- option
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
- Python Dependency Manifest (requirements.lock)
- Match Event Prompt Template
- extract_base_name
- deploy.yml
- tasks
- db
- Python Requirements Entry Point
- MemoryArtifacts
- ignored_terms
- TestTokenExchange
- content_modes
- unittest_mock
- rationale.py
- extract_catalog_item
- mcp_query
- kubernetes.core.k8s_exec
- TestGetNonprodBaseNames
- TestBuildWindowedMetrics
- collections
- test_vocabulary_db.py
- solutions
- build_sandbox_summary
- get
- ansible.builtin.assert
- .upsert_babylon_catalog_item
- RouterOutput
- Content Owner Model for Virtual CIs — Design
- test_infrastructure.py
- test_auth_routes.py
- test_field_source_sync.py
- test_advisor_session
- render_vocabulary_block
- run_analysis
- test_chat_handlers.py
- build_embedding_text
- _reset_token_cache
- pathlib
- fetch_litemaas_models
- workflow_lock_id
- 3. Candidate Model
- overlap_candidates_cmd
- TestSpoofedProxyHeaders
- test_edit_rejects_name_without_replacement_ci
- test_edit_rejected_for_retired_item
- test_edit_rejected_while_cancellation_pending
- TestUnauthenticatedAccess
- TestUnknownTermsSchema

## God Nodes (most connected - your core abstractions)
1. `Database` - 303 edges
2. `Settings` - 181 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `seed()` - 46 edges
6. `scan_babylon_item()` - 45 edges
7. `create_app()` - 41 edges
8. `run_retirement_sweep()` - 40 edges
9. `ResolvedShowroom` - 38 edges
10. `content_owner()` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Task 1: Candidate Model Refactor` --references--> `Candidate`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/models.py
- `Review Focus` --references--> `run_category()`  [INFERRED]
  docs/superpowers/plans/2026-09-25-content-type-drivers.md → src/api/rcars/services/recommender/pipeline.py
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Summary` --references--> `isArchitecture()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/frontend/src/pages/browse/helpers.ts

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

## Communities (223 total, 68 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.10
Nodes (16): _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen() (+8 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (29): osspa_sync_cmd(), Database, db(), db(), seed_infrastructure(), db(), db(), db() (+21 more)

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
Cohesion: 0.13
Nodes (9): concurrency, cancel-in-progress, group, infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group() (+1 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.12
Nodes (12): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats(), test_idempotent_upsert() (+4 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.11
Nodes (31): Task 9: Curator edits on a stub write the owner's analysis row, add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+23 more)

### Community 9 - "admin.py"
Cohesion: 0.13
Nodes (25): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+17 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.08
Nodes (33): deliver_pending_events(), comments(), event_time(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_malformed_page_does_not_prove_absence(), test_comment_missing_credentials_does_not_call_http(), unexpected() (+25 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): Task 7: Browse UI (provisional style), getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline() (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (23): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+15 more)

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 17 - "ops.py"
Cohesion: 0.13
Nodes (16): scan_all_collections(), publish_progress(), WorkerContext, _progress_bridge(), _publish(), run_babylon_pipeline(), run_catalog_refresh(), run_field_source_sync_job() (+8 more)

### Community 18 - "workload_scanner.py"
Cohesion: 0.08
Nodes (17): call_llm(), build_infrastructure_embedding_text(), ls_remote_sha(), _resolve_ref_from_lookup(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes() (+9 more)

### Community 19 - "middleware/auth.py"
Cohesion: 0.09
Nodes (18): _check_api_key_role_ceiling(), _get_cached_role_assignments(), get_current_user(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), require_performance_view() (+10 more)

### Community 20 - "routes/auth.py"
Cohesion: 0.11
Nodes (17): invalidate_api_key_cache(), _get_user_key(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key() (+9 more)

### Community 21 - "test_catalog_labels.py"
Cohesion: 0.11
Nodes (13): Task 4: Browse server-side filters and facets, _seed_label_count_items(), test_facets_platforms_and_tdps(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2() (+5 more)

### Community 22 - "test_content_owner.py"
Cohesion: 0.14
Nodes (31): Task 4: Reconcile stub artifacts at every scan entry point, rescan_all(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner() (+23 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.10
Nodes (24): AdocRead, compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough() (+16 more)

### Community 24 - "react"
Cohesion: 0.07
Nodes (36): Task 8: Frontend Refactor, BlockErrorBoundary, Props, State, ChatChip, ChatEnvelope, ProgressMessage, ProgressStream() (+28 more)

### Community 25 - "Settings"
Cohesion: 0.04
Nodes (39): create_app(), _parse_csv(), Settings, client(), client(), client(), test_auth_me_unauthenticated(), app_no_auth() (+31 more)

### Community 26 - "re"
Cohesion: 0.18
Nodes (13): _call_litemaas_inner(), LLMResult, _extract_json(), route(), llm(), _fake(), llm_call(), test_call_error_falls_back() (+5 more)

### Community 27 - "test_test_content_exclusion.py"
Cohesion: 0.05
Nodes (57): Task 1: Resolve content sources with explicit ownership, _apply_component_inheritance(), CatalogReader, collect(), load(), _collect_bases(), component_item_to_ci_name(), _content_fields() (+49 more)

### Community 28 - "schemas.py"
Cohesion: 0.06
Nodes (59): field_source_report(), health(), readiness(), AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload (+51 more)

### Community 29 - "seed"
Cohesion: 0.14
Nodes (29): Task 2: Persist source provenance and enforce scoped analysis reuse, Task 6: Advisor shows the stub in place of its owner, add_stub(), search(), test_ci_reference_to_a_stub_resolves_through_its_owner(), test_dev_hit_promotes_to_the_prod_counterpart_stub(), test_each_owner_promotes_to_its_own_stub(), test_exact_same_item_prod_requires_complete_matching_signature() (+21 more)

### Community 30 - "App.tsx"
Cohesion: 0.08
Nodes (38): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), API_DOCS_URL (+30 more)

### Community 31 - "settings.py"
Cohesion: 0.14
Nodes (7): run_chat_turn(), on_progress(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url(), scan_startup(), _startup()

### Community 32 - "common.yml"
Cohesion: 0.03
Nodes (58): admin_emails, api_cpu_limit, api_cpu_request, api_memory_limit, api_memory_request, api_replicas, app_name, app_port (+50 more)

### Community 33 - "advisor.py"
Cohesion: 0.10
Nodes (14): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+6 more)

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

### Community 38 - "patch"
Cohesion: 0.14
Nodes (9): _fetch_group_members(), _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response(), TestGroupLookup (+1 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.18
Nodes (19): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+11 more)

### Community 42 - "pipeline.py"
Cohesion: 0.09
Nodes (21): Modify, Task 6: Orchestrator + Pipeline Refactor, 2. Orchestrator and Pipeline, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Design, Display Config Structure (+13 more)

### Community 43 - "test_api_keys_db.py"
Cohesion: 0.17
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 44 - "test_analyzer.py"
Cohesion: 0.09
Nodes (26): check_showroom_stale(), classify_scan_error(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content() (+18 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.12
Nodes (24): _as_bool(), asset_type_tokens(), content_id_for(), derive_osspa_status(), fetch_palist_csv(), normalize_row(), OsspaSyncError, parse_palist_csv() (+16 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.13
Nodes (5): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), TestComputePerformanceScore

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
Cohesion: 0.13
Nodes (28): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), check_pr_statuses(), check_stale(), edit_retirement(), EditRetirementRequest (+20 more)

### Community 52 - "hashlib"
Cohesion: 0.14
Nodes (9): ensure_issue_event_comment(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), reuse_lock_id(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response() (+1 more)

### Community 53 - "chat_sessions.py"
Cohesion: 0.18
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 54 - "Vocabulary"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "Task 3: Return labels from the three analysis endpoints"
Cohesion: 0.13
Nodes (9): Task 3: Return labels from the three analysis endpoints, _extract_base_name_from_content_id(), performance_dashboard(), retirement_dashboard(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists() (+1 more)

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.22
Nodes (19): run_osspa_sync(), _csv(), fake_analyze(), fake_repo(), settings(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring() (+11 more)

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
Cohesion: 0.14
Nodes (12): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), _split_list(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms() (+4 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.08
Nodes (9): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures() (+1 more)

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "with"
Cohesion: 0.07
Nodes (31): runs-on, steps, environment, needs, runs-on, steps, name, url (+23 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.08
Nodes (13): test_token_usage(), _row(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override() (+5 more)

### Community 66 - "HandsOnDriver"
Cohesion: 0.17
Nodes (10): Task 3: Hands-on Driver, _extract_duration_target(), HandsOnDriver, Candidate, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming() (+2 more)

### Community 67 - "test_drivers.py"
Cohesion: 0.14
Nodes (14): get_driver(), get_drivers_for_types(), format_triage_candidates(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_get_driver_architecture() (+6 more)

### Community 68 - "RouterOutput"
Cohesion: 0.12
Nodes (9): _prefix_overlap(), _expand_vocab_aliases(), _find_keyword_ties(), _parse_catalog_url(), pattern_check(), resolve_item(), _result_turns(), _turn_chips() (+1 more)

### Community 69 - "sync_opl_vocabulary.py"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): Task 4: Frontend Page, findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName() (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "sys"
Cohesion: 0.17
Nodes (8): migrate(), cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 73 - "migrate_to_content_model.py"
Cohesion: 0.14
Nodes (14): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+6 more)

### Community 74 - "analyzer.py"
Cohesion: 0.07
Nodes (27): Task 3: `analyze_description()` in the analyzer, Open items for the builder, analysis_context_hash(), analysis_from_row(), build_analysis_prompt(), build_description_prompt(), _canonical_content(), compute_analysis_context_hash() (+19 more)

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (6): Retirement Analysis Integration Plan, Retirement Workflow Actions Plan, Generalized Content Model Plan, Overlap Analysis Redesign Plan, Advisor Multi-Intent Chat Plan, Performance Page Plan

### Community 76 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - ".upsert_babylon_catalog_item"
Cohesion: 0.14
Nodes (18): test_retire_missing_babylon_ignores_other_sources(), _arch(), _seed_nonprod(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators() (+10 more)

### Community 79 - "command"
Cohesion: 0.15
Nodes (12): command, flag(), get_db(), infra_stats(), note(), override_url(), refresh(), set_content_path() (+4 more)

### Community 80 - "reporting_sync.py"
Cohesion: 0.17
Nodes (10): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs(), _percentile_rank() (+2 more)

### Community 81 - "test_cancel_preserves_tracking_on_github_failure"
Cohesion: 0.12
Nodes (8): test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), close_jira(), state(), test_sweep_github_only_cancellation_preserves_revert_until_jira_available()

### Community 82 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.09
Nodes (10): get_workflow(), _nonprod_retirement_metrics(), _retirement_metrics(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestNonprodWindows (+2 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.11
Nodes (35): run_retirement_sweep(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancellation_does_not_mark_concurrently_retired_item(), test_manual_pr_creation_respects_cleanup_lock(), test_merged_revert_still_deletes_workflow(), test_refresh_completes_merged_removal_before_target_date() (+27 more)

### Community 85 - "jira.py"
Cohesion: 0.09
Nodes (14): _close_issue(), close_issue_done(), close_issue_wont_do(), _fetch_oauth_token(), _get_access_token(), get_issue_status(), _issue_is_closed(), jira_auth_configured() (+6 more)

### Community 87 - "test_workers.py"
Cohesion: 0.28
Nodes (6): test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes()

### Community 88 - "ArchitectureDriver"
Cohesion: 0.15
Nodes (11): 1. Content-Type Drivers, Adding a New Content Type, Driver Interface, What Moves Into Drivers, ArchitectureDriver, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough() (+3 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.08
Nodes (20): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+12 more)

### Community 90 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (19): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Babylon CRD Catalog Pipeline, LLM Provider Routing (LiteMaaS / Vertex AI), Nightly Maintenance Pipeline, Performance Scoring System (+11 more)

### Community 92 - ".list_content_entities_filtered"
Cohesion: 0.20
Nodes (11): _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default(), test_filtered_catalog_pagination(), test_filtered_catalog_search() (+3 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.10
Nodes (38): start_scan(), scan(), InvalidShowroomRef, order_for_reuse(), reuse_key_from_signature(), showroom_reuse_key(), scan_babylon_item(), run_stale_check() (+30 more)

### Community 94 - "asyncio"
Cohesion: 0.11
Nodes (20): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+12 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "orchestrator.py"
Cohesion: 0.20
Nodes (11): build_scaffold(), compose_answer(), _strip_formatting(), _help_answer(), process_turn(), _scope_echo(), followup_chips(), test_answer_failure_degrades_to_scaffold() (+3 more)

### Community 98 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (4): Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "Description-Based Analysis for Items With No Showroom — Design"
Cohesion: 0.12
Nodes (15): 1. Storage, 2. Source resolution, 4. Candidate selection and stale check, 5. API, 6. Frontend, 7. Coverage math, Anti-goals, Approaches considered (+7 more)

### Community 101 - "Candidate"
Cohesion: 0.14
Nodes (10): _run_catalog_second_pass(), test_candidate_similarity_pct(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published(), test_query_state_defaults() (+2 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "handlers.py"
Cohesion: 0.24
Nodes (15): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+7 more)

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.17
Nodes (10): Task 2: Reporting Sync Job, _build_field_source_sql(), run_field_source_sync(), FakeSettings, _mock_mcp_query(), test_field_source_sync_captures_user_email(), test_field_source_sync_ignores_agd_v2_items(), tracking_mock() (+2 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (10): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+2 more)

### Community 108 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.18
Nodes (10): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Goals, Non-Goals, Parallel Pipeline Instances (+2 more)

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "block"
Cohesion: 0.18
Nodes (11): cmd, migrate_pod, ansible.builtin.command, ansible.builtin.set_fact, changed_when, delay, name, register (+3 more)

### Community 112 - "database.py"
Cohesion: 0.05
Nodes (12): lifespan(), derive_status(), retirement_label(), test_sync_osspa_endpoint_enqueues_a_job(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, settings() (+4 more)

### Community 113 - "ResolvedShowroom"
Cohesion: 0.12
Nodes (16): Task 6: Add a narrowly scoped reset and verify the full rebuild contract, ResolvedShowroom, main(), snapshots(), test_dry_run_performs_no_writes(), test_execute_requires_scans_paused_confirmation(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data() (+8 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 120 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 121 - "_print"
Cohesion: 0.14
Nodes (6): _print(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 122 - "setup_logging"
Cohesion: 0.22
Nodes (8): _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), shutdown(), test_logger_outputs_json(), test_logger_with_job_id()

### Community 123 - "ContentTypeDriver"
Cohesion: 0.07
Nodes (13): Content-Type Drivers Implementation Plan, Create, Delete, Execution Notes, File Map, Global Constraints, Review Focus, Task 1: Candidate Model Refactor (+5 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.24
Nodes (10): cancel_workflow(), _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable() (+2 more)

### Community 126 - "test_showroom_reuse.py"
Cohesion: 0.13
Nodes (22): API, Data Import, Data Source, Field Source Content, Frontend, Task 3: Fetch the exact source and reject non-content inputs, git_repo(), git() (+14 more)

### Community 127 - "post_tasks"
Cohesion: 0.18
Nodes (11): msg, kind, kubeconfig, label_selectors, namespace, post_tasks, ansible.builtin.debug, kubernetes.core.k8s_info (+3 more)

### Community 128 - "effective_analysis_source"
Cohesion: 0.16
Nodes (13): Description-Based Analysis Implementation Plan, Global Constraints, Review Focus, Task 1: Schema columns + `effective_analysis_source()`, Task 5: Scan pipeline branch, Task 6: Stale check exclusion, Task 8: Frontend edit drawer, Task 9: Full verification (+5 more)

### Community 129 - ".create_job"
Cohesion: 0.22
Nodes (6): _do(), test_job_failure(), test_job_lifecycle(), test_list_jobs(), test_list_jobs_shows_running_before_newer_queued(), test_queued_job_keeps_progress_json()

### Community 131 - "action_verbs"
Cohesion: 0.20
Nodes (10): action_verbs, hands_on, interactive, read_through, rejected, valid, rejected, valid (+2 more)

### Community 132 - "content_owner"
Cohesion: 0.07
Nodes (35): Content Owner Model Implementation Plan, Global Constraints, Review Focus, Rollout, Task 1: `content_owner` helper, Task 2: Database read and write methods for stubs, Task 3: Scan skips pure stubs, Task 5: Mirror card fields when an owner scan saves (+27 more)

### Community 133 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 134 - "chat/models.py"
Cohesion: 0.14
Nodes (17): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+9 more)

### Community 136 - "_jira_event_messages"
Cohesion: 0.10
Nodes (9): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_requires_admin(), test_edit_update_skips_cancelled_workflows(), test_edit_without_change_records_no_event() (+1 more)

### Community 139 - "option"
Cohesion: 0.14
Nodes (7): cli(), init_db(), serve(), status(), vocab_stage_rescan(), vocab_unknowns(), _do()

### Community 143 - "retirement-system.md"
Cohesion: 0.16
Nodes (21): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+13 more)

### Community 169 - "Python Dependency Manifest (requirements.lock)"
Cohesion: 0.22
Nodes (9): Anthropic SDK Dependency (v0.120.0), arq Dependency (v0.28.0), Python Dependency Manifest (requirements.lock), FastAPI Dependency (v0.140.7), OpenAI SDK Dependency (v2.49.0), psycopg Dependency (v3.3.4), Pydantic Dependency (v2.13.4), Redis Client Dependency (v5.3.1) (+1 more)

### Community 172 - "extract_base_name"
Cohesion: 0.13
Nodes (8): Task 2: Union labels per base name, extract_base_name(), test_labels_empty_input(), test_labels_include_retired_stage(), test_labels_union_across_stages(), test_labels_union_tdp2_only(), test_labels_unlabeled_item_has_empty_lists(), TestExtractBaseName

### Community 173 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 174 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 175 - "db"
Cohesion: 0.13
Nodes (9): client(), db(), settings(), test_lifecycle_cancellation_closures_and_outcome_survive_comment_failure(), close(), client(), db(), create() (+1 more)

### Community 180 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 182 - "content_modes"
Cohesion: 0.40
Nodes (5): content_modes, architecture, demo, lab, sandbox

### Community 183 - "unittest_mock"
Cohesion: 0.11
Nodes (9): WorkerSettings, test_already_closed_issue_needs_no_transition(), test_required_closure_selects_resolution_and_verifies_result(), request(), clear_vocabulary_cache(), client(), TestRoleGating, test_worker_context_has_required_fields() (+1 more)

### Community 184 - "rationale.py"
Cohesion: 0.20
Nodes (9): Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, _primary_asset_type(), _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis(), _format_single_candidate(), generate_content_gaps() (+1 more)

### Community 185 - "extract_catalog_item"
Cohesion: 0.09
Nodes (18): Global Constraints, Platform and TDP Filters Implementation Plan, Task 1: Read and store Platform/TDP labels, Anti-goals, Constraints, Decisions, Goals, Left to the builder (+10 more)

### Community 186 - "mcp_query"
Cohesion: 0.13
Nodes (10): Field Source Content Report — Implementation Plan, Global Constraints, Task 1: Database Schema and Methods, Task 3: API Endpoint, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, _mcp_call(), mcp_query() (+2 more)

### Community 187 - "kubernetes.core.k8s_exec"
Cohesion: 0.50
Nodes (4): kubernetes.core.k8s_exec, kubeconfig, namespace, pod

### Community 190 - "collections"
Cohesion: 0.50
Nodes (3): collections, name, version

### Community 191 - "test_vocabulary_db.py"
Cohesion: 0.20
Nodes (3): TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm

### Community 192 - "solutions"
Cohesion: 0.50
Nodes (4): solutions, aliases, is_tdp, name

### Community 194 - "get"
Cohesion: 0.22
Nodes (6): nonprod_dashboard(), overlap_assessment_detail(), overlap_report(), _sort_empty_last(), stream_job(), TestSortEmptyLast

### Community 195 - "ansible.builtin.assert"
Cohesion: 0.67
Nodes (3): fail_msg, that, ansible.builtin.assert

### Community 196 - ".upsert_babylon_catalog_item"
Cohesion: 0.10
Nodes (8): db_with_perf_data(), test_content_path(), test_list_catalog_items(), test_upsert_and_get_catalog_item(), test_upsert_updates_existing(), test_browse_maps_retirement_to_sibling_stages(), test_browse_reports_retirement_workflow_status(), test_browse_sibling_retirement_ignores_unapproved_own_row()

### Community 197 - "RouterOutput"
Cohesion: 0.46
Nodes (12): RouterOutput, Scope, resolve_and_verify(), test_scope_shapes(), test_lb_ref_resolves(), test_low_confidence_clarifies(), test_performance_is_public_by_default(), test_role_gate_redirects() (+4 more)

### Community 198 - "Content Owner Model for Virtual CIs — Design"
Cohesion: 0.15
Nodes (12): Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Pure stub (+4 more)

### Community 199 - "test_infrastructure.py"
Cohesion: 0.14
Nodes (7): clean_infra(), test_get_infrastructure_with_item_counts(), test_list_infrastructure_with_type_filter(), test_upsert_infrastructure_insert(), test_upsert_infrastructure_update(), db(), seed_items()

### Community 200 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (4): client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 201 - "test_field_source_sync.py"
Cohesion: 0.12
Nodes (9): test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at(), _row() (+1 more)

### Community 204 - "run_analysis"
Cohesion: 0.18
Nodes (9): Execution handoff, File map and verification conventions, Global Constraints, Review Focus, Self-review, Showroom Analysis Isolation Implementation Plan, Task 4: Unify scan persistence and remove cross-item fan-out, Task 5: Keep recommendation identities within authorized relationships (+1 more)

### Community 205 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 209 - "fetch_litemaas_models"
Cohesion: 0.43
Nodes (3): llm_provider_status(), workload_scan(), fetch_litemaas_models()

### Community 210 - "workflow_lock_id"
Cohesion: 0.60
Nodes (5): workflow_lock_id(), _approved_unstarted(), test_start_retirement_holds_lock_while_creating_ticket(), fake_create(), test_start_retirement_respects_workflow_lock()

### Community 211 - "3. Candidate Model"
Cohesion: 0.50
Nodes (4): 3. Candidate Model, Candidate Dataclass, `content_entities` (shared table — all types), Source-specific tables

## Knowledge Gaps
- **92 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+87 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1403 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **68 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `effective_analysis_source`, `.create_job`, `content_owner`, `db/__init__.py`, `_jira_event_messages`, `test_retirement_jira_events.py`, `option`, `test_overlap_assessment.py`, `ops.py`, `workload_scanner.py`, `test_catalog_labels.py`, `settings.py`, `pipeline.py`, `test_api_keys_db.py`, `extract_base_name`, `db`, `chat_sessions.py`, `rationale.py`, `run_osspa_sync`, `TestGetNonprodBaseNames`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `test_vocabulary_db.py`, `test_osspa_db.py`, `.upsert_babylon_catalog_item`, `RouterOutput`, `RouterOutput`, `test_infrastructure.py`, `sys`, `test_field_source_sync.py`, `test_advisor_session`, `analyzer.py`, `.upsert_babylon_catalog_item`, `command`, `workflow_lock_id`, `test_nonprod.py`, `test_retirement_pr_status.py`, `.list_content_entities_filtered`, `asyncio`, `orchestrator.py`, `Description-Based Analysis for Items With No Showroom — Design`, `handlers.py`, `database.py`, `ResolvedShowroom`, `_print`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `Database` (e.g. with `build_evidence_pack()` and `handle_help()`) actually correct?**
  _`Database` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _92 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.10344827586206896 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `Database`, `test_description_analysis.py`, `cli.py`, `routes/catalog.py`, `admin.py`, `test_retirement_jira_events.py`, `option`, `test_overlap_assessment.py`, `ops.py`, `workload_scanner.py`, `middleware/auth.py`, `routes/auth.py`, `re`, `test_test_content_exclusion.py`, `seed`, `settings.py`, `advisor.py`, `JobProgressRelay`, `pipeline.py`, `db`, `analysis.py`, `Task 3: Return labels from the three analysis endpoints`, `unittest_mock`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `RouterOutput`, `RouterOutput`, `sys`, `test_auth_routes.py`, `analyzer.py`, `test_llm_routing.py`, `test_chat_handlers.py`, `command`, `fetch_litemaas_models`, `test_retirement_pr_status.py`, `test_showroom_scan.py`, `asyncio`, `orchestrator.py`, `handlers.py`, `database.py`, `ResolvedShowroom`, `_print`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.024483267716535435 - nodes in this community are weakly interconnected._