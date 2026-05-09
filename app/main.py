from fastapi import FastAPI

from app.api.ingest import router as ingest_router
from app.api.query import router as query_router

app = FastAPI(title="IntelliDoc")

app.include_router(ingest_router)
app.include_router(query_router)
