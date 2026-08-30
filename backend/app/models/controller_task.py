"""M7.5 async controller task ownership model.

Binds a dispatched Celery ``run_ai_controller`` task to the authenticated
user who submitted it. This is the authorization source of truth for the
async task-status endpoint: ``task_id`` alone must never grant access, so a
valid JWT for one user can never read another user's Celery task result just
by knowing its id.

Design rules:

- **Authorization only.** This record exists solely to answer "which user owns
  this task id". It stores no financial data, no AI prompts/responses, no
  JWTs, no passwords, no Celery result contents, and no remote task metadata.
- **Created at dispatch.** The ownership mapping is written by the API at
  submission time -- before the worker finishes -- so it exists independently
  of (and regardless of) the Redis result backend.
- **Unique task id.** A task id maps to exactly one owner, so lookup is
  deterministic and cannot expose another user's result.
- **User scoped.** ``user_id`` references ``users.id`` with ``ON DELETE
  CASCADE``, matching the existing models.
- **Python/dialect-portable defaults.** A Python-side UUID default keeps
  inserts portable across dialects (the test suite runs on in-memory SQLite);
  the PostgreSQL server default is kept for inserts made outside the ORM.
"""

import uuid

from ..extensions import db


class ControllerTask(db.Model):
    """Ownership binding between a Celery task and its submitting user."""

    __tablename__ = "controller_tasks"

    id = db.Column(
        db.Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("gen_random_uuid()"),
    )
    # The Celery task id returned by ``send_task``; unique so a single task
    # cannot be claimed by more than one owner.
    task_id = db.Column(
        db.Uuid,
        nullable=False,
        unique=True,
        index=True,
    )
    user_id = db.Column(
        db.Uuid,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )
