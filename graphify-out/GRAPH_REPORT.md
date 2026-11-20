# Graph Report - rhdpcd-2229  (2026-11-20)

## Corpus Check
- 291 files · ~316,779 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4079 nodes · 10094 edges · 204 communities (149 shown, 55 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1048 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4395c344`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _FakeResponse
- Database
- react
- Portfolio Architecture Ingest Design Spec
- common.yml
- devDependencies
- cli.py
- db/__init__.py
- routes/catalog.py
- admin.py
- test_retirement_jira_events.py
- Chat Router LLM
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_description_analysis.py
- ops.py
- workload_scanner.py
- test_db.py
- routes/auth.py
- .upsert_babylon_catalog_item
- .is_admin
- test_osspa_adoc.py
- react
- Settings
- re
- test_showroom_source.py
- schemas.py
- seed
- App.tsx
- settings.py
- test_agv_access.py
- advisor.py
- JobProgressRelay
- ContentAnalysisPage.tsx
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- test_jira_service.py
- structlog
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
- Vocabulary
- performance_dashboard
- osspa_sync.py
- run_osspa_sync
- loader.py
- Retirement System
- parse_analysis_response
- analyze_architecture_item
- test_catalog_osspa_routes.py
- SyncPage.tsx
- with
- test_osspa_db.py
- Candidate
- reporting_sync.py
- RouterOutput
- test_db.py
- api.ts
- ECA Production Redesign Spec
- test_chat_live.py
- sync_opl_vocabulary.py
- analyzer.py
- test_auth_middleware.py
- .get_content_entity
- TestValidation
- .upsert_babylon_catalog_item
- command
- run_category
- test_test_content_exclusion.py
- set_analysis_source
- test_nonprod.py
- test_retirement_pr_status.py
- jira.py
- _make_request
- _print
- ArchitectureDriver
- build_retirement_description
- orchestrator.py
- System Design Architecture Doc
- AdocRead
- test_showroom_scan.py
- asyncio
- Showroom analysis isolation
- Scan Pipeline
- _build_windowed_metrics
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- Design
- Candidate
- TestVocabularyEndpoints
- rcars-login.sh
- test_chat_handlers.py
- test_field_source_sync.py
- test_retirement_workflow.py
- RCARS OCP Deployment Playbook
- test_workers.py
- effective_analysis_source
- Rec Card Duration and Best Fit Spec
- rcars-login.py
- pytest
- ResolvedShowroom
- content_entities Table
- .close
- Deploy Docs GitHub Actions Workflow
- Change Detection
- _user_has_db_role
- Overlap Detection Redesign
- test_reporting.py
- recommendations.py
- build_embedding_text
- test_drivers.py
- test_orphan_cleanup.py
- retirement_cleanup.py
- test_llm_routing.py
- command
- middleware/auth.py
- vocabulary.yaml
- pre_tasks
- Content Owner Model for Virtual CIs — Design
- is_content_excluded
- _sync_nonprod_usage
- handlers.py
- .create_job
- test_edit_update_skips_cancelled_workflows
- docker-entrypoint.sh
- RCARS — Agent Instructions
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
- patch
- block
- post_tasks
- action_verbs
- build_sandbox_summary
- build_description_prompt
- Python Dependency Manifest (requirements.lock)
- test_llm_provider_status.py
- .test_ignored_term_creates_no_row
- deploy.yml
- LLM Overlap Assessment Design
- rcars
- rcars
- tasks
- Match Event Prompt Template
- extract_base_name
- _parse_sa_allowlist
- test_content_owner.py
- test_vocabulary.py
- Python Requirements Entry Point
- build_infrastructure_embedding_text
- test_cron_nightly_pipeline_binds_created_job_id
- TestTokenExchange
- rate_limit.py
- require_performance_view
- ignored_terms
- extract_catalog_item
- mcp_query
- readiness
- TestGetNonprodBaseNames
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- solutions
- ansible.builtin.assert
- content_similarity Table
- TestCreateApiKey
- test_infrastructure.py
- TestRevokeApiKey
- TestUnauthenticatedAccess
- TestRoleCeiling
- TestPromptInjection
- database.py
- Browse Page Redesign Spec

## God Nodes (most connected - your core abstractions)
1. `Database` - 299 edges
2. `Settings` - 179 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 47 edges
5. `seed()` - 46 edges
6. `scan_babylon_item()` - 43 edges
7. `create_app()` - 41 edges
8. `run_retirement_sweep()` - 40 edges
9. `ResolvedShowroom` - 37 edges
10. `react` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Summary` --references--> `isArchitecture()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/frontend/src/pages/browse/helpers.ts
- `Curator edits` --references--> `content_owner()`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py
- `Open Questions / Risks` --references--> `build_retirement_description()`  [INFERRED]
  docs/superpowers/specs/agv-retire-integration.md → src/api/rcars/services/jira.py
- `Management RBAC Bootstrap Task` --implements--> `RCARS Authentication Model`  [INFERRED]
  ansible/tasks/mgmt-rbac.yml → docs/architecture/system-design.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Content Analysis Pipeline (Vocabulary + Showroom Analysis + Overlap Assessment)** — src_api_rcars_data_vocabulary_controlled_vocabulary, src_api_rcars_prompts_analyze_showroom_analysis_prompt, src_api_rcars_prompts_overlap_assessment_overlap_prompt, src_api_rcars_prompts_analyze_showroom_learning_objectives [EXTRACTED 0.95]
- **System Evolution from Monolith to Multi-Tier** — docs_superpowers_specs_2026-04-07-eca-production-redesign-design, docs_superpowers_specs_2026-04-08-rcars-plan3a-web-ui-design, docs_superpowers_specs_2026-04-25-rearchitecture-api-design, concept_rearchitecture [EXTRACTED 0.95]
- **OSSPA Ingest Stack — CSV + Clone + Upsert + Analyze + Embed** — claude_md_osspa_sync_pipeline, claude_md_palist_csv, claude_md_osspa_gitlab_repos, claude_md_portfolio_architectures_table, claude_md_architecture_analysis_table, claude_md_content_entities_table, claude_md_llm_architecture_analysis, claude_md_embedding_model_nomic [EXTRACTED 0.95]
- **Multi-Intent Chat System** — docs_architecture_advisor_chat_router, docs_architecture_advisor_chat_intent_recommend, docs_architecture_advisor_chat_intent_overlap, docs_architecture_advisor_chat_intent_performance, docs_architecture_advisor_chat_intent_infrastructure, docs_architecture_advisor_chat_intent_item_facts [EXTRACTED 1.00]
- **Ansible Deployment Pipeline** — ansible_deploy_playbook, ansible_tasks_apply_infra, ansible_tasks_apply_manifests, ansible_tasks_build_api, ansible_tasks_build_frontend, ansible_tasks_smoke_test, ansible_tasks_namespace, ansible_vars_common [EXTRACTED 1.00]
- **Generalized Content Model Core Tables** — docs_superpowers_specs_2026_07_20_generalized_content_model_design_content_entities, docs_superpowers_specs_2026_07_20_generalized_content_model_design_babylon_items, docs_superpowers_specs_2026_07_20_generalized_content_model_design_embeddings, docs_superpowers_specs_2026_07_20_generalized_content_model_design_performance_channels [EXTRACTED 1.00]
- **RCARS Core Four Deployments on OpenShift** — claude_md_rcars_react_spa, claude_md_rcars_fastapi_api, claude_md_rcars_scan_worker, claude_md_rcars_recommend_worker, claude_md_rcars_postgresql, claude_md_rcars_redis [EXTRACTED 1.00]
- **Three-Phase Recommendation Pipeline** — docs_architecture_recommendation_engine_vector_search, docs_architecture_recommendation_engine_haiku_triage, docs_architecture_recommendation_engine_sonnet_rationale [EXTRACTED 1.00]
- **RCARS Taxonomy System (Products, Solutions, Verticals, Platforms, Difficulty)** — src_api_rcars_data_vocabulary_products_taxonomy, src_api_rcars_data_vocabulary_solutions_taxonomy, src_api_rcars_data_vocabulary_verticals_taxonomy, src_api_rcars_data_vocabulary_platforms_taxonomy, src_api_rcars_data_vocabulary_difficulty_levels [EXTRACTED 1.00]
- **Content Visibility Gate — Status + Vector Search + Browse** — claude_md_content_entities_status, claude_md_vector_similarity_search, claude_md_browse_integration, claude_md_content_entities_table [INFERRED 0.85]
- **LLM Infrastructure (Anthropic + OpenAI SDKs + Prompt Templates)** — src_api_requirements_lock_anthropic, src_api_requirements_lock_openai, src_api_rcars_prompts_analyze_showroom_analysis_prompt, src_api_rcars_prompts_overlap_assessment_overlap_prompt [INFERRED 0.85]
- **Authentication and Access Control System** — docs_superpowers_specs_2026_07_03_api_authentication_design_api_keys, docs_superpowers_specs_2026_07_03_api_authentication_design_oauth_login, docs_superpowers_specs_2026_07_03_api_authentication_design_proxy_verification, docs_superpowers_specs_2026_08_05_role_assignments_design_role_assignments_table [INFERRED 0.95]
- **Recommendation Pipeline LLM Prompts** — src_api_rcars_prompts_triage, src_api_rcars_prompts_rationale, src_api_rcars_prompts_rationale_single, src_api_rcars_prompts_rationale_synthesis [INFERRED 0.95]

## Communities (204 total, 55 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.11
Nodes (17): _jira_request(), _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry() (+9 more)

### Community 1 - "Database"
Cohesion: 0.03
Nodes (5): Database, _do(), test_advisor_session(), test_enrichment_tags(), test_advisory_lock_is_not_reentrant_across_sessions()

### Community 2 - "react"
Cohesion: 0.07
Nodes (37): react, BlockErrorBoundary, Props, State, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock() (+29 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.15
Nodes (21): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis (+13 more)

### Community 4 - "common.yml"
Cohesion: 0.03
Nodes (58): admin_emails, api_cpu_limit, api_cpu_request, api_memory_limit, api_memory_request, api_replicas, app_name, app_port (+50 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (49): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, react-dom (+41 more)

### Community 6 - "cli.py"
Cohesion: 0.13
Nodes (9): concurrency, cancel-in-progress, group, infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group() (+1 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.17
Nodes (11): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats(), test_idempotent_upsert() (+3 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.12
Nodes (30): add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item(), get_analysis() (+22 more)

### Community 9 - "admin.py"
Cohesion: 0.13
Nodes (24): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+16 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.06
Nodes (44): ensure_issue_event_comment(), jira_auth_configured(), build_jira_event(), deliver_pending_events(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), client() (+36 more)

### Community 11 - "Chat Router LLM"
Cohesion: 0.33
Nodes (6): Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, Infrastructure Embedding Search Design

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (24): assess_overlap(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector(), _seed_overlap_pair() (+16 more)

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_description_analysis.py"
Cohesion: 0.15
Nodes (36): analyze_description(), add_description_item(), add_item(), analyzed_description_item(), mock_analysis(), persist_result(), refresh_item(), seed_artifacts() (+28 more)

### Community 17 - "ops.py"
Cohesion: 0.10
Nodes (20): batch_assess_overlaps(), run_field_source_sync(), scan_all_collections(), publish_progress(), with_job_context(), WorkerContext, _progress_bridge(), _publish() (+12 more)

### Community 18 - "workload_scanner.py"
Cohesion: 0.07
Nodes (18): clone_showroom(), _is_github_throttle(), ls_remote_sha(), _resolve_ref_from_lookup(), _run_git_with_retry(), analyze_config(), analyze_role(), discover_roles() (+10 more)

### Community 19 - "test_db.py"
Cohesion: 0.08
Nodes (15): _seed_label_count_items(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none(), test_label_counts_follow_other_filters(), test_label_counts_follow_search() (+7 more)

### Community 20 - "routes/auth.py"
Cohesion: 0.19
Nodes (15): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+7 more)

### Community 21 - ".upsert_babylon_catalog_item"
Cohesion: 0.16
Nodes (15): test_retire_missing_babylon_ignores_other_sources(), _arch(), _seed_nonprod(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators() (+7 more)

### Community 22 - ".is_admin"
Cohesion: 0.16
Nodes (9): get_query_result(), get_session(), list_sessions(), stream_query(), submit_chat(), submit_query(), get_recommendations(), RecommendationRequest (+1 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.10
Nodes (24): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), git() (+16 more)

### Community 24 - "react"
Cohesion: 0.13
Nodes (23): buildUrl(), FALLBACK_FORMAT_LABELS, FORMAT_COLORS, RecCard(), RecCardProps, CollapsibleTier(), RecCardList(), RecCardListProps (+15 more)

### Community 25 - "Settings"
Cohesion: 0.08
Nodes (26): list_role_assignments(), llm_provider_status(), fetch_litemaas_models(), _parse_csv(), Settings, _get_embedding_client(), settings(), _FakeModels (+18 more)

### Community 26 - "re"
Cohesion: 0.26
Nodes (9): route(), _fake(), llm_call(), test_call_error_falls_back(), test_hallucinated_intent_falls_back_to_recommend(), test_malformed_then_valid_retries_once(), test_pattern_check_skips_llm(), test_valid_output_first_try() (+1 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.21
Nodes (23): ComponentLink, content_owner(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous(), test_curator_content_path_override_is_not_a_pure_stub() (+15 more)

### Community 28 - "schemas.py"
Cohesion: 0.06
Nodes (58): field_source_report(), AgvPrResponse, ApiKeyListResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse (+50 more)

### Community 29 - "seed"
Cohesion: 0.12
Nodes (30): ResolvedShowroom, add_stub(), search(), test_ci_reference_to_a_stub_resolves_through_its_owner(), test_dev_hit_promotes_to_the_prod_counterpart_stub(), test_each_owner_promotes_to_its_own_stub(), test_exact_same_item_prod_requires_complete_matching_signature(), test_independent_ids_keep_their_own_scores() (+22 more)

### Community 30 - "App.tsx"
Cohesion: 0.07
Nodes (42): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), LlmProviderCard() (+34 more)

### Community 31 - "settings.py"
Cohesion: 0.09
Nodes (23): _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url() (+15 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (71): References, AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr() (+63 more)

### Community 33 - "advisor.py"
Cohesion: 0.27
Nodes (4): ChatRequest, QueryRequest, select_recommendation(), SelectRequest

### Community 34 - "JobProgressRelay"
Cohesion: 0.14
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 35 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.23
Nodes (10): Controlled Vocabulary, Difficulty Levels Taxonomy, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy, Learning Objectives Extraction (Stated + Inferred), Module-Level Analysis Output (+2 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.15
Nodes (4): load_vocabulary(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "_generate_key"
Cohesion: 0.14
Nodes (7): reuse_lock_id(), _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.15
Nodes (21): _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow() (+13 more)

### Community 42 - "structlog"
Cohesion: 0.09
Nodes (14): 2. Orchestrator and Pipeline, call_llm(), generate_embedding(), QueryState, extract_urls(), run_category(), _build_deterministic_assessment(), _call_synthesis() (+6 more)

### Community 44 - "test_analyzer.py"
Cohesion: 0.09
Nodes (26): check_showroom_stale(), classify_scan_error(), description_content_hash(), filter_boilerplate_files(), get_repo_head(), hash_showroom_content(), parse_analysis_response(), _parse_nav_includes() (+18 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.15
Nodes (22): _as_bool(), asset_type_tokens(), content_id_for(), derive_osspa_status(), normalize_row(), parse_palist_csv(), scope_rows(), _split_list() (+14 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.12
Nodes (6): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), _recompute_windowed_scores(), TestComputePerformanceScore

### Community 47 - "api.ts"
Cohesion: 0.09
Nodes (54): CollapsibleFilterGroup(), CollapsibleFilterGroupProps, render(), LabelFilterGroup(), LabelFilterGroupProps, fmtTargetDate(), isInProgress(), isRecommended() (+46 more)

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
Cohesion: 0.11
Nodes (35): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_pr_statuses(), check_stale(), edit_retirement() (+27 more)

### Community 53 - "chat_sessions.py"
Cohesion: 0.18
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 55 - "performance_dashboard"
Cohesion: 0.33
Nodes (3): _extract_base_name_from_content_id(), retirement_dashboard(), TestRetirementDashboardMetrics

### Community 56 - "osspa_sync.py"
Cohesion: 0.15
Nodes (7): clone_examples_repo(), fetch_palist_csv(), file_commit_sha(), get_head_sha(), OsspaSyncError, _run_git(), _boom()

### Community 57 - "run_osspa_sync"
Cohesion: 0.28
Nodes (16): run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items(), test_missing_detail_page_marks_stale_and_skips() (+8 more)

### Community 58 - "loader.py"
Cohesion: 0.10
Nodes (13): _entries_to_dicts(), _header_comment(), _as_tuple(), _build_lookups(), _parse_entries(), _resolve_path(), _validate(), squash_key() (+5 more)

### Community 59 - "Retirement System"
Cohesion: 0.08
Nodes (25): AgV Access Layer, Architecture, Authentication and Scope, Automatic Removal Eligibility, Cancellation and Recovery, Catalog Soft-Delete, Checking Merges, Code Organization (+17 more)

### Community 60 - "parse_analysis_response"
Cohesion: 0.10
Nodes (12): _prefix_overlap(), _expand_vocab_aliases(), _find_keyword_ties(), resolve_item(), _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages() (+4 more)

### Community 61 - "analyze_architecture_item"
Cohesion: 0.16
Nodes (11): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms(), test_analyze_uses_the_dedicated_model_when_configured() (+3 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.13
Nodes (9): client(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures() (+1 more)

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "with"
Cohesion: 0.07
Nodes (31): runs-on, steps, environment, needs, runs-on, steps, name, url (+23 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.13
Nodes (11): _row(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override(), test_schema_backfills_status_from_stage() (+3 more)

### Community 66 - "Candidate"
Cohesion: 0.10
Nodes (11): HandsOnDriver, Candidate, _make_hands_on_candidate(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming() (+3 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.15
Nodes (10): _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs() (+2 more)

### Community 68 - "RouterOutput"
Cohesion: 0.21
Nodes (18): RouterOutput, Scope, _parse_catalog_url(), pattern_check(), resolve_and_verify(), _result_turns(), _turn_chips(), test_intent_enum_closed() (+10 more)

### Community 69 - "test_db.py"
Cohesion: 0.20
Nodes (11): _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default(), test_filtered_catalog_pagination(), test_filtered_catalog_search() (+3 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "test_chat_live.py"
Cohesion: 0.31
Nodes (4): _noop(), _settings(), test_live_item_facts_turn(), test_live_out_of_scope()

### Community 73 - "sync_opl_vocabulary.py"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 74 - "analyzer.py"
Cohesion: 0.10
Nodes (25): 3. Scan pipeline branch, Constraints, analysis_context_hash(), analysis_from_row(), analyze_showroom(), build_module_embedding_text(), compute_analysis_context_hash(), compute_analysis_input_hash() (+17 more)

### Community 75 - "test_auth_middleware.py"
Cohesion: 0.18
Nodes (6): _fetch_group_members(), _user_in_groups(), _mock_async_client_get(), _mock_group_response(), TestApiKeyRoleCeiling, TestGroupLookup

### Community 76 - ".get_content_entity"
Cohesion: 0.21
Nodes (15): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+7 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - ".upsert_babylon_catalog_item"
Cohesion: 0.12
Nodes (9): test_filter_platform_value(), test_upsert_stores_labels(), db_with_perf_data(), test_content_path(), test_upsert_and_get_catalog_item(), test_upsert_updates_existing(), test_browse_maps_retirement_to_sibling_stages(), test_browse_reports_retirement_workflow_status() (+1 more)

### Community 79 - "command"
Cohesion: 0.13
Nodes (13): command, flag(), get_db(), infra_stats(), note(), override_url(), refresh(), set_content_path() (+5 more)

### Community 80 - "run_category"
Cohesion: 0.08
Nodes (25): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers, Approach Decision (+17 more)

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.09
Nodes (20): _resolve_ci_references(), effective_showroom_source(), item_family_key(), resolve_showroom_source(), unresolved(), walk(), legacy_test_item(), node() (+12 more)

### Community 82 - "set_analysis_source"
Cohesion: 0.44
Nodes (8): AnalysisSourceRequest, set_analysis_source(), route_request(), test_analysis_source_endpoint_curator_ok(), test_analysis_source_endpoint_custom_without_text_400(), test_analysis_source_endpoint_empty_description_400(), test_analysis_source_endpoint_requires_curator(), test_catalog_detail_includes_analysis_source_fields()

### Community 83 - "test_nonprod.py"
Cohesion: 0.08
Nodes (11): _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestNonprodWindows (+3 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.07
Nodes (50): workflow_lock_id(), run_retirement_sweep(), test_lifecycle_old_closed_workflows_do_not_backfill(), _approved_unstarted(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup() (+42 more)

### Community 85 - "jira.py"
Cohesion: 0.04
Nodes (32): _close_issue(), close_issue_done(), close_issue_wont_do(), _get_access_token(), get_issue_status(), _issue_is_closed(), _move_to_in_progress(), _oauth_config() (+24 more)

### Community 86 - "_make_request"
Cohesion: 0.21
Nodes (5): get_current_user(), _make_request(), TestApiKeyAuth, TestGetCurrentUser, TestProxySecretEnforcement

### Community 87 - "_print"
Cohesion: 0.16
Nodes (6): _print(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 88 - "ArchitectureDriver"
Cohesion: 0.20
Nodes (8): ArchitectureDriver, _primary_asset_type(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 89 - "build_retirement_description"
Cohesion: 0.12
Nodes (16): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+8 more)

### Community 90 - "orchestrator.py"
Cohesion: 0.15
Nodes (14): _call_litemaas_inner(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), _help_answer(), process_turn(), _scope_echo() (+6 more)

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.18
Nodes (13): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API, PostgreSQL with pgvector (+5 more)

### Community 92 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.10
Nodes (38): start_scan(), InvalidShowroomRef, order_for_reuse(), reuse_key_from_signature(), showroom_reuse_key(), scan_babylon_item(), run_stale_check(), run_analysis() (+30 more)

### Community 94 - "asyncio"
Cohesion: 0.14
Nodes (16): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+8 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "Design"
Cohesion: 0.22
Nodes (9): 1. Storage, 2. Source resolution, 4. Candidate selection and stale check, 5. API, 6. Frontend, 7. Coverage math, Design, _snapshot() (+1 more)

### Community 101 - "Candidate"
Cohesion: 0.13
Nodes (11): _call_rationale_single(), _format_single_candidate(), _run_catalog_second_pass(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published() (+3 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.09
Nodes (16): test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at(), FakeSettings (+8 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (10): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+2 more)

### Community 108 - "test_workers.py"
Cohesion: 0.24
Nodes (9): test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes(), test_worker_context_has_required_fields(), test_worker_settings_has_lifecycle() (+1 more)

### Community 109 - "effective_analysis_source"
Cohesion: 0.29
Nodes (4): description_text(), effective_analysis_source(), test_effective_analysis_source_defaults_to_showroom(), test_effective_analysis_source_returns_override()

### Community 111 - "rcars-login.py"
Cohesion: 0.19
Nodes (8): _extract_json(), cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 112 - "pytest"
Cohesion: 0.04
Nodes (27): create_app(), lifespan(), RequestLoggingMiddleware, client(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists() (+19 more)

### Community 113 - "ResolvedShowroom"
Cohesion: 0.21
Nodes (9): main(), snapshots(), test_dry_run_performs_no_writes(), test_execute_requires_scans_paused_confirmation(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data(), test_reset_rejects_non_babylon_or_missing_ids_atomically(), test_reset_rejects_running_or_queued_analysis_jobs() (+1 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - ".close"
Cohesion: 0.05
Nodes (28): db(), seed_infrastructure(), db(), db(), db(), db(), db(), db() (+20 more)

### Community 120 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 121 - "recommendations.py"
Cohesion: 0.14
Nodes (5): _run_low(), registered_content_types(), run_query(), _run_one(), run_recommendation()

### Community 123 - "test_drivers.py"
Cohesion: 0.09
Nodes (15): ContentTypeDriver, get_driver(), get_drivers_for_types(), _init_drivers(), _register(), format_triage_candidates(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data() (+7 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.24
Nodes (9): _base_name(), cancel_retirement(), CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable(), _pr_state() (+1 more)

### Community 126 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 127 - "command"
Cohesion: 0.12
Nodes (9): cli(), init_db(), osspa_sync_cmd(), overlap_candidates_cmd(), scan(), serve(), status(), vocab_stage_rescan() (+1 more)

### Community 128 - "middleware/auth.py"
Cohesion: 0.27
Nodes (9): Key Patterns, _check_api_key_role_ceiling(), _get_cached_role_assignments(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), _validate_api_key_cached() (+1 more)

### Community 129 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 130 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 131 - "Content Owner Model for Virtual CIs — Design"
Cohesion: 0.13
Nodes (18): Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Pure stub (+10 more)

### Community 132 - "is_content_excluded"
Cohesion: 0.20
Nodes (8): Anti-goals, Approaches considered, Deployment, Description-Based Analysis for Items With No Showroom — Design, Goals, Intent, Non-goals, is_content_excluded()

### Community 133 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 134 - "handlers.py"
Cohesion: 0.14
Nodes (18): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+10 more)

### Community 135 - ".create_job"
Cohesion: 0.22
Nodes (6): _do(), test_job_failure(), test_job_lifecycle(), test_list_jobs(), test_list_jobs_shows_running_before_newer_queued(), test_queued_job_keeps_progress_json()

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - "showroom_source.py"
Cohesion: 0.08
Nodes (19): _apply_component_inheritance(), CatalogReader, collect(), load(), _collect_bases(), component_item_to_ci_name(), _content_fields(), extract_base_ci_refs() (+11 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.16
Nodes (26): LLM Provider Routing (LiteMaaS / Vertex AI), dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System (+18 more)

### Community 154 - "patch"
Cohesion: 0.36
Nodes (4): _validate_sa_token(), _mock_async_client(), _mock_token_review_response(), TestValidateSaToken

### Community 155 - "block"
Cohesion: 0.18
Nodes (11): cmd, migrate_pod, ansible.builtin.command, ansible.builtin.set_fact, changed_when, delay, name, register (+3 more)

### Community 156 - "post_tasks"
Cohesion: 0.18
Nodes (11): msg, kind, kubeconfig, label_selectors, namespace, post_tasks, ansible.builtin.debug, kubernetes.core.k8s_info (+3 more)

### Community 157 - "action_verbs"
Cohesion: 0.20
Nodes (10): action_verbs, hands_on, interactive, read_through, rejected, valid, rejected, valid (+2 more)

### Community 159 - "build_description_prompt"
Cohesion: 0.40
Nodes (3): Open items for the builder, build_description_prompt(), _canonical_content()

### Community 160 - "Python Dependency Manifest (requirements.lock)"
Cohesion: 0.22
Nodes (9): Anthropic SDK Dependency (v0.120.0), arq Dependency (v0.28.0), Python Dependency Manifest (requirements.lock), FastAPI Dependency (v0.140.7), OpenAI SDK Dependency (v2.49.0), psycopg Dependency (v3.3.4), Pydantic Dependency (v2.13.4), Redis Client Dependency (v5.3.1) (+1 more)

### Community 161 - "test_llm_provider_status.py"
Cohesion: 0.28
Nodes (4): _make_client(), no_litemaas_fetch(), test_lists_model_for_every_llm_use(), test_litemaas_active_with_models()

### Community 163 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 169 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 174 - "test_content_owner.py"
Cohesion: 0.05
Nodes (52): API, Data Import, Data Source, Field Source Content, Frontend, rescan_all(), reconcile_pure_stubs(), scan_candidates() (+44 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "build_infrastructure_embedding_text"
Cohesion: 0.60
Nodes (3): build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 185 - "extract_catalog_item"
Cohesion: 0.09
Nodes (15): Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+7 more)

### Community 186 - "mcp_query"
Cohesion: 0.17
Nodes (5): _fetch_oauth_token(), _mcp_call(), mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 190 - "content_modes"
Cohesion: 0.40
Nodes (5): content_modes, architecture, demo, lab, sandbox

### Community 191 - ".get_unknown_terms"
Cohesion: 0.12
Nodes (5): TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched, TestUnknownTermsSchema

### Community 192 - "kubernetes.core.k8s_exec"
Cohesion: 0.50
Nodes (4): kubernetes.core.k8s_exec, kubeconfig, namespace, pod

### Community 193 - "collections"
Cohesion: 0.50
Nodes (3): collections, name, version

### Community 195 - "solutions"
Cohesion: 0.50
Nodes (4): solutions, aliases, is_tdp, name

### Community 196 - "ansible.builtin.assert"
Cohesion: 0.67
Nodes (3): fail_msg, that, ansible.builtin.assert

### Community 197 - "content_similarity Table"
Cohesion: 0.67
Nodes (3): Evidence Pack, content_similarity Table, overlap_candidates Table

### Community 199 - "test_infrastructure.py"
Cohesion: 0.22
Nodes (6): clean_infra(), db(), test_get_infrastructure_with_item_counts(), test_list_infrastructure_with_type_filter(), test_upsert_infrastructure_insert(), test_upsert_infrastructure_update()

### Community 203 - "TestPromptInjection"
Cohesion: 0.20
Nodes (3): build_analysis_prompt(), truncate_content(), TestPromptInjection

### Community 204 - "database.py"
Cohesion: 0.12
Nodes (3): retirement_label(), db(), seed_items()

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1365 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **55 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `is_content_excluded`, `.create_job`, `test_edit_update_skips_cancelled_workflows`, `db/__init__.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `ops.py`, `workload_scanner.py`, `test_db.py`, `.upsert_babylon_catalog_item`, `Settings`, `seed`, `settings.py`, `_generate_key`, `structlog`, `Any`, `extract_base_name`, `chat_sessions.py`, `run_osspa_sync`, `extract_catalog_item`, `parse_analysis_response`, `analyze_architecture_item`, `TestGetNonprodBaseNames`, `.get_unknown_terms`, `test_catalog_osspa_routes.py`, `test_osspa_db.py`, `RouterOutput`, `test_db.py`, `test_infrastructure.py`, `test_chat_live.py`, `analyzer.py`, `database.py`, `.get_content_entity`, `.upsert_babylon_catalog_item`, `command`, `test_test_content_exclusion.py`, `test_nonprod.py`, `test_retirement_pr_status.py`, `jira.py`, `_print`, `orchestrator.py`, `test_showroom_scan.py`, `asyncio`, `test_field_source_sync.py`, `effective_analysis_source`, `rcars-login.py`, `pytest`, `ResolvedShowroom`, `.close`, `recommendations.py`?**
  _High betweenness centrality (0.193) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `Database` (e.g. with `lifespan()` and `Settings`) actually correct?**
  _`Database` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.1053763440860215 - nodes in this community are weakly interconnected._
- **Why does `Advisor v2 — Content-Type Drivers` connect `run_category` to `JobProgressRelay`?**
  _High betweenness centrality (0.181) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.025149453720882294 - nodes in this community are weakly interconnected._