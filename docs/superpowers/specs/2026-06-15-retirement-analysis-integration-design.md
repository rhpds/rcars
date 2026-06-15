# Retirement Analysis Integration — Design Spec

**Date:** 2026-06-15
**Status:** Draft
**Scope:** Phase 1 (read-only dashboard + recommendation enrichment)

## Overview

Integrate RHDP reporting data (provisions, sales, cost) into RCARS to power a retirement triage dashboard for curators and enrich recommendation cards with usage/cost/sales signals. Data is pulled nightly from the RHDP reporting MCP server and stored locally in RCARS PostgreSQL.

### Goals

1. **Retirement dashboard** — Curator-accessible view under Content Analysis showing all catalog items scored for retirement candidacy, with usage, cost, and sales metrics.
2. **Recommendation card enrichment** — Show provisions count (trailing quarter), cost per provision, and a sales impact badge on recommendation cards for all users.
3. **Browse view enrichment** (nice-to-have) — Show closed and touched sales amounts in the expanded catalog detail for curators.

### Non-Goals (Phase 1)

- Retirement workflow actions (status changes, curator notes on retirement decisions) — backlogged as Phase 2.
- Enhanced retirement scoring (percentile-based, category-aware, trend detection) — backlogged.
- Real-time reporting queries — nightly sync is sufficient.
- Historical data preservation — RCARS stores a rolling window, not a growing history.

## Data Model

### New Table: `reporting_metrics`

One row per catalog base name. Upserted each nightly sync, not appended.

```sql
CREATE TABLE reporting_metrics (
    catalog_base_name  TEXT PRIMARY KEY,    -- e.g. "sandboxes-gpte.sandbox-open"
    display_name       TEXT NOT NULL,
    provisions         INTEGER NOT NULL DEFAULT 0,
    provisions_quarter INTEGER NOT NULL DEFAULT 0,  -- trailing 90 days, for rec cards
    requests           INTEGER NOT NULL DEFAULT 0,
    experiences        INTEGER NOT NULL DEFAULT 0,
    unique_users       INTEGER NOT NULL DEFAULT 0,
    success_ratio      NUMERIC NOT NULL DEFAULT 0,
    failure_ratio      NUMERIC NOT NULL DEFAULT 0,
    touched_amount     NUMERIC NOT NULL DEFAULT 0,
    closed_amount      NUMERIC NOT NULL DEFAULT 0,
    total_cost         NUMERIC NOT NULL DEFAULT 0,
    avg_cost_per_provision NUMERIC NOT NULL DEFAULT 0,
    first_provision    DATE,                -- all-time, no windowing
    last_provision     DATE,                -- all-time, no windowing
    retirement_score   INTEGER NOT NULL DEFAULT 0,  -- 0-100
    synced_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_reporting_metrics_retirement_score ON reporting_metrics (retirement_score DESC);
CREATE INDEX ix_reporting_metrics_display_name ON reporting_metrics (display_name);
```

Delivered via Alembic migration.

### Join Key

RCARS `catalog_items.name` (ci_name) includes the stage suffix: `sandboxes-gpte.sandbox-open.prod`. The reporting DB's `catalog_items.name` is the base without stage: `sandboxes-gpte.sandbox-open`.

**Join logic:** Strip the last `.{stage}` segment from RCARS ci_name to produce `catalog_base_name`. Multiple RCARS ci_names (prod, dev, event) map to the same `reporting_metrics` row — correct, since reporting data aggregates per logical asset.

This is more reliable than joining on `display_name`, which can drift when CIs are renamed.

### Data Retention

- `reporting_metrics` is a rolling snapshot, not a history table. Each nightly sync upserts all values. If the MCP server is unreachable or a query fails, the sync step logs a warning and skips — existing rows are preserved from the previous successful sync. This ensures rec cards and the retirement dashboard continue to render with slightly stale data rather than showing nothing.
- **Provisions window:** Trailing year for retirement dashboard, trailing quarter stored separately in `provisions_quarter` for rec cards.
- **Sales/cost window:** Trailing year (today - 365 days).
- **Dates:** All-time first/last provision (two date fields, not historical).
- **Cleanup:** When catalog refresh removes a CI from `catalog_items`, its corresponding `reporting_metrics` row is also deleted. Orphan cleanup runs as part of the nightly sync.

### No PII

All reporting queries aggregate to counts and sums. No user names, emails, or individually identifiable data is stored in `reporting_metrics`. The SQL queries use `COUNT(DISTINCT p.user_id)` and similar — only integers cross the boundary.

## Nightly Sync Pipeline

New step 5 added to the existing nightly maintenance pipeline in `ops.py`:

```
1. Catalog refresh
2. Stale check
3. Re-analysis
4. Workload scan
5. Reporting metrics sync  ← NEW
```

### Sync Process

1. Check `RCARS_REPORTING_MCP_URL` and `RCARS_REPORTING_MCP_TOKEN`. If either is empty, skip silently with a log message. Reporting sync is optional — RCARS functions without it.
2. Compute date windows:
   - `sales_start` = today - `RCARS_REPORTING_SALES_DAYS` (default 365)
   - `provisions_quarter_start` = today - `RCARS_REPORTING_PROVISIONS_DAYS` (default 90)
3. Execute 5 SQL queries against the MCP server (via `urllib` in `asyncio.to_thread()`):
   - **Provisions (full period):** Provisions, requests, experiences, unique_users, success/failure ratios since `sales_start`, grouped by reporting `catalog_items.name`.
   - **Provisions (quarter):** Provision count only since `provisions_quarter_start`, grouped by reporting `catalog_items.name`.
   - **Sales:** Touched and closed amounts since `sales_start`, with `DISTINCT` on `sales_opportunity.number` to avoid double-counting. Closed = `is_closed = true AND stage IN ('Closed Won', 'Closed Booked')`.
   - **Cost:** Total cost and avg cost per provision since `sales_start`. Uses CTE to aggregate `provision_cost` by `provision_uuid` first, then join to `catalog_items` (avoids timeout on flat 3-way join). Includes `month_ts` filter for partition pruning.
   - **Dates:** All-time first/last provision per `catalog_items.name`. No date filter.
4. Merge all result sets by `catalog_base_name` (reporting `catalog_items.name`).
5. Compute `retirement_score` for each row using ported scoring logic (see Retirement Scoring section).
6. Upsert into `reporting_metrics` via `INSERT ... ON CONFLICT (catalog_base_name) DO UPDATE`.
7. Delete orphan rows: any `reporting_metrics.catalog_base_name` that no longer has a corresponding RCARS `catalog_items` entry.
8. Log summary: rows synced, orphans removed, elapsed time.

### MCP Client

Ported from `build_analysis.py`. Sends JSON-RPC POST requests to the MCP HTTP endpoint. Auto-paginates past the 500-row server cap using CTE wrapping with `ORDER BY 1 LIMIT 500 OFFSET N`. Synchronous `urllib.request` calls wrapped in `asyncio.to_thread()` — same pattern RCARS uses for LLM calls.

### SQL Query Key Changes from build_analysis.py

The existing `build_analysis.py` queries group by `ci.display_name`. The RCARS version groups by `ci.name` (the reporting DB's `catalog_items.name`, which is the AgnosticV base name). This provides a reliable join key back to RCARS.

Example (provisions query):
```sql
SELECT
    ci.name AS catalog_base_name,
    ci.display_name,
    COUNT(DISTINCT p.uuid) AS provisions,
    COUNT(DISTINCT p.request_id) AS requests,
    SUM(p.user_experiences) AS experiences,
    COUNT(DISTINCT p.user_id) AS unique_users,
    ROUND(COUNT(DISTINCT CASE WHEN p.provision_result = 'success' THEN p.uuid END)::numeric
          / NULLIF(COUNT(DISTINCT p.uuid), 0), 4) AS success_ratio,
    ROUND(COUNT(DISTINCT CASE WHEN p.provision_result = 'failure' THEN p.uuid END)::numeric
          / NULLIF(COUNT(DISTINCT p.uuid), 0), 4) AS failure_ratio
FROM provisions p
JOIN catalog_items ci ON ci.id = p.catalog_id
WHERE p.provisioned_at >= :sales_start
GROUP BY ci.name, ci.display_name
```

## Retirement Scoring

Ported from `build_analysis.py` `compute_retirement_score()`. Produces a score from 0-100 where higher = stronger retirement candidate.

### Scoring Signals

| Signal | Condition | Points |
|--------|-----------|--------|
| No prod environment | CI has no prod-stage entry in RCARS | +20 |
| Low provisions | < 60 | +20 |
| Low provisions | 60-119 | +8 |
| Low experiences | < 300 | +10 |
| Low experiences | 300-599 | +4 |
| Low sales touched | < $10M | +15 |
| Low sales touched | $10M-$50M | +6 |
| Low sales closed | < $1M | +20 |
| Low sales closed | $1M-$5M | +8 |
| Poor cost efficiency | ROI < 10x (closed/cost) | +15 |
| Poor cost efficiency | ROI 10x-50x | +5 |
| High cost, zero sales | Cost > $5K and closed = 0 | +15 |
| Recently published | First provision ≤ 90 days ago | -40 |
| Fairly new | First provision ≤ 180 days ago | -15 |

**Maximum possible score:** 100

### Has-Prod Detection

To determine whether a CI has a prod environment, the sync queries RCARS `catalog_items` for all ci_names matching the base name pattern `{base_name}.prod`. If any exist, `has_prod = true`.

### Threshold Tuning Note

These thresholds were developed against a six-month snapshot analysis (e.g., "low provisions < 60" assumes ~10 provisions/month over 6 months). With trailing-year rolling data in production, the absolute numbers will be higher and the thresholds will need recalibration. Port as-is for Phase 1 and tune after observing real data. Enhanced scoring (percentile-based, category-aware) is backlogged as a future improvement.

## API Endpoints

### New: Retirement Dashboard

```
GET /analysis/retirement
```
- **Auth:** require_curator
- **Returns:** Array of reporting metrics joined with RCARS catalog metadata
- **Query params:**
  - `sort_by` (default: `retirement_score`) — retirement_score, provisions, total_cost, closed_amount, touched_amount, display_name
  - `sort_dir` (default: `desc`) — asc, desc
  - `min_score` (optional) — filter to scores ≥ this value
  - `category` (optional) — filter by catalog category
  - `has_prod` (optional, boolean) — filter to items with/without prod stage
  - `search` (optional) — text search on display_name
- **Response includes:**
  - `synced_at` — timestamp of last reporting sync
  - `items` — array of objects, each containing:
    - All `reporting_metrics` fields
    - `category`, `product`, `product_family` from RCARS `catalog_items`
    - `stages` — array of `{stage, catalog_url}` for each RCARS ci_name matching the base name
    - `score_breakdown` — object showing points contributed by each signal

### New: Manual Sync Trigger

```
POST /admin/sync-reporting
```
- **Auth:** require_admin
- **Returns:** `{job_id}` for progress tracking
- **Behavior:** Triggers reporting sync outside the nightly cycle. Same arq job pattern as other admin actions.

### Extended: Single CI Detail

```
GET /catalog/{ci_name}
```
- **Change:** Add `reporting` object to response when metrics exist for the CI's base name.
- **Fields:** provisions, provisions_quarter, experiences, unique_users, total_cost, avg_cost_per_provision, touched_amount, closed_amount, retirement_score, first_provision, last_provision, synced_at

### Extended: Recommendation Results

- **Where:** In the recommend worker, after Phase 2 (triage), before building final results.
- **Graceful degradation:** If `reporting_metrics` has no row for a candidate (sync hasn't run, MCP was down, or CI is new), the candidate renders normally without the metrics line. The rec card never fails or looks broken due to missing reporting data.
- **Change:** Look up `reporting_metrics` for each candidate's base name. Attach to each candidate object:
  - `provisions_quarter` (integer) — trailing quarter provisions
  - `avg_cost_per_provision` (numeric)
  - `sales_impact` (string: "high" / "moderate" / "low" / null) — derived from `closed_amount`

### Sales Impact Tiers

Based on `closed_amount` from the trailing year:

| Tier | Threshold |
|------|-----------|
| High | ≥ $1M closed |
| Moderate | ≥ $100K closed |
| Low | < $100K closed or no data |

Computed by a small utility function, designed for easy future extension to incorporate `touched_amount`. Tooltip text: "Based on closed sales opportunities linked to provisions of this asset over the trailing year."

## Frontend

### Retirement Dashboard Page

**Route:** `/analysis/retirement`
**Component:** `RetirementPage` (new file)
**Nav:** Sibling to "Overlap" under "Content Analysis" in the sidebar

#### Main Row (always visible)

| Column | Format |
|--------|--------|
| Display Name | Linked to Browse detail |
| Retirement Score | Color-coded: red ≥75, amber 50-74, green <50 |
| Provisions | Integer |
| Touched Amount | $X.XM |
| Touched ROI | Xx (touched / cost) |
| Closed Amount | $X.XM |
| Closed ROI | Xx (closed / cost) |
| Total Cost | $X.XK |

#### Expanded Row (click to reveal)

- **Environments:** Clickable stage badges (prod/dev/event/test), each linking to `catalog.demo.redhat.com/catalog?item={namespace}/{ci_name}`
- **Unique Users**
- **Experiences**
- **Cost per Provision**
- **Success / Failure Ratios**
- **First Provision / Last Provision**
- **Score Breakdown:** Which scoring signals contributed how many points

#### Dashboard Header

- Title: "Retirement Analysis"
- Sync timestamp: "Last synced: X hours ago" (from `synced_at`)
- Summary stat bar: Total items, High (≥75), Review (50-74), Keepers (<50), Total cost

#### Filters

- Score threshold buttons: High ≥75 / Review 50-74 / Keepers <50 / All
- Category dropdown
- Has prod toggle
- Text search on display name

#### Interactions

- All numeric columns sortable (click header to sort)
- Row click expands/collapses detail
- Display name click navigates to Browse detail for that CI
- Column layout may be adjusted during implementation — the main/expanded split is directional, not final. If the LCARS theme renders wider than expected, some expanded fields may move to the main row

### Recommendation Card Changes

Add a compact metrics line to each rec card:

- **Provisions:** "X provisions (last 90d)" — from `provisions_quarter`
- **Cost:** "$X.XX / provision" — from `avg_cost_per_provision`
- **Sales Impact:** Small badge (high/moderate/low) with info tooltip on hover

These appear below the existing card content (why_it_fits, how_to_use, etc.).

### Browse Detail Changes (Nice-to-Have)

When `reporting` data is present in the `GET /catalog/{ci_name}` response, show in the expanded detail:

- Touched Amount, Closed Amount
- Provisions, Total Cost

Curator+ only (check role before rendering).

## CLI

Following RCARS's existing CLI patterns. Group under `rcars reporting-db`:

| Command | Purpose |
|---------|---------|
| `rcars reporting-db sync` | Trigger reporting metrics sync manually |
| `rcars reporting-db status` | Show last sync time, row count, score distribution (high/review/keeper) |
| `rcars reporting-db show CI_NAME` | Show reporting metrics for a specific CI (accepts ci_name or base name) |

## Configuration

New Pydantic Settings variables (`RCARS_` prefix):

| Variable | Default | Purpose |
|----------|---------|---------|
| `RCARS_REPORTING_MCP_URL` | `""` | MCP server HTTP endpoint. Empty = sync disabled |
| `RCARS_REPORTING_MCP_TOKEN` | `""` | Bearer token for MCP auth. From Ansible secret |
| `RCARS_REPORTING_PROVISIONS_DAYS` | `90` | Trailing window for rec card provisions (quarter) |
| `RCARS_REPORTING_SALES_DAYS` | `365` | Trailing window for sales, cost, and full provisions |

### Ansible Deployment

Add to `ansible/vars/dev.yml` and `ansible/vars/prod.yml` (both gitignored):
```yaml
rcars_reporting_mcp_url: "{{ vault_reporting_mcp_url }}"
rcars_reporting_mcp_token: "{{ vault_reporting_mcp_token }}"
```

Injected as environment variables on the scan worker pod (the worker that runs the nightly pipeline).

## Alembic Migration

Single migration file: `NNN_reporting_metrics.py` (sequence number determined at implementation time — other migrations may land first from concurrent work).

- Creates `reporting_metrics` table with all columns and indexes
- No data migration needed (table starts empty, populated by first sync)

## Testing

- **Unit tests:** Retirement score computation (port existing thresholds, verify edge cases — new items, zero cost, zero sales, no prod)
- **Unit tests:** Base name extraction from ci_name (strip stage suffix)
- **Integration tests:** MCP query pagination (mock MCP responses, verify >500 row handling)
- **Manual verification:** Deploy to dev, trigger `rcars reporting-db sync`, verify dashboard renders with real data

## Implementation Order

1. Alembic migration + data model
2. MCP client + reporting sync in ops worker
3. Config variables + Ansible vars
4. CLI commands (`reporting-db sync`, `status`, `show`)
5. API endpoints (retirement dashboard, extend catalog detail, extend recommendations)
6. Frontend retirement dashboard page
7. Frontend rec card enrichment
8. Frontend Browse enrichment (nice-to-have)
