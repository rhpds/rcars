# Graph Report - chore-rhdpcd-2297-cleanup  (2026-11-26)

## Corpus Check
- 304 files · ~333,309 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4498 nodes · 11324 edges · 240 communities (156 shown, 84 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 1055 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4878402d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _jira_request
- Database
- react
- Portfolio Architecture Ingest Design Spec
- common.yml
- devDependencies
- test_advisor_families.py
- db/__init__.py
- test_description_analysis.py
- admin.py
- test_retirement_jira_events.py
- Chat Router LLM
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_showroom_reuse.py
- ops.py
- Any
- .upsert_babylon_catalog_item
- test_catalog_families.py
- _jira_event_messages
- orchestrator.py
- test_osspa_adoc.py
- react
- Settings
- .close
- test_showroom_source.py
- Any
- seed
- App.tsx
- analysis.py
- test_agv_access.py
- test_advisor_families.py
- test_content_owner.py
- retirement_jira_events.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- settings.py
- compilerOptions
- test_jira_service.py
- pipeline.py
- Candidate
- analyzer.py
- test_showroom_rebuild.py
- compute_sales_impact
- api.ts
- normalize_analysis
- dev-services.sh
- ._artifact_connection
- structlog
- main
- test_analysis_identity.py
- Vocabulary
- test_osspa_analysis.py
- test_osspa_csv.py
- run_osspa_sync
- loader.py
- Retirement System
- parse_analysis_response
- create_app
- test_catalog_osspa_routes.py
- SyncPage.tsx
- with
- test_overlap_chat_families.py
- test_field_source_sync.py
- reporting_sync.py
- build_analysis_prompt
- api.ts
- ECA Production Redesign Spec
- HandsOnDriver
- json
- generate_embedding
- Advisor v2 — Content-Type Drivers
- routes/auth.py
- TestValidation
- Path
- command
- is_content_excluded
- test_test_content_exclusion.py
- test_drivers.py
- test_nonprod.py
- test_retirement_pr_status.py
- ArchitectureDriver
- middleware/auth.py
- extract_catalog_item
- cli.py
- build_retirement_description
- reporting_db_show
- pytest
- LLMResult
- test_showroom_scan.py
- Showroom analysis isolation
- Scan Pipeline
- chat/models.py
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- showroom_source.py
- seed_chat_fixtures
- test_vocabulary_admin.py
- rcars-login.sh
- CLAUDE.md — Project Instructions
- AdocRead
- .create_job
- RCARS OCP Deployment Playbook
- osspa_sync.py
- ContentAnalysisPage.tsx
- Rec Card Duration and Best Fit Spec
- middleware/auth.py
- workers/base.py
- option
- content_entities Table
- analyze_role
- Deploy Docs GitHub Actions Workflow
- Change Detection
- _extrapolate_count
- Overlap Detection Redesign
- mcp_query
- _resolve_item_by_name
- _expand_query_terms
- _FakeResponse
- test_orphan_cleanup.py
- retirement_cleanup.py
- _reset_token_cache
- _generate_key
- TestRetirementDashboardMetrics
- vocabulary.yaml
- pre_tasks
- _close_issue
- _reference_context
- ls_remote_sha
- workers/base.py
- .upsert_babylon_catalog_item
- test_llm_routing.py
- docker-entrypoint.sh
- RCARS — Agent Instructions
- services/catalog.py
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
- block
- post_tasks
- action_verbs
- .upsert_infrastructure
- scan_configs
- Python Dependency Manifest (requirements.lock)
- workflow_lock_id
- test_chat_handlers.py
- deploy.yml
- LLM Overlap Assessment Design
- rcars
- rcars
- tasks
- Match Event Prompt Template
- extract_base_name
- test_api_infrastructure.py
- advisor.py
- test_vocabulary.py
- Python Requirements Entry Point
- RouterOutput
- test_cancel_preserves_tracking_on_github_failure
- build_embedding_text
- test_edit_rejected_for_retired_item
- handlers.py
- ignored_terms
- build_retirement_description
- _sync_nonprod_usage
- TestGetNonprodBaseNames
- with_job_context
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- test_edit_rejected_while_cancellation_pending
- solutions
- ansible.builtin.assert
- _window_start
- family_members
- Design
- Browse Page Redesign Spec
- app_no_auth
- TestTokenExchange
- TestSpoofedProxyHeaders
- content_similarity Table
- Content Owner Model for Virtual CIs — Design
- TestRevokeApiKey
- TestRoleCeiling
- seed_items
- TestUnknownTermsSchema

## God Nodes (most connected - your core abstractions)
1. `Database` - 318 edges
2. `Settings` - 177 edges
3. `load_vocabulary()` - 67 edges
4. `seed()` - 50 edges
5. `Candidate` - 50 edges
6. `item()` - 50 edges
7. `create_app()` - 43 edges
8. `scan_babylon_item()` - 42 edges
9. `RouterOutput` - 41 edges
10. `run_retirement_sweep()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `Catalog family` --references--> `build_catalog_families()`  [INFERRED]
  docs/architecture/catalog-identity.md → src/api/rcars/services/catalog.py
- `Invariant` --references--> `enforce_card_invariant()`  [INFERRED]
  docs/architecture/catalog-identity.md → src/api/rcars/services/catalog_identity.py
- `Root cause` --references--> `AnalysisSignature`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py
- `Summary` --references--> `isArchitecture()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/frontend/src/pages/browse/helpers.ts
- `Curator edits` --references--> `content_owner()`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py

## Import Cycles
- 2-file cycle: `src/api/rcars/services/analysis_identity.py -> src/api/rcars/services/analyzer.py -> src/api/rcars/services/analysis_identity.py`

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

## Communities (240 total, 84 thin omitted)

### Community 0 - "_jira_request"
Cohesion: 0.15
Nodes (9): get_issue_status(), _jira_request(), _move_to_in_progress(), _oauth_config(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_request_with_no_jira_config_raises(), test_request_without_full_oauth_config_raises() (+1 more)

### Community 1 - "Database"
Cohesion: 0.03
Nodes (5): Database, test_advisor_session(), test_enrichment_tags(), test_advisory_lock_is_not_reentrant_across_sessions(), test_database_explicit_test_schema_reset_includes_delivery_queue()

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

### Community 6 - "test_advisor_families.py"
Cohesion: 0.08
Nodes (63): enforce_card_invariant(), family_exclusion_core(), request_with_references(), assert_invariant(), card_ids(), _clear_own_analysis(), item(), link() (+55 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.14
Nodes (12): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats(), test_idempotent_upsert() (+4 more)

### Community 8 - "test_description_analysis.py"
Cohesion: 0.06
Nodes (75): add_tag(), AnalysisSourceRequest, catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+67 more)

### Community 9 - "admin.py"
Cohesion: 0.05
Nodes (61): field_source_report(), health(), readiness(), AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload (+53 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.08
Nodes (34): deliver_pending_events(), comments(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_malformed_page_does_not_prove_absence(), test_comment_missing_credentials_does_not_call_http() (+26 more)

### Community 11 - "Chat Router LLM"
Cohesion: 0.33
Nodes (6): Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, Infrastructure Embedding Search Design

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (24): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+16 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (4): derive_status(), retirement_label(), TestDeriveStatus, TestStepOrder

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_showroom_reuse.py"
Cohesion: 0.07
Nodes (28): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git(), as_donor() (+20 more)

### Community 17 - "ops.py"
Cohesion: 0.10
Nodes (17): Decisions (Nate, 2026-11-19), run_field_source_sync(), build_sandbox_summary(), log_scan_reuse_summary(), publish_progress(), _progress_bridge(), _publish(), run_babylon_pipeline() (+9 more)

### Community 18 - "Any"
Cohesion: 0.13
Nodes (10): CatalogReader, collect(), load(), extract_base_ci_refs(), extract_infrastructure_metadata(), is_agnosticd_v2(), test_refresh_catalog_graph_returns_nodes_and_refresh_catalog_is_unchanged(), test_token_usage() (+2 more)

### Community 19 - ".upsert_babylon_catalog_item"
Cohesion: 0.05
Nodes (29): _seed_label_count_items(), test_facets_platforms_and_tdps(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none() (+21 more)

### Community 20 - "test_catalog_families.py"
Cohesion: 0.15
Nodes (31): build_catalog_families(), _clean(), four_level(), graph(), _item(), members(), node(), _rows() (+23 more)

### Community 21 - "_jira_event_messages"
Cohesion: 0.10
Nodes (9): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_requires_admin(), test_edit_update_skips_cancelled_workflows(), test_edit_without_change_records_no_event() (+1 more)

### Community 22 - "orchestrator.py"
Cohesion: 0.10
Nodes (19): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), build_scaffold(), compose_answer(), _strip_formatting(), _help_answer() (+11 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.13
Nodes (23): buildUrl(), FALLBACK_FORMAT_LABELS, FORMAT_COLORS, RecCard(), RecCardProps, CollapsibleTier(), RecCardList(), RecCardListProps (+15 more)

### Community 25 - "Settings"
Cohesion: 0.07
Nodes (28): llm_provider_status(), submit_chat(), submit_query(), auth_me(), fetch_litemaas_models(), _parse_csv(), Settings, _settings() (+20 more)

### Community 26 - ".close"
Cohesion: 0.06
Nodes (31): db(), db(), seed_infrastructure(), db(), db(), db(), db(), db() (+23 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.20
Nodes (23): ComponentLink, content_owner(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous(), test_curator_content_path_override_is_not_a_pure_stub() (+15 more)

### Community 28 - "Any"
Cohesion: 0.15
Nodes (9): _row(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override(), test_upsert_osspa_item_never_overwrites_llm_owned_fields(), test_upsert_osspa_item_unretires_on_reappearance() (+1 more)

### Community 29 - "seed"
Cohesion: 0.05
Nodes (60): Advisor, Browse, Curator edits, Model, Overlap, Pure stub, Scan, _collapse_families() (+52 more)

### Community 30 - "App.tsx"
Cohesion: 0.07
Nodes (42): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), LlmProviderCard() (+34 more)

### Community 31 - "analysis.py"
Cohesion: 0.07
Nodes (58): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary_unknowns(), list_jobs(), list_role_assignments() (+50 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (71): References, AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr() (+63 more)

### Community 33 - "test_advisor_families.py"
Cohesion: 0.08
Nodes (48): Catalog family, Catalog Identity, Deploy smoke check, Invariant, One owner, Rules for new code, Same content, Stage key (+40 more)

### Community 34 - "test_content_owner.py"
Cohesion: 0.13
Nodes (33): analyze_single(), rescan_all(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner() (+25 more)

### Community 35 - "retirement_jira_events.py"
Cohesion: 0.14
Nodes (9): ensure_issue_event_comment(), jira_auth_configured(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response() (+1 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.23
Nodes (10): Controlled Vocabulary, Difficulty Levels Taxonomy, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy, Learning Objectives Extraction (Stated + Inferred), Module-Level Analysis Output (+2 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.12
Nodes (7): get_vocabulary(), _expand_vocab_aliases(), load_vocabulary(), _noise_variants(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "settings.py"
Cohesion: 0.11
Nodes (12): WorkerContext, run_chat_turn(), on_progress(), run_recommendation(), cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url() (+4 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.21
Nodes (17): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+9 more)

### Community 42 - "pipeline.py"
Cohesion: 0.09
Nodes (13): call_llm(), _fetch_oauth_token(), _get_access_token(), QueryState, _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis(), _format_single_candidate() (+5 more)

### Community 43 - "Candidate"
Cohesion: 0.17
Nodes (9): _run_catalog_second_pass(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published(), test_query_state_defaults(), test_three_layer_workload_propagation() (+1 more)

### Community 44 - "analyzer.py"
Cohesion: 0.09
Nodes (26): check_showroom_stale(), classify_scan_error(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content() (+18 more)

### Community 45 - "test_showroom_rebuild.py"
Cohesion: 0.23
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 46 - "compute_sales_impact"
Cohesion: 0.10
Nodes (7): _build_windowed_metrics(), compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), TestBuildWindowedMetrics, TestComputePerformanceScore

### Community 47 - "api.ts"
Cohesion: 0.09
Nodes (54): CollapsibleFilterGroup(), CollapsibleFilterGroupProps, render(), LabelFilterGroup(), LabelFilterGroupProps, fmtTargetDate(), isInProgress(), isRecommended() (+46 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.12
Nodes (4): normalize_analysis(), _record_unknowns(), TestIgnoredTermsSuppression, TestNormalizeAnalysis

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "._artifact_connection"
Cohesion: 0.08
Nodes (3): _reference_summary(), test_audience_filter_applies_across_content_types(), TestReviewBadgeUntouched

### Community 51 - "structlog"
Cohesion: 0.17
Nodes (13): _add_component(), get_logger(), _reorder_keys(), setup_logging(), test_logger_outputs_json(), test_logger_with_job_id(), _lines(), test_bound_inside_job_and_cleared_after() (+5 more)

### Community 52 - "main"
Cohesion: 0.32
Nodes (3): main(), test_execute_requires_scans_paused_confirmation(), test_script_rejects_selection_with_no_showroom_items()

### Community 53 - "test_analysis_identity.py"
Cohesion: 0.07
Nodes (25): compute_content_hash(), donor_matches_commit(), donor_matches_content(), _donor_signature(), pre_clone_key(), _signature(), AnalysisSignature, signatures_match() (+17 more)

### Community 54 - "Vocabulary"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "test_osspa_analysis.py"
Cohesion: 0.16
Nodes (11): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms(), test_analyze_uses_the_dedicated_model_when_configured() (+3 more)

### Community 56 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (19): asset_type_tokens(), fetch_palist_csv(), OsspaSyncError, parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status() (+11 more)

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

### Community 61 - "create_app"
Cohesion: 0.05
Nodes (20): create_app(), RequestLoggingMiddleware, client(), client(), test_auth_me_unauthenticated(), client(), client(), client() (+12 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.15
Nodes (8): client(), _second_architecture(), settings(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "with"
Cohesion: 0.07
Nodes (31): runs-on, steps, environment, needs, runs-on, steps, name, url (+23 more)

### Community 65 - "test_overlap_chat_families.py"
Cohesion: 0.09
Nodes (34): exclusion_set_for(), lift_to_covering(), pattern_check(), resolve_item(), TestUnauthenticatedAccess, test_pattern_check_url_and_lb(), add(), link() (+26 more)

### Community 66 - "test_field_source_sync.py"
Cohesion: 0.08
Nodes (18): client(), test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_field_source_route_registered(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source() (+10 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.12
Nodes (12): _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _mcp_call() (+4 more)

### Community 68 - "build_analysis_prompt"
Cohesion: 0.15
Nodes (5): canonical_content(), build_analysis_prompt(), build_description_prompt(), truncate_content(), TestPromptInjection

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "HandsOnDriver"
Cohesion: 0.14
Nodes (9): HandsOnDriver, Candidate, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming(), test_hands_on_serialize_with_performance(), test_hands_on_triage_guidance() (+1 more)

### Community 73 - "json"
Cohesion: 0.18
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 74 - "generate_embedding"
Cohesion: 0.13
Nodes (10): build_infrastructure_embedding_text(), generate_embedding(), _get_embedding_client(), analyze_config(), analyze_role(), _normalize_products(), _vocabulary_product_hint(), test_build_infrastructure_embedding_text() (+2 more)

### Community 75 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.06
Nodes (33): 1. Content-Type Drivers, 2. Orchestrator and Pipeline, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers (+25 more)

### Community 76 - "routes/auth.py"
Cohesion: 0.20
Nodes (14): invalidate_api_key_cache(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token(), _user_max_role() (+6 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 79 - "command"
Cohesion: 0.11
Nodes (15): command, check_card_families(), flag(), get_db(), infra_stats(), init_db(), note(), override_url() (+7 more)

### Community 80 - "is_content_excluded"
Cohesion: 0.18
Nodes (9): Anti-goals, Approaches considered, Deployment, Description-Based Analysis for Items With No Showroom — Design, Goals, Intent, Non-goals, Open items for the builder (+1 more)

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.13
Nodes (16): resolve_showroom_source(), unresolved(), walk(), SourceNode, legacy_test_item(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(), test_existing_test_vectors_never_enter_content_retrieval() (+8 more)

### Community 82 - "test_drivers.py"
Cohesion: 0.09
Nodes (18): ContentTypeDriver, _extract_duration_target(), get_driver(), get_drivers_for_types(), _init_drivers(), _register(), format_triage_candidates(), test_candidate_universal_fields() (+10 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.07
Nodes (13): _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), _build_nonprod_provisions_sql(), TestListNonprodItems, TestNonprodIgnore, TestNonprodProvisionsSql, TestNonprodRouteExists (+5 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.09
Nodes (38): run_retirement_sweep(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancellation_does_not_mark_concurrently_retired_item(), test_manual_pr_creation_respects_cleanup_lock(), test_merged_revert_still_deletes_workflow() (+30 more)

### Community 85 - "ArchitectureDriver"
Cohesion: 0.20
Nodes (8): ArchitectureDriver, _primary_asset_type(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 86 - "middleware/auth.py"
Cohesion: 0.07
Nodes (18): _fetch_group_members(), get_current_user(), _parse_sa_allowlist(), _user_in_groups(), _validate_sa_token(), _make_request(), _mock_async_client(), _mock_async_client_get() (+10 more)

### Community 87 - "extract_catalog_item"
Cohesion: 0.11
Nodes (14): Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+6 more)

### Community 88 - "cli.py"
Cohesion: 0.12
Nodes (11): concurrency, cancel-in-progress, group, infra_group(), osspa_group(), refresh(), reporting_db_group(), retirement_group() (+3 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.12
Nodes (15): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+7 more)

### Community 90 - "reporting_db_show"
Cohesion: 0.14
Nodes (6): _print(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 91 - "pytest"
Cohesion: 0.05
Nodes (13): lifespan(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists(), TestCreateApiKey, TestListApiKeys, TestExpiredApiKey (+5 more)

### Community 92 - "LLMResult"
Cohesion: 0.18
Nodes (13): _call_litemaas_inner(), LLMResult, _extract_json(), route(), llm(), _fake(), llm_call(), test_call_error_falls_back() (+5 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.08
Nodes (46): start_scan(), InvalidShowroomRef, order_for_reuse(), resolve_commits(), showroom_reuse_key(), item_reuse_key(), scan_babylon_item(), run_stale_check() (+38 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "chat/models.py"
Cohesion: 0.13
Nodes (18): Chip, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs, PerformanceArgs (+10 more)

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "showroom_source.py"
Cohesion: 0.07
Nodes (35): 3. Scan pipeline branch, 4. Candidate selection and stale check, Constraints, compute_analysis_config(), fingerprint(), analysis_from_row(), analyze_description(), analyze_showroom() (+27 more)

### Community 101 - "seed_chat_fixtures"
Cohesion: 0.10
Nodes (23): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted(), test_pack_includes_shared_workload_note(), _noop() (+15 more)

### Community 102 - "test_vocabulary_admin.py"
Cohesion: 0.14
Nodes (4): clear_vocabulary_cache(), client(), TestRoleGating, TestVocabularyEndpoints

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "CLAUDE.md — Project Instructions"
Cohesion: 0.18
Nodes (13): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API, PostgreSQL with pgvector (+5 more)

### Community 105 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 106 - ".create_job"
Cohesion: 0.22
Nodes (6): _do(), test_job_failure(), test_job_lifecycle(), test_list_jobs(), test_list_jobs_shows_running_before_newer_queued(), test_queued_job_keeps_progress_json()

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (10): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+2 more)

### Community 108 - "osspa_sync.py"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 109 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 111 - "middleware/auth.py"
Cohesion: 0.13
Nodes (12): Key Patterns, _check_api_key_role_ceiling(), _get_cached_role_assignments(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), require_performance_view() (+4 more)

### Community 112 - "workers/base.py"
Cohesion: 0.14
Nodes (15): Frontend Progress Display, What Stays Unchanged, stream_job(), create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives() (+7 more)

### Community 113 - "option"
Cohesion: 0.13
Nodes (7): cli(), osspa_sync_cmd(), overlap_candidates_cmd(), scan(), status(), vocab_stage_rescan(), vocab_unknowns()

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - "analyze_role"
Cohesion: 0.14
Nodes (6): discover_roles(), _follow_task_includes(), read_config_code(), read_role_code(), test_read_config_code(), test_enriched_prompt_requests_structured_output()

### Community 120 - "mcp_query"
Cohesion: 0.27
Nodes (3): mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 121 - "_resolve_item_by_name"
Cohesion: 0.22
Nodes (3): _prefix_overlap(), _find_keyword_ties(), _resolve_item_by_name()

### Community 122 - "_expand_query_terms"
Cohesion: 0.09
Nodes (7): _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 123 - "_FakeResponse"
Cohesion: 0.13
Nodes (11): _FakeResponse, _header(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen(), test_oauth_token_request_format(), fake_urlopen() (+3 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.17
Nodes (13): check_pr_statuses(), _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira(), _close_open_pr(), complete_retirement() (+5 more)

### Community 127 - "_generate_key"
Cohesion: 0.11
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 129 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 130 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 131 - "_close_issue"
Cohesion: 0.12
Nodes (10): _close_issue(), close_issue_done(), close_issue_wont_do(), _issue_is_closed(), test_already_closed_issue_needs_no_transition(), test_closure_requires_a_terminal_result(), test_new_closure_requires_the_requested_resolution(), test_required_closure_selects_resolution_and_verifies_result() (+2 more)

### Community 133 - "ls_remote_sha"
Cohesion: 0.17
Nodes (7): commit_for_ref(), _is_github_throttle(), ls_remote_refs(), ls_remote_sha(), resolve(), _resolve_ref_from_lookup(), _run_git_with_retry()

### Community 135 - ".upsert_babylon_catalog_item"
Cohesion: 0.07
Nodes (29): _do(), test_upsert_stores_labels(), test_content_path(), test_list_catalog_items(), test_retire_missing_babylon_ignores_other_sources(), test_upsert_and_get_catalog_item(), test_upsert_updates_existing(), test_babylon_upsert_writes_status_from_stage() (+21 more)

### Community 136 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - "services/catalog.py"
Cohesion: 0.11
Nodes (11): _apply_component_inheritance(), CatalogFamilies, _collect_bases(), component_item_to_ci_name(), _content_fields(), extract_showroom_url(), parse_workload_fqcn(), _resolve_template_var() (+3 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.16
Nodes (26): LLM Provider Routing (LiteMaaS / Vertex AI), dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System (+18 more)

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
Cohesion: 0.22
Nodes (6): clean_infra(), db(), test_get_infrastructure_with_item_counts(), test_list_infrastructure_with_type_filter(), test_upsert_infrastructure_insert(), test_upsert_infrastructure_update()

### Community 159 - "scan_configs"
Cohesion: 0.21
Nodes (4): regenerate_embeddings(), scan_all_collections(), scan_collection(), scan_configs()

### Community 160 - "Python Dependency Manifest (requirements.lock)"
Cohesion: 0.22
Nodes (9): Anthropic SDK Dependency (v0.120.0), arq Dependency (v0.28.0), Python Dependency Manifest (requirements.lock), FastAPI Dependency (v0.140.7), OpenAI SDK Dependency (v2.49.0), psycopg Dependency (v3.3.4), Pydantic Dependency (v2.13.4), Redis Client Dependency (v5.3.1) (+1 more)

### Community 161 - "workflow_lock_id"
Cohesion: 0.26
Nodes (8): workflow_lock_id(), _approved_unstarted(), test_start_retirement_holds_lock_while_creating_ticket(), fake_create(), test_start_retirement_respects_workflow_lock(), _prepare(), test_route_rejects_when_workflow_lock_held(), test_route_releases_lock_after_request()

### Community 162 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 163 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 169 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 174 - "advisor.py"
Cohesion: 0.08
Nodes (13): _get_user_key(), ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest (+5 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "RouterOutput"
Cohesion: 0.19
Nodes (20): Clarify, RouterOutput, Scope, _guess_clarification(), _parse_catalog_url(), resolve_and_verify(), _result_turns(), _turn_chips() (+12 more)

### Community 180 - "test_cancel_preserves_tracking_on_github_failure"
Cohesion: 0.22
Nodes (5): test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_stops_removal_before_creating_revert(), test_retired_items_cannot_be_cancelled(), close_jira(), state()

### Community 183 - "handlers.py"
Cohesion: 0.11
Nodes (28): get_item_workloads(), get_performance_scores(), _analysis(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+20 more)

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 185 - "build_retirement_description"
Cohesion: 0.20
Nodes (5): Open Questions / Risks, _base_name_from_content_id(), build_retirement_description(), test_no_replacement(), test_wiki_markup_format()

### Community 187 - "_sync_nonprod_usage"
Cohesion: 0.33
Nodes (3): _nonprod_metrics(), _sync_nonprod_usage(), TestSyncNonprodUsage

### Community 189 - "with_job_context"
Cohesion: 0.21
Nodes (7): run_nightly_pipeline(), test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes()

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

### Community 195 - "solutions"
Cohesion: 0.50
Nodes (4): solutions, aliases, is_tdp, name

### Community 196 - "ansible.builtin.assert"
Cohesion: 0.67
Nodes (3): fail_msg, that, ansible.builtin.assert

### Community 203 - "family_members"
Cohesion: 0.43
Nodes (5): declares_or_overrides_content(), family_members(), _keep(), walk(), FamilyMember

### Community 210 - "Design"
Cohesion: 0.33
Nodes (6): 1. Storage, 2. Source resolution, 5. API, 6. Frontend, 7. Coverage math, Design

### Community 217 - "content_similarity Table"
Cohesion: 0.67
Nodes (3): Evidence Pack, content_similarity Table, overlap_candidates Table

### Community 218 - "Content Owner Model for Virtual CIs — Design"
Cohesion: 0.29
Nodes (6): Content Owner Model for Virtual CIs — Design, Problem, Rollout, Root cause, Tests, What gets removed

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1498 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **84 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `_reference_context`, `.upsert_babylon_catalog_item`, `db/__init__.py`, `test_retirement_jira_events.py`, `test_overlap_assessment.py`, `ops.py`, `Any`, `.upsert_babylon_catalog_item`, `_jira_event_messages`, `orchestrator.py`, `Settings`, `.close`, `test_showroom_source.py`, `Any`, `seed`, `.upsert_infrastructure`, `scan_configs`, `test_advisor_families.py`, `workflow_lock_id`, `settings.py`, `pipeline.py`, `extract_base_name`, `test_api_infrastructure.py`, `._artifact_connection`, `RouterOutput`, `main`, `test_analysis_identity.py`, `test_osspa_analysis.py`, `handlers.py`, `run_osspa_sync`, `TestGetNonprodBaseNames`, `test_catalog_osspa_routes.py`, `.get_unknown_terms`, `test_overlap_chat_families.py`, `test_field_source_sync.py`, `generate_embedding`, `Advisor v2 — Content-Type Drivers`, `command`, `is_content_excluded`, `test_nonprod.py`, `test_retirement_pr_status.py`, `reporting_db_show`, `pytest`, `showroom_source.py`, `seed_chat_fixtures`, `.create_job`, `_resolve_item_by_name`, `_generate_key`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `Database` (e.g. with `One owner` and `lifespan()`) actually correct?**
  _`Database` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.0257703081232493 - nodes in this community are weakly interconnected._
- **Why does `Advisor v2 — Content-Type Drivers` connect `Advisor v2 — Content-Type Drivers` to `workers/base.py`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Should `react` be split into smaller, more focused modules?**
  _Cohesion score 0.07197763801537387 - nodes in this community are weakly interconnected._