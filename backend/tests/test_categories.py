"""Tests for the category API endpoints."""

import uuid

from flask.testing import FlaskClient


def _create_user(client: FlaskClient) -> dict:
    response = client.post(
        "/api/users",
        json={"email": "category-owner@example.com"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_category(client: FlaskClient, user_id: str, **overrides) -> dict:
    payload = {
        "user_id": user_id,
        "name": "Groceries",
        "category_type": "expense",
    }
    payload.update(overrides)
    response = client.post("/api/categories", json=payload)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_create_expense_category_returns_201(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/categories",
        json={
            "user_id": user["id"],
            "name": "Groceries",
            "category_type": "expense",
        },
    )

    assert response.status_code == 201
    body = response.get_json()

    assert body["user_id"] == user["id"]
    assert body["name"] == "Groceries"
    assert body["category_type"] == "expense"
    uuid.UUID(body["id"])  # parses as a valid UUID
    assert isinstance(body["created_at"], str)


def test_create_income_category_returns_201(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/categories",
        json={
            "user_id": user["id"],
            "name": "Salary",
            "category_type": "income",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["name"] == "Salary"
    assert body["category_type"] == "income"


def test_missing_user_id_returns_400(client: FlaskClient) -> None:
    response = client.post(
        "/api/categories",
        json={"name": "Groceries", "category_type": "expense"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "user_id must be a valid UUID"


def test_invalid_user_id_format_returns_400(client: FlaskClient) -> None:
    response = client.post(
        "/api/categories",
        json={
            "user_id": "not-a-uuid",
            "name": "Groceries",
            "category_type": "expense",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "user_id must be a valid UUID"


def test_nonexistent_user_id_returns_404(client: FlaskClient) -> None:
    response = client.post(
        "/api/categories",
        json={
            "user_id": str(uuid.uuid4()),
            "name": "Groceries",
            "category_type": "expense",
        },
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_missing_name_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/categories",
        json={"user_id": user["id"], "category_type": "expense"},
    )

    assert response.status_code == 400


def test_blank_name_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/categories",
        json={"user_id": user["id"], "name": "   ", "category_type": "expense"},
    )

    assert response.status_code == 400


def test_invalid_category_type_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/categories",
        json={
            "user_id": user["id"],
            "name": "Groceries",
            "category_type": "invalid",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid category_type"


def test_transfer_category_type_is_rejected(client: FlaskClient) -> None:
    """Transfers are account movements, not a category: DB CHECK excludes
    them, so the API must reject them too."""
    user = _create_user(client)

    for category_type in ("transfer", ""):
        response = client.post(
            "/api/categories",
            json={
                "user_id": user["id"],
                "name": "Internal Move",
                "category_type": category_type,
            },
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "invalid category_type"


def test_duplicate_category_names_are_allowed(client: FlaskClient) -> None:
    """The API enforces no uniqueness on (user_id, name): both posts succeed."""
    user = _create_user(client)

    first = _create_category(client, user["id"])
    second_response = client.post(
        "/api/categories",
        json={
            "user_id": user["id"],
            "name": "Groceries",
            "category_type": "expense",
        },
    )

    assert second_response.status_code == 201
    second = second_response.get_json()
    assert first["id"] != second["id"]
    assert second["name"] == first["name"]


def test_get_existing_category_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    created = _create_category(client, user["id"])

    response = client.get(f"/api/categories/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_get_nonexistent_category_returns_404(client: FlaskClient) -> None:
    response = client.get(f"/api/categories/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "category not found"
