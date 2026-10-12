from __future__ import annotations

import re

from app.agents.graph import run_tutor_graph
from app.ai.prompts import system_prompt_for_tone
from app.ai.tts_phrases import fix_orphan_polite_sentences
from app.db.enums import MessageRole
from app.db.models import ChatMessage, ChatSession

_LEADING_PARTICLES = ('ခင်ဗျာ', 'ရှင်', 'ဗျာ')
_LEADING_TRAIL = '၊, \t\n\r'
_FINAL_PARTICLE_PATTERN = re.compile(r'(ခင်ဗျာ|ရှင်|ဗျာ)(\s*)(။|\?|!)')


def _format_history(history: list[ChatMessage]) -> str:
    if len(history) == 0:
        return '(none)'

    lines: list[str] = []
    for message in history:
        if message.role == MessageRole.USER:
            role_label = 'Student'
        else:
            role_label = 'Tutor'
        line = f'{role_label}: {message.content}'
        lines.append(line)

    joined = '\n'.join(lines)
    return joined


def _format_document_context(document_context: str | None) -> str:
    if document_context is None:
        return '(none)'
    trimmed = document_context.strip()
    if len(trimmed) == 0:
        return '(none)'
    return trimmed


def strip_leading_polite_particles(text: str) -> str:
    cleaned = text.lstrip()
    while True:
        matched = False
        for particle in _LEADING_PARTICLES:
            if not cleaned.startswith(particle):
                continue
            rest = cleaned[len(particle) :]
            rest = rest.lstrip(_LEADING_TRAIL)
            cleaned = rest
            matched = True
            break
        if not matched:
            break
    return cleaned


def thin_sentence_final_particles(text: str) -> str:
    matches = list(_FINAL_PARTICLE_PATTERN.finditer(text))
    if len(matches) <= 1:
        return text
    last_match = matches[-1]
    last_start = last_match.start()
    pieces: list[str] = []
    cursor = 0
    for match in matches:
        if match.start() == last_start:
            break
        prefix = text[cursor : match.start()]
        space_part = match.group(2)
        end_mark = match.group(3)
        pieces.append(prefix)
        already_polite = prefix.endswith('ပါ') or prefix.endswith('တယ်')
        if not already_polite:
            pieces.append('ပါ')
        pieces.append(space_part)
        pieces.append(end_mark)
        cursor = match.end()
    tail = text[cursor:]
    pieces.append(tail)
    joined = ''.join(pieces)
    return joined


async def generate_tutor_reply(
    chat_session: ChatSession,
    history: list[ChatMessage],
    user_content: str,
    document_context: str | None = None,
) -> str:
    system_prompt = system_prompt_for_tone(
        chat_session.tutor_tone,
        chat_session.tutor_avatar,
    )
    history_text = _format_history(history)
    document_text = _format_document_context(document_context)
    reply = await run_tutor_graph(
        user_content,
        history_text,
        document_text,
        system_prompt,
        '',
    )
    cleaned_reply = strip_leading_polite_particles(reply)
    cleaned_reply = thin_sentence_final_particles(cleaned_reply)
    cleaned_reply = fix_orphan_polite_sentences(cleaned_reply)
    return cleaned_reply
