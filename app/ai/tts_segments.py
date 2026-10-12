from __future__ import annotations

import unicodedata

KIND_MYANMAR = 'myanmar'
KIND_ENGLISH = 'english'


def _is_myanmar_letter(character: str) -> bool:
    code = ord(character)
    in_myanmar = False
    if 0x1000 <= code <= 0x109F:
        in_myanmar = True
    if 0xAA60 <= code <= 0xAA7F:
        in_myanmar = True
    if 0xA9E0 <= code <= 0xA9FF:
        in_myanmar = True
    if not in_myanmar:
        return False
    category = unicodedata.category(character)
    if category.startswith('L'):
        return True
    if category.startswith('M'):
        return True
    return False


def _char_kind(character: str) -> str | None:
    if _is_myanmar_letter(character):
        return KIND_MYANMAR
    if 'A' <= character <= 'Z':
        return KIND_ENGLISH
    if 'a' <= character <= 'z':
        return KIND_ENGLISH
    return None


def split_script_runs(text: str) -> list[tuple[str, str]]:
    runs: list[tuple[str, str]] = []
    current_kind = KIND_MYANMAR
    buffer = ''
    for character in text:
        kind = _char_kind(character)
        if kind is None:
            buffer = buffer + character
            continue
        if len(buffer) == 0:
            current_kind = kind
            buffer = character
            continue
        if kind == current_kind:
            buffer = buffer + character
            continue
        run = (current_kind, buffer)
        runs.append(run)
        current_kind = kind
        buffer = character
    if len(buffer) > 0:
        last = (current_kind, buffer)
        runs.append(last)
    return runs


def runs_have_english(runs: list[tuple[str, str]]) -> bool:
    for kind, _piece in runs:
        if kind == KIND_ENGLISH:
            return True
    return False


def runs_are_english_only(runs: list[tuple[str, str]]) -> bool:
    has_english = False
    for kind, piece in runs:
        for character in piece:
            if _is_myanmar_letter(character):
                return False
        if kind == KIND_ENGLISH:
            has_english = True
    return has_english
