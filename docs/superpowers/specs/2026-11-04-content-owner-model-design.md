# Content Owner Model for Virtual CIs — Design

**Issue:** RHDPCD-2238
**Date:** 2026-11-04
**Status:** Draft, curator-edit rule decided, waiting for review

## Problem

A published (virtual) CI that only points to a base component gets its own
LLM analysis and its own embeddings. The base component gets another one.
The content is the same, but:

- The Advisor shows two cards for one item.
- Browse shows two slightly different summaries for one item (two LLM runs).
- Each scan makes one extra LLM call per stub (about 37k input tokens each).

Evidence from the dev database (2026-11-04):

| | `published.ocp-virt-modernize.prod` | `summit-2026.lb2391-modernize-ocp-virt-combined.prod` |
|---|---|---|
| `owner_ci_name` | summit-2026.lb2391… | summit-2026.lb2391… |
| commit / content_hash | `ab7ef59b` / `ff62d0ff` | `ab7ef59b` / `ff62d0ff` |
| context_hash | `4963f4d7` | `1356a68a` |
| `reused_from` | empty | empty |
| scan LLM calls | 2026-10-19, 2026-11-04 | 2026-10-19, 2026-11-04 |

Dev counts of non-retired pure stubs: 42 prod, 43 dev, 3 event. Each owner has
at most one stub. Each stub is in the same stage as its owner, and no owner is
retired.

## Root cause

The link between a stub and its owner is already known. The resolver walks the
AgnosticV `__meta__.components` chain and stores `owner_ci_name` in
`babylon_items.showroom_source_json`.

The scan and the Advisor do not use that link. They ask whether two CIs have
the same 9-field `AnalysisSignature`. The signature includes `context_hash`,
which hashes the display name and category. A stub and its owner almost always
have different display names, so the signature never matches:

- `find_showroom_donor` (`db/database.py:1852`) finds no donor, so the stub gets
  its own LLM call.
- `_authorized_promotion` (`services/recommender/vector_search.py:126`) does not
  swap the base hit for the stub, so both cards show.

History: the first design shared analyses by repo + commit. That merged
unrelated CIs. RHDPCD-74 (`c30408e`) replaced it with full-signature matching.
That fixed the false merges but blocks real links. This design uses the explicit
link and stops trying to infer it from hashes.

## Model

**The owner owns the analysis.** A pure stub has no analysis and no embeddings
of its own. It shows its owner's analysis.

### Pure stub

A CI is a pure stub when all of these are true for its effective source
(`effective_showroom_source(item)`):

1. `status == "resolved"`
2. `owner_ci_name != item.ci_name`
3. Every value in `override_origins` is the owner. The stub, or a CI between the
   stub and the owner, did not override `repo`, `ref`, or `content_path`.

A curator override on the stub (`showroom_url_override` or `content_path`) puts
the stub in `override_origins`, so rule 3 fails and the CI is not a stub.

Not a stub, and unchanged by this design:

- ZT labs that point to a shared ZT base but override ref or content path
  (115 in prod on dev). Their content is different, so they keep their own scan.
- Owners themselves, and CIs that declare their own Showroom.

Add one helper in `services/showroom_source.py`:

```python
def content_owner(item: dict) -> str | None:
    """Owner CI name when item is a pure stub, else None."""
```

All code paths below use this helper. No path compares signatures to decide
ownership.

### Scan

- `get_items_needing_analysis` skips pure stubs. They never get an LLM call or
  embeddings.
- When a CI becomes a pure stub (first run after deploy, or a catalog change),
  the scan deletes its `showroom_analysis` row and its `embeddings` rows.
- After an owner's analysis is saved, the scan copies the owner's card fields
  (`summary`, `products_json`, `topics_json`, `audience_json`, `difficulty`,
  the fields `update_content_entity_card` writes at `db/database.py:1738`)
  to each of its pure stubs. Browse filters and facets then work with no
  change.
- A stub's `scan_status` mirrors its owner's.
- The stale check skips pure stubs.
- If a stub stops being a stub (for example, a new override), it becomes a
  normal CI and gets scanned on the next run.

### Advisor

Only owners have embeddings, so vector search can return only the owner.

In `vector_search.search`, after the pgvector query and before the first
candidates go to the UI (`pipeline.py:192-200`):

1. For each hit, look up pure stubs whose owner is this hit and whose stage is
   in the requested stages.
2. If exactly one exists, replace the hit with the stub. Keep the hit's
   similarity score. Apply the zt and scope filters to the stub.
3. If none or more than one exists, keep the owner.

This replaces the alias half of `_authorized_promotion` and removes
`get_virtual_content_aliases`. The stage-counterpart half (dev hit promoted to
prod of the same CI) is out of scope and stays as it is.

Card hydration, triage, and rationale read the analysis through a new
`db.get_display_analysis(content_id)`. It returns the owner's
`showroom_analysis` row for a pure stub, and the item's own row otherwise.
Callers to switch: `vector_search.py:226`, `drivers/hands_on.py:55`,
`rationale.py:221`, `api/routes/catalog.py:271` and `:317`.

### Browse

- Browse still lists every CI: virtual, base, owner, and CIs with no owner.
  The row list does not change.
- A stub's card fields come from its owner (copied at scan time).
- A stub's detail view shows its owner's analysis through
  `get_display_analysis`.
- The detail view shows a line such as "Content from
  `summit-2026.lb2391-modernize-ocp-virt-combined.prod`" with a link.

### Overlap

Stubs have no embeddings, so stub/owner pairs drop out of `overlap_candidates`.
They are the same content, not overlapping content.

### Curator edits

Decided 2026-11-04: a curator edit on a stub writes the owner's
`showroom_analysis` row. Stub and owner always show the same curated value,
because they are the same content.

- `PUT /catalog/{id}/duration` (`api/routes/catalog.py:428`) resolves the
  target through `content_owner()` before it calls `set_curated_duration`.
- Any other route that writes curated fields to `showroom_analysis` follows the
  same rule. The implementation plan lists each one.

## What gets removed

- `get_virtual_content_aliases` and the alias half of `_authorized_promotion`.
- The donor path for stubs. `find_showroom_donor` stays for stage siblings
  (RHDPCD-74 `order_for_reuse`). Changing it is out of scope.

## Tests

- A pure stub is skipped by `get_items_needing_analysis` and makes no LLM call.
- A stub with its own ref or content-path override is not a stub and is scanned.
- A CI that becomes a stub loses its own analysis and embeddings.
- Saving an owner analysis copies card fields to its stub.
- Advisor: an owner hit is shown as its stub, even when display names differ.
- Advisor: an owner with no stub, or with two stubs, is shown as the owner.
- Advisor: a stub outside the requested stages or scope is not shown.
- Browse detail of a stub returns the owner's analysis.
- Two unrelated CIs that share a Showroom repo stay separate.

## Rollout

1. Deploy to dev.
2. Run a scan. Check that the 88 dev stubs have no analysis or embedding rows,
   and that their card fields match their owners.
3. Query the Advisor for "OpenShift Virtualization modernization". Expect one
   card, `published.ocp-virt-modernize.prod`.
4. Check the token log: no scan calls for stubs.
