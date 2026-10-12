"""Prefetch pending helpers."""

from tutor.tts_prefetch import (
    prefetch_pending,
    prefetch_primary_pending,
)


def test_prefetch_pending_when_in_flight(monkeypatch) -> None:
    monkeypatch.setattr("tutor.tts_prefetch.TTS_ENABLED", True)
    monkeypatch.setattr("tutor.tts_prefetch.cached_audio_path", lambda _a, _g: None)
    monkeypatch.setattr(
        "tutor.tts_prefetch._gender_in_flight",
        {"hello\0female"},
    )
    assert prefetch_pending("hello", "Female") is True


def test_prefetch_not_pending_when_cached(monkeypatch) -> None:
    monkeypatch.setattr("tutor.tts_prefetch.TTS_ENABLED", True)
    monkeypatch.setattr(
        "tutor.tts_prefetch.cached_audio_path",
        lambda _a, _g: "/tmp/x.mp3",
    )
    assert prefetch_pending("hello", "Female") is False


def test_primary_pending_until_primary_cached(monkeypatch) -> None:
    monkeypatch.setattr("tutor.tts_prefetch.TTS_ENABLED", True)
    calls: list[str] = []

    def fake_cached(_answer: str, gender: str | None) -> str | None:
        calls.append(str(gender))
        return "/tmp/m.mp3" if gender == "male" else None

    monkeypatch.setattr("tutor.tts_prefetch.cached_audio_path", fake_cached)
    monkeypatch.setattr(
        "tutor.tts_prefetch._guard",
        __import__("threading").Lock(),
    )
    monkeypatch.setattr("tutor.tts_prefetch._primary_pending", {"hello"})
    assert prefetch_primary_pending("hello", "Male") is False
    assert prefetch_primary_pending("hello", "Female") is True
