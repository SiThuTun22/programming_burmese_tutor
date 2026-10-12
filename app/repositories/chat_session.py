from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from app.db.enums import MessageRole
from app.db.models import ChatMessage, ChatSession


@dataclass(frozen=True)
class ChatSessionListItem:
    session: ChatSession
    last_user_message_at: datetime | None


class ChatSessionRepo(SQLAlchemyAsyncRepository[ChatSession]):
    model_type = ChatSession

    async def get_owned_or_none(self, session_id: uuid.UUID, owner_id: uuid.UUID) -> ChatSession | None:
        chat_session = await self.get_one_or_none(id=session_id, owner_id=owner_id)
        return chat_session

    async def list_for_owner_recent(
        self,
        owner_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ChatSessionListItem]:
        last_user_subq = (
            select(
                ChatMessage.chat_session_id.label('chat_session_id'),
                func.max(ChatMessage.created_at).label('last_user_at'),
            )
            .where(ChatMessage.role == MessageRole.USER)
            .group_by(ChatMessage.chat_session_id)
            .subquery()
        )
        sort_key = func.coalesce(last_user_subq.c.last_user_at, ChatSession.created_at)
        statement = (
            select(ChatSession, last_user_subq.c.last_user_at)
            .outerjoin(
                last_user_subq,
                ChatSession.id == last_user_subq.c.chat_session_id,
            )
            .where(ChatSession.owner_id == owner_id)
            .order_by(sort_key.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        rows = result.all()
        items: list[ChatSessionListItem] = []
        for row in rows:
            chat_session = row[0]
            last_user_at = row[1]
            items.append(
                ChatSessionListItem(
                    session=chat_session,
                    last_user_message_at=last_user_at,
                )
            )
        return items
