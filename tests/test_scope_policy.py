"""In-scope-only policy (MIIT knowledge + CE major)."""

from __future__ import annotations

from tutor.router import OUT_OF_SCOPE_ANSWER, classify_route


def test_classify_weather_is_other() -> None:
    assert classify_route("What is the weather in Tokyo today?", "", None) == "other"


def test_classify_python_loop_is_programming() -> None:
    route = classify_route("Python for loop ကို ရှင်းပြပါ", "", None)
    assert route == "programming"


def test_aaa_engine_refuses_off_topic(monkeypatch) -> None:
    from tutor.aaa_engine import AAAEngine

    monkeypatch.setattr("tutor.aaa_bootstrap.ensure_aaa_ready", lambda: None)

    async def boom(*args, **kwargs):
        raise AssertionError("must not call LLM for off-topic")

    monkeypatch.setattr("tutor.aaa_engine.generate_from_tutor_messages", boom)
    monkeypatch.setattr(
        "tutor.aaa_engine._generate_tutor_reply_async",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no miit graph")),
    )
    engine = AAAEngine()
    out = engine.answer("What's the score in football?", code="", history=None)
    assert out == OUT_OF_SCOPE_ANSWER
    assert engine.last_route == "other"


def test_aaa_engine_miit_without_grounding_refuses(monkeypatch) -> None:
    from tutor.aaa_engine import AAAEngine

    monkeypatch.setattr("tutor.aaa_bootstrap.ensure_aaa_ready", lambda: None)
    monkeypatch.setattr(
        "tutor.router.classify_route",
        lambda *a, **k: "miit",
    )
    monkeypatch.setattr(
        "tutor.router.inherit_thread_route",
        lambda *a, **k: None,
    )

    async def no_grounding(_text: str) -> bool:
        return False

    monkeypatch.setattr("tutor.aaa_engine.miit_question_has_grounding", no_grounding)
    engine = AAAEngine()
    out = engine.answer("Random unrelated MIIT-ish noise xyz", code="", history=None)
    assert out == OUT_OF_SCOPE_ANSWER
