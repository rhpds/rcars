# RCARS Backlog

Last updated: 2026-04-27

## Completed This Session (2026-04-27)

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

## In Progress

- [ ] Full rescan running (nav.adoc fix, ~385 repos, started 2026-04-27 ~14:40 UTC)
- [ ] Workers page improvements committed but not yet deployed (waiting for scan to finish)

## Bugs

- [ ] **Viewport scroll still broken** — chat pane extends beyond viewport when response is long; `html/body/#root overflow:hidden` fix committed but not yet deployed
- [ ] **Nav.adoc edge case** — pages used outside nav.adoc (rare but possible); current behavior: nav.adoc is source of truth, unlisted pages are skipped
- [ ] **DB/worker sync** — arq worker and API update PostgreSQL independently; if worker crashes mid-pipeline, `jobs.status` and `catalog_items.scan_status` can diverge. Needs reconciliation pass or transactional wrapping
- [ ] **Orphaned running jobs** — no mechanism to detect jobs stuck in "running" state from a crashed worker

## UI / UX

- [ ] **Rec card formatting in follow-up queries** — second response can differ from first in formatting quality
- [ ] **Advisor scroll containment** — deployed fix needs verification after next build
- [ ] **Admin query history** — show user email, session duration
- [ ] **Browse page** — ZT content classification (distinguish full workshops from micro-labs, filter in recommendations)
- [ ] **Browse page** — "untagged" filter not yet implemented
- [ ] **Private mode toggle** — opt-out of query logging (design started, deferred)

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
- [ ] **Old monolith code** — `src/rcars/` should be removed once v2 is fully verified
- [ ] **Nav.adoc subdirectory xrefs** — test with repos that use nested module structures (e.g. `xref:200-ops/lab_1.adoc`)

## Architecture

- [ ] **Dev/event catalog visibility** — configurable scope filtering, "not yet available" callout for dev-only content
- [ ] **Showroom live-read endpoint** — on-demand content retrieval for PH "unpacking"
- [ ] **Conversational advisor** — multi-turn refinement with memory, interactive event URL parsing

## Publishing House Integration

- [ ] **RCARS API for vetting** — PH calls RCARS to check content overlap during intake
- [ ] **Prototyping workflow** — find closest match, read Showroom/automation, order and modify environment
- [ ] **Showroom unpacking service** — PH delegates content reading to RCARS
