"""Task modules for the finance worker.

M4.5 Step 2 defines the first real business task: the asynchronous AI
Finance Controller (``ai_controller.run_ai_controller``). Later milestones
add further task modules here; each is referenced through the Celery
``include`` list in ``celery_app.py``.
"""

from . import ai_controller  # noqa: F401
