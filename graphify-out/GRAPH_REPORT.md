# Graph Report - rcars-advisory  (2026-10-28)

## Corpus Check
- 302 files · ~526,642 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 3654 nodes · 8910 edges · 178 communities (128 shown, 50 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 893 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ef3aaff5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- HandsOnDriver
- Database
- registry.ts
- Portfolio Architecture Ingest Design Spec
- _make_request
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
- services/catalog.py
- workload_scanner.py
- test_catalog_labels.py
- routes/auth.py
- test_db.py
- effective_showroom_source
- test_osspa_adoc.py
- react
- Settings
- config.py
- router.py
- schemas.py
- seed
- App.tsx
- settings.py
- ops.py
- _extrapolate_count
- JobProgressRelay
- test_services.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- jira.py
- _sync_nonprod_usage
- test_sweep_github_only_cancellation_preserves_revert_until_jira_available
- analyzer.py
- test_osspa_csv.py
- reporting_sync.py
- api.ts
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- analysis.py
- pytest
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
- run_category
- patch
- api.ts
- ECA Production Redesign Spec
- test_vocabulary_admin.py
- json
- _user_has_db_role
- Reporting MCP Data Sync
- test_status_visibility.py
- TestValidation
- SyncPage.tsx
- cli.py
- extract_base_name
- typing
- structlog
- test_nonprod.py
- test_retirement_pr_status.py
- recommendations.py
- cli.py
- CatalogReader
- advisor.py
- TestVocabularyEndpoints
- rationale.py
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
- _print
- TestBuildWindowedMetrics
- rcars-login.sh
- ._set_showroom_override
- database.py
- API Key Authentication
- RCARS OCP Deployment Playbook
- dependencies
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- ArchitectureDriver
- app.py
- status
- content_entities Table
- .close
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- test_drivers.py
- ContentTypeDriver
- build_sandbox_summary
- test_orphan_cleanup.py
- retirement_cleanup.py
- test_field_source_sync.py
- devDependencies
- test_vocabulary.py
- extract_catalog_item
- TestRecordUnknownTerm
- build_analysis_prompt
- test_chat_handlers.py
- File map and verification conventions
- test_auth_routes.py
- docker-entrypoint.sh
- Webhook Configuration Task
- retirement_dashboard
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
- TestGetNonprodBaseNames
- test_showroom_reuse.py
- build_embedding_text
- Python Requirements Entry Point
- hashlib
- Task 1: Database Schema and Methods
- Field Source Content
- mcp_query

## God Nodes (most connected - your core abstractions)
1. `Database` - 297 edges
2. `Settings` - 172 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 53 edges
5. `run_retirement_sweep()` - 39 edges
6. `seed()` - 38 edges
7. `scan_babylon_item()` - 37 edges
8. `react` - 35 edges
9. `create_app()` - 34 edges
10. `ResolvedShowroom` - 32 edges

## Surprising Connections (you probably didn't know these)
- `Task 3: API Endpoint` --references--> `FieldSourceResponse`  [INFERRED]
  docs/superpowers/plans/2026-09-21-field-source-content-report.md → src/api/rcars/api/schemas.py
- `Data and Audit Trail` --references--> `status()`  [INFERRED]
  docs/architecture/retirement-system.md → src/api/rcars/cli.py
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

## Communities (178 total, 50 thin omitted)

### Community 0 - "HandsOnDriver"
Cohesion: 0.15
Nodes (10): Task 3: Hands-on Driver, What Moves Into Drivers, _extract_duration_target(), HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming() (+2 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (7): Database, _do(), _resolve_ci_references(), main(), test_advisory_lock_is_not_reentrant_across_sessions(), test_database_explicit_test_schema_reset_includes_delivery_queue(), test_script_rejects_selection_with_no_showroom_items()

### Community 2 - "registry.ts"
Cohesion: 0.12
Nodes (23): InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps (+15 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.17
Nodes (20): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis, OSSPA GitLab Repositories (+12 more)

### Community 4 - "_make_request"
Cohesion: 0.14
Nodes (7): get_current_user(), _make_request(), TestApiKeyAuth, TestGetCurrentUser, TestProxySecretEnforcement, TestRequireAuth, TestRequirePerformanceView

### Community 5 - "devDependencies"
Cohesion: 0.08
Nodes (23): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, @types/react (+15 more)

### Community 6 - "test_test_content_exclusion.py"
Cohesion: 0.11
Nodes (19): ContentDeclaration, resolve_showroom_source(), unresolved(), walk(), SourceNode, legacy_test_item(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes() (+11 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.13
Nodes (14): overlap_report(), generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), db(), seed_items(), test_generates_candidates_above_threshold() (+6 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.13
Nodes (23): add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis(), get_catalog_item() (+15 more)

### Community 9 - "admin.py"
Cohesion: 0.13
Nodes (24): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+16 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.06
Nodes (32): ensure_issue_event_comment(), comments(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response() (+24 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.15
Nodes (14): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+6 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.11
Nodes (34): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+26 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (24): assess_overlap(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector(), _seed_overlap_pair() (+16 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (4): derive_status(), retirement_label(), TestDeriveStatus, TestStepOrder

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 17 - "services/catalog.py"
Cohesion: 0.12
Nodes (9): _apply_component_inheritance(), _collect_bases(), component_item_to_ci_name(), _content_fields(), extract_showroom_url(), parse_workload_fqcn(), _resolve_template_var(), _source_node() (+1 more)

### Community 18 - "workload_scanner.py"
Cohesion: 0.07
Nodes (19): build_infrastructure_embedding_text(), ls_remote_sha(), _resolve_ref_from_lookup(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products() (+11 more)

### Community 19 - "test_catalog_labels.py"
Cohesion: 0.09
Nodes (19): Review Focus, Task 2: Union labels per base name, Task 4: Browse server-side filters and facets, Task 5: Shared frontend helpers and checkbox filter group, Task 7: Browse UI (provisional style), Task 8: Run locally, check, and prepare the PR, test_facets_platforms_and_tdps(), test_filter_groups_and() (+11 more)

### Community 20 - "routes/auth.py"
Cohesion: 0.16
Nodes (17): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+9 more)

### Community 21 - "test_db.py"
Cohesion: 0.08
Nodes (11): db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default(), test_filtered_catalog_pagination() (+3 more)

### Community 22 - "effective_showroom_source"
Cohesion: 0.16
Nodes (11): classify_scan_error(), regenerate_embeddings(), _authorized_promotion(), eligible(), _verified_signature(), _scan_babylon_item(), _snapshot(), analysis_generation() (+3 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.07
Nodes (41): Task 8: Frontend Refactor, 5. Frontend Card Rendering, Display Config Structure, react, BlockErrorBoundary, Props, State, CATEGORY_LABELS (+33 more)

### Community 25 - "Settings"
Cohesion: 0.12
Nodes (20): list_role_assignments(), llm_provider_status(), fetch_litemaas_models(), _parse_csv(), Settings, migrate(), test_admin_check(), test_chat_intent_roles_invalid_role_rejected() (+12 more)

### Community 26 - "config.py"
Cohesion: 0.11
Nodes (21): _call_anthropic(), _call_litemaas(), call_llm(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), _expand_vocab_aliases() (+13 more)

### Community 27 - "router.py"
Cohesion: 0.09
Nodes (38): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+30 more)

### Community 28 - "schemas.py"
Cohesion: 0.06
Nodes (61): field_source_report(), nonprod_dashboard(), overlap_assessment_detail(), _sort_empty_last(), health(), readiness(), AgvPrResponse, AuthMeResponse (+53 more)

### Community 29 - "seed"
Cohesion: 0.09
Nodes (31): Task 2: Persist source provenance and enforce scoped analysis reuse, Task 6: Add a narrowly scoped reset and verify the full rebuild contract, ResolvedShowroom, snapshots(), test_dry_run_performs_no_writes(), test_execute_requires_scans_paused_confirmation(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data() (+23 more)

### Community 30 - "App.tsx"
Cohesion: 0.05
Nodes (55): @patternfly/react-core, react-dom, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo() (+47 more)

### Community 31 - "settings.py"
Cohesion: 0.13
Nodes (13): _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url() (+5 more)

### Community 32 - "ops.py"
Cohesion: 0.11
Nodes (18): batch_assess_overlaps(), publish_progress(), WorkerContext, run_chat_turn(), on_progress(), _progress_bridge(), _publish(), run_babylon_pipeline() (+10 more)

### Community 34 - "JobProgressRelay"
Cohesion: 0.13
Nodes (15): Frontend Progress Display, What Stays Unchanged, stream_job(), create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives() (+7 more)

### Community 35 - "test_services.py"
Cohesion: 0.17
Nodes (9): _run_catalog_second_pass(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published(), test_query_state_defaults(), test_three_layer_workload_propagation() (+1 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.10
Nodes (21): Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy (+13 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.13
Nodes (5): load_vocabulary(), _noise_variants(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "_generate_key"
Cohesion: 0.10
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "jira.py"
Cohesion: 0.05
Nodes (48): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+40 more)

### Community 42 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 43 - "test_sweep_github_only_cancellation_preserves_revert_until_jira_available"
Cohesion: 0.11
Nodes (10): test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), test_required_cancel_retains_workflow_on_jira_failure(), test_retired_items_cannot_be_cancelled() (+2 more)

### Community 44 - "analyzer.py"
Cohesion: 0.06
Nodes (43): analysis_context_hash(), analysis_from_row(), analyze_showroom(), build_module_embedding_text(), _canonical_content(), check_showroom_stale(), clone_showroom(), compute_analysis_context_hash() (+35 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (19): asset_type_tokens(), fetch_palist_csv(), OsspaSyncError, parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status() (+11 more)

### Community 46 - "reporting_sync.py"
Cohesion: 0.16
Nodes (11): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _build_windowed_metrics(), _merge_published_base_pairs() (+3 more)

### Community 47 - "api.ts"
Cohesion: 0.09
Nodes (53): Task 6: Wire filters into Performance, Non-Prod and Retirement, CollapsibleFilterGroup(), CollapsibleFilterGroupProps, render(), LabelFilterGroup(), LabelFilterGroupProps, fmtTargetDate(), isInProgress() (+45 more)

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
Cohesion: 0.12
Nodes (27): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_stale(), ignore_item(), link_jira() (+19 more)

### Community 52 - "pytest"
Cohesion: 0.05
Nodes (17): WorkerSettings, client(), app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders (+9 more)

### Community 53 - "test_chat_sessions_db.py"
Cohesion: 0.17
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 54 - "generate_vocabulary_yaml"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "Task 3: Return labels from the three analysis endpoints"
Cohesion: 0.10
Nodes (9): Global Constraints, Platform and TDP Filters Implementation Plan, Task 3: Return labels from the three analysis endpoints, Decisions, _get_label(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels() (+1 more)

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

### Community 63 - "structlog"
Cohesion: 0.28
Nodes (6): test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes()

### Community 64 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.18
Nodes (10): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Goals, Non-Goals, Parallel Pipeline Instances (+2 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.24
Nodes (8): _row(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_upsert_osspa_item_never_overwrites_llm_owned_fields(), test_upsert_osspa_item_unretires_on_reappearance(), test_upsert_osspa_item_writes_all_three_rows()

### Community 66 - "handlers.py"
Cohesion: 0.12
Nodes (18): get_item_workloads(), get_performance_scores(), _prefix_overlap(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+10 more)

### Community 67 - "test_reporting.py"
Cohesion: 0.13
Nodes (5): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), TestComputePerformanceScore

### Community 68 - "run_category"
Cohesion: 0.15
Nodes (17): Modify, Task 6: Orchestrator + Pipeline Refactor, 1. Content-Type Drivers, 2. Orchestrator and Pipeline, 4. SSE Streaming, 6. Unified Serialization, Adding a New Content Type, Design (+9 more)

### Community 69 - "patch"
Cohesion: 0.11
Nodes (12): _fetch_group_members(), _parse_sa_allowlist(), _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response() (+4 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): Task 4: Frontend Page, vitest, findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate() (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "test_vocabulary_admin.py"
Cohesion: 0.32
Nodes (3): clear_vocabulary_cache(), client(), TestRoleGating

### Community 73 - "json"
Cohesion: 0.07
Nodes (33): cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists(), _connect() (+25 more)

### Community 74 - "_user_has_db_role"
Cohesion: 0.23
Nodes (3): _get_cached_role_assignments(), _user_has_db_role(), TestDbRoleCheck

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
Cohesion: 0.09
Nodes (20): cli(), flag(), get_db(), infra_stats(), init_db(), note(), osspa_sync_cmd(), overlap_candidates_cmd() (+12 more)

### Community 80 - "extract_base_name"
Cohesion: 0.16
Nodes (4): extract_base_name(), _window_start(), TestExtractBaseName, TestWindowStart

### Community 81 - "typing"
Cohesion: 0.18
Nodes (3): _init_drivers(), _register(), registered_content_types()

### Community 82 - "structlog"
Cohesion: 0.14
Nodes (6): generate_embedding(), _get_embedding_client(), QueryState, search(), _strip_embedding_filler(), run_recommendation()

### Community 83 - "test_nonprod.py"
Cohesion: 0.08
Nodes (11): get_workflow(), _nonprod_retirement_metrics(), _retirement_metrics(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestNonprodWindows (+3 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.09
Nodes (27): run_retirement_sweep(), _sweep_context(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancellation_does_not_mark_concurrently_retired_item(), test_refresh_does_not_retire_unmerged_or_unknown_pr(), test_refresh_merged_notice_does_not_complete_open_removal(), test_required_failed_cancel_is_excluded_from_removal_and_retried_by_sweep(), test_required_merged_revert_cannot_bypass_jira_failure() (+19 more)

### Community 85 - "recommendations.py"
Cohesion: 0.17
Nodes (4): get_recommendations(), RecommendationRequest, _run_low(), _run_medium()

### Community 86 - "cli.py"
Cohesion: 0.15
Nodes (6): infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 87 - "CatalogReader"
Cohesion: 0.18
Nodes (8): CatalogReader, collect(), load(), extract_base_ci_refs(), extract_infrastructure_metadata(), is_agnosticd_v2(), test_explicit_child_stage_applies_to_nested_component_references(), test_explicit_stage_infrastructure_chain_without_showroom_is_not_failure()

### Community 88 - "advisor.py"
Cohesion: 0.13
Nodes (18): _check_api_key_role_ceiling(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), require_performance_view(), _validate_api_key_cached(), ChatRequest (+10 more)

### Community 90 - "rationale.py"
Cohesion: 0.20
Nodes (9): Task 5: Triage + Rationale Driver Hooks, Task 7: Caller Integration + Cleanup, _primary_asset_type(), _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis(), _format_single_candidate(), generate_content_gaps() (+1 more)

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (18): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Babylon CRD Catalog Pipeline, LLM Provider Routing (LiteMaaS / Vertex AI), Nightly Maintenance Pipeline, Performance Scoring System (+10 more)

### Community 92 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.09
Nodes (40): Task 4: Unify scan persistence and remove cross-item fan-out, start_scan(), InvalidShowroomRef, order_for_reuse(), reuse_key_from_signature(), showroom_reuse_key(), scan_babylon_item(), run_stale_check() (+32 more)

### Community 94 - "seed_chat_fixtures"
Cohesion: 0.11
Nodes (19): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+11 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

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
Cohesion: 0.28
Nodes (19): Task 1: Resolve content sources with explicit ownership, ComponentLink, item_family_key(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous() (+11 more)

### Community 101 - "_print"
Cohesion: 0.14
Nodes (6): _print(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "._set_showroom_override"
Cohesion: 0.13
Nodes (5): _do(), db(), db(), db(), create()

### Community 105 - "database.py"
Cohesion: 0.05
Nodes (7): settings(), test_routing_golden(), client(), test_field_source_route_registered(), TestGetUnknownTerms, TestResolveUnknownTerm, TestUnknownTermsSchema

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (12): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+4 more)

### Community 108 - "dependencies"
Cohesion: 0.29
Nodes (7): dependencies, @patternfly/react-core, @patternfly/react-icons, @patternfly/react-table, react, react-dom, react-router-dom

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 111 - "ArchitectureDriver"
Cohesion: 0.17
Nodes (9): ArchitectureDriver, Candidate, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance() (+1 more)

### Community 112 - "app.py"
Cohesion: 0.06
Nodes (13): create_app(), lifespan(), _get_user_key(), RequestLoggingMiddleware, client(), test_sync_osspa_endpoint_enqueues_a_job(), client(), test_auth_me_unauthenticated() (+5 more)

### Community 113 - "status"
Cohesion: 0.33
Nodes (5): 3. Candidate Model, Candidate Dataclass, `content_entities` (shared table — all types), Source-specific tables, status()

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.07
Nodes (22): seed_infrastructure(), db(), db(), db(), db(), db(), db(), db() (+14 more)

### Community 120 - "test_drivers.py"
Cohesion: 0.14
Nodes (14): get_driver(), get_drivers_for_types(), format_triage_candidates(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_get_driver_architecture() (+6 more)

### Community 121 - "ContentTypeDriver"
Cohesion: 0.09
Nodes (11): Content-Type Drivers Implementation Plan, Create, Delete, Execution Notes, File Map, Global Constraints, Review Focus, Task 1: Candidate Model Refactor (+3 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.16
Nodes (16): check_pr_statuses(), _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable() (+8 more)

### Community 126 - "test_field_source_sync.py"
Cohesion: 0.19
Nodes (8): Task 2: Reporting Sync Job, _build_field_source_sql(), run_field_source_sync(), FakeSettings, _mock_mcp_query(), test_field_source_sync_inserts_rows(), test_field_source_sync_no_mcp(), test_field_source_sync_replaces_on_rerun()

### Community 127 - "devDependencies"
Cohesion: 0.15
Nodes (13): devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @types/react, @types/react-dom (+5 more)

### Community 129 - "test_vocabulary.py"
Cohesion: 0.17
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 131 - "extract_catalog_item"
Cohesion: 0.12
Nodes (14): Task 1: Read and store Platform/TDP labels, Anti-goals, Constraints, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+6 more)

### Community 133 - "build_analysis_prompt"
Cohesion: 0.20
Nodes (3): build_analysis_prompt(), truncate_content(), TestPromptInjection

### Community 134 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 135 - "File map and verification conventions"
Cohesion: 0.25
Nodes (7): Execution handoff, File map and verification conventions, Global Constraints, Review Focus, Self-review, Showroom Analysis Isolation Implementation Plan, Task 5: Keep recommendation identities within authorized relationships

### Community 136 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (4): client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 139 - "retirement_dashboard"
Cohesion: 0.33
Nodes (3): _extract_base_name_from_content_id(), retirement_dashboard(), TestRetirementDashboardMetrics

### Community 143 - "retirement-system.md"
Cohesion: 0.16
Nodes (21): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+13 more)

### Community 174 - "test_showroom_reuse.py"
Cohesion: 0.11
Nodes (18): Task 3: Fetch the exact source and reject non-content inputs, MemoryArtifacts, prime(), scan(), run(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_embedding_only_changes_repair_only_affected_artifacts() (+10 more)

### Community 180 - "hashlib"
Cohesion: 0.21
Nodes (5): build_jira_event(), deliver_pending_events(), _deliver_pending_events(), event_timestamp(), observe_pr_events()

### Community 190 - "Field Source Content"
Cohesion: 0.25
Nodes (7): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git()

### Community 192 - "mcp_query"
Cohesion: 0.14
Nodes (9): Field Source Content Report — Implementation Plan, Global Constraints, Task 3: API Endpoint, Task 5: Routing and Sidebar, Task 6: End-to-End Verification, _mcp_call(), mcp_query(), TestMcpQueryOrdering (+1 more)

## Knowledge Gaps
- **105 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1241 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **50 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `db/__init__.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `derive_status`, `workload_scanner.py`, `test_catalog_labels.py`, `test_db.py`, `Settings`, `router.py`, `seed`, `settings.py`, `ops.py`, `_generate_key`, `analyzer.py`, `TestGetNonprodBaseNames`, `pytest`, `test_chat_sessions_db.py`, `Task 3: Return labels from the three analysis endpoints`, `Task 1: Database Schema and Methods`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `test_osspa_db.py`, `handlers.py`, `run_category`, `test_status_visibility.py`, `cli.py`, `extract_base_name`, `structlog`, `test_nonprod.py`, `test_retirement_pr_status.py`, `rationale.py`, `test_showroom_scan.py`, `seed_chat_fixtures`, `_print`, `._set_showroom_override`, `database.py`, `app.py`, `.close`, `retirement_cleanup.py`, `test_field_source_sync.py`?**
  _High betweenness centrality (0.159) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `Database` (e.g. with `Settings` and `AnalysisSignature`) actually correct?**
  _`Database` has 52 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _105 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.019214255045083728 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `Database`, `_make_request`, `test_chat_handlers.py`, `test_test_content_exclusion.py`, `routes/catalog.py`, `admin.py`, `test_auth_routes.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `routes/auth.py`, `config.py`, `router.py`, `schemas.py`, `seed`, `settings.py`, `ops.py`, `analyzer.py`, `analysis.py`, `pytest`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `handlers.py`, `run_category`, `test_vocabulary_admin.py`, `cli.py`, `structlog`, `test_retirement_pr_status.py`, `recommendations.py`, `advisor.py`, `AdocRead`, `test_showroom_scan.py`, `seed_chat_fixtures`, `_print`, `database.py`, `app.py`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Are the 68 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Should `registry.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._