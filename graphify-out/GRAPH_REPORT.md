# Graph Report - rhdpcd-2266  (2026-11-20)

## Corpus Check
- 293 files · ~317,391 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4104 nodes · 10159 edges · 216 communities (153 shown, 63 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1056 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d7dec325`
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
- test_description_analysis.py
- admin.py
- test_retirement_jira_events.py
- Infrastructure Catalog
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_showroom_reuse.py
- ops.py
- workload_scanner.py
- .upsert_babylon_catalog_item
- routes/auth.py
- _jira_event_messages
- advisor.py
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
- .close
- JobProgressRelay
- ContentAnalysisPage.tsx
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- test_jira_service.py
- run_category
- .upsert_babylon_catalog_item
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
- TestRetirementDashboardMetrics
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
- main
- retirement_jira_events.py
- api.ts
- ECA Production Redesign Spec
- publish_progress
- sync_opl_vocabulary.py
- analyzer.py
- test_auth_middleware.py
- .get_content_entity
- TestValidation
- test_field_source_db.py
- command
- run_category
- test_test_content_exclusion.py
- test_cancel_preserves_tracking_on_github_failure
- test_nonprod.py
- test_retirement_pr_status.py
- database.py
- _make_request
- _print
- ArchitectureDriver
- build_retirement_description
- middleware/auth.py
- System Design Architecture Doc
- MemoryArtifacts
- test_showroom_scan.py
- asyncio
- Showroom analysis isolation
- Scan Pipeline
- workflow_lock_id
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- showroom_source.py
- Candidate
- TestVocabularyEndpoints
- rcars-login.sh
- patch
- test_field_source_sync.py
- pipeline.py
- RCARS OCP Deployment Playbook
- test_workers.py
- ._artifact_connection
- Rec Card Duration and Best Fit Spec
- rcars-login.py
- test_llm_provider_status.py
- test_showroom_rebuild.py
- content_entities Table
- Advisor v2 — Content-Type Drivers
- Deploy Docs GitHub Actions Workflow
- Change Detection
- _user_has_db_role
- Overlap Detection Redesign
- test_reporting.py
- settings.py
- build_embedding_text
- ContentTypeDriver
- test_orphan_cleanup.py
- retirement_cleanup.py
- test_llm_routing.py
- scan
- docs.yml
- vocabulary.yaml
- pre_tasks
- search
- showroom_scan.py
- AdocRead
- router.py
- .create_job
- Field Source Content
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
- workload_scan
- block
- post_tasks
- action_verbs
- .upsert_infrastructure
- normalize_row
- Python Dependency Manifest (requirements.lock)
- _parse_sa_allowlist
- require_performance_view
- deploy.yml
- LLM Overlap Assessment Design
- rcars
- rcars
- tasks
- Match Event Prompt Template
- extract_base_name
- jira.py
- test_content_owner.py
- test_vocabulary.py
- Python Requirements Entry Point
- build_infrastructure_embedding_text
- with_job_context
- TestTokenExchange
- _reset_token_cache
- test_drivers.py
- ignored_terms
- extract_catalog_item
- mcp_query
- readiness
- TestGetNonprodBaseNames
- db
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- ResolvedShowroom
- solutions
- ansible.builtin.assert
- TestStepOrder
- TestCreateApiKey
- test_already_closed_issue_needs_no_transition
- TestPromptInjection
- RequestLoggingMiddleware
- test_start_retirement_creates_ticket_off_event_loop
- TestRevokeApiKey
- TestUnauthenticatedAccess
- Browse Page Redesign Spec
- seed_items
- test_edit_rejects_name_without_replacement_ci
- test_edit_rejected_for_retired_item
- test_edit_rejected_while_cancellation_pending

## God Nodes (most connected - your core abstractions)
1. `Database` - 301 edges
2. `Settings` - 180 edges
3. `load_vocabulary()` - 71 edges
4. `Candidate` - 47 edges
5. `seed()` - 46 edges
6. `create_app()` - 43 edges
7. `scan_babylon_item()` - 43 edges
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
- `Management RBAC Bootstrap Task` --implements--> `RCARS Authentication Model`  [INFERRED]
  ansible/tasks/mgmt-rbac.yml → docs/architecture/system-design.md
- `3. Scan pipeline branch` --references--> `AnalysisSignature`  [INFERRED]
  docs/superpowers/specs/2026-11-17-description-analysis-design.md → src/api/rcars/services/showroom_source.py

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

## Communities (216 total, 63 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.11
Nodes (17): _jira_request(), _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry() (+9 more)

### Community 1 - "Database"
Cohesion: 0.03
Nodes (5): Database, test_advisor_session(), test_enrichment_tags(), test_token_usage(), test_advisory_lock_is_not_reentrant_across_sessions()

### Community 2 - "react"
Cohesion: 0.07
Nodes (37): react, BlockErrorBoundary, Props, State, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock() (+29 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.16
Nodes (20): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis (+12 more)

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
Cohesion: 0.15
Nodes (12): overlap_report(), generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats() (+4 more)

### Community 8 - "test_description_analysis.py"
Cohesion: 0.06
Nodes (75): add_tag(), AnalysisSourceRequest, catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+67 more)

### Community 9 - "admin.py"
Cohesion: 0.13
Nodes (25): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+17 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.08
Nodes (36): deliver_pending_events(), comments(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_malformed_page_does_not_prove_absence(), test_comment_missing_credentials_does_not_call_http() (+28 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.17
Nodes (13): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+5 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (24): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+16 more)

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_showroom_reuse.py"
Cohesion: 0.20
Nodes (13): prime(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_embedding_only_changes_repair_only_affected_artifacts(), test_every_changed_signature_input_prevents_donor_reuse(), test_force_bypasses_unchanged_fast_path_and_donors(), test_identical_revision_and_context_skips_clone_llm_and_embeddings(), test_nav_and_publishing_house_stub_return_no_content_before_lookup_or_llm() (+5 more)

### Community 17 - "ops.py"
Cohesion: 0.12
Nodes (12): Decisions (Nate, 2026-11-19), build_sandbox_summary(), scan_all_collections(), run_babylon_pipeline(), run_catalog_refresh(), run_field_source_sync_job(), _run_nightly_pipeline(), run_osspa_pipeline() (+4 more)

### Community 18 - "workload_scanner.py"
Cohesion: 0.07
Nodes (16): call_llm(), generate_embedding(), ls_remote_sha(), regenerate_embeddings(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes() (+8 more)

### Community 19 - ".upsert_babylon_catalog_item"
Cohesion: 0.06
Nodes (27): _seed_label_count_items(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none(), test_label_counts_follow_other_filters() (+19 more)

### Community 20 - "routes/auth.py"
Cohesion: 0.19
Nodes (14): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+6 more)

### Community 21 - "_jira_event_messages"
Cohesion: 0.10
Nodes (9): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_requires_admin(), test_edit_update_skips_cancelled_workflows(), test_edit_without_change_records_no_event() (+1 more)

### Community 22 - "advisor.py"
Cohesion: 0.08
Nodes (13): _get_user_key(), ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest (+5 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (24): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), git() (+16 more)

### Community 24 - "react"
Cohesion: 0.13
Nodes (23): buildUrl(), FALLBACK_FORMAT_LABELS, FORMAT_COLORS, RecCard(), RecCardProps, CollapsibleTier(), RecCardList(), RecCardListProps (+15 more)

### Community 25 - "Settings"
Cohesion: 0.07
Nodes (29): llm_provider_status(), submit_chat(), submit_query(), performance_dashboard(), fetch_litemaas_models(), _parse_csv(), Settings, session_owner_ok() (+21 more)

### Community 26 - "re"
Cohesion: 0.11
Nodes (20): _call_litemaas_inner(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), _expand_vocab_aliases(), _extract_json(), route() (+12 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.20
Nodes (23): ComponentLink, content_owner(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous(), test_curator_content_path_override_is_not_a_pure_stub() (+15 more)

### Community 28 - "schemas.py"
Cohesion: 0.06
Nodes (55): AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse, CatalogStatsResponse, ChatSubmitResponse (+47 more)

### Community 29 - "seed"
Cohesion: 0.15
Nodes (28): add_stub(), search(), test_ci_reference_to_a_stub_resolves_through_its_owner(), test_dev_hit_promotes_to_the_prod_counterpart_stub(), test_each_owner_promotes_to_its_own_stub(), test_exact_same_item_prod_requires_complete_matching_signature(), test_independent_ids_keep_their_own_scores(), test_owner_hit_is_shown_as_its_only_stub() (+20 more)

### Community 30 - "App.tsx"
Cohesion: 0.07
Nodes (42): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), LlmProviderCard() (+34 more)

### Community 31 - "settings.py"
Cohesion: 0.13
Nodes (17): _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), shutdown(), test_logger_outputs_json(), test_logger_with_job_id() (+9 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 33 - ".close"
Cohesion: 0.05
Nodes (29): db(), seed_infrastructure(), db(), db(), db(), db(), db(), db() (+21 more)

### Community 34 - "JobProgressRelay"
Cohesion: 0.13
Nodes (15): Frontend Progress Display, What Stays Unchanged, stream_job(), create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives() (+7 more)

### Community 35 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.23
Nodes (10): Controlled Vocabulary, Difficulty Levels Taxonomy, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy, Learning Objectives Extraction (Stated + Inferred), Module-Level Analysis Output (+2 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.12
Nodes (6): load_vocabulary(), _noise_variants(), snap_term(), _normalize_products(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "_generate_key"
Cohesion: 0.17
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.14
Nodes (22): Open Questions / Risks, _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics() (+14 more)

### Community 42 - "run_category"
Cohesion: 0.12
Nodes (13): 2. Orchestrator and Pipeline, What Gets Deleted, registered_content_types(), QueryState, run_category(), serialize_candidates(), run_query(), _run_one() (+5 more)

### Community 43 - ".upsert_babylon_catalog_item"
Cohesion: 0.08
Nodes (24): test_facets_platforms_and_tdps(), test_upsert_stores_labels(), db_with_perf_data(), test_list_catalog_items(), test_retire_missing_babylon_ignores_other_sources(), test_upsert_and_get_catalog_item(), test_upsert_updates_existing(), _arch() (+16 more)

### Community 44 - "test_analyzer.py"
Cohesion: 0.10
Nodes (26): analyze_showroom(), check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), hash_showroom_content(), parse_analysis_response(), _parse_nav_includes() (+18 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.22
Nodes (18): asset_type_tokens(), content_id_for(), parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_content_id_format(), test_derive_osspa_status() (+10 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.13
Nodes (5): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), TestComputePerformanceScore

### Community 47 - "api.ts"
Cohesion: 0.09
Nodes (54): CollapsibleFilterGroup(), CollapsibleFilterGroupProps, render(), LabelFilterGroup(), LabelFilterGroupProps, fmtTargetDate(), isInProgress(), isRecommended() (+46 more)

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
Cohesion: 0.09
Nodes (40): approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_pr_statuses(), check_stale(), edit_retirement(), EditRetirementRequest (+32 more)

### Community 53 - "chat_sessions.py"
Cohesion: 0.17
Nodes (8): get_session_context(), log_chat_turn(), next_turn_index(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership(), test_turn_index_increments()

### Community 54 - "Vocabulary"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 56 - "osspa_sync.py"
Cohesion: 0.15
Nodes (7): clone_examples_repo(), fetch_palist_csv(), file_commit_sha(), get_head_sha(), OsspaSyncError, _run_git(), _boom()

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

### Community 61 - "analyze_architecture_item"
Cohesion: 0.16
Nodes (11): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms(), test_analyze_uses_the_dedicated_model_when_configured() (+3 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.15
Nodes (8): client(), _second_architecture(), settings(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "with"
Cohesion: 0.10
Nodes (21): runs-on, steps, environment, needs, runs-on, steps, name, url (+13 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.12
Nodes (12): test_audience_filter_applies_across_content_types(), _row(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override() (+4 more)

### Community 66 - "Candidate"
Cohesion: 0.17
Nodes (8): _extract_duration_target(), HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming(), test_hands_on_serialize_with_performance(), test_hands_on_triage_guidance()

### Community 67 - "reporting_sync.py"
Cohesion: 0.11
Nodes (12): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _build_windowed_metrics(), _merge_published_base_pairs() (+4 more)

### Community 68 - "main"
Cohesion: 0.11
Nodes (5): _do(), main(), test_content_path(), test_execute_requires_scans_paused_confirmation(), test_script_rejects_selection_with_no_showroom_items()

### Community 69 - "retirement_jira_events.py"
Cohesion: 0.14
Nodes (10): ensure_issue_event_comment(), jira_auth_configured(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), reuse_lock_id(), test_comment_failed_lookup_does_not_post() (+2 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "publish_progress"
Cohesion: 0.15
Nodes (8): publish_progress(), run_chat_turn(), on_progress(), _progress_bridge(), _publish(), run_retirement_sweep_job(), run_recommendation(), on_progress()

### Community 73 - "sync_opl_vocabulary.py"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 74 - "analyzer.py"
Cohesion: 0.10
Nodes (24): analysis_context_hash(), analysis_from_row(), analyze_description(), compute_analysis_context_hash(), compute_analysis_input_hash(), compute_embedding_fingerprint(), description_content_hash(), description_source() (+16 more)

### Community 75 - "test_auth_middleware.py"
Cohesion: 0.18
Nodes (6): _fetch_group_members(), _user_in_groups(), _mock_async_client_get(), _mock_group_response(), TestApiKeyRoleCeiling, TestGroupLookup

### Community 76 - ".get_content_entity"
Cohesion: 0.14
Nodes (18): get_item_workloads(), get_performance_scores(), _prefix_overlap(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+10 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "test_field_source_db.py"
Cohesion: 0.17
Nodes (7): test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at()

### Community 79 - "command"
Cohesion: 0.12
Nodes (14): command, flag(), get_db(), infra_stats(), note(), override_url(), refresh(), serve() (+6 more)

### Community 80 - "run_category"
Cohesion: 0.13
Nodes (14): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Candidate Dataclass, `content_entities` (shared table — all types) (+6 more)

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.12
Nodes (16): resolve_showroom_source(), unresolved(), walk(), legacy_test_item(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(), test_cached_overlap_cannot_bypass_test_content_exclusion(), test_existing_test_vectors_never_enter_content_retrieval() (+8 more)

### Community 82 - "test_cancel_preserves_tracking_on_github_failure"
Cohesion: 0.14
Nodes (7): test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_required_cancel_jira_runs_off_event_loop(), close_jira(), state()

### Community 83 - "test_nonprod.py"
Cohesion: 0.06
Nodes (14): _retirement_metrics(), _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestListNonprodItems, TestNonprodIgnore, TestNonprodProvisionsSql, TestNonprodRouteExists (+6 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.10
Nodes (36): run_retirement_sweep(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancellation_does_not_mark_concurrently_retired_item(), test_manual_pr_creation_respects_cleanup_lock(), test_merged_revert_still_deletes_workflow(), test_refresh_completes_merged_removal_before_target_date(), test_refresh_does_not_retire_unmerged_or_unknown_pr() (+28 more)

### Community 85 - "database.py"
Cohesion: 0.03
Nodes (35): create_app(), lifespan(), retirement_label(), client(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists() (+27 more)

### Community 86 - "_make_request"
Cohesion: 0.21
Nodes (5): get_current_user(), _make_request(), TestApiKeyAuth, TestGetCurrentUser, TestProxySecretEnforcement

### Community 87 - "_print"
Cohesion: 0.14
Nodes (6): _print(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 88 - "ArchitectureDriver"
Cohesion: 0.16
Nodes (11): ArchitectureDriver, _primary_asset_type(), Candidate, _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash() (+3 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.11
Nodes (17): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+9 more)

### Community 90 - "middleware/auth.py"
Cohesion: 0.27
Nodes (9): Key Patterns, _check_api_key_role_ceiling(), _get_cached_role_assignments(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), _validate_api_key_cached() (+1 more)

### Community 91 - "System Design Architecture Doc"
Cohesion: 0.20
Nodes (16): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, LLM Provider Routing (LiteMaaS / Vertex AI), Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API (+8 more)

### Community 92 - "MemoryArtifacts"
Cohesion: 0.17
Nodes (3): MemoryArtifacts, scan(), run()

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.12
Nodes (33): start_scan(), order_for_reuse(), reuse_key_from_signature(), showroom_reuse_key(), scan_babylon_item(), run_stale_check(), run_analysis(), add_item() (+25 more)

### Community 94 - "asyncio"
Cohesion: 0.14
Nodes (18): build_evidence_pack(), seed_chat_fixtures(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted(), test_pack_includes_shared_workload_note(), _noop(), _res(), _settings() (+10 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "workflow_lock_id"
Cohesion: 0.24
Nodes (8): workflow_lock_id(), _approved_unstarted(), test_start_retirement_holds_lock_while_creating_ticket(), fake_create(), test_start_retirement_respects_workflow_lock(), _prepare(), test_route_rejects_when_workflow_lock_held(), test_route_releases_lock_after_request()

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "showroom_source.py"
Cohesion: 0.09
Nodes (26): Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Pure stub (+18 more)

### Community 101 - "Candidate"
Cohesion: 0.13
Nodes (11): _call_rationale_single(), _format_single_candidate(), _run_catalog_second_pass(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published() (+3 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "patch"
Cohesion: 0.36
Nodes (4): _validate_sa_token(), _mock_async_client(), _mock_token_review_response(), TestValidateSaToken

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.15
Nodes (11): _build_field_source_sql(), run_field_source_sync(), FakeSettings, _mock_mcp_query(), _row(), test_field_source_sync_captures_user_email(), test_field_source_sync_ignores_agd_v2_items(), tracking_mock() (+3 more)

### Community 106 - "pipeline.py"
Cohesion: 0.11
Nodes (11): _call_synthesis(), generate_content_gaps(), fake_embedding(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), FakeLLM, _noop() (+3 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (10): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+2 more)

### Community 108 - "test_workers.py"
Cohesion: 0.18
Nodes (11): WorkerContext, run_nightly_pipeline(), WorkerSettings, test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails() (+3 more)

### Community 111 - "rcars-login.py"
Cohesion: 0.23
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 112 - "test_llm_provider_status.py"
Cohesion: 0.28
Nodes (4): _make_client(), no_litemaas_fetch(), test_lists_model_for_every_llm_use(), test_litemaas_active_with_models()

### Community 113 - "test_showroom_rebuild.py"
Cohesion: 0.24
Nodes (6): snapshots(), test_dry_run_performs_no_writes(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data(), test_reset_rejects_non_babylon_or_missing_ids_atomically(), test_reset_rejects_running_or_queued_analysis_jobs()

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.18
Nodes (10): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Goals, Non-Goals, Parallel Pipeline Instances (+2 more)

### Community 121 - "settings.py"
Cohesion: 0.18
Nodes (5): recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url(), scan_startup(), _startup()

### Community 123 - "ContentTypeDriver"
Cohesion: 0.11
Nodes (3): ContentTypeDriver, _init_drivers(), _register()

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.19
Nodes (12): _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable() (+4 more)

### Community 126 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 128 - "docs.yml"
Cohesion: 0.18
Nodes (10): name, on, push, workflow_dispatch, permissions, contents, id-token, pages (+2 more)

### Community 129 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 130 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 131 - "search"
Cohesion: 0.18
Nodes (6): _owner_scope_ids(), _resolve_ci_references(), search(), _strip_embedding_filler(), test_legacy_test_sourced_wrapper_is_not_recommended(), test_test_item_cannot_seed_recommendation_neighbor_expansion()

### Community 132 - "showroom_scan.py"
Cohesion: 0.09
Nodes (19): 1. Storage, 2. Source resolution, 3. Scan pipeline branch, 4. Candidate selection and stale check, 5. API, 6. Frontend, 7. Coverage math, Constraints (+11 more)

### Community 133 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 134 - "router.py"
Cohesion: 0.08
Nodes (40): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+32 more)

### Community 135 - ".create_job"
Cohesion: 0.22
Nodes (6): _do(), test_job_failure(), test_job_lifecycle(), test_list_jobs(), test_list_jobs_shows_running_before_newer_queued(), test_queued_job_keeps_progress_json()

### Community 136 - "Field Source Content"
Cohesion: 0.29
Nodes (6): API, Data Import, Data Source, Field Source Content, Frontend, git_repo()

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - "showroom_source.py"
Cohesion: 0.08
Nodes (19): _apply_component_inheritance(), CatalogReader, collect(), load(), _collect_bases(), component_item_to_ci_name(), _content_fields(), extract_base_ci_refs() (+11 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.17
Nodes (20): dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference (+12 more)

### Community 154 - "workload_scan"
Cohesion: 0.15
Nodes (6): cli(), init_db(), osspa_sync_cmd(), vocab_stage_rescan(), vocab_unknowns(), workload_scan()

### Community 155 - "block"
Cohesion: 0.18
Nodes (11): cmd, migrate_pod, ansible.builtin.command, ansible.builtin.set_fact, changed_when, delay, name, register (+3 more)

### Community 156 - "post_tasks"
Cohesion: 0.18
Nodes (11): msg, kind, kubeconfig, label_selectors, namespace, post_tasks, ansible.builtin.debug, kubernetes.core.k8s_info (+3 more)

### Community 157 - "action_verbs"
Cohesion: 0.20
Nodes (10): action_verbs, hands_on, interactive, read_through, rejected, valid, rejected, valid (+2 more)

### Community 158 - ".upsert_infrastructure"
Cohesion: 0.29
Nodes (4): test_get_infrastructure_with_item_counts(), test_list_infrastructure_with_type_filter(), test_upsert_infrastructure_insert(), test_upsert_infrastructure_update()

### Community 159 - "normalize_row"
Cohesion: 0.36
Nodes (4): _as_bool(), derive_osspa_status(), normalize_row(), _split_list()

### Community 160 - "Python Dependency Manifest (requirements.lock)"
Cohesion: 0.22
Nodes (9): Anthropic SDK Dependency (v0.120.0), arq Dependency (v0.28.0), Python Dependency Manifest (requirements.lock), FastAPI Dependency (v0.140.7), OpenAI SDK Dependency (v2.49.0), psycopg Dependency (v3.3.4), Pydantic Dependency (v2.13.4), Redis Client Dependency (v5.3.1) (+1 more)

### Community 163 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 169 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 172 - "extract_base_name"
Cohesion: 0.15
Nodes (4): extract_base_name(), _window_start(), TestExtractBaseName, TestWindowStart

### Community 173 - "jira.py"
Cohesion: 0.09
Nodes (12): _close_issue(), close_issue_done(), close_issue_wont_do(), _fetch_oauth_token(), _get_access_token(), get_issue_status(), _issue_is_closed(), _move_to_in_progress() (+4 more)

### Community 174 - "test_content_owner.py"
Cohesion: 0.14
Nodes (31): analyze_single(), rescan_all(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner() (+23 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "build_infrastructure_embedding_text"
Cohesion: 0.60
Nodes (3): build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

### Community 183 - "test_drivers.py"
Cohesion: 0.17
Nodes (11): get_driver(), get_drivers_for_types(), format_triage_candidates(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_get_driver_architecture(), test_get_driver_lab(), test_get_driver_unknown_raises() (+3 more)

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 185 - "extract_catalog_item"
Cohesion: 0.11
Nodes (14): Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+6 more)

### Community 186 - "mcp_query"
Cohesion: 0.22
Nodes (4): _mcp_call(), mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 189 - "db"
Cohesion: 0.25
Nodes (5): InvalidShowroomRef, db(), test_older_scan_cannot_overwrite_newer_completed_generation(), overlapping(), repaired_while_checking()

### Community 190 - "content_modes"
Cohesion: 0.40
Nodes (5): content_modes, architecture, demo, lab, sandbox

### Community 191 - ".get_unknown_terms"
Cohesion: 0.20
Nodes (3): TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm

### Community 192 - "kubernetes.core.k8s_exec"
Cohesion: 0.50
Nodes (4): kubernetes.core.k8s_exec, kubeconfig, namespace, pod

### Community 193 - "collections"
Cohesion: 0.50
Nodes (3): collections, name, version

### Community 194 - "ResolvedShowroom"
Cohesion: 0.40
Nodes (3): ResolvedShowroom, test_curator_url_resolves_target_and_is_selected_after_catalog_refresh(), TestAnalyzerNormalizesOnce

### Community 195 - "solutions"
Cohesion: 0.50
Nodes (4): solutions, aliases, is_tdp, name

### Community 196 - "ansible.builtin.assert"
Cohesion: 0.67
Nodes (3): fail_msg, that, ansible.builtin.assert

### Community 199 - "test_already_closed_issue_needs_no_transition"
Cohesion: 0.40
Nodes (3): test_already_closed_issue_needs_no_transition(), test_required_closure_selects_resolution_and_verifies_result(), request()

### Community 203 - "TestPromptInjection"
Cohesion: 0.14
Nodes (6): Open items for the builder, build_analysis_prompt(), build_description_prompt(), _canonical_content(), truncate_content(), TestPromptInjection

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1379 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **63 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `search`, `showroom_scan.py`, `router.py`, `.create_job`, `db/__init__.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `ops.py`, `workload_scanner.py`, `.upsert_babylon_catalog_item`, `_jira_event_messages`, `Settings`, `test_showroom_source.py`, `.upsert_infrastructure`, `.close`, `_generate_key`, `run_category`, `.upsert_babylon_catalog_item`, `extract_base_name`, `chat_sessions.py`, `run_osspa_sync`, `TestGetNonprodBaseNames`, `analyze_architecture_item`, `db`, `.get_unknown_terms`, `test_catalog_osspa_routes.py`, `test_osspa_db.py`, `ResolvedShowroom`, `main`, `publish_progress`, `analyzer.py`, `.get_content_entity`, `test_field_source_db.py`, `command`, `test_nonprod.py`, `test_retirement_pr_status.py`, `database.py`, `_print`, `asyncio`, `workflow_lock_id`, `showroom_source.py`, `test_field_source_sync.py`, `pipeline.py`, `._artifact_connection`, `rcars-login.py`, `settings.py`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `Database` (e.g. with `lifespan()` and `Settings`) actually correct?**
  _`Database` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.1053763440860215 - nodes in this community are weakly interconnected._
- **Why does `Advisor v2 — Content-Type Drivers` connect `Advisor v2 — Content-Type Drivers` to `run_category`, `JobProgressRelay`?**
  _High betweenness centrality (0.167) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.027972027972027972 - nodes in this community are weakly interconnected._