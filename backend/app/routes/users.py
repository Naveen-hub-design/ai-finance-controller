"""User API endpoints (Milestone 3.1)."""

import uuid

from flask import Blueprint, current_app, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..models import User

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

EMAIL_ALREADY_EXISTS = "a user with this email already exists"


def _serialize_user(user: User) -> dict[str, str | None]:
    """Return the public representation of a user."""
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


@users_bp.post("")
def create_user() -> tuple[dict[str, str], int]:
    """Register a new user."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        return {"error": "email is required"}, 400
    email = email.strip().lower()

    full_name = payload.get("full_name")
    if full_name is not None and not isinstance(full_name, str):
        return {"error": "full_name must be a string"}, 400
    if isinstance(full_name, str):
        full_name = full_name.strip() or None

    try:
        existing = db.session.scalar(select(User).where(User.email == email))
        if existing is not None:
            return {"error": EMAIL_ALREADY_EXISTS}, 409

        user = User(email=email, full_name=full_name)
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        # Concurrent insert raced past the uniqueness pre-check.
        db.session.rollback()
        return {"error": EMAIL_ALREADY_EXISTS}, 409
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("user creation failed")
        return {"error": "internal server error"}, 500

    return _serialize_user(user), 201


@users_bp.get("/<uuid:user_id>")
def get_user(user_id: uuid.UUID) -> tuple[dict[str, str | None], int]:
    """Fetch a single user by id."""
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404
    return _serialize_user(user), 200


@users_bp.put("/<uuid:user_id>")
def update_user(user_id: uuid.UUID) -> tuple[dict[str, str | None], int]:
    """Update a user's email and/or full_name."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    if "email" in payload:
        email = payload["email"]
        if not isinstance(email, str) or not email.strip():
            return {"error": "email is required"}, 400
        email = email.strip().lower()

        if email != user.email:
            existing = db.session.scalar(
                select(User).where(User.email == email)
            )
            if existing is not None:
                return {"error": EMAIL_ALREADY_EXISTS}, 409
            user.email = email

    if "full_name" in payload:
        full_name = payload["full_name"]
        if full_name is not None and not isinstance(full_name, str):
            return {"error": "full_name must be a string"}, 400
        if isinstance(full_name, str):
            full_name = full_name.strip() or None
        user.full_name = full_name

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": EMAIL_ALREADY_EXISTS}, 409
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("user update failed")
        return {"error": "internal server error"}, 500

    return _serialize_user(user), 200


@users_bp.delete("/<uuid:user_id>")
def delete_user(user_id: uuid.UUID) -> tuple[dict[str, str], int]:
    """Delete a user and cascade to owned entities."""
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    try:
        db.session.delete(user)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("user deletion failed")
        return {"error": "internal server error"}, 500

    return "", 204
