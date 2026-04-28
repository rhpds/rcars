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
- [ ] **Duration constraint handling** — current soft penalty (log-curve reranking) is a stopgap. Needs constraint extraction as a pre-processing step: parse query for structured constraints (duration, audience, format), pass as parameters to pipeline
- [ ] **Scan duration data quality** — `estimated_duration_min` from LLM analysis is often inaccurate. No verification against actual lab runtimes. Consider sourcing from catalog metadata or manual curation
- [ ] **Content overlap detection** — proposal vs. catalog comparison, lab-to-lab similarity analysis
- [ ] **Multi-turn conversation** — true conversational refinement with context carry-over (currently prepends original query text as workaround)
- [ ] **Multi-vector event search** — multiple queries per category for broad events
- [ ] **Feedback loop** — "Best fit" selections are stored but not yet used to improve scoring

## Scanner / Pipeline

- [ ] **Scan dedup by commit SHA** — resolve refs via `git ls-remote` before scanning; would avoid rescanning when `main` and `v1.0` point to same commit
- [ ] **Stale detection improvements** — current content hash comparison requires full clone; could use GitHub API for lightweight checks
- [ ] **Non-Showroom content types** — Arcade demos, reference architectures, and other content formats are not scanned or indexed. These need different extraction pipelines (e.g. Arcade JSON/YAML, architecture docs from repos or Confluence). Would enable advisor responses like "here's a reference architecture for deploying X" instead of only hands-on labs
- [ ] **Old monolith code** — `src/rcars/` should be removed once v2 is fully verified

## Architecture

- [ ] **Showroom live-read endpoint** — on-demand content retrieval for PH "unpacking"
- [ ] **Conversational advisor** — multi-turn refinement with memory, interactive event URL parsing

## Publishing House Integration

- [ ] **RCARS API for vetting** — PH calls RCARS to check content overlap during intake
- [ ] **Prototyping workflow** — find closest match, read Showroom/automation, order and modify environment
- [ ] **Showroom unpacking service** — PH delegates content reading to RCARS
- [ ] **Infrastructure-aware catalog metadata** — RCARS currently analyzes Showroom content (what a lab teaches) but not environment infrastructure (what operators, workloads, and cluster config each CI provides). PH express mode needs a base-finding query: "what CI gives me an OpenShift cluster with operator X and Y?" This requires indexing AgnosticV catalog item definitions for infrastructure details, not just Showroom content. Enables the express "find closest base infrastructure" use case.
- [ ] **PH ServiceAccount in SA allowlist** — add `system:serviceaccount:publishing-house-dev:<ph-backend-sa>` to `RCARS_SA_ALLOWLIST_STR` for cluster-internal auth from PH MCP server (see PH RCARS integration spec)
