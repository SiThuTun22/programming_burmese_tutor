"""Text-to-speech for tutor answers (edge-tts, Myanmar voices)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import threading
from pathlib import Path

from tutor.config import TTS_CACHE_DIR, TTS_ENABLED, TTS_VOICE
from tutor.speech_names import apply_dynamic_person_names, map_outside_urls, strip_http_urls

logger = logging.getLogger(__name__)

VOICE_MALE = "my-MM-ThihaNeural"
VOICE_FEMALE = "my-MM-NilarNeural"

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

SPEECH_NAME_MAP: tuple[tuple[str, str], ...] = (
    ("Cynthia Sin Thi Yar Myint", "စင်သီယာမြင့်"),
    ("Sin Thi Yar Myint", "စင်သီယာမြင့်"),
    ("Cynthia Myint", "စင်သီယာမြင့်"),
    ("Cynthida Myint", "စင်သီယာမြင့်"),
    ("Win Aye", "ဝင်းအေး"),
)
_LATIN_PAREN_RE = re.compile(r"[\(（]([^()（）]*)[\)）]")
_MYANMAR_RE = re.compile(r"[\u1000-\u109F]")
_TITLE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bProf\.?(?=\s|$)", "ပါမောက္ခ"),
    (r"\bDr\.?(?=\s|$)", "ဒေါက်တာ"),
)


def default_tts_gender() -> str:
    voice = (TTS_VOICE or "").lower()
    if "thiha" in voice or voice.strip() == "male":
        return "male"
    return "female"


def normalize_gender(voice: str | None) -> str:
    raw = str(voice or default_tts_gender()).strip().lower()
    if raw in ("female", "nilar"):
        return "female"
    if raw in ("male", "thiha"):
        return "male"
    return default_tts_gender()


def resolve_edge_voice(gender: str) -> str:
    if normalize_gender(gender) == "female":
        return VOICE_FEMALE
    return VOICE_MALE


def _replace_speech_names(segment: str) -> str:
    for english, myanmar in SPEECH_NAME_MAP:
        pattern = re.compile(re.escape(english), re.IGNORECASE)
        segment = pattern.sub(myanmar, segment)
    return segment


def _strip_latin_parens(segment: str) -> str:
    def drop(match: re.Match[str]) -> str:
        inner = match.group(1)
        if _MYANMAR_RE.search(inner):
            return match.group(0)
        return ""

    stripped = _LATIN_PAREN_RE.sub(drop, segment)
    return re.sub(r"[ \t]{2,}", " ", stripped)


def _replace_speech_titles(segment: str) -> str:
    for pattern, myanmar in _TITLE_PATTERNS:
        segment = re.sub(pattern, myanmar, segment, flags=re.IGNORECASE)
    return re.sub(r"[ \t]{2,}", " ", segment)


def prepare_for_speech(text: str) -> str:
    """Normalize answer text before synthesis."""
    cleaned = text.strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = strip_http_urls(cleaned)
    cleaned = map_outside_urls(cleaned, _strip_latin_parens)
    cleaned = map_outside_urls(cleaned, _replace_speech_names)
    cleaned = map_outside_urls(cleaned, _replace_speech_titles)
    return apply_dynamic_person_names(cleaned.strip())


def _lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def cache_key(text: str, gender: str | None = None) -> str:
    prepared = prepare_for_speech(text)
    voice = resolve_edge_voice(normalize_gender(gender))
    payload = f"{prepared}\n{voice}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]


def cache_path_for(text: str, gender: str | None = None) -> Path:
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return TTS_CACHE_DIR / f"{cache_key(text, gender)}.mp3"


def cached_audio_path(text: str, gender: str | None = None) -> str | None:
    if not TTS_ENABLED or not prepare_for_speech(text):
        return None
    path = cache_path_for(text, gender)
    if path.is_file() and path.stat().st_size > 0:
        return str(path)
    return None


async def synthesize_to_file(text: str, out_path: Path, voice: str) -> Path:
    import edge_tts

    prepared = prepare_for_speech(text)
    if not prepared:
        raise ValueError("empty text")
    communicate = edge_tts.Communicate(prepared, voice=voice)
    await communicate.save(str(out_path))
    return out_path


async def _synthesize_with_fallback(
    text: str,
    out_path: Path,
    primary: str,
    fallback: str,
) -> Path:
    try:
        return await synthesize_to_file(text, out_path, primary)
    except Exception as exc:
        if primary == fallback:
            raise
        logger.warning("TTS voice %s failed (%s); trying %s", primary, exc, fallback)
        return await synthesize_to_file(text, out_path, fallback)


async def _synthesize_gender(text: str, gender: str) -> Path:
    gender = normalize_gender(gender)
    out_path = cache_path_for(text, gender)
    if out_path.is_file() and out_path.stat().st_size > 0:
        return out_path
    primary = resolve_edge_voice(gender)
    fallback = VOICE_FEMALE if gender == "male" else VOICE_MALE
    tmp_path = out_path.with_name(out_path.name + ".partial")
    try:
        await _synthesize_with_fallback(text, tmp_path, primary, fallback)
        tmp_path.replace(out_path)
        return out_path
    except Exception:
        tmp_path.unlink(missing_ok=True)
        if out_path.exists() and out_path.stat().st_size == 0:
            out_path.unlink(missing_ok=True)
        raise


def synthesize_sync(text: str, voice: str | None = None) -> str | None:
    """Return path to MP3 file, or None if disabled / failed."""
    if not TTS_ENABLED:
        return None
    if not prepare_for_speech(text):
        return None
    gender = normalize_gender(voice)
    key = cache_key(text, gender)
    with _lock_for(key):
        cached = cached_audio_path(text, gender)
        if cached:
            return cached
        out_path = cache_path_for(text, gender)
        try:
            asyncio.run(_synthesize_gender(text, gender))
            return str(out_path) if out_path.is_file() else None
        except Exception as exc:
            logger.warning("TTS synthesis failed: %s", exc)
            return None


async def _synthesize_both(text: str) -> None:
    results = await asyncio.gather(
        _synthesize_gender(text, "male"),
        _synthesize_gender(text, "female"),
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, Exception):
            logger.warning("TTS synthesis failed: %s", result)


def synthesize_both_sync(text: str, selected_gender: str | None = None) -> str | None:
    """Synthesize male and female in parallel; return the selected voice path."""
    if not TTS_ENABLED:
        return None
    if not prepare_for_speech(text):
        return None
    selected = normalize_gender(selected_gender)
    try:
        asyncio.run(_synthesize_both(text))
    except Exception as exc:
        logger.warning("TTS synthesis failed: %s", exc)
    return cached_audio_path(text, selected) or synthesize_sync(text, selected)
