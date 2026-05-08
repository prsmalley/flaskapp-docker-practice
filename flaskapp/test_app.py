import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True # nosem: python.flask.security.audit.hardcoded-config.avoid_hardcoded_config_TESTING
    with app.test_client() as client:
        yield client

def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}

def test_greet_defaults_to_world(client):
    response = client.get("/greet")
    assert response.status_code == 200
    body = response.get_json()
    assert "world" in body["greeting"].lower()

def test_greet_with_name(client):
    response = client.get("/greet", query_string={"name": "Patrick"})
    assert response.status_code == 200
    assert "Patrick" in response.get_json()["greeting"]

def test_version_endpoint(client):
    response = client.get("/version")
    assert response.status_code == 200
    assert response.get_json() == {"version": "1.0.0"}
