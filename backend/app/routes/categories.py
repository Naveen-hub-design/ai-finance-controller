"""Category API endpoints (Milestone 3.4)."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..auth import get_current_user_id
from ..extensions import db
from ..models import Category, User
from ._ownership import require_owner_or
from .users import users_bp

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
@jwt_required()
def create_category():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    current_user_id = get_current_user_id()

    user_id_raw = payload.get("user_id")
    name = payload.get("name")
    category_type = payload.get("category_type")

    # The authenticated identity is the authoritative owner. A client-supplied
    # user_id never overrides it; a mismatched one is rejected.
    if user_id_raw is not None:
        try:
            supplied_user_id = uuid.UUID(str(user_id_raw))
        except (ValueError, AttributeError, TypeError):
            return {"error": "user_id must be a valid UUID"}, 400
        if supplied_user_id != current_user_id:
            return {"error": "forbidden"}, 403

    if not isinstance(name, str) or not name.strip():
        return {"error": "name is required"}, 400

    name = name.strip()

    if category_type not in VALID_CATEGORY_TYPES:
        return {"error": "invalid category_type"}, 400

    try:
        user = db.session.get(User, current_user_id)

        if user is None:
            return {"error": "user not found"}, 404

        category = Category(
            user_id=current_user_id,
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
@jwt_required()
def get_category(category_id: uuid.UUID):
    try:
        category = db.session.get(Category, category_id)
    except SQLAlchemyError:
        current_app.logger.exception("category lookup failed")
        return {"error": "internal server error"}, 500

    if category is None:
        return {"error": "category not found"}, 404

    forbidden = require_owner_or(category.user_id)
    if forbidden is not None:
        return forbidden

    return _serialize_category(category), 200


@categories_bp.put("/<uuid:category_id>")
@jwt_required()
def update_category(category_id: uuid.UUID):
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    try:
        category = db.session.get(Category, category_id)
    except SQLAlchemyError:
        current_app.logger.exception("category lookup failed")
        return {"error": "internal server error"}, 500

    if category is None:
        return {"error": "category not found"}, 404

    forbidden = require_owner_or(category.user_id)
    if forbidden is not None:
        return forbidden

    # Ownership cannot be transferred via the request body.
    if "user_id" in payload:
        return {"error": "forbidden"}, 403

    if "name" in payload:
        name = payload["name"]
        if not isinstance(name, str) or not name.strip():
            return {"error": "name is required"}, 400
        category.name = name.strip()

    if "category_type" in payload:
        if payload["category_type"] not in VALID_CATEGORY_TYPES:
            return {"error": "invalid category_type"}, 400
        category.category_type = payload["category_type"]

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("category update failed")
        return {"error": "internal server error"}, 500

    return _serialize_category(category), 200


@categories_bp.delete("/<uuid:category_id>")
@jwt_required()
def delete_category(category_id: uuid.UUID):
    try:
        category = db.session.get(Category, category_id)
    except SQLAlchemyError:
        current_app.logger.exception("category lookup failed")
        return {"error": "internal server error"}, 500

    if category is None:
        return {"error": "category not found"}, 404

    forbidden = require_owner_or(category.user_id)
    if forbidden is not None:
        return forbidden

    try:
        db.session.delete(category)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("category deletion failed")
        return {"error": "internal server error"}, 500

    return "", 204


@users_bp.get("/<uuid:user_id>/categories")
@jwt_required()
def list_categories(user_id: uuid.UUID):
    """List categories belonging to a user (owner only).

    Only the user's own categories are returned; rows where ``user_id`` is
    NULL are intentionally excluded.
    """
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
        categories = (
            db.session.execute(
                select(Category)
                .where(Category.user_id == user_id)
                .order_by(Category.created_at.asc(), Category.id.asc())
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        current_app.logger.exception("category list failed")
        return {"error": "internal server error"}, 500

    return {
        "user_id": str(user_id),
        "categories": [_serialize_category(category) for category in categories],
    }, 200