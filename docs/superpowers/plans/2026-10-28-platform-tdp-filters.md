# Platform and TDP Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Platform and Technical Decision Point (TDP1 or TDP2) filters to the Performance, Non-Prod, Retirement and Browse pages, fed by CatalogItem labels.

**Architecture:** The catalog refresh reads three CatalogItem labels into new `babylon_items` columns. A new DB helper unions the values per catalog base name. The three analysis endpoints attach those unions to each row for client-side filtering. Browse filters server-side through `list_content_entities_filtered()` and lists values through `get_catalog_facets()`.

**Tech Stack:** Python 3.11, FastAPI, psycopg 3, PostgreSQL; React 19 + TypeScript + Vite, PatternFly 6; pytest, vitest.

**Spec:** `docs/superpowers/specs/2026-10-28-platform-tdp-filters-design.md`

## Global Constraints

- Label keys (case-sensitive, prefix `babylon.gpte.redhat.com/`): `Platform`, `TDP1`, `TDP2`. Read with `_get_label()`.
- Columns: `babylon_items.platform`, `babylon_items.tdp1`, `babylon_items.tdp2`, all `TEXT NULL`. Empty label → NULL.
- Schema change only via `ALTER TABLE babylon_items ADD COLUMN IF NOT EXISTS ...` at the bottom of `SCHEMA_SQL`.
- No value normalization in the backend. Display only: replace `_` with a space in the UI.
- "None" sentinel string, everywhere (URL, API params, facets): `__none__`. Display text: `None`.
- TDP match rule: an item/row matches if TDP1 or TDP2 is in the selected set. Within a group, choices combine with OR. Across groups, they combine with AND.
- Analysis rows: union across **all** stages of the base name, including retired stages.
- Going forward only: no backfill. Do not read labels from the AgnosticVComponent.
- Do not touch the `product`, `product_family`, `primary_bu`, `secondary_bu` extraction. Do not store them.
- Namespace filter and its `namespace` URL param stay unchanged.
- New URL params on all four pages: `platform`, `tdp` (comma-separated raw values, sorted).
- Structured logs (`component`, `action`) on new backend paths that log.
- Commits: the user must confirm the Jira key before each commit (format `[KEY-123] Imperative description`). No Jira key exists yet, so ask before the first commit.

## Review Focus

- Item with TDP2 only (no TDP1) → must match a TDP filter on that value and must NOT count as "None". Test in Task 2 (`test_labels_union_tdp2_only`) and Task 4 (`test_filter_tdp_matches_tdp2`).
- Stages that disagree (dev says `OpenShift`, prod says `AI`) → the row appears under both values. Test in Task 2 (`test_labels_union_across_stages`).
- Base name whose only stage is retired but has labels → labels still returned. Test in Task 2 (`test_labels_include_retired_stage`).
- "None" combined with a real value (`platform=__none__,OpenShift`) → returns unlabeled items OR OpenShift items. Test in Task 4 (`test_filter_platform_none_or_value`) and Task 5 (`matchesLabels` none+value case).
- Browse with Platform filter on → portfolio architectures excluded, even with `__none__`. Test in Task 4 (`test_filter_platform_none_excludes_architectures`).

---

### Task 1: Read and store Platform/TDP labels

**Files:**
- Modify: `src/api/rcars/services/catalog.py` (`extract_catalog_item()`, ~L47-94)
- Modify: `src/api/rcars/db/database.py` (`SCHEMA_SQL` bottom; `upsert_babylon_catalog_item()` `bi_fields`, ~L873)
- Test: `src/api/tests/test_catalog_labels.py` (new)

**Interfaces:**
- Produces: `extract_catalog_item(crd)` result dict gains keys `platform`, `tdp1`, `tdp2` (`str | None`, None when the label is missing or empty). `babylon_items` gains columns `platform`, `tdp1`, `tdp2`.

- [ ] **Step 1: Write failing tests** in `tests/test_catalog_labels.py`:
  - `test_extract_reads_platform_and_tdps`: a CRD with labels `babylon.gpte.redhat.com/Platform: OpenShift`, `.../TDP1: Virtualization`, `.../TDP2: Application_Platform`, `.../stage: prod` → result has `platform == "OpenShift"`, `tdp1 == "Virtualization"`, `tdp2 == "Application_Platform"`.
  - `test_extract_missing_labels_are_none`: no such labels → all three `is None`. Also label value `""` → `None`.
  - `test_extract_keys_are_case_sensitive`: label `babylon.gpte.redhat.com/platform: OpenShift` (lowercase key) → `platform is None`.
  - `test_schema_adds_label_columns`: for each col in `platform, tdp1, tdp2`, `f"ALTER TABLE babylon_items ADD COLUMN IF NOT EXISTS {col} TEXT" in SCHEMA_SQL`.
  - `test_upsert_stores_labels(db)`: uses the `db` fixture pattern from `tests/test_db.py` (copy the fixture). Upsert an item dict with `ci_name="acct.item.prod"`, `stage="prod"`, `platform="RHEL"`, `tdp1="Server_Cloud_OS"`, `tdp2=None` → `SELECT platform, tdp1, tdp2 FROM babylon_items WHERE ci_name='acct.item.prod'` returns `("RHEL", "Server_Cloud_OS", None)`. Upsert again with `platform="AI"` → row shows `"AI"`.

- [ ] **Step 2: Run and confirm they fail**
  Run: `source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_catalog_labels.py -v`
  Expected: FAIL (`KeyError`/missing columns).

- [ ] **Step 3: Implement.** In `extract_catalog_item()`, add `"platform": _get_label(metadata, "Platform") or None` and the same for `TDP1` → `tdp1`, `TDP2` → `tdp2`. Append the three `ALTER TABLE ... ADD COLUMN IF NOT EXISTS <col> TEXT;` lines at the bottom of `SCHEMA_SQL`. Add `"platform", "tdp1", "tdp2"` to `bi_fields`.

- [ ] **Step 4: Run tests, confirm PASS** (same command). Also run `python -m pytest tests/test_db.py -q` to confirm nothing regressed.

- [ ] **Step 5: Commit** (confirm Jira key with the user first): `git add src/api/rcars/services/catalog.py src/api/rcars/db/database.py src/api/tests/test_catalog_labels.py`, message `[RHDPCD-2218] Store Platform and TDP catalog labels on babylon_items`.

---

### Task 2: Union labels per base name

**Files:**
- Modify: `src/api/rcars/db/database.py` (new method next to `get_stages_for_base_names()`, ~L3337)
- Test: `src/api/tests/test_catalog_labels.py`

**Interfaces:**
- Consumes: Task 1 columns.
- Produces: `Database.get_labels_for_base_names(self, base_names: list[str]) -> dict[str, dict[str, list[str]]]`. Returns `{base_name: {"platforms": [...], "tdps": [...]}}`. Lists are distinct and sorted. NULLs are excluded. `tdps` = union of `tdp1` and `tdp2`. Includes retired stages. Base names with no rows are absent from the dict. Empty input → `{}`.

- [ ] **Step 1: Write failing tests** (DB fixture). Seed with `upsert_babylon_catalog_item` (and set `content_entities.retired_at` via SQL where needed):
  - `test_labels_union_across_stages`: `acct.x.dev` (platform `OpenShift`, tdp1 `Virtualization`) + `acct.x.prod` (platform `AI`, tdp1 `AI_Platform`) → `{"acct.x": {"platforms": ["AI", "OpenShift"], "tdps": ["AI_Platform", "Virtualization"]}}`.
  - `test_labels_union_tdp2_only`: `acct.y.prod` with tdp1 NULL, tdp2 `Automation` → `tdps == ["Automation"]`.
  - `test_labels_include_retired_stage`: `acct.z.prod` labeled `RHEL`, then retired → still `platforms == ["RHEL"]`.
  - `test_labels_unlabeled_item_has_empty_lists`: `acct.n.prod` with all NULL → `{"acct.n": {"platforms": [], "tdps": []}}`.
  - `test_labels_empty_input`: `get_labels_for_base_names([]) == {}`.

- [ ] **Step 2: Run, confirm FAIL** (`python -m pytest tests/test_catalog_labels.py -v`).

- [ ] **Step 3: Implement** with the same base-name match as `get_stages_for_base_names()` (`substring(bi.ci_name FROM '^(.+)\.[^.]+$') IN (...)`), with no retired filter, grouping in Python with `extract_base_name`. Every requested base name that has any row gets an entry, even if its lists are empty.

- [ ] **Step 4: Run, confirm PASS.**

- [ ] **Step 5: Commit** — `[RHDPCD-2218] Add per-base-name Platform/TDP union helper`.

---

### Task 3: Return labels from the three analysis endpoints

**Files:**
- Modify: `src/api/rcars/api/routes/analysis.py` — `performance_dashboard` (~L220, next to `stages_map`), `retirement_dashboard` (~L1066), `nonprod_dashboard` (~L1117)
- Test: `src/api/tests/test_analysis_labels.py` (new)

**Interfaces:**
- Consumes: `db.get_labels_for_base_names(base_names)` (Task 2).
- Produces: each row in `/analysis/performance`, `/analysis/nonprod`, `/analysis/retirement` responses gains `platforms: list[str]` and `tdps: list[str]` (empty lists when unknown). Response models stay `list[dict]`, so no schema change.

- [ ] **Step 1: Write failing tests.** Use the FastAPI `TestClient` setup pattern from `tests/test_api_infrastructure.py`, with `app.state.db` replaced by a stub. The stub returns one row per list method (`list_performance_data`, `list_nonprod_items`, `list_retirement_items`) with `catalog_base_name`/`content_id` for `acct.x`. It returns `{}` for stages/owners helpers, and `{"acct.x": {"platforms": ["OpenShift"], "tdps": ["Virtualization"]}}` for `get_labels_for_base_names`. Tests:
  - `test_performance_rows_have_labels`, `test_nonprod_rows_have_labels`, `test_retirement_rows_have_labels`: the row has `platforms == ["OpenShift"]` and `tdps == ["Virtualization"]`.
  - `test_rows_without_labels_get_empty_lists`: when the helper returns `{}`, the row has `platforms == []` and `tdps == []`.
  If the stub needs too many methods for a route, seed the real test DB instead (fixture from `tests/test_db.py`). Choose one approach per route and keep it.

- [ ] **Step 2: Run, confirm FAIL.**

- [ ] **Step 3: Implement.** In each route, after `base_names` is built, call `labels_map = db.get_labels_for_base_names(base_names)`. In the per-item loop, set `item["platforms"] = labels_map.get(bn, {}).get("platforms", [])` and the same for `tdps`.

- [ ] **Step 4: Run, confirm PASS.** Then run `python -m pytest tests/test_nonprod.py tests/test_status_visibility.py tests/test_retirement_workflow.py -q`. Pre-existing failures (DB login, golden routing, env config) are known. Compare them against `main` before you blame this change.

- [ ] **Step 5: Commit** — `[RHDPCD-2218] Return Platform/TDP sets on analysis dashboard rows`.

---

### Task 4: Browse server-side filters and facets

**Files:**
- Modify: `src/api/rcars/db/database.py` — `list_content_entities_filtered()` (~L1200), `get_catalog_facets()` (~L2192)
- Modify: `src/api/rcars/api/routes/catalog.py` — `list_catalog()` (~L56)
- Test: `src/api/tests/test_catalog_labels.py`

**Interfaces:**
- Consumes: Task 1 columns.
- Produces:
  - `list_content_entities_filtered(..., platforms: list[str] | None = None, tdps: list[str] | None = None, ...)`.
  - `GET /api/v1/catalog` query params `platform` and `tdp` (comma-separated, `__none__` allowed).
  - `get_catalog_facets()` result gains `"platforms": list[str]` and `"tdps": list[str]`: distinct non-null values over prod, non-retired Babylon items, sorted. `tdps` is the union of tdp1 and tdp2. `__none__` is NOT included (the UI adds it).

- [ ] **Step 1: Write failing tests** (DB fixture; seed prod items: A `OpenShift`/tdp1 `Virtualization`; B `AI`/tdp1 NULL/tdp2 `Automation`; C all NULL; plus one portfolio architecture row, using the seed pattern from `tests/test_osspa_db.py`):
  - `test_filter_platform_value`: `platforms=["OpenShift"]` → only A.
  - `test_filter_tdp_matches_tdp2`: `tdps=["Automation"]` → only B.
  - `test_filter_platform_none_or_value`: `platforms=["__none__", "OpenShift"]` → A and C.
  - `test_filter_tdp_none`: `tdps=["__none__"]` → only C (B is not None because it has a TDP2).
  - `test_filter_platform_none_excludes_architectures`: `platforms=["__none__"]` → C only, and the architecture is absent.
  - `test_filter_groups_and`: `platforms=["AI"], tdps=["Virtualization"]` → empty.
  - `test_facets_platforms_and_tdps`: `get_catalog_facets()["platforms"] == ["AI", "OpenShift"]` and `["tdps"] == ["Automation", "Virtualization"]`.

- [ ] **Step 2: Run, confirm FAIL.**

- [ ] **Step 3: Implement.** Add conditions. Platform: `(bi.platform = ANY(%(platforms)s) OR (%(platform_none)s AND bi.content_id IS NOT NULL AND bi.platform IS NULL))`. TDP: `(bi.tdp1 = ANY(%(tdps)s) OR bi.tdp2 = ANY(%(tdps)s) OR (%(tdp_none)s AND bi.content_id IS NOT NULL AND bi.tdp1 IS NULL AND bi.tdp2 IS NULL))`. Strip `__none__` from the value list and pass the boolean separately. When either filter is set, also require `bi.content_id IS NOT NULL`, so architectures drop out. Add both lists to `babylon_specific`. In the route, split the params like `solutions`. Add two facet queries modeled on the `cloud_provider` facet (`tdps` via `UNION` of tdp1/tdp2).

- [ ] **Step 4: Run, confirm PASS.** Also run `python -m pytest tests/test_catalog_osspa_routes.py -q`.

- [ ] **Step 5: Commit** — `[RHDPCD-2218] Filter Browse by Platform and TDP with facets`.

---

### Task 5: Shared frontend helpers and checkbox filter group

**Files:**
- Create: `src/frontend/src/utils/labelFilters.ts`
- Create: `src/frontend/src/utils/labelFilters.test.ts`
- Create: `src/frontend/src/components/LabelFilterGroup.tsx`

**Interfaces:**
- Produces:
  - `export const NONE_LABEL = '__none__'`
  - `export function labelDisplay(value: string): string`: `NONE_LABEL` → `'None'`; otherwise replaces all `_` with spaces.
  - `export function matchesLabels(values: string[], selected: Set<string>): boolean`: true if `selected` is empty, OR any value is in `selected`, OR (`selected.has(NONE_LABEL)` and `values.length === 0`).
  - `export function countLabelValues<T>(items: T[], get: (i: T) => string[]): [string, number][]`: counts each value once per item. An item with no values counts under `NONE_LABEL`. Sorted by count desc, then name. `NONE_LABEL` is always last when present.
  - `export function LabelFilterGroup(props: { title: string; options: [string, number][]; selected: Set<string>; onToggle: (v: string) => void; onClear: () => void })`: renders the same markup as the Namespace group in `PerformancePage.tsx` (~L351-375: `browse-filter-group`, label with "Clear (n)" button, scrollable checkbox list with `(count)`), using `labelDisplay()` for text.

- [ ] **Step 1: Write failing vitest tests** in `labelFilters.test.ts`:
  - `labelDisplay('Ansible_Automation') === 'Ansible Automation'`, `labelDisplay('__none__') === 'None'`.
  - `matchesLabels(['OpenShift'], new Set()) === true`; `matchesLabels(['OpenShift'], new Set(['AI'])) === false`; `matchesLabels(['AI','OpenShift'], new Set(['AI'])) === true`; `matchesLabels([], new Set(['__none__'])) === true`; `matchesLabels([], new Set(['AI', '__none__'])) === true`; `matchesLabels(['AI'], new Set(['__none__'])) === false`.
  - `countLabelValues([{v:['A']},{v:['A','B']},{v:[]}], i => i.v)` deep-equals `[['A',2],['B',1],['__none__',1]]`.

- [ ] **Step 2: Run, confirm FAIL:** `cd src/frontend && npx vitest run src/utils/labelFilters.test.ts`

- [ ] **Step 3: Implement** the helpers and the component.

- [ ] **Step 4: Run, confirm PASS**, and `npx tsc -b`.

- [ ] **Step 5: Commit** — `[RHDPCD-2218] Add shared label filter helpers and checkbox group`.

---

### Task 6: Wire filters into Performance, Non-Prod and Retirement

**Files:**
- Modify: `src/frontend/src/pages/PerformancePage.tsx`, `src/frontend/src/pages/NonProdItemsPage.tsx`, `src/frontend/src/pages/RetirementPage.tsx`
- Modify: the row types for these pages (wherever `PerformanceItem` and the Non-Prod/Retirement item types are declared) — add `platforms: string[]`, `tdps: string[]`

**Interfaces:**
- Consumes: Task 3 row fields, and Task 5 `LabelFilterGroup`, `countLabelValues`, `matchesLabels`.

- [ ] **Step 1: Per page, add state** `selectedPlatforms` / `selectedTdps: Set<string>`. Initialize them from the `platform` / `tdp` search params. Write them back in the existing URL-sync effect (sorted, comma-joined, omitted when empty). Clear them wherever Namespace is cleared (the "reset filters" paths).

- [ ] **Step 2: Filter.** Apply `matchesLabels(i.platforms ?? [], selectedPlatforms) && matchesLabels(i.tdps ?? [], selectedTdps)` at the same point `nsMatch` is applied. Compute counts with `countLabelValues` over the same base list that Namespace counts use (`statusBaseItems` on Performance, and the equivalent on the other two pages).

- [ ] **Step 3: Render** two `LabelFilterGroup`s directly after the Namespace group, titled `Platform` and `Technical Decision Point`.

- [ ] **Step 4: Verify:** `cd src/frontend && npx tsc -b && npx vitest run` passes.

- [ ] **Step 5: Commit** — `[RHDPCD-2218] Add Platform and TDP filters to analysis pages`.

---

### Task 7: Browse UI (provisional style)

**Files:**
- Modify: `src/frontend/src/services/api.ts` — `listCatalog` params (~L44) gain `platform?: string`, `tdp?: string`; `getCatalogFacets` type (~L173) gains `platforms: string[]`, `tdps: string[]`
- Modify: `src/frontend/src/components/WorkloadMultiSelect.tsx` — optional prop `formatOption?: (v: string) => string` (display only; defaults to identity)
- Modify: `src/frontend/src/pages/BrowsePage.tsx`

**Interfaces:**
- Consumes: Task 4 API, Task 5 `NONE_LABEL`, `labelDisplay`.

- [ ] **Step 1:** In `BrowsePage.tsx`, add `selectedPlatforms` / `selectedTdps: string[]` state, initialized from the `platform` / `tdp` search params. Sync them to the URL. Send them as `platform` / `tdp` in the `listCatalog` params. Reset `page` to 1 on change, the same way other filters do.

- [ ] **Step 2:** Add one `browse-filter-group` labeled "Catalog Labels", with two `WorkloadMultiSelect`s (placeholders `Platform...` and `Technical Decision Point...`). Their options are `[...facets.platforms, NONE_LABEL]` and `[...facets.tdps, NONE_LABEL]`, with `formatOption={labelDisplay}`. Keep this block self-contained, because the user will judge the style when it runs and may ask to swap it.

- [ ] **Step 3: Verify:** `npx tsc -b && npx vitest run` passes. Existing `pages/browse/helpers.test.ts` still passes.

- [ ] **Step 4: Commit** — `[RHDPCD-2218] Add Platform and TDP filters to Browse`.

---

### Task 8: Run locally, check, and prepare the PR

- [ ] **Step 1:** `./dev-services.sh start`. Run a catalog refresh locally (`rcars refresh` in the venv, or the Sync page) so the new columns fill. Confirm with `psql` that `SELECT count(*) FILTER (WHERE platform IS NOT NULL) FROM babylon_items` is > 0. The local DB needs a Babylon kubeconfig; if a refresh is not possible locally, say so and stop for the user.
- [ ] **Step 2:** Open http://localhost:3000. On Performance, Non-Prod, Retirement and Browse:
  - Select `OpenShift` and check that the rows narrow.
  - Select a TDP value and check that the rows narrow.
  - Select `None` and check it.
  - Reload the page and check that the URL keeps the filters.
  Take a screenshot of each page. Show the Browse screenshot to the user for the style decision.
- [ ] **Step 3:** `graphify update .` and commit `graphify-out/` on the branch (`[RHDPCD-2218] Update graphify output`).
- [ ] **Step 4:** Before any push, state the branch, remote and commits, and get explicit approval. Then open a PR with Summary and Changes sections, ending with `Generated with Claude Code`. Wait for CodeRabbit.
- [ ] **Step 5:** After merge, the user deploys with `ansible-playbook ansible/deploy.yml -e env=dev --tags full`, then runs a catalog refresh on dev.
