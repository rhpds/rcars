# Graph Report - rhdpcd-2297-advisor  (2026-11-24)

## Corpus Check
- 300 files · ~327,785 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4362 nodes · 10840 edges · 227 communities (152 shown, 75 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1045 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d36d0348`
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
- Chat Router LLM
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_showroom_reuse.py
- ops.py
- analyze_role
- .upsert_babylon_catalog_item
- test_catalog_families.py
- _jira_event_messages
- orchestrator.py
- test_osspa_adoc.py
- react
- Settings
- route
- test_showroom_source.py
- schemas.py
- seed
- App.tsx
- router.py
- test_agv_access.py
- test_advisor_families.py
- test_showroom_recommendation_isolation.py
- test_drivers.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- test_worker_job_context.py
- compilerOptions
- test_jira_service.py
- structlog
- test_services.py
- analyzer.py
- test_osspa_csv.py
- compute_sales_impact
- api.ts
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- analysis.py
- TestSpoofedProxyHeaders
- test_analysis_identity.py
- Vocabulary
- test_drivers.py
- Path
- run_osspa_sync
- loader.py
- Retirement System
- parse_analysis_response
- test_osspa_analysis.py
- test_catalog_osspa_routes.py
- SyncPage.tsx
- with
- .get_content_entity
- test_field_source_sync.py
- reporting_sync.py
- analyzer.py
- test_field_source_db.py
- api.ts
- ECA Production Redesign Spec
- Candidate
- json
- chat_sessions.py
- MemoryArtifacts
- routes/auth.py
- TestValidation
- test_retirement_route_locks.py
- command
- Description-Based Analysis for Items With No Showroom — Design
- test_test_content_exclusion.py
- test_api_keys_db.py
- test_nonprod.py
- test_retirement_pr_status.py
- create_app
- middleware/auth.py
- _print
- ContentTypeDriver
- build_retirement_description
- hands_on.py
- jira.py
- test_auth_middleware.py
- test_showroom_scan.py
- osspa_sync.py
- Showroom analysis isolation
- Scan Pipeline
- advisor.py
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- order_for_reuse
- Candidate
- TestVocabularyEndpoints
- rcars-login.sh
- CLAUDE.md — Project Instructions
- json
- database.py
- RCARS OCP Deployment Playbook
- test_workers.py
- Rec Card Duration and Best Fit Spec
- Field Source Content
- workers/base.py
- showroom_source.py
- content_entities Table
- TestRetirementDashboardMetrics
- Deploy Docs GitHub Actions Workflow
- Change Detection
- test_advisor_session
- Overlap Detection Redesign
- test_reporting.py
- TestBuildWindowedMetrics
- build_embedding_text
- ContentAnalysisPage.tsx
- test_orphan_cleanup.py
- retirement_cleanup.py
- test_llm_routing.py
- TestStepOrder
- vocabulary.yaml
- pre_tasks
- build_analysis_prompt
- router.py
- test_llm_provider_status.py
- handlers.py
- ._set_showroom_override
- with_job_context
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
- client
- block
- post_tasks
- action_verbs
- .upsert_infrastructure
- scan
- Python Dependency Manifest (requirements.lock)
- pytest
- option
- deploy.yml
- LLM Overlap Assessment Design
- rcars
- rcars
- tasks
- Match Event Prompt Template
- extract_base_name
- test_already_closed_issue_needs_no_transition
- test_content_owner.py
- test_vocabulary.py
- Python Requirements Entry Point
- Advisor v2 — Content-Type Drivers
- TestNonprodSchema
- settings.py
- content_similarity Table
- TestTokenExchange
- ignored_terms
- extract_catalog_item
- mcp_query
- test_api_infrastructure.py
- TestGetNonprodBaseNames
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- TestCreateApiKey
- solutions
- ansible.builtin.assert
- ResolvedShowroom
- test_edit_update_skips_cancelled_workflows
- Browse Page Redesign Spec
- OsspaSyncError
- build_infrastructure_embedding_text
- test_routing_golden
- AdocRead
- TestRevokeApiKey
- TestRoleCeiling

## God Nodes (most connected - your core abstractions)
1. `Database` - 309 edges
2. `Settings` - 179 edges
3. `load_vocabulary()` - 68 edges
4. `seed()` - 50 edges
5. `Candidate` - 48 edges
6. `create_app()` - 43 edges
7. `scan_babylon_item()` - 42 edges
8. `run_retirement_sweep()` - 39 edges
9. `ResolvedShowroom` - 36 edges
10. `react` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Root cause` --references--> `AnalysisSignature`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py
- `Anti-goals` --references--> `is_content_excluded()`  [INFERRED]
  docs/superpowers/specs/2026-11-17-description-analysis-design.md → src/api/rcars/services/showroom_source.py
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

## Communities (227 total, 75 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.10
Nodes (18): _get_access_token(), _jira_request(), _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen() (+10 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (35): Database, main(), db(), seed_infrastructure(), db(), db(), db(), db() (+27 more)

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
Cohesion: 0.13
Nodes (13): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), seed_items(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats() (+5 more)

### Community 8 - "test_description_analysis.py"
Cohesion: 0.06
Nodes (74): add_tag(), AnalysisSourceRequest, catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+66 more)

### Community 9 - "admin.py"
Cohesion: 0.12
Nodes (26): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+18 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.06
Nodes (42): ensure_issue_event_comment(), jira_auth_configured(), deliver_pending_events(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), comments(), event_time() (+34 more)

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
Cohesion: 0.08
Nodes (3): derive_status(), retirement_label(), TestDeriveStatus

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_showroom_reuse.py"
Cohesion: 0.15
Nodes (20): as_donor(), donor_row(), prime(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_description_analysis_is_never_a_showroom_donor(), test_different_ci_with_the_same_files_reuses_only_once_context_is_out_of_the_config(), test_different_content_path_in_one_repo_is_not_reused() (+12 more)

### Community 17 - "ops.py"
Cohesion: 0.09
Nodes (20): Decisions (Nate, 2026-11-19), log_catalog_families(), run_field_source_sync(), build_sandbox_summary(), log_scan_reuse_summary(), scan_all_collections(), publish_progress(), _progress_bridge() (+12 more)

### Community 18 - "analyze_role"
Cohesion: 0.10
Nodes (13): call_llm(), generate_embedding(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products(), read_config_code() (+5 more)

### Community 19 - ".upsert_babylon_catalog_item"
Cohesion: 0.04
Nodes (55): Decisions, _seed_label_count_items(), test_facets_platforms_and_tdps(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2() (+47 more)

### Community 20 - "test_catalog_families.py"
Cohesion: 0.14
Nodes (32): build_catalog_families(), _clean(), four_level(), graph(), _item(), members(), node(), _rows() (+24 more)

### Community 21 - "_jira_event_messages"
Cohesion: 0.12
Nodes (8): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_requires_admin(), test_edit_without_change_records_no_event(), test_edit_without_jira_key_records_no_event()

### Community 22 - "orchestrator.py"
Cohesion: 0.22
Nodes (10): build_scaffold(), compose_answer(), _strip_formatting(), _help_answer(), process_turn(), _scope_echo(), followup_chips(), test_answer_failure_degrades_to_scaffold() (+2 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (24): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), git() (+16 more)

### Community 24 - "react"
Cohesion: 0.13
Nodes (23): buildUrl(), FALLBACK_FORMAT_LABELS, FORMAT_COLORS, RecCard(), RecCardProps, CollapsibleTier(), RecCardList(), RecCardListProps (+15 more)

### Community 25 - "Settings"
Cohesion: 0.09
Nodes (22): fetch_litemaas_models(), _parse_csv(), Settings, _FakeModels, _litemaas_settings(), _patch_litemaas_client(), test_admin_check(), test_call_llm_propagates_litemaas_error() (+14 more)

### Community 26 - "route"
Cohesion: 0.21
Nodes (12): _call_litemaas_inner(), LLMResult, _extract_json(), route(), llm(), _fake(), llm_call(), test_call_error_falls_back() (+4 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.14
Nodes (27): CatalogReader, ComponentLink, content_owner(), item_family_key(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage() (+19 more)

### Community 28 - "schemas.py"
Cohesion: 0.06
Nodes (58): health(), readiness(), AgvPrResponse, ApiKeyInfo, ApiKeyListResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse (+50 more)

### Community 29 - "seed"
Cohesion: 0.11
Nodes (30): ResolvedShowroom, db(), snapshots(), test_dry_run_performs_no_writes(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data(), test_reset_rejects_non_babylon_or_missing_ids_atomically(), test_reset_rejects_running_or_queued_analysis_jobs() (+22 more)

### Community 30 - "App.tsx"
Cohesion: 0.07
Nodes (42): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), LlmProviderCard() (+34 more)

### Community 31 - "router.py"
Cohesion: 0.14
Nodes (17): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+9 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 33 - "test_advisor_families.py"
Cohesion: 0.07
Nodes (69): _best(), cards_sharing_a_family(), collapse_to_cards(), CollapseStats, enforce_card_invariant(), family_violations(), merge_stage_copies(), assert_invariant() (+61 more)

### Community 34 - "test_showroom_recommendation_isolation.py"
Cohesion: 0.23
Nodes (17): add_stub(), link(), search(), test_a_stage_copy_is_never_swapped_in_when_it_was_not_a_hit(), test_ci_reference_to_a_stub_resolves_through_its_owner(), test_each_owner_promotes_to_its_own_stub(), test_independent_ids_keep_their_own_scores(), test_owner_hit_is_shown_as_its_only_stub() (+9 more)

### Community 35 - "test_drivers.py"
Cohesion: 0.17
Nodes (10): get_drivers_for_types(), format_triage_candidates(), _make_hands_on_candidate(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_get_drivers_for_types_groups(), test_hands_on_serialize_streaming(), test_hands_on_serialize_with_performance() (+2 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.23
Nodes (10): Controlled Vocabulary, Difficulty Levels Taxonomy, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy, Learning Objectives Extraction (Stated + Inferred), Module-Level Analysis Output (+2 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.13
Nodes (5): load_vocabulary(), _noise_variants(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "test_worker_job_context.py"
Cohesion: 0.16
Nodes (14): _add_component(), get_logger(), _reorder_keys(), setup_logging(), test_logger_outputs_json(), test_logger_with_job_id(), _clean(), _lines() (+6 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.18
Nodes (19): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+11 more)

### Community 42 - "structlog"
Cohesion: 0.07
Nodes (27): 2. Orchestrator and Pipeline, What Gets Deleted, registered_content_types(), QueryState, run_category(), serialize_candidates(), run_query(), _run_one() (+19 more)

### Community 43 - "test_services.py"
Cohesion: 0.15
Nodes (9): _apply_component_inheritance(), _collect_bases(), _run_catalog_second_pass(), test_candidate_tier_defaults(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published(), test_three_layer_workload_propagation() (+1 more)

### Community 44 - "analyzer.py"
Cohesion: 0.10
Nodes (25): check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content(), test_content_path_antora_start_path_resolves_pages_and_nav() (+17 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.25
Nodes (16): asset_type_tokens(), parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status(), test_normalize_row_builds_the_upsert_payload(), test_normalize_row_dedups_topics_from_solutions_and_verticals() (+8 more)

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
Nodes (43): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_pr_statuses(), check_stale(), edit_retirement() (+35 more)

### Community 53 - "test_analysis_identity.py"
Cohesion: 0.07
Nodes (27): Constraints, canonical_content(), compute_content_hash(), donor_matches_commit(), donor_matches_content(), _donor_signature(), pre_clone_key(), _signature() (+19 more)

### Community 54 - "Vocabulary"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "test_drivers.py"
Cohesion: 0.17
Nodes (8): ArchitectureDriver, _primary_asset_type(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 56 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 57 - "run_osspa_sync"
Cohesion: 0.31
Nodes (16): run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items(), test_missing_detail_page_marks_stale_and_skips() (+8 more)

### Community 58 - "loader.py"
Cohesion: 0.12
Nodes (12): _entries_to_dicts(), _as_tuple(), _build_lookups(), _parse_entries(), _validate(), squash_key(), VocabEntry, Vocabulary (+4 more)

### Community 59 - "Retirement System"
Cohesion: 0.08
Nodes (25): AgV Access Layer, Architecture, Authentication and Scope, Automatic Removal Eligibility, Cancellation and Recovery, Catalog Soft-Delete, Checking Merges, Code Organization (+17 more)

### Community 60 - "parse_analysis_response"
Cohesion: 0.11
Nodes (10): _expand_vocab_aliases(), _find_keyword_ties(), resolve_item(), _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url() (+2 more)

### Community 61 - "test_osspa_analysis.py"
Cohesion: 0.16
Nodes (11): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms(), test_analyze_uses_the_dedicated_model_when_configured() (+3 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.15
Nodes (8): client(), _second_architecture(), settings(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "with"
Cohesion: 0.07
Nodes (31): runs-on, steps, environment, needs, runs-on, steps, name, url (+23 more)

### Community 65 - ".get_content_entity"
Cohesion: 0.07
Nodes (13): test_audience_filter_applies_across_content_types(), test_token_usage(), _row(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch() (+5 more)

### Community 66 - "test_field_source_sync.py"
Cohesion: 0.14
Nodes (11): test_upsert_and_query_field_source(), test_upsert_updates_retired_at(), FakeSettings, _mock_mcp_query(), _row(), test_field_source_sync_captures_user_email(), test_field_source_sync_ignores_agd_v2_items(), tracking_mock() (+3 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.14
Nodes (12): _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _build_windowed_metrics() (+4 more)

### Community 68 - "analyzer.py"
Cohesion: 0.07
Nodes (29): compute_analysis_config(), fingerprint(), analysis_from_row(), analyze_description(), build_description_prompt(), build_module_embedding_text(), commit_for_ref(), compute_analysis_input_hash() (+21 more)

### Community 69 - "test_field_source_db.py"
Cohesion: 0.18
Nodes (5): test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert()

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "Candidate"
Cohesion: 0.21
Nodes (4): HandsOnDriver, test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_triage_guidance()

### Community 73 - "json"
Cohesion: 0.18
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 74 - "chat_sessions.py"
Cohesion: 0.10
Nodes (11): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), _prefix_overlap(), build_jira_event(), test_chat_append_checks_ownership(), _log() (+3 more)

### Community 75 - "MemoryArtifacts"
Cohesion: 0.17
Nodes (3): MemoryArtifacts, scan(), run()

### Community 76 - "routes/auth.py"
Cohesion: 0.20
Nodes (13): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+5 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "test_retirement_route_locks.py"
Cohesion: 0.27
Nodes (4): client(), _prepare(), test_route_rejects_when_workflow_lock_held(), test_route_releases_lock_after_request()

### Community 79 - "command"
Cohesion: 0.12
Nodes (15): command, check_card_families(), flag(), get_db(), infra_stats(), init_db(), note(), override_url() (+7 more)

### Community 80 - "Description-Based Analysis for Items With No Showroom — Design"
Cohesion: 0.22
Nodes (7): Anti-goals, Deployment, Description-Based Analysis for Items With No Showroom — Design, Goals, Intent, Non-goals, Open items for the builder

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.06
Nodes (33): Advisor, Browse, Curator edits, Model, Overlap, Pure stub, Scan, Approaches considered (+25 more)

### Community 82 - "test_api_keys_db.py"
Cohesion: 0.16
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 83 - "test_nonprod.py"
Cohesion: 0.07
Nodes (14): _nonprod_retirement_metrics(), _retirement_metrics(), _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestListNonprodItems, TestNonprodIgnore, TestNonprodProvisionsSql (+6 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.07
Nodes (50): workflow_lock_id(), run_retirement_sweep(), test_lifecycle_old_closed_workflows_do_not_backfill(), _approved_unstarted(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup() (+42 more)

### Community 85 - "create_app"
Cohesion: 0.05
Nodes (19): create_app(), lifespan(), RequestLoggingMiddleware, client(), client(), test_auth_me_unauthenticated(), client(), app_no_auth() (+11 more)

### Community 86 - "middleware/auth.py"
Cohesion: 0.08
Nodes (21): Key Patterns, _check_api_key_role_ceiling(), _get_cached_role_assignments(), get_current_user(), _log_auth_decision(), _parse_sa_allowlist(), require_admin(), require_auth() (+13 more)

### Community 87 - "_print"
Cohesion: 0.16
Nodes (6): _print(), reporting_db_show(), reporting_db_status(), reporting_db_sync(), retirement_sweep_cmd(), _sweep()

### Community 88 - "ContentTypeDriver"
Cohesion: 0.15
Nodes (7): ContentTypeDriver, get_driver(), _init_drivers(), _register(), test_get_driver_architecture(), test_get_driver_lab(), test_get_driver_unknown_raises()

### Community 89 - "build_retirement_description"
Cohesion: 0.08
Nodes (20): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+12 more)

### Community 91 - "jira.py"
Cohesion: 0.08
Nodes (13): _close_issue(), close_issue_done(), close_issue_wont_do(), _fetch_oauth_token(), get_issue_status(), _issue_is_closed(), _move_to_in_progress(), _oauth_config() (+5 more)

### Community 92 - "test_auth_middleware.py"
Cohesion: 0.14
Nodes (9): _fetch_group_members(), _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response(), TestGroupLookup (+1 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.08
Nodes (45): InvalidShowroomRef, showroom_reuse_key(), item_reuse_key(), scan_babylon_item(), run_stale_check(), run_analysis(), add_item(), commit_of() (+37 more)

### Community 94 - "osspa_sync.py"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "advisor.py"
Cohesion: 0.08
Nodes (16): _get_user_key(), ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest (+8 more)

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "order_for_reuse"
Cohesion: 0.22
Nodes (7): Content Owner Model for Virtual CIs — Design, Problem, Rollout, Root cause, Tests, What gets removed, order_for_reuse()

### Community 101 - "Candidate"
Cohesion: 0.10
Nodes (10): 1. Content-Type Drivers, Adding a New Content Type, Driver Interface, What Moves Into Drivers, Candidate, _format_single_candidate(), test_candidate_universal_fields(), test_candidate_with_type_data() (+2 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "CLAUDE.md — Project Instructions"
Cohesion: 0.18
Nodes (13): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API, PostgreSQL with pgvector (+5 more)

### Community 105 - "json"
Cohesion: 0.25
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 106 - "database.py"
Cohesion: 0.14
Nodes (18): build_evidence_pack(), seed_chat_fixtures(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted(), test_pack_includes_shared_workload_note(), _noop(), _res(), _settings() (+10 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (10): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+2 more)

### Community 108 - "test_workers.py"
Cohesion: 0.28
Nodes (6): test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes()

### Community 111 - "Field Source Content"
Cohesion: 0.29
Nodes (6): API, Data Import, Data Source, Field Source Content, Frontend, git_repo()

### Community 112 - "workers/base.py"
Cohesion: 0.14
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 113 - "showroom_source.py"
Cohesion: 0.18
Nodes (8): analysis_artifacts_complete(), declares_or_overrides_content(), family_members(), _keep(), walk(), FamilyMember, signatures_match(), SourceNode

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 120 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 123 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.22
Nodes (10): _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable() (+2 more)

### Community 126 - "test_llm_routing.py"
Cohesion: 0.19
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 129 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 130 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 131 - "build_analysis_prompt"
Cohesion: 0.20
Nodes (3): build_analysis_prompt(), truncate_content(), TestPromptInjection

### Community 132 - "router.py"
Cohesion: 0.17
Nodes (19): RouterOutput, Scope, _parse_catalog_url(), pattern_check(), resolve_and_verify(), _result_turns(), _turn_chips(), extract_urls() (+11 more)

### Community 133 - "test_llm_provider_status.py"
Cohesion: 0.28
Nodes (4): _make_client(), no_litemaas_fetch(), test_lists_model_for_every_llm_use(), test_litemaas_active_with_models()

### Community 134 - "handlers.py"
Cohesion: 0.25
Nodes (15): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+7 more)

### Community 135 - "._set_showroom_override"
Cohesion: 0.10
Nodes (8): _do(), _do(), test_content_path(), test_job_failure(), test_job_lifecycle(), test_list_jobs(), test_list_jobs_shows_running_before_newer_queued(), test_queued_job_keeps_progress_json()

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - "services/catalog.py"
Cohesion: 0.07
Nodes (20): Non-goals, CatalogFamilies, collect(), load(), component_item_to_ci_name(), _content_fields(), extract_base_ci_refs(), extract_catalog_item() (+12 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.16
Nodes (26): LLM Provider Routing (LiteMaaS / Vertex AI), dev-services.sh Local Development Launcher, Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System (+18 more)

### Community 154 - "client"
Cohesion: 0.33
Nodes (3): clear_vocabulary_cache(), client(), TestRoleGating

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
Cohesion: 0.23
Nodes (5): clean_infra(), test_get_infrastructure_with_item_counts(), test_list_infrastructure_with_type_filter(), test_upsert_infrastructure_insert(), test_upsert_infrastructure_update()

### Community 160 - "Python Dependency Manifest (requirements.lock)"
Cohesion: 0.22
Nodes (9): Anthropic SDK Dependency (v0.120.0), arq Dependency (v0.28.0), Python Dependency Manifest (requirements.lock), FastAPI Dependency (v0.140.7), OpenAI SDK Dependency (v2.49.0), psycopg Dependency (v3.3.4), Pydantic Dependency (v2.13.4), Redis Client Dependency (v5.3.1) (+1 more)

### Community 161 - "pytest"
Cohesion: 0.05
Nodes (16): test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists(), TestListApiKeys, TestExpiredApiKey, TestRevokedApiKey, TestUnauthenticatedAccess (+8 more)

### Community 162 - "option"
Cohesion: 0.15
Nodes (6): cli(), osspa_sync_cmd(), serve(), status(), vocab_stage_rescan(), vocab_unknowns()

### Community 163 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 169 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 173 - "test_already_closed_issue_needs_no_transition"
Cohesion: 0.40
Nodes (3): test_already_closed_issue_needs_no_transition(), test_required_closure_selects_resolution_and_verifies_result(), request()

### Community 174 - "test_content_owner.py"
Cohesion: 0.14
Nodes (30): rescan_all(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner(), test_browse_difficulty_filter_finds_a_stub_by_its_mirrored_card() (+22 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.10
Nodes (19): 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy (+11 more)

### Community 181 - "settings.py"
Cohesion: 0.10
Nodes (13): WorkerContext, run_chat_turn(), on_progress(), run_recommendation(), on_progress(), cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings (+5 more)

### Community 182 - "content_similarity Table"
Cohesion: 0.67
Nodes (3): Evidence Pack, content_similarity Table, overlap_candidates Table

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 185 - "extract_catalog_item"
Cohesion: 0.25
Nodes (7): Anti-goals, Constraints, Goals, Left to the builder, Platform and Technical Decision Point filters — design, Rollout, Why

### Community 186 - "mcp_query"
Cohesion: 0.22
Nodes (4): _mcp_call(), mcp_query(), TestMcpQueryOrdering, TestMcpPagination

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

### Community 203 - "ResolvedShowroom"
Cohesion: 0.09
Nodes (18): 1. Storage, 2. Source resolution, 3. Scan pipeline branch, 4. Candidate selection and stale check, 5. API, 6. Frontend, 7. Coverage math, Design (+10 more)

### Community 213 - "OsspaSyncError"
Cohesion: 0.33
Nodes (3): fetch_palist_csv(), OsspaSyncError, _boom()

### Community 214 - "build_infrastructure_embedding_text"
Cohesion: 0.47
Nodes (3): build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

### Community 216 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1461 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **75 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Advisor v2 — Content-Type Drivers` connect `Advisor v2 — Content-Type Drivers` to `workers/base.py`?**
  _High betweenness centrality (0.167) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `Database` (e.g. with `lifespan()` and `build_evidence_pack()`) actually correct?**
  _`Database` has 25 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.09659090909090909 - nodes in this community are weakly interconnected._
- **Why does `Summary` connect `Advisor v2 — Content-Type Drivers` to `BrowsePage.tsx`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.022106754841757205 - nodes in this community are weakly interconnected._