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
            log.exception("vocabulary: failed to record unknown term %s/%s", dimension, term)
