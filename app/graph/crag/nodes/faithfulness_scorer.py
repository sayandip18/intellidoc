from __future__ import annotations

import json
import logging
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.graph.crag.state import CRAGState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a faithfulness evaluator for a retrieval-augmented generation system.\n\n"
    "Given a context (one or more document excerpts) and an answer, determine whether "
    "every claim in the answer is directly supported by the context. Do not reward answers "
    "that contain correct information drawn from outside knowledge — only context-grounded "
    "claims count.\n\n"
    "Respond with a JSON object containing exactly one key:\n"
    '  "score": a float between 0.0 and 1.0\n\n'
    "  1.0 — every claim is explicitly supported by the context\n"
    "  0.0 — the answer contradicts the context or is entirely unsupported\n"
    "  Values in between reflect partial support."
)


def _format_context(state: CRAGState) -> str:
    lines: list[str] = []
    for i, doc in enumerate(state["chunks"], start=1):
        source = doc.metadata.get("source", "unknown")
        lines.append(f"[{i}] (source: {source})\n{doc.page_content}")
    return "\n\n".join(lines)


async def faithfulness_scorer(state: CRAGState) -> dict:
    attempt = state["attempt"]
    logger.info(
        "faithfulness_scorer | attempt=%d  chunks=%d",
        attempt,
        len(state["chunks"]),
    )

    context = _format_context(state)
    user_message = f"Context:\n{context}\n\nAnswer:\n{state['answer']}"

    llm = ChatOpenAI(
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        api_key=SecretStr(os.environ["OPENAI_API_KEY"]),
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    response = await llm.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
    )

    raw = str(response.content)
    try:
        data = json.loads(raw)
        score = float(data["score"])
        score = max(0.0, min(1.0, score))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "faithfulness_scorer | could not parse score (%s) — raw=%r — defaulting to 0.0",
            exc,
            raw,
        )
        score = 0.0

    logger.info("faithfulness_scorer | score=%.3f  next_attempt=%d", score, attempt + 1)

    return {
        "faithfulness_score": score,
        "attempt": attempt + 1,
    }
