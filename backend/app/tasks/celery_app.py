# app/tasks/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "fullstack_rag_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.pdf_processing_tasks']
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
    task_annotation={'*': {'rate_limit': '300/m'}},
    broker_connection_retry_on_startup=True
)