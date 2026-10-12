"""Two-phase TTS prefetch order."""

from __future__ import annotations

import threading
import time

from tutor.tts_prefetch import (
    _prefetch_key,
    _signal_job_done,
    prefetch_primary_pending,
    prefetch_pending,
)


def test_prefetch_one_primary_before_secondary(monkeypatch) -> None:
    order: list[str] = []

    def fake_synth(answer: str, gender: str | None) -> str | None:
        order.append(str(gender))
        return f"/tmp/{gender}.mp3"

    monkeypatch.setattr("tutor.tts_prefetch.TTS_ENABLED", True)
    monkeypatch.setattr("tutor.tts_prefetch.cached_audio_path", lambda _a, _g: None)
    monkeypatch.setattr("tutor.tts_prefetch.synthesize_sync", fake_synth)

    from tutor.tts_prefetch import _prefetch_one

    _prefetch_one("hello", "Male")
    assert order == ["male", "female"]
    assert prefetch_primary_pending("hello", "Male") is False


def test_wait_for_cached_audio_waits_until_done(monkeypatch) -> None:
    monkeypatch.setattr("tutor.tts_prefetch.TTS_ENABLED", True)
    answer = "wait me"
    paths: list[str | None] = [None]

    def fake_cached(_text: str, _gender: str | None) -> str | None:
        return paths[0]

    monkeypatch.setattr("tutor.tts_prefetch.cached_audio_path", fake_cached)

    key = _prefetch_key(answer)
    with monkeypatch.context() as ctx:
        ctx.setattr("tutor.tts_prefetch._jobs_in_flight", {key})
        ctx.setattr("tutor.tts_prefetch._guard", threading.Lock())

        def finish_later() -> None:
            time.sleep(0.05)
            paths[0] = "/tmp/ready.mp3"
            _signal_job_done(answer)

        threading.Thread(target=finish_later, daemon=True).start()
        from tutor.tts_prefetch import wait_for_cached_audio

        hit = wait_for_cached_audio(answer, "female", timeout_seconds=2)
    assert hit == "/tmp/ready.mp3"
    assert prefetch_pending(answer, "female") is False
