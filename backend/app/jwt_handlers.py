"""Safe, generic error handlers for JWT authentication failures.

These are registered on the shared ``jwt`` extension instance when this module
is imported. Responses are intentionally generic: they never expose tokens,
signing secrets, stack traces, raw library exception messages, or any internal
JWT details. No credential or token material is logged.
"""

from .extensions import jwt


@jwt.unauthorized_loader
def _missing_jwt(reason: str) -> tuple[dict[str, str], int]:
    return {"error": "authorization required"}, 401


@jwt.invalid_token_loader
def _invalid_jwt(reason: str) -> tuple[dict[str, str], int]:
    return {"error": "authorization required"}, 401


@jwt.expired_token_loader
def _expired_jwt(jwt_header: dict, jwt_payload: dict) -> tuple[dict[str, str], int]:
    return {"error": "authorization token expired"}, 401
