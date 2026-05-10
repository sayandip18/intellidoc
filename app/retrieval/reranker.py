from __future__ import annotations

import cohere

from app.models.chunk import Chunk
from app.core.config import settings

_RERANK_MODEL = "rerank-english-v3.0"


async def rerank(
    query: str,
    chunks: list[Chunk],
    top_n: int = 5,
) -> list[Chunk]:
    if not chunks:
        return []

    async with cohere.AsyncClientV2(api_key=settings.cohere_api_key) as client:
        response = await client.rerank(
            model=_RERANK_MODEL,
            query=query,
            documents=[chunk.text for chunk in chunks],
            top_n=min(top_n, len(chunks)),
        )

    return [chunks[result.index] for result in response.results]
