# Graph Report - .  (2026-08-07)

## Corpus Check
- 228 files · ~333,529 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1785 nodes · 3832 edges · 103 communities (81 shown, 22 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 276 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Chat Sessions & Context
- Auth Middleware
- Database Core
- Analysis & Advisor Routes
- CLI Commands
- Logging & Redis Config
- Catalog Routes
- Advisor Card Components
- Frontend Dependencies
- Content Similarity
- Retirement & PF6 Specs
- Retirement Workflow
- Showroom Analyzer
- Content Migration Scripts
- Embeddings & LLM Client
- Catalog Service
- Query Expansion & Terms
- Jira Integration
- Database Tests
- Admin Routes & Schemas
- Recommender Pipeline
- App Settings
- Admin & Jobs Pages
- Admin API Endpoints
- Pagination & UI Controls
- Auth Routes & API Keys
- FastAPI App Setup
- Database Item Lookups
- TypeScript Config
- Advisor Routes
- Score Breakdown Popover
- LLM Provider Config
- API Key Tests
- Performance Scoring
- Auth Security Tests
- Event Parser
- Frontend App Shell
- Dev Services
- Chat Router & DB
- Reporting SQL Builders
- LLM Calls & Workloads
- Masthead Component
- CI/CD & Concepts
- Architecture Concepts
- Auth Route Tests
- Recommendation Cards
- System Design Concepts
- Log & Sync Pages
- Ansible Deployment
- Base Name Extraction
- Content Analysis Page
- Scan Worker
- Reporting MCP Client
- Duration & Triage Concepts
- Early Design Specs
- Chat Architecture Docs
- Data & Performance Docs
- Recommendation Docs
- System Design Docs
- Windowed Metrics
- Overlap & Similarity Docs
- Chat Answer Service
- Login CLI (Python)
- CLAUDE.md Architecture
- Browse & PF6 Plans
- Scan Pipeline Docs
- Auth Design Specs
- Health Routes
- Time Window Tests
- Login CLI (Shell)
- Request Logging
- Project Management
- Auth Evolution Plans
- Rate Limiting
- Token Exchange Tests
- Retirement DB Ops
- DB Connection Pool
- API Key Test Fixtures
- Channel Metrics
- API Key Pruning
- Job Pruning
- CLI Key Revocation
- Requirements Files
- Chat Depth Fixtures
- Chat Evidence Fixtures
- Chat Live Fixtures
- Chat Resolve Fixtures
- Session DB Fixtures
- Chat Integration Fixtures
- Docker Entrypoint
- Webhooks Task
- CI Name Resolution
- Root Package
- API Package
- Event Match Prompt

## God Nodes (most connected - your core abstractions)
1. `Database` - 188 edges
2. `Settings` - 117 edges
3. `compute_content_similarity()` - 29 edges
4. `JobProgressRelay` - 26 edges
5. `RouterOutput` - 26 edges
6. `seed_chat_fixtures()` - 25 edges
7. `_make_request()` - 24 edges
8. `get_current_user()` - 21 edges
9. `get_db()` - 21 edges
10. `call_llm()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Build Frontend Task` --implements--> `React 19 SPA Frontend (PatternFly 6)`  [INFERRED]
  ansible/tasks/build-frontend.yml → CLAUDE.md
- `Build API Task` --implements--> `FastAPI 2.0 API (uvicorn)`  [INFERRED]
  ansible/tasks/build-api.yml → CLAUDE.md
- `Worker Management / Operations Guide` --references--> `Scan Worker (arq:queue:scan)`  [INFERRED]
  docs/admin/operations.md → CLAUDE.md
- `Advisor Smoke Test Task` --references--> `Recommend Worker (arq:queue:recommend)`  [INFERRED]
  ansible/tasks/smoke-test.yml → CLAUDE.md
- `Worker Management / Operations Guide` --references--> `Recommend Worker (arq:queue:recommend)`  [INFERRED]
  docs/admin/operations.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Ansible Deployment Pipeline** — ansible_deploy_playbook, ansible_tasks_apply_infra, ansible_tasks_apply_manifests, ansible_tasks_build_api, ansible_tasks_build_frontend, ansible_tasks_smoke_test, ansible_tasks_namespace, ansible_vars_common [EXTRACTED 1.00]
- **RCARS Four-Component Architecture** — claude_md_frontend, claude_md_fastapi_api, claude_md_scan_worker, claude_md_recommend_worker, claude_md_postgresql_pgvector, claude_md_redis [EXTRACTED 1.00]
- **MkDocs Documentation Site** — mkdocs_config, requirements_docs, _github_workflows_docs_deploy_docs, docs_index, docs_overview, docs_admin_deployment, docs_admin_cli_guide, docs_admin_operations, docs_admin_token_usage [EXTRACTED 1.00]
- **Three-Phase Recommendation Pipeline** — docs_architecture_recommendation_engine_vector_search, docs_architecture_recommendation_engine_haiku_triage, docs_architecture_recommendation_engine_sonnet_rationale, docs_architecture_recommendation_engine [EXTRACTED 1.00]
- **Three-Tier System Architecture** — docs_architecture_system_design, docs_architecture_system_design_worker_split, docs_architecture_system_design_nightly_pipeline, docs_architecture_api_reference [EXTRACTED 1.00]
- **Content Lifecycle Pipeline** — docs_architecture_scan_pipeline, docs_architecture_content_overlap, docs_architecture_performance_analysis, docs_architecture_performance_analysis_retirement_workflow [INFERRED 0.85]
- **System Evolution from Monolith to Multi-Tier** — docs_superpowers_specs_2026-04-07-eca-production-redesign-design, docs_superpowers_specs_2026-04-08-rcars-plan3a-web-ui-design, docs_superpowers_specs_2026-04-25-rearchitecture-api-design, concept_rearchitecture [EXTRACTED 0.95]
- **Authentication and Authorization Evolution** — concept_api_key_auth, concept_openshift_group_auth, docs_superpowers_plans_2026-07-03-api-authentication, docs_superpowers_plans_2026-08-05-openshift-group-auth [INFERRED 0.85]
- **Performance Analysis Feature Stack** — concept_reporting_mcp_sync, concept_performance_scoring, concept_retirement_workflow, docs_superpowers_plans_2026-08-04-performance-page [EXTRACTED 0.95]
- **Recommendation Pipeline LLM Prompts** — src_api_rcars_prompts_triage, src_api_rcars_prompts_rationale, src_api_rcars_prompts_rationale_single, src_api_rcars_prompts_rationale_synthesis, src_api_rcars_data_product_terms [INFERRED 0.95]
- **Generalized Content Model Core Tables** — docs_superpowers_specs_2026_07_20_generalized_content_model_design_content_entities, docs_superpowers_specs_2026_07_20_generalized_content_model_design_babylon_items, docs_superpowers_specs_2026_07_20_generalized_content_model_design_embeddings, docs_superpowers_specs_2026_07_20_generalized_content_model_design_performance_channels [EXTRACTED 1.00]
- **Authentication and Access Control System** — docs_superpowers_specs_2026_07_03_api_authentication_design_api_keys, docs_superpowers_specs_2026_07_03_api_authentication_design_oauth_login, docs_superpowers_specs_2026_07_03_api_authentication_design_proxy_verification, docs_superpowers_specs_2026_08_05_role_assignments_design_role_assignments_table [INFERRED 0.95]

## Communities (103 total, 22 thin omitted)

### Community 0 - "Chat Sessions & Context"
Cohesion: 0.05
Nodes (91): integration, get_item_workloads(), get_performance_scores(), get_session_context(), log_chat_turn(), next_turn_index(), Any, Chat-session persistence and context building. Follows the db/similarity.py… (+83 more)

### Community 1 - "Auth Middleware"
Cohesion: 0.06
Nodes (42): dict, _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), _log_auth_decision(), _parse_sa_allowlist(), Request (+34 more)

### Community 3 - "Analysis & Advisor Routes"
Cohesion: 0.08
Nodes (58): Redis, stream_query(), analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_stale() (+50 more)

### Community 4 - "CLI Commands"
Cohesion: 0.07
Nodes (62): argument, command, group, option, pass_context, cli(), compute_similarity_cmd(), flag() (+54 more)

### Community 5 - "Logging & Redis Config"
Cohesion: 0.07
Nodes (41): BoundLogger, RedisSettings, _add_component(), get_logger(), setup_logging(), candidates_with_performance(), Result serialization shared by the recommend worker and the chat layer., Convert QueryState candidates to JSON dicts with performance metrics. Exact… (+33 more)

### Community 6 - "Catalog Routes"
Cohesion: 0.13
Nodes (50): field_validator, add_tag(), add_workload_mapping(), catalog_facets(), catalog_stats(), ContentPathRequest, delete_workload_mapping(), DurationRequest (+42 more)

### Community 7 - "Advisor Card Components"
Cohesion: 0.08
Nodes (37): catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps, catalogUrl(), OverlapNeighbor (+29 more)

### Community 8 - "Frontend Dependencies"
Cohesion: 0.04
Nodes (48): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-core, @patternfly/react-icons, @patternfly/react-table (+40 more)

### Community 9 - "Content Similarity"
Cohesion: 0.09
Nodes (42): _build_similar_item(), compute_content_similarity(), get_overlap_items(), get_similar_items(), get_similarity_stats(), Any, ConnectionPool, Content similarity computation and queries. Extracted from database.py to start… (+34 more)

### Community 10 - "Retirement & PF6 Specs"
Cohesion: 0.07
Nodes (37): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, Retirement Scoring Formula (0-100, Higher = Stronger Candidate), PatternFly 6 Migration Design, Navigation Restructure (Flattened Nav with Role-Gated Sections), RCARS Theme Architecture (Light/Dark Mode), Retirement Workflow Actions Design (+29 more)

### Community 11 - "Retirement Workflow"
Cohesion: 0.07
Nodes (20): derive_status(), Retirement workflow business logic., Derive the workflow status from the highest completed step., Tests for retirement workflow business logic (derive_status)., Test derive_status with various step combinations., Validate STEP_ORDER constant structure., Retired should be first (highest priority), reviewed last., With no step timestamps, status defaults to 'reviewed'. (+12 more)

### Community 12 - "Showroom Analyzer"
Cohesion: 0.10
Nodes (33): CompletedProcess, analyze_showroom(), build_analysis_prompt(), build_module_embedding_text(), check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), get_repo_head() (+25 more)

### Community 13 - "Content Migration Scripts"
Cohesion: 0.16
Nodes (30): Connection, cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists() (+22 more)

### Community 14 - "Embeddings & LLM Client"
Cohesion: 0.10
Nodes (23): generate_embedding(), _get_embedding_client(), Lazy-init a shared httpx client for the vLLM embedding server., Generate a 768-dim embedding via the vLLM embedding server. Nomic requires task…, Candidate, QueryState, Data models for the recommendation pipeline., A content entity moving through the recommendation pipeline. (+15 more)

### Community 15 - "Catalog Service"
Cohesion: 0.11
Nodes (25): CatalogReader, component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata(), extract_showroom_url(), _get_label() (+17 more)

### Community 16 - "Query Expansion & Terms"
Cohesion: 0.12
Nodes (9): build_embedding_text(), Build text for CI-level embedding from analysis results., _expand_query_terms(), _load_product_terms(), Load product term mappings from the bundled YAML file. Returns (acronyms,…, Expand product acronyms and synonyms for better embedding match., TestBuildEmbeddingText, TestExpandQueryTerms (+1 more)

### Community 17 - "Jira Integration"
Cohesion: 0.13
Nodes (27): _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _jira_request(), Jira REST API client for retirement ticket creation. Uses urllib (consistent…, Create a Jira retirement ticket. Returns the new Jira issue key (e.g.…, Make an HTTP request to the Jira REST API v3 with Basic auth. Returns parsed…, Derive catalog base name from content_id (e.g. 'babylon:foo.prod' → 'foo'). (+19 more)

### Community 18 - "Database Tests"
Cohesion: 0.09
Nodes (15): db(), db_with_perf_data(), fixture, Seed test data for filtered catalog queries., Seed performance data for testing., _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider() (+7 more)

### Community 19 - "Admin Routes & Schemas"
Cohesion: 0.16
Nodes (26): Admin routes — token usage, jobs, worker health, scheduled maintenance., CatalogItemWorkload, CatalogListResponse, ErrorDetail, HealthChecks, JobListResponse, LlmProviderResponse, OverlapItemsResponse (+18 more)

### Community 20 - "Recommender Pipeline"
Cohesion: 0.12
Nodes (26): _apply_duration_penalty(), _apply_usage_boost(), _extract_duration_target(), extract_urls(), Candidate, Three-phase recommendation pipeline with async progress callbacks., Apply a soft score penalty based on duration overshoot. Gentle: a 2x overshoot…, Boost relevance scores for candidates with proven usage. Looks up… (+18 more)

### Community 21 - "App Settings"
Cohesion: 0.11
Nodes (16): BaseSettings, _parse_csv(), Settings, migrate(), One-time migration: export token_usage from old schema, create new schema,…, fixture, settings(), test_admin_check() (+8 more)

### Community 22 - "Admin & Jobs Pages"
Cohesion: 0.09
Nodes (20): QuerySessionSummary, SessionTurn, TokenStats, Job, RecentJobsPage(), CatalogStatus, InfraStats, StatusPage() (+12 more)

### Community 23 - "Admin API Endpoints"
Cohesion: 0.15
Nodes (24): invalidate_role_assignments_cache(), add_role_assignment(), compute_similarity(), delete_role_assignment(), get_job(), list_jobs(), list_role_assignments(), llm_provider_status() (+16 more)

### Community 24 - "Pagination & UI Controls"
Cohesion: 0.10
Nodes (16): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, BrowsePage(), CatalogItem, catalogUrl() (+8 more)

### Community 25 - "Auth Routes & API Keys"
Cohesion: 0.17
Nodes (23): datetime, invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), delete (+15 more)

### Community 26 - "FastAPI App Setup"
Cohesion: 0.13
Nodes (13): FastAPI, create_app(), lifespan(), client(), fixture, test_auth_me_unauthenticated(), client(), fixture (+5 more)

### Community 28 - "TypeScript Config"
Cohesion: 0.09
Nodes (22): DOM, DOM.Iterable, ES2020, src, compilerOptions, allowImportingTsExtensions, isolatedModules, jsx (+14 more)

### Community 29 - "Advisor Routes"
Cohesion: 0.21
Nodes (22): _advisor_limit(), ChatRequest, get_query_result(), get_session(), list_sessions(), BaseModel, get, limit (+14 more)

### Community 30 - "Score Breakdown Popover"
Cohesion: 0.17
Nodes (17): fmt(), fmtRoi(), num(), scoreBg(), ScoreBreakdownPopover(), scoreColor(), stageBadgeClass, WorkflowDrawer() (+9 more)

### Community 31 - "LLM Provider Config"
Cohesion: 0.16
Nodes (15): llm_eval, _call_anthropic(), _call_litemaas(), LLMResult, route(), _fake(), test_call_error_falls_back(), test_hallucinated_intent_falls_back_to_recommend() (+7 more)

### Community 32 - "API Key Tests"
Cohesion: 0.14
Nodes (8): _generate_key(), Tests for API key database CRUD operations., Generate a raw key, its hash, and its prefix., TestCreateApiKey, TestGetApiKeyByHash, TestListApiKeys, TestRevokeApiKey, TestTouchApiKey

### Community 33 - "Performance Scoring"
Cohesion: 0.16
Nodes (10): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), compute_sales_impact(), Compute sales impact tier from closed amount., Compute performance score 0-100 using percentile ranks. Higher = stronger…, Return the full score breakdown dict (factors + explanation)., Internal: compute score and return (breakdown_dict, final_score). (+2 more)

### Community 34 - "Auth Security Tests"
Cohesion: 0.11
Nodes (11): app_no_auth(), client(), fixture, parametrize, Security test suite for RCARS API authentication. Validates that all auth…, App with NO dev_user — all auth enforced., TestExpiredApiKey, TestRevokedApiKey (+3 more)

### Community 35 - "Event Parser"
Cohesion: 0.15
Nodes (18): parse_analysis_response(), Parse Sonnet's JSON response, handling markdown fences., _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), Any (+10 more)

### Community 36 - "Frontend App Shell"
Cohesion: 0.16
Nodes (15): App(), ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), useAuthProvider(), applyTheme(), getInitialTheme() (+7 more)

### Community 37 - "Dev Services"
Cohesion: 0.18
Nodes (17): init_db(), RCARS_ADMIN_EMAILS_STR, RCARS_CURATOR_EMAILS_STR, RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 38 - "Chat Router & DB"
Cohesion: 0.14
Nodes (15): _prefix_overlap(), PostgreSQL + pgvector database layer for RCARS v2., Count keyword matches allowing prefix matching for words >= min_prefix chars., _extract_json(), _find_keyword_ties(), _parse_catalog_url(), pattern_check(), Routing: pattern check, router LLM call (Task 9), resolve & verify ladder. (+7 more)

### Community 39 - "Reporting SQL Builders"
Cohesion: 0.18
Nodes (17): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs(), _percentile_rank() (+9 more)

### Community 40 - "LLM Calls & Workloads"
Cohesion: 0.20
Nodes (14): call_llm(), Unified LLM call with automatic provider routing. LiteMaaS preferred if…, ls_remote_sha(), Get the current SHA for a ref without cloning. Returns None on failure., analyze_role(), discover_roles(), Path, Workload repo scanner — clone agDv2 collection repos, read role code, LLM-… (+6 more)

### Community 41 - "Masthead Component"
Cohesion: 0.20
Nodes (11): API_DOCS_URL, DbStatus, formatAge(), getInitials(), RcarsMasthead(), RcarsSidebar(), AuthContext, AuthState (+3 more)

### Community 42 - "CI/CD & Concepts"
Cohesion: 0.24
Nodes (13): Deploy Docs GitHub Actions Workflow, Scan Deduplication (git ls-remote + SHA), dev-services.sh Local Development Launcher, Nightly Maintenance Pipeline (5 Steps), Token Usage Tracking (5 Operation Types), CLI Admin Guide, Deployment Guide, Worker Management / Operations Guide (+5 more)

### Community 43 - "Architecture Concepts"
Cohesion: 0.17
Nodes (13): Database Schema (15 tables, SCHEMA_SQL), Performance Scoring Formula (4 Factors, Max ~80), Soft-Delete Pattern (retired_at), AgnosticD v2 (Infrastructure Config), Babylon Platform (K8s CRDs), Content Overlap Detection (Cosine Similarity), LiteMaaS (Internal Red Hat LLM Proxy), OpenShift OAuth Proxy (Red Hat SSO) (+5 more)

### Community 44 - "Auth Route Tests"
Cohesion: 0.15
Nodes (6): client(), fixture, Tests for API key management endpoints., TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 45 - "Recommendation Cards"
Cohesion: 0.21
Nodes (11): Candidate, catalogUrl(), FORMAT_COLORS, FORMAT_LABELS, RecCard(), RecCardProps, HistoryPage(), SessionDetail (+3 more)

### Community 46 - "System Design Concepts"
Cohesion: 0.20
Nodes (12): Content Model Normalization, Intent-Based Chat Routing, Overlap Analysis Redesign, Performance Scoring Formula, Reporting MCP Data Sync, Retirement Workflow, Retirement Analysis Integration Plan, Retirement Workflow Actions Plan (+4 more)

### Community 47 - "Log & Sync Pages"
Cohesion: 0.18
Nodes (5): LogWindow(), LogWindowProps, ActionState, ScheduleInfo, SyncPage()

### Community 48 - "Ansible Deployment"
Cohesion: 0.22
Nodes (11): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+3 more)

### Community 49 - "Base Name Extraction"
Cohesion: 0.27
Nodes (3): extract_base_name(), Strip stage suffix from an RCARS ci_name to get the reporting DB base name., TestExtractBaseName

### Community 50 - "Content Analysis Page"
Cohesion: 0.20
Nodes (7): ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapItem, OverlapStats

### Community 51 - "Scan Worker"
Cohesion: 0.27
Nodes (9): Exception, classify_scan_error(), Classify a scan error and return (error_class, human_message)., _propagate_to_sibling(), Analysis/scan worker tasks., Strip LLM-hallucinated keys from format_suitability — only demo and…, Propagate analysis + embeddings to a single sibling CI., run_analysis() (+1 more)

### Community 52 - "Reporting MCP Client"
Cohesion: 0.29
Nodes (7): _mcp_call(), mcp_query(), Call an MCP tool via HTTP JSON-RPC, return parsed JSON result., Execute SQL via MCP server, auto-paginating past 500-row cap., patch, Build a mock urllib response for an MCP query result., TestMcpPagination

### Community 53 - "Duration & Triage Concepts"
Cohesion: 0.22
Nodes (9): Advisor Smoke Test Task, Green/Yellow/White Tier System, Curated Duration Override, Three-Phase Recommendation Pipeline, Rec Card Duration and Best Fit Plan, Recommender Three-Phase Pipeline Spec, Token Usage Tracking Spec, Advisor List Persistence and Feedback Spec (+1 more)

### Community 54 - "Early Design Specs"
Cohesion: 0.22
Nodes (9): Async Job Pattern, Three-Tier Rearchitecture, ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec, Scan Failures and Catalog Visibility Spec (+1 more)

### Community 55 - "Chat Architecture Docs"
Cohesion: 0.22
Nodes (9): Advisor Chat Architecture, Evidence Pack, Multi-Intent Chat Routing, Scope Resolution, API Reference, Async Job Pattern, Handoff: Advisor Gen-2 Multi-Intent Chat, Plan: Async Advisor Query (+1 more)

### Community 56 - "Data & Performance Docs"
Cohesion: 0.25
Nodes (9): Data Design, Content Model (Two-Table Design), Soft-Delete Pattern, Performance Analysis, Cost Amortization Methodology, Retirement Workflow, Percentile-Based Performance Scoring, Performance Time Windows (+1 more)

### Community 57 - "Recommendation Docs"
Cohesion: 0.22
Nodes (9): Recommendation Engine, Duration-Aware Reranking, Event URL Mode, Phase 2 Haiku Triage, Phase 3 Sonnet Rationale, Plan 3a: Web UI Implementation, Plan: Admin Action Feedback, Plan: Recommender Redesign (Three-Phase Pipeline) (+1 more)

### Community 58 - "System Design Docs"
Cohesion: 0.22
Nodes (9): System Design, Babylon CRD Data Source, LLM Provider Routing, Nightly Maintenance Pipeline, Worker Split Architecture, Plan 1: Foundation and Catalog Reader, Plan 3c: OpenShift Deployment, Plan: Token Usage Tracking (+1 more)

### Community 59 - "Windowed Metrics"
Cohesion: 0.28
Nodes (6): _build_windowed_metrics(), Build per-item windowed_metrics JSONB from per-window query results. For each…, Windowed metrics should have entries for all four windows., An item with zero provisions/sales in a window should score 0., Items with different provision counts should get different scores., TestBuildWindowedMetrics

### Community 60 - "Overlap & Similarity Docs"
Cohesion: 0.25
Nodes (8): Item Resolution, Content Overlap Detection, Cosine Similarity for Overlap, Score Bands, Acronym Expansion, CI Name Resolution, Phase 1 Vector Search, Web UI Guide

### Community 61 - "Chat Answer Service"
Cohesion: 0.54
Nodes (6): build_scaffold(), compose_answer(), Deterministic scaffold + narrow narrative call. Worst case: mediocre prose next…, test_answer_failure_degrades_to_scaffold(), test_compose_prepends_scaffold(), test_scaffold_deterministic()

### Community 62 - "Login CLI (Python)"
Cohesion: 0.54
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 63 - "CLAUDE.md Architecture"
Cohesion: 0.57
Nodes (7): RCARS Architecture (4 Deployments), FastAPI 2.0 API (uvicorn), React 19 SPA Frontend (PatternFly 6), PostgreSQL with pgvector (768-dim embeddings), Recommend Worker (arq:queue:recommend), Redis (Job Queue + Pub/Sub), Scan Worker (arq:queue:scan)

### Community 64 - "Browse & PF6 Plans"
Cohesion: 0.33
Nodes (7): Infrastructure-Aware Catalog Metadata, PatternFly 6 Theme Architecture, Server-Side Filtering, Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 65 - "Scan Pipeline Docs"
Cohesion: 0.29
Nodes (7): Scan Pipeline, Boilerplate Filtering, Scan Change Detection, Scan Deduplication and Sibling Propagation, Plan 2: Analysis and Recommendations, Plan: Stale Showroom Detection, Plan: Scan Failures and Catalog Visibility

### Community 66 - "Auth Design Specs"
Cohesion: 0.38
Nodes (7): API Authentication Design, API Key Authentication (X-API-Key Header), OAuth PKCE Login Flow, Proxy Verification Secret (Anti-Spoofing), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 67 - "Health Routes"
Cohesion: 0.33
Nodes (6): health(), get, Request, readiness(), HealthResponse, ReadinessResponse

### Community 68 - "Time Window Tests"
Cohesion: 0.38
Nodes (3): Return the start date for a sliding window (today - N days)., _window_start(), TestWindowStart

### Community 69 - "Login CLI (Shell)"
Cohesion: 0.48
Nodes (5): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token()

### Community 70 - "Request Logging"
Cohesion: 0.40
Nodes (3): BaseHTTPMiddleware, Request, RequestLoggingMiddleware

### Community 71 - "Project Management"
Cohesion: 0.50
Nodes (4): Backlog Jira Migration, RCARS Project Instructions, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 72 - "Auth Evolution Plans"
Cohesion: 0.67
Nodes (4): API Key Authentication, OpenShift Group-Based Auth, API Authentication Plan, OpenShift Group Auth Plan

### Community 73 - "Rate Limiting"
Cohesion: 0.50
Nodes (3): _get_user_key(), Request, Per-user rate limiting via slowapi + Redis.

### Community 78 - "API Key Test Fixtures"
Cohesion: 0.67
Nodes (3): db(), fixture, Ephemeral test database — uses RCARS_DATABASE_URL from env (rcars_test).

## Knowledge Gaps
- **174 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_ADMIN_EMAILS_STR`, `RCARS_CURATOR_EMAILS_STR` (+169 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database Core` to `Chat Sessions & Context`, `CLI Commands`, `Logging & Redis Config`, `Content Similarity`, `Retirement Workflow`, `Embeddings & LLM Client`, `Database Tests`, `Recommender Pipeline`, `App Settings`, `FastAPI App Setup`, `Database Item Lookups`, `LLM Provider Config`, `API Key Tests`, `Chat Router & DB`, `LLM Calls & Workloads`, `Base Name Extraction`, `Job Completion`, `Retirement DB Ops`, `DB Connection Pool`, `API Key Test Fixtures`, `Channel Metrics`, `API Key Pruning`, `Job Pruning`, `CLI Key Revocation`, `Chat Depth Fixtures`, `Chat Evidence Fixtures`, `Chat Live Fixtures`, `Chat Resolve Fixtures`, `Session DB Fixtures`, `Chat Integration Fixtures`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **Why does `Settings` connect `App Settings` to `Chat Sessions & Context`, `Auth Middleware`, `CLI Commands`, `Logging & Redis Config`, `Catalog Routes`, `Showroom Analyzer`, `Embeddings & LLM Client`, `Admin Routes & Schemas`, `Recommender Pipeline`, `Admin API Endpoints`, `Auth Routes & API Keys`, `FastAPI App Setup`, `Advisor Routes`, `LLM Provider Config`, `Auth Security Tests`, `Chat Router & DB`, `LLM Calls & Workloads`, `Auth Route Tests`, `Chat Answer Service`, `Token Exchange Tests`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `compute_sales_impact()` connect `Performance Scoring` to `Chat Sessions & Context`, `Analysis & Advisor Routes`, `Logging & Redis Config`, `Catalog Routes`, `Reporting SQL Builders`, `Windowed Metrics`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Database` (e.g. with `HandlerResult` and `Resolution`) actually correct?**
  _`Database` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `Settings` (e.g. with `ChatRequest` and `QueryRequest`) actually correct?**
  _`Settings` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `JobProgressRelay` (e.g. with `ChatRequest` and `QueryRequest`) actually correct?**
  _`JobProgressRelay` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _174 weakly-connected nodes found - possible documentation gaps or missing edges._