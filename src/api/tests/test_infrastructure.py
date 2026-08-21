"""Tests for infrastructure table DB operations."""

from __future__ import annotations

import os

import psycopg
import pytest

from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture(scope="module")
def db():
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


@pytest.fixture(autouse=True)
def clean_infra(db):
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM infrastructure")
        conn.commit()


def test_upsert_infrastructure_insert(db):
    db.upsert_infrastructure(
        role_name="ocp4_workload_rhods",
        fqcn="agnosticd.ai_workloads.ocp4_workload_rhods",
        collection="agnosticd.ai_workloads",
        type="workload",
        description="Installs OpenShift AI (RHOAI) operator and components.",
        products=["OpenShift AI", "KServe"],
        capabilities=["model-serving", "notebook-hosting"],
        category="ai_ml",
        requires=["openshift 4.14+", "gpu-nodes"],
        source_sha="abc123",
    )
    row = db.get_infrastructure("ocp4_workload_rhods")
    assert row is not None
    assert row["type"] == "workload"
    assert row["description"] == "Installs OpenShift AI (RHOAI) operator and components."
    assert row["products"] == ["OpenShift AI", "KServe"]
    assert row["capabilities"] == ["model-serving", "notebook-hosting"]
    assert row["category"] == "ai_ml"


def test_upsert_infrastructure_update(db):
    db.upsert_infrastructure(
        role_name="ocp4_workload_rhods", fqcn=None, collection="agnosticd.ai_workloads",
        type="workload", description="v1", products=[], capabilities=[], category="ai_ml",
        requires=[], source_sha="sha1",
    )
    db.upsert_infrastructure(
        role_name="ocp4_workload_rhods", fqcn=None, collection="agnosticd.ai_workloads",
        type="workload", description="v2", products=["RHOAI"], capabilities=["notebooks"],
        category="ai_ml", requires=[], source_sha="sha2",
    )
    row = db.get_infrastructure("ocp4_workload_rhods")
    assert row["description"] == "v2"
    assert row["products"] == ["RHOAI"]
    assert row["source_sha"] == "sha2"


def test_list_infrastructure_with_type_filter(db):
    db.upsert_infrastructure(
        role_name="ocp4_workload_acs", fqcn=None, collection="agnosticd.core_workloads",
        type="workload", description="ACS", products=["ACS"], capabilities=[],
        category="security", requires=[], source_sha="sha1",
    )
    db.upsert_infrastructure(
        role_name="openshift-cluster", fqcn=None, collection=None,
        type="config", description="Base OpenShift cluster", products=["OpenShift"],
        capabilities=["cluster-provisioning"], category="platform", requires=[],
        source_sha="sha2",
    )
    all_rows = db.list_infrastructure()
    assert len(all_rows) == 2

    workloads = db.list_infrastructure(type_filter="workload")
    assert len(workloads) == 1
    assert workloads[0]["role_name"] == "ocp4_workload_acs"

    configs = db.list_infrastructure(type_filter="config")
    assert len(configs) == 1
    assert configs[0]["role_name"] == "openshift-cluster"


def test_get_infrastructure_with_item_counts(db):
    db.upsert_infrastructure(
        role_name="ocp4_workload_rhods", fqcn="agnosticd.ai_workloads.ocp4_workload_rhods",
        collection="agnosticd.ai_workloads", type="workload", description="RHOAI",
        products=["OpenShift AI"], capabilities=[], category="ai_ml", requires=[],
        source_sha="sha1",
    )
    rows = db.get_infrastructure_with_item_counts()
    assert any(r["role_name"] == "ocp4_workload_rhods" for r in rows)
    row = next(r for r in rows if r["role_name"] == "ocp4_workload_rhods")
    assert row["item_count"] == 0
