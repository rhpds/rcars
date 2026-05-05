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
│  Navigation  │  CONVERSATION          RECOMMENDATIONS      │
│  ──────────  │                                            │
│  💬 Advisor  │  [welcome message]     [rec card 1]        │
│  🏷 Curate   │                        [rec card 2]        │
│  ⚙ Admin     │  [your message]        [rec card 3]        │
│  ──────────  │  [response ↩]                              │
│  HISTORY     │  [input box]  [Send]                       │
│  …           │                                            │
└──────────────┴────────────────────────────────────────────┘
```

The **RCARS logo** in the header shows a currency badge that tells you how fresh the underlying catalog data is. A green **● CURRENT** badge means the catalog was synced within the last three days. A red **● STALE** badge means the data is older than that — results are still useful but may not reflect the most recent catalog additions.

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
- **Format** — booth demo, hands-on lab, presentation support
- **Duration** — 20 minutes, half-day, 90 minutes
- **Topic or product** — if you already know the focus area
- **Event context** — conference name, industry, theme, or just paste the URL

You do not need all of these. Even a short query like *"OpenShift demos for a developer audience"* returns useful results. More context narrows the ranking.

## Reading Recommendation Cards

Each result appears as a card in the right pane. Cards are ranked by fit score.

**Score colors:**

- Green (80–100%) — strong match
- Amber (50–79%) — reasonable fit with caveats
- Red (below 50%) — included because it's the closest available, but not ideal

Each card shows:

- **Score** — the fit percentage, color-coded green/amber/red
- **Name** — the display name of the catalog item
- **Metadata pills** — content type (workshop, demo), suggested format, difficulty, and estimated duration
- **Why it fits** — a structured explanation of why this content matches your request, focused on topic alignment and learning outcomes
- **How to use** — a practical delivery suggestion (e.g., "Run modules 1-4 as a live session, assign module 5 as self-paced follow-up")
- **Tags** — any curator-applied labels that add context beyond the AI analysis

Cards appear progressively as the system works through its pipeline. Initial candidates appear quickly with basic information, then the detailed analysis fills in once the AI completes its evaluation.

## Expanding a Card

Click anywhere on a card to expand it. The expanded view adds:

- **CI Name** — the internal identifier (useful when ordering through the catalog)
- **Duration notes** — timing adaptation suggestions
- **Caveats** — anything the system flags as a potential concern relevant to your request
- **Curator notes** — any notes curators have added
- **Catalog link** — a direct link to order the demo on `catalog.demo.redhat.com`

Click the card again to collapse it.

## Refining Results

You do not need to start a new session to refine your results. Type a follow-up in the input box and send it. RCARS accumulates conversation context — it remembers what you asked before and uses it to refine the recommendations.

Examples of useful follow-ups:

- *"Can you focus on workshops, not demos? This is a full half-day session."*
- *"The audience is more senior. Intermediate to advanced content preferred."*
- *"Nothing with RHEL — this event is purely OpenShift focused."*

**Rolling back.** If a previous response produced better results than the current one, click on that earlier assistant response in the conversation pane. RCARS will restore the recommendation set from that moment — no new AI call is made, so it's instant.

## Conversation History

The left sidebar shows your recent sessions. Labels are generated from the first message in each conversation. Sessions are stored server-side in PostgreSQL, tied to your SSO email — they persist across server restarts and are accessible from any device you log into.

To start a fresh session, click **+ New session** (visible at the bottom of the recommendations pane).

## Curator Mode

If your account has curator access, you will see a curator mode toggle in the top navigation. When activated, expanded recommendation cards show additional controls.

**What curators can do:**

- **Add tags** — short labels that describe the content in ways the AI analysis may miss. Tags appear on cards for all users. Examples: `booth-tested`, `aws-event`, `needs-update`, `flagship`.
- **Add notes** — longer free-text observations visible only to other curators in the Curate page.
- **Flag for review** — marks an item with ⚑ to indicate it needs attention. Flagged items appear in the Curate page's needs-review filter.

Curator changes are saved immediately when submitted. Tags can be removed from the Curate page.

## The Browse Page (with Curator Controls)

The Browse page (`/browse`) shows the full catalog in a paginated list. The default filter shows only items with Showroom content. Use the filter bar to search by name, or switch between "Has Showroom", "All items", "Needs review", and "Untagged" views.

For users with curator access, each item on the Browse page shows inline curation controls: add/remove tags, edit notes, flag or unflag, and a **Re-analyze** button that triggers an individual Showroom scan. This is the right place to do bulk enrichment work, not something you'd use during an event conversation.

## The Admin Pages

The Admin section (`/admin`) is visible to curators and admins. It is split into four sub-pages, accessible via tabs:

### Catalog (`/admin/catalog`)

- **Scheduled Maintenance** — shows the status of the nightly maintenance pipeline (enabled/disabled, schedule time, last run summary). The pipeline runs automatically at the configured time (default 04:00 UTC) and chains three steps in sequence: catalog refresh, stale check, and enqueue re-analysis. The last-run summary shows how many items were synced, how many were found stale, and how many were queued for re-analysis. Note: "queued for re-analysis" means the analysis jobs were placed on the worker queue — they are processed afterward by the scan worker through its normal job loop, not within the pipeline itself. Click **Run Maintenance Now** to trigger an on-demand run. The log window shows real-time progress through all three steps. To change the schedule, see [Worker Management — Changing the Schedule](workers.md#changing-the-schedule).
- **Catalog Status** — total items, production items, scannable Showrooms (excluding published CIs), analyzed count, and stale count
- **Catalog Sync** — triggers `rcars refresh` to pull the latest catalog metadata from Babylon
- **Showroom Analysis** — triggers `rcars scan` to analyze unscanned and stale items. Shows a live scrolling log of the scan progress.
- **Content Updates** — triggers `rcars check-stale` to detect which analyzed Showrooms have changed since the last scan. Items with content changes are marked stale and picked up by the next scan.

All background operations run in arq workers. You can navigate away and come back — the current state of any running operation is preserved and the live log resumes from where it is.

### Workers (`/admin/workers`)

Shows worker health and queue depths per queue, active jobs with CI names, recent failures with error details, and job history with status and duration.

### Token Usage (`/admin/tokens`)

Shows Anthropic API token consumption for the selected time window (see below).

### Query History (`/admin/queries`)

Shows recent advisor queries with timestamps, query text, and result counts.

### Token Usage

The Token Usage section shows how many Claude API tokens RCARS has consumed, broken down by model and operation type. It loads automatically when you open the admin page.

**Time window selector** — use the dropdown to choose the period:

| Option | What it shows |
|--------|--------------|
| Last 7 days | Rolling 7-day window |
| Last 30 days | Rolling 30-day window (default) |
| Last 90 days | Rolling 90-day window |
| All time | Every token ever logged |

**Summary table** — one row per model × operation combination, showing call count and token totals formatted in K/M shorthand:

| Model | Operation | Calls | Input | Output | Total |
|-------|-----------|------:|------:|-------:|------:|
| claude-sonnet-4-6 | scan | 95 | 12.4M | 380K | 12.8M |
| claude-sonnet-4-6 | rationale | 42 | 890K | 168K | 1.1M |
| claude-haiku-4-5 | triage | 42 | 240K | 84K | 324K |

- **scan** — Sonnet calls made by `rcars scan` to analyze Showroom content
- **triage** — Haiku calls made per advisor query (phase 2 relevance scoring)
- **rationale** — Sonnet calls made per advisor query that returns results (phase 3 explanation)

**Recent Queries table** — one row per advisor query, showing the triage and rationale token split side by side with a timestamp. Raw counts are shown (not K/M) since per-query volumes are smaller.

For a deeper explanation of how token tracking works internally, see the [Token Usage Tracking](token-usage.md) technical doc.

---

> **Screenshots:** The sections above describe the interface in text. Annotated screenshots for each major page (Advisor, expanded card, Curator mode, Curate page) are planned for a future update, captured via Playwright automation.
