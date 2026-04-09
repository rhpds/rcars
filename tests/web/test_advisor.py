import pytest
from starlette.testclient import TestClient
from rcars.web.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_advisor_page_loads(client):
    response = client.get("/advisor")
    assert response.status_code == 200
    assert "RCARS" in response.text
