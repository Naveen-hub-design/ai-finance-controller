"""Financial summary API endpoint."""

from decimal import Decimal

from flask import Blueprint, current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import Account, Transaction


financial_summary_bp = Blueprint(
    "financial_summary",
    __name__,
    url_prefix="/api/financial-summary",
)


@financial_summary_bp.get("")
def get_financial_summary():
    try:
        income = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(Transaction.transaction_type == "income")
            .scalar()
        )

        expenses = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(Transaction.transaction_type == "expense")
            .scalar()
        )

        transaction_count = db.session.query(
            func.count(Transaction.id)
        ).scalar()

        income_transaction_count = db.session.query(
            func.count(Transaction.id)
        ).filter(
            Transaction.transaction_type == "income"
        ).scalar()

        expense_transaction_count = db.session.query(
            func.count(Transaction.id)
        ).filter(
            Transaction.transaction_type == "expense"
        ).scalar()

        account_balance = (
            db.session.query(
                func.coalesce(func.sum(Account.current_balance), 0)
            ).scalar()
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