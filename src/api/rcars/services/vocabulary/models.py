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
