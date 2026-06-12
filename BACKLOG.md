# RCARS Backlog

Last updated: 2026-06-12

## Active Work (June 2026)

Items selected for current development cycle. Investigations complete, design/implementation in progress.

- [x] **Infrastructure-aware catalog metadata** — Deployed to dev (2026-06-12). AgnosticD v2 items: infra extraction (config, cloud, OCP version, OS image, workloads, ACL groups), curated workload mapping (46 verified via Haiku code analysis), faceted search API with AND semantics + alias resolution, workload scanner in nightly pipeline, Browse UI (v2 badge, infra panel, filter toggle), Admin UI (scan button, infra stats). Remaining: Browse filter dropdowns (config/cloud/OS/workload), Admin mapping management table, combined query (infra+vector) in Advisor.
- [ ] **Rec card template + duration labels + Best Fit button** — Three related UI changes: (1) Rigid card template so follow-up queries render identically to first turn. (2) Hybrid curated/LLM duration: add `curated_duration_min` column, only apply duration scoring penalty on curated values, label as "AI estimate" vs "estimated". (3) Rename "Best fit" → "This is the best fit", make it a prominent action button instead of a passive label.
- [ ] **Content overlap detection** — Pairwise cosine similarity on existing ci_summary embeddings. New `content_similarity` table, admin overlap report, Browse "similar content" section. ~400 unique showrooms = ~80K comparisons, computed periodically. Configurable thresholds: 0.85+ likely overlap, 0.75-0.85 related.
- [ ] **Non-Showroom content: Portfolio Architectures** — Ingest published architectures from OSSPA (manifest: `gitlab.com/osspa/osspa-site` PAList.csv, content: `gitlab.com/osspa/portfolio-architecture-examples` AsciiDoc). New extraction pipeline, new `content_type` field. Arcade/interactive demos deferred (need video access strategy).

## Infrastructure Metadata — Remaining

- [ ] **Browse filter dropdowns** — Config, cloud provider, OS image, and workload dropdowns populated from `/catalog/facets` API. Currently only the v2 toggle exists
- [ ] **Admin workload mapping management UI** — Table of all mappings (role/product/description/category/verified), inline edit, unmapped workloads with [Map] button
- [ ] **Combined query (infra + vector)** — Add `infra_filter` parameter to advisor queries so PH can ask "OpenShift AI cluster for fraud detection" and get both infrastructure and content matching. Deferred from Session 3

## Bugs

- [ ] **DB/worker sync divergence** — arq worker and API update PostgreSQL independently; if worker crashes mid-pipeline, `jobs.status` and `catalog_items.scan_status` can diverge. Needs reconciliation pass or transactional wrapping
- [ ] **Orphaned running jobs** — no mechanism to detect jobs stuck in "running" state from a crashed worker. Needs a timeout-based cleanup or heartbeat check

## UI / UX

- [ ] **Admin query history** — show user email, session duration
- [ ] **Browse "untagged" filter** — dropdown option exists but filter logic is missing (no switch case)
- [ ] **ZT content classification** — distinguish full workshops from micro-labs in browse and recommendations
- [ ] **Add mobile mode to UI**

## Recommendation Quality

- [ ] **Proper recommendation system evaluation** — current approach (pgvector + LLM triage + LLM rationale) works but doesn't scale well. Evaluate real recommendation frameworks vs hand-built approach as cost/ratings/feedback data grows
- [ ] **Structured constraint extraction** — current duration handling (soft penalty reranking) is a stopgap. Needs a general constraint extraction pre-processing step: parse query for structured constraints (duration, audience, format, event) and apply as hard filters or scoring overrides before triage. Event keywords (e.g. `summit-2026`) should be a hard boost, not just vector similarity. Consider curated keyword allowlist
- [ ] **Multi-turn conversation context** — true conversational refinement with memory (currently prepends original query text as workaround)
- [ ] **Multi-vector event search** — multiple queries per category for broad events
- [ ] **Feedback loop integration** — "Best fit" selections are stored but not yet used to improve scoring
- [ ] **Catalog description as context** — CRD descriptions contain metadata not in Showroom content. Descriptions are unreliable (often stale), so deprioritized vs keywords. Revisit if keyword-boosted search proves insufficient

## Architecture

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
