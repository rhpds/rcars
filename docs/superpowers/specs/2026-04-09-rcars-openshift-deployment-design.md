# RCARS OpenShift Deployment Design

> **Date:** 2026-04-09
> **Status:** Approved
> **Scope:** Containerized deployment of RCARS to OpenShift with Ansible-managed manifests, OAuth proxy auth, PostgreSQL+pgvector, Alembic migrations, and GitHub-triggered S2I builds.

---

## 1. Overview

Deploy RCARS (FastAPI web UI + CLI) to OpenShift on the `your-cluster.dal12.infra.demo.redhat.com` cluster. Two namespaces: `rcars-dev` (builds from `main`) and `rcars-prod` (builds from `production` branch). Follows the labagator deployment pattern — Ansible playbook with Jinja2-rendered manifests, no Helm dependency.

**Target cluster:** your-cluster (separate from Babylon clusters)
**Auth:** OpenShift OAuth proxy with `auth.redhat.com/GPTEInternal` SSO
**Database:** PostgreSQL 16 with pgvector extension
**Builds:** Docker strategy BuildConfig with GitHub webhook auto-trigger
**Migrations:** Alembic, run via `k8s_exec` during deployment
**Model:** sentence-transformers/all-MiniLM-L6-v2 baked into container image

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│  rcars-dev / rcars-prod namespace                   │
│                                                     │
│  ┌──────────────┐     ┌──────────────────────────┐  │
│  │ OAuth Proxy  │────▶│ RCARS App (FastAPI:8080)  │  │
│  │ (port 8080)  │     │   - web UI                │  │
│  │ pass-user-   │     │   - advisor/curate/admin   │  │
│  │ headers=true │     │   - CLI commands available │  │
│  └──────┬───────┘     └──────────┬───────────────┘  │
│         │                        │                   │
│         │ Route                  │ psycopg3          │
│         ▼                        ▼                   │
│  ┌──────────────┐     ┌──────────────────────────┐  │
│  │ OCP Route    │     │ PostgreSQL 16 + pgvector  │  │
│  │ (edge TLS)   │     │ (StatefulSet + PVC 5Gi)   │  │
│  └──────────────┘     └──────────────────────────┘  │
└─────────────────────────────────────────────────────┘

External connections (from RCARS app pod):
  → Babylon cluster (read-only kubeconfig) — CatalogItem + AgnosticVComponent CRDs
  → Vertex AI (GCP credentials JSON) — Claude Sonnet for analysis/ranking
  → GitHub (Showroom repos) — git clone during rcars scan
  → HuggingFace (NOT at runtime — model baked into image)
```

### Auth Flow

User → Route → OAuth Proxy (OpenShift SSO via `auth.redhat.com/GPTEInternal`) → sets `X-Forwarded-User: user@redhat.com` → RCARS `get_current_user()` reads it. No `RCARS_DEV_USER` env var needed on OpenShift.

Curator and admin access controlled by `RCARS_CURATOR_EMAILS` and `RCARS_ADMIN_EMAILS` env vars (comma-separated email lists in ConfigMap or deployment env).

---

## 3. File Structure

```
ansible/
├── deploy.yml                    # Main playbook
├── templates/
│   └── manifests.yaml.j2        # All k8s resources (Jinja2 template)
├── tasks/
│   ├── namespace.yml             # Create namespace
│   ├── apply-manifests.yml       # Render template + oc apply
│   ├── wait-for-builds.yml       # Wait for BuildConfig completion + rollout restart
│   └── webhooks.yml              # Register GitHub webhook URLs
└── vars/
    ├── common.yml                # Shared: image names, ports, labels, resource limits
    ├── dev.yml.example           # Dev vars template (gitignored when filled)
    └── prod.yml.example          # Prod vars template (gitignored when filled)

alembic/                          # Database migrations
├── alembic.ini
├── env.py
└── versions/
    └── 001_initial_schema.py     # Baseline: full current schema

Dockerfile                        # Updated: bake sentence-transformers model
```

---

## 4. Kubernetes Resources (manifests.yaml.j2)

All resources rendered from one Jinja2 template, applied via `oc apply -f`.

### Identity & Auth
- **ServiceAccount: `rcars-oauth`** — with `serviceaccounts.openshift.io/oauth-redirecturi` annotation
- **OAuthClient** — registered with OpenShift OAuth server, `clientID: rcars-{{ env }}`
- **Secret: `rcars-oauth-proxy-secret`** — client-id, client-secret, session cookie secret

### Credentials
- **Secret: `rcars-babylon-kubeconfig`** — read-only kubeconfig for Babylon cluster(s), mounted as file at `/etc/rcars/kubeconfig`
- **Secret: `rcars-vertex-credentials`** — GCP Vertex AI JSON key, mounted as file at `/etc/rcars/vertex-credentials.json`
- **Secret: `rcars-postgresql`** — POSTGRESQL_USER, POSTGRESQL_PASSWORD, POSTGRESQL_DATABASE

### Database
- **StatefulSet: `rcars-postgresql`**
  - Image: `pgvector/pgvector:pg16`
  - Env from `rcars-postgresql` secret
  - PVC: `rcars-postgresql-data`, 5Gi, RWO, `ocs-storagecluster-ceph-rbd`
- **Service: `rcars-postgresql`** — port 5432, ClusterIP

### Application
- **Deployment: `rcars`**
  - Image: from ImageStream `rcars:latest`
  - Replicas: 1
  - Port: 8080
  - Volume mounts:
    - `/etc/rcars/kubeconfig` from babylon-kubeconfig secret
    - `/etc/rcars/vertex-credentials.json` from vertex-credentials secret
  - Environment variables:
    - `RCARS_DATABASE_URL` — `postgresql://$(PG_USER):$(PG_PASSWORD)@rcars-postgresql:5432/$(PG_DATABASE)` (constructed from secret refs)
    - `RCARS_KUBECONFIG` — `/etc/rcars/kubeconfig`
    - `ANTHROPIC_VERTEX_PROJECT_ID` — from vars
    - `CLOUD_ML_REGION` — from vars
    - `GOOGLE_APPLICATION_CREDENTIALS` — `/etc/rcars/vertex-credentials.json`
    - `RCARS_CURATOR_EMAILS` — from vars
    - `RCARS_ADMIN_EMAILS` — from vars
    - `RCARS_STALE_DAYS` — from vars (default 3)
    - `RCARS_CLONE_DIR` — `/tmp` (emptyDir for git clones during scan)
    - `HF_HOME` — `/opt/app-root/.cache/huggingface` (baked-in model)
  - Liveness: HTTP GET `/advisor` (follows redirect from `/`)
  - Readiness: HTTP GET `/advisor`
- **Service: `rcars-service`** — port 8080, ClusterIP

### OAuth Proxy
- **Deployment: `rcars-oauth-proxy`**
  - Image: `registry.redhat.io/openshift4/ose-oauth-proxy-rhel9:latest`
  - Args:
    - `-provider=openshift`
    - `-http-address=:8080`
    - `-upstream=http://rcars-service:8080/`
    - `-openshift-service-account=rcars-oauth`
    - `-pass-user-headers=true`
    - `-skip-auth-regex=^/static/` (CSS/JS don't need auth)
    - `-upstream-timeout=180s` (recommend() calls can take 60s+)
  - Volume mounts: oauth-proxy-secret, TLS cert
- **Service: `rcars-oauth-proxy-service`** — port 8080

### Networking
- **Route: `rcars`** — `rcars-{{ env }}.apps.your-cluster.example.com` → oauth-proxy-service, edge TLS with redirect

### Build
- **ImageStream: `rcars`** — stores built images in internal registry
- **BuildConfig: `rcars`**
  - Docker strategy, `dockerfilePath: Dockerfile`
  - Source: Git, `uri: https://github.com/{{ github_repo }}.git`, `ref: {{ git_ref }}` (main for dev, production for prod)
  - Source secret: `rcars-github-source` (for private repo access)
  - Trigger: GitHub webhook + ConfigChange
- **Secret: `rcars-webhook`** — GitHub webhook secret
- **Secret: `rcars-github-source`** — GitHub token for repo access (if private)

---

## 5. Ansible Playbook

### deploy.yml

```
Playbook: Deploy RCARS to OpenShift

Pre-tasks:
  - Validate required vars (env, kubeconfig, pg_password, etc.)
  - Verify kubeconfig exists
  - Verify cluster connectivity

Tasks (with tags):
  1. Create namespace                          [namespace, apply, update]
  2. Apply manifests (render + oc apply)       [apply, update]
  3. Wait for builds + rollout restart         [builds, apply, update]
  4. Run Alembic migrations (k8s_exec)         [migrate, apply, update]
  5. Sync GitHub webhook URLs                  [webhooks, builds, apply, update]

Post-tasks:
  - Print deployment summary (namespace, URL, pod status)
```

### Usage

```bash
# Full deploy (empty namespace → running app)
ansible-playbook ansible/deploy.yml -e env=dev

# Code update (after push to main — apply + build + migrate + webhooks)
ansible-playbook ansible/deploy.yml -e env=dev --tags update

# Just wait for builds and restart
ansible-playbook ansible/deploy.yml -e env=dev --tags builds

# Just run migrations
ansible-playbook ansible/deploy.yml -e env=dev --tags migrate
```

### Vars

**common.yml** (committed):
```yaml
app_name: rcars
app_port: 8080
pg_image: pgvector/pgvector:pg16
pg_port: 5432
pg_pvc_size: 5Gi
pg_storage_class: ocs-storagecluster-ceph-rbd
oauth_proxy_image: registry.redhat.io/openshift4/ose-oauth-proxy-rhel9:latest
cluster_domain: apps.your-cluster.example.com
vertex_project_id: <gcp-project>
vertex_region: us-east5
```

**dev.yml / prod.yml** (gitignored, created from .example):
```yaml
env: dev
target_namespace: rcars-dev
kubeconfig: ~/.kube/your-cluster
git_ref: main
frontend_host: rcars-dev.apps.your-cluster.example.com
pg_password: <generated>
pg_user: rcars
pg_database: rcars
babylon_kubeconfig_path: ~/.kube/babylon-readonly
vertex_credentials_json: <contents of GCP JSON key>
oauth_client_secret: <generated>
oauth_cookie_secret: <generated>
curator_emails: "your-email@redhat.com"
admin_emails: "your-email@redhat.com"
github_repo: rhpds/rcars-advisory
github_token: <PAT for webhook registration>
webhook_secret: <generated>
```

---

## 6. Dockerfile Changes

Two additions to the existing multi-stage Dockerfile:

**Builder stage** — after pip install, bake in the sentence-transformers model:
```dockerfile
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

**Runtime stage** — copy the cached model:
```dockerfile
COPY --from=builder /opt/app-root/.cache/huggingface /opt/app-root/.cache/huggingface
ENV HF_HOME=/opt/app-root/.cache/huggingface
```

Everything else stays as-is (UBI 9, git-core, port 8080, user 1001).

---

## 7. Alembic Migration Setup

Replace the current ad-hoc `ALTER TABLE ADD COLUMN IF NOT EXISTS` in `create_schema()` with proper Alembic:

- **alembic.ini** — reads `RCARS_DATABASE_URL` from environment
- **Initial migration (001)** — current full schema as baseline (all tables, indexes, pgvector extension)
- **App startup** — does NOT run migrations automatically
- **Deployment** — Ansible runs `alembic upgrade head` via `k8s_exec` on the app pod after deploy (same as labagator)
- **Local dev** — `create_schema()` remains as a convenience for local testing; calls `alembic upgrade head` programmatically

Future schema changes become new migration files instead of ad-hoc ALTER TABLE statements.

---

## 8. What This Design Does NOT Include (Deferred)

- **CronJobs for scheduled scan/refresh** — trigger manually from admin page or CLI for now. Add CronJobs when scan frequency is established.
- **Horizontal scaling** — single replica. Add HPA if load warrants it.
- **Session persistence** — in-memory sessions. Add DB-backed sessions when needed.
- **Monitoring/alerting** — no ServiceMonitor or PrometheusRule. Add when operational patterns are clear.
- **Backup/restore** — no automated PostgreSQL backup. Add when data is critical.

---

## 9. Deployment Flow

### Initial Deploy (from scratch)

```
1. Create vars/dev.yml from vars/dev.yml.example
   - Fill in kubeconfig paths, secrets, credentials
2. ansible-playbook ansible/deploy.yml -e env=dev
   - Creates namespace
   - Applies all manifests (secrets, postgres, app, oauth, buildconfig, route)
   - BuildConfig triggers first build from GitHub
   - Waits for build to complete
   - Runs Alembic migration (creates schema)
   - Registers GitHub webhook
3. Open https://rcars-dev.apps.your-cluster.example.com
   - OAuth proxy redirects to SSO login
   - After auth, X-Forwarded-User header set
   - RCARS loads
```

### Code Update (push to main)

```
1. Developer pushes to main branch
2. GitHub webhook triggers BuildConfig
3. OpenShift builds new image from Dockerfile
4. Developer runs: ansible-playbook deploy.yml -e env=dev --tags update
   - Waits for build completion
   - Restarts deployment (picks up new image)
   - Runs any new Alembic migrations
   - Updates webhook URL if changed
```

### Promotion to Prod

```
1. Merge main → production branch
2. ansible-playbook deploy.yml -e env=prod --tags update
   - Same flow but targets rcars-prod namespace
   - Builds from production branch
```
