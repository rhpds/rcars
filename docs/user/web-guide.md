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
│  Advisor     │  [welcome message]     [rec card 1]        │
│  + New       │                        [rec card 2]        │
│  ──────────  │                        [rec card 3]        │
│  Recent      │  [your message]                            │
│   session 1  │  [progress stream]                         │
│   session 2  │  [response ↩]                              │
│  ──────────  │                                            │
│  Browse      │  [input box]  [Send]                       │
│  Admin ▸     │                                            │
└──────────────┴────────────────────────────────────────────┘
```

The **RCARS header** shows two currency indicators that tell you how fresh the underlying data is:

- **CATALOG** — when the catalog was last synced from Babylon. Green **CURRENT** means synced within the last three days; red **STALE** means older.
- **ANALYSIS** — when Showroom content was last analyzed. Green **CURRENT** means analyzed within the last three days; red **STALE** means older.

Results are still useful when stale but may not reflect recent catalog additions or content changes.

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

## Conversation History

The left sidebar shows your recent sessions (up to 8). Each session shows the first query text as a label. Sessions are stored server-side in PostgreSQL, tied to your SSO email — they persist across server restarts and are accessible from any device you log into.

To start a fresh session, click **+ New Session** in the sidebar under the Advisor link. You can also click any previous session to reload it with its full conversation history and recommendation results.

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

The Browse page (`/browse`) shows the full catalog in a searchable, filterable list with client-side pagination (50 items per page).

**Filter bar:**

- **Text search** — filters by display name or CI name (case-insensitive substring match)
- **Curator filters** (curator only) — filter by: Unanalyzed, Scan Failures, Stale, Needs Review
- **Dev toggle** — show/hide dev-stage items
- **Event toggle** — show/hide event-stage items

Each item in the list shows its display name, stage badges (DEV/EVENT), ZT badge for zero-tier items, FAILED badge for scan failures, and "needs review" badge when flagged.

**Expanded item view** (click to expand):

- Analysis data: content type, difficulty, duration with source label ("AI estimate" or "estimated")
- Summary text
- Products (purple pills) and topics (blue pills)
- Learning objectives (stated + inferred)
- Module list with per-module topics
- Links to RHDP Catalog and Showroom repository

**Similar Content** — if overlap detection has been run (see Admin section below), expanded items may show a "Similar Content" panel listing other catalog items with similar Showroom content, ranked by similarity percentage. High overlap (≥85%) is shown in red; related content (75–85%) in amber. Click a similar item's name to search for it in Browse.

**Curator controls** (visible to curators only): add/remove tags, edit notes, set curated duration (minutes), override Showroom URL, set content path with "Set & Scan" button, flag for review, and Re-analyze button.

## The Admin Pages

The Admin section (`/admin`) is visible to admins only (not curators). It is split into three sub-pages, accessible via the sidebar navigation:

### Catalog (`/admin/catalog`)

The Catalog admin page has four tabs: **Status**, **Sync & Analysis**, **Workloads**, and **Overlap**.

**Status tab:**

- **Catalog Status** — total items, prod/dev/event breakdown, scannable count, analyzed, unanalyzed (clickable link to Browse filtered view), stale count, analysis failures, and last sync/analysis timestamps with CURRENT/STALE indicators
- **Scheduled Maintenance** — shows the status of the nightly maintenance pipeline (enabled/disabled, schedule time, last run summary with items synced, stale found, and analysis queued). Click **Run Maintenance Now** to trigger an on-demand run. The log window shows real-time progress. To change the schedule, see [Operations — Changing the Schedule](../admin/operations.md#changing-the-schedule).

**Sync & Analysis tab:**

- **Catalog Sync** — triggers catalog refresh from Babylon CRDs
- **Content Analysis** — two buttons: "Analyze" (scan unanalyzed items) and "Check Stale" (detect changed Showrooms). Shows a live scrolling log.
- **Full Re-Analysis** — "Re-Analyze All" button that marks every item stale and enqueues a complete rescan. Warning: consumes significant tokens.

All background operations run in arq workers. You can navigate away and come back — the current state of any running operation is preserved and the live log resumes from where it is.

**Overlap tab:**

The Overlap tab helps curators identify catalog items that teach substantially the same content. This is useful for culling duplicates — for example, two different teams may have independently built OpenShift Pipelines labs with 85% topic overlap.

**How it works:** RCARS already generates a 384-dimensional "fingerprint" (embedding) for every analyzed Showroom lab during the scan phase. The overlap detection compares these fingerprints using cosine similarity — a mathematical measure of how aligned two fingerprints are. A score of 1.0 (100%) means identical content; 0.0 means completely unrelated. No LLM calls are made — the computation runs entirely in PostgreSQL using pgvector, comparing vectors that already exist. With ~400 labs, the full computation takes seconds.

**Deduplication:** Before comparing, the system deduplicates catalog items so that stage variants (prod/dev/event) and ZT namespace aliases of the same lab are collapsed into a single representative. Dedup groups by effective Showroom URL first (same git repo = same item), then by content hash (same content from different repos). Only the best representative from each group (preferring prod over event over dev) participates in the comparison. This ensures results show genuinely different labs with overlapping content, not expected duplicates like "prod vs dev of the same thing."

**Similarity tiers:**

- **High overlap (≥85%)** — shown in red. These labs likely cover the same material and are candidates for consolidation.
- **Related (75–85%)** — shown in amber. These labs cover similar topics but may have enough differentiation to coexist.

**Using the Overlap tab:**

1. Click **Compute Similarity** to run (or re-run) the comparison. This is a lightweight database operation — no LLM tokens consumed. The stats bar updates inline when computation completes.
2. Use the dropdown to filter between "All pairs" and "High overlap only."
3. Click any pair to expand it and see both summaries side by side.
4. Click a lab name to navigate to it in the Browse page for further review.

**CLI and API access:** Similarity can also be computed via the CLI (`rcars compute-similarity [--threshold 0.75]`) or the API (`POST /api/v1/admin/compute-similarity`). The overlap report is available at `GET /api/v1/admin/overlap`, and per-item similarity at `GET /api/v1/catalog/{ci_name}/similar`.

**When to recompute:** After a full scan or re-analysis, since embeddings may have changed. The "Last computed" timestamp shows when the data was last refreshed.

### Token Usage (`/admin/tokens`)

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

### Query History (`/admin/queries`)

Shows recent advisor sessions (last 50). Each session is expandable:

- **Collapsed** — timestamp, first query text, "has selection" badge if a recommendation was chosen
- **Expanded** — per-turn details including query text, overall assessment (truncated), and result list with relevance scores (color-coded by tier), display names, stage badges, and "SELECTED" label for chosen items. Opted-out sessions show a redacted notice.
