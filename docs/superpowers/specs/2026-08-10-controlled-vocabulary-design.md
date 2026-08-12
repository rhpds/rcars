# Controlled Vocabulary — Design Spec

**Jira:** [RHDPCD-507](https://redhat.atlassian.net/browse/RHDPCD-507) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Date:** 2026-08-10
**Status:** Design
**Author:** M. Rudisill
**Depends on:** RHDPCD-359 (Generalized Content Model — vocabulary contract sketched; not delivered)
**Related:** [RHDPCD-28 / Portfolio Architecture Ingest](2026-08-06-portfolio-architecture-ingest-design.md) (consumer; does not own this work)

## Problem

RCARS analysis emits products, topics, audience, difficulty, solution areas, and learning-objective verbs as near-free text. Today the only hard constraints at ingest are `content_type` and `format_suitability`. Near-duplicates ("RHACS" vs "Advanced Cluster Security", "ApplicationPlatform" vs "Application Platform") dilute triage, Browse filters, and cross-source similarity — and the problem gets worse the moment a second content source (OSSPA) lands.

RHDPCD-359 sketched a controlled vocabulary (`vocabularies.yaml`, unknown-term review flags) but never shipped the file, loader, prompt injection, or normalization pass.

## Approach

Ship a **source-agnostic controlled vocabulary** as its own deliverable:

1. A version-controlled YAML file is the source of truth.
2. A cached loader exposes it to analyzers.
3. **Only products** are injected into analysis prompts — the one dimension where the LLM genuinely gets names wrong and enumeration pays for itself. Everything else stays out of the prompt to avoid token bloat and boxing the model in.
4. A post-analysis normalization pass snaps aliases to canonical forms before write. This is deterministic code — exact match on aliases (case-insensitive), plus light fuzzy dedup for topics.
5. Ops can override the file per environment via a ConfigMap mount (no image rebuild) — same pattern as Publishing House `ph-validation-policy`.

OSSPA ingest and Babylon Showroom analysis both *consume* this vocabulary; neither owns it.

## Design Intent

Per Nate (2026-08-06): the list exists to **normalize** — collapse near-duplicate product names, solution areas, and learning-objective verbs so triage / Browse / similarity stay consistent across sources. It is **not** meant to cage the LLM's ability to detect fine-grained topics.

- **Products are strict** — the only dimension injected into the LLM prompt. Aliases snap deterministically post-analysis. Unknown products are flagged.
- Keep `topics` fully **open** — no enumerated list, no count cap. The LLM generates as many specific topic phrases as the content warrants (current average: ~11/item, range 0–39). A post-analysis fuzzy dedup collapses near-identical topics on the same item (e.g. "GitOps with ArgoCD" vs "GitOps with Argo CD").
- Normalize the *stable* dimensions (solutions, verticals, platforms, difficulty, action verbs) via post-analysis alias matching only — never in the prompt.
- Values outside the vocabulary are accepted but flaggable for curator review (`enrichment_review_needed` / `review_reasons`) — matching the RHDPCD-359 contract. Nothing is silently dropped.

## Source of Truth

```text
src/api/rcars/data/vocabulary.yaml         # source of truth, PR-reviewed
   └─ mounted as a ConfigMap (Ansible)     # per-env override, no rebuild
```

> **Why `data/`, not `prompts/`?** The file is reference data (product names, solution areas, verbs), not a prompt template. The `data/` directory already contains `product-terms.yaml` and `workload_mapping.yaml` — the same kind of reference data. Prompt templates in `prompts/` interpolate vocabulary lists at render time but do not own them.

A draft of this file already exists in-tree (seeded from Publishing House `ph-validation-policy`, RCARS `data/product-terms.yaml` + `data/workload_mapping.yaml`, and the live OSSPA PAList Product/Solutions/Vertical/Platform columns). This spec owns finalizing that draft, the loader, normalization, and wiring — not inventing a second file.

### Dimensions

| Dimension | Closed? | In prompt? | Post-analysis action | Purpose |
| --------- | ------- | ---------- | -------------------- | ------- |
| `products` | Soft-closed | **Yes** — only dimension in prompt | Alias snap + flag unknowns | Collapse product near-duplicates across sources |
| `solutions` | Soft-closed | No | Alias snap + flag unknowns | Align solution areas; subset maps to TDPs (see below) |
| `verticals` | Soft-closed | No | Alias snap + flag unknowns | Align OSSPA Vertical column |
| `platforms` | Soft-closed | No | Alias snap + flag unknowns | Normalize deployment targets (distinct from Babylon `cloud_provider`) |
| `topics` | Open | No | Fuzzy dedup only (no flagging) | LLM coins specific topics; dedup collapses near-duplicates |
| `audience` | Open | No | No normalization (see Audience below) | Two sub-dimensions: target audience + internal recommender audience |
| `difficulty` | Closed | No | Alias snap + flag unknowns | Snap to beginner/intermediate/advanced |
| `action_verbs` | Closed per content mode | No | Flag rejected verbs | Enforce measurable verbs; organized by content mode |

#### Solutions → TDP mapping

Solutions are kept as "solutions" in the vocabulary and database, but a subset maps to official Red Hat Technology Decision Points (TDPs):

| Solution | Is a TDP? |
| -------- | --------- |
| Application Platform | Yes |
| Automation | Yes |
| Container Management | Yes |
| Virtualization | Yes |
| AI | Yes |
| Operating System | Yes |
| Integration | No — solution area |
| Security | No — solution area |
| Sovereignty | No — solution area |
| Edge | No — solution area |
| Data Services & Storage | No — solution area |

This mapping is informational — it does not change how solutions are stored or normalized. It exists so downstream consumers (reporting, alignment with Red Hat business units) can filter by TDP when needed.

#### Platforms vs. Babylon `cloud_provider`

These are **independent signals from different data sources** and must not be conflated:

- **`platforms`** (vocabulary) — describes what the content demonstrates deploying onto. Applies to all content types. An OSSPA architecture about ARO has `platform = ARO`. A Babylon lab deploying onto ARO also has `platform = ARO`.
- **`cloud_provider`** (Babylon-specific, `babylon_items.cloud_provider`) — describes where the lab's infrastructure is provisioned. Comes from workload mappings, not content analysis. A lab with `cloud_provider = azure` might deploy VMs, not ARO.

A lab can have `cloud_provider = azure` and `platform = On-Premise` (e.g., a lab provisioned in Azure that demonstrates on-prem deployment patterns). No mapping or inference between the two.

#### Audience — two sub-dimensions

| Sub-dimension | Field | Who | Purpose | Examples |
| ------------- | ----- | --- | ------- | -------- |
| **Target audience** | `audience_json` (existing) | Who the content is FOR | Match content to user queries | platform engineers, developers, data scientists |
| **Recommender audience** | `recommender_audience_json` (new) | Who at Red Hat should know about this content | Help Advisor route recommendations to the right internal roles | solution architects, consultants, TAMs, field engineers |

Both are open dimensions (no flagging). A lab about OpenShift Virtualization targets platform engineers (`audience`) but should be recommended by SAs and consultants selling VM migration (`recommender_audience`).

The `recommender_audience_json` field is added to `showroom_analysis` and `architecture_analysis`. The LLM is asked to generate both in the analysis prompt.

#### Action verbs — organized by content mode

Different content types have different measurability criteria. A hands-on lab can verify `deploy` (a pod exists). A reference architecture can verify `compare` (the reader can identify trade-offs). An interactive demo can verify `navigate` (the user reached a specific screen).

```yaml
action_verbs:
  hands_on:      # labs, sandboxes — verify via observable state change
    valid: [configure, deploy, create, build, install, implement, integrate,
            automate, manage, scale, troubleshoot, monitor, observe, migrate,
            secure, provision, verify, diagnose, validate, design]
    rejected: [understand, learn, know, be familiar with, appreciate,
               become aware, realize, recognize]
  read_through:  # reference architectures — verify via identifiable output
    valid: [compare, evaluate, assess, identify, distinguish, review,
            classify, diagram, summarize, contrast, analyze]
    rejected: [understand, learn, know, be familiar with, appreciate,
               become aware, realize, recognize]
  interactive:   # interactive demos (future) — verify via guided completion
    valid: [navigate, interact, follow, demonstrate, observe, complete,
            select, submit, verify]
    rejected: [understand, learn, know, be familiar with, appreciate,
               become aware, realize, recognize]
```

The analyzer picks the right verb subset based on `content_type`. The rejected list is the same everywhere — non-measurable cognitive-state verbs are non-measurable regardless of content format.

> **Measurability criteria:** A verb is "measurable" if completion can be verified through an observable artifact or state change — not an internal cognitive state. This aligns with Bloom's taxonomy levels Apply through Create for hands-on content, and Analyze through Evaluate for read-through content. Verbs at the Remember and Understand levels (`list`, `describe`, `explain`) are acceptable only when paired with a concrete deliverable (e.g. "list the running pods" is measurable; "list the benefits" is not).

#### Topics — open, with fuzzy dedup

No enumerated list. No count cap. The LLM generates as many specific topic phrases as the content warrants. Current data shows an average of ~11 topics per analyzed item (range 0–39), with higher counts correlating to multi-module content — this is working as intended.

**Post-analysis fuzzy dedup** collapses near-identical topics on the same item before write:
- Case-fold + collapse whitespace + strip trailing punctuation
- Token-overlap threshold (e.g. >80% shared tokens → collapse to the longer form)
- This catches "GitOps with ArgoCD" vs "GitOps with Argo CD" (87 items with this exact near-duplicate in dev)

No cross-item dedup — topics are per-item. No flagging — topics are fully open.

> **`All` as a vertical:** `All` is a meta-value meaning "industry-agnostic" — the null case, not an actual industry. The normalizer treats an empty or missing vertical as `All`.

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

### Prompt injection

**Products only.** At analysis time, the canonical product list is interpolated into:

- `src/api/rcars/prompts/architecture_analyze.txt` (OSSPA)
- `src/api/rcars/prompts/analyze_showroom.txt` (Babylon)

The prompt instructs the model to prefer a listed product name where one fits and only coin a new one when nothing matches. No other vocabulary dimension is injected into the prompt.

A shared renderer (`render_vocabulary_block(vocab, content_type)`) builds the product instruction block and appends content-mode-specific verb guidance. Both analyzers call this renderer; neither hardcodes vocabulary lists.

### Post-analysis normalization

Deterministic code — runs after the LLM returns structured JSON, before writing to the database. Mirrors `_sanitize_format_suitability` in `scan.py`.

**Alias snap** (products, solutions, verticals, platforms, difficulty): build a case-insensitive lookup dict from the YAML `{alias → canonical_name}`. Exact match only. Unknown values are kept and flagged.

**Topic fuzzy dedup** (topics only): case-fold, collapse whitespace, compute token overlap between all topic pairs on the same item. Collapse pairs with >80% token overlap to the longer form.

**Verb validation** (action verbs): check LO verbs against the content-mode-specific valid/rejected lists. Flag rejected verbs.

| `review_reasons` reason | Dimension | When |
| ----------------------- | --------- | ---- |
| `unknown_product` | products (soft-closed) | Product not in vocabulary and not an alias |
| `unknown_solution` | solutions (soft-closed) | Solution not in vocabulary and not an alias |
| `unknown_vertical` | verticals (soft-closed) | Vertical not in vocabulary and not an alias |
| `unknown_platform` | platforms (soft-closed) | Platform not in vocabulary |
| `unknown_difficulty` | difficulty (closed) | Value doesn't snap to beginner/intermediate/advanced |
| `rejected_action_verb` | action_verbs (closed) | LO verb in the rejected list for this content mode |

`topics` and `audience` are **open** dimensions — never flagged. In all cases, the original value is **preserved** alongside the flag — nothing is silently dropped.

## Configuration

| Setting | Default | Purpose |
| ------- | ------- | ------- |
| `vocabulary_path` | `data/vocabulary.yaml` (ConfigMap mount overrides) | Controlled-vocabulary source |

Ansible mounts the file as a ConfigMap on API + scan-worker (and recommend-worker if any consumer runs there) so ops can hot-patch terms without an image rebuild.

## Scope

### In scope

- Finalize `vocabulary.yaml` (products, solutions with TDP mapping, verticals, platforms, difficulty, action verbs by content mode).
- `vocabulary.py` loader + cache + reload endpoint.
- Prompt injection for products only (both analyzers via shared renderer).
- Post-analysis normalization: alias snap for soft-closed/closed dimensions, fuzzy dedup for topics, verb validation by content mode.
- `enrichment_review_needed` / `review_reasons` flagging for unknowns.
- `recommender_audience_json` field addition to analysis tables.
- ConfigMap mount via Ansible.
- Unit tests: alias snap, unknown-product flag, rejected-verb flag, topic dedup, loader override path.

### Out of scope

- Re-analyzing the entire Babylon corpus on day one (vocabulary enforcement starts on the next re-analysis cycle; existing rows keep current values until then).
- Building a curator UI for editing the vocabulary (file + PR / ConfigMap for now).
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
| Alias snap: `FSI` → `Financial Services` vertical | Unit | Case-insensitive exact match |
| Unknown product flagged, not dropped | Unit | Value kept; `enrichment_review_needed`; `unknown_product` reason |
| Unknown solution flagged | Unit | `unknown_solution` reason |
| Rejected LO verb flagged (hands-on) | Unit | `understand` → review reason on Babylon lab analysis |
| Read-through verb accepted | Unit | `compare` valid for architecture content |
| Topic fuzzy dedup | Unit | "GitOps with ArgoCD" and "GitOps with Argo CD" collapse to one |
| Topic count not capped | Unit | Item with 20+ legitimate topics keeps all of them |
| Products injected into prompt | Unit | Rendered prompt contains canonical product names |
| Solutions NOT injected into prompt | Unit | Rendered prompt does not contain solution list |
| Architecture prompt includes product vocab | Unit | Interpolated products present in rendered prompt |
| Showroom prompt includes product vocab | Unit | Same for Babylon analyzer |
| Reload endpoint clears cache | Integration | POST reload → next load reads fresh file |

## Next Steps

1. **Review and approve this spec** — confirm the products-only prompt injection approach, the audience split, action verb organization by content mode, and the topic fuzzy dedup.
2. **Open / link a Jira child under RHDPCD-25** for tracking.
3. **Write implementation plan** — loader, prompt injection (products only, both analyzers), normalization (alias snap + topic dedup + verb validation), `recommender_audience_json` field, ConfigMap, tests.
4. **Coordinate with OSSPA ingest** — preferred ordering: OSSPA ingest ships first (analysis lands free-text), vocabulary ships second with a `--force` re-analysis of all OSSPA items to normalize. If vocabulary ships first, the architecture prompt (`architecture_analyze.txt`) does not exist yet — vocabulary injection for that prompt is a no-op until OSSPA creates the file. Either order works at the data layer; the preferred ordering avoids a dangling prompt reference.
