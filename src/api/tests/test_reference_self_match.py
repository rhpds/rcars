"""RHDPCD-2298: "similar to LBxxxx" never returns the referenced item itself.

The exclusion set is the referenced item R, its members (R a virtual CI), the virtual
CIs covering it (R a member) and the stage copies (same stage_key, any stage) of all
of them. Other virtual CIs that only share a component with R still show.
"""
from unittest.mock import Mock

from rcars.services import catalog_identity
from rcars.services.catalog_identity import family_exclusion_core
from rcars.services.recommender import rationale, vector_search
from rcars.services.recommender.models import Candidate, QueryState
from tests.showroom_helpers import db  # noqa: F401  (fixture)
from tests.test_advisor_families import card_ids, item, link
from tests.test_showroom_recommendation_isolation import add_stub


def ref(db, name, number, **kw):
    """A catalog item whose display name starts with LB<number>."""
    return item(db, name, ci_extra={"display_name": f"LB{number} {name}"}, **kw)


def run_similar(db, monkeypatch, number, hits, *, stages=("prod",), limit=25, embedding=[0.1] * 768, query=None):
    """search("Something similar to LB<number>") with ``hits`` as every vector result."""
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

    monkeypatch.setattr(db, "search_embeddings", Mock(side_effect=lambda **kw: fake(**kw)))
    monkeypatch.setattr(db, "get_embedding", lambda *a, **k: embedding)
    monkeypatch.setattr(vector_search, "generate_embedding", lambda *a, **k: [0.1] * 768)
    return vector_search.search(query or f"Something similar to LB{number}", db, stages=list(stages), limit=limit)


# ── pure rule ──

def test_core_of_a_virtual_ci_is_itself_and_its_members():
    rows = [{"virtual_content_id": "v", "member_content_id": "a"},
            {"virtual_content_id": "v", "member_content_id": "b"}]
    assert family_exclusion_core("v", rows) == {"v", "a", "b"}


def test_core_of_a_member_is_itself_and_every_covering_virtual_ci_not_its_siblings():
    rows = [{"virtual_content_id": "v1", "member_content_id": "fsc"},
            {"virtual_content_id": "v2", "member_content_id": "fsc"},
            {"virtual_content_id": "v1", "member_content_id": "other"}]
    assert family_exclusion_core("fsc", rows) == {"fsc", "v1", "v2"}


def test_core_without_family_rows_is_the_item_alone():
    assert family_exclusion_core("x", []) == {"x"}


# ── database lookups ──

def test_stage_copies_share_the_stage_key_in_any_stage(db):
    prod, dev = item(db, "lab.prod"), item(db, "lab.dev")
    other = item(db, "other.prod")
    assert db.get_stage_copy_ids([prod]) == {prod, dev}
    assert other not in db.get_stage_copy_ids([prod])


def test_exclusion_set_for_a_member_covered_by_a_vci_with_stage_copies(db):
    lab, vci = item(db, "lab.prod"), item(db, "virtual.prod", analysis=False)
    lab_dev, vci_dev = item(db, "lab.dev"), item(db, "virtual.dev", analysis=False)
    link(db, vci, lab)
    link(db, vci_dev, lab_dev)
    assert catalog_identity.exclusion_set_for(db, lab) == {lab, vci, lab_dev, vci_dev}


# ── search: the 2298 bug ──

def test_pure_stub_reference_is_not_returned_and_neither_is_its_published_vci(db, monkeypatch):
    stub = ref(db, "lb-stub.prod", 9101, analysis=False)
    vci = item(db, "published-lb.prod", analysis=False)
    owner = item(db, "owner.prod")
    link(db, vci, stub)
    other = item(db, "other.prod")
    state = run_similar(db, monkeypatch, 9101, [(owner, 0.5), (vci, 0.47), (other, 0.85)])
    assert stub not in card_ids(state.candidates)
    assert vci not in card_ids(state.candidates)
    assert other in card_ids(state.candidates)


def test_virtual_ci_reference_excludes_itself_members_and_dev_copy(db, monkeypatch):
    vci, lab = ref(db, "virtual.prod", 9102, analysis=False), item(db, "lab.prod")
    vci_dev, lab_dev = item(db, "virtual.dev", analysis=False), item(db, "lab.dev")
    link(db, vci, lab)
    link(db, vci_dev, lab_dev)
    other = item(db, "other.prod")
    state = run_similar(db, monkeypatch, 9102, [(lab, 0.9), (lab_dev, 0.9), (other, 0.8)],
                        stages=("prod", "dev"))
    assert card_ids(state.candidates) == [other]


def test_member_reference_excludes_covering_virtual_ci_and_dev_copies(db, monkeypatch):
    lab, vci = ref(db, "lab.prod", 9103), item(db, "virtual.prod", analysis=False)
    lab_dev, vci_dev = item(db, "lab.dev"), item(db, "virtual.dev", analysis=False)
    link(db, vci, lab)
    link(db, vci_dev, lab_dev)
    other = item(db, "other.prod")
    state = run_similar(db, monkeypatch, 9103, [(vci, 0.9), (vci_dev, 0.9), (other, 0.8)],
                        stages=("prod", "dev"))
    assert card_ids(state.candidates) == [other]


def test_component_covered_by_two_virtual_cis_excludes_both(db, monkeypatch):
    fsc = ref(db, "fsc.prod", 9104)
    a, b = item(db, "va.prod", analysis=False), item(db, "vb.prod", analysis=False)
    link(db, a, fsc)
    link(db, b, fsc)
    other = item(db, "other.prod")
    state = run_similar(db, monkeypatch, 9104, [(a, 0.9), (b, 0.9), (other, 0.8)])
    assert card_ids(state.candidates) == [other]


def test_virtual_ci_sharing_only_a_component_with_the_reference_still_shows(db, monkeypatch):
    fsc = item(db, "fsc.prod")
    va = ref(db, "va.prod", 9105, analysis=False)
    vb = item(db, "vb.prod", analysis=False)
    link(db, va, fsc)
    link(db, vb, fsc)
    state = run_similar(db, monkeypatch, 9105, [(fsc, 0.9), (vb, 0.85)])
    assert card_ids(state.candidates) == [vb]


def test_sibling_component_of_an_excluded_virtual_ci_still_shows_as_itself(db, monkeypatch):
    lab, sibling = ref(db, "lab.prod", 9106), item(db, "sibling.prod")
    vci = item(db, "virtual.prod", analysis=False)
    link(db, vci, lab)
    link(db, vci, sibling, "passthrough", 1)
    state = run_similar(db, monkeypatch, 9106, [(sibling, 0.9)])
    # The covering virtual CI cannot show, so the sibling is not collapsed into it.
    assert card_ids(state.candidates) == [sibling]


def test_plain_ci_reference_and_its_stage_copies_are_excluded(db, monkeypatch):
    plain, dev = ref(db, "plain.prod", 9107), item(db, "plain.dev")
    other = item(db, "other.prod")
    state = run_similar(db, monkeypatch, 9107, [(plain, 1.0), (dev, 0.95), (other, 0.7)],
                        stages=("prod", "dev"))
    assert card_ids(state.candidates) == [other]


def test_dev_copy_is_excluded_even_when_dev_is_not_selected_or_is_selected(db, monkeypatch):
    plain, dev = ref(db, "plain.prod", 9108), item(db, "plain.dev")
    other = item(db, "other.prod")
    for stages in (("prod",), ("prod", "dev")):
        state = run_similar(db, monkeypatch, 9108, [(plain, 1.0), (dev, 0.9), (other, 0.7)], stages=stages)
        assert card_ids(state.candidates) == [other]


def test_empty_family_tables_exclude_the_item_and_its_stage_copies_only(db, monkeypatch):
    plain, dev = ref(db, "plain.prod", 9109), item(db, "plain.dev")
    other = item(db, "other.prod")
    assert db.get_family_rows([plain]) == []
    state = run_similar(db, monkeypatch, 9109, [(plain, 1.0), (dev, 0.9), (other, 0.7)],
                        stages=("prod", "dev"))
    assert card_ids(state.candidates) == [other]


def test_exclusion_leaves_no_empty_slot(db, monkeypatch):
    plain = ref(db, "plain.prod", 9110)
    others = [item(db, f"other{i}.prod") for i in range(3)]
    state = run_similar(db, monkeypatch, 9110, [(plain, 1.0), *[(o, 0.8 - i / 100) for i, o in enumerate(others)]],
                        limit=3)
    assert card_ids(state.candidates) == sorted(others)


# ── the referenced item's summary reaches the answer step ──

def test_search_returns_the_referenced_summary_from_the_card_analysis(db, monkeypatch):
    vci = ref(db, "virtual.prod", 9111, analysis=False)
    anchor = item(db, "anchor.prod")  # analysis summary: "About anchor.prod"
    link(db, vci, anchor)
    other = item(db, "other.prod")
    state = run_similar(db, monkeypatch, 9111, [(other, 0.8)])
    assert len(state.references) == 1
    assert state.references[0]["content_id"] == vci
    assert state.references[0]["summary"] == "About anchor.prod"


def test_request_text_describes_what_the_referenced_item_covers():
    text = rationale.request_with_references(
        "Something similar to LB1237", [{"display_name": "LB1237 RHEL 10 on CNV", "summary": "Covers RHEL on CNV."}])
    assert text.startswith("Something similar to LB1237")
    assert "LB1237 RHEL 10 on CNV" in text and "Covers RHEL on CNV." in text


def test_request_text_is_the_query_when_there_is_no_reference():
    assert rationale.request_with_references("a query", []) == "a query"


def test_rationale_and_synthesis_receive_the_reference_summary(monkeypatch):
    seen = {}
    monkeypatch.setattr(rationale, "_call_rationale_single",
                        lambda c, analysis, query, *a, **k: seen.setdefault("single", query) and {"why_it_fits": "ok"})
    monkeypatch.setattr(rationale, "_call_synthesis",
                        lambda query, *a, **k: seen.setdefault("synthesis", query) and {"content_gaps": []})
    candidate = Candidate(content_id="babylon:x", display_name="X", content_type="lab", source="babylon",
                          summary="s", products=[], topics=[])
    db_stub = Mock()
    db_stub.get_display_analysis.return_value = {}
    state = QueryState(phase="TRIAGE_DONE", candidates=[candidate], query="Something similar to LB1237",
                       references=[{"display_name": "LB1237", "summary": "Covers RHEL on CNV."}])
    result = rationale.generate_rationale(state, db_stub, settings=Mock(triage_model="m"), driver=None, top_n=1)
    assert "Covers RHEL on CNV." in seen["single"]
    assert "Covers RHEL on CNV." in seen["synthesis"]
    assert result.references == state.references


def test_reference_without_an_embedding_is_still_excluded_and_described(db, monkeypatch):
    vci, lab = ref(db, "virtual.prod", 9112, analysis=False), item(db, "lab.prod")
    link(db, vci, lab)
    other = item(db, "other.prod")
    state = run_similar(db, monkeypatch, 9112, [(lab, 0.9), (vci, 0.9), (other, 0.8)], embedding=None)
    assert card_ids(state.candidates) == [other]
    assert state.references[0]["summary"] == "About lab.prod"


def test_keyword_match_without_a_lab_number_keeps_the_matched_item_in_the_results(db, monkeypatch):
    """A topic search that happens to match a display name is not a "similar to" request."""
    vci = item(db, "virtual.prod", analysis=False,
               ci_extra={"display_name": "OpenShift Virtualization Networking"})
    lab = item(db, "lab.prod")
    link(db, vci, lab)
    other = item(db, "other.prod")
    monkeypatch.setattr(db, "find_catalog_item_by_keyword_overlap", lambda *a, **k: db.get_babylon_item(vci) | db.get_content_entity(vci))
    state = run_similar(db, monkeypatch, 0, [(lab, 0.9), (other, 0.8)],
                        query="OpenShift Virtualization Networking")
    assert card_ids(state.candidates) == sorted([vci, other])
    assert state.references == []


def test_stage_copy_of_a_stub_owner_is_excluded_too(db, monkeypatch):
    owner, owner_dev = item(db, "owner.prod"), item(db, "owner.dev")
    stub = add_stub(db, "isolation-test.owner.prod", "isolation-test.lb-stub.prod")
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET display_name = 'LB9113 stub' WHERE content_id = %s", (stub,))
    other = item(db, "other.prod")
    state = run_similar(db, monkeypatch, 9113, [(owner, 0.9), (owner_dev, 0.9), (other, 0.8)],
                        stages=("prod", "dev"))
    assert card_ids(state.candidates) == [other]
