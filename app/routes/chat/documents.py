from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from litestar import Request, Router, get, post
from litestar.datastructures import UploadFile
from litestar.exceptions import NotFoundException, ServiceUnavailableException
from litestar.params import MultipartBody
from litestar.response import File
from litestar.security.jwt import Token

from app.ai.errors import LlmUnavailableError
from app.db.models import User
from app.repositories import (
    ChatMessageRepo,
    ChatSessionRepo,
    SessionDocumentRepo,
    provide_chat_message_repo_dep,
    provide_chat_session_repo_dep,
    provide_session_document_repo_dep,
)
from app.routes.mappers import raise_llm_unavailable, require_owned_session, to_document_read, to_message_read, to_session_read
from app.schemas import DocumentRead, DocumentUploadRead
from app.services.documents.upload import is_image_filename, is_pdf_filename, process_document_upload


@dataclass
class DocumentUploadForm:
    file: UploadFile
    question: str = ''


@get('/{session_id:uuid}/documents')
async def list_documents(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    session_document_repo: SessionDocumentRepo,
    session_id: uuid.UUID,
) -> list[DocumentRead]:
    user = request.user
    await require_owned_session(chat_session_repo, session_id, user.id)
    documents = await session_document_repo.list_for_session(session_id)
    reads: list[DocumentRead] = []
    for document in documents:
        document_read = to_document_read(document)
        reads.append(document_read)
    return reads


@get('/{session_id:uuid}/documents/{document_id:uuid}')
async def get_document(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    session_document_repo: SessionDocumentRepo,
    session_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentRead:
    user = request.user
    await require_owned_session(chat_session_repo, session_id, user.id)
    document = await session_document_repo.get_one_or_none(
        id=document_id,
        chat_session_id=session_id,
    )
    if document is None:
        raise NotFoundException(detail=f'Document {document_id} not found')
    document_read = to_document_read(document)
    return document_read


@get('/{session_id:uuid}/documents/latest')
async def get_latest_document(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    session_document_repo: SessionDocumentRepo,
    session_id: uuid.UUID,
) -> DocumentRead | None:
    user = request.user
    await require_owned_session(chat_session_repo, session_id, user.id)

    latest_document = await session_document_repo.get_latest_for_session(session_id)
    if latest_document is None:
        return None

    document_read = to_document_read(latest_document)
    return document_read


@get('/{session_id:uuid}/documents/{document_id:uuid}/file')
async def get_document_file(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    session_document_repo: SessionDocumentRepo,
    session_id: uuid.UUID,
    document_id: uuid.UUID,
) -> File:
    user = request.user
    await require_owned_session(chat_session_repo, session_id, user.id)

    document = await session_document_repo.get_one_or_none(id=document_id, chat_session_id=session_id)
    if document is None:
        raise NotFoundException(detail=f'Document {document_id} not found')

    storage_path = Path(document.storage_path)
    if not storage_path.is_file():
        raise NotFoundException(detail=f'Document file for {document_id} not found')

    file_response = File(path=storage_path, filename=document.filename)
    return file_response


@post('/{session_id:uuid}/documents', status_code=201)
async def upload_document(
    request: Request[User, Token, None],
    chat_session_repo: ChatSessionRepo,
    session_document_repo: SessionDocumentRepo,
    chat_message_repo: ChatMessageRepo,
    session_id: uuid.UUID,
    data: MultipartBody[DocumentUploadForm],
) -> DocumentUploadRead:
    user = request.user
    chat_session = await require_owned_session(chat_session_repo, session_id, user.id)

    file = data.file
    filename = file.filename or 'document.pdf'
    if not is_pdf_filename(filename) and not is_image_filename(filename):
        raise ServiceUnavailableException(
            detail='Only PDF and image files (png, jpg, jpeg, webp) are supported.',
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise ServiceUnavailableException(detail='Uploaded file is empty.')

    try:
        question_raw = data.question
        if question_raw is None:
            question_text = ''
        else:
            question_text = question_raw.strip()
        upload_result = await process_document_upload(
            chat_session,
            session_id,
            filename,
            file_bytes,
            session_document_repo,
            chat_message_repo,
            chat_session_repo,
            question_text,
        )
    except LlmUnavailableError as error:
        raise_llm_unavailable(error)
    except ValueError as error:
        raise ServiceUnavailableException(detail=str(error)) from error

    document_read = to_document_read(upload_result.document)
    user_read = to_message_read(
        upload_result.user_message,
        upload_result.document.filename,
    )
    assistant_read = to_message_read(upload_result.assistant_message)
    session_read = to_session_read(upload_result.chat_session)
    upload_read = DocumentUploadRead(
        document=document_read,
        user_message=user_read,
        assistant_message=assistant_read,
        session=session_read,
    )
    return upload_read


documents_router = Router(
    path='/api/chat-sessions',
    route_handlers=[
        list_documents,
        get_latest_document,
        get_document,
        get_document_file,
        upload_document,
    ],
    dependencies={
        'chat_session_repo': provide_chat_session_repo_dep,
        'session_document_repo': provide_session_document_repo_dep,
        'chat_message_repo': provide_chat_message_repo_dep,
    },
)
