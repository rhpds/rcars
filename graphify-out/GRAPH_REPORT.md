# Graph Report - rhdpcd-2298-reference  (2026-11-24)

## Corpus Check
- 301 files · ~329,933 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4407 nodes · 11001 edges · 213 communities (142 shown, 71 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1052 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ba272d33`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _FakeResponse
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
- analyze_role
- .upsert_babylon_catalog_item
- test_catalog_families.py
- _jira_event_messages
- LLMResult
- test_osspa_adoc.py
- react
- Settings
- .close
- test_showroom_source.py
- test_osspa_db.py
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
- test_worker_job_context.py
- compilerOptions
- test_jira_service.py
- structlog
- Candidate
- analyzer.py
- json
- compute_sales_impact
- api.ts
- normalize_analysis
- dev-services.sh
- _expand_query_terms
- test_drivers.py
- pytest
- test_analysis_identity.py
- Vocabulary
- handlers.py
- test_osspa_csv.py
- run_osspa_sync
- loader.py
- Retirement System
- parse_analysis_response
- test_osspa_analysis.py
- test_catalog_osspa_routes.py
- SyncPage.tsx
- with
- ._artifact_connection
- test_field_source_sync.py
- reporting_sync.py
- analyzer.py
- admin.py
- api.ts
- ECA Production Redesign Spec
- Candidate
- json
- orchestrator.py
- _sync_nonprod_usage
- routes/auth.py
- TestValidation
- osspa_sync.py
- command
- Description-Based Analysis for Items With No Showroom — Design
- test_test_content_exclusion.py
- commit_for_ref
- test_nonprod.py
- test_retirement_pr_status.py
- Any
- middleware/auth.py
- Platform and Technical Decision Point filters — design
- ArchitectureDriver
- build_retirement_description
- Advisor v2 — Content-Type Drivers
- json
- test_auth_middleware.py
- test_showroom_scan.py
- _parse_sa_allowlist
- Showroom analysis isolation
- Scan Pipeline
- advisor.py
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- build_retirement_description
- seed_chat_fixtures
- test_vocabulary_admin.py
- rcars-login.sh
- CLAUDE.md — Project Instructions
- AdocRead
- .create_job
- RCARS OCP Deployment Playbook
- normalize_row
- get
- Rec Card Duration and Best Fit Spec
- mcp_query
- workers/base.py
- test_advisor_session
- content_entities Table
- OsspaSyncError
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Overlap Detection Redesign
- _FakeResponse
- TestBuildWindowedMetrics
- build_embedding_text
- ContentAnalysisPage.tsx
- test_orphan_cleanup.py
- retirement_cleanup.py
- _reset_token_cache
- vocabulary.yaml
- pre_tasks
- test_edit_update_skips_cancelled_workflows
- retirement_label
- _extrapolate_count
- test_status_visibility.py
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
- Python Dependency Manifest (requirements.lock)
- app.py
- deploy.yml
- LLM Overlap Assessment Design
- rcars
- rcars
- tasks
- Match Event Prompt Template
- extract_base_name
- test_auth_security.py
- test_vocabulary.py
- Python Requirements Entry Point
- RouterOutput
- content_similarity Table
- ignored_terms
- services/catalog.py
- TestGetNonprodBaseNames
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- solutions
- ansible.builtin.assert
- Browse Page Redesign Spec
- Content Owner Model for Virtual CIs — Design
- family_members
- _window_start

## God Nodes (most connected - your core abstractions)
1. `Database` - 310 edges
2. `Settings` - 179 edges
3. `load_vocabulary()` - 68 edges
4. `seed()` - 51 edges
5. `Candidate` - 50 edges
6. `item()` - 47 edges
7. `create_app()` - 43 edges
8. `scan_babylon_item()` - 42 edges
9. `run_retirement_sweep()` - 39 edges
10. `ResolvedShowroom` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Advisor` --references--> `search()`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/recommender/vector_search.py
- `Root cause` --references--> `AnalysisSignature`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Summary` --references--> `isArchitecture()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/frontend/src/pages/browse/helpers.ts
- `Anti-goals` --references--> `is_content_excluded()`  [INFERRED]
  docs/superpowers/specs/2026-11-17-description-analysis-design.md → src/api/rcars/services/showroom_source.py

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

## Communities (213 total, 71 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.16
Nodes (12): _jira_request(), _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), test_oauth_token_request_format() (+4 more)

### Community 1 - "Database"
Cohesion: 0.03
Nodes (9): Intent, Database, _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey (+1 more)

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
Nodes (62): enforce_card_invariant(), exclusion_set_for(), family_exclusion_core(), request_with_references(), db(), assert_invariant(), card_ids(), _clear_own_analysis() (+54 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.14
Nodes (13): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats(), test_idempotent_upsert() (+5 more)

### Community 8 - "test_description_analysis.py"
Cohesion: 0.06
Nodes (76): add_tag(), AnalysisSourceRequest, catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+68 more)

### Community 9 - "admin.py"
Cohesion: 0.06
Nodes (60): field_source_report(), AgvPrResponse, ApiKeyInfo, ApiKeyListResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload (+52 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.07
Nodes (36): deliver_pending_events(), client(), comments(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_malformed_page_does_not_prove_absence() (+28 more)

### Community 11 - "Chat Router LLM"
Cohesion: 0.33
Nodes (6): Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, Infrastructure Embedding Search Design

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.05
Nodes (36): _call_litemaas(), _call_litemaas_inner(), call_llm(), assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field() (+28 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (3): derive_status(), TestDeriveStatus, TestStepOrder

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_showroom_reuse.py"
Cohesion: 0.07
Nodes (28): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git(), as_donor() (+20 more)

### Community 17 - "ops.py"
Cohesion: 0.05
Nodes (31): run_field_source_sync(), build_sandbox_summary(), log_scan_reuse_summary(), scan_candidates(), publish_progress(), with_job_context(), WorkerContext, run_chat_turn() (+23 more)

### Community 18 - "analyze_role"
Cohesion: 0.07
Nodes (19): build_infrastructure_embedding_text(), ls_remote_sha(), regenerate_embeddings(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products() (+11 more)

### Community 19 - ".upsert_babylon_catalog_item"
Cohesion: 0.05
Nodes (30): _seed_label_count_items(), test_facets_platforms_and_tdps(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none() (+22 more)

### Community 20 - "test_catalog_families.py"
Cohesion: 0.16
Nodes (30): build_catalog_families(), _clean(), four_level(), graph(), _item(), members(), node(), _rows() (+22 more)

### Community 21 - "_jira_event_messages"
Cohesion: 0.08
Nodes (14): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_rejected_for_retired_item(), test_edit_rejected_while_cancellation_pending(), test_edit_rejects_name_without_replacement_ci() (+6 more)

### Community 22 - "LLMResult"
Cohesion: 0.17
Nodes (12): LLMResult, _extract_json(), route(), llm(), _fake(), llm_call(), test_call_error_falls_back(), test_hallucinated_intent_falls_back_to_recommend() (+4 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.13
Nodes (20): compute_content_hash(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git(), repo(), test_content_hash_covers_full_body_past_the_prompt_cap(), test_content_hash_covers_prompt_input_csv_fields() (+12 more)

### Community 24 - "react"
Cohesion: 0.13
Nodes (23): buildUrl(), FALLBACK_FORMAT_LABELS, FORMAT_COLORS, RecCard(), RecCardProps, CollapsibleTier(), RecCardList(), RecCardListProps (+15 more)

### Community 25 - "Settings"
Cohesion: 0.07
Nodes (29): list_role_assignments(), llm_provider_status(), workload_scan(), fetch_litemaas_models(), _parse_csv(), Settings, _get_embedding_client(), settings() (+21 more)

### Community 26 - ".close"
Cohesion: 0.07
Nodes (30): db(), seed_infrastructure(), db(), db(), db(), db(), db(), db() (+22 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.20
Nodes (23): ComponentLink, content_owner(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous(), test_curator_content_path_override_is_not_a_pure_stub() (+15 more)

### Community 28 - "test_osspa_db.py"
Cohesion: 0.12
Nodes (12): _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override() (+4 more)

### Community 29 - "seed"
Cohesion: 0.08
Nodes (50): main(), snapshots(), test_dry_run_performs_no_writes(), test_execute_requires_scans_paused_confirmation(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data(), test_reset_rejects_non_babylon_or_missing_ids_atomically(), test_reset_rejects_running_or_queued_analysis_jobs() (+42 more)

### Community 30 - "App.tsx"
Cohesion: 0.07
Nodes (42): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), LlmProviderCard() (+34 more)

### Community 31 - "analysis.py"
Cohesion: 0.10
Nodes (37): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_pr_statuses(), check_stale(), edit_retirement() (+29 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 33 - "test_advisor_families.py"
Cohesion: 0.10
Nodes (40): _best(), cards_sharing_a_family(), collapse_to_cards(), CollapseStats, family_violations(), merge_stage_copies(), cid(), collapse() (+32 more)

### Community 34 - "test_content_owner.py"
Cohesion: 0.16
Nodes (28): reconcile_pure_stubs(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner(), test_browse_difficulty_filter_finds_a_stub_by_its_mirrored_card(), test_browse_shows_the_owner_review_flags_on_a_stub(), test_delete_stub_artifacts_keeps_the_owner_existing_curation() (+20 more)

### Community 35 - "retirement_jira_events.py"
Cohesion: 0.14
Nodes (9): ensure_issue_event_comment(), jira_auth_configured(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response() (+1 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.23
Nodes (10): Controlled Vocabulary, Difficulty Levels Taxonomy, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy, Learning Objectives Extraction (Stated + Inferred), Module-Level Analysis Output (+2 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.12
Nodes (6): _expand_vocab_aliases(), load_vocabulary(), _noise_variants(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "test_worker_job_context.py"
Cohesion: 0.09
Nodes (19): _add_component(), get_logger(), _reorder_keys(), setup_logging(), recommend_startup(), scan_startup(), _startup(), test_logger_outputs_json() (+11 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.21
Nodes (17): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_creates_ticket_and_returns_key() (+9 more)

### Community 42 - "structlog"
Cohesion: 0.07
Nodes (21): 2. Orchestrator and Pipeline, What Gets Deleted, _run_low(), registered_content_types(), QueryState, extract_urls(), run_category(), serialize_candidates() (+13 more)

### Community 43 - "Candidate"
Cohesion: 0.13
Nodes (11): _call_rationale_single(), _format_single_candidate(), _run_catalog_second_pass(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published() (+3 more)

### Community 44 - "analyzer.py"
Cohesion: 0.09
Nodes (26): check_showroom_stale(), classify_scan_error(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content() (+18 more)

### Community 45 - "json"
Cohesion: 0.12
Nodes (13): build_router_prompt(), _fetch_oauth_token(), _get_access_token(), test_examples_validate_as_router_output(), test_followup_chips_are_pre_routed(), test_prompt_contains_every_intent_and_context(), cmd_logout(), _load_credentials() (+5 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.12
Nodes (6): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), _recompute_windowed_scores(), TestComputePerformanceScore

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

### Community 51 - "test_drivers.py"
Cohesion: 0.08
Nodes (17): ContentTypeDriver, get_driver(), get_drivers_for_types(), _init_drivers(), _register(), format_triage_candidates(), run_recommendation(), on_progress() (+9 more)

### Community 52 - "pytest"
Cohesion: 0.03
Nodes (27): create_app(), client(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists(), client(), test_sync_osspa_endpoint_enqueues_a_job() (+19 more)

### Community 53 - "test_analysis_identity.py"
Cohesion: 0.07
Nodes (25): compute_content_hash(), donor_matches_commit(), donor_matches_content(), _donor_signature(), pre_clone_key(), _signature(), AnalysisSignature, signatures_match() (+17 more)

### Community 54 - "Vocabulary"
Cohesion: 0.18
Nodes (4): generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "handlers.py"
Cohesion: 0.12
Nodes (28): get_item_workloads(), get_performance_scores(), generate_embedding(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+20 more)

### Community 56 - "test_osspa_csv.py"
Cohesion: 0.22
Nodes (18): asset_type_tokens(), content_id_for(), parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_content_id_format(), test_derive_osspa_status() (+10 more)

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
Cohesion: 0.14
Nodes (8): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), _strip_html(), _validate_url(), _extract_duration_target()

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
Cohesion: 0.06
Nodes (33): runs-on, steps, concurrency, cancel-in-progress, environment, needs, runs-on, steps (+25 more)

### Community 66 - "test_field_source_sync.py"
Cohesion: 0.08
Nodes (17): test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_field_source_route_registered(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at() (+9 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.13
Nodes (11): _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _mcp_call() (+3 more)

### Community 68 - "analyzer.py"
Cohesion: 0.06
Nodes (42): 3. Scan pipeline branch, canonical_content(), compute_analysis_config(), fingerprint(), analysis_from_row(), analyze_description(), analyze_showroom(), build_analysis_prompt() (+34 more)

### Community 69 - "admin.py"
Cohesion: 0.13
Nodes (24): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+16 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "Candidate"
Cohesion: 0.10
Nodes (11): HandsOnDriver, Candidate, _make_hands_on_candidate(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming() (+3 more)

### Community 73 - "json"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 74 - "orchestrator.py"
Cohesion: 0.10
Nodes (19): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), build_scaffold(), compose_answer(), _strip_formatting(), _help_answer() (+11 more)

### Community 75 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 76 - "routes/auth.py"
Cohesion: 0.20
Nodes (13): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+5 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "osspa_sync.py"
Cohesion: 0.17
Nodes (7): clone_examples_repo(), expand_includes(), _expand(), file_commit_sha(), get_head_sha(), is_tracked_at_head(), _run_git()

### Community 79 - "command"
Cohesion: 0.05
Nodes (34): command, group, check_card_families(), cli(), flag(), get_db(), infra_group(), infra_stats() (+26 more)

### Community 80 - "Description-Based Analysis for Items With No Showroom — Design"
Cohesion: 0.12
Nodes (16): 1. Storage, 2. Source resolution, 4. Candidate selection and stale check, 5. API, 6. Frontend, 7. Coverage math, Anti-goals, Approaches considered (+8 more)

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.16
Nodes (13): resolve_showroom_source(), unresolved(), walk(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(), test_existing_test_vectors_never_enter_content_retrieval(), test_ignored_test_dependency_does_not_block_a_real_content_branch(), test_manual_analysis_endpoint_rejects_test_item_before_job_creation() (+5 more)

### Community 82 - "commit_for_ref"
Cohesion: 0.18
Nodes (6): commit_for_ref(), _is_github_throttle(), ls_remote_refs(), resolve(), _resolve_ref_from_lookup(), _run_git_with_retry()

### Community 83 - "test_nonprod.py"
Cohesion: 0.08
Nodes (11): _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestNonprodWindows (+3 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.08
Nodes (43): run_retirement_sweep(), run_retirement_sweep_job(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert() (+35 more)

### Community 85 - "Any"
Cohesion: 0.06
Nodes (9): _prefix_overlap(), _find_keyword_ties(), resolve_item(), _resolve_ci_references(), test_list_catalog_items(), test_token_usage(), test_upsert_and_get_catalog_item(), test_upsert_updates_existing() (+1 more)

### Community 86 - "middleware/auth.py"
Cohesion: 0.09
Nodes (19): Key Patterns, _check_api_key_role_ceiling(), _get_cached_role_assignments(), get_current_user(), _log_auth_decision(), require_admin(), require_auth(), require_curator() (+11 more)

### Community 87 - "Platform and Technical Decision Point filters — design"
Cohesion: 0.11
Nodes (14): Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+6 more)

### Community 88 - "ArchitectureDriver"
Cohesion: 0.20
Nodes (8): ArchitectureDriver, _primary_asset_type(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 89 - "build_retirement_description"
Cohesion: 0.11
Nodes (17): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+9 more)

### Community 90 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.08
Nodes (23): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers, Approach Decision (+15 more)

### Community 91 - "json"
Cohesion: 0.10
Nodes (12): _close_issue(), close_issue_done(), close_issue_wont_do(), _issue_is_closed(), _move_to_in_progress(), _oauth_config(), test_already_closed_issue_needs_no_transition(), test_closure_requires_a_terminal_result() (+4 more)

### Community 92 - "test_auth_middleware.py"
Cohesion: 0.14
Nodes (9): _fetch_group_members(), _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response(), TestGroupLookup (+1 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.09
Nodes (43): start_scan(), InvalidShowroomRef, order_for_reuse(), scan_babylon_item(), run_stale_check(), run_analysis(), add_item(), commit_of() (+35 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "advisor.py"
Cohesion: 0.12
Nodes (13): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+5 more)

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "build_retirement_description"
Cohesion: 0.20
Nodes (5): Open Questions / Risks, _base_name_from_content_id(), build_retirement_description(), test_basic_description(), test_no_replacement()

### Community 101 - "seed_chat_fixtures"
Cohesion: 0.09
Nodes (28): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+20 more)

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

### Community 108 - "normalize_row"
Cohesion: 0.36
Nodes (4): _as_bool(), derive_osspa_status(), normalize_row(), _split_list()

### Community 109 - "get"
Cohesion: 0.33
Nodes (3): _extract_base_name_from_content_id(), retirement_dashboard(), TestRetirementDashboardMetrics

### Community 111 - "mcp_query"
Cohesion: 0.27
Nodes (3): mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 112 - "workers/base.py"
Cohesion: 0.14
Nodes (15): Frontend Progress Display, What Stays Unchanged, stream_job(), create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives() (+7 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - "OsspaSyncError"
Cohesion: 0.33
Nodes (3): fetch_palist_csv(), OsspaSyncError, _boom()

### Community 120 - "_FakeResponse"
Cohesion: 0.22
Nodes (5): _FakeResponse, fake_urlopen(), fake_urlopen(), fake_urlopen(), _token_payload()

### Community 123 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.11
Nodes (21): _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable() (+13 more)

### Community 129 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 130 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 135 - "test_status_visibility.py"
Cohesion: 0.09
Nodes (23): _do(), test_content_path(), test_retire_missing_babylon_ignores_other_sources(), _arch(), _seed_nonprod(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_maps_retirement_to_sibling_stages() (+15 more)

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - "services/catalog.py"
Cohesion: 0.11
Nodes (13): refresh(), CatalogReader, collect(), load(), extract_base_ci_refs(), extract_infrastructure_metadata(), is_agnosticd_v2(), parse_workload_fqcn() (+5 more)

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

### Community 160 - "Python Dependency Manifest (requirements.lock)"
Cohesion: 0.22
Nodes (9): Anthropic SDK Dependency (v0.120.0), arq Dependency (v0.28.0), Python Dependency Manifest (requirements.lock), FastAPI Dependency (v0.140.7), OpenAI SDK Dependency (v2.49.0), psycopg Dependency (v3.3.4), Pydantic Dependency (v2.13.4), Redis Client Dependency (v5.3.1) (+1 more)

### Community 161 - "app.py"
Cohesion: 0.11
Nodes (5): lifespan(), _get_user_key(), RequestLoggingMiddleware, health(), readiness()

### Community 163 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 169 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 173 - "test_auth_security.py"
Cohesion: 0.11
Nodes (7): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders, TestUnauthenticatedAccess

### Community 175 - "test_vocabulary.py"
Cohesion: 0.10
Nodes (5): dedup_topics(), clear_vocabulary_cache(), TestPromptInjection, TestSquashKey, TestTopicDedup

### Community 178 - "RouterOutput"
Cohesion: 0.22
Nodes (17): RouterOutput, Scope, _parse_catalog_url(), pattern_check(), resolve_and_verify(), _result_turns(), _turn_chips(), test_scope_shapes() (+9 more)

### Community 182 - "content_similarity Table"
Cohesion: 0.67
Nodes (3): Evidence Pack, content_similarity Table, overlap_candidates Table

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 185 - "services/catalog.py"
Cohesion: 0.12
Nodes (12): _apply_component_inheritance(), CatalogFamilies, _collect_bases(), component_item_to_ci_name(), _content_fields(), extract_showroom_url(), log_catalog_families(), _resolve_template_var() (+4 more)

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

### Community 218 - "Content Owner Model for Virtual CIs — Design"
Cohesion: 0.14
Nodes (13): Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Pure stub (+5 more)

### Community 227 - "family_members"
Cohesion: 0.43
Nodes (5): declares_or_overrides_content(), family_members(), _keep(), walk(), FamilyMember

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1470 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **71 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Advisor v2 — Content-Type Drivers` connect `Advisor v2 — Content-Type Drivers` to `workers/base.py`?**
  _High betweenness centrality (0.198) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `Database` (e.g. with `lifespan()` and `build_evidence_pack()`) actually correct?**
  _`Database` has 25 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.027183146449201494 - nodes in this community are weakly interconnected._
- **Why does `Summary` connect `Advisor v2 — Content-Type Drivers` to `BrowsePage.tsx`?**
  _High betweenness centrality (0.197) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Should `react` be split into smaller, more focused modules?**
  _Cohesion score 0.07197763801537387 - nodes in this community are weakly interconnected._