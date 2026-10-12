from __future__ import annotations

import uuid

from litestar import Request, Response, Router, get, post
from litestar.exceptions import NotFoundException
from litestar.params import Parameter
from litestar.security.jwt import Token

from app.ai.errors import LlmUnavailableError
from app.ai.tts import (
    message_speech_pending,
    message_speech_ready,
    resolve_speech_avatar,
    speech_bytes_for_message,
)
from app.db.enums import MessageRole
from app.db.models import User
from app.repositories import (
    ChatMessageRepo,
    ChatSessionRepo,
    SessionDocumentRepo,
    provide_chat_message_repo_dep,
    provide_chat_session_repo_dep,
    provide_session_document_repo_dep,
)
from app.routes.mappers import raise_llm_unavailable, require_owned_session, to_message_read, to_session_read
from app.schemas import (
    ChatMessageCreate,
    ChatMessageExchangeRead,
    ChatMessageRead,
    MessageSpeechStatusRead,
)
from app.services.chat.messages import send_message_exchange


@get('/{session_id:uuid}/messages')
async def list_messages(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    chat_message_repo: ChatMessageRepo,
    session_document_repo: SessionDocumentRepo,
    session_id: uuid.UUID,
    limit: int = Parameter(default=50, ge=1, le=200),
    offset: int = Parameter(default=0, ge=0),
) -> list[ChatMessageRead]:
    user = request.user
    await require_owned_session(chat_session_repo, session_id, user.id)
    session_documents = await session_document_repo.list_for_session(session_id)
    filenames: dict[uuid.UUID, str] = {}
    for document in session_documents:
        filenames[document.id] = document.filename
    results = await chat_message_repo.list_for_session(session_id, limit, offset)
    messages: list[ChatMessageRead] = []
    for message in results:
        filename: str | None = None
        document_id = message.document_id
        if document_id is not None:
            filename = filenames.get(document_id)
        message_read = to_message_read(message, filename)
        messages.append(message_read)
    return messages


@post('/{session_id:uuid}/messages', status_code=201)
async def create_message(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    chat_message_repo: ChatMessageRepo,
    session_document_repo: SessionDocumentRepo,
    session_id: uuid.UUID,
    data: ChatMessageCreate,
) -> ChatMessageExchangeRead:
    user = request.user
    chat_session = await require_owned_session(chat_session_repo, session_id, user.id)

    try:
        exchange_result = await send_message_exchange(
            chat_session,
            session_id,
            data.content,
            chat_message_repo,
            session_document_repo,
            chat_session_repo,
        )
    except LlmUnavailableError as error:
        raise_llm_unavailable(error)

    user_read = to_message_read(exchange_result.user_message)
    assistant_read = to_message_read(exchange_result.assistant_message)
    session_read = to_session_read(
        exchange_result.chat_session,
        exchange_result.user_message.created_at,
    )
    exchange = ChatMessageExchangeRead(
        user_message=user_read,
        assistant_message=assistant_read,
        session=session_read,
    )
    return exchange


@get('/{session_id:uuid}/messages/{message_id:uuid}/speech/status')
async def get_message_speech_status(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    chat_message_repo: ChatMessageRepo,
    session_id: uuid.UUID,
    message_id: uuid.UUID,
) -> MessageSpeechStatusRead:
    user = request.user
    await require_owned_session(chat_session_repo, session_id, user.id)
    message = await chat_message_repo.get_one_or_none(
        id=message_id,
        chat_session_id=session_id,
    )
    if message is None:
        raise NotFoundException(detail=f'Message {message_id} not found')
    role_value = str(message.role)
    if role_value != MessageRole.ASSISTANT.value:
        return MessageSpeechStatusRead(ready=False, pending=False)
    ready = message_speech_ready(message_id)
    pending = message_speech_pending(message_id)
    return MessageSpeechStatusRead(ready=ready, pending=pending)


@get('/{session_id:uuid}/messages/{message_id:uuid}/speech')
async def get_message_speech(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    chat_message_repo: ChatMessageRepo,
    session_id: uuid.UUID,
    message_id: uuid.UUID,
) -> Response[bytes]:
    user = request.user
    chat_session = await require_owned_session(chat_session_repo, session_id, user.id)
    message = await chat_message_repo.get_one_or_none(id=message_id, chat_session_id=session_id)
    if message is None:
        raise NotFoundException(detail=f'Message {message_id} not found')
    role_value = str(message.role)
    if role_value != MessageRole.ASSISTANT.value:
        raise NotFoundException(detail=f'Message {message_id} not found')
    try:
        speech_avatar = resolve_speech_avatar(
            message.tutor_avatar,
            message.content,
            chat_session.tutor_avatar,
        )
        audio_bytes = await speech_bytes_for_message(
            message.id,
            message.content,
            speech_avatar,
        )
    except LlmUnavailableError as error:
        raise_llm_unavailable(error)
    response = Response(
        content=audio_bytes,
        media_type='audio/mpeg',
        headers={'Content-Disposition': 'inline; filename="speech.mp3"'},
    )
    return response


messages_router = Router(
    path='/api/chat-sessions',
    route_handlers=[
        list_messages,
        create_message,
        get_message_speech_status,
        get_message_speech,
    ],
    dependencies={
        'chat_session_repo': provide_chat_session_repo_dep,
        'chat_message_repo': provide_chat_message_repo_dep,
        'session_document_repo': provide_session_document_repo_dep,
    },
)
