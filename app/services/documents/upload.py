from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.ai.errors import LlmUnavailableError
from app.ai.gemini_vision import extract_vision_description
from app.ai.tts import schedule_message_speech
from app.ai.tutor import generate_tutor_reply
from app.db.models import ChatMessage, ChatSession, MessageRole, SessionDocument
from app.lib.config import get_vision_max_pdf_pages
from app.repositories.chat_message import ChatMessageRepo
from app.repositories.chat_session import ChatSessionRepo
from app.repositories.session_document import SessionDocumentRepo
from app.services.chat.session_title import maybe_autotitle_session
from app.services.documents.annotations import annotations_to_json, build_annotations
from app.services.documents.context import build_document_context
from app.services.documents.pdf_extract import extract_pdf_words, render_pdf_pages_as_png
from app.services.documents.storage import save_uploaded_file
from app.services.documents.terms import extract_document_terms

logger = logging.getLogger(__name__)


@dataclass
class DocumentUploadResult:
    document: SessionDocument
    user_message: ChatMessage
    assistant_message: ChatMessage
    chat_session: ChatSession


def is_pdf_filename(filename: str) -> bool:
    return filename.lower().endswith('.pdf')


def is_image_filename(filename: str) -> bool:
    lowered = filename.lower()
    if lowered.endswith('.png'):
        return True
    if lowered.endswith('.jpg') or lowered.endswith('.jpeg'):
        return True
    if lowered.endswith('.webp'):
        return True
    return False


def _title_source_for_upload(
    filename: str,
    extracted_text: str,
    vision_description: str,
) -> str:
    sections: list[str] = []
    sections.append(filename)
    vision_part = vision_description.strip()
    if len(vision_part) > 0:
        sections.append(vision_part[:500])
    text_part = extracted_text.strip()
    if len(text_part) > 0:
        sections.append(text_part[:500])
    joined = '\n'.join(sections)
    return joined


async def _vision_description_or_empty(image_bytes_list: list[bytes]) -> str:
    try:
        description = await extract_vision_description(image_bytes_list)
    except LlmUnavailableError as error:
        logger.warning('Vision description skipped; upload continues with extracted text only: %s', error)
        description = ''
    return description


def _user_content_for_upload(filename: str, user_question: str) -> str:
    stripped = user_question.strip()
    upload_note = f'(File: {filename})'
    if len(stripped) == 0:
        labeled = f'Uploaded "{filename}"'
        return labeled
    combined = stripped + '\n\n' + upload_note
    return combined


async def process_document_upload(
    chat_session: ChatSession,
    session_id: uuid.UUID,
    filename: str,
    file_bytes: bytes,
    session_document_repo: SessionDocumentRepo,
    chat_message_repo: ChatMessageRepo,
    chat_session_repo: ChatSessionRepo,
    user_question: str = '',
) -> DocumentUploadResult:
    document_id = uuid.uuid4()
    storage_path = save_uploaded_file(session_id, document_id, filename, file_bytes)

    extracted_text = ''
    vision_description = ''
    annotations_json = '[]'

    if is_pdf_filename(filename):
        extracted_text, words = extract_pdf_words(storage_path)
        terms = await extract_document_terms(extracted_text)
        annotations = build_annotations(terms, words)
        annotations_json = annotations_to_json(annotations)

        max_pages = get_vision_max_pdf_pages()
        page_images = render_pdf_pages_as_png(storage_path, max_pages)
        vision_description = await _vision_description_or_empty(page_images)
    elif is_image_filename(filename):
        image_list: list[bytes] = []
        image_list.append(file_bytes)
        vision_description = await extract_vision_description(image_list)
    else:
        raise ValueError(f'Unsupported file type: {filename}')

    document = SessionDocument(
        id=document_id,
        chat_session_id=session_id,
        filename=filename,
        storage_path=str(storage_path),
        extracted_text=extracted_text,
        vision_description=vision_description,
        annotations_json=annotations_json,
    )
    created_document = await session_document_repo.add(document)

    history = await chat_message_repo.get_recent_for_session(session_id)
    user_content = _user_content_for_upload(filename, user_question)
    user_message = ChatMessage(
        chat_session_id=session_id,
        role=MessageRole.USER,
        content=user_content,
        document_id=created_document.id,
    )
    created_user = await chat_message_repo.add(user_message)

    document_context = build_document_context(extracted_text, vision_description)
    if len(document_context) == 0:
        tutor_text = 'This file has no readable text.'
    else:
        question_stripped = user_question.strip()
        if len(question_stripped) > 0:
            tutor_prompt = question_stripped
        else:
            tutor_prompt = (
                f'Summarize only the document context for the file "{filename}". '
                'Explain the main topics in this upload.'
            )
        tutor_text = await generate_tutor_reply(
            chat_session,
            history,
            tutor_prompt,
            document_context,
        )

    assistant_message = ChatMessage(
        chat_session_id=session_id,
        role=MessageRole.ASSISTANT,
        content=tutor_text,
        tutor_avatar=chat_session.tutor_avatar,
    )
    created_assistant = await chat_message_repo.add(assistant_message)
    schedule_message_speech(
        created_assistant.id,
        created_assistant.content,
        created_assistant.tutor_avatar,
    )

    title_source = _title_source_for_upload(filename, extracted_text, vision_description)
    updated_session = await maybe_autotitle_session(
        chat_session,
        title_source,
        chat_session_repo,
    )

    result = DocumentUploadResult(
        document=created_document,
        user_message=created_user,
        assistant_message=created_assistant,
        chat_session=updated_session,
    )
    return result
