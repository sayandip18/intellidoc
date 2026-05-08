from app.graph.nodes.load_document import load_document
from app.graph.nodes.chunk_document import chunk_document
from app.graph.nodes.embed_chunks import embed_chunks
from app.graph.nodes.extract_entities import extract_entities
from app.graph.nodes.store_chunks import store_chunks
from app.graph.state import IngestionStatus


def should_stop(state) -> str:
    """
    Conditional edge guard used after every node.

    If any node sets status=FAILED, the graph jumps to END immediately
    instead of continuing the pipeline.  All other statuses let the
    normal linear edge take over.

    Returns:
        "stop"     → route to END
        "continue" → follow the default sequential edge
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