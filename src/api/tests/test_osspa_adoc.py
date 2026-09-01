import subprocess
from pathlib import Path

import pytest

from rcars.services.osspa_sync import (
    compute_content_hash,
    is_tracked_at_head,
    read_detail_adoc,
    resolve_repo_path,
    strip_passthrough,
)

MAX_BYTES = 200000


def _git(repo: Path, *args: str) -> None:
    env = {"GIT_TEMPLATE_DIR": "", "HOME": str(repo), "PATH": __import__("os").environ["PATH"]}
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "examples"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "T")
    (root / "rhacs.adoc").write_text("= RHACS\n\nSome architecture prose.\n")
    (root / "mockup").mkdir()
    (root / "mockup" / "nested.adoc").write_text("= Nested\n\nNested prose.\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def test_resolves_root_and_nested_paths(repo):
    assert resolve_repo_path(repo, "rhacs.adoc") == (repo / "rhacs.adoc").resolve()
    assert resolve_repo_path(repo, "mockup/nested.adoc") == (repo / "mockup" / "nested.adoc").resolve()


@pytest.mark.parametrize("bad", ["../outside.adoc", "/etc/passwd", "a/../../x.adoc", ""])
def test_rejects_traversal_and_absolute_paths(repo, bad):
    assert resolve_repo_path(repo, bad) is None


def test_rejects_symlink_escaping_the_clone_root(repo, tmp_path):
    secret = tmp_path / "secret.adoc"
    secret.write_text("secret")
    (repo / "escape.adoc").symlink_to(secret)
    assert resolve_repo_path(repo, "escape.adoc") is None


def test_untracked_file_is_not_read(repo):
    (repo / "untracked.adoc").write_text("= Untracked\n")
    assert is_tracked_at_head(repo, repo / "untracked.adoc") is False
    assert read_detail_adoc(repo, "untracked.adoc", MAX_BYTES) is None


def test_reads_a_tracked_adoc(repo):
    result = read_detail_adoc(repo, "rhacs.adoc", MAX_BYTES)
    assert "Some architecture prose." in result.full_text
    assert result.truncated is False


def test_missing_file_returns_none(repo):
    assert read_detail_adoc(repo, "nope.adoc", MAX_BYTES) is None


def test_strip_passthrough_removes_html_blocks_and_arcade_comments():
    text = "Intro\n\n++++\n<iframe src='x'></iframe>\n++++\n\nOutro\n<!--ARCADE EMBED start-->\n"
    stripped = strip_passthrough(text)
    assert "iframe" not in stripped
    assert "ARCADE" not in stripped
    assert "Intro" in stripped and "Outro" in stripped


def test_include_directive_is_expanded(repo):
    (repo / "partial.adoc").write_text("Shared partial body.\n")
    (repo / "main.adoc").write_text("= Main\n\ninclude::partial.adoc[]\n\nTail.\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add include")

    result = read_detail_adoc(repo, "main.adoc", MAX_BYTES)
    assert "Shared partial body." in result.full_text
    assert "include::" not in result.full_text
    assert "Tail." in result.full_text


def test_include_of_untracked_or_escaping_target_is_skipped(repo):
    (repo / "main.adoc").write_text(
        "= Main\n\ninclude::../outside.adoc[]\ninclude::http://evil/x.adoc[]\n"
        "include::{attr}/x.adoc[]\ninclude::ghost.adoc[]\n\nBody.\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "bad includes")

    result = read_detail_adoc(repo, "main.adoc", MAX_BYTES)
    assert "Body." in result.full_text
    assert "outside" not in result.full_text
    assert "evil" not in result.full_text


def test_include_cycle_terminates(repo):
    (repo / "a.adoc").write_text("A\ninclude::b.adoc[]\n")
    (repo / "b.adoc").write_text("B\ninclude::a.adoc[]\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "cycle")

    result = read_detail_adoc(repo, "a.adoc", MAX_BYTES)
    assert "A" in result.full_text and "B" in result.full_text


def test_oversized_adoc_truncates_the_prompt_copy_only(repo):
    body = "x" * 5000
    (repo / "big.adoc").write_text(body)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "big")

    result = read_detail_adoc(repo, "big.adoc", 1024)
    assert result.truncated is True
    assert len(result.prompt_text.encode("utf-8")) <= 1024
    assert len(result.full_text) >= 5000


def test_content_hash_covers_full_body_past_the_prompt_cap():
    payload = {"summary": "s", "products": ["p"], "solutions": ["a"],
               "verticals": ["v"], "meta_keyword": "k"}
    long_a = "x" * 5000 + "END-A"
    long_b = "x" * 5000 + "END-B"
    assert compute_content_hash(long_a, payload) != compute_content_hash(long_b, payload)


@pytest.mark.parametrize("field,value", [
    ("summary", "changed"), ("products", ["other"]), ("solutions", ["other"]),
    ("verticals", ["other"]), ("meta_keyword", "other"),
])
def test_content_hash_covers_prompt_input_csv_fields(field, value):
    base = {"summary": "s", "products": ["p"], "solutions": ["a"],
            "verticals": ["v"], "meta_keyword": "k"}
    changed = {**base, field: value}
    assert compute_content_hash("body", base) != compute_content_hash("body", changed)


def test_content_hash_ignores_non_prompt_csv_fields():
    base = {"summary": "s", "products": ["p"], "solutions": ["a"],
            "verticals": ["v"], "meta_keyword": "k", "image_url": "a.png"}
    changed = {**base, "image_url": "b.png", "display_name": "Renamed"}
    assert compute_content_hash("body", base) == compute_content_hash("body", changed)
