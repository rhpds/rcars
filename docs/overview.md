---
title: Overview
description: What RCARS is, why it exists, and how it works
---

# RCARS — Overview

## What is RCARS?

RCARS (RHDP Content Advisory & Recommendation System) is an AI-powered tool that helps Red Hat field teams find the right demos and hands-on labs for any event, booth, or customer conversation. Ask it a question in plain English — "what should we show at a developer-focused Kubernetes conference?" — and it returns a ranked list of RHDP catalog items that fit, each with a plain-language explanation of why it's a good match.

## The Problem It Solves

The Red Hat Demo Platform catalog contains hundreds of demos and workshop labs across every Red Hat product line. Finding the right content for a specific event — the right topic, audience level, duration, and format — requires someone who knows the catalog well. That expertise is scarce and doesn't scale. New team members don't know what exists. Even experienced people miss content outside their product area. Events get staffed with familiar demos rather than the best-fit ones.

RCARS solves this by doing the reading that no one has time to do. It reads the actual lab content — the step-by-step instructions, the exercises, the modules — not just the titles and descriptions. It understands what a learner will actually do and learn in each lab, and uses that understanding to match content to requests.

## How It Works

RCARS runs in three stages that happen automatically:

1. **Catalog sync.** RCARS reads the live RHDP catalog directly from the platform's configuration system (Babylon). Every catalog item — its name, category, product, audience tags, and links to its lab content — is stored in a local database.

2. **Content analysis.** For every catalog item that has associated lab content (a Showroom), RCARS clones the content repository and reads it. It sends that content to Claude Sonnet, which produces a structured analysis: what the lab covers, what skills it teaches, who the intended audience is, how long it takes, and whether it's suitable for a booth demo, a hands-on session, or a presentation. These analyses are stored alongside 384-dimensional vector embeddings that capture the semantic meaning of each piece of content.

3. **Recommendations.** When someone asks a question, RCARS runs a three-phase pipeline. First, the query is converted into a vector embedding and run against stored content embeddings to find semantically similar candidates. Second, a fast AI model (Claude Haiku) triages those candidates — scoring each one for relevance and filtering out poor matches. Third, the top-scoring candidates are sent to Claude Sonnet, which generates a structured analysis for each: why it fits, how to use it, and any caveats. The result is a scored, ranked list with a rationale for each item.

4. **Stale detection.** RCARS can check whether analyzed Showroom content has changed since the last scan. It clones each Showroom, hashes the content files, and compares against the stored hash. Items whose content has materially changed are marked stale and picked up automatically by the next scan.

Each of these stages is independent. The catalog can be refreshed without re-analyzing content. Content can be re-analyzed without clearing existing recommendations. Stale detection can run without triggering a rescan. Nothing is hardwired.

## Who Uses It and How

**Field teams and event staff** use the RCARS web UI. The interface is a simple two-pane layout: a conversation on the left, recommendations on the right. Type what you need, read what fits. No training required.

**Curators** — people who maintain catalog quality — can use the web UI's curator mode to tag catalog items with custom labels, add notes, and flag content that needs review. These enrichments feed back into future recommendations.

**Ops admins** who manage the RCARS deployment use the command-line interface. The CLI provides full control: syncing the catalog, running or re-running content scans, checking system status, and starting the web server. See the [CLI Admin Guide](guide-cli.md) for details.

## What It Runs On

RCARS runs on Red Hat OpenShift as a three-tier application: a React frontend, a FastAPI JSON API, and arq background workers for LLM operations. It is backed by PostgreSQL with the pgvector extension for fast similarity search over stored content embeddings. AI analysis and recommendations use Claude Sonnet via Red Hat's Vertex AI integration. Access is controlled through OpenShift's built-in OAuth proxy, so users log in with their standard Red Hat SSO credentials.

## Current Status

RCARS is running in a development environment on the RHDP infrastructure cluster. The catalog is actively synced from the production Babylon namespace, and content analysis is underway. The web UI is accessible to authenticated Red Hat users with access to the deployment.

## A Note on the Name

RCARS is a nod to LCARS — the Library Computer Access and Retrieval System, the fictional computer interface from Star Trek. LCARS is the amber-and-dark panel design that defined what a futuristic computer looked like for a generation of engineers and designers. RCARS borrows the acronym structure, the dark background, and the amber color palette. The LCARS aesthetic felt appropriate for a system that is, at its core, a library computer: you ask it what you need, it tells you where to find it.

It is also just a fun name for an internal tool.
