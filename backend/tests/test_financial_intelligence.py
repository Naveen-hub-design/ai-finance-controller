"""Tests for the financial intelligence service."""

import uuid
from decimal import Decimal

from flask.testing import FlaskClient

from app.extensions import db
from app.services.financial_intelligence import build_financial_facts
from app.models import Budget, Category, FinancialGoal


def _create_user(
    client: FlaskClient, email: str = "intelligence@example.com"
) -> tuple[dict, str]:
    created = client.post(
        "/api/users",
        json={
            "email": email,
            "name": "Intelligence User",
            "password": "test-password-123",
        },
    )
    assert created.status_code == 201, created.get_json()
    login = client.post(
        "/api/users/login",
        json={"email": email, "password": "test-password-123"},
    )
    assert login.status_code == 200, login.get_json()
    body = login.get_json()
    return body["user"], body["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_account(
    client: FlaskClient,
    token: str,
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
        headers=_headers(token),
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_transaction(
    client: FlaskClient,
    token: str,
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
        headers=_headers(token),
    )

    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_empty_user_returns_zero_facts(client: FlaskClient) -> None:
    user, _ = _create_user(client)

    facts = build_financial_facts(user["id"])

    assert facts["total_income"] == "0.0000"
    assert facts["total_expenses"] == "0.0000"
    assert facts["net_cash_flow"] == "0.0000"
    assert facts["transaction_count"] == 0
    assert facts["income_transaction_count"] == 0
    assert facts["expense_transaction_count"] == 0
    assert facts["account_balance"] == "0.0000"
    assert facts["spending_by_category"] == []
    assert facts["budgets"] == []
    assert facts["financial_goals"] == []


def test_calculates_income_expenses_and_balance(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)

    account = _create_account(
        client,
        token,
        user["id"],
        "Main Bank",
        "50000",
    )

    _create_transaction(
        client,
        token,
        account["id"],
        "5000",
        "income",
    )

    _create_transaction(
        client,
        token,
        account["id"],
        "1250",
        "expense",
    )

    facts = build_financial_facts(user["id"])

    assert facts["total_income"] == "5000.0000"
    assert facts["total_expenses"] == "1250.0000"
    assert facts["net_cash_flow"] == "3750.0000"
    assert facts["transaction_count"] == 2
    assert facts["income_transaction_count"] == 1
    assert facts["expense_transaction_count"] == 1
    assert facts["account_balance"] == "50000.0000"


def test_calculates_spending_by_category(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)

    account = _create_account(
        client,
        token,
        user["id"],
        "Main Bank",
        "20000",
    )

    groceries_response = client.post(
        "/api/categories",
        json={
            "user_id": user["id"],
            "name": "Groceries",
            "category_type": "expense",
        },
        headers=_headers(token),
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
        headers=_headers(token),
    )

    assert food_response.status_code == 201

    food = food_response.get_json()

    _create_transaction(
        client,
        token,
        account["id"],
        "3000",
        "expense",
        groceries["id"],
    )

    _create_transaction(
        client,
        token,
        account["id"],
        "1500",
        "expense",
        groceries["id"],
    )

    _create_transaction(
        client,
        token,
        account["id"],
        "2000",
        "expense",
        food["id"],
    )

    facts = build_financial_facts(user["id"])

    assert facts["spending_by_category"] == [
        {
            "category": "Groceries",
            "amount": "4500.0000",
        },
        {
            "category": "Food",
            "amount": "2000.0000",
        },
    ]


def test_includes_user_budgets(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)

    category_response = client.post(
        "/api/categories",
        json={
            "user_id": user["id"],
            "name": "Groceries",
            "category_type": "expense",
        },
        headers=_headers(token),
    )

    assert category_response.status_code == 201

    category = category_response.get_json()

    response = client.post(
        "/api/budgets",
        json={
            "user_id": user["id"],
            "category_id": category["id"],
            "amount": "10000",
            "period": "monthly",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
        },
        headers=_headers(token),
    )

    assert response.status_code == 201

    facts = build_financial_facts(user["id"])

    assert len(facts["budgets"]) == 1
    assert facts["budgets"][0]["category_id"] == category["id"]
    assert facts["budgets"][0]["amount"] == "10000.0000"
    assert facts["budgets"][0]["period"] == "monthly"


def test_calculates_financial_goal_progress(
    client: FlaskClient,
    app,
) -> None:
    user, _ = _create_user(client)

    with app.app_context():
        # Direct ORM construction requires typed UUIDs (the HTTP layer
        # normally performs this conversion); strings are not coerced.
        goal = FinancialGoal(
            user_id=uuid.UUID(user["id"]),
            name="Emergency Fund",
            target_amount=Decimal("100000"),
            current_amount=Decimal("25000"),
            target_date=None,
            status="active",
        )

        db.session.add(goal)
        db.session.commit()

    facts = build_financial_facts(user["id"])

    assert len(facts["financial_goals"]) == 1

    goal_fact = facts["financial_goals"][0]

    assert goal_fact["name"] == "Emergency Fund"
    assert goal_fact["target_amount"] == "100000.0000"
    assert goal_fact["current_amount"] == "25000.0000"
    assert goal_fact["progress_percent"] == "25.00"
    assert goal_fact["status"] == "active"


def test_financial_facts_are_isolated_by_user(
    client: FlaskClient,
) -> None:
    user_one, token_one = _create_user(client)

    user_two_response = client.post(
        "/api/users",
        json={
            "email": "other@example.com",
            "name": "Other User",
            "password": "test-password-123",
        },
    )

    assert user_two_response.status_code == 201

    login_two = client.post(
        "/api/users/login",
        json={"email": "other@example.com", "password": "test-password-123"},
    )
    assert login_two.status_code == 200, login_two.get_json()
    user_two_body = login_two.get_json()
    user_two = user_two_body["user"]
    token_two = user_two_body["access_token"]

    account_one = _create_account(
        client,
        token_one,
        user_one["id"],
        "User One Bank",
        "10000",
    )

    account_two = _create_account(
        client,
        token_two,
        user_two["id"],
        "User Two Bank",
        "90000",
    )

    _create_transaction(
        client,
        token_one,
        account_one["id"],
        "5000",
        "income",
    )

    _create_transaction(
        client,
        token_two,
        account_two["id"],
        "50000",
        "income",
    )

    facts_one = build_financial_facts(user_one["id"])
    facts_two = build_financial_facts(user_two["id"])

    assert facts_one["total_income"] == "5000.0000"
    assert facts_one["account_balance"] == "10000.0000"

    assert facts_two["total_income"] == "50000.0000"
    assert facts_two["account_balance"] == "90000.0000"