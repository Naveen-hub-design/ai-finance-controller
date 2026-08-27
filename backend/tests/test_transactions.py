"""Tests for the transaction API endpoints."""

import uuid

from flask.testing import FlaskClient


def _create_user(client: FlaskClient) -> dict:
    response = client.post(
        "/api/users",
        json={"email": "transaction-owner@example.com"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_account(client: FlaskClient, user_id: str) -> dict:
    response = client.post(
        "/api/accounts",
        json={
            "user_id": user_id,
            "name": "Demo Bank",
            "account_type": "bank",
            "currency": "INR",
            "current_balance": "50000",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_category(client: FlaskClient, user_id: str) -> dict:
    response = client.post(
        "/api/categories",
        json={
            "user_id": user_id,
            "name": "Groceries",
            "category_type": "expense",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_create_transaction_returns_201(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "1250.50",
            "transaction_type": "expense",
            "description": "Groceries",
            "transaction_date": "2026-08-24",
        },
    )

    assert response.status_code == 201
    body = response.get_json()

    assert body["account_id"] == account["id"]
    assert body["category_id"] is None
    assert body["amount"] == "1250.5000"
    assert body["transaction_type"] == "expense"
    assert body["description"] == "Groceries"
    assert body["transaction_date"] == "2026-08-24"
    uuid.UUID(body["id"])


def test_create_transaction_with_category_returns_201(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])
    category = _create_category(client, user["id"])

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "category_id": category["id"],
            "amount": "500",
            "transaction_type": "expense",
            "description": "Vegetables",
            "transaction_date": "2026-08-24",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["category_id"] == category["id"]


def test_create_transaction_rejects_invalid_account_id(client: FlaskClient) -> None:
    response = client.post(
        "/api/transactions",
        json={
            "account_id": "not-a-uuid",
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "account_id must be a valid UUID"


def test_create_transaction_rejects_missing_account(client: FlaskClient) -> None:
    response = client.post(
        "/api/transactions",
        json={
            "account_id": str(uuid.uuid4()),
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "account not found"


def test_create_transaction_rejects_missing_category(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "category_id": str(uuid.uuid4()),
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "category not found"


def test_create_transaction_rejects_cross_user_category(
    client: FlaskClient,
) -> None:
    owner = _create_user(client)
    other_user_response = client.post(
        "/api/users",
        json={"email": "other@example.com"},
    )
    assert other_user_response.status_code == 201
    other_user = other_user_response.get_json()

    account = _create_account(client, owner["id"])
    foreign_category = _create_category(client, other_user["id"])

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "category_id": foreign_category["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "category does not belong to user"


def test_create_transaction_with_same_user_category_returns_201(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])
    category = _create_category(client, user["id"])

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "category_id": category["id"],
            "amount": "500",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["category_id"] == category["id"]


def test_create_transaction_rejects_invalid_transaction_type(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "100",
            "transaction_type": "invalid",
            "transaction_date": "2026-08-24",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid transaction_type"


def test_create_transaction_rejects_non_positive_amount(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "0",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be greater than zero"


def test_create_transaction_rejects_invalid_date(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "24-08-2026",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "transaction_date must be YYYY-MM-DD"


def test_get_existing_transaction_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "750",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )

    assert created.status_code == 201
    transaction = created.get_json()

    response = client.get(f"/api/transactions/{transaction['id']}")

    assert response.status_code == 200
    assert response.get_json() == transaction


def test_get_nonexistent_transaction_returns_404(client: FlaskClient) -> None:
    response = client.get(f"/api/transactions/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "transaction not found"


# ── PUT /api/transactions/<uuid:transaction_id> ──────────────────────


def test_update_transaction_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )
    assert created.status_code == 201
    tx = created.get_json()

    response = client.put(
        f"/api/transactions/{tx['id']}",
        json={"amount": "999.99", "description": "Updated"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["amount"] == "999.9900"
    assert body["description"] == "Updated"
    assert body["id"] == tx["id"]
    assert body["account_id"] == tx["account_id"]


def test_update_transaction_preserves_untouched_fields(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "500",
            "transaction_type": "income",
            "description": "Salary",
            "transaction_date": "2026-08-01",
        },
    )
    assert created.status_code == 201
    tx = created.get_json()

    response = client.put(
        f"/api/transactions/{tx['id']}",
        json={"amount": "750"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["amount"] == "750.0000"
    assert body["transaction_type"] == "income"
    assert body["description"] == "Salary"
    assert body["transaction_date"] == "2026-08-01"
    assert body["account_id"] == tx["account_id"]


def test_update_transaction_rejects_invalid_transaction_type(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )
    assert created.status_code == 201
    tx = created.get_json()

    response = client.put(
        f"/api/transactions/{tx['id']}",
        json={"transaction_type": "invalid"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid transaction_type"


def test_update_transaction_rejects_invalid_amount(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )
    assert created.status_code == 201
    tx = created.get_json()

    response = client.put(
        f"/api/transactions/{tx['id']}",
        json={"amount": "not-a-number"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be a valid number"


def test_update_transaction_rejects_invalid_date(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )
    assert created.status_code == 201
    tx = created.get_json()

    response = client.put(
        f"/api/transactions/{tx['id']}",
        json={"transaction_date": "24-08-2026"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "transaction_date must be YYYY-MM-DD"


def test_update_nonexistent_transaction_returns_404(
    client: FlaskClient,
) -> None:
    response = client.put(
        f"/api/transactions/{uuid.uuid4()}",
        json={"amount": "100"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "transaction not found"


def test_update_transaction_rejects_cross_user_category(
    client: FlaskClient,
) -> None:
    owner = _create_user(client)
    other_response = client.post(
        "/api/users",
        json={"email": "other-cat@example.com"},
    )
    assert other_response.status_code == 201
    other_user = other_response.get_json()

    account = _create_account(client, owner["id"])
    foreign_category = _create_category(client, other_user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )
    assert created.status_code == 201
    tx = created.get_json()

    response = client.put(
        f"/api/transactions/{tx['id']}",
        json={"category_id": foreign_category["id"]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "category does not belong to user"


def test_update_transaction_clears_category_to_null(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])
    category = _create_category(client, user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "category_id": category["id"],
            "amount": "200",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )
    assert created.status_code == 201
    tx = created.get_json()
    assert tx["category_id"] == category["id"]

    response = client.put(
        f"/api/transactions/{tx['id']}",
        json={"category_id": None},
    )

    assert response.status_code == 200
    assert response.get_json()["category_id"] is None


# ── DELETE /api/transactions/<uuid:transaction_id> ───────────────────


def test_delete_transaction_returns_204(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )
    assert created.status_code == 201
    tx = created.get_json()

    response = client.delete(f"/api/transactions/{tx['id']}")

    assert response.status_code == 204
    assert response.data == b""


def test_deleted_transaction_cannot_be_fetched(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    created = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "100",
            "transaction_type": "expense",
            "transaction_date": "2026-08-24",
        },
    )
    assert created.status_code == 201
    tx = created.get_json()

    client.delete(f"/api/transactions/{tx['id']}")

    response = client.get(f"/api/transactions/{tx['id']}")
    assert response.status_code == 404


def test_delete_nonexistent_transaction_returns_404(
    client: FlaskClient,
) -> None:
    response = client.delete(f"/api/transactions/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "transaction not found"
