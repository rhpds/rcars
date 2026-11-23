# Interactive Experience Ingest — Design Spec

**Jira:** Not assigned
**Date:** 2026-10-29
**Status:** Design — draft for review
**Branch:** `spec/interactive-experience-ingestion`
**Depends on:** [Generalized Content Model](2026-07-20-generalized-content-model-design.md), [Controlled Vocabulary](2026-08-10-controlled-vocabulary-design.md), and [Advisor Content-Type Drivers](2026-09-25-advisor-v2-content-type-drivers-design.md)

## Problem

An **Interactive Experience** is a short, interactive video walkthrough created with **Arcade** that demonstrates a Red Hat product or technical capability. Arcade is the software used to create the asset; Interactive Experience is the content type RCARS catalogs.

Someone who needs an asset to showcase OpenShift Virtualization should be able to search **“OpenShift Vert”** in RCARS and find a relevant Interactive Experience. The result should explain what it demonstrates and provide the actual Arcade link. The user should not need the asset's exact title or know where it is in the spreadsheet.

The [Interactive Experiences Repository_v2 spreadsheet](https://docs.google.com/spreadsheets/d/1t7TJtTL-jbUaCVKVLMMOahbKcL5b1IyCf3uUSCmQo4A/edit?gid=1123598561#gid=1123598561) already holds the inventory, product metadata, descriptions, and extracted guide text needed for discovery.

## Approach

Follow the [Portfolio Architecture Ingest spec](2026-08-06-portfolio-architecture-ingest-design.md) and the existing `services/osspa_sync.py` pattern:

1. Read the source inventory and validate it.
2. Upsert the common `content_entities` card and an IE-specific source row.
3. Apply source publication/retirement status.
4. Analyze new or changed content using one content hash per item.
5. Save the analysis and **one enriched summary embedding per experience**.
6. Expose the content through existing Browse and Advisor integration points.

Add two tables, `interactive_experiences` and `ie_analysis`. Reuse the existing entity registry, embeddings, jobs, scan worker, vocabulary, and recommendation-driver interfaces. One IE sync job performs the source refresh and changed-item analysis, as the portfolio sync does. This design does not add a separate source-state table or a queue of per-item analysis jobs.

### Confirmed decisions

| Decision | Contract |
| --- | --- |
| Content type | All ingested assets are `interactive_experience`; the sheet's `Content Type` is an IE-specific subtype |
| Identity | The sheet's `Number` is permanent and never reused; use `ie:{Number}` |
| Analysis input | Spreadsheet descriptions/product metadata and existing guide-extraction text |
| Content links | `Production Link` is the Arcade experience; `Drupal Page URL` is the Red Hat page hosting that experience |
| Guide text and versions | Use the row's `Guide Extraction JSON` for analysis. Different versions can have different Arcade references; do not use those references to choose or replace the production link |
| Delivery | Browse and Advisor support are both in Phase 1 |
| Scope | No video transcription, image analysis, or performance-metric ingestion |

**Proposed discovery default:** include Interactive Experiences alongside the formats already enabled by default in Browse and Advisor. A product-only search can then find an IE without requiring the user to enable a new type first. Explicit filters and saved format selections still apply. This remains a proposal for review.

## Source Data

Read the configured Google spreadsheet and tab through the Sheets API, using read-only credentials.

| Source setting | Value |
| --- | --- |
| Spreadsheet | Interactive Experiences Repository_v2 |
| Spreadsheet ID | `1t7TJtTL-jbUaCVKVLMMOahbKcL5b1IyCf3uUSCmQo4A` |
| Tab | `Request_Master` |
| Numeric tab ID | `1123598561` |
| Layout observed on 2026-10-29 | One header row and 318 data rows; 251 marked Published |

These IDs belong in configuration, once for the source. They are not repeated on every item. This version supports this one inventory; changing the configured inventory requires a deliberate migration.

### Request_Master — relevant columns

| Column | Use |
| --- | --- |
| `Number` | Permanent identity → `content_id=ie:{Number}` |
| `Status` | Source lifecycle → common publication status and retirement fields |
| `Final Demo Title` | Display name |
| `Primary Product`, `Product` | Declared products; normalize using the existing vocabulary |
| `Primary Topic`, `Topic` | Declared topics |
| `Content Type` | IE subtype → `experience_kind` |
| `Demo Description` | Preferred description |
| `Demo Description (Creator input)` | Description fallback when the preferred field is blank |
| `Description for SEO` | Final description fallback |
| `SEOWords` | Supplemental search context; keywords alone do not prove a capability is demonstrated |
| `Primary Audience`, `Personas` | Declared audience, when present |
| `Production Link` | Direct Arcade experience URL → `production_url` |
| `Drupal Page URL` | Red Hat page hosting the same experience → `drupal_page_url` |
| `Guide Extraction JSON` | Existing guide text for analysis |
| `Language` | Available languages, when declared |

Fetch and persist only the fields needed for this feature. Exclude creator/requestor contact information, internal request notes, Jira/Slack workflow data, assignments, and metrics. Do not store a full spreadsheet row or add a generic raw-source payload to each item.

### Interactive Experience subtypes

The spreadsheet's **`Content Type` is specific to Interactive Experiences**. It describes the kind of experience, rather than selecting the RCARS content type.

| Source value | Stored `experience_kind` |
| --- | --- |
| Business Intro | Business Intro |
| Technical Walkthrough | Technical Walkthrough |
| Interactive Video Demo | Interactive Video Demo |
| Interactive Experience | Preserve the general source label |
| Another nonempty value | Preserve the source text |
| Blank / Undefined | Unknown for display |

Every row above remains `content_type='interactive_experience'` and `is_hands_on=FALSE`. Subtype does not gate ingestion. Use **Interactive Experience** for one asset and **Interactive Experiences** for the category. **Arcade** identifies the software and the direct experience link. The Drupal URL identifies the Red Hat page hosting it; this spec does not invent names for pages or buttons.

### Ingestion Scope & Status Tagging

Ingest identified rows for source tracking. Public discovery requires a usable title, valid `Production Link`, and description or guide text as well as Published status. The Drupal page URL is additional information and may be absent. A missing production link is a source-data issue to report, not a reason to substitute another URL field.

| Source state | RCARS behavior |
| --- | --- |
| `Published`, with usable title/production link/text | `status=prod`; Browse eligible; analyze for Advisor |
| `Published`, but required content is missing | `status=dev`; record a validation error; exclude from public discovery |
| `Request Open`, `Request Approved`, `Demo Received`, `Demo Reviewed` | `status=dev`; keep source metadata for authorized inspection; do not analyze automatically |
| `Retired` | Soft-retire with `retirement_reason=source_retired` |
| `Closed` | Soft-retire with `retirement_reason=source_closed` |
| Blank or unrecognized status | `status=dev`; report the unexpected value; never assume publication |
| Previously imported row absent from a valid full inventory | Soft-retire as `source_missing`, subject to the removal guard in 3h |

Request Approved is a supported contract value, not an observed status in the inspection snapshot. Retired/Closed/missing records also have `status=dev`. A valid republication clears source-owned retirement fields and preserves the same identity.

## Design

### 1. Identity and Naming

```text
content_id   = ie:{Number}
source       = interactive_experiences
content_type = interactive_experience
is_hands_on  = false
```

`Number` is the sole source of identity. Accept a positive integral numeric cell or digit string, canonicalize it to a base-10 string, and reject missing or duplicate IDs before reconciliation. For example, synthetic Number `900001` becomes `ie:900001`.

Row order, title changes, and updated Arcade URLs do not change the ID. Shared URLs or titles do not merge records. Row positions are useful in job diagnostics but need not be stored on each item.

### 2. Schema

Use additive `SCHEMA_SQL` changes in `src/api/rcars/db/database.py`. The common `content_entities.status` column and the shared embeddings/jobs tables already exist. Do not repeat the portfolio spec's historical status migration.

#### 2a. interactive_experiences (new table)

```sql
CREATE TABLE IF NOT EXISTS interactive_experiences (
    content_id          TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    source_number       TEXT NOT NULL UNIQUE,
    source_status       TEXT,
    experience_kind     TEXT,
    production_url      TEXT,
    drupal_page_url     TEXT,
    guide_json          JSONB,
    languages_json      JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_source_sync    TIMESTAMPTZ DEFAULT NOW()
);
```

| Field | Why it is needed |
| --- | --- |
| `source_number` | Connects the item to its permanent sheet Number |
| `source_status` | Preserves the sheet's lifecycle value |
| `experience_kind` | Preserves the IE-specific subtype |
| `production_url` | The same row's `Production Link`: direct access to the Arcade experience |
| `drupal_page_url` | The same row's `Drupal Page URL`: Red Hat page hosting the experience |
| `guide_json` | The text whitelist described in 3c; supports analysis and item questions |
| `languages_json` | Source-declared languages; blank means unknown |
| `last_source_sync` | When the source record was last refreshed |

Title, summary, products, topics, audience, difficulty, publication status, and retirement fields use the existing common entity columns. The spreadsheet/tab IDs stay in configuration. Existing job results and scan-status/error fields provide operational diagnostics.

#### 2b. ie_analysis (new table)

Use the portfolio analysis pattern: common analysis fields, a content hash, a stale flag, and a small set of IE-relevant extracted facts.

```sql
CREATE TABLE IF NOT EXISTS ie_analysis (
    content_id                  TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    summary                     TEXT,
    products_json               JSONB,
    topics_json                 JSONB,
    audience_json               JSONB,
    difficulty                  TEXT,
    detailed_topics_json        JSONB,
    use_cases_json              JSONB,
    content_hash                TEXT,
    last_analyzed               TIMESTAMPTZ,
    is_stale                    BOOLEAN DEFAULT TRUE,
    enrichment_review_needed    BOOLEAN DEFAULT FALSE,
    review_reasons              JSONB
);
```

`detailed_topics_json` describes specific demonstrated capabilities and enriches the item-level embedding, following the portfolio design. `use_cases_json` describes what someone could showcase with the asset. Existing review flags/reasons cover truncated or unusable guide input and vocabulary-review issues. Do not invent audience or difficulty values when the text does not support them.

There is no separate evidence-citation schema, analysis-signature model, embedding fingerprint, or inventory-state table in Phase 1.

#### 2c. Common card field ownership

| Field | Source refresh | Successful analysis |
| --- | --- | --- |
| `display_name` | Final Demo Title, updated each sync | Remains source-owned |
| `summary` | Seed from the selected description | Current generated summary |
| `products_json`, `topics_json`, `audience_json` | Seed from declared metadata | Normalized analysis; preserve declared products alongside supported extracted products |
| `difficulty` | Initially null | Supported value or null |
| `status`, retirement fields | Derived from source lifecycle | Never changed by the analyzer |

An unchanged refresh must preserve generated card fields. When the content hash changes, mark the prior analysis stale and replace generated card fields with current source-derived values until analysis succeeds. Commit that invalidation with the source update, so a failed analysis does not leave an old generated summary presented as current. A forced reanalysis also marks the item stale before model calls, so a failed forced attempt is retried on a later normal sync.

### 3. Ingest Pipeline

#### 3a. Service module: `src/api/rcars/services/ie_sync.py`

Use the same style as `osspa_sync.py`: focused reader/parser helpers and one sync service. Do not build a general ingestion framework.

| Function | Responsibility |
| --- | --- |
| `fetch_ie_rows(settings)` | Read the configured sheet, validate headers/completeness, and return allowlisted source data |
| `normalize_ie_row(row)` | Normalize identity, metadata, links, guide text, and source status |
| `derive_ie_status(row)` | Apply the publication/retirement mapping |
| `compute_ie_content_hash(text, metadata)` | Hash the full accepted text plus fields used in the analysis prompt |
| `upsert_ie_item(db, row)` | Write the common card and IE extension; invalidate changed analysis without overwriting unchanged generated fields |
| `retire_missing_ie(db, seen_ids)` | Soft-retire missing IE records only, after the inventory checks pass |
| `analyze_ie_item(db, row, content_hash, settings)` | Analyze, normalize vocabulary, generate one embedding, and save the result |
| `run_ie_sync(db, settings, force=False, on_progress=None)` | Serialize and run the complete sync; return counts and warnings |

The service is synchronous, like `run_osspa_sync`; the worker calls it through `asyncio.to_thread()` to keep blocking I/O off the worker event loop.

#### 3b. Orchestrator flow

```text
0. Acquire the IE source advisory lock; exit if another sync is running.
1. Fetch the complete allowlisted inventory from Sheets.
2. Validate headers and identities; reject failed, partial, or empty input.
   Normalize rows and compute their content hashes before source writes.
3. Compare seen IDs with the existing IE inventory; apply the removal guard.
4. Reconcile source metadata and lifecycle; invalidate changed analysis.
5. For each valid Published item:
     if hash matches, analysis is current, and its summary embedding exists:
         skip, unless force was requested
     otherwise:
         mark analysis stale and expose current source-derived card values
         analyze description + accepted guide text
         normalize vocabulary
         build one enriched summary embedding
         commit analysis + card fields + embedding together
     on item failure:
         record the error, retain stale state, and continue
6. Complete the job with upserted/analyzed/unchanged/retired/failed counts.
7. Release the source lock in finally.
```

Reconcile all source publication changes before starting LLM work. A retired or unpublished item must disappear from public discovery even if another item's analysis fails. Successful per-item work persists; a later sync retries remaining incomplete/stale items after interruption.

#### 3c. Sheets reader, links, and guide text

**Sheet access.** Use Google Sheets API reads with the configured numeric tab ID. Discover columns by trimmed header name rather than fixed letters, and read future rows rather than fixing the range to the inspected 319 rows. Require `Number`, `Status`, `Final Demo Title`, `Primary Product`, `Production Link`, `Demo Description`, and `Guide Extraction JSON`; optional columns may be absent. Duplicate required headers or identities abort reconciliation.

Fetch the header and selected data columns using [`spreadsheets.getByDataFilter`](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/getByDataFilter) and an explicit field mask. Check that the returned headers still match the discovered mapping; retry if they changed. A failed or incomplete read is not an empty inventory. Do not claim a revision-locked Sheets snapshot.

Use effective/formatted cell values and hyperlink/rich-text targets from [`CellData`](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/cells). Never evaluate formulas in RCARS. Normalize comma/newline/semicolon-separated product/topic lists and preserve unknown product labels through the existing vocabulary-review behavior.

**Description.** Select the first nonempty description in the order shown in Source Data. Do not concatenate multiple versions as independent evidence.

**Links.** Read two fields from the same row: `Production Link` for the Arcade experience and `Drupal Page URL` for the Red Hat page hosting it. Store them directly as `production_url` and `drupal_page_url`. There is no fallback chain: the temporary link column, RHAC field, and URLs embedded in guide JSON do not supply or replace either value.

Read actual HTTPS URLs from cell values or hyperlink targets; trim whitespace and reject explanatory prose, embedded credentials, or unsupported schemes. Validate the Arcade source hosts (`interact.redhat.com`, `app.arcade.software`) and the Red Hat page host (`www.redhat.com`). If a field contains multiple distinct URLs, flag it for source review rather than guessing which version is intended. Use supplied URLs; do not construct them from IDs or crawl the destinations. Link reachability is not checked in this version.

**Guide text.** Parse the JSON and retain only `title`, `steps` (step number/text), `bodyText`, `extractedAt`, and `truncated`. Guide IDs and URLs are unnecessary for choosing the content links. Drop them, image URLs/alt text, and other fields before storage or model input. Decode HTML entities and render text safely. Use ordered step text as the main corpus; use `bodyText` when meaningful step text is absent, without duplicating both copies.

The inspected source had 255 guide extractions, including 241 Published records. Their `bodyText` was capped at 3,000 characters, while step arrays contained more content. Analyze the step text, not just that short body field. Four extractions explicitly reported truncation; preserve that review flag.

Malformed guide JSON is an item warning; use a valid description if available. A record with neither usable description nor guide text is not analysis-ready. Frame source text as data in the prompt, not instructions.

**Versions.** The user explained that different Arcade references can come from different versions. Use the guide text associated with the row for analysis and the row's `Production Link` for the experience. Do not compare Arcade IDs, attempt version matching, or replace the source link based on guide metadata. RCARS identity remains `ie:{Number}`.

**Language.** Normalize recognized source language names and lists; preserve unfamiliar labels. A language list does not establish separate Arcade links, so do not invent language-specific URLs.

#### 3d. LLM analysis and vocabulary

Prompt file: `src/api/rcars/prompts/interactive_experience_analyze.txt`.

Use `call_llm` and the existing structured JSON parsing/validation. Request `summary`, `products`, `topics`, `detailed_topics`, `audience`, `difficulty`, and `use_cases`. The summary answers **“What could I showcase with this asset?”** Specific feature claims must be supported by the description or guide text; an incidental keyword or generic product tag is insufficient. Do not claim to have watched the video or executed the demonstration.

Inject the existing product vocabulary with `render_vocabulary_block(vocab, 'interactive_experience')`, then run existing post-analysis normalization and unknown-term handling. Add `content_modes.interactive_experience: interactive`; the interactive verb set already exists.

Use the complete accepted text for hashing, then apply the configured prompt-size limit. If text is truncated, set the existing enrichment-review flag/reason. Do not silently claim complete coverage of omitted text.

#### 3e. Embeddings

Create **one `embed_type='summary'` embedding per experience**, following the portfolio approach. Include the title, summary, normalized products/topics, detailed demonstrated capabilities, and use cases:

```text
Interactive experience: {title}
{summary}
Products: {products}
Topics: {topics and detailed_topics}
Use cases: {use_cases}
```

Use `source='interactive_experiences'`, `content_type='interactive_experience'`, and the existing embedding service/dimension. Bound input to that service's supported size. Guide text informs the extracted details; Phase 1 does not generate individual step embeddings or introduce a chunk-retrieval system.

#### 3f. Source isolation

Scope IE lifecycle writes to `content_entities.source='interactive_experiences'`. Verify the reciprocal boundary: Babylon and OSSPA refreshes must not retire IE records. Preserve OSSPA's exclusion of IE assets to avoid duplicate ingestion.

No IE rows belong in Babylon workload/provisioning/performance tables or its retirement workflow. Interactive Experiences are separate from the Interactive Labs marketing-channel concept.

#### 3g. Change detection

Use the portfolio pattern of **one `content_hash` plus `is_stale`**. Hash the full accepted description/guide text and all metadata that feeds the prompt, using stable serialization. Exclude row position, extraction timestamps alone, URLs used only as links, and ignored columns.

| Change | Work |
| --- | --- |
| Description, guide text, or prompt metadata changes | Reanalyze that item and replace its embedding |
| Link, row order, or extraction timestamp alone changes | Refresh source data; no LLM call |
| Unchanged item with current analysis and embedding | Skip |
| Missing analysis/embedding or stale failed item | Retry |
| Prompt, vocabulary, or model policy is deliberately changed | Run the existing-style forced sync to refresh affected content |

Do not add separate source/input hashes, policy-signature tables, or embedding repair fingerprints. If a missing embedding requires retry, rerun the normal item analysis path in Phase 1.

#### 3h. Robustness and visibility

- **Complete-source validation:** failed, partial, empty, or structurally invalid reads abort before source writes. Invalid/duplicate Number fails the inventory; malformed content on an identified row can be reported without losing its seen identity.
- **Removal guard:** capture the previous IE ID set before upserts, using existing IE/entity rows that have not already been retired as `source_missing`. If more than half disappear, abort reconciliation and report the proposed change. Count Retired/Closed rows still present in the source as seen. No separate inventory-state table is needed.
- **Source serialization:** one advisory lock covers the whole sync, including analysis, so manual and nightly runs cannot overlap. Use the existing lock helper with an IE-specific key. Do not hold an ordinary SQL transaction across Google/model calls.
- **Atomic writes:** reconcile source/lifecycle changes in a short transaction. For each analyzed item, generate the result and vector before committing analysis, common card fields, and embedding replacement in one transaction. Clear `is_stale` only when that publication succeeds.
- **Failure recovery:** use existing `scan_status`/error fields and job warnings. Failed new analysis leaves the item pending/stale for retry; it must not publish a partial result. An interrupted bulk sync resumes through unchanged-item checks on the next run.
- **Public visibility:** Browse defaults to `status='prod' AND retired_at IS NULL`. Advisor additionally requires non-stale successful analysis and its embedding. Apply that eligibility in retrieval before candidate limits. Direct item access and chat follow-ups enforce the same user's visibility permissions.

Browse may show current source-derived metadata before analysis completes. Generated facts are available only when current. Non-prod records can be inspected by authorized curators; they are not automatically analyzed or recommended in Phase 1.

#### 3i. Browse and API integration

Extend the existing routes rather than adding a separate IE catalog API:

| Route (under `/api/v1`) | Change |
| --- | --- |
| `GET /catalog` | Accept `content_type=interactive_experience`; include IE joins and the common status gate |
| `GET /catalog/{identifier}` | Resolve `ie:` directly; return IE metadata, `production_url`, and optional `drupal_page_url` |
| `GET /catalog/{identifier}/analysis` | Dispatch to `ie_analysis`; expose readiness without presenting stale analysis as current |
| `POST /advisor/recommendations` | Accept the new type in request validation and serialize it at low/medium effort |
| `POST /advisor/chat` | Accept the new type; support recommendation and item facts/chat |

Update the catalog prefix resolver, `Database.get_analysis`, source joins, and response schemas. Existing recommendation responses require `stage` and ignore undeclared fields: make IE stage/CI-name fields nullable and explicitly include `content_type`, `source`, public IE metadata, and driver display data. Do not populate infrastructure fields with invented defaults. Preserve existing sources' contracts.

Browse text search should match IE title/ID, summary, products, and topics, including recognized product shorthand. Use common audience/difficulty fields where supported. The existing `stage` parameter filters universal publication status; IE has no Babylon deployment stage. Babylon namespace/workload/cloud/Platform/TDP filters and architecture-only facets retain their existing source-specific meanings.

Add **Interactive Experiences** to the existing content-format controls. Under the proposed default, fresh/default selections include IE alongside currently enabled formats. Preserve explicit URL/session filters, including exclusions. IE-only selection must work.

Use the existing expandable card layout. Show the title, subtype, description/summary, relevant products/topics, declared languages, the Arcade production link, and the Drupal page URL when present. No new page/button terminology is prescribed. Omit infrastructure and performance sections. Reuse the existing RCARS detail navigation. IE-specific curator editing is deferred; hide/reject unsupported source-specific actions rather than routing them to Showroom tables.

#### 3j. Advisor integration

Register `InteractiveExperienceDriver` in the existing driver registry, with category/type `interactive_experience`. Implement its analysis lookup, triage/rationale guidance, serialization, and display hooks. Add IE hydration in vector search and the frontend's explicit category/grouping switches, including streamed and saved cards.

A fresh query such as **“OpenShift Vert”** is a valid discovery request. The vocabulary already includes Red Hat OpenShift Virtualization, and Advisor already expands product aliases/search terms. Add reviewed search terms for `OpenShift Vert` and `OpenShift Virt`; use the same product lookup for IE Browse matching. Do not expand the ambiguous word `Vert` alone or feed an embedding-expansion string directly into SQL substring matching.

The result should explain what the experience demonstrates and why it fits the requested product/capability. A bare product query can return multiple formats; an explicit showcase/walkthrough request should make relevant IE assets easy to identify. Preserve intent established by prior conversation context.

Extend chat item resolution, analysis lookup, and item-facts/item-chat handlers to IE. They may use the stored current summary, extracted capabilities, and accepted guide text, bounded to the model input budget. This does not require a separate step-search index. Unsupported infrastructure/performance/overlap questions return a scoped explanation rather than querying an unrelated Babylon item. Do not recommend an IE as though it supplies a provisioned lab.

### 4. Worker Integration

**Queue:** `arq:queue:scan`.
**Job type:** `ie_sync`.

| Entry point | Behavior |
| --- | --- |
| Nightly maintenance | Optional `run_ie_pipeline` alongside Babylon and OSSPA |
| `POST /api/v1/admin/sync-interactive-experiences` | Admin-only; enqueue `run_ie_sync_job`; return `202 {job_id}` |
| `rcars ie sync [--force]` | Call the same sync service, following the OSSPA CLI pattern |

The admin request accepts `{"force": false}` by default. Force bypasses the unchanged-analysis skip, not source validation or publication rules. Use existing effective-role dependencies, including API-key role ceilings. An enqueue failure must mark any created job failed and return an error.

Wrap `run_ie_sync` in `asyncio.to_thread()` and bridge progress through the existing job/SSE mechanism, as `run_osspa_sync_job` does. Register its timeout and queue mapping. On cancellation, signal the service to stop between items; keep the sync lock held until the thread's work ends. Cancelling the await must not release the lock while the underlying sync is still running.

```text
run_nightly_pipeline
├── run_babylon_pipeline
├── run_osspa_pipeline
├── run_ie_pipeline
│   ├── fetch and validate sheet
│   ├── reconcile metadata and lifecycle
│   └── analyze changed published items
└── existing retirement sweep (IE excluded)
```

Keep source failures isolated in the nightly result. Report fetched/upserted/analyzed/unchanged/retired/failed counts and bounded warnings through existing jobs and Sync/Status views. A completed IE sync has finished its analysis loop; item failures remain visible. A timeout is an interrupted job, not a successful full sync.

Use bounded network/model calls and an explicit worker timeout suitable for a bulk scan. The initial import may need more than one run; committed successes are skipped on retry. Do not add child-job orchestration to solve that in this version.

### 5. Configuration

Use existing `Settings`, the `RCARS_` environment prefix, and Ansible patterns. The defaults below are proposals for implementation review.

| Setting | Default / meaning |
| --- | --- |
| `ie_sync_enabled` | `false`; enable when source access is configured |
| `ie_spreadsheet_id` | Explicit configured spreadsheet ID from Source Data |
| `ie_sheet_id` | Explicit numeric tab ID from Source Data |
| `ie_fetch_timeout_s` | `30`; bounded Sheets request timeout |
| `ie_max_text_bytes` | `200000`; maximum text sent to analysis after hashing the complete input |
| `ie_analysis_model` | Empty inherits `settings.model`, following the portfolio model-setting pattern |

Use an IE-specific advisory-lock key and the 50% removal guard described in 3h. Keep retry limits and worker timeout bounded; they need not become a new configuration framework.

Use `google-auth`/Application Default Credentials with the Sheets read-only scope. A dedicated service account needs Viewer access to this spreadsheet and Sheets API access; see Google's [credential guidance](https://developers.google.com/workspace/guides/create-credentials). Mount credentials through the existing deployment Secret pattern on the scan worker. The API only enqueues; the frontend and recommend worker need no Google credentials. A CLI sync needs authorized local credentials.

Add the dependency/configuration and secret mount through the active `src/api/pyproject.toml`, `config.py`, and Ansible templates/example vars. The `gws` tool used during design is not a production dependency. Do not make the sheet public or write back to it.

### 6. Lifecycle

| Event | Result |
| --- | --- |
| New valid Published record | Source/common rows created; analyze and embed |
| New non-prod record | Retain source metadata; no automatic analysis |
| Published record becomes non-prod | Withdraw from public discovery on source reconciliation |
| Retired or Closed status | Soft-retire with the corresponding source reason |
| Row removed from a complete valid inventory | Retire as missing when the removal guard passes |
| Previously retired item is validly republished | Restore the same ID; reuse current analysis or rerun if stale/missing |
| Accepted content changes | Invalidate old generated fields, then reanalyze that item |
| Only links/row order change | Update source fields without model work |
| Configured spreadsheet/tab changes | Deliberate source migration required; not a normal refresh operation |

### 7. Failure and Edge Cases

| Case | Behavior |
| --- | --- |
| Read/auth failure, missing tab, partial response, bad required headers | Fail before reconciliation; retain existing data |
| Empty inventory or more than 50% of prior IDs disappear | Abort source writes and report the change for investigation |
| Missing/duplicate Number | Abort inventory; no last-row-wins identity policy |
| Bad content on a validly identified row | Retain seen identity and report the problem; no public eligibility without usable title/production link/text |
| Multiple distinct URLs or prose in a link field | Flag the field for review; do not guess a version or substitute a different source field |
| Different version references in guide metadata | Use the row's guide text and production link; no ID comparison or version matching |
| Malformed guide | Fall back to a valid description; mark for review |
| Truncated guide or prompt input | Preserve a review reason; avoid claims of complete content coverage |
| Item LLM/embedding failure | Keep analysis stale, record the error, continue; retry next sync |
| Failure during final database write | Roll back that item's analysis/card/embedding publication together |
| Concurrent manual/nightly sync | Second run reports that a sync is already running |
| Worker interruption | Existing job status exposes interruption; next sync skips completed work and retries incomplete items |

### 8. Testing

Use synthetic source fixtures and mocked Google/LLM/embedding calls. Use the existing isolated PostgreSQL/pgvector setup for database tests. Do not commit a real sheet export or credentials.

| Test | Type | Assertion |
| --- | --- | --- |
| Header changes, sparse rows, future rows, renamed tab | Unit | Column names and numeric tab ID resolve the intended source |
| Production and Drupal URL mapping | Unit | Each value comes from its named source field; no temporary/RHAC/guide URL fallback; ambiguous values are reported |
| Effective values, hyperlinks, rich text | Unit | Correct source data without evaluating formulas or fetching links |
| Permanent Number and duplicate-ID rejection | Unit + integration | Stable `ie:{Number}`; malformed inventory causes no writes |
| Source-field whitelist and guide parsing | Unit | Only approved text is stored/used; malformed guides fall back to descriptions; guide IDs/URLs do not affect content links or identity |
| IE subtype mapping | Unit | All source subtypes remain `interactive_experience` |
| Publication/retirement/reactivation | Integration | Public visibility follows source state; identity is preserved |
| Empty/partial source and removal guard | Integration | Existing inventory cannot be retired by a bad read |
| Source isolation | Integration | IE, Babylon, and OSSPA cannot retire one another |
| Unchanged sync | Integration | No model calls; generated card fields survive |
| Changed text/metadata and failed-item retry | Integration | Only affected items reanalyze; stale state is retried even with unchanged source |
| One summary embedding per item | Integration | Enriched summary is searchable; no step embeddings are created |
| Atomic analysis publication | Integration | Failure cannot leave mixed card/analysis/vector results |
| API serialization and authorization | API integration | IE fields survive; nonpublic direct access/follow-ups remain role-gated |
| Product shorthand discovery | Unit + integration | OpenShift Vert/Virt and canonical product queries can find the relevant experience |
| Browse/Advisor formats and card grouping | Frontend + integration | Proposed defaults, explicit selections, deep links, and streamed/history cards work |
| Relevant showcase recommendations | Controlled evaluation | Summary/capabilities and ranking support the product query without inventing demonstrated features |
| Interrupted/concurrent sync and nightly isolation | Integration | No overlapping IE writes; retries skip successes; other sources can still report outcomes |

The implementation touches the source service/prompt, database source/analysis dispatch, worker/CLI wiring, catalog and recommendation request/response schemas, the IE driver and chat handlers, vocabulary search terms, existing Browse/Advisor cards, and Sync/Status reporting. These are extensions of existing RCARS paths rather than a new ingestion framework.

### 9. Out of Scope (Phase 1)

- **Duration** — exclude the sheet/guide values from ingestion, storage, analysis, ranking, and display until their meaning is understood. Add no IE duration fields; legacy shared response fields remain null only if compatibility requires it.
- Video transcription, screenshot analysis, linked-page crawling, or upstream guide-extractor development.
- Usage/completion metrics, attribution, performance scores, and Interactive Labs channel reporting.
- Spreadsheet writes, content creation/publication, or internal request workflow/contact data.
- Provisioning, infrastructure mappings, overlap detection, and automated retirement recommendations.
- Multiple source inventories, generic ingestion frameworks, per-item child jobs, step-vector indexing, and custom provenance/signature systems.
- IE-specific curator editing and broader Browse/Advisor redesigns.

## Relationship to Other Specs

- **[Generalized Content Model](2026-07-20-generalized-content-model-design.md):** implements the reserved IE content type, `ie:` identity prefix, and source/analysis tables. The source is this spreadsheet, replacing the earlier tentative Portfolio Architecture/markdown assumption.
- **[Portfolio Architecture Ingest](2026-08-06-portfolio-architecture-ingest-design.md):** follows its two-table, content-hash, single-summary-embedding, single-sync-service pattern. OSSPA continues excluding IE records.
- **[Controlled Vocabulary](2026-08-10-controlled-vocabulary-design.md):** reuse product normalization, unknown-term review, and product-query expansion.
- **[Advisor Content-Type Drivers](2026-09-25-advisor-v2-content-type-drivers-design.md):** reuse the driver interface; update the actual code's remaining explicit type/category switches.
- **[Platform/TDP filters](2026-10-28-platform-tdp-filters-design.md):** remain Babylon-specific. Do not equate the spreadsheet's TDP field with those labels.

The inspected code baseline was `main` at `b9cd86f`. This design uses the active backend under `src/api` and the existing React frontend, scan worker, PostgreSQL/pgvector, and Redis deployments.

## Next Steps

1. Review the two-table schema, source lifecycle behavior, and proposed discovery default.
2. Arrange read-only deployment credentials for the configured spreadsheet/tab.
3. Write an implementation plan under `docs/superpowers/plans/`, ordered by schema, source service/analysis, worker/API, then Browse/Advisor integration.
4. Pilot on dev with guide-backed and description-only items. Verify a product-shorthand search, an unchanged repeat sync, retirement/reactivation, and recovery from a failed item.
5. Deploy through the normal reviewed PR/Ansible process with additive `init-db`, then enable scheduled sync. Disabling sync stops refreshes; it does not withdraw already published records.

Do not hardcode an expected published-item count: source status, valid links, and usable text determine eligibility. The permanent Number identity, row-associated guide authority, subtype distinction, and Browse/Advisor delivery are confirmed; implementation details remain proposals for review.
