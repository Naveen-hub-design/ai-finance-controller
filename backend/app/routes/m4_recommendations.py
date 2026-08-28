"""M4.2 financial recommendations API endpoint.

Exposes the deterministic financial recommendations produced by
:func:`app.services.m4.recommendations.run_recommendations` over HTTP.

The route only verifies the user exists and delegates the recommendation
logic entirely to the M4.2 service; it performs no financial calculations
and never queries transactions, budgets, or goals directly.
"""

import uuid

from flask import Blueprint, current_app
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import User
from ..services.m4.recommendations import run_recommendations


m4_recommendations_bp = Blueprint(
    "m4_recommendations",
    __name__,
    url_prefix="/api/users",
)


@m4_recommendations_bp.get("/<uuid:user_id>/recommendations")
def get_recommendations(user_id: uuid.UUID):
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    try:
        recommendations = run_recommendations(user_id)
    except SQLAlchemyError:
        current_app.logger.exception("recommendation computation failed")
        return {"error": "internal server error"}, 500

    return {
        "user_id": str(user_id),
        "recommendations": recommendations,
    }, 200
