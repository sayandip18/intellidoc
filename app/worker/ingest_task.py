from app.core.storage import get_s3_client
from app.worker.celery_app import celery_app
from config import settings


@celery_app.task(
    name="process_document",
    bind=True,
    max_retries=settings.max_retries,
    default_retry_delay=settings.retry_backoff,
)
def process_document(self, filename: str, s3_key: str, content_type: str):
    client = get_s3_client()

    try:
        response = client.get_object(Bucket=settings.minio_upload_bucket, Key=s3_key)
        content: bytes = response["Body"].read()
    except Exception as exc:
        raise self.retry(exc=exc)

    if content_type == "text/plain":
        text = content.decode("utf-8")
        # TODO: pass `text` into the LangGraph ingestion pipeline

    elif content_type == "application/pdf":
        # TODO: parse with PyMuPDF / pdfplumber, then pipeline
        pass

    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        # TODO: parse with python-docx, then pipeline
        pass

    archive_key = s3_key.replace("uploads/", "archive/", 1)
    client.copy_object(
        CopySource={"Bucket": settings.minio_upload_bucket, "Key": s3_key},
        Bucket=settings.minio_archive_bucket,
        Key=archive_key,
    )
    client.delete_object(Bucket=settings.minio_upload_bucket, Key=s3_key)

    return {"status": "done", "filename": filename, "archived_key": archive_key}
