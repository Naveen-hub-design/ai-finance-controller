"""Tests for the financial facts API endpoint."""

import uuid

from flask.testing import FlaskClient


def _create_user(client: FlaskClient, email: str = "facts@example.com") -> dict:
    response = client.post(
        "/api/users",
        json={
            "email": email,
            "name": "Facts User",
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
    category_id: str | None = None,
) -> dict:
    payload = {
        "account_id": account_id,
        "amount": amount,
        "transaction_type": transaction_type,
        "transaction_date": "2026-08-25",
    }

    if category_id is not None:
        payload["category_id"] = category_id

    response = client.post(
        "/api/transactions",
        json=payload,
    )

    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _get_facts(client: FlaskClient, user_id: str) -> dict:
    response = client.get(f"/api/users/{user_id}/financial-facts")
    assert response.status_code == 200
    return response.get_json()


def test_empty_user_returns_zero_facts(client: FlaskClient) -> None:
    user = _create_user(client)

    data = _get_facts(client, user["id"])

    assert data["total_income"] == "0.0000"
    assert data["total_expenses"] == "0.0000"
    assert data["net_cash_flow"] == "0.0000"
    assert data["transaction_count"] == 0
    assert data["income_transaction_count"] == 0
    assert data["expense_transaction_count"] == 0
    assert data["account_balance"] == "0.0000"
    assert data["spending_by_category"] == []
    assert data["budgets"] == []
    assert data["financial_goals"] == []


def test_returns_income_expenses_and_balance(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"], "Main Bank", "50000")

    _create_transaction(client, account["id"], "5000", "income")
    _create_transaction(client, account["id"], "1250", "expense")

    data = _get_facts(client, user["id"])

    assert data["total_income"] == "5000.0000"
    assert data["total_expenses"] == "1250.0000"
    assert data["net_cash_flow"] == "3750.0000"
    assert data["account_balance"] == "50000.0000"


def test_returns_transaction_counts(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"], "Main Bank", "10000")

    _create_transaction(client, account["id"], "3000", "income")
    _create_transaction(client, account["id"], "1000", "expense")
    _create_transaction(client, account["id"], "500", "expense")

    data = _get_facts(client, user["id"])

    assert data["transaction_count"] == 3
    assert data["income_transaction_count"] == 1
    assert data["expense_transaction_count"] == 2


def test_returns_spending_by_category(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"], "Main Bank", "20000")

    groceries_response = client.post(
        "/api/categories",
        json={
            "user_id": user["id"],
            "name": "Groceries",
            "category_type": "expense",
        },
    )
    assert groceries_response.status_code == 201
    groceries = groceries_response.get_json()

    food_response = client.post(
        "/api/categories",
        json={
            "user_id": user["id"],
            "name": "Food",
            "category_type": "expense",
        },
    )
    assert food_response.status_code == 201
    food = food_response.get_json()

    _create_transaction(client, account["id"], "3000", "expense", groceries["id"])
    _create_transaction(client, account["id"], "1500", "expense", groceries["id"])
    _create_transaction(client, account["id"], "2000", "expense", food["id"])

    data = _get_facts(client, user["id"])

    assert data["spending_by_category"] == [
        {"category": "Groceries", "amount": "4500.0000"},
        {"category": "Food", "amount": "2000.0000"},
    ]


def test_returns_budgets(client: FlaskClient) -> None:
    user = _create_user(client)

    category_response = client.post(
        "/api/categories",
        json={
            "user_id": user["id"],
            "name": "Groceries",
            "category_type": "expense",
        },
    )
    assert category_response.status_code == 201
    category = category_response.get_json()

    budget_response = client.post(
        "/api/budgets",
        json={
            "user_id": user["id"],
            "category_id": category["id"],
            "amount": "10000",
            "period": "monthly",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
        },
    )
    assert budget_response.status_code == 201

    data = _get_facts(client, user["id"])

    assert len(data["budgets"]) == 1
    assert data["budgets"][0]["category_id"] == category["id"]
    assert data["budgets"][0]["amount"] == "10000.0000"
    assert data["budgets"][0]["period"] == "monthly"


def test_returns_financial_goals_with_progress(
    client: FlaskClient,
) -> None:
    user = _create_user(client)

    goal_response = client.post(
        "/api/financial-goals",
        json={
            "user_id": user["id"],
            "name": "Emergency Fund",
            "target_amount": "100000",
            "current_amount": "25000",
        },
    )
    assert goal_response.status_code == 201

    data = _get_facts(client, user["id"])

    assert len(data["financial_goals"]) == 1

    goal = data["financial_goals"][0]

    assert goal["name"] == "Emergency Fund"
    assert goal["target_amount"] == "100000.0000"
    assert goal["current_amount"] == "25000.0000"
    assert goal["progress_percent"] == "25.00"
    assert goal["status"] == "active"


def test_nonexistent_user_returns_404(client: FlaskClient) -> None:
    response = client.get(f"/api/users/{uuid.uuid4()}/financial-facts")

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_invalid_user_id_returns_404(client: FlaskClient) -> None:
    response = client.get("/api/users/not-a-uuid/financial-facts")

    assert response.status_code == 404


def test_facts_are_isolated_by_user(client: FlaskClient) -> None:
    user_a = _create_user(client, email="user-a-facts@example.com")
    user_b = _create_user(client, email="user-b-facts@example.com")

    account_a = _create_account(client, user_a["id"], "A Bank", "10000")
    account_b = _create_account(client, user_b["id"], "B Bank", "90000")

    _create_transaction(client, account_a["id"], "5000", "income")
    _create_transaction(client, account_a["id"], "500", "expense")

    _create_transaction(client, account_b["id"], "50000", "income")
    _create_transaction(client, account_b["id"], "20000", "expense")

    data_a = _get_facts(client, user_a["id"])
    data_b = _get_facts(client, user_b["id"])

    assert data_a["total_income"] == "5000.0000"
    assert data_a["total_expenses"] == "500.0000"
    assert data_a["net_cash_flow"] == "4500.0000"
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
