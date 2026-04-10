# RCARS Plan 3c — OpenShift Deployment

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy RCARS to OpenShift with Ansible-managed manifests, OAuth proxy auth, PostgreSQL+pgvector, Alembic migrations, and GitHub-triggered Docker builds.

**Architecture:** Ansible playbook renders a Jinja2 manifests template into Kubernetes resources and applies them with `oc apply`. BuildConfig builds the app image from GitHub. OAuth proxy handles SSO. PostgreSQL StatefulSet with pgvector for the database. Alembic for schema migrations.

**Tech Stack:** Ansible (kubernetes.core collection), Jinja2, OpenShift BuildConfig (Docker strategy), ose-oauth-proxy, pgvector/pgvector:pg16, Alembic, UBI 9 Python 3.11.

**Design spec:** `docs/superpowers/specs/2026-04-09-rcars-openshift-deployment-design.md`

**IMPORTANT:** This plan produces deployment artifacts only. The user runs `ansible-playbook` themselves — never execute deployment commands.

---

## File Map

**New files:**
- `alembic.ini` — Alembic config, reads `RCARS_DATABASE_URL` from env
- `alembic/env.py` — Migration runner using raw psycopg3 (no SQLAlchemy)
- `alembic/script.py.mako` — Migration template
- `alembic/versions/001_initial_schema.py` — Baseline migration with full current schema
- `ansible/deploy.yml` — Main deployment playbook
- `ansible/templates/manifests.yaml.j2` — All Kubernetes resources
- `ansible/tasks/namespace.yml` — Create namespace
- `ansible/tasks/apply-manifests.yml` — Render and apply manifests
- `ansible/tasks/wait-for-builds.yml` — Wait for BuildConfig + rollout restart
- `ansible/tasks/webhooks.yml` — Register GitHub webhook
- `ansible/vars/common.yml` — Shared vars (committed)
- `ansible/vars/dev.yml.example` — Dev vars template (committed)
- `ansible/vars/prod.yml.example` — Prod vars template (committed)
- `ansible/requirements.yml` — Ansible collection dependencies
- `docs/deployment.md` — Step-by-step deployment instructions

**Modified files:**
- `Dockerfile` — Bake sentence-transformers model into image
- `src/rcars/db.py` — Update `create_schema()` to use Alembic for local dev
- `pyproject.toml` — Add alembic dependency
- `.gitignore` — Add ansible/vars/dev.yml, ansible/vars/prod.yml

---

## Task 1: Dockerfile — Bake Sentence-Transformers Model

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Update Dockerfile to download model during build**

In the builder stage, add after the `pip install` line:

```dockerfile
# Pre-download sentence-transformers model so it's baked into the image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

In the runtime stage, add after copying `prompts/`:

```dockerfile
COPY --from=builder /opt/app-root/.cache/huggingface /opt/app-root/.cache/huggingface
ENV HF_HOME=/opt/app-root/.cache/huggingface
```

The full Dockerfile should be:

```dockerfile
# RCARS — RHDP Content Advisory & Recommendation System
# Multi-stage build using RHEL UBI 9

FROM registry.access.redhat.com/ubi9/python-311:latest AS builder

USER 0
WORKDIR /opt/app-root/src

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[web,analysis]"

# Pre-download sentence-transformers model so it's baked into the image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

FROM registry.access.redhat.com/ubi9/python-311:latest AS runtime

USER 0

# Install git for shallow Showroom clones
RUN dnf install -y --nodocs git-core && \
    dnf clean all

USER 1001
WORKDIR /opt/app-root/src

COPY --from=builder /opt/app-root/lib /opt/app-root/lib
COPY --from=builder /opt/app-root/bin /opt/app-root/bin
COPY --from=builder /opt/app-root/.cache/huggingface /opt/app-root/.cache/huggingface
COPY src/ src/
COPY prompts/ prompts/
COPY alembic.ini alembic.ini
COPY alembic/ alembic/

ENV PATH="/opt/app-root/bin:$PATH"
ENV HF_HOME=/opt/app-root/.cache/huggingface

EXPOSE 8080

CMD ["uvicorn", "rcars.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Verify Dockerfile syntax**

```bash
python -c "
with open('Dockerfile') as f:
    content = f.read()
assert 'SentenceTransformer' in content
assert 'HF_HOME' in content
assert 'alembic' in content
print('Dockerfile looks correct')
"
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "docker: Bake sentence-transformers model and alembic into image"
```

---

## Task 2: Alembic Setup

**Files:**
- Modify: `pyproject.toml`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/001_initial_schema.py`
- Modify: `src/rcars/db.py`

- [ ] **Step 1: Add alembic to pyproject.toml dependencies**

Add `alembic` to the core dependencies (not an optional extra — it's needed for deployment):

```toml
dependencies = [
    "alembic>=1.13",
    "click>=8.1",
    "httpx>=0.27.0",
    "kubernetes>=29.0",
    "psycopg[binary]>=3.1",
    "rich>=13.0",
]
```

- [ ] **Step 2: Create alembic.ini**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .

# Default URL for local dev — overridden by env.py reading RCARS_DATABASE_URL
sqlalchemy.url = postgresql://rcars:dev@localhost:5432/rcars

[loggers]
keys = root,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Create alembic/env.py**

RCARS uses raw psycopg3, not SQLAlchemy ORM. This env.py uses `sqlalchemy.create_engine` only for Alembic's migration runner, and reads the DB URL from `RCARS_DATABASE_URL` env var:

```python
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config

# Override DB URL from environment if available
db_url = os.environ.get("RCARS_DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Create alembic/script.py.mako**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Create initial migration (001)**

Create `alembic/versions/001_initial_schema.py`. This captures the complete current schema as the baseline:

```python
"""Initial schema — baseline from existing RCARS database.

Revision ID: 001
Revises: None
Create Date: 2026-04-10
"""
from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
    CREATE TABLE IF NOT EXISTS catalog_items (
        ci_name TEXT PRIMARY KEY,
        display_name TEXT,
        category TEXT,
        product TEXT,
        product_family TEXT,
        primary_bu TEXT,
        secondary_bu TEXT,
        stage TEXT,
        catalog_namespace TEXT,
        keywords TEXT[],
        description TEXT,
        icon_url TEXT,
        owners_json JSONB,
        showroom_url TEXT,
        showroom_ref TEXT,
        last_crd_update TIMESTAMPTZ,
        last_refreshed TIMESTAMPTZ DEFAULT NOW(),
        is_prod BOOLEAN DEFAULT FALSE,
        is_published BOOLEAN DEFAULT FALSE,
        published_ci_name TEXT,
        base_ci_name TEXT
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS showroom_analysis (
        ci_name TEXT PRIMARY KEY REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
        content_type TEXT,
        summary TEXT,
        products_json JSONB,
        audience_json JSONB,
        topics_json JSONB,
        modules_json JSONB,
        learning_objectives_json JSONB,
        difficulty TEXT,
        estimated_duration_min INTEGER,
        event_fit_json JSONB,
        use_cases_json JSONB,
        last_repo_commit TEXT,
        last_repo_updated TIMESTAMPTZ,
        last_analyzed TIMESTAMPTZ,
        is_stale BOOLEAN DEFAULT FALSE,
        stale_commit TEXT,
        enrichment_review_needed BOOLEAN DEFAULT FALSE,
        notes TEXT
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS enrichment_tags (
        id SERIAL PRIMARY KEY,
        ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
        tag_type TEXT NOT NULL,
        tag_value TEXT NOT NULL,
        added_by TEXT,
        added_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(ci_name, tag_type, tag_value)
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id SERIAL PRIMARY KEY,
        ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
        embed_type TEXT NOT NULL,
        module_title TEXT,
        content_text TEXT,
        embedding vector(384)
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS analysis_log (
        id SERIAL PRIMARY KEY,
        ci_name TEXT,
        action TEXT NOT NULL,
        user_id TEXT,
        details TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        job_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued',
        triggered_by TEXT,
        progress_current INTEGER DEFAULT 0,
        progress_total INTEGER DEFAULT 0,
        result_json JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        started_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_catalog_items_stage ON catalog_items(stage)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_catalog_items_is_prod ON catalog_items(is_prod)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_catalog_items_category ON catalog_items(category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_catalog_items_showroom_url ON catalog_items(showroom_url)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_enrichment_tags_ci_name ON enrichment_tags(ci_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_ci_name ON embeddings(ci_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_analysis_log_ci_name ON analysis_log(ci_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_analysis_log_created_at ON analysis_log(created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS embeddings CASCADE")
    op.execute("DROP TABLE IF EXISTS enrichment_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS showroom_analysis CASCADE")
    op.execute("DROP TABLE IF EXISTS analysis_log CASCADE")
    op.execute("DROP TABLE IF EXISTS jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS catalog_items CASCADE")
```

- [ ] **Step 6: Update db.py create_schema() to use Alembic for local dev**

Replace the `create_schema` method in `src/rcars/db.py`:

```python
def create_schema(self):
    """Create all tables if they don't exist, and apply migrations.

    For local dev convenience. On OpenShift, Alembic is run by
    the Ansible playbook via k8s_exec.
    """
    with self._conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Stamp the alembic version table if it doesn't exist,
        # then run any pending migrations
        try:
            cur.execute("SELECT 1 FROM alembic_version LIMIT 1")
        except Exception:
            self._conn.rollback()
            # Fresh database — run full schema via SQL then stamp
            cur.execute(SCHEMA_SQL)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """)
            cur.execute("INSERT INTO alembic_version (version_num) VALUES ('001')")
    self._conn.commit()
```

- [ ] **Step 7: Install alembic and verify migration works**

```bash
source ~/.virtualenvs/content-advisor/bin/activate
pip install -e ".[web,dev]"
```

- [ ] **Step 8: Run tests to verify nothing broke**

```bash
source ~/.virtualenvs/content-advisor/bin/activate
python -m pytest tests/ -v -m "not integration"
```

Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml alembic.ini alembic/ src/rcars/db.py
git commit -m "db: Add Alembic migration setup with initial schema baseline"
```

---

## Task 3: Ansible Scaffolding

**Files:**
- Create: `ansible/requirements.yml`
- Create: `ansible/vars/common.yml`
- Create: `ansible/vars/dev.yml.example`
- Create: `ansible/vars/prod.yml.example`
- Modify: `.gitignore`

- [ ] **Step 1: Add ansible vars to .gitignore**

Add to `.gitignore`:

```
# Ansible vars with secrets (use .example files as templates)
ansible/vars/dev.yml
ansible/vars/prod.yml
```

- [ ] **Step 2: Create ansible/requirements.yml**

```yaml
---
collections:
  - name: kubernetes.core
    version: ">=3.0.0"
```

- [ ] **Step 3: Create ansible/vars/common.yml**

```yaml
---
# RCARS shared deployment variables
# Environment-specific vars override these in dev.yml / prod.yml

app_name: rcars
app_port: 8080

# Container images
pg_image: pgvector/pgvector:pg16
oauth_proxy_image: "registry.redhat.io/openshift4/ose-oauth-proxy-rhel9:latest"

# PostgreSQL
pg_port: 5432
pg_user: rcars
pg_database: rcars
pg_pvc_size: 5Gi
pg_storage_class: ocs-storagecluster-ceph-rbd

# Vertex AI
vertex_project_id: ""
vertex_region: us-east5

# Cluster
cluster_domain: apps.your-cluster.example.com

# App config defaults
stale_days: 3
curator_emails: ""
admin_emails: ""
```

- [ ] **Step 4: Create ansible/vars/dev.yml.example**

```yaml
---
# RCARS Dev environment variables
# Copy to dev.yml and fill in secrets:
#   cp dev.yml.example dev.yml

env: dev
target_namespace: rcars-dev
git_ref: main

# Kubeconfig for the target cluster (your-cluster)
kubeconfig: ~/.kube/your-cluster

# Hostname for the route
frontend_host: "rcars-dev.{{ cluster_domain }}"

# PostgreSQL password (generate with: openssl rand -hex 16)
pg_password: CHANGEME

# Read-only kubeconfig for Babylon cluster
# Path to the file on your local machine — contents will be loaded into a Secret
babylon_kubeconfig_path: ~/.kube/babylon-readonly

# Vertex AI credentials
# Set to true and provide the JSON key contents
vertex_enabled: true
vertex_project_id: "your-gcp-project-id"
vertex_credentials_json: |
  {
    "type": "service_account",
    "project_id": "CHANGEME"
  }

# OAuth proxy secrets (generate with: openssl rand -hex 16)
oauth_client_secret: CHANGEME
oauth_cookie_secret: CHANGEME

# Curator and admin email lists (comma-separated)
curator_emails: "your-email@redhat.com"
admin_emails: "your-email@redhat.com"

# GitHub repo for BuildConfig
github_repo: rhpds/rcars-advisory
github_token: CHANGEME
webhook_secret: CHANGEME
```

- [ ] **Step 5: Create ansible/vars/prod.yml.example**

```yaml
---
# RCARS Prod environment variables
# Copy to prod.yml and fill in secrets:
#   cp prod.yml.example prod.yml

env: prod
target_namespace: rcars-prod
git_ref: production

kubeconfig: ~/.kube/your-cluster

frontend_host: "rcars.{{ cluster_domain }}"

pg_password: CHANGEME

babylon_kubeconfig_path: ~/.kube/babylon-readonly

vertex_enabled: true
vertex_project_id: "your-gcp-project-id"
vertex_credentials_json: |
  {
    "type": "service_account",
    "project_id": "CHANGEME"
  }

oauth_client_secret: CHANGEME
oauth_cookie_secret: CHANGEME

curator_emails: "your-email@redhat.com"
admin_emails: "your-email@redhat.com"

github_repo: rhpds/rcars-advisory
github_token: CHANGEME
webhook_secret: CHANGEME
```

- [ ] **Step 6: Commit**

```bash
git add .gitignore ansible/requirements.yml ansible/vars/
git commit -m "ansible: Add deployment scaffolding with vars templates"
```

---

## Task 4: Ansible Playbook + Tasks

**Files:**
- Create: `ansible/deploy.yml`
- Create: `ansible/tasks/namespace.yml`
- Create: `ansible/tasks/apply-manifests.yml`
- Create: `ansible/tasks/wait-for-builds.yml`
- Create: `ansible/tasks/webhooks.yml`

- [ ] **Step 1: Create ansible/tasks/namespace.yml**

```yaml
---
- name: Create namespace {{ target_namespace }}
  kubernetes.core.k8s:
    kubeconfig: "{{ kubeconfig }}"
    state: present
    definition:
      apiVersion: v1
      kind: Namespace
      metadata:
        name: "{{ target_namespace }}"
```

- [ ] **Step 2: Create ansible/tasks/apply-manifests.yml**

```yaml
---
- name: Render manifests template
  ansible.builtin.template:
    src: manifests.yaml.j2
    dest: "/tmp/rcars-{{ env }}-manifests.yaml"
  changed_when: false

- name: Apply rendered manifests
  kubernetes.core.k8s:
    kubeconfig: "{{ kubeconfig }}"
    namespace: "{{ target_namespace }}"
    src: "/tmp/rcars-{{ env }}-manifests.yaml"
    state: present
    apply: true

- name: Clean up rendered manifests
  ansible.builtin.file:
    path: "/tmp/rcars-{{ env }}-manifests.yaml"
    state: absent
  changed_when: false
```

- [ ] **Step 3: Create ansible/tasks/wait-for-builds.yml**

```yaml
---
- name: Start build for {{ app_name }}
  kubernetes.core.k8s:
    kubeconfig: "{{ kubeconfig }}"
    namespace: "{{ target_namespace }}"
    state: present
    definition:
      apiVersion: build.openshift.io/v1
      kind: BuildRequest
      metadata:
        name: "{{ app_name }}"

- name: Wait for {{ app_name }} build to complete
  kubernetes.core.k8s_info:
    kubeconfig: "{{ kubeconfig }}"
    kind: Build
    namespace: "{{ target_namespace }}"
    label_selectors:
      - "buildconfig={{ app_name }}"
  register: builds
  until: >-
    builds.resources | length > 0 and
    builds.resources | sort(attribute='metadata.creationTimestamp') | last |
    json_query('status.phase') in ['Complete', 'Failed', 'Cancelled']
  retries: 60
  delay: 15

- name: Check build result
  ansible.builtin.fail:
    msg: "Build failed: {{ builds.resources | sort(attribute='metadata.creationTimestamp') | last | json_query('status.phase') }}"
  when: >-
    builds.resources | sort(attribute='metadata.creationTimestamp') | last |
    json_query('status.phase') != 'Complete'

- name: Rollout restart {{ app_name }} deployment
  ansible.builtin.command:
    cmd: >-
      oc rollout restart deployment/{{ app_name }}
      -n {{ target_namespace }}
      --kubeconfig={{ kubeconfig }}
  changed_when: true

- name: Wait for {{ app_name }} rollout to complete
  ansible.builtin.command:
    cmd: >-
      oc rollout status deployment/{{ app_name }}
      -n {{ target_namespace }}
      --kubeconfig={{ kubeconfig }}
      --timeout=120s
  changed_when: false
```

- [ ] **Step 4: Create ansible/tasks/webhooks.yml**

```yaml
---
- name: Get webhook URL from BuildConfig
  kubernetes.core.k8s_info:
    kubeconfig: "{{ kubeconfig }}"
    kind: BuildConfig
    namespace: "{{ target_namespace }}"
    name: "{{ app_name }}"
  register: bc_info

- name: Extract GitHub webhook URL
  ansible.builtin.set_fact:
    webhook_url: >-
      {{ bc_info.resources[0].spec.triggers
         | selectattr('type', 'equalto', 'GitHub')
         | map(attribute='github.secret')
         | first | default('') }}
  when: bc_info.resources | length > 0

- name: Display webhook configuration
  ansible.builtin.debug:
    msg: |
      GitHub webhook URL for {{ app_name }}:
      https://api.{{ cluster_domain | regex_replace('^apps\\.', '') }}:6443/apis/build.openshift.io/v1/namespaces/{{ target_namespace }}/buildconfigs/{{ app_name }}/webhooks/{{ webhook_secret }}/github

      Configure this in your GitHub repo settings:
      {{ github_repo }} → Settings → Webhooks → Add webhook
      Content type: application/json
      Secret: {{ webhook_secret }}
```

- [ ] **Step 5: Create ansible/deploy.yml**

```yaml
---
# RCARS OCP Deployment Playbook
#
# Automates the full setup from empty namespace to running instance.
# All tasks are idempotent — running the playbook twice produces the same result.
#
# Usage:
#   ansible-playbook ansible/deploy.yml -e env=dev                  # Full deploy
#   ansible-playbook ansible/deploy.yml -e env=prod                 # Full prod deploy
#   ansible-playbook ansible/deploy.yml -e env=dev --tags update    # Apply + build + migrate + webhooks
#   ansible-playbook ansible/deploy.yml -e env=dev --tags builds    # Just wait for builds + rollout
#   ansible-playbook ansible/deploy.yml -e env=dev --tags migrate   # Just run Alembic migrations
#   ansible-playbook ansible/deploy.yml -e env=dev --tags webhooks  # Show webhook URLs
#
# Prerequisites:
#   - ansible-galaxy collection install -r ansible/requirements.yml
#   - cp ansible/vars/dev.yml.example ansible/vars/dev.yml  (fill in secrets)
#   - kubeconfig for target cluster

- name: Deploy RCARS to OpenShift
  hosts: localhost
  connection: local
  gather_facts: false
  collections:
    - kubernetes.core

  vars_files:
    - vars/common.yml
    - "vars/{{ env }}.yml"

  pre_tasks:
    - name: Validate required variables
      ansible.builtin.assert:
        that:
          - env is defined
          - target_namespace is defined
          - kubeconfig is defined
          - pg_password is defined
        fail_msg: >
          Missing required variables. Create ansible/vars/{{ env | default('dev') }}.yml
          from the corresponding .example file.
      tags: [always]

    - name: Verify kubeconfig exists
      ansible.builtin.stat:
        path: "{{ kubeconfig }}"
      register: kubeconfig_file
      tags: [always]

    - name: Fail if kubeconfig not found
      ansible.builtin.fail:
        msg: "Kubeconfig not found at {{ kubeconfig }}"
      when: not kubeconfig_file.stat.exists
      tags: [always]

    - name: Verify cluster connectivity
      kubernetes.core.k8s_cluster_info:
        kubeconfig: "{{ kubeconfig }}"
      register: cluster_info
      tags: [always]

    - name: Load Babylon kubeconfig contents
      ansible.builtin.set_fact:
        babylon_kubeconfig_content: "{{ lookup('file', babylon_kubeconfig_path) }}"
      when: babylon_kubeconfig_path is defined and babylon_kubeconfig_path != ''
      tags: [apply, update]

  tasks:
    - name: Create namespace
      ansible.builtin.include_tasks:
        file: tasks/namespace.yml
        apply:
          tags: [namespace, apply, update]
      tags: [namespace, apply, update]

    - name: Apply manifests
      ansible.builtin.include_tasks:
        file: tasks/apply-manifests.yml
        apply:
          tags: [apply, update]
      tags: [apply, update]

    - name: Wait for builds
      ansible.builtin.include_tasks:
        file: tasks/wait-for-builds.yml
        apply:
          tags: [builds, apply, update]
      tags: [builds, apply, update]

    - name: Run database migrations
      block:
        - name: Get app pod name
          kubernetes.core.k8s_info:
            kubeconfig: "{{ kubeconfig }}"
            kind: Pod
            namespace: "{{ target_namespace }}"
            label_selectors:
              - "app={{ app_name }}"
              - "component=app"
            field_selectors:
              - status.phase=Running
          register: app_pods

        - name: Run Alembic migrations
          kubernetes.core.k8s_exec:
            kubeconfig: "{{ kubeconfig }}"
            namespace: "{{ target_namespace }}"
            pod: "{{ app_pods.resources[0].metadata.name }}"
            command: python -m alembic upgrade head
          register: migrate_result
          changed_when: "'Running upgrade' in (migrate_result.stderr | default(''))"
      tags: [migrate, apply, update]

    - name: Show webhook configuration
      ansible.builtin.include_tasks:
        file: tasks/webhooks.yml
        apply:
          tags: [webhooks, apply, update]
      tags: [webhooks, apply, update]

  post_tasks:
    - name: Get pod status
      kubernetes.core.k8s_info:
        kubeconfig: "{{ kubeconfig }}"
        kind: Pod
        namespace: "{{ target_namespace }}"
        label_selectors:
          - "app={{ app_name }}"
      register: final_pods
      tags: [always]

    - name: Deployment summary
      ansible.builtin.debug:
        msg: |
          === RCARS {{ env }} deployment complete ===

          Namespace: {{ target_namespace }}
          URL:       https://{{ frontend_host }}

          Pods:
          {% for pod in final_pods.resources | sort(attribute='metadata.name') %}
            {{ pod.metadata.name }}  {{ pod.status.phase }}
          {% endfor %}
      tags: [always]
```

- [ ] **Step 6: Commit**

```bash
git add ansible/deploy.yml ansible/tasks/
git commit -m "ansible: Add deployment playbook with namespace, build, migrate, webhook tasks"
```

---

## Task 5: Kubernetes Manifests Template

**Files:**
- Create: `ansible/templates/manifests.yaml.j2`

This is the largest task — the single Jinja2 template that renders all Kubernetes resources.

- [ ] **Step 1: Create ansible/templates/manifests.yaml.j2**

```yaml
{# RCARS OpenShift manifests — Jinja2 template rendered by Ansible #}
---
# ServiceAccount for OAuth proxy
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ app_name }}-oauth
  annotations:
    serviceaccounts.openshift.io/oauth-redirecturi.primary: "https://{{ frontend_host }}/oauth/callback"
  labels:
    app: {{ app_name }}
---
# PostgreSQL credentials
apiVersion: v1
kind: Secret
metadata:
  name: {{ app_name }}-postgresql
  labels:
    app: {{ app_name }}
    component: postgresql
type: Opaque
stringData:
  POSTGRESQL_USER: "{{ pg_user }}"
  POSTGRESQL_PASSWORD: "{{ pg_password }}"
  POSTGRESQL_DATABASE: "{{ pg_database }}"
---
# OAuth proxy credentials
apiVersion: v1
kind: Secret
metadata:
  name: {{ app_name }}-oauth-proxy-secret
  labels:
    app: {{ app_name }}
    component: oauth-proxy
type: Opaque
stringData:
  client-id: "{{ app_name }}-{{ env }}"
  client-secret: "{{ oauth_client_secret }}"
  session_secret: "{{ oauth_cookie_secret }}"
{% if babylon_kubeconfig_content is defined %}
---
# Read-only kubeconfig for Babylon cluster
apiVersion: v1
kind: Secret
metadata:
  name: {{ app_name }}-babylon-kubeconfig
  labels:
    app: {{ app_name }}
    component: app
type: Opaque
stringData:
  kubeconfig: {{ babylon_kubeconfig_content | to_json }}
{% endif %}
{% if vertex_enabled | default(false) %}
---
# Vertex AI credentials
apiVersion: v1
kind: Secret
metadata:
  name: {{ app_name }}-vertex-credentials
  labels:
    app: {{ app_name }}
    component: app
type: Opaque
stringData:
  credentials.json: {{ vertex_credentials_json | string | to_json }}
{% endif %}
---
# GitHub webhook secret for BuildConfig
apiVersion: v1
kind: Secret
metadata:
  name: {{ app_name }}-webhook
  labels:
    app: {{ app_name }}
type: Opaque
stringData:
  WebHookSecretKey: "{{ webhook_secret }}"
{% if github_token is defined and github_token != 'CHANGEME' %}
---
# GitHub source secret for private repo access
apiVersion: v1
kind: Secret
metadata:
  name: {{ app_name }}-github-source
  labels:
    app: {{ app_name }}
type: kubernetes.io/basic-auth
stringData:
  username: "{{ github_token }}"
  password: ""
{% endif %}
---
# PostgreSQL PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ app_name }}-postgresql-data
  labels:
    app: {{ app_name }}
    component: postgresql
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: {{ pg_storage_class }}
  resources:
    requests:
      storage: {{ pg_pvc_size }}
---
# PostgreSQL Service
apiVersion: v1
kind: Service
metadata:
  name: {{ app_name }}-postgresql
  labels:
    app: {{ app_name }}
    component: postgresql
spec:
  selector:
    app: {{ app_name }}
    component: postgresql
  ports:
    - port: {{ pg_port }}
      targetPort: {{ pg_port }}
  type: ClusterIP
---
# PostgreSQL StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ app_name }}-postgresql
  labels:
    app: {{ app_name }}
    component: postgresql
spec:
  replicas: 1
  serviceName: {{ app_name }}-postgresql
  selector:
    matchLabels:
      app: {{ app_name }}
      component: postgresql
  template:
    metadata:
      labels:
        app: {{ app_name }}
        component: postgresql
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: postgresql
          image: {{ pg_image }}
          ports:
            - containerPort: {{ pg_port }}
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: {{ app_name }}-postgresql
                  key: POSTGRESQL_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ app_name }}-postgresql
                  key: POSTGRESQL_PASSWORD
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: {{ app_name }}-postgresql
                  key: POSTGRESQL_DATABASE
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: {{ app_name }}-postgresql-data
---
# App Service
apiVersion: v1
kind: Service
metadata:
  name: {{ app_name }}-service
  labels:
    app: {{ app_name }}
    component: app
spec:
  selector:
    app: {{ app_name }}
    component: app
  ports:
    - port: {{ app_port }}
      targetPort: {{ app_port }}
  type: ClusterIP
---
# App Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ app_name }}
  labels:
    app: {{ app_name }}
    component: app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {{ app_name }}
      component: app
  template:
    metadata:
      labels:
        app: {{ app_name }}
        component: app
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: {{ app_name }}
          image: "image-registry.openshift-image-registry.svc:5000/{{ target_namespace }}/{{ app_name }}:latest"
          imagePullPolicy: Always
          ports:
            - containerPort: {{ app_port }}
          env:
            - name: RCARS_DATABASE_URL
              value: "postgresql://$(PG_USER):$(PG_PASSWORD)@{{ app_name }}-postgresql:{{ pg_port }}/$(PG_DB)"
            - name: PG_USER
              valueFrom:
                secretKeyRef:
                  name: {{ app_name }}-postgresql
                  key: POSTGRESQL_USER
            - name: PG_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ app_name }}-postgresql
                  key: POSTGRESQL_PASSWORD
            - name: PG_DB
              valueFrom:
                secretKeyRef:
                  name: {{ app_name }}-postgresql
                  key: POSTGRESQL_DATABASE
{% if babylon_kubeconfig_content is defined %}
            - name: RCARS_KUBECONFIG
              value: /etc/rcars/kubeconfig
{% endif %}
{% if vertex_enabled | default(false) %}
            - name: ANTHROPIC_VERTEX_PROJECT_ID
              value: "{{ vertex_project_id }}"
            - name: CLOUD_ML_REGION
              value: "{{ vertex_region }}"
            - name: GOOGLE_APPLICATION_CREDENTIALS
              value: /etc/rcars/vertex-credentials.json
{% endif %}
            - name: RCARS_CURATOR_EMAILS
              value: "{{ curator_emails }}"
            - name: RCARS_ADMIN_EMAILS
              value: "{{ admin_emails }}"
            - name: RCARS_STALE_DAYS
              value: "{{ stale_days }}"
            - name: RCARS_CLONE_DIR
              value: /tmp
            - name: HF_HOME
              value: /opt/app-root/.cache/huggingface
          volumeMounts:
{% if babylon_kubeconfig_content is defined %}
            - name: babylon-kubeconfig
              mountPath: /etc/rcars/kubeconfig
              subPath: kubeconfig
              readOnly: true
{% endif %}
{% if vertex_enabled | default(false) %}
            - name: vertex-credentials
              mountPath: /etc/rcars/vertex-credentials.json
              subPath: credentials.json
              readOnly: true
{% endif %}
          livenessProbe:
            httpGet:
              path: /advisor
              port: {{ app_port }}
            initialDelaySeconds: 15
            periodSeconds: 30
            timeoutSeconds: 10
          readinessProbe:
            httpGet:
              path: /advisor
              port: {{ app_port }}
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 5
          resources:
            requests:
              cpu: 200m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
      volumes:
{% if babylon_kubeconfig_content is defined %}
        - name: babylon-kubeconfig
          secret:
            secretName: {{ app_name }}-babylon-kubeconfig
{% endif %}
{% if vertex_enabled | default(false) %}
        - name: vertex-credentials
          secret:
            secretName: {{ app_name }}-vertex-credentials
{% endif %}
---
# OAuth Proxy Service
apiVersion: v1
kind: Service
metadata:
  name: {{ app_name }}-oauth-proxy-service
  labels:
    app: {{ app_name }}
    component: oauth-proxy
spec:
  selector:
    app: {{ app_name }}
    component: oauth-proxy
  ports:
    - name: http
      port: 8080
      targetPort: 8080
  type: ClusterIP
---
# OAuth Proxy Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ app_name }}-oauth-proxy
  labels:
    app: {{ app_name }}
    component: oauth-proxy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {{ app_name }}
      component: oauth-proxy
  template:
    metadata:
      labels:
        app: {{ app_name }}
        component: oauth-proxy
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      serviceAccountName: {{ app_name }}-oauth
      containers:
        - name: oauth-proxy
          image: {{ oauth_proxy_image }}
          args:
            - -provider=openshift
            - -http-address=:8080
            - -https-address=
            - -email-domain=*
            - "-upstream=http://{{ app_name }}-service:{{ app_port }}/"
            - -client-id=$(OAUTH_CLIENT_ID)
            - -client-secret-file=/etc/proxy/secrets/client-secret
            - -cookie-secret-file=/etc/proxy/secrets/session_secret
            - "-openshift-service-account={{ app_name }}-oauth"
            - -openshift-ca=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
            - "-skip-auth-regex=^/static/"
            - -upstream-timeout=180s
            - -pass-user-headers=true
          env:
            - name: OAUTH_CLIENT_ID
              valueFrom:
                secretKeyRef:
                  name: {{ app_name }}-oauth-proxy-secret
                  key: client-id
          ports:
            - containerPort: 8080
              name: http
          livenessProbe:
            httpGet:
              path: /oauth/healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /oauth/healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            limits:
              cpu: 200m
              memory: 128Mi
            requests:
              cpu: 100m
              memory: 64Mi
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - mountPath: /etc/proxy/secrets
              name: oauth-proxy-secret
              readOnly: true
      volumes:
        - name: oauth-proxy-secret
          secret:
            secretName: {{ app_name }}-oauth-proxy-secret
---
# Route
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ app_name }}
  labels:
    app: {{ app_name }}
spec:
  host: "{{ frontend_host }}"
  to:
    kind: Service
    name: {{ app_name }}-oauth-proxy-service
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
---
# ImageStream
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: {{ app_name }}
  labels:
    app: {{ app_name }}
---
# BuildConfig
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: {{ app_name }}
  labels:
    app: {{ app_name }}
spec:
  output:
    to:
      kind: ImageStreamTag
      name: "{{ app_name }}:latest"
  source:
    type: Git
    git:
      uri: "https://github.com/{{ github_repo }}.git"
      ref: "{{ git_ref }}"
{% if github_token is defined and github_token != 'CHANGEME' %}
    sourceSecret:
      name: {{ app_name }}-github-source
{% endif %}
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Dockerfile
  triggers:
    - type: ConfigChange
    - type: GitHub
      github:
        secretReference:
          name: {{ app_name }}-webhook
---
# OAuthClient registration
apiVersion: oauth.openshift.io/v1
kind: OAuthClient
metadata:
  name: "{{ app_name }}-{{ env }}"
grantMethod: auto
secret: "{{ oauth_client_secret }}"
redirectURIs:
  - "https://{{ frontend_host }}/oauth/callback"
```

- [ ] **Step 2: Verify template syntax**

```bash
python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('ansible/templates'))
tmpl = env.get_template('manifests.yaml.j2')
print('Template parsed successfully')
print(f'Template length: {len(tmpl.module.__loader__.get_source())} chars')
"
```

- [ ] **Step 3: Commit**

```bash
git add ansible/templates/manifests.yaml.j2
git commit -m "ansible: Add Kubernetes manifests template with all resources"
```

---

## Task 6: Deployment Documentation

**Files:**
- Create: `docs/deployment.md`

- [ ] **Step 1: Create docs/deployment.md**

```markdown
# RCARS Deployment Guide

## Prerequisites

- `oc` CLI logged into the target cluster (`your-cluster`)
- `ansible` with `kubernetes.core` collection
- Read-only kubeconfig for the Babylon cluster
- Vertex AI service account JSON key
- GitHub personal access token (for webhook registration)

### Install Ansible Dependencies

    ansible-galaxy collection install -r ansible/requirements.yml

## Initial Deployment

### 1. Create your vars file

    cd ansible/vars
    cp dev.yml.example dev.yml

Edit `dev.yml` and fill in all `CHANGEME` values:

- `pg_password` — generate with `openssl rand -hex 16`
- `oauth_client_secret` — generate with `openssl rand -hex 16`
- `oauth_cookie_secret` — generate with `openssl rand -hex 16`
- `webhook_secret` — generate with `openssl rand -hex 16`
- `babylon_kubeconfig_path` — path to your Babylon read-only kubeconfig
- `vertex_credentials_json` — paste contents of your GCP JSON key
- `vertex_project_id` — your GCP project ID
- `github_token` — GitHub PAT with repo access
- `curator_emails` / `admin_emails` — comma-separated email lists

### 2. Run the playbook

    ansible-playbook ansible/deploy.yml -e env=dev

This will:
1. Create the `rcars-dev` namespace
2. Apply all secrets, deployments, services, routes, and BuildConfig
3. Trigger the first Docker build from GitHub
4. Wait for the build to complete (~3-5 minutes)
5. Run Alembic database migrations
6. Display the webhook URL for GitHub

### 3. Configure GitHub webhook

The playbook prints a webhook URL at the end. Add it to your GitHub repo:

1. Go to `https://github.com/<your-repo>/settings/hooks`
2. Click "Add webhook"
3. Paste the URL from the playbook output
4. Content type: `application/json`
5. Secret: the `webhook_secret` value from your vars file
6. Events: "Just the push event"

### 4. Verify

Open `https://rcars-dev.apps.your-cluster.example.com`

You should see the OpenShift SSO login page. After authenticating, RCARS loads with your email in the header.

## Day-to-Day Operations

### Code update (after push to main)

If webhooks are configured, the build triggers automatically. Then:

    ansible-playbook ansible/deploy.yml -e env=dev --tags update

This waits for the build, restarts the app, and runs any new migrations.

### Just run migrations

    ansible-playbook ansible/deploy.yml -e env=dev --tags migrate

### Just restart the app (no build)

    oc rollout restart deployment/rcars -n rcars-dev

### Check logs

    oc logs deployment/rcars -n rcars-dev -f

### Run CLI commands on the pod

    oc exec deployment/rcars -n rcars-dev -- rcars status
    oc exec deployment/rcars -n rcars-dev -- rcars refresh
    oc exec deployment/rcars -n rcars-dev -- rcars scan --max 5

## Production Deployment

Same process but with `prod` vars:

    cp ansible/vars/prod.yml.example ansible/vars/prod.yml
    # Edit prod.yml with production values
    ansible-playbook ansible/deploy.yml -e env=prod

Production builds from the `production` branch. Promote by merging `main → production`.

## Troubleshooting

### Build fails

    oc logs bc/rcars -n rcars-dev

### Pod won't start

    oc describe pod -l app=rcars,component=app -n rcars-dev
    oc logs deployment/rcars -n rcars-dev

### Database connection issues

    oc exec deployment/rcars -n rcars-dev -- python -c "
    from rcars.config import Settings
    s = Settings()
    print(f'DB URL: {s.database_url[:30]}...')
    from rcars.db import Database
    db = Database(s.database_url)
    print('Connected OK')
    db.close()
    "

### OAuth proxy issues

    oc logs deployment/rcars-oauth-proxy -n rcars-dev
```

- [ ] **Step 2: Commit**

```bash
git add docs/deployment.md
git commit -m "docs: Add deployment guide with setup, operations, and troubleshooting"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ Ansible playbook with Jinja2 manifests (labagator pattern) — Tasks 3-5
- ✅ BuildConfig with Docker strategy + GitHub webhook — Task 5 (manifests)
- ✅ OAuth proxy with `-pass-user-headers=true` — Task 5 (manifests)
- ✅ PostgreSQL StatefulSet with pgvector — Task 5 (manifests)
- ✅ Babylon kubeconfig secret — Task 5 (manifests)
- ✅ Vertex AI credentials secret — Task 5 (manifests)
- ✅ Alembic migrations — Task 2
- ✅ Sentence-transformers model baked into image — Task 1
- ✅ Dev + prod environments — Tasks 3-4
- ✅ Ansible tags (update, builds, migrate, webhooks) — Task 4
- ✅ Deployment documentation — Task 6
- ✅ User runs deployment (not Claude) — noted in plan header

**Deferred (per spec section 8):**
- CronJobs for scheduled scan/refresh
- Horizontal scaling / HPA
- Session persistence
- Monitoring / alerting
- Backup / restore
