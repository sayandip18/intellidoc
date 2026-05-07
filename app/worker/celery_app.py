from celery import Celery

celery_app = Celery(
    "intellidoc",
    broker="redis://localhost:6379/0",   # db 0 for broker
    backend=None,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,  # TTL on stored results
    task_track_started=True,  # so STARTED state is actually written
    task_routes={
        "process_document": {"queue": "ingest"},
        "send_notification": {"queue": "default"},
    },
    task_default_queue="ingest",
)