"""Transaction API endpoints (Milestone 3.3)."""

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..models import Account, Category, Transaction

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


@transactions_bp.post("")
def create_transaction():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

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

        if category_id is not None:
            category = db.session.get(Category, category_id)

            if category is None:
                return {"error": "category not found"}, 404

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
def get_transaction(transaction_id: uuid.UUID):
    try:
        transaction = db.session.get(Transaction, transaction_id)
    except SQLAlchemyError:
        current_app.logger.exception("transaction lookup failed")
        return {"error": "internal server error"}, 500

    if transaction is None:
        return {"error": "transaction not found"}, 404

    return _serialize_transaction(transaction), 200