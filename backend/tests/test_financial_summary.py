"""Tests for the financial summary API."""

import uuid

from flask.testing import FlaskClient


def _create_user(client: FlaskClient, email: str = "summary@example.com") -> dict:
    response = client.post(
        "/api/users",
        json={
            "email": email,
            "name": "Summary User",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_account(
    client: FlaskClient,
    user_id: str,
    name: str,
    balance: str,
) -> dict:
    response = client.post(
        "/api/accounts",
        json={
            "user_id": user_id,
            "name": name,
            "account_type": "bank",
            "currency": "INR",
            "current_balance": balance,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_transaction(
    client: FlaskClient,
    account_id: str,
    amount: str,
    transaction_type: str,
    transaction_date: str = "2026-08-24",
) -> dict:
    response = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "amount": amount,
            "transaction_type": transaction_type,
            "transaction_date": transaction_date,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_empty_summary_returns_zero_values(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.get(f"/api/financial-summary/{user['id']}")

    assert response.status_code == 200
    assert response.get_json() == {
        "total_income": "0.0000",
        "total_expenses": "0.0000",
        "net_cash_flow": "0.0000",
        "transaction_count": 0,
        "income_transaction_count": 0,
        "expense_transaction_count": 0,
        "account_balance": "0.0000",
    }


def test_summary_calculates_income_and_expenses(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"], "Main Bank", "10000")

    _create_transaction(
        client,
        account["id"],
        "5000",
        "income",
    )
    _create_transaction(
        client,
        account["id"],
        "1250.50",
        "expense",
    )
    _create_transaction(
        client,
        account["id"],
        "750.25",
        "expense",
    )

    response = client.get(f"/api/financial-summary/{user['id']}")

    assert response.status_code == 200

    data = response.get_json()

    assert data["total_income"] == "5000.0000"
    assert data["total_expenses"] == "2000.7500"
    assert data["net_cash_flow"] == "2999.2500"
    assert data["transaction_count"] == 3
    assert data["income_transaction_count"] == 1
    assert data["expense_transaction_count"] == 2
    assert data["account_balance"] == "10000.0000"


def test_summary_includes_multiple_accounts(
    client: FlaskClient,
) -> None:
    user = _create_user(client)

    _create_account(
        client,
        user["id"],
        "Bank Account",
        "15000",
    )
    _create_account(
        client,
        user["id"],
        "Cash",
        "2500.50",
    )

    response = client.get(f"/api/financial-summary/{user['id']}")

    assert response.status_code == 200

    data = response.get_json()

    assert data["account_balance"] == "17500.5000"


def test_transfer_transactions_are_not_income_or_expense(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"], "Main Bank", "10000")

    _create_transaction(
        client,
        account["id"],
        "2000",
        "transfer",
    )

    response = client.get(f"/api/financial-summary/{user['id']}")

    assert response.status_code == 200

    data = response.get_json()

    assert data["transaction_count"] == 1
    assert data["income_transaction_count"] == 0
    assert data["expense_transaction_count"] == 0
    assert data["total_income"] == "0.0000"
    assert data["total_expenses"] == "0.0000"
    assert data["net_cash_flow"] == "0.0000"


def test_summary_handles_income_only(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"], "Main Bank", "0")

    _create_transaction(
        client,
        account["id"],
        "25000",
        "income",
    )

    response = client.get(f"/api/financial-summary/{user['id']}")

    assert response.status_code == 200

    data = response.get_json()

    assert data["total_income"] == "25000.0000"
    assert data["total_expenses"] == "0.0000"
    assert data["net_cash_flow"] == "25000.0000"


def test_summary_handles_expense_only(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"], "Main Bank", "5000")

    _create_transaction(
        client,
        account["id"],
        "1750",
        "expense",
    )

    response = client.get(f"/api/financial-summary/{user['id']}")

    assert response.status_code == 200

    data = response.get_json()

    assert data["total_income"] == "0.0000"
    assert data["total_expenses"] == "1750.0000"
    assert data["net_cash_flow"] == "-1750.0000"


def test_invalid_user_id_returns_404(client: FlaskClient) -> None:
    response = client.get("/api/financial-summary/not-a-uuid")

    assert response.status_code == 404


def test_nonexistent_user_returns_404(client: FlaskClient) -> None:
    response = client.get(f"/api/financial-summary/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_summary_is_isolated_by_user(client: FlaskClient) -> None:
    user_a = _create_user(client, email="user-a@example.com")
    user_b = _create_user(client, email="user-b@example.com")

    account_a = _create_account(client, user_a["id"], "A Bank", "10000")
    account_b = _create_account(client, user_b["id"], "B Bank", "90000")

    _create_transaction(client, account_a["id"], "3000", "income")
    _create_transaction(client, account_a["id"], "500", "expense")

    _create_transaction(client, account_b["id"], "50000", "income")
    _create_transaction(client, account_b["id"], "20000", "expense")

    summary_a = client.get(f"/api/financial-summary/{user_a['id']}")
    summary_b = client.get(f"/api/financial-summary/{user_b['id']}")

    assert summary_a.status_code == 200
    assert summary_b.status_code == 200

    data_a = summary_a.get_json()
    data_b = summary_b.get_json()

    assert data_a["total_income"] == "3000.0000"
    assert data_a["total_expenses"] == "500.0000"
    assert data_a["net_cash_flow"] == "2500.0000"
    assert data_a["account_balance"] == "10000.0000"
    assert data_a["transaction_count"] == 2
    assert data_a["income_transaction_count"] == 1
    assert data_a["expense_transaction_count"] == 1

    assert data_b["total_income"] == "50000.0000"
    assert data_b["total_expenses"] == "20000.0000"
    assert data_b["net_cash_flow"] == "30000.0000"
    assert data_b["account_balance"] == "90000.0000"
    assert data_b["transaction_count"] == 2
    assert data_b["income_transaction_count"] == 1
    assert data_b["expense_transaction_count"] == 1
