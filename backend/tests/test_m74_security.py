"""M7.4 tests: authenticated API protection & ownership authorization.

These tests prove that authorization uses the verified JWT identity
(:func:`app.auth.get_current_user_id`) and NEVER trusts client-supplied
URL/body user ids. Every cross-user denial must be 403 (authenticated but
wrong owner); every missing/malformed/tampered token must stay 401 (M7.2);
own-resource access must keep working unchanged.
"""

import uuid

import pytest
from flask import Flask
from flask.testing import FlaskClient


PASSWORD = "test-password-123"
A_EMAIL = "owner-a@example.com"
B_EMAIL = "owner-b@example.com"


def _register_login(client: FlaskClient, email: str) -> tuple[str, str]:
    created = client.post(
        "/api/users",
        json={"email": email, "full_name": "Test User", "password": PASSWORD},
    )
    assert created.status_code == 201, created.get_json()
    login = client.post("/api/users/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.get_json()
    body = login.get_json()
    return body["user"]["id"], body["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_account(client, token: str, user_id: str, name: str = "A Account") -> dict:
    r = client.post(
        "/api/accounts",
        json={
            "user_id": user_id,
            "name": name,
            "account_type": "bank",
            "currency": "INR",
            "current_balance": "1000",
        },
        headers=_headers(token),
    )
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _create_transaction(client, token: str, account_id: str) -> str:
    r = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "amount": "500",
            "transaction_type": "income",
            "transaction_date": "2026-08-01",
        },
        headers=_headers(token),
    )
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


@pytest.fixture()
def auth_pair(client: FlaskClient) -> tuple[str, str, str, str]:
    """Return (A_id, A_token, B_id, B_token) for two distinct users."""
    a_id, a_token = _register_login(client, A_EMAIL)
    b_id, b_token = _register_login(client, B_EMAIL)
    return a_id, a_token, b_id, b_token


# ── User routes (M7.4) ───────────────────────────────────────────────────


def test_owner_can_access_own_user_route(client, auth_pair):
    a_id, a_token, _, _ = auth_pair
    r = client.get(f"/api/users/{a_id}", headers=_headers(a_token))
    assert r.status_code == 200
    assert r.get_json()["id"] == a_id


def test_owner_cannot_access_another_users_user_route(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.get(f"/api/users/{a_id}", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_update_another_users_user(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.put(
        f"/api/users/{a_id}", json={"full_name": "Hacked"}, headers=_headers(b_token)
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_delete_another_users_user(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.delete(f"/api/users/{a_id}", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


# ── Missing / invalid JWT: M7.2 behavior unchanged ───────────────────────


def test_protected_route_without_jwt_is_401(client, auth_pair):
    a_id, _, _, _ = auth_pair
    for method in ("get", "put", "delete"):
        r = getattr(client, method)(f"/api/users/{a_id}")
        assert r.status_code == 401
        assert r.get_json()["error"] == "authorization required"


def test_protected_route_with_malformed_jwt_is_401(client, auth_pair):
    a_id, _, _, _ = auth_pair
    r = client.get(f"/api/users/{a_id}", headers=_headers("not-a-real-token"))
    assert r.status_code == 401
    assert r.get_json()["error"] == "authorization required"


def test_protected_route_with_tampered_jwt_is_401(client, auth_pair):
    a_id, a_token, _, _ = auth_pair
    header, payload, signature = a_token.split(".")
    flip = "A" if payload[-1] != "A" else "B"
    tampered = f"{header}.{payload[:-1] + flip}.{signature}"
    r = client.get(f"/api/users/{a_id}", headers=_headers(tampered))
    assert r.status_code == 401
    assert r.get_json()["error"] == "authorization required"


def test_health_endpoint_remains_public(client: FlaskClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "healthy"


# ── Account routes ───────────────────────────────────────────────────────


def test_owner_can_access_own_accounts(client, auth_pair):
    a_id, a_token, _, _ = auth_pair
    r = client.get(f"/api/users/{a_id}/accounts", headers=_headers(a_token))
    assert r.status_code == 200
    assert "accounts" in r.get_json()


def test_owner_cannot_access_another_users_accounts_list(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.get(f"/api/users/{a_id}/accounts", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_access_another_users_account_detail(client, auth_pair):
    a_id, a_token, _, b_token = auth_pair
    account = _create_account(client, a_token, a_id)

    r = client.get(f"/api/accounts/{account['id']}", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_update_another_users_account(client, auth_pair):
    a_id, a_token, _, b_token = auth_pair
    account = _create_account(client, a_token, a_id)

    r = client.put(
        f"/api/accounts/{account['id']}",
        json={"name": "Stolen"},
        headers=_headers(b_token),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_delete_another_users_account(client, auth_pair):
    a_id, a_token, _, b_token = auth_pair
    account = _create_account(client, a_token, a_id)

    r = client.delete(f"/api/accounts/{account['id']}", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_client_supplied_user_id_cannot_create_account_for_victim(
    client, auth_pair
):
    _, a_token, b_id, _ = auth_pair
    r = client.post(
        "/api/accounts",
        json={
            "user_id": b_id,
            "name": "Attempted",
            "account_type": "bank",
            "currency": "INR",
        },
        headers=_headers(a_token),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_update_payload_cannot_transfer_ownership(client, auth_pair):
    a_id, a_token, b_id, _ = auth_pair
    account = _create_account(client, a_token, a_id)

    # A tries to hand the account to B via body user_id.
    r = client.put(
        f"/api/accounts/{account['id']}",
        json={"user_id": b_id},
        headers=_headers(a_token),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


# ── Transaction routes (bare + list) ─────────────────────────────────────


def test_owner_can_access_own_transaction_detail(client, auth_pair):
    a_id, a_token, _, _ = auth_pair
    account = _create_account(client, a_token, a_id)
    tx_id = _create_transaction(client, a_token, account["id"])

    r = client.get(f"/api/transactions/{tx_id}", headers=_headers(a_token))
    assert r.status_code == 200
    assert r.get_json()["id"] == tx_id


def test_owner_cannot_access_another_users_transaction_detail(client, auth_pair):
    a_id, a_token, _, b_token = auth_pair
    account = _create_account(client, a_token, a_id)
    tx_id = _create_transaction(client, a_token, account["id"])

    r = client.get(f"/api/transactions/{tx_id}", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_access_another_users_transactions_list(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.get(f"/api/users/{a_id}/transactions", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


# ── Financial summary / facts / AI routes (deny + own-access) ────────────


def test_owner_can_access_own_financial_summary(client, auth_pair):
    a_id, a_token, _, _ = auth_pair
    r = client.get(f"/api/financial-summary/{a_id}", headers=_headers(a_token))
    assert r.status_code == 200
    assert "total_income" in r.get_json()


def test_owner_cannot_access_another_users_financial_summary(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.get(f"/api/financial-summary/{a_id}", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_can_access_own_financial_facts(client, auth_pair):
    a_id, a_token, _, _ = auth_pair
    r = client.get(f"/api/users/{a_id}/financial-facts", headers=_headers(a_token))
    assert r.status_code == 200


def test_owner_cannot_access_another_users_financial_facts(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.get(f"/api/users/{a_id}/financial-facts", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_access_another_users_ai_explanation(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.post(
        f"/api/users/{a_id}/financial-explanation",
        json={"question": "What is my cash flow?"},
        headers=_headers(b_token),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_access_another_users_goal_intelligence(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.post(
        f"/api/users/{a_id}/financial-goal-intelligence",
        json={"question": "Can I reach my goal?"},
        headers=_headers(b_token),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_can_access_own_risk_intelligence(client, auth_pair):
    a_id, a_token, _, _ = auth_pair
    r = client.get(f"/api/users/{a_id}/risk-intelligence", headers=_headers(a_token))
    assert r.status_code == 200


def test_owner_cannot_access_another_users_risk_intelligence(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.get(f"/api/users/{a_id}/risk-intelligence", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_can_access_own_recommendations(client, auth_pair):
    a_id, a_token, _, _ = auth_pair
    r = client.get(f"/api/users/{a_id}/recommendations", headers=_headers(a_token))
    assert r.status_code == 200


def test_owner_cannot_access_another_users_recommendations(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.get(f"/api/users/{a_id}/recommendations", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


# ── Audit routes ─────────────────────────────────────────────────────────


def test_owner_cannot_access_another_users_audit_records(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.get(f"/api/users/{a_id}/audit", headers=_headers(b_token))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_write_audit_for_another_user(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.post(
        f"/api/users/{a_id}/audit-record",
        json={"kind": "decision", "payload": {"note": "x"}},
        headers=_headers(b_token),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


# ── AI controller / async routes ─────────────────────────────────────────


def test_owner_cannot_run_ai_controller_for_another_users_url(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.post(
        f"/api/users/{a_id}/ai-controller",
        json={"intent": "Save more"},
        headers=_headers(b_token),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_owner_cannot_dispatch_async_controller_for_another_url_user(
    client, auth_pair
):
    a_id, _, _, b_token = auth_pair
    r = client.post(
        f"/api/users/{a_id}/ai-controller/async",
        json={"intent": "Save more"},
        headers=_headers(b_token),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_async_status_denied_for_cross_user(client, auth_pair):
    a_id, _, _, b_token = auth_pair
    r = client.get(
        f"/api/users/{a_id}/ai-controller/async/{uuid.uuid4()}",
        headers=_headers(b_token),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"
