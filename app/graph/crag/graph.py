from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.crag.nodes import faithfulness_scorer, generator, query_rewriter
from app.graph.crag.state import CRAGState

FAITHFULNESS_THRESHOLD = 0.7
MAX_RETRIES = 2


def _route_after_scoring(state: CRAGState) -> str:
    if state["attempt"] >= MAX_RETRIES or state["faithfulness_score"] >= FAITHFULNESS_THRESHOLD:
        return "end"
    return "rewrite"


def build_crag_graph() -> StateGraph:
    graph = StateGraph(CRAGState)

    graph.add_node("generator", generator)
    graph.add_node("faithfulness_scorer", faithfulness_scorer)
    graph.add_node("query_rewriter", query_rewriter)

    graph.add_edge(START, "generator")
    graph.add_edge("generator", "faithfulness_scorer")
    graph.add_edge("query_rewriter", "generator")

    graph.add_conditional_edges(
        "faithfulness_scorer",
        _route_after_scoring,
        {
            "end":     END,
            "rewrite": "query_rewriter",
        },
    )

    return graph


crag_graph = build_crag_graph().compile()
