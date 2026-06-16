# RCARS Worklog

Session handoff notes between developers. Read before starting work. Write before ending a session.

## Format

```
### YYYY-MM-DD — [who]

**Done:**
- What was accomplished

**In progress:**
- What was started but not finished

**Next:**
- What should be picked up next

**Blockers:**
- Anything blocking progress (optional)

**Notes:**
- Context that would help the next person (optional)
```

---

## Sessions

### 2026-06-16 — Nate + Claude (Retirement analysis + LiteMaaS + code review)

**Done:**
- **Retirement analysis (Phase 1) — full implementation and deployment:**
  - Alembic migration 005: `reporting_metrics` table with retirement_score index
  - MCP HTTP client with auto-pagination past 500-row server cap, HTTPS-only validation
  - Nightly sync step 5 in maintenance pipeline: provisions, sales, cost, dates from RHDP reporting MCP
  - Retirement scoring (0-100) based on usage, sales, cost, prod presence, age
  - CLI commands: `rcars reporting-db sync/status/show`
  - API: `GET /analysis/retirement` dashboard, `POST /admin/sync-reporting` trigger
  - Catalog detail and rec candidates enriched with reporting metrics (provisions, cost/provision, sales impact badge)
  - Frontend: Retirement page under Content Analysis with stat cards grid (total, high, review, keepers, cost, closed, touched), sortable table with sticky headers, expandable detail rows with environment badges
  - Bug fix: `get_all_base_names_with_prod()` KeyError on dict_row cursor — used named column + explicit cursor
  - Pipeline step messages clarified: removed "/3" denominators, human-readable descriptions for all 5 steps
- **LiteMaaS as primary LLM provider:**
  - Unified `call_llm()` function with per-model routing — LiteMaaS (OpenAI SDK) preferred, Vertex AI (Anthropic SDK) as automatic fallback
  - Model list cached once at worker startup from `/v1/models` endpoint
  - `provider` column added to `token_usage` table (migration 006), threaded through all 5 LLM call sites
  - Admin Status page: LLM Provider card (active providers, models) + Reporting Sync card (items synced, orphans, last synced)
  - Admin Token Usage page: Provider column with color-coded display
  - Both providers can be configured simultaneously — if LiteMaaS drops a model, next restart routes to Vertex automatically
  - Config: `RCARS_LITEMAAS_URL`, `RCARS_LITEMAAS_API_KEY`
- **Content Analysis UI unification:**
  - Shared `ca-*` CSS classes in lcars.css matching the standalone analysis.html reference design
  - Both Overlap and Retirement pages now use identical fonts, colors, controls, stat cards, and layout
  - Overlap page: search filter, full summary text (no truncation), Browse links open in new tab
  - Retirement page: stat cards grid, full-width table with `table-layout: fixed`, score badges with colored backgrounds, name column 40% width, default sort by lowest score first (healthy assets first)
  - Numbers format to $X.XXB for billions
- **Code review remediation (15 findings fixed):**
  - LiteMaaS API key and reporting MCP token moved from plain env vars to K8s Secrets with `secretKeyRef`
  - NOT NULL constraint on provider column
  - Defensive empty-response checks in both LLM providers
  - Pagination safety cap (50 pages max) on `mcp_query`
  - Null guard on `avg_cost_per_provision` float conversion
  - GROUP BY COALESCE fix for provider stats
  - Orphan job handling on sync-reporting enqueue failure
  - Reporting status endpoint checks both URL and token, queries both job types
  - Rationale prompt example fixed (single enum value)
  - Workload scanner variable shadowing (`result` → `llm_result`)
  - Redundant CLI imports removed, `.catch()` on admin API calls, keyed Fragment in RetirementPage
  - Skipped 2 findings with justification (migration raw SQL is project convention, LIKE wildcard escape unnecessary for AgnosticV identifiers)
- **Ansible deployment fix:** `init-db` crash guard for `provider` index when column doesn't exist yet (CREATE TABLE IF NOT EXISTS skips existing tables)
- **Backlog updates:** babydev cluster migration, enhanced retirement scoring + data validation + time window filter

**In progress:**
- Production deployment running (`--tags deploy`)

**Next:**
- Verify production deployment (LiteMaaS routing, reporting sync, retirement dashboard)
- Retirement scoring Phase 2: data validation (closed amount discrepancy), time window filter, enhanced scoring model
- Babydev cluster migration (deadline: end of June 2026)
- Portfolio Architecture ingest from OSSPA GitLab

**Notes:**
- Migration race condition: `--tags update` can run `alembic upgrade head` on the old pod before the new build rolls out. Happened with migration 006 on dev. Workaround: run `--tags migrate` separately after build completes, or use `--tags deploy` which sequences correctly. Consider adding build SHA verification to the migration step.
- LiteMaaS URL: `https://maas-rhdp.apps.maas.redhatworkshops.io/v1`. Models available: `claude-haiku-4-5`, `claude-sonnet-4-6`. API key stored as K8s Secret.
- Reporting MCP URL: `https://reporting-mcp.apps.ocpv-infra01.dal12.infra.demo.redhat.com/mcp/`. Token stored as K8s Secret.
- Retirement scoring thresholds were tuned for 6-month data but we're pulling trailing year — scores cluster at 85 for low-activity items. Needs recalibration in Phase 2.
- Closed amount discrepancy between RCARS and main reporting dashboard (e.g. AWS with OpenShift: $45M vs $115M) — investigate in dedicated scoring session.
- RecCard format labels simplified to "Demo" and "Hands-on Lab" (external change during session, not reverted).
- The `deploy` Ansible tag is the only one that includes both `apply` (infra secrets) and `update` (builds + migrate). Use `deploy` for any changes that touch deployment config.

---

### 2026-06-15 — Nate + Claude (Code review remediation + RecCard cleanup)

**Done:**
- **Code review remediation (2 rounds, 21 findings):**
  - Migration 003: CHECK constraint for non-negative curated_duration_min
  - admin.py: orphaned job fix (try/except around enqueue_job), structured logging
  - catalog.py: N+1 query fix (list_workload_mappings outside loop), moved facets SQL to Database class
  - cli.py + ops.py: always call sync_workloads/sync_acl_groups even with empty lists (prevents stale data)
  - config.py: validation for similarity thresholds and workload_scan_interval_days
  - database.py: stage-scoped DELETE in compute_content_similarity (was deleting all stages), structured logging on set_curated_duration, new get_catalog_facets() method
  - vector_search.py: `is not None` instead of `or` for curated_duration_min=0 edge case
  - workload_scanner.py: operator precedence bug fix (and/or without parens in discover_roles), SHA race condition fix (local HEAD instead of remote post-scan), structured logging
  - ops.py: asyncio.to_thread() for scan_all_collections to unblock event loop
  - RecCard.tsx: keyboard accessibility (role, tabIndex, onKeyDown, aria-expanded)
  - ContentAnalysisPage.tsx: stale closure fix in loadData useCallback
  - lcars.css: defined --text-secondary CSS variable
  - test_db.py: dynamic table discovery in fixture
  - web-guide.md: client-side → server-side pagination
  - Skipped 4 findings with justification (.gitignore works correctly, compute_similarity is sub-second SQL, verified filter would reduce recall, BrowsePage useEffect deps not a real bug)
- **RecCard layout cleanup (3 iterations):**
  - Removed duplicate duration pill (was in header AND expanded body)
  - Format type (Hands-on Lab, Booth Demo) displayed as colored badge in header instead of gray text
  - "AI estimate" → "AI duration estimate" for clarity
  - Unified all expanded sections into consistent two-column rec-row layout (label 85px + value)
  - Learning objectives expanded by default, positioned right after "Why it fits"
  - Duration notes shown as dim continuation under "How to use" (same row), not a separate pill
  - Caveat moved to bottom with truncation at 200 chars + "more" toggle
  - Best-fit button shrunk: no uppercase, thinner border, smaller padding
  - Removed old pill/analysis CSS in favor of unified rec-row pattern

**In progress:**
- Nothing — clean handoff

**Next:**
- Execute retirement analysis implementation plan (10 tasks, starting from Task 1)
- Further RecCard refinements if needed after user testing
- Portfolio Architecture ingest from OSSPA GitLab

**Notes:**
- BrowsePage duration label convention is intentional: curated → "(estimated)", AI → "(AI estimate)". Documented in web-guide.md and consistent across RecCard and BrowsePage. Do not "fix" this.
- All changes deployed to dev via `--tags build-frontend` and `--tags update` as appropriate
- The RecCard now uses rec-row/rec-row-label/rec-row-value CSS classes instead of the old rec-analysis-row/rec-analysis-label/rec-analysis-value pattern

---

### 2026-06-15 — Nate + Claude (Retirement analysis — design + planning)

**Done:**
- **Standalone analysis tool** (`~/devel/working/catalog_2026/build_analysis.py`) — replaced 3 CSV imports with live queries from the RHDP reporting MCP server. Auto-pagination past the 500-row server cap, `--csv` fallback flag, 2026-01-01 start date. Verified end-to-end: 528 CIs from Babylon, 500 matched with live reporting data
- **MCP server investigation** — explored reporting DB schema (`provisions`, `catalog_items`, `provision_cost`, `provision_sales`, `sales_opportunity`). Discovered `catalog_items.name` in the reporting DB matches RCARS ci_name (strip stage suffix) — much more reliable join key than `display_name`
- **Design spec** — `docs/superpowers/specs/2026-06-15-retirement-analysis-integration-design.md`. Full brainstorm covering: data model (`reporting_metrics` table), nightly sync (step 5 in maintenance pipeline), join key (base name extraction), retirement scoring (ported from build_analysis.py), API endpoints (retirement dashboard, sync trigger, catalog detail extension, rec card enrichment), frontend (Content Analysis > Retirement page, rec card metrics line, Browse detail), CLI (`reporting-db sync/status/show`), config vars, Ansible deployment, data retention (rolling window, orphan cleanup), graceful degradation, no PII
- **Implementation plan** — `docs/superpowers/plans/2026-06-15-retirement-analysis-integration.md`. 10 tasks from Alembic migration through deployment verification, with concrete code in every step
- **BACKLOG.md** — added Phase 2 backlog items: retirement workflow actions (statuses + curator notes) and enhanced retirement scoring (percentile-based, category-aware)

**In progress:**
- Nothing — clean handoff. Implementation ready to start from Task 1

**Next:**
- Execute the 10-task implementation plan (Tasks 1-3 are independent, then sequential from 4 onward)
- Task 1: Alembic migration + config variables
- Task 2: Base name utility + retirement scoring + tests
- Task 3: MCP client with auto-pagination
- Then: DB methods → sync service → CLI → API → frontend → deploy

**Notes:**
- The reporting MCP server returns plain JSON (not SSE), so `urllib.request` works without SSE parsing
- MCP server caps at 500 rows per response — auto-pagination wraps SQL in CTE with LIMIT/OFFSET
- Cost query uses CTE pre-aggregation to avoid timeout on flat 3-way join (17s vs timeout)
- Sales queries use `DISTINCT` on `sales_opportunity.number` to prevent double-counting
- Retirement scoring thresholds were tuned for a 6-month window — will need recalibration with trailing-year data
- Rec cards degrade gracefully: if no reporting data exists, the metrics line simply doesn't render
- MCP token is stored as Ansible vault secret, never in code
- The Content Analysis nav section already exists (from overlap session) — retirement is a sibling route at `/analysis/retirement`

---

### 2026-06-15 — Nate + Claude (Content overlap detection — full implementation)

**Done:**
- **Content similarity schema** — new `content_similarity` table (Alembic migration 004), indexes on ci_name_a, ci_name_b, similarity_score
- **Pairwise cosine computation** — `compute_content_similarity()` in database.py. Compares all ci_summary embeddings within a selected stage using pgvector's `<=>` operator. Stores pairs above configurable threshold (default 0.75)
- **Stage-scoped comparison** — stage selector (prod/event/dev) on API, CLI, and UI. Only compares items within the same stage — eliminates false positives from dev/prod variants of the same item. Published VCIs excluded (no content of their own)
- **Iterative dedup refinement** — went through several rounds of filtering false positives:
  - v1: compared all embeddings (3,500+ pairs, mostly noise from stage variants)
  - v2: filtered by content_hash and showroom URL (still caught ZT namespace aliases)
  - v3: dedup by content_hash before comparing (still missed same-URL different-hash from branch drift)
  - v4: two-pass dedup with URL grouping + content_hash bridging (over-engineered)
  - v5 (final): simplified to stage-scoped comparison — only compare prod vs prod, event vs event, dev vs dev. Clean, correct, and simple
- **API endpoints** — `GET /catalog/{ci_name}/similar`, `GET /admin/overlap`, `POST /admin/compute-similarity?stage=prod&threshold=0.75`
- **CLI command** — `rcars compute-similarity [--stage prod] [--threshold 0.75]` with Rich table output
- **Admin UI — Content Analysis section** — new top-level nav section (alongside Advisor, Browse, Admin) with expandable sub-items. Overlap page moved from Admin tab to `/analysis/overlap`. Stage dropdown + Compute button + filter dropdown + expandable pair list with side-by-side summaries. Clicking a lab name navigates to Browse
- **Browse integration** — expanded items show "Similar Content" panel when overlap data exists, with color-coded similarity scores and clickable lab names
- **Deploy ordering fix** — new `--tags update` Ansible tag that sequences build-frontend → build-api → migrate correctly. Fixes issue where `--tags migrate` before `--tags build-api` runs migrations on old pod code
- **Comprehensive documentation:**
  - Web guide: full Content Analysis section with plain-language explanation of embeddings, cosine similarity, stage selection, CLI/API access
  - Architecture: new Content Overlap Detection section covering cosine similarity math, SQL computation, stage scoping, similarity tiers, integration points, relationship to recommendation pipeline. Updated schema (15 tables), pages, API routes
  - Operations: stage-scoped comparison, CLI usage, configuration
  - CLI guide: `compute-similarity` with `--stage` option
  - CLAUDE.md: new table, 3 new endpoints (39 total), deploy ordering notes, dev deployment testing guideline
- **Config** — `RCARS_SIMILARITY_THRESHOLD` (0.75), `RCARS_SIMILARITY_HIGH_THRESHOLD` (0.85)
- **Frontend cleanup** — removed alert() popup on compute completion, stats refresh inline

**In progress:**
- Nothing — clean handoff

**Next:**
- Content overlap Phase 2 — cross-stage comparison (dev items vs prod items from different CIs) to flag promotion risks. Captured in BACKLOG.md
- Retirement analysis — separate Content Analysis sub-page at `/analysis/retirement` (in progress in separate session)
- Portfolio Architecture ingest from OSSPA GitLab

**Notes:**
- Prod-vs-prod is the actionable tier. ~100 prod base CIs produce ~5,000 pairwise comparisons in under a second
- The Content Analysis nav section is designed to hold multiple sub-pages: Overlap is first, Retirement Analysis is next
- `--tags update` is the correct way to deploy changes that span API code + schema. Never run `--tags migrate` before `--tags build-api` — migrations execute on the running pod and need the new code
- All changes deployed to dev environment via `--tags update` throughout the session

---

### 2026-06-15 — Nate + Claude (Rec card duration + best fit + concurrency)

**Done:**
- **Curated duration system** — full stack: Alembic migration (`curated_duration_min` on `showroom_analysis`), `PUT /catalog/{ci_name}/duration` curator endpoint, `duration_source` field threaded through Candidate model → vector search → pipeline → serialization → SSE → frontend
- **Duration labels on rec cards** — header shows `~120 min` (always visible), expanded pill shows `~120 min (AI estimate)` or `~120 min (estimated)` with source label
- **Browse page curator duration input** — inline number input in curator section, placeholder shows AI estimate
- **Browse page duration source label** — analysis summary shows "(AI estimate)" or "(estimated)"
- **Best Fit button redesign** — renamed to "★ This is the best fit", bold green outline, uppercase, visually prominent
- **Duration penalty guard** — only curated durations affect scoring, AI guesses never penalize
- **Acronym case fix** — `re.IGNORECASE` on `_ACRONYM_RE`, `rhoai` now expands like `RHOAI`
- **Card copy/paste fix** — click handler scoped to header only, expanded content is selectable
- **Concurrent query fix** — sync LLM calls (`search`, `triage`, `generate_rationale`) wrapped in `asyncio.to_thread()` so arq can run multiple recommendation jobs simultaneously
- **Nginx HTTP/1.1 upstream** — added `proxy_http_version 1.1` for concurrent SSE streams through nginx
- **Recommend worker replicas** — `recommend_worker_replicas` variable in Ansible vars (default 1, configurable per env)
- **Chat formatting** — prompt updated to separate picks with line breaks and drop "Response:" label; frontend `cleanAssessment()` strips it locally as fallback
- **No-results message** — improved to guide users toward adding more context
- Updated CLAUDE.md (new endpoint, schema, scaling notes)

**In progress:**
- Nothing — clean handoff

**Next:**
- Content overlap detection
- Portfolio Architecture ingest from OSSPA GitLab
- Consider removing caveats from rec cards (deferred this session)

**Notes:**
- `recommend_worker_replicas` defaults to 1 in common.yml. For production, set higher in prod.yml (each replica handles 3 concurrent queries)
- The "fraud detection with rhoai" (lowercase) no-results issue was NOT an acronym bug — the acronym expansion works, but the short query doesn't produce enough vector similarity to match. Follow-up turns work because they prepend the original query as context
- Design spec: `docs/superpowers/specs/2026-06-15-rec-card-duration-bestfit-design.md`
- Implementation plan: `docs/superpowers/plans/2026-06-15-rec-card-duration-bestfit.md`

---

### 2026-06-15 — Nate + Claude (Browse + Admin page redesign)

**Done:**
- **Browse page redesign** — Design spec + implementation:
  - Replaced flat filter bar with collapsible filter panel: Cloud Provider (single-select), Workloads (multi-select with AND semantics), AgnosticD Config (single-select)
  - Moved from client-side load-all (1000 items) to server-side filtering with new `list_catalog_items_filtered()` DB method and extended `GET /catalog` route
  - Added numbered pagination replacing prev/next buttons
  - Curator-only filter panel (amber) with Unanalyzed/Failures/Stale/Needs Review pills — hidden from regular users
  - URL state sync for shareable filtered views, 300ms debounced search
  - Removed v2 toggle (infrastructure filters implicitly scope), removed content-state dropdown from regular users
  - WorkloadMultiSelect component (click-outside/escape to close, checkbox list, sorted alphabetically)
  - Fixed workload dropdown clipping (overflow:visible on filter panel)
  - 9 new database tests for filtered queries (search, stage, cloud, config, workloads, content filters, pagination)
- **Admin Catalog page reorganization:**
  - Split monolithic Catalog Status table into 3 stat cards (Catalog, Analysis, Infrastructure) in responsive grid
  - Added tabbed navigation: Status | Sync & Analysis | Workloads
  - Added Workload Mapping Management section: mapped workloads table (with delete), unmapped workloads table (sorted by CI count, inline Map form)
  - Merged Workers page into Sync & Analysis tab as collapsible "Recent Jobs" section, removed Workers from sidebar
  - Fixed maintenance pipeline description to include workload scan step
  - Flexible-width layout scaling with browser window
- **Investigation:** v2 items without workloads (15 of 188) are base clusters, summit tenant CIs, and test infrastructure — confirmed Virtual/tenant CIs that reference parent CIs don't carry their own workload lists
- **Combined query (infra + vector) deferred** with rationale: content vector search already captures product mentions naturally; infrastructure hard-filtering in advisor would be redundant or harmful. PH express mode already served by `/catalog/search/infrastructure`
- Updated BACKLOG.md, design specs committed

**In progress:**
- Nothing — clean handoff

**Next:**
- Rec card template + duration labels + Best Fit button
- Content overlap detection
- Portfolio Architecture ingest from OSSPA GitLab

**Notes:**
- Admin sidebar now has 3 items: Catalog, Token Usage, Query History (Workers removed)
- Admin Catalog page has 3 tabs: Status (stat cards + scheduled maintenance), Sync & Analysis (catalog sync + content analysis + full re-analysis + recent jobs), Workloads (workload scan + mapping management)
- Browse page OS Image filter was intentionally excluded — not useful for users. Config dropdown renamed to "AgnosticD Config"
- Design specs: `docs/superpowers/specs/2026-06-15-browse-page-redesign-design.md`
- Implementation plan: `docs/superpowers/plans/2026-06-15-browse-page-redesign.md`

---

### 2026-06-12 — Nate + Claude (infrastructure-aware catalog metadata — full implementation)

**Done:**
- Design spec written and reviewed: `docs/superpowers/specs/2026-06-12-infrastructure-aware-catalog-metadata-design.md`
- **Session 1 — Data layer + extraction:**
  - Alembic migration 002: 8 new columns on `catalog_items`, 5 new tables (`catalog_item_workloads`, `workload_mapping`, `workload_aliases`, `catalog_item_acl_groups`, `workload_scan_state`)
  - Moved `alembic/` from repo root into `src/api/` so it ships in the container image
  - Fixed `alembic/env.py` to use SQLAlchemy engine with psycopg3 dialect
  - Updated Ansible `--tags migrate` to run `rcars init-db` + `alembic upgrade head`
  - V2 detection (`is_agnosticd_v2`), FQCN workload parsing, infra extraction for OCP + RHEL/VM items
  - 35 verified workload mappings + 25 product aliases in seed file
  - CLI: `rcars infra stats`, `rcars workload {sync,scan,unmapped,map,alias,list}`
  - Deployed to dev, refreshed catalog: 188 v2 items, 173 with workloads
- **Session 2 — API + faceted search + workload scanner:**
  - `search_by_infrastructure()` with AND workload semantics, alias resolution, os_image filter
  - 7 new catalog API endpoints (search, facets, mappings CRUD, infra-stats)
  - `POST /admin/scan-workloads` endpoint
  - Workload scanner (`services/workload_scanner.py`): clones agDv2 repos from GitHub, reads Ansible code (defaults/tasks/templates), Haiku analysis, SHA change detection
  - Integrated as Step 4 in nightly maintenance pipeline
  - Deployed to dev, tested: 22 OpenShift AI results, RHOAI alias resolves correctly, AND semantics works, RHEL os_image filtering works
  - Scanner tested: 69 roles across 6 repos, 46 mapped (all verified), 13 plumbing excluded
- **Session 3 — Frontend:**
  - Browse: [v2] badge on item headers, infrastructure detail panel (config, cloud, OCP/OS, workloads, ACL), v2 filter toggle
  - Admin: "Scan Workload Repos" button with job polling + log, infra stats in Catalog Status table
  - API client: 8 new methods, extended TypeScript interfaces
  - Deployed to dev
- **Documentation:**
  - New `docs/architecture/schema-reference.md` — column-level reference for all 14 tables
  - `system-design.md` — replaced inline table descriptions with summary + link, added Infrastructure Metadata Extraction section
  - Updated CLAUDE.md (14 tables, 35 endpoints, CLI groups, 4-step pipeline)
  - Updated cli-guide.md, operations.md, development.md, mkdocs.yml
  - Docs published to GitHub Pages

**In progress:**
- Nothing — clean handoff

**Next:**
- Browse filter dropdowns (config/cloud/OS/workload) from facets API
- Admin workload mapping management UI (mapping table, unmapped table, inline edit)
- Combined query support (infra filter in advisor) — lower priority
- Consider: rec card template + duration labels + Best Fit button (next backlog item)

**Notes:**
- All 6 public agDv2 repos are scanned: core_workloads(42), ai_workloads(5), cloud_vm_workloads(5), namespaced_workloads(11), cnv_workloads(1), showroom(5). `rhpds.*` repos are private and not scanned.
- Workload scan runs nightly as pipeline Step 4 with SHA change detection. First full scan was manual via `--force`.
- The dev DB was init-db --drop'd during this session (to apply schema changes before alembic was wired up). All analysis data was lost and needs a full rescan — the nightly pipeline will handle this automatically.
- `RCARS_WORKLOAD_SCAN_INTERVAL_DAYS` config exists but isn't used yet in the pipeline — the scan runs every nightly cycle. Low priority to add interval gating since change detection makes daily scans cheap.

---

### 2026-06-12 — Nate (return from vacation, planning session)

**Done:**
- Pulled latest (1 commit delta — only BACKLOG.md update from May 15)
- Confirmed no other contributors worked on RCARS during absence (all 390 commits since May 15 are Nate's)
- Dropped stale git stash (curator role fix already merged in commit 4430e6d)
- Reviewed full backlog and selected 5 items for current development cycle
- **Infra metadata investigation** — queried 1210 AgnosticVComponents from babylon-config via `babydev.kubeconfig`. Found all needed data already in CRDs: `infra_workloads`/`workloads` (496 CIs), `env_type` (~95%), `cloud_provider` (~85%), `ocp4_installer_version` (252), `__meta__.access_control` (516). Top workloads: cert_manager(295), authentication(268), gitops(195), pipelines(124), openshift_ai(61). No new data sources needed. CRD dump saved to `/tmp/all-components.json`. Design spec session started separately.
- **Scan duration investigation** — traced full pipeline from prompt → analyzer → DB → recommendation scoring. Confirmed zero ground truth: no duration metadata in CRDs, catalog params, or CatalogItem spec. `lab_duration` and `litellm_duration` fields are environment provisioning lifetimes, not lab completion times. Decision: hybrid approach — `curated_duration_min` column overrides LLM guess for scoring, labeled "AI estimate" vs "estimated" on cards.
- Generated self-contained handoff prompts for 3 implementation sessions: (1) infra metadata design spec, (2) rec card template + duration labels + Best Fit button, (3) content overlap detection
- Updated BACKLOG.md with new "Active Work" section, reorganized items (ACL folded into infra metadata, duration/formatting moved to active)
- Saved sprint context and investigation findings to memory

**In progress:**
- Infrastructure-aware catalog metadata design spec (running in separate session)

**Next:**
- Rec card template + duration labels + Best Fit button (implementation)
- Content overlap detection (implementation)
- Portfolio Architecture ingest from OSSPA GitLab (implementation, after above)

**Notes:**
- Config changes detected in other session: `workload_scan_enabled`/`workload_scan_interval_days` added to config.py, `alembic/` moved under `src/api/`, `--tags migrate` added to Ansible deploy
- Arcade/interactive demo ingest deferred — needs video access strategy before committing
- Key constraint for infra metadata: curated workload mapping required, don't guess operator names from role names. Faceted search for PH, not vector search.

---

### 2026-05-06 — Nate

**Done:**
- Removed ZT toggle from Advisor and Browse UI (ZT items now included by default based on stage)
- Bumped triage max_tokens to 8192
- Fixed triage truncation with partial JSON recovery
- Reorganized project documentation: CLAUDE.md rewrite, BACKLOG.md prioritized, docs restructured into folders
- Created this WORKLOG.md

**Next:**
- Run full re-analysis for keyword embeddings before Summit 2026 (2026-05-12) — use Admin "Rescan All", run overnight

---

### 2026-05-06 — Claude (documentation review session)

**Done:**
- Full documentation review: read all 26 backend Python files and 20 frontend TypeScript files, compared against every doc
- **docs/index.md** — fixed all broken links (were pointing to old flat paths like `guide-web.md`, now correct subdirectory paths like `user/web-guide.md`)
- **docs/overview.md** — fixed "three stages" → "four stages", fixed broken CLI guide link, added Admin pages mention
- **docs/architecture/system-design.md** — major rewrite:
    - Fixed jobs table schema (TEXT PK, progress_json JSONB, created_by — was UUID/INTEGER/triggered_by)
    - Added 3 missing tables: token_usage, advisor_sessions, api_keys (was 6 tables documented, now all 9)
    - Added 7 missing columns to catalog_items (content_path, scope, scan_status, scan_error_class, scan_error, scan_failed_at, showroom_url_override)
    - Fixed deployment tags table (was update/apply, now deploy/mgmt-rbac matching deploy.yml)
    - Replaced incomplete 10-endpoint API route list with complete 35-endpoint list with auth requirements
    - Fixed "three-tier extraction strategy" → "two-path extraction strategy" for Showroom URLs
    - Added worker timeout details (stale_check 3600s, nightly_pipeline 7200s)
    - Added content hash dedup and ref normalization documentation for vector search
    - Added duration-aware reranking documentation (soft/hard constraints)
    - Added scan error classification table (9 error classes)
    - Added git retry logic documentation
    - Added nav.adoc filtering documentation
    - Added 5 Mermaid diagrams: system architecture, recommendation pipeline, scan pipeline, auth flow, data model ER
- **docs/architecture/deployment.md** — added OAuth proxy and replica counts to architecture table, added Vertex AI vars to setup, added SA allowlist docs, added Mermaid deployment diagram
- **docs/user/web-guide.md** — major rewrite:
    - Fixed layout diagram (was showing "Curate" page that doesn't exist, now shows actual sidebar with session history)
    - Fixed currency indicators (was single badge, now two: CATALOG and ANALYSIS)
    - Replaced incorrect score colors (green/amber/red %) with actual tier system (green/yellow/white)
    - Rewrote recommendation cards section to match actual RecCard.tsx behavior
    - Fixed "rolling back" to "turn navigation" with numbered buttons
    - Fixed session history (up to 8 recent sessions, "+ New Session" in sidebar)
    - Rewrote curator mode (controls are on Browse page, not Advisor; added stage toggles)
    - Rewrote Browse page with actual filter options, expanded view details, curator controls
    - Fixed admin visibility (admins only, not curators)
    - Rewrote all four admin sub-pages with actual features from AdminPage.tsx
- **docs/admin/cli-guide.md** — 9 fixes:
    - Added missing `rcars tag` and `rcars set-content-path` commands
    - Added missing `--workers` option to `rcars serve`
    - Removed non-existent `--force` flag from `rcars scan`
    - Removed non-existent `--include-dev` flag from `rcars refresh`
    - Added `--failures` flag to `rcars status`
    - Fixed env var name `RCARS_KUBECONFIG` → `RCARS_KUBECONFIG_PATH`
    - Fixed `RCARS_CLONE_DIR` default from `/tmp` to `/tmp/rcars-clones`
    - Added 7 missing env vars (REDIS_URL, SA_ALLOWLIST_STR, PIPELINE_*, CATALOG_NAMESPACES, AGNOSTICV_COMPONENT_NAMESPACE)
    - Removed fake `rcars show` command, replaced with actual debugging workflow
- **docs/admin/token-usage.md** — added missing `event_parse` operation (was 3, now 4), fixed record count
- **docs/admin/operations.md** — added timeout details to worker table, added resource limits table, fixed monitoring section to match actual Admin UI pages
- **docs/admin/development.md** — fixed services table (was 1 worker, now 2 separate workers with queue names), added log paths and dev env vars, removed legacy `src/rcars/` reference, added OpenShift build commands
- **mkdocs.yml** — added Mermaid support via pymdownx.superfences custom_fences

**Notes:**
- The `usePrivateMode` hook exists in the frontend code but is not connected to any UI — scaffolding for a future privacy feature.

---

### 2026-05-06 — Claude (dead code cleanup + acronym fix)

**Done:**
- Added override-url input to Browse page curator controls (was API/CLI only, now has UI)
- Removed dead `catalog_items.scope` column from DDL, index, and upsert (never populated)
- Removed dead `getWorkerHealth()` from frontend api.ts (never called)
- Removed dead `rescanStale()` from frontend api.ts (redundant with `startScan`)
- Removed redundant `POST /analysis/rescan-stale` backend endpoint (scan already picks up stale items)
- Diagnosed AAP query returning zero results — the all-MiniLM-L6-v2 embedding model doesn't recognize product acronyms. "AAP" produces distance 0.66 vs "Ansible Automation Platform" at 0.28.
- Added acronym expansion to recommendation pipeline (`_expand_acronyms` in pipeline.py). Expands 15 Red Hat product acronyms inline before embedding: "AAP" → "AAP (Ansible Automation Platform)". Drops AAP query distance from 0.77 to 0.44.
- Briefly raised `vector_cutoff` from 0.55 to 0.65, then reverted — acronym expansion is the correct fix, not loosening the cutoff.
- Promoted to production and deployed both environments.

**Notes:**
- `scope` column still exists in the live database — removed from code only, not migrated. Harmless.
- Acronym list: AAP, ACM, RHACM, ACS, RHACS, RHOAI, OCP, ARO, ROSA, RHEL, RHDH, SNO, RHSSO, EDA, TAP. Add new acronyms to `_ACRONYMS` dict in `pipeline.py`.
- RHEL was the only acronym already recognized by the embedding model (distance 0.46 vs 0.37 expanded). Expansion still helps slightly.
