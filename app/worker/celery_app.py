from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "intellidoc",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_routes={
        "process_document": {"queue": "ingest"},
        "send_notification": {"queue": "default"},
    },
    task_default_queue="ingest",
)
