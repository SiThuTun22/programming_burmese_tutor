from __future__ import annotations

import uuid

from litestar import Request, Router, delete, get, patch, post
from litestar.exceptions import NotFoundException
from litestar.params import Parameter
from litestar.security.jwt import Token

from app.db.models import ChatSession, User
from app.repositories import ChatSessionRepo, provide_chat_session_repo_dep
from app.routes.mappers import to_session_read
from app.schemas import ChatSessionCreate, ChatSessionRead, ChatSessionUpdate
from app.services.documents.storage import delete_session_uploads


@get('/')
async def list_chat_sessions(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    limit: int = Parameter(default=20, ge=1, le=100),
    offset: int = Parameter(default=0, ge=0),
) -> list[ChatSessionRead]:
    user = request.user
    items = await chat_session_repo.list_for_owner_recent(
        owner_id=user.id,
        limit=limit,
        offset=offset,
    )
    sessions: list[ChatSessionRead] = []
    for item in items:
        session_read = to_session_read(item.session, item.last_user_message_at)
        sessions.append(session_read)
    return sessions


@get('/{session_id:uuid}')
async def get_chat_session(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    session_id: uuid.UUID,
) -> ChatSessionRead:
    user = request.user
    chat_session = await chat_session_repo.get_one_or_none(id=session_id, owner_id=user.id)
    if chat_session is None:
        raise NotFoundException(detail=f'Chat session {session_id} not found')
    session_read = to_session_read(chat_session)
    return session_read


@post('/', status_code=201)
async def create_chat_session(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    data: ChatSessionCreate,
) -> ChatSessionRead:
    user = request.user
    chat_session = ChatSession(
        title=data.title,
        tutor_tone=data.tutor_tone,
        tutor_avatar=data.tutor_avatar,
        status=data.status,
        owner_id=user.id,
    )
    created = await chat_session_repo.add(chat_session)
    session_read = to_session_read(created)
    return session_read


@patch('/{session_id:uuid}')
async def update_chat_session(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    session_id: uuid.UUID,
    data: ChatSessionUpdate,
) -> ChatSessionRead:
    user = request.user
    chat_session = await chat_session_repo.get_one_or_none(id=session_id, owner_id=user.id)
    if chat_session is None:
        raise NotFoundException(detail=f'Chat session {session_id} not found')

    if data.tutor_tone is not None:
        chat_session.tutor_tone = data.tutor_tone
    if data.tutor_avatar is not None:
        chat_session.tutor_avatar = data.tutor_avatar

    updated = await chat_session_repo.update(chat_session)
    session_read = to_session_read(updated)
    return session_read


@delete('/{session_id:uuid}', status_code=204)
async def delete_chat_session(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    session_id: uuid.UUID,
) -> None:
    user = request.user
    chat_session = await chat_session_repo.get_one_or_none(id=session_id, owner_id=user.id)
    if chat_session is None:
        raise NotFoundException(detail=f'Chat session {session_id} not found')
    delete_session_uploads(session_id)
    await chat_session_repo.delete(session_id)


chat_sessions_router = Router(
    path='/api/chat-sessions',
    route_handlers=[
        list_chat_sessions,
        get_chat_session,
        create_chat_session,
        update_chat_session,
        delete_chat_session,
    ],
    dependencies={'chat_session_repo': provide_chat_session_repo_dep},
)
