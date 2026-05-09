from __future__ import annotations

import logging
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.graph.crag.state import CRAGState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a precise document assistant. Answer the user's question using ONLY the "
    "information provided in the context below. Do not use any prior knowledge or make "
    "assumptions beyond what is explicitly stated in the context. If the context does not "
    "contain sufficient information to answer the question, state that clearly."
)


def _format_context(state: CRAGState) -> str:
    lines: list[str] = []
    for i, doc in enumerate(state["chunks"], start=1):
        source = doc.metadata.get("source", "unknown")
        lines.append(f"[{i}] (source: {source})\n{doc.page_content}")
    return "\n\n".join(lines)


async def generator(state: CRAGState) -> dict:
    logger.info("generator | query=%r  chunks=%d", state["query"], len(state["chunks"]))

    context = _format_context(state)
    user_message = f"Context:\n{context}\n\nQuestion: {state['query']}"

    llm = ChatOpenAI(
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        api_key=SecretStr(os.environ["OPENAI_API_KEY"]),
        temperature=0,
        streaming=True,
    )

    response = await llm.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
    )

    answer = str(response.content)
    logger.info("generator | answer_length=%d", len(answer))

    return {"answer": answer}
