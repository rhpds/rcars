"""Overlap and chat on catalog families (RHDPCD-2297 PR 4).

A. Overlap skips family pairs and groups stage copies by stage_key.
B. Chat resolve lifts a member to its covering virtual CI(s).
C. The evidence pack respects the user's stages.
D. The pre-router sends "similar to X" to recommend with similar_to.
"""
import os

import psycopg
import pytest

from rcars.db.database import Database
from rcars.db.overlap import generate_overlap_candidates
from rcars.services.catalog_identity import exclusion_set_for, lift_to_covering
from rcars.services.chat import router as chat_router
from rcars.services.chat.evidence import build_evidence_pack
from rcars.services.chat.models import RouterOutput
from tests.chat_fixtures import seed_chat_fixtures
from tests.test_chat_resolve import SETTINGS

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL", "postgresql://rcars:dev@localhost:5432/rcars_test")


@pytest.fixture
def db():
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        for row in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def add(db, ci_name, stage="prod", display=None, products=("OpenShift",),
        topics=("containers", "automation"), content_hash=None):
    """A catalog item with an analysis that overlaps with every other item built here."""
    cid = db.upsert_babylon_catalog_item({
        "ci_name": ci_name, "stage": stage, "display_name": display or ci_name,
        "showroom_url": "https://github.com/example/content", "showroom_ref": "main",
        "catalog_namespace": "babylon-catalog-prod"})
    db.upsert_showroom_analysis({
        "content_id": cid, "summary": f"About {ci_name}", "modules_json": [],
        "products_json": list(products), "topics_json": list(topics),
        "content_hash": content_hash or f"hash-{ci_name}"})
    db.set_scan_status(cid, "success")
    return cid


def link(db, virtual, member, role="anchor", depth=1):
    with db.pool.connection() as conn:
        conn.execute("INSERT INTO catalog_family_members (virtual_content_id, member_content_id, role, depth) "
                     "VALUES (%s, %s, %s, %s)", (virtual, member, role, depth))


def pairs(db):
    with db.pool.connection() as conn:
        rows = conn.execute("SELECT content_id_a, content_id_b FROM overlap_candidates").fetchall()
    return {frozenset((r["content_id_a"], r["content_id_b"])) for r in rows}


# ── A. overlap ──

def test_overlap_skips_a_virtual_ci_and_its_own_member(db):
    virtual = add(db, "published.lab.prod")
    member = add(db, "agd-v2.lab.prod")
    other = add(db, "unrelated.prod")
    link(db, virtual, member)
    generate_overlap_candidates(db.pool)
    found = pairs(db)
    assert frozenset((virtual, member)) not in found  # same content, not an overlap
    assert frozenset((virtual, other)) in found and frozenset((member, other)) in found


def test_overlap_skips_family_pair_whichever_way_the_ids_sort(db):
    member = add(db, "a-member.prod")  # sorts before the virtual CI
    virtual = add(db, "z-published.prod")
    link(db, virtual, member)
    generate_overlap_candidates(db.pool)
    assert pairs(db) == set()


def test_overlap_flags_two_virtual_cis_that_share_a_component(db):
    member = add(db, "agd-v2.ocp-field-asset-cnv.prod", products=("Other",), topics=("x", "y"))
    first = add(db, "published.ocp-field-asset.prod")
    second = add(db, "published.ocp-field-asset-shared.prod")
    link(db, first, member)
    link(db, second, member)
    generate_overlap_candidates(db.pool)
    assert frozenset((first, second)) in pairs(db)  # a real overlap between two items


def test_overlap_groups_stage_copies_by_stage_key(db):
    prod = add(db, "lab.prod", stage="prod")
    dev = add(db, "lab.dev", stage="dev")
    other = add(db, "other.prod")
    generate_overlap_candidates(db.pool)
    found = pairs(db)
    assert frozenset((prod, other)) in found  # the prod copy represents the item
    assert frozenset((dev, other)) not in found
    assert frozenset((prod, dev)) not in found


def test_overlap_does_not_merge_items_whose_name_only_looks_like_a_stage_suffix(db):
    # The old regex stripped any last dot-part: "lab.alpha" and "lab.beta" became one item.
    alpha = add(db, "lab.alpha", stage="prod")
    beta = add(db, "lab.beta", stage="prod")
    generate_overlap_candidates(db.pool)
    assert frozenset((alpha, beta)) in pairs(db)


def test_overlap_uses_the_dev_copy_when_it_is_the_only_one(db):
    dev = add(db, "lab.dev", stage="dev")
    other = add(db, "other.prod")
    generate_overlap_candidates(db.pool)
    assert frozenset((dev, other)) in pairs(db)


# ── B. chat resolve ──

def test_lift_to_covering_is_pure():
    covers = {"m": ["v1", "v2"]}
    assert lift_to_covering("m", covers, {"v1"}) == ["v1"]
    assert lift_to_covering("m", covers, {"v1", "v2"}) == ["v1", "v2"]
    assert lift_to_covering("m", covers, set()) == ["m"]
    assert lift_to_covering("plain", covers, {"v1"}) == ["plain"]


def test_resolve_member_with_one_eligible_virtual_ci_returns_the_virtual_ci(db):
    virtual = add(db, "published.lab.prod", display="LB9001 Lab")
    member = add(db, "agd-v2.lab.prod", display="LB9001 Lab member")
    link(db, virtual, member)
    for ref in (f"content_id:{member}", "LB9001 Lab member"):
        resolved = chat_router.resolve_item(ref, db)
        assert resolved["item"]["content_id"] == virtual, ref


def test_resolve_by_lab_number_is_deterministic_without_is_published(db):
    virtual = add(db, "published.lab.prod", display="LB9002 Lab")
    member = add(db, "agd-v2.lab.prod", display="LB9002 Lab")
    link(db, virtual, member)
    # Neither row is flagged published; whichever the prefix lookup finds, the answer is the virtual CI.
    assert chat_router.resolve_item("LB9002", db)["item"]["content_id"] == virtual


def test_resolve_member_with_two_virtual_cis_offers_both_as_chips(db):
    member = add(db, "agd-v2.ocp-field-asset-cnv.prod", display="Field asset CNV")
    first = add(db, "published.ocp-field-asset.prod", display="Field asset")
    second = add(db, "published.ocp-field-asset-shared.prod", display="Field asset shared")
    link(db, first, member)
    link(db, second, member)
    resolved = chat_router.resolve_item(f"content_id:{member}", db)
    assert "item" not in resolved
    assert {g["content_id"] for g in resolved["guesses"]} == {first, second}


def test_resolve_member_without_an_eligible_virtual_ci_returns_the_member(db):
    member = add(db, "agd-v2.lab.prod", display="LB9003 Lab")
    virtual = add(db, "published.lab.dev", stage="dev", display="LB9003 Lab dev")  # not in the prod default
    link(db, virtual, member)
    assert chat_router.resolve_item(f"content_id:{member}", db)["item"]["content_id"] == member
    assert chat_router.resolve_item(f"content_id:{member}", db, stages=["dev", "prod"])["item"]["content_id"] == virtual


def test_resolve_plain_item_is_unchanged(db):
    plain = add(db, "plain.prod", display="Plain lab")
    assert chat_router.resolve_item(f"content_id:{plain}", db)["item"]["content_id"] == plain


@pytest.mark.asyncio
async def test_two_virtual_cis_clarify_with_chips_in_the_existing_flow(db):
    member = add(db, "agd-v2.ocp-field-asset-cnv.prod", display="Field asset CNV")
    first = add(db, "published.ocp-field-asset.prod", display="Field asset")
    second = add(db, "published.ocp-field-asset-shared.prod", display="Field asset shared")
    link(db, first, member)
    link(db, second, member)
    out = RouterOutput(intent="recommend", confidence=0.9,
                       args={"search_query": "similar to it", "similar_to": f"content_id:{member}"})
    res = await chat_router.resolve_and_verify(out, [], db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "clarify" and res.reference_ids == []
    assert {c.args["similar_to"] for c in res.chips} == {f"content_id:{first}", f"content_id:{second}"}


@pytest.mark.asyncio
async def test_similar_to_a_member_still_excludes_the_whole_family(db):
    virtual = add(db, "published.lab.prod", display="LB9004 Lab")
    member = add(db, "agd-v2.lab.prod", display="LB9004 member")
    dev_copy = add(db, "published.lab.dev", stage="dev", display="LB9004 Lab dev")
    link(db, virtual, member)
    out = RouterOutput(intent="recommend", confidence=0.9,
                       args={"search_query": "similar to it", "similar_to": f"content_id:{member}"})
    res = await chat_router.resolve_and_verify(out, [], db, SETTINGS(chat_intent_roles_str=""), "u@x.com")
    assert res.kind == "execute" and res.reference_ids == [virtual]  # lifted
    excluded = exclusion_set_for(db, res.reference_ids[0])
    assert {virtual, member, dev_copy} <= excluded
    assert excluded == exclusion_set_for(db, member)  # same set either way


# ── C. evidence pack respects stages ──

def test_evidence_pack_filters_neighbors_by_the_users_stages(db):
    ids = seed_chat_fixtures(db)
    anchor = ids["lb2144-ansible-eda"]
    with db.pool.connection() as conn:
        conn.execute("UPDATE babylon_items SET stage = 'dev' WHERE content_id = %s",
                     (ids["lb2145-ansible-basics"],))
    assert build_evidence_pack(db, [anchor], stages=["prod"]) == []
    pack = build_evidence_pack(db, [anchor], stages=["prod", "dev"])
    assert [p["name"] for p in pack] == ["LB2145 Ansible Automation Basics"]
    assert build_evidence_pack(db, [anchor])  # no stages given: unfiltered, as before


def test_evidence_pack_filters_workload_neighbors_by_stage(db):
    ids = seed_chat_fixtures(db)
    with db.pool.connection() as conn:
        conn.execute(
            "INSERT INTO babylon_item_workloads (content_id, workload_fqcn, workload_role, workload_collection) "
            "VALUES (%s, 'rhpds.ocpvirt.setup', 'setup_virt', 'rhpds.ocpvirt')",
            (ids["lb2145-ansible-basics"],))
        conn.execute("UPDATE babylon_items SET stage = 'event' WHERE content_id = %s",
                     (ids["lb2145-ansible-basics"],))
    shared = lambda stages: [p for p in build_evidence_pack(db, [ids["ocpvirt-migration"]], stages=stages)
                             if p["relationship"] == "shared_workload"]
    assert shared(["prod"]) == []
    assert len(shared(["prod", "event"])) == 1


# ── D. pre-router ──

@pytest.mark.parametrize("message", [
    "Something similar to LB1237",
    "similar to LB1237",
    "an alternative to LB1237",
    "instead of LB1237",
])
def test_similar_to_a_lab_number_does_not_become_item_facts(message):
    out = chat_router.pattern_check(message)
    assert out is None or out.intent == "recommend"  # None = the LLM router decides
    if out is not None:
        assert out.args["similar_to"]


def test_plain_lab_number_stays_item_facts():
    out = chat_router.pattern_check("LB1237")
    assert out.intent == "item_facts" and out.item_refs == ["LB1237"]


CATALOG_URL = "https://catalog.demo.redhat.com/catalog?item=babylon-catalog-prod/lb1237-hol-rhel10-cnv.prod"


@pytest.mark.parametrize("message", [
    f"similar to {CATALOG_URL}",
    f"{CATALOG_URL} something like this",
    f"an alternative to {CATALOG_URL}",
])
def test_catalog_url_with_similar_goes_to_recommend_with_similar_to(message):
    out = chat_router.pattern_check(message)
    assert out.intent == "recommend"
    assert out.args["similar_to"] == CATALOG_URL
    assert out.args["search_query"]
    assert out.item_refs == []  # the reference is resolved once, by similar_to


def test_catalog_url_alone_stays_item_facts():
    out = chat_router.pattern_check(CATALOG_URL)
    assert out.intent == "item_facts" and out.item_refs == ["content_id:babylon:lb1237-hol-rhel10-cnv.prod"]


def test_catalog_url_with_performance_words_stays_performance():
    out = chat_router.pattern_check(f"how many provisions does {CATALOG_URL} have")
    assert out.intent == "performance"


@pytest.mark.parametrize("message", [
    f"what overlaps with {CATALOG_URL}",
    f"is {CATALOG_URL} a duplicate of anything",
    f"compare {CATALOG_URL}",
])
def test_catalog_url_with_overlap_words_goes_to_overlap(message):
    assert chat_router.pattern_check(message).intent == "overlap"


@pytest.mark.parametrize("message", [
    "what overlaps with LB1237",
    "is LB1237 a duplicate of LB1238",
    "overlaps LB1237",
])
def test_overlap_asks_about_a_lab_number_never_become_recommend_or_item_facts(message):
    out = chat_router.pattern_check(message)
    assert out is None or out.intent == "overlap"


def test_short_overlap_ask_with_a_lab_number_goes_to_overlap():
    out = chat_router.pattern_check("overlaps LB1237")
    assert out.intent == "overlap" and out.args["item_ref"] == "LB1237"


def test_similar_to_with_a_url_and_a_name_does_not_pre_route_on_the_name():
    # Display names are not parsed here: without a URL the LLM router sets similar_to.
    assert chat_router.pattern_check("something similar to Event-Driven Ansible Basics") is None


# ── review fixes ──

@pytest.mark.asyncio
async def test_overlap_from_a_lifted_virtual_ci_keeps_its_members_neighbors(db):
    from rcars.services.chat import handlers
    from rcars.services.chat.router import Resolution
    member = add(db, "agd-v2.lab.prod", display="Lab member")
    other = add(db, "unrelated.prod", display="Unrelated")
    virtual = db.upsert_babylon_catalog_item({  # a virtual CI with no analysis of its own
        "ci_name": "published.lab.prod", "stage": "prod", "display_name": "Lab"})
    link(db, virtual, member)
    generate_overlap_candidates(db.pool)
    res = Resolution(kind="execute", output=RouterOutput(intent="overlap", args={}, confidence=1.0),
                     items=[db.get_babylon_item(virtual)])
    out = await handlers.handle_overlap(res, db, SETTINGS(chat_intent_roles_str=""), ["prod"], True, None)
    assert [n["content_id"] for n in out.session_results] == [other]
    assert set(out.anchor_ids) == {virtual, member}


@pytest.mark.asyncio
async def test_resolve_and_verify_passes_the_users_stages(db):
    member = add(db, "agd-v2.lab.prod", display="LB9005 Lab")
    virtual = add(db, "published.lab.dev", stage="dev", display="LB9005 Lab dev")
    link(db, virtual, member)
    out = RouterOutput(intent="item_facts", confidence=0.9, item_refs=[f"content_id:{member}"], args={})
    settings = SETTINGS(chat_intent_roles_str="")
    prod = await chat_router.resolve_and_verify(out, [], db, settings, "u@x.com")
    both = await chat_router.resolve_and_verify(out, [], db, settings, "u@x.com", stages=["prod", "dev"])
    assert prod.items[0]["content_id"] == member and both.items[0]["content_id"] == virtual


@pytest.mark.asyncio
async def test_overlap_lists_a_neighbor_once_when_several_members_overlap_with_it(db):
    from rcars.services.chat import handlers
    from rcars.services.chat.router import Resolution
    first = add(db, "agd-v2.one.prod")
    second = add(db, "agd-v2.two.prod")
    other = add(db, "unrelated.prod")
    virtual = db.upsert_babylon_catalog_item({"ci_name": "published.lab.prod", "stage": "prod",
                                              "display_name": "Lab"})
    link(db, virtual, first)
    link(db, virtual, second, role="passthrough", depth=2)
    generate_overlap_candidates(db.pool)
    res = Resolution(kind="execute", output=RouterOutput(intent="overlap", args={}, confidence=1.0),
                     items=[db.get_babylon_item(virtual)])
    out = await handlers.handle_overlap(res, db, SETTINGS(chat_intent_roles_str=""), ["prod"], True, None)
    assert [n["content_id"] for n in out.session_results] == [other]
    assert out.scaffold_facts["neighbor_count"] == 1


def test_item_card_of_a_virtual_ci_without_analysis_shows_its_anchors_summary(db):
    from rcars.services.chat import handlers
    anchor = add(db, "agd-v2.lab.prod")
    virtual = db.upsert_babylon_catalog_item({"ci_name": "published.lab.prod", "stage": "prod",
                                              "display_name": "Lab"})
    link(db, virtual, anchor)
    card = handlers._item_card(db, db.get_babylon_item(virtual))
    assert card["summary"] == "About agd-v2.lab.prod"


# ── item card uses the same family-group neighbours as the overlap handler ──

def _family_with_pairs_on_the_member(db):
    member = add(db, "agd-v2.lab.prod", display="Lab member")
    one = add(db, "zt-one.prod", display="One")
    two = add(db, "zt-two.prod", display="Two")
    virtual = db.upsert_babylon_catalog_item({  # no analysis of its own: pairs sit on the member
        "ci_name": "published.lab.prod", "stage": "prod", "display_name": "Lab"})
    link(db, virtual, member)
    generate_overlap_candidates(db.pool)
    return virtual, member, {one, two}


@pytest.mark.asyncio
async def test_item_facts_card_lists_the_same_neighbours_as_overlap(db):
    from rcars.services.chat import handlers
    from rcars.services.chat.router import Resolution
    virtual, member, expected = _family_with_pairs_on_the_member(db)
    res = Resolution(kind="execute", output=RouterOutput(intent="item_facts", args={}, confidence=1.0),
                     items=[db.get_babylon_item(virtual)])
    settings = SETTINGS(chat_intent_roles_str="")
    facts = await handlers.handle_item_facts(res, db, settings, ["prod"], True, None)
    overlap = await handlers.handle_overlap(res, db, settings, ["prod"], True, None)
    card_ids = {n["content_id"] for n in facts.blocks[0].data["neighbors"]}
    assert card_ids == expected == {n["content_id"] for n in overlap.session_results}
    assert member not in card_ids and virtual not in card_ids  # never the anchor's own family
    assert facts.scaffold_facts["neighbor_count"] == 2


@pytest.mark.asyncio
async def test_overlap_table_block_has_the_family_neighbours(db):
    from rcars.services.chat import handlers
    from rcars.services.chat.router import Resolution
    virtual, _, expected = _family_with_pairs_on_the_member(db)
    res = Resolution(kind="execute", output=RouterOutput(intent="overlap", args={}, confidence=1.0),
                     items=[db.get_babylon_item(virtual)])
    out = await handlers.handle_overlap(res, db, SETTINGS(chat_intent_roles_str=""), ["prod"], True, None)
    assert {n["content_id"] for n in out.blocks[1].data["neighbors"]} == expected


def test_overlap_neighbors_is_the_one_shared_lookup(db):
    from rcars.services.chat.handlers import overlap_neighbors
    virtual, member, expected = _family_with_pairs_on_the_member(db)
    group, neighbors = overlap_neighbors(db, virtual, ["prod"], limit=1)
    assert set(group) == {virtual, member} and len(neighbors) == 1


@pytest.mark.asyncio
async def test_tied_scores_card_is_the_first_five_table_rows(db):
    """More than ten neighbors with the same score: both limits cut the same ordered list."""
    from rcars.services.chat import handlers
    from rcars.services.chat.router import Resolution
    member = add(db, "agd-v2.lab.prod")
    others = [add(db, f"zt-n{i:03d}.prod") for i in range(12)]
    virtual = db.upsert_babylon_catalog_item({"ci_name": "published.lab.prod", "stage": "prod",
                                              "display_name": "Lab"})
    link(db, virtual, member)
    generate_overlap_candidates(db.pool)
    res = Resolution(kind="execute", output=RouterOutput(intent="overlap", args={}, confidence=1.0),
                     items=[db.get_babylon_item(virtual)])
    settings = SETTINGS(chat_intent_roles_str="")
    table = (await handlers.handle_overlap(res, db, settings, ["prod"], True, None)).blocks[1].data["neighbors"]
    card = (await handlers.handle_item_facts(res, db, settings, ["prod"], True, None)).blocks[0].data["neighbors"]
    expected = sorted(others)  # equal scores: ties break by neighbor content_id
    assert [n["content_id"] for n in table] == expected[:10]
    assert [n["content_id"] for n in card] == expected[:5] == [n["content_id"] for n in table[:5]]
