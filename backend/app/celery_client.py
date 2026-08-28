"""M4.5 Step 3: lightweight Celery producer/result client for the API.

Makes the already-registered ``run_ai_controller`` task reachable from the
API by dispatching messages onto the same broker and reading results from the
same result backend the worker uses.

Design rules honored here:

- **Worker-owned execution.** This module only *produces* messages and reads
  results; it never registers or executes tasks. Task registration and
  execution remain the responsibility of the worker (``worker/celery_app.py``
  + ``worker/tasks``).
- **Dispatches by registered name.** Tasks are sent via ``send_task`` using
  the exact registered task name, so this module never imports the worker
  task function (``worker.tasks.ai_controller``) and never duplicates its
  implementation.
- **No worker source.** ``worker.celery_app`` and ``worker.tasks`` are never
  imported; celery is not "moved" into the backend.
- **Configuration parity.** The broker, result backend, app name, and
  serialization match the worker so an API-dispatched message lands on the
  same Redis broker the worker consumes and its result can be read back.
"""

import os

from celery import Celery

# Broker / result backend configuration mirrors worker/celery_app.py so the
# API produces to and reads from the same Redis instance as the worker.
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

# The exact task name registered by worker/tasks/ai_controller.py.
RUN_AI_CONTROLLER_TASK = "run_ai_controller"

celery_client = Celery(
    "finance_worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_client.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


def dispatch_ai_controller(user_id, intent):
    """Dispatch the registered ``run_ai_controller`` task and return an AsyncResult.

    Args:
        user_id: The user's UUID (string or ``uuid.UUID``).
        intent: The user's intent / question for the controller.

    Returns:
        An ``AsyncResult`` whose ``.id`` is the dispatched Celery task id.
    """
    return celery_client.send_task(
        RUN_AI_CONTROLLER_TASK,
        args=[str(user_id), intent],
    )


def task_result(task_id) -> "AsyncResult":
    """Return the ``AsyncResult`` for a previously dispatched task."""
    return celery_client.AsyncResult(task_id)
