---
title: Retirement Analysis
description: How RCARS imports reporting data, scores items for retirement, and surfaces results
---

# Retirement Analysis

Retirement analysis helps curators identify catalog items that should be retired based on low usage, weak sales impact, and high cost. It combines data from the RHDP reporting database with RCARS catalog metadata to produce a scored retirement dashboard.

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
| `provision_cost` | Monthly cloud cost breakdowns per provision UUID. |
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

The sync runs six queries against the reporting MCP server, all scoped to **PROD environment** and **real users only** (user groups "Only Regular Users" and "Red Hat Console"):

1. **Provisions** — per catalog item: provision count, request count, experiences, unique users, success/failure ratios. Filtered to trailing year (`reporting_sales_days`, default 365).

2. **Provisions (quarter)** — same as above but filtered to trailing quarter (`reporting_provisions_days`, default 90). Used for trend detection.

3. **Touched amount** — total opportunity value associated with provisions in the trailing year. Joins `provisions_summary → sales_opportunity` using the direct `sales_opportunity_id` FK. Deduplicates by `(opportunity number, catalog item name)` so the same opportunity is counted once per item it's linked to.

4. **Closed amount** — sum of closed-won opportunity amounts where `closed_at` falls within the trailing year. Unlike touched, this filters by the opportunity's **close date**, not the provision date. A deal demoed 18 months ago but closed 3 months ago appears in closed but not in touched — these are intentionally different metrics answering different questions.

5. **Cost** — total cloud infrastructure cost from `provision_cost`, filtered to the trailing year by `month_ts`.

6. **Dates** — first and last provision dates across all time (no date filter), used for age calculations.

### Exclusions

Test and infrastructure items are excluded before scoring:

```
tests.*              — test harnesses and empty configs
clusterplatform.*    — IT cluster platform infrastructure
resourcehub.*        — IT resource hub mirrors
```

These items would pollute the retirement dashboard with non-content entries.

### Join Key

RCARS joins reporting data to its catalog using `catalog_items.name` in the reporting database, which maps to the base name of RCARS ci_names (e.g., `sandboxes-gpte.sandbox-ocp` in the reporting DB corresponds to `sandboxes-gpte.sandbox-ocp.prod`, `.dev`, `.event` in RCARS). The `extract_base_name()` function strips stage suffixes for matching.

### Storage

Merged data is stored in the `reporting_metrics` table (one row per catalog base name) with an `ON CONFLICT ... DO UPDATE` upsert. Orphan rows (base names no longer in the reporting data) are deleted after each sync.

---

## Retirement Scoring

Each item receives a retirement score from 0 to 100. Higher scores indicate stronger retirement candidates. The score is computed using **percentile-based ranking** — each item is scored relative to its catalog peers, not against fixed dollar thresholds.

### Scoring Components

| Component | Max Points | Method |
|---|---|---|
| **Usage** | 20 | Provisions percentile among all items |
| **Pipeline** | 15 | Touched amount — zero gets max points; non-zero ranked by percentile |
| **Revenue** | 25 | Closed amount — zero gets max points; non-zero ranked by percentile |
| **Cost efficiency** | 15 | ROI (closed ÷ cost) — poor ROI or high cost with zero revenue |
| **Age discount** | -40 | Items less than 90 days old get a score reduction |

**Maximum score: 75** (before age discount). No item automatically hits 85+ just for having low activity — the score differentiates based on where each item falls relative to its peers.

### Percentile Breakdown

| Percentile | Usage points | Pipeline points (non-zero) | Revenue points (non-zero) |
|---|---|---|---|
| p0–p10 | 20 | — | — |
| p10–p25 | 15 | — | — |
| Below p50 | 8 | 10 | 15 |
| p50–p75 | 3 | 4 | 5 |
| p75+ | 0 | 0 | 0 |

Items with **zero** touched amount receive the full 15 pipeline points regardless of percentile. Items with **zero** closed amount receive the full 25 revenue points. This reflects that having no sales attribution is a stronger retirement signal than having low sales.

### Why Percentile-Based

Fixed thresholds (e.g., "closed < $1M → retirement candidate") fail when the data distribution changes. When RCARS switched from 6-month to trailing-year data and corrected the query methodology, the dollar amounts shifted significantly. Percentile-based scoring adapts automatically — the bottom 10% is always the bottom 10%, regardless of whether the dollar values doubled.

### What's Not Scored

**Production presence** is not a scoring factor. Items without a prod deployment are handled separately in the "Without Prod" tab (see below). Scoring only the items that have prod ensures the percentile ranks reflect meaningful peer comparison among items that are actually in production.

---

## Dashboard — Two Views

The retirement dashboard at `/analysis/retirement` is split into two tabs serving different purposes.

### Prod Retirements Tab

Shows scored items that have a production deployment. This is the primary triage tool.

- **Stat cards** — total assets, high retirement (score ≥75), review (50-74), keepers (<50), total cost, total closed, total touched
- **Filter pills** — All, High ≥75, Review 50-74, Keepers <50
- **Search** — filter by display name
- **Sortable table** — name, score, provisions, touched, T-ROI, closed, C-ROI, cost
- **Expandable rows** — environments (with links to Browse), unique users, experiences, cost/provision, success/failure ratio, first/last provision, category

### Without Prod Tab

Shows items that only exist in dev and/or event stages — never promoted to production. These items wouldn't appear in the prod tab but still need visibility to prevent them from being forgotten.

- **Stat cards** — total without prod, items >1 year old (red), 6-12 months (orange), <6 months (green)
- **Table** — name, stages, first provision, last provision, provisions, age in days
- **Color coding** — age >365 days in red, >180 days in orange

Items more than a year old without a prod deployment are strong candidates for either promotion or retirement.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `RCARS_REPORTING_MCP_URL` | — | MCP server HTTPS endpoint |
| `RCARS_REPORTING_MCP_TOKEN` | — | Bearer token (K8s Secret) |
| `RCARS_REPORTING_SALES_DAYS` | 365 | Trailing window for provisions, touched, cost |
| `RCARS_REPORTING_PROVISIONS_DAYS` | 90 | Trailing window for quarter provisions |

---

## CLI

```bash
rcars reporting-db sync      # Pull data from MCP, compute scores, upsert
rcars reporting-db status     # Show sync status and row counts
rcars reporting-db show NAME  # Show metrics for a specific catalog base name
```

## API

- `GET /analysis/retirement` — retirement dashboard with filtering, sorting, search
- `POST /admin/sync-reporting` — trigger a reporting sync job
- `GET /admin/reporting-status` — sync status and score distribution
