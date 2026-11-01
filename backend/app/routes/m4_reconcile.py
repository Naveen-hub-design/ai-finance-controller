"""Multi-source financial reconciliation API endpoints.

Expose the deterministic reconciliation agent (``run_reconciliation``) over
HTTP, both synchronously and asynchronously (Celery) for a 50+ record batch.
These routes only:

- validate the request body / ``source``,
- verify the caller owns (or is a business member of) the requested user,
- invoke / dispatch the reconciliation service, and
- persist an immutable ``"reconciliation"`` audit record on completion.

They perform no financial calculations, mutate no internal ledger records,
and never log statement line contents, amounts, or descriptions.

The asynchronous submit/poll pair mirrors the hardened M7.4/M7.5 async
controller pattern: the caller is authorized against the URL ``user_id`` and
each dispatched Celery task is bound to its authenticated owner via
``ControllerTask`` before its status/result is ever read back.
"""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from ..auth import get_current_user_id
from ..celery_client import dispatch_reconciliation, task_result
from ..extensions import db
from ..models import AuditRecord, ControllerTask, StatementLine, User
from ..services.m4.reconciliation import (
    VALID_REVIEW_STATUSES,
    run_reconciliation,
)
from ..services.m4.reconciliation_contracts import ReconciliationException
from ..services.m4.reconciliation_explain import explain_reconciliation_exception
from ..services.openai_provider import AIConfigurationError, AIProviderError
from ._authorization import require_business_data_access
from ._ownership import FORBIDDEN, require_owner_or

# A safe, generic message returned on FAILURE. It deliberately exposes no
# traceback, exception internals, secrets, or request data.
_FAILURE_MESSAGE = "the task did not complete successfully"

_DEFAULT_SOURCE = "bank_statement"


def _source_from_payload(payload):
    """Return ``(source_ok, source_or_error)``.

    The source label is optional and defaults to ``bank_statement``. When
    provided it must be a non-empty string.
    """
    if not isinstance(payload, dict):
        return True, _DEFAULT_SOURCE
    source = payload.get("source")
    if source is None:
        return True, _DEFAULT_SOURCE
    if not isinstance(source, str) or not source.strip():
        return False, "source must be a non-empty string"
    return True, source.strip()


def _require_access(user_id, business_id):
    """Enforce user/business authorization, returning the guard result.

    Returns ``None`` when authorized, otherwise the ``(json, status)`` tuple
    to return to the client.
    """
    if business_id is not None:
        return require_business_data_access(business_id, user_id)
    return require_owner_or(user_id)


def _lookup_user(user_id):
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return None, {"error": "internal server error"}, 500
    if user is None:
        return None, {"error": "user not found"}, 404
    return user, None, None


m4_reconcile_bp = Blueprint(
    "m4_reconcile",
    __name__,
    url_prefix="/api/users",
)


@m4_reconcile_bp.post("/<uuid:user_id>/reconcile")
@jwt_required()
def post_reconcile(user_id: uuid.UUID):
    """Run the reconciliation agent synchronously and return the report."""
    business_id_raw = request.args.get("business_id")
    business_id = None
    if business_id_raw:
        try:
            business_id = uuid.UUID(business_id_raw)
        except (ValueError, AttributeError, TypeError):
            return {"error": "business_id must be a valid UUID"}, 400

    forbidden = _require_access(user_id, business_id)
    if forbidden is not None:
        return forbidden

    payload = request.get_json(silent=True)
    source_ok, source_or_error = _source_from_payload(payload)
    if not source_ok:
        return {"error": source_or_error}, 400

    _, error, status = _lookup_user(user_id)
    if error is not None:
        return error, status

    try:
        report = run_reconciliation(user_id, business_id=business_id, source=source_or_error)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("reconciliation computation failed")
        return {"error": "internal server error"}, 500

    record = AuditRecord(
        user_id=user_id,
        business_id=business_id,
        kind="reconciliation",
        payload={
            "source": source_or_error,
            "batch_size": report.batch_size,
            "matched_count": report.matched_count,
            "match_rate": report.match_rate,
            "exception_count": len(report.exceptions),
        },
    )
    try:
        db.session.add(record)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("reconciliation audit persistence failed")
        return {"error": "internal server error"}, 500

    return report.to_dict(), 200


@m4_reconcile_bp.post("/<uuid:user_id>/reconcile/async")
@jwt_required()
def post_reconcile_async(user_id: uuid.UUID):
    """Dispatch the reconciliation agent as an asynchronous batch job."""
    business_id_raw = request.args.get("business_id")
    business_id = None
    if business_id_raw:
        try:
            business_id = uuid.UUID(business_id_raw)
        except (ValueError, AttributeError, TypeError):
            return {"error": "business_id must be a valid UUID"}, 400

    forbidden = _require_access(user_id, business_id)
    if forbidden is not None:
        return forbidden

    payload = request.get_json(silent=True)
    source_ok, source_or_error = _source_from_payload(payload)
    if not source_ok:
        return {"error": source_or_error}, 400

    _, error, status = _lookup_user(user_id)
    if error is not None:
        return error, status

    result = dispatch_reconciliation(
        str(user_id),
        source=source_or_error,
        business_id=business_id,
    )

    try:
        db.session.add(
            ControllerTask(
                task_id=uuid.UUID(str(result.id)),
                user_id=get_current_user_id(),
                business_id=business_id,
            )
        )
        db.session.commit()
    except (SQLAlchemyError, ValueError):
        db.session.rollback()
        current_app.logger.exception("reconciliation task ownership persistence failed")
        return {"error": "internal server error"}, 500

    return {"task_id": str(result.id), "status": "PENDING"}, 201


@m4_reconcile_bp.get("/<uuid:user_id>/reconcile/async/<uuid:task_id>")
@jwt_required()
def get_reconcile_task_status(user_id: uuid.UUID, task_id: uuid.UUID):
    """Return the current status/result of a previously dispatched batch.

    Authorization is task-scope aware. The task's persisted scope is the
    source of truth: a business-scoped task is readable by members of that
    business (identity-bound to the URL ``user_id``); a personal task remains
    owner-only. An unknown task id is rejected identically so task existence
    is never revealed.
    """
    forbidden = require_owner_or(user_id)
    if forbidden is not None:
        return forbidden

    _, error, status = _lookup_user(user_id)
    if error is not None:
        return error, status

    try:
        owner = get_current_user_id()
        owned = db.session.query(ControllerTask).filter_by(
            task_id=uuid.UUID(str(task_id))
        ).first()
    except SQLAlchemyError:
        current_app.logger.exception("task ownership lookup failed")
        return {"error": "internal server error"}, 500

    if owned is None:
        return FORBIDDEN

    if owned.business_id is not None:
        forbidden = require_business_data_access(owned.business_id, user_id)
        if forbidden is not None:
            return forbidden
    elif owned.user_id != owner:
        return FORBIDDEN

    result = task_result(str(task_id))
    state = result.state

    if state == "SUCCESS":
        return {
            "task_id": str(task_id),
            "status": "SUCCESS",
            "result": result.result,
        }, 200

    if state == "FAILURE":
        return {
            "task_id": str(task_id),
            "status": "FAILURE",
            "message": _FAILURE_MESSAGE,
        }, 200

    return {"task_id": str(task_id), "status": state}, 200


def _require_line_access(user_id, statement_line):
    """Enforce authorization for a single statement line.

    The line's persisted scope is the source of truth: a client can never
    pivot the requested ``user_id``/``business_id`` onto an unrelated line.
    Business-scoped lines are accessible to any business member; personal
    lines remain owner-only.
    """
    if statement_line.business_id is not None:
        return require_business_data_access(statement_line.business_id, user_id)
    if statement_line.user_id != user_id:
        return FORBIDDEN
    return require_owner_or(user_id)


def _lookup_statement_line(line_id):
    try:
        line = db.session.get(StatementLine, line_id)
    except SQLAlchemyError:
        current_app.logger.exception("statement line lookup failed")
        return None, {"error": "internal server error"}, 500
    if line is None:
        return None, {"error": "statement line not found"}, 404
    return line, None, None


@m4_reconcile_bp.patch("/<uuid:user_id>/reconcile/lines/<uuid:line_id>/review")
@jwt_required()
def patch_reconcile_line_review(user_id: uuid.UUID, line_id: uuid.UUID):
    """Update the human review status of a single statement line.

    Only the line's owner (or a member of its business) may change its review
    status. The body supplies the new ``review_status`` (UNRESOLVED, REVIEWED,
    or RESOLVED). This is a human-in-the-loop action and is audited.
    """
    line, error, status = _lookup_statement_line(line_id)
    if error is not None:
        return error, status

    forbidden = _require_line_access(user_id, line)
    if forbidden is not None:
        return forbidden

    payload = request.get_json(silent=True)
    new_status = payload.get("review_status") if isinstance(payload, dict) else None
    if new_status not in VALID_REVIEW_STATUSES:
        return {
            "error": "review_status must be one of: UNRESOLVED, REVIEWED, RESOLVED"
        }, 400

    line.review_status = new_status
    db.session.add(
        AuditRecord(
            user_id=user_id,
            business_id=line.business_id,
            kind="reconciliation",
            payload={
                "action": "review_status_update",
                "statement_line_id": str(line.id),
                "review_status": new_status,
            },
        )
    )
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("review status persistence failed")
        return {"error": "internal server error"}, 500

    return {
        "statement_line_id": str(line.id),
        "review_status": new_status,
    }, 200


@m4_reconcile_bp.post("/<uuid:user_id>/reconcile/lines/<uuid:line_id>/explain")
@jwt_required()
def post_reconcile_line_explain(user_id: uuid.UUID, line_id: uuid.UUID):
    """Return a proposal-only AI explanation for an unresolved statement line.

    The deterministic engine evidence for the line is the only input to the AI;
    the reply is always a proposal and never modifies any record. The line must
    currently be an exception.
    """
    line, error, status = _lookup_statement_line(line_id)
    if error is not None:
        return error, status

    forbidden = _require_line_access(user_id, line)
    if forbidden is not None:
        return forbidden

    if line.status != "exception":
        return {"error": "only exception lines can be explained"}, 400
    if not line.category:
        return {"error": "line has no classification to explain"}, 400

    evidence = ReconciliationException(
        statement_line_id=str(line.id),
        statement_amount=str(line.amount),
        statement_date=line.transaction_date.isoformat(),
        statement_description=line.description,
        category=line.category or "OTHER",
        reason="see stored line classification",
    )

    try:
        proposal = explain_reconciliation_exception(evidence)
    except AIConfigurationError:
        current_app.logger.exception("AI provider is not configured")
        return {"error": "AI provider is not configured"}, 503
    except AIProviderError:
        current_app.logger.exception("AI request failed")
        return {"error": "AI request failed"}, 502
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("explanation AI request failed")
        return {"error": "internal server error"}, 500

    return {
        "statement_line_id": str(line.id),
        "category": line.category,
        "explanation": proposal["explanation"],
        "suggested_resolution": proposal["suggested_resolution"],
        "is_proposal": True,
    }, 200
