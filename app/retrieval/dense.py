from __future__ import annotations

import logging

from openai import AsyncOpenAI
from sqlalchemy import select

from app.core.db import async_session_factory
from app.models.chunk import Chunk
from config import settings

logger = logging.getLogger(__name__)

_TOP_K = 10


async def _embed_query(query: str) -> list[float]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(
        input=query,
        model=settings.openai_embedding_model,
    )
    return response.data[0].embedding


async def dense_search(query: str, top_k: int = _TOP_K) -> list[Chunk]:
    """Return top_k chunks most similar to query by cosine distance."""
    query_vec = await _embed_query(query)

    async with async_session_factory() as session:
        stmt = (
            select(Chunk)
            .where(Chunk.embedding.isnot(None))
            .order_by(Chunk.embedding.cosine_distance(query_vec))
            .limit(top_k)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
