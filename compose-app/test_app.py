import pytest
import fakeredis
from unittest.mock import patch
from app import app



@pytest.fixture
def client():
    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    with patch("app.redis_client", fake):
        app.config["TESTING"] = True # nosem: python.flask.security.audit.hardcoded-config.avoid_hardcoded_config_TESTING
        with app.test_client() as client:
            yield client

def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}

def test_greet_with_name(client):
    response = client.get("/greet", query_string={"name": "Patrick"})
    assert response.status_code == 200
    assert "Patrick" in response.get_json()["greeting"]

def test_counter_increments(client):
    r1 = client.get("/counter")
    r2 = client.get("/counter")
    r3 = client.get("/counter")
    assert r1.get_json()["count"] == 1
    assert r2.get_json()["count"] == 2
    assert r3.get_json()["count"] == 3

