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


def test_set_analysis_source_rejects_sandbox_items(db):
    content_id = add_item(db, showroom_url=None)
    assert db.get_babylon_item(content_id)["content_type"] == "sandbox"

    with pytest.raises(ValueError):
        db.set_analysis_source(content_id, "agnosticv_description")

    # Reverting to showroom stays allowed so an existing override can be cleared.
    db.set_analysis_source(content_id, "showroom")


def test_set_analysis_source_rejects_content_owner_stubs(db):
    owner = "isolation-test.desc-owner.prod"
    add_item(db, owner)
    stub_id = add_item(db, "isolation-test.desc-stub.prod", showroom_source={
        "status": "resolved", "owner_ci_name": owner,
        "scope_key": "isolation-test.desc-owner", "repo": URL, "ref": "main",
    })

    with pytest.raises(ValueError):
        db.set_analysis_source(stub_id, "agnosticv_description")


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


def test_analyze_description_custom_text_runs_once_then_unchanged(db, monkeypatch):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "custom_description", "Curator text one")
    env = mock_analysis(monkeypatch)

    first = analyzer.analyze_description(db.get_babylon_item(content_id), env.settings, db=db)
    assert first["outcome"] == "analyzed"
    assert first["analysis_provenance"]["source_type"] == "custom_description"
    persist_result(db, content_id, first)
    env.llm.reset_mock()

    second = analyzer.analyze_description(db.get_babylon_item(content_id), env.settings, db=db)
    assert second["outcome"] == "unchanged"
    assert env.llm.call_count == 0


def test_analyze_description_custom_text_edit_reruns(db, monkeypatch):
    content_id = add_item(db)
    db.set_analysis_source(content_id, "custom_description", "Curator text one")
    env = mock_analysis(monkeypatch)
    persist_result(db, content_id, analyzer.analyze_description(
        db.get_babylon_item(content_id), env.settings, db=db))
    db.set_analysis_source(content_id, "custom_description", "Curator text two")
    env.llm.reset_mock()

    result = analyzer.analyze_description(db.get_babylon_item(content_id), env.settings, db=db)

    assert result["outcome"] == "analyzed"
    assert env.llm.call_count == 1


# ── Task 4: candidate selection ──


def add_description_item(database, name="isolation-test.desc-cand.prod"):
    return add_item(database, name, showroom_url=None,
                    showroom_source={"status": "invalid", "error": "no_showroom"})


def selected_names(database, settings):
    return [item["ci_name"] for item in database.get_items_needing_analysis(settings)]


def test_needing_analysis_includes_description_item_without_showroom(db, monkeypatch):
    content_id = add_description_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    env = mock_analysis(monkeypatch)

    assert "isolation-test.desc-cand.prod" in selected_names(db, env.settings)


def test_needing_analysis_skips_current_description_item(db, monkeypatch):
    content_id = add_description_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    add_description_item(db, "isolation-test.desc-cand2.prod")
    db.set_analysis_source("babylon:isolation-test.desc-cand2.prod", "agnosticv_description")
    env = mock_analysis(monkeypatch)
    persist_result(db, content_id, analyzer.analyze_description(
        db.get_babylon_item(content_id), env.settings, db=db))

    selected = selected_names(db, env.settings)
    assert "isolation-test.desc-cand.prod" not in selected
    assert "isolation-test.desc-cand2.prod" in selected


def test_needing_analysis_reselects_description_item_after_text_edit(db, monkeypatch):
    content_id = add_description_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    env = mock_analysis(monkeypatch)
    persist_result(db, content_id, analyzer.analyze_description(
        db.get_babylon_item(content_id), env.settings, db=db))
    assert "isolation-test.desc-cand.prod" not in selected_names(db, env.settings)

    set_raw(db, "babylon_items", "description", "The description changed upstream.", content_id)

    assert "isolation-test.desc-cand.prod" in selected_names(db, env.settings)


def test_needing_analysis_still_skips_content_owner_stubs(db, monkeypatch):
    owner = "isolation-test.desc-owner.prod"
    add_item(db, owner)
    stub = "isolation-test.desc-stub.prod"
    stub_id = add_item(db, stub, showroom_source={
        "status": "resolved", "owner_ci_name": owner,
        "scope_key": "isolation-test.desc-owner", "repo": URL, "ref": "main",
    })
    # The setter now rejects stubs; simulate a pre-existing override directly.
    set_raw(db, "babylon_items", "analysis_source_override", "agnosticv_description", stub_id)
    env = mock_analysis(monkeypatch)

    assert stub not in selected_names(db, env.settings)


# ── Task 5: scan pipeline ──


def test_scan_description_item_succeeds(db, monkeypatch):
    from rcars.services.showroom_scan import scan_babylon_item

    content_id = add_description_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    with db.pool.connection() as conn:
        db.invalidate_babylon_scan_failure(content_id, "invalid_source", "no source", conn=conn)
    env = mock_analysis(monkeypatch)

    result = scan_babylon_item(db, env.settings, content_id)

    assert result["success"] is True
    assert result["outcome"] == "analyzed"
    assert db.get_babylon_item(content_id)["scan_status"] == "success"
    analysis = db.get_showroom_analysis(content_id)
    assert analysis["summary"] == "Description summary"
    assert analysis["analysis_provenance_json"]["source_type"] == "agnosticv_description"
    assert db.get_content_entity(content_id)["summary"] == "Description summary"
    embeddings = db.get_embeddings_for_content(content_id)
    assert [row["embed_type"] for row in embeddings] == ["summary"]


def test_snapshot_includes_analysis_source_fields():
    from rcars.services.showroom_scan import _snapshot

    assert _snapshot({"ci_name": "a.prod"}) != _snapshot(
        {"ci_name": "a.prod", "analysis_source_override": "custom_description"})


def test_scan_description_error_marks_failed(db, monkeypatch):
    from rcars.services.showroom_scan import scan_babylon_item

    content_id = add_description_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    env = mock_analysis(monkeypatch)
    env.llm.return_value = SimpleNamespace(
        text="this is not json", input_tokens=1, output_tokens=1, provider="test")

    result = scan_babylon_item(db, env.settings, content_id)

    assert result["outcome"] == "failed"
    item = db.get_babylon_item(content_id)
    assert item["scan_status"] == "failed"
    assert item["scan_error_class"] == "parse_failed"


def test_scan_blank_description_marks_no_content(db, monkeypatch):
    from rcars.services.showroom_scan import scan_babylon_item

    content_id = add_description_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    set_raw(db, "babylon_items", "description", "   ", content_id)
    env = mock_analysis(monkeypatch)

    result = scan_babylon_item(db, env.settings, content_id)

    assert result["outcome"] == "failed"
    assert db.get_babylon_item(content_id)["scan_error_class"] == "no_content"
    assert env.llm.call_count == 0


# ── Task 6: stale check ──


def test_stale_check_candidates_exclude_description_items(db, monkeypatch):
    content_id = add_description_item(db)
    db.set_analysis_source(content_id, "agnosticv_description")
    env = mock_analysis(monkeypatch)
    persist_result(db, content_id, analyzer.analyze_description(
        db.get_babylon_item(content_id), env.settings, db=db))
    showroom_id = add_item(db, "isolation-test.show.prod")
    db.upsert_showroom_analysis({
        "content_id": showroom_id, "summary": "Showroom analysis",
        "modules_json": [], "content_hash": "abc",
    })

    names = [row["ci_name"] for row in db.get_stale_check_candidates()]

    assert "isolation-test.desc-cand.prod" not in names
    assert "isolation-test.show.prod" in names


# ── Task 7: API endpoint ──


def route_request(database, arq_redis=None):
    from unittest.mock import AsyncMock
    from rcars.config import Settings
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        db=database, settings=Settings(database_url=database._url),
        arq_redis=arq_redis or AsyncMock())))


@pytest.mark.asyncio
async def test_analysis_source_endpoint_curator_ok(db):
    from rcars.api.routes.catalog import AnalysisSourceRequest, set_analysis_source

    content_id = add_item(db)
    arq = route_request(db).app.state.arq_redis

    result = await set_analysis_source(
        "isolation-test.desc-a.prod",
        AnalysisSourceRequest(source="agnosticv_description"),
        route_request(db, arq), user="test@example.com",
    )

    assert result["job_id"]
    assert db.get_babylon_item(content_id)["analysis_source_override"] == "agnosticv_description"
    assert arq.enqueue_job.await_count == 1


@pytest.mark.asyncio
async def test_analysis_source_endpoint_requires_curator():
    from fastapi.testclient import TestClient
    from rcars.api.app import create_app
    from rcars.config import Settings

    settings = Settings(
        database_url="postgresql://rcars:dev@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="", curator_emails_str="curator@redhat.com",
        admin_emails_str="", proxy_verification_secret="s3cret",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.put(
            "/api/v1/catalog/isolation-test.desc-a.prod/analysis-source",
            json={"source": "showroom"},
            headers={"X-Proxy-Secret": "s3cret", "X-Forwarded-Email": "user@redhat.com"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_analysis_source_endpoint_custom_without_text_400(db):
    from fastapi import HTTPException
    from rcars.api.routes.catalog import AnalysisSourceRequest, set_analysis_source

    add_item(db)
    with pytest.raises(HTTPException) as excinfo:
        await set_analysis_source(
            "isolation-test.desc-a.prod",
            AnalysisSourceRequest(source="custom_description"),
            route_request(db), user="test@example.com",
        )
    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_analysis_source_endpoint_empty_description_400(db):
    from fastapi import HTTPException
    from rcars.api.routes.catalog import AnalysisSourceRequest, set_analysis_source

    add_item(db, description="")
    with pytest.raises(HTTPException) as excinfo:
        await set_analysis_source(
            "isolation-test.desc-a.prod",
            AnalysisSourceRequest(source="agnosticv_description"),
            route_request(db), user="test@example.com",
        )
    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_catalog_detail_includes_analysis_source_fields(db):
    from rcars.api.routes.catalog import get_catalog_item

    content_id = add_item(db)
    db.set_analysis_source(content_id, "custom_description", "Custom text")

    detail = await get_catalog_item(
        "isolation-test.desc-a.prod", route_request(db), user="test@example.com")

    assert detail["analysis_source_override"] == "custom_description"
    assert detail["custom_description"] == "Custom text"


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
