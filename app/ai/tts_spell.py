from __future__ import annotations

import enum
import json
import logging
import re
import threading
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.ai.errors import LlmUnavailableError
from app.ai.llm import invoke_llm
from app.ai.tts_phrases import PAUSE_SENTINEL
from app.ai.tts_roman import (
    KIND_ROMAN,
    apply_roman_cache,
    context_roman_tokens,
    is_ambiguous_roman_token,
    is_unambiguous_roman,
)
from app.lib.config import get_tts_spell_path

logger = logging.getLogger(__name__)

KIND_WORD = 'word'
KIND_SPELL = 'spell'
_TOKEN_PATTERN = re.compile(r'[A-Za-z][A-Za-z0-9]*')
_LETTER_MAP_PATH = Path(__file__).resolve().parent / 'tts_letter_map.json'
_lock = threading.Lock()
_letter_map: dict[str, str] | None = None
_ALLOWED_KINDS = {KIND_WORD, KIND_SPELL, KIND_ROMAN}

SPELL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            'system',
            'Classify Latin tokens for Myanmar TTS. '
            'kind word: speak as a normal word (Python, function, email, class). '
            'kind spell: speak letter by letter (ID, AD, opaque codes like vHVBD1MAAAAJ). '
            'kind roman: academic Roman numerals meaning numbers '
            '(English I, Physics III, Semester II, Mathematics V). '
            'I, V, or X is roman only when it is an ordinal number, not a Latin letter. '
            'Use spell for abbreviations and identifier-like strings. '
            'Do not invent tokens. Only classify the listed tokens.',
        ),
        (
            'human',
            'Tokens (JSON array):\n{tokens}\n\n'
            'Speech text:\n{spoken_text}',
        ),
    ]
)


class SpellKind(enum.StrEnum):
    WORD = KIND_WORD
    SPELL = KIND_SPELL
    ROMAN = KIND_ROMAN


class SpellEntry(BaseModel):
    token: str = Field(description='Latin token exactly as listed')
    kind: SpellKind = Field(description='word, spell, or roman')


class SpellMap(BaseModel):
    entries: list[SpellEntry] = Field(description='Classification for the listed tokens')


def _ensure_parent(path: Path) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)


def _read_raw_cache(path: Path) -> dict[str, str]:
    cache: dict[str, str] = {}
    if not path.is_file():
        return cache
    raw = path.read_text(encoding='utf-8')
    if len(raw.strip()) == 0:
        return cache
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        return cache
    for key, value in loaded.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        kind = value.strip()
        if kind not in _ALLOWED_KINDS:
            continue
        token = key.strip()
        if len(token) == 0:
            continue
        if is_unambiguous_roman(token):
            cache[token] = KIND_ROMAN
            continue
        if is_ambiguous_roman_token(token):
            continue
        cache[token] = kind
    return cache


def _write_cache(path: Path, cache: dict[str, str]) -> None:
    _ensure_parent(path)
    encoded = json.dumps(cache, ensure_ascii=False, indent=2)
    path.write_text(encoded, encoding='utf-8')


def load_spell_cache() -> dict[str, str]:
    path = get_tts_spell_path()
    with _lock:
        cache = _read_raw_cache(path)
        _write_cache(path, cache)
        return cache


def merge_spell_cache(entries: dict[str, str]) -> dict[str, str]:
    path = get_tts_spell_path()
    with _lock:
        cache = _read_raw_cache(path)
        for key, value in entries.items():
            token = key.strip()
            kind = value.strip()
            if len(token) == 0:
                continue
            if kind not in _ALLOWED_KINDS:
                continue
            if is_ambiguous_roman_token(token):
                continue
            if is_unambiguous_roman(token):
                cache[token] = KIND_ROMAN
                continue
            cache[token] = kind
        _write_cache(path, cache)
        return cache


def collect_latin_tokens(text: str) -> list[str]:
    stripped = text.replace(PAUSE_SENTINEL, ' ')
    found = _TOKEN_PATTERN.findall(stripped)
    unique: list[str] = []
    seen: set[str] = set()
    for token in found:
        if token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return unique


def fallback_kind(token: str) -> str:
    if is_unambiguous_roman(token):
        return KIND_ROMAN
    if is_ambiguous_roman_token(token):
        return KIND_WORD
    if len(token) == 2 and token.isupper():
        return KIND_SPELL
    has_letter = False
    has_digit = False
    has_upper = False
    has_lower = False
    for character in token:
        if character.isdigit():
            has_digit = True
            continue
        if 'A' <= character <= 'Z':
            has_letter = True
            has_upper = True
            continue
        if 'a' <= character <= 'z':
            has_letter = True
            has_lower = True
    if has_letter and has_digit:
        return KIND_SPELL
    if has_upper and has_lower and len(token) >= 8:
        return KIND_SPELL
    return KIND_WORD


def load_letter_map() -> dict[str, str]:
    global _letter_map
    if _letter_map is not None:
        return _letter_map
    loaded: dict[str, str] = {}
    raw = _LETTER_MAP_PATH.read_text(encoding='utf-8')
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
    _letter_map = loaded
    return loaded


def letters_for_speech(token: str) -> str:
    letter_map = load_letter_map()
    parts: list[str] = []
    for character in token:
        lookup = character
        if character.isalpha():
            lookup = character.upper()
        spoken_char = letter_map.get(lookup)
        if spoken_char is None:
            parts.append(character)
            continue
        parts.append(spoken_char)
    spaced = ' '.join(parts)
    return spaced


def apply_spell_cache(text: str, cache: dict[str, str]) -> str:
    keys: list[str] = []
    for key, kind in cache.items():
        if kind != KIND_SPELL:
            continue
        keys.append(key)
    keys.sort(key=len, reverse=True)
    spoken = text
    for key in keys:
        replacement = letters_for_speech(key)
        pattern = re.compile(r'\b' + re.escape(key) + r'\b')
        spoken = pattern.sub(replacement, spoken)
    return spoken


def apply_tts_token_cache(text: str, cache: dict[str, str]) -> str:
    spoken = apply_roman_cache(text, cache)
    spoken = apply_spell_cache(spoken, cache)
    return spoken


async def fetch_spell_kinds(tokens: list[str], spoken_text: str) -> dict[str, str]:
    empty: dict[str, str] = {}
    if len(tokens) == 0:
        return empty
    tokens_json = json.dumps(tokens, ensure_ascii=False)

    def make_runnable(chat_model: ChatGoogleGenerativeAI):
        structured_model = chat_model.with_structured_output(SpellMap)
        spell_chain = SPELL_PROMPT | structured_model
        return spell_chain

    payload: dict[str, str] = {}
    payload['tokens'] = tokens_json
    payload['spoken_text'] = spoken_text
    try:
        result = await invoke_llm(make_runnable, payload, 0.0)
    except LlmUnavailableError as error:
        logger.warning('TTS spell classification skipped: %s', error)
        return empty
    if isinstance(result, SpellMap):
        parsed = result
    elif isinstance(result, dict):
        parsed = SpellMap.model_validate(result)
    else:
        return empty
    allowed = set(tokens)
    classified: dict[str, str] = {}
    for item in parsed.entries:
        token = item.token.strip()
        if token not in allowed:
            continue
        kind_value = str(item.kind)
        if kind_value not in _ALLOWED_KINDS:
            continue
        classified[token] = kind_value
    return classified


async def resolve_spell_cache(spoken_text: str, lexicon_keys: list[str]) -> dict[str, str]:
    cache = load_spell_cache()
    overlay: dict[str, str] = {}
    for key, kind in cache.items():
        overlay[key] = kind
    tokens = collect_latin_tokens(spoken_text)
    for token in tokens:
        if is_unambiguous_roman(token):
            overlay[token] = KIND_ROMAN
    context_romans = context_roman_tokens(spoken_text)
    for token in context_romans:
        overlay[token] = KIND_ROMAN
    skipped = set(lexicon_keys)
    pending: list[str] = []
    pending_seen: set[str] = set()
    for token in tokens:
        if token in skipped:
            continue
        if is_unambiguous_roman(token):
            continue
        if token in context_romans:
            continue
        if is_ambiguous_roman_token(token):
            if token in pending_seen:
                continue
            pending_seen.add(token)
            pending.append(token)
            continue
        if token in overlay:
            continue
        if token in pending_seen:
            continue
        pending_seen.add(token)
        pending.append(token)
    if len(pending) == 0:
        persisted: dict[str, str] = {}
        for token in tokens:
            if is_unambiguous_roman(token):
                persisted[token] = KIND_ROMAN
        if len(persisted) > 0:
            cache = merge_spell_cache(persisted)
            for key, kind in cache.items():
                overlay[key] = kind
        return overlay
    classified = await fetch_spell_kinds(pending, spoken_text)
    merged: dict[str, str] = {}
    for token in pending:
        kind = classified.get(token)
        if kind is None:
            kind = fallback_kind(token)
        overlay[token] = kind
        if is_ambiguous_roman_token(token):
            continue
        merged[token] = kind
    for token in tokens:
        if is_unambiguous_roman(token):
            merged[token] = KIND_ROMAN
    if len(merged) > 0:
        cache = merge_spell_cache(merged)
        for key, kind in cache.items():
            overlay[key] = kind
        for token in context_romans:
            overlay[token] = KIND_ROMAN
        for token in pending:
            if is_ambiguous_roman_token(token):
                gemini_kind = classified.get(token)
                if gemini_kind is None:
                    gemini_kind = fallback_kind(token)
                overlay[token] = gemini_kind
    return overlay
