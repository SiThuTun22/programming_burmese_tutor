from app.db.models import SessionDocument

DOCUMENT_CONTEXT_MAX_CHARS = 6000


def truncate_document_context(extracted_text: str) -> str:
    if len(extracted_text) <= DOCUMENT_CONTEXT_MAX_CHARS:
        return extracted_text
    trimmed = extracted_text[:DOCUMENT_CONTEXT_MAX_CHARS]
    return trimmed


def _document_body(extracted_text: str, vision_description: str) -> str:
    text_part = extracted_text.strip()
    vision_part = vision_description.strip()
    sections: list[str] = []
    if len(text_part) > 0:
        sections.append('=== Document text ===\n' + text_part)
    if len(vision_part) > 0:
        sections.append('=== Visual content (from vision model) ===\n' + vision_part)
    if len(sections) == 0:
        return ''
    combined = '\n\n'.join(sections)
    return combined


def build_document_context(extracted_text: str, vision_description: str) -> str:
    combined = _document_body(extracted_text, vision_description)
    truncated = truncate_document_context(combined)
    return truncated


def _file_section(document: SessionDocument) -> str:
    body = _document_body(document.extracted_text, document.vision_description)
    if len(body) == 0:
        return ''
    header = f'=== File: {document.filename} ===\n'
    section = header + body
    return section


def build_session_document_context(documents: list[SessionDocument]) -> str:
    included: list[str] = []
    used = 0
    for document in documents:
        section = _file_section(document)
        if len(section) == 0:
            continue
        separator_len = 0
        if len(included) > 0:
            separator_len = 2
        remaining = DOCUMENT_CONTEXT_MAX_CHARS - used - separator_len
        if remaining <= 0:
            break
        if len(section) > remaining:
            piece = section[:remaining]
            included.append(piece)
            break
        included.append(section)
        used = used + separator_len + len(section)
    if len(included) == 0:
        return ''
    combined = '\n\n'.join(included)
    return combined
