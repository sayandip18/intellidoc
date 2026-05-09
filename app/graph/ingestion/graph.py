from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.ingestion.nodes import (
    chunk_document,
    embed_chunks,
    extract_entities,
    load_document,
    should_stop,
    store_chunks,
)
from app.graph.ingestion.state import IngestionState


def build_ingestion_graph() -> StateGraph:
    graph = StateGraph(IngestionState)

    graph.add_node("load_document",    load_document)
    graph.add_node("chunk_document",   chunk_document)
    graph.add_node("embed_chunks",     embed_chunks)
    graph.add_node("extract_entities", extract_entities)
    graph.add_node("store_chunks",     store_chunks)

    graph.add_edge(START, "load_document")

    _steps = [
        ("load_document",    "chunk_document"),
        ("chunk_document",   "embed_chunks"),
        ("embed_chunks",     "extract_entities"),
        ("extract_entities", "store_chunks"),
    ]
    for current, next_node in _steps:
        graph.add_conditional_edges(
            current,
            should_stop,
            {
                "stop":     END,
                "continue": next_node,
            },
        )

    graph.add_conditional_edges(
        "store_chunks",
        should_stop,
        {"stop": END, "continue": END},
    )

    return graph


ingestion_graph = build_ingestion_graph().compile()
