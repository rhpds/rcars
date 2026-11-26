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

Stage copies of one CI share a `stage_key`. Soft retirement, the Advisor
retirement filter, Browse retirement badges, performance joins and the ignore flag
all match on `stage_key`. Do not write a regex or a name split for this.

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
