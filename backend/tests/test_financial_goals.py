"""Tests for the financial goal API endpoints."""

import uuid

from flask.testing import FlaskClient


def _create_user(client: FlaskClient) -> dict:
    response = client.post(
        "/api/users",
        json={"email": f"goal-owner-{uuid.uuid4().hex[:8]}@example.com"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _goal_payload(user_id: str, **overrides) -> dict:
    payload = {
        "user_id": user_id,
        "name": "Emergency Fund",
        "target_amount": "10000",
        "current_amount": "2500.50",
        "target_date": "2026-12-31",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def _create_goal(client: FlaskClient, user_id: str, **overrides) -> dict:
    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user_id, **overrides),
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_create_goal_returns_201_with_all_fields(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(
            user["id"],
            name="  Emergency Fund  ",  # trimmed server-side
        ),
    )

    assert response.status_code == 201
    body = response.get_json()

    uuid.UUID(body["id"])  # parses as a valid UUID
    assert body["user_id"] == user["id"]
    assert body["name"] == "Emergency Fund"
    # Amounts round-trip through NUMERIC(19,4): str(Decimal) yields scale-4.
    assert body["target_amount"] == "10000.0000"
    assert body["current_amount"] == "2500.5000"
    assert body["target_date"] == "2026-12-31"
    assert body["status"] == "active"
    assert isinstance(body["created_at"], str)
    assert isinstance(body["updated_at"], str)


def test_current_amount_defaults_to_zero(client: FlaskClient) -> None:
    user = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["current_amount"]

    response = client.post("/api/financial-goals", json=payload)

    assert response.status_code == 201
    assert response.get_json()["current_amount"] == "0.0000"


def test_target_date_is_optional(client: FlaskClient) -> None:
    user = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["target_date"]

    response = client.post("/api/financial-goals", json=payload)

    assert response.status_code == 201
    assert response.get_json()["target_date"] is None


def test_status_defaults_to_active(client: FlaskClient) -> None:
    user = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["status"]

    response = client.post("/api/financial-goals", json=payload)

    assert response.status_code == 201
    assert response.get_json()["status"] == "active"


def test_all_documented_statuses_are_accepted(client: FlaskClient) -> None:
    """Final contract: the four lifecycle states from the schema CHECK."""
    user = _create_user(client)

    for status in ("active", "completed", "paused", "cancelled"):
        response = client.post(
            "/api/financial-goals",
            json=_goal_payload(user["id"], status=status),
        )
        assert response.status_code == 201, response.get_json()
        assert response.get_json()["status"] == status


def test_missing_user_id_returns_400(client: FlaskClient) -> None:
    payload = _goal_payload(str(uuid.uuid4()))
    del payload["user_id"]

    response = client.post("/api/financial-goals", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "user_id must be a valid UUID"


def test_invalid_user_id_format_returns_400(client: FlaskClient) -> None:
    response = client.post(
        "/api/financial-goals",
        json=_goal_payload("not-a-uuid"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "user_id must be a valid UUID"


def test_nonexistent_user_returns_404(client: FlaskClient) -> None:
    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(str(uuid.uuid4())),
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_missing_name_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["name"]

    response = client.post("/api/financial-goals", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "name is required"


def test_blank_name_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], name="   "),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "name is required"


def test_invalid_target_amount_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], target_amount="abc"),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "target_amount must be a valid number"
    )


def test_missing_target_amount_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["target_amount"]

    response = client.post("/api/financial-goals", json=payload)

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "target_amount must be a valid number"
    )


def test_zero_target_amount_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], target_amount="0"),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "target_amount must be greater than zero"
    )


def test_negative_target_amount_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], target_amount="-500"),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "target_amount must be greater than zero"
    )


def test_invalid_current_amount_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], current_amount="abc"),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "current_amount must be a valid number"
    )


def test_negative_current_amount_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], current_amount="-1"),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "current_amount cannot be negative"
    )


def test_invalid_target_date_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], target_date="31/12/2026"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "target_date must be YYYY-MM-DD"


def test_invalid_status_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], status="archived"),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid status"


def test_current_amount_above_target_returns_400(client: FlaskClient) -> None:
    """Extra business rule: progress cannot exceed the goal."""
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], current_amount="10001"),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "current_amount cannot exceed target_amount"
    )


def test_current_amount_equal_to_target_is_allowed(
    client: FlaskClient,
) -> None:
    user = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], current_amount="10000"),
    )

    assert response.status_code == 201
    assert response.get_json()["current_amount"] == "10000.0000"


def test_get_existing_goal_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    created = _create_goal(client, user["id"])

    response = client.get(f"/api/financial-goals/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_get_nonexistent_goal_returns_404(client: FlaskClient) -> None:
    response = client.get(f"/api/financial-goals/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "financial goal not found"
