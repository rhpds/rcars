import pytest
from rcars.services.recommender.pipeline import _load_product_terms, _expand_query_terms


class TestLoadProductTerms:
    def test_loads_both_sections(self):
        acronyms, synonyms = _load_product_terms()
        assert isinstance(acronyms, dict)
        assert isinstance(synonyms, dict)
        assert len(acronyms) > 0
        assert len(synonyms) > 0

    def test_acronyms_include_known_entries(self):
        acronyms, _ = _load_product_terms()
        assert acronyms["RHOAI"] == "Red Hat OpenShift AI"
        assert acronyms["AAP"] == "Ansible Automation Platform"
        assert acronyms["RHBK"] == "Red Hat Build of Keycloak"

    def test_synonyms_include_known_entries(self):
        _, synonyms = _load_product_terms()
        assert synonyms["Red Hat AI"] == "Red Hat OpenShift AI"
        assert synonyms["MaaS"] == "Models as a Service model serving"


class TestExpandQueryTerms:
    def test_acronym_expansion(self):
        result = _expand_query_terms("show me RHOAI labs")
        assert "Red Hat OpenShift AI" in result
        assert result.startswith("show me RHOAI")

    def test_synonym_expansion(self):
        result = _expand_query_terms("Red Hat AI 101 content")
        assert "Red Hat OpenShift AI" in result
        assert "Red Hat AI" in result

    def test_no_match_returns_unchanged(self):
        query = "something completely unrelated"
        assert _expand_query_terms(query) == query

    def test_case_insensitive_acronym(self):
        result = _expand_query_terms("tell me about rhoai")
        assert "Red Hat OpenShift AI" in result

    def test_case_insensitive_synonym(self):
        result = _expand_query_terms("red hat ai for beginners")
        assert "Red Hat OpenShift AI" in result

    def test_acronym_word_boundary(self):
        result = _expand_query_terms("the RHOACIM project")
        assert "Red Hat OpenShift AI" not in result

    def test_synonym_does_not_match_partial_words(self):
        result = _expand_query_terms("QuayIO registry setup")
        # "Quay" synonym should not match inside "QuayIO"
        # but this depends on implementation — phrase match should
        # use word boundaries or exact phrase matching
        assert result == "QuayIO registry setup"

    def test_multiple_expansions(self):
        result = _expand_query_terms("RHOAI and Red Hat AI labs")
        assert result.count("Red Hat OpenShift AI") >= 2

    def test_synonym_longest_match_first(self):
        result = _expand_query_terms("Dev Spaces environment")
        assert "Red Hat OpenShift Dev Spaces" in result

    def test_expansion_format_parenthetical(self):
        result = _expand_query_terms("deploy on OCP")
        assert "OCP (OpenShift Container Platform)" in result


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
        # display_name should appear after content fields but before any keywords
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
