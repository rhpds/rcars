# RCARS — RHDP Content Advisory & Recommendation System

Recommendation engine that matches RHDP catalog items to events, booth opportunities,
and field requests. Analyzes Showroom content and uses semantic search + LLM reasoning
to recommend the best assets for any given use case.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up PostgreSQL (local dev)
podman run -d --name rcars-db -p 5432:5432 \
  -e POSTGRESQL_USER=rcars -e POSTGRESQL_PASSWORD=dev \
  -e POSTGRESQL_DATABASE=rcars \
  registry.redhat.io/rhel9/postgresql-16:latest

# Configure
export RCARS_DATABASE_URL="postgresql://rcars:dev@localhost:5432/rcars"

# Refresh catalog from Babylon CRDs (requires oc login)
rcars refresh

# Check status
rcars status
```
