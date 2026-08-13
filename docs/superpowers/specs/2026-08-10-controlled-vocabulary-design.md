# Controlled Vocabulary — Design Spec

**Jira:** [RHDPCD-507](https://redhat.atlassian.net/browse/RHDPCD-507) (child of [RHDPCD-25](https://redhat.atlassian.net/browse/RHDPCD-25))
**Date:** 2026-08-10 (revised 2026-08-13)
**Status:** Design
**Author:** M. Rudisill
**Depends on:** RHDPCD-359 (Generalized Content Model — vocabulary contract sketched; not delivered)
**Related:** [RHDPCD-28 / Portfolio Architecture Ingest](2026-08-06-portfolio-architecture-ingest-design.md) (consumer; does not own this work)

## Problem

RCARS names the same thing differently depending on where you look.

Analysis emits products, topics, audience, difficulty, and solution areas as near-free text. The only hard constraints at ingest are `content_type` and `format_suitability`. Near-duplicates ("RHACS" vs "Advanced Cluster Security", "ApplicationPlatform" vs "Application Platform") dilute triage, Browse filters, and cross-source similarity — and the problem compounds the moment a second content source (OSSPA) lands.

Worse, there is already a *second* product list. `src/api/rcars/data/product-terms.yaml` maps acronyms and synonyms for Advisor query expansion (`_load_product_terms()` / `_expand_query_terms()` in `services/recommender/pipeline.py`). It has drifted from every other notion of a canonical product name, and internally from itself:

| Term | `product-terms.yaml` expansion |
| ---- | ------------------------------ |
| `ACS` | Advanced Cluster Security for Kubernetes |
| `RHACS` | **Red Hat** Advanced Cluster Security for Kubernetes |
| `OCP` | OpenShift Container Platform (no "Red Hat") |
| `ACM` | Advanced Cluster Management for Kubernetes |

`ACS` and `RHACS` are the same product and expand to two different strings in the same file. So the query side and the analysis side can disagree about what a product is called, which is precisely the failure this work exists to prevent.

RHDPCD-359 sketched a controlled vocabulary (`vocabularies.yaml`, unknown-term review flags) but never shipped the file, loader, prompt injection, or normalization pass.

## Approach

Ship a **source-agnostic controlled vocabulary** as its own deliverable:

1. A version-controlled YAML file is the single source of truth for canonical names and their aliases.
2. A cached loader exposes it to every consumer, with fail-fast validation at load.
3. **Products and action-verb hints** are injected into analysis prompts. Nothing else — the remaining dimensions are normalized after the fact, to avoid token bloat and boxing the model in.
4. A post-analysis normalization pass snaps aliases to canonical forms before write. Deterministic code: case-insensitive exact match on aliases, plus topic dedup.
5. **The same list drives Advisor query expansion.** `product-terms.yaml` is merged in and deleted.
6. Ops can override the file per environment via a ConfigMap mount (no image rebuild) — same pattern as Publishing House `ph-validation-policy`.

OSSPA ingest and Babylon Showroom analysis both *consume* this vocabulary; neither owns it.

### One list, two consumers

This is the central requirement. The same canonical names must be used in both directions:

```text
                    vocabulary.yaml
                    (alias → canonical)
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
    Advisor query expansion      Scan / analyze
    user types "RHACS"           LLM says "RHACS"
    → search canonical name      → store canonical name
```

Today those two paths use different files with different answers. After this work there is one file and one answer.

## Design Intent

Per Nate (2026-08-06, refined 2026-08-13): the list exists to **normalize** — collapse near-duplicate product names and solution areas so triage / Browse / similarity / query expansion stay consistent across sources. It is **not** meant to cage the LLM's ability to detect fine-grained topics, and it is **not** a quality gate on LLM output.

- **Products are the strict dimension** — injected into the prompt, alias-snapped post-analysis, unknowns queued for admin review. Also the source for Advisor query expansion.
- Keep `topics` fully **open** — no enumerated list, no count cap. The LLM generates as many specific topic phrases as the content warrants (current average ~11/item, range 0–39). Post-analysis dedup collapses spelling variants of the same topic on the same item.
- Normalize the *stable* dimensions (solutions, verticals, platforms, difficulty) via post-analysis alias matching only — never in the prompt.
- **Action verbs are guidance, not enforcement.** The mode-appropriate verb list goes into the prompt as a nudge toward measurable objectives. Nothing is validated, rejected, or flagged. See "Action verbs" below for why.
- Values outside the vocabulary are **always accepted and stored verbatim** — nothing is ever dropped or rejected. Unknown terms are recorded once per *term*, not flagged per item, and resolved through an admin review queue. See "Unknown terms".

## Source of Truth

```text
src/api/rcars/data/vocabulary.yaml         # source of truth, PR-reviewed
   └─ mounted as a ConfigMap (Ansible)     # per-env override, no rebuild
```

> **Why `data/`, not `prompts/`?** The file is reference data (product names, solution areas, verbs), not a prompt template. The `data/` directory already contains `workload_mapping.yaml` — the same kind of reference data. Prompt templates in `prompts/` interpolate vocabulary lists at render time but do not own them.

A draft of this file already exists in-tree (seeded from Publishing House `ph-validation-policy`, RCARS `data/product-terms.yaml` + `data/workload_mapping.yaml`, and the live OSSPA PAList Product/Solutions/Vertical/Platform columns). This spec owns finalizing that draft, the loader, normalization, and wiring — not inventing a second file.

### Dimensions

| Dimension | Closed? | In prompt? | Post-analysis action | Applies to |
| --------- | ------- | ---------- | -------------------- | ---------- |
| `products` | Soft-closed | **Yes** | Alias snap; unknowns recorded | All content |
| `action_verbs` | n/a | **Yes — hints only** | **None** | All content |
| `difficulty` | Closed | No | Alias snap; unknowns recorded | All content |
| `topics` | Open | No | Dedup only (no flagging) | All content |
| `audience` | Open | No | None | All content |
| `solutions` | Soft-closed | No | Alias snap; unknowns recorded | **Architecture only** |
| `verticals` | Soft-closed | No | Alias snap; unknowns recorded | **Architecture only** |
| `platforms` | Soft-closed | No | Alias snap; unknowns recorded | **Architecture only** |

**The mechanism is source-agnostic; only the wiring is architecture-first.** The normalizer is driven by the dimensions declared in the YAML and a field-mapping table — not by hardcoded per-source logic. Extending any dimension to Babylon later is a column plus a mapping entry, not new normalizer code.

#### Why solutions / verticals / platforms are architecture-only

Babylon labs are not authored around these concepts. Asking the LLM for them would fill the columns with guesses:

- **Solutions and verticals** — labs are product-centric and industry-agnostic. There is nothing in the showroom content to ground a vertical against.
- **Platforms** — most labs do not *state* a deployment target; they run on whatever RHDP provisioned them onto. The model would infer platform from infrastructure mentions in the content, which is `cloud_provider` — the exact conflation the section below warns against. A lab that genuinely demonstrates deploying onto ARO already surfaces that through `products` and `topics`.

OSSPA architectures carry all three explicitly in the PAList CSV, so they are grounded there.

#### Solutions → TDP mapping

Solutions are kept as "solutions" in the vocabulary and database, but a subset maps to official Red Hat Technology Decision Points (TDPs), marked `is_tdp: true` in the YAML:

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

- **`platforms`** (vocabulary) — what the content demonstrates deploying onto. An OSSPA architecture about ARO has `platform = ARO`.
- **`cloud_provider`** (`babylon_items.cloud_provider`) — where the lab's infrastructure is provisioned. Comes from workload mappings, not content analysis.

A lab can have `cloud_provider = azure` and demonstrate on-prem deployment patterns. No mapping or inference between the two. Since `platforms` is architecture-only in this phase, the two never meet in practice today — the distinction is recorded so that a future extension to Babylon does not collapse them.

#### Audience — two sub-dimensions

| Sub-dimension | Field | Who | Purpose | Examples |
| ------------- | ----- | --- | ------- | -------- |
| **Target audience** | `audience_json` (existing) | Who the content is FOR | Match content to user queries | platform engineers, developers, data scientists |
| **Recommender audience** | `recommender_audience_json` (new) | Who at Red Hat should know about this content | Help Advisor route recommendations to the right internal roles | solution architects, consultants, TAMs, field engineers |

Both are open dimensions — no enumerated list, no aliases, no normalization, no flagging. A lab about OpenShift Virtualization targets platform engineers (`audience`) but should be recommended by SAs and consultants selling VM migration (`recommender_audience`).

`recommender_audience_json` is added to **both** `showroom_analysis` and `architecture_analysis`, and both analysis prompts ask for it. RHDPCD-28 already specs the `architecture_analysis` half; this spec delivers the `showroom_analysis` half. It populates for Babylon via the one-off re-scan (see Rollout).

> **Note:** strictly, this field is not vocabulary work — it is never normalized. It lives here because the *distinction* between target and recommender audience is defined here, and both specs reference this section. Nothing currently reads `recommender_audience_json`; it is groundwork for role-aware Advisor routing.

#### Action verbs — prompt guidance only

Different content types have different measurability criteria. A hands-on lab can verify `deploy` (a pod exists). A reference architecture can verify `compare` (the reader can identify trade-offs). An interactive demo can verify `navigate` (the user reached a specific screen).

The mode-appropriate verb list is rendered into the analysis prompt as a **nudge**:

> Write each learning objective around a concrete, observable action such as *deploy, configure, troubleshoot, migrate*. Avoid vague framings like *understand*, *learn*, or *be familiar with*.

**There is no validation, rejection, or flagging of verbs.** This is a deliberate reversal of an earlier draft, for three reasons:

1. **Learning objectives are free-text sentences**, not verb fields. Extracting a verb from prose to check it would violate the project's own "no prose parsing" rule.
2. **Restructuring the LO shape to carry a verb would break nine consumers** — `RecCard.tsx:132`, `BrowsePage.tsx:790`, `rationale.py:44`, `handlers.py:29`, `overlap_assessment.py:95`, `serialize.py:27`, `models.py:30`, and most dangerously `analyzer.py:562`, which folds learning objectives into the **embedding text**. Objects there would stringify into the vector and degrade similarity search corpus-wide.
3. **A review flag with no remediation path is pure cost.** There is no workflow in RCARS where a curator rewrites a learning objective. Flagging a verb on ~1,700 items would build a queue with nothing at the end of it.

Quality improves where it is cheap to improve — at generation time. Existing objectives are left untouched and simply get better phrasing whenever an item is next analyzed.

```yaml
action_verbs:
  hands_on:      # labs, demos, sandboxes — verify via observable state change
    valid: [configure, deploy, create, build, install, implement, integrate,
            automate, manage, scale, troubleshoot, monitor, observe, migrate,
            secure, provision, verify, diagnose, validate, design]
    rejected: &rejected_verbs
      [understand, learn, know, be familiar with, appreciate,
       become aware, realize, recognize]
  read_through:  # reference architectures — verify via identifiable output
    valid: [compare, evaluate, assess, identify, distinguish, review,
            classify, diagram, summarize, contrast, analyze]
    rejected: *rejected_verbs
  interactive:   # interactive demos (future) — verify via guided completion
    valid: [navigate, interact, follow, demonstrate, observe, complete,
            select, submit, verify]
    rejected: *rejected_verbs
```

The `valid` list becomes the "such as" examples; the `rejected` list becomes the "avoid" examples. Both are hints in a sentence, not enumerated constraints.

#### Content modes

Verb hints are selected by **content mode**, mapped from content type in the YAML so a new content source is a data change, not a code change:

```yaml
content_modes:
  lab: hands_on
  demo: hands_on
  sandbox: hands_on
  architecture: read_through
  # interactive demos map to `interactive` when that source lands
```

**The mapping keys off `content_entities.content_type`, not the LLM's self-reported `content_type`.** Three reasons:

1. **Ordering.** The verb hint must be rendered *into* the prompt, before the model has responded. The LLM's `content_type` does not exist yet at that moment.
2. **Provenance.** `content_entities.content_type` is derived deterministically at catalog refresh (`database.py:552-556`) from the Babylon `category` field plus presence of a `showroom_url` — no LLM involved. OSSPA sets it to `architecture` from the CSV the same way.
3. **Stability.** The LLM's self-report can drift between analysis runs; it also emits `"workshop"`, a value no other part of the system uses.

Unmapped content types fall back to `hands_on` with a logged warning — never a hard failure.

#### Topics — open, with dedup

No enumerated list. No count cap. The LLM generates as many specific topic phrases as the content warrants. Current data shows ~11 topics per analyzed item on average (range 0–39), with higher counts correlating to multi-module content — working as intended.

**Post-analysis dedup** collapses spelling variants of the same topic on the same item before write. The rule is a **squash key**: casefold, strip all non-alphanumeric characters, compare for exact equality.

```text
"GitOps with ArgoCD"   → gitopswithargocd
"GitOps with Argo CD"  → gitopswithargocd   → collapse
```

Where two topics share a squash key, the **longest original form survives** (it is usually the better-spaced, more readable one), ties broken by first appearance.

> **Why not token overlap?** An earlier draft specified ">80% shared tokens", which fails on this spec's own canonical example. `{gitops, with, argocd}` vs `{gitops, with, argo, cd}` has a Jaccard similarity of 0.4 and containment of 0.67 — both below any sensible threshold, so the pair would not collapse. The squash key catches it exactly, has no threshold to tune, and is deterministic.

No cross-item dedup — topics are per-item. No flagging — topics are fully open.

> **`All` as a vertical:** `All` is a meta-value meaning "industry-agnostic" — the null case, not an actual industry. The normalizer treats an empty or missing vertical as `All`.

## Runtime

### Loading

```python
# src/api/rcars/services/vocabulary.py

@lru_cache(maxsize=1)
def load_vocabulary() -> Vocabulary: ...
```

- Reads `RCARS_VOCABULARY_PATH` (env var, mapped to `vocabulary_path` Pydantic setting; default: packaged `data/vocabulary.yaml`).
- ConfigMap mount path: `/opt/app-root/config/vocabulary.yaml` (set via Ansible `vocabulary_path` var on API + scan-worker + recommend-worker deployments — the Advisor query path runs on recommend-worker).
- Cached once per process via `@lru_cache`.

**Fail-fast validation at load.** A malformed vocabulary is caught at startup, not discovered as silent misbehavior:

| Check | On failure |
| ----- | ---------- |
| No alias maps to two different canonicals within a dimension | Raise |
| No alias collides with a canonical name of a different entry in the same dimension | Raise |
| `difficulty` contains exactly `beginner`, `intermediate`, `advanced` | Raise |
| `content_modes` values are all keys of `action_verbs` | Raise |
| No unknown top-level keys | Log warning |

Aliases may repeat *across* dimensions (`Edge` is both a solution and a platform) — lookups are per-dimension, so this is legal and not flagged.

**Update contract.** A ConfigMap change requires a **rolling restart** of API + scan-worker + recommend-worker to take effect. There is no reload endpoint.

> **Why no reload endpoint?** An earlier draft specified `POST /api/v1/admin/reload-vocabulary` calling `load_vocabulary.cache_clear()`. This cannot work: `@lru_cache` is per-process, so the call would clear the cache in exactly one uvicorn worker in one API replica — and never in scan-worker, which is the pod that actually runs analysis. An endpoint that appears to reload but silently does not is worse than no endpoint.

During a rollout, processes may briefly run different vocabulary versions. This is acceptable because normalization is idempotent — re-analysis corrects any drift.

### Prompt injection

A shared renderer builds the injected block for both analyzers; neither hardcodes vocabulary lists:

```python
def render_vocabulary_block(vocab: Vocabulary, content_type: str) -> str: ...
```

It emits two parts:

1. **Canonical product list** — with an instruction to prefer a listed name where one fits and only coin a new one when nothing matches.
2. **Action-verb hints** — selected via `content_modes[content_type]`, phrased as guidance (see above).

Injected into:

- `src/api/rcars/prompts/analyze_showroom.txt` (Babylon)
- `src/api/rcars/prompts/architecture_analyze.txt` (OSSPA — created by RHDPCD-28)

**Injection mechanics.** Two constraints in the existing code:

- `analyze_showroom.txt` contains literal `{` / `}` from its JSON output example, so `str.format()` cannot be used. Injection replaces an explicit sentinel token (`{{VOCABULARY}}`).
- `build_analysis_prompt()` (`analyzer.py:464`) splits the template by `.index("\n## Instructions\n")` and `.index("\n## Showroom Content\n")`, and only `template[:item_info_start]` plus `template[instructions_start:content_start]` reach the system prompt. **The sentinel must sit inside the `## Instructions` section** or the block is silently discarded.

Both prompts also gain a `recommender_audience` field in their JSON output schema.

### Post-analysis normalization

Deterministic code, running immediately after `parse_analysis_response()` inside the analyzer — **not** at each write site. `_sanitize_format_suitability` is currently applied inconsistently across `scan.py:112` and `cli.py:214,252`; normalization must not repeat that mistake.

```python
def normalize_analysis(analysis: dict, content_type: str) -> dict: ...
```

Driven by a module-level field map from analyzer output key → vocabulary dimension. Keys absent from a given analyzer's output are skipped, so one map serves both sources:

| Output key | Dimension |
| ---------- | --------- |
| `products` | `products` |
| `difficulty` | `difficulty` |
| `solution_areas` | `solutions` |
| `verticals` | `verticals` |
| `platforms` | `platforms` |

**Alias snap — a match ladder.** Most drift is spelling and formatting, which resolves without any human looking. Each value is tried against the rungs in order; the first hit wins:

| Rung | Rule | Catches |
| ---- | ---- | ------- |
| 1 | Exact match on canonical name or alias, case-insensitive | `RHACS`, `rhacs` |
| 2 | **Squash key** — casefold, strip all non-alphanumerics | `Openshift`/`OpenShift`, `on-prem`/`on prem`, `ArgoCD`/`Argo CD` |
| 3 | Strip known noise, then retry rungs 1–2 | trailing parentheticals (`OpenShift Container Platform (OCP)`), version suffixes (`RHEL 9`), a leading or missing `Red Hat ` |
| 4 | No match | Value stored verbatim; term recorded in the unknown-terms queue |

Rung 2 reuses the same squash key defined for topic dedup — one mechanism, two uses.

**Topic dedup** — squash key collapse, as specified above.

#### Unknown terms

**Vocabulary work never sets `enrichment_review_needed` and never writes to `review_reasons`.** That badge keeps whatever non-vocabulary meaning it already has, and vocabulary drift stays out of it.

The reason is that **the defect is in the vocabulary, not in the item.** An unknown product means the *list* is missing a term. Flagging 400 items for one missing alias produces 400 badges nobody browses for, to prompt a single YAML edit. So the unit of review is the **term**.

A rung-4 miss upserts one row per distinct term:

```sql
CREATE TABLE IF NOT EXISTS vocabulary_unknown_terms (
    dimension       TEXT NOT NULL,
    term            TEXT NOT NULL,
    occurrences     INTEGER NOT NULL DEFAULT 1,
    first_seen      TIMESTAMPTZ DEFAULT NOW(),
    last_seen       TIMESTAMPTZ DEFAULT NOW(),
    example_content_id TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',   -- pending | aliased | promoted | rejected
    resolved_to     TEXT,        -- canonical name, when status = 'aliased'
    resolved_by     TEXT,        -- admin email
    resolved_at     TIMESTAMPTZ,
    PRIMARY KEY (dimension, term)
);
```

Re-seeing a term bumps `occurrences` and `last_seen`. A term whose status is `rejected` is never re-surfaced. When a resolved term later appears in `vocabulary.yaml`, rung 1 or 2 matches it and the row goes dormant.

`topics`, `audience`, `recommender_audience`, and learning objectives are never recorded — they are open dimensions with no canonical list to be missing from.

### Advisor query expansion

`product-terms.yaml` is merged into `vocabulary.yaml` and deleted. `services/recommender/pipeline.py` changes:

- `_load_product_terms()` (line 33) and `_product_terms_cache` (line 30) are removed.
- `_expand_query_terms()` (line 53) builds its lookup from `load_vocabulary()` by inverting the product alias lists: each alias expands to its canonical product name.
- `tests/test_product_terms.py` is retargeted at the vocabulary loader.

**Merge requirements:**

1. **Coverage.** Every term in `product-terms.yaml` must survive. Several are not yet among the vocabulary's 42 products — `ARO`, `ROSA`, `RHEL`, `SNO`, `RHSSO`, `EDA`, `TAP`, `AMQ`, `CRW`, `RHBK`, `3scale`, `Service Mesh`, `Serverless`, `Dev Spaces`, `MaaS` — and must be added as products or aliases.
2. **One canonical spelling per product.** Resolve the drift documented in Problem. Vocabulary canonical names win (they carry the "Red Hat" prefix consistently).
3. **Recall terms preserved.** Query expansion deliberately widens recall beyond canonical naming — `GitOps` currently expands to `"Red Hat OpenShift GitOps ArgoCD Argo CD"`, which is a bag of search terms, not a name. Where a product needs extra recall terms beyond its aliases, it gets an optional `search_terms:` list on that product entry. Expansion appends aliases **and** `search_terms`; normalization ignores `search_terms` entirely.

### Admin vocabulary page

The unknown-terms queue is only useful if resolving a term is easy, so the UI ships with this work rather than after it. It is **admin-only and deliberately plain** — a table, three buttons, and a download. No new design language.

Route `/system/vocabulary`, inside the existing `auth.isAdmin` block in `App.tsx:61`, alongside `/system/roles`. Sidebar entry under the existing **System** section.

**Two panels:**

1. **Current vocabulary** — read-only. Dimensions, canonical names, aliases, as loaded. Confirms what the running processes actually have, which matters when a ConfigMap override is in play.
2. **Pending terms** — the `vocabulary_unknown_terms` rows with `status = 'pending'`, ranked by `occurrences` descending, with dimension, count, and one example item. Each row offers three actions:

| Action | Effect | Generated YAML |
| ------ | ------ | -------------- |
| **Alias to…** | Pick an existing canonical in that dimension | Term appended to that entry's `aliases` |
| **Promote** | Becomes a new canonical name in that dimension | New entry created |
| **Reject** | Not a real term; never surface again | Term appended to `ignored_terms` |

**Decisions are staged, not applied.** Resolving a term writes to the DB and changes nothing about how analysis behaves. A **Generate `vocabulary.yaml`** button emits the complete merged file — current vocabulary plus all staged decisions — for download, commit, PR, and deploy. The change takes effect on the next rollout.

> **Why staged rather than live?** The source of truth is a file in git. If the UI mutated a running ConfigMap, the change would be lost on the next deploy and the DB would become a second, divergent source of truth. Staging keeps git authoritative and every change reviewable in a PR. The cost is latency — an approved term does nothing until the file ships. That is acceptable: vocabulary drift is never urgent, and the value was already captured the moment the term was recorded.

**`ignored_terms` must round-trip.** Rejections have to survive regeneration, or a rejected term reappears in the queue on the next scan and the queue never drains. The YAML therefore carries:

```yaml
ignored_terms:
  products: [Kubernetes, Linux, YAML]
  solutions: []
```

The loader reads it; the generator writes it; rung 4 checks it before recording anything.

**Endpoints** (all `require_admin`, in `api/routes/admin.py`):

| Endpoint | Purpose |
| -------- | ------- |
| `GET /api/v1/admin/vocabulary` | Current loaded vocabulary |
| `GET /api/v1/admin/vocabulary/unknowns` | Queue, filterable by `status` and `dimension` |
| `PUT /api/v1/admin/vocabulary/unknowns/{dimension}/{term}` | Record a decision (`alias` / `promote` / `reject`) |
| `GET /api/v1/admin/vocabulary/generate` | Merged YAML as a downloadable file |

A `rcars vocab unknowns` CLI command prints the same queue, for use before the page exists and in scripted contexts.

## Configuration

| Setting | Default | Purpose |
| ------- | ------- | ------- |
| `vocabulary_path` | packaged `data/vocabulary.yaml` (ConfigMap mount overrides) | Controlled-vocabulary source |

Ansible mounts the file as a ConfigMap on API + scan-worker + recommend-worker so ops can hot-patch terms without an image rebuild.

## Schema Changes

Appended to `SCHEMA_SQL` in `src/api/rcars/db/database.py` as idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`:

```sql
ALTER TABLE showroom_analysis ADD COLUMN IF NOT EXISTS recommender_audience_json JSONB;
```

Plus the new `vocabulary_unknown_terms` table defined under "Unknown terms", added to `SCHEMA_SQL` as a `CREATE TABLE IF NOT EXISTS`.

`architecture_analysis.recommender_audience_json` is created by RHDPCD-28 and is not this spec's responsibility.

## Rollout

1. Ship the loader, normalization, prompt injection, and query-expansion merge.
2. **One-off Babylon re-scan** to apply normalization corpus-wide and populate `recommender_audience_json`.

The re-scan is in scope. Sibling propagation means the cost is one analysis per *distinct showroom* (same URL + resolved SHA), not per catalog item — materially fewer calls than the ~1,700 item count suggests. Without it, normalization would only reach items that happen to be re-scanned for unrelated reasons, and the new column would sit empty indefinitely.

OSSPA architecture items need no backfill — they are analyzed on arrival.

## Scope

### In scope

- Finalize `vocabulary.yaml` — products (merged with `product-terms.yaml`, with `search_terms`), solutions with TDP mapping, verticals, platforms, difficulty, action verbs by mode, `content_modes`.
- `vocabulary.py` loader + cache + fail-fast validation.
- Shared `render_vocabulary_block()`; products + verb hints injected into both analysis prompts.
- `normalize_analysis()` — dimension-driven match ladder + topic squash dedup, called once after parse.
- `vocabulary_unknown_terms` table + upsert on rung-4 misses; `ignored_terms` round-trip.
- Admin vocabulary page at `/system/vocabulary` — current list, pending queue, alias/promote/reject, YAML generator.
- Four admin endpoints + `rcars vocab unknowns` CLI.
- `recommender_audience_json` column on `showroom_analysis` + field in both prompts.
- Merge `product-terms.yaml` into the vocabulary; refactor `_expand_query_terms()`; delete the old file.
- ConfigMap mount via Ansible on all three deployments.
- One-off Babylon re-scan.
- Unit tests (see Testing).

### Out of scope

- **Verb validation, rejection, or flagging** — verbs are prompt guidance only. See "Action verbs".
- **A vocabulary reload endpoint** — ConfigMap change requires a rolling restart. See "Loading".
- **Solutions / verticals / platforms for Babylon** — architecture-only; extensible later via a column plus a field-map entry.
- **Editing existing vocabulary entries in the UI** — the admin page resolves *unknown* terms and generates the file. Renaming a canonical or removing an entry is a direct edit to `vocabulary.yaml` via PR.
- **Applying approvals at runtime** — decisions are staged and take effect on deploy. No live ConfigMap mutation, no DB overlay in the loader.
- **Consumers of `recommender_audience_json`** — the field is populated but nothing reads it yet. Role-aware Advisor routing is separate work.

## Relationship to Other Specs

- **RHDPCD-359 (Generalized Content Model)** — sketched the vocabulary contract (`vocabularies.yaml`, unknown-term review flags). This spec delivers that contract under the concrete path `data/vocabulary.yaml`, with one deliberate departure: 359's per-item review flags are replaced by a per-term admin queue, because the fix for an unknown term is an edit to the vocabulary, not to the item.
- **RHDPCD-28 (Portfolio Architecture Ingest)** — consumes the vocabulary. **No ordering dependency.** The only coupling is that `architecture_analyze.txt` is created by RHDPCD-28; if this spec ships first, it wires into `analyze_showroom.txt` and RHDPCD-28 adds the same `render_vocabulary_block()` call when it creates its prompt. RHDPCD-28 also owns `recommender_audience_json` on `architecture_analysis`.
- **RHDPCD-28's Browse filter section** claims solutions/verticals filters are "populated when vocabulary normalization runs" for Babylon items. That is inaccurate under this design and should be corrected there — those filters apply to architecture items only.

## Testing

| Test | Type | Assertion |
| ---- | ---- | --------- |
| Loader reads packaged default | Unit | Canonical product list non-empty |
| Loader honors `vocabulary_path` override | Unit | Mount/override path wins |
| Loader rejects duplicate alias within a dimension | Unit | Raises at load |
| Loader accepts same alias across dimensions | Unit | `Edge` valid as solution and platform |
| Loader rejects `content_modes` value with no verb list | Unit | Raises at load |
| Alias snap: `RHACS` → canonical product | Unit | Normalized before write |
| Alias snap: `FSI` → `Financial Services` vertical | Unit | Case-insensitive exact match |
| Ladder rung 2: squash match | Unit | `Openshift Container Platform` snaps to canonical |
| Ladder rung 3: noise strip | Unit | `OpenShift Container Platform (OCP)` and `RHEL 9` snap to canonical |
| Unknown product recorded, not dropped | Unit | Value stored verbatim; one `vocabulary_unknown_terms` row |
| Re-seeing a term bumps the counter | Unit | `occurrences` = 2, one row, `last_seen` advanced |
| Vocabulary never sets the review badge | Unit | `enrichment_review_needed` unchanged; `review_reasons` untouched |
| Rejected term never re-surfaces | Unit | `status = 'rejected'` → excluded from pending queue and not re-upserted |
| `ignored_terms` suppresses recording | Unit | Term listed in YAML → no row created |
| Generator round-trips | Unit | Generate → parse → load produces the same vocabulary plus staged decisions |
| Generator preserves rejections | Unit | Rejected term appears in `ignored_terms` in generated YAML |
| Admin endpoints reject non-admins | Integration | Curator token → 403 on all four |
| Empty vertical normalizes to `All` | Unit | Null case handled |
| Topic dedup, canonical case | Unit | "GitOps with ArgoCD" + "GitOps with Argo CD" → one, longer form survives |
| Topic count not capped | Unit | Item with 20+ legitimate topics keeps all |
| Learning objectives untouched by normalization | Unit | LO list identical before and after; shape unchanged |
| No verb ever produces a review reason | Unit | LO using `understand` yields no flag |
| Products injected into prompt | Unit | Rendered prompt contains canonical product names |
| Verb hints selected by content mode | Unit | `lab` → hands-on verbs; `architecture` → read-through verbs |
| Unmapped content type falls back | Unit | Unknown type → hands-on hints, warning logged |
| Solutions NOT injected into prompt | Unit | Rendered prompt does not contain solution list |
| Sentinel survives prompt split | Unit | Vocabulary block present in the **system** half of `build_analysis_prompt()` output |
| Query expansion reads vocabulary | Unit | `RHACS` expands to canonical name via `load_vocabulary()` |
| Query expansion covers migrated terms | Unit | Every acronym/synonym from old `product-terms.yaml` still expands |
| `search_terms` widen expansion only | Unit | Present in expanded query; ignored by `normalize_analysis()` |

## Next Steps

1. **Review and approve this spec.**
2. **Write implementation plan** — loader + validation, prompt injection, normalization, query-expansion merge, `recommender_audience_json` column, ConfigMap, tests, re-scan.
3. **Sequence the Babylon re-scan** — confirm distinct-showroom count and LLM cost before running.
