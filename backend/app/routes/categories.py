"""Category API endpoints (Milestone 3.4)."""

import uuid

from flask import Blueprint, current_app, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..models import Category, User

categories_bp = Blueprint(
    "categories",
    __name__,
    url_prefix="/api/categories",
)

VALID_CATEGORY_TYPES = {
    "income",
    "expense",
}


def _serialize_category(category: Category) -> dict:
    return {
        "id": str(category.id),
        "user_id": str(category.user_id) if category.user_id else None,
        "name": category.name,
        "category_type": category.category_type,
        "created_at": category.created_at.isoformat(),
    }


@categories_bp.post("")
def create_category():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    user_id_raw = payload.get("user_id")
    name = payload.get("name")
    category_type = payload.get("category_type")

    try:
        user_id = uuid.UUID(str(user_id_raw))
    except (ValueError, AttributeError, TypeError):
        return {"error": "user_id must be a valid UUID"}, 400

    if not isinstance(name, str) or not name.strip():
        return {"error": "name is required"}, 400

    name = name.strip()

    if category_type not in VALID_CATEGORY_TYPES:
        return {"error": "invalid category_type"}, 400

    try:
        user = db.session.get(User, user_id)

        if user is None:
            return {"error": "user not found"}, 404

        category = Category(
            user_id=user_id,
            name=name,
            category_type=category_type,
        )

        db.session.add(category)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception("category creation integrity error")
        return {"error": "category could not be created"}, 409

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("category creation failed")
        return {"error": "internal server error"}, 500

    return _serialize_category(category), 201


@categories_bp.get("/<uuid:category_id>")
def get_category(category_id: uuid.UUID):
    try:
        category = db.session.get(Category, category_id)
    except SQLAlchemyError:
        current_app.logger.exception("category lookup failed")
        return {"error": "internal server error"}, 500

    if category is None:
        return {"error": "category not found"}, 404

    return _serialize_category(category), 200