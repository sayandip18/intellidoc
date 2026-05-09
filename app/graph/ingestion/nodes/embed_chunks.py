"""
Generates dense vector embeddings for every chunk using OpenAI's
text-embedding-3-small model.

Batches requests to stay within the API's token-per-request limits.
Uses tenacity for exponential-backoff retries on transient API errors.

The output list of embeddings is parallel to state['chunks']:
  embeddings[i]  ←→  chunks[i]
"""

from __future__ import annotations

import logging
import os

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.graph.ingestion.state import IngestionState, IngestionStatus

logger = logging.getLogger(__name__)

# text-embedding-3-small accepts up to 2048 inputs per call;
# we stay conservative for token-limit headroom.
_BATCH_SIZE = 128


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(Exception),
)
def _embed_batch(client: OpenAIEmbeddings, texts: list[str]) -> list[list[float]]:
    return client.embed_documents(texts)


def embed_chunks(state: IngestionState) -> dict:
    logger.info("embed_chunks | doc_id=%s", state["document_id"])

    chunks = state.get("chunks", [])
    if not chunks:
        msg = "embed_chunks received no chunks — cannot embed."
        logger.error(msg)
        return {
            "status": IngestionStatus.FAILED,
            "errors": [msg],
            "node_trace": ["embed_chunks"],
        }

    client = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=SecretStr(os.environ["OPENAI_API_KEY"]),
    )

    texts = [doc.page_content for doc in chunks]
    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[batch_start : batch_start + _BATCH_SIZE]
        logger.debug(
            "embed_chunks | doc_id=%s  batch %d-%d",
            state["document_id"], batch_start, batch_start + len(batch) - 1,
        )
        try:
            vectors = _embed_batch(client, batch)
        except Exception as exc:
            msg = f"Embedding API failed after retries on batch starting at {batch_start}: {exc}"
            logger.exception(msg)
            return {
                "status": IngestionStatus.FAILED,
                "errors": [msg],
                "node_trace": ["embed_chunks"],
            }
        all_embeddings.extend(vectors)

    if len(all_embeddings) != len(chunks):
        msg = (
            f"Embedding count mismatch: got {len(all_embeddings)} "
            f"vectors for {len(chunks)} chunks."
        )
        logger.error(msg)
        return {
            "status": IngestionStatus.FAILED,
            "errors": [msg],
            "node_trace": ["embed_chunks"],
        }

    logger.info(
        "embed_chunks | doc_id=%s  vectors=%d  dims=%d",
        state["document_id"],
        len(all_embeddings),
        len(all_embeddings[0]) if all_embeddings else 0,
    )

    return {
        "embeddings": all_embeddings,
        "status":     IngestionStatus.EXTRACTING,
        "node_trace": ["embed_chunks"],
    }
