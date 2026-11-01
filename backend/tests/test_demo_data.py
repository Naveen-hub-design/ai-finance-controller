"""Tests for the deterministic demo-data seed (app/services/demo_data.py).

These are in-memory SQLite unit tests: they create the minimal merchant +
business the seed looks up, run the seed, and assert the deterministic,
idempotent, AI-signal-rich results. They never touch PostgreSQL, the real
demo users, the reconciliation batch, or any external provider.
"""

from decimal import Decimal

from flask import Flask
from sqlalchemy import func, select

from app.extensions import db
from app.models import Account, Budget, Business, BusinessMember, Category, FinancialGoal, Transaction, User
from app.services.demo_data import seed_demo_business
from app.services.m4.anomaly_detection import run_risk_intelligence
from app.services.m4.recommendations import run_recommendations


def _make_demo(app: Flask):
    with app.app_context():
        merchant = User(email="merchant@demo.com", full_name="Merchant Demo", role="MERCHANT")
        business = Business(name="Demo Corp")
        db.session.add(merchant)
        db.session.add(business)
        db.session.flush()
        db.session.add(BusinessMember(business_id=business.id, user_id=merchant.id, role="OWNER"))
        db.session.commit()
        return merchant, business


def test_seed_creates_expected_categories_and_accounts(app: Flask):
    _make_demo(app)
    with app.app_context():
        counts = seed_demo_business()
        assert counts["categories"] >= 5
        assert counts["accounts"] == 4
        cats = db.session.scalars(select(Category).where(Category.user_id == db.session.scalar(select(User.id).where(User.email == "merchant@demo.com")))).all()
        names = {c.name for c in cats}
        assert "Revenue" in names
        assert "Cloud Infrastructure" in names
        assert "Vendor Payments" in names


def test_seed_creates_150_plus_transactions(app: Flask):
    _make_demo(app)
    with app.app_context():
        counts = seed_demo_business()
        assert counts["transactions"] >= 150
        business = db.session.scalar(select(Business).where(Business.name == "Demo Corp"))
        total = db.session.scalar(
            select(func.count(Transaction.id))
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.business_id == business.id)
        )
        assert total >= 150


def test_seed_creates_budgets_and_goals(app: Flask):
    _make_demo(app)
    with app.app_context():
        counts = seed_demo_business()
        assert counts["budgets"] >= 4
        assert counts["goals"] == 4
        business = db.session.scalar(select(Business).where(Business.name == "Demo Corp"))
        budgets = db.session.scalars(select(Budget).where(Budget.business_id == business.id)).all()
        assert len(budgets) >= 4
        goals = db.session.scalars(select(FinancialGoal).where(FinancialGoal.business_id == business.id)).all()
        assert len(goals) == 4


def test_seed_is_idempotent(app: Flask):
    _make_demo(app)
    with app.app_context():
        first = seed_demo_business()
        merchant = db.session.scalar(select(User).where(User.email == "merchant@demo.com"))
        business = db.session.scalar(select(Business).where(Business.name == "Demo Corp"))
        txn_count = db.session.scalar(
            select(func.count(Transaction.id))
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.business_id == business.id)
        )
        second = seed_demo_business()
        txn_count_after = db.session.scalar(
            select(func.count(Transaction.id))
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.business_id == business.id)
        )
        assert second["transactions"] == 0
        assert second["accounts"] == 0
        assert second["budgets"] == 0
        assert second["goals"] == 0
        assert txn_count_after == txn_count


def test_seed_embeds_duplicate_and_large_vendor_signals(app: Flask):
    merchant, business = _make_demo(app)
    with app.app_context():
        seed_demo_business()
        dup = db.session.scalar(
            select(func.count(Transaction.id)).where(Transaction.description == "Acme Logistics")
        )
        assert dup >= 2
        large = db.session.scalar(
            select(Transaction).where(Transaction.amount == Decimal("380000"))
        )
        assert large is not None


def test_seed_feeds_deterministic_risk_and_recommendations(app: Flask):
    _make_demo(app)
    with app.app_context():
        seed_demo_business()
        merchant = db.session.scalar(select(User).where(User.email == "merchant@demo.com"))
        business = db.session.scalar(select(Business).where(Business.name == "Demo Corp"))
        signals = run_risk_intelligence(merchant.id, business.id)
        assert signals, "risk intelligence should return findings on the seeded data"
        types = {s["type"] for s in signals}
        assert "DUPLICATE_CANDIDATE" in types
        assert "LARGE_AMOUNT" in types
        recs = run_recommendations(merchant.id, business.id)
        assert isinstance(recs, list)


def test_seed_is_business_scoped_and_additive(app: Flask):
    _make_demo(app)
    with app.app_context():
        merchant = db.session.scalar(select(User).where(User.email == "merchant@demo.com"))
        business = db.session.scalar(select(Business).where(Business.name == "Demo Corp"))
        # Add a second business that must NOT receive the seeded data.
        other = Business(name="Separate Corp")
        db.session.add(other)
        db.session.flush()
        db.session.add(BusinessMember(business_id=other.id, user_id=merchant.id, role="OWNER"))
        db.session.commit()

        seed_demo_business()

        other_txns = db.session.scalar(
            select(func.count(Transaction.id))
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.business_id == other.id)
        )
        assert other_txns == 0


def test_seed_lookup_is_scoped_to_merchant_membership(app: Flask):
    """The demo business is resolved through the merchant's OWNER membership.

    Regression: a global ``Business.name == "Demo Corp"`` lookup can return an
    unrelated user's same-named business (arbitrary first match), leaking the
    merchant's seeded accounts/transactions into a foreign tenant. The seed
    must never populate a business the merchant does not own.
    """
    with app.app_context():
        outsider = User(email="outsider@demo.com", role="MERCHANT")
        outsider_biz = Business(name="Demo Corp")
        db.session.add(outsider)
        db.session.add(outsider_biz)
        db.session.flush()
        db.session.add(
            BusinessMember(business_id=outsider_biz.id, user_id=outsider.id, role="OWNER")
        )

        merchant = User(email="merchant@demo.com", role="MERCHANT")
        merchant_biz = Business(name="Demo Corp")
        db.session.add(merchant)
        db.session.add(merchant_biz)
        db.session.flush()
        db.session.add(
            BusinessMember(business_id=merchant_biz.id, user_id=merchant.id, role="OWNER")
        )
        db.session.commit()

        seed_demo_business()

        outsider_accounts = db.session.scalar(
            select(func.count(Account.id)).where(
                Account.business_id == outsider_biz.id
            )
        )
        merchant_accounts = db.session.scalar(
            select(func.count(Account.id)).where(
                Account.business_id == merchant_biz.id
            )
        )
        outsider_txns = db.session.scalar(
            select(func.count(Transaction.id))
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.business_id == outsider_biz.id)
        )
        merchant_txns = db.session.scalar(
            select(func.count(Transaction.id))
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.business_id == merchant_biz.id)
        )

        assert outsider_accounts == 0
        assert outsider_txns == 0
        assert merchant_accounts == 4
        assert merchant_txns >= 150
