# RCARS — RHDP Content Advisory & Recommendation System

AI-powered content intelligence for the Red Hat Demo Platform. RCARS reads every lab and demo in the RHDP catalog, understands what each one teaches, and uses that understanding to help teams find the right content, detect duplicate material, and identify items that should be retired.

## What It Does

- **Recommendations** — Ask a question in plain English ("what should we show at a Kubernetes conference?") and get a ranked list of catalog items with rationales
- **Content Overlap Detection** — Pairwise semantic comparison across the catalog to surface duplicate or near-duplicate labs
- **Retirement Analysis** — Scores every catalog item based on provisions, sales impact, cost, and age to identify retirement candidates
- **Infrastructure Metadata** — Extracts workload mappings, cloud providers, and platform details from AgnosticD v2 configurations
- **Catalog Browse** — Filterable view of all catalog items with curator controls for content management

## Architecture

Four deployments on OpenShift: React frontend, FastAPI API, arq workers (scan + recommend), PostgreSQL with pgvector. LLM analysis via LiteMaaS (primary) with Vertex AI fallback. Nightly pipeline handles catalog refresh, stale detection, workload scanning, content similarity, and reporting sync.

## Documentation

Full documentation is published at **[rhpds.github.io/rcars](https://rhpds.github.io/rcars/)**.

- [Overview](https://rhpds.github.io/rcars/overview/) — What RCARS is and how it works
- [Web Guide](https://rhpds.github.io/rcars/user/web-guide/) — Using the web interface
- [CLI Guide](https://rhpds.github.io/rcars/admin/cli-guide/) — Command-line reference
- [System Design](https://rhpds.github.io/rcars/architecture/system-design/) — Architecture and data model
- [Operations](https://rhpds.github.io/rcars/admin/operations/) — Deployment, monitoring, and maintenance
- [Development](https://rhpds.github.io/rcars/admin/development/) — Local setup and contributing

## Contributing

All changes must go through a pull request to the `main` branch. The project owner will review and merge. Direct pushes to `main` are blocked by branch protection.

To promote changes to production, open a PR from `main` to the `production` branch. See the [Deployment Guide](https://rhpds.github.io/rcars/admin/deployment/) for the full release process.

## Deployment

RCARS is deployed to OpenShift via Ansible. See `ansible/` for playbooks and `ansible/vars/common.yml` for shared configuration. Environment-specific vars (`dev.yml`, `prod.yml`) are gitignored.

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags deploy
```

## Local Development

```bash
./dev-services.sh start    # PostgreSQL, Redis, API, workers, frontend
./dev-services.sh stop
```

See the [Development guide](https://rhpds.github.io/rcars/admin/development/) for full setup instructions.
