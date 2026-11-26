---
title: CLI Admin Guide
description: Command reference for RCARS admins
---

# CLI Admin Guide

The RCARS CLI provides full control over the system: catalog sync, content scanning, curation, infrastructure metadata, reporting, and server management.

## Access

CLI commands run inside the API pod on OpenShift. You must be logged into the cluster with `oc login` or have your `KUBECONFIG` set to the management service account kubeconfig.

```bash
oc exec deployment/rcars-api -n rcars-dev -- rcars <command>
```

For prod, use `-n rcars-prod`. For operational workflows (initial setup, fresh start, incremental sync), see the [Deployment Guide](deployment.md#operational-workflows).

## Global Options

```bash
rcars --verbose <command>    # Enable debug logging (-v shorthand)
```

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
RCARS Catalog Status
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric            ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total catalog items │   342 │
│ Production items    │   187 │
│ With Showroom URL   │   134 │
│ Analyzed            │   112 │
│ Stale               │     3 │
│ Scan failures       │     2 │
└─────────────────────┴───────┘
```

**Stale** means the item's Showroom repository has been updated since RCARS last analyzed it. Stale items continue to appear in recommendations using their last-known analysis; run `rcars scan` to update them.

With `--failures`, shows a table of all failed items with error class and failure timestamp. See the [Deployment Guide](deployment.md#debugging-a-failed-item) for common error classes.

---

### `rcars refresh`

Pulls the current catalog from Babylon Kubernetes CRDs and upserts everything into the local database. This does not trigger content analysis — it only updates catalog metadata (names, descriptions, categories, Showroom URLs, etc.).

```bash
rcars refresh
```

Run `refresh` whenever you want to pick up new or changed catalog items. It is safe to run repeatedly. Existing analysis results are preserved. The command reads all configured namespaces (controlled by `RCARS_CATALOG_NAMESPACES`) every time.

**What it reads:** `AgnosticVComponent` custom resources in all configured Babylon namespaces. For each component, it extracts the display name, category, product, description, keywords, stage, and Showroom repository URL and ref (extracted from known workload variable names in the CRD spec).

**Soft-delete:** Items that disappear from Babylon CRDs are not deleted — they get `retired_at = NOW()`. Items that reappear in a future scan are automatically un-retired.

**CI hierarchy:** Published Virtual CIs are what users order from `catalog.demo.redhat.com`. Each points to a Base CI that contains the actual lab content. RCARS analyzes Base CIs — they're where the Showroom content lives. Published VCIs are stored for recommendation output but are not scanned themselves.

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
5. Sonnet returns a structured JSON analysis: content type, summary, products, audience, difficulty, duration, topics, learning objectives, module breakdown, use cases, and event fit assessments.
6. A 768-dimensional vector embedding is generated from the analysis using the nomic-embed-text-v1.5 model via the vLLM embedding server. Module-level embeddings are generated separately.
7. The analysis and embeddings are written to the database. The temporary clone is deleted.

**Parallelism:** Items are processed in parallel threads (default: 5, controlled by `RCARS_MAX_PARALLEL`). Reduce this if you hit API rate limits or memory pressure.

**Cost:** A scan makes at most one Sonnet API call per item. Reuse lowers the count. An item reuses a donor analysis only when the `content_hash`, `analysis_config` and content type all match, and the run is not forced. `analysis_config` includes the per-item prompt inputs (CI name, display name, category, product), so two different CIs usually need separate calls today. Use `--max` to test on a small batch before running a full scan.

**Deduplication:** A pre-clone check by repo + resolved commit + `content_path` finds a known hash. A donor with the same `content_hash` and `analysis_config` is reused from any CI or stage; each item still gets its own analysis row and embeddings. Ref names never count as content. A forced rescan skips reuse. The planned prompt change (RHDPCD-2302 PR 7) removes the per-item lines from the prompt and makes cross-CI reuse the normal case.

---

### `rcars overlap-candidates`

Finds overlapping content pairs by shared products and topics and stores them in
`overlap_candidates`. Stage copies count as one item. A virtual CI and its own
family members are never a pair. Pairs that do not meet the thresholds are
pruned. No LLM calls.

```bash
rcars overlap-candidates                       # Default: 1 shared product, 2 shared topics
rcars overlap-candidates -p 2                  # Require 2 shared products
rcars overlap-candidates -t 3                  # Require 3 shared topics
```

The nightly maintenance pipeline runs this step, then assesses new pairs with
the LLM. See [Content Overlap](../architecture/content-overlap.md).

---

### Curation Commands

These commands add metadata visible in the Browse page and recommendation cards.

#### `rcars tag <ci-name> <type> <value>`

Adds an enrichment tag to a catalog item.

```bash
rcars tag openshift-cnv.ocp4-getting-started.prod lifecycle flagship
rcars tag openshift-cnv.ocp4-getting-started.prod event kubecon-2026
```

#### `rcars untag <ci-name> <type> <value>`

Removes an enrichment tag.

```bash
rcars untag openshift-cnv.ocp4-getting-started.prod lifecycle retiring
```

#### `rcars note <ci-name> <text>`

Sets a curator note (visible to curators only on the Browse page).

```bash
rcars note openshift-cnv.ocp4-getting-started.prod "Content needs updating for OCP 4.17"
```

#### `rcars flag <ci-name>`

Flags an item for enrichment review. Flagged items appear in the "Needs review" filter on the Browse page.

```bash
rcars flag openshift-cnv.ocp4-getting-started.prod
```

#### `rcars override-url <ci-name> <url>`

Overrides the Showroom URL for a catalog item. Use this when the CRD-extracted URL is wrong or when you want to point to a different repository.

```bash
rcars override-url openshift-cnv.ocp4-getting-started.prod https://github.com/rhpds/showroom_ocp4-getting-started.git
```

#### `rcars set-content-path <ci-name> <path>`

Sets a custom content path within the Showroom repository. By default, RCARS reads from `content/modules/ROOT/pages/`. Use this when a repository uses a non-standard layout.

The path can be either an Antora start path or a directory that holds the pages. If `<path>/modules/ROOT/pages` exists, RCARS reads that directory and finds `nav.adoc` in `<path>/modules/ROOT/`. This is how the default `content` start path works. Otherwise RCARS reads `.adoc` files directly from `<path>`.

```bash
# Antora start path (the value of start_path in the playbook)
rcars set-content-path openshift-cnv.advanced-automation-bootcamp.prod documentation

# Directory that holds the pages directly
rcars set-content-path openshift-cnv.ocp4-getting-started.prod content/modules/CUSTOM/pages/
```

---

### Infrastructure Commands

These commands show statistics about the infrastructure catalog — the scanned workload roles and base configs from AgnosticD v2.

#### `rcars infra stats`

Shows coverage statistics for the infrastructure catalog.

```
Infrastructure Catalog Stats
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric                  ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total entries           │   166 │
│ Workload roles          │   125 │
│ Base configs            │    41 │
│ Linked to catalog items │    89 │
│ Orphans (no CI link)    │    77 │
└─────────────────────────┴───────┘
```

"Linked" means at least one catalog item deploys or uses this infrastructure entry. "Orphans" are entries that exist in the AgnosticD source repos but are not referenced by any current catalog item.

---

### Workload Commands

#### `rcars workload sync [--seed-only]`

Loads the workload mapping seed file (`src/api/rcars/data/workload_mapping.yaml`) into the database.

```bash
rcars workload sync               # Overwrite DB with YAML values
rcars workload sync --seed-only   # Skip roles that already exist in DB (preserve curator edits)
```

#### `rcars workload scan [--collection X] [--force]`

Scans the AgnosticD v2 workload collection repos on GitHub, reads each role's Ansible code, and uses an LLM to determine what product/operator the role installs. Also scans base configs from the AgnosticD v2 config repositories to identify what platform or infrastructure each config provisions.

```bash
rcars workload scan                                          # Scan all collections (roles + configs)
rcars workload scan --collection agnosticd.core_workloads    # Scan one collection only (-c shorthand)
rcars workload scan --force                                  # Skip SHA check, rescan everything
```

Uses `git ls-remote` to check if each repo has changed since the last scan. Unchanged repos are skipped unless `--force` is used. Results are stored in the `infrastructure` table and made searchable via vector embeddings.

#### `rcars workload unmapped`

Lists all workload roles that appear in catalog items but don't have a curated mapping yet. Sorted by how many catalog items use each role.

#### `rcars workload map <role> <product> [--category CAT] [--description DESC]`

Manually add or update a single workload mapping.

```bash
rcars workload map ocp4_workload_openshift_ai "OpenShift AI" --category ai_ml
```

#### `rcars workload alias <product> <alias>`

Add a product name alias so queries using alternate names resolve correctly.

```bash
rcars workload alias "OpenShift AI" RHOAI
rcars workload alias "Advanced Cluster Security" RHACS
```

#### `rcars workload list`

Lists all current workload mappings with their product name, category, and verification status.

---

### Reporting Commands

These commands manage the integration with the RHDP reporting database for performance analysis. Requires `RCARS_REPORTING_MCP_URL` and `RCARS_REPORTING_MCP_TOKEN` to be configured.

#### `rcars reporting-db sync`

Syncs reporting metrics (provisions, sales, cost) from the RHDP MCP server, computes performance scores, and upserts to the local database.

```bash
rcars reporting-db sync
```

#### `rcars reporting-db status`

Shows reporting sync status: last synced timestamp and score distribution (strong/moderate/low).

```bash
rcars reporting-db status
```

#### `rcars reporting-db show <ci-name>`

Shows detailed reporting metrics for a specific catalog item. Accepts either the full ci_name (e.g., `sandboxes-gpte.sandbox-ocp.prod`) or the base name (e.g., `sandboxes-gpte.sandbox-ocp`).

```bash
rcars reporting-db show sandboxes-gpte.sandbox-ocp
```

---

### `rcars retirement sweep`

Opens removal PRs for started workflows whose target date has been reached, with a linked Jira ticket and no existing removal/revert PR or retirement marker. Requires the configured database and GitHub App credentials. It runs directly in the CLI process and prints item-level results; it does not enqueue a worker job or merge any PR.

```bash
rcars retirement sweep
```

This CLI path currently creates due PRs only. It does **not** perform the merged-removal/revert reconciliation included in the API/nightly worker sweep. Use **Run Retirement Sweep** in Sync & Analysis, or refresh an individual workflow as an admin, to reconcile merges. Review overdue workflows before the first run and avoid concurrent sweeps. See [Retirement System](../architecture/retirement-system.md).

---

### `rcars retirement mark-revived`

Closes a family's current retired workflow as revived, for items that came back before revive tracking existed. It sets `revived_at` and `revived_reason` and keeps the row as history. It writes nothing unless `--apply` is given.

```bash
# Dry run: print what would change.
rcars retirement mark-revived --content-id babylon:example.item.event

# Write the change.
rcars retirement mark-revived --content-id babylon:example.item.event --apply
```

Only the families named with `--content-id` are considered; the command never scans for candidates, because the data cannot tell a revive from a workflow retired by a merged removal PR while the CatalogItem was still present. The command refuses, in this order:

- a content_id with no content entity;
- an item whose entity is still retired;
- a family with no current workflow, or with a current workflow that is not retired;
- a workflow that has a removal PR URL, unless `--force` is given. Such a workflow was retired on purpose; use `--force` only when the item truly came back.

A second run reports `already marked revived` and changes nothing. `--reason` overrides the default `Backfill: item returned before history tracking`. The command writes one `retirement_revived` row to `analysis_log` per workflow it marks.

---

### `rcars serve`

Starts the RCARS web server. In production this is managed by the OpenShift deployment.

```bash
rcars serve                             # Binds to 0.0.0.0:8080
rcars serve --host 127.0.0.1 --port 8000
rcars serve --reload                    # Enable auto-reload (development only)
rcars serve --workers 4                 # Number of uvicorn workers (default: 1)
```

---

## Environment Variables

All configuration is via `RCARS_`-prefixed environment variables. No config files. In production, these are set via the Ansible deployment — see `ansible/vars/<env>.yml` and `ansible/templates/manifests-app.yaml.j2`.

### Required

| Variable | Description |
|---|---|
| `RCARS_DATABASE_URL` | PostgreSQL connection string. Use `postgresql://` scheme (psycopg v3). |
| `RCARS_KUBECONFIG_PATH` | Path to kubeconfig with read access to Babylon namespaces. Required for `refresh`. |

### LLM Provider

RCARS uses LiteMaaS (internal Red Hat proxy) as its only LLM provider. If it is not configured, `scan` and `recommend` will refuse to run.

| Variable | Description |
|---|---|
| `RCARS_LITEMAAS_URL` | LiteMaaS proxy endpoint. |
| `RCARS_LITEMAAS_API_KEY` | LiteMaaS API key. |

### Models

| Variable | Default | Description |
|---|---|---|
| `RCARS_MODEL` | `claude-sonnet-4-6` | Model for Showroom content analysis. |
| `RCARS_TRIAGE_MODEL` | `claude-haiku-4-5` | Model for fast relevance triage. |
| `RCARS_RATIONALE_MODEL` | `claude-sonnet-4-6` | Model for detailed rationale generation. |

### Tuning

| Variable | Default | Description |
|---|---|---|
| `RCARS_MAX_PARALLEL` | `5` | Threads for parallel Showroom scanning. |
| `RCARS_CLONE_DIR` | `/tmp/rcars-clones` | Directory for temporary Showroom clones. |
| `RCARS_VECTOR_CUTOFF` | `0.55` | Maximum vector distance for results. Lower = stricter. |
| `RCARS_TRIAGE_CUTOFF` | `30` | Minimum Haiku relevance score to keep a candidate. |
| `RCARS_RATIONALE_TOP_N` | `5` | Number of top candidates to generate full rationale for. |
| `RCARS_STALE_DAYS` | `3` | Days before catalog/analysis is considered stale. |

### Access Control

| Variable | Default | Description |
|---|---|---|
| `RCARS_CURATOR_EMAILS_STR` | — | Comma-separated list of curator email addresses. |
| `RCARS_ADMIN_EMAILS_STR` | — | Comma-separated list of admin email addresses. |
| `RCARS_SA_ALLOWLIST_STR` | — | Comma-separated ServiceAccount identities for API auth. |
| `RCARS_DEV_USER` | — | Fakes the SSO email for local testing. |

### Infrastructure

| Variable | Default | Description |
|---|---|---|
| `RCARS_REDIS_URL` | `redis://localhost:6379` | Redis connection URL. |
| `RCARS_CATALOG_NAMESPACES` | `babylon-catalog-prod,babylon-catalog-dev,babylon-catalog-event` | Babylon namespaces to scan. |
| `RCARS_AGNOSTICV_COMPONENT_NAMESPACE` | `babylon-config` | Namespace for AgnosticV components. |

### Nightly Pipeline

| Variable | Default | Description |
|---|---|---|
| `RCARS_PIPELINE_ENABLED` | `true` | Enable nightly maintenance pipeline. |
| `RCARS_PIPELINE_HOUR` | `4` | UTC hour for nightly run. |
| `RCARS_PIPELINE_MINUTE` | `0` | Minute for nightly run. |

### Reporting

| Variable | Description |
|---|---|
| `RCARS_REPORTING_MCP_URL` | RHDP Reporting MCP server HTTPS endpoint. |
| `RCARS_REPORTING_MCP_TOKEN` | Bearer token for MCP server (stored as K8s Secret). |
| `RCARS_REPORTING_SALES_DAYS` | Trailing window for provisions/touched/cost (default: `365`). |
| `RCARS_REPORTING_PROVISIONS_DAYS` | Trailing window for quarter provisions (default: `90`). |
