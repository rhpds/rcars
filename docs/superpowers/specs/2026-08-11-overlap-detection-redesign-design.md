# Overlap Detection Redesign

**Date:** 2026-08-11
**Jira:** TBD (will be assigned before implementation)
**Supersedes:** 2026-08-10-llm-overlap-assessment-design.md, 2026-07-29-overlap-analysis-redesign-design.md

## Problem

The current overlap detection uses cosine similarity on summary embeddings as the candidate funnel. This produces 51,677 pairs at ≥75% threshold, most of which are noise (shared OpenShift vocabulary ≠ content overlap). Stage variants (dev/event/prod of the same CI) account for 640 of 786 near-duplicate pairs, and 79% of LLM assessment token spend is wasted confirming that stage copies are identical.

The nightly pipeline DELETEs the entire `content_similarity` table before recomputing, wiping cached LLM assessments. Step 7 then re-assesses ~772 pairs from scratch at ~1.9M tokens per run.

The cosine score (e.g., "92% similar") is meaningless to curators — they need verdicts: redundant, complementary, or differentiated.

## Scope

**Goal 1 only: Negative similarity.** Surface genuinely redundant content for merge/retirement.

Goal 2 (positive similarity — "you found X, Y is similar") is out of scope. Advisor vector search already handles recommendations. The Browse page's "Similar Content" and "Related Content" sections are removed.

## Design

### Candidate Funnel: Deterministic Structured Matching

Replace cosine similarity with deterministic matching on structured data already extracted by the scan LLM into `showroom_analysis`:

- **Product overlap:** Items sharing products from `products_json` (consistent vocabulary — same LLM extracts all items).
- **Topic overlap:** Items sharing topics from `topics_json`.

Default thresholds: ≥1 shared product AND ≥2 shared topics. Configurable via Settings.

**Validation against known data:** ≥1 product + ≥2 topics produces ~291 candidate pairs and catches 82/87 (94%) of known LLM-confirmed redundancies. The 5 misses (2 unique comparisons duplicated by stage variants) are caught at ≥1 topic. Tuning down to ≥1 topic covers 100% at ~1,096 pairs.

**Stage dedup:** Candidates are generated from stage-deduplicated items. The dedup key is `COALESCE(babylon_items.showroom_url, content_entities.content_id)` — Babylon items sharing a `showroom_url` collapse to one representative (prefer prod > event > dev); non-Babylon entities and Babylon items without a showroom_url use their `content_id` as the dedup key (always unique, always included). Dev-only and event-only items are included — stage dedup prevents comparing the same content to itself across stages, it does not exclude non-prod items.

### Data Model

**New table: `overlap_candidates`**

```sql
CREATE TABLE IF NOT EXISTS overlap_candidates (
    id SERIAL PRIMARY KEY,
    content_id_a TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_id_b TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    shared_products INTEGER NOT NULL DEFAULT 0,
    shared_topics INTEGER NOT NULL DEFAULT 0,
    content_hash_a TEXT,
    content_hash_b TEXT,
    llm_assessment JSONB,
    assessed_at TIMESTAMPTZ,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id_a, content_id_b)
);
CREATE INDEX IF NOT EXISTS idx_overlap_candidates_a ON overlap_candidates(content_id_a);
CREATE INDEX IF NOT EXISTS idx_overlap_candidates_b ON overlap_candidates(content_id_b);
CREATE INDEX IF NOT EXISTS idx_overlap_candidates_assessed ON overlap_candidates(assessed_at);
```

`content_hash_a` and `content_hash_b` store `showroom_analysis.content_hash` at assessment time. Re-assessment triggers when stored hashes differ from current.

**Dropped table:** `content_similarity` and all its indexes.

### Pipeline

Current steps 6 (compute cosine similarity) and 7 (batch LLM assessment) merge into a single step:

1. **Generate candidates** — SQL query joins `showroom_analysis` on both sides, deduplicates by `showroom_url`, computes product and topic overlap counts. `INSERT ... ON CONFLICT DO UPDATE` — no DELETE. New pairs added, existing pairs get overlap counts refreshed.

2. **Prune stale pairs** — Targeted DELETE for pairs where either item has `retired_at IS NOT NULL` or no longer has `showroom_analysis`. Replaces the blanket DELETE.

3. **Assess candidates** — For pairs meeting threshold where `llm_assessment IS NULL` OR `content_hash` differs from stored: call existing `assess_overlap()`. Same LLM call, different trigger.

**Token cost:** Initial run ~291 pairs × ~2K tokens ≈ 580K tokens (Haiku). Subsequent runs: near-zero (only changed content). Down from 1.9M tokens nightly.

### API Changes

**Removed endpoints:**
- `GET /analysis/similarity/stats` — cosine score band stats
- `GET /analysis/similarity` — cosine pair listing
- `GET /catalog/{ci_name}/similar` — similar items for Browse page

**Modified endpoint:** `GET /analysis/overlap`

Query params: `verdict` (redundant/complementary/differentiated/unassessed), `search`, `page`, `page_size`, `min_shared_products`, `min_shared_topics`.

Response: items grouped by verdict with neighbor list showing shared product/topic counts, assessment details, and recommendation. No `similarity_score` or `score_band`.

**Kept as-is:**
- `POST /analysis/overlap/assess` — on-demand pair assessment
- `GET /analysis/overlap/{content_id_a}/{content_id_b}` — single pair detail

**New settings:**
- `RCARS_OVERLAP_MIN_PRODUCTS` (int, default: 1)
- `RCARS_OVERLAP_MIN_TOPICS` (int, default: 2)

### Frontend Changes

**Content Analysis page (overlap tab):**
- Stats: verdict-based counts (redundant, complementary, unassessed) replace cosine score bands
- Filter: verdict dropdown replaces min-score slider
- Item rows: verdict badge + recommendation replaces percentage badge
- ComparisonDrawer: remove cosine score display, keep LLM assessment detail

**Browse page:**
- Remove "Similar Content" section (6a) and "Related Content" section (6b)
- Remove `similarItems` / `similarLoading` state and `getSimilarItems()` call

### Code Removal Scope

Full scrub of `content_similarity` references:

- **DB:** `content_similarity` table definition in `SCHEMA_SQL`, all indexes, ALTER TABLE additions
- **similarity.py:** `compute_content_similarity()`, `get_similar_items()`, `get_overlap_items()`, `get_similarity_stats()`, `_score_band()`, `_build_similar_item()`
- **workers/ops.py:** pipeline steps 6 and 7 (replaced by new single step)
- **API routes:** similarity endpoints, similar items endpoint
- **config.py:** `similarity_storage_threshold`, `similarity_high_threshold` settings (replaced by new overlap settings)
- **Frontend api.ts:** `getSimilarItems()` method, similarity-related API calls
- **Frontend pages:** BrowsePage similar/related sections, ContentAnalysisPage cosine-based rendering
- **overlap_assessment.py:** update to read from `overlap_candidates` instead of `content_similarity`

### What's NOT Changing

- Embeddings table and advisor vector search — untouched
- Scan pipeline (showroom analysis, content_hash computation) — untouched
- LLM assessment prompt and validation logic — reused as-is
- ComparisonDrawer component structure — stays, just drops cosine score
