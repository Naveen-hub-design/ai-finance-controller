"""Tests for the budget API endpoints."""

import uuid

from flask.testing import FlaskClient


def _create_user(client: FlaskClient) -> dict:
    response = client.post(
        "/api/users",
        json={"email": f"budget-owner-{uuid.uuid4().hex[:8]}@example.com"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_category(client: FlaskClient, user_id: str) -> dict:
    response = client.post(
        "/api/categories",
        json={
            "user_id": user_id,
            "name": f"Cat-{uuid.uuid4().hex[:8]}",
            "category_type": "expense",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _budget_payload(user_id: str, **overrides) -> dict:
    payload = {
        "user_id": user_id,
        "amount": "25000",
        "period": "monthly",
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
    }
    payload.update(overrides)
    return payload


def _create_budget(client: FlaskClient, user_id: str, **overrides) -> dict:
    response = client.post(
        "/api/budgets",
        json=_budget_payload(user_id, **overrides),
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_create_monthly_budget_with_category_returns_201(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

    response = client.post(
        "/api/budgets",
        json=_budget_payload(
            user["id"],
            category_id=category["id"],
            amount="1500.75",
        ),
    )

    assert response.status_code == 201
    body = response.get_json()

    uuid.UUID(body["id"])  # parses as a valid UUID
    assert body["user_id"] == user["id"]
    assert body["category_id"] == category["id"]
    # Amounts round-trip through NUMERIC(19,4): str(Decimal) yields scale-4.
    assert body["amount"] == "1500.7500"
    assert body["period"] == "monthly"
    assert body["start_date"] == "2026-09-01"
    assert body["end_date"] == "2026-09-30"
    assert isinstance(body["created_at"], str)


def test_create_budget_without_category_returns_201(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post("/api/budgets", json=_budget_payload(user["id"]))

    assert response.status_code == 201
    assert response.get_json()["category_id"] is None


def test_create_budget_supports_all_documented_periods(
    client: FlaskClient,
) -> None:
    user = _create_user(client)

    for period in ("weekly", "monthly", "yearly"):
        response = client.post(
            "/api/budgets",
            json=_budget_payload(user["id"], period=period),
        )
        assert response.status_code == 201, response.get_json()
        assert response.get_json()["period"] == period


def test_missing_amount_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)
    payload = _budget_payload(user["id"])
    del payload["amount"]

    response = client.post("/api/budgets", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be a valid number"


def test_zero_amount_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], amount="0"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be greater than zero"


def test_negative_amount_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], amount="-100"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be greater than zero"


def test_invalid_amount_format_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], amount="abc"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be a valid number"


def test_missing_user_id_returns_400(client: FlaskClient) -> None:
    payload = _budget_payload(str(uuid.uuid4()))
    del payload["user_id"]

    response = client.post("/api/budgets", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "user_id must be a valid UUID"


def test_invalid_user_id_format_returns_400(client: FlaskClient) -> None:
    response = client.post(
        "/api/budgets",
        json=_budget_payload("not-a-uuid"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "user_id must be a valid UUID"


def test_nonexistent_user_returns_404(client: FlaskClient) -> None:
    response = client.post(
        "/api/budgets",
        json=_budget_payload(str(uuid.uuid4())),
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_invalid_category_id_format_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], category_id="not-a-uuid"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "category_id must be a valid UUID"


def test_nonexistent_category_returns_404(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], category_id=str(uuid.uuid4())),
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "category not found"


def test_category_owned_by_another_user_returns_400(client: FlaskClient) -> None:
    owner = _create_user(client)
    other_user = _create_user(client)
    foreign_category = _create_category(client, other_user["id"])

    response = client.post(
        "/api/budgets",
        json=_budget_payload(owner["id"], category_id=foreign_category["id"]),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "category does not belong to user"


def test_invalid_period_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], period="daily"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid period"


def test_invalid_start_date_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], start_date="01/09/2026"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "start_date must be YYYY-MM-DD"


def test_invalid_end_date_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], end_date="30-09-2026"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "end_date must be YYYY-MM-DD"


def test_end_date_before_start_date_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], end_date="2026-08-31"),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "end_date cannot be before start_date"
    )


def test_equal_start_and_end_dates_are_allowed(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/budgets",
        json=_budget_payload(user["id"], end_date="2026-09-01"),
    )

    assert response.status_code == 201


def test_get_existing_budget_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    created = _create_budget(client, user_id=user["id"])

    response = client.get(f"/api/budgets/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_get_nonexistent_budget_returns_404(client: FlaskClient) -> None:
    response = client.get(f"/api/budgets/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "budget not found"


# ── PUT /api/budgets/<uuid:budget_id> ────────────────────────────────


def test_update_budget_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={
            "amount": "50000",
            "period": "yearly",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["amount"] == "50000.0000"
    assert body["period"] == "yearly"
    assert body["start_date"] == "2026-01-01"
    assert body["end_date"] == "2026-12-31"
    assert body["id"] == budget["id"]
    assert body["user_id"] == user["id"]


def test_update_budget_preserves_untouched_fields(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"amount": "9999"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["amount"] == "9999.0000"
    assert body["period"] == budget["period"]
    assert body["start_date"] == budget["start_date"]
    assert body["end_date"] == budget["end_date"]
    assert body["category_id"] == budget["category_id"]
    assert body["user_id"] == user["id"]


def test_update_budget_rejects_invalid_amount(client: FlaskClient) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"amount": "abc"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be a valid number"


def test_update_budget_rejects_non_positive_amount(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    for value in ("0", "-100"):
        response = client.put(
            f"/api/budgets/{budget['id']}",
            json={"amount": value},
        )
        assert response.status_code == 400
        assert (
            response.get_json()["error"] == "amount must be greater than zero"
        )


def test_update_budget_rejects_invalid_period(client: FlaskClient) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"period": "daily"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid period"


def test_update_budget_rejects_invalid_start_date(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"start_date": "01/09/2026"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "start_date must be YYYY-MM-DD"


def test_update_budget_rejects_invalid_end_date(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"end_date": "30-09-2026"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "end_date must be YYYY-MM-DD"


def test_update_budget_rejects_end_date_before_start_date(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"end_date": "2026-08-01"},
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "end_date cannot be before start_date"
    )


def test_update_budget_allows_equal_start_and_end_dates(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"start_date": "2026-09-15", "end_date": "2026-09-15"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["start_date"] == "2026-09-15"
    assert body["end_date"] == "2026-09-15"


def test_update_nonexistent_budget_returns_404(
    client: FlaskClient,
) -> None:
    response = client.put(
        f"/api/budgets/{uuid.uuid4()}",
        json={"amount": "1000"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "budget not found"


def test_update_budget_rejects_invalid_json_body(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        data="{not valid json",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "request body must be valid JSON"


# ── Category ownership ───────────────────────────────────────────────


def test_update_budget_with_same_user_category_returns_200(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])
    category = _create_category(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"category_id": category["id"]},
    )

    assert response.status_code == 200
    assert response.get_json()["category_id"] == category["id"]


def test_update_budget_rejects_cross_user_category(
    client: FlaskClient,
) -> None:
    owner = _create_user(client)
    other_user = _create_user(client)
    foreign_category = _create_category(client, other_user["id"])

    budget = _create_budget(client, owner["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"category_id": foreign_category["id"]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "category does not belong to user"


def test_update_budget_rejects_nonexistent_category(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"category_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "category not found"


def test_update_budget_clears_category_to_null(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])
    budget = _create_budget(client, user["id"], category_id=category["id"])
    assert budget["category_id"] == category["id"]

    response = client.put(
        f"/api/budgets/{budget['id']}",
        json={"category_id": None},
    )

    assert response.status_code == 200
    assert response.get_json()["category_id"] is None


# ── DELETE /api/budgets/<uuid:budget_id> ─────────────────────────────


def test_delete_budget_returns_204(client: FlaskClient) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    response = client.delete(f"/api/budgets/{budget['id']}")

    assert response.status_code == 204
    assert response.data == b""


def test_deleted_budget_cannot_be_fetched(client: FlaskClient) -> None:
    user = _create_user(client)
    budget = _create_budget(client, user["id"])

    client.delete(f"/api/budgets/{budget['id']}")

    response = client.get(f"/api/budgets/{budget['id']}")
    assert response.status_code == 404


def test_delete_nonexistent_budget_returns_404(
    client: FlaskClient,
) -> None:
    response = client.delete(f"/api/budgets/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "budget not found"


def test_delete_budget_does_not_affect_category_or_transactions(
    client: FlaskClient,
) -> None:
    user = _create_user(client)
    category = _create_category(client, user["id"])

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

    tx_resp = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "category_id": category["id"],
            "amount": "500",
            "transaction_type": "expense",
            "transaction_date": "2026-08-27",
        },
    )
    assert tx_resp.status_code == 201
    tx = tx_resp.get_json()

    budget = _create_budget(client, user["id"], category_id=category["id"])

    client.delete(f"/api/budgets/{budget['id']}")

    cat_response = client.get(f"/api/categories/{category['id']}")
    assert cat_response.status_code == 200
    assert cat_response.get_json()["id"] == category["id"]

    tx_response = client.get(f"/api/transactions/{tx['id']}")
    assert tx_response.status_code == 200
    assert tx_response.get_json()["category_id"] == category["id"]
