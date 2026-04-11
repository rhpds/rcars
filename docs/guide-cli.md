---
title: CLI Admin Guide
description: Command reference and operational workflows for RCARS admins
---

# CLI Admin Guide

The RCARS CLI provides full control over the system: catalog sync, content scanning, recommendations, and server management. CLI access requires either a local development setup or `oc exec` access to the running pod on OpenShift.

## Access

**On OpenShift (production/dev environment):**

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig \
  oc exec -it deployment/rcars -n rcars-dev -- rcars <command>
```

**Local development:** Install the package with `pip install -e ".[dev]"` and set the required environment variables (see below).

## Environment Variables

All configuration is via environment variables. No config files.

| Variable | Required | Description |
|---|---|---|
| `RCARS_DATABASE_URL` | Yes | PostgreSQL connection string. Use `postgresql://` scheme (psycopg v3). |
| `RCARS_KUBECONFIG` | For `refresh` | Path to kubeconfig with read access to Babylon namespaces. |
| `ANTHROPIC_VERTEX_PROJECT_ID` | For `scan`/`recommend` | GCP project ID for Vertex AI (preferred). |
| `CLOUD_ML_REGION` | For Vertex AI | GCP region (default: `us-east5`). |
| `ANTHROPIC_API_KEY` | For `scan`/`recommend` | Direct Anthropic API key (fallback if Vertex not set). |
| `RCARS_MODEL` | No | Claude model to use (default: `claude-sonnet-4-6`). |
| `RCARS_MAX_PARALLEL` | No | Threads for parallel Showroom scanning (default: `5`). |
| `RCARS_CLONE_DIR` | No | Directory for temporary Showroom clones (default: `/tmp`). |
| `RCARS_CURATOR_EMAILS` | No | Comma-separated list of curator email addresses. |
| `RCARS_ADMIN_EMAILS` | No | Comma-separated list of admin email addresses. |
| `RCARS_DEV_USER` | Local dev only | Fakes the SSO email header for local testing. |
| `RCARS_STALE_DAYS` | No | Days before catalog is considered stale (default: `3`). |

LLM credentials: RCARS prefers `ANTHROPIC_VERTEX_PROJECT_ID`. If that is not set, it falls back to `ANTHROPIC_API_KEY`. If neither is set, `scan` and `recommend` will refuse to run.

## Commands

### `rcars status`

Prints a summary of the current database state. Run this first after any operation to confirm the system is healthy.

```
Metric                   Count
─────────────────────────────
Total catalog items        342
Production items           187
With Showroom URL          134
Analyzed                   112
Stale                        3
```

**Stale** means the item's Showroom repository has been updated since RCARS last analyzed it. Stale items continue to appear in recommendations using their last-known analysis; run `rcars scan` to update them.

This command also initializes the database schema (safe to run repeatedly — all DDL uses `IF NOT EXISTS`). The Ansible deployment playbook runs `rcars status` as the schema migration step.

---

### `rcars refresh`

Pulls the current catalog from Babylon Kubernetes CRDs and upserts everything into the local database. This does not trigger content analysis — it only updates catalog metadata (names, descriptions, categories, Showroom URLs, etc.).

```bash
rcars refresh                 # Production namespace only (babylon-catalog-prod)
rcars refresh --include-dev   # All namespaces (prod + dev + event)
```

Run `refresh` whenever you want to pick up new or changed catalog items. It is safe to run repeatedly. Existing analysis results are preserved.

**What it reads:** `AgnosticVComponent` custom resources in the configured Babylon namespaces. For each component, it extracts the display name, category, product, description, keywords, stage, and Showroom repository URL and ref (extracted from known workload variable names in the CRD spec).

**CI hierarchy:** The catalog contains three tiers of items. Published Virtual CIs are what users order from `catalog.demo.redhat.com`. Each published CI points to a Base CI, which contains the actual lab content and Showroom link. Base CIs point to Infrastructure CIs (the underlying provisioning layer). RCARS analyzes Base CIs — they're where the Showroom content lives. Published VCIs are stored in the database for recommendation output (they're what users order) but are not scanned themselves.

---

### `rcars list`

Lists catalog items in a table. Useful for inspection and debugging.

```bash
rcars list                        # All items
rcars list --prod-only            # Production items only
rcars list --with-showroom        # Only items that have a Showroom URL
rcars list --category "Workshops" # Filter by category
```

Flags can be combined.

---

### `rcars show <ci-name>`

Shows the full detail record for a single catalog item.

```bash
rcars show openshift-cnv.ocp4-getting-started.prod
rcars show openshift-cnv.ocp4-getting-started.prod --full   # Include full description
```

Output includes the CI name, type (published VCI / base CI / standalone), catalog link, category, product, stage, keywords, and Showroom URL/ref. Useful for confirming what RCARS knows about a specific item before or after a scan.

---

### `rcars scan`

Analyzes Showroom content for catalog items that have not yet been analyzed (or that have become stale). This is the AI-intensive operation — it clones Showroom repositories and calls Claude Sonnet for each item.

```bash
rcars scan                  # Analyze all pending (new + stale) items
rcars scan --max 5          # Limit to 5 items (useful for testing)
rcars scan --force          # Re-analyze everything, even already-analyzed items
```

**What happens per item:**

1. The Showroom Git repository is shallow-cloned to a temporary directory.
2. AsciiDoc files are read from the standard Antora layout (`content/modules/ROOT/pages/`).
3. Boilerplate pages are filtered out — login/credentials pages, environment setup pages, index pages, and navigation files are excluded so the AI focuses on actual lab content.
4. The remaining content is assembled into a prompt alongside the catalog item's metadata and sent to Claude Sonnet.
5. Sonnet returns a structured JSON analysis: content type, summary, products covered, target audience, difficulty, estimated duration, topics, learning objectives (both stated in the content and inferred from the exercises), module-level breakdown, use cases, and event fit assessments for booth, hands-on, and presentation formats.
6. A 384-dimensional vector embedding is generated from the analysis using a local sentence-transformers model (`all-MiniLM-L6-v2`). Module-level embeddings are generated separately, one per module.
7. The analysis and embeddings are written to the database. The temporary clone is deleted.

**Parallelism:** Items are processed in parallel threads (default: 5, controlled by `RCARS_MAX_PARALLEL`). Reduce this if you hit API rate limits or memory pressure.

**Cost:** Each item requires one Sonnet API call. A full scan of ~130 Showroom items will make ~130 calls. Use `--max` to test on a small batch before running a full scan.

**Scan scope:** Only base CIs are scanned. Published VCIs are skipped because their content lives in the base CI they reference.

---

### `rcars recommend`

Runs a recommendation query from the command line. This is the same engine the web UI uses.

```bash
rcars recommend "OpenShift demos for a developer audience at a Kubernetes conference"
rcars recommend "AAP hands-on lab, 90 minutes, ops audience" --include-dev
rcars recommend "booth content for a security-focused event" --limit 20
rcars recommend "developer workshop" --json-output
```

**With an event URL:**

```bash
rcars recommend "what fits this event?" --url https://events.example.com/kubecon-2026
```

When `--url` is provided, RCARS fetches the event page, strips it to plain text, and asks Sonnet to extract a structured event profile: audience, themes, format details, and suggested search queries. That profile is merged with your query text before the similarity search runs.

**Options:**

| Flag | Description |
|---|---|
| `--url` | Event URL to parse for context |
| `--include-dev` | Include dev-stage catalog items (default: prod only) |
| `--limit N` | Number of candidates to retrieve before ranking (default: 15) |
| `--json-output` | Print raw JSON instead of formatted output |

Output shows ranked results with scores, rationale, suggested format, duration notes, and any caveats. Content gaps (topics you asked for that nothing in the catalog covers) are listed at the end.

---

### `rcars serve`

Starts the RCARS web server.

```bash
rcars serve                             # Binds to 127.0.0.1:8000
rcars serve --host 0.0.0.0 --port 8080
rcars serve --reload                    # Enable auto-reload (development only)
```

In production this is managed by the OpenShift deployment — you would not typically run this manually. Use it for local development or to test a configuration change before deploying.

---

## Operational Workflows

### Initial Setup (first deployment)

1. Ensure PostgreSQL is running and `RCARS_DATABASE_URL` is set.
2. Run `rcars status` — this initializes the schema.
3. Run `rcars refresh` — this populates the catalog.
4. Run `rcars scan --max 5` — verify the AI pipeline works end to end with a small batch.
5. Check output with `rcars status` — confirm analyzed count increased.
6. Run `rcars scan` — full scan (may take 30–60 minutes depending on catalog size and parallelism).

### Incremental Catalog Sync (routine)

```bash
rcars refresh
rcars scan
```

`refresh` picks up new and changed items. `scan` analyzes anything new or stale. Items that were already analyzed and whose Showroom repos have not changed are skipped automatically.

### Force Full Rescan

Use this when the analysis prompt has changed or when you want to ensure all items reflect the current Sonnet model's output.

```bash
rcars scan --force
```

This re-analyzes every item that has a Showroom URL, regardless of whether it has been analyzed before.

### Debugging a Failed Item

If `rcars scan` reports an error for a specific item, investigate with:

```bash
rcars show <ci-name>          # Confirm the Showroom URL is present and correct
rcars scan --max 1 --force    # Not directly targetable by CI name, so use --max 1
                              # after removing other pending items, or check logs
```

Common failure causes:
- The Showroom Git repository is private or has been deleted
- The repository does not follow the standard Antora layout (no `content/modules/ROOT/pages/`)
- The content is entirely boilerplate with no substantive pages
- API rate limits or credential issues (check `ANTHROPIC_VERTEX_PROJECT_ID` is set)

Scan errors are logged to the database action log and visible in the Admin page of the web UI.

### Testing Recommendations After a Scan

```bash
rcars recommend "OpenShift developer workshop" --limit 5
```

If results look wrong — poor scores, irrelevant items — check that `rcars status` shows a reasonable analyzed count and that embeddings are present (the similarity search requires them). If no embeddings exist, the recommendation engine has no candidates to rank.
