from __future__ import annotations

import uuid
from datetime import datetime

from litestar.exceptions import NotFoundException, ServiceUnavailableException

from app.ai.errors import LlmUnavailableError
from app.db.models import ChatMessage, ChatSession, SessionDocument
from app.repositories.chat_session import ChatSessionRepo
from app.schemas import ChatMessageRead, ChatSessionRead, DocumentAnnotationRead, DocumentRead
from app.services.documents.annotations import annotations_from_json


async def require_owned_session(
    chat_session_repo: ChatSessionRepo,
    session_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> ChatSession:
    chat_session = await chat_session_repo.get_owned_or_none(session_id, owner_id)
    if chat_session is None:
        raise NotFoundException(detail=f'Chat session {session_id} not found')
    return chat_session


def to_message_read(
    message: ChatMessage,
    document_filename: str | None = None,
) -> ChatMessageRead:
    message_read = ChatMessageRead(
        id=message.id,
        chat_session_id=message.chat_session_id,
        role=message.role,
        content=message.content,
        tutor_avatar=message.tutor_avatar,
        document_id=message.document_id,
        document_filename=document_filename,
    )
    return message_read


def to_session_read(
    chat_session: ChatSession,
    last_user_message_at: datetime | None = None,
) -> ChatSessionRead:
    session_read = ChatSessionRead(
        id=chat_session.id,
        title=chat_session.title,
        tutor_tone=chat_session.tutor_tone,
        tutor_avatar=chat_session.tutor_avatar,
        status=chat_session.status,
        owner_id=chat_session.owner_id,
        created_at=chat_session.created_at,
        last_user_message_at=last_user_message_at,
    )
    return session_read


def to_document_read(document: SessionDocument) -> DocumentRead:
    raw_annotations = annotations_from_json(document.annotations_json)
    annotations: list[DocumentAnnotationRead] = []
    for item in raw_annotations:
        annotation_read = DocumentAnnotationRead(
            term=str(item['term']),
            definition=str(item['definition']),
            page=int(item['page']),
            x=float(item['x']),
            y=float(item['y']),
            width=float(item['width']),
            height=float(item['height']),
        )
        annotations.append(annotation_read)

    file_url = f'/api/chat-sessions/{document.chat_session_id}/documents/{document.id}/file'
    content_type = 'pdf'
    lowered = document.filename.lower()
    if lowered.endswith('.png') or lowered.endswith('.jpg') or lowered.endswith('.jpeg') or lowered.endswith('.webp'):
        content_type = 'image'

    document_read = DocumentRead(
        id=document.id,
        chat_session_id=document.chat_session_id,
        filename=document.filename,
        file_url=file_url,
        content_type=content_type,
        annotations=annotations,
    )
    return document_read


def raise_llm_unavailable(error: LlmUnavailableError) -> None:
    raise ServiceUnavailableException(detail=str(error)) from error
