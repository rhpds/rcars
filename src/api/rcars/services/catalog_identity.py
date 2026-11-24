"""The only place that decides when two Advisor hits are "the same card".

Three rules, all here. Nothing else in the Advisor path decides "same card".

1. **Family.** A virtual CI (``published.*``) and the components down to its
   content anchor form one family (table ``catalog_family_members``, written at
   catalog refresh). A member component is dropped when at least one virtual CI
   that covers it is *eligible*: it would itself pass the same filters as a card
   in this request. If no covering virtual CI is eligible the member may show.
   Each eligible virtual CI is its own card, even when they share a component.
2. **Stage copies.** Never merged by name. Merged only when the user selected
   several stages AND the copies (same ``stage_key``) have the same non-empty
   ``content_hash`` (the "same content" rule in ``analysis_identity``). The highest
   stage wins: prod > event > dev. Different content stays as separate cards.
3. **Invariant.** No two final cards share a content_id, and no card is a member
   of another card's family.

A fourth question lives here too: "similar to LB1234" must not return the item
asked about (RHDPCD-2298). ``exclusion_set_for`` answers it from the same family
table and the same ``stage_key``; no name matching.

Everything below is pure: rows in, rows out. The database lookups (family table,
eligibility) live in ``Database`` and are wired up in ``recommender.vector_search``.
"""
from dataclasses import dataclass, field
from typing import Callable

from rcars.services.analysis_identity import EMPTY_CONTENT_HASH

STAGE_RANK = {"prod": 3, "event": 2, "dev": 1}


@dataclass
class CollapseStats:
    """What the collapse did, for the per-query log line."""

    dropped_members: list[tuple[str, list[str]]] = field(default_factory=list)  # member, eligible virtual CIs
    kept_members: list[tuple[str, list[str]]] = field(default_factory=list)  # member, covering CIs (none eligible)
    merged_stage_copies: list[tuple[str, str]] = field(default_factory=list)  # dropped copy, kept copy


def _best(rows: dict[str, dict], row: dict, score: float, via: str | None) -> None:
    """Keep the best-scoring version of a card in ``rows``."""
    existing = rows.get(row["content_id"])
    if existing is None or score > existing["best_similarity"]:
        rows[row["content_id"]] = {**row, "best_similarity": score, "via_content_id": via}


def collapse_to_cards(
    hits: list[dict],
    covers: dict[str, list[str]],
    eligible_rows: dict[str, dict],
    stages: list[str],
    content_hash_of: Callable[[str], str | None],
) -> tuple[list[dict], CollapseStats]:
    """Turn vector hits into one card per family and per stage-copy group.

    hits: search rows (``content_id``, ``best_similarity``, ``stage``, ``stage_key``,
        ``content_hash``).
    covers: member content_id -> virtual CI content_ids covering it. Empty when no
        families are stored: nothing collapses.
    eligible_rows: virtual CI content_id -> row, only those that pass the card
        filters in this request.
    stages: the stages the user selected.
    content_hash_of: content_id -> hash of its displayed analysis (used only for
        stage-copy merging, only when needed).

    Returns cards sorted by score, best first, plus the stats.
    """
    stats = CollapseStats()
    cards: dict[str, dict] = {}
    hit_by_id = {hit["content_id"]: hit for hit in hits}
    for hit in hits:
        cid, score = hit["content_id"], hit["best_similarity"]
        covering = covers.get(cid, [])
        eligible = [v for v in covering if v in eligible_rows]
        if not eligible:
            if covering:
                stats.kept_members.append((cid, covering))
            _best(cards, hit, score, None)
            continue
        stats.dropped_members.append((cid, eligible))
        for vci in eligible:
            # A virtual CI that was itself a hit keeps its own row (its own analysis hash).
            _best(cards, hit_by_id.get(vci) or eligible_rows[vci], score, cid)

    merged, merged_pairs = list(cards.values()), []
    if len(stages) > 1:
        merged, merged_pairs = merge_stage_copies(merged, content_hash_of)
    stats.merged_stage_copies = merged_pairs
    merged.sort(key=lambda card: -card["best_similarity"])
    return merged, stats


def merge_stage_copies(
    cards: list[dict], content_hash_of: Callable[[str], str | None],
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Merge copies of one CI across stages when their content is the same.

    Same ``stage_key`` and same non-empty ``content_hash``. The highest stage stays
    and takes the best score of the group. Without a hash nothing merges.
    """
    by_key: dict[str, list[dict]] = {}
    for card in cards:
        if card.get("stage_key"):
            by_key.setdefault(card["stage_key"], []).append(card)

    dropped: dict[str, dict] = {}  # content_id of the dropped copy -> the card that replaces it
    kept_scores: dict[str, float] = {}
    for group in by_key.values():
        if len(group) < 2:
            continue
        by_hash: dict[str, list[dict]] = {}
        for card in group:
            content_hash = card.get("content_hash") or content_hash_of(card["content_id"])
            if content_hash and content_hash != EMPTY_CONTENT_HASH:
                by_hash.setdefault(content_hash, []).append(card)
        for same_content in by_hash.values():
            if len(same_content) < 2:
                continue
            winner = max(same_content, key=lambda c: STAGE_RANK.get(c.get("stage") or c.get("status"), 0))
            kept_scores[winner["content_id"]] = max(c["best_similarity"] for c in same_content)
            for card in same_content:
                if card is not winner:
                    dropped[card["content_id"]] = winner

    result = []
    for card in cards:
        if card["content_id"] in dropped:
            continue
        if card["content_id"] in kept_scores:
            card = {**card, "best_similarity": kept_scores[card["content_id"]]}
        result.append(card)
    return result, [(loser, winner["content_id"]) for loser, winner in dropped.items()]


def family_violations(content_ids: list[str], covers: dict[str, list[str]]) -> dict[int, str]:
    """Positions in ``content_ids`` that break the card invariant, with the reason.

    A repeated content_id is flagged at its later positions. A card whose covering
    virtual CI is also a card is flagged at the member (the virtual CI stays).
    """
    present = set(content_ids)
    bad: dict[int, str] = {}
    seen: set[str] = set()
    for index, cid in enumerate(content_ids):
        if cid in seen:
            bad[index] = "duplicate_content_id"
            continue
        seen.add(cid)
        shown = [v for v in covers.get(cid, []) if v in present and v != cid]
        if shown:
            bad[index] = f"covered_by_card:{shown[0]}"
    return bad


def enforce_card_invariant(candidates: list, db) -> list:
    """Drop cards that break the invariant; log each. Normally drops nothing.

    The collapse in ``vector_search`` already guarantees this. It runs again at
    the end of the pipeline, after triage and boosts, so a later change cannot
    silently bring back a member next to its virtual CI. Works on anything with a
    ``content_id`` attribute.
    """
    import structlog

    ids = [c.content_id for c in candidates]
    bad = family_violations(ids, db.get_family_covers(ids))
    if not bad:
        return candidates
    for index, reason in bad.items():
        structlog.get_logger().error(
            "card_invariant_violation", component="rcars", action="card_invariant_drop",
            content_id=ids[index], reason=reason)
    return [c for i, c in enumerate(candidates) if i not in bad]


def cards_sharing_a_family(content_ids: list[str], family_rows: list[dict]) -> list[tuple[str, str, str]]:
    """Pairs of cards that break the family rule, as (virtual CI, member, virtual CI).

    Used by the deploy smoke check on a finished result. It is the same rule as
    ``family_violations``: a card is a violation when a virtual CI that covers it is
    also a card. Two members of a virtual CI that is not a card are fine (the
    virtual CI was not eligible). Two virtual CIs over one component are fine: each
    is its own family.
    """
    covers: dict[str, list[str]] = {}
    for row in family_rows:
        covers.setdefault(row["member_content_id"], []).append(row["virtual_content_id"])
    bad = family_violations(content_ids, covers)
    return [(reason.split(":", 1)[1], content_ids[index], reason.split(":", 1)[1])
            for index, reason in sorted(bad.items()) if reason.startswith("covered_by_card:")]


def family_exclusion_core(referenced_id: str, family_rows: list[dict]) -> set[str]:
    """The referenced item plus the family-linked items that are "the same thing".

    Referenced item R is always in. When R is a virtual CI, its members are in. When
    R is a member, every virtual CI that covers it is in (a component shared by two
    virtual CIs excludes both). Other members of those virtual CIs are not: they are
    different components. ``family_rows`` are ``catalog_family_members`` rows that
    touch R. Stage copies are added by ``exclusion_set_for``.
    """
    core = {referenced_id}
    for row in family_rows:
        if row["virtual_content_id"] == referenced_id:
            core.add(row["member_content_id"])
        if row["member_content_id"] == referenced_id:
            core.add(row["virtual_content_id"])
    return core


def exclusion_set_for(db, referenced_id: str) -> set[str]:
    """Everything "similar to <referenced_id>" must never show.

    ``family_exclusion_core`` plus the stage copies (same ``stage_key``, any stage,
    whatever stages the user selected) of every item in it. With empty family tables
    this is the item and its stage copies only.
    """
    core = family_exclusion_core(referenced_id, db.get_family_rows([referenced_id]))
    return db.get_stage_copy_ids(core)
