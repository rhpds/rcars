---
title: Content Overlap Detection
description: How RCARS finds catalog items that teach the same material
---

# Content Overlap Detection

As the RHDP catalog grows, different teams build labs that cover the same
material under different names and structures. Content overlap detection helps
curators find these duplicates.

This is a curator tool. It is not part of the recommendation pipeline.

## How candidates are found

Overlap uses the structured analysis fields, not embedding distance. Two items
are a candidate pair when:

1. Both are active Babylon items with a `showroom_analysis` row. Items under
   `babylon:tests.` are ignored.
2. They share at least `overlap_min_products` products (default 1) and at least
   `overlap_min_topics` topics (default 2).
3. Their `content_hash` values differ. Equal content is the same content, not an
   overlap.

The query lives in `src/api/rcars/db/overlap.py` (`CANDIDATE_SQL`). Results are
stored in `overlap_candidates`, one row per pair.

### One row per item

Stage copies of one CI share a `stage_key`. They count as one item, and the
highest stage represents them: `prod` > `event` > `dev`. Items without a
`stage_key` use their `content_id`.

### Family pairs are not overlaps

A virtual CI (`published.*`) and a member of its family are the same content, not
an overlap. The query skips that pair by comparing `stage_key` values in
`catalog_family_members`, so the rule holds whichever stage copy represents each
side. Two virtual CIs that share a component are two items and may overlap. See
[Catalog Identity](catalog-identity.md).

## LLM assessment

Each candidate pair is assessed by the LLM (`services/overlap_assessment.py`,
prompt `prompts/overlap_assessment.txt`). The assessment returns:

| Field | Values |
|-------|--------|
| `verdict` | `redundant`, `complementary`, `differentiated` |
| `recommendation` | `merge`, `keep_both`, `retire_one` |
| `shared_topics`, `differentiators_a`, `differentiators_b`, `rationale` | free text |

Unassessed and stale pairs are assessed in the nightly maintenance pipeline.

## Nightly pipeline

Step 6 of the nightly maintenance pipeline:

1. Prune candidates where either item is retired or has no analysis.
2. Generate candidates with `generate_overlap_candidates()`.
3. Assess unassessed or stale candidates with `batch_assess_overlaps()`.

Candidates that no longer meet the threshold are deleted on the next run.

## Overlap Report Page

The overlap page (`/analysis/overlap`) provides an item-centric, paginated view.

**Header area:** Stats (redundant, complementary, differentiated, unassessed),
verdict filter, stage filter, and search.

**Item rows:** Each shows display name, `ci_name`, content type, category, and
neighbor count. Click to expand and see all neighbors with their verdicts and
stages.

**Comparison drawer:** Clicking a neighbor's verdict badge opens a side drawer
that shows the assessment for the pair.

**Top-level items** are filtered by stage (prod by default). **Neighbors** show
items from all stages, so a prod item can see dev or event overlaps.

## Browse Card Integration

The "Similar Content" section on browse cards shows the top neighbors for each
content entity, with a link to the full overlap report.

## Integration Points

- **Overlap page** (`/analysis/overlap`) — item-centric report with comparison drawer
- **Browse page** — expanded items show a "Similar Content" section
- **Sync page** (`/system/sync`) — "Refresh Similarity" action card
- **Nightly pipeline** — Step 6
- **API** — item-centric report, per-item similarity, and queued recomputation
- **CLI** — `rcars overlap-candidates`
