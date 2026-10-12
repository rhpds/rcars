# Graph Report - rcars-advisory  (2026-10-12)

## Corpus Check
- 276 files · ~489,826 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2801 nodes · 5828 edges · 189 communities (127 shown, 62 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 313 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0f3888c7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_auth_middleware.py
- Database
- registry.ts
- Portfolio Architecture Ingest Design Spec
- command
- devDependencies
- services/catalog.py
- analysis.py
- routes/catalog.py
- admin.py
- analyzer.py
- Infrastructure Catalog
- BrowsePage.tsx
- test_overlap_assessment.py
- derive_status
- Generalized Content Model Design
- Any
- pipeline.py
- ops.py
- migrate_to_content_model.py
- create_app
- test_db.py
- router.py
- test_osspa_adoc.py
- workload_scanner.py
- Settings
- settings.py
- ContentTypeDriver
- schemas.py
- handlers.py
- App.tsx
- routes/auth.py
- seed_chat_fixtures
- db/__init__.py
- JobProgressRelay
- test_chat_handlers.py
- Controlled Vocabulary
- load_vocabulary
- render_vocabulary_block
- _generate_key
- compilerOptions
- advisor.py
- test_nonprod.py
- test_vocabulary_db.py
- config.py
- test_osspa_csv.py
- reporting_sync.py
- PerformancePage.tsx
- normalize_analysis
- dev-services.sh
- test_product_terms.py
- Advisor v2 — Content-Type Drivers
- test_auth_security.py
- test_chat_sessions_db.py
- generate_vocabulary_yaml
- test_drivers.py
- osspa_sync.py
- run_osspa_sync
- vocabulary/__init__.py
- sync_opl_vocabulary.py
- parse_analysis_response
- analyze_architecture_item
- test_catalog_osspa_routes.py
- cli.py
- scan
- test_osspa_db.py
- RcarsMasthead.tsx
- test_reporting.py
- ContentAnalysisPage.tsx
- AdvisorPage.tsx
- api.ts
- ECA Production Redesign Spec
- group
- RouterOutput
- test_auth_routes.py
- Reporting MCP Data Sync
- test_status_visibility.py
- TestValidation
- SyncPage.tsx
- recommendations.py
- extract_base_name
- build_analysis_prompt
- _reconcile_queued_orphans
- TestMcpPagination
- What You Must Do When Invoked
- Candidate
- database.py
- File Map
- _build_windowed_metrics
- _window_start
- test_api_infrastructure.py
- test_infrastructure.py
- AdocRead
- HandsOnDriver
- test_vocabulary.py
- test_vocabulary_admin.py
- RetirementPage.tsx
- rcars-login.py
- Browse Page Redesign Plan
- API Authentication Design
- RCARS — Project Instructions
- test_workers.py
- _extrapolate_count
- rcars-login.sh
- app.py
- test_field_source_sync.py
- API Key Authentication
- setup_logging
- test_auth_token.py
- Jira Epic RHDPCD-25 (RCARS Backlog)
- Rec Card Duration and Best Fit Spec
- Controlled Vocabulary Design
- .retire_missing_babylon
- .__init__
- graphify reference: extra exports and benchmark
- db
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- .advisory_lock
- .delete_infrastructure_absent
- .get_channel_metrics_map
- .get_queued_job_ids
- .list_nonprod_items
- .prune_expired_api_keys
- .prune_old_jobs
- .record_unknown_term
- .replace_embeddings
- .retire_missing_osspa
- .revoke_user_cli_keys
- .upsert_nonprod_usage
- db
- db
- db
- db
- db
- docker-entrypoint.sh
- Webhook Configuration Task
- Global Constraints
- OpenShift OAuth Proxy (Red Hat SSO)
- Follow-up Chips
- Item Facts Intent
- API Reference
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
- Plan 1: Foundation and Catalog Reader
- Plan 2: Analysis and Recommendations
- Plan 3c: OpenShift Deployment
- Plan: Async Advisor Query
- Plan: Recommender Redesign (Three-Phase Pipeline)
- Plan: Token Usage Tracking
- Plan: Advisor List Persistence and Feedback
- Plan: Scan Failures and Catalog Visibility
- Plan: Rearchitecture to Three-Tier
- LLM Overlap Assessment Plan
- LLM Overlap Assessment Design
- rcars
- rcars
- resolve_refs_to_shas
- Match Event Prompt Template
- BlockErrorBoundary
- graphify reference: query, path, explain
- Field Source Content
- graphify reference: add a URL and watch a folder
- Python Requirements Entry Point
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- extraction-spec.md
- .delete_field_source_provisions
- .get_field_source_summary
- .list_retirement_items
- .upsert_field_source_provisions

## God Nodes (most connected - your core abstractions)
1. `Database` - 265 edges
2. `Settings` - 165 edges
3. `load_vocabulary()` - 68 edges
4. `Candidate` - 42 edges
5. `run_osspa_sync()` - 31 edges
6. `normalize_analysis()` - 30 edges
7. `call_llm()` - 28 edges
8. `parse_analysis_response()` - 27 edges
9. `JobProgressRelay` - 26 edges
10. `RouterOutput` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Content Hash Change Detection` --semantically_similar_to--> `Soft-Delete Pattern for Retired Items`  [INFERRED] [semantically similar]
  docs/architecture/portfolio-architectures.md → CLAUDE.md
- `Management RBAC Bootstrap Task` --implements--> `RCARS Authentication Model`  [INFERRED]
  ansible/tasks/mgmt-rbac.yml → docs/architecture/system-design.md
- `RCARS README` --references--> `RCARS OCP Deployment Playbook`  [EXTRACTED]
  README.md → ansible/deploy.yml
- `Frontend HTML Entry Point` --conceptually_related_to--> `PatternFly 6 Migration Design`  [INFERRED]
  src/frontend/index.html → docs/superpowers/specs/2026-06-29-patternfly6-migration-design.md
- `pgvector Container Image Build Guide` --conceptually_related_to--> `Unified Embeddings Design (MAX Similarity Scoring)`  [INFERRED]
  tools/build-pgvector.md → docs/superpowers/specs/2026-07-20-generalized-content-model-design.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **OSSPA Ingest Stack — CSV + Clone + Upsert + Analyze + Embed** — claude_md_osspa_sync_pipeline, claude_md_palist_csv, claude_md_osspa_gitlab_repos, claude_md_portfolio_architectures_table, claude_md_architecture_analysis_table, claude_md_content_entities_table, claude_md_llm_architecture_analysis, claude_md_embedding_model_nomic [EXTRACTED 0.95]
- **RCARS Core Four Deployments on OpenShift** — claude_md_rcars_react_spa, claude_md_rcars_fastapi_api, claude_md_rcars_scan_worker, claude_md_rcars_recommend_worker, claude_md_rcars_postgresql, claude_md_rcars_redis [EXTRACTED 1.00]
- **Content Visibility Gate — Status + Vector Search + Browse** — claude_md_content_entities_status, claude_md_vector_similarity_search, claude_md_browse_integration, claude_md_content_entities_table [INFERRED 0.85]
- **Three-Phase Recommendation Pipeline** — docs_architecture_recommendation_engine_vector_search, docs_architecture_recommendation_engine_haiku_triage, docs_architecture_recommendation_engine_sonnet_rationale [EXTRACTED 1.00]
- **Multi-Intent Chat System** — docs_architecture_advisor_chat_router, docs_architecture_advisor_chat_intent_recommend, docs_architecture_advisor_chat_intent_overlap, docs_architecture_advisor_chat_intent_performance, docs_architecture_advisor_chat_intent_infrastructure, docs_architecture_advisor_chat_intent_item_facts [EXTRACTED 1.00]
- **Content Analysis Pipeline (Vocabulary + Showroom Analysis + Overlap Assessment)** — src_api_rcars_data_vocabulary_controlled_vocabulary, src_api_rcars_prompts_analyze_showroom_analysis_prompt, src_api_rcars_prompts_overlap_assessment_overlap_prompt, src_api_rcars_prompts_analyze_showroom_learning_objectives [EXTRACTED 0.95]
- **RCARS Taxonomy System (Products, Solutions, Verticals, Platforms, Difficulty)** — src_api_rcars_data_vocabulary_products_taxonomy, src_api_rcars_data_vocabulary_solutions_taxonomy, src_api_rcars_data_vocabulary_verticals_taxonomy, src_api_rcars_data_vocabulary_platforms_taxonomy, src_api_rcars_data_vocabulary_difficulty_levels [EXTRACTED 1.00]
- **LLM Infrastructure (Anthropic + OpenAI SDKs + Prompt Templates)** — src_api_requirements_lock_anthropic, src_api_requirements_lock_openai, src_api_rcars_prompts_analyze_showroom_analysis_prompt, src_api_rcars_prompts_overlap_assessment_overlap_prompt [INFERRED 0.85]
- **Ansible Deployment Pipeline** — ansible_deploy_playbook, ansible_tasks_apply_infra, ansible_tasks_apply_manifests, ansible_tasks_build_api, ansible_tasks_build_frontend, ansible_tasks_smoke_test, ansible_tasks_namespace, ansible_vars_common [EXTRACTED 1.00]
- **System Evolution from Monolith to Multi-Tier** — docs_superpowers_specs_2026-04-07-eca-production-redesign-design, docs_superpowers_specs_2026-04-08-rcars-plan3a-web-ui-design, docs_superpowers_specs_2026-04-25-rearchitecture-api-design, concept_rearchitecture [EXTRACTED 0.95]
- **Authentication and Authorization Evolution** — concept_api_key_auth, concept_openshift_group_auth, docs_superpowers_plans_2026-07-03-api-authentication, docs_superpowers_plans_2026-08-05-openshift-group-auth [INFERRED 0.85]
- **Performance Analysis Feature Stack** — concept_reporting_mcp_sync, concept_performance_scoring, concept_retirement_workflow, docs_superpowers_plans_2026-08-04-performance-page [EXTRACTED 0.95]
- **Recommendation Pipeline LLM Prompts** — src_api_rcars_prompts_triage, src_api_rcars_prompts_rationale, src_api_rcars_prompts_rationale_single, src_api_rcars_prompts_rationale_synthesis [INFERRED 0.95]
- **Generalized Content Model Core Tables** — docs_superpowers_specs_2026_07_20_generalized_content_model_design_content_entities, docs_superpowers_specs_2026_07_20_generalized_content_model_design_babylon_items, docs_superpowers_specs_2026_07_20_generalized_content_model_design_embeddings, docs_superpowers_specs_2026_07_20_generalized_content_model_design_performance_channels [EXTRACTED 1.00]
- **Authentication and Access Control System** — docs_superpowers_specs_2026_07_03_api_authentication_design_api_keys, docs_superpowers_specs_2026_07_03_api_authentication_design_oauth_login, docs_superpowers_specs_2026_07_03_api_authentication_design_proxy_verification, docs_superpowers_specs_2026_08_05_role_assignments_design_role_assignments_table [INFERRED 0.95]

## Communities (189 total, 62 thin omitted)

### Community 0 - "test_auth_middleware.py"
Cohesion: 0.05
Nodes (43): dict, FastAPI, _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), _log_auth_decision(), _parse_sa_allowlist() (+35 more)

### Community 2 - "registry.ts"
Cohesion: 0.13
Nodes (23): InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps (+15 more)

### Community 3 - "Portfolio Architecture Ingest Design Spec"
Cohesion: 0.07
Nodes (58): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+50 more)

### Community 4 - "command"
Cohesion: 0.13
Nodes (25): argument, command, flag(), get_db(), infra_stats(), note(), overlap_candidates_cmd(), override_url() (+17 more)

### Community 5 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-core, @patternfly/react-icons, @patternfly/react-table (+40 more)

### Community 6 - "services/catalog.py"
Cohesion: 0.10
Nodes (29): _apply_component_inheritance(), CatalogReader, _collect_bases(), component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata() (+21 more)

### Community 7 - "analysis.py"
Cohesion: 0.07
Nodes (79): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_stale(), _extract_base_name_from_content_id(), field_source_report() (+71 more)

### Community 8 - "routes/catalog.py"
Cohesion: 0.14
Nodes (41): field_validator, add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis() (+33 more)

### Community 9 - "admin.py"
Cohesion: 0.11
Nodes (41): invalidate_role_assignments_cache(), add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs() (+33 more)

### Community 10 - "analyzer.py"
Cohesion: 0.13
Nodes (25): analyze_showroom(), build_infrastructure_embedding_text(), build_module_embedding_text(), check_showroom_stale(), filter_boilerplate_files(), _get_embedding_client(), get_repo_head(), hash_showroom_content() (+17 more)

### Community 11 - "Infrastructure Catalog"
Cohesion: 0.06
Nodes (38): CLI Admin Guide, Worker Management, Advisor Chat System, Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent (+30 more)

### Community 12 - "BrowsePage.tsx"
Cohesion: 0.09
Nodes (26): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+18 more)

### Community 13 - "test_overlap_assessment.py"
Cohesion: 0.09
Nodes (34): assess_overlap(), _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), _load_analysis_pair(), Any, LLM-based overlap assessment for content similarity pairs., Assess overlap between two content items via LLM. Returns (assessment_dict,… (+26 more)

### Community 14 - "derive_status"
Cohesion: 0.07
Nodes (20): derive_status(), Retirement workflow business logic., Derive the workflow status from the highest completed step., Tests for retirement workflow business logic (derive_status)., Test derive_status with various step combinations., Validate STEP_ORDER constant structure., Retired should be first (highest priority), reviewed last., With no step timestamps, status defaults to 'reviewed'. (+12 more)

### Community 15 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (34): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, Retirement Scoring Formula (0-100, Higher = Stronger Candidate), PatternFly 6 Migration Design, Navigation Restructure (Flattened Nav with Role-Gated Sections), RCARS Theme Architecture (Light/Dark Mode), Retirement Workflow Actions Design (+26 more)

### Community 16 - "Any"
Cohesion: 0.06
Nodes (7): Any, Case-insensitive exact match on display_name., Queue rows, ranked by occurrences descending. status=None returns all., Record an admin decision. Staged only — nothing about analysis changes until a…, Get analysis for any content type — routes to the right table., Upsert a Babylon catalog item across content_entities + babylon_items in one…, Upsert one OSSPA row across content_entities + portfolio_architectures. Also…

### Community 17 - "pipeline.py"
Cohesion: 0.09
Nodes (33): generate_embedding(), Generate a 768-dim embedding via the vLLM embedding server. Nomic requires task…, All content types with registered drivers., registered_content_types(), QueryState, Data models for the recommendation pipeline., State of a recommendation query at a pipeline phase boundary., extract_urls() (+25 more)

### Community 18 - "ops.py"
Cohesion: 0.12
Nodes (27): Future, batch_assess_overlaps(), Assess all unassessed or stale overlap candidates. Returns summary:…, Pull field source content provision data from MCP, replace local table. Returns…, run_field_source_sync(), build_sandbox_summary(), Sandbox summary generation from infrastructure metadata and workload…, Assemble a sandbox summary from infrastructure metadata. workload_products:… (+19 more)

### Community 19 - "migrate_to_content_model.py"
Cohesion: 0.16
Nodes (30): Connection, cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists() (+22 more)

### Community 20 - "create_app"
Cohesion: 0.17
Nodes (8): create_app(), client(), fixture, test_auth_me_unauthenticated(), client(), non_admin_client(), fixture, Tests for POST /advisor/chat endpoint.

### Community 21 - "test_db.py"
Cohesion: 0.09
Nodes (15): db(), db_with_perf_data(), fixture, Seed test data for filtered catalog queries., Seed performance data for testing., _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider() (+7 more)

### Community 22 - "router.py"
Cohesion: 0.08
Nodes (34): llm_eval, _prefix_overlap(), Count keyword matches allowing prefix matching for words >= min_prefix chars., build_router_prompt(), _expand_vocab_aliases(), _extract_json(), _find_keyword_ties(), _parse_catalog_url() (+26 more)

### Community 23 - "test_osspa_adoc.py"
Cohesion: 0.12
Nodes (29): compute_content_hash(), is_tracked_at_head(), Safe join with canonical containment. None means reject the row., True only if the file exists in the HEAD tree — not merely on disk., Drop ++++ passthrough blocks and HTML/Arcade comments — no text signal., Read one DetailPage. None means skip the row (unsafe, missing, untracked)., SHA-256 of the FULL adoc body plus the CSV fields that feed the prompt., read_detail_adoc() (+21 more)

### Community 24 - "workload_scanner.py"
Cohesion: 0.09
Nodes (34): clone_showroom(), ls_remote_sha(), Get the current SHA for a ref without cloning. Returns None on failure., Shallow clone a Showroom repo. Returns clone path or None on failure., analyze_config(), analyze_role(), discover_roles(), _follow_task_includes() (+26 more)

### Community 25 - "Settings"
Cohesion: 0.10
Nodes (20): BaseSettings, _parse_csv(), Settings, migrate(), One-time migration: export token_usage from old schema, create new schema,…, test_admin_check(), test_chat_intent_roles_invalid_role_rejected(), test_chat_intent_roles_parse() (+12 more)

### Community 26 - "settings.py"
Cohesion: 0.12
Nodes (19): RedisSettings, fetch_litemaas_models(), Query LiteMaaS /v1/models endpoint once and cache the result., Base worker context and progress helpers., WorkerContext, Chat turn worker task — runs on the recommend queue., run_chat_turn(), Recommendation worker task. (+11 more)

### Community 27 - "ContentTypeDriver"
Cohesion: 0.09
Nodes (17): ABC, Driver for portfolio architecture content., ContentTypeDriver, Any, Abstract base class for content-type drivers., Content type strings this driver handles., Short key for SSE category labels and frontend tab grouping., Fetch full analysis data for the rationale prompt. (+9 more)

### Community 28 - "schemas.py"
Cohesion: 0.12
Nodes (28): health(), get, Request, readiness(), AuthMeResponse, CatalogItemWorkload, CatalogListResponse, ErrorDetail (+20 more)

### Community 29 - "handlers.py"
Cohesion: 0.15
Nodes (36): get_item_workloads(), get_performance_scores(), Chat-session persistence and context building. Follows the db/similarity.py…, _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_chat(), handle_item_facts() (+28 more)

### Community 30 - "App.tsx"
Cohesion: 0.11
Nodes (22): App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), useAuthProvider(), AdminQueriesPage(), AdminRolesPage() (+14 more)

### Community 31 - "routes/auth.py"
Cohesion: 0.19
Nodes (21): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), delete, get (+13 more)

### Community 32 - "seed_chat_fixtures"
Cohesion: 0.12
Nodes (26): integration, build_evidence_pack(), Evidence pack: v1 graph expansion — one hop, code-driven, bounded. The budget…, fake_embedding(), Seeded fixture catalog for chat tests (also a foundation for the broader…, Deterministic 768-dim unit vector from the text hash. Signature is monkeypatch-…, seed_chat_fixtures(), _settings() (+18 more)

### Community 33 - "db/__init__.py"
Cohesion: 0.14
Nodes (24): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), ConnectionPool, Deterministic overlap candidate generation via structured matching., Aggregate stats by verdict., Item-centric overlap report grouped by verdict. (+16 more)

### Community 34 - "JobProgressRelay"
Cohesion: 0.16
Nodes (17): Redis, create_sse_response(), JobProgressRelay, Redis pub/sub relay and SSE streaming for job progress., Subscribe to job progress. Yields message dicts, or None as keepalive., sse_stream(), translate_to_user_message(), asyncio (+9 more)

### Community 35 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (10): _noop(), Verify handler returns notice when no embeddings match., Verify handler uses embedding search, not list_infrastructure., _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler() (+2 more)

### Community 36 - "Controlled Vocabulary"
Cohesion: 0.10
Nodes (24): Action Verbs Validation Rules, Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy (+16 more)

### Community 37 - "load_vocabulary"
Cohesion: 0.15
Nodes (9): load_vocabulary(), Load, validate, and cache the controlled vocabulary for this process., Snap one value to its canonical form. Returns (result, matched). On a miss the…, snap_term(), Punctuation and spacing differences resolve without a human., The spec's worked examples, wherever on the ladder they land., search_terms widen query expansion only — the normalizer ignores them., TestLoadPackagedDefault (+1 more)

### Community 38 - "render_vocabulary_block"
Cohesion: 0.26
Nodes (5): Build the injected block for a given content_entities.content_type., render_vocabulary_block(), Only products and verb hints go into the prompt., The block is spliced into a template that cannot use str.format()., TestRenderVocabularyBlock

### Community 39 - "_generate_key"
Cohesion: 0.12
Nodes (11): db(), _generate_key(), fixture, Tests for API key database CRUD operations., Ephemeral test database — uses RCARS_DATABASE_URL from env (rcars_test)., Generate a raw key, its hash, and its prefix., TestCreateApiKey, TestGetApiKeyByHash (+3 more)

### Community 40 - "compilerOptions"
Cohesion: 0.09
Nodes (22): DOM, DOM.Iterable, ES2020, src, compilerOptions, allowImportingTsExtensions, isolatedModules, jsx (+14 more)

### Community 41 - "advisor.py"
Cohesion: 0.17
Nodes (25): _get_user_key(), Request, Per-user rate limiting via slowapi + Redis., _advisor_limit(), ChatRequest, get_query_result(), get_session(), list_sessions() (+17 more)

### Community 42 - "test_nonprod.py"
Cohesion: 0.09
Nodes (10): Return {base_name: content_id} for items with no active prod-stage variant., Tests for get_nonprod_base_names — requires live DB with test data., Verify the nonprod routes exist on the analysis router., TestGetNonprodBaseNames, TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema (+2 more)

### Community 43 - "test_vocabulary_db.py"
Cohesion: 0.09
Nodes (9): db(), fixture, Tests for the vocabulary_unknown_terms queue. Requires a live PostgreSQL., Vocabulary work never sets enrichment_review_needed or review_reasons., TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched (+1 more)

### Community 44 - "config.py"
Cohesion: 0.19
Nodes (18): _call_anthropic(), _call_litemaas(), call_llm(), LLMResult, Unified LLM call with automatic provider routing. LiteMaaS preferred if…, build_scaffold(), compose_answer(), Deterministic scaffold + narrow narrative call. Worst case: mediocre prose next… (+10 more)

### Community 45 - "test_osspa_csv.py"
Cohesion: 0.18
Nodes (26): _as_bool(), asset_type_tokens(), content_id_for(), derive_osspa_status(), normalize_row(), parse_palist_csv(), Apply the ingestion gate. Keep a row when it carries at least one of PA/VP/SP,…, Map the raw CSV booleans into Babylon's status vocabulary. (+18 more)

### Community 46 - "reporting_sync.py"
Cohesion: 0.11
Nodes (27): _build_closed_sql(), _build_cost_sql(), _build_field_source_sql(), _build_nonprod_provisions_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql() (+19 more)

### Community 47 - "PerformancePage.tsx"
Cohesion: 0.15
Nodes (19): fmt(), fmtRoi(), num(), scoreBg(), ScoreBreakdownPopover(), scoreColor(), stageBadgeClass, WorkflowDrawer() (+11 more)

### Community 48 - "normalize_analysis"
Cohesion: 0.12
Nodes (13): _noise_variants(), normalize_analysis(), Any, Post-analysis normalization — deterministic, runs once after parse. Nothing…, Snap aliases to canonical forms and dedup topics, before write. Pure when db is…, Upsert one row per distinct term. Never touches the item's review flags., Rung 3 candidates: strip known noise, then retry rungs 1-2 on each., _record_unknowns() (+5 more)

### Community 49 - "dev-services.sh"
Cohesion: 0.20
Nodes (17): db_pull(), frontend_only(), init_db(), RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 50 - "test_product_terms.py"
Cohesion: 0.08
Nodes (18): build_embedding_text(), Build text for CI-level embedding from analysis results., _build_expansion_map(), _expand_query_terms(), Invert the vocabulary's product aliases into term -> canonical name., Expand product names, acronyms, and synonyms for better embedding match., clear_vocabulary_cache(), fixture (+10 more)

### Community 51 - "Advisor v2 — Content-Type Drivers"
Cohesion: 0.07
Nodes (27): 1. Content-Type Drivers, 2. Orchestrator and Pipeline, 3. Candidate Model, 4. SSE Streaming, 5. Frontend Card Rendering, 6. Unified Serialization, Adding a New Content Type, Advisor v2 — Content-Type Drivers (+19 more)

### Community 52 - "test_auth_security.py"
Cohesion: 0.11
Nodes (11): app_no_auth(), client(), fixture, parametrize, Security test suite for RCARS API authentication. Validates that all auth…, App with NO dev_user — all auth enforced., TestExpiredApiKey, TestRevokedApiKey (+3 more)

### Community 53 - "test_chat_sessions_db.py"
Cohesion: 0.16
Nodes (13): get_session_context(), log_chat_turn(), next_turn_index(), Any, The router's view: last <=max_turns turns, fixed shape, no prose., session_owner_ok(), test_chat_append_checks_ownership(), db() (+5 more)

### Community 54 - "generate_vocabulary_yaml"
Cohesion: 0.17
Nodes (11): _entries_to_dicts(), generate_vocabulary_yaml(), _header_comment(), Any, Emit a merged vocabulary.yaml — current file plus staged admin decisions.…, Preserve the active vocabulary file's leading comment block., Merge staged decisions into the loaded vocabulary and serialize. aliased → term…, Path (+3 more)

### Community 55 - "test_drivers.py"
Cohesion: 0.10
Nodes (29): ArchitectureDriver, get_driver(), get_drivers_for_types(), Get the driver for a content type. Raises KeyError if unknown., Group content types by driver. Returns {category_key: driver}., format_triage_candidates(), Format candidates compactly for the triage prompt., _make_arch_candidate() (+21 more)

### Community 56 - "osspa_sync.py"
Cohesion: 0.18
Nodes (16): clone_examples_repo(), expand_includes(), fetch_palist_csv(), file_commit_sha(), get_head_sha(), OsspaSyncError, CompletedProcess, Exception (+8 more)

### Community 57 - "run_osspa_sync"
Cohesion: 0.37
Nodes (17): Full OSSPA sync. Synchronous by design — the worker wraps it in one…, run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items() (+9 more)

### Community 58 - "vocabulary/__init__.py"
Cohesion: 0.13
Nodes (23): Controlled vocabulary — one list, two consumers (analysis + query expansion)., _as_tuple(), _build_lookups(), _parse_entries(), Any, Vocabulary loading, path resolution, and fail-fast validation. Cached once per…, Build exact (casefold) and squash lookups, validating collisions. Aliases may…, _validate() (+15 more)

### Community 59 - "sync_opl_vocabulary.py"
Cohesion: 0.22
Nodes (17): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), Any (+9 more)

### Community 60 - "parse_analysis_response"
Cohesion: 0.11
Nodes (26): parse_analysis_response(), Parse Sonnet's JSON response, handling markdown fences., _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), Any (+18 more)

### Community 61 - "analyze_architecture_item"
Cohesion: 0.15
Nodes (19): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), Any, Split the template into (system_prompt, user_message)., One embedding per item — summary plus all extracted signal fields., LLM analysis → vocabulary normalization → analysis row → card → embedding., Comma-split a CSV cell into a deduped, order-preserving list. (+11 more)

### Community 62 - "test_catalog_osspa_routes.py"
Cohesion: 0.16
Nodes (9): client(), db(), fixture, _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures() (+1 more)

### Community 63 - "cli.py"
Cohesion: 0.12
Nodes (26): option, pass_context, cli(), init_db(), osspa_sync_cmd(), _print(), RCARS CLI — RHDP Content Advisory & Recommendation System., Show catalog status summary. (+18 more)

### Community 64 - "scan"
Cohesion: 0.22
Nodes (13): Analyze Showroom content via Sonnet API., scan(), classify_scan_error(), Exception, Classify a scan error and return (error_class, human_message)., Clear old embeddings and store fresh ones for a content_id atomically. Returns…, regenerate_embeddings(), _propagate_to_sibling() (+5 more)

### Community 65 - "test_osspa_db.py"
Cohesion: 0.18
Nodes (11): db(), fixture, _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch() (+3 more)

### Community 66 - "RcarsMasthead.tsx"
Cohesion: 0.19
Nodes (12): API_DOCS_URL, DbStatus, formatAge(), getInitials(), RcarsMasthead(), applyTheme(), getInitialTheme(), Theme (+4 more)

### Community 67 - "test_reporting.py"
Cohesion: 0.15
Nodes (10): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), Internal: compute score and return (breakdown_dict, final_score)., Compute sales impact tier from closed amount., Compute performance score 0-100 using percentile ranks. Higher = stronger…, Return the full score breakdown dict (factors + explanation). (+2 more)

### Community 68 - "ContentAnalysisPage.tsx"
Cohesion: 0.14
Nodes (9): ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment, OverlapItem, OverlapStats (+1 more)

### Community 69 - "AdvisorPage.tsx"
Cohesion: 0.08
Nodes (33): resolveBlockRenderer(), ChatChip, ChatEnvelope, ProgressMessage, ProgressStream(), ProgressStreamProps, buildUrl(), FALLBACK_FORMAT_LABELS (+25 more)

### Community 70 - "api.ts"
Cohesion: 0.12
Nodes (17): FieldSourcePage(), formatDate(), repoDisplayName(), SortField, Tab, FieldSourceData, FieldSourceProvision, FieldSourceRepo (+9 more)

### Community 71 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (13): Async Job Pattern, Green/Yellow/White Tier System, Three-Tier Rearchitecture, ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec (+5 more)

### Community 72 - "group"
Cohesion: 0.18
Nodes (11): group, infra_group(), osspa_group(), Infrastructure metadata commands., Workload mapping and scanning commands., Reporting database metrics commands., Controlled vocabulary — review queue and re-scan staging., Portfolio architecture ingest commands. (+3 more)

### Community 73 - "RouterOutput"
Cohesion: 0.29
Nodes (14): RouterOutput, Scope, resolve_and_verify(), test_scope_shapes(), test_examples_validate_as_router_output(), test_followup_chips_are_pre_routed(), asyncio, test_lb_ref_resolves() (+6 more)

### Community 74 - "test_auth_routes.py"
Cohesion: 0.15
Nodes (6): client(), fixture, Tests for API key management endpoints., TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 75 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (12): Content Model Normalization, Intent-Based Chat Routing, Overlap Analysis Redesign, Performance Scoring Formula, Reporting MCP Data Sync, Retirement Workflow, Retirement Analysis Integration Plan, Retirement Workflow Actions Plan (+4 more)

### Community 76 - "test_status_visibility.py"
Cohesion: 0.27
Nodes (10): _arch(), db(), fixture, test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators() (+2 more)

### Community 77 - "TestValidation"
Cohesion: 0.32
Nodes (4): Every document is built from one helper so indentation stays uniform —…, TestPathOverride, TestValidation, write_vocab()

### Community 78 - "SyncPage.tsx"
Cohesion: 0.18
Nodes (5): LogWindow(), LogWindowProps, ActionState, ScheduleInfo, SyncPage()

### Community 79 - "recommendations.py"
Cohesion: 0.24
Nodes (9): get_recommendations(), BaseModel, limit, post, Request, Recommendations endpoint for external integrations. Low effort runs inline…, RecommendationRequest, _run_low() (+1 more)

### Community 80 - "extract_base_name"
Cohesion: 0.27
Nodes (3): extract_base_name(), Strip stage suffix from an RCARS ci_name to get the reporting DB base name., TestExtractBaseName

### Community 81 - "build_analysis_prompt"
Cohesion: 0.20
Nodes (6): build_analysis_prompt(), Truncate content to max characters., Build analysis prompt split into system instructions and user data.…, truncate_content(), build_analysis_prompt slices the template; only the Instructions section…, TestPromptInjection

### Community 82 - "_reconcile_queued_orphans"
Cohesion: 0.44
Nodes (10): Mark queued jobs as failed if they have no entry in their arq queue. For each…, _reconcile_queued_orphans(), _mock_db(), asyncio, Tests for queued-job orphan reconciliation (RHDPCD-258)., test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed() (+2 more)

### Community 83 - "TestMcpPagination"
Cohesion: 0.53
Nodes (3): patch, Build a mock urllib response for an MCP query result., TestMcpPagination

### Community 84 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native AGENTS.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 85 - "Candidate"
Cohesion: 0.08
Nodes (26): _primary_asset_type(), Any, Candidate, A content entity moving through the recommendation pipeline., Convert similarity score (0.0-1.0) to percentage., _call_rationale_single(), _format_single_candidate(), Any (+18 more)

### Community 86 - "database.py"
Cohesion: 0.13
Nodes (15): datetime, PostgreSQL + pgvector database layer for RCARS v2., client(), db(), fixture, API tests for GET /api/v1/analysis/field-source., Verify the endpoint is registered on the analysis router., test_field_source_endpoint() (+7 more)

### Community 87 - "File Map"
Cohesion: 0.12
Nodes (16): Content-Type Drivers Implementation Plan, Create, Delete, Execution Notes, File Map, Global Constraints, Modify, Review Focus (+8 more)

### Community 88 - "_build_windowed_metrics"
Cohesion: 0.28
Nodes (6): _build_windowed_metrics(), Build per-item windowed_metrics JSONB from per-window query results. For each…, Windowed metrics should have entries for all four windows., An item with zero provisions/sales in a window should score 0., Items with different provision counts should get different scores., TestBuildWindowedMetrics

### Community 89 - "_window_start"
Cohesion: 0.38
Nodes (3): Return the start date for a sliding window (today - N days)., _window_start(), TestWindowStart

### Community 90 - "test_api_infrastructure.py"
Cohesion: 0.25
Nodes (4): client(), fixture, Tests for GET /catalog/infrastructure endpoint and removal of old workload-…, seed_infrastructure()

### Community 91 - "test_infrastructure.py"
Cohesion: 0.25
Nodes (4): clean_infra(), db(), fixture, Tests for infrastructure table DB operations.

### Community 92 - "AdocRead"
Cohesion: 0.25
Nodes (8): NamedTuple, AdocRead, db(), fake_analyze(), fake_repo(), fixture, A clone stand-in whose adoc files always read successfully., settings()

### Community 93 - "HandsOnDriver"
Cohesion: 0.18
Nodes (5): _extract_duration_target(), HandsOnDriver, Any, test_hands_on_display_config(), test_hands_on_triage_guidance()

### Community 94 - "test_vocabulary.py"
Cohesion: 0.14
Nodes (10): dedup_topics(), Collapse spelling variants of the same topic on the same item. Squash key…, clear_vocabulary_cache(), fixture, Tests for the controlled vocabulary loader, normalizer, and prompt renderer., load_vocabulary is process-cached; clear it around every test., analyze_showroom normalizes right after parse — not at the write sites., TestAnalyzerNormalizesOnce (+2 more)

### Community 95 - "test_vocabulary_admin.py"
Cohesion: 0.14
Nodes (6): clear_vocabulary_cache(), client(), fixture, Vocabulary generator + admin endpoints., TestRoleGating, TestVocabularyEndpoints

### Community 96 - "RetirementPage.tsx"
Cohesion: 0.11
Nodes (21): RcarsSidebar(), AuthContext, AuthState, defaultState, useAuth(), NonProdItemsPage(), SortField, stageBadgeClass (+13 more)

### Community 97 - "rcars-login.py"
Cohesion: 0.54
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 98 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (7): Infrastructure-Aware Catalog Metadata, PatternFly 6 Theme Architecture, Server-Side Filtering, Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "API Authentication Design"
Cohesion: 0.38
Nodes (7): API Authentication Design, API Key Authentication (X-API-Key Header), OAuth PKCE Login Flow, Proxy Verification Secret (Anti-Spoofing), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "RCARS — Project Instructions"
Cohesion: 0.13
Nodes (14): API Reference, Architecture, Build & Deploy, CLI, Collaboration, Database, Git Workflow, graphify (+6 more)

### Community 101 - "test_workers.py"
Cohesion: 0.24
Nodes (11): OSSPA sub-pipeline: CSV fetch + scope → clone → upsert + retire → analyze., Nightly maintenance orchestrator: Babylon sub-pipeline, then OSSPA., run_nightly_pipeline(), run_osspa_pipeline(), asyncio, Minimal ctx dict for testing ops pipeline functions., test_nightly_pipeline_runs_osspa_after_babylon(), test_osspa_pipeline_respects_the_enable_flag() (+3 more)

### Community 102 - "_extrapolate_count"
Cohesion: 0.43
Nodes (3): _extrapolate_count(), Scale a count metric to fill a full window if the item is newer. Returns…, TestExtrapolateCount

### Community 103 - "rcars-login.sh"
Cohesion: 0.48
Nodes (5): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token()

### Community 104 - "app.py"
Cohesion: 0.33
Nodes (3): BaseHTTPMiddleware, Request, RequestLoggingMiddleware

### Community 105 - "test_field_source_sync.py"
Cohesion: 0.21
Nodes (12): db(), FakeSettings, _mock_mcp_query(), fixture, Tests for run_field_source_sync. Requires a live PostgreSQL test DB., Re-running the sync replaces old data (full replace, not accumulate)., Returns error dict when MCP is not configured; does not touch DB., Return OCP rows for the OCP catalog_id, RHEL rows for the RHEL catalog_id. (+4 more)

### Community 106 - "API Key Authentication"
Cohesion: 0.67
Nodes (4): API Key Authentication, OpenShift Group-Based Auth, API Authentication Plan, OpenShift Group Auth Plan

### Community 107 - "setup_logging"
Cohesion: 0.33
Nodes (9): BoundLogger, lifespan(), _add_component(), get_logger(), _reorder_keys(), setup_logging(), shutdown(), test_logger_outputs_json() (+1 more)

### Community 108 - "test_auth_token.py"
Cohesion: 0.25
Nodes (5): client(), fixture, patch, Tests for OAuth token exchange endpoint (implicit grant flow)., TestTokenExchange

### Community 109 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 110 - "Rec Card Duration and Best Fit Spec"
Cohesion: 0.67
Nodes (3): Curated Duration Override, Rec Card Duration and Best Fit Plan, Rec Card Duration and Best Fit Spec

### Community 111 - "Controlled Vocabulary Design"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 114 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 115 - "db"
Cohesion: 0.67
Nodes (3): db(), fixture, Create a fresh test database with schema.

### Community 139 - "Global Constraints"
Cohesion: 0.22
Nodes (8): Field Source Content Report — Implementation Plan, Global Constraints, Task 1: Database Schema and Methods, Task 2: Reporting Sync Job, Task 3: API Endpoint, Task 4: Frontend Page, Task 5: Routing and Sidebar, Task 6: End-to-End Verification

### Community 169 - "resolve_refs_to_shas"
Cohesion: 0.25
Nodes (8): _is_github_throttle(), CompletedProcess, Run a git command with retry and exponential backoff for GitHub throttling., Batch-resolve git refs to commit SHAs via ls-remote. Groups pairs by URL so…, Resolve a single ref against the parsed ls-remote output., _resolve_ref_from_lookup(), resolve_refs_to_shas(), _run_git_with_retry()

### Community 172 - "BlockErrorBoundary"
Cohesion: 0.25
Nodes (3): BlockErrorBoundary, Props, State

### Community 173 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 174 - "Field Source Content"
Cohesion: 0.33
Nodes (5): API, Data Import, Data Source, Field Source Content, Frontend

### Community 175 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 178 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 181 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **320 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_EMBEDDING_URL`, `rcars` (+315 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **62 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `.replace_embeddings`, `.retire_missing_osspa`, `.revoke_user_cli_keys`, `.upsert_nonprod_usage`, `command`, `db`, `db`, `db`, `db`, `db`, `test_overlap_assessment.py`, `derive_status`, `Any`, `pipeline.py`, `ops.py`, `test_db.py`, `router.py`, `workload_scanner.py`, `Settings`, `settings.py`, `handlers.py`, `seed_chat_fixtures`, `db/__init__.py`, `_generate_key`, `test_nonprod.py`, `test_vocabulary_db.py`, `config.py`, `test_chat_sessions_db.py`, `.delete_field_source_provisions`, `.get_field_source_summary`, `.list_retirement_items`, `.upsert_field_source_provisions`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `cli.py`, `run_osspa_sync`, `test_osspa_db.py`, `RouterOutput`, `test_status_visibility.py`, `extract_base_name`, `database.py`, `test_api_infrastructure.py`, `test_infrastructure.py`, `AdocRead`, `test_field_source_sync.py`, `setup_logging`, `.retire_missing_babylon`, `.__init__`, `db`, `.advisory_lock`, `.delete_infrastructure_absent`, `.get_channel_metrics_map`, `.get_queued_job_ids`, `.list_nonprod_items`, `.prune_expired_api_keys`, `.prune_old_jobs`, `.record_unknown_term`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `Settings` connect `Settings` to `test_auth_middleware.py`, `command`, `analysis.py`, `routes/catalog.py`, `admin.py`, `analyzer.py`, `test_overlap_assessment.py`, `pipeline.py`, `ops.py`, `create_app`, `router.py`, `settings.py`, `handlers.py`, `routes/auth.py`, `seed_chat_fixtures`, `test_chat_handlers.py`, `advisor.py`, `config.py`, `test_auth_security.py`, `generate_vocabulary_yaml`, `run_osspa_sync`, `analyze_architecture_item`, `test_catalog_osspa_routes.py`, `cli.py`, `scan`, `RouterOutput`, `test_auth_routes.py`, `recommendations.py`, `database.py`, `test_api_infrastructure.py`, `AdocRead`, `test_vocabulary_admin.py`, `test_workers.py`, `app.py`, `test_auth_token.py`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Why does `Candidate` connect `Candidate` to `pipeline.py`, `ContentTypeDriver`, `HandsOnDriver`, `test_drivers.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Database` (e.g. with `HandlerResult` and `Resolution`) actually correct?**
  _`Database` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 32 inferred relationships involving `Settings` (e.g. with `SyncOsspaRequest` and `ChatRequest`) actually correct?**
  _`Settings` has 32 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _320 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_auth_middleware.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05396825396825397 - nodes in this community are weakly interconnected._