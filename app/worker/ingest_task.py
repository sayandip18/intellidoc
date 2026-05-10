from __future__ import annotations

import hashlib
import uuid
import tempfile
from pathlib import Path

from app.core.storage import get_s3_client
from app.worker.celery_app import celery_app
from app.core.config import settings
from app.graph.ingestion.graph import ingestion_graph
from app.graph.ingestion.state import FileType, IngestionState, IngestionStatus


_CONTENT_TYPE_TO_FILE_TYPE: dict[str, FileType] = {
    "application/pdf": FileType.PDF,
    "text/plain": FileType.TXT,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
}


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

    file_type = _CONTENT_TYPE_TO_FILE_TYPE.get(content_type)
    if file_type is None:
        raise ValueError(f"Unsupported content type: {content_type}")

    document_id = str(uuid.uuid4())
    content_hash = hashlib.sha256(content).hexdigest()

    with tempfile.NamedTemporaryFile(suffix=f".{file_type.value}", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        initial_state: IngestionState = {
            "document_id": document_id,
            "filename": filename,
            "content_hash": content_hash,
            "source_path": tmp_path,
            "file_type": file_type,
            "raw_content": None,
            "chunks": [],
            "embeddings": [],
            "entities": [],
            "chunk_metadata": [],
            "status": IngestionStatus.PENDING,
            "errors": [],
            "node_trace": [],
        }
        final_state = ingestion_graph.invoke(initial_state)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if final_state.get("status") == IngestionStatus.FAILED:
        errors = final_state.get("errors", [])
        raise RuntimeError(f"Ingestion pipeline failed for '{filename}': {errors}")

    archive_key = s3_key.replace("uploads/", "archive/", 1)
    client.copy_object(
        CopySource={"Bucket": settings.minio_upload_bucket, "Key": s3_key},
        Bucket=settings.minio_archive_bucket,
        Key=archive_key,
    )
    client.delete_object(Bucket=settings.minio_upload_bucket, Key=s3_key)

    return {
        "status": "done",
        "filename": filename,
        "document_id": document_id,
        "archived_key": archive_key,
        "chunks_stored": len(final_state.get("chunks", [])),
    }
