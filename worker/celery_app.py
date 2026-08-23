"""Celery application foundation for asynchronous finance tasks.

No business tasks are defined in M01. Later milestones register tasks in
the ``tasks`` package and reference them via the Celery ``include`` list.
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
)
