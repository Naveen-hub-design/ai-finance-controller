FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Reuse the backend's exact dependency set so the worker and API never
# diverge. This installs Flask, SQLAlchemy, celery, redis, and the other
# dependencies the backend `app` package requires.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Single source of truth: reference the same `app` package the API uses.
# The worker provides no duplicate implementation of backend business logic.
COPY backend/app ./app

# Worker-specific runtime.
COPY worker/celery_app.py ./celery_app.py
COPY worker/tasks ./tasks

# Generic entrypoint; future M4.5 tasks are registered in worker/tasks.
CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
