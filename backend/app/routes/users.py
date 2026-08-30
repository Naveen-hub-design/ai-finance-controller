"""User API endpoints (Milestone 3.1)."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import create_access_token, jwt_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..models import User
from ._ownership import require_owner_or

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

    password = payload.get("password")
    if not isinstance(password, str) or not password.strip():
        return {"error": "password is required"}, 400

    try:
        existing = db.session.scalar(select(User).where(User.email == email))
        if existing is not None:
            return {"error": EMAIL_ALREADY_EXISTS}, 409

        user = User(email=email, full_name=full_name)
        user.set_password(password)
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


@users_bp.post("/login")
def login_user() -> tuple[dict[str, str | None], int]:
    """Authenticate a user with email + password.

    Returns the serialized user plus a short-lived JWT access token on
    success. On failure (unknown email or incorrect password) it returns the
    same generic error so callers cannot tell whether the email exists, and
    no internal details are leaked.
    """
    INVALID_CREDENTIALS = "invalid email or password"

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        return {"error": INVALID_CREDENTIALS}, 401
    email = email.strip().lower()

    password = payload.get("password")
    if not isinstance(password, str) or not password:
        return {"error": INVALID_CREDENTIALS}, 401

    try:
        user = db.session.scalar(select(User).where(User.email == email))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("login lookup failed")
        return {"error": "internal server error"}, 500

    if user is None or not user.check_password(password):
        return {"error": INVALID_CREDENTIALS}, 401

    access_token = create_access_token(identity=str(user.id))
    return {"user": _serialize_user(user), "access_token": access_token}, 200


@users_bp.get("/<uuid:user_id>")
@jwt_required()
def get_user(user_id: uuid.UUID) -> tuple[dict[str, str | None], int]:
    """Fetch a single user by id (owner only)."""
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
    return _serialize_user(user), 200


@users_bp.put("/<uuid:user_id>")
@jwt_required()
def update_user(user_id: uuid.UUID) -> tuple[dict[str, str | None], int]:
    """Update a user's email and/or full_name (owner only)."""
    forbidden = require_owner_or(user_id)
    if forbidden is not None:
        return forbidden

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
@jwt_required()
def delete_user(user_id: uuid.UUID) -> tuple[dict[str, str], int]:
    """Delete a user and cascade to owned entities (owner only)."""
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
        db.session.delete(user)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("user deletion failed")
        return {"error": "internal server error"}, 500

    return "", 204
