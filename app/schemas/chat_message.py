from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.db.enums import MessageRole, TutorAvatar
from app.schemas.chat_session import ChatSessionRead


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageRead(BaseModel):
    id: uuid.UUID
    chat_session_id: uuid.UUID
    role: MessageRole
    content: str
    tutor_avatar: TutorAvatar | None = None
    document_id: uuid.UUID | None = None
    document_filename: str | None = None


class ChatMessageExchangeRead(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    session: ChatSessionRead


class MessageSpeechStatusRead(BaseModel):
    ready: bool
    pending: bool
