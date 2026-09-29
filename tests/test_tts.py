"""TTS helpers (no network in most tests)."""

from __future__ import annotations

from pathlib import Path

from tutor.tts import prepare_for_speech, synthesize_sync


def test_prepare_for_speech_collapses_whitespace() -> None:
    raw = "Hello   world\n\n\n\nMyanmar"
    assert prepare_for_speech(raw) == "Hello world\n\nMyanmar"


def test_synthesize_sync_disabled(monkeypatch) -> None:
    monkeypatch.setattr("tutor.tts.TTS_ENABLED", False)
    assert synthesize_sync("text") is None


def test_synthesize_sync_returns_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("tutor.tts.TTS_ENABLED", True)
    monkeypatch.setattr("tutor.tts.TTS_CACHE_DIR", tmp_path)
    target = tmp_path / "speech.mp3"
    monkeypatch.setattr("tutor.tts._cache_path", lambda: target)

    async def ok(text: str, path: Path) -> Path:
        path.write_bytes(b"\x00")
        return path

    monkeypatch.setattr("tutor.tts._synthesize_with_fallback", ok)

    result = synthesize_sync("မြန်မာ")
    assert result == str(target)
    assert target.is_file()
