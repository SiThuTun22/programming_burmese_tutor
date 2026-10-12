from __future__ import annotations

import uuid

from sqlalchemy import select
from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from app.db.models import SessionDocument


class SessionDocumentRepo(SQLAlchemyAsyncRepository[SessionDocument]):
    model_type = SessionDocument

    async def get_latest_for_session(self, chat_session_id: uuid.UUID) -> SessionDocument | None:
        statement = select(SessionDocument)
        statement = statement.where(SessionDocument.chat_session_id == chat_session_id)
        statement = statement.order_by(SessionDocument.created_at.desc())
        statement = statement.limit(1)
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()
        return document

    async def list_for_session(self, chat_session_id: uuid.UUID) -> list[SessionDocument]:
        statement = select(SessionDocument)
        statement = statement.where(SessionDocument.chat_session_id == chat_session_id)
        statement = statement.order_by(SessionDocument.created_at.desc())
        result = await self.session.execute(statement)
        scalars = result.scalars()
        rows = scalars.all()
        documents: list[SessionDocument] = []
        for document in rows:
            documents.append(document)
        return documents
