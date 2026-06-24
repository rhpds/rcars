# RCARS Backlog

Last updated: 2026-06-23

## Active Work (June 2026)

- [x] **Soft-delete catalog items (preserve retired content)** — deployed 2026-06-18
- [ ] **Retirement analysis (Phase 2): Workflow actions** — Add curation actions to the retirement dashboard: mark items as "Under Review", "Approved for Retirement", "Owner Notified", "Retired". Curator notes per item explaining retention/retirement decisions ("keeping because X"). Reuse existing tag/flag/note primitives where possible, add dedicated retirement status field where needed. Builds on the read-only Phase 1 dashboard. Pairs with soft-delete — retirement status persists after the item leaves Babylon.
- [x] **Migrate to new babydev cluster** — deployed to dev 2026-06-23. Catalog refresh verified (1,080 items). Prod uses separate cluster, not affected.
- [ ] **Non-Showroom content: Portfolio Architectures** — Ingest published architectures from OSSPA (manifest: `gitlab.com/osspa/osspa-site` PAList.csv, content: `gitlab.com/osspa/portfolio-architecture-examples` AsciiDoc). New extraction pipeline, new `content_type` field. Arcade/interactive demos deferred (need video access strategy).

## Bugs

- [ ] **DB/worker sync divergence** — arq worker and API update PostgreSQL independently; if worker crashes mid-pipeline, `jobs.status` and `catalog_items.scan_status` can diverge. Needs reconciliation pass or transactional wrapping
- [ ] **Orphaned running jobs** — no mechanism to detect jobs stuck in "running" state from a crashed worker. Needs a timeout-based cleanup or heartbeat check
- [ ] **CLI `reporting-db status` uses old thresholds** — The CLI command hardcodes High ≥75 / Review 50-74 but the frontend uses ≥55 / 35-54. Minor inconsistency; should read thresholds from config or match the frontend.

## Content Analysis

- [ ] **Content overlap detection (Phase 2)** — Cross-stage overlap analysis. Compare dev items against prod items from *different* catalog items to flag "this dev lab duplicates an existing prod lab — reconsider before promoting." Also compare event items against prod. Requires smarter dedup: same-item stage variants must be excluded while cross-item cross-stage pairs are surfaced. Consider a "promotion risk" flag in Browse for dev items that overlap significantly with existing prod content. May also want overlap scores integrated into the nightly pipeline as an automated check rather than manual compute.
- [ ] **Lower overlap threshold for broader detection** — The current 75% minimum threshold only catches near-duplicates and closely related content. Labs with 50-74% overlap may still share significant material worth reviewing. Consider adding a third tier (e.g., "Moderate overlap" at 50-74%) or making the threshold configurable in the UI. Store more pairs but default the view to the existing 75%+ to avoid noise.

## Retirement Analysis

- [ ] **Merge published/base CI pairs in reporting sync** — Published CIs (e.g. `published.ocp4-adv-app-platform-demo`) and their base CIs (`openshift-cnv.ocp4-adv-app-platform-demo-cnv`) are separate entries in the reporting DB with different `catalog_items.name` values. The retirement dashboard shows them as two items with split metrics — the published variant gets all the provisions/sales and the base gets almost none. 30 active pairs affected. Fix: during reporting sync, detect published/base relationships via `catalog_items.published_ci_name`, sum their reporting metrics under the published base name, and skip the base CI entry. The recommendation pipeline already deduplicates these (promotes base to published); the retirement dashboard should too.
- [ ] **Cross-namespace opportunity deduplication (low priority)** — Items that exist under multiple namespace prefixes (e.g. `zt-ansiblebu.zt-ans-bu-writing-playbook` and `zt-rhel.zt-ans-bu-writing-playbook`) share the same sales opportunities but each shows the full amount. Touched/closed figures are inflated per-item because the SQL deduplicates within each base name but not across base names sharing the same content. Conservative error (makes items look like stronger keepers), and most duplicates will be cleaned up through normal retirement. Revisit if it becomes a pattern after initial retirement pass.

## UI / UX

- [ ] **Admin query history** — show user email, session duration
- [ ] **Browse "untagged" filter** — dropdown option exists but filter logic is missing (no switch case)
- [ ] **ZT content classification** — distinguish full workshops from micro-labs in browse and recommendations
- [ ] **Add mobile mode to UI**
- [ ] **Contextual sidebar navigation** — Redesign the app sidebar so it changes content based on the active section: Advisor shows session history, Browse shows filter controls, Admin shows sub-page links. Top-level nav moves to sidebar header or app header with a back button between sections. Eliminates the double-sidebar problem and gives each section full sidebar width for its own controls

## Recommendation Quality

- [ ] **Proper recommendation system evaluation** — current approach (pgvector + LLM triage + LLM rationale) works but doesn't scale well. Evaluate real recommendation frameworks vs hand-built approach as cost/ratings/feedback data grows
- [ ] **Robust acronym expansion** — the hardcoded 15-acronym list in `pipeline.py` is a bandaid. Replace with a curated dictionary table (loadable from DB, manageable via Admin UI) or automatic expansion from product metadata. Should cover the full Red Hat product portfolio, partner products, and common industry acronyms.
- [ ] **Structured constraint extraction** — current duration handling (soft penalty reranking) is a stopgap. Needs a general constraint extraction pre-processing step: parse query for structured constraints (duration, audience, format, event) and apply as hard filters or scoring overrides before triage.
- [ ] **Multi-turn conversation context** — true conversational refinement with memory (currently prepends original query text as workaround)
- [ ] **Multi-vector event search** — multiple queries per category for broad events
- [ ] **Feedback loop integration** — "Best fit" selections are stored but not yet used to improve scoring
- [ ] **Catalog description as context** — CRD descriptions contain metadata not in Showroom content. Descriptions are unreliable (often stale), so deprioritized vs keywords. Revisit if keyword-boosted search proves insufficient
- [ ] **Combined query (infra + vector in Advisor)** — Deferred. Content vector search already captures product mentions naturally. The real use case is PH express mode which is already served by `GET /catalog/search/infrastructure`. Revisit only if PH needs infrastructure-aware results through the Advisor recommendation pipeline specifically.

## Architecture

- [ ] **Advisor query scaling + queue management** — As user base grows beyond 5 to 50+, the single recommend worker (max 3 concurrent jobs) will back up. Three pieces: (1) Per-user concurrent query limit of 1 — reject with "you already have a query running" to prevent queue flooding from a single user. (2) Queue wait feedback — when a query is queued but no worker has picked it up yet, send an SSE message like "Your query is being processed — this may take a moment during busy periods" so users know they're waiting, not hung. (3) Manual scaling via `recommend_worker_replicas` in Ansible vars when user count grows — bump from 1 to 3 to triple throughput. HPA autoscaling deferred — requires custom Prometheus metrics for queue depth, operationally fragile at current scale.
- [ ] **Showroom live-read endpoint** — on-demand content retrieval for Publishing House "unpacking" workflow
- [ ] **Conversational advisor** — multi-turn refinement with memory (event URL parsing works, this is about deeper conversation context)

## Publishing House Integration

- [ ] **Prototyping workflow** — find closest match, read Showroom/automation, order and modify environment
- [ ] **Showroom unpacking service** — PH delegates content reading to RCARS
- [ ] **Express mode learning data** — store PH express mode run data (selected base CI + customization steps) for future runs. Must be separate from content analysis to avoid polluting search. Coordinate with PH backlog

---

## Completed

- [x] Infrastructure-aware catalog metadata — deployed 2026-06-15
- [x] Rec card duration labels + Best Fit button — deployed 2026-06-15
- [x] Content overlap detection (Phase 1) — deployed 2026-06-15
- [x] Retirement analysis Phase 1 — reporting sync, dashboard, rec card enrichment, CLI — deployed 2026-06-16
- [x] Enhanced retirement scoring + time window filter — percentile scoring, provisions_zero, quarterly JSONB, catalog backfill, cost amortization — deployed 2026-06-17
- [x] LiteMaaS LLM provider — per-model routing with Vertex fallback — deployed 2026-06-16
- [x] Migration race condition fix — replaced k8s_info Jinja with oc rollout status + post-migration verification — deployed 2026-06-17
- [x] Code review remediation — secrets to K8s Secrets, defensive checks, HTTPS validation — 2026-06-16
- [x] Content Analysis unified design — shared CSS, stat cards, sticky headers — 2026-06-16
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
- [x] Admin progress logging — replaced SSE with DB-accumulated message array + polling
- [x] Catalog refresh progress — granular "Upserting... 100/968" progress during upsert phase
- [x] Stale check dedup — clone each unique (url, ref) once instead of per-CI
- [x] Stale check two-phase — `git ls-remote` first to skip unchanged repos
- [x] Stale check timeout — bumped from 10 minutes to 1 hour
- [x] GitHub retry with backoff — 3 retries with exponential delay on rate limit/403 errors
- [x] "Scan" → "Analyze" — consistent terminology across admin UI
- [x] Token Usage page — Triage/Rationale columns
- [x] Admin scrollbar hidden — CSS scrollbar-width:none
- [x] Unanalyzed filter — clickable count on admin page + Browse filter
- [x] New Session fix — custom event dispatch instead of URL navigation
- [x] Vector search candidates — bumped from 10 to 15
- [x] Admin query history — full query text, stage badges, score fallback
- [x] Recommendation dedup by content_hash
- [x] Dev stage restricted to curators/admins
- [x] Triage JSON parsing fix — array fallback extraction
- [x] Event URL parsing in advisor
- [x] Mixed text+URL queries
- [x] ZT toggle removed — included by default based on stage
- [x] Catalog keywords in embeddings
- [x] Stale detection via ls-remote — two-phase check
- [x] Old monolith code removed — 9,505 lines
- [x] Scheduled catalog refresh + stale check — nightly pipeline at 04:00 UTC
- [x] RCARS API for PH vetting
- [x] PH ServiceAccount in SA allowlist
- [x] Scan dedup by commit SHA
- [x] Browse page redesign — server-side filtering, numbered pagination, curator panel
- [x] Admin page reorganization — stat cards, tabbed layout, workload management
- [x] Browse filter dropdowns — Cloud Provider, Workloads, AgnosticD Config
- [x] Admin workload mapping management UI
- [x] Pipeline step messages — human-readable descriptions
- [x] Overlap page search filter
