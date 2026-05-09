from __future__ import annotations

from typing import Optional

from langchain_core.documents import Document
from typing_extensions import TypedDict


class CRAGState(TypedDict):
    query: str
    chunks: list[Document]
    answer: Optional[str]
    faithfulness_score: float
    attempt: int
