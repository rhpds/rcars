"""Tests for the controlled vocabulary loader, normalizer, and prompt renderer."""

from __future__ import annotations

import textwrap

import pytest

from rcars.services.vocabulary import (
    DIMENSIONS,
    VOCABULARY_SENTINEL,
    VocabularyError,
    dedup_topics,
    load_vocabulary,
    normalize_analysis,
    render_vocabulary_block,
    snap_term,
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




class TestMatchLadder:
    def test_rung1_exact_alias_case_insensitive(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "RHACS") == ("Red Hat Advanced Cluster Security for Kubernetes", True)
        assert snap_term(vocab, "products", "rhacs") == ("Red Hat Advanced Cluster Security for Kubernetes", True)

    def test_rung1_vertical_alias(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "verticals", "FSI") == ("Financial Services", True)

    def test_rung2_squash_match(self):
        """Punctuation and spacing differences resolve without a human."""
        vocab = load_vocabulary()
        assert snap_term(vocab, "platforms", "on prem") == ("On-Premise", True)
        assert snap_term(vocab, "products", "Red-Hat Quay") == ("Red Hat Quay", True)

    def test_casing_and_spacing_variants_all_resolve(self):
        """The spec's worked examples, wherever on the ladder they land."""
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "Openshift Container Platform")[0] == (
            "Red Hat OpenShift Container Platform"
        )
        assert snap_term(vocab, "platforms", "On-Premises") == ("On-Premise", True)
        assert snap_term(vocab, "products", "Argo CD")[0] == "Red Hat OpenShift GitOps"

    def test_rung3_trailing_parenthetical(self):
        vocab = load_vocabulary()
        result, matched = snap_term(vocab, "products", "OpenShift Container Platform (OCP)")
        assert (result, matched) == ("Red Hat OpenShift Container Platform", True)

    def test_rung3_version_suffix(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "RHEL 9") == ("Red Hat Enterprise Linux", True)
        assert snap_term(vocab, "products", "OpenShift 4.16")[0] == (
            "Red Hat OpenShift Container Platform"
        )

    def test_rung3_missing_red_hat_prefix(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "Quay") == ("Red Hat Quay", True)

    def test_rung3_extra_red_hat_prefix(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "Red Hat Satellite") == ("Red Hat Satellite", True)
        assert snap_term(vocab, "platforms", "Red Hat AWS") == ("AWS", True)

    def test_rung4_no_match_returns_verbatim(self):
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "Wombat Server 3000") == ("Wombat Server 3000", False)

    def test_search_terms_do_not_snap(self):
        """search_terms widen query expansion only — the normalizer ignores them."""
        vocab = load_vocabulary()
        assert snap_term(vocab, "products", "container registry")[1] is False


class TestTopicDedup:
    def test_collapses_spelling_variants_keeping_longest(self):
        assert dedup_topics(["GitOps with ArgoCD", "GitOps with Argo CD"]) == [
            "GitOps with Argo CD"
        ]

    def test_tie_broken_by_first_appearance(self):
        assert dedup_topics(["ArgoCD", "argocd"]) == ["ArgoCD"]

    def test_preserves_order_of_survivors(self):
        assert dedup_topics(["Pipelines", "GitOps", "pipelines"]) == ["Pipelines", "GitOps"]

    def test_no_count_cap(self):
        topics = [f"topic number {i}" for i in range(25)]
        assert len(dedup_topics(topics)) == 25

    def test_drops_empty_values(self):
        assert dedup_topics(["GitOps", "", None]) == ["GitOps"]


class TestNormalizeAnalysis:
    def test_snaps_products_in_place(self):
        out = normalize_analysis({"products": ["RHACS", "OCP"]}, "lab")
        assert out["products"] == [
            "Red Hat Advanced Cluster Security for Kubernetes",
            "Red Hat OpenShift Container Platform",
        ]

    def test_unknown_product_stored_verbatim(self):
        out = normalize_analysis({"products": ["Wombat Server 3000"]}, "lab")
        assert out["products"] == ["Wombat Server 3000"]

    def test_snaps_difficulty_scalar(self):
        assert normalize_analysis({"difficulty": "Introductory"}, "lab")["difficulty"] == "beginner"

    def test_empty_vertical_normalizes_to_all(self):
        assert normalize_analysis({"verticals": []}, "architecture")["verticals"] == ["All"]
        assert normalize_analysis({"verticals": None}, "architecture")["verticals"] == ["All"]

    def test_missing_vertical_key_is_not_invented(self):
        """Keys absent from an analyzer's output are skipped — one map, two sources."""
        assert "verticals" not in normalize_analysis({"products": ["OCP"]}, "lab")

    def test_dedups_topics(self):
        out = normalize_analysis({"topics": ["GitOps with ArgoCD", "GitOps with Argo CD"]}, "lab")
        assert out["topics"] == ["GitOps with Argo CD"]

    def test_learning_objectives_untouched(self):
        objectives = {
            "stated": ["Understand how GitOps works"],
            "inferred": ["Deploy an application with Argo CD"],
        }
        out = normalize_analysis({"learning_objectives": objectives}, "lab")
        assert out["learning_objectives"] == objectives

    def test_no_verb_ever_produces_a_review_reason(self):
        out = normalize_analysis(
            {"learning_objectives": {"stated": ["Understand containers"]}, "products": ["OCP"]},
            "lab",
        )
        assert "review_reasons" not in out
        assert "enrichment_review_needed" not in out

    def test_does_not_mutate_input(self):
        original = {"products": ["RHACS"]}
        normalize_analysis(original, "lab")
        assert original == {"products": ["RHACS"]}

    def test_unrelated_keys_pass_through(self):
        out = normalize_analysis({"summary": "hello", "estimated_duration_min": 60}, "lab")
        assert out["summary"] == "hello"
        assert out["estimated_duration_min"] == 60


class TestIgnoredTermsSuppression:
    def test_ignored_term_creates_no_row(self):
        """A term in ignored_terms is stored verbatim but never recorded."""

        class RecordingDb:
            def __init__(self):
                self.calls = []

            def record_unknown_term(self, dimension, term, example_content_id=None):
                self.calls.append((dimension, term))

        db = RecordingDb()
        out = normalize_analysis(
            {"products": ["Kubernetes", "Wombat Server 3000"]},
            "lab",
            db=db,
            content_id="babylon:lb1",
        )
        assert out["products"] == ["Kubernetes", "Wombat Server 3000"]
        assert db.calls == [("products", "Wombat Server 3000")]

    def test_duplicate_unknowns_recorded_once_per_call(self):
        class RecordingDb:
            def __init__(self):
                self.calls = []

            def record_unknown_term(self, dimension, term, example_content_id=None):
                self.calls.append((dimension, term))

        db = RecordingDb()
        normalize_analysis({"products": ["Wombat", "Wombat"]}, "lab", db=db)
        assert db.calls == [("products", "Wombat")]




class TestRenderVocabularyBlock:
    def test_products_are_injected(self):
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "Red Hat OpenShift Container Platform" in block
        assert "Red Hat Advanced Cluster Security" in block

    def test_solutions_are_not_injected(self):
        """Only products and verb hints go into the prompt."""
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "Data Services & Storage" not in block
        assert "Financial Services" not in block
        assert "On-Premise" not in block

    def test_hands_on_verbs_for_lab(self):
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "deploy" in block
        assert "troubleshoot" in block
        assert "compare" not in block

    def test_read_through_verbs_for_architecture(self):
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "architecture")
        assert "compare" in block
        assert "evaluate" in block
        assert "troubleshoot" not in block

    def test_rejected_verbs_appear_as_avoid_hints(self):
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "understand" in block
        assert "be familiar with" in block

    def test_unmapped_content_type_falls_back_with_warning(self, caplog):
        import logging

        vocab = load_vocabulary()
        with caplog.at_level(logging.WARNING):
            block = render_vocabulary_block(vocab, "podcast")
        assert "deploy" in block  # hands_on fallback
        assert "podcast" in caplog.text

    def test_block_contains_no_format_braces(self):
        """The block is spliced into a template that cannot use str.format()."""
        vocab = load_vocabulary()
        block = render_vocabulary_block(vocab, "lab")
        assert "{" not in block and "}" not in block


class TestPromptInjection:
    def test_sentinel_present_in_template(self):
        from rcars.services.analyzer import PROMPT_TEMPLATE_PATH

        assert VOCABULARY_SENTINEL in PROMPT_TEMPLATE_PATH.read_text()

    def test_sentinel_sits_inside_the_instructions_section(self):
        """build_analysis_prompt slices the template; only the Instructions
        section reaches the system prompt. A sentinel outside it is discarded.
        """
        from rcars.services.analyzer import PROMPT_TEMPLATE_PATH

        template = PROMPT_TEMPLATE_PATH.read_text()
        instructions_start = template.index("\n## Instructions\n")
        content_start = template.index("\n## Showroom Content\n")
        assert instructions_start < template.index(VOCABULARY_SENTINEL) < content_start

    def test_vocabulary_block_reaches_the_system_prompt(self):
        from rcars.services.analyzer import build_analysis_prompt

        system_prompt, user_message = build_analysis_prompt(
            ci_name="lb1",
            display_name="Lab One",
            category="workshop",
            product="OpenShift",
            content_files={"m1.adoc": "some content"},
            entity_content_type="lab",
        )
        assert VOCABULARY_SENTINEL not in system_prompt
        assert "Red Hat OpenShift Container Platform" in system_prompt
        assert "troubleshoot" in system_prompt
        assert "some content" in user_message

    def test_architecture_type_selects_read_through_verbs(self):
        from rcars.services.analyzer import build_analysis_prompt

        system_prompt, _ = build_analysis_prompt(
            ci_name="lb1",
            display_name="Lab One",
            category="workshop",
            product="OpenShift",
            content_files={"m1.adoc": "some content"},
            entity_content_type="architecture",
        )
        assert "evaluate" in system_prompt

    def test_prompt_asks_for_recommender_audience(self):
        from rcars.services.analyzer import PROMPT_TEMPLATE_PATH

        assert "recommender_audience" in PROMPT_TEMPLATE_PATH.read_text()


class TestAnalyzerNormalizesOnce:
    def test_analysis_is_normalized_before_return(self, monkeypatch, tmp_path):
        """analyze_showroom normalizes right after parse — not at the write sites."""
        from rcars.services import analyzer

        clone_path = tmp_path / "clone"
        clone_path.mkdir()
        monkeypatch.setattr(analyzer, "clone_showroom", lambda *a, **k: clone_path)
        monkeypatch.setattr(analyzer, "get_repo_head", lambda *a, **k: ("abc123", "2026-01-01"))
        monkeypatch.setattr(
            analyzer, "read_showroom_content", lambda *a, **k: {"m1.adoc": "content"}
        )
        monkeypatch.setattr(analyzer, "filter_boilerplate_files", lambda files: files)
        monkeypatch.setattr(analyzer, "generate_embedding", lambda *a, **k: [0.0] * 768)

        class FakeResult:
            text = (
                '{"content_type": "workshop", "summary": "s", '
                '"products": ["RHACS", "OCP"], "difficulty": "Introductory", '
                '"topics": ["GitOps with ArgoCD", "GitOps with Argo CD"], '
                '"recommender_audience": ["solution architects"], "modules": []}'
            )
            input_tokens = 1
            output_tokens = 1
            provider = "test"

        monkeypatch.setattr("rcars.config.call_llm", lambda *a, **k: FakeResult())

        result = analyzer.analyze_showroom(
            ci_name="lb1",
            display_name="Lab One",
            category="workshop",
            product="OpenShift",
            showroom_url="https://example.com/x.git",
            showroom_ref=None,
            settings=object(),
            entity_content_type="lab",
        )

        analysis = result["analysis"]
        assert analysis["products"] == [
            "Red Hat Advanced Cluster Security for Kubernetes",
            "Red Hat OpenShift Container Platform",
        ]
        assert analysis["difficulty"] == "beginner"
        assert analysis["topics"] == ["GitOps with Argo CD"]
        assert analysis["recommender_audience"] == ["solution architects"]
        assert "review_reasons" not in analysis
