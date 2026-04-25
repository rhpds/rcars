---
title: Worker Management
description: How to run, scale, and monitor arq workers
---

# Worker Management

Workers are long-running processes that pick up jobs from Redis queues. They handle all LLM operations (recommendations, analysis, scanning) so the API stays responsive.

## Running Workers

Workers use the same container image as the API — different entrypoint, same codebase.

```bash
# Start a generic worker (handles all queues)
arq rcars.workers.WorkerSettings

# Start a worker for specific queues
arq rcars.workers.WorkerSettings --queue recommend
arq rcars.workers.WorkerSettings --queue analyze
arq rcars.workers.WorkerSettings --queue ops
```

## Queues

| Queue | Tasks | Profile |
|---|---|---|
| `recommend` | Recommendation pipeline (vector → triage → rationale) | LLM-heavy, user-facing |
| `analyze` | Showroom analysis + embedding generation | LLM + I/O heavy |
| `ops` | Catalog refresh, stale check | Lightweight |

## Scaling

Workers are stateless — add replicas by deploying more pods with the same image. In Ansible vars:

```yaml
worker_replicas: 2  # or more
```

The admin dashboard at `/admin` shows queue depths. If jobs consistently back up in a queue, add a worker.

## Monitoring

The admin dashboard shows:

- **Queue depths** per queue — are jobs waiting?
- **Active jobs** — what's running right now?
- **Recent failures** — what went wrong?
- **Job history** — status, duration, who triggered

## How Jobs Flow

1. API receives a request (e.g., recommendation query)
2. API creates a job record in PostgreSQL (`status: queued`)
3. API enqueues the task in Redis
4. Worker picks up the task, updates status to `running`
5. Worker publishes progress to Redis pub/sub (`job:{id}`)
6. API subscribes to the pub/sub channel, relays progress to browser via SSE
7. Worker completes, writes results to PostgreSQL, publishes `complete`

The API and worker never communicate directly. Redis is the sole channel.

## Troubleshooting

**Jobs stuck in `queued`:** Worker isn't running, or listening on wrong queue. Check `arq` process and queue name.

**Jobs stuck in `running`:** Worker crashed mid-job. Check worker logs (`/tmp/rcars-worker.log` locally, or `oc logs` on OpenShift). The job status in PostgreSQL stays `running` — a stale job detector can clean these up.

**LLM errors (429, quota exceeded):** Check Vertex AI quotas. The worker logs the full error. The job fails and can be retried.
