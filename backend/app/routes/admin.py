"""Platform administration endpoints (admin-only)."""

import uuid

from flask import Blueprint, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import Business, User
from ._authorization import PLATFORM_ADMIN, require_role

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/stats")
@jwt_required()
def get_admin_stats() -> tuple[dict, int]:
    """Return platform-level statistics (PLATFORM_ADMIN only).

    Every metric comes from live database queries. No data is fabricated.
    """
    forbidden = require_role(PLATFORM_ADMIN)
    if forbidden is not None:
        return forbidden

    try:
        total_users = db.session.scalar(select(func.count(User.id))) or 0
        users_by_role = {}
        for role_name in (PLATFORM_ADMIN, "MERCHANT", "FINANCE_MANAGER"):
            count = db.session.scalar(
                select(func.count(User.id)).where(User.role == role_name)
            ) or 0
            users_by_role[role_name] = int(count)

        total_businesses = db.session.scalar(select(func.count(Business.id))) or 0
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("admin stats query failed")
        return {"error": "internal server error"}, 500

    return {
        "total_users": int(total_users),
        "users_by_role": users_by_role,
        "total_businesses": int(total_businesses),
    }, 200
