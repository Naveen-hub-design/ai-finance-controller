"""Celery application foundation for asynchronous finance tasks.

Business tasks are defined in the ``tasks`` package and referenced via the
Celery ``include`` list. M4.5 Step 2 introduces the first one:
``ai_controller.run_ai_controller``.
"""

import os

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)

celery = Celery(
    "finance_worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Acknowledge a job only after it finishes so transient failures may be
    # retried and a crashed task is not silently lost.
    task_acks_late=True,
)
