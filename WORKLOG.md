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
