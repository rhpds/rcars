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

Reporting data is imported during the nightly maintenance pipeline (step 5 of 5, after catalog refresh → stale check → re-analysis → workload scan). It can also be triggered manually via `rcars reporting-db sync`.

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

When catalog items disappear from the Babylon CRDs during a catalog refresh, RCARS does **not** delete them. Instead, the item's `retired_at` column is set to the current timestamp and `retirement_reason` is recorded. All associated data — Showroom analysis, vector embeddings, workload mappings, reporting metrics, enrichment tags, and curator notes — is preserved.

### How It Works

During every catalog refresh (nightly pipeline Step 1, or manual trigger), RCARS:

1. **Upserts all items** from the current CRD scan. Any item being upserted automatically has its `retired_at` cleared — this is the un-retire path.
2. **Marks missing items** as retired. After all upserts, items in `content_entities` that were NOT in the current scan and don't already have `retired_at` set get `retired_at = NOW()` with reason "Disappeared from Babylon CRDs".
3. **Logs un-retirements.** Items that were previously retired but reappear in the scan are logged with their ci_names for audit visibility.

### Query Filtering

All active-item queries include a `WHERE retired_at IS NULL` condition. This applies to:

- **Browse** — catalog listing hides retired items by default
- **Advisor** — `search_embeddings()` excludes retired items from vector search results
- **Scan pipeline** — `get_items_needing_analysis()` won't queue retired items for analysis
- **Admin stats** — `get_status_summary()` and `get_db_currency()` count only active items (with a separate retired count)
- **Facets** — `get_catalog_facets()` excludes retired items from filter dropdowns
- **Infrastructure search** — `search_by_infrastructure()` only returns active items
- **Content overlap** — `compute_content_similarity()` excludes retired items from pairwise comparison
- **Performance dashboard** — `has_prod` checks and stage lookups filter to active items

The single-item detail view (`get_catalog_item`) intentionally does **not** filter by retirement status — a retired item's full detail page is always accessible via direct URL.

### Browse Integration

The Browse page hides retired items by default. Curators see a **Show Retired** toggle in the curator filter panel. When enabled, retired items appear in the list with an amber "RETIRED" badge showing the retirement date, and the row renders at reduced opacity (60%) to visually distinguish them from active items.

### Interaction with Reporting Data

Fully-retired items (all stage variants soft-deleted) are excluded from the reporting sync and the performance dashboard:

- **Sync exclusion** — `run_reporting_sync()` calls `get_fully_retired_base_names()` and removes those names from the MCP import before computing percentile rankings. This prevents retired items from diluting the scoring pool — a mediocre active item shouldn't look good just because there are retired items with zero activity below it.
- **Dashboard exclusion** — `list_performance_data()` requires at least one active `content_entities` entry (`retired_at IS NULL`) for the base name. A fully-retired item won't appear in either the Prod or Without Prod tab.
- **Orphan cleanup** — since retired items are excluded from the sync, they're not in the synced-names set, and the orphan cleanup removes their `performance_scores` rows. This is intentional: reporting data is always re-derivable from the MCP server, unlike analysis and embeddings which are unique computed data.
- **Partial retirement** — if only the `.prod` variant is retired but `.dev` is still active, the item IS included in the sync and scores normally. It appears in the "Without Prod" tab, correctly reflecting that it's now a dev-only item.

---

## Retirement Workflow

The retirement workflow allows curators to drive the retirement process for low-performing items through a five-step workflow directly in RCARS. The workflow is tracked in the `retirement_workflow` table and culminates in a Jira ticket. Access to the workflow is controlled by curator/admin roles.

### Workflow Steps

1. **Review** (curator) — Initial review step that records who reviewed the item and when. Tracked via `step_reviewed_at/by`.

2. **Approve for Retirement** (curator) — The curator enters a reason for retirement and optionally selects a replacement CI via a searchable catalog dropdown. Clicking "Approve Retirement" freezes the item's current metrics into an `approval_snapshot` JSONB field for later comparison. The snapshot uses the **channel-specific format**: `{channel_name: {score, score_breakdown, provisions, touched, closed, ...}}`. The search supports multi-word queries (e.g., "ansible event" matches items containing both words).

3. **Owner Notified** (curator, optional) — RCARS displays the item's detected maintainers from the Babylon CRD `owners_json.maintainer` field. A "Generate Email Template" button creates a copyable notification message pre-filled with the item name, reason, and key metrics. The curator copies this into Slack or email manually. This step can be skipped.

4. **Start Retirement** (admin only) — Creates a Jira ticket in the selected project (default RHDPCD, auto-uppercased) with retirement details, metrics snapshot, and an AsciiDoc retirement notice template. The Jira description uses wiki markup and includes the target retirement period in days (e.g., "30 days"), the AgnosticV component/item reference, and a catalog search link. Only admins can execute this step — curators see a message indicating admin approval is required.

5. **Retired** (automatic) — Auto-completes when the item disappears from the Babylon CRDs during the nightly catalog refresh. The `retire_removed_items()` function checks for workflow records matching newly-retired base names and sets `step_retired_at`.

### Approval Snapshot Format

The `approval_snapshot` JSONB field stores channel-keyed performance metrics at approval time:

```json
{
  "sales": {
    "score": 18,
    "score_breakdown": {...},
    "provisions": 53,
    "pipeline_touched": 604000,
    "closed_amount": 0,
    "total_cost": 5800,
    "unique_users": 12,
    "completions": 15,
    "page_views": 0
  }
}
```

This allows comparing performance across different channels when the marketing channel is implemented.

### Access Control

- **Curators** can approve items, notify owners, generate email templates, and view all workflow state
- **Admins** can do everything curators can, plus execute "Start Retirement" (Jira creation)
- The "Stop Retirement" button appears in the started step for admins to cancel an in-progress retirement

### Jira Integration

Jira tickets are created via direct REST API v2 calls from the Python backend (`src/api/rcars/services/jira.py`). No MCP tools or LLM involvement — pure HTTP with Basic auth.

The ticket includes:
- **CI Name** — display name from the catalog
- **RHDP URL** — catalog search link on `catalog.demo.redhat.com`
- **AgV** — component/item reference (e.g., `enterprise/event-driven-ansible`). Since Babylon CRDs merge configs from multiple AgnosticV repos, RCARS cannot determine the source repo — only the component/item path is shown.
- **Retirement Notice** — target days (e.g., "30 days")
- **Replacement CI** — catalog search URL if a replacement was selected
- **Metrics snapshot** — frozen values from approval time
- **Suggested adoc template** — AsciiDoc retirement notice block with `[DATE TBD]` placeholder, in a `{code}` block for easy copy

After ticket creation, a clone link is created to the retirement template issue (configurable via `RCARS_JIRA_RETIREMENT_TEMPLATE`).

### Data Model

The `retirement_workflow` table tracks one row per catalog base name:

| Column | Type | Purpose |
|---|---|---|
| `content_id` | TEXT PK | Links to `content_entities` |
| `status` | TEXT | Derived: `approved`, `notified`, `started`, `retired` |
| `step_approved_at/by` | TIMESTAMPTZ, TEXT | When and who approved |
| `approval_reason` | TEXT | Required reason for retirement |
| `approval_snapshot` | JSONB | Frozen metrics at approval time (channel-keyed) |
| `step_notified_at/by` | TIMESTAMPTZ, TEXT | Optional owner notification |
| `step_started_at/by` | TIMESTAMPTZ, TEXT | When Jira was created |
| `retirement_target_date` | DATE | Target retirement date |
| `step_reviewed_at/by` | TIMESTAMPTZ, TEXT | When and who reviewed |
| `step_retired_at` | TIMESTAMPTZ | Auto-set when item disappears |
| `replacement_ci` | TEXT | Base name of replacement item |
| `replacement_name` | TEXT | Display name of replacement |
| `curator_notes` | TEXT | Free-form notes (auto-saves on blur) |
| `jira_key` | TEXT | Created Jira ticket key |
| `jira_project` | TEXT | Jira project (default RHDPCD) |

### Audit Trail

All workflow actions are logged in the `analysis_log` table: `retirement_approved`, `retirement_notified`, `retirement_started` (with Jira key), `retirement_auto_closed`, `retirement_cancelled`.

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

### Dashboard
- `GET /analysis/performance` — performance dashboard with filtering, sorting, search, owner data, channel selection. Response includes `score_breakdown` (per-factor points, levels, reasons, summary), `ignored_until`, and `channel_scores` for each item.

### Mute/Ignore
- `PUT /analysis/performance/ignore/{base_name}` — mute item for 30 days (curator)
- `DELETE /analysis/performance/ignore/{base_name}` — unmute item (curator)

### Workflow
- `GET /analysis/performance/workflow/{base_name}` — get workflow state
- `PUT /analysis/performance/workflow/{base_name}/review` — record initial review (curator)
- `PUT /analysis/performance/workflow/{base_name}/approve` — approve with reason + optional replacement (curator)
- `PUT /analysis/performance/workflow/{base_name}/notify` — mark owner notified (curator)
- `PUT /analysis/performance/workflow/{base_name}/start` — create Jira ticket, start clock (admin only)
- `PUT /analysis/performance/workflow/{base_name}/link-jira` — link an existing Jira ticket to the workflow
- `PUT /analysis/performance/workflow/{base_name}/notes` — update curator notes
- `DELETE /analysis/performance/workflow/{base_name}` — cancel/reset workflow

### Admin
- `POST /admin/sync-reporting` — trigger a reporting sync job
- `GET /admin/reporting-status` — sync status and score distribution
