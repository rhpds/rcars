# Description-Based Analysis for Items With No Showroom — Design

**Date:** 2026-11-17
**Status:** Approved (Nate, 2026-11-19)
**Jira:** [RHDPCD-2264](https://redhat.atlassian.net/browse/RHDPCD-2264) (epic RHDPCD-25)
**Repo context:** `src/api/rcars` (Python 3.11, FastAPI + arq workers), `src/frontend` (React 19 + PatternFly)

## Intent

Some orderable catalog items will never have a Showroom of their own — the person
provisioning them supplies the content (e.g. `agd_v2.ocp-field-asset-cnv`,
`published.ocp-field-asset`). The scanner cannot analyze them, so they sit at
`scan_status = failed` forever and drive the `analysis_stale` coverage flag in
`get_db_currency()` over its 10% threshold (currently 10.9% in prod).

We want a per-item, curator-controlled way to analyze such items from text
instead of a Showroom repo, so they become normal, recommendable, analyzed
content. We explicitly do **not** want a blanket "analyze every description"
rule: most non-Showroom items are older or one-off, and their descriptions are
not trusted.

## Goals

- A curator can set, per item, an **analysis source**:
  - `showroom` — the default, current behavior, unchanged.
  - `agnosticv_description` — analyze the item's Babylon/AgnosticV description
    (already stored in `babylon_items.description`, refreshed nightly by the
    catalog refresh). Re-analyzed automatically whenever the description text
    changes.
  - `custom_description` — analyze curator-written text stored in RCARS.
    Analyzed once when saved; never re-analyzed until a curator edits the text.
- Description-analyzed items produce the same artifacts as showroom-analyzed
  items: `showroom_analysis` row, card fields on `content_entities`
  (summary, products, topics, audience, difficulty), and embeddings — so they
  appear in Browse cards and are retrievable/recommendable by the advisor.
- Description-analyzed items count as analyzed: `scan_status = 'success'`,
  out of `failed_count`, out of the coverage numerator.
- Setting and clearing the source is curator-only, from the existing Browse
  edit drawer.

## Non-goals

- No blanket/automatic description analysis. Opt-in per item only.
- No new "exclude from scanning" mechanism in this scope. Items nobody curates
  keep their current behavior (failed scans stay failed).
- Not fixing the other ~58 failed scans. Fixing the six field-asset items
  brings coverage to ~74/735 ≈ 10.1%; the flag stays on until those are
  addressed separately.
- No changes to the OSSPA/architecture pipeline. Scope is Babylon
  `lab`/`demo` items.

## Anti-goals

- Field-asset items disappearing from Browse. They are real, orderable
  catalog items; unlike `tests.*` exclusion (which drops items at catalog
  refresh, `services/catalog.py:492`), this feature must never remove an item
  from the catalog.
- Reusing `is_content_excluded()` for this — it gates catalog ingestion, not
  scanning, so it cannot express "stay visible, analyze differently".

## Constraints

- The scanner's compare-and-swap and advisory-lock flow
  (`services/showroom_scan.py`) must keep working unchanged for showroom items.
- LLM analysis stays structured JSON with `parse_analysis_response()`; no prose
  parsing.
- Analysis provenance/signature machinery (`AnalysisSignature`,
  `analysis_generation`) must keep detecting stale generations for these items,
  because it guards the atomic persistence path.
- Scan jobs run on the scan worker (600s timeout, max 5 concurrent) —
  description analysis is far cheaper than a clone + LLM call, so no new worker
  or queue is needed.
- Curator overrides must survive `clear_babylon_generated_artifacts` /
  `reset_babylon_scan_artifacts` ("Preserve identity, source/curator overrides,
  human review fields" — `db/database.py`), like `showroom_url_override` does.

## Approaches considered

1. **Config list (Ansible var → env var).** Scanner marks listed items
   excluded. Small, but: needs a config deploy per item, gives no analysis (no
   advisor value), and exclusion as a concept collides with the
   catalog-ingestion meaning of `is_content_excluded`. Rejected — no curator
   self-service, no recommendability.
2. **Curator "never scan" DB toggle.** Self-serve, but only stops the bleeding;
   items stay unanalyzed and un-recommendable. Rejected as a standalone feature.
3. **Per-item analysis source (chosen).** Curator picks, per item in the Browse
   edit drawer, whether the item is analyzed from its AgnosticV description or
   from custom text. Rides the existing per-item override precedent
   (`showroom_url_override`, set via `POST /api/v1/catalog/{id}/override-url`,
   `routes/catalog.py:414`) and the existing hash-based staleness machinery, so
   both refresh rules (nightly for descriptions, once-only for custom text)
   fall out of a single content-hash comparison.

## Design

### 1. Storage

Two new nullable columns on `babylon_items` (ALTER TABLE ADD COLUMN IF NOT
EXISTS at the bottom of `SCHEMA_SQL`, per project convention):

- `analysis_source_override TEXT NULL` — values `NULL` (default showroom),
  `'agnosticv_description'`, `'custom_description'`.
- `custom_description TEXT NULL` — the custom text; only meaningful when the
  override is `'custom_description'`.

`babylon_items` is chosen over `content_entities` because the override only
applies to Babylon lab/demo items and because the sibling
`showroom_url_override` already lives there.

### 2. Source resolution

New pure function in `services/showroom_source.py`:

```python
def effective_analysis_source(item: dict) -> str:
    """'showroom' | 'agnosticv_description' | 'custom_description'."""
```

Reads the override off the item row. Every consumer branches on this before
any showroom-URL logic.

### 3. Scan pipeline branch

In `_scan_babylon_item` (`services/showroom_scan.py`), immediately after the
`excluded` and content-owner checks and **before** showroom-source resolution:

- If `effective_analysis_source(item) != 'showroom'`, run the description
  path instead of `analyze_showroom`, and skip reuse-key locking (there is no
  repo to share; the compare-and-swap on `analysis_generation` already
  prevents lost updates).
- The description path (new function, `analyze_description()` in
  `services/analyzer.py`):
  1. Text = `item["custom_description"]` or `item["description"]`
     (`babylon_items.description`, already refreshed nightly by
     `refresh_catalog`).
  2. `content_hash = sha256(normalized_text)`. If it equals the stored
     `content_hash`, the `context_hash` matches, and the row is not stale,
     return `unchanged` — this implements both refresh rules. Staleness is
     hash-of-text **plus** context hash (display name, category, product,
     content type, model), mirroring `_own_analysis_current` for showroom
     items, so a rename or recategorization re-triggers analysis.
  3. `force` bypasses the short-circuit, exactly as it does for showroom
     items. The "never re-analyze until edited" rule governs the *nightly*
     pipeline only; a curator can still force a manual rescan with the
     existing rescan action when the LLM produced a poor result.
  3. Build a prompt variant (`build_description_prompt`) that presents the
     catalog description as the content and asks for the **same structured
     JSON schema** the showroom triage returns, so all downstream handling —
     card fields, embeddings, drivers — works unchanged. The prompt should
     tell the model the input is a catalog description, not lab modules, and
     to expect less structure.
  4. Signature: reuse `AnalysisSignature` with sentinel values —
     `repo='description:<content_id>'` (or a similar per-item sentinel),
     `ref=None`, `commit=None`, real `content_hash`, `context_hash` over the
     same context fields, `input_hash` over the description prompt. Sentinels
     guarantee `find_showroom_donor` never cross-matches a description
     analysis with a showroom donor.
  5. Persist through the same compare-and-swap block as today: upsert
     `showroom_analysis` (provenance records `source_type`), update card
     fields, `regenerate_embeddings` with embedding text built from the
     description, `set_scan_status(content_id, 'success')`.
- Outcome/logging: outcome string e.g. `description_analyzed` /
  `description_unchanged`, with `component='scanner'` structlog fields per
  logging convention. `scan_status` is still `'success'`.

### 4. Candidate selection and stale check

- `get_items_needing_analysis` (`db/database.py:2782`): today it drops items
  whose showroom source is unresolved. Change: if
  `effective_analysis_source(item) != 'showroom'`, keep the item and apply the
  description staleness check (stored `content_hash` vs hash of current text)
  instead of `showroom_work_needed`.
- `get_stale_check_candidates` / stale check: description items must not go
  through `git ls-remote` staleness. Skip them keyed off the override —
  **not** off `source.status != 'resolved'` (`workers/ops.py:99`). Verified
  in prod (2026-11-19): the field-asset items have **no** showroom URL at
  all — their `ocp4_workload_showroom_content_git_repo` is an unresolved
  Jinja template, so every scan fails with `invalid_source`, and a stale
  check touching their source would invalidate the fresh description
  analysis. They refresh through the normal scan candidate path.
- The compare-and-swap guard must see the new columns: add
  `analysis_source_override` and `custom_description` to the `_snapshot()`
  tuple (`showroom_scan.py:17`), so a mid-scan source flip is detected as a
  superseded generation instead of a lost update.

### 5. API

One new curator-only endpoint, following the `override-url` pattern:

- `PUT /api/v1/catalog/{identifier}/analysis-source`
  Body: `{ "source": "showroom" | "agnosticv_description" | "custom_description",
           "custom_description": str | null }`
  - Sets/clears the override. `custom_description` required (non-empty) when
    source is `custom_description`; cleared when another source is chosen.
    For `agnosticv_description`, the stored `babylon_items.description` must
    be non-empty — reject at save time with a clear message rather than
    letting the nightly job bounce the item back to `failed` with an opaque
    error.
  - Switching back to `showroom` clears the description-derived artifacts
    (analysis row fields it owns, card fields, embeddings) immediately on
    save — precedent: the immediate clearing on content_type transitions in
    `db/database.py` (~line 937) — so Browse never shows a description-derived
    summary on an item that is back to showroom semantics.
  - After saving, enqueue a single-item analysis job for that content_id
    (reuse the existing single-item scan job machinery from the analysis
    routes) so the curator sees results without waiting for the nightly run.

### 6. Frontend

Browse edit drawer (`src/frontend/src/pages/BrowsePage.tsx`, API client in
`src/frontend/src/services/api.ts`):

- New "Analysis source" control: three radio options — Showroom (default),
  Use catalog description, Custom description.
- Selecting Custom description shows a textarea.
- Helper text explains the refresh behavior for each option (nightly vs
  on-save-only).
- Curator-only visibility, matching the existing override-url control in the
  same drawer.
- Nice-to-have: show the effective analysis source (e.g. a small tag) on the
  Browse card or in the Content Analysis page, so curators can see which items
  are description-based.

### 7. Coverage math

`get_db_currency` needs no change: description-analyzed items have
`scan_status = 'success'` and a current `showroom_analysis` row, so they leave
`(stale + unanalyzed + failed)` and the numerator shrinks by however many
items curators convert. `scannable` is unchanged.

## Decisions (Nate, 2026-11-19)

1. **Override scope: per row.** The columns live on `babylon_items`, so each
   stage variant (`…-cnv.prod`, `…-cnv.dev`, `…-cnv.event`) is a separate row
   that needs its own override. This matches the `showroom_url_override`
   precedent ("curator overrides belong to this target, never to its generic
   base", `showroom_source.py:92"). Showroom items get sibling coverage for
   free through reuse keys and donor matching; description items do not, and
   that is accepted.
2. **Scope: lab/demo only.** Sandboxes stay out. An item with no showroom
   declaration at all is classified `sandbox` (`db/database.py:838`) and
   never enters scan candidates; sandboxes keep their deterministic
   `build_sandbox_summary()` path. If a sandbox ever needs LLM analysis,
   that is a separate follow-up. Verified context: the sandbox auto-summary
   only has infrastructure facts for AgnosticD v2 components
   (`extract_infrastructure_metadata`, `services/catalog.py:261`, returns
   None for non-v2); for v1 sandboxes like `sandboxes-gpte.sandbox-open.prod`
   the "summary" is a byte-for-byte copy of the description (verified in
   prod), which reads as empty when the description is NOTE boilerplate.

## Open items for the builder

- Exact prompt wording for `build_description_prompt` (keep the JSON schema
  identical to showroom triage; adapt the framing for a short catalog
  description).
- Sentinel choice for signature fields — any stable per-item value works as
  long as it can never equal a real repo URL.
- Verify how the six field-asset items resolve under the content-owner model
  (`content_owner()` returns non-None for Virtual CI stubs) — the override
  branch must sit **after** the content-owner/stub branch so stub mirroring
  keeps precedence, and the six items must actually reach the override branch
  (i.e. confirm none of them is treated as a pure stub of another CI).
- Verified in prod (2026-11-19, read-only query): the field-asset items'
  stored `babylon_items.description` values are substantial (4.6k–7.5k
  chars). The `published.*` descriptions start with the real content; the
  `agd_v2.*` ones start with a "do not order this item" developer warning.
  Curators will likely prefer setting the override on the `published.*` rows.
  Also verified: all field-asset lab rows fail with `invalid_source` (empty
  showroom URL, unresolved template), and `agd-v2.ocp-field-asset-rosa.dev`
  / `published.ocp-cloud-ssa-field-asset.dev` are classified sandbox and sit
  at `not_scanned`.
- Test list (pytest, mock LLM per `tests/conftest.py` conventions): source
  resolution; scan branch selection; hash-unchanged short-circuit; `force`
  bypasses the short-circuit; description change triggers re-analysis;
  context change (rename) triggers re-analysis; custom text only re-runs on
  edit; empty-description rejection at the endpoint; reverting to showroom
  clears description artifacts; reset preserves the override columns;
  candidate selection includes overridden items; stale check skips them;
  mid-scan source flip is superseded (snapshot includes new columns);
  endpoint auth (curator gate).

## Deployment

Code-only change; schema addition is a plain `ALTER TABLE ADD COLUMN IF NOT
EXISTS`, applied by the normal `rcars init-db` on deploy. Dev first, then
prod, per project workflow. No new config vars.
