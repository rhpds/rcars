# Graph Report - .  (2026-07-31)

## Corpus Check
- 182 files · ~279,528 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1645 nodes · 3180 edges · 98 communities (82 shown, 16 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 222 edges (avg confidence: 0.61)
- Token cost: 910,145 input · 0 output

## Community Hubs (Navigation)
- Database Access Layer
- Analysis Routes & SSE Streaming
- CLI Commands
- Recommendation Pipeline (Vector/Triage/Rationale)
- Auth Middleware & Tests
- Catalog API Routes
- Deployment Pipeline & Feature Overview
- Showroom & Workload Scanners
- Historical Web UI & Auth Design Docs
- Worker Tasks & Logging
- Frontend Build Config (package.json)
- Content Similarity Computation
- Retirement Workflow Status Logic
- Advisor & History Frontend Components
- LLM Provider Config
- Content Model Migration Script
- Babylon CRD Catalog Reader
- Embedding Text & Product Terms
- Jira Retirement Ticket Client
- Admin Routes & API Schemas
- Database Layer Tests
- Browse Page Frontend
- Content Entity DB Methods
- API Key DB Tests
- TypeScript Config
- Auth & API Key Routes
- Reporting Sync SQL Builders
- Retirement Scoring Algorithm
- Frontend App Shell & Hooks
- Status/Jobs/Workloads Pages + API Client
- Retirement Page Frontend
- Advisor API Routes
- Local Dev Services Script
- Admin Route Handlers
- Event URL Parser
- Auth Security Tests
- Rec Card Duration & Best Fit Plans
- Content Model Design Spec
- Masthead, Sidebar & Auth Hook
- External API Auth Docs
- System Design & Rearchitecture Docs
- Retirement Analysis Integration Plan
- Content Model Schema Foundation
- Recommender Redesign Plan
- Auth Routes Tests
- Sync Page Frontend
- Recommendation Engine Docs & Plans
- Base Name Extraction Utility
- Content Overlap Page Frontend
- Retirement Analysis Doc Concepts
- Content Overlap Doc Concepts
- PatternFly 6 Migration Design
- Scan Error Classification & Sibling Propagation
- MCP Query Pagination
- Scan Pipeline Docs & Plans
- Browse Page Redesign Spec
- FastAPI App Bootstrap
- Windowed Metrics Tests
- Reporting Window Tests
- Web Guide & Prompt Docs
- App Smoke Tests
- CLI Login Helper (Python)
- Infra Metadata & Content Model Plan
- Scan Failure Surfacing Plan
- Retirement Workflow Actions Design
- Overlap Analysis Redesign Design
- Health Check Routes
- CLI Login Helper (Shell)
- Content Entities Schema
- Retirement Workflow Actions Plan
- Request Logging Middleware
- PatternFly 6 Migration Plan
- API Keys Admin Panel
- Rate Limiting Middleware
- Token Exchange Tests
- Async Feedback Pattern Plans
- pgvector Image Build
- Unauthenticated Access Test
- Auto-Retire Removed Items
- DB Connection Pool
- API Key Pruning
- Job Pruning
- CLI Key Revocation
- Docker Entrypoint Script
- Docs Deploy Workflow
- RCARS Package Metadata A
- RCARS Package Metadata B
- Event Match Prompt
- Rationale Prompt (Single Candidate)
- Content Gaps Synthesis Prompt

## God Nodes (most connected - your core abstractions)
1. `Database` - 154 edges
2. `Settings` - 72 edges
3. `compute_content_similarity()` - 30 edges
4. `JobProgressRelay` - 25 edges
5. `get_current_user()` - 21 edges
6. `get_db()` - 21 edges
7. `run_reporting_sync()` - 20 edges
8. `Data Design (doc)` - 19 edges
9. `call_llm()` - 18 edges
10. `analyze_showroom()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Content Overlap Detection (doc)` --references--> `compute_content_similarity()`  [EXTRACTED]
  docs/architecture/content-overlap.md → src/api/rcars/db/similarity.py
- `Content Overlap Detection (doc)` --references--> `get_similar_items()`  [EXTRACTED]
  docs/architecture/content-overlap.md → src/api/rcars/db/similarity.py
- `Content Overlap Detection (doc)` --references--> `get_overlap_items()`  [EXTRACTED]
  docs/architecture/content-overlap.md → src/api/rcars/db/similarity.py
- `Content Overlap Detection (doc)` --references--> `get_similarity_stats()`  [EXTRACTED]
  docs/architecture/content-overlap.md → src/api/rcars/db/similarity.py
- `External API Tools README` --semantically_similar_to--> `OAuth Login Flow with PKCE`  [INFERRED] [semantically similar]
  tools/README.md → docs/superpowers/specs/2026-07-03-api-authentication-design.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **RCARS Authentication & Authorization Flow** — concept_dev_bypass_auth, concept_sa_bearer_token_auth, concept_oauth_proxy_auth, concept_role_based_access_control [INFERRED 0.85]
- **Full Deploy Ansible Pipeline (--tags full)** — ansible_deploy_playbook, ansible_tasks_namespace_task, ansible_tasks_apply_infra_task, ansible_tasks_apply_manifests_task, ansible_tasks_build_api_task, ansible_tasks_build_frontend_task, ansible_tasks_smoke_test_task [EXTRACTED 1.00]
- **Nightly Maintenance Pipeline Steps** — concept_nightly_maintenance_pipeline, concept_reporting_mcp_integration, concept_infrastructure_aware_catalog_metadata, concept_scan_deduplication [INFERRED 0.85]
- **Retirement Workflow Lifecycle (Approve→Notify→Start→Retired via Jira, backed by soft-delete)** — concept_retirement_workflow_lifecycle, concept_jira_retirement_integration, table_retirement_workflow, concept_soft_delete_retirement [EXTRACTED 1.00]
- **Three-Phase Recommendation Pipeline Components** — concept_three_phase_recommendation_pipeline, concept_ci_name_resolution, concept_duration_aware_reranking, concept_tier_system [EXTRACTED 1.00]
- **Scan Pipeline Deduplication, Change Detection & Error Classification** — concept_scan_dedup_sibling_propagation, concept_change_detection_two_phase, concept_error_classification, docs_architecture_scan_pipeline [EXTRACTED 1.00]
- **Recommender pipeline evolution: three-phase design through tiering, token tracking, and duration curation** — docs_superpowers_specs_2026_04_11_recommender_redesign_design, docs_superpowers_specs_2026_04_24_advisor_list_persistence_feedback_design, docs_superpowers_specs_2026_04_14_token_usage_tracking_design, docs_superpowers_plans_2026_06_15_rec_card_duration_bestfit [INFERRED 0.80]
- **Retirement feature line: reporting integration, workflow actions, and content-model re-keying** — docs_superpowers_specs_2026_06_15_retirement_analysis_integration_design, docs_superpowers_plans_2026_06_15_retirement_analysis_integration, docs_superpowers_plans_2026_07_02_retirement_workflow_actions, docs_superpowers_plans_2026_07_20_generalized_content_model_plan [INFERRED 0.85]
- **RCARS architecture evolution: single-pod HTMX monolith to React+FastAPI+arq to normalized content model** — docs_superpowers_specs_2026_04_07_eca_production_redesign_design, docs_superpowers_specs_2026_04_08_rcars_plan3a_web_ui_design, docs_superpowers_specs_2026_04_09_rcars_openshift_deployment_design, docs_superpowers_specs_2026_04_25_rearchitecture_api_design, docs_superpowers_plans_2026_07_20_generalized_content_model_plan [INFERRED 0.85]
- **RCARS Recommendation Pipeline Prompt Stages (Triage -> Rationale -> Synthesis)** — src_api_rcars_prompts_triage_prompt, src_api_rcars_prompts_rationale_prompt, src_api_rcars_prompts_rationale_single_prompt, src_api_rcars_prompts_rationale_synthesis_prompt [INFERRED 0.85]
- **Content Similarity Computation Flow (Embeddings -> Similarity -> Overlap/Related)** — docs_superpowers_specs_2026_07_20_generalized_content_model_design_embeddings_max_similarity, docs_superpowers_specs_2026_07_20_generalized_content_model_design_content_similarity_table, docs_superpowers_specs_2026_07_20_generalized_content_model_design_content_entities_table, docs_superpowers_specs_2026_07_29_overlap_analysis_redesign_design_overlap_vs_related [INFERRED 0.80]
- **External API Access Design & Documentation Set** — docs_superpowers_specs_2026_07_03_api_authentication_design_doc, docs_user_api_access_doc, tools_readme_doc, docs_superpowers_specs_2026_07_03_api_authentication_design_login_script [INFERRED 0.85]

## Communities (98 total, 16 thin omitted)

### Community 1 - "Analysis Routes & SSE Streaming"
Cohesion: 0.09
Nodes (57): asyncio, Redis, analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_stale() (+49 more)

### Community 2 - "CLI Commands"
Cohesion: 0.07
Nodes (60): argument, command, group, option, pass_context, cli(), compute_similarity_cmd(), flag() (+52 more)

### Community 3 - "Recommendation Pipeline (Vector/Triage/Rationale)"
Cohesion: 0.07
Nodes (48): PostgreSQL + pgvector database layer for RCARS v2., generate_embedding(), Generate a 768-dim embedding via the vLLM embedding server. Nomic requires task…, Candidate, QueryState, Data models for the recommendation pipeline., A content entity moving through the recommendation pipeline., Convert similarity score (0.0-1.0) to percentage. (+40 more)

### Community 4 - "Auth Middleware & Tests"
Cohesion: 0.09
Nodes (26): _check_api_key_role_ceiling(), get_current_user(), _log_auth_decision(), _parse_sa_allowlist(), Request, require_admin(), require_auth(), require_curator() (+18 more)

### Community 5 - "Catalog API Routes"
Cohesion: 0.13
Nodes (50): field_validator, add_tag(), add_workload_mapping(), catalog_facets(), catalog_stats(), ContentPathRequest, delete_workload_mapping(), DurationRequest (+42 more)

### Community 6 - "Deployment Pipeline & Feature Overview"
Cohesion: 0.07
Nodes (51): RCARS OCP Deployment Playbook (deploy.yml), Ansible Galaxy Requirements (kubernetes.core), Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Create Namespace Task (+43 more)

### Community 7 - "Showroom & Workload Scanners"
Cohesion: 0.07
Nodes (47): CompletedProcess, analyze_showroom(), build_analysis_prompt(), build_module_embedding_text(), check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), get_repo_head() (+39 more)

### Community 8 - "Historical Web UI & Auth Design Docs"
Cohesion: 0.04
Nodes (49): RCARS Plan 3a: Web UI (FastAPI+HTMX), POST /advisor/query endpoint, base.html template (LCARS logo, nav, HTMX/Alpine CDN), web/deps.py (get_current_user, require_curator), rec_card.html / rec_card_expanded.html fragments, rcars serve CLI command, API Authentication for External Access — Implementation Plan, api_keys table (SHA-256 hashed, role-scoped) (+41 more)

### Community 9 - "Worker Tasks & Logging"
Cohesion: 0.08
Nodes (36): BoundLogger, RedisSettings, _add_component(), get_logger(), setup_logging(), build_sandbox_summary(), Sandbox summary generation from infrastructure metadata and workload…, Assemble a sandbox summary from infrastructure metadata. workload_products:… (+28 more)

### Community 10 - "Frontend Build Config (package.json)"
Cohesion: 0.04
Nodes (45): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-core, @patternfly/react-icons, @patternfly/react-table (+37 more)

### Community 11 - "Content Similarity Computation"
Cohesion: 0.09
Nodes (42): _build_similar_item(), compute_content_similarity(), get_overlap_items(), get_similar_items(), get_similarity_stats(), Any, ConnectionPool, Content similarity computation and queries. Extracted from database.py to start… (+34 more)

### Community 12 - "Retirement Workflow Status Logic"
Cohesion: 0.07
Nodes (21): datetime, derive_status(), Retirement workflow business logic., Derive the workflow status from the highest completed step., Tests for retirement workflow business logic (derive_status)., Test derive_status with various step combinations., Validate STEP_ORDER constant structure., Retired should be first (highest priority), reviewed last. (+13 more)

### Community 13 - "Advisor & History Frontend Components"
Cohesion: 0.09
Nodes (25): ProgressMessage, ProgressStream(), ProgressStreamProps, Candidate, catalogUrl(), FORMAT_COLORS, FORMAT_LABELS, RecCard() (+17 more)

### Community 14 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): BaseSettings, _call_anthropic(), _call_litemaas(), call_llm(), fetch_litemaas_models(), LLMResult, _parse_csv(), Query LiteMaaS /v1/models endpoint once and cache the result. (+10 more)

### Community 15 - "Content Model Migration Script"
Cohesion: 0.16
Nodes (30): Connection, cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists() (+22 more)

### Community 16 - "Babylon CRD Catalog Reader"
Cohesion: 0.11
Nodes (25): CatalogReader, component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata(), extract_showroom_url(), _get_label() (+17 more)

### Community 17 - "Embedding Text & Product Terms"
Cohesion: 0.12
Nodes (9): build_embedding_text(), Build text for CI-level embedding from analysis results., _expand_query_terms(), _load_product_terms(), Load product term mappings from the bundled YAML file. Returns (acronyms,…, Expand product acronyms and synonyms for better embedding match., TestBuildEmbeddingText, TestExpandQueryTerms (+1 more)

### Community 18 - "Jira Retirement Ticket Client"
Cohesion: 0.13
Nodes (27): _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _jira_request(), Jira REST API client for retirement ticket creation. Uses urllib (consistent…, Create a Jira retirement ticket. Returns the new Jira issue key (e.g.…, Make an HTTP request to the Jira REST API v3 with Basic auth. Returns parsed…, Derive catalog base name from content_id (e.g. 'babylon:foo.prod' → 'foo'). (+19 more)

### Community 19 - "Admin Routes & API Schemas"
Cohesion: 0.17
Nodes (24): Admin routes — token usage, jobs, worker health, scheduled maintenance., CatalogItemWorkload, CatalogListResponse, ErrorDetail, HealthChecks, JobListResponse, LlmProviderResponse, OverlapItemsResponse (+16 more)

### Community 20 - "Database Layer Tests"
Cohesion: 0.11
Nodes (13): db(), fixture, Seed test data for filtered catalog queries., _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale() (+5 more)

### Community 21 - "Browse Page Frontend"
Cohesion: 0.10
Nodes (16): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, BrowsePage(), CatalogItem, catalogUrl() (+8 more)

### Community 23 - "API Key DB Tests"
Cohesion: 0.12
Nodes (11): db(), _generate_key(), fixture, Tests for API key database CRUD operations., Ephemeral test database — uses RCARS_DATABASE_URL from env (rcars_test)., Generate a raw key, its hash, and its prefix., TestCreateApiKey, TestGetApiKeyByHash (+3 more)

### Community 24 - "TypeScript Config"
Cohesion: 0.09
Nodes (22): DOM, DOM.Iterable, ES2020, src, compilerOptions, allowImportingTsExtensions, isolatedModules, jsx (+14 more)

### Community 25 - "Auth & API Key Routes"
Cohesion: 0.17
Nodes (22): invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), delete, get (+14 more)

### Community 26 - "Reporting Sync SQL Builders"
Cohesion: 0.14
Nodes (21): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), compute_retirement_score_breakdown(), _compute_retirement_score_with_breakdown() (+13 more)

### Community 27 - "Retirement Scoring Algorithm"
Cohesion: 0.13
Nodes (12): compute_retirement_score(), compute_sales_impact(), Compute sales impact tier from closed amount., Compute retirement score 0-100 using percentile ranks. Higher = stronger…, Bottom percentile on everything, zero sales, high cost., Top percentile on everything., Recently published items get score reduction., High cost with zero closed sales adds 15 points. (+4 more)

### Community 28 - "Frontend App Shell & Hooks"
Cohesion: 0.14
Nodes (16): App(), useAuthProvider(), PrivateModeContext, PrivateModeState, usePrivateModeProvider(), applyTheme(), getInitialTheme(), Theme (+8 more)

### Community 29 - "Status/Jobs/Workloads Pages + API Client"
Cohesion: 0.11
Nodes (16): Job, RecentJobsPage(), CatalogStatus, InfraStats, StatusPage(), StatusFilter, UnmappedWorkload, VerificationFilter (+8 more)

### Community 30 - "Retirement Page Frontend"
Cohesion: 0.14
Nodes (16): ageColor(), ageDays(), AgeFilter, fmt(), fmtRoi(), num(), RetirementPage(), RetirementTab (+8 more)

### Community 31 - "Advisor API Routes"
Cohesion: 0.21
Nodes (19): _advisor_limit(), get_query_result(), get_session(), list_sessions(), BaseModel, get, limit, post (+11 more)

### Community 32 - "Local Dev Services Script"
Cohesion: 0.18
Nodes (17): init_db(), RCARS_ADMIN_EMAILS_STR, RCARS_CURATOR_EMAILS_STR, RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 33 - "Admin Route Handlers"
Cohesion: 0.22
Nodes (18): compute_similarity(), get_job(), list_jobs(), llm_provider_status(), overlap_report(), get, post, Request (+10 more)

### Community 34 - "Event URL Parser"
Cohesion: 0.16
Nodes (16): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), Any, Event URL parser. Fetches event web pages, follows links to…, Filter links to those that look like schedule/program/content pages. (+8 more)

### Community 35 - "Auth Security Tests"
Cohesion: 0.12
Nodes (9): app_no_auth(), client(), fixture, Security test suite for RCARS API authentication. Validates that all auth…, App with NO dev_user — all auth enforced., TestExpiredApiKey, TestRevokedApiKey, TestRoleCeiling (+1 more)

### Community 36 - "Rec Card Duration & Best Fit Plans"
Cohesion: 0.13
Nodes (16): Rec Card: Duration Labels + Best Fit Button — Implementation Plan, Acronym case-insensitive matching fix, Best Fit button redesign (btn-best-fit), Rec card copy/paste bug fix, Duration penalty guard on curated source only, duration_source field (curated vs ai), Task 4: Advisor Page + RecCard PF6 migration, scripts/migrate_to_content_model.py (export/import phases) (+8 more)

### Community 37 - "Content Model Design Spec"
Cohesion: 0.23
Nodes (15): architecture_analysis Table (Illustrative), babylon_items Extension Table, Babylon Ingestion Pipeline Phase 1 Changes, content_entities Universal Registry Table, content_id Namespaced Identity Scheme, vocabularies.yaml Controlled Vocabulary, RCARS Generalized Content Model Design, interactive_experiences Extension Table (Illustrative) (+7 more)

### Community 38 - "Masthead, Sidebar & Auth Hook"
Cohesion: 0.20
Nodes (11): API_DOCS_URL, DbStatus, formatAge(), getInitials(), RcarsMasthead(), RcarsSidebar(), AuthContext, AuthState (+3 more)

### Community 39 - "External API Auth Docs"
Cohesion: 0.23
Nodes (14): API Key Authentication Mechanism, api_keys Table Schema, 4-Step Auth Middleware Chain, Direct API OpenShift Route, RCARS API Authentication for External Access, rcars-login Helper Script, OAuth Login Flow with PKCE, OAuth Proxy Verification Secret (+6 more)

### Community 40 - "System Design & Rearchitecture Docs"
Cohesion: 0.19
Nodes (13): CI Hierarchy (Published VCI / Base CI / Infrastructure CI), Infrastructure Metadata Extraction (AgnosticD v2), LLM Provider Routing (LiteMaaS preferred, Vertex AI fallback), Showroom URL Extraction (two-path strategy), Soft-Delete / retired_at Preservation Pattern, Three-Tier Rearchitecture (React SPA + FastAPI JSON API + arq Workers), Worker Split: scan vs recommend queues (anti-starvation), System Design (doc) (+5 more)

### Community 41 - "Retirement Analysis Integration Plan"
Cohesion: 0.19
Nodes (13): Retirement Analysis Integration — Implementation Plan, compute_retirement_score(), mcp_query() — MCP HTTP client with auto-pagination, Nightly pipeline Step 5: reporting metrics sync, reporting_metrics table, RetirementPage.tsx dashboard component, run_reporting_sync() orchestrator, performance_channels table (replaces reporting_metrics) (+5 more)

### Community 42 - "Content Model Schema Foundation"
Cohesion: 0.18
Nodes (12): content_entities/babylon_items Two-Table Design, content_id Source-Prefixed Identity Scheme, Data Design (doc), RCARS Plan 1: Foundation & Catalog Reader, Token Usage Tracking Implementation Plan, SCHEMA_SQL (database.py), advisor_sessions table, babylon_items table (+4 more)

### Community 43 - "Recommender Redesign Plan"
Cohesion: 0.18
Nodes (12): search_embeddings() MAX(similarity)-per-content_id rewrite, Recommender Redesign — Three-Phase Pipeline, QueryState dataclass, recommender/ package restructure (vector_search, triage, rationale, pipeline), run_query() generator orchestrator (pipeline.py), Three-phase pipeline: vector search → Haiku triage → Sonnet rationale, Hard vector distance cutoff (RCARS_VECTOR_CUTOFF), Token Usage Tracking — Design Spec (+4 more)

### Community 44 - "Auth Routes Tests"
Cohesion: 0.17
Nodes (6): client(), fixture, Tests for API key management endpoints., TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 45 - "Sync Page Frontend"
Cohesion: 0.18
Nodes (5): LogWindow(), LogWindowProps, ActionState, ScheduleInfo, SyncPage()

### Community 46 - "Recommendation Engine Docs & Plans"
Cohesion: 0.22
Nodes (11): Acronym Expansion (AAP, RHOAI, OCP, etc.), CI Name Resolution in Vector Search, Duration-Aware Reranking (soft/hard constraint), Event URL Mode (fetch + extract + search), Published/Base CI Promotion, Three-Phase Progressive Recommendation Pipeline, Recommendation Tier System (green/yellow/white), Recommendation Engine (doc) (+3 more)

### Community 47 - "Base Name Extraction Utility"
Cohesion: 0.27
Nodes (3): extract_base_name(), Strip stage suffix from an RCARS ci_name to get the reporting DB base name., TestExtractBaseName

### Community 48 - "Content Overlap Page Frontend"
Cohesion: 0.20
Nodes (7): ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapItem, OverlapStats

### Community 49 - "Retirement Analysis Doc Concepts"
Cohesion: 0.20
Nodes (10): Catalog Backfill (zero-value items for full coverage), Cost Methodology: All-Environment Cost Amortized to Prod, Jira Retirement Ticket Integration, Percentile-Based Retirement Scoring, Why provisions_summary Instead of Raw provisions Table, Retirement Workflow Lifecycle (approve→notify→start→retired), Retirement Analysis (doc), performance_channels table (+2 more)

### Community 50 - "Content Overlap Doc Concepts"
Cohesion: 0.20
Nodes (10): Content Hash Deduplication (vector search dedup), Cosine Similarity (pgvector <=> operator), Future: LLM-Powered Overlap Assessment (RHDPCD-614), Overlap vs Related Relationship Types, Scan Deduplication & Sibling Propagation (Phase A/B/C), Overlap Score Bands (Near-duplicate/High/Related), Stage-Variant Deduplication (showroom_url identity), Content Overlap Detection (doc) (+2 more)

### Community 51 - "PatternFly 6 Migration Design"
Cohesion: 0.20
Nodes (10): Browse Page PF6 Toolbar Redesign, PF6 Clean-Break Migration Strategy, LCARS to PF6 Component Mapping, PatternFly 6 Migration Design Spec, PF6 Navigation Restructure, RecCard PF6 Design, RCARS PF6 Theme Architecture (CSS Token Layers), Theme Toggle (useTheme Hook) (+2 more)

### Community 52 - "Scan Error Classification & Sibling Propagation"
Cohesion: 0.27
Nodes (9): Exception, classify_scan_error(), Classify a scan error and return (error_class, human_message)., _propagate_to_sibling(), Analysis/scan worker tasks., Strip LLM-hallucinated keys from format_suitability — only demo and…, Propagate analysis + embeddings to a single sibling CI., run_analysis() (+1 more)

### Community 53 - "MCP Query Pagination"
Cohesion: 0.29
Nodes (7): _mcp_call(), mcp_query(), Call an MCP tool via HTTP JSON-RPC, return parsed JSON result., Execute SQL via MCP server, auto-paginating past 500-row cap., patch, Build a mock urllib response for an MCP query result., TestMcpPagination

### Community 54 - "Scan Pipeline Docs & Plans"
Cohesion: 0.25
Nodes (9): Two-Phase Change Detection (git ls-remote + content hash), Scan Error Classification (jinja_url, timeout, etc.), No-Match Behavior (fail honestly vs widen cutoff), 768-dim Vector Embeddings (nomic-embed-text-v1.5 via vLLM), Scan Pipeline (doc), Stale Showroom Detection Implementation Plan, Scan Failures & Catalog Visibility Implementation Plan, analyzer.py (Scan Pipeline Implementation) (+1 more)

### Community 55 - "Browse Page Redesign Spec"
Cohesion: 0.25
Nodes (9): Task 5: Browse Page Redesign (PF6), search_by_infrastructure() faceted search method, workload_aliases table (acronym/alias resolution), workload_mapping table (curated role → product name), Browse Page Redesign — Design Spec, Two-tier collapsible filter panel (cloud provider/workloads/config), Numbered page pagination component, Server-side filtering + pagination (replaces client-side) (+1 more)

### Community 56 - "FastAPI App Bootstrap"
Cohesion: 0.36
Nodes (6): FastAPI, create_app(), lifespan(), client(), fixture, Tests for OAuth token exchange endpoint (implicit grant flow).

### Community 57 - "Windowed Metrics Tests"
Cohesion: 0.28
Nodes (6): _build_windowed_metrics(), Build per-item windowed_metrics JSONB from per-window query results. For each…, Windowed metrics should have entries for all four windows., An item with zero provisions/sales in a window should score high., Items with different provision counts should get different scores., TestBuildWindowedMetrics

### Community 58 - "Reporting Window Tests"
Cohesion: 0.31
Nodes (4): Return the start date for a sliding window (today - N days)., _window_start(), Tests for reporting sync utilities., TestWindowStart

### Community 59 - "Web Guide & Prompt Docs"
Cohesion: 0.25
Nodes (8): Advisor Two-Pane Interface, Web UI Guide, Recommendation Card Tiers (Green/Yellow/White), Retirement Analysis Page (User Docs), RCARS MkDocs Material Site Config, requirements-docs.txt (mkdocs-material pin), Batch Rationale Prompt, Triage Relevance Prompt

### Community 60 - "App Smoke Tests"
Cohesion: 0.25
Nodes (3): client(), fixture, test_auth_me_unauthenticated()

### Community 61 - "CLI Login Helper (Python)"
Cohesion: 0.54
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 62 - "Infra Metadata & Content Model Plan"
Cohesion: 0.33
Nodes (7): retirement_workflow table, RCARS Generalized Content Model — Implementation Plan, Full normalization (Approach A) — fresh schema build, Infrastructure-Aware Catalog Metadata — Design Spec, is_agnosticd_v2() detection (catalog everything, surface selectively), catalog_item_workloads junction table, extract_infrastructure_metadata() function

### Community 63 - "Scan Failure Surfacing Plan"
Cohesion: 0.29
Nodes (7): Scan Failure Surfacing & Dev/Event Catalog Visibility, Catalog reconciliation (hard delete removed items), classify_scan_error() error classification function, psycopg ConnectionPool fix (shared connection thread-safety bug), Dev/event catalog visibility (stage toggle + badges), scan_status/scan_error_class columns on catalog_items, Stage dedup logic (prod > event > dev)

### Community 64 - "Retirement Workflow Actions Design"
Cohesion: 0.38
Nodes (7): Auto-Close Retired Workflow Items, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Jira Service Module (services/jira.py), Retirement Workflow 5-Stage Process, retirement_workflow SQL Table (catalog_base_name keyed), Retirement Workflow Drawer (User Docs)

### Community 65 - "Overlap Analysis Redesign Design"
Cohesion: 0.33
Nodes (7): content_similarity Table, Overlap Analysis Page Redesign Design, Overlap vs Related Similarity (relationship_type), ContentOverlapPage.tsx Rewrite, Item-Centric Paginated Overlap Report, db/similarity.py Module Extraction, Content Overlap Page (User Docs)

### Community 66 - "Health Check Routes"
Cohesion: 0.33
Nodes (6): health(), get, Request, readiness(), HealthResponse, ReadinessResponse

### Community 67 - "CLI Login Helper (Shell)"
Cohesion: 0.48
Nodes (5): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token()

### Community 68 - "Content Entities Schema"
Cohesion: 0.40
Nodes (6): curated_duration_min column on showroom_analysis, babylon_items table (Babylon-specific extension), content_entities table (universal entity registry), upsert_babylon_catalog_item() — two-table transactional upsert, PostgreSQL + pgvector unified data store, showroom_analysis table (original schema)

### Community 69 - "Retirement Workflow Actions Plan"
Cohesion: 0.47
Nodes (6): Retirement Workflow Actions Implementation Plan, create_retirement_ticket(), derive_status() workflow status derivation, Retirement workflow slide-out drawer UI, jira.py — Jira REST API service module, 7 workflow REST endpoints (review/approve/notify/start/notes/cancel)

### Community 70 - "Request Logging Middleware"
Cohesion: 0.40
Nodes (3): BaseHTTPMiddleware, Request, RequestLoggingMiddleware

### Community 71 - "PatternFly 6 Migration Plan"
Cohesion: 0.50
Nodes (5): PatternFly 6 Migration Implementation Plan, Task 6: AdminPage split into Status/Sync/RecentJobs/Workloads pages, RcarsMasthead.tsx component, RcarsSidebar.tsx component, useTheme() / useThemeProvider() hook

### Community 72 - "API Keys Admin Panel"
Cohesion: 0.60
Nodes (4): ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo()

### Community 73 - "Rate Limiting Middleware"
Cohesion: 0.50
Nodes (3): _get_user_key(), Request, Per-user rate limiting via slowapi + Redis.

### Community 76 - "Async Feedback Pattern Plans"
Cohesion: 0.67
Nodes (3): Fire-and-Forget Background Thread + HTMX Polling Pattern, Admin Action Feedback Implementation Plan, Async Advisor Query Implementation Plan

### Community 77 - "pgvector Image Build"
Cohesion: 0.67
Nodes (3): embeddings Table + MAX(similarity) Scoring, Building the rcars-pgvector Image, rcars-pgvector Multi-Arch Image Build

## Knowledge Gaps
- **198 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_ADMIN_EMAILS_STR`, `RCARS_CURATOR_EMAILS_STR` (+193 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Content Overlap Detection (doc)` connect `Content Overlap Doc Concepts` to `Recommendation Engine Docs & Plans`, `System Design & Rearchitecture Docs`, `Content Similarity Computation`, `Scan Pipeline Docs & Plans`?**
  _High betweenness centrality (0.208) - this node is a cross-community bridge._
- **Why does `Database` connect `Database Access Layer` to `CLI Commands`, `Recommendation Pipeline (Vector/Triage/Rationale)`, `Showroom & Workload Scanners`, `Worker Tasks & Logging`, `Job & Scan Status DB Methods`, `Content Similarity Computation`, `Retirement Workflow Status Logic`, `LLM Provider Config`, `Auto-Retire Removed Items`, `Base Name Extraction Utility`, `DB Connection Pool`, `API Key Pruning`, `Job Pruning`, `CLI Key Revocation`, `Database Layer Tests`, `Content Entity DB Methods`, `API Key DB Tests`, `FastAPI App Bootstrap`?**
  _High betweenness centrality (0.163) - this node is a cross-community bridge._
- **Why does `System Design (doc)` connect `System Design & Rearchitecture Docs` to `Content Model Schema Foundation`, `Recommendation Engine Docs & Plans`, `Retirement Analysis Doc Concepts`, `Content Overlap Doc Concepts`, `Scan Pipeline Docs & Plans`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Database` (e.g. with `TestCreateApiKey` and `TestGetApiKeyByHash`) actually correct?**
  _`Database` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `Settings` (e.g. with `QueryRequest` and `SelectRequest`) actually correct?**
  _`Settings` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `JobProgressRelay` (e.g. with `QueryRequest` and `SelectRequest`) actually correct?**
  _`JobProgressRelay` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _198 weakly-connected nodes found - possible documentation gaps or missing edges._