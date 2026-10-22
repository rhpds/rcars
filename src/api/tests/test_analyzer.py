import json
import subprocess
from pathlib import Path

import pytest

from rcars.services.analyzer import parse_analysis_response


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "remote"
    repo.mkdir()

    def git(*args):
        if args[0] == "commit":
            args = ("commit", "-m", f"[RHDPCD-74] Create test fixture: {args[2]}\n\nGenerated with OpenCode (openai/gpt-6.1-sol)")
        return subprocess.run(["git", "-C", str(repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    pages = repo / "content/modules/ROOT/pages"
    pages.mkdir(parents=True)
    (pages / "index.adoc").write_text("= Overview\n\nConfigure post-quantum TLS with OpenSSL.\n")
    git("add", ".")
    git("commit", "-m", "Initial")
    first = git("rev-parse", "HEAD")
    git("tag", "light")
    git("tag", "-a", "annotated", "-m", "Annotated")
    git("branch", "feature")
    (repo / "README.md").write_text("Not selected lab content")
    git("add", ".")
    git("commit", "-m", "Unrelated change")
    second = git("rev-parse", "HEAD")
    git("tag", "feature")  # different branch/tag targets must not pick the first
    return repo, git, first, second


@pytest.mark.parametrize("ref,revision", [("main", 3), ("light", 2), ("annotated", 2),
    ("refs/heads/feature", 2), ("refs/tags/feature", 3), (None, 3), ("HEAD", 3), ("commit", 2)])
def test_exact_branch_tag_and_commit_fetch(git_repo, tmp_path, ref, revision):
    from rcars.services.analyzer import clone_showroom, get_repo_head
    repo, _, first, _ = git_repo
    if ref == "commit":
        ref = first
    clone = clone_showroom(str(repo), ref, str(tmp_path))
    assert clone is not None
    assert get_repo_head(clone)[0] == git_repo[revision]


@pytest.mark.parametrize("ref", ["missing", "feature"])
def test_missing_or_ambiguous_ref_never_falls_back(git_repo, tmp_path, ref):
    from rcars.services.analyzer import clone_showroom, classify_scan_error
    try:
        clone = clone_showroom(str(git_repo[0]), ref, str(tmp_path))
    except ValueError as exc:
        assert classify_scan_error(exc)[0] == "invalid_ref"
    else:
        pytest.fail(f"Expected classified invalid ref, got {clone}")


def test_substantive_index_is_retained():
    from rcars.services.analyzer import filter_boilerplate_files
    content = {"index.adoc": "= Overview\n\nConfigure TLS certificates using OpenSSL."}
    assert filter_boilerplate_files(content) == content
    assert filter_boilerplate_files({"_nav.adoc": "* xref:index.adoc[Home]"}) == {}


@pytest.mark.parametrize("path", ["../outside", "/etc"])
def test_content_path_containment(git_repo, path):
    from rcars.services.analyzer import read_showroom_content
    with pytest.raises(ValueError, match="content_path"):
        read_showroom_content(git_repo[0], content_path=path)


def test_symlink_content_cannot_leave_clone(git_repo, tmp_path):
    from rcars.services.analyzer import read_showroom_content
    outside = tmp_path / "outside.adoc"
    outside.write_text("= Secret\nNot lab content")
    (git_repo[0] / "content/modules/ROOT/pages/escape.adoc").symlink_to(outside)
    with pytest.raises(ValueError, match="content_path"):
        read_showroom_content(git_repo[0])


def test_scan_and_stale_check_use_identical_content_path(git_repo):
    from rcars.services.analyzer import check_showroom_stale, hash_showroom_content, filter_boilerplate_files, read_showroom_content
    repo = git_repo[0]
    path = "other/pages"
    (repo / path).mkdir(parents=True)
    (repo / path / "overview.adoc").write_text("= Security\n\nEnable TLS 1.3 for clients.")
    expected = hash_showroom_content(filter_boilerplate_files(read_showroom_content(repo, path)))
    assert check_showroom_stale(repo, expected, content_path=path)["is_stale"] is False


def test_dict():
    assert parse_analysis_response('{"key": "val"}') == {"key": "val"}


def test_list():
    assert parse_analysis_response('[{"a": 1}]') == [{"a": 1}]


def test_fenced_json():
    assert parse_analysis_response('```json\n{"x": 1}\n```') == {"x": 1}


def test_scalar_string_returns_none():
    assert parse_analysis_response('"just a string"') is None


def test_scalar_int_returns_none():
    assert parse_analysis_response("42") is None


def test_scalar_bool_returns_none():
    assert parse_analysis_response("true") is None


def test_empty_returns_none():
    assert parse_analysis_response("") is None
    assert parse_analysis_response(None) is None


def test_unparseable_returns_none():
    assert parse_analysis_response("not json at all") is None
