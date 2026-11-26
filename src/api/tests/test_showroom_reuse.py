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
        self.commit_lookups = []
        self.content_lookups = []

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

    # A deliberately careless database: it hands back whatever donor it holds, so these
    # tests prove the analyzer itself refuses a donor that does not match the key.
    def find_showroom_donor_by_commit(self, **kwargs):
        self.commit_lookups.append(kwargs)
        return self.donor

    def find_showroom_donor_by_content(self, **kwargs):
        self.content_lookups.append(kwargs)
        return self.donor

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
    kwargs = dict(ci_name="example.item.prod", display_name="TLS workshop",
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
    scan.db.commit_lookups.clear()
    scan.db.content_lookups.clear()
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
    assert scan.db.content_lookups == []  # boilerplate-only content never becomes a shared key
    assert scan.llm.call_count == scan.embed.call_count == 0


def test_boilerplate_only_content_never_reuses_even_a_donor_with_the_empty_hash(scan, git_repo):
    repo, git, _, _ = git_repo
    (repo / "content/modules/ROOT/pages/index.adoc").write_text("= Home\n\n* xref:other.adoc[Next]")
    git("add", ".")
    git("commit", "-m", "Stub")
    prime_donor = analyzer.hash_showroom_content({})
    scan.db.donor = {"content_id": "babylon:example.other.prod", "entity_content_type": "lab",
                     "content_hash": prime_donor, "analysis_provenance_json": {"signature": {
                         "repo": scan.source.repo, "commit": git("rev-parse", "HEAD"), "content_path": None,
                         "content_hash": prime_donor, "context_hash": "any", "policy_version": 1}}}
    assert scan.run()["error"] == "no_content"
    assert scan.db.content_lookups == []
    assert scan.llm.call_count == 0


def test_identical_revision_and_context_skips_clone_llm_and_embeddings(scan, monkeypatch):
    first = prime(scan)
    clone = Mock(side_effect=AssertionError("must not clone unchanged input"))
    monkeypatch.setattr(analyzer, "clone_showroom", clone)
    result = scan.run()
    assert result["outcome"] == "unchanged"
    assert result["analysis_provenance"] == first["analysis_provenance"]
    assert clone.call_count == scan.llm.call_count == scan.embed.call_count == 0
    assert scan.db.commit_lookups == scan.db.content_lookups == []


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


def donor_row(scan, content_id="babylon:example.item.prod", **changes):
    """The saved analysis, as the database would return it for another item."""
    donor = deepcopy(scan.db.analysis)
    donor.update(content_id=content_id, ci_name=content_id.removeprefix("babylon:"), entity_content_type="lab")
    signature = donor["analysis_provenance_json"]["signature"]
    for key, value in changes.items():
        if key == "entity_content_type":
            donor[key] = value
        else:
            signature[key] = value
            if key == "content_hash":
                donor["content_hash"] = value
    return donor


def as_donor(scan, **changes):
    scan.db.donor = donor_row(scan, **changes)
    scan.db.analysis = None


def test_same_content_reuses_analysis_but_targets_own_summary(scan):
    prime(scan)
    as_donor(scan)
    result = scan.run(ci_name="example.item.dev", keywords=["target-only"])
    assert result["outcome"] == "reused"
    assert scan.llm.call_count == 0
    assert scan.embed.call_count == 1
    assert "target-only" in result["ci_embedding_text"]
    assert "TLS workshop" in result["ci_embedding_text"]
    assert result["analysis_provenance"]["reused_from"] == "babylon:example.item.prod"


def test_other_stage_with_another_ref_name_on_the_same_commit_reuses_without_cloning(scan, git_repo, monkeypatch):
    repo, git, _, second = git_repo
    git("tag", "v1")  # a tag on the same commit as main
    prime(scan)
    as_donor(scan)
    monkeypatch.setattr(analyzer, "clone_showroom", Mock(side_effect=AssertionError("pre-clone shortcut must not clone")))
    result = scan.run(ci_name="example.item.dev", source=replace(scan.source, ref="v1"))
    assert result["outcome"] == "reused"
    assert scan.llm.call_count == 0
    signature = result["analysis_provenance"]["signature"]
    assert (signature["ref"], signature["commit"]) == ("v1", second)  # own source facts stay on the item
    assert result["analysis_provenance"]["reused_from"] == "babylon:example.item.prod"
    assert scan.db.content_lookups == []  # the shortcut answered; no post-clone lookup needed


def test_new_commit_with_the_same_files_reuses_after_the_clone(scan, git_repo, monkeypatch):
    repo, git, _, _ = git_repo
    prime(scan)
    as_donor(scan)
    (repo / "README.md").write_text("Another irrelevant commit")
    git("add", ".")
    git("commit", "-m", "Documentation only")
    clone = Mock(wraps=analyzer.clone_showroom)
    monkeypatch.setattr(analyzer, "clone_showroom", clone)
    result = scan.run(ci_name="example.item.dev")
    assert result["outcome"] == "reused"
    assert clone.call_count == 1 and scan.llm.call_count == 0
    assert result["analysis_provenance"]["signature"]["commit"] == git("rev-parse", "HEAD")
    assert len(scan.db.commit_lookups) == len(scan.db.content_lookups) == 1


def test_different_content_path_in_one_repo_is_not_reused(scan, git_repo, monkeypatch):
    repo, git, _, _ = git_repo
    other = repo / "other/modules/ROOT/pages"
    other.mkdir(parents=True)
    (other / "index.adoc").write_text("= Another lab\n\nDeploy a service mesh with Istio.\n")
    git("add", ".")
    git("commit", "-m", "Second lab in the same repo")
    prime(scan)
    as_donor(scan)
    clone = Mock(wraps=analyzer.clone_showroom)
    monkeypatch.setattr(analyzer, "clone_showroom", clone)
    result = scan.run(ci_name="example.item.dev", source=replace(scan.source, content_path="other"))
    assert result["outcome"] == "analyzed"
    assert clone.call_count == 1 and scan.llm.call_count == 1


def test_different_ci_with_the_same_files_reuses_because_context_is_out_of_the_config(scan):
    first = scan.run(ci_name="example.other.prod", display_name="Another workshop",
                     source=replace(scan.source, scope_key="example.other"))
    scan.db.save(first)
    scan.llm.reset_mock()
    as_donor(scan, content_id="babylon:example.other.prod")
    result = scan.run()  # example.item.prod, "TLS workshop": same files, other CI
    assert result["outcome"] == "reused" and scan.llm.call_count == 0
    assert result["analysis_provenance"]["reused_from"] == "babylon:example.other.prod"
    assert "TLS workshop" in result["ci_embedding_text"]  # the summary embedding stays per item


@pytest.mark.parametrize("changes,blocks_reuse", [
    # The invariant: only content_hash + analysis_config (and policy, entity type) decide.
    # (A donor on this commit and path cannot hold other files, so a different hash comes
    # from another commit; the pre-clone shortcut never sees a hash.)
    ({"content_hash": "different", "commit": "f" * 40}, True), ({"context_hash": "different"}, True),
    ({"policy_version": 99}, True), ({"entity_content_type": "architecture"}, True),
    # Ref names, CI names, commits, repos, paths and prompt hashes never block reuse by themselves.
    ({"ref": "light"}, False), ({"scope_key": "example.other"}, False), ({"input_hash": "different"}, False),
    ({"commit": "f" * 40}, False), ({"content_path": "content/modules/ROOT/pages"}, False),
    ({"repo": "https://github.com/example/other"}, False)])
def test_scan_never_reuses_unless_content_hash_and_analysis_config_match(scan, changes, blocks_reuse):
    prime(scan)
    as_donor(scan, **changes)
    result = scan.run(ci_name="example.item.dev")
    if blocks_reuse:
        assert result["outcome"] == "analyzed" and scan.llm.call_count == 1
    else:
        assert result["outcome"] == "reused" and scan.llm.call_count == 0


def test_description_analysis_is_never_a_showroom_donor(scan):
    prime(scan)
    as_donor(scan, repo="description:example.item.prod")
    assert scan.run(ci_name="example.item.dev")["outcome"] == "analyzed"


@pytest.mark.parametrize("field,value", [("showroom_url_override", "url"), ("content_path", "content/modules/ROOT/pages")])
def test_curator_url_or_path_override_is_target_scoped(scan, git_repo, field, value):
    if value == "url":
        value = str(git_repo[0])
    scan.db.item = {"ci_name": "example.item.prod", "stage": "prod", "showroom_source_json": replace(scan.source, scope_key="example.base").to_dict(), field: value}
    result = scan.run()
    signature = result["analysis_provenance"]["signature"]
    assert signature["scope_key"] == "example.item"
    assert result["analysis_provenance"]["source"]["override_origins"]
