"""Vocabulary generator + admin endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import yaml
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings
from rcars.services.vocabulary import generate_vocabulary_yaml, load_vocabulary


@pytest.fixture(autouse=True)
def clear_vocabulary_cache():
    load_vocabulary.cache_clear()
    yield
    load_vocabulary.cache_clear()


@pytest.fixture
def client():
    settings = Settings(
        database_url="postgresql://rcars:rcars@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="admin@redhat.com",
        admin_emails_str="admin@redhat.com",
        curator_emails_str="admin@redhat.com,curator@redhat.com",
    )
    app = create_app(settings)
    app.state.db = MagicMock()
    app.state.redis = MagicMock()
    app.state.arq_redis = MagicMock()
    return TestClient(app)


class TestGenerator:
    def test_round_trips_current_vocabulary(self, tmp_path, monkeypatch):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [])

        path = tmp_path / "vocabulary.yaml"
        path.write_text(generated)
        monkeypatch.setenv("RCARS_VOCABULARY_PATH", str(path))
        load_vocabulary.cache_clear()
        reloaded = load_vocabulary()

        assert reloaded.canonical_names("products") == vocab.canonical_names("products")
        assert reloaded.canonical_names("solutions") == vocab.canonical_names("solutions")
        assert reloaded.content_modes == vocab.content_modes
        assert reloaded.ignored_terms == vocab.ignored_terms

    def test_alias_decision_appends_to_existing_entry(self, tmp_path, monkeypatch):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [{
            "dimension": "products",
            "term": "RHOCP",
            "status": "aliased",
            "resolved_to": "Red Hat OpenShift Container Platform",
        }])
        data = yaml.safe_load(generated)
        entry = next(
            e for e in data["products"] if e["name"] == "Red Hat OpenShift Container Platform"
        )
        assert "RHOCP" in entry["aliases"]

    def test_promote_decision_creates_new_entry(self):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [{
            "dimension": "products",
            "term": "Brand New Product",
            "status": "promoted",
            "resolved_to": None,
        }])
        data = yaml.safe_load(generated)
        assert any(e["name"] == "Brand New Product" for e in data["products"])

    def test_rejections_are_preserved_in_ignored_terms(self):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [{
            "dimension": "products",
            "term": "Wombat Server",
            "status": "rejected",
            "resolved_to": None,
        }])
        data = yaml.safe_load(generated)
        assert "Wombat Server" in data["ignored_terms"]["products"]
        assert "Kubernetes" in data["ignored_terms"]["products"]

    def test_pending_decisions_are_ignored(self):
        vocab = load_vocabulary()
        generated = generate_vocabulary_yaml(vocab, [{
            "dimension": "products",
            "term": "Undecided Thing",
            "status": "pending",
            "resolved_to": None,
        }])
        assert "Undecided Thing" not in generated

    def test_generated_file_keeps_the_header_comment(self):
        generated = generate_vocabulary_yaml(load_vocabulary(), [])
        assert generated.lstrip().startswith("#")
        assert "rcars" in generated.lower()


class TestVocabularyEndpoints:
    def test_get_vocabulary(self, client):
        resp = client.get("/api/v1/admin/vocabulary")
        assert resp.status_code == 200
        data = resp.json()
        names = [e["name"] for e in data["dimensions"]["products"]]
        assert "Red Hat OpenShift Container Platform" in names
        assert data["content_modes"]["lab"] == "hands_on"

    def test_get_unknowns(self, client):
        client.app.state.db.get_unknown_terms.return_value = [
            {"dimension": "products", "term": "Wombat", "occurrences": 4,
             "first_seen": None, "last_seen": None, "example_content_id": "babylon:lb1",
             "status": "pending", "resolved_to": None, "resolved_by": None, "resolved_at": None},
        ]
        resp = client.get("/api/v1/admin/vocabulary/unknowns")
        assert resp.status_code == 200
        assert resp.json()["terms"][0]["term"] == "Wombat"
        client.app.state.db.get_unknown_terms.assert_called_with(
            status="pending", dimension=None
        )

    def test_resolve_alias(self, client):
        client.app.state.db.resolve_unknown_term.return_value = {
            "dimension": "products", "term": "RHOCP", "occurrences": 1,
            "first_seen": None, "last_seen": None, "example_content_id": None,
            "status": "aliased", "resolved_to": "Red Hat OpenShift Container Platform",
            "resolved_by": "admin@redhat.com", "resolved_at": None,
        }
        resp = client.put(
            "/api/v1/admin/vocabulary/unknowns/products/RHOCP",
            json={"action": "alias", "resolved_to": "Red Hat OpenShift Container Platform"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "aliased"

    def test_resolve_alias_requires_target(self, client):
        resp = client.put(
            "/api/v1/admin/vocabulary/unknowns/products/RHOCP",
            json={"action": "alias"},
        )
        assert resp.status_code == 400

    def test_resolve_rejects_unknown_canonical(self, client):
        resp = client.put(
            "/api/v1/admin/vocabulary/unknowns/products/RHOCP",
            json={"action": "alias", "resolved_to": "Not A Real Canonical"},
        )
        assert resp.status_code == 400

    def test_resolve_missing_term_404(self, client):
        client.app.state.db.resolve_unknown_term.return_value = None
        resp = client.put(
            "/api/v1/admin/vocabulary/unknowns/products/Nope",
            json={"action": "reject"},
        )
        assert resp.status_code == 404

    def test_generate_returns_downloadable_yaml(self, client):
        client.app.state.db.get_unknown_terms.return_value = []
        resp = client.get("/api/v1/admin/vocabulary/generate")
        assert resp.status_code == 200
        assert "attachment" in resp.headers["content-disposition"]
        assert "vocabulary.yaml" in resp.headers["content-disposition"]
        assert "products:" in resp.text


class TestRoleGating:
    @pytest.fixture
    def curator_client(self, client):
        client.app.state.settings.dev_user = "curator@redhat.com"
        return client

    def test_all_four_endpoints_reject_curators(self, curator_client):
        assert curator_client.get("/api/v1/admin/vocabulary").status_code == 403
        assert curator_client.get("/api/v1/admin/vocabulary/unknowns").status_code == 403
        assert curator_client.get("/api/v1/admin/vocabulary/generate").status_code == 403
        assert curator_client.put(
            "/api/v1/admin/vocabulary/unknowns/products/X", json={"action": "reject"}
        ).status_code == 403
