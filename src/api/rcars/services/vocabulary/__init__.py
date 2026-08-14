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
