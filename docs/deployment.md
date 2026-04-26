# RCARS Deployment Guide

## Architecture

RCARS v2 runs as three separate components on OpenShift:

| Component | Image | What it does |
|---|---|---|
| `rcars-api` | `rcars-api:latest` | FastAPI JSON API, serves `/api/v1/*` |
| `rcars-scan-worker` | `rcars-api:latest` (same image) | arq worker for scan/analysis (queue: `arq:queue:scan`) |
| `rcars-recommend-worker` | `rcars-api:latest` (same image) | arq worker for advisor queries (queue: `arq:queue:recommend`) |
| `rcars-frontend` | `rcars-frontend:latest` | nginx serving the React SPA, proxies `/api/*` to the API service |

Workers are split into two deployments to prevent bulk scans from blocking advisor queries. Both use the same container image with different arq entrypoints.

Supporting infrastructure: PostgreSQL (pgvector), Redis 7, OAuth proxy.

---

## Prerequisites

- `oc` CLI logged into the target OpenShift cluster with cluster-admin (one-time bootstrap only)
- `ansible` with `kubernetes.core` collection installed
- Read-only kubeconfig for the Babylon cluster
- Vertex AI service account JSON key

### Install Ansible Dependencies

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

---

## One-Time Bootstrap

This creates a `rcars-mgmt-sa` service account for all future deployments. You need cluster-admin for this step only.

### Step 1. Log in with your personal account

```bash
oc login https://api.<your-cluster>:6443
oc whoami && oc whoami --show-server
```

### Step 2. Create your vars file

```bash
cp ansible/vars/dev.yml.example ansible/vars/dev.yml
```

Edit `ansible/vars/dev.yml` and fill in all `CHANGEME` values:

| Variable | How to get it |
|---|---|
| `pg_password` | `openssl rand -hex 16` |
| `oauth_client_secret` | `openssl rand -hex 16` |
| `oauth_cookie_secret` | `openssl rand -hex 16` |
| `cluster_domain` | `oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}'` |
| `babylon_kubeconfig_path` | Path to your Babylon read-only kubeconfig |
| `vertex_credentials_path` | Path to your GCP service account JSON key |
| `curator_emails` | YAML list of curator email addresses |
| `admin_emails` | YAML list of admin email addresses |

> **Identity note:** Email addresses must match the OpenShift SSO email format (e.g. `user@redhat.com`). The OAuth proxy passes `X-Forwarded-Email` — use this format, not the short username.

### Step 3. Bootstrap RBAC

```bash
ansible-playbook ansible/deploy.yml -e env=dev -e kubeconfig=~/.kube/config --tags mgmt-rbac
```

Verify:

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc whoami
# → system:serviceaccount:rcars-dev:rcars-mgmt-sa
```

### Step 4. Apply infrastructure

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags bootstrap
```

Creates: Secrets, PostgreSQL StatefulSet, Redis StatefulSet, ImageStreams, BuildConfigs, OAuthClient.

### Step 5. Deploy the application

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags update
```

This will:
1. Apply app manifests (API, Scan Worker, Recommend Worker, Frontend Deployments + Services + Route + OAuth Proxy)
2. Trigger Docker builds for API (~5 min) and frontend (~30s)
3. Wait for builds to complete and restart all deployments
4. Run database schema setup

### Step 6. Load initial data

After the app is running:

```bash
# Sync catalog from Babylon CRDs
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig \
  oc exec deployment/rcars-api -n rcars-dev -- python -c "from rcars.cli import cli; cli(['refresh'])"

# Analyze a few items to verify
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig \
  oc exec deployment/rcars-api -n rcars-dev -- python -c "from rcars.cli import cli; cli(['scan', '--max', '5'])"
```

Once verified, run a larger scan or use the Admin UI to analyze all content.

### Step 7. Verify

Open `https://rcars-dev.apps.<cluster-domain>`. After SSO login, you should see the RCARS advisor with the LCARS theme.

---

## Day-to-Day Operations

Set the kubeconfig:

```bash
export KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig
```

### Rebuild and deploy frontend only (~30s)

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags build-frontend
```

Or manually:

```bash
oc start-build rcars-frontend-build -n rcars-dev
# Wait for completion, then:
oc rollout restart deployment/rcars-frontend -n rcars-dev
```

### Rebuild and deploy API + workers (~5 min)

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags build-api
```

Or manually:

```bash
oc start-build rcars-api-build -n rcars-dev
# Wait for completion, then:
oc rollout restart deployment/rcars-api deployment/rcars-scan-worker deployment/rcars-recommend-worker -n rcars-dev
```

### Full update (build all + migrate)

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags update
```

### Apply config changes only (no build)

Re-applies manifests (env vars, replicas, resource limits) without triggering builds:

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags apply
```

---

## Managing Users

Curator and admin access is controlled by email lists in the Ansible vars file.

### Add a curator or admin

1. Edit `ansible/vars/dev.yml`:

```yaml
curator_emails:
  - existing-curator@redhat.com
  - new-curator@redhat.com

admin_emails:
  - existing-admin@redhat.com
  - new-admin@redhat.com
```

2. Apply the change:

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags apply
```

This updates the ConfigMap and restarts the API pod. The new user will have access on their next login.

### Remove a curator or admin

Remove their email from the list in `ansible/vars/dev.yml` and re-apply with `--tags apply`.

---

## CLI Commands

Run commands in the API pod:

```bash
# Catalog status
oc exec deployment/rcars-api -n rcars-dev -- rcars status

# Refresh catalog from Babylon
oc exec deployment/rcars-api -n rcars-dev -- rcars refresh

# Scan content (analyze Showrooms)
oc exec deployment/rcars-api -n rcars-dev -- rcars scan --max 10

# Show scan failures
oc exec deployment/rcars-api -n rcars-dev -- rcars status --failures

# Add a tag
oc exec deployment/rcars-api -n rcars-dev -- rcars tag ci-name.prod label flagship

# Set custom content path for non-standard Showroom
oc exec deployment/rcars-api -n rcars-dev -- rcars set-content-path ci-name.prod docs/labs/
```

---

## Check Logs

```bash
# API logs
oc logs deployment/rcars-api -n rcars-dev -f

# Scan worker logs
oc logs deployment/rcars-scan-worker -n rcars-dev -f

# Recommend worker logs
oc logs deployment/rcars-recommend-worker -n rcars-dev -f

# Frontend (nginx) logs
oc logs deployment/rcars-frontend -n rcars-dev -f

# OAuth proxy logs
oc logs deployment/rcars-oauth-proxy -n rcars-dev -f
```

---

## Restart Components

```bash
# Restart everything
oc rollout restart deployment/rcars-api deployment/rcars-scan-worker deployment/rcars-recommend-worker deployment/rcars-frontend -n rcars-dev

# Restart just the API + workers (e.g. after config change)
oc rollout restart deployment/rcars-api deployment/rcars-scan-worker deployment/rcars-recommend-worker -n rcars-dev

# Restart just the frontend
oc rollout restart deployment/rcars-frontend -n rcars-dev
```

---

## Troubleshooting

### Build fails

```bash
oc logs bc/rcars-api-build -n rcars-dev
oc logs bc/rcars-frontend-build -n rcars-dev
```

### Pod won't start

```bash
oc describe pod -l app=rcars,component=api -n rcars-dev
oc logs deployment/rcars-api -n rcars-dev
```

### Worker errors

```bash
# Scan worker (analysis failures, git clone errors)
oc logs deployment/rcars-scan-worker -n rcars-dev

# Recommend worker (advisor query failures)
oc logs deployment/rcars-recommend-worker -n rcars-dev
```

Common issues:
- **Redis connection refused** — check `RCARS_REDIS_URL` env var points to `rcars-redis:6379`
- **No Anthropic client** — verify Vertex AI credentials are mounted
- **Advisor queries stuck** — check recommend worker is running (`oc get pods -l component=recommend-worker`)

### Database connection issues

```bash
oc exec deployment/rcars-api -n rcars-dev -- \
  python -c "import os; print(os.environ.get('RCARS_DATABASE_URL', 'not set')[:40])"
```

### OAuth proxy issues

```bash
oc logs deployment/rcars-oauth-proxy -n rcars-dev
```
