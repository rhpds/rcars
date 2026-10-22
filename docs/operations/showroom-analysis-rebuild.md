# Rebuild Babylon Showroom analysis

This is an **opt-in maintenance operation**, not a deploy/startup migration.
Do not run it without separate approval for the selected environment and content
IDs. Production is not authorized by this change. Never use `init-db --drop`,
table drops, or truncation for this rebuild.

## What changes

For the enumerated Babylon IDs only, reset generated Showroom analysis fields,
generated entity-card fields, summary/module embeddings, scan state, and overlap
candidates involving those IDs. Analysis rows remain in place to preserve curated
duration, notes, enrichment-review flags, and review reasons. Source provenance,
curator URL/path overrides, catalog identity and metadata, retirement state and
workflows, Jira/GitHub links, usage/performance/nonprod/field-source records,
advisor/job/token history, enrichment, infrastructure/workloads, vocabulary,
credentials and roles are not reset. OSSPA analysis/embeddings are untouched.
Ordinary non-Showroom sandbox cards come from the infrastructure-summary workflow;
they are excluded from this reset and its affected-item counts, even when selected
by `--all-babylon`.

## Maintenance prerequisites

1. Obtain approval for the API-only dev deployment; deploy the complete isolation
   change from an approved pushed feature ref or merge. Never deploy partial
   implementation slices or uncommitted binary builds. Verify additive schema
   columns and a small fixture set before any bulk reset.
2. Record preservation snapshots/backups securely **outside the repository**:
   selected identities, human Showroom fields, retirement state/workflow links,
   source overrides, usage records, advisor/job/token history, and OSSPA counts
   and artifacts. Keep a record of the selected IDs and dry-run counts.
3. Stop scheduled and manual scan producers: disable maintenance scheduling and
   block refresh/scan/rescan endpoints and maintenance submissions for the window.
   Stop **all** scan-worker replicas, including any local development workers.
   Stop and wait for all CLI scans, catalog refreshes and sandbox-summary processes.
   Coordinate with other operators; a replica count of zero does not stop a CLI.
4. Drain/discard previously queued and in-progress scan work from Redis/arq and
   reconcile the corresponding DB job states using the existing operational
   tooling. Preserve job records; do not delete history. Confirm no worker or
   thread can still persist a pre-reset result, including timed-out CLI processes.
5. With producers still blocked, refresh catalog source metadata using the **new**
   resolver (`rcars refresh`) and let that command finish. Inspect invalid and
   ambiguous sources; they are failures, not ordinary no-Showroom sandboxes.
   Reconfirm quiescence and drained work after refresh.

The reset rejects outstanding queued/running scan-related DB jobs. **That check
cannot detect every CLI process or prevent a new producer race.**
`--confirm-scans-paused` is an operator attestation to the prerequisites above,
not an automatic proof that the system is race-safe while producers are running.

## Dry run, review, then execute

From `src/api`, with `RCARS_DATABASE_URL` securely supplied in the environment
(do not write endpoints or credentials into this document):

```bash
python scripts/rebuild_babylon_analysis.py \
  --content-id babylon:example.content.prod \
  --content-id babylon:example.virtual.dev
```

The default is read-only. Review the exact IDs and counts, preservation snapshots,
and approval before adding both execution flags:

```bash
python scripts/rebuild_babylon_analysis.py \
  --content-id babylon:example.content.prod \
  --content-id babylon:example.virtual.dev \
  --execute --confirm-scans-paused
```

For an approved full Babylon rebuild, use `--all-babylon` instead of repeated
`--content-id`; this includes retired IDs so contaminated artifacts do not remain
behind. It still leaves identities retired and does not scan them.

## Rebuild and verify

Keep ordinary producers blocked until the controlled rebuild is finished. Use
the existing scanner for the reset targets, not a second scanning implementation:

```bash
rcars scan --content-id babylon:example.content.prod \
  --content-id babylon:example.virtual.dev
```

For the approved full rebuild, `rcars scan` processes every eligible active stage
that needs work, including virtual items. Do not add `--force` routinely: unchanged
complete items skip jobs/LLM/embeddings; content-identical commits only advance the
verified revision; embedding-only changes repair affected artifacts. `--force`
is available when separately requesting analysis from scratch.

Verify LB2081b/c fail with insufficient/template-only content rather than Ansible
analysis, while LB2081a retains correct PQC analysis. Check differing stage refs,
a multi-hop virtual chain whose content component has no CatalogItem, independent
same-URL/hash items, fresh target-specific embeddings, and source/signature/donor
provenance. Compare all preservation snapshots and ensure failed scans cannot
search the old summary. Retired items must remain retired.

After all scans finish, recompute overlap candidates/assessments using the existing
overlap workflow. Confirm no old scan jobs remain, then restore scan workers,
manual producers and maintenance scheduling. A second routine run should submit
no unchanged analysis jobs. Rollback must use reviewed backups; do not restore
contaminated derived artifacts automatically or discard historical records.
