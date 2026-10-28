# Platform and Technical Decision Point filters — design

Date: 2026-10-28. Branch: `feature/platform-tdp-filters`.

## Why

Curators need to group catalog content by what it is about, not by where it lives in AgnosticV. The Namespace filter answers "which AgnosticV account?" The new filters answer "which product area?" Example: "show every item whose Platform is OpenShift", or "every item that hits the Virtualization decision point".

AgnosticV now carries these as catalog labels on (almost) every item:

- `__meta__.catalog.labels.Platform` — one value per item.
- `__meta__.catalog.labels.TDP1` — one value per item; `TDP2` — optional second value (~8% of items).

Babylon copies them onto each CatalogItem as `babylon.gpte.redhat.com/Platform`, `.../TDP1`, `.../TDP2`. Verified 2026-10-28 on Babylon prod: CatalogItem values match the AgnosticVComponent for 1,374 of 1,377 items (3 `tests.*` dev items differ). The copy works for new items and for edits.

Current values (git, 2026-10-28): Platform — `OpenShift`, `RHEL`, `AI`, `Ansible_Automation`, `RHDP`, `Open_Environments`, `Other`. TDP — `Server_Cloud_OS`, `Application_Platform`, `AI_Platform`, `Automation`, `Container_Management`, `Virtualization`, `Other`. The curator is cleaning the last typos in AgnosticV; RCARS does not fix values.

## Goals

- Two new filters, **Platform** and **Technical Decision Point**, on four pages: Performance, Non-Prod Items, Retirement, Browse Catalog.
- On Performance, Non-Prod and Retirement they sit next to the existing Namespace filter (which stays).
- Technical Decision Point is one filter: an item matches if TDP1 **or** TDP2 matches a selected value.
- Same look and behavior as each page's existing filters: multi-select (OR within a group, AND across groups), synced to the URL search params. Analysis pages use the checkbox list with per-value counts (like Namespace); Browse uses its sidebar dropdown style (see Per page).

## Non-goals

- **Business Unit filter.** Babylon stopped copying `__meta__.catalog.reportingLabels` (primaryBU/secondaryBU) to CatalogItems around 2026-08-10, so CatalogItem BU values are stale. BU waits for the Babylon fix (separate work: `~/devel/working/ai-handoffs/2026-10-28-babylon-reportinglabels-not-copied.md`). Leave the existing `primary_bu`/`secondary_bu` extraction in `extract_catalog_item()` untouched; do not store it.
- **Product / Product_Family.** Being phased out. Leave the existing extraction untouched; do not add storage.
- No value normalization, aliasing, or typo mapping in RCARS. Show what AgnosticV sends.
- No Advisor/chat/triage changes. No new columns on table rows (filters only).

## Anti-goals

- Do not read these labels from the AgnosticVComponent. The CatalogItem copy is correct and is what the refresh already reads.
- Do not break or rename the Namespace filter or its URL param.

## Decisions

**Data (user-approved):**
- `extract_catalog_item()` (`src/api/rcars/services/catalog.py`) reads `Platform`, `TDP1`, `TDP2` via `_get_label()` (prefix `babylon.gpte.redhat.com/`, case-sensitive keys).
- Stored as three nullable TEXT columns on `babylon_items`: `platform`, `tdp1`, `tdp2`. Added with `ALTER TABLE babylon_items ADD COLUMN IF NOT EXISTS ...` at the bottom of `SCHEMA_SQL` in `src/api/rcars/db/database.py`; added to `bi_fields` in `upsert_babylon_catalog_item()`. Store empty label as NULL.
- Values fill on the next catalog refresh after deploy (nightly or `rcars refresh`). No backfill script.

**Display (builder's call, approved in chat):**
- Show values with underscores replaced by spaces (`Ansible_Automation` → "Ansible Automation"). Display only; filter and URL use the raw value.
- Each group includes a **None** choice for items with no value (for TDP: no TDP1 and no TDP2), so curators can find unlabeled items.

**Per page:**
- **Performance, Non-Prod, Retirement** (`PerformancePage.tsx`, `NonProdItemsPage.tsx`, `RetirementPage.tsx`): filtering is client-side, like Namespace (`extractNs` / `availableNamespaces` / `selectedNamespaces`). Each endpoint (`/analysis/performance`, `/analysis/nonprod`, `/analysis/retirement` in `src/api/rcars/api/routes/analysis.py`) returns per row `platforms: string[]` and `tdps: string[]`.
- These pages show one row per catalog base name, merging stages. Rule: **union** — a row's `platforms` is the distinct set of `platform` across all stages of that base name; `tdps` is the distinct set of `tdp1` ∪ `tdp2` across all stages. A row matches if any value matches. (Usually stages agree; union avoids hiding a row when they don't.)
- Note: the three list queries (`list_performance_data`, `list_nonprod_items`, `list_retirement_items`) `LEFT JOIN babylon_items` on a single `content_id`, which may be one stage or none. Compute the union by base name (`substring(ci_name FROM '^(.+)\.[^.]+$')`) across all `babylon_items` rows, not only the joined one. Include retired stages too, so rows retired after deploy keep their labels.
- **Going forward only (user decision):** stages retired before deploy are never refreshed again, so they keep NULL labels and show under "None". No backfill of any kind. (AgnosticV only gained these labels on 2026-09-15, so most past retirements never had them.)
- **Browse** (`BrowsePage.tsx`, `list_content_entities_filtered()` + `get_catalog_facets()`, routes in `src/api/rcars/api/routes/catalog.py`): filtering is server-side like the other sidebar filters. New query params `platform` and `tdp` (comma-separated, same style as `workloads`/`solutions`), including a sentinel for None. *User decision (after the local run):* Browse uses the same checkbox lists as the analysis pages, without counts (`get_catalog_facets()` returns plain string lists for `platforms` and `tdps`; the UI adds None as the last choice).
- **Collapsible sidebar groups (user decision, all four pages):** every sidebar filter group folds behind its title, except the top group on each page (Performance: the score bands; Non-Prod: Stage; Retirement: Status; Browse: Content Type). Groups start closed, open on load when a filter in them is active, and show the active count in the header ("Clear (n)" or "(n)").
- **Browse sidebar order (user decision):** Content Type, Stage (dev/event toggles moved from the top bar; curator/admin only), Platform, Technical Decision Point, Audience & Difficulty (builder's call: not named by the user), Architecture Filters, Hands-on Labs, Curator Tools.
- Browse also lists portfolio architectures, which have no Platform/TDP. When either filter is active, architectures drop out. "None" means a Babylon item with no value; architectures never match any choice, including None.

## Constraints

- Follow existing filter-group markup and CSS (`browse-filter-group`, checkbox list with counts) and the per-page URL-sync pattern.
- Every visible table column stays sortable (existing rule; nothing new to sort).
- Role gates unchanged: Performance is public by default; Non-Prod and Retirement are curator-only.
- Structured logs (`component`, `action`) on any new backend path, per project convention.
- Tests: pytest for extraction, upsert, union-by-base-name, and Browse server-side filtering (including TDP1-or-TDP2 and None). Vitest for the client-side filter logic if it is factored into a helper.

## Left to the builder

- Helper placement for client-side filtering (shared helper vs per page) and the exact None sentinel string in URLs.
- Facet count scope on Browse (match existing facets: prod, non-retired).
- Sort order of filter values (suggest by count desc, None last).
- Whether to share one FilterGroup component across the three analysis pages.

## Rollout

Deploy with `--tags full` (schema + API + frontend). Then run a catalog refresh on dev and confirm the filters show values on all four pages. Screenshot each page before calling it done.
