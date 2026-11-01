"""M4.5 Step 3: Asynchronous AI Finance Controller HTTP API endpoints.

Exposes the existing ``run_ai_controller`` Celery task over HTTP for
submission and status polling. The route only:

- parses/validates the JSON request body and ``intent`` (reusing the exact
  validation behavior of the synchronous ``m4_controller`` route),
- verifies the user exists,
- dispatches the already-registered Celery task by name,
- reads task status / completed results from the Celery result backend.

It never executes ``build_controller_report`` directly, never creates a job
database record, and never writes an audit record from the route: the Celery
task owns execution and audit persistence.

No financial calculations, no financial mutation, and no action execution
occur here. Intents and report contents are never logged.

NOTE (M7): M7.4 adds JWT authentication and URL-path ownership checks to both
endpoints so a caller can only submit to / poll for a user whose id matches
their own verified identity. M7.5 additionally binds each dispatched Celery
task to its authenticated owner via ``ControllerTask`` at submission time and
enforces that binding before the status/result endpoint ever touches the
Celery ``AsyncResult``. A ``task_id`` alone therefore cannot authorize access,
and a valid JWT for one user can never read another user's task result.
"""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from ..auth import get_current_user_id
from ..celery_client import dispatch_ai_controller, task_result
from ..extensions import db
from ..models import ControllerTask, User
from ..services.openai_provider import AIConfigurationError
from ._authorization import require_business_data_access
from ._ownership import FORBIDDEN, require_owner_or
from .m4_controller import _intent_from_payload

# A safe, generic message returned on FAILURE. It deliberately exposes no
# traceback, exception internals, secrets, API keys, prompts, or request data.
_FAILURE_MESSAGE = "the task did not complete successfully"


m4_controller_async_bp = Blueprint(
    "m4_controller_async",
    __name__,
    url_prefix="/api/users",
)


@m4_controller_async_bp.post("/<uuid:user_id>/ai-controller/async")
@jwt_required()
def post_ai_controller_async(user_id: uuid.UUID):
    """Validate input, verify ownership, and dispatch the async controller task."""
    business_id_raw = request.args.get("business_id")
    business_id = None
    if business_id_raw:
        try:
            business_id = uuid.UUID(business_id_raw)
        except (ValueError, AttributeError, TypeError):
            return {"error": "business_id must be a valid UUID"}, 400
        forbidden = require_business_data_access(business_id, user_id)
        if forbidden is not None:
            return forbidden
    else:
        forbidden = require_owner_or(user_id)
        if forbidden is not None:
            return forbidden

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

    result = dispatch_ai_controller(str(user_id), intent_or_error, business_id=business_id)

    # M7.5: bind the dispatched task to the authenticated owner. The identity
    # is resolved exclusively from the verified JWT (never a client value) and
    # `require_owner_or` above already guaranteed it matches the URL user_id.
    # The mapping is written here, at dispatch time, so it exists independently
    # of the Redis result backend.
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
        # The task was dispatched but is not (or cannot be) securely owned, so
        # its result must not become readable through the protected endpoint.
        # Roll back and report a generic error without exposing the task id.
        db.session.rollback()
        current_app.logger.exception("async controller task ownership persistence failed")
        return {"error": "internal server error"}, 500

    return {"task_id": str(result.id), "status": "PENDING"}, 201


@m4_controller_async_bp.get(
    "/<uuid:user_id>/ai-controller/async/<uuid:task_id>"
)
@jwt_required()
def get_ai_controller_task_status(user_id: uuid.UUID, task_id: uuid.UUID):
    """Return the current status of a previously dispatched controller task.

    This endpoint never blocks waiting for a running task and only reads the
    already-completed result when the task reached ``SUCCESS``.

    Authorization is task-scope aware. The task's persisted scope is the
    source of truth: a business-scoped task is readable by members of that
    business (identity-bound to the URL ``user_id``); a personal task remains
    owner-only. An unknown task id is rejected identically so task existence
    is never revealed, and the Celery ``AsyncResult`` is only touched after
    the task-scope check passes.
    """
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

    # M7.5: the task id must be authorized before any Celery result is
    # retrieved. An unknown task id and one outside the caller's scope return
    # the same forbidden response, so neither Redis task data nor ownership
    # details leak to an unauthorized caller.
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
        # Keep the documented generic message for every real failure, but give
        # the known-global "provider not configured" case the same explicit
        # contract the synchronous AI endpoints already return (503) so the
        # frontend can show a clear "AI unavailable" state instead of an
        # opaque failure. Only the exception type is inspected -- never its
        # internal message, traceback, or payload.
        try:
            failed = result.result
            if isinstance(failed, AIConfigurationError):
                return {"error": "AI provider is not configured"}, 503
        except Exception:
            current_app.logger.exception(
                "could not classify failed controller task"
            )
        return {
            "task_id": str(task_id),
            "status": "FAILURE",
            "message": _FAILURE_MESSAGE,
        }, 200

    # RETRY, PENDING, and (if task tracking were enabled) STARTED all return
    # their current state without retrieving the result for non-terminal work.
    return {"task_id": str(task_id), "status": state}, 200
