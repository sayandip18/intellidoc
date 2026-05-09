from app.graph.ingestion.nodes.load_document import load_document
from app.graph.ingestion.nodes.chunk_document import chunk_document
from app.graph.ingestion.nodes.embed_chunks import embed_chunks
from app.graph.ingestion.nodes.extract_entities import extract_entities
from app.graph.ingestion.nodes.store_chunks import store_chunks
from app.graph.ingestion.state import IngestionStatus


def should_stop(state) -> str:
    """
    Routes to END immediately if any node set status=FAILED,
    otherwise continues to the next sequential node.
    """
    if state.get("status") == IngestionStatus.FAILED:
        return "stop"
    return "continue"


__all__ = [
    "load_document",
    "chunk_document",
    "embed_chunks",
    "extract_entities",
    "store_chunks",
    "should_stop",
]
