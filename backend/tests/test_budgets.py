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
