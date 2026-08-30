"""Tests for the financial goal API endpoints."""

import uuid

from flask.testing import FlaskClient
from flask_jwt_extended import create_access_token


def _create_user(client: FlaskClient) -> tuple[dict, str]:
    created = client.post(
        "/api/users",
        json={
            "email": f"goal-owner-{uuid.uuid4().hex[:8]}@example.com",
            "password": "test-password-123",
        },
    )
    assert created.status_code == 201, created.get_json()
    login = client.post(
        "/api/users/login",
        json={
            "email": created.get_json()["email"],
            "password": "test-password-123",
        },
    )
    assert login.status_code == 200, login.get_json()
    body = login.get_json()
    return body["user"], body["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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


def _create_goal(
    client: FlaskClient, token: str, user_id: str, **overrides
) -> dict:
    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user_id, **overrides),
        headers=_headers(token),
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_create_goal_returns_201_with_all_fields(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(
            user["id"],
            name="  Emergency Fund  ",  # trimmed server-side
        ),
        headers=_headers(token),
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
    user, token = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["current_amount"]

    response = client.post(
        "/api/financial-goals", json=payload, headers=_headers(token)
    )

    assert response.status_code == 201
    assert response.get_json()["current_amount"] == "0.0000"


def test_target_date_is_optional(client: FlaskClient) -> None:
    user, token = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["target_date"]

    response = client.post(
        "/api/financial-goals", json=payload, headers=_headers(token)
    )

    assert response.status_code == 201
    assert response.get_json()["target_date"] is None


def test_status_defaults_to_active(client: FlaskClient) -> None:
    user, token = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["status"]

    response = client.post(
        "/api/financial-goals", json=payload, headers=_headers(token)
    )

    assert response.status_code == 201
    assert response.get_json()["status"] == "active"


def test_all_documented_statuses_are_accepted(client: FlaskClient) -> None:
    """Final contract: the four lifecycle states from the schema CHECK."""
    user, token = _create_user(client)

    for status in ("active", "completed", "paused", "cancelled"):
        response = client.post(
            "/api/financial-goals",
            json=_goal_payload(user["id"], status=status),
            headers=_headers(token),
        )
        assert response.status_code == 201, response.get_json()
        assert response.get_json()["status"] == status


def test_missing_user_id_returns_400(client: FlaskClient) -> None:
    """M7.4: user_id is optional in the create body; the JWT identity is the
    authoritative owner, so omitting it falls back to the caller's id."""
    user, token = _create_user(client)
    payload = _goal_payload(str(uuid.uuid4()))
    del payload["user_id"]

    response = client.post(
        "/api/financial-goals", json=payload, headers=_headers(token)
    )

    assert response.status_code == 201
    assert response.get_json()["user_id"] == user["id"]


def test_invalid_user_id_format_returns_400(client: FlaskClient) -> None:
    _, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload("not-a-uuid"),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "user_id must be a valid UUID"


def test_nonexistent_user_returns_404(client: FlaskClient, app) -> None:
    ghost_id = str(uuid.uuid4())
    with app.app_context():
        token = create_access_token(identity=ghost_id)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(ghost_id),
        headers=_headers(token),
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_missing_name_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["name"]

    response = client.post(
        "/api/financial-goals", json=payload, headers=_headers(token)
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "name is required"


def test_blank_name_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], name="   "),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "name is required"


def test_invalid_target_amount_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], target_amount="abc"),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "target_amount must be a valid number"
    )


def test_missing_target_amount_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)
    payload = _goal_payload(user["id"])
    del payload["target_amount"]

    response = client.post(
        "/api/financial-goals", json=payload, headers=_headers(token)
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "target_amount must be a valid number"
    )


def test_zero_target_amount_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], target_amount="0"),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "target_amount must be greater than zero"
    )


def test_negative_target_amount_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], target_amount="-500"),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "target_amount must be greater than zero"
    )


def test_invalid_current_amount_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], current_amount="abc"),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "current_amount must be a valid number"
    )


def test_negative_current_amount_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], current_amount="-1"),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "current_amount cannot be negative"
    )


def test_invalid_target_date_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], target_date="31/12/2026"),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "target_date must be YYYY-MM-DD"


def test_invalid_status_returns_400(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], status="archived"),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid status"


def test_current_amount_above_target_returns_400(client: FlaskClient) -> None:
    """Extra business rule: progress cannot exceed the goal."""
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], current_amount="10001"),
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "current_amount cannot exceed target_amount"
    )


def test_current_amount_equal_to_target_is_allowed(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)

    response = client.post(
        "/api/financial-goals",
        json=_goal_payload(user["id"], current_amount="10000"),
        headers=_headers(token),
    )

    assert response.status_code == 201
    assert response.get_json()["current_amount"] == "10000.0000"


def test_get_existing_goal_returns_200(client: FlaskClient) -> None:
    user, token = _create_user(client)
    created = _create_goal(client, token, user["id"])

    response = client.get(
        f"/api/financial-goals/{created['id']}", headers=_headers(token)
    )

    assert response.status_code == 200
    assert response.get_json() == created


def test_get_nonexistent_goal_returns_404(client: FlaskClient) -> None:
    _, token = _create_user(client)

    response = client.get(
        f"/api/financial-goals/{uuid.uuid4()}", headers=_headers(token)
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "financial goal not found"


# ── PUT /api/financial-goals/<uuid:goal_id> ──────────────────────────


def test_update_goal_returns_200(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={
            "name": "Retirement Savings",
            "target_amount": "200000",
            "current_amount": "50000",
            "target_date": "2030-12-31",
            "status": "paused",
        },
        headers=_headers(token),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "Retirement Savings"
    assert body["target_amount"] == "200000.0000"
    assert body["current_amount"] == "50000.0000"
    assert body["target_date"] == "2030-12-31"
    assert body["status"] == "paused"
    assert body["id"] == goal["id"]
    assert body["user_id"] == user["id"]


def test_update_goal_preserves_untouched_fields(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"name": "Updated Name"},
        headers=_headers(token),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "Updated Name"
    assert body["target_amount"] == goal["target_amount"]
    assert body["current_amount"] == goal["current_amount"]
    assert body["target_date"] == goal["target_date"]
    assert body["status"] == goal["status"]
    assert body["user_id"] == user["id"]


def test_update_goal_rejects_invalid_name(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"name": 123},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "name is required"


def test_update_goal_rejects_blank_name(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"name": "   "},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "name is required"


def test_update_goal_rejects_invalid_target_amount(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"target_amount": "abc"},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "target_amount must be a valid number"
    )


def test_update_goal_rejects_non_positive_target_amount(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    for value in ("0", "-500"):
        response = client.put(
            f"/api/financial-goals/{goal['id']}",
            json={"target_amount": value},
            headers=_headers(token),
        )
        assert response.status_code == 400
        assert (
            response.get_json()["error"]
            == "target_amount must be greater than zero"
        )


def test_update_goal_rejects_invalid_current_amount(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"current_amount": "abc"},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "current_amount must be a valid number"
    )


def test_update_goal_rejects_negative_current_amount(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"current_amount": "-1"},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"] == "current_amount cannot be negative"
    )


def test_update_goal_rejects_current_amount_above_target(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"current_amount": "999999"},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "current_amount cannot exceed target_amount"
    )


def test_update_goal_rejects_target_amount_below_current(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)
    goal = _create_goal(
        client, token, user["id"], current_amount="8000", target_amount="10000"
    )

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"target_amount": "5000"},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "current_amount cannot exceed target_amount"
    )


def test_update_goal_allows_current_amount_equal_to_target(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"], target_amount="10000")

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"current_amount": "10000"},
        headers=_headers(token),
    )

    assert response.status_code == 200
    assert response.get_json()["current_amount"] == "10000.0000"


def test_update_goal_rejects_invalid_target_date(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"target_date": "31/12/2026"},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "target_date must be YYYY-MM-DD"


def test_update_goal_rejects_invalid_status(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"status": "archived"},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid status"


def test_update_nonexistent_goal_returns_404(client: FlaskClient) -> None:
    _, token = _create_user(client)

    response = client.put(
        f"/api/financial-goals/{uuid.uuid4()}",
        json={"name": "No Goal"},
        headers=_headers(token),
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "financial goal not found"


def test_update_goal_rejects_invalid_json_body(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        data="{not valid json",
        content_type="application/json",
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "request body must be valid JSON"


def test_update_goal_does_not_change_user_id(client: FlaskClient) -> None:
    """M7.4 ownership protection forbids transferring a goal via the body."""
    user, token = _create_user(client)
    other_user, _ = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.put(
        f"/api/financial-goals/{goal['id']}",
        json={"user_id": other_user["id"], "name": "Hacked Goal"},
        headers=_headers(token),
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "forbidden"


# ── DELETE /api/financial-goals/<uuid:goal_id> ───────────────────────


def test_delete_goal_returns_204(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    response = client.delete(
        f"/api/financial-goals/{goal['id']}", headers=_headers(token)
    )

    assert response.status_code == 204
    assert response.data == b""


def test_deleted_goal_cannot_be_fetched(client: FlaskClient) -> None:
    user, token = _create_user(client)
    goal = _create_goal(client, token, user["id"])

    client.delete(f"/api/financial-goals/{goal['id']}", headers=_headers(token))

    response = client.get(
        f"/api/financial-goals/{goal['id']}", headers=_headers(token)
    )
    assert response.status_code == 404


def test_delete_nonexistent_goal_returns_404(client: FlaskClient) -> None:
    _, token = _create_user(client)

    response = client.delete(
        f"/api/financial-goals/{uuid.uuid4()}", headers=_headers(token)
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "financial goal not found"
