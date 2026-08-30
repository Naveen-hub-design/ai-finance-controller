"""Tests for the user API endpoints (Milestone 3.1)."""

import uuid

from flask.testing import FlaskClient

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User


def _auth(
    client: FlaskClient,
    email: str = "owner@example.com",
    password: str = "test-password-123",
    full_name: str = "Owner",
) -> tuple[dict, str]:
    created = client.post(
        "/api/users",
        json={"email": email, "full_name": full_name, "password": password},
    )
    assert created.status_code == 201, created.get_json()
    login = client.post("/api/users/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.get_json()
    body = login.get_json()
    return body["user"], body["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token_for(user_id) -> str:
    return create_access_token(identity=str(user_id))


def _create_user(client: FlaskClient, **overrides) -> tuple[dict, str]:
    payload = {
        "email": "user@example.com",
        "full_name": "Example User",
        "password": "correct-horse-battery-staple",
    }
    payload.update(overrides)
    return _auth(
        client,
        email=payload["email"],
        password=payload["password"],
        full_name=payload["full_name"],
    )


def test_create_user_returns_201_with_public_fields(client: FlaskClient) -> None:
    response = client.post(
        "/api/users",
        json={
            "email": "  User@Example.COM ",
            "full_name": "  Example User  ",
            "password": "super-secret",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["email"] == "user@example.com"  # trimmed + lowercased
    assert body["full_name"] == "Example User"
    uuid.UUID(body["id"])  # parses as a valid UUID
    assert isinstance(body["created_at"], str)
    assert isinstance(body["updated_at"], str)


def test_full_name_is_optional(client: FlaskClient) -> None:
    response = client.post(
        "/api/users", json={"email": "anon@example.com", "password": "supersecret"}
    )

    assert response.status_code == 201
    assert response.get_json()["full_name"] is None


def test_missing_email_returns_400(client: FlaskClient) -> None:
    response = client.post("/api/users", json={"full_name": "No Email"})

    assert response.status_code == 400
    assert "email" in response.get_json()["error"]


def test_blank_email_returns_400(client: FlaskClient) -> None:
    response = client.post("/api/users", json={"email": "   "})

    assert response.status_code == 400


def test_invalid_json_body_returns_400(client: FlaskClient) -> None:
    response = client.post(
        "/api/users",
        data="{not valid json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_missing_json_body_returns_400(client: FlaskClient) -> None:
    response = client.post("/api/users")

    assert response.status_code == 400


def test_duplicate_email_returns_409(client: FlaskClient) -> None:
    first = client.post(
        "/api/users",
        json={"email": "dupe@example.com", "full_name": "First", "password": "pw"},
    )
    second = client.post(
        "/api/users",
        json={
            "email": "  DUPE@example.com ",
            "full_name": "Second",
            "password": "pw2",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert "already exists" in second.get_json()["error"]


def test_get_existing_user_returns_200(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.get(f"/api/users/{user['id']}", headers=_headers(token))

    assert response.status_code == 200
    body = response.get_json()
    assert body == user


def test_get_nonexistent_user_returns_404(client: FlaskClient) -> None:
    target_id = str(uuid.uuid4())

    response = client.get(
        f"/api/users/{target_id}", headers=_headers(_token_for(target_id))
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


# ── PUT /api/users/<uuid:user_id> ────────────────────────────────────


def test_update_email_returns_200(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"email": "updated@example.com"},
        headers=_headers(token),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["email"] == "updated@example.com"
    assert body["id"] == user["id"]


def test_update_full_name_returns_200(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"full_name": "New Name"},
        headers=_headers(token),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["full_name"] == "New Name"
    assert body["email"] == user["email"]


def test_partial_update_preserves_untouched_fields(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"full_name": "Only Name Changed"},
        headers=_headers(token),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["email"] == user["email"]
    assert body["full_name"] == "Only Name Changed"
    assert body["id"] == user["id"]


def test_update_rejects_invalid_email(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"email": 123},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert "email" in response.get_json()["error"]


def test_update_rejects_blank_email(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"email": "   "},
        headers=_headers(token),
    )

    assert response.status_code == 400


def test_update_rejects_invalid_full_name_type(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client)

    response = client.put(
        f"/api/users/{user['id']}",
        json={"full_name": 123},
        headers=_headers(token),
    )

    assert response.status_code == 400
    assert "full_name" in response.get_json()["error"]


def test_update_nonexistent_user_returns_404(
    client: FlaskClient,
) -> None:
    target_id = str(uuid.uuid4())

    response = client.put(
        f"/api/users/{target_id}",
        json={"email": "nobody@example.com"},
        headers=_headers(_token_for(target_id)),
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_update_duplicate_email_returns_409(
    client: FlaskClient,
) -> None:
    _create_user(client, email="first@example.com")
    second, token = _create_user(client, email="second@example.com")

    response = client.put(
        f"/api/users/{second['id']}",
        json={"email": "first@example.com"},
        headers=_headers(token),
    )

    assert response.status_code == 409
    assert "already exists" in response.get_json()["error"]


# ── DELETE /api/users/<uuid:user_id> ─────────────────────────────────


def test_delete_user_returns_204(client: FlaskClient) -> None:
    user, token = _create_user(client)

    response = client.delete(f"/api/users/{user['id']}", headers=_headers(token))

    assert response.status_code == 204
    assert response.data == b""


def test_deleted_user_cannot_be_fetched(client: FlaskClient) -> None:
    user, token = _create_user(client)

    client.delete(f"/api/users/{user['id']}", headers=_headers(token))

    response = client.get(f"/api/users/{user['id']}", headers=_headers(token))
    assert response.status_code == 404


def test_delete_nonexistent_user_returns_404(
    client: FlaskClient,
) -> None:
    target_id = str(uuid.uuid4())

    response = client.delete(
        f"/api/users/{target_id}", headers=_headers(_token_for(target_id))
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_delete_user_cascades_to_owned_entities(
    client: FlaskClient,
) -> None:
    user, token = _create_user(client, email="cascade@example.com")

    account_resp = client.post(
        "/api/accounts",
        json={
            "user_id": user["id"],
            "name": "Test Account",
            "account_type": "bank",
            "currency": "INR",
            "current_balance": "5000",
        },
        headers=_headers(token),
    )
    assert account_resp.status_code == 201
    account_id = account_resp.get_json()["id"]

    client.delete(f"/api/users/{user['id']}", headers=_headers(token))

    account_response = client.get(
        f"/api/accounts/{account_id}", headers=_headers(token)
    )
    assert account_response.status_code == 404


# ── M7.1: password hashing & authentication foundation ───────────────


def test_registration_requires_password(client: FlaskClient) -> None:
    response = client.post(
        "/api/users",
        json={"email": "nopw@example.com", "full_name": "No Password"},
    )

    assert response.status_code == 400
    assert "password" in response.get_json()["error"]


def test_registration_rejects_empty_password(client: FlaskClient) -> None:
    response = client.post(
        "/api/users",
        json={"email": "emptypw@example.com", "password": ""},
    )

    assert response.status_code == 400
    assert "password" in response.get_json()["error"]


def test_registration_rejects_whitespace_password(client: FlaskClient) -> None:
    response = client.post(
        "/api/users",
        json={"email": "spacepw@example.com", "password": "   "},
    )

    assert response.status_code == 400
    assert "password" in response.get_json()["error"]


def test_registration_rejects_non_string_password(client: FlaskClient) -> None:
    response = client.post(
        "/api/users",
        json={"email": "nonstring@example.com", "password": 12345},
    )

    assert response.status_code == 400
    assert "password" in response.get_json()["error"]


def test_registration_stores_only_password_hash(client: FlaskClient) -> None:
    created, _ = _create_user(client, email="hash@example.com")

    user = db.session.get(User, uuid.UUID(created["id"]))
    assert user is not None
    assert user.password_hash is not None
    assert user.password_hash != "correct-horse-battery-staple"
    assert "correct-horse-battery-staple" not in user.password_hash


def test_check_password_succeeds_and_fails(client: FlaskClient) -> None:
    created, _ = _create_user(client, email="checkpw@example.com")
    user = db.session.get(User, uuid.UUID(created["id"]))

    assert user.check_password("correct-horse-battery-staple") is True
    assert user.check_password("wrong-password") is False
    assert user.check_password("") is False


def test_serialized_user_does_not_include_password(client: FlaskClient) -> None:
    created, token = _create_user(client, email="noleak@example.com")

    assert "password" not in created
    assert "password_hash" not in created

    fetched = client.get(
        f"/api/users/{created['id']}", headers=_headers(token)
    )
    assert "password" not in fetched.get_json()
    assert "password_hash" not in fetched.get_json()


def test_login_with_correct_credentials_succeeds(client: FlaskClient) -> None:
    created, _ = _create_user(client, email="login@example.com")

    response = client.post(
        "/api/users/login",
        json={"email": "LOGIN@example.com", "password": "correct-horse-battery-staple"},
    )

    assert response.status_code == 200
    body = response.get_json()
    user = body["user"]
    assert user["id"] == created["id"]
    assert user["email"] == "login@example.com"
    assert "password" not in body
    assert "password" not in user
    assert "access_token" in body
    assert body["access_token"]


def test_login_with_incorrect_password_fails(client: FlaskClient) -> None:
    _create_user(client, email="wrongpw@example.com")

    response = client.post(
        "/api/users/login",
        json={"email": "wrongpw@example.com", "password": "not-the-password"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "invalid email or password"
    assert "password is incorrect" not in response.get_json()["error"]
    assert "does not exist" not in response.get_json()["error"]
    assert "not found" not in response.get_json()["error"]


def test_login_with_unknown_email_fails(client: FlaskClient) -> None:
    response = client.post(
        "/api/users/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "invalid email or password"


def test_unknown_email_and_wrong_password_match_error(client: FlaskClient) -> None:
    _create_user(client, email="compare@example.com")

    unknown = client.post(
        "/api/users/login",
        json={"email": "does-not-exist@example.com", "password": "x"},
    )
    wrong = client.post(
        "/api/users/login",
        json={"email": "compare@example.com", "password": "x"},
    )

    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.get_json()["error"] == wrong.get_json()["error"]


def test_login_requires_credentials(client: FlaskClient) -> None:
    missing_email = client.post(
        "/api/users/login", json={"password": "pw"}
    )
    missing_password = client.post(
        "/api/users/login", json={"email": "x@example.com"}
    )

    assert missing_email.status_code == 401
    assert missing_password.status_code == 401
    assert missing_email.get_json()["error"] == missing_password.get_json()["error"]


def test_login_invalid_json_returns_400(client: FlaskClient) -> None:
    response = client.post(
        "/api/users/login",
        data="not json",
        content_type="application/json",
    )

    assert response.status_code == 400
