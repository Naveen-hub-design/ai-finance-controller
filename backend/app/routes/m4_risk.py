"""M4.1 financial risk intelligence API endpoint.

Exposes the deterministic risk findings produced by
:func:`app.services.m4.anomaly_detection.run_risk_intelligence` over HTTP.

The route only verifies the user exists and delegates the analysis entirely
to the M4.1 service; it performs no financial calculations and never queries
transaction records directly.
"""

import uuid

from flask import Blueprint, current_app
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import User
from ..services.m4.anomaly_detection import run_risk_intelligence


m4_risk_bp = Blueprint(
    "m4_risk",
    __name__,
    url_prefix="/api/users",
)


@m4_risk_bp.get("/<uuid:user_id>/risk-intelligence")
def get_risk_intelligence(user_id: uuid.UUID):
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    try:
        signals = run_risk_intelligence(user_id)
    except SQLAlchemyError:
        current_app.logger.exception("risk intelligence computation failed")
        return {"error": "internal server error"}, 500

    return {
        "user_id": str(user_id),
        "signals": signals,
    }, 200
