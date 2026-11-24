# Graph Report - rhdpcd-2298-reference  (2026-11-24)

## Corpus Check
- 302 files · ~330,853 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .css 5, .example 2)

## Summary
- 4432 nodes · 11091 edges · 239 communities (157 shown, 82 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 1049 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `21ca6b50`
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
- create_app
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
- ResolvedShowroom
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
- Path
- command
- Description-Based Analysis for Items With No Showroom — Design
- test_test_content_exclusion.py
- commit_for_ref
- test_nonprod.py
- test_retirement_pr_status.py
- Any
- _make_request
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
- Request
- Infrastructure-Aware Catalog Metadata
- API Authentication Design
- build_retirement_description
- seed_chat_fixtures
- test_vocabulary_admin.py
- rcars-login.sh
- CLAUDE.md — Project Instructions
- AdocRead
- test_db.py
- RCARS OCP Deployment Playbook
- osspa_sync.py
- get
- Rec Card Duration and Best Fit Spec
- mcp_query
- workers/base.py
- chat/models.py
- content_entities Table
- OsspaSyncError
- Deploy Docs GitHub Actions Workflow
- Change Detection
- .reset_babylon_scan_artifacts
- Overlap Detection Redesign
- settings.py
- TestBuildWindowedMetrics
- test_product_terms.py
- vector_search.py
- test_orphan_cleanup.py
- retirement_cleanup.py
- _reset_token_cache
- _generate_key
- vocabulary.yaml
- pre_tasks
- test_llm_routing.py
- chat_sessions.py
- _user_has_db_role
- _extrapolate_count
- test_status_visibility.py
- middleware/auth.py
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
- group
- Python Dependency Manifest (requirements.lock)
- app.py
- patch
- deploy.yml
- LLM Overlap Assessment Design
- rcars
- rcars
- tasks
- Match Event Prompt Template
- extract_base_name
- pytest
- recommendations.py
- dedup_topics
- Python Requirements Entry Point
- RouterOutput
- test_cancel_preserves_tracking_on_github_failure
- _jira_request
- content_similarity Table
- test_chat_handlers.py
- ignored_terms
- test_chat_live.py
- test_llm_provider_status.py
- TestGetNonprodBaseNames
- test_osspa_pipeline_runs_even_when_babylon_fails
- content_modes
- .get_unknown_terms
- kubernetes.core.k8s_exec
- collections
- with_job_context
- solutions
- ansible.builtin.assert
- TestVocabularyEndpoints
- TestPromptInjection
- Browse Page Redesign Spec
- require_performance_view
- TestStepOrder
- TestSearchTerms
- TestTokenExchange
- Content Owner Model for Virtual CIs — Design
- readiness
- TestSpoofedProxyHeaders
- on_progress
- TestCreateApiKey
- TestRevokeApiKey
- TestRoleCeiling
- TestUnknownTermsSchema
- _move_to_in_progress
- test_edit_rejects_name_without_replacement_ci
- test_edit_rejected_for_retired_item
- test_edit_rejected_while_cancellation_pending

## God Nodes (most connected - your core abstractions)
1. `Database` - 312 edges
2. `Settings` - 179 edges
3. `load_vocabulary()` - 68 edges
4. `seed()` - 51 edges
5. `Candidate` - 50 edges
6. `item()` - 48 edges
7. `create_app()` - 43 edges
8. `scan_babylon_item()` - 42 edges
9. `run_retirement_sweep()` - 39 edges
10. `ResolvedShowroom` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Entry Points` --references--> `run_category()`  [INFERRED]
  docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md → src/api/rcars/services/recommender/pipeline.py
- `Advisor` --references--> `search()`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/recommender/vector_search.py
- `Root cause` --references--> `AnalysisSignature`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py
- `Curator edits` --references--> `content_owner()`  [INFERRED]
  docs/superpowers/specs/2026-11-04-content-owner-model-design.md → src/api/rcars/services/showroom_source.py
- `Non-goals` --references--> `extract_catalog_item()`  [INFERRED]
  docs/superpowers/specs/2026-10-28-platform-tdp-filters-design.md → src/api/rcars/services/catalog.py

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

## Communities (239 total, 82 thin omitted)

### Community 0 - "_FakeResponse"
Cohesion: 0.10
Nodes (16): _FakeResponse, _header(), _oauth_settings(), test_jira_auth_configured_requires_all_oauth_fields(), test_oauth_token_fetched_on_first_call_and_cached(), fake_urlopen(), test_oauth_token_refreshed_near_or_past_expiry(), fake_urlopen() (+8 more)

### Community 1 - "Database"
Cohesion: 0.02
Nodes (4): Database, test_advisor_session(), test_enrichment_tags(), test_advisory_lock_is_not_reentrant_across_sessions()

### Community 2 - "react"
Cohesion: 0.14
Nodes (21): InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps (+13 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.15
Nodes (21): architecture_analysis DB Table, OSSPA Asset Type Vocabulary (PA/VP/SP), Babylon CRD Catalog Pipeline, Browse Catalog Integration for Architecture Items, content_entities Universal Entity Registry Table, nomic-embed-text-v1.5 Embedding Model, Jira RHDPCD-28 Portfolio Architecture Ingest, LLM Architecture Analysis (+13 more)

### Community 4 - "common.yml"
Cohesion: 0.03
Nodes (58): admin_emails, api_cpu_limit, api_cpu_request, api_memory_limit, api_memory_request, api_replicas, app_name, app_port (+50 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (53): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-icons, @patternfly/react-table, react-dom (+45 more)

### Community 6 - "test_advisor_families.py"
Cohesion: 0.09
Nodes (61): enforce_card_invariant(), family_exclusion_core(), request_with_references(), assert_invariant(), card_ids(), _clear_own_analysis(), item(), link() (+53 more)

### Community 7 - "db/__init__.py"
Cohesion: 0.12
Nodes (13): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), seed_items(), test_generates_candidates_above_threshold(), test_get_overlap_items_groups_by_item(), test_get_overlap_stats() (+5 more)

### Community 8 - "test_description_analysis.py"
Cohesion: 0.06
Nodes (76): add_tag(), AnalysisSourceRequest, catalog_facets(), catalog_stats(), ContentPathRequest, _curation_target(), DurationRequest, flag_item() (+68 more)

### Community 9 - "admin.py"
Cohesion: 0.07
Nodes (44): field_source_report(), list_api_keys(), ApiKeyInfo, ApiKeyListResponse, AuthMeResponse, CatalogItemResponse, CatalogItemWorkload, CatalogListResponse (+36 more)

### Community 10 - "test_retirement_jira_events.py"
Cohesion: 0.08
Nodes (35): deliver_pending_events(), comments(), event_time(), settings(), test_comment_existing_event_on_later_page_prevents_post(), request(), test_comment_malformed_page_does_not_prove_absence(), test_comment_missing_credentials_does_not_call_http() (+27 more)

### Community 11 - "Chat Router LLM"
Cohesion: 0.33
Nodes (6): Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, Infrastructure Embedding Search Design

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (37): Summary, getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline() (+29 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.08
Nodes (23): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), _validate_assessment(), _make_vector() (+15 more)

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (25): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, PatternFly 6 Migration Design, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Retirement Workflow Five Stages (Reviewed to Retired), Generalized Content Model Design (+17 more)

### Community 16 - "test_showroom_reuse.py"
Cohesion: 0.07
Nodes (28): API, Data Import, Data Source, Field Source Content, Frontend, git_repo(), git(), as_donor() (+20 more)

### Community 17 - "ops.py"
Cohesion: 0.10
Nodes (15): build_sandbox_summary(), log_scan_reuse_summary(), publish_progress(), _progress_bridge(), _publish(), run_babylon_pipeline(), run_field_source_sync_job(), run_nightly_pipeline() (+7 more)

### Community 18 - "analyze_role"
Cohesion: 0.07
Nodes (18): call_llm(), generate_embedding(), _get_embedding_client(), ls_remote_sha(), analyze_config(), analyze_role(), discover_roles(), _follow_task_includes() (+10 more)

### Community 19 - ".upsert_babylon_catalog_item"
Cohesion: 0.06
Nodes (18): _seed_label_count_items(), test_facets_platforms_and_tdps(), test_filter_groups_and(), test_filter_platform_none_excludes_architectures(), test_filter_platform_none_or_value(), test_filter_platform_value(), test_filter_tdp_matches_tdp2(), test_filter_tdp_none() (+10 more)

### Community 20 - "test_catalog_families.py"
Cohesion: 0.13
Nodes (36): build_catalog_families(), declares_or_overrides_content(), family_members(), _keep(), walk(), FamilyMember, SourceNode, _clean() (+28 more)

### Community 21 - "_jira_event_messages"
Cohesion: 0.10
Nodes (9): _jira_event_messages(), test_edit_changes_replacement_ci(), test_edit_changes_replacement_name_only(), test_edit_clears_replacement_ci(), test_edit_moves_target_date(), test_edit_requires_admin(), test_edit_update_skips_cancelled_workflows(), test_edit_without_change_records_no_event() (+1 more)

### Community 22 - "LLMResult"
Cohesion: 0.14
Nodes (14): _call_litemaas_inner(), LLMResult, _extract_json(), route(), llm(), _fake(), llm_call(), test_call_error_falls_back() (+6 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.11
Nodes (23): compute_content_hash(), expand_includes(), _expand(), is_tracked_at_head(), read_detail_adoc(), resolve_repo_path(), strip_passthrough(), _git() (+15 more)

### Community 24 - "react"
Cohesion: 0.07
Nodes (40): react, BlockErrorBoundary, Props, State, CATEGORY_LABELS, RecCardsBlock(), resolveBlockRenderer(), ChatChip (+32 more)

### Community 25 - "Settings"
Cohesion: 0.08
Nodes (25): list_role_assignments(), llm_provider_status(), fetch_litemaas_models(), _parse_csv(), Settings, settings(), _FakeModels, _litemaas_settings() (+17 more)

### Community 26 - ".close"
Cohesion: 0.06
Nodes (29): db(), db(), seed_infrastructure(), db(), db(), db(), db(), db() (+21 more)

### Community 27 - "test_showroom_source.py"
Cohesion: 0.13
Nodes (31): component_item_to_ci_name(), extract_showroom_url(), _source_node(), ComponentLink, content_owner(), ContentDeclaration, item_family_key(), node() (+23 more)

### Community 28 - "test_osspa_db.py"
Cohesion: 0.13
Nodes (11): _row(), test_architecture_analysis_staleness_round_trip(), test_babylon_upsert_writes_status_from_stage(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch(), test_retire_missing_osspa_refuses_empty_set_without_override(), test_schema_backfills_status_from_stage() (+3 more)

### Community 29 - "seed"
Cohesion: 0.09
Nodes (44): snapshots(), test_dry_run_performs_no_writes(), test_full_reset_preserves_non_showroom_sandbox_card(), test_reset_preserves_all_curated_historical_and_architecture_data(), test_reset_rejects_non_babylon_or_missing_ids_atomically(), test_reset_rejects_running_or_queued_analysis_jobs(), add_stub(), link() (+36 more)

### Community 30 - "App.tsx"
Cohesion: 0.06
Nodes (51): @patternfly/react-core, react-router-dom, App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), API_DOCS_URL (+43 more)

### Community 31 - "analysis.py"
Cohesion: 0.08
Nodes (42): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_pr_statuses(), check_stale(), edit_retirement() (+34 more)

### Community 32 - "test_agv_access.py"
Cohesion: 0.06
Nodes (71): References, AgVPathAbsent, _branch_name(), close_pr(), _create_branch(), create_notice_pr(), _create_pr(), create_retire_pr() (+63 more)

### Community 33 - "test_advisor_families.py"
Cohesion: 0.10
Nodes (40): _best(), cards_sharing_a_family(), collapse_to_cards(), CollapseStats, family_violations(), merge_stage_copies(), cid(), collapse() (+32 more)

### Community 34 - "test_content_owner.py"
Cohesion: 0.14
Nodes (30): rescan_all(), reconcile_pure_stubs(), scan_candidates(), add_item(), _browse_row(), seed_stub_artifacts(), test_analyze_single_on_a_stub_analyzes_its_owner(), test_browse_difficulty_filter_finds_a_stub_by_its_mirrored_card() (+22 more)

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
Cohesion: 0.15
Nodes (15): _add_component(), get_logger(), _reorder_keys(), setup_logging(), cleanup_orphaned_jobs(), shutdown(), test_logger_outputs_json(), test_logger_with_job_id() (+7 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+10 more)

### Community 41 - "test_jira_service.py"
Cohesion: 0.26
Nodes (15): create_retirement_ticket(), _create_body(), _fake_jira(), fake(), _make_metrics(), _make_workflow(), _settings(), test_creates_ticket_and_returns_key() (+7 more)

### Community 42 - "structlog"
Cohesion: 0.10
Nodes (16): 2. Orchestrator and Pipeline, What Gets Deleted, parse_event_url(), registered_content_types(), QueryState, run_category(), serialize_candidates(), run_query() (+8 more)

### Community 43 - "Candidate"
Cohesion: 0.11
Nodes (12): _call_rationale_single(), _format_single_candidate(), _run_catalog_second_pass(), test_candidate_similarity_pct(), test_candidate_tier_defaults(), test_format_single_candidate_handles_architecture(), test_imports(), test_multi_base_published_ci() (+4 more)

### Community 44 - "analyzer.py"
Cohesion: 0.09
Nodes (26): check_showroom_stale(), classify_scan_error(), clone_showroom(), filter_boilerplate_files(), get_repo_head(), parse_analysis_response(), _parse_nav_includes(), read_showroom_content() (+18 more)

### Community 45 - "json"
Cohesion: 0.23
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

### Community 50 - "_expand_query_terms"
Cohesion: 0.17
Nodes (4): _build_expansion_map(), _expand_query_terms(), TestExpansionReadsVocabulary, TestMigrationCoverage

### Community 51 - "test_drivers.py"
Cohesion: 0.09
Nodes (15): ContentTypeDriver, _extract_duration_target(), get_driver(), get_drivers_for_types(), _init_drivers(), _register(), test_candidate_universal_fields(), test_candidate_with_type_data() (+7 more)

### Community 52 - "create_app"
Cohesion: 0.05
Nodes (20): create_app(), client(), client(), test_sync_osspa_endpoint_enqueues_a_job(), client(), test_auth_me_unauthenticated(), client(), app_no_auth() (+12 more)

### Community 53 - "test_analysis_identity.py"
Cohesion: 0.10
Nodes (21): Constraints, compute_content_hash(), donor_matches_content(), AnalysisSignature, signatures_match(), config(), donor_row(), test_config_follows_content_type_when_vocabulary_mode_differs() (+13 more)

### Community 54 - "Vocabulary"
Cohesion: 0.17
Nodes (5): _entries_to_dicts(), generate_vocabulary_yaml(), _header_comment(), _resolve_path(), TestGenerator

### Community 55 - "handlers.py"
Cohesion: 0.18
Nodes (19): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts(), handle_overlap() (+11 more)

### Community 56 - "test_osspa_csv.py"
Cohesion: 0.25
Nodes (16): asset_type_tokens(), parse_palist_csv(), scope_rows(), _csv_row(), test_asset_type_tokens_splits_and_uppercases(), test_derive_osspa_status(), test_normalize_row_builds_the_upsert_payload(), test_normalize_row_dedups_topics_from_solutions_and_verticals() (+8 more)

### Community 57 - "run_osspa_sync"
Cohesion: 0.33
Nodes (16): run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items(), test_missing_detail_page_marks_stale_and_skips() (+8 more)

### Community 58 - "loader.py"
Cohesion: 0.12
Nodes (11): _as_tuple(), _build_lookups(), _parse_entries(), _validate(), squash_key(), VocabEntry, Vocabulary, VocabularyError (+3 more)

### Community 59 - "Retirement System"
Cohesion: 0.08
Nodes (25): AgV Access Layer, Architecture, Authentication and Scope, Automatic Removal Eligibility, Cancellation and Recovery, Catalog Soft-Delete, Checking Merges, Code Organization (+17 more)

### Community 60 - "parse_analysis_response"
Cohesion: 0.18
Nodes (6): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), _strip_html(), _validate_url()

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

### Community 65 - "ResolvedShowroom"
Cohesion: 0.10
Nodes (21): 1. Storage, 2. Source resolution, 3. Scan pipeline branch, 4. Candidate selection and stale check, 5. API, 6. Frontend, 7. Coverage math, Design (+13 more)

### Community 66 - "test_field_source_sync.py"
Cohesion: 0.09
Nodes (16): test_field_source_endpoint(), test_field_source_filter(), test_field_source_filter_shared_and_cloud(), test_delete_field_source(), test_empty_upsert(), test_upsert_and_query_field_source(), test_upsert_updates_retired_at(), FakeSettings (+8 more)

### Community 67 - "reporting_sync.py"
Cohesion: 0.13
Nodes (11): _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs() (+3 more)

### Community 68 - "analyzer.py"
Cohesion: 0.07
Nodes (27): canonical_content(), compute_analysis_config(), donor_matches_commit(), _donor_signature(), fingerprint(), pre_clone_key(), _signature(), analysis_from_row() (+19 more)

### Community 69 - "admin.py"
Cohesion: 0.08
Nodes (36): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+28 more)

### Community 70 - "api.ts"
Cohesion: 0.07
Nodes (29): findButton(), findLink(), hasText(), hooks, FieldSourcePage(), formatDate(), repoDisplayName(), SortField (+21 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (10): ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+2 more)

### Community 72 - "Candidate"
Cohesion: 0.10
Nodes (11): HandsOnDriver, Candidate, format_triage_candidates(), _make_hands_on_candidate(), test_format_triage_candidates_architecture(), test_format_triage_candidates_with_type_data(), test_hands_on_display_config(), test_hands_on_format_for_rationale() (+3 more)

### Community 73 - "json"
Cohesion: 0.19
Nodes (12): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), log() (+4 more)

### Community 74 - "orchestrator.py"
Cohesion: 0.22
Nodes (10): build_scaffold(), compose_answer(), _strip_formatting(), _help_answer(), process_turn(), _scope_echo(), followup_chips(), test_answer_failure_degrades_to_scaffold() (+2 more)

### Community 75 - "_sync_nonprod_usage"
Cohesion: 0.19
Nodes (5): _build_nonprod_provisions_sql(), _nonprod_metrics(), _sync_nonprod_usage(), TestNonprodProvisionsSql, TestSyncNonprodUsage

### Community 76 - "routes/auth.py"
Cohesion: 0.19
Nodes (10): invalidate_api_key_cache(), submit_chat(), submit_query(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), revoke_api_key() (+2 more)

### Community 77 - "TestValidation"
Cohesion: 0.15
Nodes (5): clear_vocabulary_cache(), TestPathOverride, TestSquashKey, TestValidation, write_vocab()

### Community 78 - "Path"
Cohesion: 0.39
Nodes (4): clone_examples_repo(), file_commit_sha(), get_head_sha(), _run_git()

### Community 79 - "command"
Cohesion: 0.07
Nodes (29): command, check_card_families(), cli(), flag(), get_db(), infra_stats(), init_db(), note() (+21 more)

### Community 80 - "Description-Based Analysis for Items With No Showroom — Design"
Cohesion: 0.17
Nodes (10): Anti-goals, Approaches considered, Decisions (Nate, 2026-11-19), Deployment, Description-Based Analysis for Items With No Showroom — Design, Goals, Intent, Non-goals (+2 more)

### Community 81 - "test_test_content_exclusion.py"
Cohesion: 0.12
Nodes (17): resolve_showroom_source(), unresolved(), walk(), legacy_test_item(), node(), test_already_queued_or_forced_test_scan_is_excluded_without_artifact_changes(), test_cached_overlap_cannot_bypass_test_content_exclusion(), test_existing_test_vectors_never_enter_content_retrieval() (+9 more)

### Community 82 - "commit_for_ref"
Cohesion: 0.18
Nodes (6): commit_for_ref(), _is_github_throttle(), ls_remote_refs(), resolve(), _resolve_ref_from_lookup(), _run_git_with_retry()

### Community 83 - "test_nonprod.py"
Cohesion: 0.08
Nodes (13): get_workflow(), nonprod_dashboard(), _nonprod_retirement_metrics(), _retirement_metrics(), _sort_empty_last(), TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists (+5 more)

### Community 84 - "test_retirement_pr_status.py"
Cohesion: 0.09
Nodes (39): run_retirement_sweep(), test_database_schema_setup_does_not_move_cutoff(), _sweep_context(), test_cancel_audit_reports_jira_outcome(), close(), test_cancellation_does_not_mark_concurrently_retired_item(), test_manual_pr_creation_respects_cleanup_lock(), test_merged_revert_still_deletes_workflow() (+31 more)

### Community 85 - "Any"
Cohesion: 0.06
Nodes (7): _prefix_overlap(), _find_keyword_ties(), resolve_item(), test_audience_filter_applies_across_content_types(), test_list_catalog_items(), test_token_usage(), TestReviewBadgeUntouched

### Community 86 - "_make_request"
Cohesion: 0.21
Nodes (5): get_current_user(), _make_request(), TestApiKeyAuth, TestGetCurrentUser, TestProxySecretEnforcement

### Community 87 - "Platform and Technical Decision Point filters — design"
Cohesion: 0.22
Nodes (8): Anti-goals, Constraints, Goals, Left to the builder, Non-goals, Platform and Technical Decision Point filters — design, Rollout, Why

### Community 88 - "ArchitectureDriver"
Cohesion: 0.20
Nodes (8): ArchitectureDriver, _primary_asset_type(), _make_arch_candidate(), test_arch_format_for_rationale(), test_arch_post_triage_is_passthrough(), test_arch_serialize_no_performance(), test_arch_serialize_with_performance_no_crash(), test_arch_triage_guidance()

### Community 89 - "build_retirement_description"
Cohesion: 0.12
Nodes (15): AgV access layer (Python module), Credential strategy, Current RCARS Workflow Steps, Dev Testing Requirements, Documentation Updates Required, New API endpoints, New DB fields (retirement_workflow table), Phase 1 — `started` step triggers agv-retire notice PR (+7 more)

### Community 90 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.09
Nodes (22): 1. Content-Type Drivers, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers, Approach Decision (+14 more)

### Community 91 - "json"
Cohesion: 0.12
Nodes (10): _close_issue(), close_issue_done(), close_issue_wont_do(), _issue_is_closed(), test_already_closed_issue_needs_no_transition(), test_closure_requires_a_terminal_result(), test_new_closure_requires_the_requested_resolution(), test_required_closure_selects_resolution_and_verifies_result() (+2 more)

### Community 92 - "test_auth_middleware.py"
Cohesion: 0.18
Nodes (6): _fetch_group_members(), _user_in_groups(), _mock_async_client_get(), _mock_group_response(), TestApiKeyRoleCeiling, TestGroupLookup

### Community 93 - "test_showroom_scan.py"
Cohesion: 0.08
Nodes (47): InvalidShowroomRef, order_for_reuse(), showroom_reuse_key(), item_reuse_key(), reuse_lock_id(), scan_babylon_item(), run_stale_check(), run_analysis() (+39 more)

### Community 95 - "Showroom analysis isolation"
Cohesion: 0.17
Nodes (11): Acceptance, Content source resolution, Engineering choices to review with the plan, Incremental maintenance: unchanged means no work, Intent and approval, Rebuild and preservation, Recommendation behavior, Required boundaries (+3 more)

### Community 96 - "Scan Pipeline"
Cohesion: 0.33
Nodes (5): Dry run, review, then execute, Maintenance prerequisites, Rebuild and verify, Rebuild Babylon Showroom analysis, What changes

### Community 97 - "Request"
Cohesion: 0.24
Nodes (8): ChatRequest, get_query_result(), get_session(), list_sessions(), QueryRequest, select_recommendation(), SelectRequest, stream_query()

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (5): API Authentication Design, API Key Authentication (X-API-Key Header), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "build_retirement_description"
Cohesion: 0.14
Nodes (7): Open Questions / Risks, _base_name_from_content_id(), build_retirement_description(), test_basic_description(), test_no_notes(), test_no_replacement(), test_wiki_markup_format()

### Community 101 - "seed_chat_fixtures"
Cohesion: 0.13
Nodes (20): build_evidence_pack(), fake_embedding(), seed_chat_fixtures(), _settings(), test_depth_low_stops_before_triage(), test_scope_filter_restricts_pool(), test_empty_anchor_empty_pack(), test_pack_bounded_and_sorted() (+12 more)

### Community 102 - "test_vocabulary_admin.py"
Cohesion: 0.32
Nodes (3): clear_vocabulary_cache(), client(), TestRoleGating

### Community 103 - "rcars-login.sh"
Cohesion: 0.57
Nodes (6): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token(), urlencode()

### Community 104 - "CLAUDE.md — Project Instructions"
Cohesion: 0.18
Nodes (13): CLAUDE.md — Project Instructions, Ansible OpenShift Deployment, API Key Authentication via OAuth, RCARS Authentication Model, Performance Scoring System, RCARS CLI Entry Point (rcars command), RCARS FastAPI API, PostgreSQL with pgvector (+5 more)

### Community 105 - "AdocRead"
Cohesion: 0.25
Nodes (4): AdocRead, fake_analyze(), fake_repo(), settings()

### Community 106 - "test_db.py"
Cohesion: 0.09
Nodes (20): _do(), db_with_perf_data(), _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale(), test_filtered_catalog_default() (+12 more)

### Community 107 - "RCARS OCP Deployment Playbook"
Cohesion: 0.20
Nodes (10): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+2 more)

### Community 108 - "osspa_sync.py"
Cohesion: 0.18
Nodes (6): _as_bool(), content_id_for(), derive_osspa_status(), normalize_row(), _split_list(), test_content_id_format()

### Community 109 - "get"
Cohesion: 0.20
Nodes (7): _extract_base_name_from_content_id(), overlap_assessment_detail(), overlap_report(), performance_dashboard(), retirement_dashboard(), stream_job(), TestRetirementDashboardMetrics

### Community 111 - "mcp_query"
Cohesion: 0.27
Nodes (3): mcp_query(), TestMcpQueryOrdering, TestMcpPagination

### Community 112 - "workers/base.py"
Cohesion: 0.14
Nodes (14): Frontend Progress Display, What Stays Unchanged, create_sse_response(), JobProgressRelay, sse_stream(), translate_to_user_message(), test_relay_publishes_and_receives(), test_translate_complete() (+6 more)

### Community 113 - "chat/models.py"
Cohesion: 0.13
Nodes (19): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemChatArgs, ItemFactsArgs, OverlapArgs (+11 more)

### Community 114 - "content_entities Table"
Cohesion: 0.25
Nodes (7): babylon_items Table, content_entities Table, performance_channels Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow

### Community 115 - "OsspaSyncError"
Cohesion: 0.33
Nodes (3): fetch_palist_csv(), OsspaSyncError, _boom()

### Community 118 - ".reset_babylon_scan_artifacts"
Cohesion: 0.32
Nodes (3): main(), test_execute_requires_scans_paused_confirmation(), test_script_rejects_selection_with_no_showroom_items()

### Community 120 - "settings.py"
Cohesion: 0.11
Nodes (10): WorkerContext, run_chat_turn(), on_progress(), run_recommendation(), recommend_startup(), RecommendWorkerSettings, _redis_settings_from_url(), scan_startup() (+2 more)

### Community 122 - "test_product_terms.py"
Cohesion: 0.13
Nodes (7): build_embedding_text(), build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal(), clear_vocabulary_cache(), TestBuildEmbeddingText, TestOldFileGone

### Community 123 - "vector_search.py"
Cohesion: 0.11
Nodes (10): exclusion_set_for(), _collapse_families(), _embedding_owner_id(), _is_excluded(), _neighbor_rows(), _owner_scope_ids(), _reference_context(), _resolve_ci_references() (+2 more)

### Community 124 - "test_orphan_cleanup.py"
Cohesion: 0.44
Nodes (7): _reconcile_queued_orphans(), _mock_db(), test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed(), test_orphaned_recommend_job_is_failed(), test_recommend_job_checked_against_recommend_queue()

### Community 125 - "retirement_cleanup.py"
Cohesion: 0.10
Nodes (21): _base_name(), cancel_retirement(), CleanupBusy, CleanupError, _close_jira(), _close_open_pr(), complete_retirement(), _ensure_cancellable() (+13 more)

### Community 127 - "_generate_key"
Cohesion: 0.17
Nodes (6): _generate_key(), TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 129 - "vocabulary.yaml"
Cohesion: 0.14
Nodes (13): difficulty, aliases, name, platforms, aliases, name, products, aliases (+5 more)

### Community 130 - "pre_tasks"
Cohesion: 0.15
Nodes (13): msg, babylon_kubeconfig_content, path, kubeconfig, pre_tasks, ansible.builtin.fail, ansible.builtin.set_fact, ansible.builtin.stat (+5 more)

### Community 131 - "test_llm_routing.py"
Cohesion: 0.21
Nodes (10): _call_litemaas(), FakeCompletions, reset_temperature_cache(), _settings(), test_logs_model_and_usage_on_success(), test_logs_model_on_failure(), test_reraises_unrelated_errors(), test_retries_without_temperature_when_model_rejects_it() (+2 more)

### Community 132 - "chat_sessions.py"
Cohesion: 0.17
Nodes (9): get_session_context(), log_chat_turn(), next_turn_index(), session_owner_ok(), test_chat_append_checks_ownership(), _log(), test_context_builder_shape_and_window(), test_ownership() (+1 more)

### Community 135 - "test_status_visibility.py"
Cohesion: 0.09
Nodes (23): _do(), test_content_path(), test_retire_missing_babylon_ignores_other_sources(), _arch(), _seed_nonprod(), test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_maps_retirement_to_sibling_stages() (+15 more)

### Community 136 - "middleware/auth.py"
Cohesion: 0.27
Nodes (9): Key Patterns, _check_api_key_role_ceiling(), _get_cached_role_assignments(), _log_auth_decision(), require_admin(), require_auth(), require_curator(), _validate_api_key_cached() (+1 more)

### Community 138 - "RCARS — Agent Instructions"
Cohesion: 0.17
Nodes (11): Architecture, Backlog and Docs, Build and Deploy, CLI, Database, Git Workflow, graphify, RCARS — Agent Instructions (+3 more)

### Community 139 - "services/catalog.py"
Cohesion: 0.06
Nodes (22): Decisions, _apply_component_inheritance(), CatalogFamilies, CatalogReader, collect(), load(), _collect_bases(), _content_fields() (+14 more)

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

### Community 159 - "group"
Cohesion: 0.15
Nodes (7): group, infra_group(), osspa_group(), reporting_db_group(), retirement_group(), vocab_group(), workload_group()

### Community 160 - "Python Dependency Manifest (requirements.lock)"
Cohesion: 0.22
Nodes (9): Anthropic SDK Dependency (v0.120.0), arq Dependency (v0.28.0), Python Dependency Manifest (requirements.lock), FastAPI Dependency (v0.140.7), OpenAI SDK Dependency (v2.49.0), psycopg Dependency (v3.3.4), Pydantic Dependency (v2.13.4), Redis Client Dependency (v5.3.1) (+1 more)

### Community 161 - "app.py"
Cohesion: 0.12
Nodes (3): lifespan(), _get_user_key(), RequestLoggingMiddleware

### Community 162 - "patch"
Cohesion: 0.36
Nodes (4): _validate_sa_token(), _mock_async_client(), _mock_token_review_response(), TestValidateSaToken

### Community 163 - "deploy.yml"
Cohesion: 0.29
Nodes (6): collections, connection, gather_facts, hosts, name, vars_files

### Community 169 - "tasks"
Cohesion: 0.29
Nodes (7): apply, file, tags, tasks, ansible.builtin.include_tasks, name, tags

### Community 172 - "extract_base_name"
Cohesion: 0.15
Nodes (4): extract_base_name(), _window_start(), TestExtractBaseName, TestWindowStart

### Community 173 - "pytest"
Cohesion: 0.05
Nodes (12): retirement_label(), test_nonprod_rows_have_labels(), test_performance_rows_have_labels(), test_retirement_rows_have_labels(), test_rows_without_labels_get_empty_lists(), TestListApiKeys, TestExpiredApiKey, TestRevokedApiKey (+4 more)

### Community 174 - "recommendations.py"
Cohesion: 0.21
Nodes (4): get_recommendations(), RecommendationRequest, _run_low(), _run_medium()

### Community 178 - "RouterOutput"
Cohesion: 0.19
Nodes (19): RouterOutput, Scope, _guess_clarification(), _parse_catalog_url(), pattern_check(), resolve_and_verify(), _result_turns(), _turn_chips() (+11 more)

### Community 180 - "test_cancel_preserves_tracking_on_github_failure"
Cohesion: 0.17
Nodes (5): test_cancel_does_not_recreate_workflow_reconciled_during_jira_cleanup(), test_cancel_preserves_tracking_on_github_failure(), test_cancel_stops_removal_before_creating_revert(), close_jira(), state()

### Community 181 - "_jira_request"
Cohesion: 0.20
Nodes (5): _fetch_oauth_token(), _get_access_token(), _jira_request(), _oauth_config(), _mcp_call()

### Community 182 - "content_similarity Table"
Cohesion: 0.67
Nodes (3): Evidence Pack, content_similarity Table, overlap_candidates Table

### Community 183 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (8): _noop(), _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 184 - "ignored_terms"
Cohesion: 0.33
Nodes (6): ignored_terms, difficulty, platforms, products, solutions, verticals

### Community 185 - "test_chat_live.py"
Cohesion: 0.36
Nodes (4): _noop(), _settings(), test_live_item_facts_turn(), test_live_out_of_scope()

### Community 187 - "test_llm_provider_status.py"
Cohesion: 0.28
Nodes (4): _make_client(), no_litemaas_fetch(), test_lists_model_for_every_llm_use(), test_litemaas_active_with_models()

### Community 189 - "test_osspa_pipeline_runs_even_when_babylon_fails"
Cohesion: 0.28
Nodes (6): test_nightly_pipeline_runs_osspa_after_babylon(), _babylon(), _osspa(), test_osspa_pipeline_respects_the_enable_flag(), test_osspa_pipeline_runs_even_when_babylon_fails(), test_run_osspa_sync_job_completes()

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

### Community 218 - "Content Owner Model for Virtual CIs — Design"
Cohesion: 0.14
Nodes (13): Advisor, Browse, Content Owner Model for Virtual CIs — Design, Curator edits, Model, Overlap, Problem, Pure stub (+5 more)

### Community 228 - "on_progress"
Cohesion: 0.67
Nodes (3): _relay(), emit(), on_progress()

## Knowledge Gaps
- **75 isolated node(s):** `rcars`, `rcars`, `RCARS_DATABASE_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1476 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **82 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Advisor v2 — Content-Type Drivers` connect `Advisor v2 — Content-Type Drivers` to `workers/base.py`, `BrowsePage.tsx`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `Database` (e.g. with `lifespan()` and `build_evidence_pack()`) actually correct?**
  _`Database` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `RCARS_DATABASE_URL` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_FakeResponse` be split into smaller, more focused modules?**
  _Cohesion score 0.10344827586206896 - nodes in this community are weakly interconnected._
- **Why does `Summary` connect `BrowsePage.tsx` to `Advisor v2 — Content-Type Drivers`?**
  _High betweenness centrality (0.171) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `Settings` (e.g. with `lifespan()` and `get_current_user()`) actually correct?**
  _`Settings` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Should `Database` be split into smaller, more focused modules?**
  _Cohesion score 0.02397003745318352 - nodes in this community are weakly interconnected._