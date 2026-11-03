# Graph Report - rcars-advisory  (2026-11-03)

## Corpus Check
- 306 files · ~529,062 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 3703 nodes · 9010 edges · 199 communities (138 shown, 61 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 893 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c1b59b72`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- HandsOnDriver
- Database
- registry.ts
- Portfolio Architecture Ingest Design Spec
- middleware/auth.py
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
- app.py
- workload_scanner.py
- test_catalog_labels.py
- routes/auth.py
- test_db.py
- database.py
- test_osspa_adoc.py
- react
- Settings
- route
- test_auth_middleware.py
- schemas.py
- seed
- App.tsx
- settings.py
- ops.py
- test_reporting.py
- JobProgressRelay
- test_services.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- jira.py
- _sync_nonprod_usage
- Any
- test_analyzer.py
- test_osspa_csv.py
- reporting_sync.py
- api.ts
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- analysis.py
- test_drivers.py
- test_chat_sessions_db.py
- generate_vocabulary_yaml
- Task 3: Return labels from the three analysis endpoints
- Path
- run_osspa_sync
- loader.py
- Retirement System
- parse_analysis_response
- analyze_architecture_item
- test_catalog_osspa_routes.py
- structlog
- Advisor v2 — Content-Type Drivers
- test_osspa_db.py
- handlers.py
- test_reporting.py
- router.py
- test_sweep_github_only_cancellation_preserves_revert_until_jira_available
- api.ts
- ECA Production Redesign Spec
- test_vocabulary_admin.py
- migrate_to_content_model.py
- analyzer.py
- Reporting MCP Data Sync
- test_status_visibility.py
- TestValidation
- SyncPage.tsx
- command
- extract_base_name
- _make_request
- pipeline.py
- test_nonprod.py
- test_retirement_pr_status.py
- test_showroom_rebuild.py
- cli.py
- services/catalog.py
- advisor.py
- test_llm_routing.py
- test_auth_routes.py
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
- deliver_pending_events
- patch
- rcars-login.sh
- ._set_showroom_override
- test_field_source_sync.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- MemoryArtifacts
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- ArchitectureDriver
- config.py
- test_llm_provider_status.py
- content_entities Table
- .close
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- test_drivers.py
- StatusPage.tsx
- test_api_infrastructure.py
- workload_scan
- test_orphan_cleanup.py
- retirement_cleanup.py
- .pool
- Decisions
- orchestrator.py
- test_vocabulary.py
- _build_windowed_metrics
- create_sse_response
- test_vocabulary_db.py
- main
- test_chat_handlers.py
- File map and verification conventions
- require_performance_view
- docker-entrypoint.sh
- Webhook Configuration Task
- test_chat_live.py
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
- TestGetNonprodBaseNames
- test_infrastructure.py
- test_showroom_reuse.py
- test_vocabulary.py
- Python Requirements Entry Point
- TestNonprodSchema
- hashlib
- _parse_sa_allowlist
- _find_keyword_ties
- OsspaSyncError
- test_start_retirement_holds_lock_while_creating_ticket
- Task 1: Database Schema and Methods
- mcp_query
- build_embedding_text
- Field Source Content
- test_chat_routing_golden.py
- workload_scan
- build_infrastructure_embedding_text
- Controlled Vocabulary Design
- services/__init__.py
- TestTokenExchange
- ensure_issue_event_comment
- psycopg
- test_refresh_merged_notice_does_not_complete_open_removal

## God Nodes (most connected - your core abstractions)
1. `Database` - 298 edges
2. `Settings` - 176 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `run_retirement_sweep()` - 39 edges
6. `seed()` - 38 edges
7. `scan_babylon_item()` - 37 edges
8. `create_app()` - 36 edges
9. `react` - 35 edges
10. `ResolvedShowroom` - 32 edges

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

## Communities (199 total, 61 thin omitted)

### Community 0 - "HandsOnDriver"
Cohesion: 0.16
Nodes (11): Modify, Task 3: Hands-on Driver, What Moves Into Drivers, _extract_duration_target(), HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale() (+3 more)

### Community 2 - "registry.ts"
Cohesion: 0.13
Nodes (22): InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps (+14 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.19
Nodes (19): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis (+11 more)

### Community 4 - "middleware/auth.py"
Cohesion: 0.16
Nodes (9): _check_api_key_role_ceiling(), _get_cached_role_assignments(), invalidate_role_assignments_cache(), _log_auth_decision(), require_admin(), require_curator(), _user_has_db_role(), _validate_api_key_cached() (+1 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (43): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, @types/react (+35 more)

### Community 6 - "test_test_content_exclusion.py"
Cohesion: 0.13
Nodes (16): extract_showroom_url(), _source_node(), ContentDeclaration, resolve_showroom_source(), SourceNode, test_legacy_url_extractor_does_not_pick_first_ambiguous_override(), legacy_test_item(), node() (+8 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.14
Nodes (12): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats(), test_idempotent_upsert() (+4 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.13
Nodes (23): add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis(), get_catalog_item() (+15 more)

### Community 9 - "admin.py"
Cohesion: 0.08
Nodes (36): add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs(), query_history() (+28 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.09
Nodes (22): event_time(), test_comment_missing_credentials_does_not_call_http(), unexpected(), test_database_no_jira_and_deleted_workflow_do_not_queue(), test_database_open_event_is_atomic_and_deduplicated(), test_database_rollout_cutoff_and_repeat_closures(), test_database_workflow_and_event_write_roll_back_together(), test_delivery_concurrent_senders_cannot_overtake_stream() (+14 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.11
Nodes (34): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+26 more)

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

### Community 17 - "app.py"
Cohesion: 0.10
Nodes (5): lifespan(), _get_user_key(), RequestLoggingMiddleware, RecommendationLowResponse, RecommendationMediumResponse

### Community 18 - "workload_scanner.py"
Cohesion: 0.08
Nodes (16): call_llm(), generate_embedding(), regenerate_embeddings(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products() (+8 more)

### Community 19 - "test_catalog_labels.py"
Cohesion: 0.06
Nodes (28): Review Focus, Task 1: Read and store Platform/TDP labels, Task 2: Union labels per base name, Task 4: Browse server-side filters and facets, Task 5: Shared frontend helpers and checkbox filter group, Task 7: Browse UI (provisional style), Task 8: Run locally, check, and prepare the PR, _seed_label_count_items() (+20 more)

### Community 20 - "routes/auth.py"
Cohesion: 0.18
Nodes (16): invalidate_api_key_cache(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token(), _user_max_role() (+8 more)

### Community 21 - "test_db.py"
Cohesion: 0.08
Nodes (12): db(), db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default() (+4 more)

### Community 22 - "database.py"
Cohesion: 0.13
Nodes (14): _authorized_promotion(), eligible(), _strip_embedding_filler(), _verified_signature(), analysis_artifacts_complete(), AnalysisSignature, effective_showroom_source(), is_content_excluded() (+6 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.10
Nodes (24): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), git() (+16 more)

### Community 24 - "react"
Cohesion: 0.07
Nodes (41): Task 8: Frontend Refactor, 5. Frontend Card Rendering, Display Config Structure, BlockErrorBoundary, Props, State, RecCardsBlock(), resolveBlockRenderer() (+33 more)

### Community 25 - "Settings"
Cohesion: 0.13
Nodes (19): list_role_assignments(), llm_provider_status(), fetch_litemaas_models(), _parse_csv(), Settings, test_admin_check(), test_chat_intent_roles_invalid_role_rejected(), test_chat_intent_roles_parse() (+11 more)

### Community 26 - "route"
Cohesion: 0.12
Nodes (16): _call_anthropic(), LLMResult, build_router_prompt(), _extract_json(), route(), llm(), test_examples_validate_as_router_output(), test_prompt_contains_every_intent_and_context() (+8 more)

### Community 27 - "test_auth_middleware.py"
Cohesion: 0.14
Nodes (8): _fetch_group_members(), require_auth(), _user_in_groups(), _mock_async_client_get(), _mock_group_response(), TestApiKeyRoleCeiling, TestGroupLookup, TestRequireAuth

### Community 28 - "schemas.py"
Cohesion: 0.07
Nodes (42): health(), readiness(), AgvPrResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse, CatalogStatsResponse (+34 more)

### Community 29 - "seed"
Cohesion: 0.18
Nodes (22): Task 2: Persist source provenance and enforce scoped analysis reuse, add_alias(), search(), test_exact_same_item_prod_requires_complete_matching_signature(), test_explicit_multihop_virtual_alias_is_recognized_and_hydrates_own_analysis(), test_independent_ids_keep_their_own_scores(), test_infrastructure_base_is_not_a_content_alias(), test_multiple_virtual_targets_are_not_selected_arbitrarily() (+14 more)

### Community 30 - "App.tsx"
Cohesion: 0.08
Nodes (37): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), API_DOCS_URL (+29 more)

### Community 31 - "settings.py"
Cohesion: 0.08
Nodes (20): _add_component(), get_logger(), _reorder_keys(), setup_logging(), WorkerContext, run_chat_turn(), on_progress(), run_retirement_sweep_job() (+12 more)

### Community 32 - "ops.py"
Cohesion: 0.12
Nodes (14): build_sandbox_summary(), scan_all_collections(), publish_progress(), _progress_bridge(), _publish(), run_babylon_pipeline(), run_catalog_refresh(), run_field_source_sync_job() (+6 more)

### Community 33 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 34 - "JobProgressRelay"
Cohesion: 0.15
Nodes (14): 4. SSE Streaming, Frontend Progress Display, What Stays Unchanged, JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 35 - "test_services.py"
Cohesion: 0.09
Nodes (13): Candidate, _call_rationale_single(), _format_single_candidate(), _run_catalog_second_pass(), test_candidate_similarity_pct(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports() (+5 more)

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

### Community 41 - "jira.py"
Cohesion: 0.06
Nodes (47): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+39 more)

### Community 42 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 43 - "Any"
Cohesion: 0.08
Nodes (5): Task 5: Keep recommendation identities within authorized relationships, _resolve_ci_references(), search(), test_legacy_test_sourced_wrapper_is_not_recommended(), test_test_item_cannot_seed_recommendation_neighbor_expansion()

### Community 44 - "test_analyzer.py"
Cohesion: 0.09
Nodes (27): check_showroom_stale(), classify_scan_error(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), hash_showroom_content(), parse_analysis_response(), _parse_nav_includes() (+19 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.25
Nodes (16): asset_type_tokens(), parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status(), test_normalize_row_builds_the_upsert_payload(), test_normalize_row_dedups_topics_from_solutions_and_verticals() (+8 more)

### Community 46 - "reporting_sync.py"
Cohesion: 0.17
Nodes (9): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs(), _percentile_rank() (+1 more)

### Community 47 - "api.ts"
Cohesion: 0.08
Nodes (57): Task 6: Wire filters into Performance, Non-Prod and Retirement, CollapsibleFilterGroup(), CollapsibleFilterGroupProps, render(), LabelFilterGroup(), LabelFilterGroupProps, fmtTargetDate(), isInProgress() (+49 more)

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
Cohesion: 0.16
Nodes (26): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), check_stale(), ignore_item(), link_jira(), LinkJiraRequest (+18 more)

### Community 52 - "test_drivers.py"
Cohesion: 0.14
Nodes (14): get_driver(), get_drivers_for_types(), format_triage_candidates(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_get_driver_architecture() (+6 more)

### Community 53 - "test_chat_sessions_db.py"
Cohesion: 0.17
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 54 - "generate_vocabulary_yaml"
Cohesion: 0.14
Nodes (5): _entries_to_dicts(), generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "Task 3: Return labels from the three analysis endpoints"
Cohesion: 0.13
Nodes (9): Task 3: Return labels from the three analysis endpoints, _extract_base_name_from_content_id(), performance_dashboard(), retirement_dashboard(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists() (+1 more)

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.37
Nodes (16): run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items(), test_missing_detail_page_marks_stale_and_skips() (+8 more)

### Community 58 - "loader.py"
Cohesion: 0.13
Nodes (11): _as_tuple(), _build_lookups(), _parse_entries(), _validate(), squash_key(), VocabEntry, Vocabulary, VocabularyError (+3 more)

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

### Community 63 - "structlog"
Cohesion: 0.21
Nodes (9): WorkerSettings, test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes(), test_worker_context_has_required_fields() (+1 more)

### Community 64 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.10
Nodes (19): 1. Content-Type Drivers, 3. Candidate Model, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy (+11 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.18
Nodes (9): _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_upsert_osspa_item_never_overwrites_llm_owned_fields(), test_upsert_osspa_item_unretires_on_reappearance() (+1 more)

### Community 66 - "handlers.py"
Cohesion: 0.11
Nodes (25): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+17 more)

### Community 67 - "test_reporting.py"
Cohesion: 0.12
Nodes (6): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), _recompute_windowed_scores(), TestComputePerformanceScore

### Community 68 - "router.py"
Cohesion: 0.14
Nodes (22): Chip, Envelope, RouterOutput, Scope, _expand_vocab_aliases(), _parse_catalog_url(), pattern_check(), resolve_and_verify() (+14 more)

### Community 69 - "test_sweep_github_only_cancellation_preserves_revert_until_jira_available"
Cohesion: 0.09
Nodes (11): test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), test_required_cancel_retains_workflow_on_jira_failure(), test_retired_items_cannot_be_cancelled() (+3 more)

### Community 70 - "api.ts"
Cohesion: 0.08
Nodes (26): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+18 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "test_vocabulary_admin.py"
Cohesion: 0.14
Nodes (4): clear_vocabulary_cache(), client(), TestRoleGating, TestVocabularyEndpoints

### Community 73 - "migrate_to_content_model.py"
Cohesion: 0.06
Nodes (33): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+25 more)

### Community 74 - "analyzer.py"
Cohesion: 0.10
Nodes (21): analysis_context_hash(), analysis_from_row(), analyze_showroom(), build_module_embedding_text(), compute_analysis_context_hash(), compute_analysis_input_hash(), compute_embedding_fingerprint(), _embedding_specs() (+13 more)

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
Cohesion: 0.31
Nodes (11): react, LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance() (+3 more)

### Community 79 - "command"
Cohesion: 0.15
Nodes (11): flag(), get_db(), infra_stats(), init_db(), note(), override_url(), set_content_path(), tag() (+3 more)

### Community 81 - "_make_request"
Cohesion: 0.21
Nodes (5): get_current_user(), _make_request(), TestApiKeyAuth, TestGetCurrentUser, TestProxySecretEnforcement

### Community 82 - "pipeline.py"
Cohesion: 0.11
Nodes (18): Task 6: Orchestrator + Pipeline Refactor, Task 7: Caller Integration + Cleanup, 2. Orchestrator and Pipeline, What Gets Deleted, _run_low(), registered_content_types(), QueryState, extract_urls() (+10 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.09
Nodes (12): get_workflow(), nonprod_dashboard(), _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists (+4 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.10
Nodes (26): run_retirement_sweep(), _sweep_context(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancellation_does_not_mark_concurrently_retired_item(), test_manual_pr_creation_respects_cleanup_lock(), test_refresh_does_not_retire_unmerged_or_unknown_pr(), test_required_failed_cancel_is_excluded_from_removal_and_retried_by_sweep(), test_required_merged_revert_cannot_bypass_jira_failure() (+18 more)

### Community 85 - "test_showroom_rebuild.py"
Cohesion: 0.17
Nodes (8): Task 6: Add a narrowly scoped reset and verify the full rebuild contract, snapshots(), test_dry_run_performs_no_writes(), test_execute_requires_scans_paused_confirmation(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data(), test_reset_rejects_non_babylon_or_missing_ids_atomically(), test_reset_rejects_running_or_queued_analysis_jobs()

### Community 86 - "cli.py"
Cohesion: 0.13
Nodes (7): infra_group(), osspa_group(), overlap_candidates_cmd(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 87 - "services/catalog.py"
Cohesion: 0.06
Nodes (25): Global Constraints, Anti-goals, Constraints, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+17 more)

### Community 88 - "advisor.py"
Cohesion: 0.12
Nodes (14): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+6 more)

### Community 89 - "test_llm_routing.py"
Cohesion: 0.25
Nodes (8): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it(), test_seeded_model_skips_temperature_on_first_call(), test_skips_temperature_on_later_calls_for_same_model()

### Community 90 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (4): client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.20
Nodes (16): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, LLM Provider Routing (LiteMaaS / Vertex AI), Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API (+8 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.08
Nodes (44): start_scan(), scan(), order_for_reuse(), reuse_key_from_signature(), showroom_reuse_key(), reuse_lock_id(), scan_babylon_item(), _scan_babylon_item() (+36 more)

### Community 94 - "seed_chat_fixtures"
Cohesion: 0.14
Nodes (15): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+7 more)

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
Cohesion: 0.26
Nodes (19): Task 1: Resolve content sources with explicit ownership, component_item_to_ci_name(), ComponentLink, node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous() (+11 more)

### Community 101 - "deliver_pending_events"
Cohesion: 0.14
Nodes (6): _print(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 102 - "patch"
Cohesion: 0.36
Nodes (4): _validate_sa_token(), _mock_async_client(), _mock_token_review_response(), TestValidateSaToken

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.19
Nodes (8): Task 2: Reporting Sync Job, _build_field_source_sql(), run_field_source_sync(), FakeSettings, _mock_mcp_query(), test_field_source_sync_inserts_rows(), test_field_source_sync_no_mcp(), test_field_source_sync_replaces_on_rerun()

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (12): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+4 more)

### Community 108 - "MemoryArtifacts"
Cohesion: 0.17
Nodes (3): MemoryArtifacts, scan(), run()

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "ArchitectureDriver"
Cohesion: 0.20
Nodes (8): ArchitectureDriver, _primary_asset_type(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 112 - "config.py"
Cohesion: 0.04
Nodes (18): create_app(), client(), client(), test_auth_me_unauthenticated(), app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey (+10 more)

### Community 113 - "test_llm_provider_status.py"
Cohesion: 0.25
Nodes (6): _make_client(), no_litemaas_fetch(), test_fallback_active_when_vertex_configured(), test_fallback_reported_not_active_by_default(), test_lists_model_for_every_llm_use(), test_litemaas_active_with_models()

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.06
Nodes (21): migrate(), db(), db(), db(), db(), db(), db(), db() (+13 more)

### Community 120 - "test_drivers.py"
Cohesion: 0.08
Nodes (14): Content-Type Drivers Implementation Plan, Create, Delete, Execution Notes, File Map, Global Constraints, Review Focus, Task 1: Candidate Model Refactor (+6 more)

### Community 121 - "StatusPage.tsx"
Cohesion: 0.22
Nodes (10): react-dom, vitest, LlmProviderCard(), LlmProviderStatus, LlmUse, status, USE_LABELS, CatalogStatus (+2 more)

### Community 122 - "test_api_infrastructure.py"
Cohesion: 0.22
Nodes (3): client(), seed_infrastructure(), test_sync_osspa_endpoint_enqueues_a_job()

### Community 123 - "workload_scan"
Cohesion: 0.14
Nodes (7): Data and Audit Trail, cli(), osspa_sync_cmd(), serve(), status(), vocab_stage_rescan(), vocab_unknowns()

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.15
Nodes (14): cancel_workflow(), check_pr_statuses(), get_issue_status(), _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr() (+6 more)

### Community 126 - ".pool"
Cohesion: 0.14
Nodes (4): db(), test_database_explicit_test_schema_reset_includes_delivery_queue(), db(), create()

### Community 127 - "Decisions"
Cohesion: 0.12
Nodes (3): Platform and TDP Filters Implementation Plan, Decisions, retirement_label()

### Community 128 - "orchestrator.py"
Cohesion: 0.20
Nodes (11): build_scaffold(), compose_answer(), _strip_formatting(), _help_answer(), process_turn(), _scope_echo(), followup_chips(), test_answer_failure_degrades_to_scaffold() (+3 more)

### Community 129 - "test_vocabulary.py"
Cohesion: 0.17
Nodes (4): build_analysis_prompt(), _canonical_content(), truncate_content(), TestPromptInjection

### Community 131 - "create_sse_response"
Cohesion: 0.25
Nodes (5): field_source_report(), overlap_assessment_detail(), overlap_report(), stream_job(), create_sse_response()

### Community 132 - "test_vocabulary_db.py"
Cohesion: 0.10
Nodes (5): TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched, TestUnknownTermsSchema

### Community 134 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 135 - "File map and verification conventions"
Cohesion: 0.25
Nodes (7): Execution handoff, File map and verification conventions, Global Constraints, Review Focus, Self-review, Showroom Analysis Isolation Implementation Plan, Task 4: Unify scan persistence and remove cross-item fan-out

### Community 139 - "test_chat_live.py"
Cohesion: 0.36
Nodes (4): _noop(), _settings(), test_live_item_facts_turn(), test_live_out_of_scope()

### Community 143 - "retirement-system.md"
Cohesion: 0.20
Nodes (16): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+8 more)

### Community 169 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 174 - "test_showroom_reuse.py"
Cohesion: 0.18
Nodes (17): Data Import, Task 3: Fetch the exact source and reject non-content inputs, git_repo(), prime(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_embedding_only_changes_repair_only_affected_artifacts(), test_every_changed_signature_input_prevents_donor_reuse() (+9 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.17
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 180 - "hashlib"
Cohesion: 0.29
Nodes (4): build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events()

### Community 183 - "OsspaSyncError"
Cohesion: 0.33
Nodes (3): fetch_palist_csv(), OsspaSyncError, _boom()

### Community 184 - "test_start_retirement_holds_lock_while_creating_ticket"
Cohesion: 0.50
Nodes (4): _approved_unstarted(), test_start_retirement_holds_lock_while_creating_ticket(), fake_create(), test_start_retirement_respects_workflow_lock()

### Community 186 - "mcp_query"
Cohesion: 0.13
Nodes (10): Field Source Content Report — Implementation Plan, Global Constraints, Task 3: API Endpoint, Task 4: Frontend Page, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, _mcp_call(), mcp_query() (+2 more)

### Community 188 - "Field Source Content"
Cohesion: 0.50
Nodes (4): API, Data Source, Field Source Content, Frontend

### Community 192 - "build_infrastructure_embedding_text"
Cohesion: 0.60
Nodes (3): build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

### Community 193 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 194 - "services/__init__.py"
Cohesion: 0.22
Nodes (4): test_already_closed_issue_needs_no_transition(), test_required_closure_selects_resolution_and_verifies_result(), request(), test_jira_close_reports_whether_it_transitioned()

### Community 196 - "ensure_issue_event_comment"
Cohesion: 0.12
Nodes (11): ensure_issue_event_comment(), client(), comments(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response() (+3 more)

### Community 197 - "psycopg"
Cohesion: 0.25
Nodes (3): db(), db(), seed_items()

## Knowledge Gaps
- **105 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1259 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `orchestrator.py`, `Database`, `middleware/auth.py`, `main`, `test_chat_handlers.py`, `test_test_content_exclusion.py`, `require_performance_view`, `admin.py`, `routes/catalog.py`, `test_chat_live.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `app.py`, `workload_scanner.py`, `routes/auth.py`, `database.py`, `route`, `schemas.py`, `seed`, `settings.py`, `Any`, `analysis.py`, `Task 3: Return labels from the three analysis endpoints`, `run_osspa_sync`, `test_chat_routing_golden.py`, `test_catalog_osspa_routes.py`, `workload_scan`, `analyze_architecture_item`, `structlog`, `handlers.py`, `router.py`, `ensure_issue_event_comment`, `test_vocabulary_admin.py`, `migrate_to_content_model.py`, `analyzer.py`, `command`, `_make_request`, `pipeline.py`, `test_retirement_pr_status.py`, `cli.py`, `services/catalog.py`, `advisor.py`, `test_llm_routing.py`, `test_auth_routes.py`, `test_showroom_scan.py`, `seed_chat_fixtures`, `deliver_pending_events`, `config.py`, `test_llm_provider_status.py`, `.close`, `test_api_infrastructure.py`, `workload_scan`?**
  _High betweenness centrality (0.166) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `Database` (e.g. with `Settings` and `AnalysisSignature`) actually correct?**
  _`Database` has 52 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _105 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.023172479694218824 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Database` to `orchestrator.py`, `test_vocabulary_db.py`, `main`, `db/__init__.py`, `test_retirement_jira_events.py`, `test_chat_live.py`, `test_overlap_assessment.py`, `app.py`, `workload_scanner.py`, `test_catalog_labels.py`, `test_db.py`, `database.py`, `Settings`, `settings.py`, `ops.py`, `_generate_key`, `Any`, `TestGetNonprodBaseNames`, `test_infrastructure.py`, `test_chat_sessions_db.py`, `_find_keyword_ties`, `test_start_retirement_holds_lock_while_creating_ticket`, `Task 1: Database Schema and Methods`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `test_field_source_db.py`, `test_osspa_db.py`, `handlers.py`, `router.py`, `psycopg`, `migrate_to_content_model.py`, `test_status_visibility.py`, `command`, `extract_base_name`, `pipeline.py`, `test_nonprod.py`, `test_retirement_pr_status.py`, `test_showroom_rebuild.py`, `test_showroom_scan.py`, `seed_chat_fixtures`, `deliver_pending_events`, `._set_showroom_override`, `test_field_source_sync.py`, `config.py`, `.close`, `test_api_infrastructure.py`, `workload_scan`, `.pool`, `Decisions`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Are the 68 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Should `registry.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.1310483870967742 - nodes in this community are weakly interconnected._