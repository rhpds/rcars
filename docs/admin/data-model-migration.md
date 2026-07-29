# RCARS Data Model Migration Runbook

**Jira:** [RHDPCD-359](https://redhat.atlassian.net/browse/RHDPCD-359)

This runbook covers the one-time migration from the `catalog_items`-based schema to the
`content_entities`-based generalized content model. Run in dev first to validate, then repeat
for prod.

The migration preserves three categories of data across the schema swap:
- **Advisor sessions** — full query history
- **Retirement workflows** — all active workflows including Jira keys and step timestamps
- **Curator notes** — hand-written notes from `showroom_analysis`

---

## Prerequisites

- Python virtualenv: `~/.virtualenvs/rcars-v2`
- Working directory for the import script: `~/devel/rcars-advisory/src/api`
- Export file path: `~/devel/working/rcars-migration-export-<env>-<date>.json`
- DB password: `ansible/vars/<env>.yml` → `rcars_db_password`

Set these before starting:

```bash
# Dev
KUBECONFIG=~/devel/secrets/rcars-mgmt-dev.kubeconfig
DB_PASSWORD=<rcars_db_password from ansible/vars/dev.yml>
EXPORT_FILE=~/devel/working/rcars-migration-export-dev-2026-07-21.json

# Prod
KUBECONFIG=~/devel/secrets/rcars-mgmt-prod.kubeconfig
DB_PASSWORD=<rcars_db_password from ansible/vars/prod.yml>
EXPORT_FILE=~/devel/working/rcars-migration-export-prod-<date>.json
```

---

## Step 1 — Full database backup (emergency rollback)

Take a complete `pg_dump` before touching anything. This is the rollback target if the
migration fails catastrophically.

```bash
KUBECONFIG=$KUBECONFIG \
  oc exec rcars-postgresql-0 -- pg_dump -U rcars -Fc rcars \
  > ~/devel/working/rcars-full-backup-<env>-$(date +%Y%m%d-%H%M%S).dump
```

Verify it is non-empty and structurally valid:

```bash
ls -lh ~/devel/working/rcars-full-backup-<env>-*.dump

KUBECONFIG=$KUBECONFIG \
  oc exec -i rcars-postgresql-0 -- pg_restore --list \
  < ~/devel/working/rcars-full-backup-<env>-<timestamp>.dump | head -20
```

---

## Step 2 — Selective export (dev only; skip for prod if re-running)

For prod, run the export against the old schema before deploying new code. For dev dry-runs,
use the existing export file and skip to verification.

```bash
KUBECONFIG=$KUBECONFIG \
  oc port-forward rcars-postgresql-0 5432:5432 &
PF_PID=$!

source ~/.virtualenvs/rcars-v2/bin/activate
cd ~/devel/rcars-advisory/src/api

python scripts/migrate_to_content_model.py export \
  --db-url "postgresql://rcars:$DB_PASSWORD@localhost:5432/rcars" \
  --export-file $EXPORT_FILE

kill $PF_PID
```

Verify:

```bash
jq '.advisor_sessions | length'     $EXPORT_FILE
jq '.retirement_workflows | length' $EXPORT_FILE
jq '.curator_notes | length'        $EXPORT_FILE
```

---

## Phase 2 — Deploy new code and schema

This is the point of no return. The deploy drops old tables and creates the new schema.

```bash
ansible-playbook ansible/deploy.yml -e env=<dev|prod> --tags full
```

Verify new tables exist and old ones are gone:

```bash
KUBECONFIG=$KUBECONFIG \
  oc exec rcars-postgresql-0 -- psql -U rcars -d rcars \
  -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
```

Expected present: `content_entities`, `babylon_items`, `performance_channels`, `performance_scores`
Expected gone: `catalog_items`, `reporting_metrics`

---

## Step 3a — Import advisor sessions

Run immediately after deploy. Does not depend on catalog refresh.

```bash
KUBECONFIG=$KUBECONFIG \
  oc port-forward rcars-postgresql-0 5432:5432 &
PF_PID=$!

source ~/.virtualenvs/rcars-v2/bin/activate
cd ~/devel/rcars-advisory/src/api

python scripts/migrate_to_content_model.py import-sessions \
  --db-url "postgresql://rcars:$DB_PASSWORD@localhost:5432/rcars" \
  --export-file $EXPORT_FILE

kill $PF_PID
```

Verify:

```bash
KUBECONFIG=$KUBECONFIG \
  oc exec rcars-postgresql-0 -- psql -U rcars -d rcars \
  -c "SELECT COUNT(*) FROM advisor_sessions;"
# Expected: matches export count
```

---

## Step 3b — Trigger catalog refresh

The retirement workflow import requires `content_entities` to be populated so foreign keys
can resolve. Trigger catalog refresh and wait before proceeding to 3c.

```bash
KUBECONFIG=$KUBECONFIG \
  oc exec deploy/rcars-api -- \
  sh -c 'curl -s -X POST http://localhost:8080/api/v1/catalog/refresh \
  -H "X-Forwarded-Email: nstephany@redhat.com" | jq .'
```

Poll until populated (~440 rows expected):

```bash
KUBECONFIG=$KUBECONFIG \
  oc exec rcars-postgresql-0 -- psql -U rcars -d rcars \
  -c "SELECT COUNT(*) FROM content_entities;"
```

---

## Step 3c — Import retirement workflows

Run after catalog refresh completes.

```bash
KUBECONFIG=$KUBECONFIG \
  oc port-forward rcars-postgresql-0 5432:5432 &
PF_PID=$!

python scripts/migrate_to_content_model.py import-workflows \
  --db-url "postgresql://rcars:$DB_PASSWORD@localhost:5432/rcars" \
  --export-file $EXPORT_FILE

kill $PF_PID
```

Verify — all active workflows must be present and Jira keys intact:

```bash
KUBECONFIG=$KUBECONFIG \
  oc exec rcars-postgresql-0 -- psql -U rcars -d rcars \
  -c "SELECT content_id, status, jira_key FROM retirement_workflow ORDER BY content_id;"
```

---

## Step 3d — Wait for analysis pipeline

The curator notes import requires `showroom_analysis` rows to exist. Monitor progress:

```bash
KUBECONFIG=$KUBECONFIG \
  oc exec rcars-postgresql-0 -- psql -U rcars -d rcars \
  -c "SELECT COUNT(*) FROM showroom_analysis WHERE summary IS NOT NULL;"
```

Trigger manually via the UI (Sync & Analysis page) or wait for the nightly pipeline.

---

## Step 3e — Import curator notes

Run after the analysis pipeline has populated `showroom_analysis`.

```bash
KUBECONFIG=$KUBECONFIG \
  oc port-forward rcars-postgresql-0 5432:5432 &
PF_PID=$!

python scripts/migrate_to_content_model.py import-notes \
  --db-url "postgresql://rcars:$DB_PASSWORD@localhost:5432/rcars" \
  --export-file $EXPORT_FILE

kill $PF_PID
```

---

## Rollback

If the migration fails at any point after Phase 2, restore from the Step 1 backup:

```bash
# Drop the broken schema
KUBECONFIG=$KUBECONFIG \
  oc exec rcars-postgresql-0 -- psql -U rcars \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Restore
KUBECONFIG=$KUBECONFIG \
  oc exec -i rcars-postgresql-0 -- pg_restore -U rcars -d rcars \
  < ~/devel/working/rcars-full-backup-<env>-<timestamp>.dump

# Redeploy previous API image tag
ansible-playbook ansible/deploy.yml -e env=<dev|prod> --tags api \
  -e git_ref=<previous-tag>
```
