"""Tests for the user API endpoints (Milestone 3.1)."""

import uuid

from flask.testing import FlaskClient


def _create_user(client: FlaskClient, **overrides) -> dict:
    payload = {"email": "user@example.com", "full_name": "Example User"}
    payload.update(overrides)
    response = client.post("/api/users", json=payload)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_create_user_returns_201_with_public_fields(client: FlaskClient) -> None:
    response = client.post(
        "/api/users",
        json={"email": "  User@Example.COM ", "full_name": "  Example User  "},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["email"] == "user@example.com"  # trimmed + lowercased
    assert body["full_name"] == "Example User"
    uuid.UUID(body["id"])  # parses as a valid UUID
    assert isinstance(body["created_at"], str)
    assert isinstance(body["updated_at"], str)


def test_full_name_is_optional(client: FlaskClient) -> None:
    response = client.post("/api/users", json={"email": "anon@example.com"})

    assert response.status_code == 201
    assert response.get_json()["full_name"] is None


def test_missing_email_returns_400(client: FlaskClient) -> None:
    response = client.post("/api/users", json={"full_name": "No Email"})

    assert response.status_code == 400
    assert "email" in response.get_json()["error"]


def test_blank_email_returns_400(client: FlaskClient) -> None:
    response = client.post("/api/users", json={"email": "   "})

    assert response.status_code == 400


def test_invalid_json_body_returns_400(client: FlaskClient) -> None:
    response = client.post(
        "/api/users",
        data="{not valid json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_missing_json_body_returns_400(client: FlaskClient) -> None:
    response = client.post("/api/users")

    assert response.status_code == 400


def test_duplicate_email_returns_409(client: FlaskClient) -> None:
    first = client.post(
        "/api/users",
        json={"email": "dupe@example.com", "full_name": "First"},
    )
    second = client.post(
        "/api/users",
        json={"email": "  DUPE@example.com ", "full_name": "Second"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert "already exists" in second.get_json()["error"]


def test_get_existing_user_returns_200(client: FlaskClient) -> None:
    created = _create_user(client)

    response = client.get(f"/api/users/{created['id']}")

    assert response.status_code == 200
    body = response.get_json()
    assert body == created


def test_get_nonexistent_user_returns_404(client: FlaskClient) -> None:
    response = client.get(f"/api/users/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"
