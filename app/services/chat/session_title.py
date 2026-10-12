from __future__ import annotations

from app.ai.session_title import DEFAULT_SESSION_TITLE, generate_session_title
from app.db.models import ChatSession
from app.repositories.chat_session import ChatSessionRepo


async def maybe_autotitle_session(
    chat_session: ChatSession,
    source_text: str,
    chat_session_repo: ChatSessionRepo,
) -> ChatSession:
    current_title = chat_session.title.strip()
    if current_title != DEFAULT_SESSION_TITLE:
        return chat_session

    generated_title = await generate_session_title(source_text)
    chat_session.title = generated_title
    updated = await chat_session_repo.update(chat_session)
    return updated
