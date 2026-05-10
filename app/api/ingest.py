import asyncio
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.storage import ensure_buckets, get_s3_client
from app.worker.ingest_task import process_document
from app.core.config import settings

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_SIZE_MB = 30


@router.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}",
        )

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    s3_key = f"uploads/{uuid.uuid4()}/{file.filename}"

    def _upload() -> None:
        client = get_s3_client()
        ensure_buckets(client)
        client.put_object(
            Bucket=settings.minio_upload_bucket,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type,
        )

    try:
        await asyncio.to_thread(_upload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Storage upload failed: {exc}") from exc

    task = process_document.delay(file.filename, s3_key, file.content_type)

    return {"task_id": task.id, "filename": file.filename, "s3_key": s3_key, "status": "queued"}


@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    task = process_document.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None,
    }
