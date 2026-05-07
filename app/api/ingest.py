import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from app.worker.ingest_task import process_document

app = FastAPI()

ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_SIZE_MB = 10

@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}",
        )
    content = file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    
    encoded = base64.b64encode(content).decode("utf-8")
    task = process_document.delay(file.filename, encoded, file.content_type)

    return {"task_id": task.id, "filename": file.filename, "status": "queued"}

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    task = process_document.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None,
    }