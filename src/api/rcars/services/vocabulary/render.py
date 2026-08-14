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
