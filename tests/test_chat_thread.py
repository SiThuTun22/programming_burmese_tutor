"""Chat thread helpers (no live Gradio server)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "serve_gradio",
    ROOT / "scripts" / "serve_gradio.py",
)
assert _SPEC and _SPEC.loader
_SERVE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SERVE)
history_to_messages = _SERVE.history_to_messages
message_text_from_like = _SERVE.message_text_from_like
_error_answer = _SERVE._error_answer


def test_history_to_messages_keeps_every_turn() -> None:
    history = [
        {"question": "MIIT ဆိုတာ ဘာလဲ။", "answer": "တက္ကသိုလ်။"},
        {"question": "CSE သင်တန်း ဘယ်နှစ်လဲ?", "answer": "၅ နှစ်။"},
    ]
    messages = history_to_messages(history)
    assert messages == [
        {"role": "user", "content": "MIIT ဆိုတာ ဘာလဲ။"},
        {"role": "assistant", "content": "တက္ကသိုလ်။"},
        {"role": "user", "content": "CSE သင်တန်း ဘယ်နှစ်လဲ?"},
        {"role": "assistant", "content": "၅ နှစ်။"},
    ]


def test_history_to_messages_empty() -> None:
    assert history_to_messages([]) == []
    assert history_to_messages(None) == []


class _Like:
    def __init__(self, value: object) -> None:
        self.value = value


def test_message_text_from_like_string() -> None:
    assert message_text_from_like(_Like("တက္ကသိုလ်။")) == "တက္ကသိုလ်။"


def test_message_text_from_like_dict() -> None:
    assert message_text_from_like(_Like({"text": "၅ နှစ်။"})) == "၅ နှစ်။"
    assert message_text_from_like(_Like({"content": "CSE"})) == "CSE"
    assert message_text_from_like(_Like({})) == ""


def test_error_answer_quota_keeps_burmese_copy() -> None:
    text = _error_answer("429 RESOURCE_EXHAUSTED")
    assert "Quota" in text
    assert "429" not in text


def test_play_history_turn_skips_warning() -> None:
    audio, text, status = next(_SERVE.play_history_turn(_Like("⚠️ API Rate limit")))
    assert text.startswith("⚠️")
    assert status == ""
    assert audio is not None


def test_play_history_turn_skips_when_tts_off(monkeypatch) -> None:
    monkeypatch.setattr(_SERVE, "TTS_ENABLED", False)
    audio, text, status = next(_SERVE.play_history_turn(_Like("CSE သင်တန်း။"), "Male"))
    assert text == "CSE သင်တန်း။"
    assert status == ""
    assert audio is not None


def test_respeak_skips_empty() -> None:
    audio, status = next(_SERVE.respeak("", "Female"))
    assert status == ""
    assert audio is not None


def test_error_answer_hides_raw_exception() -> None:
    leak = "models/gemini-nope is not found for API version v1beta"
    not_found = _error_answer(f"404 {leak}")
    assert "GEMINI_MODEL" in not_found
    assert leak not in not_found
    assert "404" not in not_found
    other = _error_answer("Connection reset by peer secret-token")
    assert "secret-token" not in other
    assert "VPN" in other
