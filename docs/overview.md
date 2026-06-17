---
title: Overview
description: What RCARS is, why it exists, and how it works
---

# RCARS — Overview

## What is RCARS?

RCARS (RHDP Content Advisory & Recommendation System) is an AI-powered platform for managing Red Hat Demo Platform catalog content. It reads every lab and demo in the RHDP catalog, understands what each one teaches, and uses that understanding to help teams find the right content, detect duplicate material, and identify items that should be retired.

Ask it a question in plain English — "what should we show at a developer-focused Kubernetes conference?" — and it returns a ranked list of catalog items that fit, each with a rationale. But RCARS has grown beyond recommendations into a broader content intelligence system: it tracks infrastructure metadata, detects content overlap, imports usage and sales data from the RHDP reporting system, and scores items for retirement.

## The Problem It Solves

The Red Hat Demo Platform catalog contains hundreds of demos and workshop labs across every Red Hat product line. Several problems compound at this scale:

**Finding the right content** requires knowing the catalog well. New team members don't know what exists. Even experienced people miss content outside their product area. Events get staffed with familiar demos rather than the best-fit ones.

**Duplicate content** accumulates as different teams build labs that cover the same material under different names and structures. Without a way to detect semantic overlap, the catalog grows without bounds.

**Stale content** lingers after products evolve. Items that were once popular may no longer reflect current products or drive meaningful sales. Without data-driven retirement analysis, these items consume infrastructure resources and confuse content selectors.

RCARS addresses all three by reading the actual lab content — not just titles and descriptions — and combining that understanding with usage, sales, and infrastructure data from the broader RHDP ecosystem.

## How It Works

### Content Ingestion

RCARS reads the live RHDP catalog directly from the Babylon platform's Kubernetes CRDs. For every catalog item with a Showroom (lab content repository), it clones the repo, reads the AsciiDoc modules, and sends the content to Claude Sonnet for structured analysis: what the lab covers, learning objectives, audience, duration estimate, and format suitability. The analysis is stored alongside 384-dimensional vector embeddings that capture the semantic meaning of each piece of content.

For AgnosticD v2 items, RCARS also extracts infrastructure metadata — cloud provider, OCP version, installed workloads — and maps workload roles to human-readable product names through a curated mapping table.

### Recommendations

When someone asks a question, RCARS runs a three-phase pipeline:

1. **Vector search** — the query is embedded and compared against stored content embeddings using pgvector cosine similarity
2. **Haiku triage** — a fast AI model scores each candidate for relevance and filters poor matches
3. **Sonnet rationale** — the top candidates get structured rationales: why it fits, how to use it, suggested format, caveats

The pipeline supports event URL parsing (paste a conference URL, get matched content), duration-aware reranking, and acronym expansion for Red Hat product abbreviations.

### Content Overlap Detection

RCARS compares lab embeddings against each other to find catalog items that teach substantially the same material. This is a curator tool for identifying duplicates — items with 85%+ cosine similarity are flagged as near-duplicates, and 75-84% as related content worth reviewing. Comparisons are scoped by stage (prod vs prod only).

### Retirement Analysis

RCARS imports provision counts, sales pipeline data, closed revenue, and infrastructure cost from the RHDP reporting database (the same source as the SuperSet management dashboard). It uses this data to score each production item for retirement on a percentile basis — items in the bottom tier for usage, pipeline, and revenue relative to their peers score highest.

The retirement dashboard has two views: **Prod Retirements** (scored table for items with production deployments) and **Without Prod** (age-based list of dev/event-only items that haven't been promoted).

### Nightly Maintenance

A nightly pipeline runs at 04:00 UTC and chains five steps: catalog refresh, stale content detection, re-analysis of changed items, workload repo scanning, and reporting data sync. Each step runs independently — a failure in one does not block the others.

## Who Uses It

**Field teams and event staff** use the Advisor to find content for events, booths, and customer conversations. The interface is a two-pane layout: conversation on the left, recommendation cards on the right. Follow-up queries refine results. No training required.

**Content curators** use Browse to review catalog items, tag content, set duration estimates, and mark best-fit recommendations. Content Analysis provides overlap detection (which labs duplicate each other?) and retirement scoring (which items should we sunset?).

**Platform admins** use the Admin pages and CLI to monitor catalog health, trigger scans, manage workload mappings, track LLM token usage, and review query history.

**Publishing House** (the RHDP content management system) calls RCARS APIs to check content overlap during intake and search by infrastructure characteristics.

## What It Runs On

RCARS runs on OpenShift as four deployments: a React frontend (LCARS-themed), a FastAPI API, and two arq background workers (scan and recommend, split to prevent bulk operations from blocking user queries). It is backed by PostgreSQL with pgvector for semantic search and Redis for job queuing and SSE streaming.

LLM calls use LiteMaaS (Red Hat's internal AI service) as the primary provider with Vertex AI as an automatic fallback. Three models: Sonnet for content analysis and rationale, Haiku for triage and workload scanning.

Reporting data is imported from the RHDP reporting MCP server, which provides access to the same `provisions_summary` materialized view that powers the SuperSet management dashboard.

Access is controlled through OpenShift's OAuth proxy with Red Hat SSO, with three role tiers: viewer, curator, and admin.

## A Note on the Name

RCARS is a nod to LCARS — the Library Computer Access and Retrieval System, the fictional computer interface from Star Trek. LCARS is the amber-and-dark panel design that defined what a futuristic computer looked like for a generation of engineers and designers. RCARS borrows the acronym structure, the dark background, and the amber color palette. The LCARS aesthetic felt appropriate for a system that is, at its core, a library computer: you ask it what you need, it tells you where to find it.

It is also just a fun name for an internal tool.
