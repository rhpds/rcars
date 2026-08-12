# LLM Overlap Assessment Design

**Jira:** RHDPCD-614
**Date:** 2026-08-10
**Status:** Draft

## Problem

The overlap detection pipeline uses cosine similarity between summary embeddings to identify potentially redundant catalog items. This produces a percentage score but gives reviewers no actionable context — they must read both summaries and mentally assess whether the items truly overlap. Two OpenShift labs can score 92% similar because they share vocabulary, but one teaches deployment and the other teaches troubleshooting. The embedding score catches topic proximity but misses pedagogical and structural differences.

## Solution

Add an LLM-powered assessment to overlap pairs that produces a structured verdict: what specifically overlaps, what differentiates each item, and whether one could subsume the other. The assessment runs in hybrid mode — batched nightly for near-duplicate pairs (>=95%), computed on-demand when a reviewer opens the comparison drawer for lower-scoring pairs.

## Scope Boundaries

- **Overlap only (same source).** LLM assessment runs on `relationship_type='overlap'` pairs only — Babylon↔Babylon, portfolio_architecture↔portfolio_architecture. Same-source pairs always share the same analysis table, so no cross-table queries needed.
- **Related pairs (cross source) are out of scope.** Babylon↔portfolio_architecture pairs are recommendation signals ("you might also like..."), not consolidation candidates. No LLM assessment needed.
- **No new tables.** Assessment data lives on the existing `content_similarity` row as a JSONB column.

## Existing Overlap Fixes (bundled)

Two issues in the current overlap implementation addressed in this branch:

### 1. Access level: `require_admin` → `require_curator`

The overlap report endpoint (`GET /admin/overlap`) and compute-similarity endpoint (`POST /admin/compute-similarity`) currently use `require_admin`. Curators are the ones making retirement and consolidation decisions — they need access to overlap data. Changed to `require_curator` (which includes admins). The new assessment endpoint also uses `require_curator`.

### 2. "Related" score band renamed to "Moderate"

The 0.75–0.84 score band in the overlap UI was labeled "Related", which conflicts with `relationship_type='related'` (cross-source pairs). Renamed to "Moderate" to avoid confusion:

- **Near-Duplicate** (>=95%) — unchanged
- **High Overlap** (85%–94%) — unchanged
- **Moderate** (75%–84%) — was "Related"

Changes in `_score_band()` return value, frontend band labels, and CSS class names.

## Schema

Two columns added to `content_similarity`:

```sql
ALTER TABLE content_similarity ADD COLUMN IF NOT EXISTS llm_assessment JSONB;
ALTER TABLE content_similarity ADD COLUMN IF NOT EXISTS assessed_at TIMESTAMPTZ;
```

The `llm_assessment` JSONB structure:

```json
{
  "verdict": "redundant | complementary | differentiated",
  "shared_topics": ["OpenShift deployment", "CI/CD pipeline setup"],
  "differentiators_a": ["Focuses on GitOps-based deployment workflow"],
  "differentiators_b": ["Focuses on manual oc CLI deployment"],
  "recommendation": "merge | keep_both | retire_one",
  "rationale": "Both labs walk through deploying an application to OCP4 with near-identical module structure. Lab A adds a GitOps section that Lab B lacks.",
  "model": "claude-sonnet-4-6",
  "tokens": {"input": 1200, "output": 400}
}
```

**Lifecycle:** Assessments are wiped when `compute_content_similarity()` runs its `DELETE FROM content_similarity` — correct behavior since changed embeddings mean the old assessment is stale. The nightly batch re-populates >=95% pairs.

## LLM Prompt Design

### Input data per item

The prompt receives the full analysis profile for each item, pulled from the source-appropriate analysis table (`showroom_analysis` for Babylon, `architecture_analysis` for portfolio architectures when implemented).

Fields included, in priority order:

**Primary comparison surface (hard facts from content):**
- `learning_objectives_json` — stated objectives are verbatim from the lab; inferred objectives are LLM-derived but grounded in module content
- `modules_json` — actual module titles and structure
- `products_json` — products installed, configured, or demonstrated
- `summary` — LLM-generated summary of the content

**Supplementary context (LLM-inferred, may not reflect actual content):**
- `audience_json` — inferred target audience
- `difficulty` — inferred difficulty level
- `estimated_duration_min` — estimated length
- `use_cases_json` — inferred use cases
- `topics_json` — short category labels

The prompt explicitly instructs the model: "Compare primarily on learning objectives, module content, and products. Use audience, difficulty, and topics as supplementary context only — these are LLM-inferred during content scanning and may not accurately reflect the actual content."

### Prompt file

New file: `src/api/rcars/prompts/overlap_assessment.txt`

Follows the existing prompt pattern (system instructions + data section split) used by `rationale_single.txt`.

### Output format

Structured JSON. Parsed via the existing `parse_analysis_response()` utility.

## Backend Service

### New module: `src/api/rcars/services/overlap_assessment.py`

**Core function:**

```python
def assess_overlap(pool, settings, content_id_a, content_id_b) -> dict
```

1. Query `content_similarity` for the pair — return cached `llm_assessment` if `assessed_at` is set
2. Load both items' analysis data from the appropriate analysis table (determined by source from `content_entities`)
3. Format the comparison prompt with both items' analysis profiles
4. Call `call_llm()` with the configured overlap model
5. Parse structured JSON response via `parse_analysis_response()`
6. Persist to `content_similarity.llm_assessment` + set `assessed_at`
7. Return the assessment dict

**Batch function:**

```python
def batch_assess_overlaps(pool, settings, min_score=0.95) -> dict
```

1. Query all `relationship_type='overlap'` pairs with `similarity_score >= min_score` and `llm_assessment IS NULL`
2. Call `assess_overlap()` for each pair (sequential — LLM calls are the bottleneck, not DB). Individual pair failures are logged and skipped — one bad pair doesn't block the batch. Pairs where either item lacks analysis data are skipped with a log entry.
3. Return summary: pairs assessed, pairs skipped, tokens used, errors

### Config

New setting in `config.py`:

```python
overlap_model: str = "claude-sonnet-4-6"
```

Follows the existing pattern of `triage_model` and rationale model configuration via `RCARS_OVERLAP_MODEL` env var.

## API

### New endpoint

```
GET /admin/overlap/{content_id_a}/{content_id_b}/assessment
```

- **Auth:** `require_curator` (curators need overlap data for retirement decisions; admins included)
- **Behavior:** Returns cached assessment if available, otherwise computes on-demand, persists, and returns. If either item lacks analysis data (not yet scanned), returns `null` assessment with a reason field.
- **Response:** The `llm_assessment` JSONB object plus `assessed_at` timestamp

## Nightly Pipeline Integration

After `compute_content_similarity()` completes in the nightly pipeline, a new step calls `batch_assess_overlaps()` for all overlap pairs >=95% that lack an assessment. This runs on the scan worker queue since it's a batch operation.

## Frontend

### ComparisonDrawer enhancement

The existing `ComparisonDrawer` in `ContentAnalysisPage.tsx` gains a new section below the two summaries:

- **Assessment section** — appears when the drawer opens, fetched from the new endpoint
- **Loading state** — spinner while assessment computes (on-demand path)
- **Verdict badge** — color-coded: red for "redundant", amber for "complementary", green for "differentiated"
- **Shared topics** — list of what overlaps
- **Differentiators** — side-by-side lists of what's unique to each item
- **Recommendation** — merge / keep_both / retire_one with the rationale text

### No changes to the overlap list view

The main overlap table and score bands remain unchanged. The LLM assessment is accessed through the existing Compare flow (click the score badge to open the drawer).

## Testing

- Unit test for prompt formatting with full analysis data
- Unit test for assessment JSON parsing (valid response, truncated response, missing fields)
- Unit test for cache hit path (returns existing assessment without LLM call)
- Integration test for the endpoint (requires DB + LLM, mark accordingly)
