# Graph Report - feat-rhdpcd-2331-retire-history-schema  (2026-11-26)

## Corpus Check
- 307 files · ~339,987 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4606 nodes · 11658 edges · 238 communities (142 shown, 96 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1199 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d7a91838`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _jira_request
- Database
- react
- Portfolio Architecture Ingest Design Spec
- common.yml
- devDependencies
- item
- TestStepOrder
- routes/catalog.py
- schemas.py
- test_retirement_jira_events.py
- .create_schema
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_showroom_reuse.py
- test_description_analysis.py
- services/catalog.py
- handlers.py
- test_catalog_families.py
- _jira_event_messages
- orchestrator.py
- test_osspa_adoc.py
- react
- Settings
- Request
- test_showroom_source.py
- Any
- seed
- App.tsx
- test_agv_access.py
- test_catalog_identity.py
- test_content_owner.py
- osspa_sync.py
- Controlled Vocabulary
- load_vocabulary
- Any
- test_test_content_exclusion.py
- compilerOptions
- test_jira_service.py
- structlog
- extract_catalog_item
- analyzer.py
- middleware/auth.py
- compute_sales_impact
- api.ts
- normalize_analysis
- dev-services.sh
- effective_analysis_source
- structlog
- Candidate
- test_analysis_identity.py
- settings.py
- test_osspa_analysis.py
- test_osspa_csv.py
- run_osspa_sync
- loader.py
- Retirement System
- router.py
- no_litemaas_fetch
- test_catalog_osspa_routes.py
- SyncPage.tsx
- with
- test_overlap_chat_families.py
- test_field_source_sync.py
- reporting_sync.py
- TestPromptInjection
- api.ts
- ECA Production Redesign Spec
- order_for_reuse
- json
- analysis.py
- Advisor v2 — Content-Type Drivers
- routes/auth.py
- ContentAnalysisPage.tsx
- Path
- cli.py
- showroom_source.py
- test_auth_middleware.py
- Content Owner Model for Virtual CIs — Design
- test_nonprod.py
- run_retirement_sweep
- _user_has_db_role
- _make_request
- ops.py
- advisor.py
- build_retirement_description
- mcp_query
- pytest
- test_workers.py
- test_showroom_scan.py
- _build_windowed_metrics
- Showroom analysis isolation
- Scan Pipeline
- chat/models.py
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- patch
- seed_chat_fixtures
- TestVocabularyEndpoints
- rcars-login.sh
- CLAUDE.md — Project Instructions
- AdocRead
- .create_job
- RCARS OCP Deployment Playbook
- Advisor v2 — Content-Type Drivers
- workers/base.py
- Rec Card Duration and Best Fit Spec
- hashlib
- workers/base.py
- jira.py
- content_entities Table
- workload_scanner.py
- Deploy Docs GitHub Actions Workflow
- Change Detection
- test_reporting.py
- Overlap Detection Redesign
- _expand_query_terms
- _FakeResponse
- _expand_query_terms
- scan_configs
- set_analysis_source
- retirement_cleanup.py
- _reset_token_cache
- _generate_key
- .test_ignored_term_creates_no_row
- vocabulary.yaml
- pre_tasks
- test_retirement_history_schema.py
- test_worker_job_context.py
- cli.py
- _parse_sa_allowlist
- .upsert_retirement_workflow
- test_llm_routing.py
- docker-entrypoint.sh
- RCARS — Agent Instructions
- .upsert_babylon_catalog_item
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
- _extrapolate_count
- Chat Router LLM
- deploy.yml
- LLM Overlap Assessment Design
- rcars
- rcars
- tasks
- test_retirement_mark_revived.py
- Match Event Prompt Template
- extract_base_name
- build_sandbox_summary
- health.py
- dedup_topics
- Python Requirements Entry Point
- build_infrastructure_embedding_text
- RequestLoggingMiddleware
- build_embedding_text
- _run_git_with_retry
- test_edit_rejected_for_retired_item
- ignored_terms
- build_retirement_description
- _sync_nonprod_usage
- TestGetNonprodBaseNames
- content_similarity Table
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- TestRevokeApiKey
- solutions
- ansible.builtin.assert
- TestRoleCeiling
- TestUnknownTermsSchema
- test_edit_rejects_name_without_replacement_ci
- Browse Page Redesign Spec
- TestTokenExchange
- TestSpoofedProxyHeaders
- analyzer.py
- test_orphan_cleanup.py
- ResolvedShowroom
- test_already_closed_issue_needs_no_transition

## God Nodes (most connected - your core abstractions)
1. `Database` - 328 edges
2. `Settings` - 177 edges
3. `load_vocabulary()` - 66 edges
4. `Candidate` - 50 edges
5. `item()` - 50 edges
6. `seed()` - 50 edges
7. `scan_babylon_item()` - 48 edges
8. `create_app()` - 43 edges
9. `RouterOutput` - 41 edges
10. `run_retirement_sweep()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `Root cause` --references--> `AnalysisSignature`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py
- `Catalog family` --references--> `build_catalog_families()`  [INFERRED]
  docs/architecture/catalog-identity.md → src/api/rcars/services/catalog.py
- `Advisor` --references--> `search()`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/recommender/vector_search.py
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Summary` --references--> `isArchitecture()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/frontend/src/pages/browse/helpers.ts

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

## Communities (238 total, 96 thin omitted)

### Community 0 - "_jira_request"
Cohesion: 0.16
Nodes (12): _jira_request(), _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), test_oauth_token_request_format() (+4 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (8): Database, _do(), main(), test_advisor_session(), test_content_path(), test_enrichment_tags(), test_database_explicit_test_schema_reset_includes_delivery_queue(), test_execute_requires_scans_paused_confirmation()

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

### Community 6 - "item"
Cohesion: 0.09
Nodes (63): family_exclusion_core(), request_with_references(), assert_invariant(), card_ids(), _clear_own_analysis(), item(), link(), _not_eligible() (+55 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.11
Nodes (30): add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item(), get_analysis() (+22 more)

### Community 9 - "schemas.py"
Cohesion: 0.06
Nodes (58): field_source_report(), AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse, CatalogStatsResponse (+50 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.07
Nodes (38): deliver_pending_events(), TestUnauthenticatedAccess, comments(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_malformed_page_does_not_prove_absence() (+30 more)

### Community 11 - ".create_schema"
Cohesion: 0.05
Nodes (33): db(), db(), seed_infrastructure(), db(), db(), db(), db(), db() (+25 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (24): assess_overlap(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector(), _seed_overlap_pair() (+16 more)

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_showroom_reuse.py"
Cohesion: 0.07
Nodes (30): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git(), as_donor() (+22 more)

### Community 17 - "test_description_analysis.py"
Cohesion: 0.14
Nodes (38): analyze_description(), add_description_item(), add_item(), analyzed_description_item(), mock_analysis(), persist_result(), refresh_item(), seed_artifacts() (+30 more)

### Community 18 - "services/catalog.py"
Cohesion: 0.07
Nodes (19): _apply_component_inheritance(), CatalogFamilies, CatalogReader, collect(), load(), _collect_bases(), _content_fields(), extract_base_ci_refs() (+11 more)

### Community 19 - "handlers.py"
Cohesion: 0.10
Nodes (30): get_item_workloads(), get_performance_scores(), _analysis(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+22 more)

### Community 20 - "test_catalog_families.py"
Cohesion: 0.12
Nodes (37): build_catalog_families(), declares_or_overrides_content(), family_members(), _keep(), walk(), FamilyMember, SourceNode, _clean() (+29 more)

### Community 21 - "_jira_event_messages"
Cohesion: 0.10
Nodes (9): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_requires_admin(), test_edit_update_skips_cancelled_workflows(), test_edit_without_change_records_no_event() (+1 more)

### Community 22 - "orchestrator.py"
Cohesion: 0.07
Nodes (30): _call_litemaas_inner(), LLMResult, get_session_context(), log_chat_turn(), next_turn_index(), build_scaffold(), compose_answer(), _strip_formatting() (+22 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.13
Nodes (23): buildUrl(), FALLBACK_FORMAT_LABELS, FORMAT_COLORS, RecCard(), RecCardProps, CollapsibleTier(), RecCardList(), RecCardListProps (+15 more)

### Community 25 - "Settings"
Cohesion: 0.07
Nodes (25): fetch_litemaas_models(), _parse_csv(), Settings, _FakeModels, _litemaas_settings(), _patch_litemaas_client(), test_admin_check(), test_call_llm_propagates_litemaas_error() (+17 more)

### Community 26 - "Request"
Cohesion: 0.10
Nodes (34): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+26 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.18
Nodes (25): component_item_to_ci_name(), ComponentLink, content_owner(), item_family_key(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage() (+17 more)

### Community 28 - "Any"
Cohesion: 0.10
Nodes (13): test_audience_filter_applies_across_content_types(), _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch() (+5 more)

### Community 29 - "seed"
Cohesion: 0.13
Nodes (36): add_stub(), link(), search(), test_a_stage_copy_is_never_swapped_in_when_it_was_not_a_hit(), test_ci_reference_to_a_stub_resolves_through_its_owner(), test_each_owner_promotes_to_its_own_stub(), test_independent_ids_keep_their_own_scores(), test_owner_hit_is_shown_as_its_only_stub() (+28 more)

### Community 30 - "App.tsx"
Cohesion: 0.07
Nodes (42): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), LlmProviderCard() (+34 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 33 - "test_catalog_identity.py"
Cohesion: 0.09
Nodes (47): Catalog family, Catalog Identity, Deploy smoke check, Invariant, One owner, Rules for new code, Same content, Stage key (+39 more)

### Community 34 - "test_content_owner.py"
Cohesion: 0.14
Nodes (30): rescan_all(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner(), test_browse_difficulty_filter_finds_a_stub_by_its_mirrored_card() (+22 more)

### Community 35 - "osspa_sync.py"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.23
Nodes (10): Controlled Vocabulary, Difficulty Levels Taxonomy, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy, Learning Objectives Extraction (Stated + Inferred), Module-Level Analysis Output (+2 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.07
Nodes (11): _build_expansion_map(), load_vocabulary(), snap_term(), render_vocabulary_block(), clear_vocabulary_cache(), TestLoadPackagedDefault, TestMatchLadder, TestPathOverride (+3 more)

### Community 38 - "Any"
Cohesion: 0.07
Nodes (3): test_list_catalog_items(), test_token_usage(), TestReviewBadgeUntouched

### Community 39 - "test_test_content_exclusion.py"
Cohesion: 0.12
Nodes (17): resolve_showroom_source(), unresolved(), walk(), legacy_test_item(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(), test_existing_test_vectors_never_enter_content_retrieval(), test_ignored_test_dependency_does_not_block_a_real_content_branch() (+9 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.20
Nodes (18): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+10 more)

### Community 42 - "structlog"
Cohesion: 0.05
Nodes (28): 2. Orchestrator and Pipeline, What Gets Deleted, get_recommendations(), RecommendationRequest, _run_low(), _run_medium(), call_llm(), enforce_card_invariant() (+20 more)

### Community 43 - "extract_catalog_item"
Cohesion: 0.09
Nodes (15): Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+7 more)

### Community 44 - "analyzer.py"
Cohesion: 0.10
Nodes (25): check_showroom_stale(), classify_scan_error(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content() (+17 more)

### Community 45 - "middleware/auth.py"
Cohesion: 0.19
Nodes (11): Key Patterns, _check_api_key_role_ceiling(), _get_cached_role_assignments(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), require_performance_view() (+3 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.12
Nodes (6): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), _recompute_windowed_scores(), TestComputePerformanceScore

### Community 47 - "api.ts"
Cohesion: 0.09
Nodes (54): CollapsibleFilterGroup(), CollapsibleFilterGroupProps, render(), LabelFilterGroup(), LabelFilterGroupProps, fmtTargetDate(), isInProgress(), isRecommended() (+46 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.19
Nodes (3): normalize_analysis(), _record_unknowns(), TestNormalizeAnalysis

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "effective_analysis_source"
Cohesion: 0.11
Nodes (17): 1. Storage, 2. Source resolution, 3. Scan pipeline branch, 4. Candidate selection and stale check, 5. API, 6. Frontend, 7. Coverage math, Constraints (+9 more)

### Community 51 - "structlog"
Cohesion: 0.20
Nodes (12): _add_component(), get_logger(), _reorder_keys(), setup_logging(), test_logger_outputs_json(), test_logger_with_job_id(), _lines(), test_bound_inside_job_and_cleared_after() (+4 more)

### Community 52 - "Candidate"
Cohesion: 0.05
Nodes (43): ArchitectureDriver, _primary_asset_type(), _extract_duration_target(), HandsOnDriver, get_driver(), get_drivers_for_types(), Candidate, _call_rationale_single() (+35 more)

### Community 53 - "test_analysis_identity.py"
Cohesion: 0.06
Nodes (25): compute_content_hash(), donor_matches_commit(), donor_matches_content(), _donor_signature(), _signature(), AnalysisSignature, signature_matches_source(), signatures_match() (+17 more)

### Community 54 - "settings.py"
Cohesion: 0.13
Nodes (9): WorkerContext, cleanup_orphaned_jobs(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url(), scan_startup(), shutdown(), _startup() (+1 more)

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
Cohesion: 0.07
Nodes (18): _entries_to_dicts(), generate_vocabulary_yaml(), _header_comment(), _as_tuple(), _build_lookups(), _parse_entries(), _resolve_path(), _validate() (+10 more)

### Community 59 - "Retirement System"
Cohesion: 0.08
Nodes (26): AgV Access Layer, Architecture, Authentication and Scope, Automatic Removal Eligibility, Cancellation and Recovery, Catalog Soft-Delete, Checking Merges, Code Organization (+18 more)

### Community 60 - "router.py"
Cohesion: 0.06
Nodes (20): _prefix_overlap(), _expand_vocab_aliases(), _find_keyword_ties(), _resolve_item_by_name(), _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages() (+12 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.15
Nodes (8): client(), _second_architecture(), settings(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "with"
Cohesion: 0.06
Nodes (33): runs-on, steps, concurrency, cancel-in-progress, environment, needs, runs-on, steps (+25 more)

### Community 65 - "test_overlap_chat_families.py"
Cohesion: 0.05
Nodes (53): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), exclusion_set_for(), lift_to_covering(), _parse_catalog_url(), pattern_check() (+45 more)

### Community 66 - "test_field_source_sync.py"
Cohesion: 0.09
Nodes (17): run_field_source_sync(), test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at() (+9 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.16
Nodes (10): _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs() (+2 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "order_for_reuse"
Cohesion: 0.12
Nodes (10): commit_for_ref(), InvalidShowroomRef, ls_remote_refs(), order_for_reuse(), resolve_commits(), resolve(), test_order_for_reuse_groups_stages_with_other_ref_names_and_other_cis(), test_order_for_reuse_puts_one_prod_preferred_leader_per_group_first() (+2 more)

### Community 73 - "json"
Cohesion: 0.10
Nodes (19): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials(), build_product_entry() (+11 more)

### Community 74 - "analysis.py"
Cohesion: 0.11
Nodes (31): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_pr_statuses(), check_stale(), edit_retirement() (+23 more)

### Community 75 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.15
Nodes (13): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Candidate Dataclass, `content_entities` (shared table — all types) (+5 more)

### Community 76 - "routes/auth.py"
Cohesion: 0.19
Nodes (15): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+7 more)

### Community 77 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 78 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 79 - "cli.py"
Cohesion: 0.06
Nodes (30): command, check_card_families(), cli(), flag(), get_db(), infra_stats(), init_db(), note() (+22 more)

### Community 80 - "showroom_source.py"
Cohesion: 0.12
Nodes (11): Anti-goals, Approaches considered, Deployment, Description-Based Analysis for Items With No Showroom — Design, Goals, Intent, Non-goals, Open items for the builder (+3 more)

### Community 81 - "test_auth_middleware.py"
Cohesion: 0.18
Nodes (6): _fetch_group_members(), _user_in_groups(), _mock_async_client_get(), _mock_group_response(), TestApiKeyRoleCeiling, TestGroupLookup

### Community 82 - "Content Owner Model for Virtual CIs — Design"
Cohesion: 0.14
Nodes (13): Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Pure stub (+5 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.07
Nodes (12): _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema, TestNonprodWindows (+4 more)

### Community 84 - "run_retirement_sweep"
Cohesion: 0.07
Nodes (48): run_retirement_sweep(), run_retirement_sweep_job(), _approved_unstarted(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_cannot_delete_tracking_during_manual_pr_creation(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure() (+40 more)

### Community 86 - "_make_request"
Cohesion: 0.21
Nodes (5): get_current_user(), _make_request(), TestApiKeyAuth, TestGetCurrentUser, TestProxySecretEnforcement

### Community 87 - "ops.py"
Cohesion: 0.10
Nodes (18): log_catalog_families(), batch_assess_overlaps(), log_scan_reuse_summary(), scan_all_collections(), publish_progress(), run_chat_turn(), on_progress(), _progress_bridge() (+10 more)

### Community 88 - "advisor.py"
Cohesion: 0.13
Nodes (12): _get_user_key(), ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest (+4 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.12
Nodes (15): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+7 more)

### Community 90 - "mcp_query"
Cohesion: 0.22
Nodes (4): _mcp_call(), mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 91 - "pytest"
Cohesion: 0.03
Nodes (38): create_app(), lifespan(), retirement_label(), client(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists() (+30 more)

### Community 92 - "test_workers.py"
Cohesion: 0.21
Nodes (7): run_nightly_pipeline(), test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes()

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.09
Nodes (48): ls_remote_sha(), showroom_reuse_key(), item_reuse_key(), reuse_lock_id(), scan_babylon_item(), run_stale_check(), run_analysis(), cid() (+40 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "chat/models.py"
Cohesion: 0.09
Nodes (40): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+32 more)

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "patch"
Cohesion: 0.36
Nodes (4): _validate_sa_token(), _mock_async_client(), _mock_token_review_response(), TestValidateSaToken

### Community 101 - "seed_chat_fixtures"
Cohesion: 0.10
Nodes (21): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+13 more)

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

### Community 108 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.18
Nodes (10): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Goals, Non-Goals, Parallel Pipeline Instances (+2 more)

### Community 111 - "hashlib"
Cohesion: 0.15
Nodes (9): ensure_issue_event_comment(), jira_auth_configured(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response() (+1 more)

### Community 112 - "workers/base.py"
Cohesion: 0.14
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 113 - "jira.py"
Cohesion: 0.09
Nodes (12): _close_issue(), close_issue_done(), close_issue_wont_do(), _fetch_oauth_token(), _get_access_token(), get_issue_status(), _issue_is_closed(), _move_to_in_progress() (+4 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - "workload_scanner.py"
Cohesion: 0.09
Nodes (13): generate_embedding(), _extract_json(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products(), read_config_code() (+5 more)

### Community 121 - "_FakeResponse"
Cohesion: 0.22
Nodes (5): _FakeResponse, fake_urlopen(), fake_urlopen(), fake_urlopen(), _token_payload()

### Community 122 - "_expand_query_terms"
Cohesion: 0.13
Nodes (4): clear_vocabulary_cache(), TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 124 - "set_analysis_source"
Cohesion: 0.54
Nodes (7): AnalysisSourceRequest, set_analysis_source(), route_request(), test_analysis_source_endpoint_curator_ok(), test_analysis_source_endpoint_custom_without_text_400(), test_analysis_source_endpoint_empty_description_400(), test_catalog_detail_includes_analysis_source_fields()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.13
Nodes (16): _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable() (+8 more)

### Community 127 - "_generate_key"
Cohesion: 0.11
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 129 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 130 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 131 - "test_retirement_history_schema.py"
Cohesion: 0.19
Nodes (11): _columns(), _index_keys(), _indexes(), _primary_key(), _require_test_database(), _rows(), _scratch_schema_dsn(), test_current_row_index_keeps_history_rows_out_of_the_upsert() (+3 more)

### Community 133 - "cli.py"
Cohesion: 0.15
Nodes (7): group, infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 135 - ".upsert_retirement_workflow"
Cohesion: 0.12
Nodes (21): _current_id(), _insert_history_row(), _other_babylon_ids(), _seed_family(), _seed_item(), test_cancelling_the_new_workflow_keeps_history(), test_current_row_lists_skip_history_rows(), test_delete_workflow_keeps_history() (+13 more)

### Community 136 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - ".upsert_babylon_catalog_item"
Cohesion: 0.05
Nodes (49): _seed_label_count_items(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none(), test_label_counts_follow_other_filters() (+41 more)

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

### Community 162 - "Chat Router LLM"
Cohesion: 0.33
Nodes (6): Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, Infrastructure Embedding Search Design

### Community 163 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 169 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 170 - "test_retirement_mark_revived.py"
Cohesion: 0.17
Nodes (19): _clean(), _item_returns(), _other_babylon_ids(), _retire_everything(), _run(), test_ambiguous_family_is_refused(), test_apply_leaves_other_families_alone(), test_apply_marks_the_family_once() (+11 more)

### Community 178 - "build_infrastructure_embedding_text"
Cohesion: 0.60
Nodes (3): build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 185 - "build_retirement_description"
Cohesion: 0.18
Nodes (6): Open Questions / Risks, References, _base_name_from_content_id(), build_retirement_adoc_notice(), build_retirement_description(), test_wiki_markup_format()

### Community 187 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 189 - "content_similarity Table"
Cohesion: 0.67
Nodes (3): Evidence Pack, content_similarity Table, overlap_candidates Table

### Community 190 - "content_modes"
Cohesion: 0.40
Nodes (5): content_modes, architecture, demo, lab, sandbox

### Community 191 - ".get_unknown_terms"
Cohesion: 0.18
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

### Community 218 - "analyzer.py"
Cohesion: 0.07
Nodes (29): Rescan after a prompt change, canonical_content(), compute_analysis_config(), compute_description_analysis_config(), fingerprint(), pre_clone_key(), analysis_from_row(), analyze_showroom() (+21 more)

### Community 222 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 223 - "ResolvedShowroom"
Cohesion: 0.14
Nodes (12): effective_showroom_source(), ResolvedShowroom, snapshots(), test_dry_run_performs_no_writes(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data(), test_reset_rejects_non_babylon_or_missing_ids_atomically(), test_reset_rejects_running_or_queued_analysis_jobs() (+4 more)

### Community 242 - "test_already_closed_issue_needs_no_transition"
Cohesion: 0.40
Nodes (3): test_already_closed_issue_needs_no_transition(), test_required_closure_selects_resolution_and_verifies_result(), request()

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1531 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **96 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `test_retirement_history_schema.py`, `.upsert_retirement_workflow`, `test_retirement_jira_events.py`, `.create_schema`, `.upsert_babylon_catalog_item`, `test_overlap_assessment.py`, `handlers.py`, `_jira_event_messages`, `orchestrator.py`, `Any`, `.upsert_infrastructure`, `.backfill_revived_workflows`, `test_catalog_identity.py`, `Any`, `structlog`, `extract_catalog_item`, `extract_base_name`, `test_retirement_mark_revived.py`, `effective_analysis_source`, `test_analysis_identity.py`, `settings.py`, `test_osspa_analysis.py`, `run_osspa_sync`, `router.py`, `TestGetNonprodBaseNames`, `test_catalog_osspa_routes.py`, `.get_unknown_terms`, `test_overlap_chat_families.py`, `test_field_source_sync.py`, `cli.py`, `showroom_source.py`, `test_nonprod.py`, `run_retirement_sweep`, `ops.py`, `pytest`, `chat/models.py`, `seed_chat_fixtures`, `.create_job`, `workload_scanner.py`, `scan_configs`, `_generate_key`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `Database` (e.g. with `One owner` and `lifespan()`) actually correct?**
  _`Database` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.024267132595612504 - nodes in this community are weakly interconnected._
- **Why does `Advisor v2 — Content-Type Drivers` connect `Advisor v2 — Content-Type Drivers` to `workers/base.py`, `Advisor v2 — Content-Type Drivers`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Should `react` be split into smaller, more focused modules?**
  _Cohesion score 0.07197763801537387 - nodes in this community are weakly interconnected._