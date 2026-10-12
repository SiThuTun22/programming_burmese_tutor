"""Message-id TTS ready / pending helpers."""

from __future__ import annotations

import uuid

from app.ai.tts import (
    _preparing,
    message_speech_pending,
    schedule_message_speech,
)


def test_message_speech_pending_while_preparing(monkeypatch) -> None:
    mid = uuid.uuid4()
    monkeypatch.setattr(
        'app.ai.tts.message_speech_ready',
        lambda _m: False,
    )
    _preparing.add(str(mid))
    try:
        assert message_speech_pending(mid) is True
    finally:
        _preparing.discard(str(mid))


def test_message_speech_not_pending_when_ready(monkeypatch) -> None:
    mid = uuid.uuid4()
    monkeypatch.setattr(
        'app.ai.tts.message_speech_ready',
        lambda _m: True,
    )
    _preparing.add(str(mid))
    assert message_speech_pending(mid) is False


def test_schedule_skips_when_already_ready(monkeypatch) -> None:
    mid = uuid.uuid4()
    monkeypatch.setattr(
        'app.ai.tts.message_speech_ready',
        lambda _m: True,
    )
    schedule_message_speech(mid, 'hello', 'female')
    assert str(mid) not in _preparing
