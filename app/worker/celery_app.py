from celery import Celery
from config import settings

celery_app = Celery("intellidoc")
celery_app.config_from_object(settings.celery_config)
celery_app.conf.update(
    task_routes={
        "process_document": {"queue": "ingest"},
        "send_notification": {"queue": "default"},
    },
    task_default_queue="ingest",
)
