# RCARS Deployment Guide

## Architecture

RCARS runs four application deployments plus infrastructure on OpenShift. For the full system design, component diagrams, data flow, and database schema, see the [System Design](../architecture/system-design.md) document.

| Component | Image | Purpose |
|---|---|---|
| `rcars-api` | `rcars-api:latest` | FastAPI JSON API (`/api/v1/*`), health probes |
| `rcars-scan-worker` | `rcars-api:latest` (same image) | arq worker: scan, refresh, stale check, nightly maintenance |
| `rcars-recommend-worker` | `rcars-api:latest` (same image) | arq worker: advisor recommendation queries |
| `rcars-frontend` | `rcars-frontend:latest` | nginx serving React SPA |
| `rcars-oauth-proxy` | `ose-oauth-proxy` | OpenShift OAuth proxy, upstream to frontend |

Infrastructure: PostgreSQL 16 (pgvector, 20Gi PVC), Redis 7 (1Gi PVC), OAuthClient.

Two environments share the same cluster: `rcars-dev` (main branch) and `rcars-prod` (production branch). Each has its own namespace, service account, database, and secrets. Ansible vars files (`ansible/vars/dev.yml`, `ansible/vars/prod.yml`) contain secrets and are gitignored.

---

## Local Development

The `dev-services.sh` script starts the full RCARS stack locally for development and testing. It runs the complete backend — not just the frontend.

### What it starts

| Service | How | Port |
|---|---|---|
| PostgreSQL 16 (pgvector) | Podman container | `localhost:5432` |
| Redis 7 | Podman container | `localhost:6379` |
| FastAPI API | uvicorn with `--reload` | `localhost:8080` |
| Scan worker | arq background process | — |
| Recommend worker | arq background process | — |
| React frontend | Vite dev server (proxies `/api` to API) | `localhost:3000` |

### Usage

```bash
./dev-services.sh start    # Start all services
./dev-services.sh stop     # Stop all services
./dev-services.sh restart  # Restart all services
./dev-services.sh status   # Check what's running
```

Dev mode sets `RCARS_DEV_USER=dev@redhat.com` with full admin access — no OAuth or K8s auth needed.

### Accessing locally

| Interface | URL |
|---|---|
| Frontend | `http://localhost:3000` |
| Swagger UI | `http://localhost:8080/api/v1/docs` |
| ReDoc | `http://localhost:8080/api/v1/redoc` |
| API directly | `http://localhost:8080/api/v1/...` |

### Data

The local stack starts with an empty database. To populate it with real catalog data, you need additional environment variables set **before** running `./dev-services.sh start`:

**Catalog data (required for `rcars refresh`):**

```bash
export RCARS_KUBECONFIG_PATH=~/.kube/my-babylon-kubeconfig
```

A kubeconfig with read access to the Babylon cluster. This lets `rcars refresh` pull catalog items from Babylon CRDs.

**LLM access (required for `rcars scan`):**

```bash
export RCARS_LITEMAAS_URL=https://litemaas.example.com/v1
export RCARS_LITEMAAS_API_KEY=your-api-key
```

LiteMaaS is the preferred LLM provider for local development. It provides an OpenAI-compatible API backed by Claude models. Without LLM credentials, content analysis (`rcars scan`) will fail — the catalog will be populated but items won't have analysis results.

**Reporting metrics (required for `rcars reporting-db sync`):**

These are only needed for the retirement dashboard and sales impact data. Not required for basic development.

Without any of these, the stack is still fully functional for frontend development, API testing, and Swagger UI exploration — responses will just be empty.

### Requirements

- Podman (for PostgreSQL and Redis containers)
- Python virtualenv at `~/.virtualenvs/rcars-v2` with the `rcars` package installed (`pip install -e ".[dev]"`)
- Node.js and npm (for the frontend dev server)

### Logs

All service logs go to `/tmp/`:

- `/tmp/rcars-api.log`
- `/tmp/rcars-scan-worker.log`
- `/tmp/rcars-recommend-worker.log`
- `/tmp/rcars-frontend.log`

---

## Prerequisites

- `oc` CLI with cluster-admin access (one-time bootstrap only)
- `ansible` with `kubernetes.core` collection: `ansible-galaxy collection install -r ansible/requirements.yml`
- Read-only kubeconfig for the Babylon cluster
- Vertex AI service account JSON key
- GitHub PAT with repo read access (repo is private)

---

## Playbook Tags

Every tag (except `mgmt-rbac`) applies all manifests first — infra secrets, BuildConfigs, deployments, routes, ConfigMaps — so infrastructure and app state never diverge. If nothing changed, Ansible skips the task. This eliminates bugs where a BuildConfig points to the wrong branch because manifests weren't updated.

| Tag | What it does | When to use |
|---|---|---|
| `full` | Apply manifests → build API → build frontend → migrate → smoke test | First-time deploy, full update, or when both API and frontend changed |
| `api` | Apply manifests → build API → migrate → smoke test | Backend-only code changes |
| `frontend` | Apply manifests → build frontend → smoke test | Frontend-only code changes |
| `apply-config` | Apply manifests only (no builds) | Config changes: user lists, env vars, secrets, resource limits |
| `mgmt-rbac` | Create management SA, RBAC, kubeconfig | One-time per environment |

Migrations run automatically after every API build. They execute on the new pod, so code and schema are always in sync.

---

## First-Time Setup (per environment)

### 1. Create vars file

```bash
cp ansible/vars/dev.yml.example ansible/vars/dev.yml
# or for prod:
cp ansible/vars/prod.yml.example ansible/vars/prod.yml
```

Fill in all values:

| Variable | How to get it |
|---|---|
| `pg_password` | `openssl rand -hex 16` |
| `oauth_client_secret` | `openssl rand -hex 16` |
| `oauth_cookie_secret` | `openssl rand -hex 16` |
| `cluster_domain` | `oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}'` |
| `babylon_kubeconfig_path` | Path to Babylon read-only kubeconfig |
| `vertex_credentials_path` | Path to GCP Vertex AI service account JSON key |
| `vertex_project_id` | GCP project ID for Vertex AI |
| `vertex_region` | GCP region (default: `us-east5`) |
| `curator_emails` | YAML list of curator-only emails |
| `admin_emails` | YAML list of admin emails (admins also get curator access) |

### 2. Bootstrap RBAC

Requires cluster-admin. Creates the management service account, RBAC, and a kubeconfig for future deploys.

```bash
ansible-playbook ansible/deploy.yml -e env=dev -e kubeconfig=~/.kube/config --tags mgmt-rbac
```

The playbook generates a management kubeconfig that Ansible uses for all subsequent operations. Store it securely — it grants namespace-scoped admin access.

For prod:

```bash
ansible-playbook ansible/deploy.yml -e env=prod -e kubeconfig=~/.kube/config --tags mgmt-rbac
```

### 3. Deploy

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags full
```

This does everything in the right order:
1. Creates namespace
2. Applies infra (Secrets, PostgreSQL, Redis, ImageStreams, BuildConfigs, OAuthClient)
3. Applies app manifests (Deployments, Services, Routes, ConfigMaps)
4. Builds API image (~5 min) and frontend image (~30s)
5. Runs database schema setup and migrations
6. Runs advisor smoke test to verify end-to-end functionality

### 4. Load initial data

After pods are running, exec into the API pod to run CLI commands. You must be logged into the cluster with `oc login` or have your `KUBECONFIG` set to the management kubeconfig.

```bash
# Sync catalog from Babylon CRDs
oc exec deployment/rcars-api -n rcars-dev -- rcars refresh

# Analyze a few items to verify the pipeline works
oc exec deployment/rcars-api -n rcars-dev -- rcars scan --max 5

# Check results
oc exec deployment/rcars-api -n rcars-dev -- rcars status
```

Once verified, run a full scan via the Admin UI or:

```bash
oc exec deployment/rcars-api -n rcars-dev -- rcars scan
```

### 5. Verify

Open `https://rcars-dev.apps.<cluster-domain>`. After SSO login you should see the RCARS advisor.

---

## Day-to-Day Operations

### Rebuild frontend only (~30s)

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags frontend
```

### Rebuild API + workers (~5 min)

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags api
```

### Full redeploy

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags full
```

### Update config only (no builds)

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags apply-config
```

### Configure scheduled maintenance

The scan worker includes a nightly maintenance pipeline (catalog refresh → stale check → re-analyze → workload scan → reporting sync) that runs at 04:00 UTC by default. To change the schedule or disable it, update `ansible/vars/<env>.yml`:

```yaml
pipeline_enabled: true   # set to false to disable
pipeline_hour: 4         # UTC hour (0-23)
pipeline_minute: 0       # minute (0-59)
```

Then redeploy the API:

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags api
```

### Promote to production

Production merges must go through a pull request:

```bash
gh pr create --base production --head main --title "Promote main to production"
# Wait for CodeRabbit review, then merge via GitHub
ansible-playbook ansible/deploy.yml -e env=prod --tags full
```

For targeted prod updates:

```bash
ansible-playbook ansible/deploy.yml -e env=prod --tags frontend
ansible-playbook ansible/deploy.yml -e env=prod --tags api
```

---

## Managing Users

Admin access implies curator access. Only list users in `curator_emails` if they need curator access but not admin.

Edit `ansible/vars/<env>.yml`:

```yaml
curator_emails:
  - curator-only@redhat.com

admin_emails:
  - admin-user@redhat.com
```

For ServiceAccount-based API access (e.g., from automated systems), add SA identities to the allowlist:

```yaml
sa_allowlist:
  - system:serviceaccount:my-namespace:my-sa
```

Then apply the updated config:

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags apply-config
```

This updates the deployment env vars and triggers a rollout — no image rebuilds or infrastructure changes.

---

## Running CLI Commands

All RCARS CLI commands are run inside the API pod via `oc exec`. You must be logged into the cluster (`oc login`) or have your `KUBECONFIG` set to the management service account kubeconfig.

```bash
oc exec deployment/rcars-api -n rcars-dev -- rcars <command>
```

For prod, use `-n rcars-prod`.

See the [CLI Admin Guide](cli-guide.md) for the full command reference.

Common examples:

```bash
# Catalog status
oc exec deployment/rcars-api -n rcars-dev -- rcars status

# Refresh catalog from Babylon
oc exec deployment/rcars-api -n rcars-dev -- rcars refresh

# Scan content (analyze Showrooms)
oc exec deployment/rcars-api -n rcars-dev -- rcars scan --max 10

# Show scan failures
oc exec deployment/rcars-api -n rcars-dev -- rcars status --failures

# Sync reporting data
oc exec deployment/rcars-api -n rcars-dev -- rcars reporting-db sync
```

---

## Operational Workflows

### Initial Setup (first deployment)

After the Ansible deploy completes and pods are running:

1. `oc exec deployment/rcars-api -n rcars-dev -- rcars refresh` — populate the catalog from Babylon CRDs.
2. `oc exec deployment/rcars-api -n rcars-dev -- rcars scan --max 5` — verify the AI pipeline works end-to-end with a small batch.
3. `oc exec deployment/rcars-api -n rcars-dev -- rcars status` — confirm analyzed count increased.
4. `oc exec deployment/rcars-api -n rcars-dev -- rcars scan` — full scan (may take 30–60 minutes depending on catalog size and parallelism).
5. `oc exec deployment/rcars-api -n rcars-dev -- rcars reporting-db sync` — pull reporting metrics for the retirement dashboard.

### Fresh Start (reset everything)

```bash
oc exec deployment/rcars-api -n rcars-dev -- rcars init-db --drop
oc exec deployment/rcars-api -n rcars-dev -- rcars refresh
oc exec deployment/rcars-api -n rcars-dev -- rcars scan
oc exec deployment/rcars-api -n rcars-dev -- rcars reporting-db sync
```

### Incremental Catalog Sync (routine)

```bash
oc exec deployment/rcars-api -n rcars-dev -- rcars refresh
oc exec deployment/rcars-api -n rcars-dev -- rcars scan
```

`refresh` picks up new and changed items. `scan` analyzes anything new or stale. Items that were already analyzed and whose content has not changed are skipped automatically.

### Checking for Content Updates

Stale detection is triggered from the Admin UI or via the API (`POST /api/v1/analysis/check-stale`). It clones each analyzed Showroom and compares content hashes. Items whose content has changed are marked stale. The subsequent `scan` picks up stale items automatically alongside any new ones.

### Force Full Rescan

Use this when the analysis prompt has changed or when you want to ensure all items reflect the current model's output. Full rescans are triggered from the Admin UI via "Re-Analyze All" (`POST /api/v1/analysis/rescan-all`), which marks all items as stale and enqueues them for re-analysis.

### Debugging a Failed Item

```bash
oc exec deployment/rcars-api -n rcars-dev -- rcars status --failures
```

Common failure causes:

| Error Class | Meaning |
|---|---|
| `jinja_url` | Showroom URL contains unresolved Jinja2 template variables |
| `private_repo` | Git repository requires authentication |
| `http_404` | Repository URL returns a 404 |
| `clone_failed` | git clone failed (timeout, network, or other git error) |
| `missing_antora` | Repository does not follow the standard Antora layout |
| `no_content` | No substantive content files found after filtering boilerplate |
| `parse_error` | LLM response could not be parsed as JSON |
| `timeout` | Operation exceeded the timeout limit |

To re-analyze a specific item, use the Browse page's "Re-analyze" button (curator access required) or the API:

```bash
curl -X POST https://rcars-dev.apps.<domain>/api/v1/analysis/<ci-name> \
  -H "Authorization: Bearer <token>"
```

Scan errors are also visible in the Admin page of the web UI.

### Testing Recommendations After a Scan

Use the Advisor page in the web UI to test recommendations. If results look wrong — poor scores, irrelevant items — check that `rcars status` shows a reasonable analyzed count and that embeddings are present. If no embeddings exist, the recommendation engine has no candidates to rank.

---

## Troubleshooting

### Check logs

```bash
oc logs deployment/rcars-api -n rcars-dev -f
oc logs deployment/rcars-scan-worker -n rcars-dev -f
oc logs deployment/rcars-recommend-worker -n rcars-dev -f
oc logs deployment/rcars-frontend -n rcars-dev -f
oc logs deployment/rcars-oauth-proxy -n rcars-dev -f
```

### Build fails

```bash
oc logs bc/rcars-api-build -n rcars-dev
oc logs bc/rcars-frontend-build -n rcars-dev
```

### Pod won't start

```bash
oc describe pod -l app=rcars,component=api -n rcars-dev
oc get events -n rcars-dev --sort-by='.lastTimestamp' | tail -20
```

### Common issues

- **Pod stuck in ContainerCreating** — usually a missing Secret (check `oc describe pod`)
- **Redis connection refused** — verify Redis pod is running
- **No Anthropic client** — verify Vertex AI credentials are mounted
- **Advisor queries stuck** — check recommend worker is running
- **OAuth redirect loop** — verify OAuthClient name matches env (`rcars-dev` or `rcars-prod`)
