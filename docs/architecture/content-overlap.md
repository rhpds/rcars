---
title: Content Overlap Detection
description: How RCARS identifies overlapping content using pairwise embedding comparison
---

# Content Overlap Detection

As the RHDP catalog grows, different teams inevitably build labs that cover the same material under different names and structures. Content overlap detection helps curators find these duplicates by comparing the vector embeddings produced during the [scan pipeline](scan-pipeline.md) — if two items have similar embeddings, they teach similar things, even if they use different wording and module structures.

This is a curator tool for identifying redundant content. It is not part of the recommendation pipeline, though it uses the same embeddings and similarity math.

## Architecture

The overlap system is built on top of the scan and recommendation pipeline infrastructure. No new models, no new external API calls, and no new data collection steps are required.

During the scan pipeline, every analyzed content item gets a **summary embedding** — a 768-dimensional vector that captures what the item is about. These embeddings live in the `embeddings` table and are the same vectors used by the recommendation engine's vector search. The overlap system reuses them for a different purpose: instead of comparing a user's query against item embeddings, it compares item embeddings against each other.

### Relationship Types

The system distinguishes two types of similarity based on the `source` field on `content_entities`:

- **Overlap** (same source) — Two Babylon items that are too similar. "Why do we have both?" Actionable for de-duplication and retirement decisions. This is the negative signal curators act on.
- **Related** (cross source) — Items from different sources covering the same topic, e.g., a Babylon lab and a portfolio architecture. Useful for content discovery. This is a positive signal for cross-type recommendations.

The `relationship_type` column on `content_similarity` stores which type each pair is. A pair is either overlap or related, never both — enforced by the UNIQUE constraint on `(content_id_a, content_id_b)`.

### Code Organization

All similarity logic lives in `src/api/rcars/db/similarity.py` — four standalone functions that accept a `ConnectionPool` as their first argument:

| Function | Purpose |
|----------|---------|
| `compute_content_similarity()` | Compute all pairwise similarity from summary embeddings |
| `get_overlap_items()` | Item-centric paginated query for the overlap report |
| `get_similar_items()` | Per-item neighbor lookup for browse cards |
| `get_similarity_stats()` | Aggregate stats with score-band breakdowns |

These were extracted from the monolithic `database.py` and are not methods on the `Database` class.

## How Cosine Similarity Works

Each embedding is a list of 768 numbers produced by the nomic-embed-text-v1.5 model. These numbers position the item in a high-dimensional semantic space where similar content clusters together. To measure how similar two items are, RCARS computes the **cosine similarity** between their embedding vectors.

Cosine similarity measures the angle between two vectors, ignoring their magnitude. Two vectors pointing in the same direction have a cosine similarity of 1.0 (identical meaning). Two vectors at right angles have a cosine similarity of 0.0 (unrelated topics). In practice, scores below 0.5 indicate little meaningful overlap.

pgvector provides a native cosine distance operator (`<=>`) that computes `1 - cosine_similarity` directly in SQL. RCARS converts this back to similarity (`1.0 - distance`) for human-readable percentage scores.

The key insight is that this comparison captures semantic similarity, not textual similarity. Two items can use completely different wording, different module structures, and different examples — but if they teach the same concepts, their embeddings will point in similar directions and the cosine similarity will be high.

## Computation

The computation runs two SQL queries — one for overlap pairs (same source) and one for related pairs (cross source). Both join the `embeddings` table against itself, compute pairwise cosine distance, filter to pairs above the storage threshold, and upsert results into `content_similarity`.

```sql
-- Overlap pairs (same source)
INSERT INTO content_similarity
    (content_id_a, content_id_b, similarity_score, relationship_type, computed_at)
SELECT a.content_id, b.content_id,
       1.0 - (a.embedding <=> b.embedding), 'overlap', NOW()
FROM embeddings a
JOIN embeddings b ON a.content_id < b.content_id
JOIN content_entities ce_a ON ce_a.content_id = a.content_id
JOIN content_entities ce_b ON ce_b.content_id = b.content_id
WHERE a.embed_type = 'summary' AND b.embed_type = 'summary'
  AND ce_a.source = ce_b.source                     -- same source = overlap
  AND 1.0 - (a.embedding <=> b.embedding) >= 0.75   -- storage threshold
  AND ce_a.retired_at IS NULL AND ce_b.retired_at IS NULL
ON CONFLICT (content_id_a, content_id_b) DO UPDATE
  SET similarity_score = EXCLUDED.similarity_score,
      relationship_type = EXCLUDED.relationship_type,
      computed_at = EXCLUDED.computed_at
```

The `a.content_id < b.content_id` condition ensures each pair is stored exactly once. Published Virtual CIs are excluded (Babylon-specific filter). Pairs below the storage threshold (0.75) are not stored.

### Nightly Pipeline

Similarity computation runs as the final step (Step 6) in the nightly scan pipeline, after all embeddings are current. It uses the storage threshold (0.75) with no stage filter, computing pairs across all stages and sources in one pass.

### Stage-Variant Deduplication

Multiple Babylon CIs often represent the same content in different stages (prod, dev, event). These share the same Showroom URL and produce identical embeddings via sibling propagation, resulting in 100% similarity — which is expected infrastructure duplication, not content overlap.

The overlap report and browse card both deduplicate stage variants using `showroom_url` as the content identity:

- If a neighbor shares the same `showroom_url` as the top-level item, it's skipped (stage variant of self)
- Among remaining neighbors, only the best-scoring entry per `showroom_url` is kept
- When multiple stage variants exist, prod is preferred over dev/event

## Score Bands

Results are classified into three bands based on configurable thresholds:

| Band | Score | Meaning | Color |
|------|-------|---------|-------|
| Near-duplicate | >= 95% | Infrastructure variants or genuinely redundant content | Red |
| High overlap | 85–94% | Same topic, likely redundant — candidates for consolidation | Amber |
| Related | 75–84% | Similar domain, some differentiation | Muted |

Thresholds are sourced from `Settings` (`similarity_threshold`, `similarity_high_threshold`) and passed to the scoring functions — not hardcoded.

## Overlap Report Page

The overlap page (`/analysis/overlap`) provides an item-centric, paginated view grouped by score bands.

**Header area:** Stats bar (near-duplicates, high overlap, total pairs stored), stage filter (prod/dev), score threshold selector, search, and "Refresh Similarity" button.

**Score-band sections:** Three collapsible sections — Near-Duplicates (red, open by default), High Overlap (amber, open by default), Related (collapsed, visible when threshold lowered below 0.85).

**Item rows:** Each shows display name, ci_name, content type badge, category, neighbor count, and max similarity score. Click to expand and see all neighbors with individual scores and stage badges.

**Comparison drawer:** Clicking a neighbor's score badge opens a side drawer showing both items' summaries, products, and topics for comparison. Details are fetched lazily and cached.

**Top-level items** are filtered by stage (prod by default). **Neighbors** show items from all stages — a prod item needs to see dev/event overlaps to catch redundant content being created.

## Browse Card Integration

The "Similar Content" section on browse cards shows the top 5 similar items for each content entity, with a "View in overlap report" link to the full overlap analysis. Items are deduped by `showroom_url` and link clicks open in a new tab.

## Integration Points

- **Overlap page** (`/analysis/overlap`) — item-centric score-band report with comparison drawer
- **Browse page** — expanded items show "Similar Content" section with top 5 neighbors
- **Sync page** (`/system/sync`) — "Refresh Similarity" action card
- **Nightly pipeline** — Step 6, runs after all embeddings are current
- **API** — `GET /admin/overlap` (paginated item-centric report), `GET /catalog/{content_id}/similar` (per-item), `POST /admin/compute-similarity` (trigger)
- **CLI** — `rcars compute-similarity [--stage prod] [--threshold 0.75]`

## Relationship to the Recommendation Pipeline

The overlap system and the recommendation pipeline both use pgvector cosine similarity on the same embeddings, but they serve different purposes:

- **Recommendation** compares a *query embedding* (from user text) against *item embeddings* to find relevant content for a specific request. It runs on demand, per user query.
- **Overlap** compares *item embeddings* against each other to find duplicate content across the catalog. It runs nightly and on-demand by admins, with results cached in `content_similarity`.

## Future: LLM-Powered Assessment

Cosine similarity identifies *how similar* two items are but cannot determine *whether the overlap matters*. Two OpenShift Virtualization labs at 88% similarity might cover the same products but teach different skills (keep both), or might be genuinely redundant (retire one).

[RHDPCD-614](https://redhat.atlassian.net/browse/RHDPCD-614) will add an LLM assessment step to the pipeline: for each high-scoring pair, send both summaries to the LLM to generate a verdict (Redundant / Distinct / Needs Review) and rationale. This will transform the overlap page from a data viewer into an actionable curation tool.

---

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `RCARS_SIMILARITY_THRESHOLD` | `0.85` | Display threshold (high overlap band floor) |
| `RCARS_SIMILARITY_HIGH_THRESHOLD` | `0.95` | Near-duplicate band floor |
| `RCARS_SIMILARITY_STORAGE_THRESHOLD` | `0.75` | Minimum similarity to store a pair |

## CLI

```bash
rcars compute-similarity                    # all stages, default storage threshold
rcars compute-similarity --stage prod       # prod only
rcars compute-similarity --threshold 0.80   # custom storage threshold
```

## API

- `GET /admin/overlap?min_score=0.85&stage=prod&search=text&relationship_type=overlap` — paginated item-centric overlap report
- `GET /catalog/{content_id}/similar?min_score=0.85&relationship_type=all` — similar items for a specific content entity
- `POST /admin/compute-similarity?threshold=0.75&stage=prod` — trigger recomputation
