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

NOTE (M7): authentication/authorization is intentionally not implemented in
this milestone. Route handlers carry the ``<uuid:user_id>`` path argument and
verify the user exists, but the next security milestone MUST bind a Celery
task to its owning authenticated user so a caller can only observe their own
tasks' results.
"""

import uuid

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from ..celery_client import dispatch_ai_controller, task_result
from ..extensions import db
from ..models import User
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
def post_ai_controller_async(user_id: uuid.UUID):
    """Validate input, verify the user, and dispatch the async controller task."""
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

    result = dispatch_ai_controller(str(user_id), intent_or_error)

    return {"task_id": str(result.id), "status": "PENDING"}, 201


@m4_controller_async_bp.get(
    "/<uuid:user_id>/ai-controller/async/<uuid:task_id>"
)
def get_ai_controller_task_status(user_id: uuid.UUID, task_id: uuid.UUID):
    """Return the current status of a previously dispatched controller task.

    This endpoint never blocks waiting for a running task and only reads the
    already-completed result when the task reached ``SUCCESS``.
    """
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

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

    # RETRY, PENDING, and (if task tracking were enabled) STARTED all return
    # their current state without retrieving the result for non-terminal work.
    return {"task_id": str(task_id), "status": state}, 200
