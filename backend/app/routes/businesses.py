"""Business API endpoints (Milestone F9.x.1).

Provides CRUD for businesses and their memberships under the multi-user
architecture. A MERCHANT creates a business and becomes its OWNER; the OWNER
may add FINANCE_MANAGER members (who get read/access to the business) and
remove members. FINANCE_MANAGER members may view the business and its members
but cannot manage them.

Authorization contract:
- AuthN: all routes require a valid JWT (@jwt_required).
- AuthZ: resolved from the DB via _authorization; a caller who is not a
  member (including a PLATFORM_ADMIN without membership, or a member of a
  different business) gets 403 and presence of foreign resources is never
  revealed. PLATFORM_ADMIN never auto-accesses business data.
"""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..auth import get_current_user_id
from ..extensions import db
from ..models import Business, BusinessMember, User
from ._authorization import (
    FINANCE_MANAGER,
    MEMBERSHIP_ROLES,
    MERCHANT,
    OWNER,
    require_business_member,
    require_business_owner,
    require_role,
)

businesses_bp = Blueprint(
    "businesses",
    __name__,
    url_prefix="/api/businesses",
)


def _serialize_business(business: Business) -> dict:
    return {
        "id": str(business.id),
        "name": business.name,
        "created_at": business.created_at.isoformat(),
        "updated_at": business.updated_at.isoformat(),
    }


def _serialize_member(member: BusinessMember) -> dict:
    user = db.session.get(User, member.user_id)
    return {
        "id": str(member.id),
        "business_id": str(member.business_id),
        "user_id": str(member.user_id),
        "email": user.email if user else None,
        "full_name": user.full_name if user else None,
        "role": member.role,
        "created_at": member.created_at.isoformat(),
    }


@businesses_bp.get("/<uuid:business_id>/members")
@jwt_required()
def list_business_members(business_id: uuid.UUID):
    forbidden = require_business_member(business_id)
    if forbidden is not None:
        return forbidden

    try:
        members = db.session.scalars(
            select(BusinessMember)
            .where(BusinessMember.business_id == business_id)
            .order_by(BusinessMember.created_at.asc(), BusinessMember.id.asc())
        ).all()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("member list failed")
        return {"error": "internal server error"}, 500

    return {
        "business_id": str(business_id),
        "members": [_serialize_member(m) for m in members],
    }, 200


@businesses_bp.post("/<uuid:business_id>/members")
@jwt_required()
def add_business_member(business_id: uuid.UUID):
    """Add a member to a business. OWNER only.

    Accepts the target either by ``email`` (resolved server-side) or by
    ``user_id``. Role defaults to FINANCE_MANAGER.
    """
    forbidden = require_business_owner(business_id)
    if forbidden is not None:
        return forbidden

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    role = payload.get("role", FINANCE_MANAGER)
    if role not in MEMBERSHIP_ROLES:
        return {"error": "invalid membership role"}, 400

    # Resolve the target user by email (preferred; lets an OWNER add someone
    # without exposing the full user directory) or by explicit user_id.
    user_id_raw = payload.get("user_id")
    email_raw = payload.get("email")

    if email_raw is not None:
        if not isinstance(email_raw, str) or not email_raw.strip():
            return {"error": "email must be a string"}, 400
        try:
            target_user = db.session.scalar(
                select(User).where(User.email == email_raw.strip().lower())
            )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("member lookup failed")
            return {"error": "internal server error"}, 500
        if target_user is None:
            return {"error": "user not found"}, 404
        member_user_id = target_user.id
    elif user_id_raw is not None:
        try:
            member_user_id = uuid.UUID(str(user_id_raw))
        except (ValueError, AttributeError, TypeError):
            return {"error": "user_id must be a valid UUID"}, 400
        target_user = db.session.get(User, member_user_id)
        if target_user is None:
            return {"error": "user not found"}, 404
    else:
        return {"error": "user_id or email is required"}, 400

    try:
        business = db.session.get(Business, business_id)
        if business is None:
            return {"error": "business not found"}, 404

        # A PLATFORM_ADMIN cannot be added as a business member role. Business
        # membership is for MERCHANT / FINANCE_MANAGER collaboration only.
        if target_user.role == "PLATFORM_ADMIN":
            return {"error": "forbidden"}, 403

        existing = db.session.scalar(
            select(BusinessMember.id).where(
                BusinessMember.business_id == business_id,
                BusinessMember.user_id == member_user_id,
            )
        )
        if existing is not None:
            return {"error": "user is already a member"}, 409

        member = BusinessMember(
            business_id=business_id,
            user_id=member_user_id,
            role=role,
        )
        db.session.add(member)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception("member add integrity error")
        return {"error": "user is already a member"}, 409
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("member add failed")
        return {"error": "internal server error"}, 500

    return _serialize_member(member), 201


@businesses_bp.delete("/<uuid:business_id>/members/<uuid:user_id>")
@jwt_required()
def remove_business_member(business_id: uuid.UUID, user_id: uuid.UUID):
    """Remove a member from a business. OWNER only."""
    forbidden = require_business_owner(business_id)
    if forbidden is not None:
        return forbidden

    try:
        member = db.session.scalar(
            select(BusinessMember).where(
                BusinessMember.business_id == business_id,
                BusinessMember.user_id == user_id,
            )
        )
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("member lookup failed")
        return {"error": "internal server error"}, 500

    if member is None:
        return {"error": "member not found"}, 404

    # The OWNER cannot be removed (a business must always keep its owner).
    if member.role == OWNER:
        return {"error": "cannot remove the business owner"}, 409

    try:
        db.session.delete(member)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("member removal failed")
        return {"error": "internal server error"}, 500

    return "", 204


@businesses_bp.post("")
@jwt_required()
def create_business():
    """Create a business; the caller (a MERCHANT) becomes its OWNER.

    Restricted to the MERCHANT (owner) role. A business must always be created
    and owned by a MERCHANT — a FINANCE_MANAGER is an operations/analysis role
    and a PLATFORM_ADMIN is a platform role; neither should receive ownership
    of a merchant business.
    """
    forbidden = require_role(MERCHANT)
    if forbidden is not None:
        return forbidden

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"error": "name is required"}, 400
    name = name.strip()

    current_user_id = get_current_user_id()

    try:
        business = Business(name=name)
        db.session.add(business)
        db.session.flush()

        owner_member = BusinessMember(
            business_id=business.id,
            user_id=current_user_id,
            role=OWNER,
        )
        db.session.add(owner_member)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception("business creation integrity error")
        return {"error": "business could not be created"}, 409
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("business creation failed")
        return {"error": "internal server error"}, 500

    return _serialize_business(business), 201


@businesses_bp.get("")
@jwt_required()
def list_businesses():
    """List businesses the caller belongs to (owner or any member)."""
    current_user_id = get_current_user_id()

    try:
        rows = db.session.execute(
            select(Business, BusinessMember.role)
            .join(
                BusinessMember,
                BusinessMember.business_id == Business.id,
            )
            .where(BusinessMember.user_id == current_user_id)
            .order_by(Business.created_at.asc(), Business.id.asc())
        ).all()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("business list failed")
        return {"error": "internal server error"}, 500

    result = [
        {**_serialize_business(business), "my_role": member_role}
        for business, member_role in rows
    ]
    return {"businesses": result}, 200


@businesses_bp.get("/<uuid:business_id>")
@jwt_required()
def get_business(business_id: uuid.UUID):
    forbidden = require_business_member(business_id)
    if forbidden is not None:
        return forbidden

    try:
        business = db.session.get(Business, business_id)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("business lookup failed")
        return {"error": "internal server error"}, 500

    if business is None:
        return {"error": "business not found"}, 404

    return _serialize_business(business), 200


@businesses_bp.put("/<uuid:business_id>")
@jwt_required()
def update_business(business_id: uuid.UUID):
    forbidden = require_business_owner(business_id)
    if forbidden is not None:
        return forbidden

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    try:
        business = db.session.get(Business, business_id)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("business lookup failed")
        return {"error": "internal server error"}, 500

    if business is None:
        return {"error": "business not found"}, 404

    if "name" in payload:
        name = payload["name"]
        if not isinstance(name, str) or not name.strip():
            return {"error": "name is required"}, 400
        business.name = name.strip()
        business.updated_at = db.func.now()

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("business update failed")
        return {"error": "internal server error"}, 500

    return _serialize_business(business), 200


@businesses_bp.delete("/<uuid:business_id>")
@jwt_required()
def delete_business(business_id: uuid.UUID):
    forbidden = require_business_owner(business_id)
    if forbidden is not None:
        return forbidden

    try:
        business = db.session.get(Business, business_id)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("business lookup failed")
        return {"error": "internal server error"}, 500

    if business is None:
        return {"error": "business not found"}, 404

    try:
        db.session.delete(business)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("business deletion failed")
        return {"error": "internal server error"}, 500

    return "", 204
