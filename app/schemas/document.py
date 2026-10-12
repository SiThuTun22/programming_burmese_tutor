from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.schemas.chat_message import ChatMessageRead
from app.schemas.chat_session import ChatSessionRead


class DocumentAnnotationRead(BaseModel):
    term: str
    definition: str
    page: int
    x: float
    y: float
    width: float
    height: float


class DocumentRead(BaseModel):
    id: uuid.UUID
    chat_session_id: uuid.UUID
    filename: str
    file_url: str
    content_type: str
    annotations: list[DocumentAnnotationRead]


class DocumentUploadRead(BaseModel):
    document: DocumentRead
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    session: ChatSessionRead
