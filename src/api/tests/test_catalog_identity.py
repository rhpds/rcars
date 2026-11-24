"""Card identity (RHDPCD-2297 PR 2): the pure rules, no database."""
import itertools

import pytest

from rcars.services.catalog_identity import (
    cards_sharing_a_family, collapse_to_cards, family_violations, merge_stage_copies,
)


def hit(content_id, score=0.9, stage="prod", stage_key=None, content_hash=None):
    return {"content_id": content_id, "best_similarity": score, "stage": stage, "status": stage,
            "stage_key": stage_key or content_id.rsplit(".", 1)[0], "content_hash": content_hash}


def row(content_id, stage="prod", stage_key=None):
    """A virtual CI row from the eligibility query (no similarity)."""
    return {k: v for k, v in hit(content_id, stage=stage, stage_key=stage_key).items()
            if k != "best_similarity"}


def ids(cards):
    return [c["content_id"] for c in cards]


def collapse(hits, covers=None, eligible=(), stages=("prod",), hashes=None):
    cards, stats = collapse_to_cards(
        hits, covers or {}, {r["content_id"]: r for r in eligible}, list(stages),
        lambda cid: (hashes or {}).get(cid))
    return cards, stats


# ── empty family tables ──

def test_no_family_data_changes_nothing():
    cards, stats = collapse([hit("babylon:a.prod"), hit("babylon:b.prod", 0.8)])
    assert ids(cards) == ["babylon:a.prod", "babylon:b.prod"]
    assert stats.dropped_members == [] and stats.kept_members == []


# ── member vs virtual CI ──

def test_member_is_replaced_by_its_eligible_virtual_ci_keeping_the_score():
    cards, stats = collapse([hit("babylon:lab.prod", 0.8)],
                            {"babylon:lab.prod": ["babylon:published.lab.prod"]},
                            [row("babylon:published.lab.prod")])
    assert ids(cards) == ["babylon:published.lab.prod"]
    assert cards[0]["best_similarity"] == 0.8
    assert cards[0]["via_content_id"] == "babylon:lab.prod"
    assert stats.dropped_members == [("babylon:lab.prod", ["babylon:published.lab.prod"])]


def test_member_and_its_virtual_ci_both_hit_show_once_with_best_score():
    cards, _ = collapse([hit("babylon:published.lab.prod", 0.7), hit("babylon:lab.prod", 0.9)],
                        {"babylon:lab.prod": ["babylon:published.lab.prod"]},
                        [row("babylon:published.lab.prod")])
    assert ids(cards) == ["babylon:published.lab.prod"]
    assert cards[0]["best_similarity"] == 0.9


def test_member_shows_when_no_covering_virtual_ci_is_eligible():
    cards, stats = collapse([hit("babylon:lab.prod")],
                            {"babylon:lab.prod": ["babylon:published.lab.prod"]}, [])
    assert ids(cards) == ["babylon:lab.prod"]
    assert stats.kept_members == [("babylon:lab.prod", ["babylon:published.lab.prod"])]


def test_field_asset_one_component_two_eligible_virtual_cis_gives_two_cards():
    covers = {"babylon:fsc.prod": ["babylon:published.fa-shared.prod", "babylon:published.fa.prod"]}
    cards, _ = collapse([hit("babylon:fsc.prod")], covers,
                        [row("babylon:published.fa.prod"), row("babylon:published.fa-shared.prod")])
    assert sorted(ids(cards)) == ["babylon:published.fa-shared.prod", "babylon:published.fa.prod"]


def test_field_asset_only_one_virtual_ci_eligible_gives_one_card():
    covers = {"babylon:fsc.prod": ["babylon:published.fa-shared.prod", "babylon:published.fa.prod"]}
    cards, _ = collapse([hit("babylon:fsc.prod")], covers, [row("babylon:published.fa.prod")])
    assert ids(cards) == ["babylon:published.fa.prod"]


def test_field_asset_no_virtual_ci_eligible_member_shows():
    covers = {"babylon:fsc.prod": ["babylon:published.fa-shared.prod", "babylon:published.fa.prod"]}
    assert ids(collapse([hit("babylon:fsc.prod")], covers, [])[0]) == ["babylon:fsc.prod"]


def test_four_level_chain_every_member_collapses_to_the_one_virtual_ci():
    covers = {m: ["babylon:published.x.prod"] for m in ("babylon:wrapper.prod", "babylon:lab.prod")}
    cards, _ = collapse([hit("babylon:lab.prod", 0.9), hit("babylon:wrapper.prod", 0.85),
                         hit("babylon:pool.prod", 0.8)],
                        covers, [row("babylon:published.x.prod")])
    assert ids(cards) == ["babylon:published.x.prod", "babylon:pool.prod"]


def test_virtual_ci_without_anchor_has_no_family_so_nothing_collapses():
    cards, _ = collapse([hit("babylon:published.noanchor.prod"), hit("babylon:sandbox.prod", 0.8)])
    assert ids(cards) == ["babylon:published.noanchor.prod", "babylon:sandbox.prod"]


def test_two_members_of_one_virtual_ci_give_one_card_with_the_best_member_score():
    covers = {"babylon:cnv.prod": ["babylon:published.v.prod"], "babylon:aws.prod": ["babylon:published.v.prod"]}
    cards, _ = collapse([hit("babylon:cnv.prod", 0.7), hit("babylon:aws.prod", 0.9)], covers,
                        [row("babylon:published.v.prod")])
    assert ids(cards) == ["babylon:published.v.prod"]
    assert cards[0]["best_similarity"] == 0.9 and cards[0]["via_content_id"] == "babylon:aws.prod"


# ── stage copies ──

def test_single_stage_never_merges_stage_copies():
    hits = [hit("babylon:x.prod", 0.9, "prod", "x", "h"), hit("babylon:x.dev", 0.9, "dev", "x", "h")]
    assert ids(collapse(hits, stages=("prod",))[0]) == ["babylon:x.prod", "babylon:x.dev"]


def test_several_stages_same_content_keeps_highest_stage_and_best_score():
    hits = [hit("babylon:x.dev", 0.95, "dev", "x", "h"), hit("babylon:x.prod", 0.9, "prod", "x", "h")]
    cards, stats = collapse(hits, stages=("prod", "dev"))
    assert ids(cards) == ["babylon:x.prod"]
    assert cards[0]["best_similarity"] == 0.95
    assert stats.merged_stage_copies == [("babylon:x.dev", "babylon:x.prod")]


def test_several_stages_different_content_stay_separate():
    hits = [hit("babylon:x.prod", 0.9, "prod", "x", "h1"), hit("babylon:x.dev", 0.8, "dev", "x", "h2")]
    assert ids(collapse(hits, stages=("prod", "dev"))[0]) == ["babylon:x.prod", "babylon:x.dev"]


@pytest.mark.parametrize("empty", [None, ""])
def test_missing_content_hash_never_merges(empty):
    hits = [hit("babylon:x.prod", 0.9, "prod", "x", empty), hit("babylon:x.dev", 0.8, "dev", "x", empty)]
    assert len(collapse(hits, stages=("prod", "dev"))[0]) == 2


def test_dev_and_event_only_keep_the_event_copy():
    hits = [hit("babylon:x.dev", 0.9, "dev", "x", "h"), hit("babylon:x.event", 0.8, "event", "x", "h")]
    assert ids(collapse(hits, stages=("event", "dev"))[0]) == ["babylon:x.event"]


def test_stage_copies_are_never_merged_by_name_alone():
    # Same stage_key, no content_hash on either: two cards.
    hits = [hit("babylon:x.prod", stage="prod", stage_key="x"), hit("babylon:x.dev", stage="dev", stage_key="x")]
    assert len(collapse(hits, stages=("prod", "dev"))[0]) == 2


def test_different_stage_keys_with_equal_hash_never_merge():
    hits = [hit("babylon:a.prod", 0.9, "prod", "a", "h"), hit("babylon:b.dev", 0.8, "dev", "b", "h")]
    assert len(collapse(hits, stages=("prod", "dev"))[0]) == 2


def test_virtual_ci_stage_copies_merge_on_the_displayed_content_hash():
    covers = {"babylon:lab.prod": ["babylon:published.v.prod"], "babylon:lab.dev": ["babylon:published.v.dev"]}
    cards, _ = collapse(
        [hit("babylon:lab.prod", 0.9), hit("babylon:lab.dev", 0.8, "dev")], covers,
        [row("babylon:published.v.prod"), row("babylon:published.v.dev", "dev")], ("prod", "dev"),
        hashes={"babylon:published.v.prod": "h", "babylon:published.v.dev": "h"})
    assert ids(cards) == ["babylon:published.v.prod"]


def test_virtual_ci_stage_copies_with_different_content_stay_two_cards():
    covers = {"babylon:lab.prod": ["babylon:published.v.prod"], "babylon:lab.dev": ["babylon:published.v.dev"]}
    cards, _ = collapse(
        [hit("babylon:lab.prod", 0.9), hit("babylon:lab.dev", 0.8, "dev")], covers,
        [row("babylon:published.v.prod"), row("babylon:published.v.dev", "dev")], ("prod", "dev"),
        hashes={"babylon:published.v.prod": "h1", "babylon:published.v.dev": "h2"})
    assert sorted(ids(cards)) == ["babylon:published.v.dev", "babylon:published.v.prod"]


def test_merge_stage_copies_is_independent_of_input_order():
    base = [hit("babylon:x.dev", 0.9, "dev", "x", "h"), hit("babylon:x.event", 0.8, "event", "x", "h"),
            hit("babylon:x.prod", 0.7, "prod", "x", "h")]
    for perm in itertools.permutations(base):
        merged, _ = merge_stage_copies(list(perm), lambda cid: None)
        assert [c["content_id"] for c in merged] == ["babylon:x.prod"]


# ── the invariant ──

def test_family_violations_flags_a_member_next_to_its_virtual_ci():
    covers = {"babylon:lab.prod": ["babylon:published.lab.prod"]}
    assert family_violations(["babylon:published.lab.prod", "babylon:lab.prod"], covers) == {
        1: "covered_by_card:babylon:published.lab.prod"}


def test_family_violations_flags_duplicate_content_ids():
    assert family_violations(["babylon:a.prod", "babylon:a.prod"], {}) == {1: "duplicate_content_id"}


def test_family_violations_allows_a_member_whose_virtual_ci_is_absent():
    covers = {"babylon:lab.prod": ["babylon:published.lab.prod"]}
    assert family_violations(["babylon:lab.prod", "babylon:other.prod"], covers) == {}


def test_family_violations_two_virtual_cis_over_one_component_are_fine():
    covers = {"babylon:fsc.prod": ["babylon:published.a.prod", "babylon:published.b.prod"]}
    assert family_violations(["babylon:published.a.prod", "babylon:published.b.prod"], covers) == {}


# ── smoke check: do two cards share a family? ──

def fam(virtual, member):
    return {"virtual_content_id": virtual, "member_content_id": member}


def test_cards_sharing_a_family_flags_member_next_to_its_virtual_ci():
    rows = [fam("v", "m")]
    assert cards_sharing_a_family(["v", "m"], rows) == [("v", "m", "v")]


def test_cards_sharing_a_family_flags_two_members_of_one_virtual_ci():
    rows = [fam("v", "m1"), fam("v", "m2")]
    assert cards_sharing_a_family(["m1", "m2"], rows) == [("m1", "m2", "v")]


def test_two_virtual_cis_over_one_shared_component_do_not_share_a_family():
    rows = [fam("va", "fsc"), fam("vb", "fsc")]
    assert cards_sharing_a_family(["va", "vb"], rows) == []


def test_unrelated_cards_share_nothing():
    assert cards_sharing_a_family(["a", "b"], [fam("v", "m")]) == []
