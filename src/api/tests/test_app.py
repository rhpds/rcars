import pytest
from fastapi.testclient import TestClient
from rcars.api.app import create_app
from rcars.config import Settings


@pytest.fixture
def client():
    settings = Settings(
        database_url="postgresql://rcars:dev@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
        dev_user="test@redhat.com",
        admin_emails_str="test@redhat.com",
        curator_emails_str="test@redhat.com",
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_auth_me(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@redhat.com"
    assert "admin" in data["roles"]
    assert "curator" in data["roles"]
    assert "user" in data["roles"]


def test_auth_me_unauthenticated():
    settings = Settings(
        database_url="postgresql://rcars:dev@localhost:5432/rcars_test",
        redis_url="redis://localhost:6379",
    )
    app = create_app(settings)
    with TestClient(app) as c:
        resp = c.get("/api/v1/auth/me")
        assert resp.status_code == 401


def test_swagger_docs(client):
    resp = client.get("/api/v1/docs")
    assert resp.status_code == 200


def test_openapi_schema(client):
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/auth/me" in schema["paths"]
