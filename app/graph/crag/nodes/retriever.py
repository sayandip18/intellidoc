from __future__ import annotations

import asyncio
import logging

from langchain_core.documents import Document

from app.graph.crag.state import CRAGState
from app.retrieval.dense import dense_search
from app.retrieval.reranker import rerank
from app.retrieval.rrf import rrf_merge
from app.retrieval.sparse import sparse_search

logger = logging.getLogger(__name__)


def _to_document(chunk) -> Document:
    return Document(
        page_content=chunk.text,
        metadata={
            "source": chunk.document_id,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
        },
    )


async def retriever(state: CRAGState) -> dict:
    query = state["query"]
    logger.info("retriever | query=%r", query)

    dense, sparse = await asyncio.gather(
        dense_search(query),
        sparse_search(query),
    )
    merged = rrf_merge(dense, sparse)
    reranked = await rerank(query, merged)

    docs = [_to_document(chunk) for chunk in reranked]
    logger.info("retriever | returned %d docs", len(docs))

    return {"chunks": docs}
