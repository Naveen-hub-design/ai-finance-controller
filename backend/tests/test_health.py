"""Tests for the /api/health endpoint."""

from flask.testing import FlaskClient


def test_health_returns_http_200(client: FlaskClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200


def test_health_returns_expected_payload(client: FlaskClient) -> None:
    response = client.get("/api/health")

    assert response.get_json() == {
        "status": "healthy",
        "service": "finance-controller-api",
    }
