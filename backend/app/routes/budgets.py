"""Budget API endpoints (Milestone 3.5)."""

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..auth import get_current_user_id
from ..extensions import db
from ..models import Account, Budget, BusinessMember, Category, Transaction, User
from ._authorization import require_business_data_access, require_business_member
from ._ownership import require_owner_or
from .users import users_bp

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
        "business_id": str(budget.business_id) if budget.business_id is not None else None,
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
@jwt_required()
def create_budget():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    current_user_id = get_current_user_id()

    user_id_raw = payload.get("user_id")
    category_id_raw = payload.get("category_id")
    amount_raw = payload.get("amount")
    period = payload.get("period")
    start_date_raw = payload.get("start_date")
    end_date_raw = payload.get("end_date")

    business_id = None
    if "business_id" in payload:
        business_id_raw = payload.get("business_id")
        if business_id_raw is not None:
            try:
                business_id = uuid.UUID(str(business_id_raw))
            except (ValueError, AttributeError, TypeError):
                return {"error": "business_id must be a valid UUID"}, 400
            membership = require_business_member(business_id)
            if membership is not None:
                return membership

    # The authenticated identity is the authoritative owner. A client-supplied
    # user_id never overrides it; a mismatched one is rejected.
    if user_id_raw is not None:
        try:
            supplied_user_id = uuid.UUID(str(user_id_raw))
        except (ValueError, AttributeError, TypeError):
            return {"error": "user_id must be a valid UUID"}, 400
        if supplied_user_id != current_user_id:
            return {"error": "forbidden"}, 403

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
        user = db.session.get(User, current_user_id)

        if user is None:
            return {"error": "user not found"}, 404

        if category_id is not None:
            category = db.session.get(Category, category_id)

            if category is None:
                return {"error": "category not found"}, 404

            if category.user_id != current_user_id:
                if business_id is not None:
                    from ..models import BusinessMember
                    is_cat_user_member = db.session.scalar(
                        select(BusinessMember.user_id).where(
                            BusinessMember.business_id == business_id,
                            BusinessMember.user_id == category.user_id
                        )
                    ) is not None
                    if not is_cat_user_member:
                        return {"error": "category does not belong to user"}, 400
                else:
                    return {"error": "category does not belong to user"}, 400

        budget = Budget(
            user_id=current_user_id,
            business_id=business_id,
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
@jwt_required()
def get_budget(budget_id: uuid.UUID):
    try:
        budget = db.session.get(Budget, budget_id)
    except SQLAlchemyError:
        current_app.logger.exception("budget lookup failed")
        return {"error": "internal server error"}, 500

    if budget is None:
        return {"error": "budget not found"}, 404

    if budget.business_id is not None:
        forbidden = require_business_member(budget.business_id)
    else:
        forbidden = require_owner_or(budget.user_id)
    if forbidden is not None:
        return forbidden

    return _serialize_budget(budget), 200


@budgets_bp.put("/<uuid:budget_id>")
@jwt_required()
def update_budget(budget_id: uuid.UUID):
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    try:
        budget = db.session.get(Budget, budget_id)
    except SQLAlchemyError:
        current_app.logger.exception("budget lookup failed")
        return {"error": "internal server error"}, 500

    if budget is None:
        return {"error": "budget not found"}, 404

    if budget.business_id is not None:
        forbidden = require_business_member(budget.business_id)
    else:
        forbidden = require_owner_or(budget.user_id)
    if forbidden is not None:
        return forbidden

    # Ownership cannot be transferred via the request body.
    if "user_id" in payload:
        return {"error": "forbidden"}, 403

    if "amount" in payload:
        try:
            amount = Decimal(str(payload["amount"]))
        except (InvalidOperation, ValueError, TypeError):
            return {"error": "amount must be a valid number"}, 400
        if amount <= 0:
            return {"error": "amount must be greater than zero"}, 400
        budget.amount = amount

    if "period" in payload:
        if payload["period"] not in VALID_PERIODS:
            return {"error": "invalid period"}, 400
        budget.period = payload["period"]

    if "start_date" in payload:
        try:
            budget.start_date = date.fromisoformat(str(payload["start_date"]))
        except (ValueError, TypeError):
            return {"error": "start_date must be YYYY-MM-DD"}, 400

    if "end_date" in payload:
        try:
            budget.end_date = date.fromisoformat(str(payload["end_date"]))
        except (ValueError, TypeError):
            return {"error": "end_date must be YYYY-MM-DD"}, 400

    if budget.end_date < budget.start_date:
        return {"error": "end_date cannot be before start_date"}, 400

    if "category_id" in payload:
        category_id_raw = payload["category_id"]
        if category_id_raw is None:
            budget.category_id = None
        else:
            try:
                new_category_id = uuid.UUID(str(category_id_raw))
            except (ValueError, AttributeError, TypeError):
                return {"error": "category_id must be a valid UUID"}, 400
            category = db.session.get(Category, new_category_id)
            if category is None:
                return {"error": "category not found"}, 404
            if category.user_id != budget.user_id:
                # A business budget may reference a category owned by another
                # member of the same business; otherwise the category must
                # belong to the budget owner. Mirror create_budget's rule.
                if budget.business_id is not None:
                    is_cat_user_member = db.session.scalar(
                        select(BusinessMember.user_id).where(
                            BusinessMember.business_id == budget.business_id,
                            BusinessMember.user_id == category.user_id,
                        )
                    ) is not None
                    if not is_cat_user_member:
                        return {"error": "category does not belong to user"}, 400
                else:
                    return {"error": "category does not belong to user"}, 400
            budget.category_id = new_category_id

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("budget update failed")
        return {"error": "internal server error"}, 500

    return _serialize_budget(budget), 200


@budgets_bp.delete("/<uuid:budget_id>")
@jwt_required()
def delete_budget(budget_id: uuid.UUID):
    try:
        budget = db.session.get(Budget, budget_id)
    except SQLAlchemyError:
        current_app.logger.exception("budget lookup failed")
        return {"error": "internal server error"}, 500

    if budget is None:
        return {"error": "budget not found"}, 404

    if budget.business_id is not None:
        forbidden = require_business_member(budget.business_id)
    else:
        forbidden = require_owner_or(budget.user_id)
    if forbidden is not None:
        return forbidden

    try:
        db.session.delete(budget)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("budget deletion failed")
        return {"error": "internal server error"}, 500

    return "", 204


def _budget_spending(user_id, budgets, business_id=None) -> dict:
    """Return ``{budget_id: spent Decimal}`` for a user's budgets."""
    if not budgets:
        return {}

    if business_id is not None:
        user_account_ids = select(Account.id).where(Account.business_id == business_id)
    else:
        user_account_ids = select(Account.id).where(Account.user_id == user_id, Account.business_id.is_(None))

    rows = (
        db.session.query(
            Budget.id,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .outerjoin(
            Transaction,
            and_(
                Transaction.account_id.in_(user_account_ids),
                Transaction.transaction_type == "expense",
                Transaction.transaction_date >= Budget.start_date,
                Transaction.transaction_date <= Budget.end_date,
                or_(
                    Budget.category_id.is_(None),
                    Transaction.category_id == Budget.category_id,
                ),
            ),
        )
        .filter(Budget.id.in_([b.id for b in budgets]))
        .group_by(Budget.id)
        .all()
    )

    return {str(budget_id): Decimal(str(spent)) for budget_id, spent in rows}


@users_bp.get("/<uuid:user_id>/budgets")
@jwt_required()
def list_budgets(user_id: uuid.UUID):
    """List a user's budgets with precise spending/progress information (owner only)."""
    business_id_raw = request.args.get("business_id")
    if business_id_raw:
        try:
            business_id = uuid.UUID(business_id_raw)
        except (ValueError, AttributeError, TypeError):
            return {"error": "business_id must be a valid UUID"}, 400
        forbidden = require_business_data_access(business_id, user_id)
        if forbidden is not None:
            return forbidden
    else:
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
        if business_id_raw:
            stmt = (
                select(Budget)
                .where(Budget.business_id == business_id)
                .order_by(Budget.start_date.asc(), Budget.id.asc())
            )
        else:
            stmt = (
                select(Budget)
                .where(Budget.user_id == user_id, Budget.business_id.is_(None))
                .order_by(Budget.start_date.asc(), Budget.id.asc())
            )
        budgets = db.session.execute(stmt).scalars().all()
    except SQLAlchemyError:
        current_app.logger.exception("budget list failed")
        return {"error": "internal server error"}, 500

    spending = _budget_spending(user_id, budgets, business_id=business_id if business_id_raw else None)

    result = []
    for budget in budgets:
        data = _serialize_budget(budget)
        amount = Decimal(str(budget.amount))
        spent = spending.get(str(budget.id), Decimal("0"))
        remaining = amount - spent
        progress = (spent / amount * Decimal("100")) if amount > 0 else Decimal("0")
        data["spent"] = f"{spent:.4f}"
        data["remaining"] = f"{remaining:.4f}"
        data["progress_percent"] = f"{progress:.2f}"
        result.append(data)

    return {
        "user_id": str(user_id),
        "budgets": result,
    }, 200