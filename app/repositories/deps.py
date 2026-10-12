from __future__ import annotations

from collections.abc import AsyncIterator

from litestar.di import Provide
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.chat_message import ChatMessageRepo
from app.repositories.chat_session import ChatSessionRepo
from app.repositories.session_document import SessionDocumentRepo
from app.repositories.user import UserRepo


async def provide_user_repo(db_session: AsyncSession) -> AsyncIterator[UserRepo]:
    repo = UserRepo(session=db_session)
    yield repo


async def provide_chat_session_repo(db_session: AsyncSession) -> AsyncIterator[ChatSessionRepo]:
    repo = ChatSessionRepo(session=db_session)
    yield repo


async def provide_session_document_repo(db_session: AsyncSession) -> AsyncIterator[SessionDocumentRepo]:
    repo = SessionDocumentRepo(session=db_session)
    yield repo


async def provide_chat_message_repo(db_session: AsyncSession) -> AsyncIterator[ChatMessageRepo]:
    repo = ChatMessageRepo(session=db_session)
    yield repo


provide_user_repo_dep = Provide(provide_user_repo)
provide_chat_session_repo_dep = Provide(provide_chat_session_repo)
provide_session_document_repo_dep = Provide(provide_session_document_repo)
provide_chat_message_repo_dep = Provide(provide_chat_message_repo)
