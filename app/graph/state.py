# Graph states for both ingestion and CRAG flows
from __future__ import annotations
 
import operator
from enum import Enum
from typing import Annotated, Any, Optional
 
from langchain_core.documents import Document
from typing_extensions import TypedDict

class FileType(str, Enum):
    PDF  = "pdf"
    TXT  = "txt"
    DOCX = "docx"
 
 
class IngestionStatus(str, Enum):
    PENDING    = "pending"
    CHUNKING   = "chunking"
    EMBEDDING  = "embedding"
    EXTRACTING = "extracting_entities"
    STORING    = "storing"
    DONE       = "done"
    FAILED     = "failed"

class ChunkMetadata(TypedDict, total=False):
    document_id:  str
    chunk_index:  int
    page_number:  Optional[int]       # PDFs only
    source_path:  str
    file_type:    str
    char_start:   int
    char_end:     int

class ExtractedEntity(TypedDict):
    text:        str
    label:       str   # e.g. "PERSON", "ORG", "DATE"
    chunk_index: int

class IngestionState(TypedDict):
    """ 
    Lifecycle:
        raw bytes → chunks → embeddings → entities → stored in pgvector
    """
 
    # --- Input (set once at the start, never mutated) ---
    document_id:  str                  # UUID assigned at upload time
    source_path:  str                  # path on disk / object-store key
    file_type:    FileType
    raw_content:  Optional[bytes]      # populated by the loader node
 
    # --- Pipeline outputs (each node fills its slice) ---
    chunks:       list[Document]       # LangChain Documents (text + metadata)
    embeddings:   list[list[float]]    # parallel to chunks; dense vectors
 
    entities:     Annotated[          # accumulate across chunk batches
        list[ExtractedEntity],
        operator.add
    ]
 
    chunk_metadata: list[ChunkMetadata]   # parallel to chunks
 
    # --- Control / observability ---
    status:       IngestionStatus
    errors:       Annotated[list[str], operator.add]   # append-only error log
    node_trace:   Annotated[list[str], operator.add]   # ordered node names visited
 
 