"""
Splits raw document text into overlapping chunks using LangChain's
RecursiveCharacterTextSplitter.  Attaches ChunkMetadata to every
LangChain Document so downstream nodes and pgvector have full lineage.

Chunk sizes are tuned per file type:
  - PDF / DOCX : larger chunks (800 chars) — prose-heavy, context matters
  - TXT        : smaller chunks (512 chars) — often logs / structured data
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.graph.ingestion.state import ChunkMetadata, FileType, IngestionState, IngestionStatus

logger = logging.getLogger(__name__)

_SPLITTER_CONFIGS: dict[FileType, dict[str, Any]] = {
    FileType.PDF: {
        "chunk_size": 800,
        "chunk_overlap": 150,
        "separators": ["\n\n", "\n", ". ", " ", ""],
    },
    FileType.DOCX: {
        "chunk_size": 800,
        "chunk_overlap": 150,
        "separators": ["\n\n", "\n", ". ", " ", ""],
    },
    FileType.TXT: {
        "chunk_size": 512,
        "chunk_overlap": 80,
        "separators": ["\n\n", "\n", " ", ""],
    },
}


def chunk_document(state: IngestionState) -> dict:
    logger.info("chunk_document | doc_id=%s", state["document_id"])

    raw: bytes | None = state.get("raw_content")
    if not raw:
        msg = "chunk_document received empty raw_content — skipping."
        logger.error(msg)
        return {
            "status": IngestionStatus.FAILED,
            "errors": [msg],
            "node_trace": ["chunk_document"],
        }

    text = raw.decode("utf-8", errors="replace")
    file_type = state["file_type"]
    cfg = _SPLITTER_CONFIGS[file_type]

    splitter = RecursiveCharacterTextSplitter(**cfg)
    raw_chunks: list[str] = splitter.split_text(text)

    if not raw_chunks:
        msg = "chunk_document produced zero chunks — document may be empty."
        logger.warning(msg)
        return {
            "status": IngestionStatus.FAILED,
            "errors": [msg],
            "node_trace": ["chunk_document"],
        }

    doc_id = state["document_id"]
    source_path = state["source_path"]

    documents: list[Document] = []
    chunk_metadata: list[ChunkMetadata] = []

    cursor = 0
    for idx, chunk_text in enumerate(raw_chunks):
        char_start = text.find(chunk_text, cursor)
        char_end = char_start + len(chunk_text)
        cursor = max(cursor, char_start)

        meta: ChunkMetadata = {
            "document_id":  doc_id,
            "chunk_index":  idx,
            "source_path":  source_path,
            "file_type":    file_type.value,
            "char_start":   char_start,
            "char_end":     char_end,
        }
        chunk_metadata.append(meta)

        documents.append(
            Document(
                page_content=chunk_text,
                metadata=dict(meta),
            )
        )

    logger.info(
        "chunk_document | doc_id=%s  chunks=%d  avg_chars=%d",
        doc_id,
        len(documents),
        sum(len(d.page_content) for d in documents) // len(documents),
    )

    return {
        "chunks":         documents,
        "chunk_metadata": chunk_metadata,
        "status":         IngestionStatus.EMBEDDING,
        "node_trace":     ["chunk_document"],
    }
