"""User API endpoints (Milestone 3.1)."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import create_access_token, jwt_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..models import User
from ._ownership import require_owner_or
from ._authorization import (
    FINANCE_MANAGER,
    MERCHANT,
    PLATFORM_ADMIN,
    require_role,
)

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

EMAIL_ALREADY_EXISTS = "a user with this email already exists"


def _serialize_user(user: User) -> dict[str, str | None]:
    """Return the public representation of a user."""
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


@users_bp.post("")
def create_user() -> tuple[dict[str, str], int]:
    """Register a new user."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        return {"error": "email is required"}, 400
    email = email.strip().lower()

    full_name = payload.get("full_name")
    if full_name is not None and not isinstance(full_name, str):
        return {"error": "full_name must be a string"}, 400
    if isinstance(full_name, str):
        full_name = full_name.strip() or None

    password = payload.get("password")
    if not isinstance(password, str) or not password.strip():
        return {"error": "password is required"}, 400

    try:
        existing = db.session.scalar(select(User).where(User.email == email))
        if existing is not None:
            return {"error": EMAIL_ALREADY_EXISTS}, 409

        # role is NEVER accepted from the client on registration; everyone
        # starts as MERCHANT and can only be elevated by a PLATFORM_ADMIN.
        if "role" in payload:
            return {"error": "forbidden"}, 403

        user = User(email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        # Concurrent insert raced past the uniqueness pre-check.
        db.session.rollback()
        return {"error": EMAIL_ALREADY_EXISTS}, 409
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("user creation failed")
        return {"error": "internal server error"}, 500

    return _serialize_user(user), 201


@users_bp.post("/login")
def login_user() -> tuple[dict[str, str | None], int]:
    """Authenticate a user with email + password.

    Returns the serialized user plus a short-lived JWT access token on
    success. On failure (unknown email or incorrect password) it returns the
    same generic error so callers cannot tell whether the email exists, and
    no internal details are leaked.
    """
    INVALID_CREDENTIALS = "invalid email or password"

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        return {"error": INVALID_CREDENTIALS}, 401
    email = email.strip().lower()

    password = payload.get("password")
    if not isinstance(password, str) or not password:
        return {"error": INVALID_CREDENTIALS}, 401

    try:
        user = db.session.scalar(select(User).where(User.email == email))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("login lookup failed")
        return {"error": "internal server error"}, 500

    if user is None or not user.check_password(password):
        return {"error": INVALID_CREDENTIALS}, 401

    access_token = create_access_token(identity=str(user.id))
    return {"user": _serialize_user(user), "access_token": access_token}, 200


def _seed_demo_data():
    from datetime import date
    from decimal import Decimal
    from ..models import User, Business, BusinessMember, Account, Transaction, Category, Budget, FinancialGoal, StatementLine
    
    # Check if users already exist
    admin = db.session.scalar(select(User).where(User.email == "admin@demo.com"))
    merchant = db.session.scalar(select(User).where(User.email == "merchant@demo.com"))
    finance = db.session.scalar(select(User).where(User.email == "finance@demo.com"))

    if not admin:
        admin = User(email="admin@demo.com", role="PLATFORM_ADMIN")
        admin.set_password("demo-password-123")
        db.session.add(admin)
    if not merchant:
        merchant = User(email="merchant@demo.com", role="MERCHANT")
        merchant.set_password("demo-password-123")
        db.session.add(merchant)
    if not finance:
        finance = User(email="finance@demo.com", role="FINANCE_MANAGER")
        finance.set_password("demo-password-123")
        db.session.add(finance)

    db.session.commit()

    # Resolve the demo business strictly through the merchant's OWNER
    # membership. A global name lookup could bind demo data to another user's
    # "Demo Corp", leaking seed rows across tenants. When absent, create the
    # merchant's own Demo Corp and make the merchant its OWNER.
    business = db.session.scalar(
        select(Business)
        .join(BusinessMember, BusinessMember.business_id == Business.id)
        .where(
            BusinessMember.user_id == merchant.id,
            BusinessMember.role == "OWNER",
            Business.name.in_(["Apex Global Technologies", "Demo Corp"]),
        )
        .order_by(Business.created_at.asc())
        .limit(1)
    )
    if business is None:
        business = Business(name="Demo Corp")
        db.session.add(business)
        db.session.flush()
        db.session.add(
            BusinessMember(business_id=business.id, user_id=merchant.id, role="OWNER")
        )
        db.session.commit()

    # Ensure the finance manager is a member (idempotent), so a partial earlier
    # run can never leave the demo FM without access to the demo business.
    fm_membership = db.session.scalar(
        select(BusinessMember).where(
            BusinessMember.business_id == business.id,
            BusinessMember.user_id == finance.id,
        )
    )
    if fm_membership is None:
        db.session.add(
            BusinessMember(
                business_id=business.id, user_id=finance.id, role="FINANCE_MANAGER"
            )
        )
        db.session.commit()

    # Check categories
    merchant_cats = db.session.scalars(select(Category).where(Category.user_id == merchant.id)).all()
    if not merchant_cats:
        cats = [
            Category(user_id=merchant.id, name="Salary", category_type="income"),
            Category(user_id=merchant.id, name="Rent", category_type="expense"),
            Category(user_id=merchant.id, name="Utilities", category_type="expense"),
            Category(user_id=merchant.id, name="Office Supplies", category_type="expense"),
            Category(user_id=merchant.id, name="Marketing", category_type="expense"),
        ]
        db.session.add_all(cats)
        db.session.commit()
        merchant_cats = cats

    # Check accounts (scoped to the merchant's demo business -- never a global
    # account-name lookup).
    biz_acc = db.session.scalar(
        select(Account)
        .where(Account.name == "Main Business Bank Account")
        .where(Account.user_id == merchant.id)
        .where(Account.business_id == business.id)
        .limit(1)
    )
    if not biz_acc:
        biz_acc = Account(
            user_id=merchant.id,
            business_id=business.id,
            name="Main Business Bank Account",
            account_type="bank",
            currency="INR",
            current_balance=Decimal("550000.00")
        )
        db.session.add(biz_acc)
        
        pers_acc = Account(
            user_id=merchant.id,
            name="Personal Wallet",
            account_type="cash",
            currency="INR",
            current_balance=Decimal("15000.00")
        )
        db.session.add(pers_acc)
        db.session.commit()

        # Add transactions for Business
        rent_cat = next(c for c in merchant_cats if c.name == "Rent")
        supplies_cat = next(c for c in merchant_cats if c.name == "Office Supplies")
        marketing_cat = next(c for c in merchant_cats if c.name == "Marketing")
        salary_cat = next(c for c in merchant_cats if c.name == "Salary")

        txs = [
            Transaction(account_id=biz_acc.id, category_id=salary_cat.id, amount=Decimal("100000.00"), transaction_type="income", description="Client Project Payment", transaction_date=date(2026, 8, 1)),
            Transaction(account_id=biz_acc.id, category_id=rent_cat.id, amount=Decimal("30000.00"), transaction_type="expense", description="Office Rent", transaction_date=date(2026, 8, 2)),
            Transaction(account_id=biz_acc.id, category_id=supplies_cat.id, amount=Decimal("5000.00"), transaction_type="expense", description="Stationery", transaction_date=date(2026, 8, 5)),
            Transaction(account_id=biz_acc.id, category_id=marketing_cat.id, amount=Decimal("15000.00"), transaction_type="expense", description="Google Ads", transaction_date=date(2026, 8, 10)),
        ]
        db.session.add_all(txs)

        ptxs = [
            Transaction(account_id=pers_acc.id, category_id=rent_cat.id, amount=Decimal("12000.00"), transaction_type="expense", description="Home Rent", transaction_date=date(2026, 8, 3)),
        ]
        db.session.add_all(ptxs)
        db.session.commit()

        # Add budgets
        b1 = Budget(
            user_id=merchant.id,
            business_id=business.id,
            category_id=marketing_cat.id,
            amount=Decimal("20000.00"),
            period="monthly",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31)
        )
        db.session.add(b1)
        db.session.commit()

        # Add goals
        g1 = FinancialGoal(
            user_id=merchant.id,
            business_id=business.id,
            name="Quarterly Tax Reserves",
            target_amount=Decimal("150000.00"),
            current_amount=Decimal("75000.00"),
            target_date=date(2026, 12, 31),
            status="active"
        )
        db.session.add(g1)
        db.session.commit()

    _seed_reconciliation_batch(merchant, business)

    # Populate the deterministic, idempotent realistic SMB dataset (accounts,
    # categories, 150+ transactions across Jan-Jun, budgets, goals). This is
    # additive and never disturbs the reconciliation batch above.
    from ..services.demo_data import seed_demo_business
    seed_demo_business()


def _seed_reconciliation_batch(merchant, business):
    """Seed a 75+ record synthetic batch for the reconciliation agent.

    Creates the internal ledger (source A) entries and the matching external
    statement lines (source B) for the merchant's business, so the finance-ops
    reconciliation loop can run across a real 75+ record batch and report a
    match rate plus unresolved exceptions.

    The batch is deterministic (no randomness) and idempotent: statement lines
    are only created the first time they are absent for the source/business.
    It intentionally contains SUCCESS and FAILURE:

    - 74 exact-match lines (matched)
    - 3 amount mismatches   (same date + description, different amount)
    - 3 date mismatches     (same amount + description, different date)
    - 2 duplicate pairs     (one ledger entry claimed by two identical lines)
    - 4 missing ledger records (amount/date/description near nothing)

    Fresh setups therefore report 76/88 matched = 86.36% with 12 exceptions
    spanning four deterministic categories. The already-seeded live demo batch
    (44/55 = 80.00%) is left untouched by the idempotency guard.
    """
    from datetime import date
    from decimal import Decimal
    from ..models import Account, Transaction, StatementLine

    biz_acc = db.session.scalar(
        select(Account)
        .where(Account.name == "Main Business Bank Account")
        .where(Account.user_id == merchant.id)
        .where(Account.business_id == business.id)
        .limit(1)
    )
    if biz_acc is None:
        return

    existing = db.session.scalar(
        select(StatementLine)
        .where(StatementLine.user_id == merchant.id)
        .where(StatementLine.business_id == business.id)
        .where(StatementLine.source == "bank_statement")
        .limit(1)
    )
    if existing is not None:
        return

    vendors = [
        "AWS Hosting",
        "Client Retainer",
        "Office Supplies Co",
        "Marketing Agency",
        "Software License",
        "Travel & Logistics",
        "Legal Counsel",
        "Equipment Lease",
        "Freelance Contractor",
        "Cloud Storage",
    ]

    # Source A: 82 internal ledger entries. Amount/dates are deterministic.
    ledger_txs = [
        Transaction(
            account_id=biz_acc.id,
            amount=Decimal((i + 1) * 500),
            transaction_type="expense",
            description=vendors[i % len(vendors)],
            transaction_date=date(2026, 8, 1 + (i % 25)),
        )
        for i in range(82)
    ]
    db.session.add_all(ledger_txs)
    db.session.commit()

    def _line(tx, amount, ref):
        return StatementLine(
            user_id=merchant.id,
            business_id=business.id,
            source="bank_statement",
            external_reference=ref,
            amount=amount,
            transaction_date=tx.transaction_date,
            description=tx.description,
        )

    statement_lines = []

    # 74 exact-match lines (matched against ledger entries L0..L73).
    for i, tx in enumerate(ledger_txs[:74]):
        statement_lines.append(
            StatementLine(
                user_id=merchant.id,
                business_id=business.id,
                source="bank_statement",
                external_reference=f"BANK-REF-{1000 + i}",
                amount=tx.amount,
                transaction_date=tx.transaction_date,
                description=tx.description,
            )
        )

    # 3 AMOUNT_MISMATCH: same date + description, different amount.
    for i in (74, 76, 78):
        tx = ledger_txs[i]
        statement_lines.append(
            StatementLine(
                user_id=merchant.id,
                business_id=business.id,
                source="bank_statement",
                external_reference=f"BANK-AMT-{i}",
                amount=tx.amount + Decimal("250"),
                transaction_date=tx.transaction_date,
                description=tx.description,
            )
        )

    # 3 DATE_MISMATCH: same amount + description, different date.
    for i in (75, 77, 79):
        tx = ledger_txs[i]
        statement_lines.append(
            StatementLine(
                user_id=merchant.id,
                business_id=business.id,
                source="bank_statement",
                external_reference=f"BANK-DATE-{i}",
                amount=tx.amount,
                transaction_date=date.fromordinal(tx.transaction_date.toordinal() + 1),
                description=tx.description,
            )
        )

    # 2 DUPLICATE_RECORD pairs: one ledger entry claimed by two identical lines.
    for i in (80, 81):
        tx = ledger_txs[i]
        for dup in range(2):
            statement_lines.append(
                StatementLine(
                    user_id=merchant.id,
                    business_id=business.id,
                    source="bank_statement",
                    external_reference=f"BANK-DUP-{i}-{dup}",
                    amount=tx.amount,
                    transaction_date=tx.transaction_date,
                    description=tx.description,
                )
            )

    # 4 MISSING_LEDGER_RECORD: amount/date/description near nothing.
    missing = [
        (Decimal("310"), date(2026, 8, 26), "Unknown Vendor 1"),
        (Decimal("7777"), date(2026, 8, 27), "Unknown Vendor 2"),
        (Decimal("12345"), date(2026, 8, 28), "Unknown Vendor 3"),
        (Decimal("54321"), date(2026, 8, 29), "Unknown Vendor 4"),
    ]
    for idx, (amount, d, desc) in enumerate(missing):
        statement_lines.append(
            StatementLine(
                user_id=merchant.id,
                business_id=business.id,
                source="bank_statement",
                external_reference=f"BANK-MISS-{idx + 1}",
                amount=amount,
                transaction_date=d,
                description=desc,
            )
        )

    db.session.add_all(statement_lines)
    db.session.commit()


@users_bp.post("/demo-login")
def demo_login():
    import os
    if current_app.config.get("SECRET_KEY") != "dev-only-not-for-production" or os.environ.get("FLASK_ENV") == "production":
        return {"error": "forbidden"}, 403

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    role = payload.get("role")
    if role not in ("PLATFORM_ADMIN", "MERCHANT", "FINANCE_MANAGER"):
        return {"error": "invalid role requested"}, 400

    try:
        _seed_demo_data()

        email = {
            "PLATFORM_ADMIN": "admin@demo.com",
            "MERCHANT": "merchant@demo.com",
            "FINANCE_MANAGER": "finance@demo.com",
        }[role]

        user = db.session.scalar(select(User).where(User.email == email))
        if user is None:
            return {"error": "demo user not found after seed"}, 500

        access_token = create_access_token(identity=str(user.id))
        return {"user": _serialize_user(user), "access_token": access_token}, 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("demo login or seed failed")
        return {"error": "internal server error"}, 500


@users_bp.get("/<uuid:user_id>")
@jwt_required()
def get_user(user_id: uuid.UUID) -> tuple[dict[str, str | None], int]:
    """Fetch a single user by id (owner only)."""
    forbidden = require_owner_or(user_id)
    if forbidden is not None:
        return forbidden

    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404
    return _serialize_user(user), 200


@users_bp.put("/<uuid:user_id>")
@jwt_required()
def update_user(user_id: uuid.UUID) -> tuple[dict[str, str | None], int]:
    """Update a user's email and/or full_name (owner only)."""
    forbidden = require_owner_or(user_id)
    if forbidden is not None:
        return forbidden

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    # role can never be changed via a normal user update (no self-elevation);
    # only PLATFORM_ADMIN may assign roles through the admin endpoint.
    if "role" in payload:
        return {"error": "forbidden"}, 403

    if "email" in payload:
        email = payload["email"]
        if not isinstance(email, str) or not email.strip():
            return {"error": "email is required"}, 400
        email = email.strip().lower()

        if email != user.email:
            existing = db.session.scalar(
                select(User).where(User.email == email)
            )
            if existing is not None:
                return {"error": EMAIL_ALREADY_EXISTS}, 409
            user.email = email

    if "full_name" in payload:
        full_name = payload["full_name"]
        if full_name is not None and not isinstance(full_name, str):
            return {"error": "full_name must be a string"}, 400
        if isinstance(full_name, str):
            full_name = full_name.strip() or None
        user.full_name = full_name

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": EMAIL_ALREADY_EXISTS}, 409
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("user update failed")
        return {"error": "internal server error"}, 500

    return _serialize_user(user), 200


@users_bp.delete("/<uuid:user_id>")
@jwt_required()
def delete_user(user_id: uuid.UUID) -> tuple[dict[str, str], int]:
    """Delete a user and cascade to owned entities (owner only)."""
    forbidden = require_owner_or(user_id)
    if forbidden is not None:
        return forbidden

    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    try:
        db.session.delete(user)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("user deletion failed")
        return {"error": "internal server error"}, 500

    return "", 204


@users_bp.get("")
@jwt_required()
def list_users() -> tuple[dict, int]:
    """List all users (PLATFORM_ADMIN only)."""
    forbidden = require_role(PLATFORM_ADMIN)
    if forbidden is not None:
        return forbidden

    try:
        users = db.session.scalars(
            select(User).order_by(User.created_at.asc(), User.id.asc())
        ).all()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("user list failed")
        return {"error": "internal server error"}, 500

    return {"users": [_serialize_user(u) for u in users]}, 200


@users_bp.patch("/<uuid:user_id>/role")
@jwt_required()
def update_user_role(user_id: uuid.UUID) -> tuple[dict, int]:
    """Assign a user's application role (PLATFORM_ADMIN only).

    The caller must be a PLATFORM_ADMIN. Only valid roles may be assigned;
    nobody (including a PLATFORM_ADMIN) may demote the last PLATFORM_ADMIN to
    avoid locking the platform out of administration. A PLATFORM_ADMIN cannot
    be assigned as a business member role (that is enforced by the business
    routes).
    """
    forbidden = require_role(PLATFORM_ADMIN)
    if forbidden is not None:
        return forbidden

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    role = payload.get("role")
    if role not in (PLATFORM_ADMIN, MERCHANT, FINANCE_MANAGER):
        return {"error": "invalid role"}, 400

    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        # Do not reveal whether the target exists; generic 404 without detail.
        return {"error": "user not found"}, 404

    # Prevent demoting the final PLATFORM_ADMIN.
    if user.role == PLATFORM_ADMIN and role != PLATFORM_ADMIN:
        try:
            admin_count = db.session.scalar(
                select(db.func.count(User.id)).where(
                    User.role == PLATFORM_ADMIN
                )
            )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("admin count failed")
            return {"error": "internal server error"}, 500
        if admin_count is not None and int(admin_count) <= 1:
            return {"error": "cannot demote the last platform admin"}, 409

    try:
        user.role = role
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("role update failed")
        return {"error": "internal server error"}, 500

    return _serialize_user(user), 200

