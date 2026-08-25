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
