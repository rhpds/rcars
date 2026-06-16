# RCARS Backlog

Last updated: 2026-06-16

## Active Work (June 2026)

Items selected for current development cycle. Investigations complete, design/implementation in progress.

- [x] **Infrastructure-aware catalog metadata** — Fully deployed (2026-06-15). AgnosticD v2 items: infra extraction, curated workload mapping (46 verified), faceted search API, workload scanner in nightly pipeline. Browse page redesigned with collapsible filter panel (Cloud Provider, Workloads multi-select, AgnosticD Config), server-side filtering, numbered pagination, curator-only filter panel. Admin page reorganized with stat cards, tabbed layout (Status / Sync & Analysis / Workloads), workload mapping management UI, Workers page merged into Sync & Analysis tab.
- [x] **Rec card duration labels + Best Fit button** — Deployed (2026-06-15). Curated duration system (Alembic migration, curator endpoint, `duration_source` threaded through pipeline). Duration in card header + source-labeled pill. Best Fit button redesigned with bold green outline. Duration penalty only on curated values. Acronym case fix, card copy/paste fix, concurrent query fix (`asyncio.to_thread`), nginx HTTP/1.1 for SSE, `recommend_worker_replicas` configurable.
- [x] **Content overlap detection (Phase 1)** — Deployed (2026-06-15). Pairwise cosine similarity on ci_summary embeddings within a single stage (prod/event/dev selector). New `content_similarity` table, admin Overlap tab with expandable side-by-side comparison, Browse "similar content" section, CLI `rcars compute-similarity`, API endpoints. Stage-scoped comparison eliminates false positives from stage variants.
- [ ] **Retirement analysis (Phase 1)** — Nightly sync from RHDP reporting MCP server, `reporting_metrics` table, retirement scoring (0-100), retirement dashboard under Content Analysis (curator+), rec card enrichment (provisions, cost/provision, sales impact badge), Browse detail enrichment (nice-to-have). Spec: `docs/superpowers/specs/2026-06-15-retirement-analysis-integration-design.md`. Plan: `docs/superpowers/plans/2026-06-15-retirement-analysis-integration.md`. Join key: RCARS ci_name (strip stage suffix) → reporting DB `catalog_items.name`.
- [ ] **Content overlap detection (Phase 2)** — Cross-stage overlap analysis. Compare dev items against prod items from *different* catalog items to flag "this dev lab duplicates an existing prod lab — reconsider before promoting." Also compare event items against prod. Requires smarter dedup: same-item stage variants must be excluded while cross-item cross-stage pairs are surfaced. Consider a "promotion risk" flag in Browse for dev items that overlap significantly with existing prod content. May also want overlap scores integrated into the nightly pipeline as an automated check rather than manual compute.
- [ ] **Non-Showroom content: Portfolio Architectures** — Ingest published architectures from OSSPA (manifest: `gitlab.com/osspa/osspa-site` PAList.csv, content: `gitlab.com/osspa/portfolio-architecture-examples` AsciiDoc). New extraction pipeline, new `content_type` field. Arcade/interactive demos deferred (need video access strategy).

## Bugs

- [ ] **DB/worker sync divergence** — arq worker and API update PostgreSQL independently; if worker crashes mid-pipeline, `jobs.status` and `catalog_items.scan_status` can diverge. Needs reconciliation pass or transactional wrapping
- [ ] **Orphaned running jobs** — no mechanism to detect jobs stuck in "running" state from a crashed worker. Needs a timeout-based cleanup or heartbeat check

## UI / UX

- [ ] **Admin query history** — show user email, session duration
- [ ] **Browse "untagged" filter** — dropdown option exists but filter logic is missing (no switch case)
- [ ] **ZT content classification** — distinguish full workshops from micro-labs in browse and recommendations
- [ ] **Add mobile mode to UI**
- [ ] **Contextual sidebar navigation** — Redesign the app sidebar so it changes content based on the active section: Advisor shows session history, Browse shows filter controls, Admin shows sub-page links. Top-level nav moves to sidebar header or app header with a back button between sections. Eliminates the double-sidebar problem and gives each section full sidebar width for its own controls

## Recommendation Quality

- [ ] **Proper recommendation system evaluation** — current approach (pgvector + LLM triage + LLM rationale) works but doesn't scale well. Evaluate real recommendation frameworks vs hand-built approach as cost/ratings/feedback data grows
- [ ] **Structured constraint extraction** — current duration handling (soft penalty reranking) is a stopgap. Needs a general constraint extraction pre-processing step: parse query for structured constraints (duration, audience, format, event) and apply as hard filters or scoring overrides before triage. Event keywords (e.g. `summit-2026`) should be a hard boost, not just vector similarity. Consider curated keyword allowlist
- [ ] **Multi-turn conversation context** — true conversational refinement with memory (currently prepends original query text as workaround)
- [ ] **Multi-vector event search** — multiple queries per category for broad events
- [ ] **Feedback loop integration** — "Best fit" selections are stored but not yet used to improve scoring
- [ ] **Catalog description as context** — CRD descriptions contain metadata not in Showroom content. Descriptions are unreliable (often stale), so deprioritized vs keywords. Revisit if keyword-boosted search proves insufficient
- [ ] **Combined query (infra + vector in Advisor)** — Deferred. For queries like "fraud detection on OpenShift AI", the content vector search already captures product mentions naturally (via Showroom content + acronym expansion). Infrastructure hard-filtering in the Advisor pipeline would either be redundant (content already matches) or harmful (eliminating good content matches that happen to lack the workload metadata). The real use case is PH express mode ("what demos can run on this cluster?") which is already served by `GET /catalog/search/infrastructure`. Revisit only if PH needs infrastructure-aware results through the Advisor recommendation pipeline specifically, and consider a soft boost (triage score bump) rather than hard filter

## Retirement Analysis

- [ ] **Retirement analysis (Phase 2): Workflow actions** — Add curation actions to the retirement dashboard: mark items as "Under Review", "Approved for Retirement", "Owner Notified", "Retired". Curator notes per item explaining retention/retirement decisions ("keeping because X"). Reuse existing tag/flag/note primitives where possible, add dedicated retirement status field where needed. Builds on the read-only Phase 1 dashboard.
- [ ] **Enhanced retirement scoring + data validation + time window filter** — Replace fixed thresholds (provisions < 60, closed < $1M, etc.) with a more robust scoring model. Consider: weighted scoring with configurable thresholds, percentile-based scoring relative to catalog peers, category-aware thresholds (workshops vs demos vs open envs have different usage profiles), trend detection (declining usage over time vs stable low usage). Investigate discrepancy between RCARS closed amounts and the main reporting dashboard (e.g. AWS with OpenShift: RCARS shows $45M closed vs dashboard $115M) — may be date window, aggregation methodology, or query differences. Add a time window selector to the retirement dashboard (1 quarter / 2 quarters / 3 quarters / 1 year) that re-runs the retirement analysis against the selected window. The nightly sync already pulls a full year of data — the window filter would compute scores on the selected subset, letting curators see how an item looks over 3 months vs 12 months. This requires storing per-quarter breakdowns or re-querying the MCP server on demand.

## Architecture

- [ ] **Migrate to new babydev cluster** — Current Babylon readonly cluster (babydev) is being retired in ~2 weeks (by end of June 2026). RCARS uses it for catalog refresh (CRD queries via kubeconfig). Need to update kubeconfig paths in `ansible/vars/dev.yml` and `ansible/vars/prod.yml`, verify CRD access on the new cluster, and confirm the nightly pipeline works. Impacts: `babylon_kubeconfig_path` var, potentially `agnosticv_component_namespace` and `catalog_namespaces` if they differ on the new cluster.
- [ ] **Migrate from Vertex AI to RHDP MaaS** — currently uses Claude via Google Vertex AI directly. Transition to RHDP's managed Model-as-a-Service endpoint. Reduces credential management and aligns with RHDP infrastructure standards
- [ ] **Showroom live-read endpoint** — on-demand content retrieval for Publishing House "unpacking" workflow
- [ ] **Conversational advisor** — multi-turn refinement with memory (event URL parsing works, this is about deeper conversation context)

## Publishing House Integration

- [ ] **Prototyping workflow** — find closest match, read Showroom/automation, order and modify environment
- [ ] **Showroom unpacking service** — PH delegates content reading to RCARS
- [ ] **Express mode learning data** — store PH express mode run data (selected base CI + customization steps) for future runs. Must be separate from content analysis to avoid polluting search. Coordinate with PH backlog

---

## Completed

- [x] SSE streaming for admin log windows (catalog refresh, stale check)
- [x] Worker scan log parity — showroom URL, ref, content files, tokens logged
- [x] Scan dedup breakdown — "577 scannable → 400 unique, 177 propagated"
- [x] Auto-refresh on Workers page (jobs + health) and Catalog Status refresh button
- [x] Browse multi-expand — multiple items open simultaneously
- [x] Browse page depth — modules and learning objectives inline
- [x] ZT content toggle in Browse filter bar
- [x] Progressive rec cards during SSE streaming (vector search → triage → rationale)
- [x] Green tier promotion — candidates with full rationale promoted to green
- [x] Content gaps moved from rec panel to chat response
- [x] Markdown rendering in assistant chat messages
- [x] Query history — sessions stored from recommend worker, sidebar shows recent
- [x] Clickable session history with conversation reload
- [x] Follow-up queries prepend original query for vector search context
- [x] Tier labels: Best fit / Other options / Also reviewed
- [x] "Best fit" feedback button with tooltip
- [x] Learning objectives in expanded green cards
- [x] demo.redhat.com catalog links on rec cards
- [x] Admin page reorganized: Catalog, Content Analysis, Full Rescan
- [x] Rescan All with auto-resuming scan monitor
- [x] Compact admin tables, Workers page with duration/completed columns
- [x] Token usage compact query log format
- [x] Admin query history card layout with tier-colored scores
- [x] Nav.adoc-aware scanning — only scan pages referenced in active nav entries
- [x] Duration-aware scoring — soft penalty for duration mismatch, hard penalty for "hard limit" language
- [x] Rationale prompt uses display names, not CI paths
- [x] Scan-progress scoped to current batch (not counting old completed jobs)
- [x] Viewport scroll containment — overflow:hidden on html/body/#root, flex layout
- [x] Advisor scroll containment — flex panes with min-height:0 and overflow-y:auto
- [x] Nav.adoc subdirectory xrefs — handles nested module paths (e.g. `200-ops/lab_1.adoc`)
- [x] Dev/event/ZT toggles in Advisor — pill toggles with server-side ZT filtering
- [x] Clickable failure/stale counts on Admin page — deep link to Browse filtered view
- [x] Browse URL param filtering — `?filter=scan_failures` etc. from Admin links
- [x] Scan failure error details — expanded items show error class, message, timestamp
- [x] Analysis stale threshold — percentage-based (>10% incomplete), not any-failure
- [x] Content path API + UI — curator input to set custom content folder and trigger rescan
- [x] Analysis max_tokens bumped to 8192 for large showrooms
- [x] Stale item visibility — Browse filter + clickable Admin count
- [x] Recommendation dedup across stages — group by (showroom_url, showroom_ref), prefer prod > published > best distance
- [x] Admin progress logging — replaced SSE with DB-accumulated message array + polling; proxy chain was killing idle SSE connections
- [x] Catalog refresh progress — granular "Upserting... 100/968" progress during upsert phase
- [x] Stale check dedup — clone each unique (url, ref) once instead of per-CI; reduced 555 clones to 388
- [x] Stale check two-phase — `git ls-remote` first to skip unchanged repos, clone only repos with new commits
- [x] Stale check timeout — bumped from 10 minutes to 1 hour for large catalog runs
- [x] GitHub retry with backoff — 3 retries with exponential delay on rate limit/403 errors for ls-remote and clone
- [x] "Scan" → "Analyze" — consistent terminology across admin UI (buttons, log messages, filter labels)
- [x] Token Usage page — Triage/Rationale columns replacing confusing nested query list
- [x] Admin scrollbar hidden — CSS scrollbar-width:none on content area, log windows reduced to 200px
- [x] Unanalyzed filter — clickable count on admin page + Browse filter, excludes published Virtual CIs
- [x] New Session fix — works when already in a fresh session (custom event dispatch instead of URL navigation)
- [x] Vector search candidates — bumped from 10 to 15 for wider triage net
- [x] Admin query history — full query text visible in expanded view, multiple cards expandable simultaneously
- [x] Admin query history — stage badges (dev/event) on non-prod candidates
- [x] Recommendation dedup by content_hash — collapses dev/prod variants with identical Showroom content while preserving genuinely different branch content
- [x] Dev stage restricted to curators/admins — toggle hidden for regular users, API enforces server-side
- [x] Triage JSON parsing fix — array fallback extraction for LLM responses with preamble text; added error logging on parse failures
- [x] Event URL parsing in advisor — paste a URL, RCARS fetches the page, extracts event profile via Sonnet, generates search queries, runs them through the pipeline
- [x] Mixed text+URL queries — combine user text constraints with event context extracted from URL
- [x] Admin query history score fallback — show vector_similarity_pct when relevance_score is null (white-tier items)
- [x] ZT toggle removed — ZT items included by default based on stage, no separate toggle. ZT badge still shown on Browse items
- [x] Catalog keywords in embeddings — catalog keywords from CRD `spec.keywords` appended to embedding text during analysis
- [x] Stale detection via ls-remote — two-phase check replaces full-clone-every-repo approach
- [x] Old monolith code removed — `src/rcars/` and `tests/` (9,505 lines)
- [x] Scheduled catalog refresh + stale check — nightly maintenance pipeline via arq cron (refresh → stale → re-analyze at 04:00 UTC)
- [x] RCARS API for PH vetting — PH calls RCARS to check content overlap during intake
- [x] PH ServiceAccount in SA allowlist — `system:serviceaccount:publishing-house-dev:default` added to dev vars
- [x] Scan dedup by commit SHA — resolve refs via `git ls-remote` before scanning; batch per URL, pass SHA siblings as job args for propagation
- [x] Browse page redesign — collapsible filter panel (Cloud Provider, Workloads multi-select, AgnosticD Config), server-side filtering replacing client-side load-all, numbered pagination, curator-only filter panel (amber), URL state sync, debounced search
- [x] Admin page reorganization — stat cards (Catalog/Analysis/Infrastructure) replacing monolithic table, tabbed layout (Status / Sync & Analysis / Workloads), workload mapping management UI (mapped + unmapped tables, inline map form), Workers page merged into Sync & Analysis tab
- [x] Browse filter dropdowns — Cloud Provider, Workloads (multi-select with AND semantics + alias resolution), AgnosticD Config populated from `/catalog/facets` API
- [x] Admin workload mapping management UI — mapped workloads table with delete, unmapped workloads table sorted by CI count with inline Map form
