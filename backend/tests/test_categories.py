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


# ── PUT /api/categories/<uuid:category_id> ───────────────────────────


def test_update_category_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    response = client.put(
        f"/api/categories/{category['id']}",
        json={"name": "Food & Dining", "category_type": "income"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "Food & Dining"
    assert body["category_type"] == "income"
    assert body["id"] == category["id"]
    assert body["user_id"] == user["id"]


def test_update_category_preserves_untouched_fields(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    response = client.put(
        f"/api/categories/{category['id']}",
        json={"name": "Updated Name"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "Updated Name"
    assert body["category_type"] == "expense"
    assert body["user_id"] == user["id"]


def test_update_category_rejects_invalid_category_type(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    response = client.put(
        f"/api/categories/{category['id']}",
        json={"category_type": "invalid"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid category_type"


def test_update_category_rejects_blank_name(client: FlaskClient) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    response = client.put(
        f"/api/categories/{category['id']}",
        json={"name": "   "},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "name is required"


def test_update_category_rejects_invalid_name_type(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    response = client.put(
        f"/api/categories/{category['id']}",
        json={"name": 123},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "name is required"


def test_update_nonexistent_category_returns_404(
    client: FlaskClient,
) -> None:
    response = client.put(
        f"/api/categories/{uuid.uuid4()}",
        json={"name": "Ghost"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "category not found"


def test_update_category_rejects_invalid_json_body(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    response = client.put(
        f"/api/categories/{category['id']}",
        data="{not valid json",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "request body must be valid JSON"


# ── DELETE /api/categories/<uuid:category_id> ────────────────────────


def test_delete_category_returns_204(client: FlaskClient) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    response = client.delete(f"/api/categories/{category['id']}")

    assert response.status_code == 204
    assert response.data == b""


def test_deleted_category_cannot_be_fetched(client: FlaskClient) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    client.delete(f"/api/categories/{category['id']}")

    response = client.get(f"/api/categories/{category['id']}")
    assert response.status_code == 404


def test_delete_nonexistent_category_returns_404(
    client: FlaskClient,
) -> None:
    response = client.delete(f"/api/categories/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "category not found"


def test_delete_category_sets_transaction_category_id_to_null(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account_resp = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Bank",
            "account_type": "bank",
        },
    )
    assert account_resp.status_code == 201
    account = account_resp.get_json()

    category = _create_category(client, user["id"])

    tx_resp = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "category_id": category["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-27",
        },
    )
    assert tx_resp.status_code == 201
    tx = tx_resp.get_json()
    assert tx["category_id"] == category["id"]

    client.delete(f"/api/categories/{category['id']}")

    tx_response = client.get(f"/api/transactions/{tx['id']}")
    assert tx_response.status_code == 200
    assert tx_response.get_json()["category_id"] is None


def test_delete_category_sets_budget_category_id_to_null(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    budget_resp = client.post(
        "/api/budgets",
        json={
            "user_id": user["id"],
            "category_id": category["id"],
            "amount": "5000",
            "period": "monthly",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
        },
    )
    assert budget_resp.status_code == 201
    budget = budget_resp.get_json()
    assert budget["category_id"] == category["id"]

    client.delete(f"/api/categories/{category['id']}")

    budget_response = client.get(f"/api/budgets/{budget['id']}")
    assert budget_response.status_code == 200
    assert budget_response.get_json()["category_id"] is None
