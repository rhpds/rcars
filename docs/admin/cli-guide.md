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
  oc exec -it deployment/rcars-api -n rcars-dev -- rcars <command>
```

**Local development:** Install the package with `pip install -e ".[dev]"` and set the required environment variables (see below).

## Environment Variables

All configuration is via environment variables. No config files.

| Variable | Required | Description |
|---|---|---|
| `RCARS_DATABASE_URL` | Yes | PostgreSQL connection string. Use `postgresql://` scheme (psycopg v3). |
| `RCARS_KUBECONFIG_PATH` | For `refresh` | Path to kubeconfig with read access to Babylon namespaces. |
| `ANTHROPIC_VERTEX_PROJECT_ID` | For `scan`/`recommend` | GCP project ID for Vertex AI (preferred). |
| `CLOUD_ML_REGION` | For Vertex AI | GCP region (default: `us-east5`). |
| `ANTHROPIC_API_KEY` | For `scan`/`recommend` | Direct Anthropic API key (fallback if Vertex not set). |
| `RCARS_MODEL` | No | Claude model for analysis (default: `claude-sonnet-4-6`). |
| `RCARS_MAX_PARALLEL` | No | Threads for parallel Showroom scanning (default: `5`). |
| `RCARS_CLONE_DIR` | No | Directory for temporary Showroom clones (default: `/tmp/rcars-clones`). |
| `RCARS_VECTOR_CUTOFF` | No | Maximum vector distance to include in results (default: `0.55`). Lower = stricter. |
| `RCARS_TRIAGE_MODEL` | No | Model for fast relevance triage (default: `claude-haiku-4-5`). |
| `RCARS_TRIAGE_CUTOFF` | No | Minimum Haiku relevance score to keep a candidate (default: `30`). |
| `RCARS_RATIONALE_MODEL` | No | Model for detailed rationale generation (default: `claude-sonnet-4-6`). |
| `RCARS_RATIONALE_TOP_N` | No | Number of top candidates to generate full rationale for (default: `5`). |
| `RCARS_CURATOR_EMAILS_STR` | No | Comma-separated list of curator email addresses. |
| `RCARS_ADMIN_EMAILS_STR` | No | Comma-separated list of admin email addresses. |
| `RCARS_DEV_USER` | Local dev only | Fakes the SSO email header for local testing. |
| `RCARS_STALE_DAYS` | No | Days before catalog is considered stale (default: `3`). |
| `RCARS_REDIS_URL` | No | Redis connection URL (default: `redis://localhost:6379`). |
| `RCARS_SA_ALLOWLIST_STR` | No | Comma-separated ServiceAccount identities for API auth. |
| `RCARS_PIPELINE_ENABLED` | No | Enable nightly maintenance pipeline (default: `true`). |
| `RCARS_PIPELINE_HOUR` | No | UTC hour for nightly run (default: `4`). |
| `RCARS_PIPELINE_MINUTE` | No | Minute for nightly run (default: `0`). |
| `RCARS_CATALOG_NAMESPACES` | No | Comma-separated Babylon namespaces (default: `babylon-catalog-prod,babylon-catalog-dev,babylon-catalog-event`). |
| `RCARS_AGNOSTICV_COMPONENT_NAMESPACE` | No | Namespace for AgnosticV components (default: `babylon-config`). |

LLM credentials: RCARS prefers `ANTHROPIC_VERTEX_PROJECT_ID`. If that is not set, it falls back to `ANTHROPIC_API_KEY`. If neither is set, `scan` and `recommend` will refuse to run.

## Commands

### `rcars init-db`

Initializes or resets the database schema. Safe to run repeatedly — all DDL uses `IF NOT EXISTS`.

```bash
rcars init-db             # Create schema if it doesn't exist
rcars init-db --drop      # Drop all tables and recreate from scratch
```

The `--drop` flag terminates other database connections before dropping tables, so it works even when the web app is running. Use this for a fresh start — after dropping, you will need to run `refresh` and `scan` again to repopulate the catalog.

---

### `rcars status`

Prints a summary of the current database state. Run this first after any operation to confirm the system is healthy.

```bash
rcars status                # Catalog summary
rcars status --failures     # Include scan failure details
```

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
rcars refresh                 # Sync all configured namespaces (prod + dev + event)
```

Run `refresh` whenever you want to pick up new or changed catalog items. It is safe to run repeatedly. Existing analysis results are preserved. The command reads all configured namespaces (controlled by `RCARS_CATALOG_NAMESPACES`) every time — there is no flag to limit to a single namespace.

**What it reads:** `AgnosticVComponent` custom resources in all configured Babylon namespaces. For each component, it extracts the display name, category, product, description, keywords, stage, and Showroom repository URL and ref (extracted from known workload variable names in the CRD spec).

**CI hierarchy:** The catalog contains three tiers of items. Published Virtual CIs are what users order from `catalog.demo.redhat.com`. Each published CI points to a Base CI, which contains the actual lab content and Showroom link. Base CIs point to Infrastructure CIs (the underlying provisioning layer). RCARS analyzes Base CIs — they're where the Showroom content lives. Published VCIs are stored in the database for recommendation output (they're what users order) but are not scanned themselves.

---

### `rcars scan`

Analyzes Showroom content for catalog items that have not yet been analyzed (or that have become stale). This is the AI-intensive operation — it clones Showroom repositories and calls Claude Sonnet for each item.

```bash
rcars scan                  # Analyze all unanalyzed items
rcars scan --max 5          # Limit to 5 items (useful for testing)
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

### `rcars tag <ci-name> <type> <value>`

Adds an enrichment tag to a catalog item. Tags are visible to all users on recommendation cards and in the Browse page.

```bash
rcars tag openshift-cnv.ocp4-getting-started.prod lifecycle flagship
rcars tag openshift-cnv.ocp4-getting-started.prod event kubecon-2026
```

---

### `rcars untag <ci-name> <type> <value>`

Removes an enrichment tag from a catalog item.

```bash
rcars untag openshift-cnv.ocp4-getting-started.prod lifecycle retiring
```

---

### `rcars note <ci-name> <text>`

Sets a curator note on a catalog item. Notes are visible only to curators on the Browse page.

```bash
rcars note openshift-cnv.ocp4-getting-started.prod "Content needs updating for OCP 4.17"
```

---

### `rcars flag <ci-name>`

Flags a catalog item for enrichment review. Flagged items appear in the "Needs review" filter on the Browse page.

```bash
rcars flag openshift-cnv.ocp4-getting-started.prod
```

---

### `rcars override-url <ci-name> <url>`

Overrides the Showroom URL for a catalog item. Use this when the CRD-extracted URL is wrong or when you want to point to a different repository.

```bash
rcars override-url openshift-cnv.ocp4-getting-started.prod https://github.com/rhpds/showroom_ocp4-getting-started.git
```

---

### `rcars set-content-path <ci-name> <path>`

Sets a custom content path within the Showroom repository. By default, RCARS reads from `content/modules/ROOT/pages/`. Use this when a repository uses a non-standard layout.

```bash
rcars set-content-path openshift-cnv.ocp4-getting-started.prod content/modules/CUSTOM/pages/
```

---

### `rcars serve`

Starts the RCARS web server.

```bash
rcars serve                             # Binds to 0.0.0.0:8080
rcars serve --host 127.0.0.1 --port 8000
rcars serve --reload                    # Enable auto-reload (development only)
rcars serve --workers 4                 # Number of uvicorn workers (default: 1)
```

In production this is managed by the OpenShift deployment — you would not typically run this manually. Use it for local development or to test a configuration change before deploying.

---

## Operational Workflows

### Initial Setup (first deployment)

1. Ensure PostgreSQL is running and `RCARS_DATABASE_URL` is set.
2. Run `rcars init-db` — this creates the schema.
3. Run `rcars refresh` — this populates the catalog.
4. Run `rcars scan --max 5` — verify the AI pipeline works end to end with a small batch.
5. Check output with `rcars status` — confirm analyzed count increased.
6. Run `rcars scan` — full scan (may take 30–60 minutes depending on catalog size and parallelism).

### Fresh Start (reset everything)

```bash
rcars init-db --drop    # Wipe and recreate schema
rcars refresh           # Re-populate catalog from Babylon
rcars scan              # Full scan
```

### Incremental Catalog Sync (routine)

```bash
rcars refresh
rcars scan
```

`refresh` picks up new and changed items. `scan` analyzes anything new or stale. Items that were already analyzed and whose content has not changed are skipped automatically.

### Checking for Content Updates

Stale detection is triggered from the Admin UI or via the API (`POST /api/v1/analysis/check-stale`). It clones each analyzed Showroom and compares content hashes. Items whose content has changed are marked stale. The subsequent `scan` picks up stale items automatically alongside any new ones.

```bash
rcars scan              # Re-analyzes stale items alongside any new ones
```

### Force Full Rescan

Use this when the analysis prompt has changed or when you want to ensure all items reflect the current Sonnet model's output. Full rescans are triggered from the Admin UI via "Re-Analyze All" (`POST /api/v1/analysis/rescan-all`), which marks all items as stale and enqueues them for re-analysis.

### Debugging a Failed Item

If `rcars scan` reports an error for a specific item, investigate with:

```bash
rcars status --failures     # List all items with scan failures and error details
```

Common failure causes:
- **jinja_url** — the Showroom URL contains unresolved Jinja2 template variables
- **private_repo** — the Git repository requires authentication
- **http_404** — the repository URL returns a 404
- **clone_failed** — git clone failed (timeout, network, or other git error)
- **missing_antora** — repository does not follow the standard Antora layout
- **no_content** — no substantive content files found after filtering boilerplate
- **parse_error** — the LLM response could not be parsed as JSON
- **timeout** — the operation exceeded the timeout limit

To re-analyze a specific item, use the Browse page's "Re-analyze" button (curator access required) or the API:

```bash
curl -X POST https://rcars-dev.apps.<domain>/api/v1/analysis/<ci-name> \
  -H "Authorization: Bearer <token>"
```

Scan errors are logged to the database and visible in the Admin page of the web UI and via `rcars status --failures`.

### Testing Recommendations After a Scan

Use the Advisor page in the web UI to test recommendations. If results look wrong — poor scores, irrelevant items — check that `rcars status` shows a reasonable analyzed count and that embeddings are present (the similarity search requires them). If no embeddings exist, the recommendation engine has no candidates to rank.
