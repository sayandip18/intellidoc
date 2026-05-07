from app.worker.celery_app import celery_app
from app.worker.ingest_task import process_document

__all__ = ["celery_app", "process_document"]
