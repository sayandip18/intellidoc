# IntelliDoc — Claude Code Context

## Project Overview

Agentic Document Intelligence Pipeline. Ingests documents (PDF, TXT, DOCX), processes them
through a LangGraph multi-node pipeline, stores chunks and embeddings in Postgres via pgvector,
and answers queries using hybrid search + self-correcting RAG (CRAG). Exposed via FastAPI.
No frontend, no auth, no multi-tenancy.

---

## Commands

### Install dependencies

```bash
pip install -e ".[dev]"
```

### Run FastAPI server

```bash
uvicorn app.main:app --reload
```

### Run Celery worker

```bash
celery -A app.worker.celery_app worker --loglevel=info
```

### Run tests

```bash
pytest
pytest tests/pipeline/          # run a specific module
pytest -k "test_chunker"        # run a specific test
```

### Lint and format

```bash
ruff check .
ruff format .
```

### Type checking

```bash
mypy app/
```

### Database migrations

```bash
alembic revision --autogenerate -m "description"   # generate migration
alembic upgrade head                                # apply migrations
alembic downgrade -1                                # rollback one step
```

### Start infra (Postgres + Redis + MinIO)

```bash
docker compose -f docker/docker-compose.yml up -d
```

---

## Architecture

### Request flows

**Ingestion flow:**
POST /ingest → file uploaded to MinIO → Celery task queued → LangGraph ingestion pipeline runs:
chunker node → embedder node → entity_extractor node → metadata_storer node
All output persisted to Postgres.

**Query flow:**
GET /query?q=... → hybrid search (pgvector dense + BM25 sparse) → RRF merge →
Cohere reranker → LangGraph CRAG loop (generate → score → rewrite if needed) →
SSE streamed response

---

## Project Structure

```
app/
├── api/                        # FastAPI routers
│   ├── ingest.py
│   └── query.py
├── core/                       # Config, DB engine, storage client
│   ├── config.py
│   ├── db.py
│   └── storage.py
├── graph/                      # LangGraph graphs
│   ├── crag/                   # CRAG query graph (runs in FastAPI async context)
│   │   ├── graph.py
│   │   ├── state.py
│   │   └── nodes/
│   │       ├── faithfulness_scorer.py
│   │       ├── generator.py
│   │       ├── query_rewriter.py
│   │       └── retriever.py
│   └── ingestion/              # Ingestion graph (runs in Celery worker)
│       ├── graph.py
│       ├── state.py
│       └── nodes/
│           ├── chunk_document.py
│           ├── embed_chunks.py
│           ├── extract_entities.py
│           ├── load_document.py
│           └── store_chunks.py
├── models/                     # SQLAlchemy ORM models
│   ├── base.py
│   ├── chunk.py
│   ├── document.py
│   ├── entity.py
│   └── job.py
├── retrieval/                  # Hybrid search + reranker
│   ├── dense.py
│   ├── reranker.py
│   ├── rrf.py
│   └── sparse.py
├── worker/                     # Celery app and tasks
│   ├── celery_app.py
│   └── ingest_task.py
└── main.py                     # FastAPI app entrypoint
```

---

## Key Conventions

### IDs

All primary keys are UUID strings, generated in Python via `generate_uuid()` in
`app/models/base.py`. Not DB-generated — this allows the ID to be known before DB insert.

### Async vs sync

- FastAPI layer is fully async (asyncpg driver)
- Celery workers are sync (psycopg2-binary driver)
- Never use sync SQLAlchemy sessions inside async FastAPI routes

### ORM models vs Pydantic schemas

- `app/models/` — SQLAlchemy ORM models, used for DB interaction only
- Pydantic request/response schemas are currently inlined in the API route files (`app/api/`)
- Never return ORM model objects directly from API endpoints — always serialize to schema

### Relationships

- `back_populates` is declared on both sides of every relationship
- `ondelete="CASCADE"` on all FKs pointing to `documents.id` — DB-level cleanup
- `ondelete="SET NULL"` on `entities.source_chunk_id` — chunk deletion doesn't kill entity

### LangGraph graphs

There are two separate graphs:

- `app/graph/ingestion/graph.py` — ingestion graph (runs inside Celery worker)
- `app/graph/crag/graph.py` — CRAG query graph (runs inside FastAPI async context)
  Keep their states, nodes, and chains strictly separate.

### Environment config

All config lives in `app/core/config.py` via Pydantic Settings.
Never hardcode secrets or connection strings. Always read from `.env`.
Copy `.env.example` to `.env` to get started.

---

## Database

### Tables

- `documents` — document metadata, raw text, ingestion status
- `chunks` — text chunks with pgvector embedding column
- `entities` — extracted entities (PERSON, ORG, DATE, LOCATION, CLAUSE, KEYWORD)
- `jobs` — Celery job tracking (linked 1:1 with a document)

### Embedding dimensions

Defined as `EMBEDDING_DIMENSIONS = 1536` in `app/models/chunk.py`.
Change this constant if switching from OpenAI to a different embedding model (Cohere = 1024).

### pgvector index

An HNSW index should be created on `chunks.embedding` for fast similarity search.
This is handled in an Alembic migration — do not add it manually.

---

## Environment Variables

```
# LLM
OPENAI_API_KEY=

# Reranker
COHERE_API_KEY=

# Postgres
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/intellidoc
SYNC_DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/intellidoc

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO / S3
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_UPLOAD_BUCKET=intellidoc-uploads
MINIO_ARCHIVE_BUCKET=intellidoc-archive

# Pipeline config
CHUNK_SIZE=512
CHUNK_OVERLAP=64
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini
CRAG_MAX_RETRIES=3
FAITHFULNESS_THRESHOLD=0.7
```

---

## What This Project Is Not

- Not production-ready — no auth, no rate limiting, no multi-tenancy
- Not a frontend project — test all endpoints via curl or Postman
- Not a microservices project — everything runs in one repo
