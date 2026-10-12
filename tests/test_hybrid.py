"""Hybrid chat routing (no live Gemini)."""

from __future__ import annotations

import pytest

from tutor.hybrid import HybridEngine
from tutor.router import clear_route_cache, set_route_generate_fn


@pytest.fixture(autouse=True)
def _reset_router(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    monkeypatch.setattr("tutor.router.ROUTER_CACHE_DIR", tmp_path / "router")
    set_route_generate_fn(None)
    clear_route_cache()
    yield
    set_route_generate_fn(None)
    clear_route_cache()


def _engine(generate_fn) -> HybridEngine:
    return HybridEngine(generate_fn=generate_fn)


def test_question_calls_gemini_not_stored_answer() -> None:
    calls: list[list[dict]] = []

    def generate(messages: list[dict]) -> str:
        calls.append(messages)
        return "GEMINI"

    engine = _engine(generate)
    answer = engine.answer("Fragment ဆိုတာ ဘာလဲ?", "")
    assert answer == "GEMINI"
    assert calls
    prompt = calls[0][0]["content"]
    assert "အလယ်အလတ်" in prompt
    assert "စာအုပ်မှ ကိုးကား:" not in prompt
    assert engine.last_route == "gemini"
    assert engine.last_badge == "Gemini"


def test_answer_strips_teacher_cue() -> None:
    engine = _engine(lambda _messages: "ဆရာ့အဖြေ:\nမင်္ဂလာပါ။")
    answer = engine.answer("Fragment ဆိုတာ ဘာလဲ?", "")
    assert answer == "မင်္ဂလာပါ။"
    assert "ဆရာ့အဖြေ:" not in answer


def test_code_question_calls_gemini() -> None:
    engine = _engine(lambda messages: f"GEMINI:{messages[0]['content']}")
    answer = engine.answer("ဒီ code ကို ရှင်းပြပါ", "x = 1")
    assert answer.startswith("GEMINI:")
    assert "x = 1" in answer
    assert "စာအုပ်မှ ကိုးကား:" not in answer


def test_question_skips_book_quotes() -> None:
    captured: list[str] = []

    def generate(messages: list[dict]) -> str:
        captured.append(messages[0]["content"])
        return "GEMINI"

    engine = _engine(generate)
    answer = engine.answer("unrelated zzz question", "")
    assert answer == "GEMINI"
    assert captured
    assert "အလယ်အလတ်" in captured[0]
    assert "စာအုပ်မှ ကိုးကား:" not in captured[0]


def test_create_engine_returns_hybrid(monkeypatch) -> None:
    from tutor import hybrid as hy

    class Dummy:
        pass

    monkeypatch.setattr("tutor.config.TUTOR_BACKEND", "hybrid")
    monkeypatch.setattr(hy, "HybridEngine", Dummy)
    created = hy.create_engine()
    assert isinstance(created, Dummy)


def test_create_engine_returns_aaa_when_configured(monkeypatch) -> None:
    from tutor import hybrid as hy

    class DummyAAA:
        pass

    monkeypatch.setattr("tutor.config.TUTOR_BACKEND", "aaa")
    monkeypatch.setattr("tutor.aaa_engine.AAAEngine", DummyAAA)
    created = hy.create_engine()
    assert isinstance(created, DummyAAA)


def test_any_question_uses_general_prompt() -> None:
    captured: list[list[dict]] = []

    def generate(messages: list[dict]) -> str:
        captured.append(messages)
        return "COBOL EXPLANATION"

    engine = _engine(generate)
    answer = engine.answer("cobol programming language ဆိုတာ ဘာလဲ?", "")
    assert answer == "COBOL EXPLANATION"
    assert engine.last_route == "gemini"
    assert engine.last_badge == "Gemini"
    assert captured
    prompt_text = captured[0][0]["content"]
    assert "COBOL" in prompt_text or "cobol" in prompt_text
    assert "အလယ်အလတ်" in prompt_text
    assert "စာအုပ်မှ ကိုးကား:" not in prompt_text
    assert "library" in prompt_text
    assert "စာကြည့်တိုက်" in prompt_text


def test_follow_up_includes_previous_answer() -> None:
    captured: list[str] = []

    def generate(messages: list[dict]) -> str:
        captured.append(messages[0]["content"])
        return "FOLLOW"

    engine = _engine(generate)
    history = [
        {"question": "old one", "answer": "FIRST"},
        {"question": "old two", "answer": "SECOND"},
        {"question": "old three", "answer": "THIRD"},
        {"question": "old four", "answer": "FOURTH"},
    ]
    answer = engine.answer("ဥပမာ ထပ်ပေး", "", history)
    assert answer == "FOLLOW"
    prompt = captured[0]
    assert "FOURTH" in prompt
    assert "THIRD" in prompt
    assert "SECOND" in prompt
    assert "FIRST" not in prompt
    assert "ဥပမာ ထပ်ပေး" in prompt


def test_cynthia_question_uses_miit_passages() -> None:
    captured: list[str] = []

    def generate(messages: list[dict]) -> str:
        captured.append(messages[0]["content"])
        return "MIIT"

    engine = _engine(generate)
    answer = engine.answer("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?", "")
    assert answer == "MIIT"
    assert engine.last_route == "miit"
    assert engine.last_badge == "MIIT"
    prompt = captured[0]
    assert "Cynthia" in prompt
    assert "researchgate.net/profile/Cynthia-Myint" in prompt
    assert "အလယ်အလတ်" not in prompt
    assert "library ကို စာကြည့်တိုက်" not in prompt


def test_typo_cynthia_uses_miit_when_embed_matches(monkeypatch) -> None:
    from tutor.knowledge import KnowledgeChunk, RetrieveResult

    chunk = KnowledgeChunk(
        id="cynthia-role",
        text="Cynthia Myint MIIT",
        sources=("https://www.researchgate.net/profile/Cynthia-Myint",),
        tokens=frozenset(),
    )

    def fake_retrieve(question: str, **kwargs):
        assert "Cynthida" in question
        return RetrieveResult(chunks=[chunk], best_score=0.91)

    monkeypatch.setattr("tutor.specialists.retrieve_miit", fake_retrieve)
    captured: list[str] = []

    def generate(messages: list[dict]) -> str:
        captured.append(messages[0]["content"])
        return "MIIT"

    engine = _engine(generate)
    answer = engine.answer("Cynthida Myint ဆိုတာ ဘယ်သူလဲ?", "")
    assert answer == "MIIT"
    assert engine.last_route == "miit"
    assert engine.last_score == 0.91
    assert "researchgate.net/profile/Cynthia-Myint" in captured[0]


def test_usestate_skips_miit_note() -> None:
    captured: list[str] = []

    def generate(messages: list[dict]) -> str:
        captured.append(messages[0]["content"])
        return "GEMINI"

    engine = _engine(generate)
    answer = engine.answer("useState hook ကို ဘယ်လို သုံးမလဲ?", "")
    assert answer == "GEMINI"
    assert engine.last_route == "gemini"
    prompt = captured[0]
    assert "အလယ်အလတ်" in prompt
    assert "researchgate.net/profile/Cynthia-Myint" not in prompt
    assert "မှတ်တမ်း:" not in prompt


def test_format_answer_metrics_burmese() -> None:
    from tutor.demo_log import format_answer_metrics

    line = format_answer_metrics("COBOL သည် လုပ်ငန်းသုံး ဘာသာစကား ဖြစ်သည်။")
    assert "Language style (not accuracy)." in line
    assert "Myanmar-script ratio:" in line
    assert "English-mix penalty:" in line
    assert "Ends with ။: yes." in line


def test_programming_route_passes_tutor_sampling() -> None:
    seen: dict = {}

    def generate(messages: list[dict], **kwargs) -> str:
        del messages
        seen.update(kwargs)
        return "ok"

    engine = _engine(generate)
    engine.answer("Fragment ဆိုတာ ဘာလဲ?", "")
    assert seen["temperature"] == 0.85
    assert seen["top_p"] == 0.95


def test_miit_route_passes_miit_sampling() -> None:
    seen: dict = {}

    def generate(messages: list[dict], **kwargs) -> str:
        del messages
        seen.update(kwargs)
        return "ok"

    engine = _engine(generate)
    engine.answer("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?", "")
    assert engine.last_route == "miit"
    assert seen["temperature"] == 0.7
    assert seen["top_p"] == 0.9


def test_classifier_programming_skips_miit_notes(monkeypatch) -> None:
    from tutor.router import clear_route_cache, set_route_generate_fn

    clear_route_cache()
    set_route_generate_fn(lambda messages, **kwargs: '{"route":"programming"}')
    captured: list[str] = []

    def generate(messages: list[dict], **kwargs) -> str:
        captured.append(messages[0]["content"])
        return "CODE"

    try:
        engine = _engine(generate)
        answer = engine.answer("useState hook ကို ဘယ်လို သုံးမလဲ?", "")
        assert answer == "CODE"
        assert engine.last_route == "gemini"
        assert "researchgate.net/profile/Cynthia-Myint" not in captured[0]
        assert "အလယ်အလတ်" in captured[0]
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_classifier_miit_keeps_notes(monkeypatch) -> None:
    from tutor.router import clear_route_cache, set_route_generate_fn

    clear_route_cache()
    set_route_generate_fn(lambda messages, **kwargs: '{"route":"miit"}')
    captured: list[str] = []

    def generate(messages: list[dict], **kwargs) -> str:
        captured.append(messages[0]["content"])
        return "MIIT"

    try:
        engine = _engine(generate)
        answer = engine.answer("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?", "")
        assert answer == "MIIT"
        assert engine.last_route == "miit"
        assert "researchgate.net/profile/Cynthia-Myint" in captured[0]
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_classifier_other_skips_chat_generate() -> None:
    from tutor.router import OUT_OF_SCOPE_ANSWER, clear_route_cache, set_route_generate_fn

    clear_route_cache()
    calls = {"n": 0}

    def generate(messages: list[dict], **kwargs) -> str:
        content = str(messages[0].get("content", ""))
        if content.startswith("Classify the student question"):
            return '{"route":"other"}'
        calls["n"] += 1
        return "SHOULD_NOT"

    try:
        engine = _engine(generate)
        answer = engine.answer("What's the weather in Yangon?", "")
        assert answer == OUT_OF_SCOPE_ANSWER
        assert engine.last_route == "other"
        assert calls["n"] == 0
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_ohms_law_hits_gemini_not_out_of_scope() -> None:
    from tutor.router import OUT_OF_SCOPE_ANSWER, clear_route_cache, set_route_generate_fn

    clear_route_cache()
    set_route_generate_fn(lambda messages, **kwargs: '{"route":"other"}')
    calls = {"n": 0}

    def generate(messages: list[dict], **kwargs) -> str:
        calls["n"] += 1
        return "OHM"

    try:
        engine = _engine(generate)
        answer = engine.answer("Ohm's law ဆိုတာ ဘာလဲ?", "")
        assert answer == "OHM"
        assert answer != OUT_OF_SCOPE_ANSWER
        assert engine.last_route == "gemini"
        assert calls["n"] == 1
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_classifier_binary_search_hits_chat_not_out_of_scope() -> None:
    from tutor.router import OUT_OF_SCOPE_ANSWER, clear_route_cache, set_route_generate_fn

    clear_route_cache()
    set_route_generate_fn(lambda messages, **kwargs: '{"route":"other"}')
    calls = {"n": 0}

    def generate(messages: list[dict], **kwargs) -> str:
        calls["n"] += 1
        return "BINARY"

    try:
        engine = _engine(generate)
        answer = engine.answer(
            "binary search algo",
            "def binary_search(arr, target):\n    return 0",
        )
        assert answer == "BINARY"
        assert engine.last_route == "gemini"
        assert answer != OUT_OF_SCOPE_ANSWER
        assert calls["n"] == 1
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_classifier_empty_key_uses_retrieve(monkeypatch) -> None:
    monkeypatch.setattr("tutor.router.resolved_gemini_api_keys", lambda: [])
    from tutor.router import clear_route_cache, set_route_generate_fn

    clear_route_cache()
    set_route_generate_fn(None)
    engine = _engine(lambda messages, **kwargs: "ok")
    engine.answer("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?", "")
    assert engine.last_route == "miit"


def test_cse_followup_does_not_return_out_of_scope() -> None:
    from tutor.router import OUT_OF_SCOPE_ANSWER

    set_route_generate_fn(lambda messages, **kwargs: '{"route":"other"}')
    try:
        engine = _engine(lambda messages, **kwargs: "MORE")
        history = [
            {
                "question": "B.E (Hons.) CSE မှာခုနှစ် ဘယ်ဘာသာတွေကို သင်ကြားပေးပါသလဲ။",
                "answer": "Year I စသင်သည်။",
            }
        ]
        answer = engine.answer("နောက်ထပ် ရှိသေးလား။", "", history)
        assert answer != OUT_OF_SCOPE_ANSWER
        assert answer == "MORE"
        assert engine.last_route == "miit"
    finally:
        set_route_generate_fn(None)
        clear_route_cache()


def test_second_cse_followup_does_not_return_out_of_scope() -> None:
    from tutor.router import OUT_OF_SCOPE_ANSWER

    set_route_generate_fn(lambda messages, **kwargs: '{"route":"other"}')
    try:
        engine = _engine(lambda messages, **kwargs: "REST")
        history = [
            {
                "question": "B.E (Hons.) CSE မှာခုနှစ် ဘယ်ဘာသာတွေကို သင်ကြားပေးပါသလဲ။",
                "answer": "Year I စသင်သည်။",
            },
            {
                "question": "ကျွန်တော့်ကို အသေးစိတ် ပြောပြပါ။",
                "answer": "အပို semester များ ရှိပါသည်။",
            },
        ]
        answer = engine.answer("နောက်ထပ် ရှိသေးလား။", "", history)
        assert answer != OUT_OF_SCOPE_ANSWER
        assert answer == "REST"
        assert engine.last_route == "miit"
    finally:
        set_route_generate_fn(None)
        clear_route_cache()
