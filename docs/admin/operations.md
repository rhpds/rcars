---
title: Worker Management
description: How to run, scale, and monitor arq workers
---

# Worker Management

Workers are long-running processes that pick up jobs from Redis queues. They are split into two deployments to prevent bulk scans from blocking user-facing advisor queries.

## Worker Deployments

| Deployment | Entry Point | Queue | Tasks | Timeouts |
|---|---|---|---|---|
| `rcars-scan-worker` | `arq rcars.workers.WorkerSettings` | `arq:queue:scan` | `run_analysis`, `run_catalog_refresh`, `run_stale_check`, `run_nightly_pipeline` | 600s default, stale_check 3600s, nightly 7200s |
| `rcars-recommend-worker` | `arq rcars.workers.RecommendWorkerSettings` | `arq:queue:recommend` | `run_recommendation` | 120s |

Both use the same container image (`rcars-api:latest`) with different arq entrypoints.

## Running Workers Locally

```bash
# Start both workers (handled by dev-services.sh)
./dev-services.sh start

# Or start individually
arq rcars.workers.WorkerSettings          # scan/ops worker
arq rcars.workers.RecommendWorkerSettings  # recommend worker
```

Logs: `/tmp/rcars-scan-worker.log` and `/tmp/rcars-recommend-worker.log`

## Scaling

Workers are stateless — add replicas by deploying more pods. Replica counts and resource limits are set in `ansible/vars/common.yml` (or overridden per environment in `dev.yml`/`prod.yml`):

```yaml
# Replica counts
scan_worker_replicas: 1       # increase for bulk scan throughput
recommend_worker_replicas: 1  # each replica handles 3 concurrent queries

# API resource limits
api_cpu_request: 500m
api_cpu_limit: "2"
api_memory_request: 1Gi
api_memory_limit: 4Gi

# Scan worker resource limits
worker_cpu_request: 500m
worker_cpu_limit: "2"
worker_memory_request: 1Gi
worker_memory_limit: 4Gi

# Recommend worker resource limits
recommend_worker_cpu_request: 250m
recommend_worker_cpu_limit: "1"
recommend_worker_memory_request: 1Gi
recommend_worker_memory_limit: 2Gi
```

After changing vars, deploy with `--tags apply` to update the manifests without rebuilding images.

Each worker pod has a fixed concurrency limit (hardcoded in `src/api/rcars/workers/settings.py`):

| Setting | Scan Worker | Recommend Worker |
|---|---|---|
| Concurrent jobs per pod | 5 | 3 |
| Default job timeout | 600s | 120s |

These per-pod limits cannot be changed via configuration. To increase total concurrency, increase the number of replicas. For example, setting `recommend_worker_replicas: 2` gives 6 concurrent recommendation queries (3 per pod × 2 pods).

Some tasks override the default timeout: stale check (3600s), workload scan (3600s), nightly pipeline (7200s).

The scan worker has higher resource limits because it runs `git clone` operations and loads the sentence-transformers model for embedding generation.

## Scan Deduplication

The scan worker deduplicates by `(showroom_url, showroom_ref)`. When multiple catalog items share the same Showroom content:

1. One representative item is scanned (cloned + analyzed by LLM)
2. The analysis and embeddings are propagated to all siblings
3. Each sibling gets its own `showroom_analysis` row and `embeddings` — every CI is independently searchable

Example: if `agd-v2.modernize-ocp-virt` has dev (ref=main), event (ref=v1.0.0), and prod (ref=v1.0.0):
- Dev is scanned independently (different ref)
- Event and prod share the same ref — one is scanned, the other gets propagated analysis

## Scheduled Maintenance Pipeline

The scan worker runs a nightly maintenance pipeline via arq's built-in cron support. By default it fires at **04:00 UTC** daily and chains five steps sequentially:

1. **Catalog Refresh** — syncs catalog metadata from all Babylon namespaces. For AgnosticD v2 items, this also extracts infrastructure metadata (config type, cloud provider, workloads, OCP/RHEL version, ACL groups) and stores them alongside the catalog data.
2. **Stale Check** — runs `git ls-remote` on all analyzed Showrooms, then clones only repos with new commits to compare content hashes
3. **Enqueue Re-Analysis** — queues analysis jobs for any items found stale or unanalyzed
4. **Workload Repo Scan** — scans the AgnosticD v2 workload collection repos on GitHub (`github.com/agnosticd/*`) for changes. If a repo has new commits since the last scan, clones it, reads the Ansible code for each role, and uses Claude Haiku to determine what product each role installs. Updates the workload mapping table with verified product names. Gated on `RCARS_WORKLOAD_SCAN_ENABLED` (default: true).
5. **Reporting Sync** — pulls provision, sales, and cost data from the RHDP reporting MCP server and computes retirement scores. Requires `RCARS_REPORTING_MCP_URL` and `RCARS_REPORTING_MCP_TOKEN` to be configured. See [Retirement Analysis](../architecture/retirement-analysis.md) for details.

Each step runs to completion before the next begins. If a step fails, the error is logged and the pipeline continues to the next step — a catalog refresh failure won't block stale checking or workload scanning.

**Step 3 is an enqueue, not a blocking wait.** The pipeline creates individual `run_analysis` jobs on the `arq:queue:scan` queue and then marks itself complete. The analysis jobs are picked up by the scan worker through its normal job processing — they are identical to analysis jobs created by clicking "Analyze" in the admin UI. This means the pipeline finishes in minutes (catalog refresh + stale check + workload scan), while the actual re-analysis of stale content may take much longer depending on how many items changed. You can monitor analysis progress on the Workers page or via the "Analyze" log window on the Catalog page.

**Step 4 uses change detection.** The workload scanner runs `git ls-remote` against each collection repo and compares the HEAD SHA to the last-scanned value stored in `workload_scan_state`. Repos that haven't changed are skipped entirely. This makes the step cheap to run daily — typically a few seconds when nothing has changed, a few minutes when repos need rescanning.

The pipeline creates a parent `maintenance` job plus sub-jobs for each step, all visible in the Workers page job history with `created_by: maintenance`. Progress messages stream to the Admin UI log window if an admin has it open.

### Changing the Schedule

Three environment variables control the schedule. They are read once at worker startup — changing them requires a worker restart (which happens automatically when you redeploy via Ansible).

| Variable | Default | Description |
|---|---|---|
| `RCARS_PIPELINE_ENABLED` | `true` | Set to `false` to disable the cron schedule entirely. Manual triggers still work. |
| `RCARS_PIPELINE_HOUR` | `4` | Hour (UTC, 0-23) for the nightly run |
| `RCARS_PIPELINE_MINUTE` | `0` | Minute (0-59) for the nightly run |
| `RCARS_WORKLOAD_SCAN_ENABLED` | `true` | Set to `false` to skip Step 4 (workload repo scan) in the pipeline |

To change the schedule, update `ansible/vars/common.yml` (applies to all environments) or `ansible/vars/<env>.yml` (per-environment override):

```yaml
pipeline_enabled: true
pipeline_hour: 4
pipeline_minute: 0
```

Then redeploy the scan worker so it picks up the new values:

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags build-api
```

The new schedule takes effect when the scan-worker pod restarts. The current schedule is visible in the Admin UI under **Scheduled Maintenance** (e.g. "Schedule: 04:00 UTC daily").

### Manual Trigger

The pipeline can also be triggered on-demand from the Admin UI ("Run Maintenance Now" button on the Catalog page) or via the API:

```bash
curl -X POST https://rcars-dev.apps.<domain>/api/v1/admin/run-maintenance \
  -H "Authorization: Bearer <token>"
```

### Multi-Worker Safety

arq's `unique=True` flag ensures the cron job runs only once even if multiple scan-worker replicas are deployed. Manual triggers via the API are not deduplicated — avoid clicking "Run Maintenance Now" while a scheduled run is in progress.

## Content Overlap Detection

The overlap detection system identifies catalog items that cover substantially the same material, helping curators consolidate duplicate content. It reuses the embeddings already generated during Showroom scanning — no additional LLM calls or external API calls are required.

### How It Works

Each analyzed Showroom lab has a 384-dimensional embedding stored in the `embeddings` table. These embeddings are numerical fingerprints generated by the all-MiniLM-L6-v2 sentence-transformer model during the scan phase. They capture the semantic meaning of each lab's content — topics, products, learning objectives — in a form that can be compared mathematically.

The overlap system computes **cosine similarity** between pairs of these embeddings. Cosine similarity measures the angle between two vectors: if two lab fingerprints point in the same direction (covering the same material), their cosine similarity approaches 1.0. If they cover unrelated topics, the similarity drops toward 0. Pairs scoring above the configured threshold (default: 0.75) are stored in the `content_similarity` table.

The comparison is scoped to a single stage at a time (prod, event, or dev) — controlled by the `stage` parameter. This ensures the report shows genuinely different labs with overlapping content, not expected duplicates like prod and dev variants of the same item. Published Virtual CIs are excluded because they contain no Showroom content of their own.

The full computation for ~100 prod items (~5,000 pairwise comparisons) runs in under a second using pgvector's `<=>` cosine distance operator inside PostgreSQL.

### Configuration

| Variable | Default | Description |
|---|---|---|
| `RCARS_SIMILARITY_THRESHOLD` | `0.75` | Minimum similarity score to store. Pairs below this are not saved. |
| `RCARS_SIMILARITY_HIGH_THRESHOLD` | `0.85` | Threshold for "high overlap" (likely duplicate) vs "related content" |

### API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/catalog/{ci_name}/similar` | any user | Similar items for a specific CI |
| `GET` | `/api/v1/admin/overlap` | admin | Global overlap report with all pairs |
| `POST` | `/api/v1/admin/compute-similarity?stage=prod` | admin | Trigger recomputation for a stage |

Query parameters: `min_score` (float, 0–1) overrides the threshold; `stage` (prod/event/dev, default: prod) selects which items to compare.

### CLI Usage

```bash
rcars compute-similarity                        # Prod items, default threshold
rcars compute-similarity --stage event          # Event items
rcars compute-similarity --stage dev            # Dev items
rcars compute-similarity --threshold 0.80       # Higher threshold = fewer pairs
```

The CLI command outputs a summary table showing total pairs, high overlap count, and related count.

### When to Recompute

Recompute after:

- A full scan or re-analysis (embeddings may have changed)
- Adding new catalog items with Showroom content
- Changing the similarity threshold or stage

The computation is idempotent — it clears the old results and writes fresh pairs each time.

## Monitoring

The admin dashboard at `/admin/workers` shows:

- **Worker Status** — auto-refreshes every 10 seconds. Summary bar with running, queued, complete, failed counts.
- **Recent Jobs** — last 50 jobs with type, CI name, status (color-coded), timestamps, and duration. Running/queued jobs sort to the top.

The `/admin/catalog` page shows:

- **Catalog Status** — total items, analyzed/unanalyzed/stale counts, last sync/analysis timestamps with CURRENT/STALE indicators
- **Scheduled Maintenance** — pipeline status, last run summary, "Run Maintenance Now" button

## How Jobs Flow

1. API receives a request (e.g., recommendation query or scan trigger)
2. API creates a job record in PostgreSQL (`status: queued`)
3. API enqueues the task to the appropriate Redis queue
4. Worker picks up the task, updates status to `running`
5. Worker publishes progress to Redis pub/sub (`job:{id}`)
6. API subscribes to the pub/sub channel, relays progress to browser via SSE
7. Worker completes, writes results to PostgreSQL, publishes `complete`

The API and worker never communicate directly. Redis is the sole channel.

## Troubleshooting

**Jobs stuck in `queued`:** Worker isn't running, or listening on wrong queue. Verify the correct worker deployment is up: `oc get pods -l component=scan-worker` or `component=recommend-worker`.

**Jobs stuck in `running`:** Worker crashed mid-job. Check worker logs (`oc logs deployment/rcars-scan-worker`). The job status in PostgreSQL stays `running` — a stale job detector can clean these up.

**Advisor queries not responding:** Check the recommend worker is running separately from the scan worker. If only the scan worker is up, advisor queries will never be picked up.

**LLM errors (429, quota exceeded):** Check Vertex AI quotas. The worker logs the full error. The job fails and can be retried.
