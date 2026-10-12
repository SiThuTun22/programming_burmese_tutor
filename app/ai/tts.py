from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

import edge_tts

from app.ai.errors import LlmUnavailableError
from app.ai.tts_lexicon import apply_lexicon, load_lexicon, merge_lexicon
from app.ai.tts_phrases import PAUSE_SENTINEL, strip_markdown_for_speech
from app.ai.tts_pronounce import fetch_new_pronunciations
from app.ai.tts_segments import runs_are_english_only, split_script_runs
from app.ai.tts_spell import apply_tts_token_cache, resolve_spell_cache
from app.db.enums import TutorAvatar
from app.lib.config import get_tts_audio_dir, get_tts_english_rate

logger = logging.getLogger(__name__)

VOICE_FEMALE = 'my-MM-NilarNeural'
VOICE_MALE = 'my-MM-ThihaNeural'
MAX_SPEECH_CHARS = 4000
_TTS_DOWN = 'Text-to-speech is not reachable. Check network access.'

_prepare_locks: dict[str, asyncio.Lock] = {}
_prepare_guard = asyncio.Lock()
_preparing: set[str] = set()


def voice_for_avatar(tutor_avatar: TutorAvatar | str) -> str:
    avatar_value = str(tutor_avatar)
    if avatar_value == TutorAvatar.MALE.value:
        return VOICE_MALE
    return VOICE_FEMALE


def infer_tutor_avatar(content: str) -> TutorAvatar | None:
    if 'ကျွန်တော်' in content:
        return TutorAvatar.MALE
    if 'ခင်ဗျာ' in content:
        return TutorAvatar.MALE
    if 'ကျွန်မ' in content:
        return TutorAvatar.FEMALE
    if 'ရှင်' in content:
        return TutorAvatar.FEMALE
    return None


def resolve_speech_avatar(
    message_avatar: TutorAvatar | str | None,
    content: str,
    session_avatar: TutorAvatar | str,
) -> str:
    if message_avatar is not None:
        avatar_value = str(message_avatar)
        if len(avatar_value) > 0:
            return avatar_value
    inferred = infer_tutor_avatar(content)
    if inferred is not None:
        return inferred.value
    return str(session_avatar)


def message_speech_ready(message_id: uuid.UUID) -> bool:
    path = audio_path_for_message(message_id)
    if not path.is_file():
        return False
    return path.stat().st_size > 0


def message_speech_pending(message_id: uuid.UUID) -> bool:
    if message_speech_ready(message_id):
        return False
    return str(message_id) in _preparing


def audio_path_for_message(message_id: uuid.UUID) -> Path:
    audio_dir = get_tts_audio_dir()
    audio_dir.mkdir(parents=True, exist_ok=True)
    file_name = f'{message_id}.mp3'
    path = audio_dir / file_name
    return path


async def _lock_for_message(message_id: uuid.UUID) -> asyncio.Lock:
    key = str(message_id)
    async with _prepare_guard:
        existing = _prepare_locks.get(key)
        if existing is not None:
            return existing
        created = asyncio.Lock()
        _prepare_locks[key] = created
        return created


async def _synthesize_one(text: str, voice: str, rate: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    stream = communicate.stream()
    chunks: list[bytes] = []
    async for message in stream:
        message_type = message.get('type')
        if message_type != 'audio':
            continue
        data = message.get('data')
        if isinstance(data, bytes):
            chunks.append(data)
    audio = b''.join(chunks)
    if len(audio) == 0:
        raise LlmUnavailableError(_TTS_DOWN)
    return audio


async def _synthesize_phrase(spoken: str, voice: str, default_rate: str, english_rate: str) -> bytes:
    runs = split_script_runs(spoken)
    rate = default_rate
    if runs_are_english_only(runs):
        rate = english_rate
    audio = await _synthesize_one(spoken, voice, rate)
    return audio


async def synthesize_plain(spoken: str, tutor_avatar: TutorAvatar | str) -> bytes:
    if len(spoken) == 0:
        raise LlmUnavailableError('This message has no readable text to speak.')
    clipped = spoken
    if len(clipped) > MAX_SPEECH_CHARS:
        clipped = clipped[:MAX_SPEECH_CHARS]
    voice = voice_for_avatar(tutor_avatar)
    default_rate = '+0%'
    english_rate = get_tts_english_rate()
    raw_phrases = clipped.split(PAUSE_SENTINEL)
    phrases: list[str] = []
    for raw_phrase in raw_phrases:
        phrase = raw_phrase.strip()
        if len(phrase) == 0:
            continue
        phrases.append(phrase)
    if len(phrases) == 0:
        raise LlmUnavailableError('This message has no readable text to speak.')
    try:
        clips: list[bytes] = []
        for phrase in phrases:
            clip = await _synthesize_phrase(phrase, voice, default_rate, english_rate)
            clips.append(clip)
        joined = b''.join(clips)
        return joined
    except LlmUnavailableError:
        raise
    except Exception as error:
        logger.warning('Segmented TTS failed; using a single clip: %s', error)
        fallback_text = ' '.join(phrases)
        try:
            audio = await _synthesize_one(fallback_text, voice, default_rate)
            return audio
        except Exception as fallback_error:
            raise LlmUnavailableError(_TTS_DOWN) from fallback_error


async def prepare_message_speech(
    message_id: uuid.UUID,
    content: str,
    tutor_avatar: TutorAvatar | str,
) -> bytes:
    message_key = str(message_id)
    lock = await _lock_for_message(message_id)
    async with lock:
        path = audio_path_for_message(message_id)
        if path.is_file():
            stored = path.read_bytes()
            return stored
        owned_pending = message_key not in _preparing
        if owned_pending:
            _preparing.add(message_key)
        try:
            spoken = strip_markdown_for_speech(content)
            lexicon = load_lexicon()
            existing_keys: list[str] = []
            for lex_key in lexicon:
                existing_keys.append(lex_key)
            new_entries = await fetch_new_pronunciations(spoken, existing_keys)
            if len(new_entries) > 0:
                lexicon = merge_lexicon(new_entries)
            spoken = apply_lexicon(spoken, lexicon)
            lexicon_keys: list[str] = []
            for lex_key in lexicon:
                lexicon_keys.append(lex_key)
            spell_cache = await resolve_spell_cache(spoken, lexicon_keys)
            spoken = apply_tts_token_cache(spoken, spell_cache)
            audio = await synthesize_plain(spoken, tutor_avatar)
            path.write_bytes(audio)
            return audio
        finally:
            if owned_pending:
                _preparing.discard(message_key)


def schedule_message_speech(
    message_id: uuid.UUID,
    content: str,
    tutor_avatar: TutorAvatar | str,
) -> None:
    if message_speech_ready(message_id):
        return
    avatar_value = str(tutor_avatar)
    key = str(message_id)
    _preparing.add(key)

    async def _run() -> None:
        try:
            await prepare_message_speech(message_id, content, avatar_value)
        except Exception as error:
            logger.warning('Background TTS failed for %s: %s', message_id, error)
        finally:
            _preparing.discard(key)

    asyncio.create_task(_run())


async def speech_bytes_for_message(
    message_id: uuid.UUID,
    content: str,
    tutor_avatar: TutorAvatar | str,
) -> bytes:
    audio = await prepare_message_speech(message_id, content, tutor_avatar)
    return audio
