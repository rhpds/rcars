# Controlled Vocabulary — Design Spec

**Jira:** [RHDPCD-507](https://redhat.atlassian.net/browse/RHDPCD-507) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Date:** 2026-08-10
**Status:** Design
**Author:** M. Rudisill
**Depends on:** RHDPCD-359 (Generalized Content Model — vocabulary contract sketched; not delivered)
**Related:** [RHDPCD-28 / Portfolio Architecture Ingest](2026-08-06-portfolio-architecture-ingest-design.md) (consumer; does not own this work)

## Problem

RCARS analysis emits products, topics, audience, difficulty, solution areas, and learning-objective verbs as near-free text. Today the only hard constraints at ingest are `content_type` and `format_suitability`. Near-duplicates ("RHACS" vs "Advanced Cluster Security", "ApplicationPlatform" vs "Application Platform") dilute triage, Browse filters, and cross-source similarity — and the problem gets worse the moment a second content source (OSSPA) lands.

RHDPCD-359 sketched a controlled vocabulary (`vocabularies.yaml`, unknown-term review flags) but never shipped the file, loader, prompt injection, or normalization pass. That work is cross-cutting: it touches every analyzer, not just Portfolio Architecture ingest. Landing it inside the OSSPA ingest spec would munge an all-sources concern into a single-source feature.

## Approach

Ship a **source-agnostic controlled vocabulary** as its own deliverable:

1. A version-controlled YAML file is the source of truth.
2. A cached loader exposes it to analyzers.
3. Analysis prompts interpolate the lists and instruct the model to prefer listed terms.
4. A post-analysis normalization pass snaps aliases / near-misses to canonical forms before write.
5. Ops can override the file per environment via a ConfigMap mount (no image rebuild) — same pattern as Publishing House `ph-validation-policy`.

OSSPA ingest and Babylon Showroom analysis both *consume* this vocabulary; neither owns it.

## Design Intent

Per Nate (2026-08-06): the list exists to **normalize** — collapse near-duplicate product names, solution areas, and learning-objective verbs so triage / Browse / similarity stay consistent across sources. It is **not** meant to cage the LLM's ability to detect fine-grained topics.

- Keep `topics` **broad**; let the model coin specific topics (e.g. "web search augmentation").
- Do not enumerate niche capabilities. The OSSPA `PAList.csv` `metaKeyword` column alone has ~186 near-unique keywords (e.g. "granite 3.2 8b instruct") — never codify that granularity.
- Normalize the *stable* dimensions: products, solutions, verticals, difficulty, LO verbs.
- Values outside the vocabulary are accepted but should be flaggable for curator review (`enrichment_review_needed` / `review_reasons`) — matching the RHDPCD-359 contract. Nothing is silently dropped.

## Source of Truth

```text
src/api/rcars/data/vocabulary.yaml         # source of truth, PR-reviewed
   └─ mounted as a ConfigMap (Ansible)     # per-env override, no rebuild
```

> **Why `data/`, not `prompts/`?** The file is reference data (product names, solution areas, verbs), not a prompt template. The `data/` directory already contains `product-terms.yaml` and `workload_mapping.yaml` — the same kind of reference data. Prompt templates in `prompts/` interpolate vocabulary lists at render time but do not own them.

A draft of this file already exists in-tree (seeded from Publishing House `ph-validation-policy`, RCARS `data/product-terms.yaml` + `data/workload_mapping.yaml`, and the live OSSPA PAList Product/Solutions/Vertical/Platform columns). This spec owns finalizing that draft, the loader, injection, normalization, and wiring — not inventing a second file.

Layout mirrors the Publishing House ConfigMap:

```yaml
# vocabulary.yaml — source-agnostic; shared by all content analyzers.
products:                                    # canonical Red Hat product names + aliases
  - {name: "Red Hat Advanced Cluster Security", aliases: [RHACS, ACS, StackRox]}
  - ...
solutions:                                   # high-level solution areas
  - {name: "Application Platform", aliases: [ApplicationPlatform, ApplicationDevelopment]}
  - ...
verticals:                                   # industry verticals
  - {name: "Financial Services", aliases: [FSI]}
  - ...
platforms:  [On-Premise, AWS, Azure, Cloud, Edge]   # deployment target (normalization aid)
topics:     [gitops, service-mesh, observability, ...]   # BROAD only — LLM coins the specifics
audience:   ["platform engineers", developers, ...]      # roles (open-ended seed set)
difficulty: [beginner, intermediate, advanced]           # closed set
action_verbs_valid:    [deploy, configure, integrate, ...]   # LO verbs (Babylon labs)
action_verbs_rejected: [understand, learn, know, ...]        # non-measurable — flag/replace
```

### Dimensions

| Dimension | Closed? | Purpose |
| --------- | ------- | ------- |
| `products` | Soft-closed (aliases normalize; unknown → flag) | Collapse product near-duplicates across sources |
| `solutions` | Soft-closed | Align OSSPA Solutions + architecture `solution_areas` |
| `verticals` | Soft-closed | Align OSSPA Vertical column |
| `platforms` | Soft-closed | Normalize deployment-target tokens (LLM not asked to invent these) |
| `topics` | Open (broad guide only) | Prefer listed broad terms; model coins specifics |
| `audience` | Open (seed set) | Role descriptors |
| `difficulty` | Closed | Snap near-misses to beginner/intermediate/advanced |
| `action_verbs_*` | Closed (Babylon) | Enforce measurable LO verbs; reject non-measurable |

`action_verbs_*` apply to labs, not architectures. They live in the shared file so Babylon and any future lab-like source share one list.

> **`All` as a vertical:** `All` is a meta-value meaning "industry-agnostic," not an actual industry. It is stored as the canonical form for items with no specific vertical. The normalizer treats an empty or missing vertical as `All`. It is not a member of the vertical taxonomy in the same sense as `Financial Services` — it is the null case.

> **Measurability criteria for action verbs:** A verb is "measurable" if a lab environment can verify completion through observable state change. `deploy` → a pod exists; `configure` → a setting changed. `explore` and `analyze` are included as valid because labs can verify them through concrete output (e.g., "run this query and observe the result"). `understand` and `learn` are rejected because they describe internal cognitive states with no observable artifact.

## Runtime

### Loading

```python
# src/api/rcars/services/vocabulary.py
@lru_cache
def load_vocabulary() -> dict: ...   # {"solutions": [...], "products": [...], ...}
```

- Reads `RCARS_VOCABULARY_PATH` (env var, mapped to `vocabulary_path` Pydantic setting; default: packaged `data/vocabulary.yaml`).
- ConfigMap mount path: `/opt/app-root/config/vocabulary.yaml` (set via Ansible `vocabulary_path` var on API + scan-worker deployments).
- Cached once per process via `@lru_cache`. **Update contract:** a ConfigMap change requires a rolling restart of API + scan-worker + recommend-worker to take effect. An admin endpoint `POST /api/v1/admin/reload-vocabulary` calls `load_vocabulary.cache_clear()` for hot-reload without restart. During rollout, processes may briefly run different vocabulary versions — this is acceptable because normalization is idempotent (re-analysis corrects any drift).

### Injection

At analysis time, vocabulary lists are interpolated into:

- `src/api/rcars/prompts/architecture_analyze.txt` (OSSPA)
- `src/api/rcars/prompts/analyze_showroom.txt` (Babylon)

The prompt instructs the model to prefer a listed term where one fits and only coin a new one when nothing matches.

A shared renderer (`render_vocabulary_block(vocab, content_type)`) builds the vocabulary instruction block. It includes `action_verbs_*` only when `content_type` is `lab` or `demo` (not `architecture`). Both analyzers call this renderer; neither hardcodes vocabulary lists.

### Normalization

A post-analysis pass — mirroring `_sanitize_format_suitability` in `scan.py` — snaps aliases and obvious near-misses to canonical form before write. Unknown values are kept and flagged:

| `review_reasons` reason | Dimension | When |
| ----------------------- | --------- | ---- |
| `unknown_product` | products (soft-closed) | Product not in vocabulary and not an alias |
| `unknown_solution` | solutions (soft-closed) | Solution not in vocabulary and not an alias |
| `unknown_vertical` | verticals (soft-closed) | Vertical not in vocabulary and not an alias |
| `unknown_platform` | platforms (soft-closed) | Platform not in vocabulary |
| `unknown_difficulty` | difficulty (closed) | Value doesn't snap to beginner/intermediate/advanced |
| `rejected_action_verb` | action_verbs (closed) | LO verb in `action_verbs_rejected` |

`topics` and `audience` are **open** dimensions — they are never flagged. The LLM is encouraged to coin specific topics and audience terms beyond the seed lists. Flagging is reserved for soft-closed and closed dimensions where an unlisted value indicates a normalization gap, not model creativity.

In all cases, the original value is **preserved** alongside the flag — nothing is silently dropped. This matches the RHDPCD-359 review-flag contract.

## Configuration

| Setting | Default | Purpose |
| ------- | ------- | ------- |
| `vocabulary_path` | `data/vocabulary.yaml` (ConfigMap mount overrides) | Controlled-vocabulary source |

Ansible mounts the file as a ConfigMap on API + scan-worker (and recommend-worker if any consumer runs there) so ops can hot-patch terms without an image rebuild.

## Scope

### In scope

- Finalize `vocabulary.yaml` (products, solutions, verticals, platforms, broad topics, audience seed, difficulty, LO verbs).
- `vocabulary.py` loader + cache.
- Prompt injection for **both** architecture and Showroom analyzers.
- Post-analysis normalization + `enrichment_review_needed` / `review_reasons` flagging for unknown products (and rejected LO verbs on Babylon).
- ConfigMap mount via Ansible.
- Unit tests: alias snap, unknown-product flag, rejected-verb flag, loader override path.

### Out of scope

- Re-analyzing the entire Babylon corpus on day one (vocabulary enforcement starts on the next re-analysis cycle; existing rows keep current values until then).
- Building a curator UI for editing the vocabulary (file + PR / ConfigMap for now).
- Turning `topics` into a closed taxonomy.
- Query-time synonym expansion — that remains `data/product-terms.yaml` (separate concern: query rewriting, not analysis output).

## Relationship to Other Specs

- **RHDPCD-359 (Generalized Content Model)** — sketched the vocabulary contract (`vocabularies.yaml`, unknown-term review flags). This spec delivers that contract under the concrete path `data/vocabulary.yaml`.
- **RHDPCD-28 (Portfolio Architecture Ingest)** — consumes the vocabulary once this ships; OSSPA Phase 1 must not block on it. Architecture analysis can land free-text first and pick up normalization on the next re-analysis after this ships, or land with injection if this ships first — either order is fine because the two are independently deployable.
- **Query synonym expansion (`product-terms.yaml`)** — complementary, not replaced. Analysis-time normalization ≠ query-time expansion.

## Testing


| Test | Type | Assertion |
| ---- | ---- | --------- |
| Loader reads packaged default | Unit | Canonical product list non-empty |
| Loader honors `vocabulary_path` override | Unit | Mount/override path wins |
| Alias snap: `RHACS` → canonical product | Unit | Normalized before write |
| Unknown product flagged, not dropped | Unit | Value kept; `enrichment_review_needed`; `unknown_product` reason |
| Rejected LO verb flagged | Unit | `understand` → review reason on Babylon analysis |
| Architecture prompt includes vocabulary lists | Unit | Interpolated products/solutions present in rendered prompt |
| Showroom prompt includes vocabulary lists | Unit | Same for Babylon analyzer |

## Next Steps

1. **Review and approve this spec** — confirm dimensions, open-vs-closed choices (especially broad `topics`), and the unknown-term flagging contract.
2. **Open / link a Jira child under RHDPCD-25** for tracking.
3. **Write implementation plan** — loader, prompt injection (both analyzers), normalization, ConfigMap, tests.
4. **Coordinate with OSSPA ingest** — preferred ordering: OSSPA ingest ships first (analysis lands free-text), vocabulary ships second with a `--force` re-analysis of all OSSPA items to normalize. If vocabulary ships first, the architecture prompt (`architecture_analyze.txt`) does not exist yet — vocabulary injection for that prompt is a no-op until OSSPA creates the file. Either order works at the data layer; the preferred ordering avoids a dangling prompt reference.
