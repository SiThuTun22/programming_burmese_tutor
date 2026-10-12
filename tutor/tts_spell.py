"""Classify Latin tokens as word, letter-spell, or Roman numeral for TTS."""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path

from tutor.config import TTS_SPELL_PATH
from tutor.tts_phrases import PAUSE_SENTINEL
from tutor.tts_roman import (
    KIND_ROMAN,
    apply_roman_cache,
    context_roman_tokens,
    is_ambiguous_roman_token,
    is_unambiguous_roman,
)

logger = logging.getLogger(__name__)

KIND_WORD = "word"
KIND_SPELL = "spell"
_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_LETTER_MAP_PATH = Path(__file__).resolve().parent / "tts_letter_map.json"
_lock = threading.Lock()
_letter_map: dict[str, str] | None = None
_ALLOWED_KINDS = {KIND_WORD, KIND_SPELL, KIND_ROMAN}
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
SPELL_PROMPT = (
    "Classify Latin tokens for Myanmar TTS. Return JSON only with an entries array. "
    "Each entry: token and kind (word, spell, or roman). "
    "kind word: speak as a normal word (Python, function, email, class). "
    "kind spell: speak letter by letter (ID, AD, opaque codes). "
    "kind roman: academic Roman numerals (Semester II, Physics III). "
    "Do not invent tokens. Only classify the listed tokens.\n\n"
    "Tokens (JSON array):\n{tokens}\n\n"
    "Speech text:\n{spoken_text}"
)


def load_letter_map() -> dict[str, str]:
    global _letter_map
    if _letter_map is not None:
        return _letter_map
    loaded: dict[str, str] = {}
    parsed = json.loads(_LETTER_MAP_PATH.read_text(encoding="utf-8"))
    if isinstance(parsed, dict):
        for key, value in parsed.items():
            if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
                loaded[key.strip()] = value.strip()
    _letter_map = loaded
    return loaded


def letters_for_speech(token: str) -> str:
    letter_map = load_letter_map()
    parts: list[str] = []
    for character in token:
        lookup = character.upper() if character.isalpha() else character
        parts.append(letter_map.get(lookup, character))
    return " ".join(parts)


def collect_latin_tokens(text: str) -> list[str]:
    found = _TOKEN_PATTERN.findall(text.replace(PAUSE_SENTINEL, " "))
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
    has_letter = has_digit = has_upper = has_lower = False
    for character in token:
        if character.isdigit():
            has_digit = True
        elif "A" <= character <= "Z":
            has_letter = True
            has_upper = True
        elif "a" <= character <= "z":
            has_letter = True
            has_lower = True
    if has_letter and has_digit:
        return KIND_SPELL
    if has_upper and has_lower and len(token) >= 8:
        return KIND_SPELL
    return KIND_WORD


def _read_raw_cache(path: Path) -> dict[str, str]:
    cache: dict[str, str] = {}
    if not path.is_file():
        return cache
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return cache
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        return cache
    for key, value in loaded.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        kind = value.strip()
        token = key.strip()
        if kind not in _ALLOWED_KINDS or not token or is_ambiguous_roman_token(token):
            continue
        cache[token] = KIND_ROMAN if is_unambiguous_roman(token) else kind
    return cache


def load_spell_cache() -> dict[str, str]:
    path = TTS_SPELL_PATH
    with _lock:
        cache = _read_raw_cache(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        return cache


def merge_spell_cache(entries: dict[str, str]) -> dict[str, str]:
    path = TTS_SPELL_PATH
    with _lock:
        cache = _read_raw_cache(path)
        for key, value in entries.items():
            token = key.strip()
            kind = value.strip()
            if not token or kind not in _ALLOWED_KINDS or is_ambiguous_roman_token(token):
                continue
            cache[token] = KIND_ROMAN if is_unambiguous_roman(token) else kind
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        return cache


def apply_spell_cache(text: str, cache: dict[str, str]) -> str:
    keys = [key for key, kind in cache.items() if kind == KIND_SPELL]
    keys.sort(key=len, reverse=True)
    spoken = text
    for key in keys:
        spoken = re.compile(r"\b" + re.escape(key) + r"\b").sub(letters_for_speech(key), spoken)
    return spoken


def apply_tts_token_cache(text: str, cache: dict[str, str]) -> str:
    spoken = apply_roman_cache(text, cache)
    return apply_spell_cache(spoken, cache)


def _parse_spell_entries(raw: str) -> list[dict]:
    payload = _FENCE_RE.sub("", (raw or "").strip()).strip()
    if not payload:
        return []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    rows = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def fetch_spell_kinds(tokens: list[str], spoken_text: str) -> dict[str, str]:
    from tutor.config import TTS_SKIP_GEMINI_HELPERS

    if TTS_SKIP_GEMINI_HELPERS:
        return {}
    if not tokens:
        return {}
    prompt = SPELL_PROMPT.format(
        tokens=json.dumps(tokens, ensure_ascii=False),
        spoken_text=spoken_text,
    )
    try:
        from tutor.gemini_client import get_tts_helper_gemini_client

        messages = [{"role": "user", "content": prompt}]
        kwargs = {"temperature": 0.0, "top_p": 1.0, "max_new_tokens": 256}
        raw = get_tts_helper_gemini_client().generate(messages, **kwargs)
    except Exception as exc:
        logger.warning("TTS spell classification skipped: %s", exc)
        return {}
    allowed = set(tokens)
    classified: dict[str, str] = {}
    for item in _parse_spell_entries(raw):
        token = str(item.get("token") or "").strip()
        kind = str(item.get("kind") or "").strip()
        if token not in allowed or kind not in _ALLOWED_KINDS:
            continue
        classified[token] = kind
    return classified


def resolve_spell_cache(spoken_text: str, lexicon_keys: list[str]) -> dict[str, str]:
    overlay = dict(load_spell_cache())
    tokens = collect_latin_tokens(spoken_text)
    context_romans = context_roman_tokens(spoken_text)
    for token in tokens:
        if is_unambiguous_roman(token):
            overlay[token] = KIND_ROMAN
    for token in context_romans:
        overlay[token] = KIND_ROMAN
    skipped = set(lexicon_keys)
    pending: list[str] = []
    pending_seen: set[str] = set()
    for token in tokens:
        if token in skipped or is_unambiguous_roman(token) or token in context_romans:
            continue
        if token in overlay and not is_ambiguous_roman_token(token):
            continue
        if token in pending_seen:
            continue
        pending_seen.add(token)
        pending.append(token)
    classified = fetch_spell_kinds(pending, spoken_text) if pending else {}
    merged: dict[str, str] = {}
    for token in pending:
        kind = classified.get(token)
        if kind is None:
            if not classified:
                continue
            kind = fallback_kind(token)
        overlay[token] = kind
        if not is_ambiguous_roman_token(token):
            merged[token] = kind
    for token in tokens:
        if is_unambiguous_roman(token):
            merged[token] = KIND_ROMAN
    if merged:
        overlay.update(merge_spell_cache(merged))
    for token in context_romans:
        overlay[token] = KIND_ROMAN
    return overlay
