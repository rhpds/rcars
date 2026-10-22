# Showroom analysis isolation

## Intent and approval

RHDPCD-74 is the commit key only. Do not update its description, comments, or status. The user approved the content-source resolution policy in the October 16 conversation. This document records that policy; implementation details identified below are engineering recommendations, not additional user decisions.

Prevent unrelated CatalogItems from acquiring one another's Showroom analysis or recommendation identity. Fix the rules going forward and regenerate disposable scan artifacts rather than reconstructing historical donor chains.

## Required boundaries

- The same item means its namespace-qualified catalog/component identity with only its known stage suffix removed. Do not merge names based on lab number, title, repository, infrastructure base, or approximate similarity.
- Sharing between that item's dev/event/prod variants requires the exact effective repository, requested Git ref, and matching content hash. Also require the fetched commit and content path to match; hashes never establish item identity.
- Different items scan independently even if all repository/ref/hash values match. Duplicate scans are an acceptable correctness tradeoff.
- Explicit virtual/published-to-content-component relationships may share analysis. Do not restrict this to the `published` folder or to a fixed chain length.
- Resolve each stage's component graph independently. Different stage configuration or content gets independent analysis.

## Content source resolution

Resolve the effective Showroom configuration from allowed CRD fields and component parameter overrides. Starting at the requesting item, select the nearest applicable explicit content declaration along its actual dependency path. A nearer repo/ref/path override changes the effective source; it must not borrow the underlying component's unmodified analysis.

Transparent wrappers can delegate through multiple levels. Stop content traversal on a branch when its explicit Showroom source is resolved: dependencies below that source are not additional analysis owners, regardless of whether they also define a Showroom. Never propagate analysis downward into them.

Retain declaration field-presence information: an omitted ref and an explicitly selected default HEAD must not accidentally acquire a deeper component's ref. Existing curator URL/content-path overrides remain authoritative for that target; changing them produces target-owned effective configuration and invalidates its previous analysis signature.

Do not classify infrastructure through component names, folders, number of levels, LLM judgments, or the presence of a previously inherited `showroom_url`. A component with no Showroom is not automatically infrastructure; it simply does not declare content at that point. Keep content resolution separate from existing infrastructure/workload inheritance.

Multiple distinct candidate sources without an explicit selection are ambiguous: do not choose the first dependency. Missing components, unresolved variables/refs, dependency cycles, and excessive depth must be visible resolution failures. No source anywhere is a distinct, ordinary no-Showroom outcome.

Persist the explicit source component, effective repo/ref/path, relationship path, and override origin. A source component need not itself have a CatalogItem row. Two separate roots that happen to use matching URLs remain separate; a transparent explicit delegation can identify the same content owner.

## Scanning and reuse

Remove global content-hash donor lookup. Never use global URL/ref or URL/SHA groups for scan selection, propagation, or recommendation promotion.

Engineering recommendation: schedule at most one job per resolved CatalogItem stage that actually needs work, including virtual items. Routine maintenance must not enqueue every valid unchanged item. Resolve and verify its source before looking for a permitted same-item/explicit-owner donor; fetch content only if its revision or other relevant inputs need checking. This avoids pre-fetch deduplication races; occasional simultaneous duplicate LLM calls are acceptable. Eliminate unsolicited sibling fan-out rather than introducing another hierarchy of propagation exceptions.

An eligible donor must have the same authorized content-owner/item scope, effective repo, exact requested ref, fetched commit, content path, content hash, and analysis-input fingerprint. The fingerprint covers canonical item information actually sent to the LLM, prompt/vocabulary content, model, and analysis policy version. Canonicalize the prompt's CI name to the stage-independent scope; differing other prompt metadata conservatively prevents reuse. Old unscoped analyses and stale/failed donors are ineligible.

When a summary embedding needs creating or updating, generate it from the target's own display name and keywords. Do not regenerate an existing valid target embedding whose text, model, and embedding configuration are unchanged. Module embeddings can be copied only from the authorized identical analysis. Store donor identity or fresh-generation provenance; do not discard `reused_from` after returning from the analyzer.

Explicit virtual relationships supply content provenance, not permission to borrow across different effective overrides. Materialize each virtual item's analysis/card/embeddings from its resolved source so consumers do not guess from generic `base_ci_name`.

## Incremental maintenance: unchanged means no work

- Same resolved source configuration, remote commit, analysis context, and complete current embeddings: a lightweight freshness check only; no clone, analysis job, LLM call, embedding call, or artifact replacement. The analysis context fingerprint covers non-content prompt metadata, prompt/vocabulary text, model, and policy version so this fast path does not miss prompt/configuration changes.
- New commit but identical selected content hash and analysis context: inspect the fetched content, then advance the verified revision/provenance without an LLM call or embedding regeneration. Preserve the original generation revision and `last_analyzed` timestamp; store the newly verified revision separately from when the LLM actually ran. This avoids repeatedly cloning the same irrelevant commit on every maintenance run.
- Changed analysis content or analysis context: analyze that item/stage or use an authorized matching scoped donor. Recreate only embeddings whose text/configuration changed or whose artifacts are missing.
- Changed embedding-only inputs (for example catalog keywords that are not in the analysis prompt, or embedding-model configuration): repair affected embeddings without rerunning otherwise-current LLM analysis. Display-name changes that affect both the prompt and embedding text invalidate both as appropriate.
- Explicit force/rescan-from-scratch bypasses these skip paths for the requested targets. The one-time reset does not change the steady-state incremental policy.

These rules apply equally to materialized virtual items. Source changes, failed ref resolution, missing embeddings, and stale/invalid provenance cannot be misreported as an unchanged complete scan.

## Source correctness

Support branch, tag (including annotated tag), and commit-ID refs. A missing or unresolvable requested ref fails; never silently clone the default branch. An absent ref means the repository's default HEAD and remains distinct from an explicitly requested ref for reuse.

Retain substantive `index.adoc` content. Navigation and known Publishing House/template stubs alone are not analyzable content. Reject them before either donor lookup or LLM calls. Do not add an arbitrary minimum length that rejects valid short content. Read and hash the same selected content path for scanning and staleness checks; respect path containment.

## Recommendation behavior

Replace hash-only prod promotion with exact same-item stage counterpart checks using verified analysis signatures. Promotion must respect requested stages and explicit content-ID scope. Preserve explicit virtual identity only through its persisted stage-specific content relationship, not infrastructure-base links or URL equality. Ambiguous multiple virtual targets must not be chosen arbitrarily.

## Rebuild and preservation

After deploying the boundary fix, recreate Babylon Showroom-generated analysis fields, entity-card fields, summary/module embeddings, and dependent overlap results. No donor-chain repair or general-purpose migration framework is needed.

Preserve content identities, retirement/soft-delete metadata, retirement workflows and Jira/GitHub links, usage/performance/nonprod/field-source records, advisor history, jobs/token logs, infrastructure/workload mappings, vocabulary decisions, enrichment tags, credentials/roles, Showroom overrides/content paths, and human-curated fields including duration and notes. Leave OSSPA architecture analysis/embeddings unchanged.

Provide a dry-run-first, explicitly executed Babylon-scoped reset. Quiesce scheduled/manual scans and drain or discard old scan jobs before reset; prevent an in-flight pre-reset result from restoring old artifacts. Reset derived analysis fields in place where necessary to preserve curated fields. A failed or template-only rescan must not leave the old contaminated summary searchable.

Rebuild execution is an operational step requiring separate confirmation, not an automatic deploy/startup migration. Do not run `init-db --drop` or drop/truncate tables.

Engineering recommendation: perform the one-time reset in an explicit maintenance window with scan producers/workers stopped and old work drained. A dry run is read-only and execution rejects outstanding scan jobs. Do not introduce a generation-tracking subsystem or ongoing migration machinery merely for this rebuild.

## Engineering choices to review with the plan

- Use a pure content-source resolver with a 32-component maximum path length, cycle detection, allowlisted metadata, and deterministic ambiguity handling.
- Persist structured source provenance and a versioned analysis signature using additive idempotent schema changes; keep existing infra fields for their existing purpose.
- Schedule individual stage jobs and reuse only after source verification; do not optimize fetches across unrelated items in this change.
- Preserve the ordinary rescan-all operation, but make its forced analysis semantics explicit. Keep artifact reset an opt-in operational tool.
- Use existing Python/pytest/PostgreSQL patterns and no new dependencies or frontend feature work.

## Acceptance

The LB2081 crypto placeholders cannot receive Ansible analysis. Independent items cannot exchange analysis or recommendation identities through matching hashes, URLs, or SHAs. Identical stages of one item can reuse verified analysis, while changed refs or content cannot. A four-level virtual chain resolves its nearest explicit content source without copying analysis into the infrastructure base. Reset/rebuild changes only enumerated derived artifacts and preserves historical and curated state.
