"""Multi-source financial reconciliation Celery task.

Runs the deterministic reconciliation agent off the HTTP request path across
a batch of external statement lines and persists an auditable report.

Design rules honored here (consistent with the rest of the project):

- **No financial logic duplication.** All matching is delegated to the
  existing reconciliation service ``run_reconciliation``.
- **Deterministic, no retry.** Unlike the AI provider task, reconciliation is
  purely deterministic and never touches an external AI service, so there is
  nothing transient to retry. Input validation and database errors fail the
  task permanently.
- **App context per execution.** A fresh Flask app is created and its context
  pushed inside the task body, never at module import time.
- **Session hygiene.** ``db.session.remove()`` is guaranteed in ``finally``.
- **Auditable.** On success a ``kind="reconciliation"`` ``AuditRecord`` is
  written carrying the Celery task id so the write is idempotent across
  re-delivery.
- **No sensitive logging.** Only generic task lifecycle messages are logged;
  statement line contents, amounts, and descriptions are never logged.
"""

import uuid

from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import AuditRecord
from app.services.m4.reconciliation import run_reconciliation
from celery_app import celery


def _reconciliation_exists(user_id, task_id: str) -> bool:
    """Return True when a reconciliation audit record exists for task_id.

    Idempotency is keyed off the Celery task id stored inside the JSON
    ``payload``, matching the controller-task audit pattern.
    """
    records = (
        db.session.query(AuditRecord)
        .filter(
            AuditRecord.user_id == user_id,
            AuditRecord.kind == "reconciliation",
        )
        .all()
    )
    for record in records:
        payload = record.payload
        if isinstance(payload, dict) and payload.get("task_id") == task_id:
            return True
    return False


def _write_reconciliation_audit(
    user_id, business_id, task_id: str, report: dict
) -> None:
    """Persist an immutable reconciliation audit record for a completed run."""
    record = AuditRecord(
        user_id=user_id,
        business_id=business_id,
        kind="reconciliation",
        payload={
            "task_id": task_id,
            "result": report,
        },
    )
    db.session.add(record)
    db.session.commit()


@celery.task(
    name="run_reconciliation_batch",
    bind=True,
    acks_late=True,
)
def run_reconciliation_batch(self, user_id: str, source: str = "bank_statement", business_id: str | None = None) -> dict:
    """Run the multi-source reconciliation agent as an asynchronous job.

    Args:
        user_id: The user's UUID as a string. Invalid UUIDs fail permanently.
        source: The external source label to reconcile.
        business_id: Optional business scope as a string.

    Returns:
        The JSON-serializable ``ReconciliationReport.to_dict()``.
    """
    user_uuid = uuid.UUID(str(user_id))
    business_uuid = uuid.UUID(str(business_id)) if business_id else None

    task_id = self.request.id
    app = create_app(Config)

    try:
        with app.app_context():
            report = run_reconciliation(user_uuid, business_id=business_uuid, source=source)
            result = report.to_dict()

            if not _reconciliation_exists(user_uuid, task_id):
                try:
                    _write_reconciliation_audit(
                        user_uuid, business_uuid, task_id, result
                    )
                except SQLAlchemyError:
                    db.session.rollback()
                    raise
    finally:
        with app.app_context():
            db.session.remove()

    return result
