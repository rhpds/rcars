"""Content ownership must come from explicit paths, never shared infra/URLs."""
from unittest.mock import Mock

import pytest

from rcars.services.showroom_source import (
    ComponentLink, ContentDeclaration, SourceNode, ResolvedShowroom,
    item_family_key, resolve_showroom_source,
)

URL = "https://github.com/example/content"


def node(name, *, repo=None, ref=None, path=None, fields=None, links=()):
    fields = fields if fields is not None else {
        key for key, value in (("repo", repo), ("ref", ref), ("content_path", path))
        if value is not None
    }
    return SourceNode(name, name.rsplit(".", 1)[-1],
                      ContentDeclaration(repo, ref, path, frozenset(fields)),
                      tuple(ComponentLink(link, {}) if isinstance(link, str) else link for link in links))


def resolve(*nodes):
    return resolve_showroom_source(nodes[0].ci_name, {n.ci_name: n for n in nodes})


def test_four_level_chain_stops_at_content_owner():
    result = resolve(node("example.virtual.prod", links=("example.wrapper.prod",)),
                     node("example.wrapper.prod", links=("example.content.prod",)),
                     node("example.content.prod", repo=URL, links=("example.infra.prod",)),
                     node("example.infra.prod", repo=URL + "/infra"))
    assert result.status == "resolved"
    assert result.owner_ci_name == "example.content.prod"
    assert result.scope_key == "example.content"
    assert result.paths == (("example.virtual.prod", "example.wrapper.prod", "example.content.prod"),)
    assert ResolvedShowroom.from_dict(result.to_dict()) == result


def test_independent_roots_with_own_same_url_have_distinct_scopes():
    assert resolve(node("example.a.prod", repo=URL)).scope_key == "example.a"
    assert resolve(node("example.b.prod", repo=URL)).scope_key == "example.b"
    assert item_family_key("other.lb123.dev", "prod") == "other.lb123.dev"
    assert item_family_key("other.lb123.prod", "prod") == "other.lb123"


@pytest.mark.parametrize("stage", ["dev", "event", "prod"])
def test_stage_paths_resolve_independently(stage):
    result = resolve(node(f"example.a.{stage}", links=(f"example.content.{stage}",)),
                     node(f"example.content.{stage}", repo=URL, ref=stage))
    assert result.ref == stage
    assert result.owner_ci_name == f"example.content.{stage}"


@pytest.mark.parametrize("field,value", [("ref", "feature"), ("repo", URL + "/other"),
                                         ("content_path", "other/pages")])
def test_ref_override_creates_requester_scope(field, value):
    result = resolve(node("example.wrapper.prod", links=(ComponentLink("example.content.prod", {field: value}),)),
                     node("example.content.prod", repo=URL, ref="main"))
    assert getattr(result, field) == value
    assert result.scope_key == "example.wrapper"
    assert result.override_origins[field] == "example.wrapper.prod"
    assert result.owner_ci_name == "example.content.prod"


def test_explicit_default_head_does_not_inherit_deeper_ref():
    result = resolve(node("example.a.prod", fields={"ref"}, links=("example.b.prod",)),
                     node("example.b.prod", repo=URL, ref="pinned"))
    assert result.ref is None
    assert result.scope_key == "example.a"


@pytest.mark.parametrize("on_edge", [False, True])
def test_nearer_valid_override_replaces_unresolved_deeper_value(on_edge):
    root = (node("example.wrapper.prod", links=(ComponentLink("example.content.prod", {"ref": "release"}),))
            if on_edge else node("example.wrapper.prod", ref="release", links=("example.content.prod",)))
    result = resolve(root, node("example.content.prod", repo=URL, ref="{{ unavailable }}"))
    assert result.status == "resolved"
    assert result.ref == "release"
    assert result.scope_key == "example.wrapper"
    assert result.override_origins["ref"] == "example.wrapper.prod"


def test_nearest_override_also_shadows_unresolved_intermediate_edge():
    result = resolve(node("a.prod", ref="release", links=("b.prod",)),
        node("b.prod", links=(ComponentLink("owner.prod", {"ref": "{{ unavailable }}"}),)),
        node("owner.prod", repo=URL, ref="main"))
    assert result.status == "resolved"
    assert result.ref == "release"


def test_branch_with_two_sources_is_ambiguous():
    result = resolve(node("example.a.prod", links=("example.b.prod", "example.c.prod")),
                     node("example.b.prod", repo=URL), node("example.c.prod", repo=URL))
    assert result.status == "ambiguous"
    assert len(result.paths) == 2
    assert result.error


def test_converging_paths_to_one_owner_are_unambiguous():
    result = resolve(node("a.prod", links=("b.prod", "c.prod")),
                     node("b.prod", links=("owner.prod",)), node("c.prod", links=("owner.prod",)),
                     node("owner.prod", repo=URL))
    assert result.status == "resolved"
    assert result.paths == (("a.prod", "b.prod", "owner.prod"), ("a.prod", "c.prod", "owner.prod"))


@pytest.mark.parametrize("kind", ["cycle", "missing_dependency", "unresolved"])
def test_invalid_graph_is_visible(kind):
    a = node("a.prod", links=("b.prod",))
    b = node("b.prod", links=("a.prod",)) if kind == "cycle" else node("b.prod", repo="{{ missing }}")
    result = resolve(a, *(() if kind == "missing_dependency" else (b,)))
    assert result.status == "invalid"
    assert kind in result.error
    assert result.paths


@pytest.mark.parametrize("length,status", [(32, "resolved"), (33, "invalid")])
def test_depth_32_allowed_33_invalid(length, status):
    nodes = [node(f"n{i}.prod", links=(f"n{i+1}.prod",)) for i in range(length - 1)]
    nodes.append(node(f"n{length-1}.prod", repo=URL))
    assert resolve(*nodes).status == status


def test_no_source_is_none():
    result = resolve(node("a.prod", links=("b.prod",)), node("b.prod"))
    assert result.status == "none"
    assert result.paths == (("a.prod", "b.prod"),)


def test_legacy_url_extractor_does_not_pick_first_ambiguous_override():
    from rcars.services.catalog import extract_showroom_url
    crd = {"spec": {"definition": {"__meta__": {"components": [
        {"item": "example/a", "parameter_values": {"showroom_git_repo": URL}},
        {"item": "example/b", "parameter_values": {"showroom_git_repo": URL + "/other"}},
    ]}}}}
    assert extract_showroom_url(crd) == (None, None)


@pytest.mark.parametrize("reverse", [False, True])
def test_owner_need_not_have_catalogitem_and_adapter_order_is_independent(reverse):
    from rcars.services.catalog import CatalogReader
    components = {
        "example.virtual.prod": {"__meta__": {"components": [{"item": "example/wrapper"}]}},
        "example.wrapper.prod": {"__meta__": {"components": [{"item": "example/content", "parameter_values": {
            "showroom_git_ref": "{{ revision }}"}}]}, "revision": "feature"},
        "example.content.prod": {"showroom_git_repo": URL, "showroom_git_ref": "main"},
        "example.other.prod": {"showroom_git_repo": URL},
    }
    crds = [{"metadata": {"name": name, "labels": {"babylon.gpte.redhat.com/stage": "prod"}},
             "spec": {}} for name in ("example.virtual.prod", "example.other.prod", "example.content.prod")]
    reader = CatalogReader.__new__(CatalogReader)
    reader.list_catalog_items = Mock(return_value=list(reversed(crds)) if reverse else crds)
    reader.get_agnosticv_component = Mock(side_effect=lambda name, ns: {"spec": {"definition": components[name]}})
    rows = {row["ci_name"]: row for row in reader.refresh_catalog(["example"])}
    source = rows["example.virtual.prod"]["showroom_source"]
    assert source["owner_ci_name"] == "example.content.prod"
    assert source["scope_key"] == "example.wrapper"
    assert source["ref"] == "feature"
    assert source["paths"] == [["example.virtual.prod", "example.wrapper.prod", "example.content.prod"]]
    assert rows["example.other.prod"]["showroom_source"]["scope_key"] == "example.other"
    fetched_names = [call.args[0] for call in reader.get_agnosticv_component.call_args_list]
    assert sorted(fetched_names) == sorted(components)
