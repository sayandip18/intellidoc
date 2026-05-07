from app.worker.celery_app import celery_app

@celery_app.task(name="process_document")
def process_document(filename: str, content: bytes, content_type: str):
    """
    Receives the raw file bytes and processes them.
    Add your PDF/DOCX/TXT parsing logic here.
    """
    print(f"Processing: {filename} ({content_type}), size: {len(content)} bytes")

    if content_type == "text/plain":
        text = content.decode("utf-8")
        # ... handle txt

    elif content_type == "application/pdf":
        # e.g. use PyMuPDF / pdfplumber
        pass

    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        # e.g. use python-docx
        pass

    return {"status": "done", "filename": filename}