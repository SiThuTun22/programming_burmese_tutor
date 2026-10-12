"""LangChain invoke_llm helpers for AAA backend (programming path)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI

from app.ai.llm import invoke_llm


def _make_programming_runnable(chat_model: ChatGoogleGenerativeAI) -> Runnable:
    async def _run(payload: dict[str, str]) -> str:
        content = payload.get("content", "")
        response = await chat_model.ainvoke([HumanMessage(content=content)])
        text = getattr(response, "content", response)
        return str(text)

    return RunnableLambda(_run)


async def generate_from_tutor_messages(
    messages: list[dict],
    *,
    temperature: float,
    top_p: float,
) -> str:
    del top_p  # AAA ChatGoogleGenerativeAI path uses temperature only
    if not messages:
        return ""
    content = str(messages[0].get("content") or "")
    reply = await invoke_llm(
        _make_programming_runnable,
        {"content": content},
        temperature,
    )
    return str(reply)
