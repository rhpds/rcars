"""Tests for GET /catalog/infrastructure endpoint and removal of old workload-mapping endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from rcars.api.app import create_app
from rcars.config import Settings
from rcars.db.database import Database


TEST_DB_URL = "postgresql://rcars:dev@localhost:5432/rcars_test"


@pytest.fixture(scope="module")
def client():
    settings = Settings(
        database_url=TEST_DB_URL,
        redis_url="redis://localhost:6379",
        dev_user="test@redhat.com",
        admin_emails_str="test@redhat.com",
        curator_emails_str="test@redhat.com",
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def seed_infrastructure():
    db = Database(TEST_DB_URL)
    db.create_schema()
    db.upsert_infrastructure(
        role_name="ocp4_workload_rhods",
        fqcn="agnosticd.ai_workloads.ocp4_workload_rhods",
        collection="agnosticd.ai_workloads",
        type="workload",
        description="Installs OpenShift AI (RHOAI) operator and components.",
        products=["OpenShift AI", "KServe"],
        capabilities=["model-serving", "notebook-hosting"],
        category="ai_ml",
        requires=[],
        source_sha="abc123",
    )
    db.upsert_infrastructure(
        role_name="openshift-cluster",
        fqcn=None,
        collection=None,
        type="config",
        description="Base OpenShift cluster config.",
        products=["OpenShift"],
        capabilities=["cluster-provisioning"],
        category="platform",
        requires=[],
        source_sha="def456",
    )
    yield
    with db.pool.connection() as conn:
        conn.execute(
            "DELETE FROM infrastructure WHERE role_name IN ('ocp4_workload_rhods', 'openshift-cluster')"
        )
        conn.commit()
    db.close()


def test_get_infrastructure(client):
    resp = client.get("/api/v1/catalog/infrastructure")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) > 0
    assert "item_count" in data["items"][0]


def test_get_infrastructure_type_filter(client):
    resp = client.get("/api/v1/catalog/infrastructure?type=workload")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["type"] == "workload"


def test_old_workload_mappings_removed(client):
    resp = client.post("/api/v1/catalog/workload-mappings",
                       json={"workload_role": "x", "product_name": "y"})
    assert resp.status_code in (404, 405)

    resp = client.delete("/api/v1/catalog/workload-mappings/x")
    assert resp.status_code in (404, 405)

    resp = client.get("/api/v1/catalog/workload-mappings/unmapped")
    assert resp.status_code in (404, 405)


def test_sync_osspa_endpoint_enqueues_a_job(client, monkeypatch):
    enqueued = {}

    async def _enqueue(name, **kwargs):
        enqueued["name"] = name
        enqueued["kwargs"] = kwargs

    client.app.state.arq_redis.enqueue_job = _enqueue

    resp = client.post("/api/v1/admin/sync-osspa",
                       json={"force": True, "confirm_empty_inventory": False})

    assert resp.status_code == 200
    assert "job_id" in resp.json()
    assert enqueued["name"] == "run_osspa_sync_job"
    assert enqueued["kwargs"]["force"] is True
    assert enqueued["kwargs"]["confirm_empty_inventory"] is False
