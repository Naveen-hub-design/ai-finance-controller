"""M7.3 tests: trusted authenticated identity.

These tests verify that the authenticated caller's identity is resolved
exclusively from the verified JWT via :func:`app.auth.get_current_user_id`,
and that client-supplied identifiers can never influence that resolution.
No ownership/authorization is implemented yet (M7.4+); the throwaway
protected endpoint below exists only to exercise the identity mechanism.
"""

import uuid as uuid_mod

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_jwt_extended import create_access_token, jwt_required

from app.auth import AuthenticationError, get_current_user_id


def _register_and_login(
    client: FlaskClient,
    email: str = "identity@example.com",
    password: str = "test-password-123",
) -> dict:
    created = client.post(
        "/api/users",
        json={"email": email, "full_name": "Identity User", "password": password},
    )
    assert created.status_code == 201, created.get_json()

    login = client.post(
        "/api/users/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.get_json()
    return login.get_json()


@pytest.fixture()
def identity_client(app: Flask) -> FlaskClient:
    """A test client exposing a single throwaway identity-resolution endpoint.

    The endpoint requires a verified JWT and resolves the caller via
    ``get_current_user_id``, mapping any invalid-identity failure to the safe,
    generic ``authorization required`` response that M7.4 routes will use.
    """

    @app.route("/api/test/identity", methods=["GET"])
    @jwt_required()
    def _identity() -> tuple[dict[str, object], int]:
        try:
            user_id = get_current_user_id()
        except AuthenticationError:
            return {"error": "authorization required"}, 401
        return {
            "identity": str(user_id),
            "is_uuid": isinstance(user_id, uuid_mod.UUID),
        }, 200

    return app.test_client()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Valid identity from a verified JWT ───────────────────────────────────


def test_valid_jwt_identity_matches_user(identity_client: FlaskClient) -> None:
    login = _register_and_login(identity_client)
    user_id = login["user"]["id"]
    token = login["access_token"]

    response = identity_client.get("/api/test/identity", headers=_auth_headers(token))

    assert response.status_code == 200
    body = response.get_json()
    assert body["identity"] == user_id
    assert body["is_uuid"] is True


def test_identity_resolves_to_uuid_type(identity_client: FlaskClient) -> None:
    login = _register_and_login(identity_client)

    response = identity_client.get(
        "/api/test/identity", headers=_auth_headers(login["access_token"])
    )

    assert response.status_code == 200
    # After being returned through JSON (a string), it must still parse to a
    # valid UUID, proving the helper normalized the identity into a UUID.
    uuid_mod.UUID(response.get_json()["identity"])


def test_identity_comes_from_jwt_not_client_input(
    identity_client: FlaskClient,
) -> None:
    # Two distinct users. The token belongs to user A only.
    login_a = _register_and_login(identity_client, email="user-a@example.com")
    login_b = _register_and_login(identity_client, email="user-b@example.com")
    user_b_id = login_b["user"]["id"]

    response = identity_client.get(
        f"/api/test/identity?client_supplied_user_id={user_b_id}",
        headers=_auth_headers(login_a["access_token"]),
    )

    # The helper must ignore the client-supplied user B id and return user A.
    assert response.status_code == 200
    assert response.get_json()["identity"] == login_a["user"]["id"]
    assert response.get_json()["identity"] != user_b_id


# ── Invalid / missing identity inside a verified JWT ─────────────────────


def test_invalid_jwt_identity_handled_safely(
    app: Flask, identity_client: FlaskClient
) -> None:
    with app.app_context():
        bad_token = create_access_token(identity="not-a-uuid")

    response = identity_client.get(
        "/api/test/identity", headers=_auth_headers(bad_token)
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "authorization required"


def test_missing_jwt_identity_handled_safely(
    app: Flask, identity_client: FlaskClient
) -> None:
    with app.app_context():
        empty_token = create_access_token(identity="")

    response = identity_client.get(
        "/api/test/identity", headers=_auth_headers(empty_token)
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "authorization required"


# ── No token / invalid token: M7.2 behavior unchanged ────────────────────


def test_missing_token_still_rejected(identity_client: FlaskClient) -> None:
    response = identity_client.get("/api/test/identity")

    assert response.status_code == 401
    assert response.get_json()["error"] == "authorization required"


def test_malformed_token_still_rejected(identity_client: FlaskClient) -> None:
    response = identity_client.get(
        "/api/test/identity", headers=_auth_headers("not-a-real-token")
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "authorization required"


def test_tampered_token_still_rejected(
    app: Flask, identity_client: FlaskClient
) -> None:
    with app.app_context():
        valid = create_access_token(identity=str(uuid_mod.uuid4()))
    # Corrupt a payload character: changing the signed payload bytes always
    # invalidates the HMAC signature, so verification must fail.
    header, payload, signature = valid.split(".")
    flip = "A" if payload[-1] != "A" else "B"
    tampered = f"{header}.{payload[:-1] + flip}.{signature}"

    response = identity_client.get(
        "/api/test/identity", headers=_auth_headers(tampered)
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "authorization required"
