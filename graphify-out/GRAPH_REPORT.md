# Graph Report - rcars-advisory  (2026-08-03)

## Corpus Check
- 196 files · ~315,284 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1948 nodes · 3945 edges · 122 communities (103 shown, 19 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 265 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1717c9e8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Database
- analysis.py
- cli.py
- pipeline.py
- get_current_user
- Request
- RCARS Project Instructions (CLAUDE.md)
- analyzer.py
- RCARS Production Redesign — Design Specification
- settings.py
- devDependencies
- admin.py
- derive_status
- AdvisorPage.tsx
- Settings
- migrate_to_content_model.py
- services/catalog.py
- _expand_query_terms
- Advisor Chat — Multi-Intent Design
- schemas.py
- test_db.py
- BrowsePage.tsx
- Any
- _generate_key
- compilerOptions
- routes/auth.py
- reporting_sync.py
- compute_retirement_score
- App.tsx
- api.ts
- RetirementPage.tsx
- advisor.py
- dev-services.sh
- handlers.py
- event_parser.py
- app.py
- Rec Card: Duration Labels + Best Fit Button — Implementation Plan
- RCARS Generalized Content Model Design
- RcarsMasthead.tsx
- RCARS API Authentication for External Access
- System Design (doc)
- Retirement Analysis Integration — Design Spec
- Data Design (doc)
- Recommender Redesign — Three-Phase Pipeline
- TestRevokeApiKey
- SyncPage.tsx
- Recommendation Engine (doc)
- extract_base_name
- ContentAnalysisPage.tsx
- test_jira_service.py
- Content Overlap Detection (doc)
- PatternFly 6 Migration Design Spec
- call_llm
- mcp_query
- RCARS Plan 3a: Web UI (FastAPI+HTMX)
- RCARS Generalized Content Model — Implementation Plan
- Design: Admin Action Feedback + Per-Item Re-analyze
- _build_windowed_metrics
- test_reporting.py
- Web UI Guide
- Task Sequence
- rcars-login.py
- Retirement Workflow Actions Implementation Plan
- content_entities table (universal entity registry)
- Retirement Workflow Actions Design
- Overlap Analysis Page Redesign Design
- routes/catalog.py
- rcars-login.sh
- config.py
- router.py
- api_keys table (SHA-256 hashed, role-scoped)
- PatternFly 6 Migration Implementation Plan
- chat_sessions.py
- seed_chat_fixtures
- TestTokenExchange
- Fire-and-Forget Background Thread + HTMX Polling Pattern
- embeddings Table + MAX(similarity) Scoring
- route
- .retire_removed_items
- .__init__
- .prune_expired_api_keys
- .prune_old_jobs
- .revoke_user_cli_keys
- docker-entrypoint.sh
- Deploy Docs GitHub Actions Workflow
- rcars
- rcars
- Event Page Match Prompt
- Single-Candidate Rationale Prompt
- Content Gaps Synthesis Prompt
- orchestrator.py
- HistoryPage.tsx
- File Map
- test_auth_security.py
- test_chat_live.py
- TestCreateApiKey
- logging.py
- Retirement Analysis (doc)
- Advisor Chat — Multi-Intent Architecture
- scan.py
- Scan Pipeline (doc)
- Session Model & Multi-Turn
- test_app.py
- test_chat_api.py
- test_chat_handlers.py
- Tools, Grounding & Graph-Shaped Retrieval
- test_chat_registry.py
- WorkloadsPage.tsx
- Intents & Router Contract
- Architecture
- UX
- Testing
- db
- db

## God Nodes (most connected - your core abstractions)
1. `Database` - 184 edges
2. `Settings` - 110 edges
3. `compute_content_similarity()` - 30 edges
4. `JobProgressRelay` - 26 edges
5. `RouterOutput` - 26 edges
6. `seed_chat_fixtures()` - 25 edges
7. `get_current_user()` - 21 edges
8. `get_db()` - 21 edges
9. `call_llm()` - 21 edges
10. `process_turn()` - 21 edges

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

## Communities (122 total, 19 thin omitted)

### Community 1 - "analysis.py"
Cohesion: 0.09
Nodes (57): asyncio, Redis, analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_stale() (+49 more)

### Community 2 - "cli.py"
Cohesion: 0.07
Nodes (62): argument, command, group, option, pass_context, cli(), compute_similarity_cmd(), flag() (+54 more)

### Community 3 - "pipeline.py"
Cohesion: 0.10
Nodes (28): generate_embedding(), Generate a 768-dim embedding via the vLLM embedding server. Nomic requires task…, Candidate, QueryState, Data models for the recommendation pipeline., A content entity moving through the recommendation pipeline., Convert similarity score (0.0-1.0) to percentage., State of a recommendation query at a pipeline phase boundary. (+20 more)

### Community 4 - "get_current_user"
Cohesion: 0.09
Nodes (26): _check_api_key_role_ceiling(), get_current_user(), _log_auth_decision(), _parse_sa_allowlist(), Request, require_admin(), require_auth(), require_curator() (+18 more)

### Community 5 - "Request"
Cohesion: 0.13
Nodes (29): add_tag(), add_workload_mapping(), catalog_facets(), catalog_stats(), delete_workload_mapping(), flag_item(), get_analysis(), get_catalog_item() (+21 more)

### Community 6 - "RCARS Project Instructions (CLAUDE.md)"
Cohesion: 0.07
Nodes (52): RCARS OCP Deployment Playbook (deploy.yml), Ansible Galaxy Requirements (kubernetes.core), Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Create Namespace Task (+44 more)

### Community 7 - "analyzer.py"
Cohesion: 0.07
Nodes (47): CompletedProcess, analyze_showroom(), build_analysis_prompt(), build_module_embedding_text(), check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), _get_embedding_client() (+39 more)

### Community 8 - "RCARS Production Redesign — Design Specification"
Cohesion: 0.20
Nodes (10): RCARS Production Redesign — Design Specification, APScheduler nightly scheduling, Babylon K8s CRDs as catalog source (replaces AgnosticV clone), enrichment_tags table (Type 2 RCARS-native enrichment), Helm chart subchart structure for OpenShift deployment, Prod/Everything stage filtering, RCARS OpenShift Deployment Design, Alembic migration setup (replaces ad-hoc ALTER TABLE) (+2 more)

### Community 9 - "settings.py"
Cohesion: 0.08
Nodes (33): RedisSettings, PostgreSQL + pgvector database layer for RCARS v2., candidates_with_performance(), Result serialization shared by the recommend worker and the chat layer., Convert QueryState candidates to JSON dicts with performance metrics. Exact…, build_sandbox_summary(), Sandbox summary generation from infrastructure metadata and workload…, Assemble a sandbox summary from infrastructure metadata. workload_products:… (+25 more)

### Community 10 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-core, @patternfly/react-icons, @patternfly/react-table (+40 more)

### Community 11 - "admin.py"
Cohesion: 0.07
Nodes (61): compute_similarity(), get_job(), list_jobs(), llm_provider_status(), overlap_report(), get, post, Request (+53 more)

### Community 12 - "derive_status"
Cohesion: 0.07
Nodes (20): derive_status(), Retirement workflow business logic., Derive the workflow status from the highest completed step., Tests for retirement workflow business logic (derive_status)., Test derive_status with various step combinations., Validate STEP_ORDER constant structure., Retired should be first (highest priority), reviewed last., With no step timestamps, status defaults to 'reviewed'. (+12 more)

### Community 13 - "AdvisorPage.tsx"
Cohesion: 0.08
Nodes (35): catalogUrl(), ItemCardBlock(), ItemCardBlockProps, ItemNeighbor, NoticeBlock(), NoticeBlockProps, OverlapNeighbor, OverlapTableBlock() (+27 more)

### Community 14 - "Settings"
Cohesion: 0.11
Nodes (16): BaseSettings, _parse_csv(), Settings, migrate(), One-time migration: export token_usage from old schema, create new schema,…, fixture, settings(), test_admin_check() (+8 more)

### Community 15 - "migrate_to_content_model.py"
Cohesion: 0.16
Nodes (30): Connection, cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists() (+22 more)

### Community 16 - "services/catalog.py"
Cohesion: 0.11
Nodes (25): CatalogReader, component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata(), extract_showroom_url(), _get_label() (+17 more)

### Community 17 - "_expand_query_terms"
Cohesion: 0.12
Nodes (9): build_embedding_text(), Build text for CI-level embedding from analysis results., _expand_query_terms(), _load_product_terms(), Load product term mappings from the bundled YAML file. Returns (acronyms,…, Expand product acronyms and synonyms for better embedding match., TestBuildEmbeddingText, TestExpandQueryTerms (+1 more)

### Community 18 - "Advisor Chat — Multi-Intent Design"
Cohesion: 0.18
Nodes (11): Advisor Chat — Multi-Intent Design, API Surface, Approach Decision, Configuration, Deployment, Error Handling & Observability, Follow-On Work (not in v1), Goals (+3 more)

### Community 19 - "schemas.py"
Cohesion: 0.12
Nodes (29): health(), get, Request, readiness(), CatalogItemWorkload, CatalogListResponse, ErrorDetail, HealthChecks (+21 more)

### Community 20 - "test_db.py"
Cohesion: 0.11
Nodes (13): db(), fixture, Seed test data for filtered catalog queries., _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider(), test_filtered_catalog_content_filter_failures(), test_filtered_catalog_content_filter_stale() (+5 more)

### Community 21 - "BrowsePage.tsx"
Cohesion: 0.10
Nodes (16): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, BrowsePage(), CatalogItem, catalogUrl() (+8 more)

### Community 23 - "_generate_key"
Cohesion: 0.12
Nodes (11): db(), _generate_key(), fixture, Tests for API key database CRUD operations., Ephemeral test database — uses RCARS_DATABASE_URL from env (rcars_test)., Generate a raw key, its hash, and its prefix., TestCreateApiKey, TestGetApiKeyByHash (+3 more)

### Community 24 - "compilerOptions"
Cohesion: 0.09
Nodes (22): DOM, DOM.Iterable, ES2020, src, compilerOptions, allowImportingTsExtensions, isolatedModules, jsx (+14 more)

### Community 25 - "routes/auth.py"
Cohesion: 0.16
Nodes (23): datetime, invalidate_api_key_cache(), auth_me(), create_api_key(), exchange_token(), _generate_api_key(), list_api_keys(), delete (+15 more)

### Community 26 - "reporting_sync.py"
Cohesion: 0.14
Nodes (21): _build_closed_sql(), _build_cost_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), compute_retirement_score_breakdown(), _compute_retirement_score_with_breakdown() (+13 more)

### Community 27 - "compute_retirement_score"
Cohesion: 0.13
Nodes (12): compute_retirement_score(), compute_sales_impact(), Compute sales impact tier from closed amount., Compute retirement score 0-100 using percentile ranks. Higher = stronger…, Bottom percentile on everything, zero sales, high cost., Top percentile on everything., Recently published items get score reduction., High cost with zero closed sales adds 15 points. (+4 more)

### Community 28 - "App.tsx"
Cohesion: 0.14
Nodes (16): App(), useAuthProvider(), PrivateModeContext, PrivateModeState, usePrivateModeProvider(), applyTheme(), getInitialTheme(), Theme (+8 more)

### Community 29 - "api.ts"
Cohesion: 0.13
Nodes (15): ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo(), Job, RecentJobsPage(), CatalogStatus, InfraStats (+7 more)

### Community 30 - "RetirementPage.tsx"
Cohesion: 0.14
Nodes (16): ageColor(), ageDays(), AgeFilter, fmt(), fmtRoi(), num(), RetirementPage(), RetirementTab (+8 more)

### Community 31 - "advisor.py"
Cohesion: 0.17
Nodes (25): _get_user_key(), Request, Per-user rate limiting via slowapi + Redis., _advisor_limit(), ChatRequest, get_query_result(), get_session(), list_sessions() (+17 more)

### Community 32 - "dev-services.sh"
Cohesion: 0.18
Nodes (17): init_db(), RCARS_ADMIN_EMAILS_STR, RCARS_CURATOR_EMAILS_STR, RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL, RCARS_REDIS_URL, dev-services.sh script (+9 more)

### Community 33 - "handlers.py"
Cohesion: 0.18
Nodes (26): get_item_workloads(), get_performance_scores(), handle_item_facts(), handle_overlap(), handle_performance(), handle_recommend(), HandlerResult, _item_card() (+18 more)

### Community 34 - "event_parser.py"
Cohesion: 0.16
Nodes (16): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), Any, Event URL parser. Fetches event web pages, follows links to…, Filter links to those that look like schedule/program/content pages. (+8 more)

### Community 35 - "app.py"
Cohesion: 0.14
Nodes (13): BaseHTTPMiddleware, FastAPI, create_app(), lifespan(), Request, RequestLoggingMiddleware, client(), fixture (+5 more)

### Community 36 - "Rec Card: Duration Labels + Best Fit Button — Implementation Plan"
Cohesion: 0.22
Nodes (10): Rec Card: Duration Labels + Best Fit Button — Implementation Plan, Acronym case-insensitive matching fix, Best Fit button redesign (btn-best-fit), Rec card copy/paste bug fix, Duration penalty guard on curated source only, duration_source field (curated vs ai), Candidate dataclass (models.py), Advisor List, Query Persistence & Feedback Design (+2 more)

### Community 37 - "RCARS Generalized Content Model Design"
Cohesion: 0.23
Nodes (15): architecture_analysis Table (Illustrative), babylon_items Extension Table, Babylon Ingestion Pipeline Phase 1 Changes, content_entities Universal Registry Table, content_id Namespaced Identity Scheme, vocabularies.yaml Controlled Vocabulary, RCARS Generalized Content Model Design, interactive_experiences Extension Table (Illustrative) (+7 more)

### Community 38 - "RcarsMasthead.tsx"
Cohesion: 0.20
Nodes (11): API_DOCS_URL, DbStatus, formatAge(), getInitials(), RcarsMasthead(), RcarsSidebar(), AuthContext, AuthState (+3 more)

### Community 39 - "RCARS API Authentication for External Access"
Cohesion: 0.23
Nodes (14): API Key Authentication Mechanism, api_keys Table Schema, 4-Step Auth Middleware Chain, Direct API OpenShift Route, RCARS API Authentication for External Access, rcars-login Helper Script, OAuth Login Flow with PKCE, OAuth Proxy Verification Secret (+6 more)

### Community 40 - "System Design (doc)"
Cohesion: 0.19
Nodes (13): CI Hierarchy (Published VCI / Base CI / Infrastructure CI), Infrastructure Metadata Extraction (AgnosticD v2), LLM Provider Routing (LiteMaaS preferred, Vertex AI fallback), Showroom URL Extraction (two-path strategy), Soft-Delete / retired_at Preservation Pattern, Three-Tier Rearchitecture (React SPA + FastAPI JSON API + arq Workers), Worker Split: scan vs recommend queues (anti-starvation), System Design (doc) (+5 more)

### Community 41 - "Retirement Analysis Integration — Design Spec"
Cohesion: 0.19
Nodes (13): Retirement Analysis Integration — Implementation Plan, compute_retirement_score(), mcp_query() — MCP HTTP client with auto-pagination, Nightly pipeline Step 5: reporting metrics sync, reporting_metrics table, RetirementPage.tsx dashboard component, run_reporting_sync() orchestrator, performance_channels table (replaces reporting_metrics) (+5 more)

### Community 42 - "Data Design (doc)"
Cohesion: 0.18
Nodes (12): content_entities/babylon_items Two-Table Design, content_id Source-Prefixed Identity Scheme, Data Design (doc), RCARS Plan 1: Foundation & Catalog Reader, Token Usage Tracking Implementation Plan, SCHEMA_SQL (database.py), advisor_sessions table, babylon_items table (+4 more)

### Community 43 - "Recommender Redesign — Three-Phase Pipeline"
Cohesion: 0.18
Nodes (12): search_embeddings() MAX(similarity)-per-content_id rewrite, Recommender Redesign — Three-Phase Pipeline, QueryState dataclass, recommender/ package restructure (vector_search, triage, rationale, pipeline), run_query() generator orchestrator (pipeline.py), Three-phase pipeline: vector search → Haiku triage → Sonnet rationale, Hard vector distance cutoff (RCARS_VECTOR_CUTOFF), Token Usage Tracking — Design Spec (+4 more)

### Community 45 - "SyncPage.tsx"
Cohesion: 0.18
Nodes (5): LogWindow(), LogWindowProps, ActionState, ScheduleInfo, SyncPage()

### Community 46 - "Recommendation Engine (doc)"
Cohesion: 0.24
Nodes (10): Acronym Expansion (AAP, RHOAI, OCP, etc.), Duration-Aware Reranking (soft/hard constraint), Event URL Mode (fetch + extract + search), Published/Base CI Promotion, Three-Phase Progressive Recommendation Pipeline, Recommendation Tier System (green/yellow/white), Recommendation Engine (doc), RCARS Plan 2: Analysis & Recommendations (+2 more)

### Community 47 - "extract_base_name"
Cohesion: 0.27
Nodes (3): extract_base_name(), Strip stage suffix from an RCARS ci_name to get the reporting DB base name., TestExtractBaseName

### Community 48 - "ContentAnalysisPage.tsx"
Cohesion: 0.20
Nodes (7): ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapItem, OverlapStats

### Community 49 - "test_jira_service.py"
Cohesion: 0.13
Nodes (27): _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _jira_request(), Jira REST API client for retirement ticket creation. Uses urllib (consistent…, Create a Jira retirement ticket. Returns the new Jira issue key (e.g.…, Make an HTTP request to the Jira REST API v3 with Basic auth. Returns parsed…, Derive catalog base name from content_id (e.g. 'babylon:foo.prod' → 'foo'). (+19 more)

### Community 50 - "Content Overlap Detection (doc)"
Cohesion: 0.20
Nodes (10): Content Hash Deduplication (vector search dedup), Cosine Similarity (pgvector <=> operator), Future: LLM-Powered Overlap Assessment (RHDPCD-614), Overlap vs Related Relationship Types, Scan Deduplication & Sibling Propagation (Phase A/B/C), Overlap Score Bands (Near-duplicate/High/Related), Stage-Variant Deduplication (showroom_url identity), Content Overlap Detection (doc) (+2 more)

### Community 51 - "PatternFly 6 Migration Design Spec"
Cohesion: 0.20
Nodes (10): Browse Page PF6 Toolbar Redesign, PF6 Clean-Break Migration Strategy, LCARS to PF6 Component Mapping, PatternFly 6 Migration Design Spec, PF6 Navigation Restructure, RecCard PF6 Design, RCARS PF6 Theme Architecture (CSS Token Layers), Theme Toggle (useTheme Hook) (+2 more)

### Community 52 - "call_llm"
Cohesion: 0.13
Nodes (25): call_llm(), Unified LLM call with automatic provider routing. LiteMaaS preferred if…, parse_analysis_response(), Parse Sonnet's JSON response, handling markdown fences., _build_deterministic_assessment(), _call_rationale_single(), _call_synthesis(), _format_single_candidate() (+17 more)

### Community 53 - "mcp_query"
Cohesion: 0.29
Nodes (7): _mcp_call(), mcp_query(), Call an MCP tool via HTTP JSON-RPC, return parsed JSON result., Execute SQL via MCP server, auto-paginating past 500-row cap., patch, Build a mock urllib response for an MCP query result., TestMcpPagination

### Community 54 - "RCARS Plan 3a: Web UI (FastAPI+HTMX)"
Cohesion: 0.14
Nodes (15): RCARS Plan 3a: Web UI (FastAPI+HTMX), POST /advisor/query endpoint, base.html template (LCARS logo, nav, HTMX/Alpine CDN), web/deps.py (get_current_user, require_curator), rec_card.html / rec_card_expanded.html fragments, rcars serve CLI command, RCARS Plan 3a — Web UI Design Spec, /admin operational controls page (+7 more)

### Community 55 - "RCARS Generalized Content Model — Implementation Plan"
Cohesion: 0.13
Nodes (18): Task 5: Browse Page Redesign (PF6), RCARS Generalized Content Model — Implementation Plan, Full normalization (Approach A) — fresh schema build, scripts/migrate_to_content_model.py (export/import phases), advisor_sessions table, log_advisor_session() DB method, Infrastructure-Aware Catalog Metadata — Design Spec, is_agnosticd_v2() detection (catalog everything, surface selectively) (+10 more)

### Community 56 - "Design: Admin Action Feedback + Per-Item Re-analyze"
Cohesion: 0.20
Nodes (10): Design: Admin Action Feedback + Per-Item Re-analyze, Analyze Showroom Content component (live log streaming), Catalog Sync component (admin page), Per-item Re-analyze component (curate page), Fire-and-forget + HTMX polling shared pattern, Async Advisor Query — Design Spec, OpenShift HAProxy 60s timeout problem, _query_status module-level dict (keyed by session_id) (+2 more)

### Community 57 - "_build_windowed_metrics"
Cohesion: 0.28
Nodes (6): _build_windowed_metrics(), Build per-item windowed_metrics JSONB from per-window query results. For each…, Windowed metrics should have entries for all four windows., An item with zero provisions/sales in a window should score high., Items with different provision counts should get different scores., TestBuildWindowedMetrics

### Community 58 - "test_reporting.py"
Cohesion: 0.31
Nodes (4): Return the start date for a sliding window (today - N days)., _window_start(), Tests for reporting sync utilities., TestWindowStart

### Community 59 - "Web UI Guide"
Cohesion: 0.25
Nodes (8): Advisor Two-Pane Interface, Web UI Guide, Recommendation Card Tiers (Green/Yellow/White), Retirement Analysis Page (User Docs), RCARS MkDocs Material Site Config, requirements-docs.txt (mkdocs-material pin), Batch Rationale Prompt, Triage Relevance Prompt

### Community 60 - "Task Sequence"
Cohesion: 0.09
Nodes (22): Advisor Multi-Intent Chat Implementation Plan, File Map, Global Constraints, Self-Review Notes, Task 10: Answer composer (`answer.py`), Task 11: Orchestrator (`process_turn`) + 3-turn deterministic integration test, Task 12: arq task, worker registration, `POST /advisor/chat`, SSE labels, Task 13: Golden routing eval (`llm_eval`) + live integration tier (+14 more)

### Community 61 - "rcars-login.py"
Cohesion: 0.54
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 62 - "Retirement Workflow Actions Implementation Plan"
Cohesion: 0.38
Nodes (7): Retirement Workflow Actions Implementation Plan, create_retirement_ticket(), derive_status() workflow status derivation, Retirement workflow slide-out drawer UI, jira.py — Jira REST API service module, retirement_workflow table, 7 workflow REST endpoints (review/approve/notify/start/notes/cancel)

### Community 63 - "content_entities table (universal entity registry)"
Cohesion: 0.17
Nodes (13): curated_duration_min column on showroom_analysis, babylon_items table (Babylon-specific extension), content_entities table (universal entity registry), upsert_babylon_catalog_item() — two-table transactional upsert, PostgreSQL + pgvector unified data store, showroom_analysis table (original schema), Scan Failure Surfacing & Dev/Event Catalog Visibility, Catalog reconciliation (hard delete removed items) (+5 more)

### Community 64 - "Retirement Workflow Actions Design"
Cohesion: 0.38
Nodes (7): Auto-Close Retired Workflow Items, Retirement Workflow Actions Design, Jira Ticket Creation for Retirement, Jira Service Module (services/jira.py), Retirement Workflow 5-Stage Process, retirement_workflow SQL Table (catalog_base_name keyed), Retirement Workflow Drawer (User Docs)

### Community 65 - "Overlap Analysis Page Redesign Design"
Cohesion: 0.33
Nodes (7): content_similarity Table, Overlap Analysis Page Redesign Design, Overlap vs Related Similarity (relationship_type), ContentOverlapPage.tsx Rewrite, Item-Centric Paginated Overlap Report, db/similarity.py Module Extraction, Content Overlap Page (User Docs)

### Community 66 - "routes/catalog.py"
Cohesion: 0.37
Nodes (21): field_validator, ContentPathRequest, DurationRequest, NoteRequest, OverrideUrlRequest, BaseModel, Catalog routes — browsing, curation, refresh., TagRequest (+13 more)

### Community 67 - "rcars-login.sh"
Cohesion: 0.48
Nodes (5): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token()

### Community 68 - "config.py"
Cohesion: 0.29
Nodes (9): _call_anthropic(), _call_litemaas(), LLMResult, build_scaffold(), compose_answer(), Deterministic scaffold + narrow narrative call. Worst case: mediocre prose next…, test_answer_failure_degrades_to_scaffold(), test_compose_prepends_scaffold() (+1 more)

### Community 69 - "router.py"
Cohesion: 0.21
Nodes (20): RouterOutput, Scope, pattern_check(), Routing: pattern check, router LLM call (Task 9), resolve & verify ladder., Deterministic pre-router. Narrow by design — the LLM router is the main path., Catalog resolution: LB regex → name keyword overlap → embedding guesses. The…, Turns that produced results — clarification turns are skipped when resolving., resolve_and_verify() (+12 more)

### Community 70 - "api_keys table (SHA-256 hashed, role-scoped)"
Cohesion: 0.15
Nodes (14): API Authentication for External Access — Implementation Plan, api_keys table (SHA-256 hashed, role-scoped), ApiKeysPanel.tsx admin UI component, get_current_user() auth middleware (dev/SA/API key/proxy), POST /auth/token OAuth code exchange endpoint, Mandatory proxy_verification_secret enforcement, tools/rcars-login.py CLI login helper, API key role ceiling (never exceeds creator's role) (+6 more)

### Community 71 - "PatternFly 6 Migration Implementation Plan"
Cohesion: 0.29
Nodes (8): PatternFly 6 Migration Implementation Plan, Task 6: AdminPage split into Status/Sync/RecentJobs/Workloads pages, RcarsMasthead.tsx component, RcarsSidebar.tsx component, Task 4: Advisor Page + RecCard PF6 migration, useTheme() / useThemeProvider() hook, Rec Card: Duration Labels + Best Fit Button (Design), Duration source labeling rationale (LLM guess vs curated)

### Community 72 - "chat_sessions.py"
Cohesion: 0.16
Nodes (15): get_session_context(), log_chat_turn(), next_turn_index(), Any, Chat-session persistence and context building. Follows the db/similarity.py…, The router's view: last <=max_turns turns, fixed shape, no prose., session_owner_ok(), test_chat_append_checks_ownership() (+7 more)

### Community 73 - "seed_chat_fixtures"
Cohesion: 0.21
Nodes (13): fake_embedding(), Seeded fixture catalog for chat tests (also a foundation for the broader…, Deterministic 768-dim unit vector from the text hash. Signature is monkeypatch-…, seed_chat_fixtures(), test_scope_filter_restricts_pool(), db(), FakeLLM, _noop() (+5 more)

### Community 76 - "Fire-and-Forget Background Thread + HTMX Polling Pattern"
Cohesion: 0.67
Nodes (3): Fire-and-Forget Background Thread + HTMX Polling Pattern, Admin Action Feedback Implementation Plan, Async Advisor Query Implementation Plan

### Community 77 - "embeddings Table + MAX(similarity) Scoring"
Cohesion: 0.67
Nodes (3): embeddings Table + MAX(similarity) Scoring, Building the rcars-pgvector Image, rcars-pgvector Multi-Arch Image Build

### Community 78 - "route"
Cohesion: 0.22
Nodes (13): llm_eval, _extract_json(), Strip code fences / leading prose, then parse. Raises on failure., route(), _fake(), test_call_error_falls_back(), test_hallucinated_intent_falls_back_to_recommend(), test_malformed_then_valid_retries_once() (+5 more)

### Community 98 - "orchestrator.py"
Cohesion: 0.23
Nodes (11): build_evidence_pack(), Evidence pack: v1 graph expansion — one hop, code-driven, bounded. The budget…, process_turn(), The chat turn flow. LLM client injectable for the deterministic test tier., _scope_echo(), followup_chips(), db(), fixture (+3 more)

### Community 99 - "HistoryPage.tsx"
Cohesion: 0.19
Nodes (12): Candidate, catalogUrl(), FORMAT_COLORS, FORMAT_LABELS, RecCard(), RecCardProps, HistoryPage(), SessionDetail (+4 more)

### Community 100 - "File Map"
Cohesion: 0.17
Nodes (11): Dependency Graph, File Map, Global Constraints, Overlap Analysis Redesign Implementation Plan, Task 1: Schema + Config + Extract db/similarity.py, Task 2: Generalize Similarity Computation, Task 3: Item-Centric Paginated Overlap API, Task 4: Similar Items Relationship Type Filter (+3 more)

### Community 101 - "test_auth_security.py"
Cohesion: 0.11
Nodes (11): app_no_auth(), client(), fixture, parametrize, Security test suite for RCARS API authentication. Validates that all auth…, App with NO dev_user — all auth enforced., TestExpiredApiKey, TestRevokedApiKey (+3 more)

### Community 102 - "test_chat_live.py"
Cohesion: 0.24
Nodes (10): integration, db(), _noop(), fixture, End-to-end chat integration tests — real LLM calls against seeded DB. Tests…, Query a specific item by LB number — expect item_facts intent and item card., Query outside RCARS scope — expect out_of_scope intent., _settings() (+2 more)

### Community 104 - "logging.py"
Cohesion: 0.35
Nodes (9): BoundLogger, _add_component(), get_logger(), setup_logging(), cleanup_orphaned_jobs(), shutdown(), startup(), test_logger_outputs_json() (+1 more)

### Community 105 - "Retirement Analysis (doc)"
Cohesion: 0.20
Nodes (10): Catalog Backfill (zero-value items for full coverage), Cost Methodology: All-Environment Cost Amortized to Prod, Jira Retirement Ticket Integration, Percentile-Based Retirement Scoring, Why provisions_summary Instead of Raw provisions Table, Retirement Workflow Lifecycle (approve→notify→start→retired), Retirement Analysis (doc), performance_channels table (+2 more)

### Community 106 - "Advisor Chat — Multi-Intent Architecture"
Cohesion: 0.20
Nodes (8): Adding an Intent, Advisor Chat — Multi-Intent Architecture, Backend Modules, Configuration, Core Principles, Frontend Structure, Intent Registry, Turn Flow

### Community 107 - "scan.py"
Cohesion: 0.27
Nodes (9): Exception, classify_scan_error(), Classify a scan error and return (error_class, human_message)., _propagate_to_sibling(), Analysis/scan worker tasks., Strip LLM-hallucinated keys from format_suitability — only demo and…, Propagate analysis + embeddings to a single sibling CI., run_analysis() (+1 more)

### Community 108 - "Scan Pipeline (doc)"
Cohesion: 0.25
Nodes (9): Two-Phase Change Detection (git ls-remote + content hash), Scan Error Classification (jinja_url, timeout, etc.), No-Match Behavior (fail honestly vs widen cutoff), 768-dim Vector Embeddings (nomic-embed-text-v1.5 via vLLM), Scan Pipeline (doc), Stale Showroom Detection Implementation Plan, Scan Failures & Catalog Visibility Implementation Plan, analyzer.py (Scan Pipeline Implementation) (+1 more)

### Community 109 - "Session Model & Multi-Turn"
Cohesion: 0.25
Nodes (8): Context builder, History page, Ownership, Persisted per turn (`db/chat_sessions.py`; columns via `ALTER TABLE ADD COLUMN IF NOT EXISTS`), Reference-resolution conventions (fixed rules), Resuming sessions, Session ≠ job, Session Model & Multi-Turn

### Community 110 - "test_app.py"
Cohesion: 0.25
Nodes (3): client(), fixture, test_auth_me_unauthenticated()

### Community 111 - "test_chat_api.py"
Cohesion: 0.33
Nodes (4): client(), non_admin_client(), fixture, Tests for POST /advisor/chat endpoint.

### Community 112 - "test_chat_handlers.py"
Cohesion: 0.71
Nodes (6): _noop(), _res(), _settings(), test_item_facts_handler(), test_overlap_handler(), test_performance_handler_rows_match_scope()

### Community 113 - "Tools, Grounding & Graph-Shaped Retrieval"
Cohesion: 0.33
Nodes (6): `depth` parameter, Evidence pack (v1 graph expansion: one hop, code-driven, bounded), Grounding rule, Scale posture (vector + relational vs. graph DB), Tool layer, Tools, Grounding & Graph-Shaped Retrieval

### Community 114 - "test_chat_registry.py"
Cohesion: 0.33
Nodes (4): build_router_prompt(), test_examples_validate_as_router_output(), test_followup_chips_are_pre_routed(), test_prompt_contains_every_intent_and_context()

### Community 115 - "WorkloadsPage.tsx"
Cohesion: 0.33
Nodes (5): StatusFilter, UnmappedWorkload, VerificationFilter, WorkloadMapping, WorkloadsPage()

### Community 116 - "Intents & Router Contract"
Cohesion: 0.40
Nodes (5): Intents & Router Contract, Router contract, V1 intent registry, Validation & fallback ladder (all deterministic), What LLMs decide vs. what code decides

### Community 117 - "Architecture"
Cohesion: 0.50
Nodes (4): Architecture, Backend modules, Frontend, Turn flow (in the worker)

### Community 118 - "UX"
Cohesion: 0.50
Nodes (4): Evidence pane (right), Progress streaming, Transcript (left pane), UX

### Community 119 - "Testing"
Cohesion: 0.50
Nodes (4): Relation to the testing backlog item, Running the tests, Testing, Tiers

## Knowledge Gaps
- **274 isolated node(s):** `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER`, `RCARS_ADMIN_EMAILS_STR`, `RCARS_CURATOR_EMAILS_STR` (+269 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Content Overlap Detection (doc)` connect `Content Overlap Detection (doc)` to `System Design (doc)`, `admin.py`, `Scan Pipeline (doc)`, `Recommendation Engine (doc)`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Why does `Database` connect `Database` to `cli.py`, `pipeline.py`, `analyzer.py`, `settings.py`, `admin.py`, `derive_status`, `Settings`, `test_db.py`, `Any`, `_generate_key`, `handlers.py`, `app.py`, `extract_base_name`, `call_llm`, `router.py`, `chat_sessions.py`, `seed_chat_fixtures`, `.complete_job`, `.retire_removed_items`, `.__init__`, `.prune_expired_api_keys`, `.prune_old_jobs`, `.revoke_user_cli_keys`, `orchestrator.py`, `test_chat_live.py`, `logging.py`, `db`, `db`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Why does `Settings` connect `Settings` to `cli.py`, `pipeline.py`, `get_current_user`, `analyzer.py`, `settings.py`, `admin.py`, `routes/auth.py`, `advisor.py`, `handlers.py`, `app.py`, `TestRevokeApiKey`, `call_llm`, `config.py`, `router.py`, `seed_chat_fixtures`, `TestTokenExchange`, `route`, `orchestrator.py`, `test_auth_security.py`, `test_chat_live.py`, `TestCreateApiKey`, `logging.py`, `test_app.py`, `test_chat_api.py`, `test_chat_handlers.py`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Database` (e.g. with `HandlerResult` and `Resolution`) actually correct?**
  _`Database` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `Settings` (e.g. with `ChatRequest` and `QueryRequest`) actually correct?**
  _`Settings` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `JobProgressRelay` (e.g. with `ChatRequest` and `QueryRequest`) actually correct?**
  _`JobProgressRelay` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RCARS_DATABASE_URL`, `RCARS_REDIS_URL`, `RCARS_DEV_USER` to the rest of the system?**
  _274 weakly-connected nodes found - possible documentation gaps or missing edges._