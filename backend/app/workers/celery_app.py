"""Celery Application Configuration for MarginOps Background Workers.

Note on Windows Execution:
Celery's default prefork worker pool is not supported natively on Windows due to
lack of POSIX fork(). Worker execution is deferred to containerized Linux environments
via Docker Compose. For local debugging on Windows without Docker, invoke with:
`celery -A app.workers.celery_app worker --loglevel=info --pool=solo`
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "marginops_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)
