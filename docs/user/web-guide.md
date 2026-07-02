---
title: Web UI Guide
description: How to use the RCARS advisor and curator interfaces
---

# Web UI Guide

## Accessing RCARS

RCARS is available to authenticated Red Hat users. Navigate to the deployment URL and log in with your standard Red Hat SSO credentials. RCARS will detect your identity and assign you the appropriate role (viewer, curator, or admin) automatically.

## The Advisor Interface

The main page is the Advisor — a two-pane layout that is always split. The left pane is your conversation with the system. The right pane shows the current recommendation results. Both are present from the moment you load the page.

```
┌──────────────┬────────────────────────────────────────────┐
│  ADVISOR     │  CHAT                  RECOMMENDATIONS      │
│  New Session │                                            │
│  History     │  [welcome message]     [rec card 1]        │
│  ──────────  │                        [rec card 2]        │
│  BROWSE      │  [your message]        [rec card 3]        │
│  Catalog     │  [progress stream]                         │
│  Workloads   │  [response ↩]                              │
│  ──────────  │                                            │
│  ANALYSIS    │  [input box]  [Send]   41/2000             │
│  Overlap     │                                            │
│  Retirement  │                                            │
│  ──────────  │                                            │
│  SYSTEM      │                                            │
│  Status      │                                            │
│  Sync & ...  │                                            │
└──────────────┴────────────────────────────────────────────┘
```

The **RCARS header** shows two currency indicators that tell you how fresh the underlying data is:

- **CATALOG** — when the catalog was last synced from Babylon. Green **CURRENT** means synced within the last three days; red **STALE** means older.
- **ANALYSIS** — when Showroom content was last analyzed. Green **CURRENT** means analyzed within the last three days; red **STALE** means older.

Results are still useful when stale but may not reflect recent catalog additions or content changes.

### Sidebar Navigation

The sidebar is organized into four labeled sections:

- **ADVISOR** — **New Session** starts a fresh advisor conversation. **History** shows your past sessions with saved recommendations.
- **BROWSE** — **Catalog** is the main catalog browser with filtering and curation tools. **Workloads** (curator only) shows infrastructure workload mappings.
- **ANALYSIS** (admin only) — **Overlap** detects duplicate content. **Retirement** provides data-driven retirement scoring.
- **SYSTEM** (admin only) — **Status** shows system health. **Sync & Analysis** runs catalog operations. **Recent Jobs** lists background tasks. **Token Usage** tracks LLM consumption. **Query History** shows advisor sessions.

### Theme Toggle

A light/dark mode toggle is in the top-right corner of the masthead (☽/☀ icon). Your preference is saved to local storage and persists across sessions. RCARS defaults to dark mode.

## Writing a Good Query

RCARS understands natural language. Write what you actually need, not a keyword search. The more context you give, the better the results.

**Examples that work well:**

- *"What demos would work for a 20-minute booth slot at a developer conference focused on Kubernetes and platform engineering?"*
- *"We have a 3-hour hands-on lab slot at an AAP-focused event. The audience is IT operations people, mostly Windows admins moving to Linux. What fits?"*
- *"I need something for a financial services customer who wants to see how Red Hat handles compliance and security in OpenShift."*

**Pasting an event URL:**

You can paste a conference or event URL directly into the chat. RCARS will:

1. Fetch the event landing page and follow links to schedule, program, tracks, and talks pages on the same site
2. Send that content to Claude Sonnet to extract the event's themes, audience, format, and generate targeted search queries
3. Show you what it found (e.g., *Parsed "KubeCon NA" — searching for: Kubernetes platform engineering, cloud-native security, ...*)
4. Run those search queries through the normal recommendation pipeline

You can also combine a URL with text. For example:

- *`https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/`* — URL only, RCARS derives everything from the page
- *"I'm presenting at this event, focus on demos under 30 minutes: https://example.com/conference"* — RCARS fetches the URL for event context and combines it with your text constraints

If the URL cannot be fetched (site down, blocked, etc.), RCARS tells you and suggests describing the event in text instead. If you provided text alongside the URL, it falls through to a normal text search.

For broad multi-track events, use a follow-up message to narrow results to a specific area — for example: *"Focus on platform and infrastructure content"*.

**What makes a query effective:**

- **Audience** — developers, ops, architects, executives, mixed
- **Format** — demo, hands-on lab
- **Duration** — 20 minutes, half-day, 90 minutes
- **Topic or product** — if you already know the focus area
- **Event context** — conference name, industry, theme, or just paste the URL
- **Similar to existing content** — reference a lab number like *"What is similar to LB2144?"* or name an existing item like *"content similar to the Parasol Insurance workshop"*

You do not need all of these. Even a short query like *"OpenShift demos for a developer audience"* returns useful results. More context narrows the ranking.

**If you get no results:** the query may be too specific. Event names, lab numbers, and delivery constraints ("Summit connect", "fill the AI slot") dilute the search. Try simplifying to just the core topic — *"beginner AI hands-on lab"* works better than *"90 minute lab for Summit connect to fill the AI slot, beginner level, not advanced."* If you want to find content similar to a specific item, reference it by lab number (e.g., *"What's similar to LB2144?"*) — RCARS will look up that item and search for neighbors directly.

## Reading Recommendation Cards

Results appear as cards in the right pane, grouped by tier.

**Tiers:**

- **Green — "Best fit"** — strong match with full rationale. These are the top candidates that received detailed analysis from Sonnet.
- **Yellow — "Other options"** — relevant matches that scored well in triage but did not receive full rationale. Shown in a collapsible section.
- **White — "Also reviewed"** — items that were reviewed by the triage phase but scored below the relevance cutoff. Shown in a collapsible section.

Each card shows:

- **Relevance score** — percentage, color-coded by tier
- **Name** — the display name of the catalog item
- **Duration** — estimated duration in minutes (e.g., "~120 min"), shown in the card header
- **Stage badge** — DEV or EVENT badges for non-production items (visible to curators who toggle dev/event stages)
- **CI name** — the internal identifier

For green-tier cards (expanded):

- **Why it fits** — a structured explanation of why this content matches your request
- **How to use** — a practical delivery suggestion
- **Duration pill** — duration with source label: "(AI estimate)" for LLM-guessed durations, "(estimated)" for curator-set durations
- **Suggested format** and **duration notes** — shown as pills
- **Caveats** — anything flagged as a potential concern
- **Learning objectives** — up to 5 objectives from the analysis
- **Catalog link** — direct link to order on `demo.redhat.com`
- **"★ This is the best fit" button** — mark this as your selected recommendation (feedback for future improvement)

Cards appear progressively as the system works through its pipeline. During vector search, candidates appear as a flat list. During triage, they are evaluated and scored. After completion, they are grouped into tiers with full detail on the best matches.

## Expanding a Card

Click on a card's header to expand it. Click the header again to collapse it. Text inside expanded cards can be selected and copied. Green-tier cards show the full rationale (why it fits, how to use, caveats, learning objectives). Yellow and white cards show the triage score and one-line reason.

## Refining Results

You do not need to start a new session to refine your results. Type a follow-up in the input box and send it. RCARS accumulates conversation context — it remembers what you asked before and uses it to refine the recommendations.

Examples of useful follow-ups:

- *"Can you focus on workshops, not demos? This is a full half-day session."*
- *"The audience is more senior. Intermediate to advanced content preferred."*
- *"Nothing with RHEL — this event is purely OpenShift focused."*

**Navigating turns.** When you have multiple recommendation sets from follow-up queries, numbered buttons ("Rec 1", "Rec 2", "Current") appear above the recommendation pane. Click any button to switch between recommendation sets — no new AI call is made, so switching is instant.

## Session History

Click **History** in the sidebar to view your past advisor sessions. The History page shows a scrollable list of sessions on the left with the first query as a label, and the full recommendation results on the right when you select one. Sessions are stored server-side in PostgreSQL, tied to your SSO email — they persist across server restarts and are accessible from any device you log into.

To start a fresh session, click **New Session** in the sidebar. This clears the current conversation and recommendation panes.

## Curator Mode

Curator controls are available in the **Browse page** (not the Advisor page). If your account has curator access (`RCARS_CURATOR_EMAILS_STR`), you will see additional controls on each catalog item in the Browse page.

**What curators can do:**

- **Add/remove tags** — short labels that describe the content. Tags are visible to all users. Examples: `booth-tested`, `kubecon-2026`, `needs-update`, `flagship`.
- **Add notes** — free-text observations visible on the Browse page.
- **Set curated duration** — override the AI-estimated duration with a known value (in minutes). Curated durations are labeled "(estimated)" on rec cards and in Browse; AI guesses are labeled "(AI estimate)". Only curated durations affect duration-based scoring penalties.
- **Flag for review** — marks an item as needing attention. Flagged items appear in the "Needs review" filter.
- **Re-analyze** — trigger a fresh Showroom scan for a single item.
- **Override Showroom URL** — point to a different git repository for Showroom content.
- **Set content path** — override the default Antora content path for a Showroom repository.

Curator changes are saved immediately. Tags can be removed by clicking the X on the tag pill.

**Stage toggles:** Curators see additional toggles on the Advisor page for including `dev` and `event` stage items in recommendations. Non-curator users can toggle `event` items but not `dev`.

## The Browse Page

The Browse page (`/browse`) shows the full catalog in a searchable, filterable list with server-side pagination (50 items per page).

### Primary Bar

- **Text search** — filters by display name or CI name (case-insensitive substring match)
- **Dev toggle** — show/hide dev-stage items
- **Event toggle** — show/hide event-stage items
- **Item count** — total matching items

### Filters Panel

A collapsible "Filters" panel provides multi-dimensional filtering. Active filters appear as removable chips. When collapsed, the active filter chips are shown inline; when expanded, the full dropdowns appear:

- **Cloud Provider** — dropdown of all cloud providers in the catalog (e.g., AWS, Azure, GCP)
- **Workloads** — multi-select dropdown of AgnosticD workload products, grouped by category
- **AgnosticD Config** — dropdown of AgnosticD configuration names

A **Clear all** button removes all active filters at once.

### Curator Filters

Curators see a second collapsible panel ("Curator Filters") with quick-access pills:

- **Unanalyzed** — items not yet scanned by the analysis pipeline
- **Failures** — items whose Showroom scan failed
- **Stale** — items whose Showroom content has changed since the last analysis
- **Needs Review** — items flagged by a curator for review
- **Show Retired** — toggle to include soft-deleted items that have disappeared from Babylon

### Item Badges

Each item in the list shows its display name plus contextual badges:

- **DEV** / **EVENT** — stage badges for non-production items
- **ZT** — zero-tier (namespace starts with `zt-`)
- **v2** — AgnosticD v2 infrastructure
- **FAILED** — Showroom scan failure
- **needs review** — flagged by a curator
- **RETIRED** — soft-deleted item (only visible when "Show Retired" is enabled), shown with the retirement date at reduced opacity

### Expanded Item View

Click an item to expand it. The expanded view shows:

- **Analysis data** — content type, difficulty, duration with source label ("AI estimate" or "estimated")
- **Infrastructure details** (v2 items) — AgnosticD config, cloud provider, OCP version, OS image, worker/control plane instance counts, workloads list
- **Summary text**
- **Products** (purple pills) and **topics** (blue pills)
- **Learning objectives** (stated + inferred)
- **Module list** with per-module topics
- **Links** to RHDP Catalog and Showroom repository
- **Scan errors** (if failed) — error class, message, and failure timestamp
- **Similar Content** — if overlap detection has been run (see Content Analysis below), a panel listing other catalog items with similar Showroom content, ranked by similarity percentage. High overlap (≥85%) is shown in red; related content (75–85%) in amber. Click a similar item's name to search for it in Browse.

**Curator controls** (visible to curators only): add/remove tags, edit notes, set curated duration (minutes), override Showroom URL, set content path with "Set & Scan" button, flag for review, and Re-analyze button.

## Content Analysis

The Content Analysis section is a top-level navigation group in the sidebar, visible to admins only. It contains two sub-pages for analyzing catalog content at scale.

### Content Overlap (`/analysis/overlap`)

The Overlap page helps identify catalog items that teach substantially the same content. This is useful for culling duplicates — for example, two different teams may have independently built separate OpenShift Pipelines labs with 85% topic overlap.

#### Understanding how similarity works

When RCARS scans a Showroom lab, it sends the lab's content to Claude Sonnet, which returns a structured analysis: summary, topics, products, modules, and learning objectives. RCARS then feeds that analysis text into a sentence-transformer model (all-MiniLM-L6-v2), which converts it into a list of 384 numbers called an **embedding**. Think of this as a fingerprint that captures *what the lab is about* — not the exact words used, but the underlying meaning. Two labs about "deploying containerized applications on OpenShift" will get similar fingerprints even if they use completely different wording.

Every analyzed lab in the catalog already has one of these fingerprints stored in the database from its original scan. The overlap detection reuses them — it does not call Claude or any external API. The entire computation runs inside PostgreSQL.

To compare two labs, RCARS uses **cosine similarity**, which measures how closely two fingerprints point in the same direction. Imagine each fingerprint as an arrow in a high-dimensional space. If two arrows point the same way, the angle between them is small and the cosine similarity is close to 1.0 (100%). If they point in unrelated directions, the similarity drops toward 0. In practice:

- **90%+** — the labs cover nearly identical material
- **85–90%** — strong overlap, likely candidates for consolidation
- **75–85%** — related topics with some differentiation
- **Below 75%** — different enough that overlap is not a concern (these pairs are not stored)

The computation compares every lab against every other lab within the selected stage. With ~100 prod labs, that is about 5,000 comparisons — pgvector handles this in under a second.

#### Using the Overlap page

1. Select a **stage** from the dropdown (Production, Event, or Dev).
2. Click **Compute Similarity** to run the comparison. This is fast (seconds) and consumes no LLM tokens.
3. The stats cards show total pairs, high overlap count, and related count.
4. Use the second dropdown to filter between "All pairs" and "High overlap only."
5. Use the **search box** to filter pairs by name.
6. Click any pair to expand it and see both summaries side by side.
7. Click a lab name to navigate to it in Browse for detailed review.

Published Virtual CIs are excluded because they have no Showroom content of their own — they are wrappers that point to a base CI. The comparison happens between the base CIs that own the actual lab content.

**CLI and API access:** Similarity can also be computed via the CLI (`rcars compute-similarity [--stage prod] [--threshold 0.75]`) or the API (`POST /api/v1/admin/compute-similarity?stage=prod`). The overlap report is available at `GET /api/v1/admin/overlap`, and per-item similarity at `GET /api/v1/catalog/{ci_name}/similar`.

**When to recompute:** After a full scan or re-analysis, since the underlying fingerprints may have changed. The "Last computed" timestamp shows when the data was last refreshed.

### Retirement Analysis (`/analysis/retirement`)

The Retirement page helps curators identify catalog items that should be retired based on low usage, weak sales impact, and high cost. It combines data from the RHDP reporting database with RCARS catalog metadata to produce a scored dashboard. For the full technical details of the scoring methodology, data pipeline, and configuration, see the [Retirement Analysis architecture doc](../architecture/retirement-analysis.md).

The page header shows when the reporting data was last synced (e.g., "Last synced: 3h ago").

#### Time Window Selector

The Prod tab has a time window selector that controls how far back the data looks:

- **1 Quarter** — trailing 3 months of activity
- **2 Quarters** — trailing 6 months
- **3 Quarters** — trailing 9 months
- **1 Year** (default) — trailing 12 months

Selecting a shorter window shows how items perform with only recent data. An item that had strong usage last year but zero activity this quarter will score higher (worse) in the 1Q view. Scores are recomputed locally from stored quarterly breakdowns — no re-query to the reporting database is needed.

The total asset count stays constant across all windows — all current catalog items are always shown regardless of their activity in the selected period.

#### Prod Retirements Tab

Shows scored items that have a production deployment. This is the primary triage tool.

**Stat cards** — total assets, high retirement (score ≥55), review (35-54), keepers (<35), total cost, total closed, total touched.

**Filter pills** — All, High ≥55, Review 35-54, Keepers <35.

**Search** — filter by display name.

**Sortable columns** — click any column header to sort:

| Column | Description |
|--------|-------------|
| Name | Display name |
| Score | Retirement score (0-100, higher = stronger retirement candidate) |
| Provisions | Total production provisions in the time window |
| Touched | Total opportunity value linked to provisions |
| T-ROI | Touched-to-cost ratio |
| Closed | Total closed-won revenue |
| C-ROI | Closed-to-cost ratio |
| Cost | Total infrastructure cost (all environments amortized) |

Score badges are color-coded: red (≥55), orange (35-54), green (<35).

**Expanded rows** — click any row to expand and see:

- **Environments** — stage badges (prod/dev/event) that link to Browse. Items without Showroom content in RCARS show a gray "catalog" badge linking to demo.redhat.com instead.
- **Unique Users** — distinct users who provisioned the item
- **Experiences** — total experience count
- **Cost / Provision** — amortized cost per production deployment
- **Success** / **Failure** — provision success and failure ratios as percentages
- **First Provision** / **Last Provision** — date range of activity
- **Category** — the catalog item's category

#### Without Prod Tab

Shows items that only exist in dev and/or event stages — never promoted to production. No time window selector (always shows the trailing year view).

**Stat cards** — total without prod, items > 1 year old (red), 6-12 months (orange), < 6 months (green).

**Age filter pills** — All, > 1 Year, 6-12 Mo, < 6 Mo.

**Search** — filter by display name.

**Table columns** — name, stages, first provision, last provision, provisions, age in days.

**Age color coding** — age > 365 days in red, > 180 days in orange.

**Expanded rows** — click to see: environments (with Browse links), catalog name, unique users, experiences, total cost, and category.

Items more than a year old without a prod deployment are strong candidates for either promotion or retirement.

#### Understanding Retirement Scores

Each item receives a score from 0 to 100. Higher scores indicate stronger retirement candidates. The score combines four dimensions, each scored relative to catalog peers using percentile ranking:

| Component | Max Points | What it measures |
|---|---|---|
| Usage | 25 | Provision count — zero gets max; non-zero ranked by percentile |
| Pipeline | 15 | Touched amount (sales impact) — zero gets max; non-zero by percentile |
| Revenue | 25 | Closed-won amount — zero gets max; non-zero by percentile |
| Cost efficiency | 15 | ROI when both cost and revenue exist; penalty for cost with no revenue |
| Age discount | -30 | New items (<90 days: -30, 90-180 days: -10) get a score reduction |

**Dashboard thresholds:**

| Tier | Score | Meaning |
|---|---|---|
| High Retirement | ≥ 55 | Strong candidates — low/zero activity across multiple dimensions |
| Review | 35–54 | Weak but non-zero activity — worth investigating |
| Keepers | < 35 | Meaningful activity — retain |

## The System Pages

The System section is visible to admins only (not curators). It has five pages accessible via the sidebar: **Status**, **Sync & Analysis**, **Recent Jobs**, **Token Usage**, and **Query History**.

### Status (`/system/status`)

The Status tab shows five summary cards plus the scheduled maintenance panel.

**Catalog card** — total items with prod/dev/event breakdown, items with Showroom, unique Showroom repos, and last sync timestamp with CURRENT/STALE indicator.

**Analysis card** — analyzed count, unanalyzed count (clickable — opens Browse filtered to unanalyzed items), stale count (clickable), failure count (clickable), and last analysis run timestamp.

**Infrastructure card** — AgnosticD v2 item count, items with workloads, mapped roles (total and verified), and unmapped workload count.

**LLM Provider card** — shows which LLM provider is active (LiteMaaS, Vertex AI, or both with fallback). Lists available models and the model assigned to each operation (analysis, triage, rationale, scanning).

**Reporting Sync card** — shows whether reporting data is synced, total assets tracked, counts with provisions/cost/sales data, and last sync timestamp.

**Scheduled Maintenance** — shows the status of the nightly maintenance pipeline (enabled/disabled, schedule time, last run summary with items synced, stale found, and analysis queued). Click **Run Maintenance Now** to trigger an on-demand run. A log window shows real-time progress. To change the schedule, see [Operations — Changing the Schedule](../admin/operations.md#changing-the-schedule).

A **Refresh** button at the top reloads all status cards.

### Sync & Analysis (`/system/sync`)

- **Catalog Sync** — triggers catalog refresh from Babylon CRDs. Retired items that reappear are automatically un-retired.
- **Content Analysis** — two buttons: "Analyze" (scan unanalyzed items) and "Check Stale" (detect changed Showrooms). Shows a live scrolling log with real-time progress.
- **Full Re-Analysis** — "Re-Analyze All" button that marks every item stale and enqueues a complete rescan. Warning: consumes significant tokens.
- **Recent Jobs** — collapsible section showing the last 50 background jobs (scan, analysis, refresh). Auto-refreshes every 10 seconds when expanded. Shows job type, CI name, status (color-coded), timestamps, and duration.

All background operations run in arq workers. You can navigate away and come back — the current state of any running operation is preserved and the live log resumes from where it is.

### Token Usage (`/system/tokens`)

Shows Claude API token consumption broken down by model and operation type.

**Time period selector** — choose from 7, 30, 90, or 365 days.

**Summary table** — one row per model × operation combination:

| Operation | Model | Calls | Input | Output | Total |
|-----------|-------|------:|------:|-------:|------:|
| scan | claude-sonnet-4-6 | 95 | 12.4M | 380K | 12.8M |
| rationale | claude-sonnet-4-6 | 42 | 890K | 168K | 1.1M |
| triage | claude-haiku-4-5 | 42 | 240K | 84K | 324K |
| event_parse | claude-sonnet-4-6 | 8 | 120K | 32K | 152K |

**Recent Queries table** — shows per-query triage and rationale token breakdown with timestamps. For a deeper explanation, see the [Token Usage Tracking](../admin/token-usage.md) doc.

### Query History (`/system/queries`)

Shows recent advisor sessions (last 50). Each session is expandable:

- **Collapsed** — timestamp, first query text, "has selection" badge if a recommendation was chosen
- **Expanded** — per-turn details including query text, overall assessment (truncated), and result list with relevance scores (color-coded by tier), display names, stage badges, and "SELECTED" label for chosen items. Opted-out sessions show a redacted notice.
