# Overlap Analysis Page Redesign

**Date:** 2026-07-29
**Jira:** [RHDPCD-599](https://redhat.atlassian.net/browse/RHDPCD-599) (child of [RHDPCD-26](https://redhat.atlassian.net/browse/RHDPCD-26))
**Status:** Draft

## Problem

The overlap analysis page at `/analysis/overlap` is unusable. The `GET /api/v1/admin/overlap` endpoint returns all 5,869 `content_similarity` pairs in a single 8.7MB JSON response, crashing the browser. The data is also unprioritized — 63% of pairs fall in the 0.75-0.80 noise band where items are merely in the same domain, not truly overlapping.

Beyond the performance problem, the system needs to support two distinct similarity concepts as new content types (portfolio architectures, interactive experiences) are added:

- **Negative similarity (overlap):** Two items of the same source that are too similar — "why do we have both?" Actionable for de-duplication and retirement decisions. Compared within the same `source` (e.g., Babylon↔Babylon, portfolio_arch↔portfolio_arch).
- **Positive similarity (related):** Items from different sources covering the same topic — "this portfolio architecture relates to this hands-on lab." Useful for content discovery and eventually for cross-type advisor recommendations.

The `source` field on `content_entities` (established in the generalized content model, RHDPCD-359) is the natural isolation boundary. Labs, demos, and sandboxes are all `source='babylon'` — comparing a demo to a lab for overlap is valid. Comparing a Babylon lab to a portfolio architecture is not overlap, it's related content.

## Design

### 1. Data Model Changes

#### `content_similarity` table

Add a `relationship_type` column to distinguish overlap from related-content pairs:

```sql
CREATE TABLE IF NOT EXISTS content_similarity (
    id SERIAL PRIMARY KEY,
    content_id_a TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_id_b TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    similarity_score REAL NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'overlap',  -- 'overlap' or 'related'
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id_a, content_id_b)
);

CREATE INDEX IF NOT EXISTS idx_content_similarity_a ON content_similarity(content_id_a);
CREATE INDEX IF NOT EXISTS idx_content_similarity_b ON content_similarity(content_id_b);
CREATE INDEX IF NOT EXISTS idx_content_similarity_score ON content_similarity(similarity_score DESC);
CREATE INDEX IF NOT EXISTS idx_content_similarity_reltype ON content_similarity(relationship_type);
```

- `overlap`: same-source pairs (e.g., two Babylon items). Powers the overlap report.
- `related`: cross-source pairs (e.g., Babylon lab ↔ portfolio architecture). Powers the "Related content" section on browse cards.

The UNIQUE constraint on `(content_id_a, content_id_b)` remains — a pair is either overlap or related, never both (same-source = overlap, cross-source = related).

#### Configuration changes

In `config.py`:

- `similarity_threshold`: 0.75 → 0.85 (display default for both overlap report and browse card similar items)
- `similarity_high_threshold`: 0.85 → 0.95 (near-duplicate boundary for the top score band)
- Storage threshold remains 0.75 (passed to `compute_content_similarity()` — the database cost is trivially small and keeping 0.75+ pairs allows users to explore weaker relationships via the filter)

### 2. Backend Changes

#### `compute_content_similarity()` — Generalized computation

The function currently computes pairs within a single Babylon stage, filtering by Babylon-specific fields (`bi_a.stage`, `bi_a.is_published`). It needs to be generalized to work across content sources while keeping source-specific filters.

**Overlap pairs (same source):**
```sql
INSERT INTO content_similarity (content_id_a, content_id_b, similarity_score, relationship_type, computed_at)
SELECT a.content_id, b.content_id,
       1.0 - (a.embedding <=> b.embedding),
       'overlap',
       NOW()
FROM embeddings a
JOIN embeddings b ON a.content_id < b.content_id
JOIN content_entities ce_a ON ce_a.content_id = a.content_id
JOIN content_entities ce_b ON ce_b.content_id = b.content_id
WHERE a.embed_type = 'summary'
  AND b.embed_type = 'summary'
  AND ce_a.source = ce_b.source                     -- same source = overlap
  AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
  AND ce_a.retired_at IS NULL
  AND ce_b.retired_at IS NULL
```

For Babylon items specifically, the existing filters remain — published items (event-branded copies) and stage filtering are applied via a LEFT JOIN to `babylon_items`:

```sql
  -- Babylon-specific exclusions (no-op for non-Babylon sources)
  AND (bi_a.content_id IS NULL OR (bi_a.is_published IS NULL OR bi_a.is_published = FALSE))
  AND (bi_b.content_id IS NULL OR (bi_b.is_published IS NULL OR bi_b.is_published = FALSE))
```

**Related pairs (cross source):**
```sql
INSERT INTO content_similarity (content_id_a, content_id_b, similarity_score, relationship_type, computed_at)
SELECT a.content_id, b.content_id,
       1.0 - (a.embedding <=> b.embedding),
       'related',
       NOW()
FROM embeddings a
JOIN embeddings b ON a.content_id < b.content_id
JOIN content_entities ce_a ON ce_a.content_id = a.content_id
JOIN content_entities ce_b ON ce_b.content_id = b.content_id
WHERE a.embed_type = 'summary'
  AND b.embed_type = 'summary'
  AND ce_a.source != ce_b.source                    -- different source = related
  AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
  AND ce_a.retired_at IS NULL
  AND ce_b.retired_at IS NULL
```

Cross-source pairs produce no results today (only Babylon has embeddings). The query is ready for when portfolio architectures are ingested.

The function deletes all existing rows before re-inserting (current behavior, unchanged).

The existing `stage` parameter on the endpoint remains for backward compatibility but only applies to Babylon overlap pairs.

#### New endpoint: `GET /api/v1/admin/overlap` — Paginated, item-centric

Replace the current dump-all response with an item-centric, paginated API.

**Request parameters:**
- `min_score` (float, default 0.85): minimum similarity score for display
- `stage` (str, optional): filter Babylon items by stage
- `content_type` (str, optional): filter to items of a specific content_type
- `source` (str, optional): filter to items of a specific source
- `search` (str, optional): text search on display_name
- `page` (int, default 1): page number
- `page_size` (int, default 100): items per page
- `relationship_type` (str, default 'overlap'): 'overlap' or 'related'

**Response shape:**
```json
{
  "items": [
    {
      "content_id": "babylon:openshift-cnv.ocp4-getting-started.prod",
      "display_name": "OCP Getting Started (AWS)",
      "content_type": "lab",
      "source": "babylon",
      "category": "workshop",
      "stage": "prod",
      "max_score": 0.96,
      "neighbor_count": 4,
      "score_band": "near_duplicate",
      "neighbors": [
        {
          "content_id": "babylon:openshift-cnv.ocp4-getting-started-azure.prod",
          "display_name": "OCP Getting Started (Azure)",
          "content_type": "lab",
          "source": "babylon",
          "category": "workshop",
          "stage": "prod",
          "similarity_score": 0.96
        }
      ]
    }
  ],
  "total_items": 47,
  "page": 1,
  "page_size": 100,
  "stats": {
    "near_duplicates": 10,
    "high_overlap": 35,
    "related_band": 120,
    "total_pairs_stored": 5869,
    "last_computed": "2026-07-29T04:00:00Z"
  },
  "thresholds": {
    "display": 0.85,
    "near_duplicate": 0.95
  }
}
```

**SQL approach:** Group pairs by item, count neighbors, return items sorted by `max_score DESC, neighbor_count DESC`. Each item includes its full neighbor list (filtered by `min_score`). With ~47 items at 0.85, pagination won't usually be needed, but is available for lower thresholds.

```sql
WITH item_scores AS (
    SELECT content_id, MAX(similarity_score) AS max_score, COUNT(*) AS neighbor_count
    FROM (
        SELECT content_id_a AS content_id, similarity_score FROM content_similarity
        WHERE similarity_score >= %(min_score)s AND relationship_type = %(relationship_type)s
        UNION ALL
        SELECT content_id_b AS content_id, similarity_score FROM content_similarity
        WHERE similarity_score >= %(min_score)s AND relationship_type = %(relationship_type)s
    ) AS all_sides
    GROUP BY content_id
    ORDER BY max_score DESC, neighbor_count DESC
    LIMIT %(page_size)s OFFSET %(offset)s
)
SELECT is.content_id, is.max_score, is.neighbor_count,
       ce.display_name, ce.content_type, ce.source
FROM item_scores is
JOIN content_entities ce ON ce.content_id = is.content_id
```

Neighbors for each item on the page are fetched in a second query using the existing `get_similar_items()` pattern (query both directions of the pair).

#### `get_similar_items()` — Add relationship_type filter

The existing per-item endpoint (`GET /api/v1/catalog/{identifier}/similar`) gets a `relationship_type` query parameter:
- `overlap` (default): same-source similar items
- `related`: cross-source related items
- `all`: both, with `relationship_type` included in each result

Default min_score raised to 0.85 (matching the new `similarity_threshold`).

#### `get_similarity_stats()` — Updated stats

Stats query adds breakdowns by relationship_type and score band:
- Near-duplicates (overlap, >= 0.95): count
- High overlap (overlap, 0.85-0.94): count
- Related (related, >= 0.85): count
- Total pairs stored (all, >= 0.75): count
- Last computed timestamp

### 3. Frontend Changes

#### Overlap Report Page (`ContentOverlapPage.tsx`) — Rewrite

**Layout:** Item-centric list with score-band sections.

**Header area:**
- Stats bar: item counts per band, last computed timestamp
- Filter bar: min score (default 0.85, adjustable), stage dropdown, source dropdown, search input
- "Refresh Similarity" button (calls POST compute-similarity, shows spinner)

**Score-band sections:**
Three collapsible sections, each showing items sorted by max_score DESC within the band:

1. **Near-Duplicates (0.95+)** — red score badges. Infra variants of the same content.
2. **High Overlap (0.85–0.94)** — amber score badges. Same topic, likely redundant.
3. **Related (0.75–0.84)** — collapsed by default. Visible when user lowers the threshold filter below 0.85.

**Item rows within each section:**
- Display name, content_type badge, category, stage
- "N similar" count badge
- Max similarity score badge (color-coded by band)
- Click to expand: shows all neighbors with individual pair scores, display names, categories, stages, and links to the item's browse card

**Search behavior:** Typing in the search bar filters the top-level item list by display_name. If you search "Azure", you see "OCP Getting Started (Azure)" with all its neighbors listed — the natural item-centric lookup.

#### Browse Card — Similar Content section update

The existing "Similar Content" collapsible section on browse cards splits into two subsections:

1. **Overlapping Content** (same source, `relationship_type='overlap'`): "These items cover very similar ground." Score badges, color-coded. Only renders when overlap pairs exist for this item.
2. **Related Content** (cross source, `relationship_type='related'`): "Related content from other types." Only renders when cross-source pairs exist (empty until portfolio architectures are ingested).

Both use the 0.85 default threshold. Each neighbor row is clickable, linking to that item's browse card.

The browse card calls `getSimilarItems(identifier, 'all')` and splits the results client-side by `relationship_type`. One API call, two sections.

#### Sync & Analysis Page — Refresh button

Add a "Refresh Similarity" action card to the Sync page (`/system/sync`) alongside existing pipeline triggers (Catalog Refresh, Content Scan, Reporting Sync). Same POST endpoint as the overlap page button. Shows a spinner and completion toast with pair count.

### 4. Nightly Pipeline Integration

Add `compute_content_similarity()` as the final step in the nightly scan pipeline (scan worker).

**Execution order:**
1. Catalog refresh → populates `content_entities` + `babylon_items`
2. Stale check → marks changed content
3. Content analysis → LLM analysis + embedding generation
4. Workload scan → infrastructure metadata
5. Sandbox summary generation → metadata-derived summaries + embeddings
6. Reporting sync → performance metrics
7. **Compute content similarity** (new — last step, after all embeddings are current)

The nightly run uses the storage threshold (0.75) and processes all sources. Both overlap and related pairs are computed in one pass.

### 5. Code Organization — `db/similarity.py`

Extract all similarity logic from the monolithic `database.py` (2,741 lines) into a new `src/api/rcars/db/similarity.py` module. This is the first step toward breaking up `database.py` — scoped to similarity only, broader refactoring is a separate effort.

**What moves:**
- `compute_content_similarity()` — pair computation (lines ~1500-1535)
- `get_overlap_report()` → replaced by new `get_overlap_items()` — item-centric paginated query (lines ~1570-1593)
- `get_similar_items()` — per-item neighbor lookup (lines ~1537-1568)
- `get_similarity_stats()` — aggregate stats (lines ~1595-1619)

**Pattern:** Standalone functions that accept the connection pool as a parameter, not methods on the Database class.

```python
# src/api/rcars/db/similarity.py

from psycopg_pool import ConnectionPool

def compute_content_similarity(pool: ConnectionPool, threshold: float = 0.75, stage: str | None = None) -> dict:
    ...

def get_overlap_items(pool: ConnectionPool, min_score: float = 0.85, ...) -> dict:
    ...

def get_similar_items(pool: ConnectionPool, content_id: str, ...) -> list[dict]:
    ...

def get_similarity_stats(pool: ConnectionPool, relationship_type: str | None = None) -> dict:
    ...
```

**Database class:** The old methods are removed. Routes call `similarity.py` functions directly, passing `request.app.state.db.pool`. This avoids thin wrapper methods that just delegate.

**Routes:** The overlap and compute-similarity endpoints in `admin.py` import from `db.similarity` directly.

### 6. CLI Changes

The `rcars compute-similarity` CLI command updates to match:
- Computes both overlap and related pairs in one run (same as nightly)
- `--threshold` default stays 0.75 (storage threshold)
- `--stage` continues to filter Babylon items by stage for overlap pairs
- Output table shows counts by relationship_type and score band

### 6. What's NOT in Scope

- **Clustering algorithms:** Dropped. Score-band sections + item-centric expand provide structure without algorithmic complexity.
- **Advisor changes:** The advisor will eventually use cross-source similarity for recommendations, but that's a separate effort.
- **Portfolio architecture ingestion:** This design is forward-compatible with new sources but doesn't add any. Cross-source "related" pairs will be empty until another source has embeddings.
- **Module-level similarity:** Only summary embeddings are compared. Module-level overlap detection is a future enhancement.
