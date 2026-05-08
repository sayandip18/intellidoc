# IntelliDoc — Agentic Document Intelligence Pipeline

A backend-focused AI engineering project that ingests documents, processes them through a
multi-stage LangGraph agent pipeline, and exposes intelligent querying via a FastAPI REST API.
Built to explore production-grade patterns in RAG, agentic orchestration, and async backend
systems — without the overhead of auth, multi-tenancy, or a frontend.

---

## What It Does

- **Ingests** PDFs, plain text, and Word documents via an async API endpoint backed by Celery workers
- **Processes** documents through a stateful LangGraph pipeline — chunking, embedding, entity extraction, and metadata storage
- **Retrieves** relevant context using hybrid search (pgvector dense search + BM25 sparse search), merged with Reciprocal Rank Fusion (RRF) and reranked via Cohere
- **Answers** queries using a self-correcting RAG loop (CRAG) — if the generated answer scores low on faithfulness against retrieved chunks, the query is automatically reformulated and retried
- **Streams** final answers token-by-token back to the client via Server-Sent Events (SSE), with intermediate agent step visibility

---

## Tech Stack

| Layer            | Technology                           |
| ---------------- | ------------------------------------ |
| API              | FastAPI, Uvicorn, SSE-Starlette      |
| Task Queue       | Celery, Redis                        |
| AI Orchestration | LangGraph, LangChain                 |
| Embeddings & LLM | OpenAI                               |
| Reranker         | Cohere                               |
| Vector Store     | Postgres + pgvector                  |
| ORM & Migrations | SQLAlchemy (async), Alembic          |
| Validation       | Pydantic v2                          |
| Document Parsing | pypdf, python-docx                   |
| Search           | pgvector (dense), rank-bm25 (sparse) |
| Testing          | Pytest, pytest-asyncio, HTTPX        |

---

## Architecture Overview

```text
POST /ingest
↓
Celery Worker
↓
LangGraph Ingestion Pipeline
├── Chunker node
├── Embedder node
├── Entity Extractor node
└── Metadata Storer node
↓
Postgres + pgvector

GET /query?q=...
↓
Hybrid Search (pgvector + BM25 → RRF merge)
↓
Cohere Reranker
↓
LangGraph CRAG Loop
├── Generator node
├── Faithfulness Scorer node
└── Query Rewriter node (on retry)
↓
SSE Streamed Response
```

---

## Known Limitations & Planned Optimizations

### BM25 index rebuilt on every query

`sparse_search` currently loads the full chunk corpus from Postgres and rebuilds a
`BM25Okapi` index on every request. This is intentional — it keeps the implementation
simple while the end-to-end pipeline is being proven. At scale it becomes a bottleneck. To fix:

- **Pre-built index** — serialize the BM25 index (e.g. with `pickle`) after each ingestion
  run and store it in Redis or on disk.
- **Redis cache** — cache the serialized index with a TTL; invalidate and rebuild when new
  chunks are stored (hook into the `store_chunks` LangGraph node).
- **Incremental update** — BM25Okapi does not support incremental updates, so the rebuild
  must cover the full corpus; with a Redis-cached index the cost is paid once per ingestion
  batch rather than once per query.

---

## Project Goals

This project is scoped to backend and AI engineering depth:

- Stateful multi-node agent graphs with LangGraph
- Hybrid retrieval with dense + sparse search fusion
- Self-correcting RAG with automatic query reformulation
- Async FastAPI with background job processing via Celery
- Clean module separation between ingestion pipeline, retrieval, and RAG layers

## Ingestion graph topology

```
Graph topology:

    START
      │
      ▼

load_document ──[FAILED]──► END
│
▼
chunk_document ──[FAILED]──► END
│
▼
embed_chunks ──[FAILED]──► END
│
▼
extract_entities ──[FAILED]──► END
│
▼
store_chunks ──[FAILED]──► END
│
▼
END
```

## To Run (Dev)

### 1. Prerequisites

- Docker Desktop running
- Python 3.11+
- An `.env` file at the repo root (see below)

### 2. Configure environment

Copy the example and fill in your API keys:

```bash
cp .env.example .env
```

Minimum required values:

```env
OPENAI_API_KEY=sk-...
COHERE_API_KEY=...

DATABASE_URL=postgresql+asyncpg://intellidoc:intellidoc@localhost:5432/intellidoc
SYNC_DATABASE_URL=postgresql+psycopg2://intellidoc:intellidoc@localhost:5432/intellidoc
REDIS_URL=redis://localhost:6379/0
```

The Postgres and Redis credentials match what `docker-compose.yml` sets by default — no changes needed if you use the bundled infra.

### 3. Start infra + app with hot reload

```bash
cd docker
docker compose up --build
```

This spins up:

- **Postgres** (pgvector/pgvector:pg16) on port `5432`
- **Redis** on port `6379`
- **API** (uvicorn `--reload`) on port `8000` — restarts on any `.py` change under `app/`
- **Worker** (Celery + watchmedo) — restarts on any `.py` change under `app/`

`docker-compose.override.yml` is picked up automatically and enables the hot-reload mounts. No extra flags needed.

### 4. Run database migrations

With the containers running, apply Alembic migrations:

```bash
docker compose exec api alembic upgrade head
```

### 5. Verify

```bash
curl http://localhost:8000/health
```

---

### Running locally (without Docker)

If you prefer to run the API and worker directly on your machine while Docker provides infra:

```bash
# Start only Postgres + Redis
docker compose up postgres redis

# In one terminal — activate venv and start API
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
uvicorn app.main:app --reload

# In another terminal — start Celery worker
celery -A app.worker.celery_app worker --loglevel=info -Q ingest,default
```

---

### Useful commands

| Action                | Command                                                                    |
| --------------------- | -------------------------------------------------------------------------- |
| Tail all logs         | `docker compose logs -f`                                                   |
| Tail API only         | `docker compose logs -f api`                                               |
| Tail worker only      | `docker compose logs -f worker`                                            |
| Open psql shell       | `docker compose exec postgres psql -U intellidoc`                          |
| Generate migration    | `docker compose exec api alembic revision --autogenerate -m "description"` |
| Rollback one step     | `docker compose exec api alembic downgrade -1`                             |
| Stop everything       | `docker compose down`                                                      |
| Stop + wipe DB volume | `docker compose down -v`                                                   |
