"""Deterministic financial intelligence calculations."""

import uuid
from decimal import Decimal

from sqlalchemy import func

from ..extensions import db
from ..models import Account, Budget, Category, FinancialGoal, Transaction


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def build_financial_facts(user_id, business_id=None) -> dict:
    """Build verified financial facts for a single user or business context."""

    user_id = uuid.UUID(str(user_id))
    if business_id is not None:
        business_uuid = uuid.UUID(str(business_id))
        account_filter = Account.business_id == business_uuid
        budget_filter = Budget.business_id == business_uuid
        goal_filter = FinancialGoal.business_id == business_uuid
    else:
        from sqlalchemy import and_
        account_filter = and_(Account.user_id == user_id, Account.business_id.is_(None))
        budget_filter = and_(Budget.user_id == user_id, Budget.business_id.is_(None))
        goal_filter = and_(FinancialGoal.user_id == user_id, FinancialGoal.business_id.is_(None))

    income = (
        db.session.query(
            func.coalesce(func.sum(Transaction.amount), 0)
        )
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            account_filter,
            Transaction.transaction_type == "income",
        )
        .scalar()
    )

    expenses = (
        db.session.query(
            func.coalesce(func.sum(Transaction.amount), 0)
        )
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            account_filter,
            Transaction.transaction_type == "expense",
        )
        .scalar()
    )

    transaction_count = (
        db.session.query(func.count(Transaction.id))
        .join(Account, Transaction.account_id == Account.id)
        .filter(account_filter)
        .scalar()
    )

    income_transaction_count = (
        db.session.query(func.count(Transaction.id))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            account_filter,
            Transaction.transaction_type == "income",
        )
        .scalar()
    )

    expense_transaction_count = (
        db.session.query(func.count(Transaction.id))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            account_filter,
            Transaction.transaction_type == "expense",
        )
        .scalar()
    )

    account_balance = (
        db.session.query(
            func.coalesce(func.sum(Account.current_balance), 0)
        )
        .filter(account_filter)
        .scalar()
    )

    total_income = _decimal(income)
    total_expenses = _decimal(expenses)
    total_account_balance = _decimal(account_balance)

    category_rows = (
        db.session.query(
            Category.name,
            func.sum(Transaction.amount),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            account_filter,
            Transaction.transaction_type == "expense",
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    spending_by_category = [
        {
            "category": name,
            "amount": f"{_decimal(amount):.4f}",
        }
        for name, amount in category_rows
    ]

    budgets = (
        db.session.query(Budget)
        .filter(budget_filter)
        .order_by(Budget.start_date)
        .all()
    )

    budget_category_ids = {
        budget.category_id
        for budget in budgets
        if budget.category_id is not None
    }

    category_names: dict = {}
    if budget_category_ids:
        category_rows = (
            db.session.query(Category.id, Category.name)
            .filter(Category.id.in_(budget_category_ids))
            .all()
        )
        category_names = {category_id: name for category_id, name in category_rows}

    budget_facts = [
        {
            "id": str(budget.id),
            "category_id": (
                str(budget.category_id)
                if budget.category_id is not None
                else None
            ),
            "category_name": (
                category_names.get(budget.category_id)
                if budget.category_id is not None
                else None
            ),
            "amount": f"{_decimal(budget.amount):.4f}",
            "period": budget.period,
            "start_date": budget.start_date.isoformat(),
            "end_date": budget.end_date.isoformat(),
        }
        for budget in budgets
    ]

    goals = (
        db.session.query(FinancialGoal)
        .filter(goal_filter)
        .order_by(FinancialGoal.target_date)
        .all()
    )

    goal_facts = []

    for goal in goals:
        target = _decimal(goal.target_amount)
        current = _decimal(goal.current_amount)

        progress = (
            (current / target * Decimal("100"))
            if target > 0
            else Decimal("0")
        )

        goal_facts.append(
            {
                "id": str(goal.id),
                "name": goal.name,
                "target_amount": f"{target:.4f}",
                "current_amount": f"{current:.4f}",
                "progress_percent": f"{progress:.2f}",
                "target_date": (
                    goal.target_date.isoformat()
                    if goal.target_date is not None
                    else None
                ),
                "status": goal.status,
            }
        )

    return {
        "total_income": f"{total_income:.4f}",
        "total_expenses": f"{total_expenses:.4f}",
        "net_cash_flow": f"{total_income - total_expenses:.4f}",
        "transaction_count": transaction_count,
        "income_transaction_count": income_transaction_count,
        "expense_transaction_count": expense_transaction_count,
        "account_balance": f"{total_account_balance:.4f}",
        "spending_by_category": spending_by_category,
        "budgets": budget_facts,
        "financial_goals": goal_facts,
    }