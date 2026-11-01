"""Role- and membership-based route authorization (Milestone F9.x.1).

Extends the ownership-only rule in :mod:`._ownership` with two higher-level
checks, both resolved from the DATABASE after the JWT identity is verified.

Security contract (matches the rest of the API):

- JWT is identity-only; role and business membership are ALWAYS read from the
  DB at request time. role/business_id never come from the token or the body.
- PLATFORM_ADMIN is a platform-level role. It grants platform administration
  (managing users/roles) but is never sufficient to bypass a business
  membership check -- a PLATFORM_ADMIN cannot auto-access merchant financial
  data or business membership data without being a member.
- Foreign/unknown resources never leak existence: they resolve to the generic
  403 "forbidden" (same as an authorized-but-non-member caller).

This module is authorization-only: it never queries financial data, never
performs business logic, never calls AI/Celery, and never logs sensitive data.
"""

import uuid

from sqlalchemy import select

from ..auth import AuthenticationError, get_current_user_id
from ..extensions import db
from ..models import BusinessMember, User
from ._ownership import FORBIDDEN, UNAUTHORIZED

PLATFORM_ADMIN = "PLATFORM_ADMIN"
MERCHANT = "MERCHANT"
FINANCE_MANAGER = "FINANCE_MANAGER"
OWNER = "OWNER"

MEMBERSHIP_ROLES = {OWNER: "OWNER", FINANCE_MANAGER: "FINANCE_MANAGER"}
VALID_USER_ROLES = {PLATFORM_ADMIN, MERCHANT, FINANCE_MANAGER}


def get_current_user(user_id: uuid.UUID | None = None) -> User | None:
    """Return the authenticated User row (fresh from the DB).

    Resolves from the verified JWT identity, never from a client-supplied
    value. Returns None if the JWT has no usable identity or the user no
    longer exists.
    """
    try:
        resolved = user_id or get_current_user_id()
    except AuthenticationError:
        return None
    return db.session.get(User, resolved)


def load_user_role(user_id: uuid.UUID) -> str | None:
    """Return the DB role of ``user_id``, or None if the user does not exist.

    The DB is the source of truth; no JWT claim is consulted.
    """
    row = db.session.get(User, user_id)
    if row is None:
        return None
    return row.role


def require_role(role: str, user_id: uuid.UUID | None = None):
    """Return None if the authenticated user's DB role equals ``role``.

    Otherwise return a ``(error_json, status)`` tuple (403 forbidden / 401
    unauthorized), matching the existing ownership contract. Must be called
    inside a ``@jwt_required()`` route.
    """
    try:
        resolved = user_id or get_current_user_id()
    except AuthenticationError:
        return UNAUTHORIZED

    db_role = load_user_role(resolved)
    if db_role is None:
        return FORBIDDEN
    if db_role != role:
        return FORBIDDEN
    return None


def get_membership_role(business_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    """Return the caller's membership role in ``business_id`` (or None).

    None means "not a member" -- used for the 403 on any non-member access.
    """
    return db.session.scalar(
        select(BusinessMember.role).where(
            BusinessMember.business_id == business_id,
            BusinessMember.user_id == user_id,
        )
    )


def require_business_member(business_id, user_id=None):
    """Return None if the authenticated user is a member of ``business_id``.

    A PLATFORM_ADMIN without membership is NOT granted access -- business
    access is gated strictly by membership. Non-members (including platform
    admins and foreign users) get 403 without leaking whether the business
    exists.
    """
    try:
        resolved = user_id or get_current_user_id()
    except AuthenticationError:
        return UNAUTHORIZED

    try:
        is_member = (
            db.session.scalar(
                select(BusinessMember.user_id).where(
                    BusinessMember.business_id == business_id,
                    BusinessMember.user_id == resolved,
                )
            )
            is not None
        )
    except Exception:
        return FORBIDDEN

    if not is_member:
        return FORBIDDEN
    return None


def require_business_owner(business_id, user_id=None):
    """Return None if the authenticated user is the OWNER of ``business_id``."""
    try:
        resolved = user_id or get_current_user_id()
    except AuthenticationError:
        return UNAUTHORIZED

    try:
        role = get_membership_role(business_id, resolved)
    except Exception:
        return FORBIDDEN

    if role != OWNER:
        return FORBIDDEN
    return None


def require_business_data_access(business_id, user_id=None):
    """Return None if the caller is a member of ``business_id`` AND the
    requested ``user_id`` is a member of that same business.

    This is the identity-binding check for business-scoped ("?business_id=...")
    list / read / AI endpoints. Membership alone is not enough: the path
    ``user_id`` must also belong to the same business, so a member cannot
    pivot a request identity to an unrelated user. When ``user_id`` is the
    caller, this degenerates to a plain membership check.
    """
    forbidden = require_business_member(business_id)
    if forbidden is not None:
        return forbidden

    try:
        resolved_target = user_id or get_current_user_id()
        target_role = get_membership_role(business_id, resolved_target)
    except Exception:
        return FORBIDDEN

    if target_role is None:
        return FORBIDDEN
    return None
