"""Actual analyzer exercised with local Git; only LLM/embedding transport is fake."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tests.test_analyzer import git_repo
from rcars.services import analyzer
from rcars.services.showroom_source import ResolvedShowroom


class MemoryArtifacts:
    def __init__(self):
        self.analysis = None
        self.embeddings = []
        self.item = None
        self.donor = None
        self.lookups = []

    def get_showroom_analysis(self, _):
        return self.analysis

    def get_babylon_item(self, _):
        return self.item

    def get_embeddings_for_content(self, _):
        return self.embeddings

    def log_token_usage(self, **kwargs):
        pass

    def record_unknown_term(self, *args, **kwargs):
        pass

    def find_showroom_donor(self, signature, *, exclude_content_id):
        self.lookups.append(signature)
        if self.donor and self.donor["analysis_provenance_json"]["signature"] == signature.to_dict():
            return self.donor
        return None

    def save(self, result):
        self.analysis = {**{key + "_json": value for key, value in result["analysis"].items()},
                         **{key: result["analysis"].get(key) for key in ("summary", "content_type", "difficulty", "estimated_duration_min")},
                         "analysis_provenance_json": result["analysis_provenance"],
                         "content_hash": result["content_hash"], "is_stale": False,
                         "last_analyzed": "2026-10-01T00:00:00+00:00"}
        self.embeddings = [{"embed_type": "summary", "module_title": None,
                            "content_text": result["ci_embedding_text"], "embedding_text": str(result["ci_embedding"])}]
        self.embeddings += [{**row, "embed_type": "module", "embedding_text": str(row["embedding"])}
                            for row in result["module_embeddings"]]


@pytest.fixture
def scan(git_repo, tmp_path, monkeypatch):
    settings = SimpleNamespace(model="example-model", clone_dir=str(tmp_path), embedding_model="example-embed", embedding_dim=768)
    source = ResolvedShowroom("resolved", "example.item.prod", "example.item", str(git_repo[0]), "main",
                              paths=(("example.item.prod",),))
    llm = Mock(return_value=SimpleNamespace(text='{"summary":"Configure TLS","modules":[{"title":"TLS","topics":["security"]}]}',
                                           input_tokens=10, output_tokens=20, provider="fake"))
    embed = Mock(return_value=[0.1] * 768)
    monkeypatch.setattr("rcars.config.call_llm", llm)
    monkeypatch.setattr(analyzer, "generate_embedding", embed)
    db = MemoryArtifacts()
    kwargs = dict(ci_name="example.item.prod", display_name="TLS workshop", category="Workshop", product="",
                  showroom_url=source.repo, showroom_ref=source.ref, settings=settings, model=settings.model,
                  clone_dir=str(tmp_path), db=db, source=source, keywords=["original"])

    def run(**updates):
        return analyzer.analyze_showroom(**{**kwargs, **updates})

    return SimpleNamespace(run=run, db=db, llm=llm, embed=embed, source=source, settings=settings, kwargs=kwargs)


def prime(scan):
    result = scan.run()
    assert "error" not in result
    scan.db.save(result)
    scan.llm.reset_mock()
    scan.embed.reset_mock()
    return result


def test_valid_short_overview_is_analyzable(scan):
    result = scan.run()
    assert result["analysis"]["summary"] == "Configure TLS"
    assert result["analysis_provenance"]["generated_for"] == "babylon:example.item.prod"
    assert result["analysis_provenance"]["signature"]["scope_key"] == "example.item"
    assert result["outcome"] == "analyzed"


@pytest.mark.parametrize("content", ["= Home\n\n* xref:other.adoc[Next]", "= Welcome to the Publishing House\n\nThis is a placeholder for your content."])
def test_nav_and_publishing_house_stub_return_no_content_before_lookup_or_llm(scan, git_repo, content):
    repo, git, _, _ = git_repo
    (repo / "content/modules/ROOT/pages/index.adoc").write_text(content)
    git("add", ".")
    git("commit", "-m", "Stub")
    result = scan.run()
    assert result["error"] == "no_content"
    assert scan.db.lookups == []
    assert scan.llm.call_count == scan.embed.call_count == 0


def test_identical_revision_and_context_skips_clone_llm_and_embeddings(scan, monkeypatch):
    first = prime(scan)
    clone = Mock(side_effect=AssertionError("must not clone unchanged input"))
    monkeypatch.setattr(analyzer, "clone_showroom", clone)
    result = scan.run()
    assert result["outcome"] == "unchanged"
    assert result["analysis_provenance"] == first["analysis_provenance"]
    assert clone.call_count == scan.llm.call_count == scan.embed.call_count == 0


def test_new_commit_same_selected_content_only_advances_verified_revision(scan, git_repo, monkeypatch):
    original = prime(scan)
    repo, git, _, _ = git_repo
    (repo / "README.md").write_text("Another irrelevant commit")
    git("add", ".")
    git("commit", "-m", "Documentation only")
    result = scan.run()
    assert result["outcome"] == "revision_verified"
    assert result["analysis_provenance"]["signature"]["commit"] == git("rev-parse", "HEAD")
    assert result["analysis_provenance"]["generated_commit"] == original["analysis_provenance"]["generated_commit"]
    assert result["last_analyzed"] == "2026-10-01T00:00:00+00:00"
    assert scan.llm.call_count == scan.embed.call_count == 0
    scan.db.save(result)
    monkeypatch.setattr(analyzer, "clone_showroom", Mock(side_effect=AssertionError("verified revision refetched")))
    assert scan.run()["outcome"] == "unchanged"


def test_whitespace_only_commit_preserves_llm_generation(scan, git_repo):
    original = prime(scan)
    repo, git, _, _ = git_repo
    page = repo / "content/modules/ROOT/pages/index.adoc"
    page.write_text("\r\n\r\n" + "\r\n".join(line + "   " for line in page.read_text().splitlines()) + "\r\n\r\n")
    git("add", ".")
    git("commit", "-m", "Whitespace only")
    result = scan.run()
    assert result["outcome"] == "revision_verified"
    assert result["analysis_provenance"]["generated_commit"] == original["analysis_provenance"]["generated_commit"]
    assert result["last_analyzed"] == "2026-10-01T00:00:00+00:00"
    assert scan.llm.call_count == scan.embed.call_count == 0


@pytest.mark.parametrize("change,count", [("keywords", 1), ("model", 2), ("missing_module", 1)])
def test_embedding_only_changes_repair_only_affected_artifacts(scan, change, count, monkeypatch):
    prime(scan)
    updates = {}
    if change == "keywords":
        updates["keywords"] = ["new-keyword"]
    elif change == "model":
        scan.settings.embedding_model = "new-embedding-model"
    else:
        scan.db.embeddings = [row for row in scan.db.embeddings if row["embed_type"] != "module"]
    monkeypatch.setattr(analyzer, "clone_showroom", Mock(side_effect=AssertionError("embedding repair cloned")))
    result = scan.run(**updates)
    assert result["outcome"] == "embeddings_repaired"
    assert scan.llm.call_count == 0
    assert scan.embed.call_count == count
    if change == "keywords":
        assert "new-keyword" in result["ci_embedding_text"]


def test_changed_prompt_context_invalidates_unchanged_git_revision(scan, monkeypatch):
    prime(scan)
    original = analyzer.build_analysis_prompt
    monkeypatch.setattr(analyzer, "build_analysis_prompt", lambda *a, **k: ("Changed prompt", original(*a, **k)[1]))
    assert scan.run()["outcome"] == "analyzed"
    assert scan.llm.call_count == 1


def test_new_analysis_keeps_embeddings_with_identical_text(scan):
    prime(scan)
    result = scan.run(model="new-analysis-model")
    assert result["outcome"] == "analyzed"
    assert scan.llm.call_count == 1
    assert scan.embed.call_count == 0


def test_stale_revision_with_same_content_does_not_force_llm(scan, git_repo):
    original = prime(scan)
    scan.db.analysis["is_stale"] = True
    repo, git, _, _ = git_repo
    (repo / "README.md").write_text("Freshness check found an irrelevant commit")
    git("add", ".")
    git("commit", "-m", "Another unrelated change")
    result = scan.run()
    assert result["outcome"] == "revision_verified"
    assert result["analysis_provenance"]["generated_commit"] == original["analysis_provenance"]["generated_commit"]
    assert scan.llm.call_count == scan.embed.call_count == 0


def test_force_bypasses_unchanged_fast_path_and_donors(scan):
    prime(scan)
    scan.db.donor = scan.db.analysis
    result = scan.run(force=True)
    assert result["outcome"] == "analyzed"
    assert scan.llm.call_count == 1
    assert scan.embed.call_count == 2


def test_same_scoped_signature_reuses_analysis_but_targets_own_summary(scan):
    prime(scan)
    donor = deepcopy(scan.db.analysis)
    donor.update(content_id="babylon:example.item.prod", ci_name="example.item.prod")
    scan.db.donor = donor
    scan.db.analysis = None
    result = scan.run(ci_name="example.item.dev", keywords=["target-only"])
    assert result["outcome"] == "reused"
    assert scan.llm.call_count == 0
    assert scan.embed.call_count == 1
    assert "target-only" in result["ci_embedding_text"]
    assert "TLS workshop" in result["ci_embedding_text"]
    assert result["analysis_provenance"]["reused_from"] == "babylon:example.item.prod"


@pytest.mark.parametrize("field,value", [("scope_key", "example.other"), ("ref", "light"),
    ("content_path", "content/modules/ROOT/pages"), ("commit", "f" * 40),
    ("repo", "https://github.com/example/other"), ("content_hash", "different"),
    ("context_hash", "different"), ("input_hash", "different")])
def test_every_changed_signature_input_prevents_donor_reuse(scan, field, value):
    prime(scan)
    donor = deepcopy(scan.db.analysis)
    donor["analysis_provenance_json"]["signature"][field] = value
    scan.db.donor = donor
    scan.db.analysis = None
    assert scan.run()["outcome"] == "analyzed"
    assert scan.llm.call_count == 1


@pytest.mark.parametrize("field,value", [("showroom_url_override", "url"), ("content_path", "content/modules/ROOT/pages")])
def test_curator_url_or_path_override_is_target_scoped(scan, git_repo, field, value):
    if value == "url":
        value = str(git_repo[0])
    scan.db.item = {"ci_name": "example.item.prod", "stage": "prod", "showroom_source_json": replace(scan.source, scope_key="example.base").to_dict(), field: value}
    result = scan.run()
    signature = result["analysis_provenance"]["signature"]
    assert signature["scope_key"] == "example.item"
    assert result["analysis_provenance"]["source"]["override_origins"]
