from __future__ import annotations

import json
import re
from pathlib import Path

from app.ai.tts_phrases import PAUSE_SENTINEL

KIND_ROMAN = 'roman'
_AMBIGUOUS = {'I', 'V', 'X'}
_TOKEN_PATTERN = re.compile(r'[A-Za-z][A-Za-z0-9]*')
_ROMAN_MAP_PATH = Path(__file__).resolve().parent / 'tts_roman_map.json'
_roman_map: dict[str, str] | None = None

_UNIT_HINTS = {
    'english',
    'physics',
    'mathematics',
    'math',
    'programming',
    'electronics',
    'semester',
    'lab',
    'chemistry',
    'language',
    'year',
    'chapter',
    'volume',
    'part',
    'type',
    'level',
    'generation',
    'machine',
    'learning',
}


def load_roman_map() -> dict[str, str]:
    global _roman_map
    if _roman_map is not None:
        return _roman_map
    loaded: dict[str, str] = {}
    raw = _ROMAN_MAP_PATH.read_text(encoding='utf-8')
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        for key, value in parsed.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            map_key = key.strip()
            map_value = value.strip()
            if len(map_key) == 0 or len(map_value) == 0:
                continue
            loaded[map_key] = map_value
    _roman_map = loaded
    return loaded


def roman_lookup_key(token: str) -> str:
    return token.upper()


def is_ambiguous_roman_token(token: str) -> bool:
    key = roman_lookup_key(token)
    if key not in _AMBIGUOUS:
        return False
    if token.isdigit():
        return False
    return True


def is_unambiguous_roman(token: str) -> bool:
    if len(token) < 2:
        return False
    for character in token:
        if character.isdigit():
            return False
    roman_map = load_roman_map()
    key = roman_lookup_key(token)
    if key not in roman_map:
        return False
    if key in _AMBIGUOUS:
        return False
    return True


def tokens_with_previous(text: str) -> list[tuple[str, str | None]]:
    stripped = text.replace(PAUSE_SENTINEL, ' ')
    pairs: list[tuple[str, str | None]] = []
    previous: str | None = None
    matches = _TOKEN_PATTERN.finditer(stripped)
    for match in matches:
        token = match.group(0)
        pair = (token, previous)
        pairs.append(pair)
        previous = token
    return pairs


def has_unit_hint_previous(previous: str | None) -> bool:
    if previous is None:
        return False
    folded = previous.casefold()
    if folded in _UNIT_HINTS:
        return True
    return False


def context_roman_tokens(text: str) -> set[str]:
    marked: set[str] = set()
    pairs = tokens_with_previous(text)
    for token, previous in pairs:
        if not is_ambiguous_roman_token(token):
            continue
        if not has_unit_hint_previous(previous):
            continue
        marked.add(token)
    return marked


def apply_roman_cache(text: str, cache: dict[str, str]) -> str:
    roman_map = load_roman_map()
    keys: list[str] = []
    for key, kind in cache.items():
        if kind != KIND_ROMAN:
            continue
        lookup = roman_lookup_key(key)
        if lookup not in roman_map:
            continue
        keys.append(key)
    keys.sort(key=len, reverse=True)
    spoken = text
    for key in keys:
        lookup = roman_lookup_key(key)
        replacement = roman_map[lookup]
        pattern = re.compile(r'\b' + re.escape(key) + r'\b')
        spoken = pattern.sub(replacement, spoken)
    return spoken
