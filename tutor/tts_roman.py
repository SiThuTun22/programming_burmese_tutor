"""Roman-numeral speech mappings for Myanmar TTS."""

from __future__ import annotations

import json
import re
from pathlib import Path

from tutor.tts_phrases import PAUSE_SENTINEL

KIND_ROMAN = "roman"
_AMBIGUOUS = {"I", "V", "X"}
_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_ROMAN_MAP_PATH = Path(__file__).resolve().parent / "tts_roman_map.json"
_roman_map: dict[str, str] | None = None
_UNIT_HINTS = {
    "english",
    "physics",
    "mathematics",
    "math",
    "programming",
    "electronics",
    "semester",
    "lab",
    "chemistry",
    "language",
    "year",
    "chapter",
    "volume",
    "part",
    "type",
    "level",
    "generation",
    "machine",
    "learning",
}


def load_roman_map() -> dict[str, str]:
    global _roman_map
    if _roman_map is not None:
        return _roman_map
    loaded: dict[str, str] = {}
    parsed = json.loads(_ROMAN_MAP_PATH.read_text(encoding="utf-8"))
    if isinstance(parsed, dict):
        for key, value in parsed.items():
            if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
                loaded[key.strip()] = value.strip()
    _roman_map = loaded
    return loaded


def roman_lookup_key(token: str) -> str:
    return token.upper()


def is_ambiguous_roman_token(token: str) -> bool:
    return roman_lookup_key(token) in _AMBIGUOUS and not token.isdigit()


def is_unambiguous_roman(token: str) -> bool:
    if len(token) < 2 or any(character.isdigit() for character in token):
        return False
    key = roman_lookup_key(token)
    return key in load_roman_map() and key not in _AMBIGUOUS


def context_roman_tokens(text: str) -> set[str]:
    stripped = text.replace(PAUSE_SENTINEL, " ")
    marked: set[str] = set()
    previous: str | None = None
    for match in _TOKEN_PATTERN.finditer(stripped):
        token = match.group(0)
        if is_ambiguous_roman_token(token) and previous and previous.casefold() in _UNIT_HINTS:
            marked.add(token)
        previous = token
    return marked


def apply_roman_cache(text: str, cache: dict[str, str]) -> str:
    roman_map = load_roman_map()
    keys = [
        key
        for key, kind in cache.items()
        if kind == KIND_ROMAN and roman_lookup_key(key) in roman_map
    ]
    keys.sort(key=len, reverse=True)
    spoken = text
    for key in keys:
        replacement = roman_map[roman_lookup_key(key)]
        spoken = re.compile(r"\b" + re.escape(key) + r"\b").sub(replacement, spoken)
    return spoken
