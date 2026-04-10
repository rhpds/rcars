# RCARS Deployment Guide

## Prerequisites

- `oc` CLI logged into the target OpenShift cluster with cluster-admin (for the one-time bootstrap)
- `ansible` with `kubernetes.core` collection installed
- Read-only kubeconfig for the Babylon cluster
- Vertex AI service account JSON key
- GitHub personal access token (for private repo access and webhook registration)

### Install Ansible Dependencies

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

---

## One-Time Bootstrap (first deploy only)

This creates a `rcars-mgmt-sa` service account with minimum permissions for all future deployments. You need cluster-admin for this step only — after this, the playbook runs as the service account.

### Step 1. Log in with your personal account

```bash
oc login https://api.<your-cluster>:6443
```

Confirm you're on the right cluster:

```bash
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
| `webhook_secret` | `openssl rand -hex 16` |
| `cluster_domain` | `oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}'` |
| `babylon_kubeconfig_path` | path to your Babylon read-only kubeconfig |
| `vertex_credentials_path` | path to your GCP service account JSON key (e.g. `~/devel/secrets/gcp-vertex-key.json`) — project ID is read from the file automatically |
| `github_token` | GitHub PAT with `repo` scope |
| `curator_emails` / `admin_emails` | YAML lists of email addresses |

Leave `kubeconfig` as-is (`~/devel/secrets/rcars-mgmt.kubeconfig`) — the next step creates that file.

### Step 3. Bootstrap RBAC and generate the mgmt kubeconfig

Run with your personal kubeconfig, passing it explicitly:

```bash
ansible-playbook ansible/deploy.yml -e env=dev -e kubeconfig=~/.kube/config --tags mgmt-rbac
```

This creates:
- Namespaces `rcars-dev` and `rcars-prod`
- Service account `rcars-mgmt-sa` in `rcars-dev`
- ClusterRole `rcars-mgmt` (namespace lifecycle + OAuthClient management)
- ClusterRoleBinding and admin RoleBinding in `rcars-dev`
- Long-lived token Secret `rcars-mgmt-sa-token`
- Kubeconfig at `~/devel/secrets/rcars-mgmt.kubeconfig`

Verify it works:

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc whoami
# → system:serviceaccount:rcars-dev:rcars-mgmt-sa

KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc get ns rcars-dev rcars-prod
```

---

## Initial Application Deployment

### Step 4. Run the full deploy

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags update
```

This uses the mgmt kubeconfig from your `dev.yml` and will:
1. Apply all secrets, deployments, services, routes, ImageStream, and BuildConfig
2. Trigger the first Docker build from GitHub (~3–5 minutes)
3. Wait for the build to complete and roll out the new image
4. Run Alembic database migrations
5. Display the GitHub webhook URL

### Step 5. Configure GitHub webhook

The playbook prints the webhook URL at the end. Add it to your GitHub repo:

1. Go to `https://github.com/<your-repo>/settings/hooks`
2. Click "Add webhook"
3. Paste the URL from the playbook output
4. Content type: `application/json`
5. Secret: the `webhook_secret` value from your vars file
6. Events: "Just the push event"

### Step 6. Verify

Open the URL from `frontend_host` in your vars file (e.g. `https://rcars-dev.apps.<cluster-domain>`).

You should see the OpenShift SSO login page. After authenticating, RCARS loads with your email in the header.

---

## Day-to-Day Operations

All `oc` commands should use the mgmt kubeconfig:

```bash
export KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig
```

Or prefix each command inline: `KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc ...`

### Code update (after push to main)

Webhooks trigger builds automatically. Once the build completes, to run migrations and confirm rollout:

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags update
```

### Apply config/secret changes only (no build)

Re-applies manifests, runs migrations, shows webhook URL — skips the build entirely:

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags apply
```

### Just run migrations

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags migrate
```

### Restart the app

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc rollout restart deployment/rcars -n rcars-dev
```

### Check logs

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc logs deployment/rcars -n rcars-dev -f
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc logs deployment/rcars-oauth-proxy -n rcars-dev -f
```

### Run a command on the pod

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc exec deployment/rcars -n rcars-dev -- rcars status
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc exec deployment/rcars -n rcars-dev -- rcars refresh
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc exec deployment/rcars -n rcars-dev -- rcars scan --max 5
```

---

## Production Deployment

### Bootstrap prod RBAC (one-time)

The mgmt SA already exists but needs an admin RoleBinding in `rcars-prod`. Run the bootstrap for prod with your personal kubeconfig:

```bash
ansible-playbook ansible/deploy.yml -e env=prod -e kubeconfig=~/.kube/config --tags mgmt-rbac
```

### Create prod vars file

```bash
cp ansible/vars/prod.yml.example ansible/vars/prod.yml
# Edit with production values — same fields as dev.yml
```

### Deploy to prod

```bash
ansible-playbook ansible/deploy.yml -e env=prod --tags update
```

Production builds from the `production` branch. Promote by merging `main → production` — the webhook triggers the build automatically.

---

## Troubleshooting

### Build fails

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc logs bc/rcars -n rcars-dev
```

### Pod won't start

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc describe pod -l app=rcars,component=app -n rcars-dev
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc logs deployment/rcars -n rcars-dev
```

### Database connection issues

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc exec deployment/rcars -n rcars-dev -- \
  python -c "import os; print(os.environ.get('RCARS_DATABASE_URL', 'not set')[:40])"
```

### OAuth proxy issues

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig oc logs deployment/rcars-oauth-proxy -n rcars-dev
```

### Re-run RBAC bootstrap (e.g. token expired or kubeconfig lost)

```bash
ansible-playbook ansible/deploy.yml -e env=dev -e kubeconfig=~/.kube/config --tags mgmt-rbac
```

The mgmt-rbac task is fully idempotent — it's safe to run at any time.
