from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict):
    user_content: str
    history: str
    document_context: str
    system_prompt: str
    delivery_style: str
    routes: list[str]
    query_embedding: list[float]
    retrieved: Annotated[list[str], operator.add]
    reply: str
