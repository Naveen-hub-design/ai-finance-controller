"""M4.5 Step 2: Asynchronous AI Finance Controller Celery task.

This is the first real asynchronous task for the AI Finance Controller. It
runs the existing controller service off the HTTP request path and persists
an auditable decision.

Design rules honored here (consistent with the rest of the project):

- **No financial calculations.** The task never performs arithmetic and never
  queries transactions, accounts, budgets, categories, or financial goals.
  All financial reasoning is delegated to the existing controller service
  ``build_controller_report``.
- **Proposal-only.** The task never executes any proposed controller action,
  never transfers/pays/approves/refunds, and never mutates financial records.
- **App context per execution.** A fresh Flask app is created and its context
  pushed inside the task body, never at module import time.
- **Session hygiene.** ``db.session.remove()`` is guaranteed in ``finally``.
- **Auditable.** On success a ``kind="decision"`` ``AuditRecord`` is written,
  carrying the Celery task id so the write is idempotent across re-delivery.
- **Retry only transient AI failures.** Only ``AIProviderError`` is retried
  (with bounded exponential backoff). Permanent failures -- invalid UUID,
  missing AI configuration, database errors -- are never retried.
- **No sensitive logging.** Only generic task lifecycle messages are logged;
  intents, financial context, source facts, money values, model responses,
  prompts, and API keys are never logged.
"""

import uuid

from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import AuditRecord
from app.services.m4.controller import build_controller_report
from app.services.openai_provider import (
    AIConfigurationError,
    AIProviderError,
)
from celery_app import celery

# The only retried failure class: transient OpenAI/transport/rate-limit
# failures raised by the existing provider. Permanent failures are not retried.
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 5  # seconds


def _decision_exists(user_id, task_id: str) -> bool:
    """Return True when a decision audit record already exists for task_id.

    There is no dedicated task_id column; idempotency is keyed off the
    Celery task id stored inside the JSON ``payload``. This keeps the audit
    write idempotent across broker re-delivery without any schema change.
    """
    records = (
        db.session.query(AuditRecord)
        .filter(
            AuditRecord.user_id == user_id,
            AuditRecord.kind == "decision",
        )
        .all()
    )
    for record in records:
        payload = record.payload
        if isinstance(payload, dict) and payload.get("task_id") == task_id:
            return True
    return False


def _write_decision_audit(user_id, task_id: str, intent: str, result: dict) -> None:
    """Persist an immutable decision audit record for a completed run."""
    record = AuditRecord(
        user_id=user_id,
        kind="decision",
        payload={
            "task_id": task_id,
            "result": result,
            "intent": intent,
        },
    )
    db.session.add(record)
    db.session.commit()


@celery.task(
    name="run_ai_controller",
    bind=True,
    acks_late=True,
    max_retries=_MAX_RETRIES,
    default_retry_delay=_RETRY_BASE_DELAY,
    retry_backoff=True,
    retry_backoff_max=60,
)
def run_ai_controller(self, user_id: str, intent: str) -> dict:
    """Run the AI finance controller for a user as an asynchronous job.

    Args:
        user_id: The user's UUID as a string. Invalid UUIDs fail permanently;
            they are never retried.
        intent: The user's intent / question for the controller.

    Returns:
        The JSON-serializable ``FinancialControllerReport.to_dict()``.
    """
    # Validate up front. A non-UUID input is a permanent input error, so it
    # is raised before any controller work and never retried.
    user_uuid = uuid.UUID(str(user_id))

    task_id = self.request.id
    app = create_app(Config)

    try:
        with app.app_context():
            try:
                report = build_controller_report(user_uuid, intent)
            except AIConfigurationError:
                # Missing/misconfigured provider is permanent -- never retried.
                raise
            except AIProviderError as exc:
                # Transient OpenAI/transport/rate-limit failure -- retry.
                raise self.retry(exc=exc)
            result = report.to_dict()

            if not _decision_exists(user_uuid, task_id):
                try:
                    _write_decision_audit(user_uuid, task_id, intent, result)
                except SQLAlchemyError:
                    db.session.rollback()
                    raise
    finally:
        with app.app_context():
            db.session.remove()

    return result
