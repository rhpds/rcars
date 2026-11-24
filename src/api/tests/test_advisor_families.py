"""Advisor card identity against the database (RHDPCD-2297 PR 2).

Invariant: no two final cards share a family. Fixtures cover 4-level chains,
shared members, no-anchor virtual CIs, stage copies with equal and different
content, and virtual CIs that are not eligible (retired, retirement started,
wrong stage, ZT excluded).
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcars.services.catalog_identity import enforce_card_invariant
from rcars.services.recommender import vector_search
from tests.showroom_helpers import db  # noqa: F401  (fixture)

P = "isolation-test."


def cid(name):
    return f"babylon:{P}{name}"


def item(db, name, *, stage=None, analysis=True, content_hash="h-" , ci_extra=None):
    """A catalog item; with analysis=True it also has an analysis row (and so can be a hit)."""
    stage = stage or name.rsplit(".", 1)[-1]
    content_id = db.upsert_babylon_catalog_item({
        "ci_name": f"{P}{name}", "stage": stage, "display_name": name,
        "showroom_url": "https://github.com/example/content", "showroom_ref": "main",
        **(ci_extra or {})})
    if analysis:
        db.upsert_showroom_analysis({"content_id": content_id, "summary": f"About {name}", "modules_json": [],
                                     "content_hash": content_hash if content_hash != "h-" else f"h-{name}"})
        db.set_scan_status(content_id, "success")
    return content_id


def link(db, virtual, member, role="anchor", depth=1):
    with db.pool.connection() as conn:
        conn.execute("INSERT INTO catalog_family_members (virtual_content_id, member_content_id, role, depth) "
                     "VALUES (%s, %s, %s, %s)", (virtual, member, role, depth))


def run(db, monkeypatch, hits, *, stages=("prod",), include_zt=True, scope=None, limit=25):
    """Run search() with the given (content_id, score) hits as the vector result."""
    def fake(**kwargs):
        rows = []
        for content_id, score in hits:
            entity = db.get_content_entity(content_id)
            bi = db.get_babylon_item(content_id) or {}
            analysis = db.get_showroom_analysis(content_id) or {}
            rows.append({"content_id": content_id, "content_type": entity["content_type"], "source": "babylon",
                         "best_similarity": score, "display_name": entity["display_name"],
                         "is_hands_on": True, "status": entity["status"], "stage_key": entity["stage_key"],
                         "ci_name": bi.get("ci_name"), "stage": bi.get("stage"), "category": "",
                         "catalog_namespace": bi.get("catalog_namespace"), "base_ci_name": None,
                         "content_hash": analysis.get("content_hash")})
        return rows

    fake.calls = []
    monkeypatch.setattr(db, "search_embeddings", Mock(side_effect=lambda **kw: fake(**kw)))
    monkeypatch.setattr(vector_search, "generate_embedding", lambda *a, **k: [0.1] * 768)
    return vector_search.search("query", db, stages=list(stages), include_zt=include_zt,
                                scope_content_ids=scope, limit=limit).candidates


def card_ids(cards):
    return sorted(c.content_id for c in cards)


def assert_invariant(db, cards):
    """No two cards share a content_id and no card is a member of another card's family."""
    ids = [c.content_id for c in cards]
    assert len(ids) == len(set(ids))
    covers = db.get_family_covers(ids)
    for member, virtuals in covers.items():
        assert not (set(virtuals) & set(ids)), f"{member} shows next to its virtual CI"
    assert enforce_card_invariant(cards, db) == cards


# ── the 2297 bug ──

def test_member_and_virtual_ci_never_both_show(db, monkeypatch):
    lab, vci = item(db, "lab.prod"), item(db, "virtual.prod", analysis=False)
    link(db, vci, lab)
    cards = run(db, monkeypatch, [(lab, 0.9)])
    assert card_ids(cards) == [vci]
    assert cards[0].vector_similarity_pct == 90
    assert cards[0].summary == f"About lab.prod"  # the card shows its anchor's analysis
    assert_invariant(db, cards)


def test_virtual_ci_whose_own_analysis_exists_is_not_replaced_by_the_member(db, monkeypatch):
    lab, vci = item(db, "lab.prod"), item(db, "virtual.prod")
    link(db, vci, lab)
    cards = run(db, monkeypatch, [(lab, 0.9), (vci, 0.8)])
    assert card_ids(cards) == [vci]
    assert cards[0].vector_similarity_pct == 90
    assert cards[0].summary == "About virtual.prod"


def test_four_level_chain_only_the_virtual_ci_shows(db, monkeypatch):
    pool, base = item(db, "pool.prod", analysis=False), item(db, "base.prod", analysis=False)
    fsc, vci = item(db, "fsc.prod"), item(db, "virtual.prod", analysis=False)
    link(db, vci, fsc)
    cards = run(db, monkeypatch, [(fsc, 0.9)])
    assert card_ids(cards) == [vci]
    assert pool not in card_ids(cards) and base not in card_ids(cards)
    assert_invariant(db, cards)


def test_pass_through_wrapper_and_lab_both_drop(db, monkeypatch):
    wrapper, lab, vci = item(db, "wrapper.prod"), item(db, "lab.prod"), item(db, "virtual.prod", analysis=False)
    link(db, vci, wrapper, "passthrough", 1)
    link(db, vci, lab, "anchor", 2)
    cards = run(db, monkeypatch, [(wrapper, 0.8), (lab, 0.9)])
    assert card_ids(cards) == [vci]
    assert_invariant(db, cards)


# ── shared members (field-asset) ──

def test_shared_member_two_eligible_virtual_cis_two_cards(db, monkeypatch):
    fsc = item(db, "fsc.prod")
    a, b = item(db, "va.prod", analysis=False), item(db, "vb.prod", analysis=False)
    link(db, a, fsc)
    link(db, b, fsc)
    cards = run(db, monkeypatch, [(fsc, 0.9)])
    assert card_ids(cards) == sorted([a, b])
    assert_invariant(db, cards)


def test_shared_member_one_virtual_ci_not_eligible_one_card(db, monkeypatch):
    fsc = item(db, "fsc.prod")
    a, b = item(db, "va.prod", analysis=False), item(db, "vb.prod", analysis=False)
    link(db, a, fsc)
    link(db, b, fsc)
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET retired_at = NOW() WHERE content_id = %s", (b,))
    assert card_ids(run(db, monkeypatch, [(fsc, 0.9)])) == [a]


# ── virtual CI not eligible => the member shows ──

def _not_eligible(db, vci, how):
    with db.pool.connection() as conn:
        if how == "retired":
            conn.execute("UPDATE content_entities SET retired_at = NOW() WHERE content_id = %s", (vci,))
        elif how == "retirement_started":
            conn.execute("INSERT INTO retirement_workflow (content_id, status) VALUES (%s, 'started')", (vci,))
        elif how == "retirement_started_on_stage_sibling":
            sibling = item(db, "virtual.dev", analysis=False)
            conn.execute("INSERT INTO retirement_workflow (content_id, status) VALUES (%s, 'started')", (sibling,))
        elif how == "wrong_stage":
            conn.execute("UPDATE content_entities SET status = 'dev' WHERE content_id = %s", (vci,))
        elif how == "zt":
            pass


@pytest.mark.parametrize("how", ["retired", "retirement_started", "retirement_started_on_stage_sibling", "wrong_stage"])
def test_member_shows_when_its_virtual_ci_is_not_eligible(db, monkeypatch, how):
    lab, vci = item(db, "lab.prod"), item(db, "virtual.prod", analysis=False)
    link(db, vci, lab)
    _not_eligible(db, vci, how)
    cards = run(db, monkeypatch, [(lab, 0.9)])
    assert card_ids(cards) == [lab]
    assert_invariant(db, cards)


def test_member_shows_when_the_virtual_ci_is_zt_and_zt_is_excluded(db, monkeypatch):
    lab = item(db, "lab.prod")
    vci = item(db, "virtual.prod", analysis=False, ci_extra={"catalog_namespace": "zt-isolation-test"})
    link(db, vci, lab)
    assert card_ids(run(db, monkeypatch, [(lab, 0.9)], include_zt=False)) == [lab]
    assert card_ids(run(db, monkeypatch, [(lab, 0.9)], include_zt=True)) == [vci]


def test_member_shows_when_the_virtual_ci_is_excluded_test_content(db, monkeypatch):
    lab = item(db, "lab.prod")
    vci = db.upsert_babylon_catalog_item({"ci_name": "tests.isolation-test-virtual.prod", "stage": "prod"})
    try:
        link(db, vci, lab)
        assert card_ids(run(db, monkeypatch, [(lab, 0.9)])) == [lab]
    finally:
        with db.pool.connection() as conn:
            conn.execute("DELETE FROM catalog_family_members WHERE virtual_content_id = %s", (vci,))
            conn.execute("DELETE FROM content_entities WHERE content_id = %s", (vci,))


def test_member_shows_when_the_virtual_ci_is_outside_the_requested_scope(db, monkeypatch):
    lab, vci = item(db, "lab.prod"), item(db, "virtual.prod", analysis=False)
    link(db, vci, lab)
    assert card_ids(run(db, monkeypatch, [(lab, 0.9)], scope=[lab])) == [lab]
    assert card_ids(run(db, monkeypatch, [(lab, 0.9)], scope=[vci])) == [vci]


# ── no anchor / no families ──

def test_virtual_ci_without_anchor_stands_alone_and_nothing_collapses(db, monkeypatch):
    sandbox, vci = item(db, "sandbox.prod"), item(db, "virtual-noanchor.prod")
    cards = run(db, monkeypatch, [(vci, 0.9), (sandbox, 0.8)])
    assert card_ids(cards) == sorted([vci, sandbox])


def test_empty_family_tables_change_nothing_and_do_not_fail(db, monkeypatch):
    a, b = item(db, "a.prod"), item(db, "b.prod")
    assert card_ids(run(db, monkeypatch, [(a, 0.9), (b, 0.8)])) == sorted([a, b])


# ── stage copies ──

def _set_hash(db, content_id, value):
    with db.pool.connection() as conn:
        conn.execute("UPDATE showroom_analysis SET content_hash = %s WHERE content_id = %s", (value, content_id))


def test_stage_copies_equal_content_merge_to_the_highest_stage_when_several_stages(db, monkeypatch):
    dev, prod = item(db, "x.dev"), item(db, "x.prod")
    _set_hash(db, dev, "same"), _set_hash(db, prod, "same")
    cards = run(db, monkeypatch, [(dev, 0.95), (prod, 0.9)], stages=("prod", "dev"))
    assert card_ids(cards) == [prod]
    assert cards[0].vector_similarity_pct == 95


def test_stage_copies_different_content_stay_two_cards(db, monkeypatch):
    dev, prod = item(db, "x.dev"), item(db, "x.prod")
    _set_hash(db, dev, "one"), _set_hash(db, prod, "two")
    assert card_ids(run(db, monkeypatch, [(dev, 0.95), (prod, 0.9)], stages=("prod", "dev"))) == sorted([dev, prod])


def test_stage_copies_never_merge_when_one_stage_is_selected(db, monkeypatch):
    dev, prod = item(db, "x.dev"), item(db, "x.prod")
    _set_hash(db, dev, "same"), _set_hash(db, prod, "same")
    assert card_ids(run(db, monkeypatch, [(dev, 0.95), (prod, 0.9)], stages=("prod",))) == sorted([dev, prod])


def test_stage_copies_are_not_merged_by_name_without_content_hash(db, monkeypatch):
    dev, prod = item(db, "x.dev", analysis=False), item(db, "x.prod", analysis=False)
    db.store_embedding(dev, "lab", "babylon", "summary", "x", [0.1] * 768)
    cards = run(db, monkeypatch, [(dev, 0.9), (prod, 0.8)], stages=("prod", "dev"))
    assert card_ids(cards) == sorted([dev, prod])


def test_virtual_ci_stage_copies_merge_on_their_anchors_content(db, monkeypatch):
    lab_prod, lab_dev = item(db, "lab.prod"), item(db, "lab.dev")
    v_prod, v_dev = item(db, "virtual.prod", analysis=False), item(db, "virtual.dev", analysis=False)
    link(db, v_prod, lab_prod)
    link(db, v_dev, lab_dev)
    _set_hash(db, lab_prod, "same"), _set_hash(db, lab_dev, "same")
    cards = run(db, monkeypatch, [(lab_prod, 0.9), (lab_dev, 0.8)], stages=("prod", "dev"))
    assert card_ids(cards) == [v_prod]
    _set_hash(db, lab_dev, "other")
    assert card_ids(run(db, monkeypatch, [(lab_prod, 0.9), (lab_dev, 0.8)], stages=("prod", "dev"))) == sorted([v_prod, v_dev])


# ── the top-K cut happens after the family rule ──

def test_dropped_members_do_not_leave_empty_slots(db, monkeypatch):
    members = [item(db, f"m{i}.prod") for i in range(3)]
    vcis = [item(db, f"v{i}.prod", analysis=False) for i in range(3)]
    others = [item(db, f"o{i}.prod") for i in range(2)]
    for v, m in zip(vcis, members):
        link(db, v, m)
    hits = [(m, 0.95 - i * 0.01) for i, m in enumerate(members)] + [(o, 0.8 - i * 0.01) for i, o in enumerate(others)]
    cards = run(db, monkeypatch, hits, limit=4)
    assert len(cards) == 4
    assert card_ids(cards) == sorted(vcis + others[:1])
    # the search asks SQL for every item of the window; the cut to `limit` is after the collapse
    assert db.search_embeddings.call_args.kwargs["limit"] is None


def test_cut_to_limit_happens_after_the_collapse_with_an_uncapped_result(db, monkeypatch):
    # 30 members of 30 virtual CIs hit first, then 30 plain items. limit=25: the cards are
    # the 25 best of (30 virtual CIs + 30 plain items), never members.
    members = [item(db, f"m{i:02d}.prod") for i in range(30)]
    vcis = [item(db, f"v{i:02d}.prod", analysis=False) for i in range(30)]
    plain = [item(db, f"p{i:02d}.prod") for i in range(30)]
    for v, m in zip(vcis, members):
        link(db, v, m)
    hits = [(m, 0.99 - i * 0.001) for i, m in enumerate(members)] + [(p, 0.9 - i * 0.001) for i, p in enumerate(plain)]
    cards = run(db, monkeypatch, hits, limit=25)
    assert card_ids(cards) == sorted(vcis[:25])
    assert not set(card_ids(cards)) & set(members)


def test_search_embeddings_without_a_limit_returns_every_item_that_passes_the_bar(db):
    ids = [item(db, f"u{i:02d}.prod") for i in range(30)]
    for content_id in ids:
        db.store_embedding(content_id, "lab", "babylon", "summary", "text", [0.1] * 768)
    vec = [0.1] * 768
    assert len(db.search_embeddings(vec, scope_content_ids=ids)) == 25
    assert len(db.search_embeddings(vec, limit=None, scope_content_ids=ids)) == 30


# ── everything at once ──

def test_invariant_over_a_fixture_with_every_case(db, monkeypatch):
    # 4-level chain (field-asset style, shared member), plain lab, stage copies, ineligible virtual CI
    fsc = item(db, "fsc.prod")
    fa, fa_shared = item(db, "fa.prod", analysis=False), item(db, "fa-shared.prod", analysis=False)
    link(db, fa, fsc), link(db, fa_shared, fsc)
    lab, vlab = item(db, "lab.prod"), item(db, "vlab.prod", analysis=False)
    link(db, vlab, lab)
    plain = item(db, "plain.prod")
    retired_lab, retired_v = item(db, "rlab.prod"), item(db, "rv.prod", analysis=False)
    link(db, retired_v, retired_lab)
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET retired_at = NOW() WHERE content_id = %s", (retired_v,))
    dev, prod = item(db, "copy.dev"), item(db, "copy.prod")
    _set_hash(db, dev, "same"), _set_hash(db, prod, "same")
    hits = [(fsc, 0.99), (lab, 0.97), (plain, 0.95), (retired_lab, 0.93), (dev, 0.92), (prod, 0.91), (vlab, 0.5)]
    cards = run(db, monkeypatch, hits, stages=("prod", "dev"))
    assert card_ids(cards) == sorted([fa, fa_shared, vlab, plain, retired_lab, prod])
    assert_invariant(db, cards)


# ── the pipeline-level invariant guard ──

def test_enforce_card_invariant_drops_a_member_next_to_its_virtual_ci(db):
    lab, vci, other = item(db, "lab.prod"), item(db, "virtual.prod"), item(db, "other.prod")
    link(db, vci, lab)
    cards = [SimpleNamespace(content_id=c) for c in (vci, lab, other)]
    assert [c.content_id for c in enforce_card_invariant(cards, db)] == [vci, other]


# ── deploy smoke check command ──

def test_check_card_families_command(db, monkeypatch):
    from click.testing import CliRunner
    from rcars import cli as cli_module

    lab, vci, other = item(db, "lab.prod"), item(db, "virtual.prod"), item(db, "other.prod")
    link(db, vci, lab)
    monkeypatch.setattr(cli_module, "get_db", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    runner = CliRunner()
    assert runner.invoke(cli_module.cli, ["check-card-families", vci, other]).exit_code == 0
    bad = runner.invoke(cli_module.cli, ["check-card-families", vci, lab])
    assert bad.exit_code == 1 and "share the family" in bad.output


def test_check_card_families_passes_with_a_warning_when_no_families_are_stored(db, monkeypatch):
    from click.testing import CliRunner
    from rcars import cli as cli_module

    monkeypatch.setattr(cli_module, "get_db", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(db, "count_family_members", lambda: 0)
    result = CliRunner().invoke(cli_module.cli, ["check-card-families", "babylon:a", "babylon:b"])
    assert result.exit_code == 0 and "WARNING" in result.output


# ── card analysis: a cleared own row must not hide the anchor ──

def _clear_own_analysis(db, content_id):
    with db.pool.connection() as conn:  # keeps the row, summary etc. become NULL
        db.clear_babylon_generated_artifacts([content_id], conn=conn)


def test_card_analysis_uses_the_anchor_when_the_virtual_ci_row_is_cleared(db):
    anchor, vci = item(db, "lab.prod"), item(db, "virtual.prod")
    link(db, vci, anchor)
    _clear_own_analysis(db, vci)
    assert db.get_showroom_analysis(vci) is not None and db.get_showroom_analysis(vci)["summary"] is None
    assert db.get_card_analysis(vci)["summary"] == "About lab.prod"


def test_card_analysis_keeps_the_cleared_own_row_when_there_is_no_anchor(db):
    vci = item(db, "virtual.prod")
    _clear_own_analysis(db, vci)
    result = db.get_card_analysis(vci)
    assert result is not None and result["content_id"] == vci and result["summary"] is None


def test_card_analysis_prefers_a_usable_own_analysis(db):
    anchor, vci = item(db, "lab.prod"), item(db, "virtual.prod")
    link(db, vci, anchor)
    assert db.get_card_analysis(vci)["summary"] == "About virtual.prod"
