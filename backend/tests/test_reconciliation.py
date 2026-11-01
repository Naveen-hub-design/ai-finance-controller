"""M10.x: tests for the multi-source financial reconciliation agent.

Covers the deterministic reconciliation service (match rate + exceptions +
one-ledger-entry-per-match), the synchronous and asynchronous HTTP routes
(auth + ownership binding + audit persistence), and the worker task.

Redis / Celery are never required: the async route tests mock the dispatch
boundary (``m4_reconcile.dispatch_reconciliation`` and ``task_result``) and
the worker-task tests use Celery's eager ``apply(...)`` (in-process) with the
shared-file-SQLite pattern from ``test_ai_controller_task.py``.
"""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import (
    Account,
    AuditRecord,
    Business,
    BusinessMember,
    StatementLine,
    Transaction,
    User,
)
from app.services.m4.reconciliation import run_reconciliation

PASSWORD = "test-password-123"
MERCHANT_EMAIL = "recon-owner@example.com"
FM_EMAIL = "recon-fm@example.com"
FOREIGN_EMAIL = "recon-foreign@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def _new_business(app: Flask, name: str = "Recon Ltd") -> str:
    with app.app_context():
        b = Business(name=name)
        db.session.add(b)
        db.session.commit()
        return str(b.id)


def _add_member(app: Flask, business_id: str, user_id: str, role: str) -> None:
    with app.app_context():
        db.session.add(
            BusinessMember(
                business_id=uuid.UUID(business_id),
                user_id=uuid.UUID(user_id),
                role=role,
            )
        )
        db.session.commit()


def _new_account(
    app: Flask, user_id: str, business_id: str | None = None, name: str = "Acct"
) -> str:
    with app.app_context():
        a = Account(
            user_id=uuid.UUID(user_id),
            business_id=uuid.UUID(business_id) if business_id else None,
            name=name,
            account_type="checking",
        )
        db.session.add(a)
        db.session.commit()
        return str(a.id)


def _new_txn(app: Flask, account_id: str, amount, d, desc: str) -> str:
    with app.app_context():
        t = Transaction(
            account_id=uuid.UUID(account_id),
            amount=amount,
            transaction_type="expense",
            description=desc,
            transaction_date=d,
        )
        db.session.add(t)
        db.session.commit()
        return str(t.id)


def _new_statement(
    app: Flask,
    user_id: str,
    business_id: str | None,
    amount,
    d,
    desc: str,
    source: str = "bank_statement",
) -> str:
    with app.app_context():
        s = StatementLine(
            user_id=uuid.UUID(user_id),
            business_id=uuid.UUID(business_id) if business_id else None,
            source=source,
            amount=amount,
            transaction_date=d,
            description=desc,
        )
        db.session.add(s)
        db.session.commit()
        return str(s.id)


def _audit_kind_count(app: Flask, user_id: str, kind: str) -> int:
    with app.app_context():
        return AuditRecord.query.filter_by(
            user_id=uuid.UUID(user_id), kind=kind
        ).count()


# ---------------------------------------------------------------------------
# 1. Service: match rate, exceptions, one-ledger-entry-per-match
# ---------------------------------------------------------------------------


def test_service_reports_match_rate_and_exceptions(app: Flask):
    uid = _make_user(app, "svc@example.com")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    # Internal ledger (source A).
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_txn(app, acct, Decimal("250.0000"), d, "Vendor B")
    _new_txn(app, acct, Decimal("300.5000"), d, "Vendor C")
    # Statement batch (source B): 2 match, 1 does not.
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("250.0000"), d, "Vendor B")
    _new_statement(app, uid, biz, Decimal("999.9900"), d, "Unknown Vendor")

    with app.app_context():
        report = run_reconciliation(uid, business_id=biz, source="bank_statement")

    assert report.batch_size == 3
    assert report.matched_count == 2
    assert report.ledger_matched_count == 2
    assert report.match_rate == "66.67%"
    assert len(report.exceptions) == 1
    ex = report.exceptions[0]
    assert ex.statement_description == "Unknown Vendor"
    assert "no internal ledger transaction matched" in ex.reason

    # Match records carry the resolved match basis.
    assert all(rec.match_basis == "amount_date_description" for rec in report.matched)
    assert {rec.statement_description for rec in report.matched} == {
        "Vendor A",
        "Vendor B",
    }


def test_service_consumes_each_ledger_entry_once(app: Flask):
    uid = _make_user(app, "svc2@example.com")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    # One internal ledger entry.
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    # Two identical statement lines claim the same key.
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")

    with app.app_context():
        report = run_reconciliation(uid, business_id=biz)

    assert report.matched_count == 1
    assert report.ledger_matched_count == 1
    assert len(report.exceptions) == 1
    # The second duplicate could not be satisfied by the same ledger row.
    assert report.match_rate == "50.00%"


def test_service_scopes_personal_ledger_out_of_business(app: Flask):
    uid = _make_user(app, "svc3@example.com")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    biz_acct = _new_account(app, uid, biz)
    per_acct = _new_account(app, uid, business_id=None, name="Personal")

    d = date(2026, 8, 1)
    # Personal internal transaction with the same key as the statement line.
    _new_txn(app, per_acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")

    with app.app_context():
        report = run_reconciliation(uid, business_id=biz)

    # The business-scoped run must not see the personal ledger row.
    assert report.matched_count == 0
    assert report.matched == []
    assert len(report.exceptions) == 1


def test_service_personal_run_excludes_business_statement_lines(app: Flask):
    uid = _make_user(app, "svc4@example.com")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    per_acct = _new_account(app, uid, business_id=None, name="Personal")

    d = date(2026, 8, 1)
    # One internal personal ledger transaction.
    _new_txn(app, per_acct, Decimal("100.0000"), d, "Vendor A")
    # Identical statement lines: one business-scoped, one personal. The
    # business line is inserted first so, pre-fix, it would consume the
    # personal ledger entry and corrupt the personal reconcile batch.
    biz_line = _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")
    per_line = _new_statement(app, uid, None, Decimal("100.0000"), d, "Vendor A")

    with app.app_context():
        report = run_reconciliation(uid)

    # A personal run must analyze only the personal statement line.
    assert report.batch_size == 1
    assert report.matched_count == 1
    assert report.ledger_matched_count == 1
    assert report.matched[0].statement_line_id == per_line
    assert report.match_rate == "100.00%"

    # The business statement line must be left untouched (no stale status
    # rewrite, no matched_transaction_id).
    with app.app_context():
        biz_row = db.session.get(StatementLine, uuid.UUID(biz_line))
        assert biz_row.status == "pending"
        assert biz_row.matched_transaction_id is None
        assert biz_row.category is None


# ---------------------------------------------------------------------------
# 2. Sync route: auth + audit
# ---------------------------------------------------------------------------


def test_reconcile_requires_auth(client: FlaskClient):
    r = client.post(f"/api/users/{uuid.uuid4()}/reconcile", json={"source": "bank_statement"})
    assert r.status_code == 401


def test_owner_can_run_reconcile_and_persists_audit(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("999.9900"), d, "Unknown Vendor")

    tok = _login(client, MERCHANT_EMAIL)
    r = client.post(
        f"/api/users/{uid}/reconcile?business_id={biz}",
        json={"source": "bank_statement"},
        headers=_headers(tok),
    )
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["batch_size"] == 2
    assert body["matched_count"] == 1
    assert body["match_rate"] == "50.00%"
    assert len(body["exceptions"]) == 1

    assert _audit_kind_count(app, uid, "reconciliation") == 1


def test_business_member_can_run_reconcile(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    fm = _make_user(app, FM_EMAIL, role="FINANCE_MANAGER")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    _add_member(app, biz, fm, "FINANCE_MANAGER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")

    tok = _login(client, FM_EMAIL)
    r = client.post(
        f"/api/users/{uid}/reconcile?business_id={biz}",
        json={"source": "bank_statement"},
        headers=_headers(tok),
    )
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["matched_count"] == 1


def test_business_reconcile_audit_is_business_scoped(
    client: FlaskClient, app: Flask,
):
    uid = _make_user(app, MERCHANT_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")

    tok = _login(client, MERCHANT_EMAIL)
    r = client.post(
        f"/api/users/{uid}/reconcile?business_id={biz}",
        json={"source": "bank_statement"},
        headers=_headers(tok),
    )
    assert r.status_code == 200, r.get_json()

    biz_view = client.get(
        f"/api/users/{uid}/audit?business_id={biz}", headers=_headers(tok)
    )
    assert biz_view.status_code == 200
    records = biz_view.get_json()["records"]
    assert len(records) == 1
    assert records[0]["kind"] == "reconciliation"

    personal = client.get(f"/api/users/{uid}/audit", headers=_headers(tok))
    assert personal.status_code == 200
    assert personal.get_json()["records"] == []


def test_non_member_cannot_run_reconcile(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    foreign = _make_user(app, FOREIGN_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")

    tok = _login(client, FOREIGN_EMAIL)
    r = client.post(
        f"/api/users/{uid}/reconcile?business_id={biz}",
        json={"source": "bank_statement"},
        headers=_headers(tok),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_reconcile_rejects_invalid_business_id(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    tok = _login(client, MERCHANT_EMAIL)
    r = client.post(
        f"/api/users/{uid}/reconcile?business_id=not-a-uuid",
        json={"source": "bank_statement"},
        headers=_headers(tok),
    )
    assert r.status_code == 400


def test_reconcile_rejects_blank_source(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    tok = _login(client, MERCHANT_EMAIL)
    r = client.post(
        f"/api/users/{uid}/reconcile",
        json={"source": "   "},
        headers=_headers(tok),
    )
    assert r.status_code == 400


def test_reconcile_another_users_personal_data_is_403(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    foreign = _make_user(app, FOREIGN_EMAIL)
    tok = _login(client, FOREIGN_EMAIL)
    # A foreign user cannot run a personal (non-business) reconciliation for
    # another user: ownership is checked before any lookup or computation.
    r = client.post(
        f"/api/users/{uid}/reconcile",
        json={"source": "bank_statement"},
        headers=_headers(tok),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


# ---------------------------------------------------------------------------
# 3. Async route: submit + ownership-bound poll
# ---------------------------------------------------------------------------


def _fake_result(task_id: str, state: str = "PENDING", result=None):
    class _Fake:
        def __init__(self):
            self.id = task_id
            self.state = state
            self.result = result
    return _Fake()


def test_reconcile_async_requires_auth(client: FlaskClient):
    r = client.post(f"/api/users/{uuid.uuid4()}/reconcile/async", json={"source": "bank_statement"})
    assert r.status_code == 401


def test_reconcile_async_submit_binds_owner_and_polls(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")

    tok = _login(client, MERCHANT_EMAIL)
    task_id = str(uuid.uuid4())

    with patch(
        "app.routes.m4_reconcile.dispatch_reconciliation",
        return_value=_fake_result(task_id),
    ) as mock_dispatch:
        r = client.post(
            f"/api/users/{uid}/reconcile/async?business_id={biz}",
            json={"source": "bank_statement"},
            headers=_headers(tok),
        )
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["task_id"] == task_id
    assert r.get_json()["status"] == "PENDING"
    mock_dispatch.assert_called_once_with(
        str(uid), source="bank_statement", business_id=uuid.UUID(biz)
    )

    report = {
        "user_id": uid,
        "source": "bank_statement",
        "batch_size": 1,
        "matched_count": 1,
        "match_rate": "100.00%",
        "ledger_matched_count": 1,
        "matched": [],
        "exceptions": [],
    }
    with patch(
        "app.routes.m4_reconcile.task_result",
        return_value=_fake_result(task_id, state="SUCCESS", result=report),
    ):
        r = client.get(
            f"/api/users/{uid}/reconcile/async/{task_id}",
            headers=_headers(tok),
        )
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["status"] == "SUCCESS"
    assert r.get_json()["result"]["matched_count"] == 1


def test_reconcile_async_poll_rejects_non_owner(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    foreign = _make_user(app, FOREIGN_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")

    owner_tok = _login(client, MERCHANT_EMAIL)
    task_id = str(uuid.uuid4())

    with patch(
        "app.routes.m4_reconcile.dispatch_reconciliation",
        return_value=_fake_result(task_id),
    ):
        r = client.post(
            f"/api/users/{uid}/reconcile/async?business_id={biz}",
            json={"source": "bank_statement"},
            headers=_headers(owner_tok),
        )
    assert r.status_code == 201

    foreign_tok = _login(client, FOREIGN_EMAIL)
    r = client.get(
        f"/api/users/{uid}/reconcile/async/{task_id}",
        headers=_headers(foreign_tok),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_reconcile_async_finance_manager_roundtrip(
    client: FlaskClient, app: Flask,
):
    uid = _make_user(app, MERCHANT_EMAIL)
    fm = _make_user(app, FM_EMAIL, role="FINANCE_MANAGER")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    _add_member(app, biz, fm, "FINANCE_MANAGER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")

    fm_tok = _login(client, FM_EMAIL)
    task_id = str(uuid.uuid4())
    report = {
        "user_id": uid,
        "source": "bank_statement",
        "batch_size": 1,
        "matched_count": 1,
        "match_rate": "100.00%",
        "ledger_matched_count": 1,
        "matched": [],
        "exceptions": [],
    }

    with patch(
        "app.routes.m4_reconcile.dispatch_reconciliation",
        return_value=_fake_result(task_id),
    ):
        r = client.post(
            f"/api/users/{fm}/reconcile/async?business_id={biz}",
            json={"source": "bank_statement"},
            headers=_headers(fm_tok),
        )
    assert r.status_code == 201, r.get_json()

    with patch(
        "app.routes.m4_reconcile.task_result",
        return_value=_fake_result(task_id, state="SUCCESS", result=report),
    ):
        r = client.get(
            f"/api/users/{fm}/reconcile/async/{task_id}",
            headers=_headers(fm_tok),
        )
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["status"] == "SUCCESS"
    assert r.get_json()["result"]["matched_count"] == 1


def test_reconcile_async_member_can_poll_owner_business_task(
    client: FlaskClient, app: Flask,
):
    uid = _make_user(app, MERCHANT_EMAIL)
    fm = _make_user(app, FM_EMAIL, role="FINANCE_MANAGER")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    _add_member(app, biz, fm, "FINANCE_MANAGER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")

    task_id = str(uuid.uuid4())
    with patch(
        "app.routes.m4_reconcile.dispatch_reconciliation",
        return_value=_fake_result(task_id),
    ):
        r = client.post(
            f"/api/users/{uid}/reconcile/async?business_id={biz}",
            json={"source": "bank_statement"},
            headers=_headers(_login(client, MERCHANT_EMAIL)),
        )
    assert r.status_code == 201

    fm_tok = _login(client, FM_EMAIL)
    with patch(
        "app.routes.m4_reconcile.task_result",
        return_value=_fake_result(task_id),
    ):
        r = client.get(
            f"/api/users/{fm}/reconcile/async/{task_id}",
            headers=_headers(fm_tok),
        )
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["status"] == "PENDING"


def test_reconcile_async_fm_polls_foreign_business_task_forbidden(
    client: FlaskClient, app: Flask,
):
    uid = _make_user(app, MERCHANT_EMAIL)
    fm = _make_user(app, FM_EMAIL, role="FINANCE_MANAGER")
    own_biz = _new_business(app)
    foreign_biz = _new_business(app, name="Foreign Recon Ltd")
    _add_member(app, own_biz, uid, "OWNER")
    _add_member(app, own_biz, fm, "FINANCE_MANAGER")
    _add_member(app, foreign_biz, uid, "OWNER")

    task_id = str(uuid.uuid4())
    with patch(
        "app.routes.m4_reconcile.dispatch_reconciliation",
        return_value=_fake_result(task_id),
    ):
        r = client.post(
            f"/api/users/{uid}/reconcile/async?business_id={foreign_biz}",
            json={"source": "bank_statement"},
            headers=_headers(_login(client, MERCHANT_EMAIL)),
        )
    assert r.status_code == 201

    fm_tok = _login(client, FM_EMAIL)
    r = client.get(
        f"/api/users/{fm}/reconcile/async/{task_id}",
        headers=_headers(fm_tok),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_reconcile_async_unrelated_personal_task_never_readable_by_member(
    client: FlaskClient, app: Flask,
):
    owner = _make_user(app, MERCHANT_EMAIL)
    other = _make_user(app, "recon-standalone@example.com")
    fm = _make_user(app, FM_EMAIL, role="FINANCE_MANAGER")
    biz = _new_business(app)
    _add_member(app, biz, owner, "OWNER")
    _add_member(app, biz, fm, "FINANCE_MANAGER")

    task_id = str(uuid.uuid4())
    other_tok = _login(client, "recon-standalone@example.com")
    with patch(
        "app.routes.m4_reconcile.dispatch_reconciliation",
        return_value=_fake_result(task_id),
    ):
        r = client.post(
            f"/api/users/{other}/reconcile/async",
            json={"source": "bank_statement"},
            headers=_headers(other_tok),
        )
    assert r.status_code == 201

    fm_tok = _login(client, FM_EMAIL)
    r = client.get(
        f"/api/users/{fm}/reconcile/async/{task_id}",
        headers=_headers(fm_tok),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_reconcile_async_poll_forbids_platform_admin(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    pm = _make_user(app, "recon-pm@example.com", role="PLATFORM_ADMIN")
    foreign = _make_user(app, FOREIGN_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")

    task_id = str(uuid.uuid4())
    with patch(
        "app.routes.m4_reconcile.dispatch_reconciliation",
        return_value=_fake_result(task_id),
    ):
        r = client.post(
            f"/api/users/{uid}/reconcile/async?business_id={biz}",
            json={"source": "bank_statement"},
            headers=_headers(_login(client, MERCHANT_EMAIL)),
        )
    assert r.status_code == 201

    pm_tok = _login(client, "recon-pm@example.com")
    r = client.get(
        f"/api/users/{pm}/reconcile/async/{task_id}",
        headers=_headers(pm_tok),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"

    outsider_tok = _login(client, FOREIGN_EMAIL)
    r = client.get(
        f"/api/users/{uid}/reconcile/async/{task_id}",
        headers=_headers(outsider_tok),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


def test_reconcile_async_poll_requires_jwt(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    task_id = str(uuid.uuid4())
    with patch(
        "app.routes.m4_reconcile.dispatch_reconciliation",
        return_value=_fake_result(task_id),
    ):
        r = client.post(
            f"/api/users/{uid}/reconcile/async?business_id={biz}",
            json={"source": "bank_statement"},
            headers=_headers(_login(client, MERCHANT_EMAIL)),
        )
    assert r.status_code == 201

    r = client.get(f"/api/users/{uid}/reconcile/async/{task_id}")
    assert r.status_code == 401


def test_reconcile_async_unknown_task_is_forbidden_before_result_read(
    client: FlaskClient, app: Flask,
):
    uid = _make_user(app, MERCHANT_EMAIL)
    tok = _login(client, MERCHANT_EMAIL)

    with patch(
        "app.routes.m4_reconcile.task_result"
    ) as mock_result:
        r = client.get(
            f"/api/users/{uid}/reconcile/async/{uuid.uuid4()}",
            headers=_headers(tok),
        )

    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"
    mock_result.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Service: category classification + metrics
# ---------------------------------------------------------------------------


def test_service_reports_metrics_and_missing_category(app: Flask):
    uid = _make_user(app, "metrics@example.com")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("999.9900"), d, "Unknown Vendor")

    with app.app_context():
        report = run_reconciliation(uid, business_id=biz)

    assert report.exception_count == 1
    assert report.exception_rate == "50.00%"
    assert report.match_rate == "50.00%"
    assert report.processing_duration_seconds >= 0
    assert report.throughput > 0
    assert report.exceptions[0].category == "MISSING_LEDGER_RECORD"
    assert report.exceptions[0].review_status == "UNRESOLVED"


def test_service_classifies_amount_mismatch(app: Flask):
    uid = _make_user(app, "amtex@example.com")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    # Ledger has 250.00/2026-08-01/Vendor B; statement claims 260.00 same day/desc.
    _new_txn(app, acct, Decimal("250.0000"), d, "Vendor B")
    _new_statement(app, uid, biz, Decimal("260.0000"), d, "Vendor B")

    with app.app_context():
        report = run_reconciliation(uid, business_id=biz)

    assert report.matched_count == 0
    assert report.exceptions[0].category == "AMOUNT_MISMATCH"
    assert "ledger shows amount 250.0000 on the same date/description" in (
        report.exceptions[0].reason
    )


def test_service_classifies_date_mismatch(app: Flask):
    uid = _make_user(app, "dateex@example.com")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    # Ledger has 300.00/2026-08-01/Vendor C; statement claims 300.00 next day.
    _new_txn(app, acct, Decimal("300.0000"), d, "Vendor C")
    _new_statement(app, uid, biz, Decimal("300.0000"), date(2026, 8, 2), "Vendor C")

    with app.app_context():
        report = run_reconciliation(uid, business_id=biz)

    assert report.exceptions[0].category == "DATE_MISMATCH"
    assert "different date" in report.exceptions[0].reason


def test_service_classifies_duplicate_record(app: Flask):
    uid = _make_user(app, "dupex@example.com")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(app, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")
    _new_statement(app, uid, biz, Decimal("100.0000"), d, "Vendor A")

    with app.app_context():
        report = run_reconciliation(uid, business_id=biz)

    assert report.matched_count == 1
    assert report.exceptions[0].category == "DUPLICATE_RECORD"


def test_service_persists_category_and_review_status_on_lines(app: Flask):
    uid = _make_user(app, "persist@example.com")
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)
    _new_statement(app, uid, biz, Decimal("999.9900"), date(2026, 8, 1), "Unknown Vendor")

    with app.app_context():
        run_reconciliation(uid, business_id=biz)
        line = StatementLine.query.first()
        assert line.status == "exception"
        assert line.category == "MISSING_LEDGER_RECORD"
        assert line.review_status == "UNRESOLVED"


# ---------------------------------------------------------------------------
# 6. Human review route
# ---------------------------------------------------------------------------


def test_review_route_requires_auth(client: FlaskClient):
    r = client.patch(
        f"/api/users/{uuid.uuid4()}/reconcile/lines/{uuid.uuid4()}/review",
        json={"review_status": "REVIEWED"},
    )
    assert r.status_code == 401


def test_owner_can_update_review_status(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)
    line_id = _new_statement(app, uid, biz, Decimal("999.9900"), date(2026, 8, 1), "Unknown Vendor")

    with app.app_context():
        run_reconciliation(uid, business_id=biz)

    tok = _login(client, MERCHANT_EMAIL)
    r = client.patch(
        f"/api/users/{uid}/reconcile/lines/{line_id}/review",
        json={"review_status": "REVIEWED"},
        headers=_headers(tok),
    )
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["review_status"] == "REVIEWED"

    with app.app_context():
        line = db.session.get(StatementLine, uuid.UUID(line_id))
        assert line.review_status == "REVIEWED"
        review_audits = [
            rec
            for rec in AuditRecord.query.filter_by(kind="reconciliation").all()
            if isinstance(rec.payload, dict)
            and rec.payload.get("action") == "review_status_update"
            and rec.payload.get("statement_line_id") == line_id
        ]
        assert len(review_audits) == 1
        assert review_audits[0].payload["review_status"] == "REVIEWED"


def test_review_route_rejects_invalid_status(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    line_id = _new_statement(app, uid, biz, Decimal("999.9900"), date(2026, 8, 1), "X")

    tok = _login(client, MERCHANT_EMAIL)
    r = client.patch(
        f"/api/users/{uid}/reconcile/lines/{line_id}/review",
        json={"review_status": "NOPE"},
        headers=_headers(tok),
    )
    assert r.status_code == 400


def test_review_route_forbids_foreign_user(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    foreign = _make_user(app, FOREIGN_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    line_id = _new_statement(app, uid, biz, Decimal("999.9900"), date(2026, 8, 1), "X")

    tok = _login(client, FOREIGN_EMAIL)
    r = client.patch(
        f"/api/users/{uid}/reconcile/lines/{line_id}/review",
        json={"review_status": "RESOLVED"},
        headers=_headers(tok),
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"


# ---------------------------------------------------------------------------
# 7. AI exception explanation route (proposal-only)
# ---------------------------------------------------------------------------


def test_explain_route_requires_auth(client: FlaskClient):
    r = client.post(
        f"/api/users/{uuid.uuid4()}/reconcile/lines/{uuid.uuid4()}/explain",
        json={},
    )
    assert r.status_code == 401


def test_owner_can_explain_exception(client: FlaskClient, app: Flask, monkeypatch):
    uid = _make_user(app, MERCHANT_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)
    line_id = _new_statement(app, uid, biz, Decimal("999.9900"), date(2026, 8, 1), "Unknown Vendor")

    with app.app_context():
        run_reconciliation(uid, business_id=biz)

    from app.services.m4 import reconciliation_explain

    def _fake_proposal(_exception):
        return {
            "explanation": "No ledger entry matches.",
            "suggested_resolution": "Verify against the bank.",
            "is_proposal": True,
        }

    monkeypatch.setattr(
        reconciliation_explain, "send_text_request", lambda *a, **k: "Fake AI reply"
    )
    monkeypatch.setattr(
        "app.services.m4.reconciliation_explain.explain_reconciliation_exception",
        _fake_proposal,
    )

    tok = _login(client, MERCHANT_EMAIL)
    r = client.post(
        f"/api/users/{uid}/reconcile/lines/{line_id}/explain",
        json={},
        headers=_headers(tok),
    )
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["is_proposal"] is True
    assert body["category"] == "MISSING_LEDGER_RECORD"
    assert body["explanation"]


def test_explain_route_only_explains_exception_lines(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    acct = _new_account(app, uid, biz)
    line_id = _new_statement(app, uid, biz, Decimal("999.9900"), date(2026, 8, 1), "X")

    tok = _login(client, MERCHANT_EMAIL)
    r = client.post(
        f"/api/users/{uid}/reconcile/lines/{line_id}/explain",
        json={},
        headers=_headers(tok),
    )
    assert r.status_code == 400
    assert "only exception lines" in r.get_json()["error"]


def test_explain_route_forbids_foreign_user(client: FlaskClient, app: Flask):
    uid = _make_user(app, MERCHANT_EMAIL)
    foreign = _make_user(app, FOREIGN_EMAIL)
    biz = _new_business(app)
    _add_member(app, biz, uid, "OWNER")
    line_id = _new_statement(app, uid, biz, Decimal("999.9900"), date(2026, 8, 1), "X")

    tok = _login(client, FOREIGN_EMAIL)
    r = client.post(
        f"/api/users/{uid}/reconcile/lines/{line_id}/explain",
        json={},
        headers=_headers(tok),
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# 8. Worker task (requires worker source on path, else skipped)
# ---------------------------------------------------------------------------

try:  # requires the worker source to be on the python path
    import tasks.reconciliation as task_module
    from celery_app import celery as celery_app
except ImportError:
    task_module = None
    celery_app = None

NEEDS_WORKER = pytest.mark.skipif(
    task_module is None,
    reason="worker task module not available in this test environment",
)

TASK_ID = str(uuid.uuid4())


@pytest.fixture()
def recon_task_env(tmp_path, monkeypatch):
    from app.config import Config

    uri = f"sqlite:///{tmp_path / 'recon_task.db'}"
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", uri)
    from app import create_app

    application = create_app(Config)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


def _recon_audit_records(app, user_id, task_id):
    with app.app_context():
        return [
            r
            for r in AuditRecord.query.filter_by(user_id=user_id, kind="reconciliation").all()
            if isinstance(r.payload, dict) and r.payload.get("task_id") == task_id
        ]


@NEEDS_WORKER
def test_task_writes_reconciliation_audit(recon_task_env):
    uid = _make_user(recon_task_env, "task@example.com")
    biz = _new_business(recon_task_env)
    _add_member(recon_task_env, biz, uid, "OWNER")
    acct = _new_account(recon_task_env, uid, biz)

    d = date(2026, 8, 1)
    _new_txn(recon_task_env, acct, Decimal("100.0000"), d, "Vendor A")
    _new_statement(recon_task_env, uid, biz, Decimal("100.0000"), d, "Vendor A")

    result = task_module.run_reconciliation_batch.apply(
        args=[uid, "bank_statement", biz], task_id=TASK_ID
    ).get()
    assert result["match_rate"] == "100.00%"
    assert result["matched_count"] == 1

    records = _recon_audit_records(recon_task_env, uid, TASK_ID)
    assert len(records) == 1
    assert records[0].payload["result"] == result


@NEEDS_WORKER
def test_task_invalid_uuid_fails_permanently(recon_task_env):
    with pytest.raises(ValueError):
        task_module.run_reconciliation_batch.apply(
            args=["not-a-uuid", "bank_statement"], task_id=TASK_ID
        ).get(propagate=True)


@NEEDS_WORKER
def test_task_is_registered_under_expected_name():
    assert celery_app.tasks.get("run_reconciliation_batch") is not None
