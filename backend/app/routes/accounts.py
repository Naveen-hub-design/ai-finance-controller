"""Account API endpoints (Milestone 3.2)."""

import uuid
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..models import Account, User

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")

VALID_ACCOUNT_TYPES = {
    "bank",
    "cash",
    "credit_card",
    "investment",
    "loan",
    "other",
}


def _serialize_account(account: Account) -> dict:
    return {
        "id": str(account.id),
        "user_id": str(account.user_id),
        "name": account.name,
        "account_type": account.account_type,
        "currency": account.currency,
        "current_balance": str(account.current_balance),
        "created_at": account.created_at.isoformat(),
        "updated_at": account.updated_at.isoformat(),
    }


@accounts_bp.post("")
def create_account():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    user_id_raw = payload.get("user_id")
    name = payload.get("name")
    account_type = payload.get("account_type")
    currency = payload.get("currency", "INR")
    balance_raw = payload.get("current_balance", "0")

    try:
        user_id = uuid.UUID(str(user_id_raw))
    except (ValueError, AttributeError, TypeError):
        return {"error": "user_id must be a valid UUID"}, 400

    if not isinstance(name, str) or not name.strip():
        return {"error": "name is required"}, 400

    name = name.strip()

    if account_type not in VALID_ACCOUNT_TYPES:
        return {"error": "invalid account_type"}, 400

    if not isinstance(currency, str) or len(currency.strip()) != 3:
        return {"error": "currency must be a 3-letter code"}, 400

    currency = currency.strip().upper()

    try:
        balance = Decimal(str(balance_raw))
    except (InvalidOperation, ValueError, TypeError):
        return {"error": "current_balance must be a valid number"}, 400

    if balance < 0:
        return {"error": "current_balance cannot be negative"}, 400

    try:
        user = db.session.get(User, user_id)

        if user is None:
            return {"error": "user not found"}, 404

        account = Account(
            user_id=user_id,
            name=name,
            account_type=account_type,
            currency=currency,
            current_balance=balance,
        )

        db.session.add(account)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception("account creation integrity error")
        return {"error": "account could not be created"}, 409

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("account creation failed")
        return {"error": "internal server error"}, 500

    return _serialize_account(account), 201


@accounts_bp.get("/<uuid:account_id>")
def get_account(account_id: uuid.UUID):
    try:
        account = db.session.get(Account, account_id)
    except SQLAlchemyError:
        current_app.logger.exception("account lookup failed")
        return {"error": "internal server error"}, 500

    if account is None:
        return {"error": "account not found"}, 404

    return _serialize_account(account), 200
