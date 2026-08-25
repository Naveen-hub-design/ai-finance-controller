"""Financial goal API endpoints (Milestone 3.6)."""

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..models import FinancialGoal, User

financial_goals_bp = Blueprint(
    "financial_goals",
    __name__,
    url_prefix="/api/financial-goals",
)


VALID_STATUSES = {
    "active",
    "completed",
    "paused",
    "cancelled",
}


def _serialize_goal(goal: FinancialGoal) -> dict:
    return {
        "id": str(goal.id),
        "user_id": str(goal.user_id),
        "name": goal.name,
        "target_amount": str(goal.target_amount),
        "current_amount": str(goal.current_amount),
        "target_date": (
            goal.target_date.isoformat()
            if goal.target_date is not None
            else None
        ),
        "status": goal.status,
        "created_at": goal.created_at.isoformat(),
        "updated_at": goal.updated_at.isoformat(),
    }


@financial_goals_bp.post("")
def create_goal():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    user_id_raw = payload.get("user_id")
    name = payload.get("name")
    target_amount_raw = payload.get("target_amount")
    current_amount_raw = payload.get("current_amount", "0")
    target_date_raw = payload.get("target_date")
    status = payload.get("status", "active")

    try:
        user_id = uuid.UUID(str(user_id_raw))
    except (ValueError, AttributeError, TypeError):
        return {"error": "user_id must be a valid UUID"}, 400

    if not isinstance(name, str) or not name.strip():
        return {"error": "name is required"}, 400

    name = name.strip()

    try:
        target_amount = Decimal(str(target_amount_raw))
    except (InvalidOperation, ValueError, TypeError):
        return {"error": "target_amount must be a valid number"}, 400

    if target_amount <= 0:
        return {"error": "target_amount must be greater than zero"}, 400

    try:
        current_amount = Decimal(str(current_amount_raw))
    except (InvalidOperation, ValueError, TypeError):
        return {"error": "current_amount must be a valid number"}, 400

    if current_amount < 0:
        return {"error": "current_amount cannot be negative"}, 400

    if current_amount > target_amount:
        return {"error": "current_amount cannot exceed target_amount"}, 400

    if status not in VALID_STATUSES:
        return {"error": "invalid status"}, 400

    target_date = None

    if target_date_raw is not None:
        try:
            target_date = date.fromisoformat(str(target_date_raw))
        except (ValueError, TypeError):
            return {"error": "target_date must be YYYY-MM-DD"}, 400

    try:
        user = db.session.get(User, user_id)

        if user is None:
            return {"error": "user not found"}, 404

        goal = FinancialGoal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date,
            status=status,
        )

        db.session.add(goal)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception("financial goal creation integrity error")
        return {"error": "financial goal could not be created"}, 409

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("financial goal creation failed")
        return {"error": "internal server error"}, 500

    return _serialize_goal(goal), 201


@financial_goals_bp.get("/<uuid:goal_id>")
def get_goal(goal_id: uuid.UUID):
    try:
        goal = db.session.get(FinancialGoal, goal_id)
    except SQLAlchemyError:
        current_app.logger.exception("financial goal lookup failed")
        return {"error": "internal server error"}, 500

    if goal is None:
        return {"error": "financial goal not found"}, 404

    return _serialize_goal(goal), 200