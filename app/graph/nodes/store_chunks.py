"""
Persists the fully-processed document to the database:

  1. chunks + embeddings  →  pgvector (documents.chunks table)
     Uses pgvector's vector column for dense ANN search.
     Also stores the raw chunk text for BM25 sparse search via
     a tsvector column (populated by a Postgres trigger or here directly).

  2. entities             →  relational metadata table (documents.entities)

  3. document record      →  documents.documents  (status = 'completed')

Uses psycopg3 (psycopg) with asyncio support — but this node is called
synchronously from the Celery worker, so we use the sync connection API.
"""

from __future__ import annotations

import logging
import os
import uuid

import psycopg
from pgvector.psycopg import register_vector

from state import IngestionState, IngestionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

_UPSERT_DOCUMENT = """
    INSERT INTO documents (id, filename, file_type, status)
    VALUES (%s, %s, %s, 'completed')
    ON CONFLICT (id)
    DO UPDATE SET status = 'completed';
"""

_INSERT_CHUNK = """
    INSERT INTO chunks (id, document_id, chunk_index, text, embedding)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (document_id, chunk_index) DO UPDATE
        SET text      = EXCLUDED.text,
            embedding = EXCLUDED.embedding;
"""

_INSERT_ENTITY = """
    INSERT INTO entities (id, document_id, source_chunk_id, entity_type, value)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT DO NOTHING;
"""


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def store_chunks(state: IngestionState) -> dict:
    """
    LangGraph node — store_chunks.

    Writes chunks, embeddings, entities, and a document status record
    to Postgres / pgvector in a single transaction.
    """
    doc_id = state["document_id"]
    logger.info("store_chunks | doc_id=%s  chunks=%d", doc_id, len(state.get("chunks", [])))

    chunks     = state.get("chunks", [])
    embeddings = state.get("embeddings", [])
    entities   = state.get("entities", [])
    metadata   = state.get("chunk_metadata", [])

    # -----------------------------------------------------------------------
    # Validate state is coherent before touching the DB
    # -----------------------------------------------------------------------
    if not chunks:
        msg = "store_chunks: no chunks to store."
        logger.error(msg)
        return {
            "status":     IngestionStatus.FAILED,
            "errors":     [msg],
            "node_trace": ["store_chunks"],
        }

    if len(embeddings) != len(chunks):
        msg = (
            f"store_chunks: embedding/chunk count mismatch "
            f"({len(embeddings)} vs {len(chunks)})."
        )
        logger.error(msg)
        return {
            "status":     IngestionStatus.FAILED,
            "errors":     [msg],
            "node_trace": ["store_chunks"],
        }

    # -----------------------------------------------------------------------
    # Write to Postgres in one transaction
    # -----------------------------------------------------------------------
    dsn = os.environ["POSTGRES_DSN"]

    # Pre-generate chunk IDs so entities can reference them via source_chunk_id.
    chunk_ids = [str(uuid.uuid4()) for _ in chunks]
    chunk_index_to_id = {
        meta.get("chunk_index", idx): chunk_id
        for idx, (meta, chunk_id) in enumerate(zip(metadata, chunk_ids))
    }

    try:
        with psycopg.connect(dsn) as conn:
            register_vector(conn)   # enables pgvector <-> Python list conversion

            with conn.transaction():

                # 1. Upsert the parent document record
                conn.execute(
                    _UPSERT_DOCUMENT,
                    (
                        doc_id,
                        state["source_path"],
                        state["file_type"].value,
                    ),
                )

                # 2. Insert all chunks + embeddings
                chunk_rows = [
                    (
                        chunk_id,
                        doc_id,
                        meta.get("chunk_index", idx),
                        doc.page_content,
                        embedding,          # psycopg + pgvector handles list→vector
                    )
                    for idx, (chunk_id, doc, embedding, meta) in enumerate(zip(chunk_ids, chunks, embeddings, metadata))
                ]
                with conn.cursor() as cur:
                    cur.executemany(_INSERT_CHUNK, chunk_rows)

                    # 3. Insert extracted entities
                    if entities:
                        entity_rows = [
                            (
                                str(uuid.uuid4()),
                                doc_id,
                                chunk_index_to_id.get(ent["chunk_index"]),
                                ent["label"],
                                ent["text"],
                            )
                            for ent in entities
                        ]
                        cur.executemany(_INSERT_ENTITY, entity_rows)

    except psycopg.Error as exc:
        msg = f"store_chunks: database error for doc_id={doc_id}: {exc}"
        logger.exception(msg)
        return {
            "status":     IngestionStatus.FAILED,
            "errors":     [msg],
            "node_trace": ["store_chunks"],
        }

    logger.info(
        "store_chunks | doc_id=%s  stored chunks=%d  entities=%d — DONE",
        doc_id, len(chunks), len(entities),
    )

    return {
        "status":     IngestionStatus.DONE,
        "node_trace": ["store_chunks"],
    }
