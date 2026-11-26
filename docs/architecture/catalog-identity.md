---
title: Catalog Identity
description: The single owner of "same card" and "same content" decisions
---

# Catalog Identity

RCARS answers three different identity questions. This page names the one answer
for each. Do not add another rule for any of them.

| Question | Answer | Owner |
|----------|--------|-------|
| Is this the published face of that content? | Catalog family | `services/catalog_identity.py` + `catalog_family_members` |
| Is this the same CI in another stage? | `content_entities.stage_key` | `content_entities.stage_key` |
| Is this the same content? | `content_hash` | `services/analysis_identity.py` |

## Catalog family

A **virtual CI** is a catalog item whose name starts with `published.`. Babylon
has no other marker for one.

A virtual CI exists to publish content. The content is declared on one component:
the first component on a path from the virtual CI that declares or overrides any
of `repo`, `ref`, or `content_path`. That component is the **content anchor**.
The virtual CI, every component above the anchor, and the anchor itself form one
**family**. Nothing below the anchor is a member: pools, base clusters and shared
templates only give the content a place to run.

- Each virtual CI is its own family. Families never merge.
- A component can belong to two families. For example, one field-source component
  is a member of both `published.ocp-field-asset` and
  `published.ocp-field-asset-shared`.
- A virtual CI with no content anchor has no members. Each item then stands alone.
- Families live inside one stage. Two stage copies are never in one family.

The family is stored at catalog refresh in two tables:

- `catalog_components` — every component link of the per-stage graph, in declared
  order.
- `catalog_family_members` — one row per (virtual CI, member), with `role`
  (`anchor` or `passthrough`) and `depth`.

`services/catalog.py` builds both tables with `build_catalog_families()` from the
same node graph that the Showroom resolver uses. The refresh replaces both tables
in one transaction and logs a summary.

A member shows as an Advisor card only when **no** covering virtual CI is
eligible. An eligible virtual CI shows instead. Two eligible virtual CIs over one
component show as two cards.

## Stage key

`content_entities.stage_key` is a CI name minus its stage suffix, for example
`agd-v2.ocp-field-asset-cnv` for `agd-v2.ocp-field-asset-cnv.prod`. Only the known
stages (`prod`, `event`, `dev`, `test`) are stripped. A non-Babylon item uses its
`content_id`.

Stage copies of one CI share a `stage_key`. These consumers match on it: Browse
retirement badges (`_SIBLING_RETIREMENT_JOIN`), the Advisor started-retirement
filter, the overlap representative rule and family keys, and the "similar to"
stage-copy exclusion. Do not write a regex or a name split for these.

Other consumers do **not** use `stage_key` for a stage sibling. The Performance
report joins `retirement_workflow` by `content_id`, so an event-stage row does not
inherit a prod sibling's retirement state. The Performance ignore flag updates one
`content_id`. Catalog soft-delete retires one `content_id` at a time. It closes a
retirement workflow only when every known stage name of that CI is gone, and it
builds those names itself instead of reading `stage_key`.

Stage copies are **not** merged by `stage_key` alone. They merge only when the
user selects more than one stage **and** their displayed analyses have the same
non-empty `content_hash`. The highest stage wins: `prod` > `event` > `dev`.
Different content stays as separate cards with stage badges.

## Same content

Two items have the same Showroom content when their `content_hash` is equal.
`content_hash` is the SHA-256 of the selected, filtered files that the LLM reads.
Ref names, tags, commits and CI names never count. `services/analysis_identity.py`
owns the rule. Scan reuse uses it with `analysis_config`; the Advisor stage merge
uses it alone.

## Rescan after a prompt change

The Showroom content prompt carries only the selected content plus the entity
content type. When that prompt changes, bump `SHOWROOM_ANALYSIS_POLICY_VERSION`
in `services/showroom_source.py`. The policy version is part of
`analysis_config` and of every stored signature, so all older analyses stop
matching and are selected for re-analysis.

What triggers the re-analysis:

1. The nightly maintenance pipeline (`run_nightly_pipeline` →
   `run_babylon_pipeline`). Step 2 `run_stale_check` runs the same current check,
   then step 3 `scan_candidates` → `get_items_needing_analysis` →
   `showroom_work_needed` enqueues every item stage whose analysis no longer
   matches. Jobs go to `arq:queue:scan` and run in the background.
2. Manually, without waiting for the night: `rcars scan` analyzes everything
   that needs work, `rcars scan --content-id babylon:<ci_name>` one item, and
   `rcars scan --force` bypasses the unchanged and donor fast paths.

Expected LLM runs on dev (read-only counts, 2026-11-26, after the eligibility
filters of `get_items_needing_analysis`: active lab/demo, non-test, resolved
Showroom or description source, no pure stubs):

- 731 eligible Showroom analyses have a summary; all are policy 1.
  17 eligible Showroom items have no summary. 8 items are description-sourced.
- The 731 prior analyses cover 355 distinct (`content_hash`, entity content
  type) pairs and 401 distinct stored pre-clone groups (repo + stored commit +
  content path + content type).
- Estimate: about 363-426 LLM runs -- 355-401 Showroom leaders, plus up to 17
  items with no prior hash, plus 8 description items. The same batch under the
  old per-CI config needs about 412-469 runs. Treat both as estimates: content
  can change, a fresh commit can move a group, and concurrent jobs in different
  pre-clone groups can miss the same donor.
- Description analyses keep the item fields in their setup
  (`compute_description_analysis_config`) and re-run per item.

Step 3 enqueues and returns; the scan worker runs 5 jobs at a time with a 600s
per-job timeout, and the nightly pipeline has a 7200s timeout of its own.

Timing is not yet measured for a full batch. Dev `jobs` rows for completed
`analyze` jobs over the last 30 days: 1,260 jobs, p50 17.7s, p90 36.9s. Most
were reuse-only; a leader job also clones and calls the LLM, so these values are
a floor, not a batch estimate. Measure the first rescan on dev.

During the rescan the previous analysis stays in `showroom_analysis` and the
Advisor keeps showing it. Each successful re-analysis replaces its row and
clears `is_stale`. A re-analyzed donor row is reusable immediately by other
items with the same content. Old policy-1 rows are never reused, because the
donor lookup excludes stale rows and rejects a different policy version.

After the content is read, a failure of the LLM call, a malformed or
unparseable response, or an embedding error records `scan_status = 'failed'`
but keeps the prior analysis and embeddings, so the item stays visible and the
next scan retries. Source, clone and content-read failures keep their original
behavior. Description-sourced analyses keep their original failure behavior and
do not preserve prior artifacts.

## One owner

`services/catalog_identity.py` is the only place that decides when two Advisor
hits are the same card. It is pure: rows in, rows out. The SQL lookups live in
`Database` and are wired up in `services/recommender/vector_search.py`.

| Function | Job |
|----------|-----|
| `collapse_to_cards()` | Lift hits to eligible covering virtual CIs; keep the member when none is eligible; merge stage copies |
| `merge_stage_copies()` | Merge copies of one `stage_key` with the same `content_hash` |
| `family_violations()` / `enforce_card_invariant()` | Enforce the card invariant at the end of the pipeline |
| `cards_sharing_a_family()` | Deploy smoke check |
| `exclusion_set_for()` | RHDPCD-2298: what "similar to X" must not return |
| `lift_to_covering()` | Resolve a chat reference to its covering virtual CI |

Overlap and chat use the same tables. A virtual CI and its own member are never
an overlap pair. Chat lifts a member to its covering virtual CI.

## Invariant

A finished Advisor result must satisfy all of these:

1. No two cards share a `content_id`.
2. No card is a member of another card's family.
3. No two cards share a `stage_key` with the same `content_hash`.

`enforce_card_invariant()` runs at the end of the pipeline, after triage and
boosts, and drops any card that breaks the rule. `catalog_identity.py` documents
it, and `tests/test_catalog_identity.py` covers every case.

## Deploy smoke check

The Ansible smoke test runs three fixed Advisor queries at depth `low`:
"RHEL AI", "Platform Engineering Roadshow", and "OpenShift Virtualization"
(prod + event). For each result, `rcars check-card-families` reads the family
table and exits non-zero when two cards share a family. This fails the deploy.

Before the first catalog refresh stores families, the check prints a warning and
passes.

## Rules for new code

- Do not add new dedup or card-identity logic. Use `catalog_identity.py`.
- Do not write a stage-name regex or name split. Use `stage_key`.
- Do not add another "same content" rule. Use `content_hash`.
- A change that touches card identity needs a test in `tests/test_catalog_identity.py`.
