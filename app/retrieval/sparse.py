from __future__ import annotations

import logging
import re

from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.core.db import async_session_factory
from app.models.chunk import Chunk

logger = logging.getLogger(__name__)

_TOP_K = 10


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


async def _load_corpus() -> list[Chunk]:
    async with async_session_factory() as session:
        result = await session.execute(select(Chunk))
        return list(result.scalars().all())


async def sparse_search(query: str, top_k: int = _TOP_K) -> list[tuple[Chunk, float]]:
    """Score all chunks with BM25 and return the top_k with their scores.

    NOTE: rebuilds the index on every call — acceptable for initial development
    but expensive at scale. See README for the planned optimization path.
    """
    chunks = await _load_corpus()
    if not chunks:
        return []

    corpus = [_tokenize(chunk.text) for chunk in chunks]
    bm25 = BM25Okapi(corpus)

    scores = bm25.get_scores(_tokenize(query))

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    logger.debug(
        "sparse_search | corpus=%d top_k=%d best_score=%.4f",
        len(chunks),
        top_k,
        float(scores[top_indices[0]]) if top_indices else 0.0,
    )

    return [(chunks[i], float(scores[i])) for i in top_indices]
