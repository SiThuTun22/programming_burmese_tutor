"""TTS-only person-name Myanmar spellings (static map + optional Gemini JSON)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path

from tutor.config import TTS_CACHE_DIR

logger = logging.getLogger(__name__)

NameGenerateFn = Callable[..., str]

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_CANDIDATE_RE = re.compile(r"(?:Dr\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}")
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

NAME_BLOCKLIST = frozenset(
    {
        "react",
        "nlp",
        "miit",
        "html",
        "css",
        "api",
        "javascript",
        "python",
        "laravel",
        "hook",
        "fragment",
        "usestate",
        "gemini",
        "natural",
        "language",
        "processing",
        "institute",
        "information",
        "technology",
        "university",
        "international",
        "journal",
        "researchgate",
        "linkedin",
        "character",
        "clustering",
        "springer",
        "myanmar",
        "hello",
        "world",
    }
)

_NAME_PROMPT = (
    "List person names written in English (Latin letters) in the text. "
    "Return JSON only with this shape: "
    '{"replacements":[{"en":"Jane Doe","my":"ဂျိန်းဒိုး"}]}. '
    "Person names only. Never programming terms, products, organizations, "
    "or acronyms (React, NLP, MIIT, HTML, CSS, API). "
    "my must be Myanmar script for pronunciation. "
    "Use an empty replacements list if there are no person names.\n\n"
    "Text:\n"
)

_memory: dict[str, list[tuple[str, str]]] = {}
_generate_fn: NameGenerateFn | None = None


def set_speech_name_generate_fn(fn: NameGenerateFn | None) -> None:
    global _generate_fn
    _generate_fn = fn


def clear_speech_name_cache() -> None:
    _memory.clear()


def strip_http_urls(text: str) -> str:
    """Remove http(s) URLs so they are not spoken. Chat text is unchanged."""
    cleaned = _URL_RE.sub(" ", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def map_outside_urls(text: str, transform) -> str:
    parts: list[str] = []
    last = 0
    for match in _URL_RE.finditer(text):
        parts.append(transform(text[last:match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(transform(text[last:]))
    return "".join(parts)


def _tokens(span: str) -> list[str]:
    cleaned = re.sub(r"^Dr\.?\s+", "", span, flags=re.IGNORECASE)
    return [part for part in re.split(r"\s+", cleaned) if part]


def name_candidates(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def collect(segment: str) -> str:
        for match in _CANDIDATE_RE.finditer(segment):
            span = match.group(0)
            words = _tokens(span)
            if not words:
                continue
            if any(word.lower().strip(".") in NAME_BLOCKLIST for word in words):
                continue
            key = span.lower()
            if key not in seen:
                seen.add(key)
                found.append(span)
        return segment

    map_outside_urls(text, collect)
    return found


def _parse_replacements(raw: str) -> list[tuple[str, str]]:
    payload = _FENCE_RE.sub("", raw.strip()).strip()
    if not payload:
        return []
    data = json.loads(payload)
    rows = data.get("replacements") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    out: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        english = str(row.get("en") or "").strip()
        myanmar = str(row.get("my") or "").strip()
        if not english or not myanmar:
            continue
        if any(part.lower().strip(".") in NAME_BLOCKLIST for part in _tokens(english)):
            continue
        out.append((english, myanmar))
    out.sort(key=lambda item: len(item[0]), reverse=True)
    return out


def _names_cache_path(cache_key: str) -> Path:
    directory = Path(TTS_CACHE_DIR) / "names"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{cache_key}.json"


def _load_cached(cache_key: str) -> list[tuple[str, str]] | None:
    if cache_key in _memory:
        return _memory[cache_key]
    path = _names_cache_path(cache_key)
    if not path.is_file():
        return None
    try:
        rows = _parse_replacements(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    _memory[cache_key] = rows
    return rows


def _store_cached(cache_key: str, rows: list[tuple[str, str]]) -> None:
    _memory[cache_key] = rows
    path = _names_cache_path(cache_key)
    payload = {
        "replacements": [{"en": english, "my": myanmar} for english, myanmar in rows]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _call_name_model(prompt: str) -> str:
    kwargs = {"temperature": 0.0, "top_p": 1.0, "max_new_tokens": 256}
    messages = [{"role": "user", "content": prompt}]
    if _generate_fn is not None:
        return str(_generate_fn(messages, **kwargs) or "")
    from tutor.gemini_client import get_tts_helper_gemini_client

    return get_tts_helper_gemini_client().generate(messages, **kwargs)


def fetch_dynamic_replacements(text: str) -> list[tuple[str, str]]:
    if not name_candidates(text):
        return []
    cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    cached = _load_cached(cache_key)
    if cached is not None:
        return cached
    try:
        raw = _call_name_model(_NAME_PROMPT + text)
        rows = _parse_replacements(raw)
    except Exception as exc:
        logger.warning("TTS name lookup failed: %s", exc)
        return []
    _store_cached(cache_key, rows)
    return rows


def apply_named_replacements(text: str, rows: list[tuple[str, str]]) -> str:
    def replace_segment(segment: str) -> str:
        for english, myanmar in rows:
            if not english:
                continue
            pattern = re.compile(re.escape(english), re.IGNORECASE)
            segment = pattern.sub(myanmar, segment)
        return segment

    return map_outside_urls(text, replace_segment)


def apply_dynamic_person_names(text: str) -> str:
    rows = fetch_dynamic_replacements(text)
    if not rows:
        return text
    return apply_named_replacements(text, rows)
