"""Description-based analysis: source resolution, setter, analyzer, pipeline."""

import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from tests.showroom_helpers import db  # noqa: F401 — pytest fixture
from rcars.services import analyzer
from rcars.services.showroom_source import effective_analysis_source

URL = "https://github.com/example/content"


def add_item(database, name="isolation-test.desc-a.prod", **updates):
    payload = {
        "ci_name": name,
        "stage": name.rsplit(".", 1)[-1],
        "display_name": name,
        "category": "Workshop",
        "showroom_url": URL,
        "showroom_ref": "main",
        "description": "Provides a cluster.",
    }
    payload.update(updates)
    return database.upsert_babylon_catalog_item(payload)


def seed_artifacts(database, content_id):
    database.upsert_showroom_analysis(
        {"content_id": content_id, "summary": "Old analysis", "modules_json": [], "content_hash": "abc"}
    )
    database.replace_embeddings(content_id, [{
        "content_id": content_id, "content_type": "lab", "source": "babylon",
        "embed_type": "summary", "content_text": "old", "embedding": [0.1] * 768,
    }])


def test_set_analysis_source_custom_requires_text(db):
    content_id = add_item(db)
    with pytest.raises(ValueError):
        db.set_analysis_source(content_id, "custom_description", None)
    with pytest.raises(ValueError):
        db.set_analysis_source(content_id, "custom_description", "   ")


def test_set_analysis_source_description_requires_stored_description(db):
    content_id = add_item(db, description="")
    with pytest.raises(ValueError):
        db.set_analysis_source(content_id, "agnosticv_description")


def test_set_analysis_source_updates_columns_and_clears_artifacts(db):
    content_id = add_item(db)
    seed_artifacts(db, content_id)

    db.set_analysis_source(content_id, "agnosticv_description")

    item = db.get_babylon_item(content_id)
    assert item["analysis_source_override"] == "agnosticv_description"
    assert item["custom_description"] is None
    assert item["scan_status"] == "not_scanned"
    assert db.get_showroom_analysis(content_id)["summary"] is None
    assert db.get_embeddings_for_content(content_id) == []


def test_set_analysis_source_reverting_to_showroom_clears_artifacts(db):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "custom_description", "Custom text")
    seed_artifacts(db, content_id)

    db.set_analysis_source(content_id, "showroom")

    item = db.get_babylon_item(content_id)
    assert item["analysis_source_override"] is None
    assert item["custom_description"] is None
    assert db.get_showroom_analysis(content_id)["summary"] is None
    assert db.get_embeddings_for_content(content_id) == []


def test_set_analysis_source_is_noop_when_unchanged(db):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "custom_description", "Custom text")
    seed_artifacts(db, content_id)

    db.set_analysis_source(content_id, "custom_description", "Custom text")

    assert db.get_showroom_analysis(content_id)["summary"] == "Old analysis"
    assert len(db.get_embeddings_for_content(content_id)) == 1


def test_clear_babylon_generated_artifacts_preserves_override(db):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")

    with db.pool.connection() as conn:
        db.invalidate_babylon_scan_failure(content_id, "parse_failed", "bad", conn=conn)

    item = db.get_babylon_item(content_id)
    assert item["analysis_source_override"] == "agnosticv_description"
    assert item["custom_description"] is None


# ── Task 3: analyze_description ──


LLM_RESPONSE = '{"summary":"Description summary","modules":[]}'


def mock_analysis(monkeypatch):
    llm = Mock(return_value=SimpleNamespace(
        text=LLM_RESPONSE, input_tokens=1, output_tokens=1, provider="test"))
    embed = Mock(return_value=[0.1] * 768)
    monkeypatch.setattr("rcars.config.call_llm", llm)
    monkeypatch.setattr(analyzer, "generate_embedding", embed)
    settings = SimpleNamespace(model="example-model", embedding_model="example-embed",
                               embedding_dim=768, clone_dir="/tmp")
    return SimpleNamespace(llm=llm, embed=embed, settings=settings)


def persist_result(database, content_id, result):
    analysis = result["analysis"]
    data = {
        "content_id": content_id,
        "analysis_provenance_json": result["analysis_provenance"],
        "content_hash": result["content_hash"], "is_stale": False,
        "last_repo_commit": result["last_repo_commit"],
        "last_analyzed": result["last_analyzed"],
    }
    for key in ("summary", "content_type", "difficulty", "estimated_duration_min"):
        data[key] = analysis.get(key)
    for key in ("products", "audience", "recommender_audience", "topics", "modules",
                "learning_objectives", "format_suitability", "use_cases"):
        data[key + "_json"] = analysis.get(key)
    data["modules_json"] = analysis.get("modules") or []
    database.upsert_showroom_analysis(data)
    rows = [{
        "content_id": content_id, "content_type": "lab", "source": "babylon",
        "embed_type": "summary", "content_text": result["ci_embedding_text"],
        "embedding": result["ci_embedding"],
    }]
    rows += [{
        "content_id": content_id, "content_type": "lab", "source": "babylon",
        "embed_type": "module", "module_title": module["module_title"],
        "content_text": module["content_text"], "embedding": module["embedding"],
    } for module in result["module_embeddings"]]
    database.replace_embeddings(content_id, rows)
    database.set_scan_status(content_id, "success")


def set_raw(database, table, column, value, content_id):
    with database.pool.connection() as conn:
        conn.execute(f"UPDATE {table} SET {column} = %s WHERE content_id = %s", (value, content_id))


def test_analyze_description_first_run_analyzes(db, monkeypatch):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    env = mock_analysis(monkeypatch)

    result = analyzer.analyze_description(db.get_babylon_item(content_id), env.settings, db=db)

    assert result["outcome"] == "analyzed"
    assert env.llm.call_count == 1
    assert result["analysis_provenance"]["source_type"] == "agnosticv_description"
    assert result["analysis_provenance"]["signature"]["repo"] == f"description:{content_id.removeprefix('babylon:')}"


def test_analyze_description_second_run_unchanged(db, monkeypatch):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    env = mock_analysis(monkeypatch)
    persist_result(db, content_id, analyzer.analyze_description(
        db.get_babylon_item(content_id), env.settings, db=db))
    env.llm.reset_mock()
    env.embed.reset_mock()

    result = analyzer.analyze_description(db.get_babylon_item(content_id), env.settings, db=db)

    assert result["outcome"] == "unchanged"
    assert env.llm.call_count == 0
    assert env.embed.call_count == 0


def test_analyze_description_force_bypasses_shortcircuit(db, monkeypatch):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    env = mock_analysis(monkeypatch)
    persist_result(db, content_id, analyzer.analyze_description(
        db.get_babylon_item(content_id), env.settings, db=db))
    env.llm.reset_mock()

    result = analyzer.analyze_description(db.get_babylon_item(content_id), env.settings, db=db, force=True)

    assert result["outcome"] == "analyzed"
    assert env.llm.call_count == 1


def test_analyze_description_changed_text_reruns(db, monkeypatch):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    env = mock_analysis(monkeypatch)
    persist_result(db, content_id, analyzer.analyze_description(
        db.get_babylon_item(content_id), env.settings, db=db))
    env.llm.reset_mock()
    set_raw(db, "babylon_items", "description", "A different description.", content_id)

    result = analyzer.analyze_description(db.get_babylon_item(content_id), env.settings, db=db)

    assert result["outcome"] == "analyzed"
    assert env.llm.call_count == 1


def test_analyze_description_rename_reruns(db, monkeypatch):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    env = mock_analysis(monkeypatch)
    persist_result(db, content_id, analyzer.analyze_description(
        db.get_babylon_item(content_id), env.settings, db=db))
    env.llm.reset_mock()
    set_raw(db, "content_entities", "display_name", "A new display name", content_id)

    result = analyzer.analyze_description(db.get_babylon_item(content_id), env.settings, db=db)

    assert result["outcome"] == "analyzed"
    assert env.llm.call_count == 1


def test_analyze_description_blank_text_returns_no_content(db, monkeypatch):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    set_raw(db, "babylon_items", "description", "   ", content_id)
    env = mock_analysis(monkeypatch)

    result = analyzer.analyze_description(db.get_babylon_item(content_id), env.settings, db=db)

    assert result["error"] == "no_content"
    assert env.llm.call_count == 0


def test_effective_analysis_source_defaults_to_showroom():
    assert effective_analysis_source({}) == "showroom"
    assert effective_analysis_source({"analysis_source_override": None}) == "showroom"
    assert effective_analysis_source({"analysis_source_override": "bogus"}) == "showroom"


def test_effective_analysis_source_returns_override():
    assert effective_analysis_source(
        {"analysis_source_override": "agnosticv_description"}
    ) == "agnosticv_description"
    assert effective_analysis_source(
        {"analysis_source_override": "custom_description"}
    ) == "custom_description"
