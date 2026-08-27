"""Tests for the account API endpoints."""

import uuid

from flask.testing import FlaskClient


def _create_user(client: FlaskClient) -> dict:
    response = client.post(
        "/api/users",
        json={"email": "account-owner@example.com", "full_name": "Account Owner"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_create_account_returns_201(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Demo Bank",
            "account_type": "bank",
            "currency": "INR",
            "current_balance": "50000",
        },
    )

    assert response.status_code == 201
    body = response.get_json()

    assert body["user_id"] == user["id"]
    assert body["name"] == "Demo Bank"
    assert body["account_type"] == "bank"
    assert body["currency"] == "INR"
    assert body["current_balance"] == "50000.0000"
    uuid.UUID(body["id"])


def test_create_account_defaults_currency_and_balance(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Cash",
            "account_type": "cash",
        },
    )

    assert response.status_code == 201
    body = response.get_json()

    assert body["currency"] == "INR"
    assert body["current_balance"] == "0.0000"


def test_create_account_rejects_invalid_user_id(client: FlaskClient) -> None:
    response = client.post(
        "/api/accounts",
        json={
            "user_id": "not-a-uuid",
            "name": "Demo Bank",
            "account_type": "bank",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "user_id must be a valid UUID"


def test_create_account_rejects_missing_user(client: FlaskClient) -> None:
    response = client.post(
        "/api/accounts",
        json={
            "user_id": str(uuid.uuid4()),
            "name": "Demo Bank",
            "account_type": "bank",
        },
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_create_account_rejects_invalid_account_type(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Demo",
            "account_type": "invalid",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid account_type"


def test_create_account_rejects_negative_balance(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Demo Bank",
            "account_type": "bank",
            "current_balance": "-100",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "current_balance cannot be negative"


def test_get_existing_account_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)

    created = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Savings",
            "account_type": "bank",
            "current_balance": "25000",
        },
    )

    assert created.status_code == 201
    account = created.get_json()

    response = client.get(f"/api/accounts/{account['id']}")

    assert response.status_code == 200
    assert response.get_json() == account


def test_get_nonexistent_account_returns_404(client: FlaskClient) -> None:
    response = client.get(f"/api/accounts/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "account not found"


# ── PUT /api/accounts/<uuid:account_id> ──────────────────────────────


def test_update_account_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    created = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Old Name",
            "account_type": "bank",
            "currency": "INR",
            "current_balance": "1000",
        },
    )
    assert created.status_code == 201
    account = created.get_json()

    response = client.put(
        f"/api/accounts/{account['id']}",
        json={"name": "New Name", "current_balance": "9999"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "New Name"
    assert body["current_balance"] == "9999.0000"
    assert body["id"] == account["id"]
    assert body["user_id"] == account["user_id"]


def test_update_account_preserves_untouched_fields(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    created = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Savings",
            "account_type": "bank",
            "currency": "INR",
            "current_balance": "50000",
        },
    )
    assert created.status_code == 201
    account = created.get_json()

    response = client.put(
        f"/api/accounts/{account['id']}",
        json={"name": "My Savings"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "My Savings"
    assert body["account_type"] == "bank"
    assert body["currency"] == "INR"
    assert body["current_balance"] == "50000.0000"
    assert body["user_id"] == account["user_id"]


def test_update_account_rejects_invalid_account_type(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    created = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Test",
            "account_type": "bank",
        },
    )
    assert created.status_code == 201
    account = created.get_json()

    response = client.put(
        f"/api/accounts/{account['id']}",
        json={"account_type": "invalid"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid account_type"


def test_update_account_rejects_negative_balance(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    created = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Test",
            "account_type": "bank",
        },
    )
    assert created.status_code == 201
    account = created.get_json()

    response = client.put(
        f"/api/accounts/{account['id']}",
        json={"current_balance": "-500"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "current_balance cannot be negative"


def test_update_nonexistent_account_returns_404(
    client: FlaskClient,
) -> None:
    response = client.put(
        f"/api/accounts/{uuid.uuid4()}",
        json={"name": "Ghost"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "account not found"


# ── DELETE /api/accounts/<uuid:account_id> ───────────────────────────


def test_delete_account_returns_204(client: FlaskClient) -> None:
    user = _create_user(client)
    created = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Doomed",
            "account_type": "cash",
        },
    )
    assert created.status_code == 201
    account = created.get_json()

    response = client.delete(f"/api/accounts/{account['id']}")

    assert response.status_code == 204
    assert response.data == b""


def test_deleted_account_cannot_be_fetched(client: FlaskClient) -> None:
    user = _create_user(client)
    created = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Ephemeral",
            "account_type": "bank",
        },
    )
    assert created.status_code == 201
    account = created.get_json()

    client.delete(f"/api/accounts/{account['id']}")

    response = client.get(f"/api/accounts/{account['id']}")
    assert response.status_code == 404


def test_delete_nonexistent_account_returns_404(
    client: FlaskClient,
) -> None:
    response = client.delete(f"/api/accounts/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "account not found"


def test_delete_account_cascades_to_transactions(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    created = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Cascade Test",
            "account_type": "bank",
        },
    )
    assert created.status_code == 201
    account = created.get_json()

    tx_resp = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "amount": "1000",
            "transaction_type": "income",
            "transaction_date": "2026-08-27",
        },
    )
    assert tx_resp.status_code == 201
    transaction_id = tx_resp.get_json()["id"]

    client.delete(f"/api/accounts/{account['id']}")

    assert client.get(f"/api/accounts/{account['id']}").status_code == 404
    assert client.get(f"/api/transactions/{transaction_id}").status_code == 404
