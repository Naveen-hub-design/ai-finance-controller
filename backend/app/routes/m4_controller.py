"""M4.3 Step 2: AI Finance Controller HTTP API endpoint.

Exposes :func:`app.services.m4.controller.build_controller_report` over HTTP.
The route only:

- parses/validates the JSON request body and ``intent``,
- verifies the user exists,
- delegates the entire controller decision to the M4.3 service.

It performs no financial calculations, never queries transactions,
accounts, budgets, or goals directly, never imports or calls the OpenAI SDK
directly, and never modifies financial records.

The response is produced directly by
:class:`app.services.m4.contracts.FinancialControllerReport.to_dict()` so no
second serialization format is invented. No financial context, user
questions, or AI answers are logged.
"""

import uuid

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import User
from ..services.m4.controller import build_controller_report


m4_controller_bp = Blueprint(
    "m4_controller",
    __name__,
    url_prefix="/api/users",
)


def _intent_from_payload(payload):
    """Return ``(intent_ok, intent_or_error)``.

    If the payload has a valid string intent, returns ``(True, intent)``.
    Otherwise returns ``(False, error_message)``.
    """
    intent = payload.get("intent")
    if not isinstance(intent, str):
        return False, "intent must be a non-empty string"
    if not intent.strip():
        return False, "intent must be a non-empty string"
    return True, intent


@m4_controller_bp.post("/<uuid:user_id>/ai-controller")
def post_ai_controller(user_id: uuid.UUID):
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    intent_ok, intent_or_error = _intent_from_payload(payload)
    if not intent_ok:
        return {"error": intent_or_error}, 400

    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    try:
        report = build_controller_report(user_id, intent_or_error)
    except SQLAlchemyError:
        current_app.logger.exception("controller computation failed")
        return {"error": "internal server error"}, 500

    return report.to_dict(), 200
