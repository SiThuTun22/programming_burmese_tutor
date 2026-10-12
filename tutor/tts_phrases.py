"""Split tutor answers into spoken phrases with sentence pauses."""

from __future__ import annotations

import re

from app.ai.tts_phrases import (
    _merge_orphan_polite_phrases,
    fix_orphan_polite_sentences,
)

PAUSE_SENTINEL = "\x1e"

_PAREN_PATTERN = re.compile(r"\([^()]*\)")
_MYANMAR_RE = re.compile(r"[\u1000-\u109F]")
_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_FENCE_PATTERN = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
_MD_MARK_PATTERN = re.compile(r"[#*_>]+")
_SEP_PATTERN = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$")


def _strip_parens(text: str) -> str:
    def drop(match: re.Match[str]) -> str:
        inner = match.group(1) if match.lastindex else match.group(0)[1:-1]
        if _MYANMAR_RE.search(inner):
            return match.group(0)
        return " "

    cleaned = text
    while True:
        stripped = _PAREN_PATTERN.sub(drop, cleaned)
        if stripped == cleaned:
            break
        cleaned = stripped
    return cleaned


def _unwrap_markdown(text: str) -> str:
    cleaned = _FENCE_PATTERN.sub(" ", text)
    cleaned = _INLINE_CODE_PATTERN.sub(r"\1", cleaned)
    cleaned = _LINK_PATTERN.sub(r"\1", cleaned)
    cleaned = _MD_MARK_PATTERN.sub(" ", cleaned)
    return _strip_parens(cleaned)


def _collapse_spaces(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if "-" not in stripped:
        return False
    return _SEP_PATTERN.match(stripped) is not None


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    return stripped.count("|") >= 2 and not _is_table_separator(stripped)


def _row_to_phrase(line: str) -> str:
    cells = [_collapse_spaces(part) for part in line.strip().split("|")]
    return "၊ ".join(cell for cell in cells if cell)


def _is_ascii_letter(character: str) -> bool:
    return "A" <= character <= "Z" or "a" <= character <= "z"


def _is_sentence_dot(text: str, index: int) -> bool:
    if index < 0 or index >= len(text) or text[index] != ".":
        return False
    prev_index = index - 1
    next_index = index + 1
    if prev_index >= 0 and text[prev_index].isdigit():
        if next_index < len(text) and text[next_index].isdigit():
            return False
    letter_run = 0
    scan = prev_index
    while scan >= 0 and _is_ascii_letter(text[scan]):
        letter_run += 1
        scan -= 1
    if 0 < letter_run < 4:
        return False
    if next_index >= len(text):
        return True
    return text[next_index].isspace()


def _split_sentences(text: str) -> list[str]:
    phrases: list[str] = []
    buffer: list[str] = []
    for index, character in enumerate(text):
        buffer.append(character)
        ended = character in "။?!" or _is_sentence_dot(text, index)
        if ended:
            phrase = _collapse_spaces("".join(buffer))
            if phrase:
                phrases.append(phrase)
            buffer = []
    if buffer:
        phrase = _collapse_spaces("".join(buffer))
        if phrase:
            phrases.append(phrase)
    return phrases


def phrases_from_markdown(text: str) -> list[str]:
    phrases: list[str] = []
    for line in _unwrap_markdown(fix_orphan_polite_sentences(text)).split("\n"):
        if _is_table_separator(line):
            continue
        if _is_table_row(line):
            phrase = _row_to_phrase(line)
            if phrase:
                phrases.append(phrase)
            continue
        phrases.extend(_split_sentences(line))
    return _merge_orphan_polite_phrases(phrases)


def strip_markdown_for_speech(text: str) -> str:
    return PAUSE_SENTINEL.join(phrases_from_markdown(text)).strip()
