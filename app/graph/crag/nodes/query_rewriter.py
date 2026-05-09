from __future__ import annotations

import logging
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.graph.crag.state import CRAGState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a search query optimizer for a document retrieval system. "
    "The user's original question produced an answer that was not well-supported "
    "by the retrieved documents. Reformulate the question into a more effective "
    "search query that will surface better-matching document chunks.\n\n"
    "Strategies to apply (choose the most appropriate for the situation):\n"
    "  • Break a compound question into its most specific sub-question\n"
    "  • Replace ambiguous pronouns or references with explicit entity names\n"
    "  • Add domain-specific terminology likely to appear in source documents\n"
    "  • Rephrase as a declarative statement rather than a question\n\n"
    "Output ONLY the rewritten query — no explanation, no prefix, no surrounding quotes."
)


async def query_rewriter(state: CRAGState) -> dict:
    logger.info("query_rewriter | original=%r", state["query"])

    user_message = (
        f"Original question: {state['query']}\n\n"
        f"The previous answer was:\n{state['answer']}\n\n"
        "Rewrite the question to retrieve more relevant document chunks."
    )

    llm = ChatOpenAI(
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        api_key=SecretStr(os.environ["OPENAI_API_KEY"]),
        temperature=0.3,
    )

    response = await llm.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
    )

    rewritten = str(response.content).strip()
    logger.info("query_rewriter | rewritten=%r", rewritten)

    return {"query": rewritten}
