"""M4.4 decision / audit trail API endpoints.

Persist and read immutable, user-scoped audit records for M4 decisions,
signals, and recommendations. The API is strictly append-only: there is no
update or delete endpoint.

This module performs no financial calculations, does not reinterpret the
stored payload, and never imports or calls the OpenAI SDK. Payload contents
are never logged.
"""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import AuditRecord, User
from ._authorization import require_business_data_access
from ._ownership import require_owner_or

# The only explicitly allowed audit kinds. Rejects arbitrary/bounded kinds.
VALID_AUDIT_KINDS = {"risk", "recommendation", "decision", "reconciliation"}


m4_audit_bp = Blueprint(
    "m4_audit",
    __name__,
    url_prefix="/api/users",
)


def _lookup_user(user_id: uuid.UUID):
    """Return the user or a ``(error_json, status)`` tuple.

    Raises to the caller's exception handler for classification.
    """
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return None, ({"error": "internal server error"}, 500)

    if user is None:
        return None, ({"error": "user not found"}, 404)

    return user, None


@m4_audit_bp.post("/<uuid:user_id>/audit-record")
@jwt_required()
def create_audit_record(user_id: uuid.UUID):
    forbidden = require_owner_or(user_id)
    if forbidden is not None:
        return forbidden

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    kind = payload.get("kind")
    data = payload.get("payload")

    if not isinstance(kind, str) or kind not in VALID_AUDIT_KINDS:
        return (
            {"error": "kind must be one of: risk, recommendation, decision, reconciliation"},
            400,
        )

    if not isinstance(data, dict):
        return {"error": "payload must be a JSON object"}, 400

    _, error = _lookup_user(user_id)
    if error is not None:
        return error

    record = AuditRecord(
        user_id=user_id,
        kind=kind,
        payload=data,
    )

    try:
        db.session.add(record)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("audit record creation failed")
        return {"error": "internal server error"}, 500

    return record.to_dict(), 201


@m4_audit_bp.get("/<uuid:user_id>/audit")
@jwt_required()
def list_audit_records(user_id: uuid.UUID):
    """Return the user's audit trail in a single scope.

    ``?business_id=...`` selects the business-scoped trail: the caller must be
    a member of that business AND the path ``user_id`` must be a member of the
    same business (identity-binding, matching the rest of the API). Without the
    parameter the personal trail is returned: only the owner may read it.
    """
    business_id_raw = request.args.get("business_id")
    business_id = None
    if business_id_raw:
        try:
            business_id = uuid.UUID(business_id_raw)
        except (ValueError, AttributeError, TypeError):
            return {"error": "business_id must be a valid UUID"}, 400

    if business_id is not None:
        forbidden = require_business_data_access(business_id, user_id)
        if forbidden is not None:
            return forbidden
    else:
        forbidden = require_owner_or(user_id)
        if forbidden is not None:
            return forbidden

    _, error = _lookup_user(user_id)
    if error is not None:
        return error

    try:
        query = db.session.query(AuditRecord).filter(AuditRecord.user_id == user_id)
        if business_id is not None:
            query = query.filter(AuditRecord.business_id == business_id)
        else:
            query = query.filter(AuditRecord.business_id.is_(None))
        records = (
            query.order_by(
                AuditRecord.created_at.desc(),
                AuditRecord.id,
            )
            .all()
        )
    except SQLAlchemyError:
        current_app.logger.exception("audit record lookup failed")
        return {"error": "internal server error"}, 500

    return {
        "user_id": str(user_id),
        "records": [record.to_dict() for record in records],
    }, 200
