"""AAA message-id TTS for Gradio (schedule_message_speech + wait)."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from pathlib import Path

from tutor.config import TTS_ENABLED
from tutor.tts import cached_audio_path, normalize_gender, synthesize_sync
from tutor.tts_prefetch import is_speakable_answer, opposite_gender, prefetch_pending

logger = logging.getLogger(__name__)

_turn_audio_id: dict[str, uuid.UUID] = {}
_preparing: set[uuid.UUID] = set()
_guard = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=_loop.run_forever,
                name="aaa-tts-loop",
                daemon=True,
            )
            thread.start()
        return _loop


def register_turn_audio(turn_id: str, message_id: uuid.UUID) -> None:
    with _guard:
        _turn_audio_id[turn_id] = message_id


def message_id_for_turn(turn_id: str) -> uuid.UUID | None:
    with _guard:
        return _turn_audio_id.get(turn_id)


def message_id_from_turn(turn: dict) -> uuid.UUID | None:
    for key in ("audio_message_id", "message_id"):
        raw = str(turn.get(key) or "").strip()
        if raw:
            try:
                return uuid.UUID(raw)
            except ValueError:
                pass
    tid = str(turn.get("tts_id") or turn.get("turn_id") or "").strip()
    if tid:
        return message_id_for_turn(tid)
    return None


def restore_turn_audio_ids(history: list[dict] | None) -> None:
    """Rebuild in-memory UUID map from persisted chat turns (survives restart)."""
    for turn in list(history or []):
        tid = str(turn.get("tts_id") or turn.get("turn_id") or "").strip()
        mid = message_id_from_turn(turn)
        if tid and mid is not None:
            register_turn_audio(tid, mid)


def turn_primary_gender(turn: dict) -> str:
    raw = str(turn.get("tts_voice") or "Female").strip()
    return normalize_gender(raw)


def aaa_prepare_in_flight(message_id: uuid.UUID) -> bool:
    with _guard:
        return message_id in _preparing


def aaa_audio_path_if_ready(message_id: uuid.UUID) -> Path | None:
    from app.ai.tts import audio_path_for_message

    path = audio_path_for_message(message_id)
    if path.is_file() and path.stat().st_size > 0:
        return path
    return None


def aaa_audio_file_ready(message_id: uuid.UUID) -> bool:
    return aaa_audio_path_if_ready(message_id) is not None


def aaa_primary_pending(turn: dict) -> bool:
    """True while AAA primary (ask-time voice) MP3 is actively being generated."""
    answer = str(turn.get("answer") or "").strip()
    if not is_speakable_answer(answer):
        return False
    message_id = message_id_from_turn(turn)
    if message_id is None:
        return False
    if aaa_audio_file_ready(message_id):
        return False
    return aaa_prepare_in_flight(message_id)


def aaa_audio_not_ready(turn: dict, gender: str | None) -> bool:
    """Ear spinner until a real MP3 exists for the current radio gender."""
    answer = str(turn.get("answer") or "").strip()
    if not is_speakable_answer(answer):
        return False
    radio = normalize_gender(gender)
    primary = turn_primary_gender(turn)
    if radio == primary:
        mid = message_id_from_turn(turn)
        if mid is not None and aaa_audio_file_ready(mid):
            return False
        if cached_audio_path(answer, radio):
            return False
        return True
    if cached_audio_path(answer, radio):
        return False
    return prefetch_pending(answer, radio)


def aaa_prefetch_in_progress(turn: dict) -> bool:
    """Backward-compatible: primary AAA path still generating."""
    return aaa_primary_pending(turn)


def message_id_for_text(text: str, history: list[dict] | None) -> uuid.UUID | None:
    """Resolve message UUID for TTS file lookup (memory map or persisted on turn)."""
    target = (text or "").strip()
    if not target:
        return None
    for turn in reversed(list(history or [])):
        answer = str(turn.get("answer") or "").strip()
        if answer != target:
            continue
        for key in ("audio_message_id", "message_id"):
            raw = str(turn.get(key) or "").strip()
            if raw:
                try:
                    return uuid.UUID(raw)
                except ValueError:
                    pass
        tid = str(turn.get("tts_id") or turn.get("turn_id") or "").strip()
        if tid:
            mid = message_id_for_turn(tid)
            if mid:
                return mid
    return None


def _schedule_secondary_cache(answer: str, primary_voice: str | None) -> None:
    secondary = opposite_gender(primary_voice)
    if cached_audio_path(answer, secondary):
        return
    try:
        synthesize_sync(answer, secondary)
    except Exception as exc:
        logger.warning("AAA secondary TTS cache failed: %s", exc)


def kickoff_aaa_tts(
    answer: str,
    voice: str | None,
    turn_id: str,
    message_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Schedule AAA background TTS; reuse persisted UUID when present."""
    existing = message_id or message_id_for_turn(turn_id)
    if existing is None:
        existing = uuid.uuid4()
    register_turn_audio(turn_id, existing)
    if not TTS_ENABLED or not is_speakable_answer(answer):
        return existing
    file_ready = aaa_audio_file_ready(existing)
    with _guard:
        already = existing in _preparing
        if not file_ready and not already:
            _preparing.add(existing)
            should_prepare = True
        else:
            should_prepare = False
    if not should_prepare:
        if file_ready:
            threading.Thread(
                target=_schedule_secondary_cache,
                args=(answer, voice),
                daemon=True,
                name="aaa-tts-secondary",
            ).start()
        return existing
    from app.db.enums import TutorAvatar
    from app.ai.tts import prepare_message_speech

    avatar = TutorAvatar.MALE if (voice or "").strip().lower() == "male" else TutorAvatar.FEMALE
    loop = _ensure_loop()

    async def _bg() -> None:
        try:
            await prepare_message_speech(existing, answer, avatar)
        except Exception as exc:
            logger.warning("AAA TTS prefetch failed for %s: %s", existing, exc)
        finally:
            with _guard:
                _preparing.discard(existing)
        await asyncio.to_thread(_schedule_secondary_cache, answer, voice)

    asyncio.run_coroutine_threadsafe(_bg(), loop)
    return existing


def wait_for_aaa_audio(
    message_id: uuid.UUID,
    content: str,
    voice: str | None,
    *,
    timeout_seconds: float = 120.0,
) -> Path | None:
    from app.ai.tts import audio_path_for_message, speech_bytes_for_message
    from app.db.enums import TutorAvatar

    path = audio_path_for_message(message_id)
    if path.is_file():
        return path
    avatar = TutorAvatar.MALE if (voice or "").strip().lower() == "male" else TutorAvatar.FEMALE
    loop = _ensure_loop()

    async def _prepare() -> None:
        await speech_bytes_for_message(message_id, content, avatar)

    future = asyncio.run_coroutine_threadsafe(_prepare(), loop)
    try:
        future.result(timeout=timeout_seconds)
    except Exception as exc:
        logger.warning("AAA TTS wait failed: %s", exc)
    return path if path.is_file() else None
