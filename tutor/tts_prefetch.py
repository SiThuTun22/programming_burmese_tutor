"""Background TTS prefetch: primary gender first, then opposite."""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from tutor.config import TTS_ENABLED
from tutor.tts import cached_audio_path, normalize_gender, synthesize_sync

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tts-prefetch")
_jobs_in_flight: set[str] = set()
_gender_in_flight: set[str] = set()
_primary_pending: set[str] = set()
_guard = threading.Lock()
_done_events: dict[str, threading.Event] = {}
WAIT_POLL_SECONDS = 0.35
DEFAULT_WAIT_TIMEOUT_SECONDS = 120

_SPEAK_SKIP_PREFIX = "⚠️"


def is_speakable_answer(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if stripped.startswith(_SPEAK_SKIP_PREFIX):
        return False
    if stripped == "မေးခွန်း ထည့်ပါ။":
        return False
    return True


def opposite_gender(gender: str | None) -> str:
    voice = normalize_gender(gender)
    return "female" if voice == "male" else "male"


def _answer_key(answer: str) -> str:
    return (answer or "").strip()


def _gender_key(answer: str, gender: str | None) -> str:
    return f"{_answer_key(answer)}\0{normalize_gender(gender)}"


def _prefetch_key(answer: str) -> str:
    """Backward-compatible job key (answer only)."""
    return _answer_key(answer)


def _both_cached(answer: str) -> bool:
    return bool(cached_audio_path(answer, "male")) and bool(
        cached_audio_path(answer, "female")
    )


def prefetch_in_flight(answer: str, gender: str | None = None) -> bool:
    if gender is not None:
        return prefetch_pending(answer, gender)
    key = _answer_key(answer)
    with _guard:
        return key in _jobs_in_flight


def prefetch_primary_pending(answer: str, primary_gender: str | None) -> bool:
    """True until ask-time (primary) gender audio is cached."""
    if not TTS_ENABLED or not is_speakable_answer(answer):
        return False
    primary = normalize_gender(primary_gender)
    if cached_audio_path(answer, primary):
        return False
    key = _answer_key(answer)
    with _guard:
        return key in _primary_pending


def prefetch_pending(answer: str, gender: str | None = None) -> bool:
    """True while the given gender's audio is not cached and prefetch may still run."""
    if not TTS_ENABLED or not is_speakable_answer(answer):
        return False
    voice = normalize_gender(gender)
    if cached_audio_path(answer, voice):
        return False
    gkey = _gender_key(answer, voice)
    with _guard:
        if gkey in _gender_in_flight:
            return True
        if _answer_key(answer) in _jobs_in_flight:
            return True
    return False


def _done_event(answer: str) -> threading.Event:
    key = _answer_key(answer)
    with _guard:
        event = _done_events.get(key)
        if event is None:
            event = threading.Event()
            _done_events[key] = event
        return event


def _set_gender_in_flight(answer: str, gender: str | None, active: bool) -> None:
    gkey = _gender_key(answer, gender)
    with _guard:
        if active:
            _gender_in_flight.add(gkey)
        else:
            _gender_in_flight.discard(gkey)


def _signal_job_done(answer: str) -> None:
    key = _answer_key(answer)
    with _guard:
        _jobs_in_flight.discard(key)
        _primary_pending.discard(key)
        _done_events.setdefault(key, threading.Event()).set()


def _synth_gender(answer: str, gender: str | None) -> None:
    voice = normalize_gender(gender)
    if cached_audio_path(answer, voice):
        return
    _set_gender_in_flight(answer, voice, True)
    try:
        synthesize_sync(answer, voice)
    except Exception as exc:
        logger.warning("TTS prefetch failed (%s): %s", voice, exc)
    finally:
        _set_gender_in_flight(answer, voice, False)


def _prefetch_one(answer: str, primary_gender: str | None) -> None:
    key = _answer_key(answer)
    if not TTS_ENABLED or not is_speakable_answer(answer):
        _signal_job_done(answer)
        return
    primary = normalize_gender(primary_gender)
    secondary = opposite_gender(primary)
    try:
        _synth_gender(answer, primary)
    finally:
        with _guard:
            _primary_pending.discard(key)
    _synth_gender(answer, secondary)
    _signal_job_done(answer)


def _enqueue(answer: str, primary_gender: str | None) -> None:
    if not TTS_ENABLED or not is_speakable_answer(answer):
        return
    if _both_cached(answer):
        return
    key = _answer_key(answer)
    primary = normalize_gender(primary_gender)
    with _guard:
        if key in _jobs_in_flight:
            return
        _jobs_in_flight.add(key)
        if not cached_audio_path(answer, primary):
            _primary_pending.add(key)
        _done_events.setdefault(key, threading.Event()).clear()
    _executor.submit(_prefetch_one, answer, primary_gender)


def prefetch_answer(answer: str, gender: str | None = None) -> None:
    _enqueue(answer, gender)


def _answers_in_history(history: list[dict] | None) -> set[str]:
    allowed: set[str] = set()
    for turn in list(history or []):
        answer = str(turn.get("answer", "")).strip()
        if is_speakable_answer(answer):
            allowed.add(answer)
    return allowed


def sync_prefetch_scope(history: list[dict] | None) -> None:
    """Drop in-flight prefetch state for answers no longer in this chat."""
    allowed = _answers_in_history(history)
    with _guard:
        for key in list(_jobs_in_flight):
            if key not in allowed:
                _jobs_in_flight.discard(key)
                _primary_pending.discard(key)
        for gkey in list(_gender_in_flight):
            ans = gkey.split("\0", 1)[0]
            if ans not in allowed:
                _gender_in_flight.discard(gkey)


def prefetch_turns(history: list[dict] | None, gender: str | None = None) -> None:
    sync_prefetch_scope(history)
    from tutor.config import TUTOR_BACKEND

    if TUTOR_BACKEND == "aaa":
        from tutor.aaa_tts import kickoff_aaa_tts, message_id_from_turn, restore_turn_audio_ids

        restore_turn_audio_ids(history)
        for turn in list(history or []):
            answer = str(turn.get("answer", "")).strip()
            if not is_speakable_answer(answer):
                continue
            turn_id = str(turn.get("tts_id") or turn.get("turn_id") or "").strip()
            if not turn_id:
                import uuid

                turn_id = uuid.uuid4().hex
                turn["turn_id"] = turn_id
                turn["tts_id"] = turn_id
            primary = turn.get("tts_voice") or gender
            mid = message_id_from_turn(turn)
            audio_id = kickoff_aaa_tts(answer, primary, turn_id, message_id=mid)
            turn["audio_message_id"] = str(audio_id)
            if not turn.get("tts_voice") and primary:
                turn["tts_voice"] = str(primary)
        return
    for turn in list(history or []):
        answer = str(turn.get("answer", "")).strip()
        if not is_speakable_answer(answer):
            continue
        primary = turn.get("tts_voice") or gender
        _enqueue(answer, primary)


def kickoff_answer_tts(
    answer: str,
    voice: str | None,
    history: list[dict] | None = None,
) -> None:
    """Enqueue prefetch for the latest answer only (idempotent)."""
    del history
    prefetch_answer(answer, voice)


def wait_for_cached_audio(
    answer: str,
    gender: str | None = None,
    *,
    timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
    poll_seconds: float = WAIT_POLL_SECONDS,
) -> str | None:
    """Return cached MP3 path when ready; wait if prefetch is in flight."""
    if not TTS_ENABLED or not is_speakable_answer(answer):
        return None
    voice = normalize_gender(gender)
    hit = cached_audio_path(answer, voice)
    if hit:
        return hit
    deadline = time.monotonic() + timeout_seconds
    event = _done_event(answer)
    while time.monotonic() < deadline:
        hit = cached_audio_path(answer, voice)
        if hit:
            return hit
        if not prefetch_pending(answer, voice) and event.is_set():
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        event.wait(timeout=min(poll_seconds, remaining))
    return cached_audio_path(answer, voice)


def resolve_cached_or_wait(
    answer: str,
    gender: str | None = None,
    *,
    timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
) -> str | None:
    return wait_for_cached_audio(
        answer,
        gender,
        timeout_seconds=timeout_seconds,
    )
