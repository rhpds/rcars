# Scan Failure Surfacing & Dev/Event Catalog Visibility

**Date:** 2026-04-24
**Status:** Design approved, pending implementation

## Summary

Three related improvements to RCARS:

1. **Scan failure surfacing** — scan errors are currently logged but never surfaced. Add error classification, persistent scan status on catalog items, failure views in admin/curate/CLI, and a Showroom URL override mechanism for items that need manual resolution.
2. **Dev/event catalog visibility** — dev and event CIs are synced but hidden. Make them visible through UI filters and advisor toggle, with stage badges, callouts, and dedup logic to avoid showing duplicate content across stages.
3. **Catalog reconciliation** — items removed from Babylon are never cleaned up. Add hard delete during refresh for CIs no longer present in the Babylon catalog.

## Database Changes

### New columns on `catalog_items`

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `scan_status` | TEXT | `'not_scanned'` | One of: `not_scanned`, `success`, `failed` |
| `scan_error_class` | TEXT | NULL | Classification of the failure (see Error Classification) |
| `scan_error` | TEXT | NULL | Full human-readable error message |
| `scan_failed_at` | TIMESTAMPTZ | NULL | Timestamp of last scan failure |
| `showroom_url_override` | TEXT | NULL | Manual override — scanner uses this instead of auto-detected `showroom_url` when set |

### Behavior on scan

- **Success:** set `scan_status = 'success'`, clear `scan_error_class`, `scan_error`, `scan_failed_at`
- **Failure:** set `scan_status = 'failed'`, populate error fields, set `scan_failed_at = now()`
- **Catalog refresh:** preserve all scan status fields and `showroom_url_override` on upsert — do not clobber

### Scanner URL resolution

When scanning an item, use `showroom_url_override` if set, otherwise fall back to `showroom_url`. This allows manual correction of items whose auto-detected URL is wrong.

## Error Classification

A `classify_scan_error(exception, context)` function in `analyzer.py` inspects the exception type and message to assign a class:

| Class | Triggered by |
|-------|-------------|
| `private_repo` | Git clone auth failure (permission denied, 403) |
| `missing_antora` | Clone succeeds but no `.adoc` files found in expected Antora layout |
| `jinja_url` | Showroom URL contains unresolved Jinja/template variables (`{{`, `{%`) |
| `clone_failed` | Git clone fails for reasons other than auth (bad URL, DNS, network) |
| `timeout` | Clone or analysis exceeds time limit |
| `http_404` | Showroom URL returns 404 or repo not found |
| `no_content` | Files found but all filtered out as boilerplate |
| `parse_error` | Sonnet analysis returns unparseable JSON |
| `unknown` | Catch-all for unexpected failures |

Returns `(error_class, human_message)` tuple. Replaces the current `str(e)[:200]` truncation in the scan command's error handler.

## Scan Failure UI

### Admin page

Add a **Scan failures** row to the existing status summary table. The count is a clickable link to `/curate?filter=scan_failed`.

```
Total catalog items       126
Production items           95
With Showroom URL          84
Analyzed                   74
Stale                       3
Scan failures              10  ← links to /curate?filter=scan_failed
```

### Curate page — scan failures filter

Add `scan_failed` to the existing filter dropdown (alongside `has_showroom`, `all`, `needs_review`, `untagged`).

When selected, shows only items where `scan_status = 'failed'`. Each failure card shows:

- CI name and display name
- Error badge pill with `scan_error_class` (e.g., "private_repo", "missing_antora")
- Full `scan_error` message text
- `scan_failed_at` timestamp
- Showroom URL override text input — pre-populated with current `showroom_url`, editable. Submit saves to `showroom_url_override`.
- Retry button — triggers re-scan using override URL if set, otherwise original

Scan failures do NOT appear in the default Curate view (`has_showroom` filter). They are a separate operational concern, not content to curate.

### CLI — `rcars status`

Add a "Scan failures" row to the default 5-row summary table (now 6 rows). Add a `--failures` flag that prints a secondary table listing each failure:

```
CI Name                          Error Class      Failed At
openshift_cnv/some-broken-lab    private_repo     2026-04-13 14:22
openshift_cnv/another-lab        missing_antora   2026-04-13 14:25
```

## Dev/Event Catalog Visibility

### Refresh changes

`rcars refresh` always syncs all three Babylon namespaces: `babylon-catalog-prod`, `babylon-catalog-dev`, `babylon-catalog-event`. Remove the `--include-dev` flag entirely. All items land in the DB; UI filters control what users see.

### Stage dedup logic

When displaying items across stages, deduplicate based on Showroom content identity:

- Group CIs that represent the same underlying content across stages. The grouping key must be determined during implementation by examining real Babylon CRD naming patterns — CI names may share a base name across namespaces (e.g., same `ci_name` in `babylon-catalog-prod` vs `babylon-catalog-dev`), or may require stripping stage prefixes. Investigate actual CRD data before committing to a grouping strategy.
- If all variants in a group point to the same `showroom_url` + `showroom_ref` → show only the highest-priority stage: **prod > event > dev**
- If repo or branch differs across stages → show each as a distinct item (content is meaningfully different)
- Items without Showroom URLs are never deduped

A `db.get_stage_deduplicated_items()` query function handles this grouping and comparison.

### Curate page — stage filter

Add a **separate** stage filter control alongside the existing status filter. Two independent filters that compose:

- **Stage filter:** All stages (default) / Prod / Dev / Event
- **Status filter:** Has Showroom (default) / All / Needs review / Untagged / Scan failed

Stage dedup applies when "All stages" is selected. Single-stage filter shows only that stage.

Stage badges on item cards:
- **Prod:** no badge (default, clean)
- **Event:** amber/orange badge — "EVENT"
- **Dev:** blue badge — "DEV"

### Advisor page — non-prod toggle

Add an "Include non-prod content" toggle, **off by default**.

When enabled:
- Vector search queries across all stages, not just prod
- Stage dedup applied to results
- Non-prod result cards show stage badge plus stage-specific callout:
  - **Event:** *"Event-only content. Not self-service — contact RHDP ops to order on your behalf."*
  - **Dev:** *"In development. This content may be incomplete or awaiting promotion."*
- Prod items render as today — no badge, no callout

### Scanning dev/event items

All items with Showroom URLs get scanned regardless of stage. Items are only scanned if they don't have a `showroom_analysis` record (new items) or if `--force` is passed. `check-stale` uses content hashing to flag changes. Extra scan cost for dev/event items is minimal.

## Catalog Reconciliation

### During every `rcars refresh`

1. Sync all items from all three Babylon namespaces — upsert as today
2. Collect the full set of `ci_name` values returned by Babylon
3. Query the DB for all `catalog_items` whose `ci_name` is NOT in that set
4. Hard delete those items — cascade to `showroom_analysis`, `analysis_log`, embeddings, `enrichment_tags`
5. Log each removal with CI name and stage
6. Print summary: *"Refreshed N items. Removed M items no longer in Babylon catalog."*

### Future migration path

When historical tracking is desired, switch from hard delete to soft delete:
- Add `removed_at` (TIMESTAMPTZ, nullable) and `removed_reason` (TEXT) columns
- Change delete logic to set `removed_at = now()` instead of `DELETE`
- Add `WHERE removed_at IS NULL` to active queries
- No architectural decisions in this design block that migration
