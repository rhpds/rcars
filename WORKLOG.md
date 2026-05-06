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
- The `usePrivateMode` hook exists in the frontend code but is not connected to any UI — it's scaffolding for a future privacy feature. Not documented intentionally.
- The `api.rescanStale()` function exists in the API client but is never called by any frontend component.
- The `api.getWorkerHealth()` function exists but is never called — the Workers page uses `getScanProgress()` instead.
- The `/catalog/{ci_name}/override-url` endpoint exists in the backend but has no frontend UI — only available via CLI or API.
- The `catalog_items.scope` column exists in the schema but is never populated by any code path.
