"""Financial facts API endpoint."""

import uuid

from flask import Blueprint, current_app
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import User
from ..services.financial_intelligence import build_financial_facts


financial_facts_bp = Blueprint(
    "financial_facts",
    __name__,
    url_prefix="/api/users",
)


@financial_facts_bp.get("/<uuid:user_id>/financial-facts")
def get_financial_facts(user_id: uuid.UUID):
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    try:
        facts = build_financial_facts(user_id)
    except SQLAlchemyError:
        current_app.logger.exception("financial facts computation failed")
        return {"error": "internal server error"}, 500

    return facts, 200
