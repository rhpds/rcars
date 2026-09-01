import os

import pytest
from fastapi.testclient import TestClient

from rcars.api.app import create_app
from rcars.config import Settings
from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def settings():
    return Settings(
        database_url=TEST_DB_URL,
        redis_url="redis://localhost:6379",
        dev_user="test@redhat.com",
        admin_emails_str="test@redhat.com",
        curator_emails_str="test@redhat.com",
    )


@pytest.fixture
def db(settings):
    import psycopg
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")
    database = Database(TEST_DB_URL)
    database.create_schema()
    database.upsert_osspa_item({
        "content_id": "pa:275", "ppid": 275, "pa_name": "275-rhacs",
        "display_name": "Multitenant Setup for RHACS", "status": "prod",
        "summary": "CSV seed", "products": ["RHACS"], "topics": ["Security"],
        "audience": ["architect"], "solutions": ["Security"], "verticals": ["All"],
        "detail_page": "rhacs.adoc", "image_url": "images/x.png",
        "is_live": True, "show_in_catalog": True, "asset_type": "PA,VP",
    })
    database.upsert_architecture_analysis({
        "content_id": "pa:275", "summary": "LLM summary",
        "use_cases_json": ["Isolate tenants"], "key_components_json": ["RHACS"],
        "solution_areas_json": ["Application Platform"], "content_hash": "h1",
    })
    database.upsert_babylon_catalog_item({
        "ci_name": "lab.prod", "display_name": "A Lab", "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod", "showroom_url": "https://example.com/r"})
    yield database
    database.close()


@pytest.fixture
def client(settings, db):
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def test_list_returns_architecture_card_fields(client):
    resp = client.get("/api/v1/catalog", params={"content_type": "architecture", "stage": "prod"})
    assert resp.status_code == 200
    item = resp.json()["items"][0]

    assert item["content_id"] == "pa:275"
    assert item["ci_name"] is None
    assert item["source"] == "portfolio_arch"
    assert item["content_type"] == "architecture"
    assert item["is_hands_on"] is False
    assert item["status"] == "prod"
    assert item["pa_name"] == "275-rhacs"
    assert item["asset_type"] == "PA,VP"
    assert item["solutions"] == ["Security"]


def test_detail_route_resolves_a_pa_identifier(client):
    resp = client.get("/api/v1/catalog/pa:275")
    assert resp.status_code == 200
    body = resp.json()

    assert body["display_name"] == "Multitenant Setup for RHACS"
    assert body["analysis"]["summary"] == "LLM summary"
    assert body["analysis"]["use_cases_json"] == ["Isolate tenants"]
    assert body["pa_name"] == "275-rhacs"
    assert body["source_url"].endswith("/-/blob/main/rhacs.adoc")
    assert body["workloads"] == []
    assert body["acl_groups"] == []


def test_detail_route_unprefixed_identifier_still_means_babylon(client):
    resp = client.get("/api/v1/catalog/lab.prod")
    assert resp.status_code == 200
    assert resp.json()["ci_name"] == "lab.prod"


def test_analysis_route_is_source_aware(client):
    assert client.get("/api/v1/catalog/pa:275/analysis").json()["summary"] == "LLM summary"


def test_curator_actions_work_on_a_pa_identifier(client, db):
    assert client.post("/api/v1/catalog/pa:275/tags",
                       json={"tag_type": "label", "tag_value": "sovereign-cloud"}).status_code == 200
    assert client.put("/api/v1/catalog/pa:275/note", json={"note": "checked"}).status_code == 200
    assert client.post("/api/v1/catalog/pa:275/flag").status_code == 200

    analysis = db.get_architecture_analysis("pa:275")
    assert analysis["notes"] == "checked"
    assert analysis["enrichment_review_needed"] is True
    assert client.get("/api/v1/catalog/pa:275").json()["tags"][0]["tag_value"] == "sovereign-cloud"


def test_unknown_pa_identifier_is_404(client):
    assert client.get("/api/v1/catalog/pa:9999").status_code == 404


def _second_architecture(db):
    db.upsert_osspa_item({
        "content_id": "pa:300", "ppid": 300, "pa_name": "300-edge",
        "display_name": "Edge Manufacturing", "status": "prod",
        "summary": "s", "products": [], "topics": [], "audience": [],
        "solutions": ["Edge"], "verticals": ["Manufacturing"],
        "detail_page": "edge.adoc", "image_url": None,
        "is_live": True, "show_in_catalog": True, "asset_type": "SP",
    })
    db.update_content_entity_card("pa:300", summary="s", products_json=[],
                                  topics_json=[], audience_json=["operations teams"],
                                  difficulty=None)


def test_solutions_filter_narrows_to_matching_architectures(client, db):
    _second_architecture(db)

    resp = client.get("/api/v1/catalog",
                      params={"content_type": "architecture", "stage": "prod", "solutions": "Edge"})

    assert [i["content_id"] for i in resp.json()["items"]] == ["pa:300"]


def test_verticals_filter_narrows_to_matching_architectures(client, db):
    _second_architecture(db)

    resp = client.get("/api/v1/catalog",
                      params={"content_type": "architecture", "stage": "prod", "verticals": "Manufacturing"})

    assert [i["content_id"] for i in resp.json()["items"]] == ["pa:300"]


def test_solutions_filter_excludes_babylon_items(client, db):
    resp = client.get("/api/v1/catalog",
                      params={"content_type": "lab,demo,sandbox,architecture",
                              "stage": "prod", "solutions": "Security"})

    assert [i["content_id"] for i in resp.json()["items"]] == ["pa:275"]


def test_audience_filter_applies_across_content_types(client, db):
    _second_architecture(db)
    db.update_content_entity_card("pa:275", summary="LLM summary", products_json=["RHACS"],
                                  topics_json=["Security"], audience_json=["security architects"],
                                  difficulty="intermediate")

    resp = client.get("/api/v1/catalog",
                      params={"content_type": "architecture", "stage": "prod",
                              "audience": "operations teams"})

    assert [i["content_id"] for i in resp.json()["items"]] == ["pa:300"]


def test_facets_include_solutions_verticals_and_audience(client, db):
    _second_architecture(db)

    facets = client.get("/api/v1/catalog/facets").json()

    assert "Security" in facets["solutions"]
    assert "Manufacturing" in facets["verticals"]
    assert "operations teams" in facets["audience"]
