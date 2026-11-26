"""The single owners of "same content" and "analysis_config". Pure: no DB, no Git."""
from dataclasses import replace

import pytest

from rcars.services import analysis_identity as ident
from rcars.services import analyzer
from rcars.services.showroom_source import SHOWROOM_ANALYSIS_POLICY_VERSION, AnalysisSignature

CONFIG = "config-a"


def donor_row(**changes):
    signature = AnalysisSignature("example.item", "https://git.example.com/org/repo", "main", None,
                                  "a" * 40, "hash-a", CONFIG, "input-a", SHOWROOM_ANALYSIS_POLICY_VERSION)
    row = {"content_hash": "hash-a", "entity_content_type": "lab",
           "analysis_provenance_json": {"signature": signature.to_dict()}}
    for key, value in changes.items():
        if key == "row_hash":  # stored row hash only
            row["content_hash"] = value
        elif key in signature.to_dict():
            row["analysis_provenance_json"]["signature"][key] = value
            if key == "content_hash":
                row["content_hash"] = value
        else:
            row[key] = value
    return row


# ── content_hash: the one "same content" rule ──

def test_content_hash_has_one_owner():
    assert analyzer.hash_showroom_content is ident.compute_content_hash


def test_content_hash_ignores_whitespace_line_endings_and_file_order():
    first = {"b.adoc": "= B\n\nBody  \n\n\n\nMore", "a.adoc": "= A\r\n\r\nText"}
    second = {"a.adoc": "= A\n\nText\n\n", "b.adoc": "= B\n\nBody\n\nMore"}
    assert ident.compute_content_hash(first) == ident.compute_content_hash(second)


def test_content_hash_changes_with_file_name_or_text():
    base = {"a.adoc": "= A\n\nText"}
    assert ident.compute_content_hash(base) != ident.compute_content_hash({"b.adoc": "= A\n\nText"})
    assert ident.compute_content_hash(base) != ident.compute_content_hash({"a.adoc": "= A\n\nOther"})


def test_empty_content_hash_is_never_a_reusable_key():
    empty = ident.compute_content_hash({})
    assert empty == ident.EMPTY_CONTENT_HASH
    assert not ident.donor_matches_content(donor_row(content_hash=empty), content_hash=empty,
                                           analysis_config=CONFIG, entity_content_type="lab")


# ── analysis_config ──

def config(**changes):
    args = dict(entity_content_type="lab", model="example-model")
    return ident.compute_analysis_config(**{**args, **changes})


def test_config_is_stable_and_follows_model_and_policy(monkeypatch):
    base = config()
    assert config() == base
    assert config(model="other-model") != base
    monkeypatch.setattr(ident, "SHOWROOM_ANALYSIS_POLICY_VERSION", SHOWROOM_ANALYSIS_POLICY_VERSION + 1)
    assert config() != base


def test_config_follows_prompt_template_and_vocabulary(monkeypatch):
    base = config()
    original = analyzer.build_analysis_prompt
    monkeypatch.setattr(analyzer, "build_analysis_prompt", lambda *a, **k: ("Changed prompt", original(*a, **k)[1]))
    assert config() != base


def test_config_follows_content_type_when_vocabulary_mode_differs():
    assert config(entity_content_type="architecture") != config(entity_content_type="lab")


def test_prompt_carries_only_content_and_entity_content_type():
    """The content prompt must not name the item; item fields come from the catalog row."""
    system, user_message = analyzer.build_analysis_prompt(
        {"m1.adoc": "= Module one\n\nSome content"}, entity_content_type="lab")
    assert user_message == "## Showroom Content\n\n=== File: m1.adoc ===\n= Module one\n\nSome content"
    for item_field in ("## Item Information", "- CI Name:", "- Display Name:",
                       "- Category:", "- Product:"):
        assert item_field not in system and item_field not in user_message


def test_two_items_with_the_same_content_and_type_share_the_analysis_config():
    """Different CI name, display name, category and product must not change the config."""
    item = dict(content_type="lab", display_name="Lab One", category="Workshop", product="OpenShift")
    other = dict(content_type="lab", display_name="Lab Two (prod)", category="Demo", product="Ansible")
    assert (analyzer._item_analysis_config(item, "example-model")
            == analyzer._item_analysis_config(other, "example-model"))
    assert (analyzer._item_analysis_config(item, "example-model")
            != analyzer._item_analysis_config({**other, "content_type": "architecture"}, "example-model"))


def test_policy_version_bump_marks_an_older_analysis_as_not_current():
    """The policy bump is what forces the one-time rescan after the prompt change."""
    from rcars.services.showroom_source import ResolvedShowroom, signature_matches_source
    source = ResolvedShowroom("resolved", "example.item.prod", "example.item",
                              "https://git.example.com/org/repo", "main", None,
                              paths=(("example.item.prod",),))
    current = dict(scope_key="example.item", repo=source.repo, ref="main", content_path=None,
                   commit="a" * 40, content_hash="hash-a", context_hash=config(), input_hash="input-a",
                   policy_version=SHOWROOM_ANALYSIS_POLICY_VERSION)
    assert signature_matches_source(current, source)
    older = {**current, "policy_version": SHOWROOM_ANALYSIS_POLICY_VERSION - 1}
    assert not signature_matches_source(older, source)


def test_policy_version_was_bumped_for_the_content_only_prompt():
    assert SHOWROOM_ANALYSIS_POLICY_VERSION == 2


# ── pre-clone key ──

def test_pre_clone_key_ignores_ref_name_and_ci_but_not_content_inputs():
    key = ident.pre_clone_key("https://git.example.com/org/repo", "a" * 40, None, CONFIG, "lab")
    assert key == ident.pre_clone_key("https://git.example.com/org/repo", "a" * 40, None, CONFIG, "lab")
    assert key != ident.pre_clone_key("https://git.example.com/org/other", "a" * 40, None, CONFIG, "lab")
    assert key != ident.pre_clone_key("https://git.example.com/org/repo", "b" * 40, None, CONFIG, "lab")
    assert key != ident.pre_clone_key("https://git.example.com/org/repo", "a" * 40, "docs", CONFIG, "lab")
    assert key != ident.pre_clone_key("https://git.example.com/org/repo", "a" * 40, None, "config-b", "lab")
    assert key != ident.pre_clone_key("https://git.example.com/org/repo", "a" * 40, None, CONFIG, "demo")


# ── donor matchers: the invariant "reuse only when content_hash + analysis_config match" ──

def test_content_donor_matches_on_hash_config_and_type_only():
    kwargs = dict(content_hash="hash-a", analysis_config=CONFIG, entity_content_type="lab")
    assert ident.donor_matches_content(donor_row(), **kwargs)
    # Ref names, CI names, commits, repos, paths and input hashes never count.
    for field, value in (("ref", "v1.2"), ("scope_key", "example.other"), ("commit", "f" * 40),
                         ("repo", "https://git.example.com/org/fork"), ("content_path", "docs"),
                         ("input_hash", "other")):
        assert ident.donor_matches_content(donor_row(**{field: value}), **kwargs), field


@pytest.mark.parametrize("changes", [
    {"content_hash": "hash-b"},                       # donor hashed other files
    {"row_hash": "hash-b"},                           # stored row hash differs from its signature
    {"analysis_provenance_json": {}},                 # legacy row, no signature
    {"entity_content_type": "architecture"},
    {"context_hash": "config-b"},
    {"policy_version": SHOWROOM_ANALYSIS_POLICY_VERSION + 1},
    {"repo": "description:example.item.prod"},        # description analyses are never Showroom donors
])
def test_content_donor_rejected_when_any_key_part_differs(changes):
    assert not ident.donor_matches_content(donor_row(**changes), content_hash="hash-a",
                                           analysis_config=CONFIG, entity_content_type="lab")


def test_content_donor_rejected_when_signature_hash_differs_from_row_hash():
    row = donor_row()
    row["analysis_provenance_json"]["signature"]["content_hash"] = "hash-b"
    assert not ident.donor_matches_content(row, content_hash="hash-a", analysis_config=CONFIG,
                                           entity_content_type="lab")


def test_commit_donor_needs_repo_commit_path_and_config():
    kwargs = dict(repo="https://git.example.com/org/repo", commit="a" * 40, content_path=None,
                  analysis_config=CONFIG, entity_content_type="lab")
    assert ident.donor_matches_commit(donor_row(), **kwargs)
    assert ident.donor_matches_commit(donor_row(ref="v1", scope_key="example.other"), **kwargs)  # ref never counts
    for field, value in (("repo", "https://git.example.com/org/other"), ("commit", "b" * 40),
                         ("content_path", "docs"), ("context_hash", "config-b"),
                         ("policy_version", SHOWROOM_ANALYSIS_POLICY_VERSION + 1)):
        assert not ident.donor_matches_commit(donor_row(**{field: value}), **kwargs), field
    assert not ident.donor_matches_commit(donor_row(entity_content_type="demo"), **kwargs)


def test_signature_exposes_analysis_config():
    signature = AnalysisSignature("s", "r", None, None, "c", "h", "config-a", "i", 1)
    assert signature.analysis_config == "config-a"
    assert replace(signature, context_hash="x").analysis_config == "x"
