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


# ── PUT /api/users/<uuid:user_id> ────────────────────────────────────


def test_update_email_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"email": "updated@example.com"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["email"] == "updated@example.com"
    assert body["id"] == user["id"]


def test_update_full_name_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"full_name": "New Name"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["full_name"] == "New Name"
    assert body["email"] == user["email"]


def test_partial_update_preserves_untouched_fields(
    client: FlaskClient,
) -> None:
    user = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"full_name": "Only Name Changed"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["email"] == user["email"]
    assert body["full_name"] == "Only Name Changed"
    assert body["id"] == user["id"]


def test_update_rejects_invalid_email(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"email": 123},
    )

    assert response.status_code == 400
    assert "email" in response.get_json()["error"]


def test_update_rejects_blank_email(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"email": "   "},
    )

    assert response.status_code == 400


def test_update_rejects_invalid_full_name_type(
    client: FlaskClient,
) -> None:
    user = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"full_name": 123},
    )

    assert response.status_code == 400
    assert "full_name" in response.get_json()["error"]


def test_update_nonexistent_user_returns_404(
    client: FlaskClient,
) -> None:
    response = client.put(
        f"/api/users/{uuid.uuid4()}",
        json={"email": "nobody@example.com"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_update_duplicate_email_returns_409(
    client: FlaskClient,
) -> None:
    _create_user(client, email="first@example.com")
    second = _create_user(client, email="second@example.com")

    response = client.put(
        f"/api/users/{second['id']}",
        json={"email": "first@example.com"},
    )

    assert response.status_code == 409
    assert "already exists" in response.get_json()["error"]


# ── DELETE /api/users/<uuid:user_id> ─────────────────────────────────


def test_delete_user_returns_204(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.delete(f"/api/users/{user['id']}")

    assert response.status_code == 204
    assert response.data == b""


def test_deleted_user_cannot_be_fetched(client: FlaskClient) -> None:
    user = _create_user(client)

    client.delete(f"/api/users/{user['id']}")

    response = client.get(f"/api/users/{user['id']}")
    assert response.status_code == 404


def test_delete_nonexistent_user_returns_404(
    client: FlaskClient,
) -> None:
    response = client.delete(f"/api/users/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_delete_user_cascades_to_owned_entities(
    client: FlaskClient,
) -> None:
    user = _create_user(client, email="cascade@example.com")

    account_resp = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Test Account",
            "account_type": "bank",
            "currency": "INR",
            "current_balance": "5000",
        },
    )
    assert account_resp.status_code == 201
    account_id = account_resp.get_json()["id"]

    client.delete(f"/api/users/{user['id']}")

    account_response = client.get(f"/api/accounts/{account_id}")
    assert account_response.status_code == 404
