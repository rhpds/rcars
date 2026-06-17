---
title: Content Overlap Detection
description: How RCARS identifies duplicate lab content using pairwise embedding comparison
---

# Content Overlap Detection

As the RHDP catalog grows, different teams inevitably build labs that cover the same material under different names and structures. Content overlap detection helps curators find these duplicates by comparing the vector embeddings produced during the [scan pipeline](scan-pipeline.md) — if two labs have similar embeddings, they teach similar things, even if they use different wording and module structures.

This is a curator tool for consolidating duplicate content. It is not part of the recommendation pipeline, though it uses the same embeddings and similarity math.

## Architecture

The overlap system is built entirely on top of infrastructure that already exists from the scan and recommendation pipelines. No new models, no new external API calls, and no new data collection steps are required.

During the scan pipeline, every analyzed Showroom lab gets a **CI-level embedding** — a 384-dimensional vector that captures what the lab is about. These embeddings live in the `embeddings` table and are the same vectors used by the recommendation engine's vector search. The overlap system reuses them for a different purpose: instead of comparing a user's query against lab embeddings, it compares lab embeddings against each other.

## How Cosine Similarity Works

Each embedding is a list of 384 numbers produced by the sentence-transformer model. These numbers position the lab in a high-dimensional semantic space where similar content clusters together. To measure how similar two labs are, RCARS computes the **cosine similarity** between their embedding vectors.

Cosine similarity measures the angle between two vectors, ignoring their magnitude. Two vectors pointing in the same direction have a cosine similarity of 1.0 (identical meaning). Two vectors at right angles have a cosine similarity of 0.0 (unrelated topics). In practice, scores below 0.5 indicate little meaningful overlap.

pgvector provides a native cosine distance operator (`<=>`) that computes `1 - cosine_similarity` directly in SQL. RCARS converts this back to similarity (`1.0 - distance`) for human-readable percentage scores.

The key insight is that this comparison captures semantic similarity, not textual similarity. Two labs can use completely different wording, different module structures, and different examples — but if they teach the same concepts (e.g., "deploying applications on OpenShift with GitOps"), their embeddings will point in similar directions and the cosine similarity will be high.

## Computation

The computation is a single SQL query that joins the `embeddings` table against itself, computes pairwise cosine distance, filters to pairs above the threshold, and inserts results into `content_similarity`. With ~100 prod items, this produces about 5,000 pairwise comparisons and completes in under a second.

```sql
-- Simplified version of the actual query
INSERT INTO content_similarity (ci_name_a, ci_name_b, similarity_score)
SELECT a.ci_name, b.ci_name, 1.0 - (a.embedding <=> b.embedding)
FROM embeddings a
JOIN embeddings b ON a.ci_name < b.ci_name   -- each pair once
WHERE a.embed_type = 'ci_summary'
  AND b.embed_type = 'ci_summary'
  AND 1.0 - (a.embedding <=> b.embedding) >= 0.75  -- threshold
  AND ci_a.stage = 'prod'                           -- same stage
  AND ci_b.stage = 'prod'
```

The `a.ci_name < b.ci_name` condition ensures each pair is stored exactly once (A↔B, never both A→B and B→A). Published Virtual CIs are excluded because they have no Showroom content — they are ordering wrappers that point to a base CI.

## Stage Scoping

Comparisons are scoped to a single stage at a time: prod vs prod, event vs event, or dev vs dev. This is by design — the goal is to find different labs that overlap, not to flag that a dev and prod version of the same lab are similar (which is expected and uninteresting).

The stage is selected at computation time via the `stage` parameter on the API endpoint or CLI command. Switching stages clears and recomputes the entire `content_similarity` table.

## Similarity Tiers

Results are classified into two tiers based on configurable thresholds:

| Tier | Score | Meaning | Color |
|---|---|---|---|
| High overlap | ≥ 85% | Near-duplicate content, candidates for consolidation | Red |
| Related | 75–84% | Similar topics with some differentiation | Amber |

Pairs below 75% are not stored.

## Integration Points

- **Admin UI** (`/analysis/overlap`) — stage selector, compute button, expandable pair list with side-by-side summaries
- **Browse page** — expanded items show a "Similar Content" section listing overlapping items with similarity scores
- **API** — `GET /admin/overlap` (global report), `GET /catalog/{ci_name}/similar` (per-item), `POST /admin/compute-similarity` (trigger)
- **CLI** — `rcars compute-similarity [--stage prod] [--threshold 0.75]`

## Relationship to the Recommendation Pipeline

The overlap system and the recommendation pipeline both use pgvector cosine similarity on the same embeddings, but they serve different purposes:

- **Recommendation** compares a *query embedding* (from user text) against *lab embeddings* to find relevant content for a specific request. It runs on demand, per user query.
- **Overlap** compares *lab embeddings* against each other to find duplicate content across the catalog. It runs on demand by an admin, and results are cached in the `content_similarity` table.

The recommendation pipeline has its own deduplication logic (content hash grouping, base-to-published promotion) that operates during query time. The overlap system does not need this — it simply compares all items within a stage.
