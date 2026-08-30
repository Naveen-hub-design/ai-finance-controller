"""Reusable route-authorization helpers (Milestone 7.4).

This module centralizes the single ownership rule used across the API:

    verified JWT identity == requested resource owner  -> allow

Its job is authorization only. It never queries financial data, never
performs business logic, never calls AI or Celery, never calculates
financial values, and never logs sensitive data.
"""

from ..auth import AuthenticationError, get_current_user_id

# The one, consistent response for an authenticated-but-not-owner request.
FORBIDDEN = {"error": "forbidden"}, 403

# Used when a verified JWT happens to carry no usable identity (defensive;
# the M7.2 JWT token handlers already reject missing/invalid/expired tokens
# with 401 before any route body runs).
UNAUTHORIZED = {"error": "authorization required"}, 401


def require_owner_or(path_user_id):
    """Return None if the verified JWT identity owns ``path_user_id``.

    Otherwise return a ``(error_json, status)`` tuple:
    ``({"error": "forbidden"}, 403)`` for a verified caller who does not own
    the resource, or ``({"error": "authorization required"}, 401)`` if the
    verified JWT carries no usable, valid identity.

    Must be invoked inside a ``@jwt_required()`` route. The identity used is
    always :func:`app.auth.get_current_user_id`, which resolves exclusively
    from the verified JWT -- never from any client-supplied value.
    """
    try:
        current = get_current_user_id()
    except AuthenticationError:
        return UNAUTHORIZED

    if current != path_user_id:
        return FORBIDDEN

    return None
