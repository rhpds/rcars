# Controlled Vocabulary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a single source-agnostic controlled vocabulary that normalizes product names and stable dimensions across analysis and Advisor query expansion, with an admin queue for unknown terms.

**Architecture:** One version-controlled YAML file (`src/api/rcars/data/vocabulary.yaml`) is loaded once per process by a cached loader with fail-fast validation. Products and action-verb hints are rendered into analysis prompts; every other dimension is normalized after the LLM responds via a deterministic four-rung match ladder. Unknown terms are recorded once per term in a DB queue and resolved by an admin, who then downloads a regenerated YAML to commit. The same vocabulary replaces `product-terms.yaml` for Advisor query expansion.

**Tech Stack:** Python 3.11, FastAPI, psycopg3 + PostgreSQL, Click CLI, arq workers, React 19 + PatternFly 6 (Vite/TypeScript), Ansible/Jinja2 for OpenShift manifests, pytest.

**Spec:** `docs/superpowers/specs/2026-08-10-controlled-vocabulary-design.md`

**Jira:** RHDPCD-507

## Global Constraints

Every task's requirements implicitly include this section.

- **Never set `enrichment_review_needed` and never write to `review_reasons`.** Vocabulary work must not touch either column, in any code path.
- **Nothing is ever dropped or rejected.** A value that does not match the vocabulary is stored verbatim; only the *term* is recorded for review.
- **No verb validation, rejection, or flagging.** Action verbs are prompt guidance only.
- **No vocabulary reload endpoint.** A ConfigMap change requires a rolling restart of API + scan-worker + recommend-worker.
- **`solutions`, `verticals`, and `platforms` are architecture-only in this phase.** The normalizer is dimension-driven so this is data, not code — but no Babylon prompt asks for them and no Babylon column stores them.
- **Only `products` and action-verb hints go into the prompt.** Solutions, verticals, platforms, difficulty, topics, and audience must never appear in a rendered prompt block.
- **Canonical product names carry the `Red Hat ` prefix consistently** where the official product name has it. Vocabulary canonical names win over `product-terms.yaml` spellings.
- **Content mode is keyed off `content_entities.content_type`** (`lab` / `demo` / `sandbox` / `architecture`), never the LLM's self-reported `content_type`. Unmapped types fall back to `hands_on` with a logged warning — never a hard failure.
- **ConfigMap mount path:** `/opt/app-root/config/vocabulary.yaml`.
- **Setting name:** `vocabulary_path` (env `RCARS_VOCABULARY_PATH`), empty string means "use the packaged file".
- **Commit messages** use the form `[RHDPCD-507] Sentence-case summary`. **Do not add `Co-Authored-By` trailers** — this repo does not use AI attribution in commits.
- **Tests** run from `src/api` with `source ~/.virtualenvs/rcars-v2/bin/activate`. PostgreSQL with pgvector on localhost:5432 and Redis on localhost:6379 must be running (`./dev-services.sh start`). Test database is `rcars_test`.
- **Do not push to any remote.** Commit locally only; the repo owner reviews and pushes.

## File Structure

**New — Python:**

| File | Responsibility |
| ---- | -------------- |
| `src/api/rcars/services/vocabulary/__init__.py` | Public API re-exports so `from rcars.services.vocabulary import load_vocabulary` works |
| `src/api/rcars/services/vocabulary/models.py` | `VocabEntry`, `Vocabulary` dataclasses, `squash_key()`, `VocabularyError` |
| `src/api/rcars/services/vocabulary/loader.py` | `load_vocabulary()` — path resolution, parse, fail-fast validation, `@lru_cache` |
| `src/api/rcars/services/vocabulary/normalize.py` | Match ladder, `normalize_analysis()`, topic dedup, field map |
| `src/api/rcars/services/vocabulary/render.py` | `render_vocabulary_block()` — the injected prompt text |
| `src/api/rcars/services/vocabulary/generate.py` | `generate_vocabulary_yaml()` — merged file for download |

**New — frontend:**

| File | Responsibility |
| ---- | -------------- |
| `src/frontend/src/pages/VocabularyPage.tsx` | Admin page: current vocabulary panel + pending-terms queue + generate button |

**New — tests:**

| File | Responsibility |
| ---- | -------------- |
| `src/api/tests/test_vocabulary.py` | Loader, validation, match ladder, topic dedup, render |
| `src/api/tests/test_vocabulary_db.py` | `vocabulary_unknown_terms` table + Database methods (needs live PG) |
| `src/api/tests/test_vocabulary_admin.py` | Four admin endpoints, role gating, generator round-trip |

**Modified:**

| File | Change |
| ---- | ------ |
| `src/api/rcars/data/vocabulary.yaml` | Finalize: `content_modes`, `ignored_terms`, `search_terms`, missing products |
| `src/api/rcars/data/product-terms.yaml` | **Deleted** in Task 6 |
| `src/api/rcars/config.py` | Add `vocabulary_path` setting |
| `src/api/rcars/db/database.py` | Schema additions + three unknown-term methods + `recommender_audience_json` in upsert |
| `src/api/rcars/services/analyzer.py` | Thread `entity_content_type`, inject vocabulary block, call `normalize_analysis()` |
| `src/api/rcars/prompts/analyze_showroom.txt` | `{{VOCABULARY}}` sentinel + `recommender_audience` output field |
| `src/api/rcars/workers/scan.py` | Pass `entity_content_type`, persist `recommender_audience_json` |
| `src/api/rcars/cli.py` | Same as scan.py, plus new `rcars vocab` group |
| `src/api/rcars/services/recommender/pipeline.py` | `_expand_query_terms()` reads the vocabulary |
| `src/api/rcars/api/routes/admin.py` | Four vocabulary endpoints |
| `src/api/rcars/api/schemas.py` | Response/request models for those endpoints |
| `src/api/tests/test_product_terms.py` | Retargeted at the vocabulary loader |
| `src/frontend/src/services/api.ts` | Four client methods + types |
| `src/frontend/src/App.tsx` | `/system/vocabulary` route inside the `auth.isAdmin` block |
| `src/frontend/src/components/RcarsSidebar.tsx` | Nav entry under System |
| `ansible/templates/manifests-infra.yaml.j2` | Vocabulary ConfigMap |
| `ansible/templates/manifests-app.yaml.j2` | Mount + `RCARS_VOCABULARY_PATH` on three deployments |

---

### Task 1: Vocabulary data file, loader, and fail-fast validation

**Files:**
- Modify: `src/api/rcars/data/vocabulary.yaml`
- Create: `src/api/rcars/services/vocabulary/__init__.py`
- Create: `src/api/rcars/services/vocabulary/models.py`
- Create: `src/api/rcars/services/vocabulary/loader.py`
- Modify: `src/api/rcars/config.py`
- Test: `src/api/tests/test_vocabulary.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `squash_key(value: str) -> str`
  - `class VocabularyError(Exception)`
  - `class VocabEntry` — frozen dataclass, fields `name: str`, `aliases: tuple[str, ...]`, `search_terms: tuple[str, ...]`, `is_tdp: bool`
  - `class Vocabulary` — frozen dataclass, fields `dimensions: dict[str, tuple[VocabEntry, ...]]`, `action_verbs: dict[str, dict[str, tuple[str, ...]]]`, `content_modes: dict[str, str]`, `ignored_terms: dict[str, frozenset[str]]` (squash keys), `ignored_originals: dict[str, tuple[str, ...]]` (source spellings), `exact_lookup: dict[str, dict[str, str]]`, `squash_lookup: dict[str, dict[str, str]]`; methods `entries(dimension) -> tuple[VocabEntry, ...]`, `canonical_names(dimension) -> list[str]`, `is_ignored(dimension, term) -> bool`
  - `load_vocabulary() -> Vocabulary` (`@lru_cache(maxsize=1)`, exposes `.cache_clear()`)
  - `DIMENSIONS: tuple[str, ...] = ("products", "solutions", "verticals", "platforms", "difficulty")`
  - `Settings.vocabulary_path: str`

- [ ] **Step 1: Finalize `vocabulary.yaml` — add the three missing top-level sections**

Append these three blocks to the end of `src/api/rcars/data/vocabulary.yaml` (after the `action_verbs` block):

```yaml
# ---------------------------------------------------------------------------
# content_modes — maps content_entities.content_type to an action_verbs mode.
#
# Keys off content_entities.content_type (derived deterministically at catalog
# refresh from Babylon category + showroom_url presence; set to 'architecture'
# by OSSPA ingest), NOT the LLM's self-reported content_type — the verb hint is
# rendered into the prompt before the model has responded.
#
# Unmapped content types fall back to hands_on with a logged warning.
# ---------------------------------------------------------------------------
content_modes:
  lab: hands_on
  demo: hands_on
  sandbox: hands_on
  architecture: read_through

# ---------------------------------------------------------------------------
# ignored_terms — terms an admin has rejected via the vocabulary queue.
#
# These are real strings the LLM emits that are NOT products (or solutions,
# etc.) and never will be. Listing them here stops them being re-recorded in
# the unknown-terms queue on every scan. Round-trips through the generator.
# ---------------------------------------------------------------------------
ignored_terms:
  products: [Kubernetes, Linux, YAML, Git, Docker, Prometheus, Grafana]
  solutions: []
  verticals: []
  platforms: []
  difficulty: []
```

- [ ] **Step 2: Finalize `vocabulary.yaml` — close the `product-terms.yaml` coverage gaps**

Every term in `product-terms.yaml` must survive the merge in Task 6. Two products are missing entirely and several entries need `search_terms` to preserve the recall the old synonyms provided.

Add these two new entries to the `products:` list, immediately before the `# NOTE: OSSPA "Consulting"...` comment:

```yaml
  - name: Red Hat Trusted Application Pipeline
    aliases: [TAP, Trusted Application Pipeline]
  - name: Models as a Service
    aliases: [MaaS]
    search_terms: [model serving, LLM inference]
```

Then add `search_terms` to the existing entries below. `search_terms` widen Advisor query expansion only — the normalizer ignores them entirely. Edit each entry in place so it reads exactly as shown:

```yaml
  - name: Red Hat OpenShift GitOps
    aliases: [GitOps, ArgoCD, Argo CD]
    search_terms: [ArgoCD, Argo CD]
  - name: Red Hat OpenShift Pipelines
    aliases: [Pipelines, Tekton]
    search_terms: [Tekton]
  - name: Red Hat OpenShift Virtualization
    aliases: [OpenShift Virtualization, CNV, KubeVirt]
    search_terms: [KubeVirt, virtual machines]
  - name: Red Hat OpenShift Service Mesh
    aliases: [Service Mesh, OSSM]
    search_terms: [Istio]
  - name: Red Hat OpenShift Serverless
    aliases: [Serverless, Knative]
    search_terms: [Knative]
  - name: Red Hat Quay
    aliases: [Quay]
    search_terms: [container registry]
```

Two spellings drift between the files and the vocabulary wins, per the spec's merge requirements: `RHSSO` stays an alias of `Red Hat build of Keycloak` (not the retired "Red Hat Single Sign-On" name), and `CRW` stays an alias of `Red Hat OpenShift Dev Spaces` (not "Red Hat CodeReady Workspaces"). Both are already correct in the file — leave them.

- [ ] **Step 3: Fix the stale topic-dedup comment in `vocabulary.yaml`**

The `topics` comment block still describes the rejected token-overlap rule. Replace the line

```yaml
# Post-analysis: fuzzy dedup collapses near-identical topics on the same item
# (case-fold + token overlap >80% → keep the longer form). No flagging.
```

with

```yaml
# Post-analysis: squash-key dedup collapses spelling variants of the same topic
# on the same item (casefold + strip non-alphanumerics; longest original form
# survives, ties broken by first appearance). No flagging.
```

- [ ] **Step 4: Commit the data file**

```bash
git add src/api/rcars/data/vocabulary.yaml
git commit -m "[RHDPCD-507] Finalize vocabulary.yaml content modes, ignored terms, search terms"
```

- [ ] **Step 5: Write the failing loader tests**

Create `src/api/tests/test_vocabulary.py`:

```python
"""Tests for the controlled vocabulary loader, normalizer, and prompt renderer."""

from __future__ import annotations

import textwrap

import pytest

from rcars.services.vocabulary import (
    DIMENSIONS,
    VocabularyError,
    load_vocabulary,
    squash_key,
)


@pytest.fixture(autouse=True)
def clear_vocabulary_cache():
    """load_vocabulary is process-cached; clear it around every test."""
    load_vocabulary.cache_clear()
    yield
    load_vocabulary.cache_clear()


def write_vocab(tmp_path, body: str):
    path = tmp_path / "vocabulary.yaml"
    path.write_text(textwrap.dedent(body))
    return path


class TestSquashKey:
    def test_strips_case_and_punctuation(self):
        assert squash_key("GitOps with Argo CD") == "gitopswithargocd"
        assert squash_key("GitOps with ArgoCD") == "gitopswithargocd"
        assert squash_key("on-prem") == "onprem"
        assert squash_key("On Prem") == "onprem"


class TestLoadPackagedDefault:
    def test_reads_packaged_default(self):
        vocab = load_vocabulary()
        assert len(vocab.canonical_names("products")) > 0
        assert "Red Hat OpenShift Container Platform" in vocab.canonical_names("products")

    def test_all_dimensions_present(self):
        vocab = load_vocabulary()
        for dimension in DIMENSIONS:
            assert vocab.entries(dimension), f"{dimension} is empty"

    def test_content_modes_loaded(self):
        vocab = load_vocabulary()
        assert vocab.content_modes["lab"] == "hands_on"
        assert vocab.content_modes["architecture"] == "read_through"

    def test_ignored_terms_loaded(self):
        vocab = load_vocabulary()
        assert vocab.is_ignored("products", "Kubernetes")
        assert vocab.is_ignored("products", "kubernetes")  # case-insensitive
        assert not vocab.is_ignored("products", "Red Hat Quay")

    def test_ignored_originals_keep_source_spelling(self):
        vocab = load_vocabulary()
        assert "Kubernetes" in vocab.ignored_originals["products"]
        assert vocab.ignored_originals["solutions"] == ()

    def test_search_terms_kept_separate_from_aliases(self):
        vocab = load_vocabulary()
        gitops = next(e for e in vocab.entries("products") if e.name == "Red Hat OpenShift GitOps")
        assert "ArgoCD" in gitops.aliases
        assert "Argo CD" in gitops.search_terms

    def test_is_tdp_flag(self):
        vocab = load_vocabulary()
        solutions = {e.name: e.is_tdp for e in vocab.entries("solutions")}
        assert solutions["Application Platform"] is True
        assert solutions["Integration"] is False


class TestPathOverride:
    def test_override_path_wins(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, """
            products:
              - name: Only Product
                aliases: [OP]
            solutions: []
            verticals: []
            platforms: []
            difficulty:
              - name: beginner
              - name: intermediate
              - name: advanced
            action_verbs:
              hands_on:
                valid: [deploy]
                rejected: [understand]
            content_modes:
              lab: hands_on
        """)
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        vocab = load_vocabulary()
        assert vocab.canonical_names("products") == ["Only Product"]


class TestValidation:
    """Every document is built from one helper so indentation stays uniform —
    write_vocab dedents the whole string, so both halves must share a prefix.
    """

    def _doc(self, dimensions: str, content_modes: str = "              lab: hands_on") -> str:
        return f"""
            difficulty:
              - name: beginner
              - name: intermediate
              - name: advanced
            action_verbs:
              hands_on:
                valid: [deploy]
                rejected: [understand]
              read_through:
                valid: [compare]
                rejected: [understand]
            content_modes:
{content_modes}
{dimensions}
        """

    def test_rejects_duplicate_alias_within_dimension(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, self._doc("""
            products:
              - name: Product A
                aliases: [SHARED]
              - name: Product B
                aliases: [SHARED]
        """))
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        with pytest.raises(VocabularyError, match="SHARED"):
            load_vocabulary()

    def test_rejects_alias_colliding_with_other_canonical(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, self._doc("""
            products:
              - name: Product A
                aliases: []
              - name: Product B
                aliases: [Product A]
        """))
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        with pytest.raises(VocabularyError, match="Product A"):
            load_vocabulary()

    def test_accepts_same_alias_across_dimensions(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, self._doc("""
            products: []
            solutions:
              - name: Edge
                aliases: [EdgeComputing]
            platforms:
              - name: Edge
                aliases: [EdgeComputing]
        """))
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        vocab = load_vocabulary()
        assert "Edge" in vocab.canonical_names("solutions")
        assert "Edge" in vocab.canonical_names("platforms")

    def test_rejects_wrong_difficulty_set(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, """
            products: []
            difficulty:
              - name: easy
              - name: hard
            action_verbs:
              hands_on:
                valid: [deploy]
                rejected: [understand]
            content_modes:
              lab: hands_on
        """)
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        with pytest.raises(VocabularyError, match="difficulty"):
            load_vocabulary()

    def test_rejects_content_mode_with_no_verb_list(self, tmp_path, monkeypatch):
        path = write_vocab(
            tmp_path,
            self._doc("            products: []", content_modes="              lab: nonexistent_mode"),
        )
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        with pytest.raises(VocabularyError, match="nonexistent_mode"):
            load_vocabulary()

    def test_unknown_top_level_key_warns_only(self, tmp_path, monkeypatch, caplog):
        path = write_vocab(tmp_path, self._doc("""
            products: []
            mystery_section:
              - anything
        """))
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        vocab = load_vocabulary()
        assert vocab is not None
        assert "mystery_section" in caplog.text
```

- [ ] **Step 6: Run the tests to verify they fail**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'rcars.services.vocabulary'`.

- [ ] **Step 7: Write `models.py`**

Create `src/api/rcars/services/vocabulary/models.py`:

```python
"""Controlled vocabulary data model.

The vocabulary is a source-agnostic list of canonical names plus their aliases,
used in two directions: rendered into analysis prompts (products only) and used
to snap LLM output back to canonical form after the fact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Dimensions that carry canonical entries. Order is stable for rendering and
# generation. Adding a dimension here plus a block in vocabulary.yaml is all
# that is required — the normalizer is driven by this tuple and FIELD_MAP.
DIMENSIONS: tuple[str, ...] = (
    "products",
    "solutions",
    "verticals",
    "platforms",
    "difficulty",
)

DIFFICULTY_LEVELS: frozenset[str] = frozenset({"beginner", "intermediate", "advanced"})

TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    set(DIMENSIONS) | {"action_verbs", "content_modes", "ignored_terms"}
)

DEFAULT_CONTENT_MODE = "hands_on"

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


class VocabularyError(Exception):
    """Raised when vocabulary.yaml is malformed. Fail fast at load."""


def squash_key(value: str) -> str:
    """Casefold and strip every non-alphanumeric character.

    One mechanism, two uses: rung 2 of the alias match ladder, and topic dedup.
    'GitOps with Argo CD' and 'GitOps with ArgoCD' both squash to the same key.
    """
    return _NON_ALNUM.sub("", (value or "").casefold())


@dataclass(frozen=True)
class VocabEntry:
    """One canonical name and everything that should resolve to it.

    aliases      — normalize to this name AND widen query expansion
    search_terms — widen query expansion ONLY; the normalizer ignores them
    is_tdp       — informational: this solution is a Red Hat Technology
                   Decision Point. Does not affect storage or normalization.
    """

    name: str
    aliases: tuple[str, ...] = ()
    search_terms: tuple[str, ...] = ()
    is_tdp: bool = False


@dataclass(frozen=True)
class Vocabulary:
    dimensions: dict[str, tuple[VocabEntry, ...]] = field(default_factory=dict)
    action_verbs: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)
    content_modes: dict[str, str] = field(default_factory=dict)
    # Squash keys, for O(1) suppression checks at rung 4.
    ignored_terms: dict[str, frozenset[str]] = field(default_factory=dict)
    # The same terms in their source spelling, for display and regeneration.
    ignored_originals: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # dimension -> casefolded name/alias -> canonical name
    exact_lookup: dict[str, dict[str, str]] = field(default_factory=dict)
    # dimension -> squash key -> canonical name
    squash_lookup: dict[str, dict[str, str]] = field(default_factory=dict)

    def entries(self, dimension: str) -> tuple[VocabEntry, ...]:
        return self.dimensions.get(dimension, ())

    def canonical_names(self, dimension: str) -> list[str]:
        return [e.name for e in self.entries(dimension)]

    def is_ignored(self, dimension: str, term: str) -> bool:
        """True when an admin has rejected this term for this dimension."""
        return squash_key(term) in self.ignored_terms.get(dimension, frozenset())
```

- [ ] **Step 8: Write `loader.py`**

Create `src/api/rcars/services/vocabulary/loader.py`:

```python
"""Vocabulary loading, path resolution, and fail-fast validation.

Cached once per process. A ConfigMap change requires a rolling restart of the
API, scan-worker, and recommend-worker — there is deliberately no reload
endpoint, because @lru_cache is per-process and an endpoint could only ever
clear one uvicorn worker in one API replica.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from importlib.resources import files as _pkg_files
from pathlib import Path
from typing import Any

import yaml

from rcars.services.vocabulary.models import (
    DIFFICULTY_LEVELS,
    DIMENSIONS,
    TOP_LEVEL_KEYS,
    VocabEntry,
    Vocabulary,
    VocabularyError,
    squash_key,
)

log = logging.getLogger(__name__)


def _resolve_path() -> Path:
    """Settings override wins; otherwise use the file packaged in rcars.data."""
    from rcars.config import Settings

    configured = (Settings().vocabulary_path or "").strip()
    if configured:
        return Path(configured)
    return Path(str(_pkg_files("rcars.data").joinpath("vocabulary.yaml")))


def _as_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(str(v) for v in value)


def _parse_entries(dimension: str, raw: Any) -> tuple[VocabEntry, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise VocabularyError(f"{dimension}: expected a list, got {type(raw).__name__}")

    entries = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("name"):
            raise VocabularyError(f"{dimension}: every entry needs a 'name' (got {item!r})")
        entries.append(
            VocabEntry(
                name=str(item["name"]),
                aliases=_as_tuple(item.get("aliases")),
                search_terms=_as_tuple(item.get("search_terms")),
                is_tdp=bool(item.get("is_tdp", False)),
            )
        )
    return tuple(entries)


def _build_lookups(
    dimension: str, entries: tuple[VocabEntry, ...]
) -> tuple[dict[str, str], dict[str, str]]:
    """Build exact (casefold) and squash lookups, validating collisions.

    Aliases may repeat ACROSS dimensions ('Edge' is both a solution and a
    platform) — lookups are per-dimension, so that is legal.
    """
    canonicals = {e.name.casefold(): e.name for e in entries}
    exact: dict[str, str] = dict(canonicals)
    squash: dict[str, str] = {squash_key(e.name): e.name for e in entries}

    for entry in entries:
        for alias in entry.aliases:
            key = alias.casefold()
            owner = canonicals.get(key)
            if owner and owner != entry.name:
                raise VocabularyError(
                    f"{dimension}: alias '{alias}' on '{entry.name}' collides with "
                    f"the canonical name '{owner}'"
                )
            existing = exact.get(key)
            if existing and existing != entry.name:
                raise VocabularyError(
                    f"{dimension}: alias '{alias}' maps to both '{existing}' and '{entry.name}'"
                )
            exact[key] = entry.name
            squash.setdefault(squash_key(alias), entry.name)

    return exact, squash


def _validate(data: dict[str, Any], vocab: Vocabulary) -> None:
    unknown = set(data) - TOP_LEVEL_KEYS
    if unknown:
        log.warning("vocabulary: ignoring unknown top-level keys: %s", ", ".join(sorted(unknown)))

    difficulty = {e.name.casefold() for e in vocab.entries("difficulty")}
    if difficulty != DIFFICULTY_LEVELS:
        raise VocabularyError(
            f"difficulty must contain exactly {sorted(DIFFICULTY_LEVELS)}, got {sorted(difficulty)}"
        )

    for content_type, mode in vocab.content_modes.items():
        if mode not in vocab.action_verbs:
            raise VocabularyError(
                f"content_modes['{content_type}'] = '{mode}' has no matching action_verbs entry"
            )


@lru_cache(maxsize=1)
def load_vocabulary() -> Vocabulary:
    """Load, validate, and cache the controlled vocabulary for this process."""
    path = _resolve_path()
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except FileNotFoundError as exc:
        raise VocabularyError(f"vocabulary file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise VocabularyError(f"vocabulary file is not valid YAML: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise VocabularyError(f"vocabulary file must be a mapping: {path}")

    dimensions: dict[str, tuple[VocabEntry, ...]] = {}
    exact_lookup: dict[str, dict[str, str]] = {}
    squash_lookup: dict[str, dict[str, str]] = {}
    for dimension in DIMENSIONS:
        entries = _parse_entries(dimension, data.get(dimension))
        dimensions[dimension] = entries
        exact_lookup[dimension], squash_lookup[dimension] = _build_lookups(dimension, entries)

    action_verbs = {
        mode: {
            "valid": _as_tuple((lists or {}).get("valid")),
            "rejected": _as_tuple((lists or {}).get("rejected")),
        }
        for mode, lists in (data.get("action_verbs") or {}).items()
    }

    ignored_raw = data.get("ignored_terms") or {}
    ignored_originals = {
        dimension: _as_tuple(ignored_raw.get(dimension)) for dimension in DIMENSIONS
    }
    ignored_terms = {
        dimension: frozenset(squash_key(t) for t in terms)
        for dimension, terms in ignored_originals.items()
    }

    vocab = Vocabulary(
        dimensions=dimensions,
        action_verbs=action_verbs,
        content_modes={str(k): str(v) for k, v in (data.get("content_modes") or {}).items()},
        ignored_terms=ignored_terms,
        ignored_originals=ignored_originals,
        exact_lookup=exact_lookup,
        squash_lookup=squash_lookup,
    )
    _validate(data, vocab)

    log.info(
        "vocabulary_loaded path=%s products=%d solutions=%d verticals=%d platforms=%d modes=%d",
        path,
        len(vocab.entries("products")),
        len(vocab.entries("solutions")),
        len(vocab.entries("verticals")),
        len(vocab.entries("platforms")),
        len(vocab.content_modes),
    )
    return vocab
```

- [ ] **Step 9: Write `__init__.py`**

Create `src/api/rcars/services/vocabulary/__init__.py`. Keep it a package with a flat public API so `from rcars.services.vocabulary import load_vocabulary` reads the same as the spec's `services/vocabulary.py`:

```python
"""Controlled vocabulary — one list, two consumers (analysis + query expansion)."""

from rcars.services.vocabulary.loader import load_vocabulary
from rcars.services.vocabulary.models import (
    DEFAULT_CONTENT_MODE,
    DIFFICULTY_LEVELS,
    DIMENSIONS,
    VocabEntry,
    Vocabulary,
    VocabularyError,
    squash_key,
)

__all__ = [
    "DEFAULT_CONTENT_MODE",
    "DIFFICULTY_LEVELS",
    "DIMENSIONS",
    "VocabEntry",
    "Vocabulary",
    "VocabularyError",
    "load_vocabulary",
    "squash_key",
]
```

- [ ] **Step 10: Add the `vocabulary_path` setting**

In `src/api/rcars/config.py`, find the `# Content overlap` comment block (around line 97) and insert this block immediately above it:

```python
    # Controlled vocabulary (RHDPCD-507)
    # Empty → the file packaged in rcars/data/vocabulary.yaml. Ansible mounts a
    # ConfigMap at /opt/app-root/config/vocabulary.yaml and sets this so ops can
    # patch terms without an image rebuild. A change needs a rolling restart.
    vocabulary_path: str = ""
```

- [ ] **Step 11: Run the tests to verify they pass**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary.py -v
```

Expected: PASS (all classes in the file so far).

- [ ] **Step 12: Commit**

```bash
git add src/api/rcars/services/vocabulary/ src/api/rcars/config.py src/api/tests/test_vocabulary.py
git commit -m "[RHDPCD-507] Add vocabulary loader with fail-fast validation"
```

---

### Task 2: Match ladder, topic dedup, and the pure normalizer

**Files:**
- Create: `src/api/rcars/services/vocabulary/normalize.py`
- Modify: `src/api/rcars/services/vocabulary/__init__.py`
- Test: `src/api/tests/test_vocabulary.py` (append)

**Interfaces:**
- Consumes: `load_vocabulary()`, `Vocabulary`, `squash_key()`, `DEFAULT_CONTENT_MODE` from Task 1.
- Produces:
  - `FIELD_MAP: dict[str, str]` — analyzer output key → vocabulary dimension
  - `snap_term(vocab: Vocabulary, dimension: str, value: str) -> tuple[str, bool]` — returns `(canonical_or_verbatim, matched)`
  - `dedup_topics(topics: list[str]) -> list[str]`
  - `normalize_analysis(analysis: dict, content_type: str, db=None, content_id: str | None = None) -> dict`

**Deviation from spec, deliberate:** the spec writes the signature as `normalize_analysis(analysis, content_type) -> dict`. Two optional keyword arguments are added so the function is pure and unit-testable without a database, and records unknown terms when a database is supplied (Task 3 wires that up). Behaviour with `db=None` is exactly the spec's.

- [ ] **Step 1: Write the failing normalizer tests**

Append to `src/api/tests/test_vocabulary.py`:

```python
from rcars.services.vocabulary import dedup_topics, normalize_analysis, snap_term


class TestMatchLadder:
    def test_rung1_exact_alias_case_insensitive(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "RHACS") == ("Red Hat Advanced Cluster Security", True)
        assert snap_term(vocab, "products", "rhacs") == ("Red Hat Advanced Cluster Security", True)

    def test_rung1_vertical_alias(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "verticals", "FSI") == ("Financial Services", True)

    def test_rung2_squash_match(self):
        """Punctuation and spacing differences resolve without a human."""
        vocab = load_vocabulary()
        # 'on-prem' is an alias; 'on prem' differs only by punctuation.
        assert snap_term(vocab, "platforms", "on prem") == ("On-Premise", True)
        # Hyphen inside the canonical name — casefold-exact misses, squash hits.
        assert snap_term(vocab, "products", "Red-Hat Quay") == ("Red Hat Quay", True)

    def test_casing_and_spacing_variants_all_resolve(self):
        """The spec's worked examples, wherever on the ladder they land."""
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "Openshift Container Platform")[0] == (
            "Red Hat OpenShift Container Platform"
        )
        assert snap_term(vocab, "platforms", "On-Premises") == ("On-Premise", True)
        assert snap_term(vocab, "products", "Argo CD")[0] == "Red Hat OpenShift GitOps"

    def test_rung3_trailing_parenthetical(self):
        vocab = load_vocabulary()
        result, matched = snap_term(vocab, "products", "OpenShift Container Platform (OCP)")
        assert (result, matched) == ("Red Hat OpenShift Container Platform", True)

    def test_rung3_version_suffix(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "RHEL 9") == ("Red Hat Enterprise Linux", True)
        assert snap_term(vocab, "products", "OpenShift 4.16")[0] == (
            "Red Hat OpenShift Container Platform"
        )

    def test_rung3_missing_red_hat_prefix(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "Quay") == ("Red Hat Quay", True)

    def test_rung3_extra_red_hat_prefix(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "Red Hat Satellite") == ("Red Hat Satellite", True)
        assert snap_term(vocab, "platforms", "Red Hat AWS") == ("AWS", True)

    def test_rung4_no_match_returns_verbatim(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "Wombat Server 3000") == ("Wombat Server 3000", False)

    def test_search_terms_do_not_snap(self):
        """search_terms widen query expansion only — the normalizer ignores them."""
        vocab = load_vocabulary()
        # 'container registry' is a Quay search_term, not an alias.
        assert snap_term(vocab, "products", "container registry")[1] is False


class TestTopicDedup:
    def test_collapses_spelling_variants_keeping_longest(self):
        assert dedup_topics(["GitOps with ArgoCD", "GitOps with Argo CD"]) == [
            "GitOps with Argo CD"
        ]

    def test_tie_broken_by_first_appearance(self):
        assert dedup_topics(["ArgoCD", "argocd"]) == ["ArgoCD"]

    def test_preserves_order_of_survivors(self):
        assert dedup_topics(["Pipelines", "GitOps", "pipelines"]) == ["Pipelines", "GitOps"]

    def test_no_count_cap(self):
        topics = [f"topic number {i}" for i in range(25)]
        assert len(dedup_topics(topics)) == 25

    def test_drops_empty_values(self):
        assert dedup_topics(["GitOps", "", None]) == ["GitOps"]


class TestNormalizeAnalysis:
    def test_snaps_products_in_place(self):
        out = normalize_analysis({"products": ["RHACS", "OCP"]}, "lab")
        assert out["products"] == [
            "Red Hat Advanced Cluster Security",
            "Red Hat OpenShift Container Platform",
        ]

    def test_unknown_product_stored_verbatim(self):
        out = normalize_analysis({"products": ["Wombat Server 3000"]}, "lab")
        assert out["products"] == ["Wombat Server 3000"]

    def test_snaps_difficulty_scalar(self):
        assert normalize_analysis({"difficulty": "Introductory"}, "lab")["difficulty"] == "beginner"

    def test_empty_vertical_normalizes_to_all(self):
        assert normalize_analysis({"verticals": []}, "architecture")["verticals"] == ["All"]
        assert normalize_analysis({"verticals": None}, "architecture")["verticals"] == ["All"]

    def test_missing_vertical_key_is_not_invented(self):
        """Keys absent from an analyzer's output are skipped — one map, two sources."""
        assert "verticals" not in normalize_analysis({"products": ["OCP"]}, "lab")

    def test_dedups_topics(self):
        out = normalize_analysis({"topics": ["GitOps with ArgoCD", "GitOps with Argo CD"]}, "lab")
        assert out["topics"] == ["GitOps with Argo CD"]

    def test_learning_objectives_untouched(self):
        objectives = {
            "stated": ["Understand how GitOps works"],
            "inferred": ["Deploy an application with Argo CD"],
        }
        out = normalize_analysis({"learning_objectives": objectives}, "lab")
        assert out["learning_objectives"] == objectives

    def test_no_verb_ever_produces_a_review_reason(self):
        out = normalize_analysis(
            {"learning_objectives": {"stated": ["Understand containers"]}, "products": ["OCP"]},
            "lab",
        )
        assert "review_reasons" not in out
        assert "enrichment_review_needed" not in out

    def test_does_not_mutate_input(self):
        original = {"products": ["RHACS"]}
        normalize_analysis(original, "lab")
        assert original == {"products": ["RHACS"]}

    def test_unrelated_keys_pass_through(self):
        out = normalize_analysis({"summary": "hello", "estimated_duration_min": 60}, "lab")
        assert out["summary"] == "hello"
        assert out["estimated_duration_min"] == 60
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary.py -v
```

Expected: `ImportError: cannot import name 'dedup_topics' from 'rcars.services.vocabulary'`.

- [ ] **Step 3: Write `normalize.py`**

Create `src/api/rcars/services/vocabulary/normalize.py`:

```python
"""Post-analysis normalization — deterministic, runs once after parse.

Nothing here is a quality gate. Values that do not match the vocabulary are
stored verbatim; only the unmatched TERM is recorded, once, for admin review.
This module never sets enrichment_review_needed and never writes review_reasons.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from rcars.services.vocabulary.loader import load_vocabulary
from rcars.services.vocabulary.models import Vocabulary, squash_key

log = logging.getLogger(__name__)

# Analyzer output key -> vocabulary dimension. Keys absent from a given
# analyzer's output are skipped, so one map serves Babylon and OSSPA.
# Extending a dimension to a new source is an entry here, not new code.
FIELD_MAP: dict[str, str] = {
    "products": "products",
    "difficulty": "difficulty",
    "solution_areas": "solutions",
    "verticals": "verticals",
    "platforms": "platforms",
}

# Dimensions whose empty/missing value has a meaningful default.
DIMENSION_DEFAULTS: dict[str, str] = {"verticals": "All"}

# Scalar (non-list) output keys.
SCALAR_KEYS: frozenset[str] = frozenset({"difficulty"})

_TRAILING_PARENS = re.compile(r"\s*\([^()]*\)\s*$")
_VERSION_SUFFIX = re.compile(r"\s+v?\d+(?:\.\d+)*\s*$")
_RED_HAT_PREFIX = re.compile(r"^red\s+hat\s+", re.IGNORECASE)


def _rungs_1_2(vocab: Vocabulary, dimension: str, value: str) -> str | None:
    """Rung 1: exact match on canonical or alias, case-insensitive.
    Rung 2: squash key — casefold and strip all non-alphanumerics.
    """
    hit = vocab.exact_lookup.get(dimension, {}).get(value.casefold())
    if hit:
        return hit
    return vocab.squash_lookup.get(dimension, {}).get(squash_key(value))


def _noise_variants(value: str) -> list[str]:
    """Rung 3 candidates: strip known noise, then retry rungs 1-2 on each."""
    variants: list[str] = []
    stripped = _TRAILING_PARENS.sub("", value).strip()
    if stripped and stripped != value:
        variants.append(stripped)

    for base in [stripped or value]:
        versionless = _VERSION_SUFFIX.sub("", base).strip()
        if versionless and versionless != base:
            variants.append(versionless)

    # A leading or missing "Red Hat " — try it both ways for every variant so far.
    for base in [value, *variants]:
        if _RED_HAT_PREFIX.match(base):
            variants.append(_RED_HAT_PREFIX.sub("", base).strip())
        else:
            variants.append(f"Red Hat {base}".strip())

    seen: set[str] = set()
    ordered: list[str] = []
    for v in variants:
        if v and v != value and v not in seen:
            seen.add(v)
            ordered.append(v)
    return ordered


def snap_term(vocab: Vocabulary, dimension: str, value: str) -> tuple[str, bool]:
    """Snap one value to its canonical form.

    Returns (result, matched). On a miss the ORIGINAL value is returned — the
    caller stores it verbatim and records the term for review.
    """
    if not value or not str(value).strip():
        return value, False
    value = str(value).strip()

    hit = _rungs_1_2(vocab, dimension, value)
    if hit:
        return hit, True

    for variant in _noise_variants(value):
        hit = _rungs_1_2(vocab, dimension, variant)
        if hit:
            return hit, True

    return value, False


def dedup_topics(topics: list[Any]) -> list[str]:
    """Collapse spelling variants of the same topic on the same item.

    Squash key equality. Longest original form survives (usually the
    better-spaced, more readable one); ties broken by first appearance.
    No count cap, no cross-item dedup, no flagging — topics are fully open.
    """
    best: dict[str, str] = {}
    order: list[str] = []
    for raw in topics or []:
        if raw is None:
            continue
        topic = str(raw).strip()
        if not topic:
            continue
        key = squash_key(topic)
        if not key:
            continue
        if key not in best:
            best[key] = topic
            order.append(key)
        elif len(topic) > len(best[key]):
            best[key] = topic
    return [best[key] for key in order]


def _snap_values(
    vocab: Vocabulary,
    dimension: str,
    values: list[Any],
    unknowns: list[tuple[str, str]],
) -> list[str]:
    out: list[str] = []
    for raw in values:
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        snapped, matched = snap_term(vocab, dimension, text)
        if not matched and not vocab.is_ignored(dimension, text):
            unknowns.append((dimension, text))
        if snapped not in out:
            out.append(snapped)
    return out


def normalize_analysis(
    analysis: dict[str, Any],
    content_type: str,
    db: Any = None,
    content_id: str | None = None,
) -> dict[str, Any]:
    """Snap aliases to canonical forms and dedup topics, before write.

    Pure when db is None. When db is supplied, unmatched terms are upserted into
    vocabulary_unknown_terms — one row per distinct TERM, never per item.

    content_type is content_entities.content_type; it is accepted for symmetry
    with render_vocabulary_block() and future per-source rules.
    """
    if not isinstance(analysis, dict):
        return analysis

    vocab = load_vocabulary()
    result = dict(analysis)
    unknowns: list[tuple[str, str]] = []

    for key, dimension in FIELD_MAP.items():
        if key not in result:
            continue
        value = result[key]

        if key in SCALAR_KEYS:
            if value is None or not str(value).strip():
                continue
            snapped, matched = snap_term(vocab, dimension, str(value))
            if not matched and not vocab.is_ignored(dimension, str(value)):
                unknowns.append((dimension, str(value).strip()))
            result[key] = snapped
            continue

        values = value if isinstance(value, list) else ([value] if value else [])
        snapped_list = _snap_values(vocab, dimension, values, unknowns)
        default = DIMENSION_DEFAULTS.get(dimension)
        if not snapped_list and default:
            snapped_list = [default]
        result[key] = snapped_list

    if "topics" in result:
        result["topics"] = dedup_topics(result.get("topics") or [])

    if unknowns and db is not None:
        _record_unknowns(db, unknowns, content_id)

    log.info(
        "vocabulary_normalized content_id=%s content_type=%s unknown_terms=%d",
        content_id,
        content_type,
        len(unknowns),
    )
    return result


def _record_unknowns(db: Any, unknowns: list[tuple[str, str]], content_id: str | None) -> None:
    """Upsert one row per distinct term. Never touches the item's review flags."""
    seen: set[tuple[str, str]] = set()
    for dimension, term in unknowns:
        if (dimension, term) in seen:
            continue
        seen.add((dimension, term))
        try:
            db.record_unknown_term(dimension, term, example_content_id=content_id)
        except Exception:
            # A vocabulary bookkeeping failure must never fail an analysis.
            log.exception("vocabulary: failed to record unknown term %s/%s", dimension, term)
```

- [ ] **Step 4: Export the new functions**

In `src/api/rcars/services/vocabulary/__init__.py`, add the import and the `__all__` entries:

```python
from rcars.services.vocabulary.normalize import (
    FIELD_MAP,
    dedup_topics,
    normalize_analysis,
    snap_term,
)
```

Add `"FIELD_MAP"`, `"dedup_topics"`, `"normalize_analysis"`, and `"snap_term"` to `__all__`.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary.py -v
```

Expected: PASS. If `test_rung3_extra_red_hat_prefix` fails on `Red Hat AWS`, confirm `_noise_variants` emits the prefix-stripped form — that case exercises the "leading Red Hat" half of rung 3.

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/services/vocabulary/ src/api/tests/test_vocabulary.py
git commit -m "[RHDPCD-507] Add alias match ladder and topic dedup normalizer"
```

---

### Task 3: Unknown-terms table, DB methods, and recording

**Files:**
- Modify: `src/api/rcars/db/database.py`
- Test: `src/api/tests/test_vocabulary_db.py` (create)

**Interfaces:**
- Consumes: `normalize_analysis(..., db=...)` calling `db.record_unknown_term(dimension, term, example_content_id=None)` from Task 2.
- Produces, on `Database`:
  - `record_unknown_term(dimension: str, term: str, example_content_id: str | None = None) -> None`
  - `get_unknown_terms(status: str | None = "pending", dimension: str | None = None) -> list[dict]`
  - `resolve_unknown_term(dimension: str, term: str, action: str, resolved_to: str | None, resolved_by: str) -> dict | None`

- [ ] **Step 1: Write the failing DB tests**

Create `src/api/tests/test_vocabulary_db.py`:

```python
"""Tests for the vocabulary_unknown_terms queue. Requires a live PostgreSQL."""

from __future__ import annotations

import os

import pytest

from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    import psycopg

    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")

    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


class TestUnknownTermsSchema:
    def test_table_created(self, db):
        with db.pool.connection() as conn:
            cur = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'vocabulary_unknown_terms'"
            )
            assert cur.fetchone() is not None

    def test_recommender_audience_column_added(self, db):
        with db.pool.connection() as conn:
            cur = conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'showroom_analysis' "
                "AND column_name = 'recommender_audience_json'"
            )
            assert cur.fetchone() is not None


class TestRecordUnknownTerm:
    def test_records_one_row(self, db):
        db.record_unknown_term("products", "Wombat Server", example_content_id="babylon:lb1")
        rows = db.get_unknown_terms()
        assert len(rows) == 1
        assert rows[0]["dimension"] == "products"
        assert rows[0]["term"] == "Wombat Server"
        assert rows[0]["occurrences"] == 1
        assert rows[0]["status"] == "pending"
        assert rows[0]["example_content_id"] == "babylon:lb1"

    def test_reseeing_bumps_counter_not_rows(self, db):
        db.record_unknown_term("products", "Wombat Server")
        db.record_unknown_term("products", "Wombat Server")
        rows = db.get_unknown_terms()
        assert len(rows) == 1
        assert rows[0]["occurrences"] == 2
        assert rows[0]["last_seen"] >= rows[0]["first_seen"]

    def test_same_term_different_dimensions_are_separate_rows(self, db):
        db.record_unknown_term("products", "Edge")
        db.record_unknown_term("platforms", "Edge")
        assert len(db.get_unknown_terms()) == 2

    def test_rejected_term_is_not_reupserted(self, db):
        db.record_unknown_term("products", "Wombat Server")
        db.resolve_unknown_term("products", "Wombat Server", "reject", None, "admin@redhat.com")
        db.record_unknown_term("products", "Wombat Server")
        rows = db.get_unknown_terms(status=None)
        assert len(rows) == 1
        assert rows[0]["status"] == "rejected"
        assert rows[0]["occurrences"] == 1

    def test_rejected_term_excluded_from_pending_queue(self, db):
        db.record_unknown_term("products", "Wombat Server")
        db.resolve_unknown_term("products", "Wombat Server", "reject", None, "admin@redhat.com")
        assert db.get_unknown_terms(status="pending") == []


class TestGetUnknownTerms:
    def test_ranked_by_occurrences_desc(self, db):
        db.record_unknown_term("products", "Rare")
        for _ in range(3):
            db.record_unknown_term("products", "Common")
        terms = [r["term"] for r in db.get_unknown_terms()]
        assert terms == ["Common", "Rare"]

    def test_filter_by_dimension(self, db):
        db.record_unknown_term("products", "P")
        db.record_unknown_term("verticals", "V")
        rows = db.get_unknown_terms(dimension="verticals")
        assert [r["term"] for r in rows] == ["V"]


class TestResolveUnknownTerm:
    def test_alias_records_target(self, db):
        db.record_unknown_term("products", "RHOCP")
        row = db.resolve_unknown_term(
            "products", "RHOCP", "alias",
            "Red Hat OpenShift Container Platform", "admin@redhat.com",
        )
        assert row["status"] == "aliased"
        assert row["resolved_to"] == "Red Hat OpenShift Container Platform"
        assert row["resolved_by"] == "admin@redhat.com"
        assert row["resolved_at"] is not None

    def test_promote_sets_status(self, db):
        db.record_unknown_term("products", "Brand New Product")
        row = db.resolve_unknown_term(
            "products", "Brand New Product", "promote", None, "admin@redhat.com"
        )
        assert row["status"] == "promoted"

    def test_missing_term_returns_none(self, db):
        assert db.resolve_unknown_term(
            "products", "Nope", "reject", None, "admin@redhat.com"
        ) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary_db.py -v
```

Expected: FAIL — `test_table_created` asserts on a missing table; the rest raise `AttributeError: 'Database' object has no attribute 'record_unknown_term'`.

- [ ] **Step 3: Add the schema**

In `src/api/rcars/db/database.py`, insert this immediately before the closing `"""` of `SCHEMA_SQL` (after the `-- Rename completions → experiences` block around line 455):

```sql
-- Controlled vocabulary — RHDPCD-507
-- The unit of review is the TERM, not the item: an unknown product means the
-- LIST is missing a term, so vocabulary work never sets enrichment_review_needed.
CREATE TABLE IF NOT EXISTS vocabulary_unknown_terms (
    dimension       TEXT NOT NULL,
    term            TEXT NOT NULL,
    occurrences     INTEGER NOT NULL DEFAULT 1,
    first_seen      TIMESTAMPTZ DEFAULT NOW(),
    last_seen       TIMESTAMPTZ DEFAULT NOW(),
    example_content_id TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',   -- pending | aliased | promoted | rejected
    resolved_to     TEXT,
    resolved_by     TEXT,
    resolved_at     TIMESTAMPTZ,
    PRIMARY KEY (dimension, term)
);

CREATE INDEX IF NOT EXISTS idx_vocab_unknown_status
    ON vocabulary_unknown_terms(status, occurrences DESC);

-- Who at Red Hat should know about this content (distinct from audience_json,
-- which is who the content is FOR). Nothing reads this yet — groundwork for
-- role-aware Advisor routing.
ALTER TABLE showroom_analysis ADD COLUMN IF NOT EXISTS recommender_audience_json JSONB;
```

- [ ] **Step 4: Add the three Database methods**

In `src/api/rcars/db/database.py`, add these methods to the `Database` class immediately after `upsert_showroom_analysis` (which ends around line 1004, just before `def update_content_entity_card`):

```python
    # ── Controlled vocabulary — unknown terms queue ──

    def record_unknown_term(
        self, dimension: str, term: str, example_content_id: str | None = None
    ) -> None:
        """Upsert one row per distinct term. Re-seeing bumps occurrences.

        A term an admin has rejected is never re-surfaced: the counter is left
        alone and the status is preserved, so the queue actually drains.
        """
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO vocabulary_unknown_terms
                    (dimension, term, occurrences, example_content_id)
                VALUES (%(dimension)s, %(term)s, 1, %(example_content_id)s)
                ON CONFLICT (dimension, term) DO UPDATE SET
                    occurrences = CASE
                        WHEN vocabulary_unknown_terms.status = 'rejected'
                        THEN vocabulary_unknown_terms.occurrences
                        ELSE vocabulary_unknown_terms.occurrences + 1
                    END,
                    last_seen = CASE
                        WHEN vocabulary_unknown_terms.status = 'rejected'
                        THEN vocabulary_unknown_terms.last_seen
                        ELSE NOW()
                    END,
                    example_content_id = COALESCE(
                        vocabulary_unknown_terms.example_content_id,
                        EXCLUDED.example_content_id
                    )
                """,
                {"dimension": dimension, "term": term, "example_content_id": example_content_id},
            )
            conn.commit()

    def get_unknown_terms(
        self, status: str | None = "pending", dimension: str | None = None
    ) -> list[dict[str, Any]]:
        """Queue rows, ranked by occurrences descending. status=None returns all."""
        clauses = []
        params: dict[str, Any] = {}
        if status:
            clauses.append("status = %(status)s")
            params["status"] = status
        if dimension:
            clauses.append("dimension = %(dimension)s")
            params["dimension"] = dimension
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._pool.connection() as conn:
            cur = conn.execute(
                f"""
                SELECT dimension, term, occurrences, first_seen, last_seen,
                       example_content_id, status, resolved_to, resolved_by, resolved_at
                FROM vocabulary_unknown_terms
                {where}
                ORDER BY occurrences DESC, dimension, term
                """,
                params,
            )
            return cur.fetchall()

    def resolve_unknown_term(
        self,
        dimension: str,
        term: str,
        action: str,
        resolved_to: str | None,
        resolved_by: str,
    ) -> dict[str, Any] | None:
        """Record an admin decision. Staged only — nothing about analysis changes
        until a regenerated vocabulary.yaml is committed and deployed.
        """
        status = {"alias": "aliased", "promote": "promoted", "reject": "rejected"}.get(action)
        if not status:
            raise ValueError(f"unknown vocabulary action: {action}")

        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE vocabulary_unknown_terms
                SET status = %(status)s,
                    resolved_to = %(resolved_to)s,
                    resolved_by = %(resolved_by)s,
                    resolved_at = NOW()
                WHERE dimension = %(dimension)s AND term = %(term)s
                RETURNING dimension, term, occurrences, first_seen, last_seen,
                          example_content_id, status, resolved_to, resolved_by, resolved_at
                """,
                {
                    "status": status,
                    "resolved_to": resolved_to if status == "aliased" else None,
                    "resolved_by": resolved_by,
                    "dimension": dimension,
                    "term": term,
                },
            )
            row = cur.fetchone()
            conn.commit()
            return row
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary_db.py -v
```

Expected: PASS, all 11 tests.

- [ ] **Step 6: Add the "never sets the review badge" guard test**

Append to `src/api/tests/test_vocabulary_db.py`:

```python
class TestReviewBadgeUntouched:
    def test_normalization_never_sets_review_flags(self, db):
        """Vocabulary work never sets enrichment_review_needed or review_reasons."""
        from rcars.services.vocabulary import normalize_analysis

        db.upsert_babylon_catalog_item({
            "ci_name": "lb1",
            "display_name": "Lab One",
            "category": "workshop",
            "stage": "prod",
            "showroom_url": "https://example.com/showroom.git",
        })
        db.upsert_showroom_analysis({
            "content_id": "babylon:lb1",
            "summary": "A lab",
            "enrichment_review_needed": False,
            "review_reasons": None,
        })

        normalize_analysis(
            {"products": ["Wombat Server 3000"], "topics": ["a", "A"]},
            "lab",
            db=db,
            content_id="babylon:lb1",
        )

        with db.pool.connection() as conn:
            cur = conn.execute(
                "SELECT enrichment_review_needed, review_reasons "
                "FROM showroom_analysis WHERE content_id = 'babylon:lb1'"
            )
            row = cur.fetchone()
        assert row["enrichment_review_needed"] is False
        assert row["review_reasons"] is None
        assert len(db.get_unknown_terms()) == 1
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary_db.py -v
```

Expected: PASS, 12 tests. If `upsert_babylon_catalog_item` rejects the fixture dict, read its field list in `database.py` and supply the keys it requires — the point of the test is the two review columns, not the catalog row.

- [ ] **Step 8: Add the ignored-terms suppression test**

Append to `src/api/tests/test_vocabulary.py`:

```python
class TestIgnoredTermsSuppression:
    def test_ignored_term_creates_no_row(self):
        """A term in ignored_terms is stored verbatim but never recorded."""

        class RecordingDb:
            def __init__(self):
                self.calls = []

            def record_unknown_term(self, dimension, term, example_content_id=None):
                self.calls.append((dimension, term))

        db = RecordingDb()
        out = normalize_analysis(
            {"products": ["Kubernetes", "Wombat Server 3000"]},
            "lab",
            db=db,
            content_id="babylon:lb1",
        )
        assert out["products"] == ["Kubernetes", "Wombat Server 3000"]
        assert db.calls == [("products", "Wombat Server 3000")]

    def test_duplicate_unknowns_recorded_once_per_call(self):
        class RecordingDb:
            def __init__(self):
                self.calls = []

            def record_unknown_term(self, dimension, term, example_content_id=None):
                self.calls.append((dimension, term))

        db = RecordingDb()
        normalize_analysis({"products": ["Wombat", "Wombat"]}, "lab", db=db)
        assert db.calls == [("products", "Wombat")]
```

- [ ] **Step 9: Run both test files to verify they pass**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary.py tests/test_vocabulary_db.py -v
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/api/rcars/db/database.py src/api/tests/test_vocabulary_db.py src/api/tests/test_vocabulary.py
git commit -m "[RHDPCD-507] Add vocabulary unknown-terms queue and recommender_audience column"
```

---

### Task 4: Prompt renderer and injection into the Showroom prompt

**Files:**
- Create: `src/api/rcars/services/vocabulary/render.py`
- Modify: `src/api/rcars/services/vocabulary/__init__.py`
- Modify: `src/api/rcars/prompts/analyze_showroom.txt`
- Modify: `src/api/rcars/services/analyzer.py:464-500`
- Test: `src/api/tests/test_vocabulary.py` (append)

**Interfaces:**
- Consumes: `load_vocabulary()`, `Vocabulary`, `DEFAULT_CONTENT_MODE` from Task 1.
- Produces:
  - `render_vocabulary_block(vocab: Vocabulary, content_type: str) -> str`
  - `VOCABULARY_SENTINEL: str = "{{VOCABULARY}}"`
  - `build_analysis_prompt(ci_name, display_name, category, product, content_files, entity_content_type: str = "lab") -> tuple[str, str]` — new trailing keyword argument

- [ ] **Step 1: Write the failing renderer tests**

Append to `src/api/tests/test_vocabulary.py`:

```python
from rcars.services.vocabulary import VOCABULARY_SENTINEL, render_vocabulary_block


class TestRenderVocabularyBlock:
    def test_products_are_injected(self):
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "Red Hat OpenShift Container Platform" in block
        assert "Red Hat Advanced Cluster Security" in block

    def test_solutions_are_not_injected(self):
        """Only products and verb hints go into the prompt."""
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "Data Services & Storage" not in block
        assert "Financial Services" not in block
        assert "On-Premise" not in block

    def test_hands_on_verbs_for_lab(self):
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "deploy" in block
        assert "troubleshoot" in block
        assert "compare" not in block

    def test_read_through_verbs_for_architecture(self):
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "architecture")
        assert "compare" in block
        assert "evaluate" in block
        assert "troubleshoot" not in block

    def test_rejected_verbs_appear_as_avoid_hints(self):
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "understand" in block
        assert "be familiar with" in block

    def test_unmapped_content_type_falls_back_with_warning(self, caplog):
        import logging

        vocab = load_vocabulary()
        with caplog.at_level(logging.WARNING):
            block = render_vocabulary_block(vocab, "podcast")
        assert "deploy" in block  # hands_on fallback
        assert "podcast" in caplog.text

    def test_block_contains_no_format_braces(self):
        """The block is spliced into a template that cannot use str.format()."""
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "{" not in block and "}" not in block


class TestPromptInjection:
    def test_sentinel_present_in_template(self):
        from rcars.services.analyzer import PROMPT_TEMPLATE_PATH

        assert VOCABULARY_SENTINEL in PROMPT_TEMPLATE_PATH.read_text()

    def test_sentinel_sits_inside_the_instructions_section(self):
        """build_analysis_prompt slices the template; only the Instructions
        section reaches the system prompt. A sentinel outside it is discarded.
        """
        from rcars.services.analyzer import PROMPT_TEMPLATE_PATH

        template = PROMPT_TEMPLATE_PATH.read_text()
        instructions_start = template.index("\n## Instructions\n")
        content_start = template.index("\n## Showroom Content\n")
        assert instructions_start < template.index(VOCABULARY_SENTINEL) < content_start

    def test_vocabulary_block_reaches_the_system_prompt(self):
        from rcars.services.analyzer import build_analysis_prompt

        system_prompt, user_message = build_analysis_prompt(
            ci_name="lb1",
            display_name="Lab One",
            category="workshop",
            product="OpenShift",
            content_files={"m1.adoc": "some content"},
            entity_content_type="lab",
        )
        assert VOCABULARY_SENTINEL not in system_prompt
        assert "Red Hat OpenShift Container Platform" in system_prompt
        assert "troubleshoot" in system_prompt
        assert "some content" in user_message

    def test_architecture_type_selects_read_through_verbs(self):
        from rcars.services.analyzer import build_analysis_prompt

        system_prompt, _ = build_analysis_prompt(
            ci_name="lb1",
            display_name="Lab One",
            category="workshop",
            product="OpenShift",
            content_files={"m1.adoc": "some content"},
            entity_content_type="architecture",
        )
        assert "evaluate" in system_prompt

    def test_prompt_asks_for_recommender_audience(self):
        from rcars.services.analyzer import PROMPT_TEMPLATE_PATH

        assert "recommender_audience" in PROMPT_TEMPLATE_PATH.read_text()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary.py -k "Render or Injection" -v
```

Expected: `ImportError: cannot import name 'VOCABULARY_SENTINEL'`.

- [ ] **Step 3: Write `render.py`**

Create `src/api/rcars/services/vocabulary/render.py`:

```python
"""The vocabulary block injected into analysis prompts.

Two parts, and only two: a canonical product list, and mode-appropriate action
verb hints. Solutions, verticals, platforms, difficulty, topics, and audience
are normalized after the fact and must never appear here — injecting them would
bloat the prompt and box the model in.

Verbs are a NUDGE. Nothing is validated, rejected, or flagged.
"""

from __future__ import annotations

import logging

from rcars.services.vocabulary.models import DEFAULT_CONTENT_MODE, Vocabulary

log = logging.getLogger(__name__)

# The template cannot use str.format() — it contains literal braces from its
# JSON output example — so injection replaces an explicit sentinel token.
VOCABULARY_SENTINEL = "{{VOCABULARY}}"


def _mode_for(vocab: Vocabulary, content_type: str) -> str:
    mode = vocab.content_modes.get((content_type or "").lower())
    if mode:
        return mode
    log.warning(
        "vocabulary: no content_modes entry for content_type=%r, falling back to %s",
        content_type,
        DEFAULT_CONTENT_MODE,
    )
    return DEFAULT_CONTENT_MODE


def render_vocabulary_block(vocab: Vocabulary, content_type: str) -> str:
    """Build the injected block for a given content_entities.content_type."""
    products = vocab.canonical_names("products")
    mode = _mode_for(vocab, content_type)
    verbs = vocab.action_verbs.get(mode) or vocab.action_verbs.get(DEFAULT_CONTENT_MODE) or {}
    valid = ", ".join(verbs.get("valid", ())[:12])
    rejected = ", ".join(verbs.get("rejected", ())[:6])

    lines = [
        "### Product Naming",
        "",
        "When naming Red Hat products, prefer a name from this list where one "
        "fits. Only coin a new name when nothing here matches what the content "
        "actually covers.",
        "",
        "; ".join(products),
        "",
        "### Learning Objective Phrasing",
        "",
        f"Write each learning objective around a concrete, observable action "
        f"such as {valid}.",
    ]
    if rejected:
        lines.append(f"Avoid vague framings like {rejected}.")

    return "\n".join(lines)
```

- [ ] **Step 4: Export the renderer**

In `src/api/rcars/services/vocabulary/__init__.py`, add:

```python
from rcars.services.vocabulary.render import VOCABULARY_SENTINEL, render_vocabulary_block
```

Add `"VOCABULARY_SENTINEL"` and `"render_vocabulary_block"` to `__all__`.

- [ ] **Step 5: Add the sentinel and the new field to the prompt template**

In `src/api/rcars/prompts/analyze_showroom.txt`, insert the sentinel between the "Focus your analysis on" block and the "### Learning Objectives" heading. Replace:

```text
- How long it would realistically take to complete

### Learning Objectives
```

with:

```text
- How long it would realistically take to complete

{{VOCABULARY}}

### Learning Objectives
```

Then add the new output field. Replace:

```text
  "audience": ["target audience descriptors, e.g. 'platform engineers', 'developers', 'IT decision makers'"],
```

with:

```text
  "audience": ["who this content is FOR, e.g. 'platform engineers', 'developers', 'IT decision makers'"],
  "recommender_audience": ["who at Red Hat should know about this content, e.g. 'solution architects', 'consultants', 'TAMs', 'field engineers'"],
```

The sentinel sits between `## Instructions` and `## Showroom Content`, so it lands in the system half of the split. Do not move it above `## Instructions` — `build_analysis_prompt` would discard it silently.

- [ ] **Step 6: Wire injection into `build_analysis_prompt`**

In `src/api/rcars/services/analyzer.py`, replace the whole of `build_analysis_prompt` (lines 464-500) with:

```python
def build_analysis_prompt(
    ci_name: str,
    display_name: str,
    category: str,
    product: str,
    content_files: dict[str, str],
    entity_content_type: str = "lab",
) -> tuple[str, str]:
    """Build analysis prompt split into system instructions and user data.

    entity_content_type is content_entities.content_type — NOT the LLM's
    self-reported content_type, which does not exist yet at this point. It
    selects the action-verb hints in the injected vocabulary block.

    Returns (system_prompt, user_message) for system/user separation (M-1/M-4).
    """
    from rcars.services.vocabulary import (
        VOCABULARY_SENTINEL,
        load_vocabulary,
        render_vocabulary_block,
    )

    template = PROMPT_TEMPLATE_PATH.read_text()

    # The template contains literal { } from its JSON example, so str.format()
    # cannot be used — replace an explicit sentinel instead.
    vocabulary_block = render_vocabulary_block(load_vocabulary(), entity_content_type)
    template = template.replace(VOCABULARY_SENTINEL, vocabulary_block)

    # Concatenate file contents with headers
    content_parts = []
    for filename, content in sorted(content_files.items()):
        content_parts.append(f"=== File: {filename} ===\n{content}")
    all_content = "\n\n".join(content_parts)
    all_content = truncate_content(all_content)

    # Split template: system gets role + instructions, user gets item info + content
    item_info_start = template.index("\n## Item Information\n")
    instructions_start = template.index("\n## Instructions\n")
    content_start = template.index("\n## Showroom Content\n")

    system_prompt = template[:item_info_start].strip() + "\n\n" + template[instructions_start:content_start].strip()

    user_message = (
        f"## Item Information\n"
        f"- CI Name: {ci_name}\n"
        f"- Display Name: {display_name or ci_name}\n"
        f"- Category: {category or 'Unknown'}\n"
        f"- Product: {product or 'Unknown'}\n\n"
        f"## Showroom Content\n\n{all_content}"
    )

    return system_prompt, user_message
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/api/rcars/services/vocabulary/ src/api/rcars/prompts/analyze_showroom.txt src/api/rcars/services/analyzer.py src/api/tests/test_vocabulary.py
git commit -m "[RHDPCD-507] Inject product list and verb hints into the analysis prompt"
```

---

### Task 5: Normalize on the analysis path and persist `recommender_audience_json`

**Files:**
- Modify: `src/api/rcars/services/analyzer.py:593-773`
- Modify: `src/api/rcars/db/database.py` (`upsert_showroom_analysis`)
- Modify: `src/api/rcars/workers/scan.py:53-130`
- Modify: `src/api/rcars/cli.py:172-270`
- Test: `src/api/tests/test_vocabulary.py` (append)

**Interfaces:**
- Consumes: `normalize_analysis()` from Task 2, `build_analysis_prompt(..., entity_content_type=...)` from Task 4, `db.record_unknown_term()` from Task 3.
- Produces: `analyze_showroom(..., entity_content_type: str = "lab")` — new trailing keyword argument; every returned `analysis` dict is already normalized.

**Why here and only here:** normalization runs immediately after `parse_analysis_response()` inside the analyzer, not at each write site. `_sanitize_format_suitability` is applied inconsistently across `scan.py:112` and `cli.py:214,252`; do not repeat that.

- [ ] **Step 1: Write the failing analyzer test**

Append to `src/api/tests/test_vocabulary.py`:

```python
class TestAnalyzerNormalizesOnce:
    def test_analysis_is_normalized_before_return(self, monkeypatch):
        """analyze_showroom normalizes right after parse — not at the write sites."""
        from pathlib import Path

        from rcars.services import analyzer

        monkeypatch.setattr(analyzer, "clone_showroom", lambda *a, **k: Path("/tmp"))
        monkeypatch.setattr(analyzer, "get_repo_head", lambda *a, **k: ("abc123", "2026-01-01"))
        monkeypatch.setattr(
            analyzer, "read_showroom_content", lambda *a, **k: {"m1.adoc": "content"}
        )
        monkeypatch.setattr(analyzer, "filter_boilerplate_files", lambda files: files)
        monkeypatch.setattr(analyzer, "generate_embedding", lambda *a, **k: [0.0] * 768)

        class FakeResult:
            text = (
                '{"content_type": "workshop", "summary": "s", '
                '"products": ["RHACS", "OCP"], "difficulty": "Introductory", '
                '"topics": ["GitOps with ArgoCD", "GitOps with Argo CD"], '
                '"recommender_audience": ["solution architects"], "modules": []}'
            )
            input_tokens = 1
            output_tokens = 1
            provider = "test"

        monkeypatch.setattr("rcars.config.call_llm", lambda *a, **k: FakeResult())

        result = analyzer.analyze_showroom(
            ci_name="lb1",
            display_name="Lab One",
            category="workshop",
            product="OpenShift",
            showroom_url="https://example.com/x.git",
            showroom_ref=None,
            settings=object(),
            entity_content_type="lab",
        )

        analysis = result["analysis"]
        assert analysis["products"] == [
            "Red Hat Advanced Cluster Security",
            "Red Hat OpenShift Container Platform",
        ]
        assert analysis["difficulty"] == "beginner"
        assert analysis["topics"] == ["GitOps with Argo CD"]
        assert analysis["recommender_audience"] == ["solution architects"]
        assert "review_reasons" not in analysis
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary.py -k AnalyzerNormalizes -v
```

Expected: FAIL — `analyze_showroom() got an unexpected keyword argument 'entity_content_type'`.

- [ ] **Step 3: Thread `entity_content_type` and normalize in `analyze_showroom`**

In `src/api/rcars/services/analyzer.py`, add the parameter to the signature (line 593-606). Insert it after `keywords`:

```python
    keywords: list[str] | None = None,
    entity_content_type: str = "lab",
) -> dict[str, Any] | None:
```

Then in the donor-reuse branch, normalize the borrowed analysis before it is used. Replace:

```python
                # Rebuild CI embedding with this CI's own keywords
                ci_embedding_text = build_embedding_text(donor_analysis, keywords=keywords, display_name=display_name)
```

with:

```python
                # Normalize the borrowed analysis too — the donor may predate a
                # vocabulary change, and normalization is idempotent.
                from rcars.services.vocabulary import normalize_analysis
                donor_analysis["recommender_audience"] = donor.get("recommender_audience_json")
                donor_analysis = normalize_analysis(
                    donor_analysis, entity_content_type,
                    db=db, content_id=f"babylon:{ci_name}",
                )

                # Rebuild CI embedding with this CI's own keywords
                ci_embedding_text = build_embedding_text(donor_analysis, keywords=keywords, display_name=display_name)
```

Next, pass the content type into the prompt builder. Replace:

```python
        system_prompt, user_message = build_analysis_prompt(
            ci_name, display_name, category, product, content_files
        )
```

with:

```python
        system_prompt, user_message = build_analysis_prompt(
            ci_name, display_name, category, product, content_files,
            entity_content_type=entity_content_type,
        )
```

Finally, normalize immediately after the parse. Replace:

```python
        analysis = parse_analysis_response(response_text)
        if not analysis:
            log.error("analyze %s: failed to parse Sonnet response", ci_name)
            return {"error": "parse_failed", "message": f"Failed to parse LLM response for {ci_name}"}
```

with:

```python
        analysis = parse_analysis_response(response_text)
        if not analysis:
            log.error("analyze %s: failed to parse Sonnet response", ci_name)
            return {"error": "parse_failed", "message": f"Failed to parse LLM response for {ci_name}"}

        # Normalize ONCE, here — never at the individual write sites.
        from rcars.services.vocabulary import normalize_analysis
        analysis = normalize_analysis(
            analysis, entity_content_type, db=db, content_id=f"babylon:{ci_name}"
        )
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary.py -k AnalyzerNormalizes -v
```

Expected: PASS.

- [ ] **Step 5: Persist the new column**

In `src/api/rcars/db/database.py`, `upsert_showroom_analysis`: add `"recommender_audience_json"` to both the `fields` list and the `jsonb_fields` list.

```python
        fields = [
            "content_id", "content_type", "summary",
            "products_json", "audience_json", "recommender_audience_json", "topics_json",
            "modules_json", "learning_objectives_json",
            "difficulty", "estimated_duration_min",
            "format_suitability_json", "use_cases_json",
            "last_repo_commit", "last_repo_updated",
            "last_analyzed", "is_stale", "stale_commit", "content_hash",
            "enrichment_review_needed", "review_reasons",
        ]
```

```python
        jsonb_fields = [
            "products_json", "audience_json", "recommender_audience_json", "topics_json",
            "modules_json", "learning_objectives_json",
            "format_suitability_json", "use_cases_json",
            "review_reasons",
        ]
```

- [ ] **Step 6: Wire the scan worker**

In `src/api/rcars/workers/scan.py`, in `run_analysis`, add the content type to the `analyze_showroom` partial. After the `keywords=item.get("keywords") or [],` line add:

```python
                entity_content_type=item.get("content_type") or "lab",
```

Then add the new field to `analysis_data` (after `"audience_json": analysis.get("audience"),`):

```python
                "recommender_audience_json": analysis.get("recommender_audience"),
```

`get_babylon_item` selects `ce.*`, so `item["content_type"]` is the entity content type, not the LLM's.

- [ ] **Step 7: Wire the CLI scan command**

In `src/api/rcars/cli.py`, in `process_item` (line 172-187), add to the `analyze_showroom` call after `keywords=item.get("keywords") or [],`:

```python
            entity_content_type=item.get("content_type") or "lab",
```

Then add `"recommender_audience_json": analysis.get("recommender_audience"),` after the `"audience_json"` line in **both** dicts — the direct `upsert_showroom_analysis` call around line 208 and the `analysis_data` sibling-propagation dict around line 246.

- [ ] **Step 8: Run the full backend suite**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/ -m "not integration" -q
```

Expected: PASS, with the exception of `tests/test_product_terms.py`, which is retargeted in Task 6. Note any other failure and fix it before committing.

- [ ] **Step 9: Commit**

```bash
git add src/api/rcars/services/analyzer.py src/api/rcars/db/database.py src/api/rcars/workers/scan.py src/api/rcars/cli.py src/api/tests/test_vocabulary.py
git commit -m "[RHDPCD-507] Normalize analysis output once, after parse"
```

---

### Task 6: Merge `product-terms.yaml` into the vocabulary for Advisor query expansion

**Files:**
- Modify: `src/api/rcars/services/recommender/pipeline.py:30-72`
- Delete: `src/api/rcars/data/product-terms.yaml`
- Rewrite: `src/api/tests/test_product_terms.py`

**Interfaces:**
- Consumes: `load_vocabulary()` from Task 1.
- Produces: `_expand_query_terms(query: str) -> str`, unchanged signature, now vocabulary-backed. `_load_product_terms()` and `_product_terms_cache` are removed.

**This is the central requirement of the spec:** the same canonical names must be used in both directions. After this task there is one file and one answer.

- [ ] **Step 1: Rewrite the test file to target the vocabulary**

Replace the entire contents of `src/api/tests/test_product_terms.py`:

```python
"""Advisor query expansion, now backed by the controlled vocabulary.

Formerly tested data/product-terms.yaml, which was merged into
data/vocabulary.yaml and deleted (RHDPCD-507).
"""

from __future__ import annotations

import pytest

from rcars.services.recommender.pipeline import _expand_query_terms
from rcars.services.vocabulary import load_vocabulary

# Every acronym and synonym key from the deleted product-terms.yaml.
# Coverage requirement from the spec: every term must survive the merge.
LEGACY_PRODUCT_TERMS = [
    "AAP", "ACM", "RHACM", "ACS", "RHACS", "RHOAI", "OCP", "ARO", "ROSA",
    "RHEL", "RHDH", "SNO", "RHSSO", "EDA", "TAP", "AMQ", "CRW", "RHBK",
    "Red Hat AI", "OpenShift AI", "DevSpaces", "Dev Spaces", "Developer Hub",
    "Quay", "3scale", "Service Mesh", "Serverless", "GitOps", "Virtualization",
    "MaaS",
]


@pytest.fixture(autouse=True)
def clear_vocabulary_cache():
    load_vocabulary.cache_clear()
    yield
    load_vocabulary.cache_clear()


class TestExpansionReadsVocabulary:
    def test_acronym_expands_to_canonical_name(self):
        result = _expand_query_terms("show me RHACS labs")
        assert "Red Hat Advanced Cluster Security" in result
        assert result.startswith("show me RHACS")

    def test_case_insensitive(self):
        assert "Red Hat OpenShift AI" in _expand_query_terms("rhoai content")

    def test_canonical_name_in_query_still_recognised(self):
        result = _expand_query_terms("Red Hat Quay setup")
        assert "Red Hat Quay" in result

    def test_no_match_returns_unchanged(self):
        assert _expand_query_terms("wombat husbandry") == "wombat husbandry"

    def test_partial_word_is_not_expanded(self):
        """Word-boundary matching — RHOAI inside RHOAIX must not expand."""
        assert "Red Hat OpenShift AI" not in _expand_query_terms("RHOAIX platform")

    def test_no_double_expansion(self):
        result = _expand_query_terms("RHACS")
        assert result.count("Red Hat Advanced Cluster Security") == 1


class TestMigrationCoverage:
    @pytest.mark.parametrize("term", LEGACY_PRODUCT_TERMS)
    def test_every_legacy_term_still_expands(self, term):
        result = _expand_query_terms(f"find {term} content")
        assert result != f"find {term} content", f"'{term}' no longer expands"


class TestSearchTerms:
    def test_search_terms_widen_expansion(self):
        """GitOps must still pull in ArgoCD and Argo CD as recall terms."""
        result = _expand_query_terms("GitOps demos")
        assert "Red Hat OpenShift GitOps" in result
        assert "Argo CD" in result

    def test_search_terms_ignored_by_normalization(self):
        """search_terms widen recall only — they never snap a value."""
        from rcars.services.vocabulary import normalize_analysis

        out = normalize_analysis({"products": ["container registry"]}, "lab")
        assert out["products"] == ["container registry"]


class TestOldFileGone:
    def test_product_terms_yaml_is_deleted(self):
        from importlib.resources import files as pkg_files

        assert not pkg_files("rcars.data").joinpath("product-terms.yaml").is_file()

    def test_loader_function_removed(self):
        import rcars.services.recommender.pipeline as pipeline

        assert not hasattr(pipeline, "_load_product_terms")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_product_terms.py -v
```

Expected: FAIL — `RHACS` currently expands to the old `product-terms.yaml` string "Red Hat Advanced Cluster Security for Kubernetes"; `TestOldFileGone` fails because the file still exists.

- [ ] **Step 3: Rewrite the expansion functions**

In `src/api/rcars/services/recommender/pipeline.py`, delete `_product_terms_cache` (line 30), `_load_product_terms` (lines 33-48), and `_expand_query_terms` (lines 51-72), and replace all three with:

```python
def _build_expansion_map() -> dict[str, str]:
    """Invert the vocabulary's product aliases into term -> canonical name.

    Aliases normalize AND widen recall; search_terms widen recall only. Both are
    appended at query time. Longest term first at match time so 'Dev Spaces'
    wins over 'Spaces'.
    """
    from rcars.services.vocabulary import load_vocabulary

    expansion: dict[str, str] = {}
    for entry in load_vocabulary().entries("products"):
        extras = " ".join(entry.search_terms)
        target = f"{entry.name} {extras}".strip() if extras else entry.name
        for term in (entry.name, *entry.aliases, *entry.search_terms):
            expansion.setdefault(term, target)
    return expansion


def _expand_query_terms(query: str) -> str:
    """Expand product names, acronyms, and synonyms for better embedding match.

    One list, two consumers: this reads the same vocabulary the analyzer writes
    canonical names from, so the query side and the analysis side cannot drift.
    """
    expansion = _build_expansion_map()
    if not expansion:
        return query

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(t) for t in sorted(expansion, key=len, reverse=True)) + r")\b",
        re.IGNORECASE,
    )
    lookup = {t.casefold(): v for t, v in expansion.items()}

    def _replace(m: re.Match) -> str:
        matched = m.group(0)
        target = lookup[matched.casefold()]
        # Do not append an expansion the user already typed.
        if target.casefold() == matched.casefold():
            return matched
        return f"{matched} ({target})"

    return pattern.sub(_replace, query)
```

`_build_expansion_map()` is cheap — it reads the process-cached vocabulary and builds a dict of a few hundred entries per query. Do not add a second cache layer; `load_vocabulary()` is already the cache.

- [ ] **Step 4: Remove the now-unused imports**

In `src/api/rcars/services/recommender/pipeline.py`, `yaml` (line 8) and `files as _pkg_files` (line 9) are no longer used. Delete both import lines. Verify nothing else in the file uses them:

```bash
cd src/api && grep -n "yaml\.\|_pkg_files" rcars/services/recommender/pipeline.py
```

Expected: no output.

- [ ] **Step 5: Delete the old data file**

```bash
git rm src/api/rcars/data/product-terms.yaml
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_product_terms.py -v
```

Expected: PASS. If a `TestMigrationCoverage` case fails, add the missing term as an alias or `search_terms` entry on the right product in `vocabulary.yaml` — do not weaken the test.

- [ ] **Step 7: Check for other references to the deleted file**

```bash
cd /Users/natestephany/devel/rcars && grep -rn "product-terms\|_load_product_terms" --include="*.py" --include="*.yaml" --include="*.j2" --include="*.md" --include="*.toml" . | grep -v docs/superpowers/specs | grep -v graphify-out
```

Expected: no output. Fix any hit before committing (`pyproject.toml` uses a `data/*` glob, so no change is needed there).

- [ ] **Step 8: Run the full backend suite**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/ -m "not integration" -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/api/rcars/services/recommender/pipeline.py src/api/tests/test_product_terms.py src/api/rcars/data/product-terms.yaml
git commit -m "[RHDPCD-507] Drive Advisor query expansion from the vocabulary"
```

---

### Task 7: YAML generator and the four admin endpoints

**Files:**
- Create: `src/api/rcars/services/vocabulary/generate.py`
- Modify: `src/api/rcars/services/vocabulary/__init__.py`
- Modify: `src/api/rcars/api/schemas.py`
- Modify: `src/api/rcars/api/routes/admin.py`
- Test: `src/api/tests/test_vocabulary_admin.py` (create)

**Interfaces:**
- Consumes: `load_vocabulary()`, `Vocabulary`, `DIMENSIONS` from Task 1; `db.get_unknown_terms()`, `db.resolve_unknown_term()` from Task 3.
- Produces:
  - `generate_vocabulary_yaml(vocab: Vocabulary, decisions: list[dict]) -> str`
  - `GET /api/v1/admin/vocabulary`
  - `GET /api/v1/admin/vocabulary/unknowns?status=&dimension=`
  - `PUT /api/v1/admin/vocabulary/unknowns/{dimension}/{term:path}`
  - `GET /api/v1/admin/vocabulary/generate`

- [ ] **Step 1: Write the failing generator and endpoint tests**

Create `src/api/tests/test_vocabulary_admin.py`:

```python
"""Vocabulary generator + admin endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import yaml
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings
from rcars.services.vocabulary import generate_vocabulary_yaml, load_vocabulary


@pytest.fixture(autouse=True)
def clear_vocabulary_cache():
    load_vocabulary.cache_clear()
    yield
    load_vocabulary.cache_clear()


@pytest.fixture
def client():
    settings = Settings(
        database_url="postgresql://rcars:rcars@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="admin@redhat.com",
        admin_emails_str="admin@redhat.com",
        curator_emails_str="admin@redhat.com,curator@redhat.com",
    )
    app = create_app(settings)
    app.state.db = MagicMock()
    app.state.redis = MagicMock()
    app.state.arq_redis = MagicMock()
    return TestClient(app)


class TestGenerator:
    def test_round_trips_current_vocabulary(self, tmp_path, monkeypatch):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [])

        path = tmp_path / "vocabulary.yaml"
        path.write_text(generated)
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        load_vocabulary.cache_clear()
        reloaded = load_vocabulary()

        assert reloaded.canonical_names("products") == vocab.canonical_names("products")
        assert reloaded.canonical_names("solutions") == vocab.canonical_names("solutions")
        assert reloaded.content_modes == vocab.content_modes
        assert reloaded.ignored_terms == vocab.ignored_terms

    def test_alias_decision_appends_to_existing_entry(self, tmp_path, monkeypatch):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [{
            "dimension": "products",
            "term": "RHOCP",
            "status": "aliased",
            "resolved_to": "Red Hat OpenShift Container Platform",
        }])
        data = yaml.safe_load(generated)
        entry = next(
            e for e in data["products"] if e["name"] == "Red Hat OpenShift Container Platform"
        )
        assert "RHOCP" in entry["aliases"]

    def test_promote_decision_creates_new_entry(self):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [{
            "dimension": "products",
            "term": "Brand New Product",
            "status": "promoted",
            "resolved_to": None,
        }])
        data = yaml.safe_load(generated)
        assert any(e["name"] == "Brand New Product" for e in data["products"])

    def test_rejections_are_preserved_in_ignored_terms(self):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [{
            "dimension": "products",
            "term": "Wombat Server",
            "status": "rejected",
            "resolved_to": None,
        }])
        data = yaml.safe_load(generated)
        assert "Wombat Server" in data["ignored_terms"]["products"]
        # existing rejections survive too
        assert "Kubernetes" in data["ignored_terms"]["products"]

    def test_pending_decisions_are_ignored(self):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [{
            "dimension": "products",
            "term": "Undecided Thing",
            "status": "pending",
            "resolved_to": None,
        }])
        assert "Undecided Thing" not in generated

    def test_generated_file_keeps_the_header_comment(self):
        generated = generate_vocabulary_yaml(load_vocabulary(), [])
        assert generated.lstrip().startswith("#")
        assert "controlled vocabulary" in generated.lower()


class TestVocabularyEndpoints:
    def test_get_vocabulary(self, client):
        resp = client.get("/api/v1/admin/vocabulary")
        assert resp.status_code == 200
        data = resp.json()
        names = [e["name"] for e in data["dimensions"]["products"]]
        assert "Red Hat OpenShift Container Platform" in names
        assert data["content_modes"]["lab"] == "hands_on"

    def test_get_unknowns(self, client):
        client.app.state.db.get_unknown_terms.return_value = [
            {"dimension": "products", "term": "Wombat", "occurrences": 4,
             "first_seen": None, "last_seen": None, "example_content_id": "babylon:lb1",
             "status": "pending", "resolved_to": None, "resolved_by": None, "resolved_at": None},
        ]
        resp = client.get("/api/v1/admin/vocabulary/unknowns")
        assert resp.status_code == 200
        assert resp.json()["terms"][0]["term"] == "Wombat"
        client.app.state.db.get_unknown_terms.assert_called_with(
            status="pending", dimension=None
        )

    def test_resolve_alias(self, client):
        client.app.state.db.resolve_unknown_term.return_value = {
            "dimension": "products", "term": "RHOCP", "occurrences": 1,
            "first_seen": None, "last_seen": None, "example_content_id": None,
            "status": "aliased", "resolved_to": "Red Hat OpenShift Container Platform",
            "resolved_by": "admin@redhat.com", "resolved_at": None,
        }
        resp = client.put(
            "/api/v1/admin/vocabulary/unknowns/products/RHOCP",
            json={"action": "alias", "resolved_to": "Red Hat OpenShift Container Platform"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "aliased"

    def test_resolve_alias_requires_target(self, client):
        resp = client.put(
            "/api/v1/admin/vocabulary/unknowns/products/RHOCP",
            json={"action": "alias"},
        )
        assert resp.status_code == 400

    def test_resolve_rejects_unknown_canonical(self, client):
        resp = client.put(
            "/api/v1/admin/vocabulary/unknowns/products/RHOCP",
            json={"action": "alias", "resolved_to": "Not A Real Canonical"},
        )
        assert resp.status_code == 400

    def test_resolve_missing_term_404(self, client):
        client.app.state.db.resolve_unknown_term.return_value = None
        resp = client.put(
            "/api/v1/admin/vocabulary/unknowns/products/Nope",
            json={"action": "reject"},
        )
        assert resp.status_code == 404

    def test_generate_returns_downloadable_yaml(self, client):
        client.app.state.db.get_unknown_terms.return_value = []
        resp = client.get("/api/v1/admin/vocabulary/generate")
        assert resp.status_code == 200
        assert "attachment" in resp.headers["content-disposition"]
        assert "vocabulary.yaml" in resp.headers["content-disposition"]
        assert "products:" in resp.text


class TestRoleGating:
    @pytest.fixture
    def curator_client(self, client):
        client.app.state.settings.dev_user = "curator@redhat.com"
        return client

    def test_all_four_endpoints_reject_curators(self, curator_client):
        assert curator_client.get("/api/v1/admin/vocabulary").status_code == 403
        assert curator_client.get("/api/v1/admin/vocabulary/unknowns").status_code == 403
        assert curator_client.get("/api/v1/admin/vocabulary/generate").status_code == 403
        assert curator_client.put(
            "/api/v1/admin/vocabulary/unknowns/products/X", json={"action": "reject"}
        ).status_code == 403
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary_admin.py -v
```

Expected: `ImportError: cannot import name 'generate_vocabulary_yaml'`.

- [ ] **Step 3: Write `generate.py`**

Create `src/api/rcars/services/vocabulary/generate.py`:

```python
"""Emit a merged vocabulary.yaml — current file plus staged admin decisions.

Decisions are STAGED, not applied. The source of truth is a file in git; the
generated output is downloaded, committed, reviewed in a PR, and deployed. A
live ConfigMap mutation would be lost on the next deploy and would make the
database a second, divergent source of truth.
"""

from __future__ import annotations

from importlib.resources import files as _pkg_files
from typing import Any

import yaml

from rcars.services.vocabulary.models import DIMENSIONS, Vocabulary

_GENERATED_BANNER = (
    "# ─────────────────────────────────────────────────────────────────────────\n"
    "# GENERATED by the RCARS admin vocabulary page (RHDPCD-507).\n"
    "# Review, commit, open a PR, and deploy. Takes effect on the next rollout.\n"
    "# ─────────────────────────────────────────────────────────────────────────\n"
)


def _header_comment() -> str:
    """Preserve the packaged file's leading comment block.

    Everything the file explains about design intent lives in comments, and
    yaml.safe_dump would throw it away. Keep the header so the committed file
    stays readable.
    """
    path = _pkg_files("rcars.data").joinpath("vocabulary.yaml")
    lines: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            lines.append(line)
        else:
            break
    return "\n".join(lines).rstrip() + "\n\n"


def _entries_to_dicts(vocab: Vocabulary, dimension: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in vocab.entries(dimension):
        item: dict[str, Any] = {"name": entry.name, "aliases": list(entry.aliases)}
        if entry.search_terms:
            item["search_terms"] = list(entry.search_terms)
        if entry.is_tdp:
            item["is_tdp"] = True
        out.append(item)
    return out


def generate_vocabulary_yaml(vocab: Vocabulary, decisions: list[dict[str, Any]]) -> str:
    """Merge staged decisions into the loaded vocabulary and serialize.

    aliased  → term appended to the target entry's aliases
    promoted → term becomes a new canonical entry in that dimension
    rejected → term appended to ignored_terms[dimension]
    pending  → ignored
    """
    data: dict[str, Any] = {d: _entries_to_dicts(vocab, d) for d in DIMENSIONS}
    ignored: dict[str, list[str]] = {
        d: sorted(vocab.ignored_originals.get(d, ())) for d in DIMENSIONS
    }

    for decision in decisions:
        dimension = decision.get("dimension")
        term = (decision.get("term") or "").strip()
        status = decision.get("status")
        if dimension not in data or not term:
            continue

        if status == "aliased":
            target = decision.get("resolved_to")
            for entry in data[dimension]:
                if entry["name"] == target:
                    if term not in entry["aliases"]:
                        entry["aliases"].append(term)
                    break
        elif status == "promoted":
            if not any(e["name"] == term for e in data[dimension]):
                data[dimension].append({"name": term, "aliases": []})
        elif status == "rejected":
            if term not in ignored[dimension]:
                ignored[dimension].append(term)
                ignored[dimension].sort()

    data["action_verbs"] = {
        mode: {"valid": list(lists.get("valid", ())), "rejected": list(lists.get("rejected", ()))}
        for mode, lists in vocab.action_verbs.items()
    }
    data["content_modes"] = dict(vocab.content_modes)
    data["ignored_terms"] = ignored

    body = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return _header_comment() + _GENERATED_BANNER + "\n" + body
```

`_header_comment()` reads the packaged file rather than the active override, because the header is explanatory prose that belongs to the committed file. Everything that carries meaning — entries, ignored terms, modes — comes from the loaded `Vocabulary`, so an override's data is preserved even when its comments are not.

- [ ] **Step 4: Export the generator**

In `src/api/rcars/services/vocabulary/__init__.py`, add:

```python
from rcars.services.vocabulary.generate import generate_vocabulary_yaml
```

Add `"generate_vocabulary_yaml"` to `__all__`.

- [ ] **Step 5: Add the API schemas**

Append to `src/api/rcars/api/schemas.py`:

```python
# ── Controlled vocabulary (RHDPCD-507) ──


class VocabEntryOut(BaseModel):
    name: str
    aliases: list[str] = []
    search_terms: list[str] = []
    is_tdp: bool = False


class VocabularyResponse(BaseModel):
    dimensions: dict[str, list[VocabEntryOut]]
    content_modes: dict[str, str]
    ignored_terms: dict[str, list[str]]


class UnknownTerm(BaseModel):
    dimension: str
    term: str
    occurrences: int
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    example_content_id: str | None = None
    status: str
    resolved_to: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None


class UnknownTermsResponse(BaseModel):
    terms: list[UnknownTerm]


class ResolveUnknownTermRequest(BaseModel):
    action: Literal["alias", "promote", "reject"]
    resolved_to: str | None = None
```

Check the top of `schemas.py` for the existing imports; add `datetime` and `Literal` only if they are not already imported.

- [ ] **Step 6: Add the four endpoints**

Append to `src/api/rcars/api/routes/admin.py`:

```python
# ── Controlled vocabulary (RHDPCD-507) ──


@router.get(
    "/vocabulary",
    summary="Current controlled vocabulary",
    description=(
        "Returns the vocabulary as loaded by this process. Confirms what the running "
        "processes actually have, which matters when a ConfigMap override is in play. "
        "Admin-only."
    ),
    response_model=VocabularyResponse,
)
async def get_vocabulary(user: str = Depends(require_admin)):
    from rcars.services.vocabulary import DIMENSIONS, load_vocabulary

    vocab = load_vocabulary()
    return {
        "dimensions": {
            dimension: [
                {
                    "name": e.name,
                    "aliases": list(e.aliases),
                    "search_terms": list(e.search_terms),
                    "is_tdp": e.is_tdp,
                }
                for e in vocab.entries(dimension)
            ]
            for dimension in DIMENSIONS
        },
        "content_modes": dict(vocab.content_modes),
        "ignored_terms": {
            d: list(vocab.ignored_originals.get(d, ())) for d in DIMENSIONS
        },
    }


@router.get(
    "/vocabulary/unknowns",
    summary="Unknown-term review queue",
    description=(
        "Terms the normalizer could not match, one row per distinct term, ranked by "
        "occurrences. The unit of review is the term, not the item — an unknown term "
        "means the list is missing an entry. Admin-only."
    ),
    response_model=UnknownTermsResponse,
)
async def get_vocabulary_unknowns(
    request: Request,
    user: str = Depends(require_admin),
    status: str | None = Query("pending"),
    dimension: str | None = Query(None),
):
    db = request.app.state.db
    return {"terms": db.get_unknown_terms(status=status, dimension=dimension)}


@router.put(
    "/vocabulary/unknowns/{dimension}/{term:path}",
    summary="Record a decision on an unknown term",
    description=(
        "Stages an alias / promote / reject decision. Nothing about analysis changes "
        "until a regenerated vocabulary.yaml is committed and deployed. Admin-only."
    ),
    response_model=UnknownTerm,
)
async def resolve_vocabulary_unknown(
    dimension: str,
    term: str,
    body: ResolveUnknownTermRequest,
    request: Request,
    user: str = Depends(require_admin),
):
    from rcars.services.vocabulary import DIMENSIONS, load_vocabulary

    if dimension not in DIMENSIONS:
        raise HTTPException(status_code=400, detail=f"Unknown dimension '{dimension}'")

    if body.action == "alias":
        if not body.resolved_to:
            raise HTTPException(status_code=400, detail="alias requires resolved_to")
        if body.resolved_to not in load_vocabulary().canonical_names(dimension):
            raise HTTPException(
                status_code=400,
                detail=f"'{body.resolved_to}' is not a canonical name in {dimension}",
            )

    db = request.app.state.db
    row = db.resolve_unknown_term(dimension, term, body.action, body.resolved_to, user)
    if not row:
        raise HTTPException(status_code=404, detail=f"No queued term '{term}' in {dimension}")
    logger.info(
        "vocabulary_term_resolved", component="rcars", action="resolve_vocabulary_term",
        dimension=dimension, term=term, decision=body.action, resolved_by=user,
    )
    return row


@router.get(
    "/vocabulary/generate",
    summary="Download a merged vocabulary.yaml",
    description=(
        "Emits the complete merged file — current vocabulary plus all staged decisions — "
        "for download, commit, PR, and deploy. Admin-only."
    ),
    response_class=PlainTextResponse,
)
async def generate_vocabulary(request: Request, user: str = Depends(require_admin)):
    from rcars.services.vocabulary import generate_vocabulary_yaml, load_vocabulary

    db = request.app.state.db
    decisions = [
        row
        for row in db.get_unknown_terms(status=None)
        if row.get("status") in ("aliased", "promoted", "rejected")
    ]
    content = generate_vocabulary_yaml(load_vocabulary(), decisions)
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": 'attachment; filename="vocabulary.yaml"'},
    )
```

Add the imports at the top of `admin.py`: `from fastapi.responses import PlainTextResponse`, and extend the `rcars.api.schemas` import list with `VocabularyResponse, UnknownTermsResponse, UnknownTerm, ResolveUnknownTermRequest`.

- [ ] **Step 7: Run the tests to verify they pass**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/test_vocabulary_admin.py -v
```

Expected: PASS.

- [ ] **Step 8: Run the full backend suite**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/ -m "not integration" -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/api/rcars/services/vocabulary/ src/api/rcars/api/schemas.py src/api/rcars/api/routes/admin.py src/api/tests/test_vocabulary_admin.py
git commit -m "[RHDPCD-507] Add vocabulary admin endpoints and YAML generator"
```

---

### Task 8: `rcars vocab` CLI

**Files:**
- Modify: `src/api/rcars/cli.py`

**Interfaces:**
- Consumes: `db.get_unknown_terms()` from Task 3, `generate_vocabulary_yaml()` from Task 7.
- Produces: `rcars vocab unknowns`, `rcars vocab stage-rescan`.

`rcars vocab unknowns` exists so the queue is usable before the admin page ships and in scripted contexts. `rcars vocab stage-rescan` prepares the one-off Babylon re-scan in Task 11 — it is the tool that task drives.

- [ ] **Step 1: Add the `vocab` group and the `unknowns` command**

In `src/api/rcars/cli.py`, add after the `reporting-db` group block (which starts around line 657) — match the placement and style of `@cli.group(name="workload")`:

```python
@cli.group(name="vocab")
def vocab_group():
    """Controlled vocabulary — review queue and re-scan staging."""


@vocab_group.command("unknowns")
@click.option("--status", default="pending", show_default=True,
              help="Filter by status: pending, aliased, promoted, rejected, or 'all'")
@click.option("--dimension", default=None, help="Filter by dimension")
@click.option("--limit", type=int, default=50, show_default=True, help="Max rows to print")
def vocab_unknowns(status: str, dimension: str | None, limit: int):
    """List terms the normalizer could not match, ranked by occurrences."""
    db = get_db()
    try:
        rows = db.get_unknown_terms(
            status=None if status == "all" else status, dimension=dimension
        )
    finally:
        db.close()

    if not rows:
        _print("No unknown terms.")
        return

    _print(f"{len(rows)} unknown term(s), showing up to {limit}:")
    _print(f"{'DIMENSION':<12} {'COUNT':>6}  {'STATUS':<10} {'TERM':<40} EXAMPLE")
    for row in rows[:limit]:
        _print(
            f"{row['dimension']:<12} {row['occurrences']:>6}  {row['status']:<10} "
            f"{row['term'][:40]:<40} {row.get('example_content_id') or ''}"
        )
```

- [ ] **Step 2: Add the re-scan staging command**

Append to `src/api/rcars/cli.py`:

```python
@vocab_group.command("stage-rescan")
@click.option("--execute", is_flag=True, default=False,
              help="Actually stage the re-scan. Without this, only report the cost.")
def vocab_stage_rescan(execute: bool):
    """Stage the one-off Babylon re-scan that applies normalization corpus-wide.

    Marks every analyzed Babylon lab/demo stale and clears its content_hash, so
    `rcars scan` re-analyzes each DISTINCT showroom once. Clearing the hash
    matters: find_donor_by_content_hash would otherwise hand back the old,
    un-normalized analysis and the whole re-scan would be a no-op.

    Sibling propagation means the cost is one analysis per distinct showroom
    (same URL + resolved SHA), not per catalog item.
    """
    db = get_db()
    try:
        with db.pool.connection() as conn:
            cur = conn.execute("""
                SELECT COUNT(*) AS items,
                       COUNT(DISTINCT (COALESCE(bi.showroom_url_override, bi.showroom_url),
                                       COALESCE(bi.showroom_ref, ''))) AS showrooms
                FROM showroom_analysis sa
                JOIN content_entities ce ON ce.content_id = sa.content_id
                JOIN babylon_items bi ON bi.content_id = sa.content_id
                WHERE ce.retired_at IS NULL AND ce.content_type IN ('lab', 'demo')
            """)
            counts = cur.fetchone()

        _print(f"Analyzed Babylon items:     {counts['items']}")
        _print(f"Distinct showrooms (url+ref): {counts['showrooms']}  <- LLM calls")

        if not execute:
            _print("")
            _print("Dry run. Re-run with --execute to stage, then run: rcars scan")
            return

        with db.pool.connection() as conn:
            cur = conn.execute("""
                UPDATE showroom_analysis sa
                SET is_stale = TRUE, content_hash = NULL
                FROM content_entities ce
                WHERE ce.content_id = sa.content_id
                  AND ce.retired_at IS NULL
                  AND ce.content_type IN ('lab', 'demo')
            """)
            staged = cur.rowcount
            conn.commit()

        _print(f"Staged {staged} item(s) for re-analysis. Now run: rcars scan")
    finally:
        db.close()
```

- [ ] **Step 3: Verify the commands register**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && rcars vocab --help && rcars vocab unknowns --help && rcars vocab stage-rescan --help
```

Expected: all three print help without error, and `rcars vocab --help` lists `stage-rescan` and `unknowns`.

- [ ] **Step 4: Smoke-test against the dev database**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && rcars vocab unknowns && rcars vocab stage-rescan
```

Expected: `unknowns` prints "No unknown terms." (or a table); `stage-rescan` prints two counts and the dry-run notice without modifying anything. Requires `./dev-services.sh start`.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/cli.py
git commit -m "[RHDPCD-507] Add rcars vocab unknowns and stage-rescan commands"
```

---

### Task 9: Admin vocabulary page

**Files:**
- Create: `src/frontend/src/pages/VocabularyPage.tsx`
- Modify: `src/frontend/src/services/api.ts`
- Modify: `src/frontend/src/App.tsx`
- Modify: `src/frontend/src/components/RcarsSidebar.tsx`

**Interfaces:**
- Consumes: the four endpoints from Task 7.
- Produces: route `/system/vocabulary`, sidebar entry "Vocabulary" under System.

**Deliberately plain** — a table, three buttons, and a download. No new design language. Reuse the existing `admin-layout`, `admin-section`, `status-table`, `filter-select`, and `action-btn` classes exactly as `AdminRolesPage` does.

- [ ] **Step 1: Add the API client methods**

In `src/frontend/src/services/api.ts`, add these types near the other exported interfaces:

```ts
export interface VocabEntry {
  name: string
  aliases: string[]
  search_terms: string[]
  is_tdp: boolean
}

export interface VocabularyData {
  dimensions: Record<string, VocabEntry[]>
  content_modes: Record<string, string>
  ignored_terms: Record<string, string[]>
}

export interface UnknownTerm {
  dimension: string
  term: string
  occurrences: number
  first_seen: string | null
  last_seen: string | null
  example_content_id: string | null
  status: string
  resolved_to: string | null
  resolved_by: string | null
  resolved_at: string | null
}
```

Then add these methods to the `api` object, immediately after `deleteRoleAssignment` (around line 344):

```ts
  getVocabulary: () => request<VocabularyData>('/admin/vocabulary'),
  getVocabularyUnknowns: (status = 'pending') =>
    request<{ terms: UnknownTerm[] }>(
      `/admin/vocabulary/unknowns?status=${encodeURIComponent(status)}`
    ),
  resolveVocabularyTerm: (
    dimension: string,
    term: string,
    action: 'alias' | 'promote' | 'reject',
    resolvedTo?: string,
  ) =>
    request<UnknownTerm>(
      `/admin/vocabulary/unknowns/${encodeURIComponent(dimension)}/${encodeURIComponent(term)}`,
      { method: 'PUT', body: JSON.stringify({ action, resolved_to: resolvedTo ?? null }) },
    ),
  vocabularyGenerateUrl: () => '/api/v1/admin/vocabulary/generate',
```

`vocabularyGenerateUrl` returns a plain path rather than fetching: the generated file is a download, so the browser handles it via a link.

- [ ] **Step 2: Write the page**

Create `src/frontend/src/pages/VocabularyPage.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { api, type UnknownTerm, type VocabularyData } from '../services/api'

const DIMENSIONS = ['products', 'solutions', 'verticals', 'platforms', 'difficulty']

export function VocabularyPage() {
  const [vocab, setVocab] = useState<VocabularyData | null>(null)
  const [terms, setTerms] = useState<UnknownTerm[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [aliasTargets, setAliasTargets] = useState<Record<string, string>>({})
  const [openDimension, setOpenDimension] = useState('products')

  const load = () => {
    setLoading(true)
    Promise.all([api.getVocabulary(), api.getVocabularyUnknowns('pending')])
      .then(([v, u]) => { setVocab(v); setTerms(u.terms) })
      .catch(() => setError('Failed to load vocabulary.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const rowKey = (t: UnknownTerm) => `${t.dimension}::${t.term}`

  const resolve = async (
    t: UnknownTerm,
    action: 'alias' | 'promote' | 'reject',
  ) => {
    const key = rowKey(t)
    if (action === 'alias' && !aliasTargets[key]) {
      setError('Pick a canonical name to alias to.')
      return
    }
    setBusy(key)
    setError('')
    try {
      await api.resolveVocabularyTerm(t.dimension, t.term, action, aliasTargets[key])
      setTerms(prev => prev.filter(x => rowKey(x) !== key))
    } catch {
      setError(`Failed to record decision for '${t.term}'.`)
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <div className="admin-layout"><div style={{ color: 'var(--text-muted)' }}>Loading…</div></div>

  return (
    <div className="admin-layout admin-layout--wide">
      {error && (
        <div style={{ color: 'var(--score-red, #c9190b)', fontSize: '12px', marginBottom: '10px' }}>
          {error}
        </div>
      )}

      <div className="admin-section">
        <h3>Pending Terms</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
          Terms analysis produced that are not in the vocabulary. The item kept the value
          verbatim — the list is what is missing an entry. Decisions are staged: they take
          effect when a regenerated <code>vocabulary.yaml</code> is committed and deployed.
        </p>

        {terms.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Queue is empty.</div>
        ) : (
          <table className="status-table">
            <thead>
              <tr>
                <th>Dimension</th><th>Term</th><th>Count</th><th>Example</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {terms.map(t => {
                const key = rowKey(t)
                const canonicals = vocab?.dimensions[t.dimension] ?? []
                return (
                  <tr key={key}>
                    <td style={{ color: 'var(--text-muted)' }}>{t.dimension}</td>
                    <td>{t.term}</td>
                    <td>{t.occurrences}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                      {t.example_content_id ?? '—'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                        <select
                          className="filter-select"
                          style={{ width: 'auto', maxWidth: '220px' }}
                          value={aliasTargets[key] ?? ''}
                          onChange={e => setAliasTargets(prev => ({ ...prev, [key]: e.target.value }))}
                        >
                          <option value="">Alias to…</option>
                          {canonicals.map(c => (
                            <option key={c.name} value={c.name}>{c.name}</option>
                          ))}
                        </select>
                        <button
                          className="action-btn action-btn--primary"
                          disabled={busy === key}
                          onClick={() => resolve(t, 'alias')}
                        >
                          Alias
                        </button>
                        <button
                          className="action-btn"
                          disabled={busy === key}
                          onClick={() => resolve(t, 'promote')}
                        >
                          Promote
                        </button>
                        <button
                          className="action-btn"
                          disabled={busy === key}
                          onClick={() => resolve(t, 'reject')}
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}

        <div style={{ marginTop: '16px', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <a
            className="action-btn action-btn--primary"
            href={api.vocabularyGenerateUrl()}
            download="vocabulary.yaml"
          >
            Generate vocabulary.yaml
          </a>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Downloads the merged file. Commit it, open a PR, deploy.
          </span>
        </div>
      </div>

      <div className="admin-section">
        <h3>Current Vocabulary</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
          As loaded by this process — reflects any ConfigMap override in effect. Read-only;
          renaming or removing an entry is a direct edit to <code>vocabulary.yaml</code> via PR.
        </p>

        <div style={{ display: 'flex', gap: '6px', marginBottom: '12px', flexWrap: 'wrap' }}>
          {DIMENSIONS.map(d => (
            <button
              key={d}
              className={`action-btn${openDimension === d ? ' action-btn--primary' : ''}`}
              onClick={() => setOpenDimension(d)}
            >
              {d} ({vocab?.dimensions[d]?.length ?? 0})
            </button>
          ))}
        </div>

        <table className="status-table">
          <thead>
            <tr><th>Canonical name</th><th>Aliases</th><th>Search terms</th></tr>
          </thead>
          <tbody>
            {(vocab?.dimensions[openDimension] ?? []).map(e => (
              <tr key={e.name}>
                <td>
                  {e.name}
                  {e.is_tdp && (
                    <span style={{ marginLeft: '6px', fontSize: '11px', color: 'var(--text-muted)', border: '1px solid var(--border-default)', borderRadius: '3px', padding: '1px 5px' }}>
                      TDP
                    </span>
                  )}
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                  {e.aliases.join(', ') || '—'}
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                  {e.search_terms.join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {(vocab?.ignored_terms[openDimension]?.length ?? 0) > 0 && (
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px' }}>
            Ignored: {vocab?.ignored_terms[openDimension].join(', ')}
          </p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add the route**

In `src/frontend/src/App.tsx`, add the import next to the other page imports:

```tsx
import { VocabularyPage } from './pages/VocabularyPage'
```

Then add the route inside the `auth.isAdmin` block, immediately after the `/system/roles` route:

```tsx
                      <Route path="/system/vocabulary" element={<VocabularyPage />} />
```

- [ ] **Step 4: Add the sidebar entry**

In `src/frontend/src/components/RcarsSidebar.tsx`, add after the "Access Control" `NavLink` (around line 138):

```tsx
              <NavLink
                to="/system/vocabulary"
                className={({ isActive }) => `rcars-nav-item rcars-nav-item--indent${isActive ? ' active' : ''}`}
              >
                Vocabulary
              </NavLink>
```

- [ ] **Step 5: Typecheck and build**

```bash
cd /Users/natestephany/devel/rcars/src/frontend && npm run build
```

Expected: build succeeds with no TypeScript errors. If `npm run build` is not the project's typecheck script, check `package.json` scripts and run whichever one invokes `tsc`.

- [ ] **Step 6: Verify in the browser**

```bash
cd /Users/natestephany/devel/rcars && ./dev-services.sh start
```

Open http://localhost:3000/system/vocabulary. Confirm: the sidebar shows **Vocabulary** under System; the Current Vocabulary panel lists products with aliases and a TDP badge on the six TDP solutions; the dimension buttons switch tables; the queue shows "Queue is empty" on a fresh database. Then seed one row and re-check the actions:

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -c "
from rcars.config import Settings
from rcars.db.database import Database
db = Database(Settings().database_url)
db.record_unknown_term('products', 'Wombat Server 3000', example_content_id='babylon:lb1')
db.close()
"
```

Reload the page: the term appears with count 1. Use **Alias** with a selected canonical, confirm the row disappears, and confirm the download link returns a YAML file containing `Wombat Server 3000` in that product's aliases.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/pages/VocabularyPage.tsx src/frontend/src/services/api.ts src/frontend/src/App.tsx src/frontend/src/components/RcarsSidebar.tsx
git commit -m "[RHDPCD-507] Add admin vocabulary page"
```

---

### Task 10: ConfigMap mount via Ansible

**Files:**
- Modify: `ansible/templates/manifests-infra.yaml.j2`
- Modify: `ansible/templates/manifests-app.yaml.j2`

**Interfaces:**
- Consumes: `Settings.vocabulary_path` from Task 1.
- Produces: ConfigMap `{{ app_name }}-vocabulary`, mounted at `/opt/app-root/config/vocabulary.yaml` on the API, scan-worker, and recommend-worker deployments, with `RCARS_VOCABULARY_PATH` set to match.

All three deployments need it: the API serves the admin page, scan-worker runs analysis, and recommend-worker runs Advisor query expansion.

- [ ] **Step 1: Add the ConfigMap**

In `ansible/templates/manifests-infra.yaml.j2`, add before the `# ServiceAccount for OAuth proxy` block (around line 197):

```yaml
---
# Controlled vocabulary — RHDPCD-507
# Rendered from the in-repo file so git stays the source of truth. Ops can
# `oc edit configmap` for an emergency term patch, but a change needs a rolling
# restart of api + scan-worker + recommend-worker to take effect, and the next
# deploy resets it to the committed file.
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ app_name }}-vocabulary
  labels:
    app: {{ app_name }}
data:
  vocabulary.yaml: |
{{ lookup('file', playbook_dir + '/../src/api/rcars/data/vocabulary.yaml') | indent(4, true) }}
```

- [ ] **Step 2: Mount it on all three deployments**

In `ansible/templates/manifests-app.yaml.j2`, for **each** of the three deployments (API around line 165, scan-worker around line 330, recommend-worker around line 478), add to that container's `volumeMounts:` list:

```yaml
            - name: vocabulary
              mountPath: /opt/app-root/config/vocabulary.yaml
              subPath: vocabulary.yaml
              readOnly: true
```

and to the same deployment's `volumes:` list (around lines 211, 374, 514):

```yaml
        - name: vocabulary
          configMap:
            name: {{ app_name }}-vocabulary
```

These are unconditional — no `{% if %}` guard — because the file is always present in the repo.

- [ ] **Step 3: Set the env var on all three deployments**

For each of the three containers, add to its `env:` list:

```yaml
            - name: RCARS_VOCABULARY_PATH
              value: /opt/app-root/config/vocabulary.yaml
```

Match the surrounding indentation exactly; find an existing plain `value:` env entry in each deployment and place this next to it.

- [ ] **Step 4: Verify the templates render**

```bash
cd /Users/natestephany/devel/rcars && ansible-playbook ansible/deploy.yml -e env=dev --tags apply-config --check --diff
```

Expected: renders and reports what would change, with no Jinja or YAML errors. If `--check` is not supported by a task in that tag, run the render step alone and inspect the output; the goal is only to confirm the templates are valid.

- [ ] **Step 5: Commit**

```bash
git add ansible/templates/manifests-infra.yaml.j2 ansible/templates/manifests-app.yaml.j2
git commit -m "[RHDPCD-507] Mount vocabulary.yaml as a ConfigMap on all three deployments"
```

---

### Task 11: Deploy to dev and run the one-off Babylon re-scan

**Files:** none — this task deploys and verifies.

**Interfaces:**
- Consumes: everything above.
- Produces: a dev environment running the vocabulary, and a normalized Babylon corpus with `recommender_audience_json` populated.

The re-scan is in scope. Without it, normalization would only reach items that happen to be re-scanned for unrelated reasons, and the new column would sit empty indefinitely.

- [ ] **Step 1: Run the full test suite one more time**

```bash
source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/ -m "not integration" -q
```

Expected: PASS. Do not proceed on a failure — report it instead.

- [ ] **Step 2: Ask the repo owner to review and push**

Show the branch, the commits, and the destination, then wait for approval. Do not push without it.

```bash
cd /Users/natestephany/devel/rcars && git log --oneline main..HEAD && git status -sb
```

- [ ] **Step 3: Deploy to dev**

This touches the API, the workers, and the frontend, so it is a full deploy.

```bash
cd /Users/natestephany/devel/rcars && ansible-playbook ansible/deploy.yml -e env=dev --tags full
```

Expected: builds succeed, `rcars init-db` runs, smoke test passes.

- [ ] **Step 4: Verify the vocabulary loaded in the running pods**

```bash
oc logs -l app=rcars,component=scan-worker --tail=200 | grep vocabulary_loaded
```

Expected: one `vocabulary_loaded path=/opt/app-root/config/vocabulary.yaml products=44 ...` line. If `path=` shows the packaged path instead, `RCARS_VOCABULARY_PATH` did not reach that deployment — fix Task 10 before continuing.

- [ ] **Step 5: Confirm the re-scan cost before running it**

```bash
oc exec deploy/rcars-api -- rcars vocab stage-rescan
```

Expected: prints the analyzed-item count and the distinct-showroom count. The second number is the number of LLM calls. **Show it to the repo owner and get agreement before executing** — this is the spec's Next Step 3.

- [ ] **Step 6: Stage and run the re-scan**

```bash
oc exec deploy/rcars-api -- rcars vocab stage-rescan --execute
oc exec deploy/rcars-api -- rcars scan
```

Expected: `stage-rescan --execute` reports the number staged; `scan` analyzes one showroom per distinct URL+SHA group and propagates to siblings.

- [ ] **Step 7: Verify normalization and the new column landed**

```bash
oc exec deploy/rcars-api -- psql "$RCARS_DATABASE_URL" -c "
SELECT COUNT(*) FILTER (WHERE recommender_audience_json IS NOT NULL) AS with_audience,
       COUNT(*) AS total
FROM showroom_analysis sa
JOIN content_entities ce ON ce.content_id = sa.content_id
WHERE ce.retired_at IS NULL AND ce.content_type IN ('lab','demo');"
```

Expected: `with_audience` is close to `total`. Items still at zero are ones the scan skipped (published duplicates, retired, failed clones) — check `scan_status` on those before treating it as a bug.

Then confirm product names collapsed:

```bash
oc exec deploy/rcars-api -- psql "$RCARS_DATABASE_URL" -c "
SELECT p AS product, COUNT(*)
FROM showroom_analysis, jsonb_array_elements_text(products_json) p
GROUP BY p ORDER BY COUNT(*) DESC LIMIT 30;"
```

Expected: canonical names dominate; near-duplicates like bare `OpenShift` alongside `Red Hat OpenShift Container Platform` are gone.

- [ ] **Step 8: Work the queue once**

Open `/system/vocabulary` on the dev route. Review the pending terms the re-scan produced, resolve the obvious ones, download the generated `vocabulary.yaml`, and diff it against the in-repo file:

```bash
diff <(cat ~/Downloads/vocabulary.yaml) src/api/rcars/data/vocabulary.yaml
```

Expected: the diff contains only the staged decisions. Commit the regenerated file if the decisions are right — that closes the loop the whole design is built around.

- [ ] **Step 9: Report**

Report to the repo owner: distinct-showroom count and actual LLM calls, how many items now carry `recommender_audience_json`, the top pending terms remaining, and anything that did not work.

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
| ---------------- | ---- |
| Finalize `vocabulary.yaml` (products + search_terms, solutions with TDP, verticals, platforms, difficulty, action verbs, content_modes) | 1 |
| `vocabulary.py` loader + cache + fail-fast validation | 1 |
| Shared `render_vocabulary_block()`; products + verb hints in the prompt | 4 |
| `normalize_analysis()` — dimension-driven ladder + topic squash dedup, called once after parse | 2, 5 |
| `vocabulary_unknown_terms` table + rung-4 upsert; `ignored_terms` round-trip | 3, 7 |
| Admin page at `/system/vocabulary` | 9 |
| Four admin endpoints + `rcars vocab unknowns` CLI | 7, 8 |
| `recommender_audience_json` column + field in the prompt | 3, 4, 5 |
| Merge `product-terms.yaml`, refactor `_expand_query_terms()`, delete the file | 6 |
| ConfigMap mount on all three deployments | 10 |
| One-off Babylon re-scan | 8 (tooling), 11 (execution) |
| Every row of the spec's Testing table | 1, 2, 3, 4, 6, 7 |

The spec's `architecture_analyze.txt` injection is explicitly RHDPCD-28's, not this plan's — the renderer is built source-agnostically so that spec adds one call.

**Deviations, all deliberate and noted inline:**
1. `services/vocabulary.py` is a package, not a module. The import path in the spec (`from rcars.services.vocabulary import load_vocabulary`) is unchanged, and it matches `services/recommender/` and `services/chat/`.
2. `normalize_analysis()` takes two extra optional keyword arguments (`db`, `content_id`) so it is pure and testable without a database. Behaviour with `db=None` is exactly the spec's.
3. `rcars vocab stage-rescan` is added beyond the spec's `rcars vocab unknowns`, because the re-scan is in scope and needs a tool. It clears `content_hash` as well as setting `is_stale`, without which `find_donor_by_content_hash` would hand back un-normalized analyses and the re-scan would be a no-op — a trap the spec does not mention.
4. The donor-reuse path in `analyze_showroom` also normalizes, so a borrowed analysis from before a vocabulary change is corrected rather than propagated stale.
