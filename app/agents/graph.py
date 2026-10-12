from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    campus_node,
    courses_node,
    embed_node,
    faculty_node,
    pdf_node,
    router_node,
    tutor_node,
)
from app.agents.router import ROUTE_CAMPUS, ROUTE_COURSES, ROUTE_FACULTY, ROUTE_PDF
from app.agents.state import AgentState
from app.ai.errors import LlmUnavailableError

_graph = None


def build_tutor_graph():
    builder = StateGraph(AgentState)
    builder.add_node('router', router_node)
    builder.add_node('embed', embed_node)
    builder.add_node(ROUTE_FACULTY, faculty_node)
    builder.add_node(ROUTE_CAMPUS, campus_node)
    builder.add_node(ROUTE_COURSES, courses_node)
    builder.add_node(ROUTE_PDF, pdf_node)
    builder.add_node('tutor', tutor_node)
    builder.add_edge(START, 'router')
    builder.add_edge('router', 'embed')
    builder.add_edge('embed', ROUTE_FACULTY)
    builder.add_edge(ROUTE_FACULTY, ROUTE_CAMPUS)
    builder.add_edge(ROUTE_CAMPUS, ROUTE_COURSES)
    builder.add_edge(ROUTE_COURSES, ROUTE_PDF)
    builder.add_edge(ROUTE_PDF, 'tutor')
    builder.add_edge('tutor', END)
    compiled = builder.compile()
    return compiled


def get_tutor_graph():
    global _graph
    if _graph is None:
        compiled = build_tutor_graph()
        _graph = compiled
    return _graph


async def run_tutor_graph(
    user_content: str,
    history: str,
    document_context: str,
    system_prompt: str,
    delivery_style: str,
) -> str:
    graph = get_tutor_graph()
    initial: AgentState = {
        'user_content': user_content,
        'history': history,
        'document_context': document_context,
        'system_prompt': system_prompt,
        'delivery_style': delivery_style,
        'routes': [],
        'query_embedding': [],
        'retrieved': [],
        'reply': '',
    }
    result = await graph.ainvoke(initial)
    reply = result.get('reply')
    if not isinstance(reply, str) or len(reply.strip()) == 0:
        raise LlmUnavailableError('Gemini returned an empty tutor response.')
    trimmed = reply.strip()
    return trimmed
