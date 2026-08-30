"""Trusted authenticated-identity resolution (Milestone 7.3).

This module provides the application's single source of "who is the caller".
Identity is derived EXCLUSIVELY from the verified JWT presented in the
Authorization header. No client-controlled value (URL user_id, JSON user_id,
query parameter, entity owner field) is ever accepted here.

Callers must invoke these helpers from within a ``@jwt_required()``-protected
request context; the identity resolution itself never queries the database.
"""

import uuid

from flask_jwt_extended import get_jwt_identity


class AuthenticationError(Exception):
    """Raised when a verified JWT carries no usable authenticated identity.

    Deliberately carries no claims, token contents, or internal details so it
    can be mapped to a safe, generic client-facing error.
    """


def get_current_user_id() -> uuid.UUID:
    """Return the authenticated user's id as a UUID from the verified JWT.

    Raises :class:`AuthenticationError` if the verified JWT has no identity or
    its identity is not a valid UUID. It never falls back to a fabricated,
    default, or client-supplied identifier.
    """
    identity = get_jwt_identity()
    if not identity:
        raise AuthenticationError("no identity in authenticated request")

    try:
        return uuid.UUID(str(identity))
    except (TypeError, ValueError, AttributeError):
        raise AuthenticationError("invalid identity in authenticated request") from None
