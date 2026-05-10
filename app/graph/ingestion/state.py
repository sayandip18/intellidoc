from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Optional

from langchain_core.documents import Document
from typing_extensions import TypedDict


class FileType(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"


class IngestionStatus(str, Enum):
    PENDING = "pending"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    EXTRACTING = "extracting_entities"
    STORING = "storing"
    DONE = "done"
    FAILED = "failed"


class ChunkMetadata(TypedDict, total=False):
    document_id: str
    chunk_index: int
    page_number: Optional[int]
    source_path: str
    file_type: str
    char_start: int
    char_end: int


class ExtractedEntity(TypedDict):
    text: str
    label: str
    chunk_index: int


class IngestionState(TypedDict):
    """
    Lifecycle:
        raw bytes → chunks → embeddings → entities → stored in pgvector
    """

    document_id: str
    filename: str
    content_hash: str
    source_path: str
    file_type: FileType
    raw_content: Optional[bytes]

    chunks: list[Document]
    embeddings: list[list[float]]

    entities: Annotated[
        list[ExtractedEntity],
        operator.add
    ]

    chunk_metadata: list[ChunkMetadata]

    # observability
    status:       IngestionStatus
    errors:       Annotated[list[str], operator.add]
    node_trace:   Annotated[list[str], operator.add]
