"""Budget API endpoints (Milestone 3.5)."""

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..models import Budget, Category, User

budgets_bp = Blueprint(
    "budgets",
    __name__,
    url_prefix="/api/budgets",
)


VALID_PERIODS = {
    "weekly",
    "monthly",
    "yearly",
}


def _serialize_budget(budget: Budget) -> dict:
    return {
        "id": str(budget.id),
        "user_id": str(budget.user_id),
        "category_id": (
            str(budget.category_id)
            if budget.category_id is not None
            else None
        ),
        "amount": str(budget.amount),
        "period": budget.period,
        "start_date": budget.start_date.isoformat(),
        "end_date": budget.end_date.isoformat(),
        "created_at": budget.created_at.isoformat(),
    }


@budgets_bp.post("")
def create_budget():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    user_id_raw = payload.get("user_id")
    category_id_raw = payload.get("category_id")
    amount_raw = payload.get("amount")
    period = payload.get("period")
    start_date_raw = payload.get("start_date")
    end_date_raw = payload.get("end_date")

    try:
        user_id = uuid.UUID(str(user_id_raw))
    except (ValueError, AttributeError, TypeError):
        return {"error": "user_id must be a valid UUID"}, 400

    category_id = None

    if category_id_raw is not None:
        try:
            category_id = uuid.UUID(str(category_id_raw))
        except (ValueError, AttributeError, TypeError):
            return {"error": "category_id must be a valid UUID"}, 400

    if period not in VALID_PERIODS:
        return {"error": "invalid period"}, 400

    try:
        amount = Decimal(str(amount_raw))
    except (InvalidOperation, ValueError, TypeError):
        return {"error": "amount must be a valid number"}, 400

    if amount <= 0:
        return {"error": "amount must be greater than zero"}, 400

    try:
        start_date = date.fromisoformat(str(start_date_raw))
    except (ValueError, TypeError):
        return {"error": "start_date must be YYYY-MM-DD"}, 400

    try:
        end_date = date.fromisoformat(str(end_date_raw))
    except (ValueError, TypeError):
        return {"error": "end_date must be YYYY-MM-DD"}, 400

    if end_date < start_date:
        return {"error": "end_date cannot be before start_date"}, 400

    try:
        user = db.session.get(User, user_id)

        if user is None:
            return {"error": "user not found"}, 404

        if category_id is not None:
            category = db.session.get(Category, category_id)

            if category is None:
                return {"error": "category not found"}, 404

            if category.user_id != user_id:
                return {"error": "category does not belong to user"}, 400

        budget = Budget(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )

        db.session.add(budget)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception("budget creation integrity error")
        return {"error": "budget could not be created"}, 409

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("budget creation failed")
        return {"error": "internal server error"}, 500

    return _serialize_budget(budget), 201


@budgets_bp.get("/<uuid:budget_id>")
def get_budget(budget_id: uuid.UUID):
    try:
        budget = db.session.get(Budget, budget_id)
    except SQLAlchemyError:
        current_app.logger.exception("budget lookup failed")
        return {"error": "internal server error"}, 500

    if budget is None:
        return {"error": "budget not found"}, 404

    return _serialize_budget(budget), 200