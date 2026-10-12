"""TTS prefetch helpers."""

import threading
import time

from tutor.tts_prefetch import (
    _prefetch_key,
    _signal_job_done,
    is_speakable_answer,
    kickoff_answer_tts,
    prefetch_in_flight,
    prefetch_turns,
    wait_for_cached_audio,
)


def test_is_speakable_answer() -> None:
    assert not is_speakable_answer("")
    assert not is_speakable_answer("⚠️ failed")
    assert is_speakable_answer("မြန်မာ")


def test_prefetch_turns_skips_errors(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("tutor.tts_prefetch.TTS_ENABLED", True)
    monkeypatch.setattr("tutor.config.TUTOR_BACKEND", "hybrid")
    monkeypatch.setattr(
        "tutor.tts_prefetch._enqueue",
        lambda answer, _gender: calls.append(answer),
    )
    prefetch_turns(
        [
            {"question": "q", "answer": "⚠️ no"},
            {"question": "q2", "answer": "ok"},
        ]
    )
    assert calls == ["ok"]


def test_wait_for_cached_audio_immediate_hit(monkeypatch) -> None:
    monkeypatch.setattr("tutor.tts_prefetch.TTS_ENABLED", True)
    monkeypatch.setattr(
        "tutor.tts_prefetch.cached_audio_path",
        lambda _text, _gender: "/tmp/x.mp3",
    )
    assert wait_for_cached_audio("hello", "female", timeout_seconds=1) == "/tmp/x.mp3"


def test_wait_for_cached_audio_waits_until_done(monkeypatch) -> None:
    monkeypatch.setattr("tutor.tts_prefetch.TTS_ENABLED", True)
    answer = "wait me"
    key = _prefetch_key(answer)
    paths: list[str | None] = [None]

    def fake_cached(_text: str, _gender: str | None) -> str | None:
        return paths[0]

    monkeypatch.setattr("tutor.tts_prefetch.cached_audio_path", fake_cached)

    with monkeypatch.context() as ctx:
        ctx.setattr("tutor.tts_prefetch._jobs_in_flight", {key})
        ctx.setattr("tutor.tts_prefetch._guard", threading.Lock())

        def finish_later() -> None:
            time.sleep(0.05)
            paths[0] = "/tmp/ready.mp3"
            _signal_job_done(answer)

        threading.Thread(target=finish_later, daemon=True).start()
        hit = wait_for_cached_audio(answer, "female", timeout_seconds=2)
    assert hit == "/tmp/ready.mp3"
    assert not prefetch_in_flight(answer, "female")


def test_kickoff_answer_tts_enqueues_latest_and_history(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("tutor.tts_prefetch.TTS_ENABLED", True)
    monkeypatch.setattr(
        "tutor.tts_prefetch._enqueue",
        lambda answer, _gender: calls.append(answer),
    )
    kickoff_answer_tts(
        "new",
        "Female",
        [{"question": "q", "answer": "old"}],
    )
    assert calls == ["new"]
