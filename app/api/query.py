from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.graph.crag.graph import crag_graph

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/query")
async def query_doc(q: str = Query(..., description="Question to answer")):
    if not q.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty")

    async def event_generator():
        initial_state = {"query": q, "attempt": 0}
        final_score: float = 0.0
        final_attempts: int = 0
        rewrite_count: int = 0

        try:
            async for event in crag_graph.astream_events(initial_state, version="v2"):
                kind: str = event["event"]
                name: str = event.get("name", "")
                data = event.get("data") or {}
                meta: dict = event.get("metadata", {})

                if kind == "on_chat_model_stream" and meta.get("langgraph_node") == "generator":
                    chunk = data.get("chunk")
                    if chunk and chunk.content:
                        yield {
                            "event": "token",
                            "data": json.dumps({"content": chunk.content}),
                        }

                elif kind == "on_chain_end":
                    output: dict = data.get("output") or {}

                    if name == "retriever":
                        n = len(output.get("chunks", []))
                        yield {
                            "event": "step",
                            "data": json.dumps({"node": "retriever", "detail": f"retrieved {n} chunks"}),
                        }

                    elif name == "faithfulness_scorer":
                        score = float(output.get("faithfulness_score", 0.0))
                        attempt = int(output.get("attempt", 0))
                        final_score = score
                        final_attempts = attempt
                        yield {
                            "event": "step",
                            "data": json.dumps({"node": "faithfulness_scorer", "score": score}),
                        }

                    elif name == "query_rewriter":
                        rewrite_count += 1
                        rewritten = output.get("query", "")
                        yield {
                            "event": "step",
                            "data": json.dumps({
                                "node": "query_rewriter",
                                "attempt": rewrite_count,
                                "rewritten_query": rewritten,
                            }),
                        }

            yield {
                "event": "done",
                "data": json.dumps({"final_score": final_score, "attempts": final_attempts}),
            }

        except Exception as exc:
            logger.exception("query pipeline failed: %s", exc)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }

    return EventSourceResponse(event_generator())
