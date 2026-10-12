"""AAA Gradio engine (programming path uses hybrid prompts)."""

from __future__ import annotations

from tutor.aaa_engine import AAAEngine


def test_aaa_engine_programming_uses_generate(monkeypatch) -> None:
    monkeypatch.setattr("tutor.aaa_bootstrap.ensure_aaa_ready", lambda: None)
    captured: list[list[dict]] = []

    def generate(messages: list[dict], **kwargs) -> str:
        captured.append(messages)
        return "ဆရာ့အဖြေ: loop answer"

    async def fake_llm(messages, *, temperature, top_p):
        generate(messages)
        return "ဆရာ့အဖြေ: loop answer"

    monkeypatch.setattr(
        "tutor.aaa_engine.generate_from_tutor_messages",
        fake_llm,
    )
    engine = AAAEngine()
    out = engine.answer("Python for loop ရှင်းပြပါ", code="", history=None, voice="Female")
    assert "loop answer" in out
    assert captured
    assert engine.last_route == "gemini"


def test_aaa_engine_other_out_of_scope(monkeypatch) -> None:
    monkeypatch.setattr("tutor.aaa_bootstrap.ensure_aaa_ready", lambda: None)
    monkeypatch.setattr("tutor.aaa_bootstrap.ensure_aaa_ready", lambda: None)

    async def noop(*a, **k):
        return "x"

    monkeypatch.setattr("tutor.aaa_engine.generate_from_tutor_messages", noop)
    engine = AAAEngine()
    out = engine.answer("What is the weather in Tokyo?", code="", history=None)
    assert "MIIT" in out or "အပြင်ဘက်" in out
