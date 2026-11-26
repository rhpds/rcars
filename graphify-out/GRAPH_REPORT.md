# Graph Report - feat-rhdpcd-2297-content-only-prompt  (2026-11-26)

## Corpus Check
- 306 files · ~337,761 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4568 nodes · 11546 edges · 232 communities (152 shown, 80 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1182 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `935c80d1`
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
- TestStepOrder
- test_description_analysis.py
- admin.py
- test_retirement_jira_events.py
- .create_schema
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_showroom_reuse.py
- catalog_identity.py
- Any
- handlers.py
- test_catalog_families.py
- _jira_event_messages
- orchestrator.py
- test_osspa_adoc.py
- react
- Settings
- item
- test_showroom_source.py
- Any
- seed
- App.tsx
- .upsert_babylon_catalog_item
- test_agv_access.py
- test_catalog_identity.py
- test_content_owner.py
- osspa_sync.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- test_test_content_exclusion.py
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
- showroom_source.py
- structlog
- HandsOnDriver
- test_analysis_identity.py
- Vocabulary
- test_osspa_analysis.py
- test_osspa_csv.py
- run_osspa_sync
- loader.py
- Retirement System
- re
- test_start_retirement_creates_ticket_off_event_loop
- test_catalog_osspa_routes.py
- SyncPage.tsx
- with
- test_overlap_chat_families.py
- test_field_source_sync.py
- reporting_sync.py
- build_analysis_prompt
- api.ts
- ECA Production Redesign Spec
- showroom_reuse_key
- json
- analysis.py
- Advisor v2 — Content-Type Drivers
- routes/auth.py
- TestValidation
- Path
- cli.py
- Description-Based Analysis for Items With No Showroom — Design
- test_auth_middleware.py
- test_drivers.py
- test_nonprod.py
- run_retirement_sweep
- _user_has_db_role
- _make_request
- ops.py
- advisor.py
- build_retirement_description
- mcp_query
- pytest
- router.py
- test_showroom_scan.py
- _build_windowed_metrics
- Showroom analysis isolation
- Scan Pipeline
- chat/models.py
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- analyze_showroom
- seed_chat_fixtures
- TestVocabularyEndpoints
- rcars-login.sh
- CLAUDE.md — Project Instructions
- AdocRead
- test_db.py
- RCARS OCP Deployment Playbook
- ArchitectureDriver
- Field Source Content
- Rec Card Duration and Best Fit Spec
- retirement_jira_events.py
- workers/base.py
- jira.py
- content_entities Table
- workload_scanner.py
- Deploy Docs GitHub Actions Workflow
- Change Detection
- test_reporting.py
- Overlap Detection Redesign
- family_members
- showroom_analysis_current
- _expand_query_terms
- CatalogReader
- generate_overlap_candidates
- retirement_cleanup.py
- _reset_token_cache
- _generate_key
- TestRetirementDashboardMetrics
- vocabulary.yaml
- pre_tasks
- test_retirement_history_schema.py
- item_reuse_key
- cli.py
- _clean
- .upsert_retirement_workflow
- test_llm_routing.py
- docker-entrypoint.sh
- RCARS — Agent Instructions
- test_catalog_labels.py
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
- deploy.yml
- LLM Overlap Assessment Design
- rcars
- rcars
- tasks
- Match Event Prompt Template
- extract_base_name
- advisor.py
- dedup_topics
- Python Requirements Entry Point
- RouterOutput
- build_embedding_text
- ignored_terms
- build_retirement_description
- _sync_nonprod_usage
- TestGetNonprodBaseNames
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- solutions
- ansible.builtin.assert
- cards_sharing_a_family
- Browse Page Redesign Spec
- TestTokenExchange
- TestSpoofedProxyHeaders
- analyzer.py
- test_orphan_cleanup.py
- ResolvedShowroom
- hashlib
- test_already_closed_issue_needs_no_transition
- TestCreateApiKey
- test_chat_similar_to.py
- request_with_references

## God Nodes (most connected - your core abstractions)
1. `Database` - 322 edges
2. `Settings` - 177 edges
3. `load_vocabulary()` - 66 edges
4. `seed()` - 50 edges
5. `Candidate` - 50 edges
6. `item()` - 50 edges
7. `scan_babylon_item()` - 48 edges
8. `create_app()` - 43 edges
9. `RouterOutput` - 41 edges
10. `add_item()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `What gets removed` --references--> `order_for_reuse()`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/analyzer.py
- `Anti-goals` --references--> `is_content_excluded()`  [INFERRED]
  docs/superpowers/specs/2026-11-17-description-analysis-design.md → src/api/rcars/services/showroom_source.py
- `Approaches considered` --references--> `is_content_excluded()`  [INFERRED]
  docs/superpowers/specs/2026-11-17-description-analysis-design.md → src/api/rcars/services/showroom_source.py
- `Root cause` --references--> `AnalysisSignature`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py
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

## Communities (232 total, 80 thin omitted)

### Community 0 - "_jira_request"
Cohesion: 0.10
Nodes (16): _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen() (+8 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (8): Database, _do(), main(), test_advisor_session(), test_content_path(), test_enrichment_tags(), test_execute_requires_scans_paused_confirmation(), test_script_rejects_selection_with_no_showroom_items()

### Community 2 - "react"
Cohesion: 0.14
Nodes (21): InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps (+13 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.16
Nodes (20): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis (+12 more)

### Community 4 - "common.yml"
Cohesion: 0.03
Nodes (58): admin_emails, api_cpu_limit, api_cpu_request, api_memory_limit, api_memory_request, api_replicas, app_name, app_port (+50 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (53): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, react-dom (+45 more)

### Community 6 - "test_advisor_families.py"
Cohesion: 0.16
Nodes (31): assert_invariant(), card_ids(), _clear_own_analysis(), link(), _not_eligible(), run(), _set_hash(), test_card_analysis_keeps_the_cleared_own_row_when_there_is_no_anchor() (+23 more)

### Community 8 - "test_description_analysis.py"
Cohesion: 0.05
Nodes (80): add_tag(), AnalysisSourceRequest, catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+72 more)

### Community 9 - "admin.py"
Cohesion: 0.06
Nodes (50): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), resolve_vocabulary_unknown(), sync_osspa(), SyncOsspaRequest, field_source_report(), health() (+42 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.06
Nodes (42): ensure_issue_event_comment(), deliver_pending_events(), _deliver_pending_events(), TestUnauthenticatedAccess, client(), comments(), event_time(), settings() (+34 more)

### Community 11 - ".create_schema"
Cohesion: 0.05
Nodes (32): db(), db(), seed_infrastructure(), db(), db(), db(), db(), db() (+24 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (37): Summary, getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline() (+29 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (25): overlap_assess(), assess_overlap(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+17 more)

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_showroom_reuse.py"
Cohesion: 0.15
Nodes (20): as_donor(), donor_row(), prime(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_description_analysis_is_never_a_showroom_donor(), test_different_ci_with_the_same_files_reuses_because_context_is_out_of_the_config(), test_different_content_path_in_one_repo_is_not_reused() (+12 more)

### Community 17 - "catalog_identity.py"
Cohesion: 0.07
Nodes (24): Catalog family, Catalog Identity, Deploy smoke check, Invariant, One owner, Rules for new code, Same content, Stage key (+16 more)

### Community 18 - "Any"
Cohesion: 0.06
Nodes (11): collect(), load(), extract_base_ci_refs(), extract_infrastructure_metadata(), is_agnosticd_v2(), parse_workload_fqcn(), _reference_context(), _reference_summary() (+3 more)

### Community 19 - "handlers.py"
Cohesion: 0.15
Nodes (20): get_item_workloads(), get_performance_scores(), _analysis(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+12 more)

### Community 20 - "test_catalog_families.py"
Cohesion: 0.18
Nodes (26): build_catalog_families(), four_level(), graph(), _item(), members(), node(), test_build_keeps_all_component_links_with_position_and_override_flag(), test_build_only_walks_published_items() (+18 more)

### Community 21 - "_jira_event_messages"
Cohesion: 0.10
Nodes (9): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_requires_admin(), test_edit_update_skips_cancelled_workflows(), test_edit_without_change_records_no_event() (+1 more)

### Community 22 - "orchestrator.py"
Cohesion: 0.08
Nodes (21): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), build_scaffold(), compose_answer(), _help_answer(), process_turn() (+13 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.07
Nodes (40): react, BlockErrorBoundary, Props, State, CATEGORY_LABELS, RecCardsBlock(), resolveBlockRenderer(), ChatChip (+32 more)

### Community 25 - "Settings"
Cohesion: 0.09
Nodes (24): list_role_assignments(), workload_scan(), fetch_litemaas_models(), _parse_csv(), Settings, _FakeModels, _litemaas_settings(), _patch_litemaas_client() (+16 more)

### Community 26 - "item"
Cohesion: 0.18
Nodes (23): item(), test_search_embeddings_without_a_limit_returns_every_item_that_passes_the_bar(), ref(), run_similar(), test_component_covered_by_two_virtual_cis_excludes_both(), test_dev_copy_is_excluded_even_when_dev_is_not_selected_or_is_selected(), test_empty_family_tables_exclude_the_item_and_its_stage_copies_only(), test_exclusion_leaves_no_empty_slot() (+15 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.18
Nodes (24): component_item_to_ci_name(), ComponentLink, content_owner(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous() (+16 more)

### Community 28 - "Any"
Cohesion: 0.11
Nodes (13): db(), _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch() (+5 more)

### Community 29 - "seed"
Cohesion: 0.06
Nodes (60): Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Pure stub (+52 more)

### Community 30 - "App.tsx"
Cohesion: 0.06
Nodes (51): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), API_DOCS_URL (+43 more)

### Community 31 - ".upsert_babylon_catalog_item"
Cohesion: 0.13
Nodes (18): test_retire_missing_babylon_ignores_other_sources(), _arch(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_maps_retirement_to_sibling_stages(), test_browse_mixed_content_types_return_both_sources(), test_browse_reports_retirement_workflow_status(), test_browse_returns_prod_architectures_with_stage_prod() (+10 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 33 - "test_catalog_identity.py"
Cohesion: 0.24
Nodes (24): collapse(), hit(), ids(), row(), test_dev_and_event_only_keep_the_event_copy(), test_different_stage_keys_with_equal_hash_never_merge(), test_field_asset_no_virtual_ci_eligible_member_shows(), test_field_asset_one_component_two_eligible_virtual_cis_gives_two_cards() (+16 more)

### Community 34 - "test_content_owner.py"
Cohesion: 0.14
Nodes (31): analyze_single(), rescan_all(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner() (+23 more)

### Community 35 - "osspa_sync.py"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.23
Nodes (10): Controlled Vocabulary, Difficulty Levels Taxonomy, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy, Learning Objectives Extraction (Stated + Inferred), Module-Level Analysis Output (+2 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.12
Nodes (7): get_vocabulary(), load_vocabulary(), _noise_variants(), snap_term(), _normalize_products(), TestLoadPackagedDefault, TestMatchLadder

### Community 39 - "test_test_content_exclusion.py"
Cohesion: 0.11
Nodes (21): extract_showroom_url(), _source_node(), ContentDeclaration, resolve_showroom_source(), unresolved(), walk(), SourceNode, test_legacy_url_extractor_does_not_pick_first_ambiguous_override() (+13 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.20
Nodes (18): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+10 more)

### Community 42 - "pipeline.py"
Cohesion: 0.09
Nodes (19): 2. Orchestrator and Pipeline, What Gets Deleted, _run_low(), registered_content_types(), QueryState, extract_urls(), run_category(), emit() (+11 more)

### Community 43 - "Candidate"
Cohesion: 0.11
Nodes (13): _apply_component_inheritance(), _collect_bases(), _call_rationale_single(), _format_single_candidate(), _run_catalog_second_pass(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports() (+5 more)

### Community 44 - "analyzer.py"
Cohesion: 0.11
Nodes (22): check_showroom_stale(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content(), test_content_path_antora_start_path_resolves_pages_and_nav(), test_content_path_containment() (+14 more)

### Community 45 - "test_showroom_rebuild.py"
Cohesion: 0.24
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

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

### Community 50 - "showroom_source.py"
Cohesion: 0.07
Nodes (17): classify_scan_error(), regenerate_embeddings(), CatalogFamilies, _content_fields(), _resolve_template_var(), _collapse_families(), _embedding_owner_id(), _is_excluded() (+9 more)

### Community 51 - "structlog"
Cohesion: 0.10
Nodes (16): RequestLoggingMiddleware, _add_component(), get_logger(), _reorder_keys(), setup_logging(), test_logger_outputs_json(), test_logger_with_job_id(), _clean() (+8 more)

### Community 52 - "HandsOnDriver"
Cohesion: 0.14
Nodes (9): HandsOnDriver, Candidate, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming(), test_hands_on_serialize_with_performance(), test_hands_on_triage_guidance() (+1 more)

### Community 53 - "test_analysis_identity.py"
Cohesion: 0.10
Nodes (18): compute_content_hash(), donor_matches_content(), AnalysisSignature, signatures_match(), config(), donor_row(), test_config_follows_content_type_when_vocabulary_mode_differs(), test_config_follows_prompt_template_and_vocabulary() (+10 more)

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

### Community 60 - "re"
Cohesion: 0.15
Nodes (7): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), _strip_html(), _validate_url()

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.08
Nodes (10): client(), db(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience() (+2 more)

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "with"
Cohesion: 0.07
Nodes (31): runs-on, steps, environment, needs, runs-on, steps, name, url (+23 more)

### Community 65 - "test_overlap_chat_families.py"
Cohesion: 0.08
Nodes (42): generate_overlap_candidates(), lift_to_covering(), pattern_check(), resolve_item(), test_pattern_check_url_and_lb(), test_generates_candidates_above_threshold(), test_idempotent_upsert(), test_overlap_candidates_exclude_non_babylon_sources() (+34 more)

### Community 66 - "test_field_source_sync.py"
Cohesion: 0.10
Nodes (16): test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at(), FakeSettings (+8 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.15
Nodes (10): _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs() (+2 more)

### Community 68 - "build_analysis_prompt"
Cohesion: 0.12
Nodes (7): Open items for the builder, canonical_content(), build_analysis_prompt(), build_description_prompt(), truncate_content(), test_prompt_carries_only_content_and_entity_content_type(), TestPromptInjection

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "showroom_reuse_key"
Cohesion: 0.18
Nodes (10): pre_clone_key(), showroom_reuse_key(), cid(), commit_of(), test_concurrent_sibling_scans_make_one_llm_call(), overlapping(), test_reuse_key_differs_by_commit_and_content_path(), test_reuse_key_ignores_ref_name_ci_and_display_name() (+2 more)

### Community 73 - "json"
Cohesion: 0.18
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 74 - "analysis.py"
Cohesion: 0.07
Nodes (58): generate_vocabulary(), get_job(), get_vocabulary_unknowns(), list_jobs(), llm_provider_status(), query_history(), query_session_detail(), reporting_status() (+50 more)

### Community 75 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.09
Nodes (22): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers, Approach Decision (+14 more)

### Community 76 - "routes/auth.py"
Cohesion: 0.17
Nodes (15): invalidate_api_key_cache(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token(), ApiKeyInfo (+7 more)

### Community 77 - "TestValidation"
Cohesion: 0.15
Nodes (5): clear_vocabulary_cache(), TestPathOverride, TestSquashKey, TestValidation, write_vocab()

### Community 78 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 79 - "cli.py"
Cohesion: 0.07
Nodes (28): command, check_card_families(), cli(), flag(), get_db(), infra_stats(), init_db(), note() (+20 more)

### Community 80 - "Description-Based Analysis for Items With No Showroom — Design"
Cohesion: 0.10
Nodes (16): 1. Storage, 2. Source resolution, 5. API, 6. Frontend, 7. Coverage math, Anti-goals, Approaches considered, Constraints (+8 more)

### Community 81 - "test_auth_middleware.py"
Cohesion: 0.14
Nodes (9): _fetch_group_members(), _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response(), TestGroupLookup (+1 more)

### Community 82 - "test_drivers.py"
Cohesion: 0.08
Nodes (18): ContentTypeDriver, _extract_duration_target(), get_driver(), get_drivers_for_types(), _init_drivers(), _register(), format_triage_candidates(), test_candidate_universal_fields() (+10 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.07
Nodes (13): _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), _build_nonprod_provisions_sql(), TestListNonprodItems, TestNonprodIgnore, TestNonprodProvisionsSql, TestNonprodRouteExists (+5 more)

### Community 84 - "run_retirement_sweep"
Cohesion: 0.07
Nodes (39): run_retirement_sweep(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), close(), test_cancel_stops_removal_before_creating_revert(), test_cancellation_does_not_mark_concurrently_retired_item() (+31 more)

### Community 85 - "_user_has_db_role"
Cohesion: 0.25
Nodes (3): _get_cached_role_assignments(), _user_has_db_role(), TestDbRoleCheck

### Community 86 - "_make_request"
Cohesion: 0.11
Nodes (10): get_current_user(), _parse_sa_allowlist(), _make_request(), TestApiKeyAuth, TestApiKeyRoleCeiling, TestGetCurrentUser, TestParseSaAllowlist, TestProxySecretEnforcement (+2 more)

### Community 87 - "ops.py"
Cohesion: 0.04
Nodes (42): Rescan after a prompt change, log_catalog_families(), batch_assess_overlaps(), run_field_source_sync(), log_scan_reuse_summary(), analysis_generation(), scan_all_collections(), publish_progress() (+34 more)

### Community 88 - "advisor.py"
Cohesion: 0.11
Nodes (26): Key Patterns, _check_api_key_role_ceiling(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), require_performance_view(), _validate_api_key_cached() (+18 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.12
Nodes (15): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+7 more)

### Community 90 - "mcp_query"
Cohesion: 0.22
Nodes (4): _mcp_call(), mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 91 - "pytest"
Cohesion: 0.03
Nodes (38): create_app(), lifespan(), derive_status(), retirement_label(), client(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels() (+30 more)

### Community 92 - "router.py"
Cohesion: 0.08
Nodes (20): _call_litemaas_inner(), LLMResult, _prefix_overlap(), _strip_formatting(), _expand_vocab_aliases(), _extract_json(), _find_keyword_ties(), _resolve_item_by_name() (+12 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.10
Nodes (37): start_scan(), InvalidShowroomRef, order_for_reuse(), resolve_commits(), scan_babylon_item(), add_item(), test_analysis_card_and_embeddings_roll_back_together(), test_cli_scans_independent_stages_and_reuses_shared_content() (+29 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "chat/models.py"
Cohesion: 0.12
Nodes (21): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+13 more)

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "analyze_showroom"
Cohesion: 0.28
Nodes (5): 3. Scan pipeline branch, analyze_showroom(), _finish_retryably(), _own_analysis_current(), RetryableAnalysisError

### Community 101 - "seed_chat_fixtures"
Cohesion: 0.11
Nodes (26): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+18 more)

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "CLAUDE.md — Project Instructions"
Cohesion: 0.20
Nodes (16): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, LLM Provider Routing (LiteMaaS / Vertex AI), Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API (+8 more)

### Community 105 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 106 - "test_db.py"
Cohesion: 0.08
Nodes (22): _do(), test_filter_platform_none_or_value(), db(), db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures() (+14 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.18
Nodes (12): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+4 more)

### Community 108 - "ArchitectureDriver"
Cohesion: 0.20
Nodes (8): ArchitectureDriver, _primary_asset_type(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 109 - "Field Source Content"
Cohesion: 0.25
Nodes (7): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git()

### Community 111 - "retirement_jira_events.py"
Cohesion: 0.32
Nodes (3): build_jira_event(), event_timestamp(), observe_pr_events()

### Community 112 - "workers/base.py"
Cohesion: 0.15
Nodes (15): Frontend Progress Display, What Stays Unchanged, stream_job(), create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives() (+7 more)

### Community 113 - "jira.py"
Cohesion: 0.10
Nodes (14): _close_issue(), close_issue_done(), close_issue_wont_do(), _fetch_oauth_token(), _get_access_token(), get_issue_status(), _issue_is_closed(), jira_auth_configured() (+6 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - "workload_scanner.py"
Cohesion: 0.08
Nodes (14): call_llm(), ls_remote_sha(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), read_config_code(), read_role_code() (+6 more)

### Community 118 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 120 - "family_members"
Cohesion: 0.43
Nodes (5): declares_or_overrides_content(), family_members(), _keep(), walk(), FamilyMember

### Community 121 - "showroom_analysis_current"
Cohesion: 0.33
Nodes (3): _item_analysis_config(), showroom_analysis_current(), test_two_items_with_the_same_content_and_type_share_the_analysis_config()

### Community 122 - "_expand_query_terms"
Cohesion: 0.09
Nodes (7): _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 123 - "CatalogReader"
Cohesion: 0.33
Nodes (4): CatalogReader, test_refresh_catalog_graph_returns_nodes_and_refresh_catalog_is_unchanged(), test_explicit_child_stage_applies_to_nested_component_references(), test_explicit_stage_infrastructure_chain_without_showroom_is_not_failure()

### Community 124 - "generate_overlap_candidates"
Cohesion: 0.18
Nodes (6): get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats(), test_prune_stale_retired()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.10
Nodes (22): check_pr_statuses(), _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira(), _close_open_pr(), complete_retirement() (+14 more)

### Community 127 - "_generate_key"
Cohesion: 0.18
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 129 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 130 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 131 - "test_retirement_history_schema.py"
Cohesion: 0.18
Nodes (11): _columns(), _index_keys(), _indexes(), _primary_key(), _require_test_database(), _rows(), _scratch_schema_dsn(), test_current_row_index_keeps_history_rows_out_of_the_upsert() (+3 more)

### Community 132 - "item_reuse_key"
Cohesion: 0.33
Nodes (5): item_reuse_key(), reuse_lock_id(), test_item_without_a_resolvable_commit_takes_no_lock_and_still_scans(), test_pure_stub_and_description_items_take_no_lock(), test_scan_lock_is_taken_on_the_pre_clone_key_not_the_ref_name()

### Community 133 - "cli.py"
Cohesion: 0.13
Nodes (9): concurrency, cancel-in-progress, group, infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group() (+1 more)

### Community 134 - "_clean"
Cohesion: 0.60
Nodes (5): _clean(), _rows(), test_member_primary_key_allows_one_component_under_two_virtual_cis(), test_replace_catalog_families_replaces_all_rows_in_one_transaction(), test_replace_catalog_families_rolls_back_on_failure()

### Community 135 - ".upsert_retirement_workflow"
Cohesion: 0.09
Nodes (28): test_edit_rejected_for_retired_item(), test_edit_rejected_while_cancellation_pending(), test_edit_rejects_name_without_replacement_ci(), _current_id(), _insert_history_row(), _other_babylon_ids(), _seed_family(), _seed_item() (+20 more)

### Community 136 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - "test_catalog_labels.py"
Cohesion: 0.04
Nodes (31): Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+23 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.10
Nodes (31): Token Usage Tracking (5 Operation Types), CLI Admin Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, Evidence Pack, Infrastructure Intent, Overlap Intent (+23 more)

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

### Community 163 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 169 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 174 - "advisor.py"
Cohesion: 0.12
Nodes (6): _get_user_key(), get_recommendations(), RecommendationRequest, _run_medium(), RecommendationLowResponse, RecommendationMediumResponse

### Community 178 - "RouterOutput"
Cohesion: 0.25
Nodes (17): RouterOutput, Scope, _parse_catalog_url(), resolve_and_verify(), _result_turns(), _turn_chips(), test_scope_shapes(), test_lb_ref_resolves() (+9 more)

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 185 - "build_retirement_description"
Cohesion: 0.18
Nodes (6): Open Questions / Risks, References, _base_name_from_content_id(), build_retirement_adoc_notice(), build_retirement_description(), test_no_notes()

### Community 187 - "_sync_nonprod_usage"
Cohesion: 0.33
Nodes (3): _nonprod_metrics(), _sync_nonprod_usage(), TestSyncNonprodUsage

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

### Community 203 - "cards_sharing_a_family"
Cohesion: 0.43
Nodes (6): cards_sharing_a_family(), fam(), test_cards_sharing_a_family_flags_member_next_to_its_virtual_ci(), test_two_members_of_a_virtual_ci_that_is_not_a_card_are_allowed(), test_two_virtual_cis_over_one_shared_component_do_not_share_a_family(), test_unrelated_cards_share_nothing()

### Community 218 - "analyzer.py"
Cohesion: 0.07
Nodes (25): 4. Candidate selection and stale check, analysis_from_row(), build_infrastructure_embedding_text(), build_module_embedding_text(), clone_showroom(), commit_for_ref(), compute_embedding_fingerprint(), _description_analysis_config() (+17 more)

### Community 222 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 223 - "ResolvedShowroom"
Cohesion: 0.11
Nodes (7): ResolvedShowroom, MemoryArtifacts, scan(), run(), test_catalog_resolution_failure_invalidates_previous_vectors_without_scan(), test_failed_resolution_is_visible_without_borrowing_analysis(), TestAnalyzerNormalizesOnce

### Community 227 - "hashlib"
Cohesion: 0.15
Nodes (8): compute_analysis_config(), compute_description_analysis_config(), donor_matches_commit(), _donor_signature(), fingerprint(), _signature(), compute_analysis_input_hash(), test_commit_donor_needs_repo_commit_path_and_config()

### Community 242 - "test_already_closed_issue_needs_no_transition"
Cohesion: 0.40
Nodes (3): test_already_closed_issue_needs_no_transition(), test_required_closure_selects_resolution_and_verifies_result(), request()

### Community 247 - "test_chat_similar_to.py"
Cohesion: 0.24
Nodes (8): resolve(), test_ambiguous_reference_clarifies_and_excludes_nothing_until_picked(), test_every_way_of_naming_the_item_gives_the_same_reference(), test_handler_passes_no_reference_for_a_topic_search(), test_handler_passes_the_resolved_references_to_the_pipeline(), fake_run_query(), noop(), test_no_similar_to_means_no_reference_even_when_the_query_names_an_item()

### Community 249 - "request_with_references"
Cohesion: 0.50
Nodes (3): request_with_references(), test_request_text_describes_what_the_referenced_item_covers(), test_request_text_is_the_query_when_there_is_no_reference()

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1519 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **80 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Advisor v2 — Content-Type Drivers` connect `Advisor v2 — Content-Type Drivers` to `workers/base.py`, `BrowsePage.tsx`?**
  _High betweenness centrality (0.168) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `Database` (e.g. with `One owner` and `lifespan()`) actually correct?**
  _`Database` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_jira_request` be split into smaller, more focused modules?**
  _Cohesion score 0.10344827586206896 - nodes in this community are weakly interconnected._
- **Why does `Summary` connect `BrowsePage.tsx` to `Advisor v2 — Content-Type Drivers`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.024444444444444446 - nodes in this community are weakly interconnected._