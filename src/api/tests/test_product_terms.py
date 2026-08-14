"""Advisor query expansion, now backed by the controlled vocabulary.

Formerly tested data/product-terms.yaml, which was merged into
data/vocabulary.yaml and deleted (RHDPCD-507).
"""

from __future__ import annotations

import pytest

from rcars.services.recommender.pipeline import _expand_query_terms
from rcars.services.vocabulary import load_vocabulary

# Every acronym and synonym key from the deleted product-terms.yaml.
# Coverage requirement from the spec: every term must survive the merge.
LEGACY_PRODUCT_TERMS = [
    "AAP", "ACM", "RHACM", "ACS", "RHACS", "RHOAI", "OCP", "ARO", "ROSA",
    "RHEL", "RHDH", "SNO", "RHSSO", "EDA", "TAP", "AMQ", "CRW", "RHBK",
    "Red Hat AI", "OpenShift AI", "DevSpaces", "Dev Spaces", "Developer Hub",
    "Quay", "3scale", "Service Mesh", "Serverless", "GitOps", "Virtualization",
    "MaaS",
]


@pytest.fixture(autouse=True)
def clear_vocabulary_cache():
    load_vocabulary.cache_clear()
    yield
    load_vocabulary.cache_clear()


class TestExpansionReadsVocabulary:
    def test_acronym_expands_to_canonical_name(self):
        result = _expand_query_terms("show me RHACS labs")
        assert "Red Hat Advanced Cluster Security" in result
        assert result.startswith("show me RHACS")

    def test_case_insensitive(self):
        assert "Red Hat OpenShift AI" in _expand_query_terms("rhoai content")

    def test_canonical_name_in_query_still_recognised(self):
        result = _expand_query_terms("Red Hat Quay setup")
        assert "Red Hat Quay" in result

    def test_no_match_returns_unchanged(self):
        assert _expand_query_terms("wombat husbandry") == "wombat husbandry"

    def test_partial_word_is_not_expanded(self):
        """Word-boundary matching — RHOAI inside RHOAIX must not expand."""
        assert "Red Hat OpenShift AI" not in _expand_query_terms("RHOAIX platform")

    def test_no_double_expansion(self):
        result = _expand_query_terms("RHACS")
        assert result.count("Red Hat Advanced Cluster Security") == 1


class TestMigrationCoverage:
    @pytest.mark.parametrize("term", LEGACY_PRODUCT_TERMS)
    def test_every_legacy_term_still_expands(self, term):
        result = _expand_query_terms(f"find {term} content")
        assert result != f"find {term} content", f"'{term}' no longer expands"


class TestSearchTerms:
    def test_search_terms_widen_expansion(self):
        """GitOps must still pull in ArgoCD and Argo CD as recall terms."""
        result = _expand_query_terms("GitOps demos")
        assert "Red Hat OpenShift GitOps" in result
        assert "Argo CD" in result

    def test_search_terms_ignored_by_normalization(self):
        """search_terms widen recall only — they never snap a value."""
        from rcars.services.vocabulary import normalize_analysis

        out = normalize_analysis({"products": ["container registry"]}, "lab")
        assert out["products"] == ["container registry"]


class TestOldFileGone:
    def test_product_terms_yaml_is_deleted(self):
        from importlib.resources import files as pkg_files

        assert not pkg_files("rcars.data").joinpath("product-terms.yaml").is_file()

    def test_loader_function_removed(self):
        import rcars.services.recommender.pipeline as pipeline

        assert not hasattr(pipeline, "_load_product_terms")


from rcars.services.analyzer import build_embedding_text


class TestBuildEmbeddingText:
    def test_without_display_name(self):
        analysis = {"summary": "A test lab about OpenShift."}
        result = build_embedding_text(analysis)
        assert result == "A test lab about OpenShift."

    def test_with_display_name_positioned_after_content(self):
        analysis = {
            "summary": "A workshop about AI.",
            "topics": ["machine learning"],
            "products": ["OpenShift AI"],
            "audience": ["developers"],
            "use_cases": ["model training"],
        }
        result = build_embedding_text(analysis, display_name="My Great Workshop")
        summary_pos = result.index("A workshop about AI.")
        name_pos = result.index("My Great Workshop")
        assert name_pos > summary_pos

    def test_with_display_name_before_keywords(self):
        analysis = {
            "summary": "A workshop about AI.",
        }
        result = build_embedding_text(
            analysis, keywords=["ai", "ml"], display_name="My Workshop"
        )
        name_pos = result.index("My Workshop")
        keyword_pos = result.index("ai")
        assert name_pos < keyword_pos

    def test_display_name_none_is_skipped(self):
        analysis = {"summary": "Just a summary."}
        result = build_embedding_text(analysis, display_name=None)
        assert result == "Just a summary."

    def test_display_name_empty_string_is_skipped(self):
        analysis = {"summary": "Just a summary."}
        result = build_embedding_text(analysis, display_name="")
        assert result == "Just a summary."

    def test_backward_compatible_without_keyword_arg(self):
        analysis = {"summary": "Summary.", "topics": ["k8s"]}
        result = build_embedding_text(analysis, keywords=["tag1"])
        assert "Summary." in result
        assert "k8s" in result
        assert "tag1" in result
