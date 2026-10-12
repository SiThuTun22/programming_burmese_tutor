from __future__ import annotations

import uuid

from sqlalchemy import select
from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from app.db.models import ChatMessage


class ChatMessageRepo(SQLAlchemyAsyncRepository[ChatMessage]):
    model_type = ChatMessage

    async def list_for_session(
        self,
        chat_session_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatMessage]:
        statement = select(ChatMessage)
        statement = statement.where(ChatMessage.chat_session_id == chat_session_id)
        statement = statement.order_by(ChatMessage.created_at.asc())
        statement = statement.offset(offset)
        statement = statement.limit(limit)
        result = await self.session.execute(statement)
        scalars = result.scalars()
        rows = scalars.all()
        messages: list[ChatMessage] = []
        for message in rows:
            messages.append(message)
        return messages

    async def get_recent_for_session(
        self,
        chat_session_id: uuid.UUID,
        limit: int = 50,
    ) -> list[ChatMessage]:
        statement = select(ChatMessage)
        statement = statement.where(ChatMessage.chat_session_id == chat_session_id)
        statement = statement.order_by(ChatMessage.created_at.desc())
        statement = statement.limit(limit)
        result = await self.session.execute(statement)
        scalars = result.scalars()
        rows = scalars.all()
        newest_first: list[ChatMessage] = []
        for message in rows:
            newest_first.append(message)
        chronological: list[ChatMessage] = []
        index = len(newest_first) - 1
        while index >= 0:
            chronological.append(newest_first[index])
            index = index - 1
        return chronological
