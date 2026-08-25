# Graph Report - .  (2026-08-21)

## Corpus Check
- 111 files · ~414,253 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2245 nodes · 4496 edges · 172 communities (112 shown, 60 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 241 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Auth & Role Management
- Database Core
- Analysis API Routes
- Advisor Chat UI
- Frontend Dependencies
- Catalog Service
- Catalog API Routes
- Recommender Pipeline
- Admin & Health Routes
- Retirement Workflow
- Overlap Assessment
- Design Specs Archive
- Chat Intent Handlers
- Showroom Git & Clone
- Workers & Configuration
- Workload Scanner
- Migration Scripts
- Chat Router
- Vocabulary Generation
- Database Tests
- Recommender & DB Init
- Overlap Database
- Database Lookups
- Chat Evidence Pack
- Vocabulary Loader Tests
- Vocabulary Normalization
- Browse Page UI
- Settings & Config Types
- Controlled Vocabulary Data
- Showroom Analyzer Core
- Vocabulary Models
- API Key Management
- Score Breakdown Popover
- TypeScript Lib Defs
- Advisor API Routes
- Non-Prod Items
- Duration Penalties
- Vocabulary Fixtures
- Redis & SSE Streaming
- Admin Routes
- Auth Routes
- Reporting Sync
- CLI Arguments
- App Shell & Sidebar
- Recent Jobs Page
- CLI Options
- Performance Scoring
- Auth Security Tests
- Dev Services
- Chat Sessions DB
- Vocabulary Codegen
- Ansible Deploy
- OPL Vocabulary Sync
- CLI Guide & Docs
- FastAPI App Factory
- LLM Eval & Router
- Event Parser
- CLI Print Helpers
- Recommender Models
- LLM Config
- Masthead Component
- Content Analysis Page
- Data Design Docs
- CLI Scan Commands
- Chat Answer Builder
- Architecture Concepts
- Auth Route Tests
- Recommendation Card
- Content Model Concepts
- Vocabulary Renderer
- Vocabulary Path Tests
- Log Window Component
- Base Name Extraction
- Analysis Prompt Builder
- Analysis Response Parser
- Chat Handler Registry
- Operations Docs
- Architecture Reference
- MCP Query Sync
- Overlap Assessment Build
- Windowed Metrics
- Infrastructure CLI
- Structured Logging
- Infrastructure Tests
- Vocabulary Admin Tests
- Workflow & Non-Prod UI
- Login CLI
- CLAUDE.md Docs
- UI Design Concepts
- Auth Design Specs
- Vector Search
- Reporting Window Tests
- Chat Tests
- Login Shell Scripts
- Chat Intent Types
- Chat Registry
- Request Logging
- Infrastructure Embeddings
- API Keys Panel
- Backlog & Jira
- API Key Auth Design
- Rate Limiting
- Health Endpoint
- Token Exchange Tests
- Schema & Scoring Docs
- Duration Best-Fit
- MkDocs Config
- Retirement Cleanup
- DB Connection Pool
- Docs Deploy
- Change Detection
- Plan UI & Feedback
- Overlap Redesign Plan
- Infrastructure Pruning
- Channel Metrics
- Queued Job IDs
- Non-Prod Items DB
- Key Expiry Pruning
- Old Job Pruning
- Unknown Term Recording
- Embedding Replace
- User CLI Keys
- Non-Prod Usage DB
- Chat Depth Tests
- Chat Evidence Tests
- Chat Live Tests
- Chat Resolve Tests
- Chat Integration Tests
- Docker Entrypoint
- Webhook Tasks
- CI Name Resolution
- Scan Deduplication
- OAuth Proxy
- Follow-Up Chips
- Item Facts Intent
- Advisor Sessions Schema
- Catalog Config Type
- Catalog Workload Type
- Analysis Time Windows
- CI Name Resolution Alt
- Duration Reranking
- Event URL Mode
- Haiku Triage
- Sonnet Recommendation
- Scan Pipeline Dedup
- React Frontend
- Analysis Recommendations
- OpenShift Deployment
- Async Advisor Query
- Recommender Redesign
- Token Usage Tracking
- List Persistence
- Catalog Visibility
- Rearchitecture Plan
- Overlap Assessment Plan
- LLM Overlap Assessment
- Exception Handling
- API Package Config
- Root Package Config
- Similarity Legacy
- Similarity DB Legacy
- Event Match Prompts
- Requirements Lock
- Similarity Test Legacy

## God Nodes (most connected - your core abstractions)
1. `Database` - 225 edges
2. `Settings` - 141 edges
3. `load_vocabulary()` - 64 edges
4. `normalize_analysis()` - 28 edges
5. `RouterOutput` - 26 edges
6. `parse_analysis_response()` - 25 edges
7. `seed_chat_fixtures()` - 25 edges
8. `_make_request()` - 24 edges
9. `call_llm()` - 24 edges
10. `get_current_user()` - 21 edges

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

## Communities (172 total, 60 thin omitted)

### Community 0 - "Auth & Role Management"
Cohesion: 0.05
Nodes (43): dict, _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), invalidate_role_assignments_cache(), _log_auth_decision(), _parse_sa_allowlist() (+35 more)

### Community 2 - "Analysis API Routes"
Cohesion: 0.07
Nodes (71): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_stale(), _extract_base_name_from_content_id(), get_workflow() (+63 more)

### Community 3 - "Advisor Chat UI"
Cohesion: 0.06
Nodes (42): BlockErrorBoundary, Props, State, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps (+34 more)

### Community 4 - "Frontend Dependencies"
Cohesion: 0.04
Nodes (48): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-core, @patternfly/react-icons, @patternfly/react-table (+40 more)

### Community 5 - "Catalog Service"
Cohesion: 0.07
Nodes (39): _apply_component_inheritance(), CatalogReader, _collect_bases(), component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata() (+31 more)

### Community 6 - "Catalog API Routes"
Cohesion: 0.14
Nodes (41): field_validator, add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis() (+33 more)

### Community 7 - "Recommender Pipeline"
Cohesion: 0.08
Nodes (18): parametrize, build_embedding_text(), Build text for CI-level embedding from analysis results., _build_expansion_map(), _expand_query_terms(), Invert the vocabulary's product aliases into term -> canonical name. Aliases…, Expand product names, acronyms, and synonyms for better embedding match. One…, clear_vocabulary_cache() (+10 more)

### Community 8 - "Admin & Health Routes"
Cohesion: 0.13
Nodes (33): add_role_assignment(), put, Admin routes — token usage, jobs, worker health, scheduled maintenance., resolve_vocabulary_unknown(), AddRoleAssignmentRequest, CatalogItemWorkload, CatalogListResponse, ErrorDetail (+25 more)

### Community 9 - "Retirement Workflow"
Cohesion: 0.07
Nodes (20): derive_status(), Retirement workflow business logic., Derive the workflow status from the highest completed step., Tests for retirement workflow business logic (derive_status)., Test derive_status with various step combinations., Validate STEP_ORDER constant structure., Retired should be first (highest priority), reviewed last., With no step timestamps, status defaults to 'reviewed'. (+12 more)

### Community 10 - "Overlap Assessment"
Cohesion: 0.09
Nodes (31): patch, assess_overlap(), _load_analysis_pair(), Assess overlap between two content items via LLM. Returns (assessment_dict,…, Validate LLM assessment response and coerce to canonical form. Returns None if…, Load showroom_analysis + content_entities for both items., _validate_assessment(), db() (+23 more)

### Community 11 - "Design Specs Archive"
Cohesion: 0.08
Nodes (34): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, Retirement Scoring Formula (0-100, Higher = Stronger Candidate), PatternFly 6 Migration Design, Navigation Restructure (Flattened Nav with Role-Gated Sections), RCARS Theme Architecture (Light/Dark Mode), Retirement Workflow Actions Design (+26 more)

### Community 12 - "Chat Intent Handlers"
Cohesion: 0.18
Nodes (29): _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_facts(), handle_overlap(), handle_performance(), handle_recommend(), HandlerResult (+21 more)

### Community 13 - "Showroom Git & Clone"
Cohesion: 0.10
Nodes (31): CompletedProcess, clone_showroom(), _is_github_throttle(), ls_remote_sha(), Run a git command with retry and exponential backoff for GitHub throttling., Get the current SHA for a ref without cloning. Returns None on failure., Batch-resolve git refs to commit SHAs via ls-remote. Groups pairs by URL so…, Shallow clone a Showroom repo. Returns clone path or None on failure. (+23 more)

### Community 14 - "Workers & Configuration"
Cohesion: 0.11
Nodes (23): asyncio, RedisSettings, fetch_litemaas_models(), Query LiteMaaS /v1/models endpoint once and cache the result., Sync reporting metrics from MCP server (standalone, not part of pipeline)., run_reporting_sync_job(), cleanup_orphaned_jobs(), arq worker settings — startup, shutdown, and task registration. (+15 more)

### Community 15 - "Workload Scanner"
Cohesion: 0.10
Nodes (28): generate_embedding(), Generate a 768-dim embedding via the vLLM embedding server. Nomic requires task…, analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products(), Path (+20 more)

### Community 16 - "Migration Scripts"
Cohesion: 0.16
Nodes (30): Connection, cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists() (+22 more)

### Community 17 - "Chat Router"
Cohesion: 0.15
Nodes (29): _prefix_overlap(), Count keyword matches allowing prefix matching for words >= min_prefix chars., RouterOutput, Scope, _find_keyword_ties(), _parse_catalog_url(), pattern_check(), Routing: pattern check, router LLM call (Task 9), resolve & verify ladder. (+21 more)

### Community 18 - "Vocabulary Generation"
Cohesion: 0.12
Nodes (24): _header_comment(), Emit a merged vocabulary.yaml — current file plus staged admin decisions.…, Preserve the active vocabulary file's leading comment block., Controlled vocabulary — one list, two consumers (analysis + query expansion)., _as_tuple(), _build_lookups(), _parse_entries(), Any (+16 more)

### Community 19 - "Database Tests"
Cohesion: 0.09
Nodes (15): db(), db_with_perf_data(), fixture, Seed test data for filtered catalog queries., Seed performance data for testing., _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider() (+7 more)

### Community 20 - "Recommender & DB Init"
Cohesion: 0.13
Nodes (21): datetime, PostgreSQL + pgvector database layer for RCARS v2., Three-phase recommendation pipeline with async progress callbacks., _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis(), _format_single_candidate(), generate_content_gaps() (+13 more)

### Community 21 - "Overlap Database"
Cohesion: 0.13
Nodes (25): overlap_candidates_cmd(), Generate overlap candidates via deterministic structural matching., generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), ConnectionPool, Deterministic overlap candidate generation via structured matching. (+17 more)

### Community 22 - "Database Lookups"
Cohesion: 0.08
Nodes (4): Any, Queue rows, ranked by occurrences descending. status=None returns all., Record an admin decision. Staged only — nothing about analysis changes until a…, Upsert a Babylon catalog item across content_entities + babylon_items in one…

### Community 23 - "Chat Evidence Pack"
Cohesion: 0.15
Nodes (20): integration, build_evidence_pack(), Evidence pack: v1 graph expansion — one hop, code-driven, bounded. The budget…, fake_embedding(), Seeded fixture catalog for chat tests (also a foundation for the broader…, Deterministic 768-dim unit vector from the text hash. Signature is monkeypatch-…, seed_chat_fixtures(), _settings() (+12 more)

### Community 24 - "Vocabulary Loader Tests"
Cohesion: 0.15
Nodes (9): load_vocabulary(), Load, validate, and cache the controlled vocabulary for this process., Snap one value to its canonical form. Returns (result, matched). On a miss the…, snap_term(), Punctuation and spacing differences resolve without a human., The spec's worked examples, wherever on the ladder they land., search_terms widen query expansion only — the normalizer ignores them., TestLoadPackagedDefault (+1 more)

### Community 25 - "Vocabulary Normalization"
Cohesion: 0.12
Nodes (13): _noise_variants(), normalize_analysis(), Any, Post-analysis normalization — deterministic, runs once after parse. Nothing…, Snap aliases to canonical forms and dedup topics, before write. Pure when db is…, Upsert one row per distinct term. Never touches the item's review flags., Rung 3 candidates: strip known noise, then retry rungs 1-2 on each., _record_unknowns() (+5 more)

### Community 26 - "Browse Page UI"
Cohesion: 0.10
Nodes (16): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, BrowsePage(), CatalogItem, catalogUrl() (+8 more)

### Community 27 - "Settings & Config Types"
Cohesion: 0.13
Nodes (13): BaseSettings, _parse_csv(), Settings, migrate(), test_admin_check(), test_chat_intent_roles_invalid_role_rejected(), test_chat_intent_roles_parse(), test_chat_model_defaults_follow_triage_and_rationale() (+5 more)

### Community 28 - "Controlled Vocabulary Data"
Cohesion: 0.10
Nodes (24): Action Verbs Validation Rules, Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy (+16 more)

### Community 29 - "Showroom Analyzer Core"
Cohesion: 0.14
Nodes (23): analyze_showroom(), build_module_embedding_text(), check_showroom_stale(), filter_boilerplate_files(), _get_embedding_client(), get_repo_head(), hash_showroom_content(), _parse_nav_includes() (+15 more)

### Community 30 - "Vocabulary Models"
Cohesion: 0.11
Nodes (15): Casefold and strip every non-alphanumeric character. One mechanism, two uses:…, True when an admin has rejected this term for this dimension., squash_key(), dedup_topics(), Collapse spelling variants of the same topic on the same item. Squash key…, Rung 1: exact match on canonical or alias, case-insensitive. Rung 2: squash key…, _rungs_1_2(), clear_vocabulary_cache() (+7 more)

### Community 31 - "API Key Management"
Cohesion: 0.12
Nodes (11): db(), _generate_key(), fixture, Tests for API key database CRUD operations., Ephemeral test database — uses RCARS_DATABASE_URL from env (rcars_test)., Generate a raw key, its hash, and its prefix., TestCreateApiKey, TestGetApiKeyByHash (+3 more)

### Community 32 - "Score Breakdown Popover"
Cohesion: 0.13
Nodes (18): fmt(), fmtRoi(), num(), scoreBg(), ScoreBreakdownPopover(), scoreColor(), stageBadgeClass, WorkflowItem (+10 more)

### Community 33 - "TypeScript Lib Defs"
Cohesion: 0.09
Nodes (22): DOM, DOM.Iterable, ES2020, src, compilerOptions, allowImportingTsExtensions, isolatedModules, jsx (+14 more)

### Community 34 - "Advisor API Routes"
Cohesion: 0.22
Nodes (22): _advisor_limit(), ChatRequest, get_query_result(), get_session(), list_sessions(), BaseModel, get, limit (+14 more)

### Community 35 - "Non-Prod Items"
Cohesion: 0.09
Nodes (10): Return {base_name: content_id} for items with no active prod-stage variant., Tests for get_nonprod_base_names — requires live DB with test data., Verify the nonprod routes exist on the analysis router., TestGetNonprodBaseNames, TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema (+2 more)

### Community 36 - "Duration Penalties"
Cohesion: 0.13
Nodes (19): _apply_duration_penalty(), _apply_usage_boost(), _extract_duration_target(), Candidate, QueryState, Apply a soft score penalty based on duration overshoot. Gentle: a 2x overshoot…, Boost relevance scores for candidates with proven usage. Looks up…, Extract a duration target (minutes) and whether it's a hard constraint. (+11 more)

### Community 37 - "Vocabulary Fixtures"
Cohesion: 0.09
Nodes (9): db(), fixture, Tests for the vocabulary_unknown_terms queue. Requires a live PostgreSQL., Vocabulary work never sets enrichment_review_needed or review_reasons., TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched (+1 more)

### Community 38 - "Redis & SSE Streaming"
Cohesion: 0.16
Nodes (17): Redis, create_sse_response(), JobProgressRelay, Redis pub/sub relay and SSE streaming for job progress., Subscribe to job progress. Yields message dicts, or None as keepalive., sse_stream(), translate_to_user_message(), asyncio (+9 more)

### Community 39 - "Admin Routes"
Cohesion: 0.17
Nodes (22): delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs(), list_role_assignments(), llm_provider_status() (+14 more)

### Community 40 - "Auth Routes"
Cohesion: 0.19
Nodes (21): auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), delete, get, limit (+13 more)

### Community 41 - "Reporting Sync"
Cohesion: 0.14
Nodes (21): _build_closed_sql(), _build_cost_sql(), _build_nonprod_provisions_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs() (+13 more)

### Community 42 - "CLI Arguments"
Cohesion: 0.16
Nodes (21): argument, command, flag(), get_db(), infra_stats(), note(), override_url(), Add an enrichment tag to a catalog item. (+13 more)

### Community 43 - "App Shell & Sidebar"
Cohesion: 0.14
Nodes (15): App(), RcarsSidebar(), AuthContext, AuthState, defaultState, useAuth(), useAuthProvider(), AdminQueriesPage() (+7 more)

### Community 44 - "Recent Jobs Page"
Cohesion: 0.12
Nodes (16): Job, RecentJobsPage(), CatalogStatus, InfraStats, StatusPage(), VocabularyPage(), api, MarketingMetrics (+8 more)

### Community 45 - "CLI Options"
Cohesion: 0.14
Nodes (19): group, option, cli(), infra_group(), init_db(), RCARS CLI — RHDP Content Advisory & Recommendation System., Show catalog status summary., RCARS — RHDP Content Advisory & Recommendation System. (+11 more)

### Community 46 - "Performance Scoring"
Cohesion: 0.16
Nodes (10): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), Compute sales impact tier from closed amount., Compute performance score 0-100 using percentile ranks. Higher = stronger…, Return the full score breakdown dict (factors + explanation)., Internal: compute score and return (breakdown_dict, final_score). (+2 more)

### Community 47 - "Auth Security Tests"
Cohesion: 0.11
Nodes (11): app_no_auth(), client(), fixture, parametrize, Security test suite for RCARS API authentication. Validates that all auth…, App with NO dev_user — all auth enforced., TestExpiredApiKey, TestRevokedApiKey (+3 more)

### Community 48 - "Dev Services"
Cohesion: 0.18
Nodes (18): frontend_only(), init_db(), RCARS_ADMIN_EMAILS_STR, RCARS_CURATOR_EMAILS_STR, RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL (+10 more)

### Community 49 - "Chat Sessions DB"
Cohesion: 0.15
Nodes (14): get_session_context(), log_chat_turn(), next_turn_index(), Any, Chat-session persistence and context building. Follows the db/similarity.py…, The router's view: last <=max_turns turns, fixed shape, no prose., session_owner_ok(), test_chat_append_checks_ownership() (+6 more)

### Community 50 - "Vocabulary Codegen"
Cohesion: 0.16
Nodes (10): _entries_to_dicts(), generate_vocabulary_yaml(), Any, Merge staged decisions into the loaded vocabulary and serialize. aliased → term…, clear_vocabulary_cache(), client(), fixture, Vocabulary generator + admin endpoints. (+2 more)

### Community 51 - "Ansible Deploy"
Cohesion: 0.13
Nodes (18): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+10 more)

### Community 52 - "OPL Vocabulary Sync"
Cohesion: 0.22
Nodes (17): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), Any (+9 more)

### Community 53 - "CLI Guide & Docs"
Cohesion: 0.15
Nodes (17): CLI Admin Guide, Evidence Pack, Infrastructure Intent, Content Overlap Detection, Cosine Similarity for Overlap, Score Bands, content_similarity Table, embeddings Table (+9 more)

### Community 54 - "FastAPI App Factory"
Cohesion: 0.18
Nodes (9): FastAPI, create_app(), lifespan(), client(), fixture, test_auth_me_unauthenticated(), client(), fixture (+1 more)

### Community 55 - "LLM Eval & Router"
Cohesion: 0.18
Nodes (15): llm_eval, _extract_json(), Strip code fences / leading prose, then parse. Raises on failure., route(), _fake(), test_call_error_falls_back(), test_hallucinated_intent_falls_back_to_recommend(), test_malformed_then_valid_retries_once() (+7 more)

### Community 56 - "Event Parser"
Cohesion: 0.16
Nodes (16): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), Any, Event URL parser. Fetches event web pages, follows links to…, Filter links to those that look like schedule/program/content pages. (+8 more)

### Community 57 - "CLI Print Helpers"
Cohesion: 0.14
Nodes (16): pass_context, _print(), Scan agDv2 workload repos and base configs via LLM., Sync reporting metrics from RHDP MCP server., Show reporting sync status and score distribution., Show performance metrics for a content entity (accepts ci_name, content_id, or…, List terms the normalizer could not match, ranked by occurrences., Stage the one-off Babylon re-scan that applies normalization corpus-wide. Marks… (+8 more)

### Community 58 - "Recommender Models"
Cohesion: 0.17
Nodes (12): Candidate, QueryState, Data models for the recommendation pipeline., A content entity moving through the recommendation pipeline., Convert similarity score (0.0-1.0) to percentage., State of a recommendation query at a pipeline phase boundary., format_triage_candidates(), Candidate (+4 more)

### Community 59 - "LLM Config"
Cohesion: 0.27
Nodes (11): _call_anthropic(), _call_litemaas(), call_llm(), LLMResult, Unified LLM call with automatic provider routing. LiteMaaS preferred if…, FakeLLM, _noop(), Queue of canned router/answer texts, FIFO. (+3 more)

### Community 60 - "Masthead Component"
Cohesion: 0.18
Nodes (12): API_DOCS_URL, DbStatus, formatAge(), getInitials(), RcarsMasthead(), applyTheme(), getInitialTheme(), Theme (+4 more)

### Community 61 - "Content Analysis Page"
Cohesion: 0.14
Nodes (9): ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment, OverlapItem, OverlapStats (+1 more)

### Community 62 - "Data Design Docs"
Cohesion: 0.14
Nodes (14): babylon_items Table, content_entities Table, performance_scores Table, retirement_workflow Table, showroom_analysis Table, Retirement Workflow, Performance Scoring Formula, Acronym Expansion (+6 more)

### Community 63 - "CLI Scan Commands"
Cohesion: 0.22
Nodes (13): Analyze Showroom content via Sonnet API., scan(), classify_scan_error(), Exception, Classify a scan error and return (error_class, human_message)., Clear old embeddings and store fresh ones for a content_id atomically. Returns…, regenerate_embeddings(), _propagate_to_sibling() (+5 more)

### Community 64 - "Chat Answer Builder"
Cohesion: 0.31
Nodes (11): build_scaffold(), compose_answer(), Deterministic scaffold + narrow narrative call. Worst case: mediocre prose next…, _help_answer(), process_turn(), The chat turn flow. LLM client injectable for the deterministic test tier., _scope_echo(), followup_chips() (+3 more)

### Community 65 - "Architecture Concepts"
Cohesion: 0.15
Nodes (13): Async Job Pattern, Green/Yellow/White Tier System, Three-Tier Rearchitecture, ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec (+5 more)

### Community 66 - "Auth Route Tests"
Cohesion: 0.15
Nodes (6): client(), fixture, Tests for API key management endpoints., TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 67 - "Recommendation Card"
Cohesion: 0.21
Nodes (11): Candidate, catalogUrl(), FORMAT_COLORS, FORMAT_LABELS, RecCard(), RecCardProps, HistoryPage(), SessionDetail (+3 more)

### Community 68 - "Content Model Concepts"
Cohesion: 0.20
Nodes (12): Content Model Normalization, Intent-Based Chat Routing, Overlap Analysis Redesign, Performance Scoring Formula, Reporting MCP Data Sync, Retirement Workflow, Retirement Analysis Integration Plan, Retirement Workflow Actions Plan (+4 more)

### Community 69 - "Vocabulary Renderer"
Cohesion: 0.26
Nodes (5): Build the injected block for a given content_entities.content_type., render_vocabulary_block(), Only products and verb hints go into the prompt., The block is spliced into a template that cannot use str.format()., TestRenderVocabularyBlock

### Community 70 - "Vocabulary Path Tests"
Cohesion: 0.32
Nodes (4): Every document is built from one helper so indentation stays uniform —…, TestPathOverride, TestValidation, write_vocab()

### Community 71 - "Log Window Component"
Cohesion: 0.18
Nodes (5): LogWindow(), LogWindowProps, ActionState, ScheduleInfo, SyncPage()

### Community 72 - "Base Name Extraction"
Cohesion: 0.27
Nodes (3): extract_base_name(), Strip stage suffix from an RCARS ci_name to get the reporting DB base name., TestExtractBaseName

### Community 73 - "Analysis Prompt Builder"
Cohesion: 0.20
Nodes (6): build_analysis_prompt(), Truncate content to max characters., Build analysis prompt split into system instructions and user data.…, truncate_content(), build_analysis_prompt slices the template; only the Instructions section…, TestPromptInjection

### Community 74 - "Analysis Response Parser"
Cohesion: 0.33
Nodes (10): parse_analysis_response(), Parse Sonnet's JSON response, handling markdown fences., test_dict(), test_empty_returns_none(), test_fenced_json(), test_list(), test_scalar_bool_returns_none(), test_scalar_int_returns_none() (+2 more)

### Community 75 - "Chat Handler Registry"
Cohesion: 0.45
Nodes (10): _noop(), Verify handler returns notice when no embeddings match., Verify handler uses embedding search, not list_infrastructure., _res(), _settings(), test_infrastructure_handler_no_match_returns_notice(), test_infrastructure_handler_uses_embedding_search(), test_item_facts_handler() (+2 more)

### Community 76 - "Operations Docs"
Cohesion: 0.22
Nodes (10): Worker Management, Advisor Chat System, performance_channels Table, Cost Methodology, Performance Analysis, RHDP Reporting MCP Server, Recommend Worker, Non-Prod Items Page Plan (+2 more)

### Community 77 - "Architecture Reference"
Cohesion: 0.20
Nodes (10): API Reference, Babylon Kubernetes CRDs, FastAPI API, LiteMaaS LLM Provider, Nightly Maintenance Pipeline, PostgreSQL with pgvector, Scan Worker, Vertex AI LLM Provider (+2 more)

### Community 78 - "MCP Query Sync"
Cohesion: 0.29
Nodes (7): _mcp_call(), mcp_query(), Call an MCP tool via HTTP JSON-RPC, return parsed JSON result., Execute SQL via MCP server, auto-paginating past 500-row cap., patch, Build a mock urllib response for an MCP query result., TestMcpPagination

### Community 79 - "Overlap Assessment Build"
Cohesion: 0.28
Nodes (8): _build_assessment_prompt(), _coerce_list(), _fmt_json_field(), Any, LLM-based overlap assessment for content similarity pairs., Coerce value to string list. None→[], str→[str], list→filtered strings, else→[]., Format JSONB field for prompt. None/empty → 'None available'., Build overlap assessment prompt from template.

### Community 80 - "Windowed Metrics"
Cohesion: 0.28
Nodes (6): _build_windowed_metrics(), Build per-item windowed_metrics JSONB from per-window query results. For each…, Windowed metrics should have entries for all four windows., An item with zero provisions/sales in a window should score 0., Items with different provision counts should get different scores., TestBuildWindowedMetrics

### Community 81 - "Infrastructure CLI"
Cohesion: 0.25
Nodes (4): clean_infra(), db(), fixture, Tests for infrastructure table DB operations.

### Community 82 - "Structured Logging"
Cohesion: 0.50
Nodes (6): BoundLogger, _add_component(), get_logger(), setup_logging(), test_logger_outputs_json(), test_logger_with_job_id()

### Community 83 - "Infrastructure Tests"
Cohesion: 0.29
Nodes (4): client(), fixture, Tests for GET /catalog/infrastructure endpoint and removal of old workload-…, seed_infrastructure()

### Community 85 - "Workflow & Non-Prod UI"
Cohesion: 0.25
Nodes (7): WorkflowDrawer(), NonProdItemsPage(), SortField, stageBadgeClass, StatusFilter, TimeWindow, NonProdItem

### Community 86 - "Login CLI"
Cohesion: 0.54
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 87 - "CLAUDE.md Docs"
Cohesion: 0.57
Nodes (7): RCARS Architecture (4 Deployments), FastAPI 2.0 API (uvicorn), React 19 SPA Frontend (PatternFly 6), PostgreSQL with pgvector (768-dim embeddings), Recommend Worker (arq:queue:recommend), Redis (Job Queue + Pub/Sub), Scan Worker (arq:queue:scan)

### Community 88 - "UI Design Concepts"
Cohesion: 0.33
Nodes (7): Infrastructure-Aware Catalog Metadata, PatternFly 6 Theme Architecture, Server-Side Filtering, Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 89 - "Auth Design Specs"
Cohesion: 0.38
Nodes (7): API Authentication Design, API Key Authentication (X-API-Key Header), OAuth PKCE Login Flow, Proxy Verification Secret (Anti-Spoofing), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 90 - "Vector Search"
Cohesion: 0.29
Nodes (7): QueryState, Generate query embedding, search pgvector, apply quality threshold. The DB…, Remove grammatical filler words before embedding to reduce dilution., Find CI references in the query and return neighbors based on the referenced…, _resolve_ci_references(), search(), _strip_embedding_filler()

### Community 91 - "Reporting Window Tests"
Cohesion: 0.38
Nodes (3): Return the start date for a sliding window (today - N days)., _window_start(), TestWindowStart

### Community 92 - "Chat Tests"
Cohesion: 0.33
Nodes (4): client(), non_admin_client(), fixture, Tests for POST /advisor/chat endpoint.

### Community 93 - "Login Shell Scripts"
Cohesion: 0.48
Nodes (5): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token()

### Community 94 - "Chat Intent Types"
Cohesion: 0.33
Nodes (6): Overlap Intent, Performance Intent, Recommend Intent, Chat Router LLM, Recommendation Engine, RCARS System

### Community 95 - "Chat Registry"
Cohesion: 0.33
Nodes (4): build_router_prompt(), test_examples_validate_as_router_output(), test_followup_chips_are_pre_routed(), test_prompt_contains_every_intent_and_context()

### Community 96 - "Request Logging"
Cohesion: 0.40
Nodes (3): BaseHTTPMiddleware, Request, RequestLoggingMiddleware

### Community 97 - "Infrastructure Embeddings"
Cohesion: 0.60
Nodes (4): build_infrastructure_embedding_text(), Build text for infrastructure embedding from an infrastructure table row., test_build_infrastructure_embedding_text(), test_build_infrastructure_embedding_text_minimal()

### Community 98 - "API Keys Panel"
Cohesion: 0.60
Nodes (4): ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo()

### Community 99 - "Backlog & Jira"
Cohesion: 0.50
Nodes (4): Backlog Jira Migration, RCARS Project Instructions, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 100 - "API Key Auth Design"
Cohesion: 0.67
Nodes (4): API Key Authentication, OpenShift Group-Based Auth, API Authentication Plan, OpenShift Group Auth Plan

### Community 101 - "Rate Limiting"
Cohesion: 0.50
Nodes (3): _get_user_key(), Request, Per-user rate limiting via slowapi + Redis.

### Community 102 - "Health Endpoint"
Cohesion: 0.50
Nodes (4): health(), get, Request, readiness()

### Community 105 - "Schema & Scoring Docs"
Cohesion: 0.67
Nodes (3): Database Schema (15 tables, SCHEMA_SQL), Performance Scoring Formula (4 Factors, Max ~80), Soft-Delete Pattern (retired_at)

### Community 106 - "Duration Best-Fit"
Cohesion: 0.67
Nodes (3): Curated Duration Override, Rec Card Duration and Best Fit Plan, Rec Card Duration and Best Fit Spec

### Community 107 - "MkDocs Config"
Cohesion: 0.67
Nodes (3): MkDocs Material Theme Configuration, Architecture Documentation Section, RCARS Documentation Site (MkDocs)

## Knowledge Gaps
- **216 isolated node(s):** `rcars`, `rcars`, `docker-entrypoint.sh script`, `PaginationProps`, `WorkloadMultiSelectProps` (+211 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **60 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database Core` to `Chat Integration Tests`, `Overlap Assessment`, `Chat Intent Handlers`, `Showroom Git & Clone`, `Workers & Configuration`, `Workload Scanner`, `Chat Router`, `Database Tests`, `Recommender & DB Init`, `Overlap Database`, `Database Lookups`, `Chat Evidence Pack`, `Settings & Config Types`, `API Key Management`, `Non-Prod Items`, `Duration Penalties`, `Vocabulary Fixtures`, `CLI Arguments`, `CLI Options`, `Chat Sessions DB`, `FastAPI App Factory`, `CLI Print Helpers`, `LLM Config`, `Chat Answer Builder`, `Base Name Extraction`, `Infrastructure CLI`, `Infrastructure Tests`, `Vector Search`, `Job Completion`, `Retirement Cleanup`, `DB Connection Pool`, `Infrastructure Pruning`, `Channel Metrics`, `Queued Job IDs`, `Non-Prod Items DB`, `Key Expiry Pruning`, `Old Job Pruning`, `Unknown Term Recording`, `Embedding Replace`, `User CLI Keys`, `Non-Prod Usage DB`, `Chat Depth Tests`, `Chat Evidence Tests`, `Chat Live Tests`, `Chat Resolve Tests`?**
  _High betweenness centrality (0.178) - this node is a cross-community bridge._
- **Why does `Settings` connect `Settings & Config Types` to `Auth & Role Management`, `Analysis API Routes`, `Catalog API Routes`, `Admin & Health Routes`, `Overlap Assessment`, `Chat Intent Handlers`, `Showroom Git & Clone`, `Workers & Configuration`, `Workload Scanner`, `Chat Router`, `Recommender & DB Init`, `Chat Evidence Pack`, `Showroom Analyzer Core`, `Advisor API Routes`, `Duration Penalties`, `Admin Routes`, `Auth Routes`, `CLI Arguments`, `CLI Options`, `Auth Security Tests`, `Vocabulary Codegen`, `FastAPI App Factory`, `LLM Eval & Router`, `CLI Print Helpers`, `LLM Config`, `CLI Scan Commands`, `Chat Answer Builder`, `Auth Route Tests`, `Chat Handler Registry`, `Overlap Assessment Build`, `Infrastructure Tests`, `Vocabulary Admin Tests`, `Chat Tests`, `Token Exchange Tests`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Why does `load_vocabulary()` connect `Vocabulary Loader Tests` to `Vocabulary Renderer`, `Vocabulary Path Tests`, `Admin Routes`, `Admin & Health Routes`, `Analysis Prompt Builder`, `Recommender Pipeline`, `Workload Scanner`, `Vocabulary Generation`, `Vocabulary Codegen`, `Recommender & DB Init`, `Vocabulary Normalization`, `Showroom Analyzer Core`, `Vocabulary Models`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `Database` (e.g. with `HandlerResult` and `Resolution`) actually correct?**
  _`Database` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `Settings` (e.g. with `ChatRequest` and `QueryRequest`) actually correct?**
  _`Settings` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `docker-entrypoint.sh script` to the rest of the system?**
  _216 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Auth & Role Management` be split into smaller, more focused modules?**
  _Cohesion score 0.05327281414237936 - nodes in this community are weakly interconnected._