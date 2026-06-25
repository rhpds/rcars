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

### 2026-06-24 — Nate + Claude (Security hardening release + production deploy)

**Done:**
- Security audit remediation — all HIGH and most MEDIUM findings fixed (PRs #30, #50, #51, #52, #53, #54)
- Triaged and merged 8 external PRs, closed 2 issues (#26, #2)
- Operational hardening: SSE timeout, liveness probes, orphaned job sweep (#52)
- Best Fit button fix + orphaned job cleanup
- Deployed to production via PR #55, smoke test passing

**In progress:**
- Nothing — clean handoff

**Next:**
- Close remaining open PRs (#48, #46, #33, #32)
- Retirement Phase 2: workflow actions
- Portfolio Architecture ingest

---

### 2026-06-23 — Nate + Claude (Babydev migration, format_suitability deploy, PR triage)

**Done:**
- **Babydev cluster migration (dev):**
  - Generated long-lived SA token, updated kubeconfig and Ansible vars
  - Rolled out to dev, verified catalog refresh: 1,080 items across 3 namespaces, 58 retired (post-Summit cleanup)
  - Pods required manual `oc rollout restart` — the `--tags apply` updated the K8s secret but the checksum annotation didn't change (investigate Ansible template logic)
  - Prod is not affected — prod uses a separate Babylon cluster
- **Format suitability rename deployed to dev:**
  - Pushed commit 8e2d99d to main
  - Ran `--tags update` — frontend + API builds + migration 009 applied
  - Verified: `event_fit_json` column renamed to `format_suitability_json`, alembic at version 009
- **External PR triage (10 draft PRs from bbethell-1, all June 22):**
  - Reviewed all 10 PRs. 3 were previously merged and reverted (#31, #41, #42)
  - Recommended close: #48 (metadata embeddings), #32 (CI pipeline), #46 (light mode) — new features not aligned with priorities
  - Recommended merge: #30 (auth scoping — IDOR fixes), #29 (schema fix), #39 (no-match message), #40 (prompt guardrails)
  - Needs conflict resolution: #33/#34/#35 overlap on database.py and frontend files
  - Detailed review of #30: session access scoped by user_email, tag deletion scoped by ci_name, auth returns None instead of "", catch-all route redirect
- **Backlog updated:** babydev migration marked complete

**In progress:**
- Security audit running in separate session (clean context, no PR bias)

**Next:**
- Review security audit results against external PRs
- Merge #30 (auth scoping) after security audit confirms findings
- Deploy format_suitability to prod via PR main → production
- Close PRs #48, #32, #46 with comments explaining reasoning

**Notes:**
- Checksum annotation on deployments didn't trigger rollout when the K8s secret changed — may need to hash the secret content in the annotation rather than using a static checksum
- The 10 external PRs are all from the same contributor (Billy Bethell) and were all opened on the same day — appears to be a batch contribution after the repo went public
- Prod kubeconfig does NOT need updating for babydev — that's a dev-only cluster

---

### 2026-06-23 — Nate + Claude (Remove legacy "event" terminology from analysis fields)

**Done:**
- **Root cause fix for "brand events" hallucination in recommendation caveats:**
  - The `event_fit_json` field (from the original "Event Content Advisor" branding) was passed to the rationale LLM labeled as "Event Fit". The LLM saw "event" and hallucinated "designed for brand events" in caveats.
  - Renamed `event_fit` → `format_suitability` across the full stack:
    - Analysis prompt (`analyze_showroom.txt`): JSON key `event_fit` → `format_suitability`
    - Rationale prompt (`rationale.txt`): added explicit guidance "RHDP content types are demo and hands-on lab only — do not invent other categories"
    - Rationale builder (`rationale.py`): context label `Event Fit` → `Format Suitability`
    - DB schema (`database.py`): column reference `event_fit_json` → `format_suitability_json`
    - Scan worker (`scan.py`): analysis dict key updated
    - CLI (`cli.py`): analysis dict key updated (2 locations)
    - Alembic migration 009: `ALTER TABLE showroom_analysis RENAME COLUMN event_fit_json TO format_suitability_json`
- Committed to main (8e2d99d), push pending (network/VPN was down)

**In progress:**
- Push to main + deploy to dev with `--tags update` (Nate handling manually)

**Next:**
- After deploy, run an advisor query to verify caveats no longer mention "brand events"
- Existing analysis data carries over (column rename only) — no rescan needed
- Consider further cleanup of `event_parser.py` / `match_event.txt` naming if the URL parsing feature warrants generalization

**Notes:**
- The `event_parser.py` module and `match_event.txt` prompt were NOT renamed — they handle genuine event URL parsing (paste a conference URL to get recommendations) and are still accurate for that feature
- Babylon catalog stages (prod/event/dev) are infrastructure terms and were intentionally left unchanged
- Pre-existing test failure: `test_use_vertex` fails due to `ANTHROPIC_VERTEX_PROJECT_ID` env var in shell — unrelated

---

### 2026-06-22 — Nate + Claude (LLM fallback, scoring, deploy reliability, overlap fix)

**Done:**
- **LLM fallback**: `call_llm()` now wraps LiteMaaS in try/except and falls back to Vertex/Anthropic on any error. Previously a LiteMaaS 401 crashed the entire request with no fallback.
- **Score capping**: `_apply_usage_boost()` and `_apply_duration_penalty()` now clamp scores to 0–100. Frontend `RecCard.tsx` also clamps. Fixes 104% display bug on recommendation cards.
- **Deploy reliability**: Added `checksum/secrets` annotation to API, scan-worker, and recommend-worker pod templates. Secret value changes (e.g. API key rotation) now trigger automatic rollouts on `--tags apply` — no more stale credentials.
- **Advisor smoke test**: New `tasks/smoke-test.yml` runs end-to-end advisor query after deploy/apply. Verifies LLM connectivity. Runs on `--tags deploy`, `--tags apply`, `--tags smoke-test`.
- **Content overlap stage filter**: `get_overlap_report()` and `get_similarity_stats()` now accept a `stage` parameter. Frontend passes selected stage and reloads on stage change. Fixes bug where switching between prod/event/dev showed stale pairs from other stages.
- **LiteMaaS key rotation**: Updated API key in dev and prod vars, rolled out to both environments. Discovered pods weren't restarting because `secretKeyRef` env vars are only read at pod startup — the checksum annotation fix prevents this going forward.
- **PR #19 merged to production**: All fixes deployed to prod with smoke test passing (23 candidates).

**In progress:**
- Nothing — all items shipped

**Next:**
- Monitor prod for any LiteMaaS issues with the new key
- Overlap fix needs PR to production when ready

---

### 2026-06-22 — Nate + Claude (Documentation overhaul — web guide + admin docs)

**Done:**
- **Web UI Guide (`docs/user/web-guide.md`) — full review and update:**
  - Added missing **Retirement Analysis** section: time window selector, Prod Retirements tab (stat cards, filter pills, sortable columns, expanded rows), Without Prod tab (age filters, table, expanded rows), scoring overview table
  - Added **Sidebar Navigation** subsection documenting Content Analysis sub-nav (Overlap + Retirement)
  - Fixed Content Analysis section: filter pills → dropdown selectors (matches actual UI), added search-by-name input
  - Restructured Browse page into subsections: Primary Bar, Filters Panel (Cloud Provider, Workloads, AgnosticD Config), Curator Filters, Item Badges, Expanded Item View
  - Added missing v2 badge for AgnosticD v2 items
  - Added infrastructure details in expanded view (config, cloud, OCP version, workloads)
  - Added scan error display in expanded view
  - Fixed Admin section: Status tab now describes all 5 stat cards (Catalog, Analysis, Infrastructure, LLM Provider, Reporting Sync) plus Refresh button
  - Added Sync & Analysis tab Recent Jobs section
  - Added Workloads tab description (Workload Repos scan + Workload Mappings)
  - Removed Workers page reference (redirects to Catalog — effectively deprecated)

- **Deployment Guide (`docs/admin/deployment.md`) — restructured:**
  - Replaced full architecture section (mermaid diagram, component walk-through) with brief component table + link to system-design.md
  - Removed all `~/devel/secrets/rcars-mgmt-*.kubeconfig` local path references
  - Changed CLI commands to use plain `oc exec` with note about cluster access requirements
  - Absorbed Operational Workflows from CLI guide: initial setup, fresh start, incremental sync, debugging failed items, force rescan, testing recommendations
  - Added `reporting-db sync` to initial setup and fresh start workflows

- **CLI Admin Guide (`docs/admin/cli-guide.md`) — restructured:**
  - Removed local kubeconfig path references and "Local development" access option
  - Moved environment variables to the bottom, organized into grouped tables (Required, LLM Provider, Models, Tuning, Access Control, Infrastructure, Nightly Pipeline, Reporting)
  - Removed Operational Workflows section (moved to deployment guide)
  - Added undocumented `--verbose` global option
  - All 25 CLI commands verified against `src/api/rcars/cli.py` — all match

- **Operations Guide (`docs/admin/operations.md`):**
  - Removed Content Overlap Detection section (already covered in `docs/architecture/content-overlap.md` and web guide)
  - Removed "Running Workers Locally" section

- **Development Guide (`docs/admin/development.md`):**
  - Deleted entirely — no local development workflow needed
  - Removed from `mkdocs.yml` nav and `docs/index.md`

**In progress:**
- Nothing — clean handoff

**Next:**
- Monitor GPTEINFRA-16949 for reporting DB name garbling fix (3 items)
- Retirement Phase 2: workflow actions (Under Review / Approved / Retired statuses)
- Babydev cluster migration (deadline: end of June 2026)

---

### 2026-06-19 — Nate + Claude (Retirement analysis data validation + published/base merge)

**Done:**
- **Retirement data validation against Superset:**
  - Compared RCARS prod `reporting_metrics` against Superset's actual dashboard queries (provisions + sales + cost)
  - Verified the Superset dashboard queries are correct — they properly deduplicate with `DISTINCT ON (so.number, ps.asset_name)`
  - Confirmed provision counts match: 314/354 exact, remaining deltas explained by grouping key differences and name issues
  - Confirmed touched/closed amounts match live when run against the same data (1:1 ratio), stored RCARS values lag by up to ~24h from nightly sync
  - Confirmed cost methodology difference is by design: RCARS includes all environments (dev/event/prod), Superset PROD-only. RCARS is ~14% higher overall. Documented in CLAUDE.md.
  - Investigated extreme ROIs (1M+ T-ROI) — confirmed they're driven by single large opportunities linked to low-cost workshops, not data errors. The attribution model gives full credit to every CI that touches an opportunity.
- **Identified reporting DB name garbling bug (3 items):**
  - `.dev` stripped from middle of `catalog_items.name` when item name starts with `dev` after a dot boundary
  - Affected: `sandboxes-gpte.devsecops-ctf-on-openshift`, `sandboxes-gpte.developer-hub-workshop`, `rhdp.dev-sandbox`
  - Filed GPTEINFRA-16949 with diagnostic queries, updated with third item found during session
- **Published/base CI merge in reporting sync:**
  - 30 published/base pairs were appearing as separate entries with split metrics
  - Base CIs scored 65-80 (high retirement) even though they're actively needed
  - Added `get_published_base_mapping()` DB method using existing `published_ci_name` field
  - Added `_merge_published_base_pairs()` post-merge step: sums provisions/touched/closed/cost, merges quarterly data, removes base CI entry
  - Base CIs excluded from catalog backfill to prevent re-adding with zeros
  - Used `DISTINCT ON (base_base_name)` for deterministic mapping when multiple stages exist
  - Verified on dev (30 pairs merged), deployed to prod via PR #18
- **Prod deployment fix:**
  - Build config still referenced deleted `rcars-github-source` secret — cleared via `--tags apply`
  - Cancelled stuck pending builds from prior session
- **Documentation:**
  - CLAUDE.md: added `rcars reporting-db` subgroup to CLI section
  - GPTEINFRA-16949: full bug report with 3 affected items and diagnostic SQL

**In progress:**
- Nothing — clean handoff

**Next:**
- Monitor GPTEINFRA-16949 for reporting DB fix (3 items with garbled names)
- Retirement Phase 2: workflow actions (Under Review / Approved / Retired statuses)
- Babydev cluster migration (deadline: end of June 2026)

**Blockers:**
- 3 catalog items show 0 provisions in RCARS due to name garbling in reporting DB — waiting on GPTEINFRA-16949

**Notes:**
- The custom Superset CSV query the user provided had a dedup bug (missing DISTINCT ON for sales) — the actual Superset dashboard queries are correct
- 144 Superset items didn't match RCARS by display name — mostly expected: retired items purged before soft-delete, name evolution over time, summit-prefixed variants
- Cost ROI can appear extreme when low-cost workshops (e.g., $772 for Ansible on AWS) touch large opportunities — this is attribution model behavior, not a data bug
- Prod API kubeconfig for management: `<path-redacted>/rcars-mgmt-prod.kubeconfig`
- Dev API kubeconfig for management: `<path-redacted>/rcars-mgmt-dev.kubeconfig`
- Prod build config was updated to remove `sourceSecret` reference — builds now pull from public repo without credentials

---

### 2026-06-18 — Nate + Claude (Soft-delete catalog items)

**Done:**
- **Soft-delete implementation — full stack:**
  - Alembic migration 008: `retired_at TIMESTAMPTZ` + `retirement_reason TEXT` on `catalog_items`, partial index on `retired_at IS NOT NULL`
  - `delete_removed_items()` → `retire_removed_items()`: items missing from CRD scan get `retired_at = NOW()` instead of CASCADE delete
  - Auto un-retire: items that reappear in a future scan get `retired_at` cleared both via upsert (immediate) and retire pass (logged)
  - `retired_at IS NULL` filter added to 20+ query methods: `list_catalog_items`, `list_catalog_items_filtered`, `get_items_needing_analysis`, `get_scan_dedup_stats`, `get_siblings_by_showroom`, `get_scan_failures`, `get_status_summary`, `get_db_currency`, `search_embeddings`, `get_infra_stats`, `get_catalog_facets`, `search_by_infrastructure`, `compute_content_similarity`, `get_catalog_base_names`, `get_stages_for_base_names`, `has_prod_stage`, `get_all_base_names_with_prod`, `list_reporting_metrics` (has_prod subqueries + LATERAL join)
  - Browse API: `include_retired` query parameter, passed through to filtered query
  - Browse page: curator-only "Show Retired" toggle in curator filter panel, `retired_at` in CatalogItem interface, amber "RETIRED" badge with date, 60% opacity on retired rows
  - Admin page: updated pipeline result type from `removed_items` to `retired_items`, updated refresh description
  - CLI: `refresh` command uses `retire_removed_items()`, messages say "retired" not "removed"
  - CLAUDE.md: documented soft-delete pattern, updated migration count
  - BACKLOG.md: marked soft-delete complete

- **Retirement analysis exclusion fix:**
  - Retired items from the reporting MCP were being imported, scored, and could appear in the dashboard's Without Prod tab
  - `get_fully_retired_base_names()` — new DB method returns base names where ALL stage variants are soft-deleted
  - `run_reporting_sync()` now excludes fully-retired base names from `merged_rows` before percentile scoring, preventing retired items from diluting active item rankings
  - `list_reporting_metrics()` now requires at least one active `catalog_items` entry (`retired_at IS NULL`) to appear in the dashboard
  - Partial retirement handled correctly: if only `.prod` is retired but `.dev` is active, the item still scores and appears in Without Prod tab
- **Documentation updates:**
  - overview.md: new "Catalog Preservation" section
  - retirement-analysis.md: full "Soft-Delete" section covering mechanics, query filtering, Browse integration, and reporting data interaction
  - system-design.md: database section note on soft-delete pattern
  - schema-reference.md: retired_at and retirement_reason column docs
  - operations.md: catalog refresh step mentions soft-delete

**In progress:**
- Dev deployment running (`--tags update`)

**Next:**
- Verify dev deployment: run catalog refresh, confirm retired items appear with curator toggle
- Test un-retire: manually retire an item via SQL, run refresh, confirm it comes back
- Retirement Phase 2: workflow actions (Under Review / Approved / Retired statuses)
- Babydev cluster migration (deadline: end of June 2026)

**Notes:**
- Fully-retired items (all stages soft-deleted) are excluded from the reporting sync and orphan cleanup removes their `reporting_metrics` rows. Reporting data is re-derivable from the MCP; analysis and embeddings are unique data that IS preserved.
- `get_catalog_item()` (single item lookup) intentionally does NOT filter retired items — you can still view a retired item's detail page
- The upsert path clears `retired_at` and `retirement_reason` on every upsert, ensuring any item present in the CRD scan is automatically active
- DB test fixture has a pre-existing error (dict access on tuple rows) — not related to this change
- `test_use_vertex` fails due to env var `ANTHROPIC_VERTEX_PROJECT_ID` from shell — pre-existing

---

### 2026-06-17 — Nate + Claude (Retirement scoring + time window + catalog completeness)

**Done:**
- **Stale scoring cleanup:**
  - `delete_orphan_reporting_metrics` now removes items not in the current sync batch AND items no longer in `catalog_items`
  - 163 stale items from old scoring (85, 100) cleaned up — scores now 0-65 max
- **Time window filter for retirement dashboard:**
  - Migration 007: `quarterly_data JSONB` column on `reporting_metrics`
  - 4 new quarterly SQL queries grouped by `TO_CHAR(DATE_TRUNC('quarter', date), 'YYYY-"Q"Q')`
  - `compute_windowed_scores()` recomputes percentile rankings from stored quarterly data — no MCP re-query
  - API: `window` query parameter (1q/2q/3q/1y); frontend: pill selector on Prod tab
  - Cost quarterly query uses provision quarter (provisioned_at) not billing quarter (month_ts). 300s timeout.
  - Fixed `compute_retirement_score` to handle `datetime.date` objects from psycopg3
- **More aggressive scoring:**
  - Added `provisions_zero` flag (+25), matching touched_zero/closed_zero pattern
  - Provision percentiles computed among non-zero peers only (was diluted by all items)
  - Bumped provision weights: < 25th pct +14, < 10th +18
  - Reduced age discount from -40/-15 to -30/-10
  - Lowered thresholds: high ≥55, review ≥35 (was 75/50)
- **Full catalog coverage in retirement dashboard:**
  - `get_catalog_base_names()` pulls all 528 unique base names from `catalog_items`
  - Sync backfills zero-data entries for catalog items with no reporting data (176 items)
  - Items without Showroom get `has_content=false` and gray "catalog" badge linking to demo.redhat.com
  - `get_stages_for_base_names()` now includes `has_showroom` flag
  - All windows: Prod (353) + Without Prod (175) = 528 unique catalog items
- **Removed activity filter** — all 353 prod items always shown regardless of window; items with zero recent activity are retirement candidates, not items to hide
- **Investigated cross-namespace duplication** — items like `zt-ansiblebu.zt-ans-bu-writing-playbook` and `zt-rhel.zt-ans-bu-writing-playbook` share sales opportunities, inflating per-item touched/closed amounts. Conservative error (makes items look like keepers). Added as low-priority backlog item.
- **Isolation verified** — changes confined to retirement endpoint, reporting_sync, and database methods only used by retirement code. Scan pipeline, recommendation pipeline, overlap detection, and admin functions untouched.

**In progress:**
- Nothing — clean handoff

**Next:**
- Visual verification of the retirement dashboard via browser (OAuth login required)
- Retirement Phase 2: workflow actions (mark as Under Review / Approved / Retired)
- Documentation update for retirement analysis architecture page
- Babydev cluster migration (deadline: end of June 2026)

**Notes:**
- The kubeconfig for dev management is at `<path-redacted>/rcars-mgmt-dev.kubeconfig`
- Max achievable score is ~80 (provisions_zero 25 + touched_zero 15 + closed_zero 25 + high cost no closed 15). Age discount subtracts up to 30 for items < 90 days old.
- Quarterly data stored as JSONB: `{"2026-Q2": {"provisions": 27, "touched": 150000, "closed": 80000, "cost": 5000}}`. Sync adds ~60s for quarterly queries.
- `delete_orphan_reporting_metrics` takes `synced_names` set — removes items not in the current sync AND items without catalog entries.
- The Ansible deploy playbook intermittently fails cluster connectivity checks (404 from k8s API). Workaround: use `oc start-build` directly with the management SA kubeconfig.

---

### 2026-06-17 — Nate + Claude (Retirement Phase 2 — data validation + scoring + docs)

**Done:**
- **Data validation investigation and fix (3 root causes found and fixed):**
  1. Sales SQL was filtering by `p.provisioned_at` (provision date) instead of `so.closed_at` (opportunity close date). Split `_build_sales_sql()` into `_build_touched_sql()` (provision-date filtered) and `_build_closed_sql()` (closed_at filtered). Fixed sandbox-ocp from $45M → $104M closed.
  2. All queries filtered to `environment='PROD'` and `user_group IN ('Only Regular Users', 'Red Hat Console')` to match SuperSet dashboard scope. Removed 42% of inflated provisions from DEV/TEST/EVENT and internal users.
  3. Switched all queries from raw `provisions` table to `provisions_summary` materialized view (the same source SuperSet uses), and from `provision_sales` intermediary join to direct `provisions_summary.sales_opportunity_id → sales_opportunity.id` FK. Fixed RHADS from $1.1B → $213M touched.
- **Percentile-based retirement scoring:**
  - Replaced fixed-threshold scoring with percentile ranking against catalog peers
  - Removed `has_prod` from scoring — dev-only items handled in separate tab
  - Excluded test/infra items (`tests.*`, `clusterplatform.*`, `resourcehub.*`) from sync
  - Two-pass scoring in `run_reporting_sync()`: collect data → compute percentiles → score
  - Max score 75 (headroom for future dimensions), age discount unchanged
- **Retirement dashboard redesign:**
  - Split into Prod Retirements (scored) and Without Prod (age-based) tabs
  - Stat cards compute from filtered items (not global summary)
  - Without Prod: expandable rows with detail, clickable stage badges linking to Browse, age filter pills (All / >1 Year / 6-12 Mo / < 6 Mo)
- **Admin status cards redesigned:**
  - LLM Provider: models under both LiteMaaS and Vertex AI, Analysis/Triage/Rationale rows
  - Reporting Sync: "Assets tracked" with color-coded score breakdown replacing opaque counts
- **API memory bumped** from 512Mi/2Gi to 1Gi/4Gi to prevent OOM during sync
- **Documentation overhaul:**
  - Split monolithic `system-design.md` (684 lines) into 5 focused pages: system design, scan pipeline, recommendation engine, content overlap, retirement analysis
  - Rewrote overview.md to reflect current RCARS capabilities
  - Fixed inaccuracies: namespace sync (all 3, not prod-only), ZTE naming, workload extraction vs scanning, catalog reader extraction list, vector embeddings explanation
  - Scan pipeline: added intro, nav.adoc in diagram, rewrote Step 4 with actual prompt fields + example output, rewrote Step 6 embeddings with clear explanation, moved dedup after Step 7, added change detection section
  - Recommendation engine: vertical diagram with subgroups, expanded Phase 1 vector search explanation, triage prompt/response examples, clarified triage (compact 8-field) vs rationale (full analysis) data, acronym table
  - Retirement analysis: explained 75-point max, added three worked scoring examples
  - Added config/CLI/API reference sections to all architecture pages
- **Backlog additions:** robust acronym expansion, lower overlap threshold for broader detection
- All changes deployed to dev, sync verified

**In progress:**
- Nothing — clean handoff

**Next:**
- Time window filter for retirement dashboard (1Q / 2Q / 3Q / 1Y selector). Design decision needed: store per-quarter breakdowns during sync vs re-query MCP on demand. The nightly sync already pulls trailing year; the filter would recompute scores on the selected subset.
- Re-sync on dev and verify percentile score distribution looks right (new scoring deployed but hasn't been synced yet with latest frontend fixes)
- Documentation review continuation (CLI/API reference sections added but content review paused mid-stream)
- Babydev cluster migration (deadline: end of June 2026)

**Notes:**
- `provisions_summary` is a PostgreSQL materialized view (not in `information_schema`, found via `pg_matviews`). It has ~15K fewer rows than `provisions` and different opportunity linkage — must be used for dashboard-matching numbers.
- The `PROVISION_FILTERS` constant in `reporting_sync.py` applies environment + user_group filters to all queries.
- `EXCLUDE_PREFIXES` in `reporting_sync.py` filters out test/infra items before scoring.
- Reporting MCP env vars were manually injected on dev via `oc set env` because `--tags apply` failed transiently. Next `--tags deploy` will set them up canonically via the template.
- The frontend TS build is strict — unused variables cause build failures. The `summary` state removal caught this.

---

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
