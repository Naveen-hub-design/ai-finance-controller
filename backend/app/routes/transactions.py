"""Transaction API endpoints (Milestone 3.3)."""

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..auth import get_current_user_id
from ..extensions import db
from ..models import Account, Category, Transaction, User
from ._ownership import require_owner_or
from .users import users_bp

transactions_bp = Blueprint(
    "transactions",
    __name__,
    url_prefix="/api/transactions",
)

VALID_TRANSACTION_TYPES = {
    "income",
    "expense",
    "transfer",
}


def _serialize_transaction(transaction: Transaction) -> dict:
    return {
        "id": str(transaction.id),
        "account_id": str(transaction.account_id),
        "category_id": (
            str(transaction.category_id)
            if transaction.category_id is not None
            else None
        ),
        "amount": str(transaction.amount),
        "transaction_type": transaction.transaction_type,
        "description": transaction.description,
        "transaction_date": transaction.transaction_date.isoformat(),
        "created_at": transaction.created_at.isoformat(),
    }


def _transaction_owner_id(transaction: Transaction):
    """Return the user id that owns ``transaction`` (via its account).

    Resolves the Transaction -> Account -> User chain so ownership is never
    inferred from any client-supplied value.
    """
    account = db.session.get(Account, transaction.account_id)
    return account.user_id if account is not None else None


@transactions_bp.post("")
@jwt_required()
def create_transaction():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    current_user_id = get_current_user_id()

    account_id_raw = payload.get("account_id")
    category_id_raw = payload.get("category_id")
    amount_raw = payload.get("amount")
    transaction_type = payload.get("transaction_type")
    description = payload.get("description")
    transaction_date_raw = payload.get("transaction_date")

    try:
        account_id = uuid.UUID(str(account_id_raw))
    except (ValueError, AttributeError, TypeError):
        return {"error": "account_id must be a valid UUID"}, 400

    category_id = None

    if category_id_raw is not None:
        try:
            category_id = uuid.UUID(str(category_id_raw))
        except (ValueError, AttributeError, TypeError):
            return {"error": "category_id must be a valid UUID"}, 400

    if transaction_type not in VALID_TRANSACTION_TYPES:
        return {"error": "invalid transaction_type"}, 400

    try:
        amount = Decimal(str(amount_raw))
    except (InvalidOperation, ValueError, TypeError):
        return {"error": "amount must be a valid number"}, 400

    if amount <= 0:
        return {"error": "amount must be greater than zero"}, 400

    if description is not None and not isinstance(description, str):
        return {"error": "description must be a string"}, 400

    if isinstance(description, str):
        description = description.strip() or None

    try:
        transaction_date = date.fromisoformat(str(transaction_date_raw))
    except (ValueError, TypeError):
        return {"error": "transaction_date must be YYYY-MM-DD"}, 400

    try:
        account = db.session.get(Account, account_id)

        if account is None:
            return {"error": "account not found"}, 404

        if account.user_id != current_user_id:
            return {"error": "forbidden"}, 403

        if category_id is not None:
            category = db.session.get(Category, category_id)

            if category is None:
                return {"error": "category not found"}, 404

            if category.user_id != account.user_id:
                return {"error": "category does not belong to user"}, 400

        transaction = Transaction(
            account_id=account_id,
            category_id=category_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            transaction_date=transaction_date,
        )

        db.session.add(transaction)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception("transaction creation integrity error")
        return {"error": "transaction could not be created"}, 409

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("transaction creation failed")
        return {"error": "internal server error"}, 500

    return _serialize_transaction(transaction), 201


@transactions_bp.get("/<uuid:transaction_id>")
@jwt_required()
def get_transaction(transaction_id: uuid.UUID):
    try:
        transaction = db.session.get(Transaction, transaction_id)
    except SQLAlchemyError:
        current_app.logger.exception("transaction lookup failed")
        return {"error": "internal server error"}, 500

    if transaction is None:
        return {"error": "transaction not found"}, 404

    forbidden = require_owner_or(_transaction_owner_id(transaction))
    if forbidden is not None:
        return forbidden

    return _serialize_transaction(transaction), 200


@transactions_bp.put("/<uuid:transaction_id>")
@jwt_required()
def update_transaction(transaction_id: uuid.UUID):
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    try:
        transaction = db.session.get(Transaction, transaction_id)
    except SQLAlchemyError:
        current_app.logger.exception("transaction lookup failed")
        return {"error": "internal server error"}, 500

    if transaction is None:
        return {"error": "transaction not found"}, 404

    forbidden = require_owner_or(_transaction_owner_id(transaction))
    if forbidden is not None:
        return forbidden

    # The authenticated identity is the authoritative owner. Any target
    # account/category the transaction is attached to must belong to it.
    current_user_id = get_current_user_id()

    try:
        if "account_id" in payload:
            try:
                new_account_id = uuid.UUID(str(payload["account_id"]))
            except (ValueError, AttributeError, TypeError):
                return {"error": "account_id must be a valid UUID"}, 400
            account = db.session.get(Account, new_account_id)
            if account is None:
                return {"error": "account not found"}, 404
            if account.user_id != current_user_id:
                return {"error": "forbidden"}, 403
            transaction.account_id = new_account_id

        if "category_id" in payload:
            category_id_raw = payload["category_id"]
            if category_id_raw is None:
                transaction.category_id = None
            else:
                try:
                    new_category_id = uuid.UUID(str(category_id_raw))
                except (ValueError, AttributeError, TypeError):
                    return {"error": "category_id must be a valid UUID"}, 400
                category = db.session.get(Category, new_category_id)
                if category is None:
                    return {"error": "category not found"}, 404
                account = db.session.get(Account, transaction.account_id)
                if category.user_id != account.user_id:
                    return {"error": "category does not belong to user"}, 400
                transaction.category_id = new_category_id

        if "amount" in payload:
            try:
                amount = Decimal(str(payload["amount"]))
            except (InvalidOperation, ValueError, TypeError):
                return {"error": "amount must be a valid number"}, 400
            if amount <= 0:
                return {"error": "amount must be greater than zero"}, 400
            transaction.amount = amount

        if "transaction_type" in payload:
            if payload["transaction_type"] not in VALID_TRANSACTION_TYPES:
                return {"error": "invalid transaction_type"}, 400
            transaction.transaction_type = payload["transaction_type"]

        if "description" in payload:
            description = payload["description"]
            if description is not None and not isinstance(description, str):
                return {"error": "description must be a string"}, 400
            if isinstance(description, str):
                description = description.strip() or None
            transaction.description = description

        if "transaction_date" in payload:
            try:
                transaction.transaction_date = date.fromisoformat(
                    str(payload["transaction_date"])
                )
            except (ValueError, TypeError):
                return {"error": "transaction_date must be YYYY-MM-DD"}, 400

        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("transaction update failed")
        return {"error": "internal server error"}, 500

    return _serialize_transaction(transaction), 200


@transactions_bp.delete("/<uuid:transaction_id>")
@jwt_required()
def delete_transaction(transaction_id: uuid.UUID):
    try:
        transaction = db.session.get(Transaction, transaction_id)
    except SQLAlchemyError:
        current_app.logger.exception("transaction lookup failed")
        return {"error": "internal server error"}, 500

    if transaction is None:
        return {"error": "transaction not found"}, 404

    forbidden = require_owner_or(_transaction_owner_id(transaction))
    if forbidden is not None:
        return forbidden

    try:
        db.session.delete(transaction)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("transaction deletion failed")
        return {"error": "internal server error"}, 500

    return "", 204


@users_bp.get("/<uuid:user_id>/transactions")
@jwt_required()
def list_transactions(user_id: uuid.UUID):
    """List a user's transactions with optional filters and pagination.

    Returns only transactions on accounts owned by ``user_id`` and does not
    trust any client-supplied ownership hint. Owner only.
    """
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

    transaction_type = request.args.get("transaction_type")
    if transaction_type is not None:
        transaction_type = transaction_type.strip()
        if transaction_type not in VALID_TRANSACTION_TYPES:
            return {"error": "invalid transaction_type"}, 400

    date_from = None
    date_from_raw = request.args.get("date_from")
    if date_from_raw is not None:
        try:
            date_from = date.fromisoformat(date_from_raw)
        except (ValueError, TypeError):
            return {"error": "date_from must be YYYY-MM-DD"}, 400

    date_to = None
    date_to_raw = request.args.get("date_to")
    if date_to_raw is not None:
        try:
            date_to = date.fromisoformat(date_to_raw)
        except (ValueError, TypeError):
            return {"error": "date_to must be YYYY-MM-DD"}, 400

    if date_from is not None and date_to is not None and date_from > date_to:
        return {"error": "date_from cannot be after date_to"}, 400

    search = request.args.get("search")
    if search is not None:
        search = search.strip()
        if search == "":
            search = None

    try:
        page = int(request.args.get("page", "1"))
    except (ValueError, TypeError):
        return {"error": "page must be a positive integer"}, 400
    if page < 1:
        return {"error": "page must be a positive integer"}, 400

    try:
        page_size = int(request.args.get("page_size", "25"))
    except (ValueError, TypeError):
        return {"error": "page_size must be an integer between 1 and 100"}, 400
    if page_size < 1 or page_size > 100:
        return {"error": "page_size must be an integer between 1 and 100"}, 400

    conditions = [Account.user_id == user_id]
    if transaction_type is not None:
        conditions.append(Transaction.transaction_type == transaction_type)
    if date_from is not None:
        conditions.append(Transaction.transaction_date >= date_from)
    if date_to is not None:
        conditions.append(Transaction.transaction_date <= date_to)
    if search is not None:
        conditions.append(
            func.lower(Transaction.description).contains(search.lower())
        )

    try:
        total = db.session.execute(
            select(func.count(Transaction.id))
            .join(Account, Transaction.account_id == Account.id)
            .where(*conditions)
        ).scalar_one()

        offset = (page - 1) * page_size
        transactions = (
            db.session.execute(
                select(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .where(*conditions)
                .order_by(
                    Transaction.transaction_date.desc(),
                    Transaction.created_at.desc(),
                    Transaction.id.asc(),
                )
                .limit(page_size)
                .offset(offset)
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        current_app.logger.exception("transaction list failed")
        return {"error": "internal server error"}, 500

    return {
        "user_id": str(user_id),
        "transactions": [_serialize_transaction(tx) for tx in transactions],
        "total": total,
        "page": page,
        "page_size": page_size,
    }, 200