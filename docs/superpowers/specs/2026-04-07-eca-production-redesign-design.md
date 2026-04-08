# RCARS Production Redesign — Design Specification

**RCARS: RHDP Content Advisory & Recommendation System**

**Date:** 2026-04-07
**Status:** Draft
**Author:** Test User + Claude

## 1. Overview

RCARS (formerly Event Content Advisor / ECA) is being redesigned from a single-user experimental CLI tool into a production multi-user service running on RHDP OpenShift infrastructure. The redesign replaces ad-hoc local execution with a containerized, always-on service that keeps catalog and Showroom analysis data fresh automatically.

The name pays homage to Star Trek's LCARS (Library Computer Access/Retrieval System) — because RCARS is, at its core, a library content advisory and retrieval system for the RHDP catalog.

### Goals

- Deploy as containers on RHDP OpenShift (Helm-based, GitOps-ready)
- Support ~15 concurrent users across three roles (admin, curator, viewer)
- Automate daily catalog refresh and Showroom analysis via built-in scheduler
- Replace AgnosticV git cloning with Babylon K8s CRD queries (security, simplicity)
- Replace SQLite + ChromaDB with PostgreSQL + pgvector (unified data layer)
- Improve analysis quality with richer learning objectives and boilerplate filtering
- Add stage filtering (prod-only default, "everything" toggle)
- Prepare architecture for future chat interface and feedback capture

### Non-Goals (This Phase)

- Chat/conversational interface (architecture supports it, implementation deferred)
- Feedback/selection capture UI (tables designed, UI deferred)
- SuperSet usage data import (schema ready, integration deferred)
- Frontend visual redesign (functional improvements only in this phase)
- Cost-based filtering of recommendations (schema ready, requires SuperSet data)

---

## 2. Architecture

### 2.1 Deployment Topology

Two pods on RHDP OpenShift:

```
                     ┌─────────────────────────────────┐
                     │     OpenShift Route (HTTPS)      │
                     │     rcars.apps.rhdp.example.com    │
                     └───────────────┬─────────────────┘
                                     │
                          Red Hat SSO │ OAuth2
                                     │
                     ┌───────────────▼─────────────────┐
                     │                                  │
                     │    Pod 1: RCARS App                │
                     │                                  │
                     │  ┌────────────────────────────┐  │
                     │  │  FastAPI (uvicorn)          │  │
                     │  │  /recommend  /catalog       │  │
                     │  │  /chat  /admin  /system     │  │
                     │  └──────────┬─────────────────┘  │
                     │             │                     │
                     │  ┌──────────▼─────────────────┐  │
                     │  │  Background Workers         │  │
                     │  │  (asyncio / thread pool)    │  │
                     │  │  • Showroom analysis        │  │
                     │  │  • Recommendation ranking   │  │
                     │  │  • Event URL parsing        │  │
                     │  └──────────┬─────────────────┘  │
                     │             │                     │
                     │  ┌──────────▼─────────────────┐  │
                     │  │  Scheduler (APScheduler)    │  │
                     │  │  • Daily: catalog refresh   │  │
                     │  │  • Daily: Showroom stale    │  │
                     │  │    check + auto-rescan      │  │
                     │  └────────────────────────────┘  │
                     │                                  │
                     └──────┬──────────────┬────────────┘
                            │              │
          ┌─────────────────▼──┐   ┌───────▼──────────────┐
          │                    │   │                       │
          │  Pod 2: PostgreSQL │   │  Babylon K8s API      │
          │  + pgvector        │   │  (via kubeconfig)     │
          │                    │   │                       │
          │  PVC-backed        │   │  CatalogItems from:   │
          │  storage           │   │  • babylon-catalog-   │
          │                    │   │    prod               │
          │                    │   │  • babylon-catalog-   │
          │                    │   │    dev                │
          │                    │   │  • babylon-catalog-   │
          │                    │   │    event              │
          │                    │   │                       │
          │                    │   │  AgnosticVComponents  │
          │                    │   │  from babylon-config  │
          └────────────────────┘   └───────────────────────┘
```

### 2.2 Why Single App Pod (Not Microservices)

At ~15 users with single-digit concurrency, splitting web server, workers, and scheduler into separate services adds operational complexity with no benefit. All three run in the same process. Background workers use an in-process task queue (asyncio tasks or thread pool), not Celery/Redis.

If scaling is ever needed, the app pod can be replicated (with APScheduler using PostgreSQL-backed job store and leader election so only one replica runs scheduled jobs).

### 2.3 External Dependencies

| Dependency | Purpose | Access Method |
|---|---|---|
| Claude Sonnet (Vertex AI) | Analysis, recommendations, event parsing | Vertex AI API via GCP credentials |
| Babylon K8s cluster | Catalog metadata, Showroom URLs | Kubeconfig (read-only, mounted Secret) |
| Showroom git repos | Content to analyze | Shallow clone to tmpfs (ephemeral) |
| Red Hat SSO | Authentication | OAuth proxy sidecar |

---

## 3. Data Layer

### 3.1 PostgreSQL + pgvector (Unified Store)

Replaces both SQLite and ChromaDB. All data — catalog metadata, analysis results, enrichment, vector embeddings, chat, feedback — lives in a single PostgreSQL database with the pgvector extension.

**Why unified:**
- Eliminates the sync gap between SQLite and ChromaDB (a crash between two writes can no longer leave vectors stale)
- Real concurrent writes with row-level locking (MVCC)
- JSONB columns enable native queries inside JSON arrays
- Transactions, foreign keys, and constraints are battle-tested
- Standard OpenShift deployment (prefer Crunchy PostgreSQL operator — Red Hat certified — or CloudNativePG)

**Scale:** ~500 catalog items, ~2,500 module-level embeddings at 384 dimensions (all-MiniLM-L6-v2). pgvector handles this trivially — sub-millisecond queries up to 100K vectors.

### 3.2 Schema

#### `catalog_items` — Catalog Metadata (from Babylon CRDs)

| Column | Type | Source |
|---|---|---|
| `ci_name` | TEXT PK | CatalogItem `.metadata.name` |
| `display_name` | TEXT | CatalogItem `spec.displayName` |
| `category` | TEXT | CatalogItem `spec.category` |
| `product` | TEXT | CatalogItem label `Product` |
| `product_family` | TEXT | CatalogItem label `Product_Family` |
| `primary_bu` | TEXT | CatalogItem label `primaryBU` |
| `secondary_bu` | TEXT | CatalogItem label `secondaryBU` |
| `stage` | TEXT | CatalogItem label `stage` (prod/dev/event) |
| `catalog_namespace` | TEXT | CatalogItem `.metadata.namespace` |
| `keywords` | TEXT[] | CatalogItem `spec.keywords` |
| `description` | TEXT | CatalogItem `spec.description.content` |
| `icon_url` | TEXT | CatalogItem `spec.icon.url` |
| `owners_json` | JSONB | CatalogItem `spec.owners` |
| `showroom_url` | TEXT | AgnosticVComponent definition (extracted) |
| `showroom_ref` | TEXT | AgnosticVComponent definition (extracted) |
| `last_crd_update` | TIMESTAMPTZ | CatalogItem `spec.lastUpdate.git.when_committer` |
| `last_refreshed` | TIMESTAMPTZ | When RCARS last read this CRD |
| `is_prod` | BOOLEAN | Derived: stage = 'prod' |

#### `showroom_analysis` — LLM Analysis Results

| Column | Type | Description |
|---|---|---|
| `ci_name` | TEXT PK/FK | Links to catalog_items |
| `content_type` | TEXT | workshop / demo |
| `summary` | TEXT | LLM-generated summary |
| `products_json` | JSONB | Red Hat products covered |
| `audience_json` | JSONB | Target audience descriptors |
| `topics_json` | JSONB | Topics/technologies |
| `modules_json` | JSONB | Module objects with learning objectives (see 5.2) |
| `learning_objectives_json` | JSONB | Stated + LLM-inferred learning objectives |
| `difficulty` | TEXT | beginner / intermediate / advanced |
| `estimated_duration_min` | INTEGER | Total estimated duration |
| `event_fit_json` | JSONB | Booth/lab/presentation suitability |
| `use_cases_json` | JSONB | Business problems solved |
| `last_repo_commit` | TEXT | Showroom repo HEAD SHA when analyzed |
| `last_repo_updated` | TIMESTAMPTZ | Date of last commit in Showroom repo |
| `last_analyzed` | TIMESTAMPTZ | When analysis was performed |
| `is_stale` | BOOLEAN | Showroom has new commits since analysis |
| `stale_commit` | TEXT | New HEAD SHA that triggered stale flag |
| `enrichment_review_needed` | BOOLEAN | Analysis delta exceeded threshold (see 5.4) |

#### `enrichment_tags` — RCARS-Native Enrichment (Type 2 Edits)

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PK | Auto-increment |
| `ci_name` | TEXT FK | Links to catalog_items |
| `tag_type` | TEXT | keyword / audience / product / event_fit / lifecycle / custom |
| `tag_value` | TEXT | The tag content (e.g., "good for booth", "retiring Q3 2026") |
| `added_by` | TEXT | Username who added the tag |
| `added_at` | TIMESTAMPTZ | When added |

Design: Enrichment is purely additive. Rescans never touch this table. Concurrent tag additions by two curators produce a union (no conflict). Tags can be removed individually by curators.

#### `embeddings` — pgvector Semantic Search

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PK | Auto-increment |
| `ci_name` | TEXT FK | Links to catalog_items |
| `embed_type` | TEXT | ci_summary / module |
| `module_title` | TEXT | NULL for ci_summary, module title for module-level |
| `content_text` | TEXT | The text that was embedded |
| `embedding` | vector(384) | all-MiniLM-L6-v2 embedding |

Indexes: IVFFlat or HNSW index on `embedding` column for fast similarity search.

#### `chat_sessions` — Conversation History (Future)

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Session identifier |
| `user_id` | TEXT | Authenticated user |
| `created_at` | TIMESTAMPTZ | Session start |
| `context_json` | JSONB | Referenced CIs, event context |

#### `chat_messages` — Individual Messages (Future)

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PK | Auto-increment |
| `session_id` | UUID FK | Links to chat_sessions |
| `role` | TEXT | user / assistant |
| `content` | TEXT | Message content |
| `created_at` | TIMESTAMPTZ | Timestamp |

#### `feedback` — Selection Capture (Future)

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PK | Auto-increment |
| `user_id` | TEXT | Who made the selection |
| `query_text` | TEXT | Original recommendation query |
| `event_context` | TEXT | Event name/URL if applicable |
| `selected_ci_names` | TEXT[] | CIs the user chose |
| `rejected_ci_names` | TEXT[] | CIs explicitly rejected |
| `notes` | TEXT | Optional user notes |
| `created_at` | TIMESTAMPTZ | When captured |

#### `analysis_log` — Audit Trail

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PK | Auto-increment |
| `ci_name` | TEXT | CI affected |
| `action` | TEXT | refresh / analyze / stale / rescan / enrich / error |
| `user_id` | TEXT | Who triggered (NULL for scheduled) |
| `details` | TEXT | Additional context |
| `created_at` | TIMESTAMPTZ | Timestamp |

#### `jobs` — Background Job Tracking

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Job identifier |
| `job_type` | TEXT | full_scan / single_rescan / recommend / event_parse |
| `status` | TEXT | queued / running / completed / failed |
| `triggered_by` | TEXT | Username or "scheduler" |
| `progress_current` | INTEGER | Items processed |
| `progress_total` | INTEGER | Total items |
| `result_json` | JSONB | Job output (recommendations, errors, etc.) |
| `created_at` | TIMESTAMPTZ | When queued |
| `started_at` | TIMESTAMPTZ | When started |
| `completed_at` | TIMESTAMPTZ | When finished |

---

## 4. Catalog Source: Babylon K8s CRDs

### 4.1 Why CRDs Instead of Cloning AgnosticV

The previous approach cloned 3 private AgnosticV git repos (which contain vault-encrypted secrets, SSH keys, cloud credentials) and parsed raw YAML with custom `#include` stripping, `!vault` handling, and Jinja template detection.

The new approach reads Babylon CRDs — the pre-processed, deployed representation of the catalog — via the K8s API. This:

- Eliminates security risk of handling repos with credentials
- Eliminates complex YAML parsing (the Babylon operator already did this)
- Provides the resolved/merged view (no need to follow component references)
- Makes stage filtering trivial (CRDs live in stage-specific namespaces)
- Works identically from local dev (kubeconfig) and in-cluster (mounted Secret)

### 4.2 CRD Access Pattern

**Authentication:** Read-only kubeconfig stored as an OpenShift Secret, mounted into the app pod. Same pattern as parsec (`rhdp-readonly` SA with `babylon-readonly` ClusterRole) and labagator.

For local development, the developer's existing `oc login` kubeconfig works.

**CRD Queries:**

| Resource | Namespace(s) | Fields Extracted |
|---|---|---|
| CatalogItem | `babylon-catalog-prod`, `babylon-catalog-dev`, `babylon-catalog-event` | displayName, category, keywords, description, owners, icon, labels (Product, Product_Family, stage, primaryBU, secondaryBU), lastUpdate |
| AgnosticVComponent | `babylon-config` | Showroom URL + ref from `spec.definition` (allowlisted fields only) |

**Prod-only mode (default):** Query `babylon-catalog-prod` only.
**Everything mode (opt-in):** Query all three namespaces. Items not in prod are flagged with a "Dev only" badge in the UI.

### 4.3 Showroom URL Extraction from AgnosticVComponent

The Showroom URL lives inside `spec.definition` as a top-level variable. RCARS extracts using an **allowlist** of known variable names:

- `ocp4_workload_showroom_content_git_repo`
- `ocp4_workload_showroom_content_git_repo_ref`
- `showroom_git_repo`
- `showroom_git_repo_ref`

**Security:** The full `spec.definition` contains vault-encrypted secrets, SSH keys, S3 credentials, and other sensitive data. RCARS must:

1. Extract only allowlisted fields
2. Never store, log, or cache the full definition
3. Discard the CRD response after extraction

### 4.4 CatalogItem ↔ AgnosticVComponent Correlation

CatalogItems and AgnosticVComponents share the same `.metadata.name` (e.g., `openshift-cnv.ocp4-lightspeed-cnv.prod`). The refresh process:

1. List all CatalogItems from target namespace(s)
2. For each CatalogItem, fetch the matching AgnosticVComponent from `babylon-config`
3. Extract Showroom URL/ref from the component
4. Upsert the merged record into `catalog_items`

---

## 5. Showroom Analysis

### 5.1 Analysis Pipeline

1. **Clone:** `git clone --depth 1 --branch <showroom_ref>` to Kubernetes `emptyDir` with `medium: Memory` (tmpfs). Falls back to default branch if ref doesn't exist.
2. **Read:** All `.adoc` files from `content/modules/ROOT/pages/`, plus `nav.adoc` and `antora.yml`
3. **Filter:** Skip boilerplate pages (see 5.3)
4. **Analyze:** Send to Sonnet (`temperature=0`) with improved `analyze_showroom` prompt
5. **Store:** Structured JSON → PostgreSQL (showroom_analysis + embeddings)
6. **Cleanup:** Delete tmpfs clone immediately

### 5.2 Enriched Module Schema

Each module in `modules_json` includes learning objectives:

```json
{
  "title": "Configuring RHDH User Permissions",
  "topics": ["RHDH", "RBAC", "Keycloak"],
  "learning_objectives": [
    "Install Red Hat Developer Hub on OCP",
    "Configure group-based permission policies",
    "Create and manage user roles via the admin UI"
  ],
  "estimated_duration_min": 25
}
```

The top-level `learning_objectives_json` contains both:
- **Stated objectives:** What the Showroom explicitly calls out in intro/overview sections
- **Inferred objectives:** What Sonnet determines you'll actually learn by completing the lab (e.g., a lab that teaches GitOps by deploying with ArgoCD — the inferred objective is "understand GitOps workflows" even if the Showroom never uses that phrase)

### 5.3 Boilerplate Page Filtering

The `analyze_showroom` prompt instructs Sonnet to ignore common boilerplate pages that waste context:

- Login/credentials pages ("your username is...", "connect to bastion...")
- Environment setup pages ("your lab environment has been provisioned...")
- Navigation/index pages (table of contents, module listings)
- Author bios, revision history
- Generic "how to use this lab" preamble

These are identified by page title patterns and content signals. The prompt directs Sonnet to focus analysis budget on actual learning content.

### 5.4 Enrichment Review Flags

When a Showroom is re-analyzed after content changes, RCARS compares the old analysis to the new analysis on key fields:

- Products list changed (>30% difference)
- Difficulty level changed
- Learning objectives changed substantially
- Duration changed by >50%

If any of these conditions are met, `enrichment_review_needed` is set to `true` on that CI. The comparison is a simple set/value diff between the old and new analysis JSON — no LLM call needed. The curator UI shows flagged items with a diff summary: "This lab's analysis changed — products went from [X] to [Y]. Please verify your enrichment tags still apply."

Minor Showroom edits (typos, formatting, screenshots) produce nearly identical analysis output and do not trigger the flag.

### 5.5 Stale Detection

Based on the Showroom repo's HEAD commit SHA for the specified branch/ref (via `git ls-remote <repo> <ref>`), not on AgnosticV/CRD changes. A metadata change in the CatalogItem (e.g., keyword update) does not trigger re-analysis — only Showroom content changes do.

---

## 6. Edit Philosophy

### 6.1 Type 1 — Source-of-Truth Corrections

Changes to display name, category, product, description, Showroom URL, or analysis accuracy must be fixed upstream in AgnosticV/Showroom repos. RCARS does not store corrections to upstream data.

The workflow:
1. Curator notices incorrect data in RCARS
2. Curator fixes it in AgnosticV (for catalog metadata) or Showroom (for content)
3. Curator triggers a per-item rescan in RCARS
4. RCARS re-reads the CRD and/or re-analyzes the Showroom
5. Corrected data appears in RCARS

### 6.2 Type 2 — RCARS-Native Enrichment

Tags, annotations, and metadata that exist only in RCARS and are meaningful to the recommendation engine:

- Event fitness tags: "good for booth demo", "too long for booth"
- Lifecycle tags: "retiring Q3 2026", "new for Summit 2026"
- Audience annotations: "great for partner enablement"
- Additional keywords for search recall
- Custom notes

These live in the `enrichment_tags` table, are purely additive, and are never touched by rescans. Concurrent tag additions by two curators produce a union (no locking needed).

---

## 7. User Model & Authentication

### 7.1 Authentication

Red Hat SSO via OAuth proxy sidecar (same pattern as parsec and labagator on RHDP OpenShift). Users authenticate with their Red Hat credentials.

Role determination: Query the OpenShift groups API (`/apis/user.openshift.io/v1/groups`) from the pod's service account, with 60-second in-memory cache. Do not rely on OAuth proxy `--openshift-group` headers (unreliable, per parsec's experience).

### 7.2 Roles

| Role | Who | Permissions |
|---|---|---|
| **Admin** | ~2-3 people | Everything below + trigger full scan, manage schedule, view system status |
| **Curator** | ~10-12 content devs | Everything below + add/remove enrichment tags, trigger per-item rescan |
| **Viewer** | Field team, anyone with SSO access | Run recommendations, browse catalog, use chat (future) |

Role mapping: OpenShift groups → RCARS roles (configurable in Helm values).

### 7.3 Admin Capabilities

- Trigger immediate full catalog refresh + Showroom scan (background job with progress)
- View/modify scan schedule (daily cadence, time of day)
- Pause/resume scheduled jobs
- View system status (total CIs, analyzed, pending, stale, errors)
- View background job history and status
- View audit log

### 7.4 Curator Capabilities

- Add/remove enrichment tags on any CI
- Trigger per-item rescan (re-read CRD + re-analyze Showroom)
- Review enrichment flags (items where analysis changed significantly)
- View analysis details for any CI

---

## 8. Stage Filtering

### 8.1 Two Modes

| Mode | Namespaces Queried | Default? |
|---|---|---|
| **Prod** | `babylon-catalog-prod` | Yes |
| **Everything** | `babylon-catalog-prod` + `babylon-catalog-dev` + `babylon-catalog-event` | Opt-in toggle |

### 8.2 UI Behavior

- Default view shows prod items only (unmarked)
- "Include dev/event items" toggle expands to everything
- Items from `babylon-catalog-dev` display a "Dev only" badge
- Items from `babylon-catalog-event` are treated the same as prod (no badge) — event is a subset of prod-ready content
- The toggle affects both the catalog browser and recommendation results
- Recommendations in "Everything" mode include a warning: "Some results are dev-only and may not be available on the production catalog"

### 8.3 Data Model

The `catalog_items.stage` column stores the stage from the CRD label. The `catalog_items.is_prod` boolean provides a fast filter. The `catalog_namespace` column preserves the exact source namespace.

---

## 9. Recommendation Engine

### 9.1 Query Flow

```
User query (text or event URL)
  │
  ├─ If URL → fetch page, Sonnet extracts themes (temperature=0)
  │
  ├─ pgvector semantic search (top 15 candidates)
  │   └─ WHERE is_prod = true (default) or no filter (everything mode)
  │   └─ Optional filters: difficulty, product, content_type
  │
  ├─ Enrich with catalog metadata + enrichment tags
  │
  ├─ Sonnet ranking (temperature=0)
  │   └─ Returns scored recommendations with rationale, caveats, content gaps
  │
  └─ Return results
```

### 9.2 Embedding Strategy

Two levels of embeddings stored in the `embeddings` table:

- **CI-level:** Concatenation of summary + learning objectives + topics + products + audience → single embedding per CI
- **Module-level:** Each module's title + learning objectives + topics → one embedding per module

Recommendation queries search CI-level embeddings. Future chat queries can search module-level embeddings for more granular answers ("does this lab cover X?").

### 9.3 Background Execution

Recommendation ranking (which calls Sonnet) runs as a background job. The web UI receives an immediate response with a job ID, then polls or uses SSE (Server-Sent Events) for progress updates. No more request timeouts.

---

## 10. Scheduler

### 10.1 Scheduled Jobs

| Job | Frequency | What It Does |
|---|---|---|
| Catalog refresh | Daily | Query Babylon CRDs, upsert catalog_items |
| Stale check + rescan | Daily (after refresh) | `git ls-remote` each Showroom ref, mark stale, auto-rescan stale items |

### 10.2 Implementation

APScheduler with PostgreSQL-backed job store (survives pod restarts). If the app is replicated, leader election ensures only one replica runs scheduled jobs.

### 10.3 Admin Controls

Admins can:
- Trigger immediate full scan (in addition to scheduled)
- View next scheduled run time
- Pause/resume the schedule
- Modify schedule cadence (via admin UI or Helm values)

---

## 11. Background Jobs

All long-running operations run as background tasks with progress tracking:

| Operation | Triggered By | Duration |
|---|---|---|
| Full catalog refresh | Scheduler or admin | ~2-5 min |
| Full Showroom scan | Scheduler or admin | ~15-30 min (Sonnet API calls) |
| Single-item rescan | Curator | ~30-60 sec |
| Recommendation ranking | Viewer | ~10-20 sec |
| Event URL parsing | Viewer | ~5-10 sec |

Job status is stored in the `jobs` table. The web UI shows progress for the user's own jobs and (for admins) system-wide job status.

### 11.1 Concurrency

- Showroom analysis: Thread pool with configurable max workers (default 5)
- Recommendation ranking: One at a time per user (queued)
- All workers share the PostgreSQL connection pool

### 11.2 Timeouts

All Sonnet API calls have explicit timeouts:
- Analysis: 120 seconds per CI
- Recommendation ranking: 60 seconds
- Event URL parsing: 60 seconds
- Retry with exponential backoff on transient failures (max 3 retries)

---

## 12. Deployment

### 12.1 Helm Chart Structure

Following labagator's subchart pattern:

```
helm/rcars/
├── Chart.yaml
├── values.yaml
├── charts/
│   ├── app/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       ├── route.yaml
│   │       ├── configmap.yaml
│   │       ├── secret-kubeconfig.yaml
│   │       ├── secret-vertex.yaml
│   │       └── serviceaccount.yaml
│   ├── postgresql/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── statefulset.yaml
│   │       ├── service.yaml
│   │       ├── pvc.yaml
│   │       └── secret.yaml
│   └── oauth-proxy/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           └── secret.yaml
```

### 12.2 Key Helm Values

```yaml
global:
  clusterDomain: apps.rhdp.example.com

app:
  replicaCount: 1
  image:
    repository: quay.io/rhpds/rcars
    tag: latest
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi
  env:
    RCARS_MODEL: claude-sonnet-4-6
    RCARS_MAX_PARALLEL: "5"
    CLOUD_ML_REGION: us-east5
  schedule:
    catalogRefresh: "0 2 * * *"    # 2 AM daily
    showroomScan: "0 3 * * *"      # 3 AM daily
  roleMapping:
    admin: ["rhpds-admins", "rcars-admins"]
    curator: ["rhpds-devs", "rcars-curators"]
    viewer: []  # all authenticated users

postgresql:
  image:
    repository: registry.redhat.io/rhel9/postgresql-16
    tag: latest
  storage:
    size: 10Gi
    storageClass: ocs-storagecluster-ceph-rbd
  extensions:
    - pgvector  # installed via postgresql-pgvector RPM or compiled in init container

secrets:
  vertexCredentials: {}     # GCP SA JSON
  babylonKubeconfig: {}     # read-only kubeconfig
```

### 12.3 Container Build

Single Dockerfile, multi-stage build using RHEL UBI (Universal Base Image):

```dockerfile
FROM registry.access.redhat.com/ubi9/python-311:latest AS builder
# Install dependencies, build wheel

FROM registry.access.redhat.com/ubi9/python-311:latest AS runtime
# Copy wheel, install
# Install git (for shallow clones)
# Run as non-root (UBI images support arbitrary UIDs by default)
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Container image policy:** Use Red Hat UBI or RHEL-based images wherever possible. This applies to all containers in the deployment — app, PostgreSQL, OAuth proxy, and any init containers.

### 12.4 Multi-Architecture & Build Strategy

**Local development builds on macOS (arm64) but deploys to OpenShift (amd64).** All container builds must account for this:

- Local `podman build` for testing: builds for native arm64
- Production images: must target `linux/amd64`
- When building locally for push to registry: use `podman build --platform linux/amd64` or `podman manifest` for multi-arch

**Recommended production build strategy: OpenShift BuildConfig (S2I)**

Follow the labagator pattern — use OpenShift BuildConfigs with GitHub webhook triggers:

1. Push to `main` branch → webhook triggers BuildConfig → S2I build on OpenShift (native amd64) → ImageStream tag update → Deployment rollout
2. Push to `production` branch → same flow for production namespace
3. No local image building needed for production — OpenShift handles the build natively on amd64

This eliminates cross-architecture concerns entirely for production. Developers build and test locally on arm64, push code, and OpenShift builds the amd64 image from source.

```yaml
# Helm template: BuildConfig (simplified)
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: rcars
spec:
  source:
    type: Git
    git:
      uri: https://github.com/rhpds/rcars.git
      ref: main
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Dockerfile
  output:
    to:
      kind: ImageStreamTag
      name: rcars:latest
  triggers:
    - type: GitHub
      github:
        secretReference:
          name: rcars-github-webhook
```

Alternative: OpenShift Pipelines (Tekton) if more complex CI/CD is needed (running tests, linting, security scans before build). For RCARS at this stage, S2I BuildConfig is simpler and sufficient.

Showroom clones use a Kubernetes `emptyDir` with `medium: Memory` (tmpfs) — content lives in RAM, never touches disk, automatically wiped on pod recycle.

### 12.5 Local Development

```bash
# Start local PostgreSQL with pgvector (RHEL UBI-based for consistency)
# Option A: Red Hat PostgreSQL image + pgvector extension
podman run -d --name rcars-db -p 5432:5432 \
  -e POSTGRESQL_USER=rcars -e POSTGRESQL_PASSWORD=dev \
  -e POSTGRESQL_DATABASE=rcars \
  registry.redhat.io/rhel9/postgresql-16:latest
# Note: pgvector extension must be installed separately for local dev;
# alternatively use pgvector/pgvector:pg16 for convenience locally

# Activate venv, install deps
source ~/.virtualenvs/content-advisor/bin/activate
pip install -e ".[web]"

# Uses existing oc login kubeconfig for CRD access
# Uses existing GCP credentials for Vertex AI
rcars refresh   # queries Babylon CRDs
rcars scan      # clones Showrooms, calls Sonnet
rcars web       # starts FastAPI on :8080
```

---

## 13. Migration Path

### 13.1 From Current to New Architecture

1. **Database migration:** Export existing SQLite catalog_items and showroom_analysis to PostgreSQL. Map existing ChromaDB documents to pgvector embeddings.
2. **Scanner replacement:** Replace `scanner.py` (AgnosticV YAML walker) with `catalog_reader.py` (Babylon CRD client). The data extracted is the same; only the source changes.
3. **Analyzer update:** Update `analyzer.py` to use PostgreSQL instead of SQLite + ChromaDB. Improve prompt with boilerplate filtering and learning objectives.
4. **Recommender update:** Replace ChromaDB queries with pgvector queries. Replace SQLite enrichment with PostgreSQL queries.
5. **Web app update:** Add auth middleware, background job endpoints, enrichment tag endpoints, stage filter.
6. **Helm chart:** New — build from scratch following labagator subchart pattern.

### 13.2 CLI Preservation

The `rcars` CLI commands remain functional for local development and debugging:

| Command | Behavior |
|---|---|
| `rcars refresh` | Query Babylon CRDs, upsert PostgreSQL |
| `rcars scan` | Analyze Showrooms, store in PostgreSQL |
| `rcars scan --force` | Re-analyze everything |
| `rcars recommend "..."` | Run recommendation (CLI output) |
| `rcars status` | Show DB summary |
| `rcars list` | List catalog items |
| `rcars show <ci>` | Full details for one CI |
| `rcars web` | Start FastAPI server |

---

## 14. Future: Chat Interface

Architecture supports a chat interface where users can ask follow-up questions about recommended labs:

- "Does lab X cover installing RHDH and configuring user permissions?"
- "Which of these three labs is best for a 30-minute booth demo?"
- "X and Y look good, but Z doesn't fit — can you find alternatives?"

The chat answers from enriched module-level analysis data (learning objectives, topics per module) — not from raw Showroom content. This provides learning-objective-level granularity without requiring raw `.adoc` storage.

Chat sessions and messages are stored in PostgreSQL for context continuity.

---

## 15. Future: Feedback Capture

When users "select" labs for an event, RCARS captures:
- The original query/event context
- Which CIs were selected vs. rejected
- Optional user notes

This builds a training dataset for improving future recommendations — understanding what content was actually chosen for what types of events.

---

## 16. Future: Cost Filtering

When usage/cost data is available (via SuperSet integration or direct metrics), users should be able to filter recommendations by cost:

- "Less than $1/hour to run"
- "Under $50 per student for a 3-hour workshop"
- Sort by cost efficiency (value per dollar)

This requires the `usage_metrics` table to be populated with provision costs. The recommendation prompt would include cost data alongside other ranking factors.

---

## 17. Security Considerations

1. **AgnosticV repos are never cloned.** All catalog metadata comes from Babylon CRDs via K8s API.
2. **AgnosticVComponent CRDs contain secrets.** RCARS uses an allowlist of extracted fields and discards the full definition immediately.
3. **Showroom repos** are cloned to tmpfs (`emptyDir` with `medium: Memory`). Content is never persisted to PVs.
4. **Babylon kubeconfig** is read-only and stored as an OpenShift Secret.
5. **GCP/Vertex AI credentials** are stored as an OpenShift Secret, never in Helm values or ConfigMaps.
6. **All admin actions are logged** in the `analysis_log` table with user identity.
7. **OAuth proxy** handles TLS termination and SSO before requests reach the app.

---

## 18. Project Structure (New)

```
rcars/
├── README.md
├── CHANGELOG.md
├── pyproject.toml
├── Dockerfile
├── .claude/
│   └── CLAUDE.md
├── helm/
│   └── rcars/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── charts/
│           ├── app/
│           ├── postgresql/
│           └── oauth-proxy/
├── src/
│   ├── rcars/
│   │   ├── __init__.py
│   │   ├── cli.py                  # Click CLI (preserved)
│   │   ├── config.py               # Env var config + client factories
│   │   ├── db.py                   # PostgreSQL + pgvector (replaces SQLite + ChromaDB)
│   │   ├── catalog_reader.py       # Babylon CRD client (replaces scanner.py)
│   │   ├── analyzer.py             # Showroom analysis (improved prompts)
│   │   ├── recommender.py          # pgvector search + Sonnet ranking
│   │   ├── event_parser.py         # Event URL parsing
│   │   ├── enrichment.py           # Type 2 tag management
│   │   ├── scheduler.py            # APScheduler job definitions
│   │   └── jobs.py                 # Background job runner
│   └── web/
│       ├── app.py                  # FastAPI routes + auth middleware
│       ├── auth.py                 # OAuth + OpenShift groups
│       ├── static/
│       └── templates/
├── prompts/
│   ├── analyze_showroom.txt        # Improved: boilerplate skip, learning objectives
│   ├── match_event.txt
│   └── recommend.txt
├── docs/
│   └── superpowers/
│       └── specs/
└── tests/
```
