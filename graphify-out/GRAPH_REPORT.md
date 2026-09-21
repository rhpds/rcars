# Graph Report - .  (2026-09-18)

## Corpus Check
- 69 files · ~454,224 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2518 nodes · 5080 edges · 182 communities (119 shown, 63 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 275 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Auth Middleware
- Database Layer
- Advisor Frontend
- Ansible Deployment
- CLI Commands
- Frontend Config
- Catalog Service
- Analysis API Routes
- Catalog API Routes
- Admin API Routes
- Showroom Analyzer
- Architecture Docs
- Browse UI Components
- Overlap Assessment
- Retirement Workflow
- Design Specs
- Vector Search
- Recommender Pipeline
- Worker Ops
- Migration Scripts
- FastAPI App
- Test Fixtures
- Content Overlap DB
- OSSPA Sync
- Workload Scanner
- Configuration
- Structured Logging
- Jira Integration
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 171
- Community 173
- Community 174
- Community 175
- Community 176
- Community 178
- Community 181

## God Nodes (most connected - your core abstractions)
1. `Database` - 250 edges
2. `Settings` - 161 edges
3. `load_vocabulary()` - 62 edges
4. `run_osspa_sync()` - 31 edges
5. `normalize_analysis()` - 28 edges
6. `parse_analysis_response()` - 27 edges
7. `call_llm()` - 26 edges
8. `seed_chat_fixtures()` - 25 edges
9. `_make_request()` - 24 edges
10. `create_app()` - 22 edges

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

## Communities (182 total, 63 thin omitted)

### Community 0 - "Auth Middleware"
Cohesion: 0.05
Nodes (43): dict, _check_api_key_role_ceiling(), _fetch_group_members(), _get_cached_role_assignments(), get_current_user(), invalidate_role_assignments_cache(), _log_auth_decision(), _parse_sa_allowlist() (+35 more)

### Community 2 - "Advisor Frontend"
Cohesion: 0.06
Nodes (41): BlockErrorBoundary, Props, State, InfraDetailBlock(), InfraDetailBlockProps, catalogUrl(), ItemCardBlock(), ItemCardBlockProps (+33 more)

### Community 3 - "Ansible Deployment"
Cohesion: 0.07
Nodes (58): RCARS OCP Deployment Playbook, Ansible kubernetes.core Collection Requirement, Apply Infra Manifests Task, Apply App Manifests Task, Build API Task, Build Frontend Task, Management RBAC Bootstrap Task, Namespace Creation Task (+50 more)

### Community 4 - "CLI Commands"
Cohesion: 0.08
Nodes (53): argument, command, option, pass_context, flag(), get_db(), infra_stats(), init_db() (+45 more)

### Community 5 - "Frontend Config"
Cohesion: 0.04
Nodes (48): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, @patternfly/react-core, @patternfly/react-icons, @patternfly/react-table (+40 more)

### Community 6 - "Catalog Service"
Cohesion: 0.07
Nodes (39): _apply_component_inheritance(), CatalogReader, _collect_bases(), component_item_to_ci_name(), extract_base_ci_refs(), extract_catalog_item(), _extract_from_dict(), extract_infrastructure_metadata() (+31 more)

### Community 7 - "Analysis API Routes"
Cohesion: 0.14
Nodes (44): analyze_single(), approve_item(), ApproveRequest, _base_name_to_content_id(), cancel_workflow(), check_stale(), _extract_base_name_from_content_id(), get_workflow() (+36 more)

### Community 8 - "Catalog API Routes"
Cohesion: 0.14
Nodes (41): field_validator, add_tag(), catalog_facets(), catalog_stats(), ContentPathRequest, DurationRequest, flag_item(), get_analysis() (+33 more)

### Community 9 - "Admin API Routes"
Cohesion: 0.11
Nodes (42): add_role_assignment(), delete_role_assignment(), generate_vocabulary(), get_job(), get_vocabulary(), get_vocabulary_unknowns(), list_jobs(), list_role_assignments() (+34 more)

### Community 10 - "Showroom Analyzer"
Cohesion: 0.08
Nodes (39): analyze_showroom(), build_infrastructure_embedding_text(), build_module_embedding_text(), check_showroom_stale(), clone_showroom(), filter_boilerplate_files(), _get_embedding_client(), get_repo_head() (+31 more)

### Community 11 - "Architecture Docs"
Cohesion: 0.06
Nodes (38): CLI Admin Guide, Worker Management, Advisor Chat System, Evidence Pack, Infrastructure Intent, Overlap Intent, Performance Intent, Recommend Intent (+30 more)

### Community 12 - "Browse UI Components"
Cohesion: 0.09
Nodes (26): getPageNumbers(), Pagination(), PaginationProps, WorkloadMultiSelect(), WorkloadMultiSelectProps, architectureDetailUrl(), architectureSubline(), ASSET_TYPE_LABELS (+18 more)

### Community 13 - "Overlap Assessment"
Cohesion: 0.10
Nodes (32): assess_overlap(), batch_assess_overlaps(), _build_assessment_prompt(), _load_analysis_pair(), Assess overlap between two content items via LLM. Returns (assessment_dict,…, Assess all unassessed or stale overlap candidates. Returns summary:…, Validate LLM assessment response and coerce to canonical form. Returns None if…, Load showroom_analysis + content_entities for both items. (+24 more)

### Community 14 - "Retirement Workflow"
Cohesion: 0.07
Nodes (20): derive_status(), Retirement workflow business logic., Derive the workflow status from the highest completed step., Tests for retirement workflow business logic (derive_status)., Test derive_status with various step combinations., Validate STEP_ORDER constant structure., Retired should be first (highest priority), reviewed last., With no step timestamps, status defaults to 'reviewed'. (+12 more)

### Community 15 - "Design Specs"
Cohesion: 0.08
Nodes (34): Retirement Analysis Integration Design, Nightly Reporting Sync Pipeline, Reporting Metrics Table, Retirement Scoring Formula (0-100, Higher = Stronger Candidate), PatternFly 6 Migration Design, Navigation Restructure (Flattened Nav with Role-Gated Sections), RCARS Theme Architecture (Light/Dark Mode), Retirement Workflow Actions Design (+26 more)

### Community 16 - "Vector Search"
Cohesion: 0.07
Nodes (6): Any, Queue rows, ranked by occurrences descending. status=None returns all., Record an admin decision. Staged only — nothing about analysis changes until a…, Get analysis for any content type — routes to the right table., Upsert a Babylon catalog item across content_entities + babylon_items in one…, Upsert one OSSPA row across content_entities + portfolio_architectures. Also…

### Community 17 - "Recommender Pipeline"
Cohesion: 0.09
Nodes (31): _apply_duration_penalty(), _apply_usage_boost(), _extract_duration_target(), extract_urls(), QueryState, Three-phase recommendation pipeline with async progress callbacks., Apply a soft score penalty based on duration overshoot. Gentle: a 2x overshoot…, Boost relevance scores for candidates with proven usage. Looks up… (+23 more)

### Community 18 - "Worker Ops"
Cohesion: 0.11
Nodes (27): asyncio, Future, _progress_bridge(), Ops worker tasks — catalog refresh, stale check, nightly maintenance pipeline., Babylon sub-pipeline: catalog refresh → stale check → re-analyze →…, Further deduplicate ref-based scan items by resolving refs to commit SHAs.…, Scan agDv2 workload repos, analyze roles via LLM, update mappings., Let the synchronous sync publish SSE progress from its worker thread. Returns… (+19 more)

### Community 19 - "Migration Scripts"
Cohesion: 0.16
Nodes (30): Connection, cmd_export(), cmd_import_notes(), cmd_import_sessions(), cmd_import_token_usage(), cmd_import_workflows(), cmd_migrate(), _column_exists() (+22 more)

### Community 20 - "FastAPI App"
Cohesion: 0.10
Nodes (18): FastAPI, create_app(), lifespan(), client(), fixture, test_auth_me_unauthenticated(), client(), fixture (+10 more)

### Community 21 - "Test Fixtures"
Cohesion: 0.09
Nodes (15): db(), db_with_perf_data(), fixture, Seed test data for filtered catalog queries., Seed performance data for testing., _seed_items(), test_filtered_catalog_agd_config(), test_filtered_catalog_cloud_provider() (+7 more)

### Community 22 - "Content Overlap DB"
Cohesion: 0.11
Nodes (28): Chip, RouterOutput, _prefix_overlap(), Count keyword matches allowing prefix matching for words >= min_prefix chars., _expand_vocab_aliases(), _extract_json(), _find_keyword_ties(), _parse_catalog_url() (+20 more)

### Community 23 - "OSSPA Sync"
Cohesion: 0.12
Nodes (29): compute_content_hash(), is_tracked_at_head(), Safe join with canonical containment. None means reject the row., True only if the file exists in the HEAD tree — not merely on disk., Drop ++++ passthrough blocks and HTML/Arcade comments — no text signal., Read one DetailPage. None means skip the row (unsafe, missing, untracked)., SHA-256 of the FULL adoc body plus the CSV fields that feed the prompt., read_detail_adoc() (+21 more)

### Community 24 - "Workload Scanner"
Cohesion: 0.11
Nodes (26): analyze_config(), analyze_role(), discover_roles(), _follow_task_includes(), _normalize_products(), Path, Workload repo scanner — clone agDv2 collection repos, read role code, LLM-…, Read key files from an Ansible role for LLM analysis. (+18 more)

### Community 25 - "Configuration"
Cohesion: 0.11
Nodes (18): BaseSettings, _parse_csv(), Settings, migrate(), One-time migration: export token_usage from old schema, create new schema,…, test_admin_check(), test_chat_intent_roles_invalid_role_rejected(), test_chat_intent_roles_parse() (+10 more)

### Community 26 - "Structured Logging"
Cohesion: 0.12
Nodes (23): BoundLogger, RedisSettings, _add_component(), get_logger(), _reorder_keys(), setup_logging(), Chat turn worker task — runs on the recommend queue., run_chat_turn() (+15 more)

### Community 27 - "Jira Integration"
Cohesion: 0.13
Nodes (27): _base_name_from_content_id(), build_retirement_description(), create_retirement_ticket(), _jira_request(), Jira REST API client for retirement ticket creation. Uses urllib (consistent…, Create a Jira retirement ticket. Returns the new Jira issue key (e.g.…, Make an HTTP request to the Jira REST API v3 with Basic auth. Returns parsed…, Derive catalog base name from content_id (e.g. 'babylon:foo.prod' → 'foo'). (+19 more)

### Community 28 - "Community 28"
Cohesion: 0.13
Nodes (26): health(), get, Request, readiness(), AuthMeResponse, CatalogItemWorkload, CatalogListResponse, ErrorDetail (+18 more)

### Community 29 - "Community 29"
Cohesion: 0.18
Nodes (23): Block, Chip, Clarify, Envelope, HelpArgs, InfrastructureArgs, ItemFactsArgs, OverlapArgs (+15 more)

### Community 30 - "Community 30"
Cohesion: 0.11
Nodes (20): App(), RcarsSidebar(), AuthContext, AuthState, defaultState, useAuthProvider(), AdminQueriesPage(), AdminRolesPage() (+12 more)

### Community 31 - "Community 31"
Cohesion: 0.14
Nodes (25): datetime, invalidate_api_key_cache(), _get_user_key(), Request, Per-user rate limiting via slowapi + Redis., auth_me(), create_api_key(), exchange_token() (+17 more)

### Community 32 - "Community 32"
Cohesion: 0.16
Nodes (19): PostgreSQL + pgvector database layer for RCARS v2., build_evidence_pack(), Evidence pack: v1 graph expansion — one hop, code-driven, bounded. The budget…, fake_embedding(), Seeded fixture catalog for chat tests (also a foundation for the broader…, Deterministic 768-dim unit vector from the text hash. Signature is monkeypatch-…, seed_chat_fixtures(), _settings() (+11 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (24): generate_overlap_candidates(), get_overlap_items(), get_overlap_stats(), prune_stale_candidates(), ConnectionPool, Deterministic overlap candidate generation via structured matching., Aggregate stats by verdict., Item-centric overlap report grouped by verdict. (+16 more)

### Community 34 - "Community 34"
Cohesion: 0.14
Nodes (20): Redis, create_sse_response(), JobProgressRelay, Redis pub/sub relay and SSE streaming for job progress., Subscribe to job progress. Yields message dicts, or None as keepalive., sse_stream(), translate_to_user_message(), publish_progress() (+12 more)

### Community 35 - "Community 35"
Cohesion: 0.21
Nodes (23): generate_embedding(), Generate a 768-dim embedding via the vLLM embedding server. Nomic requires task…, _detect_type_hint(), handle_help(), handle_infrastructure(), handle_item_facts(), handle_overlap(), handle_performance() (+15 more)

### Community 36 - "Community 36"
Cohesion: 0.10
Nodes (24): Action Verbs Validation Rules, Content Modes Mapping, Controlled Vocabulary, Difficulty Levels Taxonomy, Ignored Terms List, Platforms Taxonomy, Products Taxonomy, Solutions Taxonomy (+16 more)

### Community 37 - "Community 37"
Cohesion: 0.13
Nodes (13): _noise_variants(), Vocabulary, Post-analysis normalization — deterministic, runs once after parse. Nothing…, Rung 1: exact match on canonical or alias, case-insensitive. Rung 2: squash key…, Rung 3 candidates: strip known noise, then retry rungs 1-2 on each., Snap one value to its canonical form. Returns (result, matched). On a miss the…, _rungs_1_2(), snap_term() (+5 more)

### Community 38 - "Community 38"
Cohesion: 0.12
Nodes (14): _mode_for(), Vocabulary, The vocabulary block injected into analysis prompts. Two parts, and only two: a…, Build the injected block for a given content_entities.content_type., render_vocabulary_block(), clear_vocabulary_cache(), fixture, Tests for the controlled vocabulary loader, normalizer, and prompt renderer. (+6 more)

### Community 39 - "Community 39"
Cohesion: 0.12
Nodes (11): db(), _generate_key(), fixture, Tests for API key database CRUD operations., Ephemeral test database — uses RCARS_DATABASE_URL from env (rcars_test)., Generate a raw key, its hash, and its prefix., TestCreateApiKey, TestGetApiKeyByHash (+3 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (22): DOM, DOM.Iterable, ES2020, src, compilerOptions, allowImportingTsExtensions, isolatedModules, jsx (+14 more)

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (22): _advisor_limit(), ChatRequest, get_query_result(), get_session(), list_sessions(), BaseModel, get, limit (+14 more)

### Community 42 - "Community 42"
Cohesion: 0.09
Nodes (10): Return {base_name: content_id} for items with no active prod-stage variant., Tests for get_nonprod_base_names — requires live DB with test data., Verify the nonprod routes exist on the analysis router., TestGetNonprodBaseNames, TestListNonprodItems, TestNonprodIgnore, TestNonprodRouteExists, TestNonprodSchema (+2 more)

### Community 43 - "Community 43"
Cohesion: 0.09
Nodes (9): db(), fixture, Tests for the vocabulary_unknown_terms queue. Requires a live PostgreSQL., Vocabulary work never sets enrichment_review_needed or review_reasons., TestGetUnknownTerms, TestRecordUnknownTerm, TestResolveUnknownTerm, TestReviewBadgeUntouched (+1 more)

### Community 44 - "Community 44"
Cohesion: 0.17
Nodes (17): _call_anthropic(), _call_litemaas(), call_llm(), LLMResult, Unified LLM call with automatic provider routing. LiteMaaS preferred if…, build_scaffold(), compose_answer(), Deterministic scaffold + narrow narrative call. Worst case: mediocre prose next… (+9 more)

### Community 45 - "Community 45"
Cohesion: 0.22
Nodes (21): asset_type_tokens(), content_id_for(), parse_palist_csv(), Apply the ingestion gate. Keep a row when it carries at least one of PA/VP/SP,…, Parse PAList.csv. Raises OsspaSyncError if the header is not usable., scope_rows(), _csv_row(), parametrize (+13 more)

### Community 46 - "Community 46"
Cohesion: 0.14
Nodes (21): _build_closed_sql(), _build_cost_sql(), _build_nonprod_provisions_sql(), _build_provisions_quarter_sql(), _build_provisions_sql(), _build_touched_sql(), _build_unique_users_window_sql(), _merge_published_base_pairs() (+13 more)

### Community 47 - "Community 47"
Cohesion: 0.16
Nodes (16): fmt(), fmtRoi(), num(), scoreBg(), ScoreBreakdownPopover(), scoreColor(), stageBadgeClass, WorkflowDrawer() (+8 more)

### Community 48 - "Community 48"
Cohesion: 0.15
Nodes (9): normalize_analysis(), Any, Snap aliases to canonical forms and dedup topics, before write. Pure when db is…, Upsert one row per distinct term. Never touches the item's review flags., _record_unknowns(), Keys absent from an analyzer's output are skipped — one map, two sources., A term in ignored_terms is stored verbatim but never recorded., TestIgnoredTermsSuppression (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.17
Nodes (19): db_pull(), frontend_only(), init_db(), RCARS_ADMIN_EMAILS_STR, RCARS_CURATOR_EMAILS_STR, RCARS_DATABASE_URL, RCARS_DEV_USER, RCARS_EMBEDDING_URL (+11 more)

### Community 50 - "Community 50"
Cohesion: 0.13
Nodes (11): _build_expansion_map(), _expand_query_terms(), Invert the vocabulary's product aliases into term -> canonical name. Aliases…, Expand product names, acronyms, and synonyms for better embedding match. One…, parametrize, Word-boundary matching — RHOAI inside RHOAIX must not expand., GitOps must still pull in ArgoCD and Argo CD as recall terms., search_terms widen recall only — they never snap a value. (+3 more)

### Community 51 - "Community 51"
Cohesion: 0.17
Nodes (12): _as_tuple(), _build_lookups(), load_vocabulary(), _parse_entries(), Any, Vocabulary, Vocabulary loading, path resolution, and fail-fast validation. Cached once per…, Load, validate, and cache the controlled vocabulary for this process. (+4 more)

### Community 52 - "Community 52"
Cohesion: 0.11
Nodes (11): app_no_auth(), client(), fixture, parametrize, Security test suite for RCARS API authentication. Validates that all auth…, App with NO dev_user — all auth enforced., TestExpiredApiKey, TestRevokedApiKey (+3 more)

### Community 53 - "Community 53"
Cohesion: 0.15
Nodes (14): get_session_context(), log_chat_turn(), next_turn_index(), Any, Chat-session persistence and context building. Follows the db/similarity.py…, The router's view: last <=max_turns turns, fixed shape, no prose., session_owner_ok(), test_chat_append_checks_ownership() (+6 more)

### Community 54 - "Community 54"
Cohesion: 0.16
Nodes (12): _entries_to_dicts(), generate_vocabulary_yaml(), _header_comment(), Any, Vocabulary, Emit a merged vocabulary.yaml — current file plus staged admin decisions.…, Preserve the active vocabulary file's leading comment block., Merge staged decisions into the loaded vocabulary and serialize. aliased → term… (+4 more)

### Community 55 - "Community 55"
Cohesion: 0.18
Nodes (16): parse_analysis_response(), Parse Sonnet's JSON response, handling markdown fences., format_triage_candidates(), QueryState, Phase 2 — Haiku triage for relevance scoring., Format candidates compactly for the triage prompt., Send candidates to Haiku for relevance triage. Returns QueryState with phase…, triage() (+8 more)

### Community 56 - "Community 56"
Cohesion: 0.18
Nodes (16): clone_examples_repo(), expand_includes(), fetch_palist_csv(), file_commit_sha(), get_head_sha(), OsspaSyncError, CompletedProcess, Exception (+8 more)

### Community 57 - "Community 57"
Cohesion: 0.37
Nodes (17): Full OSSPA sync. Synchronous by design — the worker wraps it in one…, run_osspa_sync(), _csv(), _stub_csv(), test_clone_failure_aborts_before_any_db_write(), test_empty_active_set_aborts_without_retiring(), test_empty_active_set_with_confirmation_retires_everything(), test_force_reanalyzes_unchanged_items() (+9 more)

### Community 58 - "Community 58"
Cohesion: 0.16
Nodes (12): Controlled vocabulary — one list, two consumers (analysis + query expansion)., Exception, Controlled vocabulary data model. The vocabulary is a source-agnostic list of…, Raised when vocabulary.yaml is malformed. Fail fast at load., Casefold and strip every non-alphanumeric character. One mechanism, two uses:…, One canonical name and everything that should resolve to it. aliases —…, True when an admin has rejected this term for this dimension., squash_key() (+4 more)

### Community 59 - "Community 59"
Cohesion: 0.22
Nodes (17): build_product_entry(), _fetch(), fetch_all_products(), fetch_product_detail(), _find_current_match(), load_current_vocabulary(), main(), Any (+9 more)

### Community 60 - "Community 60"
Cohesion: 0.16
Nodes (16): _extract_links(), fetch_event_content(), _fetch_html(), _find_content_pages(), parse_event_url(), Any, Event URL parser. Fetches event web pages, follows links to…, Filter links to those that look like schedule/program/content pages. (+8 more)

### Community 61 - "Community 61"
Cohesion: 0.19
Nodes (16): analyze_architecture_item(), build_architecture_embedding_text(), build_architecture_prompt(), Split the template into (system_prompt, user_message)., One embedding per item — summary plus all extracted signal fields., LLM analysis → vocabulary normalization → analysis row → card → embedding., db(), fixture (+8 more)

### Community 62 - "Community 62"
Cohesion: 0.16
Nodes (9): client(), db(), fixture, _second_architecture(), settings(), test_audience_filter_applies_across_content_types(), test_facets_include_solutions_verticals_and_audience(), test_solutions_filter_narrows_to_matching_architectures() (+1 more)

### Community 63 - "Community 63"
Cohesion: 0.17
Nodes (7): build_embedding_text(), Build text for CI-level embedding from analysis results., clear_vocabulary_cache(), fixture, Advisor query expansion, now backed by the controlled vocabulary. Formerly…, TestBuildEmbeddingText, TestOldFileGone

### Community 64 - "Community 64"
Cohesion: 0.17
Nodes (15): classify_scan_error(), Exception, Classify a scan error and return (error_class, human_message)., Clear old embeddings and store fresh ones for a content_id atomically. Returns…, regenerate_embeddings(), Scan a single collection repo. Returns stats dict., Scan all (or filtered) agDv2 collection repos., scan_all_collections() (+7 more)

### Community 65 - "Community 65"
Cohesion: 0.18
Nodes (11): db(), fixture, _row(), test_advisory_lock_is_not_reentrant_across_sessions(), test_architecture_analysis_staleness_round_trip(), test_curator_note_and_flag_are_source_aware(), test_ensure_architecture_analysis_row_is_stale(), test_retire_missing_osspa_only_touches_portfolio_arch() (+3 more)

### Community 66 - "Community 66"
Cohesion: 0.18
Nodes (13): API_DOCS_URL, DbStatus, formatAge(), getInitials(), RcarsMasthead(), useAuth(), applyTheme(), getInitialTheme() (+5 more)

### Community 67 - "Community 67"
Cohesion: 0.20
Nodes (7): compute_performance_score(), compute_performance_score_breakdown(), _compute_performance_score_with_breakdown(), Internal: compute score and return (breakdown_dict, final_score)., Compute performance score 0-100 using percentile ranks. Higher = stronger…, Return the full score breakdown dict (factors + explanation)., TestComputePerformanceScore

### Community 68 - "Community 68"
Cohesion: 0.14
Nodes (9): ContentOverlapPage(), DrawerPair, extractSummary(), ItemSummary, NeighborItem, OverlapAssessment, OverlapItem, OverlapStats (+1 more)

### Community 69 - "Community 69"
Cohesion: 0.19
Nodes (12): Candidate, catalogUrl(), FORMAT_COLORS, FORMAT_LABELS, RecCard(), RecCardProps, HistoryPage(), SessionDetail (+4 more)

### Community 70 - "Community 70"
Cohesion: 0.16
Nodes (11): VocabularyPage(), MarketingMetrics, NonProdDashboardResponse, PerformanceDashboardResponse, RetirementWorkflow, RoleAssignment, SalesMetrics, ScoreBreakdown (+3 more)

### Community 71 - "Community 71"
Cohesion: 0.15
Nodes (13): Async Job Pattern, Green/Yellow/White Tier System, Three-Tier Rearchitecture, ECA Production Redesign Spec, RCARS Web UI Design Spec, OpenShift Deployment Spec, Catalog Refresh Feedback Spec, Async Advisor Query Spec (+5 more)

### Community 72 - "Community 72"
Cohesion: 0.15
Nodes (13): group, cli(), infra_group(), osspa_group(), RCARS — RHDP Content Advisory & Recommendation System., Infrastructure metadata commands., Workload mapping and scanning commands., Reporting database metrics commands. (+5 more)

### Community 73 - "Community 73"
Cohesion: 0.46
Nodes (12): RouterOutput, Scope, resolve_and_verify(), test_scope_shapes(), asyncio, test_lb_ref_resolves(), test_low_confidence_clarifies(), test_role_gate_redirects() (+4 more)

### Community 74 - "Community 74"
Cohesion: 0.15
Nodes (6): client(), fixture, Tests for API key management endpoints., TestCreateApiKey, TestListApiKeys, TestRevokeApiKey

### Community 75 - "Community 75"
Cohesion: 0.20
Nodes (12): Content Model Normalization, Intent-Based Chat Routing, Overlap Analysis Redesign, Performance Scoring Formula, Reporting MCP Data Sync, Retirement Workflow, Retirement Analysis Integration Plan, Retirement Workflow Actions Plan (+4 more)

### Community 76 - "Community 76"
Cohesion: 0.27
Nodes (10): _arch(), db(), fixture, test_browse_babylon_only_facet_still_works(), test_browse_default_content_types_exclude_architectures(), test_browse_mixed_content_types_return_both_sources(), test_browse_returns_prod_architectures_with_stage_prod(), test_browse_shows_dev_architectures_for_curators() (+2 more)

### Community 77 - "Community 77"
Cohesion: 0.32
Nodes (4): Every document is built from one helper so indentation stays uniform —…, TestPathOverride, TestValidation, write_vocab()

### Community 78 - "Community 78"
Cohesion: 0.18
Nodes (5): LogWindow(), LogWindowProps, ActionState, ScheduleInfo, SyncPage()

### Community 79 - "Community 79"
Cohesion: 0.24
Nodes (9): get_recommendations(), BaseModel, limit, post, Request, Recommendations endpoint for external integrations. Low effort runs inline…, RecommendationRequest, _run_low() (+1 more)

### Community 80 - "Community 80"
Cohesion: 0.27
Nodes (3): extract_base_name(), Strip stage suffix from an RCARS ci_name to get the reporting DB base name., TestExtractBaseName

### Community 81 - "Community 81"
Cohesion: 0.20
Nodes (6): build_analysis_prompt(), Truncate content to max characters., Build analysis prompt split into system instructions and user data.…, truncate_content(), build_analysis_prompt slices the template; only the Instructions section…, TestPromptInjection

### Community 82 - "Community 82"
Cohesion: 0.44
Nodes (10): Mark queued jobs as failed if they have no entry in their arq queue. For each…, _reconcile_queued_orphans(), _mock_db(), asyncio, Tests for queued-job orphan reconciliation (RHDPCD-258)., test_job_present_in_redis_is_not_failed(), test_no_queued_jobs_skips_redis(), test_orphan_not_in_redis_is_failed() (+2 more)

### Community 83 - "Community 83"
Cohesion: 0.29
Nodes (7): patch, _mcp_call(), mcp_query(), Call an MCP tool via HTTP JSON-RPC, return parsed JSON result., Execute SQL via MCP server, auto-paginating past 500-row cap., Build a mock urllib response for an MCP query result., TestMcpPagination

### Community 84 - "Community 84"
Cohesion: 0.36
Nodes (8): integration, _noop(), End-to-end chat integration tests — real LLM calls against seeded DB. Tests…, Query a specific item by LB number — expect item_facts intent and item card., Query outside RCARS scope — expect out_of_scope intent., _settings(), test_live_item_facts_turn(), test_live_out_of_scope()

### Community 85 - "Community 85"
Cohesion: 0.28
Nodes (6): Candidate, QueryState, Data models for the recommendation pipeline., A content entity moving through the recommendation pipeline., Convert similarity score (0.0-1.0) to percentage., State of a recommendation query at a pipeline phase boundary.

### Community 86 - "Community 86"
Cohesion: 0.25
Nodes (5): candidates_with_performance(), Result serialization shared by the recommend worker and the chat layer., Convert QueryState candidates to JSON dicts with performance metrics. Exact…, compute_sales_impact(), Compute sales impact tier from closed amount.

### Community 87 - "Community 87"
Cohesion: 0.28
Nodes (8): QueryState, Phase 1 — vector search with quality threshold., Generate query embedding, search pgvector, apply quality threshold. The DB…, Remove grammatical filler words before embedding to reduce dilution., Find CI references in the query and return neighbors based on the referenced…, _resolve_ci_references(), search(), _strip_embedding_filler()

### Community 88 - "Community 88"
Cohesion: 0.28
Nodes (6): _build_windowed_metrics(), Build per-item windowed_metrics JSONB from per-window query results. For each…, Windowed metrics should have entries for all four windows., An item with zero provisions/sales in a window should score 0., Items with different provision counts should get different scores., TestBuildWindowedMetrics

### Community 89 - "Community 89"
Cohesion: 0.31
Nodes (4): Return the start date for a sliding window (today - N days)., _window_start(), Tests for reporting sync utilities., TestWindowStart

### Community 90 - "Community 90"
Cohesion: 0.25
Nodes (4): client(), fixture, Tests for GET /catalog/infrastructure endpoint and removal of old workload-…, seed_infrastructure()

### Community 91 - "Community 91"
Cohesion: 0.25
Nodes (4): clean_infra(), db(), fixture, Tests for infrastructure table DB operations.

### Community 92 - "Community 92"
Cohesion: 0.25
Nodes (8): NamedTuple, AdocRead, db(), fake_analyze(), fake_repo(), fixture, A clone stand-in whose adoc files always read successfully., settings()

### Community 93 - "Community 93"
Cohesion: 0.36
Nodes (8): _as_bool(), derive_osspa_status(), normalize_row(), Any, Map the raw CSV booleans into Babylon's status vocabulary., CSV row → the payload upsert_osspa_item takes., Comma-split a CSV cell into a deduped, order-preserving list., _split_list()

### Community 94 - "Community 94"
Cohesion: 0.39
Nodes (3): dedup_topics(), Collapse spelling variants of the same topic on the same item. Squash key…, TestTopicDedup

### Community 96 - "Community 96"
Cohesion: 0.25
Nodes (7): WorkflowItem, NonProdItemsPage(), SortField, stageBadgeClass, StatusFilter, TimeWindow, NonProdItem

### Community 97 - "Community 97"
Cohesion: 0.54
Nodes (7): cmd_logout(), _load_credentials(), main(), cmd_login(), cmd_status(), cmd_token(), _save_credentials()

### Community 98 - "Community 98"
Cohesion: 0.33
Nodes (7): Infrastructure-Aware Catalog Metadata, PatternFly 6 Theme Architecture, Server-Side Filtering, Browse Page Redesign Plan, PatternFly 6 Migration Plan, Infrastructure-Aware Catalog Metadata Spec, Browse Page Redesign Spec

### Community 99 - "Community 99"
Cohesion: 0.38
Nodes (7): API Authentication Design, API Key Authentication (X-API-Key Header), OAuth PKCE Login Flow, Proxy Verification Secret (Anti-Spoofing), Role Assignments Design, Role Assignments Table (DB-Backed Role Elevation), External API Tools Documentation

### Community 100 - "Community 100"
Cohesion: 0.29
Nodes (6): llm_eval, fixture, parametrize, Golden routing eval — real prompt assembly, real model, real validation. Hard-…, settings(), test_routing_golden()

### Community 101 - "Community 101"
Cohesion: 0.29
Nodes (4): build_router_prompt(), test_examples_validate_as_router_output(), test_followup_chips_are_pre_routed(), test_prompt_contains_every_intent_and_context()

### Community 102 - "Community 102"
Cohesion: 0.43
Nodes (3): _extrapolate_count(), Scale a count metric to fill a full window if the item is newer. Returns…, TestExtrapolateCount

### Community 103 - "Community 103"
Cohesion: 0.48
Nodes (5): json_get(), rcars-login.sh script, cmd_login(), cmd_status(), cmd_token()

### Community 104 - "Community 104"
Cohesion: 0.40
Nodes (3): BaseHTTPMiddleware, Request, RequestLoggingMiddleware

### Community 105 - "Community 105"
Cohesion: 0.60
Nodes (4): ApiKeyRow, ApiKeysPanel(), expiryLabel(), timeAgo()

### Community 106 - "Community 106"
Cohesion: 0.67
Nodes (4): API Key Authentication, OpenShift Group-Based Auth, API Authentication Plan, OpenShift Group Auth Plan

### Community 107 - "Community 107"
Cohesion: 0.50
Nodes (3): build_sandbox_summary(), Sandbox summary generation from infrastructure metadata and workload…, Assemble a sandbox summary from infrastructure metadata. workload_products:…

### Community 109 - "Community 109"
Cohesion: 0.67
Nodes (3): Backlog Jira Migration, Jira Epic RHDPCD-25 (RCARS Backlog), WORKLOG (Archived)

### Community 110 - "Community 110"
Cohesion: 0.67
Nodes (3): Curated Duration Override, Rec Card Duration and Best Fit Plan, Rec Card Duration and Best Fit Spec

### Community 111 - "Community 111"
Cohesion: 0.67
Nodes (3): Acronym Expansion, Controlled Vocabulary Plan, Controlled Vocabulary Design

### Community 115 - "Community 115"
Cohesion: 0.67
Nodes (3): db(), fixture, Create a fresh test database with schema.

## Knowledge Gaps
- **215 isolated node(s):** `rcars`, `rcars`, `docker-entrypoint.sh script`, `name`, `private` (+210 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **63 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database Layer` to `Community 128`, `Community 129`, `Community 130`, `Community 131`, `CLI Commands`, `Community 132`, `Community 133`, `Community 134`, `Community 135`, `Community 136`, `Showroom Analyzer`, `Overlap Assessment`, `Vector Search`, `Recommender Pipeline`, `FastAPI App`, `Test Fixtures`, `Content Overlap DB`, `Workload Scanner`, `Configuration`, `Structured Logging`, `Community 29`, `Community 32`, `Community 33`, `Community 34`, `Community 35`, `Community 39`, `Community 42`, `Community 43`, `Community 53`, `Community 57`, `Community 61`, `Community 62`, `Community 64`, `Community 65`, `Community 73`, `Community 76`, `Community 80`, `Community 84`, `Community 87`, `Community 90`, `Community 91`, `Community 92`, `Community 112`, `Community 113`, `Community 114`, `Community 115`, `Community 120`, `Community 121`, `Community 122`, `Community 123`, `Community 124`, `Community 125`, `Community 126`, `Community 127`?**
  _High betweenness centrality (0.163) - this node is a cross-community bridge._
- **Why does `Settings` connect `Configuration` to `Auth Middleware`, `CLI Commands`, `Analysis API Routes`, `Catalog API Routes`, `Admin API Routes`, `Showroom Analyzer`, `Overlap Assessment`, `Recommender Pipeline`, `Worker Ops`, `FastAPI App`, `Content Overlap DB`, `Structured Logging`, `Community 29`, `Community 31`, `Community 32`, `Community 34`, `Community 35`, `Community 41`, `Community 44`, `Community 52`, `Community 54`, `Community 57`, `Community 61`, `Community 62`, `Community 73`, `Community 74`, `Community 79`, `Community 84`, `Community 90`, `Community 92`, `Community 95`, `Community 100`, `Community 108`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `Database` (e.g. with `HandlerResult` and `Resolution`) actually correct?**
  _`Database` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 32 inferred relationships involving `Settings` (e.g. with `SyncOsspaRequest` and `ChatRequest`) actually correct?**
  _`Settings` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `load_vocabulary()` (e.g. with `generate_vocabulary()` and `get_vocabulary()`) actually correct?**
  _`load_vocabulary()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `run_osspa_sync()` (e.g. with `run_osspa_pipeline()` and `run_osspa_sync_job()`) actually correct?**
  _`run_osspa_sync()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `rcars`, `rcars`, `docker-entrypoint.sh script` to the rest of the system?**
  _215 weakly-connected nodes found - possible documentation gaps or missing edges._