"""M7.2 tests: JWT authentication infrastructure.

These tests verify the JWT plumbing introduced in M7.2 -- token issuance on
login, identity claims, finite expiry, and safe handling of JWT failures.
Ownership authorization is NOT yet implemented (M7.3), so no ordinary
application endpoint is protected here. Instead, a small throwaway protected
endpoint is registered on the test app instance solely to exercise the JWT
verification/error-handler path without changing production API authorization.
"""

from datetime import timedelta

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_jwt_extended import (
    create_access_token,
    decode_token,
    get_jwt_identity,
    jwt_required,
)

from app.config import TestingConfig


def _register_and_login(
    client: FlaskClient,
    email: str = "jwt@example.com",
    password: str = "test-password-123",
) -> dict:
    created = client.post(
        "/api/users",
        json={"email": email, "full_name": "JWT User", "password": password},
    )
    assert created.status_code == 201, created.get_json()

    login = client.post(
        "/api/users/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.get_json()
    return login.get_json()


@pytest.fixture()
def protected_client(app: Flask) -> FlaskClient:
    """A test client with a single throwaway jwt_required endpoint.

    Exists only so M7.2 can verify JWT error handling without protecting any
    production API (ownership/authorization is M7.3+/M7.4).
    """

    @app.route("/api/test/protected", methods=["GET"])
    @jwt_required()
    def _protected() -> tuple[dict[str, object], int]:
        return {"ok": True, "identity": str(get_jwt_identity())}, 200

    return app.test_client()


# ── Token issuance on successful login ───────────────────────────────────


def test_login_returns_nonempty_access_token(client: FlaskClient) -> None:
    body = _register_and_login(client)

    assert "access_token" in body
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_login_response_keeps_serialized_user(client: FlaskClient) -> None:
    login = _register_and_login(client)

    user = login["user"]
    assert "id" in user
    assert "email" in user
    assert "password" not in user
    assert "password_hash" not in user


def test_access_token_decodes_with_configured_secret(
    app: Flask, client: FlaskClient
) -> None:
    body = _register_and_login(client)

    with app.app_context():
        payload = decode_token(body["access_token"])

    assert "sub" in payload


def test_token_identity_equals_user_uuid_string(
    app: Flask, client: FlaskClient
) -> None:
    login = _register_and_login(client)
    user_id = login["user"]["id"]

    with app.app_context():
        payload = decode_token(login["access_token"])

    assert payload["sub"] == user_id
    # identity is a plain string UUID, not an embedded object
    assert isinstance(payload["sub"], str)


def test_token_has_finite_expiration(app: Flask, client: FlaskClient) -> None:
    from datetime import datetime, timezone

    body = _register_and_login(client)

    with app.app_context():
        payload = decode_token(body["access_token"])

    exp = payload.get("exp")
    assert exp is not None
    assert exp > int(datetime.now(timezone.utc).timestamp())
    assert exp <= int(datetime.now(timezone.utc).timestamp()) + 3600


def test_token_contains_no_sensitive_data(
    app: Flask, client: FlaskClient
) -> None:
    body = _register_and_login(client)

    with app.app_context():
        payload = decode_token(body["access_token"])

    lowered = {k.lower() for k in payload}
    assert "password" not in lowered
    assert "password_hash" not in lowered
    assert "balance" not in lowered
    assert "transaction" not in lowered
    assert "secret" not in lowered
    assert "financial" not in lowered


# ── Login failures remain unchanged ──────────────────────────────────────


def test_login_wrong_password_still_401(client: FlaskClient) -> None:
    _register_and_login(client, email="wrongpw@example.com")

    response = client.post(
        "/api/users/login",
        json={"email": "wrongpw@example.com", "password": "nope"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "invalid email or password"


def test_login_unknown_email_still_401(client: FlaskClient) -> None:
    response = client.post(
        "/api/users/login",
        json={"email": "ghost@example.com", "password": "whatever"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "invalid email or password"


def test_unknown_email_and_wrong_password_same_error(
    client: FlaskClient,
) -> None:
    _register_and_login(client, email="compare@example.com")

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


# ── JWT error handling through the throwaway protected endpoint ──────────


def test_missing_jwt_handled_safely(protected_client: FlaskClient) -> None:
    response = protected_client.get("/api/test/protected")

    assert response.status_code == 401
    assert response.get_json()["error"] == "authorization required"


def test_malformed_jwt_handled_safely(protected_client: FlaskClient) -> None:
    response = protected_client.get(
        "/api/test/protected",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "authorization required"


def test_expired_jwt_handled_safely(
    app: Flask, protected_client: FlaskClient
) -> None:
    with app.app_context():
        expired = create_access_token(
            identity="00000000-0000-0000-0000-000000000001",
            expires_delta=timedelta(seconds=-30),
        )

    response = protected_client.get(
        "/api/test/protected",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "authorization token expired"


def test_tampered_jwt_rejected(
    app: Flask, protected_client: FlaskClient
) -> None:
    from uuid import uuid4

    with app.app_context():
        valid = create_access_token(identity=str(uuid4()))
    # Corrupt a payload character: changing the signed payload bytes always
    # invalidates the HMAC signature, so verification must fail.
    header, payload, signature = valid.split(".")
    flip = "A" if payload[-1] != "A" else "B"
    tampered = f"{header}.{payload[:-1] + flip}.{signature}"

    response = protected_client.get(
        "/api/test/protected",
        headers={"Authorization": f"Bearer {tampered}"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "authorization required"
    # The token itself must never be echoed back.
    assert tampered not in response.get_data(as_text=True)


def test_valid_token_passes_protected_endpoint(
    app: Flask, protected_client: FlaskClient
) -> None:
    from uuid import uuid4

    user_id = str(uuid4())
    with app.app_context():
        token = create_access_token(identity=user_id)

    response = protected_client.get(
        "/api/test/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert response.get_json()["identity"] == user_id


# ── Configuration ────────────────────────────────────────────────────────


def test_jwt_secret_from_testing_config(app: Flask) -> None:
    secret = app.config["JWT_SECRET_KEY"]
    assert isinstance(secret, str) and secret
    assert secret == TestingConfig.JWT_SECRET_KEY
    # Never a hard-coded insecure production secret.
    for forbidden in ("dev-secret", "secret", "jwt-secret", "dev-only-not-for-production"):
        assert secret != forbidden


def test_jwt_algorithm_is_hs256(app: Flask) -> None:
    assert app.config["JWT_ALGORITHM"] == "HS256"


def test_jwt_expiry_is_finite(app: Flask) -> None:
    expires = app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    assert isinstance(expires, timedelta)
    assert expires.total_seconds() > 0
