# Graph Report - feat-rhdpcd-2331-retire-history-schema  (2026-11-26)

## Corpus Check
- 307 files · ~337,980 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4575 nodes · 11574 edges · 244 communities (159 shown, 85 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1118 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `afd92b82`
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
- services/catalog.py
- test_description_analysis.py
- schemas.py
- test_retirement_jira_events.py
- Chat Router LLM
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_showroom_reuse.py
- catalog_identity.py
- services/catalog.py
- .upsert_babylon_catalog_item
- test_catalog_families.py
- test_retirement_edit.py
- chat_sessions.py
- test_osspa_adoc.py
- react
- Settings
- item
- test_showroom_source.py
- Any
- seed
- App.tsx
- analysis.py
- test_agv_access.py
- test_catalog_identity.py
- test_content_owner.py
- test_chat_live.py
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
- vector_search.py
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
- create_app
- test_catalog_osspa_routes.py
- SyncPage.tsx
- with
- test_overlap_chat_families.py
- test_field_source_sync.py
- reporting_sync.py
- TestPromptInjection
- api.ts
- ECA Production Redesign Spec
- test_showroom_recommendation_isolation.py
- json
- analysis.py
- Advisor v2 — Content-Type Drivers
- .create_job
- TestValidation
- osspa_sync.py
- cli.py
- Description-Based Analysis for Items With No Showroom — Design
- test_auth_middleware.py
- test_drivers.py
- test_nonprod.py
- run_retirement_sweep
- _user_has_db_role
- middleware/auth.py
- asyncio
- hashlib
- build_retirement_description
- MemoryArtifacts
- test_analysis_labels.py
- json
- test_showroom_scan.py
- showroom_source.py
- Showroom analysis isolation
- Scan Pipeline
- pytest
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- ResolvedShowroom
- seed_chat_fixtures
- test_vocabulary_admin.py
- rcars-login.sh
- CLAUDE.md — Project Instructions
- AdocRead
- .upsert_babylon_catalog_item
- RCARS OCP Deployment Playbook
- ArchitectureDriver
- ContentAnalysisPage.tsx
- Rec Card Duration and Best Fit Spec
- test_api_infrastructure.py
- workers/base.py
- jira.py
- content_entities Table
- workload_scanner.py
- Deploy Docs GitHub Actions Workflow
- Change Detection
- _extrapolate_count
- Overlap Detection Redesign
- _build_windowed_metrics
- parametrize
- _expand_query_terms
- Catalog Identity
- .create_schema
- workflow_lock_id
- _reset_token_cache
- _generate_key
- TestRetirementDashboardMetrics
- vocabulary.yaml
- pre_tasks
- test_retirement_history_schema.py
- Field Source Content
- main
- rate_limit.py
- .upsert_retirement_workflow
- test_llm_routing.py
- docker-entrypoint.sh
- RCARS — Agent Instructions
- extract_catalog_item
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
- client
- Python Dependency Manifest (requirements.lock)
- test_chat_handlers.py
- deploy.yml
- LLM Overlap Assessment Design
- rcars
- rcars
- tasks
- test_retirement_mark_revived.py
- Match Event Prompt Template
- extract_base_name
- _window_start
- advisor.py
- test_vocabulary.py
- Python Requirements Entry Point
- RouterOutput
- _resolve_ci_references
- build_embedding_text
- retirement_label
- ignored_terms
- _sync_nonprod_usage
- TestGetNonprodBaseNames
- ops.py
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- Content Owner Model for Virtual CIs — Design
- solutions
- ansible.builtin.assert
- readiness
- Browse Page Redesign Spec
- Candidate
- TestTokenExchange
- test_auth_security.py
- content_similarity Table
- analyzer.py
- test_orphan_cleanup.py
- _retirement_metrics
- TestNonprodSchema
- services/__init__.py
- test_auth_routes.py
- handlers.py
- request_with_references
- test_drivers.py

## God Nodes (most connected - your core abstractions)
1. `Database` - 326 edges
2. `Settings` - 177 edges
3. `load_vocabulary()` - 67 edges
4. `Candidate` - 50 edges
5. `item()` - 50 edges
6. `seed()` - 50 edges
7. `create_app()` - 43 edges
8. `scan_babylon_item()` - 42 edges
9. `RouterOutput` - 41 edges
10. `run_retirement_sweep()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `Root cause` --references--> `AnalysisSignature`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py
- `Catalog family` --references--> `build_catalog_families()`  [INFERRED]
  docs/architecture/catalog-identity.md → src/api/rcars/services/catalog.py
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Advisor` --references--> `search()`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/recommender/vector_search.py
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

## Communities (244 total, 85 thin omitted)

### Community 0 - "_jira_request"
Cohesion: 0.10
Nodes (16): _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen() (+8 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (5): reporting_db_show(), Database, _reference_summary(), test_advisor_session(), test_enrichment_tags()

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
Cohesion: 0.16
Nodes (32): assert_invariant(), card_ids(), _clear_own_analysis(), link(), _not_eligible(), run(), _set_hash(), test_card_analysis_keeps_the_cleared_own_row_when_there_is_no_anchor() (+24 more)

### Community 7 - "services/catalog.py"
Cohesion: 0.12
Nodes (10): _apply_component_inheritance(), CatalogFamilies, _collect_bases(), component_item_to_ci_name(), _content_fields(), extract_showroom_url(), _resolve_template_var(), _source_node() (+2 more)

### Community 8 - "test_description_analysis.py"
Cohesion: 0.05
Nodes (79): 4. Candidate selection and stale check, add_tag(), AnalysisSourceRequest, catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest (+71 more)

### Community 9 - "schemas.py"
Cohesion: 0.05
Nodes (71): invalidate_api_key_cache(), field_source_report(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+63 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.06
Nodes (40): ensure_issue_event_comment(), deliver_pending_events(), client(), comments(), db(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post() (+32 more)

### Community 11 - "Chat Router LLM"
Cohesion: 0.33
Nodes (6): Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, Infrastructure Embedding Search Design

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (25): overlap_assess(), assess_overlap(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+17 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (3): derive_status(), TestDeriveStatus, TestStepOrder

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_showroom_reuse.py"
Cohesion: 0.15
Nodes (20): as_donor(), donor_row(), prime(), test_changed_prompt_context_invalidates_unchanged_git_revision(), test_curator_url_or_path_override_is_target_scoped(), test_description_analysis_is_never_a_showroom_donor(), test_different_ci_with_the_same_files_reuses_only_once_context_is_out_of_the_config(), test_different_content_path_in_one_repo_is_not_reused() (+12 more)

### Community 17 - "catalog_identity.py"
Cohesion: 0.10
Nodes (19): One owner, _best(), cards_sharing_a_family(), collapse_to_cards(), CollapseStats, enforce_card_invariant(), exclusion_set_for(), family_violations() (+11 more)

### Community 18 - "services/catalog.py"
Cohesion: 0.09
Nodes (11): CatalogReader, collect(), load(), extract_base_ci_refs(), extract_infrastructure_metadata(), is_agnosticd_v2(), parse_workload_fqcn(), test_refresh_catalog_graph_returns_nodes_and_refresh_catalog_is_unchanged() (+3 more)

### Community 19 - ".upsert_babylon_catalog_item"
Cohesion: 0.08
Nodes (22): _do(), test_content_path(), test_list_catalog_items(), test_retire_missing_babylon_ignores_other_sources(), test_schema_backfills_status_from_stage(), _arch(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures() (+14 more)

### Community 20 - "test_catalog_families.py"
Cohesion: 0.15
Nodes (31): build_catalog_families(), _clean(), four_level(), graph(), _item(), members(), node(), _rows() (+23 more)

### Community 21 - "test_retirement_edit.py"
Cohesion: 0.06
Nodes (16): db(), _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_rejected_for_retired_item(), test_edit_rejected_while_cancellation_pending() (+8 more)

### Community 22 - "chat_sessions.py"
Cohesion: 0.14
Nodes (12): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), _help_answer(), process_turn(), _scope_echo(), test_chat_append_checks_ownership() (+4 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.13
Nodes (23): buildUrl(), FALLBACK_FORMAT_LABELS, FORMAT_COLORS, RecCard(), RecCardProps, CollapsibleTier(), RecCardList(), RecCardListProps (+15 more)

### Community 25 - "Settings"
Cohesion: 0.10
Nodes (22): list_role_assignments(), _parse_csv(), Settings, _FakeModels, _litemaas_settings(), _patch_litemaas_client(), test_admin_check(), test_call_llm_propagates_litemaas_error() (+14 more)

### Community 26 - "item"
Cohesion: 0.14
Nodes (27): family_exclusion_core(), item(), test_search_embeddings_without_a_limit_returns_every_item_that_passes_the_bar(), ref(), run_similar(), test_component_covered_by_two_virtual_cis_excludes_both(), test_core_of_a_member_is_itself_and_every_covering_virtual_ci_not_its_siblings(), test_core_of_a_virtual_ci_is_itself_and_its_members() (+19 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.20
Nodes (24): ComponentLink, content_owner(), item_family_key(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous() (+16 more)

### Community 28 - "Any"
Cohesion: 0.12
Nodes (11): _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override() (+3 more)

### Community 29 - "seed"
Cohesion: 0.21
Nodes (20): test_reset_rejects_running_or_queued_analysis_jobs(), by_commit(), by_content(), CONFIG_FOR_EXAMPLE(), seed(), test_another_ci_is_a_donor_when_it_has_the_same_analysis_config(), test_description_analysis_is_never_a_showroom_donor(), test_independent_items_and_virtual_stages_are_not_deduplicated() (+12 more)

### Community 30 - "App.tsx"
Cohesion: 0.07
Nodes (42): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), LlmProviderCard() (+34 more)

### Community 31 - "analysis.py"
Cohesion: 0.11
Nodes (34): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+26 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 33 - "test_catalog_identity.py"
Cohesion: 0.25
Nodes (24): cid(), collapse(), hit(), ids(), row(), test_dev_and_event_only_keep_the_event_copy(), test_different_stage_keys_with_equal_hash_never_merge(), test_field_asset_no_virtual_ci_eligible_member_shows() (+16 more)

### Community 34 - "test_content_owner.py"
Cohesion: 0.15
Nodes (30): analyze_single(), rescan_all(), reconcile_pure_stubs(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner(), test_browse_difficulty_filter_finds_a_stub_by_its_mirrored_card() (+22 more)

### Community 35 - "test_chat_live.py"
Cohesion: 0.31
Nodes (4): _noop(), _settings(), test_live_item_facts_turn(), test_live_out_of_scope()

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.23
Nodes (10): Controlled Vocabulary, Difficulty Levels Taxonomy, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy, Verticals Taxonomy, Learning Objectives Extraction (Stated + Inferred), Module-Level Analysis Output (+2 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.13
Nodes (5): load_vocabulary(), _noise_variants(), snap_term(), TestLoadPackagedDefault, TestMatchLadder

### Community 38 - "render_vocabulary_block"
Cohesion: 0.20
Nodes (3): _mode_for(), render_vocabulary_block(), TestRenderVocabularyBlock

### Community 39 - "test_test_content_exclusion.py"
Cohesion: 0.14
Nodes (14): resolve_showroom_source(), unresolved(), walk(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(), test_existing_test_vectors_never_enter_content_retrieval(), test_ignored_test_dependency_does_not_block_a_real_content_branch(), test_manual_analysis_endpoint_rejects_test_item_before_job_creation() (+6 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.18
Nodes (19): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+11 more)

### Community 42 - "pipeline.py"
Cohesion: 0.06
Nodes (24): 2. Orchestrator and Pipeline, What Gets Deleted, _run_low(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), registered_content_types(), QueryState (+16 more)

### Community 43 - "Candidate"
Cohesion: 0.11
Nodes (14): 1. Content-Type Drivers, Adding a New Content Type, Driver Interface, What Moves Into Drivers, _format_single_candidate(), _run_catalog_second_pass(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture() (+6 more)

### Community 44 - "analyzer.py"
Cohesion: 0.11
Nodes (24): check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content(), test_content_path_antora_start_path_resolves_pages_and_nav() (+16 more)

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

### Community 50 - "vector_search.py"
Cohesion: 0.10
Nodes (10): _collapse_families(), _embedding_owner_id(), _is_excluded(), _neighbor_rows(), _owner_scope_ids(), _reference_context(), search(), _strip_embedding_filler() (+2 more)

### Community 51 - "structlog"
Cohesion: 0.13
Nodes (14): _add_component(), get_logger(), _reorder_keys(), setup_logging(), test_logger_outputs_json(), test_logger_with_job_id(), _lines(), test_bound_inside_job_and_cleared_after() (+6 more)

### Community 52 - "HandsOnDriver"
Cohesion: 0.18
Nodes (7): HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming(), test_hands_on_serialize_with_performance(), test_hands_on_triage_guidance()

### Community 53 - "test_analysis_identity.py"
Cohesion: 0.13
Nodes (16): AnalysisSignature, signatures_match(), config(), donor_row(), test_commit_donor_needs_repo_commit_path_and_config(), test_config_follows_content_type_when_vocabulary_mode_differs(), test_config_follows_prompt_template_and_vocabulary(), test_config_is_stable_and_follows_model_and_policy() (+8 more)

### Community 55 - "test_osspa_analysis.py"
Cohesion: 0.15
Nodes (12): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), db(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms() (+4 more)

### Community 56 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (19): asset_type_tokens(), fetch_palist_csv(), OsspaSyncError, parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status() (+11 more)

### Community 57 - "run_osspa_sync"
Cohesion: 0.23
Nodes (19): run_osspa_sync(), _csv(), db(), fake_analyze(), settings(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring() (+11 more)

### Community 58 - "loader.py"
Cohesion: 0.11
Nodes (13): _entries_to_dicts(), _header_comment(), _as_tuple(), _build_lookups(), _parse_entries(), _resolve_path(), _validate(), squash_key() (+5 more)

### Community 59 - "Retirement System"
Cohesion: 0.08
Nodes (26): AgV Access Layer, Architecture, Authentication and Scope, Automatic Removal Eligibility, Cancellation and Recovery, Catalog Soft-Delete, Checking Merges, Code Organization (+18 more)

### Community 60 - "re"
Cohesion: 0.10
Nodes (11): _prefix_overlap(), _expand_vocab_aliases(), _find_keyword_ties(), _resolve_item_by_name(), _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages() (+3 more)

### Community 61 - "create_app"
Cohesion: 0.05
Nodes (19): create_app(), lifespan(), RequestLoggingMiddleware, client(), client(), test_auth_me_unauthenticated(), client(), client() (+11 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.12
Nodes (10): client(), db(), _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_curator_actions_work_on_a_pa_identifier(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience() (+2 more)

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "with"
Cohesion: 0.07
Nodes (31): runs-on, steps, environment, needs, runs-on, steps, name, url (+23 more)

### Community 65 - "test_overlap_chat_families.py"
Cohesion: 0.11
Nodes (34): generate_overlap_candidates(), lift_to_covering(), resolve_item(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats(), test_idempotent_upsert(), test_overlap_candidates_exclude_non_babylon_sources() (+26 more)

### Community 66 - "test_field_source_sync.py"
Cohesion: 0.09
Nodes (16): test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at(), FakeSettings (+8 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.16
Nodes (10): _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs() (+2 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "test_showroom_recommendation_isolation.py"
Cohesion: 0.25
Nodes (17): add_stub(), link(), search(), test_a_stage_copy_is_never_swapped_in_when_it_was_not_a_hit(), test_each_owner_promotes_to_its_own_stub(), test_independent_ids_keep_their_own_scores(), test_owner_hit_is_shown_as_its_only_stub(), test_owner_with_two_stubs_shows_each_stub_as_its_own_card_never_the_owner() (+9 more)

### Community 73 - "json"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 74 - "analysis.py"
Cohesion: 0.13
Nodes (26): approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), edit_retirement(), EditRetirementRequest, get_workflow(), ignore_item() (+18 more)

### Community 75 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.18
Nodes (10): Advisor v2 — Content-Type Drivers, Approach Decision, Architecture, Branch Strategy, Entry Points, Goals, Non-Goals, Parallel Pipeline Instances (+2 more)

### Community 76 - ".create_job"
Cohesion: 0.22
Nodes (6): _do(), test_job_failure(), test_job_lifecycle(), test_list_jobs(), test_list_jobs_shows_running_before_newer_queued(), test_queued_job_keeps_progress_json()

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (3): TestPathOverride, TestValidation, write_vocab()

### Community 78 - "osspa_sync.py"
Cohesion: 0.13
Nodes (10): _as_bool(), clone_examples_repo(), content_id_for(), derive_osspa_status(), file_commit_sha(), get_head_sha(), normalize_row(), _run_git() (+2 more)

### Community 79 - "cli.py"
Cohesion: 0.05
Nodes (37): command, concurrency, cancel-in-progress, group, check_card_families(), cli(), flag(), get_db() (+29 more)

### Community 80 - "Description-Based Analysis for Items With No Showroom — Design"
Cohesion: 0.09
Nodes (18): 1. Storage, 2. Source resolution, 5. API, 6. Frontend, 7. Coverage math, Anti-goals, Approaches considered, Constraints (+10 more)

### Community 81 - "test_auth_middleware.py"
Cohesion: 0.14
Nodes (9): _fetch_group_members(), _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response(), TestGroupLookup (+1 more)

### Community 82 - "test_drivers.py"
Cohesion: 0.13
Nodes (4): ContentTypeDriver, _extract_duration_target(), _init_drivers(), _register()

### Community 83 - "test_nonprod.py"
Cohesion: 0.08
Nodes (12): _nonprod_retirement_metrics(), _sort_empty_last(), _mcp_call(), mcp_query(), TestListNonprodItems, TestMcpQueryOrdering, TestNonprodIgnore, TestNonprodRouteExists (+4 more)

### Community 84 - "run_retirement_sweep"
Cohesion: 0.07
Nodes (46): run_retirement_sweep(), test_lifecycle_completion_retry_comments_only_after_jira_cleanup(), test_lifecycle_notice_terminal_comments_once(), test_lifecycle_old_closed_workflows_do_not_backfill(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure() (+38 more)

### Community 85 - "_user_has_db_role"
Cohesion: 0.23
Nodes (3): _get_cached_role_assignments(), _user_has_db_role(), TestDbRoleCheck

### Community 86 - "middleware/auth.py"
Cohesion: 0.10
Nodes (18): Key Patterns, _check_api_key_role_ceiling(), get_current_user(), _log_auth_decision(), _parse_sa_allowlist(), require_admin(), require_auth(), require_curator() (+10 more)

### Community 87 - "asyncio"
Cohesion: 0.21
Nodes (12): InvalidShowroomRef, run_stale_check(), run_analysis(), test_legacy_queue_sibling_payload_cannot_write_other_items(), test_missing_repo_stale_lookup_invalidates_artifacts(), test_stale_check_never_clears_unrelated_stale_item(), test_stale_lookup_failure_cannot_fail_newer_source(), repaired_while_checking() (+4 more)

### Community 88 - "hashlib"
Cohesion: 0.24
Nodes (5): jira_auth_configured(), build_jira_event(), _deliver_pending_events(), event_timestamp(), observe_pr_events()

### Community 89 - "build_retirement_description"
Cohesion: 0.08
Nodes (20): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+12 more)

### Community 90 - "MemoryArtifacts"
Cohesion: 0.17
Nodes (3): MemoryArtifacts, scan(), run()

### Community 91 - "test_analysis_labels.py"
Cohesion: 0.20
Nodes (4): test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists()

### Community 92 - "json"
Cohesion: 0.09
Nodes (21): _call_litemaas_inner(), call_llm(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), _extract_json(), route() (+13 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.09
Nodes (37): start_scan(), pre_clone_key(), order_for_reuse(), resolve_commits(), showroom_reuse_key(), item_reuse_key(), reuse_lock_id(), scan_babylon_item() (+29 more)

### Community 94 - "showroom_source.py"
Cohesion: 0.36
Nodes (6): declares_or_overrides_content(), family_members(), _keep(), walk(), FamilyMember, SourceNode

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "pytest"
Cohesion: 0.10
Nodes (24): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+16 more)

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "ResolvedShowroom"
Cohesion: 0.17
Nodes (10): effective_showroom_source(), ResolvedShowroom, snapshots(), test_dry_run_performs_no_writes(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data(), test_reset_rejects_non_babylon_or_missing_ids_atomically(), test_catalog_resolution_failure_invalidates_previous_vectors_without_scan() (+2 more)

### Community 101 - "seed_chat_fixtures"
Cohesion: 0.12
Nodes (22): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+14 more)

### Community 102 - "test_vocabulary_admin.py"
Cohesion: 0.14
Nodes (4): clear_vocabulary_cache(), client(), TestRoleGating, TestVocabularyEndpoints

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "CLAUDE.md — Project Instructions"
Cohesion: 0.18
Nodes (13): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API, PostgreSQL with pgvector (+5 more)

### Community 106 - ".upsert_babylon_catalog_item"
Cohesion: 0.05
Nodes (31): _seed_label_count_items(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none(), test_label_counts_follow_other_filters() (+23 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (10): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+2 more)

### Community 108 - "ArchitectureDriver"
Cohesion: 0.20
Nodes (8): ArchitectureDriver, _primary_asset_type(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 109 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 111 - "test_api_infrastructure.py"
Cohesion: 0.22
Nodes (3): client(), seed_infrastructure(), test_sync_osspa_endpoint_enqueues_a_job()

### Community 112 - "workers/base.py"
Cohesion: 0.09
Nodes (23): 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Candidate Dataclass, `content_entities` (shared table — all types), Design, Display Config Structure (+15 more)

### Community 113 - "jira.py"
Cohesion: 0.13
Nodes (10): _close_issue(), close_issue_done(), _fetch_oauth_token(), _get_access_token(), get_issue_status(), _issue_is_closed(), _jira_request(), _move_to_in_progress() (+2 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - "workload_scanner.py"
Cohesion: 0.07
Nodes (20): build_infrastructure_embedding_text(), generate_embedding(), _get_embedding_client(), ls_remote_sha(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes() (+12 more)

### Community 121 - "parametrize"
Cohesion: 0.16
Nodes (12): _parse_catalog_url(), pattern_check(), test_pattern_check_url_and_lb(), test_catalog_url_alone_stays_item_facts(), test_catalog_url_with_overlap_words_goes_to_overlap(), test_catalog_url_with_performance_words_stays_performance(), test_catalog_url_with_similar_goes_to_recommend_with_similar_to(), test_overlap_asks_about_a_lab_number_never_become_recommend_or_item_facts() (+4 more)

### Community 122 - "_expand_query_terms"
Cohesion: 0.09
Nodes (7): _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 123 - "Catalog Identity"
Cohesion: 0.25
Nodes (7): Catalog family, Catalog Identity, Deploy smoke check, Invariant, Rules for new code, Same content, Stage key

### Community 124 - ".create_schema"
Cohesion: 0.06
Nodes (28): db(), db(), db(), db(), db(), db(), db(), db() (+20 more)

### Community 125 - "workflow_lock_id"
Cohesion: 0.09
Nodes (25): check_pr_statuses(), retirement_sweep_cmd(), _sweep(), _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira() (+17 more)

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

### Community 132 - "Field Source Content"
Cohesion: 0.25
Nodes (7): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git()

### Community 133 - "main"
Cohesion: 0.32
Nodes (3): main(), test_execute_requires_scans_paused_confirmation(), test_script_rejects_selection_with_no_showroom_items()

### Community 135 - ".upsert_retirement_workflow"
Cohesion: 0.13
Nodes (21): _current_id(), _insert_history_row(), _other_babylon_ids(), _seed_family(), _seed_item(), test_cancelling_the_new_workflow_keeps_history(), test_current_row_lists_skip_history_rows(), test_delete_workflow_keeps_history() (+13 more)

### Community 136 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - "extract_catalog_item"
Cohesion: 0.09
Nodes (15): Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+7 more)

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

### Community 162 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 163 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 169 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 170 - "test_retirement_mark_revived.py"
Cohesion: 0.24
Nodes (14): _item_returns(), _other_babylon_ids(), _retire_everything(), _run(), test_apply_leaves_other_families_alone(), test_apply_marks_the_family_once(), test_dry_run_reports_the_change_and_writes_nothing(), test_non_retired_workflow_is_not_marked() (+6 more)

### Community 174 - "advisor.py"
Cohesion: 0.12
Nodes (15): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query() (+7 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "RouterOutput"
Cohesion: 0.42
Nodes (13): RouterOutput, Scope, resolve_and_verify(), test_lb_ref_resolves(), test_low_confidence_clarifies(), test_performance_is_public_by_default(), test_role_gate_redirects(), test_scope_ordinal() (+5 more)

### Community 180 - "_resolve_ci_references"
Cohesion: 0.33
Nodes (3): _resolve_ci_references(), test_ci_reference_to_a_stub_resolves_through_its_owner(), test_test_item_cannot_seed_recommendation_neighbor_expansion()

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 187 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 189 - "ops.py"
Cohesion: 0.05
Nodes (37): log_catalog_families(), batch_assess_overlaps(), run_field_source_sync(), log_scan_reuse_summary(), scan_candidates(), publish_progress(), with_job_context(), WorkerContext (+29 more)

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

### Community 194 - "Content Owner Model for Virtual CIs — Design"
Cohesion: 0.14
Nodes (13): Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Pure stub (+5 more)

### Community 195 - "solutions"
Cohesion: 0.50
Nodes (4): solutions, aliases, is_tdp, name

### Community 196 - "ansible.builtin.assert"
Cohesion: 0.67
Nodes (3): fail_msg, that, ansible.builtin.assert

### Community 212 - "Candidate"
Cohesion: 0.14
Nodes (4): Candidate, test_candidate_universal_fields(), test_candidate_with_type_data(), test_candidate_similarity_pct()

### Community 214 - "test_auth_security.py"
Cohesion: 0.11
Nodes (7): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders, TestUnauthenticatedAccess

### Community 217 - "content_similarity Table"
Cohesion: 0.67
Nodes (3): Evidence Pack, content_similarity Table, overlap_candidates Table

### Community 218 - "analyzer.py"
Cohesion: 0.05
Nodes (43): 3. Scan pipeline branch, canonical_content(), compute_analysis_config(), compute_content_hash(), donor_matches_commit(), donor_matches_content(), _donor_signature(), fingerprint() (+35 more)

### Community 222 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 242 - "services/__init__.py"
Cohesion: 0.19
Nodes (6): close_issue_wont_do(), test_already_closed_issue_needs_no_transition(), test_closure_requires_a_terminal_result(), test_required_closure_selects_resolution_and_verifies_result(), request(), test_jira_close_reports_whether_it_transitioned()

### Community 243 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (4): client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 247 - "handlers.py"
Cohesion: 0.13
Nodes (24): get_item_workloads(), get_performance_scores(), _analysis(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+16 more)

### Community 249 - "request_with_references"
Cohesion: 0.50
Nodes (3): request_with_references(), test_request_text_describes_what_the_referenced_item_covers(), test_request_text_is_the_query_when_there_is_no_reference()

### Community 250 - "test_drivers.py"
Cohesion: 0.16
Nodes (12): get_driver(), get_drivers_for_types(), format_triage_candidates(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_get_driver_architecture(), test_get_driver_lab(), test_get_driver_unknown_raises() (+4 more)

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1519 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **85 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `test_retirement_history_schema.py`, `main`, `.upsert_retirement_workflow`, `test_description_analysis.py`, `test_retirement_jira_events.py`, `extract_catalog_item`, `test_overlap_assessment.py`, `catalog_identity.py`, `services/catalog.py`, `.upsert_babylon_catalog_item`, `test_retirement_edit.py`, `chat_sessions.py`, `Any`, `.upsert_infrastructure`, `._card_visibility_sql`, `test_chat_live.py`, `pipeline.py`, `test_retirement_mark_revived.py`, `extract_base_name`, `vector_search.py`, `RouterOutput`, `_resolve_ci_references`, `retirement_label`, `test_osspa_analysis.py`, `showroom_helpers.py`, `run_osspa_sync`, `re`, `create_app`, `TestGetNonprodBaseNames`, `.get_unknown_terms`, `test_catalog_osspa_routes.py`, `test_overlap_chat_families.py`, `test_field_source_sync.py`, `ops.py`, `.create_job`, `cli.py`, `Description-Based Analysis for Items With No Showroom — Design`, `test_nonprod.py`, `run_retirement_sweep`, `analyzer.py`, `test_analysis_labels.py`, `json`, `test_showroom_scan.py`, `seed_chat_fixtures`, `.upsert_babylon_catalog_item`, `test_api_infrastructure.py`, `workload_scanner.py`, `handlers.py`, `.create_schema`, `workflow_lock_id`, `_generate_key`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `Database` (e.g. with `One owner` and `lifespan()`) actually correct?**
  _`Database` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_jira_request` be split into smaller, more focused modules?**
  _Cohesion score 0.10344827586206896 - nodes in this community are weakly interconnected._
- **Why does `Advisor v2 — Content-Type Drivers` connect `Advisor v2 — Content-Type Drivers` to `workers/base.py`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.022893772893772892 - nodes in this community are weakly interconnected._