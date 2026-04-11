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

**What makes a query effective:**

- **Audience** — developers, ops, architects, executives, mixed
- **Format** — booth demo, hands-on lab, presentation support
- **Duration** — 20 minutes, half-day, 90 minutes
- **Topic or product** — if you already know the focus area
- **Event context** — conference name, industry, theme

You do not need all of these. Even a short query like *"OpenShift demos for a developer audience"* returns useful results. More context narrows the ranking.

## Reading Recommendation Cards

Each result appears as a card in the right pane. Cards are ranked by fit score.

**Score colors:**

- Green (80–100%) — strong match
- Amber (50–79%) — reasonable fit with caveats
- Red (below 50%) — included because it's the closest available, but not ideal

Each card shows:

- **Name** — the display name of the catalog item
- **CI Name** — the internal identifier (useful when ordering through the catalog)
- **Format** — whether the content suits a booth demo, hands-on lab, or presentation
- **Duration** — estimated time to complete
- **Difficulty** — beginner, intermediate, or advanced
- **Rationale** — a plain-language explanation of why this item fits your request. Read this. It tells you whether the fit is genuine or a stretch.
- **Tags** — any curator-applied labels that add context beyond the AI analysis

## Expanding a Card

Click anywhere on a card to expand it. The expanded view adds:

- **Caveats** — anything the system flags as a potential issue (content gaps, timing concerns, audience mismatches)
- **Module list** — the individual sections of the lab, with estimated time per module
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

The left sidebar shows your recent sessions. Labels are generated from the first message in each conversation. Sessions are stored in your browser — they are not shared with other users and are not stored on the server. If the server restarts, session history labels will still appear in the sidebar but clicking them will no longer restore results.

To start a fresh session, click **+ New session** (visible at the bottom of the recommendations pane).

## Curator Mode

If your account has curator access, you will see a curator mode toggle in the top navigation. When activated, expanded recommendation cards show additional controls.

**What curators can do:**

- **Add tags** — short labels that describe the content in ways the AI analysis may miss. Tags appear on cards for all users. Examples: `booth-tested`, `aws-event`, `needs-update`, `flagship`.
- **Add notes** — longer free-text observations visible only to other curators in the Curate page.
- **Flag for review** — marks an item with ⚑ to indicate it needs attention. Flagged items appear in the Curate page's needs-review filter.

Curator changes are saved immediately when submitted. Tags can be removed from the Curate page.

## The Curate Page

The Curate page (`/curate`) shows the full catalog — not just current recommendations — in a paginated list. Use the filter bar to search by name, filter by product, or show only flagged or untagged items.

Per-item controls on this page are the same as in the expanded card view: add/remove tags, edit notes, flag or unflag. This page is the right place to do bulk enrichment work, not something you'd use during an event conversation.

## The Admin Page

The Admin page (`/admin`) is visible to curators and admins. It shows the current scan status (how many items are pending analysis, when the last scan ran), lets you trigger a new scan, and shows the current DB currency. Ops-level operations — forcing a full rescan, reading scan logs — are handled via the CLI.

---

> **Screenshots:** The sections above describe the interface in text. Annotated screenshots for each major page (Advisor, expanded card, Curator mode, Curate page) are planned for a future update, captured via Playwright automation.
