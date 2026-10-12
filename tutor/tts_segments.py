"""Myanmar vs English script runs for TTS rate."""

from __future__ import annotations

import unicodedata

KIND_MYANMAR = "myanmar"
KIND_ENGLISH = "english"


def _is_myanmar_letter(character: str) -> bool:
    code = ord(character)
    in_myanmar = (
        0x1000 <= code <= 0x109F
        or 0xAA60 <= code <= 0xAA7F
        or 0xA9E0 <= code <= 0xA9FF
    )
    if not in_myanmar:
        return False
    category = unicodedata.category(character)
    return category.startswith("L") or category.startswith("M")


def _char_kind(character: str) -> str | None:
    if _is_myanmar_letter(character):
        return KIND_MYANMAR
    if "A" <= character <= "Z" or "a" <= character <= "z":
        return KIND_ENGLISH
    return None


def split_script_runs(text: str) -> list[tuple[str, str]]:
    runs: list[tuple[str, str]] = []
    current_kind = KIND_MYANMAR
    buffer = ""
    for character in text:
        kind = _char_kind(character)
        if kind is None:
            buffer += character
            continue
        if not buffer:
            current_kind = kind
            buffer = character
            continue
        if kind == current_kind:
            buffer += character
            continue
        runs.append((current_kind, buffer))
        current_kind = kind
        buffer = character
    if buffer:
        runs.append((current_kind, buffer))
    return runs


def runs_are_english_only(runs: list[tuple[str, str]]) -> bool:
    has_english = False
    for kind, piece in runs:
        if any(_is_myanmar_letter(character) for character in piece):
            return False
        if kind == KIND_ENGLISH:
            has_english = True
    return has_english
