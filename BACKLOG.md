# RCARS Backlog

Last updated: 2026-04-28

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

## Bugs

- [ ] **DB/worker sync** — arq worker and API update PostgreSQL independently; if worker crashes mid-pipeline, `jobs.status` and `catalog_items.scan_status` can diverge. Needs reconciliation pass or transactional wrapping
- [ ] **Orphaned running jobs** — no mechanism to detect jobs stuck in "running" state from a crashed worker

## UI / UX

- [ ] **Rec card formatting in follow-up queries** — second response can differ from first in formatting quality
- [ ] **Admin query history** — show user email, session duration
- [ ] **Browse "untagged" filter** — dropdown option exists but filter logic is missing (no switch case)
- [ ] **ZT content classification** — distinguish full workshops from micro-labs in browse and recommendations

## Recommendation Quality

- [ ] **Proper recommendation system** — current approach (pgvector + LLM triage + LLM rationale) works but doesn't scale well. Evaluate real recommendation frameworks vs hand-built pgvector+Sonnet as cost/ratings/feedback data grows
- [ ] **Structured constraint extraction** — current duration handling (soft penalty reranking) is a stopgap. Needs a general constraint extraction pre-processing step: parse query for structured constraints (duration, audience, format, event) and apply them as hard filters or scoring overrides before triage. Event keywords (e.g. `summit-2026`, `rh1-2026`) are a high-priority case: when someone asks for "Summit 2026 content", matching against catalog item keywords should be a hard boost that triage can't override, not a vector similarity signal. Consider a curated allowlist of meaningful keywords rather than trusting all keywords equally — catalog keywords contain junk that shouldn't influence scoring
- [ ] **Scan duration data quality** — `estimated_duration_min` from LLM analysis is often inaccurate. No verification against actual lab runtimes. Consider sourcing from catalog metadata or manual curation
- [ ] **Content overlap detection** — proposal vs. catalog comparison, lab-to-lab similarity analysis
- [ ] **Multi-turn conversation** — true conversational refinement with context carry-over (currently prepends original query text as workaround)
- [ ] **Multi-vector event search** — multiple queries per category for broad events
- [ ] **Feedback loop** — "Best fit" selections are stored but not yet used to improve scoring
- [ ] **Catalog description as context** — the catalog item description (from the CRD) contains metadata not present in the Showroom content itself, such as which event it was built for (e.g. "Summit 2026"). Currently the analyzer only sees Showroom .adoc files. Indexing the catalog description alongside the analysis would let queries like "Summit 2026 labs" match even after the CI name loses its event prefix. Need to decide whether to feed it to the LLM analysis, add it to the embedding text, or use it as a structured filter

## Scanner / Pipeline

- [x] **Stale detection via ls-remote** — two-phase check: `git ls-remote` to compare SHA, clone only if changed. Replaces full-clone-every-repo approach
- [ ] **Scan dedup by commit SHA** — resolve refs via `git ls-remote` before scanning; would avoid rescanning when `main` and `v1.0` point to same commit
- [ ] **Non-Showroom content types** — Arcade demos, reference architectures, and other content formats are not scanned or indexed. These need different extraction pipelines (e.g. Arcade JSON/YAML, architecture docs from repos or Confluence). Would enable advisor responses like "here's a reference architecture for deploying X" instead of only hands-on labs
- [ ] **Old monolith code** — `src/rcars/` should be removed once v2 is fully verified

## Operations

- [x] **Scheduled catalog refresh + stale check** — nightly maintenance pipeline via arq cron (refresh → stale check → re-analyze at 04:00 UTC). Configurable via `RCARS_PIPELINE_*` env vars. Manual trigger via Admin UI or `POST /admin/run-maintenance`


## Architecture

- [ ] **Showroom live-read endpoint** — on-demand content retrieval for PH "unpacking"
- [ ] **Conversational advisor** — multi-turn refinement with memory, interactive event URL parsing

## Publishing House Integration

- [ ] **RCARS API for vetting** — PH calls RCARS to check content overlap during intake
- [ ] **Prototyping workflow** — find closest match, read Showroom/automation, order and modify environment
- [ ] **Showroom unpacking service** — PH delegates content reading to RCARS
- [ ] **Infrastructure-aware catalog metadata** — RCARS currently analyzes Showroom content (what a lab teaches) but not environment infrastructure (what operators, workloads, and cluster config each CI provides). PH express mode needs a base-finding query: "what CI gives me an OpenShift cluster with operator X and Y?" This requires indexing AgnosticV catalog item definitions for infrastructure details, not just Showroom content. Enables the express "find closest base infrastructure" use case. Also enables recommending "Open Environments" (no Showroom, just infrastructure credentials) — these have no content to analyze, so catalog description + keywords + AgnosticV definition would be the only signals. Between description and infra metadata, RCARS could recommend "here's an OpenShift cluster with GPU nodes" even without guided lab content.
- [ ] **Express mode learning data** — Store PH express mode run data (selected base CI + customization steps) so future express runs benefit from past experience. Must be stored separately from content analysis data to avoid polluting content search results (this is infrastructure/workflow data, not lab content). Could feed into infrastructure-aware catalog metadata to improve base-finding query accuracy. Coordinate with PH backlog.
- [ ] **PH ServiceAccount in SA allowlist** — add `system:serviceaccount:publishing-house-dev:<ph-backend-sa>` to `RCARS_SA_ALLOWLIST_STR` for cluster-internal auth from PH MCP server (see PH RCARS integration spec)
