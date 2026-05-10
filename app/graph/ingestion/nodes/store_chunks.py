"""
Persists the fully-processed document to the database:

  1. chunks + embeddings  →  pgvector (chunks table)
  2. entities             →  entities table
  3. document record      →  documents table  (status = 'completed')

Uses psycopg3 sync API — this node runs inside the Celery worker.
"""

from __future__ import annotations

import logging
import uuid

import psycopg
from pgvector.psycopg import register_vector

from app.core.config import settings
from app.graph.ingestion.state import IngestionState, IngestionStatus

logger = logging.getLogger(__name__)

_UPSERT_DOCUMENT = """
    INSERT INTO documents (id, filename, file_type, content_hash, status)
    VALUES (%s, %s, %s, %s, 'completed')
    ON CONFLICT (id)
    DO UPDATE SET
        filename     = EXCLUDED.filename,
        file_type    = EXCLUDED.file_type,
        content_hash = EXCLUDED.content_hash,
        status       = 'completed';
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


def store_chunks(state: IngestionState) -> dict:
    doc_id = state["document_id"]
    logger.info("store_chunks | doc_id=%s  chunks=%d", doc_id, len(state.get("chunks", [])))

    chunks     = state.get("chunks", [])
    embeddings = state.get("embeddings", [])
    entities   = state.get("entities", [])
    metadata   = state.get("chunk_metadata", [])

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

    dsn = settings.sync_database_url.replace("+psycopg2", "", 1)

    chunk_ids = [str(uuid.uuid4()) for _ in chunks]
    chunk_index_to_id = {
        meta.get("chunk_index", idx): chunk_id
        for idx, (meta, chunk_id) in enumerate(zip(metadata, chunk_ids))
    }

    try:
        with psycopg.connect(dsn) as conn:
            register_vector(conn)

            with conn.transaction():
                conn.execute(
                    _UPSERT_DOCUMENT,
                    (doc_id, state["filename"], state["file_type"].value, state["content_hash"]),
                )

                chunk_rows = [
                    (
                        chunk_id,
                        doc_id,
                        meta.get("chunk_index", idx),
                        doc.page_content,
                        embedding,
                    )
                    for idx, (chunk_id, doc, embedding, meta) in enumerate(
                        zip(chunk_ids, chunks, embeddings, metadata)
                    )
                ]
                with conn.cursor() as cur:
                    cur.executemany(_INSERT_CHUNK, chunk_rows)

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
