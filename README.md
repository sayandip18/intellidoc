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

## Project Goals

This project is scoped to backend and AI engineering depth:

- Stateful multi-node agent graphs with LangGraph
- Hybrid retrieval with dense + sparse search fusion
- Self-correcting RAG with automatic query reformulation
- Async FastAPI with background job processing via Celery
- Clean module separation between ingestion pipeline, retrieval, and RAG layers

No frontend. No auth. No multi-tenancy. Just the core engineering.

## To Run

Activate venv

```
.venv\Scripts\activate
```
