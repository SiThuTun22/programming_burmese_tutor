from __future__ import annotations

import re

PAUSE_SENTINEL = '\x1e'

_PAREN_PATTERN = re.compile(r'\([^()]*\)')
_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_FENCE_PATTERN = re.compile(r'```[\s\S]*?```')
_INLINE_CODE_PATTERN = re.compile(r'`([^`]+)`')
_MD_MARK_PATTERN = re.compile(r'[#*_>]+')
_SEP_PATTERN = re.compile(r'^\s*\|?[\s:\-|]+\|?\s*$')
_ORPHAN_POLITE_SENTENCE = re.compile(
    r'([။?!])\s+(ခင်ဗျာ|ရှင်|ဗျာ)\s*([။?!])',
)
_POLITE_ONLY_PHRASE = re.compile(r'^(ခင်ဗျာ|ရှင်|ဗျာ)\s*[။?!]+$')


def _strip_parens(text: str) -> str:
    cleaned = text
    while True:
        stripped_parens = _PAREN_PATTERN.sub(' ', cleaned)
        if stripped_parens == cleaned:
            break
        cleaned = stripped_parens
    return cleaned


def _unwrap_markdown(text: str) -> str:
    cleaned = text
    cleaned = _FENCE_PATTERN.sub(' ', cleaned)
    cleaned = _INLINE_CODE_PATTERN.sub(r'\1', cleaned)
    cleaned = _LINK_PATTERN.sub(r'\1', cleaned)
    cleaned = _MD_MARK_PATTERN.sub(' ', cleaned)
    cleaned = _strip_parens(cleaned)
    return cleaned


def _collapse_spaces(text: str) -> str:
    collapsed = re.sub(r'[ \t]+', ' ', text)
    trimmed = collapsed.strip()
    return trimmed


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) == 0:
        return False
    if '-' not in stripped:
        return False
    match = _SEP_PATTERN.match(stripped)
    if match is None:
        return False
    return True


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith('|'):
        return False
    pipe_count = stripped.count('|')
    if pipe_count < 2:
        return False
    if _is_table_separator(stripped):
        return False
    return True


def _row_to_phrase(line: str) -> str:
    stripped = line.strip()
    parts = stripped.split('|')
    cells: list[str] = []
    for part in parts:
        cell = _collapse_spaces(part)
        if len(cell) == 0:
            continue
        cells.append(cell)
    joined = '၊ '.join(cells)
    return joined


def _is_ascii_letter(character: str) -> bool:
    if 'A' <= character <= 'Z':
        return True
    if 'a' <= character <= 'z':
        return True
    return False


def _is_sentence_dot(text: str, index: int) -> bool:
    if index < 0:
        return False
    if index >= len(text):
        return False
    character = text[index]
    if character != '.':
        return False
    prev_index = index - 1
    next_index = index + 1
    if prev_index >= 0:
        prev_char = text[prev_index]
        if prev_char.isdigit():
            if next_index < len(text):
                next_char = text[next_index]
                if next_char.isdigit():
                    return False
    letter_run = 0
    scan = prev_index
    while scan >= 0:
        scan_char = text[scan]
        if not _is_ascii_letter(scan_char):
            break
        letter_run = letter_run + 1
        scan = scan - 1
    if letter_run > 0 and letter_run < 4:
        return False
    if next_index >= len(text):
        return True
    next_char = text[next_index]
    if next_char.isspace():
        return True
    return False


def fix_orphan_polite_sentences(text: str) -> str:
    """Join «…။ particle။» so the polite word stays on the same sentence for TTS."""
    cleaned = text
    while True:
        updated = _ORPHAN_POLITE_SENTENCE.sub(r' \2\3', cleaned)
        if updated == cleaned:
            return cleaned
        cleaned = updated


def _merge_orphan_polite_phrases(phrases: list[str]) -> list[str]:
    merged: list[str] = []
    for phrase in phrases:
        stripped = phrase.strip()
        if _POLITE_ONLY_PHRASE.match(stripped) and len(merged) > 0:
            particle_match = re.match(r'^(ခင်ဗျာ|ရှင်|ဗျာ)', stripped)
            if particle_match is None:
                merged.append(phrase)
                continue
            particle = particle_match.group(1)
            end_match = re.search(r'([။?!]+)\s*$', stripped)
            end_mark = end_match.group(1) if end_match is not None else '။'
            prev = merged[-1].rstrip()
            prev = re.sub(r'[။?!]+\s*$', '', prev)
            merged[-1] = f'{prev} {particle}{end_mark}'
            continue
        merged.append(phrase)
    return merged


def _split_sentences(text: str) -> list[str]:
    phrases: list[str] = []
    buffer_chars: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        buffer_chars.append(character)
        is_end = False
        if character == '။':
            is_end = True
        elif character == '?':
            is_end = True
        elif character == '!':
            is_end = True
        elif _is_sentence_dot(text, index):
            is_end = True
        if is_end:
            joined = ''.join(buffer_chars)
            phrase = _collapse_spaces(joined)
            if len(phrase) > 0:
                phrases.append(phrase)
            buffer_chars = []
        index = index + 1
    if len(buffer_chars) > 0:
        joined = ''.join(buffer_chars)
        phrase = _collapse_spaces(joined)
        if len(phrase) > 0:
            phrases.append(phrase)
    return phrases


def phrases_from_markdown(text: str) -> list[str]:
    unwrapped = _unwrap_markdown(fix_orphan_polite_sentences(text))
    lines = unwrapped.split('\n')
    phrases: list[str] = []
    for line in lines:
        if _is_table_separator(line):
            continue
        if _is_table_row(line):
            phrase = _row_to_phrase(line)
            if len(phrase) > 0:
                phrases.append(phrase)
            continue
        sentence_phrases = _split_sentences(line)
        for phrase in sentence_phrases:
            phrases.append(phrase)
    return _merge_orphan_polite_phrases(phrases)


def strip_markdown_for_speech(text: str) -> str:
    phrases = phrases_from_markdown(text)
    spoken = PAUSE_SENTINEL.join(phrases)
    trimmed = spoken.strip()
    return trimmed
