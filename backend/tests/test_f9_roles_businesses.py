"""F9.x.1 tests: role-based authN + multi-user business architecture.

Covers:
- registration always yields MERCHANT; client can never set role.
- user serializer exposes role; normal update never changes it.
- PLATFORM_ADMIN-only admin endpoints (list users, assign roles) with the
  403 / 401 security contract.
- business creation makes the creator the OWNER; members can be added only by
  the OWNER; FINANCE_MANAGER members get read access but cannot manage
  members; non-members (including a PLATFORM_ADMIN without membership) get
  403; cross-business access is 403; duplicate membership 409; an OWNER
  cannot be removed; personal flows are unchanged.
- business_id on accounts is server-validated against membership.
"""

import uuid

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import User

PASSWORD = "test-password-123"
MERCHANT_EMAIL = "merchant@example.com"
PM_EMAIL = "admin@example.com"
FM_EMAIL = "finance@example.com"
FOREIGN_EMAIL = "foreign@example.com"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_user(app: Flask, email: str, role: str = "MERCHANT") -> str:
    """Create a user directly in the DB with the given role; return its id."""
    u = User(email=email, full_name=email.split("@")[0], role=role)
    u.set_password(PASSWORD)
    with app.app_context():
        db.session.add(u)
        db.session.commit()
        return str(u.id)


def _login(client: FlaskClient, email: str) -> dict:
    r = client.post("/api/users/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _biz_owner_bundle(client: FlaskClient, app: Flask, email: str = MERCHANT_EMAIL):
    """Create (or load) a MERCHANT, log in, and create one business."""
    uid = _make_user(app, email)
    sid = str(uid)
    tok = _login(client, email)["access_token"]
    r = client.post("/api/businesses", json={"name": "Acme Ltd"}, headers=_headers(tok))
    assert r.status_code == 201, r.get_json()
    bid = r.get_json()["id"]
    return sid, bid, tok


# ── Registration & serialization ─────────────────────────────────────────


def test_registration_defaults_to_merchant(client: FlaskClient):
    r = client.post(
        "/api/users",
        json={"email": MERCHANT_EMAIL, "full_name": "M", "password": PASSWORD},
    )
    assert r.status_code == 201
    assert r.get_json()["role"] == "MERCHANT"


def test_registration_rejects_client_supplied_role(client: FlaskClient):
    r = client.post(
        "/api/users",
        json={
            "email": MERCHANT_EMAIL,
            "full_name": "M",
            "password": PASSWORD,
            "role": "PLATFORM_ADMIN",
        },
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_login_exposes_role(client: FlaskClient, app: Flask):
    _make_user(app, MERCHANT_EMAIL)
    body = _login(client, MERCHANT_EMAIL)
    assert body["user"]["role"] == "MERCHANT"


def test_user_update_cannot_self_elevate_role(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    tok = _login(client, MERCHANT_EMAIL)["access_token"]
    r = client.put(
        f"/api/users/{uid}",
        json={"role": "PLATFORM_ADMIN"},
        headers=_headers(tok),
    )
    assert r.status_code == 403


# ── PLATFORM_ADMIN admin endpoints ───────────────────────────────────────


def test_only_platform_admin_can_list_users(client: FlaskClient, app: Flask):
    _make_user(app, MERCHANT_EMAIL)
    _make_user(app, PM_EMAIL, "PLATFORM_ADMIN")
    pm_tok = _login(client, PM_EMAIL)["access_token"]
    m_tok = _login(client, MERCHANT_EMAIL)["access_token"]

    r = client.get("/api/users", headers=_headers(m_tok))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"

    r = client.get("/api/users", headers=_headers(pm_tok))
    assert r.status_code == 200
    assert len(r.get_json()["users"]) == 2


def test_only_platform_admin_can_assign_role(client: FlaskClient, app: Flask):
    target = _make_user(app, MERCHANT_EMAIL)
    _make_user(app, PM_EMAIL, "PLATFORM_ADMIN")
    pm_tok = _login(client, PM_EMAIL)["access_token"]

    # A normal merchant cannot assign roles.
    r = client.patch(
        f"/api/users/{target}/role", json={"role": "FINANCE_MANAGER"}, headers={}
    )
    assert r.status_code == 401

    # PLATFORM_ADMIN can.
    r = client.patch(
        f"/api/users/{target}/role",
        json={"role": "FINANCE_MANAGER"},
        headers=_headers(pm_tok),
    )
    assert r.status_code == 200
    assert r.get_json()["role"] == "FINANCE_MANAGER"


def test_role_assignment_rejects_invalid_role(client: FlaskClient, app: Flask):
    target = _make_user(app, MERCHANT_EMAIL)
    _make_user(app, PM_EMAIL, "PLATFORM_ADMIN")
    pm_tok = _login(client, PM_EMAIL)["access_token"]
    r = client.patch(
        f"/api/users/{target}/role",
        json={"role": "GOD"},
        headers=_headers(pm_tok),
    )
    assert r.status_code == 400


def test_platform_admin_cannot_demote_last_platform_admin(
    client: FlaskClient, app: Flask
):
    admin_id = _make_user(app, PM_EMAIL, "PLATFORM_ADMIN")
    pm_tok = _login(client, PM_EMAIL)["access_token"]
    r = client.patch(
        f"/api/users/{admin_id}/role",
        json={"role": "MERCHANT"},
        headers=_headers(pm_tok),
    )
    assert r.status_code == 409


# ── Businesses: creation & listing ───────────────────────────────────────


def test_create_business_makes_creator_owner(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    members = client.get(f"/api/businesses/{bid}/members", headers=_headers(tok))
    assert members.status_code == 200
    assert len(members.get_json()["members"]) == 1
    assert members.get_json()["members"][0]["user_id"] == uid
    assert members.get_json()["members"][0]["role"] == "OWNER"


def test_create_business_requires_name(client: FlaskClient, app: Flask):
    _make_user(app, MERCHANT_EMAIL)
    tok = _login(client, MERCHANT_EMAIL)["access_token"]
    r = client.post("/api/businesses", json={"name": "  "}, headers=_headers(tok))
    assert r.status_code == 400


def test_create_business_is_merchant_only(client: FlaskClient, app: Flask):
    """Only a MERCHANT may create (and thereby own) a business.

    A FINANCE_MANAGER is an operations/analysis role and a PLATFORM_ADMIN is a
    platform role; neither may acquire ownership of a merchant business.
    """
    # FINANCE_MANAGER cannot create a business.
    _make_user(app, FM_EMAIL, role="FINANCE_MANAGER")
    r = client.post(
        "/api/businesses", json={"name": "No FM Biz"}, headers=_headers(_login(client, FM_EMAIL)["access_token"])
    )
    assert r.status_code == 403

    # PLATFORM_ADMIN cannot create a business either.
    _make_user(app, PM_EMAIL, role="PLATFORM_ADMIN")
    r = client.post(
        "/api/businesses", json={"name": "No Admin Biz"}, headers=_headers(_login(client, PM_EMAIL)["access_token"])
    )
    assert r.status_code == 403

    # A foreign MERCHANT can still create a business.
    merchant_email = "creator-merchant@example.com"
    _make_user(app, merchant_email)
    r = client.post(
        "/api/businesses", json={"name": "New Biz"}, headers=_headers(_login(client, merchant_email)["access_token"])
    )
    assert r.status_code == 201


def test_business_list_shows_only_memberships(client: FlaskClient, app: Flask):
    m_uid, bid, m_tok = _biz_owner_bundle(client, app)
    _make_user(app, FOREIGN_EMAIL)
    f_tok = _login(client, FOREIGN_EMAIL)["access_token"]

    # Owner sees the business.
    r = client.get("/api/businesses", headers=_headers(m_tok))
    assert r.status_code == 200
    assert any(b["id"] == bid for b in r.get_json()["businesses"])

    # Foreign user (not a member) sees none.
    r = client.get("/api/businesses", headers=_headers(f_tok))
    assert r.status_code == 200
    assert r.get_json()["businesses"] == []


# ── Business: member management (OWNER only) ─────────────────────────────


def test_owner_can_add_finance_manager_member(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    fm_id = _make_user(app, FM_EMAIL)
    r = client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": fm_id, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["role"] == "FINANCE_MANAGER"


def test_owner_can_add_member_by_email(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    _make_user(app, FM_EMAIL)
    # An OWNER adds the member using just the email (no user id needed).
    r = client.post(
        f"/api/businesses/{bid}/members",
        json={"email": FM_EMAIL, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["email"] == FM_EMAIL


def test_add_member_by_unknown_email_is_404(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    r = client.post(
        f"/api/businesses/{bid}/members",
        json={"email": "nobody@example.com", "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    assert r.status_code == 404


def test_finance_manager_cannot_manage_members(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    fm_id = _make_user(app, FM_EMAIL)
    client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": fm_id, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    fm_tok = _login(client, FM_EMAIL)["access_token"]

    # FM can view members (read access)...
    r = client.get(f"/api/businesses/{bid}/members", headers=_headers(fm_tok))
    assert r.status_code == 200

    # ...but cannot add or remove members.
    other = _make_user(app, FOREIGN_EMAIL)
    r = client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": other, "role": "FINANCE_MANAGER"},
        headers=_headers(fm_tok),
    )
    assert r.status_code == 403
    r = client.delete(
        f"/api/businesses/{bid}/members/{fm_id}", headers=_headers(fm_tok)
    )
    assert r.status_code == 403


def test_duplicate_membership_is_409(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    fm_id = _make_user(app, FM_EMAIL)
    client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": fm_id, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    r = client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": fm_id, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    assert r.status_code == 409


def test_invalid_membership_role_is_400(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    fm_id = _make_user(app, FM_EMAIL)
    r = client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": fm_id, "role": "PLATFORM_ADMIN"},
        headers=_headers(tok),
    )
    assert r.status_code == 400


def test_platform_admin_cannot_be_added_as_member(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    pm_id = _make_user(app, PM_EMAIL, "PLATFORM_ADMIN")
    r = client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": pm_id, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    assert r.status_code == 403


def test_owner_cannot_remove_self(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    r = client.delete(f"/api/businesses/{bid}/members/{uid}", headers=_headers(tok))
    assert r.status_code == 409


def test_owner_can_remove_finance_manager(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    fm_id = _make_user(app, FM_EMAIL)
    client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": fm_id, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    r = client.delete(f"/api/businesses/{bid}/members/{fm_id}", headers=_headers(tok))
    assert r.status_code == 204


# ── Cross-business / outsider access never leaks ─────────────────────────


def test_non_member_gets_403_for_business(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    _make_user(app, FOREIGN_EMAIL)
    f_tok = _login(client, FOREIGN_EMAIL)["access_token"]

    r = client.get(f"/api/businesses/{bid}", headers=_headers(f_tok))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_business_member_of_a_different_business_cannot_access(
    client: FlaskClient, app: Flask
):
    _, bid_a, tok_a = _biz_owner_bundle(client, app, "a@example.com")
    far_id, bid_b, tok_b = _biz_owner_bundle(client, app, "b@example.com")

    # far_id is a member (owner) of business B but not of A.
    r = client.get(f"/api/businesses/{bid_a}/members", headers=_headers(tok_b))
    assert r.status_code == 403


def test_platform_admin_without_membership_cannot_access_business_data(
    client: FlaskClient, app: Flask
):
    uid, bid, tok = _biz_owner_bundle(client, app)
    _make_user(app, PM_EMAIL, "PLATFORM_ADMIN")
    pm_tok = _login(client, PM_EMAIL)["access_token"]

    r = client.get(f"/api/businesses/{bid}", headers=_headers(pm_tok))
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_finance_manager_can_view_business(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    fm_id = _make_user(app, FM_EMAIL)
    client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": fm_id, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    fm_tok = _login(client, FM_EMAIL)["access_token"]
    r = client.get(f"/api/businesses/{bid}", headers=_headers(fm_tok))
    assert r.status_code == 200
    assert r.get_json()["id"] == bid


# ── Business-scoped accounts (server-validated) ──────────────────────────


def test_owner_can_create_business_scoped_account(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    r = client.post(
        "/api/accounts",
        json={
            "user_id": uid,
            "business_id": bid,
            "name": "Biz Account",
            "account_type": "bank",
            "currency": "INR",
        },
        headers=_headers(tok),
    )
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["business_id"] == bid


def test_finance_manager_can_create_business_scoped_account(
    client: FlaskClient, app: Flask
):
    uid, bid, tok = _biz_owner_bundle(client, app)
    fm_id = _make_user(app, FM_EMAIL)
    client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": fm_id, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    fm_tok = _login(client, FM_EMAIL)["access_token"]
    r = client.post(
        "/api/accounts",
        json={
            "user_id": fm_id,
            "business_id": bid,
            "name": "FM Biz Account",
            "account_type": "bank",
            "currency": "INR",
        },
        headers=_headers(fm_tok),
    )
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["business_id"] == bid


def test_non_member_cannot_create_business_scoped_account(
    client: FlaskClient, app: Flask
):
    uid, bid, tok = _biz_owner_bundle(client, app)
    _make_user(app, FOREIGN_EMAIL)
    f_tok = _login(client, FOREIGN_EMAIL)["access_token"]
    r = client.post(
        "/api/accounts",
        json={
            "user_id": str(uuid.uuid4()),
            "business_id": bid,
            "name": "Attempt",
            "account_type": "bank",
            "currency": "INR",
        },
        headers=_headers(f_tok),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_account_update_cannot_change_business_scope(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    account = client.post(
        "/api/accounts",
        json={
            "user_id": uid,
            "name": "Personal",
            "account_type": "bank",
            "currency": "INR",
        },
        headers=_headers(tok),
    ).get_json()
    r = client.put(
        f"/api/accounts/{account['id']}",
        json={"business_id": bid},
        headers=_headers(tok),
    )
    assert r.status_code == 403


def test_personal_account_has_null_business_id(client: FlaskClient, app: Flask):
    uid, bid, tok = _biz_owner_bundle(client, app)
    account = client.post(
        "/api/accounts",
        json={
            "user_id": uid,
            "name": "Personal",
            "account_type": "bank",
            "currency": "INR",
        },
        headers=_headers(tok),
    ).get_json()
    assert account["business_id"] is None


def test_demo_login_success_and_idempotent(client: FlaskClient, app: Flask):
    # Test first login for MERCHANT role
    r = client.post("/api/users/demo-login", json={"role": "MERCHANT"})
    assert r.status_code == 200
    res = r.get_json()
    assert "access_token" in res
    assert res["user"]["email"] == "merchant@demo.com"

    # Test second login (idempotency check)
    r2 = client.post("/api/users/demo-login", json={"role": "MERCHANT"})
    assert r2.status_code == 200

    # Test PLATFORM_ADMIN role
    r3 = client.post("/api/users/demo-login", json={"role": "PLATFORM_ADMIN"})
    assert r3.status_code == 200
    assert r3.get_json()["user"]["email"] == "admin@demo.com"


def test_demo_login_fails_in_production(client: FlaskClient, app: Flask, monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    r = client.post("/api/users/demo-login", json={"role": "MERCHANT"})
    assert r.status_code == 403


def test_demo_login_never_binds_to_unrelated_demo_corp(client: FlaskClient, app: Flask):
    """Demo login creates the merchant's OWN Demo Corp, never a foreign one.

    Regression for the unscoped ``Business.name == "Demo Corp"`` lookup: the
    demo chain must stay inside the merchant's own business and an unrelated
    same-named business must not gain merchant/finance members or seed rows.
    """
    from sqlalchemy import select

    from app.models import Business, BusinessMember

    foreign_uid = _make_user(app, "outsider@demo.com")
    f_tok = _login(client, "outsider@demo.com")["access_token"]
    r = client.post(
        "/api/businesses", json={"name": "Demo Corp"}, headers=_headers(f_tok)
    )
    assert r.status_code == 201
    foreign_bid = r.get_json()["id"]

    r = client.post("/api/users/demo-login", json={"role": "MERCHANT"})
    assert r.status_code == 200

    with app.app_context():
        merch = db.session.scalar(select(User).where(User.email == "merchant@demo.com"))
        finance = db.session.scalar(
            select(User).where(User.email == "finance@demo.com")
        )
        foreign_biz = db.session.get(Business, uuid.UUID(foreign_bid))
        assert foreign_biz is not None
        member_ids = {
            m.user_id
            for m in db.session.scalars(
                select(BusinessMember).where(
                    BusinessMember.business_id == foreign_biz.id
                )
            ).all()
        }
        assert member_ids == {uuid.UUID(foreign_uid)}
        assert merch.id not in member_ids
        assert finance.id not in member_ids

        own = db.session.scalar(
            select(Business)
            .join(BusinessMember, BusinessMember.business_id == Business.id)
            .where(
                BusinessMember.user_id == merch.id,
                BusinessMember.role == "OWNER",
                Business.name == "Demo Corp",
            )
        )
        assert own is not None
        assert own.id != foreign_biz.id


# ── DEFECT fix: business-scoped reads bind the path user_id to the business ──


def _biz_with_finance_manager(client: FlaskClient, app: Flask):
    """Create a MERCHANT + business, add a FINANCE_MANAGER member."""
    uid, bid, tok = _biz_owner_bundle(client, app)
    fm_id = _make_user(app, FM_EMAIL)
    client.post(
        f"/api/businesses/{bid}/members",
        json={"user_id": fm_id, "role": "FINANCE_MANAGER"},
        headers=_headers(tok),
    )
    fm_tok = _login(client, FM_EMAIL)["access_token"]
    return uid, bid, tok, fm_id, fm_tok


def test_business_scoped_list_binds_path_user_id(client: FlaskClient, app: Flask):
    """A member cannot pivot the path user_id to a non-member of the business.

    Regression for the identity-decoupling gap: when ``business_id`` is
    supplied, the requested ``user_id`` must itself be a member of that
    business, not merely the caller.
    """
    uid, bid, tok, fm_id, fm_tok = _biz_with_finance_manager(client, app)
    outside_id = _make_user(app, "z@example.com")

    # Member (FM) passing an unrelated non-member id under the business -> 403.
    r = client.get(
        f"/api/users/{outside_id}/accounts?business_id={bid}",
        headers=_headers(fm_tok),
    )
    assert r.status_code == 403, r.get_json()

    # Owner also cannot read as an unrelated non-member id.
    r = client.get(
        f"/api/users/{outside_id}/accounts?business_id={bid}",
        headers=_headers(tok),
    )
    assert r.status_code == 403, r.get_json()


def test_business_scoped_list_allows_other_member_for_member(
    client: FlaskClient, app: Flask
):
    """A member may read a business scope under a fellow member's id."""
    uid, bid, tok, fm_id, fm_tok = _biz_with_finance_manager(client, app)

    # FM writes an account then reads under the OWNER's id in the business.
    client.post(
        "/api/accounts",
        json={
            "user_id": fm_id,
            "business_id": bid,
            "name": "Biz Account",
            "account_type": "bank",
            "currency": "INR",
        },
        headers=_headers(fm_tok),
    )
    r = client.get(
        f"/api/users/{uid}/accounts?business_id={bid}",
        headers=_headers(fm_tok),
    )
    assert r.status_code == 200, r.get_json()
    assert any(a["business_id"] == bid for a in r.get_json()["accounts"])

