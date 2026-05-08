from __future__ import annotations

from app.models.chunk import Chunk


def rrf_merge(
    dense: list[Chunk],
    sparse: list[tuple[Chunk, float]],
    k: int = 60,
    top_n: int = 10,
) -> list[Chunk]:
    """Reciprocal Rank Fusion over a dense and a sparse result list.

    Score for chunk c = Σ 1 / (k + rank)  across every list in which c appears.
    Rank is 0-based; chunks absent from a list contribute nothing.
    Chunks appearing in both lists receive two additive terms (double contribution).
    """
    scores: dict[str, float] = {}
    chunks_by_id: dict[str, Chunk] = {}

    for rank, chunk in enumerate(dense):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
        chunks_by_id[chunk.id] = chunk

    for rank, (chunk, _) in enumerate(sparse):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
        chunks_by_id[chunk.id] = chunk

    ranked = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    return [chunks_by_id[cid] for cid in ranked[:top_n]]
