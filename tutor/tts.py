"""Text-to-speech for tutor answers (edge-tts, Myanmar voices)."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from pathlib import Path

from tutor.config import (
    TTS_CACHE_DIR,
    TTS_ENABLED,
    TTS_VOICE,
    TTS_VOICE_FALLBACK,
)

logger = logging.getLogger(__name__)


def prepare_for_speech(text: str) -> str:
    """Normalize answer text before synthesis."""
    cleaned = text.strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def _cache_path() -> Path:
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return TTS_CACHE_DIR / f"{uuid.uuid4().hex}.mp3"


async def synthesize_to_file(text: str, out_path: Path, voice: str) -> Path:
    import edge_tts

    prepared = prepare_for_speech(text)
    if not prepared:
        raise ValueError("empty text")
    communicate = edge_tts.Communicate(prepared, voice=voice)
    await communicate.save(str(out_path))
    return out_path


async def _synthesize_with_fallback(text: str, out_path: Path) -> Path:
    try:
        return await synthesize_to_file(text, out_path, TTS_VOICE)
    except Exception as exc:
        if TTS_VOICE == TTS_VOICE_FALLBACK:
            raise
        logger.warning("TTS voice %s failed (%s); trying %s", TTS_VOICE, exc, TTS_VOICE_FALLBACK)
        return await synthesize_to_file(text, out_path, TTS_VOICE_FALLBACK)


def synthesize_sync(text: str) -> str | None:
    """Return path to MP3 file, or None if disabled / failed."""
    if not TTS_ENABLED:
        return None
    if not prepare_for_speech(text):
        return None
    out_path = _cache_path()
    try:
        asyncio.run(_synthesize_with_fallback(text, out_path))
        return str(out_path)
    except Exception as exc:
        logger.warning("TTS synthesis failed: %s", exc)
        if out_path.exists():
            out_path.unlink(missing_ok=True)
        return None
