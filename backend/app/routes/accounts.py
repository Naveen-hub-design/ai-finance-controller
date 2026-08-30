"""Account API endpoints (Milestone 3.2)."""

import uuid
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..auth import get_current_user_id
from ..extensions import db
from ..models import Account, User
from ._ownership import require_owner_or
from .users import users_bp

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
@jwt_required()
def create_account():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    current_user_id = get_current_user_id()

    user_id_raw = payload.get("user_id")
    name = payload.get("name")
    account_type = payload.get("account_type")
    currency = payload.get("currency", "INR")
    balance_raw = payload.get("current_balance", "0")

    # The authenticated identity is the authoritative owner. A client-supplied
    # user_id is never trusted as ownership; a mismatched one is rejected so a
    # caller cannot create a resource for another user.
    if user_id_raw is not None:
        try:
            supplied_user_id = uuid.UUID(str(user_id_raw))
        except (ValueError, AttributeError, TypeError):
            return {"error": "user_id must be a valid UUID"}, 400
        if supplied_user_id != current_user_id:
            return {"error": "forbidden"}, 403

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
        user = db.session.get(User, current_user_id)

        if user is None:
            return {"error": "user not found"}, 404

        account = Account(
            user_id=current_user_id,
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
@jwt_required()
def get_account(account_id: uuid.UUID):
    try:
        account = db.session.get(Account, account_id)
    except SQLAlchemyError:
        current_app.logger.exception("account lookup failed")
        return {"error": "internal server error"}, 500

    if account is None:
        return {"error": "account not found"}, 404

    forbidden = require_owner_or(account.user_id)
    if forbidden is not None:
        return forbidden

    return _serialize_account(account), 200


@accounts_bp.put("/<uuid:account_id>")
@jwt_required()
def update_account(account_id: uuid.UUID):
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    try:
        account = db.session.get(Account, account_id)
    except SQLAlchemyError:
        current_app.logger.exception("account lookup failed")
        return {"error": "internal server error"}, 500

    if account is None:
        return {"error": "account not found"}, 404

    forbidden = require_owner_or(account.user_id)
    if forbidden is not None:
        return forbidden

    # Ownership cannot be transferred via the request body.
    if "user_id" in payload:
        if isinstance(payload["user_id"], str) and payload["user_id"]:
            return {"error": "forbidden"}, 403
        return {"error": "forbidden"}, 403

    if "name" in payload:
        name = payload["name"]
        if not isinstance(name, str) or not name.strip():
            return {"error": "name is required"}, 400
        account.name = name.strip()

    if "account_type" in payload:
        account_type = payload["account_type"]
        if account_type not in VALID_ACCOUNT_TYPES:
            return {"error": "invalid account_type"}, 400
        account.account_type = account_type

    if "currency" in payload:
        currency = payload["currency"]
        if not isinstance(currency, str) or len(currency.strip()) != 3:
            return {"error": "currency must be a 3-letter code"}, 400
        account.currency = currency.strip().upper()

    if "current_balance" in payload:
        try:
            balance = Decimal(str(payload["current_balance"]))
        except (InvalidOperation, ValueError, TypeError):
            return {"error": "current_balance must be a valid number"}, 400
        if balance < 0:
            return {"error": "current_balance cannot be negative"}, 400
        account.current_balance = balance

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("account update failed")
        return {"error": "internal server error"}, 500

    return _serialize_account(account), 200


@accounts_bp.delete("/<uuid:account_id>")
@jwt_required()
def delete_account(account_id: uuid.UUID):
    try:
        account = db.session.get(Account, account_id)
    except SQLAlchemyError:
        current_app.logger.exception("account lookup failed")
        return {"error": "internal server error"}, 500

    if account is None:
        return {"error": "account not found"}, 404

    forbidden = require_owner_or(account.user_id)
    if forbidden is not None:
        return forbidden

    try:
        db.session.delete(account)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("account deletion failed")
        return {"error": "internal server error"}, 500

    return "", 204


@users_bp.get("/<uuid:user_id>/accounts")
@jwt_required()
def list_accounts(user_id: uuid.UUID):
    """List all accounts belonging to a user (owner only)."""
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
        accounts = (
            db.session.execute(
                select(Account)
                .where(Account.user_id == user_id)
                .order_by(Account.created_at.asc(), Account.id.asc())
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        current_app.logger.exception("account list failed")
        return {"error": "internal server error"}, 500

    return {
        "user_id": str(user_id),
        "accounts": [_serialize_account(account) for account in accounts],
    }, 200
