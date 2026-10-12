from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.router import (
    ROUTE_CAMPUS,
    ROUTE_COURSES,
    ROUTE_FACULTY,
    ROUTE_PDF,
    classify_routes,
)
from app.agents.state import AgentState
from app.ai.errors import LlmUnavailableError
from app.ai.llm import invoke_llm
from app.ai.prompts import TUTOR_PROMPT, pick_delivery_style
from app.lib.config import get_gemini_tutor_temperature, get_rag_top_k
from app.knowledge.store import (
    CATEGORY_CAMPUS,
    CATEGORY_COURSES,
    CATEGORY_FACULTY,
    KnowledgeChunk,
    embed_query,
    retrieve,
)
from tutor.faculty_query import (
    expand_faculty_retrieval_query_with_history,
    looks_like_research_question,
)


def _format_chunks(title: str, chunks: list[KnowledgeChunk]) -> str:
    if len(chunks) == 0:
        return ''
    lines: list[str] = []
    lines.append(title)
    for chunk in chunks:
        source_text = ', '.join(chunk.sources)
        line = f'- ({chunk.id}) {chunk.text}'
        if len(source_text) > 0:
            line = f'{line} [sources: {source_text}]'
        lines.append(line)
    joined = '\n'.join(lines)
    return joined


def router_node(state: AgentState) -> dict[str, list[str]]:
    user_content = state['user_content']
    document_context = state['document_context']
    message_history = state['history']
    routes = classify_routes(user_content, document_context, message_history)
    return {'routes': routes}


async def embed_node(state: AgentState) -> dict[str, list[float]]:
    routes = state['routes']
    needs_knowledge = False
    if ROUTE_FACULTY in routes:
        needs_knowledge = True
    if ROUTE_CAMPUS in routes:
        needs_knowledge = True
    if ROUTE_COURSES in routes:
        needs_knowledge = True
    if not needs_knowledge:
        empty: list[float] = []
        return {'query_embedding': empty}
    user_content = expand_faculty_retrieval_query_with_history(
        state['user_content'],
        state['history'],
    )
    values = await embed_query(user_content)
    return {'query_embedding': values}


async def faculty_node(state: AgentState) -> dict[str, list[str]]:
    routes = state['routes']
    if ROUTE_FACULTY not in routes:
        return {'retrieved': []}
    user_content = expand_faculty_retrieval_query_with_history(
        state['user_content'],
        state['history'],
    )
    query_embedding = state['query_embedding']
    limit = None
    if looks_like_research_question(state['user_content']):
        limit = max(8, get_rag_top_k())
    chunks = await retrieve(CATEGORY_FACULTY, user_content, query_embedding, limit=limit)
    blob = _format_chunks('Faculty knowledge:', chunks)
    if len(blob) == 0:
        return {'retrieved': []}
    retrieved: list[str] = []
    retrieved.append(blob)
    return {'retrieved': retrieved}


async def campus_node(state: AgentState) -> dict[str, list[str]]:
    routes = state['routes']
    if ROUTE_CAMPUS not in routes:
        return {'retrieved': []}
    user_content = expand_faculty_retrieval_query_with_history(
        state['user_content'],
        state['history'],
    )
    query_embedding = state['query_embedding']
    chunks = await retrieve(CATEGORY_CAMPUS, user_content, query_embedding)
    blob = _format_chunks('Campus / MIIT knowledge:', chunks)
    if len(blob) == 0:
        return {'retrieved': []}
    retrieved: list[str] = []
    retrieved.append(blob)
    return {'retrieved': retrieved}


async def courses_node(state: AgentState) -> dict[str, list[str]]:
    routes = state['routes']
    if ROUTE_COURSES not in routes:
        return {'retrieved': []}
    user_content = expand_faculty_retrieval_query_with_history(
        state['user_content'],
        state['history'],
    )
    query_embedding = state['query_embedding']
    chunks = await retrieve(CATEGORY_COURSES, user_content, query_embedding)
    blob = _format_chunks('Course / handout knowledge:', chunks)
    if len(blob) == 0:
        return {'retrieved': []}
    retrieved: list[str] = []
    retrieved.append(blob)
    return {'retrieved': retrieved}


def pdf_node(state: AgentState) -> dict[str, list[str]]:
    routes = state['routes']
    if ROUTE_PDF not in routes:
        return {'retrieved': []}
    document_context = state['document_context']
    trimmed = document_context.strip()
    if trimmed == '(none)' or len(trimmed) == 0:
        return {'retrieved': []}
    blob = f'Session document:\n{trimmed}'
    retrieved: list[str] = []
    retrieved.append(blob)
    return {'retrieved': retrieved}


def _make_tutor_runnable(chat_model: ChatGoogleGenerativeAI) -> Runnable:
    output_parser = StrOutputParser()
    tutor_chain = TUTOR_PROMPT | chat_model | output_parser
    return tutor_chain


async def tutor_node(state: AgentState) -> dict[str, str]:
    retrieved_parts = state['retrieved']
    if len(retrieved_parts) == 0:
        knowledge_blob = '(none)'
    else:
        knowledge_blob = '\n\n'.join(retrieved_parts)

    routes = state['routes']
    for_faculty_profile = ROUTE_FACULTY in routes
    delivery_style = pick_delivery_style(for_faculty_profile)

    payload = {
        'system_prompt': state['system_prompt'],
        'retrieved_knowledge': knowledge_blob,
        'document_context': state['document_context'],
        'message_history': state['history'],
        'user_content': state['user_content'],
        'delivery_style': delivery_style,
    }
    tutor_temperature = get_gemini_tutor_temperature()
    reply = await invoke_llm(_make_tutor_runnable, payload, tutor_temperature)
    if not isinstance(reply, str):
        raise LlmUnavailableError('Gemini returned an unexpected tutor response.')
    trimmed = reply.strip()
    if len(trimmed) == 0:
        raise LlmUnavailableError('Gemini returned an empty tutor response.')
    return {'reply': trimmed}
