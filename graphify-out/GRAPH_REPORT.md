# Graph Report - feat-rhdpcd-2331-retire-history-schema  (2026-11-26)

## Corpus Check
- 307 files · ~338,585 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4585 nodes · 11598 edges · 231 communities (151 shown, 80 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1121 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c292d7b0`
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
- ops.py
- test_description_analysis.py
- schemas.py
- test_retirement_jira_events.py
- Infrastructure Catalog
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- test_showroom_reuse.py
- test_catalog_identity.py
- services/catalog.py
- .upsert_babylon_catalog_item
- test_catalog_families.py
- _jira_event_messages
- chat_sessions.py
- test_osspa_adoc.py
- react
- Settings
- routes/auth.py
- test_showroom_source.py
- .get_content_entity
- seed
- App.tsx
- catalog_identity.py
- test_agv_access.py
- test_overlap_candidates.py
- test_content_owner.py
- run_category
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- test_test_content_exclusion.py
- compilerOptions
- test_jira_service.py
- pipeline.py
- Candidate
- analyzer.py
- item
- compute_sales_impact
- api.ts
- normalize_analysis
- dev-services.sh
- test_osspa_analysis.py
- ._artifact_connection
- HandsOnDriver
- test_analysis_identity.py
- Vocabulary
- ls_remote_sha
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
- mcp_query
- json
- Request
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
- test_analysis_labels.py
- middleware/auth.py
- test_auth_routes.py
- hashlib
- build_retirement_description
- Path
- Design
- config.py
- test_showroom_scan.py
- showroom_source.py
- Showroom analysis isolation
- Scan Pipeline
- pytest
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- test_workers.py
- pytest
- test_vocabulary_admin.py
- rcars-login.sh
- CLAUDE.md — Project Instructions
- AdocRead
- test_db.py
- RCARS OCP Deployment Playbook
- ArchitectureDriver
- ContentAnalysisPage.tsx
- Rec Card Duration and Best Fit Spec
- _parse_sa_allowlist
- test_api_infrastructure.py
- jira.py
- content_entities Table
- workload_scanner.py
- Deploy Docs GitHub Actions Workflow
- Change Detection
- test_reporting.py
- Overlap Detection Redesign
- _build_windowed_metrics
- Catalog Identity
- _expand_query_terms
- retirement_jira_events.py
- .create_schema
- workflow_lock_id
- _generate_key
- TestRetirementDashboardMetrics
- vocabulary.yaml
- pre_tasks
- test_retirement_history_schema.py
- client
- retirement_label
- recommendations.py
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
- request_with_references
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
- advisor.py
- test_vocabulary.py
- Python Requirements Entry Point
- RouterOutput
- build_embedding_text
- ignored_terms
- _sync_nonprod_usage
- TestGetNonprodBaseNames
- settings.py
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- Content Owner Model for Virtual CIs — Design
- solutions
- ansible.builtin.assert
- Browse Page Redesign Spec
- Candidate
- TestTokenExchange
- test_auth_security.py
- analyzer.py
- handlers.py

## God Nodes (most connected - your core abstractions)
1. `Database` - 328 edges
2. `Settings` - 177 edges
3. `load_vocabulary()` - 67 edges
4. `Candidate` - 50 edges
5. `seed()` - 50 edges
6. `item()` - 50 edges
7. `create_app()` - 43 edges
8. `scan_babylon_item()` - 42 edges
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

## Communities (231 total, 80 thin omitted)

### Community 0 - "_jira_request"
Cohesion: 0.10
Nodes (16): _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen() (+8 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (7): Database, main(), test_advisor_session(), test_enrichment_tags(), test_advisory_lock_is_not_reentrant_across_sessions(), test_execute_requires_scans_paused_confirmation(), test_script_rejects_selection_with_no_showroom_items()

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

### Community 6 - "test_advisor_families.py"
Cohesion: 0.13
Nodes (32): assert_invariant(), cid(), _clear_own_analysis(), link(), _not_eligible(), run(), _set_hash(), test_card_analysis_keeps_the_cleared_own_row_when_there_is_no_anchor() (+24 more)

### Community 7 - "ops.py"
Cohesion: 0.06
Nodes (24): Decisions (Nate, 2026-11-19), workload_scan(), ls_remote_sha(), run_field_source_sync(), build_sandbox_summary(), log_scan_reuse_summary(), scan_candidates(), scan_all_collections() (+16 more)

### Community 8 - "test_description_analysis.py"
Cohesion: 0.06
Nodes (76): add_tag(), AnalysisSourceRequest, catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+68 more)

### Community 9 - "schemas.py"
Cohesion: 0.05
Nodes (64): field_source_report(), health(), readiness(), AgvPrResponse, AuthMeResponse, CancelWorkflowResponse, CatalogItemResponse, CatalogItemWorkload (+56 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.07
Nodes (35): deliver_pending_events(), client(), comments(), event_time(), settings(), request(), test_comment_malformed_page_does_not_prove_absence(), test_comment_missing_credentials_does_not_call_http() (+27 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.17
Nodes (13): Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, content_similarity Table, embeddings Table (+5 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (36): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+28 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.09
Nodes (21): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+13 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (3): derive_status(), TestDeriveStatus, TestStepOrder

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_showroom_reuse.py"
Cohesion: 0.07
Nodes (28): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git(), as_donor() (+20 more)

### Community 17 - "test_catalog_identity.py"
Cohesion: 0.24
Nodes (24): collapse(), hit(), ids(), row(), test_dev_and_event_only_keep_the_event_copy(), test_different_stage_keys_with_equal_hash_never_merge(), test_field_asset_no_virtual_ci_eligible_member_shows(), test_field_asset_one_component_two_eligible_virtual_cis_gives_two_cards() (+16 more)

### Community 18 - "services/catalog.py"
Cohesion: 0.06
Nodes (22): refresh(), _apply_component_inheritance(), CatalogFamilies, CatalogReader, collect(), load(), _collect_bases(), component_item_to_ci_name() (+14 more)

### Community 19 - ".upsert_babylon_catalog_item"
Cohesion: 0.07
Nodes (25): _do(), test_upsert_stores_labels(), db_with_perf_data(), test_content_path(), test_list_catalog_items(), test_retire_missing_babylon_ignores_other_sources(), test_upsert_and_get_catalog_item(), test_upsert_updates_existing() (+17 more)

### Community 20 - "test_catalog_families.py"
Cohesion: 0.16
Nodes (30): build_catalog_families(), _clean(), four_level(), graph(), _item(), members(), node(), _rows() (+22 more)

### Community 21 - "_jira_event_messages"
Cohesion: 0.07
Nodes (15): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_rejected_for_retired_item(), test_edit_rejected_while_cancellation_pending(), test_edit_rejects_name_without_replacement_ci() (+7 more)

### Community 22 - "chat_sessions.py"
Cohesion: 0.17
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.13
Nodes (23): buildUrl(), FALLBACK_FORMAT_LABELS, FORMAT_COLORS, RecCard(), RecCardProps, CollapsibleTier(), RecCardList(), RecCardListProps (+15 more)

### Community 25 - "Settings"
Cohesion: 0.08
Nodes (27): list_role_assignments(), llm_provider_status(), fetch_litemaas_models(), _parse_csv(), Settings, settings(), _FakeModels, _litemaas_settings() (+19 more)

### Community 26 - "routes/auth.py"
Cohesion: 0.22
Nodes (10): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), revoke_api_key(), revoke_own_token() (+2 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.20
Nodes (23): ComponentLink, content_owner(), node(), resolve(), test_branch_with_two_sources_is_ambiguous(), test_component_reference_honors_explicit_stage(), test_converging_paths_to_one_owner_are_unambiguous(), test_curator_content_path_override_is_not_a_pure_stub() (+15 more)

### Community 28 - ".get_content_entity"
Cohesion: 0.13
Nodes (12): db(), _row(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override() (+4 more)

### Community 29 - "seed"
Cohesion: 0.10
Nodes (43): snapshots(), test_dry_run_performs_no_writes(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data(), test_reset_rejects_non_babylon_or_missing_ids_atomically(), test_reset_rejects_running_or_queued_analysis_jobs(), add_stub(), link() (+35 more)

### Community 30 - "App.tsx"
Cohesion: 0.07
Nodes (42): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), LlmProviderCard() (+34 more)

### Community 31 - "catalog_identity.py"
Cohesion: 0.08
Nodes (23): One owner, _best(), cards_sharing_a_family(), collapse_to_cards(), CollapseStats, enforce_card_invariant(), exclusion_set_for(), family_exclusion_core() (+15 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (69): AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr(), _delete_directory_tree() (+61 more)

### Community 33 - "test_overlap_candidates.py"
Cohesion: 0.10
Nodes (12): get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), seed_items(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats(), test_idempotent_upsert() (+4 more)

### Community 34 - "test_content_owner.py"
Cohesion: 0.13
Nodes (31): analyze_single(), rescan_all(), reconcile_pure_stubs(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner(), test_browse_difficulty_filter_finds_a_stub_by_its_mirrored_card() (+23 more)

### Community 35 - "run_category"
Cohesion: 0.08
Nodes (24): 1. Content-Type Drivers, 2. Orchestrator and Pipeline, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Candidate Dataclass (+16 more)

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
Cohesion: 0.10
Nodes (23): extract_showroom_url(), _source_node(), _resolve_ci_references(), ContentDeclaration, resolve_showroom_source(), unresolved(), walk(), SourceNode (+15 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.18
Nodes (19): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_basic_description() (+11 more)

### Community 42 - "pipeline.py"
Cohesion: 0.08
Nodes (13): _build_deterministic_assessment(), _call_synthesis(), generate_content_gaps(), generate_rationale(), triage(), _collapse_families(), _embedding_owner_id(), _is_excluded() (+5 more)

### Community 43 - "Candidate"
Cohesion: 0.12
Nodes (12): QueryState, test_query_state_no_grouped_results(), test_rationale_and_synthesis_receive_the_reference_summary(), _run_catalog_second_pass(), test_candidate_tier_defaults(), test_imports(), test_multi_base_published_ci(), test_published_ci_name_not_set_by_non_published() (+4 more)

### Community 44 - "analyzer.py"
Cohesion: 0.09
Nodes (26): check_showroom_stale(), classify_scan_error(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content() (+18 more)

### Community 45 - "item"
Cohesion: 0.21
Nodes (23): card_ids(), item(), test_virtual_ci_without_anchor_stands_alone_and_nothing_collapses(), ref(), run_similar(), test_component_covered_by_two_virtual_cis_excludes_both(), test_dev_copy_is_excluded_even_when_dev_is_not_selected_or_is_selected(), test_empty_family_tables_exclude_the_item_and_its_stage_copies_only() (+15 more)

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

### Community 50 - "test_osspa_analysis.py"
Cohesion: 0.15
Nodes (12): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), test_curator_actions_work_on_a_pa_identifier(), stub_llm(), test_analyze_flags_review_when_the_adoc_was_truncated(), test_analyze_leaves_item_stale_when_the_embedding_write_fails(), test_analyze_normalizes_vocabulary_and_queues_unknown_terms() (+4 more)

### Community 52 - "HandsOnDriver"
Cohesion: 0.17
Nodes (8): _extract_duration_target(), HandsOnDriver, _make_hands_on_candidate(), test_hands_on_display_config(), test_hands_on_format_for_rationale(), test_hands_on_serialize_streaming(), test_hands_on_serialize_with_performance(), test_hands_on_triage_guidance()

### Community 53 - "test_analysis_identity.py"
Cohesion: 0.11
Nodes (17): donor_matches_content(), config(), donor_row(), test_commit_donor_needs_repo_commit_path_and_config(), test_config_follows_content_type_when_vocabulary_mode_differs(), test_config_follows_prompt_template_and_vocabulary(), test_config_is_stable_and_follows_model_and_policy(), test_content_donor_matches_on_hash_config_and_type_only() (+9 more)

### Community 55 - "ls_remote_sha"
Cohesion: 0.18
Nodes (6): commit_for_ref(), _is_github_throttle(), ls_remote_refs(), resolve(), _resolve_ref_from_lookup(), _run_git_with_retry()

### Community 56 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (19): asset_type_tokens(), fetch_palist_csv(), OsspaSyncError, parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status() (+11 more)

### Community 57 - "run_osspa_sync"
Cohesion: 0.33
Nodes (16): run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items(), test_missing_detail_page_marks_stale_and_skips() (+8 more)

### Community 58 - "loader.py"
Cohesion: 0.11
Nodes (13): _entries_to_dicts(), _header_comment(), _as_tuple(), _build_lookups(), _parse_entries(), _resolve_path(), _validate(), squash_key() (+5 more)

### Community 59 - "Retirement System"
Cohesion: 0.08
Nodes (26): AgV Access Layer, Architecture, Authentication and Scope, Automatic Removal Eligibility, Cancellation and Recovery, Catalog Soft-Delete, Checking Merges, Code Organization (+18 more)

### Community 60 - "re"
Cohesion: 0.13
Nodes (8): _expand_vocab_aliases(), _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), _strip_html(), _validate_url()

### Community 61 - "create_app"
Cohesion: 0.05
Nodes (18): create_app(), lifespan(), RequestLoggingMiddleware, client(), test_auth_me_unauthenticated(), client(), client(), non_admin_client() (+10 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.16
Nodes (7): client(), _second_architecture(), settings(), test_detail_route_reports_sibling_stage_retirement(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures(), test_verticals_filter_narrows_to_matching_architectures()

### Community 63 - "SyncPage.tsx"
Cohesion: 0.33
Nodes (10): LogWindow(), LogWindowProps, ActionState, AdminAction(), RescanAllSection(), ScanMonitor(), ScheduledMaintenance(), ScheduleInfo (+2 more)

### Community 64 - "with"
Cohesion: 0.07
Nodes (31): runs-on, steps, environment, needs, runs-on, steps, name, url (+23 more)

### Community 65 - "test_overlap_chat_families.py"
Cohesion: 0.09
Nodes (40): generate_overlap_candidates(), lift_to_covering(), pattern_check(), resolve_item(), TestUnauthenticatedAccess, test_pattern_check_url_and_lb(), add(), _family_with_pairs_on_the_member() (+32 more)

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

### Community 72 - "mcp_query"
Cohesion: 0.22
Nodes (4): _mcp_call(), mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 73 - "json"
Cohesion: 0.10
Nodes (19): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials(), build_product_entry() (+11 more)

### Community 74 - "Request"
Cohesion: 0.06
Nodes (60): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+52 more)

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
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 79 - "cli.py"
Cohesion: 0.05
Nodes (37): command, concurrency, cancel-in-progress, group, check_card_families(), cli(), flag(), get_db() (+29 more)

### Community 80 - "Description-Based Analysis for Items With No Showroom — Design"
Cohesion: 0.17
Nodes (10): Anti-goals, Approaches considered, Constraints, Deployment, Description-Based Analysis for Items With No Showroom — Design, Goals, Intent, Non-goals (+2 more)

### Community 81 - "test_auth_middleware.py"
Cohesion: 0.14
Nodes (9): _fetch_group_members(), _user_in_groups(), _validate_sa_token(), _mock_async_client(), _mock_async_client_get(), _mock_group_response(), _mock_token_review_response(), TestGroupLookup (+1 more)

### Community 82 - "test_drivers.py"
Cohesion: 0.10
Nodes (14): ContentTypeDriver, get_driver(), get_drivers_for_types(), _init_drivers(), _register(), format_triage_candidates(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data() (+6 more)

### Community 83 - "test_nonprod.py"
Cohesion: 0.07
Nodes (13): _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), _build_nonprod_provisions_sql(), TestListNonprodItems, TestNonprodIgnore, TestNonprodProvisionsSql, TestNonprodRouteExists (+5 more)

### Community 84 - "run_retirement_sweep"
Cohesion: 0.07
Nodes (42): run_retirement_sweep(), run_retirement_sweep_job(), test_database_schema_setup_does_not_move_cutoff(), test_lifecycle_old_closed_workflows_do_not_backfill(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure() (+34 more)

### Community 85 - "test_analysis_labels.py"
Cohesion: 0.15
Nodes (5): client(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists()

### Community 86 - "middleware/auth.py"
Cohesion: 0.07
Nodes (22): Key Patterns, _check_api_key_role_ceiling(), _get_cached_role_assignments(), get_current_user(), _log_auth_decision(), require_admin(), require_auth(), require_curator() (+14 more)

### Community 87 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (4): client(), TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 88 - "hashlib"
Cohesion: 0.13
Nodes (9): ensure_issue_event_comment(), jira_auth_configured(), _oauth_config(), _reset_token_cache(), _deliver_pending_events(), _clean_token_cache(), test_comment_failed_lookup_does_not_post(), test_comment_http_payload_accepts_object_marker_and_recovers_lost_response() (+1 more)

### Community 89 - "build_retirement_description"
Cohesion: 0.08
Nodes (20): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Open Questions / Risks (+12 more)

### Community 90 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 91 - "Design"
Cohesion: 0.33
Nodes (6): 1. Storage, 2. Source resolution, 5. API, 6. Frontend, 7. Coverage math, Design

### Community 92 - "config.py"
Cohesion: 0.13
Nodes (19): _call_litemaas_inner(), call_llm(), LLMResult, build_scaffold(), compose_answer(), _strip_formatting(), _extract_json(), route() (+11 more)

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.07
Nodes (54): start_scan(), pre_clone_key(), InvalidShowroomRef, order_for_reuse(), showroom_reuse_key(), item_reuse_key(), reuse_lock_id(), scan_babylon_item() (+46 more)

### Community 94 - "showroom_source.py"
Cohesion: 0.43
Nodes (5): declares_or_overrides_content(), family_members(), _keep(), walk(), FamilyMember

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "pytest"
Cohesion: 0.11
Nodes (21): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+13 more)

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "test_workers.py"
Cohesion: 0.24
Nodes (6): test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes()

### Community 101 - "pytest"
Cohesion: 0.08
Nodes (28): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+20 more)

### Community 102 - "test_vocabulary_admin.py"
Cohesion: 0.14
Nodes (4): clear_vocabulary_cache(), client(), TestRoleGating, TestVocabularyEndpoints

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
Cohesion: 0.06
Nodes (27): _seed_label_count_items(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none(), test_label_counts_follow_other_filters() (+19 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.18
Nodes (12): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+4 more)

### Community 108 - "ArchitectureDriver"
Cohesion: 0.20
Nodes (8): ArchitectureDriver, _primary_asset_type(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 109 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (14): AssessmentSection(), ComparisonDrawer(), ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment (+6 more)

### Community 113 - "jira.py"
Cohesion: 0.09
Nodes (15): _close_issue(), close_issue_done(), close_issue_wont_do(), _fetch_oauth_token(), _get_access_token(), get_issue_status(), _issue_is_closed(), _jira_request() (+7 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - "workload_scanner.py"
Cohesion: 0.07
Nodes (17): build_infrastructure_embedding_text(), generate_embedding(), _get_embedding_client(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products() (+9 more)

### Community 118 - "test_reporting.py"
Cohesion: 0.18
Nodes (4): _extrapolate_count(), _window_start(), TestExtrapolateCount, TestWindowStart

### Community 121 - "Catalog Identity"
Cohesion: 0.25
Nodes (7): Catalog family, Catalog Identity, Deploy smoke check, Invariant, Rules for new code, Same content, Stage key

### Community 122 - "_expand_query_terms"
Cohesion: 0.09
Nodes (7): _build_expansion_map(), _expand_query_terms(), clear_vocabulary_cache(), TestExpansionReadsVocabulary, TestMigrationCoverage, TestOldFileGone, TestSearchTerms

### Community 123 - "retirement_jira_events.py"
Cohesion: 0.32
Nodes (3): build_jira_event(), event_timestamp(), observe_pr_events()

### Community 124 - ".create_schema"
Cohesion: 0.06
Nodes (31): db(), db(), seed_infrastructure(), db(), db(), db(), db(), db() (+23 more)

### Community 125 - "workflow_lock_id"
Cohesion: 0.12
Nodes (20): _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable() (+12 more)

### Community 127 - "_generate_key"
Cohesion: 0.15
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

### Community 134 - "recommendations.py"
Cohesion: 0.12
Nodes (4): _get_user_key(), get_recommendations(), RecommendationRequest, _run_medium()

### Community 135 - ".upsert_retirement_workflow"
Cohesion: 0.10
Nodes (25): _current_id(), _insert_history_row(), _other_babylon_ids(), _seed_family(), _seed_item(), test_cancelling_the_new_workflow_keeps_history(), test_current_row_lists_skip_history_rows(), test_delete_workflow_keeps_history() (+17 more)

### Community 136 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - "extract_catalog_item"
Cohesion: 0.10
Nodes (14): Anti-goals, Constraints, Decisions, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout (+6 more)

### Community 143 - "retirement-system.md"
Cohesion: 0.19
Nodes (18): Token Usage Tracking (5 Operation Types), CLI Admin Guide, Worker Management, Token Usage Tracking Guide, Advisor Chat System, API Reference, Content Overlap Detection, Cosine Similarity for Overlap (+10 more)

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

### Community 159 - "request_with_references"
Cohesion: 0.50
Nodes (3): request_with_references(), test_request_text_describes_what_the_referenced_item_covers(), test_request_text_is_the_query_when_there_is_no_reference()

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
Cohesion: 0.17
Nodes (19): _clean(), _item_returns(), _other_babylon_ids(), _retire_everything(), _run(), test_ambiguous_family_is_refused(), test_apply_leaves_other_families_alone(), test_apply_marks_the_family_once() (+11 more)

### Community 174 - "advisor.py"
Cohesion: 0.09
Nodes (23): Frontend Progress Display, What Stays Unchanged, ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation() (+15 more)

### Community 175 - "test_vocabulary.py"
Cohesion: 0.15
Nodes (4): dedup_topics(), clear_vocabulary_cache(), TestSquashKey, TestTopicDedup

### Community 178 - "RouterOutput"
Cohesion: 0.16
Nodes (20): _prefix_overlap(), RouterOutput, Scope, _find_keyword_ties(), _guess_clarification(), _parse_catalog_url(), resolve_and_verify(), _result_turns() (+12 more)

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 187 - "_sync_nonprod_usage"
Cohesion: 0.33
Nodes (3): _nonprod_metrics(), _sync_nonprod_usage(), TestSyncNonprodUsage

### Community 189 - "settings.py"
Cohesion: 0.07
Nodes (32): _add_component(), get_logger(), _reorder_keys(), setup_logging(), WorkerContext, run_chat_turn(), on_progress(), cleanup_orphaned_jobs() (+24 more)

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
Cohesion: 0.12
Nodes (7): Candidate, _call_rationale_single(), _format_single_candidate(), test_candidate_universal_fields(), test_candidate_with_type_data(), test_candidate_similarity_pct(), test_format_single_candidate_handles_architecture()

### Community 214 - "test_auth_security.py"
Cohesion: 0.12
Nodes (6): app_no_auth(), client(), TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling, TestSpoofedProxyHeaders

### Community 218 - "analyzer.py"
Cohesion: 0.06
Nodes (41): 3. Scan pipeline branch, 4. Candidate selection and stale check, canonical_content(), compute_analysis_config(), compute_content_hash(), donor_matches_commit(), _donor_signature(), fingerprint() (+33 more)

### Community 247 - "handlers.py"
Cohesion: 0.08
Nodes (27): get_item_workloads(), get_performance_scores(), _analysis(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+19 more)

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1524 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **80 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `test_retirement_history_schema.py`, `retirement_label`, `ops.py`, `.upsert_retirement_workflow`, `test_retirement_jira_events.py`, `extract_catalog_item`, `test_overlap_assessment.py`, `services/catalog.py`, `.upsert_babylon_catalog_item`, `_jira_event_messages`, `chat_sessions.py`, `test_showroom_source.py`, `.get_content_entity`, `.upsert_infrastructure`, `catalog_identity.py`, `showroom_helpers.py`, `test_overlap_candidates.py`, `run_category`, `test_test_content_exclusion.py`, `pipeline.py`, `test_retirement_mark_revived.py`, `extract_base_name`, `test_osspa_analysis.py`, `._artifact_connection`, `RouterOutput`, `test_analysis_identity.py`, `run_osspa_sync`, `TestGetNonprodBaseNames`, `settings.py`, `create_app`, `.get_unknown_terms`, `test_catalog_osspa_routes.py`, `test_overlap_chat_families.py`, `test_field_source_sync.py`, `json`, `.create_job`, `cli.py`, `Description-Based Analysis for Items With No Showroom — Design`, `test_nonprod.py`, `run_retirement_sweep`, `test_analysis_labels.py`, `analyzer.py`, `pytest`, `pytest`, `test_db.py`, `test_api_infrastructure.py`, `workload_scanner.py`, `handlers.py`, `.create_schema`, `workflow_lock_id`, `.backfill_revived_workflows`, `_generate_key`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `Database` (e.g. with `One owner` and `lifespan()`) actually correct?**
  _`Database` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_jira_request` be split into smaller, more focused modules?**
  _Cohesion score 0.10344827586206896 - nodes in this community are weakly interconnected._
- **Why does `Advisor v2 — Content-Type Drivers` connect `Advisor v2 — Content-Type Drivers` to `run_category`, `advisor.py`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.024250743536948068 - nodes in this community are weakly interconnected._