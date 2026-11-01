"""Tests for the platform admin stats endpoint (app/routes/admin.py)."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import Business, BusinessMember, User

PASSWORD = "correct-horse-battery-staple"


def _make_user(app: Flask, email: str, role: str = "MERCHANT") -> str:
    u = User(email=email, full_name=email.split("@")[0], role=role)
    u.set_password(PASSWORD)
    with app.app_context():
        db.session.add(u)
        db.session.commit()
        return str(u.id)


def _login(client: FlaskClient, email: str) -> str:
    r = client.post("/api/users/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["access_token"]


def test_admin_stats_platform_admin_only(client: FlaskClient, app: Flask):
    _make_user(app, "admin@x.com", "PLATFORM_ADMIN")
    _make_user(app, "merchant@x.com", "MERCHANT")
    _make_user(app, "fm@x.com", "FINANCE_MANAGER")

    # A MERCHANT must be forbidden from admin stats.
    m_tok = _login(client, "merchant@x.com")
    r = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {m_tok}"})
    assert r.status_code == 403

    # A PLATFORM_ADMIN may read the stats.
    a_tok = _login(client, "admin@x.com")
    r = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {a_tok}"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["total_users"] == 3
    assert data["users_by_role"]["PLATFORM_ADMIN"] == 1
    assert data["users_by_role"]["MERCHANT"] == 1
    assert data["users_by_role"]["FINANCE_MANAGER"] == 1
    assert data["total_businesses"] == 0


def test_admin_stats_business_count(client: FlaskClient, app: Flask):
    _make_user(app, "admin@x.com", "PLATFORM_ADMIN")
    merchant_id = _make_user(app, "merchant@x.com", "MERCHANT")
    with app.app_context():
        from uuid import UUID as _UUID

        b = Business(name="Acme Ltd")
        db.session.add(b)
        db.session.flush()
        db.session.add(
            BusinessMember(
                business_id=b.id, user_id=_UUID(merchant_id), role="OWNER"
            )
        )
        db.session.commit()
    tok = _login(client, "admin@x.com")
    r = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.get_json()["total_businesses"] == 1


def test_admin_stats_unauthenticated(client: FlaskClient):
    r = client.get("/api/admin/stats")
    assert r.status_code == 401
