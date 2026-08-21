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
    import os

    configured = os.environ.get("RCARS_VOCABULARY_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(str(_pkg_files("rcars.data").joinpath("vocabulary.yaml")))


def _as_tuple(value: Any, field: str = "?") -> tuple[str, ...]:
    if not value:
        return ()
    if not isinstance(value, list):
        raise VocabularyError(f"{field}: expected a list, got {type(value).__name__} {value!r}")
    result = []
    for v in value:
        if not isinstance(v, str) or not v.strip():
            raise VocabularyError(f"{field}: entries must be non-empty strings, got {v!r}")
        result.append(v)
    return tuple(result)


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
                aliases=_as_tuple(item.get("aliases"), f"{dimension}[{item['name']!r}].aliases"),
                search_terms=_as_tuple(item.get("search_terms"), f"{dimension}[{item['name']!r}].search_terms"),
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
    squash: dict[str, str] = {}
    for e in entries:
        sq = squash_key(e.name)
        existing = squash.get(sq)
        if existing and existing != e.name:
            raise VocabularyError(
                f"{dimension}: canonical '{e.name}' squash-collides with '{existing}'"
            )
        squash[sq] = e.name

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
            sq = squash_key(alias)
            existing_sq = squash.get(sq)
            if existing_sq and existing_sq != entry.name:
                raise VocabularyError(
                    f"{dimension}: alias '{alias}' on '{entry.name}' squash-collides with "
                    f"existing owner '{existing_sq}'"
                )
            squash[sq] = entry.name

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
            "valid": _as_tuple((lists or {}).get("valid"), f"action_verbs[{mode!r}].valid"),
            "rejected": _as_tuple((lists or {}).get("rejected"), f"action_verbs[{mode!r}].rejected"),
        }
        for mode, lists in (data.get("action_verbs") or {}).items()
    }

    ignored_raw = data.get("ignored_terms") or {}
    ignored_originals = {
        dimension: _as_tuple(ignored_raw.get(dimension), f"ignored_terms[{dimension!r}]") for dimension in DIMENSIONS
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
