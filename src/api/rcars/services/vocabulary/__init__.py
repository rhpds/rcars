"""Controlled vocabulary — one list, two consumers (analysis + query expansion)."""

from rcars.services.vocabulary.loader import load_vocabulary
from rcars.services.vocabulary.normalize import (
    FIELD_MAP,
    dedup_topics,
    normalize_analysis,
    snap_term,
)
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
    "FIELD_MAP",
    "VocabEntry",
    "Vocabulary",
    "VocabularyError",
    "dedup_topics",
    "load_vocabulary",
    "normalize_analysis",
    "snap_term",
    "squash_key",
]
