---
title: Performance Analysis
description: How RCARS imports reporting data, scores items for performance, and surfaces results
---

# Performance Analysis

Performance analysis helps curators understand catalog item impact based on usage, sales performance, and cost efficiency. It combines data from the RHDP reporting database with RCARS catalog metadata to produce a scored performance dashboard. Higher scores indicate better-performing items.

## Access Model

The Performance page is public by default (`RCARS_PERFORMANCE_PUBLIC=true`), allowing all authenticated users to view performance data. Curators see additional features: item muting, retirement workflow access, and expanded metrics. To restrict the page to curators only, set `RCARS_PERFORMANCE_PUBLIC=false`. When restricting page access, also configure `RCARS_CHAT_INTENT_ROLES=performance:curator` so chat performance answers match page access.

## Data Source — RHDP Reporting Database

RCARS does not generate usage or sales data. It pulls this data from the RHDP reporting database via an MCP (Model Context Protocol) server. The reporting database is the same source that powers the SuperSet "Demo Platform Overview" dashboard used by RHDP management.

### The Reporting MCP Server

The reporting MCP server exposes a SQL query tool over JSON-RPC. RCARS connects to it using:

- `RCARS_REPORTING_MCP_URL` — the HTTPS endpoint (e.g., `https://reporting-mcp.apps.example.com/mcp/`)
- `RCARS_REPORTING_MCP_TOKEN` — a bearer token stored as a Kubernetes Secret (`rcars-reporting-mcp`)

The MCP server caps responses at 500 rows. RCARS auto-paginates by wrapping queries in a CTE with `LIMIT/OFFSET`, up to 50 pages (25,000 rows maximum).

### Key Tables in the Reporting Database

RCARS queries three tables and one materialized view:

| Table | Purpose |
|---|---|
| `provisions_summary` | Materialized view of all provisions with pre-joined user, department, and cost data. This is the authoritative source — the same view the SuperSet dashboard queries. Contains `asset_name`, `sales_opportunity_id`, environment, user group, and provision dates. |
| `sales_opportunity` | Sales opportunities linked to provisions. Contains opportunity number, amount, close date, stage (Closed Won/Closed Booked), and account information. |
| `provision_cost` | Monthly cloud infrastructure cost breakdowns per provision UUID. |
| `catalog_items` | Catalog item metadata in the reporting DB (name, display name, ID). Used to join provisions back to RCARS catalog items via `catalog_id`. |

### Why `provisions_summary` Instead of `provisions`

The raw `provisions` table has ~1.49M rows and includes internal test provisions, duplicate entries, and differently-linked sales opportunities. The `provisions_summary` materialized view (~1.47M rows) is the curated version used by all official RHDP reports. Key differences:

- Pre-joins user hierarchy, department, and chargeback data
- Includes computed columns like `provision_success`/`provision_failure` counts
- Has `asset_name` (display name) and `order_channel` pre-resolved
- Sales opportunity linkage matches what SuperSet uses

Using the raw `provisions` table instead of `provisions_summary` produced ~5x inflated touched amounts for some items (e.g., RHADS showed $1.1B instead of $213M) due to different opportunity linkage in the `provision_sales` intermediary table.

---

## Data Import — Nightly Sync

Reporting data is imported during the nightly maintenance pipeline (step 5 of the Babylon pipeline, after catalog refresh → stale check → re-analysis → workload scan). The reporting sync also pulls [field source content provisions](field-source-content.md) as a sub-step (5b). It can also be triggered manually via `rcars reporting-db sync`.

### What Gets Queried

The sync runs ten queries against the reporting MCP server. Usage, sales, and date queries are scoped to **PROD environment** and **real users only** (user groups "Only Regular Users" and "Red Hat Console"). Cost queries intentionally include **all environments** (see Cost Methodology below).

1. **Provisions** — per catalog item: provision count, request count, completions, unique users, success/failure ratios. Filtered to trailing year (`reporting_sales_days`, default 365). PROD + real users only.

2. **Provisions (quarter)** — same as above but filtered to trailing quarter (`reporting_provisions_days`, default 90). Used for trend detection.

3. **Touched amount** — total opportunity value associated with provisions in the trailing year. Joins `provisions_summary → sales_opportunity` using the direct `sales_opportunity_id` FK. Deduplicates by `(opportunity number, catalog item name)` so the same opportunity is counted once per item it's linked to. PROD + real users only.

4. **Closed amount** — sum of closed-won opportunity amounts where `closed_at` falls within the trailing year. Unlike touched, this filters by the opportunity's **close date**, not the provision date. A deal demoed 18 months ago but closed 3 months ago appears in closed but not in touched — these are intentionally different metrics answering different questions. PROD + real users only.

5. **Cost** — total cloud infrastructure cost from `provision_cost`, filtered to the trailing year by `month_ts`. Includes **all environments** (prod, dev, event) — see Cost Methodology below.

6. **Dates** — first and last provision dates across all time (no date filter), used for age calculations. PROD + real users only.

7-10. **Quarterly breakdowns** — provisions, touched, closed, and cost broken down by calendar quarter (`YYYY-QN` format). Same filters as the corresponding total queries. Stored as JSONB in `quarterly_data` for the time window feature.

### Cost Methodology

Cost is calculated differently from the other metrics: it includes **all environments** (dev, event, and prod), not just production. The total cost is then divided by the number of **production provisions only** to produce the cost per provision.

This amortization means that development and event infrastructure costs are baked into each production deployment. An item that costs $500/year in dev testing and $200/year in prod across 100 prod provisions shows a cost per provision of $7.00, not $2.00. This reflects the true total cost of maintaining an item in the catalog — if an item is retired, all its dev and event environments go away too.

### Catalog Backfill

After importing reporting data, the sync queries the local `content_entities` table (joined with `babylon_items`) for all unique base names. Items that exist in the current catalog but have no reporting data (never provisioned by a PROD real user) are backfilled into `performance_scores` with zero values. These items score low on the performance scale (zero provisions + zero sales = low performance).

This ensures the performance dashboard covers the entire current catalog — `Prod Items + Without Prod = total unique catalog items`.

### Exclusions

Test and infrastructure items are excluded before scoring:

```
tests.*              — test harnesses and empty configs
clusterplatform.*    — IT cluster platform infrastructure
resourcehub.*        — IT resource hub mirrors
```

These items would pollute the performance dashboard with non-content entries.

### Join Key

RCARS joins reporting data to its catalog using `catalog_items.name` in the reporting database, which maps to the base name of RCARS ci_names (e.g., `sandboxes-gpte.sandbox-ocp` in the reporting DB corresponds to `sandboxes-gpte.sandbox-ocp.prod`, `.dev`, `.event` in RCARS). The `extract_base_name()` function strips stage suffixes for matching.

### Storage

Merged data is stored in the `performance_channels` and `performance_scores` tables (one set of rows per content entity) with an `ON CONFLICT ... DO UPDATE` upsert. The `windowed_metrics` JSONB column on `performance_scores` stores pre-computed metrics for each time window (3m, 6m, 9m, 12m), including the `score_breakdown` dict with per-factor points, levels, and reasons. The `ignored_until` DATE column tracks muted items. After upsert, orphan cleanup removes items not in the current sync batch AND items no longer in the local `content_entities` table.

---

## Performance Channels

Performance data is tracked in two channels, each representing a distinct data source:

| Channel | Source | Description |
|---|---|---|
| `sales` | `rhdp` | Sales-driven metrics from RHDP reporting DB (provisions, touched, closed, cost). Primary channel, fully implemented. |
| `marketing` | `interactive_labs` | Marketing-driven metrics from interactive.labs.redhat.com usage tracking. Backlogged (RHDPCD-629). |

The `CHANNEL_SOURCES` mapping in `reporting_sync.py` defines this relationship. Channel-specific scores are stored in the `channel_scores` JSONB column on `performance_scores`, keyed by channel name. The default channel is `sales`.

### S/M Data Tags

Items appear on the performance dashboard with data source tags:

- **S** (Sales) — has `sales` channel data
- **M** (Marketing) — has `marketing` channel data
- **S+M** — has both channels
- No tag — item exists in catalog but has no performance data from any channel

---

## Performance Scoring

Each item receives a performance score from 0 to 100. **Higher scores indicate better-performing items.** The score is computed using **percentile-based ranking** — each item is scored relative to its catalog peers, not against fixed dollar thresholds.

The theoretical maximum score is approximately **80 points** across the four scoring components. The scale goes to 100, but reaching 85 requires an item to have strong provisions, strong pipeline, strong revenue, and excellent cost efficiency. In practice, most items score between 10 and 70. The headroom above 80 accommodates future scoring dimensions (e.g., failure rate, trend detection).

### Scoring Components

| Component | Max Points | Method |
|---|---|---|
| **Usage** | 25 | Zero provisions gets 0 points; non-zero ranked by percentile among non-zero peers (inverted tiers: 0, 3, 7, 15, 22, 25) |
| **Pipeline** | 15 | Touched amount — zero gets 0 points; non-zero ranked by percentile (inverted tiers: 0, 5, 11, 15) |
| **Revenue** | 25 | Closed amount — zero gets 0 points; non-zero ranked by percentile (inverted tiers: 0, 10, 20, 25) |
| **Cost efficiency** | 15 | Continuous percentile-scaled ROI: `round(15 × percentile/100)`. Produces smooth 0–15 values. Zero revenue with any cost always gets 0. |

**Note:** Unlike the old retirement scoring, there is **no age discount**. All items are scored equally regardless of age.

### Percentile Breakdown

All three main dimensions use the same pattern: zero-value items receive zero points (they have no activity to measure), then percentile ranking among non-zero peers only. Percentiles are computed against non-zero items to prevent the large population of zero-activity items from diluting the rankings.

The top percentile brackets are compressed toward the maximum score to reward high performers — an item in the top 5% should score near the maximum.

| Percentile | Usage points | Pipeline points (non-zero) | Revenue points (non-zero) |
|---|---|---|---|
| Zero value | 0 | 0 | 0 |
| p0–p10 | 3 | 5 | 10 |
| p10–p25 | 7 | — | — |
| p25–p50 | 15 | 11 | 20 |
| p50–p75 | 22 | — | — |
| p75+ | 25 | 15 | 25 |

### Cost Efficiency Scoring

Cost efficiency uses **continuous percentile-scaled scoring** rather than fixed ROI thresholds. This produces a smooth distribution of 0–15 points across all items with ROI data, instead of clustering items into a few coarse buckets.

For items with both cost and closed revenue, ROI is computed as `closed_amount / total_cost`, then ranked against all other items that also have ROI. The formula is `points = round(15 × percentile / 100)`:

| Percentile | Points | Meaning |
|---|---|---|
| p90 (top 10%) | 14 | Strong return — among the best ROI in the catalog |
| p75 (top 25%) | 12 | Good return |
| p50 (median) | 8 | Average return |
| p25 (bottom 25%) | 4 | Below-average return |
| p10 (bottom 10%) | 2 | Poor return — among the worst ROI |

Items with zero closed revenue but non-zero cost always receive 0 points — spending money with no closed deals shows no return on investment. Items with no cost data receive 0 points.

### Dashboard Thresholds

| Tier | Score Range | Meaning |
|---|---|---|
| **Strong** | ≥ 55 | Strong performers — meaningful activity across multiple dimensions |
| **Moderate** | 35–54 | Moderate activity — steady but not standout |
| **Low** | < 35 | Low/zero activity — may be niche, new, or candidates for review |

### Score Breakdown

Each score includes a `score_breakdown` dict with:

- **`summary`** — one-line explanation (e.g., "Strong usage and sales with solid pipeline")
- **`factors`** — per-factor dicts with:
  - `points` — points awarded (e.g., 22)
  - `max_points` — maximum possible (e.g., 25)
  - `level` — `none` / `low` / `moderate` / `strong`
  - `reason` — plain-English explanation with actual values and percentile context (e.g., "6,106 provisions — top tier (percentile 95 of items with activity)")

The breakdown appears in a popover when clicking a score badge in the UI.

### Scoring Examples

To illustrate how percentile scoring works in practice, here are three hypothetical catalog items scored against the same peer set:

**Example 1: "AWS with OpenShift Open Environment"** — a heavily used sandbox

| Metric | Value | Percentile | Points |
|---|---|---|---|
| Provisions | 6,106 | p95 (top 5%) | 25 |
| Touched | $1.28B | p99 | 15 |
| Closed | $104M | p98 | 25 |
| Cost | $686K, ROI = 151x | p92 (top 10%) | 14 |

**Score: 79** — this item is in the top percentile on every dimension. It drives massive revenue relative to its cost. Clear strong performer.

**Example 2: "Day in the Life Camel"** — a niche demo with low usage

| Metric | Value | Percentile | Points |
|---|---|---|---|
| Provisions | 53 | p18 (bottom 20%) | 7 |
| Touched | $604K | p58 (non-zero) | 11 |
| Closed | $0 | zero | 0 |
| Cost | $5.8K, zero closed | zero revenue, has cost | 0 |

**Score: 18** — low provisions, zero closed revenue, and costs $5.8K/year with no return. The touched amount shows some pipeline activity, but overall performance is weak.

**Example 3: "RHEL Image Mode Workshop"** — a new item, 4 months old

| Metric | Value | Percentile | Points |
|---|---|---|---|
| Provisions | 280 | p42 | 15 |
| Touched | $0 | zero | 0 |
| Closed | $0 | zero | 0 |
| Cost | $12K, zero closed | zero revenue, has cost | 0 |

**Score: 15** — moderate provisions but zero sales data. As a new item (4 months old), it may not have had time to build a sales track record yet. The score accurately reflects current performance without age-based penalties.

### Why Percentile-Based

Fixed thresholds (e.g., "closed > $1M → strong performer") fail when the data distribution changes. When RCARS switched from 6-month to trailing-year data and corrected the query methodology, the dollar amounts shifted significantly. Percentile-based scoring adapts automatically — the top 10% is always the top 10%, regardless of whether the dollar values doubled.

### What's Not Scored

**Production presence** is not a scoring factor. Items without a prod deployment are handled separately in the "Without Prod" tab (see below). Scoring only the items that have prod ensures the percentile ranks reflect meaningful peer comparison among items that are actually in production.

---

## Time Windows

The performance dashboard supports four time windows, each pulling from pre-computed metrics in the `windowed_metrics` JSONB column:

| Window | Description |
|---|---|
| `3m` | 3 months (1 quarter) — recent activity only |
| `6m` | 6 months (2 quarters) |
| `9m` | 9 months (3 quarters) |
| `12m` | 12 months (1 year) — **default** |

Selecting a window recomputes scores fresh from quarterly breakdowns stored during sync. Shorter windows show how items perform with only recent data — an item that had strong usage last year but zero activity this quarter will score lower (worse) in the 3m view.

Scores are recomputed fresh for each window: quarterly values are summed, new percentile rankings are calculated, and scores are assigned. This is a local computation (no MCP re-query), sub-millisecond for the full catalog.

The total asset count stays constant across all windows — all current catalog items are always shown regardless of their activity in the selected period. Items with zero activity in the window receive low scores, reflecting current performance accurately.

---

## Soft-Delete — Preserving Retired Items

Catalog preservation and the distinction between workflow completion and catalog visibility are documented in [Retirement System — Catalog Soft-Delete](retirement-system.md#catalog-soft-delete). A merged removal PR can complete a workflow before Babylon sync removes the item from active catalog views.

For performance analysis, fully retired base names are excluded from normal reporting imports. Derived performance rows may be cleaned up, while the workflow's approval snapshot preserves the evidence used for the retirement decision. If another stage remains active, the item can still appear in performance or non-production views. A reporting refresh is not an immutable archive of past metrics.

---

## Retirement Workflow

Performance is a decision input, not an automated retirement approval. Curators can recommend an item from its metrics; admins handle notification, Jira, and catalog-change PR actions. The shared drawer is also used by the Non-Prod Items and Retirement pages.

The complete lifecycle, role matrix, snapshots, Jira/AgV integration, sweeps, cancellation, reporting, and API contract now live in [Retirement System](retirement-system.md). This page remains the reference for performance imports, scoring, time windows, and muting. Muting suppresses performance review noise; it does not retire an item or cancel a workflow.

---

## Dashboard — Two Views

The performance dashboard at `/analysis/performance` is split into two tabs. Together they cover the **entire active catalog** — Prod total + Without Prod total = total unique active catalog items.

### Prod Performance Tab

Shows scored items that have a production deployment. This is the primary performance review tool.

- **Time window selector** — 3m / 6m / 9m / 12m (default 12m). Recomputes scores from quarterly breakdowns.
- **Channel selector** — Sales / Marketing (when implemented). Filters to items with data for the selected channel.
- **Stat cards** — total items, strong (score ≥55), moderate (35-54), low (<35), total cost, total closed, total touched. Muted items are excluded from all counts.
- **Score filter** — All, Strong ≥55, Moderate 35-54, Low <35
- **Status filter** — All, No Action, In Process, Started, Muted. The "Muted" filter shows only muted items; all other filters exclude them.
- **Search** — filter by display name
- **Sortable table** — name, score, provisions, touched, T-ROI, closed, C-ROI, cost, data source tag (S/M/S+M)
- **Score breakdown popover** — clicking a score badge opens a popover explaining why the score is what it is. Shows a one-line summary (e.g., "Strong usage and sales with solid pipeline"), then per-factor breakdowns with points, progress bars, and plain-English reasons including actual values and percentile rankings (e.g., "6,106 provisions — top tier (percentile 95 of items with activity)"). Click anywhere outside or on the badge again to dismiss.
- **Expandable rows** — environments (with links to Browse for items with Showroom content, or to demo.redhat.com catalog for items without), unique users, completions, cost/provision, success/failure ratio, first/last provision, category, and action buttons
- **Mute button** — "Mute 30d" in the expanded row marks an item as ignored for 30 days. Muted items appear at reduced opacity with a "muted" badge when viewing via the Muted status filter. Click "Unmute" to remove the mute early. Useful for infrastructure items (e.g., shared pool clusters) whose usage is reflected in other items.
- Items without Showroom content in RCARS show a gray "catalog" badge instead of colored stage badges

### Without Prod Tab

Shows items that only exist in dev and/or event stages — never promoted to production. No time window selector (always shows the trailing year view). No channel selector (shows combined data across all channels).

- **Stat cards** — total without prod, items >1 year old (amber), 6-12 months (blue), <6 months (green)
- **Table** — name, stages, first provision, last provision, provisions, age in days (not sortable — server-determined order)
- **Color coding** — age >365 days in amber, >180 days in blue

Items more than a year old without a prod deployment are strong candidates for either promotion or retirement.

---

## URL State

The dashboard supports URL parameters for deep linking and state preservation:

| Parameter | Values | Default | Description |
|---|---|---|
| `tab` | `prod`, `without-prod` | `prod` | Active tab |
| `window` | `3m`, `6m`, `9m`, `12m` | `12m` | Time window (Prod tab only) |
| `channel` | `sales`, `marketing` | `sales` | Performance channel (Prod tab only) |
| `score_filter` | `all`, `strong`, `moderate`, `low` | `all` | Score tier filter |
| `status_filter` | `all`, `no_action`, `in_process`, `started`, `muted` | `all` | Workflow status filter |
| `search` | string | — | Display name search query |

URL state updates on every filter/tab change and is read on page load to restore the previous view.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `RCARS_PERFORMANCE_PUBLIC` | `true` | Make Performance page public to all authenticated users. Set `false` to restrict to curators. |
| `RCARS_REPORTING_MCP_URL` | — | MCP server HTTPS endpoint |
| `RCARS_REPORTING_MCP_TOKEN` | — | Bearer token (K8s Secret) |
| `RCARS_REPORTING_SALES_DAYS` | 365 | Trailing window for provisions, touched, cost |
| `RCARS_REPORTING_PROVISIONS_DAYS` | 90 | Trailing window for quarter provisions |

When setting `RCARS_PERFORMANCE_PUBLIC=false`, also configure `RCARS_CHAT_INTENT_ROLES=performance:curator` so chat performance answers match page access.

---

## CLI

```bash
rcars reporting-db sync      # Pull data from MCP, compute scores, upsert
rcars reporting-db status     # Show sync status and score distribution
rcars reporting-db show NAME  # Show metrics for a specific catalog base name
```

## API

See [Swagger UI](api-reference.md#interactive-api-documentation) for **Performance** operations and **Administration** reporting-sync operations, including filters, schemas, and access requirements. Retirement has its own **Retirement** group; its lifecycle is described in [Retirement System](retirement-system.md).
