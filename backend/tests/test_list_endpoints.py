"""Tests for the M6.1 user-scoped list / query endpoints.

These endpoints live under ``/api/users/<uuid:user_id>/<resource>`` and must
only ever return rows belonging to the requested user.
"""

import uuid

from flask.testing import FlaskClient

from app.extensions import db
from app.models import Category


def _auth(
    client: FlaskClient,
    email: str = "list@example.com",
    password: str = "test-password-123",
) -> tuple[dict, str]:
    created = client.post(
        "/api/users",
        json={"email": email, "full_name": "List User", "password": password},
    )
    assert created.status_code == 201, created.get_json()
    login = client.post("/api/users/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.get_json()
    body = login.get_json()
    return body["user"], body["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token_for(client: FlaskClient, identity) -> str:
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        return create_access_token(identity=str(identity))


def _create_user(client: FlaskClient, email: str | None = None) -> tuple[dict, str]:
    return _auth(
        client,
        email=email or f"list-owner-{uuid.uuid4().hex[:8]}@example.com",
    )


def _create_account(
    client: FlaskClient,
    user_id: str,
    name: str | None = None,
    *,
    token: str,
) -> dict:
    response = client.post(
        "/api/accounts",
        headers=_headers(token),
        json={
            "user_id": user_id,
            "name": name or f"Bank-{uuid.uuid4().hex[:8]}",
            "account_type": "bank",
            "currency": "INR",
            "current_balance": "50000",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_category(
    client: FlaskClient,
    user_id: str,
    name: str | None = None,
    *,
    token: str,
) -> dict:
    response = client.post(
        "/api/categories",
        headers=_headers(token),
        json={
            "user_id": user_id,
            "name": name or f"Cat-{uuid.uuid4().hex[:8]}",
            "category_type": "expense",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_transaction(
    client: FlaskClient,
    account_id: str,
    amount: str,
    transaction_type: str,
    transaction_date: str,
    category_id: str | None = None,
    description: str | None = None,
    *,
    token: str,
) -> dict:
    payload = {
        "account_id": account_id,
        "amount": amount,
        "transaction_type": transaction_type,
        "transaction_date": transaction_date,
    }
    if category_id is not None:
        payload["category_id"] = category_id
    if description is not None:
        payload["description"] = description
    response = client.post("/api/transactions", headers=_headers(token), json=payload)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


# ── Accounts ─────────────────────────────────────────────────────────


def test_accounts_list_returns_created_accounts(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], name="Savings", token=token)

    response = client.get(
        f"/api/users/{user['id']}/accounts", headers=_headers(token)
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user_id"] == user["id"]
    assert len(body["accounts"]) == 1
    assert body["accounts"][0] == account


def test_accounts_list_empty(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.get(
        f"/api/users/{user['id']}/accounts", headers=_headers(token)
    )

    assert response.status_code == 200
    assert response.get_json() == {"user_id": user["id"], "accounts": []}


def test_accounts_list_user_isolation(client: FlaskClient) -> None:
    user_a, token_a = _create_user(client)
    user_b, token_b = _create_user(client)
    _create_account(client, user_a["id"], name="A's Bank", token=token_a)

    a = client.get(
        f"/api/users/{user_a['id']}/accounts", headers=_headers(token_a)
    ).get_json()["accounts"]
    b = client.get(
        f"/api/users/{user_b['id']}/accounts", headers=_headers(token_b)
    ).get_json()["accounts"]

    assert len(a) == 1
    assert len(b) == 0


def test_accounts_list_unknown_user_404(client: FlaskClient) -> None:
    rid = uuid.uuid4()
    response = client.get(
        f"/api/users/{rid}/accounts", headers=_headers(_token_for(client, rid))
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


# ── Categories ───────────────────────────────────────────────────────


def test_categories_list_returns_created_categories(client: FlaskClient) -> None:
    user, token = _create_user(client)
    category = _create_category(client, user["id"], name="Groceries", token=token)

    response = client.get(
        f"/api/users/{user['id']}/categories", headers=_headers(token)
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user_id"] == user["id"]
    assert len(body["categories"]) == 1
    assert body["categories"][0] == category


def test_categories_list_empty(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.get(
        f"/api/users/{user['id']}/categories", headers=_headers(token)
    )

    assert response.status_code == 200
    assert response.get_json() == {"user_id": user["id"], "categories": []}


def test_categories_list_user_isolation(client: FlaskClient) -> None:
    user_a, token_a = _create_user(client)
    user_b, token_b = _create_user(client)
    _create_category(client, user_a["id"], name="A's Category", token=token_a)

    a = client.get(
        f"/api/users/{user_a['id']}/categories", headers=_headers(token_a)
    ).get_json()["categories"]
    b = client.get(
        f"/api/users/{user_b['id']}/categories", headers=_headers(token_b)
    ).get_json()["categories"]

    assert len(a) == 1
    assert len(b) == 0


def test_categories_list_does_not_include_global_null_user_categories(
    client: FlaskClient,
    app,
) -> None:
    user, token = _create_user(client)
    _create_category(client, user["id"], name="Owned", token=token)

    # The category create API requires a user_id, so a global (NULL user)
    # category can only be created directly through the ORM.
    with app.app_context():
        db.session.add(
            Category(name="Global Category", category_type="expense")
        )
        db.session.commit()

    response = client.get(
        f"/api/users/{user['id']}/categories", headers=_headers(token)
    )

    assert response.status_code == 200
    categories = response.get_json()["categories"]
    assert all(c["name"] != "Global Category" for c in categories)
    assert all(c["user_id"] == user["id"] for c in categories)


def test_categories_list_unknown_user_404(client: FlaskClient) -> None:
    rid = uuid.uuid4()
    response = client.get(
        f"/api/users/{rid}/categories", headers=_headers(_token_for(client, rid))
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


# ── Financial Goals ──────────────────────────────────────────────────


def _create_goal(
    client: FlaskClient,
    user_id: str,
    name: str | None = None,
    *,
    token: str,
) -> dict:
    response = client.post(
        "/api/financial-goals",
        headers=_headers(token),
        json={
            "user_id": user_id,
            "name": name or f"Goal-{uuid.uuid4().hex[:8]}",
            "target_amount": "10000",
            "current_amount": "1000",
            "target_date": "2026-12-31",
            "status": "active",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_financial_goals_list_returns_created_goals(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, user["id"], name="Emergency Fund", token=token)

    response = client.get(
        f"/api/users/{user['id']}/financial-goals", headers=_headers(token)
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user_id"] == user["id"]
    assert len(body["financial_goals"]) == 1
    assert body["financial_goals"][0] == goal


def test_financial_goals_list_empty(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.get(
        f"/api/users/{user['id']}/financial-goals", headers=_headers(token)
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "user_id": user["id"],
        "financial_goals": [],
    }


def test_financial_goals_list_user_isolation(client: FlaskClient) -> None:
    user_a, token_a = _create_user(client)
    user_b, token_b = _create_user(client)
    _create_goal(client, user_a["id"], name="A's Goal", token=token_a)

    a = client.get(
        f"/api/users/{user_a['id']}/financial-goals", headers=_headers(token_a)
    ).get_json()["financial_goals"]
    b = client.get(
        f"/api/users/{user_b['id']}/financial-goals", headers=_headers(token_b)
    ).get_json()["financial_goals"]

    assert len(a) == 1
    assert len(b) == 0


def test_financial_goals_list_unknown_user_404(client: FlaskClient) -> None:
    rid = uuid.uuid4()
    response = client.get(
        f"/api/users/{rid}/financial-goals",
        headers=_headers(_token_for(client, rid)),
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


# ── Transactions ─────────────────────────────────────────────────────


def test_transactions_list_returns_created_transactions(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    tx = _create_transaction(
        client, account["id"], "100", "expense", "2026-08-01", token=token
    )

    response = client.get(
        f"/api/users/{user['id']}/transactions", headers=_headers(token)
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user_id"] == user["id"]
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert body["transactions"][0] == tx


def test_transactions_list_user_isolation(client: FlaskClient) -> None:
    user_a, token_a = _create_user(client)
    user_b, token_b = _create_user(client)
    account_a = _create_account(client, user_a["id"], token=token_a)
    account_b = _create_account(client, user_b["id"], token=token_b)
    _create_transaction(
        client, account_a["id"], "100", "expense", "2026-08-01", token=token_a
    )
    _create_transaction(
        client, account_b["id"], "200", "expense", "2026-08-02", token=token_b
    )

    body_a = client.get(
        f"/api/users/{user_a['id']}/transactions", headers=_headers(token_a)
    ).get_json()
    body_b = client.get(
        f"/api/users/{user_b['id']}/transactions", headers=_headers(token_b)
    ).get_json()

    assert body_a["total"] == 1
    assert body_b["total"] == 1
    assert body_a["transactions"][0]["account_id"] == account_a["id"]
    assert body_b["transactions"][0]["account_id"] == account_b["id"]


def test_transactions_list_deterministic_ordering(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    # Distinct dates exercise the primary deterministic sort key
    # (transaction_date DESC) without relying on the created_at/id tie-breaks.
    tx1 = _create_transaction(
        client, account["id"], "100", "expense", "2026-08-01", token=token
    )
    tx2 = _create_transaction(
        client, account["id"], "50", "expense", "2026-08-03", token=token
    )
    tx3 = _create_transaction(
        client, account["id"], "999", "expense", "2026-08-05", token=token
    )

    body = client.get(
        f"/api/users/{user['id']}/transactions", headers=_headers(token)
    ).get_json()
    ids = [t["id"] for t in body["transactions"]]

    assert ids == [tx3["id"], tx2["id"], tx1["id"]]


def test_transactions_list_same_date_ties_sorted_by_id(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    tx1 = _create_transaction(
        client, account["id"], "100", "expense", "2026-08-01", token=token
    )
    tx2 = _create_transaction(
        client, account["id"], "999", "expense", "2026-08-01", token=token
    )

    body = client.get(
        f"/api/users/{user['id']}/transactions", headers=_headers(token)
    ).get_json()
    ids = [t["id"] for t in body["transactions"]]

    # Same date and (likely) same created_at second resolve via id ASC, so the
    # two rows must appear in sorted id order (not insertion order).
    assert ids == sorted([tx1["id"], tx2["id"]])


def test_transactions_list_pagination_and_total(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    for i in range(14):
        _create_transaction(
            client, account["id"], str(i + 1), "expense", "2026-08-01", token=token
        )

    page1 = client.get(
        f"/api/users/{user['id']}/transactions?page=1&page_size=5",
        headers=_headers(token),
    ).get_json()
    page3 = client.get(
        f"/api/users/{user['id']}/transactions?page=3&page_size=5",
        headers=_headers(token),
    ).get_json()

    assert page1["total"] == 14
    assert len(page1["transactions"]) == 5
    assert page1["page"] == 1
    assert page1["page_size"] == 5
    assert page3["total"] == 14
    assert len(page3["transactions"]) == 4  # 14 = 5 + 5 + 4


def test_transactions_list_type_filter(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(client, account["id"], "100", "income", "2026-08-01", token=token)
    _create_transaction(client, account["id"], "200", "expense", "2026-08-01", token=token)

    body = client.get(
        f"/api/users/{user['id']}/transactions?transaction_type=expense",
        headers=_headers(token),
    ).get_json()

    assert body["total"] == 1
    assert body["transactions"][0]["transaction_type"] == "expense"
    assert body["transactions"][0]["amount"] == "200.0000"


def test_transactions_list_invalid_type(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.get(
        f"/api/users/{user['id']}/transactions?transaction_type=bogus",
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid transaction_type"


def test_transactions_list_date_from(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(client, account["id"], "100", "expense", "2026-08-01", token=token)
    _create_transaction(client, account["id"], "200", "expense", "2026-08-10", token=token)

    body = client.get(
        f"/api/users/{user['id']}/transactions?date_from=2026-08-05",
        headers=_headers(token),
    ).get_json()

    assert body["total"] == 1
    assert body["transactions"][0]["transaction_date"] == "2026-08-10"


def test_transactions_list_date_to(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(client, account["id"], "100", "expense", "2026-08-01", token=token)
    _create_transaction(client, account["id"], "200", "expense", "2026-08-10", token=token)

    body = client.get(
        f"/api/users/{user['id']}/transactions?date_to=2026-08-05",
        headers=_headers(token),
    ).get_json()

    assert body["total"] == 1
    assert body["transactions"][0]["transaction_date"] == "2026-08-01"


def test_transactions_list_inclusive_date_boundaries(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(client, account["id"], "100", "expense", "2026-08-01", token=token)
    _create_transaction(client, account["id"], "200", "expense", "2026-08-10", token=token)
    _create_transaction(client, account["id"], "300", "expense", "2026-08-31", token=token)

    body = client.get(
        f"/api/users/{user['id']}/transactions"
        "?date_from=2026-08-10&date_to=2026-08-10",
        headers=_headers(token),
    ).get_json()

    assert body["total"] == 1
    assert body["transactions"][0]["transaction_date"] == "2026-08-10"


def test_transactions_list_invalid_date_format(client: FlaskClient) -> None:
    user, token = _create_user(client)

    from_response = client.get(
        f"/api/users/{user['id']}/transactions?date_from=10/08/2026",
        headers=_headers(token),
    )
    to_response = client.get(
        f"/api/users/{user['id']}/transactions?date_to=10/08/2026",
        headers=_headers(token),
    )

    assert from_response.status_code == 400
    assert from_response.get_json()["error"] == "date_from must be YYYY-MM-DD"
    assert to_response.status_code == 400
    assert to_response.get_json()["error"] == "date_to must be YYYY-MM-DD"


def test_transactions_list_date_from_after_date_to(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.get(
        f"/api/users/{user['id']}/transactions"
        "?date_from=2026-08-10&date_to=2026-08-01",
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "date_from cannot be after date_to"


def test_transactions_list_search(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(
        client, account["id"], "100", "expense", "2026-08-01",
        description="Grocery shopping", token=token,
    )
    _create_transaction(
        client, account["id"], "200", "expense", "2026-08-01",
        description="Coffee", token=token,
    )

    body = client.get(
        f"/api/users/{user['id']}/transactions?search=grocery",
        headers=_headers(token),
    ).get_json()

    assert body["total"] == 1
    assert body["transactions"][0]["description"] == "Grocery shopping"


def test_transactions_list_search_case_insensitive(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(
        client, account["id"], "100", "expense", "2026-08-01",
        description="GROCERY Store", token=token,
    )

    body = client.get(
        f"/api/users/{user['id']}/transactions?search=grocerY",
        headers=_headers(token),
    ).get_json()

    assert body["total"] == 1


def test_transactions_list_search_no_matches(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(
        client, account["id"], "100", "expense", "2026-08-01",
        description="Coffee", token=token,
    )

    body = client.get(
        f"/api/users/{user['id']}/transactions?search=zzz",
        headers=_headers(token),
    ).get_json()

    assert body["total"] == 0
    assert body["transactions"] == []


def test_transactions_list_blank_search_is_ignored(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(client, account["id"], "100", "expense", "2026-08-01", token=token)

    body = client.get(
        f"/api/users/{user['id']}/transactions?search=   ",
        headers=_headers(token),
    ).get_json()

    assert body["total"] == 1


def test_transactions_list_null_description_search_ok(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(client, account["id"], "100", "expense", "2026-08-01", token=token)

    response = client.get(
        f"/api/users/{user['id']}/transactions?search=x", headers=_headers(token)
    )

    assert response.status_code == 200
    assert response.get_json()["total"] == 0


def test_transactions_list_page_validation(client: FlaskClient) -> None:
    user, token = _create_user(client)

    for value in ("0", "-1", "abc"):
        response = client.get(
            f"/api/users/{user['id']}/transactions?page={value}",
            headers=_headers(token),
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "page must be a positive integer"


def test_transactions_list_page_size_validation(client: FlaskClient) -> None:
    user, token = _create_user(client)

    for value in ("0", "101", "abc"):
        response = client.get(
            f"/api/users/{user['id']}/transactions?page_size={value}",
            headers=_headers(token),
        )
        assert response.status_code == 400
        assert (
            response.get_json()["error"]
            == "page_size must be an integer between 1 and 100"
        )


def test_transactions_list_page_size_maximum_100(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    for i in range(101):
        _create_transaction(
            client, account["id"], "1", "expense", "2026-08-01", token=token
        )

    response = client.get(
        f"/api/users/{user['id']}/transactions?page_size=100",
        headers=_headers(token),
    )

    assert response.status_code == 200
    assert response.get_json()["total"] == 101
    assert len(response.get_json()["transactions"]) == 100


def test_transactions_list_unknown_user_404(client: FlaskClient) -> None:
    rid = uuid.uuid4()
    response = client.get(
        f"/api/users/{rid}/transactions", headers=_headers(_token_for(client, rid))
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


# ── Budgets ──────────────────────────────────────────────────────────


def _create_budget(
    client: FlaskClient,
    user_id: str,
    amount: str,
    start_date: str,
    end_date: str,
    category_id: str | None = None,
    *,
    token: str,
) -> dict:
    payload = {
        "user_id": user_id,
        "amount": amount,
        "period": "monthly",
        "start_date": start_date,
        "end_date": end_date,
    }
    if category_id is not None:
        payload["category_id"] = category_id
    response = client.post(
        "/api/budgets", headers=_headers(token), json=payload
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_budgets_list_returns_created_budgets(client: FlaskClient) -> None:
    user, token = _create_user(client)
    budget = _create_budget(
        client, user["id"], "10000", "2026-08-01", "2026-08-31", token=token
    )

    response = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user_id"] == user["id"]
    assert len(body["budgets"]) == 1
    assert body["budgets"][0]["id"] == budget["id"]
    assert body["budgets"][0]["amount"] == "10000.0000"
    assert body["budgets"][0]["spent"] == "0.0000"
    assert body["budgets"][0]["remaining"] == "10000.0000"
    assert body["budgets"][0]["progress_percent"] == "0.00"


def test_budgets_list_empty(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    )

    assert response.status_code == 200
    assert response.get_json() == {"user_id": user["id"], "budgets": []}


def test_budgets_list_user_isolation(client: FlaskClient) -> None:
    user_a, token_a = _create_user(client)
    user_b, token_b = _create_user(client)
    _create_budget(
        client, user_a["id"], "5000", "2026-08-01", "2026-08-31", token=token_a
    )

    a = client.get(
        f"/api/users/{user_a['id']}/budgets", headers=_headers(token_a)
    ).get_json()["budgets"]
    b = client.get(
        f"/api/users/{user_b['id']}/budgets", headers=_headers(token_b)
    ).get_json()["budgets"]

    assert len(a) == 1
    assert len(b) == 0


def test_budgets_list_unknown_user_404(client: FlaskClient) -> None:
    rid = uuid.uuid4()
    response = client.get(
        f"/api/users/{rid}/budgets", headers=_headers(_token_for(client, rid))
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_budget_counts_in_period_expense(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(
        client, account["id"], "2500", "expense", "2026-08-15", token=token
    )
    _create_budget(client, user["id"], "10000", "2026-08-01", "2026-08-31", token=token)

    budget = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    ).get_json()["budgets"][0]

    assert budget["spent"] == "2500.0000"
    assert budget["remaining"] == "7500.0000"
    assert budget["progress_percent"] == "25.00"


def test_budget_ignores_out_of_period_expense(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(
        client, account["id"], "9999", "expense", "2026-07-31", token=token
    )
    _create_transaction(
        client, account["id"], "9999", "expense", "2026-09-01", token=token
    )
    _create_budget(client, user["id"], "10000", "2026-08-01", "2026-08-31", token=token)

    budget = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    ).get_json()["budgets"][0]

    assert budget["spent"] == "0.0000"
    assert budget["remaining"] == "10000.0000"


def test_budget_excludes_income(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(
        client, account["id"], "5000", "income", "2026-08-15", token=token
    )
    _create_budget(client, user["id"], "10000", "2026-08-01", "2026-08-31", token=token)

    budget = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    ).get_json()["budgets"][0]

    assert budget["spent"] == "0.0000"


def test_budget_excludes_transfer(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(
        client, account["id"], "5000", "transfer", "2026-08-15", token=token
    )
    _create_budget(client, user["id"], "10000", "2026-08-01", "2026-08-31", token=token)

    budget = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    ).get_json()["budgets"][0]

    assert budget["spent"] == "0.0000"


def test_category_specific_budget_counts_only_that_category(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    groceries = _create_category(client, user["id"], name="Groceries", token=token)
    dining = _create_category(client, user["id"], name="Dining", token=token)
    _create_transaction(
        client, account["id"], "3000", "expense", "2026-08-15",
        category_id=groceries["id"], token=token,
    )
    _create_transaction(
        client, account["id"], "7000", "expense", "2026-08-16",
        category_id=dining["id"], token=token,
    )
    _create_budget(
        client, user["id"], "5000", "2026-08-01", "2026-08-31",
        category_id=groceries["id"], token=token,
    )

    budget = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    ).get_json()["budgets"][0]

    assert budget["spent"] == "3000.0000"
    assert budget["remaining"] == "2000.0000"
    assert budget["progress_percent"] == "60.00"


def test_category_less_budget_counts_all_expenses(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    groceries = _create_category(client, user["id"], name="Groceries", token=token)
    dining = _create_category(client, user["id"], name="Dining", token=token)
    _create_transaction(
        client, account["id"], "3000", "expense", "2026-08-15",
        category_id=groceries["id"], token=token,
    )
    _create_transaction(
        client, account["id"], "7000", "expense", "2026-08-16",
        category_id=dining["id"], token=token,
    )
    _create_budget(client, user["id"], "10000", "2026-08-01", "2026-08-31", token=token)

    budget = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    ).get_json()["budgets"][0]

    assert budget["spent"] == "10000.0000"
    assert budget["remaining"] == "0.0000"
    assert budget["progress_percent"] == "100.00"


def test_budget_overspending_negative_remaining(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(
        client, account["id"], "12000", "expense", "2026-08-15", token=token
    )
    _create_budget(client, user["id"], "10000", "2026-08-01", "2026-08-31", token=token)

    budget = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    ).get_json()["budgets"][0]

    assert budget["spent"] == "12000.0000"
    assert budget["remaining"] == "-2000.0000"
    assert budget["progress_percent"] == "120.00"


def test_multiple_budgets_receive_independent_spending(client: FlaskClient) -> None:
    user, token = _create_user(client)
    account = _create_account(client, user["id"], token=token)
    _create_transaction(
        client, account["id"], "800", "expense", "2026-08-10", token=token
    )
    _create_budget(client, user["id"], "1000", "2026-08-01", "2026-08-31", token=token)
    _create_budget(client, user["id"], "500", "2026-09-01", "2026-09-30", token=token)

    budgets = client.get(
        f"/api/users/{user['id']}/budgets", headers=_headers(token)
    ).get_json()["budgets"]

    assert len(budgets) == 2
    assert budgets[0]["spent"] == "800.0000"
    assert budgets[0]["remaining"] == "200.0000"
    assert budgets[1]["spent"] == "0.0000"
    assert budgets[1]["remaining"] == "500.0000"