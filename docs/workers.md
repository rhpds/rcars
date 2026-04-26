---
title: Worker Management
description: How to run, scale, and monitor arq workers
---

# Worker Management

Workers are long-running processes that pick up jobs from Redis queues. They are split into two deployments to prevent bulk scans from blocking user-facing advisor queries.

## Worker Deployments

| Deployment | Entry Point | Queue | Tasks |
|---|---|---|---|
| `rcars-scan-worker` | `arq rcars.workers.WorkerSettings` | `arq:queue:scan` | `run_analysis`, `run_catalog_refresh`, `run_stale_check` |
| `rcars-recommend-worker` | `arq rcars.workers.RecommendWorkerSettings` | `arq:queue:recommend` | `run_recommendation` |

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

Workers are stateless — add replicas by deploying more pods. In Ansible vars:

```yaml
scan_worker_replicas: 2      # for bulk scan throughput
# recommend worker is always 1 replica (lightweight)
```

## Scan Deduplication

The scan worker deduplicates by `(showroom_url, showroom_ref)`. When multiple catalog items share the same Showroom content:

1. One representative item is scanned (cloned + analyzed by LLM)
2. The analysis and embeddings are propagated to all siblings
3. Each sibling gets its own `showroom_analysis` row and `embeddings` — every CI is independently searchable

Example: if `agd-v2.modernize-ocp-virt` has dev (ref=main), event (ref=v1.0.0), and prod (ref=v1.0.0):
- Dev is scanned independently (different ref)
- Event and prod share the same ref — one is scanned, the other gets propagated analysis

## Monitoring

The admin dashboard at `/admin` shows:

- **Queue depths** per queue — are jobs waiting?
- **Active jobs** — what's running right now, with CI name
- **Recent failures** — what went wrong, with CI name and error class
- **Job history** — status, duration, who triggered

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
