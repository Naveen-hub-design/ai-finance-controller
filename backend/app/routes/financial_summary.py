"""Financial summary API endpoint."""

import uuid
from decimal import Decimal

from flask import Blueprint, current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import Account, Transaction, User


financial_summary_bp = Blueprint(
    "financial_summary",
    __name__,
    url_prefix="/api/financial-summary",
)


@financial_summary_bp.get("/<uuid:user_id>")
def get_financial_summary(user_id: uuid.UUID):
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    try:
        income = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account, Transaction.account_id == Account.id)
            .filter(
                Account.user_id == user_id,
                Transaction.transaction_type == "income",
            )
            .scalar()
        )

        expenses = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account, Transaction.account_id == Account.id)
            .filter(
                Account.user_id == user_id,
                Transaction.transaction_type == "expense",
            )
            .scalar()
        )

        transaction_count = (
            db.session.query(func.count(Transaction.id))
            .join(Account, Transaction.account_id == Account.id)
            .filter(Account.user_id == user_id)
            .scalar()
        )

        income_transaction_count = (
            db.session.query(func.count(Transaction.id))
            .join(Account, Transaction.account_id == Account.id)
            .filter(
                Account.user_id == user_id,
                Transaction.transaction_type == "income",
            )
            .scalar()
        )

        expense_transaction_count = (
            db.session.query(func.count(Transaction.id))
            .join(Account, Transaction.account_id == Account.id)
            .filter(
                Account.user_id == user_id,
                Transaction.transaction_type == "expense",
            )
            .scalar()
        )

        account_balance = (
            db.session.query(
                func.coalesce(func.sum(Account.current_balance), 0)
            )
            .filter(Account.user_id == user_id)
            .scalar()
        )

    except SQLAlchemyError:
        current_app.logger.exception("financial summary lookup failed")
        return {"error": "internal server error"}, 500

    total_income = Decimal(str(income))
    total_expenses = Decimal(str(expenses))
    net_cash_flow = total_income - total_expenses
    total_account_balance = Decimal(str(account_balance))

    return {
        "total_income": f"{total_income:.4f}",
        "total_expenses": f"{total_expenses:.4f}",
        "net_cash_flow": f"{net_cash_flow:.4f}",
        "transaction_count": transaction_count,
        "income_transaction_count": income_transaction_count,
        "expense_transaction_count": expense_transaction_count,
        "account_balance": f"{total_account_balance:.4f}",
    }, 200
