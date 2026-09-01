# Graph Report - rcars  (2026-08-25)

## Corpus Check
- 238 files · ~417,377 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2239 nodes · 4639 edges · 165 communities (112 shown, 53 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 251 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `be94ad95`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_auth_middleware.py
- Database
- test_jira_service.py
- AdvisorPage.tsx
- devDependencies
- services/catalog.py
- routes/catalog.py
- _expand_query_terms
- schemas.py
- derive_status
- test_overlap_assessment.py
- Generalized Content Model Design
- chat/models.py
- ops.py
- settings.py
- workload_scanner.py
- migrate_to_content_model.py
- router.py
- vocabulary/__init__.py
- test_db.py
- call_llm
- db/__init__.py
- Any
- database.py
- load_vocabulary
- normalize_analysis
- BrowsePage.tsx
- Settings
- Controlled Vocabulary
- analyzer.py
- test_vocabulary.py
- _generate_key
- PerformancePage.tsx
- compilerOptions
- advisor.py
- test_nonprod.py
- _apply_duration_penalty
- test_vocabulary_db.py
- JobProgressRelay
- Request
- routes/auth.py
- reporting_sync.py
- cli.py
- App.tsx
- api.ts
- group
- compute_sales_impact
- test_auth_security.py
- dev-services.sh
- orchestrator.py
- generate_vocabulary_yaml
- RCARS OCP Deployment Playbook
- sync_opl_vocabulary.py
- Scan Pipeline
- create_app
- route
- event_parser.py
- analysis.py
- pipeline.py
- handlers.py
- RcarsMasthead.tsx
- ContentAnalysisPage.tsx
- content_entities Table
- scan
- config.py
- ECA Production Redesign Spec
- test_services.py
- HistoryPage.tsx
- Reporting MCP Data Sync
- render_vocabulary_block
- TestValidation
- SyncPage.tsx
- extract_base_name
- build_analysis_prompt
- parse_analysis_response
- test_chat_handlers.py
- Performance Analysis
- Scan Worker
- mcp_query
- _coerce_list
- _build_windowed_metrics
- test_infrastructure.py
- _reconcile_queued_orphans
- test_api_infrastructure.py
- TestVocabularyEndpoints
- useAuth.ts
- rcars-login.py
- RCARS Architecture (4 Deployments)
- Browse Page Redesign Plan
- API Authentication Design
- test_product_terms.py
- _window_start
- build_embedding_text
- rcars-login.sh
- Chat Router LLM
- test_chat_routing_golden.py
- app.py
- format_triage_candidates
- ApiKeysPanel.tsx
- Jira Epic RHDPCD-25 (RCARS Backlog)
- API Key Authentication
- migrate_token_usage.py
- db
- test_auth_token.py
- Database Schema (15 tables, SCHEMA_SQL)
- Rec Card Duration and Best Fit Spec
- RCARS Documentation Site (MkDocs)
- .retire_removed_items
- .__init__
- Deploy Docs GitHub Actions Workflow
- Change Detection
- Plan 3a: Web UI Implementation
- Overlap Detection Redesign Plan
- .delete_infrastructure_absent
- .get_channel_metrics_map
- .get_queued_job_ids
- .list_nonprod_items
- .prune_expired_api_keys
- .prune_old_jobs
- .record_unknown_term
- .replace_embeddings
- .revoke_user_cli_keys
- .upsert_nonprod_usage
- test_chat_live.py
- db
- docker-entrypoint.sh
- Webhook Configuration Task
- CI Name Resolution (Vector Search + Regex)
- Scan Deduplication (git ls-remote + SHA)
- OpenShift OAuth Proxy (Red Hat SSO)
- Follow-up Chips
- Item Facts Intent
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
- React Frontend SPA
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
- Match Event Prompt Template
- Python Requirements Entry Point

## God Nodes (most connected - your core abstractions)
1. `Database` - 225 edges
2. `Settings` - 141 edges
3. `load_vocabulary()` - 64 edges
4. `normalize_analysis()` - 28 edges
5. `JobProgressRelay` - 26 edges
6. `RouterOutput` - 26 edges
7. `parse_analysis_response()` - 25 edges
8. `seed_chat_fixtures()` - 25 edges
9. `call_llm()` - 24 edges
10. `_make_request()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `Build Frontend Task` --implements--> `React 19 SPA Frontend (PatternFly 6)`  [INFERRED]
  ansible/tasks/build-frontend.yml → CLAUDE.md
- `Build API Task` --implements--> `FastAPI 2.0 API (uvicorn)`  [INFERRED]
  ansible/tasks/build-api.yml → CLAUDE.md
- `Advisor Smoke Test Task` --references--> `Recommend Worker (arq:queue:recommend)`  [INFERRED]
  ansible/tasks/smoke-test.yml → CLAUDE.md
- `FastAPI API` --shares_data_with--> `Redis (Job Queue + Pub/Sub)`  [EXTRACTED]
  docs/architecture/system-design.md → CLAUDE.md
- `Recommend Worker` --shares_data_with--> `Redis (Job Queue + Pub/Sub)`  [EXTRACTED]
  docs/architecture/system-design.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Three-Phase Recommendation Pipeline** — docs_architecture_recommendation_engine_vector_search, docs_architecture_recommendation_engine_haiku_triage, docs_architecture_recommendation_engine_sonnet_rationale, docs_architecture_system_design_nomic_embed, docs_architecture_system_design_pgvector [EXTRACTED 1.00]
- **Four-Deployment OpenShift Architecture** — docs_architecture_system_design_fastapi_api, docs_architecture_system_design_scan_worker, docs_architecture_system_design_recommend_worker, docs_architecture_system_design_react_frontend, docs_architecture_system_design_pgvector [EXTRACTED 1.00]
- **Multi-Intent Chat System** — docs_architecture_advisor_chat_router, docs_architecture_advisor_chat_intent_recommend, docs_architecture_advisor_chat_intent_overlap, docs_architecture_advisor_chat_intent_performance, docs_architecture_advisor_chat_intent_infrastructure, docs_architecture_advisor_chat_intent_item_facts [EXTRACTED 1.00]
- **Content Analysis Pipeline (Vocabulary + Showroom Analysis + Overlap Assessment)** — src_api_rcars_data_vocabulary_controlled_vocabulary, src_api_rcars_prompts_analyze_showroom_analysis_prompt, src_api_rcars_prompts_overlap_assessment_overlap_prompt, src_api_rcars_prompts_analyze_showroom_learning_objectives [EXTRACTED 0.95]
- **RCARS Taxonomy System (Products, Solutions, Verticals, Platforms, Difficulty)** — src_api_rcars_data_vocabulary_products_taxonomy, src_api_rcars_data_vocabulary_solutions_taxonomy, src_api_rcars_data_vocabulary_verticals_taxonomy, src_api_rcars_data_vocabulary_platforms_taxonomy, src_api_rcars_data_vocabulary_difficulty_levels [EXTRACTED 1.00]
- **LLM Infrastructure (Anthropic + OpenAI SDKs + Prompt Templates)** — src_api_requirements_lock_anthropic, src_api_requirements_lock_openai, src_api_rcars_prompts_analyze_showroom_analysis_prompt, src_api_rcars_prompts_overlap_assessment_overlap_prompt [INFERRED 0.85]
- **Ansible Deployment Pipeline** — ansible_deploy_playbook, ansible_tasks_apply_infra, ansible_tasks_apply_manifests, ansible_tasks_build_api, ansible_tasks_build_frontend, ansible_tasks_smoke_test, ansible_tasks_namespace, ansible_vars_common [EXTRACTED 1.00]
- **RCARS Four-Component Architecture** — claude_md_frontend, claude_md_fastapi_api, claude_md_scan_worker, claude_md_recommend_worker, claude_md_postgresql_pgvector, claude_md_redis [EXTRACTED 1.00]
- **System Evolution from Monolith to Multi-Tier** — docs_superpowers_specs_2026-04-07-eca-production-redesign-design, docs_superpowers_specs_2026-04-08-rcars-plan3a-web-ui-design, docs_superpowers_specs_2026-04-25-rearchitecture-api-design, concept_rearchitecture [EXTRACTED 0.95]
- **Authentication and Authorization Evolution** — concept_api_key_auth, concept_openshift_group_auth, docs_superpowers_plans_2026-07-03-api-authentication, docs_superpowers_plans_2026-08-05-openshift-group-auth [INFERRED 0.85]
- **Performance Analysis Feature Stack** — concept_reporting_mcp_sync, concept_performance_scoring, concept_retirement_workflow, docs_superpowers_plans_2026-08-04-performance-page [EXTRACTED 0.95]
- **Recommendation Pipeline LLM Prompts** — src_api_rcars_prompts_triage, src_api_rcars_prompts_rationale, src_api_rcars_prompts_rationale_single, src_api_rcars_prompts_rationale_synthesis [INFERRED 0.95]
- **Generalized Content Model Core Tables** — docs_superpowers_specs_2026_07_20_generalized_content_model_design_content_entities, docs_superpowers_specs_2026_07_20_generalized_content_model_design_babylon_items, docs_superpowers_specs_2026_07_20_generalized_content_model_design_embeddings, docs_superpowers_specs_2026_07_20_generalized_content_model_design_performance_channels [EXTRACTED 1.00]
- **Authentication and Access Control System** — docs_superpowers_specs_2026_07_03_api_authentication_design_api_keys, docs_superpowers_specs_2026_07_03_api_authentication_design_oauth_login, docs_superpowers_specs_2026_07_03_api_authentication_design_proxy_verification, docs_superpowers_specs_2026_08_05_role_assignments_design_role_assignments_table [INFERRED 0.95]

## Communities (165 total, 53 thin omitted)

### Community 0 - "test_auth_middleware.py"
Cohesion: 0.05
Nodes (43): dict, _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), invalidate_role_assignments_cache(), _log_auth_decision(), _parse_sa_allowlist() (+35 more)

### Community 2 - "test_jira_service.py"
Cohesion: 0.13
Nodes (27): _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _jira_request(), Jira REST API client for retirement ticket creation. Uses urllib (consistent…, Create a Jira retirement ticket. Returns the new Jira issue key (e.g.…, Make an HTTP request to the Jira REST API v3 with Basic auth. Returns parsed…, Derive catalog base name from content_id (e.g. 'babylon:foo.prod' → 'foo'). (+19 more)

### Community 3 - "AdvisorPage.tsx"
Cohesion: 0.06
Nodes (42): BlockErrorBoundary, Props, State, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps (+34 more)

### Community 4 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-core, @patternfly/react-icons, @patternfly/react-table (+40 more)

### Community 5 - "services/catalog.py"
Cohesion: 0.11
Nodes (27): _apply_component_inheritance(), _collect_bases(), component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata(), extract_showroom_url() (+19 more)

### Community 6 - "routes/catalog.py"
Cohesion: 0.14
Nodes (41): field_validator, add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis() (+33 more)

### Community 7 - "_expand_query_terms"
Cohesion: 0.15
Nodes (9): _build_expansion_map(), _expand_query_terms(), Invert the vocabulary's product aliases into term -> canonical name. Aliases…, Expand product names, acronyms, and synonyms for better embedding match. One…, parametrize, Word-boundary matching — RHOAI inside RHOAIX must not expand., GitOps must still pull in ArgoCD and Argo CD as recall terms., TestExpansionReadsVocabulary (+1 more)

### Community 8 - "schemas.py"
Cohesion: 0.09
Nodes (53): add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs(), list_role_assignments() (+45 more)

### Community 9 - "derive_status"
Cohesion: 0.07
Nodes (20): derive_status(), Retirement workflow business logic., Derive the workflow status from the highest completed step., Tests for retirement workflow business logic (derive_status)., Test derive_status with various step combinations., Validate STEP_ORDER constant structure., Retired should be first (highest priority), reviewed last., With no step timestamps, status defaults to 'reviewed'. (+12 more)

### Community 10 - "test_overlap_assessment.py"
Cohesion: 0.09
Nodes (33): assess_overlap(), _build_assessment_prompt(), _load_analysis_pair(), Assess overlap between two content items via LLM. Returns (assessment_dict,…, Validate LLM assessment response and coerce to canonical form. Returns None if…, Load showroom_analysis + content_entities for both items., Build overlap assessment prompt from template., _validate_assessment() (+25 more)

### Community 11 - "Generalized Content Model Design"
Cohesion: 0.08
Nodes (34): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, Retirement Scoring Formula (0-100, Higher = Stronger Candidate), PatternFly 6 Migration Design, Navigation Restructure (Flattened Nav with Role-Gated Sections), RCARS Theme Architecture (Light/Dark Mode), Retirement Workflow Actions Design (+26 more)

### Community 12 - "chat/models.py"
Cohesion: 0.23
Nodes (17): Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemFactsArgs, OverlapArgs, PerformanceArgs (+9 more)

### Community 13 - "ops.py"
Cohesion: 0.08
Nodes (37): CompletedProcess, clone_showroom(), _is_github_throttle(), ls_remote_sha(), Run a git command with retry and exponential backoff for GitHub throttling., Get the current SHA for a ref without cloning. Returns None on failure., Batch-resolve git refs to commit SHAs via ls-remote. Groups pairs by URL so…, Shallow clone a Showroom repo. Returns clone path or None on failure. (+29 more)

### Community 14 - "settings.py"
Cohesion: 0.09
Nodes (27): BoundLogger, RedisSettings, fetch_litemaas_models(), Query LiteMaaS /v1/models endpoint once and cache the result., _add_component(), get_logger(), setup_logging(), candidates_with_performance() (+19 more)

### Community 15 - "workload_scanner.py"
Cohesion: 0.09
Nodes (30): build_infrastructure_embedding_text(), Build text for infrastructure embedding from an infrastructure table row., analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products(), Path (+22 more)

### Community 16 - "migrate_to_content_model.py"
Cohesion: 0.09
Nodes (35): Connection, datetime, cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate() (+27 more)

### Community 17 - "router.py"
Cohesion: 0.16
Nodes (27): _prefix_overlap(), Count keyword matches allowing prefix matching for words >= min_prefix chars., RouterOutput, Scope, _find_keyword_ties(), _parse_catalog_url(), pattern_check(), Routing: pattern check, router LLM call (Task 9), resolve & verify ladder. (+19 more)

### Community 18 - "vocabulary/__init__.py"
Cohesion: 0.10
Nodes (31): _header_comment(), Emit a merged vocabulary.yaml — current file plus staged admin decisions.…, Preserve the active vocabulary file's leading comment block., Controlled vocabulary — one list, two consumers (analysis + query expansion)., _as_tuple(), _build_lookups(), _parse_entries(), Any (+23 more)

### Community 19 - "test_db.py"
Cohesion: 0.09
Nodes (15): db(), db_with_perf_data(), fixture, Seed test data for filtered catalog queries., Seed performance data for testing., _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider() (+7 more)

### Community 20 - "call_llm"
Cohesion: 0.19
Nodes (17): call_llm(), Unified LLM call with automatic provider routing. LiteMaaS preferred if…, _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis(), _format_single_candidate(), generate_content_gaps(), generate_rationale() (+9 more)

### Community 21 - "db/__init__.py"
Cohesion: 0.14
Nodes (23): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), ConnectionPool, Deterministic overlap candidate generation via structured matching., Aggregate stats by verdict., Item-centric overlap report grouped by verdict. (+15 more)

### Community 22 - "Any"
Cohesion: 0.08
Nodes (4): Any, Queue rows, ranked by occurrences descending. status=None returns all., Record an admin decision. Staged only — nothing about analysis changes until a…, Upsert a Babylon catalog item across content_entities + babylon_items in one…

### Community 23 - "database.py"
Cohesion: 0.12
Nodes (25): PostgreSQL + pgvector database layer for RCARS v2., build_evidence_pack(), Evidence pack: v1 graph expansion — one hop, code-driven, bounded. The budget…, fake_embedding(), Seeded fixture catalog for chat tests (also a foundation for the broader…, Deterministic 768-dim unit vector from the text hash. Signature is monkeypatch-…, seed_chat_fixtures(), db() (+17 more)

### Community 24 - "load_vocabulary"
Cohesion: 0.13
Nodes (11): load_vocabulary(), Load, validate, and cache the controlled vocabulary for this process., _noise_variants(), Rung 3 candidates: strip known noise, then retry rungs 1-2 on each., Snap one value to its canonical form. Returns (result, matched). On a miss the…, snap_term(), Punctuation and spacing differences resolve without a human., The spec's worked examples, wherever on the ladder they land. (+3 more)

### Community 25 - "normalize_analysis"
Cohesion: 0.15
Nodes (9): normalize_analysis(), Any, Snap aliases to canonical forms and dedup topics, before write. Pure when db is…, Upsert one row per distinct term. Never touches the item's review flags., _record_unknowns(), Keys absent from an analyzer's output are skipped — one map, two sources., A term in ignored_terms is stored verbatim but never recorded., TestIgnoredTermsSuppression (+1 more)

### Community 26 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (16): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, BrowsePage(), CatalogItem, catalogUrl() (+8 more)

### Community 27 - "Settings"
Cohesion: 0.13
Nodes (14): BaseSettings, _parse_csv(), Settings, _get_embedding_client(), Lazy-init a shared httpx client for the vLLM embedding server., test_admin_check(), test_chat_intent_roles_invalid_role_rejected(), test_chat_intent_roles_parse() (+6 more)

### Community 28 - "Controlled Vocabulary"
Cohesion: 0.10
Nodes (24): Action Verbs Validation Rules, Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy (+16 more)

### Community 29 - "analyzer.py"
Cohesion: 0.16
Nodes (21): analyze_showroom(), build_module_embedding_text(), check_showroom_stale(), filter_boilerplate_files(), get_repo_head(), hash_showroom_content(), _parse_nav_includes(), Any (+13 more)

### Community 30 - "test_vocabulary.py"
Cohesion: 0.14
Nodes (10): dedup_topics(), Collapse spelling variants of the same topic on the same item. Squash key…, clear_vocabulary_cache(), fixture, Tests for the controlled vocabulary loader, normalizer, and prompt renderer., load_vocabulary is process-cached; clear it around every test., analyze_showroom normalizes right after parse — not at the write sites., TestAnalyzerNormalizesOnce (+2 more)

### Community 31 - "_generate_key"
Cohesion: 0.12
Nodes (11): db(), _generate_key(), fixture, Tests for API key database CRUD operations., Ephemeral test database — uses RCARS_DATABASE_URL from env (rcars_test)., Generate a raw key, its hash, and its prefix., TestCreateApiKey, TestGetApiKeyByHash (+3 more)

### Community 32 - "PerformancePage.tsx"
Cohesion: 0.16
Nodes (18): fmt(), fmtRoi(), num(), scoreBg(), ScoreBreakdownPopover(), scoreColor(), stageBadgeClass, WorkflowDrawer() (+10 more)

### Community 33 - "compilerOptions"
Cohesion: 0.09
Nodes (22): DOM, DOM.Iterable, ES2020, src, compilerOptions, allowImportingTsExtensions, isolatedModules, jsx (+14 more)

### Community 34 - "advisor.py"
Cohesion: 0.20
Nodes (23): _advisor_limit(), ChatRequest, get_query_result(), get_session(), list_sessions(), BaseModel, get, limit (+15 more)

### Community 35 - "test_nonprod.py"
Cohesion: 0.09
Nodes (10): Return {base_name: content_id} for items with no active prod-stage variant., Tests for get_nonprod_base_names — requires live DB with test data., Verify the nonprod routes exist on the analysis router., TestGetNonprodBaseNames, TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema (+2 more)

### Community 36 - "_apply_duration_penalty"
Cohesion: 0.40
Nodes (5): _apply_duration_penalty(), _apply_usage_boost(), Candidate, Apply a soft score penalty based on duration overshoot. Gentle: a 2x overshoot…, Boost relevance scores for candidates with proven usage. Looks up…

### Community 37 - "test_vocabulary_db.py"
Cohesion: 0.09
Nodes (9): db(), fixture, Tests for the vocabulary_unknown_terms queue. Requires a live PostgreSQL., Vocabulary work never sets enrichment_review_needed or review_reasons., TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched (+1 more)

### Community 38 - "JobProgressRelay"
Cohesion: 0.16
Nodes (17): Redis, create_sse_response(), JobProgressRelay, Redis pub/sub relay and SSE streaming for job progress., Subscribe to job progress. Yields message dicts, or None as keepalive., sse_stream(), translate_to_user_message(), asyncio (+9 more)

### Community 39 - "Request"
Cohesion: 0.16
Nodes (28): analyze_single(), approve_item(), _base_name_to_content_id(), cancel_workflow(), check_stale(), get_workflow(), ignore_item(), link_jira() (+20 more)

### Community 40 - "routes/auth.py"
Cohesion: 0.18
Nodes (22): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), delete, get (+14 more)

### Community 41 - "reporting_sync.py"
Cohesion: 0.14
Nodes (21): _build_closed_sql(), _build_cost_sql(), _build_nonprod_provisions_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs() (+13 more)

### Community 42 - "cli.py"
Cohesion: 0.09
Nodes (49): argument, command, option, pass_context, cli(), flag(), get_db(), infra_stats() (+41 more)

### Community 43 - "App.tsx"
Cohesion: 0.14
Nodes (16): App(), useAuthProvider(), AdminQueriesPage(), AdminRolesPage(), AdminTokensPage(), QuerySessionSummary, SessionTurn, TokenStats (+8 more)

### Community 44 - "api.ts"
Cohesion: 0.18
Nodes (10): VocabularyPage(), MarketingMetrics, NonProdDashboardResponse, PerformanceDashboardResponse, RoleAssignment, SalesMetrics, ScoreBreakdownFactor, UnknownTerm (+2 more)

### Community 45 - "group"
Cohesion: 0.22
Nodes (9): group, infra_group(), Infrastructure metadata commands., Workload mapping and scanning commands., Reporting database metrics commands., Controlled vocabulary — review queue and re-scan staging., reporting_db_group(), vocab_group() (+1 more)

### Community 46 - "compute_sales_impact"
Cohesion: 0.16
Nodes (10): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), Compute sales impact tier from closed amount., Compute performance score 0-100 using percentile ranks. Higher = stronger…, Return the full score breakdown dict (factors + explanation)., Internal: compute score and return (breakdown_dict, final_score). (+2 more)

### Community 47 - "test_auth_security.py"
Cohesion: 0.11
Nodes (11): app_no_auth(), client(), fixture, parametrize, Security test suite for RCARS API authentication. Validates that all auth…, App with NO dev_user — all auth enforced., TestExpiredApiKey, TestRevokedApiKey (+3 more)

### Community 48 - "dev-services.sh"
Cohesion: 0.17
Nodes (19): db_pull(), frontend_only(), init_db(), RCARS_ADMIN_EMAILS_STR, RCARS_CURATOR_EMAILS_STR, RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL (+11 more)

### Community 49 - "orchestrator.py"
Cohesion: 0.18
Nodes (15): get_session_context(), log_chat_turn(), next_turn_index(), Any, Chat-session persistence and context building. Follows the db/similarity.py…, The router's view: last <=max_turns turns, fixed shape, no prose., _help_answer(), process_turn() (+7 more)

### Community 50 - "generate_vocabulary_yaml"
Cohesion: 0.16
Nodes (10): _entries_to_dicts(), generate_vocabulary_yaml(), Any, Merge staged decisions into the loaded vocabulary and serialize. aliased → term…, clear_vocabulary_cache(), client(), fixture, Vocabulary generator + admin endpoints. (+2 more)

### Community 51 - "RCARS OCP Deployment Playbook"
Cohesion: 0.13
Nodes (18): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+10 more)

### Community 52 - "sync_opl_vocabulary.py"
Cohesion: 0.22
Nodes (17): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), Any (+9 more)

### Community 53 - "Scan Pipeline"
Cohesion: 0.15
Nodes (17): CLI Admin Guide, Evidence Pack, Infrastructure Intent, Content Overlap Detection, Cosine Similarity for Overlap, Score Bands, content_similarity Table, embeddings Table (+9 more)

### Community 54 - "create_app"
Cohesion: 0.13
Nodes (12): create_app(), lifespan(), client(), fixture, test_auth_me_unauthenticated(), client(), fixture, client() (+4 more)

### Community 55 - "route"
Cohesion: 0.19
Nodes (13): build_router_prompt(), _extract_json(), Strip code fences / leading prose, then parse. Raises on failure., route(), test_examples_validate_as_router_output(), test_followup_chips_are_pre_routed(), test_prompt_contains_every_intent_and_context(), _fake() (+5 more)

### Community 56 - "event_parser.py"
Cohesion: 0.16
Nodes (16): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), Any, Event URL parser. Fetches event web pages, follows links to…, Filter links to those that look like schedule/program/content pages. (+8 more)

### Community 57 - "analysis.py"
Cohesion: 0.36
Nodes (16): ApproveRequest, _extract_base_name_from_content_id(), LinkJiraRequest, NotesRequest, BaseModel, Analysis routes — scan, stale check, rescan, single-item analysis, retirement., Derive a catalog_base_name from a content_id for backward compatibility.…, StartRequest (+8 more)

### Community 58 - "pipeline.py"
Cohesion: 0.13
Nodes (24): generate_embedding(), Generate a 768-dim embedding via the vLLM embedding server. Nomic requires task…, Candidate, QueryState, Data models for the recommendation pipeline., A content entity moving through the recommendation pipeline., Convert similarity score (0.0-1.0) to percentage., State of a recommendation query at a pipeline phase boundary. (+16 more)

### Community 59 - "handlers.py"
Cohesion: 0.37
Nodes (14): get_item_workloads(), get_performance_scores(), _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_facts(), handle_overlap(), handle_performance() (+6 more)

### Community 60 - "RcarsMasthead.tsx"
Cohesion: 0.19
Nodes (12): API_DOCS_URL, DbStatus, formatAge(), getInitials(), RcarsMasthead(), applyTheme(), getInitialTheme(), Theme (+4 more)

### Community 61 - "ContentAnalysisPage.tsx"
Cohesion: 0.14
Nodes (9): ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment, OverlapItem, OverlapStats (+1 more)

### Community 62 - "content_entities Table"
Cohesion: 0.14
Nodes (14): babylon_items Table, content_entities Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow, Performance Scoring Formula, Acronym Expansion (+6 more)

### Community 63 - "scan"
Cohesion: 0.22
Nodes (13): Analyze Showroom content via Sonnet API., scan(), classify_scan_error(), Exception, Classify a scan error and return (error_class, human_message)., Clear old embeddings and store fresh ones for a content_id atomically. Returns…, regenerate_embeddings(), _propagate_to_sibling() (+5 more)

### Community 64 - "config.py"
Cohesion: 0.29
Nodes (9): _call_anthropic(), _call_litemaas(), LLMResult, build_scaffold(), compose_answer(), Deterministic scaffold + narrow narrative call. Worst case: mediocre prose next…, test_answer_failure_degrades_to_scaffold(), test_compose_prepends_scaffold() (+1 more)

### Community 65 - "ECA Production Redesign Spec"
Cohesion: 0.15
Nodes (13): Async Job Pattern, Green/Yellow/White Tier System, Three-Tier Rearchitecture, ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec (+5 more)

### Community 66 - "test_services.py"
Cohesion: 0.17
Nodes (12): If middle and bottom share a workload, it appears only once., Non-published items with base_ci_name must not set published_ci_name on their…, Published CI with multiple bases gets union of workloads and combined infra…, Run the production second pass and return items keyed by ci_name., Workloads merge up the full chain: bottom → middle → published., _run_catalog_second_pass(), test_candidate_tier_defaults(), test_multi_base_published_ci() (+4 more)

### Community 67 - "HistoryPage.tsx"
Cohesion: 0.21
Nodes (11): Candidate, catalogUrl(), FORMAT_COLORS, FORMAT_LABELS, RecCard(), RecCardProps, HistoryPage(), SessionDetail (+3 more)

### Community 68 - "Reporting MCP Data Sync"
Cohesion: 0.20
Nodes (12): Content Model Normalization, Intent-Based Chat Routing, Overlap Analysis Redesign, Performance Scoring Formula, Reporting MCP Data Sync, Retirement Workflow, Retirement Analysis Integration Plan, Retirement Workflow Actions Plan (+4 more)

### Community 69 - "render_vocabulary_block"
Cohesion: 0.26
Nodes (5): Build the injected block for a given content_entities.content_type., render_vocabulary_block(), Only products and verb hints go into the prompt., The block is spliced into a template that cannot use str.format()., TestRenderVocabularyBlock

### Community 70 - "TestValidation"
Cohesion: 0.32
Nodes (4): Every document is built from one helper so indentation stays uniform —…, TestPathOverride, TestValidation, write_vocab()

### Community 71 - "SyncPage.tsx"
Cohesion: 0.18
Nodes (5): LogWindow(), LogWindowProps, ActionState, ScheduleInfo, SyncPage()

### Community 72 - "extract_base_name"
Cohesion: 0.27
Nodes (3): extract_base_name(), Strip stage suffix from an RCARS ci_name to get the reporting DB base name., TestExtractBaseName

### Community 73 - "build_analysis_prompt"
Cohesion: 0.20
Nodes (6): build_analysis_prompt(), Truncate content to max characters., Build analysis prompt split into system instructions and user data.…, truncate_content(), build_analysis_prompt slices the template; only the Instructions section…, TestPromptInjection

### Community 74 - "parse_analysis_response"
Cohesion: 0.33
Nodes (10): parse_analysis_response(), Parse Sonnet's JSON response, handling markdown fences., test_dict(), test_empty_returns_none(), test_fenced_json(), test_list(), test_scalar_bool_returns_none(), test_scalar_int_returns_none() (+2 more)

### Community 75 - "test_chat_handlers.py"
Cohesion: 0.45
Nodes (10): _noop(), Verify handler returns notice when no embeddings match., Verify handler uses embedding search, not list_infrastructure., _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler() (+2 more)

### Community 76 - "Performance Analysis"
Cohesion: 0.22
Nodes (10): Worker Management, Advisor Chat System, performance_channels Table, Cost Methodology, Performance Analysis, RHDP Reporting MCP Server, Recommend Worker, Non-Prod Items Page Plan (+2 more)

### Community 77 - "Scan Worker"
Cohesion: 0.20
Nodes (10): API Reference, Babylon Kubernetes CRDs, FastAPI API, LiteMaaS LLM Provider, Nightly Maintenance Pipeline, PostgreSQL with pgvector, Scan Worker, Vertex AI LLM Provider (+2 more)

### Community 78 - "mcp_query"
Cohesion: 0.29
Nodes (7): _mcp_call(), mcp_query(), Call an MCP tool via HTTP JSON-RPC, return parsed JSON result., Execute SQL via MCP server, auto-paginating past 500-row cap., patch, Build a mock urllib response for an MCP query result., TestMcpPagination

### Community 79 - "_coerce_list"
Cohesion: 0.40
Nodes (5): _coerce_list(), _fmt_json_field(), Any, Coerce value to string list. None→[], str→[str], list→filtered strings, else→[]., Format JSONB field for prompt. None/empty → 'None available'.

### Community 80 - "_build_windowed_metrics"
Cohesion: 0.28
Nodes (6): _build_windowed_metrics(), Build per-item windowed_metrics JSONB from per-window query results. For each…, Windowed metrics should have entries for all four windows., An item with zero provisions/sales in a window should score 0., Items with different provision counts should get different scores., TestBuildWindowedMetrics

### Community 81 - "test_infrastructure.py"
Cohesion: 0.25
Nodes (4): clean_infra(), db(), fixture, Tests for infrastructure table DB operations.

### Community 82 - "_reconcile_queued_orphans"
Cohesion: 0.44
Nodes (10): Mark queued jobs as failed if they have no entry in their arq queue. For each…, _reconcile_queued_orphans(), _mock_db(), asyncio, Tests for queued-job orphan reconciliation (RHDPCD-258)., test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed() (+2 more)

### Community 83 - "test_api_infrastructure.py"
Cohesion: 0.29
Nodes (4): client(), fixture, Tests for GET /catalog/infrastructure endpoint and removal of old workload-…, seed_infrastructure()

### Community 85 - "useAuth.ts"
Cohesion: 0.17
Nodes (12): WorkflowItem, RcarsSidebar(), AuthContext, AuthState, defaultState, useAuth(), NonProdItemsPage(), SortField (+4 more)

### Community 86 - "rcars-login.py"
Cohesion: 0.54
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 87 - "RCARS Architecture (4 Deployments)"
Cohesion: 0.57
Nodes (7): RCARS Architecture (4 Deployments), FastAPI 2.0 API (uvicorn), React 19 SPA Frontend (PatternFly 6), PostgreSQL with pgvector (768-dim embeddings), Recommend Worker (arq:queue:recommend), Redis (Job Queue + Pub/Sub), Scan Worker (arq:queue:scan)

### Community 88 - "Browse Page Redesign Plan"
Cohesion: 0.33
Nodes (7): Infrastructure-Aware Catalog Metadata, PatternFly 6 Theme Architecture, Server-Side Filtering, Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 89 - "API Authentication Design"
Cohesion: 0.38
Nodes (7): API Authentication Design, API Key Authentication (X-API-Key Header), OAuth PKCE Login Flow, Proxy Verification Secret (Anti-Spoofing), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 90 - "test_product_terms.py"
Cohesion: 0.20
Nodes (6): clear_vocabulary_cache(), fixture, Advisor query expansion, now backed by the controlled vocabulary. Formerly…, search_terms widen recall only — they never snap a value., TestOldFileGone, TestSearchTerms

### Community 91 - "_window_start"
Cohesion: 0.38
Nodes (3): Return the start date for a sliding window (today - N days)., _window_start(), TestWindowStart

### Community 92 - "build_embedding_text"
Cohesion: 0.36
Nodes (3): build_embedding_text(), Build text for CI-level embedding from analysis results., TestBuildEmbeddingText

### Community 93 - "rcars-login.sh"
Cohesion: 0.48
Nodes (5): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token()

### Community 94 - "Chat Router LLM"
Cohesion: 0.33
Nodes (6): Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, Recommendation Engine, RCARS System

### Community 95 - "test_chat_routing_golden.py"
Cohesion: 0.29
Nodes (6): llm_eval, fixture, parametrize, Golden routing eval — real prompt assembly, real model, real validation. Hard-…, settings(), test_routing_golden()

### Community 96 - "app.py"
Cohesion: 0.12
Nodes (13): BaseHTTPMiddleware, FastAPI, _get_user_key(), Request, Per-user rate limiting via slowapi + Redis., Request, RequestLoggingMiddleware, health() (+5 more)

### Community 97 - "format_triage_candidates"
Cohesion: 0.67
Nodes (3): format_triage_candidates(), Candidate, Format candidates compactly for the triage prompt.

### Community 98 - "ApiKeysPanel.tsx"
Cohesion: 0.60
Nodes (4): ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo()

### Community 99 - "Jira Epic RHDPCD-25 (RCARS Backlog)"
Cohesion: 0.50
Nodes (4): Backlog Jira Migration, RCARS Project Instructions, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 100 - "API Key Authentication"
Cohesion: 0.67
Nodes (4): API Key Authentication, OpenShift Group-Based Auth, API Authentication Plan, OpenShift Group Auth Plan

### Community 104 - "test_auth_token.py"
Cohesion: 0.25
Nodes (5): client(), fixture, patch, Tests for OAuth token exchange endpoint (implicit grant flow)., TestTokenExchange

### Community 105 - "Database Schema (15 tables, SCHEMA_SQL)"
Cohesion: 0.67
Nodes (3): Database Schema (15 tables, SCHEMA_SQL), Performance Scoring Formula (4 Factors, Max ~80), Soft-Delete Pattern (retired_at)

### Community 106 - "Rec Card Duration and Best Fit Spec"
Cohesion: 0.67
Nodes (3): Curated Duration Override, Rec Card Duration and Best Fit Plan, Rec Card Duration and Best Fit Spec

### Community 107 - "RCARS Documentation Site (MkDocs)"
Cohesion: 0.67
Nodes (3): MkDocs Material Theme Configuration, Architecture Documentation Section, RCARS Documentation Site (MkDocs)

### Community 126 - "test_chat_live.py"
Cohesion: 0.24
Nodes (10): integration, db(), _noop(), fixture, End-to-end chat integration tests — real LLM calls against seeded DB. Tests…, Query a specific item by LB number — expect item_facts intent and item card., Query outside RCARS scope — expect out_of_scope intent., _settings() (+2 more)

## Knowledge Gaps
- **210 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_ADMIN_EMAILS_STR`, `RCARS_CURATOR_EMAILS_STR` (+205 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `derive_status`, `test_overlap_assessment.py`, `ops.py`, `settings.py`, `workload_scanner.py`, `migrate_to_content_model.py`, `router.py`, `test_db.py`, `call_llm`, `db/__init__.py`, `Any`, `database.py`, `_generate_key`, `test_nonprod.py`, `test_vocabulary_db.py`, `cli.py`, `orchestrator.py`, `create_app`, `pipeline.py`, `handlers.py`, `extract_base_name`, `test_infrastructure.py`, `test_api_infrastructure.py`, `migrate_token_usage.py`, `db`, `.complete_job`, `.retire_removed_items`, `.__init__`, `.delete_infrastructure_absent`, `.get_channel_metrics_map`, `.get_queued_job_ids`, `.list_nonprod_items`, `.prune_expired_api_keys`, `.prune_old_jobs`, `.record_unknown_term`, `.replace_embeddings`, `.revoke_user_cli_keys`, `.upsert_nonprod_usage`, `test_chat_live.py`, `db`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Why does `Settings` connect `Settings` to `test_auth_middleware.py`, `routes/catalog.py`, `schemas.py`, `test_overlap_assessment.py`, `ops.py`, `settings.py`, `migrate_to_content_model.py`, `router.py`, `call_llm`, `database.py`, `analyzer.py`, `advisor.py`, `Request`, `routes/auth.py`, `cli.py`, `test_auth_security.py`, `orchestrator.py`, `generate_vocabulary_yaml`, `create_app`, `route`, `analysis.py`, `pipeline.py`, `handlers.py`, `scan`, `config.py`, `test_chat_handlers.py`, `test_api_infrastructure.py`, `TestVocabularyEndpoints`, `test_chat_routing_golden.py`, `app.py`, `migrate_token_usage.py`, `test_auth_token.py`, `test_chat_live.py`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `load_vocabulary()` connect `load_vocabulary` to `test_product_terms.py`, `TestValidation`, `_expand_query_terms`, `schemas.py`, `build_analysis_prompt`, `render_vocabulary_block`, `workload_scanner.py`, `vocabulary/__init__.py`, `generate_vocabulary_yaml`, `normalize_analysis`, `pipeline.py`, `analyzer.py`, `test_vocabulary.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `Database` (e.g. with `HandlerResult` and `Resolution`) actually correct?**
  _`Database` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `Settings` (e.g. with `ChatRequest` and `QueryRequest`) actually correct?**
  _`Settings` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _210 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_auth_middleware.py` be split into smaller, more focused modules?**
  _Cohesion score 0.054212454212454214 - nodes in this community are weakly interconnected._