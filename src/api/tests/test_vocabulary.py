"""Tests for the controlled vocabulary loader, normalizer, and prompt renderer."""

from __future__ import annotations

import textwrap

import pytest

from rcars.services.vocabulary import (
    DIMENSIONS,
    VocabularyError,
    load_vocabulary,
    squash_key,
)


@pytest.fixture(autouse=True)
def clear_vocabulary_cache():
    """load_vocabulary is process-cached; clear it around every test."""
    load_vocabulary.cache_clear()
    yield
    load_vocabulary.cache_clear()


def write_vocab(tmp_path, body: str):
    path = tmp_path / "vocabulary.yaml"
    path.write_text(textwrap.dedent(body))
    return path


class TestSquashKey:
    def test_strips_case_and_punctuation(self):
        assert squash_key("GitOps with Argo CD") == "gitopswithargocd"
        assert squash_key("GitOps with ArgoCD") == "gitopswithargocd"
        assert squash_key("on-prem") == "onprem"
        assert squash_key("On Prem") == "onprem"


class TestLoadPackagedDefault:
    def test_reads_packaged_default(self):
        vocab = load_vocabulary()
        assert len(vocab.canonical_names("products")) > 0
        assert "Red Hat OpenShift Container Platform" in vocab.canonical_names("products")

    def test_all_dimensions_present(self):
        vocab = load_vocabulary()
        for dimension in DIMENSIONS:
            assert vocab.entries(dimension), f"{dimension} is empty"

    def test_content_modes_loaded(self):
        vocab = load_vocabulary()
        assert vocab.content_modes["lab"] == "hands_on"
        assert vocab.content_modes["architecture"] == "read_through"

    def test_ignored_terms_loaded(self):
        vocab = load_vocabulary()
        assert vocab.is_ignored("products", "Kubernetes")
        assert vocab.is_ignored("products", "kubernetes")  # case-insensitive
        assert not vocab.is_ignored("products", "Red Hat Quay")

    def test_ignored_originals_keep_source_spelling(self):
        vocab = load_vocabulary()
        assert "Kubernetes" in vocab.ignored_originals["products"]
        assert vocab.ignored_originals["solutions"] == ()

    def test_search_terms_kept_separate_from_aliases(self):
        vocab = load_vocabulary()
        gitops = next(e for e in vocab.entries("products") if e.name == "Red Hat OpenShift GitOps")
        assert "ArgoCD" in gitops.aliases
        assert "Argo CD" in gitops.search_terms

    def test_is_tdp_flag(self):
        vocab = load_vocabulary()
        solutions = {e.name: e.is_tdp for e in vocab.entries("solutions")}
        assert solutions["Application Platform"] is True
        assert solutions["Integration"] is False


class TestPathOverride:
    def test_override_path_wins(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, """
            products:
              - name: Only Product
                aliases: [OP]
            solutions: []
            verticals: []
            platforms: []
            difficulty:
              - name: beginner
              - name: intermediate
              - name: advanced
            action_verbs:
              hands_on:
                valid: [deploy]
                rejected: [understand]
            content_modes:
              lab: hands_on
        """)
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        vocab = load_vocabulary()
        assert vocab.canonical_names("products") == ["Only Product"]


class TestValidation:
    """Every document is built from one helper so indentation stays uniform —
    write_vocab dedents the whole string, so both halves must share a prefix.
    """

    def _doc(self, dimensions: str, content_modes: str = "              lab: hands_on") -> str:
        return f"""
            difficulty:
              - name: beginner
              - name: intermediate
              - name: advanced
            action_verbs:
              hands_on:
                valid: [deploy]
                rejected: [understand]
              read_through:
                valid: [compare]
                rejected: [understand]
            content_modes:
{content_modes}
{dimensions}
        """

    def test_rejects_duplicate_alias_within_dimension(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, self._doc("""
            products:
              - name: Product A
                aliases: [SHARED]
              - name: Product B
                aliases: [SHARED]
        """))
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        with pytest.raises(VocabularyError, match="SHARED"):
            load_vocabulary()

    def test_rejects_alias_colliding_with_other_canonical(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, self._doc("""
            products:
              - name: Product A
                aliases: []
              - name: Product B
                aliases: [Product A]
        """))
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        with pytest.raises(VocabularyError, match="Product A"):
            load_vocabulary()

    def test_accepts_same_alias_across_dimensions(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, self._doc("""
            products: []
            solutions:
              - name: Edge
                aliases: [EdgeComputing]
            platforms:
              - name: Edge
                aliases: [EdgeComputing]
        """))
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        vocab = load_vocabulary()
        assert "Edge" in vocab.canonical_names("solutions")
        assert "Edge" in vocab.canonical_names("platforms")

    def test_rejects_wrong_difficulty_set(self, tmp_path, monkeypatch):
        path = write_vocab(tmp_path, """
            products: []
            difficulty:
              - name: easy
              - name: hard
            action_verbs:
              hands_on:
                valid: [deploy]
                rejected: [understand]
            content_modes:
              lab: hands_on
        """)
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        with pytest.raises(VocabularyError, match="difficulty"):
            load_vocabulary()

    def test_rejects_content_mode_with_no_verb_list(self, tmp_path, monkeypatch):
        path = write_vocab(
            tmp_path,
            self._doc("            products: []", content_modes="              lab: nonexistent_mode"),
        )
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        with pytest.raises(VocabularyError, match="nonexistent_mode"):
            load_vocabulary()

    def test_unknown_top_level_key_warns_only(self, tmp_path, monkeypatch, caplog):
        path = write_vocab(tmp_path, self._doc("""
            products: []
            mystery_section:
              - anything
        """))
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        vocab = load_vocabulary()
        assert vocab is not None
        assert "mystery_section" in caplog.text
