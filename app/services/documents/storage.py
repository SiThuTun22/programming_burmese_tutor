from __future__ import annotations

import shutil
import uuid
from pathlib import Path


def _extension_for_filename(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith('.pdf'):
        return '.pdf'
    if lowered.endswith('.png'):
        return '.png'
    if lowered.endswith('.jpg') or lowered.endswith('.jpeg'):
        return '.jpg'
    if lowered.endswith('.webp'):
        return '.webp'
    return '.bin'


def save_uploaded_file(
    chat_session_id: uuid.UUID,
    document_id: uuid.UUID,
    filename: str,
    file_bytes: bytes,
) -> Path:
    session_dir = Path('uploads') / str(chat_session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    extension = _extension_for_filename(filename)
    storage_path = session_dir / f'{document_id}{extension}'
    storage_path.write_bytes(file_bytes)
    return storage_path


def save_uploaded_pdf(chat_session_id: uuid.UUID, document_id: uuid.UUID, file_bytes: bytes) -> Path:
    storage_path = save_uploaded_file(chat_session_id, document_id, 'document.pdf', file_bytes)
    return storage_path


def delete_session_uploads(chat_session_id: uuid.UUID) -> None:
    session_dir = Path('uploads') / str(chat_session_id)
    if not session_dir.exists():
        return
    shutil.rmtree(session_dir)
