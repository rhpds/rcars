# Interactive Experiences Ingest — Design Spec

**Jira:** [RHDPCD-2042](https://redhat.atlassian.net/browse/RHDPCD-2042)
**Date:** 2026-09-28
**Status:** Draft — direct Databricks SQL pull defined; OAuth M2M access request pending; live source-contract check is the first delivery gate
**Author:** M. Rudisill
**Depends on:** Generalized Content Model (deployed); Portfolio Architecture ingest (deployed)

## Problem

RCARS currently indexes Babylon labs and Portfolio Architectures, but it cannot recommend Red Hat Interactive Experiences: guided, click-through experiences delivered through Arcade, video, or a hosted web experience. These are not provisioned environments, but they can be the right answer for a user who needs a quick product walkthrough or conceptual demonstration rather than a hands-on lab.

For this integration, **RCARS uses `dev.arcade_demo.request_master` in Databricks as its sole source of truth**. It reads that request-level view through a SQL warehouse. No other source or flow-level Arcade view is in the Phase 1 RCARS ingest path.

The companion [Architecture + Arcade analytics SQL repository](https://gitlab.cee.redhat.com/yunjyang/architecture-arcade-analytics-sql) defines `dev.arcade_demo.request_master` as the request-level compatibility view. Its current fields are sufficient for the Phase 1 catalog: identity, title, lifecycle status, direct production URL, RHCA/Interact landing-page URL, product, content type, description, language, and lifecycle timestamps.

This design makes the ownership boundary explicit:

- **Databricks owns the authoritative Interactive Experience dataset.**
- **`dev.arcade_demo.request_master` is the RCARS-facing source.** RCARS reads a fixed, explicit set of its columns and validates their shape on every sync.
- **RCARS owns its local entity, analysis, embedding, and synchronization state.** It never writes to Databricks source objects.

## Goals

1. Ingest eligible interactive experiences as first-class RCARS content entities and make them searchable beside labs and architectures.
2. Preserve a deterministic, stable identity even when a title, URL, or source row changes.
3. Read a fixed, documented set of columns from `dev.arcade_demo.request_master` through a read-only SQL warehouse connection.
4. Analyze only the source metadata and `demo_description` supplied by `request_master`; do not scrape, download, transcribe, or use guide-extraction data during Phase 1.
5. Make changes idempotent, observable, safe to retry, and safe against a partial/empty source read.

## Non-goals

- Building or hosting the interactive experience itself.
- Browser automation, Arcade scraping, video download, OCR, screenshot analysis, or automatic speech-to-text.
- Joining `v_arcade_dim_latest` or any raw upstream table in the Phase 1 ingest.
- Usage/performance ingestion. Web metrics can later use the existing `performance_channels` table with `channel='web'`.
- Changing the existing Babylon or Portfolio Architecture lifecycle rules.

## Approach

```text
Databricks authoritative data
  dev.arcade_demo.request_master
                         │  (RCARS's only external read)
                         ▼
  RCARS sync → local analysis + embeddings → Browse / Advisor
```

Yes—this will be one Databricks SQL API call, not an export, replica, scrape, or new integration service. Once the access request is approved, RCARS will authenticate as a service principal and submit a fixed `SELECT` to a SQL warehouse using Databricks' Statement Execution API. The official Python SDK makes that HTTPS API call and handles OAuth token acquisition; RCARS does not construct OAuth requests or raw HTTP calls itself.

The first implementation task is to grant RCARS read-only access to `dev.arcade_demo.request_master` through one SQL warehouse. RCARS uses the fixed select list below, rather than `SELECT *`, and validates the returned column manifest before accepting rows. This keeps the integration stable without creating another data layer.

## Databricks Access Request

RCARS is applying for OAuth machine-to-machine (M2M) access; it does not yet have a Databricks service principal, client ID, client secret, warehouse grant, or network rule. Access is required only for this Phase 1 read-only catalog integration.

| Request field | Proposed value / status |
| --- | --- |
| Service-principal owner | Molly Rudisill (`mrudisil@redhat.com`) |
| Authentication | OAuth M2M client credentials through the official Databricks SDK; no personal access token in a deployed RCARS environment |
| Principals | Separate non-production and production principals, client IDs, and secrets; credentials are not shared across environments |
| Source | `dev.arcade_demo.request_master` only, queried through one approved SQL warehouse |
| Minimum permissions | `CAN USE` on that warehouse; `USE CATALOG` on `dev`; `USE SCHEMA` on `arcade_demo`; and `SELECT` on `request_master` only. No write or warehouse-management permission. |
| Data boundary | The fixed query returns only the fields documented in [Source Data](#source-data): catalog metadata, lifecycle values, launch URLs, and `demo_description`. It excludes requestor/creator emails, Slack data, raw intake data, guide-extraction content, credentials, and tokens. RCARS stores normalized catalog metadata and derived analysis internally; it does not write to Databricks. The full `demo_description` is analyzed and discarded, and its use by the configured LLM provider requires source-owner approval before enablement. |
| Network rule | **Pending RCARS platform confirmation.** Databricks is in AWS `us-west-2`; the RCARS OpenShift cluster region and the fixed EgressIP/NAT IP or CIDR for `rcars-dev` and `rcars-prod` must be supplied by the MP+/OpenShift platform owner. |
| CMDB application code | **Unassigned.** RCARS work is tracked in Jira under `RHDPCD`; `RHDPCD-2042` is the engineering issue for this work, not a CMDB application code. Confirm whether CMDB registration is required before access is provisioned. |

The service-principal secret will be injected from the organization-approved secret manager into the appropriate RCARS OpenShift namespace. It must never be committed, included in application logs, or exposed in prompts. Rotation follows the Databricks/platform policy and is an operating responsibility of the service-principal owner.

## Source Data

### `request_master` — RCARS's only source

- `request_number` is the analytics repository's canonical request identity and becomes the stable RCARS key. `Global ID` is not required because it can be absent.
- It provides the request-level grain RCARS needs: one catalog item per publishable Interactive Experience rather than one per Arcade flow.
- It contains the Phase 1 analysis input, `demo_description`. `Guide_Extraction_JSON` is not selected by this view, so guide bodies and ordered steps are explicitly excluded from this phase.
- It has no completed-refresh batch identifier. RCARS therefore never retires an item merely because it is absent from one read; retirement is driven by an explicit retired lifecycle value or curator confirmation after review.

`content_type` is optional Databricks request metadata, not RCARS's top-level `content_entities.content_type` and not an ingest gate. Every valid `request_master` row is represented in RCARS as `content_type='interactive_experience'`; the supplied value, when present, is preserved separately as `source_content_type`.

### Source discovery (one-time, read-only)

Run these in the Databricks SQL editor or with a read-only developer identity before configuring RCARS. They establish the deployed shape and row counts; they are not the production sync query.

```sql
-- 1. Confirm the compatibility-view schema actually deployed in dev.
DESCRIBE TABLE dev.arcade_demo.request_master;

-- 2. Inspect the request-level catalog without selecting PII fields.
SELECT
    request_number,
    final_demo_title,
    status,
    content_type,
    production_link,
    rhca_page,
    product,
    demo_description,
    language,
    status_published_timestamp,
    status_retired_timestamp
FROM dev.arcade_demo.request_master
ORDER BY request_number;

-- 3. Count supplied/missing request types and lifecycle states before first sync.
SELECT
    COALESCE(NULLIF(TRIM(content_type), ''), '<missing>') AS source_content_type,
    status,
    COUNT(*) AS request_count
FROM dev.arcade_demo.request_master
GROUP BY COALESCE(NULLIF(TRIM(content_type), ''), '<missing>'), status
ORDER BY source_content_type, status;
```

These queries are the complete Phase 1 data-discovery scope. RCARS does not inspect raw pipeline tables or `Guide_Extraction_JSON`.

### Production pull: exact API request

Every sync executes this immutable statement. It intentionally includes retired and unpublished requests so RCARS can record their lifecycle; eligibility is derived locally after validation. There are no user-supplied values and no configurable object name in the query.

```sql
SELECT
    request_number,
    final_demo_title,
    status,
    content_type,
    production_link,
    rhca_page,
    product,
    demo_description,
    language,
    status_published_timestamp,
    status_retired_timestamp
FROM dev.arcade_demo.request_master
ORDER BY request_number
```

Conceptually, the SDK submits the following request to `POST /api/2.0/sql/statements`; it is shown to make the network boundary explicit, not as an instruction to hand-roll an HTTP client:

```json
{
  "warehouse_id": "${RCARS_IE_DATABRICKS_WAREHOUSE_ID}",
  "catalog": "dev",
  "schema": "arcade_demo",
  "statement": "<the fixed SELECT above>",
  "format": "JSON_ARRAY",
  "disposition": "INLINE",
  "wait_timeout": "30s",
  "on_wait_timeout": "CONTINUE"
}
```

The worker polls the returned statement ID only when the initial wait expires, fails if the statement reaches `FAILED`, `CANCELED`, or `CLOSED`, and fetches every inline result chunk by index. It rejects a truncated response and cancels a statement that exceeds RCARS's end-to-end timeout. `INLINE`/`JSON_ARRAY` is appropriate for the expected small catalog response; its 25 MiB API limit is a fail-closed guard, not a reason to quietly ingest a partial catalog. If the validated catalog outgrows that limit, a separately reviewed switch to `EXTERNAL_LINKS` is required because those responses contain short-lived credential-bearing URLs.

### Required source columns and ownership

The RCARS source contract is the following fixed, explicit projection from `dev.arcade_demo.request_master`. It uses only fields that are present in the current compatibility view and excludes requestor/creator emails, Slack identifiers, raw intake text, viewer data, credentials, and tokens.

| RCARS field | `request_master` column / derivation | Required source shape | RCARS use |
| --- | --- | --- | --- |
| `interactive_id` | Canonical string form of `request_number` | Non-empty `STRING` | Stable identity; becomes `content_id = ie:{interactive_id}`. |
| `title` | `final_demo_title` | Non-empty `STRING` | Display name. |
| `source_status` | `status` | Non-empty `STRING` | Drives `prod`, `dev`, and retirement. |
| `source_published_at`, `source_retired_at` | `status_published_timestamp`, `status_retired_timestamp` | `TIMESTAMP` or `NULL` | Lifecycle audit data. |
| `source_content_type` | `content_type` | `STRING` or `NULL` | Optional Databricks request metadata; it never controls inclusion. |
| `experience_format` | `content_type`: `Interactive Video Demo` → `video`; all other values, including `NULL`, → `arcade` | Derived after normalizing absent/blank type to `NULL` | UI/recommendation delivery format. The original type remains available when supplied. |
| `experience_url` | `production_link` | Non-empty HTTPS `STRING`; configured allowlisted host | Validated direct experience URL; required for every accepted row. |
| `interact_page_url` | `rhca_page` | HTTPS `STRING` or `NULL`; configured `interact.redhat.com` allowlisted host when populated | Canonical Interact landing page. It is preferred for the RCARS launch CTA. |
| `product` | `product` | `STRING` or `NULL` | Source taxonomy hint. |
| `summary_seed` | `demo_description` | `STRING` or `NULL`; byte-bounded before analysis | The only Phase 1 free-text analysis input. |
| `language` | `language` | `STRING` or `NULL` | Card metadata and analysis hint. |
| `source_payload_hash` | SHA-256 computed by RCARS from the normalized fields above | Not source-supplied | Deterministic change detection. |
| `source_observed_at` | RCARS sync timestamp | Not source-supplied | Audit timestamp only; it does not assert a Databricks-wide completed refresh. |

RCARS obtains the entire request-level source with one explicit query containing only that column list. It does not use `SELECT *` or filter on `content_type`: many legitimate demos do not supply one, and RCARS must not omit them for that reason. A missing or renamed required column fails the sync before database writes.

Before validation and hashing, RCARS trims outer whitespace from identifiers and taxonomy/status fields; normalizes a blank `content_type` to `NULL`; converts timestamps to UTC; lowercases only the URL host for allowlist comparison; and preserves the original title, product, language, and description text for display or analysis. It serializes the normalized source fields in a fixed key order before calculating `source_payload_hash`, so a retry yields the same hash for the same source row. No case-folding or title rewriting is allowed because that would make a presentation change invisible to change detection.

### Source-type-to-format mapping

| Databricks `content_type` | `experience_format` | RCARS treatment |
| --- | --- | --- |
| `Interactive Video Demo` | `video` | Ingest as an Interactive Experience and render a video format. |
| `Interactive Demo`, `Technical Walkthrough`, `Business Intro` | `arcade` | Ingest as an Interactive Experience and render an Arcade format. |
| `NULL`, blank, or any other value | `arcade` | Ingest as an Interactive Experience. Preserve the supplied value when present; do not make it a visibility or eligibility decision. |

`demo_description` is untrusted source data, not executable instruction. It is bounded by a configurable byte limit, logged only by length/checksum, framed as untrusted material in the LLM prompt, and never used to influence program control flow. Phase 1 does not use guide bodies, ordered Arcade steps, screenshots, browser scraping, video download, or automatic transcription.

### Ownership and curation

Phase 1 reads **only** `dev.arcade_demo.request_master`. RCARS curator notes and review flags stay in its database and never alter Databricks-owned source fields.

If a separate curation workflow is needed later, it must use a dedicated RCARS-owned UI or data store keyed by `interactive_id`. It may suppress an otherwise eligible item but must never create items, replace source URLs/statuses, or bypass `request_master`. That workflow is out of scope for the initial connection.

### Snapshot and row validation

The Statement Execution response is one source snapshot. RCARS makes **no local write** until every result chunk has been retrieved and the snapshot passes these checks:

1. The result manifest contains exactly the required named columns, in the expected order, with compatible identifier/string/timestamp types.
2. Every selected row has a unique, non-empty `request_number`, a non-empty `final_demo_title`, an optional text `content_type`, and parseable lifecycle timestamps when populated.
3. Every `production_link` is a non-empty HTTPS URL whose host is in the configured allowlist. This is required for every accepted row, not only published rows, because `interactive_experiences.experience_url` is a required field and RCARS must not persist an unsafe launch target. When populated, `rhca_page` must also be an allowlisted HTTPS Interact-page URL.
4. Every selected row normalizes deterministically, including a canonical string ID and a SHA-256 source-payload hash. A duplicate ID, missing required value, invalid URL, incompatible schema, incomplete/truncated result, or any malformed row fails the entire snapshot without changing RCARS.

`demo_description` is the only optional source field for acceptance. It is bounded before analysis; a missing or over-limit description does not discard an otherwise valid request, but it prevents `prod` visibility and analysis as described below. RCARS logs only source counts, field names, lengths, hashes, and validation reasons—not descriptions, URLs, OAuth material, or result payloads.

## Ingestion Scope, Identity, and Visibility

Every accepted record is represented as:

| Field | Value |
| --- | --- |
| `content_id` | `ie:{request_number}` |
| `source` | `interactive_experience` |
| `content_type` | `interactive_experience` |
| `is_hands_on` | `FALSE` |

RCARS ingests every structurally valid row returned by the fixed query, regardless of whether it is currently published. “Ingested” means it has a local entity and extension row; it does **not** mean that it is recommended or visible by default. This mirrors the Portfolio Architecture pattern: preserve a curator-visible inventory while the shared `status='prod'` predicate protects Browse and Advisor.

| Source state after snapshot validation | RCARS action | Default visibility / analysis |
| --- | --- | --- |
| `status='Published'`, no `status_retired_timestamp`, and valid bounded `demo_description` | Upsert as `prod`; analyze and embed when the effective hash changes. | Visible in Browse and Advisor. |
| Any non-retired status other than `Published`, with a valid bounded description | Upsert as `dev` with `not_published` or `unrecognized_source_status` review reason; analyze and embed when the effective hash changes. | Curator-visible only; excluded by the shared `prod` predicate. |
| Structurally valid non-retired row with a missing or over-limit `demo_description` | Upsert as `dev` with `missing_demo_description` or `description_too_large`; do not analyze or embed. | Curator-visible only. |
| `status='Retired'` or a populated `status_retired_timestamp` | Upsert source lifecycle metadata, then soft-retire the matching Interactive Experience. | Never default-visible or recommended. |
| Any malformed row or snapshot | Abort before all RCARS writes. | Existing RCARS inventory remains unchanged. |

`prod` remains the universal default visibility predicate in Browse and Advisor. No RCARS-local field can force `prod` if `request_master` reports an item unpublished, retired, incomplete, or invalid. `Closed` has no implicit mapping: it remains `dev` until the Databricks owner explicitly defines its lifecycle meaning.

## Schema

The existing `content_entities`, `embeddings`, controlled-vocabulary, job, status, and retirement mechanisms are reused. Interactive Experience-specific fields live in new 1:1 extension and analysis tables.

```sql
CREATE TABLE IF NOT EXISTS interactive_experiences (
    content_id              TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    interactive_id          TEXT NOT NULL UNIQUE, -- canonical request_number string
    experience_url          TEXT NOT NULL,
    interact_page_url       TEXT,
    source_content_type     TEXT, -- nullable: source metadata, never an inclusion gate
    experience_format       TEXT NOT NULL CHECK (experience_format IN ('arcade', 'video')),
    product                 TEXT,
    language                TEXT,
    source_status           TEXT NOT NULL,
    source_published_at     TIMESTAMPTZ,
    source_retired_at       TIMESTAMPTZ,
    source_payload_hash     TEXT NOT NULL,
    source_observed_at      TIMESTAMPTZ NOT NULL,
    has_demo_description    BOOLEAN NOT NULL DEFAULT FALSE,
    last_databricks_sync    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ie_interactive_id ON interactive_experiences(interactive_id);
CREATE INDEX IF NOT EXISTS idx_ie_format ON interactive_experiences(experience_format);

CREATE TABLE IF NOT EXISTS interactive_experience_analysis (
    content_id                  TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,

    -- Shared analysis contract
    summary                     TEXT,
    products_json               JSONB,
    topics_json                 JSONB,
    audience_json               JSONB,
    difficulty                  TEXT,
    content_hash                TEXT,
    last_analyzed               TIMESTAMPTZ,
    is_stale                    BOOLEAN DEFAULT FALSE,
    stale_commit                TEXT,

    -- Interactive-specific analysis
    learning_outcomes_json      JSONB,
    use_cases_json              JSONB,
    detailed_topics_json        JSONB,
    recommender_audience_json   JSONB,

    -- Curator controls
    enrichment_review_needed    BOOLEAN DEFAULT FALSE,
    review_reasons              JSONB,
    notes                       TEXT
);
```

The existing RCARS jobs table remains the operational run record. The advisory lock prevents concurrent snapshots; every successful scheduled or operator-initiated run is independently safe to repeat because upserts are keyed by `interactive_id` and content hashes.

The full `demo_description` is fetched for the run, bounded, hashed, analyzed, and discarded rather than persisted in RCARS. Phase 1 creates no step or transcript records because `request_master` does not expose guide text.

## Synchronization Design

### Pipeline

```text
acquire advisory lock
  → connect to the dedicated SQL warehouse with OAuth M2M
  → submit the fixed request_master SELECT through Statement Execution
  → wait/poll, fetch all result chunks, and validate expected columns, IDs, URLs, formats, row count, and duplicates
  → derive status from normalized source lifecycle
  → apply shrink/empty-inventory guard
  → upsert entities + extension rows in a transaction
  → retire only records explicitly marked retired by source lifecycle
  → re-analyze records whose effective content hash changed
  → atomically replace embeddings after successful analysis
  → publish RCARS job summary
release lock
```

All external reads will have explicit connection, query, and response timeouts. Once access is provisioned, RCARS will query Databricks only through `dev.arcade_demo.request_master`, using a dedicated read-only service principal and SQL warehouse. Its OAuth client secret will live in the deployment secret store, never in a checked-in config, a job log, or an analysis prompt.

No database write occurs before the connection succeeds and the complete query result passes structural validation: the response manifest has the expected named columns with compatible types; every `request_number` is unique and non-empty; every selected row has a valid source hash, valid format mapping, allowlisted HTTPS direct URL, valid optional Interact-page URL, and an accepted inventory count. A query failure, unexpected schema, truncated response, duplicate request number, malformed row, empty result, or guarded shrink fails the job without changing RCARS.

### Sync cadence

Phase 1 uses RCARS's existing nightly pipeline and an administrator-initiated sync. Each run reads the latest committed contents of `request_master`; it does not start, modify, or inspect a Databricks workflow. This is enough for a catalog feed and avoids coupling the first delivery to a second Databricks API or a callback endpoint.

```text
RCARS nightly pipeline or admin command
  → execute fixed request_master SELECT
  → validate whole snapshot
  → upsert RCARS catalog records
```

If low-latency propagation becomes necessary, a future Databricks success callback may enqueue this same sync job. It must carry no source rows, and it does not change the query, grants, validation, or retention behavior described here. It is deliberately not a Phase 1 prerequisite.

### Connection and authorization

RCARS will use the official Databricks SDK for Python with OAuth machine-to-machine authentication once the access request is approved. It creates a `WorkspaceClient`, calls `statement_execution.execute_statement(...)` with the fixed query and configured warehouse ID, polls with `get_statement(...)` only when needed, fetches any remaining chunks, and cancels an overlong statement. This is the supported REST API path for running SQL on a warehouse. A personal access token is acceptable only for an individual developer's local smoke test, never for deployed RCARS. [OAuth M2M guidance](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m) and the [Statement Execution API guide](https://docs.databricks.com/aws/en/dev-tools/sql-execution-tutorial) describe the underlying authentication and SQL request.

RCARS is applying for a dedicated M2M service principal in each environment, with:

- a scoped OAuth secret limited to the SQL capability required by this integration;
- `CAN USE` on one approved SQL warehouse, not warehouse-management permission;
- `USE CATALOG` on `dev`, `USE SCHEMA` on `arcade_demo`, and `SELECT` on `request_master` only; and
- no write-capable Databricks permission.

The grant is for the RCARS-facing view, not its underlying raw sources. The connection check must verify this works with the workspace's deployed view-security model before production is enabled. The final service-principal IDs, warehouse IDs, network rule, and secret rotation owner are documented before RCARS is configured.

### Connection-readiness gate

The first RCARS delivery is a **read-only source check**, not an ingest. It is exposed as `rcars interactive-experiences check-source` and uses exactly the same settings and OAuth M2M path that the worker will use. It performs no RCARS database write or external write.

The check must:

1. acquire an OAuth M2M connection to the configured SQL warehouse;
2. issue a small `SELECT` against `dev.arcade_demo.request_master` and verify the required column names/types;
3. verify that eligible rows have unique request numbers and that optional `content_type` values normalize safely;
4. report only connection identity, observed-at timestamp, eligible/rejected counts, and validation errors—never descriptions or credentials; and
5. return non-zero on missing grant, expired/invalid client secret, unexpected schema, duplicate request number, or zero rows (unless an operator explicitly requests an empty-source diagnostic).

`sync` is enabled only after this check succeeds against the intended non-production warehouse and the same check is recorded for production. A successful OAuth token alone is not enough: the required `request_master` schema and lifecycle values must validate too.

### Hashing and incremental analysis

RCARS computes a `source_payload_hash` from the normalized `request_master` fields it persists: request number, title, status, lifecycle timestamps, content type, direct production URL, RHCA/Interact-page URL, product, description, and language. It computes a separate effective analysis hash from title, content type, product, description, language, and the current analysis-prompt version. This makes the direct-source normalization explicit and reproducible.

Changing source lifecycle metadata, an RCARS-private curator note, synchronization timestamp, direct launch URL, or Interact-page URL updates the extension row without re-running analysis. A changed title, content type, product, description, language, or analysis-prompt version re-runs analysis and embeddings.

For changed eligible records, RCARS first marks the analysis stale, performs LLM analysis and vocabulary normalization, updates the common card fields, generates embeddings, and swaps the item's embedding rows atomically. It clears `is_stale` only after all of those writes succeed. A failed run leaves the last good production analysis and embeddings intact while the item remains marked stale for retry.

Phase 1 creates one summary embedding per experience. The summary begins with the fixed prefix `"Interactive experience: "`. This prefix is an embedding contract: changing it requires a full re-embed. Step embeddings are out of scope because the selected source does not contain guide steps.

## Lifecycle and Recovery

The current source has no completed-refresh batch watermark, so absence from a single `request_master` query is **not** a retirement signal. The pipeline never retires a record solely because it was missing from a run. It soft-retires only `source='interactive_experience'` rows whose lifecycle explicitly becomes `Retired` or supplies `status_retired_timestamp`.

| Source event | RCARS result |
| --- | --- |
| New, structurally valid request | Upsert a new `ie:{request_number}` entity and extension row; derive `prod` or `dev` from the source state. |
| `status` changes from a non-published value to `Published`, with no retirement timestamp | Clear any source-specific retirement fields, derive `prod` if the description is valid, and analyze/embed if the effective hash changed. |
| `status` changes away from `Published` without a retirement timestamp | Keep the item ingested, derive `dev`, and remove it from default Browse/Advisor through the shared status predicate. |
| `status='Retired'` or `status_retired_timestamp` is populated | Update lifecycle metadata and soft-retire only the matching `source='interactive_experience'` item. |
| A previously retired request reappears as non-retired | Clear the RCARS retirement fields during upsert, re-derive `prod`/`dev`, and treat it as an active item again. |
| `demo_description`, title, product, language, or optional source type changes | Update the extension row; a changed effective analysis hash marks analysis stale and triggers re-analysis/embedding. |
| Direct launch URL, Interact-page URL, or lifecycle timestamp changes only | Update the extension row and source hash; do not re-run analysis or embeddings. |
| Request disappears from the full query or its request number changes | Do not retire automatically. Record the formerly active ID as missing for curator review, because the source provides no completed-snapshot watermark. |
| `status='Closed'` | Keep the item `dev` until the Databricks owner supplies an explicit lifecycle mapping. |

Before any write, require a configurable shrink guard: if the accepted source inventory falls below 50% of the currently non-retired interactive inventory, stop. An empty source inventory also stops the run. Preserve the observed-at timestamp, counts, missing IDs, skipped-row reasons, and run outcome in job progress/logs so a bad upstream result is diagnosable.

## Failure and Edge Cases

| Case | Behavior |
| --- | --- |
| OAuth secret is missing, expired, or rejected; warehouse is unavailable; or the SQL statement reaches `FAILED`, `CANCELED`, or `CLOSED` | Abort before RCARS writes; retain the prior catalog and report a source-connection failure. |
| Statement exceeds the end-to-end timeout | Cancel it, poll to a terminal state, and fail the run without RCARS writes. |
| Result manifest has a missing/renamed column, an incompatible type, a changed column order, or the result is truncated | Fail the snapshot before RCARS writes; require a source-contract review. |
| Result chunks cannot all be fetched, or the returned row count does not match the manifest | Treat the snapshot as incomplete; fail without RCARS writes. |
| Empty accepted inventory or accepted inventory below the shrink guard | Abort without upserts or retirements; report the count and guard threshold. |
| Duplicate request number, blank title/status/URL, invalid URL, malformed timestamp, or non-text `content_type` in a returned row | Fail the entire snapshot before RCARS writes; do not silently skip a potentially incomplete inventory. |
| Description is missing or larger than `ie_max_demo_description_bytes` | Preserve the otherwise valid item as `dev` with a precise review reason; do not analyze or embed it. |
| One LLM analysis or embedding update fails after a source upsert | Preserve the last good analysis and embeddings, leave the item stale, and retry on a later run without blocking unrelated valid items. |
| Concurrent nightly and administrator syncs | The second run exits as `locked`; it does not issue a competing Databricks query or make writes. |
| A source type is added upstream | Preserve it as optional metadata and ingest the request with the safe default `arcade` format. No query or schema change is required; a future explicit mapping may refine its presentation. |

## Analysis, Safety, and Prompting

The analysis prompt receives a clearly delimited source-metadata section and a clearly delimited untrusted-content section. It asks for only factual, concise outputs supported by those inputs:

- card summary;
- products, topics, intended consumer audience, and difficulty;
- learning outcomes and use cases;
- detailed topics and internal recommender audience.

It must not infer a hands-on environment, access model, certification outcome, product support statement, guide step, or interaction sequence. It must not claim the experience is current beyond the observed source lifecycle data. Vocabulary normalization follows the shipped term-level workflow: unknown terms are written to `vocabulary_unknown_terms`, not used to set an item-level review flag.

The system does not make a browser request to `experience_url` or `interact_page_url` during Phase 1. This protects against tokenized URLs, authentication redirects, unstable player markup, untrusted remote content, and accidental collection of data viewers may be authorized to see but RCARS is not.

## Product Integration

Interactive Experiences participate in the existing shared retrieval path through `content_entities` and `embeddings`.

- Browse gains `Interactive Experiences` under the content-format filter and renders the format, source content type, product/language when present, and a `Launch Experience` CTA.
- The launch CTA uses validated `interact_page_url` when present and falls back to `experience_url`; it opens that external URL with `target="_blank"` and `rel="noopener noreferrer"`, does not proxy the experience, and transfers no RCARS credential.
- Advisor hydration and rationale dispatch add an `interactive_experience` branch. Rationale language distinguishes a click-through/video experience from a hands-on lab.
- Catalog detail and curator notes/review actions dispatch by source to `interactive_experience_analysis`, as architectures already do for `architecture_analysis`.
- `status='prod'`, not source-specific UI code, continues to gate default Browse and Advisor visibility.

## Verified Current-Infra Fit and Implementation Surface

The architecture is compatible with the RCARS codebase as it exists on 2026-09-28. It intentionally extends the deployed Portfolio Architecture pattern instead of introducing another ingestion framework. The table below is the concrete implementation boundary; each item is required before the feature is called complete.

| Area | Current RCARS capability | Required Interactive Experience change |
| --- | --- | --- |
| Configuration and packages | Typed `Settings` already backs the API and workers, but the backend dependency list contains no Databricks SDK. | Add a pinned `databricks-sdk` backend dependency. Add `ie_*` Settings with validation: when `ie_sync_enabled=false` (the safe default), no Databricks credentials are required; when true, hostname, warehouse ID, client ID, client secret, positive timeout, valid host allowlist, and a distinct advisory-lock ID are required. |
| Source adapter | `services/osspa_sync.py` already provides a synchronous, lock-protected inventory sync invoked from a worker thread. | Add `services/interactive_experience_sync.py` with a narrow `fetch_request_master_snapshot(settings)` adapter and `run_interactive_experience_sync(db, settings, ...)`. It uses the SDK SQL Statement Execution API against the fixed `dev.arcade_demo.request_master` object, retrieves every result chunk, and applies bounded polling/cancellation on timeout. No object name is interpolated from configuration. |
| Persistence | `content_entities` supplies common identity, visibility, retirement, scan state, and embeddings. Portfolio Architectures use 1:1 extension and analysis tables. | Create `interactive_experiences` and `interactive_experience_analysis`, plus database methods for idempotent upsert, fetch, count-active, lifecycle retirement, analysis-row lifecycle, notes, and review status. Update the shared browse query so Interactive Experience fields/analysis are joined and coalesced rather than falling through Babylon or Architecture-only joins. |
| Catalog routes | Catalog resolution explicitly recognizes only `babylon:` and `pa:` identifiers; analysis and curator dispatch have Babylon/Architecture branches. | Add the `ie:` prefix, `get_interactive_experience`, and `interactive_experience_analysis` branches to catalog detail, analysis, notes, and review routes. Update route descriptions and response handling so an IE item never attempts Babylon workload, ACL, or reporting lookups. |
| Worker and operations | The ops worker runs OSSPA synchronously inside `asyncio.to_thread(...)`, with admin job, CLI, advisory lock, progress relay, and isolated nightly-pipeline failure handling. | Register `run_interactive_experience_sync_job` and `run_interactive_experience_pipeline` in `workers/ops.py` and `workers/settings.py`; add the admin endpoint and CLI group. The nightly pipeline and the administrator command both invoke the same direct Databricks pull. One failed IE run must leave the other two results intact. |
| Retrieval and rationale | Shared embedding retrieval already supports multiple content types, but source-specific hydration/rationale has an Architecture branch only. | Add `interactive_experience` hydration and rationale language, using the IE analysis table. Preserve the existing `status='prod'` default predicate and exclude `dev`, stale/failed, and retired IE records from default results. |
| Browse UI | Browse currently models only `hands_on` and `architecture`; its `format=all` behavior assumes there are exactly two formats. | Add `interactive_experience` as a third `ContentFormat`, card treatment, detail handling, and validated launch CTA. Refactor format URL serialization to an explicit comma-separated set (for example `hands_on,interactive_experience`); retain `all` only as a backward-compatible alias for all three formats. Do not make the new format depend on Architecture-only solutions/vertical filters. |

The implementation must use source-specific methods, not a generic `else` branch. The existing code has several Architecture-versus-Babylon conditionals; each must gain an explicit Interactive Experience branch so incorrect analysis tables, card fields, and links cannot be selected silently.

### Exact implementation sequence

1. **Submit and validate the access request.** Obtain the non-production OAuth M2M service principal, approved SQL warehouse, least-privilege Unity Catalog grants, and applicable network rule. RCARS then adds the SDK, settings, source adapter, and `check-source` command, and runs the read-only check successfully.
2. **Add database and source adapter tests.** Add the two extension tables and database methods; implement direct-source row normalization, manifest validation, polling/chunk handling, and timeout cancellation using a fake SDK client in tests. Do not enable the scheduled worker yet.
3. **Implement sync safety.** Add lock, progress, idempotent upsert, shrink/empty guard, explicit-lifecycle-only retirement, LLM analysis, and atomic embedding replacement. Exercise it against a non-production `request_master` dataset with an explicitly approved test record.
4. **Wire product surfaces.** Complete catalog dispatch, recommender hydration/rationale, Browse filter/cards, admin endpoint, CLI, and nightly pipeline. Turn `RCARS_IE_SYNC_ENABLED=true` on only in the environment whose source check and smoke sync pass.
5. **Promote deliberately.** Repeat the source check and a no-op/known-delta smoke sync in production, then enable the nightly worker.

## Operations and Configuration

The implementation should add a synchronous `services/interactive_experience_sync.py` service and wrap it with the existing worker's `asyncio.to_thread(...)` pattern. It follows the current OSSPA design: an advisory lock, a standalone admin job, a CLI command, progress events, nightly orchestration, and a source-specific enable flag.

Illustrative configuration names:

```text
RCARS_IE_SYNC_ENABLED=false
RCARS_IE_DATABRICKS_HOST=...
RCARS_IE_DATABRICKS_WAREHOUSE_ID=...
RCARS_IE_DATABRICKS_TIMEOUT_S=30
RCARS_IE_ALLOWED_HOSTS=interact.redhat.com,...
RCARS_IE_MAX_DEMO_DESCRIPTION_BYTES=200000
RCARS_IE_SOURCE_SHRINK_GUARD_PCT=0.5
RCARS_IE_ADVISORY_LOCK_ID=...
RCARS_IE_ANALYSIS_MODEL=...
```

`RCARS_IE_DATABRICKS_CLIENT_ID` and `RCARS_IE_DATABRICKS_CLIENT_SECRET` are injected from the organization-approved secret manager and are deliberately not represented by settings output, job logs, or documentation examples. The implementation adds `databricks-sdk` as an explicit backend dependency, pins a compatible version, and uses its OAuth M2M support. Development access uses a separate non-production service principal and warehouse.

Human operator entry points are `rcars interactive-experiences sync`, `POST /admin/sync-interactive-experiences`, and the nightly pipeline. A `--force` option re-analyzes valid eligible records. Empty and shrink-guard failures do not trigger retirement and must be resolved at the source or reviewed by a curator; no command-line flag treats source absence as retirement. Neither entry point bypasses source-manifest, URL, or credential validation.

`RCARS_IE_SYNC_ENABLED` defaults to `false` so deploying the code before Databricks grants/secrets exist cannot break the existing Babylon or OSSPA workers. `check-source` remains available only when complete connection settings are supplied; it does not require the scheduled sync to be enabled.

### Test plan mapped to the existing test layout

Add focused tests beside the current OSSPA suite rather than depending on a live Databricks workspace in CI:

| Test module | Required coverage |
| --- | --- |
| `tests/test_interactive_experience_source.py` | SDK configuration, immutable unfiltered SQL projection including `rhca_page`, strict manifest/order/type validation, all-result-chunk handling, known video/Arcade mappings plus missing/unknown `content_type` fallback, direct/Interact URL validation, SQL timeout/cancellation, and no secret/source-text logging. |
| `tests/test_interactive_experience_sync.py` | Empty/shrink guards, repeat-run idempotency, explicit-lifecycle-only retirement, reactivation after a non-retired reappearance, missing-row reporting, progress events, lock contention, and disabled behavior. |
| `tests/test_interactive_experience_db.py` | Extension rows, `prod`/`dev`/retired status derivation, source-type/format mapping, IE-only retirement, analysis lifecycle, notes/review dispatch, and shared browse-query fields. |
| `tests/test_interactive_experience_analysis.py` | Prompt framing, byte bounds, hash stability, stale retry, and atomic embedding replacement. |
| `tests/test_catalog_interactive_routes.py` | `ie:` resolution, detail/analysis routes, non-Babylon handling, curator operations, and public `prod` visibility. |
| `src/frontend/src/pages/browse/helpers.test.ts` and Browse tests | Three-format serialization, backward-compatible `all`, Interactive Experiences filter, and launch CTA safety. |

The only live Databricks test is the operator-run `check-source` command against non-production `request_master`. CI uses a fake SDK client/statement response and must never require corporate-network access, a personal token, or a production client secret.

## Acceptance Criteria

1. A scheduled or administrator-initiated sync submits one authenticated, fixed `request_master` SQL statement through the Statement Execution API and never reads another Arcade source.
2. RCARS has only the minimum warehouse/catalog/schema/`request_master` permissions, fetches every response chunk, and accepts the source only when the returned manifest and rows match the contract.
3. Every structurally valid `request_master` record, including one whose `content_type` is missing or unfamiliar, produces `ie:{request_number}`, `source='interactive_experience'`, `content_type='interactive_experience'`, and an extension row without touching any other source.
4. A published record with a valid `demo_description` becomes `prod`, is analyzed and embedded, and is returned by Browse/Advisor through the shared status predicate.
5. An unpublished, retired, malformed, or description-less record cannot become a default-visible recommendation. Description-less but otherwise valid records remain curator-visible with a precise reason.
6. An unavailable required column, query failure, incomplete/truncated result, duplicate request number, non-text source type, invalid URL, malformed row, empty result, or guarded shrink is reported and prevents database writes.
7. A changed title, content type, product, description, language, or analysis-prompt version re-analyzes the item exactly once; a lifecycle update, launch-URL change, or private curator note alone does not.
8. A failed LLM/embedding update preserves the previous successful embeddings and leaves the item stale for retry.
9. RCARS never retires an item solely because it is absent from a source read; an explicit `Retired` lifecycle value retires only Interactive Experience rows.
10. The read-only `check-source` command validates deployed non-production `request_master` access and exits without an RCARS database write; its production counterpart passes before the production worker is enabled.
11. Tests cover connection configuration without secrets, direct-source parsing and manifest/chunk handling, status derivation, direct/Interact URL validation and CTA preference, known and fallback source-type mapping, reactivation, hash stability, repeat-run idempotency, shrink guards, retirement isolation, prompt framing, stale retries, atomic embedding swap, source-aware catalog dispatch, three-format Browse behavior, and `prod` visibility.

## Decisions Required Before Implementation

1. Confirm that `request_master` remains the supported request-level Databricks source and that its listed Phase 1 columns are stable enough for RCARS to query directly.
2. Confirm the exact `status` values, especially the `Closed` mapping, and the deployed shape/host of `rhca_page`. The default is that `rhca_page`, when present, is a validated `interact.redhat.com` launch URL and is preferred over `production_link`; every accepted direct URL remains a validated allowlisted production target.
3. Confirm that the Databricks request `Number` is immutable for a publishable experience. If it can be reused, provide an immutable replacement key.
4. Confirm that `demo_description` is approved for the configured LLM provider, its maximum size, and the expected behavior when it is absent.
5. Approve and provision the non-production and production OAuth M2M service principals and SQL warehouses with the stated least-privilege grants.
6. Confirm the RCARS OpenShift AWS region and the EgressIP/NAT IP or CIDR that Databricks must allowlist for each environment; confirm whether a CMDB registration is required for this access request.
7. Approve the experience URL host allowlist, regional/language behavior, retirement retention policy, and the later use of web-performance data.

Until decisions 1–7 are made and `request_master` validates against live Databricks, implementation stops at the connection adapter and source-contract tests. It must not infer column names, use raw upstream tables, or use unapproved credentials.

## Relationship to Other Specs

- **[Generalized Content Model](2026-07-20-generalized-content-model-design.md)** — prerequisite and shared entity/embedding contract. This spec adds a third source-specific extension/analysis pair while retaining `content_entities`, `embeddings`, shared status filtering, and `is_hands_on=FALSE`.
- **[Portfolio Architecture ingest](2026-08-06-portfolio-architecture-ingest-design.md)** — the operational pattern: source-specific adapter, extension/analysis tables, advisory lock, upsert before analysis, stale retry, atomic embeddings, source-isolated retirement, Browse format, and a `prod` visibility gate. The source mechanics differ: this spec reads one validated Databricks snapshot rather than a CSV plus Git checkout.
- **[Controlled vocabulary](2026-08-10-controlled-vocabulary-design.md)** — assumed available for product/topic normalization after Interactive Experience analysis. Unknown terms follow the existing vocabulary workflow and do not modify Databricks source data.
- **Browse and Advisor integration** — unlike the earlier Architecture Phase 1, this spec intentionally includes source-aware Browse and Advisor hydration/rationale. Interactive Experiences are still excluded from Babylon-only workload, ACL, reporting, and overlap logic unless those systems receive an explicit source branch.

## Next Steps

1. **Approve the data contract.** Confirm the exact deployed column names/types, the optional `content_type` distribution, the video/default-Arcade format mapping, status vocabulary, immutable request-number behavior, and URL-host allowlist with the Databricks owner.
2. **Provision non-production access.** After the request is approved, create the read-only OAuth M2M service principal, scoped secret, SQL warehouse permission, Unity Catalog/view grants, and applicable network rule; run `rcars interactive-experiences check-source` successfully without an RCARS database write.
3. **Write the implementation plan.** Break the approved design into independently testable migrations, settings/dependency work, source adapter and fake-SDK tests, sync/analysis implementation, source-aware routes, Browse, Advisor, and operational wiring.
4. **Pilot in non-production.** Run a full snapshot against approved test data containing at least one row for each supported request type and lifecycle state; spot-check card data, status gating, analysis, embeddings, and missing/retired behavior.
5. **Promote deliberately.** Repeat the source check and no-op/known-delta sync in production, then enable the nightly job. Keep the first production runs under curator review before treating the catalog as broadly available.
