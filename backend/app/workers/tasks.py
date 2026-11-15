"""Celery task declarations for MarginOps foundation."""
from typing import Dict, Any
from app.workers.celery_app import celery_app


@celery_app.task(name="marginops.foundation_ping")
def foundation_ping() -> Dict[str, Any]:
    """Basic task to verify Celery task registration and configuration."""
    return {"status": "ok", "message": "Celery worker configuration initialized"}
