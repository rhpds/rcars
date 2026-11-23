"""Catalog family data (RHDPCD-2297 PR 1): content-anchor walk and storage."""
from unittest.mock import Mock

import pytest

from rcars.services.catalog import CatalogReader, build_catalog_families
from rcars.services.showroom_source import (
    ComponentLink, ContentDeclaration, SourceNode, declares_or_overrides_content, family_members,
)
from tests.showroom_helpers import db  # noqa: F401  (fixture)

URL = "https://github.com/example/content"


def node(name, repo=None, ref=None, path=None, links=(), overrides=None):
    """links: names, or (name, {override fields}) pairs."""
    fields = {k: v for k, v in (("repo", repo), ("ref", ref), ("content_path", path)) if v is not None}
    built = []
    for link in links:
        target, over = (link, {}) if isinstance(link, str) else link
        built.append(ComponentLink(target, dict(over)))
    return SourceNode(name, name.rsplit(".", 1)[-1],
                      ContentDeclaration(repo, ref, path, frozenset(overrides if overrides is not None else fields)),
                      tuple(built))


def graph(*nodes):
    return {n.ci_name: n for n in nodes}


def members(vci, nodes):
    return {m.ci_name: (m.role, m.depth) for m in family_members(vci, nodes)}


# ── the single content-node test ──

def test_declaration_overrides_and_templated_values_count_as_content():
    assert declares_or_overrides_content(node("a.x.prod", repo=URL))
    assert declares_or_overrides_content(node("a.x.prod", ref="main"))
    assert declares_or_overrides_content(node("a.x.prod", repo="{{ user_repo | default('') }}"))
    assert declares_or_overrides_content(node("a.x.prod", links=[("a.y.prod", {"ref": "v1"})]))
    assert not declares_or_overrides_content(node("a.x.prod", links=["a.y.prod"]))
    assert not declares_or_overrides_content(node("a.x.prod"))


# ── family_members ──

def four_level():
    return graph(
        node("agd-v2.ocp-cluster-cnv-pools.prod"),
        node("agd-v2.ocp-cluster-cnv.prod", links=["agd-v2.ocp-cluster-cnv-pools.prod"]),
        node("agd-v2.ocp-field-asset-cnv.prod", repo="{{ field_repo | default('') }}",
             links=["agd-v2.ocp-cluster-cnv.prod"]),
        node("published.ocp-field-asset.prod", links=["agd-v2.ocp-field-asset-cnv.prod"]),
        node("published.ocp-field-asset-shared.prod", links=["agd-v2.ocp-field-asset-cnv.prod"]),
        node("openshift-cnv.some-lab-cnv.prod", repo=URL, links=["agd-v2.ocp-cluster-cnv.prod"]),
        node("published.some-lab.prod", links=["openshift-cnv.some-lab-cnv.prod"]),
    )


def test_four_level_fixture_two_virtual_cis_share_the_fsc_member():
    nodes = four_level()
    assert members("published.ocp-field-asset.prod", nodes) == {"agd-v2.ocp-field-asset-cnv.prod": ("anchor", 1)}
    assert members("published.ocp-field-asset-shared.prod", nodes) == {
        "agd-v2.ocp-field-asset-cnv.prod": ("anchor", 1)}
    assert members("published.some-lab.prod", nodes) == {"openshift-cnv.some-lab-cnv.prod": ("anchor", 1)}


def test_four_level_fixture_never_includes_base_cluster_or_pool():
    nodes = four_level()
    for vci in ("published.ocp-field-asset.prod", "published.ocp-field-asset-shared.prod",
                "published.some-lab.prod"):
        found = set(members(vci, nodes))
        assert "agd-v2.ocp-cluster-cnv.prod" not in found
        assert "agd-v2.ocp-cluster-cnv-pools.prod" not in found


def test_passthrough_wrapper_between_virtual_ci_and_lab():
    nodes = graph(
        node("a.pool.prod"),
        node("a.lab.prod", repo=URL, links=["a.pool.prod"]),
        node("a.wrapper.prod", links=["a.lab.prod"]),
        node("published.x.prod", links=["a.wrapper.prod"]),
    )
    assert members("published.x.prod", nodes) == {"a.wrapper.prod": ("passthrough", 1), "a.lab.prod": ("anchor", 2)}


def test_zt_lab_with_link_override_is_anchor_and_template_stays_out():
    nodes = graph(
        node("zt.template.prod", repo=URL, ref="main"),
        node("zt.lab.prod", links=[("zt.template.prod", {"ref": "lab-branch"})]),
        node("published.zt.prod", links=["zt.lab.prod"]),
    )
    assert members("published.zt.prod", nodes) == {"zt.lab.prod": ("anchor", 1)}


def test_plain_zt_labs_on_one_template_have_no_family():
    nodes = graph(
        node("zt.template.prod", repo=URL),
        node("zt.lab1.prod", links=[("zt.template.prod", {"ref": "a"})]),
        node("zt.lab2.prod", links=[("zt.template.prod", {"ref": "b"})]),
    )
    result = build_catalog_families([_item("zt.lab1.prod"), _item("zt.lab2.prod")], nodes)
    assert result.members == []


def test_virtual_ci_wrapping_cnv_and_aws_has_both():
    nodes = graph(
        node("a.pool.prod"),
        node("a.lab-cnv.prod", repo=URL, links=["a.pool.prod"]),
        node("a.lab-aws.prod", repo=URL, links=["a.pool.prod"]),
        node("published.both.prod", links=["a.lab-cnv.prod", "a.lab-aws.prod"]),
    )
    assert members("published.both.prod", nodes) == {"a.lab-cnv.prod": ("anchor", 1), "a.lab-aws.prod": ("anchor", 1)}


def test_no_anchor_virtual_ci_has_no_family_and_no_passthrough_members():
    nodes = graph(
        node("a.pool.prod"),
        node("a.cluster.prod", links=["a.pool.prod"]),
        node("published.cluster.prod", links=["a.cluster.prod"]),
    )
    assert family_members("published.cluster.prod", nodes) == []


def test_only_paths_that_reach_an_anchor_contribute_members():
    nodes = graph(
        node("a.lab.prod", repo=URL),
        node("a.cluster.prod"),
        node("a.wrapper.prod", links=["a.cluster.prod"]),
        node("published.mixed.prod", links=["a.lab.prod", "a.wrapper.prod"]),
    )
    assert members("published.mixed.prod", nodes) == {"a.lab.prod": ("anchor", 1)}


def test_virtual_ci_that_declares_content_itself_has_no_members():
    nodes = graph(node("a.lab.prod", repo=URL), node("published.own.prod", repo=URL, links=["a.lab.prod"]))
    assert family_members("published.own.prod", nodes) == []


def test_virtual_ci_that_overrides_content_on_its_link_has_no_members():
    nodes = graph(node("a.lab.prod", repo=URL),
                  node("published.own.prod", links=[("a.lab.prod", {"ref": "v2"})]))
    assert family_members("published.own.prod", nodes) == []


def test_missing_and_excluded_components_are_skipped():
    nodes = graph(
        node("a.lab.prod", repo=URL),
        node("published.x.prod", links=["a.missing.prod", "tests.hidden.prod", "a.lab.prod"]),
        node("tests.hidden.prod", repo=URL),
    )
    assert members("published.x.prod", nodes) == {"a.lab.prod": ("anchor", 1)}


def test_same_names_in_prod_and_dev_form_separate_families():
    nodes = graph(
        node("a.lab.prod", repo=URL), node("published.x.prod", links=["a.lab.prod"]),
        node("a.lab.dev", repo=URL + "/dev"), node("published.x.dev", links=["a.lab.dev"]),
    )
    assert members("published.x.prod", nodes) == {"a.lab.prod": ("anchor", 1)}
    assert members("published.x.dev", nodes) == {"a.lab.dev": ("anchor", 1)}


# ── build_catalog_families ──

def _item(name):
    return {"ci_name": name, "is_published": name.startswith("published.")}


def test_build_rows_and_summary_for_four_level_fixture():
    nodes = four_level()
    items = [_item(n) for n in nodes if n.startswith(("published.", "openshift-cnv."))]
    result = build_catalog_families(items, nodes)
    assert {(m["virtual_content_id"], m["member_content_id"], m["role"], m["depth"]) for m in result.members} == {
        ("babylon:published.ocp-field-asset.prod", "babylon:agd-v2.ocp-field-asset-cnv.prod", "anchor", 1),
        ("babylon:published.ocp-field-asset-shared.prod", "babylon:agd-v2.ocp-field-asset-cnv.prod", "anchor", 1),
        ("babylon:published.some-lab.prod", "babylon:openshift-cnv.some-lab-cnv.prod", "anchor", 1),
    }
    assert result.summary["virtual_cis"] == 3
    assert result.summary["with_members"] == 3
    assert result.summary["without_anchor"] == []
    assert result.summary["shared_members"] == {
        "agd-v2.ocp-field-asset-cnv.prod": ["published.ocp-field-asset-shared.prod", "published.ocp-field-asset.prod"]}


def test_build_keeps_all_component_links_with_position_and_override_flag():
    nodes = four_level()
    nodes.update(graph(node("zt.template.prod", repo=URL),
                       node("zt.lab.prod", links=[("zt.template.prod", {"ref": "x"}), "a.other.prod"])))
    result = build_catalog_families([], nodes)
    rows = {(c["parent_content_id"], c["child_ci_name"]): c for c in result.components}
    assert rows[("babylon:zt.lab.prod", "zt.template.prod")] == {
        "parent_content_id": "babylon:zt.lab.prod", "child_ci_name": "zt.template.prod",
        "position": 0, "has_content_override": True}
    assert rows[("babylon:zt.lab.prod", "a.other.prod")]["position"] == 1
    assert rows[("babylon:zt.lab.prod", "a.other.prod")]["has_content_override"] is False
    # pools and base clusters are links too: ALL links are kept
    assert ("babylon:agd-v2.ocp-cluster-cnv.prod", "agd-v2.ocp-cluster-cnv-pools.prod") in rows
    assert len(result.components) == sum(len(n.links) for n in nodes.values())


def test_build_reports_virtual_cis_without_anchor():
    nodes = graph(node("a.pool.prod"), node("published.cluster.prod", links=["a.pool.prod"]))
    result = build_catalog_families([_item("published.cluster.prod")], nodes)
    assert result.summary["without_anchor"] == ["published.cluster.prod"]
    assert result.summary["with_members"] == 0


def test_build_only_walks_published_items():
    nodes = graph(node("a.lab.prod", repo=URL), node("a.plain.prod", links=["a.lab.prod"]))
    result = build_catalog_families([_item("a.plain.prod")], nodes)
    assert result.members == [] and result.summary["virtual_cis"] == 0


def test_refresh_catalog_graph_returns_nodes_and_refresh_catalog_is_unchanged():
    definitions = {
        "example.virtual.prod": {"__meta__": {"components": [{"item": "example/content"}]}},
        "example.content.prod": {"showroom_git_repo": URL},
    }
    crds = [{"metadata": {"name": "example.virtual.prod", "labels": {"babylon.gpte.redhat.com/stage": "prod"}},
             "spec": {}}]
    reader = CatalogReader.__new__(CatalogReader)
    reader.list_catalog_items = Mock(return_value=crds)
    reader.get_agnosticv_component = Mock(side_effect=lambda name, ns: {"spec": {"definition": definitions[name]}})
    items, nodes = reader.refresh_catalog_graph(["example"])
    assert set(nodes) == set(definitions)
    assert [i["ci_name"] for i in reader.refresh_catalog(["example"])] == [i["ci_name"] for i in items]


# ── database ──

def _clean(db):
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM catalog_family_members WHERE virtual_content_id LIKE 'babylon:isolation-test.%'")
        conn.execute("DELETE FROM catalog_components WHERE parent_content_id LIKE 'babylon:isolation-test.%'")


def _rows(db, table):
    with db.pool.connection() as conn:
        return conn.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()


def test_replace_catalog_families_replaces_all_rows_in_one_transaction(db):
    _clean(db)
    comps = [{"parent_content_id": "babylon:isolation-test.v.prod", "child_ci_name": "isolation-test.c.prod",
              "position": 0, "has_content_override": False}]
    mems = [{"virtual_content_id": "babylon:isolation-test.v.prod",
             "member_content_id": "babylon:isolation-test.c.prod", "role": "anchor", "depth": 1}]
    try:
        db.replace_catalog_families(comps, mems)
        assert [r for r in _rows(db, "catalog_family_members") if r["virtual_content_id"].startswith(
            "babylon:isolation-test.")] == [{**mems[0]}]
        db.replace_catalog_families([], [])
        assert [r for r in _rows(db, "catalog_family_members") if r["virtual_content_id"].startswith(
            "babylon:isolation-test.")] == []
    finally:
        _clean(db)


def test_replace_catalog_families_rolls_back_on_failure(db):
    _clean(db)
    good = {"parent_content_id": "babylon:isolation-test.v.prod", "child_ci_name": "isolation-test.c.prod",
            "position": 0, "has_content_override": False}
    db.replace_catalog_families([good], [])
    try:
        with pytest.raises(Exception):
            db.replace_catalog_families(
                [{**good, "child_ci_name": "isolation-test.new.prod"}],
                [{"virtual_content_id": "babylon:isolation-test.v.prod",
                  "member_content_id": "babylon:isolation-test.c.prod", "role": "anchor", "depth": 1}] * 2)
        kept = [r for r in _rows(db, "catalog_components") if r["parent_content_id"].startswith(
            "babylon:isolation-test.")]
        assert [r["child_ci_name"] for r in kept] == ["isolation-test.c.prod"]
    finally:
        _clean(db)


def test_member_primary_key_allows_one_component_under_two_virtual_cis(db):
    _clean(db)
    mems = [{"virtual_content_id": f"babylon:isolation-test.{v}.prod",
             "member_content_id": "babylon:isolation-test.fsc.prod", "role": "anchor", "depth": 1}
            for v in ("a", "b")]
    try:
        db.replace_catalog_families([], mems)
        assert len([r for r in _rows(db, "catalog_family_members") if r["member_content_id"] ==
                    "babylon:isolation-test.fsc.prod"]) == 2
    finally:
        _clean(db)


def test_upsert_sets_stage_key_for_babylon_items(db):
    content_id = db.upsert_babylon_catalog_item({
        "ci_name": "isolation-test.stagekey.prod", "stage": "prod", "display_name": "Stage key"})
    assert db.get_content_entity(content_id)["stage_key"] == "isolation-test.stagekey"


def test_backfill_stage_key_babylon_and_non_babylon(db):
    content_id = db.upsert_babylon_catalog_item({
        "ci_name": "isolation-test.backfill.event", "stage": "event", "display_name": "Backfill"})
    with db.pool.connection() as conn:
        conn.execute("UPDATE content_entities SET stage_key = NULL WHERE content_id = %s", (content_id,))
        conn.execute("""INSERT INTO content_entities (content_id, source, content_type, display_name)
                        VALUES ('osspa:isolation-test-pa', 'portfolio_arch', 'architecture', 'PA')
                        ON CONFLICT (content_id) DO UPDATE SET stage_key = NULL""")
    try:
        db.backfill_stage_keys()
        assert db.get_content_entity(content_id)["stage_key"] == "isolation-test.backfill"
        assert db.get_content_entity("osspa:isolation-test-pa")["stage_key"] == "osspa:isolation-test-pa"
        db.backfill_stage_keys()  # idempotent
    finally:
        with db.pool.connection() as conn:
            conn.execute("DELETE FROM content_entities WHERE content_id = 'osspa:isolation-test-pa'")


@pytest.mark.asyncio
async def test_catalog_refresh_job_writes_families_after_upserts(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from rcars.workers import ops

    nodes = graph(node("a.lab.prod", repo=URL), node("published.x.prod", links=["a.lab.prod"]))
    items = [_item("published.x.prod"), _item("a.lab.prod")]
    calls = []
    db = Mock()
    db.upsert_babylon_catalog_item.side_effect = lambda item: calls.append("upsert") or f"babylon:{item['ci_name']}"
    db.retire_missing_babylon.side_effect = lambda ids: calls.append("retire") or []
    db.replace_catalog_families.side_effect = lambda c, m: calls.append("families")
    wctx = SimpleNamespace(db=db, relay=Mock(), settings=SimpleNamespace(
        kubeconfig_path="", catalog_namespaces=["example"], agnosticv_component_namespace="x"))
    monkeypatch.setattr(ops, "publish_progress", AsyncMock())
    monkeypatch.setattr(ops, "CatalogReader", lambda **kw: SimpleNamespace(
        refresh_catalog_graph=lambda **k: (items, nodes)))
    await ops.run_catalog_refresh({"worker_ctx": wctx}, "job-1")
    assert calls == ["upsert", "upsert", "retire", "families"]
    components, members = db.replace_catalog_families.call_args.args
    assert [m["member_content_id"] for m in members] == ["babylon:a.lab.prod"]


def test_duplicate_virtual_ci_names_from_two_namespaces_give_one_family():
    nodes = graph(node("a.lab.prod", repo=URL), node("published.x.prod", links=["a.lab.prod"]))
    result = build_catalog_families([_item("published.x.prod"), _item("published.x.prod")], nodes)
    assert len(result.members) == 1 and result.summary["virtual_cis"] == 1


@pytest.mark.asyncio
async def test_catalog_refresh_job_keeps_stored_families_on_empty_scan(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from rcars.workers import ops

    db = Mock()
    db.retire_missing_babylon.return_value = []
    wctx = SimpleNamespace(db=db, relay=Mock(), settings=SimpleNamespace(
        kubeconfig_path="", catalog_namespaces=["example"], agnosticv_component_namespace="x"))
    monkeypatch.setattr(ops, "publish_progress", AsyncMock())
    monkeypatch.setattr(ops, "CatalogReader", lambda **kw: SimpleNamespace(
        refresh_catalog_graph=lambda **k: ([], {})))
    await ops.run_catalog_refresh({"worker_ctx": wctx}, "job-2")
    db.replace_catalog_families.assert_not_called()
